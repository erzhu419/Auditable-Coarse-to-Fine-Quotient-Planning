#!/usr/bin/env python3
"""Compare GAP24, CACHED24 and CACHED32 on a frozen fresh H2 cohort."""

import argparse
from collections import Counter
import gzip
import json
from itertools import permutations
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_local_v21 import run_local_allocation, ARMS as LOCAL_ARMS
from acfqp.science.controlled_predictive_gap_frontier_v31 import GapFrontierPlannerState
from acfqp.science.controlled_predictive_new_starts_v28 import acquire_common_prefix, prepare_query, generate_board
from acfqp.domains.standard_2048 import legal_actions_v1, state_from_board_v1, Swipe2048Status
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_snapshot_v21 import state_record
from run_controlled_predictive_new_starts_v28 import _identity, _key, _validate_local, TRACE_FIELDS

PROTOCOL = Path("specs/CONTROLLED_PREDICTIVE_BUDGET_TRANSFER_V35.md")
DEFAULT_PLAN = Path("reports/controlled_predictive_budget_transfer_plan_v35.json")
DEFAULT_PREFIXES = Path("reports/controlled_predictive_budget_transfer_prefixes_v35.json.gz")
DEFAULT_ENDPOINTS = Path("reports/controlled_predictive_budget_transfer_endpoints_v35.jsonl.gz")
DEFAULT_OUTPUT = Path("reports/controlled_predictive_budget_transfer_v35.json.gz")


def bind_plan(plan, source_plan, source_analysis, novelty_plans):
    """Check frozen algorithm and acquisition identities before physical work."""
    fixed = ("queries", "source_query_order", "prefix_batches_per_board",
             "samples_per_batch", "total_path_batch_cap", "selection_rule")
    checks = {key: plan[key] == source_plan[key] for key in fixed}
    original = source_analysis["accounting"]
    checks.update(source_analysis_passed=source_analysis["all_analysis_checks_passed"],
        historical_batches=plan["source_historical_physical_batches"] == original["historical_physical_batches"] + original["total_physical_batches"],
        historical_draws=plan["source_historical_physical_draws"] == original["historical_physical_draws"] + original["total_physical_draws"])
    checks["configurations"] = plan["configurations"] == [
        {"name": "GAP24", "arm": "GAP_FRONTIER", "budget": 24},
        {"name": "CACHED24", "arm": "CACHED", "budget": 24},
        {"name": "CACHED32", "arm": "CACHED", "budget": 32}]
    checks["configured_arms"] = {row["arm"] for row in plan["configurations"]} == set(source_plan["arms"])
    all_old_boards = [row for old_plan in [source_plan, *novelty_plans] for row in old_plan["boards"]]
    all_old_replicates = [row for old_plan in [source_plan, *novelty_plans] for row in old_plan["replicates"]]
    board_records = []
    old_boards = {tuple(row["board"]) for row in all_old_boards}
    old_generation = {row["generation_seed"] for row in all_old_boards}
    old_prefix = {row["prefix_seed"] for row in all_old_boards}
    old_suffix = {row["base_seed"] for row in all_old_replicates}
    for board in plan["boards"]:
        value = tuple(board["board"])
        board_checks = {"generated_board": value == generate_board(board["generation_seed"]),
            "horizon": board["horizon"] == 2, "active": state_from_board_v1(value).status is Swipe2048Status.ACTIVE,
            "legal_actions": board["legal_actions"] == sorted(action.value for action in legal_actions_v1(value)),
            "new_board": value not in old_boards, "new_generation_seed": board["generation_seed"] not in old_generation,
            "new_prefix_seed": board["prefix_seed"] not in old_prefix}
        board_records.append({"board_index": board["board_index"], "passed": all(board_checks.values()), "checks": board_checks})
    expected = [(board["board_index"], name) for board in plan["boards"] for name in plan["source_query_order"]]
    actual = [(row["board_index"], row["query_name"]) for row in plan["contexts"]]
    boards = {row["board_index"]: row for row in plan["boards"]}
    cohort = {"frozen_prerequisites": bool(plan["cohort_prerequisites"]) and all(plan["cohort_prerequisites"].values()),
        "all_boards": all(row["passed"] for row in board_records),
        "frozen_seed_bands": plan["seed_bands"] == {
            "generation": [row["generation_seed"] for row in plan["boards"]],
            "prefix": [row["prefix_seed"] for row in plan["boards"]],
            "suffix": [row["base_seed"] for row in plan["replicates"]]},
        "frozen_registry_no_reuse": plan["seed_registry_reused_values"] == [],
        "board_count": len(plan["boards"]) == plan["board_count"],
        "unique_boards": len({tuple(row["board"]) for row in plan["boards"]}) == len(plan["boards"]),
        "unique_board_indices": len(boards) == len(plan["boards"]),
        "unique_generation_seeds": len({row["generation_seed"] for row in plan["boards"]}) == len(plan["boards"]),
        "unique_prefix_seeds": len({row["prefix_seed"] for row in plan["boards"]}) == len(plan["boards"]),
        "query_count": len(plan["source_query_order"]) == plan["query_count"],
        "query_definitions": set(plan["queries"]) == set(plan["source_query_order"]),
        "context_product": actual == expected and len(actual) == plan["context_count"],
        "context_indices": [row["context_index"] for row in plan["contexts"]] == list(range(len(actual))),
        "context_targets": all(row["target_key"] == [boards[row["board_index"]]["horizon"], boards[row["board_index"]]["board"]]
            and row["case_name"] == boards[row["board_index"]]["name"] for row in plan["contexts"]),
        "context_prefixes": all(row["initial_batches"] == plan["prefix_batches_per_board"] for row in plan["contexts"]),
        "replicate_count": len(plan["replicates"]) == plan["replicate_count"],
        "replicate_indices": [row["replicate_index"] for row in plan["replicates"]] == list(range(plan["replicate_count"])),
        "unique_suffix_seeds": len({row["base_seed"] for row in plan["replicates"]}) == plan["replicate_count"],
        "new_suffix_seeds": all(row["base_seed"] not in old_suffix for row in plan["replicates"]),
        "triple_count": plan["expected_triple_count"] == plan["context_count"] * plan["replicate_count"],
        "configuration_count": plan["expected_run_count"] == 3 * plan["expected_triple_count"]}
    return ({"passed": all(checks.values()), "checks": checks},
            {"passed": all(cohort.values()), "checks": cohort, "boards": board_records})


