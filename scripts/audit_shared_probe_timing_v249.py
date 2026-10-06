"""Independent full-lifecycle proof and fixed native-A probe timing audit.

Only the established independent V243/V245 arithmetic is reused. Probe
observations continue the original native A streams; settled decisions are
checked at their actual observation time, without optimizer calls.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import json
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_query_allocation_lifecycle_v245 as allocation

prior, paid, evidence = allocation.prior, allocation.paid, allocation.evidence
fractions = allocation.fractions
OUTPUT = ROOT/'reports/shared_probe_timing_v249'
LIVES, ARMS, TARGETS = (0, 1, 2), ('BEFORE_SHARED', 'DEFERRED_SHARED', 'REBUILD'), prior.TARGETS
CORE_ARMS = dict(BEFORE_SHARED='ONE_WAY', DEFERRED_SHARED='ONE_WAY', REBUILD='REBUILD')
OPERATORS, ALPHABETS = allocation.OPERATORS, allocation.ALPHABETS
PROBE_OPERATORS = OPERATORS[:2]
SOURCE_BASE, TARGET_BASE, PROBE_BASE = 288000, 289000, 290000
LIFE_CAPS, SOURCE_COST, PROBE_QUOTA, ROW_QUOTA, BATCH, CAP = (14144, 17072, 17168), 4608, 768, 128, 16, 384
REGRET, THRESHOLD = F(1, 20), 960


def quota(arm):
    return 0 if arm == 'REBUILD' else PROBE_QUOTA


def probe_schedule(arm, identities):
    """Freeze probe visibility independently of outcomes, plans and stopping."""
    if arm == 'REBUILD':
        return []
    if arm == 'BEFORE_SHARED':
        return [(54, identity) for identity in range(3)]
    seen, schedule = set(), []
    for index in range(54, 78):
        identity = identities[index]
        if identity not in seen:
            seen.add(identity)
            schedule.append((index, identity))
    return schedule


def source_replay(rows, check):
    sources, cursor = {}, 0
    for life in LIVES:
        _, laws, _, _ = paid.world(life)
        sources[life] = {}
        for context, indexes, size in (('A', (0, 1, 2), 384), ('B', (27, 28, 29), 128)):
            anchors = []
            for local, index in enumerate(indexes):
                slot = local if context == 'A' else local+3
                anchor = paid.empty()
                for j, operator in enumerate(OPERATORS):
                    seed = SOURCE_BASE+(life*6+slot)*3+j
                    generator = random.Random(seed)
                    for offset in range(0, size, BATCH):
                        increments = paid.draw(generator, laws[index], operator)
                        expected = dict(life=life, context=context, index=index, slot=slot,
                            operator=operator, seed=seed, draw_start=offset,
                            draw_end=offset+BATCH, increments=increments)
                        check('fresh_source_actual_batch_and_offset',
                              cursor < len(rows) and rows[cursor] == expected)
                        cursor += 1
                        for category, count in increments.items():
                            anchor[operator][category] += count
                anchors.append(anchor)
            sources[life][context.lower()] = anchors
    check('all_physical_source_batches_once', cursor == len(rows) == 864)
    return sources


def budget_values(life, arm, index, history, probe_paid, spent=0):
    """Full source/probe reservation is distinct from actually paid samples."""
    source = 3456 if index < 30 else SOURCE_COST
    reserved = quota(arm)
    available = LIFE_CAPS[life]-SOURCE_COST-history-reserved
    return dict(source_paid=source, quota=reserved, available=available,
        pending_probe=reserved-probe_paid, future_source=SOURCE_COST-source,
        reference_paid=source+history+probe_paid+spent,
        adaptive_after=available-spent)


def expected_probe_batches(life, identity, law):
    """Actual representative outcomes, preserving each paired row's cursor."""
    batches = []
    for j, operator in enumerate(PROBE_OPERATORS):
        seed = PROBE_BASE+(life*3+identity)*2+j
        generator = random.Random(seed)
        for offset in range(0, ROW_QUOTA, BATCH):
            batches.append(dict(identity=identity, operator=operator, seed=seed,
                draw_start=offset, draw_end=offset+BATCH,
                increments=paid.draw(generator, law, operator)))
    return batches


