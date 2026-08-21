"""Partial acquisition for a source-unseen higher-order residual domain.

The prior arm retains only exact cross-schema factor assignments.  A matched
strict control gets the identical raw prefix and makes one complete-model
construction attempt with the frozen generic grammar.  Failure to express an
output is a typed negative control, not an infeasibility or planning claim.
"""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v119 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as v59
from acfqp.generic_atomic_expression_world_model_v4 import (
    ATOMIC_COMPOSITION_MAX_DEPTH_V4,
    GENERIC_ATOMIC_OPCODES_V4,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    exact_partial_factor_replay_v15,
    partial_factor_bit_codelength_stop_update_v15,
    synthesize_partial_factor_candidate_v15,
)


class SourceUnseenPartialAcquisitionV119Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise SourceUnseenPartialAcquisitionV119Error(message)


def _identifier(domain: str, payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {**payload, key: domains.extension_content_id_v119(domain, payload)}


def acquire_source_unseen_partial_model_v119(
    adapter: Any,
    factor_library: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    rows: list[Any] = []
    batches: list[tuple[Any, ...]] = []
    candidate = None
    issued = invalidated = disagreements = epoch = successes = 0
    previous_id = None
    accepting_label = None
    history: list[dict[str, Any]] = []
    maximum = config["families"][adapter.family]["maximum_acquisition_labels"]
    for labels, batch in enumerate(
        v59.predecessor.predecessor.ground._witness_blind_depth_frontier(adapter), 1
    ):
        if labels > maximum:
            break
        rows.extend(batch)
        batches.append(batch)
        current = tuple(rows)
        if accepting_label is None and any(
            row.terminal_acceptance_after is True for row in batch
        ):
            accepting_label = labels
        if candidate is not None:
            replay = exact_partial_factor_replay_v15(
                candidate, current, adapter.catalogue
            )
            if replay["exact"] is True:
                successes += 1
            else:
                previous_id = candidate.public_document["candidate_id"]
                candidate = None
                invalidated += 1
                epoch += 1
                successes = 0
        if candidate is None:
            try:
                candidate = synthesize_partial_factor_candidate_v15(
                    current,
                    adapter.catalogue,
                    V51_FACTOR_TEMPLATE_PROJECTION,
                    support_label_count=labels,
                    layout_domain=config["generic_domains"]["layout"],
                    candidate_domain=config["successor_domains"]["acquisition"],
                    candidate_content_id=v59.domains.extension_content_id_v59,
                    minimum_factor_assignment_count=config[
                        "minimum_reusable_factor_count"
                    ],
                )
                issued = labels
                if (
                    previous_id is not None
                    and candidate.public_document["candidate_id"] != previous_id
                ):
                    disagreements += 1
            except Exception as error:
                history.append(
                    {
                        "support_label_count": labels,
                        "candidate_available": False,
                        "constructor_error_type": type(error).__name__,
                    }
                )
                continue
        stop = partial_factor_bit_codelength_stop_update_v15(
            candidate,
            current,
            adapter.catalogue,
            candidate_epoch=epoch,
            invalidated_candidate_count=invalidated,
            post_issuance_exact_prediction_success_count=successes,
            global_alpha_denominator=config["global_alpha_denominator"],
        )
        history.append(
            {
                "support_label_count": labels,
                "candidate_available": True,
                "candidate_id": candidate.public_document["candidate_id"],
                "stopped_by_true_bits_and_universal_evidence": stop["stopped"],
                "accepting_projection_available": accepting_label is not None,
            }
        )
        if stop["stopped"] is not True or accepting_label is None:
            continue
        partial_payload = {
            "schema": "acfqp.source_unseen_partial_acquisition.v119",
            "family": adapter.family,
            "seed": adapter.seed,
            "arm": "ANONYMOUS_FACTOR_PRIOR_ON",
            "factor_prior_enabled": True,
            "ground_support_labels": labels,
            "raw_transition_count": len(current),
            "raw_transition_sha256": v59.predecessor.predecessor.ground._raw_sha(
                current
            ),
            "candidate": dict(candidate.public_document),
            "candidate_issued_at_support_label": issued,
            "invalidated_candidate_count": invalidated,
            "candidate_program_disagreement_count": disagreements,
            "candidate_epoch": epoch,
            "post_issuance_exact_prediction_success_count": successes,
            "first_accepting_observation_label": accepting_label,
            "terminal_stop_update": dict(stop),
            "stopping_history": history,
            "same_witness_blind_raw_prefix_as_strict_control": True,
            "domain_source_available_to_synthesizer": False,
            "partial_prediction_scope_only": True,
            "unknown_residual_outputs_claimed": False,
            "complete_world_model_claimed": False,
            "planning_authority_present": False,
            "reachable_frontier_exhaustion_input_consumed": False,
            "heuristic_mdl_information_units_consumed": False,
            "predictive_evidence_to_mdl_credit_consumed": False,
        }
        partial_document = _identifier(
            domains.CONSTRUCTION_K7_SOURCE_UNSEEN_PARTIAL_ACQUISITION_V119_DOMAIN,
            partial_payload,
            "acquisition_id",
        )
        strict_candidate = None
        strict_error_type = None
        try:
            strict_candidate = v59.predecessor.predecessor.ground._candidate(
                current, adapter.catalogue, factor_library, labels, config
            )
        except Exception as error:
            strict_error_type = type(error).__name__
        strict_payload = {
            "schema": "acfqp.source_unseen_strict_complete_model_control.v119",
            "family": adapter.family,
            "seed": adapter.seed,
            "arm": "STRICT_NO_PRIOR_SINGLE_MATCHED_PREFIX_ATTEMPT",
            "factor_prior_enabled": False,
            "ground_support_labels": labels,
            "raw_transition_count": len(current),
            "raw_transition_sha256": partial_payload["raw_transition_sha256"],
            "matched_partial_acquisition_id": partial_document["acquisition_id"],
            "generic_atomic_composition_max_depth": ATOMIC_COMPOSITION_MAX_DEPTH_V4,
            "generic_atomic_opcode_names": [row[0] for row in GENERIC_ATOMIC_OPCODES_V4],
            "attempt_count": 1,
            "outcome_kind": (
                "COMPLETE_CANDIDATE_SYNTHESIZED"
                if strict_candidate is not None
                else "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR"
            ),
            "complete_candidate": (
                None
                if strict_candidate is None
                else dict(strict_candidate.public_document)
            ),
            "constructor_error_type": strict_error_type,
            "typed_rejection_is_not_domain_infeasibility": True,
            "typed_rejection_is_not_planning_failure": True,
            "strict_control_used_for_safety_authority": False,
            "sample_efficiency_sign_claimed": False,
        }
        strict_document = _identifier(
            domains.CONSTRUCTION_K7_SOURCE_UNSEEN_STRICT_CONTROL_V119_DOMAIN,
            strict_payload,
            "strict_control_id",
        )
        return {
            "partial": {
                "document": partial_document,
                "candidate": candidate,
                "rows": current,
                "batches": tuple(batches),
            },
            "strict_control": {"document": strict_document},
        }
    _fail(
        "V119 source-unseen partial acquisition did not stop before its cap for "
        f"{adapter.family} seed {adapter.seed}"
    )


__all__ = (
    "SourceUnseenPartialAcquisitionV119Error",
    "acquire_source_unseen_partial_model_v119",
)
