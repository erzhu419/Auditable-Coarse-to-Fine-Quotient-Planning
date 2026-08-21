"""Outcome-blind relation schedule balanced across source occurrences.

V39 covers anonymous relation-signature strata but, after source pooling, can
place every early query from one occurrence.  V66 retains the exact V39 rank
inside each observed occurrence-signature bucket and round-robins the buckets.
Only occurrence identity, pre-state, and anonymous action metadata affect the
schedule; successor, legality-after, terminal labels, and outcome tapes remain
unread by the ranking rule.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_adaptive_role_free_terminal_acquisition_v35 import (
    _groups,
)
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericOccurrenceBalancedRelationScheduleV66Error(ValueError):
    pass


_SCHEDULE_DOMAIN = b"acfqp:generic-occurrence-balanced-relation-schedule:v66\x00"


def _fail(message: str) -> NoReturn:
    raise GenericOccurrenceBalancedRelationScheduleV66Error(message)


def schedule_occurrence_balanced_relation_queries_v66(
    source_complete_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    if type(source_complete_evidence) is not dict:
        _fail("V66 source evidence changed")
    base = schedule_relation_covering_queries_v39(source_complete_evidence)
    groups = _groups(base["scheduled_raw_transition_rows"])
    buckets: dict[tuple[int, ...], list[tuple[int, list[dict[str, Any]]]]] = {}
    for base_index, group in enumerate(groups):
        occurrences = tuple(sorted({row.get("occurrence") for row in group}))
        if (
            not occurrences
            or any(type(value) is not int or value < 0 for value in occurrences)
        ):
            _fail("V66 source occurrence identity changed")
        buckets.setdefault(occurrences, []).append((base_index, group))
    ordered = []
    for round_index in range(max(len(rows) for rows in buckets.values())):
        for signature in sorted(buckets):
            values = buckets[signature]
            if round_index < len(values):
                base_index, group = values[round_index]
                ordered.append((round_index, signature, base_index, group))
    if len(ordered) != len(groups):  # pragma: no cover
        raise AssertionError
    payload = {
        "schema": "acfqp.generic_occurrence_balanced_relation_schedule.v66",
        "base_v39_query_schedule_id": base["query_schedule_id"],
        "base_v39_query_count": base["query_count"],
        "query_count": len(ordered),
        "raw_transition_row_count": sum(len(row[3]) for row in ordered),
        "occurrence_signature_bucket_count": len(buckets),
        "occurrence_signatures": [list(row) for row in sorted(buckets)],
        "schedule": [
            {
                "scheduled_query_index": index,
                "occurrence_balance_round": round_index,
                "occurrence_signature": list(signature),
                "base_v39_scheduled_query_index": base_index,
                "raw_transition_row_count": len(group),
            }
            for index, (round_index, signature, base_index, group) in enumerate(
                ordered
            )
        ],
        "scheduled_raw_transition_rows": [
            copy.deepcopy(item) for row in ordered for item in row[3]
        ],
        "occurrence_identity_accessed": True,
        "pre_state_and_anonymous_action_relations_inherited_from_v39": True,
        "post_state_fields_accessed_by_ranking": False,
        "legality_after_accessed_by_ranking": False,
        "terminal_acceptance_label_accessed_by_ranking": False,
        "outcome_tape_accessed_by_ranking": False,
        "fixed_label_floor_present": False,
        "fixed_confirmation_block_present": False,
        "schedule_promoted_to_safety_authority": False,
    }
    return {
        **payload,
        "occurrence_balanced_query_schedule_id": hashlib.sha256(
            _SCHEDULE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("schedule_occurrence_balanced_relation_queries_v66",)
