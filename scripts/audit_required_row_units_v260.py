"""Independent predictable required-row-unit lifecycle audit.

The V260 producer and core are not imported. Established independent direct
bet and execution-region mathematics are evaluated on replayed physical data.
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
from scripts import audit_executable_trajectory_v254 as direct
from scripts import audit_query_allocation_lifecycle_v245 as allocation
from scripts import audit_coupled_impossibility_v257 as coupled

execution, paid = allocation.prior, allocation.paid
OPERATORS, ALPHABETS, POLICIES = direct.OPERATORS, direct.ALPHABETS, direct.POLICIES
S, D, R = OPERATORS
QUERIES = ('reward', 'goal', 'risk')
LIVES, ARMS = (0, 1, 2), ('REQUIRED_ROWS_REUSE', 'CONTINUOUS_REUSE', 'TRAJECTORY_REBUILD')
CAPS, SOURCE_A, SOURCE_B, MEMBER_CAP, MEMBER_BATCH, SHARED_BATCH = (14144, 17072, 17168), 3456, 1152, 384, 16, 256
SOURCE_BASE, SHARED_BASE, MEMBER_BASE, EXECUTION_BASE, MIX_BASE = 318000, 319000, 320000, 321000, 322000
TARGETS = tuple(range(3, 27))+tuple(range(30, 78))
COSTS = (('low', '17/20'), ('low', '19/20'), ('high', '17/20'), ('high', '19/20'))
OUTPUT = ROOT/'reports/required_row_units_v260'
load, exact, rows = direct.load, direct.exact, direct.trajectory.read_rows


def native_bank():
    return [paid.empty() for _ in range(3)]


def state_for(life):
    return dict(life=life, pools={'A': native_bank(), 'B': native_bank()}, sources={'A': None, 'B': None},
        rounds=[], complete={'A': [[], [], []], 'B': [[], [], []]}, cursors={'A': 0, 'B': 0},
        generators={}, offsets=Counter(), step=0, source_paid=0, shared_paid=0, member_paid=0,
        execution_paid=0, tails=Counter(), interface=None, query_counts={'A': native_bank(), 'B': native_bank()},
        tape_position=0, round_position=0, batch_position=0, check_position=0, preview_position=0,
        source_position=0, phase_position=0, a_switch=None, return_merge=None)


def full_paid(state):
    return sum(state[field] for field in ('source_paid', 'shared_paid', 'member_paid', 'execution_paid'))


def budget(life, index, state, remaining=None):
    remaining = sum(target >= index for target in TARGETS) if remaining is None else remaining
    future = max(0, SOURCE_B-max(0, state['source_paid']-SOURCE_A))
    paid_samples = full_paid(state)
    return dict(cap=CAPS[life], fees={name: state[f'{name}_paid'] for name in ('source', 'shared', 'member', 'execution')},
        paid=paid_samples, future_B_source_reserved=future, remaining_targets=remaining,
        execution_reserved=2*remaining, available=CAPS[life]-paid_samples-future-2*remaining)


def cyclic_type(cursor, eligible):
    return next((cursor+offset)%3 for offset in range(3) if (cursor+offset)%3 in eligible)


def compatible_rounds(state, context, identity, required, arm):
    other = 'B' if context == 'A' else 'A'
    interface = state['interface']
    mapped = None if interface is None else (interface['b_to_a'].index(identity) if context == 'A'
                                             else interface['b_to_a'][identity])
    return [record for record in state['rounds']
        if set(required) <= set(record['declared_rows']) and (
            record['context'] == context and record['identity'] == identity
            or arm in ARMS[:2] and interface is not None and interface['changed_operator'] not in required
            and record['context'] == other and record['identity'] == mapped)]


def point_rounds(state, context, identity):
    return [record for record in state['rounds']
        if record['context'] == context and record['identity'] == identity
        and tuple(record['declared_rows']) == OPERATORS]


def declared_rows_for_plans(plans):
    """Only previous retained plans decide the next batch's observation mask."""
    if any(not execution_resolved(plan) for plan in plans):
        return list(OPERATORS)
    needed = set()
    for plan in plans:
        for query in ('goal', 'risk'):
            decision = plan['query_evidence']['queries'][query]
            for comparison in decision['comparisons']:
                if not comparison['certified']:
                    needed.update(direct.trajectory.specification(query, decision['policy'],
                        comparison['other'], plan['case']['retry_cost'])[0])
    return [operator for operator in OPERATORS if operator in needed]


def unit_outcomes(declared, outcomes):
    """Require real declared outcomes; conditional R absence needs no padding."""
    if tuple(declared) != tuple(operator for operator in OPERATORS if operator in declared):
        return False
    if R in declared and D not in declared:
        return False
    observed = set(declared)-{R}
    if R in declared and outcomes.get(D) == 'RECOVERY':
        observed.add(R)
    if set(outcomes) != set(declared):
        return False
    if R in declared and outcomes.get(D) != 'RECOVERY' and outcomes[R] is not None:
        return False
    return all(outcomes[operator] in ALPHABETS[operator] for operator in observed)


def execution_counts(state, context, identity, arm):
    counts = deepcopy(state['pools'][context][identity])
    interface = state['interface']
    if arm in ARMS[:2] and interface is not None:
        other = 'B' if context == 'A' else 'A'
        mapped = interface['b_to_a'].index(identity) if context == 'A' else interface['b_to_a'][identity]
        for operator in OPERATORS:
            if operator != interface['changed_operator']:
                for category, value in state['pools'][other][mapped][operator].items():
                    counts[operator][category] += value
    return counts


def execution_regions(life, index, context, identity, state, member, arm):
    if arm in ARMS[:2]:
        return continuous_regions(life, index, context, identity, state, member)
    result, interface = {}, state['interface']
    for operator in OPERATORS:
        event = f'l{life}/{context}/pool{identity}/{operator}'
        regions = [dict(counts=deepcopy(bank[identity][operator]), threshold=720, event=event)
                   for bank in (state['sources'][context], state['pools'][context])]
        regions.append(dict(counts=deepcopy(member[operator]), threshold=8640,
                            event=f'l{life}/member{index}/{operator}'))
        if arm in ARMS[:2] and interface is not None and operator != interface['changed_operator']:
            other = 'B' if context == 'A' else 'A'
            mapped = interface['b_to_a'].index(identity) if context == 'A' else interface['b_to_a'][identity]
            event = f'l{life}/{other}/pool{mapped}/{operator}'
            regions.extend(dict(counts=deepcopy(bank[mapped][operator]), threshold=720, event=event)
                           for bank in (state['sources'][other], state['pools'][other]))
        result[operator] = regions
    return result


def continuous_regions(life, index, context, identity, state, member):
    interface, result = state['interface'], {}
    for operator in OPERATORS:
        compatible = interface is not None and operator != interface['changed_operator']
        a_identity = interface['b_to_a'][identity] if compatible and context == 'B' else identity
        b_identity = interface['b_to_a'].index(a_identity) if compatible else None
        event = f'l{life}/A/pool{a_identity}/{operator}' if compatible else f'l{life}/{context}/pool{identity}/{operator}'

        def prefix(kind, entries):
            native = {ctx: dict(identity=slot, counts=deepcopy(counts)) for ctx, slot, counts in entries}
            counts = {category: sum(row['counts'][category] for row in native.values()) for category in ALPHABETS[operator]}
            return dict(counts=counts, threshold=720, event=event, prefix_kind=kind, native_context_counts=native)

        if compatible:
            source = state['sources']['A'][a_identity][operator]
            switch = state['a_switch'][a_identity][operator]
            b_source = state['sources']['B'][b_identity][operator]
            regions = [prefix('a_source', [('A', a_identity, source)]),
                prefix('a_switch', [('A', a_identity, switch)]),
                prefix('a_switch_plus_b_source', [('A', a_identity, switch), ('B', b_identity, b_source)]),
                prefix('continuous_current', [('A', a_identity, state['pools']['A'][a_identity][operator]),
                    ('B', b_identity, state['pools']['B'][b_identity][operator])])]
        else:
            regions = [dict(counts=deepcopy(bank[identity][operator]), threshold=720, event=event)
                       for bank in (state['sources'][context], state['pools'][context])]
        member_region = dict(counts=deepcopy(member[operator]), threshold=8640, event=f'l{life}/member{index}/{operator}')
        if compatible:
            member_region.update(prefix_kind='member', native_context_counts={})
        regions.append(member_region)
        result[operator] = regions
    return result


