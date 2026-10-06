"""Fresh lifecycle experiment fixing S/D probe quantity and changing its timing.

Nine isolated life/arm processes retain all decisions before posthoc scoring.
Shared probes update only native A pools and never revise a retained decision.
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
from acfqp.science import scoped_route_task_v228 as task
from acfqp.science import mixture_confidence_v225 as scalar_cs
from acfqp.science import joint_gap_v230 as execution_joint
from acfqp.science import joint_query_evidence_v235 as query_joint
from acfqp.science import convex_query_null_v240 as convex
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_reuse_rebuild_lifecycle_v242 import retain_plan, evaluate, aggregate

OUTPUT = ROOT/'reports/shared_probe_timing_v249'
LIVES, ARMS = (0, 1, 2), ('BEFORE_SHARED', 'DEFERRED_SHARED', 'REBUILD')
TARGETS = tuple(range(3, 27))+tuple(range(30, 78))
OPERATORS, ALPHABETS = core.OPERATORS, core.ALPHABETS
SOURCE_BASE, TARGET_BASE, PROBE_BASE = 288000, 289000, 290000
TOTAL_BUDGETS, SOURCE_COST = (14144, 17072, 17168), 4608
CAP, BATCH = 384, 16
PROBE_OPERATORS, PROBE_AMOUNT = OPERATORS[:2], CAP//3
PROBE_QUOTA = 3*len(PROBE_OPERATORS)*PROBE_AMOUNT
CORE_ARMS = dict(BEFORE_SHARED='ONE_WAY', DEFERRED_SHARED='ONE_WAY', REBUILD='REBUILD')
TIMING_SCOPES = ('planning', 'initialization', 'begin_b', 'probe_pool_updates',
                 'acquisition', 'observation', 'probe_draw')
MODEL_SCOPES = ('planning', 'initialization', 'begin_b', 'probe_pool_updates')
COMPUTATION_CACHE_SCOPE = dict(query_certificates='per_life_arm', scalar_intervals='per_life_arm',
    execution_normalizer='per_life_arm_maxsize4096',
    query_and_convex_normalizer='shared_within_arm_per_life_maxsize256')


def probe_quota(arm):
    return 0 if arm == 'REBUILD' else PROBE_QUOTA


def worker_filename(kind, life, arm):
    ending = '.jsonl' if kind == 'probes' else '.jsonl.gz'
    return OUTPUT/f'{kind}_life_{life:02d}_{arm}{ending}'


def activate_cold_caches():
    """Each process owns one arm; query/interval/normalizer caches start cold."""
    scalar_cs._INTERVAL_CACHE = {}
    normalizers = dict(
        execution=lru_cache(maxsize=4096)(execution_joint.mixture_normalizer.__wrapped__),
        query=lru_cache(maxsize=256)(query_joint.mixture_normalizer.__wrapped__))
    execution_joint.mixture_normalizer = normalizers['execution']
    query_joint.mixture_normalizer = normalizers['query']
    convex.mixture_normalizer = normalizers['query']
    return normalizers


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
                    operator=operator, seed=seed, draw_start=start,
                    draw_end=progress['draw_end'], increments=increments))
        anchors.append(anchor)
    return anchors, seconds


def run_target(life, index, case, identity, state, arm, law, work,
               source_paid_samples, history_paid_samples, actual_probe_paid_before,
               query_cache, profile_stream, profile_ids):
    seeds = {op: TARGET_BASE+(life*78+index)*3+j for j, op in enumerate(OPERATORS)}
    generators = {op: random.Random(seed) for op, seed in seeds.items()}
    member, spent = core.empty(), 0
    model_seconds, acquisition_seconds, observation_seconds, output_seconds = 0., 0., 0., 0.
    bank = 'a' if case['context'] == 'A' else 'b'
    before = deepcopy(state[bank]['pools'][identity])
    quota = probe_quota(arm)
    pending = quota-actual_probe_paid_before
    available = TOTAL_BUDGETS[life]-SOURCE_COST-history_paid_samples-quota

    def timed(operation, *args, acquisition_call=False):
        nonlocal model_seconds, acquisition_seconds
        begun = process_time()
        result = operation(*args)
        elapsed = process_time()-begun
        model_seconds += elapsed
        if acquisition_call:
            acquisition_seconds += elapsed
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
        choice = timed(acquisition.choose, member, plan, spent, work, acquisition_call=True)
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
        initial_plan=initial, batches=batches, terminal_plan=terminal, spent=spent,
        member=deepcopy(member), pooled_before=before,
        pooled_after=deepcopy(state[bank]['pools'][identity]),
        source_paid_samples=source_paid_samples, history_paid_samples=history_paid_samples,
        ordinary_history_paid_samples=history_paid_samples,
        actual_probe_paid_before=actual_probe_paid_before, pending_probe_reserved=pending,
        future_B_source_reserved=SOURCE_COST-source_paid_samples, probe_quota_samples=quota,
        current_paid_samples=spent, new_paid_samples=spent,
        total_reference_paid_samples=source_paid_samples+history_paid_samples+actual_probe_paid_before+spent,
        life_budget_remaining_before=available, life_budget_remaining_after=available-spent,
        budget_exhausted=available-spent < BATCH, member_cap_exhausted=spent == CAP,
        model_seconds=model_seconds, acquisition_seconds=acquisition_seconds,
        observation_seconds=observation_seconds, output_seconds=output_seconds,
        execution_certified=plan['utility_lower'] >= 2, goal_impossible=plan['goal_impossible'],
        query_certified=plan['query_ready'], joint_completed=completed, fallback=not completed,
        executed_mix=deepcopy(plan['mix']) if completed else [('WAIT', F(1))])


def shared_probes(life, arm, identity, trigger_index, timing, state, cases, laws,
                  ordinary_paid, probe_paid, work, stream, generators, offsets):
    """Read one identity's fixed paired streams into its existing native A pool."""
    model_seconds, observation_seconds, output_seconds, batches = 0., 0., 0., 0
    for j, operator in enumerate(PROBE_OPERATORS):
        key = (identity, operator)
        seed = PROBE_BASE+(life*3+identity)*len(PROBE_OPERATORS)+j
        if key not in generators:
            generators[key] = random.Random(seed)
            offsets[key] = 0
        while offsets[key] < PROBE_AMOUNT:
            start = offsets[key]
            increments = dict.fromkeys(ALPHABETS[operator], 0)
            progress = dict(draw_end=start, n=start)
            before = deepcopy(state['a']['pools'][identity][operator])
            begun = perf_counter()
            draw(generators[key], laws[identity], operator, increments, BATCH, work, progress)
            observation_seconds += perf_counter()-begun
            begun = process_time()
            core.observe(state, cases[identity], identity, operator, increments)
            model_seconds += process_time()-begun
            row = dict(life=life, arm=arm, identity=identity, source_index=identity,
                operator=operator, seed=seed, draw_start=start, draw_end=progress['draw_end'],
                increments=increments, trigger_index=trigger_index, timing=timing,
                pool_before=before, pool_after=deepcopy(state['a']['pools'][identity][operator]),
                probe_paid_before=probe_paid, probe_paid_after=probe_paid+BATCH,
                pending_probe_reserved_before=probe_quota(arm)-probe_paid,
                pending_probe_reserved_after=probe_quota(arm)-probe_paid-BATCH,
                ordinary_history_paid_samples=ordinary_paid, source_paid_samples=SOURCE_COST)
            probe_paid += BATCH
            offsets[key] = progress['draw_end']
            work['shared_probe_batches'] += 1
            work['shared_probe_samples'] += BATCH
            batches += 1
            begun = perf_counter()
            stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
            stream.flush()
            output_seconds += perf_counter()-begun
    return dict(paid_samples=probe_paid, batches=batches, model_seconds=model_seconds,
                observation_seconds=observation_seconds, output_seconds=output_seconds)


