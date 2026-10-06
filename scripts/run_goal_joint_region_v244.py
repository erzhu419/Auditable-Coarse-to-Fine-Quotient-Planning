"""Diagnose the frozen V243 ONE_WAY return goal comparisons without sampling."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import goal_joint_region_v244 as core

BASELINE = ROOT/'reports/bidirectional_lifecycle_v243'
OUTPUT = ROOT/'reports/goal_joint_region_v244'
STATUSES = ('unknown', 'paid_constraints_reject_candidate', 'full_region_bad_witness')
COMPARISON = dict(query='goal', chosen='SHORT', other='DETOUR_RETRY')


def read(path):
    return json.loads(path.read_text())


def rows(path):
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            yield json.loads(line)


def save(path, value):
    path.write_text(json.dumps(value, default=str, indent=2)+'\n')


def endpoints():
    """Select all prior unknowns, before any candidate is constructed."""
    selected = []
    for life in range(3):
        for row in rows(BASELINE/f'records_life_{life:02d}.jsonl.gz'):
            if row['arm'] != 'ONE_WAY' or row['case']['stage'] != 'A_RETURN':
                continue
            goal = row['terminal_plan']['query_evidence']['queries']['goal']
            if goal['policy'] != 'SHORT':
                continue
            reference = next(x for x in goal['comparisons'] if x['other'] == 'DETOUR_RETRY')
            if not reference['certified']:
                selected.append((row, reference))
    if len(selected) != 24 or Counter(row['life'] for row, _ in selected) != {0: 8, 1: 8, 2: 8}:
        raise ValueError('the frozen 24-comparison roster is incomplete')
    return sorted(selected, key=lambda pair: (pair[0]['life'], pair[0]['index']))


def status_counts(records):
    counts = Counter(row['status'] for row in records)
    return {status: counts[status] for status in STATUSES}


def summarize(records):
    query_rejections, execution_rejections = Counter(), Counter()
    for row in records:
        query_rejections.update(family for family, member in row['query_regions'].items()
                                if not member['exact_inside'])
        execution_rejections.update(
            f'{("source", "pool", "member")[event["position"]]}:{event["operator"]}'
            for event in row['execution_regions'] if not event['membership']['exact_inside'])
    return dict(complete=True, records=len(records), arm='ONE_WAY', comparison=COMPARISON,
        status_counts=status_counts(records),
        life_summaries=[dict(life=life, records=sum(row['life'] == life for row in records),
            status_counts=status_counts([row for row in records if row['life'] == life])) for life in range(3)],
        canonical_admitted=sum(row['canonical_inside'] is True for row in records),
        all_query_admitted=sum(row['all_query_inside'] is True for row in records),
        all_execution_admitted=sum(row['all_execution_inside'] is True for row in records),
        query_rejection_counts=dict(sorted(query_rejections.items())),
        execution_rejection_counts=dict(sorted(execution_rejections.items())),
        new_observations=0, new_optimizer_calls=0, new_query_certificates=0,
        posthoc_scoring_calls=0, scientific_gate_changed=False, diagnostic_only=True)


def capture():
    files = {'scripts/run_goal_joint_region_v244.py', 'scripts/audit_goal_joint_region_v244.py',
        'src/acfqp/science/goal_joint_region_v244.py', 'tests/test_goal_joint_region_v244.py',
        'tests/test_goal_joint_region_v244_audit.py', 'tests/test_goal_joint_region_v244_runner.py',
        'specs/GOAL_JOINT_REGION_V244.md'}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT/'src'):
                files.add(path.relative_to(ROOT).as_posix())
    for relative in sorted(files):
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    save(OUTPUT/'source_manifest.json', sorted(files))


def run():
    begun = perf_counter()
    baseline_run, baseline_audit = read(BASELINE/'run.json'), read(BASELINE/'analysis.json')
    if not baseline_run['complete'] or not baseline_audit['valid']:
        raise ValueError('V243 must be complete and independently valid')
    selected = endpoints()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    capture()
    roster = [dict(life=row['life'], index=row['index'], profile_id=ref['profile_id'])
              for row, ref in selected]
    protocol = dict(baseline='reports/bidirectional_lifecycle_v243', arm='ONE_WAY',
        comparison=COMPARISON, roster=roster, query_threshold=960,
        execution_thresholds='retained_source720_pool720_member8640', strict_gap='50001/1000000',
        candidate_rule='maximum_finite_dual_leaf_first_tie_or_retained_bad_null_mle',
        repair='one_algebraic_SHORT_DELIVERY_update_without_clipping',
        data_access='retained_records_profiles_source_records_interfaces_only',
        new_observations=0, new_optimizer_calls=0, new_query_certificates=0,
        posthoc_scoring_calls=0, scientific_gate_changed=False, diagnostic_only=True)
    save(OUTPUT/'run.json', dict(protocol, complete=False, phases=['protocol_frozen']))
    records = []
    for life in range(3):
        needed = {ref['profile_id'] for row, ref in selected if row['life'] == life}
        profiles = {item['profile_id']: item for item in rows(BASELINE/f'profiles_life_{life:02d}.jsonl.gz')
                    if item['profile_id'] in needed}
        for row, ref in selected:
            if row['life'] != life:
                continue
            plan, certificate = row['terminal_plan'], profiles[ref['profile_id']]['certificate']
            result = core.classify(plan['evidence_counts'], plan['joint_constraints'], row['case'], certificate)
            record = dict(life=life, index=row['index'], case=row['case'], identity=row['identity'],
                profile_id=ref['profile_id'], evidence_counts=deepcopy(plan['evidence_counts']),
                joint_constraints=deepcopy(plan['joint_constraints']), **result)
            records.append(record)
            save(OUTPUT/'records.json', records)
            print(f'life={life} index={row["index"]} status={result["status"]}', flush=True)
    summary = dict(summarize(records), elapsed_seconds=perf_counter()-begun)
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol, complete=True,
        phases=['protocol_frozen', 'all_endpoints_diagnosed', 'complete']))
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    run()
