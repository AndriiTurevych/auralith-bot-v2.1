import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    telegram_bot_token: str
    model: str = "claude-sonnet-4-6"


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        model=os.environ.get("AURALITH_MODEL", "claude-sonnet-4-6"),
    )
