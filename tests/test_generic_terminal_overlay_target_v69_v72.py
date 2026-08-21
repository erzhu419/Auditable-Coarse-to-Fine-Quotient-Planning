from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from acfqp import construction_k7_domain_registry_extension_v91r2 as domains
from acfqp import construction_k7_prior_only_occurrence_source_preregistration_v91r2 as pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as v59
from acfqp.generic_joint_partial_terminal_acquisition_v70 import (
    acquire_joint_partial_terminal_prefix_v70,
)
from acfqp.generic_terminal_overlay_target_ablation_v72 import (
    run_matched_terminal_overlay_target_ablation_v72,
)
from acfqp.generic_terminal_overlay_version_space_planner_v69 import (
    plan_terminal_overlay_version_space_v69,
)


@pytest.fixture(scope="module")
def development_result():
    config = pre.campaign_config_v91r2()
    model = json.loads(
        Path(".tmp/exact-freeze/v91r3_source_model_acceptance.json").read_text()
    )["accepted_joint_successor_version_space_model"]
    adapter = v59.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        "COUPLED_EXCHANGE", 941_101, config
    )
    acquisition = acquire_joint_partial_terminal_prefix_v70(
        adapter,
        model,
        maximum_ground_support_labels=160,
        global_alpha_denominator=config["global_alpha_denominator"],
        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
        terminal_confidence_denominator=4,
        maximum_terminal_program_candidates=128,
        layout_domain=config["generic_domains"]["layout"],
        partial_acquisition_domain=(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_PARTIAL_ACQUISITION_V91R2_DOMAIN
        ),
        joint_acquisition_domain=(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_MEMBER_V91R2_DOMAIN
        ),
        content_id=domains.extension_content_id_v91r2,
    )
    ablation = run_matched_terminal_overlay_target_ablation_v72(
        acquisition["projected_adapter"],
        acquisition["candidate"],
        acquisition["aligned_rows"],
        model,
        acquisition["terminal_overlay"],
        episode_index=2,
        maximum_abstract_depth=5,
        maximum_execution_steps=12,
        maximum_target_ground_support_labels=10_000,
        maximum_robust_state_depth_evaluations=1,
        maximum_abstract_support_branch_evaluations=1_000_000,
        abstract_support_feasible_beam_width=8,
    )
    return model, acquisition, ablation


def test_joint_stop_extends_only_until_current_terminal_candidate_closes(
    development_result,
):
    _model, acquisition, _ablation = development_result
    document = acquisition["document"]
    assert document["partial_factor_stop_ground_support_labels"] == 17
    assert document["terminal_confidence_crossing_ground_support_label"] == 19
    assert document["joint_stop_ground_support_labels"] == 19
    assert document["terminal_calibration_incremental_ground_support_labels"] == 2
    assert document["terminal_overlay"]["retired_terminal_candidate_count"] == 1
    assert document["terminal_witness_used_to_schedule_queries"] is False
    assert document["fixed_confirmation_block_used"] is False
    assert document["target_episode_outcomes_used"] is False
    assert document["raw_transition_rows"]
    assert document["action_catalogue"]


def test_same_exact_engine_uses_model_only_for_ordering_and_reduces_labels(
    development_result,
):
    _model, _acquisition, ablation = development_result
    derived = ablation["arms"][
        "SOURCE_RESIDUAL_PLUS_TARGET_TERMINAL_OVERLAY"
    ]
    strict = ablation["arms"]["STRICT_DIRECT_GROUND"]
    assert derived["success"] is strict["success"] is True
    assert derived["target_certificate_local_ground_support_labels"] == 6
    assert strict["target_certificate_local_ground_support_labels"] == 12
    assert derived["execution_action_matches_abstract_proposal_count"] == 2
    assert ablation["actual_target_sample_reduction_observed"] is True
    assert ablation[
        "all_actual_residual_and_terminal_candidates_jointly_propagated"
    ] is True
    for episode in (derived, strict):
        assert len(episode["failed_certificates"]) == len(
            episode["local_distinctions"]
        )
        assert episode["all_ground_queries_followed_failed_certificates"] is True
        assert episode[
            "query_local_exact_overlay_exclusively_used_for_safety"
        ] is True
        assert episode[
            "model_alignment_or_terminal_overlay_used_as_safety_authority"
        ] is False


def test_planner_rejects_a_confirmation_block_claim_flip(development_result):
    model, acquisition, _ablation = development_result
    forged = copy.deepcopy(acquisition["terminal_overlay"])
    forged["fixed_confirmation_block_used"] = True
    with pytest.raises(ValueError):
        plan_terminal_overlay_version_space_v69(
            model,
            forged,
            acquisition["candidate"],
            acquisition["projected_adapter"].catalogue,
            acquisition["projected_adapter"].encode(
                acquisition["projected_adapter"].initial()
            ),
            maximum_depth=5,
            maximum_robust_state_depth_evaluations=1,
            maximum_support_branch_evaluations=1_000_000,
            support_feasible_beam_width=8,
        )
