"""Six frozen-case paired continuations of acquisition, with actual suffix reads."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import scoped_repair_v228 as old
from acfqp.science import scoped_route_task_v228 as task
from acfqp.science import gap_acquisition_v230 as acquisition
from scripts.probe_action_gap_v230 import (
    INPUT, FAILURES, frozen_state, feasible_kernel, plus, rows_for)
from scripts.run_conditioned_mechanisms_v205 import draw, save, exact_json
from scripts.run_persistent_evidence_v221 import score, query_score

OUTPUT = ROOT/'reports/gap_continuation_v230'
METHODS = ('OLD_V229', 'CANDIDATE_MULTI')
PREFIX, CAP, BATCH = 256, 384, 16
SOURCE_FILES = (
    'scripts/run_gap_continuation_v230.py',
    'scripts/probe_action_gap_v230.py',
    'src/acfqp/science/gap_acquisition_v230.py',
    'tests/test_gap_continuation_v230.py',
    'specs/ACTION_GAP_V230.md',
)


def suffix_seeds(life, index):
    return {op: 260000+(life*78+index)*3+j for j, op in enumerate(old.OPERATORS)}


def prefix_counts(row):
    member = old.empty()
    for batch in row['batches']:
        if batch['spent'] > PREFIX:
            break
        addition = old.empty()
        addition[batch['operator']] = batch['increments']
        member = plus(member, addition)
    if sum(sum(counts.values()) for counts in member.values()) != PREFIX:
        raise ValueError('fixed failure has no complete 256-observation prefix')
    return member


def reference_costs(row, source, history):
    # Every selected case follows the paid B source interface.  Entire earlier
    # target history includes the A evidence inherited by repair in B as well.
    sources = sum(sum(sum(counts[op].values()) for op in old.OPERATORS)
                  for context in ('a', 'b') for counts in source[context])
    previous = [r for r in history if r['index'] < row['index']]
    return dict(source_paid_samples=sources,
                history_paid_samples=sum(r['spent'] for r in previous),
                historical_targets=len(previous), prefix_paid_samples=PREFIX)


def ready(plan):
    return (plan['utility_lower'] >= 2 or plan['goal_impossible']) and plan['query_ready']


def candidate_plan(member, case, state, work):
    plan = old.make_plan(member, case, state, work)
    kernels = {}
    for key in plan['candidates']:
        index = plan['candidate_labels'][key]['index']
        if index not in kernels:
            kernels[index] = feasible_kernel(plan['candidate_envelopes'][key])
    plan['candidate_posteriors'] = kernels or {'member': plan['posterior']}
    return plan


def continue_one(row, source, history, method, law):
    """Continue one actual prefix; oracle scoring and evidence commits are absent."""
    state, member = frozen_state(row, source), prefix_counts(row)
    library_before = deepcopy(state)
    original_prefix = deepcopy(member)
    seeds = suffix_seeds(row['life'], row['index'])
    generators = {op: random.Random(seed) for op, seed in seeds.items()}
    offsets = dict.fromkeys(old.OPERATORS, 0)
    work, model_seconds, observation_seconds = Counter(), 0., 0.
    # A fresh per-method cache prevents the preceding comparison from paying
    # for this method's confidence interval calculations.
    old.confidence.mixture._INTERVAL_CACHE = {}
    begun = perf_counter()
    plan = candidate_plan(member, row['case'], state, work)
    model_seconds += perf_counter()-begun
    initial_plan = deepcopy(plan)
    batches, spent = [], PREFIX
    while spent < CAP and not ready(plan):
        begun = perf_counter()
        if method == METHODS[0]:
            choice = old.choose(member, row['case'], state, plan, spent, work)
        else:
            choice = acquisition.choose(member, plan, spent, work,
                lambda hypothetical, counter: old.make_plan(
                    hypothetical, row['case'], state, counter))
        model_seconds += perf_counter()-begun
        operator = choice['operator']
        increments = dict.fromkeys(old.ALPHABETS[operator], 0)
        progress = dict(draw_end=offsets[operator], n=offsets[operator])
        start = offsets[operator]
        begun = perf_counter()
        draw(generators[operator], law, operator, increments, BATCH, work, progress)
        observation_seconds += perf_counter()-begun
        offsets[operator] = progress['draw_end']
        addition = old.empty()
        addition[operator] = increments
        member = plus(member, addition)
        spent += BATCH
        begun = perf_counter()
        plan = candidate_plan(member, row['case'], state, work)
        model_seconds += perf_counter()-begun
        batches.append(dict(operator=operator, seed=seeds[operator],
            draw_start=start, draw_end=offsets[operator], increments=increments,
            spent=spent, choice=choice, plan=deepcopy(plan)))
    cost = reference_costs(row, source, history)
    cost['additional_paid_samples'] = spent-PREFIX
    cost['total_reference_paid_samples'] = sum(cost[key] for key in (
        'source_paid_samples', 'history_paid_samples', 'prefix_paid_samples',
        'additional_paid_samples'))
    return dict(life=row['life'], index=row['index'], method=method, case=row['case'],
        seeds=seeds, prefix_member=original_prefix, member=member, spent=spent,
        prefix_operator_samples={op: sum(original_prefix[op].values()) for op in old.OPERATORS},
        suffix_operator_samples=offsets, fees=cost, initial_plan=initial_plan,
        terminal_plan=deepcopy(plan), batches=batches, completed=ready(plan),
        execution_certified=plan['utility_lower'] >= 2,
        goal_impossible=plan['goal_impossible'], query_certified=plan['query_ready'],
        library_before=library_before, library_after=deepcopy(state),
        library_frozen=state == library_before, commits=0, work=work,
        model_seconds=model_seconds, observation_seconds=observation_seconds)


def evaluate(record):
    _, laws, _, _ = task.world(record['life'])
    law, case = laws[record['index']], record['case']
    plans = [record['initial_plan']]+[batch['plan'] for batch in record['batches']]
    history = []
    for position, plan in enumerate(plans):
        spent = PREFIX if position == 0 else record['batches'][position-1]['spent']
        result = score(plan, law, case, spent)
        result['queries'] = query_score(plan['queries'], law, case)
        result['query_bounds_ok'] = all(F(0) <= result['queries'][query]['regret']
            <= certificate['regret_upper'] for query, certificate in plan['query_certificates'].items())
        history.append(result)
    return dict(life=record['life'], index=record['index'], method=record['method'],
                history=history, initial=history[0], terminal=history[-1])


def run():
    begun = perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    for name in SOURCE_FILES:
        destination = OUTPUT/'source_code'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, destination)
    save(OUTPUT/'source_manifest.json', [dict(path=name) for name in SOURCE_FILES])
    sources = {row['life']: row for row in json.loads((INPUT/'source_evidence.json').read_text())}
    records, orders = [], []
    save(OUTPUT/'run.json', dict(phases=['protocol_frozen'], input=str(INPUT),
        selection=FAILURES, methods=METHODS, prefix=PREFIX, cap=CAP,
        suffix_seed_base=260000, qualification_only=True))
    for position, (life, index) in enumerate(FAILURES):
        life_rows = rows_for(life)
        row = next(record for record in life_rows if record['index'] == index)
        _, laws, _, _ = task.world(life)
        order = METHODS[position % 2:]+METHODS[:position % 2]
        orders.append(dict(life=life, index=index, order=order))
        for method in order:
            record = continue_one(row, sources[life], life_rows, method, laws[index])
            records.append(record)
            save(OUTPUT/'records.json', records)
            print(f'continuation {life}:{index} {method} new={record["fees"]["additional_paid_samples"]} '
                  f'ready={record["completed"]}', flush=True)
    # All actual decisions are saved before any law-based regret assessment.
    save(OUTPUT/'run.json', dict(phases=['protocol_frozen', 'all_decisions_frozen'],
        input=str(INPUT), selection=FAILURES, arm_orders=orders, prefix=PREFIX,
        cap=CAP, suffix_seed_base=260000, qualification_only=True))
    results = [evaluate(record) for record in records]
    save(OUTPUT/'results.json', results)
    methods = {}
    for method in METHODS:
        selected = [row for row in records if row['method'] == method]
        assessed = [row for row in results if row['method'] == method]
        methods[method] = dict(records=len(selected), completed=sum(r['completed'] for r in selected),
            query_certified=sum(r['query_certified'] for r in selected),
            additional_paid_samples=sum(r['fees']['additional_paid_samples'] for r in selected),
            model_seconds=sum(r['model_seconds'] for r in selected),
            mean_query_regret=sum(float(q['regret']) for row in assessed
                for q in row['terminal']['queries'].values())/(len(assessed)*3),
            risk_violations=sum(point['violation'] for row in assessed for point in row['history']),
            false_query_bounds=sum(not point['query_bounds_ok'] for row in assessed for point in row['history']))
    paired = []
    for life, index in FAILURES:
        pair = {row['method']: row for row in records if row['life'] == life and row['index'] == index}
        left, right = pair[METHODS[0]], pair[METHODS[1]]
        paired.append(dict(life=life, index=index,
            completed_old=left['completed'], completed_new=right['completed'],
            additional_old=left['fees']['additional_paid_samples'],
            additional_new=right['fees']['additional_paid_samples'],
            saved_observations=left['fees']['additional_paid_samples']-right['fees']['additional_paid_samples']))
    summary = dict(kind='six_fixed_failure_actual_paired_continuations', qualification_only=True,
        scientific_gate_changed=False, methods=methods, paired=paired,
        new_environment_observations=sum(r['fees']['additional_paid_samples'] for r in records),
        reference_fee_scope='each fixed snapshot includes all paid sources and prior target history; overlapping snapshots are not additive',
        library_frozen=all(row['library_frozen'] for row in records), elapsed_seconds=perf_counter()-begun)
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(phases=['protocol_frozen', 'all_decisions_frozen',
        'oracle_evaluated', 'complete'], input=str(INPUT), selection=FAILURES,
        arm_orders=orders, prefix=PREFIX, cap=CAP, suffix_seed_base=260000,
        qualification_only=True, complete=True))
    print(json.dumps(exact_json(summary), ensure_ascii=False), flush=True)
    return summary


if __name__ == '__main__':
    run()
