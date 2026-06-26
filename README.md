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
- `/board <topic>` — convene the full board: every executive gives their take, then the CEO synthesizes a final decision with next steps
- `/roles` — list all available executives and their domains

## Architecture

- `auralith/agents/` — `Agent` dataclass (`key`, `title`, `domain`, `system_prompt`) and the nine role definitions
- `auralith/orchestrator.py` — `Orchestrator.ask()` for single-agent queries, `Orchestrator.board_meeting()` for parallel multi-agent consultation + CEO synthesis
- `auralith/bot/telegram_bot.py` — aiogram `Dispatcher` wiring Telegram commands to the orchestrator
- `auralith/main.py` — entry point; wires up the Anthropic client, orchestrator, and bot, then starts polling

Adding a new role: define an `Agent` in `auralith/agents/roles.py` and add it
to `AGENTS`. It automatically gets a `/<key>` Telegram command and joins the
board meeting.

## Tests

```bash
pytest
```

Tests mock the Anthropic client, so no API key or network access is needed.
