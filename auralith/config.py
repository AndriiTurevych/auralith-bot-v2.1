import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    telegram_bot_token: str
    model: str = "claude-sonnet-4-6"
    company_context_path: str = "company_context.md"
    decision_log_path: str = "decisions.log.jsonl"
    debate_rounds: int = 2
    board_panel_size: int = 6
    memory_turns: int = 4


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        model=os.environ.get("AURALITH_MODEL", "claude-sonnet-4-6"),
        company_context_path=os.environ.get("COMPANY_CONTEXT_PATH", "company_context.md"),
        decision_log_path=os.environ.get("DECISION_LOG_PATH", "decisions.log.jsonl"),
        debate_rounds=int(os.environ.get("DEBATE_ROUNDS", "2")),
        board_panel_size=int(os.environ.get("BOARD_PANEL_SIZE", "6")),
        memory_turns=int(os.environ.get("MEMORY_TURNS", "4")),
    )
