# Auralith Bot v2.1 — C-Suite Agents

A multi-agent system that simulates a company's executive leadership team using
Claude. Each role is an independent agent with its own domain, expertise, and
decision-making style. A Telegram bot exposes them for one-off advice or a
full "board meeting" where every executive weighs in and the CEO synthesizes
a final decision.

## Roles

| Command | Role | Domain | Web search |
|---|---|---|---|
| `/ceo` | CEO | Strategy, vision, resource allocation, final decisions | |
| `/coo` | COO | Operations, execution, delivery | |
| `/cfo` | CFO | Budget, cash flow, unit economics, financial risk | ✅ |
| `/cmo` | CMO | Marketing, brand, growth, acquisition | ✅ |
| `/cto` | CTO | Technology strategy, architecture, engineering | |
| `/cio` | CIO | Internal IT, infrastructure, data governance, security | |
| `/chro` | CHRO | People, hiring, org design, culture | |
| `/clo` | CLO | Legal risk, contracts, compliance | ✅ |
| `/cpo` | CPO | Product strategy, roadmap, UX | |
| `/analyst` | Chief Analytics Officer | Data analysis, reporting, forecasting | ✅ |
| `/planner` | Production Planning Director | Production scheduling, capacity, bottlenecks | |
| `/energy` | Energy Manager | Power supply, grid resilience, backup power | ✅ |
| `/cro` | Chief Risk Officer | Enterprise risk, war/sanctions/FX risk, insurance | ✅ |
| `/scd` | Supply Chain Director | Logistics, customs, supplier networks | ✅ |
| `/procurement` | Procurement Specialist | Sourcing, vendor negotiation, procurement law | ✅ |
| `/export` | Export Sales Director | International distribution, export channels, route-to-market | ✅ |
| `/quality` | Quality Director | Product quality, lab testing, certification | ✅ |
| `/engineer` | Chief Engineer | Plant engineering, equipment reliability, capital construction | |

All agents default to Ukrainian and reason from Ukrainian legal, tax, and
regulatory context (martial law, NBU currency controls, Prozorro public
procurement, customs, NEURC energy regulation, etc.) instead of generic
Western assumptions. They reply in whatever language you write in.

## Web search

Roles whose advice depends on facts that go stale (FX rates, tariffs,
sanctions lists, regulations, market/competitor news) get Claude's built-in
web search tool, marked ✅ above. Anthropic runs the actual search
server-side — Auralith just declares the tool on the request and the agent's
system prompt instructs it to search before stating any time-sensitive
number or claim, cross-check it against another source, and say plainly when
something couldn't be verified instead of guessing. Other roles (CEO, COO,
CTO, CIO, CHRO, CPO, Production Planning Director, Chief Engineer) reason
from company context and domain expertise only — their calls are more about
internal trade-offs than external facts, so they skip the extra round trip.

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
- `/<role> <question>` — shortcut for the above, e.g. `/cto Should we migrate to microservices?`. Each role remembers the last few exchanges in that chat, so follow-ups build on prior context.
- `/board <topic>` — a router pass picks the executives actually relevant to the topic (cheaper, faster than asking all 17), they give their take in parallel, then the CEO synthesizes a final decision with next steps
- `/fullboard <topic>` — same as `/board`, but every executive weighs in regardless of relevance — use it when you genuinely want exhaustive coverage
- `/debate <topic>` — full board debate: every executive sees the others' positions and gets a rebuttal round before the CEO synthesizes (more API calls, sharper conflict)
- `/context` — show the company context currently injected into every agent prompt
- `/log` — show the last 5 logged board/debate decisions
- `/roles` — list all available executives and their domains
- `/reset` — clear this chat's conversation memory with every executive

## Company context

`company_context.md` (repo root) is automatically read and injected into
every agent prompt — edit it with real metrics, stage, priorities, and
constraints so advice is grounded instead of generic. Override the path with
`COMPANY_CONTEXT_PATH`. If the file is missing, agents just get the question
with no company context.

## Decision log

Every `/board`, `/fullboard`, and `/debate` run is appended as a JSON line to
`decisions.log.jsonl` (path override: `DECISION_LOG_PATH`) with a timestamp,
mode (`smart_board`, `board_meeting`, or `board_debate`), topic, every
executive's position, and the CEO's final decision. This file is gitignored
— treat it as runtime data, not source.

## Conversation memory

Each `/ask`/`/<role>` conversation keeps the last `MEMORY_TURNS` (default `4`)
question/answer exchanges per chat per role, so a follow-up like "and what
about next quarter?" carries context from the prior answer. Memory is
in-process only (cleared on bot restart) and scoped per Telegram chat — use
`/reset` to clear it manually.

## Architecture

- `auralith/agents/` — `Agent` dataclass (`key`, `title`, `domain`, `system_prompt`, `web_search`) and the role definitions
- `auralith/company_context.py` — loads `company_context.md` (or the configured path) as a string
- `auralith/decision_log.py` — appends/reads board decisions as JSONL
- `auralith/memory.py` — `ConversationMemory`, an in-process per-(chat, role) rolling history used to give `/ask` follow-ups context
- `auralith/orchestrator.py` — `Orchestrator.ask()` for single-agent queries (auto-injects company context and optional conversation history; attaches Claude's web search tool when `agent.web_search` is set); `Orchestrator.select_panel()` asks a lightweight router call to pick the executives relevant to a topic; `Orchestrator.smart_board_meeting()` runs `board_meeting()` against that router-selected panel; `Orchestrator.board_meeting()` runs the full (or a given) set of agents in parallel + CEO synthesis; `Orchestrator.board_debate()` is multi-round rebuttal before synthesis. All meeting modes log to the decision log.
- `auralith/bot/telegram_bot.py` — aiogram `Dispatcher` wiring Telegram commands to the orchestrator
- `auralith/main.py` — entry point; wires up the Anthropic client, orchestrator, conversation memory, and bot, then starts polling

Adding a new role: define an `Agent` in `auralith/agents/roles.py` and add it
to `AGENTS`. It automatically gets a `/<key>` Telegram command and joins the
board meeting, smart board routing, and debate.

Tuning debate depth: `DEBATE_ROUNDS` (default `2` — one opening round plus
one rebuttal round). Each extra round costs one more LLM call per executive.

Tuning smart-board panel size: `BOARD_PANEL_SIZE` (default `6`) caps how many
executives the router can select for `/board`. If the router's response
doesn't parse to any known role, `select_panel` falls back to the full
roster rather than silently asking nobody.

With 17 non-CEO members, `/fullboard` makes 18 LLM calls and `/debate`
(2 rounds) makes 35 — expect noticeably higher latency and API cost than
`/board` (router call + up to `BOARD_PANEL_SIZE` executives + CEO synthesis)
or asking one agent directly with `/ask`.

## Tests

```bash
pytest
```

Tests mock the Anthropic client, so no API key or network access is needed.
