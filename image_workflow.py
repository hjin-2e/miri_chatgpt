#!/usr/bin/env python3
"""ChatGPT 웹에서 수동 다운로드한 이미지의 안전한 로컬 매핑/검수 도우미."""
import argparse, shutil, sys
from pathlib import Path
from miri_common import OUT, read_rows, write_rows, find_row, status_of
from chatgpt_batch import build_prompt, load_templates, clipboard

INBOX=OUT/'download_inbox'
IMAGES=OUT/'images'

def prepare():
    rows,_=read_rows()
    row=next((r for r in rows if status_of(r)=='pending'),None)
    if not row:
        print('생성 대기 항목 없음');return
    prompt=build_prompt(row,load_templates())
    text=f"""하나의 독립된 이미지만 생성해줘. 콜라주나 여러 항목을 한 이미지에 합치지 마.\n\n{prompt}\n\n이미지 안에 글자나 파일명을 그리지 마. 피사체 전체가 잘리지 않도록 하고 배경은 실제 투명 PNG를 요청해.\n"""
    p=OUT/'current_image_prompt.txt';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text,encoding='utf-8')
    copied=clipboard(text)
    print(f'현재 소재: {row["subject"]} / 스타일: {row["template_id"]}')
    print(f'기대 파일명: {row["filename"]}')
    print(f'프롬프트: {p}'+(' (클립보드 복사됨)' if copied else ''))
    print('ChatGPT에서 이미지 1개 생성 → 다운로드 → 파일을 output/download_inbox에 이동하세요.')

def import_one(source, filename):
    rows,header=read_rows();row=find_row(rows,filename)
    if not row: raise SystemExit('CSV에 없는 파일명: '+filename)
    source=Path(source).expanduser().resolve()
    if not source.is_file(): raise SystemExit('원본 파일 없음: '+str(source))
    if source.suffix.lower()!='.png': raise SystemExit('PNG만 허용합니다. ChatGPT에서 PNG를 다운로드하세요.')
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit('Pillow 설치 필요: python3 -m pip install Pillow')
    with Image.open(source) as im:
        im.load()
        if im.format!='PNG': raise SystemExit('실제 PNG 형식이 아닙니다.')
        rgba=im.convert('RGBA')
        alpha=rgba.getchannel('A')
        transparent=alpha.getextrema()[0]<255
        w,h=im.size
    IMAGES.mkdir(parents=True,exist_ok=True)
    dest=IMAGES/filename
    if dest.exists(): raise SystemExit('동일 파일명 이미 존재: '+str(dest)+' (덮어쓰기 금지)')
    shutil.copy2(source,dest)
    print(f'이미지 복사: {dest} ({w}×{h})')
    if not transparent:
        print('주의: 투명 픽셀이 없습니다. 배경 제거 후 다시 검수하세요. CSV 상태는 변경하지 않습니다.')
        return
    row['status']='generated'
    write_rows(rows,header)
    print('투명 픽셀 확인 / CSV 상태 generated 변경. PNG 사전 검수도 반드시 실행하세요.')
    print('python3 png_preflight.py --copy-ready')

def main():
    ap=argparse.ArgumentParser(description='ChatGPT 수동 이미지 생성 + 다운로드 매핑 도우미')
    sub=ap.add_subparsers(dest='cmd',required=True)
    sub.add_parser('prepare',help='다음 1개 이미지 프롬프트 클립보드 복사')
    imp=sub.add_parser('import',help='다운로드한 PNG를 CSV 파일명으로 매핑')
    imp.add_argument('--source',required=True,help='다운로드된 실제 PNG 경로')
    imp.add_argument('--filename',required=True,help='subjects.csv의 filename')
    args=ap.parse_args()
    if args.cmd=='prepare':prepare()
    else:import_one(args.source,args.filename)
if __name__=='__main__':main()
