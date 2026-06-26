from aiogram import Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from ..agents.base import Agent
from ..agents.roles import AGENTS
from ..orchestrator import Orchestrator

HELP_TEXT = (
    "Auralith C-Suite Bot\n\n"
    "/ask <role> <question> - get a perspective from one executive\n"
    "/board <question> - convene the full board and get a synthesized decision\n"
    "/roles - list available executives\n"
    "/<role> <question> - shortcut, e.g. /cfo What's our runway?\n\n"
    "Available roles: " + ", ".join(sorted(AGENTS))
)


def build_dispatcher(orchestrator: Orchestrator) -> Dispatcher:
    dp = Dispatcher()

    async def handle_start(message: Message) -> None:
        await message.answer(HELP_TEXT)

    async def handle_roles(message: Message) -> None:
        lines = [f"/{key} - {agent.title}: {agent.domain}" for key, agent in sorted(AGENTS.items())]
        await message.answer("\n".join(lines))

    async def handle_ask(message: Message) -> None:
        args = (message.text or "").split(maxsplit=2)
        if len(args) < 3:
            await message.answer("Usage: /ask <role> <question>\nExample: /ask cfo What's our cash runway?")
            return
        role_key, question = args[1].lower(), args[2]
        agent = AGENTS.get(role_key)
        if agent is None:
            await message.answer(f"Unknown role '{role_key}'. Use /roles to see options.")
            return
        await _answer_as(message, orchestrator, agent, question)

    async def handle_board(message: Message) -> None:
        args = (message.text or "").split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Usage: /board <topic>\nExample: /board Should we raise prices by 10%?")
            return
        topic = args[1]
        await message.answer("Convening the board...")
        opinions = await orchestrator.board_meeting(topic)
        for title, opinion in opinions.items():
            await message.answer(f"{title}:\n{opinion}")

    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_start, Command("help"))
    dp.message.register(handle_roles, Command("roles"))
    dp.message.register(handle_ask, Command("ask"))
    dp.message.register(handle_board, Command("board"))

    for key, agent in AGENTS.items():
        dp.message.register(_make_role_handler(orchestrator, agent), Command(key))

    return dp


def _make_role_handler(orchestrator: Orchestrator, agent: Agent):
    async def handler(message: Message) -> None:
        args = (message.text or "").split(maxsplit=1)
        if len(args) < 2:
            await message.answer(f"Usage: /{agent.key} <question>")
            return
        await _answer_as(message, orchestrator, agent, args[1])

    return handler


async def _answer_as(message: Message, orchestrator: Orchestrator, agent: Agent, question: str) -> None:
    await message.answer(f"{agent.title} is thinking...")
    answer = await orchestrator.ask(agent, question)
    await message.answer(f"{agent.title}:\n{answer}")
