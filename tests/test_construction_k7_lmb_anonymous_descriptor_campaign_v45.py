from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_lmb_anonymous_descriptor_campaign_v45 as campaign
from acfqp import construction_k7_lmb_anonymous_descriptor_preregistration_v45 as pre


@pytest.fixture(scope="module")
def frozen():
    return campaign.run_lmb_anonymous_descriptor_campaign_v45()


def test_v45_campaign_identity_and_predecessor_chain(frozen) -> None:
    assert frozen.campaign_id == campaign.EXPECTED_CAMPAIGN_ID
    assert len(frozen.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        campaign.EXPECTED_CANONICAL_SHA256
    )
    document = frozen.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["v44_failure_id"] == pre.V44_FAILURE_ID
    assert document["v44r1_campaign_id"] == pre.V44R1_CAMPAIGN_ID
    assert document["v44r1_verification_id"] == pre.V44R1_VERIFICATION_ID


def test_v45_infers_one_anonymous_descriptor_projection(frozen) -> None:
    program = frozen.to_document()["derived_program"]
    assert program["selected_anonymous_descriptor_field_index"] == 1
    evaluations = program["anonymous_projection_evaluations"]
    assert [row["anonymous_field_index"] for row in evaluations] == [0, 1, 2]
    assert [row["valid_projection"] for row in evaluations] == [False, True, False]
    assert evaluations[1]["satisfied_row_count"] == 31
    assert evaluations[1]["counterexample_observation_ids"] == []
    assert program["source_projection_label_count"] == 13
    assert program["source_confirmation_label_count"] == 18
    assert program["total_source_transition_label_count"] == 31
    assert (
        program["projection_acquisition_episode_closures"][-1][
            "distinct_changed_coordinate_token_count"
        ]
        == 6
    )
    assert program["source_confirmation_observations"][-1]["post_status"] == "success"
    assert program["named_action_class_scaffold_present"] is False
    assert b"ACTION_PUBLIC_CLASS" not in frozen.canonical_bytes


def test_v45_compiles_program_and_derives_minimal_support(frozen) -> None:
    program = frozen.to_document()["derived_program"]
    assert program["rewrite_cardinality_derivation"] == {
        "all_rows_satisfy_modular_increment": True,
        "derived_numeric_literal": 3,
        "numeric_candidate_grid_used": False,
    }
    dependency = program["dependency_derived_support_signature"]
    assert dependency["algorithm"] == pre.DEPENDENCY_MINIMIZATION
    assert dependency["minimal_support_signature"] == [
        "selected_count",
        "capacity_slack",
        "will_remove_last_tile",
    ]
    assert dependency["hand_written_structural_support_key_used"] is False
    assert dependency["unique_minimum_under_tie_break"] is True
    assert all(
        trial["removal_preserves_program_semantics"] is False
        for trial in dependency["deletion_trials"]
    )
    assert dependency["deletion_assignment_evaluation_count"] == 18
    assert all(trial["counterexample"] is not None for trial in dependency["deletion_trials"])
    assert program["hand_written_structural_support_key_present"] is False


def test_v45_transfers_across_descriptor_and_coordinate_permutations(frozen) -> None:
    document = frozen.to_document()
    source_tokens = {
        token
        for row in document["derived_program"]["projection_acquisition_observations"]
        for token in row["coordinate_tokens"]
    } | set(document["derived_program"]["source_confirmation_layout"]["coordinate_tokens"])
    target_tokens = {
        token
        for episode in document["episodes"]
        for token in episode["anonymous_layout"]["coordinate_tokens"]
    }
    assert source_tokens.isdisjoint(target_tokens)
    source_descriptor_values = {
        value
        for row in [
            *document["derived_program"]["projection_acquisition_observations"],
            *document["derived_program"]["source_confirmation_observations"],
        ]
        for value in row["action_descriptor_fields"]
    }
    target_descriptor_values = {
        value
        for episode in document["episodes"]
        for decision in episode["decisions"]
        for value in decision["selected_action_descriptor_fields"]
    }
    assert source_descriptor_values.isdisjoint(target_descriptor_values)
    assert len(document["episodes"]) == 12
    assert all(
        episode["anonymous_layout"]["coordinate_order_is_nonidentity"] is True
        for episode in document["episodes"]
    )
    assert all(episode["instance_specification"] == pre.TARGET_SPEC for episode in document["episodes"])
    assert all(episode["terminal_state"]["status"] == "success" for episode in document["episodes"])
    assert document["summary"]["source_target_descriptor_value_namespaces_disjoint"] is True
    assert document["summary"]["source_target_coordinate_token_namespaces_disjoint"] is True
    assert document["summary"]["descriptor_values_and_coordinate_order_permuted_on_target"] is True


def test_v45_ground_distinctions_only_follow_failed_certificates(frozen) -> None:
    for episode in frozen.to_document()["episodes"]:
        for decision in episode["decisions"]:
            distinction = decision["local_distinction"]
            if distinction is None:
                assert decision["initial_certificate"]["status"] == "CERTIFIED_MODEL_SUPPORT"
                assert decision["replanned_after_local_distinction"] is False
            else:
                assert decision["initial_certificate"]["status"] == "FAILED_MISSING_SUPPORT"
                assert distinction["failed_certificate_id"] == decision["initial_certificate"]["certificate_id"]
                assert distinction["acquired_after_failed_certificate"] is True
                assert decision["final_certificate"]["status"] == "CERTIFIED_AFTER_LOCAL_DISTINCTION"
                assert decision["replanned_after_local_distinction"] is True
            assert decision["model_matches_execution"] is True


def test_v45_accounting_axes_and_claim_boundaries(frozen) -> None:
    document = frozen.to_document()
    summary = document["summary"]
    assert summary["source_projection_label_count"] == 13
    assert summary["source_confirmation_label_count"] == 18
    assert summary["total_source_transition_label_count"] == 31
    assert summary["structural_meta_prior_target_label_count"] == 21
    assert summary["strict_no_prior_target_label_count"] == 126
    assert summary["target_label_fraction"].numerator == 1
    assert summary["target_label_fraction"].denominator == 6
    assert summary["execution_environment_step_count_per_arm"] == 126
    assert summary["source_abstract_compute_events"] == 126
    assert summary["projection_program_dependency_derivation_compute_events"] == 374
    assert summary["structural_abstract_compute_events"] == 10663
    assert summary["control_abstract_compute_events"] == 18860
    assert summary["planning_kernel_step_count"] == 0
    assert summary["labels_steps_and_compute_separate"] is True
    assert document["named_action_class_scaffold_present"] is False
    assert document["hand_written_structural_support_key_present"] is False
    assert document["open_ended_descriptor_or_grammar_invention_claimed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
