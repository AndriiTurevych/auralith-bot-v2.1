from collections import deque

DEFAULT_MAX_TURNS = 4


class ConversationMemory:
    def __init__(self, max_turns: int = DEFAULT_MAX_TURNS):
        self._max_turns = max_turns
        self._histories: dict[tuple[int, str], deque[tuple[str, str]]] = {}

    def get(self, chat_id: int, role_key: str) -> list[tuple[str, str]]:
        return list(self._histories.get((chat_id, role_key), ()))

    def add(self, chat_id: int, role_key: str, question: str, answer: str) -> None:
        key = (chat_id, role_key)
        history = self._histories.setdefault(key, deque(maxlen=self._max_turns))
        history.append((question, answer))

    def reset(self, chat_id: int) -> None:
        for key in [k for k in self._histories if k[0] == chat_id]:
            del self._histories[key]
