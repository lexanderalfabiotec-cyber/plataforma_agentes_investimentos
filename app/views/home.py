"""Painel inicial com resumo dos ativos selecionados."""

import streamlit as st

from investment_agents.formatting import format_date, format_percent, format_price
from investment_agents.services.market_data import day_change, fetch_histories
from investment_agents.services.ticker_catalog import company_name
from investment_agents.ui import render_no_selection, render_sidebar, show_fetch_issues

COLUMNS_PER_ROW = 4


def render() -> None:
    symbols = render_sidebar()
    st.title("Visão geral")
    if not symbols:
        render_no_selection()
        return

    with st.spinner("Carregando cotações..."):
        batch = fetch_histories(symbols, period="1mo")

    changes = {symbol: day_change(history.candles) for symbol, history in batch.histories.items()}
    known = [change for change in changes.values() if change is not None]
    if known:
        rising = sum(change > 0 for change in known)
        falling = sum(change < 0 for change in known)
        total = len(batch.histories)
        st.caption(
            f"{total} {'ativo' if total == 1 else 'ativos'} · {rising} em alta · "
            f"{falling} em queda no último pregão"
        )

    show_fetch_issues(batch)

    columns = st.columns(COLUMNS_PER_ROW)
    for index, (symbol, history) in enumerate(batch.histories.items()):
        if not history.candles:
            continue
        last = history.candles[-1]
        change = changes[symbol]
        with columns[index % COLUMNS_PER_ROW]:
            st.metric(
                symbol,
                format_price(last.close, history.currency),
                f"{format_percent(change)} no dia" if change is not None else None,
                chart_data=[candle.close for candle in history.candles],
                chart_type="line",
                border=True,
                help=company_name(symbol) or None,
            )
            st.caption(
                f"Mín. {format_price(last.low, history.currency)} · "
                f"Máx. {format_price(last.high, history.currency)} · {format_date(last.date.date())}"
            )
