"""Análise técnica de uma ação acompanhada."""

import logging

import requests
import streamlit as st

from investment_agents.ui import render_sidebar, show_backend_unavailable
from investment_agents.agents.specialist_agent import get_specialist_advice
from investment_agents.services.technical_analysis import analyze_ticker, compact_analysis

logger = logging.getLogger(__name__)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_analysis(symbol: str):
    return analyze_ticker(symbol)


def render() -> None:
    symbols = render_sidebar()
    st.title("Especialista em Investimentos")
    st.caption("Indicadores calculados localmente; o modelo recebe apenas um resumo compacto.")
    if not symbols:
        st.info("Selecione um ticker em Ações acompanhadas ou cadastre um pela barra lateral para começar.")
        return

    if st.session_state.get("specialist_symbol") not in symbols:
        st.session_state["specialist_symbol"] = symbols[0]
    symbol = st.selectbox("Ação para analisar", options=symbols, key="specialist_symbol")

    try:
        with st.spinner("Calculando indicadores técnicos..."):
            snapshot = _cached_analysis(symbol)
    except requests.RequestException:
        logger.warning("Falha ao buscar candles de %s", symbol, exc_info=True)
        show_backend_unavailable()
        return
    except Exception:
        logger.exception("Falha na análise técnica de %s", symbol)
        st.error(f"Não foi possível analisar {symbol}.")
        return

    st.subheader("Indicadores técnicos")
    st.dataframe([snapshot.as_row()], width="stretch", hide_index=True)
    rsi_status = (
        "sobrecomprado" if snapshot.rsi14 is not None and snapshot.rsi14 >= 70
        else "sobrevendido" if snapshot.rsi14 is not None and snapshot.rsi14 <= 30
        else "neutro" if snapshot.rsi14 is not None
        else "indisponível"
    )
    macd_status = (
        "positivo" if snapshot.macd_histogram is not None and snapshot.macd_histogram > 0
        else "negativo" if snapshot.macd_histogram is not None and snapshot.macd_histogram < 0
        else "neutro" if snapshot.macd_histogram is not None
        else "indisponível"
    )
    rsi_value = f"{snapshot.rsi14:.1f}" if snapshot.rsi14 is not None else "n/d"
    st.info(
        f"Resumo: tendência {snapshot.trend}; MACD {macd_status}; "
        f"RSI 14 em {rsi_value} ({rsi_status})."
    )

    if not st.button("Gerar análise do especialista", type="primary"):
        return
    try:
        with st.status("Gerando resumo técnico..."):
            advice = get_specialist_advice(compact_analysis([snapshot]))
        st.markdown(advice)
    except Exception:
        logger.exception("Falha ao gerar o resumo técnico")
        st.info("Os indicadores foram calculados; não foi possível gerar o resumo do especialista agora.")

