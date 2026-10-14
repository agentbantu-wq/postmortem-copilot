# Contributing to postmortem-copilot

Thanks for your interest! This project is intentionally small and
dependency-free — please keep it that way.

## Ground rules

- **Stdlib only.** No new third-party dependencies without discussion.
  The zero-install story is a feature.
- **Tests for behavior.** `python -m pytest` must pass. Mock the HTTP
  layer; never hit a real API in tests.
- **Small, focused PRs.** One change per PR, with a clear description of
  the incident-workflow problem it solves.

## Setup

```bash
git clone https://github.com/shivareddy519/postmortem-copilot
cd postmortem-copilot
pip install -e .
python -m pytest
```

## Good first issues

- Importers for Slack / PagerDuty / incident.io timeline exports
- Additional output formats (Confluence, Notion)
- Prompt improvements with before/after examples
- More realistic example timelines in `examples/`

## Code of Conduct

Be kind, be blameless — in code review as in postmortems.
