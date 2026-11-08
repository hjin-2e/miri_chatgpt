# 미리캔버스 macOS v6 — 매일 새로운 Subject 10개 자동 준비

기존 v5.1 파일, 기존 `input/subjects.csv`의 7개 소재, 6개 스타일, 심사 메일 설정은 유지했습니다.

## 핵심 기능

- 매일 오전 9시: `templates/daily_catalog.json`의 20개 카테고리 / 240개 후보 중 **기존에 사용하지 않은 Subject 10개**를 선정합니다.
- 각 항목에 한국어 요소명, 키워드(최대 8개), 6개 스타일 중 하나, 고유 파일명, `pending` 상태를 자동 추가합니다.
- 기존 `input/subjects.csv`의 항목을 삭제하거나 덮어쓰지 않습니다.
- `input/subject_history.csv`에 생성 이력을 누적해 중복을 방지합니다. 같은 날짜에 여러 번 실행해도 새로 추가하지 않습니다.
- 카테고리를 가능한 한 다양하게 섞고 날짜 기반으로 순서를 바꿉니다.
- **중요: 이 기능은 로컬 카탈로그 기반 규칙 생성입니다. ChatGPT/Claude를 무인 호출하거나 새로운 AI 소재를 스스로 발명하지 않습니다.** 카탈로그를 보충하지 않으면 최대 24일(기존 CSV와 중복 시 더 짧을 수 있음) 이후 소재가 부족할 수 있습니다. 부족하면 오류를 기록하고 CSV를 변경하지 않습니다.
- **ChatGPT 내장 이미지 생성은 자동 실행되지 않습니다.** `batch` 명령으로 프롬프트를 만들고 ChatGPT에 붙여넣어 생성/다운로드해야 합니다. DesignHub 로그인/업로드도 자동화되지 않았습니다.

## 처음 설치

압축을 풀고 터미널에서 새 폴더로 이동합니다.

```bash
python3 daily_subject_generator.py --dry-run
python3 daily_subject_generator.py
python3 chatgpt_batch.py list
python3 chatgpt_batch.py batch --limit 10
./install_daily_subjects.sh
```

- `--dry-run`은 CSV를 변경하지 않습니다.
- `python3 daily_subject_generator.py`는 당일 분량을 실제로 추가합니다. 당일 재실행은 중복을 방지합니다.
- `batch`는 **가장 오래된 pending부터** 10개를 선택합니다. 기존 7개가 pending이면 처음 배치에 먼저 포함됩니다.
- 매일 자동 준비 로그: `tail -n 30 output/daily_subjects.log`
- 일일 작업 제거: `./install_daily_subjects.sh uninstall`
- 기존 심사 확인 자동 실행(09:00)은 `install_launchd.sh`로 별도 관리합니다.

## 소재 추가

`templates/daily_catalog.json`에서 카테고리와 `subjects` 배열을 확장할 수 있습니다. 각 항목은 고유 `ko`, 파일명용 영문 소문자/밑줄 `en`, `tags` 배열을 포함해야 합니다. **`ko`가 기존 소재와 동일하면 중복으로 제외됩니다.**

## 운영 주의

- 매일 소재 10개를 추가하므로 이미지 제작보다 소재가 빠르게 쌓일 수 있습니다.
- `input/subjects.csv`, `input/subject_history.csv`, `config.json`은 백업하세요.
- 다른 폴더로 프로그램을 옮기면 LaunchAgent 경로를 새 폴더 기준으로 재설치하세요.
- Gmail 앱 비밀번호는 키체인에만 보관하고 ZIP에 넣지 마세요.
