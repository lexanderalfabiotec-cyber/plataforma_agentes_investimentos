"""Agente especialista em investimentos."""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")


def get_specialist_advice(ticker_info: str) -> str:
    message = f"""
    Você é um especialista em investimentos.
    Analise o ativo abaixo:

    {ticker_info}

    Com base nisso, me dê uma recomendação de investimento.
    Responda em JSON com a seguinte estrutura:
    {{
        "recommended_investment": "string",
        "reasoning": "string"
    }}
    """

    response = client.chat.completions.create(
        model="lfm3",
        messages=[
            {"role": "system", "content": "Você é um assistente financeiro."},
            {"role": "user", "content": message},
        ],
        temperature=0.0,
        max_tokens=100,
    )
    return response.choices[0].message.content or ""
