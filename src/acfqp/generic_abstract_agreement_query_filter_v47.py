"""Abstract-agreement filter for target-local query priorities.

The filter asks the already frozen abstract model for its target initial action
without consulting target transition outcomes.  A translated source priority is
enabled only when it selects the same action.  Otherwise an inert, schema-valid
priority is supplied to the exact V44 engine so the matched model-only arm uses
the identical implementation and stopping rule.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
    plan_joint_successor_version_space_v42,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_portable_certificate_query_priority_v44 import (
    verify_portable_certificate_query_priority_v44,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericAbstractAgreementQueryFilterV47Error(ValueError):
    pass


_FILTER_DOMAIN = b"acfqp:generic-abstract-agreement-query-filter:v47\x00"
_V44_PRIORITY_DOMAIN = b"acfqp:generic-portable-certificate-query-priority:v44\x00"
_INERT_SENTINEL = 9_223_372_036_854_775_807


def _fail(message: str) -> NoReturn:
    raise GenericAbstractAgreementQueryFilterV47Error(message)


def _priority_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        _V44_PRIORITY_DOMAIN + canonical_json_bytes(payload)
    ).hexdigest()


def _inert_priority(priority: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        key: copy.deepcopy(value)
        for key, value in priority.items()
        if key != "portable_query_priority_id"
    }
    payload["priority_rows"] = [
        {
            "canonical_state": [_INERT_SENTINEL] * payload["state_width"],
            "canonical_action_fields": copy.deepcopy(
                priority["priority_rows"][0]["canonical_action_fields"]
            ),
        }
    ]
    payload["priority_state_count"] = 1
    result = {**payload, "portable_query_priority_id": _priority_id(payload)}
    return verify_portable_certificate_query_priority_v44(result)


def apply_abstract_agreement_query_filter_v47(
    model: Mapping[str, Any],
    target_candidate: PartialFactorCandidateV15,
    target_adapter: Any,
    translated: Mapping[str, Any],
    *,
    maximum_abstract_depth: int,
    maximum_support_branch_evaluations: int,
    support_feasible_beam_width: int,
) -> dict[str, Any]:
    if type(target_candidate) is not PartialFactorCandidateV15 or type(translated) is not dict:
        _fail("V47 filter inventory changed")
    priority = verify_portable_certificate_query_priority_v44(
        translated.get("portable_priority")
    )
    receipt = translated.get("translation_receipt")
    if (
        type(receipt) is not dict
        or receipt.get("translated_priority_id")
        != priority["portable_query_priority_id"]
        or type(receipt.get("selected_target_action_key")) is not int
        or receipt.get("target_transition_outcomes_used") is not False
        or receipt.get("safety_authority_present") is not False
    ):
        _fail("V47 translated-priority receipt changed")
    raw = target_adapter.encode(target_adapter.initial())
    if type(raw) is not tuple:
        _fail("V47 target initial observation changed")
    plan = None
    reason = None
    try:
        plan = plan_joint_successor_version_space_v42(
            model,
            target_candidate,
            target_adapter.catalogue,
            raw,
            maximum_depth=maximum_abstract_depth,
            maximum_support_branch_evaluations=maximum_support_branch_evaluations,
            support_feasible_beam_width=support_feasible_beam_width,
        )
    except GenericJointSuccessorVersionSpacePlannerV42Error as error:
        reason = str(error)
    model_key = None if plan is None else plan["initial_action_key"]
    source_key = receipt["selected_target_action_key"]
    enabled = model_key is not None and model_key == source_key
    inert = _inert_priority(priority)
    filtered = priority if enabled else inert
    payload = {
        "schema": "acfqp.generic_abstract_agreement_query_filter.v47",
        "target_partial_candidate_id": target_candidate.public_document["candidate_id"],
        "target_seed": target_adapter.seed,
        "structural_translation_id": receipt["translation_id"],
        "unfiltered_priority_id": priority["portable_query_priority_id"],
        "model_only_inert_priority_id": inert["portable_query_priority_id"],
        "filtered_priority_id": filtered["portable_query_priority_id"],
        "source_rank_selected_action_key": source_key,
        "abstract_model_initial_action_key": model_key,
        "abstract_model_plan_sha256": (
            None if plan is None else hashlib.sha256(canonical_json_bytes(plan)).hexdigest()
        ),
        "abstract_model_abstention_reason": reason,
        "source_priority_enabled": enabled,
        "decision_rule": "ENABLE_IFF_SOURCE_RANK_ACTION_EQUALS_TARGET_ABSTRACT_MODEL_ACTION",
        "target_transition_outcomes_used_for_filter": False,
        "filter_is_query_ordering_only": True,
        "ground_transition_authority_present": False,
        "safety_authority_present": False,
    }
    receipt_out = {
        **payload,
        "agreement_filter_id": hashlib.sha256(
            _FILTER_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    return {
        "filtered_priority": copy.deepcopy(filtered),
        "model_only_inert_priority": copy.deepcopy(inert),
        "agreement_filter_receipt": receipt_out,
    }


__all__ = ("apply_abstract_agreement_query_filter_v47",)
