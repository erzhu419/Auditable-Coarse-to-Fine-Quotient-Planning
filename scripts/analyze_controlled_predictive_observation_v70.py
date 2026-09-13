"""Summarize frozen-rule construction and cold-start finite observation routing."""
from collections import Counter
import argparse
import json
from pathlib import Path
from time import perf_counter


METHODS = ('FULL_MAP', 'COMPOSED_MAP', 'COMPOSED_DAG')
UPSTREAM = {'FULL_MAP': 'FULL', 'COMPOSED_MAP': 'COMPOSED', 'COMPOSED_DAG': 'COMPOSED'}


def summed(rows):
    result = Counter()
    for row in rows:
        result.update({key: value for key, value in row.items() if type(value) in (int, float)})
    return dict(result)


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def analyze(directory):
    """Read retained results only; this function does not write or run any model."""
    started = perf_counter()
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text())
    records = [json.loads(line) for line in (directory/'targets.jsonl').read_text().splitlines()]
    completed = [row for row in records if row['status'] == 'complete']
    old_path = directory.parent/'controlled_predictive_composition_v69'/'analysis.json'
    old = json.loads(old_path.read_text())
    expected_active = old['arms']['FULL']['construction']['concrete_active_states']
    expected_observations = 60
    names = [row['case']['name'] if isinstance(row['case'], dict) else row['case'] for row in completed]
    complete = (manifest['status'] == 'complete' and manifest['target_roots'] == 32 and
                manifest['completed_targets'] == 32 and len(completed) == len(records) == 32 and
                len(set(names)) == 32)
    covered = sum(row['audit']['active_observations'] for row in completed)
    matched = sum(row['audit']['portable_observations'] for row in completed)
    support_preserved = (complete and covered == expected_active and matched == expected_observations and
                         all(row['audit']['routing_correct'] for row in completed))
    methods = {}
    for method in METHODS:
        arms = [row['arms'][method] for row in completed]
        bases = [row['upstream'][UPSTREAM[method]] for row in completed]
        router_audits = [row['audit']['routers'][method] for row in completed]
        workers = [row['portable'][method] for row in completed]
        upstream_seconds = sum(row['times']['total'] for row in bases)
        downstream_seconds = sum(row['times']['total'] for row in arms)
        checked_active = sum(row['covered_observations'] for row in router_audits)
        checked_existing = sum(row['portable_observations'] for row in router_audits)
        artifact_passed = all(row['kernel_equal'] and row['plans_equal'] and row['routes_equal'] for row in arms)
        worker_passed = all(row['passed'] and row['exit_code'] == 0 and row['stderr_bytes'] == 0 for row in workers)
        methods[method] = dict(
            complete_targets=len(arms), upstream_variant=UPSTREAM[method],
            artifacts_preserved=complete and artifact_passed,
            portable_passed=complete and worker_passed,
            full_active_routing_preserved=(support_preserved and checked_active == expected_active and
                checked_existing == expected_observations and all(row['valid'] for row in router_audits)),
            active_observations_checked=checked_active, matched_observations=checked_existing,
            unsupported_observations_checked=sum(row['unsupported_observations'] for row in router_audits),
            package_bytes=sum(row['package_bytes'] for row in arms),
            router_bytes=sum(row['router_bytes'] for row in arms),
            construction_counts=summed(row['counts'] for row in bases),
            compile_counts=summed(row['compile_counts'] for row in arms),
            routing_counts=summed(row['routing_counts'] for row in arms),
            planning_counts=summed(row['planning_counts'] for row in arms),
            times=dict(upstream_seconds=upstream_seconds, downstream_seconds=downstream_seconds,
                cold_method_total_seconds=upstream_seconds + downstream_seconds,
                upstream_stages=summed(row['times'] for row in bases),
                downstream_stages=summed(row['times'] for row in arms),
                worker_command_seconds_included_in_downstream=sum(row['command_seconds'] for row in workers)))
    preserved = support_preserved and all(row['artifacts_preserved'] and row['portable_passed'] and
        row['full_active_routing_preserved'] for row in methods.values())
    old_valid = (old['complete'] and old['policy_and_dynamics_preserved'] and old['portable_passed'])
    inherited = preserved and old_valid
    ratios = {}
    for left, right in (('COMPOSED_MAP', 'FULL_MAP'), ('COMPOSED_DAG', 'FULL_MAP'),
                        ('COMPOSED_DAG', 'COMPOSED_MAP')):
        a, b = methods[left], methods[right]
        ratios[left + '_vs_' + right] = dict(
            cold_method_total_seconds=ratio(a['times']['cold_method_total_seconds'], b['times']['cold_method_total_seconds']),
            package_bytes=ratio(a['package_bytes'], b['package_bytes']),
            router_bytes=ratio(a['router_bytes'], b['router_bytes']),
            planning_action_rows=ratio(a['planning_counts'].get('state_action_rows', 0),
                                       b['planning_counts'].get('state_action_rows', 0)))
    inherited_metrics = None
    if inherited:
        inherited_metrics = {variant: dict(
            root_queries=old['arms'][variant]['root_queries'],
            optimal_executable_root_queries=old['arms'][variant]['optimal_executable_root_queries'],
            strict_query_switches=old['arms'][variant]['strict_query_switches'])
            for variant in ('FULL', 'COMPOSED')}
    actual_upstream = {variant: sum(row['upstream'][variant]['times']['total'] for row in completed)
                       for variant in ('FULL', 'COMPOSED')}
    result = dict(complete=complete, declared_targets=manifest['target_roots'],
        completed_targets=len(completed), incomplete_targets=[row['case'] for row in records if row['status'] != 'complete'],
        source_learning_reused=manifest.get('source_learning_reused') is True,
        all_artifacts_routing_and_portable_preserved=preserved,
        inherited_v69_policy_evidence_valid=inherited,
        inherited_v69_policy_metrics=inherited_metrics,
        inheritance_source=str(old_path), active_observations=covered, matched_observations=matched,
        methods=methods, ratios=ratios,
        finite_direct_routing_established=preserved,
        finite_dag_cold_cost_benefit_vs_full=(preserved and
            methods['COMPOSED_DAG']['times']['cold_method_total_seconds'] < methods['FULL_MAP']['times']['cold_method_total_seconds']),
        finite_dag_cold_cost_benefit_vs_composed_map=(preserved and
            methods['COMPOSED_DAG']['times']['cold_method_total_seconds'] < methods['COMPOSED_MAP']['times']['cold_method_total_seconds']),
        general_semantic_encoder_established=False, general_strategic_learning_solved=False,
        actual_execution=dict(upstream_seconds_by_variant=actual_upstream,
            upstream_seconds=sum(actual_upstream.values()),
            downstream_seconds=sum(row['times']['downstream_seconds'] for row in methods.values()),
            shared_composed_upstream_executions_per_target=1,
            audit_seconds=sum(row['audit']['elapsed_seconds'] for row in completed),
            audit_counts=summed(row['audit']['counts'] for row in completed),
            worker_command_seconds_included_in_downstream=sum(
                row['times']['worker_command_seconds_included_in_downstream'] for row in methods.values()),
            case_cleanup_seconds=sum(row['case_cleanup_seconds'] for row in completed),
            runner_wall_seconds=manifest['wall_seconds'], peak_rss_bytes=manifest['peak_rss_bytes']),
        timing_scope='Each method pays its upstream construction once plus downstream times.total. The two composed deployments each attribute the same shared construction, which actually executes once per target. Worker startup, loading, indexing, planning, routing, and result serialization are included in downstream total; their displayed substage times and portable command time must not be added again. Frozen source learning and independent audit costs are outside method cost.',
        evidence_scope='Same 32 V69 supports and frozen relational rule. Kernels, 14 query policies, all retained active routes, and the same 60 observations are compared. V69 policy evidence is inherited only after complete preservation; no new ground validation or strategic generalization result is claimed. Timing is one descriptive cold-start comparison.',
        analysis_seconds_before_write=perf_counter() - started)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.input)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: result[key] for key in ('complete',
        'all_artifacts_routing_and_portable_preserved', 'inherited_v69_policy_evidence_valid',
        'active_observations', 'matched_observations', 'ratios')}, indent=2))
