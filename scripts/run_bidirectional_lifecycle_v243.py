"""Fresh three-arm lifecycle test of returning paid unchanged B rows to A."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from functools import lru_cache
import gzip
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import bidirectional_pool_v243 as core
from acfqp.science import oracle_gap_acquisition_v231 as acquisition
from acfqp.science import scoped_route_task_v228 as task
from acfqp.science import mixture_confidence_v225 as scalar_cs
from acfqp.science import joint_gap_v230 as execution_joint
from acfqp.science import joint_query_evidence_v235 as query_joint
from acfqp.science import convex_query_null_v240 as convex
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_reuse_rebuild_lifecycle_v242 import retain_plan, evaluate, aggregate

OUTPUT = ROOT/'reports/bidirectional_lifecycle_v243'
LIVES, ARMS = (0, 1, 2), ('ONE_WAY', 'TWO_WAY', 'REBUILD')
TARGETS = tuple(range(3, 27))+tuple(range(30, 78))
OPERATORS, ALPHABETS = core.OPERATORS, core.ALPHABETS
SOURCE_BASE, TARGET_BASE = 280000, 281000
TOTAL_BUDGETS, SOURCE_COST = (14144, 17072, 17168), 4608
CAP, BATCH = 384, 16
COMPUTATION_CACHE_SCOPE = dict(query_certificates='per_life_arm', scalar_intervals='per_life_arm',
    execution_normalizer='per_life_arm_maxsize4096',
    query_and_convex_normalizer='shared_within_arm_per_life_maxsize256')


def arm_order(life, position):
    offset = (life+position) % len(ARMS)
    return ARMS[offset:]+ARMS[:offset]


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
        begun = perf_counter()
        result = operation(*args)
        model_seconds += perf_counter()-begun
        return result

    def retained(active):
        nonlocal output_seconds
        begun = perf_counter()
        result = retain_plan(active, profile_stream, profile_ids)
        output_seconds += perf_counter()-begun
        return result

    plan = timed(core.make_plan, member, case, state, identity, index, query_cache, work)
    initial = retained(plan)
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
            plan=retained(plan)))
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
        methods[arm]['planning_seconds'] = sum(timings['planning'][arm].values())
        methods[arm]['initialization_seconds'] = sum(timings['initialization'][arm].values())
        methods[arm]['begin_b_seconds'] = sum(timings['begin_b'][arm].values())
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            life_summaries.append(dict(life=life, arm=arm, source_samples=SOURCE_COST,
                total_samples=SOURCE_COST+sum(row['spent'] for row in subset),
                model_seconds=sum(timings[scope][arm][life]
                    for scope in ('planning', 'initialization', 'begin_b')),
                stages={stage: method_aggregate([row for row in subset if row['stage'] == stage])
                        for stage in task.STAGES}))
    two = methods['TWO_WAY']
    conditions = dict(late_b_quality=two['late_b']['query_certified'] >= 27,
        a_return_quality=two['a_return']['query_certified'] >= 54)
    for control in ('ONE_WAY', 'REBUILD'):
        name = control.lower()
        other = methods[control]
        conditions.update({
            f'matched_{name}_late_b_quality': two['late_b']['query_certified'] >= other['late_b']['query_certified'],
            f'matched_{name}_a_return_quality': two['a_return']['query_certified'] >= other['a_return']['query_certified'],
            f'matched_{name}_joint_quality': two['joint_completed'] >= other['joint_completed'],
            f'actual_acquisition_saving_vs_{name}': two['total_samples'] < other['total_samples']})
    conditions['valid_certificates_and_execution'] = all(method[field] == 0 for method in methods.values()
        for field in ('false_query_certificates', 'false_execution_certificates',
                      'false_impossible_certificates', 'risk_violations', 'executed_risk_violations'))
    paired = []
    for life in LIVES:
        rows = {row['arm']: row for row in life_summaries if row['life'] == life}
        paired.append(dict(life=life,
            one_way_minus_two_way_samples=rows['ONE_WAY']['total_samples']-rows['TWO_WAY']['total_samples'],
            rebuild_minus_two_way_samples=rows['REBUILD']['total_samples']-rows['TWO_WAY']['total_samples'],
            return_one_way_minus_two_way_samples=rows['ONE_WAY']['stages']['A_RETURN']['target_samples']-
                rows['TWO_WAY']['stages']['A_RETURN']['target_samples'],
            return_two_way_minus_one_way_query_certified=rows['TWO_WAY']['stages']['A_RETURN']['query_certified']-
                rows['ONE_WAY']['stages']['A_RETURN']['query_certified'],
            return_two_way_minus_one_way_joint_completed=rows['TWO_WAY']['stages']['A_RETURN']['joint_completed']-
                rows['ONE_WAY']['stages']['A_RETURN']['joint_completed']))
    return dict(complete=True, records=len(records), methods=methods, life_summaries=life_summaries,
        paired=paired, conditions=conditions, stage_condition_met=all(conditions.values()),
        physical_source_samples=SOURCE_COST*len(LIVES), source_samples_charged_per_arm=SOURCE_COST*len(LIVES),
        new_environment_observations=SOURCE_COST*len(LIVES)+sum(row['spent'] for row in records),
        risk_violation_scope='all_retained_plans',
        model_seconds_scope='planning_acquisition_pool_observation_return_merge_and_bank_initialization',
        scientific_gate_changed=False, qualification_only=True)


def prerequisites():
    qualification = json.loads((ROOT/'reports/convex_query_qualification_v241/analysis.json').read_text())
    repair = json.loads((ROOT/'reports/v242_runtime_tmp/binary_interval_repair_verification.json').read_text())
    if not qualification['valid'] or not qualification['stage_condition_met'] or not repair['valid']:
        raise ValueError('V241 qualification and V242 interval repair verification must permit the new lifecycle')
    return dict(v241_qualification_valid=True, v241_stage_condition_met=True,
        v242_interval_repair_valid=True, v242_cohort_valid_required=False)


def capture():
    from scripts import audit_bidirectional_lifecycle_v243
    paths = set(('scripts/run_bidirectional_lifecycle_v243.py',
        'scripts/audit_bidirectional_lifecycle_v243.py', 'src/acfqp/science/bidirectional_pool_v243.py',
        'tests/test_bidirectional_pool_v243.py', 'tests/test_bidirectional_lifecycle_v243_runner.py',
        'tests/test_bidirectional_normalizer_caches_v243.py',
        'tests/test_bidirectional_lifecycle_v243_audit.py', 'tests/test_mixture_confidence_outward_v242.py',
        'specs/BIDIRECTIONAL_LIFECYCLE_V243.md'))
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
        computation_cache_scope=COMPUTATION_CACHE_SCOPE,
        oracle_information=['type identity', 'B changed operator', 'B-to-A correspondence'])
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen'], complete=False))
    started = perf_counter()
    capture()
    output_seconds += perf_counter()-started
    source_records, source_evidence, cases_saved, interfaces, final_states, orders = [], [], [], [], [], []
    work, source_work = {arm: Counter() for arm in ARMS}, Counter()
    timings = {scope: {arm: dict.fromkeys(LIVES, 0.) for arm in ARMS}
               for scope in ('planning', 'initialization', 'begin_b', 'observation')}
    source_seconds, profile_counts, normalizer_statistics = {}, {}, {arm: {} for arm in ARMS}
    for life in LIVES:
        cases, laws, identities, metadata = task.world(life)
        cases_saved.append(dict(life=life, cases=cases))
        interfaces.append(dict(life=life, identities=identities, metadata=metadata))
        output(OUTPUT/'cases.json', cases_saved)
        output(OUTPUT/'interfaces.json', interfaces)
        a_anchors, source_seconds[life] = sources(life, 'A', laws, source_records, source_work)
        output(OUTPUT/'source_records.json', source_records)
        states = {}
        for arm in ARMS:
            started = perf_counter()
            states[arm] = core.prepare(a_anchors, life, arm, work[arm])
            timings['initialization'][arm][life] += perf_counter()-started
        query_caches, interval_caches = {arm: {} for arm in ARMS}, {arm: {} for arm in ARMS}
        normalizers = normalizer_caches()
        paid, profile_ids = dict.fromkeys(ARMS, 0), {}
        with (gzip.open(OUTPUT/f'records_life_{life:02d}.jsonl.gz', 'wt') as stream,
              gzip.open(OUTPUT/f'profiles_life_{life:02d}.jsonl.gz', 'wt') as profiles):
            for position, index in enumerate(TARGETS):
                if index == 30:
                    b_anchors, seconds = sources(life, 'B', laws, source_records, source_work)
                    source_seconds[life] += seconds
                    source_evidence.append(dict(life=life, a=a_anchors, b=b_anchors))
                    output(OUTPUT/'source_records.json', source_records)
                    output(OUTPUT/'source_evidence.json', source_evidence)
                    for arm in ARMS:
                        started = perf_counter()
                        core.begin_b(states[arm], b_anchors, metadata['changed_operator'], metadata['b_to_a'], work[arm])
                        timings['begin_b'][arm][life] += perf_counter()-started
                order = arm_order(life, position)
                orders.append(dict(life=life, index=index, order=order))
                for arm in order:
                    activate_arm_caches(arm, interval_caches, normalizers)
                    row = run_target(life, index, cases[index], identities[index], states[arm], arm,
                        laws[index], work[arm], 3456 if index < 30 else SOURCE_COST, paid[arm],
                        query_caches[arm], profiles, profile_ids)
                    timings['planning'][arm][life] += row['model_seconds']
                    timings['observation'][arm][life] += row['observation_seconds']
                    output_seconds += row['output_seconds']
                    paid[arm] += row['spent']
                    started = perf_counter()
                    stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
                    stream.flush()
                    output_seconds += perf_counter()-started
                    print(f'life={life} target={index} arm={arm} spent={row["spent"]} '
                        f'query={row["query_certified"]} joint={row["joint_completed"]} '
                        f'life_paid={SOURCE_COST+paid[arm]}', flush=True)
        profile_counts[life] = len(profile_ids)
        for arm in ARMS:
            normalizer_statistics[arm][life] = {name: function.cache_info()._asdict()
                for name, function in normalizers[arm].items()}
        final_states.append(dict(life=life, states=deepcopy(states)))
        output(OUTPUT/'final_states.json', final_states)
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen', 'all_decisions_frozen'],
        arm_orders=orders, complete=False))
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
        scoring_seconds=scoring_seconds, output_seconds=output_seconds,
        output_seconds_scope='captured_sources_and_json_writes_and_proof_retention_before_final_summary',
        computation_cache_scope=COMPUTATION_CACHE_SCOPE, normalizer_cache_statistics=normalizer_statistics,
        source_seconds=source_seconds, source_work=source_work, work=work, profiles=profile_counts,
        return_transfers=[dict(life=row['life'], arm=arm, ledger=state['return_merge'])
            for row in final_states for arm, state in row['states'].items()])
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol,
        phases=['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'],
        arm_orders=orders, complete=True))
    print(json.dumps(exact_json(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
