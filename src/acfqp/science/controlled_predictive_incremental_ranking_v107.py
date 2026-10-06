"""Frozen-half statistics with fresh or half-parameter starts on full experience."""
from copy import deepcopy
from time import perf_counter
import numpy as np
from .controlled_predictive_candidate_learning_v100 import metrics
from .controlled_predictive_capacity_ranking_v103 import (
    CandidateModel, RATE, L2_COEFFICIENT, L2_REFERENCE_PARAMETERS, initialize, objective)

STEPS = 1000
FAMILY = 'UNIFORM_SHRINK'
MODES = ('FROZEN_STATS_SCRATCH', 'FROZEN_STATS_WARM')


def fit_update(records, checkpoint, half_payload, mode):
    """Use half statistics for both starts and reset Adam moments in either mode."""
    start = perf_counter()
    if mode not in MODES:
        raise ValueError(f'unknown frozen-statistics update {mode}')
    half = CandidateModel.from_payload(half_payload)
    hidden = half.hidden
    if half.family != FAMILY or hidden not in (4, 16) or half.checkpoint >= checkpoint:
        raise ValueError('update requires an earlier UNIFORM_SHRINK H4 or H16 payload')
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
    mean, scale = half.mean.copy(), half.scale.copy()
    x = (x - mean) / scale
    uniform_gamma = half.uniform_gamma
    statistics_roots = sum(len(episodes) for episodes in half.training_episodes.values())
    episodes = {q: sorted({r['episode'] for r in training if r['query'] == q}) for q in ('reward', 'risk_goal')}
    tick = perf_counter()
    warm = mode == 'FROZEN_STATS_WARM'
    parameters = [p.copy() for p in half.parameters] if warm else initialize(x.shape[-1], hidden)
    inherited_steps = half.optimizer_steps if warm else 0
    expected_initial = half.parameters if warm else initialize(x.shape[-1], hidden)
    checks = dict(initial_parameters_from_half_or_original=all(
        np.array_equal(actual, expected) for actual, expected in zip(parameters, expected_initial)))
    args = dict(replica_utilities=replicas, uniform_gamma=uniform_gamma)
    first, _ = objective(parameters, x, y, FAMILY, **args)
    first_moment, second_moment = ([np.zeros_like(p) for p in parameters] for _ in range(2))
    checks['optimizer_moments_reset'] = all(np.all(moment == 0) for moment in first_moment + second_moment)
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
    checks['frozen_half_statistics'] = (np.array_equal(model.mean, half.mean)
        and np.array_equal(model.scale, half.scale) and model.uniform_gamma == half.uniform_gamma)
    checks['full_training_roster'] = model.training_episodes == episodes and model.checkpoint == checkpoint
    training_scores = np.asarray([model.score_candidates(r['features']) for r in training])
    heldout_scores = np.asarray([model.score_candidates(r['features']) for r in heldout])
    fit_log = dict(counts=dict(neural_model_fits=1, optimizer_steps=STEPS,
        diagnostic_candidate_predictions=5 * (len(training) + len(heldout))), initial_loss=first,
        final_loss=final, final_gradient_norm=float(np.sqrt(sum(np.sum(g * g) for g in gradients))),
        hidden=hidden, parameter_count=sum(p.size for p in parameters), l2_coefficient=L2_COEFFICIENT,
        training=metrics(training_scores, y, 'PAIRWISE_RANK'),
        heldout=metrics(heldout_scores, np.asarray([r['utilities'] for r in heldout]), 'PAIRWISE_RANK'),
        seconds=perf_counter() - tick)
    return model, dict(mode=mode, family=FAMILY, hidden=hidden, parameter_count=model.parameter_count,
        initialization='half_parameters' if warm else 'original_initialization',
        optimizer_state='reset_zero_moments', new_optimizer_steps=STEPS,
        inherited_parameter_steps=inherited_steps, parameter_lineage_steps=inherited_steps + STEPS,
        statistics_source_checkpoint=half.checkpoint, statistics_training_episodes=deepcopy(half.training_episodes), checks=checks,
        l2_coefficient=L2_COEFFICIENT, l2_reference_parameters=L2_REFERENCE_PARAMETERS,
        checkpoint=checkpoint, training_episodes=episodes, training_roots=len(training),
        heldout_roots=len(heldout), normalization_training_roots=statistics_roots, uniform_gamma=uniform_gamma,
        training_replica_rows=int(replicas.shape[0] * replicas.shape[1]), conflict_mass_training_roots=statistics_roots,
        total_training_pairs=len(training) * 10,
        models={FAMILY: fit_log}, counts=dict(neural_model_fits=1, optimizer_steps=STEPS),
        seconds=perf_counter() - start)
