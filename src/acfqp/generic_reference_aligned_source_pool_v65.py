"""Align partially observed source layouts before empirical source pooling.

V50 partitions on exact finite-observation structural colours.  In a partial or
stochastic domain, two occurrences can expose the same anonymous schema while
different observed branches refine those colours differently.  This module
replays every stored common-partial observation, chooses the lowest member ID
as an outcome-blind reference, and uses the existing generic relation matcher
to align the remaining occurrences before invoking the unchanged V48 pooler.

The reference matcher can inspect source terminal-acceptance observations.  It
never receives a target occurrence, family name, named coordinate, or target
outcome.  Its result remains empirical proposal evidence and grants no safety
authority.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_canonical_source_pool_v48 import (
    pool_canonical_source_evidence_v48,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    DiscoveredLayoutV5,
    discover_generic_layout_v5,
    match_generic_layout_meta_prior_v5,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericReferenceAlignedSourcePoolV65Error(ValueError):
    pass


_ALIGNMENT_DOMAIN = b"acfqp:generic-reference-source-alignment:v65\x00"
_EVIDENCE_DOMAIN = b"acfqp:generic-reference-aligned-source-evidence:v65\x00"
_POOL_DOMAIN = b"acfqp:generic-reference-aligned-source-pool:v65\x00"


def _fail(message: str) -> NoReturn:
    raise GenericReferenceAlignedSourcePoolV65Error(message)


def _actions(value: Any) -> tuple[FlatRawActionV4, ...]:
    if type(value) is not list or not value:
        _fail("V65 anonymous action catalogue changed")
    result = []
    for document in value:
        if type(document) is not dict or set(document) != {
            "action_key",
            "anonymous_fields",
        }:
            _fail("V65 anonymous action document changed")
        try:
            action = FlatRawActionV4(
                document["action_key"], tuple(document["anonymous_fields"])
            )
        except (TypeError, ValueError) as error:
            _fail(f"V65 anonymous action rejected: {error}")
        if action.to_document() != document:
            _fail("V65 anonymous action reconstruction diverged")
        result.append(action)
    keys = [row.key for row in result]
    if len(set(keys)) != len(keys):
        _fail("V65 anonymous action keys changed")
    return tuple(result)


def _rows(
    value: Any, catalogue: tuple[FlatRawActionV4, ...]
) -> tuple[FlatRawTransitionV4, ...]:
    if type(value) is not list or not value:
        _fail("V65 common-partial transition inventory changed")
    by_key = {row.key: row for row in catalogue}
    result = []
    required = {
        "occurrence",
        "transition_index",
        "pre_vector",
        "legal_action_keys_before",
        "selected_action",
        "post_vector",
        "legal_action_keys_after",
        "terminal_acceptance_after",
        "outcome_tape_sha256",
    }
    for document in value:
        selected = document.get("selected_action") if type(document) is dict else None
        key = selected.get("action_key") if type(selected) is dict else None
        if (
            type(document) is not dict
            or set(document) != required
            or type(key) is not int
            or key not in by_key
            or selected != by_key[key].to_document()
        ):
            _fail("V65 common-partial transition document changed")
        try:
            row = FlatRawTransitionV4(
                document["occurrence"],
                document["transition_index"],
                tuple(document["pre_vector"]),
                tuple(document["legal_action_keys_before"]),
                by_key[key],
                tuple(document["post_vector"]),
                tuple(document["legal_action_keys_after"]),
                document["terminal_acceptance_after"],
                document["outcome_tape_sha256"],
            )
        except (TypeError, ValueError) as error:
            _fail(f"V65 common-partial transition rejected: {error}")
        if row.to_document() != document:
            _fail("V65 common-partial transition reconstruction diverged")
        result.append(row)
    if [row.index for row in result] != list(range(len(result))):
        _fail("V65 common-partial transition order changed")
    return tuple(result)


def _layout(value: Any) -> DiscoveredLayoutV5:
    if type(value) is not dict:
        _fail("V65 discovered layout changed")
    try:
        result = DiscoveredLayoutV5(
            tuple(value["state_canonical_to_raw"]),
            tuple(value["action_canonical_to_raw"]),
            tuple(value["state_structural_colors"]),
            tuple(value["action_structural_colors"]),
            value["schema_signature"],
            value["refinement_rounds"],
            value["relation_evaluations"],
            value["layout_id"],
            value["reference_layout_id"],
            value["graph_edit_score"],
            value["cross_occurrence_value_overlap"],
        )
    except (KeyError, TypeError) as error:
        _fail(f"V65 discovered layout rejected: {error}")
    if result.to_document() != value:
        _fail("V65 discovered layout reconstruction diverged")
    return result


def _prepared_member(
    member: Mapping[str, Any], layout_domain: str
) -> tuple[dict[str, Any], tuple[FlatRawTransitionV4, ...], tuple[FlatRawActionV4, ...], DiscoveredLayoutV5]:
    if type(member) is not dict:
        _fail("V65 source member type changed")
    evidence = member.get("source_evidence")
    if type(evidence) is not dict:
        _fail("V65 source evidence changed")
    acquisition = member.get("common_partial_acquisition")
    candidate = acquisition.get("candidate") if type(acquisition) is dict else None
    if type(candidate) is not dict:
        _fail("V65 partial-candidate issuance evidence changed")
    actions = _actions(member.get("action_catalogue"))
    rows = _rows(evidence.get("common_partial_raw_transition_rows"), actions)
    layout = _layout(evidence.get("layout"))
    issuance_count = candidate.get("raw_transition_count_at_issuance")
    issuance_sha = candidate.get("raw_transition_sha256")
    if (
        type(issuance_count) is not int
        or not 0 < issuance_count <= len(rows)
        or type(issuance_sha) is not str
        or hashlib.sha256(
            canonical_json_bytes(
                [row.to_document() for row in rows[:issuance_count]]
            )
        ).hexdigest()
        != issuance_sha
        or candidate.get("layout") != evidence.get("layout")
        or candidate.get("unknown_residual_target_columns")
        != evidence.get("unknown_residual_target_columns")
    ):
        _fail("V65 partial-candidate issuance join changed")
    replay = discover_generic_layout_v5(
        rows[:issuance_count], actions, layout_domain=layout_domain
    )
    if replay.to_document() != layout.to_document():
        _fail("V65 stored layout does not replay from common-partial observations")
    unknown = evidence.get("unknown_residual_target_columns")
    if (
        type(unknown) is not list
        or unknown != sorted(set(unknown))
        or any(type(row) is not int or not 0 <= row < len(layout.state_canonical_to_raw) for row in unknown)
    ):
        _fail("V65 residual coordinate inventory changed")
    return copy.deepcopy(member), rows, actions, layout


def _aligned_evidence(
    member: Mapping[str, Any],
    original_layout: DiscoveredLayoutV5,
    aligned_layout: DiscoveredLayoutV5,
    reference_member_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence = copy.deepcopy(member["source_evidence"])
    original_sha = hashlib.sha256(canonical_json_bytes(evidence)).hexdigest()
    original_id = evidence.get("source_evidence_id")
    raw_unknown = {
        original_layout.state_canonical_to_raw[index]
        for index in evidence["unknown_residual_target_columns"]
    }
    aligned_unknown = [
        index
        for index, raw in enumerate(aligned_layout.state_canonical_to_raw)
        if raw in raw_unknown
    ]
    alignment_payload = {
        "schema": "acfqp.generic_reference_source_alignment.v65",
        "source_member_id": member["member_id"],
        "reference_member_id": reference_member_id,
        "original_source_evidence_id": original_id,
        "original_source_evidence_sha256": original_sha,
        "original_layout_id": original_layout.layout_id,
        "aligned_layout_id": aligned_layout.layout_id,
        "aligned_state_canonical_to_raw": list(
            aligned_layout.state_canonical_to_raw
        ),
        "aligned_action_canonical_to_raw": list(
            aligned_layout.action_canonical_to_raw
        ),
        "aligned_unknown_residual_target_columns": aligned_unknown,
        "graph_edit_score": aligned_layout.graph_edit_score,
        "cross_occurrence_value_overlap": (
            aligned_layout.cross_occurrence_value_overlap
        ),
        "alignment_derived_from_common_partial_source_observations": True,
        "source_terminal_acceptance_observations_available_to_matcher": True,
        "family_or_named_coordinate_input_present": False,
        "target_occurrence_or_target_outcome_input_present": False,
        "alignment_promoted_to_safety_authority": False,
    }
    receipt = {
        **alignment_payload,
        "source_alignment_id": hashlib.sha256(
            _ALIGNMENT_DOMAIN + canonical_json_bytes(alignment_payload)
        ).hexdigest(),
    }
    evidence.pop("source_evidence_id", None)
    evidence["layout"] = aligned_layout.to_document()
    evidence["unknown_residual_target_columns"] = aligned_unknown
    evidence["reference_source_alignment"] = receipt
    evidence_payload = {
        **evidence,
        "original_source_evidence_id": original_id,
        "original_source_evidence_sha256": original_sha,
        "empirical_alignment_only": True,
    }
    aligned = {
        **evidence_payload,
        "source_evidence_id": hashlib.sha256(
            _EVIDENCE_DOMAIN + canonical_json_bytes(evidence_payload)
        ).hexdigest(),
    }
    return aligned, receipt


def pool_reference_aligned_source_evidence_v65(
    members: Sequence[Mapping[str, Any]], *, layout_domain: str
) -> dict[str, Any]:
    """Replay, align, and pool one anonymous structural-schema source group."""
    if type(members) not in (tuple, list) or len(members) < 2:
        _fail("V65 requires at least two source members")
    ordered = sorted(members, key=lambda row: row.get("member_id", ""))
    member_ids = [row.get("member_id") for row in ordered]
    if (
        any(type(row) is not str or len(row) != 64 for row in member_ids)
        or len(set(member_ids)) != len(member_ids)
        or type(layout_domain) is not str
        or not layout_domain
    ):
        _fail("V65 source member identity or layout domain changed")
    prepared = [_prepared_member(row, layout_domain) for row in ordered]
    reference_member, reference_rows, reference_actions, reference_layout = prepared[0]
    aligned_members = []
    receipts = []
    for index, (member, rows, actions, layout) in enumerate(prepared):
        aligned_layout = (
            reference_layout
            if index == 0
            else match_generic_layout_meta_prior_v5(
                reference_rows,
                reference_actions,
                reference_layout,
                rows,
                actions,
                layout_domain=layout_domain,
            )
        )
        evidence, receipt = _aligned_evidence(
            member, layout, aligned_layout, reference_member["member_id"]
        )
        aligned_members.append(
            {
                "member_id": member["member_id"],
                "source_evidence": evidence,
                "action_catalogue": member["action_catalogue"],
            }
        )
        receipts.append(receipt)
    reference_unknown = aligned_members[0]["source_evidence"][
        "unknown_residual_target_columns"
    ]
    if any(
        row["source_evidence"]["unknown_residual_target_columns"]
        != reference_unknown
        for row in aligned_members
    ):
        _fail("V65 aligned residual coordinate inventories remain incompatible")
    pooled = pool_canonical_source_evidence_v48(aligned_members)
    payload = {
        "schema": "acfqp.generic_reference_aligned_source_pool.v65",
        "source_member_ids": member_ids,
        "source_member_count": len(member_ids),
        "reference_member_id": reference_member["member_id"],
        "source_alignment_receipts": receipts,
        "aligned_unknown_residual_target_columns": reference_unknown,
        "canonical_source_pool": pooled,
        "every_original_source_evidence_replayed_before_alignment": True,
        "every_source_member_retained_exactly_once": True,
        "full_finite_observation_structural_color_equality_required": False,
        "shared_anonymous_schema_and_unique_reference_alignment_required": True,
        "source_terminal_acceptance_observations_available_to_matcher": True,
        "family_or_named_coordinate_input_present": False,
        "target_occurrence_or_target_outcome_input_present": False,
        "empirical_source_pool_promoted_to_safety_authority": False,
    }
    return {
        **payload,
        "reference_aligned_source_pool_id": hashlib.sha256(
            _POOL_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "GenericReferenceAlignedSourcePoolV65Error",
    "pool_reference_aligned_source_evidence_v65",
)
