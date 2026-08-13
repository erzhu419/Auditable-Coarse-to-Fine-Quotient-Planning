from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_matched_repair_preregistration_v19 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_matched_repair_gate_is_outcome_free() -> None:
    value = pre.freeze_standard_2048_matched_repair_preregistration_v19()
    assert pre.verify_standard_2048_matched_repair_preregistration_v19(value) is value
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False
    assert document["program_prior_query_count"] == 0
    assert document["no_prior_query_count"] == 0
    assert document["strict_query_reduction_observed"] is False


def test_two_matched_arms_and_active_rule_are_frozen() -> None:
    document = pre.freeze_standard_2048_matched_repair_preregistration_v19().to_document()
    assert [row["arm"] for row in document["matched_arms"]] == list(pre.ARMS)
    assert document["matched_arms"][0]["query_rule"] == (
        "MINIMIZE_MAXIMUM_VERSION_SPACE_BUCKET_THEN_MIN_EMPTY_COUNT"
    )
    assert document["matched_arms"][1]["query_rule"] == (
        "QUERY_EVERY_UNBOUND_EMPTY_COUNT_IN_FAILED_FRONTIER_ASCENDING"
    )
    matching = document["matching_contract"]
    assert matching["same_target_kernel"] is True
    assert matching["same_initial_boards_and_tapes"] is True
    assert matching["same_certificate_failure_before_first_query"] is True
    assert matching["positive_sample_result_requires_strictly_fewer_unique_queries"] is True


def test_fresh_workload_and_predecessors_are_frozen() -> None:
    document = pre.freeze_standard_2048_matched_repair_preregistration_v19().to_document()
    assert document["target_workload"]["episode_count"] == 3
    assert document["target_workload"]["maximum_decisions_per_episode"] == 4
    assert document["target_workload"]["planning_horizon"] == 3
    assert document["frozen_predecessors"]["v18_independent_verification_id"] == (
        pre.V18_INDEPENDENT_VERIFICATION_ID
    )
    assert document["frozen_predecessors"]["v18_results_frozen_before_v19_target_execution"] is True


def test_domains_sample_axes_and_claim_locks() -> None:
    document = pre.freeze_standard_2048_matched_repair_preregistration_v19().to_document()
    assert len(pre.FUTURE_DOMAINS) == 8
    assert len(set(pre.FUTURE_DOMAINS.values())) == 8
    assert set(pre.FUTURE_DOMAINS.values()).issubset(PHASE3E_DOMAIN_TAGS)
    assert document["sample_axes"]["ground_distinction_queries"] == "PRIMARY_REGISTERED_SAMPLE_AXIS"
    assert document["sample_axes"]["scalar_sum_present"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_and_caller_mint_are_rejected() -> None:
    value = pre.freeze_standard_2048_matched_repair_preregistration_v19()
    tampered = copy.copy(value)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7Standard2048MatchedRepairPreregistrationV19Error):
        pre.verify_standard_2048_matched_repair_preregistration_v19(tampered)
    with pytest.raises(pre.ConstructionK7Standard2048MatchedRepairPreregistrationV19Error):
        pre.Standard2048MatchedRepairPreregistrationV19(
            object(), value.canonical_bytes, value.preregistration_id
        )
