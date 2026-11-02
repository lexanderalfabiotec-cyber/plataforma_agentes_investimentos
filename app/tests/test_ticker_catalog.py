from investment_agents.services.ticker_catalog import (
    TickerOption,
    company_name,
    load_ticker_catalog,
    resolve_ticker,
)

CATALOG = (TickerOption(papel="PETR4", nome="Petrobras", yahoo_ticker="PETR4.SA"),)


def test_resolve_maps_b3_code_to_yahoo_ticker():
    assert resolve_ticker(" petr4 ", CATALOG) == "PETR4.SA"


def test_resolve_keeps_tickers_outside_catalog():
    assert resolve_ticker("aapl", CATALOG) == "AAPL"
    assert resolve_ticker("PETR4.SA", CATALOG) == "PETR4.SA"


def test_company_name():
    assert company_name("PETR4.SA", CATALOG) == "Petrobras"
    assert company_name("AAPL", CATALOG) == ""


def test_load_catalog_reads_project_csv_and_caches():
    catalog = load_ticker_catalog()
    assert len(catalog) > 1000
    assert load_ticker_catalog() is catalog


def test_load_catalog_missing_file(tmp_path):
    assert load_ticker_catalog(tmp_path / "nao_existe.csv") == ()
