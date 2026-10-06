"""Independent scoped confidence, acquisition and query reconstruction for V229.

Only previously independent scalar confidence and route arithmetic are reused.
No scoped producer or V228 learner is imported.  State updates consume integer
retained observations; forecasts never update a confidence bank.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations, permutations, product

from scripts import analyze_mixture_confidence_v225 as prior

ARMS = ('REPAIR_CS', 'REBUILD_CS', 'PARAM')
OPERATORS, SUPPORT = prior.OPERATORS, prior.SUPPORT
ALPHABETS = SUPPORT
POLICIES = ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY')
WEIGHTS = {'reward': (1, 0, 0), 'goal': (1, 0, 4), 'risk': (1, 4, 4)}
MEMBER_THRESHOLD, POOL_THRESHOLD = 20160, 1680
BATCH, TARGET_CAP = 16, 384
THRESHOLD = F(1, 20)
empty = prior.empty
posterior = prior.independent.posterior
vectors = prior.settled.vectors
queries = prior.queries
score = prior.score
query_score = prior.query_score
exact_json = prior.settled.exact_json
same = prior.same
project_simplex = prior.union_math.project_simplex
feasible = prior.feasible


def _add(work, key, amount=1):
    if work is not None:
        work[key] = work.get(key, 0) + amount


def boxes(counts, work=None, threshold=MEMBER_THRESHOLD):
    _add(work, 'independent_scoped_boxes')
    return {
        op: dict(n=sum(counts[op].values()), counts=deepcopy(counts[op]),
                 bounds={cat: list(prior.mixture_interval(
                     counts[op][cat], sum(counts[op].values()), threshold))
                         for cat in SUPPORT[op]})
        for op in OPERATORS}


def intersect_all(first, others):
    """Intersect every marginal constraint before projecting its simplex."""
    result = deepcopy(first)
    for op in OPERATORS:
        for cat in SUPPORT[op]:
            endpoints = [first[op]['bounds'][cat]]
            endpoints.extend(other[op]['bounds'][cat] for other in others)
            result[op]['bounds'][cat] = [max(pair[0] for pair in endpoints),
                                        min(pair[1] for pair in endpoints)]
    return project_simplex(result) if feasible(result) else None


def _state(priors, anchors, changed_op):
    return dict(priors=deepcopy(priors), anchor_counts=deepcopy(anchors),
                changed_op=changed_op, members=[], bounds=deepcopy(priors),
                masks=[], no_feasible=False, iterations=0, max_dp_states=0)


def initial_state(anchors, work):
    _add(work, 'independent_scoped_initializations')
    return _state([project_simplex(boxes(anchor, work, POOL_THRESHOLD))
                   for anchor in anchors], anchors, None)


def calibrated_branch(a_bounds, changed_op, permutation, b_anchors, work):
    priors, failed = [], False
    for b_index, anchor in enumerate(b_anchors):
        block = boxes(anchor, work, POOL_THRESHOLD)
        inherited = a_bounds[permutation[b_index]]
        for op in OPERATORS:
            block[op]['kind'] = ('scoped_calibrated_changed' if op == changed_op
                                 else 'scoped_calibrated_inherited')
            if op != changed_op:
                for cat in SUPPORT[op]:
                    new, old = block[op]['bounds'][cat], inherited[op]['bounds'][cat]
                    block[op]['bounds'][cat] = [max(new[0], old[0]), min(new[1], old[1])]
        if feasible(block):
            block = project_simplex(block)
        else:
            failed = True
        priors.append(block)
    bank = _state(priors, b_anchors, changed_op)
    bank['permutation'] = tuple(permutation)
    if failed:
        bank.update(bounds=[], no_feasible=True)
    _add(work, 'independent_scoped_calibrated_initializations')
    return bank


def prepare(anchors, arm, work):
    return dict(arm=arm, a=initial_state(anchors, work),
                a_anchors=deepcopy(anchors), b=None, b_points=None)


def begin_b(state, anchors, work):
    state['a_at_switch'] = deepcopy(state['a']['bounds'])
    state['b_points'] = deepcopy(anchors)
    if state['arm'] == 'REBUILD_CS':
        state['b'] = {'rebuild': initial_state(anchors, work)}
    else:
        state['b'] = {}
        for changed_op in OPERATORS:
            for correspondence in permutations(range(3)):
                name = changed_op + ':' + ''.join(str(i) for i in correspondence)
                state['b'][name] = calibrated_branch(
                    state['a_at_switch'], changed_op, correspondence, anchors, work)


def candidates(bank, member, work):
    raw = project_simplex(boxes(member, work))
    result = {}
    for index, prior_box in enumerate(bank['bounds']):
        block = intersect_all(prior_box, [raw])
        if block is not None:
            result[index] = block
    return result


def _no_feasible(members, iterations, maximum):
    return dict(bounds=[], masks=[[] for _ in members], no_feasible=True,
                iterations=iterations, max_dp_states=maximum)


def _outer(bank, member_boxes, masks, work):
    """Coordinate outer envelope over every still-compatible assignment."""
    iterations, maximum = 0, 0
    members = bank['members']
    while True:
        iterations += 1
        _add(work, 'independent_scoped_outer_iterations')
        if any(not mask for mask in masks):
            return _no_feasible(members, iterations, maximum)
        bounds = []
        for index, prior_box in enumerate(bank['priors']):
            mandatory = [j for j, mask in enumerate(masks) if mask == [index]]
            optional = [j for j, mask in enumerate(masks)
                        if index in mask and len(mask) > 1]
            pooled = deepcopy(bank['anchor_counts'][index])
            for j in mandatory:
                for op in OPERATORS:
                    for cat in SUPPORT[op]:
                        pooled[op][cat] += members[j][op][cat]
            block = intersect_all(prior_box, [member_boxes[j] for j in mandatory])
            if block is None:
                return _no_feasible(members, iterations, maximum)
            for op in OPERATORS:
                base_n = sum(pooled[op].values())
                for cat in SUPPORT[op]:
                    additions = [(sum(members[j][op].values()), members[j][op][cat])
                                 for j in optional]
                    attainable = prior.union_math.subset_extrema(
                        base_n, pooled[op][cat], additions)
                    maximum = max(maximum, len(attainable))
                    lo = min(prior.mixture_interval(low, n, POOL_THRESHOLD)[0]
                             for n, (low, high) in attainable.items())
                    hi = max(prior.mixture_interval(high, n, POOL_THRESHOLD)[1]
                             for n, (low, high) in attainable.items())
                    old = block[op]['bounds'][cat]
                    block[op]['bounds'][cat] = [max(old[0], lo), min(old[1], hi)]
            if not feasible(block):
                return _no_feasible(members, iterations, maximum)
            bounds.append(project_simplex(block))
        reduced = [[i for i in mask
                    if intersect_all(bounds[i], [member_boxes[j]]) is not None]
                   for j, mask in enumerate(masks)]
        if reduced == masks:
            return dict(bounds=bounds, masks=masks, no_feasible=False,
                        iterations=iterations, max_dp_states=maximum)
        masks = reduced


def advance_bank(bank, member, work):
    bank['members'].append(deepcopy(member))
    raw = [project_simplex(boxes(row, work)) for row in bank['members']]
    masks = [[i for i, prior_box in enumerate(bank['priors'])
              if intersect_all(prior_box, [block]) is not None] for block in raw]
    result = _outer(bank, raw, masks, work)
    bank.update(result)
    _add(work, 'independent_scoped_retained_targets')
    return result


def parameter_compatibility(bank, member, work):
    bank['members'].append(deepcopy(member))
    raw = [project_simplex(boxes(row, work)) for row in bank['members']]
    masks = [[i for i, prior_box in enumerate(bank['priors'])
              if intersect_all(prior_box, [block]) is not None] for block in raw]
    admitted = not bank['no_feasible'] and all(masks)
    bank.update(masks=masks, bounds=deepcopy(bank['priors']) if admitted else [],
                no_feasible=not admitted)
    _add(work, 'independent_scoped_parameter_compatibility_targets')


def row_vertices(bounds):
    """All vertices obtained by fixing all but one categorical coordinate."""
    cats = tuple(bounds)
    ends = {cat: tuple(F(value) for value in bounds[cat]) for cat in cats}
    admitted = set()
    for fixed in combinations(cats, len(cats)-1):
        free = next(cat for cat in cats if cat not in fixed)
        for values in product(*(ends[cat] for cat in fixed)):
            coordinates = dict(zip(fixed, values))
            coordinates[free] = 1 - sum(values)
            if all(ends[cat][0] <= coordinates[cat] <= ends[cat][1] for cat in cats):
                admitted.add(tuple(coordinates[cat] for cat in cats))
    if not admitted:
        raise ValueError('empty categorical box/simplex intersection')
    return [dict(zip(cats, values)) for values in sorted(admitted)]


def box_vertices(block):
    return [dict(zip(OPERATORS, rows))
            for rows in product(*(row_vertices(block[op]['bounds']) for op in OPERATORS))]


def utility(vector, weights):
    return weights[0]*vector[0] - weights[1]*vector[1] + weights[2]*vector[2]


def certificates(case, envelope, point_queries, work=None, threshold=THRESHOLD):
    values = [vectors(case, kernel) for kernel in box_vertices(envelope)]
    result = {}
    for query, weights in WEIGHTS.items():
        chosen = point_queries[query]['policy']
        upper = max(F(0), *(utility(row[other], weights) - utility(row[chosen], weights)
                           for row in values for other in POLICIES))
        result[query] = dict(policy=chosen,
            utility_bounds={policy: [min(utility(row[policy], weights) for row in values),
                                      max(utility(row[policy], weights) for row in values)]
                            for policy in POLICIES},
            regret_upper=upper, certified=upper <= threshold)
    _add(work, 'independent_query_certificate_kernel_vertices', len(values))
    return dict(queries=result, all_ready=all(row['certified'] for row in result.values()),
                vertex_count=len(values))


def goal_upper(case, envelope, work=None):
    values = [vectors(case, kernel) for kernel in box_vertices(envelope)]
    minimum_risk = {policy: min(row[policy][1] for row in values) for policy in POLICIES}
    maximum_goal = {policy: max(utility(row[policy], WEIGHTS['goal']) for row in values)
                    for policy in POLICIES}
    optimistic = {policy: [maximum_goal[policy], F(0), F(0)] for policy in POLICIES}
    work_for_solve = Counter() if work is None else work
    _add(work, 'independent_goal_upper_kernel_vertices', len(values))
    return prior.settled.optimize(optimistic, minimum_risk, maximum_goal,
                                  work_for_solve)['predicted_utility']


def _plus(first, second):
    return {op: {cat: first[op][cat] + second[op][cat] for cat in SUPPORT[op]}
            for op in OPERATORS}


def make_plan(member, case, state, work):
    blocks, labels, means = {}, {}, {}
    banks = {'A': state['a']} if case['context'] == 'A' else state['b']
    points = state['a_anchors'] if case['context'] == 'A' else state['b_points']
    for branch_name, bank in banks.items():
        for index, block in candidates(bank, member, work).items():
            key = branch_name + '/' + str(index)
            blocks[key] = block
            labels[key] = dict(branch=branch_name, index=index)
            means[index] = posterior(_plus(points[index], member))
    raw = project_simplex(boxes(member, work))
    if blocks:
        p = {op: {cat: sum(mean[op][cat] for mean in means.values()) / len(means)
                  for cat in SUPPORT[op]} for op in OPERATORS}
        envelope = deepcopy(raw)
        for op in OPERATORS:
            for cat in SUPPORT[op]:
                envelope[op]['bounds'][cat] = [
                    min(block[op]['bounds'][cat][0] for block in blocks.values()),
                    max(block[op]['bounds'][cat][1] for block in blocks.values())]
        mode, models = 'library', list(blocks.values())
    else:
        p, envelope, mode, models = posterior(member), raw, 'member', [raw]
    risk_sets = [prior.settled.risk_bounds(block) for block in models]
    goal_sets = [prior.settled.goal_bounds(block, case) for block in models]
    risks = {policy: max(row[policy] for row in risk_sets) for policy in POLICIES}
    goals = {policy: min(row[policy] for row in goal_sets) for policy in POLICIES}
    pure = vectors(case, p)
    plan = dict(prior.settled.optimize(pure, risks, goals, work),
                envelopes=envelope, risks=risks, goals_lower=goals, pure_vectors=pure,
                candidates=list(blocks), candidate_envelopes=blocks,
                candidate_labels=labels, mode=mode, posterior=p)
    chosen = queries(plan)
    bounds = [certificates(case, block, chosen, work) for block in models]
    query_bounds = {}
    for query in WEIGHTS:
        upper = max(result['queries'][query]['regret_upper'] for result in bounds)
        query_bounds[query] = dict(policy=chosen[query]['policy'], regret_upper=upper,
                                   certified=upper <= THRESHOLD)
    plan.update(queries=chosen, query_certificates=query_bounds,
                query_ready=all(row['certified'] for row in query_bounds.values()),
                goal_upper=max(goal_upper(case, block, work) for block in models))
    plan['goal_impossible'] = plan['goal_upper'] < 2
    _add(work, 'independent_scoped_planning_calls')
    return plan


def finish(plan):
    return dict(execution_plan=plan, knowledge_plan=plan, queries=plan['queries'],
                execution_certified=plan['utility_lower'] >= 2,
                goal_impossible=plan['goal_impossible'], query_certified=plan['query_ready'],
                fallback=plan['mode'] == 'member')


def _deficit(plan):
    execution = F(0) if plan['goal_impossible'] else max(F(0), F(2)-plan['utility_lower'])
    return execution + max(row['regret_upper'] for row in plan['query_certificates'].values())


def choose(member, case, state, plan, spent, work):
    if spent >= TARGET_CAP or ((plan['utility_lower'] >= 2 or plan['goal_impossible'])
                               and plan['query_ready']):
        return None
    scores = {}
    for op in OPERATORS:
        expected = {cat: BATCH*plan['posterior'][op][cat] for cat in SUPPORT[op]}
        increments = {cat: int(value) for cat, value in expected.items()}
        order = sorted(SUPPORT[op], key=lambda cat: (
            -(expected[cat]-increments[cat]), SUPPORT[op].index(cat)))
        for cat in order[:BATCH-sum(increments.values())]:
            increments[cat] += 1
        forecast = deepcopy(member)
        for cat, count in increments.items():
            forecast[op][cat] += count
        predicted = make_plan(forecast, case, state, work)
        scores[op] = _deficit(plan) - _deficit(predicted)
        _add(work, 'independent_scoped_acquisition_forecasts')
    operator = min(OPERATORS, key=lambda op: (
        -scores[op], sum(member[op].values()), OPERATORS.index(op)))
    return dict(operator=operator, reason='execution_and_query_deficit', scores=scores)


def advance(state, member, case, plan, work):
    samples = sum(sum(row.values()) for row in member.values())
    if case['context'] == 'A':
        advance_bank(state['a'], member, work)
        return dict(context='A', retained_samples=samples)
    point_commit = None
    indices = {label['index'] for label in plan['candidate_labels'].values()}
    if plan['mode'] == 'library' and len(indices) == 1:
        index = next(iter(indices))
        state['b_points'][index] = _plus(state['b_points'][index], member)
        point_commit = dict(index=index, samples=samples)
        _add(work, 'independent_scoped_point_committed_targets')
        _add(work, 'independent_scoped_point_committed_samples', samples)
    for bank in state['b'].values():
        if state['arm'] == 'PARAM':
            parameter_compatibility(bank, member, work)
        else:
            advance_bank(bank, member, work)
    return dict(context='B', point_commit=point_commit,
                feasible_branches=sum(not bank['no_feasible'] for bank in state['b'].values()))


def covered(block, law):
    return all(lo <= law[op][cat] <= hi for op, row in block.items()
               for cat, (lo, hi) in row['bounds'].items())


def oracle_goal(case, law, work):
    """True-kernel safe optimum used only after decisions have been frozen."""
    pure = vectors(case, law)
    risks = {policy: vector[1] for policy, vector in pure.items()}
    goals = {policy: utility(vector, WEIGHTS['goal']) for policy, vector in pure.items()}
    return prior.settled.optimize(pure, risks, goals, work)['utility_lower']
