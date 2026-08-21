"""Per-action receipt accepting either a fresh V106 or revalidated V109 order."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v109 as domains
from acfqp.generic_abstract_execution_receipt_v103 import (
    verify_abstract_execution_receipt_v103,
)
from acfqp.phase3e_ids import canonical_json_bytes


_V106_PLAN_DOMAIN = b"acfqp:generic-legality-conditioned-quotient-plan:v106\x00"


class GenericDependencyRevalidatedExecutionReceiptV109Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericDependencyRevalidatedExecutionReceiptV109Error(message)


def _plan(document: Mapping[str, Any]) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V109 plan type changed")
    payload = {
        key: value
        for key, value in document.items()
        if key != "legality_conditioned_quotient_plan_id"
    }
    schema = document.get("schema")
    if schema == "acfqp.generic_legality_conditioned_quotient_plan.v106":
        identity = hashlib.sha256(
            _V106_PLAN_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest()
    elif schema == "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109":
        identity = domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_PLAN_V109_DOMAIN,
            payload,
        )
        if (
            document.get("cached_ordering_used_as_safety_authority") is not False
            or document.get("ground_transition_accessed_during_dependency_revalidation")
            is not False
        ):
            _fail("V109 revalidated plan authority boundary changed")
    else:
        _fail("V109 plan schema changed")
    if (
        document.get("legality_conditioned_quotient_plan_id") != identity
        or document.get(
            "ground_legality_used_only_after_existing_support_or_failed_certificate"
        )
        is not True
        or document.get("query_local_exact_overlay_remains_only_safety_authority")
        is not True
    ):
        _fail("V109 plan identity or safety boundary changed")
    return dict(document)


def build_dependency_revalidated_execution_receipt_v109(
    *,
    episode_index: int,
    base_execution_receipt: Mapping[str, Any],
    quotient_plan_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if type(episode_index) is not int or type(base_execution_receipt) is not dict:
        _fail("V109 execution receipt inventory changed")
    base = verify_abstract_execution_receipt_v103(dict(base_execution_receipt))
    plan = None
    if quotient_plan_receipt is not None:
        if (
            type(quotient_plan_receipt) is not dict
            or quotient_plan_receipt.get("raw_state") != base["raw_state"]
        ):
            _fail("V109 plan/execution state join changed")
        plan = _plan(quotient_plan_receipt.get("abstract_plan"))
        if (
            plan["exact_legal_action_keys_at_initial_state"]
            != base["legal_action_keys"]
            or plan["agreement_shield_receipt"] != base["shield_receipt"]
        ):
            _fail("V109 plan/execution legality join changed")
    proposed = None if plan is None else plan["initial_action_key"]
    admitted = proposed in base["legal_action_keys"] if proposed is not None else False
    chosen = base["chosen_action_key"]
    match = admitted and chosen == proposed
    source = (
        "ACTUAL_DEPENDENCY_REVALIDATED_QUOTIENT_ORDER"
        if match
        else "EXACT_CERTIFICATE_FALLBACK_AFTER_DEPENDENCY_REVALIDATED_ORDER"
        if admitted
        else "EXACT_CERTIFICATE_ONLY_NO_QUOTIENT_ORDER"
    )
    payload = {
        "schema": "acfqp.generic_dependency_revalidated_execution_receipt.v109",
        "episode_index": episode_index,
        "decision_index": base["decision_index"],
        "raw_state": base["raw_state"],
        "chosen_action_key": chosen,
        "legal_action_keys": base["legal_action_keys"],
        "base_execution_receipt": base,
        "base_execution_receipt_id": base["execution_receipt_id"],
        "quotient_plan_receipt": quotient_plan_receipt,
        "quotient_graph_id": None if plan is None else plan["quotient_graph_id"],
        "quotient_plan_id": None
        if plan is None
        else plan["legality_conditioned_quotient_plan_id"],
        "quotient_proposed_action_key": proposed,
        "quotient_proposal_admitted_to_real_action_order": admitted,
        "chosen_action_matches_admitted_quotient_proposal": match,
        "actual_action_ordering_source": source,
        "legality_support_source": None
        if plan is None
        else plan["legality_support_source"],
        "legality_failure_index": None
        if plan is None
        else plan["legality_failure_index"],
        "exact_certificate_may_override_fallible_quotient_order": True,
        "receipt_is_observation_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "actual_dependency_revalidated_execution_receipt_id": domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_EXECUTION_RECEIPT_V109_DOMAIN,
            payload,
        ),
    }


def verify_dependency_revalidated_execution_receipt_v109(
    document: Any,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V109 execution receipt type changed")
    expected = build_dependency_revalidated_execution_receipt_v109(
        episode_index=document.get("episode_index"),
        base_execution_receipt=document.get("base_execution_receipt"),
        quotient_plan_receipt=document.get("quotient_plan_receipt"),
    )
    if document != expected:
        _fail("V109 execution receipt semantics changed")
    return expected


__all__ = (
    "build_dependency_revalidated_execution_receipt_v109",
    "verify_dependency_revalidated_execution_receipt_v109",
)
