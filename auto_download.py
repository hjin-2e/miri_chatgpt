#!/usr/bin/env python3
"""Run existing download bridge and click a download button in the user's logged-in Chrome."""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = r'''
tell application "Google Chrome" to activate
delay 0.5
tell application "System Events"
  tell process "Google Chrome"
    set frontmost to true
    set hits to {}
    try
      set elems to entire contents of front window
      repeat with e in elems
        try
          if role of e is "AXButton" then
            set n to ""
            set d to ""
            try
              set n to name of e as text
            end try
            try
              set d to description of e as text
            end try
            if n contains "다운로드" or n contains "Download" or d contains "다운로드" or d contains "Download" then
              set end of hits to e
            end if
          end if
        end try
      end repeat
    on error errText
      error "Chrome 접근성 요소를 읽지 못했습니다: " & errText
    end try
    if (count of hits) is not 1 then
      error "다운로드 버튼을 정확히 하나 찾지 못했습니다. 발견 수: " & (count of hits) & ". 잘못된 클릭을 방지하기 위해 중단합니다."
    end if
    click item 1 of hits
  end tell
end tell
'''

def main():
    p = argparse.ArgumentParser(description='Chrome 다운로드 버튼 자동 클릭 + 기존 다운로드 감지')
    p.add_argument('--filename', required=True)
    p.add_argument('--timeout', type=int, default=300)
    p.add_argument('--preflight', action='store_true')
    p.add_argument('--click-x', type=int, help='접근성 탐색 실패 시 사용자가 확인한 화면 절대 좌표')
    p.add_argument('--click-y', type=int)
    args = p.parse_args()
    if (args.click_x is None) != (args.click_y is None):
        p.error('--click-x 와 --click-y 는 함께 지정해야 합니다')
    bridge = ROOT / 'download_bridge.py'
    if not bridge.exists():
        sys.exit('download_bridge.py가 같은 폴더에 없습니다.')
    dest = ROOT / 'output' / 'images' / args.filename
    if dest.exists():
        sys.exit(f'이미 존재하는 파일입니다(덮어쓰기 방지): {dest}')
    cmd = [sys.executable, str(bridge), '--filename', args.filename, '--timeout', str(args.timeout)]
    if args.preflight:
        cmd.append('--preflight')
    watcher = subprocess.Popen(cmd, cwd=ROOT)
    try:
        time.sleep(2)
        if watcher.poll() is not None:
            sys.exit('다운로드 감시가 시작되지 않았습니다. 위 오류 메시지를 확인하세요.')
        if args.click_x is not None:
            click_script = f'''tell application "Google Chrome" to activate\ndelay 0.5\ntell application "System Events" to click at {{{args.click_x}, {args.click_y}}}\n'''
        else:
            click_script = SCRIPT
        result = subprocess.run(['osascript', '-e', click_script], text=True, capture_output=True)
        if result.returncode:
            sys.exit('다운로드 자동 클릭 실패: ' + (result.stderr.strip() or result.stdout.strip()) + '\n이미지 화면이 열려 있는지, iTerm 접근성 권한이 있는지 확인하세요.')
        print('다운로드 클릭 명령 실행. 파일 저장 및 검수 결과를 기다리는 중...', flush=True)
        sys.exit(watcher.wait())
    finally:
        if watcher.poll() is None:
            watcher.terminate()
            try:
                watcher.wait(timeout=5)
            except subprocess.TimeoutExpired:
                watcher.kill()

if __name__ == '__main__':
    main()
