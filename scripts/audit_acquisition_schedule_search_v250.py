"""Independent audit of the eight frozen exploratory acquisition schedules.

All candidates are replayed separately with native A/B evidence, complete
fees, and the established independent proof arithmetic. A selected witness
does not acquire a postselection coverage guarantee from this audit.
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
OUTPUT = ROOT/'reports/acquisition_schedule_search_v250'
SOURCE = ROOT/'reports/shared_probe_timing_v249'
LIVES, TARGETS = (0, 1, 2), prior.TARGETS
PLAN_IDS = ('SD128_B0', 'SD128_B384', 'SD512_B0', 'SD512_B384',
            'SD1024_B0', 'SD1024_B384', 'ALL512_B0', 'ALL512_B384')
PLAN_PARAMETERS = ((128, 2, 0), (128, 2, 384), (512, 2, 0), (512, 2, 384),
                   (1024, 2, 0), (1024, 2, 384), (512, 3, 0), (512, 3, 384))
OPERATORS, ALPHABETS = allocation.OPERATORS, allocation.ALPHABETS
SOURCE_BASE, TARGET_BASE, PROBE_BASE = 288000, 289000, 294000
LIFE_CAPS, SOURCE_COST, BATCH, CAP = (14144, 17072, 17168), 4608, 16, 384
REGRET, THRESHOLD = F(1, 20), 960


def parameters(candidate):
    return PLAN_PARAMETERS[PLAN_IDS.index(candidate)]


def quota(candidate):
    amount, rows, changed = parameters(candidate)
    return 3*(amount*rows+changed)


def probe_schedule(candidate, changed_operator):
    amount, rows, changed = parameters(candidate)
    schedule = [(3, 'A', identity, {operator: amount for operator in OPERATORS[:rows]})
                for identity in range(3)]
    if changed:
        schedule.extend((30, 'B', identity, {changed_operator: changed}) for identity in range(3))
    return schedule


def retained_sources(rows, check):
    """Sum settled V249 observations without redrawing their source streams."""
    sources = {life: {context: [paid.empty() for _ in range(3)]
                     for context in ('a', 'b')} for life in LIVES}
    cursor = 0
    for life in LIVES:
        for context, indexes, size in (('A', (0, 1, 2), 384), ('B', (27, 28, 29), 128)):
            for local, index in enumerate(indexes):
                slot = local if context == 'A' else local+3
                anchor = sources[life][context.lower()][local]
                for j, operator in enumerate(OPERATORS):
                    seed = SOURCE_BASE+(life*6+slot)*3+j
                    for offset in range(0, size, BATCH):
                        saved = rows[cursor]
                        increments = saved['increments']
                        expected = dict(life=life, context=context, index=index, slot=slot,
                            operator=operator, seed=seed, draw_start=offset,
                            draw_end=offset+BATCH, increments=increments)
                        check('settled_source_record_identity_and_paid_batch', saved == expected
                              and set(increments) == set(ALPHABETS[operator])
                              and all(count >= 0 for count in increments.values())
                              and sum(increments.values()) == BATCH)
                        cursor += 1
                        for category, count in increments.items():
                            anchor[operator][category] += count
    check('all_settled_sources_reused_without_new_physical_draw', cursor == len(rows) == 864)
    return sources


def budget_values(life, candidate, index, history, probe_paid, spent=0):
    """Full source/probe reservation is distinct from actually paid samples."""
    source = 3456 if index < 30 else SOURCE_COST
    reserved = quota(candidate)
    available = LIFE_CAPS[life]-SOURCE_COST-history-reserved
    return dict(source_paid=source, quota=reserved, available=available,
        pending_probe=reserved-probe_paid, future_source=SOURCE_COST-source,
        reference_paid=source+history+probe_paid+spent,
        adaptive_after=available-spent)


def expected_probe_batches(life, context, identity, amounts, law):
    """Actual representative outcomes, preserving each paired row's cursor."""
    batches = []
    context_slot = 0 if context == 'A' else 1
    for j, operator in enumerate(OPERATORS):
        if operator not in amounts:
            continue
        seed = PROBE_BASE+(life*6+context_slot*3+identity)*3+j
        generator = random.Random(seed)
        for offset in range(0, amounts[operator], BATCH):
            batches.append(dict(context=context, identity=identity, operator=operator, seed=seed,
                draw_start=offset, draw_end=offset+BATCH,
                increments=paid.draw(generator, law, operator)))
    return batches