def run_budget_transfer(plan_path, prefixes_path, endpoints_path, output_path, progress=None):
    started_all = perf_counter()
    for path in (prefixes_path, endpoints_path, output_path):
        if path.exists():
            raise FileExistsError(f"V35 output already exists: {path}")
    accounting = Counter()
    tick = perf_counter()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    accounting["frozen_plan_read_seconds"] = perf_counter() - tick
    tick = perf_counter()
    source_plan = json.loads(Path(plan["source_plan"]).read_text(encoding="utf-8"))
    source_analysis = json.loads(Path(plan["source_analysis"]).read_text(encoding="utf-8"))
    original_accounting = source_analysis["accounting"]
    novelty_plans = [json.loads(Path(path).read_text(encoding="utf-8")) for path in plan["source_novelty_plans"]]
    plan_binding, cohort_binding = bind_plan(plan, source_plan, source_analysis, novelty_plans)
    accounting["source_metadata_read_and_binding_seconds"] = perf_counter() - tick
    if not plan_binding["passed"] or not cohort_binding["passed"]:
        raise ValueError("V35 source algorithm or fresh cohort binding differs before acquisition")
    LOCAL_ARMS["GAP_FRONTIER"] = GapFrontierPlannerState
    configuration_lookup = {row["name"]: row for row in plan["configurations"]}
    configuration_names = list(configuration_lookup)
    run_orders = list(permutations(configuration_names))
    queries = {name: Query(**plan["queries"][name]) for name in plan["source_query_order"]}
    prefixes, preparations, snapshots = {}, {}, {}
    prefix_provider, preparation_work = Counter(), Counter()
    evidence = {"schema": "acfqp.controlled_predictive_budget_transfer_prefixes.v35", "plan": plan,
        "prefixes": [], "query_starts": [], "local_acquisition_started": False, "oracle_constructed": False}
    for board in plan["boards"]:
        root = board["horizon"], tuple(board["board"])
        records, acquisition = acquire_common_prefix(root, board["prefix_seed"])
        prefix_checks = {"fixed_batch_count": len(records) == plan["prefix_batches_per_board"],
            "legal_actions": acquisition["root_legal_actions"] == board["legal_actions"],
            "provider_batches": acquisition["provider_counts"].get("row_requests", 0) == acquisition["physical_batches"] == len(records),
            "physical_draws": acquisition["provider_counts"].get("physical_draws", 0) == acquisition["physical_draws"] == 256*len(records)}
        prefix = {"board_index": board["board_index"], "name": board["name"], "prefix_seed": board["prefix_seed"],
            "accounting": acquisition, "validation": {"passed": all(prefix_checks.values()), "checks": prefix_checks}}
        prefixes[board["board_index"]] = prefix
        prefix_provider.update(acquisition["provider_counts"])
        accounting["prefix_acquisition_seconds"] += acquisition["whole_seconds"]
        evidence["prefixes"].append({**prefix, "batches": records})
        for context in (row for row in plan["contexts"] if row["board_index"] == board["board_index"]):
            state, preparation = prepare_query(root, context["query_name"], queries[context["query_name"]], records)
            checks = {"prefix": prefix["validation"]["passed"], "target": _key(context["target_key"]) == root,
                "single_query": list(state.queries) == [context["query_name"]],
                "initial_batches": state.spent_batches == context["initial_batches"] == plan["prefix_batches_per_board"],
                "no_new_samples": preparation["new_provider_calls"] == preparation["new_physical_draws"] == 0}
            item = {"identity": _identity(context), "accounting": preparation,
                "validation": {"passed": all(checks.values()), "checks": checks}}
            preparations[context["context_index"]] = item
            snapshots[context["context_index"]] = state
            accounting["single_query_preparation_seconds"] += preparation["whole_seconds"]
            preparation_work.update(preparation["work_counts"])
            tick = perf_counter()
            evidence["query_starts"].append({**item, "state": state_record(state, context["query_name"])})
            accounting["query_start_materialization_seconds"] += perf_counter() - tick
        if progress:
            progress({"stage": "PREFIX_AND_QUERY_PREPARATION", "board_index": board["board_index"]})
    tick = perf_counter()
    with gzip.open(prefixes_path, "xt", encoding="utf-8") as writer:
        json.dump(evidence, writer, separators=(",", ":"), allow_nan=False)
    accounting["prefix_artifact_serialization_seconds"] = perf_counter() - tick
    del evidence
    providers, local_stages, local_work = ({name: Counter() for name in configuration_names} for _ in range(3))
    tick = perf_counter()
    writer = gzip.open(endpoints_path, "xt", encoding="utf-8")
    accounting["endpoint_stream_open_seconds"] = perf_counter() - tick
    try:
        for repetition in plan["replicates"]:
            valid_count, complete_count = 0, 0
            for context in plan["contexts"]:
                index, seed = context["context_index"], repetition["base_seed"]
                snapshot = snapshots[index]
                order = run_orders[(repetition["replicate_index"] * plan["context_count"] + index) % len(run_orders)]
                pair = {**repetition, "identity": _identity(context), "target_key": context["target_key"],
                    "initial_batches": context["initial_batches"],
                    "run_order": list(order), "initial_snapshot_validation": preparations[index]["validation"], "configurations": {}}
                for configuration_name in order:
                    configuration = configuration_lookup[configuration_name]
                    arm, budget = configuration["arm"], configuration["budget"]
                    configured_context = {**context, "requested_batch_count": budget}
                    provider = BatchRowSampleProvider(seed)
                    state, local = run_local_allocation(snapshot, arm, provider, context["query_name"],
                        _key(context["target_key"]), requested_batches=budget)
                    accounting["local_configuration_run_count"] += 1
                    accounting["reset_from_prepared_query_count"] += 1
                    accounting["local_allocation_wall_seconds"] += local["accounting"]["whole_run_seconds"]
                    providers[configuration_name].update(local["provider_counts"])
                    local_stages[configuration_name].update(local["accounting"]["seconds_by_stage"])
                    local_work[configuration_name].update(local["accounting"]["work_counts"])
                    tick = perf_counter()
                    local["repeat_batches_on_rows_absent_from_common"] = sum(request["kind"] == "REPEAT_OBSERVATION" and
                        (_key(request["row_key"][0]), request["row_key"][1]) not in snapshot.rows for request in local["requested_batches"])
                    accounting["repeat_classification_seconds"] += perf_counter() - tick
                    tick = perf_counter()
                    stored = state_record(state, context["query_name"])
                    accounting["endpoint_materialization_seconds"] += perf_counter() - tick
                    tick = perf_counter()
                    validation = _validate_local(local, stored, configured_context, arm)
                    validation["checks"]["prepared_start"] = preparations[index]["validation"]["passed"]
                    validation["passed"] = all(validation["checks"].values())
                    accounting["source_validation_seconds"] += perf_counter() - tick
                    prefix_seconds = prefixes[context["board_index"]]["accounting"]["whole_seconds"]
                    prepare_seconds = preparations[index]["accounting"]["whole_seconds"]
                    local_seconds = local["accounting"]["whole_run_seconds"]
                    pair["configurations"][configuration_name] = {"configuration": configuration, "state": stored, "local": local, "source_validation": validation,
                        "source_valid": validation["passed"], "completed_requested_budget": local["completed_batches"] == budget,
                        "costs": {"prefix_sampling_seconds": prefix_seconds, "single_query_prepare_seconds": prepare_seconds,
                            "local_whole_run_seconds": local_seconds, "independent_query_seconds": prefix_seconds+prepare_seconds+local_seconds}}
                    del state
                pair["source_valid"] = all(row["source_valid"] for row in pair["configurations"].values())
                pair["fixed_budget_complete"] = all(row["completed_requested_budget"] for row in pair["configurations"].values())
                valid_count += pair["source_valid"]
                complete_count += pair["source_valid"] and pair["fixed_budget_complete"]
                tick = perf_counter()
                json.dump(pair, writer, separators=(",", ":"), allow_nan=False)
                writer.write("\n")
                accounting["endpoint_stream_write_seconds"] += perf_counter() - tick
                accounting["endpoint_triple_records_written"] += 1
            if progress:
                progress({"stage": "SAMPLING", **repetition, "source_valid_triples": valid_count, "fixed_budget_complete_triples": complete_count})
    finally:
        tick = perf_counter()
        writer.close()
        accounting["endpoint_stream_close_seconds"] += perf_counter() - tick
    # Every prefix/query snapshot and every physical local run is retained first.
    oracles, closure_counts = {}, {}
    for board in plan["boards"]:
        tick = perf_counter()
        closure = build_development_closure(horizon=board["horizon"], max_nodes=30_000,
                                           boards={board["name"]: tuple(board["board"])})
        accounting["exact_closure_construction_seconds"] += perf_counter() - tick
        tick = perf_counter()
        oracles[board["board_index"]] = ExactOracle.from_closure(closure)
        accounting["oracle_initialization_seconds"] += perf_counter() - tick
        closure_counts[board["board_index"]] = closure.counts
    repetitions = []
    evaluation_work, evaluation_stages = Counter(), Counter()
    with gzip.open(endpoints_path, "rt", encoding="utf-8") as reader:
        for repetition in plan["replicates"]:
            result_rep = {**repetition, "contexts": []}
            for context in plan["contexts"]:
                tick = perf_counter()
                endpoint = json.loads(reader.readline())
                accounting["endpoint_reload_read_seconds"] += perf_counter() - tick
                accounting["endpoint_triple_records_reloaded"] += 1
                expected = {**repetition, "identity": _identity(context), "target_key": context["target_key"],
                    "initial_batches": context["initial_batches"]}
                aligned = all(endpoint.get(key) == value for key, value in expected.items())
                result = {key: value for key, value in endpoint.items() if key not in ("configurations", "replicate_index", "base_seed")}
                result["configurations"] = {}
                for configuration_name, row in endpoint["configurations"].items():
                    configuration = configuration_lookup[configuration_name]
                    arm, budget = configuration["arm"], configuration["budget"]
                    configured_context = {**context, "requested_batch_count": budget}
                    tick = perf_counter()
                    compact = {key: value for key, value in row.items() if key not in ("state", "local")}
                    compact["local"] = {key: value for key, value in row["local"].items() if key not in TRACE_FIELDS}
                    validation = _validate_local(row["local"], row["state"], configured_context, arm)
                    validation["checks"].update(endpoint_identity=aligned, configuration=row["configuration"] == configuration, query_weights=row["state"]["query"] == plan["queries"][context["query_name"]],
                        prepared_start=preparations[context["context_index"]]["validation"]["passed"])
                    validation["passed"] = all(validation["checks"].values())
                    compact.update(source_validation=validation, source_valid=validation["passed"], policy_evaluable=False,
                        first_action_validation={"passed": False, "reason": "POLICY_NOT_EVALUATED"})
                    accounting["source_validation_seconds"] += perf_counter() - tick
                    tick = perf_counter()
                    accounting["frozen_policy_evaluation_calls"] += 1
                    try:
                        evaluation = evaluate_frozen_policy(row["state"], context["target_key"], queries[context["query_name"]], oracles[context["board_index"]])
                    except ValueError as error:
                        compact["evaluation_validation"] = {"passed": False, "reason": str(error)}
                    else:
                        compact.update(evaluation=evaluation, evaluation_validation={"passed": True}, policy_evaluable=evaluation["policy_evaluable"])
                        evaluation_work.update(evaluation["accounting"]["work_counts"])
                        evaluation_stages.update({key: evaluation["accounting"][key] for key in ("policy_extraction_seconds", "fixed_policy_evaluation_seconds")})
                        checks = {"initial_action": evaluation["initial_action"] == row["local"]["final_action"],
                            "lower": evaluation["lower"] == row["local"]["lower"], "upper": evaluation["upper"] == row["local"]["upper"],
                            "selected_action_observed": evaluation["selected_action_observed"] == row["local"]["selected_action_observed"]}
                        compact["first_action_validation"] = {"passed": all(checks.values()), "checks": checks}
                    accounting["frozen_policy_evaluation_seconds"] += perf_counter() - tick
                    result["configurations"][configuration_name] = compact
                result["source_valid"] = aligned and set(result["configurations"]) == set(configuration_names) and all(row["source_valid"] for row in result["configurations"].values())
                result["fixed_budget_complete"] = all(row["completed_requested_budget"] for row in result["configurations"].values())
                result["policy_evaluable"] = all(row["policy_evaluable"] for row in result["configurations"].values())
                result["complete"] = result["source_valid"] and result["fixed_budget_complete"] and result["policy_evaluable"] and all(
                    row["first_action_validation"]["passed"] and row["evaluation"]["identities_pass"] and row["evaluation"]["reach_probability_pass"]
                    for row in result["configurations"].values())
                result["status"] = ("TRIPLE_COMPLETE" if result["complete"] else "SOURCE_INVALID" if not result["source_valid"] else
                    "VALID_EARLY_STOP" if not result["fixed_budget_complete"] else "POLICY_EVALUATION_INCOMPLETE")
                result_rep["contexts"].append(result)
            result_rep.update(source_valid=all(row["source_valid"] for row in result_rep["contexts"]),
                fixed_budget_complete=all(row["fixed_budget_complete"] for row in result_rep["contexts"]),
                complete=all(row["complete"] for row in result_rep["contexts"]))
            result_rep["status"] = "REPETITION_COMPLETE" if result_rep["complete"] else "REPETITION_RETAINED_WITH_INCOMPLETE_QUALITY"
            repetitions.append(result_rep)
            if progress:
                progress({"stage": "EVALUATION", **repetition, "source_valid": result_rep["source_valid"], "complete": result_rep["complete"]})
    prefix_batches, prefix_draws = sum(row["accounting"]["physical_batches"] for row in prefixes.values()), sum(row["accounting"]["physical_draws"] for row in prefixes.values())
    local_batches, local_draws = sum(row.get("row_requests", 0) for row in providers.values()), sum(row.get("physical_draws", 0) for row in providers.values())
    report = {"schema": "acfqp.controlled_predictive_budget_transfer.v35", "plan": plan,
        "status": "BUDGET_TRANSFER_COMPLETE" if all(row["complete"] for row in repetitions) else "BUDGET_TRANSFER_WITH_ISSUES",
        "prefixes": list(prefixes.values()), "query_preparations": list(preparations.values()), "repetitions": repetitions,
        "plan_binding_validation": plan_binding, "cohort_binding_validation": cohort_binding,
        "original_source_accounting": original_accounting,
        "source_valid_repetition_count": sum(row["source_valid"] for row in repetitions),
        "complete_repetition_count": sum(row["complete"] for row in repetitions),
        "fixed_budget_complete_triple_count": sum(context["fixed_budget_complete"] for repetition in repetitions for context in repetition["contexts"]),
        "accounting": {**accounting, "prefix_board_count": len(prefixes), "prepared_query_count": len(preparations),
            "prefix_physical_batches": prefix_batches, "prefix_physical_draws": prefix_draws, "prefix_provider_counts": dict(prefix_provider),
            "local_physical_batches": local_batches, "local_physical_draws": local_draws,
            "total_physical_batches": prefix_batches+local_batches, "total_physical_draws": prefix_draws+local_draws,
            "new_prefix_stream_count": len(plan["boards"]), "new_suffix_stream_count": len(plan["replicates"]),
            "reused_prior_seed_count": 0,
            "historical_physical_batches": plan["source_historical_physical_batches"],
            "historical_physical_draws": plan["source_historical_physical_draws"],
            "historical_plus_new_physical_batches": plan["source_historical_physical_batches"]+prefix_batches+local_batches,
            "historical_plus_new_physical_draws": plan["source_historical_physical_draws"]+prefix_draws+local_draws,
            "provider_counts_by_configuration": {arm: dict(value) for arm, value in providers.items()},
            "local_seconds_by_stage_by_configuration": {arm: dict(value) for arm, value in local_stages.items()},
            "local_work_counts_by_configuration": {arm: dict(value) for arm, value in local_work.items()},
            "query_preparation_work_counts": dict(preparation_work), "evaluation_work_counts": dict(evaluation_work),
            "evaluation_seconds_by_stage": dict(evaluation_stages), "exact_closure_counts_by_board": closure_counts,
            "oracle_by_board": {index: oracle.accounting() for index, oracle in oracles.items()},
            "prefix_artifact_bytes": prefixes_path.stat().st_size, "endpoint_artifact_bytes": endpoints_path.stat().st_size},
        "all_prefix_snapshots_closed_before_local": True, "all_sampling_endpoints_closed_before_oracle": True,
        "endpoint_evaluation_replanning_calls": 0, "prefix_artifact": str(prefixes_path), "endpoint_artifact": str(endpoints_path),
        "elapsed_seconds_before_report_serialization": perf_counter() - started_all,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Frozen V31 algorithms on fresh dense H2 roots, fresh root-only prefixes and fresh suffix seeds; same board-generator family, not a new domain. Every query prepares its own caches once; each independent-query cost fully attributes prefix acquisition, that preparation and its local run. Actual prefix sampling occurs only once per board. Quality requires all three configurations to complete their own fixed budget and have evaluable policies. Normal early stops retain source validity and actual costs. The three budgets are intentionally unequal. Prefix and suffix stream identities are fresh relative to the frozen prior registry, while configurations and queries remain paired on shared seed/row/batch identities; physical draws are not independent observations. All endpoint sampling precedes exact evaluation; nested accounting spans are not additive."}
    tick = perf_counter()
    with gzip.open(output_path, "xt", encoding="utf-8") as writer:
        json.dump(report, writer, separators=(",", ":"), allow_nan=False)
    return report, {"report_serialization_seconds": perf_counter() - tick, "report_bytes": output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--prefixes", type=Path, default=DEFAULT_PREFIXES)
    parser.add_argument("--endpoints", type=Path, default=DEFAULT_ENDPOINTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not PROTOCOL.is_file() or not args.plan.is_file():
        parser.error("the frozen V35 protocol and plan must exist before acquisition")
    report, serialization = run_budget_transfer(args.plan, args.prefixes, args.endpoints, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({"status": report["status"], "source_valid_repetition_count": report["source_valid_repetition_count"],
        "complete_repetition_count": report["complete_repetition_count"], "output": str(args.output), **serialization}), flush=True)


if __name__ == "__main__":
    main()
