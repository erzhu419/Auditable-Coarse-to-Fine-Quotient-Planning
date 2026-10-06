"""Known-type cumulative joint confidence for a paid allocation diagnostic.

The interface supplies type identities and the changed B row, not transition
probabilities. Each observed batch immediately enters its own context's pool.
A confidence/count snapshot is inherited only by unchanged B rows.
"""
from copy import deepcopy
from fractions import Fraction as F

from . import joint_gap_v230 as joint
from . import latent_mechanisms_v213 as mechanics
from . import scoped_queries_v228 as query_math
from . import assignment_union_v222 as geometry

OPERATORS, ALPHABETS = joint.OPERATORS, joint.ALPHABETS
BATCH, CAP = 16, 384
empty = mechanics.empty


def _bank(anchors):
    return dict(sources=deepcopy(anchors), pools=deepcopy(anchors))


def prepare(anchors, life, work):
    work['oracle_pool_initializations'] += 1
    return dict(life=life, a=_bank(anchors), b=None, a_at_switch=None)


def begin_b(state, anchors, changed_operator, b_to_a, work):
    state['a_at_switch'] = deepcopy(state['a'])
    state['b'] = _bank(anchors)
    state['changed_operator'] = changed_operator
    state['b_to_a'] = tuple(b_to_a)
    work['oracle_scope_initializations'] += 1


def bank(state, case):
    return state['a' if case['context'] == 'A' else 'b']


def observe(state, case, identity, operator, increments):
    """Only this actual batch is added; current member counts are separate."""
    row = bank(state, case)['pools'][identity][operator]
    for category, count in increments.items():
        row[category] += count


def regions(member, case, state, identity, index):
    current, result = bank(state, case), {}
    for op in OPERATORS:
        event = f'l{state["life"]}/{case["context"]}/pool{identity}/{op}'
        result[op] = [dict(joint.region(counts[identity][op], 720), event=event)
                      for counts in (current['sources'], current['pools'])]
        result[op].append(dict(joint.region(member[op], 8640),
                              event=f'l{state["life"]}/member{index}/{op}'))
        if case['context'] == 'B' and op != state['changed_operator']:
            a_index = state['b_to_a'][identity]
            a_event = f'l{state["life"]}/A/pool{a_index}/{op}'
            result[op].extend(dict(joint.region(counts[a_index][op], 720), event=a_event)
                for counts in (state['a_at_switch']['sources'], state['a_at_switch']['pools']))
    return result


def point_counts(case, state, identity):
    counts = deepcopy(bank(state, case)['pools'][identity])
    if case['context'] == 'B':
        inherited = state['a_at_switch']['pools'][state['b_to_a'][identity]]
        for op in OPERATORS:
            if op != state['changed_operator']:
                for cat in ALPHABETS[op]:
                    counts[op][cat] += inherited[op][cat]
    return counts


def projected_box(constraints, counts, work):
    box, supports = {}, {}
    for op in OPERATORS:
        if len(ALPHABETS[op]) == 2:
            lo, hi = joint.interval(constraints[op], 'DELIVERY', work)
            bounds = {'DELIVERY': [lo, hi], 'LOST': [1-hi, 1-lo]}
        else:
            bounds, supports[op] = {}, {}
            for cat in ALPHABETS[op]:
                coefficient = {other: F(other == cat) for other in ALPHABETS[op]}
                high = joint.support(constraints[op], coefficient, work)
                low = joint.support(constraints[op],
                                    {other: -v for other, v in coefficient.items()}, work)
                bounds[cat] = [max(F(0), -low['upper']), min(F(1), high['upper'])]
                supports[op][cat] = dict(lower=low, upper=high)
        box[op] = dict(bounds=bounds, counts=deepcopy(counts[op]), n=sum(counts[op].values()))
    if not geometry._feasible(box):
        raise ValueError('empty oracle joint confidence projection')
    return geometry._project_simplex(box), supports


def make_plan(member, case, state, identity, index, work):
    constraints = regions(member, case, state, identity, index)
    observed = point_counts(case, state, identity)
    envelope, projections = projected_box(constraints, observed, work)
    posterior = mechanics.posterior(observed)
    pure = mechanics.vectors(case, posterior)
    risks = mechanics.robust.risk_bounds(envelope, work)
    goals = mechanics.robust.goals_lower(envelope, case, work)
    plan = dict(**mechanics.robust.solve(pure, risks, goals, work),
                posterior=posterior, pure_vectors=pure, risks=risks,
                goals_lower=goals, envelopes=envelope, case=deepcopy(case),
                effective_n={op: sum(observed[op].values()) for op in OPERATORS})
    chosen = mechanics.queries(plan)
    certificate = joint.certificates(case, constraints, chosen, work)
    if certificate['empty']:
        raise ValueError('empty oracle query confidence projection')
    comparisons = {query: dict.fromkeys(joint.POLICIES, F(0)) for query in joint.WEIGHTS}
    for row in certificate['support_records']:
        comparisons[row['query']][row['other']] = max(
            comparisons[row['query']][row['other']], row['support']['upper'])
    plan.update(queries=chosen, query_certificates=deepcopy(certificate['queries']),
                query_ready=certificate['all_ready'], query_gap_bounds=comparisons,
                goal_upper=query_math.goal_upper(case, envelope, work),
                joint_constraints=constraints, query_certificate=certificate,
                projection_supports=projections)
    plan['goal_impossible'] = plan['goal_upper'] < 2
    work['oracle_joint_plans'] += 1
    return plan


def ready(plan):
    return (plan['utility_lower'] >= 2 or plan['goal_impossible']) and plan['query_ready']


def balanced(member, plan, spent):
    if spent >= CAP or ready(plan):
        return None
    op = min(OPERATORS, key=lambda row: (sum(member[row].values()), OPERATORS.index(row)))
    return dict(operator=op, reason='balanced_current_target')
