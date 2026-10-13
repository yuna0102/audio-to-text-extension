"""음성 녹음 → 전사문 → 요약 · 인사이트 (Streamlit 앱)

실행:  streamlit run app.py
"""
import os
import tempfile
from datetime import datetime

import anthropic
import streamlit as st

from core import KINDS, build_chat_prompt, build_report, fmt_ts, load_whisper, stamp, stream_summary, transcribe_file

AUDIO_TYPES = ["mp3", "m4a", "wav", "mp4", "webm", "ogg", "flac", "aac"]
LANGUAGES = {"한국어": "ko", "English": "en", "日本語": "ja", "中文": "zh", "자동 감지": None}
MODEL_SIZES = {
    "base (가장 빠름, 낮은 정확도)": "base",
    "small (빠름, 보통 정확도)": "small",
    "medium (균형, 메모리 많이 사용)": "medium",
    "large-v3 (느림, 가장 정확)": "large-v3",
}


def secret(name: str) -> str:
    """환경변수 → Streamlit secrets 순으로 찾는다. 없으면 빈 문자열."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        return str(st.secrets.get(name, ""))
    except Exception:  # secrets.toml이 없으면 예외가 난다
        return ""


@st.cache_resource(show_spinner="Whisper 모델 로딩 중... (처음 한 번은 다운로드 시간이 걸립니다)")
def cached_whisper(size: str):
    return load_whisper(size)


def transcribe(uploaded, model_size: str, language):
    suffix = os.path.splitext(uploaded.name)[1] or ".audio"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        path = tmp.name
    try:
        model = cached_whisper(model_size)
        bar = st.progress(0.0, text="전사 중...")

        def on_progress(pos, total):
            total = max(total, 1)
            bar.progress(min(pos / total, 1.0), text=f"전사 중... {fmt_ts(pos)} / {fmt_ts(total)}")

        result, info = transcribe_file(model, path, language, on_progress)
        bar.empty()
        return result, info.duration
    finally:
        os.unlink(path)


# ───────────────────────── UI ─────────────────────────
st.set_page_config(page_title="음성 → 전사 · 요약 · 인사이트", page_icon="🎙️", layout="wide")

# 배포 시 APP_PASSWORD를 설정하면 비밀번호를 아는 사람만 사용할 수 있다 (서버 API 키 남용 방지).
app_password = secret("APP_PASSWORD")
if app_password and not st.session_state.get("authed"):
    st.title("🎙️ 음성 → 전사 · 요약 · 인사이트")
    pw = st.text_input("비밀번호", type="password")
    if pw:
        if pw == app_password:
            st.session_state["authed"] = True
            st.rerun()
        st.error("비밀번호가 틀렸습니다.")
    st.stop()

st.title("🎙️ 음성 → 전사 · 요약 · 인사이트")
st.caption("녹음 파일을 올리면 전사문을 만들고, Claude가 요약과 인사이트를 정리해줍니다.")

server_key = secret("ANTHROPIC_API_KEY")

with st.sidebar:
    st.header("설정")
    # 서버 키는 브라우저로 내려보내지 않는다. 입력란은 개인 키를 쓰고 싶을 때만.
    user_key = st.text_input(
        "Anthropic API Key (선택)",
        type="password",
        help="서버에 키가 설정돼 있으면 비워둬도 됩니다." if server_key
        else "없으면 전사만 하고, claude.ai에 붙여넣을 요약 프롬프트를 만들어줍니다.",
    )
    lang_label = st.selectbox("녹음 언어", list(LANGUAGES), index=0)
    size_label = st.selectbox("전사 모델", list(MODEL_SIZES), index=1)
    kind = st.selectbox("녹음 유형", list(KINDS))
    context = st.text_area("추가 맥락 (선택)", placeholder="예: 하우미 커머스 기능 주간회의, 참석자 3명")

api_key = user_key.strip() or server_key

uploaded = st.file_uploader("음성/영상 파일 업로드", type=AUDIO_TYPES)

if uploaded:
    st.audio(uploaded)

if not api_key:
    st.info("API 키 없이 사용 중입니다. 전사는 그대로 되고, 요약은 claude.ai에 붙여넣을 프롬프트로 제공됩니다.")

if st.button("분석 시작", type="primary", disabled=uploaded is None):
    try:
        segments, duration = transcribe(uploaded, MODEL_SIZES[size_label], LANGUAGES[lang_label])
    except Exception as e:  # 손상된 파일, 지원하지 않는 코덱 등
        st.error(f"전사 중 오류가 발생했습니다: {e}")
        st.stop()
    if not segments:
        st.warning("인식된 음성이 없습니다. 파일이나 언어 설정을 확인해주세요.")
        st.stop()

    st.session_state["name"] = uploaded.name
    st.session_state["stamped"] = stamp(segments)
    st.session_state["duration"] = duration
    st.session_state["chat_prompt"] = build_chat_prompt(st.session_state["stamped"], kind, context)
    st.session_state["summary"] = ""

    # 스트리밍 중에만 보여주고, 끝나면 아래 탭에서 한 번만 보이도록 지운다.
    if api_key:
        live = st.empty()
        try:
            with live.container():
                st.subheader("요약 · 인사이트 (생성 중)")
                client = anthropic.Anthropic(api_key=api_key)
                st.session_state["summary"] = st.write_stream(
                    stream_summary(client, st.session_state["stamped"], kind, context)
                )
            live.empty()
        except anthropic.AuthenticationError:
            live.empty()
            st.error("Anthropic API 키가 올바르지 않습니다. 키를 확인해주세요. (전사문은 아래에서 확인할 수 있습니다)")
        except anthropic.APIError as e:
            live.empty()
            st.error(f"요약 중 오류가 발생했습니다: {e}")

if "stamped" in st.session_state:
    summary = st.session_state.get("summary", "")
    tab1, tab2 = st.tabs(["📝 요약 · 인사이트", "📄 전사문"])
    with tab1:
        if summary:
            st.markdown(summary)
        else:
            st.info(
                "자동 요약이 없습니다. 아래 프롬프트를 복사(오른쪽 위 복사 아이콘)해서 "
                "[claude.ai](https://claude.ai) 새 채팅에 붙여넣으면 같은 형식의 요약 · 인사이트를 받을 수 있습니다."
            )
            st.code(st.session_state["chat_prompt"], language=None, wrap_lines=True, height=300)
    with tab2:
        st.text_area("타임스탬프 포함", st.session_state["stamped"], height=400)

    stem = os.path.splitext(st.session_state["name"])[0]
    report = build_report(stem, st.session_state["duration"], summary, st.session_state["stamped"], datetime.now())
    c1, c2 = st.columns(2)
    c1.download_button("전체 리포트 (.md)", report, file_name=f"{stem}_report.md", mime="text/markdown")
    c2.download_button("전사문만 (.txt)", st.session_state["stamped"], file_name=f"{stem}_transcript.txt")
