from aiogram import Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from .. import decision_log
from ..agents.base import Agent
from ..agents.roles import AGENTS
from ..memory import ConversationMemory
from ..orchestrator import Orchestrator

HELP_TEXT = (
    "Auralith C-Suite Bot\n\n"
    "/ask <role> <question> - get a perspective from one executive\n"
    "/board <question> - convene the executives relevant to the topic and get a synthesized decision\n"
    "/fullboard <question> - same as /board, but every executive weighs in\n"
    "/debate <question> - board debate: executives rebut each other before the CEO decides\n"
    "/context - show the current company context fed to every agent\n"
    "/log - show the last 5 board decisions\n"
    "/roles - list available executives\n"
    "/reset - clear this chat's conversation memory with every executive\n"
    "/<role> <question> - shortcut, e.g. /cfo What's our runway?\n\n"
    "Available roles: " + ", ".join(sorted(AGENTS))
)


def build_dispatcher(orchestrator: Orchestrator, memory: ConversationMemory | None = None) -> Dispatcher:
    dp = Dispatcher()
    memory = memory if memory is not None else ConversationMemory()

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
        await _answer_as(message, orchestrator, memory, agent, question)

    async def handle_board(message: Message) -> None:
        args = (message.text or "").split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Usage: /board <topic>\nExample: /board Should we raise prices by 10%?")
            return
        topic = args[1]
        await message.answer("Selecting the relevant executives...")
        opinions = await orchestrator.smart_board_meeting(topic)
        for title, opinion in opinions.items():
            await message.answer(f"{title}:\n{opinion}")

    async def handle_full_board(message: Message) -> None:
        args = (message.text or "").split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Usage: /fullboard <topic>\nExample: /fullboard Should we raise prices by 10%?")
            return
        topic = args[1]
        await message.answer("Convening the full board...")
        opinions = await orchestrator.board_meeting(topic)
        for title, opinion in opinions.items():
            await message.answer(f"{title}:\n{opinion}")

    async def handle_debate(message: Message) -> None:
        args = (message.text or "").split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Usage: /debate <topic>\nExample: /debate Should we cut the marketing budget?")
            return
        topic = args[1]
        await message.answer("Opening the floor for debate...")
        positions = await orchestrator.board_debate(topic)
        for title, opinion in positions.items():
            await message.answer(f"{title}:\n{opinion}")

    async def handle_context(message: Message) -> None:
        context = orchestrator.company_context()
        await message.answer(context if context else "No company context file found.")

    async def handle_log(message: Message) -> None:
        entries = decision_log.list_decisions(limit=5)
        if not entries:
            await message.answer("No decisions logged yet.")
            return
        for entry in entries:
            decision = entry["opinions"].get("CEO (Final Decision)", "")
            await message.answer(
                f"[{entry['timestamp']}] ({entry['mode']}) {entry['topic']}\n\nCEO decision:\n{decision}"
            )

    async def handle_reset(message: Message) -> None:
        memory.reset(message.chat.id)
        await message.answer("Conversation memory cleared for this chat.")

    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_start, Command("help"))
    dp.message.register(handle_roles, Command("roles"))
    dp.message.register(handle_ask, Command("ask"))
    dp.message.register(handle_board, Command("board"))
    dp.message.register(handle_full_board, Command("fullboard"))
    dp.message.register(handle_debate, Command("debate"))
    dp.message.register(handle_context, Command("context"))
    dp.message.register(handle_log, Command("log"))
    dp.message.register(handle_reset, Command("reset"))

    for key, agent in AGENTS.items():
        dp.message.register(_make_role_handler(orchestrator, memory, agent), Command(key))

    return dp


def _make_role_handler(orchestrator: Orchestrator, memory: ConversationMemory, agent: Agent):
    async def handler(message: Message) -> None:
        args = (message.text or "").split(maxsplit=1)
        if len(args) < 2:
            await message.answer(f"Usage: /{agent.key} <question>")
            return
        await _answer_as(message, orchestrator, memory, agent, args[1])

    return handler


async def _answer_as(message: Message, orchestrator: Orchestrator, memory: ConversationMemory, agent: Agent, question: str) -> None:
    await message.answer(f"{agent.title} is thinking...")
    history = memory.get(message.chat.id, agent.key)
    answer = await orchestrator.ask(agent, question, history=history)
    memory.add(message.chat.id, agent.key, question, answer)
    await message.answer(f"{agent.title}:\n{answer}")
