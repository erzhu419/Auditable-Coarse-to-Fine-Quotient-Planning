"""Summarize direct H1 construction separately from candidate enumeration."""
import argparse
import json
from pathlib import Path
from time import perf_counter


ARMS = ("FULL_BASE", "COMPOSED_BASE", "FULL_LOCAL", "COMPOSED_LOCAL")
COMPARISONS = (("FULL_LOCAL", "FULL_BASE"), ("COMPOSED_LOCAL", "COMPOSED_BASE"),
               ("COMPOSED_LOCAL", "FULL_LOCAL"))


def summed(rows):
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
    """Read the main cohort and its V69 evidence only; no probe data or execution."""
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
    expected_observations = manifest["matched_observations"]
    cases_with_h1 = sum(row["arms"]["FULL_BASE"]["counts"]
                        .get("concrete_active_by_h", {}).get("1", 0) > 0 for row in completed)
    observation_schedule_valid = (manifest["original_observations"] == 60 and
        manifest["added_h1_observations"] == 27 and cases_with_h1 == 27 and
        expected_observations == manifest["original_observations"] + manifest["added_h1_observations"])
    audits_valid = (complete and active_observations == expected_active and
                    observation_schedule_valid and portable_observations == expected_observations and
                    all(row["audit"]["valid"] for row in completed))

    arms = {}
    for name in ARMS:
        values = [row["arms"][name] for row in completed]
        deployments = [row["deployment"] for row in values]
        workers = [row["portable"] for row in values]
        construction = summed(row["counts"] for row in values)
        artifact_valid = (complete and all(row["kernel_equal"] and row["labels_equal"] and
                          row["plans_equal"] and row["routes_equal"] for row in values))
        portable_valid = (complete and all(row["passed"] and row["exit_code"] == 0 and
                                          row["stderr_bytes"] == 0 for row in workers))
        run_seconds = sum(row["times"]["total"] for row in values)
        concrete_by_h = construction.get("concrete_states_by_h", {})
        active_by_h = construction.get("concrete_active_by_h", {})
        arms[name] = dict(
            complete_targets=len(values), artifacts_preserved=artifact_valid,
            portable_passed=portable_valid, construction_counts=construction,
            concrete_active_states=construction.get("concrete_active_states", 0),
            active_cells_by_h=construction.get("active_cells_by_h", {}),
            concrete_active_by_h=active_by_h, concrete_states_by_h=concrete_by_h,
            h1_materialized_states=concrete_by_h.get("1", 0),
            h1_boards_generated=construction.get("h1_boards_generated"),
            higher_materialized_active_states=sum(value for h, value in active_by_h.items()
                                                 if int(h) > 1),
            direct_h1_contract_evaluations=construction.get("direct_h1_contract_evaluations", 0),
            boundary_spawn_candidates=construction.get("boundary_spawn_candidates", 0),
            active_boundary_candidates=construction.get("active_boundary_candidates", 0),
            local_compiler_counts=construction.get("local_compiler", {}),
            planning_counts=summed(row["planning_counts"] for row in deployments),
            routing_counts=summed(row["routing_counts"] for row in deployments),
            package_bytes=sum(row["package_bytes"] for row in deployments),
            router_bytes=sum(row["router_bytes"] for row in deployments),
            times=dict(case_method_seconds=run_seconds,
                       attributed_rule_compile_seconds=compile_seconds,
                       method_total_seconds=run_seconds + compile_seconds,
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
            h1_materialized_states=ratio(a["h1_materialized_states"], b["h1_materialized_states"]),
            higher_materialized_active_states=ratio(a["higher_materialized_active_states"],
                                                    b["higher_materialized_active_states"]),
            active_cells=ratio(ac.get("active_states", 0), bc.get("active_states", 0)),
            planning_action_rows=ratio(a["planning_counts"].get("state_action_rows", 0),
                                       b["planning_counts"].get("state_action_rows", 0)),
            package_bytes=ratio(a["package_bytes"], b["package_bytes"]),
            router_bytes=ratio(a["router_bytes"], b["router_bytes"]))
        effects[key] = dict(
            isolated_factor="local_h1_construction" if baseline.endswith("BASE") else "state_quotient",
            saved_concrete_states=bc.get("concrete_states", 0) - ac.get("concrete_states", 0),
            saved_generated_successors=bc.get("concrete_successor_entries", 0) - ac.get("concrete_successor_entries", 0),
            saved_h1_materialized_states=b["h1_materialized_states"] - a["h1_materialized_states"],
            higher_materialized_active_states_delta=a["higher_materialized_active_states"] -
                                                    b["higher_materialized_active_states"],
            active_cells_delta=ac.get("active_states", 0) - bc.get("active_states", 0),
            candidate_direct_h1_contract_evaluations=a["direct_h1_contract_evaluations"],
            candidate_boundary_spawn_candidates=a["boundary_spawn_candidates"],
            candidate_active_boundary_candidates=a["active_boundary_candidates"],
            finite_method_cost_benefit=preserved and
                a["times"]["method_total_seconds"] < b["times"]["method_total_seconds"])

    local, baseline = arms["COMPOSED_LOCAL"], arms["COMPOSED_BASE"]
    result = dict(
        complete=complete, declared_targets=manifest["target_roots"], completed_targets=len(completed),
        incomplete_targets=[row["case"] for row in records if row["status"] != "complete"],
        source_learning_reused=manifest.get("source_learning_reused") is True,
        all_artifacts_routing_and_portable_preserved=preserved,
        inherited_v69_policy_evidence_valid=inherited,
        inherited_v69_policy_metrics=inherited_metrics, inheritance_source=str(old_path),
        active_observations=active_observations, matched_observations=portable_observations,
        original_observations=manifest["original_observations"],
        added_h1_observations=manifest["added_h1_observations"],
        observation_schedule_valid=observation_schedule_valid,
        arms=arms, ratios=ratios, effects=effects,
        finite_h1_board_materialization_removed=(preserved and
            local["h1_boards_generated"] == 0 and local["h1_materialized_states"] == 0 and
            baseline["h1_materialized_states"] > 0),
        local_boundary_candidates_still_enumerated=local["boundary_spawn_candidates"] > 0,
        higher_materialized_active_states_reduced=(preserved and
            local["higher_materialized_active_states"] < baseline["higher_materialized_active_states"]),
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
        timing_scope="All four methods attribute one full V71 terminal-rule compilation. That compilation executes once in actual_execution. Per-case LocalCompiler initialization is already included in LOCAL construction. Method totals sum case times.total plus the attributed compile fee; stage and worker times are included, not additional. Frozen source learning is historical, verification is separate, and this is one descriptive timing run.",
        evidence_scope="This analysis reads only the 32-root frozen main cohort and its V69 evidence, not the separate new-observation probe. The four methods receive the same 60 old observations plus the first retained H1 observation from each of 27 eligible roots. Policy inheritance requires preserved exact kernels, active labels/routes, all query plans, portable results, and valid audits. H1 board materialization, direct contract evaluation, boundary candidate enumeration, and higher-layer states are reported separately. Fewer generated boards do not establish fewer boundary candidates or new general strategic learning.",
        counter_scope="BASE h1_boards_generated is null when that generation counter was not recorded; concrete_states_by_h still gives materialized distinct H1 states. Boundary and direct-contract counters describe LOCAL operations, not the size of the full mathematical support. Nested local_compiler counts include line work and reuse.",
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
                      "inherited_v69_policy_evidence_valid", "finite_h1_board_materialization_removed",
                      "local_boundary_candidates_still_enumerated", "ratios")}, indent=2))
