"""Total-label ablation for a projected model with preloaded target rows."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_applicability_conditioned_planner_v58 import (
    GenericApplicabilityConditionedPlannerV58Error,
    plan_applicability_conditioned_model_v58,
)
from acfqp.generic_coordinate_aligned_certificate_planner_v60 import _projection
from acfqp.generic_coordinate_alignment_v60 import compile_coordinate_alignment_v60
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_preloaded_certificate_receding_engine_v74 import (
    run_preloaded_certificate_receding_episode_v74,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericProjectedTotalLabelAblationV77Error(ValueError):
    pass


_ABLATION_DOMAIN = b"acfqp:generic-projected-total-label-ablation:v77\x00"


def _fail(message: str) -> NoReturn:
    raise GenericProjectedTotalLabelAblationV77Error(message)


def run_projected_total_label_ablation_v77(
    adapter: Any,
    target_candidate: PartialFactorCandidateV15,
    observed_rows: tuple[Any, ...],
    acquisition_ground_support_labels: int,
    model: Mapping[str, Any],
    applicability_program: Mapping[str, Any],
    *,
    model_source_episode_index: int,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
    maximum_abstract_support_branch_evaluations: int,
    abstract_support_feasible_beam_width: int,
) -> dict[str, Any]:
    if (
        type(target_candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or type(acquisition_ground_support_labels) is not int
        or acquisition_ground_support_labels <= 0
    ):
        _fail("V77 projected total-label inventory changed")
    alignment = compile_coordinate_alignment_v60(
        model,
        applicability_program,
        target_candidate,
        observed_rows,
        adapter.catalogue,
    )
    projected_adapter, projected_candidate, projected_rows = _projection(
        adapter,
        target_candidate,
        observed_rows,
        model,
        alignment,
    )

    def orderer(raw: tuple[int, ...]) -> Mapping[str, Any] | None:
        try:
            return plan_applicability_conditioned_model_v58(
                model,
                applicability_program,
                projected_candidate,
                projected_adapter.catalogue,
                raw,
                maximum_depth=maximum_abstract_depth,
                maximum_support_branch_evaluations=(
                    maximum_abstract_support_branch_evaluations
                ),
                support_feasible_beam_width=abstract_support_feasible_beam_width,
            )
        except GenericApplicabilityConditionedPlannerV58Error:
            return None

    shared = {
        "episode_index": episode_index,
        "maximum_execution_steps": maximum_execution_steps,
        "maximum_incremental_certificate_ground_support_labels": (
            maximum_incremental_certificate_ground_support_labels
        ),
    }
    transfer = run_preloaded_certificate_receding_episode_v74(
        projected_adapter,
        projected_candidate,
        projected_rows,
        preloaded_acquisition_ground_support_labels=(
            acquisition_ground_support_labels
        ),
        arm="PROJECTED_LOW_LABEL_TRANSFER",
        abstract_orderer=orderer,
        **shared,
    )
    strict = run_preloaded_certificate_receding_episode_v74(
        projected_adapter,
        projected_candidate,
        (),
        preloaded_acquisition_ground_support_labels=0,
        arm="STRICT_COLD_DIRECT_GROUND",
        abstract_orderer=None,
        **shared,
    )
    transfer_total = transfer["total_target_ground_support_labels"]
    strict_total = strict["total_target_ground_support_labels"]
    receipts = transfer["abstract_plan_receipts"]
    all_candidates = bool(receipts) and all(
        row["abstract_plan"]["retained_residual_expression_count"]
        == sum(
            item["batch_exact_candidate_count"]
            for item in model["residual_version_spaces"]
        )
        and row["abstract_plan"]["retained_terminal_tree_count"]
        == model["mdl_minimal_terminal_candidate_count"]
        for row in receipts
    )
    payload = {
        "schema": "acfqp.generic_projected_total_label_ablation.v77",
        "family": adapter.family,
        "seed": adapter.seed,
        "model_source_episode_index": model_source_episode_index,
        "target_episode_index": episode_index,
        "source_model_id": model[
            "projected_disagreement_successor_model_id"
        ],
        "source_applicability_program_id": applicability_program[
            "action_applicability_program_id"
        ],
        "target_candidate_id": target_candidate.public_document["candidate_id"],
        "projected_target_candidate_id": projected_candidate.public_document[
            "candidate_id"
        ],
        "coordinate_alignment": copy.deepcopy(alignment),
        "coordinate_alignment_id": alignment["coordinate_alignment_id"],
        "arms": {
            "PROJECTED_LOW_LABEL_TRANSFER": copy.deepcopy(transfer),
            "STRICT_COLD_DIRECT_GROUND": copy.deepcopy(strict),
        },
        "transfer_total_target_ground_support_labels": transfer_total,
        "strict_total_target_ground_support_labels": strict_total,
        "strict_minus_transfer_total_target_labels": strict_total - transfer_total,
        "total_target_sample_reduction_observed": transfer_total < strict_total,
        "same_target_kernel_seed_episode_and_exact_engine": True,
        "acquisition_rows_paid_once_and_reused_as_exact_evidence": True,
        "strict_arm_receives_no_transfer_or_free_target_rows": True,
        "all_actual_residual_and_terminal_candidates_propagated_as_heuristics": (
            all_candidates
        ),
        "all_incremental_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "model_alignment_or_applicability_used_as_safety_authority": False,
        "target_episode_outcomes_used_to_refit_model_alignment_or_applicability": False,
        "sample_labels_execution_steps_derivation_certificate_and_planning_compute_separate": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "ablation_id": hashlib.sha256(
            _ABLATION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_projected_total_label_ablation_v77",)
