"""Summarize the frozen 2x2 contract/terminal construction comparison."""
import argparse
import json
from pathlib import Path
from time import perf_counter


ARMS = ("FULL_ENUM", "COMPOSED_ENUM", "FULL_SYMBOLIC", "COMPOSED_SYMBOLIC")
COMPARISONS = (("FULL_SYMBOLIC", "FULL_ENUM"),
               ("COMPOSED_SYMBOLIC", "COMPOSED_ENUM"),
               ("COMPOSED_SYMBOLIC", "FULL_SYMBOLIC"))


def summed(rows):
    """Sum numeric counters, including the declared per-horizon dictionaries."""
    result = {}
    for row in rows:
        for key, value in row.items():
            if isinstance(value, dict):
                result[key] = summed((result.get(key, {}), value))
            elif type(value) in (int, float):
                result[key] = result.get(key, 0) + value
    return result


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def analyze(directory):
    """Read retained JSON; no model, query, or experiment is executed here."""
    started = perf_counter()
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    records = [json.loads(line) for line in
               (directory / "targets.jsonl").read_text().splitlines() if line.strip()]
    completed = [row for row in records if row["status"] == "complete"]
    old_path = directory.parent / "controlled_predictive_composition_v69" / "analysis.json"
    old = json.loads(old_path.read_text())
    compile_record = manifest["rule_compile"]
    compile_seconds = compile_record["seconds"]
    names = [row["case"]["name"] if isinstance(row["case"], dict) else row["case"]
             for row in completed]
    complete = (manifest["status"] == "complete" and manifest["target_roots"] == 32 and
                manifest["completed_targets"] == 32 and len(completed) == len(records) == 32 and
                len(set(names)) == 32)
    active_observations = sum(row["audit"]["active_observations"] for row in completed)
    portable_observations = sum(row["audit"]["portable_observations"] for row in completed)
    expected_active = old["arms"]["FULL"]["construction"]["concrete_active_states"]
    audits_valid = (complete and active_observations == expected_active and
                    portable_observations == 60 and all(row["audit"]["valid"] for row in completed))

    arms = {}
    for name in ARMS:
        values = [row["arms"][name] for row in completed]
        deployments = [row["deployment"] for row in values]
        workers = [row["portable"] for row in values]
        construction = summed(row["counts"] for row in values)
        construction.setdefault("h0_boards_generated", 0)
        artifact_valid = (complete and all(row["kernel_equal"] and row["labels_equal"] and
                          row["plans_equal"] and row["routes_equal"] for row in values))
        portable_valid = (complete and all(row["passed"] and row["exit_code"] == 0 and
                                          row["stderr_bytes"] == 0 for row in workers))
        run_seconds = sum(row["times"]["total"] for row in values)
        attributed_compile = compile_seconds if name.endswith("SYMBOLIC") else 0.0
        arms[name] = dict(
            complete_targets=len(values), artifacts_preserved=artifact_valid,
            portable_passed=portable_valid, construction_counts=construction,
            concrete_active_states=construction.get("concrete_active_states", 0),
            active_cells_by_h=construction.get("active_cells_by_h", {}),
            concrete_active_by_h=construction.get("concrete_active_by_h", {}),
            concrete_states_by_h=construction.get("concrete_states_by_h", {}),
            planning_counts=summed(row["planning_counts"] for row in deployments),
            routing_counts=summed(row["routing_counts"] for row in deployments),
            package_bytes=sum(row["package_bytes"] for row in deployments),
            router_bytes=sum(row["router_bytes"] for row in deployments),
            times=dict(case_method_seconds=run_seconds,
                       attributed_rule_compile_seconds=attributed_compile,
                       method_total_seconds=run_seconds + attributed_compile,
                       case_stages=summed(row["times"] for row in values),
                       deployment_stages=summed(row["times"] for row in deployments),
                       worker_command_seconds_included_in_method=sum(
                           row["command_seconds"] for row in workers)))

    preserved = audits_valid and all(row["artifacts_preserved"] and row["portable_passed"]
                                    for row in arms.values())
    old_valid = (old["complete"] and old["policy_and_dynamics_preserved"] and
                 old["portable_passed"] and old["completed_targets"] == 32 and
                 all(old["arms"][variant]["root_queries"] == 448 and
                     old["arms"][variant]["optimal_executable_root_queries"] == 448 and
                     old["arms"][variant]["strict_query_switches"] ==
                     {"required": 1227, "violations": 0}
                     for variant in ("FULL", "COMPOSED")))
    inherited = preserved and old_valid
    inherited_metrics = None
    if inherited:
        inherited_metrics = {variant: dict(
            root_queries=old["arms"][variant]["root_queries"],
            optimal_executable_root_queries=old["arms"][variant]["optimal_executable_root_queries"],
            strict_query_switches=old["arms"][variant]["strict_query_switches"])
            for variant in ("FULL", "COMPOSED")}

    ratios, effects = {}, {}
    for candidate, baseline in COMPARISONS:
        a, b = arms[candidate], arms[baseline]
        ac, bc = a["construction_counts"], b["construction_counts"]
        key = candidate + "_vs_" + baseline
        ratios[key] = dict(
            method_total_seconds=ratio(a["times"]["method_total_seconds"], b["times"]["method_total_seconds"]),
            concrete_states=ratio(ac.get("concrete_states", 0), bc.get("concrete_states", 0)),
            generated_successors=ratio(ac.get("concrete_successor_entries", 0), bc.get("concrete_successor_entries", 0)),
            concrete_active_states=ratio(a["concrete_active_states"], b["concrete_active_states"]),
            active_cells=ratio(ac.get("active_states", 0), bc.get("active_states", 0)),
            planning_action_rows=ratio(a["planning_counts"].get("state_action_rows", 0),
                                       b["planning_counts"].get("state_action_rows", 0)),
            package_bytes=ratio(a["package_bytes"], b["package_bytes"]),
            router_bytes=ratio(a["router_bytes"], b["router_bytes"]))
        effects[key] = dict(
            isolated_factor="terminal_construction" if baseline.endswith("ENUM") else "state_quotient",
            saved_concrete_states=bc.get("concrete_states", 0) - ac.get("concrete_states", 0),
            saved_generated_successors=bc.get("concrete_successor_entries", 0) - ac.get("concrete_successor_entries", 0),
            candidate_h0_boards_generated=ac.get("h0_boards_generated", 0),
            baseline_h0_boards_generated=bc.get("h0_boards_generated", 0),
            concrete_active_states_delta=a["concrete_active_states"] - b["concrete_active_states"],
            active_cells_delta=ac.get("active_states", 0) - bc.get("active_states", 0),
            finite_method_cost_benefit=preserved and
                a["times"]["method_total_seconds"] < b["times"]["method_total_seconds"])

    symbolic_pairs = COMPARISONS[:2]
    result = dict(
        complete=complete, declared_targets=manifest["target_roots"],
        completed_targets=len(completed),
        incomplete_targets=[row["case"] for row in records if row["status"] != "complete"],
        source_learning_reused=manifest.get("source_learning_reused") is True,
        all_artifacts_routing_and_portable_preserved=preserved,
        inherited_v69_policy_evidence_valid=inherited,
        inherited_v69_policy_metrics=inherited_metrics, inheritance_source=str(old_path),
        active_observations=active_observations, matched_observations=portable_observations,
        arms=arms, ratios=ratios, effects=effects,
        terminal_generation_reduction_established=preserved and all(
            arms[candidate]["construction_counts"]["h0_boards_generated"] == 0 and
            arms[candidate]["construction_counts"].get("concrete_successor_entries", 0) <
            arms[baseline]["construction_counts"].get("concrete_successor_entries", 0)
            for candidate, baseline in symbolic_pairs),
        nonterminal_distinct_states_reduced=preserved and any(
            arms[candidate]["concrete_active_states"] < arms[baseline]["concrete_active_states"]
            for candidate, baseline in symbolic_pairs),
        general_strategic_learning_solved=False,
        actual_execution=dict(
            arm_method_seconds=sum(row["times"]["case_method_seconds"] for row in arms.values()),
            rule_compile_seconds=compile_seconds, rule_compile_counts=compile_record["counts"],
            rule_compile_executions=1,
            construction_executions=len(completed) * len(ARMS),
            cold_worker_executions=len(completed) * len(ARMS),
            verification_seconds=sum(row["verification_seconds"] for row in completed),
            audit_counts=summed(row["audit"].get("counts", {}) for row in completed),
            case_cleanup_seconds=sum(row["case_cleanup_seconds"] for row in completed),
            summed_case_seconds=sum(row["case_seconds"] for row in completed),
            runner_wall_seconds=manifest["wall_seconds"], peak_rss_bytes=manifest["peak_rss_bytes"]),
        timing_scope="Each arm is built and cold-loaded independently once per target. Method totals sum case times.total and attribute one complete rule compilation to each SYMBOLIC arm. Rule compilation actually executes once and is counted once in actual_execution. Deployment, worker wall time, and stage durations are already included in method totals. Frozen source learning is a historical expense, and verification is outside method cost. Timings are one descriptive run.",
        evidence_scope="The same 32 frozen V69 supports and rule are compared in a 2x2 design. Inheritance requires exact kernels, all active labels, policies, routes, and portable results with valid audits. Symbolic construction avoids terminal board materialization; concrete nonterminal states and active abstract cells are reported separately. This is not new strategic generalization or a new ground-policy experiment.",
        analysis_seconds_before_write=perf_counter() - started)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.input)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in
                     ("complete", "all_artifacts_routing_and_portable_preserved",
                      "inherited_v69_policy_evidence_valid", "terminal_generation_reduction_established",
                      "nonterminal_distinct_states_reduced", "ratios")}, indent=2))
