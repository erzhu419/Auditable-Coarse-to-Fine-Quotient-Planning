"""Partition anonymous source evidence before compatibility-safe pooling.

V48 deliberately rejects a heterogeneous source list.  V50 turns that
rejection into an explicit structural routing step: it derives an exact
compatibility signature from discovered layouts, partitions without family or
outcome information, and invokes V48 only inside groups where its precondition
holds.  Singleton groups remain valid empirical source streams; they are not
silently discarded or relabelled as pooled evidence.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.generic_canonical_source_pool_v48 import (
    pool_canonical_source_evidence_v48,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericStructuralSourcePartitionV50Error(ValueError):
    pass


_PARTITION_DOMAIN = b"acfqp:generic-structural-source-partition:v50\x00"
_SINGLETON_DOMAIN = b"acfqp:generic-singleton-source-group:v50\x00"


def _fail(message: str) -> NoReturn:
    raise GenericStructuralSourcePartitionV50Error(message)


def _permutation(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or any(type(item) is not int for item in value)
        or sorted(value) != list(range(len(value)))
    ):
        _fail(f"V50 {label} changed")
    return value


def _descriptor(member: Mapping[str, Any]) -> dict[str, Any]:
    evidence = member.get("source_evidence")
    if type(evidence) is not dict:
        _fail("V50 source evidence changed")
    layout = evidence.get("layout")
    if type(layout) is not dict:
        _fail("V50 discovered layout changed")
    state_order = _permutation(
        layout.get("state_canonical_to_raw"), "state permutation"
    )
    action_order = _permutation(
        layout.get("action_canonical_to_raw"), "action permutation"
    )
    unknown = evidence.get("unknown_residual_target_columns")
    if (
        type(unknown) is not list
        or unknown != sorted(set(unknown))
        or any(type(value) is not int for value in unknown)
    ):
        _fail("V50 residual coordinate inventory changed")
    descriptor = {
        "state_width": len(state_order),
        "action_field_width": len(action_order),
        "unknown_residual_target_columns": list(unknown),
        "schema_signature": copy.deepcopy(layout.get("schema_signature")),
        "state_structural_colors": copy.deepcopy(
            layout.get("state_structural_colors")
        ),
        "action_structural_colors": copy.deepcopy(
            layout.get("action_structural_colors")
        ),
    }
    if (
        type(descriptor["schema_signature"]) is not str
        or type(descriptor["state_structural_colors"]) is not list
        or type(descriptor["action_structural_colors"]) is not list
    ):
        _fail("V50 structural descriptor changed")
    return descriptor


def _singleton(member: Mapping[str, Any], signature_id: str) -> dict[str, Any]:
    evidence = copy.deepcopy(member["source_evidence"])
    rows = evidence.get("raw_transition_rows")
    if type(rows) is not list or not rows:
        _fail("V50 singleton transition inventory changed")
    payload = {
        **evidence,
        "structural_partition_signature_id": signature_id,
        "structural_partition_source_member_ids": [member["member_id"]],
        "structural_partition_member_count": 1,
        "v48_cross_occurrence_pooling_applied": False,
        "singleton_source_retained_without_discard": True,
        "family_or_named_coordinate_input_present": False,
        "target_outcome_input_present": False,
        "empirical_source_group_promoted_to_safety_authority": False,
    }
    return {
        **payload,
        "singleton_source_group_id": hashlib.sha256(
            _SINGLETON_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def partition_canonical_source_evidence_v50(
    members: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if type(members) not in (tuple, list) or len(members) < 2:
        _fail("V50 requires at least two source members")
    if any(type(member) is not dict for member in members):
        _fail("V50 source member type changed")
    ordered = sorted(members, key=lambda member: member.get("member_id", ""))
    member_ids = [member.get("member_id") for member in ordered]
    if (
        any(type(value) is not str or len(value) != 64 for value in member_ids)
        or len(set(member_ids)) != len(member_ids)
    ):
        _fail("V50 source member identity changed")

    grouped: dict[str, list[Mapping[str, Any]]] = {}
    descriptors: dict[str, dict[str, Any]] = {}
    for member in ordered:
        descriptor = _descriptor(member)
        signature_id = hashlib.sha256(canonical_json_bytes(descriptor)).hexdigest()
        grouped.setdefault(signature_id, []).append(member)
        descriptors.setdefault(signature_id, descriptor)

    groups = []
    for signature_id in sorted(grouped):
        rows = grouped[signature_id]
        pooled = (
            pool_canonical_source_evidence_v48(rows)
            if len(rows) > 1
            else _singleton(rows[0], signature_id)
        )
        groups.append(
            {
                "structural_signature_id": signature_id,
                "compatibility_descriptor": descriptors[signature_id],
                "source_member_ids": [row["member_id"] for row in rows],
                "source_member_count": len(rows),
                "source_evidence": pooled,
                "v48_cross_occurrence_pooling_applied": len(rows) > 1,
                "singleton_source_group": len(rows) == 1,
            }
        )
    payload = {
        "schema": "acfqp.generic_structural_source_partition.v50",
        "source_member_ids": member_ids,
        "source_member_count": len(member_ids),
        "structural_groups": groups,
        "structural_group_count": len(groups),
        "singleton_group_count": sum(len(rows) == 1 for rows in grouped.values()),
        "multi_member_group_count": sum(len(rows) > 1 for rows in grouped.values()),
        "every_source_member_retained_exactly_once": sorted(
            member_id
            for group in groups
            for member_id in group["source_member_ids"]
        )
        == member_ids,
        "partition_key_derived_only_from_discovered_layout": True,
        "family_or_named_coordinate_used_for_partition": False,
        "terminal_or_target_outcome_used_for_partition": False,
        "incompatible_sources_forced_into_one_model": False,
        "empirical_partition_promoted_to_safety_authority": False,
    }
    return {
        **payload,
        "structural_source_partition_id": hashlib.sha256(
            _PARTITION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "GenericStructuralSourcePartitionV50Error",
    "partition_canonical_source_evidence_v50",
)
