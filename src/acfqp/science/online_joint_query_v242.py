"""Fixed online routing of joint evidence and the two convex risk nulls.

All necessary counts contain paid source observations and this arm's observed
prefix.  The route selects one proof engine; it never ORs their conclusions or
uses optimizer success as evidence.  Training, acquisition and stopping remain
the responsibility of the lifecycle planner.
"""
from fractions import Fraction as F

from . import convex_query_null_v240 as convex
from . import joint_query_evidence_v235 as joint


def _add(work, field):
    if work is not None:
        work[field] = work.get(field, 0)+1


def _convex_certificate(counts, case, query, chosen, other, cache, work):
    family = joint.canonical_family(query, chosen, other)
    projected = joint.project_counts(counts, family)
    sc, dc = joint.COST_PRIOR[case['operating']]
    cost = dc-sc if family == 'S_D_FULL' else F(case['retry_cost'])
    key = (family, query, chosen, other, cost,
           tuple((name, tuple(projected[name].items())) for name in joint.FAMILIES[family]))
    _add(work, 'online_convex_certificate_calls')
    if key in cache:
        _add(work, 'online_convex_certificate_cache_hits')
        return cache[key]
    point, optimizer = convex._proposal(projected, case, family)
    _add(work, 'online_convex_proposal_calls')
    tangent = convex._tangent(point, projected, case, family) if point is not None and convex._interior(point) else None
    certified = tangent is not None and tangent['certified']
    result = dict(family=family, projected_counts=projected, optimizer=optimizer,
                  proposed_point=point, global_tangent=tangent)
    proof = dict(query=query, chosen=chosen, other=other, family=family,
        projected_counts=projected, threshold=joint.THRESHOLD, regret_threshold=joint.REGRET,
        status='certified' if certified else 'unknown', certified=certified,
        engine='convex_tangent', relevant_cost=cost, result=result)
    cache[key] = proof
    return proof


def certificates(counts, case, point_queries, cache, work):
    """AND the original alternatives under one declared engine per comparison."""
    if point_queries['reward']['policy'] != 'WAIT':
        raise ValueError('the frozen reward query uses cost-optimal WAIT')
    old_cache = cache.setdefault('V235', {})
    convex_cache = cache.setdefault('convex_tangent', {})
    decisions = {'reward': dict(policy='WAIT', certified=True, kind='known_nonnegative_cost')}
    records = []
    for query in ('goal', 'risk'):
        chosen = point_queries[query]['policy']
        comparisons = []
        for other in joint.POLICIES:
            if other == chosen:
                continue
            _add(work, 'online_query_comparison_calls')
            if query == 'risk' and chosen == 'DETOUR_RETURN' and other in ('SHORT', 'DETOUR_RETRY'):
                proof = _convex_certificate(counts, case, query, chosen, other, convex_cache, work)
            else:
                proof = joint.certificate(counts, case, query, chosen, other, old_cache, work)
            comparisons.append(proof)
        decisions[query] = dict(policy=chosen, certified=all(row['certified'] for row in comparisons),
                                comparisons=comparisons)
        records.extend(comparisons)
    return dict(queries=decisions, all_ready=all(row['certified'] for row in decisions.values()),
                comparison_records=records, threshold=joint.THRESHOLD)
