import asyncio

from anthropic import AsyncAnthropic

from . import decision_log
from .agents.base import Agent
from .agents.roles import AGENTS, CEO
from .company_context import load_company_context

MAX_TOKENS = 2048
DEFAULT_DEBATE_ROUNDS = 2


class Orchestrator:
    def __init__(
        self,
        client: AsyncAnthropic,
        model: str,
        context_path: str | None = None,
        log_path: str | None = None,
    ):
        self._client = client
        self._model = model
        self._context_path = context_path
        self._log_path = log_path

    def company_context(self) -> str:
        return load_company_context(self._context_path)

    async def ask(self, agent: Agent, question: str, context: str = "") -> str:
        parts = []
        company_context = self.company_context()
        if company_context:
            parts.append(f"Company context:\n{company_context}")
        if context:
            parts.append(f"Additional context:\n{context}")
        parts.append(f"Question:\n{question}")
        user_content = "\n\n".join(parts)

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

        decision = await self._synthesize(topic, opinions_by_role, debated=False)
        opinions_by_role["CEO (Final Decision)"] = decision

        decision_log.record_decision(topic, opinions_by_role, mode="board_meeting", path=self._log_path)
        return opinions_by_role

    async def board_debate(self, topic: str, rounds: int = DEFAULT_DEBATE_ROUNDS) -> dict[str, str]:
        members = [agent for agent in AGENTS.values() if agent.key != CEO.key]

        opening = await asyncio.gather(*(self.ask(member, topic) for member in members))
        positions = {member.title: opinion for member, opinion in zip(members, opening)}

        for round_number in range(2, rounds + 1):
            updated = await asyncio.gather(*(self._rebut(member, topic, positions, round_number) for member in members))
            positions = {member.title: opinion for member, opinion in zip(members, updated)}

        decision = await self._synthesize(topic, positions, debated=True)
        positions["CEO (Final Decision)"] = decision

        decision_log.record_decision(topic, positions, mode="board_debate", path=self._log_path)
        return positions

    async def _rebut(self, agent: Agent, topic: str, positions: dict[str, str], round_number: int) -> str:
        others = "\n\n".join(
            f"{title}: {opinion}" for title, opinion in positions.items() if title != agent.title
        )
        prompt = (
            f"Topic: {topic}\n\n"
            f"Round {round_number - 1} positions from the other executives:\n\n{others}\n\n"
            f"Your previous position:\n{positions[agent.title]}\n\n"
            "Respond to what the others said. Defend your position, concede where they're right, "
            "or sharpen your disagreement. Do not just repeat yourself."
        )
        return await self.ask(agent, prompt)

    async def _synthesize(self, topic: str, opinions_by_role: dict[str, str], debated: bool) -> str:
        opinions_text = "\n\n".join(f"{title}:\n{opinion}" for title, opinion in opinions_by_role.items())
        verb = "debated" if debated else "discussed"
        synthesis_question = (
            f"The board {verb} the following topic: {topic}\n\n"
            f"Here is what each executive said (final positions):\n\n{opinions_text}\n\n"
            "As CEO, synthesize these perspectives into a final decision with clear next steps."
        )
        return await self.ask(CEO, synthesis_question)
