# v6.2 — 오전 9시 소재 생성

- `install_daily_subjects.sh`: 매일 오전 9시 새 Subject 10개와 키워드 생성
- `install_launchd.sh`: 매일 오전 9시 심사 메일 확인 (별도 작업)
- 두 작업은 같은 시각에 시작할 수 있습니다.
- ChatGPT 이미지 생성과 다운로드는 여전히 직접 진행해야 합니다.

## 설치
```bash
chmod +x install_daily_subjects.sh install_launchd.sh
./install_daily_subjects.sh
./install_launchd.sh
```

기존 설치가 있으면 동일한 launchd 라벨을 다시 설치해 경로와 시간을 갱신합니다.

## 수동 시험
```bash
python3 daily_subject_generator.py --dry-run
python3 image_workflow.py prepare
```

## 주의
기존 `subjects.csv` 및 생성 이력을 덮어쓰지 않도록 현재 사용 중인 파일은 별도로 백업한 후 옮기세요. 자동 생성은 등록된 후보 목록을 활용하는 규칙 기반 방식입니다.
