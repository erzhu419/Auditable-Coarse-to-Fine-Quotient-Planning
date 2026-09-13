"""Exact characterization of a fixed mechanism cohort, without method fitting.

The ten query policies and the exact quotient are privileged finite-model
references. Witnesses are the first three conflict states in state-ID order;
all declared cases and all strict query-pair counts remain in the report.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from itertools import combinations
import math
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from .controlled_predictive_2048_v1 import DevelopmentClosure, build_development_closure
from .controlled_predictive_comparison_v3 import (
    COMPARISON_QUERIES, COMPONENTS, NUMERIC_TOLERANCE, PROBE_QUERIES,
    _arm, _fit, _reference, _switches,
)
from .controlled_predictive_quotient_v1 import Query, _actions, build_quotient, compile_full_state


def strict_query_pairs(references: Mapping[str, Mapping[str, Any]], state: int,
                       names: Sequence[str]) -> list[tuple[str, str]]:
    """Different deterministic tie choices alone never constitute a conflict."""
    return [(left, right) for left, right in combinations(names, 2)
            if set(references[left]["optimal_actions"][state]).isdisjoint(
                references[right]["optimal_actions"][state])]


def first_action_metrics(closure: DevelopmentClosure, state: int,
                         continuation: Mapping[int, Mapping[str, float]],
                         query: Query) -> dict[str, dict[str, Any]]:
    """Force each first action, then retain the supplied query policy unchanged."""
    result = {}
    for action in _actions(closure.model)[state]:
        row = closure.model.rows[state, action]
        immediate_reward = math.fsum(outcome.probability * outcome.reward for outcome in row)
        future_reward = math.fsum(outcome.probability * continuation[outcome.next_state]["reward"] for outcome in row)
        failure = math.fsum(outcome.probability * continuation[outcome.next_state]["failure"] for outcome in row)
        success = math.fsum(outcome.probability * continuation[outcome.next_state]["success"] for outcome in row)
        result[action] = {
            "reward": immediate_reward + future_reward, "failure": failure, "success": success,
            "value": query.reward_weight * (immediate_reward + future_reward)
                - query.failure_penalty * failure + query.goal_bonus * success,
            "immediate_reward": immediate_reward, "continuation_reward": future_reward,
            "one_step_failure": math.fsum(outcome.probability for outcome in row
                if closure.model.terminal[outcome.next_state] == "LOST"),
            "one_step_success": math.fsum(outcome.probability for outcome in row
                if closure.model.terminal[outcome.next_state] == "WON"),
        }
    return result


def _state_characterization(closure: DevelopmentClosure, state: int,
                            queries: Mapping[str, Query], references: Mapping[str, Any],
                            private: Mapping[str, Any], reach: Mapping[str, Mapping[int, float]]) -> dict[str, Any]:
    policies = {}
    for name, query in queries.items():
        actions = first_action_metrics(closure, state, private[name]["actual"], query)
        policies[name] = {
            "selected_action": private[name]["policy"][state],
            "optimal_action_set": references[name]["optimal_actions"][state],
            "optimal_policy_metrics": private[name]["actual"][state],
            "first_action_then_frozen_query_policy": actions,
        }
    pairs = strict_query_pairs(references, state, tuple(queries))
    pair_details = []
    for left, right in pairs:
        left_metrics, right_metrics = private[left]["actual"][state], private[right]["actual"][state]
        left_query, right_query = queries[left], queries[right]
        def objective(metrics: Mapping[str, float], query: Query) -> float:
            return query.reward_weight * metrics["reward"] - query.failure_penalty * metrics["failure"] + query.goal_bonus * metrics["success"]
        pair_details.append({
            "left_query": left, "right_query": right,
            "right_minus_left_optimal_policy_components": {
                component: right_metrics[component] - left_metrics[component]
                for component in ("reward", "failure", "success")},
            "left_query_loss_using_frozen_right_policy": left_metrics["value"] - objective(right_metrics, left_query),
            "right_query_loss_using_frozen_left_policy": right_metrics["value"] - objective(left_metrics, right_query),
        })
    return {
        "state": state, "board": closure.boards[state],
        "remaining_horizon": closure.model.layers[state], "queries": policies,
        "canonical_root_policy_reach_probability_by_query": {name: reach[name][state] for name in queries},
        "strict_query_pair_count": len(pairs), "strict_query_pairs": pair_details,
    }


def canonical_policy_reach(closure: DevelopmentClosure, policy: Mapping[int, str]
                           ) -> tuple[dict[int, float], dict[str, int]]:
    """Propagate probability under one frozen policy, starting uniformly at roots."""
    mass = {state: 0.0 for state in closure.model.layers}
    for state in closure.model.roots:
        mass[state] += 1.0 / len(closure.model.roots)
    counts = {"positive_mass_active_states": 0, "state_action_rows": 0, "outcomes": 0}
    for state in sorted(closure.model.layers, key=lambda item: (-closure.model.layers[item], item)):
        if not mass[state] or closure.model.terminal[state] != "ACTIVE":
            continue
        row = closure.model.rows[state, policy[state]]
        counts["positive_mass_active_states"] += 1
        counts["state_action_rows"] += 1
        counts["outcomes"] += len(row)
        for outcome in row:
            mass[outcome.next_state] += mass[state] * outcome.probability
    return mass, counts


def characterize_closure(closure: DevelopmentClosure, *,
                         fit_queries: Mapping[str, Query] | None = None,
                         probe_queries: Mapping[str, Query] | None = None) -> dict[str, Any]:
    """Expose exact query conflicts and test exact quotient policy optimality."""
    bank = dict(COMPARISON_QUERIES if fit_queries is None else fit_queries)
    probes = dict(PROBE_QUERIES if probe_queries is None else probe_queries)
    if not bank or bank.keys() & probes.keys():
        raise ValueError("a nonempty bank and distinct query names are required")
    queries = {**bank, **probes}
    groups = {"FIT_BANK": tuple(bank), "PROBES": tuple(probes), "ALL": tuple(queries)}
    active = tuple(sorted(state for state, status in closure.model.terminal.items() if status == "ACTIVE"))
    started = perf_counter()
    exact, exact_inventory, _ = _fit(lambda: compile_full_state(closure.model), closure)
    references = _reference(closure, exact, queries)
    full_arm, private = _arm(exact, exact_inventory, closure, queries, references, groups,
        sampling_seconds=0.0, privileged=True, supplied_plans=True)
    quotient, quotient_inventory, _ = _fit(lambda: build_quotient(closure.model), closure)
    quotient_arm, quotient_private = _arm(quotient, quotient_inventory, closure, queries, references, groups,
        sampling_seconds=0.0, privileged=True)
    core_seconds = perf_counter() - started
    started = perf_counter()
    reach_started = perf_counter()
    reach, reach_counts = {}, Counter()
    for name in queries:
        reach[name], counts = canonical_policy_reach(closure, private[name]["policy"])
        reach_counts.update(counts)
    reach_seconds = perf_counter() - reach_started
    conflicts = [state for state in active if strict_query_pairs(references, state, tuple(queries))]
    reached = tuple(state for state in active if any(reach[name][state] > 0 for name in queries))
    reached_conflicts = [state for state in conflicts if state in reached]
    root_switches = _switches(references, closure.model.roots, groups)
    all_switches = _switches(references, active, groups)
    classification = ("ROOT_QUERY_CONFLICT" if root_switches["ALL"]["states_with_required_switch"]
        else "CANONICAL_POLICY_REACHED_DOWNSTREAM_ONLY_QUERY_CONFLICT" if reached_conflicts
        else "OFF_POLICY_ONLY_QUERY_CONFLICT" if conflicts else "NO_QUERY_CONFLICT")
    by_horizon = {}
    for horizon in sorted({closure.model.layers[state] for state in active}, reverse=True):
        states = tuple(state for state in active if closure.model.layers[state] == horizon)
        by_horizon[str(horizon)] = {"active_states": len(states),
            "query_groups": _switches(references, states, groups),
            "possible_state_query_pairs": len(states) * math.comb(len(queries), 2)}
    component_summary = {}
    for name in queries:
        actual = private[name]["actual"]
        component_summary[name] = {
            "all_active_states": len(active),
            "states_with_positive_failure_probability": sum(actual[state]["failure"] > 0 for state in active),
            "states_with_positive_success_probability": sum(actual[state]["success"] > 0 for state in active),
            "ranges": {component: {"minimum": min(actual[state][component] for state in active),
                "maximum": max(actual[state][component] for state in active)}
                for component in COMPONENTS},
        }
    component_differences = {component: max(abs(private[name]["actual"][state][component]
        - quotient_private[name]["actual"][state][component]) for name in queries for state in active)
        for component in COMPONENTS}
    roots = [_state_characterization(closure, state, queries, references, private, reach)
             for state in closure.model.roots]
    witnesses = [_state_characterization(closure, state, queries, references, private, reach)
                 for state in conflicts[:3]]
    extra_work = Counter()
    for row in references.values():
        extra_work.update(row["all_state_action_labeling_counts"])
    witness_states = (*closure.model.roots, *conflicts[:3])
    witness_rows = sum(len(_actions(closure.model)[state]) for state in witness_states) * len(queries)
    witness_outcomes = sum(len(closure.model.rows[state, action]) for state in witness_states
        for action in _actions(closure.model)[state]) * len(queries)
    return {
        "classification": classification,
        "exact_root_required_switches": root_switches,
        "exact_all_state_required_switches": all_switches,
        "canonical_policy_reach": {
            "active_states_reached_by_any_query_policy": len(reached),
            "reached_conflict_states": len(reached_conflicts),
            "off_policy_only_conflict_states": len(conflicts) - len(reached_conflicts),
            "reached_state_required_switches": _switches(references, reached, groups),
            "strict_pairs_at_states_reached_by_either_pair_policy": sum(
                reach[left][state] > 0 or reach[right][state] > 0 for state in conflicts
                for left, right in strict_query_pairs(references, state, tuple(queries))),
            "scope": "Positive exact occupancy under at least one of the ten canonical root-optimal policies. Sorted-action DP tie selection is fixed; other tied optimal policies are not enumerated. Multiple roots, if supplied, receive equal initial mass.",
        },
        "possible_all_state_query_pairs": len(active) * math.comb(len(queries), 2),
        "possible_root_query_pairs": len(closure.model.roots) * math.comb(len(queries), 2),
        "conflicts_by_remaining_horizon": by_horizon,
        "root_characterization": roots,
        "conflict_witnesses": witnesses,
        "conflict_witness_rule": "At most three conflict states, in ascending state-ID order, with every query shown. Root tables are always included separately.",
        "all_state_optimal_policy_components": component_summary,
        "references": {"full_state_exact": full_arm, "zero_tolerance_exact_quotient": quotient_arm},
        "exact_quotient_comparison": {
            "all_state_query_count": len(active) * len(queries),
            "all_state_optimal_action_count": sum(row["all_active_states"]["exact_optimal_action_count"] for row in quotient_arm["queries"].values()),
            "all_state_optimal_full_policy_count": sum(row["all_active_states"]["optimal_full_policy_count"] for row in quotient_arm["queries"].values()),
            "maximum_actual_policy_component_difference_from_full_state": component_differences,
            "maximum_all_state_objective_regret": max(row["all_active_states"]["maximum_exact_lifted_objective_regret"] for row in quotient_arm["queries"].values()),
            "note": "Both references use the exact kernel. Optimal policies can choose different tied actions; component differences are measured separately from objective optimality.",
        },
        "characterization_cost": {
            "compile_plan_forecast_audit_seconds": core_seconds,
            "conflict_tables_and_component_summaries_seconds": perf_counter() - started,
            "additional_action_labeling_seconds": math.fsum(row["all_state_action_labeling_seconds"] for row in references.values()),
            "additional_action_labeling_counts": dict(extra_work),
            "root_and_witness_first_action_rows": witness_rows,
            "root_and_witness_first_action_outcomes": witness_outcomes,
            "additional_exact_transition_generation_calls": 0,
            "canonical_policy_reach_seconds": reach_seconds,
            "canonical_policy_reach_counts": dict(reach_counts),
        },
    }


def _closure_overlap(cases: Sequence[Any], board_sets: Mapping[str, set[tuple[int, ...]]],
                     layered_sets: Mapping[str, set[tuple[tuple[int, ...], int]]]) -> dict[str, Any]:
    from .controlled_predictive_cohort_v6 import board_symmetries

    orbit_sets = {name: {min(board_symmetries(board).values()) for board in boards}
                  for name, boards in board_sets.items()}
    pairs = []
    for left, right in combinations(board_sets, 2):
        raw, layered, orbit = (len(board_sets[left] & board_sets[right]),
            len(layered_sets[left] & layered_sets[right]), len(orbit_sets[left] & orbit_sets[right]))
        if raw or layered or orbit:
            pairs.append({"left_case": left, "right_case": right,
                "shared_raw_boards": raw, "shared_board_and_horizon_states": layered,
                "shared_dihedral_board_orbits": orbit})
    return {
        "completed_closure_count": len(board_sets), "overlapping_case_pairs": pairs,
        "unique_raw_boards": len(set().union(*board_sets.values())) if board_sets else 0,
        "unique_board_and_horizon_states": len(set().union(*layered_sets.values())) if layered_sets else 0,
        "unique_dihedral_board_orbits": len(set().union(*orbit_sets.values())) if orbit_sets else 0,
        "roots_present_in_other_completed_closures": [{"root_case": case.name,
            "other_case_names": [name for name, boards in board_sets.items()
                                 if name != case.name and tuple(case.board) in boards]}
            for case in cases if any(name != case.name and tuple(case.board) in boards
                                    for name, boards in board_sets.items())],
        "additional_closure_calls": 0,
        "scope": "Already-built V6 closures only. Raw-board and dihedral overlap ignore horizon. No historical descendant closures are reconstructed.",
    }


def _summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    completed = [record for record in records if record["status"] == "COMPLETE"]
    return {
        "declared_case_count": len(records), "completed_case_count": len(completed),
        "closure_budget_exceeded_count": sum(record["status"] == "CLOSURE_BUDGET_EXCEEDED" for record in records),
        "classification_counts": dict(Counter(record["classification"] for record in records)),
        "source_group_count": len({record["case"]["group"] for record in records}),
        "root_strict_query_pairs": sum(record["exact_root_required_switches"]["ALL"]["required_state_query_pair_count"] for record in completed),
        "all_state_strict_query_pairs": sum(record["exact_all_state_required_switches"]["ALL"]["required_state_query_pair_count"] for record in completed),
        "all_state_conflict_states": sum(record["exact_all_state_required_switches"]["ALL"]["states_with_required_switch"] for record in completed),
        "canonical_policy_reached_conflict_states": sum(record["canonical_policy_reach"]["reached_conflict_states"] for record in completed),
        "canonical_policy_reached_strict_query_pairs": sum(record["canonical_policy_reach"]["reached_state_required_switches"]["ALL"]["required_state_query_pair_count"] for record in completed),
        "active_states": sum(record["coverage"]["active_states"] for record in completed),
        "exact_transition_generation_calls_completed_cases": sum(record["coverage"]["exact_transition_row_calls"] for record in completed),
        "exact_outcomes_enumerated_completed_cases": sum(record["coverage"]["exact_outcomes_enumerated"] for record in completed),
        "exact_quotient_active_cells": sum(record["references"]["zero_tolerance_exact_quotient"]["inventory"]["active_cells"] for record in completed),
        "all_state_query_count": sum(record["exact_quotient_comparison"]["all_state_query_count"] for record in completed),
        "exact_quotient_all_state_optimal_full_policy_count": sum(record["exact_quotient_comparison"]["all_state_optimal_full_policy_count"] for record in completed),
        "maximum_exact_quotient_all_state_objective_regret": max((record["exact_quotient_comparison"]["maximum_all_state_objective_regret"] for record in completed), default=None),
    }


def run_characterization_v6(*, cases: Sequence[Any] | None = None,
                            cohort_roster: Mapping[str, Any] | None = None,
                            max_nodes: int = 30_000,
                            fit_queries: Mapping[str, Query] | None = None,
                            probe_queries: Mapping[str, Query] | None = None,
                            progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    from .controlled_predictive_challenges_v6 import declared_cases_v6

    declared = tuple(declared_cases_v6() if cases is None else cases)
    queries = {**(COMPARISON_QUERIES if fit_queries is None else fit_queries),
               **(PROBE_QUERIES if probe_queries is None else probe_queries)}
    roster_rows = {row["case"]["name"]: row for row in cohort_roster["cases"]} if cohort_roster is not None else {}
    started = perf_counter()
    records, board_sets, layered_sets = [], {}, {}
    for case in declared:
        case_started = perf_counter()
        record: dict[str, Any] = {"case": asdict(case)}
        if case.name in roster_rows:
            record["pre_outcome_exposure"] = {key: value for key, value in roster_rows[case.name].items() if key != "case"}
        try:
            closure = build_development_closure(horizon=case.horizon, max_nodes=max_nodes,
                                                boards={case.name: tuple(case.board)})
        except ValueError as error:
            if "complete closure exceeds max_nodes=" not in str(error):
                raise
            record.update(status="CLOSURE_BUDGET_EXCEEDED", classification="CLOSURE_BUDGET_EXCEEDED",
                error=str(error), elapsed_seconds=perf_counter() - case_started,
                exact_transition_generation_calls=None,
                cost_note="Failed closure elapsed time is charged; the existing builder does not return partial transition counts.")
        else:
            board_sets[case.name] = set(closure.boards.values())
            layered_sets[case.name] = {(board, closure.model.layers[state]) for state, board in closure.boards.items()}
            record.update(status="COMPLETE", coverage={**closure.counts,
                "exact_closure_seconds": closure.elapsed_seconds, "complete_all_action_all_outcome_closure": True})
            record.update(characterize_closure(closure, fit_queries=fit_queries, probe_queries=probe_queries))
            record["elapsed_seconds"] = perf_counter() - case_started
        records.append(record)
        if progress is not None:
            progress({"case": case.name, "status": record["status"], "classification": record["classification"],
                      "completed_records": len(records), "declared_records": len(declared)})
    overlap_started = perf_counter()
    overlap = _closure_overlap(declared, board_sets, layered_sets)
    overlap["elapsed_seconds"] = perf_counter() - overlap_started
    return {
        "schema": "controlled_predictive_characterization_v6", "status": "COMPLETE",
        "queries": {name: asdict(query) for name, query in queries.items()},
        "scope": "Privileged exact characterization of all fixed development inputs; no sampled representation, query refinement, encoder training, scientific Gate, or prospective assurance run.",
        "settings": {"max_nodes": max_nodes, "numeric_tolerance": NUMERIC_TOLERANCE,
            "conflict_witness_limit_per_case": 3, "all_declared_cases_retained": True},
        "cohort_roster": cohort_roster,
        "cases": records, "summary": _summary(records),
        "summary_by_family": {family: _summary([row for row in records if row["case"]["family"] == family])
                              for family in dict.fromkeys(case.family for case in declared)},
        "summary_by_role": {role: _summary([row for row in records if row["case"]["role"] == role])
                            for role in dict.fromkeys(case.role for case in declared)},
        "summary_by_pre_outcome_exposure": {exposure: _summary([row for row in records
            if row.get("pre_outcome_exposure", {}).get("exposure", "UNREGISTERED") == exposure])
            for exposure in dict.fromkeys(row.get("pre_outcome_exposure", {}).get("exposure", "UNREGISTERED") for row in records)},
        "within_cohort_closure_overlap": overlap,
        "elapsed_seconds": perf_counter() - started,
        "u006_assurance_started": False, "deferred_v2_24_case_cohort_executed": False,
    }
