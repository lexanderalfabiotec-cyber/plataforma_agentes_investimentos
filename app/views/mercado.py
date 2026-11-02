"""Consulta de cotações e histórico do mercado."""

import logging

import streamlit as st

from investment_agents.charts import candles_frame, price_chart, volume_chart
from investment_agents.formatting import format_compact, format_date, format_percent, format_price
from investment_agents.integrations.ticker_client import (
    ProviderError,
    ServiceUnavailableError,
    TickerNotFoundError,
    get_history,
)
from investment_agents.services.market_data import day_change, period_change
from investment_agents.ui import (
    PERIOD_LABELS,
    render_no_selection,
    render_sidebar,
    select_period,
    select_symbol,
    show_service_unavailable,
    theme_type,
)

logger = logging.getLogger(__name__)


def _render_summary(history, period: str) -> None:
    candles = history.candles
    last = candles[-1]
    currency = history.currency
    change = day_change(candles)
    variation = period_change(candles)
    price, performance, extremes, volume = st.columns(4)
    price.metric(
        f"Último preço · {format_date(last.date.date())}",
        format_price(last.close, currency),
        f"{format_percent(change)} no dia" if change is not None else None,
        border=True,
        height="stretch",
    )
    performance.metric(
        f"Variação em {PERIOD_LABELS[period]}",
        format_percent(variation) if variation is not None else "—",
        border=True,
        height="stretch",
    )
    extremes.metric(
        "Máxima do período",
        format_price(max(candle.high for candle in candles), currency),
        f"Mínima {format_price(min(candle.low for candle in candles), currency)}",
        delta_color="off",
        delta_arrow="off",
        border=True,
        height="stretch",
    )
    volume.metric(
        "Volume médio diário",
        format_compact(sum(candle.volume for candle in candles) / len(candles)),
        border=True,
        height="stretch",
    )


def _render_table(frame) -> None:
    table = frame.sort_values("date", ascending=False).rename(
        columns={
            "date": "Data",
            "open": "Abertura",
            "high": "Máxima",
            "low": "Mínima",
            "close": "Fechamento",
            "volume": "Volume",
        }
    )
    number = st.column_config.NumberColumn(format="localized")
    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Abertura": number,
            "Máxima": number,
            "Mínima": number,
            "Fechamento": number,
            "Volume": number,
        },
    )


def render() -> None:
    symbols = render_sidebar()
    st.title("Mercado")
    if not symbols:
        render_no_selection()
        return

    selector, periods = st.columns([2, 3], vertical_alignment="bottom")
    with selector:
        symbol = select_symbol(symbols, page="mercado")
    with periods:
        period = select_period(["5d", "1mo", "3mo", "6mo", "1y", "2y"], default="3mo", page="mercado")

    try:
        with st.spinner("Carregando histórico..."):
            history = get_history(symbol, range=period, interval="1d")
    except ServiceUnavailableError:
        show_service_unavailable()
        return
    except TickerNotFoundError:
        st.warning(
            f"Sem dados para {symbol}. O ativo pode ter saído de negociação.", icon=":material/search_off:"
        )
        return
    except ProviderError:
        logger.warning("Provedor falhou ao consultar %s", symbol, exc_info=True)
        st.warning(
            "O provedor de cotações não respondeu. Tente novamente em instantes.", icon=":material/schedule:"
        )
        return

    if not history.candles:
        st.info("Não há cotações para esse período.")
        return

    _render_summary(history, period)
    frame = candles_frame(history.candles)
    theme = theme_type()
    st.altair_chart(price_chart(frame, theme), width="stretch")
    st.altair_chart(volume_chart(frame, theme), width="stretch")
    with st.expander("Ver tabela de cotações"):
        _render_table(frame)
