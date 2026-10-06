"""Native executable trajectories and fixed comparison-specific legal reuse."""
from copy import deepcopy
from fractions import Fraction as F

from . import executable_trajectory_v254 as trajectory
from . import bidirectional_pool_v243 as row_views
from . import oracle_gap_pool_v231 as native

ARMS = ('TRAJECTORY_REUSE', 'TRAJECTORY_REBUILD')
OPERATORS, ALPHABETS = native.OPERATORS, native.ALPHABETS
empty, ready = native.empty, native.ready


def prepare(life, arm, work):
    state = row_views.prepare([empty() for _ in range(3)], life,
        'TWO_WAY' if arm == 'TRAJECTORY_REUSE' else 'REBUILD', work)
    state.update(trajectory_arm=arm, trajectory={'A':[trajectory.new_type_state() for _ in range(3)],'B':None}, round_log=[])
    return state


def begin_b(state, changed_operator, b_to_a, work):
    row_views.begin_b(state, [empty() for _ in range(3)], changed_operator, b_to_a, work)
    state['trajectory']['B'] = [trajectory.new_type_state() for _ in range(3)]


def observe_row(state, context, identity, operator, increments):
    row_views.observe(state, {'context':context}, identity, operator, increments)


def freeze_sources(state, context):
    bank = state['a' if context=='A' else 'b']
    bank['sources'] = deepcopy(bank['pools'])


def observe_round(state, record):
    trajectory.observe_round(state['trajectory'][record['context']][record['identity']], record['outcomes'], record['round_id'])
    state['round_log'].append(deepcopy(record))


def observe_tail(state, context, identity, outcome):
    trajectory.observe_tail_s(state['trajectory'][context][identity], outcome)


def admitted_rounds(state, context, identity, spec):
    compatible = state['trajectory_arm']=='TRAJECTORY_REUSE' and state['b'] is not None and state['changed_operator'] not in spec.required_rows
    other_context = 'B' if context=='A' else 'A'
    other_identity = (state['b_to_a'].index(identity) if context=='A' else state['b_to_a'][identity]) if compatible else None
    return [record for record in state['round_log'] if
        record['context']==context and record['identity']==identity or
        compatible and record['context']==other_context and record['identity']==other_identity]


def query_plan(state, case, identity, cache, work):
    context, direct = case['context'], trajectory.direct
    typestate = state['trajectory'][context][identity]
    pure = trajectory.pure_vectors(typestate, case)
    queries = trajectory.point_queries(pure)
    decisions = {'reward':dict(policy='WAIT',certified=True,kind='known_nonnegative_cost')}
    for query in direct.QUERIES:
        chosen, comparisons = queries[query]['policy'], []
        for other in direct.POLICIES:
            if other==chosen:
                continue
            spec = direct.score_spec(query,chosen,other,case['retry_cost'])
            admitted = admitted_rounds(state,context,identity,spec)
            statistics = trajectory.actual_statistics([record['outcomes'] for record in admitted],
                query,chosen,other,case['retry_cost'],cache,work)
            comparisons.append(dict(direct.statistics_record(statistics),**direct.evaluate(statistics,case),
                score_source='actual_complete_conditional_rounds',admitted_round_ids=[record['round_id'] for record in admitted],
                admitted_by_context={ctx:sum(record['context']==ctx for record in admitted) for ctx in ('A','B')},
                cross_context=any(record['context']!=context for record in admitted)))
            work['trajectory_certificate_evaluations'] += 1
        decisions[query] = dict(policy=chosen,certified=all(record['certified'] for record in comparisons),comparisons=comparisons)
    evidence = dict(queries=decisions,all_ready=all(record['certified'] for record in decisions.values()),threshold=4320)
    blockers = {query:[record['other'] for record in decision.get('comparisons',()) if not record['certified']]
        for query,decision in decisions.items()}
    certificates = {query:dict(policy=decision['policy'],certified=decision['certified'],
        regret_upper=F(0) if query=='reward' else F(1,20) if decision['certified'] else F(20))
        for query,decision in decisions.items()}
    return dict(case=deepcopy(case),queries=queries,query_pure_vectors=pure,query_ready=evidence['all_ready'],
        query_certificates=certificates,query_blockers=blockers,
        query_gap_bounds={query:{policy:F(policy in blockers[query]) for policy in direct.POLICIES} for query in decisions},
        query_gap_bounds_kind='uncertified_comparison_marker_not_regret_bound',query_evidence=evidence,
        native_round_ids=[record['round_id'] for record in state['round_log'] if record['context']==context and record['identity']==identity],
        native_joint_outcome_counts=deepcopy(typestate['joint_outcome_counts']),native_complete_rounds=len(typestate['rounds']))


def make_plan(member, case, state, identity, index, cache, work):
    constraints = row_views.regions(member,case,state,identity,index)
    observed = row_views.point_counts(case,state,identity)
    envelope,projections = native.projected_box(constraints,observed,work)
    posterior = native.mechanics.posterior(observed)
    pure = native.mechanics.vectors(case,posterior)
    risks = native.mechanics.robust.risk_bounds(envelope,work)
    goals = native.mechanics.robust.goals_lower(envelope,case,work)
    plan = dict(**native.mechanics.robust.solve(pure,risks,goals,work),posterior=posterior,
        pure_vectors=pure,risks=risks,goals_lower=goals,envelopes=envelope,evidence_counts=deepcopy(observed),
        effective_n={operator:sum(counts.values()) for operator,counts in observed.items()},
        joint_constraints=constraints,projection_supports=projections,
        goal_upper=native.query_math.goal_upper(case,envelope,work))
    plan['goal_impossible'] = plan['goal_upper']<2
    plan.update(query_plan(state,case,identity,cache,work))
    work['trajectory_lifecycle_plans'] += 1
    return plan
