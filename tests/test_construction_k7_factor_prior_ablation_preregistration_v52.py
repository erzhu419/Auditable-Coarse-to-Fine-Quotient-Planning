from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_factor_prior_ablation_preregistration_v52 as pre


def test_v52_preregistration_is_frozen_and_content_addressed() -> None:
    frozen = pre.freeze_factor_prior_ablation_preregistration_v52()
    assert pre.verify_factor_prior_ablation_preregistration_v52(frozen) is frozen
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256


def test_v52_preregisters_ground_distinct_matched_acquisition() -> None:
    document = pre.freeze_factor_prior_ablation_preregistration_v52().to_document()
    assert document["target_domain"][
        "ground_semantics_distinct_from_v51_coupled_exchange"
    ] is True
    assert document["target_domain"]["semantic_bridge_available_to_constructor"] is False
    matched = document["matched_acquisition_arms"]
    assert matched["no_prior_arm_factor_library_access_forbidden"] is True
    assert matched["no_prior_arm_compiled_prior_access_forbidden"] is True
    assert matched["same_ground_kernel_seed_initial_state_and_outcome_tape_schedule"] is True


def test_v52_preregisters_full_historical_sample_tax() -> None:
    document = pre.freeze_factor_prior_ablation_preregistration_v52().to_document()
    tax = document["sample_tax_contract"]
    assert tax["historical_factor_prior_labels"] == 583
    assert tax["historical_prior_cost_included_before_first_target_occurrence"] is True
    assert tax["individual_factor_only_causal_effect_claimed"] is False
    assert tax["maximum_registered_break_even_occurrences"] == 16


def test_v52_preregistration_is_outcome_free_and_gates_stay_locked() -> None:
    document = pre.freeze_factor_prior_ablation_preregistration_v52().to_document()
    assert document["fresh_v52_registered_outcome_execution_performed"] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["official_N_break_even"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["claim_boundary"]["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v52_preregistration_source_closure_is_complete() -> None:
    document = pre.freeze_factor_prior_ablation_preregistration_v52().to_document()
    facts = document["source_closure"]["source_facts"]
    assert [row["relative_path"] for row in facts] == list(pre.BOUND_SOURCE_PATHS)
    assert all(row["byte_count"] > 0 and len(row["sha256"]) == 64 for row in facts)
    assert document["source_closure"][
        "development_seed_identities_disjoint_from_registered_identities"
    ] is True


def test_v52_preregistration_rejects_mutation() -> None:
    frozen = pre.freeze_factor_prior_ablation_preregistration_v52()
    with pytest.raises(pre.ConstructionK7FactorPriorAblationPreregistrationV52Error):
        pre.FactorPriorAblationPreregistrationV52(
            object(), frozen.canonical_bytes, frozen.preregistration_id
        )
    object.__setattr__(frozen, "canonical_bytes", frozen.canonical_bytes + b" ")
    with pytest.raises(ValueError):
        pre.verify_factor_prior_ablation_preregistration_v52(frozen)
