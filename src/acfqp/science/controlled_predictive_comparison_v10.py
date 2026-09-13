"""Demand-driven feature computation versus simultaneous eager target-rule builds.

The empirical bank and source-fit scenarios are unchanged from V8. Target
observations intentionally enter adaptation and scratch fitting, never queries
or exact policy labels. Exact eager/lazy comparisons and ground auditing follow all eight frozen plans.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from .controlled_predictive_2048_v1 import DevelopmentClosure, build_development_closure
from .controlled_predictive_adaptation_v9 import (
    build_adapted_target as build_adapted_target_v9, build_scratch_target as build_scratch_target_v9,
)
from .controlled_predictive_adaptation_v10 import (
    build_adapted_target as build_adapted_target_v10, build_scratch_target as build_scratch_target_v10,
)
from .controlled_predictive_cohort_v7 import V7Case
from .controlled_predictive_cohort_v10 import build_cohort_roster_v10, cases_v10
from .controlled_predictive_comparison_v3 import (
    COMPARISON_QUERIES, COMPONENTS, NUMERIC_TOLERANCE, PROBE_QUERIES, SAMPLE_SEEDS,
    _fit, _reference, _summarize, _switches,
)
from .controlled_predictive_comparison_v7 import (
    FrozenArm, _audit_arm, _cell_conflicts, _pre_fit_overlap, _worst_encoding_added_loss,
)
from .controlled_predictive_comparison_v8 import _record_for_scenario, _validate_scenarios
from .controlled_predictive_encoder_io_v7 import artifact_inventory, freeze_artifact_payload
from .controlled_predictive_encoder_runtime_v8 import compile_encoded as compile_encoded_v8
from .controlled_predictive_encoder_runtime_v10 import compile_encoded as compile_encoded_v10
from .controlled_predictive_encoder_v7 import TrainingModel
from .controlled_predictive_encoder_v8 import fit_constraint_encoder
from .controlled_predictive_quotient_v1 import (
    CompiledModel, FiniteModel, Query, action_outcome_shuffle,
    build_quotient, compile_full_state, plan, sample_model,
)


ARM_NAMES = ("full_state_empirical", "exact_empirical_quotient", "frozen_rule_encoder",
             "target_scratch_encoder_v9", "target_adapted_encoder_v9",
             "target_scratch_encoder_v10", "target_adapted_encoder_v10",
             "action_outcome_shuffle_adapted_v10")
TARGET_ARMS = ARM_NAMES[3:7]
ENCODER_ARMS = ARM_NAMES[2:7]
SOURCE_USING_ARMS = ("frozen_rule_encoder", "target_adapted_encoder_v9",
                     "target_adapted_encoder_v10", "action_outcome_shuffle_adapted_v10")
RUNTIME_PAIRS = {"scratch": ("target_scratch_encoder_v9", "target_scratch_encoder_v10"),
                 "adapted": ("target_adapted_encoder_v9", "target_adapted_encoder_v10")}
SAMPLES_PER_ROW = 256


@dataclass
class FrozenTargetArm(FrozenArm):
    encoder: Any


def _freeze_arm(name: str, empirical: FiniteModel, closure: DevelopmentClosure,
                source_encoder: Any, queries: Mapping[str, Query], *, case_name: str,
                adapted: FrozenTargetArm | None = None) -> FrozenTargetArm:
    """Measure actual construction separately from the control's reused setup."""
    encoded = None
    encoder = None
    shuffle_seconds = 0.0
    if name == "full_state_empirical":
        builder = lambda: compile_full_state(empirical)
    elif name == "exact_empirical_quotient":
        builder = lambda: build_quotient(empirical)
    elif name in TARGET_ARMS:
        target = TrainingModel(case_name, empirical, closure.boards)
        def builder() -> CompiledModel:
            nonlocal encoded, encoder
            if name == "target_scratch_encoder_v9":
                encoded = build_scratch_target_v9(target)
            elif name == "target_adapted_encoder_v9":
                encoded = build_adapted_target_v9(source_encoder, target)
            elif name == "target_scratch_encoder_v10":
                encoded = build_scratch_target_v10(target)
            else:
                encoded = build_adapted_target_v10(source_encoder, target)
            encoder = encoded.encoder
            return encoded.compiled
    else:
        kernel = empirical
        encoder = source_encoder
        if name == "action_outcome_shuffle_adapted_v10":
            if adapted is None:
                raise ValueError("the shuffled control requires the already-built adapted encoder")
            encoder = adapted.encoder
            started = perf_counter()
            kernel = action_outcome_shuffle(empirical)
            shuffle_seconds = perf_counter() - started
        def builder() -> CompiledModel:
            nonlocal encoded
            compiler = compile_encoded_v10 if name == "action_outcome_shuffle_adapted_v10" else compile_encoded_v8
            encoded = compiler(kernel, closure.boards, encoder)
            return encoded.compiled
    compiled, inventory, _ = _fit(builder, closure)
    actual = inventory["construction_seconds"] + shuffle_seconds
    setup = adapted.inventory["actual_construction_seconds"] if name == "action_outcome_shuffle_adapted_v10" else 0.0
    inventory.update(actual_construction_seconds=actual,
        construction_seconds=actual + setup,
        reused_target_adaptation_setup_seconds_attributed_to_workload=setup,
        action_shuffle_seconds_included_in_actual_construction=shuffle_seconds)
    if encoded is not None:
        started = perf_counter()
        inventory["portable_encoder_and_model_bytes"] = artifact_inventory(
            freeze_artifact_payload(encoder, compiled, encoded.code_to_cell))
        inventory["portable_inventory_serialization_seconds"] = perf_counter() - started
        inventory["registered_state_and_board_maps_are_audit_only"] = True
        inventory["cell_diameter_status"] = "UNMEASURED"
    plans = {}
    for query_name, query in queries.items():
        started = perf_counter()
        solution = plan(compiled, query)
        plans[query_name] = solution, perf_counter() - started
    return FrozenTargetArm(compiled, inventory, plans,
        encoded.diagnostics if encoded is not None else None,
        encoded.code_to_cell if encoded is not None else None, encoder)


