from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_exact_factor_preregistration_v15 as p
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_exact_factor_preregistration_is_outcome_free() -> None:
    value = p.freeze_standard_2048_exact_factor_preregistration_v15()
    assert p.verify_standard_2048_exact_factor_preregistration_v15(value) is value
    document = value.to_document()
    assert value.preregistration_id == p.PREREGISTRATION_ID
    assert document["outcome_fields_present"] is False
    assert document["v13_target_transition_or_route_outcomes_read_before_freeze"] is False
    assert document["exact_factored_campaign_run"] is False
    assert document["target_execution_performed"] is False
    assert document["sample_tax_reduction_claimed"] is False


def test_synthesized_swipe_and_source_closed_spawn_are_separated() -> None:
    document = p.freeze_standard_2048_exact_factor_preregistration_v15().to_document()
    operator = document["exact_factored_operator"]
    assert operator["deterministic_component"] == (
        "V14_OBSERVATION_PROPOSED_EXACT_PROVED_SWIPE_PROGRAM"
    )
    assert operator["stochastic_component"] == (
        "SOURCE_CLOSED_STANDARD_2048_SPAWN_CONTRACT"
    )
    source = document["exact_factor_source_closure"]
    assert source["source_sha256"] == p.STANDARD_2048_SOURCE_SHA256
    assert source["source_byte_count"] == p.STANDARD_2048_SOURCE_BYTE_COUNT
    assert source["public_rule_is_domain_contract_not_statistically_inferred"] is True
    assert source["spawn_distribution"][0]["probability"] == pytest.approx(0.9)


def test_exact_model_planning_and_failure_route_are_frozen() -> None:
    document = p.freeze_standard_2048_exact_factor_preregistration_v15().to_document()
    certificate = document["certificate_protocol"]
    assert certificate["planning_horizon"] == 3
    assert certificate["certificate_kind"] == "EXACT_FACTORED_H3_BELLMAN_OPTIMALITY"
    assert certificate["certificate_uses_ground_step_v1"] is False
    assert certificate["certificate_frozen_before_target_transition"] is True
    assert certificate["fallback_only_after_certificate_failure"] is True
    target = document["target_workload"]
    assert target["episode_count"] == 4
    assert target["maximum_decision_count"] == 64


def test_sample_tax_claim_requires_target_equivalence_and_axes_stay_separate() -> None:
    sample = p.freeze_standard_2048_exact_factor_preregistration_v15().to_document()[
        "sample_tax_gate"
    ]
    assert sample["program_arm_offline_transition_observation_count"] == 768
    assert sample["matched_fixed_observation_control_count"] == 8192
    assert sample["registered_offline_observation_difference"] == 7424
    assert sample["positive_result_requires_all_target_action_value_loss_equivalence"] is True
    assert sample["target_transition_count_reported_separately"] is True
    assert sample["program_proof_compute_count_reported_separately"] is True
    assert sample["total_operational_work_saving_claimed"] is False


def test_domains_and_locked_official_fields_reject_tampering() -> None:
    assert len(set(p.FUTURE_DOMAINS.values())) == len(p.FUTURE_DOMAINS)
    assert set(p.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    value = p.freeze_standard_2048_exact_factor_preregistration_v15()
    document = value.to_document()
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    forged = copy.copy(value)
    object.__setattr__(forged, "preregistration_id", "f" * 64)
    with pytest.raises(p.ConstructionK7Standard2048ExactFactorPreregistrationV15Error):
        p.verify_standard_2048_exact_factor_preregistration_v15(forged)
    with pytest.raises(p.ConstructionK7Standard2048ExactFactorPreregistrationV15Error):
        p.Standard2048ExactFactorPreregistrationV15(
            object(), value.canonical_bytes, value.preregistration_id
        )
