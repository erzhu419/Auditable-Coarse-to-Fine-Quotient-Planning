"""Global query qualification from source training and completed validation.

This pure certificate engine receives already frozen observed rows.  Its
predictive numerator uses source-trained Jeffreys distributions; every global
bad-null likelihood bound uses validation counts alone.  It does not acquire
observations, change selected policies, or evaluate true probabilities.
"""
from fractions import Fraction as F

from . import kernel_query_profile_v232 as profile
from .joint_query_evidence_v235 import (
    FAMILIES, POLICIES, REGRET, THRESHOLD, canonical_family, embedded_counts,
    project_counts,
)
from .source_predictive_evidence_v236 import predictive_normalizer


def _count_key(counts, family):
    return tuple((name, tuple(counts[name].items())) for name in FAMILIES[family])


def certificate(training, validation, case, query, chosen, other, cache=None, work=None):
    """Exclude the whole gap >= .05 null with fixed global outward bounds.

    The unchanged V232 engine evaluates legal likelihood dual witnesses over
    all 32 retry cells when nonlinear.  A local optimizer supplies only a dual
    proposal, never the certification decision.
    """
    family = canonical_family(query, chosen, other)
    trained = project_counts(training, family)
    validated = project_counts(validation, family)
    cache_key = (case['operating'], F(case['retry_cost']), query, chosen, other,
                 family, _count_key(trained, family), _count_key(validated, family),
                 profile.PARTITIONS)
    profile._add(work, 'predictive_certificate_calls')
    if cache is not None and cache_key in cache:
        profile._add(work, 'predictive_certificate_cache_hits')
        return cache[cache_key]
    counts = embedded_counts(validated, family)
    log_predictive_lower = sum((profile._log_bounds(predictive_normalizer(
        tuple(trained[name][category] for category in validated[name]),
        tuple(validated[name].values())))[0] for name in FAMILIES[family]), F(0))
    log_threshold_upper = profile._log_bounds(THRESHOLD)[1]
    base = dict(query=query, chosen=chosen, other=other, family=family,
                training_counts=trained, validation_counts=validated, embedded_counts=counts,
                threshold=THRESHOLD, regret_threshold=REGRET,
                log_predictive_lower=log_predictive_lower, log_threshold_upper=log_threshold_upper)
    mle = {operator: {category: F(count, sum(row.values())) if sum(row.values()) else F(1, len(row))
                      for category, count in row.items()} for operator, row in counts.items()}
    mle_gap = profile.gap(case, query, chosen, other, mle)
    if mle_gap >= REGRET:
        # Q is the posterior expectation of validation likelihood, hence
        # Q <= max L(validation).  This embedded MLE attains that maximum.
        result = dict(base, status='unknown', certified=False, witness_kind='bad_null_mle',
            bad_null_kernel=mle, bad_null_gap=mle_gap, partitions=0, leaves=[],
            log_bad_likelihood_upper=None, log_e_lower=None)
        profile._add(work, 'predictive_bad_null_mle')
    else:
        slope = (profile.gap(case, query, chosen, other, profile._kernel(recovery=F(1), retry=F(1)))
                 -profile.gap(case, query, chosen, other, profile._kernel(recovery=F(1))))
        partitions = profile.PARTITIONS if slope else 1
        intervals = [(F(index, partitions), F(index+1, partitions)) for index in range(partitions)]
        leaves = [profile._leaf(case, query, chosen, other, counts, interval,
                    interval[1] if slope >= 0 else interval[0], REGRET, work) for interval in intervals]
        profile._add(work, 'predictive_partition_leaves', len(leaves))
        finite = [leaf['log_bad_likelihood_upper'] for leaf in leaves
                  if leaf['log_bad_likelihood_upper'] is not None]
        if not finite:
            result = dict(base, status='certified', certified=True, witness_kind='empty_global_bad_null',
                partitions=partitions, retry_slope=slope, leaves=leaves,
                log_bad_likelihood_upper=None, log_e_lower=None)
        else:
            upper = max(finite)
            lower = log_predictive_lower-upper
            certified = lower > log_threshold_upper
            result = dict(base, status='certified' if certified else 'unknown', certified=certified,
                witness_kind='global_likelihood_dual', partitions=partitions, retry_slope=slope,
                leaves=leaves, log_bad_likelihood_upper=upper, log_e_lower=lower)
    profile._add(work, 'predictive_unique_certificates')
    if cache is not None:
        cache[cache_key] = result
    return result


def certificates(training, validation, case, point_queries, cache=None, work=None):
    """AND every original goal/risk alternative; cost-optimal WAIT is analytic."""
    if point_queries['reward']['policy'] != 'WAIT':
        raise ValueError('the frozen reward query uses cost-optimal WAIT')
    decisions = {'reward': dict(policy='WAIT', certified=True, kind='known_nonnegative_cost')}
    records = []
    for query in ('goal', 'risk'):
        chosen = point_queries[query]['policy']
        comparisons = [certificate(training, validation, case, query, chosen, other, cache, work)
                       for other in POLICIES if other != chosen]
        decisions[query] = dict(policy=chosen, certified=all(row['certified'] for row in comparisons),
                                comparisons=comparisons)
        records.extend(comparisons)
    return dict(queries=decisions, all_ready=all(row['certified'] for row in decisions.values()),
                comparison_records=records, threshold=THRESHOLD)
