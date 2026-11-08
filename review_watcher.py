#!/usr/bin/env python3
"""미리캔버스 심사 결과 메일 확인기.

- 'submitted' 상태의 항목만 대상으로, 받은 메일에서 승인/반려 안내를 찾아 CSV 상태를 갱신합니다.
- 확인 주기는 config.json의 interval_days이며 기본 1일입니다.
- 알림은 config.json의 notify.channels (기본: macos + email)로 모두 보냅니다.
- 사이트에 로그인하지 않습니다. 메일(IMAP)만 읽습니다.
"""
import argparse, email, imaplib, re, sys
from datetime import datetime, timedelta, timezone
from email import policy
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from html import unescape
from pathlib import Path
from miri_common import (read_rows, write_rows, load_config, load_state, save_state, now_iso, norm, status_of,
                         notify, get_mail_password)

MAX_SEEN = 500


def dh(value):
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return str(value or "")


def message_text(msg):
    """text/plain 우선, 없으면 HTML 태그를 제거한 텍스트."""
    plain, html = [], []
    for part in msg.walk():
        if part.get_content_maintype() != "text":
            continue
        try:
            payload = part.get_content()
        except Exception:
            continue
        (plain if part.get_content_subtype() == "plain" else html).append(str(payload))
    if plain:
        return "\n".join(plain)
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", "\n".join(html))
    return unescape(re.sub(r"<[^>]+>", " ", text))


def parse_mail(raw):
    msg = email.message_from_bytes(raw, policy=policy.default)
    try:
        date = parsedate_to_datetime(msg["Date"]) if msg["Date"] else None
    except Exception:
        date = None
    return {"id": norm(msg["Message-ID"]) or f"nomsgid:{hash(raw)}", "from": parseaddr(dh(msg["From"]))[1].lower(),
            "from_raw": dh(msg["From"]).lower(), "subject": dh(msg["Subject"]), "date": date,
            "text": re.sub(r"[ \t ]+", " ", message_text(msg))}


def load_eml_dir(path):
    return [parse_mail(p.read_bytes()) for p in sorted(Path(path).glob("*.eml"))]


def fetch_imap(cfg, since):
    mail = cfg["mail"]
    box = imaplib.IMAP4_SSL(mail.get("imap_host", "imap.gmail.com"), timeout=60)
    try:
        box.login(mail["user"], get_mail_password(mail))
        box.select(mail.get("folder", "INBOX"), readonly=True)
        typ, data = box.search(None, "SINCE", since.strftime("%d-%b-%Y"))
        if typ != "OK":
            raise RuntimeError(f"IMAP 검색 실패: {typ}")
        out = []
        for num in data[0].split():
            typ, parts = box.fetch(num, "(BODY.PEEK[])")   # PEEK: 읽음 표시를 바꾸지 않음
            if typ == "OK" and parts and isinstance(parts[0], tuple):
                out.append(parse_mail(parts[0][1]))
        return out
    finally:
        try:
            box.logout()
        except Exception:
            pass


def is_review_mail(m, rcfg):
    sender_ok = any(s.lower() in m["from_raw"] or s.lower() in m["from"] for s in rcfg["sender_contains"])
    hint = rcfg.get("subject_hint") or []
    return sender_ok and (not hint or any(h in m["subject"] for h in hint))


def classify(text, rcfg):
    """명확한 확정 문구만 판정한다. 진행/수정 요청 문맥에서는 자동 확정하지 않는다."""
    t = re.sub(r"\s+", " ", text or "").lower()
    if any(w.lower() in t for w in rcfg.get("pending_words", [])):
        return None
    # 부정·반려 확정 문구를 승인보다 먼저 검사
    if any(w.lower() in t for w in rcfg.get("reject_words", [])):
        return "rejected"
    if any(w.lower() in t for w in rcfg.get("approve_words", [])):
        return "approved"
    return None


def match_rows(m, submitted):
    """메일이 가리키는 submitted 행을 찾는다. 반환: [(row, 근거문장)], 모호하면 빈 리스트."""
    text = f"{m['subject']}\n{m['text']}"
    hits = []
    for r in submitted:
        name, subj = norm(r.get("element_name")), norm(r.get("subject"))
        pos = text.find(name) if name else -1
        if pos < 0 and subj:
            same = [x for x in submitted if norm(x.get("subject")) == subj]
            if len(same) == 1:           # 같은 소재가 여러 스타일로 제출된 경우엔 소재명만으로 단정하지 않음
                pos = text.find(subj)
        if pos >= 0:
            hits.append((r, text[max(0, pos - 80): pos + len(name or subj) + 120]))
    return hits


