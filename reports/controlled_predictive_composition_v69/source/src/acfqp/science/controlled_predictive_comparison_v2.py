"""Declared public-board comparisons for the exploratory controlled quotient.

The same finite empirical kernel is reused for every objective and matched arm.
All declared roots are retained. Exact dynamics label decision conflicts and
audit frozen policies; they do not select roots or tune quotient tolerances.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from itertools import combinations
import math
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from acfqp.science.controlled_predictive_2048_v1 import (
    DevelopmentClosure,
    PUBLIC_DEVELOPMENT_BOARDS,
    _compiled_inventory,
    build_development_closure,
)
from acfqp.science.controlled_predictive_2048_challenges_v2 import (
    ChallengeCase,
    generate_challenge_cases,
)
from acfqp.science.controlled_predictive_quotient_v1 import (
    CompiledModel,
    FiniteModel,
    Plan,
    Query,
    _actions,
    _distance,
    _signature,
    action_outcome_shuffle,
    audit_policy,
    build_quotient,
    compile_full_state,
    evaluate_compiled_policy,
    plan,
    sample_model,
)


COMPARISON_QUERIES: dict[str, Query] = {
    "risk_0": Query(1.0, 0.0, 0.0),
    "risk_0_05": Query(1.0, 0.05, 0.0),
    "risk_0_2": Query(1.0, 0.2, 0.0),
    "risk_1": Query(1.0, 1.0, 0.0),
    "risk_5": Query(1.0, 5.0, 0.0),
    "goal_1_risk_1": Query(1.0, 1.0, 1.0),
}
SAMPLE_SEEDS = (832101, 832102, 832103)
FRESH_CHALLENGE_SPLITS = frozenset({"TRAIN_DEVELOPMENT", "CALIBRATION", "EVALUATION"})
TIE_TOLERANCE = 1e-10
COMPONENTS = ("reward", "failure", "success", "value")


def comparison_cases() -> tuple[ChallengeCase, ...]:
    """Keep 24 fresh candidates distinct from three already exposed V1 regressions."""
    regression = tuple(ChallengeCase(
        name=f"v1_regression_{name}", group=f"v1_regression_{name}", split="REGRESSION",
        board=board, family="seen_v1_regression", seed=0,
    ) for name, board in PUBLIC_DEVELOPMENT_BOARDS.items())
    return (*generate_challenge_cases(), *regression)


def optimal_action_set(q_values: Mapping[str, float], tolerance: float = TIE_TOLERANCE) -> tuple[str, ...]:
    """Keep numerical ties; an arbitrary argmax change is not a decision switch."""
    if not q_values:
        return ()
    best = max(q_values.values())
    return tuple(sorted(action for action, value in q_values.items() if best - value <= tolerance))


def disjoint_optimal_pairs(action_sets: Mapping[str, Sequence[str]]) -> list[tuple[str, str]]:
    return [
        (left, right) for left, right in combinations(action_sets, 2)
        if action_sets[left] and action_sets[right]
        and set(action_sets[left]).isdisjoint(action_sets[right])
    ]


def _exact_q_values(exact: FiniteModel, compiled: CompiledModel, solved: Plan,
                    query: Query, *, one_step: bool = False) -> dict[str, float]:
    root = exact.roots[0]

    def continuation(state: int) -> float:
        if not one_step:
            return solved.values[compiled.state_to_cell[state]]
        status = exact.terminal[state]
        return query.goal_bonus if status == "WON" else -query.failure_penalty if status == "LOST" else 0.0

    return {
        action: math.fsum(o.probability * (query.reward_weight * o.reward + continuation(o.next_state)) for o in row)
        for (state, action), row in exact.rows.items() if state == root
    }


def _sum_counts(rows: Sequence[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(row[key])
    return dict(counts)


def _evaluate(compiled: CompiledModel, closure: DevelopmentClosure, query: Query,
              exact_set: Sequence[str], exact_value: float, solved: Plan | None = None,
              premeasured_plan_seconds: float | None = None) -> dict[str, Any]:
    started = perf_counter()
    solution = plan(compiled, query) if solved is None else solved
    planning_seconds = perf_counter() - started if premeasured_plan_seconds is None else premeasured_plan_seconds
    started = perf_counter()
    predicted = evaluate_compiled_policy(compiled, solution, query)
    forecast_seconds = perf_counter() - started
    started = perf_counter()
    audited = audit_policy(closure.model, compiled, solution, query)
    audit_seconds = perf_counter() - started
    root = closure.model.roots[0]
    cell = compiled.state_to_cell[root]
    forecast = predicted.root_metrics[cell]
    actual = audited.root_metrics[root]
    action = solution.policy.get(cell)
    return {
        "root_action": action,
        "root_action_in_exact_optimal_set": action in exact_set if exact_set else action is None,
        "predicted_root_metrics": forecast,
        "exact_lifted_root_metrics": actual,
        "exact_lifted_objective_regret": exact_value - actual["value"],
        "root_prediction_absolute_errors": {name: abs(forecast[name] - actual[name]) for name in COMPONENTS},
        "planning_seconds": planning_seconds,
        "planning_counts": solution.counts,
        "compiled_policy_evaluation_seconds": forecast_seconds,
        "compiled_policy_evaluation_counts": predicted.counts,
        "ground_audit_seconds": audit_seconds,
        "ground_audit_counts": audited.counts,
        "recovery_calls": 0,
    }


def _fit(builder: Callable[[], CompiledModel], closure: DevelopmentClosure) -> tuple[CompiledModel, dict[str, Any]]:
    started = perf_counter()
    compiled = builder()
    construction_seconds = perf_counter() - started
    started = perf_counter()
    inventory = _compiled_inventory(compiled, closure)
    inventory["inventory_serialization_seconds"] = perf_counter() - started
    inventory["construction_seconds"] = construction_seconds
    inventory["active_state_compression_factor"] = (
        closure.counts["active_states"] / inventory["active_cells"] if inventory["active_cells"] else None
    )
    return compiled, inventory


def _reuse_costs(results: Mapping[str, dict[str, Any]], inventory: dict[str, Any],
                 *, closure_seconds: float, sampling_seconds: float) -> list[dict[str, Any]]:
    """Charge one construction and the measured prefix, with no simulated warmup."""
    ordered = list(results.values())
    counts = sorted({min(count, len(ordered)) for count in (1, 3, 6)})
    output = []
    for count in counts:
        prefix = ordered[:count]
        planning = math.fsum(row["planning_seconds"] for row in prefix)
        forecasting = math.fsum(row["compiled_policy_evaluation_seconds"] for row in prefix)
        auditing = math.fsum(row["ground_audit_seconds"] for row in prefix)
        construction = inventory["construction_seconds"]
        output.append({
            "query_count": count,
            "query_names": list(results)[:count],
            "shared_exact_closure_seconds": closure_seconds,
            "shared_sampling_seconds": sampling_seconds,
            "one_time_model_construction_seconds": construction,
            "cumulative_planning_seconds": planning,
            "cumulative_forecast_evaluation_seconds": forecasting,
            "cumulative_ground_audit_seconds": auditing,
            "cumulative_planning_counts": _sum_counts(prefix, "planning_counts"),
            "cumulative_forecast_evaluation_counts": _sum_counts(prefix, "compiled_policy_evaluation_counts"),
            "cumulative_ground_audit_counts": _sum_counts(prefix, "ground_audit_counts"),
            "construction_plus_planning_seconds": construction + planning,
            "sample_build_plan_forecast_audit_seconds": sampling_seconds + construction + planning + forecasting + auditing,
            "including_shared_exact_closure_seconds": closure_seconds + sampling_seconds + construction + planning + forecasting + auditing,
        })
    return output


def _arm_result(compiled: CompiledModel, inventory: dict[str, Any], closure: DevelopmentClosure,
                queries: Mapping[str, Query], references: Mapping[str, dict[str, Any]],
                switch_pairs: Sequence[tuple[str, str]], *, sampling_seconds: float,
                privileged: bool, solved_references: Mapping[str, tuple[Plan, float]] | None = None) -> dict[str, Any]:
    results = {}
    for name, query in queries.items():
        solved, seconds = solved_references[name] if solved_references else (None, None)
        reference = references[name]
        results[name] = _evaluate(compiled, closure, query, reference["optimal_actions"],
                                  reference["optimal_value"], solved, seconds)
    preserved = [
        [left, right] for left, right in switch_pairs
        if results[left]["root_action_in_exact_optimal_set"]
        and results[right]["root_action_in_exact_optimal_set"]
        and results[left]["root_action"] != results[right]["root_action"]
    ]
    return {
        "privileged_exact_dynamics": privileged,
        "model_build_count": 1,
        "query_count_using_same_compiled_model": len(queries),
        "inventory": inventory,
        "queries": results,
        "required_switch_pair_count": len(switch_pairs),
        "preserved_exact_switch_pairs": preserved,
        "all_required_switch_pairs_preserved": len(preserved) == len(switch_pairs) if switch_pairs else None,
        "measured_cumulative_workloads": _reuse_costs(results, inventory,
            closure_seconds=closure.elapsed_seconds, sampling_seconds=sampling_seconds),
    }


def _local_conflict_witness(exact: FiniteModel, compiled: CompiledModel,
                            closure: DevelopmentClosure) -> dict[str, Any] | None:
    """Find a representative/member exact mismatch without exhaustive pair search."""
    actions = _actions(exact)
    for cell_id, cell in compiled.cells.items():
        if cell.terminal != "ACTIVE" or len(cell.members) < 2:
            continue
        left = cell.members[0]
        signature = _signature(exact, left, actions[left], compiled.state_to_cell)
        for right in cell.members[1:]:
            other = _signature(exact, right, actions[right], compiled.state_to_cell)
            for left_coordinate, right_coordinate in zip(signature, other, strict=True):
                reward, tv = _distance((left_coordinate,), (right_coordinate,))
                if reward or tv:
                    return {
                        "cell": cell_id, "remaining_horizon": cell.layer,
                        "left_state": left, "right_state": right,
                        "left_board": closure.boards[left], "right_board": closure.boards[right],
                        "action": left_coordinate[0], "exact_reward_difference": reward,
                        "exact_successor_cell_total_variation": tv,
                        "scope": "Local exact action-coordinate mismatch in a fitted merged cell; not evidence of root reachability or a causal explanation of root regret.",
                    }
    return None


def _subset_summary(cases: Sequence[dict[str, Any]]) -> dict[str, Any]:
    completed = [case for case in cases if case["status"] == "COMPLETE"]
    arms: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for case in completed:
        for name, arm in case["references"].items():
            arms[name].append((case["case"]["name"], arm))
        for sampled in case["sampled_runs"]:
            for name, arm in sampled["arms"].items():
                arms[name].append((case["case"]["name"], arm))
    summaries = {}
    paired: dict[str, list[dict[str, float]]] = defaultdict(list)
    for case in completed:
        for sampled in case["sampled_runs"]:
            for query_name, row in sampled["matched_comparisons"].items():
                paired[query_name].append(row)
    for name, runs in arms.items():
        rows = [query for _, arm in runs for query in arm["queries"].values()]
        switch_runs = [arm for _, arm in runs if arm["required_switch_pair_count"]]
        compressions = [arm["inventory"]["active_state_compression_factor"] for _, arm in runs
                        if arm["inventory"]["active_state_compression_factor"] is not None]
        by_query = defaultdict(list)
        for _, arm in runs:
            for query_name, row in arm["queries"].items():
                by_query[query_name].append(row)
        summaries[name] = {
            "case_count": len({case for case, _ in runs}),
            "case_seed_run_count": len(runs),
            "query_evaluation_count": len(rows),
            "root_action_exact_optimal_fraction": sum(row["root_action_in_exact_optimal_set"] for row in rows) / len(rows),
            "maximum_exact_lifted_objective_regret": max(row["exact_lifted_objective_regret"] for row in rows),
            "maximum_component_prediction_absolute_errors": {
                component: max(row["root_prediction_absolute_errors"][component] for row in rows)
                for component in COMPONENTS
            },
            "mean_active_state_compression_factor": math.fsum(compressions) / len(compressions) if compressions else None,
            "minimum_active_state_compression_factor": min(compressions) if compressions else None,
            "switch_case_seed_run_count": len(switch_runs),
            "all_required_switch_pairs_preserved_fraction": (
                sum(arm["all_required_switch_pairs_preserved"] for arm in switch_runs) / len(switch_runs)
                if switch_runs else None
            ),
            "by_query": {
                query_name: {
                    "count": len(query_rows),
                    "mean_exact_lifted_objective_regret": math.fsum(row["exact_lifted_objective_regret"] for row in query_rows) / len(query_rows),
                    "maximum_exact_lifted_objective_regret": max(row["exact_lifted_objective_regret"] for row in query_rows),
                    "root_action_exact_optimal_fraction": sum(row["root_action_in_exact_optimal_set"] for row in query_rows) / len(query_rows),
                } for query_name, query_rows in by_query.items()
            },
        }
    return {
        "declared_case_count": len(cases),
        "declared_source_group_count": len({case["case"]["group"] for case in cases}),
        "status_counts": dict(Counter(case["status"] for case in cases)),
        "completed_case_count": len(completed),
        "completed_source_group_count": len({case["case"]["group"] for case in completed}),
        "actual_switch_case_count": sum(case["decision_conflicts"]["has_required_query_switch"] for case in completed),
        "risk_only_switch_case_count": sum(case["decision_conflicts"]["has_required_risk_only_query_switch"] for case in completed),
        "deferred_consequence_case_count": sum(case["decision_conflicts"]["has_h1_vs_horizon_disjoint_optima"] for case in completed),
        "arms": summaries,
        "matched_empirical_comparisons_by_query": {
            query_name: {
                "case_seed_count": len(rows),
                "mean_quotient_extra_regret_over_full_state": math.fsum(row["quotient_extra_regret_over_full_state"] for row in rows) / len(rows),
                "maximum_quotient_extra_regret_over_full_state": max(row["quotient_extra_regret_over_full_state"] for row in rows),
                "mean_quotient_actual_value_advantage_over_shuffle": math.fsum(row["quotient_actual_value_advantage_over_shuffle"] for row in rows) / len(rows),
                "minimum_quotient_actual_value_advantage_over_shuffle": min(row["quotient_actual_value_advantage_over_shuffle"] for row in rows),
            } for query_name, rows in paired.items()
        },
    }


def run_comparison(*, cases: Sequence[ChallengeCase] | None = None, horizon: int = 3,
                   max_nodes: int = 30_000, samples_per_row: int = 64,
                   sample_seeds: Sequence[int] = SAMPLE_SEEDS,
                   queries: Mapping[str, Query] | None = None,
                   progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Run every declared case and emit compact evidence, never a scientific PASS."""
    fixtures = tuple(comparison_cases() if cases is None else cases)
    objectives = dict(COMPARISON_QUERIES if queries is None else queries)
    if not fixtures or not objectives or not sample_seeds:
        raise ValueError("cases, queries, and sample_seeds must be nonempty")
    if len({case.name for case in fixtures}) != len(fixtures):
        raise ValueError("case names must be unique")
    if len(set(sample_seeds)) != len(sample_seeds):
        raise ValueError("sample seeds must be unique")
    started_all = perf_counter()
    results: list[dict[str, Any]] = []
    board_owners: dict[tuple[int, ...], set[str]] = defaultdict(set)
    root_owners: dict[tuple[int, ...], set[str]] = defaultdict(set)
    for case in fixtures:
        root_owners[case.board].add(case.split)
    for case in fixtures:
        started_case = perf_counter()
        record: dict[str, Any] = {"case": asdict(case)}
        try:
            closure = build_development_closure(horizon=horizon, max_nodes=max_nodes,
                                                boards={case.name: case.board})
        except ValueError as error:
            if "complete closure exceeds max_nodes=" not in str(error):
                raise
            record.update(status="CLOSURE_BUDGET_EXCEEDED", reason=str(error),
                          elapsed_seconds=perf_counter() - started_case)
            results.append(record)
            if progress:
                progress({"case": case.name, "status": record["status"], "completed": len(results), "total": len(fixtures)})
            continue
        for board in set(closure.boards.values()):
            board_owners[board].add(case.split)
        record["coverage"] = {**closure.counts, "exact_closure_seconds": closure.elapsed_seconds,
                              "unique_boards_excluding_horizon": len(set(closure.boards.values())),
                              "complete_all_legal_actions_and_outcomes": True}
        exact, exact_inventory = _fit(lambda: compile_full_state(closure.model), closure)
        references, exact_solutions = {}, {}
        for name, query in objectives.items():
            started = perf_counter()
            solved = plan(exact, query)
            seconds = perf_counter() - started
            exact_solutions[name] = solved, seconds
            q_values = _exact_q_values(closure.model, exact, solved, query)
            h1_values = _exact_q_values(closure.model, exact, solved, query, one_step=True)
            optima, h1_optima = optimal_action_set(q_values), optimal_action_set(h1_values)
            references[name] = {
                "q_values_with_exact_optimal_continuation": q_values,
                "optimal_actions": optima,
                "optimal_value": solved.values[exact.roots[0]],
                "h1_q_values": h1_values,
                "h1_optimal_actions": h1_optima,
                "h1_vs_horizon_disjoint_optima": bool(optima and h1_optima and set(optima).isdisjoint(h1_optima)),
            }
        switch_pairs = disjoint_optimal_pairs({name: value["optimal_actions"] for name, value in references.items()})
        risk_pairs = disjoint_optimal_pairs({name: references[name]["optimal_actions"]
                                           for name, query in objectives.items() if query.goal_bonus == 0})
        record["decision_conflicts"] = {
            "exact_query_references": references,
            "required_query_switch_pairs": switch_pairs,
            "has_required_query_switch": bool(switch_pairs),
            "required_risk_only_query_switch_pairs": risk_pairs,
            "has_required_risk_only_query_switch": bool(risk_pairs),
            "has_h1_vs_horizon_disjoint_optima": any(row["h1_vs_horizon_disjoint_optima"] for row in references.values()),
        }
        record["references"] = {"exact_ground": _arm_result(exact, exact_inventory, closure,
            objectives, references, switch_pairs, sampling_seconds=0, privileged=True,
            solved_references=exact_solutions)}
        oracle, inventory = _fit(lambda: build_quotient(closure.model), closure)
        record["references"]["oracle_exact_quotient"] = _arm_result(oracle, inventory, closure,
            objectives, references, switch_pairs, sampling_seconds=0, privileged=True)
        record["sampled_runs"] = []
        for seed in sample_seeds:
            started = perf_counter()
            empirical = sample_model(closure.model, samples_per_row=samples_per_row, seed=seed)
            sampling_seconds = perf_counter() - started
            sampled: dict[str, Any] = {
                "sample_seed": seed, "sampling_seconds": sampling_seconds,
                "empirical_draws": len(empirical.rows) * samples_per_row,
                "empirical_rows": len(empirical.rows),
                "empirical_model_sample_count": 1, "arms": {},
            }
            builders = {
                "full_state_empirical": lambda: compile_full_state(empirical),
                "learned_controlled_quotient": lambda: build_quotient(empirical, reward_tolerance=0.01, tv_tolerance=0.2),
                "action_outcome_shuffle": lambda: build_quotient(action_outcome_shuffle(empirical), reward_tolerance=0.01, tv_tolerance=0.2),
            }
            for name, builder in builders.items():
                compiled, inventory = _fit(builder, closure)
                sampled["arms"][name] = _arm_result(compiled, inventory, closure, objectives,
                    references, switch_pairs, sampling_seconds=sampling_seconds, privileged=False)
                if name == "learned_controlled_quotient":
                    started = perf_counter()
                    sampled["local_exact_cell_conflict_witness"] = _local_conflict_witness(closure.model, compiled, closure)
                    sampled["posthoc_witness_diagnosis_seconds"] = perf_counter() - started
            sampled["matched_comparisons"] = {
                name: {
                    "quotient_extra_regret_over_full_state": (
                        sampled["arms"]["learned_controlled_quotient"]["queries"][name]["exact_lifted_objective_regret"]
                        - sampled["arms"]["full_state_empirical"]["queries"][name]["exact_lifted_objective_regret"]
                    ),
                    "quotient_actual_value_advantage_over_shuffle": (
                        sampled["arms"]["learned_controlled_quotient"]["queries"][name]["exact_lifted_root_metrics"]["value"]
                        - sampled["arms"]["action_outcome_shuffle"]["queries"][name]["exact_lifted_root_metrics"]["value"]
                    ),
                } for name in objectives
            }
            record["sampled_runs"].append(sampled)
        record["status"] = "COMPLETE"
        record["elapsed_seconds"] = perf_counter() - started_case
        results.append(record)
        if progress:
            progress({"case": case.name, "split": case.split, "status": record["status"],
                      "completed": len(results), "total": len(fixtures), "states": closure.counts["states"],
                      "actual_switch": bool(switch_pairs), "elapsed_seconds": record["elapsed_seconds"]})
    splits = sorted({case.split for case in fixtures})
    overlap_pairs = {}
    for left, right in combinations(splits, 2):
        examples = [board for board, owners in board_owners.items() if {left, right} <= owners]
        overlap_pairs[f"{left}|{right}"] = {"board_count": len(examples), "example_boards": sorted(examples)[:2]}
    root_overlap = [board for board, owners in root_owners.items() if len(owners) > 1]
    summaries = {}
    for split in ["ALL", "FRESH_CHALLENGES", *splits]:
        subset = (results if split == "ALL" else
                  [row for row in results if row["case"]["split"] in FRESH_CHALLENGE_SPLITS] if split == "FRESH_CHALLENGES" else
                  [row for row in results if row["case"]["split"] == split])
        switch_subset = [row for row in subset if row["status"] == "COMPLETE" and row["decision_conflicts"]["has_required_query_switch"]]
        risk_subset = [row for row in subset if row["status"] == "COMPLETE" and row["decision_conflicts"]["has_required_risk_only_query_switch"]]
        summaries[split] = {"all_declared": _subset_summary(subset), "actual_switch_subset": _subset_summary(switch_subset),
                            "risk_only_switch_subset": _subset_summary(risk_subset)}
    return {
        "schema": "acfqp.controlled_predictive_comparison.v2",
        "status": "DEVELOPMENT_COMPLETE" if all(row["status"] == "COMPLETE" for row in results) else "DEVELOPMENT_COMPLETE_WITH_CLOSURE_EXCLUSIONS",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "settings": {"horizon": horizon, "max_nodes": max_nodes, "samples_per_row": samples_per_row,
                     "sample_seeds": list(sample_seeds), "reward_tolerance": 0.01, "tv_tolerance": 0.2,
                     "tie_tolerance": TIE_TOLERANCE, "queries": {name: asdict(query) for name, query in objectives.items()},
                     "query_order": list(objectives), "reward_units": "merge score / 2048"},
        "all_declared_candidates_retained": True,
        "case_count": len(fixtures),
        "fresh_challenge_case_count": sum(case.split in FRESH_CHALLENGE_SPLITS for case in fixtures),
        "seen_v1_regression_case_count": sum(case.split == "REGRESSION" for case in fixtures),
        "cases": results, "summary_by_split": summaries,
        "board_identity_overlap_excluding_horizon": {
            "unique_covered_boards": len(board_owners),
            "root_cross_split_overlap_count": len(root_overlap), "root_examples": sorted(root_overlap)[:2],
            "cross_split_covered_board_count": sum(len(owners) > 1 for owners in board_owners.values()),
            "pairwise_closure_overlap": overlap_pairs,
            "complete_closure_case_count": sum(row["status"] == "COMPLETE" for row in results),
            "coverage_excludes_unfinished_closures": True,
            "unseen_state_generalization_demonstrated": False,
        },
        "elapsed_seconds": perf_counter() - started_all,
        "accounting": {
            "matched_inputs": "Each case/seed samples its exact covered action rows once; full-state and controlled quotient receive the same empirical kernel. The destructive control permutes those same rows across legal actions.",
            "references": "Exact ground and exact quotient are constructed once per case and use privileged exact dynamics; their measurements are not repeated for every sampling seed.",
            "costs": "One-time coverage enumeration, shared sampling, model construction, inventory serialization, all-cell planning, compiled-policy prediction and ground audits are separate. Cumulative workloads use actual ordered query measurements with one construction; inventory serialization is report-only and excluded from workload totals.",
            "switching": "Only queries with disjoint exact optimal action sets require a root switch. Sets include all actions within 1e-10 of the optimum, computed using exact optimal continuation.",
            "one_step": "H1 uses the identical root actions and spawn outcomes, retaining immediate reward and terminal success/failure only; no alternate sampling or closure is used.",
            "execution_boundary": "Planning and lifting use registered state IDs. Board-and-horizon lookup storage is reported, but fresh-process loading and online board encoding are not measured by these B-stage workload totals.",
            "witness": "One representative/member action-coordinate mismatch per candidate and sampling seed is diagnosed on the exact kernel after fitting. Diagnostic time is separate; no witness is fed back into the partition.",
        },
        "limitations": [
            "This is a public finite-board exploratory comparison, not a frozen confirmatory Gate or a full-game evaluation.",
            "The encoder remains a board-and-horizon lookup and every covered row is sampled separately per case. Provenance splits do not establish held-out encoder generalization; closure overlap is reported using board identities without horizon.",
            "Three prespecified sample seeds measure finite-sampling sensitivity on fixed boards, not population uncertainty or independent board replication.",
            "Spatial variants share a source group and are not independent board replications; source-group counts accompany board counts.",
            "No-switch cases and closure-budget exclusions remain in all-declared accounting. The actual-switch subset is an exact-labeled descriptive subset, not a selected replacement experiment.",
            "Risk weights are scalar objective penalties, not hard safety constraints. Terminal cutoff states are not failures.",
            "The frozen learned-representation FAIL and U006 nonexecution are unchanged.",
        ],
    }


__all__ = ("COMPARISON_QUERIES", "SAMPLE_SEEDS", "TIE_TOLERANCE", "comparison_cases", "optimal_action_set", "disjoint_optimal_pairs", "run_comparison")
