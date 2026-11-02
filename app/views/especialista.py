"""Análise técnica de uma ação acompanhada."""

import logging

import streamlit as st

from investment_agents.agents.specialist_agent import SpecialistUnavailableError, stream_specialist_advice
from investment_agents.formatting import format_date, format_price
from investment_agents.integrations.ticker_client import (
    ProviderError,
    ServiceUnavailableError,
    TickerNotFoundError,
)
from investment_agents.services.technical_analysis import analyze_ticker, compact_analysis
from investment_agents.ui import render_no_selection, render_sidebar, select_symbol, show_service_unavailable

logger = logging.getLogger(__name__)

_ADVICE_KEY = "specialist_advice"


def _render_indicators(snapshot) -> None:
    price, trend, rsi, macd = st.columns(4)
    price.metric(
        f"Preço · {format_date(snapshot.as_of)}",
        format_price(snapshot.close, snapshot.currency),
        border=True,
        height="stretch",
    )
    trend.metric(
        "Tendência",
        snapshot.trend.capitalize(),
        border=True,
        height="stretch",
        help="Compara o preço com as médias de 50 e 200 dias, ou com a de 20 dias se o histórico for curto.",
    )
    rsi.metric(
        "RSI 14",
        f"{snapshot.rsi14:.1f}".replace(".", ",") if snapshot.rsi14 is not None else "—",
        snapshot.rsi_status.capitalize(),
        delta_color="off",
        delta_arrow="off",
        border=True,
        height="stretch",
        help="Força recente do preço, de 0 a 100. Acima de 70 sugere sobrecompra; abaixo de 30, sobrevenda.",
    )
    macd.metric(
        "Momentum (MACD)",
        snapshot.macd_status.capitalize(),
        border=True,
        height="stretch",
        help="Histograma do MACD: positivo indica aceleração de alta; negativo, de baixa.",
    )
    with st.expander("Ver todos os indicadores"):
        st.dataframe([snapshot.as_row()], width="stretch", hide_index=True)


def _render_advice(snapshot) -> None:
    saved_advice = st.session_state.setdefault(_ADVICE_KEY, {})
    saved = saved_advice.get(snapshot.symbol)

    st.subheader("Parecer da IA")
    generate = st.button(
        "Gerar novamente" if saved else "Gerar parecer",
        type="secondary" if saved else "primary",
        icon=":material/auto_awesome:",
    )
    if generate:
        try:
            with st.spinner(
                "O modelo está analisando os indicadores; a primeira resposta pode levar cerca de 1 minuto..."
            ):
                text = st.write_stream(stream_specialist_advice(compact_analysis([snapshot])))
        except SpecialistUnavailableError as error:
            logger.warning("Parecer indisponível para %s", snapshot.symbol, exc_info=True)
            st.warning(str(error), icon=":material/smart_toy:")
            return
        if not text:
            st.warning("O modelo não retornou conteúdo. Tente novamente.", icon=":material/smart_toy:")
            return
        saved = saved_advice[snapshot.symbol] = {
            "text": text,
            "basis": f"{format_price(snapshot.close, snapshot.currency)} em {format_date(snapshot.as_of)}",
        }
    elif saved:
        st.markdown(saved["text"])

    if saved:
        st.caption(f"Parecer baseado no preço de {saved['basis']}.")
    st.caption(
        "Conteúdo gerado por IA a partir de indicadores técnicos, sem considerar notícias ou fundamentos. "
        "Pode conter erros e não constitui recomendação de investimento."
    )


def render() -> None:
    symbols = render_sidebar()
    st.title("Especialista")
    if not symbols:
        render_no_selection()
        return

    symbol = select_symbol(symbols, page="especialista", label="Ativo para analisar")
    try:
        with st.spinner("Calculando indicadores..."):
            snapshot = analyze_ticker(symbol)
    except ServiceUnavailableError:
        show_service_unavailable()
        return
    except (TickerNotFoundError, ValueError):
        st.warning(f"Sem dados suficientes para analisar {symbol}.", icon=":material/search_off:")
        return
    except ProviderError:
        logger.warning("Provedor falhou ao analisar %s", symbol, exc_info=True)
        st.warning(
            "O provedor de cotações não respondeu. Tente novamente em instantes.", icon=":material/schedule:"
        )
        return

    _render_indicators(snapshot)
    st.divider()
    _render_advice(snapshot)
