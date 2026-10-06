"""Two prespecified endpoint bad kernels: retained and empirical R-centered.

The second keeps the same originally recovered D row and performs its own
one-time SHORT repair. Neither a rejected point nor a missing recovery proves
the complete bad null empty. All original full categorical events are used.
"""
from copy import deepcopy
from fractions import Fraction as F

from . import goal_joint_region_v244 as original

joint = original.joint
S, D, R = original.S, original.D, original.R
VARIANTS = ('RETAINED', 'R_CENTERED')


def _centered(counts, case, parent):
    candidate = dict(kind='r_centered_fixed_d', parent_kind=parent['kind'],
        leaf_index=parent['leaf_index'], original_retry_probability=None,
        recovered_kernel=None, short_delivery_unclipped=None, repair_applied=False,
        kernel=None, gap=None, reason=parent['reason'])
    recovered = parent['recovered_kernel']
    if recovered is None or not original._simplex(recovered):
        return candidate
    candidate['original_retry_probability'] = recovered[R]['DELIVERY']
    recovered = deepcopy(recovered)
    q = F(counts[R]['DELIVERY'], sum(counts[R].values()))
    recovered[R] = {'DELIVERY': q, 'LOST': 1-q}
    sc, dc = joint.COST_PRIOR[case['operating']]
    row = recovered[D]
    short = (sc-dc+4*row['DELIVERY']+row['RECOVERY']*(4*q-F(case['retry_cost']))
             -original.STRICT_GAP)/4
    candidate.update(recovered_kernel=recovered, short_delivery_unclipped=short,
                     repair_applied=True, reason=None)
    if not 0 <= short <= 1:
        return dict(candidate, reason='short_delivery_outside_simplex')
    kernel = deepcopy(recovered)
    kernel[S] = {'DELIVERY': short, 'LOST': 1-short}
    gap = joint.gap(case, 'goal', 'SHORT', 'DETOUR_RETRY',
                    joint.project_parameters(kernel, original.CANONICAL))
    if not original._simplex(kernel) or gap <= joint.REGRET:
        return dict(candidate, reason='repair_not_strict_bad_kernel', gap=gap)
    return dict(candidate, kernel=kernel, gap=gap)


def _classify(counts, constraints, candidate):
    result = dict(candidate=candidate, canonical_inside=None, all_query_inside=None,
        all_execution_inside=None, query_regions={}, execution_regions=[], status='unknown')
    kernel = candidate['kernel']
    if kernel is None:
        return result
    queries = {family: joint.membership(joint.project_counts(counts, family),
                joint.project_parameters(kernel, family)) for family in joint.FAMILIES}
    events = []
    for op in joint.OPERATORS:
        for position, event in enumerate(constraints[op]):
            member = joint.membership({op: event['counts']}, {op: kernel[op]}, event['threshold'])
            events.append(dict(operator=op, position=position, event=event['event'],
                threshold=event['threshold'], counts=deepcopy(event['counts']), membership=member))
    canonical = queries[original.CANONICAL]['exact_inside']
    all_query = all(row['exact_inside'] for row in queries.values())
    all_execution = all(row['membership']['exact_inside'] for row in events)
    status = ('unknown' if not canonical else 'full_region_bad_witness'
              if all_query and all_execution else 'paid_constraints_reject_candidate')
    result.update(canonical_inside=canonical, all_query_inside=all_query,
        all_execution_inside=all_execution, query_regions=queries, execution_regions=events, status=status)
    return result


def classify(counts, constraints, case, certificate):
    retained = original.classify(counts, constraints, case, certificate)
    centered = _classify(counts, constraints, _centered(counts, case, retained['candidate']))
    variants = dict(RETAINED=retained, R_CENTERED=centered)
    empirical = {op: {category: F(count, sum(row.values())) for category, count in row.items()}
                 for op, row in counts.items()}
    distances = {variant: {op: (sum((abs(kernel[op][category]-empirical[op][category])
                 for category in joint.ALPHABETS[op]), F(0))/2 if kernel is not None else None)
                 for op in joint.OPERATORS} for variant, record in variants.items()
                 for kernel in (record['candidate']['kernel'],)}
    return dict(variants=variants, empirical_rows=empirical, distances=distances)