def replay_probe_group(rows, life, candidate, context, identity, index, amounts,
                       state, law, history, probe_paid, check):
    """Append one fixed paid representative group, with no member/query reset."""
    source_index = identity if context == 'A' else 27+identity
    source_paid = 3456 if context == 'A' else SOURCE_COST
    for expected in expected_probe_batches(life, context, identity, amounts, law):
        saved = next(rows)
        operator, increments = expected['operator'], expected['increments']
        pool = state[context.lower()][identity][operator]
        before = deepcopy(pool)
        for category, count in increments.items():
            pool[category] += count
        record = dict(expected, life=life, arm=candidate, candidate=candidate, source_index=source_index,
            trigger_index=index, timing='before_target', pool_before=before, pool_after=deepcopy(pool),
            probe_paid_before=probe_paid, probe_paid_after=probe_paid+BATCH,
            pending_probe_reserved_before=quota(candidate)-probe_paid,
            pending_probe_reserved_after=quota(candidate)-probe_paid-BATCH,
            ordinary_history_paid_samples=history, source_paid_samples=source_paid)
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
    schedule = probe_schedule(arm, interface['changed_operator'])
    history, probe_paid, plans, projections = 0, 0, 0, 0
    observations, acquisitions, work, scored, seen = 0., 0., Counter(), [], set()
    check('complete_fresh_full_lifecycle_records_and_results', len(records) == len(results) == 72)
    for position, index in enumerate(TARGETS):
        location = dict(life=life, arm=arm, index=index)
        if index == 30:
            state['a_switch'], state['b'] = deepcopy(state['a']), deepcopy(sources['b'])
        for trigger, probe_context, probe_identity, amounts in schedule:
            if index == trigger:
                source_index = probe_identity if probe_context == 'A' else 27+probe_identity
                probe_paid = replay_probe_group(probes, life, arm, probe_context, probe_identity, trigger,
                    amounts, state, laws[source_index], history, probe_paid, check)
        row, case, identity = records[position], cases[index], identities[index]
        seen.add((life, index, arm))
        context, pool_arm = case['context'].lower(), 'ONE_WAY'
        pool = state[context][identity]
        check('chronological_target_native_pool_before_and_public_case',
              (row['life'], row['index'], row['arm']) == (life, index, arm)
              and row['candidate'] == arm and row['case'] == case
              and row['identity'] == identity and row['pooled_before'] == pool
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
        independent.update(identity=identity, candidate=arm)
        check('posthoc_truth_scores_all_original_frozen_plans', fractions(results[position]) == independent)
        scored.append(independent)
        history += spent
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
        observations=observations, acquisitions=acquisitions, work=work,
        profiles=len(profiles), leaves=leaves, plans=plans, projections=projections,
        elapsed_seconds=perf_counter()-begun)



def literal_plans():
    return [dict(candidate=candidate, order=order,
        a_family=('SD' if rows == 2 else 'ALL')+str(amount),
        a_row_samples={operator: amount if j < rows else 0 for j, operator in enumerate(OPERATORS)},
        b_changed_row_samples=changed, quota_samples=quota(candidate))
        for order, (candidate, (amount, rows, changed)) in enumerate(zip(PLAN_IDS, PLAN_PARAMETERS))]


def conditions(method, budgets):
    quality = dict(late_b_quality=method['late_b']['query_certified'] >= 27,
        a_return_quality=method['a_return']['query_certified'] >= 54,
        per_life_budget_valid=all(budgets),
        valid_certificates_and_execution=all(method[field] == 0 for field in (
            'false_query_certificates', 'false_execution_certificates', 'false_impossible_certificates',
            'false_goal_uppers', 'risk_violations', 'executed_risk_violations')))
    qualification = dict(quality, whole_lifecycle_joint_quality=method['joint_completed'] >= 132,
                         whole_charged_cost=method['total_samples'] <= 47792)
    return quality, qualification


def winner(candidates, field):
    eligible = [item for item in candidates if item[field]]
    if not eligible:
        return None
    return min(eligible, key=lambda item: (item['total_samples'], -item['joint_completed'],
                                           PLAN_IDS.index(item['candidate'])))['candidate']


