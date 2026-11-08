#!/usr/bin/env python3
"""실험적 ChatGPT 웹 UI 조작: 로그인은 사용자, 이미지 생성/다운로드는 가능할 때만 자동 시도.
공식 ChatGPT API가 아니며 화면 변경/제한/브라우저 환경에 따라 실패할 수 있다.
"""
import argparse, time, sys
from pathlib import Path
from miri_common import OUT, read_rows, status_of
from chatgpt_batch import build_prompt, load_templates
from image_workflow import import_one

PROFILE = OUT / 'browser_profile_chatgpt'
INBOX = OUT / 'download_inbox'

def get_playwright():
    try: from playwright.sync_api import sync_playwright
    except ImportError: raise SystemExit('Playwright 설치 필요: python3 -m pip install playwright && python3 -m playwright install chromium')
    return sync_playwright

def choose_row(filename):
    rows,_=read_rows()
    if filename:
        row=next((r for r in rows if r.get('filename')==filename),None)
        if row is None: raise SystemExit('CSV에서 파일명을 찾지 못함: '+filename)
        if status_of(row)!='pending': raise SystemExit('pending 상태가 아닙니다: '+filename)
    else: row=next((r for r in rows if status_of(r)=='pending'),None)
    if not row: raise SystemExit('pending 이미지 없음')
    return row

def main():
    ap=argparse.ArgumentParser(description='ChatGPT 브라우저 이미지 생성 실험 (공식 API 아님)')
    ap.add_argument('--filename',help='대상 파일명 (생략하면 첫 pending)')
    ap.add_argument('--send',action='store_true',help='브라우저 입력창을 찾아 프롬프트 자동 전송 시도')
    ap.add_argument('--auto-download',action='store_true',help='생성 후 다운로드 버튼 자동 클릭 시도 (성공 보장 안 됨)')
    ap.add_argument('--wait-seconds',type=int,default=180,help='다운로드 대기 시간, 기본 180초')
    args=ap.parse_args()
    if args.auto_download and not args.send: ap.error('--auto-download는 --send와 함께 사용')
    row=choose_row(args.filename)
    prompt='한 개의 독립된 이미지로 생성해줘. 이미지 안에 글자나 파일명은 넣지 마. 실제 투명 배경 PNG로 만들어줘.\n\n'+build_prompt(row,load_templates())
    INBOX.mkdir(parents=True,exist_ok=True)
    PROFILE.mkdir(parents=True,exist_ok=True)
    print('대상:',row['subject'],'→',row['filename'])
    print('전용 브라우저 프로필:',PROFILE)
    print('주의: ChatGPT 로그인/보안인증은 직접 진행. 자동화는 이미지 생성/저장을 보장하지 않습니다.')
    sync_playwright=get_playwright()
    with sync_playwright() as p:
        ctx=p.chromium.launch_persistent_context(str(PROFILE),channel="chrome",headless=False,accept_downloads=True,viewport={'width':1280,'height':850})
        page=ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto('https://chatgpt.com/',wait_until='domcontentloaded',timeout=60000)
        if not args.send:
            print('브라우저에서 로그인 후 아래 프롬프트 파일을 직접 붙여넣어 생성/다운로드하세요.')
            f=OUT/'current_image_prompt.txt';f.write_text(prompt,encoding='utf-8');print(f)
            input('이미지를 다운로드한 뒤 Enter를 누르면 종료합니다...')
            ctx.close();return
        input('로그인 및 이미지 생성 가능한 대화창이 준비되면 Enter를 누르세요...')
        editors=[page.locator('#prompt-textarea'),page.locator('[contenteditable="true"][data-placeholder]'),page.locator('div[contenteditable="true"]'),page.locator('textarea')]
        editor=next((x.first for x in editors if x.count()>0 and x.first.is_visible()),None)
        if editor is None:
            print('입력창을 찾지 못했습니다. ChatGPT 화면이 바뀌었을 수 있습니다. 수동 모드를 사용하세요.')
            ctx.close();return
        try:
            editor.fill(prompt,timeout=10000)
            send=page.locator('[data-testid="send-button"]')
            if send.count() and send.first.is_enabled(): send.first.click()
            else: editor.press('Enter')
            print('전송을 시도했습니다. 실제 이미지 생성 성공 여부는 화면에서 확인하세요.')
        except Exception as e:
            print('전송 실패:',str(e)[:250]);ctx.close();return
        if not args.auto_download:
            print('생성 완료 후 화면의 이미지 다운로드 버튼을 직접 눌러주세요.')
            input('다운로드가 끝나면 Enter를 누르세요...')
            ctx.close();return
        # UI에 따라 다운로드 버튼이 다르므로 시도 후 실패하면 사용자 조작으로 넘긴다.
        print('자동 다운로드 버튼 감지 시도 중...')
        start=time.monotonic(); saved=None
        while time.monotonic()-start<args.wait_seconds:
            try:
                buttons=page.get_by_role('button',name='Download',exact=True)
                if buttons.count()==0: buttons=page.get_by_role('button',name='다운로드',exact=True)
                if buttons.count():
                    with page.expect_download(timeout=8000) as d: buttons.last.click()
                    download=d.value
                    target=INBOX/(str(int(time.time()))+'_'+Path(download.suggested_filename).name)
                    download.save_as(target);saved=target;break
            except Exception: pass
            time.sleep(3)
        if saved:
            print('다운로드 감지:',saved)
            try: import_one(str(saved),row['filename'])
            except SystemExit as e: print('자동 가져오기 실패:',e)
            print('검수 실행: python3 png_preflight.py --copy-ready --fix-dpi')
        else:
            print('자동 다운로드 실패/시간 초과. 화면에서 직접 다운로드하고 아래 명령으로 가져오세요:')
            print('python3 image_workflow.py import --source "다운로드한_PNG_경로" --filename "'+row['filename']+'"')
            input('확인 후 Enter를 누르면 종료합니다...')
        ctx.close()
if __name__=='__main__':main()
