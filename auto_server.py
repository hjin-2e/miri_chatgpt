#!/usr/bin/env python3
"""Local-only queue and download importer for ChatGPT Chrome extension."""
import argparse, json, csv, re, subprocess, sys, time, threading, shutil
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent
STATE={'items':[], 'active':None, 'events':[]}
LOCK=threading.RLock()

def safe_name(s):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.png',s or '') or '..' in s: raise ValueError('unsafe filename')
    return s

def load():
    src=ROOT/'input'/'subjects.csv'
    if not src.exists(): raise SystemExit(f'CSV 없음: {src}')
    with src.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    from importlib.util import spec_from_file_location,module_from_spec
    promptmod=ROOT/'miri_common.py'
    # Simple, self-contained English prompts for browser keystroke reliability.
    for r in rows:
        name=r.get('filename') or r.get('fileName')
        if not name: continue
        try: safe_name(name)
        except ValueError: continue
        if (ROOT/'output'/'images'/name).exists(): continue
        subject=r.get('subject') or r.get('elementName') or name.rsplit('.',1)[0]
        style=(r.get('template_id') or 'cute_3d_icon').replace('_',' ')
        # Avoid Korean IME keyboard issues by using clipboard-like DOM insertion.
        prompt=(f'Create exactly one isolated illustration of {subject}. Style: {style}. '
                'Single subject centered, fully visible, clean smooth edges, transparent PNG with true alpha. '
                'No floor, no cast shadow, no background, no text, no logo, no collage.')
        STATE['items'].append({'filename':name,'prompt':prompt,'subject':subject,'status':'pending'})

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,code,obj):
        data=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path=='/health': return self.reply(200,{'ok':True})
        if self.path=='/next':
            with LOCK:
                a=STATE['active']
                if a is None:
                    a=next((i for i in STATE['items'] if i['status']=='pending'),None)
                    if a: a['status']='in_progress'; STATE['active']=a
                return self.reply(200,{'item':a})
        if self.path=='/status':
            with LOCK:return self.reply(200,{'items':STATE['items'],'events':STATE['events'][-15:]})
        self.reply(404,{'error':'not found'})
    def do_POST(self):
        if self.path not in ('/complete','/fail'):return self.reply(404,{'error':'not found'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>8192:raise ValueError('too large')
            data=json.loads(self.rfile.read(n))
            name=safe_name(data.get('filename'))
            with LOCK:
                a=STATE['active']
                if not a or a['filename']!=name:raise ValueError('not active item')
                a['status']='downloaded' if self.path=='/complete' else 'failed'
                a['message']=str(data.get('message',''))[:300]
                STATE['events'].append({'file':name,'status':a['status'],'message':a['message']})
                STATE['active']=None
            return self.reply(200,{'ok':True})
        except Exception as e:return self.reply(400,{'error':str(e)})

def watch(download_dir, preflight):
    inbox=download_dir/'miri_auto_inbox'
    dest=ROOT/'output'/'images';dest.mkdir(parents=True,exist_ok=True)
    seen=set()
    while True:
        with LOCK: candidates=[i for i in STATE['items'] if i['status']=='downloaded']
        for item in candidates:
            name=item['filename']; src=inbox/name; target=dest/name
            if not src.exists() or target.exists():
                if target.exists(): item['status']='ready'
                continue
            try:
                # Wait for Chrome to finish and validate actual PNG, not just extension notification.
                if time.time()-src.stat().st_mtime<1:continue
                from PIL import Image
                with Image.open(src) as im:
                    if im.format!='PNG':raise ValueError('not PNG')
                    im.verify()
                shutil.copy2(src,target)
                item['status']='ready';print('저장 완료:',target,flush=True)
                if preflight and (ROOT/'png_preflight.py').exists():
                    subprocess.run([sys.executable,str(ROOT/'png_preflight.py'),'--copy-ready','--fix-dpi'],cwd=ROOT,check=False)
            except Exception as e:
                item['status']='import_error';print('가져오기 실패:',name,e,flush=True)
        time.sleep(1)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--downloads',type=Path,default=Path.home()/'Downloads');ap.add_argument('--port',type=int,default=8765);ap.add_argument('--preflight',action='store_true');args=ap.parse_args()
    load();threading.Thread(target=watch,args=(args.downloads.expanduser(),args.preflight),daemon=True).start()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'로컬 서버: http://127.0.0.1:{args.port} / 대기 {len(STATE["items"])}개',flush=True)
    print('Chrome 확장 프로그램을 켜고 ChatGPT 탭을 열어 두세요.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
if __name__=='__main__':main()
