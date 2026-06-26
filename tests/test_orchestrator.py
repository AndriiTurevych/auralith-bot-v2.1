from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auralith.agents.roles import AGENTS, CEO
from auralith.orchestrator import Orchestrator


def make_client(text: str = "ok") -> AsyncMock:
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=SimpleNamespace(content=[SimpleNamespace(text=text)]))
    return client


@pytest.mark.asyncio
async def test_ask_returns_agent_text_and_uses_agent_system_prompt() -> None:
    client = make_client(text="hello from cfo")
    orchestrator = Orchestrator(client, model="claude-sonnet-4-6")

    result = await orchestrator.ask(AGENTS["cfo"], "What's our runway?")

    assert result == "hello from cfo"
    client.messages.create.assert_awaited_once()
    _, kwargs = client.messages.create.call_args
    assert kwargs["system"] == AGENTS["cfo"].system_prompt
    assert kwargs["messages"] == [{"role": "user", "content": "What's our runway?"}]


@pytest.mark.asyncio
async def test_ask_includes_context_when_provided() -> None:
    client = make_client()
    orchestrator = Orchestrator(client, model="claude-sonnet-4-6")

    await orchestrator.ask(AGENTS["cto"], "Should we migrate?", context="We run on legacy infra.")

    _, kwargs = client.messages.create.call_args
    content = kwargs["messages"][0]["content"]
    assert "We run on legacy infra." in content
    assert "Should we migrate?" in content


@pytest.mark.asyncio
async def test_board_meeting_includes_all_members_and_ceo_decision() -> None:
    client = make_client(text="opinion")
    orchestrator = Orchestrator(client, model="claude-sonnet-4-6")

    result = await orchestrator.board_meeting("Should we raise prices?")

    non_ceo_members = [agent for agent in AGENTS.values() if agent.key != CEO.key]
    for member in non_ceo_members:
        assert member.title in result
    assert "CEO (Final Decision)" in result
    assert client.messages.create.await_count == len(non_ceo_members) + 1
