"""Per-action receipts that distinguish full and honest partial abstraction."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_abstract_execution_receipt_v103 import (
    verify_abstract_execution_receipt_v103,
)
from acfqp.phase3e_ids import canonical_json_bytes

_DOMAIN = b"acfqp:hierarchical-abstract-execution-receipt:v104\x00"


class GenericHierarchicalAbstractExecutionReceiptV104Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericHierarchicalAbstractExecutionReceiptV104Error(message)


def build_hierarchical_abstract_execution_receipt_v104(
    *,
    episode_index: int,
    base_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if type(episode_index) is not int or type(base_receipt) is not dict:
        _fail("V104 hierarchical receipt inventory changed")
    verified = verify_abstract_execution_receipt_v103(dict(base_receipt))
    legal = verified["legal_action_keys"]
    partial_key = next(
        (key for key in verified["partial_proposal"] if key in legal), None
    )
    full_key = next(
        (key for key in verified["abstract_proposal"] if key in legal), None
    )
    chosen = verified["chosen_action_key"]
    full_match = verified["chosen_action_matches_admitted_abstract_proposal"]
    partial_match = partial_key is not None and chosen == partial_key
    if full_match:
        source = "FULL_POST_DEPENDENCY_WORLD_MODEL"
    elif partial_match:
        source = "COMPILED_PARTIAL_WORLD_MODEL_FALLBACK"
    else:
        source = "EXACT_CERTIFICATE_POLICY_ONLY"
    payload = {
        "schema": "acfqp.hierarchical_abstract_execution_receipt.v104",
        "episode_index": episode_index,
        "decision_index": verified["decision_index"],
        "base_v103_execution_receipt": verified,
        "base_v103_execution_receipt_id": verified["execution_receipt_id"],
        "chosen_action_key": chosen,
        "full_post_dependency_legal_proposal": full_key,
        "compiled_partial_legal_proposal": partial_key,
        "chosen_action_matches_full_post_dependency_proposal": full_match,
        "chosen_action_matches_compiled_partial_proposal": partial_match,
        "abstract_ordering_source": source,
        "chosen_action_matches_admitted_abstract_model_proposal": (
            full_match or partial_match
        ),
        "full_model_match_not_inferred_from_partial_fallback": True,
        "partial_world_model_explicitly_missing_residual_coordinates": True,
        "residual_completion_disagreement_retained": (
            verified["abstract_partial_exact_action_agreement"] is False
        ),
        "receipt_is_observation_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_claimed": False,
    }
    return {
        **payload,
        "hierarchical_execution_receipt_id": hashlib.sha256(
            _DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def verify_hierarchical_abstract_execution_receipt_v104(
    document: Any,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V104 hierarchical receipt type changed")
    expected = build_hierarchical_abstract_execution_receipt_v104(
        episode_index=document.get("episode_index"),
        base_receipt=document.get("base_v103_execution_receipt"),
    )
    if document != expected:
        _fail("V104 hierarchical receipt semantics changed")
    return expected


__all__ = (
    "build_hierarchical_abstract_execution_receipt_v104",
    "verify_hierarchical_abstract_execution_receipt_v104",
)
