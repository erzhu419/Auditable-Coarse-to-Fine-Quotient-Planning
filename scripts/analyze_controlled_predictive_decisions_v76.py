"""Compare source-trained H2 decisions using specified execution and full costs."""
import argparse
from itertools import combinations
import json
import math
from pathlib import Path
from time import perf_counter


METHODS = ("EXACT", "GREEDY", "RULE", "SELECTIVE")
METRICS = ("reward", "failure", "success", "value")
TOLERANCE = 1e-12


def statistics(values):
    values = [float(value) for value in values if value is not None]
    total = math.fsum(values)
    return dict(count=len(values), total=total, mean=total / len(values) if values else None,
                minimum=min(values) if values else None, maximum=max(values) if values else None)


def quality(rows):
    rows = list(rows)
    actual = [row for row in rows if row["execution_verified"] and row["actual_metrics"] is not None]
    result = dict(queries=len(rows), execution_verified=len(actual),
        root_legal=sum(row["root_action_legal"] for row in rows),
        root_optimal=sum(row["root_action_optimal_membership"] for row in rows),
        continuation_optimal=sum(row["continuation_optimal"] is True for row in rows),
        fully_optimal_execution=sum(row["execution_verified"] and row["root_action_optimal_membership"]
            and row["continuation_optimal"] is True for row in rows),
        root_decision_regret=statistics(row["root_decision_regret"] for row in rows),
        continuation_regret=statistics(row["continuation_regret"] for row in rows),
        total_regret=statistics(row["total_regret"] for row in rows),
        actual_metrics={metric: statistics(row["actual_metrics"][metric] for row in actual)
                        for metric in METRICS},
        reference_metrics={metric: statistics(row["reference_metrics"][metric] for row in rows)
                           for metric in METRICS},
        deltas_to_reference={metric: statistics(row["deltas_to_reference"][metric] for row in actual)
                             for metric in METRICS},
        failure_increase_queries=sum(row["failure_delta"] > TOLERANCE for row in actual),
        failure_decrease_queries=sum(row["failure_delta"] < -TOLERANCE for row in actual),
        success_increase_queries=sum(row["success_delta"] > TOLERANCE for row in actual),
        success_decrease_queries=sum(row["success_delta"] < -TOLERANCE for row in actual))
    result["root_optimal_fraction"] = result["root_optimal"] / len(rows) if rows else None
    result["fully_optimal_execution_fraction"] = result["fully_optimal_execution"] / len(rows) if rows else None
    return result


