import pytest
from streamlit import config

from investment_agents import theme, watchlist_db


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(watchlist_db, "DB_PATH", tmp_path / "ativos.db")
    watchlist_db.initialize_database()
    original = config.get_option("theme.base")
    yield
    config.set_option("theme.base", original)


def test_sync_applies_saved_theme_only_when_different():
    config.set_option("theme.base", "light")
    watchlist_db.set_preference("tema", "dark")
    assert theme.sync_saved_theme() is True
    assert theme.theme_type() == "dark"
    assert theme.sync_saved_theme() is False


def test_sync_without_saved_theme_keeps_default():
    config.set_option("theme.base", "light")
    assert theme.sync_saved_theme() is False
    assert theme.theme_type() == "light"


def test_sync_ignores_invalid_value():
    config.set_option("theme.base", "light")
    watchlist_db.set_preference("tema", "rosa")
    assert theme.sync_saved_theme() is False
    assert theme.theme_type() == "light"


def test_first_run_after_restart_applies_saved_theme():
    from streamlit.testing.v1 import AppTest

    def app():
        from investment_agents.theme import render_theme_toggle

        render_theme_toggle()

    config.set_option("theme.base", "light")
    watchlist_db.set_preference("tema", "dark")
    at = AppTest.from_function(app).run()
    assert not at.exception
    assert config.get_option("theme.base") == "dark"
    assert at.session_state["theme_selector"] == "dark"


def test_app_toggle_switches_saves_and_survives_active_option_click(monkeypatch):
    from streamlit.testing.v1 import AppTest

    def app():
        from investment_agents.theme import render_theme_toggle

        render_theme_toggle()

    config.set_option("theme.base", "light")
    at = AppTest.from_function(app).run()
    assert at.session_state["theme_selector"] == "light"

    at.button_group[0].set_value(["dark"]).run()
    assert not at.exception
    assert config.get_option("theme.base") == "dark"
    assert watchlist_db.get_preference("tema") == "dark"

    # Clicar de novo na opção ativa não pode deixar o seletor vazio.
    at.button_group[0].set_value([]).run()
    assert not at.exception
    assert config.get_option("theme.base") == "dark"
    assert at.session_state["theme_selector"] == "dark"
