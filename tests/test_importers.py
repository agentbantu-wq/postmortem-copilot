"""Tests for the Slack export importer."""

import json

import pytest

from postmortem_copilot.importers import load_slack_export


def write_export(tmp_path, data, name="export.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def msg(ts, text, **extra):
    m = {"type": "message", "ts": ts, "text": text}
    m.update(extra)
    return m


def test_epoch_converted_to_iso_utc(tmp_path):
    # 2026-09-18T14:02:11Z
    path = write_export(
        tmp_path, [msg("1789740131.000000", "Firing: CheckoutLatencyHigh", user="U01")]
    )
    events, skipped = load_slack_export(path)
    assert len(events) == 1
    assert events[0].timestamp == "2026-09-18T14:02:11Z"
    assert events[0].source == "slack:U01"
    assert skipped == 0


def test_messages_sorted_chronologically(tmp_path):
    path = write_export(
        tmp_path,
        [
            msg("1789740451.000000", "second", user="U01"),
            msg("1789740131.000000", "first", user="U01"),
        ],
    )
    events, _ = load_slack_export(path)
    assert [e.message for e in events] == ["first", "second"]


def test_housekeeping_subtypes_skipped(tmp_path):
    path = write_export(
        tmp_path,
        [
            msg("1789740131.000000", "someone joined", user="U01", subtype="channel_join"),
            msg("1789740132.000000", "topic set", user="U01", subtype="channel_topic"),
            msg("1789740133.000000", "real signal", user="U01"),
        ],
    )
    events, skipped = load_slack_export(path)
    assert [e.message for e in events] == ["real signal"]
    assert skipped == 2


def test_empty_text_skipped(tmp_path):
    path = write_export(
        tmp_path,
        [
            msg("1789740131.000000", "   ", user="U01"),
            msg("1789740132.000000", "", user="U01"),
            msg("1789740133.000000", "kept", user="U01"),
        ],
    )
    events, skipped = load_slack_export(path)
    assert [e.message for e in events] == ["kept"]
    assert skipped == 2


def test_bot_message_uses_username(tmp_path):
    path = write_export(
        tmp_path,
        [
            msg(
                "1789740131.000000",
                "checkout-api v2.14.3 deployed",
                subtype="bot_message",
                username="deploy-bot",
                bot_id="B01",
            )
        ],
    )
    events, _ = load_slack_export(path)
    assert events[0].source == "slack:deploy-bot"


def test_display_name_prefers_profile_over_user_id(tmp_path):
    path = write_export(
        tmp_path,
        [
            msg(
                "1789740131.000000",
                "Rolling back now",
                user="U01234",
                user_profile={"display_name": "oncall", "real_name": "Shiva S"},
            )
        ],
    )
    events, _ = load_slack_export(path)
    assert events[0].source == "slack:oncall"


def test_attachment_fallback_text_used_when_text_empty(tmp_path):
    path = write_export(
        tmp_path,
        [
            msg(
                "1789740131.000000",
                "",
                subtype="bot_message",
                username="alertmanager",
                attachments=[{"fallback": "Firing: CheckoutLatencyHigh"}],
            )
        ],
    )
    events, skipped = load_slack_export(path)
    assert len(events) == 1
    assert events[0].message == "Firing: CheckoutLatencyHigh"
    assert skipped == 0


def test_messages_key_wrapper_accepted(tmp_path):
    path = write_export(
        tmp_path, {"messages": [msg("1789740131.000000", "hi", user="U01")]}
    )
    events, _ = load_slack_export(path)
    assert len(events) == 1


def test_unparseable_ts_skipped_not_fatal(tmp_path):
    path = write_export(
        tmp_path,
        [
            msg("not-a-timestamp", "bad ts", user="U01"),
            msg("1789740131.000000", "good ts", user="U01"),
        ],
    )
    events, skipped = load_slack_export(path)
    assert [e.message for e in events] == ["good ts"]
    assert skipped == 1


def test_not_an_array_raises(tmp_path):
    path = write_export(tmp_path, {"channel": "incidents"})
    with pytest.raises(ValueError, match="JSON array of messages"):
        load_slack_export(path)


def test_empty_after_filtering_raises(tmp_path):
    path = write_export(
        tmp_path, [msg("1789740131.000000", "joined", subtype="channel_join")]
    )
    with pytest.raises(ValueError, match="No usable messages"):
        load_slack_export(path)


def test_bad_json_raises(tmp_path):
    path = tmp_path / "export.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_slack_export(str(path))


def test_missing_file_raises(tmp_path):
    with pytest.raises(OSError):
        load_slack_export(str(tmp_path / "nope.json"))


def test_cli_import_writes_timeline(tmp_path):
    from postmortem_copilot.cli import main
    from postmortem_copilot.timeline import load_timeline

    export = write_export(
        tmp_path,
        [
            msg("1789740451.000000", "second", user="U01"),
            msg("1789740131.000000", "first", user="U01"),
        ],
    )
    out = tmp_path / "timeline.json"
    assert main(["import", "slack", export, "-o", str(out)]) == 0
    events = load_timeline(str(out))
    assert [e.message for e in events] == ["first", "second"]


def test_cli_import_missing_file_returns_1(tmp_path, capsys):
    from postmortem_copilot.cli import main

    assert main(["import", "slack", str(tmp_path / "nope.json")]) == 1
    assert "Error reading Slack export" in capsys.readouterr().err
