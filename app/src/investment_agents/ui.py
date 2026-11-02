"""Componentes compartilhados pela interface Streamlit."""

from __future__ import annotations

import logging
from collections.abc import Sequence

import streamlit as st

from investment_agents.integrations.ticker_client import (
    ProviderError,
    ServiceUnavailableError,
    TickerNotFoundError,
    get_latest,
)
from investment_agents.services.market_data import HistoryBatch
from investment_agents.services.ticker_catalog import company_name, load_ticker_catalog, resolve_ticker
from investment_agents.watchlist_db import add_ticker, delete_ticker, get_tickers

logger = logging.getLogger(__name__)

PERIOD_LABELS = {
    "5d": "5 dias",
    "1mo": "1 mês",
    "3mo": "3 meses",
    "6mo": "6 meses",
    "1y": "1 ano",
    "2y": "2 anos",
}

_SELECTED_KEY = "selected_symbols"
_NEWLY_ADDED_KEY = "newly_added_symbols"
_ACTIVE_SYMBOL_KEY = "active_symbol"
_CANDIDATE_KEY = "watchlist_candidate"
_TYPED_KEY = "watchlist_typed"
_NOTICE_KEY = "watchlist_notice"
_PENDING_REMOVAL_KEY = "watchlist_pending_removal"


def theme_type() -> str:
    """Retorna o tema em uso, para os gráficos usarem as cores corretas."""
    return "dark" if st.context.theme.type == "dark" else "light"


# ── Gestão da lista de ativos ─────────────────────────────────────────────────


def _validate_and_add(ticker: str) -> tuple[str, str]:
    """Valida o ticker no backend, salva e retorna (nível, mensagem) para o aviso."""
    try:
        get_latest(ticker)
    except TickerNotFoundError:
        return "error", (
            f"Não encontramos **{ticker}**. Confira o código; ações da B3 usam o sufixo .SA, como PETR4.SA."
        )
    except ServiceUnavailableError:
        return "warning", "O serviço de cotações está indisponível, então o ativo não foi salvo."
    except ProviderError:
        return "warning", f"Não foi possível validar **{ticker}** agora. Tente novamente em instantes."
    except Exception:
        logger.exception("Erro ao validar o ticker %s", ticker)
        return "error", "Ocorreu um erro ao validar o ativo. Tente novamente."

    if not add_ticker(ticker):
        return "info", f"**{ticker}** já está na sua lista."
    st.session_state.setdefault(_NEWLY_ADDED_KEY, []).append(ticker)
    return "success", f"**{ticker}** adicionado."


def _add_candidate() -> None:
    # O formulário limpa os campos após o envio; o código digitado tem prioridade.
    typed = (st.session_state.get(_TYPED_KEY) or "").strip()
    candidate = typed or st.session_state.get(_CANDIDATE_KEY)
    if candidate:
        st.session_state[_NOTICE_KEY] = _validate_and_add(resolve_ticker(candidate))
    else:
        st.session_state[_NOTICE_KEY] = ("info", "Escolha um ativo do catálogo ou digite um código.")


def _request_removal(ticker: str) -> None:
    st.session_state[_PENDING_REMOVAL_KEY] = ticker
    st.session_state.pop(_NOTICE_KEY, None)


def _cancel_removal() -> None:
    st.session_state.pop(_PENDING_REMOVAL_KEY, None)


def _confirm_removal(ticker: str) -> None:
    st.session_state.pop(_PENDING_REMOVAL_KEY, None)
    if delete_ticker(ticker):
        st.session_state[_NOTICE_KEY] = ("success", f"**{ticker}** removido.")
    else:
        st.session_state[_NOTICE_KEY] = ("warning", f"**{ticker}** já não estava na lista.")


def _render_watchlist_row(ticker: str) -> None:
    name = company_name(ticker)
    label = f"**{ticker}** · {name}" if name else f"**{ticker}**"
    if st.session_state.get(_PENDING_REMOVAL_KEY) == ticker:
        st.markdown(f"Remover {label}?")
        cancel, confirm = st.columns(2)
        cancel.button("Cancelar", key=f"cancel_{ticker}", on_click=_cancel_removal, width="stretch")
        confirm.button(
            "Remover",
            key=f"confirm_{ticker}",
            type="primary",
            on_click=_confirm_removal,
            args=(ticker,),
            width="stretch",
        )
        return
    text, action = st.columns([5, 1], vertical_alignment="center")
    text.markdown(label)
    action.button(
        "",
        key=f"remove_{ticker}",
        icon=":material/delete:",
        help=f"Remover {ticker}",
        type="tertiary",
        on_click=_request_removal,
        args=(ticker,),
    )


