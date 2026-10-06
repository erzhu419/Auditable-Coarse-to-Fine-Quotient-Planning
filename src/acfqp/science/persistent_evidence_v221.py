"""Persist uniquely certified target evidence without pooling confidence counts."""
from copy import deepcopy
from fractions import Fraction as F

from . import fixed_source_acquisition_v219 as prior
from . import latent_mechanisms_v213 as evidence
from . import query_sufficient_v214 as query_core

OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
empty, vectors, queries = prior.empty, prior.vectors, prior.queries


def prepare(anchors, work):
    work['persistent_preparations'] += 1
    return dict(counts=deepcopy(anchors),
                bounds=[evidence.boxes(anchor, work) for anchor in anchors],
                commits=[0]*len(anchors))


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False,
              state=None):
    if arm != 'PERSIST':
        return prior.make_plan(member, anchors, case, 'SET' if arm == 'FROZEN' else arm,
                               work, identity, force_member)
    cumulative = state['counts']
    if force_member:
        return prior.make_plan(member, cumulative, case, 'SET', work, identity, True)
    raw, blocks, candidates = evidence.boxes(member, work), {}, []
    for i, source in enumerate(state['bounds']):
        block, ok = deepcopy(raw), True
        for op in OPERATORS:
            for cat in ALPHABETS[op]:
                a, b = raw[op]['bounds'][cat], source[op]['bounds'][cat]
                pair = [max(a[0], b[0]), min(a[1], b[1])]
                if pair[0] > pair[1]:
                    ok = False
                block[op]['bounds'][cat] = pair
        if ok:
            candidates.append(i)
            blocks[i] = block
    if candidates:
        risks, goals, means = {}, {}, []
        for i, block in blocks.items():
            r = evidence.robust.risk_bounds(block, work)
            g = evidence.robust.goals_lower(block, case, work)
            for policy in r:
                risks[policy] = max(risks.get(policy, F(0)), r[policy])
                goals[policy] = min(goals.get(policy, g[policy]), g[policy])
            combined = {op: {cat: member[op][cat]+cumulative[i][op][cat]
                             for cat in ALPHABETS[op]} for op in OPERATORS}
            means.append(evidence.posterior(combined))
        p = {op: {cat: sum(mean[op][cat] for mean in means)/len(means)
                  for cat in ALPHABETS[op]} for op in OPERATORS}
        envelope = deepcopy(raw)
        for op in OPERATORS:
            for cat in ALPHABETS[op]:
                envelope[op]['bounds'][cat] = [
                    min(block[op]['bounds'][cat][0] for block in blocks.values()),
                    max(block[op]['bounds'][cat][1] for block in blocks.values())]
        mode = 'library'
    else:
        envelope, mode = raw, 'member'
        risks = evidence.robust.risk_bounds(raw, work)
        goals = evidence.robust.goals_lower(raw, case, work)
        p = evidence.posterior(member)
    pure = vectors(case, p)
    work['planning_calls'] += 1
    work['persistent_planning_calls'] += 1
    result = dict(**evidence.robust.solve(pure, risks, goals, work),
                  envelopes=envelope, risks=risks, goals_lower=goals,
                  pure_vectors=pure, candidates=candidates,
                  candidate_envelopes=blocks, mode=mode)
    result['query_proxy'] = query_core.query_proxy(member, cumulative, case, result, work)
    result['query_ready'] = (mode == 'library' and result['utility_lower'] >= 2
                             and result['query_proxy'] is not None
                             and result['query_proxy'] <= query_core.THRESHOLD)
    return result


def choose(member, anchors, case, arm, plan, spent, work, state=None):
    if arm == 'PERSIST':
        return prior.choose(member, state['counts'], case, 'SET', plan, spent, work)
    return prior.choose(member, anchors, case, 'SET' if arm == 'FROZEN' else arm,
                        plan, spent, work)


def commit(state, member, plan, work):
    """Called once after the actual terminal plan and before the next target."""
    if (plan['utility_lower'] < 2 or plan['mode'] != 'library'
            or len(plan['candidates']) != 1):
        return None
    index = plan['candidates'][0]
    raw = evidence.boxes(member, work)
    for op in OPERATORS:
        for cat in ALPHABETS[op]:
            state['counts'][index][op][cat] += member[op][cat]
            old, new = state['bounds'][index][op]['bounds'][cat], raw[op]['bounds'][cat]
            state['bounds'][index][op]['bounds'][cat] = [max(old[0], new[0]), min(old[1], new[1])]
    state['commits'][index] += 1
    samples = sum(sum(row.values()) for row in member.values())
    work['persistent_committed_tasks'] += 1
    work['persistent_committed_samples'] += samples
    return dict(source_index=index, samples=samples)
