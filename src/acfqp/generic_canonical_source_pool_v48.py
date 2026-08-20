"""Canonicalize compatible source occurrences into one acquisition stream.

The pool is deliberately generic: it only uses the discovered state/action
layouts, anonymous action catalogues, and raw transition documents.  It does
not inspect a family name, a semantic coordinate name, a terminal witness, or
any target outcome.  Each source member remains present in the provenance
inventory while a deterministic projection places all rows in the first
member's raw layout and gives semantically identical anonymous actions the
same pooled key.

The resulting artifact is empirical source evidence.  It is not a dynamics
certificate and it grants no target or safety authority.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.phase3e_ids import canonical_json_bytes


class GenericCanonicalSourcePoolV48Error(ValueError):
    pass


_POOL_DOMAIN = b"acfqp:generic-canonical-source-pool:v48\x00"


def _fail(message: str) -> NoReturn:
    raise GenericCanonicalSourcePoolV48Error(message)


def _permutation(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or any(type(item) is not int for item in value)
        or sorted(value) != list(range(len(value)))
    ):
        _fail(f"V48 {label} is not a permutation")
    return value


def _canonical(values: Any, order: list[int], label: str) -> tuple[int, ...]:
    if (
        type(values) is not list
        or len(values) != len(order)
        or any(type(item) is not int for item in values)
    ):
        _fail(f"V48 {label} vector changed")
    return tuple(values[index] for index in order)


def _reference_raw(canonical: tuple[int, ...], order: list[int]) -> list[int]:
    raw = [0] * len(order)
    for canonical_index, raw_index in enumerate(order):
        raw[raw_index] = canonical[canonical_index]
    return raw


def _catalogue(
    value: Any, action_order: list[int], member_index: int
) -> tuple[dict[int, tuple[int, ...]], list[tuple[int, ...]]]:
    if type(value) is not list or not value:
        _fail("V48 source action catalogue changed")
    by_key: dict[int, tuple[int, ...]] = {}
    signatures = []
    for row in value:
        key = row.get("action_key") if type(row) is dict else None
        fields = row.get("anonymous_fields") if type(row) is dict else None
        if type(key) is not int or key in by_key:
            _fail("V48 source action key inventory changed")
        signature = _canonical(
            fields, action_order, f"member {member_index} action"
        )
        by_key[key] = signature
        signatures.append(signature)
    if len(set(signatures)) != len(signatures):
        _fail("V48 canonical action signatures are not unique")
    return by_key, signatures


def pool_canonical_source_evidence_v48(
    members: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return a content-addressed, layout-normalized source pool."""
    if type(members) not in (tuple, list) or len(members) < 2:
        _fail("V48 requires at least two source members")
    if any(type(member) is not dict for member in members):
        _fail("V48 source member type changed")
    member_ids = [member.get("member_id") for member in members]
    if (
        any(type(value) is not str or not value for value in member_ids)
        or len(set(member_ids)) != len(member_ids)
    ):
        _fail("V48 source member identities changed")

    reference = members[0].get("source_evidence")
    if type(reference) is not dict:
        _fail("V48 reference source evidence changed")
    reference_layout = reference.get("layout")
    if type(reference_layout) is not dict:
        _fail("V48 reference layout changed")
    reference_state_order = _permutation(
        reference_layout.get("state_canonical_to_raw"), "reference state layout"
    )
    reference_action_order = _permutation(
        reference_layout.get("action_canonical_to_raw"), "reference action layout"
    )
    reference_unknown = reference.get("unknown_residual_target_columns")
    if (
        type(reference_unknown) is not list
        or reference_unknown != sorted(set(reference_unknown))
        or any(
            type(value) is not int
            or not 0 <= value < len(reference_state_order)
            for value in reference_unknown
        )
    ):
        _fail("V48 reference residual inventory changed")
    reference_signature = reference_layout.get("schema_signature")
    reference_state_colors = reference_layout.get("state_structural_colors")
    reference_action_colors = reference_layout.get("action_structural_colors")

    prepared = []
    all_action_signatures: set[tuple[int, ...]] = set()
    for member_index, member in enumerate(members):
        evidence = member.get("source_evidence")
        catalogue = member.get("action_catalogue")
        if type(evidence) is not dict:
            _fail("V48 member source evidence changed")
        layout = evidence.get("layout")
        if type(layout) is not dict:
            _fail("V48 member layout changed")
        state_order = _permutation(
            layout.get("state_canonical_to_raw"), f"member {member_index} state layout"
        )
        action_order = _permutation(
            layout.get("action_canonical_to_raw"), f"member {member_index} action layout"
        )
        if (
            len(state_order) != len(reference_state_order)
            or len(action_order) != len(reference_action_order)
            or evidence.get("unknown_residual_target_columns") != reference_unknown
            or layout.get("schema_signature") != reference_signature
            or layout.get("state_structural_colors") != reference_state_colors
            or layout.get("action_structural_colors") != reference_action_colors
        ):
            _fail("V48 source members are not structurally compatible")
        by_key, signatures = _catalogue(catalogue, action_order, member_index)
        all_action_signatures.update(signatures)
        rows = evidence.get("raw_transition_rows")
        if type(rows) is not list or not rows:
            _fail("V48 member transition inventory changed")
        prepared.append((evidence, state_order, action_order, by_key, rows))

    ordered_signatures = sorted(all_action_signatures)
    pooled_key = {
        signature: index for index, signature in enumerate(ordered_signatures)
    }
    pooled_rows = []
    receipts = []
    for member_index, (member, prepared_row) in enumerate(
        zip(members, prepared, strict=True)
    ):
        evidence, state_order, action_order, by_key, rows = prepared_row
        transformed = []
        for source_row_offset, row in enumerate(rows):
            selected = row.get("selected_action") if type(row) is dict else None
            raw_key = selected.get("action_key") if type(selected) is dict else None
            raw_fields = (
                selected.get("anonymous_fields") if type(selected) is dict else None
            )
            legal_before = row.get("legal_action_keys_before") if type(row) is dict else None
            legal_after = row.get("legal_action_keys_after") if type(row) is dict else None
            if (
                type(raw_key) is not int
                or raw_key not in by_key
                or _canonical(
                    raw_fields, action_order, f"member {member_index} selected action"
                )
                != by_key[raw_key]
                or type(legal_before) is not list
                or type(legal_after) is not list
                or any(type(key) is not int or key not in by_key for key in (*legal_before, *legal_after))
            ):
                _fail("V48 transition/action catalogue join changed")
            canonical_action = by_key[raw_key]
            projected = copy.deepcopy(row)
            projected["occurrence"] = member_index
            projected["transition_index"] = source_row_offset
            projected["pre_vector"] = _reference_raw(
                _canonical(row.get("pre_vector"), state_order, "pre-state"),
                reference_state_order,
            )
            projected["post_vector"] = _reference_raw(
                _canonical(row.get("post_vector"), state_order, "post-state"),
                reference_state_order,
            )
            projected["legal_action_keys_before"] = sorted(
                {pooled_key[by_key[key]] for key in legal_before}
            )
            projected["selected_action"] = {
                "action_key": pooled_key[canonical_action],
                "anonymous_fields": _reference_raw(
                    canonical_action, reference_action_order
                ),
            }
            projected["legal_action_keys_after"] = sorted(
                {pooled_key[by_key[key]] for key in legal_after}
            )
            projected["canonical_source_pool_member_index"] = member_index
            projected["canonical_source_pool_source_row_offset"] = source_row_offset
            transformed.append(projected)
        pooled_rows.extend(transformed)
        receipts.append(
            {
                "member_index": member_index,
                "member_id": member["member_id"],
                "source_evidence_id": evidence.get("source_evidence_id"),
                "source_evidence_sha256": hashlib.sha256(
                    canonical_json_bytes(evidence)
                ).hexdigest(),
                "source_row_count": len(rows),
                "projected_row_count": len(transformed),
                "state_canonical_to_raw": list(state_order),
                "action_canonical_to_raw": list(action_order),
            }
        )

    payload = {
        "schema": "acfqp.generic_canonical_source_pool.v48",
        "layout": copy.deepcopy(reference_layout),
        "unknown_residual_target_columns": list(reference_unknown),
        "raw_transition_rows": pooled_rows,
        "source_member_receipts": receipts,
        "source_member_count": len(receipts),
        "pooled_raw_transition_row_count": len(pooled_rows),
        "canonical_action_signatures": [list(row) for row in ordered_signatures],
        "canonical_action_signature_count": len(ordered_signatures),
        "reference_member_id": members[0]["member_id"],
        "all_members_retained_in_provenance": True,
        "state_and_action_layouts_only_used_for_projection": True,
        "family_or_named_coordinate_input_present": False,
        "target_outcome_input_present": False,
        "terminal_witness_used_for_pool_order": False,
        "empirical_source_pool_promoted_to_safety_authority": False,
    }
    return {
        **payload,
        "canonical_source_pool_id": hashlib.sha256(
            _POOL_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "GenericCanonicalSourcePoolV48Error",
    "pool_canonical_source_evidence_v48",
)
