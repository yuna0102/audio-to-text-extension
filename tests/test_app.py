from streamlit.testing.v1 import AppTest


def test_app_renders(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    at = AppTest.from_file("../app.py").run(timeout=30)
    assert not at.exception
    assert at.button[0].label == "분석 시작" and at.button[0].disabled


def test_password_gate(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "pw123")
    at = AppTest.from_file("../app.py").run(timeout=30)
    assert not at.exception and len(at.button) == 0
    at.text_input[0].input("wrong").run()
    assert at.error[0].value == "비밀번호가 틀렸습니다."
    at.text_input[0].input("pw123").run()
    assert not at.exception and at.button[0].label == "분석 시작"


def test_server_key_is_not_sent_to_browser(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret")
    at = AppTest.from_file("../app.py").run(timeout=30)
    assert at.sidebar.text_input[0].value == ""
