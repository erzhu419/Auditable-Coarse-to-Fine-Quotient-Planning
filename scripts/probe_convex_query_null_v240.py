"""One fixed comparison per unresolved V239 endpoint; no new observations."""
from collections import Counter
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import convex_query_null_v240 as core
from scripts import convex_null_selection_v240 as selection
from scripts.run_life_end_query_evidence_v238 import exact, save, rows

V239 = ROOT/'reports/life_end_joint_evidence_v239'
OUTPUT = ROOT/'reports/convex_query_null_v240'
STATUSES = ('admitted_bad_kernel', 'global_bad_null_excluded', 'unknown')


def classify(descriptor):
    begun = perf_counter()
    result = core.classify(descriptor['projected_counts'], descriptor['case'], descriptor['family'])
    return dict(**{field: value for field, value in descriptor.items() if field != 'old_comparison'},
        result=result, model_seconds=perf_counter()-begun, new_observations=0, new_paid_samples=0)


def status_counts(records):
    counts = Counter(row['result']['status'] for row in records)
    return {status: counts[status] for status in STATUSES}


def capture():
    from scripts import audit_convex_query_null_v240

    paths = {'scripts/probe_convex_query_null_v240.py', 'scripts/convex_null_selection_v240.py',
        'scripts/audit_convex_query_null_v240.py', 'specs/CONVEX_QUERY_NULL_V240.md',
        'reports/v240_runtime_tmp/convex_null_note.md', 'tests/test_convex_query_null_v240.py',
        'tests/test_convex_null_selection_v240.py', 'tests/test_convex_query_null_v240_runner.py',
        'tests/test_convex_query_null_v240_audit.py'}
    for module in tuple(sys.modules.values()):
        source = getattr(module, '__file__', None)
        if source:
            try:
                relative = Path(source).resolve().relative_to(ROOT)
            except ValueError:
                continue
            if relative.suffix == '.py':
                paths.add(str(relative))
    for relative in sorted(paths):
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    save(OUTPUT/'source_manifest.json', sorted(paths))


def run():
    begun = perf_counter()
    prior_audit = json.loads((V239/'analysis.json').read_text())
    if not prior_audit['valid']:
        raise ValueError('V239 paid counts and comparisons must have a valid independent audit')
    descriptors = selection.select(rows(V239/'records.jsonl.gz'))
    protocol = dict(records=9, families={'S_D_FULL': 6, 'D_REC_R': 3}, threshold=960,
        regret_threshold='1/20', stream_count=48, delta_per_life_arm='1/20', certificate_index=77,
        classification_only=True, qualification_changed=False, scientific_gate_changed=False,
        new_observations=0, new_paid_samples=0, selected=[{field: row[field] for field in
            ('life', 'index', 'arm', 'query', 'chosen', 'other', 'family')} for row in descriptors])
    phases = ['protocol_frozen']
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    save(OUTPUT/'input_records.json', descriptors)
    save(OUTPUT/'input_references.json', dict(prior_records=str(V239/'records.jsonl.gz'),
        prior_audit=str(V239/'analysis.json'), prior_summary=str(V239/'summary.json'),
        spec=str(ROOT/'specs/CONVEX_QUERY_NULL_V240.md')))
    phases.append('inputs_frozen')
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    capture()
    results = []
    for descriptor in descriptors:
        row = classify(descriptor)
        results.append(row)
        # Retain each completed result even if a later numerical proposal fails.
        save(OUTPUT/'records.json', results)
        print(f'convex-null life={row["life"]} index={row["index"]} arm={row["arm"]} '
            f'family={row["family"]} status={row["result"]["status"]}', flush=True)
    phases.append('classifications_frozen')
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    counts = status_counts(results)
    prior_summary = json.loads((V239/'summary.json').read_text())
    summary = dict(complete=True, records=9, statuses=counts,
        groups={kind: dict(records=sum(row['kind'] == kind for row in results),
            statuses=status_counts([row for row in results if row['kind'] == kind]))
            for kind in ('failure', 'positive')},
        families={family: dict(records=sum(row['family'] == family for row in results),
            statuses=status_counts([row for row in results if row['family'] == family]))
            for family in ('S_D_FULL', 'D_REC_R')},
        fixed_evidence_numerical_repair_ruled_out_cases=counts['admitted_bad_kernel'],
        global_bound_repair_cases=counts['global_bad_null_excluded'], unknown_cases=counts['unknown'],
        model_seconds=sum(row['model_seconds'] for row in results), optimizer_calls=9,
        life_costs=prior_summary['life_costs'], classification_only=True, qualification_changed=False,
        scientific_gate_changed=False, new_observations=0, new_paid_samples=0,
        elapsed_seconds=perf_counter()-begun)
    save(OUTPUT/'summary.json', summary)
    phases.append('complete')
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=True))
    print(json.dumps(exact(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
