import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auralith.agents.roles import AGENTS, CEO
from auralith.orchestrator import Orchestrator

NO_CONTEXT_PATH = "/nonexistent/company_context.md"


def make_client(text: str = "ok") -> AsyncMock:
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=SimpleNamespace(content=[SimpleNamespace(text=text)]))
    return client


def make_orchestrator(client: AsyncMock, log_path: str) -> Orchestrator:
    return Orchestrator(client, model="claude-sonnet-4-6", context_path=NO_CONTEXT_PATH, log_path=log_path)


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "decisions.log.jsonl")


def test_agents_include_expanded_specialist_roles() -> None:
    expected_keys = {
        "ceo", "coo", "cfo", "cmo", "cto", "cio", "chro", "clo", "cpo",
        "analyst", "planner", "energy", "cro", "scd", "procurement",
        "export", "quality", "engineer",
    }
    assert set(AGENTS) == expected_keys


@pytest.mark.asyncio
async def test_ask_returns_agent_text_and_uses_agent_system_prompt(log_path) -> None:
    client = make_client(text="hello from cfo")
    orchestrator = make_orchestrator(client, log_path)

    result = await orchestrator.ask(AGENTS["cfo"], "What's our runway?")

    assert result == "hello from cfo"
    client.messages.create.assert_awaited_once()
    _, kwargs = client.messages.create.call_args
    assert kwargs["system"] == AGENTS["cfo"].system_prompt
    assert kwargs["messages"] == [{"role": "user", "content": "Question:\nWhat's our runway?"}]


@pytest.mark.asyncio
async def test_ask_attaches_web_search_tool_for_web_search_agents(log_path) -> None:
    client = make_client()
    orchestrator = make_orchestrator(client, log_path)

    await orchestrator.ask(AGENTS["cfo"], "What's the official NBU rate today?")

    _, kwargs = client.messages.create.call_args
    assert kwargs["tools"] == [{"type": "web_search_20250305", "name": "web_search"}]


@pytest.mark.asyncio
async def test_ask_omits_web_search_tool_for_non_web_search_agents(log_path) -> None:
    client = make_client()
    orchestrator = make_orchestrator(client, log_path)

    await orchestrator.ask(AGENTS["coo"], "How do we tighten the ops cadence?")

    _, kwargs = client.messages.create.call_args
    assert "tools" not in kwargs


@pytest.mark.asyncio
async def test_ask_concatenates_only_text_blocks_from_response(log_path) -> None:
    client = AsyncMock()
    client.messages.create = AsyncMock(
        return_value=SimpleNamespace(
            content=[
                SimpleNamespace(type="server_tool_use", text="ignored"),
                SimpleNamespace(type="text", text="hello "),
                SimpleNamespace(type="text", text="from cfo"),
            ]
        )
    )
    orchestrator = make_orchestrator(client, log_path)

    result = await orchestrator.ask(AGENTS["cfo"], "What's our runway?")

    assert result == "hello from cfo"


@pytest.mark.asyncio
async def test_ask_includes_history_when_provided(log_path) -> None:
    client = make_client()
    orchestrator = make_orchestrator(client, log_path)

    await orchestrator.ask(
        AGENTS["cfo"],
        "And next quarter?",
        history=[("What's our runway?", "6 months at current burn.")],
    )

    _, kwargs = client.messages.create.call_args
    content = kwargs["messages"][0]["content"]
    assert "What's our runway?" in content
    assert "6 months at current burn." in content
    assert "And next quarter?" in content


@pytest.mark.asyncio
async def test_ask_includes_context_when_provided(log_path) -> None:
    client = make_client()
    orchestrator = make_orchestrator(client, log_path)

    await orchestrator.ask(AGENTS["cto"], "Should we migrate?", context="We run on legacy infra.")

    _, kwargs = client.messages.create.call_args
    content = kwargs["messages"][0]["content"]
    assert "We run on legacy infra." in content
    assert "Should we migrate?" in content


@pytest.mark.asyncio
async def test_ask_injects_company_context_file(tmp_path, log_path) -> None:
    context_file = tmp_path / "company_context.md"
    context_file.write_text("Runway: 6 months.")
    client = make_client()
    orchestrator = Orchestrator(client, model="claude-sonnet-4-6", context_path=str(context_file), log_path=log_path)

    await orchestrator.ask(AGENTS["cfo"], "Can we hire?")

    _, kwargs = client.messages.create.call_args
    content = kwargs["messages"][0]["content"]
    assert "Runway: 6 months." in content


