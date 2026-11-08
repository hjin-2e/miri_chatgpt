# v6.3 — ChatGPT 웹 브라우저 자동화 실험 + PNG 검수 개선

## 중요한 한계
- ChatGPT 내장 이미지 생성에는 이 프로젝트가 사용할 공식 무인 실행 API가 없습니다. 이 스크립트는 Playwright로 웹 UI를 조작하는 **실험 기능**입니다. 로그인/인증/사용량 제한을 우회하지 않습니다. UI 변경 시 동작하지 않을 수 있습니다.
- 로그인은 사용자 본인이 전용 브라우저 창에서 합니다. 비밀번호를 코드에 넣지 않습니다.
- 기본적으로 이미지 생성은 사용자가 확인합니다. `--send --auto-download`를 주면 **1개 이미지에 한해** 전송/다운로드를 시도합니다. 완전 무인 실행, 매일 10개 생성, 미리캔버스 자동 제출은 아직 구현되지 않았습니다.
- 이미지 생성 실패, 다운로드 실패, 배경 불투명, 해상도/DPI 미달 시 `upload_ready`는 비어 있을 수 있습니다. PNG 검수 통과는 심사 통과 보장이 아닙니다.

## 설치
```bash
python3 -m pip install Pillow playwright
python3 -m playwright install chromium
```

## 1개 테스트
```bash
python3 chatgpt_browser.py --send --auto-download --wait-seconds 240
```
전용 Chromium 창에서 ChatGPT 로그인 후 터미널에서 Enter를 누릅니다. 생성 및 다운로드를 시도합니다. 자동 다운로드에 실패하면 이미지의 다운로드 버튼을 직접 눌러서:
```bash
python3 image_workflow.py import --source "$HOME/Downloads/실제파일.png" --filename "CSV에_있는_파일명.png"
```

## 업로드 준비 폴더가 비는 문제
```bash
python3 png_preflight.py --copy-ready --fix-dpi
cat output/review/png_quality_report.csv
open output/upload_ready
```
- `MISSING`: `output/images`에 CSV와 같은 이름의 파일이 없음
- `REVIEW`: PNG가 있지만 투명도/해상도/용량/DPI 등 기준 미충족. `checks` 열을 확인
- `READY`: 검수 통과하여 `output/upload_ready`에 사본 생성
- `--fix-dpi`는 **사본에만** DPI 120 메타데이터를 기록하며 원본 이미지는 보존합니다.
- 생성 이미지에 투명 픽셀이 없으면 `import`가 이미지를 복사해도 CSV 상태를 generated로 바꾸지 않습니다. 투명 배경으로 다시 생성/편집해야 합니다.

## 주의
`output/browser_profile_chatgpt`는 로그인 세션 정보를 포함할 수 있으므로 공유하거나 ZIP에 넣지 마세요. 본 스크립트는 DesignHub 로그인이나 업로드를 수행하지 않습니다.
