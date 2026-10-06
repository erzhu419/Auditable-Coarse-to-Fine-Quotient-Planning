"""Frozen 24-case qualification after the V235 witness prerequisite passes."""
from collections import Counter
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import joint_query_evidence_v235 as core

V232 = ROOT/'reports/kernel_query_profile_v232'
V233 = ROOT/'reports/paired_query_score_v233'
V234 = ROOT/'reports/shared_prefix_score_v234'
PREREQUISITE = ROOT/'reports/joint_query_evidence_v235'
OUTPUT = ROOT/'reports/joint_query_qualification_v235'


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
    path.write_text(json.dumps(exact(value), ensure_ascii=False, separators=(',', ':'))+'\n')


def rows(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def key(row):
    return row['life'], row['index'], row['arm']


def policies(queries):
    return {query: decision['policy'] for query, decision in queries.items()}


def qualify(tape, previous, old, cache):
    begun, before = perf_counter(), len(cache)
    plan = previous['terminal_plan']
    result = core.certificates(tape['operators'], tape['case'], plan['queries'], cache)
    if policies(result['queries']) != policies(plan['queries']):
        raise ValueError('V235 must retain the original selected policies')
    return dict(**{field: tape[field] for field in
        ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees')},
        queries=result['queries'], query_ready=result['all_ready'],
        old_query_ready=plan['query_ready'], v234_query_ready=old['query_ready'],
        row_lengths={op: len(values) for op, values in tape['operators'].items()},
        unique_profile_calls=len(cache)-before,
        profile_cache_hits=len(result['comparison_records'])-(len(cache)-before),
        model_seconds=perf_counter()-begun, new_observations=0, new_paid_samples=0)


def capture():
    paths = set(json.loads((V232/'source_manifest.json').read_text()))
    paths.update(('scripts/run_joint_query_qualification_v235.py',
        'scripts/audit_joint_query_qualification_v235.py',
        'src/acfqp/science/joint_query_evidence_v235.py',
        'src/acfqp/science/kernel_query_profile_v232.py',
        'src/acfqp/science/joint_gap_v230.py',
        'src/acfqp/science/latent_mechanisms_v213.py',
        'src/acfqp/science/continual_route_kernels_v202.py',
        'specs/JOINT_QUERY_EVIDENCE_V235.md',
        'reports/v235_runtime_tmp/projected_mixture_proof.md',
        'tests/test_joint_query_qualification_v235.py',
        'tests/test_joint_query_qualification_runner_v235.py',
        'tests/test_joint_query_qualification_v235_audit.py'))
    for relative in sorted(paths):
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    save(OUTPUT/'source_manifest.json', sorted(paths))


def score_frozen(results, previous):
    truth = {key(row): row for row in json.loads((V233/'scores.json').read_text())}
    if set(truth) != {key(row) for row in results}:
        raise ValueError('saved true-regret roster must match the frozen qualification')
    scored = []
    for row in results:
        if policies(row['queries']) != policies(previous[key(row)]['queries']):
            raise ValueError('saved truth requires unchanged policies')
        original = truth[key(row)]
        scored.append(dict(life=row['life'], index=row['index'], arm=row['arm'],
            kind=row['kind'], regrets=original['regrets'],
            false_certificates=sum(row['queries'][query]['certified'] and F(value)>F(1, 20)
                for query, value in original['regrets'].items())))
    save(OUTPUT/'scores.json', scored)
    return scored


def run():
    begun, cache = perf_counter(), {}
    prerequisite = json.loads((PREREQUISITE/'summary.json').read_text())
    audit = json.loads((PREREQUISITE/'analysis.json').read_text())
    if not prerequisite['full_qualification_eligible'] or not audit['valid']:
        raise ValueError('the frozen, independently audited witness prerequisite must pass')
    previous = {key(row): row for row in rows(V232/'inputs.jsonl.gz')}
    old = {key(row): row for row in rows(V234/'records.jsonl.gz')}
    tapes = rows(V234/'tapes.jsonl.gz')
    if len(previous)!=24 or [key(row) for row in tapes]!=list(previous) or set(old)!=set(previous):
        raise ValueError('the original 24-case roster is fixed')
    protocol = dict(stream_count=48, threshold=960, partitions=32, delta_per_life_arm='1/20',
        qualification_only=True, scientific_gate_changed=False, new_observations=0,
        new_paid_samples=0, selected=[{field: row[field] for field in
            ('life', 'index', 'arm', 'kind', 'phase')} for row in tapes])
    phases = ['prerequisite_passed', 'protocol_frozen']
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    shutil.copyfile(V234/'tapes.jsonl.gz', OUTPUT/'tapes.jsonl.gz')
    save(OUTPUT/'input_references.json', dict(paid_tapes=str(V234/'tapes.jsonl.gz'),
        prior_tape_audit=str(V234/'analysis.json'), prerequisite=str(PREREQUISITE/'analysis.json'),
        original_queries=str(V232/'inputs.jsonl.gz'), saved_truth=str(V233/'scores.json')))
    phases.append('tapes_frozen')
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    capture()
    results = []
    with gzip.open(OUTPUT/'records.jsonl.gz', 'wt') as stream:
        for tape in tapes:
            result = qualify(tape, previous[key(tape)], old[key(tape)], cache)
            results.append(result)
            stream.write(json.dumps(exact(result), separators=(',', ':'))+'\n')
            stream.flush()
            print(f'joint life={tape["life"]} index={tape["index"]} arm={tape["arm"]} '
                  f'old={result["v234_query_ready"]} new={result["query_ready"]}', flush=True)
    phases.append('certificates_frozen')
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    scored = score_frozen(results, old)
    groups = {}
    for kind in ('failure', 'positive'):
        selected = [row for row in results if row['kind']==kind]
        blockers = Counter(comparison['family'] for row in selected for query in ('goal', 'risk')
            for comparison in row['queries'][query]['comparisons'] if not comparison['certified'])
        groups[kind] = dict(targets=len(selected),
            old_query_ready=sum(row['old_query_ready'] for row in selected),
            v234_query_ready=sum(row['v234_query_ready'] for row in selected),
            query_ready=sum(row['query_ready'] for row in selected),
            queries={query: sum(row['queries'][query]['certified'] for row in selected)
                for query in ('reward', 'goal', 'risk')}, blockers_by_family=dict(blockers))
    summary = dict(complete=True, records=len(results), groups=groups,
        unique_profile_calls=len(cache), profile_cache_hits=sum(row['profile_cache_hits'] for row in results),
        model_seconds=sum(row['model_seconds'] for row in results),
        false_certificates=sum(row['false_certificates'] for row in scored),
        new_observations=0, new_paid_samples=0, qualification_only=True,
        scientific_gate_changed=False, elapsed_seconds=perf_counter()-begun)
    save(OUTPUT/'summary.json', summary)
    phases.extend(['saved_truth_evaluated', 'complete'])
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=True))
    print(json.dumps(exact(summary)), flush=True)
    return summary


if __name__=='__main__':
    run()
