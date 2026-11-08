# 미리캔버스 ChatGPT 브라우저 자동화 v7 (실험판)

## 중요: 아직 실제 Chrome에서 검증되지 않았습니다
이 프로그램은 화면 좌표나 수동 다운로드 클릭을 요구하지 않도록 설계한 **첫 구현**입니다. ChatGPT DOM 구조와 생성 이미지 URL 형태가 바뀌면 작동하지 않을 수 있습니다. ChatGPT Plus 웹 UI에는 공식 자동 생성/다운로드 API가 제공된다는 보장이 없습니다. 추가 API 비용은 사용하지 않습니다.

## 설치
1. ZIP을 풀고 `auto_server.py`와 `extension/` 폴더를 기존 `miri_chatgpt` 프로젝트 폴더에 복사합니다. 기존 파일은 덮어쓰지 않습니다.
2. `python3 -m pip install Pillow` (이미 설치돼 있으면 생략)
3. Chrome 주소창 `chrome://extensions` → **개발자 모드** → **압축해제된 확장 프로그램 로드** → `miri_chatgpt/extension` 폴더 선택. 해당 확장 프로그램의 chatgpt.com 및 로컬 서버 접근 권한을 확인합니다.
4. Chrome 설정의 기본 다운로드 폴더가 `~/Downloads`인지 확인하고, **다운로드 전에 각 파일의 저장 위치 확인** 옵션을 끕니다. (최초 설정만 필요)
5. 기존 로그인된 ChatGPT 대화 탭을 새로고침합니다.

## 실행
프로젝트 폴더에서:

```bash
python3 auto_server.py --preflight
```

Chrome ChatGPT 탭에서 확장 프로그램 아이콘 → **자동 실행 시작**을 한 번 누릅니다. 이는 최초 실행 트리거이며 개별 이미지 다운로드 클릭은 필요하지 않습니다.

## 저장 경로
확장 프로그램은 `~/Downloads/miri_auto_inbox/파일명.png`로 저장을 요청합니다. Python은 해당 PNG를 검증한 뒤 `output/images/`로 복사하고 기존 `png_preflight.py`로 `output/upload_ready/`를 갱신합니다.

## 실패 시 확인
- 서버 상태: `http://127.0.0.1:8765/status`
- Chrome 확장 프로그램 관리 → 서비스 워커 오류 확인
- ChatGPT 탭 개발자 도구 Console의 `[Miri Auto]` 오류 확인
- 생성 이미지가 `blob:` URL로 제공되면 안전하게 실패합니다. 이 경우 확장 프로그램의 다운로드 처리 부분을 추가로 조정해야 합니다.
- 서버를 재시작하면 메모리 큐가 초기화됩니다. 이미 저장된 이미지는 다시 작업하지 않습니다. 진행 중 실패한 항목은 수동 재시작 전에 상태를 확인하세요.

## 주의
이 버전은 실험판입니다. 이미지 생성 완료 감지와 브라우저 다운로드가 실제로 성공했다고 보장하지 않습니다. 다른 탭이나 브라우저 UI에 대한 좌표 클릭은 수행하지 않습니다. 미리캔버스 DesignHub 자동 업로드는 포함하지 않습니다.
