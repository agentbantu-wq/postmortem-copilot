"""Command-line interface for postmortem-copilot."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .generator import DEFAULT_MODEL, generate
from .timeline import load_timeline

SAMPLE_TIMELINE = {
    "service": "checkout-api",
    "severity": "SEV-2",
    "events": [
        {
            "timestamp": "2026-09-18T14:02:11Z",
            "source": "alertmanager",
            "message": "Firing: CheckoutLatencyHigh — p99 latency > 2s for 5m (checkout-api, prod-us)",
        },
        {
            "timestamp": "2026-09-18T14:05:44Z",
            "source": "oncall",
            "message": "Acknowledged page. Dashboard shows latency spike starting ~13:58, error rate still < 0.1%.",
        },
        {
            "timestamp": "2026-09-18T14:11:02Z",
            "source": "deploy-bot",
            "message": "checkout-api v2.14.3 deployed to prod-us at 13:57 by CI pipeline (commit 9f3ac21).",
        },
        {
            "timestamp": "2026-09-18T14:16:37Z",
            "source": "oncall",
            "message": "v2.14.3 changed pricing-cache TTL from 300s to 30s. Cache hit ratio dropped 98% -> 41%. Looks like a cache stampede on the pricing DB.",
        },
        {
            "timestamp": "2026-09-18T14:19:05Z",
            "source": "oncall",
            "message": "Rolled back to v2.14.2. Latency recovering.",
        },
        {
            "timestamp": "2026-09-18T14:24:50Z",
            "source": "alertmanager",
            "message": "Resolved: CheckoutLatencyHigh — p99 back under 400ms.",
        },
        {
            "timestamp": "2026-09-18T14:31:12Z",
            "source": "comms",
            "message": "Status page updated: incident resolved, ~27 min of degraded checkout latency, no failed payments observed.",
        },
    ],
}


def cmd_init(args: argparse.Namespace) -> int:
    """Write a sample timeline JSON file to get started."""
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(SAMPLE_TIMELINE, f, indent=2)
    print(f"Wrote sample timeline to {args.output}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate a postmortem draft from a timeline file."""
    try:
        events = load_timeline(args.timeline)
    except (OSError, ValueError) as exc:
        print(f"Error reading timeline: {exc}", file=sys.stderr)
        return 1

    try:
        markdown = generate(
            events,
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
            service=args.service,
            severity=args.severity,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"Wrote postmortem to {args.out}")
    else:
        print(markdown)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pmc",
        description="Turn incident timelines into blameless postmortem drafts.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Write a sample timeline JSON file.")
    p_init.add_argument(
        "-o", "--output", default="timeline.json", help="Output path (default: timeline.json)"
    )
    p_init.set_defaults(func=cmd_init)

    p_gen = sub.add_parser("generate", help="Generate a postmortem from a timeline.")
    p_gen.add_argument("timeline", help="Path to timeline JSON file.")
    p_gen.add_argument("--service", default="", help="Service name for context.")
    p_gen.add_argument("--severity", default="", help="Severity, e.g. SEV-2.")
    p_gen.add_argument("--api-key", default=None, help="API key (or set OPENAI_API_KEY).")
    p_gen.add_argument(
        "--base-url",
        default=None,
        help="OpenAI-compatible base URL (or set OPENAI_BASE_URL).",
    )
    p_gen.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL})."
    )
    p_gen.add_argument("-o", "--out", default=None, help="Write Markdown to file instead of stdout.")
    p_gen.set_defaults(func=cmd_generate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
