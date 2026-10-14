"""Tests for timeline parsing and validation."""

import json

import pytest

from postmortem_copilot.timeline import Event, format_timeline, load_timeline


def write_timeline(tmp_path, data):
    path = tmp_path / "timeline.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_load_bare_array(tmp_path):
    path = write_timeline(
        tmp_path,
        [
            {"timestamp": "2026-01-01T00:02:00Z", "source": "b", "message": "second"},
            {"timestamp": "2026-01-01T00:01:00Z", "source": "a", "message": "first"},
        ],
    )
    events = load_timeline(path)
    assert [e.message for e in events] == ["first", "second"]  # sorted chronologically


def test_load_object_with_events_key(tmp_path):
    path = write_timeline(
        tmp_path,
        {"events": [{"timestamp": "2026-01-01T00:00:00Z", "source": "a", "message": "m"}]},
    )
    events = load_timeline(path)
    assert len(events) == 1
    assert events[0].source == "a"


def test_missing_field_raises(tmp_path):
    path = write_timeline(
        tmp_path, [{"timestamp": "2026-01-01T00:00:00Z", "source": "a"}]
    )
    with pytest.raises(ValueError, match="missing required field"):
        load_timeline(path)


def test_empty_timeline_raises(tmp_path):
    path = write_timeline(tmp_path, [])
    with pytest.raises(ValueError, match="non-empty"):
        load_timeline(path)


def test_format_timeline():
    events = [Event(timestamp="t", source="s", message="m")]
    assert format_timeline(events) == "- [t] (s) m"
