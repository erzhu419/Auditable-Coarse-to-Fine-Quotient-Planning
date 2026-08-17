from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_template_free_campaign_v48 as campaign
from acfqp import construction_k7_template_free_preregistration_v48 as pre


@pytest.fixture(scope="module")
def frozen():
    return campaign.freeze_template_free_campaign_v48()


def test_v48_campaign_identity_and_template_free_programs(frozen) -> None:
    assert frozen.campaign_id == campaign.CAMPAIGN_ID
    assert len(frozen.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert (
        hashlib.sha256(frozen.canonical_bytes).hexdigest()
        == campaign.EXPECTED_CANONICAL_SHA256
    )
    document = frozen.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["one_synthesizer_three_distinct_programs"] is True
    assert len(document["programs"]) == 3
    assert len({row["selected_clause_set_sha256"] for row in document["programs"]}) == 3
    assert all(row["whole_program_template_count"] == 0 for row in document["programs"])
    assert document["whole_program_template_count"] == 0
    assert document["historical_template_opcode_names_in_programs"] == []
    assert "T00" not in repr(document["programs"])
    assert "T01" not in repr(document["programs"])


def test_v48_receding_plans_and_failure_only_local_recovery(frozen) -> None:
    document = frozen.to_document()
    expected = (
        [("D00", seed) for seed in pre.LMB_TARGET_SEEDS]
        + [("D01", seed) for seed in pre.ROUTING_TARGET_SEEDS]
        + [("D02", seed) for seed in pre.MODULAR_TARGET_SEEDS]
    )
    assert [(row["anonymous_family"], row["seed"]) for row in document["episodes"]] == expected
    assert all(row["terminal_status"] == "SUCCESS" for row in document["episodes"])
    assert all(row["planner_consumed_compiled_ast_only"] is True for row in document["episodes"])
    distinctions = [
        decision["local_distinction"]
        for episode in document["episodes"]
        for decision in episode["decisions"]
        if decision["local_distinction"] is not None
    ]
    assert len(distinctions) == 1
    assert distinctions[0]["acquired_after_failed_certificate"] is True
    assert distinctions[0]["anonymous_relation_value"] == pre.SHARED_MODE_TOKENS[-1]
    assert distinctions[0]["observed_modular_delta"] == pre.MODULAR_TARGET_SPEC["mode_deltas"][-1]
    assert document["adaptive_acquisition"]["target_failed_certificate_count"] == 1
    assert document["adaptive_acquisition"]["target_local_ground_label_count"] == 1
    assert document["adaptive_acquisition"]["overlay_reused_occurrence_count"] == 5
    assert document["D02_overlay_acquired_once_and_reused"] is True


def test_v48_partial_dynamics_sample_tax_and_accounting_are_honest(frozen) -> None:
    document = frozen.to_document()
    partial = document["stochastic_partial_model"]
    assert partial["support_complete_on_registered_source"] is True
    assert partial["exact_probability_authority"] is False
    assert partial["planner_probability_input"] == "NONE_ROBUST_WORST_SUPPORT"
    assert all(row["conservative_probability_interval"] == [0, 1] for row in partial["support_rows"])

    sample = document["sample_tax"]
    assert sample["offline_source_labels"] == 215
    assert sample["structural_target_local_labels"] == 1
    assert sample["structural_total_labels_including_offline"] == 216
    assert sample["strict_target_ground_labels"] == 695
    assert sample["registered_label_saving"] == 479
    assert sample["diagnostic_episode_break_even"] == 2
    assert sample["positive_registered_condition_passed"] is True
    assert sample["broad_cross_domain_sample_efficiency_claimed"] is False
    assert sample["total_operational_work_saving_claimed"] is False

    accounting = document["accounting_axes"]
    assert accounting["offline_source_labels"] == 215
    assert accounting["target_local_labels_structural"] == 1
    assert accounting["target_ground_labels_strict"] == 695
    assert accounting["labels_execution_synthesis_planning_certificate_and_peak_kept_separate"] is True


def test_v48_strict_ood_and_official_claim_locks(frozen) -> None:
    document = frozen.to_document()
    assert document["strict_ood_control"]["decision"] == "OOD_SCHEMA_REJECTED_NO_TRANSFER"
    assert document["strict_ood_control"]["prior_access_count"] == 0
    assert document["strict_ood_control"]["environment_outcome_count"] == 0
    assert document["strict_ood_control"]["environment_step_count"] == 0
    assert document["broad_world_model_synthesis_claimed"] is False
    assert document["broad_cross_domain_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