def _runtime_semantic_equivalence(frozen: Mapping[str, FrozenTargetArm],
                                  queries: Mapping[str, Query]) -> dict[str, Any]:
    """Compare exact execution semantics after timing, without consulting truth."""
    started = perf_counter()
    pairs = {}
    for kind, (eager_name, lazy_name) in RUNTIME_PAIRS.items():
        eager, lazy = frozen[eager_name], frozen[lazy_name]
        eager_payload, lazy_payload = eager.encoder.to_payload(), lazy.encoder.to_payload()
        checks = {"encoder_payload": eager_payload == lazy_payload,
            **{field: getattr(eager.compiled, field) == getattr(lazy.compiled, field)
               for field in ("cells", "rows", "roots", "state_to_cell", "diameters")},
            "code_to_cell": eager.code_to_cell == lazy.code_to_cell}
        query_checks = {name: {field: getattr(eager.plans[name][0], field) == getattr(lazy.plans[name][0], field)
            for field in ("policy", "values", "counts")} for name in queries}
        pairs[kind] = {"eager_arm": eager_name, "lazy_arm": lazy_name,
            "model_field_equal": checks, "query_field_equal": query_checks,
            "all_equal": all(checks.values()) and all(all(row.values()) for row in query_checks.values())}
        if not checks["encoder_payload"]:
            pairs[kind]["unequal_encoder_payloads"] = {"eager": eager_payload, "lazy": lazy_payload}
    return {"all_equal": all(row["all_equal"] for row in pairs.values()), "pairs": pairs,
        "comparison_seconds": perf_counter() - started, "exact_equality_without_tolerance": True,
        "performed_before_exact_reference": True}


