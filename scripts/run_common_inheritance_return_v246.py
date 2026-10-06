"""Fresh paired A_RETURN suffixes from one paid V245 ONE_WAY A+B prefix."""
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
from acfqp.science import common_inheritance_v246 as inheritance
from acfqp.science import oracle_gap_acquisition_v231 as acquisition
from acfqp.science import query_directed_acquisition_v245 as query_acquisition
from acfqp.science import scoped_route_task_v228 as task
from acfqp.science import mixture_confidence_v225 as scalar_cs
from acfqp.science import joint_gap_v230 as execution_joint
from acfqp.science import joint_query_evidence_v235 as query_joint
from acfqp.science import convex_query_null_v240 as convex
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_reuse_rebuild_lifecycle_v242 import retain_plan, evaluate, aggregate

OUTPUT = ROOT/'reports/common_inheritance_return_v246'
PREFIX_DIRECTORY = ROOT/'reports/query_allocation_lifecycle_v245'
LIVES, ARMS, TARGETS = (0, 1, 2), ('ONE_WAY', 'RETURN_DIRECTED'), tuple(range(54, 78))
OPERATORS, ALPHABETS = core.OPERATORS, core.ALPHABETS
TARGET_BASE, TOTAL_BUDGETS, SOURCE_COST = 285000, (14144, 17072, 17168), 4608
HISTORY_PAID = (6768, 9216, 7952)
CAP, BATCH = 384, 16
COMPUTATION_CACHE_SCOPE = dict(query_certificates='per_life_arm', scalar_intervals='per_life_arm',
    execution_normalizer='per_life_arm_maxsize4096',
    query_and_convex_normalizer='shared_within_arm_per_life_maxsize256')


def arm_order(life, position):
    offset = (life+position) % len(ARMS)
    return ARMS[offset:]+ARMS[:offset]


def choose(arm, member, plan, spent, work):
    allocator = query_acquisition if arm == 'RETURN_DIRECTED' else acquisition
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


def run_target(life, index, case, identity, state, arm, law, work,
               source_paid_samples, history_paid_samples, query_cache, profile_stream, profile_ids):
    seeds = {op: TARGET_BASE+(life*78+index)*3+j for j, op in enumerate(OPERATORS)}
    generators = {op: random.Random(seed) for op, seed in seeds.items()}
    member, spent, model_seconds, observation_seconds, output_seconds = core.empty(), 0, 0., 0., 0.
    before = deepcopy(state['a']['pools'][identity])
    available = TOTAL_BUDGETS[life]-source_paid_samples-history_paid_samples

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
        pooled_before=before, pooled_after=deepcopy(state['a']['pools'][identity]),
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
            inherited_target_samples=sum(HISTORY_PAID),
            total_samples=SOURCE_COST*len(LIVES)+sum(HISTORY_PAID)+sum(row['spent'] for row in selected))
        for scope in ('planning', 'initialization'):
            methods[arm][scope+'_seconds'] = sum(timings[scope][arm].values())
        methods[arm]['model_seconds'] = sum(timings[scope][arm][life]
            for scope in ('planning', 'initialization') for life in LIVES)
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            life_summaries.append(dict(life=life, arm=arm, source_samples=SOURCE_COST,
                inherited_target_samples=HISTORY_PAID[life],
                total_samples=SOURCE_COST+HISTORY_PAID[life]+sum(row['spent'] for row in subset),
                model_seconds=sum(timings[scope][arm][life] for scope in ('planning', 'initialization')),
                a_return=method_aggregate(subset)))
    directed, control = methods['RETURN_DIRECTED'], methods['ONE_WAY']
    conditions = dict(a_return_quality=directed['query_certified'] >= 54,
        matched_one_way_query_quality=directed['query_certified'] >= control['query_certified'],
        matched_one_way_joint_quality=directed['joint_completed'] >= control['joint_completed'],
        actual_acquisition_nondegrading_vs_one_way=directed['total_samples'] <= control['total_samples'],
        valid_certificates_and_execution=all(method[field] == 0 for method in methods.values()
            for field in ('false_query_certificates', 'false_execution_certificates',
                'false_impossible_certificates', 'false_goal_uppers', 'risk_violations', 'executed_risk_violations')))
    paired = []
    for life in LIVES:
        rows = {row['arm']: row for row in life_summaries if row['life'] == life}
        paired.append(dict(life=life,
            one_way_minus_return_directed_samples=rows['ONE_WAY']['total_samples']-rows['RETURN_DIRECTED']['total_samples'],
            return_directed_minus_one_way_query_certified=rows['RETURN_DIRECTED']['a_return']['query_certified']-
                rows['ONE_WAY']['a_return']['query_certified'],
            return_directed_minus_one_way_joint_completed=rows['RETURN_DIRECTED']['a_return']['joint_completed']-
                rows['ONE_WAY']['a_return']['joint_completed']))
    return dict(complete=True, records=len(records), methods=methods, life_summaries=life_summaries,
        paired=paired, conditions=conditions, stage_condition_met=all(conditions.values()),
        physical_source_samples=0, inherited_source_samples_charged_per_arm=SOURCE_COST*len(LIVES),
        inherited_target_samples_charged_per_arm=sum(HISTORY_PAID),
        new_environment_observations=sum(row['spent'] for row in records),
        risk_violation_scope='all_retained_return_plans',
        model_seconds_scope='summed_process_CPU_planning_acquisition_pool_observation_and_state_copy',
        scientific_gate_changed=False, qualification_only=True, suffix_only=True)