def summaries(rows, timings):
    scopes = ('planning', 'initialization', 'begin_b', 'probe_pool_updates')
    candidates, life_summaries = [], []
    for order, candidate in enumerate(PLAN_IDS):
        amount, operators, changed = parameters(candidate)
        selected = [row for row in rows if row['arm'] == candidate]
        method = dict(prior.aggregate(selected), candidate=candidate, order=order,
            a_family=('SD' if operators == 2 else 'ALL')+str(amount), b_changed_row_samples=changed,
            source_samples=13824, probe_samples=quota(candidate)*len(LIVES),
            total_samples=13824+quota(candidate)*len(LIVES)+sum(row['spent'] for row in selected),
            late_b=prior.aggregate([row for row in selected if 42 <= row['index'] < 54]),
            a_return=prior.aggregate([row for row in selected if row['stage'] == 'A_RETURN']))
        method['model_seconds'] = sum(timings[scope][candidate][str(life)] for scope in scopes for life in LIVES)
        for scope in scopes+('acquisition',):
            method[scope+'_seconds'] = sum(timings[scope][candidate].values())
        budgets = []
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            total = SOURCE_COST+quota(candidate)+sum(row['spent'] for row in subset)
            budget_valid = total <= LIFE_CAPS[life]
            budgets.append(budget_valid)
            life_summaries.append(dict(life=life, arm=candidate, candidate=candidate,
                source_samples=SOURCE_COST, probe_samples=quota(candidate), total_samples=total,
                budget_valid=budget_valid,
                model_seconds=sum(timings[scope][candidate][str(life)] for scope in scopes),
                stages={stage: prior.aggregate([row for row in subset if row['stage'] == stage])
                        for stage in ('A', 'B', 'A_RETURN')}))
        quality, qualification = conditions(method, budgets)
        method.update(budget_quality_conditions=quality, budget_quality_feasible=all(quality.values()),
            qualification_conditions=qualification, qualification_witness=all(qualification.values()))
        candidates.append(method)
    return candidates, life_summaries


