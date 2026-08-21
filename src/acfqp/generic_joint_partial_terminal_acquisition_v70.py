"""Jointly stop reusable partial-factor and target-terminal acquisition.

The reusable factor proposal closes first on the existing witness-blind depth
stream.  The same stream is then continued, without a terminal witness or a
fixed confirmation block, until the current target-local terminal proposal
crosses its prequential confidence boundary.  Coordinate alignment is frozen
from the factor prefix; later calibration rows cannot change it.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Callable, Mapping, NoReturn

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp.generic_prior_only_partial_acquisition_v67 import (
    acquire_prior_only_partial_candidate_v67,
)
from acfqp.generic_terminal_overlay_version_space_planner_v69 import (
    GenericTerminalOverlayVersionSpacePlannerV69Error,
    prepare_terminal_overlay_target_inputs_v69,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericJointPartialTerminalAcquisitionV70Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericJointPartialTerminalAcquisitionV70Error(message)


def _batch_documents(batch: tuple[Any, ...]) -> list[dict[str, Any]]:
    return [row.to_document() for row in batch]


def acquire_joint_partial_terminal_prefix_v70(
    adapter: Any,
    model: Mapping[str, Any],
    *,
    maximum_ground_support_labels: int,
    global_alpha_denominator: int,
    minimum_factor_assignment_count: int,
    terminal_confidence_denominator: int,
    maximum_terminal_program_candidates: int,
    layout_domain: str,
    partial_acquisition_domain: str,
    joint_acquisition_domain: str,
    content_id: Callable[[str, Any], str],
) -> dict[str, Any]:
    if (
        type(maximum_ground_support_labels) is not int
        or maximum_ground_support_labels <= 0
        or type(terminal_confidence_denominator) is not int
        or terminal_confidence_denominator <= 1
        or type(maximum_terminal_program_candidates) is not int
        or not 1 <= maximum_terminal_program_candidates <= 128
        or type(joint_acquisition_domain) is not str
        or not joint_acquisition_domain
        or not callable(content_id)
    ):
        _fail("V70 joint acquisition contract changed")
    partial = acquire_prior_only_partial_candidate_v67(
        adapter,
        maximum_ground_support_labels=maximum_ground_support_labels,
        global_alpha_denominator=global_alpha_denominator,
        minimum_factor_assignment_count=minimum_factor_assignment_count,
        layout_domain=layout_domain,
        acquisition_domain=partial_acquisition_domain,
        content_id=content_id,
    )
    stream = iter(ground._witness_blind_depth_frontier(adapter))  # noqa: SLF001
    batches: list[tuple[Any, ...]] = []
    for expected in partial["batches"]:
        try:
            observed = next(stream)
        except StopIteration:
            _fail("V70 witness-blind stream ended inside its factor prefix")
        if _batch_documents(observed) != _batch_documents(expected):
            _fail("V70 reconstructed factor prefix changed")
        batches.append(observed)
    if len(batches) > maximum_ground_support_labels:
        _fail("V70 factor prefix crossed the joint label cap")

    while True:
        rows = tuple(row for batch in batches for row in batch)
        try:
            alignment, overlay, projected, candidate, aligned_rows = (
                prepare_terminal_overlay_target_inputs_v69(
                    adapter,
                    partial["candidate"],
                    rows,
                    model,
                    layout_domain=layout_domain,
                    layout_observed_rows=partial["rows"],
                    terminal_confidence_denominator=(
                        terminal_confidence_denominator
                    ),
                    maximum_terminal_program_candidates=(
                        maximum_terminal_program_candidates
                    ),
                )
            )
        except GenericTerminalOverlayVersionSpacePlannerV69Error as error:
            if str(error) != (
                "V69 terminal overlay did not close before its common-prefix cap"
            ):
                raise
            if len(batches) >= maximum_ground_support_labels:
                _fail("V70 terminal overlay did not close before its label cap")
            try:
                batches.append(next(stream))
            except StopIteration:
                _fail(
                    "V70 terminal overlay did not close before the witness-blind "
                    "stream ended"
                )
            continue
        break

    row_documents = [row.to_document() for row in rows]
    aligned_documents = [row.to_document() for row in aligned_rows]
    action_documents = [row.to_document() for row in adapter.catalogue]
    partial_labels = partial["document"]["ground_support_labels"]
    labels = len(batches)
    if (
        labels < partial_labels
        or overlay["joint_acquisition_stop_ground_support_labels"] != labels
        or overlay["candidate_confidence_crossing_ground_support_label"]
        > labels
    ):
        _fail("V70 factor/terminal stop join changed")
    payload = {
        "schema": "acfqp.generic_joint_partial_terminal_acquisition.v70",
        "family": adapter.family,
        "seed": adapter.seed,
        "source_model_id": model["joint_successor_version_space_model_id"],
        "partial_acquisition": copy.deepcopy(partial["document"]),
        "partial_acquisition_id": partial["document"]["acquisition_id"],
        "partial_factor_stop_ground_support_labels": partial_labels,
        "terminal_confidence_crossing_ground_support_label": overlay[
            "candidate_confidence_crossing_ground_support_label"
        ],
        "joint_stop_ground_support_labels": labels,
        "terminal_calibration_incremental_ground_support_labels": (
            labels - partial_labels
        ),
        "raw_transition_rows": row_documents,
        "raw_transition_row_count": len(row_documents),
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes(row_documents)
        ).hexdigest(),
        "aligned_transition_rows": aligned_documents,
        "aligned_transition_row_count": len(aligned_documents),
        "aligned_transition_sha256": hashlib.sha256(
            canonical_json_bytes(aligned_documents)
        ).hexdigest(),
        "action_catalogue": action_documents,
        "action_catalogue_sha256": hashlib.sha256(
            canonical_json_bytes(action_documents)
        ).hexdigest(),
        "alignment": copy.deepcopy(alignment),
        "terminal_overlay": copy.deepcopy(overlay),
        "witness_blind_depth_stream_used": True,
        "terminal_witness_used_to_schedule_queries": False,
        "fixed_label_floor_used": False,
        "fixed_confirmation_block_used": False,
        "candidate_disagreement_mdl_and_confidence_stopping_only": True,
        "alignment_frozen_at_partial_factor_stop": True,
        "target_episode_outcomes_used": False,
        "source_residual_model_refit": False,
        "proposal_used_as_safety_authority": False,
        "complete_world_model_claimed": False,
    }
    document = {
        **payload,
        "joint_acquisition_id": content_id(joint_acquisition_domain, payload),
    }
    return {
        "document": document,
        "partial": partial,
        "alignment": alignment,
        "terminal_overlay": overlay,
        "projected_adapter": projected,
        "candidate": candidate,
        "rows": rows,
        "aligned_rows": aligned_rows,
        "batches": tuple(batches),
    }


__all__ = ("acquire_joint_partial_terminal_prefix_v70",)
