"""Use the unchanged joint engine on V238's fixed paid-life endpoints."""
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
from scripts.run_life_end_query_evidence_v238 import exact, save, rows, key, policies, grouped

V232 = ROOT/'reports/kernel_query_profile_v232'
V233 = ROOT/'reports/paired_query_score_v233'
V235 = ROOT/'reports/joint_query_qualification_v235'
V238 = ROOT/'reports/life_end_query_evidence_v238'
OUTPUT = ROOT/'reports/life_end_joint_evidence_v239'


def qualify(tape, previous, early, conditional, cache, work):
    begun, before = perf_counter(), len(cache)
    plan = previous['terminal_plan']
    result = core.certificates(tape['operators'], tape['case'], plan['queries'], cache, work)
    if policies(result['queries']) != policies(plan['queries']):
        raise ValueError('same-endpoint comparison must retain original policies')
    return dict(**{field: tape[field] for field in
        ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees',
         'early_fees', 'endpoint_index', 'certificate_index', 'evidence_end_index')},
        queries=result['queries'], query_ready=result['all_ready'],
        old_query_ready=plan['query_ready'], v235_query_ready=early['query_ready'],
        v238_query_ready=conditional['query_ready'],
        row_lengths={op: len(values) for op, values in tape['operators'].items()},
        unique_profile_calls=len(cache)-before,
        profile_cache_hits=len(result['comparison_records'])-(len(cache)-before),
        model_seconds=perf_counter()-begun, new_observations=0, new_paid_samples=0)


def score_frozen(results, originals):
    truth = {key(row): row for row in json.loads((V233/'scores.json').read_text())}
    if set(truth) != {key(row) for row in results}:
        raise ValueError('saved truth must match the fixed 24-policy roster')
    scored = []
    for row in results:
        if policies(row['queries']) != policies(originals[key(row)]['terminal_plan']['queries']):
            raise ValueError('saved regret requires unchanged policies')
        original = truth[key(row)]
        scored.append(dict(life=row['life'], index=row['index'], arm=row['arm'], kind=row['kind'],
            regrets=original['regrets'], false_certificates=sum(
                row['queries'][query]['certified'] and F(value)>core.REGRET
                for query, value in original['regrets'].items())))
    save(OUTPUT/'scores.json', scored)
    return scored


def capture():
    from scripts import audit_life_end_joint_evidence_v239

    paths = {'scripts/run_life_end_joint_evidence_v239.py',
        'scripts/audit_life_end_joint_evidence_v239.py',
        'specs/LIFE_END_JOINT_EVIDENCE_V239.md', 'reports/v239_runtime_tmp/joint_endpoint_note.md',
        'tests/test_life_end_joint_evidence_v239.py',
        'tests/test_life_end_joint_evidence_v239_runner.py',
        'tests/test_life_end_joint_evidence_v239_audit.py'}
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
    prior_audit = json.loads((V238/'analysis.json').read_text())
    if not prior_audit['valid']:
        raise ValueError('fixed paid endpoints must have passed independent audit')
    originals = {key(row): row for row in rows(V232/'inputs.jsonl.gz')}
    early = {key(row): row for row in rows(V235/'records.jsonl.gz')}
    conditional = {key(row): row for row in rows(V238/'records.jsonl.gz')}
    tapes = rows(V238/'tapes.jsonl.gz')
    if (len(originals) != 24 or [key(row) for row in tapes] != list(originals)
            or set(early) != set(originals) or set(conditional) != set(originals)):
        raise ValueError('the original 24 endpoints and comparator records are fixed')
    protocol = dict(engine='V235_joint_all_paid', stream_count=48, threshold=960, partitions=32,
        delta_per_life_arm='1/20', certification_index=77, qualification_only=True,
        scientific_gate_changed=False, new_observations=0, new_paid_samples=0,
        selected=[{field: tape[field] for field in ('life', 'index', 'arm', 'kind', 'phase')}
                  for tape in tapes])
    phases = ['protocol_frozen']
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    shutil.copyfile(V238/'tapes.jsonl.gz', OUTPUT/'tapes.jsonl.gz')
    save(OUTPUT/'input_references.json', dict(paid_tapes=str(V238/'tapes.jsonl.gz'),
        endpoint_audit=str(V238/'analysis.json'), conditional_qualification=str(V238/'records.jsonl.gz'),
        original_queries=str(V232/'inputs.jsonl.gz'), early_joint_qualification=str(V235/'records.jsonl.gz'),
        saved_truth=str(V233/'scores.json')))
    phases.append('tapes_frozen')
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    capture()
    results = []
    with gzip.open(OUTPUT/'records.jsonl.gz', 'wt') as stream:
        for tape in tapes:
            snapshot = key(tape)
            result = qualify(tape, originals[snapshot], early[snapshot], conditional[snapshot], cache, work)
            results.append(result)
            stream.write(json.dumps(exact(result), separators=(',', ':'))+'\n')
            stream.flush()
            print(f'joint-end life={tape["life"]} index={tape["index"]} arm={tape["arm"]} '
                f'conditional={result["v238_query_ready"]} joint={result["query_ready"]}', flush=True)
    phases.append('certificates_frozen')
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=False))
    scored = score_frozen(results, originals)
    groups = grouped(results)
    for kind, group in groups.items():
        group['v238_query_ready'] = sum(row['v238_query_ready'] for row in results if row['kind'] == kind)
    false_certificates = sum(row['false_certificates'] for row in scored)
    prior_summary = json.loads((V238/'summary.json').read_text())
    summary = dict(complete=True, records=len(results), groups=groups,
        stage_condition_met=(groups['failure']['query_ready'] > 0
            and groups['positive']['query_ready'] == 12 and false_certificates == 0),
        engine=protocol['engine'], certification_index=77, life_costs=prior_summary['life_costs'],
        unique_profile_calls=len(cache), profile_cache_hits=sum(row['profile_cache_hits'] for row in results),
        work=dict(work), model_seconds=sum(row['model_seconds'] for row in results),
        false_certificates=false_certificates, new_observations=0, new_paid_samples=0,
        qualification_only=True, scientific_gate_changed=False, elapsed_seconds=perf_counter()-begun)
    save(OUTPUT/'summary.json', summary)
    phases.extend(['saved_truth_evaluated', 'complete'])
    save(OUTPUT/'run.json', dict(protocol, phases=phases, complete=True))
    print(json.dumps(exact(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
