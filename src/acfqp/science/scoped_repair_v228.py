"""Scoped repair and matched cumulative rebuilding under public A/B contexts."""
from copy import deepcopy
from fractions import Fraction as F
from itertools import permutations

from . import scoped_union_v228 as confidence
from . import scoped_queries_v228 as query_bounds
from . import latent_mechanisms_v213 as mechanics

ARMS = ('REPAIR_CS', 'REBUILD_CS', 'PARAM')
OPERATORS, ALPHABETS = confidence.OPERATORS, confidence.ALPHABETS
empty = confidence.empty
BATCH, TARGET_CAP = 16, 384


def prepare(anchors, arm, work):
    return dict(arm=arm, a=confidence.initial_state(anchors, work),
                a_anchors=deepcopy(anchors), b=None, b_points=None)


def begin_b(state, anchors, work):
    """New B source indices are public; their correspondence with A is not."""
    state['a_at_switch'] = deepcopy(state['a']['bounds'])
    state['b_points'] = deepcopy(anchors)
    if state['arm'] == 'REBUILD_CS':
        state['b'] = {'rebuild': confidence.initial_state(anchors, work)}
    else:
        state['b'] = {}
        for op in OPERATORS:
            for permutation in permutations(range(3)):
                name = op+':'+''.join(str(i) for i in permutation)
                state['b'][name] = confidence.calibrated_branch(
                    state['a_at_switch'], op, permutation, anchors, work)


def _plus(base, member):
    return {op: {cat: base[op][cat]+member[op][cat] for cat in ALPHABETS[op]}
            for op in OPERATORS}


def make_plan(member, case, state, work):
    blocks, labels, means = {}, {}, {}
    if case['context'] == 'A':
        banks, points = {'A': state['a']}, state['a_anchors']
    else:
        banks, points = state['b'], state['b_points']
    for name, bank in banks.items():
        for index, block in confidence.candidates(bank, member, work).items():
            key = name+'/'+str(index)
            blocks[key] = block
            labels[key] = dict(branch=name, index=index)
            means[index] = mechanics.posterior(_plus(points[index], member))
    raw = confidence.union._project_simplex(confidence.boxes(member, work))
    if blocks:
        p = {op: {cat: sum(mean[op][cat] for mean in means.values())/len(means)
                  for cat in ALPHABETS[op]} for op in OPERATORS}
        envelope = deepcopy(raw)
        for op in OPERATORS:
            for cat in ALPHABETS[op]:
                envelope[op]['bounds'][cat] = [
                    min(block[op]['bounds'][cat][0] for block in blocks.values()),
                    max(block[op]['bounds'][cat][1] for block in blocks.values())]
        mode, models = 'library', list(blocks.values())
    else:
        p, envelope, mode, models = mechanics.posterior(member), raw, 'member', [raw]
    risks, goals = {}, {}
    for block in models:
        r = mechanics.robust.risk_bounds(block, work)
        g = mechanics.robust.goals_lower(block, case, work)
        for policy in r:
            risks[policy] = max(risks.get(policy, F(0)), r[policy])
            goals[policy] = min(goals.get(policy, g[policy]), g[policy])
    pure = mechanics.vectors(case, p)
    work['scoped_planning_calls'] += 1
    plan = dict(**mechanics.robust.solve(pure, risks, goals, work),
        envelopes=envelope, risks=risks, goals_lower=goals, pure_vectors=pure,
        candidates=list(blocks), candidate_envelopes=blocks,
        candidate_labels=labels, mode=mode, posterior=p)
    chosen = mechanics.queries(plan)
    certificates = [query_bounds.certificates(case, block, chosen, work) for block in models]
    query_certificates = {}
    for query in query_bounds.WEIGHTS:
        upper = max(result['queries'][query]['regret_upper'] for result in certificates)
        query_certificates[query] = dict(policy=chosen[query]['policy'], regret_upper=upper,
                                       certified=upper <= query_bounds.THRESHOLD)
    plan.update(queries=chosen, query_certificates=query_certificates,
                query_ready=all(row['certified'] for row in query_certificates.values()),
                goal_upper=max(query_bounds.goal_upper(case, block, work) for block in models))
    plan['goal_impossible'] = plan['goal_upper'] < 2
    return plan


def finish(plan):
    """Goal eligibility and query eligibility are separate contracts."""
    return dict(execution_plan=plan, knowledge_plan=plan, queries=plan['queries'],
                execution_certified=plan['utility_lower'] >= 2,
                goal_impossible=plan['goal_impossible'],
                query_certified=plan['query_ready'], fallback=plan['mode'] == 'member')


def _deficit(plan):
    return ((F(0) if plan['goal_impossible'] else max(F(0), F(2)-plan['utility_lower']))
            + max(row['regret_upper'] for row in plan['query_certificates'].values()))


def choose(member, case, state, plan, spent, work):
    """Forecast one batch per operator under the same rule in all three arms."""
    if spent >= TARGET_CAP or (plan['utility_lower'] >= 2 or plan['goal_impossible']) and plan['query_ready']:
        return None
    scores = {}
    for op in OPERATORS:
        expected = {cat: BATCH*plan['posterior'][op][cat] for cat in ALPHABETS[op]}
        increments = {cat: int(value) for cat, value in expected.items()}
        order = sorted(ALPHABETS[op], key=lambda cat: (
            -(expected[cat]-increments[cat]), ALPHABETS[op].index(cat)))
        for cat in order[:BATCH-sum(increments.values())]:
            increments[cat] += 1
        hypothetical = deepcopy(member)
        for cat, count in increments.items():
            hypothetical[op][cat] += count
        predicted = make_plan(hypothetical, case, state, work)
        scores[op] = _deficit(plan)-_deficit(predicted)
        work['scoped_acquisition_forecasts'] += 1
    operator = min(OPERATORS, key=lambda op: (
        -scores[op], sum(member[op].values()), OPERATORS.index(op)))
    return dict(operator=operator, reason='execution_and_query_deficit', scores=scores)


def _parameter_compatibility(bank, member, work):
    """Use all ended members for compatibility, without pooled-count intervals."""
    bank['members'].append(deepcopy(member))
    raw = [confidence.union._project_simplex(confidence.boxes(row, work))
           for row in bank['members']]
    masks = [[i for i, prior in enumerate(bank['priors'])
              if confidence.union._intersection(prior, [box]) is not None] for box in raw]
    feasible = not bank['no_feasible'] and all(masks)
    bank.update(masks=masks, bounds=deepcopy(bank['priors']) if feasible else [],
                no_feasible=not feasible)
    work['scoped_parameter_compatibility_targets'] += 1


def advance(state, member, case, plan, work):
    """The caller freezes the terminal decision before submitting any evidence."""
    if case['context'] == 'A':
        confidence.advance(state['a'], member, work)
        return dict(context='A', retained_samples=sum(sum(row.values()) for row in member.values()))
    point_commit = None
    indices = {label['index'] for label in plan['candidate_labels'].values()}
    if plan['mode'] == 'library' and len(indices) == 1:
        index = next(iter(indices))
        state['b_points'][index] = _plus(state['b_points'][index], member)
        point_commit = dict(index=index, samples=sum(sum(row.values()) for row in member.values()))
        work['scoped_point_committed_targets'] += 1
        work['scoped_point_committed_samples'] += point_commit['samples']
    for bank in state['b'].values():
        if state['arm'] == 'PARAM':
            _parameter_compatibility(bank, member, work)
        else:
            confidence.advance(bank, member, work)
    return dict(context='B', point_commit=point_commit,
                feasible_branches=sum(not bank['no_feasible'] for bank in state['b'].values()))
