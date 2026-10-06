"""Fixed-prediction diagnostics of eight retained paired suffix outcomes.

Each value is the complete query-utility difference H1 minus H2 on one
common suffix. Independent suffix streams make s²/n an estimate of the
eight-suffix mean's sampling variance. Subtracting it from squared error
is intentionally not clipped: individual estimates can be negative.
The 35 balanced partitions are descriptive, overlapping partitions, not
35 independent replications.
"""
from itertools import combinations
from math import fsum


def balanced_partitions():
    """Return each unordered 4/4 partition once, with index zero first."""
    return tuple((first, tuple(index for index in range(8) if index not in first))
                 for tail in combinations(range(1, 8), 3)
                 for first in [(0, *tail)])


def _sign(value):
    return int(value > 0.)-int(value < 0.)


def _halves(values, first, second):
    means = [fsum(values[index] for index in indices)/4.
             for indices in (first, second)]
    signs = [_sign(value) for value in means]
    gates = [value > 0. for value in means]
    return dict(indices=[list(first), list(second)], means=means, signs=signs,
                gates=gates, sign_agreement=signs[0] == signs[1],
                gate_agreement=gates[0] == gates[1],
                positive_both=signs == [1, 1], negative_both=signs == [-1, -1],
                mixed_sign=signs[0]*signs[1] == -1,
                zero_both=signs == [0, 0], one_zero=(signs[0] == 0) != (signs[1] == 0))


def label_diagnostics(values, predictions):
    """Summarize label noise and fixed prediction errors without fitting.

``predictions`` maps method names to total query-utility advantage estimates.
The cross-half product estimates squared error against the latent suffix
mean when the predictor is independent of the held-out suffix outcomes.
"""
    values = tuple(map(float, values))
    if len(values) != 8:
        raise ValueError('V146 uses exactly eight retained paired suffixes')
    mean = fsum(values)/8.
    variance = fsum((value-mean)**2 for value in values)/7.
    noise = variance/8.
    fixed = _halves(values, tuple(range(4)), tuple(range(4, 8)))
    partitions = [_halves(values, first, second)
                  for first, second in balanced_partitions()]
    rates = {name: sum(partition[name] for partition in partitions)/35.
             for name in ('sign_agreement', 'gate_agreement', 'positive_both',
                          'negative_both', 'mixed_sign', 'zero_both', 'one_zero')}
    methods = {}
    for method, estimate in predictions.items():
        estimate = float(estimate)
        error = (estimate-mean)**2
        methods[method] = dict(prediction=estimate, squared_error=error,
                               noise_adjusted_squared_error=error-noise,
                               select_h1=estimate > 0.,
                               cross_half_squared_error=(estimate-fixed['means'][0])
                               *(estimate-fixed['means'][1]))
    return dict(n=8, mean=mean, variance=variance, mean_noise_variance=noise,
                fixed_halves=fixed, partitions=dict(count=35, half_count=70, **rates),
                methods=methods)
