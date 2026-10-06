"""Necessary paid-suffix information budgets for the fixed V237 bad kernels.

The true rows enter this oracle diagnostic only.  The bounds give any adaptive
sampler the best row KL, while retaining the original predictive evidence and
threshold.  They neither propose samples nor establish a feasible learner.
"""
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction as F

from . import source_predictive_evidence_v236 as predictive

THRESHOLD, BATCH, BISECTIONS = 960, 16, 64


def _logs(value):
    return tuple(map(F, predictive.log_bounds(value)))


def categorical_kl_bounds(p_row, q_row):
    """Outward bounds on KL(p || q), skipping exact zero-probability terms."""
    lower, upper = F(0), F(0)
    for category, probability in p_row.items():
        probability = F(probability)
        if probability:
            lo, hi = _logs(probability/F(q_row[category]))
            lower += probability*lo
            upper += probability*hi
    return max(F(0), lower), max(F(0), upper)


def exact_e0(training_counts, validation_counts, parameters):
    """Exact V236 predictive likelihood ratio on the validation outcomes only."""
    numerator, denominator = F(1), F(1)
    for name, row in validation_counts.items():
        numerator *= predictive.predictive_normalizer(
            tuple(training_counts[name][category] for category in row), tuple(row.values()))
        for category, count in row.items():
            denominator *= F(parameters[name][category])**count
    return numerator/denominator


def _binary_kl_bounds(probability, log_alpha, log_complement):
    """Outward Bernoulli KL bounds with the large-alpha logs computed once."""
    probability = F(probability)
    lower, upper = F(0), F(0)
    for value, null_logs in ((probability, log_alpha), (1-probability, log_complement)):
        if value:
            lo, hi = _logs(value)
            lower += value*(lo-null_logs[1])
            upper += value*(hi-null_logs[0])
    return max(F(0), lower), max(F(0), upper)


def _decimal_bounds(value):
    """Compact directed bounds without converting a large integer to text."""
    value = F(value)
    with localcontext() as context:
        context.prec, context.rounding = 80, ROUND_FLOOR
        lower = Decimal(value.numerator)/Decimal(value.denominator)
        context.rounding = ROUND_CEILING
        upper = Decimal(value.numerator)/Decimal(value.denominator)
    return dict(lower=str(lower), upper=str(upper))


def _compact_logs(value):
    lower, upper = predictive.log_bounds(value)
    return dict(lower=lower, upper=upper)


def _ceil(value):
    value = F(value)
    return -(-value.numerator//value.denominator)


def budget_bounds(e0, truth_named, witness_named, budget, target=F(3, 4)):
    """Necessary expected samples, batch cap, and a certified power upper bound.

    Only the bisection upper endpoint is claimed as an outward bound.  It moves
    down solely when a KL lower bound exceeds the information-budget upper
    bound.  Working lower endpoints are numerical probes, not root bounds.
    Large exact e0 and alpha stay internal; returned scalars are compact logs,
    decimal intervals, or bounded-size fractions.
    """
    e0, target, budget = F(e0), F(target), int(budget)
    alpha = e0/THRESHOLD
    if not 0 < alpha <= 1:
        raise ValueError('V237 requires a positive retained-witness ratio at or below 960')
    per_row = {name: categorical_kl_bounds(row, witness_named[name])
               for name, row in truth_named.items()}
    imax_upper = max(upper for _, upper in per_row.values())
    information_budget_upper = budget*imax_upper
    log_alpha = _logs(alpha)
    log_complement = _logs(1-alpha) if alpha < 1 else None
    information_need_lower = (_binary_kl_bounds(target, log_alpha, log_complement)[0]
                              if alpha < target else F(0))
    if information_need_lower and not imax_upper:
        expected_lower, required_cap = None, None
    else:
        expected_lower = information_need_lower/imax_upper if imax_upper else F(0)
        required_cap = BATCH*_ceil(expected_lower/BATCH)
    insufficient = information_budget_upper < information_need_lower
    lower, upper, boundary_kl_lower, steps = F(0), F(1), None, 0
    if alpha < 1:
        for _ in range(BISECTIONS):
            midpoint = (lower+upper)/2
            if midpoint <= alpha:
                lower = midpoint
            else:
                midpoint_kl_lower = _binary_kl_bounds(midpoint, log_alpha, log_complement)[0]
                if midpoint_kl_lower > information_budget_upper:
                    upper, boundary_kl_lower = midpoint, midpoint_kl_lower
                else:
                    lower = midpoint
            steps += 1
    return dict(
        target=str(target), available_samples=budget,
        per_row_kl={name: dict(lower=str(lo), upper=str(hi)) for name, (lo, hi) in per_row.items()},
        imax_upper=str(imax_upper), information_budget_upper=str(information_budget_upper),
        log_e0=_compact_logs(e0), log_alpha=_compact_logs(alpha), alpha_bounds=_decimal_bounds(alpha),
        information_need_lower=str(information_need_lower),
        expected_samples_lower=str(expected_lower) if expected_lower is not None else 'Infinity',
        required_batch_cap=required_cap, budget_insufficient=insufficient,
        power_upper=str(upper), power_upper_bounds=_decimal_bounds(upper),
        power_upper_kl_lower=str(boundary_kl_lower) if boundary_kl_lower is not None else None,
        power_bisection_steps=steps,
        scope='oracle_necessary_suffix_budget_not_a_sampling_strategy_or_certificate')
