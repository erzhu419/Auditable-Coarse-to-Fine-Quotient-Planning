"""Independent chronological and acquisition audit of the fresh V245 cohort.

Reuse the independent V243 certificate arithmetic, not the V245 producer.
The new allocation is reconstructed from the currently retained goal proof.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from fractions import Fraction as F
from math import log
from pathlib import Path
import json
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_bidirectional_lifecycle_v243 as prior
from scripts import audit_goal_joint_region_v244 as witness

OUTPUT = ROOT/'reports/query_allocation_lifecycle_v245'
ARMS, LIVES, TARGETS = ('ONE_WAY', 'QUERY_DIRECTED', 'REBUILD'), (0, 1, 2), prior.TARGETS
OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
BATCH, CAP, SOURCE_BASE, TARGET_BASE = 16, 384, 282000, 283000
LIFE_CAPS, TARGET_CAPS = (14144, 17072, 17168), (9536, 12464, 12560)
REGRET, THRESHOLD = F(1, 20), 960
paid, evidence, fractions = prior.paid, prior.evidence, prior.fractions


def original_choice(member, saved):
    result = paid.gap_choice(member, saved)
    return dict(result, reason='known_type_action_gap',
                effective_n=dict(saved['effective_n']), initial_deficits=deficits(saved))


def deficits(saved):
    deficits = {query: max(F(0), F(row['regret_upper'])-REGRET)
                for query, row in saved['query_certificates'].items()}
    deficits['execution'] = (F(0) if saved['goal_impossible']
                             else max(F(0), 2-F(saved['utility_lower'])))
    return deficits


def materialize_goal(saved, profiles):
    result = deepcopy(saved)
    goal = result['query_evidence']['queries']['goal']
    goal['comparisons'] = [profiles[row['profile_id']]['certificate']
                           for row in goal['comparisons']]
    return result


def directed_choice(member, saved, work):
    """Replay one cue without importing acquisition or generating evidence."""
    plan = fractions(saved)
    goal = plan['query_evidence']['queries']['goal']
    eligible = plan['utility_lower'] >= 2 or plan['goal_impossible']
    comparison = next((row for row in goal['comparisons']
                       if row['other'] == 'DETOUR_RETRY' and not row['certified']), None)
    if not eligible or goal['policy'] != 'SHORT' or comparison is None:
        work['oracle_gap_direct_choices'] += 1
        return original_choice(member, saved)

    candidate = witness.reconstruct_candidate(comparison, plan['case'])
    work['query_directed_reconstructions'] += 1

    def fallback(reason):
        work['oracle_gap_direct_choices'] += 1
        work['query_directed_fallback_choices'] += 1
        return dict(original_choice(member, saved), query_directed_candidate=candidate,
                    query_directed_scores=None, query_directed_reason=reason)

    kernel = candidate['kernel']
    if kernel is None:
        return fallback('candidate_unavailable')
    scores = {}
    for operator in OPERATORS:
        counts = plan['evidence_counts'][operator]
        total = sum(counts.values())
        terms = []
        for category in ALPHABETS[operator]:
            if counts[category]:
                probability = kernel[operator][category]
                if not probability:
                    return fallback('positive_count_boundary_zero')
                empirical = F(counts[category], total)
                terms.append(float(empirical)*log(float(empirical/probability)))
        scores[operator] = BATCH*sum(terms)
        work['query_directed_row_kl_evaluations'] += 1
    if not any(scores.values()):
        return fallback('zero_discrimination')
    operator = min(OPERATORS, key=lambda name: (
        -scores[name], sum(member[name].values()), OPERATORS.index(name)))
    work['query_directed_choices'] += 1
    return dict(operator=operator, reason='retained_goal_bad_kernel_discrimination',
                query_directed_reason='active', query_directed_candidate=candidate,
                query_directed_scores=scores, effective_n=dict(saved['effective_n']),
                initial_deficits=deficits(saved))


def source_replay(rows, check):
    sources, cursor = {}, 0
    for life in LIVES:
        _, laws, _, _ = paid.world(life)
        sources[life] = {}
        for context, indexes, size in (('A', (0, 1, 2), 384), ('B', (27, 28, 29), 128)):
            anchors = []
            for local, index in enumerate(indexes):
                slot, anchor = (local if context == 'A' else local+3), paid.empty()
                for j, operator in enumerate(OPERATORS):
                    seed = SOURCE_BASE+(life*6+slot)*3+j
                    generator = random.Random(seed)
                    for offset in range(0, size, BATCH):
                        increments = paid.draw(generator, laws[index], operator)
                        expected = dict(life=life, context=context, index=index, slot=slot,
                            operator=operator, seed=seed, draw_start=offset, draw_end=offset+BATCH,
                            increments=increments)
                        check('fresh_source_random_batch_and_offset',
                              cursor < len(rows) and rows[cursor] == expected)
                        cursor += 1
                        for category, count in increments.items():
                            anchor[operator][category] += count
                anchors.append(anchor)
            sources[life][context.lower()] = anchors
    check('all_source_batches_once', cursor == len(rows) == 864)
    return sources


def audit_life(arguments):
    life, sources, cases_saved, interface_saved, states_saved, profile_total = arguments
    begun, checks, failures, location = perf_counter(), Counter(), [], {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    cases, laws, identities, interface = paid.world(life)
    check('predeclared_public_world_and_interfaces', cases_saved == cases
          and interface_saved == dict(life=life, identities=identities, metadata=interface))
    profiles = evidence.read_rows(OUTPUT/f'profiles_life_{life:02d}.jsonl.gz')
    check('complete_profile_numbering',
          [row['profile_id'] for row in profiles] == list(range(len(profiles))))
    profile_decisions, leaves = {}, 0
    for profile in profiles:
        location = dict(life=life, profile_id=profile['profile_id'])
        profile_decisions[profile['profile_id']] = prior.audit_profile(profile, check)
        leaves += len(profile['certificate'].get('leaves', ()))
    states = {arm: dict(a=deepcopy(sources['a']), b=None, a_switch=None) for arm in ARMS}
    histories, projection_cache, used_profiles = dict.fromkeys(ARMS, 0), {}, set()
    results = evidence.read_rows(OUTPUT/f'results_life_{life:02d}.jsonl.gz')
    rows = iter(evidence.read_rows(OUTPUT/f'records_life_{life:02d}.jsonl.gz'))
    scored, orders, seen, observations = [], [], set(), {arm: 0. for arm in ARMS}
    work = {arm: Counter() for arm in ARMS}
    convex_keys = {arm: set() for arm in ARMS}
    plans, projections, results_cursor = 0, 0, 0
    for position, index in enumerate(TARGETS):
        if index == 30:
            for state in states.values():
                state['a_switch'], state['b'] = deepcopy(state['a']), deepcopy(sources['b'])
        offset = (life+position) % 3
        order = ARMS[offset:]+ARMS[:offset]
        orders.append(dict(life=life, index=index, order=list(order)))
        for arm in order:
            row, location = next(rows), dict(life=life, index=index, arm=arm)
            seen.add((life, index, arm))
            check('all_targets_in_frozen_arm_order',
                  (row['life'], row['index'], row['arm']) == (life, index, arm))
            case, identity, state = cases[index], identities[index], states[arm]
            context, source_fee = case['context'].lower(), 3456 if index < 30 else 4608
            pool, pool_arm = state[context][identity], ('ONE_WAY' if arm == 'QUERY_DIRECTED' else arm)
            check('actual_case_identity_and_own_pool_before', row['case'] == case
                  and row['identity'] == identity and row['pooled_before'] == pool
                  and (context != 'b' or state['a'] == state['a_switch']))
            check('nonnegative_cpu_model_wall_observation_and_output_times',
                  all(row[field] >= 0 for field in ('model_seconds', 'observation_seconds', 'output_seconds')))
            observations[arm] += row['observation_seconds']
            seeds = {operator: TARGET_BASE+(life*78+index)*3+j
                     for j, operator in enumerate(OPERATORS)}
            check('same_latent_target_seed_without_cross_arm_cursor', row['seeds'] == seeds)
            generators = {operator: random.Random(seed) for operator, seed in seeds.items()}
            member, spent, available = paid.empty(), 0, TARGET_CAPS[life]-histories[arm]

            def plan_check(saved):
                nonlocal plans, projections
                counts = prior.evidence_counts(state, case, identity, pool_arm, interface)
                constraints = prior.execution_constraints(life, index, case, identity,
                    sources, state, member, pool_arm, interface)
                before = checks['terminal_projected_detour_box']
                prior.audit_plan(saved, case, counts, constraints, profiles, profile_decisions,
                                 projection_cache, used_profiles, check)
                check('no_two_way_return_transfer', saved['return_transfer'] is None)
                projections += checks['terminal_projected_detour_box']-before
                plans += 1
                work[arm]['online_query_comparison_calls'] += 6
                for query in ('goal', 'risk'):
                    for reference in saved['query_evidence']['queries'][query]['comparisons']:
                        certificate = profiles[reference['profile_id']]['certificate']
                        if certificate.get('engine') == 'convex_tangent':
                            work[arm]['online_convex_certificate_calls'] += 1
                            convex_keys[arm].add((certificate['family'], query,
                                certificate['chosen'], certificate['other'],
                                F(certificate['relevant_cost']), prior.freeze(certificate['projected_counts'])))

            current = row['initial_plan']
            plan_check(current)
            for batch in row['batches']:
                check('acquisition_respects_joint_stop_and_both_budget_caps',
                      spent+BATCH <= min(CAP, available) and not prior.ready(current))
                if arm == 'QUERY_DIRECTED':
                    choice = directed_choice(member, materialize_goal(current, profiles), work[arm])
                else:
                    choice = original_choice(member, current)
                    work[arm]['oracle_gap_direct_choices'] += 1
                check('exact_current_proof_allocation_and_all_retained_fields',
                      fractions(batch['choice']) == choice)
                operator, start = choice['operator'], sum(member[choice['operator']].values())
                increments = paid.draw(generators[operator], laws[index], operator)
                check('own_paid_random_prefix_and_category_increments', batch['operator'] == operator
                      and batch['draw_start'] == start and batch['draw_end'] == start+BATCH
                      and batch['increments'] == increments)
                for category, count in increments.items():
                    member[operator][category] += count
                    pool[operator][category] += count
                spent += BATCH
                check('actual_batch_paid_prefix', batch['spent'] == spent)
                current = batch['plan']
                plan_check(current)
            terminal, completed = row['terminal_plan'], prior.ready(current)
            check('terminal_last_observed_plan_and_valid_stop',
                  terminal == current and prior.terminal_stop(spent, available, terminal))
            expected_mix = fractions(terminal['mix']) if completed else [['WAIT', F(1)]]
            check('terminal_flags_safe_fallback_and_own_pool', row['member'] == member
                  and row['spent'] == row['current_paid_samples'] == row['new_paid_samples'] == spent == paid.samples(member)
                  and row['pooled_after'] == pool and row['execution_certified'] == (F(terminal['utility_lower']) >= 2)
                  and row['goal_impossible'] == terminal['goal_impossible']
                  and row['query_certified'] == terminal['query_ready']
                  and row['joint_completed'] == completed and row['fallback'] == (not completed)
                  and fractions(row['executed_mix']) == expected_mix)
            check('source_history_fees_and_reserved_life_budget', row['source_paid_samples'] == source_fee
                  and row['history_paid_samples'] == histories[arm]
                  and row['total_reference_paid_samples'] == source_fee+histories[arm]+spent
                  and row['life_budget_remaining_before'] == available
                  and row['life_budget_remaining_after'] == available-spent
                  and row['budget_exhausted'] == (available-spent < BATCH)
                  and row['member_cap_exhausted'] == (spent == CAP)
                  and 0 <= spent <= min(CAP, available) and spent % BATCH == 0)
            independent = prior.score_history(row, laws[index])
            check('frozen_decisions_all_points_and_actual_execution_truth',
                  fractions(results[results_cursor]) == independent)
            scored.append(independent)
            results_cursor += 1
            histories[arm] += spent
            print(f'audit life={life} target={index} arm={arm} paid={spent}', flush=True)
    check('all_life_targets_results_and_profiles_retained', next(rows, None) is None
          and results_cursor == len(results) == 216 and len(seen) == 216
          and used_profiles == set(range(len(profiles))) and profile_total == len(profiles))
    for arm in ARMS:
        saved, state = states_saved[arm], states[arm]
        check('final_native_banks_sources_switch_and_single_arm_retention',
              saved['life'] == life and saved['arm'] == ('ONE_WAY' if arm == 'QUERY_DIRECTED' else arm)
              and saved['a'] == dict(sources=sources['a'], pools=state['a'])
              and saved['b'] == dict(sources=sources['b'], pools=state['b'])
              and saved['a_at_switch'] == dict(sources=sources['a'], pools=state['a_switch'])
              and saved['changed_operator'] == interface['changed_operator']
              and saved['b_to_a'] == interface['b_to_a'] and saved['return_merge'] is None)
        check('actual_life_total_cap', 4608+histories[arm] <= LIFE_CAPS[life])
        work[arm]['online_convex_proposal_calls'] = len(convex_keys[arm])
        work[arm]['online_convex_certificate_cache_hits'] = (
            work[arm]['online_convex_certificate_calls']-len(convex_keys[arm]))
    return dict(life=life, checks=checks, failures=failures, scored=scored, orders=orders,
        observations=observations, work=work, profiles=len(profiles), leaves=leaves,
        plans=plans, projections=projections, elapsed_seconds=perf_counter()-begun)


def summaries(rows, timings):
    methods, lives = {}, []
    for arm in ARMS:
        selected = [row for row in rows if row['arm'] == arm]
        methods[arm] = dict(prior.aggregate(selected), source_samples=13824,
            total_samples=13824+sum(row['spent'] for row in selected),
            late_b=prior.aggregate([row for row in selected if 42 <= row['index'] < 54]),
            a_return=prior.aggregate([row for row in selected if row['stage'] == 'A_RETURN']))
        methods[arm]['model_seconds'] = sum(timings[scope][arm][str(life)]
            for scope in ('planning', 'initialization', 'begin_b') for life in LIVES)
        for scope in ('planning', 'initialization', 'begin_b'):
            methods[arm][scope+'_seconds'] = sum(timings[scope][arm].values())
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            lives.append(dict(life=life, arm=arm, source_samples=4608,
                total_samples=4608+sum(row['spent'] for row in subset),
                model_seconds=sum(timings[scope][arm][str(life)]
                    for scope in ('planning', 'initialization', 'begin_b')),
                stages={stage: prior.aggregate([row for row in subset if row['stage'] == stage])
                        for stage in ('A', 'B', 'A_RETURN')}))
    directed, conditions = methods['QUERY_DIRECTED'], {}
    conditions.update(late_b_quality=directed['late_b']['query_certified'] >= 27,
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
        for field in ('false_query_certificates', 'false_execution_certificates', 'false_impossible_certificates',
                      'false_goal_uppers', 'risk_violations', 'executed_risk_violations'))
    paired = []
    for life in LIVES:
        selected = {row['arm']: row for row in lives if row['life'] == life}
        one, directed, rebuild = selected['ONE_WAY'], selected['QUERY_DIRECTED'], selected['REBUILD']
        paired.append(dict(life=life,
            one_way_minus_query_directed_samples=one['total_samples']-directed['total_samples'],
            rebuild_minus_query_directed_samples=rebuild['total_samples']-directed['total_samples'],
            return_one_way_minus_query_directed_samples=one['stages']['A_RETURN']['target_samples']-
                directed['stages']['A_RETURN']['target_samples'],
            return_query_directed_minus_one_way_query_certified=directed['stages']['A_RETURN']['query_certified']-
                one['stages']['A_RETURN']['query_certified'],
            return_query_directed_minus_one_way_joint_completed=directed['stages']['A_RETURN']['joint_completed']-
                one['stages']['A_RETURN']['joint_completed']))
    return methods, lives, conditions, paired


def run():
    begun, checks, failures = perf_counter(), Counter(), []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location={'scope': 'cohort'}))

    read = lambda name: evidence.load(OUTPUT/name)
    metadata, summary = read('run.json'), read('summary.json')
    prerequisites = {}
    for version, directory in ((243, 'bidirectional_lifecycle_v243'), (244, 'goal_joint_region_v244')):
        protocol = evidence.load(ROOT/'reports'/directory/'run.json')
        analysis = evidence.load(ROOT/'reports'/directory/'analysis.json')
        check('actual_complete_and_independently_valid_prerequisite', protocol['complete'] and analysis['valid'])
        prerequisites.update({f'v{version}_complete': True, f'v{version}_independent_valid': True})
    check('frozen_fresh_protocol_and_global_decision_freeze_before_scoring', metadata['complete']
        and metadata['prerequisites'] == prerequisites and metadata['lives'] == list(LIVES)
        and metadata['arms'] == list(ARMS) and metadata['targets_per_life'] == 72
        and metadata['cap'] == CAP and metadata['batch'] == BATCH
        and metadata['source_seed_base'] == SOURCE_BASE and metadata['target_seed_base'] == TARGET_BASE
        and metadata['per_life_total_budgets'] == list(LIFE_CAPS) and metadata['source_samples_per_life'] == 4608
        and metadata['query_stream_count'] == 48 and metadata['query_threshold'] == THRESHOLD
        and metadata['query_delta_per_life_arm'] == metadata['execution_delta_per_life_arm'] == '1/20'
        and metadata['combined_delta_upper'] == '1/10' and not metadata['scientific_gate_changed']
        and metadata['qualification_only'] and metadata['phases'] == [
            'protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete']
        and metadata['pool_core_arm_mapping'] == dict(ONE_WAY='ONE_WAY', QUERY_DIRECTED='ONE_WAY', REBUILD='REBUILD')
        and metadata['execution'] == dict(independent_life_processes=3, posthoc_scoring='after_all_648_decisions_frozen')
        and metadata['model_seconds_clock'] == 'process_time'
        and metadata['observation_output_scoring_seconds_clock'] == 'perf_counter')
    check('separate_query_and_execution_event_budgets', F(48, THRESHOLD) == REGRET
          and F(216, 8640)+F(9, 720)+F(9, 720) == REGRET and 2*REGRET == F(1, 10))
    check('per_arm_computation_cache_scope', metadata['computation_cache_scope']
          == summary['computation_cache_scope'] == prior.COMPUTATION_CACHE_SCOPE)
    captured = read('source_manifest.json')
    required = ('scripts/run_query_allocation_lifecycle_v245.py',
        'scripts/audit_query_allocation_lifecycle_v245.py', 'src/acfqp/science/query_directed_acquisition_v245.py',
        'specs/QUERY_ALLOCATION_LIFECYCLE_V245.md')
    check('captured_new_protocol_implementation_and_independent_auditor',
          all(relative in captured for relative in required))
    for relative in captured:
        check('captured_source_matches_current_audited_bytes',
              (OUTPUT/'source_code'/relative).read_bytes() == (ROOT/relative).read_bytes())
    sources = source_replay(read('source_records.json'), check)
    check('physical_sources_once_and_paid_banks',
          read('source_evidence.json') == [dict(life=life, **sources[life]) for life in LIVES])
    cases = {row['life']: row['cases'] for row in read('cases.json')}
    interfaces = {row['life']: row for row in read('interfaces.json')}
    states = {row['life']: row['states'] for row in read('final_states.json')}
    arguments = [(life, sources[life], cases[life], interfaces[life], states[life], summary['profiles'][str(life)])
                 for life in LIVES]
    with ProcessPoolExecutor(max_workers=3) as executor:
        lifetimes = list(executor.map(audit_life, arguments))
    for life in lifetimes:
        checks.update(life['checks'])
        failures.extend(life['failures'])
    scored = [row for life in lifetimes for row in life['scored']]
    orders = [row for life in lifetimes for row in life['orders']]
    methods, life_summaries, conditions, paired = summaries(scored, summary['timings'])
    transfers = [dict(life=life, arm=arm, ledger=None) for life in LIVES for arm in ARMS]
    check('complete_648_target_cohort_order_and_truth_freeze', len(scored) == 648
          and metadata['arm_orders'] == orders)
    check('actual_quality_fees_false_certificates_and_fixed_11_conditions', summary['complete']
        and summary['records'] == 648 and summary['methods'] == methods
        and summary['life_summaries'] == life_summaries and summary['paired'] == paired
        and summary['conditions'] == conditions and len(conditions) == 11
        and summary['stage_condition_met'] == all(conditions.values()) and summary['qualification_only']
        and not summary['scientific_gate_changed'] and summary['physical_source_samples'] == 13824
        and summary['source_samples_charged_per_arm'] == 13824 and summary['return_transfers'] == transfers
        and summary['new_environment_observations'] == 13824+sum(row['spent'] for row in scored)
        and summary['risk_violation_scope'] == 'all_retained_plans'
        and summary['model_seconds_scope'] == 'summed_process_CPU_planning_acquisition_pool_observation_and_bank_initialization'
        and summary['output_seconds_scope'] == 'summed_parent_and_worker_write_and_retention_wall_calls_before_final_summary')
    check('per_life_wall_time_recorded_separately_from_summed_model_cpu',
          set(summary['life_wall_seconds']) == {str(life) for life in LIVES}
          and all(seconds >= 0 for seconds in summary['life_wall_seconds'].values())
          and summary['life_wall_seconds_scope'] == 'worker_entry_through_all_decisions_retained_before_artifact_write')
    for arm in ARMS:
        for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
            check('actual_target_environment_work', summary['work'][arm][field] == methods[arm]['target_samples'])
        expected_work = sum((life['work'][arm] for life in lifetimes), Counter())
        for field in ('oracle_gap_direct_choices', 'query_directed_reconstructions',
                      'query_directed_row_kl_evaluations', 'query_directed_choices', 'query_directed_fallback_choices',
                      'online_query_comparison_calls', 'online_convex_certificate_calls',
                      'online_convex_proposal_calls', 'online_convex_certificate_cache_hits'):
            check('exact_retained_allocation_branch_and_online_certificate_work',
                  summary['work'][arm].get(field, 0) == expected_work[field])
        for life in lifetimes:
            index = str(life['life'])
            selected = [row for row in life['scored'] if row['arm'] == arm]
            check('per_arm_actual_cpu_planning_and_wall_observation_times',
                  summary['timings']['planning'][arm][index] == sum(row['model_seconds'] for row in selected)
                  and summary['timings']['observation'][arm][index] == life['observations'][arm])
            for scope in ('initialization', 'begin_b'):
                check('nonnegative_per_arm_bank_initialization_and_switch_cpu_times',
                      summary['timings'][scope][arm][index] >= 0)
            for name, capacity in (('execution', 4096), ('query', 256)):
                stats = summary['normalizer_cache_statistics'][arm][index][name]
                check('per_arm_exact_normalizer_cache_statistics', stats['maxsize'] == capacity
                      and 0 <= stats['currsize'] <= min(stats['misses'], capacity) and stats['hits'] >= 0)
    for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
        check('actual_source_environment_work', summary['source_work'][field] == 13824)
    result = dict(valid=not failures, complete=True, records=648,
        plans=sum(life['plans'] for life in lifetimes),
        independently_checked_profiles=sum(life['profiles'] for life in lifetimes),
        independently_checked_global_leaves=sum(life['leaves'] for life in lifetimes),
        independently_checked_execution_projections=sum(life['projections'] for life in lifetimes),
        methods=methods, conditions=conditions, stage_condition_met=all(conditions.values()),
        risk_violation_scope='all_retained_plans',
        planned_risk_violations={arm: methods[arm]['risk_violations'] for arm in ARMS},
        executed_risk_violations={arm: methods[arm]['executed_risk_violations'] for arm in ARMS},
        physical_source_samples=13824, physical_observations=13824+sum(row['spent'] for row in scored),
        binary_projection_comparison_tolerance=0, independent_life_processes=3,
        life_elapsed_seconds={life['life']: life['elapsed_seconds'] for life in lifetimes},
        checks=dict(checks), failures=failures, seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
