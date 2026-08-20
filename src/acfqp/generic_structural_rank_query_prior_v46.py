"""Cross-occurrence query ordering from anonymous action-rank relations.

The source artifact records how the first queried action ranks within the
source legal catalogue after both state and action coordinates have been put in
their discovered canonical order.  A target occurrence translates that rank
rule into one target-local V44 priority row using only its initial observation,
legal action descriptors, and partial candidate.  No target transition outcome
is inspected and the translated priority remains ordering-only.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_portable_certificate_query_priority_v44 import (
    verify_portable_certificate_query_priority_v44,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericStructuralRankQueryPriorV46Error(ValueError):
    pass


_PRIOR_DOMAIN = b"acfqp:generic-structural-rank-query-prior:v46\x00"
_TRANSLATION_DOMAIN = b"acfqp:generic-structural-rank-query-translation:v46\x00"
_V44_PRIORITY_DOMAIN = b"acfqp:generic-portable-certificate-query-priority:v44\x00"


def _fail(message: str) -> NoReturn:
    raise GenericStructuralRankQueryPriorV46Error(message)


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _canonical_fields(
    action: FlatRawActionV4, action_order: list[int]
) -> tuple[int, ...]:
    return tuple(action.fields[index] for index in action_order)


def _rank_vector(
    action: FlatRawActionV4,
    legal: tuple[FlatRawActionV4, ...],
    action_order: list[int],
) -> tuple[int, ...]:
    selected = _canonical_fields(action, action_order)
    canonical_legal = tuple(_canonical_fields(row, action_order) for row in legal)
    return tuple(
        sorted({row[index] for row in canonical_legal}).index(value)
        for index, value in enumerate(selected)
    )


def _state_signature(raw: tuple[int, ...], state_order: list[int]) -> dict[str, Any]:
    state = tuple(raw[index] for index in state_order)
    equality = [
        [right for right in range(left) if state[left] == state[right]]
        for left in range(len(state))
    ]
    return {
        "zero_mask": [index for index, value in enumerate(state) if value == 0],
        "equality_predecessors": equality,
    }


def compile_structural_rank_query_prior_v46(
    source_episode: Mapping[str, Any],
    source_layout: Mapping[str, Any],
    source_catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    if (
        type(source_episode) is not dict
        or source_episode.get("success") is not True
        or type(source_layout) is not dict
        or type(source_catalogue) is not tuple
        or not source_catalogue
        or any(type(row) is not FlatRawActionV4 for row in source_catalogue)
    ):
        _fail("V46 source inventory changed")
    state_order = source_layout.get("state_canonical_to_raw")
    action_order = source_layout.get("action_canonical_to_raw")
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V46 source layout changed")
    by_key = {row.key: row for row in source_catalogue}
    rules = []
    for distinction in source_episode.get("local_distinctions", ()):
        if distinction.get("distinction_kind") != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            continue
        raw = distinction.get("raw_state")
        rows = distinction.get("raw_transition_rows")
        if type(raw) is not list or type(rows) is not list or not rows:
            _fail("V46 source distinction changed")
        first = rows[0]
        selected = first.get("selected_action")
        legal_keys = first.get("legal_action_keys_before")
        key = selected.get("action_key") if type(selected) is dict else None
        if (
            type(key) is not int
            or type(legal_keys) is not list
            or key not in by_key
            or any(legal_key not in by_key for legal_key in legal_keys)
        ):
            _fail("V46 source legal-action evidence changed")
        legal = tuple(by_key[legal_key] for legal_key in legal_keys)
        rule = {
            "source_query_index": len(rules),
            "source_state_signature": _state_signature(tuple(raw), state_order),
            "selected_action_rank_vector": list(
                _rank_vector(by_key[key], legal, action_order)
            ),
            "source_legal_action_count": len(legal),
        }
        if rule not in rules:
            rules.append(rule)
    if not rules:
        _fail("V46 source episode contains no query-order rule")
    payload = {
        "schema": "acfqp.generic_structural_rank_query_prior.v46",
        "source_episode_id": source_episode.get("episode_id"),
        "source_joint_successor_version_space_model_id": source_episode.get(
            "joint_successor_version_space_model_id"
        ),
        "state_width": len(state_order),
        "action_field_width": len(action_order),
        "source_rules": rules,
        "fallback_selected_action_rank_vector": rules[0][
            "selected_action_rank_vector"
        ],
        "source_query_order_only": True,
        "target_transition_outcomes_used": False,
        "ground_transition_authority_present": False,
        "safety_authority_present": False,
    }
    return {
        **payload,
        "structural_rank_query_prior_id": _content_id(_PRIOR_DOMAIN, payload),
    }


def verify_structural_rank_query_prior_v46(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("V46 prior type changed")
    payload = {
        key: item for key, item in value.items() if key != "structural_rank_query_prior_id"
    }
    rules = value.get("source_rules")
    if (
        value.get("schema") != "acfqp.generic_structural_rank_query_prior.v46"
        or _content_id(_PRIOR_DOMAIN, payload)
        != value.get("structural_rank_query_prior_id")
        or type(rules) is not list
        or not rules
        or value.get("fallback_selected_action_rank_vector")
        != rules[0].get("selected_action_rank_vector")
        or value.get("source_query_order_only") is not True
        or value.get("target_transition_outcomes_used") is not False
        or value.get("ground_transition_authority_present") is not False
        or value.get("safety_authority_present") is not False
    ):
        _fail("V46 prior identity or claim boundary changed")
    return copy.deepcopy(value)


def translate_structural_rank_prior_to_initial_v44_priority_v46(
    prior: Mapping[str, Any],
    target_candidate: PartialFactorCandidateV15,
    target_adapter: Any,
) -> dict[str, Any]:
    verified = verify_structural_rank_query_prior_v46(prior)
    if type(target_candidate) is not PartialFactorCandidateV15:
        _fail("V46 target candidate changed")
    document = target_candidate.public_document
    layout = document.get("layout")
    state_order = layout.get("state_canonical_to_raw") if type(layout) is dict else None
    action_order = layout.get("action_canonical_to_raw") if type(layout) is dict else None
    if (
        type(state_order) is not list
        or type(action_order) is not list
        or document.get("state_width") != verified["state_width"]
        or document.get("action_field_width") != verified["action_field_width"]
    ):
        _fail("V46 target width is incompatible with the structural rank prior")
    state = target_adapter.initial()
    raw = target_adapter.encode(state)
    legal = tuple(target_adapter.actions(state))
    if type(raw) is not tuple or not legal or any(type(row) is not FlatRawActionV4 for row in legal):
        _fail("V46 target initial inventory changed")
    wanted = tuple(verified["fallback_selected_action_rank_vector"])
    ranked = [
        (
            sum(abs(left - right) for left, right in zip(_rank_vector(row, legal, action_order), wanted, strict=True)),
            _canonical_fields(row, action_order),
            row.key,
            row,
        )
        for row in legal
    ]
    ranked.sort(key=lambda item: item[:3])
    selected = ranked[0][3]
    canonical_state = tuple(raw[index] for index in state_order)
    canonical_action = _canonical_fields(selected, action_order)
    priority_payload = {
        "schema": "acfqp.generic_portable_certificate_query_priority.v44",
        "source_episode_id": verified["source_episode_id"],
        "source_joint_successor_version_space_model_id": verified[
            "source_joint_successor_version_space_model_id"
        ],
        "source_partial_candidate_id": document["candidate_id"],
        "state_width": document["state_width"],
        "action_field_width": document["action_field_width"],
        "state_structural_colors": copy.deepcopy(layout["state_structural_colors"]),
        "action_structural_colors": copy.deepcopy(layout["action_structural_colors"]),
        "compiled_factor_assignments": copy.deepcopy(
            document["compiled_factor_assignments"]
        ),
        "priority_rows": [
            {
                "canonical_state": list(canonical_state),
                "canonical_action_fields": list(canonical_action),
            }
        ],
        "priority_state_count": 1,
        "source_transition_query_count": len(verified["source_rules"]),
        "first_source_transition_query_per_canonical_state_retained": True,
        "raw_action_key_reused_across_occurrences": False,
        "canonical_anonymous_action_descriptor_used": True,
        "target_outcomes_used_to_fit_priority": False,
        "priority_used_only_for_query_ordering": True,
        "ground_transition_authority_present": False,
        "safety_authority_present": False,
    }
    priority = {
        **priority_payload,
        "portable_query_priority_id": _content_id(
            _V44_PRIORITY_DOMAIN, priority_payload
        ),
    }
    verify_portable_certificate_query_priority_v44(priority)
    receipt_payload = {
        "schema": "acfqp.generic_structural_rank_query_translation.v46",
        "structural_rank_query_prior_id": verified[
            "structural_rank_query_prior_id"
        ],
        "target_partial_candidate_id": document["candidate_id"],
        "target_seed": target_adapter.seed,
        "target_initial_state_signature": _state_signature(raw, state_order),
        "wanted_rank_vector": list(wanted),
        "selected_target_action_rank_vector": list(
            _rank_vector(selected, legal, action_order)
        ),
        "selected_target_action_key": selected.key,
        "selection_rule": "MIN_L1_RANK_DISTANCE_THEN_CANONICAL_FIELDS_THEN_KEY",
        "target_transition_outcomes_used": False,
        "translated_priority_id": priority["portable_query_priority_id"],
        "ordering_only": True,
        "safety_authority_present": False,
    }
    receipt = {
        **receipt_payload,
        "translation_id": _content_id(_TRANSLATION_DOMAIN, receipt_payload),
    }
    return {"portable_priority": priority, "translation_receipt": receipt}


__all__ = (
    "compile_structural_rank_query_prior_v46",
    "translate_structural_rank_prior_to_initial_v44_priority_v46",
    "verify_structural_rank_query_prior_v46",
)
