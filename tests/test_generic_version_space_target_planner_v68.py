from __future__ import annotations

import json
from pathlib import Path

import pytest

from acfqp import construction_k7_domain_registry_extension_v91r2 as domains
from acfqp import construction_k7_prior_only_occurrence_source_preregistration_v91r2 as pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as v59
from acfqp.generic_prior_only_partial_acquisition_v67 import (
    acquire_prior_only_partial_candidate_v67,
)
from acfqp.generic_version_space_target_planner_v68 import (
    align_version_space_target_inputs_v68,
    run_matched_version_space_target_ablation_v68,
)


def _inputs(seed: int = 941_102):
    config = pre.campaign_config_v91r2()
    acceptance = json.loads(
        Path(
            ".tmp/exact-freeze/v91r3_source_model_acceptance.json"
        ).read_text()
    )
    model = acceptance["accepted_joint_successor_version_space_model"]
    adapter = v59.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        "COUPLED_EXCHANGE", seed, config
    )
    partial = acquire_prior_only_partial_candidate_v67(
        adapter,
        maximum_ground_support_labels=config[
            "source_partial_acquisition_maximum_ground_labels"
        ],
        global_alpha_denominator=config["global_alpha_denominator"],
        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
        layout_domain=config["generic_domains"]["layout"],
        acquisition_domain=(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_PARTIAL_ACQUISITION_V91R2_DOMAIN
        ),
        content_id=domains.extension_content_id_v91r2,
    )
    return config, model, adapter, partial


@pytest.fixture(scope="module")
def ablation():
    config, model, adapter, partial = _inputs()
    return run_matched_version_space_target_ablation_v68(
        adapter,
        partial["candidate"],
        partial["rows"],
        model,
        layout_domain=config["generic_domains"]["layout"],
        episode_index=1,
        maximum_abstract_depth=5,
        maximum_execution_steps=12,
        maximum_target_ground_support_labels=10_000,
        maximum_robust_state_depth_evaluations=1,
        maximum_abstract_support_branch_evaluations=1_000_000,
        abstract_support_feasible_beam_width=8,
    )


def test_v68_aligns_a_different_finite_observation_layout_without_target_episode():
    config, model, adapter, partial = _inputs()
    alignment, projected, candidate, rows = align_version_space_target_inputs_v68(
        adapter,
        partial["candidate"],
        partial["rows"],
        model,
        layout_domain=config["generic_domains"]["layout"],
    )
    assert alignment["every_retained_partial_residual_and_terminal_program_replayed"] is True
    assert alignment["target_episode_outcomes_used"] is False
    assert alignment["alignment_used_as_safety_authority"] is False
    assert candidate.public_document["compiled_factor_assignments"] == model[
        "known_partial_factor_assignments"
    ]
    assert candidate.public_document["unknown_residual_target_columns"] == [6, 9]
    assert projected.encode(adapter.initial()) == rows[0].pre


def test_v68_receding_abstract_ordering_reduces_exact_local_queries(ablation):
    derived = ablation["arms"]["JOINT_VERSION_SPACE_WORLD_MODEL"]
    strict = ablation["arms"]["STRICT_DIRECT_GROUND"]
    assert derived["success"] is strict["success"] is True
    assert derived["target_certificate_local_ground_support_labels"] == 11
    assert strict["target_certificate_local_ground_support_labels"] == 17
    assert derived["abstract_plan_success_count"] > 0
    assert len(derived["abstract_plan_receipts"]) == derived[
        "abstract_plan_success_count"
    ]
    assert all(
        row["abstract_plan"]["all_residual_version_spaces_jointly_propagated"]
        is True
        for row in derived["abstract_plan_receipts"]
    )
    assert derived["execution_action_matches_abstract_proposal_count"] >= 2
    assert derived["execution_steps"] >= 3
    assert ablation["actual_target_sample_reduction_observed"] is True


def test_v68_ground_distinctions_follow_certificate_failure_only(ablation):
    for episode in ablation["arms"].values():
        assert len(episode["failed_certificates"]) == len(
            episode["local_distinctions"]
        )
        assert all(
            row["ground_query_performed_before_failure"] is False
            for row in episode["failed_certificates"]
        )
        assert all(
            row["query_after_failed_certificate"] is True
            for row in episode["local_distinctions"]
        )
        assert episode["query_local_exact_overlay_exclusively_used_for_safety"] is True
        assert episode["model_or_alignment_used_as_safety_authority"] is False


def test_v68_rejects_a_source_model_claim_flip():
    config, model, adapter, partial = _inputs(941_101)
    forged = dict(model)
    forged["complete_world_model_claimed"] = True
    with pytest.raises(ValueError):
        align_version_space_target_inputs_v68(
            adapter,
            partial["candidate"],
            partial["rows"],
            forged,
            layout_domain=config["generic_domains"]["layout"],
        )
