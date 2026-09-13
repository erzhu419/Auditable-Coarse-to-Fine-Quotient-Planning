"""Matched empirical exact-quotient and incremental-refinement development.

The declared exposed and fresh source boards are all retained. Each sampled
kernel is shared by all four arms; exact dynamics label and audit frozen
policies only. Output stores compact aggregates rather than state dumps.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, replace
import math
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from .controlled_predictive_2048_challenges_v2 import FAMILIES, _source_board
from .controlled_predictive_2048_v1 import build_development_closure
from .controlled_predictive_comparison_v2 import COMPARISON_QUERIES, SAMPLE_SEEDS
from .controlled_predictive_comparison_v3 import (
    COMPONENTS, NUMERIC_TOLERANCE, PROBE_QUERIES, RefinementCase,
    _arm, _fit, _reference, _switches, refinement_cases,
)
from .controlled_predictive_quotient_v1 import (
    CompiledModel, Query, build_quotient, compile_full_state, sample_model,
)
from .controlled_predictive_refinement_v3 import build_refined_quotient
from .controlled_predictive_refinement_v4 import build_refined_quotient_v4


DEVELOPMENT_SEEDS_V4 = (836101, 836201, 836301, 836401)
ARM_NAMES = ("full_state_empirical", "exact_empirical_quotient",
             "query_refinement_v3", "incremental_refinement_v4")


def comparison_cases_v4() -> tuple[RefinementCase, ...]:
    exposed = tuple(replace(case, split="EXPOSED_V3_DEVELOPMENT") for case in refinement_cases())
    fresh = tuple(RefinementCase(
        f"v4_{family}_{seed + index}", f"v4_{family}_{seed + index}",
        "NEW_DEVELOPMENT_V4", _source_board(family, seed + index), family,
        seed + index, 3,
    ) for index, family in enumerate(FAMILIES) for seed in DEVELOPMENT_SEEDS_V4)
    return exposed + fresh


def root_board_overlap(cases: Sequence[RefinementCase]) -> dict[str, Any]:
    """Report repeated starting boards without dropping declared generation units."""
    grouped: dict[tuple[int, ...], list[RefinementCase]] = defaultdict(list)
    for case in cases:
        grouped[tuple(case.board)].append(case)
    exposed = {tuple(case.board) for case in cases if case.split == "EXPOSED_V3_DEVELOPMENT"}
    new = [case for case in cases if case.split == "NEW_DEVELOPMENT_V4"]
    repeated = [{
        "board": board,
        "case_names": [case.name for case in members],
        "splits": [case.split for case in members],
    } for board, members in grouped.items() if len(members) > 1]
    reused = [{
        "new_case_name": case.name,
        "exposed_case_names": [member.name for member in grouped[tuple(case.board)]
                               if member.split == "EXPOSED_V3_DEVELOPMENT"],
        "board": tuple(case.board),
    } for case in new if tuple(case.board) in exposed]
    return {
        "declared_case_count": len(cases),
        "unique_root_board_count": len(grouped),
        "duplicate_root_group_count": len(repeated),
        "duplicate_root_groups": repeated,
        "new_seed_case_count": len(new),
        "unique_new_root_board_count": len({tuple(case.board) for case in new}),
        "new_cases_reusing_exposed_roots": reused,
        "new_cases_reusing_exposed_root_count": len(reused),
        "unique_new_roots_not_among_declared_exposed_roots": len({
            tuple(case.board) for case in new} - exposed),
        "all_declared_cases_retained": True,
        "scope": "Starting board tuples in this declared cohort only. New generator seeds do not guarantee new boards; unseen roots do not imply unseen descendant states or independent samples.",
    }


def _compact_diagnostics(diagnostics: dict[str, Any] | None) -> dict[str, Any] | None:
    if diagnostics is None:
        return None
    result = {key: value for key, value in diagnostics.items() if key not in {
        "iterations", "queries", "construction_scope"}}
    result["iterations"] = [{
        "iteration": row["iteration"], "inventory": row["inventory"],
        "worst_errors": row["worst_errors"], "violating_cells": row["violating_cells"],
        "violating_states": row["violating_states"], "split_cells": len(row["splits"]),
        "elapsed_seconds": row["elapsed_seconds"],
        **{key: row[key] for key in ("recomputed_cells", "recomputed_states", "cached_cells", "cached_states")
           if key in row},
    } for row in diagnostics["iterations"]]
    return result


def _compact_arm(arm: dict[str, Any]) -> dict[str, Any]:
    queries = {}
    for name, row in arm["queries"].items():
        queries[name] = {
            "root_action": row["root_action"],
            "root_action_in_exact_optimal_set": row["root_action_in_exact_optimal_set"],
            "exact_lifted_objective_regret": row["exact_lifted_objective_regret"],
            "predicted_root_metrics": row["predicted_root_metrics"],
            "exact_lifted_root_metrics": row["exact_lifted_root_metrics"],
            "all_active_states": {key: value for key, value in row["all_active_states"].items()
                                  if key != "worst_regret_witness"},
        }
    worst_query = max(arm["queries"], key=lambda name: arm["queries"][name]["all_active_states"][
        "maximum_exact_lifted_objective_regret"])
    return {
        "inventory": arm["inventory"], "queries": queries,
        "refinement_diagnostics": _compact_diagnostics(arm["refinement_diagnostics"]),
        "all_state_required_switches": arm["all_state_required_switches"],
        "root_required_switches": arm["root_required_switches"],
        "measured_cumulative_workloads": arm["measured_cumulative_workloads"],
        "worst_regret_witness": {"query": worst_query, **arm["queries"][worst_query][
            "all_active_states"]["worst_regret_witness"]},
        "model_build_count": arm["model_build_count"],
        "query_count_using_same_compiled_model": arm["query_count_using_same_compiled_model"],
    }


def compiled_equivalence(left: CompiledModel, right: CompiledModel) -> dict[str, Any]:
    """Compare dynamics after replacing arbitrary cell IDs with member tuples."""
    left_keys = {key: tuple(sorted(cell.members)) for key, cell in left.cells.items()}
    right_keys = {key: tuple(sorted(cell.members)) for key, cell in right.cells.items()}
    same_partition = set(left_keys.values()) == set(right_keys.values())
    result: dict[str, Any] = {"same_member_partition": same_partition,
        "same_roots": tuple(left_keys[key] for key in left.roots) == tuple(right_keys[key] for key in right.roots),
        "same_cell_labels": False, "same_action_successor_support": False,
        "maximum_transition_probability_difference": None,
        "maximum_probability_weighted_reward_difference": None,
        "equivalent": False}
    if not same_partition:
        return result

    def normalized(model: CompiledModel, keys: Mapping[int, tuple[int, ...]]) -> tuple[dict, dict]:
        labels = {keys[key]: (cell.layer, cell.terminal) for key, cell in model.cells.items()}
        rows = {}
        for (cell, action), outcomes in model.rows.items():
            masses: dict[tuple[int, ...], list] = defaultdict(list)
            for outcome in outcomes:
                masses[keys[outcome.next_state]].append(outcome)
            rows[keys[cell], action] = {successor: (
                math.fsum(outcome.probability for outcome in grouped),
                math.fsum(outcome.probability * outcome.reward for outcome in grouped),
            ) for successor, grouped in masses.items()}
        return labels, rows

    labels_l, rows_l = normalized(left, left_keys)
    labels_r, rows_r = normalized(right, right_keys)
    same_support = rows_l.keys() == rows_r.keys() and all(
        rows_l[key].keys() == rows_r[key].keys() for key in rows_l)
    result.update(same_cell_labels=labels_l == labels_r,
                  same_action_successor_support=same_support)
    if same_support:
        differences = [(abs(rows_l[key][successor][0] - rows_r[key][successor][0]),
                        abs(rows_l[key][successor][1] - rows_r[key][successor][1]))
                       for key in rows_l for successor in rows_l[key]]
        result["maximum_transition_probability_difference"] = max((row[0] for row in differences), default=0.0)
        result["maximum_probability_weighted_reward_difference"] = max((row[1] for row in differences), default=0.0)
        result["equivalent"] = (result["same_roots"] and result["same_cell_labels"] and all(
            value <= NUMERIC_TOLERANCE for row in differences for value in row))
    return result


def _matched(private: Mapping[str, Any], active: Sequence[int], root: int,
             queries: Mapping[str, Query]) -> dict[str, Any]:
    result = {}
    for name in ARM_NAMES[1:]:
        query_rows = {}
        for query in queries:
            full = private[ARM_NAMES[0]][query]
            candidate = private[name][query]
            extra = {state: full["actual"][state]["value"] - candidate["actual"][state]["value"]
                     for state in active}
            query_rows[query] = {
                "root_extra_regret_over_full_state": extra[root],
                "maximum_all_state_extra_regret_over_full_state": max(extra.values()),
                "minimum_all_state_extra_regret_over_full_state": min(extra.values()),
                "mean_all_state_extra_regret_over_full_state": math.fsum(extra.values()) / len(active),
                "states_with_extra_regret_over_full_state": sum(value > NUMERIC_TOLERANCE for value in extra.values()),
                "action_disagreements_with_full_state": sum(candidate["policy"][state] != full["policy"][state] for state in active),
                "maximum_actual_component_difference_from_full_state": {component: max(abs(
                    candidate["actual"][state][component] - full["actual"][state][component])
                    for state in active) for component in COMPONENTS},
            }
        result[name] = query_rows
    result["v4_vs_v3"] = {query: {
        "active_state_count": len(active),
        "action_disagreement_count": sum(private[ARM_NAMES[2]][query]["policy"][state] !=
                                          private[ARM_NAMES[3]][query]["policy"][state] for state in active),
        "maximum_actual_component_differences": {component: max(abs(
            private[ARM_NAMES[2]][query]["actual"][state][component] -
            private[ARM_NAMES[3]][query]["actual"][state][component]) for state in active)
            for component in COMPONENTS},
    } for query in queries}
    return result


def _summary(records: Sequence[dict[str, Any]], groups: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    runs = [sample for case in records if case["status"] == "COMPLETE" for sample in case["sampled_runs"]]
    arms = {}
    for arm_name in ARM_NAMES:
        entries = [sample["arms"][arm_name] for sample in runs]
        if not entries:
            continue
        query_groups = {}
        for group, names in groups.items():
            rows = [entry["queries"][name] for entry in entries for name in names]
            query_groups[group] = {
                "query_evaluations": len(rows),
                "state_query_evaluations": sum(row["all_active_states"]["state_count"] for row in rows),
                "root_optimal_action_count": sum(row["root_action_in_exact_optimal_set"] for row in rows),
                "root_optimal_policy_count": sum(row["exact_lifted_objective_regret"] <= NUMERIC_TOLERANCE for row in rows),
                "all_state_optimal_action_count": sum(row["all_active_states"]["exact_optimal_action_count"] for row in rows),
                "all_state_optimal_policy_count": sum(row["all_active_states"]["optimal_full_policy_count"] for row in rows),
                "maximum_root_regret": max(row["exact_lifted_objective_regret"] for row in rows),
                "maximum_all_state_regret": max(row["all_active_states"]["maximum_exact_lifted_objective_regret"] for row in rows),
                "mean_state_regret_equal_case_seed_query_weight": math.fsum(row["all_active_states"][
                    "mean_exact_lifted_objective_regret"] for row in rows) / len(rows),
                "maximum_all_state_prediction_errors": {component: max(row["all_active_states"][
                    "maximum_prediction_absolute_errors"][component] for row in rows) for component in COMPONENTS},
                "required_state_query_pairs": sum(entry["all_state_required_switches"][group][
                    "required_state_query_pair_count"] for entry in entries),
                "preserved_state_query_pairs": sum(entry["all_state_required_switches"][group][
                    "preserved_state_query_pair_count"] for entry in entries),
            }
        arm_summary = {
            "case_seed_runs": len(entries), "query_groups": query_groups,
            "mean_active_cells": math.fsum(entry["inventory"]["active_cells"] for entry in entries) / len(entries),
            "mean_construction_seconds": math.fsum(entry["inventory"]["construction_seconds"] for entry in entries) / len(entries),
            "mean_construct_plus_ten_queries_seconds": math.fsum(entry["measured_cumulative_workloads"][-1][
                "construction_plus_planning_seconds"] for entry in entries) / len(entries),
            "mean_full_workload_seconds": math.fsum(entry["measured_cumulative_workloads"][-1][
                "including_shared_closure_sample_build_plan_forecast_audit_seconds"] for entry in entries) / len(entries),
        }
        if arm_name != ARM_NAMES[0]:
            matched = [sample["matched_comparisons"][arm_name][name] for sample in runs for name in groups["ALL"]]
            arm_summary["maximum_extra_regret_over_full_state"] = max(row[
                "maximum_all_state_extra_regret_over_full_state"] for row in matched)
            arm_summary["state_queries_with_extra_regret_over_full_state"] = sum(row[
                "states_with_extra_regret_over_full_state"] for row in matched)
        arms[arm_name] = arm_summary
    geometry = Counter()
    for sample in runs:
        exact = sample["arms"][ARM_NAMES[1]]["inventory"]["active_cells"]
        refined = sample["arms"][ARM_NAMES[3]]["inventory"]["active_cells"]
        geometry["refined_fewer_cells" if refined < exact else "refined_more_cells" if refined > exact else "same_cell_count"] += 1
    return {"declared_cases": len(records), "source_groups": len({row["case"]["group"] for row in records}),
        "status_counts": dict(Counter(row["status"] for row in records)), "case_seed_runs": len(runs), "arms": arms,
        "v4_vs_exact_empirical_active_cell_counts": dict(geometry),
        "v4_v3_compiled_equivalence_count": sum(sample["v4_v3_compiled_equivalence"]["equivalent"] for sample in runs),
        "v4_v3_actual_policy_disagreement_count": sum(row["action_disagreement_count"]
            for sample in runs for row in sample["matched_comparisons"]["v4_vs_v3"].values()),
    }


def run_comparison_v4(*, cases: Sequence[RefinementCase] | None = None,
        fit_queries: Mapping[str, Query] | None = None, probe_queries: Mapping[str, Query] | None = None,
        samples_per_row: int = 64, sample_seeds: Sequence[int] = SAMPLE_SEEDS, max_nodes: int = 30_000,
        progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    fixtures = tuple(comparison_cases_v4() if cases is None else cases)
    bank = dict(COMPARISON_QUERIES if fit_queries is None else fit_queries)
    probes = dict(PROBE_QUERIES if probe_queries is None else probe_queries)
    if not fixtures or not bank or not sample_seeds or set(bank) & set(probes):
        raise ValueError("cases, fit queries, and sample seeds must be nonempty; bank and probes must be disjoint")
    if len({case.name for case in fixtures}) != len(fixtures) or len(set(sample_seeds)) != len(sample_seeds):
        raise ValueError("case names and sample seeds must be unique")
    queries = {**bank, **probes}
    groups = {"FIT_BANK": tuple(bank), **({"PROBES": tuple(probes)} if probes else {}), "ALL": tuple(queries)}
    started_all = perf_counter()
    records = []
    board_owners: dict[tuple[int, ...], set[str]] = defaultdict(set)
    for case_index, case in enumerate(fixtures):
        started_case = perf_counter()
        record: dict[str, Any] = {"case": asdict(case)}
        try:
            closure = build_development_closure(horizon=case.horizon, max_nodes=max_nodes, boards={case.name: case.board})
        except ValueError as error:
            if "complete closure exceeds max_nodes=" not in str(error):
                raise
            record.update(status="CLOSURE_BUDGET_EXCEEDED", reason=str(error))
            records.append(record)
            if progress:
                progress({"case": case.name, "status": record["status"]})
            continue
        for board in set(closure.boards.values()):
            board_owners[board].add(case.name)
        active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
        root = closure.model.roots[0]
        record["coverage"] = {**closure.counts, "exact_closure_seconds": closure.elapsed_seconds,
            "complete_all_legal_actions_and_outcomes": True}
        exact, inventory, _ = _fit(lambda: compile_full_state(closure.model), closure)
        references = _reference(closure, exact, queries)
        record["exact_reference_construction_seconds"] = inventory["construction_seconds"]
        record["exact_reference_query_labeling_seconds"] = math.fsum(row["planning_seconds"] +
            row["all_state_action_labeling_seconds"] for row in references.values())
        record["exact_root_query_references"] = {name: {"root_q_values": row["root_q_values"],
            "root_optimal_actions": row["optimal_actions"][root], "root_optimal_value": row["values"][root]}
            for name, row in references.items()}
        record["exact_all_state_required_switches"] = _switches(references, active, groups)
        record["sampled_runs"] = []
        for seed_index, seed in enumerate(sample_seeds):
            started = perf_counter()
            empirical = sample_model(closure.model, samples_per_row=samples_per_row, seed=seed)
            sampling_seconds = perf_counter() - started
            builders = {
                ARM_NAMES[0]: (lambda: compile_full_state(empirical), False),
                ARM_NAMES[1]: (lambda: build_quotient(empirical), False),
                ARM_NAMES[2]: (lambda: build_refined_quotient(empirical, bank, numeric_tolerance=NUMERIC_TOLERANCE), True),
                ARM_NAMES[3]: (lambda: build_refined_quotient_v4(empirical, bank, numeric_tolerance=NUMERIC_TOLERANCE), True),
            }
            offset = (case_index * len(sample_seeds) + seed_index) % len(ARM_NAMES)
            order = ARM_NAMES[offset:] + ARM_NAMES[:offset]
            sample: dict[str, Any] = {"sample_seed": seed, "sampling_seconds": sampling_seconds,
                "empirical_draws": len(empirical.rows) * samples_per_row,
                "empirical_model_sample_count": 1, "measured_arm_order": order, "arms": {}}
            private, models = {}, {}
            for name in order:
                builder, refined = builders[name]
                compiled, inventory, diagnostics = _fit(builder, closure, refined=refined)
                arm, private[name] = _arm(compiled, inventory, closure, queries, references, groups,
                    sampling_seconds=sampling_seconds, privileged=False, diagnostics=diagnostics)
                sample["arms"][name] = _compact_arm(arm)
                models[name] = compiled
            started = perf_counter()
            sample["v4_v3_compiled_equivalence"] = compiled_equivalence(models[ARM_NAMES[2]], models[ARM_NAMES[3]])
            sample["matched_comparisons"] = _matched(private, active, root, queries)
            sample["post_measurement_comparison_seconds"] = perf_counter() - started
            record["sampled_runs"].append(sample)
            if progress:
                progress({"case": case.name, "sample_seed": seed, "status": "SAMPLE_COMPLETE",
                    "active_cells": {name: row["inventory"]["active_cells"] for name, row in sample["arms"].items()},
                    "v4_v3_equivalent": sample["v4_v3_compiled_equivalence"]["equivalent"]})
        record.update(status="COMPLETE", elapsed_seconds=perf_counter() - started_case)
        records.append(record)
        if progress:
            progress({"case": case.name, "status": "COMPLETE", "completed": len(records), "total": len(fixtures)})
    owners_splits = {case.name: case.split for case in fixtures}
    return {
        "schema": "acfqp.controlled_predictive_comparison.v4", "scientific_gate": "NOT_A_FORMAL_GATE",
        "status": "DEVELOPMENT_COMPLETE" if all(row["status"] == "COMPLETE" for row in records)
                  else "DEVELOPMENT_COMPLETE_WITH_CLOSURE_EXCLUSIONS",
        "settings": {"fit_queries": {name: asdict(query) for name, query in bank.items()},
            "probe_queries": {name: asdict(query) for name, query in probes.items()}, "query_order": list(queries),
            "samples_per_row": samples_per_row, "sample_seeds": list(sample_seeds), "max_nodes": max_nodes,
            "initial_reward_tolerance": 0.01, "initial_tv_tolerance": 0.2, "numeric_tolerance": NUMERIC_TOLERANCE,
            "empirical_exact_quotient_tolerances": {"reward": 0.0, "tv": 0.0}},
        "case_count": len(fixtures), "all_declared_candidates_retained": True, "cases": records,
        "summary_by_split": {split: _summary(records if split == "ALL" else
            [row for row in records if row["case"]["split"] == split], groups)
            for split in ("ALL", *sorted({case.split for case in fixtures}))},
        "summary_by_source_group": {group: _summary([row for row in records if row["case"]["group"] == group], groups)
            for group in sorted({case.group for case in fixtures})},
        "root_board_identity_overlap": root_board_overlap(fixtures),
        "board_identity_overlap_excluding_horizon": {
            "scope": "Declared completed V4 closures only; prior V1/discovery and deferred V2 cohort are not reconstructed.",
            "unique_boards": len(board_owners),
            "cross_case_boards": sum(len(owners) > 1 for owners in board_owners.values()),
            "cross_split_boards": sum(len({owners_splits[name] for name in owners}) > 1 for owners in board_owners.values()),
            "unseen_state_generalization_demonstrated": False},
        "original_deferred_24_case_cohort_executed": False, "elapsed_seconds": perf_counter() - started_all,
        "accounting": {
            "matching": "One 64-per-row empirical kernel per case/seed is shared by all four arms. Exact zero-tolerance empirical quotient uses no exact environmental probabilities. V3 and V4 use only the fit query bank.",
            "audit": "Each planned cell policy is frozen and lifted before exact all-state evaluation. Regret and required switches concern the exact environment. All-state summaries are unweighted diagnostics, not natural-play visitation.",
            "costs": "Four build-plus-query blocks rotate starting arm by case/seed. Construction includes internal refinement; external planning, component forecast and exact frozen-policy audit are separately charged. Shared closure/sampling are counted once in each hypothetical arm workload. Inventory serialization, oracle action labeling and post-measurement equivalence comparisons are separately reported.",
            "units": "Old V3 boards are exposed. Fresh development seeds are fixed without performance selection; distinct seeds can produce identical roots, reported separately by raw board tuple. Source groups are generation units, not necessarily distinct boards. Sample seeds and states are repeated measurements. No timing confidence interval is inferred from different sampled models.",
        },
        "limitations": [
            "Exploratory finite covered-board models; no formal Gate or full-game performance claim.",
            "Empirical policy consistency does not certify true risk. Probe queries do not establish unseen-board encoder generalization.",
            "Timing is one interleaved local pass, not repeated same-model latency benchmarking; workload excludes online board encoding and loading.",
            "U005 remains FAIL and U006 remains unstarted; the original deferred 24-case cohort is not consumed.",
        ],
    }
