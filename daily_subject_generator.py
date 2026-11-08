#!/usr/bin/env python3
"""매일 새로운 소재 10개를 CSV에 추가. API 호출 없음, 로컬 카탈로그 기반."""
import argparse
import csv
import hashlib
import json
import random
import re
from datetime import date, datetime
from pathlib import Path
from miri_common import ROOT, OUT, STYLE_INFO, read_rows, write_rows, norm, make_element_name

CATALOG = ROOT / 'templates' / 'daily_catalog.json'
HISTORY = ROOT / 'input' / 'subject_history.csv'
STATE = OUT / 'daily_generator_state.json'
HISTORY_FIELDS = ['date', 'subject', 'category', 'template_id', 'filename', 'keywords']

def clean_slug(s):
    return re.sub(r'[^a-z0-9_]+', '_', s.lower()).strip('_')

def key(s):
    return re.sub(r'\s+', '', norm(s)).casefold()

def keywords(item, category, category_tags, style):
    terms = [item['ko']] + item.get('tags', []) + category_tags + STYLE_INFO[style][1]
    result, seen = [], set()
    for term in terms:
        term = norm(term)
        if term and key(term) not in seen:
            seen.add(key(term)); result.append(term)
    return ', '.join(result[:8])

def main():
    p = argparse.ArgumentParser(description='매일 새 Subject 10개 자동 준비 (로컬 소재 카탈로그)')
    p.add_argument('--date', default=date.today().isoformat(), help='YYYY-MM-DD (기본: 오늘)')
    p.add_argument('--count', type=int, default=10)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    try:
        run_date = date.fromisoformat(args.date)
    except ValueError:
        p.error('--date는 YYYY-MM-DD 형식이어야 합니다')
    if not 1 <= args.count <= 10:
        p.error('--count는 1~10 사이여야 합니다')
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    rows, header = read_rows()
    prior = []
    if HISTORY.exists():
        with HISTORY.open(encoding='utf-8-sig', newline='') as f:
            prior = list(csv.DictReader(f))
    existing = {key(r.get('subject')) for r in rows} | {key(r.get('subject')) for r in prior}
    used_files = {r.get('filename', '').casefold() for r in rows}
    if any(r.get('date') == run_date.isoformat() for r in prior):
        print(f'{run_date}: 이미 생성한 기록이 있습니다. 중복 생성하지 않습니다.')
        return
    candidates = []
    for category, data in catalog.items():
        for item in data['subjects']:
            if key(item['ko']) not in existing:
                candidates.append((category, data['tags'], item))
    if len(candidates) < args.count:
        print(f'새 소재 부족: 남은 고유 Subject {len(candidates)}개 / 요청 {args.count}개. 카탈로그를 확장하세요. CSV 변경 없음.')
        raise SystemExit(2)
    seed = int(hashlib.sha256(run_date.isoformat().encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    rng.shuffle(candidates)
    selected, categories = [], set()
    # 가능한 한 카테고리를 다양하게 섞음
    for entry in candidates:
        if entry[0] not in categories:
            selected.append(entry); categories.add(entry[0])
        if len(selected) == args.count: break
    if len(selected) < args.count:
        selected_keys = {key(e[2]['ko']) for e in selected}
        selected.extend(e for e in candidates if key(e[2]['ko']) not in selected_keys)
        selected = selected[:args.count]
    styles = list(STYLE_INFO)
    new_rows, new_history = [], []
    for i, (category, tags, item) in enumerate(selected):
        style = styles[(run_date.toordinal() + i) % len(styles)]
        filename = f"daily_{run_date:%Y%m%d}_{clean_slug(item['en'])}_{style}.png"
        if filename.casefold() in used_files:
            raise SystemExit(f'파일명 중복: {filename}')
        used_files.add(filename.casefold())
        kw = keywords(item, category, tags, style)
        new_rows.append({'subject': item['ko'], 'template_id': style, 'filename': filename,
                         'status': 'pending', 'element_name': make_element_name(item['ko'], style),
                         'keywords': kw, 'submitted_at': '', 'reviewed_at': '', 'review_note': ''})
        new_history.append({'date': run_date.isoformat(), 'subject': item['ko'], 'category': category,
                            'template_id': style, 'filename': filename, 'keywords': kw})
    if args.dry_run:
        for row in new_rows: print(f"[미리보기] {row['subject']} | {row['template_id']} | {row['keywords']}")
        return
    # 히스토리보다 원본 CSV를 먼저 기록. 재실행 시 CSV 중복 검사가 안전망.
    write_rows(rows + new_rows, header)
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open('a', encoding='utf-8-sig' if not HISTORY.exists() else 'utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
        if f.tell() == 0: writer.writeheader()
        writer.writerows(new_history)
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({'last_run': datetime.now().astimezone().isoformat(),
                                  'date': run_date.isoformat(), 'added': len(new_rows)}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{run_date}: 신규 Subject {len(new_rows)}개 추가. 전체 {len(rows) + len(new_rows)}개.')
    print('다음 단계: python3 chatgpt_batch.py batch --limit 10 (ChatGPT 웹에 직접 붙여넣기)')

if __name__ == '__main__':
    main()
