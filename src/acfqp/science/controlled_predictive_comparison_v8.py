"""V8 source-constrained fitting and matched six-arm development comparison.

One empirical bank is reused across the primary V7 split and three complete
mechanism-family holdouts. Only the declared source subset reaches each fit.
All case policies are frozen before exact optimal labels audit that case.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, replace
import json
import math
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from .controlled_predictive_2048_v1 import DevelopmentClosure, build_development_closure
from .controlled_predictive_cohort_v7 import V7Case
from .controlled_predictive_cohort_v8 import build_cohort_roster_v8, cases_v8
from .controlled_predictive_comparison_v3 import (
    COMPARISON_QUERIES, COMPONENTS, NUMERIC_TOLERANCE, PROBE_QUERIES, SAMPLE_SEEDS,
    _fit, _reference, _summarize, _switches,
)
from .controlled_predictive_comparison_v7 import (
    FrozenArm, _audit_arm, _cell_conflicts, _pre_fit_overlap, _worst_encoding_added_loss,
)
from .controlled_predictive_encoder_io_v7 import artifact_inventory, freeze_artifact_payload
from .controlled_predictive_encoder_runtime_v8 import RuntimeEncoder, compile_encoded
from .controlled_predictive_encoder_v7 import EncoderFit, TrainingModel, fit_encoder
from .controlled_predictive_encoder_v8 import fit_constraint_encoder, fit_uncapped_sse_encoder
from .controlled_predictive_quotient_v1 import (
    CompiledModel, FiniteModel, Query, action_outcome_shuffle,
    build_quotient, compile_full_state, plan, sample_model,
)


ARM_NAMES = ("full_state_empirical", "exact_empirical_quotient", "v7_fixed_rule_encoder",
             "uncapped_sse_encoder", "frozen_rule_encoder", "action_outcome_shuffle_encoder")
LEARNER_NAMES = ARM_NAMES[2:5]
SAMPLES_PER_ROW = 256


def _fit_learners(training: Sequence[TrainingModel]) -> tuple[dict[str, EncoderFit], dict[str, Any]]:
    """This interface deliberately accepts no query, target model, or oracle."""
    fitted, records = {}, {}
    for name, fitter in (
        ("v7_fixed_rule_encoder", lambda items: fit_encoder(items, max_depth=4, min_leaf=2)),
        ("uncapped_sse_encoder", fit_uncapped_sse_encoder),
        ("frozen_rule_encoder", fit_constraint_encoder),
    ):
        started = perf_counter()
        result = fitter(tuple(training))
        if name == "v7_fixed_rule_encoder":
            result = EncoderFit(RuntimeEncoder(result.encoder.trees), result.diagnostics)
        fit_seconds = perf_counter() - started
        fitted[name] = result
        started = perf_counter()
        payload = result.encoder.to_payload()
        size = len(json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8"))
        records[name] = {"encoder_fit_seconds": fit_seconds, "encoder": payload,
            "encoder_bytes_once_per_fit": size,
            "encoder_inventory_serialization_seconds": perf_counter() - started,
            "diagnostics": result.diagnostics, "queries_used_in_fit": [],
            "source_case_names_received_by_fit": [item.name for item in training]}
    return fitted, records


def _freeze_arm(name: str, empirical: FiniteModel, closure: DevelopmentClosure,
                encoder: Any, queries: Mapping[str, Query]) -> FrozenArm:
    encoded = None
    shuffle_seconds = 0.0
    if name == "full_state_empirical":
        builder = lambda: compile_full_state(empirical)
    elif name == "exact_empirical_quotient":
        builder = lambda: build_quotient(empirical)
    else:
        kernel = empirical
        if name == "action_outcome_shuffle_encoder":
            started = perf_counter()
            kernel = action_outcome_shuffle(empirical)
            shuffle_seconds = perf_counter() - started
        def builder() -> CompiledModel:
            nonlocal encoded
            encoded = compile_encoded(kernel, closure.boards, encoder)
            return encoded.compiled
    compiled, inventory, _ = _fit(builder, closure)
    inventory["construction_seconds"] += shuffle_seconds
    inventory["action_shuffle_seconds_included_in_construction"] = shuffle_seconds
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
    return FrozenArm(compiled, inventory, plans,
        encoded.diagnostics if encoded is not None else None,
        encoded.code_to_cell if encoded is not None else None)


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


def _record_for_scenario(case: V7Case, scenario: Mapping[str, Any], closure_record: Mapping[str, Any]
                         ) -> dict[str, Any]:
    record = {"case": asdict(replace(case, split=scenario["case_splits"][case.name],
                                   role=scenario["case_splits"][case.name])),
              "references": {}, "sampled_runs": []}
    record.update({key: value for key, value in closure_record.items() if key != "case"})
    return record


def _training_collision_labels(case_name: str, closure: DevelopmentClosure,
                               fitted: Mapping[str, EncoderFit], references: Mapping[str, Any]
                               ) -> dict[str, Any]:
    """Annotate retained training feature-collision examples using existing audits."""
    result = {}
    for learner in ("uncapped_sse_encoder", "frozen_rule_encoder"):
        states = set()
        for group in fitted[learner].diagnostics.get("groups", ()):
            witness = group.get("identical_feature_collision_witness")
            if witness is not None:
                states.update(witness[side]["source_state"] for side in ("left", "right")
                    if witness[side]["source_model"] == case_name)
        result[learner] = {state: {"source_model": case_name, "source_state": state,
            "board": closure.boards[state], "remaining_horizon": closure.model.layers[state],
            "queries": {name: {"exact_optimal_actions": reference["optimal_actions"][state],
                "exact_optimal_value": reference["values"][state]}
                for name, reference in references.items()}}
            for state in sorted(states)}
    return result


def _validate_scenarios(cases: Sequence[V7Case], scenarios: Sequence[Mapping[str, Any]]) -> None:
    names = {case.name for case in cases}
    by_name = {case.name: case for case in cases}
    if not scenarios or len({scenario["name"] for scenario in scenarios}) != len(scenarios):
        raise ValueError("nonempty scenarios must have unique names")
    for scenario in scenarios:
        source = scenario["source_case_names"]
        evaluation = scenario["evaluation_case_names"]
        if (not source or not evaluation or len(set(source)) != len(source)
                or len(set(evaluation)) != len(evaluation)
                or not set(source) <= set(evaluation) <= names
                or set(scenario["case_splits"]) != set(evaluation)):
            raise ValueError("scenario sources, evaluations and split labels must identify the declared cases")
        if any(scenario["case_splits"][name] != "TRAIN" for name in source):
            raise ValueError("every source must be labeled TRAIN in its scenario")
        family = scenario["target_family"]
        if family is not None and (any(by_name[name].family == family for name in source)
                or any(by_name[name].family != family for name in evaluation if name not in source)):
            raise ValueError("a LOFO scenario cannot train on or mix its held-out target family")


def run_comparison_v8(*, cases: Sequence[V7Case] | None = None,
                       cohort_roster: Mapping[str, Any] | None = None,
                       samples_per_row: int = SAMPLES_PER_ROW,
                       sample_seeds: Sequence[int] = SAMPLE_SEEDS,
                       max_nodes: int = 30_000,
                       fit_queries: Mapping[str, Query] | None = None,
                       probe_queries: Mapping[str, Query] | None = None,
                       progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    roster = build_cohort_roster_v8() if cohort_roster is None else cohort_roster
    declared = tuple(cases_v8() if cases is None else cases)
    scenarios = tuple(roster["scenarios"])
    bank_queries = dict(COMPARISON_QUERIES if fit_queries is None else fit_queries)
    probes = dict(PROBE_QUERIES if probe_queries is None else probe_queries)
    if (not declared or not bank_queries or not sample_seeds or samples_per_row < 1
            or bank_queries.keys() & probes.keys()
            or len({case.name for case in declared}) != len(declared)
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
            fitted, fit_records = _fit_learners(training)
            scenario_fits[scenario["name"]] = fitted
            fit_record = {"sample_seed": seed, "source_case_names": list(names),
                "source_empirical_draws": sum(len(empirical_bank[name].rows) * samples_per_row for name in names),
                "source_sampling_seconds": math.fsum(sampling_seconds[name] for name in names),
                "source_closure_seconds": math.fsum(closures[name].elapsed_seconds for name in names),
                "source_data_are_reused_bank_subset": True,
                "amortization_declared_case_count": len(scenario["evaluation_case_names"]),
                "learners": fit_records}
            scenario_record["encoder_fits"].append(fit_record)
            if progress:
                progress({"scenario": scenario["name"], "sample_seed": seed,
                    "status": "THREE_ENCODERS_FROZEN", "source_case_names": names,
                    "constraint_fit_satisfied": fitted["frozen_rule_encoder"].diagnostics.get(
                        "all_training_predictive_constraints_satisfied")})
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
                offset = (seed_index + scenario_index + case_index) % len(ARM_NAMES)
                order = ARM_NAMES[offset:] + ARM_NAMES[:offset]
                for arm in order:
                    learner = "frozen_rule_encoder" if arm == "action_outcome_shuffle_encoder" else arm
                    encoder = fitted[learner].encoder if learner in fitted else None
                    frozen[arm] = _freeze_arm(arm, empirical, closure, encoder, queries)
                if frozen["frozen_rule_encoder"].compiled.state_to_cell != frozen["action_outcome_shuffle_encoder"].compiled.state_to_cell:
                    raise AssertionError("action outcome shuffle changed the frozen constraint-encoder partition")
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
                    "current_case_is_training_source": name in scenario["source_case_names"],
                    "measured_arm_order": order, "arms": {},
                    "exact_reference_cost": {"full_state_construction_seconds": exact_build_seconds,
                        "planning_seconds": math.fsum(row["planning_seconds"] for row in references.values()),
                        "action_labeling_seconds": math.fsum(row["all_state_action_labeling_seconds"] for row in references.values())}}
                private = {}
                for arm in ARM_NAMES:
                    learner = "frozen_rule_encoder" if arm == "action_outcome_shuffle_encoder" else arm
                    fit_seconds = fit_record["learners"][learner]["encoder_fit_seconds"] if learner in fitted else 0.0
                    source_extra = (fit_seconds + math.fsum(closures[source].elapsed_seconds + sampling_seconds[source]
                        for source in scenario["source_case_names"] if source != name)) if learner in fitted else 0.0
                    run["arms"][arm], private[arm] = _audit_arm(frozen[arm], closure, queries, references, groups,
                        sampling_seconds[name], fit_seconds / len(scenario["evaluation_case_names"]), source_extra)
                    run["arms"][arm]["source_fit_learner"] = learner if learner in fitted else None
                started = perf_counter()
                run["matched_comparisons"] = matched_comparisons(private, active, root, queries)
                run["worst_encoding_added_loss_by_arm"] = {
                    arm: _worst_encoding_added_loss({"full_state_empirical": private["full_state_empirical"],
                        "frozen_rule_encoder": private[arm]}, closure, queries, fitted[arm].encoder)
                    for arm in LEARNER_NAMES}
                run["encoder_cell_conflicts_by_arm"] = {arm: _cell_conflicts(frozen[arm], closure,
                    references, fitted[arm].encoder) for arm in LEARNER_NAMES}
                run["training_feature_collision_exact_labels_by_arm"] = _training_collision_labels(
                    name, closure, fitted, references) if name in scenario["source_case_names"] else {}
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
                    candidate = frozen["frozen_rule_encoder"]
                    compiled_model_example = {"scenario": scenario["name"], "case_name": name, "sample_seed": seed,
                        "artifact": freeze_artifact_payload(fitted["frozen_rule_encoder"].encoder, candidate.compiled,
                            candidate.code_to_cell, example_board=case_by_name[name].board,
                            example_horizon=case_by_name[name].horizon),
                        "queries": {query_name: {"query": asdict(query),
                            "expected_root_action": candidate.plans[query_name][0].policy[candidate.compiled.state_to_cell[root]],
                            "expected_root_value": candidate.plans[query_name][0].values[candidate.compiled.state_to_cell[root]]}
                            for query_name, query in queries.items()},
                        "serialization_seconds": perf_counter() - started}
                record["status"] = "COMPLETE"
                if progress:
                    progress({"scenario": scenario["name"], "case": name, "sample_seed": seed,
                        "status": "SAMPLE_COMPLETE", "active_states": len(active),
                        "constraint_active_cells": frozen["frozen_rule_encoder"].inventory["active_cells"]})
    for scenario_record in scenario_records:
        records = scenario_record["cases"]
        scenario_record["summary_by_split"] = {split: _summarize(records if split == "ALL" else [row for row in records
            if row["case"]["split"] == split], groups) for split in ("ALL", *sorted({row["case"]["split"] for row in records}))}
        scenario_record["status"] = "DEVELOPMENT_COMPLETE" if all(row["status"] == "COMPLETE" for row in records) else "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES"
    lofo_targets = [row for scenario_record in scenario_records if scenario_record["scenario"]["target_family"] is not None
                    for row in scenario_record["cases"] if row["case"]["split"] == "FAMILY_HELD_OUT"]
    all_runs = [run for scenario_record in scenario_records for row in scenario_record["cases"] for run in row["sampled_runs"]]
    fit_records = [fit for scenario_record in scenario_records for fit in scenario_record["encoder_fits"]]
    return {
        "schema": "acfqp.controlled_predictive_encoder_comparison.v8",
        "status": "DEVELOPMENT_COMPLETE" if all(s["status"] == "DEVELOPMENT_COMPLETE" for s in scenario_records)
            else "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES",
        "scientific_gate": "NOT_A_FORMAL_GATE", "case_count": len(declared),
        "scenario_count": len(scenarios),
        "declared_scenario_case_count_per_seed": sum(len(s["evaluation_case_names"]) for s in scenarios),
        "completed_scenario_case_seed_runs": len(all_runs),
        "settings": {"samples_per_row": samples_per_row, "sample_seeds": list(sample_seeds),
            "max_nodes": max_nodes, "queries": {name: asdict(query) for name, query in queries.items()},
            "query_groups": groups, "queries_used_in_encoder_fit": [],
            "arm_names": ARM_NAMES, "v7_max_depth": 4, "v7_min_leaf": 2,
            "runtime": "shared_v8_terminal_aware_v7_equivalent_active_features"},
        "cohort_roster": roster, "closure_records": closure_records,
        "pre_fit_closure_overlap": overlap, "empirical_bank": bank_records,
        "scenarios": scenario_records,
        "lofo_target_aggregate": _summarize(lofo_targets, groups),
        "compiled_model_example": compiled_model_example,
        "accounting": {
            "actual_physical_draws": physical_draws, "bank_model_count": len(bank_records),
            "scenario_case_logical_draws_including_repeated_bank_reads": sum(run["logical_current_case_draws"] for run in all_runs),
            "scenario_additional_physical_draws": sum(run["additional_physical_draws_in_scenario"] for run in all_runs),
            "actual_sampling_seconds_once_per_bank_model": math.fsum(row["sampling_seconds"] for row in bank_records),
            "actual_completed_closure_seconds_once_per_case": math.fsum(closure.elapsed_seconds for closure in closures.values()),
            "actual_failed_closure_seconds": math.fsum(row["elapsed_seconds"] for row in closure_records if row["status"] == "CLOSURE_BUDGET_EXCEEDED"),
            "encoder_fit_count": sum(len(row["learners"]) for row in fit_records),
            "scenario_seed_source_fit_groups": len(fit_records),
            "actual_encoder_fit_seconds": math.fsum(learner["encoder_fit_seconds"] for row in fit_records for learner in row["learners"].values()),
            "actual_six_arm_target_build_plan_forecast_audit_seconds": math.fsum(
                arm["inventory"]["construction_seconds"] + arm["measured_cumulative_workloads"][-1]["cumulative_planning_seconds"]
                + arm["measured_cumulative_workloads"][-1]["cumulative_forecast_seconds"]
                + arm["measured_cumulative_workloads"][-1]["cumulative_ground_audit_seconds"]
                for run in all_runs for arm in run["arms"].values()),
            "bank_reuse": "Each original case/seed is sampled once. The same immutable empirical model objects supply every relevant scenario and all six arms. Source reads, repeated scenario costs, and the shuffled kernel do not create new observations.",
            "fit_access": "The union of source kernels is acquired first; each learner receives only its scenario's source subset. A withheld root can already exist in the bank because another scenario uses it as a source. Bank availability is not fit access. All scenario fits finish before remaining nonsource kernels are sampled and before exact query labels are produced for that seed.",
            "source_costs": "Each learner fit is charged once per scenario/seed and amortized over the declared 16 or 6 case workload. Shuffle reuses the constraint fit. Source acquisition is a subset of bank acquisition; own TRAIN current-case acquisition is excluded from standalone additional source cost. Full-state and exact-quotient baselines have source data available but do not fit a transferable rule.",
            "matching": "Current empirical samples are identical across arms and reused across scenarios. The source pools and fitting computations differ. This is neither equal total cost nor zero-shot target dynamics transfer.",
            "audit_order": "All six current-case ten-query policies freeze before exact optimal labels and fixed-policy audits. No exact label or query enters any source fit. The unresolved-constraint diagnosis never filters a learner or changes the cohort.",
            "timing": "All encoded arms use the same V8 runtime. Old V7 wall-clock timings are not a simultaneous runtime comparison. Scenario workload tables include shared bank/closure costs for a standalone use, while actual campaign totals charge each physical operation once.",
            "sampling_stream": "The unchanged sample_model uses one deterministic global Random per case/seed over sorted rows; N=256 only, no new sample-size scan.",
        },
        "limitations": [
            "All roots and mechanism families were already exposed. PRIMARY and LOFO are reported separately; source repetitions and seeds are not independent confirmations.",
            "Rules use source empirical signatures, which remain subject to sampling error. A training-constraint result is not a certificate for true kernels, unseen feature combinations, or arbitrary query weights.",
            "Every target's covered state/action transition rows are still sampled. The transferred object is an executable coding rule, not a zero-shot dynamics model.",
            "Declared closure failures and unresolved training constraints remain in the records; no candidate selection, feature changes or replacement roots are performed.",
            "The portable example and additional-query reload concern model execution only, not new-query true optimality.",
            "U005 remains scientifically failed; U006 and the original deferred V2 cohort are not executed.",
        ],
        "all_declared_cases_retained": True, "u006_assurance_started": False,
        "deferred_v2_24_case_cohort_executed": False, "elapsed_seconds": perf_counter() - started_all,
    }


__all__ = ("ARM_NAMES", "LEARNER_NAMES", "run_comparison_v8", "matched_comparisons")
