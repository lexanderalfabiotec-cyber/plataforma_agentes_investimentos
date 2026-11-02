"""Gráficos Altair da plataforma, com cores definidas por papel e por tema."""

from __future__ import annotations

from collections.abc import Sequence

import altair as alt
import pandas as pd

from investment_agents.integrations.ticker_client import Candle

# Paleta categórica validada para daltonismo; a ordem é fixa e não deve ser ciclada.
SERIES_COLORS = {
    "light": ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"),
    "dark": ("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"),
}
MAX_COMPARED_SERIES = len(SERIES_COLORS["light"])

_UP_COLOR = {"light": "#1baf7a", "dark": "#199e70"}
_DOWN_COLOR = {"light": "#e34948", "dark": "#e66767"}
_NEUTRAL_COLOR = {"light": "#8a8985", "dark": "#8a8985"}
_LABEL_COLOR = {"light": "#52514e", "dark": "#c3c2b7"}

_DATE_TITLE = "Data"
_DATE_FORMAT = "%d/%m/%Y"
# Largura fixa do eixo Y para alinhar as datas dos gráficos de preço e volume.
_Y_AXIS_WIDTH = 60
_DIRECT_LABEL_LIMIT = 4


def candles_frame(candles: Sequence[Candle]) -> pd.DataFrame:
    """Converte candles em um DataFrame com data sem horário."""
    return pd.DataFrame(
        {
            "date": [pd.Timestamp(candle.date.date()) for candle in candles],
            "open": [candle.open for candle in candles],
            "high": [candle.high for candle in candles],
            "low": [candle.low for candle in candles],
            "close": [candle.close for candle in candles],
            "volume": [candle.volume for candle in candles],
        }
    )


def _date_axis(span_days: int) -> alt.X:
    label_format = "%d/%m" if span_days <= 200 else "%m/%Y"
    return alt.X("date:T", title=None, axis=alt.Axis(format=label_format, tickCount=6, grid=False))


def _crosshair(frame: pd.DataFrame, tooltip: list[alt.Tooltip], x: alt.X, theme: str) -> alt.Chart:
    """Cria a camada de hover: uma régua na data mais próxima do ponteiro."""
    hover = alt.selection_point(
        fields=["date"], nearest=True, on="pointerover", clear="pointerout", empty=False
    )
    return (
        alt.Chart(frame)
        .mark_rule(strokeWidth=1, color=_NEUTRAL_COLOR[theme])
        .encode(x=x, opacity=alt.condition(hover, alt.value(0.8), alt.value(0)), tooltip=tooltip)
        .add_params(hover)
    )


def price_chart(frame: pd.DataFrame, theme: str = "light", height: int = 340) -> alt.LayerChart:
    """Candles até seis meses; acima disso, linha, pois os corpos ficam ilegíveis."""
    span_days = (frame["date"].max() - frame["date"].min()).days
    x = _date_axis(span_days)
    y_scale = alt.Scale(zero=False, nice=True)
    y = alt.Y(
        "low:Q",
        title="Preço",
        scale=y_scale,
        axis=alt.Axis(tickCount=6, minExtent=_Y_AXIS_WIDTH, maxExtent=_Y_AXIS_WIDTH),
    )
    tooltip = [
        alt.Tooltip("date:T", title=_DATE_TITLE, format=_DATE_FORMAT),
        alt.Tooltip("open:Q", title="Abertura", format=",.2f"),
        alt.Tooltip("high:Q", title="Máxima", format=",.2f"),
        alt.Tooltip("low:Q", title="Mínima", format=",.2f"),
        alt.Tooltip("close:Q", title="Fechamento", format=",.2f"),
    ]
    crosshair = _crosshair(frame, tooltip, x, theme)

    if span_days > 200:
        line = (
            alt.Chart(frame)
            .mark_line(strokeWidth=2, color=SERIES_COLORS[theme][0])
            .encode(
                x=x,
                y=alt.Y(
                    "close:Q",
                    title="Preço",
                    scale=y_scale,
                    axis=alt.Axis(tickCount=6, minExtent=_Y_AXIS_WIDTH, maxExtent=_Y_AXIS_WIDTH),
                ),
            )
        )
        return alt.layer(line, crosshair).properties(height=height)

    direction = alt.condition(
        "datum.close >= datum.open", alt.value(_UP_COLOR[theme]), alt.value(_DOWN_COLOR[theme])
    )
    base = alt.Chart(frame).encode(x=x, color=direction)
    wick = base.mark_rule(strokeWidth=1).encode(y=y, y2="high:Q")
    body_width = max(2, min(12, int(560 / max(len(frame), 1))))
    body = base.mark_bar(size=body_width).encode(
        y=alt.Y("open:Q", title="Preço", scale=y_scale), y2="close:Q"
    )
    return alt.layer(wick, body, crosshair).properties(height=height)


