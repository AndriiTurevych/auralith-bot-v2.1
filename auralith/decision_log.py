import json
import os
from datetime import datetime, timezone

DEFAULT_LOG_PATH = "decisions.log.jsonl"


def record_decision(
    topic: str,
    opinions: dict[str, str],
    mode: str,
    path: str | None = None,
) -> None:
    resolved_path = path or os.environ.get("DECISION_LOG_PATH", DEFAULT_LOG_PATH)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "topic": topic,
        "opinions": opinions,
    }
    with open(resolved_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_decisions(limit: int = 5, path: str | None = None) -> list[dict]:
    resolved_path = path or os.environ.get("DECISION_LOG_PATH", DEFAULT_LOG_PATH)
    if not os.path.exists(resolved_path):
        return []
    with open(resolved_path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    return entries[-limit:]
