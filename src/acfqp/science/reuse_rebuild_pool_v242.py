"""Matched known-type planning with B inheritance as the sole arm difference.

Both arms accumulate their own B observations and restore their own A bank
on A_RETURN. REUSE additionally inherits unchanged A rows at the B switch.
Execution keeps V231's row confidence events; query evidence uses the new
online joint engine. Their separate per-life/arm budgets are each delta .05.

The legacy acquisition field ``query_gap_bounds`` contains 0/1 blocker marks,
not regret bounds. Its old consumer uses them only to select comparisons for
the unchanged observed-uncertainty spans. Actual query certification uses
the online engine's boolean decisions and full evidence.
"""
from copy import deepcopy
from fractions import Fraction as F

from . import oracle_gap_pool_v231 as original
from . import online_joint_query_v242 as query_evidence

OPERATORS, ALPHABETS = original.OPERATORS, original.ALPHABETS
BATCH, CAP = original.BATCH, original.CAP
empty, bank = original.empty, original.bank
begin_b, observe = original.begin_b, original.observe


def prepare(anchors, life, arm, work):
    if arm not in ('REUSE', 'REBUILD'):
        raise ValueError('the fixed comparison has REUSE and REBUILD arms')
    state = original.prepare(anchors, life, work)
    state['arm'] = arm
    return state


def point_counts(case, state, identity):
    if case['context'] == 'B' and state['arm'] == 'REBUILD':
        return deepcopy(bank(state, case)['pools'][identity])
    return original.point_counts(case, state, identity)


def regions(member, case, state, identity, index):
    constraints = original.regions(member, case, state, identity, index)
    if case['context'] == 'B' and state['arm'] == 'REBUILD':
        # The first three are this arm's B source, B pool and current member.
        # Both inherited A snapshots are absent from the REBUILD comparison.
        return {operator: row[:3] for operator, row in constraints.items()}
    return constraints


def make_plan(member, case, state, identity, index, query_cache, work):
    constraints = regions(member, case, state, identity, index)
    observed = point_counts(case, state, identity)
    return plan_from_evidence(constraints, observed, case, query_cache, work)


def plan_from_evidence(constraints, observed, case, query_cache, work):
    """Plan from supplied row counts/regions using the unchanged V242 engines."""
    envelope, projections = original.projected_box(constraints, observed, work)
    posterior = original.mechanics.posterior(observed)
    pure = original.mechanics.vectors(case, posterior)
    risks = original.mechanics.robust.risk_bounds(envelope, work)
    goals = original.mechanics.robust.goals_lower(envelope, case, work)
    plan = dict(**original.mechanics.robust.solve(pure, risks, goals, work),
        posterior=posterior, pure_vectors=pure, risks=risks, goals_lower=goals,
        envelopes=envelope, case=deepcopy(case), evidence_counts=deepcopy(observed),
        effective_n={operator: sum(row.values()) for operator, row in observed.items()})
    chosen = original.mechanics.queries(plan)
    certificate = query_evidence.certificates(observed, case, chosen, query_cache, work)
    blockers, markers, summaries = {}, {}, {}
    for query, decision in certificate['queries'].items():
        blockers[query] = [comparison['other'] for comparison in decision.get('comparisons', ())
                           if not comparison['certified']]
        markers[query] = {policy: F(policy in blockers[query]) for policy in original.joint.POLICIES}
        # 20 bounds every pure-policy utility gap for the fixed costs/weights.
        # These conservative bounds serve acquisition logs, never new proof.
        summaries[query] = dict(policy=decision['policy'], certified=decision['certified'],
            regret_upper=F(0) if query == 'reward' else F(1, 20) if decision['certified'] else F(20))
    plan.update(queries=chosen, query_certificates=summaries,
        query_ready=certificate['all_ready'], query_blockers=blockers,
        query_gap_bounds=markers, query_gap_bounds_kind='uncertified_comparison_marker_not_regret_bound',
        query_evidence=certificate, joint_constraints=constraints,
        projection_supports=projections,
        goal_upper=original.query_math.goal_upper(case, envelope, work))
    plan['goal_impossible'] = plan['goal_upper'] < 2
    work['reuse_rebuild_joint_plans'] += 1
    return plan


def ready(plan):
    return original.ready(plan)
