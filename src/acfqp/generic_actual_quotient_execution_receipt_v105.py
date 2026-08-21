"""Per-action proof that a quotient proposal entered the real action order."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_abstract_execution_receipt_v103 import (
    verify_abstract_execution_receipt_v103,
)
from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN = b"acfqp:generic-actual-quotient-execution-receipt:v105\x00"
_PLAN_DOMAIN = b"acfqp:generic-observation-quotient-plan:v105\x00"


class GenericActualQuotientExecutionReceiptV105Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericActualQuotientExecutionReceiptV105Error(message)


def build_actual_quotient_execution_receipt_v105(
    *,
    episode_index: int,
    base_execution_receipt: Mapping[str, Any],
    quotient_plan_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if type(episode_index) is not int or type(base_execution_receipt) is not dict:
        _fail("V105 actual quotient receipt inventory changed")
    base = verify_abstract_execution_receipt_v103(dict(base_execution_receipt))
    plan = None
    if quotient_plan_receipt is not None:
        if (
            type(quotient_plan_receipt) is not dict
            or quotient_plan_receipt.get("raw_state") != base["raw_state"]
            or type(quotient_plan_receipt.get("abstract_plan")) is not dict
        ):
            _fail("V105 plan/execution state join changed")
        plan = quotient_plan_receipt["abstract_plan"]
        plan_payload = {
            key: value
            for key, value in plan.items()
            if key
            not in (
                "quotient_plan_id",
                "agreement_shield_receipt",
                "legacy_two_channel_shield_carries_one_identical_quotient_proposal",
            )
        }
        if (
            plan.get("schema") != "acfqp.generic_observation_quotient_plan.v105"
            or type(plan.get("quotient_plan_id")) is not str
            or len(plan["quotient_plan_id"]) != 64
            or plan["quotient_plan_id"]
            != hashlib.sha256(
                _PLAN_DOMAIN + canonical_json_bytes(plan_payload)
            ).hexdigest()
            or plan.get("query_local_exact_overlay_remains_only_safety_authority")
            is not True
            or plan.get("agreement_shield_receipt") != base["shield_receipt"]
            or plan.get(
                "legacy_two_channel_shield_carries_one_identical_quotient_proposal"
            )
            is not True
        ):
            _fail("V105 quotient plan receipt changed")
    proposed = None if plan is None else plan["initial_action_key"]
    admitted = proposed in base["legal_action_keys"] if proposed is not None else False
    chosen = base["chosen_action_key"]
    match = admitted and chosen == proposed
    source = (
        "ACTUAL_QUOTIENT_MODEL_ORDER"
        if match
        else "EXACT_CERTIFICATE_FALLBACK_AFTER_QUOTIENT_ORDER"
        if admitted
        else "EXACT_CERTIFICATE_ONLY_NO_QUOTIENT_ORDER"
    )
    payload = {
        "schema": "acfqp.generic_actual_quotient_execution_receipt.v105",
        "episode_index": episode_index,
        "decision_index": base["decision_index"],
        "raw_state": base["raw_state"],
        "chosen_action_key": chosen,
        "legal_action_keys": base["legal_action_keys"],
        "base_execution_receipt": base,
        "base_execution_receipt_id": base["execution_receipt_id"],
        "quotient_plan_receipt": quotient_plan_receipt,
        "quotient_graph_id": None if plan is None else plan["quotient_graph_id"],
        "quotient_plan_id": None if plan is None else plan["quotient_plan_id"],
        "quotient_proposed_action_key": proposed,
        "quotient_proposal_admitted_to_real_action_order": admitted,
        "chosen_action_matches_admitted_quotient_proposal": match,
        "actual_action_ordering_source": source,
        "exact_certificate_may_override_fallible_quotient_order": True,
        "receipt_is_observation_not_safety_authority": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "actual_quotient_execution_receipt_id": hashlib.sha256(
            _DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def verify_actual_quotient_execution_receipt_v105(document: Any) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V105 actual quotient receipt type changed")
    expected = build_actual_quotient_execution_receipt_v105(
        episode_index=document.get("episode_index"),
        base_execution_receipt=document.get("base_execution_receipt"),
        quotient_plan_receipt=document.get("quotient_plan_receipt"),
    )
    if document != expected:
        _fail("V105 actual quotient receipt semantics changed")
    return expected


__all__ = (
    "build_actual_quotient_execution_receipt_v105",
    "verify_actual_quotient_execution_receipt_v105",
)
