"""Comparação simples do histórico dos ativos selecionados."""

import streamlit as st

from investment_agents.integrations.ticker_client import get_history
from investment_agents.ui import render_sidebar


def render() -> None:
    symbols = render_sidebar()
    st.title("Análise de desempenho")
    st.caption("Compare a variação percentual dos ativos no período escolhido.")
    period = st.selectbox("Período de comparação", ["1mo", "3mo", "6mo", "1y", "2y"], index=1)
    if not symbols:
        st.info("Selecione ações na barra lateral para montar a comparação.")
        return

    series: dict[str, dict] = {}
    for symbol in symbols:
        try:
            candles = get_history(symbol, range=period, interval="1d").candles
            if len(candles) > 1 and candles[0].close:
                base = candles[0].close
                series[symbol] = {candle.date: (candle.close / base - 1) * 100 for candle in candles}
        except Exception as error:
            st.warning(f"Não foi possível carregar {symbol}: {error}")

    if series:
        st.line_chart(series, y_label="Variação (%)")
        st.caption("A comparação começa em 0% na primeira cotação disponível do período. Dados históricos não garantem resultados futuros.")
    else:
        st.info("Ainda não há dados suficientes para comparar os ativos.")
