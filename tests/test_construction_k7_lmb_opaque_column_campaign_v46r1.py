from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_lmb_opaque_column_failure_v46 as failure
from acfqp import construction_k7_lmb_opaque_column_preregistration_v46 as base
from acfqp import construction_k7_lmb_opaque_column_campaign_v46r1 as campaign
from acfqp import (
    construction_k7_lmb_opaque_column_successor_preregistration_v46r1 as pre,
)


@pytest.fixture(scope="module")
def frozen():
    return campaign.freeze_lmb_opaque_column_campaign_v46r1()


def test_v46r1_campaign_identity_and_failed_predecessor_chain(frozen) -> None:
    assert frozen.campaign_id == campaign.CAMPAIGN_ID
    assert len(frozen.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        campaign.EXPECTED_CANONICAL_SHA256
    )
    document = frozen.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["v46_preregistration_id"] == base.PREREGISTRATION_ID
    assert document["v46_attempted_campaign_id"] == pre.V46_ATTEMPTED_CAMPAIGN_ID
    assert document["v46_failure_id"] == failure.FAILURE_ID
    assert document["v46_failure_preserved"] is True


def test_v46r1_derives_columns_projection_cardinality_and_program(frozen) -> None:
    program = frozen.to_document()["derived_program"]
    cross = program["cross_occurrence_factorization"]
    assert cross["selected_anonymous_action_field_index"] == 1
    assert cross["cyclic_cardinality"] == 3
    assert cross["state_column_roles_predeclared"] is False
    assert cross["coordinate_token_equality_join_used"] is False
    factorizations = [
        *cross["source_occurrence_factorizations"],
        cross["source_confirmation_factorization"],
    ]
    assert len(factorizations) == 2
    for factorization in factorizations:
        assert factorization["selected_anonymous_action_field_index"] == 1
        assert factorization["cyclic_cardinality"] == 3
        assert factorization["predeclared_state_column_roles_used"] is False
        assert factorization["coordinate_token_equality_join_used"] is False
        assert len(factorization["dynamic_column_indices"]) >= pre.MIN_DYNAMIC_COLUMN_COUNT
        assert factorization["removed_set_column_index"] not in factorization["dynamic_column_indices"]
        assert factorization["terminal_column_index"] not in factorization["dynamic_column_indices"]
        assert factorization["capacity_column_index"] not in factorization["dynamic_column_indices"]
        assert len(factorization["selected_group_to_changed_column_relation"]) == len(
            factorization["dynamic_column_indices"]
        )
    assert len(factorizations[-1]["dynamic_column_indices"]) == pre.SOURCE_SPEC["type_count"]


def test_v46r1_compiled_program_is_closed_under_registered_grammar(frozen) -> None:
    program = frozen.to_document()["derived_program"]
    registered = {row[0] for row in pre.GENERIC_RELATION_META_GRAMMAR["constructors"]}
    assert set(program["registered_constructor_names"]) == registered
    assert set(program["used_constructor_names"]) <= registered
    assert set(pre.ADDED_CONSTRUCTORS) <= set(program["used_constructor_names"])
    assert program["unregistered_constructor_names"] == []
    assert program["all_compiled_constructors_belong_to_registered_meta_grammar"] is True
    dependency = program["dependency_derived_support_signature"]
    assert dependency["support_signature_fields_predeclared"] == []
    assert dependency["minimal_support_signature"] == [
        "selected_count",
        "capacity_slack",
        "will_remove_last_action",
    ]
    assert dependency["unique_minimum_under_tie_break"] is True
    assert all(
        trial["removal_preserves_program_semantics"] is False
        for trial in dependency["deletion_trials"]
    )


def test_v46r1_reuses_program_across_fresh_opaque_permutations(frozen) -> None:
    document = frozen.to_document()
    program = document["derived_program"]
    source_layouts = {
        row["layout_id"] for row in program["source_acquisition_observations"]
    } | {program["source_confirmation_layout"]["layout_id"]}
    target_layouts = {episode["opaque_layout"]["layout_id"] for episode in document["episodes"]}
    assert source_layouts.isdisjoint(target_layouts)
    source_values = {
        value
        for row in [
            *program["source_acquisition_observations"],
            *program["source_confirmation_observations"],
        ]
        for value in row["action_metadata_fields"]
    }
    target_values = {
        value
        for episode in document["episodes"]
        for decision in episode["decisions"]
        for value in decision["selected_action_metadata_fields"]
    }
    assert source_values.isdisjoint(target_values)
    assert len(document["episodes"]) == 12
    assert all(episode["instance_specification"] == pre.TARGET_SPEC for episode in document["episodes"])
    assert all(episode["terminal_state"]["status"] == "success" for episode in document["episodes"])
    assert document["summary"]["source_target_layout_id_sets_disjoint"] is True
    assert document["summary"]["source_target_action_value_namespaces_disjoint"] is True


def test_v46r1_ground_distinctions_only_follow_failed_certificates(frozen) -> None:
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


def test_v46r1_ood_rejection_accounting_and_claim_boundaries(frozen) -> None:
    document = frozen.to_document()
    summary = document["summary"]
    ood = document["ood_no_transfer"]
    assert ood["decision"] == "OOD_SCHEMA_REJECTED_NO_TRANSFER"
    assert ood["schema_compatible"] is False
    assert ood["prior_access_count"] == 0
    assert ood["overlay_access_count"] == 0
    assert ood["transition_outcome_access_count"] == 0
    assert ood["target_label_count"] == 0
    assert ood["environment_step_count"] == 0
    assert summary["source_acquisition_label_count"] == 11
    assert summary["source_confirmation_label_count"] == 21
    assert summary["total_source_transition_label_count"] == 32
    assert summary["structural_target_label_count"] == 70
    assert summary["strict_no_prior_target_label_count"] == 144
    assert summary["execution_environment_step_count_per_arm"] == 144
    assert summary["factorization_relation_program_dependency_compute_events"] == 405
    assert summary["source_abstract_compute_events"] == 164
    assert summary["structural_abstract_compute_events"] == 22_330
    assert summary["control_abstract_compute_events"] == 28_824
    assert summary["labels_steps_and_compute_separate"] is True
    assert summary["planning_kernel_step_count"] == 0
    assert document["state_column_roles_predeclared"] is False
    assert document["coordinate_token_equality_scaffold_present"] is False
    assert document["open_ended_relation_grammar_invention_claimed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
