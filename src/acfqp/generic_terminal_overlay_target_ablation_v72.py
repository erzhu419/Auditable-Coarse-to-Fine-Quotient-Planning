"""Matched target episodes for a source residual model plus local terminal overlay."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_certificate_local_receding_engine_v71 import (
    run_certificate_local_receding_episode_v71,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_terminal_overlay_version_space_planner_v69 import (
    GenericTerminalOverlayVersionSpacePlannerV69Error,
    plan_terminal_overlay_version_space_v69,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericTerminalOverlayTargetAblationV72Error(ValueError):
    pass


_ABLATION_DOMAIN = b"acfqp:generic-terminal-overlay-target-ablation:v72\x00"


def _fail(message: str) -> NoReturn:
    raise GenericTerminalOverlayTargetAblationV72Error(message)


def _identifier(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_ABLATION_DOMAIN + canonical_json_bytes(payload)).hexdigest()


def run_matched_terminal_overlay_target_ablation_v72(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[Any, ...],
    model: Mapping[str, Any],
    terminal_overlay: Mapping[str, Any],
    *,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_target_ground_support_labels: int,
    maximum_robust_state_depth_evaluations: int,
    maximum_abstract_support_branch_evaluations: int,
    abstract_support_feasible_beam_width: int,
) -> dict[str, Any]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or type(model) is not dict
        or type(terminal_overlay) is not dict
    ):
        _fail("V72 matched-ablation inventory changed")

    def orderer(raw: tuple[int, ...]) -> Mapping[str, Any] | None:
        try:
            return plan_terminal_overlay_version_space_v69(
                model,
                terminal_overlay,
                candidate,
                adapter.catalogue,
                raw,
                maximum_depth=maximum_abstract_depth,
                maximum_robust_state_depth_evaluations=(
                    maximum_robust_state_depth_evaluations
                ),
                maximum_support_branch_evaluations=(
                    maximum_abstract_support_branch_evaluations
                ),
                support_feasible_beam_width=abstract_support_feasible_beam_width,
            )
        except GenericTerminalOverlayVersionSpacePlannerV69Error:
            return None

    shared = {
        "episode_index": episode_index,
        "maximum_execution_steps": maximum_execution_steps,
        "maximum_target_ground_support_labels": (
            maximum_target_ground_support_labels
        ),
    }
    derived = run_certificate_local_receding_episode_v71(
        adapter,
        candidate,
        observed_rows,
        arm="SOURCE_RESIDUAL_PLUS_TARGET_TERMINAL_OVERLAY",
        abstract_orderer=orderer,
        **shared,
    )
    strict = run_certificate_local_receding_episode_v71(
        adapter,
        candidate,
        observed_rows,
        arm="STRICT_DIRECT_GROUND",
        abstract_orderer=None,
        **shared,
    )
    derived_labels = derived["target_certificate_local_ground_support_labels"]
    strict_labels = strict["target_certificate_local_ground_support_labels"]
    receipts = derived["abstract_plan_receipts"]
    all_components_propagated = bool(receipts) and all(
        row["abstract_plan"][
            "all_source_residual_version_spaces_jointly_propagated"
        ]
        is True
        and row["abstract_plan"][
            "all_target_mdl_minimal_terminal_trees_jointly_propagated"
        ]
        is True
        for row in receipts
    )
    payload = {
        "schema": "acfqp.generic_terminal_overlay_target_ablation.v72",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "source_model_id": model["joint_successor_version_space_model_id"],
        "terminal_overlay_id": terminal_overlay["terminal_overlay_id"],
        "target_candidate_id": candidate.public_document["candidate_id"],
        "arms": {
            "SOURCE_RESIDUAL_PLUS_TARGET_TERMINAL_OVERLAY": copy.deepcopy(
                derived
            ),
            "STRICT_DIRECT_GROUND": copy.deepcopy(strict),
        },
        "derived_target_certificate_local_ground_support_labels": (
            derived_labels
        ),
        "strict_target_certificate_local_ground_support_labels": strict_labels,
        "strict_minus_derived_target_labels": strict_labels - derived_labels,
        "actual_target_sample_reduction_observed": (
            derived_labels < strict_labels
        ),
        "same_target_adapter_kernel_seed_episode_and_exact_engine": True,
        "only_abstract_orderer_availability_differs_between_arms": True,
        "alignment_and_terminal_overlay_frozen_before_target_episode": True,
        "target_episode_outcomes_used_to_refit_source_residual_or_target_overlay": False,
        "all_actual_residual_and_terminal_candidates_jointly_propagated": (
            all_components_propagated
        ),
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "model_alignment_or_terminal_overlay_used_as_safety_authority": False,
        "sample_labels_execution_steps_derivation_certificate_and_planning_compute_separate": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "ablation_id": _identifier(payload)}


__all__ = ("run_matched_terminal_overlay_target_ablation_v72",)
