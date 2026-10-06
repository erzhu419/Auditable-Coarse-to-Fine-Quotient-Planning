"""Fixed-comparison evidence from predeclared executable observation units.

A unit's declared_rows is chosen from the previous observed history, before
its first fresh draw. Only a declaration covering a fixed ScoreSpec's entire
required_rows admits the unit to that comparison; the current outcomes never
decide admission. Declaring R requires D and samples R only after RECOVERY.
No retry sample is needed after another D outcome, but a D-only declaration
cannot opportunistically enter a retry comparison on such an outcome.

For every admitted unit the original bounded score has its fixed conditional
mean under the declared row laws. Its V233 bet depends only on past admitted
scores; skipped units leave that fixed e-process unchanged. Predictable unit
selection and original whole-required-row equality checks therefore preserve
the original all-prefix event4320 and 216-stream allocation. No events reset.
Source and ALL units alone update the original complete-joint empirical point
state. Partial units cannot update that state even when their observed D branch
happens not to need R. Every actual primitive separately updates native row CS.
"""
from copy import deepcopy
from fractions import Fraction as F

from . import continuous_row_cs_v259 as original
from .continuous_row_cs_v259 import (
    OPERATORS, ALPHABETS, empty, ready, begin_b, observe_row, freeze_sources,
    observe_tail, admitted_rounds, native, trajectory, row_views, upper_bound,
    regions,
)

ARMS = ('REQUIRED_ROWS_REUSE', 'CONTINUOUS_REUSE', 'TRAJECTORY_REBUILD')
S, D, R = OPERATORS


def prepare(life, arm, work):
    if arm not in ARMS:
        raise ValueError('the fixed comparison has required, complete and rebuild arms')
    state = original.prepare(life,
        'CONTINUOUS_REUSE' if arm == 'REQUIRED_ROWS_REUSE' else arm, work)
    state['acquisition_arm'] = arm
    return state


def observe_unit(state, record):
    declared = tuple(record['declared_rows'])
    if R in declared and D not in declared:
        raise ValueError('a retry declaration requires its detour path')
    if declared == OPERATORS:
        original.observe_round(state, record)
    else:
        state['round_log'].append(deepcopy(record))


def admitted_units(state, context, identity, spec):
    return [record for record in admitted_rounds(state, context, identity, spec)
        if set(spec.required_rows).issubset(record['declared_rows'])]


def unit_statistics(units, query, chosen, other, retry_cost, cache, work=None):
    direct = trajectory.direct
    spec = direct.score_spec(query, chosen, other, retry_cost)
    prefix = tuple(tuple(record['outcomes'].get(op) for op in spec.required_rows)
        for record in units)
    key = spec, prefix
    if key in cache:
        if work is not None:
            work['required_unit_score_cache_hits'] += 1
        return cache[key]
    scores = []
    for record in units:
        score = (direct._random_utility(other, query, spec.retry_cost, record['outcomes'])
            - direct._random_utility(chosen, query, spec.retry_cost, record['outcomes']))
        scores.append((score*direct.SCORE_SCALE).numerator)
    scores = tuple(scores)
    result = direct.StreamStatistics(spec, scores, direct.predictable_bets(spec, scores),
        sum(scores), sum(value*value for value in scores))
    cache[key] = result
    if work is not None:
        work['required_unit_unique_score_prefixes'] += 1
        work['required_unit_score_evaluations'] += len(scores)
    return result


def query_plan(state, case, identity, cache, work):
    if state['acquisition_arm'] != 'REQUIRED_ROWS_REUSE':
        return original.query_plan(state, case, identity, cache, work)
    context, direct = case['context'], trajectory.direct
    typestate = state['trajectory'][context][identity]
    pure = trajectory.pure_vectors(typestate, case)
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
        native_complete_rounds=len(typestate['rounds']))


def declared_rows_for_plans(plans):
    if any(F(plan['utility_lower']) < 2 and not plan['goal_impossible'] for plan in plans):
        return OPERATORS
    needed = set()
    for plan in plans:
        for query, decision in plan['query_evidence']['queries'].items():
            for comparison in decision.get('comparisons', ()):
                if not comparison['certified']:
                    needed.update(trajectory.direct.score_spec(query, decision['policy'],
                        comparison['other'], plan['case']['retry_cost']).required_rows)
    return tuple(op for op in OPERATORS if op in needed)


def make_plan(member, case, state, identity, index, cache, work):
    if state['acquisition_arm'] != 'REQUIRED_ROWS_REUSE':
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
