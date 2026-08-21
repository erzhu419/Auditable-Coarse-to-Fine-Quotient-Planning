"""Content-addressed per-execution abstract-ordering receipts for V103."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN = b"acfqp:generic-abstract-execution-receipt:v103\x00"


class GenericAbstractExecutionReceiptV103Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericAbstractExecutionReceiptV103Error(message)


def build_abstract_execution_receipt_v103(
    *,
    decision_index: int,
    raw_state: tuple[int, ...],
    chosen_action_key: int,
    abstract_proposal: tuple[int, ...],
    partial_proposal: tuple[int, ...],
    legal_action_keys: tuple[int, ...],
    shield_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(decision_index) is not int
        or decision_index < 0
        or type(raw_state) is not tuple
        or any(type(value) is not int for value in raw_state)
        or type(chosen_action_key) is not int
        or type(abstract_proposal) is not tuple
        or type(partial_proposal) is not tuple
        or type(legal_action_keys) is not tuple
        or chosen_action_key not in legal_action_keys
        or type(shield_receipt) is not dict
    ):
        _fail("V103 execution receipt inventory changed")
    abstract_key = next(
        (key for key in abstract_proposal if key in legal_action_keys), None
    )
    partial_key = next(
        (key for key in partial_proposal if key in legal_action_keys), None
    )
    agreement = (
        abstract_key is not None
        and partial_key is not None
        and abstract_key == partial_key
    )
    if (
        shield_receipt.get("abstract_proposal") != list(abstract_proposal)
        or shield_receipt.get("partial_proposal") != list(partial_proposal)
        or shield_receipt.get("legal_action_keys") != list(legal_action_keys)
        or shield_receipt.get("abstract_partial_agreement") is not agreement
        or shield_receipt.get("abstract_proposal_admitted_to_action_order")
        is not agreement
        or shield_receipt.get("query_local_exact_overlay_remains_only_safety_authority")
        is not True
    ):
        _fail("V103 shield receipt join changed")
    payload = {
        "schema": "acfqp.generic_abstract_execution_receipt.v103",
        "decision_index": decision_index,
        "raw_state": list(raw_state),
        "chosen_action_key": chosen_action_key,
        "abstract_proposal": list(abstract_proposal),
        "partial_proposal": list(partial_proposal),
        "legal_action_keys": list(legal_action_keys),
        "shield_receipt": dict(shield_receipt),
        "abstract_partial_exact_action_agreement": agreement,
        "chosen_action_matches_admitted_abstract_proposal": (
            agreement and chosen_action_key == abstract_key
        ),
        "receipt_is_observation_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "execution_receipt_id": hashlib.sha256(
            _DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def verify_abstract_execution_receipt_v103(
    document: Any,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V103 execution receipt type changed")
    expected = build_abstract_execution_receipt_v103(
        decision_index=document.get("decision_index"),
        raw_state=tuple(document.get("raw_state", [])),
        chosen_action_key=document.get("chosen_action_key"),
        abstract_proposal=tuple(document.get("abstract_proposal", [])),
        partial_proposal=tuple(document.get("partial_proposal", [])),
        legal_action_keys=tuple(document.get("legal_action_keys", [])),
        shield_receipt=document.get("shield_receipt"),
    )
    if document != expected:
        _fail("V103 execution receipt bytes or semantics changed")
    return expected


__all__ = (
    "build_abstract_execution_receipt_v103",
    "verify_abstract_execution_receipt_v103",
)
