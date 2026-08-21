"""Acquire only the reusable partial factor required by source synthesis.

Earlier source-only campaigns inherited a matched sample-tax ablation and
therefore blocked whenever the irrelevant strict complete-model arm abstained.
This generic boundary consumes the same witness-blind source stream but runs
only the anonymous partial-factor arm.  It does not compare arms or claim a
sample-tax result; the resulting partial proposal remains non-authoritative.
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Mapping, NoReturn

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    exact_partial_factor_replay_v15,
    partial_factor_bit_codelength_stop_update_v15,
    synthesize_partial_factor_candidate_v15,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericPriorOnlyPartialAcquisitionV67Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPriorOnlyPartialAcquisitionV67Error(message)


def acquire_prior_only_partial_candidate_v67(
    adapter: Any,
    *,
    maximum_ground_support_labels: int,
    global_alpha_denominator: int,
    minimum_factor_assignment_count: int,
    layout_domain: str,
    acquisition_domain: str,
    content_id: Callable[[str, Any], str],
) -> dict[str, Any]:
    if (
        type(maximum_ground_support_labels) is not int
        or maximum_ground_support_labels <= 0
        or type(global_alpha_denominator) is not int
        or global_alpha_denominator < 2
        or type(minimum_factor_assignment_count) is not int
        or minimum_factor_assignment_count <= 0
        or type(layout_domain) is not str
        or not layout_domain
        or type(acquisition_domain) is not str
        or not acquisition_domain
        or not callable(content_id)
    ):
        _fail("V67 prior-only acquisition contract changed")
    rows: list[Any] = []
    batches: list[tuple[Any, ...]] = []
    candidate = None
    issued = 0
    invalidated = 0
    disagreements = 0
    epoch = 0
    successes = 0
    previous = None
    accepting_label = None
    history = []
    for labels, batch in enumerate(
        ground._witness_blind_depth_frontier(adapter), 1  # noqa: SLF001
    ):
        if labels > maximum_ground_support_labels:
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
                previous = candidate.public_document["candidate_id"]
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
                    layout_domain=layout_domain,
                    candidate_domain=acquisition_domain,
                    candidate_content_id=content_id,
                    minimum_factor_assignment_count=(
                        minimum_factor_assignment_count
                    ),
                )
                issued = labels
                if (
                    previous is not None
                    and candidate.public_document["candidate_id"] != previous
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
                candidate = None
        if candidate is None:
            continue
        stop = partial_factor_bit_codelength_stop_update_v15(
            candidate,
            current,
            adapter.catalogue,
            candidate_epoch=epoch,
            invalidated_candidate_count=invalidated,
            post_issuance_exact_prediction_success_count=successes,
            global_alpha_denominator=global_alpha_denominator,
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
        row_documents = [row.to_document() for row in current]
        payload = {
            "schema": "acfqp.generic_prior_only_partial_acquisition.v67",
            "family": adapter.family,
            "seed": adapter.seed,
            "arm": "ANONYMOUS_FACTOR_PRIOR_ON",
            "factor_prior_enabled": True,
            "ground_support_labels": labels,
            "raw_transition_count": len(current),
            "raw_transition_sha256": hashlib.sha256(
                canonical_json_bytes(row_documents)
            ).hexdigest(),
            "candidate": dict(candidate.public_document),
            "candidate_issued_at_support_label": issued,
            "invalidated_candidate_count": invalidated,
            "candidate_program_disagreement_count": disagreements,
            "candidate_epoch": epoch,
            "post_issuance_exact_prediction_success_count": successes,
            "first_accepting_observation_label": accepting_label,
            "terminal_stop_update": dict(stop),
            "stopping_history": history,
            "strict_no_prior_arm_executed": False,
            "matched_sample_tax_comparison_claimed": False,
            "partial_prediction_scope_only": True,
            "unknown_residual_outputs_claimed": False,
            "complete_world_model_claimed": False,
            "reachable_frontier_exhaustion_input_consumed": False,
            "proposal_used_as_safety_authority": False,
        }
        document = {
            **payload,
            "acquisition_id": content_id(acquisition_domain, payload),
        }
        return {
            "document": document,
            "candidate": candidate,
            "rows": current,
            "batches": tuple(batches),
        }
    _fail(
        "V67 prior-only partial acquisition did not close before its cap for "
        f"{adapter.family} seed {adapter.seed}"
    )


__all__ = ("acquire_prior_only_partial_candidate_v67",)
