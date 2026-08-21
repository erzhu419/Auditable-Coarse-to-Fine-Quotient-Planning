"""Low-label applicability of a projected anonymous world model.

The same witness-blind prefix, constructor, semantic-stability signature and
universal-mixture stopping formula are used in both arms.  The sole switch is
the preregistered source-model prior odds.  A source model can order actions,
but neither the projection nor the prior receives safety authority.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Callable, Mapping, NoReturn

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp.generic_coordinate_alignment_v60 import compile_coordinate_alignment_v60
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    synthesize_partial_factor_candidate_v15,
)
from acfqp.generic_projected_disagreement_model_compiler_v56 import (
    verify_projected_disagreement_model_v56,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericProjectedLowLabelApplicabilityV76Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericProjectedLowLabelApplicabilityV76Error(message)


def _semantic_signature(candidate: Any, alignment: Mapping[str, Any]) -> str:
    document = candidate.public_document
    layout = document["layout"]
    payload = {
        "compiled_factor_assignments": document["compiled_factor_assignments"],
        "unknown_residual_target_columns": document[
            "unknown_residual_target_columns"
        ],
        "state_structural_colors": layout["state_structural_colors"],
        "action_structural_colors": layout["action_structural_colors"],
        "source_state_to_target_canonical": alignment[
            "source_state_to_target_canonical"
        ],
        "source_action_to_target_canonical": alignment[
            "source_action_to_target_canonical"
        ],
        "target_applicability_state_column": alignment[
            "target_applicability_state_column"
        ],
        "target_applicability_action_field": alignment[
            "target_applicability_action_field"
        ],
    }
    return hashlib.sha256(
        b"acfqp:generic-projected-applicability-semantic-signature:v76\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


def acquire_projected_low_label_applicability_v76(
    adapter: Any,
    model: Mapping[str, Any],
    applicability_program: Mapping[str, Any],
    *,
    maximum_ground_support_labels: int,
    confidence_denominator: int,
    source_meta_prior_odds: int,
    minimum_factor_assignment_count: int,
    layout_domain: str,
    acquisition_domain: str,
    content_id: Callable[[str, Any], str],
) -> dict[str, Any]:
    verified = verify_projected_disagreement_model_v56(model)
    if (
        type(applicability_program) is not dict
        or applicability_program.get("source_model_id")
        != verified["projected_disagreement_successor_model_id"]
        or applicability_program.get("training_exact") is not True
        or applicability_program.get("heldout_exact") is not True
        or type(maximum_ground_support_labels) is not int
        or maximum_ground_support_labels <= 0
        or type(confidence_denominator) is not int
        or confidence_denominator <= 1
        or type(source_meta_prior_odds) is not int
        or source_meta_prior_odds <= 0
        or type(minimum_factor_assignment_count) is not int
        or minimum_factor_assignment_count <= 0
        or type(layout_domain) is not str
        or not layout_domain
        or type(acquisition_domain) is not str
        or not acquisition_domain
        or not callable(content_id)
    ):
        _fail("V76 projected applicability contract changed")
    rows = []
    batches = []
    candidate = None
    alignment = None
    signature = None
    issuance_label = None
    successes = 0
    epoch = 0
    retired = []
    history = []
    projection_compute = 0
    for label, batch in enumerate(
        ground._witness_blind_depth_frontier(adapter), 1  # noqa: SLF001
    ):
        if label > maximum_ground_support_labels:
            break
        rows.extend(batch)
        batches.append(batch)
        current = tuple(rows)
        try:
            proposed = synthesize_partial_factor_candidate_v15(
                current,
                adapter.catalogue,
                V51_FACTOR_TEMPLATE_PROJECTION,
                support_label_count=label,
                layout_domain=layout_domain,
                candidate_domain=acquisition_domain,
                candidate_content_id=content_id,
                minimum_factor_assignment_count=minimum_factor_assignment_count,
            )
            proposed_alignment = compile_coordinate_alignment_v60(
                verified,
                applicability_program,
                proposed,
                current,
                adapter.catalogue,
            )
            proposed_signature = _semantic_signature(
                proposed, proposed_alignment
            )
            projection_compute += (
                proposed_alignment["target_applicability_relation_evaluations"]
                + proposed_alignment["full_model_replay_row_evaluations"]
            )
        except Exception as error:
            if not error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            if signature is not None:
                retired.append(
                    {
                        "candidate_epoch": epoch,
                        "semantic_signature_sha256": signature,
                        "failed_ground_support_label": label,
                        "reason": "PROJECTION_OR_MODEL_REPLAY_FAILED",
                    }
                )
                candidate = None
                alignment = None
                signature = None
                issuance_label = None
                successes = 0
                epoch += 1
            history.append(
                {
                    "ground_support_label": label,
                    "candidate_epoch": epoch,
                    "candidate_available": False,
                    "constructor_error_type": type(error).__name__,
                    "stopped": False,
                }
            )
            continue
        if signature is None or proposed_signature != signature:
            if signature is not None:
                retired.append(
                    {
                        "candidate_epoch": epoch,
                        "semantic_signature_sha256": signature,
                        "failed_ground_support_label": label,
                        "reason": "SEMANTIC_PROJECTION_SIGNATURE_CHANGED",
                    }
                )
                epoch += 1
            candidate = proposed
            alignment = proposed_alignment
            signature = proposed_signature
            issuance_label = label
            successes = 0
            issued_now = True
        else:
            candidate = proposed
            alignment = proposed_alignment
            successes += 1
            issued_now = False
        threshold = confidence_denominator * (epoch + 1) * (epoch + 2)
        numerator = 2 ** (successes + 1) - 1
        denominator = successes + 1
        stopped = numerator * source_meta_prior_odds >= denominator * threshold
        history.append(
            {
                "ground_support_label": label,
                "candidate_epoch": epoch,
                "candidate_available": True,
                "candidate_issued": issued_now,
                "semantic_signature_sha256": signature,
                "post_issuance_exact_prediction_success_count": successes,
                "universal_mixture_evalue_numerator": numerator,
                "universal_mixture_evalue_denominator": denominator,
                "evalue_threshold": threshold,
                "source_meta_prior_odds": source_meta_prior_odds,
                "source_meta_prior_only_crossing": stopped and successes == 0,
                "stopped": stopped,
            }
        )
        if stopped:
            break
    if (
        candidate is None
        or alignment is None
        or signature is None
        or issuance_label is None
        or not history
        or history[-1].get("stopped") is not True
    ):
        _fail("V76 projected applicability did not close before its label cap")
    raw_documents = [row.to_document() for row in rows]
    action_documents = [row.to_document() for row in adapter.catalogue]
    payload = {
        "schema": "acfqp.generic_projected_low_label_applicability.v76",
        "family": adapter.family,
        "seed": adapter.seed,
        "source_model_id": verified[
            "projected_disagreement_successor_model_id"
        ],
        "source_applicability_program_id": applicability_program[
            "action_applicability_program_id"
        ],
        "ground_support_labels": len(batches),
        "raw_transition_rows": raw_documents,
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes(raw_documents)
        ).hexdigest(),
        "action_catalogue": action_documents,
        "action_catalogue_sha256": hashlib.sha256(
            canonical_json_bytes(action_documents)
        ).hexdigest(),
        "projected_target_candidate": copy.deepcopy(
            dict(candidate.public_document)
        ),
        "coordinate_alignment": copy.deepcopy(dict(alignment)),
        "coordinate_alignment_id": alignment["coordinate_alignment_id"],
        "semantic_projection_signature_sha256": signature,
        "candidate_issued_at_ground_support_label": issuance_label,
        "confidence_crossing_ground_support_label": len(batches),
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
        "projection_derivation_compute_events": projection_compute,
        "witness_blind_depth_stream_used": True,
        "terminal_witness_used_to_schedule_queries": False,
        "fixed_label_floor_used": False,
        "fixed_confirmation_block_used": False,
        "same_constructor_projection_replay_and_stopping_rule_in_prior_on_off_arms": True,
        "empirical_source_meta_prior_strength_preregistered_not_universal": True,
        "target_episode_outcomes_used": False,
        "source_model_or_applicability_refit": False,
        "projection_promoted_to_global_applicability_fact": False,
        "proposal_used_as_safety_authority": False,
        "complete_world_model_claimed": False,
    }
    document = {
        **payload,
        "applicability_id": content_id(acquisition_domain, payload),
    }
    return {
        "document": document,
        "candidate": candidate,
        "alignment": alignment,
        "rows": tuple(rows),
        "batches": tuple(batches),
    }


__all__ = ("acquire_projected_low_label_applicability_v76",)
