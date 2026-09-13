"""Exposed sampling-error decomposition and fixed, nested sample-size curve.

Exact dynamics generate observations and audit frozen policies. They do not
allocate observations or enter either empirical representation builder.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, replace
import math
import random
from time import perf_counter
from typing import Any, Callable, Iterator, Mapping, Sequence

from acfqp.science.controlled_predictive_2048_challenges_v2 import _source_board
from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_comparison_v2 import COMPARISON_QUERIES, SAMPLE_SEEDS, optimal_action_set
from acfqp.science.controlled_predictive_comparison_v3 import (
    COMPONENTS, NUMERIC_TOLERANCE, PROBE_QUERIES, RefinementCase,
    _arm, _fit, _reference, refinement_cases,
)
from acfqp.science.controlled_predictive_quotient_v1 import (
    FiniteModel, Outcome, Query, _actions, _evaluate_policy,
    build_quotient, compile_full_state, plan, sample_model,
)


SAMPLE_BUDGETS = (64, 256, 1024)
NEW_BASE_SEEDS = (837101, 837201)
EXPOSED_NAMES = ("v3_cross_axis_pairs_835401", "v3_gradient_bottleneck_835402")
QUERIES = {**COMPARISON_QUERIES, **PROBE_QUERIES}
QUERY_GROUPS = {"FIT_BANK": tuple(COMPARISON_QUERIES), "PROBES": tuple(PROBE_QUERIES), "ALL": tuple(QUERIES)}


def sampling_cases() -> tuple[RefinementCase, ...]:
    exposed = tuple(replace(case, split="EXPOSED_SAMPLING_DIAGNOSIS")
                    for case in refinement_cases() if case.name in EXPOSED_NAMES)
    fresh = tuple(RefinementCase(
        f"v4_sampling_{family}_{seed + index}", f"v4_sampling_{family}_{seed + index}",
        "NEW_DEVELOPMENT", _source_board(family, seed + index), family, seed + index, 3,
    ) for index, family in enumerate(("cross_axis_pairs", "gradient_bottleneck"))
      for seed in NEW_BASE_SEEDS)
    return (*exposed, *fresh)


def nested_sample_curve(model: FiniteModel, budgets: Sequence[int], seed: int
                        ) -> Iterator[tuple[int, FiniteModel, dict[str, Any]]]:
    """Append per-row draws at each dose; no future-dose draws occur early.

    Separate deterministic row streams ensure each dose extends every previous
    row prefix. RNGs and counts are retained only while this iterator is alive.
    Sampling time is cumulative and includes every materialized stage model.
    Time spent by callers evaluating a yielded model is excluded.
    """
    budgets = tuple(budgets)
    if not budgets or budgets[0] < 1 or tuple(sorted(set(budgets))) != budgets:
        raise ValueError("budgets must be positive, strictly increasing integers")
    started = perf_counter()
    streams = {key: random.Random(f"acfqp-v4:{seed}:{key[0]}:{key[1]}") for key in sorted(model.rows)}
    counts: dict[tuple[int, str], Counter[tuple[int, float]]] = {key: Counter() for key in streams}
    cumulative_seconds, previous = perf_counter() - started, 0
    for budget in budgets:
        started = perf_counter()
        rows = {}
        for key, rng in streams.items():
            row = model.rows[key]
            draws = rng.choices(row, weights=[item.probability for item in row], k=budget - previous)
            counts[key].update((item.next_state, item.reward) for item in draws)
            rows[key] = tuple(Outcome(count / budget, target, reward)
                              for (target, reward), count in sorted(counts[key].items()))
        empirical = FiniteModel(dict(model.layers), dict(model.terminal), rows, model.roots)
        increment = perf_counter() - started
        cumulative_seconds += increment
        yield budget, empirical, {
            "stream": "independent_row_rng_nested_v4", "sample_seed": seed,
            "samples_per_row": budget, "incremental_draws": (budget - previous) * len(rows),
            "cumulative_draws": budget * len(rows),
            "incremental_sampling_seconds": increment,
            "cumulative_sampling_seconds_including_prior_stage_materialization": cumulative_seconds,
        }
        previous = budget


def _q_components(model: FiniteModel, state: int, action: str,
                  continuation: Mapping[int, Mapping[str, float]], query: Query) -> dict[str, float]:
    row = model.rows[state, action]
    result = {component: math.fsum(item.probability * continuation[item.next_state][component]
                                  for item in row) for component in ("reward", "failure", "success")}
    result["reward"] += math.fsum(item.probability * item.reward for item in row)
    result["value"] = query.reward_weight * result["reward"] - query.failure_penalty * result["failure"] + query.goal_bonus * result["success"]
    return result


def _row_error(exact: FiniteModel, empirical: FiniteModel, state: int, action: str) -> dict[str, Any]:
    truth: dict[tuple[int, float], float] = defaultdict(float)
    sample: dict[tuple[int, float], float] = defaultdict(float)
    for item in exact.rows[state, action]:
        truth[item.next_state, item.reward] += item.probability
    for item in empirical.rows[state, action]:
        sample[item.next_state, item.reward] += item.probability
    missing = [key for key in truth if key not in sample]
    return {
        "exact_support_size": len(truth), "observed_support_size": len(sample),
        "missed_support_count": len(missing), "missed_true_probability_mass": math.fsum(truth[key] for key in missing),
        "missed_true_probability_range": [min(truth[key] for key in missing), max(truth[key] for key in missing)] if missing else None,
        "total_variation": 0.5 * math.fsum(abs(truth.get(key, 0) - sample.get(key, 0)) for key in truth.keys() | sample.keys()),
        "true_immediate_failure_probability": math.fsum(probability for (target, _), probability in truth.items() if exact.terminal[target] == "LOST"),
        "empirical_immediate_failure_probability": math.fsum(probability for (target, _), probability in sample.items() if empirical.terminal[target] == "LOST"),
    }


def decompose_policy_error(exact: FiniteModel, empirical: FiniteModel, query: Query,
                           *, boards: Mapping[int, tuple[int, ...]] | None = None) -> dict[str, Any]:
    """Diagnosis only: decompose Q bias and locate reachable wrong decisions.

    Qhat(pi)-Q* = [Qtrue(pi)-Q*] + [Qhat(Vtrue(pi))-Qtrue(pi)]
                + [Qhat(Vhat(pi))-Qhat(Vtrue(pi))].
    The terms are continuation-policy loss, root kernel bias, and propagated
    continuation prediction bias. No term is used to change the sampler.
    """
    actions = _actions(exact)
    exact_compiled, empirical_compiled = compile_full_state(exact), compile_full_state(empirical)
    optimum, solved = plan(exact_compiled, query), plan(empirical_compiled, query)
    optimal_policy = {state: optimum.policy[exact_compiled.state_to_cell[state]] for state in actions}
    policy = {state: solved.policy[empirical_compiled.state_to_cell[state]] for state in _actions(empirical)}
    all_states = tuple(exact.layers)
    truth_optimal = _evaluate_policy(exact.terminal, exact.rows, all_states, optimal_policy, query).root_metrics
    truth_policy = _evaluate_policy(exact.terminal, exact.rows, all_states, policy, query).root_metrics
    predicted = _evaluate_policy(empirical.terminal, empirical.rows, all_states, policy, query).root_metrics
    root = exact.roots[0]

    def action_rows(state: int) -> dict[str, Any]:
        result = {}
        for action in actions[state]:
            q_star = _q_components(exact, state, action, truth_optimal, query)
            q_true = _q_components(exact, state, action, truth_policy, query)
            q_root_sample = _q_components(empirical, state, action, truth_policy, query)
            q_hat = _q_components(empirical, state, action, predicted, query)
            result[action] = {
                "true_optimal_continuation": q_star, "true_frozen_continuation": q_true,
                "predicted_frozen_continuation": q_hat,
                "empirical_row_with_true_optimal_continuation": _q_components(empirical, state, action, truth_optimal, query),
                "signed_continuation_policy_difference": {key: q_true[key] - q_star[key] for key in COMPONENTS},
                "signed_local_kernel_bias": {key: q_root_sample[key] - q_true[key] for key in COMPONENTS},
                "signed_continuation_prediction_bias": {key: q_hat[key] - q_root_sample[key] for key in COMPONENTS},
                "row_error": _row_error(exact, empirical, state, action),
            }
        return result

    root_rows = action_rows(root)
    true_q = {action: row["true_optimal_continuation"]["value"] for action, row in root_rows.items()}
    empirical_q = {action: row["predicted_frozen_continuation"]["value"] for action, row in root_rows.items()}
    root_gap = max(true_q.values()) - true_q[policy[root]]
    continuation_loss = true_q[policy[root]] - truth_policy[root]["value"]
    occupancy: dict[int, float] = defaultdict(float, {root: 1.0})
    contributors = []
    for state in sorted(exact.layers, key=lambda item: (-exact.layers[item], item)):
        if exact.terminal[state] != "ACTIVE" or occupancy[state] == 0:
            continue
        rows = action_rows(state)
        values = {action: row["true_optimal_continuation"]["value"] for action, row in rows.items()}
        local_gap = max(values.values()) - values[policy[state]]
        if local_gap > NUMERIC_TOLERANCE:
            estimates = {action: row["predicted_frozen_continuation"]["value"] for action, row in rows.items()}
            contributors.append({
                "state": state, "board": boards[state] if boards else None,
                "remaining_horizon": exact.layers[state], "true_reach_probability": occupancy[state],
                "chosen_action": policy[state], "exact_optimal_actions": optimal_action_set(values),
                "empirical_optimal_actions": optimal_action_set(estimates), "exact_q_values": values,
                "empirical_q_values": estimates, "local_optimality_gap": local_gap,
                "reach_weighted_gap": occupancy[state] * local_gap,
                "action_rows": rows,
            })
        for item in exact.rows[state, policy[state]]:
            occupancy[item.next_state] += occupancy[state] * item.probability
    total_regret = truth_optimal[root]["value"] - truth_policy[root]["value"]
    return {
        "root_action": policy[root], "exact_root_optimal_actions": optimal_action_set(true_q),
        "empirical_root_optimal_actions": optimal_action_set(empirical_q),
        "root_action_gap": root_gap, "root_continuation_loss": continuation_loss,
        "root_total_regret": total_regret, "root_actions": root_rows,
        "positive_reachable_decision_contributors": contributors,
        "sum_reach_weighted_local_gaps": math.fsum(item["reach_weighted_gap"] for item in contributors),
        "gap_sum_residual": total_regret - math.fsum(item["reach_weighted_gap"] for item in contributors),
    }


def diagnose_original_exposed(report: Mapping[str, Any], *, max_nodes: int = 30_000) -> dict[str, Any]:
    started = perf_counter()
    records = []
    for record in report["cases"]:
        if record["case"]["name"] not in EXPOSED_NAMES:
            continue
        case = record["case"]
        closure = build_development_closure(horizon=case["horizon"], max_nodes=max_nodes,
                                             boards={case["name"]: tuple(case["board"])})
        replay = []
        for sampled in record["sampled_runs"]:
            empirical = sample_model(closure.model, 64, sampled["sample_seed"])
            bad = {}
            for name, prior in sampled["arms"]["full_state_empirical"]["queries"].items():
                if prior["exact_lifted_objective_regret"] <= NUMERIC_TOLERANCE:
                    continue
                diagnosis = decompose_policy_error(closure.model, empirical, QUERIES[name], boards=closure.boards)
                if diagnosis["root_action"] != prior["root_action"] or abs(diagnosis["root_total_regret"] - prior["exact_lifted_objective_regret"]) > NUMERIC_TOLERANCE:
                    raise AssertionError("original empirical baseline replay changed")
                bad[name] = diagnosis
            replay.append({"sample_seed": sampled["sample_seed"], "bad_query_count": len(bad), "bad_queries": bad})
        records.append({"case": {**case, "split": "EXPOSED_SAMPLING_DIAGNOSIS"},
                        "closure_counts": closure.counts, "samples_per_row": 64,
                        "replayed_draws": 64 * len(closure.model.rows) * len(replay), "sampled_runs": replay})
    if len(records) != len(EXPOSED_NAMES):
        raise ValueError("V3 report must contain both declared exposed sources")
    return {"stream": "original_v3_global_rng_separate_from_nested_curve", "cases": records,
            "all_original_bad_query_results_reproduced": True, "elapsed_seconds": perf_counter() - started}


def _compact_arm(arm: dict[str, Any]) -> dict[str, Any]:
    rows = {}
    for name, row in arm["queries"].items():
        active = row["all_active_states"]
        rows[name] = {
            "root_action": row["root_action"], "root_action_optimal": row["root_action_in_exact_optimal_set"],
            "root_regret": row["exact_lifted_objective_regret"],
            "true_root_metrics": row["exact_lifted_root_metrics"], "predicted_root_metrics": row["predicted_root_metrics"],
            "active_states": active["state_count"], "optimal_full_policy_states": active["optimal_full_policy_count"],
            "optimal_action_states": active["exact_optimal_action_count"],
            "maximum_state_regret": active["maximum_exact_lifted_objective_regret"],
            "mean_state_regret": active["mean_exact_lifted_objective_regret"],
            "maximum_state_prediction_errors": active["maximum_prediction_absolute_errors"],
        }
    return {"inventory": arm["inventory"], "queries": rows,
            "all_state_required_switches": arm["all_state_required_switches"],
            "root_required_switches": arm["root_required_switches"],
            "full_query_workload": arm["measured_cumulative_workloads"][-1]}


def _summarize_curve(records: Sequence[dict[str, Any]], budgets: Sequence[int]) -> dict[str, Any]:
    result = {}
    for split in ("ALL", "EXPOSED_SAMPLING_DIAGNOSIS", "NEW_DEVELOPMENT"):
        selected = [record for record in records if record["status"] == "COMPLETE" and (split == "ALL" or record["case"]["split"] == split)]
        doses = {}
        for budget in budgets:
            doses[str(budget)] = {}
            for name in ("full_state_empirical", "exact_empirical_quotient"):
                runs = [dose["arms"][name] for record in selected for sampled in record["sampled_runs"]
                        for dose in sampled["doses"] if dose["samples_per_row"] == budget]
                rows = [row for run in runs for row in run["queries"].values()]
                if not rows:
                    continue
                doses[str(budget)][name] = {
                    "source_count": len(selected), "case_seed_count": len(runs), "root_query_count": len(rows),
                    "root_optimal_full_policy_count": sum(row["root_regret"] <= NUMERIC_TOLERANCE for row in rows),
                    "state_query_count": sum(row["active_states"] for row in rows),
                    "all_state_optimal_full_policy_count": sum(row["optimal_full_policy_states"] for row in rows),
                    "maximum_root_regret": max(row["root_regret"] for row in rows),
                    "maximum_state_regret": max(row["maximum_state_regret"] for row in rows),
                    "maximum_failure_prediction_error": max(row["maximum_state_prediction_errors"]["failure"] for row in rows),
                    "required_strict_state_query_pairs": sum(run["all_state_required_switches"]["ALL"]["required_state_query_pair_count"] for run in runs),
                    "preserved_strict_state_query_pairs": sum(run["all_state_required_switches"]["ALL"]["preserved_state_query_pair_count"] for run in runs),
                    "mean_active_cells": math.fsum(run["inventory"]["active_cells"] for run in runs) / len(runs),
                    "mean_construction_seconds": math.fsum(run["inventory"]["construction_seconds"] for run in runs) / len(runs),
                    "mean_full_query_workload_seconds": math.fsum(run["full_query_workload"]["including_shared_closure_sample_build_plan_forecast_audit_seconds"] for run in runs) / len(runs),
                }
        result[split] = doses
    return result


def run_sampling_curve(*, cases: Sequence[RefinementCase] | None = None,
                       budgets: Sequence[int] = SAMPLE_BUDGETS, sample_seeds: Sequence[int] = SAMPLE_SEEDS,
                       max_nodes: int = 30_000,
                       progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    started_all = perf_counter()
    records, board_owners = [], defaultdict(set)
    for case in sampling_cases() if cases is None else cases:
        record: dict[str, Any] = {"case": asdict(case)}
        records.append(record)
        try:
            closure = build_development_closure(horizon=case.horizon, max_nodes=max_nodes, boards={case.name: case.board})
        except ValueError as error:
            if "complete closure exceeds max_nodes=" not in str(error):
                raise
            record.update(status="CLOSURE_BUDGET_EXCEEDED", error=str(error))
            continue
        for board in closure.boards.values():
            board_owners[board].add(case.name)
        reference_started = perf_counter()
        exact = compile_full_state(closure.model)
        references = _reference(closure, exact, QUERIES)
        reference_seconds = perf_counter() - reference_started
        record.update(status="COMPLETE", closure_counts=closure.counts, closure_seconds=closure.elapsed_seconds,
                      privileged_reference_build_plan_label_seconds=reference_seconds, sampled_runs=[])
        for seed in sample_seeds:
            sampled = {"sample_seed": seed, "doses": []}
            record["sampled_runs"].append(sampled)
            for budget, empirical, sampling in nested_sample_curve(closure.model, budgets, seed):
                dose = {"samples_per_row": budget, "sampling": sampling, "arms": {}}
                sampled["doses"].append(dose)
                private = {}
                for name, builder in (("full_state_empirical", lambda: compile_full_state(empirical)),
                                      ("exact_empirical_quotient", lambda: build_quotient(empirical))):
                    compiled, inventory, _ = _fit(builder, closure)
                    arm, private[name] = _arm(compiled, inventory, closure, QUERIES, references, QUERY_GROUPS,
                        sampling_seconds=sampling["cumulative_sampling_seconds_including_prior_stage_materialization"], privileged=False)
                    dose["arms"][name] = _compact_arm(arm)
                differences = [abs(private["full_state_empirical"][query]["actual"][state][component]
                                   - private["exact_empirical_quotient"][query]["actual"][state][component])
                               for query in QUERIES for state in closure.model.layers for component in COMPONENTS]
                dose["maximum_true_component_difference_between_matched_arms"] = max(differences)
                if progress:
                    progress({"stage": "sampling_curve", "case": case.name, "seed": seed,
                              "samples_per_row": budget, "status": "COMPLETE"})
    return {
        "schema": "controlled_predictive_sampling_curve_v4", "status": "DEVELOPMENT_COMPLETE" if all(record["status"] == "COMPLETE" for record in records) else "DEVELOPMENT_WITH_BUDGET_EXCLUSIONS",
        "settings": {"budgets": tuple(budgets), "sample_seeds": tuple(sample_seeds), "max_nodes": max_nodes,
                     "queries": {name: asdict(query) for name, query in QUERIES.items()}, "query_groups": QUERY_GROUPS},
        "cases": records, "summary_by_split": _summarize_curve(records, budgets),
        "actual_unique_curve_draws": sum(sampled["doses"][-1]["sampling"]["cumulative_draws"] for record in records if record["status"] == "COMPLETE" for sampled in record["sampled_runs"]),
        "within_curve_shared_raw_board_count": sum(len(owners) > 1 for owners in board_owners.values()),
        "elapsed_seconds": perf_counter() - started_all,
        "scientific_gate": "NOT_A_CONFIRMATORY_GATE", "deferred_v2_cohort_executed": False,
        "limitations": ["Four new public generated sources are development data; each source is refitted.",
            "Full support closure and exact policy audits are privileged reference operations.",
            "The zero-tolerance quotient and full-state builder share empirical rows; neither receives true probabilities.",
            "Same source, sampling repeats, query objectives and nested doses are dependent observations.",
            "All-state audits are unweighted coverage tests; root metrics use exact reach probabilities.",
            "Timing includes staged materialization; one timing is not a speed benchmark.",
            "No sample dose is selected as a new Gate or as a guarantee of true risk correctness."],
    }
