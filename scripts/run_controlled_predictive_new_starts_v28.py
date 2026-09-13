#!/usr/bin/env python3
"""Compare the frozen CACHED/VARIANCE rules on prospective H2 starts."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_local_v21 import run_local_allocation
from acfqp.science.controlled_predictive_new_starts_v28 import acquire_common_prefix, prepare_query
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science.controlled_predictive_sampling_v15 import BatchRowSampleProvider
from acfqp.science.controlled_predictive_snapshot_v21 import state_record

PROTOCOL = Path("specs/CONTROLLED_PREDICTIVE_NEW_STARTS_V28.md")
DEFAULT_PLAN = Path("reports/controlled_predictive_new_starts_plan_v28.json")
DEFAULT_PREFIXES = Path("reports/controlled_predictive_new_starts_prefixes_v28.json.gz")
DEFAULT_ENDPOINTS = Path("reports/controlled_predictive_new_starts_endpoints_v28.jsonl.gz")
DEFAULT_OUTPUT = Path("reports/controlled_predictive_new_starts_v28.json.gz")
ARMS = ("CACHED", "VARIANCE")
TRACE_FIELDS = ("requested_batches", "observed_batches", "gap_assessments")


def _key(value):
    return value[0], tuple(value[1])


def _identity(context):
    return {key: value for key, value in context.items() if key not in ("target_key", "requested_batch_count", "initial_batches")}


def _budget_status(arms, requested):
    locals_ = [arms[arm]["local"] for arm in ARMS]
    counts = [row["completed_batches"] for row in locals_]
    complete = all(n == requested and row["completed_fixed_budget"] for n, row in zip(counts, locals_))
    shared_stop = (counts[0] == counts[1] < requested and all(row["stop_reason"] == "NO_ELIGIBLE_CANDIDATE"
                   and not row["completed_fixed_budget"] for row in locals_))
    return {"budget_matched": complete or shared_stop, "completed_K_pair": complete,
            "shared_normal_stop_pair": shared_stop, "unequal_budget_pair": counts[0] != counts[1]}


def _validate_local(local, state, context, arm):
    n, K, initial = local["completed_batches"], context["requested_batch_count"], context["initial_batches"]
    provider = local["provider_counts"]
    policy = next((row for row in state["policy_and_intervals"] if row["key"] == context["target_key"]), None)
    checks = {"arm": local["arm"] == arm, "query": local["query_name"] == context["query_name"],
        "target": local["target_key"] == context["target_key"], "requested_K": local["requested_batch_count"] == K,
        "actual_K": 0 <= n <= K, "completion_label": local["completed_fixed_budget"] == (n == K),
        "stop_reason": local["stop_reason"] == ("FIXED_BATCH_BUDGET_COMPLETE" if n == K else "NO_ELIGIBLE_CANDIDATE"),
        "initial_batches": local["initial_batches"] == initial,
        "final_batches": local["final_batches"] == initial+n == state["spent_batches"] <= 128,
        "model_batches": sum(row["batch_count"] for row in state["rows"]) == state["spent_batches"],
        "physical_draws": local["actual_draws"] == provider.get("physical_draws", 0) == 256*n,
        "provider_batches": provider.get("row_requests", 0) == n,
        "first_repeat_batches": provider.get("first_batch_requests", 0) + provider.get("repeat_batch_requests", 0) == n,
        "stored_action": policy is not None and policy["action"] == local["final_action"],
        "stored_lower": policy is not None and policy["lower"] == local["lower"],
        "stored_upper": policy is not None and policy["upper"] == local["upper"]}
    return {"passed": all(checks.values()), "checks": checks}


def run_new_starts(plan_path, prefixes_path, endpoints_path, output_path, progress=None):
    started_all = perf_counter()
    for path in (prefixes_path, endpoints_path, output_path):
        if path.exists():
            raise FileExistsError(f"V28 output already exists: {path}")
    accounting = Counter()
    tick = perf_counter()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    accounting["frozen_plan_read_seconds"] = perf_counter() - tick
    queries = {name: Query(**plan["queries"][name]) for name in plan["source_query_order"]}
    boards = {row["board_index"]: row for row in plan["boards"]}
    prefixes, preparations, snapshots = {}, {}, {}
    prefix_provider, preparation_work = Counter(), Counter()
    evidence = {"schema": "acfqp.controlled_predictive_new_starts_prefixes.v28", "plan": plan,
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
                "fixed_K": context["requested_batch_count"] == plan["requested_batches_per_arm"],
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
    providers, local_stages, local_work = ({arm: Counter() for arm in ARMS} for _ in range(3))
    tick = perf_counter()
    writer = gzip.open(endpoints_path, "xt", encoding="utf-8")
    accounting["endpoint_stream_open_seconds"] = perf_counter() - tick
    try:
        for repetition in plan["replicates"]:
            valid_count, matched_count = 0, 0
            for context in plan["contexts"]:
                index, seed = context["context_index"], repetition["base_seed"]
                snapshot = snapshots[index]
                order = ARMS if (repetition["replicate_index"] + index) % 2 == 0 else ARMS[::-1]
                pair = {**repetition, "identity": _identity(context), "target_key": context["target_key"],
                    "requested_batch_count": context["requested_batch_count"], "initial_batches": context["initial_batches"],
                    "run_order": list(order), "initial_snapshot_validation": preparations[index]["validation"], "arms": {}}
                for arm in order:
                    provider = BatchRowSampleProvider(seed)
                    state, local = run_local_allocation(snapshot, arm, provider, context["query_name"],
                        _key(context["target_key"]), requested_batches=context["requested_batch_count"])
                    accounting["local_arm_run_count"] += 1
                    accounting["reset_from_prepared_query_count"] += 1
                    accounting["local_allocation_wall_seconds"] += local["accounting"]["whole_run_seconds"]
                    providers[arm].update(local["provider_counts"])
                    local_stages[arm].update(local["accounting"]["seconds_by_stage"])
                    local_work[arm].update(local["accounting"]["work_counts"])
                    tick = perf_counter()
                    local["repeat_batches_on_rows_absent_from_common"] = sum(request["kind"] == "REPEAT_OBSERVATION" and
                        (_key(request["row_key"][0]), request["row_key"][1]) not in snapshot.rows for request in local["requested_batches"])
                    accounting["repeat_classification_seconds"] += perf_counter() - tick
                    tick = perf_counter()
                    stored = state_record(state, context["query_name"])
                    accounting["endpoint_materialization_seconds"] += perf_counter() - tick
                    tick = perf_counter()
                    validation = _validate_local(local, stored, context, arm)
                    validation["checks"]["prepared_start"] = preparations[index]["validation"]["passed"]
                    validation["passed"] = all(validation["checks"].values())
                    accounting["source_validation_seconds"] += perf_counter() - tick
                    prefix_seconds = prefixes[context["board_index"]]["accounting"]["whole_seconds"]
                    prepare_seconds = preparations[index]["accounting"]["whole_seconds"]
                    local_seconds = local["accounting"]["whole_run_seconds"]
                    pair["arms"][arm] = {"state": stored, "local": local, "source_validation": validation,
                        "source_valid": validation["passed"], "completed_requested_budget": local["completed_batches"] == context["requested_batch_count"],
                        "costs": {"prefix_sampling_seconds": prefix_seconds, "single_query_prepare_seconds": prepare_seconds,
                            "local_whole_run_seconds": local_seconds, "independent_query_seconds": prefix_seconds+prepare_seconds+local_seconds}}
                    del state
                pair["source_valid"] = all(row["source_valid"] for row in pair["arms"].values())
                pair.update(_budget_status(pair["arms"], context["requested_batch_count"]))
                valid_count += pair["source_valid"]
                matched_count += pair["source_valid"] and pair["budget_matched"]
                tick = perf_counter()
                json.dump(pair, writer, separators=(",", ":"), allow_nan=False)
                writer.write("\n")
                accounting["endpoint_stream_write_seconds"] += perf_counter() - tick
                accounting["endpoint_pair_records_written"] += 1
            if progress:
                progress({"stage": "SAMPLING", **repetition, "source_valid_pairs": valid_count, "budget_matched_pairs": matched_count})
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
                accounting["endpoint_pair_records_reloaded"] += 1
                expected = {**repetition, "identity": _identity(context), "target_key": context["target_key"],
                    "requested_batch_count": context["requested_batch_count"], "initial_batches": context["initial_batches"]}
                aligned = all(endpoint.get(key) == value for key, value in expected.items())
                result = {key: value for key, value in endpoint.items() if key not in ("arms", "replicate_index", "base_seed")}
                result["arms"] = {}
                for arm, row in endpoint["arms"].items():
                    tick = perf_counter()
                    compact = {key: value for key, value in row.items() if key not in ("state", "local")}
                    compact["local"] = {key: value for key, value in row["local"].items() if key not in TRACE_FIELDS}
                    validation = _validate_local(row["local"], row["state"], context, arm)
                    validation["checks"].update(endpoint_identity=aligned, query_weights=row["state"]["query"] == plan["queries"][context["query_name"]],
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
                    result["arms"][arm] = compact
                result["source_valid"] = aligned and set(result["arms"]) == set(ARMS) and all(row["source_valid"] for row in result["arms"].values())
                result.update(_budget_status(result["arms"], context["requested_batch_count"]))
                result["policy_evaluable"] = all(row["policy_evaluable"] for row in result["arms"].values())
                result["paired_complete"] = result["source_valid"] and result["budget_matched"] and result["policy_evaluable"] and all(
                    row["first_action_validation"]["passed"] and row["evaluation"]["identities_pass"] and row["evaluation"]["reach_probability_pass"]
                    for row in result["arms"].values())
                result["status"] = ("PAIR_COMPLETE" if result["paired_complete"] else "SOURCE_INVALID" if not result["source_valid"] else
                    "VALID_EARLY_STOP" if not result["budget_matched"] else "POLICY_EVALUATION_INCOMPLETE")
                result_rep["contexts"].append(result)
            result_rep.update(source_valid=all(row["source_valid"] for row in result_rep["contexts"]),
                budget_matched=all(row["budget_matched"] for row in result_rep["contexts"]),
                complete=all(row["paired_complete"] for row in result_rep["contexts"]))
            result_rep["status"] = "REPETITION_COMPLETE" if result_rep["complete"] else "REPETITION_RETAINED_WITH_INCOMPLETE_QUALITY"
            repetitions.append(result_rep)
            if progress:
                progress({"stage": "EVALUATION", **repetition, "source_valid": result_rep["source_valid"], "complete": result_rep["complete"]})
    prefix_batches, prefix_draws = sum(row["accounting"]["physical_batches"] for row in prefixes.values()), sum(row["accounting"]["physical_draws"] for row in prefixes.values())
    local_batches, local_draws = sum(row.get("row_requests", 0) for row in providers.values()), sum(row.get("physical_draws", 0) for row in providers.values())
    report = {"schema": "acfqp.controlled_predictive_new_starts.v28", "plan": plan,
        "status": "NEW_STARTS_COMPLETE" if all(row["complete"] for row in repetitions) else "NEW_STARTS_COMPLETE_WITH_DECLARED_ISSUES",
        "prefixes": list(prefixes.values()), "query_preparations": list(preparations.values()), "repetitions": repetitions,
        "source_valid_repetition_count": sum(row["source_valid"] for row in repetitions),
        "complete_repetition_count": sum(row["complete"] for row in repetitions),
        "budget_counts": {key: sum(context[key] for repetition in repetitions for context in repetition["contexts"])
            for key in ("completed_K_pair", "shared_normal_stop_pair", "unequal_budget_pair")},
        "accounting": {**accounting, "prefix_board_count": len(prefixes), "prepared_query_count": len(preparations),
            "prefix_physical_batches": prefix_batches, "prefix_physical_draws": prefix_draws, "prefix_provider_counts": dict(prefix_provider),
            "local_physical_batches": local_batches, "local_physical_draws": local_draws,
            "total_physical_batches": prefix_batches+local_batches, "total_physical_draws": prefix_draws+local_draws,
            "provider_counts_by_arm": {arm: dict(value) for arm, value in providers.items()},
            "local_seconds_by_stage_by_arm": {arm: dict(value) for arm, value in local_stages.items()},
            "local_work_counts_by_arm": {arm: dict(value) for arm, value in local_work.items()},
            "query_preparation_work_counts": dict(preparation_work), "evaluation_work_counts": dict(evaluation_work),
            "evaluation_seconds_by_stage": dict(evaluation_stages), "exact_closure_counts_by_board": closure_counts,
            "oracle_by_board": {index: oracle.accounting() for index, oracle in oracles.items()},
            "prefix_artifact_bytes": prefixes_path.stat().st_size, "endpoint_artifact_bytes": endpoints_path.stat().st_size},
        "all_prefix_snapshots_closed_before_local": True, "all_sampling_endpoints_closed_before_oracle": True,
        "endpoint_evaluation_replanning_calls": 0, "prefix_artifact": str(prefixes_path), "endpoint_artifact": str(endpoints_path),
        "elapsed_seconds_before_report_serialization": perf_counter() - started_all,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Fixed new dense H2 roots and shared physical root-only prefixes. Every query prepares its own caches once; each independent-query cost fully attributes prefix acquisition, that preparation and its local run. Actual prefix sampling occurs only once per board. Quality requires complete K in both arms or the same actual count at normal no-candidate stops, plus evaluable policies; unequal counts retain source validity and costs. All endpoint sampling precedes exact evaluation; nested accounting spans are not additive."}
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
        parser.error("the frozen V28 protocol and plan must exist before acquisition")
    report, serialization = run_new_starts(args.plan, args.prefixes, args.endpoints, args.output,
        progress=lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    print(json.dumps({"status": report["status"], "source_valid_repetition_count": report["source_valid_repetition_count"],
        "complete_repetition_count": report["complete_repetition_count"], "output": str(args.output), **serialization}), flush=True)


if __name__ == "__main__":
    main()
