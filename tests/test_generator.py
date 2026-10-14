"""Tests for the LLM postmortem generator (HTTP layer is mocked)."""

import json

import pytest

from postmortem_copilot import generator
from postmortem_copilot.timeline import Event


def make_events():
    return [Event(timestamp="2026-01-01T00:00:00Z", source="alert", message="boom")]


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_build_messages_includes_context():
    messages = generator.build_messages(make_events(), service="api", severity="SEV-1")
    assert messages[0]["role"] == "system"
    user = messages[1]["content"]
    assert "Service: api" in user
    assert "Severity: SEV-1" in user
    assert "boom" in user


def test_generate_posts_to_chat_completions(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["auth"] = req.headers.get("Authorization")
        return FakeResponse({"choices": [{"message": {"content": "# Postmortem"}}]})

    monkeypatch.setattr(generator.urllib.request, "urlopen", fake_urlopen)

    result = generator.generate(make_events(), api_key="sk-test", base_url="http://localhost:11434/v1")

    assert result == "# Postmortem"
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["body"]["model"] == generator.DEFAULT_MODEL


def test_generate_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="No API key"):
        generator.generate(make_events())


def test_generate_rejects_bad_response(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return FakeResponse({"unexpected": "shape"})

    monkeypatch.setattr(generator.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="Unexpected API response"):
        generator.generate(make_events(), api_key="sk-test")
