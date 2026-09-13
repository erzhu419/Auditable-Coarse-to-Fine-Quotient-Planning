"""Fixed-pilot, equal-budget allocation comparison on covered finite models.

Each arm uses an exact quotient of its own empirical kernel.  Query-dependent
allocation is the treatment; representation and logical observation budgets
are matched.  Ground-model labels are produced only after plans are frozen.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from itertools import combinations
import math
import random
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from .controlled_predictive_2048_v1 import DevelopmentClosure, build_development_closure
from .controlled_predictive_allocation_v5 import plan_allocations
from .controlled_predictive_comparison_v2 import COMPARISON_QUERIES, SAMPLE_SEEDS
from .controlled_predictive_comparison_v3 import (
    COMPONENTS, NUMERIC_TOLERANCE, PROBE_QUERIES, RefinementCase,
    _evaluate, _fit, _reference, _switches,
)
from .controlled_predictive_comparison_v4 import _compact_arm
from .controlled_predictive_quotient_v1 import (
    CompiledModel, FiniteModel, Outcome, Plan, Query, build_quotient,
    compile_full_state, plan,
)


PILOT_SAMPLES = 64
SAMPLE_BUDGETS = (256, 1024)
ARM_NAMES = ("UNIFORM", "DIRECTED")
RowKey = tuple[int, str]


class RowSampler:
    """Retained per-row streams, count sufficient statistics, and nested draws."""

    def __init__(self, exact: FiniteModel, seed: int):
        started = perf_counter()
        self.exact = exact
        self.streams = {key: random.Random(f"acfqp-v5:{seed}:{key[0]}:{key[1]}")
                        for key in sorted(exact.rows)}
        self.counts: dict[RowKey, Counter[tuple[int, float]]] = {
            key: Counter() for key in self.streams}
        self.row_totals = {key: 0 for key in self.streams}
        self.physical_draws = 0
        self.sampling_seconds = perf_counter() - started

    def fork(self) -> tuple[RowSampler, float]:
        started = perf_counter()
        branch = object.__new__(RowSampler)
        branch.exact = self.exact
        branch.streams = {}
        for key, rng in self.streams.items():
            copied = random.Random(0)
            copied.setstate(rng.getstate())
            branch.streams[key] = copied
        branch.counts = {key: Counter(counts) for key, counts in self.counts.items()}
        branch.row_totals = dict(self.row_totals)
        branch.physical_draws = 0  # The common pilot is copied, never redrawn.
        branch.sampling_seconds = self.sampling_seconds
        return branch, perf_counter() - started

    def advance(self, targets: Mapping[RowKey, int]) -> tuple[FiniteModel, dict[str, Any]]:
        if targets.keys() != self.row_totals.keys() or any(
                not isinstance(targets[key], int) or targets[key] < max(1, old)
                for key, old in self.row_totals.items()):
            raise ValueError("targets must cover every row and extend existing positive prefixes")
        started = perf_counter()
        rows, additional = {}, 0
        for key, rng in self.streams.items():
            row = self.exact.rows[key]
            increment = targets[key] - self.row_totals[key]
            draws = rng.choices(row, weights=[item.probability for item in row], k=increment)
            self.counts[key].update((item.next_state, item.reward) for item in draws)
            self.row_totals[key] = targets[key]
            additional += increment
            rows[key] = tuple(Outcome(count / targets[key], target, reward)
                for (target, reward), count in sorted(self.counts[key].items()))
        empirical = FiniteModel(dict(self.exact.layers), dict(self.exact.terminal), rows, self.exact.roots)
        elapsed = perf_counter() - started
        self.physical_draws += additional
        self.sampling_seconds += elapsed
        return empirical, {
            "incremental_physical_draws": additional,
            "branch_physical_draws_after_shared_pilot": self.physical_draws,
            "logical_draws_in_current_model": sum(targets.values()),
            "incremental_sampling_seconds": elapsed,
            "cumulative_sampling_seconds_including_pilot_and_prior_materialization": self.sampling_seconds,
        }


@dataclass
class FrozenArm:
    compiled: CompiledModel
    inventory: dict[str, Any]
    plans: dict[str, tuple[Plan, float]]
    full_state: CompiledModel
    full_plans: dict[str, tuple[Plan, float]]
    full_state_construction_seconds: float
    sampling: dict[str, Any]
    allocation_seconds: float
    fork_seconds: float
    row_counts: tuple[int, ...]


def _freeze_arm(empirical: FiniteModel, closure: DevelopmentClosure,
                queries: Mapping[str, Query], sampling: dict[str, Any],
                allocation_seconds: float, fork_seconds: float,
                counts: Mapping[RowKey, int]) -> FrozenArm:
    compiled, inventory, _ = _fit(lambda: build_quotient(empirical), closure)
    plans = {}
    for name, query in queries.items():
        started = perf_counter()
        solution = plan(compiled, query)
        plans[name] = solution, perf_counter() - started
    started = perf_counter()
    full_state = compile_full_state(empirical)
    full_construction = perf_counter() - started
    full_plans = {}
    for name, query in queries.items():
        started = perf_counter()
        solution = plan(full_state, query)
        full_plans[name] = solution, perf_counter() - started
    return FrozenArm(compiled, inventory, plans, full_state, full_plans,
                     full_construction, sampling, allocation_seconds, fork_seconds,
                     tuple(counts[key] for key in sorted(counts)))


def _audit_arm(frozen: FrozenArm, closure: DevelopmentClosure,
               queries: Mapping[str, Query], references: Mapping[str, Any],
               groups: Mapping[str, Sequence[str]]) -> tuple[dict[str, Any], dict[str, Any]]:
    active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
    rows, private, full_rows, full_private = {}, {}, {}, {}
    for name, query in queries.items():
        rows[name], private[name] = _evaluate(frozen.compiled, closure, query,
            references[name], active, frozen.plans[name])
        full_rows[name], full_private[name] = _evaluate(frozen.full_state, closure, query,
            references[name], active, frozen.full_plans[name])
    sampling_seconds = frozen.sampling["cumulative_sampling_seconds_including_pilot_and_prior_materialization"]
    workloads = []
    for count in sorted({1, len(groups["FIT_BANK"]), len(queries)}):
        prefix = list(rows.values())[:count]
        planning = math.fsum(row["planning_seconds"] for row in prefix)
        forecasting = math.fsum(row["all_cell_forecast_seconds"] for row in prefix)
        audit = math.fsum(row["all_state_ground_audit_seconds"] for row in prefix)
        build = frozen.inventory["construction_seconds"]
        online_work = sampling_seconds + frozen.allocation_seconds + build + planning
        workloads.append({
            "query_count": count, "query_names": list(queries)[:count],
            "shared_exact_closure_seconds": closure.elapsed_seconds,
            "shared_pilot_and_branch_sampling_seconds": sampling_seconds,
            "one_time_allocation_seconds_including_pilot_planning": frozen.allocation_seconds,
            "one_time_construction_seconds": build,
            "cumulative_planning_seconds": planning, "cumulative_forecast_seconds": forecasting,
            "cumulative_ground_audit_seconds": audit,
            "construction_plus_planning_seconds": build + planning,
            "sample_allocate_build_plan_seconds": online_work,
            "including_shared_closure_sample_allocate_build_plan_forecast_audit_seconds": (
                closure.elapsed_seconds + online_work + forecasting + audit),
            "experimental_branch_fork_seconds_excluded_from_single_arm_workload": frozen.fork_seconds,
        })
    root = closure.model.roots[0]
    equivalence = {}
    for name in queries:
        candidate, full = private[name], full_private[name]
        extra = {state: full["actual"][state]["value"] - candidate["actual"][state]["value"] for state in active}
        equivalence[name] = {
            "maximum_empirical_optimal_value_difference": max(abs(
                frozen.plans[name][0].values[frozen.compiled.state_to_cell[state]] -
                frozen.full_plans[name][0].values[frozen.full_state.state_to_cell[state]]) for state in active),
            "action_disagreement_count": sum(candidate["policy"][state] != full["policy"][state] for state in active),
            "root_extra_regret_over_full_state": extra[root],
            "maximum_all_state_extra_regret_over_full_state": max(extra.values()),
            "minimum_all_state_extra_regret_over_full_state": min(extra.values()),
            "states_with_extra_regret_over_full_state": sum(value > NUMERIC_TOLERANCE for value in extra.values()),
            "maximum_actual_component_differences": {component: max(abs(
                candidate["actual"][state][component] - full["actual"][state][component])
                for state in active) for component in COMPONENTS},
        }
    arm = _compact_arm({
        "inventory": frozen.inventory, "queries": rows, "refinement_diagnostics": None,
        "all_state_required_switches": _switches(references, active, groups,
            {name: row["policy"] for name, row in private.items()}),
        "root_required_switches": _switches(references, closure.model.roots, groups,
            {name: row["policy"] for name, row in private.items()}),
        "measured_cumulative_workloads": workloads, "model_build_count": 1,
        "query_count_using_same_compiled_model": len(queries),
    })
    arm.update(
        row_sample_counts_in_declared_row_order=frozen.row_counts,
        sampling=frozen.sampling,
        same_sample_full_state_comparator={
            "purpose": "Auxiliary check for empirical quotient and ground-policy equivalence; not an additional sampling arm.",
            "queries": equivalence,
            "separate_validation_seconds": frozen.full_state_construction_seconds + math.fsum(
                row["planning_seconds"] + row["all_cell_forecast_seconds"] + row["all_state_ground_audit_seconds"]
                for row in full_rows.values()),
        },
    )
    return arm, private


def _matched_allocations(private: Mapping[str, Any], active: Sequence[int], root: int,
                         queries: Mapping[str, Query]) -> dict[str, Any]:
    result = {}
    for name in queries:
        uniform, directed = private["UNIFORM"][name], private["DIRECTED"][name]
        gain = {state: directed["actual"][state]["value"] - uniform["actual"][state]["value"] for state in active}
        result[name] = {
            "root_directed_value_gain_over_uniform": gain[root],
            "mean_all_state_directed_value_gain_over_uniform": math.fsum(gain.values()) / len(active),
            "minimum_all_state_directed_value_gain_over_uniform": min(gain.values()),
            "maximum_all_state_directed_value_gain_over_uniform": max(gain.values()),
            "improved_state_count": sum(value > NUMERIC_TOLERANCE for value in gain.values()),
            "worsened_state_count": sum(value < -NUMERIC_TOLERANCE for value in gain.values()),
            "tied_state_count": sum(abs(value) <= NUMERIC_TOLERANCE for value in gain.values()),
            "root_directed_minus_uniform_failure_probability": directed["actual"][root]["failure"] - uniform["actual"][root]["failure"],
        }
    return result


def pilot_ranking_audit(pair_rows: Sequence[Mapping[str, Any]], closure: DevelopmentClosure,
                        references: Mapping[str, Any], queries: Mapping[str, Query]) -> dict[str, Any]:
    """Ground labels classify the frozen pilot diagnostic, never modify sampling."""
    pair_confusion = Counter()
    decisions: dict[tuple[str, int], dict[str, bool]] = {}
    witnesses = []
    for row in pair_rows:
        name, state = row["query"], row["state"]
        query, values = queries[name], references[name]["values"]
        best, competitor = row["best_action"], row["competitor_action"]
        def q_value(action: str) -> float:
            return math.fsum(outcome.probability * (query.reward_weight * outcome.reward + values[outcome.next_state])
                             for outcome in closure.model.rows[state, action])
        true_competitor_advantage = q_value(competitor) - q_value(best)
        wrong = true_competitor_advantage > NUMERIC_TOLERANCE
        ambiguous = row["ambiguous"]
        category = ("flagged_true_rank_reversal" if wrong else "flagged_without_true_rank_reversal") if ambiguous else (
            "missed_true_rank_reversal" if wrong else "unflagged_without_true_rank_reversal")
        pair_confusion[category] += 1
        decision = decisions.setdefault((name, state), {
            "flagged": False, "wrong": best not in references[name]["optimal_actions"][state]})
        decision["flagged"] |= ambiguous
        if wrong:
            witnesses.append({**row, "classification": category,
                "true_competitor_advantage": true_competitor_advantage,
                "exact_optimal_actions": references[name]["optimal_actions"][state],
                "board": closure.boards[state], "remaining_horizon": closure.model.layers[state]})
    categories = ("flagged_and_wrong", "unflagged_and_wrong", "flagged_and_correct", "unflagged_and_correct")
    confusion, root_confusion = Counter(), Counter()
    for (_, state), decision in decisions.items():
        category = ("flagged" if decision["flagged"] else "unflagged") + "_and_" + ("wrong" if decision["wrong"] else "correct")
        confusion[category] += 1
        if state == closure.model.roots[0]:
            root_confusion[category] += 1
    return {
        "pair_count": len(pair_rows), "state_query_decision_count": len(decisions),
        "all_state_decision_counts": {key: confusion[key] for key in categories},
        "root_decision_counts": {key: root_confusion[key] for key in categories},
        "pair_ordering_counts": dict(pair_confusion),
        "largest_true_rank_reversal_witnesses": sorted(witnesses,
            key=lambda row: (-row["true_competitor_advantage"], row["query"], row["state"]))[:6],
        "scope": "Post-allocation exact optimal-action-set audit of pilot decisions with competing legal actions; a decision is flagged when any competitor is ambiguous. Flagged-and-correct is not a false uncertainty claim: correct choices can remain uncertain. Pair reversals are reported separately. These heuristics are not confidence intervals.",
    }


def _summary(records: Sequence[dict[str, Any]], groups: Mapping[str, Sequence[str]],
             budgets: Sequence[int]) -> dict[str, Any]:
    completed = [record for record in records if record["status"] == "COMPLETE"]
    runs = [run for record in completed for run in record["sampled_runs"]]
    by_budget = {}
    for budget in budgets:
        stages = [run["budgets"][str(budget)] for run in runs]
        arms = {}
        for arm_name in ARM_NAMES:
            entries = [stage["arms"][arm_name] for stage in stages]
            if not entries:
                continue
            query_groups = {}
            for group, names in groups.items():
                rows = [entry["queries"][name] for entry in entries for name in names]
                query_groups[group] = {
                    "query_evaluation_count": len(rows),
                    "state_query_evaluation_count": sum(row["all_active_states"]["state_count"] for row in rows),
                    "root_exact_optimal_action_count": sum(row["root_action_in_exact_optimal_set"] for row in rows),
                    "root_optimal_full_policy_count": sum(row["exact_lifted_objective_regret"] <= NUMERIC_TOLERANCE for row in rows),
                    "maximum_root_regret": max(row["exact_lifted_objective_regret"] for row in rows),
                    "mean_root_regret": math.fsum(row["exact_lifted_objective_regret"] for row in rows) / len(rows),
                    "all_state_exact_optimal_action_count": sum(row["all_active_states"]["exact_optimal_action_count"] for row in rows),
                    "all_state_optimal_full_policy_count": sum(row["all_active_states"]["optimal_full_policy_count"] for row in rows),
                    "maximum_all_state_regret": max(row["all_active_states"]["maximum_exact_lifted_objective_regret"] for row in rows),
                    "mean_state_regret_with_equal_case_seed_query_weight": math.fsum(row["all_active_states"]["mean_exact_lifted_objective_regret"] for row in rows) / len(rows),
                    "required_state_query_pairs": sum(entry["all_state_required_switches"][group]["required_state_query_pair_count"] for entry in entries),
                    "preserved_state_query_pairs": sum(entry["all_state_required_switches"][group]["preserved_state_query_pair_count"] for entry in entries),
                }
            equivalence = [row for entry in entries for row in entry["same_sample_full_state_comparator"]["queries"].values()]
            arms[arm_name] = {
                "case_seed_run_count": len(entries), "query_groups": query_groups,
                "mean_active_cells": math.fsum(entry["inventory"]["active_cells"] for entry in entries) / len(entries),
                "mean_allocation_seconds": math.fsum(entry["measured_cumulative_workloads"][-1]["one_time_allocation_seconds_including_pilot_planning"] for entry in entries) / len(entries),
                "mean_sample_allocate_build_plan_seconds": math.fsum(entry["measured_cumulative_workloads"][-1]["sample_allocate_build_plan_seconds"] for entry in entries) / len(entries),
                "mean_total_workload_seconds": math.fsum(entry["measured_cumulative_workloads"][-1]["including_shared_closure_sample_allocate_build_plan_forecast_audit_seconds"] for entry in entries) / len(entries),
                "maximum_same_sample_quotient_extra_regret": max(row["maximum_all_state_extra_regret_over_full_state"] for row in equivalence),
                "maximum_same_sample_empirical_value_difference": max(row["maximum_empirical_optimal_value_difference"] for row in equivalence),
            }
        paired = {}
        for group, names in groups.items():
            rows = [stage["matched_allocations"][name] for stage in stages for name in names]
            if rows:
                paired[group] = {
                    "query_evaluation_count": len(rows),
                    "root_improved": sum(row["root_directed_value_gain_over_uniform"] > NUMERIC_TOLERANCE for row in rows),
                    "root_worsened": sum(row["root_directed_value_gain_over_uniform"] < -NUMERIC_TOLERANCE for row in rows),
                    "root_tied": sum(abs(row["root_directed_value_gain_over_uniform"]) <= NUMERIC_TOLERANCE for row in rows),
                    "mean_root_directed_value_gain": math.fsum(row["root_directed_value_gain_over_uniform"] for row in rows) / len(rows),
                    "mean_state_directed_value_gain_with_equal_case_seed_query_weight": math.fsum(row["mean_all_state_directed_value_gain_over_uniform"] for row in rows) / len(rows),
                    "worst_root_directed_value_gain": min(row["root_directed_value_gain_over_uniform"] for row in rows),
                    "worst_state_directed_value_gain": min(row["minimum_all_state_directed_value_gain_over_uniform"] for row in rows),
                }
        by_budget[str(budget)] = {"arms": arms, "paired_allocation_comparison": paired}
    pilot_counts = Counter()
    for run in runs:
        pilot_counts.update(run["pilot_ranking_audit"]["all_state_decision_counts"])
    return {"declared_case_count": len(records), "completed_case_count": len(completed),
            "source_group_count": len({record["case"]["group"] for record in records}),
            "status_counts": dict(Counter(record["status"] for record in records)),
            "case_seed_run_count": len(runs), "by_budget": by_budget,
            "pilot_all_state_decision_counts": dict(pilot_counts)}


def _closure_overlap_inventory(cases: Sequence[RefinementCase],
        board_sets: Mapping[str, set[tuple[int, ...]]],
        board_layer_sets: Mapping[str, set[tuple[tuple[int, ...], int]]]) -> dict[str, Any]:
    """Account for reused boards using only already-materialized closures."""
    by_name = {case.name: case for case in cases}
    board_owners: dict[tuple[int, ...], set[str]] = defaultdict(set)
    layer_owners: dict[tuple[tuple[int, ...], int], set[str]] = defaultdict(set)
    for name, boards in board_sets.items():
        for board in boards:
            board_owners[board].add(name)
        for board_layer in board_layer_sets[name]:
            layer_owners[board_layer].add(name)

    def counts(owners: Mapping[Any, set[str]]) -> dict[str, int]:
        return {
            "unique_count": len(owners),
            "cross_case_count": sum(len(names) > 1 for names in owners.values()),
            "cross_source_group_count": sum(len({by_name[name].group for name in names}) > 1 for names in owners.values()),
            "cross_split_count": sum(len({by_name[name].split for name in names}) > 1 for names in owners.values()),
        }

    pairs = []
    for left, right in combinations(board_sets, 2):
        common = board_sets[left] & board_sets[right]
        if common:
            pairs.append({"left": left, "right": right,
                "same_source_group": by_name[left].group == by_name[right].group,
                "same_root_exposure_split": by_name[left].split == by_name[right].split,
                "raw_board_count_excluding_horizon": len(common),
                "board_and_remaining_horizon_count": len(board_layer_sets[left] & board_layer_sets[right]),
                "raw_board_example": min(common)})
    return {
        "scope": "Already-built complete closures of this V5 cohort only. Raw-board equality ignores remaining horizon; board-plus-horizon equality identifies the same finite-state input. Historical descendant closures are not reconstructed, and root exposure labels remain those in the frozen roster.",
        "completed_closure_count": len(board_sets),
        "excluded_case_names": [case.name for case in cases if case.name not in board_sets],
        "raw_boards_excluding_horizon": counts(board_owners),
        "board_and_remaining_horizon": counts(layer_owners),
        "nonempty_cross_case_pairs": pairs,
        "roots_present_in_other_completed_case_closures": [
            {"case_name": case.name, "source_group": case.group, "root_exposure_split": case.split,
             "other_case_names": sorted(board_owners.get(case.board, set()) - {case.name})}
            for case in cases if board_owners.get(case.board, set()) - {case.name}],
        "additional_closure_or_query_calls": 0,
        "unseen_state_generalization_demonstrated": False,
    }


def run_comparison_v5(*, cases: Sequence[RefinementCase] | None = None,
        fit_queries: Mapping[str, Query] | None = None,
        probe_queries: Mapping[str, Query] | None = None,
        sample_seeds: Sequence[int] = SAMPLE_SEEDS, budgets: Sequence[int] = SAMPLE_BUDGETS,
        pilot_samples: int = PILOT_SAMPLES, max_nodes: int = 30_000,
        cohort_roster: Mapping[str, Any] | None = None,
        progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    if cases is None:
        from .controlled_predictive_cohort_v5 import cases_v5
        cases = cases_v5()
    fixtures = tuple(cases)
    bank = dict(COMPARISON_QUERIES if fit_queries is None else fit_queries)
    probes = dict(PROBE_QUERIES if probe_queries is None else probe_queries)
    budgets = tuple(budgets)
    if (not fixtures or not bank or not sample_seeds or set(bank) & set(probes)
            or len({case.name for case in fixtures}) != len(fixtures)
            or len(set(sample_seeds)) != len(sample_seeds)):
        raise ValueError("cases/seeds/bank must be nonempty and unique; probes must be disjoint")
    if not budgets or tuple(sorted(set(budgets))) != budgets or budgets[0] // 2 < pilot_samples:
        raise ValueError("budgets must increase and their row floors must contain the pilot")
    queries = {**bank, **probes}
    groups = {"FIT_BANK": tuple(bank), **({"PROBES": tuple(probes)} if probes else {}), "ALL": tuple(queries)}
    started_all = perf_counter()
    records = []
    covered_board_sets, covered_board_layer_sets = {}, {}
    for case_index, case in enumerate(fixtures):
        started_case = perf_counter()
        record: dict[str, Any] = {"case": asdict(case)}
        try:
            closure = build_development_closure(horizon=case.horizon, max_nodes=max_nodes,
                                               boards={case.name: case.board})
        except ValueError as error:
            if "complete closure exceeds max_nodes=" not in str(error):
                raise
            record.update(status="CLOSURE_BUDGET_EXCEEDED", reason=str(error), elapsed_seconds=perf_counter() - started_case)
            records.append(record)
            if progress:
                progress({"case": case.name, "status": record["status"], "completed": len(records), "total": len(fixtures)})
            continue
        covered_board_sets[case.name] = set(closure.boards.values())
        covered_board_layer_sets[case.name] = {
            (board, closure.model.layers[state]) for state, board in closure.boards.items()}
        active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
        row_order = tuple(sorted(closure.model.rows))
        record["coverage"] = {**closure.counts, "exact_closure_seconds": closure.elapsed_seconds,
            "complete_all_legal_actions_and_outcomes": True}
        record["sample_row_order"] = row_order
        frozen_runs = []
        for seed_index, seed in enumerate(sample_seeds):
            sampler = RowSampler(closure.model, seed)
            pilot, pilot_info = sampler.advance({key: pilot_samples for key in row_order})
            pilot_counts = {key: pilot_samples for key in row_order}
            started = perf_counter()
            allocation = plan_allocations(pilot, pilot_counts, bank, budgets=budgets)
            allocation_seconds = perf_counter() - started
            targets = {"UNIFORM": {budget: {key: budget for key in row_order} for budget in budgets},
                       "DIRECTED": allocation.allocations}
            for arm_targets in targets.values():
                previous = pilot_counts
                for budget in budgets:
                    counts = arm_targets[budget]
                    if (counts.keys() != pilot_counts.keys() or sum(counts.values()) != budget * len(row_order)
                            or any(counts[key] < max(previous[key], budget // 2) for key in row_order)):
                        raise AssertionError("allocation must preserve logical budget, floor and nested row prefixes")
                    previous = counts
            branches, forks = {}, {}
            for arm_name in ARM_NAMES:
                branches[arm_name], forks[arm_name] = sampler.fork()
            frozen_stages = {}
            for budget_index, budget in enumerate(budgets):
                order = ARM_NAMES if (case_index + seed_index + budget_index) % 2 == 0 else ARM_NAMES[::-1]
                stage = {}
                for arm_name in order:
                    empirical, info = branches[arm_name].advance(targets[arm_name][budget])
                    stage[arm_name] = _freeze_arm(empirical, closure, queries, info,
                        allocation_seconds if arm_name == "DIRECTED" else 0.0,
                        forks[arm_name], targets[arm_name][budget])
                frozen_stages[budget] = (stage, order)
            frozen_runs.append({"sample_seed": seed, "pilot_sampling": pilot_info,
                "allocation_diagnostics": allocation.diagnostics,
                "allocation_seconds": allocation_seconds,
                "pair_diagnostics": allocation.pair_diagnostics,
                "frozen_stages": frozen_stages,
                "physical_draw_accounting": {"shared_pilot_draws": sampler.physical_draws,
                    "branch_draws_after_pilot": {name: branches[name].physical_draws for name in ARM_NAMES},
                    "total_actual_draw_calls": sampler.physical_draws + sum(branch.physical_draws for branch in branches.values()),
                    "logical_final_budget_per_arm": budgets[-1] * len(row_order),
                    "pilot_drawn_once": True, "branch_prefixes_duplicated_physically_after_pilot": True}})
            if progress:
                progress({"case": case.name, "sample_seed": seed, "status": "ALL_ARM_PLANS_FROZEN",
                          "active_states": len(active), "rows": len(row_order)})
        # All observations, allocations, empirical constructions and ten-query
        # policies for this case are fixed before any ground-optimal label.
        exact, exact_inventory, _ = _fit(lambda: compile_full_state(closure.model), closure)
        references = _reference(closure, exact, queries)
        root = closure.model.roots[0]
        record["exact_query_references"] = {name: {
            "root_q_values": row["root_q_values"], "root_optimal_actions": row["optimal_actions"][root],
            "root_optimal_value": row["values"][root]} for name, row in references.items()}
        record["exact_all_state_required_switches"] = _switches(references, active, groups)
        record["exact_reference_separate_seconds"] = exact_inventory["construction_seconds"] + math.fsum(
            row["planning_seconds"] + row["all_state_action_labeling_seconds"] for row in references.values())
        record["sampled_runs"] = []
        for frozen_run in frozen_runs:
            run = {key: value for key, value in frozen_run.items() if key not in {"frozen_stages", "pair_diagnostics"}}
            run["pilot_ranking_audit"] = pilot_ranking_audit(frozen_run["pair_diagnostics"], closure, references, bank)
            run["budgets"] = {}
            for budget, (stage, order) in frozen_run["frozen_stages"].items():
                arms, private = {}, {}
                for arm_name in order:
                    arms[arm_name], private[arm_name] = _audit_arm(stage[arm_name], closure, queries, references, groups)
                run["budgets"][str(budget)] = {
                    "logical_draw_budget_per_arm": budget * len(row_order),
                    "mean_logical_samples_per_row": budget, "measured_arm_order": order,
                    "arms": arms, "matched_allocations": _matched_allocations(private, active, root, queries)}
            record["sampled_runs"].append(run)
        record.update(status="COMPLETE", elapsed_seconds=perf_counter() - started_case)
        records.append(record)
        if progress:
            progress({"case": case.name, "status": "COMPLETE", "completed": len(records), "total": len(fixtures),
                      "elapsed_seconds": record["elapsed_seconds"]})
    return {
        "schema": "acfqp.controlled_predictive_allocation_comparison.v5",
        "status": "DEVELOPMENT_COMPLETE" if all(row["status"] == "COMPLETE" for row in records) else "DEVELOPMENT_COMPLETE_WITH_CLOSURE_EXCLUSIONS",
        "scientific_gate": "NOT_A_FORMAL_GATE", "case_count": len(fixtures),
        "all_declared_candidates_retained": True, "cohort_roster": cohort_roster,
        "settings": {"pilot_samples_per_row": pilot_samples, "budgets_mean_samples_per_row": budgets,
            "sample_seeds": list(sample_seeds), "query_order": list(queries),
            "fit_queries": {name: asdict(query) for name, query in bank.items()},
            "probe_queries": {name: asdict(query) for name, query in probes.items()},
            "numeric_tolerance": NUMERIC_TOLERANCE, "max_nodes": max_nodes,
            "row_stream": "acfqp-v5:{sample_seed}:{state}:{action}", "reward_units": "merge score / 2048"},
        "cases": records,
        "within_cohort_closure_overlap": _closure_overlap_inventory(
            fixtures, covered_board_sets, covered_board_layer_sets),
        "summary_by_split": {split: _summary(records if split == "ALL" else [row for row in records if row["case"]["split"] == split], groups, budgets)
            for split in ("ALL", *sorted({case.split for case in fixtures}))},
        "summary_by_source_group": {group: _summary([row for row in records if row["case"]["group"] == group], groups, budgets)
            for group in sorted({case.group for case in fixtures})},
        "elapsed_seconds": perf_counter() - started_all,
        "accounting": {
            "treatment": "Both arms use exact empirical quotient; only the post-pilot per-row observation allocation differs. No exact probabilities, exact Q values or probe queries enter allocation.",
            "sampling": "Pilot sampled once; both budgets are allocated from it before further draws. Independent arm stream states share identical row prefixes; each arm advances nested 256 to 1024 targets. Logical budgets count the pilot once per arm; physical branch duplication is reported separately.",
            "audit": "All case/seed/budget/arm plans are frozen before exact optimal labels for that case. Every covered active state receives exact frozen-policy evaluation. All-state averages are descriptive, not natural-play visitation frequencies.",
            "costs": "Directed workload includes all fixed-pilot allocation time, including six-query empirical planning and influence analysis. Each dose includes cumulative sampling/materialization but its own current-model construction/planning. Branch-fork bookkeeping, exact reference labeling, full-state auxiliary validation and inventory serialization are separate experimental costs.",
            "units": "Source groups identify declared starting boards. Sampling seeds, queries and covered states are repeated measurements, not independent replications. Root exposure and duplicate identity are retained in the cohort roster.",
        },
        "limitations": [
            "Exploratory covered finite-board model; no formal Gate, independent confirmation, unseen-state encoding or full-game guarantee.",
            "Pilot gap uncertainty is a plug-in linearization around empirical policy and probabilities. Policy switching and unobserved outcome support can invalidate its ranking heuristic.",
            "The directed arm uses the six-query bank; four unfit probes reuse its sampled dynamics without influencing allocation.",
            "Timing is descriptive local wall time; repeated-query doses are nested diagnostics and not independent runtime replications.",
            "U005 remains scientifically failed and U006 is not executed.",
        ],
    }


__all__ = ("RowSampler", "FrozenArm", "pilot_ranking_audit", "run_comparison_v5")
