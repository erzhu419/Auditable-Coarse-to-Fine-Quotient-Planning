"""One frozen goal bad-kernel candidate checked against all paid regions.

The retained V235 dual supplies a reconstruction proposal, not a primal
optimum. A single algebraic SHORT repair follows; exact V235 membership
checks never replace a full categorical event with its marginal envelope.
"""
from copy import deepcopy
from fractions import Fraction as F

from . import joint_query_evidence_v235 as joint

STRICT_GAP = joint.REGRET + F(1, 10**6)
CANONICAL = 'S_D_FULL_R'
S, D, R = joint.OPERATORS


def _simplex(kernel):
    return (set(kernel) == set(joint.OPERATORS)
            and all(set(kernel[op]) == set(joint.ALPHABETS[op])
                    and sum(kernel[op].values()) == 1
                    and min(kernel[op].values()) >= 0
                    for op in joint.OPERATORS))


def reconstruct(certificate, case):
    """Recover one retained proposal and repair SHORT exactly once.

    Failed recovery or an infeasible repair stays unavailable. No alternative
    leaf, clipping, numerical optimizer or fresh observation is used.
    """
    kind = certificate['witness_kind']
    result = dict(kind=kind, leaf_index=None, recovered_kernel=None,
                  short_delivery_unclipped=None, repair_applied=False,
                  kernel=None, gap=None, reason=None)
    if kind == 'bad_null_mle':
        recovered = {op: {cat: F(value) for cat, value in row.items()}
                     for op, row in certificate['bad_null_kernel'].items()}
    elif kind == 'global_likelihood_dual':
        finite = [(index, leaf) for index, leaf in enumerate(certificate['leaves'])
                  if leaf['log_bad_likelihood_upper'] is not None]
        if not finite:
            return dict(result, reason='no_finite_leaf')
        index, leaf = max(finite, key=lambda item: F(item[1]['log_bad_likelihood_upper']))
        result['leaf_index'] = index
        recovered = {}
        for op in (S, D):
            witness = leaf['row_witnesses'][op]
            if witness['kind'] == 'free_simplex':
                return dict(result, reason=f'free_simplex:{op}')
            counts = certificate['embedded_counts'][op]
            if not sum(counts.values()):
                return dict(result, reason=f'zero_row:{op}')
            multiplier, nu = F(leaf['multiplier']), F(witness['nu'])
            row = {}
            for cat in joint.ALPHABETS[op]:
                denominator = nu - multiplier * F(leaf['gap_coefficients'][op][cat])
                if denominator <= 0:
                    return dict(result, reason=f'nonpositive_denominator:{op}:{cat}')
                row[cat] = F(counts[cat]) / denominator
            total = sum(row.values())
            if total <= 0:
                return dict(result, reason=f'zero_reconstructed_row:{op}')
            recovered[op] = {cat: value / total for cat, value in row.items()}
        retry = F(leaf['retry_likelihood']['probability'])
        recovered[R] = {'DELIVERY': retry, 'LOST': 1-retry}
    else:
        return dict(result, reason='unsupported_witness_kind')

    result['recovered_kernel'] = recovered
    if not _simplex(recovered):
        return dict(result, reason='recovered_kernel_not_simplex')
    sc, dc = joint.COST_PRIOR[case['operating']]
    detour, retry = recovered[D], recovered[R]['DELIVERY']
    short = (sc-dc+4*detour['DELIVERY']
             +detour['RECOVERY']*(4*retry-F(case['retry_cost']))-STRICT_GAP)/4
    result.update(short_delivery_unclipped=short, repair_applied=True)
    if not 0 <= short <= 1:
        return dict(result, reason='short_delivery_outside_simplex')
    kernel = deepcopy(recovered)
    kernel[S] = {'DELIVERY': short, 'LOST': 1-short}
    projected = joint.project_parameters(kernel, CANONICAL)
    gap = joint.gap(case, 'goal', 'SHORT', 'DETOUR_RETRY', projected)
    if not _simplex(kernel) or gap <= joint.REGRET:
        return dict(result, reason='repair_not_strict_bad_kernel', gap=gap)
    return dict(result, kernel=kernel, gap=gap)


def classify(counts, constraints, case, certificate):
    """Check a fixed candidate in canonical, eight query and execution events.

    Rejecting this one point does not prove an empty bad null. Original
    source/pool/member thresholds and event labels stay attached to each row.
    """
    candidate = reconstruct(certificate, case)
    result = dict(candidate=candidate, canonical_inside=None,
                  all_query_inside=None, all_execution_inside=None,
                  query_regions={}, execution_regions=[], status='unknown')
    kernel = candidate['kernel']
    if kernel is None:
        return result
    queries = {
        family: joint.membership(joint.project_counts(counts, family),
                                 joint.project_parameters(kernel, family))
        for family in joint.FAMILIES}
    execution = []
    for op in joint.OPERATORS:
        for position, region in enumerate(constraints[op]):
            member = joint.membership({op: region['counts']}, {op: kernel[op]},
                                      threshold=region['threshold'])
            execution.append(dict(operator=op, position=position,
                event=region['event'], threshold=region['threshold'],
                counts=deepcopy(region['counts']), membership=member))
    canonical = queries[CANONICAL]['exact_inside']
    all_query = all(row['exact_inside'] for row in queries.values())
    all_execution = all(row['membership']['exact_inside'] for row in execution)
    status = ('unknown' if not canonical else 'full_region_bad_witness'
              if all_query and all_execution else 'paid_constraints_reject_candidate')
    result.update(canonical_inside=canonical, all_query_inside=all_query,
                  all_execution_inside=all_execution, query_regions=queries,
                  execution_regions=execution, status=status)
    return result