def audit_goal_upper(plan, case, check):
    point = exact(plan)
    _, dual, _ = coupled.box_proof(point, case)
    box = dual['value']
    proof = point['goal_feasibility']
    skipped = point['utility_lower'] >= 2 or box < 2
    reason = 'execution_certified' if point['utility_lower'] >= 2 else 'box_impossible' if box < 2 else None
    check('original_exact_box_goal_upper_and_frozen_feasibility_skip_rule',
        point['box_goal_upper'] == box and proof['box_goal_upper'] == box
        and proof['kind'] == 'coupled_goal_feasibility_v258' and proof['skipped'] == skipped
        and proof['skip_reason'] == reason and proof['risk_limit'] == F(1, 20) and proof['goal_threshold'] == 2)
    search = proof['search']
    check('frozen_goal_dual_search_bracket_and_configured_reductions',
          search['interval'] == [0, box/F(1, 20)] and search['configured_reductions'] == 20)
    if skipped:
        upper = box
        check('skipped_search_retains_original_decision_and_has_no_new_support',
              proof['winner'] is None and proof['old_dual'] is None
              and search['reductions'] == search['evaluations'] == 0 and search['trace'] == [])
    else:
        winner = proof['winner']
        lam = winner['lambda_value']
        check('exact_old_rectangle_dual_and_diagnostic_proposal_trace',
              proof['old_dual'] == dict(lambda_value=dual['lambda_value'], value=box)
              and search['reductions'] == 20 and search['evaluations'] == len(search['trace'])
              and 0 <= lam <= box/F(1, 20)
              and len({row['lambda_value'] for row in search['trace']}) == search['evaluations']
              and all(0 <= row['lambda_value'] <= box/F(1, 20) for row in search['trace'])
              and {0, box/F(1, 20), dual['lambda_value'], lam}
                  <= {row['lambda_value'] for row in search['trace']})
        s, q = (point['envelopes'][operator]['bounds']['DELIVERY'][1] for operator in (S, R))
        check('winning_dual_binary_CS_uppers_and_retry_monotonicity',
              winner['binary_upper'] == {S: s, R: q} and 0 <= s <= 1 and 0 <= q <= 1 and 4+lam > 0)
        coefficients = coupled.branch_coefficients(case, lam, q)
        check('two_winning_original_D_support_directions', set(winner['d_supports']) == set(coefficients))
        for policy in ('DETOUR_RETURN', 'DETOUR_RETRY'):
            support = winner['d_supports'][policy]
            check('winning_D_support_exact_goal_minus_lambda_risk_coefficients',
                  support['coefficients'] == coefficients[policy])
            check('winning_D_weak_dual_outward_100_digit_evidence',
                  execution.joint.audit_support(point['joint_constraints'][D], coefficients[policy], support['support']))
        short_cost, detour_cost = execution.joint.COSTS[case['operating']]
        branches = dict(WAIT=F(0), SHORT=-short_cost-lam+(4+lam)*s,
            DETOUR_RETURN=-detour_cost+winner['d_supports']['DETOUR_RETURN']['support']['upper'],
            DETOUR_RETRY=-detour_cost+winner['d_supports']['DETOUR_RETRY']['support']['upper'])
        candidate = lam*F(1, 20)+max(branches.values())
        check('winning_four_coupled_branches_and_exact_candidate',
              winner['branches'] == branches and winner['candidate_upper'] == candidate)
        upper = min(box, candidate)
    check('safe_minimum_original_box_and_winning_dual_strict_impossibility',
          proof['upper'] == point['goal_upper'] == upper <= box
          and proof['old_impossible'] == (box < 2)
          and proof['new_impossible'] == point['goal_impossible'] == (upper < 2))
    return upper


def audit_execution_plan(saved, case, counts, constraints, projection_cache, check):
    point, posterior = exact(saved), paid.posterior(counts)
    check('native_rows_and_eligible_execution_rows_paid_once', point['case'] == exact(case)
        and point['evidence_counts'] == counts and point['posterior'] == posterior
        and point['effective_n'] == {operator: sum(row.values()) for operator, row in counts.items()}
        and point['joint_constraints'] == constraints
        and all(point['envelopes'][operator]['counts'] == counts[operator]
                and point['envelopes'][operator]['n'] == sum(counts[operator].values()) for operator in OPERATORS))
    key = execution.freeze({operator: [{field: region[field] for field in ('counts', 'threshold')}
        for region in regions] for operator, regions in constraints.items()})
    projection = dict(supports=point['projection_supports'],
                      bounds={operator: point['envelopes'][operator]['bounds'] for operator in OPERATORS})
    if projection_cache.get(key) != projection:
        execution.audit_projection(constraints, saved, check)
        projection_cache[key] = projection
    risks = execution.math.prior.settled.risk_bounds(point['envelopes'])
    goals = execution.math.prior.settled.goal_bounds(point['envelopes'], case)
    check('unchanged_execution_row_posterior_vectors_robust_goals_and_risks',
        point['pure_vectors'] == execution.joint.vectors(case, posterior)
        and point['risks'] == risks and point['goals_lower'] == goals)
    check('actual_execution_mix_and_original_risk_bound', all(weight >= 0 for _, weight in point['mix'])
        and sum(weight for _, weight in point['mix']) == 1
        and point['risk_upper'] == sum(weight*risks[policy] for policy, weight in point['mix']) <= F(1, 20)
        and point['utility_lower'] == sum(weight*goals[policy] for policy, weight in point['mix']))
    audit_goal_upper(saved, case, check)


def audit_row_method(saved, arm, check):
    check('predeclared_fixed_arm_row_confidence_method',
        saved.get('row_confidence_kind') == 'continuous_compatible_jeffreys_prefixes' if arm in ARMS[:2]
        else 'row_confidence_kind' not in saved)


def realized_vector(case, policy, observations):
    short_cost, detour_cost = direct.trajectory.COSTS[case['operating']]
    if policy == 'WAIT':
        return [F(0), F(0), F(0)]
    outcome = observations[S if policy == 'SHORT' else D]
    reward = -short_cost if policy == 'SHORT' else -detour_cost
    if policy == 'DETOUR_RETRY' and outcome == 'RECOVERY':
        outcome, reward = observations[R], reward-F(case['retry_cost'])
    return [reward, F(outcome == 'LOST'), F(outcome == 'DELIVERY')]


def sample_mixture(mix, coin):
    cumulative = F(0)
    for policy, weight in exact(mix):
        cumulative += weight
        if F(coin) < cumulative:
            return policy


def execution_resolved(plan):
    return F(plan['utility_lower']) >= 2 or plan['goal_impossible']


def jointly_ready(plan):
    return execution_resolved(plan) and plan['query_ready']


def audit_profile(profile, round_map, arm, check):
    certificate, case = profile['certificate'], profile['case']
    id_field = 'admitted_unit_ids' if arm == ARMS[0] else 'admitted_round_ids'
    admitted = [round_map[identifier] for identifier in certificate[id_field]]
    check('private_direct_profile_original_round_ids_and_context_counts',
          certificate[id_field] == sorted(set(certificate[id_field]))
          and certificate['admitted_by_context'] == {context: sum(record['context'] == context for record in admitted)
                                                    for context in ('A', 'B')}
          and certificate['cross_context'] == any(record['context'] != case['context'] for record in admitted))
    required = direct.trajectory.specification(certificate['query'], certificate['chosen'],
        certificate['other'], case['retry_cost'])[0]
    check('every_admitted_unit_predeclared_all_required_rows_and_only_actual_outcomes',
          all(set(required) <= set(record['declared_rows'])
              and unit_outcomes(record['declared_rows'], record['outcomes']) for record in admitted))
    proof = deepcopy(certificate)
    if arm == ARMS[0]:
        check('partial_score_source_is_declared_unit_not_paired_or_imputed_rows',
              certificate['score_source'] == 'actual_declared_required_row_units')
        # Reuse only established score/bet/outward-product mathematics. The
        # observed score list is computed directly from these actual units.
        proof['score_source'] = 'actual_complete_conditional_rounds'
    return direct.audit_direct_comparison([record['outcomes'] for record in admitted], case,
        certificate['query'], certificate['chosen'], certificate['other'], proof, check, {})