def analyze(directory):
    started = perf_counter()
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    audit = json.loads((directory / "audit.json").read_text())
    source_summary = json.loads((directory / "source_summary.json").read_text())
    workers = {name: json.loads((directory / f"{name}.json").read_text()) for name in METHODS}
    query_names, trained = manifest["query_names"], set(manifest["train_query_names"])
    cases = audit["cases"]
    names = {case["name"] for case in cases}
    expected = manifest["target_cases"] * len(query_names)
    expected_seen = manifest["target_cases"] * len(trained)
    expected_heldout = expected - expected_seen
    worker_cases = {method: {case["name"]: case for case in worker["cases"]}
                    for method, worker in workers.items()}
    roster_complete = (manifest["target_cases"] == len(cases) == len(names) == 48 and
        len(query_names) == len(set(query_names)) == 14 and len(trained) == 6 and trained <= set(query_names) and
        all(len(case["queries"]) == 14 and {query["query_name"] for query in case["queries"]} == set(query_names)
            for case in cases) and all(set(entries) == names for entries in worker_cases.values()) and
        all(set(case["actions"]) == set(query_names) and set(case["h1_actions"]) == set(query_names)
            for worker in workers.values() for case in worker["cases"]))
    seen_labels_valid = all(query["seen_query"] == (query["query_name"] in trained)
                            for case in cases for query in case["queries"])
    executions_succeeded = all(manifest["worker_commands"][name]["exit_code"] == 0 and
        not workers[name]["ground_imports"] and not workers[name]["forbidden_imports"] for name in METHODS)
    integrity = dict(manifest_complete=manifest["status"] == "complete",
        audit_complete=audit["complete"] is True,
        ground_models_valid=audit["valid_ground_models"] is True,
        h1_encoder_valid=audit["h1_encoder_valid"] is True,
        source_target_disjoint=audit["source_target_disjoint"] is True,
        roster_complete=roster_complete, seen_labels_valid=seen_labels_valid,
        worker_execution_succeeded=executions_succeeded,
        predicted_kernels_equal=all(case["predicted_kernel_equal"] for case in cases))
    integrity_valid = all(integrity.values())
    input_seconds, source_seconds = manifest["input_preparation_seconds"], manifest["source_cost_seconds"]
    exact_total = input_seconds + manifest["worker_commands"]["EXACT"]["seconds"]
    methods = {}
    for method in METHODS:
        all_rows, seen_rows, heldout_rows = [], [], []
        by_query = {name: [] for name in query_names}
        matched_h1 = []
        for case in cases:
            for query in case["queries"]:
                row = query["methods"][method]
                all_rows.append(row)
                (seen_rows if query["seen_query"] else heldout_rows).append(row)
                by_query[query["query_name"]].append(row)
                matched_h1.append(query["matched_h1"][method])
        overall = quality(all_rows)
        matched = dict(queries=len(matched_h1),
            legal=sum(row["action_legal"] for row in matched_h1),
            optimal=sum(row["action_optimal_membership"] for row in matched_h1),
            metrics_equal=sum(row["metrics_equal"] is True for row in matched_h1))
        command = manifest["worker_commands"][method]
        attributed_source = source_seconds if method in ("RULE", "SELECTIVE") else 0.0
        total = command["seconds"] + input_seconds + attributed_source
        correct = (len(all_rows) == expected and len(seen_rows) == expected_seen and
            len(heldout_rows) == expected_heldout and overall["execution_verified"] == expected and
            overall["fully_optimal_execution"] == expected and
            all(row["total_regret"] is not None and row["total_regret"] <= TOLERANCE for row in all_rows) and
            matched["queries"] == matched["legal"] == matched["optimal"] == matched["metrics_equal"] == expected)
        methods[method] = dict(overall=overall, seen_queries=quality(seen_rows),
            heldout_queries=quality(heldout_rows), by_query={name: quality(rows) for name, rows in by_query.items()},
            matched_h1=matched, worker_counts=workers[method]["counts"], worker_work=workers[method]["work"],
            worker_times=workers[method]["times"], costs=dict(cold_worker_command_seconds=command["seconds"],
                input_preparation_seconds=input_seconds, attributed_source_seconds=attributed_source,
                total_seconds=total, ratio_to_exact=total / exact_total,
                delta_to_exact_seconds=total - exact_total, stderr_bytes=command["stderr_bytes"]),
            quality_preserved=correct,
            adoption=dict(reference=method == "EXACT", integrity_valid=integrity_valid,
                all_root_and_h1_decisions_optimal=correct, lower_total_cost_than_exact=total < exact_total,
                eligible=integrity_valid and correct and total < exact_total if method != "EXACT" else None))

    selective_groups = {"accepted_rule": [], "exact_fallback": [], "no_action": []}
    selective_by_split = {split: {group: [] for group in selective_groups} for split in ("seen", "heldout")}
    for case in cases:
        selections = worker_cases["SELECTIVE"][case["name"]]["actions"]
        for query in case["queries"]:
            decision = selections[query["query_name"]]
            group = ("no_action" if decision["action"] is None else
                     "exact_fallback" if decision["fallback"] else "accepted_rule")
            row = query["methods"]["SELECTIVE"]
            selective_groups[group].append(row)
            selective_by_split["seen" if query["seen_query"] else "heldout"][group].append(row)
    selective = dict(groups={name: quality(rows) for name, rows in selective_groups.items()},
        by_split={split: {name: quality(rows) for name, rows in groups.items()}
                  for split, groups in selective_by_split.items()},
        threshold_scope="Source-score routing rule; confidence thresholds are not a safety certificate.")

    obligations = 0
    violations = {method: 0 for method in METHODS}
    case_switches = []
    for case in cases:
        count, failed = 0, {method: 0 for method in METHODS}
        for left, right in combinations(case["queries"], 2):
            left_set = set(left["methods"]["EXACT"]["optimal_actions"])
            right_set = set(right["methods"]["EXACT"]["optimal_actions"])
            if left_set.isdisjoint(right_set):
                count += 1
                for method in METHODS:
                    failed[method] += left["methods"][method]["selected_action"] == right["methods"][method]["selected_action"]
        obligations += count
        for method in METHODS:
            violations[method] += failed[method]
        case_switches.append(dict(case=case["name"], obligations=count, violations=failed))
    switch_summary = dict(obligations=obligations, violations=violations, cases=case_switches,
        definition="Each pair of queries with disjoint ground-optimal action sets requires a changed root action.")
    actual_worker_seconds = math.fsum(command["seconds"] for command in manifest["worker_commands"].values())
    return dict(schema="acfqp.decision_analysis.v76", complete=integrity["manifest_complete"] and integrity["audit_complete"]
            and roster_complete, integrity=integrity, integrity_valid=integrity_valid,
        target_cases=len(cases), total_queries=expected, seen_queries=expected_seen,
        heldout_queries=expected_heldout, methods=methods, selective=selective,
        strict_query_switches=switch_summary, source_summary=source_summary,
        actual_executed_cost_accounting=dict(source_once_seconds=source_seconds,
            input_preparation_once_seconds=input_seconds, all_cold_worker_commands_seconds=actual_worker_seconds,
            accounted_method_work_seconds=source_seconds + input_seconds + actual_worker_seconds,
            campaign_wall_seconds=manifest["campaign_wall_seconds"],
            scope="Source training and common preparation executed once; attributed arm totals must not be summed."),
        separate_validation=dict(audit_seconds=manifest["audit_seconds"], ground_seconds=audit["ground_seconds"],
            ground_counts=audit["ground_counts"],
            scope="Independent full-support execution and H1-encoder validation; excluded from method costs."),
        metric_scope="Metrics evaluate the selected root action and supplied H1 continuation. Canonical-reference "
            "failure/success deltas may differ between tied optimal policies and are not additional risk caps.",
        evidence_scope="Source-trained decisions on 48 unseen H2 boards and 14 fixed queries; no H3 claim is inherited.",
        elapsed_seconds=perf_counter() - started)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.directory)
    output = args.output or args.directory / "analysis.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(complete=result["complete"], integrity_valid=result["integrity_valid"],
        methods={name: dict(optimal=row["overall"]["root_optimal"], queries=row["overall"]["queries"],
            total_seconds=row["costs"]["total_seconds"], eligible=row["adoption"]["eligible"])
            for name, row in result["methods"].items()})))
