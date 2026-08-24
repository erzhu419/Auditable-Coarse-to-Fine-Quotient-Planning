from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp.routing_v1 import TerminalCode


def test_protocol_preregisters_exactly_one_fresh_execution_per_terminal() -> None:
    document = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()
    rows = document["production_execution_slots"]
    assert [row["terminal_code"] for row in rows] == [
        code.value for code in TerminalCode
    ]
    assert [row["ordinal"] for row in rows] == list(range(10))
    assert len({row["production_execution_slot_id"] for row in rows}) == 10
    assert len({row["execution_nonce"] for row in rows}) == 10


def test_protocol_forbids_fixture_summary_and_identity_reuse() -> None:
    document = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()
    for row in document["production_execution_slots"]:
        assert row["native_counter_record_source_required"] is True
        assert row["historical_summary_to_counter_translation_forbidden"] is True
        assert row["development_fixture_evidence_forbidden"] is True
        assert row["same_identity_rerun_after_terminal_forbidden"] is True
        assert row["producer_free_replay_required"] is True
        assert row["outcome_accessed"] is False


def test_protocol_unlocks_no_formal_gate() -> None:
    document = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()
    assert document["production_outcomes_accessed"] is False
    assert document["fresh_production_occurrence_count"] == 0
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
