"""Fixed V232 qualification with shared-prefix certificates and saved paid tapes."""
from collections import Counter
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from acfqp.science import shared_prefix_score_v234 as core

INPUT = ROOT / 'reports/kernel_query_profile_v232'
PAID = ROOT / 'reports/paired_query_score_v233'
OUTPUT = ROOT / 'reports/shared_prefix_score_v234'


def exact(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {key: exact(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact(item) for item in value]
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(exact(value), ensure_ascii=False, separators=(',', ':')) + '\n')


def read_rows(path):
    with gzip.open(path, 'rt') as handle:
        return [json.loads(line) for line in handle]


def key(row):
    return row['life'], row['index'], row['arm']


def policies(queries):
    return {query: row['policy'] for query, row in queries.items()}


def cache_counts(cache):
    rows = sum(item[0] == 'bernoulli' for item in cache)
    return dict(row_intervals=rows, direct_score_streams=len(cache) - rows)


def qualify(snapshot, previous, cache):
    begun, before = perf_counter(), cache_counts(cache)
    plan = previous['terminal_plan']
    certificate = core.certificates(snapshot['operators'], snapshot['case'], plan['queries'], cache)
    if policies(certificate['queries']) != policies(plan['queries']):
        raise ValueError('V234 qualification must preserve the frozen selected policies')
    after = cache_counts(cache)
    direct_calls = sum(row['method'] == 'paired_direct' for row in certificate['comparison_records'])
    row_calls = len(certificate['evidence_records'])
    new_direct = after['direct_score_streams'] - before['direct_score_streams']
    new_rows = after['row_intervals'] - before['row_intervals']
    return dict(**{field: snapshot[field] for field in
        ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees')},
        old_query_ready=plan['query_ready'], queries=certificate['queries'],
        query_ready=certificate['all_ready'], threshold=certificate['threshold'],
        evidence_records=certificate['evidence_records'],
        row_lengths={op: len(seq) for op, seq in snapshot['operators'].items()},
        model_seconds=perf_counter() - begun,
        direct_score_calls=direct_calls, unique_direct_score_streams=new_direct,
        direct_score_cache_hits=direct_calls - new_direct,
        row_interval_calls=row_calls, unique_row_intervals=new_rows,
        row_interval_cache_hits=row_calls - new_rows,
        new_observations=0, new_paid_samples=0)


def capture():
    paths = (
        'scripts/run_shared_prefix_score_v234.py',
        'scripts/audit_shared_prefix_score_v234.py',
        'scripts/audit_paired_query_score_v233.py',
        'scripts/audit_joint_gap_v230.py',
        'scripts/analyze_scoped_lifecycle_v229.py',
        'scripts/scoped_repair_v229_math.py',
        'scripts/analyze_mixture_confidence_v225.py',
        'scripts/analyze_assignment_union_v222.py',
        'scripts/analyze_fixed_source_acquisition_v219.py',
        'scripts/analyze_joint_acquisition_v218.py',
        'scripts/analyze_latent_mechanisms_v213.py',
        'scripts/analyze_conditioned_mechanisms_v205.py',
        'src/acfqp/science/structured_route_task_v201.py',
        'src/acfqp/science/shared_prefix_score_v234.py',
        'src/acfqp/science/paired_query_score_v233.py',
        'src/acfqp/science/continual_route_kernels_v202.py',
        'specs/SHARED_PREFIX_SCORE_V234.md',
        'tests/test_shared_prefix_score_v234.py',
        'tests/test_shared_prefix_score_runner_v234.py',
        'tests/test_shared_prefix_score_v234_audit.py',
    )
    for relative in paths:
        destination = OUTPUT / 'source_code' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    save(OUTPUT / 'source_manifest.json', list(paths))


def score_frozen(results, v233):
    """Reuse unchanged-policy true regrets only after all certificates are saved."""
    saved = {key(row): row for row in json.loads((PAID / 'scores.json').read_text())}
    if set(saved) != {key(row) for row in results}:
        raise ValueError('saved V233 score roster differs from the frozen V234 roster')
    scores = []
    for row in results:
        old = v233[key(row)]
        if policies(row['queries']) != policies(old['queries']):
            raise ValueError('reusing V233 truth requires unchanged query policies')
        score = saved[key(row)]
        if score['kind'] != row['kind']:
            raise ValueError('saved V233 score kind differs from the fixed selection')
        regrets = score['regrets']
        scores.append(dict(life=row['life'], index=row['index'], arm=row['arm'], kind=row['kind'],
            regrets=regrets, false_certificates=sum(row['queries'][query]['certified']
                and F(value) > F(1, 20) for query, value in regrets.items())))
    save(OUTPUT / 'scores.json', scores)
    return scores


def summarize(results, scores, cache, begun):
    groups = {}
    for kind in ('failure', 'positive'):
        rr = [row for row in results if row['kind'] == kind]
        methods, blockers = Counter(), Counter()
        for row in rr:
            for decision in row['queries'].values():
                for comparison in decision.get('comparisons', ()):
                    method = comparison['method']
                    methods[(method, 'certified' if comparison['certified'] else 'unknown')] += 1
                    if not comparison['certified']:
                        blockers[method] += 1
        groups[kind] = dict(targets=len(rr),
            old_query_ready=sum(r['old_query_ready'] for r in rr),
            v232_query_ready=sum(r['v232_query_ready'] for r in rr),
            v233_query_ready=sum(r['v233_query_ready'] for r in rr),
            query_ready=sum(r['query_ready'] for r in rr),
            queries={q: sum(r['queries'][q]['certified'] for r in rr)
                     for q in ('reward', 'goal', 'risk')},
            arms={arm: dict(targets=sum(r['arm'] == arm for r in rr),
                query_ready=sum(r['query_ready'] and r['arm'] == arm for r in rr))
                for arm in ('ORACLE_BALANCED', 'ORACLE_GAP')},
            methods={method: {status: methods[(method, status)]
                     for status in ('certified', 'unknown')}
                     for method in ('paired_direct', 'shared_prefix_rectangle')},
            blockers_by_method=dict(blockers))
    counts = cache_counts(cache)
    return dict(complete=True, records=len(results), groups=groups,
        unique_direct_score_streams=counts['direct_score_streams'],
        direct_score_calls=sum(r['direct_score_calls'] for r in results),
        direct_score_cache_hits=sum(r['direct_score_cache_hits'] for r in results),
        unique_row_intervals=counts['row_intervals'],
        row_interval_calls=sum(r['row_interval_calls'] for r in results),
        row_interval_cache_hits=sum(r['row_interval_cache_hits'] for r in results),
        model_seconds=sum(r['model_seconds'] for r in results),
        false_certificates=sum(r['false_certificates'] for r in scores),
        new_observations=0, new_paid_samples=0, qualification_only=True,
        scientific_gate_changed=False, elapsed_seconds=perf_counter() - begun)


def run():
    begun, cache = perf_counter(), {}
    previous_rows = read_rows(INPUT / 'inputs.jsonl.gz')
    previous = {key(row): row for row in previous_rows}
    v232 = {key(row): row for row in read_rows(INPUT / 'records.jsonl.gz')}
    v233 = {key(row): row for row in read_rows(PAID / 'records.jsonl.gz')}
    snapshots = read_rows(PAID / 'tapes.jsonl.gz')
    if len(previous) != 24 or [key(row) for row in snapshots] != [key(row) for row in previous_rows]:
        raise ValueError('V234 uses exactly the fixed 24 V232/V233 snapshots in original order')
    if set(previous) != set(v232) or set(previous) != set(v233):
        raise ValueError('prior certificate records differ from the fixed 24-case roster')
    protocol = dict(qualification_only=True, stream_count=180, direct_stream_count=168,
        bernoulli_stream_count=12, threshold=3600, delta_per_life_arm='1/20',
        new_observations=0, new_paid_samples=0, scientific_gate_changed=False,
        selected=[{field: row[field] for field in ('life', 'index', 'arm', 'kind', 'phase')}
                  for row in previous_rows])
    phases = ['protocol_frozen']
    save(OUTPUT / 'run.json', dict(protocol, phases=phases, complete=False))
    shutil.copyfile(PAID / 'tapes.jsonl.gz', OUTPUT / 'tapes.jsonl.gz')
    save(OUTPUT / 'input_references.json', dict(
        paid_tapes=str(PAID / 'tapes.jsonl.gz'),
        prior_paid_tape_audit=str(PAID / 'analysis.json'),
        prior_source_manifest=str(PAID / 'source_manifest.json'),
        selection=str(INPUT / 'inputs.jsonl.gz'),
        v232_certificates=str(INPUT / 'records.jsonl.gz'),
        v233_certificates=str(PAID / 'records.jsonl.gz'),
        unchanged_policy_truth=str(PAID / 'scores.json'),
        acquisition='reuse_saved_paid_tapes', new_observations=0, new_paid_samples=0))
    phases.append('tapes_frozen')
    save(OUTPUT / 'run.json', dict(protocol, phases=phases, complete=False))
    capture()
    results = []
    with gzip.open(OUTPUT / 'records.jsonl.gz', 'wt') as handle:
        for snapshot in snapshots:
            row = qualify(snapshot, previous[key(snapshot)], cache)
            if policies(row['queries']) != policies(v233[key(row)]['queries']):
                raise ValueError('V234 must retain all V233 selected query policies')
            row['v232_query_ready'] = v232[key(row)]['query_ready']
            row['v233_query_ready'] = v233[key(row)]['query_ready']
            results.append(row)
            handle.write(json.dumps(exact(row), separators=(',', ':')) + '\n')
            handle.flush()
            print(f'shared {row["kind"]} life={row["life"]} index={row["index"]} '
                  f'arm={row["arm"]} v233={row["v233_query_ready"]} new={row["query_ready"]}', flush=True)
    phases.append('certificates_frozen')
    save(OUTPUT / 'run.json', dict(protocol, phases=phases, complete=False))
    scores = score_frozen(results, v233)
    phases.append('saved_truth_evaluated')
    summary = summarize(results, scores, cache, begun)
    save(OUTPUT / 'summary.json', summary)
    phases.append('complete')
    save(OUTPUT / 'run.json', dict(protocol, phases=phases, complete=True))
    print(json.dumps(exact(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
