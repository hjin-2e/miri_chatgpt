#!/usr/bin/env python3
"""공통 모듈: CSV 입출력, 상태 값, 설정, 키워드 생성, 알림(macOS + 이메일)."""
from pathlib import Path
import csv, json, os, re, smtplib, subprocess, unicodedata
from datetime import datetime
from email.message import EmailMessage

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "input" / "subjects.csv"
TEMPLATE_FILE = ROOT / "templates" / "prompt_templates.json"
THEME_FILE = ROOT / "templates" / "themes.json"
CONFIG_FILE = ROOT / "config.json"
STATE_FILE = ROOT / "output" / "state.json"
OUT = ROOT / "output"

BASE_FIELDS = ["subject", "template_id", "filename", "status",
               "element_name", "keywords", "submitted_at", "reviewed_at", "review_note"]

# 상태 흐름: pending -> generated -> submitted -> approved / rejected  (done = generated 별칭)
STATUS_ALIAS = {"done": "generated"}


def norm(s):
    return unicodedata.normalize("NFC", str(s or "")).strip()


def status_of(row):
    s = norm(row.get("status")).lower()
    return STATUS_ALIAS.get(s, s)


# ---------- CSV ----------
def read_rows():
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames or []
    for r in rows:
        for k in BASE_FIELDS:
            r.setdefault(k, "")
            if r[k] is None:
                r[k] = ""
    return rows, header


def write_rows(rows, header=None):
    fields = list(header or [])
    for k in BASE_FIELDS:            # 새 컬럼은 자동으로 추가
        if k not in fields:
            fields.append(k)
    for r in rows:                   # 사용자가 추가한 컬럼도 보존
        for k in r:
            if k not in fields:
                fields.append(k)
    tmp = CSV_PATH.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(CSV_PATH)            # 쓰는 도중 중단돼도 원본 보호


def find_row(rows, filename):
    fn = norm(filename)
    for r in rows:
        if norm(r.get("filename")) == fn:
            return r
    return None


# ---------- 설정 / 상태 ----------
def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---------- 키워드 / 요소 이름 ----------
STYLE_INFO = {
    "cute_3d_icon":    ("3D 아이콘",   ["3D", "아이콘", "귀여운", "입체"]),
    "clear_bubble":    ("투명 버블",   ["투명", "버블", "젤리", "아이콘"]),
    "wax_crayon":      ("크레용",      ["크레용", "왁스", "손그림", "귀여운"]),
    "soft_oil_pastel": ("오일파스텔",  ["오일파스텔", "파스텔", "손그림", "따뜻한"]),
    "naive_doodle":    ("낙서",        ["낙서", "도들", "손그림", "심플"]),
    "watercolor":      ("수채화",      ["수채화", "수채", "손그림", "클립아트"]),
}


def load_themes():
    return json.loads(THEME_FILE.read_text(encoding="utf-8"))


def find_subject_info(subject, themes):
    """subject가 속한 테마와 개별 태그를 찾는다."""
    s = norm(subject)
    for tname, t in themes.items():
        for item in t["subjects"]:
            if norm(item["ko"]) == s:
                return tname, t, item
    return None, None, None


def make_element_name(subject, template_id):
    label = STYLE_INFO.get(template_id, ("", []))[0]
    return f"{norm(subject)} {label}".strip()


def make_keywords(subject, template_id, themes, limit=8):
    """키워드 1~8개: 소재 > 소재별 태그 > 테마 태그 > 스타일 태그 순서로 채운다."""
    tname, theme, item = find_subject_info(subject, themes)
    words = [norm(subject)]
    words += [w for w in str(norm(subject)).split() if len(w) > 1]
    if item:
        words += item.get("tags", [])
    if theme:
        words += theme.get("tags", [])
    words += STYLE_INFO.get(template_id, ("", []))[1]
    seen, out = set(), []
    for w in words:
        w = norm(w)
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    return out[:max(1, min(limit, 8))]


def fill_metadata(rows, themes, overwrite=False):
    """element_name / keywords가 비어 있는 행을 자동으로 채운다. 채운 개수를 반환."""
    n = 0
    for r in rows:
        tid = norm(r.get("template_id"))
        if overwrite or not norm(r.get("element_name")):
            r["element_name"] = make_element_name(r["subject"], tid)
            n += 1
        if overwrite or not norm(r.get("keywords")):
            r["keywords"] = ", ".join(make_keywords(r["subject"], tid, themes))
    return n


# ---------- 알림 (macOS + 이메일) ----------
def _applescript_escape(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def notify_macos(title, message):
    script = f'display notification "{_applescript_escape(message[:240])}" with title "{_applescript_escape(title)}"'
    subprocess.run(["osascript", "-e", script], check=True, timeout=15)


def get_mail_password(cfg):
    pw = os.environ.get("MIRI_MAIL_PASSWORD")
    if pw:
        return pw
    service = cfg.get("keychain_service", "miri_watcher")
    try:  # macOS 키체인: security add-generic-password -s miri_watcher -a <메일주소> -w
        res = subprocess.run(["security", "find-generic-password", "-s", service, "-a", cfg["user"], "-w"],
                             capture_output=True, text=True, timeout=15, check=True)
        return res.stdout.strip()
    except Exception:
        raise RuntimeError("메일 앱 비밀번호를 찾을 수 없습니다. README의 '메일 설정'을 확인하세요.")


def notify_email(title, message, cfg):
    mail = cfg["mail"]
    msg = EmailMessage()
    msg["Subject"] = f"[미리캔버스] {title}"
    msg["From"] = mail["user"]
    msg["To"] = cfg.get("notify_to") or mail["user"]
    msg.set_content(message)
    with smtplib.SMTP_SSL(mail.get("smtp_host", "smtp.gmail.com"), mail.get("smtp_port", 465), timeout=30) as s:
        s.login(mail["user"], get_mail_password(mail))
        s.send_message(msg)


def notify(title, message, cfg, dry_run=False):
    """cfg['notify']['channels']에 지정된 채널(기본: macos + email)로 모두 보낸다.
    한 채널이 실패해도 나머지는 계속 보낸다. 결과 dict 반환."""
    channels = cfg.get("notify", {}).get("channels", ["macos", "email"])
    results = {}
    for ch in channels:
        if dry_run:
            print(f"[dry-run:{ch}] {title}\n{message}\n")
            results[ch] = "dry-run"
            continue
        try:
            if ch == "macos":
                notify_macos(title, message)
            elif ch == "email":
                notify_email(title, message, cfg)
            else:
                raise ValueError(f"알 수 없는 알림 채널: {ch}")
            results[ch] = "ok"
        except Exception as e:
            results[ch] = f"실패: {type(e).__name__}: {e}"
    return results
