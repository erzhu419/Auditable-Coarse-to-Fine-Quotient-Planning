"""Retain every raw row required to reconstruct a V28 terminal program.

V30 deliberately returned only query-local rows, while its terminal relation
program also consumed the common partial-acquisition rows.  V31 is an additive
source-complete envelope: it runs the unchanged V30 planner, persists the exact
union of source rows, and binds that evidence to the emitted V28 program.  It
does not change planning or safety authority.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relational_terminal_program_v28 import (
    synthesize_relational_terminal_program_v28,
)
from acfqp.generic_relational_world_model_certificate_planner_v30 import (
    run_relational_world_model_certificate_episode_v30,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericSourceCompleteRelationalWorldModelV31Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericSourceCompleteRelationalWorldModelV31Error(message)


def run_source_complete_relational_world_model_episode_v31(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    *,
    residual_prior_library: Mapping[str, Any] | None,
    episode_index: int,
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    confidence_denominator: int = 64,
    maximum_terminal_program_candidates_to_try: int = 32,
    maximum_relational_support_branch_evaluations: int = 1_000_000,
    relational_support_feasible_beam_width: int = 32,
) -> dict[str, Any]:
    episode = run_relational_world_model_certificate_episode_v30(
        adapter,
        candidate,
        observed_rows,
        residual_prior_library=residual_prior_library,
        episode_index=episode_index,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        confidence_denominator=confidence_denominator,
        maximum_terminal_program_candidates_to_try=(
            maximum_terminal_program_candidates_to_try
        ),
        maximum_relational_support_branch_evaluations=(
            maximum_relational_support_branch_evaluations
        ),
        relational_support_feasible_beam_width=(
            relational_support_feasible_beam_width
        ),
    )
    source_payload = {
        "schema": "acfqp.source_complete_terminal_program_evidence.v31",
        "layout": candidate.public_document["layout"],
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "common_partial_raw_transition_rows": [
            row.to_document() for row in observed_rows
        ],
        "query_local_raw_transition_rows": episode["raw_local_transition_rows"],
        "raw_transition_rows": [
            *(row.to_document() for row in observed_rows),
            *episode["raw_local_transition_rows"],
        ],
        "common_partial_row_count": len(observed_rows),
        "query_local_row_count": len(episode["raw_local_transition_rows"]),
        "all_v28_source_rows_retained": True,
    }
    evidence = {
        **source_payload,
        "source_evidence_id": hashlib.sha256(
            b"acfqp:source-complete-terminal-program-evidence:v31\x00"
            + canonical_json_bytes(source_payload)
        ).hexdigest(),
    }
    replay_input = {
        "layout": evidence["layout"],
        "unknown_residual_target_columns": evidence[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": evidence["raw_transition_rows"],
    }
    reconstructed = synthesize_relational_terminal_program_v28(replay_input)
    if reconstructed != episode["final_relational_terminal_program"]:
        _fail("V31 retained source rows do not reconstruct the emitted V28 program")
    payload = {
        "schema": "acfqp.generic_source_complete_relational_world_model_episode.v31",
        "predecessor_v30_episode": episode,
        "terminal_program_source_evidence": evidence,
        "source_evidence_id": evidence["source_evidence_id"],
        "terminal_program_id": reconstructed["terminal_program_id"],
        "all_v28_source_rows_retained": True,
        "producer_free_terminal_program_reconstruction_enabled": True,
        "planning_behavior_changed_from_v30": False,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "relational_abstract_plan_used_as_safety_authority": False,
        "complete_world_model_synthesized": False,
    }
    return {
        **payload,
        "source_complete_episode_id": hashlib.sha256(
            b"acfqp:generic-source-complete-relational-world-model:v31\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_source_complete_relational_world_model_episode_v31",)
