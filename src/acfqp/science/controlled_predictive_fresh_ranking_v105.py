"""The frozen V103 uniform-shrink recipe for independent fresh training histories."""
from copy import deepcopy
from time import perf_counter
import numpy as np
from .controlled_predictive_candidate_learning_v100 import metrics
from .controlled_predictive_capacity_ranking_v103 import (
    CandidateModel, RATE, L2_COEFFICIENT, L2_REFERENCE_PARAMETERS, initialize, objective, pair_gamma)

STEPS = 1000
FAMILY = 'UNIFORM_SHRINK'


def fit_model(records, checkpoint, hidden):
    """Fit one width from its original initialization using eligible whole roots."""
    start = perf_counter()
    training = [r for r in records if r['episode'] < checkpoint and r['episode'] % 5 != 4]
    heldout = [r for r in records if r['episode'] < checkpoint and r['episode'] % 5 == 4]
    if not training:
        raise ValueError('fresh ranking requires complete training roots')
    x = np.asarray([r['features'] for r in training], dtype=float)
    y = np.asarray([r['utilities'] for r in training], dtype=float)
    replicas = np.asarray([r['replica_utilities'] for r in training], dtype=float)
    if (x.ndim != 3 or x.shape[1] != 5 or y.shape != x.shape[:2] or replicas.ndim != 3
            or replicas.shape[::2] != y.shape or not np.all(replicas[:, :, 0] == 0)
            or not np.allclose(replicas.mean(axis=1), y, rtol=1e-10, atol=1e-12)):
        raise ValueError('five-candidate roots require paired replica utilities averaging to the root targets')
    mean, scale = x.mean(axis=(0, 1)), x.std(axis=(0, 1))
    scale[scale == 0] = 1.
    x = (x - mean) / scale
    gamma = pair_gamma(y, replicas)
    uniform_gamma = float(gamma.mean())
    episodes = {q: sorted({r['episode'] for r in training if r['query'] == q}) for q in ('reward', 'risk_goal')}
    tick = perf_counter()
    parameters = initialize(x.shape[-1], hidden)
    args = dict(replica_utilities=replicas, uniform_gamma=uniform_gamma)
    first, _ = objective(parameters, x, y, FAMILY, **args)
    first_moment, second_moment = ([np.zeros_like(p) for p in parameters] for _ in range(2))
    for step in range(1, STEPS + 1):
        _, gradients = objective(parameters, x, y, FAMILY, **args)
        for i, gradient in enumerate(gradients):
            first_moment[i] = .9 * first_moment[i] + .1 * gradient
            second_moment[i] = .999 * second_moment[i] + .001 * gradient ** 2
            parameters[i] -= RATE * (first_moment[i] / (1 - .9 ** step)) / (
                np.sqrt(second_moment[i] / (1 - .999 ** step)) + 1e-8)
    final, gradients = objective(parameters, x, y, FAMILY, **args)
    model = CandidateModel(parameters, mean.copy(), scale.copy(), checkpoint,
        FAMILY, deepcopy(episodes), uniform_gamma, STEPS)
    training_scores = np.asarray([model.score_candidates(r['features']) for r in training])
    heldout_scores = np.asarray([model.score_candidates(r['features']) for r in heldout])
    fit_log = dict(counts=dict(neural_model_fits=1, optimizer_steps=STEPS,
        diagnostic_candidate_predictions=5 * (len(training) + len(heldout))), initial_loss=first,
        final_loss=final, final_gradient_norm=float(np.sqrt(sum(np.sum(g * g) for g in gradients))),
        hidden=hidden, parameter_count=sum(p.size for p in parameters), l2_coefficient=L2_COEFFICIENT,
        training=metrics(training_scores, y, 'PAIRWISE_RANK'),
        heldout=metrics(heldout_scores, np.asarray([r['utilities'] for r in heldout]), 'PAIRWISE_RANK'),
        seconds=perf_counter() - tick)
    return model, dict(family=FAMILY, hidden=hidden, parameter_count=model.parameter_count,
        l2_coefficient=L2_COEFFICIENT, l2_reference_parameters=L2_REFERENCE_PARAMETERS,
        checkpoint=checkpoint, training_episodes=episodes, training_roots=len(training),
        heldout_roots=len(heldout), normalization_training_roots=len(training), uniform_gamma=uniform_gamma,
        training_replica_rows=int(replicas.shape[0] * replicas.shape[1]), conflict_mass_training_roots=len(training),
        conflict_pairs=int(np.count_nonzero(gamma > 0)), total_training_pairs=int(gamma.size),
        models={FAMILY: fit_log}, counts=dict(neural_model_fits=1, optimizer_steps=STEPS),
        seconds=perf_counter() - start)
