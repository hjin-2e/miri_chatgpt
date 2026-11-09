# 기존 자동화 통합 1단계

## 확인 결과
- `backup/local-work`는 로컬 `git init`에서 만들어져 `main`과 **공통 조상이 없습니다**. 단순 GitHub PR 병합을 바로 진행하지 않습니다.
- 기존 `input/subjects.csv`는 `subject,template_id,filename,status,element_name,keywords,...` 스키마입니다.
- `main`의 신규 `scripts/preflight.py`는 다른 CSV 스키마(`fileName,elementName,style`)를 기대합니다.
- 기존 `png_preflight.py`는 PNG 품질 검사와 업로드 메타데이터 CSV까지 지원합니다. **기존 검수기를 우선 유지**합니다.
- `chatgpt_batch.py`는 프롬프트 준비 도구이며 이미지 API를 호출하지 않습니다.
- `review_watcher.py`는 로컬 IMAP 메일 검사 코드입니다. 실제 실행 및 계정 연동은 검증되지 않았습니다.

## 이번 단계
- 원본 백업 브랜치를 보존하고 별도 `feature/integrate-automation` 브랜치를 생성했습니다.
- Pillow 의존성 파일과 검수 워크플로를 추가했습니다.
- 로컬 원본 이미지, 로그인 정보, `config.json`을 GitHub에 올리지 않습니다.

## 다음 단계
1. 기존 코드의 로컬 실행 테스트 및 안전성 검토
2. `input/subjects.csv`를 유지하는 상태 JSON 내보내기 도구 구현
3. 대시보드 저장소로 공개 가능한 상태 데이터만 전달
4. 이미지 생성은 ChatGPT Plus 수동 승인 경로와 별도 API 경로를 구분
5. DesignHub 등록은 공식 지원 방식과 인증 절차 확인 후 연결

## 로컬 실행
```bash
git fetch origin
git switch feature/integrate-automation
python3 -m pip install -r requirements.txt
python3 png_preflight.py
```
실제 PNG 파일이 없으면 검수 보고서에 누락으로 표시될 수 있습니다.
