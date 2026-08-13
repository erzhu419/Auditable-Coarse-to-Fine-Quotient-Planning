from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v29 as pre


def test_fourth_checkpoint_preregistration_is_outcome_free_and_exact() -> None:
    value = pre.freeze_standard_2048_expression_checkpoint_preregistration_v29()
    document = value.to_document()
    workload = document["checkpoint_workload"]
    assert document["outcome_fields_present"] is False
    assert document["checkpoint_execution_performed"] is False
    assert workload["global_decision_start_inclusive"] == 128
    assert workload["global_decision_stop_exclusive"] == 192
    assert workload["segment_decision_limit"] == 64
    assert workload["checkpoint_boards"] == [list(board) for board in pre.CHECKPOINT_BOARDS]
    assert document["sample_tax_contract"]["additional_model_acquisition_label_budget"] == 0


def test_fourth_checkpoint_cache_reset_keeps_exact_planning() -> None:
    protocol = pre.freeze_standard_2048_expression_checkpoint_preregistration_v29().to_document()[
        "exact_checkpoint_protocol"
    ]
    assert protocol["cache_not_required_to_cross_checkpoint_boundary"] is True
    assert protocol["cache_reset_changes_exact_values_or_action_selection"] is False
    assert protocol["fraction_or_precision_approximation_allowed"] is False


def test_fourth_checkpoint_identity_and_claim_locks_are_frozen() -> None:
    value = pre.freeze_standard_2048_expression_checkpoint_preregistration_v29()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    document = value.to_document()
    assert document["full_standard_2048_game_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    tampered = copy.copy(value)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(Exception):
        pre.verify_standard_2048_expression_checkpoint_preregistration_v29(tampered)
