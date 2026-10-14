"""Parse and validate incident timelines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

REQUIRED_FIELDS = ("timestamp", "source", "message")


@dataclass
class Event:
    """A single event in an incident timeline."""

    timestamp: str
    source: str
    message: str

    def sort_key(self) -> datetime:
        try:
            return datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError:
            # Unparseable timestamps sort first; validation of content is
            # intentionally lenient so messy real-world logs still work.
            return datetime.min


def load_timeline(path: str) -> list[Event]:
    """Load a timeline from a JSON file.

    Accepts either a bare JSON array of events, or an object with an
    ``"events"`` key holding the array. Each event needs ``timestamp``,
    ``source`` and ``message`` fields. Events are returned in chronological
    order.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "events" in data:
        data = data["events"]

    if not isinstance(data, list) or not data:
        raise ValueError(
            "Timeline must be a non-empty JSON array of events "
            "(or an object with an 'events' key)."
        )

    events: list[Event] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Event #{i} must be a JSON object.")
        missing = [f for f in REQUIRED_FIELDS if f not in item]
        if missing:
            raise ValueError(
                f"Event #{i} is missing required field(s): {', '.join(missing)}"
            )
        events.append(
            Event(
                timestamp=str(item["timestamp"]),
                source=str(item["source"]),
                message=str(item["message"]),
            )
        )

    events.sort(key=lambda e: e.sort_key())
    return events


def format_timeline(events: list[Event]) -> str:
    """Render events as a plain-text timeline for the LLM prompt."""
    return "\n".join(f"- [{e.timestamp}] ({e.source}) {e.message}" for e in events)
