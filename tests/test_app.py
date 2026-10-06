from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parents[1]


def test_app_initial_render_and_synthetic_investigation(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "disabled")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert any(t.value == "Research with receipts." for t in app.title)
    next(button for button in app.button if button.label == "Try synthetic example").click().run()
    assert not app.exception
    assert len(app.session_state["critic_results"]) >= 6
    assert any(result.verdict.value == "CONTRADICTED" for result in app.session_state["critic_results"])
    assert any(m.label == "Contradicted" and int(m.value) >= 2 for m in app.metric)
    next(button for button in app.button if button.label == "Clear session results").click().run()
    assert not app.exception
    assert "document" not in app.session_state


def test_app_empty_search_validation():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    next(button for button in app.button if button.label == "Start Investigation").click().run()
    assert not app.exception
    assert any("research topic" in item.value.lower() for item in app.error)