def volume_chart(frame: pd.DataFrame, theme: str = "light", height: int = 110) -> alt.Chart:
    """Volume em gráfico separado, em vez de um segundo eixo no gráfico de preços."""
    span_days = (frame["date"].max() - frame["date"].min()).days
    body_width = max(1, min(12, int(560 / max(len(frame), 1))))
    return (
        alt.Chart(frame)
        .mark_bar(size=body_width, color=_NEUTRAL_COLOR[theme], opacity=0.55)
        .encode(
            x=_date_axis(span_days),
            y=alt.Y(
                "volume:Q",
                title="Volume",
                axis=alt.Axis(format="~s", tickCount=3, minExtent=_Y_AXIS_WIDTH, maxExtent=_Y_AXIS_WIDTH),
            ),
            tooltip=[
                alt.Tooltip("date:T", title=_DATE_TITLE, format=_DATE_FORMAT),
                alt.Tooltip("volume:Q", title="Volume", format=",.0f"),
            ],
        )
        .properties(height=height)
    )


def comparison_chart(
    series: dict[str, Sequence[Candle]], color_order: Sequence[str], theme: str = "light", height: int = 420
) -> alt.LayerChart:
    """Compara a variação acumulada; a cor acompanha o ativo, não sua posição no gráfico."""
    frames = []
    for symbol, candles in series.items():
        base = candles[0].close
        frames.append(
            pd.DataFrame(
                {
                    "date": [pd.Timestamp(candle.date.date()) for candle in candles],
                    "symbol": symbol,
                    "change": [(candle.close / base - 1) * 100 for candle in candles],
                }
            )
        )
    long_frame = pd.concat(frames, ignore_index=True)
    span_days = (long_frame["date"].max() - long_frame["date"].min()).days
    x = _date_axis(span_days)

    color = alt.Color(
        "symbol:N",
        title=None,
        scale=alt.Scale(domain=list(color_order), range=list(SERIES_COLORS[theme])),
        legend=alt.Legend(orient="top", values=list(series)),
    )
    lines = (
        alt.Chart(long_frame)
        .mark_line(strokeWidth=2)
        .encode(
            x=x,
            y=alt.Y(
                "change:Q",
                title="Variação (%)",
                axis=alt.Axis(tickCount=6, minExtent=_Y_AXIS_WIDTH, maxExtent=_Y_AXIS_WIDTH),
            ),
            color=color,
        )
    )
    baseline = (
        alt.Chart(pd.DataFrame({"zero": [0]}))
        .mark_rule(strokeWidth=1, color=_NEUTRAL_COLOR[theme])
        .encode(y="zero:Q")
    )

    # Tabela larga com nomes neutros: tickers como PETR4.SA têm ponto, que o Vega
    # interpretaria como acesso a um campo aninhado.
    columns = {symbol: f"s{index}" for index, symbol in enumerate(series)}
    wide = (
        long_frame.pivot_table(index="date", columns="symbol", values="change")
        .rename(columns=columns)
        .reset_index()
    )
    tooltip = [alt.Tooltip("date:T", title=_DATE_TITLE, format=_DATE_FORMAT)] + [
        alt.Tooltip(f"{column}:Q", title=symbol, format="+.2f") for symbol, column in columns.items()
    ]
    crosshair = _crosshair(wide, tooltip, x, theme)

    layers = [baseline, lines, crosshair]
    padding = {}
    if len(series) <= _DIRECT_LABEL_LIMIT:
        last_points = long_frame.sort_values("date").groupby("symbol", as_index=False).last()
        labels = (
            alt.Chart(last_points)
            .mark_text(align="left", dx=6, fontSize=12, color=_LABEL_COLOR[theme])
            .encode(x=x, y="change:Q", text="symbol:N")
        )
        layers.append(labels)
        padding = {"right": 80}
    return alt.layer(*layers).properties(height=height, padding=padding)
