"""A symmetric negative-transfer shield for fallible abstract proposals."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


class GenericAbstractPartialAgreementShieldV99Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericAbstractPartialAgreementShieldV99Error(message)


def shield_abstract_action_order_v99(
    *,
    abstract_proposal: tuple[int, ...],
    partial_proposal: tuple[int, ...],
    legal_action_keys: tuple[int, ...],
) -> dict[str, Any]:
    if (
        type(abstract_proposal) is not tuple
        or type(partial_proposal) is not tuple
        or type(legal_action_keys) is not tuple
        or not legal_action_keys
        or len(set(legal_action_keys)) != len(legal_action_keys)
        or any(type(key) is not int for key in legal_action_keys)
        or any(type(key) is not int for key in abstract_proposal)
        or any(type(key) is not int for key in partial_proposal)
    ):
        _fail("V99 agreement-shield inventory changed")
    abstract = next(
        (key for key in abstract_proposal if key in legal_action_keys), None
    )
    partial = next(
        (key for key in partial_proposal if key in legal_action_keys), None
    )
    agreed = abstract is not None and partial is not None and abstract == partial
    ordered = []
    if agreed:
        ordered.append(abstract)
    if partial is not None and partial not in ordered:
        ordered.append(partial)
    for key in legal_action_keys:
        if key not in ordered:
            ordered.append(key)
    payload = {
        "schema": "acfqp.abstract_partial_agreement_shield.v99",
        "abstract_proposal": list(abstract_proposal),
        "partial_proposal": list(partial_proposal),
        "legal_action_keys": list(legal_action_keys),
        "abstract_legal_proposal": abstract,
        "partial_legal_proposal": partial,
        "abstract_partial_agreement": agreed,
        "abstract_proposal_admitted_to_action_order": agreed,
        "abstract_disagreement_abstained": abstract is not None and not agreed,
        "shielded_action_order": ordered,
        "abstract_proposal_can_precede_partial_without_agreement": False,
        "same_shield_applied_to_prior_and_no_prior_arms": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "shield_receipt_id": hashlib.sha256(
            b"acfqp:abstract-partial-agreement-shield:v99\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def replay_abstract_action_order_shield_v99(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if type(receipt) is not dict:
        _fail("V99 agreement-shield receipt type changed")
    expected = shield_abstract_action_order_v99(
        abstract_proposal=tuple(receipt.get("abstract_proposal", ())),
        partial_proposal=tuple(receipt.get("partial_proposal", ())),
        legal_action_keys=tuple(receipt.get("legal_action_keys", ())),
    )
    if receipt != expected:
        _fail("V99 agreement-shield receipt did not replay")
    return expected


__all__ = (
    "replay_abstract_action_order_shield_v99",
    "shield_abstract_action_order_v99",
)
