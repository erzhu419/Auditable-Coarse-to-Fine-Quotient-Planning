"""Qualify the original 24 policies at a fixed, later paid-life endpoint."""
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
from acfqp.science import life_end_query_evidence_v238 as core
from acfqp.science import source_predictive_evidence_v236 as split
from scripts import retained_life_end_tapes_v238 as replay

V231 = ROOT/'reports/oracle_gap_lifecycle_v231'
V232 = ROOT/'reports/kernel_query_profile_v232'
V233 = ROOT/'reports/paired_query_score_v233'
V235 = ROOT/'reports/joint_query_qualification_v235'
OUTPUT = ROOT/'reports/life_end_query_evidence_v238'


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


def qualify(tape, previous, old, cache, work):
    begun, before = perf_counter(), len(cache)
    plan = previous['terminal_plan']
    separated = split.split_tape(tape)
    result = core.certificates(separated['training'], separated['validation'],
        tape['case'], plan['queries'], cache, work)
    if policies(result['queries']) != policies(plan['queries']):
        raise ValueError('later qualification must retain the original selected policies')
    return dict(**{field: tape[field] for field in
        ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees',
         'early_fees', 'endpoint_index', 'certificate_index', 'evidence_end_index')},
        queries=result['queries'], query_ready=result['all_ready'],
        old_query_ready=plan['query_ready'], v235_query_ready=old['query_ready'],
        row_lengths={op: len(values) for op, values in tape['operators'].items()},
        training_row_lengths={op: len(values) for op, values in separated['training'].items()},
        validation_row_lengths={op: len(values) for op, values in separated['validation'].items()},
        unique_profile_calls=len(cache)-before,
        profile_cache_hits=len(result['comparison_records'])-(len(cache)-before),
        model_seconds=perf_counter()-begun, new_observations=0, new_paid_samples=0)


def score_frozen(results, originals):
    # No truth is read until every later certificate has been retained.
    truth = {key(row): row for row in json.loads((V233/'scores.json').read_text())}
    if set(truth) != {key(row) for row in results}:
        raise ValueError('saved regret roster must match the original 24 policies')
    scored = []
    for row in results:
        if policies(row['queries']) != policies(originals[key(row)]['terminal_plan']['queries']):
            raise ValueError('saved truth requires unchanged policies')
        original = truth[key(row)]
        scored.append(dict(life=row['life'], index=row['index'], arm=row['arm'], kind=row['kind'],
            regrets=original['regrets'], false_certificates=sum(
                row['queries'][query]['certified'] and F(value)>F(1, 20)
                for query, value in original['regrets'].items())))
    save(OUTPUT/'scores.json', scored)
    return scored


def grouped(results):
    groups = {}
    for kind in ('failure', 'positive'):
        selected = [row for row in results if row['kind'] == kind]
        blockers = Counter(comparison['family'] for row in selected for query in ('goal', 'risk')
            for comparison in row['queries'][query]['comparisons'] if not comparison['certified'])
        groups[kind] = dict(targets=len(selected),
            old_query_ready=sum(row['old_query_ready'] for row in selected),
            v235_query_ready=sum(row['v235_query_ready'] for row in selected),
            query_ready=sum(row['query_ready'] for row in selected),
            queries={query: sum(row['queries'][query]['certified'] for row in selected)
                for query in ('reward', 'goal', 'risk')}, blockers_by_family=dict(blockers),
            arms={arm: dict(targets=sum(row['arm'] == arm for row in selected),
                query_ready=sum(row['arm'] == arm and row['query_ready'] for row in selected))
                for arm in ('ORACLE_BALANCED', 'ORACLE_GAP')})
    return groups


def life_costs():
    paid = json.loads((V231/'summary.json').read_text())
    return [dict(life=row['life'], arm=row['arm'], source_samples=row['source_samples'],
        target_samples=sum(stage['target_samples'] for stage in row['stages'].values()),
        total_samples=row['total_samples']) for row in paid['life_summaries']]


