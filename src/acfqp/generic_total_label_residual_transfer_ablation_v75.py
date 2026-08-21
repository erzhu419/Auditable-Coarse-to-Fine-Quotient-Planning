"""Compare total target labels for low-label transfer against cold direct proof."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
    plan_joint_successor_version_space_v42,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_preloaded_certificate_receding_engine_v74 import (
    run_preloaded_certificate_receding_episode_v74,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericTotalLabelResidualTransferAblationV75Error(ValueError):
    pass


_ABLATION_DOMAIN = b"acfqp:generic-total-label-residual-transfer-ablation:v75\x00"


def _fail(message: str) -> NoReturn:
    raise GenericTotalLabelResidualTransferAblationV75Error(message)


def _identifier(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_ABLATION_DOMAIN + canonical_json_bytes(payload)).hexdigest()


def run_total_label_residual_transfer_ablation_v75(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    applicability_rows: tuple[Any, ...],
    applicability_ground_support_labels: int,
    model: Mapping[str, Any],
    *,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
    maximum_robust_state_depth_evaluations: int,
    maximum_abstract_support_branch_evaluations: int,
    abstract_support_feasible_beam_width: int,
) -> dict[str, Any]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(applicability_rows) is not tuple
        or not applicability_rows
        or type(applicability_ground_support_labels) is not int
        or applicability_ground_support_labels <= 0
        or type(model) is not dict
    ):
        _fail("V75 total-label ablation inventory changed")

    def orderer(raw: tuple[int, ...]) -> Mapping[str, Any] | None:
        try:
            return plan_joint_successor_version_space_v42(
                model,
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
        except GenericJointSuccessorVersionSpacePlannerV42Error:
            return None

    shared = {
        "episode_index": episode_index,
        "maximum_execution_steps": maximum_execution_steps,
        "maximum_incremental_certificate_ground_support_labels": (
            maximum_incremental_certificate_ground_support_labels
        ),
    }
    transfer = run_preloaded_certificate_receding_episode_v74(
        adapter,
        candidate,
        applicability_rows,
        preloaded_acquisition_ground_support_labels=(
            applicability_ground_support_labels
        ),
        arm="LOW_LABEL_RESIDUAL_TRANSFER",
        abstract_orderer=orderer,
        **shared,
    )
    strict = run_preloaded_certificate_receding_episode_v74(
        adapter,
        candidate,
        (),
        preloaded_acquisition_ground_support_labels=0,
        arm="STRICT_COLD_DIRECT_GROUND",
        abstract_orderer=None,
        **shared,
    )
    transfer_total = transfer["total_target_ground_support_labels"]
    strict_total = strict["total_target_ground_support_labels"]
    receipts = transfer["abstract_plan_receipts"]
    all_source_candidates_propagated = bool(receipts) and all(
        row["abstract_plan"]["all_residual_version_spaces_jointly_propagated"]
        is True
        and row["abstract_plan"]["all_mdl_minimal_terminal_trees_jointly_propagated"]
        is True
        for row in receipts
    )
    payload = {
        "schema": "acfqp.generic_total_label_residual_transfer_ablation.v75",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "source_model_id": model["joint_successor_version_space_model_id"],
        "target_candidate_id": candidate.public_document["candidate_id"],
        "arms": {
            "LOW_LABEL_RESIDUAL_TRANSFER": copy.deepcopy(transfer),
            "STRICT_COLD_DIRECT_GROUND": copy.deepcopy(strict),
        },
        "transfer_total_target_ground_support_labels": transfer_total,
        "strict_total_target_ground_support_labels": strict_total,
        "strict_minus_transfer_total_target_labels": strict_total - transfer_total,
        "total_target_sample_reduction_observed": transfer_total < strict_total,
        "same_target_kernel_seed_episode_and_exact_engine": True,
        "transfer_arm_applicability_rows_paid_once_and_reused_as_exact_evidence": True,
        "strict_arm_receives_no_transfer_or_free_target_rows": True,
        "source_terminal_program_used_only_as_fallible_action_ordering_heuristic": True,
        "source_terminal_applicability_claimed": False,
        "all_actual_source_residual_and_terminal_candidates_propagated_as_heuristics": (
            all_source_candidates_propagated
        ),
        "all_incremental_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "model_or_alignment_used_as_safety_authority": False,
        "target_episode_outcomes_used_to_refit_model_or_alignment": False,
        "sample_labels_execution_steps_derivation_certificate_and_planning_compute_separate": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "ablation_id": _identifier(payload)}


__all__ = ("run_total_label_residual_transfer_ablation_v75",)