def audit_query(saved, case, identity, state, arm, profiles, decisions, used, point_cache, check):
    context = case['context']
    native = point_rounds(state, context, identity)
    outcomes = [record['outcomes'] for record in native]
    key = context, identity, len(native), case['operating'], F(case['retry_cost'])
    if key not in point_cache:
        point_cache[key] = direct.empirical_vectors(outcomes, case)
    vectors, chosen = point_cache[key], direct.point_queries(point_cache[key])
    check('query_choices_from_native_complete_rounds_only_with_lexical_ties',
        saved['case'] == case and exact(saved['query_pure_vectors']) == vectors
        and saved['queries'] == {query: dict(policy=policy) for query, policy in chosen.items()}
        and saved['native_round_ids'] == [record['round_id'] for record in native]
        and saved['native_complete_rounds'] == len(native)
        and saved['native_joint_outcome_counts'] == direct.joint_histogram(outcomes))
    if arm == ARMS[0]:
        check('partial_units_do_not_update_complete_point_history_even_when_D_does_not_recover',
              saved['native_unit_ids'] == [record['round_id'] for record in state['rounds']
                  if record['context'] == context and record['identity'] == identity])
    evidence, ready = saved['query_evidence'], dict(reward=True)
    check('direct_original_event_threshold_and_known_reward', evidence['threshold'] == 4320
          and evidence['queries']['reward'] == dict(policy='WAIT', certified=True, kind='known_nonnegative_cost'))
    blockers = dict(reward=[])
    for query in ('goal', 'risk'):
        decision, selected = evidence['queries'][query], chosen[query]
        alternatives = [policy for policy in POLICIES if policy != selected]
        check('all_fixed_ordered_direct_alternatives_in_original_order', decision['policy'] == selected
              and [reference['other'] for reference in decision['comparisons']] == alternatives)
        results, blockers[query] = [], []
        for reference, other in zip(decision['comparisons'], alternatives):
            identifier = reference['profile_id']
            used.add(identifier)
            profile, certificate = profiles[identifier], profiles[identifier]['certificate']
            required = direct.trajectory.specification(query, selected, other, case['retry_cost'])[0]
            admitted = compatible_rounds(state, context, identity, required, arm)
            id_field = 'admitted_unit_ids' if arm == ARMS[0] else 'admitted_round_ids'
            check('comparison_uses_declared_required_rows_compatible_current_prefix_without_future_or_duplicate',
                profile['query_identity'] == identity
                and exact(profile['case']) == exact({field: case[field] for field in ('operating', 'retry_cost', 'context')})
                and certificate['query'] == query and certificate['chosen'] == selected and certificate['other'] == other
                and certificate['required_rows'] == list(required)
                and certificate[id_field] == [record['round_id'] for record in admitted]
                and certificate['admitted_by_context'] == {ctx: sum(record['context'] == ctx for record in admitted) for ctx in ('A', 'B')}
                and certificate['cross_context'] == any(record['context'] != context for record in admitted)
                and reference['certified'] == certificate['certified'] == decisions[identifier])
            results.append(decisions[identifier])
            if not decisions[identifier]:
                blockers[query].append(other)
        ready[query] = len(results) == 3 and all(results)
        check('current_direct_three_alternatives_AND', decision['certified'] == ready[query])
    certificates = {query: dict(policy=chosen[query], certified=ready[query],
        regret_upper=F(0) if query == 'reward' else F(1, 20) if ready[query] else F(20)) for query in QUERIES}
    markers = {query: {policy: F(policy in blockers[query]) for policy in POLICIES} for query in QUERIES}
    check('joint_current_query_ready_and_original_V231_acquisition_fields',
        evidence['all_ready'] == saved['query_ready'] == all(ready.values())
        and exact(saved['query_certificates']) == certificates
        and saved['query_blockers'] == blockers and exact(saved['query_gap_bounds']) == markers
        and saved['query_gap_bounds_kind'] == 'uncertified_comparison_marker_not_regret_bound')
    return ready


def replay_observation(life, phase, context, identity, index, operator, state, law):
    base = {'SOURCE': SOURCE_BASE, 'SHARED': SHARED_BASE, 'MEMBER': MEMBER_BASE, 'EXECUTION': EXECUTION_BASE}[phase]
    slot = identity+(3 if context == 'B' else 0)
    seed = base+((life*6+slot)*3 if phase in ('SOURCE', 'SHARED') else (life*78+index)*3)+OPERATORS.index(operator)
    key = phase, context, identity, None if phase in ('SOURCE', 'SHARED') else index, operator
    if key not in state['generators']:
        state['generators'][key] = random.Random(seed)
    offset = state['offsets'][key]
    increments = paid.draw(state['generators'][key], law, operator, 1)
    outcome = next(category for category, value in increments.items() if value)
    state['offsets'][key] += 1
    state['step'] += 1
    state[{'SOURCE': 'source_paid', 'SHARED': 'shared_paid', 'MEMBER': 'member_paid', 'EXECUTION': 'execution_paid'}[phase]] += 1
    state['pools'][context][identity][operator][outcome] += 1
    return dict(seed=seed, draw_start=offset, draw_end=offset+1, outcome=outcome)


def actual_query_scores(saved, law):
    scores = direct.score_queries(saved['queries'], saved['case'], law)
    false = sum(saved['query_certificates'][query]['certified'] and scores[query]['regret'] > F(1, 20) for query in QUERIES)
    return scores, false


def score_execution(saved, law):
    plan = exact(saved)
    vectors = execution.joint.vectors(saved['case'], law)
    actual = [sum(weight*vectors[policy][coordinate] for policy, weight in plan['mix']) for coordinate in range(3)]
    utility, risk = actual[0]+4*actual[2], actual[1]
    optimum = paid.oracle_goal(vectors)
    return dict(actual_utility=utility, actual_risk=risk, true_optimum=optimum,
        execution_certified=plan['utility_lower'] >= 2, execution_resolved=execution_resolved(plan),
        goal_impossible=plan['goal_impossible'], query_certified=plan['query_ready'], joint_completed=jointly_ready(plan),
        false_execution_certificate=plan['utility_lower'] >= 2 and (utility < 2 or risk > F(1, 20)),
        false_impossible_certificate=plan['goal_impossible'] and optimum >= 2,
        false_goal_upper=optimum > plan['goal_upper'], false_utility_lower=utility < plan['utility_lower'],
        false_risk_upper=risk > plan['risk_upper'], risk_violation=risk > F(1, 20),
        new_impossible_vs_box=plan['goal_impossible'] and plan['box_goal_upper'] >= 2,
        box_goal_upper=plan['box_goal_upper'], goal_upper=plan['goal_upper'],
        utility_lower=plan['utility_lower'], risk_upper=plan['risk_upper'], nonlooser_goal_upper=plan['goal_upper'] <= plan['box_goal_upper'])


def score_execution_history(row, law):
    plans = [(row['initial_plan'], 0)]+[(batch['plan'], batch['spent']) for batch in row['batches']]
    return [dict(**{field: row[field] for field in ('life', 'arm', 'index', 'identity')},
        prefix_position=position, spent=spent, is_terminal=position == len(plans)-1,
        **score_execution(plan, law)) for position, (plan, spent) in enumerate(plans)]


def score_target(row, law):
    # The old exact scorer handles every initial/member/terminal execution
    # envelope and the actual frozen mix; direct choices are supplied explicitly.
    result = execution.score_history(row, law)
    result['actual_execution'] = row['actual_execution']
    result['new_impossible_vs_box'] = row['terminal_plan']['goal_impossible'] and F(row['terminal_plan']['box_goal_upper']) >= 2
    return result


def replay_primitive(life, arm, phase, context, identity, index, operator, state, tape, laws,
                     check, round_id=None, batch_id=None, role=None, cursor_before=None):
    law_index = identity if context == 'A' else 27+identity
    if phase in ('MEMBER', 'EXECUTION'):
        law_index = index
    observed = replay_observation(life, phase, context, identity, index, operator, state, laws[law_index])
    expected = dict(life=life, arm=arm, phase=phase, context=context, identity=identity, index=index,
        step_index=state['step'], operator=operator, round_id=round_id, batch_id=batch_id, role=role,
        cursor_before=cursor_before, **observed)
    check('actual_paired_primitive_law_seed_phase_offset_order_role_and_native_fee', tape[state['tape_position']] == expected)
    state['tape_position'] += 1
    return expected


