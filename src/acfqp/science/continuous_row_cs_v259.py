"""Continue declared equal A/B rows through one Jeffreys confidence process.

For a fixed native A type/row, let p be its categorical law. Before B the
process receives that native A row; after the exogenous equality declaration,
it also receives the mapped native B row exactly when that row is unchanged.
Each admitted next outcome has conditional law p given the available history.
In particular, choosing a retry observation after seeing RECOVERY does not
expose its fresh independent retry outcome. Acquisition and execution feedback
may select which row to observe predictably without changing this property.

The mixture likelihood ratio Z(counts)/prod(p[c]**counts[c]) is consequently a
nonnegative supermartingale at its observed times (a martingale when every
category has positive probability), and is constant between them.
Ville's inequality covers every retained prefix with the SAME canonical event
and threshold 720. At return, A continues after B; A-only return counts are not
a prefix of this process. Historical A source/switch and switch+B source are
prefixes, while the current prefix sums the two physically separate native
banks once. Changed B rows retain their own original processes, and current
member processes retain threshold 8640. There are 9 A and 3 active changed-B
pool events: 12/720 + 216/8640 = 1/24 <= .05. Query processes are unchanged.
"""
from copy import deepcopy

from . import goal_feasibility_v258 as original
from .goal_feasibility_v258 import (
    OPERATORS, ALPHABETS, empty, ready, begin_b, observe_row, freeze_sources,
    observe_round, observe_tail, admitted_rounds, query_plan, native, trajectory,
    row_views, upper_bound,
)

ARMS = ('CONTINUOUS_REUSE', 'TRAJECTORY_REUSE', 'TRAJECTORY_REBUILD')


def prepare(life, arm, work):
    if arm not in ARMS:
        raise ValueError('the fixed comparison has continuous, separate and rebuild arms')
    state = original.prepare(life,
        'TRAJECTORY_REUSE' if arm == 'CONTINUOUS_REUSE' else arm, work)
    state['research_arm'] = arm
    return state


def _prefix(operator, event, kind, components):
    native_counts = {context: dict(identity=identity, counts=deepcopy(counts))
        for context, (identity, counts) in components.items()}
    counts = {category: sum(part['counts'][category] for part in native_counts.values())
        for category in ALPHABETS[operator]}
    return dict(native.joint.region(counts, 720), event=event,
        prefix_kind=kind, native_context_counts=native_counts)


def regions(member, case, state, identity, index):
    # Preserve the original genuine return_merge ledger and unchanged rows.
    constraints = row_views.regions(member, case, state, identity, index)
    if state['research_arm'] != 'CONTINUOUS_REUSE' or state['b'] is None:
        return constraints
    a_identity = state['b_to_a'][identity] if case['context'] == 'B' else identity
    b_identity = identity if case['context'] == 'B' else state['b_to_a'].index(identity)
    for op in OPERATORS:
        if op == state['changed_operator']:
            continue
        event = f'l{state["life"]}/A/pool{a_identity}/{op}'
        a_source = state['a']['sources'][a_identity][op]
        a_switch = state['a_at_switch']['pools'][a_identity][op]
        b_source = state['b']['sources'][b_identity][op]
        constraints[op] = [
            _prefix(op, event, 'a_source', {'A': (a_identity, a_source)}),
            _prefix(op, event, 'a_switch', {'A': (a_identity, a_switch)}),
            _prefix(op, event, 'a_switch_plus_b_source', {
                'A': (a_identity, a_switch), 'B': (b_identity, b_source)}),
            _prefix(op, event, 'continuous_current', {
                'A': (a_identity, state['a']['pools'][a_identity][op]),
                'B': (b_identity, state['b']['pools'][b_identity][op])}),
            dict(native.joint.region(member[op], 8640),
                event=f'l{state["life"]}/member{index}/{op}',
                prefix_kind='member', native_context_counts={}),
        ]
    return constraints


def make_plan(member, case, state, identity, index, cache, work):
    if state['research_arm'] != 'CONTINUOUS_REUSE':
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
