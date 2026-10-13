"""전사 · 요약 핵심 로직 (UI와 분리해 테스트 가능하게 유지)"""
from __future__ import annotations

from typing import Callable, Iterator

CLAUDE_MODEL = "claude-sonnet-5-5"

KINDS = {
    "회의": "회의 녹음입니다. 결정사항, 담당자별 액션아이템, 쟁점에 집중하세요.",
    "강의/세미나": "강의 또는 세미나 녹음입니다. 핵심 개념, 구조, 복습용 포인트에 집중하세요.",
    "인터뷰/사용자 리서치": "인터뷰 또는 사용자 리서치 녹음입니다. 응답자의 니즈, 페인포인트, 인상적인 발언, 패턴에 집중하세요.",
    "일반 음성 메모": "일반 음성 메모입니다. 아이디어와 해야 할 일을 정리하는 데 집중하세요.",
}

SYSTEM_PROMPT = """당신은 음성 녹음 전사문을 분석하는 전문 분석가입니다.
전사문은 음성 인식 결과라 오탈자·고유명사 오류·화자 구분 부재가 있을 수 있습니다. 문맥으로 합리적으로 보정하되, 전사문에 없는 내용을 지어내지 마세요.
반드시 한국어 마크다운으로, 아래 구조로 답하세요.

## 한 줄 요약
(1문장)

## 핵심 요약
(5~8개 불릿. 중요한 순서대로)

## 주요 논의 및 결정사항
(주제별로 묶어서 정리. 결정된 것과 미정인 것을 구분)

## 액션 아이템
(할 일 / 담당자(언급된 경우) / 기한(언급된 경우). 없으면 '언급 없음')

## 인사이트
(전사문 이면의 시사점, 반복되는 패턴, 숨은 리스크나 기회, 말하지 않았지만 중요한 것. 3~5개, 각각 근거가 된 발언을 짧게 덧붙이기)

## 열린 질문 / 후속 확인 필요
(불명확하거나 추가 확인이 필요한 항목)
"""


def fmt_ts(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def load_whisper(size: str):
    from faster_whisper import WhisperModel

    return WhisperModel(size, device="auto", compute_type="auto")


def transcribe_file(model, path: str, language: str | None,
                    on_progress: Callable[[float, float], None] | None = None):
    """오디오 파일을 전사해 ([{start, end, text}], info)를 돌려준다."""
    segments, info = model.transcribe(path, language=language, vad_filter=True, beam_size=5)
    result = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            result.append({"start": seg.start, "end": seg.end, "text": text})
        if on_progress:
            on_progress(seg.end, info.duration)
    return result, info


def stamp(segments) -> str:
    return "\n".join(f"[{fmt_ts(s['start'])}] {s['text']}" for s in segments)


def build_user_prompt(transcript: str, kind: str, context: str) -> str:
    user = f"[녹음 유형]\n{KINDS[kind]}\n"
    if context.strip():
        user += f"\n[추가 맥락]\n{context.strip()}\n"
    return user + f"\n[전사문]\n{transcript}"


def build_chat_prompt(transcript: str, kind: str, context: str) -> str:
    """API 키 없이 claude.ai 채팅에 그대로 붙여넣을 수 있는 한 덩어리 프롬프트."""
    return SYSTEM_PROMPT + "\n---\n\n" + build_user_prompt(transcript, kind, context)


def stream_summary(client, transcript: str, kind: str, context: str) -> Iterator[str]:
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(transcript, kind, context)}],
    ) as stream:
        yield from stream.text_stream


def build_report(name: str, duration: float, summary: str, stamped: str, now) -> str:
    return (
        f"# {name}\n\n"
        f"- 분석일: {now:%Y-%m-%d %H:%M}\n"
        f"- 녹음 길이: {fmt_ts(duration)}\n\n"
        f"{summary}\n\n---\n\n## 전사문\n\n{stamped}\n"
    )