def prerequisites():
    run = json.loads((PREFIX_DIRECTORY/'run.json').read_text())
    analysis = json.loads((PREFIX_DIRECTORY/'analysis.json').read_text())
    if not run['complete'] or not analysis['valid']:
        raise ValueError('V245 must be complete and independently valid')
    return dict(v245_complete=True, v245_independent_valid=True)


def capture():
    from scripts import audit_common_inheritance_return_v246
    paths = set(('scripts/run_common_inheritance_return_v246.py',
        'scripts/audit_common_inheritance_return_v246.py', 'src/acfqp/science/common_inheritance_v246.py',
        'tests/test_common_inheritance_v246.py', 'tests/test_common_inheritance_return_v246_runner.py',
        'tests/test_common_inheritance_return_v246_audit.py', 'specs/COMMON_INHERITANCE_RETURN_V246.md'))
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
    life_begun, prefix_read_begun = perf_counter(), perf_counter()
    prefix = inheritance.load_prefix(PREFIX_DIRECTORY, life)
    cases_saved = next(row for row in json.loads((PREFIX_DIRECTORY/'cases.json').read_text()) if row['life'] == life)
    interface = next(row for row in json.loads((PREFIX_DIRECTORY/'interfaces.json').read_text()) if row['life'] == life)
    prefix_read_seconds = perf_counter()-prefix_read_begun
    replay_work = Counter()
    begun = process_time()
    common_state, ledger = inheritance.replay_prefix(prefix, replay_work)
    prefix_replay_seconds = process_time()-begun
    if ledger['source_paid_samples'] != SOURCE_COST or ledger['history_paid_samples'] != HISTORY_PAID[life]:
        raise ValueError('the retained prefix must match the frozen paid fees')
    states, work = {}, {arm: Counter() for arm in ARMS}
    timings = {scope: dict.fromkeys(ARMS, 0.) for scope in ('planning', 'initialization', 'observation')}
    for arm in ARMS:
        begun = process_time()
        states[arm] = deepcopy(common_state)
        timings['initialization'][arm] += process_time()-begun
    cases, identities = cases_saved['cases'], interface['identities']
    _, laws, _, _ = task.world(life)
    query_caches, interval_caches = {arm: {} for arm in ARMS}, {arm: {} for arm in ARMS}
    normalizers = normalizer_caches()
    paid, profile_ids, orders, output_seconds = dict.fromkeys(ARMS, 0), {}, [], 0.
    with (gzip.open(OUTPUT/f'records_life_{life:02d}.jsonl.gz', 'wt') as stream,
          gzip.open(OUTPUT/f'profiles_life_{life:02d}.jsonl.gz', 'wt') as profiles):
        for position, index in enumerate(TARGETS):
            order = arm_order(life, position)
            orders.append(dict(life=life, index=index, order=order))
            for arm in order:
                activate_arm_caches(arm, interval_caches, normalizers)
                row = run_target(life, index, cases[index], identities[index], states[arm], arm,
                    laws[index], work[arm], SOURCE_COST, ledger['history_paid_samples']+paid[arm],
                    query_caches[arm], profiles, profile_ids)
                timings['planning'][arm] += row['model_seconds']
                timings['observation'][arm] += row['observation_seconds']
                output_seconds += row['output_seconds']
                paid[arm] += row['spent']
                begun = perf_counter()
                stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
                stream.flush()
                output_seconds += perf_counter()-begun
                print(f'life={life} target={index} arm={arm} spent={row["spent"]} '
                    f'query={row["query_certified"]} joint={row["joint_completed"]} '
                    f'whole_paid={SOURCE_COST+ledger["history_paid_samples"]+paid[arm]}', flush=True)
    artifact = dict(life=life, cases=cases_saved, interfaces=interface, prefix_ledger=ledger,
        common_prefix_state=dict(life=life, history_paid_samples=ledger['history_paid_samples'], state=common_state),
        final_states=dict(life=life, states=deepcopy(states)), arm_orders=orders, timings=timings,
        work=work, prefix_replay_work=replay_work, prefix_replay_seconds=prefix_replay_seconds,
        prefix_read_seconds=prefix_read_seconds, profiles=len(profile_ids),
        normalizer_cache_statistics={arm: {name: function.cache_info()._asdict()
            for name, function in normalizers[arm].items()} for arm in ARMS})
    artifact['life_wall_seconds'] = perf_counter()-life_begun
    begun = perf_counter()
    save(OUTPUT/f'life_artifacts_{life:02d}.json', artifact)
    output_seconds += perf_counter()-begun
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

    protocol = dict(lives=LIVES, arms=ARMS, targets_per_life=24, cap=CAP, batch=BATCH,
        target_seed_base=TARGET_BASE, per_life_total_budgets=TOTAL_BUDGETS,
        inherited_source_samples_per_life=SOURCE_COST, inherited_target_samples_per_life=HISTORY_PAID,
        initial_return_available_samples=[TOTAL_BUDGETS[life]-SOURCE_COST-HISTORY_PAID[life] for life in LIVES],
        prefix_directory=PREFIX_DIRECTORY.relative_to(ROOT).as_posix(), prefix_arm='ONE_WAY',
        prefix_stages=['A', 'B'], new_source_observations=0, query_stream_count=48, query_threshold=960,
        query_delta_per_life_arm='1/20', execution_delta_per_life_arm='1/20', combined_delta_upper='1/10',
        scientific_gate_changed=False, qualification_only=True, suffix_only=True, prerequisites=admitted,
        computation_cache_scope=COMPUTATION_CACHE_SCOPE,
        execution=dict(independent_life_processes=3, posthoc_scoring='after_all_144_decisions_frozen'),
        model_seconds_clock='process_time', prefix_replay_seconds_clock='process_time',
        observation_output_scoring_seconds_clock='perf_counter',
        oracle_information=['type identity', 'B changed operator', 'B-to-A correspondence'])
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen'], complete=False))
    started = perf_counter()
    capture()
    output_seconds += perf_counter()-started
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {life: executor.submit(run_life, life) for life in LIVES}
        artifacts = [futures[life].result() for life in LIVES]
    for key, filename in (('cases', 'cases.json'), ('interfaces', 'interfaces.json'),
            ('prefix_ledger', 'prefix_ledgers.json'), ('common_prefix_state', 'common_prefix_states.json'),
            ('final_states', 'final_states.json')):
        output(OUTPUT/filename, [item[key] for item in artifacts])
    orders = [order for item in artifacts for order in item['arm_orders']]
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen', 'all_decisions_frozen'],
        arm_orders=orders, complete=False))
    timings = {scope: {arm: {item['life']: item['timings'][scope][arm] for item in artifacts} for arm in ARMS}
               for scope in ('planning', 'initialization', 'observation')}
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
        common_prefix_replay_CPU_seconds={item['life']: item['prefix_replay_seconds'] for item in artifacts},
        common_prefix_replay_CPU_seconds_scope='one_common_prefix_replay_per_life_separate_from_both_arm_model_times',
        prefix_read_seconds={item['life']: item['prefix_read_seconds'] for item in artifacts},
        scoring_seconds=scoring_seconds, output_seconds=output_seconds,
        output_seconds_scope='summed_parent_and_worker_write_and_retention_wall_calls_before_final_summary',
        computation_cache_scope=COMPUTATION_CACHE_SCOPE,
        normalizer_cache_statistics={arm: {item['life']: item['normalizer_cache_statistics'][arm]
            for item in artifacts} for arm in ARMS},
        prefix_replay_work=sum((Counter(item['prefix_replay_work']) for item in artifacts), Counter()),
        work={arm: sum((Counter(item['work'][arm]) for item in artifacts), Counter()) for arm in ARMS},
        profiles={item['life']: item['profiles'] for item in artifacts})
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol,
        phases=['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'],
        arm_orders=orders, complete=True))
    print(json.dumps(exact_json(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