def run_life_arm(life, arm, bundle):
    """One chronological, cold, isolated worker; this function never scores truth."""
    begun = perf_counter()
    cases, laws, identities, metadata = (bundle[key] for key in ('cases', 'laws', 'identities', 'metadata'))
    normalizers, query_cache, work = activate_cold_caches(), {}, Counter()
    timings = dict.fromkeys(TIMING_SCOPES, 0.)
    started = process_time()
    state = core.prepare(bundle['a'], life, CORE_ARMS[arm], work)
    timings['initialization'] += process_time()-started
    paid, probe_paid, probe_batches, output_seconds = 0, 0, 0, 0.
    first_return, completed, generators, offsets, profile_ids = {}, [], {}, {}, {}
    with (gzip.open(worker_filename('records', life, arm), 'wt') as stream,
          gzip.open(worker_filename('profiles', life, arm), 'wt') as profiles,
          worker_filename('probes', life, arm).open('w') as probes):

        def probe(identity, index, timing):
            nonlocal probe_paid, probe_batches, output_seconds
            result = shared_probes(life, arm, identity, index, timing, state, cases, laws,
                paid, probe_paid, work, probes, generators, offsets)
            probe_paid = result['paid_samples']
            probe_batches += result['batches']
            timings['probe_pool_updates'] += result['model_seconds']
            timings['probe_draw'] += result['observation_seconds']
            output_seconds += result['output_seconds']
            completed.append(identity)

        for index in TARGETS:
            if index == 30:
                started = process_time()
                core.begin_b(state, bundle['b'], metadata['changed_operator'], metadata['b_to_a'], work)
                timings['begin_b'] += process_time()-started
            if arm == 'BEFORE_SHARED' and index == 54:
                for identity in range(3):
                    probe(identity, index, 'before_target')
            identity = identities[index]
            row = run_target(life, index, cases[index], identity, state, arm,
                laws[index], work, 3456 if index < 30 else SOURCE_COST, paid, probe_paid,
                query_cache, profiles, profile_ids)
            timings['planning'] += row['model_seconds']
            timings['acquisition'] += row['acquisition_seconds']
            timings['observation'] += row['observation_seconds']
            output_seconds += row['output_seconds']
            paid += row['spent']
            started = perf_counter()
            stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
            stream.flush()
            profiles.flush()
            output_seconds += perf_counter()-started
            # The row, terminal proof, and executed mix are already frozen.
            if index >= 54 and identity not in first_return:
                first_return[identity] = index
                if arm == 'DEFERRED_SHARED':
                    probe(identity, index, 'after_target')
            print(f'life={life} arm={arm} target={index} spent={row["spent"]} '
                f'query={row["query_certified"]} joint={row["joint_completed"]} '
                f'ordinary_paid={paid} probe_paid={probe_paid}', flush=True)
    artifact = dict(life=life, arm=arm, final_state=deepcopy(state), timings=timings,
        work=work, profiles=len(profile_ids),
        probe_ledger=dict(life=life, arm=arm, quota_samples=probe_quota(arm),
            paid_samples=probe_paid, pending_reserved_samples=probe_quota(arm)-probe_paid,
            probe_batches=probe_batches, first_return_index_by_type=first_return,
            completed_probe_identities=completed),
        normalizer_cache_statistics={name: function.cache_info()._asdict()
            for name, function in normalizers.items()},
        life_arm_wall_seconds=perf_counter()-begun)
    started = perf_counter()
    save(OUTPUT/f'worker_artifacts_life_{life:02d}_{arm}.json', artifact)
    output_seconds += perf_counter()-started
    return dict(artifact, output_seconds=output_seconds)


