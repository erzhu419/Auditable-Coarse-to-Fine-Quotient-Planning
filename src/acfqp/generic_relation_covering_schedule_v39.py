"""Outcome-blind relation-signature covering query schedule.

Each query is projected to anonymous pre-state and action metadata.  V39 forms
only generic three-way order signatures among modeled state coordinates and
among anonymous action fields, then round-robins the observed signature strata.
No successor, legality, terminal, or outcome field participates.  The schedule
is intended to expose structurally diverse confirmations early; it grants no
model or safety authority.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


class GenericRelationCoveringScheduleV39Error(ValueError):
    pass


PRESERVED_V39_RETROSPECTIVE_DIAGNOSTIC = MappingProxyType(
    {
        "schema": "acfqp.relation_covering_retrospective_diagnostic.v39",
        "frozen_source_campaign_id": (
            "a8a9ebead0bcfeb1587be1a6b21ddb11189ec74e26d871ab5ada0ec279261e17"
        ),
        "prior_validated_occurrences": 5,
        "prior_failed_noncertificate_occurrences": 1,
        "prior_counterfactual_consumed_labels": 168,
        "strict_validated_occurrences": 5,
        "strict_failed_noncertificate_occurrences": 1,
        "strict_counterfactual_consumed_labels": 168,
        "registered_scientific_result": False,
        "sample_tax_reduction_observed": False,
        "failure_preserved": True,
    }
)


def _fail(message: str) -> NoReturn:
    raise GenericRelationCoveringScheduleV39Error(message)


def _compare(left: int, right: int) -> int:
    return -1 if left < right else (1 if left > right else 0)


def _projection(row: Mapping[str, Any]) -> dict[str, Any]:
    action = row.get("selected_action")
    pre = row.get("pre_vector")
    if (
        type(pre) is not list
        or any(type(value) is not int for value in pre)
        or type(action) is not dict
        or type(action.get("action_key")) is not int
        or type(action.get("anonymous_fields")) is not list
        or any(type(value) is not int for value in action["anonymous_fields"])
    ):
        _fail("V39 query projection changed")
    return {
        "pre_vector": pre,
        "action_key": action["action_key"],
        "anonymous_action_fields": action["anonymous_fields"],
    }


def _groups(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped = {}
    order = []
    for row in rows:
        projection = _projection(row)
        key = (tuple(projection["pre_vector"]), projection["action_key"])
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)
    return [grouped[key] for key in order]


def _signature(
    projection: Mapping[str, Any], order: list[int], known: tuple[int, ...]
) -> dict[str, Any]:
    canonical_pre = [projection["pre_vector"][raw] for raw in order]
    action = projection["anonymous_action_fields"]
    state_relations = []
    for left_offset, left in enumerate(known):
        for right in known[left_offset + 1 :]:
            state_relations.append(
                {
                    "left_anonymous_coordinate": left,
                    "right_anonymous_coordinate": right,
                    "three_way_order": _compare(
                        canonical_pre[left], canonical_pre[right]
                    ),
                }
            )
    action_relations = []
    for left in range(len(action)):
        for right in range(left + 1, len(action)):
            action_relations.append(
                {
                    "left_anonymous_action_field": left,
                    "right_anonymous_action_field": right,
                    "three_way_order": _compare(action[left], action[right]),
                }
            )
    return {
        "modeled_pre_coordinate_relations": state_relations,
        "anonymous_action_field_relations": action_relations,
        "action_field_count": len(action),
    }


def schedule_relation_covering_queries_v39(
    source_complete_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    if type(source_complete_evidence) is not dict:
        _fail("V39 source evidence changed")
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
        _fail("V39 source inventory changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V39 state layout changed")
    known = tuple(index for index in range(len(order)) if index not in unknown)
    if len(known) < 2:
        _fail("V39 needs at least two modeled coordinates")
    groups = _groups(rows)
    strata: dict[bytes, list[tuple[str, int, list[dict[str, Any]], dict[str, Any], dict[str, Any]]]] = {}
    source_projections = []
    for original_index, group in enumerate(groups):
        projection = _projection(group[0])
        source_projections.append(projection)
        signature = _signature(projection, order, known)
        encoded = canonical_json_bytes(signature)
        identity_sha = hashlib.sha256(canonical_json_bytes(projection)).hexdigest()
        strata.setdefault(encoded, []).append(
            (identity_sha, original_index, group, projection, signature)
        )
    for values in strata.values():
        values.sort(key=lambda row: (row[0], row[1]))
    ordered_strata = sorted(
        strata,
        key=lambda encoded: (
            len(strata[encoded]),
            hashlib.sha256(encoded).hexdigest(),
        ),
    )
    ranked = []
    round_index = 0
    while len(ranked) < len(groups):
        progressed = False
        for encoded in ordered_strata:
            values = strata[encoded]
            if round_index < len(values):
                ranked.append((round_index, encoded, values[round_index]))
                progressed = True
        if not progressed:  # pragma: no cover
            raise AssertionError
        round_index += 1
    payload = {
        "schema": "acfqp.generic_relation_covering_query_schedule.v39",
        "query_source_projection_sha256": hashlib.sha256(
            canonical_json_bytes(source_projections)
        ).hexdigest(),
        "query_count": len(groups),
        "raw_transition_row_count": len(rows),
        "relation_signature_stratum_count": len(strata),
        "modeled_coordinate_pair_evaluation_count": (
            len(groups) * (len(known) * (len(known) - 1) // 2)
        ),
        "schedule": [
            {
                "scheduled_query_index": index,
                "coverage_round": row[0],
                "original_query_index": row[2][1],
                "query_projection": row[2][3],
                "relation_signature": row[2][4],
                "relation_signature_sha256": hashlib.sha256(row[1]).hexdigest(),
                "stratum_size": len(strata[row[1]]),
                "raw_transition_row_count": len(row[2][2]),
            }
            for index, row in enumerate(ranked)
        ],
        "scheduled_raw_transition_rows": [
            item for row in ranked for item in row[2][2]
        ],
        "pre_state_fields_accessed": True,
        "anonymous_action_fields_accessed": True,
        "post_state_fields_accessed": False,
        "legality_after_accessed": False,
        "terminal_acceptance_label_accessed": False,
        "outcome_tape_accessed": False,
        "fixed_label_floor_present": False,
        "coverage_schedule_not_safety_authority": True,
    }
    return {
        **payload,
        "query_schedule_id": hashlib.sha256(
            b"acfqp:generic-relation-covering-query-schedule:v39\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "PRESERVED_V39_RETROSPECTIVE_DIAGNOSTIC",
    "schedule_relation_covering_queries_v39",
)
