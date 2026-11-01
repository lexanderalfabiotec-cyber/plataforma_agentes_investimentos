"""Consulta de cotações e histórico do mercado."""

import streamlit as st

from investment_agents.integrations.ticker_client import get_history, get_latest
from investment_agents.ui import format_price, render_sidebar


def render() -> None:
    symbols = render_sidebar()
    st.title("Mercado")
    st.caption("Cotações e histórico fornecidos pelo backend de mercado.")
    if not symbols:
        st.info("Selecione ao menos uma ação na barra lateral.")
        return

    symbol = st.selectbox("Ativo", symbols)
    period = st.selectbox("Período", ["5d", "1mo", "3mo", "6mo", "1y", "2y"], index=1)
    try:
        latest = get_latest(symbol)
        candle = latest.candle
        st.metric(symbol, format_price(candle.close, latest.currency), f"Abertura {format_price(candle.open, latest.currency)}")
        history = get_history(symbol, range=period, interval="1d")
        if history.candles:
            st.subheader(f"Histórico — {period}")
            st.line_chart({"Fechamento": {item.date: item.close for item in history.candles}})
            st.dataframe(
                [{"Data": item.date, "Abertura": item.open, "Máxima": item.high, "Mínima": item.low, "Fechamento": item.close, "Volume": item.volume} for item in history.candles],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("O backend não retornou candles para esse período.")
    except Exception as error:
        st.error(f"Não foi possível consultar {symbol}. Verifique se o backend Go está disponível. Detalhes: {error}")
