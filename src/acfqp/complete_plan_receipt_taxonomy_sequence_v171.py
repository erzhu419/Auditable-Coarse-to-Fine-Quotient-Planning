"""Attach the complete four-source V170 taxonomy to a fresh V171 sequence."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v109 as domains_v109
from acfqp import construction_k7_domain_registry_extension_v115 as domains_v115
from acfqp import construction_k7_domain_registry_extension_v171 as domains
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
    raise ValueError("V171 plan schema escaped V170 taxonomy")


def _typed(sequence_id, episode, ordinal, wrapper):
    if type(wrapper) is not dict or set(wrapper) != {"raw_state", "abstract_plan"}:
        raise ValueError("V171 abstract plan wrapper changed")
    plan = wrapper["abstract_plan"]
    if type(plan) is not dict or type(wrapper["raw_state"]) is not list:
        raise ValueError("V171 abstract plan wrapper type changed")
    typed_source = TAXONOMY.get((plan.get("schema"), plan.get("planning_source")))
    if typed_source is None:
        raise ValueError("V171 plan source escaped V170 taxonomy")
    identity = _plan_id(plan)
    if not (
        plan.get("legality_conditioned_quotient_plan_id") == identity
        and plan.get("query_local_exact_overlay_remains_only_safety_authority")
        is True
        and plan.get("complete_ground_world_model_claimed") is False
        and type(plan.get("initial_action_key")) is int
        and plan["initial_action_key"]
        in plan.get("exact_legal_action_keys_at_initial_state", [])
        and type(plan.get("projected_action_path")) is list
        and plan["projected_action_path"]
        and plan["projected_action_path"][0] == plan["initial_action_key"]
    ):
        raise ValueError("V171 plan identity or safety boundary changed")
    ground_values = [
        plan[name]
        for name in (
            "ground_transition_accessed_during_abstract_search",
            "ground_transition_accessed_during_dependency_revalidation",
            "ground_transition_accessed_during_program_memo_reuse",
        )
        if name in plan
    ]
    if ground_values != [False]:
        raise ValueError("V171 abstract planning accessed a ground transition")
    payload = {
        "schema": "acfqp.typed_abstract_plan_receipt.v171",
        "source_sequence_id": sequence_id,
        "episode_index": episode["episode_index"],
        "plan_ordinal": ordinal,
        "plan_schema": plan["schema"],
        "planning_source": plan["planning_source"],
        "typed_plan_source": typed_source,
        "source_plan_id": identity,
        "source_wrapper_sha256": _sha(wrapper),
        "raw_state_sha256": _sha(wrapper["raw_state"]),
        "initial_action_key": plan["initial_action_key"],
        "projected_action_count": len(plan["projected_action_path"]),
        "ground_transition_accessed_during_abstract_reasoning": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "typed_receipt_changes_planning_or_execution": False,
        "typed_receipt_is_safety_authority": False,
    }
    return {
        **payload,
        "typed_plan_receipt_id": domains.extension_content_id_v171(
            domains.CONSTRUCTION_K7_TYPED_PLAN_RECEIPT_V171_DOMAIN, payload
        ),
    }


def _join(sequence_id, episode, execution, typed, wrappers):
    if not (
        type(execution) is dict
        and execution.get("schema")
        == "acfqp.generic_dependency_revalidated_execution_receipt.v109"
        and execution.get("receipt_is_observation_not_safety_authority") is True
        and execution.get("query_local_exact_overlay_remains_only_safety_authority")
        is True
        and type(execution.get("quotient_plan_receipt")) is dict
    ):
        raise ValueError("V171 execution receipt boundary changed")
    source_payload = {
        key: value
        for key, value in execution.items()
        if key != "actual_dependency_revalidated_execution_receipt_id"
    }
    source_id = domains_v109.extension_content_id_v109(
        domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_EXECUTION_RECEIPT_V109_DOMAIN,
        source_payload,
    )
    if execution.get("actual_dependency_revalidated_execution_receipt_id") != source_id:
        raise ValueError("V171 execution receipt identity changed")
    target = canonical_json_bytes(execution["quotient_plan_receipt"])
    matches = [
        index
        for index, wrapper in enumerate(wrappers)
        if canonical_json_bytes(wrapper) == target
    ]
    if len(matches) != 1:
        raise ValueError("V171 execution did not join exactly one plan instance")
    ordinal = matches[0]
    typed_receipt = typed[ordinal]
    plan = execution["quotient_plan_receipt"]["abstract_plan"]
    if not (
        execution["episode_index"] == episode["episode_index"]
        and execution["raw_state"] == execution["quotient_plan_receipt"]["raw_state"]
        and execution["quotient_plan_id"] == plan["legality_conditioned_quotient_plan_id"]
        and execution["quotient_proposed_action_key"] == plan["initial_action_key"]
        and execution["chosen_action_key"] in execution["legal_action_keys"]
    ):
        raise ValueError("V171 plan/execution join changed")
    payload = {
        "schema": "acfqp.typed_plan_execution_join_receipt.v171",
        "source_sequence_id": sequence_id,
        "episode_index": episode["episode_index"],
        "decision_index": execution["decision_index"],
        "source_v109_execution_receipt_id": source_id,
        "typed_plan_receipt_id": typed_receipt["typed_plan_receipt_id"],
        "source_plan_ordinal": ordinal,
        "typed_plan_source": typed_receipt["typed_plan_source"],
        "raw_state_sha256": typed_receipt["raw_state_sha256"],
        "chosen_action_key": execution["chosen_action_key"],
        "quotient_proposed_action_key": execution["quotient_proposed_action_key"],
        "quotient_proposal_admitted_to_real_action_order": execution[
            "quotient_proposal_admitted_to_real_action_order"
        ],
        "chosen_action_matches_admitted_quotient_proposal": execution[
            "chosen_action_matches_admitted_quotient_proposal"
        ],
        "actual_action_ordering_source": execution["actual_action_ordering_source"],
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "typed_join_changes_planning_or_execution": False,
        "typed_join_is_safety_authority": False,
    }
    return {
        **payload,
        "execution_join_receipt_id": domains.extension_content_id_v171(
            domains.CONSTRUCTION_K7_EXECUTION_JOIN_RECEIPT_V171_DOMAIN, payload
        ),
    }


def annotate_complete_plan_receipt_taxonomy_sequence_v171(
    sequence: Mapping[str, Any],
) -> dict[str, Any]:
    if type(sequence) is not dict or type(sequence.get("sequence_id")) is not str:
        raise ValueError("V171 source sequence changed")
    source_sequence_id = sequence["sequence_id"]
    rows = []
    histogram = {source: 0 for source in TAXONOMY.values()}
    typed_count = join_count = 0
    for episode in sequence["episodes"]:
        wrappers = episode["abstract_plan_receipts"]
        typed = [
            _typed(source_sequence_id, episode, ordinal, wrapper)
            for ordinal, wrapper in enumerate(wrappers)
        ]
        if len({row["source_wrapper_sha256"] for row in typed}) != len(typed):
            raise ValueError("V171 duplicate plan instance in one episode")
        joins = [
            _join(source_sequence_id, episode, execution, typed, wrappers)
            for execution in episode["actual_legality_conditioned_execution_receipts"]
        ]
        if len(joins) != episode["execution_steps"]:
            raise ValueError("V171 episode execution join count changed")
        row_histogram = {
            source: sum(item["typed_plan_source"] == source for item in typed)
            for source in TAXONOMY.values()
        }
        for source, count in row_histogram.items():
            histogram[source] += count
        typed_count += len(typed)
        join_count += len(joins)
        rows.append(
            {
                "schema": "acfqp.complete_plan_receipt_taxonomy_episode.v171",
                "episode_index": episode["episode_index"],
                "typed_plan_receipts": typed,
                "typed_plan_receipt_count": len(typed),
                "typed_plan_source_histogram": row_histogram,
                "execution_join_receipts": joins,
                "execution_join_receipt_count": len(joins),
                "untyped_abstract_plan_receipt_count": 0,
                "unjoined_executed_action_count": 0,
            }
        )
    payload = {
        **{
            key: value
            for key, value in sequence.items()
            if key not in {"schema", "sequence_id"}
        },
        "schema": "acfqp.complete_plan_receipt_taxonomy_sequence.v171",
        "source_v168_shape_sequence_id": source_sequence_id,
        "typed_plan_taxonomy_episode_rows": rows,
        "typed_plan_receipt_count": typed_count,
        "execution_join_receipt_count": join_count,
        "typed_plan_source_histogram": histogram,
        "untyped_abstract_plan_receipt_count": 0,
        "unjoined_executed_action_count": 0,
        "complete_four_source_taxonomy_applied": True,
        "every_abstract_plan_instance_typed": True,
        "every_executed_action_exactly_joined": True,
        "taxonomy_changes_planning_or_execution": False,
        "taxonomy_is_model_or_safety_authority": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v171(
            domains.CONSTRUCTION_K7_SEQUENCE_V171_DOMAIN, payload
        ),
    }


__all__ = (
    "TAXONOMY",
    "annotate_complete_plan_receipt_taxonomy_sequence_v171",
)
