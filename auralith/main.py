import asyncio
import logging

from aiogram import Bot
from anthropic import AsyncAnthropic

from .bot.telegram_bot import build_dispatcher
from .config import load_settings
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
    )

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = build_dispatcher(orchestrator)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
