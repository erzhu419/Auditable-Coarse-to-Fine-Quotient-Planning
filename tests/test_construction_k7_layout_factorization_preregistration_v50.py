from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_layout_factorization_preregistration_v50 as pre


def test_v50_preregistration_is_outcome_free_and_content_addressed() -> None:
    frozen = pre.freeze_layout_factorization_preregistration_v50()
    assert pre.verify_layout_factorization_preregistration_v50(frozen) is frozen
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    document = frozen.to_document()
    assert document["fresh_v50_registered_outcome_execution_performed"] is False
    assert document["raw_interface"]["layout_positions_preregistered"] is False
    assert document["source_closure"]["frozen_before_any_v50_registered_source_or_target_outcome"] is True


def test_v50_preregisters_two_fresh_stochastic_families_and_sample_tax_gate() -> None:
    document = pre.freeze_layout_factorization_preregistration_v50().to_document()
    workload = document["fresh_workload"]
    all_seeds = (
        workload["modular_source_seeds"]
        + workload["modular_target_seeds"]
        + workload["inventory_source_seeds"]
        + workload["inventory_target_seeds"]
    )
    assert len(all_seeds) == len(set(all_seeds)) == 22
    assert workload["matched_target_occurrence_count"] == 16
    assert document["required_positive_conditions"][-1] == (
        "OFFLINE_PLUS_STRUCTURAL_TARGET_LABELS_STRICTLY_LESS_THAN_STRICT_TARGET_LABELS"
    )
    assert document["acquisition_and_recovery_protocol"]["maximum_target_layout_labels_per_occurrence"] == 16


def test_v50_source_closure_and_claim_locks_are_exact() -> None:
    document = pre.freeze_layout_factorization_preregistration_v50().to_document()
    facts = document["source_closure"]["source_facts"]
    assert [row["relative_path"] for row in facts] == list(pre.BOUND_SOURCE_PATHS)
    for row in facts:
        raw = (pre.SOURCE_ROOT / row["relative_path"]).read_bytes()
        assert len(raw) == row["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    boundary = document["claim_boundary"]
    assert boundary["official_execution_allowed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["official_N_break_even"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert boundary["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v50_preregistration_rejects_foreign_values_and_mutation() -> None:
    frozen = pre.freeze_layout_factorization_preregistration_v50()
    with pytest.raises(pre.ConstructionK7LayoutFactorizationPreregistrationV50Error):
        pre.LayoutFactorizationPreregistrationV50(
            object(), frozen.canonical_bytes, frozen.preregistration_id
        )
    object.__setattr__(frozen, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7LayoutFactorizationPreregistrationV50Error):
        pre.verify_layout_factorization_preregistration_v50(frozen)
