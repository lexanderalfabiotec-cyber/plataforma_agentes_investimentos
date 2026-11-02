"""Comparação do desempenho dos ativos selecionados."""

import streamlit as st

from investment_agents.charts import MAX_COMPARED_SERIES, comparison_chart
from investment_agents.services.market_data import fetch_histories, performance_stats
from investment_agents.theme import theme_type
from investment_agents.ui import (
    render_no_selection,
    render_sidebar,
    select_period,
    show_fetch_issues,
)
from investment_agents.watchlist_db import get_tickers


def _render_ranking(histories: dict) -> None:
    rows = []
    for symbol, history in histories.items():
        stats = performance_stats(history.candles)
        if stats is not None:
            rows.append(
                {
                    "Ativo": symbol,
                    "Retorno": stats.total_return / 100,
                    "Volatilidade anual": None
                    if stats.annual_volatility is None
                    else stats.annual_volatility / 100,
                    "Maior queda": stats.max_drawdown / 100,
                }
            )
    rows.sort(key=lambda row: row["Retorno"], reverse=True)
    percent = st.column_config.NumberColumn(format="percent")
    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        column_config={
            "Retorno": percent,
            "Volatilidade anual": st.column_config.NumberColumn(
                format="percent", help="Oscilação dos retornos diários, anualizada."
            ),
            "Maior queda": st.column_config.NumberColumn(
                format="percent", help="Maior recuo a partir de um pico dentro do período."
            ),
        },
    )


def render() -> None:
    symbols = render_sidebar()
    st.title("Análise de desempenho")
    if not symbols:
        render_no_selection()
        return

    period = select_period(["1mo", "3mo", "6mo", "1y", "2y"], default="3mo", page="analise")
    with st.spinner("Calculando desempenho..."):
        batch = fetch_histories(symbols, period=period)
    show_fetch_issues(batch)

    comparable = {
        symbol: history
        for symbol, history in batch.histories.items()
        if len(history.candles) > 1 and history.candles[0].close
    }
    if not comparable:
        if not (batch.service_unavailable or batch.provider_failed or batch.not_found):
            st.info("Ainda não há dados suficientes para comparar os ativos.")
        return

    charted = dict(list(comparable.items())[:MAX_COMPARED_SERIES])
    if len(comparable) > len(charted):
        st.info(
            f"O gráfico mostra os {MAX_COMPARED_SERIES} primeiros ativos para continuar legível; "
            "a tabela abaixo inclui todos."
        )
    # A cor segue a posição do ativo na lista salva, para não mudar quando outro
    # ativo é desmarcado. Listas maiores que a paleta usam a ordem do gráfico.
    registered = get_tickers()
    color_order = registered if len(registered) <= MAX_COMPARED_SERIES else list(charted)
    series = {symbol: history.candles for symbol, history in charted.items()}
    st.altair_chart(comparison_chart(series, color_order, theme_type()), width="stretch")

    _render_ranking(comparable)
    st.caption(
        "A comparação parte de 0% na primeira cotação do período, na moeda de cada ativo. "
        "Dados históricos não garantem resultados futuros."
    )
