"""Comparação simples do histórico dos ativos selecionados."""

import logging

import requests
import streamlit as st

from investment_agents.integrations.ticker_client import get_history
from investment_agents.ui import render_sidebar, show_backend_unavailable

logger = logging.getLogger(__name__)


def render() -> None:
    symbols = render_sidebar()
    st.title("Análise de desempenho")
    st.caption("Compare a variação percentual dos ativos no período escolhido.")
    period = st.selectbox("Período de comparação", ["1mo", "3mo", "6mo", "1y", "2y"], index=1)
    if not symbols:
        st.info("Selecione ações na barra lateral para montar a comparação.")
        return

    series: dict[str, dict] = {}
    backend_unavailable = False
    for symbol in symbols:
        try:
            candles = get_history(symbol, range=period, interval="1d").candles
            if len(candles) > 1 and candles[0].close:
                base = candles[0].close
                series[symbol] = {candle.date: (candle.close / base - 1) * 100 for candle in candles}
        except Exception as error:
            logger.warning("Falha ao carregar histórico de %s", symbol, exc_info=True)
            if isinstance(error, requests.RequestException):
                backend_unavailable = True
            else:
                st.warning(f"Não foi possível carregar os dados de {symbol}.")

    if backend_unavailable:
        show_backend_unavailable()

    if series:
        st.line_chart(series, y_label="Variação (%)")
        st.caption("A comparação começa em 0% na primeira cotação disponível do período. Dados históricos não garantem resultados futuros.")
    else:
        st.info("Ainda não há dados suficientes para comparar os ativos.")