def replay_probe_group(rows, life, arm, identity, index, state, law, history, probe_paid, check):
    """Append one fixed paid representative group, with no member/query reset."""
    timing = 'before_target' if arm == 'BEFORE_SHARED' else 'after_target'
    for expected in expected_probe_batches(life, identity, law):
        saved = next(rows)
        operator, increments = expected['operator'], expected['increments']
        pool = state['a'][identity][operator]
        before = deepcopy(pool)
        for category, count in increments.items():
            pool[category] += count
        record = dict(expected, life=life, arm=arm, source_index=identity,
            trigger_index=index, timing=timing, pool_before=before, pool_after=deepcopy(pool),
            probe_paid_before=probe_paid, probe_paid_after=probe_paid+BATCH,
            pending_probe_reserved_before=quota(arm)-probe_paid,
            pending_probe_reserved_after=quota(arm)-probe_paid-BATCH,
            ordinary_history_paid_samples=history, source_paid_samples=SOURCE_COST)
        check('fixed_probe_actual_stream_timing_pool_and_paid_reservation', saved == record)
        probe_paid += BATCH
    return probe_paid


def audit_life_arm(arguments):
    life, arm, sources, cases_saved, interface_saved, state_saved, profile_total = arguments
    begun, checks, failures, location = perf_counter(), Counter(), [], {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    cases, laws, identities, interface = paid.world(life)
    check('predeclared_public_world_and_interface', cases_saved == cases
          and interface_saved == dict(life=life, identities=identities, metadata=interface))
    name = f'life_{life:02d}_{arm}'
    profiles = evidence.read_rows(OUTPUT/f'profiles_{name}.jsonl.gz')
    check('complete_local_profile_numbering',
          [row['profile_id'] for row in profiles] == list(range(len(profiles))))
    profile_decisions, leaves = {}, 0
    for profile in profiles:
        location = dict(life=life, arm=arm, profile_id=profile['profile_id'])
        profile_decisions[profile['profile_id']] = prior.audit_profile(profile, check)
        leaves += len(profile['certificate'].get('leaves', ()))
    state = dict(a=deepcopy(sources['a']), b=None, a_switch=None)
    projection_cache, used_profiles, convex_keys = {}, set(), set()
    results = evidence.read_rows(OUTPUT/f'results_{name}.jsonl.gz')
    records = evidence.read_rows(OUTPUT/f'records_{name}.jsonl.gz')
    probes_saved = [json.loads(line) for line in (OUTPUT/f'probes_{name}.jsonl').read_text().splitlines()]
    probes = iter(probes_saved)
    schedule = probe_schedule(arm, identities)
    history, probe_paid, plans, projections, pre_return_state = 0, 0, 0, 0, None
    observations, acquisitions, work, scored, seen = 0., 0., Counter(), [], set()
    check('complete_fresh_full_lifecycle_records_and_results', len(records) == len(results) == 72)
    for position, index in enumerate(TARGETS):
        location = dict(life=life, arm=arm, index=index)
        if index == 30:
            state['a_switch'], state['b'] = deepcopy(state['a']), deepcopy(sources['b'])
        if index == 54:
            pre_return_state = deepcopy(state)
        if arm == 'BEFORE_SHARED' and index == 54:
            for trigger, probe_identity in schedule:
                probe_paid = replay_probe_group(probes, life, arm, probe_identity, trigger,
                    state, laws[probe_identity], history, probe_paid, check)
        row, case, identity = records[position], cases[index], identities[index]
        seen.add((life, index, arm))
        context, pool_arm = case['context'].lower(), CORE_ARMS[arm]
        pool = state[context][identity]
        check('chronological_target_native_pool_before_and_public_case',
              (row['life'], row['index'], row['arm']) == (life, index, arm)
              and row['case'] == case and row['identity'] == identity and row['pooled_before'] == pool
              and (context != 'b' or state['a'] == state['a_switch']))
        check('nonnegative_model_acquisition_observation_and_output_times',
              all(row[field] >= 0 for field in ('model_seconds', 'acquisition_seconds', 'observation_seconds', 'output_seconds'))
              and row['acquisition_seconds'] <= row['model_seconds'])
        observations += row['observation_seconds']
        acquisitions += row['acquisition_seconds']
        seeds = {operator: TARGET_BASE+(life*78+index)*3+j for j, operator in enumerate(OPERATORS)}
        check('fresh_paired_target_seed_independent_from_probe_streams', row['seeds'] == seeds)
        generators = {operator: random.Random(seed) for operator, seed in seeds.items()}
        member, spent = paid.empty(), 0
        budget = budget_values(life, arm, index, history, probe_paid)
        available = budget['available']

        def plan_check(saved):
            nonlocal plans, projections
            counts = prior.evidence_counts(state, case, identity, pool_arm, interface)
            constraints = prior.execution_constraints(life, index, case, identity,
                sources, state, member, pool_arm, interface)
            previous = checks['terminal_projected_detour_box']
            prior.audit_plan(saved, case, counts, constraints, profiles, profile_decisions,
                             projection_cache, used_profiles, check)
            check('same_native_query_stream_without_B_return_import', saved['return_transfer'] is None)
            projections += checks['terminal_projected_detour_box']-previous
            plans += 1
            work['online_query_comparison_calls'] += 6
            for query in ('goal', 'risk'):
                for reference in saved['query_evidence']['queries'][query]['comparisons']:
                    certificate = profiles[reference['profile_id']]['certificate']
                    if certificate.get('engine') == 'convex_tangent':
                        work['online_convex_certificate_calls'] += 1
                        convex_keys.add((certificate['family'], query, certificate['chosen'],
                            certificate['other'], F(certificate['relevant_cost']),
                            prior.freeze(certificate['projected_counts'])))

        current = row['initial_plan']
        plan_check(current)
        for batch in row['batches']:
            check('joint_stop_member_cap_and_full_source_probe_reservation',
                  spent+BATCH <= min(CAP, available) and not prior.ready(current))
            choice = allocation.original_choice(member, current)
            work['oracle_gap_direct_choices'] += 1
            check('unchanged_exact_V231_allocation_all_fields', fractions(batch['choice']) == choice)
            operator, offset = choice['operator'], sum(member[choice['operator']].values())
            increments = paid.draw(generators[operator], laws[index], operator)
            check('actual_target_outcomes_own_offsets_and_paid_prefix', batch['operator'] == operator
                  and batch['draw_start'] == offset and batch['draw_end'] == offset+BATCH
                  and batch['increments'] == increments)
            for category, count in increments.items():
                member[operator][category] += count
                pool[operator][category] += count
            spent += BATCH
            check('ordinary_current_target_paid_batch_total', batch['spent'] == spent)
            current = batch['plan']
            plan_check(current)
        terminal, completed = row['terminal_plan'], prior.ready(current)
        check('frozen_terminal_is_last_plan_and_exact_stop',
              terminal == current and prior.terminal_stop(spent, available, terminal))
        expected_mix = fractions(terminal['mix']) if completed else [['WAIT', F(1)]]
        check('terminal_member_pool_and_decisions_before_deferred_probe', row['member'] == member
              and row['spent'] == row['current_paid_samples'] == row['new_paid_samples'] == spent == paid.samples(member)
              and row['pooled_after'] == pool and row['execution_certified'] == (F(terminal['utility_lower']) >= 2)
              and row['goal_impossible'] == terminal['goal_impossible'] and row['query_certified'] == terminal['query_ready']
              and row['joint_completed'] == completed and row['fallback'] == (not completed)
              and fractions(row['executed_mix']) == expected_mix)
        check('separate_actual_probe_payment_and_future_reserved_samples',
              row['source_paid_samples'] == budget['source_paid']
              and row['history_paid_samples'] == row['ordinary_history_paid_samples'] == history
              and row['actual_probe_paid_before'] == probe_paid
              and row['pending_probe_reserved'] == budget['pending_probe']
              and row['future_B_source_reserved'] == budget['future_source']
              and row['probe_quota_samples'] == quota(arm)
              and row['total_reference_paid_samples'] == budget['reference_paid']+spent
              and row['life_budget_remaining_before'] == available
              and row['life_budget_remaining_after'] == available-spent
              and row['budget_exhausted'] == (available-spent < BATCH)
              and row['member_cap_exhausted'] == (spent == CAP)
              and 0 <= spent <= min(CAP, available) and spent % BATCH == 0)
        independent = prior.score_history(row, laws[index])
        independent['identity'] = identity
        check('posthoc_truth_scores_all_original_frozen_plans', fractions(results[position]) == independent)
        scored.append(independent)
        history += spent
        if arm == 'DEFERRED_SHARED' and (index, identity) in schedule:
            probe_paid = replay_probe_group(probes, life, arm, identity, index, state,
                laws[identity], history, probe_paid, check)
        print(f'audit life={life} arm={arm} target={index} target_paid={spent} probe_paid={probe_paid}', flush=True)
    check('all_fixed_probe_batches_paid_once_and_no_extra_probe', next(probes, None) is None
          and len(probes_saved) == quota(arm)//BATCH and probe_paid == quota(arm))
    check('all_profiles_referenced_and_complete_local_cohort', len(seen) == 72
          and used_profiles == set(range(len(profiles))) and profile_total == len(profiles))
    check('final_native_banks_sources_switch_and_own_arm', state_saved == dict(
        life=life, arm=pool_arm, a=dict(sources=sources['a'], pools=state['a']),
        b=dict(sources=sources['b'], pools=state['b']),
        a_at_switch=dict(sources=sources['a'], pools=state['a_switch']),
        changed_operator=interface['changed_operator'], b_to_a=interface['b_to_a'], return_merge=None))
    check('whole_lifecycle_actual_cost_respects_full_budget', SOURCE_COST+history+probe_paid <= LIFE_CAPS[life])
    work['online_convex_proposal_calls'] = len(convex_keys)
    work['online_convex_certificate_cache_hits'] = work['online_convex_certificate_calls']-len(convex_keys)
    return dict(life=life, arm=arm, checks=checks, failures=failures, scored=scored,
        ordinary_paid=history, probe_paid=probe_paid, probe_batches=probes_saved,
        pre_return_state=pre_return_state,
        observations=observations, acquisitions=acquisitions, work=work,
        profiles=len(profiles), leaves=leaves, plans=plans, projections=projections,
        elapsed_seconds=perf_counter()-begun)


def conditions(methods):
    before = methods['BEFORE_SHARED']
    result = dict(late_b_quality=before['late_b']['query_certified'] >= 27,
                  a_return_quality=before['a_return']['query_certified'] >= 54)
    for arm in ('DEFERRED_SHARED', 'REBUILD'):
        name, control = arm.lower(), methods[arm]
        result.update({
            f'matched_{name}_late_b_quality': before['late_b']['query_certified'] >= control['late_b']['query_certified'],
            f'matched_{name}_a_return_quality': before['a_return']['query_certified'] >= control['a_return']['query_certified'],
            f'matched_{name}_joint_quality': before['joint_completed'] >= control['joint_completed']})
    result['actual_acquisition_saving_vs_rebuild'] = before['total_samples'] < methods['REBUILD']['total_samples']
    result['actual_acquisition_nondegrading_vs_deferred_shared'] = before['total_samples'] <= methods['DEFERRED_SHARED']['total_samples']
    result['valid_certificates_and_execution'] = all(method[field] == 0 for method in methods.values()
        for field in ('false_query_certificates', 'false_execution_certificates',
            'false_impossible_certificates', 'false_goal_uppers', 'risk_violations', 'executed_risk_violations'))
    return result


def summaries(rows, timings):
    first = {(life, index) for life in LIVES
             for index, _ in probe_schedule('DEFERRED_SHARED', paid.world(life)[2])}
    scopes = ('planning', 'initialization', 'begin_b', 'probe_pool_updates')
    methods, life_summaries = {}, []
    for arm in ARMS:
        selected = [row for row in rows if row['arm'] == arm]
        methods[arm] = dict(prior.aggregate(selected), source_samples=13824,
            probe_samples=quota(arm)*len(LIVES),
            total_samples=13824+quota(arm)*len(LIVES)+sum(row['spent'] for row in selected),
            late_b=prior.aggregate([row for row in selected if 42 <= row['index'] < 54]),
            a_return=prior.aggregate([row for row in selected if row['stage'] == 'A_RETURN']),
            first_return=prior.aggregate([row for row in selected if (row['life'], row['index']) in first]),
            later_return=prior.aggregate([row for row in selected if row['stage'] == 'A_RETURN'
                                         and (row['life'], row['index']) not in first]))
        for scope in scopes+('acquisition',):
            methods[arm][scope+'_seconds'] = sum(timings[scope][arm].values())
        methods[arm]['model_seconds'] = sum(timings[scope][arm][str(life)] for scope in scopes for life in LIVES)
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            life_summaries.append(dict(life=life, arm=arm, source_samples=SOURCE_COST,
                probe_samples=quota(arm),
                total_samples=SOURCE_COST+quota(arm)+sum(row['spent'] for row in subset),
                model_seconds=sum(timings[scope][arm][str(life)] for scope in scopes),
                stages={stage: prior.aggregate([row for row in subset if row['stage'] == stage])
                        for stage in ('A', 'B', 'A_RETURN')},
                first_return=prior.aggregate([row for row in subset if (life, row['index']) in first]),
                later_return=prior.aggregate([row for row in subset if row['stage'] == 'A_RETURN'
                                             and (life, row['index']) not in first])))
    paired = []
    for life in LIVES:
        selected = {row['arm']: row for row in life_summaries if row['life'] == life}
        before, deferred, rebuild = (selected[arm] for arm in ARMS)
        paired.append(dict(life=life,
            deferred_shared_minus_before_shared_samples=deferred['total_samples']-before['total_samples'],
            rebuild_minus_before_shared_samples=rebuild['total_samples']-before['total_samples'],
            return_before_shared_minus_deferred_shared_query_certified=before['stages']['A_RETURN']['query_certified']-
                deferred['stages']['A_RETURN']['query_certified'],
            return_before_shared_minus_deferred_shared_joint_completed=before['stages']['A_RETURN']['joint_completed']-
                deferred['stages']['A_RETURN']['joint_completed']))
    return methods, life_summaries, conditions(methods), paired


def run():
    begun, checks, failures = perf_counter(), Counter(), []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=dict(scope='cohort')))

    read = lambda name: evidence.load(OUTPUT/name)
    metadata, summary = read('run.json'), read('summary.json')
    prerequisite_dir = ROOT/'reports/endpoint_regions_v248'
    prerequisite_run = evidence.load(prerequisite_dir/'run.json')
    prerequisite_audit = evidence.load(prerequisite_dir/'analysis.json')
    check('actual_complete_valid_48_endpoint_96_classification_prerequisite',
          prerequisite_run['complete'] and prerequisite_audit['valid']
          and prerequisite_audit['endpoints'] == 48 and prerequisite_audit['records'] == 96)
    check('frozen_fresh_full_lifecycle_and_global_truth_freeze', metadata['complete']
        and metadata['lives'] == list(LIVES) and metadata['arms'] == list(ARMS)
        and metadata['targets_per_life'] == 72 and metadata['cap'] == CAP and metadata['batch'] == BATCH
        and metadata['source_seed_base'] == SOURCE_BASE and metadata['target_seed_base'] == TARGET_BASE
        and metadata['probe_seed_base'] == PROBE_BASE
        and metadata['per_life_total_budgets'] == list(LIFE_CAPS)
        and metadata['source_samples_per_life'] == SOURCE_COST
        and metadata['query_stream_count'] == 48 and metadata['query_threshold'] == THRESHOLD
        and metadata['query_delta_per_life_arm'] == metadata['execution_delta_per_life_arm'] == '1/20'
        and metadata['combined_delta_upper'] == '1/10' and not metadata['scientific_gate_changed']
        and metadata['qualification_only'] and metadata['pool_core_arm_mapping'] == CORE_ARMS
        and metadata['prerequisites'] == dict(v248_complete=True, v248_independent_valid=True,
            v248_endpoints=48, v248_classifications=96)
        and metadata['phases'] == ['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete']
        and metadata['execution'] == dict(independent_life_arm_processes=9,
            posthoc_scoring='after_all_648_decisions_frozen')
        and metadata['worker_jobs'] == [dict(life=life, arm=arm) for life in LIVES for arm in ARMS]
        and metadata['model_seconds_clock'] == 'process_time'
        and metadata['observation_output_scoring_seconds_clock'] == 'perf_counter')
    check('fixed_public_probe_quantity_operators_and_visibility',
          metadata['probe_samples_per_identity_operator'] == ROW_QUOTA
          and metadata['probe_operators'] == list(PROBE_OPERATORS)
          and metadata['probe_quota_per_life_arm'] == {arm: quota(arm) for arm in ARMS}
          and metadata['probe_timing'] == dict(BEFORE_SHARED='all_before_target54',
              DEFERRED_SHARED='each_identity_after_first_return_decision_frozen', REBUILD='none'))
    check('unchanged_full_process_query_and_execution_event_budgets', F(48, THRESHOLD) == REGRET
          and F(216, 8640)+F(9, 720)+F(9, 720) == REGRET and 2*REGRET == F(1, 10))
    check('isolated_per_life_arm_computation_cache_scope', metadata['computation_cache_scope']
          == summary['computation_cache_scope'] == prior.COMPUTATION_CACHE_SCOPE)
    captured = read('source_manifest.json')
    check('captured_new_runner_auditor_tests_and_frozen_protocol', all(relative in captured for relative in (
        'scripts/run_shared_probe_timing_v249.py', 'scripts/audit_shared_probe_timing_v249.py',
        'tests/test_shared_probe_timing_v249_runner.py', 'tests/test_shared_probe_timing_v249_audit.py',
        'specs/SHARED_PROBE_TIMING_V249.md')))
    for relative in captured:
        check('captured_source_matches_current_bytes',
              (OUTPUT/'source_code'/relative).read_bytes() == (ROOT/relative).read_bytes())
    sources = source_replay(read('source_records.json'), check)
    check('sources_physical_once_before_worker_dispatch',
          read('source_evidence.json') == [dict(life=life, **sources[life]) for life in LIVES])
    cases = {row['life']: row['cases'] for row in read('cases.json')}
    interfaces = {row['life']: row for row in read('interfaces.json')}
    states = {(row['life'], row['arm']): row['state'] for row in read('final_states.json')}
    arguments = [(life, arm, sources[life], cases[life], interfaces[life], states[life, arm],
                  summary['profiles'][arm][str(life)]) for life in LIVES for arm in ARMS]
    with ProcessPoolExecutor(max_workers=9) as executor:
        jobs = list(executor.map(audit_life_arm, arguments))
    for job in jobs:
        checks.update(job['checks'])
        failures.extend(job['failures'])
    scored = [row for job in jobs for row in job['scored']]
    methods, life_summaries, science_conditions, paired = summaries(scored, summary['timings'])
    check('complete_actual_648_decisions_11_conditions_and_full_charged_fees',
          summary['complete'] and summary['records'] == len(scored) == 648
          and summary['methods'] == methods and summary['life_summaries'] == life_summaries
          and summary['paired'] == paired and summary['conditions'] == science_conditions
          and len(science_conditions) == 11 and summary['stage_condition_met'] == all(science_conditions.values())
          and summary['qualification_only'] and not summary['scientific_gate_changed']
          and summary['physical_source_samples'] == summary['source_samples_charged_per_arm'] == 13824
          and summary['physical_probe_samples'] == sum(job['probe_paid'] for job in jobs) == 4608
          and summary['new_environment_observations'] == 13824+4608+sum(row['spent'] for row in scored)
          and summary['risk_violation_scope'] == 'all_retained_plans'
          and summary['model_seconds_scope'] == 'summed_process_CPU_planning_acquisition_pool_observation_bank_initialization_and_probe_pool_updates'
          and summary['acquisition_seconds_scope'] == 'full_choose_process_CPU_subset_of_planning_model_time'
          and summary['output_seconds_scope'] == 'summed_parent_and_worker_write_and_retention_wall_calls_before_final_summary')
    check('nine_worker_wall_times_separate_from_summed_model_cpu',
          summary['life_arm_wall_seconds_scope'] == 'worker_entry_through_all_decisions_and_probes_retained_before_artifact_write'
          and set(summary['life_arm_wall_seconds']) == set(ARMS)
          and all(set(summary['life_arm_wall_seconds'][arm]) == {str(life) for life in LIVES}
                  and all(seconds >= 0 for seconds in summary['life_arm_wall_seconds'][arm].values()) for arm in ARMS))
    for life in LIVES:
        before, deferred = (next(job for job in jobs if job['life'] == life and job['arm'] == arm)
                            for arm in ARMS[:2])
        check('matched_ordinary_pre_return_native_history_and_full_reservation',
              before['pre_return_state'] == deferred['pre_return_state'])
        fields = ('identity', 'operator', 'seed', 'draw_start', 'draw_end', 'increments')
        normalized = lambda job: sorted([{field: row[field] for field in fields}
            for row in job['probe_batches']], key=lambda row: (row['identity'], OPERATORS.index(row['operator']), row['draw_start']))
        check('same_fixed_actual_probe_histograms_without_cross_arm_prefix_read', normalized(before) == normalized(deferred))
    ledgers = []
    for job in jobs:
        first_by_type = {str(identity): index for index, identity
                         in probe_schedule('DEFERRED_SHARED', paid.world(job['life'])[2])}
        ledgers.append(dict(life=job['life'], arm=job['arm'], quota_samples=quota(job['arm']),
            paid_samples=job['probe_paid'], pending_reserved_samples=quota(job['arm'])-job['probe_paid'],
            probe_batches=len(job['probe_batches']), first_return_index_by_type=first_by_type,
            completed_probe_identities=[identity for _, identity in probe_schedule(job['arm'], paid.world(job['life'])[2])]))
    check('actual_final_probe_ledger_first_type_times_and_full_quota',
          read('probe_ledgers.json') == summary['probe_ledgers'] == ledgers)
    check('no_B_native_return_transfer_in_any_arm', summary['return_transfers']
          == [dict(life=life, arm=arm, ledger=None) for life in LIVES for arm in ARMS])
    for arm in ARMS:
        expected_work = sum((job['work'] for job in jobs if job['arm'] == arm), Counter())
        for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
            check('actual_target_and_probe_environment_work', summary['work'][arm][field]
                  == methods[arm]['target_samples']+methods[arm]['probe_samples'])
        for field in ('oracle_gap_direct_choices', 'online_query_comparison_calls', 'online_convex_certificate_calls',
                      'online_convex_proposal_calls', 'online_convex_certificate_cache_hits'):
            check('actual_unchanged_acquisition_and_online_proof_work', summary['work'][arm].get(field, 0) == expected_work[field])
        check('actual_fixed_probe_batch_and_sample_work',
              summary['work'][arm].get('shared_probe_batches', 0) == methods[arm]['probe_samples']//BATCH
              and summary['work'][arm].get('shared_probe_samples', 0) == methods[arm]['probe_samples'])
        for job in (job for job in jobs if job['arm'] == arm):
            life = str(job['life'])
            check('actual_cpu_planning_acquisition_and_wall_target_observation_sums',
                  summary['timings']['planning'][arm][life] == sum(row['model_seconds'] for row in job['scored'])
                  and summary['timings']['acquisition'][arm][life] == job['acquisitions']
                  and summary['timings']['observation'][arm][life] == job['observations'])
            for scope in ('initialization', 'begin_b', 'probe_pool_updates', 'probe_draw'):
                check('nonnegative_bank_switch_probe_update_and_observation_time', summary['timings'][scope][arm][life] >= 0)
            for name, capacity in (('execution', 4096), ('query', 256)):
                stats = summary['normalizer_cache_statistics'][arm][life][name]
                check('isolated_normalizer_cache_statistics', stats['maxsize'] == capacity
                      and 0 <= stats['currsize'] <= min(stats['misses'], capacity) and stats['hits'] >= 0)
    for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
        check('source_environment_work_physical_once', summary['source_work'][field] == 13824)
    result = dict(valid=not failures, complete=True, records=len(scored),
        probe_batches=sum(len(job['probe_batches']) for job in jobs),
        plans=sum(job['plans'] for job in jobs), independently_checked_profiles=sum(job['profiles'] for job in jobs),
        independently_checked_global_leaves=sum(job['leaves'] for job in jobs),
        independently_checked_execution_projections=sum(job['projections'] for job in jobs),
        methods=methods, conditions=science_conditions, stage_condition_met=all(science_conditions.values()),
        physical_source_samples=13824, physical_probe_samples=4608,
        physical_observations=13824+4608+sum(row['spent'] for row in scored),
        risk_violation_scope='all_retained_plans', binary_projection_comparison_tolerance=0,
        independent_life_arm_processes=9,
        life_arm_elapsed_seconds={f'{job["life"]}/{job["arm"]}': job['elapsed_seconds'] for job in jobs},
        checks=dict(checks), failures=failures, elapsed_seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
