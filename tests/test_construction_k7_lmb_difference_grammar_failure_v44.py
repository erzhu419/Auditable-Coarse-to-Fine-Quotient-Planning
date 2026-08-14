from __future__ import annotations

import hashlib

from acfqp import construction_k7_lmb_difference_grammar_failure_v44 as failure
from acfqp import construction_k7_lmb_difference_grammar_preregistration_v44 as pre


def test_v44_preserves_exact_preregistered_source_coverage_failure() -> None:
    frozen = failure.freeze_lmb_difference_grammar_failure_v44()
    assert frozen.failure_id == failure.EXPECTED_FAILURE_ID
    assert len(frozen.canonical_bytes) == failure.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        failure.EXPECTED_CANONICAL_SHA256
    )
    replay = failure.freeze_lmb_difference_grammar_failure_v44()
    assert replay.canonical_bytes == frozen.canonical_bytes
    document = frozen.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["offline_source_transition_label_count"] == 42
    assert document["target_episode_execution_count"] == 0
    assert document["failure_code"] == (
        "PREREGISTERED_SOURCE_SUCCESS_COVERAGE_NOT_OBSERVED"
    )
    assert document["status"] == "TYPED_PREREGISTERED_COVERAGE_FAILURE"
    assert all(
        row["source_generation_witness_accessed"] is False
        for row in document["raw_observations"]
    )


def test_v44_failure_is_specific_and_keeps_all_gates_locked() -> None:
    document = failure.freeze_lmb_difference_grammar_failure_v44().to_document()
    facts = document["coverage_facts"]
    assert facts == {
        "active_at_capacity_observed": True,
        "failure_one_above_capacity_observed": True,
        "increment_difference_observed": True,
        "operated_component_join_observed": True,
        "rewrite_difference_observed": True,
        "success_on_full_removal_observed": False,
    }
    assert len(document["source_episode_closures"]) == 5
    assert all(
        row["terminal_status"] == "failure"
        for row in document["source_episode_closures"]
    )
    assert document["failure_preserved_before_successor_preregistration"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
