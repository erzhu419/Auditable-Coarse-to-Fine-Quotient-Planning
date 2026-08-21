"""Minimal BFS proof-dependency receipts for quotient ordering reuse."""

from __future__ import annotations

from collections import defaultdict, deque
import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v109 as domains


class GenericQuotientPlanDependencyReceiptV109Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericQuotientPlanDependencyReceiptV109Error(message)


def _terminal_match(state: tuple[int, ...], rules: tuple[Mapping[str, Any], ...]) -> bool:
    for value, rule in zip(state, rules, strict=True):
        kind = rule["kind"]
        if kind == "EQUAL" and value != rule["value"]:
            return False
        if kind == "AT_LEAST" and value < rule["value"]:
            return False
        if kind == "AT_MOST" and value > rule["value"]:
            return False
        if kind == "OBSERVED_SET" and value not in rule["values"]:
            return False
    return True


def _adjacency(model: Mapping[str, Any]) -> dict[tuple[int, ...], tuple[tuple[int, tuple[int, ...]], ...]]:
    staged: dict[tuple[int, ...], set[tuple[int, tuple[int, ...]]]] = defaultdict(set)
    for row in model["projected_edge_rows"]:
        staged[tuple(row["projected_pre"])].add(
            (row["action_key"], tuple(row["projected_post"]))
        )
    return {state: tuple(sorted(edges)) for state, edges in staged.items()}


def build_quotient_plan_dependency_receipt_v109(
    *,
    source_model: Mapping[str, Any],
    source_plan: Mapping[str, Any],
    initial_projected_state: tuple[int, ...],
) -> dict[str, Any]:
    if (
        source_plan.get("schema")
        != "acfqp.generic_legality_conditioned_quotient_plan.v106"
        or source_plan.get("planning_source") != "OBSERVATION_QUOTIENT_GRAPH"
        or source_plan.get("quotient_graph_id") != source_model.get("quotient_graph_id")
        or type(initial_projected_state) is not tuple
    ):
        _fail("V109 dependency source inventory changed")
    legal = tuple(source_plan["exact_legal_action_keys_at_initial_state"])
    rules = tuple(
        copy.deepcopy(source_plan["embedded_projected_plan"]["terminal_projection_rule"])
    )
    adjacency = _adjacency(source_model)
    queue = deque((initial_projected_state,))
    predecessor: dict[
        tuple[int, ...], tuple[tuple[int, ...], int] | None
    ] = {initial_projected_state: None}
    popped = []
    goal = None
    evaluations = 0
    while queue:
        state = queue.popleft()
        terminal = _terminal_match(state, rules)
        edges = adjacency.get(state, ())
        popped.append(
            {
                "projected_state": list(state),
                "terminal_match": terminal,
                "outgoing_edges": [
                    {"action_key": key, "projected_post": list(post)}
                    for key, post in edges
                ],
            }
        )
        if terminal:
            goal = state
            break
        for key, successor in edges:
            evaluations += 1
            if state == initial_projected_state and key not in legal:
                continue
            if successor not in predecessor:
                predecessor[successor] = (state, key)
                queue.append(successor)
    if goal is None:
        _fail("V109 dependency trace found no quotient goal")
    actions = []
    cursor = goal
    while predecessor[cursor] is not None:
        parent, key = predecessor[cursor]
        actions.append(key)
        cursor = parent
    actions.reverse()
    if (
        actions != source_plan["projected_action_path"]
        or evaluations != source_plan["abstract_support_branch_evaluations"]
    ):
        _fail("V109 dependency trace differs from source plan")
    payload = {
        "schema": "acfqp.generic_quotient_plan_dependency_receipt.v109",
        "source_quotient_plan_id": source_plan[
            "legality_conditioned_quotient_plan_id"
        ],
        "source_quotient_graph_id": source_model["quotient_graph_id"],
        "partial_candidate_id": source_plan["partial_candidate_id"],
        "initial_projected_state": list(initial_projected_state),
        "exact_legal_action_keys": list(legal),
        "terminal_projection_rule": [dict(row) for row in rules],
        "ordered_bfs_dependency_rows": popped,
        "source_projected_action_path": actions,
        "source_initial_action_key": actions[0],
        "source_branch_evaluations": evaluations,
        "dependency_row_count": len(popped),
        "dependency_validation_check_count": sum(
            1 + len(row["outgoing_edges"]) for row in popped
        ),
        "only_dequeued_pre_goal_states_and_the_first_goal_retained": True,
        "unrelated_quotient_edges_deliberately_excluded": True,
        "receipt_is_ordering_dependency_not_safety_authority": True,
        "query_local_exact_certificate_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "dependency_receipt_id": domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_DEPENDENCY_V109_DOMAIN,
            payload,
        ),
    }


def revalidate_quotient_plan_dependency_v109(
    receipt: Mapping[str, Any],
    *,
    current_model: Mapping[str, Any],
    current_terminal_projection_rule: tuple[Mapping[str, Any], ...],
) -> dict[str, Any] | None:
    if type(receipt) is not dict:
        _fail("V109 dependency receipt type changed")
    payload = {
        key: value for key, value in receipt.items() if key != "dependency_receipt_id"
    }
    if (
        receipt.get("dependency_receipt_id")
        != domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_DEPENDENCY_V109_DOMAIN,
            payload,
        )
        or receipt.get("schema")
        != "acfqp.generic_quotient_plan_dependency_receipt.v109"
        or receipt.get("terminal_projection_rule")
        != [dict(row) for row in current_terminal_projection_rule]
    ):
        return None
    adjacency = _adjacency(current_model)
    checks = 0
    for row in receipt["ordered_bfs_dependency_rows"]:
        state = tuple(row["projected_state"])
        checks += 1
        if _terminal_match(state, current_terminal_projection_rule) is not row[
            "terminal_match"
        ]:
            return None
        actual_edges = [
            {"action_key": key, "projected_post": list(post)}
            for key, post in adjacency.get(state, ())
        ]
        checks += len(actual_edges)
        if actual_edges != row["outgoing_edges"]:
            return None
    if checks != receipt["dependency_validation_check_count"]:
        _fail("V109 dependency validation accounting changed")
    return {
        "dependency_receipt_id": receipt["dependency_receipt_id"],
        "source_quotient_graph_id": receipt["source_quotient_graph_id"],
        "current_quotient_graph_id": current_model["quotient_graph_id"],
        "dependency_validation_check_count": checks,
        "source_action_path_remains_valid_under_current_dependency_slice": True,
        "full_current_quotient_graph_identity_required": False,
    }


__all__ = (
    "build_quotient_plan_dependency_receipt_v109",
    "revalidate_quotient_plan_dependency_v109",
)