def run():
    begun, checks, failures = perf_counter(), Counter(), []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=dict(scope='search')))

    read = lambda name: evidence.load(OUTPUT/name)
    metadata, summary = read('run.json'), read('summary.json')
    previous_run, previous_analysis = evidence.load(SOURCE/'run.json'), evidence.load(SOURCE/'analysis.json')
    check('complete_independently_valid_settled_source_prerequisite', previous_run['complete']
          and previous_analysis['valid'] and previous_run['source_seed_base'] == SOURCE_BASE)
    plans = literal_plans()
    check('literal_eight_full_lifecycle_plans_and_complete_global_truth_freeze', metadata['complete']
        and metadata['lives'] == list(LIVES) and metadata['plans'] == plans
        and metadata['targets_per_life'] == 72 and metadata['cap'] == CAP and metadata['batch'] == BATCH
        and metadata['source_seed_base'] == SOURCE_BASE and metadata['target_seed_base'] == TARGET_BASE
        and metadata['probe_seed_base'] == PROBE_BASE
        and metadata['per_life_total_budgets'] == list(LIFE_CAPS)
        and metadata['source_samples_per_life'] == SOURCE_COST
        and metadata['source_reference'] == 'shared_probe_timing_v249' and metadata['physical_new_source_samples'] == 0
        and metadata['pool_core_arm'] == 'ONE_WAY'
        and metadata['probe_timing'] == dict(A='before_target3', B='after_begin_b_before_target30')
        and metadata['prerequisites'] == dict(v249_complete=True, v249_independent_valid=True)
        and metadata['phases'] == ['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete']
        and metadata['worker_jobs'] == [dict(life=life, candidate=candidate) for life in LIVES for candidate in PLAN_IDS]
        and metadata['execution'] == dict(cold_life_plan_jobs=24, max_workers=8,
            posthoc_scoring='after_all_1728_decisions_frozen')
        and metadata['model_seconds_clock'] == 'process_time'
        and metadata['observation_output_scoring_seconds_clock'] == 'perf_counter')
    check('fixed_quality_qualification_and_independent_selection_rules',
          metadata['qualification_reference'] == dict(late_b_query_minimum=27, return_query_minimum=54,
              whole_lifecycle_joint_minimum=132, whole_charged_cost_maximum=47792)
          and metadata['selection_order'] == ['total_samples_ascending', 'joint_completed_descending', 'declared_candidate_order'])
    check('unchanged_nominal_events_without_postselected_coverage_claim',
          metadata['query_stream_count'] == 48 and metadata['query_threshold'] == THRESHOLD
          and metadata['nominal_query_delta_per_life_trajectory'] == metadata['nominal_execution_delta_per_life_trajectory'] == '1/20'
          and metadata['nominal_combined_delta_upper'] == '1/10'
          and F(48, THRESHOLD) == REGRET and F(216, 8640)+F(9, 720)+F(9, 720) == REGRET
          and metadata['post_selection_coverage_guarantee'] is None and not metadata['selected_guarantee_claimed']
          and metadata['exploratory_search'] and not metadata['scientific_gate_changed'])
    check('isolated_per_life_plan_computation_cache_scope', metadata['computation_cache_scope']
          == summary['computation_cache_scope'] == prior.COMPUTATION_CACHE_SCOPE)
    captured = read('source_manifest.json')
    check('captured_new_search_auditor_tests_and_frozen_literal_protocol', all(relative in captured for relative in (
        'scripts/run_acquisition_schedule_search_v250.py', 'scripts/audit_acquisition_schedule_search_v250.py',
        'tests/test_acquisition_schedule_search_v250_runner.py', 'tests/test_acquisition_schedule_search_v250_audit.py',
        'specs/ACQUISITION_SCHEDULE_SEARCH_V250.md')))
    for relative in captured:
        check('captured_source_matches_current_bytes',
              (OUTPUT/'source_code'/relative).read_bytes() == (ROOT/relative).read_bytes())
    sources = retained_sources(evidence.load(SOURCE/'source_records.json'), check)
    check('settled_source_banks_reused_without_new_sampling',
          read('source_evidence.json') == evidence.load(SOURCE/'source_evidence.json')
          == [dict(life=life, **sources[life]) for life in LIVES])
    check('explicit_inherited_source_reference_and_zero_new_source_draw', read('source_reference.json') == dict(
        directory='shared_probe_timing_v249', retained_records='source_records.json',
        retained_evidence='source_evidence.json', inherited_samples=13824, physical_new_samples=0))
    check('same_settled_public_cases_and_declared_interfaces',
          read('cases.json') == evidence.load(SOURCE/'cases.json')
          and read('interfaces.json') == evidence.load(SOURCE/'interfaces.json'))
    cases = {row['life']: row['cases'] for row in read('cases.json')}
    interfaces = {row['life']: row for row in read('interfaces.json')}
    states = {(row['life'], row['candidate']): row['state'] for row in read('final_states.json')}
    check('complete_candidate_local_final_state_roster', read('final_states.json')
          == [dict(life=life, arm=candidate, candidate=candidate, state=states[life, candidate])
              for life in LIVES for candidate in PLAN_IDS])
    arguments = [(life, candidate, sources[life], cases[life], interfaces[life], states[life, candidate],
                  summary['profiles'][candidate][str(life)]) for life in LIVES for candidate in PLAN_IDS]
    with ProcessPoolExecutor(max_workers=8) as executor:
        jobs = list(executor.map(audit_life_arm, arguments))
    for job in jobs:
        checks.update(job['checks'])
        failures.extend(job['failures'])
    scored = [row for job in jobs for row in job['scored']]
    candidates, life_summaries = summaries(scored, summary['timings'])
    selected = winner(candidates, 'qualification_witness')
    quality_witness = winner(candidates, 'budget_quality_feasible')
    probe_samples, ordinary_samples = sum(job['probe_paid'] for job in jobs), sum(row['spent'] for row in scored)
    check('all_1728_decisions_independent_filters_winners_and_full_search_fees',
          summary['complete'] and summary['records'] == len(scored) == 1728
          and summary['candidates'] == candidates and summary['life_summaries'] == life_summaries
          and summary['selected'] == selected and summary['budget_quality_witness'] == quality_witness
          and summary['physical_source_samples'] == 0
          and summary['inherited_source_samples'] == summary['inherited_source_samples_charged_per_candidate'] == 13824
          and summary['physical_probe_samples'] == probe_samples == 101376
          and summary['ordinary_search_samples'] == ordinary_samples
          and summary['new_environment_observations'] == ordinary_samples+probe_samples
          and summary['total_search_model_seconds'] == sum(item['model_seconds'] for item in candidates)
          and summary['risk_violation_scope'] == 'all_retained_plans'
          and summary['exploratory_search'] and not summary['scientific_gate_changed']
          and summary['post_selection_coverage_guarantee'] is None and not summary['selected_guarantee_claimed'])
    check('cpu_subtiming_scopes_and_separate_parallel_wall_times',
          summary['model_seconds_scope'] == 'summed_process_CPU_planning_acquisition_pool_observation_bank_initialization_and_probe_pool_updates'
          and summary['acquisition_seconds_scope'] == 'full_choose_process_CPU_subset_of_planning_model_time'
          and summary['output_seconds_scope'] == 'summed_parent_and_worker_write_and_retention_wall_calls_before_final_summary'
          and summary['life_plan_wall_seconds_scope'] == 'worker_entry_through_all_decisions_and_probes_retained_before_artifact_write'
          and set(summary['life_plan_wall_seconds']) == set(PLAN_IDS)
          and all(set(summary['life_plan_wall_seconds'][candidate]) == {str(life) for life in LIVES}
                  and all(seconds >= 0 for seconds in summary['life_plan_wall_seconds'][candidate].values())
                  for candidate in PLAN_IDS))
    ledgers = []
    for job in jobs:
        amount, rows, changed = parameters(job['arm'])
        ledgers.append(dict(life=job['life'], arm=job['arm'], candidate=job['arm'],
            quota_samples=quota(job['arm']), paid_samples=job['probe_paid'], pending_reserved_samples=0,
            probe_batches=len(job['probe_batches']), by_context=dict(A=3*amount*rows, B=3*changed)))
    check('complete_actual_probe_ledger_per_candidate_and_context', read('probe_ledgers.json') == summary['probe_ledgers'] == ledgers)
    # Literal stream entries agree across overlapping candidate prefixes.
    for life in LIVES:
        observations = {}
        for job in (job for job in jobs if job['life'] == life):
            for row in job['probe_batches']:
                key = (row['context'], row['identity'], row['operator'], row['draw_start'])
                entry = (row['seed'], row['draw_end'], row['increments'])
                check('same_context_type_operator_potential_probe_prefix',
                      key not in observations or observations[key] == entry)
                observations[key] = entry
    for candidate in PLAN_IDS:
        method = candidates[PLAN_IDS.index(candidate)]
        expected_work = sum((job['work'] for job in jobs if job['arm'] == candidate), Counter())
        for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
            check('actual_all_candidate_target_and_probe_environment_work', summary['work'][candidate][field]
                  == method['target_samples']+method['probe_samples'])
        for field in ('oracle_gap_direct_choices', 'online_query_comparison_calls', 'online_convex_certificate_calls',
                      'online_convex_proposal_calls', 'online_convex_certificate_cache_hits'):
            check('actual_original_acquisition_and_online_proof_work', summary['work'][candidate].get(field, 0) == expected_work[field])
        check('actual_context_probe_batch_and_sample_work',
              summary['work'][candidate].get('shared_probe_batches', 0) == method['probe_samples']//BATCH
              and summary['work'][candidate].get('shared_probe_samples', 0) == method['probe_samples'])
        for job in (job for job in jobs if job['arm'] == candidate):
            life = str(job['life'])
            check('actual_cpu_and_target_observation_sums',
                  summary['timings']['planning'][candidate][life] == sum(row['model_seconds'] for row in job['scored'])
                  and summary['timings']['acquisition'][candidate][life] == job['acquisitions']
                  and summary['timings']['observation'][candidate][life] == job['observations'])
            for scope in ('initialization', 'begin_b', 'probe_pool_updates', 'probe_draw'):
                check('nonnegative_bank_switch_probe_update_and_observation_time', summary['timings'][scope][candidate][life] >= 0)
            for name, capacity in (('execution', 4096), ('query', 256)):
                stats = summary['normalizer_cache_statistics'][candidate][life][name]
                check('per_job_normalizer_cache_statistics', stats['maxsize'] == capacity
                      and 0 <= stats['currsize'] <= min(stats['misses'], capacity) and stats['hits'] >= 0)
    result = dict(valid=not failures, complete=True, records=len(scored),
        probe_batches=sum(len(job['probe_batches']) for job in jobs),
        plans=sum(job['plans'] for job in jobs), independently_checked_profiles=sum(job['profiles'] for job in jobs),
        independently_checked_global_leaves=sum(job['leaves'] for job in jobs),
        independently_checked_execution_projections=sum(job['projections'] for job in jobs),
        candidates=candidates, selected=selected, budget_quality_witness=quality_witness,
        physical_source_samples=0, inherited_source_samples=13824, physical_probe_samples=probe_samples,
        ordinary_search_samples=ordinary_samples, physical_observations=ordinary_samples+probe_samples,
        risk_violation_scope='all_retained_plans', exploratory_search=True,
        post_selection_coverage_guarantee=None, selected_guarantee_claimed=False,
        binary_projection_comparison_tolerance=0, cold_life_plan_jobs=24, max_workers=8,
        life_plan_elapsed_seconds={f'{job["life"]}/{job["arm"]}': job['elapsed_seconds'] for job in jobs},
        checks=dict(checks), failures=failures, elapsed_seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
