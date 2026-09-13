"""Measure guarded transition-template reuse with frozen deployment artifacts."""
import argparse
import json
from pathlib import Path
from time import perf_counter


ARMS = ("BASE", "TRACE", "PARAM")
PARAMETRIC = ("TRACE", "PARAM")
COMPARISONS = (("TRACE", "BASE"), ("PARAM", "TRACE"), ("PARAM", "BASE"))
PARAMETRIC_METRICS = (
    "contract_calls", "zero_mask_rank_reads", "template_guard_trials", "guard_checks",
    "guard_rank_reads", "template_guard_rejections", "template_hits", "template_misses",
    "template_compilations", "template_bind_calls", "bound_reward_terms",
    "bound_h1_descriptions", "bound_spawn_entries", "compile_symbolic_swipes",
    "compile_symbolic_line_rewrites", "compile_symbolic_action_boards",
    "compile_h1_symbolic_boards", "compile_h0_symbolic_boards", "compile_spawn_candidates",
    "compile_h1_descriptions", "compile_terminal_mass_calls", "compile_equality_tests",
    "compile_goal_tests", "compile_adjacency_tests", "compile_guard_requests",
    "compiled_guards", "compile_terminal_probability_combinations")


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
    started = perf_counter()
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    records = [json.loads(line) for line in
               (directory / "targets.jsonl").read_text().splitlines() if line.strip()]
    completed = [row for row in records if row["status"] == "complete"]
    old_path = directory.parent / "controlled_predictive_composition_v69" / "analysis.json"
    prior_path = directory.parent / "controlled_predictive_effect_v74" / "analysis.json"
    old, prior = [json.loads(path.read_text()) for path in (old_path, prior_path)]
    compile_record = manifest["rule_compile"]
    compile_seconds = compile_record["seconds"]
    names = [row["case"]["name"] if isinstance(row["case"], dict) else row["case"]
             for row in completed]
    complete = (manifest["status"] == "complete" and manifest["target_roots"] == 32 and
                manifest["completed_targets"] == 32 and len(completed) == len(records) == 32 and
                len(set(names)) == 32)
    observation_schedule_valid = manifest["matched_observations"] == 95
    retained_audit = prior["direct_audits"]["SHARED"]
    prior_valid = (prior["complete"] and prior["completed_targets"] == 32 and
        prior["all_artifacts_routing_and_portable_preserved"] and
        prior["inherited_v69_policy_evidence_valid"] and retained_audit["valid"] and
        retained_audit["active_observations"] == 15209 and retained_audit["portable_observations"] == 95)
    audit_reuse_declared = complete and all(row["inherited_v74_audit"] is True for row in completed)

    arms = {}
    for name in ARMS:
        values = [row["arms"][name] for row in completed]
        deployments = [row["deployment"] for row in values]
        workers = [row["portable"] for row in values]
        construction = summed(row["counts"] for row in values)
        routing = summed(row["routing_counts"] for row in deployments)
        package_valid = complete and all(row["package_exact_v74"] for row in values)
        artifact_valid = (package_valid and all(row["kernel_equal"] and row["labels_equal"] and
                          row["plans_equal"] and row["routes_equal"] for row in values))
        portable_valid = (complete and routing.get("observations", 0) == 95 and
            all(row["passed"] and row["exit_code"] == 0 and row["stderr_bytes"] == 0 for row in workers))
        run_seconds = sum(row["times"]["total"] for row in values)
        pc = construction.get("parametric_compiler", {})
        unique_observation_accounting = (complete and name in PARAMETRIC and
            all(row["counts"].get("h2_observation_bindings", 0) ==
                row["counts"].get("unique_h2_geometries", 0) ==
                row["counts"].get("parametric_compiler", {}).get("contract_calls", 0)
                for row in values))
        arms[name] = dict(
            complete_targets=len(values), package_exact_v74=package_valid,
            artifacts_preserved=artifact_valid, portable_passed=portable_valid,
            construction_counts=construction,
            concrete_active_states=construction.get("concrete_active_states", 0),
            geometric_active_states=construction.get("geometric_active_states", 0),
            unique_h2_geometries=construction.get("unique_h2_geometries", 0),
            h2_observation_bindings=construction.get("h2_observation_bindings", 0),
            active_cells_by_h=construction.get("active_cells_by_h", {}),
            concrete_active_by_h=construction.get("concrete_active_by_h", {}),
            grouped_compiler_counts=construction.get("grouped_compiler", {}),
            parametric_compiler_counts=pc,
            parametric_work=({key: pc.get(key, 0) for key in PARAMETRIC_METRICS}
                             if name in PARAMETRIC else None),
            unique_h2_observation_accounting_valid=unique_observation_accounting,
            new_observation_template_hits=(pc.get("template_hits", 0)
                                           if unique_observation_accounting else None),
            planning_counts=summed(row["planning_counts"] for row in deployments),
            routing_counts=routing, actual_cold_observations=routing.get("observations", 0),
            package_bytes=sum(row["package_bytes"] for row in deployments),
            router_bytes=sum(row["router_bytes"] for row in deployments),
            times=dict(case_method_seconds=run_seconds,
                       attributed_rule_compile_seconds=compile_seconds,
                       method_total_seconds=run_seconds + compile_seconds,
                       case_stages=summed(row["times"] for row in values),
                       deployment_stages=summed(row["times"] for row in deployments),
                       worker_command_seconds_included_in_method=sum(
                           row["command_seconds"] for row in workers)))

    preserved = (complete and observation_schedule_valid and audit_reuse_declared and prior_valid and
                 all(row["artifacts_preserved"] and row["portable_passed"] for row in arms.values()))
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

    ratios = {}
    for candidate, baseline in COMPARISONS:
        a, b = arms[candidate], arms[baseline]
        ratios[candidate + "_vs_" + baseline] = dict(
            method_total_seconds=ratio(a["times"]["method_total_seconds"], b["times"]["method_total_seconds"]),
            construction_seconds=ratio(a["times"]["case_stages"].get("construction", 0),
                                       b["times"]["case_stages"].get("construction", 0)),
            geometric_active_states=ratio(a["geometric_active_states"], b["geometric_active_states"]),
            unique_h2_geometries=ratio(a["unique_h2_geometries"], b["unique_h2_geometries"]),
            active_cells=ratio(a["construction_counts"].get("active_states", 0),
                               b["construction_counts"].get("active_states", 0)),
            planning_action_rows=ratio(a["planning_counts"].get("state_action_rows", 0),
                                       b["planning_counts"].get("state_action_rows", 0)),
            package_bytes=ratio(a["package_bytes"], b["package_bytes"]),
            router_bytes=ratio(a["router_bytes"], b["router_bytes"]),
            finite_method_cost_benefit=preserved and
                a["times"]["method_total_seconds"] < b["times"]["method_total_seconds"])
    trace, param = (arms[name]["parametric_work"] for name in PARAMETRIC)
    parameter_work_effects = {key: dict(trace=trace[key], param=param[key],
                                      delta=param[key] - trace[key], ratio=ratio(param[key], trace[key]))
                             for key in PARAMETRIC_METRICS}
    return dict(
        complete=complete, declared_targets=manifest["target_roots"], completed_targets=len(completed),
        incomplete_targets=[row["case"] for row in records if row["status"] != "complete"],
        source_learning_reused=manifest.get("source_learning_reused") is True,
        all_artifacts_routing_and_portable_preserved=preserved,
        inherited_v74_route_evidence_valid=preserved,
        inherited_v69_policy_evidence_valid=inherited, inherited_v69_policy_metrics=inherited_metrics,
        inheritance_sources=dict(route_audit=str(prior_path), policy=str(old_path)),
        inherited_route_observations=15209 if preserved else 0,
        matched_observations=manifest["matched_observations"],
        observation_schedule_valid=observation_schedule_valid,
        arms=arms, ratios=ratios, parameter_work_effects=parameter_work_effects,
        template_reuse_observed=preserved and param["template_hits"] > 0,
        symbolic_compilation_reduction_established=preserved and
            param["template_compilations"] < trace["template_compilations"] and
            param["compile_spawn_candidates"] < trace["compile_spawn_candidates"],
        higher_observation_geometry_count_reduced=preserved and
            arms["PARAM"]["geometric_active_states"] < arms["BASE"]["geometric_active_states"],
        general_strategic_learning_solved=False,
        actual_execution=dict(
            arm_method_seconds=sum(row["times"]["case_method_seconds"] for row in arms.values()),
            rule_compile_seconds=compile_seconds, rule_compile_counts=compile_record["counts"],
            rule_compile_executions=1, construction_executions=len(completed) * len(ARMS),
            cold_worker_executions=len(completed) * len(ARMS),
            cold_route_observations=sum(row["actual_cold_observations"] for row in arms.values()),
            new_full_route_audits=0, new_full_route_audit_observations=0,
            inherited_route_observations=15209 if preserved else 0,
            verification_seconds=sum(row["verification_seconds"] for row in completed),
            case_cleanup_seconds=sum(row["case_cleanup_seconds"] for row in completed),
            summed_case_seconds=sum(row["case_seconds"] for row in completed),
            source_fit_calls=manifest.get("source_fit_calls"), target_ground_calls=manifest.get("target_ground_calls"),
            runner_wall_seconds=manifest["wall_seconds"], peak_rss_bytes=manifest["peak_rss_bytes"]),
        timing_scope="All three methods pay one complete common terminal-rule compilation, executed once. Per-case compiler initialization, construction, binding, deployment, and cold-worker work are included in method totals; displayed stage durations are not additional. Frozen source learning is historical and artifact verification is separate. Timing is one descriptive run.",
        evidence_scope="Each package must exactly equal its retained V74 SHARED package, with exact kernels, labels, plans, and 95 newly executed cold routes. The unchanged V74 worker/router and its previously complete 15209-observation audit supply inherited route evidence; no new full-route audit is run. This inheritance is required before reporting the retained 448 optimal root queries and 1227 strict switches. Separate numeric-binding probes and exploratory shape diagnostics are not read here.",
        work_scope="Parametric counters describe construction only; all three deployments still use the same V74 SHARED router. Initial H2 observation bindings and retained geometry are separate from template compilation, symbolic candidate expansion, guard trials, and reward binding. Template hits skip compilation but still bind H1 descriptions, rewards, and individual spawn entries. Hits are new-observation hits only when the builder's complete geometry deduplication accounting matches; cross-numeric-binding transfer requires the separate probe. Concrete boards placed in symbolic containers do not by themselves constitute compression.",
        analysis_seconds_before_write=perf_counter() - started)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.input)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in
                     ("complete", "all_artifacts_routing_and_portable_preserved",
                      "inherited_v69_policy_evidence_valid", "template_reuse_observed",
                      "symbolic_compilation_reduction_established", "ratios")}, indent=2))
