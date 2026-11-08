# v6.1 — ChatGPT 이미지 생성·저장 연결 (API 미사용)

이 버전은 기존 v6의 Subject 자동 생성, 6개 스타일, Gmail 심사 알림 코드를 유지합니다.

## 실제 가능한 범위

- `image_workflow.py prepare`: 다음 pending 소재 **하나**의 프롬프트를 만들고 Mac 클립보드에 복사합니다.
- 사용자가 ChatGPT 이미지 생성 화면에 붙여넣고 이미지 1개를 생성해 다운로드합니다.
- `image_workflow.py import`: 사용자가 다운로드한 PNG를 **명시한 CSV 파일명**에 안전하게 복사하고, 실제 투명 픽셀이 있는 경우 `generated`로 변경합니다.
- `png_preflight.py`: 해상도/투명도/DPI/용량 검사 및 업로드 준비 파일 생성. 통과해도 시각 검수는 필수입니다.

**ChatGPT 웹 UI 자동 입력/생성/다운로드는 구현되지 않았습니다.** 공식 API 없이 완전 무인 이미지 생성을 보장하지 않습니다. 브라우저 자동 조작은 계정 보안·서비스 제한·UI 변경에 영향을 받을 수 있어 포함하지 않았습니다.

## 사용 방법 (Mac 터미널)

```bash
python3 -m pip install Pillow
python3 daily_subject_generator.py  # 당일 소재가 아직 없을 때
python3 image_workflow.py prepare
```

ChatGPT 대화창에 붙여넣고 **이미지 한 개**를 생성하여 다운로드하세요. 터미널에서 다음과 같이 연결합니다.

```bash
python3 image_workflow.py import --source "$HOME/Downloads/ChatGPT_Image.png" --filename "subjects.csv에_있는_파일명.png"
python3 png_preflight.py --copy-ready
python3 image_workflow.py prepare  # 다음 소재
```

CSV 파일명은 `python3 chatgpt_batch.py list`로 확인합니다. 실제 다운로드 이름은 Mac에 저장된 파일명에 맞게 변경하세요. 자동으로 가장 최근 다운로드를 가져오지 않는 이유는 다른 이미지와 잘못 매칭되는 사고를 방지하기 위해서입니다. 원본 다운로드는 삭제하지 않습니다. 대상 파일이 이미 있으면 덮어쓰지 않습니다.

실제 투명 픽셀이 없으면 PNG는 복사되지만 CSV는 `pending`으로 유지됩니다. 배경 제거 후 이미 존재하는 output/images 파일을 먼저 별도 보관하거나 삭제하고 다시 import해야 합니다. `generated`가 되어도 크기·DPI 등 기준을 통과했다는 뜻은 아닙니다.

## 자동화 범위

매일 오전 9시 소재 10개 자동 준비는 기존 v6 스크립트에서 계속 담당합니다. 이미지 생성 자체는 ChatGPT 웹에서 사용자가 실행합니다. 미리캔버스 DesignHub 자동 업로드도 아직 구현되지 않았습니다. 기존 Gmail 심사 확인은 제출 상태가 없으면 확인을 건너뛸 수 있습니다.

기존 Mac 폴더를 덮어쓰기 전 `input/subjects.csv`, `input/subject_history.csv`, `output/state.json`, `config.json`을 백업하고, launchd 스크립트를 새 경로에서 재설치하세요. **앱 비밀번호는 ZIP에 포함하지 않습니다.**
