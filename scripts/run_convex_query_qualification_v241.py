"""Integrate the nine audited convex comparisons into all 24 fixed queries."""
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
from acfqp.science import convex_query_qualification_v241 as core

V239 = ROOT/'reports/life_end_joint_evidence_v239'
V240 = ROOT/'reports/convex_query_null_v240'
OUTPUT = ROOT/'reports/convex_query_qualification_v241'


def key(row):
    return row['life'], row['index'], row['arm']


def save(name, value):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT/name).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n')


def groups(records):
    result = {}
    for kind in ('failure', 'positive'):
        selected = [row for row in records if row['kind'] == kind]
        blockers = Counter(cert['family'] for row in selected for query in ('goal', 'risk')
                           for cert in row['queries'][query]['comparisons'] if not cert['certified'])
        result[kind] = dict(targets=len(selected),
            old_query_ready=sum(row['old_query_ready'] for row in selected),
            v235_query_ready=sum(row['v235_query_ready'] for row in selected),
            v238_query_ready=sum(row['v238_query_ready'] for row in selected),
            v239_query_ready=sum(row['v239_query_ready'] for row in selected),
            query_ready=sum(row['query_ready'] for row in selected),
            queries={query: sum(row['queries'][query]['certified'] for row in selected)
                     for query in ('reward', 'goal', 'risk')},
            blockers_by_family=dict(blockers),
            arms={arm: dict(targets=sum(row['arm'] == arm for row in selected),
                query_ready=sum(row['arm'] == arm and row['query_ready'] for row in selected))
                for arm in ('ORACLE_BALANCED', 'ORACLE_GAP')})
    return result


def score_frozen(records, previous):
    """Read only the already-saved regrets, after all certificates are frozen."""
    metadata = json.loads((OUTPUT/'run.json').read_text())
    if metadata['phases'][-1] != 'certificates_frozen':
        raise ValueError('all certificates must be frozen before saved truth is read')
    truth = {key(row): row for row in json.loads(
        (ROOT/'reports/paired_query_score_v233/scores.json').read_text())}
    originals = {key(row): row for row in previous}
    if set(truth) != set(originals) or {key(row) for row in records} != set(truth):
        raise ValueError('saved truth requires the original 24-policy roster')
    scores = []
    for row in records:
        original = originals[key(row)]
        if {query: decision['policy'] for query, decision in row['queries'].items()} != {
                query: decision['policy'] for query, decision in original['queries'].items()}:
            raise ValueError('saved regret requires unchanged policies')
        saved = truth[key(row)]
        scores.append(dict(life=row['life'], index=row['index'], arm=row['arm'], kind=row['kind'],
            regrets=saved['regrets'], false_certificates=sum(
                row['queries'][query]['certified'] and F(regret) > F(1, 20)
                for query, regret in saved['regrets'].items())))
    save('scores.json', scores)
    return scores


def capture():
    paths = ('src/acfqp/science/convex_query_qualification_v241.py',
        'scripts/run_convex_query_qualification_v241.py',
        'scripts/audit_convex_query_qualification_v241.py',
        'tests/test_convex_query_qualification_v241.py',
        'tests/test_convex_query_qualification_v241_audit.py',
        'specs/CONVEX_QUERY_QUALIFICATION_V241.md')
    for relative in paths:
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    save('source_manifest.json', list(paths))


def run():
    begun = perf_counter()
    for directory in (V239, V240):
        if not json.loads((directory/'analysis.json').read_text())['valid']:
            raise ValueError('both qualification inputs require a valid independent audit')
    with gzip.open(V239/'records.jsonl.gz', 'rt') as stream:
        previous = [json.loads(line) for line in stream]
    classifications = json.loads((V240/'records.json').read_text())
    if len(previous) != 24 or len(classifications) != 9:
        raise ValueError('the original 24 queries and nine convex diagnostics are fixed')
    protocol = dict(engine='V239_with_V240_fixed_comparisons', stream_count=48, threshold=960,
        regret_threshold='1/20', delta_per_life_arm='1/20', certification_index=77,
        qualification_only=True, scientific_gate_changed=False,
        new_observations=0, new_paid_samples=0, optimizer_calls=0,
        selected=[{field: row[field] for field in ('life', 'index', 'arm', 'kind', 'phase')}
                  for row in previous])
    phases = ['protocol_frozen']
    save('run.json', dict(protocol, phases=phases, complete=False))
    save('input_references.json', dict(
        previous_records=str(V239/'records.jsonl.gz'), previous_audit=str(V239/'analysis.json'),
        previous_summary=str(V239/'summary.json'), paid_tapes=str(V239/'tapes.jsonl.gz'),
        convex_records=str(V240/'records.json'), convex_audit=str(V240/'analysis.json'),
        convex_summary=str(V240/'summary.json'),
        saved_truth=str(ROOT/'reports/paired_query_score_v233/scores.json'),
        spec=str(ROOT/'specs/CONVEX_QUERY_QUALIFICATION_V241.md')))
    phases.append('input_references_frozen')
    save('run.json', dict(protocol, phases=phases, complete=False))
    capture()
    start = perf_counter()
    records = core.qualify(previous, classifications)
    integration_seconds = perf_counter()-start
    save('records.json', records)
    phases.append('certificates_frozen')
    save('run.json', dict(protocol, phases=phases, complete=False))
    scores = score_frozen(records, previous)
    grouped = groups(records)
    false = sum(row['false_certificates'] for row in scores)
    previous_summary = json.loads((V239/'summary.json').read_text())
    summary = dict(complete=True, records=len(records), groups=grouped,
        stage_condition_met=(grouped['failure']['query_ready'] > 0
            and grouped['positive']['query_ready'] == 12 and false == 0),
        engine=protocol['engine'], certification_index=77, false_certificates=false,
        total_comparisons=144, routed_comparisons=9, reused_comparisons=135,
        life_costs=previous_summary['life_costs'], integration_seconds=integration_seconds,
        new_observations=0, new_paid_samples=0, optimizer_calls=0,
        qualification_only=True, scientific_gate_changed=False,
        elapsed_seconds=perf_counter()-begun)
    save('summary.json', summary)
    phases.extend(['saved_truth_evaluated', 'complete'])
    save('run.json', dict(protocol, phases=phases, complete=True))
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    run()