def run_check(args):
    cfg = load_config()
    rcfg = cfg["review_mail"]
    rows, header = read_rows()
    submitted = [r for r in rows if status_of(r) == "submitted"]
    state = load_state()
    interval = timedelta(days=cfg.get("interval_days", 3))

    last = state.get("last_checked")
    if last and not args.force:
        elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(last)
        if elapsed < interval - timedelta(hours=1):
            nxt = datetime.fromisoformat(last) + interval
            print(f"확인 주기 전입니다. 다음 확인 예정: {nxt.astimezone():%Y-%m-%d %H:%M}  (--force로 즉시 확인)")
            return 0
    if not submitted:
        summary = "현재 CSV에 미리캔버스 심사 확인 대상(submitted)이 없습니다."
        print(summary)
        if not args.dry_run and cfg.get("notify", {}).get("on_no_change", False):
            print("알림:", notify("심사 확인 요약", summary, cfg, args.dry_run))
        return 0

    try:
        if args.eml_dir:
            mails = load_eml_dir(args.eml_dir)
        else:
            oldest = min((datetime.fromisoformat(r["submitted_at"]) for r in submitted if norm(r.get("submitted_at"))),
                         default=None)
            days = cfg["mail"].get("lookback_days", 30)
            since = (oldest - timedelta(days=1)) if oldest else (datetime.now() - timedelta(days=days))
            mails = fetch_imap(cfg, since)
    except Exception as e:
        msg = f"메일 확인 실패: {type(e).__name__}: {e}"
        print(msg)
        notify("심사 메일 확인 실패", msg, cfg, args.dry_run)   # last_checked는 갱신하지 않아 다음 실행 때 재시도
        return 1

    seen = list(state.get("seen", []))
    unmatched_seen = set(state.get("unmatched_notified", []))
    changes, unmatched = [], []
    for m in sorted((x for x in mails if is_review_mail(x, rcfg)), key=lambda x: x["date"] or datetime.min.replace(tzinfo=timezone.utc)):
        if m["id"] in seen:
            continue
        pending_rows = [r for r in submitted if status_of(r) == "submitted"]
        hits = match_rows(m, pending_rows)
        applied = False
        for r, ctx in hits:
            verdict = classify(ctx, rcfg)
            if verdict is None and len(hits) == 1:
                verdict = classify(m["subject"], rcfg)
            if verdict:
                r["status"], r["reviewed_at"] = verdict, now_iso()
                r["review_note"] = f"메일: {m['subject'][:80]}"
                changes.append((r, verdict))
                applied = True
        full_verdict = classify(f"{m['subject']}\n{m['text']}", rcfg)
        if applied:
            seen.append(m["id"])
        elif full_verdict:
            # 매칭 실패 메일은 seen 처리하지 않아 다음 실행에서 다시 검사할 수 있게 한다.
            if m["id"] not in unmatched_seen:
                unmatched.append(m)
                unmatched_seen.add(m["id"])

    still = [r for r in rows if status_of(r) == "submitted"]
    if changes and not args.dry_run:
        write_rows(rows, header)
    if not args.dry_run:
        state["last_checked"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        state["seen"] = seen[-MAX_SEEN:]
        state["unmatched_notified"] = list(unmatched_seen)[-MAX_SEEN:]
        save_state(state)

    lines = []
    for r, v in changes:
        lines.append(f"{'승인' if v == 'approved' else '반려'}: {r['element_name'] or r['subject']} ({r['filename']})")
    for m in unmatched:
        lines.append(f"확인 필요(어느 항목인지 특정 못함): {m['subject'][:60]}")
    lines.append(f"심사 대기 중: {len(still)}개")
    summary = "\n".join(lines)
    print(summary)

    if (changes or unmatched) or cfg.get("notify", {}).get("on_no_change", False):
        title = f"심사 결과 {len(changes)}건 도착" if changes else ("심사 메일 확인 필요" if unmatched else "심사 변동 없음")
        res = notify(title, summary, cfg, args.dry_run)
        print("알림:", res)
    return 0


def run_status(_):
    cfg = load_config()
    rows, _h = read_rows()
    state = load_state()
    counts = {}
    for r in rows:
        counts[status_of(r)] = counts.get(status_of(r), 0) + 1
    print("상태별 개수:", counts)
    print("마지막 확인:", state.get("last_checked", "없음"), "| 확인 주기:", cfg.get("interval_days", 1), "일")
    for r in rows:
        if status_of(r) in ("submitted", "rejected"):
            print(f"  {status_of(r):<9} {r['filename']}  제출 {r.get('submitted_at','')[:10]}  {r.get('review_note','')}")


def main():
    ap = argparse.ArgumentParser(description="미리캔버스 심사 메일 확인기")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="주기가 됐으면 메일을 읽어 심사 상태 갱신 + 알림")
    c.add_argument("--force", action="store_true", help="확인 주기와 관계없이 지금 확인")
    c.add_argument("--dry-run", action="store_true", help="CSV/상태를 저장하지 않고 알림도 화면에만 출력")
    c.add_argument("--eml-dir", help="IMAP 대신 .eml 파일 폴더를 읽음 (테스트용)")
    sub.add_parser("status", help="현재 상태와 마지막 확인 시각 보기")
    args = ap.parse_args()
    sys.exit(run_check(args) if args.cmd == "check" else (run_status(args) or 0))


if __name__ == "__main__":
    main()
