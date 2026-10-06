"""Zero-draw qualification of joint confidence and candidate-aware acquisition."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import scoped_repair_v228 as old
from acfqp.science import scoped_route_task_v228 as task
from acfqp.science import joint_gap_v230 as joint
from acfqp.science import gap_acquisition_v230 as acquisition
from scripts.run_conditioned_mechanisms_v205 import save

INPUT = ROOT/'reports/scoped_lifecycle_v229'
OUTPUT = ROOT/'reports/action_gap_v230'
FAILURES = ((0, 58), (1, 58), (2, 42), (2, 44), (4, 44), (4, 58))
PUBLIC = 'PUBLIC_SOURCE_MEMBER'
SOURCE_ORACLE = 'ORACLE_SOURCE_MEMBER'
POOL_ORACLE = 'ORACLE_CUMULATIVE_POOL'


def rows_for(life):
    return [row for line in (INPUT/f'records_life_{life:02d}.jsonl').read_text().splitlines()
            if (row := json.loads(line))['arm'] == 'REPAIR_CS']


def plus(left, right):
    return {op: {cat: left[op][cat]+right[op][cat] for cat in old.ALPHABETS[op]}
            for op in old.OPERATORS}


def constraint(counts, threshold, event):
    return dict(joint.region(counts, threshold), event=event)


def regions(source, member, life, context, identity, index, pooled=None):
    result = {}
    for op in old.OPERATORS:
        event = f'l{life}/{context}/pool{identity}/{op}'
        result[op] = [constraint(source[op], 720, event),
                      constraint(member[op], 8640, f'l{life}/member{index}/{op}')]
        if pooled is not None:
            result[op].append(constraint(pooled[op], 720, event))
    return result


def actual_regrets(case, law, chosen):
    vectors = old.mechanics.vectors(case, law)
    return {query: max(old.query_bounds.utility(v, weights) for v in vectors.values())
            - old.query_bounds.utility(vectors[chosen[query]['policy']], weights)
            for query, weights in old.query_bounds.WEIGHTS.items()}


def feasible_kernel(block):
    """Deterministic simplex point inside the exact candidate interval box."""
    result = {}
    for op in old.OPERATORS:
        categories = old.ALPHABETS[op]
        pairs = block[op]['bounds']
        row = {cat: F(pairs[cat][0]) for cat in categories}
        capacity = {cat: F(pairs[cat][1])-row[cat] for cat in categories}
        slack, total = 1-sum(row.values()), sum(capacity.values())
        if total:
            row = {cat: row[cat]+slack*capacity[cat]/total for cat in categories}
        assert sum(row.values()) == 1
        assert all(F(pairs[c][0]) <= row[c] <= F(pairs[c][1]) for c in categories)
        result[op] = row
    return result


def restore_box(box):
    return {op: dict(bounds={cat: [F(v) for v in pair]
                            for cat, pair in row['bounds'].items()})
            for op, row in box.items()}


def frozen_state(row, source):
    saved = row['library_before']
    banks = None if saved['b'] is None else {
        name: dict(bounds=[restore_box(box) for box in bank['bounds']])
        for name, bank in saved['b'].items()}
    return dict(a=dict(bounds=[restore_box(box) for box in saved['a']['bounds']]),
                a_anchors=deepcopy(source['a']), b=banks,
                b_points=deepcopy(saved['b_points']))


def acquisition_probe(row, source, work):
    state = frozen_state(row, source)
    member = old.empty()
    prefix = None
    for batch in row['batches']:
        for cat, count in batch['increments'].items():
            member[batch['operator']][cat] += count
        if batch['spent'] == 256:
            prefix = batch
            break
    if prefix is None:
        raise ValueError('fixed failure has no 256-observation prefix')
    before = deepcopy((state, member))
    plan = old.make_plan(member, row['case'], state, work)
    for query, certificate in plan['query_certificates'].items():
        assert certificate['regret_upper'] == F(prefix['plan']['query_certificates'][query]['regret_upper'])
    kernels = {}
    for key in plan['candidates']:
        index = plan['candidate_labels'][key]['index']
        if index not in kernels:
            kernels[index] = feasible_kernel(plan['candidate_envelopes'][key])
    plan['candidate_posteriors'] = kernels or {'member': plan['posterior']}
    start = perf_counter()
    original = old.choose(member, row['case'], state, plan, 256, work)
    old_seconds = perf_counter()-start
    start = perf_counter()
    proposed = acquisition.choose(member, plan, 256, work,
        lambda hypothetical, counter: old.make_plan(hypothetical, row['case'], state, counter))
    new_seconds = perf_counter()-start
    assert before == (state, member)
    return dict(life=row['life'], index=row['index'], context=row['case']['context'],
                spent=256, member=member, candidate_posteriors=kernels,
                original=original, proposed=proposed,
                old_seconds=old_seconds, new_seconds=new_seconds,
                immutable=True, new_observations=0)


def run():
    begun = perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    sources = {row['life']: row for row in json.loads((INPUT/'source_evidence.json').read_text())}
    selection = []
    for life, index in FAILURES:
        life_rows = rows_for(life)
        failed = next(row for row in life_rows if row['index'] == index)
        control = next(row for row in life_rows
                       if row['case']['stage'] == failed['case']['stage'] and row['query_certified'])
        selection.extend([(life, index, 'failure'), (life, control['index'], 'positive_control')])
    save(OUTPUT/'selection.json', [dict(life=l, index=i, role=role) for l, i, role in selection])
    work, records, acquisition_rows = Counter(), [], []
    for life, index, role in selection:
        cases, laws, identities, metadata = task.world(life)
        life_rows = rows_for(life)
        row = next(r for r in life_rows if r['index'] == index)
        case, member = row['case'], row['member']
        context, true_index = case['context'], identities[index]
        anchors = sources[life]['a' if context == 'A' else 'b']
        pooled = deepcopy(anchors[true_index])
        for previous in life_rows:
            if (previous['index'] <= index and previous['case']['context'] == context
                    and identities[previous['index']] == true_index):
                pooled = plus(pooled, previous['member'])
        chosen = row['terminal_plan']['queries']
        candidates = {str(i): regions(anchor, member, life, context, i, index)
                      for i, anchor in enumerate(anchors)}
        plans = {}
        for method, models in (
                (PUBLIC, candidates),
                (SOURCE_ORACLE, {str(true_index): candidates[str(true_index)]}),
                (POOL_ORACLE, {str(true_index): regions(anchors[true_index], member,
                    life, context, true_index, index, pooled)})):
            results = {key: joint.certificates(case, constraints, chosen, work)
                       for key, constraints in models.items()}
            supported = [result for result in results.values() if not result['empty']]
            if not supported:
                raise ValueError('no joint candidate remains in a truth-qualified input')
            queries = {query: dict(policy=chosen[query]['policy'],
                regret_upper=max(result['queries'][query]['regret_upper'] for result in supported))
                for query in old.query_bounds.WEIGHTS}
            for value in queries.values():
                value['certified'] = value['regret_upper'] <= F(1, 20)
            plans[method] = dict(constraints=models, candidate_certificates=results,
                query_certificates=queries, query_ready=all(value['certified'] for value in queries.values()))
        records.append(dict(life=life, index=index, role=role, arm='REPAIR_CS',
            case=case, member=member, source_counts=anchors, pooled_counts=pooled,
            true_index=true_index, chosen=chosen,
            old_certificates=row['terminal_plan']['query_certificates'],
            actual_regrets=actual_regrets(case, laws[index], chosen), methods=plans,
            retained_spent=row['spent'], source_paid_samples=sum(sum(sum(counts[op].values())
                for op in old.OPERATORS) for counts in anchors), new_observations=0))
        save(OUTPUT/'records.json', records)
        print(f'joint {life}:{index} {role} '+str({name: data['query_ready'] for name, data in plans.items()}), flush=True)
        if role == 'failure':
            acquisition_rows.append(acquisition_probe(row, sources[life], work))
            save(OUTPUT/'acquisition.json', acquisition_rows)
            print(f'acquisition {life}:{index} '+acquisition_rows[-1]['proposed']['operator'], flush=True)
    summary = dict(new_observations=0, fresh_gate_run=False, records=len(records),
        failure_examples=len(FAILURES), work=work, elapsed_seconds=perf_counter()-begun,
        ready={role: {method: sum(row['role'] == role and row['methods'][method]['query_ready']
                                 for row in records) for method in (PUBLIC, SOURCE_ORACLE, POOL_ORACLE)}
               for role in ('failure', 'positive_control')},
        acquisition_changes=sum(row['original']['operator'] != row['proposed']['operator']
                                for row in acquisition_rows),
        acquisition_old_seconds=sum(row['old_seconds'] for row in acquisition_rows),
        acquisition_new_seconds=sum(row['new_seconds'] for row in acquisition_rows))
    save(OUTPUT/'summary.json', summary)
    own_files = ('src/acfqp/science/joint_gap_v230.py', 'src/acfqp/science/gap_acquisition_v230.py',
                 'scripts/probe_action_gap_v230.py', 'specs/ACTION_GAP_V230.md')
    for name in own_files:
        destination = OUTPUT/'source_code'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, destination)
    save(OUTPUT/'source_manifest.json', list(own_files))
    print(json.dumps({k: v for k, v in summary.items() if k != 'work'}, ensure_ascii=False), flush=True)
    return summary


if __name__ == '__main__':
    run()
