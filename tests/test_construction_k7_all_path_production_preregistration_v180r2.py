from acfqp import construction_k7_all_path_production_preregistration_v180r2 as prereg
from acfqp.routing_v1 import TerminalCode


def test_all_ten_production_occurrence_slots_are_frozen_before_outcomes() -> None:
    document = prereg.freeze_all_path_production_preregistration_v180r2().to_document()
    assert document["ordered_terminal_codes"] == [code.value for code in TerminalCode]
    assert document["ordered_denominator"] == 10
    assert len(document["terminal_occurrence_slots"]) == 10
    assert len({row["occurrence_slot_id"] for row in document["terminal_occurrence_slots"]}) == 10
    assert document["production_outcomes_accessed"] is False
    assert document["fresh_production_occurrence_count"] == 0


def test_every_slot_requires_fresh_v9_chain_and_exact_evidence_roles() -> None:
    document = prereg.freeze_all_path_production_preregistration_v180r2().to_document()
    for row in document["terminal_occurrence_slots"]:
        assert row["fresh_occurrence_required"] is True
        assert row["historical_or_fixture_evidence_forbidden"] is True
        assert row["counter_registry_version_required"] == "9.0.0"
        assert row["counter_record_work_vector_comparison_vector_required"] is True
        assert row["output_fixed_point_required"] is True
        assert row["outcome_accessed"] is False
        assert len(row["required_evidence_roles"]) >= 7


def test_preregistration_does_not_unlock_formal_gates() -> None:
    document = prereg.freeze_all_path_production_preregistration_v180r2().to_document()
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
