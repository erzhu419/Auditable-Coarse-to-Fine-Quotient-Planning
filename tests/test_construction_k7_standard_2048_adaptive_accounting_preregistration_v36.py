from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp import construction_k7_standard_2048_adaptive_accounting_preregistration_v36 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


@pytest.fixture(scope="module")
def frozen():
    return pre.freeze_standard_2048_adaptive_accounting_preregistration_v36()


def test_v35_native_accounting_stages_are_preregistered(frozen) -> None:
    document = frozen.to_document()
    stages = document["registered_stage_plan"]
    assert [row["stage"] for row in stages] == [
        "CERTIFICATE_FAILURE_FRONTIER_FREEZE",
        "ADAPTIVE_LABEL_ACQUISITION_AND_CANDIDATE_ELIMINATION",
        "EXPRESSION_PROPOSAL_FREEZE",
        "EXACT_PROGRAM_PROOF",
        "PROVED_OVERLAY_FREEZE",
        "EPISODE_ABSTRACT_PLANNING_AND_CERTIFICATION",
        "EPISODE_SELECTED_TARGET_EXECUTION",
        "MATCHED_FIRST_FRONTIER_NO_PRIOR_CONTROL",
        "COLD_EXACT_GROUND_CHECKPOINT_REPLAY",
        "PROCESS_AND_IO_SUPERVISION",
    ]
    assert stages[0]["target_probability_access_allowed"] is False
    assert stages[1]["query_must_reference_previously_failed_frontier"] is True
    assert stages[7]["may_modify_operational_overlay"] is False
    assert stages[8]["may_enter_operational_comparison"] is False


def test_counter_registry_and_nine_shared_resources_are_frozen(frozen) -> None:
    protocol = frozen.to_document()["actual_accounting_protocol"]
    assert protocol["summary_to_counter_translation_allowed"] is False
    assert protocol["all_required_leaves_emit_native_zero"] is True
    assert protocol["maximum_worker_processes"] == 2
    assert protocol["maximum_tasks_per_worker_process"] == 1
    assert protocol["shared_resource_paths"] == list(pre.SHARED_RESOURCE_PATHS)
    assert len(protocol["shared_resource_paths"]) == 9


def test_predecessors_are_pending_without_outcome_leakage(frozen) -> None:
    document = frozen.to_document()
    predecessors = document["frozen_predecessors"]
    assert predecessors["v34r1_accounting_preregistration_id"] == (
        pre.V34R1_PREREGISTRATION_ID
    )
    assert predecessors["v35_adaptive_expression_preregistration_id"] == (
        pre.V35_PREREGISTRATION_ID
    )
    assert predecessors["v35_adaptive_expression_campaign_id"]["kind"] == (
        "PENDING_POSTEXECUTION_BINDING"
    )
    assert document["outcome_fields_present"] is False
    assert document["accounting_execution_performed"] is False
    correction = document["stage_separation_contract_correction"]
    assert correction["superseded_v36_preregistration_id"] == (
        pre.SUPERSEDED_V36_PREREGISTRATION_ID
    )
    assert correction["superseded_preregistration_executed"] is False
    assert correction["outcomes_known_when_corrected"] is False


def test_preregistration_identity_domains_and_claim_locks(frozen) -> None:
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        pre.EXPECTED_CANONICAL_SHA256
    )
    assert set(pre.FUTURE_DOMAINS.values()).issubset(PHASE3E_DOMAIN_TAGS)
    document = frozen.to_document()
    assert document["counter_records_issued"] is False
    assert document["automatic_reusable_world_model_goal_completed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    forged = copy.copy(frozen)
    object.__setattr__(forged, "preregistration_id", "f" * 64)
    with pytest.raises(
        pre.ConstructionK7Standard2048AdaptiveAccountingPreregistrationV36Error
    ):
        pre.verify_standard_2048_adaptive_accounting_preregistration_v36(forged)
