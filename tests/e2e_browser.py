"""실제 브라우저로 앱을 조작하는 E2E 검증.

사용: python tests/e2e_browser.py <오디오파일> <언어라벨> <스크린샷경로>
앱은 http://localhost:8501 에서 이미 실행 중이어야 한다.
"""
import os
import sys

from playwright.sync_api import sync_playwright

audio, lang, shot = sys.argv[1], sys.argv[2], sys.argv[3]

with sync_playwright() as p:
    page = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH")).new_page(viewport={"width": 1400, "height": 1000})
    page.goto("http://localhost:8501")
    page.get_by_text("분석 시작").wait_for(timeout=60_000)

    if lang != "한국어":
        page.locator("[data-testid='stSidebar'] [data-testid='stSelectbox'] div[role='combobox'], [data-testid='stSidebar'] [data-testid='stSelectbox'] input").first.click()
        page.get_by_role("option", name=lang).click()

    page.locator("input[type='file']").set_input_files(audio)
    page.locator("audio").wait_for(timeout=30_000)
    page.get_by_role("button", name="분석 시작").click()

    # 모델 다운로드 + 전사 + 요약까지 넉넉히 기다린다
    page.get_by_role("tab", name="📄 전사문").wait_for(timeout=600_000)
    page.wait_for_timeout(1000)

    errors = [e.inner_text() for e in page.locator("[data-testid='stAlertContentError']").all()]
    summary = page.locator("[data-testid='stTabs'] [data-testid='stMarkdown']").all_inner_texts()
    page.screenshot(path=shot, full_page=True)

    page.get_by_role("tab", name="📄 전사문").click()
    transcript = page.locator("textarea").last.input_value()

    print("=== TRANSCRIPT ===\n" + transcript)
    print("=== SUMMARY ===\n" + "\n".join(summary))
    print("=== ERRORS ===\n" + "\n".join(errors))
    assert transcript.strip(), "전사문이 비어 있음"
