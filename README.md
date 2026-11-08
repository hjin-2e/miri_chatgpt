# MIRI ChatGPT — automation pipeline

미리캔버스 DesignHub용 **이미지 제작 작업·검수·메타데이터 자동화 코드** 전용 저장소입니다.

## 저장소 역할

- [hjin-Portfolio](https://github.com/hjin-2e/hjin-Portfolio): 포트폴리오와 `/miri/` 대시보드(표시/UI)
- **miri_chatgpt**: 작업 데이터, CSV 파싱, PNG 검수, 상태 JSON 생성, 실행 스크립트, 예약 워크플로(처리/백엔드)

> 주의: GitHub Actions와 ChatGPT Plus 웹 구독만으로 무인 이미지 생성을 보장할 수 없습니다. 현재는 작업 데이터 및 기존 PNG 파일 검수 파이프라인만 구현 대상으로 둡니다. Gmail/ChatGPT 세션 자동 로그인을 시도하거나 토큰을 저장하지 않습니다.

## 권장 구조

```text
miri_chatgpt/
├── README.md
├── .gitignore
├── input/
│   └── subjects.csv
├── scripts/
│   ├── prepare_jobs.py
│   ├── png_preflight.py
│   └── export_dashboard.py
├── output/                   # gitignore, 로컬 결과
│   ├── images/
│   ├── upload_ready/
│   └── review/
├── data/
│   └── status.json           # 공개용, 개인정보 제외
└── .github/
    └── workflows/
        └── preflight.yml     # 추후 연결
```

## 현재 진행 상태

- [x] 자동화 전용 저장소 역할 확정
- [ ] 기존 로컬 `image_workflow.py`, `png_preflight.py`, `download_bridge.py`, `auto_download.py` 코드 검토 후 안전하게 이관
- [ ] PNG 투명도·해상도 자동 검수 및 메타데이터 출력
- [ ] GitHub Actions 예약 실행과 대시보드 데이터 연결
- [ ] 실제 이미지 생성 엔진 연결 (추가 API 비용 없이 무인 생성은 미해결)

## 로컬 기존 작업물 올리기

먼저 이 저장소를 clone하고, 기존 로컬 프로젝트의 **스크립트와 예제 데이터만 검토해 옮기세요.** 세션 쿠키, 브라우저 프로필, 계정 정보, 인증 토큰, 미공개 개인 파일은 올리지 마세요.

```bash
cd ~/Desktop/Study
git clone https://github.com/hjin-2e/miri_chatgpt.git
cd miri_chatgpt
git status
```

## 보안

이 저장소는 **공개(public)** 상태입니다. API 키, Gmail OAuth 토큰, ChatGPT 세션/쿠키, 민감한 이메일 내용은 커밋하지 마세요. DesignHub 업로드 자동화와 심사 상태 데이터는 실제 구현 및 승인된 접근 범위를 확인한 뒤 추가합니다.
