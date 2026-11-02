"""Formatação de valores no padrão brasileiro."""

from __future__ import annotations

from datetime import date

_CURRENCY_SYMBOLS = {"BRL": "R$", "USD": "US$", "EUR": "€", "GBP": "£"}
_COMPACT_UNITS = ((1e9, "bi"), (1e6, "mi"), (1e3, "mil"))


def _number(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_price(value: float, currency: str) -> str:
    code = currency.upper()
    return f"{_CURRENCY_SYMBOLS.get(code, code)} {_number(value)}"


def format_percent(value: float, signed: bool = True) -> str:
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{_number(value)}%"


def format_compact(value: float) -> str:
    for threshold, unit in _COMPACT_UNITS:
        if abs(value) >= threshold:
            return f"{_number(value / threshold, 1)} {unit}"
    return _number(value, 0)


def format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")