def replay_conditional_batch(life, arm, phase, context, index, amount, eligible, prior_check,
                             state, tapes, round_records, batches, laws, check, declarations=None, preview_refs=None):
    identifier, before_step, cursor = state['batch_position'], state['step'], state['cursors'][context]
    before_rounds, before_budget = len(state['rounds']), budget(life, index, state)
    declarations = [list(OPERATORS) for _ in range(3)] if declarations is None else declarations
    target, tails, complete, partial = before_step+amount, 0, 0, 0
    while state['step'] < target:
        previous_cursor = state['cursors'][context]
        identity = cyclic_type(previous_cursor, eligible)
        state['cursors'][context] = identity+1
        declared = declarations[identity]
        check('unit_mask_frozen_before_its_outcomes_and_R_has_D_trigger',
              bool(declared) and (R not in declared or D in declared))
        if target-state['step'] < len(declared):
            primitive = replay_primitive(life, arm, phase, context, identity, None, S, state, tapes, laws, check,
                batch_id=identifier, role='tail_S', cursor_before=previous_cursor)
            state['query_counts'][context][identity][S][primitive['outcome']] += 1
            state['tails'][context, identity] += 1
            tails += 1
            continue
        round_id, steps, observations = len(state['rounds'])+1, [], {}
        unit_budget = budget(life, index, state)
        for operator in OPERATORS:
            if operator not in declared or operator == R and observations[D] != 'RECOVERY':
                continue
            primitive = replay_primitive(life, arm, phase, context, identity, None, operator, state, tapes, laws, check,
                round_id=round_id, batch_id=identifier, role={S: 'S', D: 'D', R: 'R'}[operator],
                cursor_before=previous_cursor)
            steps.append(primitive['step_index'])
            observations[operator] = primitive['outcome']
        if R in declared and R not in observations:
            observations[R] = None
        expected = dict(life=life, arm=arm, phase=phase, context=context, identity=identity, round_id=round_id,
            batch_id=identifier, start_step=steps[0], end_step=steps[-1], primitive_steps=steps,
            outcomes=observations, declared_rows=list(declared), all_rows_declared=tuple(declared) == OPERATORS,
            maximum_calls_reserved=len(declared), budget_before=unit_budget)
        check('predeclared_unit_actual_fields_steps_maximum_reserve_no_offpath_R_or_imputation',
              round_records[state['round_position']] == expected and unit_outcomes(declared, observations))
        state['round_position'] += 1
        state['rounds'].append(expected)
        if tuple(declared) == OPERATORS:
            complete += 1
            state['complete'][context][identity].append(observations)
            for operator, outcome in observations.items():
                if outcome is not None:
                    state['query_counts'][context][identity][operator][outcome] += 1
        else:
            partial += 1
    expected = dict(life=life, arm=arm, phase=phase, context=context, index=index, batch_id=identifier,
        prior_check_id=prior_check, eligible_types_frozen=list(eligible), declared_rows_by_type=declarations,
        preview_ids_by_type=preview_refs,
        start_step=before_step, end_step=state['step'], actual_samples=amount,
        cursor_before=cursor, cursor_after=state['cursors'][context],
        observation_units=len(state['rounds'])-before_rounds, complete_rounds=complete, partial_units=partial,
        standalone_S_tails=tails,
        budget_before=before_budget, budget_after=budget(life, index, state))
    check('batch_predeclared_masks_prior_check_cyclic_cursor_clamp_and_all_physical_fees', batches[identifier] == expected)
    state['batch_position'] += 1
    return identifier


def replay_source(life, arm, context, index, state, data, laws, check):
    amount = SOURCE_A if context == 'A' else SOURCE_B
    batch_id = replay_conditional_batch(life, arm, 'SOURCE', context, index, amount, [0, 1, 2], None,
        state, data['tapes'], data['rounds'], data['batches'], laws, check)
    state['sources'][context] = deepcopy(state['pools'][context])
    expected = dict(life=life, arm=arm, context=context, index=index, batch_id=batch_id,
        source_counts=state['sources'][context], actual_samples=amount,
        source_round_ids=[record['round_id'] for record in state['rounds'] if record['phase'] == 'SOURCE' and record['context'] == context],
        cursor=state['cursors'][context], budget=budget(life, index, state))
    check('chronological_source_native_snapshot_and_actual_complete_source_fees', data['sources'][state['source_position']] == expected)
    state['source_position'] += 1


def audit_shared_check(life, arm, stage, context, index, state, data, profiles, decisions, used,
                       point_cache, projection_cache, check):
    identifier, readiness, references = state['check_position'], [True]*3, []
    declarations, references_by_type = [], []
    for identity in range(3):
        plans, type_refs = [], []
        for cost_index, (operating, retry) in enumerate(COSTS):
            case = dict(id=f'v260_l{life}_{stage}_t{identity}_c{cost_index}', context=context,
                        stage=stage, operating=operating, retry_cost=retry)
            preview_id = identifier*12+identity*4+cost_index
            saved = data['previews'][state['preview_position']]
            check('all12_public_auxiliary_case_ids_costs_current_prefix_and_paid_budget',
                {field: saved[field] for field in ('life', 'arm', 'stage', 'context', 'index', 'check_id', 'identity', 'cost_index', 'preview_id', 'budget')}
                == dict(life=life, arm=arm, stage=stage, context=context, index=index, check_id=identifier,
                        identity=identity, cost_index=cost_index, preview_id=preview_id, budget=budget(life, index, state)))
            counts = execution_counts(state, context, identity, arm)
            constraints = execution_regions(life, index, context, identity, state, paid.empty(), arm)
            audit_row_method(saved['plan'], arm, check)
            audit_execution_plan(saved['plan'], case, counts, constraints, projection_cache, check)
            ready = audit_query(saved['plan'], case, identity, state, arm, profiles, decisions, used, point_cache, check)
            readiness[identity] = readiness[identity] and all(ready.values()) and execution_resolved(saved['plan'])
            references.append(preview_id)
            type_refs.append(preview_id)
            plans.append(saved['plan'])
            state['preview_position'] += 1
        declarations.append(declared_rows_for_plans(plans) if arm == ARMS[0] else list(OPERATORS))
        references_by_type.append(type_refs)
    expected = dict(life=life, arm=arm, stage=stage, context=context, index=index, check_id=identifier,
        preview_ids=references, ready_by_type=readiness, all_ready=all(readiness), cursor=state['cursors'][context],
        budget=budget(life, index, state), declared_rows_by_type=declarations,
        preview_ids_by_type=references_by_type)
    check('all12_current_query_AND_execution_resolved_shared_check_no_latched_readiness', data['checks'][identifier] == expected)
    state['check_position'] += 1
    return expected


def replay_shared_phase(life, arm, stage, context, index, state, data, laws, profiles, decisions, used,
                        point_cache, projection_cache, check):
    before, shared_before = budget(life, index, state), state['shared_paid']
    current = audit_shared_check(life, arm, stage, context, index, state, data, profiles, decisions, used,
                                 point_cache, projection_cache, check)
    initial, identifiers, batches = current['check_id'], [current['check_id']], []
    while not current['all_ready'] and budget(life, index, state)['available'] > 0:
        eligible = [identity for identity in range(3) if not current['ready_by_type'][identity]]
        amount = min(SHARED_BATCH, budget(life, index, state)['available'])
        batches.append(replay_conditional_batch(life, arm, 'SHARED', context, index, amount, eligible, current['check_id'],
            state, data['tapes'], data['rounds'], data['batches'], laws, check,
            current['declared_rows_by_type'], current['preview_ids_by_type']))
        current = audit_shared_check(life, arm, stage, context, index, state, data, profiles, decisions, used,
                                     point_cache, projection_cache, check)
        identifiers.append(current['check_id'])
    expected = dict(life=life, arm=arm, stage=stage, context=context, index=index, initial_check_id=initial,
        final_check_id=current['check_id'], check_ids=identifiers, batch_ids=batches,
        paid_samples=state['shared_paid']-shared_before, final_ready_by_type=current['ready_by_type'],
        stop_reason='all_ready' if current['all_ready'] else 'budget_exhausted', budget_before=before,
        budget_after=budget(life, index, state))
    check('shared_phase_first_current_all12_stop_or_actual_available_exhaustion', data['phases'][state['phase_position']] == expected)
    state['phase_position'] += 1


def replay_execution(life, arm, index, case, identity, mix, state, data, laws, check):
    before, remaining = budget(life, index, state), sum(target >= index for target in TARGETS)
    seed = MIX_BASE+life*78+index
    coin = F(random.Random(seed).random())
    selected = sample_mixture(mix, coin)
    steps, observations = [], {}
    if selected != 'WAIT':
        operator = S if selected == 'SHORT' else D
        primitive = replay_primitive(life, arm, 'EXECUTION', case['context'], identity, index, operator,
            state, data['tapes'], laws, check, role=selected)
        observations[operator] = primitive['outcome']
        steps.append(primitive['step_index'])
        if selected == 'DETOUR_RETRY' and primitive['outcome'] == 'RECOVERY':
            primitive = replay_primitive(life, arm, 'EXECUTION', case['context'], identity, index, R,
                state, data['tapes'], laws, check, role=selected)
            observations[R] = primitive['outcome']
            steps.append(primitive['step_index'])
    reward, failure, delivery = realized_vector(case, selected, observations)
    realized = dict(reward=reward, failure=int(failure), delivery=int(delivery),
        terminal='WON' if delivery else 'LOST' if failure else 'ABORT',
        goal_utility=reward+4*delivery, risk_utility=reward-4*failure+4*delivery)
    return dict(mix_seed=seed, mix_coin=coin, selected_policy=selected, primitive_steps=steps,
        outcomes=observations, actual_samples=len(steps), realized=realized,
        released_execution_reserve=2-len(steps), budget_before=before,
        budget_after=budget(life, index, state, remaining-1))


