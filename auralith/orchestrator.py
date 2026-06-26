import asyncio

from anthropic import AsyncAnthropic

from .agents.base import Agent
from .agents.roles import AGENTS, CEO

MAX_TOKENS = 2048


class Orchestrator:
    def __init__(self, client: AsyncAnthropic, model: str):
        self._client = client
        self._model = model

    async def ask(self, agent: Agent, question: str, context: str = "") -> str:
        user_content = question if not context else f"Context:\n{context}\n\nQuestion:\n{question}"
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=agent.system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text

    async def board_meeting(self, topic: str) -> dict[str, str]:
        members = [agent for agent in AGENTS.values() if agent.key != CEO.key]
        opinions = await asyncio.gather(*(self.ask(member, topic) for member in members))
        opinions_by_role = {member.title: opinion for member, opinion in zip(members, opinions)}

        synthesis_input = "\n\n".join(f"{title}:\n{opinion}" for title, opinion in opinions_by_role.items())
        synthesis_question = (
            f"The board discussed the following topic: {topic}\n\n"
            f"Here is what each executive said:\n\n{synthesis_input}\n\n"
            "As CEO, synthesize these perspectives into a final decision with clear next steps."
        )
        decision = await self.ask(CEO, synthesis_question)
        opinions_by_role["CEO (Final Decision)"] = decision
        return opinions_by_role
