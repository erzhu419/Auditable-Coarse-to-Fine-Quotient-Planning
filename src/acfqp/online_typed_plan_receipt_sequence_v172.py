"""Issue typed receipts before each abstract orderer returns its plan."""

from __future__ import annotations

import contextvars
import copy
import hashlib
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import certified_memoized_planner_sequence_v154 as v154
from acfqp import construction_k7_domain_registry_extension_v109 as domains_v109
from acfqp import construction_k7_domain_registry_extension_v115 as domains_v115
from acfqp import construction_k7_domain_registry_extension_v172 as domains
from acfqp.phase3e_ids import canonical_json_bytes


V106_PLAN_DOMAIN = "acfqp:generic-legality-conditioned-quotient-plan:v106"
TAXONOMY = {
    (
        "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "OBSERVATION_QUOTIENT_GRAPH",
    ): "OBSERVATION_DERIVED_QUOTIENT_ORDER",
    (
        "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "COMPILED_FACTOR_PROGRAM_FALLBACK",
    ): "DIRECT_COMPILED_PROGRAM_ORDER",
    (
        "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109",
        "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
    ): "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE",
    (
        "acfqp.generic_projected_program_memo_plan.v115",
        "COMPILED_FACTOR_PROGRAM_MEMOIZED",
    ): "SUCCESSOR_STATE_MEMOIZED_PROGRAM_REUSE",
}


class OnlineTypedPlanReceiptSequenceV172Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OnlineTypedPlanReceiptSequenceV172Error(message)


def _clone(function, namespace):
    clone = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _sha(document: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def _plan_id(plan: Mapping[str, Any]) -> str:
    payload = {
        key: value
        for key, value in plan.items()
        if key != "legality_conditioned_quotient_plan_id"
    }
    if plan["schema"] == "acfqp.generic_legality_conditioned_quotient_plan.v106":
        return _content_id(V106_PLAN_DOMAIN, payload)
    if plan["schema"] == "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109":
        return domains_v109.extension_content_id_v109(
            domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_PLAN_V109_DOMAIN,
            payload,
        )
    if plan["schema"] == "acfqp.generic_projected_program_memo_plan.v115":
        return domains_v115.extension_content_id_v115(
            domains_v115.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PLAN_V115_DOMAIN,
            payload,
        )
    _fail("V172 plan schema escaped the complete taxonomy")


_ACTIVE_TRACE: contextvars.ContextVar[list[dict[str, Any]] | None] = (
    contextvars.ContextVar("v172_online_typed_plan_trace", default=None)
)
_BASE_ORDERER = v154._RUN.__globals__["_owned_orderer"]  # noqa: SLF001


def _issuance_receipt(raw, legal, support_source, failure_index, plan, ordinal):
    typed_source = TAXONOMY.get((plan.get("schema"), plan.get("planning_source")))
    if typed_source is None:
        _fail("V172 online plan source escaped the complete taxonomy")
    plan_id = _plan_id(plan)
    if not (
        plan.get("legality_conditioned_quotient_plan_id") == plan_id
        and plan.get("query_local_exact_overlay_remains_only_safety_authority")
        is True
        and plan.get("complete_ground_world_model_claimed") is False
        and plan.get("initial_action_key") in legal
    ):
        _fail("V172 online plan identity or authority boundary changed")
    wrapper = {"raw_state": list(raw), "abstract_plan": copy.deepcopy(plan)}
    payload = {
        "schema": "acfqp.online_typed_abstract_plan_issuance_receipt.v172",
        "issuance_ordinal": ordinal,
        "plan_schema": plan["schema"],
        "planning_source": plan["planning_source"],
        "typed_plan_source": typed_source,
        "source_plan_id": plan_id,
        "source_plan_wrapper_sha256": _sha(wrapper),
        "raw_state_sha256": _sha(list(raw)),
        "exact_legal_action_keys": list(legal),
        "exact_legal_action_keys_sha256": _sha(list(legal)),
        "legality_support_source": support_source,
        "legality_failure_index": failure_index,
        "initial_action_key": plan["initial_action_key"],
        "delegate_plan_sha256_before_receipt": _sha(plan),
        "receipt_issued_before_orderer_return": True,
        "caller_has_not_received_plan_at_receipt_issuance": True,
        "delegate_plan_returned_byte_exact": True,
        "receipt_changes_plan_or_action_order": False,
        "receipt_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    receipt = {
        **payload,
        "online_plan_issuance_receipt_id": domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_ONLINE_PLAN_ISSUANCE_V172_DOMAIN, payload
        ),
    }
    return wrapper, receipt


def _online_orderer(*args, **kwargs):
    delegate = _BASE_ORDERER(*args, **kwargs)

    def order(raw, legal, legality_support_source, legality_failure_index):
        plan = delegate(
            raw, legal, legality_support_source, legality_failure_index
        )
        if plan is None:
            return None
        trace = _ACTIVE_TRACE.get()
        if trace is None:
            _fail("V172 online orderer has no owner-bound issuance trace")
        before = canonical_json_bytes(plan)
        wrapper, receipt = _issuance_receipt(
            raw,
            legal,
            legality_support_source,
            legality_failure_index,
            plan,
            len(trace),
        )
        if canonical_json_bytes(plan) != before:
            _fail("V172 receipt issuance mutated the delegate plan")
        trace.append({"wrapper": wrapper, "receipt": receipt})
        return plan

    return order


