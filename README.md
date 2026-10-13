# 🎙️ 음성 → 전사 · 요약 · 인사이트

음성 녹음 파일을 올리면 전사문을 만들고, Claude가 요약·액션아이템·인사이트를 정리해주는 웹 앱입니다.

## 구성

- **전사**: `faster-whisper` (앱이 실행되는 서버에서 처리, 오디오는 Claude로 보내지 않음)
- **요약·인사이트**: Claude API (전사 텍스트만 전송)
- **UI**: Streamlit

## 웹에 배포하기 (Streamlit Community Cloud, 무료)

1. https://share.streamlit.io 에 GitHub 계정으로 로그인합니다.
2. **Create app → Deploy a public app from GitHub**를 고릅니다.
   - Repository: `yuna0102/audio-to-text-extension`
   - Branch: 이 코드가 있는 브랜치
   - Main file path: `app.py`
3. **Advanced settings**에서 Python `3.12`를 고릅니다.
4. **Deploy**를 누르면 `https://<이름>.streamlit.app` 주소가 생깁니다.

API 키 없이도 동작합니다. 이때는 전사만 하고, 요약 탭에 claude.ai 새 채팅에 그대로 붙여넣을 프롬프트를 보여줍니다.
나중에 자동 요약을 켜려면 앱 설정 → Secrets에 아래를 넣으세요 (`.streamlit/secrets.toml.example` 참고).

```toml
ANTHROPIC_API_KEY = "sk-ant-..."   # https://console.anthropic.com → API Keys
APP_PASSWORD = "원하는-비밀번호"     # 선택. 공개 URL에서 내 API 키를 남이 쓰지 못하게 막음
```

> 무료 서버는 CPU만 있고 메모리가 작습니다. 전사 모델은 `small`(기본)을 권장하고, `medium` 이상은 메모리 부족으로 앱이 재시작될 수 있습니다. 첫 분석 때는 모델 다운로드로 1~2분이 더 걸립니다.

## 로컬에서 실행

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # 또는 앱 사이드바에 직접 입력
streamlit run app.py
```

브라우저에서 `http://localhost:8501`이 열립니다. 오디오 디코딩은 faster-whisper에 포함된 PyAV가 처리하므로 ffmpeg를 따로 설치하지 않아도 됩니다.

## 사용법

1. 사이드바에서 녹음 언어, 전사 모델, 녹음 유형(회의 / 강의 / 인터뷰 / 메모)을 선택합니다.
2. 필요하면 "추가 맥락"에 배경을 적어줍니다. (예: 하우미 주간회의, 참석자 3명)
3. 파일(mp3, m4a, wav, mp4, webm 등, 최대 200MB)을 올리고 **분석 시작**을 누릅니다.
4. 결과는 두 탭에서 확인합니다.
   - **요약 · 인사이트**: 한 줄 요약, 핵심 요약, 논의/결정사항, 액션아이템, 인사이트, 열린 질문
   - **전사문**: 타임스탬프 포함 전체 텍스트
5. 전체 리포트(.md) 또는 전사문(.txt)으로 다운로드합니다.

## API 키

- 키가 없으면 전사 + claude.ai용 요약 프롬프트를 제공합니다.
- 서버에 `ANTHROPIC_API_KEY`(환경변수 또는 Streamlit Secrets)를 설정하면 사용자는 키 없이 쓸 수 있습니다. 서버 키는 브라우저로 전달되지 않습니다.
- 사이드바에 키를 입력하면 그 키가 우선 사용됩니다.

## 테스트

```bash
pip install -r requirements-dev.txt
pytest -q tests
```

GitHub Actions(`.github/workflows/e2e.yml`)는 푸시할 때마다 다음을 실행합니다.

1. 단위 테스트와 앱 렌더링 테스트를 돌립니다.
2. TTS로 한국어(m4a)와 영어(mp3) 테스트 녹음을 만듭니다.
3. 실제 브라우저에서 업로드 → 전사 → 요약 흐름을 검증합니다.

결과 스크린샷과 전사문은 실행 결과의 `e2e-results` 아티팩트에 들어 있습니다. 저장소 Secrets에 `ANTHROPIC_API_KEY`를 넣으면 요약 단계까지 실제로 검증합니다.

## 팁

- 요약 모델은 `core.py`의 `CLAUDE_MODEL`, 요약 형식은 `SYSTEM_PROMPT`에서 바꿀 수 있습니다.
- GPU가 있는 서버라면 `large-v3`가 가장 정확합니다.

## 한계

- 화자 분리(누가 말했는지)는 지원하지 않습니다. 필요하면 `pyannote.audio` 연동을 추가할 수 있습니다.
- 매우 긴 녹음(수 시간)은 CPU 서버에서 전사 시간이 오래 걸립니다.