@st.dialog("Gerenciar ativos", on_dismiss="rerun")
def _manage_watchlist_dialog() -> None:
    labels = {item.yahoo_ticker: item.label for item in load_ticker_catalog()}
    # Campos separados de propósito: com texto livre no mesmo seletor, a busca
    # aproximada troca "AAPL" pela primeira opção parecida do catálogo ao teclar Enter.
    with st.form("add_asset_form", clear_on_submit=True, border=False):
        st.selectbox(
            "Buscar no catálogo",
            options=list(labels),
            index=None,
            format_func=labels.get,
            key=_CANDIDATE_KEY,
            placeholder="Nome da empresa ou código",
        )
        st.text_input("Ou digite outro código", key=_TYPED_KEY, placeholder="Ex.: AAPL, BTC-USD")
        st.form_submit_button("Adicionar", type="primary", on_click=_add_candidate)

    notice = st.session_state.pop(_NOTICE_KEY, None)
    if notice:
        level, message = notice
        getattr(st, level)(message)

    st.divider()
    tickers = get_tickers()
    if tickers:
        st.markdown(f"**Na sua lista** ({len(tickers)})")
        with st.container(height=min(280, 52 * len(tickers) + 16), border=False):
            for ticker in tickers:
                _render_watchlist_row(ticker)
    else:
        st.caption("Sua lista está vazia.")

    if st.button("Concluir", width="stretch"):
        st.rerun()


def open_manage_watchlist() -> None:
    st.session_state.pop(_PENDING_REMOVAL_KEY, None)
    st.session_state.pop(_NOTICE_KEY, None)
    _manage_watchlist_dialog()


def render_sidebar() -> list[str]:
    """Desenha a barra lateral e retorna os ativos selecionados."""
    registered = get_tickers()
    with st.sidebar:
        st.subheader("Ações acompanhadas")
        selected: list[str] = []
        if registered:
            # A lista pode mudar no diálogo ou em outra aba; um valor fora das
            # opções faria o multiselect falhar.
            current = st.session_state.get(_SELECTED_KEY, registered)
            added = st.session_state.pop(_NEWLY_ADDED_KEY, [])
            st.session_state[_SELECTED_KEY] = [
                symbol for symbol in dict.fromkeys([*current, *added]) if symbol in registered
            ]
            selected = st.multiselect(
                "Ações acompanhadas",
                options=registered,
                key=_SELECTED_KEY,
                label_visibility="collapsed",
                placeholder="Escolha os ativos",
            )
        if st.button("Gerenciar ativos", icon=":material/tune:", width="stretch"):
            open_manage_watchlist()
        st.caption("Cotações do Yahoo Finance, sujeitas a atraso.")
    return selected


# ── Elementos reutilizados pelas páginas ──────────────────────────────────────


def render_no_selection() -> None:
    """Estado vazio com a próxima ação que o usuário deve tomar."""
    if get_tickers():
        st.info("Selecione ao menos um ativo na barra lateral.", icon=":material/arrow_back:")
        return
    st.info("Sua lista está vazia. Adicione os ativos que deseja acompanhar.", icon=":material/add_chart:")
    if st.button("Adicionar ativos", type="primary", icon=":material/add:"):
        open_manage_watchlist()


def show_service_unavailable() -> None:
    st.error(
        "Não foi possível conectar ao serviço de cotações. "
        "Verifique se o backend está em execução e tente novamente.",
        icon=":material/cloud_off:",
    )
    st.button("Tentar novamente", icon=":material/refresh:")


def show_fetch_issues(batch: HistoryBatch) -> None:
    """Explica por ativo o que não pôde ser carregado, separando as causas."""
    if batch.service_unavailable:
        show_service_unavailable()
    if batch.provider_failed:
        st.warning(
            f"O provedor de cotações não respondeu para {', '.join(batch.provider_failed)}. "
            "Tente novamente em instantes.",
            icon=":material/schedule:",
        )
    if batch.not_found:
        st.warning(
            f"Sem dados para {', '.join(batch.not_found)}. O ativo pode ter saído de negociação; "
            "você pode removê-lo em **Gerenciar ativos**.",
            icon=":material/search_off:",
        )


def select_symbol(symbols: Sequence[str], page: str, label: str = "Ativo") -> str:
    """Seletor de ativo que mantém a mesma escolha ao trocar de página."""
    key = f"{page}_symbol"
    if st.session_state.get(key) not in symbols:
        active = st.session_state.get(_ACTIVE_SYMBOL_KEY)
        st.session_state[key] = active if active in symbols else symbols[0]
    symbol = st.selectbox(label, options=symbols, key=key, format_func=symbol_label)
    st.session_state[_ACTIVE_SYMBOL_KEY] = symbol
    return symbol


def _keep_period_selected(key: str, last_key: str) -> None:
    """Clicar no período ativo desmarcaria o controle; mantém a última escolha."""
    if st.session_state.get(key) is None:
        st.session_state[key] = st.session_state.get(last_key)


def select_period(options: Sequence[str], default: str, page: str) -> str:
    """Seletor de período que sempre mantém uma opção marcada."""
    key, last_key = f"{page}_period", f"{page}_last_period"
    last = st.session_state.setdefault(last_key, default)
    if st.session_state.get(key) not in options:
        st.session_state[key] = last
    selection = st.segmented_control(
        "Período",
        options=options,
        format_func=PERIOD_LABELS.get,
        key=key,
        on_change=_keep_period_selected,
        args=(key, last_key),
    )
    st.session_state[last_key] = selection or last
    return st.session_state[last_key]


def symbol_label(symbol: str) -> str:
    name = company_name(symbol)
    return f"{symbol} · {name}" if name else symbol
