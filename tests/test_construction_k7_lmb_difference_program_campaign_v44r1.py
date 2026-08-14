from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_lmb_difference_program_campaign_v44r1 as campaign
from acfqp import (
    construction_k7_lmb_difference_grammar_successor_preregistration_v44r1 as pre,
)


@pytest.fixture(scope="module")
def frozen():
    return campaign.run_lmb_difference_program_campaign_v44r1()


def test_v44r1_campaign_identity_and_failed_predecessor_join(frozen) -> None:
    assert frozen.campaign_id == campaign.EXPECTED_CAMPAIGN_ID
    assert len(frozen.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        campaign.EXPECTED_CANONICAL_SHA256
    )
    document = frozen.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["v44_preregistration_id"] == pre.V44_PREREGISTRATION_ID
    assert document["v44_failure_id"] == pre.V44_FAILURE_ID
    program = document["derived_program"]
    assert program["v44_failure_id"] == pre.V44_FAILURE_ID
    assert program["inherited_offline_source_transition_label_count"] == 42
    assert program["additional_source_confirmation_label_count"] == 15
    assert program["total_offline_source_transition_label_count"] == 57


def test_v44r1_derives_typed_program_without_numeric_candidate_grid(frozen) -> None:
    program = frozen.to_document()["derived_program"]
    rewrite = program["rewrite_cardinality_derivation"]
    assert rewrite["wrap_difference_equations"] == [[2, 0, 3]]
    assert rewrite["derived_numeric_literal"] == 3
    assert rewrite["numeric_candidate_grid_used"] is False
    assert rewrite["all_rows_satisfy_modular_increment"] is True
    assert program["operated_component_derivation"] == {
        "expression": ["ACTION_PUBLIC_CLASS"],
        "unique_difference_join_count": 57,
        "all_rows_satisfied": True,
    }
    assert program["removed_set_derivation"]["all_rows_satisfied"] is True
    assert program["capacity_boundary_derivation"]["expression"] == [
        "GREATER_THAN",
        "post_load",
        "INSTANCE_CAPACITY",
    ]
    assert program["capacity_boundary_derivation"]["numeric_capacity_offset_grid_used"] is False
    assert program["terminal_rule_derivation"]["success_on_full_removal_observation_count"] == 1
    assert program["predeclared_numeric_program_grid_present"] is False
    assert program["source_program_planning_kernel_step_count"] == 0
    assert program["source_generation_witness_access_count"] == 0
    confirmation = program["fresh_source_confirmation_observations"]
    assert len(confirmation) == 15
    assert confirmation[-1]["post_board_empty"] is True
    assert confirmation[-1]["post_status"] == "success"
    assert all(row["source_generation_witness_accessed"] is False for row in confirmation)


def test_v44r1_reuses_program_across_changed_cardinality_capacity_and_depth(frozen) -> None:
    document = frozen.to_document()
    assert pre.SOURCE_SPEC == {
        "tile_count": 15,
        "type_count": 5,
        "capacity": 5,
        "max_layers": 3,
    }
    assert pre.TARGET_SPEC == {
        "tile_count": 18,
        "type_count": 6,
        "capacity": 6,
        "max_layers": 4,
    }
    assert len(document["episodes"]) == 12
    for episode in document["episodes"]:
        assert episode["instance_specification"] == pre.TARGET_SPEC
        assert episode["terminal_state"]["status"] == "success"
        assert episode["full_board_cleared"] is True
        assert episode["execution_environment_step_count"] == 18
        assert episode["source_generation_witness_access_count"] == 0
        assert episode["target_generation_witness_access_count"] == 0


def test_v44r1_ground_rows_only_follow_failed_certificates(frozen) -> None:
    for episode in frozen.to_document()["episodes"]:
        for decision in episode["decisions"]:
            distinction = decision["local_distinction"]
            if distinction is None:
                assert decision["initial_certificate"]["status"] == (
                    "CERTIFIED_MODEL_SUPPORT"
                )
                assert decision["replanned_after_local_distinction"] is False
            else:
                assert decision["initial_certificate"]["status"] == (
                    "FAILED_MISSING_SUPPORT"
                )
                assert distinction["failed_certificate_id"] == (
                    decision["initial_certificate"]["certificate_id"]
                )
                assert distinction["acquired_after_failed_certificate"] is True
                assert decision["final_certificate"]["status"] == (
                    "CERTIFIED_AFTER_LOCAL_DISTINCTION"
                )
                assert decision["replanned_after_local_distinction"] is True
            assert decision["model_matches_execution"] is True


def test_v44r1_sample_axes_compute_and_claim_boundaries(frozen) -> None:
    document = frozen.to_document()
    summary = document["summary"]
    assert summary["structural_meta_prior_target_label_count"] == 18
    assert summary["strict_no_prior_target_label_count"] == 108
    assert summary["target_label_fraction"].numerator == 1
    assert summary["target_label_fraction"].denominator == 6
    assert summary["execution_environment_step_count_per_arm"] == 108
    assert summary["source_abstract_compute_events"] == 94
    assert summary["grammar_derivation_compute_events"] == 397
    assert summary["structural_abstract_compute_events"] == 7227
    assert summary["control_abstract_compute_events"] == 12214
    assert summary["planning_kernel_step_count"] == 0
    assert summary["labels_steps_and_compute_separate"] is True
    assert document["open_ended_grammar_invention_claimed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
