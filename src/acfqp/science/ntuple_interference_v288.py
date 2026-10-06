"""Isolated V120 updates on retained afterstates, without fitting a table.

An address repeated within either state's 32 features retains its multiplicity.
The resulting kernel uses V120's actual update scale, with no division by 32.
Discovery and validation moments describe the retained batches; their sample
variation is not an identified population noise variance.
"""
import numpy as np

from .controlled_predictive_ntuple_td_v120 import ALPHA


def feature_kernel(features):
    """Return K[i,j] = sum_address count_i(address) * count_j(address)."""
    features = np.asarray(features, dtype=np.int64)
    n = len(features)
    kernel = np.zeros((n, n), dtype=np.int64)
    addresses = features.reshape(-1)
    owners = np.repeat(np.arange(n, dtype=np.int64), 32)
    order = np.argsort(addresses, kind='stable')
    addresses, owners = addresses[order], owners[order]
    boundaries = np.r_[0, np.flatnonzero(addresses[1:] != addresses[:-1]) + 1,
                       len(addresses)]
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        rows, counts = np.unique(owners[start:end], return_counts=True)
        kernel[np.ix_(rows, rows)] += counts[:, None] * counts[None, :]
    return kernel


def pair_metrics(vi, vj, discovery32, validation32, k, alpha=ALPHA):
    """Score an isolated update at i against retained validation returns at j.

    ``vi`` and ``vj`` are the frozen, query-converted direct afterstate leaf
    predictions. Labels are future utility after the current action, excluding
    that action's reward. No H2 expected-value tail belongs in these arguments.
    The same validation batch evaluates all updates, so its variance contributes
    to the baseline MSE and cancels from the update's MSE difference.
    """
    discovery = np.asarray(discovery32, dtype=np.float64)
    validation = np.asarray(validation32, dtype=np.float64)
    vi, vj = float(vi), float(vj)
    mean1, mean2 = float(discovery.mean()), float(validation.mean())
    var1, var2 = float(discovery.var()), float(validation.var())
    beta = float(alpha) * int(k)
    single_deltas = beta * (discovery - vi)
    delta = beta * (mean1 - vi)
    bias = vj - mean2
    baseline = float(np.mean((vj - validation) ** 2))
    mean_delta_mse = delta * delta + 2. * bias * delta
    single_delta_mse = float(np.mean(single_deltas * single_deltas
                                   + 2. * bias * single_deltas))
    penalty = beta * beta * var1
    return dict(
        vi=vi, vj=vj, k=int(k), alpha=float(alpha), beta=beta,
        batch1_count=int(discovery.size), batch2_count=int(validation.size),
        batch1_mean=mean1, batch2_mean=mean2,
        batch1_popvar=var1, batch2_popvar=var2,
        batch1_second_moment=float(np.mean(discovery * discovery)),
        batch2_second_moment=float(np.mean(validation * validation)),
        baseline_bias=bias, baseline_validation_mse=baseline,
        mean_label_prediction_delta=delta,
        mean_label_delta_mse=mean_delta_mse,
        single_label_mean_delta_mse=single_delta_mse,
        empirical_noise_penalty=penalty,
        mean_label_validation_mse=baseline + mean_delta_mse,
        single_label_mean_validation_mse=baseline + single_delta_mse)
