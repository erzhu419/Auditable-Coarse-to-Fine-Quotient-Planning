from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp import construction_k7_standard_2048_adaptive_checkpoint_preregistration_v39 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


@pytest.fixture(scope="module")
def frozen():
    return pre.freeze_standard_2048_adaptive_checkpoint_preregistration_v39()


def test_v39_binds_verified_v35_through_v37_without_target_outcomes(frozen) -> None:
    document = frozen.to_document()
    predecessors = document["frozen_predecessors"]
    assert predecessors["v35_adaptive_expression_campaign_id"] == pre.V35_CAMPAIGN_ID
    assert predecessors["v35_adaptive_expression_verification_id"] == (
        pre.V35_VERIFICATION_ID
    )
    assert predecessors["v36r4_accounted_campaign_id"] == pre.V36R4_CAMPAIGN_ID
    assert predecessors["v36r4_accounting_verification_id"] == (
        pre.V36R4_VERIFICATION_ID
    )
    assert predecessors["v37_adaptive_checkpoint_preregistration_id"] == (
        pre.V37_PREREGISTRATION_ID
    )
    assert predecessors["v37_adaptive_checkpoint_campaign_id"] == pre.V37_CAMPAIGN_ID
    assert predecessors["v37_adaptive_checkpoint_verification_id"] == (
        pre.V37_VERIFICATION_ID
    )
    assert document["outcome_fields_present"] is False
    assert document["checkpoint_execution_performed"] is False


def test_v39_preserves_failed_v38_oom_and_freezes_two_fresh_waves(frozen) -> None:
    document = frozen.to_document()
    failure = document["failed_v38_resource_attempt"]
    assert failure["kernel_failure_class"] == "GLOBAL_OOM_KILL"
    assert failure["failure_exception_type"] == "BrokenProcessPool"
    assert failure["killed_process_anon_rss_kib"] == 11_657_504
    assert failure["campaign_artifact_byte_count"] == 0
    assert failure["campaign_identity_issued"] is False
    assert failure["partial_or_failed_output_may_be_reused"] is False
    successor = document["resource_successor_protocol"]
    assert successor["maximum_concurrent_worker_processes"] == 2
    assert successor["execution_wave_count"] == 2
    assert successor["episode_tasks_per_wave"] == 2
    assert successor["maximum_tasks_per_worker_process"] == 1
    assert successor["fresh_executor_required_for_each_wave"] is True
    assert successor["only_process_schedule_and_memory_concurrency_changed"] is True


def test_v39_freezes_all_four_decision_256_checkpoints(frozen) -> None:
    workload = frozen.to_document()["checkpoint_workload"]
    assert workload["source_episode_ids"] == list(pre.CHECKPOINT_EPISODE_IDS)
    assert workload["checkpoint_boards"] == [list(row) for row in pre.CHECKPOINT_BOARDS]
    assert workload["checkpoint_status"] == ["ACTIVE"] * 4
    assert workload["source_decision_count"] == 256
    assert workload["global_decision_start_inclusive"] == 256
    assert workload["global_decision_stop_exclusive"] == 512
    assert workload["segment_decision_limit"] == 256


def test_v39_reuses_only_the_proved_expression_and_allows_no_new_labels(frozen) -> None:
    document = frozen.to_document()
    model = document["proved_reusable_world_model"]
    assert model["adaptive_expression_overlay_id"] == pre.ADAPTIVE_EXPRESSION_OVERLAY_ID
    assert model["adaptive_expression_proof_id"] == pre.ADAPTIVE_EXPRESSION_PROOF_ID
    assert model["expression_ast"] == {
        "operator": "COUNT_EQ",
        "vector_source": "POST_SWIPE_BOARD_RANKS",
        "constant": 2,
    }
    assert model["threshold"] == 1
    assert model["serialized_target_probability_table_present"] is False
    sample = document["sample_tax_contract"]
    assert sample["inherited_target_probability_label_count"] == 6
    assert sample["additional_model_acquisition_label_budget"] == 0
    assert sample["strict_no_prior_context_label_count"] == 2400
    assert sample["inherited_label_fraction_of_no_prior"].numerator == 1
    assert sample["inherited_label_fraction_of_no_prior"].denominator == 400


def test_v39_identity_domains_and_claim_locks(frozen) -> None:
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        pre.EXPECTED_CANONICAL_SHA256
    )
    assert set(pre.FUTURE_DOMAINS.values()).issubset(PHASE3E_DOMAIN_TAGS)
    assert len(set(pre.FUTURE_DOMAINS.values())) == len(pre.FUTURE_DOMAINS)
    document = frozen.to_document()
    assert document["full_standard_2048_game_claimed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    forged = copy.copy(frozen)
    object.__setattr__(forged, "preregistration_id", "f" * 64)
    with pytest.raises(
        pre.ConstructionK7Standard2048AdaptiveCheckpointPreregistrationV39Error
    ):
        pre.verify_standard_2048_adaptive_checkpoint_preregistration_v39(forged)
