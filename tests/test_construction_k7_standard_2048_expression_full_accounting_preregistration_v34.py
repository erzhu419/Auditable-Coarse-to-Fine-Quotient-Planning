from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp import construction_k7_standard_2048_expression_full_accounting_preregistration_v34 as pre


@pytest.fixture(scope="module")
def frozen():
    return pre.freeze_standard_2048_expression_full_accounting_preregistration_v34()


def test_complete_campaign_accounting_plan_is_frozen(frozen) -> None:
    document = frozen.to_document()
    segments = document["registered_segment_plan"]
    assert len(segments) == 9
    assert [row["expected_new_decision_count"] for row in segments] == [
        128,
        128,
        128,
        128,
        256,
        512,
        938,
        765,
        204,
    ]
    assert sum(row["expected_new_decision_count"] for row in segments) == 3187
    campaign = document["registered_complete_campaign"]
    assert campaign["logical_occurrence_count"] == 4
    assert campaign["expected_won_occurrence_count"] == 2
    assert campaign["expected_lost_occurrence_count"] == 2
    assert campaign["terminal_occurrences_remain_in_all_denominators"] is True


def test_complete_accounting_requires_native_windows_not_summary_translation(
    frozen,
) -> None:
    document = frozen.to_document()
    protocol = document["actual_accounting_protocol"]
    assert protocol["fresh_native_counter_window_required_for_every_segment"] is True
    assert protocol["summary_to_counter_translation_allowed"] is False
    assert protocol["all_required_leaves_emit_native_zero"] is True
    assert protocol["shared_resource_paths"] == list(pre.SHARED_RESOURCE_PATHS)
    assert len(protocol["shared_resource_paths"]) == 9


def test_complete_accounting_identity_and_claim_locks_are_frozen(frozen) -> None:
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    document = frozen.to_document()
    assert document["outcome_fields_present"] is False
    assert document["full_accounting_execution_performed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    tampered = copy.copy(frozen)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(Exception):
        pre.verify_standard_2048_expression_full_accounting_preregistration_v34(
            tampered
        )
