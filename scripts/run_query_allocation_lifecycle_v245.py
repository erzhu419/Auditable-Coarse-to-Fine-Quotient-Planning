"""Fresh lifecycle comparison changing only query-directed acquisition.

Each of the three independent lives runs in its own process. All 648 decisions
are retained before the parent computes any posthoc truth-based score.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from fractions import Fraction as F
from functools import lru_cache
import gzip
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter, process_time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import bidirectional_pool_v243 as core
from acfqp.science import oracle_gap_acquisition_v231 as acquisition
from acfqp.science import query_directed_acquisition_v245 as query_acquisition
from acfqp.science import scoped_route_task_v228 as task
from acfqp.science import mixture_confidence_v225 as scalar_cs
from acfqp.science import joint_gap_v230 as execution_joint
from acfqp.science import joint_query_evidence_v235 as query_joint
from acfqp.science import convex_query_null_v240 as convex
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_reuse_rebuild_lifecycle_v242 import retain_plan, evaluate, aggregate

OUTPUT = ROOT/'reports/query_allocation_lifecycle_v245'
LIVES, ARMS = (0, 1, 2), ('ONE_WAY', 'QUERY_DIRECTED', 'REBUILD')
TARGETS = tuple(range(3, 27))+tuple(range(30, 78))
OPERATORS, ALPHABETS = core.OPERATORS, core.ALPHABETS
SOURCE_BASE, TARGET_BASE = 282000, 283000
TOTAL_BUDGETS, SOURCE_COST = (14144, 17072, 17168), 4608
CAP, BATCH = 384, 16
CORE_ARMS = dict(ONE_WAY='ONE_WAY', QUERY_DIRECTED='ONE_WAY', REBUILD='REBUILD')
COMPUTATION_CACHE_SCOPE = dict(query_certificates='per_life_arm', scalar_intervals='per_life_arm',
    execution_normalizer='per_life_arm_maxsize4096',
    query_and_convex_normalizer='shared_within_arm_per_life_maxsize256')


def arm_order(life, position):
    offset = (life+position) % len(ARMS)
    return ARMS[offset:]+ARMS[:offset]


def prepare_state(anchors, life, arm, work):
    return core.prepare(anchors, life, CORE_ARMS[arm], work)


def choose(arm, member, plan, spent, work):
    allocator = query_acquisition if arm == 'QUERY_DIRECTED' else acquisition
    return allocator.choose(member, plan, spent, work)


def normalizer_caches():
    return {arm: dict(
        execution=lru_cache(maxsize=4096)(execution_joint.mixture_normalizer.__wrapped__),
        query=lru_cache(maxsize=256)(query_joint.mixture_normalizer.__wrapped__)) for arm in ARMS}


def activate_arm_caches(arm, intervals, normalizers):
    scalar_cs._INTERVAL_CACHE = intervals[arm]
    execution_joint.mixture_normalizer = normalizers[arm]['execution']
    query_joint.mixture_normalizer = normalizers[arm]['query']
    convex.mixture_normalizer = normalizers[arm]['query']


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
    member, spent, model_seconds, observation_seconds, output_seconds = core.empty(), 0, 0., 0., 0.
    bank = 'a' if case['context'] == 'A' else 'b'
    before = deepcopy(state[bank]['pools'][identity])
    available = TOTAL_BUDGETS[life]-SOURCE_COST-history_paid_samples

    def timed(operation, *args):
        nonlocal model_seconds
        begun = process_time()
        result = operation(*args)
        model_seconds += process_time()-begun
        return result

    def retained(active):
        nonlocal output_seconds
        begun = perf_counter()
        result = retain_plan(active, profile_stream, profile_ids)
        output_seconds += perf_counter()-begun
        return result

    plan = timed(core.make_plan, member, case, state, identity, index, query_cache, work)
    initial, batches = retained(plan), []
    while spent+BATCH <= min(CAP, available) and not core.ready(plan):
        choice = timed(choose, arm, member, plan, spent, work)
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
            draw_end=progress['draw_end'], increments=increments, spent=spent, plan=retained(plan)))
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
        model_seconds=model_seconds, observation_seconds=observation_seconds, output_seconds=output_seconds,
        execution_certified=plan['utility_lower'] >= 2, goal_impossible=plan['goal_impossible'],
        query_certified=plan['query_ready'], joint_completed=completed, fallback=not completed,
        executed_mix=deepcopy(plan['mix']) if completed else [('WAIT', F(1))])


def method_aggregate(rows):
    result = aggregate(rows)
    result['executed_risk_violations'] = sum(row['executed']['violation'] for row in rows)
    return result


def summarize(records, timings):
    methods, life_summaries = {}, []
    for arm in ARMS:
        selected = [row for row in records if row['arm'] == arm]
        methods[arm] = dict(method_aggregate(selected), source_samples=SOURCE_COST*len(LIVES),
            total_samples=SOURCE_COST*len(LIVES)+sum(row['spent'] for row in selected),
            late_b=method_aggregate([row for row in selected if 42 <= row['index'] < 54]),
            a_return=method_aggregate([row for row in selected if row['stage'] == 'A_RETURN']))
        methods[arm]['model_seconds'] = sum(
            timings[scope][arm][life] for scope in ('planning', 'initialization', 'begin_b') for life in LIVES)
        for scope in ('planning', 'initialization', 'begin_b'):
            methods[arm][scope+'_seconds'] = sum(timings[scope][arm].values())
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            life_summaries.append(dict(life=life, arm=arm, source_samples=SOURCE_COST,
                total_samples=SOURCE_COST+sum(row['spent'] for row in subset),
                model_seconds=sum(timings[scope][arm][life]
                    for scope in ('planning', 'initialization', 'begin_b')),
                stages={stage: method_aggregate([row for row in subset if row['stage'] == stage])
                        for stage in task.STAGES}))
    directed = methods['QUERY_DIRECTED']
    conditions = dict(late_b_quality=directed['late_b']['query_certified'] >= 27,
        a_return_quality=directed['a_return']['query_certified'] >= 54)
    for control in ('ONE_WAY', 'REBUILD'):
        name, other = control.lower(), methods[control]
        conditions.update({
            f'matched_{name}_late_b_quality': directed['late_b']['query_certified'] >= other['late_b']['query_certified'],
            f'matched_{name}_a_return_quality': directed['a_return']['query_certified'] >= other['a_return']['query_certified'],
            f'matched_{name}_joint_quality': directed['joint_completed'] >= other['joint_completed']})
    conditions['actual_acquisition_saving_vs_rebuild'] = directed['total_samples'] < methods['REBUILD']['total_samples']
    conditions['actual_acquisition_nondegrading_vs_one_way'] = directed['total_samples'] <= methods['ONE_WAY']['total_samples']
    conditions['valid_certificates_and_execution'] = all(method[field] == 0 for method in methods.values()
        for field in ('false_query_certificates', 'false_execution_certificates',
            'false_impossible_certificates', 'false_goal_uppers', 'risk_violations', 'executed_risk_violations'))
    paired = []
    for life in LIVES:
        rows = {row['arm']: row for row in life_summaries if row['life'] == life}
        paired.append(dict(life=life,
            one_way_minus_query_directed_samples=rows['ONE_WAY']['total_samples']-rows['QUERY_DIRECTED']['total_samples'],
            rebuild_minus_query_directed_samples=rows['REBUILD']['total_samples']-rows['QUERY_DIRECTED']['total_samples'],
            return_one_way_minus_query_directed_samples=rows['ONE_WAY']['stages']['A_RETURN']['target_samples']-
                rows['QUERY_DIRECTED']['stages']['A_RETURN']['target_samples'],
            return_query_directed_minus_one_way_query_certified=rows['QUERY_DIRECTED']['stages']['A_RETURN']['query_certified']-
                rows['ONE_WAY']['stages']['A_RETURN']['query_certified'],
            return_query_directed_minus_one_way_joint_completed=rows['QUERY_DIRECTED']['stages']['A_RETURN']['joint_completed']-
                rows['ONE_WAY']['stages']['A_RETURN']['joint_completed']))
    return dict(complete=True, records=len(records), methods=methods, life_summaries=life_summaries,
        paired=paired, conditions=conditions, stage_condition_met=all(conditions.values()),
        physical_source_samples=SOURCE_COST*len(LIVES), source_samples_charged_per_arm=SOURCE_COST*len(LIVES),
        new_environment_observations=SOURCE_COST*len(LIVES)+sum(row['spent'] for row in records),
        risk_violation_scope='all_retained_plans',
        model_seconds_scope='summed_process_CPU_planning_acquisition_pool_observation_and_bank_initialization',
        scientific_gate_changed=False, qualification_only=True)


def prerequisites():
    admitted = {}
    for version, directory in ((243, 'bidirectional_lifecycle_v243'), (244, 'goal_joint_region_v244')):
        run = json.loads((ROOT/'reports'/directory/'run.json').read_text())
        analysis = json.loads((ROOT/'reports'/directory/'analysis.json').read_text())
        if not run['complete'] or not analysis['valid']:
            raise ValueError(f'V{version} must be complete and independently valid')
        admitted.update({f'v{version}_complete': True, f'v{version}_independent_valid': True})
    return admitted


def capture():
    from scripts import audit_query_allocation_lifecycle_v245
    paths = set(('scripts/run_query_allocation_lifecycle_v245.py',
        'scripts/audit_query_allocation_lifecycle_v245.py', 'src/acfqp/science/query_directed_acquisition_v245.py',
        'tests/test_query_directed_acquisition_v245.py', 'tests/test_query_allocation_lifecycle_v245_runner.py',
        'tests/test_query_allocation_lifecycle_v245_audit.py', 'specs/QUERY_ALLOCATION_LIFECYCLE_V245.md'))
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


def run_life(life):
    """Write one chronological life without evaluating any retained decision."""
    life_begun = perf_counter()
    cases, laws, identities, metadata = task.world(life)
    source_records, source_work = [], Counter()
    a_anchors, source_seconds = sources(life, 'A', laws, source_records, source_work)
    work, states = {arm: Counter() for arm in ARMS}, {}
    timings = {scope: dict.fromkeys(ARMS, 0.) for scope in ('planning', 'initialization', 'begin_b', 'observation')}
    for arm in ARMS:
        started = process_time()
        states[arm] = prepare_state(a_anchors, life, arm, work[arm])
        timings['initialization'][arm] += process_time()-started
    query_caches, interval_caches = {arm: {} for arm in ARMS}, {arm: {} for arm in ARMS}
    normalizers = normalizer_caches()
    paid, profile_ids, orders, output_seconds = dict.fromkeys(ARMS, 0), {}, [], 0.
    with (gzip.open(OUTPUT/f'records_life_{life:02d}.jsonl.gz', 'wt') as stream,
          gzip.open(OUTPUT/f'profiles_life_{life:02d}.jsonl.gz', 'wt') as profiles):
        for position, index in enumerate(TARGETS):
            if index == 30:
                b_anchors, seconds = sources(life, 'B', laws, source_records, source_work)
                source_seconds += seconds
                for arm in ARMS:
                    started = process_time()
                    core.begin_b(states[arm], b_anchors, metadata['changed_operator'], metadata['b_to_a'], work[arm])
                    timings['begin_b'][arm] += process_time()-started
            order = arm_order(life, position)
            orders.append(dict(life=life, index=index, order=order))
            for arm in order:
                activate_arm_caches(arm, interval_caches, normalizers)
                row = run_target(life, index, cases[index], identities[index], states[arm], arm,
                    laws[index], work[arm], 3456 if index < 30 else SOURCE_COST, paid[arm],
                    query_caches[arm], profiles, profile_ids)
                timings['planning'][arm] += row['model_seconds']
                timings['observation'][arm] += row['observation_seconds']
                output_seconds += row['output_seconds']
                paid[arm] += row['spent']
                started = perf_counter()
                stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
                stream.flush()
                output_seconds += perf_counter()-started
                print(f'life={life} target={index} arm={arm} spent={row["spent"]} '
                    f'query={row["query_certified"]} joint={row["joint_completed"]} '
                    f'life_paid={SOURCE_COST+paid[arm]}', flush=True)
    artifact = dict(life=life, source_records=source_records,
        source_evidence=dict(life=life, a=a_anchors, b=b_anchors),
        cases=dict(life=life, cases=cases), interfaces=dict(life=life, identities=identities, metadata=metadata),
        final_states=dict(life=life, states=deepcopy(states)), arm_orders=orders, timings=timings,
        work=work, source_work=source_work, source_seconds=source_seconds, profiles=len(profile_ids),
        normalizer_cache_statistics={arm: {name: function.cache_info()._asdict()
            for name, function in normalizers[arm].items()} for arm in ARMS})
    artifact['life_wall_seconds'] = perf_counter()-life_begun
    started = perf_counter()
    save(OUTPUT/f'life_artifacts_{life:02d}.json', artifact)
    output_seconds += perf_counter()-started
    return dict(artifact, output_seconds=output_seconds)


def run():
    begun, admitted = perf_counter(), prerequisites()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    output_seconds = 0.

    def output(path, value):
        nonlocal output_seconds
        started = perf_counter()
        save(path, value)
        output_seconds += perf_counter()-started

    protocol = dict(lives=LIVES, arms=ARMS, targets_per_life=72, cap=CAP, batch=BATCH,
        source_seed_base=SOURCE_BASE, target_seed_base=TARGET_BASE, per_life_total_budgets=TOTAL_BUDGETS,
        source_samples_per_life=SOURCE_COST, query_stream_count=48, query_threshold=960,
        query_delta_per_life_arm='1/20', execution_delta_per_life_arm='1/20', combined_delta_upper='1/10',
        scientific_gate_changed=False, qualification_only=True, prerequisites=admitted,
        computation_cache_scope=COMPUTATION_CACHE_SCOPE, pool_core_arm_mapping=CORE_ARMS,
        execution=dict(independent_life_processes=3, posthoc_scoring='after_all_648_decisions_frozen'),
        model_seconds_clock='process_time', observation_output_scoring_seconds_clock='perf_counter',
        oracle_information=['type identity', 'B changed operator', 'B-to-A correspondence'])
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen'], complete=False))
    started = perf_counter()
    capture()
    output_seconds += perf_counter()-started
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {life: executor.submit(run_life, life) for life in LIVES}
        artifacts = [futures[life].result() for life in LIVES]
    # Every future has completed; no worker or unfinished decision reaches scoring.
    for key in ('source_records', 'source_evidence', 'cases', 'interfaces', 'final_states'):
        values = ([row for item in artifacts for row in item[key]] if key == 'source_records'
                  else [item[key] for item in artifacts])
        output(OUTPUT/(key+'.json'), values)
    orders = [order for item in artifacts for order in item['arm_orders']]
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen', 'all_decisions_frozen'],
        arm_orders=orders, complete=False))
    timings = {scope: {arm: {item['life']: item['timings'][scope][arm] for item in artifacts} for arm in ARMS}
               for scope in ('planning', 'initialization', 'begin_b', 'observation')}
    output_seconds += sum(item['output_seconds'] for item in artifacts)
    results, scoring_seconds = [], 0.
    for life in LIVES:
        _, laws, _, _ = task.world(life)
        with (gzip.open(OUTPUT/f'records_life_{life:02d}.jsonl.gz', 'rt') as source,
              gzip.open(OUTPUT/f'results_life_{life:02d}.jsonl.gz', 'wt') as destination):
            for line in source:
                row = json.loads(line)
                started = perf_counter()
                result = evaluate(row, laws[row['index']])
                scoring_seconds += perf_counter()-started
                results.append(result)
                started = perf_counter()
                destination.write(json.dumps(exact_json(result), separators=(',', ':'))+'\n')
                output_seconds += perf_counter()-started
    summary = summarize(results, timings)
    summary.update(elapsed_seconds=perf_counter()-begun, timings=timings,
        life_wall_seconds={item['life']: item['life_wall_seconds'] for item in artifacts},
        life_wall_seconds_scope='worker_entry_through_all_decisions_retained_before_artifact_write',
        scoring_seconds=scoring_seconds, output_seconds=output_seconds,
        output_seconds_scope='summed_parent_and_worker_write_and_retention_wall_calls_before_final_summary',
        computation_cache_scope=COMPUTATION_CACHE_SCOPE,
        normalizer_cache_statistics={arm: {item['life']: item['normalizer_cache_statistics'][arm]
            for item in artifacts} for arm in ARMS},
        source_seconds={item['life']: item['source_seconds'] for item in artifacts},
        source_work=sum((Counter(item['source_work']) for item in artifacts), Counter()),
        work={arm: sum((Counter(item['work'][arm]) for item in artifacts), Counter()) for arm in ARMS},
        profiles={item['life']: item['profiles'] for item in artifacts},
        return_transfers=[dict(life=item['life'], arm=arm, ledger=state['return_merge'])
            for item in artifacts for arm, state in item['final_states']['states'].items()])
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol,
        phases=['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'],
        arm_orders=orders, complete=True))
    print(json.dumps(exact_json(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
