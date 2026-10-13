from datetime import datetime
from types import SimpleNamespace

import core


def test_fmt_ts():
    assert core.fmt_ts(0) == "00:00"
    assert core.fmt_ts(75.9) == "01:15"
    assert core.fmt_ts(3725) == "01:02:05"


def test_build_user_prompt_includes_context_only_when_given():
    p = core.build_user_prompt("[00:00] 안녕", "회의", "  ")
    assert "[추가 맥락]" not in p and core.KINDS["회의"] in p and p.endswith("[00:00] 안녕")
    p = core.build_user_prompt("x", "강의/세미나", "주간회의")
    assert "[추가 맥락]\n주간회의" in p


class FakeModel:
    def transcribe(self, path, **kw):
        segs = [SimpleNamespace(start=0.0, end=2.0, text=" 안녕하세요 "),
                SimpleNamespace(start=2.0, end=3.0, text="  "),
                SimpleNamespace(start=3.0, end=5.5, text="회의를 시작합니다")]
        return iter(segs), SimpleNamespace(duration=6.0)


def test_transcribe_file_strips_and_drops_empty_segments():
    seen = []
    result, info = core.transcribe_file(FakeModel(), "x.wav", "ko", lambda p, t: seen.append((p, t)))
    assert [s["text"] for s in result] == ["안녕하세요", "회의를 시작합니다"]
    assert info.duration == 6.0 and seen[-1] == (5.5, 6.0)
    assert core.stamp(result) == "[00:00] 안녕하세요\n[00:03] 회의를 시작합니다"


class FakeStream:
    text_stream = iter(["## 한 줄 ", "요약"])
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_stream_summary_passes_prompt_and_yields_text():
    calls = {}
    def stream(**kw):
        calls.update(kw)
        return FakeStream()
    client = SimpleNamespace(messages=SimpleNamespace(stream=stream))
    assert "".join(core.stream_summary(client, "[00:00] 안녕", "회의", "")) == "## 한 줄 요약"
    assert calls["model"] == core.CLAUDE_MODEL and calls["system"] == core.SYSTEM_PROMPT
    assert calls["messages"][0]["content"].endswith("[00:00] 안녕")


def test_build_report():
    r = core.build_report("meeting", 65, "## 요약", "[00:00] hi", datetime(2026, 1, 2, 3, 4))
    assert r.startswith("# meeting\n") and "2026-01-02 03:04" in r and "01:05" in r and r.endswith("[00:00] hi\n")


def test_build_chat_prompt_contains_instructions_and_transcript():
    p = core.build_chat_prompt("[00:00] 안녕", "회의", "")
    assert p.startswith(core.SYSTEM_PROMPT) and "## 액션 아이템" in p and p.endswith("[00:00] 안녕")