def _runtime_cost_and_work(frozen: Mapping[str, FrozenTargetArm],
                           queries: Mapping[str, Query]) -> dict[str, Any]:
    """Keep paired contemporary target costs and instrumentation scopes explicit."""
    result = {}
    for kind, (eager_name, lazy_name) in RUNTIME_PAIRS.items():
        eager, lazy = frozen[eager_name], frozen[lazy_name]
        eager_build = eager.inventory["actual_construction_seconds"]
        lazy_build = lazy.inventory["actual_construction_seconds"]
        eager_work = eager.diagnostics.get("work_counts", {})
        lazy_work = lazy.diagnostics.get("work_counts", {})
        workloads = {}
        for count in sorted({1, min(6, len(queries)), len(queries)}):
            names = tuple(queries)[:count]
            e = eager_build + math.fsum(eager.plans[name][1] for name in names)
            l = lazy_build + math.fsum(lazy.plans[name][1] for name in names)
            workloads[count] = {"eager_construction_plus_planning_seconds": e,
                "lazy_construction_plus_planning_seconds": l, "lazy_minus_eager_seconds": l - e}
        result[kind] = {"eager_arm": eager_name, "lazy_arm": lazy_name,
            "eager_actual_construction_seconds": eager_build, "lazy_actual_construction_seconds": lazy_build,
            "lazy_minus_eager_construction_seconds": lazy_build - eager_build,
            "eager_over_lazy_construction_factor": eager_build / lazy_build,
            "construction_plus_planning_by_query_count": workloads,
            "work_counts": {"eager": eager_work, "lazy": lazy_work},
            "lazy_minus_eager_common_work_counts": {key: lazy_work[key] - eager_work[key]
                for key in sorted(eager_work.keys() & lazy_work.keys())},
            "portable_bytes": {"eager": eager.inventory["portable_encoder_and_model_bytes"],
                "lazy": lazy.inventory["portable_encoder_and_model_bytes"]},
            "source_cost_excluded_from_target_only_delta": True,
            "independent_build_local_caches": True}
    return result


def matched_comparisons(private: Mapping[str, Any], active: Sequence[int], root: int,
                        queries: Mapping[str, Query]) -> dict[str, Any]:
    result = {}
    for arm in ARM_NAMES[1:]:
        result[arm] = {}
        for name in queries:
            full, candidate = private["full_state_empirical"][name], private[arm][name]
            extra = {state: full["actual"][state]["value"] - candidate["actual"][state]["value"]
                     for state in active}
            result[arm][name] = {
                "root_extra_regret_over_full_state": extra[root],
                "maximum_all_state_extra_regret_over_full_state": max(extra.values()),
                "minimum_all_state_extra_regret_over_full_state": min(extra.values()),
                "mean_all_state_extra_regret_over_full_state": math.fsum(extra.values()) / len(active),
                "states_worse_than_full_state": sum(value > NUMERIC_TOLERANCE for value in extra.values()),
                "states_better_than_full_state": sum(value < -NUMERIC_TOLERANCE for value in extra.values()),
                "action_disagreement_count": sum(candidate["policy"][state] != full["policy"][state] for state in active),
                "maximum_actual_component_difference_from_full_state": {component: max(abs(
                    candidate["actual"][state][component] - full["actual"][state][component])
                    for state in active) for component in COMPONENTS},
            }
    return result


def _adapted_vs_scratch(private: Mapping[str, Any], frozen: Mapping[str, FrozenTargetArm],
                        active: Sequence[int], root: int, queries: Mapping[str, Query]) -> dict[str, Any]:
    rows = {}
    for name in queries:
        scratch, adapted = private["target_scratch_encoder_v10"][name], private["target_adapted_encoder_v10"][name]
        gain = {state: adapted["actual"][state]["value"] - scratch["actual"][state]["value"] for state in active}
        rows[name] = {"root_adapted_value_gain_over_scratch": gain[root],
            "minimum_all_state_adapted_value_gain": min(gain.values()),
            "maximum_all_state_adapted_value_gain": max(gain.values()),
            "mean_all_state_adapted_value_gain": math.fsum(gain.values()) / len(active),
            "states_adapted_better": sum(value > NUMERIC_TOLERANCE for value in gain.values()),
            "states_adapted_worse": sum(value < -NUMERIC_TOLERANCE for value in gain.values()),
            "action_disagreement_count": sum(adapted["policy"][state] != scratch["policy"][state] for state in active),
            "root_adapted_minus_scratch_components": {component: adapted["actual"][root][component] - scratch["actual"][root][component]
                for component in COMPONENTS},
            "maximum_all_state_actual_component_difference": {component: max(abs(
                adapted["actual"][state][component] - scratch["actual"][state][component]) for state in active)
                for component in COMPONENTS}}
    scratch, adapted = frozen["target_scratch_encoder_v10"], frozen["target_adapted_encoder_v10"]
    return {"queries": rows,
        "adapted_minus_scratch_target_construction_seconds": adapted.inventory["actual_construction_seconds"] - scratch.inventory["actual_construction_seconds"],
        "target_construction_seconds": {"scratch": scratch.inventory["actual_construction_seconds"],
                                        "adapted": adapted.inventory["actual_construction_seconds"]},
        "target_construction_work_counts": {"scratch": scratch.diagnostics.get("work_counts", {}),
                                             "adapted": adapted.diagnostics.get("work_counts", {})},
        "active_cells": {"scratch": scratch.inventory["active_cells"], "adapted": adapted.inventory["active_cells"]},
        "source_cost_excluded_from_target_only_delta": True}


