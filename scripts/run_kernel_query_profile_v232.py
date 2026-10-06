"""Zero-observation profile-likelihood qualification on fixed V231 snapshots."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import kernel_query_profile_v232 as core

INPUT = ROOT/'reports/oracle_gap_lifecycle_v231'
OUTPUT = ROOT/'reports/kernel_query_profile_v232'
PARTITIONS = 32
POLICIES = ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')
QUERIES = ('reward', 'goal', 'risk')


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


def phase(index):
    return 'late_B' if 42 <= index < 54 else ('A_RETURN' if 54 <= index < 78 else None)


def read_records():
    rows = []
    for path in sorted(INPUT.glob('records_life_*.jsonl.gz')):
        with gzip.open(path, 'rt') as handle:
            rows.extend(json.loads(line) for line in handle)
    return rows


def select(rows, failures):
    failed_keys = {(r['life'], r['index'], r['arm']) for r in failures}
    selected, controls = [], set()
    for row in sorted(rows, key=lambda r: (r['life'], r['index'], r['arm'])):
        key = row['life'], row['index'], row['arm']
        kind = 'failure' if key in failed_keys else None
        group = row['life'], row['arm'], phase(row['index'])
        if group[2] is not None and row['terminal_plan']['query_ready'] and group not in controls:
            controls.add(group)
            kind = 'positive'
        if kind:
            selected.append(dict(kind=kind, phase=phase(row['index']), **deepcopy(row)))
    return selected


def prefixes(row):
    constraints = row['terminal_plan']['joint_constraints']
    ops = tuple(constraints)
    threshold = 480 if row['case']['context'] == 'A' else 240
    current = lambda j: {op: deepcopy(constraints[op][j]['counts']) for op in ops}
    inherited = tuple(op for op in ops if len(constraints[op]) == 5)
    result = [dict(name='pool', threshold=threshold, operators=list(ops), counts=current(1))]
    if inherited:
        result.append(dict(name='inherited_pool', threshold=480, operators=list(inherited),
                           counts={op: deepcopy(constraints[op][4]['counts']) for op in inherited}))
    result.append(dict(name='source', threshold=threshold, operators=list(ops), counts=current(0)))
    if inherited:
        result.append(dict(name='inherited_source', threshold=480, operators=list(inherited),
                           counts={op: deepcopy(constraints[op][3]['counts']) for op in inherited}))
    result.append(dict(name='member', threshold=2880, operators=list(ops), counts=current(2)))
    return result


def cache_key(case, query, chosen, alternative, prefix):
    return (case['operating'], str(case['retry_cost']), query, chosen, alternative,
            prefix['threshold'], tuple((op, tuple(prefix['counts'][op].items()))
                                      for op in prefix['operators']), PARTITIONS)


def qualify(row, cache, work):
    started = perf_counter()
    plan, groups = row['terminal_plan'], prefixes(row)
    decisions = {}
    for query in QUERIES:
        chosen = plan['queries'][query]['policy']
        comparisons = []
        for other in POLICIES:
            if other == chosen:
                continue
            attempts, used = [], None
            for prefix in groups:
                key = cache_key(row['case'], query, chosen, other, prefix)
                if key not in cache:
                    cache[key] = core.certificate(row['case'], query, chosen, other,
                        prefix['counts'], prefix['operators'], prefix['threshold'],
                        regret_threshold=F(1, 20), partitions=PARTITIONS, work=work)
                    work['unique_profile_calls'] += 1
                else:
                    work['profile_cache_hits'] += 1
                proof = cache[key]
                attempts.append(dict(prefix=prefix['name'], certificate=proof))
                if proof['status'] == 'certified':
                    used = prefix['name']
                    break
            comparisons.append(dict(other=other, certified=used is not None,
                                    used_prefix=used, attempts=attempts))
        decisions[query] = dict(policy=chosen,
            certified=all(c['certified'] for c in comparisons), comparisons=comparisons)
    return dict(life=row['life'], index=row['index'], arm=row['arm'], kind=row['kind'],
        phase=row['phase'], case=row['case'], prefixes=groups,
        old_queries=plan['query_certificates'], old_query_ready=plan['query_ready'],
        queries=decisions, query_ready=all(q['certified'] for q in decisions.values()),
        model_seconds=perf_counter()-started, new_observations=0)


def capture():
    paths = {'scripts/run_kernel_query_profile_v232.py', 'specs/KERNEL_QUERY_PROFILE_V232.md',
             'tests/test_kernel_query_profile_v232.py',
             'tests/test_kernel_query_profile_runner_v232.py',
             'tests/test_kernel_query_profile_v232_audit.py'}
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path:
            try:
                relative = Path(path).resolve().relative_to(ROOT)
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
    started, cache, work = perf_counter(), {}, Counter()
    failures = json.loads((INPUT/'countermodel_summary.json').read_text())['cases']
    selected = select(read_records(), failures)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    protocol = dict(partitions=PARTITIONS, new_observations=0, new_paid_samples=0,
        qualification_only=True, scientific_gate_changed=False,
        selected=[{k: r[k] for k in ('life', 'index', 'arm', 'kind', 'phase')} for r in selected])
    save(OUTPUT/'run.json', dict(protocol, phases=['inputs_frozen'], complete=False))
    with gzip.open(OUTPUT/'inputs.jsonl.gz', 'wt') as handle:
        for row in selected:
            handle.write(json.dumps(exact(row), separators=(',', ':'))+'\n')
    capture()
    results = []
    with gzip.open(OUTPUT/'records.jsonl.gz', 'wt') as handle:
        for row in selected:
            result = qualify(row, cache, work)
            results.append(result)
            handle.write(json.dumps(exact(result), separators=(',', ':'))+'\n')
            handle.flush()
            print(f'profile {row["kind"]} life={row["life"]} index={row["index"]} '
                  f'arm={row["arm"]} old={result["old_query_ready"]} new={result["query_ready"]}', flush=True)
    save(OUTPUT/'run.json', dict(protocol, phases=['inputs_frozen', 'certificates_frozen'], complete=False))
    # Oracle data only enters this post-certificate diagnostic.
    from acfqp.science import scoped_route_task_v228 as task
    from acfqp.science import latent_mechanisms_v213 as mechanics
    weights = {'reward': (1, 0, 0), 'goal': (1, 0, 4), 'risk': (1, 4, 4)}
    worlds = {life: task.world(life)[1] for life in range(3)}
    scores = []
    for row in results:
        vectors = mechanics.vectors(row['case'], worlds[row['life']][row['index']])
        regrets = {}
        for query, decision in row['queries'].items():
            w = weights[query]
            utility = lambda policy: sum(F(a)*b for a, b in zip((w[0], -w[1], w[2]), vectors[policy]))
            regrets[query] = max(map(utility, POLICIES))-utility(decision['policy'])
        scores.append(dict(life=row['life'], index=row['index'], arm=row['arm'], kind=row['kind'],
                           regrets=regrets, false_certificates=sum(row['queries'][q]['certified']
                              and value > F(1, 20) for q, value in regrets.items())))
    save(OUTPUT/'scores.json', scores)
    aggregates = {}
    for kind in ('failure', 'positive'):
        rr = [row for row in results if row['kind'] == kind]
        aggregates[kind] = dict(targets=len(rr), old_query_ready=sum(r['old_query_ready'] for r in rr),
            query_ready=sum(r['query_ready'] for r in rr),
            queries={q: sum(r['queries'][q]['certified'] for r in rr) for q in QUERIES},
            arms={a: dict(targets=sum(r['arm'] == a for r in rr),
                         query_ready=sum(r['query_ready'] and r['arm'] == a for r in rr))
                  for a in ('ORACLE_BALANCED', 'ORACLE_GAP')})
    summary = dict(complete=True, records=len(results), groups=aggregates, work=dict(work),
        false_certificates=sum(r['false_certificates'] for r in scores), new_observations=0,
        new_paid_samples=0, qualification_only=True, scientific_gate_changed=False,
        model_seconds=sum(r['model_seconds'] for r in results), elapsed_seconds=perf_counter()-started)
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol, phases=['inputs_frozen', 'certificates_frozen', 'oracle_evaluated', 'complete'], complete=True))
    print(json.dumps(exact(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