def expected_final_state(life, arm, state, interface):
    trajectory = {}
    for context in ('A', 'B'):
        trajectory[context] = []
        for identity in range(3):
            native = point_rounds(state, context, identity)
            trajectory[context].append(dict(native_counts=state['query_counts'][context][identity],
                rounds=[record['outcomes'] for record in native],
                joint_outcome_counts=direct.joint_histogram([record['outcomes'] for record in native]),
                tail_s_samples=state['tails'][context, identity], round_prefix_last_id=native[-1]['round_id'] if native else None))
    return dict(life=life, arm='TWO_WAY' if arm in ARMS[:2] else 'REBUILD',
        a=dict(sources=state['sources']['A'], pools=state['pools']['A']),
        b=dict(sources=state['sources']['B'], pools=state['pools']['B']),
        a_at_switch=dict(sources=state['sources']['A'], pools=state['a_switch']),
        changed_operator=interface['changed_operator'], b_to_a=interface['b_to_a'], return_merge=state['return_merge'],
        acquisition_arm=arm, research_arm='CONTINUOUS_REUSE' if arm in ARMS[:2] else 'TRAJECTORY_REBUILD',
        trajectory_arm='TRAJECTORY_REUSE' if arm in ARMS[:2] else 'TRAJECTORY_REBUILD',
        trajectory=trajectory, round_log=state['rounds'])


