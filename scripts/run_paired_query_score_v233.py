"""Fixed V232 terminal qualification using only V231's recovered paid tapes."""
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
from acfqp.science import paired_query_score_v233 as core
from scripts import retained_query_tapes_v233 as replay

INPUT = ROOT/'reports/kernel_query_profile_v232'
OUTPUT = ROOT/'reports/paired_query_score_v233'


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


def read_rows(path):
    with gzip.open(path, 'rt') as handle:
        return [json.loads(line) for line in handle]


def key(row):
    return row['life'], row['index'], row['arm']


def qualify(snapshot, previous, cache):
    begun, before = perf_counter(), len(cache)
    plan = previous['terminal_plan']
    certificate = core.certificates(snapshot['operators'], snapshot['case'], plan['queries'], cache)
    unique = len(cache)-before
    return dict(**{field: snapshot[field] for field in
        ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees')},
        old_query_ready=plan['query_ready'], queries=certificate['queries'],
        query_ready=certificate['all_ready'], threshold=certificate['threshold'],
        row_lengths={op: len(seq) for op, seq in snapshot['operators'].items()},
        model_seconds=perf_counter()-begun, unique_score_streams=unique,
        score_cache_hits=len(certificate['comparison_records'])-unique,
        new_observations=0, new_paid_samples=0)


def capture():
    paths = {'scripts/run_paired_query_score_v233.py', 'specs/PAIRED_QUERY_SCORE_V233.md',
             'tests/test_paired_query_score_v233.py', 'tests/test_retained_query_tapes_v233.py',
             'tests/test_paired_query_score_runner_v233.py',
             'tests/test_paired_query_score_v233_audit.py'}
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
    begun, cache = perf_counter(), {}
    previous = {key(row): row for row in read_rows(INPUT/'inputs.jsonl.gz')}
    v232 = {key(row): row for row in read_rows(INPUT/'records.jsonl.gz')}
    protocol = dict(qualification_only=True, stream_count=216, threshold=4320,
        delta_per_life_arm='1/20', bet_anchor='1/20', new_observations=0, new_paid_samples=0,
        scientific_gate_changed=False,
        selected=[{field: row[field] for field in ('life', 'index', 'arm', 'kind', 'phase')}
                  for row in previous.values()])
    save(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen'], complete=False))
    start = perf_counter()
    recovered = replay.reconstruct()
    replay_seconds = perf_counter()-start
    with gzip.open(OUTPUT/'tapes.jsonl.gz', 'wt') as handle:
        for row in recovered['snapshots']:
            handle.write(json.dumps(exact(row), separators=(',', ':'))+'\n')
    save(OUTPUT/'replay_summary.json', dict(recovered['summary'], replay_seconds=replay_seconds,
         source_code_paths=recovered['source_code_paths'], input_paths=recovered['input_paths']))
    save(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen', 'tapes_frozen'], complete=False))
    capture()
    results = []
    with gzip.open(OUTPUT/'records.jsonl.gz', 'wt') as handle:
        for snapshot in recovered['snapshots']:
            row = qualify(snapshot, previous[key(snapshot)], cache)
            row['v232_query_ready'] = v232[key(row)]['query_ready']
            results.append(row)
            handle.write(json.dumps(exact(row), separators=(',', ':'))+'\n')
            handle.flush()
            print(f'paired {row["kind"]} life={row["life"]} index={row["index"]} '
                  f'arm={row["arm"]} old={row["old_query_ready"]} new={row["query_ready"]}', flush=True)
    save(OUTPUT/'run.json', dict(protocol,
        phases=['protocol_frozen', 'tapes_frozen', 'certificates_frozen'], complete=False))
    # Truth is used here only for post-certificate regret diagnostics.
    from acfqp.science import latent_mechanisms_v213 as mechanics
    worlds, _ = replay.frozen_worlds(replay.INPUT)
    weights = {'reward': (1, 0, 0), 'goal': (1, 0, 4), 'risk': (1, 4, 4)}
    scores = []
    for row in results:
        vectors = mechanics.vectors(row['case'], worlds[row['life']][1][row['index']])
        regrets = {}
        for query, decision in row['queries'].items():
            reward, risk, goal = weights[query]
            utility = lambda p: reward*vectors[p][0]-risk*vectors[p][1]+goal*vectors[p][2]
            regrets[query] = max(map(utility, core.POLICIES))-utility(decision['policy'])
        scores.append(dict(life=row['life'], index=row['index'], arm=row['arm'], kind=row['kind'],
            regrets=regrets, false_certificates=sum(row['queries'][q]['certified'] and value > F(1, 20)
                                                   for q, value in regrets.items())))
    save(OUTPUT/'scores.json', scores)
    groups = {}
    for kind in ('failure', 'positive'):
        rr = [row for row in results if row['kind'] == kind]
        groups[kind] = dict(targets=len(rr), old_query_ready=sum(r['old_query_ready'] for r in rr),
            v232_query_ready=sum(r['v232_query_ready'] for r in rr),
            query_ready=sum(r['query_ready'] for r in rr),
            queries={q: sum(r['queries'][q]['certified'] for r in rr) for q in weights},
            arms={arm: dict(targets=sum(r['arm'] == arm for r in rr),
                 query_ready=sum(r['query_ready'] and r['arm'] == arm for r in rr))
                 for arm in ('ORACLE_BALANCED', 'ORACLE_GAP')})
    summary = dict(complete=True, records=len(results), groups=groups,
        unique_score_streams=len(cache), score_cache_hits=sum(r['score_cache_hits'] for r in results),
        model_seconds=sum(r['model_seconds'] for r in results), replay_seconds=replay_seconds,
        false_certificates=sum(r['false_certificates'] for r in scores),
        new_observations=0, new_paid_samples=0, qualification_only=True, scientific_gate_changed=False,
        elapsed_seconds=perf_counter()-begun)
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol,
        phases=['protocol_frozen', 'tapes_frozen', 'certificates_frozen', 'oracle_evaluated', 'complete'], complete=True))
    print(json.dumps(exact(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
