from datetime import date

from investment_agents.formatting import format_compact, format_date, format_percent, format_price


def test_format_price_uses_brazilian_separators_and_symbol():
    assert format_price(1234567.891, "BRL") == "R$ 1.234.567,89"
    assert format_price(10, "usd") == "US$ 10,00"
    assert format_price(10, "JPY") == "JPY 10,00"


def test_format_percent_sign():
    assert format_percent(1.5) == "+1,50%"
    assert format_percent(-1.5) == "-1,50%"
    assert format_percent(0) == "0,00%"
    assert format_percent(1.5, signed=False) == "1,50%"


def test_format_compact_units():
    assert format_compact(950) == "950"
    assert format_compact(12_500) == "12,5 mil"
    assert format_compact(3_400_000) == "3,4 mi"
    assert format_compact(2_000_000_000) == "2,0 bi"


def test_format_date():
    assert format_date(date(2026, 10, 30)) == "30/10/2026"
