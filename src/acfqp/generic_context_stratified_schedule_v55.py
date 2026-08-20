"""Outcome-blind round-robin across source contexts and relation strata."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericContextStratifiedScheduleV55Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericContextStratifiedScheduleV55Error(message)


def schedule_context_stratified_queries_v55(
    source_complete_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(source_complete_evidence) is not dict
        or source_complete_evidence.get(
            "contextual_action_supports_derived_from_catalogue_only"
        )
        is not True
        or source_complete_evidence.get(
            "unacquired_successor_or_terminal_used_for_action_supports"
        )
        is not False
    ):
        _fail("V55 source evidence changed")
    base = schedule_relation_covering_queries_v39(source_complete_evidence)
    groups = v42._groups(base["scheduled_raw_transition_rows"])  # noqa: SLF001
    if len(groups) != base["query_count"]:
        _fail("V55 predecessor schedule grouping changed")
    buckets: dict[int, list[tuple[int, list[dict[str, Any]]]]] = {}
    for base_index, group in enumerate(groups):
        contexts = {
            row.get("contextual_source_member_index")
            for row in group
            if type(row) is dict
        }
        if (
            len(contexts) != 1
            or any(type(value) is not int or value < 0 for value in contexts)
        ):
            _fail("V55 query group crossed source contexts")
        context = next(iter(contexts))
        buckets.setdefault(context, []).append((base_index, group))
    expected_contexts = list(range(len(source_complete_evidence["contextual_action_field_supports"])))
    if sorted(buckets) != expected_contexts:
        _fail("V55 context inventory changed")
    ranked = []
    round_index = 0
    while len(ranked) < len(groups):
        progressed = False
        for context in expected_contexts:
            values = buckets[context]
            if round_index < len(values):
                ranked.append((round_index, context, values[round_index]))
                progressed = True
        if not progressed:  # pragma: no cover
            raise AssertionError
        round_index += 1
    schedule_rows = []
    for index, (round_value, context, (base_index, group)) in enumerate(ranked):
        base_row = base["schedule"][base_index]
        schedule_rows.append(
            {
                "scheduled_query_index": index,
                "context_round": round_value,
                "contextual_source_member_index": context,
                "predecessor_relation_schedule_index": base_index,
                "predecessor_relation_signature_sha256": base_row[
                    "relation_signature_sha256"
                ],
                "query_projection": base_row["query_projection"],
                "raw_transition_row_count": len(group),
            }
        )
    payload = {
        "schema": "acfqp.generic_context_stratified_query_schedule.v55",
        "source_relation_covering_schedule_id": base["query_schedule_id"],
        "context_count": len(expected_contexts),
        "query_count": len(groups),
        "raw_transition_row_count": sum(len(row[2][1]) for row in ranked),
        "schedule": schedule_rows,
        "scheduled_raw_transition_rows": [
            item for row in ranked for item in row[2][1]
        ],
        "context_and_relation_round_robin": True,
        "context_derived_only_from_source_member_provenance": True,
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
        "context_stratified_query_schedule_id": hashlib.sha256(
            b"acfqp:generic-context-stratified-query-schedule:v55\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("schedule_context_stratified_queries_v55",)
