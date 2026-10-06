"""Native policy means from observation units declared before their outcomes.

SHORT requires S, RETURN requires D, and RETRY requires D/R. Every unit
whose declared mask covers that policy contributes one complete policy result,
including D/R units taking a non-RECOVERY branch. A D-only or S/D unit never
enters RETRY because its observed detour happened to avoid recovery.

Only native SOURCE/SHARED units update these point means. Different policies
can have different sample counts; observations are neither joined nor imputed.
The original complete-joint state remains alongside them. Fixed comparison
admission, predictable bets, row confidence processes and execution planning
are unchanged; only the first arm's empirical query candidate changes.
"""
from copy import deepcopy
from fractions import Fraction as F

from . import required_row_units_v260 as original
from .required_row_units_v260 import (
    OPERATORS, ALPHABETS, empty, ready, observe_row, freeze_sources,
    observe_tail, admitted_rounds, admitted_units, unit_statistics,
    native, trajectory, row_views, upper_bound, regions, declared_rows_for_plans,
)

ARMS = ('PARTIAL_POINT_REUSE', 'REQUIRED_ROWS_REUSE', 'CONTINUOUS_REUSE')
S, D, R = OPERATORS
POLICY_PATHS = {'SHORT': (S,), 'DETOUR_RETURN': (D,), 'DETOUR_RETRY': (D, R)}


def new_type_statistics():
    return {policy: dict(n=0, delivery=0, failure=0, recovery_calls=0,
        last_unit_id=None) for policy in POLICY_PATHS}


def prepare(life, arm, work):
    if arm not in ARMS:
        raise ValueError('the fixed comparison has partial-point, required and complete arms')
    state = original.prepare(life,
        'REQUIRED_ROWS_REUSE' if arm == ARMS[0] else arm, work)
    state['point_learning_arm'] = arm
    if arm == ARMS[0]:
        state['policy_path_stats'] = {'A': [new_type_statistics() for _ in range(3)], 'B': None}
    return state


def begin_b(state, changed_operator, b_to_a, work):
    original.begin_b(state, changed_operator, b_to_a, work)
    if state['point_learning_arm'] == ARMS[0]:
        state['policy_path_stats']['B'] = [new_type_statistics() for _ in range(3)]


def observe_unit(state, record):
    original.observe_unit(state, record)
    if state['point_learning_arm'] != ARMS[0] or record['phase'] not in ('SOURCE', 'SHARED'):
        return
    declared, outcomes = set(record['declared_rows']), record['outcomes']
    statistics = state['policy_path_stats'][record['context']][record['identity']]
    for policy, path in POLICY_PATHS.items():
        if not set(path).issubset(declared):
            continue
        if policy == 'SHORT':
            delivery, failure, recovery_calls = outcomes[S] == 'DELIVERY', outcomes[S] == 'LOST', False
        elif policy == 'DETOUR_RETURN':
            delivery, failure, recovery_calls = outcomes[D] == 'DELIVERY', outcomes[D] == 'LOST', False
        else:
            recovery_calls = outcomes[D] == 'RECOVERY'
            delivery = outcomes[D] == 'DELIVERY' or recovery_calls and outcomes[R] == 'DELIVERY'
            failure = outcomes[D] == 'LOST' or recovery_calls and outcomes[R] == 'LOST'
        row = statistics[policy]
        row['n'] += 1
        row['delivery'] += int(delivery)
        row['failure'] += int(failure)
        row['recovery_calls'] += int(recovery_calls)
        row['last_unit_id'] = record['round_id']


def path_vectors(statistics, case):
    short_cost, detour_cost = trajectory.direct.COST_PRIOR[case['operating']]
    result = {policy: [F(0)]*3 for policy in trajectory.direct.POLICIES}
    for policy, row in statistics.items():
        if row['n']:
            cost = short_cost if policy == 'SHORT' else detour_cost
            result[policy] = [-cost-F(case['retry_cost'])*F(row['recovery_calls'], row['n']),
                F(row['failure'], row['n']), F(row['delivery'], row['n'])]
    return result


