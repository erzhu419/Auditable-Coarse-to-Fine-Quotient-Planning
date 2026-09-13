"""Partial target acquisition with complete fixed-policy audits after freezing.

Each method owns its row provider. Full target support is acquired only after
all partial checkpoints freeze, then used for full-row benchmarks and truth.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
import math
import random
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from .controlled_predictive_2048_v1 import DevelopmentClosure, build_development_closure
from .controlled_predictive_cohort_v7 import V7Case
from .controlled_predictive_cohort_v12 import build_cohort_roster_v12, cases_v12
from .controlled_predictive_comparison_v3 import (
    COMPARISON_QUERIES, PROBE_QUERIES, SAMPLE_SEEDS, COMPONENTS,
    NUMERIC_TOLERANCE, _reference, _switches, _evaluate, _fit,
)
from .controlled_predictive_comparison_v8 import _validate_scenarios
from .controlled_predictive_encoder_io_v7 import artifact_inventory, freeze_artifact_payload
from .controlled_predictive_encoder_v7 import TrainingModel
from .controlled_predictive_partial_v12 import RowSampleProvider, row_seed, run_partial
from .controlled_predictive_source_prior_v12 import fit_source_prior
from .controlled_predictive_quotient_v1 import (
    FiniteModel, Outcome, Query, _evaluate_policy, build_quotient, compile_full_state, plan,
)

PARTIAL_ARMS = ("bfs", "query_interval", "source_priority", "shuffled_source_priority")
FULL_ARMS = ("full_state_empirical", "exact_empirical_quotient")
SOURCE_ARMS = PARTIAL_ARMS[2:]
ROW_BUDGETS = (8, 32, 128)
SAMPLES_PER_ROW = 256


def _key(closure: DevelopmentClosure, state: int) -> tuple[int, tuple[int, ...]]:
    return closure.model.layers[state], closure.boards[state]


def _acquire_complete(closure: DevelopmentClosure, seed: int, samples_per_row: int
                      ) -> tuple[FiniteModel, dict[str, Any]]:
    """Sample the already-paid complete support with the same row-key stream."""
    started = perf_counter()
    index = {_key(closure, state): state for state in closure.model.layers}
    rows = {}
    work: Counter = Counter()
    for state, action in sorted(closure.model.rows):
        support = closure.model.rows[state, action]
        sampled = random.Random(row_seed(seed, _key(closure, state), action)).choices(
            support, weights=[outcome.probability for outcome in support], k=samples_per_row)
        counts = Counter((_key(closure, outcome.next_state), outcome.reward) for outcome in sampled)
        rows[state, action] = tuple(Outcome(count / samples_per_row, index[next_key], reward)
            for (next_key, reward), count in sorted(counts.items()))
        work.update(full_rows_sampled=1, physical_draws=samples_per_row,
            support_entries_read_from_complete_closure=len(support),
            sampled_successor_entries_returned=len(rows[state, action]))
    empirical = FiniteModel(dict(closure.model.layers), dict(closure.model.terminal), rows, closure.model.roots)
    return empirical, {"acquisition_and_model_assembly_seconds": perf_counter() - started,
        "observation_work_counts": dict(work), "reused_complete_support": True,
        "additional_support_enumeration_calls": 0,
        "actual_rows_acquired": len(rows), "physical_sample_draws": len(rows) * samples_per_row,
        "all_support_states_retained": True, "observations_shared_with_partial": False}


def _checkpoint_record(checkpoint: Any, source_setup: float, scenario_case_count: int) -> dict[str, Any]:
    return {"row_budget": checkpoint.budget, "actual_rows_acquired": len(checkpoint.known_rows),
        "discovered_state_records": len(checkpoint.profiles), "stop_reason": checkpoint.stop_reason,
        "root_intervals": {name: asdict(value) for name, value in checkpoint.root_intervals.items()},
        "work_counts": dict(checkpoint.work_counts), "provider_work_counts": dict(checkpoint.provider_counts),
        "source_priority_diagnostics": dict(checkpoint.prior_diagnostics),
        "construction_seconds": checkpoint.elapsed_seconds, "provider_seconds_included": checkpoint.provider_seconds,
        "checkpoint_copy_seconds_included": checkpoint.checkpoint_copy_seconds,
        "source_priority_seconds_included": checkpoint.prior_seconds,
        "amortized_source_setup_seconds": source_setup / scenario_case_count,
        "standalone_source_setup_seconds": source_setup,
        "construction_plus_amortized_source_setup_seconds": checkpoint.elapsed_seconds + source_setup / scenario_case_count,
        "construction_plus_standalone_source_setup_seconds": checkpoint.elapsed_seconds + source_setup,
        "status": "POLICIES_FROZEN", "queries": {}}


def _occupancy(closure: DevelopmentClosure, policy: Mapping[int, str], fallback: Mapping[int, bool],
               unobserved: Mapping[int, bool], fallback_swipes: Mapping[int, int]) -> dict[str, Any]:
    """Root reach and expected calls under exact dynamics, used after freezing."""
    root = closure.model.roots[0]
    mass = {root: 1.0}
    no_fallback = {root: 1.0}
    no_unobserved = {root: 1.0}
    fallback_reach = unobserved_reach = 0.0
    expected_fallback = expected_unobserved = expected_swipes = 0.0
    for state in sorted(closure.model.layers, key=lambda s: (-closure.model.layers[s], s)):
        if closure.model.terminal[state] != "ACTIVE":
            continue
        p = mass.get(state, 0.0)
        f, u = fallback[state], unobserved[state]
        expected_fallback += p * f
        expected_unobserved += p * u
        expected_swipes += p * fallback_swipes[state]
        if f:
            fallback_reach += no_fallback.get(state, 0.0)
        if u:
            unobserved_reach += no_unobserved.get(state, 0.0)
        for outcome in closure.model.rows[state, policy[state]]:
            target, weight = outcome.next_state, outcome.probability
            mass[target] = mass.get(target, 0.0) + p * weight
            if not f:
                no_fallback[target] = no_fallback.get(target, 0.0) + no_fallback.get(state, 0.0) * weight
            if not u:
                no_unobserved[target] = no_unobserved.get(target, 0.0) + no_unobserved.get(state, 0.0) * weight
    return {"probability_reaching_unrecorded_state_fallback": fallback_reach,
        "expected_unrecorded_state_fallback_calls": expected_fallback,
        "expected_fallback_deterministic_swipes": expected_swipes,
        "probability_executing_any_unobserved_action": unobserved_reach,
        "expected_unobserved_action_executions": expected_unobserved,
        "online_wall_clock_measured": False,
        "scope": "Exact root occupancy of the frozen policy; no extra samples or feedback into construction."}


def _audit_partial(checkpoint: Any, closure: DevelopmentClosure, queries: Mapping[str, Query],
                   references: Mapping[str, Any], full_private: Mapping[str, Any]) -> dict[str, Any]:
    active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
    root = closure.model.roots[0]
    rows, policies = {}, {}
    for name, query in queries.items():
        frozen = checkpoint.frozen_policy
        started = perf_counter()
        before_work = Counter(frozen.work_counts)
        before_fallback_seconds = frozen.fallback_seconds
        policy, fallback, unobserved, fallback_swipes = {}, {}, {}, {}
        for state in active:
            key = _key(closure, state)
            unseen = key not in frozen.policies[name]
            before_swipes = frozen.work_counts.get("deterministic_swipe_calls", 0)
            action = frozen.action(key, name)
            policy[state] = action
            fallback[state] = unseen
            unobserved[state] = (key, action) not in checkpoint.known_rows
            fallback_swipes[state] = frozen.work_counts.get("deterministic_swipe_calls", 0) - before_swipes if unseen else 0
        lookup_seconds = perf_counter() - started
        lookup_work = {key: value - before_work.get(key, 0) for key, value in frozen.work_counts.items()}
        fallback_seconds = frozen.fallback_seconds - before_fallback_seconds
        started = perf_counter()
        actual = _evaluate_policy(closure.model.terminal, closure.model.rows,
            tuple(closure.model.layers), policy, query)
        audit_seconds = perf_counter() - started
        started = perf_counter()
        occupancy = _occupancy(closure, policy, fallback, unobserved, fallback_swipes)
        occupancy_seconds = perf_counter() - started
        regrets = {state: references[name]["values"][state] - actual.root_metrics[state]["value"] for state in active}
        full = full_private[name]
        extra = {state: full["actual"][state]["value"] - actual.root_metrics[state]["value"] for state in active}
        worst = max(active, key=lambda state: regrets[state])
        worst_extra = max(active, key=lambda state: extra[state])
        def witness(state: int) -> dict[str, Any]:
            return {"state": state, "board": closure.boards[state], "remaining_horizon": closure.model.layers[state],
                "action": policy[state], "unrecorded_state_fallback": fallback[state],
                "selected_action_was_unobserved": unobserved[state],
                "actual_metrics": actual.root_metrics[state], "exact_optimal_actions": references[name]["optimal_actions"][state],
                "exact_optimal_value": references[name]["values"][state], "regret": regrets[state],
                "full_state_action": full["policy"][state], "full_state_actual_metrics": full["actual"][state],
                "extra_regret_over_full_state": extra[state]}
        rows[name] = {"root_action": policy[root],
            "root_action_in_exact_optimal_set": policy[root] in references[name]["optimal_actions"][root],
            "exact_lifted_root_metrics": actual.root_metrics[root], "exact_lifted_objective_regret": regrets[root],
            "root_extra_regret_over_full_state": extra[root], "root_execution": occupancy,
            "all_active_states": {"state_count": len(active),
                "exact_optimal_action_count": sum(policy[state] in references[name]["optimal_actions"][state] for state in active),
                "optimal_full_policy_count": sum(value <= NUMERIC_TOLERANCE for value in regrets.values()),
                "mean_exact_lifted_objective_regret": math.fsum(regrets.values()) / len(active),
                "maximum_exact_lifted_objective_regret": max(regrets.values()),
                "maximum_extra_regret_over_full_state": max(extra.values()),
                "minimum_extra_regret_over_full_state": min(extra.values()),
                "mean_extra_regret_over_full_state": math.fsum(extra.values()) / len(active),
                "states_worse_than_full_state": sum(value > NUMERIC_TOLERANCE for value in extra.values()),
                "states_better_than_full_state": sum(value < -NUMERIC_TOLERANCE for value in extra.values()),
                "action_disagreement_with_full_state_count": sum(policy[state] != full["policy"][state] for state in active),
                "unrecorded_state_fallback_count": sum(fallback.values()),
                "recorded_state_selected_unobserved_action_count": sum(unobserved[state] and not fallback[state] for state in active),
                "maximum_actual_component_difference_from_full_state": {component: max(abs(
                    actual.root_metrics[state][component] - full["actual"][state][component]) for state in active)
                    for component in COMPONENTS},
                "worst_regret_witness": witness(worst), "worst_added_loss_witness": witness(worst_extra)},
            "audit_policy_lookup_and_fallback_seconds": lookup_seconds,
            "audit_fallback_seconds_included_in_lookup": fallback_seconds,
            "audit_policy_lookup_work_counts": lookup_work,
            "all_state_ground_audit_seconds": audit_seconds, "all_state_ground_audit_counts": actual.counts,
            "root_occupancy_audit_seconds": occupancy_seconds}
        policies[name] = policy
    return {"queries": rows, "all_state_required_switches": _switches(references, active, {"ALL": tuple(queries)}, policies),
        "root_required_switches": _switches(references, (root,), {"ALL": tuple(queries)}, policies), "status": "AUDITED"}


def _full_arms(empirical: FiniteModel, closure: DevelopmentClosure, queries: Mapping[str, Query]) -> dict[str, Any]:
    frozen = {}
    for arm, builder in ((FULL_ARMS[0], compile_full_state), (FULL_ARMS[1], build_quotient)):
        compiled, inventory, _ = _fit(lambda: builder(empirical), closure)
        plans = {}
        for name, query in queries.items():
            started = perf_counter()
            plans[name] = plan(compiled, query), perf_counter() - started
        frozen[arm] = (compiled, inventory, plans)
    return frozen


def _audit_full(frozen: Mapping[str, Any], closure: DevelopmentClosure, queries: Mapping[str, Query],
                references: Mapping[str, Any], acquisition: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    arms, private = {}, {}
    active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
    for arm, (compiled, inventory, plans) in frozen.items():
        rows, internals = {}, {}
        for name, query in queries.items():
            rows[name], internals[name] = _evaluate(compiled, closure, query, references[name], active, plans[name])
        planning = math.fsum(row["planning_seconds"] for row in rows.values())
        arms[arm] = {"inventory": inventory, "queries": rows,
            "all_state_required_switches": _switches(references, active, {"ALL": tuple(queries)}, {name: row["policy"] for name, row in internals.items()}),
            "acquisition_seconds_attributed": acquisition["acquisition_and_model_assembly_seconds"],
            "complete_target_closure_seconds_attributed": closure.elapsed_seconds,
            "construction_plus_all_query_planning_seconds": inventory["construction_seconds"] + planning,
            "complete_target_acquisition_construction_and_planning_seconds": closure.elapsed_seconds + acquisition["acquisition_and_model_assembly_seconds"] + inventory["construction_seconds"] + planning,
            "actual_rows_acquired": acquisition["actual_rows_acquired"], "budget_scope": "ALL_ROWS_COST_AND_QUALITY_BENCHMARK"}
        private[arm] = internals
    return arms, private


def _summarize_items(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not items:
        return {"run_count": 0}
    rows = [row for item in items for row in item["queries"].values()]
    result = {"run_count": len(items), "query_count": len(rows),
        "root_optimal_first_action_count": sum(row["root_action_in_exact_optimal_set"] for row in rows),
        "root_optimal_full_policy_count": sum(row["exact_lifted_objective_regret"] <= NUMERIC_TOLERANCE for row in rows),
        "state_query_count": sum(row["all_active_states"]["state_count"] for row in rows),
        "all_state_optimal_full_policy_count": sum(row["all_active_states"]["optimal_full_policy_count"] for row in rows),
        "maximum_root_regret": max(row["exact_lifted_objective_regret"] for row in rows),
        "maximum_all_state_regret": max(row["all_active_states"]["maximum_exact_lifted_objective_regret"] for row in rows),
        "mean_rows_acquired": math.fsum(item["actual_rows_acquired"] for item in items) / len(items),
        "required_state_query_pairs": sum(item["all_state_required_switches"]["ALL"]["required_state_query_pair_count"] for item in items),
        "preserved_state_query_pairs": sum(item["all_state_required_switches"]["ALL"]["preserved_state_query_pair_count"] for item in items)}
    if "row_budget" in items[0]:
        result.update(stop_reason_counts=dict(Counter(item["stop_reason"] for item in items)),
            empirical_root_interval_closed_query_count=sum(
                interval["upper"] - interval["lower"] <= NUMERIC_TOLERANCE for item in items for interval in item["root_intervals"].values()),
            mean_construction_seconds=math.fsum(item["construction_seconds"] for item in items) / len(items),
            mean_construction_plus_amortized_source_seconds=math.fsum(item["construction_plus_amortized_source_setup_seconds"] for item in items) / len(items),
            mean_construction_plus_standalone_source_seconds=math.fsum(item["construction_plus_standalone_source_setup_seconds"] for item in items) / len(items),
            mean_expected_root_fallback_calls=math.fsum(row["root_execution"]["expected_unrecorded_state_fallback_calls"] for row in rows) / len(rows),
            mean_root_fallback_reach_probability=math.fsum(row["root_execution"]["probability_reaching_unrecorded_state_fallback"] for row in rows) / len(rows),
            mean_expected_root_unobserved_actions=math.fsum(row["root_execution"]["expected_unobserved_action_executions"] for row in rows) / len(rows),
            mean_expected_root_fallback_swipes=math.fsum(row["root_execution"]["expected_fallback_deterministic_swipes"] for row in rows) / len(rows),
            maximum_extra_regret_over_full_state=max(row["all_active_states"]["maximum_extra_regret_over_full_state"] for row in rows))
    else:
        result["mean_complete_target_acquisition_construction_and_planning_seconds"] = math.fsum(item["complete_target_acquisition_construction_and_planning_seconds"] for item in items) / len(items)
    return result


def _summarize(records: Sequence[Mapping[str, Any]], budgets: Sequence[int]) -> dict[str, Any]:
    runs = [run for record in records for run in record["sampled_runs"] if run["status"] == "AUDITED"]
    return {"declared_case_count": len(records), "case_status_counts": dict(Counter(record["status"] for record in records)),
        "retained_run_status_counts": dict(Counter(run["status"] for record in records for run in record["sampled_runs"])),
        "audited_case_seed_run_count": len(runs),
        "full_baselines": {arm: _summarize_items([run["full_baselines"][arm] for run in runs]) for arm in FULL_ARMS},
        "partial_by_budget": {str(budget): {arm: _summarize_items([checkpoint for run in runs
            for checkpoint in run["partial_arms"][arm] if checkpoint["row_budget"] == budget]) for arm in PARTIAL_ARMS} for budget in budgets}}


def run_comparison_v12(*, cases: Sequence[V7Case] | None = None,
                       cohort_roster: Mapping[str, Any] | None = None,
                       samples_per_row: int = SAMPLES_PER_ROW,
                       sample_seeds: Sequence[int] = SAMPLE_SEEDS,
                       row_budgets: Sequence[int] = ROW_BUDGETS,
                       queries: Mapping[str, Query] | None = None,
                       max_nodes: int = 30_000,
                       progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    roster = build_cohort_roster_v12() if cohort_roster is None else cohort_roster
    declared = tuple(cases_v12() if cases is None else cases)
    scenarios = tuple(roster["scenarios"])
    queries = dict({**COMPARISON_QUERIES, **PROBE_QUERIES} if queries is None else queries)
    budgets = tuple(row_budgets)
    if (not declared or not queries or not sample_seeds or samples_per_row < 1 or not budgets
            or budgets != tuple(sorted(set(budgets))) or budgets[0] < 1
            or len(set(sample_seeds)) != len(sample_seeds)):
        raise ValueError("nonempty cases/queries/seeds and strictly increasing positive row budgets required")
    _validate_scenarios(declared, scenarios)
    started_all = perf_counter()
    case_by_name = {case.name: case for case in declared}
    union_sources = {name for scenario in scenarios for name in scenario["source_case_names"]}
    closures, closure_records = {}, {}
    def get_closure(name: str, scope: str) -> DevelopmentClosure | None:
        if name in closure_records:
            return closures.get(name)
        case = case_by_name[name]
        started = perf_counter()
        record = {"case_name": name, "first_acquisition_scope": scope}
        try:
            closure = build_development_closure(horizon=case.horizon, max_nodes=max_nodes,
                boards={name: tuple(case.board)})
        except ValueError as error:
            if "complete closure exceeds max_nodes=" not in str(error):
                raise
            record.update(status="CLOSURE_BUDGET_EXCEEDED", reason=str(error),
                actual_closure_seconds=perf_counter() - started)
        else:
            closures[name] = closure
            record.update(status="CLOSURE_COMPLETE", actual_closure_seconds=closure.elapsed_seconds,
                coverage=closure.counts)
        closure_records[name] = record
        if progress:
            progress({"case": name, "status": record["status"], "scope": scope})
        return closures.get(name)
    for case in declared:
        if case.name in union_sources:
            get_closure(case.name, "DECLARED_SOURCE_PREPARATION")
    scenario_records = []
    for scenario in scenarios:
        scenario_records.append({"scenario": dict(scenario), "source_fits": [],
            "source_closure_failure": any(name not in closures for name in scenario["source_case_names"]),
            "cases": [{"case": {**asdict(case_by_name[name]), "split": scenario["case_splits"][name]},
                "status": "NOT_RUN", "sampled_runs": []} for name in scenario["evaluation_case_names"]]})
    source_acquisitions, example = [], None
    for seed_index, seed in enumerate(sample_seeds):
        source_models, source_costs = {}, {}
        for case in declared:
            if case.name not in union_sources or case.name not in closures:
                continue
            empirical, acquisition = _acquire_complete(closures[case.name], seed, samples_per_row)
            source_models[case.name] = TrainingModel(case.name, empirical, closures[case.name].boards)
            source_costs[case.name] = acquisition
            source_acquisitions.append({"case_name": case.name, "sample_seed": seed, **acquisition})
        fitted_by_scenario = {}
        for scenario_record in scenario_records:
            if scenario_record["source_closure_failure"]:
                for record in scenario_record["cases"]:
                    record["status"] = "NOT_RUN_SOURCE_CLOSURE_INCOMPLETE"
                continue
            scenario = scenario_record["scenario"]
            names = scenario["source_case_names"]
            started = perf_counter()
            fitted = fit_source_prior(tuple(source_models[name] for name in names), queries)
            setup_build_seconds = perf_counter() - started
            fitted_by_scenario[scenario["name"]] = fitted
            source_closure_seconds = math.fsum(closures[name].elapsed_seconds for name in names)
            source_acquisition_seconds = math.fsum(source_costs[name]["acquisition_and_model_assembly_seconds"] for name in names)
            started = perf_counter()
            inventory = artifact_inventory(freeze_artifact_payload(fitted.encoder, fitted.compiled, fitted.code_to_cell))
            encoder = fitted.encoder.to_payload()
            q_table = {name: [[code, sorted(values.items())] for code, values in sorted(table.items())]
                       for name, table in fitted.q_by_query.items()}
            inventory_seconds = perf_counter() - started
            scenario_record["source_fits"].append({"sample_seed": seed, "source_case_names": names,
                "source_closure_seconds_attributed": source_closure_seconds,
                "source_acquisition_seconds_attributed": source_acquisition_seconds,
                "source_fit_compile_query_seconds": setup_build_seconds,
                "total_source_setup_seconds_attributed": source_closure_seconds + source_acquisition_seconds + setup_build_seconds,
                "source_observations_reused_from_declared_source_bank": True,
                "amortization_declared_case_count": len(scenario["evaluation_case_names"]),
                "diagnostics": fitted.diagnostics, "encoder": encoder, "source_q_table": q_table,
                "portable_encoder_and_source_model_bytes": inventory,
                "source_inventory_serialization_seconds": inventory_seconds})
            if progress:
                progress({"scenario": scenario["name"], "sample_seed": seed, "status": "SOURCE_PRIOR_FROZEN"})
        for scenario_index, scenario_record in enumerate(scenario_records):
            if scenario_record["source_closure_failure"]:
                continue
            scenario = scenario_record["scenario"]
            fitted = fitted_by_scenario[scenario["name"]]
            fit_record = scenario_record["source_fits"][-1]
            for case_index, record in enumerate(scenario_record["cases"]):
                case = case_by_name[record["case"]["name"]]
                root_key = (case.horizon, tuple(case.board))
                frozen_by_arm, partial_records, trajectories = {}, {}, {}
                offset = (seed_index + scenario_index + case_index) % len(PARTIAL_ARMS)
                order = PARTIAL_ARMS[offset:] + PARTIAL_ARMS[:offset]
                for arm in order:
                    provider = RowSampleProvider(seed=seed, samples_per_row=samples_per_row)
                    prior = fitted.make_priority(shuffled=arm == "shuffled_source_priority") if arm in SOURCE_ARMS else None
                    started = perf_counter()
                    checkpoints = run_partial(root_key, provider, queries, budgets=budgets, mode=arm, prior=prior)
                    elapsed = perf_counter() - started
                    frozen_by_arm[arm] = checkpoints
                    source_setup = fit_record["total_source_setup_seconds_attributed"] if arm in SOURCE_ARMS else 0.0
                    partial_records[arm] = [_checkpoint_record(cp, source_setup, len(scenario["evaluation_case_names"])) for cp in checkpoints]
                    trajectories[arm] = {"actual_trajectory_seconds": elapsed,
                        "actual_rows_acquired": len(checkpoints[-1].known_rows),
                        "physical_sample_draws": len(checkpoints[-1].known_rows) * samples_per_row,
                        "provider_seconds": provider.provider_seconds, "provider_work_counts": dict(provider.work_counts),
                        "source_priority_used": prior is not None, "independent_provider": True,
                        "checkpoints_are_one_nested_trajectory": True}
                    if progress:
                        progress({"scenario": scenario["name"], "case": case.name, "sample_seed": seed,
                            "arm": arm, "status": "PARTIAL_CHECKPOINTS_FROZEN", "rows": len(checkpoints[-1].known_rows)})
                run = {"sample_seed": seed, "status": "PARTIAL_POLICIES_FROZEN", "partial_arm_order": order,
                    "partial_arms": partial_records, "partial_trajectories": trajectories,
                    "current_case_is_source_training_item": case.name in scenario["source_case_names"],
                    "all_partial_checkpoints_frozen_before_target_full_model": True,
                    "complete_source_model_was_not_passed_to_partial": True}
                record["sampled_runs"].append(run)
                closure = get_closure(case.name, "AFTER_ALL_PARTIAL_CHECKPOINTS_FROZEN")
                if closure is None:
                    run["status"] = record["status"] = "AUDIT_CLOSURE_BUDGET_EXCEEDED"
                    continue
                empirical, full_acquisition = _acquire_complete(closure, seed, samples_per_row)
                full_frozen = _full_arms(empirical, closure, queries)
                started = perf_counter()
                exact = compile_full_state(closure.model)
                exact_compile_seconds = perf_counter() - started
                references = _reference(closure, exact, queries)
                full_arms, full_private = _audit_full(full_frozen, closure, queries, references, full_acquisition)
                run.update(full_target_acquisition=full_acquisition, full_baselines=full_arms,
                    all_full_benchmark_plans_frozen_before_truth=True,
                    exact_reference_cost={"compile_seconds": exact_compile_seconds,
                        "planning_seconds": math.fsum(value["planning_seconds"] for value in references.values()),
                        "labeling_seconds": math.fsum(value["all_state_action_labeling_seconds"] for value in references.values())})
                for arm in PARTIAL_ARMS:
                    for cp, output in zip(frozen_by_arm[arm], partial_records[arm]):
                        output.update(_audit_partial(cp, closure, queries, references, full_private["full_state_empirical"]))
                if scenario["name"] == "PRIMARY_V7_SPLIT" and case.name == "v6_spawn_edge_rescue_2" and seed == 832101:
                    from .controlled_predictive_partial_io_v12 import freeze_policy_payload
                    cp = next(cp for cp in frozen_by_arm["source_priority"] if cp.budget == 128)
                    started = perf_counter()
                    metadata = {"scenario": scenario["name"], "case_name": case.name, "sample_seed": seed,
                        "arm": "source_priority", "row_budget": cp.budget}
                    example = {**metadata, "artifact": freeze_policy_payload(cp, queries, root_key, metadata=metadata),
                        "expected_root_actions": {name: cp.frozen_policy.action(root_key, name) for name in queries},
                        "root_intervals": {name: asdict(value) for name, value in cp.root_intervals.items()},
                        "serialization_seconds": perf_counter() - started}
                run["status"] = record["status"] = "AUDITED"
                if progress:
                    progress({"scenario": scenario["name"], "case": case.name, "sample_seed": seed, "status": "CASE_AUDITED"})
    for scenario_record in scenario_records:
        records = scenario_record["cases"]
        scenario_record["summary_by_split"] = {split: _summarize(records if split == "ALL" else [record for record in records
            if record["case"]["split"] == split], budgets) for split in ("ALL", *sorted({record["case"]["split"] for record in records}))}
    all_runs = [run for scenario in scenario_records for record in scenario["cases"] for run in record["sampled_runs"]]
    audited = [run for run in all_runs if run["status"] == "AUDITED"]
    lofo_targets = [record for scenario in scenario_records if scenario["scenario"]["target_family"] is not None
        for record in scenario["cases"] if record["case"]["split"] == "FAMILY_HELD_OUT"]
    fits = [fit for scenario in scenario_records for fit in scenario["source_fits"]]
    trajectories = [trajectory for run in all_runs for trajectory in run["partial_trajectories"].values()]
    full_acquisitions = [run["full_target_acquisition"] for run in audited]
    partial_rows = [row for run in audited for checkpoints in run["partial_arms"].values() for cp in checkpoints for row in cp["queries"].values()]
    full_rows = [row for run in audited for arm in run["full_baselines"].values() for row in arm["queries"].values()]
    draws_by_scope = {"source": sum(item["physical_sample_draws"] for item in source_acquisitions),
        "partial": sum(item["physical_sample_draws"] for item in trajectories),
        "full_target_benchmarks": sum(item["physical_sample_draws"] for item in full_acquisitions)}
    return {"schema": "acfqp.controlled_predictive_partial_observation.v12",
        "status": "DEVELOPMENT_COMPLETE" if len(audited) == sum(len(s["evaluation_case_names"]) for s in scenarios) * len(sample_seeds)
            else "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES",
        "scientific_gate": "NOT_A_FORMAL_GATE", "case_count": len(declared), "scenario_count": len(scenarios),
        "completed_scenario_case_seed_runs": len(audited), "retained_partial_scenario_case_seed_runs": len(all_runs),
        "settings": {"samples_per_row": samples_per_row, "sample_seeds": list(sample_seeds),
            "row_budgets": budgets, "queries": {name: asdict(query) for name, query in queries.items()},
            "all_queries_participate_in_construction": True, "query_order": list(queries), "partial_arm_names": PARTIAL_ARMS,
            "full_benchmark_names": FULL_ARMS, "max_nodes": max_nodes},
        "cohort_roster": roster, "closure_records": list(closure_records.values()),
        "source_acquisitions": source_acquisitions, "scenarios": scenario_records,
        "lofo_target_aggregate": _summarize(lofo_targets, budgets), "partial_policy_example": example,
        "accounting": {"physical_sample_draws_by_scope": draws_by_scope,
            "actual_physical_sample_draws": sum(draws_by_scope.values()),
            "actual_complete_support_rows_enumerated_once_per_case": sum(row.get("coverage", {}).get("exact_transition_row_calls", 0) for row in closure_records.values()),
            "actual_complete_support_entries_enumerated_once_per_case": sum(row.get("coverage", {}).get("exact_outcomes_enumerated", 0) for row in closure_records.values()),
            "actual_partial_support_rows_enumerated": sum(row["provider_work_counts"].get("exact_transition_row_calls", 0) for row in trajectories),
            "actual_partial_support_entries_enumerated": sum(row["provider_work_counts"].get("support_entries_enumerated", 0) for row in trajectories),
            "source_fit_count": len(fits),
            "source_acquisition_count": len(source_acquisitions), "partial_trajectory_count": len(trajectories),
            "frozen_partial_checkpoint_count": sum(len(cps) for run in all_runs for cps in run["partial_arms"].values()),
            "full_target_acquisition_count": len(full_acquisitions),
            "full_benchmark_count": len(audited) * len(FULL_ARMS),
            "actual_closure_seconds_once_per_case": math.fsum(row["actual_closure_seconds"] for row in closure_records.values()),
            "actual_source_acquisition_seconds": math.fsum(row["acquisition_and_model_assembly_seconds"] for row in source_acquisitions),
            "actual_source_fit_compile_query_seconds": math.fsum(row["source_fit_compile_query_seconds"] for row in fits),
            "actual_partial_trajectory_seconds": math.fsum(row["actual_trajectory_seconds"] for row in trajectories),
            "actual_full_target_acquisition_seconds": math.fsum(row["acquisition_and_model_assembly_seconds"] for row in full_acquisitions),
            "actual_full_benchmark_construction_and_planning_seconds": math.fsum(arm["construction_plus_all_query_planning_seconds"] for run in audited for arm in run["full_baselines"].values()),
            "audit_partial_policy_lookup_and_fallback_seconds": math.fsum(row["audit_policy_lookup_and_fallback_seconds"] for row in partial_rows),
            "audit_partial_fallback_seconds_included_in_lookup": math.fsum(row["audit_fallback_seconds_included_in_lookup"] for row in partial_rows),
            "audit_partial_exact_policy_and_occupancy_seconds": math.fsum(row["all_state_ground_audit_seconds"] + row["root_occupancy_audit_seconds"] for row in partial_rows),
            "audit_full_forecast_and_exact_policy_seconds": math.fsum(row["all_cell_forecast_seconds"] + row["all_state_ground_audit_seconds"] for row in full_rows),
            "exact_reference_seconds": math.fsum(sum(run["exact_reference_cost"].values()) for run in audited),
            "inventory_serialization_seconds": math.fsum(fit["source_inventory_serialization_seconds"] for fit in fits) + math.fsum(arm["inventory"]["inventory_serialization_seconds"] for run in audited for arm in run["full_baselines"].values()),
            "source_cost_rule": "Full source closure, actual source observation acquisition, fit, pooling and ten-query prior preparation are attributed to both source methods, amortized over the declared scenario targets or charged in full standalone. Partial providers independently re-execute rows even on a source target; none of that repeated work is subtracted.",
            "physical_sharing_rule": "Source-bank acquisitions and per-scenario priors are physically reused; each partial method has a fresh provider. Each target full sampling reuses its paid complete support and is shared only by its two full benchmarks. Identical row streams re-executed by different providers are counted again. Complete closures are physically acquired once per original case and never passed to partial planners.",
            "checkpoint_rule": "Budgets are prefixes of one trajectory; physical totals use its last checkpoint and whole trajectory time, never the sum of nested prefixes.",
            "fallback_rule": "Audit enumerates every true active state and measures frozen-policy lookup/fallback separately. Root-occupancy expected calls/swipes are deployment work counts, not measured online latency; fallback collects no samples."},
        "limitations": ["All cases, source families and queries were already exposed; this is development evidence.",
            "Ten queries now participate in construction. The changed row stream prevents causal comparisons with V9-V11 quality.",
            "Full-row benchmarks use larger budgets. Partial interval bounds use empirical probabilities and are not statistical confidence intervals for true dynamics.",
            "Exact closure and optimal labels are used only after partial policies freeze; existing source closures remain unavailable to partial planners.",
            "Missing states use the declared greedy fallback, whose consequences and expected execution work remain in the reported policy.",
            "No outcome-based replacement, rerun or parameter selection occurs."],
        "all_declared_cases_retained": True, "u006_assurance_started": False,
        "deferred_v2_24_case_cohort_executed": False, "elapsed_seconds": perf_counter() - started_all}


__all__ = ("PARTIAL_ARMS", "FULL_ARMS", "run_comparison_v12")
