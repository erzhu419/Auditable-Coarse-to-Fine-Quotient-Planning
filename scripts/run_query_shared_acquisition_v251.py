"""Frozen shared query acquisition and stopping experiment; truth follows retention."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from fractions import Fraction as F
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
from acfqp.science import latent_mechanisms_v213 as mechanics
from acfqp.science import online_joint_query_v242 as online
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_reuse_rebuild_lifecycle_v242 import retain_plan, evaluate
from scripts.run_persistent_evidence_v221 import query_score
from scripts.run_shared_probe_timing_v249 import (activate_cold_caches,
    method_aggregate, return_groups, COMPUTATION_CACHE_SCOPE)

OUTPUT = ROOT/'reports/query_shared_acquisition_v251'
LIVES, ARMS = (0, 1, 2), ('UNIFORM_SHARED', 'QUERY_FIXED', 'QUERY_SHARED')
TARGETS = tuple(range(3, 27))+tuple(range(30, 78))
OPERATORS, ALPHABETS = core.OPERATORS, core.ALPHABETS
SOURCE_BASE, TARGET_BASE, PROBE_BASE = 295000, 296000, 297000
TOTAL_BUDGETS, SOURCE_COST, CAP, BATCH = (14144, 17072, 17168), 4608, 384, 16
A_SHARED_CAP, B_SHARED_FIXED, SHARED_CAP = 3072, 1152, 4224
PUBLIC_COSTS = (('low', '17/20'), ('low', '19/20'), ('high', '17/20'), ('high', '19/20'))
MODEL_SCOPES = ('planning', 'initialization', 'begin_b', 'probe_pool_updates', 'query_previews', 'shared_acquisition')
TIMING_SCOPES = MODEL_SCOPES+('acquisition', 'observation', 'probe_draw')
ERROR_FIELDS = ('false_query_certificates', 'false_execution_certificates',
    'false_impossible_certificates', 'false_goal_uppers', 'risk_violations',
    'executed_risk_violations', 'aux_false_query_certificates')


def worker_filename(kind, life, arm):
    ending = '.jsonl' if kind == 'probes' else '.jsonl.gz'
    return OUTPUT/f'{kind}_life_{life:02d}_{arm}{ending}'


def write_row(stream, row):
    begun = perf_counter()
    stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
    stream.flush()
    return perf_counter()-begun


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
               source_paid_samples, history_paid_samples, actual_probe_paid_before, pending_probe_reserved, released_probe_samples,
               query_cache, profile_stream, profile_ids):
    seeds = {op: TARGET_BASE+(life*78+index)*3+j for j, op in enumerate(OPERATORS)}
    generators = {op: random.Random(seed) for op, seed in seeds.items()}
    member, spent = core.empty(), 0
    model_seconds, acquisition_seconds, observation_seconds, output_seconds = 0., 0., 0., 0.
    bank = 'a' if case['context'] == 'A' else 'b'
    before = deepcopy(state[bank]['pools'][identity])
    available = TOTAL_BUDGETS[life]-SOURCE_COST-history_paid_samples-actual_probe_paid_before-pending_probe_reserved

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
    return dict(life=life, index=index, case=deepcopy(case), identity=identity, arm=arm, seeds=seeds, initial_plan=initial, batches=batches,
        terminal_plan=terminal, spent=spent, member=deepcopy(member), pooled_before=before,
        pooled_after=deepcopy(state[bank]['pools'][identity]),
        source_paid_samples=source_paid_samples, history_paid_samples=history_paid_samples,
        ordinary_history_paid_samples=history_paid_samples, actual_probe_paid_before=actual_probe_paid_before,
        pending_probe_reserved=pending_probe_reserved, released_probe_samples=released_probe_samples,
        probe_cap_samples=SHARED_CAP,
        future_B_source_reserved=SOURCE_COST-source_paid_samples, probe_quota_samples=SHARED_CAP,
        current_paid_samples=spent, new_paid_samples=spent,
        total_reference_paid_samples=source_paid_samples+history_paid_samples+actual_probe_paid_before+spent,
        life_budget_remaining_before=available, life_budget_remaining_after=available-spent,
        budget_exhausted=available-spent < BATCH, member_cap_exhausted=spent == CAP,
        model_seconds=model_seconds, acquisition_seconds=acquisition_seconds,
        observation_seconds=observation_seconds, output_seconds=output_seconds,
        execution_certified=plan['utility_lower'] >= 2, goal_impossible=plan['goal_impossible'],
        query_certified=plan['query_ready'], joint_completed=completed, fallback=not completed,
        executed_mix=deepcopy(plan['mix']) if completed else [('WAIT', F(1))])



def query_preview(life, arm, identity, cost_index, preview_id, after_probe_batch,
                  state, bundle, query_cache, work, profile_stream, profile_ids):
    """Query-only observed-pool proof, with no execution/member planning."""
    begun = process_time()
    case = deepcopy(bundle['cases'][identity])
    case['operating'], case['retry_cost'] = PUBLIC_COSTS[cost_index]
    counts = core.point_counts(case, state, identity)
    posterior = mechanics.posterior(counts)
    vectors = mechanics.vectors(case, posterior)
    queries = mechanics.queries(dict(pure_vectors=vectors))
    evidence = online.certificates(counts, case, queries, query_cache, work)
    work['aux_query_previews'] += 1
    model_seconds = process_time()-begun
    begun = perf_counter()
    record = retain_plan(dict(life=life, arm=arm, preview_id=preview_id, identity=identity,
        cost_index=cost_index, after_probe_batch=after_probe_batch, case=case,
        evidence_counts=deepcopy(counts), posterior=posterior, pure_vectors=vectors,
        queries=queries, query_evidence=evidence, query_ready=evidence['all_ready']),
        profile_stream, profile_ids)
    return dict(record=record, model_seconds=model_seconds, output_seconds=perf_counter()-begun)


def shared_choice(arm, ready_by_type, paid_by_type_op):
    unresolved = [] if arm == 'UNIFORM_SHARED' else [i for i, ready in enumerate(ready_by_type) if not ready]
    if arm == 'UNIFORM_SHARED':
        identity, operator = next((i, op) for i in range(3) for op in OPERATORS[:2]
            if paid_by_type_op[i][op] < 512)
        reason, all_ready = 'uniform_fixed_allocation', None
    elif unresolved:
        identity = min(unresolved, key=lambda i: (sum(paid_by_type_op[i].values()), i))
        operator = min(OPERATORS[:2], key=lambda op: (paid_by_type_op[identity][op], OPERATORS.index(op)))
        reason, all_ready = 'unresolved_type_balanced_row', False
    else:
        identity, operator = min(((i, op) for i in range(3) for op in OPERATORS[:2]),
            key=lambda pair: (paid_by_type_op[pair[0]][pair[1]], pair[0], OPERATORS.index(pair[1])))
        reason, all_ready = 'all_ready_balanced_all_rows', True
    return dict(identity=identity, operator=operator, reason=reason,
        unresolved_types=unresolved, all_ready=all_ready)


def observe_probe(life, arm, context, identity, operator, state, bundle, ordinary_paid,
                  ledger, work, stream, generators, offsets, probe_sequence):
    bank, slot = ('a', 0) if context == 'A' else ('b', 1)
    source_index = identity if context == 'A' else 27+identity
    key = (context, identity, operator)
    seed = PROBE_BASE+(life*6+slot*3+identity)*3+OPERATORS.index(operator)
    if key not in generators:
        generators[key], offsets[key] = random.Random(seed), 0
    start = offsets[key]
    increments = dict.fromkeys(ALPHABETS[operator], 0)
    progress = dict(draw_end=start, n=start)
    before = deepcopy(state[bank]['pools'][identity][operator])
    begun = perf_counter()
    draw(generators[key], bundle['laws'][source_index], operator, increments, BATCH, work, progress)
    draw_seconds = perf_counter()-begun
    begun = process_time()
    core.observe(state, bundle['cases'][source_index], identity, operator, increments)
    model_seconds = process_time()-begun
    row = dict(life=life, arm=arm, context=context, identity=identity,
        source_index=source_index, operator=operator, seed=seed, draw_start=start,
        draw_end=progress['draw_end'], increments=increments,
        trigger_index=3 if context == 'A' else 30, timing='before_target',
        pool_before=before, pool_after=deepcopy(state[bank]['pools'][identity][operator]),
        probe_paid_before=ledger['paid_samples'], probe_paid_after=ledger['paid_samples']+BATCH,
        pending_probe_reserved_before=ledger['pending_samples'],
        pending_probe_reserved_after=ledger['pending_samples']-BATCH,
        released_samples_before=ledger['released_samples'], released_samples_after=ledger['released_samples'],
        ordinary_history_paid_samples=ordinary_paid, source_paid_samples=3456 if context == 'A' else SOURCE_COST,
        probe_sequence=probe_sequence)
    ledger['paid_samples'] += BATCH
    ledger['pending_samples'] -= BATCH
    offsets[key] = progress['draw_end']
    work['shared_probe_batches'] += 1
    work['shared_probe_samples'] += BATCH
    return dict(row=row, model_seconds=model_seconds, draw_seconds=draw_seconds,
        output_seconds=write_row(stream, row))


def shared_a(life, arm, state, bundle, work, query_cache, profile_stream, profile_ids,
             preview_stream, probe_stream, ledger, generators, offsets):
    paid_rows = [{op: 0 for op in OPERATORS[:2]} for _ in range(3)]
    ready, latest, initial, batches = [], [], [], []
    timing = dict.fromkeys(('query_previews', 'shared_acquisition', 'probe_pool_updates', 'probe_draw'), 0.)
    output_seconds, preview_count, paid = 0., 0, 0

    def previews(identity, batch_index):
        nonlocal output_seconds, preview_count
        ids, all_ready = [], True
        for cost_index in range(4):
            result = query_preview(life, arm, identity, cost_index, preview_count,
                batch_index, state, bundle, query_cache, work, profile_stream, profile_ids)
            preview = result['record']
            timing['query_previews'] += result['model_seconds']
            output_seconds += result['output_seconds']+write_row(preview_stream, preview)
            ids.append(preview_count)
            preview_count += 1
            all_ready = all_ready and preview['query_ready']
        return ids, all_ready

    if arm != 'UNIFORM_SHARED':
        for identity in range(3):
            ids, type_ready = previews(identity, 0)
            initial.extend(ids)
            latest.append(ids)
            ready.append(type_ready)
    first_ready = 0 if ready and all(ready) else None
    while paid < A_SHARED_CAP:
        if arm == 'QUERY_SHARED' and all(ready):
            break
        begun = process_time()
        choice = shared_choice(arm, ready, paid_rows)
        work['shared_acquisition_choices'] += 1
        timing['shared_acquisition'] += process_time()-begun
        batch_index = len(batches)+1
        result = observe_probe(life, arm, 'A', choice['identity'], choice['operator'], state,
            bundle, 0, ledger, work, probe_stream, generators, offsets, batch_index)
        paid += BATCH
        paid_rows[choice['identity']][choice['operator']] += BATCH
        timing['probe_pool_updates'] += result['model_seconds']
        timing['probe_draw'] += result['draw_seconds']
        output_seconds += result['output_seconds']
        updated = []
        if arm != 'UNIFORM_SHARED':
            updated, ready[choice['identity']] = previews(choice['identity'], batch_index)
            latest[choice['identity']] = updated
            if all(ready) and first_ready is None:
                first_ready = paid
        batches.append(dict(batch_index=batch_index, choice=choice, probe_sequence=batch_index,
            updated_previews=updated, paid_by_type_op_after=deepcopy(paid_rows)))
    before_release = deepcopy(ledger)
    released = A_SHARED_CAP-paid
    ledger['pending_samples'] -= released
    ledger['released_samples'] += released
    phase = dict(life=life, arm=arm, cap_samples=A_SHARED_CAP, initial_previews=initial,
        batches=batches, final_ready_by_type=ready, latest_preview_ids=latest,
        first_all_ready_paid=first_ready,
        stop_reason='all_ready' if arm == 'QUERY_SHARED' and all(ready) else 'cap',
        a_paid_samples=paid, released_delta=released,
        ledger_before_release=before_release, ledger_after_release=deepcopy(ledger))
    return dict(phase=phase, timings=timing, previews=preview_count, output_seconds=output_seconds)


def run_life_arm(life, arm, bundle):
    begun = perf_counter()
    normalizers, query_cache, work = activate_cold_caches(), {}, Counter()
    timings = dict.fromkeys(TIMING_SCOPES, 0.)
    started = process_time()
    state = core.prepare(bundle['a'], life, 'ONE_WAY', work)
    timings['initialization'] += process_time()-started
    paid, probe_batches, output_seconds = 0, 0, 0.
    generators, offsets, profile_ids = {}, {}, {}
    ledger = dict(cap_samples=SHARED_CAP, paid_samples=0, pending_samples=SHARED_CAP, released_samples=0)
    with (gzip.open(worker_filename('records', life, arm), 'wt') as stream,
          gzip.open(worker_filename('profiles', life, arm), 'wt') as profiles,
          gzip.open(worker_filename('previews', life, arm), 'wt') as previews,
          worker_filename('probes', life, arm).open('w') as probes):
        result = shared_a(life, arm, state, bundle, work, query_cache, profiles, profile_ids,
            previews, probes, ledger, generators, offsets)
        phase, preview_count = result['phase'], result['previews']
        probe_batches = len(phase['batches'])
        for scope, elapsed in result['timings'].items():
            timings[scope] += elapsed
        output_seconds += result['output_seconds']
        started = perf_counter()
        save(OUTPUT/f'a_phase_life_{life:02d}_{arm}.json', phase)
        output_seconds += perf_counter()-started
        for index in TARGETS:
            if index == 30:
                started = process_time()
                metadata = bundle['metadata']
                core.begin_b(state, bundle['b'], metadata['changed_operator'], metadata['b_to_a'], work)
                timings['begin_b'] += process_time()-started
                for identity in range(3):
                    for _ in range(384//BATCH):
                        probe_batches += 1
                        result = observe_probe(life, arm, 'B', identity, metadata['changed_operator'],
                            state, bundle, paid, ledger, work, probes, generators, offsets, probe_batches)
                        timings['probe_pool_updates'] += result['model_seconds']
                        timings['probe_draw'] += result['draw_seconds']
                        output_seconds += result['output_seconds']
            row = run_target(life, index, bundle['cases'][index], bundle['identities'][index], state,
                arm, bundle['laws'][index], work, 3456 if index < 30 else SOURCE_COST, paid,
                ledger['paid_samples'], ledger['pending_samples'], ledger['released_samples'],
                query_cache, profiles, profile_ids)
            for scope, field in (('planning', 'model_seconds'), ('acquisition', 'acquisition_seconds'),
                                 ('observation', 'observation_seconds')):
                timings[scope] += row[field]
            output_seconds += row['output_seconds']+write_row(stream, row)
            profiles.flush()
            paid += row['spent']
            print(f'life={life} arm={arm} target={index} spent={row["spent"]} '
                f'query={row["query_certified"]} joint={row["joint_completed"]} '
                f'ordinary_paid={paid} probe_paid={ledger["paid_samples"]} released={ledger["released_samples"]}', flush=True)
    artifact = dict(life=life, arm=arm, final_state=deepcopy(state), timings=timings,
        work=work, profiles=len(profile_ids), previews=preview_count,
        a_phase_summary={key: phase[key] for key in ('a_paid_samples', 'released_delta',
            'stop_reason', 'final_ready_by_type', 'first_all_ready_paid')},
        probe_ledger=dict(life=life, arm=arm, cap_samples=SHARED_CAP,
            paid_samples=ledger['paid_samples'], pending_reserved_samples=ledger['pending_samples'],
            released_samples=ledger['released_samples'], by_context=dict(A=phase['a_paid_samples'], B=B_SHARED_FIXED),
            probe_batches=probe_batches),
        normalizer_cache_statistics={name: function.cache_info()._asdict() for name, function in normalizers.items()},
        life_arm_wall_seconds=perf_counter()-begun)
    started = perf_counter()
    save(OUTPUT/f'worker_artifacts_life_{life:02d}_{arm}.json', artifact)
    output_seconds += perf_counter()-started
    return dict(artifact, output_seconds=output_seconds)


def score_preview(row, law):
    queries = query_score(row['queries'], law, row['case'])
    certified = {query: decision['certified'] for query, decision in row['query_evidence']['queries'].items()}
    return dict(**{key: row[key] for key in ('life', 'arm', 'preview_id', 'identity', 'cost_index', 'after_probe_batch', 'case')},
        queries=queries, certified_by_query=certified,
        false_aux_query_certificates=sum(certified[q] and queries[q]['regret'] > F(1, 20) for q in queries))


def conditions_for(methods):
    selected = methods['QUERY_SHARED']
    conditions = dict(late_b_quality=selected['late_b']['query_certified'] >= 27,
        a_return_quality=selected['a_return']['query_certified'] >= 54)
    for control in ('QUERY_FIXED', 'UNIFORM_SHARED'):
        other, name = methods[control], control.lower()
        conditions.update({f'matched_{name}_late_b_quality': selected['late_b']['query_certified'] >= other['late_b']['query_certified'],
            f'matched_{name}_a_return_quality': selected['a_return']['query_certified'] >= other['a_return']['query_certified'],
            f'matched_{name}_joint_quality': selected['joint_completed'] >= other['joint_completed']})
    conditions['actual_acquisition_saving_vs_uniform_shared'] = selected['total_samples'] < methods['UNIFORM_SHARED']['total_samples']
    conditions['actual_acquisition_nondegrading_vs_query_fixed'] = selected['total_samples'] <= methods['QUERY_FIXED']['total_samples']
    conditions['valid_certificates_and_execution'] = all(method[field] == 0 for method in methods.values() for field in ERROR_FIELDS)
    return conditions


def summarize(records, preview_results, timings, probe_ledgers):
    methods, life_summaries = {}, []
    for arm in ARMS:
        selected = [row for row in records if row['arm'] == arm]
        previews = [row for row in preview_results if row['arm'] == arm]
        ledgers = [item for item in probe_ledgers if item['arm'] == arm]
        returns = [row for row in selected if row['stage'] == 'A_RETURN']
        first, later = return_groups(returns)
        methods[arm] = dict(method_aggregate(selected), source_samples=SOURCE_COST*len(LIVES),
            probe_samples=sum(item['paid_samples'] for item in ledgers),
            a_shared_samples=sum(item['by_context']['A'] for item in ledgers),
            b_fixed_samples=sum(item['by_context']['B'] for item in ledgers),
            released_probe_samples=sum(item['released_samples'] for item in ledgers),
            total_samples=SOURCE_COST*len(LIVES)+sum(row['spent'] for row in selected)+sum(item['paid_samples'] for item in ledgers),
            late_b=method_aggregate([row for row in selected if 42 <= row['index'] < 54]),
            a_return=method_aggregate(returns), first_return=method_aggregate(first), later_return=method_aggregate(later),
            aux_preview_records=len(previews), aux_false_query_certificates=sum(row['false_aux_query_certificates'] for row in previews),
            model_seconds=sum(timings[scope][arm][life] for scope in MODEL_SCOPES for life in LIVES))
        for scope in MODEL_SCOPES+('acquisition',):
            methods[arm][scope+'_seconds'] = sum(timings[scope][arm].values())
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            ledger = next(item for item in ledgers if item['life'] == life)
            total = SOURCE_COST+ledger['paid_samples']+sum(row['spent'] for row in subset)
            first, later = return_groups([row for row in subset if row['stage'] == 'A_RETURN'])
            life_summaries.append(dict(life=life, arm=arm, source_samples=SOURCE_COST,
                probe_samples=ledger['paid_samples'], a_shared_samples=ledger['by_context']['A'],
                b_fixed_samples=ledger['by_context']['B'], released_probe_samples=ledger['released_samples'],
                total_samples=total, budget_valid=total <= TOTAL_BUDGETS[life],
                aux_preview_records=sum(row['life'] == life for row in previews),
                aux_false_query_certificates=sum(row['false_aux_query_certificates'] for row in previews if row['life'] == life),
                model_seconds=sum(timings[scope][arm][life] for scope in MODEL_SCOPES),
                stages={stage: method_aggregate([row for row in subset if row['stage'] == stage]) for stage in task.STAGES},
                first_return=method_aggregate(first), later_return=method_aggregate(later)))
    conditions = conditions_for(methods)
    paired = []
    for life in LIVES:
        rows = {row['arm']: row for row in life_summaries if row['life'] == life}
        paired.append(dict(life=life,
            query_fixed_minus_uniform_shared_samples=rows['QUERY_FIXED']['total_samples']-rows['UNIFORM_SHARED']['total_samples'],
            query_shared_minus_query_fixed_samples=rows['QUERY_SHARED']['total_samples']-rows['QUERY_FIXED']['total_samples'],
            return_query_shared_minus_query_fixed_query_certified=rows['QUERY_SHARED']['stages']['A_RETURN']['query_certified']-rows['QUERY_FIXED']['stages']['A_RETURN']['query_certified'],
            return_query_fixed_minus_uniform_shared_query_certified=rows['QUERY_FIXED']['stages']['A_RETURN']['query_certified']-rows['UNIFORM_SHARED']['stages']['A_RETURN']['query_certified']))
    physical_probes = sum(item['paid_samples'] for item in probe_ledgers)
    return dict(complete=True, records=len(records), aux_preview_records=len(preview_results),
        methods=methods, life_summaries=life_summaries, paired=paired, conditions=conditions,
        stage_condition_met=all(conditions.values()), physical_source_samples=SOURCE_COST*len(LIVES),
        source_samples_charged_per_arm=SOURCE_COST*len(LIVES), physical_probe_samples=physical_probes,
        new_environment_observations=SOURCE_COST*len(LIVES)+sum(row['spent'] for row in records)+physical_probes,
        risk_violation_scope='all_retained_plans',
        validity_scope='all_retained_plans_and_auxiliary_query_previews',
        model_seconds_scope='summed_process_CPU_planning_acquisition_pool_observation_bank_initialization_begin_b_probe_pool_updates_query_previews_and_shared_acquisition',
        acquisition_seconds_scope='full_choose_process_CPU_subset_of_planning_model_time',
        scientific_gate_changed=False, qualification_only=True)


def prerequisites():
    previous = ROOT/'reports/acquisition_schedule_search_v250'
    run = json.loads((previous/'run.json').read_text())
    analysis = json.loads((previous/'analysis.json').read_text())
    if not run['complete'] or not analysis['valid']:
        raise ValueError('V250 must be complete and independently valid')
    return dict(v250_complete=True, v250_independent_valid=True)


def capture():
    from scripts import audit_query_shared_acquisition_v251
    paths = set(('scripts/run_query_shared_acquisition_v251.py', 'scripts/audit_query_shared_acquisition_v251.py',
        'tests/test_query_shared_acquisition_v251_runner.py', 'tests/test_query_shared_acquisition_v251_audit.py',
        'specs/QUERY_SHARED_ACQUISITION_V251.md'))
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
        a_shared_cap_samples=A_SHARED_CAP, b_fixed_samples=B_SHARED_FIXED, shared_cap_samples=SHARED_CAP,
        public_preview_costs=PUBLIC_COSTS, probe_timing=dict(A='before_target3', B='after_begin_b_before_target30'),
        pool_core_arm='ONE_WAY', query_stream_count=48, query_threshold=960,
        query_delta_per_life_arm='1/20', execution_delta_per_life_arm='1/20', combined_delta_upper='1/10',
        delta_scope='unconditional_complete_life_arm_process', scientific_gate_changed=False,
        qualification_only=True, prerequisites=admitted, computation_cache_scope=COMPUTATION_CACHE_SCOPE,
        worker_jobs=jobs, execution=dict(independent_life_arm_processes=9, max_workers=9,
            posthoc_scoring='after_all_648_decisions_and_all_previews_frozen'),
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
    output(OUTPUT/'interfaces.json', [dict(life=life, identities=bundles[life]['identities'], metadata=bundles[life]['metadata']) for life in LIVES])
    with ProcessPoolExecutor(max_workers=9) as executor:
        futures = [executor.submit(run_life_arm, job['life'], job['arm'], bundles[job['life']]) for job in jobs]
        artifacts = [future.result() for future in futures]
    ledgers = [item['probe_ledger'] for item in artifacts]
    output(OUTPUT/'final_states.json', [dict(life=item['life'], arm=item['arm'], state=item['final_state']) for item in artifacts])
    output(OUTPUT/'probe_ledgers.json', ledgers)
    output(OUTPUT/'a_phase_summaries.json', [dict(life=item['life'], arm=item['arm'], **item['a_phase_summary']) for item in artifacts])
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen', 'all_decisions_and_previews_frozen'], complete=False))
    timings = {scope: {arm: {item['life']: item['timings'][scope] for item in artifacts if item['arm'] == arm} for arm in ARMS} for scope in TIMING_SCOPES}
    output_seconds += sum(item['output_seconds'] for item in artifacts)
    results, preview_results, scoring_seconds = [], [], 0.
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
                output_seconds += write_row(destination, result)
        with (gzip.open(worker_filename('previews', life, arm), 'rt') as source,
              gzip.open(worker_filename('preview_results', life, arm), 'wt') as destination):
            for line in source:
                row = json.loads(line)
                started = perf_counter()
                result = score_preview(row, bundles[life]['laws'][row['identity']])
                scoring_seconds += perf_counter()-started
                preview_results.append(result)
                output_seconds += write_row(destination, result)
    summary = summarize(results, preview_results, timings, ledgers)
    summary.update(elapsed_seconds=perf_counter()-begun, timings=timings,
        life_arm_wall_seconds={arm: {item['life']: item['life_arm_wall_seconds'] for item in artifacts if item['arm'] == arm} for arm in ARMS},
        life_arm_wall_seconds_scope='worker_entry_through_all_decisions_probes_and_previews_retained_before_artifact_write',
        scoring_seconds=scoring_seconds, output_seconds=output_seconds,
        output_seconds_scope='summed_parent_and_worker_write_and_retention_wall_calls_before_final_summary',
        computation_cache_scope=COMPUTATION_CACHE_SCOPE,
        normalizer_cache_statistics={arm: {item['life']: item['normalizer_cache_statistics'] for item in artifacts if item['arm'] == arm} for arm in ARMS},
        source_seconds=source_seconds, source_work=source_work,
        work={arm: sum((Counter(item['work']) for item in artifacts if item['arm'] == arm), Counter()) for arm in ARMS},
        profiles={arm: {item['life']: item['profiles'] for item in artifacts if item['arm'] == arm} for arm in ARMS},
        previews={arm: {item['life']: item['previews'] for item in artifacts if item['arm'] == arm} for arm in ARMS},
        probe_ledgers=ledgers, a_phase_summaries=[dict(life=item['life'], arm=item['arm'], **item['a_phase_summary']) for item in artifacts])
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen', 'all_decisions_and_previews_frozen', 'oracle_evaluated', 'complete'], complete=True))
    print(json.dumps(exact_json(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
