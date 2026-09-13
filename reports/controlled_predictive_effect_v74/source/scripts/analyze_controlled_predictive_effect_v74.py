"""Compare early action effects and shared successor work with full costs."""
import argparse
import json
from pathlib import Path
from time import perf_counter


ARMS = ("BASE", "LATE", "EARLY", "SHARED")
DIRECT = ("LATE", "EARLY", "SHARED")
COMPARISONS = (("LATE", "BASE"), ("EARLY", "BASE"), ("EARLY", "LATE"),
               ("SHARED", "EARLY"), ("SHARED", "BASE"))
WORK_METRICS = ("contract_materializations", "terminal_probability_combinations",
                    "contract_fraction_accumulations", "predicate_calls",
                    "predicate_materializations", "candidate_predicate_evaluations",
                    "terminal_predicate_evaluations", "candidate_action_predicate_evaluations",
                    "candidate_action_changed_tests", "line_evaluations", "line_lookups",
                    "spawn_candidates", "spawn_groups", "incoming_probability_evaluations",
                    "incoming_group_probability_additions", "effect_key_constructions",
                    "effect_cache_lookups", "effect_cache_hits", "effect_cache_entries",
                    "effect_score_aggregations", "effect_output_line_references",
                    "effect_vacancy_keys", "effect_exact_output_keys",
                    "successor_group_cache_lookups", "successor_group_cache_hits",
                    "successor_group_materializations", "successor_group_cached_groups")


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
    old = json.loads(old_path.read_text())
    compile_record = manifest["rule_compile"]
    compile_seconds = compile_record["seconds"]
    names = [row["case"]["name"] if isinstance(row["case"], dict) else row["case"]
             for row in completed]
    complete = (manifest["status"] == "complete" and manifest["target_roots"] == 32 and
                manifest["completed_targets"] == 32 and len(completed) == len(records) == 32 and
                len(set(names)) == 32)
    expected_active = old["arms"]["FULL"]["construction"]["concrete_active_states"]
    active_observations = sum(row["audit"]["active_observations"] for row in completed)
    portable_observations = sum(row["audit"]["portable_observations"] for row in completed)
    observation_schedule_valid = (manifest["original_observations"] == 87 and
        manifest["added_h2_observations"] == 8 and manifest["matched_observations"] == 95)
    direct_audits = {}
    for name in DIRECT:
        audits = [row["direct_audits"][name] for row in completed]
        checked_active = sum(row["active_observations"] for row in audits)
        checked_portable = sum(row["portable_observations"] for row in audits)
        direct_audits[name] = dict(
            valid=complete and checked_active == expected_active and checked_portable == 95 and
                  all(row["valid"] for row in audits),
            active_observations=checked_active, portable_observations=checked_portable,
            counts=summed(row.get("counts", {}) for row in audits))
    audits_valid = (complete and observation_schedule_valid and active_observations == expected_active and
                    portable_observations == 95 and all(row["audit"]["valid"] for row in completed) and
                    all(row["valid"] for row in direct_audits.values()))

    arms = {}
    for name in ARMS:
        values = [row["arms"][name] for row in completed]
        deployments = [row["deployment"] for row in values]
        workers = [row["portable"] for row in values]
        construction = summed(row["counts"] for row in values)
        routing = summed(row["routing_counts"] for row in deployments)
        artifact_valid = (complete and all(row["kernel_equal"] and row["labels_equal"] and
                          row["plans_equal"] and row["routes_equal"] for row in values))
        portable_valid = (complete and all(row["passed"] and row["exit_code"] == 0 and
                                          row["stderr_bytes"] == 0 for row in workers))
        run_seconds = sum(row["times"]["total"] for row in values)
        concrete_by_h = construction.get("concrete_states_by_h", {})
        geometric_active = (construction.get("concrete_active_states", 0) if name == "BASE"
                            else construction.get("geometric_active_states", 0))
        grouped = construction.get("grouped_compiler", {})
        measured_work = ({key: grouped.get(key, 0) + routing.get(key, 0)
                          for key in WORK_METRICS} if name in DIRECT else None)
        arms[name] = dict(
            complete_targets=len(values), artifacts_preserved=artifact_valid,
            portable_passed=portable_valid, construction_counts=construction,
            concrete_active_states=construction.get("concrete_active_states", 0),
            geometric_active_states=geometric_active,
            h2_literal_states=concrete_by_h.get("2", 0),
            unique_h2_geometries=construction.get("unique_h2_geometries", 0),
            active_cells_by_h=construction.get("active_cells_by_h", {}),
            concrete_active_by_h=construction.get("concrete_active_by_h", {}),
            concrete_states_by_h=concrete_by_h,
            grouped_compiler_counts=grouped,
            combined_construction_and_routing_work=measured_work,
            planning_counts=summed(row["planning_counts"] for row in deployments),
            routing_counts=routing,
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

    ratios = {}
    for candidate, baseline in COMPARISONS:
        a, b = arms[candidate], arms[baseline]
        ac, bc = a["construction_counts"], b["construction_counts"]
        ratios[candidate + "_vs_" + baseline] = dict(
            method_total_seconds=ratio(a["times"]["method_total_seconds"], b["times"]["method_total_seconds"]),
            concrete_active_states=ratio(a["concrete_active_states"], b["concrete_active_states"]),
            geometric_active_states=ratio(a["geometric_active_states"], b["geometric_active_states"]),
            generated_successors=ratio(ac.get("concrete_successor_entries", 0), bc.get("concrete_successor_entries", 0)),
            active_cells=ratio(ac.get("active_states", 0), bc.get("active_states", 0)),
            planning_action_rows=ratio(a["planning_counts"].get("state_action_rows", 0),
                                       b["planning_counts"].get("state_action_rows", 0)),
            package_bytes=ratio(a["package_bytes"], b["package_bytes"]),
            router_bytes=ratio(a["router_bytes"], b["router_bytes"]),
            finite_method_cost_benefit=preserved and
                a["times"]["method_total_seconds"] < b["times"]["method_total_seconds"])

    late = arms["LATE"]["combined_construction_and_routing_work"]
    early = arms["EARLY"]["combined_construction_and_routing_work"]
    shared = arms["SHARED"]["combined_construction_and_routing_work"]
    work_effects = {}
    for candidate, baseline in (("EARLY", "LATE"), ("SHARED", "EARLY")):
        a = arms[candidate]["combined_construction_and_routing_work"]
        b = arms[baseline]["combined_construction_and_routing_work"]
        work_effects[candidate + "_vs_" + baseline] = {
            key: dict(candidate=a[key], baseline=b[key], delta=a[key] - b[key],
                      ratio=ratio(a[key], b[key])) for key in WORK_METRICS}
    result = dict(
        complete=complete, declared_targets=manifest["target_roots"], completed_targets=len(completed),
        incomplete_targets=[row["case"] for row in records if row["status"] != "complete"],
        source_learning_reused=manifest.get("source_learning_reused") is True,
        all_artifacts_routing_and_portable_preserved=preserved,
        inherited_v69_policy_evidence_valid=inherited,
        inherited_v69_policy_metrics=inherited_metrics, inheritance_source=str(old_path),
        active_observations=active_observations, matched_observations=portable_observations,
        original_observations=manifest["original_observations"],
        added_h2_observations=manifest["added_h2_observations"],
        observation_schedule_valid=observation_schedule_valid,
        direct_audits=direct_audits, arms=arms, ratios=ratios, work_effects=work_effects,
        early_terminal_predicate_reduction_established=preserved and
            early["terminal_predicate_evaluations"] < late["terminal_predicate_evaluations"],
        early_spawn_candidate_tests_reduced=preserved and early["spawn_candidates"] < late["spawn_candidates"],
        early_predicate_calls_reduced=preserved and early["predicate_calls"] < late["predicate_calls"],
        shared_spawn_candidate_reduction_established=preserved and shared["spawn_candidates"] < early["spawn_candidates"],
        shared_terminal_predicate_reduction_established=preserved and
            shared["terminal_predicate_evaluations"] < early["terminal_predicate_evaluations"],
        higher_geometry_count_reduced=preserved and arms["SHARED"]["geometric_active_states"] <
                                                   arms["BASE"]["geometric_active_states"],
        general_strategic_learning_solved=False,
        actual_execution=dict(
            arm_method_seconds=sum(row["times"]["case_method_seconds"] for row in arms.values()),
            rule_compile_seconds=compile_seconds, rule_compile_counts=compile_record["counts"],
            rule_compile_executions=1,
            construction_executions=len(completed) * len(ARMS),
            cold_worker_executions=len(completed) * len(ARMS),
            verification_seconds=sum(row["verification_seconds"] for row in completed),
            audit_counts=summed(row["counts"] for row in direct_audits.values()),
            direct_audit_active_observations=sum(row["active_observations"] for row in direct_audits.values()),
            case_cleanup_seconds=sum(row["case_cleanup_seconds"] for row in completed),
            summed_case_seconds=sum(row["case_seconds"] for row in completed),
            runner_wall_seconds=manifest["wall_seconds"], peak_rss_bytes=manifest["peak_rss_bytes"]),
        timing_scope="All four methods pay one complete terminal-rule compilation; actual_execution counts its single execution once. Per-case compiler initialization, construction, deployment, and cold-worker work are included in case method totals. Displayed stage durations must not be added again. Frozen source learning is historical, and verification is separate. Timing is a single descriptive run.",
        evidence_scope="Only the 32-root frozen main cohort and V69 policy evidence are read; separate prediction probes are excluded. All methods receive the same 95 fixed observations. LATE, EARLY, and SHARED are each audited over all 15209 active observations before inheriting the 448 optimal root queries and 1227 strict switches. Geometry counts include complete H2 row-block contexts as well as literal higher boards, so fewer flat boards do not imply less geometry or a new semantic quotient.",
        work_scope="Work effects combine charged construction and cold routing, excluding verification. Candidate scans, action-effect keys, actual terminal predicates, contract materializations, and probability combinations are separate counters. BASE does not implement these effect counters. The unique cohort is counted once, while actual_execution sums all three full direct-router audits. EARLY/LATE isolates action-effect reuse; SHARED/EARLY isolates same-afterstate successor reuse. SHARED additionally retains exact afterstate geometry as cache keys; cache materializations and stored group counts are reported rather than treating reuse as cost-free.",
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
                      "inherited_v69_policy_evidence_valid", "early_terminal_predicate_reduction_established",
                      "shared_spawn_candidate_reduction_established", "higher_geometry_count_reduced",
                      "work_effects", "ratios")}, indent=2))
