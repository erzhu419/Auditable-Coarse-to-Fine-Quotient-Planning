"""Independent joint prediction, paid-prefix and fresh return audit.

Hypothetical increments only reconstruct the acquisition score. Actual query
proofs and execution are checked from the following real retained batches.
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
OUTPUT = ROOT/'reports/joint_prediction_return_v247'
PREFIX = ROOT/'reports/query_allocation_lifecycle_v245'
LIVES, ARMS, TARGETS = (0, 1, 2), ('ONE_WAY', 'JOINT_PREDICTION'), tuple(range(54, 78))
PREFIX_TARGETS = tuple(range(3, 27))+tuple(range(30, 54))
OPERATORS, ALPHABETS = allocation.OPERATORS, allocation.ALPHABETS
BATCH, CAP, SOURCE_COST, TARGET_BASE = 16, 384, 4608, 286000
LIFE_CAPS = (14144, 17072, 17168)


def retained_sources(rows, check):
    """Sum validated historical increments; do not redraw settled old streams."""
    sources = {life: {context: [paid.empty() for _ in range(3)]
                     for context in ('a', 'b')} for life in LIVES}
    for row in rows:
        context, slot = row['context'].lower(), row['slot']-(3 if row['context'] == 'B' else 0)
        check('historical_source_batch_physical_count', sum(row['increments'].values()) == BATCH)
        pool = sources[row['life']][context][slot][row['operator']]
        for category, count in row['increments'].items():
            pool[category] += count
    for life in LIVES:
        check('historical_source_fees_not_omitted',
              sum(paid.samples(pool) for pool in sources[life]['a']) == 3456
              and sum(paid.samples(pool) for pool in sources[life]['b']) == 1152)
    return sources


def common_prefix(life, sources, rows, check):
    """Replay only paid native ONE_WAY A/B rows, not inherited query counts."""
    state = dict(a=deepcopy(sources['a']), b=deepcopy(sources['b']), a_switch=None)
    selected = [row for row in rows if row['arm'] == 'ONE_WAY' and row['index'] < 54]
    check('prefix_exact_one_way_A_B_targets',
          [row['index'] for row in selected] == list(PREFIX_TARGETS)
          and all(row['life'] == life for row in selected))
    history = 0
    for row in selected:
        if row['index'] == 30:
            state['a_switch'] = deepcopy(state['a'])
        context, identity = row['case']['context'].lower(), row['identity']
        pool = state[context][identity]
        check('prefix_original_paid_native_pool_before', row['pooled_before'] == pool)
        member = paid.empty()
        for batch in row['batches']:
            operator = batch['operator']
            check('prefix_batch_fees_and_category_counts', sum(batch['increments'].values()) == BATCH)
            for category, amount in batch['increments'].items():
                member[operator][category] += amount
                pool[operator][category] += amount
        check('prefix_native_pool_after_and_paid_history', row['pooled_after'] == pool
              and row['member'] == member and paid.samples(member) == row['spent']
              and row['history_paid_samples'] == history)
        history += row['spent']
    return state, history


def prefix_ledger(life, sources, rows):
    selected = [row for row in rows if row['arm'] == 'ONE_WAY' and row['index'] < 54]
    source = {context: sum(paid.samples(pool) for pool in sources[context.lower()])
              for context in ('A', 'B')}
    target = {context: sum(row['spent'] for row in selected if row['case']['context'] == context)
              for context in ('A', 'B')}
    batches = {context: sum(len(row['batches']) for row in selected if row['case']['context'] == context)
               for context in ('A', 'B')}
    return dict(life=life, reference=dict(directory=str(PREFIX), source_records='source_records.json',
            target_records=f'records_life_{life:02d}.jsonl.gz', arm='ONE_WAY', stages=['A', 'B'],
            first_target=3, last_target=53, targets=48),
        source_samples_by_context=source, target_samples_by_context=target,
        target_batches_by_context=batches, source_paid_samples=sum(source.values()),
        history_paid_samples=sum(target.values()), total_prefix_paid_samples=sum(source.values())+sum(target.values()),
        new_observations=0, retained_decisions_imported=0, return_observations_imported=0,
        another_arm_observations_imported=0)


def saved_state(life, sources, state, metadata):
    return dict(life=life, arm='ONE_WAY',
        a=dict(sources=sources['a'], pools=state['a']),
        b=dict(sources=sources['b'], pools=state['b']),
        a_at_switch=dict(sources=sources['a'], pools=state['a_switch']),
        changed_operator=metadata['changed_operator'], b_to_a=metadata['b_to_a'], return_merge=None)


def expected_increment(row, operator):
    total = sum(row.values())
    exact = {category: F(BATCH*row[category], total) for category in ALPHABETS[operator]}
    result = {category: value.numerator//value.denominator for category, value in exact.items()}
    remaining = BATCH-sum(result.values())
    order = sorted(ALPHABETS[operator], key=lambda category:
        (-(exact[category]-result[category]), ALPHABETS[operator].index(category)))
    for category in order[:remaining]:
        result[category] += 1
    return result


def materialize(plan, profiles):
    result = fractions(deepcopy(plan))
    for query in ('goal', 'risk'):
        decision = result['query_evidence']['queries'][query]
        decision['comparisons'] = [fractions(profiles[row['profile_id']]['certificate'])
                                   for row in decision['comparisons']]
    return result


def predicted_bounds(comparison, case, raw_counts):
    """Independent 100-digit upper/lower enclosures, without any proposal."""
    arithmetic = prior.arithmetic
    uniform = {operator: dict.fromkeys(categories, F(1, len(categories)))
               for operator, categories in ALPHABETS.items()}
    projected, _ = evidence.named_projection(comparison['family'], raw_counts, uniform)
    mixture = sum((arithmetic.logarithm(evidence.predictive_weight(tuple(row.values())))[0]
                   for row in projected.values()), F(0))
    leaves, tangent, fallback = [], None, None
    if comparison.get('engine') == 'convex_tangent':
        retained = comparison['result']['global_tangent']
        if retained is not None:
            tangent = prior.convex_audit.tangent_components(case, comparison['family'], projected,
                                                           retained['point'], retained['multiplier'])
            upper = tangent['global_upper']
        else:
            fallback = 'missing_retained_tangent'
    else:
        if comparison['witness_kind'] == 'bad_null_mle':
            fallback = 'bad_null_mle'
        elif not comparison['leaves']:
            fallback = 'missing_retained_partition'
        if fallback is None:
            counts = prior.global_audit.embedded_counts(projected)
            old = prior.global_audit.embedded_counts(comparison['projected_counts'])
            for index, leaf in enumerate(comparison['leaves']):
                if leaf['kind'] == 'empty_bad_null':
                    leaves.append(dict(index=index, kind='empty_bad_null',
                        log_bad_likelihood_upper=None, row_nus={}, retry_probability=None))
                    continue
                multiplier = F(leaf['multiplier'])
                row_bounds, row_nus = [], {}
                for operator, coefficients in leaf['gap_coefficients'].items():
                    witness = leaf['row_witnesses'][operator]
                    if witness['kind'] == 'free_simplex':
                        assert sum(counts[operator].values()) == 0
                        row_nus[operator] = None
                        row_upper = max(multiplier*F(value) for value in coefficients.values())
                    else:
                        nu = F(witness['nu'])+sum(counts[operator].values())-sum(old[operator].values())
                        row_nus[operator] = nu
                        row_upper = arithmetic.row_dual_upper(counts[operator], coefficients, multiplier, nu)
                    row_bounds.append(row_upper)
                retry = arithmetic.retry_likelihood_upper(counts[OPERATORS[2]], leaf['retry_interval'])
                total = sum(counts[OPERATORS[2]].values())
                probability = F(counts[OPERATORS[2]]['DELIVERY'], total) if total else F(1, 2)
                probability = min(F(leaf['retry_interval'][1]), max(F(leaf['retry_interval'][0]), probability))
                upper = multiplier*(F(leaf['gap_constant'])-F(comparison['regret_threshold']))+retry+sum(row_bounds, F(0))
                leaves.append(dict(index=index, kind='likelihood_dual', log_bad_likelihood_upper=upper,
                                   row_nus=row_nus, retry_probability=probability))
            finite = [row['log_bad_likelihood_upper'] for row in leaves if row['log_bad_likelihood_upper'] is not None]
            upper = max(finite) if finite else None
    if fallback is not None:
        upper = F(0)
        for row in projected.values():
            total = sum(row.values())
            for category, count in row.items():
                if count:
                    upper += count*arithmetic.logarithm(F(count, total))[1]
    return dict(projected_counts=projected, fallback=fallback, tangent=tangent, leaf_bounds=leaves,
                log_mixture_lower=mixture, log_bad_likelihood_upper=upper)


def audit_prediction(saved, proof, case, raw_counts, work, check):
    expected = predicted_bounds(proof, case, raw_counts)
    engine = proof.get('engine', 'V235')
    check('prediction_same_unfinished_comparison_canonical_projection_and_fallback',
          all(saved[field] == proof[field] for field in ('query', 'chosen', 'other', 'family'))
          and saved['engine'] == engine and saved['projected_counts'] == expected['projected_counts']
          and saved['fallback'] == expected['fallback'])
    check('prediction_updated_mixture_and_threshold_outward_bounds',
          saved['log_mixture_lower'] <= expected['log_mixture_lower']
          and saved['log_threshold_upper'] >= prior.arithmetic.logarithm(F(proof['threshold']))[1])
    check('prediction_all_original_cells_without_cell_selection',
          len(saved['leaf_bounds']) == len(expected['leaf_bounds']))
    for retained, rebuilt in zip(saved['leaf_bounds'], expected['leaf_bounds']):
        check('prediction_cell_fixed_nu_increment_retry_MLE_and_geometry',
              all(retained[field] == rebuilt[field] for field in ('index', 'kind', 'row_nus', 'retry_probability')))
        if rebuilt['log_bad_likelihood_upper'] is None:
            check('prediction_preserves_structurally_empty_cell', retained['log_bad_likelihood_upper'] is None)
        else:
            check('prediction_whole_cell_likelihood_upper',
                  retained['log_bad_likelihood_upper'] >= rebuilt['log_bad_likelihood_upper'])
    check('prediction_complete_null_or_explicit_unrestricted_MLE_upper',
          saved['log_bad_likelihood_upper'] >= expected['log_bad_likelihood_upper'])
    if expected['leaf_bounds'] and expected['fallback'] is None:
        check('prediction_global_upper_maximizes_all_original_cells', saved['log_bad_likelihood_upper'] ==
              max(row['log_bad_likelihood_upper'] for row in saved['leaf_bounds']
                  if row['log_bad_likelihood_upper'] is not None))
    check('prediction_score_only_margin_arithmetic',
          saved['log_e_lower'] == saved['log_mixture_lower']-saved['log_bad_likelihood_upper']
          and saved['deficit'] == max(F(0), saved['log_threshold_upper']-saved['log_e_lower']))
    if expected['fallback'] is not None:
        work['joint_prediction_mle_fallbacks'] += 1
    if expected['tangent'] is not None:
        work['joint_prediction_tangent_evaluations'] += 1
    for leaf in expected['leaf_bounds']:
        work['joint_prediction_cell_evaluations'] += 1
        if leaf['log_bad_likelihood_upper'] is not None:
            work['joint_prediction_row_bound_evaluations'] += len(leaf['row_nus'])
    independent_margin = expected['log_mixture_lower']-expected['log_bad_likelihood_upper']
    return max(F(0), prior.arithmetic.logarithm(F(proof['threshold']))[1]-independent_margin)


def choose(arm, member, plan, profiles, work, recorded=None, check=None):
    check = check or (lambda name, condition: None)
    if arm == 'ONE_WAY' or not (F(plan['utility_lower']) >= 2 or plan['goal_impossible']) or plan['query_ready']:
        work['oracle_gap_direct_choices'] += 1
        return allocation.original_choice(member, plan)
    restored, saved = materialize(plan, profiles), fractions(recorded)
    proofs = [proof for query in ('goal', 'risk')
              for proof in restored['query_evidence']['queries'][query]['comparisons'] if not proof['certified']]
    check('query_only_prediction_requires_all_goal_and_risk_blockers', bool(proofs)
          and saved['prediction_only'] and saved['reason'] == 'joint_retained_proof_prediction'
          and saved['joint_prediction_reason'] == 'active')
    counts, case = restored['evidence_counts'], restored['case']
    check('current_prediction_all_unfinished_comparisons', len(saved['joint_prediction_current']) == len(proofs))
    for comparison, proof in zip(saved['joint_prediction_current'], proofs):
        audit_prediction(comparison, proof, case, counts, work, check)
    work['joint_prediction_current_comparison_evaluations'] += len(proofs)
    increments = {operator: expected_increment(counts[operator], operator) for operator in OPERATORS}
    check('empirical_raw_full_row_integer_prediction_precedes_projection',
          saved['joint_prediction_expected_increments'] == increments)
    independent_scores = {}
    check('all_actual_operator_predictions_retained', set(saved['joint_prediction_candidates']) == set(OPERATORS))
    for operator in OPERATORS:
        hypothetical = deepcopy(counts)
        for category, count in increments[operator].items():
            hypothetical[operator][category] += count
        candidate = saved['joint_prediction_candidates'][operator]
        check('candidate_predicts_all_unfinished_comparisons', len(candidate['comparisons']) == len(proofs))
        deficits = [audit_prediction(comparison, proof, case, hypothetical, work, check)
                    for comparison, proof in zip(candidate['comparisons'], proofs)]
        independent_scores[operator] = max(deficits)
        check('joint_prediction_worst_deficit_uses_all_comparisons',
              candidate['worst_deficit'] == max(row['deficit'] for row in candidate['comparisons']))
        work['joint_prediction_candidate_comparison_evaluations'] += len(proofs)
    selected = min(OPERATORS, key=lambda operator: (independent_scores[operator],
                   sum(member[operator].values()), OPERATORS.index(operator)))
    work['joint_prediction_choices'] += 1
    return dict(saved, operator=selected, effective_n=dict(plan['effective_n']),
                initial_deficits=allocation.deficits(plan))


def audit_life(arguments):
    life, sources, cases_saved, interface_saved, states_saved, profile_total, prefix_saved = arguments
    begun, checks, failures, location = perf_counter(), Counter(), [], {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    cases, laws, identities, interface = paid.world(life)
    check('actual_public_world_and_interface', cases_saved == cases
          and interface_saved == dict(life=life, identities=identities, metadata=interface))
    prefix, historic = common_prefix(life, sources,
        evidence.read_rows(PREFIX/f'records_life_{life:02d}.jsonl.gz'), check)
    check('only_common_native_one_way_prefix_saved', prefix_saved['life'] == life
          and prefix_saved['history_paid_samples'] == historic
          and prefix_saved['state'] == saved_state(life, sources, prefix, interface))
    states = {arm: deepcopy(prefix) for arm in ARMS}
    histories = dict.fromkeys(ARMS, historic)
    profiles = evidence.read_rows(OUTPUT/f'profiles_life_{life:02d}.jsonl.gz')
    check('complete_profile_numbering',
          [row['profile_id'] for row in profiles] == list(range(len(profiles))))
    profile_decisions, leaves = {}, 0
    for profile in profiles:
        location = dict(life=life, profile_id=profile['profile_id'])
        profile_decisions[profile['profile_id']] = prior.audit_profile(profile, check)
        leaves += len(profile['certificate'].get('leaves', ()))
    results = evidence.read_rows(OUTPUT/f'results_life_{life:02d}.jsonl.gz')
    rows = iter(evidence.read_rows(OUTPUT/f'records_life_{life:02d}.jsonl.gz'))
    scored, orders, seen = [], [], set()
    projection_cache, used_profiles = {}, set()
    observations, acquisitions = dict.fromkeys(ARMS, 0.), dict.fromkeys(ARMS, 0.)
    work = {arm: Counter() for arm in ARMS}
    convex_keys = {arm: set() for arm in ARMS}
    plans, projections, results_cursor = 0, 0, 0
    for position, index in enumerate(TARGETS):
        offset = (life+position) % len(ARMS)
        order = ARMS[offset:]+ARMS[:offset]
        orders.append(dict(life=life, index=index, order=list(order)))
        for arm in order:
            row, location = next(rows), dict(life=life, index=index, arm=arm)
            seen.add((life, index, arm))
            check('all_return_targets_in_frozen_arm_order',
                  (row['life'], row['index'], row['arm']) == (life, index, arm))
            case, identity, state = cases[index], identities[index], states[arm]
            pool = state['a'][identity]
            check('actual_case_own_pool_and_unchanged_B_prefix', row['case'] == case
                  and row['identity'] == identity and row['pooled_before'] == pool
                  and state['b'] == prefix['b'] and state['a_switch'] == prefix['a_switch'])
            check('nonnegative_retained_process_and_wall_times',
                  all(row[field] >= 0 for field in ('model_seconds', 'observation_seconds', 'output_seconds')))
            check('full_choice_cpu_included_in_model_once', 0 <= row['acquisition_seconds'] <= row['model_seconds'])
            observations[arm] += row['observation_seconds']
            acquisitions[arm] += row['acquisition_seconds']
            seeds = {operator: TARGET_BASE+(life*78+index)*3+j
                     for j, operator in enumerate(OPERATORS)}
            check('fresh_shared_suffix_seeds_and_independent_cursors', row['seeds'] == seeds)
            generators = {operator: random.Random(seed) for operator, seed in seeds.items()}
            member, spent, available = paid.empty(), 0, LIFE_CAPS[life]-SOURCE_COST-histories[arm]

            def plan_check(saved):
                nonlocal plans, projections
                counts = prior.evidence_counts(state, case, identity, 'ONE_WAY', interface)
                constraints = prior.execution_constraints(life, index, case, identity,
                    sources, state, member, 'ONE_WAY', interface)
                before = checks['terminal_projected_detour_box']
                prior.audit_plan(saved, case, counts, constraints, profiles, profile_decisions,
                                 projection_cache, used_profiles, check)
                check('return_queries_have_no_B_import', saved['return_transfer'] is None)
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
                check('joint_stop_member_and_full_charged_life_caps',
                      spent+BATCH <= min(CAP, available) and not prior.ready(current))
                choice = choose(arm, member, current, profiles, work[arm], batch['choice'], check)
                check('exact_live_choice_materializes_actual_referenced_profile',
                      fractions(batch['choice']) == choice)
                operator, start = choice['operator'], sum(member[choice['operator']].values())
                increments = paid.draw(generators[operator], laws[index], operator)
                check('actual_paid_suffix_random_batch_and_offset', batch['operator'] == operator
                      and batch['draw_start'] == start and batch['draw_end'] == start+BATCH
                      and batch['increments'] == increments)
                for category, count in increments.items():
                    member[operator][category] += count
                    pool[operator][category] += count
                spent += BATCH
                check('every_observation_paid_once', batch['spent'] == spent)
                current = batch['plan']
                plan_check(current)
            terminal, completed = row['terminal_plan'], prior.ready(current)
            check('terminal_last_observed_plan_and_valid_stop',
                  terminal == current and prior.terminal_stop(spent, available, terminal))
            expected_mix = fractions(terminal['mix']) if completed else [['WAIT', F(1)]]
            check('terminal_flags_safe_fallback_own_paid_member_and_pool', row['member'] == member
                  and row['spent'] == row['current_paid_samples'] == row['new_paid_samples'] == spent == paid.samples(member)
                  and row['pooled_after'] == pool and row['execution_certified'] == (F(terminal['utility_lower']) >= 2)
                  and row['goal_impossible'] == terminal['goal_impossible']
                  and row['query_certified'] == terminal['query_ready']
                  and row['joint_completed'] == completed and row['fallback'] == (not completed)
                  and fractions(row['executed_mix']) == expected_mix)
            check('full_source_past_target_fees_and_original_total_budget', row['source_paid_samples'] == SOURCE_COST
                  and row['history_paid_samples'] == histories[arm]
                  and row['total_reference_paid_samples'] == SOURCE_COST+histories[arm]+spent
                  and row['life_budget_remaining_before'] == available
                  and row['life_budget_remaining_after'] == available-spent
                  and row['budget_exhausted'] == (available-spent < BATCH)
                  and row['member_cap_exhausted'] == (spent == CAP)
                  and 0 <= spent <= min(CAP, available) and spent % BATCH == 0)
            independent = prior.score_history(row, laws[index])
            check('all_retained_points_and_actual_execution_truth',
                  fractions(results[results_cursor]) == independent)
            scored.append(independent)
            results_cursor += 1
            histories[arm] += spent
            print(f'audit life={life} target={index} arm={arm} paid={spent}', flush=True)
    check('all_48_return_targets_results_and_profiles_retained', next(rows, None) is None
          and results_cursor == len(results) == 48 and len(seen) == 48
          and used_profiles == set(range(len(profiles))) and profile_total == len(profiles))
    for arm in ARMS:
        check('final_native_banks_keep_B_and_A_switch_unmodified',
              states_saved[arm] == saved_state(life, sources, states[arm], interface))
        check('actual_full_charged_life_cap', SOURCE_COST+histories[arm] <= LIFE_CAPS[life])
        work[arm]['online_convex_proposal_calls'] = len(convex_keys[arm])
        work[arm]['online_convex_certificate_cache_hits'] = (
            work[arm]['online_convex_certificate_calls']-len(convex_keys[arm]))
    return dict(life=life, checks=checks, failures=failures, scored=scored, orders=orders,
        observations=observations, acquisitions=acquisitions, work=work, profiles=len(profiles), leaves=leaves,
        plans=plans, projections=projections, prefix_samples=historic,
        elapsed_seconds=perf_counter()-begun)


def conditions(methods):
    directed, one = methods['JOINT_PREDICTION'], methods['ONE_WAY']
    return dict(a_return_quality=directed['query_certified'] >= 54,
        matched_one_way_query_quality=directed['query_certified'] >= one['query_certified'],
        matched_one_way_joint_quality=directed['joint_completed'] >= one['joint_completed'],
        actual_acquisition_nondegrading_vs_one_way=directed['total_samples'] <= one['total_samples'],
        valid_certificates_and_execution=all(method[field] == 0 for method in methods.values()
            for field in ('false_query_certificates', 'false_execution_certificates',
                          'false_impossible_certificates', 'false_goal_uppers',
                          'risk_violations', 'executed_risk_violations')))


def summaries(rows, timings, histories):
    methods, lives = {}, []
    for arm in ARMS:
        selected = [row for row in rows if row['arm'] == arm]
        methods[arm] = dict(prior.aggregate(selected), source_samples=SOURCE_COST*len(LIVES),
            inherited_target_samples=sum(histories.values()),
            total_samples=SOURCE_COST*len(LIVES)+sum(histories.values())+sum(row['spent'] for row in selected))
        for scope in ('planning', 'initialization', 'acquisition'):
            methods[arm][scope+'_seconds'] = sum(timings[scope][arm].values())
        methods[arm]['model_seconds'] = sum(timings[scope][arm][str(life)]
            for scope in ('planning', 'initialization') for life in LIVES)
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            lives.append(dict(life=life, arm=arm, source_samples=SOURCE_COST,
                inherited_target_samples=histories[life],
                total_samples=SOURCE_COST+histories[life]+sum(row['spent'] for row in subset),
                model_seconds=sum(timings[scope][arm][str(life)] for scope in ('planning', 'initialization')),
                acquisition_seconds=timings['acquisition'][arm][str(life)],
                a_return=prior.aggregate(subset)))
    paired = []
    for life in LIVES:
        selected = {row['arm']: row for row in lives if row['life'] == life}
        one, directed = selected['ONE_WAY'], selected['JOINT_PREDICTION']
        paired.append(dict(life=life, one_way_minus_joint_prediction_samples=one['total_samples']-directed['total_samples'],
            joint_prediction_minus_one_way_query_certified=directed['a_return']['query_certified']-
                one['a_return']['query_certified'],
            joint_prediction_minus_one_way_joint_completed=directed['a_return']['joint_completed']-
                one['a_return']['joint_completed']))
    return methods, lives, paired


def run():
    begun, checks, failures = perf_counter(), Counter(), []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location={'scope': 'cohort'}))

    read = lambda name: evidence.load(OUTPUT/name)
    metadata, summary = read('run.json'), read('summary.json')
    prefix_run, prefix_analysis = evidence.load(PREFIX/'run.json'), evidence.load(PREFIX/'analysis.json')
    check('validated_complete_historical_prefix_prerequisite', prefix_run['complete'] and prefix_analysis['valid'])
    v246 = ROOT/'reports/common_inheritance_return_v246'
    check('validated_complete_common_inheritance_diagnostic_prerequisite',
          evidence.load(v246/'run.json')['complete'] and evidence.load(v246/'analysis.json')['valid'])
    check('frozen_conditional_suffix_protocol_before_truth', metadata['complete']
        and metadata['prerequisites'] == dict(v245_complete=True, v245_independent_valid=True,
            v246_complete=True, v246_independent_valid=True)
        and metadata['lives'] == list(LIVES) and metadata['arms'] == list(ARMS)
        and metadata['targets_per_life'] == 24 and metadata['cap'] == CAP and metadata['batch'] == BATCH
        and metadata['target_seed_base'] == TARGET_BASE and metadata['per_life_total_budgets'] == list(LIFE_CAPS)
        and metadata['inherited_source_samples_per_life'] == SOURCE_COST
        and metadata['inherited_target_samples_per_life'] == [6768, 9216, 7952]
        and metadata['initial_return_available_samples'] == [2768, 3248, 4608]
        and metadata['prefix_directory'] == PREFIX.relative_to(ROOT).as_posix()
        and metadata['prefix_arm'] == 'ONE_WAY' and metadata['prefix_stages'] == ['A', 'B']
        and metadata['new_source_observations'] == 0 and metadata['query_stream_count'] == 48
        and metadata['query_threshold'] == 960
        and metadata['query_delta_per_life_arm'] == metadata['execution_delta_per_life_arm'] == '1/20'
        and metadata['combined_delta_upper'] == '1/10' and not metadata['scientific_gate_changed']
        and metadata['qualification_only'] and metadata['suffix_only']
        and metadata['phases'] == ['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete']
        and metadata['execution'] == dict(independent_life_processes=3, posthoc_scoring='after_all_144_decisions_frozen')
        and metadata['model_seconds_clock'] == metadata['prefix_replay_seconds_clock'] == 'process_time'
        and metadata['observation_output_scoring_seconds_clock'] == 'perf_counter')
    check('unchanged_whole_process_query_and_execution_delta_budgets', F(48, 960) == F(1, 20)
          and F(216, 8640)+F(9, 720)+F(9, 720) == F(1, 20))
    check('per_arm_empty_cache_scope', metadata['computation_cache_scope']
          == summary['computation_cache_scope'] == prior.COMPUTATION_CACHE_SCOPE)
    captured = read('source_manifest.json')
    required = ('scripts/run_joint_prediction_return_v247.py',
        'scripts/audit_joint_prediction_return_v247.py', 'src/acfqp/science/joint_prediction_acquisition_v247.py',
        'specs/JOINT_PREDICTION_RETURN_V247.md')
    check('captured_protocol_prefix_replay_runner_and_independent_auditor',
          all(relative in captured for relative in required))
    for relative in captured:
        check('captured_source_matches_current_audited_bytes',
              (OUTPUT/'source_code'/relative).read_bytes() == (ROOT/relative).read_bytes())
    sources = retained_sources(evidence.load(PREFIX/'source_records.json'), check)
    check('summed_historical_source_banks_match_original_retention',
          evidence.load(PREFIX/'source_evidence.json') == [dict(life=life, **sources[life]) for life in LIVES])
    ledgers = {row['life']: row for row in read('prefix_ledgers.json')}
    cases = {row['life']: row['cases'] for row in read('cases.json')}
    interfaces = {row['life']: row for row in read('interfaces.json')}
    states = {row['life']: row['states'] for row in read('final_states.json')}
    prefixes = {row['life']: row for row in read('common_prefix_states.json')}
    histories = {}
    for life in LIVES:
        old = evidence.read_rows(PREFIX/f'records_life_{life:02d}.jsonl.gz')
        ledger = prefix_ledger(life, sources[life], old)
        check('exact_common_prefix_observations_costs_and_reference_ledger', ledgers[life] == ledger)
        histories[life] = ledger['history_paid_samples']
    check('frozen_history_fees_and_original_return_capacities',
          [histories[life] for life in LIVES] == [6768, 9216, 7952])
    arguments = [(life, sources[life], cases[life], interfaces[life], states[life], summary['profiles'][str(life)],
                  prefixes[life]) for life in LIVES]
    with ProcessPoolExecutor(max_workers=3) as executor:
        lifetimes = list(executor.map(audit_life, arguments))
    for life in lifetimes:
        checks.update(life['checks'])
        failures.extend(life['failures'])
    scored = [row for life in lifetimes for row in life['scored']]
    orders = [row for life in lifetimes for row in life['orders']]
    methods, life_summaries, paired = summaries(scored, summary['timings'], histories)
    phase_conditions = conditions(methods)
    check('all_144_frozen_suffix_targets_and_orders', len(scored) == 144 and metadata['arm_orders'] == orders)
    check('actual_query_quality_full_charged_fees_and_five_conditions', summary['complete']
        and summary['records'] == 144 and summary['methods'] == methods and summary['life_summaries'] == life_summaries
        and summary['paired'] == paired and summary['conditions'] == phase_conditions
        and len(phase_conditions) == 5 and summary['stage_condition_met'] == all(phase_conditions.values())
        and summary['qualification_only'] and summary['suffix_only'] and not summary['scientific_gate_changed']
        and summary['physical_source_samples'] == 0
        and summary['inherited_source_samples_charged_per_arm'] == SOURCE_COST*len(LIVES)
        and summary['inherited_target_samples_charged_per_arm'] == sum(histories.values())
        and summary['new_environment_observations'] == sum(row['spent'] for row in scored)
        and summary['risk_violation_scope'] == 'all_retained_return_plans'
        and summary['model_seconds_scope'] == 'summed_process_CPU_planning_acquisition_pool_observation_and_state_copy')
    check('actual_shared_prefix_replay_cost_recorded_separately_from_arm_model_cost',
          summary['common_prefix_replay_CPU_seconds_scope'] ==
              'one_common_prefix_replay_per_life_separate_from_both_arm_model_times'
          and all(summary['common_prefix_replay_CPU_seconds'][str(life)] >= 0 for life in LIVES)
          and all(summary['prefix_read_seconds'][str(life)] >= 0 for life in LIVES))
    check('predicted_scores_retained_without_extra_scoring_experiments',
          summary['acquisition_seconds_scope'] == 'full_choose_process_CPU_subset_of_planning_model_time'
          and summary['prediction_realization_scope'] == 'retained_choice_predictions_and_following_batch_plan_profiles_only')
    check('per_life_wall_times_recorded_separately', set(summary['life_wall_seconds']) == {str(life) for life in LIVES}
        and all(seconds >= 0 for seconds in summary['life_wall_seconds'].values())
        and summary['life_wall_seconds_scope'] == 'worker_entry_through_all_decisions_retained_before_artifact_write')
    for arm in ARMS:
        for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
            check('actual_fresh_suffix_environment_work', summary['work'][arm][field] == methods[arm]['target_samples'])
        expected_work = sum((life['work'][arm] for life in lifetimes), Counter())
        for field in ('oracle_gap_direct_choices', 'joint_prediction_choices',
                      'joint_prediction_current_comparison_evaluations', 'joint_prediction_candidate_comparison_evaluations',
                      'joint_prediction_cell_evaluations', 'joint_prediction_row_bound_evaluations',
                      'joint_prediction_mle_fallbacks', 'joint_prediction_tangent_evaluations',
                      'online_query_comparison_calls', 'online_convex_certificate_calls',
                      'online_convex_proposal_calls', 'online_convex_certificate_cache_hits'):
            check('live_allocation_and_online_certificate_work', summary['work'][arm].get(field, 0) == expected_work[field])
        for life in lifetimes:
            index = str(life['life'])
            selected = [row for row in life['scored'] if row['arm'] == arm]
            check('actual_arm_planning_and_observation_time_sums',
                  summary['timings']['planning'][arm][index] == sum(row['model_seconds'] for row in selected)
                  and summary['timings']['observation'][arm][index] == life['observations'][arm]
                  and summary['timings']['acquisition'][arm][index] == life['acquisitions'][arm]
                  and summary['timings']['initialization'][arm][index] >= 0)
            for name, capacity in (('execution', 4096), ('query', 256)):
                stats = summary['normalizer_cache_statistics'][arm][index][name]
                check('separate_arm_normalizer_caches', stats['maxsize'] == capacity
                      and 0 <= stats['currsize'] <= min(stats['misses'], capacity) and stats['hits'] >= 0)
    result = dict(valid=not failures, complete=True, records=144,
        plans=sum(life['plans'] for life in lifetimes),
        independently_checked_profiles=sum(life['profiles'] for life in lifetimes),
        independently_checked_global_leaves=sum(life['leaves'] for life in lifetimes),
        independently_checked_execution_projections=sum(life['projections'] for life in lifetimes),
        methods=methods, conditions=phase_conditions, stage_condition_met=all(phase_conditions.values()),
        risk_violation_scope='all_retained_return_plans', physical_source_samples=0,
        physical_observations=sum(row['spent'] for row in scored),
        inherited_source_samples_charged_per_arm=SOURCE_COST*len(LIVES),
        inherited_target_samples_charged_per_arm=sum(histories.values()),
        binary_projection_comparison_tolerance=0, independent_life_processes=3,
        suffix_only=True, scientific_gate_changed=False,
        life_elapsed_seconds={life['life']: life['elapsed_seconds'] for life in lifetimes},
        checks=dict(checks), failures=failures, seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