def _target_collision_labels(case_name: str, closure: DevelopmentClosure,
                             frozen: Mapping[str, FrozenTargetArm], references: Mapping[str, Any]
                             ) -> dict[str, Any]:
    result = {}
    for arm in TARGET_ARMS:
        states = set()
        for group in frozen[arm].diagnostics.get("groups", ()):
            for subgroup in group.get("original_output_codes", ()):
                witness = subgroup.get("identical_feature_collision_witness")
                if witness is not None:
                    states.update(witness[side]["source_state"] for side in ("left", "right")
                        if witness[side]["source_model"] == case_name)
        result[arm] = {state: {"target_case": case_name, "target_state": state,
            "board": closure.boards[state], "remaining_horizon": closure.model.layers[state],
            "queries": {name: {"exact_optimal_actions": reference["optimal_actions"][state],
                "exact_optimal_value": reference["values"][state]} for name, reference in references.items()}}
            for state in sorted(states)}
    return result


def run_comparison_v10(*, cases: Sequence[V7Case] | None = None,
                       cohort_roster: Mapping[str, Any] | None = None,
                       samples_per_row: int = SAMPLES_PER_ROW,
                       sample_seeds: Sequence[int] = SAMPLE_SEEDS,
                       max_nodes: int = 30_000,
                       fit_queries: Mapping[str, Query] | None = None,
                       probe_queries: Mapping[str, Query] | None = None,
                       progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    roster = build_cohort_roster_v10() if cohort_roster is None else cohort_roster
    declared = tuple(cases_v10() if cases is None else cases)
    scenarios = tuple(roster["scenarios"])
    bank_queries = dict(COMPARISON_QUERIES if fit_queries is None else fit_queries)
    probes = dict(PROBE_QUERIES if probe_queries is None else probe_queries)
    if (not declared or not bank_queries or not sample_seeds or samples_per_row < 1
            or bank_queries.keys() & probes.keys() or len({case.name for case in declared}) != len(declared)
            or len(set(sample_seeds)) != len(sample_seeds)):
        raise ValueError("nonempty unique cases/seeds, positive samples, and distinct query names are required")
    _validate_scenarios(declared, scenarios)
    queries = {**bank_queries, **probes}
    groups = {"FIT_BANK": tuple(bank_queries), **({"PROBES": tuple(probes)} if probes else {}), "ALL": tuple(queries)}
    case_by_name = {case.name: case for case in declared}
    started_all = perf_counter()
    closures, closure_records = {}, []
    for case in declared:
        started = perf_counter()
        record: dict[str, Any] = {"case": asdict(case)}
        try:
            closure = build_development_closure(horizon=case.horizon, max_nodes=max_nodes,
                                                boards={case.name: tuple(case.board)})
        except ValueError as error:
            if "complete closure exceeds max_nodes=" not in str(error):
                raise
            record.update(status="CLOSURE_BUDGET_EXCEEDED", reason=str(error),
                elapsed_seconds=perf_counter() - started,
                cost_note="Failed closure time retained; partial transition counts unavailable.")
        else:
            closures[case.name] = closure
            record.update(status="CLOSURE_COMPLETE", coverage={**closure.counts,
                "exact_closure_seconds": closure.elapsed_seconds,
                "complete_all_legal_actions_and_outcomes": True})
        closure_records.append(record)
        if progress:
            progress({"case": case.name, "status": record["status"],
                "completed_closures": len(closure_records), "total": len(declared)})
    by_closure_name = {row["case"]["name"]: row for row in closure_records}
    overlap = _pre_fit_overlap(declared, closures)
    overlap["training_exposure_counts_use_primary_v7_source_labels"] = True
    overlap["all_case_pair_overlaps_apply_to_every_declared_scenario"] = True
    scenario_records = []
    for scenario in scenarios:
        rows = [_record_for_scenario(case_by_name[name], scenario, by_closure_name[name])
                for name in scenario["evaluation_case_names"]]
        source_failure = any(name not in closures for name in scenario["source_case_names"])
        if source_failure:
            for row in rows:
                if row["status"] == "CLOSURE_COMPLETE":
                    row["status"] = "NOT_RUN_TRAINING_CLOSURE_INCOMPLETE"
        scenario_records.append({"scenario": dict(scenario), "cases": rows, "encoder_fits": [],
            "source_closure_failure": source_failure})
    union_sources = {name for scenario in scenarios for name in scenario["source_case_names"]}
    bank_records, compiled_model_example = [], None
    physical_draws = 0
    for seed_index, seed in enumerate(sample_seeds):
        empirical_bank, sampling_seconds = {}, {}
        def acquire(name: str) -> None:
            nonlocal physical_draws
            started = perf_counter()
            empirical = sample_model(closures[name].model, samples_per_row=samples_per_row, seed=seed)
            sampling_seconds[name] = perf_counter() - started
            empirical_bank[name] = empirical
            draws = len(empirical.rows) * samples_per_row
            physical_draws += draws
            bank_records.append({"case_name": name, "sample_seed": seed,
                "samples_per_row": samples_per_row, "empirical_rows": len(empirical.rows),
                "physical_draws": draws, "sampling_seconds": sampling_seconds[name],
                "available_as_source_in_at_least_one_scenario": name in union_sources})
        for case in declared:
            if case.name in union_sources and case.name in closures:
                acquire(case.name)
        scenario_fits = {}
        for scenario_record in scenario_records:
            if scenario_record["source_closure_failure"]:
                continue
            scenario = scenario_record["scenario"]
            names = scenario["source_case_names"]
            training = tuple(TrainingModel(name, empirical_bank[name], closures[name].boards) for name in names)
            started = perf_counter()
            fitted = fit_constraint_encoder(training)
            fit_seconds = perf_counter() - started
            scenario_fits[scenario["name"]] = fitted
            started = perf_counter()
            payload = fitted.encoder.to_payload()
            size = len(json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8"))
            inventory_seconds = perf_counter() - started
            scenario_record["encoder_fits"].append({"sample_seed": seed,
                "source_case_names": list(names), "source_case_names_received_by_fit": [item.name for item in training],
                "source_empirical_draws": sum(len(empirical_bank[name].rows) * samples_per_row for name in names),
                "source_sampling_seconds": math.fsum(sampling_seconds[name] for name in names),
                "source_closure_seconds": math.fsum(closures[name].elapsed_seconds for name in names),
                "source_data_are_reused_bank_subset": True, "queries_used_in_source_fit": [],
                "amortization_declared_case_count": len(scenario["evaluation_case_names"]),
                "encoder_fit_seconds": fit_seconds, "encoder": payload,
                "encoder_bytes_once_per_fit": size, "encoder_inventory_serialization_seconds": inventory_seconds,
                "diagnostics": fitted.diagnostics})
            if progress:
                progress({"scenario": scenario["name"], "sample_seed": seed,
                    "status": "SOURCE_ENCODER_FROZEN", "source_case_names": names,
                    "source_constraint_fit_satisfied": fitted.diagnostics.get("all_training_predictive_constraints_satisfied")})
        for case in declared:
            if case.name not in empirical_bank and case.name in closures:
                acquire(case.name)
        for scenario_index, scenario_record in enumerate(scenario_records):
            if scenario_record["source_closure_failure"]:
                continue
            scenario = scenario_record["scenario"]
            fitted = scenario_fits[scenario["name"]]
            fit_record = scenario_record["encoder_fits"][-1]
            for case_index, record in enumerate(scenario_record["cases"]):
                name = record["case"]["name"]
                if name not in closures:
                    continue
                closure, empirical = closures[name], empirical_bank[name]
                frozen = {}
                offset = (seed_index + scenario_index + case_index) % 7
                order = ARM_NAMES[:7][offset:] + ARM_NAMES[:7][:offset] + (ARM_NAMES[-1],)
                for arm in order:
                    frozen[arm] = _freeze_arm(arm, empirical, closure, fitted.encoder, queries,
                        case_name=name, adapted=frozen.get("target_adapted_encoder_v10"))
                if frozen["target_adapted_encoder_v10"].compiled.state_to_cell != frozen["action_outcome_shuffle_adapted_v10"].compiled.state_to_cell:
                    raise AssertionError("shuffled control changed the already-adapted partition")
                semantic_check = _runtime_semantic_equivalence(frozen, queries)
                started = perf_counter()
                exact = compile_full_state(closure.model)
                exact_build_seconds = perf_counter() - started
                references = _reference(closure, exact, queries)
                active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
                root = closure.model.roots[0]
                run: dict[str, Any] = {"sample_seed": seed, "empirical_model_sample_count": 0,
                    "empirical_model_reused_from_bank": True, "empirical_rows": len(empirical.rows),
                    "logical_current_case_draws": len(empirical.rows) * samples_per_row,
                    "additional_physical_draws_in_scenario": 0, "samples_per_row": samples_per_row,
                    "sampling_seconds_reused_from_bank": sampling_seconds[name],
                    "current_case_is_source_encoder_training_source": name in scenario["source_case_names"],
                    "target_data_used_for_adaptation_and_scratch_fit": True,
                    "queries_used_in_target_rule_construction": [], "measured_arm_order": order, "arms": {},
                    "eager_lazy_semantic_equivalence": semantic_check,
                    "exact_reference_cost": {"full_state_construction_seconds": exact_build_seconds,
                        "planning_seconds": math.fsum(row["planning_seconds"] for row in references.values()),
                        "action_labeling_seconds": math.fsum(row["all_state_action_labeling_seconds"] for row in references.values())}}
                private = {}
                for arm in ARM_NAMES:
                    fit_seconds = fit_record["encoder_fit_seconds"] if arm in SOURCE_USING_ARMS else 0.0
                    source_extra = (fit_seconds + math.fsum(closures[source].elapsed_seconds + sampling_seconds[source]
                        for source in scenario["source_case_names"] if source != name)) if arm in SOURCE_USING_ARMS else 0.0
                    run["arms"][arm], private[arm] = _audit_arm(frozen[arm], closure, queries, references, groups,
                        sampling_seconds[name], fit_seconds / len(scenario["evaluation_case_names"]), source_extra)
                    run["arms"][arm]["source_encoder_fit_reused"] = arm in SOURCE_USING_ARMS
                started = perf_counter()
                run["matched_comparisons"] = matched_comparisons(private, active, root, queries)
                run["adapted_vs_scratch"] = _adapted_vs_scratch(private, frozen, active, root, queries)
                run["eager_lazy_cost_and_work"] = _runtime_cost_and_work(frozen, queries)
                run["worst_encoding_added_loss_by_arm"] = {arm: _worst_encoding_added_loss(
                    {"full_state_empirical": private["full_state_empirical"], "frozen_rule_encoder": private[arm]},
                    closure, queries, frozen[arm].encoder) for arm in ENCODER_ARMS}
                run["encoder_cell_conflicts_by_arm"] = {arm: _cell_conflicts(frozen[arm], closure,
                    references, frozen[arm].encoder) for arm in ENCODER_ARMS}
                run["target_feature_collision_exact_labels_by_arm"] = _target_collision_labels(name, closure, frozen, references)
                run["posthoc_matched_loss_cell_conflicts_and_witness_features_seconds"] = perf_counter() - started
                record["sampled_runs"].append(run)
                if "exact_query_references" not in record:
                    record["exact_query_references"] = {query_name: {"root_q_values": row["root_q_values"],
                        "root_optimal_actions": row["optimal_actions"][root], "root_optimal_value": row["values"][root]}
                        for query_name, row in references.items()}
                    record["exact_all_state_required_switches"] = _switches(references, active, groups)
                    record["exact_root_required_switches"] = _switches(references, closure.model.roots, groups)
                if scenario["name"] == "PRIMARY_V7_SPLIT" and name == "v6_spawn_edge_rescue_2" and seed == 832101:
                    started = perf_counter()
                    candidate = frozen["target_adapted_encoder_v10"]
                    compiled_model_example = {"scenario": scenario["name"], "case_name": name, "sample_seed": seed,
                        "arm": "target_adapted_encoder_v10",
                        "artifact": freeze_artifact_payload(candidate.encoder, candidate.compiled, candidate.code_to_cell,
                            example_board=case_by_name[name].board, example_horizon=case_by_name[name].horizon),
                        "queries": {query_name: {"query": asdict(query),
                            "expected_root_action": candidate.plans[query_name][0].policy[candidate.compiled.state_to_cell[root]],
                            "expected_root_value": candidate.plans[query_name][0].values[candidate.compiled.state_to_cell[root]]}
                            for query_name, query in queries.items()},
                        "serialization_seconds": perf_counter() - started}
                record["status"] = "COMPLETE"
                if progress:
                    progress({"scenario": scenario["name"], "case": name, "sample_seed": seed,
                        "status": "SAMPLE_COMPLETE", "active_states": len(active),
                        "adapted_active_cells": frozen["target_adapted_encoder_v10"].inventory["active_cells"],
                        "eager_lazy_semantics_equal": semantic_check["all_equal"],
                        "adapted_target_constraints_satisfied": frozen["target_adapted_encoder_v10"].diagnostics.get(
                            "all_target_predictive_constraints_satisfied")})
    for scenario_record in scenario_records:
        records = scenario_record["cases"]
        scenario_record["summary_by_split"] = {split: _summarize(records if split == "ALL" else [row for row in records
            if row["case"]["split"] == split], groups) for split in ("ALL", *sorted({row["case"]["split"] for row in records}))}
        scenario_record["status"] = "DEVELOPMENT_COMPLETE" if all(row["status"] == "COMPLETE" for row in records) else "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES"
    lofo_targets = [row for scenario_record in scenario_records if scenario_record["scenario"]["target_family"] is not None
                    for row in scenario_record["cases"] if row["case"]["split"] == "FAMILY_HELD_OUT"]
    all_runs = [run for scenario_record in scenario_records for row in scenario_record["cases"] for run in row["sampled_runs"]]
    fits = [fit for scenario_record in scenario_records for fit in scenario_record["encoder_fits"]]
    return {
        "schema": "acfqp.controlled_predictive_encoder_comparison.v10",
        "status": "DEVELOPMENT_COMPLETE" if all(s["status"] == "DEVELOPMENT_COMPLETE" for s in scenario_records)
            else "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES",
        "scientific_gate": "NOT_A_FORMAL_GATE", "case_count": len(declared), "scenario_count": len(scenarios),
        "declared_scenario_case_count_per_seed": sum(len(s["evaluation_case_names"]) for s in scenarios),
        "completed_scenario_case_seed_runs": len(all_runs),
        "eager_lazy_semantic_equivalence": {"all_equal": all(run["eager_lazy_semantic_equivalence"]["all_equal"] for run in all_runs),
            "compared_run_count": len(all_runs), "compared_target_build_pair_count": 2 * len(all_runs),
            "failed_run_count": sum(not run["eager_lazy_semantic_equivalence"]["all_equal"] for run in all_runs)},
        "settings": {"samples_per_row": samples_per_row, "sample_seeds": list(sample_seeds),
            "max_nodes": max_nodes, "queries": {name: asdict(query) for name, query in queries.items()},
            "query_groups": groups, "queries_used_in_source_or_target_fit": [], "arm_names": ARM_NAMES,
            "runtime": "concurrent_v9_eager_and_v10_build_local_lazy_features; source_fit_and_frozen_arm_v8_unchanged"},
        "cohort_roster": roster, "closure_records": closure_records, "pre_fit_closure_overlap": overlap,
        "empirical_bank": bank_records, "scenarios": scenario_records,
        "lofo_target_aggregate": _summarize(lofo_targets, groups), "compiled_model_example": compiled_model_example,
        "accounting": {
            "actual_physical_draws": physical_draws, "bank_model_count": len(bank_records),
            "scenario_case_logical_draws_including_repeated_bank_reads": sum(run["logical_current_case_draws"] for run in all_runs),
            "scenario_additional_physical_draws": sum(run["additional_physical_draws_in_scenario"] for run in all_runs),
            "actual_sampling_seconds_once_per_bank_model": math.fsum(row["sampling_seconds"] for row in bank_records),
            "actual_completed_closure_seconds_once_per_case": math.fsum(closure.elapsed_seconds for closure in closures.values()),
            "actual_failed_closure_seconds": math.fsum(row["elapsed_seconds"] for row in closure_records if row["status"] == "CLOSURE_BUDGET_EXCEEDED"),
            "source_encoder_fit_count": len(fits),
            "target_fit_and_compile_count_by_arm": {arm: len(all_runs) for arm in TARGET_ARMS},
            "actual_source_encoder_fit_seconds": math.fsum(row["encoder_fit_seconds"] for row in fits),
            "actual_eager_lazy_semantic_comparison_seconds": math.fsum(
                run["eager_lazy_semantic_equivalence"]["comparison_seconds"] for run in all_runs),
            "actual_posthoc_matched_loss_conflict_and_work_diagnostics_seconds": math.fsum(
                run["posthoc_matched_loss_cell_conflicts_and_witness_features_seconds"] for run in all_runs),
            "actual_inventory_serialization_seconds": math.fsum(
                arm["inventory"]["inventory_serialization_seconds"] + arm["inventory"].get("portable_inventory_serialization_seconds", 0.0)
                for run in all_runs for arm in run["arms"].values()) + math.fsum(
                fit["encoder_inventory_serialization_seconds"] for fit in fits),
            "actual_eight_arm_target_build_plan_forecast_audit_seconds": math.fsum(
                arm["inventory"]["actual_construction_seconds"] + arm["measured_cumulative_workloads"][-1]["cumulative_planning_seconds"]
                + arm["measured_cumulative_workloads"][-1]["cumulative_forecast_seconds"]
                + arm["measured_cumulative_workloads"][-1]["cumulative_ground_audit_seconds"]
                for run in all_runs for arm in run["arms"].values()),
            "control_reused_adaptation_setup_seconds_attributed_but_not_physically_repeated": math.fsum(
                run["arms"]["action_outcome_shuffle_adapted_v10"]["inventory"]["reused_target_adaptation_setup_seconds_attributed_to_workload"]
                for run in all_runs),
            "bank_reuse": "Each original case/seed is sampled once. Source fits, target adaptation, direct target fitting, repeated scenarios and controls read that bank without additional sampling.",
            "fit_access": "The union of scenario source kernels is acquired first; each source encoder receives only its own declared subset. After source encoders freeze, target adaptation and scratch fitting intentionally receive the current target empirical model. No queries or exact optimal labels enter either operation.",
            "source_costs": "The unchanged V8 source fit per scenario/seed is amortized over the declared 16 or 6 cases for frozen, V9-adapted, V10-adapted and adapted-control alternatives. Both scratch alternatives have no source fit. Standalone additional source acquisition excludes the current source case's own acquisition, already charged in target cost.",
            "control_costs": "The control compiles shuffled rows using the already-adapted rule; it never adapts on shuffled observations. Its workload construction includes the full reused adapted build plus its actual shuffle-and-compile work. Actual campaign totals use actual_construction_seconds and charge that setup only to the build that performed it.",
            "target_costs": "Scratch and adaptation construction timings include target profiling, signature construction, rule work, constraint diagnostics and one final compilation. Source-conditioned adaptation is compared directly with target scratch fitting on the same kernel, including target construction work counts and all-state true policy differences.",
            "audit_order": "The first seven arms rotate their construction order; the dependent control runs last. All eight ten-query policies freeze before exact eager/lazy equality checks, exact references and true fixed-policy audits. Semantic mismatch flags remain in results. Unresolved constraints never filter cases or methods.",
            "scope": "Split labels refer to source fitting only. Target adaptation uses evaluation observations by design and is not frozen-rule or zero-shot transfer. Shared current observations do not imply equal source use or equal total cost.",
            "cache_scope": "Every V10 target build and control compilation constructs its own empty cache. No cache is shared with any other arm, scenario, case or seed. Cache entries are temporary storage counts, not Python process RAM bytes.",
            "sampling_stream": "Unchanged sample_model, deterministic per case/seed, N=256 only. Physical bank observations and repeated logical use are reported separately.",
        },
        "limitations": [
            "All roots and mechanism families were already exposed; source repetitions, sample seeds and queries do not constitute independent confirmation.",
            "Target empirical data now modify the rule. Target constraint satisfaction concerns the sampled kernel, not true dynamics, new boards or arbitrary query weights.",
            "Each target still supplies a complete finite closure and samples every action row. No sampling-efficiency or zero-shot dynamics claim follows.",
            "Adaptation retains source partition boundaries; any extra cells and rule cost relative to direct target fitting remain part of the comparison.",
            "Closure failures and unresolved target feature collisions remain in the fixed cohort. No outcome-based tuning or replacement is performed.",
            "Eager/lazy comparisons are exact and concurrent. Timings from older campaigns do not establish causal speed differences. Portable-model reload proves execution equivalence only. U005 remains failed; U006 and the deferred V2 cohort are not executed.",
        ],
        "all_declared_cases_retained": True, "u006_assurance_started": False,
        "deferred_v2_24_case_cohort_executed": False, "elapsed_seconds": perf_counter() - started_all,
    }


__all__ = ("ARM_NAMES", "ENCODER_ARMS", "run_comparison_v10", "matched_comparisons")
