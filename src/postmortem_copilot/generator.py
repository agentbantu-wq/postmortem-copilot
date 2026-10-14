"""Generate a postmortem draft via an OpenAI-compatible chat completions API."""

from __future__ import annotations

import json
import os
import urllib.request

from .prompts import SYSTEM_PROMPT
from .timeline import Event, format_timeline

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


def build_messages(
    events: list[Event], service: str = "", severity: str = ""
) -> list[dict]:
    """Build the chat messages sent to the LLM."""
    context_lines = []
    if service:
        context_lines.append(f"Service: {service}")
    if severity:
        context_lines.append(f"Severity: {severity}")

    user = "Generate a blameless postmortem for the following incident.\n"
    if context_lines:
        user += "\n".join(context_lines) + "\n"
    user += "\nTimeline:\n" + format_timeline(events)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def generate(
    events: list[Event],
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    service: str = "",
    severity: str = "",
    timeout: int = 120,
) -> str:
    """Call the LLM and return the postmortem Markdown.

    Works with any OpenAI-compatible endpoint (OpenAI, Azure OpenAI,
    Ollama, vLLM, LiteLLM proxy, ...).
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("No API key: pass --api-key or set OPENAI_API_KEY.")
    base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = model or os.environ.get("POSTMORTEM_MODEL") or DEFAULT_MODEL

    payload = json.dumps(
        {
            "model": model,
            "messages": build_messages(events, service=service, severity=severity),
            "temperature": 0.3,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        base_url + "/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected API response: {body}") from exc
