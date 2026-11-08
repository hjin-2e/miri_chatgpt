#!/usr/bin/env python3
"""Watch Chrome's download folder and import one newly downloaded PNG safely.
Does not initiate downloads or control ChatGPT. Requires existing v6.3 scripts.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    p = argparse.ArgumentParser(description='ChatGPT PNG 다운로드 감지 → output/images → PNG 검수')
    p.add_argument('--downloads', type=Path, default=Path.home() / 'Downloads')
    p.add_argument('--filename', help='subjects.csv의 대상 PNG 파일명. 생략하면 pending 첫 항목')
    p.add_argument('--timeout', type=int, default=300)
    p.add_argument('--preflight', action='store_true', help='가져온 후 PNG 사전 검수 실행')
    args = p.parse_args()
    try:
        from miri_common import read_rows, status_of
        from PIL import Image
    except ImportError as exc:
        sys.exit('필요한 패키지/프로그램 없음: ' + str(exc) + '\n기존 v6.3 폴더에 스크립트를 넣고 python3 -m pip install Pillow')
    rows, _ = read_rows()
    row = next((r for r in rows if r.get('filename') == args.filename), None) if args.filename else next((r for r in rows if status_of(r) == 'pending'), None)
    if row is None:
        sys.exit('대상 항목을 찾을 수 없습니다. --filename 또는 input/subjects.csv 확인')
    expected = row['filename']
    if (ROOT / 'output' / 'images' / expected).exists():
        sys.exit('이미 존재하는 파일입니다(덮어쓰기 방지): ' + expected)
    downloads = args.downloads.expanduser().resolve()
    if not downloads.is_dir():
        sys.exit('다운로드 폴더를 찾을 수 없습니다: ' + str(downloads))
    # Only watch files appearing or changing AFTER this command starts.
    start_ns = time.time_ns()
    seen = set()
    print(f'대상: {row["subject"]} / {expected}')
    print(f'감시 폴더: {downloads}')
    print('이제 로그인된 Chrome의 ChatGPT에서 해당 이미지의 다운로드 버튼을 한 번 눌러주세요.')
    print('다운로드가 끝나면 자동으로 output/images에 복사합니다. 중지: Ctrl+C')
    deadline = time.monotonic() + args.timeout
    stable = {}
    while time.monotonic() < deadline:
        for f in downloads.iterdir():
            if not f.is_file() or f.suffix.lower() != '.png' or f.name.startswith('.'):
                continue
            try:
                st = f.stat()
            except OSError:
                continue
            if st.st_mtime_ns < start_ns and st.st_ctime_ns < start_ns:
                continue
            if f in seen:
                continue
            previous = stable.get(f)
            stable[f] = (st.st_size, time.monotonic()) if previous is None or previous[0] != st.st_size else previous
            if st.st_size < 100 or time.monotonic() - stable[f][1] < 1.5:
                continue
            try:
                with Image.open(f) as im:
                    if im.format != 'PNG':
                        continue
                    im.verify()
            except (OSError, ValueError):
                continue
            # Ambiguous when multiple PNGs downloaded: do not silently mis-map.
            candidates = []
            for x in downloads.iterdir():
                if x.is_file() and x.suffix.lower() == '.png':
                    try:
                        xs = x.stat()
                        if xs.st_mtime_ns >= start_ns or xs.st_ctime_ns >= start_ns:
                            candidates.append(x)
                    except OSError:
                        pass
            if len(candidates) != 1:
                sys.exit('새 PNG가 여러 개 감지됐습니다. 잘못된 매핑 방지를 위해 중단합니다: ' + ', '.join(x.name for x in candidates))
            print('새 PNG 발견:', f.name)
            command = [sys.executable, str(ROOT / 'image_workflow.py'), 'import', '--source', str(f), '--filename', expected]
            rc = subprocess.call(command, cwd=ROOT)
            if rc != 0:
                sys.exit('이미지 가져오기 실패')
            if args.preflight:
                subprocess.call([sys.executable, str(ROOT / 'png_preflight.py'), '--copy-ready', '--fix-dpi'], cwd=ROOT)
            print('완료: output/images/' + expected)
            return
        time.sleep(0.5)
    sys.exit('시간 초과: 새 PNG 다운로드가 감지되지 않았습니다. 다운로드 버튼을 누른 뒤 다시 실행하세요.')

if __name__ == '__main__':
    main()