def method_aggregate(rows):
    result = aggregate(rows)
    result['executed_risk_violations'] = sum(row['executed']['violation'] for row in rows)
    return result


def return_groups(rows):
    first = {}
    for row in sorted(rows, key=lambda item: (item['life'], item['index'])):
        first.setdefault((row['life'], row['identity']), row['index'])
    return ([row for row in rows if row['index'] == first[row['life'], row['identity']]],
            [row for row in rows if row['index'] != first[row['life'], row['identity']]])


def summarize(records, timings):
    methods, life_summaries = {}, []
    for arm in ARMS:
        selected = [row for row in records if row['arm'] == arm]
        returns = [row for row in selected if row['stage'] == 'A_RETURN']
        first, later = return_groups(returns)
        methods[arm] = dict(method_aggregate(selected), source_samples=SOURCE_COST*len(LIVES),
            probe_samples=probe_quota(arm)*len(LIVES),
            total_samples=(SOURCE_COST+probe_quota(arm))*len(LIVES)+sum(row['spent'] for row in selected),
            late_b=method_aggregate([row for row in selected if 42 <= row['index'] < 54]),
            a_return=method_aggregate(returns),
            first_return=method_aggregate(first), later_return=method_aggregate(later))
        methods[arm]['model_seconds'] = sum(timings[scope][arm][life]
            for scope in MODEL_SCOPES for life in LIVES)
        for scope in MODEL_SCOPES+('acquisition',):
            methods[arm][scope+'_seconds'] = sum(timings[scope][arm].values())
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            return_subset = [row for row in subset if row['stage'] == 'A_RETURN']
            first, later = return_groups(return_subset)
            life_summaries.append(dict(life=life, arm=arm, source_samples=SOURCE_COST,
                probe_samples=probe_quota(arm),
                total_samples=SOURCE_COST+probe_quota(arm)+sum(row['spent'] for row in subset),
                model_seconds=sum(timings[scope][arm][life] for scope in MODEL_SCOPES),
                stages={stage: method_aggregate([row for row in subset if row['stage'] == stage])
                        for stage in task.STAGES},
                first_return=method_aggregate(first), later_return=method_aggregate(later)))
    before = methods['BEFORE_SHARED']
    conditions = dict(late_b_quality=before['late_b']['query_certified'] >= 27,
                      a_return_quality=before['a_return']['query_certified'] >= 54)
    for control in ('DEFERRED_SHARED', 'REBUILD'):
        name, other = control.lower(), methods[control]
        conditions.update({
            f'matched_{name}_late_b_quality': before['late_b']['query_certified'] >= other['late_b']['query_certified'],
            f'matched_{name}_a_return_quality': before['a_return']['query_certified'] >= other['a_return']['query_certified'],
            f'matched_{name}_joint_quality': before['joint_completed'] >= other['joint_completed']})
    conditions['actual_acquisition_saving_vs_rebuild'] = before['total_samples'] < methods['REBUILD']['total_samples']
    conditions['actual_acquisition_nondegrading_vs_deferred_shared'] = before['total_samples'] <= methods['DEFERRED_SHARED']['total_samples']
    conditions['valid_certificates_and_execution'] = all(method[field] == 0 for method in methods.values()
        for field in ('false_query_certificates', 'false_execution_certificates',
            'false_impossible_certificates', 'false_goal_uppers', 'risk_violations', 'executed_risk_violations'))
    paired = []
    for life in LIVES:
        rows = {row['arm']: row for row in life_summaries if row['life'] == life}
        paired.append(dict(life=life,
            deferred_shared_minus_before_shared_samples=rows['DEFERRED_SHARED']['total_samples']-rows['BEFORE_SHARED']['total_samples'],
            rebuild_minus_before_shared_samples=rows['REBUILD']['total_samples']-rows['BEFORE_SHARED']['total_samples'],
            return_before_shared_minus_deferred_shared_query_certified=rows['BEFORE_SHARED']['stages']['A_RETURN']['query_certified']-
                rows['DEFERRED_SHARED']['stages']['A_RETURN']['query_certified'],
            return_before_shared_minus_deferred_shared_joint_completed=rows['BEFORE_SHARED']['stages']['A_RETURN']['joint_completed']-
                rows['DEFERRED_SHARED']['stages']['A_RETURN']['joint_completed']))
    return dict(complete=True, records=len(records), methods=methods, life_summaries=life_summaries,
        paired=paired, conditions=conditions, stage_condition_met=all(conditions.values()),
        physical_source_samples=SOURCE_COST*len(LIVES), source_samples_charged_per_arm=SOURCE_COST*len(LIVES),
        physical_probe_samples=sum(probe_quota(arm) for arm in ARMS)*len(LIVES),
        new_environment_observations=SOURCE_COST*len(LIVES)+sum(row['spent'] for row in records)+
            sum(probe_quota(arm) for arm in ARMS)*len(LIVES),
        risk_violation_scope='all_retained_plans',
        model_seconds_scope='summed_process_CPU_planning_acquisition_pool_observation_bank_initialization_and_probe_pool_updates',
        acquisition_seconds_scope='full_choose_process_CPU_subset_of_planning_model_time',
        scientific_gate_changed=False, qualification_only=True)


