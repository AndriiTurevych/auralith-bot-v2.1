import os

DEFAULT_CONTEXT_PATH = "company_context.md"


def load_company_context(path: str | None = None) -> str:
    """Read the human-edited company context file, if it exists."""
    resolved_path = path or os.environ.get("COMPANY_CONTEXT_PATH", DEFAULT_CONTEXT_PATH)
    if not os.path.exists(resolved_path):
        return ""
    with open(resolved_path, encoding="utf-8") as f:
        return f.read().strip()
