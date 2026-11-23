"""Import incident timelines from chat / incident-platform exports.

Supported formats (more to come):

- ``slack`` — a Slack channel export: a JSON array of message objects, the
  shape Slack's export tool writes (one file per channel per day), or an
  object with a ``"messages"`` key holding that array.

Slack messages are noisy by nature, so the importer is deliberately
lenient: it keeps every message with usable text, skips channel
housekeeping (joins/leaves/topic changes), and reports how many messages
it skipped. Nothing is silently reworded — the message text is kept
verbatim, including ``<@U...>`` mention markup, so the timeline stays a
faithful record of what was said.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .timeline import Event

# Slack message subtypes that carry no incident signal: membership changes
# and channel-metadata housekeeping. Everything else with non-empty text is
# kept — including ``bot_message`` posts, because deploy bots and alert bots
# are often the most reliable signal in an incident channel.
SKIPPED_SUBTYPES = frozenset(
    {
        "channel_join",
        "channel_leave",
        "channel_topic",
        "channel_purpose",
        "channel_name",
        "channel_archive",
        "channel_unarchive",
        "pinned_item",
        "unpinned_item",
        "reminder_add",
    }
)


def _epoch_to_iso(ts: object) -> str:
    """Convert a Slack epoch timestamp (``"1726509731.123456"``) to ISO-8601 UTC."""
    seconds = float(ts)  # raises ValueError/TypeError for garbage input
    return (
        datetime.fromtimestamp(seconds, tz=timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )


def _display_name(message: dict) -> str:
    """Best human-readable name for the message author."""
    if message.get("username"):
        return str(message["username"])
    profile = message.get("user_profile")
    if isinstance(profile, dict):
        for key in ("display_name", "real_name"):
            if profile.get(key):
                return str(profile[key])
    if message.get("user"):
        return str(message["user"])
    if message.get("bot_id"):
        return str(message["bot_id"])
    return "unknown"


def _message_text(message: dict) -> str:
    """Message text, falling back to attachment text for bot posts.

    Alert bots often post with an empty ``text`` and the content in
    ``attachments[].fallback`` (or ``attachments[].text``).
    """
    text = str(message.get("text") or "").strip()
    if text:
        return text
    attachments = message.get("attachments")
    if isinstance(attachments, list):
        parts = []
        for att in attachments:
            if isinstance(att, dict):
                for key in ("fallback", "text"):
                    if att.get(key):
                        parts.append(str(att[key]).strip())
        text = " ".join(p for p in parts if p)
    return text


def load_slack_export(path: str) -> tuple[list[Event], int]:
    """Load a Slack channel export into timeline events.

    Returns ``(events, skipped)`` where ``events`` are chronologically
    sorted :class:`~postmortem_copilot.timeline.Event` objects and
    ``skipped`` is the number of messages dropped (housekeeping subtypes,
    empty text, or unparseable timestamps).

    Raises ``ValueError`` if the file is not a Slack export at all, or if
    no usable messages remain after filtering.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "messages" in data:
        data = data["messages"]

    if not isinstance(data, list):
        raise ValueError(
            "Slack export must be a JSON array of messages "
            "(or an object with a 'messages' key)."
        )

    events: list[Event] = []
    skipped = 0
    for i, message in enumerate(data):
        if not isinstance(message, dict):
            skipped += 1
            continue
        if message.get("subtype") in SKIPPED_SUBTYPES:
            skipped += 1
            continue
        text = _message_text(message)
        if not text:
            skipped += 1
            continue
        try:
            timestamp = _epoch_to_iso(message.get("ts"))
        except (TypeError, ValueError, OverflowError, OSError):
            skipped += 1
            continue
        events.append(
            Event(
                timestamp=timestamp,
                source=f"slack:{_display_name(message)}",
                message=text,
            )
        )

    if not events:
        raise ValueError(
            "No usable messages in Slack export "
            f"({len(data)} messages read, {skipped} skipped)."
        )

    events.sort(key=lambda e: e.sort_key())
    return events, skipped
