#!/bin/bash
cd "$(dirname "$0")"
echo "1) 목록  2) 10개 배치 프롬프트  3) 다음 1개 프롬프트  4) PNG 사전 검수  5) 통과 파일 복사"
echo "6) 테마로 Subject·키워드 자동 생성  7) 요소 이름·키워드 빈칸 채우기  8) 심사 메일 확인(지금)  9) 상태 보기"
read -r -p "선택 (1-9): " choice
case "$choice" in
  1) python3 chatgpt_batch.py list ;;
  2) python3 chatgpt_batch.py batch ;;
  3) python3 chatgpt_batch.py next ;;
  4) python3 png_preflight.py ;;
  5) python3 png_preflight.py --copy-ready ;;
  6) read -r -p "테마(겨울/봄/여름/가을): " th; read -r -p "스타일 template_id [cute_3d_icon]: " tp
     read -r -p "개수 [10]: " n
     python3 chatgpt_batch.py suggest --theme "$th" --template "${tp:-cute_3d_icon}" --count "${n:-10}" ;;
  7) python3 chatgpt_batch.py keywords ;;
  8) python3 review_watcher.py check --force ;;
  9) python3 review_watcher.py status ;;
  *) echo "잘못된 선택입니다." ;;
esac
echo
read -r -p "엔터를 누르면 종료합니다."
