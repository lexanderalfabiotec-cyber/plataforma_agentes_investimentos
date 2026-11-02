from types import SimpleNamespace

import httpx
import openai
import pytest

from investment_agents.agents import specialist_agent
from investment_agents.agents.specialist_agent import SpecialistUnavailableError, stream_specialist_advice


def _chunk(content):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


def _install(monkeypatch, create):
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(specialist_agent, "_client", lambda: client)


def test_stream_yields_only_text_and_includes_data_in_prompt(monkeypatch):
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return iter([_chunk("Olá"), _chunk(None), SimpleNamespace(choices=[]), _chunk(" mundo")])

    _install(monkeypatch, create)
    assert "".join(stream_specialist_advice("PETR4.SA px=30")) == "Olá mundo"
    assert captured["stream"] is True
    assert "PETR4.SA px=30" in captured["messages"][1]["content"]


REQUEST = httpx.Request("POST", "http://ollama/v1/chat/completions")


@pytest.mark.parametrize(
    ("error", "fragment"),
    [
        (openai.NotFoundError("x", response=httpx.Response(404, request=REQUEST), body=None), "ollama pull"),
        (openai.APIConnectionError(request=REQUEST), "Ollama"),
        (openai.APITimeoutError(request=REQUEST), "demorou"),
        (openai.InternalServerError("x", response=httpx.Response(500, request=REQUEST), body=None), "erro"),
    ],
)
def test_openai_errors_become_friendly_messages(monkeypatch, error, fragment):
    def create(**kwargs):
        raise error

    _install(monkeypatch, create)
    with pytest.raises(SpecialistUnavailableError, match=fragment):
        list(stream_specialist_advice("dados"))