@pytest.mark.asyncio
async def test_board_meeting_includes_all_members_and_ceo_decision(log_path) -> None:
    client = make_client(text="opinion")
    orchestrator = make_orchestrator(client, log_path)

    result = await orchestrator.board_meeting("Should we raise prices?")

    non_ceo_members = [agent for agent in AGENTS.values() if agent.key != CEO.key]
    for member in non_ceo_members:
        assert member.title in result
    assert "CEO (Final Decision)" in result
    assert client.messages.create.await_count == len(non_ceo_members) + 1


@pytest.mark.asyncio
async def test_board_meeting_records_decision_log(log_path) -> None:
    client = make_client(text="opinion")
    orchestrator = make_orchestrator(client, log_path)

    await orchestrator.board_meeting("Should we raise prices?")

    with open(log_path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]
    assert len(entries) == 1
    assert entries[0]["mode"] == "board_meeting"
    assert entries[0]["topic"] == "Should we raise prices?"
    assert "CEO (Final Decision)" in entries[0]["opinions"]


@pytest.mark.asyncio
async def test_board_debate_runs_extra_rebuttal_round_per_member(log_path) -> None:
    client = make_client(text="opinion")
    orchestrator = make_orchestrator(client, log_path)

    non_ceo_members = [agent for agent in AGENTS.values() if agent.key != CEO.key]
    result = await orchestrator.board_debate("Should we cut marketing spend?", rounds=2)

    for member in non_ceo_members:
        assert member.title in result
    assert "CEO (Final Decision)" in result
    # opening round (N) + rebuttal round (N) + CEO synthesis (1)
    assert client.messages.create.await_count == 2 * len(non_ceo_members) + 1


@pytest.mark.asyncio
async def test_board_debate_single_round_skips_rebuttal(log_path) -> None:
    client = make_client(text="opinion")
    orchestrator = make_orchestrator(client, log_path)

    non_ceo_members = [agent for agent in AGENTS.values() if agent.key != CEO.key]
    await orchestrator.board_debate("Should we cut marketing spend?", rounds=1)

    assert client.messages.create.await_count == len(non_ceo_members) + 1


@pytest.mark.asyncio
async def test_select_panel_returns_only_router_chosen_agents(log_path) -> None:
    client = make_client(text="cfo, cto")
    orchestrator = make_orchestrator(client, log_path)

    panel = await orchestrator.select_panel("Should we adopt a new payment processor?")

    assert {agent.key for agent in panel} == {"cfo", "cto"}


@pytest.mark.asyncio
async def test_select_panel_falls_back_to_all_when_router_response_unparseable(log_path) -> None:
    client = make_client(text="I'm not confident, better ask everyone on this one.")
    orchestrator = make_orchestrator(client, log_path)
    non_ceo_members = [agent for agent in AGENTS.values() if agent.key != CEO.key]

    panel = await orchestrator.select_panel("Should we raise prices?")

    assert {agent.key for agent in panel} == {agent.key for agent in non_ceo_members}


@pytest.mark.asyncio
async def test_select_panel_caps_to_max_members(log_path) -> None:
    client = make_client(text=",".join(AGENTS.keys()))
    orchestrator = make_orchestrator(client, log_path)

    panel = await orchestrator.select_panel("Should we raise prices?", max_members=3)

    assert len(panel) == 3


@pytest.mark.asyncio
async def test_smart_board_meeting_only_asks_selected_panel_members(log_path) -> None:
    client = AsyncMock()
    client.messages.create = AsyncMock(
        side_effect=[
            SimpleNamespace(content=[SimpleNamespace(text="cfo, cto")]),
            SimpleNamespace(content=[SimpleNamespace(text="cfo take")]),
            SimpleNamespace(content=[SimpleNamespace(text="cto take")]),
            SimpleNamespace(content=[SimpleNamespace(text="final decision")]),
        ]
    )
    orchestrator = make_orchestrator(client, log_path)

    result = await orchestrator.smart_board_meeting("Should we adopt a new payment processor?")

    assert AGENTS["cfo"].title in result
    assert AGENTS["cto"].title in result
    assert AGENTS["coo"].title not in result
    assert "CEO (Final Decision)" in result
    assert client.messages.create.await_count == 4


@pytest.mark.asyncio
async def test_smart_board_meeting_logs_decision_with_smart_board_mode(log_path) -> None:
    client = AsyncMock()
    client.messages.create = AsyncMock(
        side_effect=[
            SimpleNamespace(content=[SimpleNamespace(text="cfo")]),
            SimpleNamespace(content=[SimpleNamespace(text="cfo take")]),
            SimpleNamespace(content=[SimpleNamespace(text="final decision")]),
        ]
    )
    orchestrator = make_orchestrator(client, log_path)

    await orchestrator.smart_board_meeting("Should we raise prices?")

    with open(log_path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]
    assert len(entries) == 1
    assert entries[0]["mode"] == "smart_board"
