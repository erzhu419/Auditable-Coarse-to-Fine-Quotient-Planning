"""Frozen board-rule encoder comparison on the exposed V6 finite cohort.

Only the three training empirical kernels enter tree fitting. Every other
sampled kernel is constructed after fitting, and all four policies are frozen
before exact labels audit that case. Shared target samples do not imply equal
source information or total construction cost.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from itertools import combinations
import json
import math
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from .controlled_predictive_2048_v1 import DevelopmentClosure, build_development_closure
from .controlled_predictive_cohort_v6 import board_symmetries
from .controlled_predictive_comparison_v3 import (
    COMPARISON_QUERIES, COMPONENTS, NUMERIC_TOLERANCE, PROBE_QUERIES, SAMPLE_SEEDS,
    _evaluate, _fit, _reference, _summarize, _switches,
)
from .controlled_predictive_comparison_v4 import _compact_arm
from .controlled_predictive_encoder_v7 import (
    FEATURE_NAMES, TrainingModel, board_features, compile_encoded, fit_encoder,
)
from .controlled_predictive_quotient_v1 import (
    CompiledModel, FiniteModel, Plan, Query, action_outcome_shuffle,
    build_quotient, compile_full_state, plan, sample_model,
)


ARM_NAMES = ("full_state_empirical", "exact_empirical_quotient",
             "frozen_rule_encoder", "action_outcome_shuffle_encoder")
SAMPLES_PER_ROW = 256


@dataclass
class FrozenArm:
    compiled: CompiledModel
    inventory: dict[str, Any]
    plans: dict[str, tuple[Plan, float]]
    diagnostics: dict[str, Any] | None
    code_to_cell: dict[Any, int] | None


def _freeze_arm(name: str, empirical: FiniteModel, closure: DevelopmentClosure,
                encoder: Any, queries: Mapping[str, Query]) -> FrozenArm:
    encoded = None
    shuffled_seconds = 0.0
    if name == "full_state_empirical":
        builder = lambda: compile_full_state(empirical)
    elif name == "exact_empirical_quotient":
        builder = lambda: build_quotient(empirical)
    else:
        kernel = empirical
        if name == "action_outcome_shuffle_encoder":
            started = perf_counter()
            kernel = action_outcome_shuffle(empirical)
            shuffled_seconds = perf_counter() - started
        def builder() -> CompiledModel:
            nonlocal encoded
            encoded = compile_encoded(kernel, closure.boards, encoder)
            return encoded.compiled
    compiled, inventory, _ = _fit(builder, closure)
    inventory["construction_seconds"] += shuffled_seconds
    inventory["action_shuffle_seconds_included_in_construction"] = shuffled_seconds
    if encoded is not None:
        from .controlled_predictive_encoder_io_v7 import artifact_inventory, freeze_artifact_payload
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
                     encoded.diagnostics if encoded else None,
                     encoded.code_to_cell if encoded else None)


def _audit_arm(frozen: FrozenArm, closure: DevelopmentClosure,
               queries: Mapping[str, Query], references: Mapping[str, Any],
               groups: Mapping[str, Sequence[str]], sampling_seconds: float,
               amortized_fit_seconds: float, standalone_source_seconds: float
               ) -> tuple[dict[str, Any], dict[str, Any]]:
    active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
    rows, private = {}, {}
    for name, query in queries.items():
        rows[name], private[name] = _evaluate(frozen.compiled, closure, query,
            references[name], active, frozen.plans[name])
    workloads = []
    for count in sorted({1, len(groups["FIT_BANK"]), len(queries)}):
        prefix = list(rows.values())[:count]
        planning = math.fsum(row["planning_seconds"] for row in prefix)
        forecast = math.fsum(row["all_cell_forecast_seconds"] for row in prefix)
        audit = math.fsum(row["all_state_ground_audit_seconds"] for row in prefix)
        build = frozen.inventory["construction_seconds"]
        counters = {}
        for key in ("planning_counts", "all_cell_forecast_counts", "all_state_ground_audit_counts"):
            counter: Counter[str] = Counter()
            for row in prefix:
                counter.update(row[key])
            counters[key] = dict(counter)
        workloads.append({
            "query_count": count, "query_names": list(queries)[:count],
            "shared_exact_closure_seconds": closure.elapsed_seconds,
            "shared_sampling_seconds": sampling_seconds,
            "one_time_construction_seconds": build,
            "amortized_source_encoder_fit_seconds": amortized_fit_seconds,
            "standalone_additional_source_acquisition_and_fit_seconds": standalone_source_seconds,
            "cumulative_planning_seconds": planning,
            "cumulative_forecast_seconds": forecast,
            "cumulative_ground_audit_seconds": audit,
            "construction_plus_planning_seconds": build + planning,
            "sample_build_plan_plus_amortized_fit_seconds": sampling_seconds + build + planning + amortized_fit_seconds,
            "standalone_source_and_target_closure_sample_build_plan_seconds": (
                standalone_source_seconds + closure.elapsed_seconds + sampling_seconds + build + planning),
            "including_shared_closure_sample_build_plan_forecast_audit_seconds": (
                closure.elapsed_seconds + sampling_seconds + build + planning + forecast + audit + amortized_fit_seconds),
            "cumulative_counts": counters,
        })
    arm = _compact_arm({
        "inventory": frozen.inventory, "queries": rows, "refinement_diagnostics": None,
        "all_state_required_switches": _switches(references, active, groups,
            {name: row["policy"] for name, row in private.items()}),
        "root_required_switches": _switches(references, closure.model.roots, groups,
            {name: row["policy"] for name, row in private.items()}),
        "measured_cumulative_workloads": workloads, "model_build_count": 1,
        "query_count_using_same_compiled_model": len(queries),
    })
    arm["encoding_diagnostics"] = frozen.diagnostics
    return arm, private


def matched_comparisons(private: Mapping[str, Any], active: Sequence[int], root: int,
                        queries: Mapping[str, Query], closure: DevelopmentClosure | None = None
                        ) -> dict[str, Any]:
    result = {}
    for arm in ARM_NAMES[1:]:
        result[arm] = {}
        for name in queries:
            full, candidate = private[ARM_NAMES[0]][name], private[arm][name]
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


def _worst_encoding_added_loss(private: Mapping[str, Any], closure: DevelopmentClosure,
                               queries: Mapping[str, Query], encoder: Any) -> dict[str, Any]:
    active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
    def extra(name: str, state: int) -> float:
        return (private["full_state_empirical"][name]["actual"][state]["value"]
            - private["frozen_rule_encoder"][name]["actual"][state]["value"])
    name, state = max(((name, state) for name in queries for state in active), key=lambda item: extra(*item))
    full, candidate = private["full_state_empirical"][name], private["frozen_rule_encoder"][name]
    return {"query": name, "state": state, "extra_regret": extra(name, state),
        "board": closure.boards[state], "remaining_horizon": closure.model.layers[state],
        "full_state_action": full["policy"][state], "candidate_action": candidate["policy"][state],
        "full_state_exact_metrics": full["actual"][state], "candidate_exact_metrics": candidate["actual"][state],
        "frozen_code": encoder.encode(closure.boards[state], closure.model.layers[state]),
        "board_features": dict(zip(FEATURE_NAMES, board_features(closure.boards[state])))}


def _cell_conflicts(frozen: FrozenArm, closure: DevelopmentClosure,
                    references: Mapping[str, Any], encoder: Any) -> dict[str, Any]:
    """Post-hoc incompatibility witnesses; no state is removed or re-encoded."""
    conflicting_cells, conflicting_cell_queries, witnesses = set(), 0, []
    for cell_id, cell in frozen.compiled.cells.items():
        if cell.terminal != "ACTIVE" or len(cell.members) < 2:
            continue
        for name, reference in references.items():
            sets = [set(reference["optimal_actions"][state]) for state in cell.members]
            if set.intersection(*sets):
                continue
            conflicting_cells.add(cell_id)
            conflicting_cell_queries += 1
            if len(witnesses) >= 3:
                continue
            pair = next(((left, right) for left, right in combinations(cell.members, 2)
                if set(reference["optimal_actions"][left]).isdisjoint(
                    reference["optimal_actions"][right])), None)
            members = pair if pair is not None else cell.members
            witnesses.append({"cell": cell_id, "query": name,
                "reason": "No action is exact-optimal for every member of this cell.",
                "disjoint_pair_exists": pair is not None,
                "states": [{"state": state, "board": closure.boards[state],
                    "remaining_horizon": closure.model.layers[state],
                    "frozen_code": encoder.encode(closure.boards[state], closure.model.layers[state]),
                    "board_features": dict(zip(FEATURE_NAMES, board_features(closure.boards[state]))),
                    "exact_optimal_actions": reference["optimal_actions"][state]}
                    for state in members]})
    return {"conflicting_active_cells": len(conflicting_cells),
        "conflicting_cell_query_count": conflicting_cell_queries,
        "first_three_conflicts_in_cell_and_query_order": witnesses}


def _pre_fit_overlap(cases: Sequence[Any], closures: Mapping[str, DevelopmentClosure]) -> dict[str, Any]:
    started = perf_counter()
    boards = {name: set(closure.boards.values()) for name, closure in closures.items()}
    layered = {name: {(board, closure.model.layers[state]) for state, board in closure.boards.items()}
               for name, closure in closures.items()}
    orbit_cache = {board: min(board_symmetries(board).values()) for board in set().union(*boards.values())}
    orbits = {name: {orbit_cache[board] for board in board_set} for name, board_set in boards.items()}
    train_names = {case.name for case in cases if case.split == "TRAIN" and case.name in closures}
    train_boards = set().union(*(boards[name] for name in train_names))
    train_layered = set().union(*(layered[name] for name in train_names))
    train_orbits = set().union(*(orbits[name] for name in train_names))
    by_name = {case.name: case for case in cases}
    pairs = []
    for left, right in combinations(closures, 2):
        raw, exact_layered, orbit = len(boards[left] & boards[right]), len(layered[left] & layered[right]), len(orbits[left] & orbits[right])
        if raw or exact_layered or orbit:
            pairs.append({"left_case": left, "right_case": right,
                "left_split": by_name[left].split, "right_split": by_name[right].split,
                "shared_raw_boards": raw, "shared_board_horizon_states": exact_layered,
                "shared_dihedral_board_orbits": orbit})
    return {"before_any_encoder_fit": True, "completed_closure_count": len(closures),
        "overlapping_pairs": pairs,
        "case_exposure_to_training_closures": {name: {
            "split": by_name[name].split, "shared_raw_boards": len(boards[name] & train_boards),
            "shared_board_horizon_states": len(layered[name] & train_layered),
            "shared_dihedral_board_orbits": len(orbits[name] & train_orbits),
            "active_states_sharing_training_raw_board": sum(
                closure.model.terminal[state] == "ACTIVE" and board in train_boards
                for state, board in closure.boards.items()),
            "active_states_sharing_training_dihedral_orbit": sum(
                closure.model.terminal[state] == "ACTIVE" and orbit_cache[board] in train_orbits
                for state, board in closure.boards.items()),
        } for name, closure in closures.items()},
        "all_overlaps_retained": True, "additional_closure_calls": 0,
        "historically_exposed_development_cohort": True,
        "elapsed_seconds": perf_counter() - started}


def run_comparison_v7(*, cases: Sequence[Any] | None = None,
                       cohort_roster: Mapping[str, Any] | None = None,
                       samples_per_row: int = SAMPLES_PER_ROW,
                       sample_seeds: Sequence[int] = SAMPLE_SEEDS,
                       max_nodes: int = 30_000,
                       fit_queries: Mapping[str, Query] | None = None,
                       probe_queries: Mapping[str, Query] | None = None,
                       progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    from .controlled_predictive_cohort_v7 import cases_v7

    declared = tuple(cases_v7() if cases is None else cases)
    bank = dict(COMPARISON_QUERIES if fit_queries is None else fit_queries)
    probes = dict(PROBE_QUERIES if probe_queries is None else probe_queries)
    if not declared or not bank or not sample_seeds or bank.keys() & probes.keys():
        raise ValueError("nonempty cases, bank, seeds and distinct query names are required")
    if samples_per_row < 1 or len({case.name for case in declared}) != len(declared):
        raise ValueError("positive sample count and unique case names are required")
    if not any(case.split == "TRAIN" for case in declared):
        raise ValueError("the declared cohort must contain training cases")
    queries = {**bank, **probes}
    groups = {"FIT_BANK": tuple(bank), **({"PROBES": tuple(probes)} if probes else {}), "ALL": tuple(queries)}
    started_all = perf_counter()
    records, closures = [], {}
    for case in declared:
        started = perf_counter()
        record: dict[str, Any] = {"case": asdict(case), "references": {}, "sampled_runs": []}
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
        records.append(record)
        if progress:
            progress({"case": case.name, "status": record["status"], "completed_closures": len(records), "total": len(declared)})
    overlap = _pre_fit_overlap(declared, closures)
    record_by_name = {row["case"]["name"]: row for row in records}
    source_cases = [case for case in declared if case.split == "TRAIN"]
    source_failure = any(case.name not in closures for case in source_cases)
    encoder_fits, compiled_model_example = [], None
    physical_draws = 0
    if source_failure:
        for row in records:
            if row["status"] == "CLOSURE_COMPLETE":
                row["status"] = "NOT_RUN_TRAINING_CLOSURE_INCOMPLETE"
    else:
        for seed_index, seed in enumerate(sample_seeds):
            empirical_by_name, sample_seconds = {}, {}
            def acquire(case: Any) -> FiniteModel:
                nonlocal physical_draws
                started = perf_counter()
                model = sample_model(closures[case.name].model, samples_per_row=samples_per_row, seed=seed)
                sample_seconds[case.name] = perf_counter() - started
                empirical_by_name[case.name] = model
                physical_draws += len(model.rows) * samples_per_row
                return model
            for case in source_cases:
                acquire(case)
            started = perf_counter()
            fitted = fit_encoder(tuple(TrainingModel(case.name, empirical_by_name[case.name], closures[case.name].boards)
                for case in source_cases), max_depth=4, min_leaf=2)
            fit_seconds = perf_counter() - started
            source_draws = sum(len(empirical_by_name[case.name].rows) * samples_per_row for case in source_cases)
            started = perf_counter()
            encoder_payload = fitted.encoder.to_payload()
            encoder_bytes = len(json.dumps(encoder_payload, separators=(",", ":"), allow_nan=False).encode("utf-8"))
            encoder_inventory_seconds = perf_counter() - started
            encoder_fits.append({"sample_seed": seed, "source_case_names": [case.name for case in source_cases],
                "source_empirical_draws": source_draws,
                "source_sampling_seconds": math.fsum(sample_seconds[case.name] for case in source_cases),
                "source_closure_seconds": math.fsum(closures[case.name].elapsed_seconds for case in source_cases),
                "encoder_fit_seconds": fit_seconds, "diagnostics": fitted.diagnostics,
                "encoder": encoder_payload, "encoder_bytes_once_per_fit": encoder_bytes,
                "encoder_inventory_serialization_seconds": encoder_inventory_seconds,
                "amortization_case_count": len(closures),
                "training_queries": [], "nontraining_samples_constructed_before_fit": 0,
                "source_acquisition_is_subset_of_campaign_case_costs": True})
            if progress:
                progress({"sample_seed": seed, "status": "ENCODER_FROZEN", "source_case_count": len(source_cases),
                          "source_draws": source_draws, "fit_seconds": fit_seconds})
            for case_index, case in enumerate(declared):
                if case.name not in closures:
                    continue
                closure, record = closures[case.name], record_by_name[case.name]
                empirical = empirical_by_name[case.name] if case.name in empirical_by_name else acquire(case)
                frozen = {}
                offset = (seed_index + case_index) % len(ARM_NAMES)
                order = ARM_NAMES[offset:] + ARM_NAMES[:offset]
                for arm in order:
                    frozen[arm] = _freeze_arm(arm, empirical, closure, fitted.encoder, queries)
                if frozen["frozen_rule_encoder"].compiled.state_to_cell != frozen["action_outcome_shuffle_encoder"].compiled.state_to_cell:
                    raise AssertionError("shuffle control changed frozen encoder codes")
                # Exact policy labels enter only after every arm's plans are frozen.
                started = perf_counter()
                exact = compile_full_state(closure.model)
                exact_build_seconds = perf_counter() - started
                references = _reference(closure, exact, queries)
                active = tuple(state for state, status in closure.model.terminal.items() if status == "ACTIVE")
                root = closure.model.roots[0]
                run: dict[str, Any] = {"sample_seed": seed, "empirical_draws": len(empirical.rows) * samples_per_row,
                    "empirical_model_sample_count": 1, "empirical_rows": len(empirical.rows),
                    "samples_per_row": samples_per_row, "sampling_seconds": sample_seconds[case.name],
                    "training_kernel_reused_without_redrawing": case.split == "TRAIN",
                    "measured_arm_order": order, "arms": {},
                    "exact_reference_cost": {"full_state_construction_seconds": exact_build_seconds,
                        "planning_seconds": math.fsum(row["planning_seconds"] for row in references.values()),
                        "action_labeling_seconds": math.fsum(row["all_state_action_labeling_seconds"] for row in references.values())}}
                private = {}
                for arm in ARM_NAMES:
                    source_extra = fit_seconds + math.fsum(closures[source.name].elapsed_seconds + sample_seconds[source.name]
                        for source in source_cases if source.name != case.name)
                    run["arms"][arm], private[arm] = _audit_arm(frozen[arm], closure, queries, references, groups,
                        sample_seconds[case.name], fit_seconds / len(closures) if arm in ARM_NAMES[2:] else 0.0,
                        source_extra if arm in ARM_NAMES[2:] else 0.0)
                posthoc_started = perf_counter()
                run["matched_comparisons"] = matched_comparisons(private, active, root, queries, closure)
                run["worst_encoding_added_loss_witness"] = _worst_encoding_added_loss(private, closure, queries, fitted.encoder)
                run["encoder_cell_conflicts"] = _cell_conflicts(frozen["frozen_rule_encoder"], closure, references, fitted.encoder)
                witness = run["arms"]["frozen_rule_encoder"]["worst_regret_witness"]
                witness["frozen_code"] = fitted.encoder.encode(tuple(witness["board"]), witness["remaining_horizon"])
                witness["board_features"] = dict(zip(FEATURE_NAMES, board_features(tuple(witness["board"]))))
                run["posthoc_matched_loss_cell_conflicts_and_witness_features_seconds"] = perf_counter() - posthoc_started
                record["sampled_runs"].append(run)
                if "exact_query_references" not in record:
                    record["exact_query_references"] = {name: {"root_q_values": row["root_q_values"],
                        "root_optimal_actions": row["optimal_actions"][root], "root_optimal_value": row["values"][root]}
                        for name, row in references.items()}
                    record["exact_all_state_required_switches"] = _switches(references, active, groups)
                    record["exact_root_required_switches"] = _switches(references, closure.model.roots, groups)
                if case.name == "v6_spawn_edge_rescue_2" and seed == 832101:
                    from .controlled_predictive_encoder_io_v7 import freeze_artifact_payload
                    started = perf_counter()
                    candidate = frozen["frozen_rule_encoder"]
                    payload = freeze_artifact_payload(fitted.encoder, candidate.compiled, candidate.code_to_cell,
                        example_board=tuple(case.board), example_horizon=case.horizon)
                    compiled_model_example = {"case_name": case.name, "sample_seed": seed, "artifact": payload,
                        "queries": {name: {"query": asdict(query),
                            "expected_root_action": candidate.plans[name][0].policy[candidate.compiled.state_to_cell[root]],
                            "expected_root_value": candidate.plans[name][0].values[candidate.compiled.state_to_cell[root]]}
                            for name, query in queries.items()},
                        "serialization_seconds": perf_counter() - started}
                record["status"] = "COMPLETE"
                if progress:
                    progress({"case": case.name, "sample_seed": seed, "status": "SAMPLE_COMPLETE",
                        "active_states": len(active),
                        "encoder_active_cells": frozen["frozen_rule_encoder"].inventory["active_cells"]})
    return {
        "schema": "acfqp.controlled_predictive_encoder_comparison.v7",
        "status": "DEVELOPMENT_COMPLETE" if all(row["status"] == "COMPLETE" for row in records)
            else "DEVELOPMENT_COMPLETE_WITH_DECLARED_FAILURES",
        "scientific_gate": "NOT_A_FORMAL_GATE", "case_count": len(declared),
        "settings": {"samples_per_row": samples_per_row, "sample_seeds": list(sample_seeds),
            "max_nodes": max_nodes, "max_tree_depth": 4, "min_tree_leaf": 2,
            "queries": {name: asdict(query) for name, query in queries.items()},
            "query_groups": groups, "queries_used_in_encoder_fit": []},
        "cohort_roster": cohort_roster, "pre_fit_closure_overlap": overlap,
        "cases": records, "encoder_fits": encoder_fits, "compiled_model_example": compiled_model_example,
        "summary_by_split": {split: _summarize(records if split == "ALL" else [row for row in records
            if row["case"]["split"] == split], groups) for split in ("ALL", *sorted({case.split for case in declared}))},
        "summary_by_family": {family: _summarize([row for row in records if row["case"]["family"] == family], groups)
            for family in dict.fromkeys(case.family for case in declared)},
        "accounting": {"actual_physical_draws": physical_draws,
            "current_case_draws_including_reused_training_kernels": sum(run["empirical_draws"] for row in records for run in row["sampled_runs"]),
            "encoder_fit_count": len(encoder_fits),
            "total_encoder_fit_seconds": math.fsum(row["encoder_fit_seconds"] for row in encoder_fits),
            "matching": "All four arms share one current empirical kernel per case/seed. The shuffled control permutes its action outcomes using unchanged frozen encoder codes. No additional observations or refitting occur for the control.",
            "source_costs": "The three TRAIN kernels are reused as their own current-case kernels. Source closures and observations are a reported subset of the sixteen-case campaign acquisition cost, never added twice. Each encoder fit is charged once per seed, amortized across completed cases; the shuffle arm is an alternative using the same source fit. Full-state and exact-quotient baselines have the source data available but do not use them or pay encoder fitting cost.",
            "standalone_target_cost": "Deploying one held-out target with no source pool would additionally require acquisition of all three source models and the entire encoder fit, rather than the campaign-amortized fit shown here.",
            "scope": "Shared target information and sample budget only; source use and total cost differ. Exact closure generation, empirical sampling, feature extraction/tree traversal, compilation, planning, component forecasts and exact auditing are charged separately. Diagnostic exact reference planning and inventory serialization remain separately reported.",
            "sampling_stream": "Existing sample_model uses one deterministic global Random per case/seed over sorted rows. This is a single dose; there is no nested-budget claim.",
            "audit_order": "Encoder fit precedes nontraining empirical construction. All four case policies for all ten queries are frozen before that case's exact optimal labels are produced. Query weights never enter encoder fitting.",
        },
        "limitations": [
            "All V6 roots and the old H2 regression were already characterized by exact dynamics. Fit-held-out is a training split, not independent scientific confirmation.",
            "Training and target closures may overlap in boards or dihedral orbits; all such overlaps remain in the pre-fit audit and denominator.",
            "A frozen executable board rule transfers, but current target transition rows are still sampled for every covered state-action pair. This is not a learned transferable dynamics model or a sample-efficiency result.",
            "The fixed-depth empirical target tree need not preserve true optimal action sets or risk. Validation diagnoses the single frozen specification; it does not select or tune it.",
            "Source variants, seeds, queries, state counts and symmetry overlaps do not constitute independent replications. Timings are descriptive single-host measurements.",
            "U005 remains scientifically failed. U006 and the deferred original V2 cohort are not executed.",
        ],
        "all_declared_cases_retained": True, "u006_assurance_started": False,
        "deferred_v2_24_case_cohort_executed": False,
        "elapsed_seconds": perf_counter() - started_all,
    }


__all__ = ("ARM_NAMES", "run_comparison_v7", "matched_comparisons")