_RUN_GLOBALS = dict(v154._RUN.__globals__)  # noqa: SLF001
_RUN_GLOBALS["_owned_orderer"] = _online_orderer
_ONLINE_RUN = _clone(v154._RUN, _RUN_GLOBALS)  # noqa: SLF001
_V154_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v154=domains.extension_content_id_v172,
    CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V172_DOMAIN,
)
_V154_GLOBALS = dict(v154.__dict__)
_V154_GLOBALS.update(_RUN=_ONLINE_RUN, domains=_V154_DOMAIN_PROXY)
_ONLINE_V154 = _clone(v154.run_certified_memoized_planner_sequence_v154, _V154_GLOBALS)


def _execution_join(sequence_id, execution, issuance, ordinal):
    source_payload = {
        key: value
        for key, value in execution.items()
        if key != "actual_dependency_revalidated_execution_receipt_id"
    }
    source_id = domains_v109.extension_content_id_v109(
        domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_EXECUTION_RECEIPT_V109_DOMAIN,
        source_payload,
    )
    receipt = issuance["receipt"]
    if not (
        execution.get("actual_dependency_revalidated_execution_receipt_id")
        == source_id
        and canonical_json_bytes(execution.get("quotient_plan_receipt"))
        == canonical_json_bytes(issuance["wrapper"])
        and execution.get("quotient_plan_id") == receipt["source_plan_id"]
        and execution.get("quotient_proposed_action_key")
        == receipt["initial_action_key"]
        and execution.get("query_local_exact_overlay_remains_only_safety_authority")
        is True
    ):
        _fail("V172 online receipt/execution join changed")
    payload = {
        "schema": "acfqp.online_typed_plan_execution_join.v172",
        "source_sequence_id": sequence_id,
        "execution_join_ordinal": ordinal,
        "episode_index": execution["episode_index"],
        "decision_index": execution["decision_index"],
        "source_v109_execution_receipt_id": source_id,
        "online_plan_issuance_receipt_id": receipt[
            "online_plan_issuance_receipt_id"
        ],
        "typed_plan_source": receipt["typed_plan_source"],
        "chosen_action_key": execution["chosen_action_key"],
        "quotient_proposed_action_key": execution["quotient_proposed_action_key"],
        "chosen_action_matches_admitted_quotient_proposal": execution[
            "chosen_action_matches_admitted_quotient_proposal"
        ],
        "receipt_was_issued_before_plan_return": True,
        "receipt_changes_plan_or_action_order": False,
        "receipt_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "online_execution_join_receipt_id": domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_ONLINE_EXECUTION_JOIN_V172_DOMAIN, payload
        ),
    }


def run_online_typed_plan_receipt_sequence_v172(*args, **kwargs):
    trace: list[dict[str, Any]] = []
    token = _ACTIVE_TRACE.set(trace)
    try:
        historical = _ONLINE_V154(*args, **kwargs)
    finally:
        _ACTIVE_TRACE.reset(token)
    wrappers = [
        wrapper
        for episode in historical["episodes"]
        for wrapper in episode["abstract_plan_receipts"]
    ]
    if not (
        len(wrappers) == len(trace)
        and all(
            canonical_json_bytes(wrapper)
            == canonical_json_bytes(event["wrapper"])
            for wrapper, event in zip(wrappers, trace, strict=True)
        )
    ):
        _fail("V172 online issuance trace escaped stored abstract receipts")
    index = {}
    cursor = 0
    for episode in historical["episodes"]:
        for wrapper in episode["abstract_plan_receipts"]:
            event = trace[cursor]
            cursor += 1
            key = (episode["episode_index"], canonical_json_bytes(wrapper))
            if key in index:
                _fail("V172 online issuance wrapper identity is ambiguous")
            index[key] = event
    joins = []
    for execution in historical["all_actual_legality_conditioned_execution_receipts"]:
        event = index.get(
            (
                execution["episode_index"],
                canonical_json_bytes(execution["quotient_plan_receipt"]),
            )
        )
        if event is None:
            _fail("V172 executed action lacks a prior online plan receipt")
        joins.append(
            _execution_join(historical["sequence_id"], execution, event, len(joins))
        )
    histogram = {
        source: sum(
            event["receipt"]["typed_plan_source"] == source for event in trace
        )
        for source in TAXONOMY.values()
    }
    receipts = [event["receipt"] for event in trace]
    payload = {
        **{
            key: value
            for key, value in historical.items()
            if key not in {"schema", "sequence_id"}
        },
        "schema": "acfqp.online_typed_plan_receipt_sequence.v172",
        "source_v154_shape_sequence_id": historical["sequence_id"],
        "online_plan_issuance_receipts": receipts,
        "online_plan_issuance_receipt_count": len(receipts),
        "online_execution_join_receipts": joins,
        "online_execution_join_receipt_count": len(joins),
        "online_typed_plan_source_histogram": histogram,
        "every_abstract_plan_receipt_issued_before_orderer_return": True,
        "every_executed_action_joins_prior_online_receipt": len(joins)
        == historical["execution_step_count"],
        "delegate_plan_byte_identity_preserved": True,
        "online_receipt_changes_planning_or_execution": False,
        "online_receipt_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_SEQUENCE_V172_DOMAIN, payload
        ),
    }


__all__ = (
    "TAXONOMY",
    "run_online_typed_plan_receipt_sequence_v172",
)
