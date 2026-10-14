# postmortem-copilot

Turn incident timelines into blameless postmortem drafts with an LLM.

`pmc` takes a JSON timeline of incident events — alerts, deploys, on-call
notes — and produces a structured postmortem: summary, impact, timeline,
root-cause analysis, contributing factors, what went well, action items,
and lessons learned. Zero dependencies, works with any OpenAI-compatible
API (OpenAI, Azure, Ollama, vLLM, LiteLLM...).

## Why this exists

Incident platforms (incident.io, Rootly, FireHydrant) bundle AI
postmortems with the platform — and your incident data. postmortem-copilot
is the standalone alternative: bring any timeline export, point it at any
OpenAI-compatible model (including a local Ollama/vLLM instance your data
never leaves), and get a blameless draft in seconds. No platform lock-in,
no data leaving your VPC.

## Quickstart

```bash
git clone https://github.com/shivareddy519/postmortem-copilot
cd postmortem-copilot
pip install -e .
export OPENAI_API_KEY=sk-...

# create a sample timeline to see the format
pmc init

# generate a postmortem draft
pmc generate timeline.json --service checkout-api --severity SEV-2 -o postmortem.md
```

Using a local model:

```bash
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_API_KEY=ollama
export POSTMORTEM_MODEL=llama3.1
pmc generate timeline.json
```

## Timeline format

A JSON array of events (or an object with an `"events"` key). Each event
needs `timestamp`, `source`, and `message`:

```json
{
  "events": [
    {"timestamp": "2026-09-18T14:02:11Z", "source": "alertmanager", "message": "Firing: CheckoutLatencyHigh"},
    {"timestamp": "2026-09-18T14:19:05Z", "source": "oncall", "message": "Rolled back to v2.14.2."}
  ]
}
```

Events are sorted chronologically automatically. Sources can be anything:
`alertmanager`, `deploy-bot`, `oncall`, `comms`, `slack`, ...

## How it works

1. **Parse & validate** the timeline (`timeline.py`)
2. **Build a blameless-postmortem prompt** with 5-whys root-cause guidance
   and strict "don't invent facts" rules (`prompts.py`)
3. **Call the LLM** via the OpenAI chat-completions API (`generator.py`)
4. **Output Markdown** to stdout or a file

The prompt explicitly marks inferences as `(inferred)` and unknowns as
`(unknown)` — a draft is a starting point, not the truth. Always review
before sharing.

## Development

```bash
pip install -e ".[dev]" 2>/dev/null || pip install -e .
python -m pytest
```

## Roadmap

- [ ] Import timelines directly from Slack / PagerDuty / incident.io exports
- [ ] `--format confluence|notion` output targets
- [ ] Action-item tracking (open GitHub/Jira issues from the table)
- [ ] Eval harness scoring draft quality against real postmortems

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
