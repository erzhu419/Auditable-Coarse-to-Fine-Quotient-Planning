"""Frozen three-life, known-type comparison of observed action-gap acquisition."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
from itertools import combinations
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import oracle_gap_pool_v231 as core
from acfqp.science import oracle_gap_acquisition_v231 as acquisition
from acfqp.science import scoped_route_task_v228 as task
from acfqp.science import latent_mechanisms_v213 as route
from acfqp.science import mixture_confidence_v225 as scalar_cs
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_persistent_evidence_v221 import score, query_score

OUTPUT = ROOT/'reports/oracle_gap_lifecycle_v231'
LIVES = (0, 1, 2)
ARMS = ('ORACLE_BALANCED', 'ORACLE_GAP')
TARGET_INDEXES = tuple(range(3, 27))+tuple(range(30, 78))
OPERATORS, ALPHABETS = route.OPERATORS, route.ALPHABETS
CAP, BATCH = 384, 16
SOURCE_BASE, TARGET_BASE = 262000, 263000
HEAVY_PLAN_FIELDS = ('joint_constraints', 'query_certificate', 'projection_supports')


def target_seeds(life, index):
    return {op: TARGET_BASE+(life*78+index)*3+j for j, op in enumerate(OPERATORS)}


def compact_plan(plan):
    return {key: deepcopy(value) for key, value in plan.items() if key not in HEAVY_PLAN_FIELDS}


def selected_pool(state, case, identity):
    return deepcopy(state['a' if case['context'] == 'A' else 'b']['pools'][identity])


def run_target(life, index, case, identity, state, arm, law, work,
               source_paid_samples, history_paid_samples):
    """Acquire a single real target; the law is passed only to the draw routine."""
    seeds = target_seeds(life, index)
    generators = {op: random.Random(seed) for op, seed in seeds.items()}
    member, spent, model_seconds, observation_seconds = core.empty(), 0, 0., 0.
    before = selected_pool(state, case, identity)

    def timed(operation, *args):
        nonlocal model_seconds
        start = perf_counter()
        result = operation(*args)
        model_seconds += perf_counter()-start
        return result

    plan = timed(core.make_plan, member, case, state, identity, index, work)
    initial = compact_plan(plan)
    batches = []
    while spent < CAP and not core.ready(plan):
        if arm == ARMS[0]:
            choice = timed(core.balanced, member, plan, spent)
        else:
            choice = timed(acquisition.choose, member, plan, spent, work)
        op = choice['operator']
        start = sum(member[op].values())
        increments = dict.fromkeys(ALPHABETS[op], 0)
        progress = dict(draw_end=start, n=start)
        begun = perf_counter()
        draw(generators[op], law, op, increments, BATCH, work, progress)
        observation_seconds += perf_counter()-begun
        for cat, count in increments.items():
            member[op][cat] += count
        spent += BATCH
        # Only actual increments update the shared known-type evidence pool.
        timed(core.observe, state, case, identity, op, increments)
        plan = timed(core.make_plan, member, case, state, identity, index, work)
        batches.append(dict(operator=op, choice=choice, draw_start=start,
            draw_end=progress['draw_end'], increments=increments, spent=spent,
            plan=compact_plan(plan)))
    return dict(life=life, index=index, case=deepcopy(case), identity=identity,
        arm=arm, seeds=seeds, initial_plan=initial, batches=batches,
        spent=spent, member=deepcopy(member), terminal_plan=deepcopy(plan),
        pooled_before=before, pooled_after=selected_pool(state, case, identity),
        source_paid_samples=source_paid_samples, history_paid_samples=history_paid_samples,
        current_paid_samples=spent, new_paid_samples=spent,
        total_reference_paid_samples=source_paid_samples+history_paid_samples+spent,
        model_seconds=model_seconds, observation_seconds=observation_seconds,
        execution_certified=plan['utility_lower'] >= 2,
        goal_impossible=plan['goal_impossible'], query_certified=plan['query_ready'],
        joint_completed=core.ready(plan), fallback=False)


def sources(life, indexes, context, laws, records, work):
    anchors, seconds = [], 0.
    for local, index in enumerate(indexes):
        slot = local if context == 'A' else local+3
        anchor, amount = core.empty(), 384 if context == 'A' else 128
        for j, op in enumerate(OPERATORS):
            seed = SOURCE_BASE+(life*6+slot)*3+j
            generator = random.Random(seed)
            for start in range(0, amount, BATCH):
                increments = dict.fromkeys(ALPHABETS[op], 0)
                progress = dict(draw_end=start, n=start)
                begun = perf_counter()
                draw(generator, laws[index], op, increments, BATCH, work, progress)
                seconds += perf_counter()-begun
                for cat, count in increments.items():
                    anchor[op][cat] += count
                records.append(dict(life=life, context=context, index=index, slot=slot,
                    operator=op, seed=seed, draw_start=start, draw_end=progress['draw_end'],
                    increments=increments))
        anchors.append(anchor)
    return anchors, seconds


def restored_plan(saved):
    plan = deepcopy(saved)
    for key in ('predicted_utility', 'risk_upper', 'utility_lower', 'goal_upper'):
        plan[key] = F(plan[key])
    plan['mix'] = [(name, F(weight)) for name, weight in plan['mix']]
    for row in plan['envelopes'].values():
        row['bounds'] = {cat: list(map(F, pair)) for cat, pair in row['bounds'].items()}
    for row in plan['query_certificates'].values():
        row['regret_upper'] = F(row['regret_upper'])
    return plan


def oracle_goal(case, law):
    pure = route.vectors(case, law)
    utility = lambda vector: vector[0]+4*vector[2]
    values = [utility(vector) for vector in pure.values() if vector[1] <= F(1, 20)]
    for left, right in combinations(pure.values(), 2):
        if min(left[1], right[1]) < F(1, 20) < max(left[1], right[1]):
            weight = (F(1, 20)-right[1])/(left[1]-right[1])
            values.append(weight*utility(left)+(1-weight)*utility(right))
    return max(values)


def evaluate(row, law):
    """Score retained decisions after every arm and life has finished acquisition."""
    case, history, optimum = row['case'], [], oracle_goal(row['case'], law)
    points = [(row['initial_plan'], 0)]+[(batch['plan'], batch['spent']) for batch in row['batches']]
    for saved, spent in points:
        plan = restored_plan(saved)
        point = score(plan, law, case, spent)
        queries = query_score(plan['queries'], law, case)
        point.update(queries=queries,
            query_bounds_ok=all(F(0) <= queries[q]['regret'] <= certificate['regret_upper']
                for q, certificate in plan['query_certificates'].items()),
            goal_upper_ok=optimum <= plan['goal_upper'],
            false_query_certificate=plan['query_ready'] and any(
                value['regret'] > F(1, 20) for value in queries.values()),
            false_execution_certificate=plan['utility_lower'] >= 2 and (
                point['actual_utility'] < 2 or point['violation']),
            false_impossible_certificate=plan['goal_impossible'] and optimum >= 2)
        history.append(point)
    return dict(life=row['life'], index=row['index'], arm=row['arm'],
        stage=case['stage'], spent=row['spent'],
        execution_certified=row['execution_certified'], goal_impossible=row['goal_impossible'],
        query_certified=row['query_certified'], joint_completed=row['joint_completed'],
        model_seconds=row['model_seconds'], history=history, terminal=history[-1],
        oracle_goal=optimum)


def aggregate(rows):
    points = [point for row in rows for point in row['history']]
    return dict(targets=len(rows), target_samples=sum(row['spent'] for row in rows),
        execution_certified=sum(row['execution_certified'] for row in rows),
        goal_impossible=sum(row['goal_impossible'] for row in rows),
        query_certified=sum(row['query_certified'] for row in rows),
        joint_completed=sum(row['joint_completed'] for row in rows),
        model_seconds=sum(row['model_seconds'] for row in rows),
        mean_query_regret=sum(float(q['regret']) for row in rows
            for q in row['terminal']['queries'].values())/(3*len(rows)),
        mean_actual_utility=sum(float(row['terminal']['actual_utility']) for row in rows)/len(rows),
        risk_violations=sum(point['violation'] for point in points),
        max_actual_risk=max(float(point['actual'][1]) for point in points),
        false_query_certificates=sum(point['false_query_certificate'] for point in points),
        false_execution_certificates=sum(point['false_execution_certificate'] for point in points),
        false_impossible_certificates=sum(point['false_impossible_certificate'] for point in points),
        false_query_bounds=sum(not point['query_bounds_ok'] for point in points),
        false_goal_upper=sum(not point['goal_upper_ok'] for point in points),
        uncovered_boxes=sum(not point['coverage'] for point in points))


def capture():
    files = {Path(__file__).relative_to(ROOT).as_posix(),
        'tests/test_oracle_gap_lifecycle_v231_runner.py',
        'tests/test_oracle_gap_acquisition_v231.py', 'tests/test_oracle_gap_pool_v231.py',
        'specs/ORACLE_GAP_LIFECYCLE_V231.md'}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):
                files.add(path.relative_to(ROOT).as_posix())
    for name in sorted(files):
        destination = OUTPUT/'source_code'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, destination)
    save(OUTPUT/'source_manifest.json', [dict(path=name) for name in sorted(files)])


def run():
    begun = perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    capture()
    protocol = dict(lives=LIVES, arms=ARMS, targets_per_life=72, cap=CAP, batch=BATCH,
        source_seed_base=SOURCE_BASE, target_seed_base=TARGET_BASE,
        oracle_information=['true source index', 'B changed operator', 'B-to-A correspondence'],
        scientific_gate_changed=False, fresh_scientific_gate=False,
        qualification_only=True, per_arm_source_samples_per_life=4608)
    save(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen'], complete=False))
    work = {arm: Counter() for arm in ARMS}
    source_work, source_records, evidence, cases_saved, final_states, orders = Counter(), [], [], [], [], []
    model_seconds = {arm: dict.fromkeys(LIVES, 0.) for arm in ARMS}
    observation_seconds = {arm: dict.fromkeys(LIVES, 0.) for arm in ARMS}
    source_seconds = dict.fromkeys(LIVES, 0.)
    for life in LIVES:
        cases, laws, identities, metadata = task.world(life)
        cases_saved.append(dict(life=life, cases=cases))
        save(OUTPUT/'cases.json', cases_saved)
        a_anchors, source_seconds[life] = sources(life, (0, 1, 2), 'A', laws, source_records, source_work)
        save(OUTPUT/'source_records.json', source_records)
        states, caches, paid_history = {}, {arm: {} for arm in ARMS}, dict.fromkeys(ARMS, 0)

        def timed(arm, operation, *args):
            scalar_cs._INTERVAL_CACHE = caches[arm]
            start = perf_counter()
            result = operation(*args)
            model_seconds[arm][life] += perf_counter()-start
            return result

        for arm in ARMS[life % 2:]+ARMS[:life % 2]:
            states[arm] = timed(arm, core.prepare, a_anchors, life, work[arm])
        with gzip.open(OUTPUT/f'records_life_{life:02d}.jsonl.gz', 'wt', encoding='utf-8') as stream:
            for position, index in enumerate(TARGET_INDEXES):
                if index == 30:
                    b_anchors, seconds = sources(life, (27, 28, 29), 'B', laws, source_records, source_work)
                    source_seconds[life] += seconds
                    evidence.append(dict(life=life, a=a_anchors, b=b_anchors))
                    save(OUTPUT/'source_records.json', source_records)
                    save(OUTPUT/'source_evidence.json', evidence)
                    for arm in ARMS:
                        timed(arm, core.begin_b, states[arm], b_anchors,
                            metadata['changed_operator'], metadata['b_to_a'], work[arm])
                offset = (life+position) % 2
                order = ARMS[offset:]+ARMS[:offset]
                orders.append(dict(life=life, index=index, order=order))
                for arm in order:
                    scalar_cs._INTERVAL_CACHE = caches[arm]
                    row = run_target(life, index, cases[index], identities[index], states[arm],
                        arm, laws[index], work[arm], 3456 if index < 30 else 4608, paid_history[arm])
                    model_seconds[arm][life] += row['model_seconds']
                    observation_seconds[arm][life] += row['observation_seconds']
                    paid_history[arm] += row['spent']
                    stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
                    stream.flush()
                    print(f'life={life} target={index} arm={arm} spent={row["spent"]} '
                        f'query={row["query_certified"]} joint={row["joint_completed"]}', flush=True)
        final_states.append(dict(life=life, states=deepcopy(states)))
        save(OUTPUT/'final_states.json', final_states)
    save(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen', 'all_decisions_frozen'],
        arm_orders=orders, complete=False))
    results = []
    for life in LIVES:
        _, laws, _, _ = task.world(life)
        with (
            gzip.open(OUTPUT/f'records_life_{life:02d}.jsonl.gz', 'rt', encoding='utf-8') as source,
            gzip.open(OUTPUT/f'results_life_{life:02d}.jsonl.gz', 'wt', encoding='utf-8') as destination,
        ):
            for line in source:
                row = json.loads(line)
                result = evaluate(row, laws[row['index']])
                results.append(result)
                destination.write(json.dumps(exact_json(result), separators=(',', ':'))+'\n')
    life_summaries = []
    methods = {}
    for arm in ARMS:
        arm_rows = [row for row in results if row['arm'] == arm]
        primary = [row for row in arm_rows if row['stage'] == 'A_RETURN' or 42 <= row['index'] < 54]
        methods[arm] = dict(aggregate(arm_rows), source_samples=4608*len(LIVES),
            total_samples=4608*len(LIVES)+sum(row['spent'] for row in arm_rows),
            model_seconds=sum(model_seconds[arm].values()), primary=aggregate(primary))
        for life in LIVES:
            selected = [row for row in arm_rows if row['life'] == life]
            life_summaries.append(dict(life=life, arm=arm, source_samples=4608,
                stages={stage: aggregate([row for row in selected if row['stage'] == stage])
                    for stage in task.STAGES},
                primary=aggregate([row for row in selected
                    if row['stage'] == 'A_RETURN' or 42 <= row['index'] < 54]),
                total_samples=4608+sum(row['spent'] for row in selected),
                model_seconds=model_seconds[arm][life]))
    summary = dict(complete=True, kind='three_life_oracle_pool_acquisition_isolation',
        scientific_gate_changed=False, qualification_only=True, records=len(results),
        methods=methods, life_summaries=life_summaries,
        new_environment_observations=4608*len(LIVES)+sum(row['spent'] for row in results),
        physical_source_samples=4608*len(LIVES), source_samples_charged_per_arm=4608*len(LIVES),
        observation_seconds=observation_seconds, source_seconds=source_seconds,
        source_work=source_work, work=work, elapsed_seconds=perf_counter()-begun,
        row_fee_scope='each row reports cumulative sources and previous targets once for its route; row reference fees are not additive')
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol,
        phases=['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'],
        arm_orders=orders, complete=True))
    print(json.dumps(exact_json(summary), ensure_ascii=False), flush=True)
    return summary


if __name__ == '__main__':
    run()
