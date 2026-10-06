"""Frozen eight-plan exploration of full-lifecycle acquisition feasibility.

All 24 cold life/plan jobs retain decisions before any truth-based scoring.
Selection is exploratory and carries no postselection coverage guarantee.
"""
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
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_reuse_rebuild_lifecycle_v242 import retain_plan, evaluate
from scripts.run_shared_probe_timing_v249 import (activate_cold_caches,
    method_aggregate, COMPUTATION_CACHE_SCOPE, TIMING_SCOPES, MODEL_SCOPES)

OUTPUT = ROOT/'reports/acquisition_schedule_search_v250'
SOURCE_DIRECTORY = ROOT/'reports/shared_probe_timing_v249'
LIVES, TARGETS = (0, 1, 2), tuple(range(3, 27))+tuple(range(30, 78))
OPERATORS, ALPHABETS = core.OPERATORS, core.ALPHABETS
SOURCE_BASE, TARGET_BASE, PROBE_BASE = 288000, 289000, 294000
TOTAL_BUDGETS, SOURCE_COST, CAP, BATCH = (14144, 17072, 17168), 4608, 384, 16
PLANS = tuple(dict(candidate=f'{family}_B{b}', order=2*i+j, a_family=family,
    a_row_samples={op: amount if op != OPERATORS[2] or family == 'ALL512' else 0 for op in OPERATORS},
    b_changed_row_samples=b, quota_samples=3*(amount*(3 if family == 'ALL512' else 2)+b))
    for i, (family, amount) in enumerate((('SD128', 128), ('SD512', 512), ('SD1024', 1024), ('ALL512', 512)))
    for j, b in enumerate((0, 384)))
PLAN_IDS = tuple(plan['candidate'] for plan in PLANS)
ERROR_FIELDS = ('false_query_certificates', 'false_execution_certificates',
    'false_impossible_certificates', 'false_goal_uppers', 'risk_violations', 'executed_risk_violations')


def worker_filename(kind, life, candidate):
    ending = '.jsonl' if kind == 'probes' else '.jsonl.gz'
    return OUTPUT/f'{kind}_life_{life:02d}_{candidate}{ending}'


