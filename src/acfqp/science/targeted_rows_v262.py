"""V262 native row acquisition with one joint row-confidence query proof.

The three arms share the same row confidence events and query certificate.  The
primary comparison changes only how an unresolved target is sampled:

* ``DIRECT_ROW_REUSE`` pays one operator row at a time (D/R for query-only
  uncertainty, S/D/R when execution is also unresolved).
* ``FULL_UNIT_ROW_CS`` keeps the V261 predeclared-unit acquisition.
* ``CONTINUOUS_REUSE`` keeps complete S/D/R units as the strong reference.

Direct observations update the native row pool and a separate direct-row
ledger.  They never enter ``round_log`` or the executable trajectory state, so
an R row cannot be relabelled as a D/R unit.  Query point means are native
posterior row means for all arms.  Query certification is supplied by the
single joint row confidence intersection in :mod:`joint_gap_v230`.

For the risk query, the exact RETURN/RETRY branch difference on a recovery is
``d_REC * (8*r_DEL - 4 - retry_cost)``.  The certificate derives this factor
from the shared categorical kernel; no separate direct-score e-process is used.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from . import required_row_units_v260 as original
from .required_row_units_v260 import (
    OPERATORS, ALPHABETS, empty, ready, observe_row, freeze_sources,
    observe_tail, admitted_rounds, admitted_units, unit_statistics,
    native, trajectory, row_views, upper_bound, regions, declared_rows_for_plans,
)
from . import joint_gap_v230 as query_confidence

ARMS = ('DIRECT_ROW_REUSE', 'FULL_UNIT_ROW_CS', 'CONTINUOUS_REUSE')
S, D, R = OPERATORS
QUERY_ONLY_ROWS = (D, R)
EXECUTION_ROWS = OPERATORS


def _new_direct_counts():
    return {op: {category: 0 for category in ALPHABETS[op]} for op in OPERATORS}


def _new_context_direct_counts():
    return [_new_direct_counts() for _ in range(3)]


def prepare(life, arm, work):
    """Create a V262 state while preserving V260 native row/accounting state."""
    if arm not in ARMS:
        raise ValueError('the fixed comparison has direct rows, full units and continuous units')
    underlying = 'REQUIRED_ROWS_REUSE' if arm in ARMS[:2] else 'CONTINUOUS_REUSE'
    state = original.prepare(life, underlying, work)
    state.update(
        targeted_row_arm=arm,
        query_proof_method='unified_native_joint_row_cs_v262',
        direct_row_log=[],
        direct_row_counts={'A': _new_context_direct_counts(), 'B': None},
    )
    return state


def begin_b(state, changed_operator, b_to_a, work):
    original.begin_b(state, changed_operator, b_to_a, work)
    state['direct_row_counts']['B'] = _new_context_direct_counts()


def observe_unit(state, record):
    """Record a declared unit using the original trajectory/unit semantics."""
    original.observe_unit(state, record)


def observe_direct_row(state, context, identity, operator, increments):
    """Pay one native operator row without creating an executable unit.

    ``increments`` is a one-row categorical count.  The native pool is the
    only planning evidence; the explicit ledger makes the provenance visible
    to an independent audit and deliberately has no D/R-unit fields.
    """
    if state.get('targeted_row_arm') != ARMS[0]:
        raise ValueError('observe_direct_row is reserved for DIRECT_ROW_REUSE')
    if context not in ('A', 'B'):
        raise ValueError('direct rows require native context A or B')
    if operator not in OPERATORS:
        raise ValueError('unknown native operator')
    if state['b'] is None and context == 'B':
        raise ValueError('B direct rows require begin_b')
    total = sum(int(value) for value in increments.values())
    if total != 1 or any(category not in ALPHABETS[operator]
                          for category in increments):
        raise ValueError('a direct row must contain exactly one known category')
    original.observe_row(state, context, identity, operator, dict(increments))
    row_counts = state['direct_row_counts'][context][identity][operator]
    for category, value in increments.items():
        row_counts[category] += int(value)
    state['direct_row_log'].append(dict(
        direct_row_index=len(state['direct_row_log']), context=context,
        identity=identity, operator=operator, increments=deepcopy(dict(increments))))


def targeted_rows_for_unresolved(plan):
    """Return the frozen direct-row target for the current terminal plan."""
    execution_unresolved = not (plan['utility_lower'] >= 2 or plan['goal_impossible'])
    if execution_unresolved:
        return tuple(EXECUTION_ROWS)
    if not plan['query_ready']:
        return tuple(QUERY_ONLY_ROWS)
    return ()


def return_retry_risk_gap(d_recovery, r_delivery, retry_cost):
    """Exact risk-query RETURN/RETRY gap contribution."""
    return F(d_recovery) * (8 * F(r_delivery) - 4 - F(retry_cost))


def _query_comparisons(certificate, query, chosen):
    result = []
    for other in query_confidence.POLICIES:
        if other == chosen:
            continue
        records = [record for record in certificate['support_records']
                   if record['query'] == query and record['chosen'] == chosen
                   and record['other'] == other]
        upper = max((F(record['support']['upper']) for record in records), default=F(0))
        result.append(dict(query=query, chosen=chosen, other=other,
            certified=upper <= query_confidence.THRESHOLD, regret_upper=upper,
            score_source='native_joint_row_cs', required_rows=[D, R],
            support_records=deepcopy(records)))
    return result


def query_plan(state, case, identity, cache=None, work=None, constraints=None,
               member=None, index=0):
    """Build point choices and certify them with the shared row CS."""
    del cache  # The joint proof is an immutable row-count calculation.
    if work is None:
        work = Counter()
    if member is None:
        member = empty()
    context = case['context']
    observed = row_views.point_counts(case, state, identity)
    posterior = native.mechanics.posterior(observed)
    pure = native.mechanics.vectors(case, posterior)
    queries = trajectory.point_queries(pure)
    if constraints is None:
        constraints = regions(member, case, state, identity, index)
    certificate = query_confidence.certificates(case, constraints, queries, work)
    decisions = {}
    for query, choice in queries.items():
        chosen = choice['policy']
        if query == 'reward':
            decisions[query] = dict(policy=chosen, certified=True,
                kind='known_nonnegative_cost', comparisons=[])
            continue
        comparisons = _query_comparisons(certificate, query, chosen)
        decisions[query] = dict(policy=chosen,
            certified=all(row['certified'] for row in comparisons),
            regret_upper=max((row['regret_upper'] for row in comparisons), default=F(0)),
            comparisons=comparisons)
    evidence = dict(queries=decisions, all_ready=all(row['certified'] for row in decisions.values()),
        threshold=query_confidence.THRESHOLD, method='unified_native_joint_row_cs_v262',
        event_allocation=dict(pool_threshold=query_confidence.POOL_THRESHOLD,
            member_threshold=query_confidence.MEMBER_THRESHOLD,
            query_delta='1/20', shared_with_execution_cs=True),
        support_records=deepcopy(certificate['support_records']),
        binary_intervals=deepcopy(certificate.get('binary_intervals', {})))
    blockers = {query: [row['other'] for row in decision.get('comparisons', ())
                        if not row['certified']]
                for query, decision in decisions.items()}
    gap_bounds = {query: {policy: F(0) for policy in query_confidence.POLICIES}
                  for query in decisions}
    for query, decision in decisions.items():
        for row in decision.get('comparisons', ()):
            gap_bounds[query][row['other']] = row['regret_upper']
    own = [record for record in state['round_log']
           if record['context'] == context and record['identity'] == identity]
    typestate = state['trajectory'][context][identity]
    return dict(case=deepcopy(case), queries=queries, query_pure_vectors=pure,
        query_proof_method='unified_native_joint_row_cs_v262',
        query_ready=evidence['all_ready'], query_certificates={
            query: dict(policy=decision['policy'], certified=decision['certified'],
                        regret_upper=decision.get('regret_upper', F(0)))
            for query, decision in decisions.items()},
        query_blockers=blockers, query_gap_bounds=gap_bounds,
        query_gap_bounds_kind='native_joint_row_cs_regret_upper',
        query_evidence=evidence,
        native_round_ids=[record['round_id'] for record in own
                          if tuple(record['declared_rows']) == OPERATORS],
        native_unit_ids=[record['round_id'] for record in own],
        native_joint_outcome_counts=deepcopy(typestate['joint_outcome_counts']),
        native_complete_rounds=len(typestate['rounds']),
        native_row_counts=deepcopy(observed), native_row_posterior=deepcopy(posterior),
        query_point_method='native_row_posterior_means',
        query_point_statistics=deepcopy(observed),
        direct_rows_for_unresolved=(QUERY_ONLY_ROWS if not evidence['all_ready'] else ()))


def make_plan(member, case, state, identity, index, cache, work):
    """Plan execution with native posterior points and the unified query proof."""
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
    plan.update(query_plan(state, case, identity, cache, work, constraints, member, index))
    plan['direct_rows_for_unresolved'] = targeted_rows_for_unresolved(plan)
    work['trajectory_lifecycle_plans'] += 1
    proof = upper_bound(plan, case, work)
    plan.update(box_goal_upper=proof['box_goal_upper'], goal_feasibility=proof,
        goal_upper=proof['upper'], goal_impossible=proof['new_impossible'],
        row_confidence_kind='unified_native_joint_row_cs_v262')
    plan['direct_rows_for_unresolved'] = targeted_rows_for_unresolved(plan)
    return plan


__all__ = [name for name in globals() if not name.startswith('_')]
