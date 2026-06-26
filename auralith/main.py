import asyncio
import logging

from aiogram import Bot
from anthropic import AsyncAnthropic

from .bot.telegram_bot import build_dispatcher
from .config import load_settings
from .memory import ConversationMemory
from .orchestrator import Orchestrator


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()

    anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    orchestrator = Orchestrator(
        anthropic_client,
        settings.model,
        context_path=settings.company_context_path,
        log_path=settings.decision_log_path,
        panel_size=settings.board_panel_size,
    )
    memory = ConversationMemory(max_turns=settings.memory_turns)

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = build_dispatcher(orchestrator, memory)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