def audit_life_arm(job):
    life, arm = job
    begun, checks, failures, location = perf_counter(), Counter(), [], dict(life=life, arm=arm)

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    kinds = ('tapes', 'rounds', 'sources', 'batches', 'previews', 'checks', 'phases', 'profiles', 'decisions', 'records')
    data = {kind: rows(OUTPUT/f'{kind}_life_{life:02d}_{arm}.jsonl.gz') for kind in kinds}
    results_saved = rows(OUTPUT/f'results_life_{life:02d}_{arm}.jsonl.gz')
    auxiliary_saved = rows(OUTPUT/f'preview_results_life_{life:02d}_{arm}.jsonl.gz')
    execution_history_saved = rows(OUTPUT/f'execution_history_results_life_{life:02d}_{arm}.jsonl.gz')
    cases, laws, identities, interface = paid.world(life)
    profiles, used, decisions, point_cache, projection_cache = data['profiles'], set(), {}, {}, {}
    check('all_private_direct_profile_ids_literal_order', [profile['profile_id'] for profile in profiles] == list(range(len(profiles))))
    round_map = {record['round_id']: record for record in data['rounds']}
    check('all_complete_round_ids_original_global_chronology', list(round_map) == list(range(1, len(data['rounds'])+1)))
    for profile in profiles:
        location = dict(life=life, arm=arm, profile_id=profile['profile_id'])
        decisions[profile['profile_id']] = audit_profile(profile, round_map, arm, check)
    state, plan_count, member_batches = state_for(life), 0, 0
    check('all72_target_decisions_actual_executions_and_results_retained',
          len(data['records']) == len(data['decisions']) == len(results_saved) == 72)
    replay_source(life, arm, 'A', 3, state, data, laws, check)
    replay_shared_phase(life, arm, 'A', 'A', 3, state, data, laws, profiles, decisions, used,
                        point_cache, projection_cache, check)
    scored, execution_history = [], []
    for position, index in enumerate(TARGETS):
        location = dict(life=life, arm=arm, index=index)
        if index == 30:
            state['a_switch'] = deepcopy(state['pools']['A'])
            state['interface'] = interface
            replay_source(life, arm, 'B', 30, state, data, laws, check)
            replay_shared_phase(life, arm, 'B', 'B', 30, state, data, laws, profiles, decisions, used,
                                point_cache, projection_cache, check)
        if index == 54:
            replay_shared_phase(life, arm, 'A_RETURN', 'A', 54, state, data, laws, profiles, decisions, used,
                                point_cache, projection_cache, check)
            if arm in ARMS[:2]:
                old_sources = {'a': state['sources']['A'], 'b': state['sources']['B']}
                old_state = dict(a=state['pools']['A'], b=state['pools']['B'], a_switch=state['a_switch'])
                state['return_merge'] = execution.transfer_ledger(life, index, old_sources, old_state, interface)
        row, case, identity = data['records'][position], cases[index], identities[index]
        context, before = case['context'], budget(life, index, state)
        pool = state['pools'][context][identity]
        check('chronological_public_target_identity_and_own_native_pool_before_planning',
              (row['life'], row['arm'], row['index'], row['identity'], row['case']) == (life, arm, index, identity, case)
              and row['pooled_before'] == pool and row['budget_before'] == before
              and (context != 'B' or state['pools']['A'] == state['a_switch']))
        member, spent = paid.empty(), 0

        def plan_check(saved):
            nonlocal plan_count
            counts = execution_counts(state, context, identity, arm)
            constraints = execution_regions(life, index, context, identity, state, member, arm)
            audit_row_method(saved, arm, check)
            audit_execution_plan(saved, case, counts, constraints, projection_cache, check)
            audit_query(saved, case, identity, state, arm, profiles, decisions, used, point_cache, check)
            plan_count += 1

        current = row['initial_plan']
        plan_check(current)
        for batch in row['batches']:
            check('member_only_while_execution_unresolved_with_current_full_reservations',
                  not execution_resolved(current) and spent+MEMBER_BATCH <= MEMBER_CAP
                  and budget(life, index, state)['available'] >= MEMBER_BATCH)
            choice = allocation.original_choice(member, current)
            check('unchanged_V231_actual_query_markers_and_execution_acquisition_choice', exact(batch['choice']) == choice)
            operator, offset, increments, primitive_steps = choice['operator'], sum(member[choice['operator']].values()), dict.fromkeys(ALPHABETS[choice['operator']], 0), []
            for _ in range(MEMBER_BATCH):
                primitive = replay_primitive(life, arm, 'MEMBER', context, identity, index, operator, state, data['tapes'], laws, check, role='member')
                increments[primitive['outcome']] += 1
                primitive_steps.append(primitive['step_index'])
            for category, value in increments.items():
                member[operator][category] += value
            spent += MEMBER_BATCH
            member_batches += 1
            check('actual_member_batch_draw_offsets_refs_increment_and_cost',
                  batch['operator'] == operator and batch['draw_start'] == offset and batch['draw_end'] == offset+MEMBER_BATCH
                  and batch['increments'] == increments and batch['primitive_steps'] == primitive_steps and batch['spent'] == spent)
            current = batch['plan']
            plan_check(current)
        terminal, completed = row['terminal_plan'], jointly_ready(current)
        resolved, terminal_budget, terminal_pool = execution_resolved(current), budget(life, index, state), deepcopy(pool)
        mix = exact(terminal['mix']) if completed else [['WAIT', F(1)]]
        reason = 'joint_ready' if completed else 'direct_unresolved_no_shared_budget' if resolved else 'member_cap' if spent == MEMBER_CAP else 'budget_exhausted'
        check('first_execution_resolution_or_member_cap_or_reserved_budget_stop',
              terminal == current and (resolved or spent == MEMBER_CAP or terminal_budget['available'] < MEMBER_BATCH))
        frozen = dict(life=life, arm=arm, index=index, identity=identity, terminal_plan=terminal,
                      executed_mix=mix, member=member, pooled_after_terminal=terminal_pool, budget=terminal_budget)
        check('terminal_mix_member_and_native_pool_frozen_before_any_execution_feedback', exact(data['decisions'][position]) == exact(frozen))
        check('terminal_fees_flags_and_WAIT_fallback_before_actual_execution',
            row['member'] == member and row['spent'] == paid.samples(member) == spent
            and row['pooled_after_terminal'] == terminal_pool and row['budget_terminal'] == terminal_budget
            and row['source_paid_samples'] == state['source_paid'] and row['shared_paid_before'] == before['fees']['shared']
            and row['history_paid_samples'] == before['fees']['member'] and row['execution_paid_before'] == before['fees']['execution']
            and row['execution_certified'] == (F(terminal['utility_lower']) >= 2) and row['execution_resolved'] == resolved
            and row['goal_impossible'] == terminal['goal_impossible'] and row['query_certified'] == terminal['query_ready']
            and row['joint_completed'] == completed and row['fallback'] == (not completed) and row['stop_reason'] == reason
            and row['budget_exhausted'] == (terminal_budget['available'] < MEMBER_BATCH)
            and row['member_cap_exhausted'] == (spent == MEMBER_CAP) and exact(row['executed_mix']) == mix)
        executed = replay_execution(life, arm, index, case, identity, mix, state, data, laws, check)
        check('exact_mix_coin_actual_legal_policy_path_realized_outcome_fee_and_released_reserve', exact(row['actual_execution']) == executed)
        check('execution_observations_added_after_terminal_only_to_later_native_pool',
              row['pooled_after_execution'] == pool and row['budget_after'] == executed['budget_after']
              and row['member'] == member and row['terminal_plan'] == terminal)
        check('actual_target_model_CPU_and_acquisition_subset_nonnegative', row['model_seconds'] >= 0
              and 0 <= row['acquisition_seconds'] <= row['model_seconds'])
        independent = score_target(row, laws[index])
        check('all_frozen_history_expected_mix_risk_and_realized_execution_posthoc_truth', exact(results_saved[position]) == exact(independent))
        scored.append(independent)
        execution_history.extend(score_execution_history(row, laws[index]))
        print(f'audit life={life} arm={arm} index={index} paid={state["step"]} joint={completed}', flush=True)
    check('all_initial_member_terminal_numeric_upper_lower_risk_claims_posthoc_true_scored',
          exact(execution_history_saved) == exact(execution_history))
    auxiliary = []
    for preview in data['previews']:
        law = laws[preview['identity'] if preview['context'] == 'A' else 27+preview['identity']]
        queries, false = actual_query_scores(preview['plan'], law)
        auxiliary.append(dict(**{field: preview[field] for field in ('life', 'arm', 'preview_id', 'check_id', 'index', 'stage', 'context', 'identity', 'cost_index')},
            queries=queries, false_query_certificates=false, **score_execution(preview['plan'], law)))
    check('all_full_auxiliary_query_and_execution_upper_lower_risk_claims_scored_only_after_freeze', exact(auxiliary_saved) == exact(auxiliary))
    check('all_sources_rounds_batches_auxiliary_phases_and_physical_calls_consumed_once',
        state['step'] == len(data['tapes']) == state['tape_position'] == full_paid(state)
        and state['round_position'] == len(data['rounds']) and state['batch_position'] == len(data['batches'])
        and state['source_position'] == len(data['sources']) == 2 and state['phase_position'] == len(data['phases']) == 3
        and state['check_position'] == len(data['checks']) and state['preview_position'] == len(data['previews']) == len(auxiliary)
        and state['source_paid'] == 4608 and full_paid(state) <= CAPS[life])
    check('all_private_direct_profiles_referenced_by_actual_retained_plan_or_aux', used == set(range(len(profiles))))
    artifact = load(OUTPUT/f'worker_artifacts_life_{life:02d}_{arm}.json')
    check('exact_final_native_sources_switch_query_rounds_and_no_inherited_round_duplication',
          artifact['final_state'] == expected_final_state(life, arm, state, interface))
    check('actual_full_fee_components_source_shared_member_execution_and_final_cursors',
        artifact['life'] == life and artifact['arm'] == arm and artifact['remaining_targets'] == 0
        and artifact['fees'] == budget(life, 78, state)['fees'] and artifact['primitive_samples'] == state['step']
        and artifact['cursors'] == state['cursors'] and artifact['profiles'] == len(profiles)
        and artifact['auxiliary_records'] == len(auxiliary))
    for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
        check('physical_environment_calls_include_actual_execution_all_fee_components', artifact['work'].get(field, 0) == state['step'])
    complete_units = sum(tuple(record['declared_rows']) == OPERATORS for record in state['rounds'])
    partial_units = len(state['rounds'])-complete_units
    check('actual_complete_partial_predeclared_units_and_standalone_S_tail_work',
        artifact['work'].get('declared_observation_units', 0) == len(state['rounds'])
        and artifact['work'].get('complete_conditional_rounds', 0) == complete_units
        and artifact['work'].get('partial_required_row_units', 0) == partial_units
        and artifact['work'].get('standalone_S_tails', 0) == sum(state['tails'].values())
        and artifact['work'].get('oracle_gap_direct_choices', 0) == member_batches
        and artifact['work']['trajectory_lifecycle_plans'] == plan_count+len(auxiliary))
    unit_accounting = dict(source_complete_units=sum(record['phase'] == 'SOURCE' for record in state['rounds']),
        source_tail_samples=sum(row['phase'] == 'SOURCE' and row['role'] == 'tail_S' for row in data['tapes']),
        shared_complete_units=sum(record['phase'] == 'SHARED' and tuple(record['declared_rows']) == OPERATORS for record in state['rounds']),
        shared_partial_units=partial_units,
        shared_tail_samples=sum(row['phase'] == 'SHARED' and row['role'] == 'tail_S' for row in data['tapes']))
    shared_by_operator = {operator: sum(row['phase'] == 'SHARED' and row['operator'] == operator for row in data['tapes']) for operator in OPERATORS}
    shared_sets = dict(Counter('|'.join(record['declared_rows']) for record in state['rounds'] if record['phase'] == 'SHARED'))
    check('all_physical_shared_row_fees_and_predeclared_full_partial_tail_units',
          artifact['unit_accounting'] == unit_accounting
          and artifact['shared_primitive_samples_by_operator'] == shared_by_operator
          and artifact['shared_declared_row_sets'] == shared_sets
          and sum(shared_by_operator.values()) == state['shared_paid'])
    all_plans = [plan for row in data['records'] for plan in
                 [row['initial_plan']]+[batch['plan'] for batch in row['batches']]]
    all_plans.extend(preview['plan'] for preview in data['previews'])
    proofs = [plan['goal_feasibility'] for plan in all_plans]
    evaluations = sum(proof['search']['evaluations'] for proof in proofs)
    check('actual_goal_feasibility_search_skip_support_and_interval_work',
        artifact['work'].get('goal_feasibility_bounds', 0) == len(proofs)
        and artifact['work'].get('goal_feasibility_skips', 0) == sum(proof['skipped'] for proof in proofs)
        and artifact['work'].get('goal_feasibility_candidate_evaluations', 0) == evaluations
        and artifact['work'].get('goal_feasibility_d_support_calls', 0) == 2*evaluations
        and artifact['work'].get('goal_feasibility_interval_reductions', 0)
            == sum(proof['search']['reductions'] for proof in proofs))
    score_keys = {}
    for profile in profiles:
        certificate = profile['certificate']
        retry = F(profile['case']['retry_cost']) if 'DETOUR_RETRY' in (certificate['chosen'], certificate['other']) else None
        id_field = 'admitted_unit_ids' if arm == ARMS[0] else 'admitted_round_ids'
        required = certificate['required_rows'] if arm == ARMS[0] else OPERATORS
        observations = tuple(tuple(round_map[identifier]['outcomes'].get(operator) for operator in required)
                             for identifier in certificate[id_field])
        score_keys[certificate['query'], certificate['chosen'], certificate['other'], retry, observations] = len(observations)
    direct_calls = 6*(plan_count+len(auxiliary))
    expected_work = dict(trajectory_certificate_evaluations=direct_calls,
        sampling_threshold_comparisons=sum(ALPHABETS[row['operator']].index(row['outcome'])+1 for row in data['tapes']),
        sampling_threshold_accumulations=sum(ALPHABETS[row['operator']].index(row['outcome'])+1 for row in data['tapes']))
    if arm == ARMS[0]:
        expected_work.update(required_unit_unique_score_prefixes=len(score_keys),
            required_unit_score_cache_hits=direct_calls-len(score_keys), required_unit_score_evaluations=sum(score_keys.values()))
    else:
        expected_work.update(trajectory_unique_score_prefixes=len(score_keys),
            trajectory_score_cache_hits=direct_calls-len(score_keys), trajectory_complete_score_evaluations=sum(score_keys.values()))
    check('actual_original_direct_score_cache_and_sampling_work',
          all(artifact['work'].get(field, 0) == value for field, value in expected_work.items())
          and artifact['cache_statistics']['direct_score_prefixes'] == len(score_keys))
    check('actual_model_observation_output_and_six_worker_CPU_wall_scopes',
        set(artifact['timings']) == {'initialization', 'begin_b', 'type_selection', 'row_pool_updates', 'trajectory_updates', 'query_previews', 'planning', 'execution_choice'}
        and all(value >= 0 for value in artifact['timings'].values())
        and 0 <= artifact['acquisition_seconds'] <= artifact['timings']['planning']
        and artifact['observation_seconds'] >= 0 and artifact['output_seconds'] >= 0 and artifact['worker_wall_seconds'] >= 0)
    for name, size in (('execution', 4096), ('query', 256)):
        stats = artifact['cache_statistics']['normalizers'][name]
        check('private_cold_life_arm_normalizer_cache_statistics', stats['maxsize'] == size
              and 0 <= stats['currsize'] <= min(stats['misses'], size) and stats['hits'] >= 0)
    signatures = [{field: primitive[field] for field in ('phase', 'context', 'identity', 'operator', 'role', 'cursor_before', 'seed', 'draw_start', 'draw_end', 'outcome')}
                  for primitive in data['tapes'] if primitive['phase'] == 'SOURCE']
    return dict(life=life, arm=arm, scored=scored, auxiliary=auxiliary, execution_history=execution_history,
        artifact=artifact, checks=checks,
        failures=failures, profiles=len(profiles), plans=plan_count, rounds=len(data['rounds']),
        projections=checks['terminal_projected_detour_box'], source_signature=signatures, elapsed_seconds=perf_counter()-begun)


MODEL_SCOPES = ('initialization', 'begin_b', 'type_selection', 'row_pool_updates', 'trajectory_updates', 'query_previews', 'planning', 'execution_choice')


