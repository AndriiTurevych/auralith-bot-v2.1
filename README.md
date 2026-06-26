# Auralith Bot v2.1 — C-Suite Agents

A multi-agent system that simulates a company's executive leadership team using
Claude. Each role is an independent agent with its own domain, expertise, and
decision-making style. A Telegram bot exposes them for one-off advice or a
full "board meeting" where every executive weighs in and the CEO synthesizes
a final decision.

## Roles

| Command | Role | Domain |
|---|---|---|
| `/ceo` | CEO | Strategy, vision, resource allocation, final decisions |
| `/coo` | COO | Operations, execution, delivery |
| `/cfo` | CFO | Budget, cash flow, unit economics, financial risk |
| `/cmo` | CMO | Marketing, brand, growth, acquisition |
| `/cto` | CTO | Technology strategy, architecture, engineering |
| `/cio` | CIO | Internal IT, infrastructure, data governance, security |
| `/chro` | CHRO | People, hiring, org design, culture |
| `/clo` | CLO | Legal risk, contracts, compliance |
| `/cpo` | CPO | Product strategy, roadmap, UX |
| `/analyst` | Chief Analytics Officer | Data analysis, reporting, forecasting |
| `/planner` | Production Planning Director | Production scheduling, capacity, bottlenecks |
| `/energy` | Energy Manager | Power supply, grid resilience, backup power |
| `/cro` | Chief Risk Officer | Enterprise risk, war/sanctions/FX risk, insurance |
| `/scd` | Supply Chain Director | Logistics, customs, supplier networks |
| `/procurement` | Procurement Specialist | Sourcing, vendor negotiation, procurement law |

All agents default to Ukrainian and reason from Ukrainian legal, tax, and
regulatory context (martial law, NBU currency controls, Prozorro public
procurement, customs, NEURC energy regulation, etc.) instead of generic
Western assumptions. They reply in whatever language you write in.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env  # fill in ANTHROPIC_API_KEY and TELEGRAM_BOT_TOKEN
```

## Run the bot

```bash
python -m auralith.main
```

## Telegram commands

- `/ask <role> <question>` — get a single executive's perspective, e.g. `/ask cfo What's our runway?`
- `/<role> <question>` — shortcut for the above, e.g. `/cto Should we migrate to microservices?`
- `/board <topic>` — convene the full board: every executive gives their take in parallel, then the CEO synthesizes a final decision with next steps
- `/debate <topic>` — like `/board`, but executives see each other's positions and get a rebuttal round before the CEO synthesizes (more API calls, sharper conflict)
- `/context` — show the company context currently injected into every agent prompt
- `/log` — show the last 5 logged board/debate decisions
- `/roles` — list all available executives and their domains

## Company context

`company_context.md` (repo root) is automatically read and injected into
every agent prompt — edit it with real metrics, stage, priorities, and
constraints so advice is grounded instead of generic. Override the path with
`COMPANY_CONTEXT_PATH`. If the file is missing, agents just get the question
with no company context.

## Decision log

Every `/board` and `/debate` run is appended as a JSON line to
`decisions.log.jsonl` (path override: `DECISION_LOG_PATH`) with a timestamp,
mode, topic, every executive's position, and the CEO's final decision. This
file is gitignored — treat it as runtime data, not source.

## Architecture

- `auralith/agents/` — `Agent` dataclass (`key`, `title`, `domain`, `system_prompt`) and the nine role definitions
- `auralith/company_context.py` — loads `company_context.md` (or the configured path) as a string
- `auralith/decision_log.py` — appends/reads board decisions as JSONL
- `auralith/orchestrator.py` — `Orchestrator.ask()` for single-agent queries (auto-injects company context); `Orchestrator.board_meeting()` for parallel multi-agent consultation + CEO synthesis; `Orchestrator.board_debate()` for multi-round rebuttal before synthesis. Both meeting modes log to the decision log.
- `auralith/bot/telegram_bot.py` — aiogram `Dispatcher` wiring Telegram commands to the orchestrator
- `auralith/main.py` — entry point; wires up the Anthropic client, orchestrator, and bot, then starts polling

Adding a new role: define an `Agent` in `auralith/agents/roles.py` and add it
to `AGENTS`. It automatically gets a `/<key>` Telegram command and joins the
board meeting and debate.

Tuning debate depth: `DEBATE_ROUNDS` (default `2` — one opening round plus
one rebuttal round). Each extra round costs one more LLM call per executive.

With 14 non-CEO members, `/board` makes 15 LLM calls and `/debate` (2 rounds)
makes 29 — expect noticeably higher latency and API cost than asking one
agent directly with `/ask`.

## Tests

```bash
pytest
```

Tests mock the Anthropic client, so no API key or network access is needed.
