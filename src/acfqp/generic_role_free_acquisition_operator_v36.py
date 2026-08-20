"""Outcome-blind heuristic scheduling for role-free terminal acquisition.

The operator sees only each query's pre-state and anonymous action descriptor.
With a structural prior it ranks queries near an anonymous equality/order
boundary among already modeled coordinates; without a prior it uses a frozen
content-hash order.  Post-states, legality-after, terminal labels, and outcome
tapes are inaccessible to scheduling.  V35 remains the shared constructor and
stop rule.
"""

from __future__ import annotations

import copy
import hashlib
from itertools import combinations
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.generic_adaptive_role_free_terminal_acquisition_v35 import (
    acquire_adaptive_role_free_terminal_program_v35,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericRoleFreeAcquisitionOperatorV36Error(ValueError):
    pass


# This was a development-only diagnostic, not a preregistered campaign.  It is
# retained because it falsified the first hypothesis that an outcome-blind
# boundary schedule plus the V35 MDL stop was already sufficient.  A successor
# must use a calibrated prequential stop; it may not erase or relabel this run.
PRESERVED_V36_DEVELOPMENT_FAILURE = MappingProxyType(
    {
        "schema": "acfqp.role_free_acquisition_development_failure.v36",
        "family": "MAINTENANCE_CASCADE",
        "seed": 720_974,
        "prior_status": "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE",
        "prior_stop_labels": 9,
        "prior_full_query_count": 91,
        "prior_heldout_query_count": 82,
        "strict_status": "PROPOSAL_ISSUED_HELDOUT_VALIDATED",
        "strict_stop_labels": 13,
        "strict_full_query_count": 91,
        "strict_heldout_query_count": 78,
        "registered_scientific_result": False,
        "safety_authority": False,
        "failure_preserved": True,
    }
)


def _fail(message: str) -> NoReturn:
    raise GenericRoleFreeAcquisitionOperatorV36Error(message)


def _query_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    action = row.get("selected_action")
    pre = row.get("pre_vector")
    if (
        type(pre) is not list
        or type(action) is not dict
        or type(action.get("action_key")) is not int
        or type(action.get("anonymous_fields")) is not list
    ):
        _fail("V36 pre-state/action query projection changed")
    return {
        "pre_vector": pre,
        "action_key": action["action_key"],
        "anonymous_action_fields": action["anonymous_fields"],
    }


def _groups(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped = {}
    order = []
    for row in rows:
        projection = _query_projection(row)
        key = (
            tuple(projection["pre_vector"]),
            projection["action_key"],
        )
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)
    return [grouped[key] for key in order]


def schedule_role_free_acquisition_queries_v36(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if type(source_complete_evidence) is not dict:
        _fail("V36 source evidence changed")
    layout = source_complete_evidence.get("layout")
    unknown = source_complete_evidence.get("unknown_residual_target_columns")
    rows = source_complete_evidence.get("raw_transition_rows")
    if (
        type(layout) is not dict
        or type(unknown) is not list
        or unknown != sorted(set(unknown))
        or type(rows) is not list
        or not rows
    ):
        _fail("V36 source inventory changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V36 state layout changed")
    groups = _groups(rows)
    known = tuple(index for index in range(len(order)) if index not in unknown)
    if len(known) < 2:
        _fail("V36 heuristic needs at least two modeled coordinates")
    structural_prior = role_free_template_library is not None
    ranked = []
    source_projections = []
    for original_index, group in enumerate(groups):
        projection = _query_projection(group[0])
        source_projections.append(projection)
        identity_sha = hashlib.sha256(canonical_json_bytes(projection)).hexdigest()
        if structural_prior:
            canonical_pre = [projection["pre_vector"][raw] for raw in order]
            boundary_distance = min(
                abs(canonical_pre[left] - canonical_pre[right])
                for left, right in combinations(known, 2)
            )
            score = (boundary_distance, identity_sha)
            score_document = {
                "anonymous_modeled_coordinate_boundary_distance": boundary_distance,
                "content_hash_tiebreak": identity_sha,
            }
        else:
            score = (identity_sha,)
            score_document = {"content_hash_order": identity_sha}
        ranked.append((score, original_index, group, projection, score_document))
    ranked.sort(key=lambda row: (row[0], row[1]))
    scheduled_rows = [item for row in ranked for item in row[2]]
    schedule = [
        {
            "scheduled_query_index": index,
            "original_query_index": row[1],
            "query_projection": row[3],
            "outcome_blind_score": row[4],
            "raw_transition_row_count": len(row[2]),
        }
        for index, row in enumerate(ranked)
    ]
    payload = {
        "schema": "acfqp.generic_role_free_acquisition_query_schedule.v36",
        "arm": (
            "ROLE_FREE_HEURISTIC_OPERATOR_ON"
            if structural_prior
            else "STRICT_CONTENT_HASH_SCHEDULE"
        ),
        "role_free_template_library_id": (
            None
            if role_free_template_library is None
            else role_free_template_library.get("template_library_id")
        ),
        "query_source_projection_sha256": hashlib.sha256(
            canonical_json_bytes(source_projections)
        ).hexdigest(),
        "query_count": len(groups),
        "raw_transition_row_count": len(rows),
        "outcome_blind_score_evaluation_count": (
            len(groups) * (len(known) * (len(known) - 1) // 2)
            if structural_prior
            else len(groups)
        ),
        "schedule": schedule,
        "scheduled_raw_transition_rows": scheduled_rows,
        "pre_state_fields_accessed": True,
        "anonymous_action_fields_accessed": True,
        "post_state_fields_accessed": False,
        "legality_after_accessed": False,
        "terminal_acceptance_label_accessed": False,
        "outcome_tape_accessed": False,
        "heuristic_operator_not_safety_authority": True,
    }
    return {
        **payload,
        "query_schedule_id": hashlib.sha256(
            b"acfqp:generic-role-free-acquisition-query-schedule:v36\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_role_free_heuristic_acquisition_v36(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    schedule = schedule_role_free_acquisition_queries_v36(
        source_complete_evidence,
        role_free_template_library=role_free_template_library,
    )
    ordered = copy.deepcopy(source_complete_evidence)
    ordered["raw_transition_rows"] = schedule["scheduled_raw_transition_rows"]
    acquisition = acquire_adaptive_role_free_terminal_program_v35(
        ordered,
        role_free_template_library=role_free_template_library,
        confidence_denominator=confidence_denominator,
    )
    payload = {
        "schema": "acfqp.generic_role_free_heuristic_acquisition.v36",
        "query_schedule": schedule,
        "adaptive_acquisition": acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "adaptive_acquisition_id": acquisition["adaptive_acquisition_id"],
        "same_v35_constructor_and_stop_rule_in_both_arms": True,
        "only_prior_controlled_scheduler_and_program_code_length_differ": True,
        "outcome_witness_used_for_scheduling": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "heuristic_operator_not_safety_authority": True,
    }
    return {
        **payload,
        "heuristic_acquisition_id": hashlib.sha256(
            b"acfqp:generic-role-free-heuristic-acquisition:v36\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "run_role_free_heuristic_acquisition_v36",
    "schedule_role_free_acquisition_queries_v36",
)
