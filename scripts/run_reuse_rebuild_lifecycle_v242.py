"""Fresh matched lifecycles: retain unchanged A rows or rebuild all B rows."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import reuse_rebuild_pool_v242 as core
from acfqp.science import oracle_gap_acquisition_v231 as acquisition
from acfqp.science import scoped_route_task_v228 as task
from acfqp.science import mixture_confidence_v225 as scalar_cs
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_oracle_gap_lifecycle_v231 import oracle_goal, restored_plan
from scripts.run_persistent_evidence_v221 import score, query_score

OUTPUT = ROOT/'reports/reuse_rebuild_lifecycle_v242'
LIVES, ARMS = (0, 1, 2), ('REUSE', 'REBUILD')
TARGETS = tuple(range(3, 27))+tuple(range(30, 78))
OPERATORS, ALPHABETS = core.OPERATORS, core.ALPHABETS
SOURCE_BASE, TARGET_BASE = 278000, 279000
TOTAL_BUDGETS, SOURCE_COST = (14144, 17072, 17168), 4608
CAP, BATCH = 384, 16


def retain_plan(plan, profile_stream, profile_ids):
    """Store each proof once; each retained decision keeps its exact proof refs."""
    saved = deepcopy({field: value for field, value in plan.items() if field != 'query_evidence'})
    evidence, decisions = plan['query_evidence'], {}
    for query, decision in evidence['queries'].items():
        retained = {field: value for field, value in decision.items() if field != 'comparisons'}
        if 'comparisons' in decision:
            retained['comparisons'] = []
            for certificate in decision['comparisons']:
                counts = tuple((name, tuple(row.items())) for name, row in certificate['projected_counts'].items())
                costs = (plan['case']['operating'], F(plan['case']['retry_cost']))
                identity = (certificate.get('engine', 'V235'), costs, query,
                    certificate['chosen'], certificate['other'], certificate['family'], counts)
                if identity not in profile_ids:
                    profile_ids[identity] = len(profile_ids)
                    record = dict(profile_id=profile_ids[identity], case=dict(
                        operating=costs[0], retry_cost=str(costs[1])), certificate=certificate)
                    profile_stream.write(json.dumps(exact_json(record), separators=(',', ':'))+'\n')
                    profile_stream.flush()
                retained['comparisons'].append(dict(profile_id=profile_ids[identity],
                    other=certificate['other'], certified=certificate['certified']))
        decisions[query] = retained
    saved['query_evidence'] = dict(queries=decisions, all_ready=evidence['all_ready'], threshold=960)
    return saved


def sources(life, context, laws, records, work):
    indexes = (0, 1, 2) if context == 'A' else (27, 28, 29)
    amount, anchors, seconds = (384 if context == 'A' else 128), [], 0.
    for local, index in enumerate(indexes):
        slot = local if context == 'A' else local+3
        anchor = core.empty()
        for j, operator in enumerate(OPERATORS):
            seed = SOURCE_BASE+(life*6+slot)*3+j
            generator = random.Random(seed)
            for start in range(0, amount, BATCH):
                increments = dict.fromkeys(ALPHABETS[operator], 0)
                progress = dict(draw_end=start, n=start)
                begun = perf_counter()
                draw(generator, laws[index], operator, increments, BATCH, work, progress)
                seconds += perf_counter()-begun
                for category, count in increments.items():
                    anchor[operator][category] += count
                records.append(dict(life=life, context=context, index=index, slot=slot,
                    operator=operator, seed=seed, draw_start=start, draw_end=progress['draw_end'],
                    increments=increments))
        anchors.append(anchor)
    return anchors, seconds


def run_target(life, index, case, identity, state, arm, law, work,
               source_paid_samples, history_paid_samples, query_cache, profile_stream, profile_ids):
    seeds = {op: TARGET_BASE+(life*78+index)*3+j for j, op in enumerate(OPERATORS)}
    generators = {op: random.Random(seed) for op, seed in seeds.items()}
    member, spent, model_seconds, observation_seconds = core.empty(), 0, 0., 0.
    bank = 'a' if case['context'] == 'A' else 'b'
    before = deepcopy(state[bank]['pools'][identity])
    available = TOTAL_BUDGETS[life]-SOURCE_COST-history_paid_samples

    def timed(operation, *args):
        nonlocal model_seconds
        begun = perf_counter()
        result = operation(*args)
        model_seconds += perf_counter()-begun
        return result

    plan = timed(core.make_plan, member, case, state, identity, index, query_cache, work)
    initial = retain_plan(plan, profile_stream, profile_ids)
    batches = []
    while spent+BATCH <= min(CAP, available) and not core.ready(plan):
        choice = timed(acquisition.choose, member, plan, spent, work)
        operator = choice['operator']
        start = sum(member[operator].values())
        increments = dict.fromkeys(ALPHABETS[operator], 0)
        progress = dict(draw_end=start, n=start)
        begun = perf_counter()
        draw(generators[operator], law, operator, increments, BATCH, work, progress)
        observation_seconds += perf_counter()-begun
        for category, count in increments.items():
            member[operator][category] += count
        spent += BATCH
        timed(core.observe, state, case, identity, operator, increments)
        plan = timed(core.make_plan, member, case, state, identity, index, query_cache, work)
        batches.append(dict(operator=operator, choice=choice, draw_start=start,
            draw_end=progress['draw_end'], increments=increments, spent=spent,
            plan=retain_plan(plan, profile_stream, profile_ids)))
    terminal = batches[-1]['plan'] if batches else initial
    completed = core.ready(plan)
    return dict(life=life, index=index, case=deepcopy(case), identity=identity, arm=arm, seeds=seeds,
        initial_plan=initial, batches=batches, terminal_plan=terminal, spent=spent, member=deepcopy(member),
        pooled_before=before, pooled_after=deepcopy(state[bank]['pools'][identity]),
        source_paid_samples=source_paid_samples, history_paid_samples=history_paid_samples,
        current_paid_samples=spent, new_paid_samples=spent,
        total_reference_paid_samples=source_paid_samples+history_paid_samples+spent,
        life_budget_remaining_before=available, life_budget_remaining_after=available-spent,
        budget_exhausted=available-spent < BATCH, member_cap_exhausted=spent == CAP,
        model_seconds=model_seconds, observation_seconds=observation_seconds,
        execution_certified=plan['utility_lower'] >= 2, goal_impossible=plan['goal_impossible'],
        query_certified=plan['query_ready'], joint_completed=completed, fallback=not completed,
        executed_mix=deepcopy(plan['mix']) if completed else [('WAIT', F(1))])


def evaluate(row, law):
    case, history, optimum = row['case'], [], oracle_goal(row['case'], law)
    points = [(row['initial_plan'], 0)]+[(batch['plan'], batch['spent']) for batch in row['batches']]
    for saved, spent in points:
        plan = restored_plan(saved)
        point = score(plan, law, case, spent)
        queries = query_score(plan['queries'], law, case)
        point.update(queries=queries,
            false_query_certificates=sum(certificate['certified'] and queries[query]['regret'] > F(1, 20)
                for query, certificate in plan['query_certificates'].items()),
            false_execution_certificate=plan['utility_lower'] >= 2 and (
                point['actual_utility'] < 2 or point['violation']),
            false_impossible_certificate=plan['goal_impossible'] and optimum >= 2,
            goal_upper_ok=optimum <= plan['goal_upper'])
        history.append(point)
    actual = deepcopy(restored_plan(row['terminal_plan']))
    actual['mix'] = [(policy, F(weight)) for policy, weight in row['executed_mix']]
    if row['fallback']:
        actual['risk_upper'] = F(0)
        actual['utility_lower'] = F(0)
    executed = score(actual, law, case, row['spent'])
    return dict(life=row['life'], index=row['index'], arm=row['arm'], stage=case['stage'],
        spent=row['spent'], execution_certified=row['execution_certified'],
        goal_impossible=row['goal_impossible'], query_certified=row['query_certified'],
        joint_completed=row['joint_completed'], fallback=row['fallback'],
        budget_exhausted=row['budget_exhausted'], model_seconds=row['model_seconds'],
        history=history, terminal=history[-1], executed=executed)


def aggregate(records):
    points = [point for row in records for point in row['history']]
    return dict(targets=len(records), target_samples=sum(row['spent'] for row in records),
        query_certified=sum(row['query_certified'] for row in records),
        joint_completed=sum(row['joint_completed'] for row in records),
        execution_certified=sum(row['execution_certified'] for row in records),
        goal_impossible=sum(row['goal_impossible'] for row in records),
        fallbacks=sum(row['fallback'] for row in records),
        budget_exhausted_targets=sum(row['budget_exhausted'] for row in records),
        model_seconds=sum(row['model_seconds'] for row in records),
        false_query_certificates=sum(point['false_query_certificates'] for point in points),
        false_execution_certificates=sum(point['false_execution_certificate'] for point in points),
        false_impossible_certificates=sum(point['false_impossible_certificate'] for point in points),
        risk_violations=sum(point['violation'] for point in points),
        false_goal_uppers=sum(not point['goal_upper_ok'] for point in points),
        uncovered_boxes=sum(not point['coverage'] for point in points),
        mean_executed_utility=sum(float(row['executed']['actual_utility']) for row in records)/len(records))


def summarize(records, model_seconds):
    methods, life_summaries = {}, []
    for arm in ARMS:
        selected = [row for row in records if row['arm'] == arm]
        methods[arm] = dict(aggregate(selected), source_samples=SOURCE_COST*3,
            total_samples=SOURCE_COST*3+sum(row['spent'] for row in selected),
            late_b=aggregate([row for row in selected if 42 <= row['index'] < 54]),
            a_return=aggregate([row for row in selected if row['stage'] == 'A_RETURN']))
        methods[arm]['model_seconds'] = sum(model_seconds[arm].values())
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            life_summaries.append(dict(life=life, arm=arm, source_samples=SOURCE_COST,
                total_samples=SOURCE_COST+sum(row['spent'] for row in subset),
                model_seconds=model_seconds[arm][life],
                stages={stage: aggregate([row for row in subset if row['stage'] == stage])
                        for stage in task.STAGES}))
    reuse, rebuild = methods['REUSE'], methods['REBUILD']
    conditions = dict(late_b_quality=reuse['late_b']['query_certified'] >= 27,
        a_return_quality=reuse['a_return']['query_certified'] >= 54,
        matched_late_b_quality=reuse['late_b']['query_certified'] >= rebuild['late_b']['query_certified'],
        matched_a_return_quality=reuse['a_return']['query_certified'] >= rebuild['a_return']['query_certified'],
        matched_joint_quality=reuse['joint_completed'] >= rebuild['joint_completed'],
        actual_acquisition_saving=reuse['total_samples'] < rebuild['total_samples'],
        valid_certificates_and_execution=all(method[field] == 0 for method in methods.values()
            for field in ('false_query_certificates', 'false_execution_certificates',
                          'false_impossible_certificates', 'risk_violations')))
    paired = [dict(life=life,
        rebuild_minus_reuse_samples=next(row['total_samples'] for row in life_summaries
            if row['life'] == life and row['arm'] == 'REBUILD')-
            next(row['total_samples'] for row in life_summaries if row['life'] == life and row['arm'] == 'REUSE'))
        for life in LIVES]
    return dict(complete=True, records=len(records), methods=methods, life_summaries=life_summaries,
        paired=paired, conditions=conditions, stage_condition_met=all(conditions.values()),
        physical_source_samples=SOURCE_COST*3, source_samples_charged_per_arm=SOURCE_COST*3,
        new_environment_observations=SOURCE_COST*3+sum(row['spent'] for row in records),
        scientific_gate_changed=False, qualification_only=True)


def capture():
    from scripts import audit_reuse_rebuild_lifecycle_v242
    paths = set(('scripts/run_reuse_rebuild_lifecycle_v242.py',
        'scripts/audit_reuse_rebuild_lifecycle_v242.py',
        'src/acfqp/science/online_joint_query_v242.py', 'src/acfqp/science/reuse_rebuild_pool_v242.py',
        'tests/test_online_joint_query_v242.py', 'tests/test_reuse_rebuild_pool_v242.py',
        'tests/test_reuse_rebuild_lifecycle_v242_runner.py',
        'tests/test_reuse_rebuild_lifecycle_v242_audit.py', 'specs/REUSE_REBUILD_LIFECYCLE_V242.md'))
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):
                paths.add(path.relative_to(ROOT).as_posix())
    for relative in sorted(paths):
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    save(OUTPUT/'source_manifest.json', sorted(paths))


def run():
    begun = perf_counter()
    prerequisite = json.loads((ROOT/'reports/convex_query_qualification_v241/analysis.json').read_text())
    if not prerequisite['valid'] or not prerequisite['stage_condition_met']:
        raise ValueError('V241 qualification and independent audit must permit lifecycle comparison')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    protocol = dict(lives=LIVES, arms=ARMS, targets_per_life=72, cap=CAP, batch=BATCH,
        source_seed_base=SOURCE_BASE, target_seed_base=TARGET_BASE, per_life_total_budgets=TOTAL_BUDGETS,
        source_samples_per_life=SOURCE_COST, query_stream_count=48, query_threshold=960,
        query_delta_per_life_arm='1/20', execution_delta_per_life_arm='1/20', combined_delta_upper='1/10',
        scientific_gate_changed=False, qualification_only=True,
        oracle_information=['type identity', 'B changed operator', 'B-to-A correspondence'])
    save(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen'], complete=False))
    capture()
    source_records, source_evidence, cases_saved, interfaces, final_states, orders = [], [], [], [], [], []
    work = {arm: Counter() for arm in ARMS}
    source_work = Counter()
    model_seconds = {arm: dict.fromkeys(LIVES, 0.) for arm in ARMS}
    observation_seconds = {arm: dict.fromkeys(LIVES, 0.) for arm in ARMS}
    source_seconds, profile_counts = {}, {}
    for life in LIVES:
        cases, laws, identities, metadata = task.world(life)
        cases_saved.append(dict(life=life, cases=cases))
        interfaces.append(dict(life=life, identities=identities, metadata=metadata))
        save(OUTPUT/'cases.json', cases_saved)
        save(OUTPUT/'interfaces.json', interfaces)
        a_anchors, source_seconds[life] = sources(life, 'A', laws, source_records, source_work)
        save(OUTPUT/'source_records.json', source_records)
        states = {arm: core.prepare(a_anchors, life, arm, work[arm]) for arm in ARMS}
        query_caches, interval_caches = {arm: {} for arm in ARMS}, {arm: {} for arm in ARMS}
        paid, profile_ids = dict.fromkeys(ARMS, 0), {}
        with (gzip.open(OUTPUT/f'records_life_{life:02d}.jsonl.gz', 'wt') as stream,
              gzip.open(OUTPUT/f'profiles_life_{life:02d}.jsonl.gz', 'wt') as profiles):
            for position, index in enumerate(TARGETS):
                if index == 30:
                    b_anchors, seconds = sources(life, 'B', laws, source_records, source_work)
                    source_seconds[life] += seconds
                    source_evidence.append(dict(life=life, a=a_anchors, b=b_anchors))
                    save(OUTPUT/'source_records.json', source_records)
                    save(OUTPUT/'source_evidence.json', source_evidence)
                    for arm in ARMS:
                        core.begin_b(states[arm], b_anchors, metadata['changed_operator'], metadata['b_to_a'], work[arm])
                offset = (life+position) % 2
                order = ARMS[offset:]+ARMS[:offset]
                orders.append(dict(life=life, index=index, order=order))
                for arm in order:
                    scalar_cs._INTERVAL_CACHE = interval_caches[arm]
                    row = run_target(life, index, cases[index], identities[index], states[arm], arm,
                        laws[index], work[arm], 3456 if index < 30 else SOURCE_COST, paid[arm],
                        query_caches[arm], profiles, profile_ids)
                    model_seconds[arm][life] += row['model_seconds']
                    observation_seconds[arm][life] += row['observation_seconds']
                    paid[arm] += row['spent']
                    stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
                    stream.flush()
                    print(f'life={life} target={index} arm={arm} spent={row["spent"]} '
                        f'query={row["query_certified"]} joint={row["joint_completed"]} '
                        f'life_paid={SOURCE_COST+paid[arm]}', flush=True)
        profile_counts[life] = len(profile_ids)
        final_states.append(dict(life=life, states=deepcopy(states)))
        save(OUTPUT/'final_states.json', final_states)
    save(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen', 'all_decisions_frozen'],
        arm_orders=orders, complete=False))
    results = []
    for life in LIVES:
        _, laws, _, _ = task.world(life)
        with (gzip.open(OUTPUT/f'records_life_{life:02d}.jsonl.gz', 'rt') as source,
              gzip.open(OUTPUT/f'results_life_{life:02d}.jsonl.gz', 'wt') as destination):
            for line in source:
                row = json.loads(line)
                result = evaluate(row, laws[row['index']])
                results.append(result)
                destination.write(json.dumps(exact_json(result), separators=(',', ':'))+'\n')
    summary = summarize(results, model_seconds)
    summary.update(elapsed_seconds=perf_counter()-begun, model_seconds=model_seconds,
        observation_seconds=observation_seconds, source_seconds=source_seconds,
        source_work=source_work, work=work, profiles=profile_counts)
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol,
        phases=['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'],
        arm_orders=orders, complete=True))
    print(json.dumps(exact_json(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
