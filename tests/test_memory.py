from auralith.memory import ConversationMemory


def test_memory_returns_empty_history_for_new_chat() -> None:
    memory = ConversationMemory()
    assert memory.get(1, "cfo") == []


def test_memory_stores_and_returns_exchanges_in_order() -> None:
    memory = ConversationMemory()
    memory.add(1, "cfo", "Q1", "A1")
    memory.add(1, "cfo", "Q2", "A2")
    assert memory.get(1, "cfo") == [("Q1", "A1"), ("Q2", "A2")]


def test_memory_is_isolated_per_chat_and_role() -> None:
    memory = ConversationMemory()
    memory.add(1, "cfo", "Q1", "A1")
    memory.add(2, "cfo", "Q2", "A2")
    memory.add(1, "cto", "Q3", "A3")

    assert memory.get(1, "cfo") == [("Q1", "A1")]
    assert memory.get(2, "cfo") == [("Q2", "A2")]
    assert memory.get(1, "cto") == [("Q3", "A3")]


def test_memory_caps_history_to_max_turns() -> None:
    memory = ConversationMemory(max_turns=2)
    memory.add(1, "cfo", "Q1", "A1")
    memory.add(1, "cfo", "Q2", "A2")
    memory.add(1, "cfo", "Q3", "A3")

    assert memory.get(1, "cfo") == [("Q2", "A2"), ("Q3", "A3")]


def test_memory_reset_clears_all_roles_for_chat_but_not_other_chats() -> None:
    memory = ConversationMemory()
    memory.add(1, "cfo", "Q1", "A1")
    memory.add(1, "cto", "Q2", "A2")
    memory.add(2, "cfo", "Q3", "A3")

    memory.reset(1)

    assert memory.get(1, "cfo") == []
    assert memory.get(1, "cto") == []
    assert memory.get(2, "cfo") == [("Q3", "A3")]
