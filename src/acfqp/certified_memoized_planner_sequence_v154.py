"""Consume V115 memoized abstract plans inside the certified V150 sequence."""

from __future__ import annotations

import copy
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import certified_planner_abstention_sequence_v150 as v150
from acfqp import construction_k7_domain_registry_extension_v115 as domains_v115
from acfqp import construction_k7_domain_registry_extension_v154 as domains
from acfqp import generic_dependency_revalidated_execution_receipt_v109 as receipt_v109
from acfqp import generic_dependency_revalidated_quotient_sequence_v109 as sequence_v109
from acfqp.phase3e_ids import canonical_json_bytes


class CertifiedMemoizedPlannerSequenceV154Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise CertifiedMemoizedPlannerSequenceV154Error(message)


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


def _plan_v154(document: Mapping[str, Any]) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V154 plan type changed")
    if document.get("schema") != "acfqp.generic_projected_program_memo_plan.v115":
        return receipt_v109._plan(document)  # noqa: SLF001
    payload = {key: value for key, value in document.items() if key != "legality_conditioned_quotient_plan_id"}
    expected_id = domains_v115.extension_content_id_v115(
        domains_v115.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PLAN_V115_DOMAIN,
        payload,
    )
    source = receipt_v109._plan(  # noqa: SLF001
        document.get("source_compiled_factor_program_plan")
    )
    if (
        document.get("legality_conditioned_quotient_plan_id") != expected_id
        or document.get("source_compiled_factor_program_plan_id")
        != source["legality_conditioned_quotient_plan_id"]
        or document.get("partial_candidate_id") != source["partial_candidate_id"]
        or document.get("initial_action_key") != source["initial_action_key"]
        or document.get("projected_action_path") != source["projected_action_path"]
        or document.get("planning_source") != "COMPILED_FACTOR_PROGRAM_MEMOIZED"
        or document.get("abstract_support_branch_evaluations") != 0
        or document.get("source_successor_state_id")
        != document.get("current_successor_state_id")
        or document.get("projected_state_and_exact_legal_set_cache_keyed") is not True
        or document.get("cache_reused_only_under_identical_compiled_successor_state") is not True
        or document.get("initial_illegal_actions_forbidden_in_reused_order") is not True
        or document.get("ground_legality_used_only_after_existing_support_or_failed_certificate") is not True
        or document.get("cached_program_ordering_used_as_safety_authority") is not False
        or document.get("ground_transition_accessed_during_program_memo_reuse") is not False
        or document.get("query_local_exact_overlay_remains_only_safety_authority") is not True
        or document.get("complete_ground_world_model_claimed") is not False
        or canonical_json_bytes(document) != canonical_json_bytes({**payload, "legality_conditioned_quotient_plan_id": expected_id})
    ):
        _fail("V154 memoized plan identity or authority boundary changed")
    return dict(document)


_BUILD_GLOBALS = dict(receipt_v109.__dict__)
_BUILD_GLOBALS["_plan"] = _plan_v154
_BUILD = _clone(receipt_v109.build_dependency_revalidated_execution_receipt_v109, _BUILD_GLOBALS)
_VERIFY_GLOBALS = dict(receipt_v109.__dict__)
_VERIFY_GLOBALS["build_dependency_revalidated_execution_receipt_v109"] = _BUILD
_VERIFY = _clone(receipt_v109.verify_dependency_revalidated_execution_receipt_v109, _VERIFY_GLOBALS)
_ACTUAL_GLOBALS = dict(sequence_v109.__dict__)
_ACTUAL_GLOBALS.update(
    build_dependency_revalidated_execution_receipt_v109=_BUILD,
    verify_dependency_revalidated_execution_receipt_v109=_VERIFY,
)
_ACTUAL = _clone(sequence_v109._actual_receipts, _ACTUAL_GLOBALS)  # noqa: SLF001
_V109_PROXY = SimpleNamespace(**sequence_v109.__dict__)
_V109_PROXY._actual_receipts = _ACTUAL
_RUN_GLOBALS = dict(v150._RUN.__globals__)  # noqa: SLF001
_RUN_GLOBALS["v109"] = _V109_PROXY
_RUN = _clone(v150._RUN, _RUN_GLOBALS)  # noqa: SLF001


def run_certified_memoized_planner_sequence_v154(*args, **kwargs):
    historical = _RUN(*args, **kwargs)
    memoized = sum(
        wrapper["abstract_plan"].get("schema")
        == "acfqp.generic_projected_program_memo_plan.v115"
        for episode in historical["episodes"]
        for wrapper in episode["abstract_plan_receipts"]
    )
    payload = {
        **{key: value for key, value in historical.items() if key not in {"schema", "sequence_id"}},
        "schema": "acfqp.certified_memoized_planner_sequence.v154",
        "query_local_relational_overlay_model_present": True,
        "incomplete_abstract_action_path_treated_as_abstention": True,
        "incomplete_abstract_plan_abstention_count": sum(
            episode["abstract_plan_abstention_count"]
            for episode in historical["episodes"]
        ),
        "certified_legal_search_remains_fallback_authority": True,
        "source_partial_program_mutated_after_certificate_failure": False,
        "every_uncompiled_edge_is_certificate_local": all(
            model["all_overlay_rows_acquired_after_failed_certificate"] is True
            for model in historical["quotient_models_after_each_episode"]
        ),
        "total_query_local_exact_overlay_edge_count": max(
            model["query_local_exact_overlay_edge_count"]
            for model in historical["quotient_models_after_each_episode"]
        ),
        "overlay_promoted_to_global_dynamics": False,
        "query_local_overlay_used_as_safety_authority": False,
        "v115_memoized_compiled_program_plan_receipt_count": memoized,
        "v115_memoized_compiled_program_plan_receipts_consumed": memoized > 0,
        "memoized_plan_revalidated_before_v109_execution_receipt": True,
        "memoized_plan_used_only_for_ordering": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_synthesized": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v154(
            domains.CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN, payload
        ),
    }


__all__ = ("run_certified_memoized_planner_sequence_v154",)