def capture(recovered):
    # Retain the independent checker's dependency closure as well; importing
    # its definitions does not read truth or execute the audit.
    from scripts import audit_life_end_query_evidence_v238

    paths = set(recovered['source_code_paths'])
    paths.update(('scripts/run_life_end_query_evidence_v238.py',
        'scripts/retained_life_end_tapes_v238.py', 'scripts/retained_query_tapes_v233.py',
        'scripts/audit_life_end_query_evidence_v238.py',
        'src/acfqp/science/life_end_query_evidence_v238.py',
        'specs/LIFE_END_QUERY_EVIDENCE_V238.md', 'reports/v238_runtime_tmp/endpoint_proof.md',
        'tests/test_life_end_query_evidence_v238.py', 'tests/test_retained_life_end_tapes_v238.py',
        'tests/test_life_end_query_evidence_v238_runner.py',
        'tests/test_life_end_query_evidence_v238_audit.py'))
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
    begun, cache, work = perf_counter(), {}, Counter()
    originals = {key(row): row for row in rows(V232/'inputs.jsonl.gz')}
    old = {key(row): row for row in rows(V235/'records.jsonl.gz')}
    if len(originals) != 24 or set(old) != set(originals):
        raise ValueError('the original 24 policies and baseline records are fixed')
    protocol = dict(stream_count=48, threshold=960, partitions=32, delta_per_life_arm='1/20',
        certification_index=77, qualification_only=True, scientific_gate_changed=False,
        new_observations=0, new_paid_samples=0, selected=[{field: row[field] for field in
            ('life', 'index', 'arm', 'kind', 'phase')} for row in originals.values()])
    phases = ['protocol_frozen']
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    start = perf_counter()
    recovered = replay.reconstruct()
    replay_seconds = perf_counter()-start
    tapes = recovered['snapshots']
    if [key(row) for row in tapes] != list(originals):
        raise ValueError('life endpoints must preserve the original qualification order')
    with gzip.open(OUTPUT/'tapes.jsonl.gz', 'wt') as stream:
        for row in tapes:
            stream.write(json.dumps(exact(row), separators=(',', ':'))+'\n')
    save(OUTPUT/'replay_summary.json', dict(recovered['summary'], replay_seconds=replay_seconds,
        source_code_paths=recovered['source_code_paths'], input_paths=recovered['input_paths']))
    save(OUTPUT/'input_references.json', dict(paid_batches=str(V231),
        original_queries=str(V232/'inputs.jsonl.gz'), early_tapes=str(V235/'tapes.jsonl.gz'),
        early_qualification=str(V235/'records.jsonl.gz'), saved_truth=str(V233/'scores.json')))
    phases.append('tapes_frozen')
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    capture(recovered)
    results = []
    with gzip.open(OUTPUT/'records.jsonl.gz', 'wt') as stream:
        for tape in tapes:
            result = qualify(tape, originals[key(tape)], old[key(tape)], cache, work)
            results.append(result)
            stream.write(json.dumps(exact(result), separators=(',', ':'))+'\n')
            stream.flush()
            print(f'life-end life={tape["life"]} index={tape["index"]} arm={tape["arm"]} '
                f'early={result["v235_query_ready"]} later={result["query_ready"]}', flush=True)
    phases.append('certificates_frozen')
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    scored = score_frozen(results, originals)
    groups = grouped(results)
    false_certificates = sum(row['false_certificates'] for row in scored)
    summary = dict(complete=True, records=len(results), groups=groups,
        stage_condition_met=(groups['failure']['query_ready'] > 0
            and groups['positive']['query_ready'] == 12 and false_certificates == 0),
        certification_index=77, life_costs=life_costs(),
        unique_profile_calls=len(cache), profile_cache_hits=sum(row['profile_cache_hits'] for row in results),
        work=dict(work), model_seconds=sum(row['model_seconds'] for row in results),
        replay_seconds=replay_seconds, false_certificates=false_certificates,
        new_observations=0, new_paid_samples=0, qualification_only=True,
        scientific_gate_changed=False, elapsed_seconds=perf_counter()-begun)
    save(OUTPUT/'summary.json', summary)
    phases.extend(['saved_truth_evaluated', 'complete'])
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=True))
    print(json.dumps(exact(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