def stage_aggregate(results):
    result = execution.aggregate(results)
    result.update(execution_resolved=sum(row['execution_certified'] or row['goal_impossible'] for row in results),
        execution_unresolved=sum(not (row['execution_certified'] or row['goal_impossible']) for row in results),
        query_unresolved=sum(not row['query_certified'] for row in results),
        query_only_unresolved=sum(not row['query_certified'] and (row['execution_certified'] or row['goal_impossible']) for row in results),
        execution_only_unresolved=sum(row['query_certified'] and not (row['execution_certified'] or row['goal_impossible']) for row in results),
        both_unresolved=sum(not row['query_certified'] and not (row['execution_certified'] or row['goal_impossible']) for row in results),
        new_impossible_vs_box=sum(row['new_impossible_vs_box'] for row in results),
        actual_execution_samples=sum(row['actual_execution']['actual_samples'] for row in results),
        realized_delivery=sum(row['actual_execution']['realized']['delivery'] for row in results),
        realized_failure=sum(row['actual_execution']['realized']['failure'] for row in results),
        realized_reward=sum(F(row['actual_execution']['realized']['reward']) for row in results),
        realized_goal_utility=sum(F(row['actual_execution']['realized']['goal_utility']) for row in results))
    return result


EXECUTION_ERRORS = ('false_execution_certificate', 'false_impossible_certificate', 'false_goal_upper',
                    'false_utility_lower', 'false_risk_upper', 'risk_violation')


def summarize(results, auxiliary, execution_history, artifacts):
    methods, lives = {}, []
    for arm in ARMS:
        own, jobs = [row for row in results if row['arm'] == arm], [job for job in artifacts if job['arm'] == arm]
        fees = {kind: sum(job['fees'][kind] for job in jobs) for kind in ('source', 'shared', 'member', 'execution')}
        methods[arm] = dict(stage_aggregate(own), fees=fees, total_samples=sum(fees.values()),
            unit_accounting={field: sum(job['unit_accounting'][field] for job in jobs)
                for field in ('source_complete_units', 'source_tail_samples', 'shared_complete_units', 'shared_partial_units', 'shared_tail_samples')},
            shared_primitive_samples_by_operator={operator: sum(job['shared_primitive_samples_by_operator'][operator] for job in jobs) for operator in OPERATORS},
            shared_declared_row_sets=dict(sum((Counter(job['shared_declared_row_sets']) for job in jobs), Counter())),
            aux_false_query_certificates=sum(row['false_query_certificates'] for row in auxiliary if row['arm'] == arm),
            auxiliary_execution_errors={field: sum(row[field] for row in auxiliary if row['arm'] == arm) for field in EXECUTION_ERRORS},
            history_execution_errors={field: sum(row[field] for row in execution_history if row['arm'] == arm) for field in EXECUTION_ERRORS},
            execution_history_snapshots=sum(row['arm'] == arm for row in execution_history),
            new_impossible_prefixes_vs_box=sum(row['new_impossible_vs_box'] for row in execution_history if row['arm'] == arm),
            aux_new_impossible_vs_box=sum(row['new_impossible_vs_box'] for row in auxiliary if row['arm'] == arm),
            all_goal_uppers_nonlooser_than_box=all(row['nonlooser_goal_upper'] for row in auxiliary+execution_history if row['arm'] == arm),
            auxiliary_records=sum(job['auxiliary_records'] for job in jobs),
            late_b=stage_aggregate([row for row in own if 42 <= row['index'] < 54]),
            a_return=stage_aggregate([row for row in own if row['stage'] == 'A_RETURN']),
            stages={stage: stage_aggregate([row for row in own if row['stage'] == stage]) for stage in ('A', 'B', 'A_RETURN')},
            model_seconds=sum(sum(job['timings'].values()) for job in jobs))
        for job in jobs:
            selected = [row for row in own if row['life'] == job['life']]
            lives.append(dict(life=job['life'], arm=arm, fees=job['fees'], total_samples=sum(job['fees'].values()),
                unit_accounting=job['unit_accounting'], shared_primitive_samples_by_operator=job['shared_primitive_samples_by_operator'],
                shared_declared_row_sets=job['shared_declared_row_sets'],
                cap=CAPS[job['life']], stages={stage: stage_aggregate([row for row in selected if row['stage'] == stage]) for stage in ('A', 'B', 'A_RETURN')}))
    continuous, controls = methods[ARMS[0]], [methods[arm] for arm in ARMS[1:]]
    errors = ('false_query_certificates', 'false_execution_certificates', 'false_impossible_certificates', 'false_goal_uppers',
              'risk_violations', 'executed_risk_violations', 'aux_false_query_certificates')
    conditions = dict(late_b_quality=continuous['late_b']['query_certified'] >= 27, a_return_quality=continuous['a_return']['query_certified'] >= 54,
        matched_late_b_quality=all(continuous['late_b']['query_certified'] >= control['late_b']['query_certified'] for control in controls),
        matched_a_return_quality=all(continuous['a_return']['query_certified'] >= control['a_return']['query_certified'] for control in controls),
        matched_joint_quality=all(continuous['joint_completed'] >= control['joint_completed'] for control in controls),
        actual_acquisition_saving=all(continuous['total_samples'] < control['total_samples'] for control in controls),
        per_life_budgets=all(row['total_samples'] <= row['cap'] for row in lives),
        valid_certificates_and_execution=all(method[field] == 0 for method in methods.values() for field in errors)
            and all(value == 0 for method in methods.values() for scope in ('auxiliary_execution_errors', 'history_execution_errors')
                    for value in method[scope].values())
            and all(method['all_goal_uppers_nonlooser_than_box'] for method in methods.values()))
    paired = []
    for control in ARMS[1:]:
        before = {(row['life'], row['index']): row for row in results if row['arm'] == control}
        for life in LIVES:
            own = [row for row in results if row['life'] == life and row['arm'] == ARMS[0]]
            paired.append(dict(life=life, control=control,
                control_minus_required_rows_samples=next(row['total_samples'] for row in lives if row['life'] == life and row['arm'] == control)-next(row['total_samples'] for row in lives if row['life'] == life and row['arm'] == ARMS[0]),
                query_gains=sum(row['query_certified'] and not before[life, row['index']]['query_certified'] for row in own),
                query_losses=sum(not row['query_certified'] and before[life, row['index']]['query_certified'] for row in own),
                joint_gains=sum(row['joint_completed'] and not before[life, row['index']]['joint_completed'] for row in own),
                joint_losses=sum(not row['joint_completed'] and before[life, row['index']]['joint_completed'] for row in own),
                execution_resolved_gains=sum((row['execution_certified'] or row['goal_impossible'])
                    and not (before[life, row['index']]['execution_certified'] or before[life, row['index']]['goal_impossible']) for row in own),
                execution_resolved_losses=sum(not (row['execution_certified'] or row['goal_impossible'])
                    and (before[life, row['index']]['execution_certified'] or before[life, row['index']]['goal_impossible']) for row in own),
                impossibility_gains=sum(row['goal_impossible'] and not before[life, row['index']]['goal_impossible'] for row in own),
                impossibility_losses=sum(not row['goal_impossible'] and before[life, row['index']]['goal_impossible'] for row in own)))
    return dict(complete=True, records=len(results), methods=methods, life_summaries=lives, paired=paired,
        conditions=conditions, stage_condition_met=all(conditions.values()),
        physical_source_samples=sum(job['fees']['source'] for job in artifacts),
        new_environment_observations=sum(sum(job['fees'].values()) for job in artifacts),
        model_seconds=sum(sum(job['timings'].values()) for job in artifacts),
        model_timings={scope: sum(job['timings'][scope] for job in artifacts) for scope in MODEL_SCOPES},
        acquisition_seconds=sum(job['acquisition_seconds'] for job in artifacts), acquisition_seconds_scope='subset_of_planning_process_CPU',
        model_seconds_scope='summed_process_CPU_all_initialization_pool_trajectory_query_plan_acquisition_and_execution_choice_once',
        observation_seconds=sum(job['observation_seconds'] for job in artifacts), output_seconds=sum(job['output_seconds'] for job in artifacts),
        auxiliary_records=sum(job['auxiliary_records'] for job in artifacts),
        execution_history_snapshots=len(execution_history),
        all_goal_uppers_nonlooser_than_box=all(method['all_goal_uppers_nonlooser_than_box'] for method in methods.values()),
        cache_statistics=[dict(life=job['life'], arm=job['arm'], profiles=job['profiles'], **job['cache_statistics']) for job in artifacts],
        work=[dict(life=job['life'], arm=job['arm'], **job['work']) for job in artifacts], actual_execution=True,
        realized_failures_are_certificate_errors=False, scientific_gate_changed=False, qualification_only=True, known_interface=True)


