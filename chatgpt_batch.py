#!/usr/bin/env python3
"""ChatGPT 내장 이미지 생성용 배치 프롬프트 도우미 (v5). 이미지 API는 호출하지 않습니다."""
from pathlib import Path
import argparse, json, re, subprocess
from miri_common import (OUT, TEMPLATE_FILE, read_rows, write_rows, find_row, norm, status_of,
                         load_themes, fill_metadata, make_element_name, make_keywords, now_iso, STYLE_INFO)

PROMPTS = OUT / "prompts"


def load_templates():
    return json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))


def safe_name(s):
    return re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", s).strip("_") or "subject"


def clipboard(text):
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except FileNotFoundError:
        return False


def build_prompt(row, templates):
    tid = row["template_id"].strip()
    if tid not in templates:
        raise ValueError(f"알 수 없는 template_id: {tid}")
    prompt = templates[tid]["prompt"]
    prompt = prompt.replace("{subject}", row["subject"].strip())
    keywords = row.get("keywords", "").strip()
    prompt = prompt.replace("{keywords}", keywords or row["subject"].strip())
    return prompt


def cmd_list(rows, templates):
    print("번호 | 상태 | Subject | 템플릿 | 파일명")
    print("-" * 72)
    for i, r in enumerate(rows, 1):
        name = templates.get(r["template_id"], {}).get("name", r["template_id"])
        print(f"{i:>2} | {status_of(r):<9} | {r['subject']} | {name} | {r['filename']}")


def cmd_batch(rows, templates, limit, include_done=False):
    selected = rows if include_done else [r for r in rows if status_of(r) == "pending"]
    selected = selected[:limit]
    if not selected:
        print("생성 대기 중인 Subject가 없습니다.")
        return
    PROMPTS.mkdir(parents=True, exist_ok=True)
    blocks = []
    for idx, row in enumerate(selected, 1):
        prompt = build_prompt(row, templates)
        (PROMPTS / (safe_name(Path(row["filename"]).stem) + ".txt")).write_text(prompt, encoding="utf-8")
        blocks.append(f"## {idx}. {row['subject']} — {templates[row['template_id']]['name']}\n"
                      f"저장 파일명: {row['filename']}\n\n{prompt}")
    batch_text = (
        "아래 작업 목록의 이미지를 생성해줘. 각 항목은 서로 독립된 이미지야.\n"
        "중요: 한 장의 콜라주, 스프라이트 시트, 그리드, 한 화면에 여러 소재를 배치한 이미지로 만들지 말고, "
        "각 항목을 개별 이미지 결과물로 생성해줘. 각 프롬프트의 스타일과 투명 배경 조건을 유지해줘.\n"
        "이미지 생성 기능에서 한 번에 모든 개별 결과물을 만들 수 없는 경우, 첫 번째 항목부터 순서대로 생성하고 "
        "각 결과가 완성된 뒤 다음 항목을 이어서 생성해줘.\n\n" + "\n\n---\n\n".join(blocks))
    out_file = OUT / "batch_prompt.md"
    out_file.write_text(batch_text, encoding="utf-8")
    if clipboard(batch_text):
        print(f"배치 프롬프트 {len(selected)}개를 만들고 클립보드에 복사했습니다.")
    else:
        print(f"배치 프롬프트 {len(selected)}개를 만들었습니다. pbcopy가 없어 파일을 직접 열어 복사하세요.")
    print(f"전체 배치 파일: {out_file}")
    print("ChatGPT 대화창에 붙여넣고, 결과가 항목별로 따로 생성되는지 확인하세요.")


def cmd_next(rows, templates):
    pending = next((r for r in rows if status_of(r) == "pending"), None)
    if not pending:
        print("생성 대기 중인 Subject가 없습니다."); return
    prompt = build_prompt(pending, templates)
    PROMPTS.mkdir(parents=True, exist_ok=True)
    target = PROMPTS / (safe_name(Path(pending["filename"]).stem) + ".txt")
    target.write_text(prompt, encoding="utf-8")
    if clipboard(prompt):
        print(f"클립보드에 복사: {pending['subject']} ({pending['filename']})")
    else:
        print(f"프롬프트 파일을 열어 직접 복사하세요: {target}")


