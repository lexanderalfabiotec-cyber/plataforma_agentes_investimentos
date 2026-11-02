"""Agente especialista em investimentos."""

from __future__ import annotations

import os
from collections.abc import Iterator
from functools import lru_cache

import openai

MODEL = os.getenv("OLLAMA_MODEL", "lfm3")

SYSTEM_PROMPT = (
    "Você é um analista técnico de ações. Responda em português do Brasil, de forma clara e "
    "objetiva. Baseie-se somente nos dados recebidos e não invente preços, notícias ou "
    "fundamentos. Quando um indicador estiver como nd, trate-o como indisponível."
)

RESPONSE_TEMPLATE = (
    "Interprete tendência, momentum e riscos usando somente estes dados:\n"
    "{ticker_info}\n\n"
    "Legenda: px = último fechamento; MA = média móvel simples; hist = histograma do MACD.\n\n"
    "Responda em markdown exatamente neste formato:\n"
    "#### Resumo\n"
    "1. **Tendência:** subindo, caindo ou lateral, com a justificativa.\n"
    "2. **Momentum:** forte, moderado ou fraco, com a justificativa.\n"
    "3. **Risco:** baixo, moderado ou alto, com a justificativa.\n"
    "4. **Recomendação:** comprar, vender ou manter, com a justificativa.\n"
    "#### Conclusão\n"
    "Um parágrafo curto."
)


class SpecialistUnavailableError(Exception):
    """Falha ao gerar o parecer; a mensagem pode ser exibida ao usuário."""


@lru_cache(maxsize=1)
def _client() -> openai.OpenAI:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    # O timeout de leitura vale entre pedaços da resposta e precisa cobrir a
    # carga inicial do modelo na memória, que é o trecho mais lento.
    timeout = openai.Timeout(180.0, connect=5.0)
    return openai.OpenAI(base_url=f"{host}/v1", api_key="ollama", timeout=timeout, max_retries=0)


def stream_specialist_advice(ticker_info: str) -> Iterator[str]:
    """Gera o parecer em partes, para o texto aparecer enquanto o modelo escreve."""
    try:
        stream = _client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": RESPONSE_TEMPLATE.format(ticker_info=ticker_info)},
            ],
            temperature=0.1,
            stream=True,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content if chunk.choices else None
            if content:
                yield content
    except openai.NotFoundError as error:
        raise SpecialistUnavailableError(
            f"O modelo de IA “{MODEL}” não está instalado. Execute `ollama pull {MODEL}` e tente novamente."
        ) from error
    except openai.APITimeoutError as error:
        raise SpecialistUnavailableError(
            "O modelo de IA demorou demais para responder. Tente novamente em instantes."
        ) from error
    except openai.APIConnectionError as error:
        raise SpecialistUnavailableError(
            "Não foi possível conectar ao serviço de IA. Verifique se o Ollama está em execução."
        ) from error
    except openai.APIError as error:
        raise SpecialistUnavailableError(
            "O serviço de IA retornou um erro ao gerar o parecer. Tente novamente em instantes."
        ) from error
