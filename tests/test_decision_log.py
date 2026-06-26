from auralith import decision_log


def test_list_decisions_returns_empty_when_file_missing(tmp_path) -> None:
    path = str(tmp_path / "missing.jsonl")

    assert decision_log.list_decisions(path=path) == []


def test_record_and_list_decisions_round_trip(tmp_path) -> None:
    path = str(tmp_path / "decisions.log.jsonl")

    decision_log.record_decision("Topic A", {"CEO (Final Decision)": "Go for it"}, mode="board_meeting", path=path)
    decision_log.record_decision("Topic B", {"CEO (Final Decision)": "Hold off"}, mode="board_debate", path=path)

    entries = decision_log.list_decisions(limit=5, path=path)

    assert [entry["topic"] for entry in entries] == ["Topic A", "Topic B"]
    assert entries[1]["mode"] == "board_debate"


def test_list_decisions_respects_limit(tmp_path) -> None:
    path = str(tmp_path / "decisions.log.jsonl")
    for i in range(10):
        decision_log.record_decision(f"Topic {i}", {"CEO (Final Decision)": "x"}, mode="board_meeting", path=path)

    entries = decision_log.list_decisions(limit=3, path=path)

    assert [entry["topic"] for entry in entries] == ["Topic 7", "Topic 8", "Topic 9"]