def run_target(life, index, case, identity, state, plan_spec, law, work,
               source_paid_samples, history_paid_samples, actual_probe_paid_before,
               query_cache, profile_stream, profile_ids):
    seeds = {op: TARGET_BASE+(life*78+index)*3+j for j, op in enumerate(OPERATORS)}
    generators = {op: random.Random(seed) for op, seed in seeds.items()}
    member, spent = core.empty(), 0
    model_seconds, acquisition_seconds, observation_seconds, output_seconds = 0., 0., 0., 0.
    bank = 'a' if case['context'] == 'A' else 'b'
    before, quota = deepcopy(state[bank]['pools'][identity]), plan_spec['quota_samples']
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
    completed, candidate = core.ready(plan), plan_spec['candidate']
    return dict(life=life, index=index, case=deepcopy(case), identity=identity, arm=candidate,
        candidate=candidate, seeds=seeds, initial_plan=initial, batches=batches,
        terminal_plan=terminal, spent=spent, member=deepcopy(member), pooled_before=before,
        pooled_after=deepcopy(state[bank]['pools'][identity]),
        source_paid_samples=source_paid_samples, history_paid_samples=history_paid_samples,
        ordinary_history_paid_samples=history_paid_samples, actual_probe_paid_before=actual_probe_paid_before,
        pending_probe_reserved=quota-actual_probe_paid_before,
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


def context_probes(life, plan_spec, context, state, bundle, ordinary_paid, probe_paid,
                   work, stream, generators, offsets):
    bank, slot = ('a', 0) if context == 'A' else ('b', 1)
    trigger_index, source_paid = (3, 3456) if context == 'A' else (30, SOURCE_COST)
    amounts = (plan_spec['a_row_samples'] if context == 'A' else
        {op: plan_spec['b_changed_row_samples'] if op == bundle['metadata']['changed_operator'] else 0
         for op in OPERATORS})
    candidate, quota = plan_spec['candidate'], plan_spec['quota_samples']
    model_seconds, observation_seconds, output_seconds, batches = 0., 0., 0., 0
    for identity in range(3):
        source_index = identity if context == 'A' else 27+identity
        for j, operator in enumerate(OPERATORS):
            key = (context, identity, operator)
            seed = PROBE_BASE+(life*6+slot*3+identity)*3+j
            generators[key], offsets[key] = random.Random(seed), 0
            for start in range(0, amounts[operator], BATCH):
                increments = dict.fromkeys(ALPHABETS[operator], 0)
                progress = dict(draw_end=offsets[key], n=offsets[key])
                before = deepcopy(state[bank]['pools'][identity][operator])
                begun = perf_counter()
                draw(generators[key], bundle['laws'][source_index], operator, increments, BATCH, work, progress)
                observation_seconds += perf_counter()-begun
                begun = process_time()
                core.observe(state, bundle['cases'][source_index], identity, operator, increments)
                model_seconds += process_time()-begun
                row = dict(life=life, arm=candidate, candidate=candidate, context=context,
                    identity=identity, source_index=source_index, operator=operator, seed=seed,
                    draw_start=start, draw_end=progress['draw_end'], increments=increments,
                    trigger_index=trigger_index, timing='before_target', pool_before=before,
                    pool_after=deepcopy(state[bank]['pools'][identity][operator]),
                    probe_paid_before=probe_paid, probe_paid_after=probe_paid+BATCH,
                    pending_probe_reserved_before=quota-probe_paid,
                    pending_probe_reserved_after=quota-probe_paid-BATCH,
                    ordinary_history_paid_samples=ordinary_paid, source_paid_samples=source_paid)
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


def run_life_plan(life, plan_spec, bundle):
    """Cold per-job state and caches even when a process runs a later plan."""
    begun, candidate = perf_counter(), plan_spec['candidate']
    normalizers, query_cache, work = activate_cold_caches(), {}, Counter()
    timings = dict.fromkeys(TIMING_SCOPES, 0.)
    started = process_time()
    state = core.prepare(bundle['a'], life, 'ONE_WAY', work)
    timings['initialization'] += process_time()-started
    paid, probe_paid, probe_batches, output_seconds = 0, 0, 0, 0.
    by_context, generators, offsets, profile_ids = {}, {}, {}, {}
    with (gzip.open(worker_filename('records', life, candidate), 'wt') as stream,
          gzip.open(worker_filename('profiles', life, candidate), 'wt') as profiles,
          worker_filename('probes', life, candidate).open('w') as probes):

        def probe(context):
            nonlocal probe_paid, probe_batches, output_seconds
            before = probe_paid
            result = context_probes(life, plan_spec, context, state, bundle, paid, probe_paid,
                work, probes, generators, offsets)
            probe_paid, probe_batches = result['paid_samples'], probe_batches+result['batches']
            by_context[context] = probe_paid-before
            timings['probe_pool_updates'] += result['model_seconds']
            timings['probe_draw'] += result['observation_seconds']
            output_seconds += result['output_seconds']

        probe('A')
        for index in TARGETS:
            if index == 30:
                started = process_time()
                metadata = bundle['metadata']
                core.begin_b(state, bundle['b'], metadata['changed_operator'], metadata['b_to_a'], work)
                timings['begin_b'] += process_time()-started
                probe('B')
            row = run_target(life, index, bundle['cases'][index], bundle['identities'][index],
                state, plan_spec, bundle['laws'][index], work, 3456 if index < 30 else SOURCE_COST,
                paid, probe_paid, query_cache, profiles, profile_ids)
            for scope, field in (('planning', 'model_seconds'), ('acquisition', 'acquisition_seconds'),
                                 ('observation', 'observation_seconds')):
                timings[scope] += row[field]
            output_seconds += row['output_seconds']
            paid += row['spent']
            started = perf_counter()
            stream.write(json.dumps(exact_json(row), separators=(',', ':'))+'\n')
            stream.flush()
            profiles.flush()
            output_seconds += perf_counter()-started
            print(f'life={life} candidate={candidate} target={index} spent={row["spent"]} '
                f'query={row["query_certified"]} joint={row["joint_completed"]} '
                f'ordinary_paid={paid} probe_paid={probe_paid}', flush=True)
    artifact = dict(life=life, arm=candidate, candidate=candidate, final_state=deepcopy(state),
        timings=timings, work=work, profiles=len(profile_ids),
        probe_ledger=dict(life=life, arm=candidate, candidate=candidate,
            quota_samples=plan_spec['quota_samples'], paid_samples=probe_paid,
            pending_reserved_samples=plan_spec['quota_samples']-probe_paid,
            probe_batches=probe_batches, by_context=by_context),
        normalizer_cache_statistics={name: function.cache_info()._asdict() for name, function in normalizers.items()},
        life_plan_wall_seconds=perf_counter()-begun)
    started = perf_counter()
    save(OUTPUT/f'worker_artifacts_life_{life:02d}_{candidate}.json', artifact)
    output_seconds += perf_counter()-started
    return dict(artifact, output_seconds=output_seconds)


def winner(candidates, field):
    eligible = [item for item in candidates if item[field]]
    return (min(eligible, key=lambda item: (item['total_samples'], -item['joint_completed'], item['order']))['candidate']
            if eligible else None)


def summarize(records, timings):
    candidates, life_summaries = [], []
    for plan_spec in PLANS:
        candidate, quota = plan_spec['candidate'], plan_spec['quota_samples']
        selected = [row for row in records if row['arm'] == candidate]
        method = dict(method_aggregate(selected), candidate=candidate, order=plan_spec['order'],
            a_family=plan_spec['a_family'], b_changed_row_samples=plan_spec['b_changed_row_samples'],
            source_samples=SOURCE_COST*len(LIVES), probe_samples=quota*len(LIVES),
            total_samples=(SOURCE_COST+quota)*len(LIVES)+sum(row['spent'] for row in selected),
            late_b=method_aggregate([row for row in selected if 42 <= row['index'] < 54]),
            a_return=method_aggregate([row for row in selected if row['stage'] == 'A_RETURN']))
        method['model_seconds'] = sum(timings[scope][candidate][life] for scope in MODEL_SCOPES for life in LIVES)
        for scope in MODEL_SCOPES+('acquisition',):
            method[scope+'_seconds'] = sum(timings[scope][candidate].values())
        budgets = []
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            total = SOURCE_COST+quota+sum(row['spent'] for row in subset)
            budget_valid = total <= TOTAL_BUDGETS[life]
            budgets.append(budget_valid)
            life_summaries.append(dict(life=life, arm=candidate, candidate=candidate,
                source_samples=SOURCE_COST, probe_samples=quota, total_samples=total, budget_valid=budget_valid,
                model_seconds=sum(timings[scope][candidate][life] for scope in MODEL_SCOPES),
                stages={stage: method_aggregate([row for row in subset if row['stage'] == stage]) for stage in task.STAGES}))
        feasible = dict(late_b_quality=method['late_b']['query_certified'] >= 27,
            a_return_quality=method['a_return']['query_certified'] >= 54,
            per_life_budget_valid=all(budgets), valid_certificates_and_execution=all(method[field] == 0 for field in ERROR_FIELDS))
        qualification = dict(feasible, whole_lifecycle_joint_quality=method['joint_completed'] >= 132,
                             whole_charged_cost=method['total_samples'] <= 47792)
        method.update(budget_quality_conditions=feasible, budget_quality_feasible=all(feasible.values()),
            qualification_conditions=qualification, qualification_witness=all(qualification.values()))
        candidates.append(method)
    return dict(complete=True, records=len(records), candidates=candidates, life_summaries=life_summaries,
        selected=winner(candidates, 'qualification_witness'),
        budget_quality_witness=winner(candidates, 'budget_quality_feasible'),
        physical_source_samples=0, inherited_source_samples=SOURCE_COST*len(LIVES),
        inherited_source_samples_charged_per_candidate=SOURCE_COST*len(LIVES),
        physical_probe_samples=sum(plan['quota_samples'] for plan in PLANS)*len(LIVES),
        ordinary_search_samples=sum(row['spent'] for row in records),
        new_environment_observations=sum(row['spent'] for row in records)+sum(plan['quota_samples'] for plan in PLANS)*len(LIVES),
        total_search_model_seconds=sum(item['model_seconds'] for item in candidates),
        risk_violation_scope='all_retained_plans', exploratory_search=True,
        model_seconds_scope='summed_process_CPU_planning_acquisition_pool_observation_bank_initialization_and_probe_pool_updates',
        acquisition_seconds_scope='full_choose_process_CPU_subset_of_planning_model_time',
        scientific_gate_changed=False, post_selection_coverage_guarantee=None,
        selected_guarantee_claimed=False)


def prerequisites():
    run = json.loads((SOURCE_DIRECTORY/'run.json').read_text())
    analysis = json.loads((SOURCE_DIRECTORY/'analysis.json').read_text())
    if not run['complete'] or not analysis['valid']:
        raise ValueError('V249 must be complete and independently valid')
    return dict(v249_complete=True, v249_independent_valid=True)


def capture():
    from scripts import audit_acquisition_schedule_search_v250
    paths = set(('scripts/run_acquisition_schedule_search_v250.py', 'scripts/audit_acquisition_schedule_search_v250.py',
        'tests/test_acquisition_schedule_search_v250_runner.py', 'tests/test_acquisition_schedule_search_v250_audit.py',
        'specs/ACQUISITION_SCHEDULE_SEARCH_V250.md'))
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

    jobs = [dict(life=life, candidate=plan['candidate']) for life in LIVES for plan in PLANS]
    protocol = dict(lives=LIVES, plans=PLANS, targets_per_life=72, cap=CAP, batch=BATCH,
        source_seed_base=SOURCE_BASE, target_seed_base=TARGET_BASE, probe_seed_base=PROBE_BASE,
        per_life_total_budgets=TOTAL_BUDGETS, source_samples_per_life=SOURCE_COST,
        source_reference='shared_probe_timing_v249', physical_new_source_samples=0,
        probe_timing=dict(A='before_target3', B='after_begin_b_before_target30'),
        pool_core_arm='ONE_WAY', query_stream_count=48, query_threshold=960,
        nominal_query_delta_per_life_trajectory='1/20', nominal_execution_delta_per_life_trajectory='1/20',
        nominal_combined_delta_upper='1/10', post_selection_coverage_guarantee=None,
        selected_guarantee_claimed=False, exploratory_search=True, scientific_gate_changed=False,
        qualification_reference=dict(late_b_query_minimum=27, return_query_minimum=54,
            whole_lifecycle_joint_minimum=132, whole_charged_cost_maximum=47792),
        selection_order=['total_samples_ascending', 'joint_completed_descending', 'declared_candidate_order'],
        prerequisites=admitted, computation_cache_scope=COMPUTATION_CACHE_SCOPE,
        worker_jobs=jobs, execution=dict(cold_life_plan_jobs=24, max_workers=8,
            posthoc_scoring='after_all_1728_decisions_frozen'),
        model_seconds_clock='process_time', observation_output_scoring_seconds_clock='perf_counter',
        oracle_information=['type identity', 'B changed operator', 'B-to-A correspondence'])
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen'], complete=False))
    started = perf_counter()
    capture()
    output_seconds += perf_counter()-started
    source_evidence = json.loads((SOURCE_DIRECTORY/'source_evidence.json').read_text())
    cases = json.loads((SOURCE_DIRECTORY/'cases.json').read_text())
    interfaces = json.loads((SOURCE_DIRECTORY/'interfaces.json').read_text())
    bundles = {}
    for life in LIVES:
        anchors = next(item for item in source_evidence if item['life'] == life)
        public_cases = next(item['cases'] for item in cases if item['life'] == life)
        interface = next(item for item in interfaces if item['life'] == life)
        bundles[life] = dict(a=anchors['a'], b=anchors['b'], cases=public_cases,
            laws=task.world(life)[1], identities=interface['identities'], metadata=interface['metadata'])
    output(OUTPUT/'source_evidence.json', source_evidence)
    output(OUTPUT/'source_reference.json', dict(directory='shared_probe_timing_v249',
        retained_records='source_records.json', retained_evidence='source_evidence.json',
        inherited_samples=SOURCE_COST*len(LIVES), physical_new_samples=0))
    output(OUTPUT/'cases.json', cases)
    output(OUTPUT/'interfaces.json', interfaces)
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(run_life_plan, life, plan, bundles[life]) for life in LIVES for plan in PLANS]
        artifacts = [future.result() for future in futures]
    output(OUTPUT/'final_states.json', [dict(life=item['life'], arm=item['arm'], candidate=item['candidate'],
        state=item['final_state']) for item in artifacts])
    output(OUTPUT/'probe_ledgers.json', [item['probe_ledger'] for item in artifacts])
    output(OUTPUT/'run.json', dict(protocol, phases=['protocol_frozen', 'all_decisions_frozen'], complete=False))
    timings = {scope: {candidate: {item['life']: item['timings'][scope] for item in artifacts if item['candidate'] == candidate}
        for candidate in PLAN_IDS} for scope in TIMING_SCOPES}
    output_seconds += sum(item['output_seconds'] for item in artifacts)
    results, scoring_seconds = [], 0.
    for job in jobs:
        life, candidate = job['life'], job['candidate']
        with (gzip.open(worker_filename('records', life, candidate), 'rt') as source,
              gzip.open(worker_filename('results', life, candidate), 'wt') as destination):
            for line in source:
                row = json.loads(line)
                started = perf_counter()
                result = evaluate(row, bundles[life]['laws'][row['index']])
                scoring_seconds += perf_counter()-started
                result.update(identity=row['identity'], candidate=candidate)
                results.append(result)
                started = perf_counter()
                destination.write(json.dumps(exact_json(result), separators=(',', ':'))+'\n')
                output_seconds += perf_counter()-started
    summary = summarize(results, timings)
    summary.update(elapsed_seconds=perf_counter()-begun, timings=timings,
        life_plan_wall_seconds={candidate: {item['life']: item['life_plan_wall_seconds'] for item in artifacts
            if item['candidate'] == candidate} for candidate in PLAN_IDS},
        life_plan_wall_seconds_scope='worker_entry_through_all_decisions_and_probes_retained_before_artifact_write',
        scoring_seconds=scoring_seconds, output_seconds=output_seconds,
        output_seconds_scope='summed_parent_and_worker_write_and_retention_wall_calls_before_final_summary',
        computation_cache_scope=COMPUTATION_CACHE_SCOPE,
        normalizer_cache_statistics={candidate: {item['life']: item['normalizer_cache_statistics']
            for item in artifacts if item['candidate'] == candidate} for candidate in PLAN_IDS},
        work={candidate: sum((Counter(item['work']) for item in artifacts if item['candidate'] == candidate), Counter())
            for candidate in PLAN_IDS},
        profiles={candidate: {item['life']: item['profiles'] for item in artifacts if item['candidate'] == candidate}
            for candidate in PLAN_IDS}, probe_ledgers=[item['probe_ledger'] for item in artifacts])
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol,
        phases=['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'], complete=True))
    print(json.dumps(exact_json(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