def cmd_set_status(rows, header, filename, new_status, note=""):
    """filename(고유값)으로 상태를 바꾼다. 같은 Subject가 여러 줄이어도 안전."""
    r = find_row(rows, filename)
    if not r:
        raise SystemExit(f"CSV에 없는 파일명입니다: {filename}  (`list`로 확인)")
    r["status"] = new_status
    if new_status == "submitted":
        r["submitted_at"] = now_iso()
    if new_status in ("approved", "rejected"):
        r["reviewed_at"] = now_iso()
    if note:
        r["review_note"] = note
    write_rows(rows, header)
    print(f"{filename}: {new_status}")


def cmd_suggest(rows, header, theme, template_id, count):
    themes = load_themes()
    if theme not in themes:
        raise SystemExit(f"등록된 테마: {', '.join(themes)}  (templates/themes.json에 직접 추가 가능)")
    if template_id not in STYLE_INFO:
        raise SystemExit(f"알 수 없는 template_id. 사용 가능: {', '.join(STYLE_INFO)}")
    existing = {(norm(r["subject"]), norm(r["template_id"])) for r in rows}
    existing_files = {norm(r["filename"]) for r in rows}
    added = 0
    for item in themes[theme]["subjects"]:
        if added >= count:
            break
        if (norm(item["ko"]), template_id) in existing:
            continue
        fn = f"{item['en']}_{template_id}.png"
        if fn in existing_files:
            continue
        rows.append({"subject": item["ko"], "template_id": template_id, "filename": fn, "status": "pending",
                     "element_name": make_element_name(item["ko"], template_id),
                     "keywords": ", ".join(make_keywords(item["ko"], template_id, themes)),
                     "submitted_at": "", "reviewed_at": "", "review_note": ""})
        added += 1
    write_rows(rows, header)
    print(f"테마 '{theme}' / 스타일 '{template_id}': {added}개 추가 (요소 이름·키워드 자동 입력)")


def main():
    parser = argparse.ArgumentParser(description="ChatGPT 이미지 생성 배치 프롬프트 도우미 v5")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="Subject와 진행 상태 확인")
    b = sub.add_parser("batch", help="대기 중인 Subject 최대 10개를 한 번에 프롬프트화")
    b.add_argument("--limit", type=int, default=10, choices=range(1, 11), metavar="1..10")
    b.add_argument("--include-done", action="store_true")
    sub.add_parser("next", help="다음 대기 Subject 하나를 클립보드에 복사")
    for name, hlp in (("done", "이미지 생성 완료(generated)"), ("submit", "미리캔버스에 제출함(submitted)"),
                      ("approve", "수동으로 승인 처리"), ("reject", "수동으로 반려 처리")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("--filename", help="CSV의 filename (권장, 고유값)")
        p.add_argument("--subject", help="Subject로 지정 (같은 Subject가 여러 줄이면 거부됨)")
        if name == "reject":
            p.add_argument("--note", default="")
    s = sub.add_parser("suggest", help="테마로 Subject·요소 이름·키워드를 자동 생성해 CSV에 추가")
    s.add_argument("--theme", required=True)
    s.add_argument("--template", default="cute_3d_icon")
    s.add_argument("--count", type=int, default=10)
    k = sub.add_parser("keywords", help="비어 있는 요소 이름·키워드를 자동으로 채움")
    k.add_argument("--overwrite", action="store_true", help="이미 있는 값도 다시 생성")
    args = parser.parse_args()

    rows, header = read_rows()
    templates = load_templates()
    c = args.command
    if c == "list": cmd_list(rows, templates)
    elif c == "batch": cmd_batch(rows, templates, args.limit, args.include_done)
    elif c == "next": cmd_next(rows, templates)
    elif c in ("done", "submit", "approve", "reject"):
        fn = args.filename
        if not fn:
            if not args.subject:
                raise SystemExit("--filename (권장) 또는 --subject 가 필요합니다.")
            hits = [r for r in rows if norm(r["subject"]) == norm(args.subject)]
            if len(hits) != 1:
                names = ", ".join(r["filename"] for r in hits) or "없음"
                raise SystemExit(f"Subject '{args.subject}'가 {len(hits)}줄입니다. --filename으로 지정하세요: {names}")
            fn = hits[0]["filename"]
        new = {"done": "generated", "submit": "submitted", "approve": "approved", "reject": "rejected"}[c]
        cmd_set_status(rows, header, fn, new, getattr(args, "note", ""))
    elif c == "suggest": cmd_suggest(rows, header, args.theme, args.template, args.count)
    elif c == "keywords":
        n = fill_metadata(rows, load_themes(), args.overwrite)
        write_rows(rows, header)
        print(f"요소 이름·키워드 자동 입력: {n}행")


if __name__ == "__main__":
    main()
