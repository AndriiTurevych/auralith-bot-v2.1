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