def query_plan(state, case, identity, cache, work):
    if state['point_learning_arm'] != ARMS[0]:
        return original.query_plan(state, case, identity, cache, work)
    context, direct = case['context'], trajectory.direct
    typestate = state['trajectory'][context][identity]
    point_statistics = state['policy_path_stats'][context][identity]
    pure = path_vectors(point_statistics, case)
    queries = trajectory.point_queries(pure)
    decisions = {'reward': dict(policy='WAIT', certified=True, kind='known_nonnegative_cost')}
    for query in direct.QUERIES:
        chosen, comparisons = queries[query]['policy'], []
        for other in direct.POLICIES:
            if other == chosen:
                continue
            spec = direct.score_spec(query, chosen, other, case['retry_cost'])
            units = admitted_units(state, context, identity, spec)
            statistics = unit_statistics(units, query, chosen, other, case['retry_cost'], cache, work)
            comparisons.append(dict(direct.statistics_record(statistics), **direct.evaluate(statistics, case),
                score_source='actual_declared_required_row_units',
                admitted_unit_ids=[record['round_id'] for record in units],
                admitted_by_context={ctx: sum(record['context'] == ctx for record in units) for ctx in ('A', 'B')},
                cross_context=any(record['context'] != context for record in units)))
            work['trajectory_certificate_evaluations'] += 1
        decisions[query] = dict(policy=chosen,
            certified=all(record['certified'] for record in comparisons), comparisons=comparisons)
    evidence = dict(queries=decisions,
        all_ready=all(record['certified'] for record in decisions.values()), threshold=4320)
    blockers = {query: [record['other'] for record in decision.get('comparisons', ()) if not record['certified']]
        for query, decision in decisions.items()}
    certificates = {query: dict(policy=decision['policy'], certified=decision['certified'],
        regret_upper=F(0) if query == 'reward' else F(1, 20) if decision['certified'] else F(20))
        for query, decision in decisions.items()}
    own = [record for record in state['round_log'] if record['context'] == context and record['identity'] == identity]
    return dict(case=deepcopy(case), queries=queries, query_pure_vectors=pure, query_ready=evidence['all_ready'],
        query_certificates=certificates, query_blockers=blockers,
        query_gap_bounds={query: {policy: F(policy in blockers[query]) for policy in direct.POLICIES} for query in decisions},
        query_gap_bounds_kind='uncertified_comparison_marker_not_regret_bound', query_evidence=evidence,
        native_round_ids=[record['round_id'] for record in own if tuple(record['declared_rows']) == OPERATORS],
        native_unit_ids=[record['round_id'] for record in own],
        native_joint_outcome_counts=deepcopy(typestate['joint_outcome_counts']),
        native_complete_rounds=len(typestate['rounds']),
        query_point_method='native_predeclared_policy_path_means',
        query_point_statistics=deepcopy(point_statistics))


def make_plan(member, case, state, identity, index, cache, work):
    if state['point_learning_arm'] != ARMS[0]:
        return original.make_plan(member, case, state, identity, index, cache, work)
    constraints = regions(member, case, state, identity, index)
    observed = row_views.point_counts(case, state, identity)
    envelope, projections = native.projected_box(constraints, observed, work)
    posterior = native.mechanics.posterior(observed)
    pure = native.mechanics.vectors(case, posterior)
    risks = native.mechanics.robust.risk_bounds(envelope, work)
    goals = native.mechanics.robust.goals_lower(envelope, case, work)
    plan = dict(**native.mechanics.robust.solve(pure, risks, goals, work),
        posterior=posterior, pure_vectors=pure, risks=risks, goals_lower=goals,
        envelopes=envelope, evidence_counts=deepcopy(observed),
        effective_n={op: sum(counts.values()) for op, counts in observed.items()},
        joint_constraints=constraints, projection_supports=projections,
        goal_upper=native.query_math.goal_upper(case, envelope, work))
    plan['goal_impossible'] = plan['goal_upper'] < 2
    plan.update(query_plan(state, case, identity, cache, work))
    work['trajectory_lifecycle_plans'] += 1
    proof = upper_bound(plan, case, work)
    plan.update(box_goal_upper=proof['box_goal_upper'], goal_feasibility=proof,
        goal_upper=proof['upper'], goal_impossible=proof['new_impossible'],
        row_confidence_kind='continuous_compatible_jeffreys_prefixes')
    return plan
