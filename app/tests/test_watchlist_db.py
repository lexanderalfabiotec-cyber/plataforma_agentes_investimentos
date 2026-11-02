import pytest

from investment_agents import watchlist_db


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(watchlist_db, "DB_PATH", tmp_path / "nested" / "ativos.db")
    watchlist_db.initialize_database()


def test_add_normalizes_and_keeps_insertion_order():
    assert watchlist_db.add_ticker(" petr4.sa ") is True
    assert watchlist_db.add_ticker("AAPL") is True
    assert watchlist_db.get_tickers() == ["PETR4.SA", "AAPL"]


def test_add_rejects_duplicates_and_blank():
    assert watchlist_db.add_ticker("AAPL") is True
    assert watchlist_db.add_ticker("aapl") is False
    assert watchlist_db.add_ticker("   ") is False
    assert watchlist_db.get_tickers() == ["AAPL"]


def test_delete():
    watchlist_db.add_ticker("AAPL")
    assert watchlist_db.delete_ticker("aapl") is True
    assert watchlist_db.delete_ticker("AAPL") is False
    assert watchlist_db.get_tickers() == []


def test_initialize_is_idempotent_and_keeps_data():
    watchlist_db.add_ticker("AAPL")
    watchlist_db.initialize_database()
    assert watchlist_db.get_tickers() == ["AAPL"]
