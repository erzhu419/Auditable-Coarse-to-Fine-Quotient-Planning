"""Bounded exact diagnosis inside one already exposed discovery trajectory.

The source and root action are declared here. Successors are selected only by
exact decision conflict, before any candidate quotient is fitted or evaluated.
"""

from __future__ import annotations

from dataclasses import asdict
import math
from time import perf_counter
from typing import Any, Mapping

from acfqp.science.controlled_predictive_2048_challenges_v2 import ChallengeCase
from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_comparison_v2 import (
    COMPARISON_QUERIES,
    TIE_TOLERANCE,
    disjoint_optimal_pairs,
    optimal_action_set,
)
from acfqp.science.controlled_predictive_quotient_v1 import compile_full_state, plan


SOURCE_CASE_NAME = "discovery_cross_axis_pairs_830011"
SOURCE_ACTION = "LEFT"


def extract_decision_point_cases(discovery_report: Mapping[str, Any]) -> tuple[tuple[ChallengeCase, ...], dict[str, Any]]:
    """Inspect every positive-probability LEFT successor of the fixed H3 source."""
    source_records = [row for row in discovery_report["records"] if row["name"] == SOURCE_CASE_NAME]
    if len(source_records) != 1:
        raise ValueError(f"discovery report must contain exactly one {SOURCE_CASE_NAME}")
    source = source_records[0]
    board = tuple(source["board"])
    started_total = perf_counter()
    closure = build_development_closure(horizon=3, max_nodes=30_000, boards={SOURCE_CASE_NAME: board})
    started = perf_counter()
    compiled = compile_full_state(closure.model)
    compile_seconds = perf_counter() - started
    solutions, replay, query_seconds = {}, {}, {}
    root = closure.model.roots[0]

    def q_values(state: int, query_name: str) -> dict[str, float]:
        query = COMPARISON_QUERIES[query_name]
        solution = solutions[query_name]
        return {
            action: math.fsum(outcome.probability * (
                query.reward_weight * outcome.reward
                + solution.values[compiled.state_to_cell[outcome.next_state]]) for outcome in outcomes)
            for (source_state, action), outcomes in closure.model.rows.items() if source_state == state
        }

    for name, query in COMPARISON_QUERIES.items():
        started = perf_counter()
        solutions[name] = plan(compiled, query)
        query_seconds[name] = perf_counter() - started
        values = q_values(root, name)
        optimal = optimal_action_set(values)
        if SOURCE_ACTION not in optimal:
            raise ValueError(f"declared action {SOURCE_ACTION} is not optimal for source query {name}")
        replay[name] = {"query": asdict(query), "root_q_values": values,
                        "root_optimal_actions": optimal,
                        "root_chosen_action": solutions[name].policy[compiled.state_to_cell[root]]}
    original_queries = source["horizons"]["3"]["queries"]
    replay_errors = [
        abs(replay[name]["root_q_values"][action] - value)
        for name, query in COMPARISON_QUERIES.items() if query.goal_bonus == 0
        for action, value in original_queries[str(query.failure_penalty)]["root_action_values"].items()
    ]
    if max(replay_errors) > TIE_TOLERANCE:
        raise ValueError("fixed source exact replay differs from its recorded discovery action values")
    started = perf_counter()
    inspected, cases = [], []
    for outcome_index, outcome in enumerate(closure.model.rows[root, SOURCE_ACTION]):
        if outcome.probability <= 0:
            continue
        state = outcome.next_state
        characterization = {}
        for name in COMPARISON_QUERIES:
            values = q_values(state, name)
            characterization[name] = {"q_values_with_exact_optimal_continuation": values,
                                      "optimal_actions": optimal_action_set(values)}
        pairs = disjoint_optimal_pairs({name: row["optimal_actions"] for name, row in characterization.items()})
        risk_pairs = disjoint_optimal_pairs({name: characterization[name]["optimal_actions"]
                                            for name, query in COMPARISON_QUERIES.items() if query.goal_bonus == 0})
        witness = {
            "source_case": SOURCE_CASE_NAME, "source_group": source["group"],
            "source_root_state": root, "source_root_action": SOURCE_ACTION,
            "source_outcome_index": outcome_index,
            "one_step_reach_probability_under_source_action": outcome.probability,
            "source_immediate_reward": outcome.reward,
            "parent_state_id": state, "remaining_horizon": closure.model.layers[state],
            "board": closure.boards[state], "terminal_status": closure.model.terminal[state],
            "exact_queries": characterization, "required_query_switch_pairs": pairs,
            "required_risk_only_query_switch_pairs": risk_pairs,
            "retained_for_comparison": bool(pairs),
        }
        if pairs:
            case = ChallengeCase(
                name=f"{SOURCE_CASE_NAME}_after_{SOURCE_ACTION.lower()}_state_{state}",
                group=source["group"], split="EXPOSED_DECISION_POINT",
                board=closure.boards[state], family="exposed_reached_decision_point",
                seed=source["seed"], variant=f"parent_state_{state}",
            )
            cases.append(case)
            witness["comparison_case_name"] = case.name
        inspected.append(witness)
    diagnosis_seconds = perf_counter() - started
    provenance = {
        "source_case": {
            "name": SOURCE_CASE_NAME, "group": source["group"], "split": source["split"],
            "board": board, "family": source["family"], "seed": source["seed"],
        },
        "source_selection_rationale": "The existing exposed source record keeps LEFT at the root for every objective while its exact lifted reward and failure change between risk penalties 0 and 0.05. This follow-up inspects that already observed downstream decision change.",
        "original_observed_policy_metrics": {
            penalty: original_queries[penalty]["metrics"] for penalty in ("0.0", "0.05")
        },
        "declared_source_horizon": 3, "declared_source_action": SOURCE_ACTION,
        "source_exact_query_replay": replay,
        "maximum_recorded_root_q_replay_absolute_error": max(replay_errors),
        "source_action_optimal_for_all_six_queries": True,
        "source_action_uniquely_optimal_for_all_six_queries": all(
            row["root_optimal_actions"] == (SOURCE_ACTION,) for row in replay.values()),
        "selection_rule": "Inspect all positive-probability immediate successors of the declared common-optimal LEFT action. Retain every successor having at least two disjoint exact optimal action sets across the six fixed queries; do not inspect other root-action successors or use candidate performance for selection.",
        "inspected_successor_count": len(inspected),
        "inspected_total_reach_probability": math.fsum(row["one_step_reach_probability_under_source_action"] for row in inspected),
        "retained_conflict_successor_count": len(cases),
        "retained_total_reach_probability": math.fsum(row["one_step_reach_probability_under_source_action"] for row in inspected if row["retained_for_comparison"]),
        "all_inspected_successors": inspected,
        "retained_comparison_cases": [asdict(case) for case in cases],
        "parent_reconstruction_costs": {
            "exact_h3_closure_counts": closure.counts,
            "exact_h3_closure_seconds": closure.elapsed_seconds,
            "exact_compilation_seconds": compile_seconds,
            "exact_plan_count": len(solutions),
            "exact_query_planning_seconds": query_seconds,
            "exact_query_planning_counts": {name: solved.counts for name, solved in solutions.items()},
            "successor_diagnosis_seconds": diagnosis_seconds,
            "total_parent_replay_and_extraction_seconds": perf_counter() - started_total,
            "accounting_note": "These one-time parent reconstruction and diagnosis costs are separate from the subsequent H2 witness comparison workload costs.",
        },
        "limitations": [
            "These decision points are exact-selected exposed diagnostic states from one source group, not fresh challenge cases or independent replications.",
            "This bounded downstream mechanism diagnosis does not replace or change the retained discovery result: no required root-query switch was found among the 36 exposed discovery roots.",
        ],
    }
    return tuple(cases), provenance


__all__ = ("SOURCE_CASE_NAME", "SOURCE_ACTION", "extract_decision_point_cases")