def prerequisites():
    previous = ROOT/'reports/endpoint_regions_v248'
    run = json.loads((previous/'run.json').read_text())
    analysis = json.loads((previous/'analysis.json').read_text())
    summary = json.loads((previous/'summary.json').read_text())
    if not run['complete'] or not analysis['valid'] or summary['endpoints'] != 48 or summary['records'] != 96:
        raise ValueError('V248 must have all 48 endpoints/96 classifications complete and independently valid')
    return dict(v248_complete=True, v248_independent_valid=True, v248_endpoints=48, v248_classifications=96)


def capture():
    from scripts import audit_shared_probe_timing_v249
    paths = set(('scripts/run_shared_probe_timing_v249.py', 'scripts/audit_shared_probe_timing_v249.py',
        'tests/test_shared_probe_timing_v249_runner.py', 'tests/test_shared_probe_timing_v249_audit.py',
        'specs/SHARED_PROBE_TIMING_V249.md'))
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

    jobs = [dict(life=life, arm=arm) for life in LIVES for arm in ARMS]
    protocol = dict(lives=LIVES, arms=ARMS, targets_per_life=72, cap=CAP, batch=BATCH,
        source_seed_base=SOURCE_BASE, target_seed_base=TARGET_BASE, probe_seed_base=PROBE_BASE,
        per_life_total_budgets=TOTAL_BUDGETS, source_samples_per_life=SOURCE_COST,
        probe_samples_per_identity_operator=PROBE_AMOUNT, probe_operators=PROBE_OPERATORS,
        probe_quota_per_life_arm={arm: probe_quota(arm) for arm in ARMS},
        probe_timing=dict(BEFORE_SHARED='all_before_target54',
            DEFERRED_SHARED='each_identity_after_first_return_decision_frozen', REBUILD='none'),
        query_stream_count=48, query_threshold=960, query_delta_per_life_arm='1/20',
        execution_delta_per_life_arm='1/20', combined_delta_upper='1/10',
        scientific_gate_changed=False, qualification_only=True, prerequisites=admitted,
        computation_cache_scope=COMPUTATION_CACHE_SCOPE, pool_core_arm_mapping=CORE_ARMS,
        worker_jobs=jobs, execution=dict(independent_life_arm_processes=9,
            posthoc_scoring='after_all_648_decisions_frozen'),
        model_seconds_clock='process_time', observation_output_scoring_seconds_clock='perf_counter',
        oracle_information=['type identity', 'B changed operator', 'B-to-A correspondence'])
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen'], complete=False))
    started = perf_counter()
    capture()
    output_seconds += perf_counter()-started
    bundles, source_records, source_work, source_seconds = {}, [], Counter(), {}
    for life in LIVES:
        cases, laws, identities, metadata = task.world(life)
        a, a_seconds = sources(life, 'A', laws, source_records, source_work)
        b, b_seconds = sources(life, 'B', laws, source_records, source_work)
        source_seconds[life] = a_seconds+b_seconds
        bundles[life] = dict(cases=cases, laws=laws, identities=identities, metadata=metadata, a=a, b=b)
    output(OUTPUT/'source_records.json', source_records)
    output(OUTPUT/'source_evidence.json', [dict(life=life, a=bundles[life]['a'], b=bundles[life]['b']) for life in LIVES])
    output(OUTPUT/'cases.json', [dict(life=life, cases=bundles[life]['cases']) for life in LIVES])
    output(OUTPUT/'interfaces.json', [dict(life=life, identities=bundles[life]['identities'],
        metadata=bundles[life]['metadata']) for life in LIVES])
    with ProcessPoolExecutor(max_workers=9) as executor:
        futures = [executor.submit(run_life_arm, job['life'], job['arm'], bundles[job['life']]) for job in jobs]
        artifacts = [future.result() for future in futures]
    output(OUTPUT/'final_states.json', [dict(life=item['life'], arm=item['arm'], state=item['final_state']) for item in artifacts])
    output(OUTPUT/'probe_ledgers.json', [item['probe_ledger'] for item in artifacts])
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen', 'all_decisions_frozen'], complete=False))
    timings = {scope: {arm: {item['life']: item['timings'][scope] for item in artifacts if item['arm'] == arm}
        for arm in ARMS} for scope in TIMING_SCOPES}
    output_seconds += sum(item['output_seconds'] for item in artifacts)
    results, scoring_seconds = [], 0.
    for job in jobs:
        life, arm = job['life'], job['arm']
        with (gzip.open(worker_filename('records', life, arm), 'rt') as source,
              gzip.open(worker_filename('results', life, arm), 'wt') as destination):
            for line in source:
                row = json.loads(line)
                started = perf_counter()
                result = evaluate(row, bundles[life]['laws'][row['index']])
                scoring_seconds += perf_counter()-started
                result['identity'] = row['identity']
                results.append(result)
                started = perf_counter()
                destination.write(json.dumps(exact_json(result), separators=(',', ':'))+'\n')
                output_seconds += perf_counter()-started
    summary = summarize(results, timings)
    summary.update(elapsed_seconds=perf_counter()-begun, timings=timings,
        life_arm_wall_seconds={arm: {item['life']: item['life_arm_wall_seconds'] for item in artifacts
            if item['arm'] == arm} for arm in ARMS},
        life_arm_wall_seconds_scope='worker_entry_through_all_decisions_and_probes_retained_before_artifact_write',
        scoring_seconds=scoring_seconds, output_seconds=output_seconds,
        output_seconds_scope='summed_parent_and_worker_write_and_retention_wall_calls_before_final_summary',
        computation_cache_scope=COMPUTATION_CACHE_SCOPE,
        normalizer_cache_statistics={arm: {item['life']: item['normalizer_cache_statistics']
            for item in artifacts if item['arm'] == arm} for arm in ARMS},
        source_seconds=source_seconds, source_work=source_work,
        work={arm: sum((Counter(item['work']) for item in artifacts if item['arm'] == arm), Counter()) for arm in ARMS},
        profiles={arm: {item['life']: item['profiles'] for item in artifacts if item['arm'] == arm} for arm in ARMS},
        probe_ledgers=[item['probe_ledger'] for item in artifacts],
        return_transfers=[dict(life=item['life'], arm=item['arm'], ledger=item['final_state']['return_merge']) for item in artifacts])
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol,
        phases=['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'], complete=True))
    print(json.dumps(exact_json(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
