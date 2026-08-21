"""Prequentially confirm a reusable residual model with few target labels.

Only the source layout, partial factor and residual successor programs are
tested.  The source terminal program remains an explicitly fallible action
ordering heuristic; exact query-local certificates retain all safety authority.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Callable, Mapping, NoReturn

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp.generic_layout_factorized_world_model_v5 import (
    DiscoveredLayoutV5,
    align_generic_occurrence_v5,
    match_generic_layout_meta_prior_v5,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_terminal_overlay_version_space_planner_v69 import (
    _check_residual_prefix,
)
from acfqp.generic_version_space_target_planner_v68 import (
    _AlignedTargetAdapterV68,
    _model_reference_inputs,
)
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    verify_joint_successor_version_space_model_v42,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericLowLabelResidualApplicabilityV73Error(ValueError):
    pass


_CANDIDATE_DOMAIN = b"acfqp:generic-low-label-residual-candidate:v73\x00"


def _fail(message: str) -> NoReturn:
    raise GenericLowLabelResidualApplicabilityV73Error(message)


def _identifier(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def acquire_low_label_residual_applicability_v73(
    adapter: Any,
    model: Mapping[str, Any],
    *,
    maximum_ground_support_labels: int,
    confidence_denominator: int,
    source_meta_prior_odds: int,
    layout_domain: str,
    applicability_domain: str,
    content_id: Callable[[str, Any], str],
) -> dict[str, Any]:
    verified = verify_joint_successor_version_space_model_v42(model)
    if (
        type(maximum_ground_support_labels) is not int
        or maximum_ground_support_labels <= 0
        or type(confidence_denominator) is not int
        or confidence_denominator <= 1
        or type(source_meta_prior_odds) is not int
        or source_meta_prior_odds <= 0
        or type(layout_domain) is not str
        or not layout_domain
        or type(applicability_domain) is not str
        or not applicability_domain
        or not callable(content_id)
    ):
        _fail("V73 residual applicability contract changed")
    reference_rows, reference_catalogue, reference_layout = (
        _model_reference_inputs(verified)
    )
    rows = []
    batches = []
    matched_layout = None
    issuance_label = None
    confidence_crossing = None
    successes = 0
    epoch = 0
    retired = []
    history = []
    replay_compute = 0
    for label, batch in enumerate(
        ground._witness_blind_depth_frontier(adapter), 1  # noqa: SLF001
    ):
        if label > maximum_ground_support_labels:
            break
        rows.extend(batch)
        batches.append(batch)
        if matched_layout is not None:
            try:
                aligned_batch, _catalogue = align_generic_occurrence_v5(
                    batch,
                    adapter.catalogue,
                    matched_layout,
                    canonical_occurrence=0,
                )
                replay = _check_residual_prefix(verified, aligned_batch)
            except Exception as error:
                if not error.__class__.__module__.startswith("acfqp.generic_"):
                    raise
                retired.append(
                    {
                        "candidate_epoch": epoch,
                        "layout_id": matched_layout.layout_id,
                        "failed_ground_support_label": label,
                        "reason": "PREQUENTIAL_PARTIAL_OR_RESIDUAL_PREDICTION_FAILED",
                    }
                )
                history.append(
                    {
                        "ground_support_label": label,
                        "candidate_epoch": epoch,
                        "layout_id": matched_layout.layout_id,
                        "exact_prequential_residual_prediction": False,
                        "stopped": False,
                    }
                )
                matched_layout = None
                issuance_label = None
                confidence_crossing = None
                successes = 0
                epoch += 1
            else:
                replay_compute += (
                    replay["partial_replay_evaluations"]
                    + replay["residual_replay_evaluations"]
                )
                successes += 1
                numerator = 2 ** (successes + 1) - 1
                denominator = successes + 1
                threshold = confidence_denominator * (epoch + 1) * (epoch + 2)
                stopped = (
                    numerator * source_meta_prior_odds
                    >= denominator * threshold
                )
                history.append(
                    {
                        "ground_support_label": label,
                        "candidate_epoch": epoch,
                        "layout_id": matched_layout.layout_id,
                        "exact_prequential_residual_prediction": True,
                        "post_issuance_exact_prediction_success_count": successes,
                        "universal_mixture_evalue_numerator": numerator,
                        "universal_mixture_evalue_denominator": denominator,
                        "evalue_threshold": threshold,
                        "source_meta_prior_odds": source_meta_prior_odds,
                        "stopped": stopped,
                    }
                )
                if stopped:
                    confidence_crossing = label
                    break
        if matched_layout is None:
            current = tuple(rows)
            try:
                proposal = match_generic_layout_meta_prior_v5(
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                    current,
                    adapter.catalogue,
                    layout_domain=layout_domain,
                )
                aligned_current, _catalogue = align_generic_occurrence_v5(
                    current,
                    adapter.catalogue,
                    proposal,
                    canonical_occurrence=0,
                )
                replay = _check_residual_prefix(verified, aligned_current)
            except Exception as error:
                if not error.__class__.__module__.startswith("acfqp.generic_"):
                    raise
                history.append(
                    {
                        "ground_support_label": label,
                        "candidate_epoch": epoch,
                        "layout_id": None,
                        "candidate_issued": False,
                        "reason": str(error),
                        "stopped": False,
                    }
                )
                continue
            matched_layout = proposal
            issuance_label = label
            replay_compute += (
                replay["partial_replay_evaluations"]
                + replay["residual_replay_evaluations"]
            )
            history.append(
                {
                    "ground_support_label": label,
                    "candidate_epoch": epoch,
                    "layout_id": proposal.layout_id,
                    "candidate_issued": True,
                    "post_issuance_exact_prediction_success_count": 0,
                    "stopped": False,
                }
            )
            prior_only_threshold = (
                confidence_denominator * (epoch + 1) * (epoch + 2)
            )
            if source_meta_prior_odds >= prior_only_threshold:
                confidence_crossing = label
                history[-1]["stopped"] = True
                history[-1]["source_meta_prior_only_crossing"] = True
                break
    if (
        matched_layout is None
        or issuance_label is None
        or confidence_crossing is None
    ):
        _fail("V73 residual applicability did not close before its label cap")
    raw_rows = tuple(rows)
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        raw_rows,
        adapter.catalogue,
        matched_layout,
        canonical_occurrence=0,
    )
    final_replay = _check_residual_prefix(verified, aligned_rows)
    replay_compute += (
        final_replay["partial_replay_evaluations"]
        + final_replay["residual_replay_evaluations"]
    )
    width = verified["state_width"]
    action_width = verified["action_field_width"]
    identity_layout = DiscoveredLayoutV5(
        tuple(range(width)),
        tuple(range(action_width)),
        tuple(verified["source_layout"]["state_structural_colors"]),
        tuple(verified["source_layout"]["action_structural_colors"]),
        verified["source_layout"]["schema_signature"],
        0,
        replay_compute,
        hashlib.sha256(
            b"acfqp:generic-low-label-residual-identity-layout:v73\x00"
            + canonical_json_bytes(
                {
                    "source_model_id": verified[
                        "joint_successor_version_space_model_id"
                    ],
                    "target_seed": adapter.seed,
                    "state_order": list(range(width)),
                    "action_order": list(range(action_width)),
                }
            )
        ).hexdigest(),
        verified["source_layout"]["layout_id"],
        matched_layout.graph_edit_score,
        matched_layout.cross_occurrence_value_overlap,
    )
    candidate_payload = {
        "schema": "acfqp.generic_low_label_residual_candidate.v73",
        "source_model_id": verified["joint_successor_version_space_model_id"],
        "layout": identity_layout.to_document(),
        "state_width": width,
        "action_field_width": action_width,
        "compiled_factor_assignments": copy.deepcopy(
            verified["known_partial_factor_assignments"]
        ),
        "unknown_residual_target_columns": sorted(
            [
                *[
                    row["target_column"]
                    for row in verified["residual_version_spaces"]
                ],
                verified["status_target_column"],
            ]
        ),
        "transformed_observation_count": len(aligned_rows),
        "transformed_observation_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in aligned_rows])
        ).hexdigest(),
        "source_partial_and_residual_model_refit": False,
        "source_terminal_program_applicability_claimed": False,
        "planning_authority_present": False,
        "complete_world_model_claimed": False,
    }
    candidate_document = {
        **candidate_payload,
        "candidate_id": _identifier(_CANDIDATE_DOMAIN, candidate_payload),
    }
    candidate = PartialFactorCandidateV15(
        candidate_document,
        identity_layout,
        tuple(verified["known_partial_factor_assignments"]),
        aligned_rows,
    )
    raw_documents = [row.to_document() for row in raw_rows]
    aligned_documents = [row.to_document() for row in aligned_rows]
    action_documents = [row.to_document() for row in adapter.catalogue]
    payload = {
        "schema": "acfqp.generic_low_label_residual_applicability.v73",
        "family": adapter.family,
        "seed": adapter.seed,
        "source_model_id": verified["joint_successor_version_space_model_id"],
        "ground_support_labels": len(batches),
        "raw_transition_rows": raw_documents,
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes(raw_documents)
        ).hexdigest(),
        "aligned_transition_rows": aligned_documents,
        "aligned_transition_sha256": hashlib.sha256(
            canonical_json_bytes(aligned_documents)
        ).hexdigest(),
        "action_catalogue": action_documents,
        "action_catalogue_sha256": hashlib.sha256(
            canonical_json_bytes(action_documents)
        ).hexdigest(),
        "matched_target_layout": matched_layout.to_document(),
        "source_state_to_target_raw": list(
            matched_layout.state_canonical_to_raw
        ),
        "source_action_to_target_raw": list(
            matched_layout.action_canonical_to_raw
        ),
        "projected_target_candidate": copy.deepcopy(candidate_document),
        "candidate_issued_at_ground_support_label": issuance_label,
        "confidence_crossing_ground_support_label": confidence_crossing,
        "confidence_denominator": confidence_denominator,
        "source_meta_prior_odds": source_meta_prior_odds,
        "source_meta_prior_enabled": source_meta_prior_odds > 1,
        "candidate_epoch": epoch,
        "retired_candidate_count": len(retired),
        "retired_candidates": retired,
        "post_issuance_exact_prediction_success_count": successes,
        "target_predictive_confirmation_count": successes,
        "source_meta_prior_only_stop_at_issuance": successes == 0,
        "prequential_history": history,
        "partial_and_residual_replay_compute_events": replay_compute,
        "source_terminal_tree_mismatch_count_on_prefix": final_replay[
            "source_terminal_tree_mismatch_count"
        ],
        "witness_blind_depth_stream_used": True,
        "terminal_witness_used_to_schedule_queries": False,
        "fixed_label_floor_used": False,
        "fixed_confirmation_block_used": False,
        "source_terminal_program_used_only_as_fallible_action_ordering_heuristic": True,
        "empirical_source_meta_prior_strength_preregistered_not_universal": True,
        "residual_applicability_promoted_to_global_fact": False,
        "target_terminal_overlay_synthesized": False,
        "target_episode_outcomes_used": False,
        "source_partial_or_residual_model_refit": False,
        "proposal_used_as_safety_authority": False,
        "complete_world_model_claimed": False,
    }
    document = {
        **payload,
        "applicability_id": content_id(applicability_domain, payload),
    }
    projected = _AlignedTargetAdapterV68(
        adapter,
        adapter.family,
        adapter.seed,
        adapter.kernel,
        aligned_catalogue,
        tuple(matched_layout.state_canonical_to_raw),
    )
    return {
        "document": document,
        "projected_adapter": projected,
        "candidate": candidate,
        "raw_rows": raw_rows,
        "aligned_rows": aligned_rows,
        "batches": tuple(batches),
    }


__all__ = ("acquire_low_label_residual_applicability_v73",)