def run():
    begun, checks, failures = perf_counter(), Counter(), []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name))

    saved, summary_saved = load(OUTPUT/'run.json'), load(OUTPUT/'summary.json')
    protocol = dict(lives=list(LIVES), arms=list(ARMS), targets=list(TARGETS), total_caps=list(CAPS), source_budget=4608,
        source_A_budget=3456, source_B_budget=1152, source_seed_base=SOURCE_BASE, shared_seed_base=SHARED_BASE,
        member_seed_base=MEMBER_BASE, execution_seed_base=EXECUTION_BASE, mix_seed_base=MIX_BASE,
        shared_batch=SHARED_BATCH, member_batch=MEMBER_BATCH, member_cap=MEMBER_CAP, shared_before_indexes=[3, 30, 54],
        query_streams=216, query_threshold=4320, query_delta='1/20', execution_delta='1/20',
        confidence_scope='per_life_fixed_arm_query_plus_execution_1/10_not_whole_cohort', execution_pool_event=720,
        execution_member_event=8640, execution_utility_threshold=2, execution_risk_limit='1/20',
        execution_cs_method_by_arm=dict(REQUIRED_ROWS_REUSE='continuous_compatible_jeffreys_prefixes',
            CONTINUOUS_REUSE='continuous_compatible_jeffreys_prefixes', TRAJECTORY_REBUILD='separate_native_source_pool_member_regions'),
        continuous_active_pool_streams=12, continuous_reserved_pool_streams=18, member_streams=216,
        continuous_compatibility='canonical_A_stream_for_unchanged_rows_B_changed_native_stream_no_new_events',
        execution_reserve='2_per_remaining_unexecuted_target_including_current',
        direct_unit='same_actual_unit_with_predeclared_rows_covering_fixed_comparison_required_rows',
        direct_point='native_current_context_raw_joint_mean_of_ALL_predeclared_units_only',
        shared_unit_by_arm=dict(REQUIRED_ROWS_REUSE='batch_frozen_uncertified_query_required_rows_union_ALL_if_any_cost_execution_unresolved',
            CONTINUOUS_REUSE='ALL_S_D_conditional_R', TRAJECTORY_REBUILD='ALL_S_D_conditional_R'),
        unit_reservation='declared_row_count_before_any_unit_observation_conditional_R_only_if_declared_and_D_RECOVERY',
        batch_tail='native_only_S_when_remaining_below_declared_maximum_not_query_or_point_evidence',
        transfer='same_whole_declared_unit_only_when_all_fixed_comparison_required_rows_unchanged',
        member_rule='old_V231_choose_only_while_execution_unresolved_query_markers_remain_actual',
        shared_preview='full_execution_and_direct_query_plan_empty_member_upcoming_real_target_index',
        type_ready='all_four_public_costs_execution_certified_or_goal_impossible_AND_query_ready',
        goal_upper='V258_full_original_risk_constrained_D_joint_CS_dual_and_minimum_with_original_box',
        preview_execution_validity='posthoc_all_numeric_goal_upper_utility_lower_risk_upper_and_impossibility_claims',
        target_execution_validity='all_initial_member_and_terminal_numeric_claims_after_global_freeze',
        execution_feedback='native_row_pool_after_terminal_freeze_not_member_or_direct_rounds',
        truth_scoring='only_after_all_648_targets_auxiliary_checks_and_actual_executions_frozen',
        comparison_scope='required_rows_vs_continuous_reuse_isolates_shared_unit_declaration_rebuild_is_strong_reference',
        prerequisites=dict(v259_complete=True, v259_independent_valid=True, v259_stage_negative=True),
        scientific_gate_changed=False, known_interface=True, qualification_only=True, complete=True,
        phases=['protocol_and_public_roster_frozen', 'source_captured', 'all_648_targets_auxiliary_and_executions_frozen', 'posthoc_truth_scored', 'complete'])
    check('literal_frozen_full_lifecycle_direct_execution_source_budget_and_truth_barrier', saved == protocol)
    prerequisite = ROOT/'reports/continuous_row_cs_v259'
    check('settled_V259_independently_valid_negative_lifecycle',
        load(prerequisite/'run.json')['complete'] and load(prerequisite/'analysis.json')['valid']
        and not load(prerequisite/'summary.json')['stage_condition_met'])
    check('separate_original_direct_and_execution_event_budgets', F(216, 4320) == F(18, 720)+F(216, 8640) == F(1, 20))
    check('continuous_canonical_and_changed_row_events_within_original_reserved_alpha',
          F(12, 720)+F(216, 8640) == F(1, 24) <= F(1, 20))
    cases, interfaces = load(OUTPUT/'cases.json'), load(OUTPUT/'interfaces.json')
    for life in LIVES:
        public, _, identities, interface = paid.world(life)
        check('frozen_original72_public_world_cases_and_declared_known_interface',
              cases[life] == dict(life=life, cases=public) and interfaces[life] == dict(life=life, identities=identities,
                  metadata={key: interface[key] for key in ('changed_operator', 'b_to_a', 'stage_ranges')}))
    required = {'src/acfqp/science/required_row_units_v260.py', 'scripts/run_required_row_units_v260.py',
        'scripts/audit_required_row_units_v260.py', 'tests/test_required_row_units_v260_core.py',
        'tests/test_required_row_units_v260_runner.py', 'tests/test_required_row_units_v260_audit.py', 'specs/REQUIRED_ROW_UNITS_V260.md'}
    manifest = load(OUTPUT/'source_manifest.json')
    check('all_declared_new_sources_spec_and_tests_captured_before_sampling', required <= set(manifest))
    for relative in manifest:
        check('captured_source_exact_bytes_unchanged', (ROOT/relative).read_bytes() == (OUTPUT/'source_code'/relative).read_bytes())
    with ProcessPoolExecutor(max_workers=6) as executor:
        groups = list(executor.map(audit_life_arm, [(life, arm) for life in LIVES for arm in ARMS]))
    for group in groups:
        checks.update(group['checks'])
        failures.extend(group['failures'])
    for life in LIVES:
        paired_sources = [group['source_signature'] for group in groups if group['life'] == life]
        check('paired_potential_source_tapes_physically_drawn_and_fully_charged_per_arm',
              len(paired_sources) == 3 and all(signature == paired_sources[0] for signature in paired_sources[1:]))
    scored = [row for group in groups for row in group['scored']]
    auxiliary = [row for group in groups for row in group['auxiliary']]
    execution_history = [row for group in groups for row in group['execution_history']]
    artifacts = [group['artifact'] for group in groups]
    summary = summarize(scored, auxiliary, execution_history, artifacts)
    expected = dict(summary, elapsed_seconds=summary_saved['elapsed_seconds'], scoring_seconds=summary_saved['scoring_seconds'],
        worker_wall_seconds={f'{job["life"]}:{job["arm"]}': job['worker_wall_seconds'] for job in artifacts})
    check('all648_targets_all_actual_executions_and_auxiliary_incidents_retained', len(scored) == 648
          and len(auxiliary) == summary['auxiliary_records'] and summary['physical_source_samples'] == 41472)
    check('independent_complete_lifecycle_quality_realized_expected_cost_and_frozen_conditions_summary', exact(summary_saved) == exact(expected))
    check('actual_parent_scoring_elapsed_wall_and_model_cost_nonnegative', summary_saved['elapsed_seconds'] >= 0 and summary_saved['scoring_seconds'] >= 0)
    result = dict(valid=not failures, complete=True, records=len(scored), auxiliary_records=len(auxiliary), life_arm_jobs=len(groups),
        execution_history_snapshots=len(execution_history), all_goal_uppers_nonlooser_than_box=summary['all_goal_uppers_nonlooser_than_box'],
        independently_checked_profiles=sum(group['profiles'] for group in groups),
        independently_checked_direct_comparisons=checks['direct_exact_certification_status'],
        independently_checked_observation_units=sum(group['rounds'] for group in groups),
        independently_checked_complete_rounds=sum(job['unit_accounting']['source_complete_units']+job['unit_accounting']['shared_complete_units'] for job in artifacts),
        independently_checked_partial_units=sum(job['unit_accounting']['shared_partial_units'] for job in artifacts),
        independently_checked_execution_plans=sum(group['plans'] for group in groups)+len(auxiliary),
        independently_checked_execution_projections=sum(group['projections'] for group in groups),
        physical_source_samples=summary['physical_source_samples'], new_environment_observations=summary['new_environment_observations'],
        methods=summary['methods'], conditions=summary['conditions'], stage_condition_met=summary['stage_condition_met'],
        actual_execution=True, scientific_gate_changed=False, known_interface=True, checks=dict(checks), failures=failures,
        elapsed_seconds=perf_counter()-begun, life_arm_elapsed_seconds={f'{group["life"]}:{group["arm"]}': group['elapsed_seconds'] for group in groups})
    (OUTPUT/'analysis.json').write_text(json.dumps(result, default=str, indent=2)+'\n')
    print(json.dumps(result, default=str), flush=True)
    return result


if __name__ == '__main__':
    sys.exit(0 if run()['valid'] else 1)
