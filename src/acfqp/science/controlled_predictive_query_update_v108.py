"""Remove one query data gradient while retaining the joint denominator and L2."""
from copy import deepcopy
from time import perf_counter
import numpy as np
from .controlled_predictive_candidate_learning_v100 import metrics
from .controlled_predictive_capacity_ranking_v103 import (
    CandidateModel, RATE, L2, L2_COEFFICIENT, L2_REFERENCE_PARAMETERS, objective as original_objective)

STEPS = 1000
FAMILY = 'UNIFORM_SHRINK'
MODES = ('REWARD_ONLY', 'RISK_ONLY')


def masked_objective(parameters, x, y, active_mask, uniform_gamma):
    """Keep each active root's original joint weight and include the full L2 once."""
    active_mask = np.asarray(active_mask, dtype=bool)
    if np.all(active_mask):
        return original_objective(parameters, x, y, FAMILY, uniform_gamma=uniform_gamma)
    weight = float(np.count_nonzero(active_mask)) / len(x)
    penalty = L2 * sum(float(np.sum(p * p)) for p in parameters) / L2_REFERENCE_PARAMETERS
    penalty_gradients = [2 * L2 * p / L2_REFERENCE_PARAMETERS for p in parameters]
    if not np.any(active_mask):
        return penalty, penalty_gradients
    loss, gradients = original_objective(parameters, x[active_mask], y[active_mask], FAMILY,
        uniform_gamma=uniform_gamma)
    return weight * loss + (1 - weight) * penalty, [weight * gradient + (1 - weight) * regularizer
        for gradient, regularizer in zip(gradients, penalty_gradients)]


def fit_update(records, checkpoint, half_payload, mode):
    """Start at half parameters; JOINT is retained only for the exact oracle test."""
    start = perf_counter()
    if mode not in MODES + ('JOINT',):
        raise ValueError(f'unknown query-gradient update {mode}')
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
    optimized_queries = ['reward', 'risk_goal'] if mode == 'JOINT' else ['reward' if mode == 'REWARD_ONLY' else 'risk_goal']
    active_mask = np.asarray([r['query'] in optimized_queries for r in training])
    active_roots = int(np.count_nonzero(active_mask))
    active_episodes = {query: deepcopy(episodes[query]) for query in optimized_queries}
    tick = perf_counter()
    parameters = [p.copy() for p in half.parameters]
    inherited_steps = half.optimizer_steps
    expected_initial = half.parameters
    checks = dict(initial_parameters_from_half_or_original=all(
        np.array_equal(actual, expected) for actual, expected in zip(parameters, expected_initial)))
    first, _ = masked_objective(parameters, x, y, active_mask, uniform_gamma)
    first_moment, second_moment = ([np.zeros_like(p) for p in parameters] for _ in range(2))
    checks['optimizer_moments_reset'] = all(np.all(moment == 0) for moment in first_moment + second_moment)
    for step in range(1, STEPS + 1):
        _, gradients = masked_objective(parameters, x, y, active_mask, uniform_gamma)
        for i, gradient in enumerate(gradients):
            first_moment[i] = .9 * first_moment[i] + .1 * gradient
            second_moment[i] = .999 * second_moment[i] + .001 * gradient ** 2
            parameters[i] -= RATE * (first_moment[i] / (1 - .9 ** step)) / (
                np.sqrt(second_moment[i] / (1 - .999 ** step)) + 1e-8)
    final, gradients = masked_objective(parameters, x, y, active_mask, uniform_gamma)
    model = CandidateModel(parameters, mean.copy(), scale.copy(), checkpoint,
        FAMILY, deepcopy(episodes), uniform_gamma, STEPS)
    checks['frozen_half_statistics'] = (np.array_equal(model.mean, half.mean)
        and np.array_equal(model.scale, half.scale) and model.uniform_gamma == half.uniform_gamma)
    checks['full_training_roster'] = model.training_episodes == episodes and model.checkpoint == checkpoint
    training_scores = np.asarray([model.score_candidates(r['features']) for r in training])
    heldout_scores = np.asarray([model.score_candidates(r['features']) for r in heldout])
    heldout_targets = np.asarray([r['utilities'] for r in heldout])
    per_query = {}
    for label, rows, scores, targets in (('training', training, training_scores, y),
            ('heldout', heldout, heldout_scores, heldout_targets)):
        per_query[label] = {}
        for query in ('reward', 'risk_goal'):
            selected = np.asarray([r['query'] == query for r in rows], dtype=bool)
            per_query[label][query] = metrics(scores[selected], targets[selected], 'PAIRWISE_RANK')
    checks['query_mask_matches_mode'] = set(active_episodes) == set(optimized_queries)
    fit_log = dict(counts=dict(neural_model_fits=1, optimizer_steps=STEPS,
        optimizer_root_passes=STEPS * active_roots, optimizer_pair_passes=10 * STEPS * active_roots,
        diagnostic_candidate_predictions=5 * (len(training) + len(heldout))), initial_loss=first,
        final_loss=final, final_gradient_norm=float(np.sqrt(sum(np.sum(g * g) for g in gradients))),
        hidden=hidden, parameter_count=sum(p.size for p in parameters), l2_coefficient=L2_COEFFICIENT,
        training=metrics(training_scores, y, 'PAIRWISE_RANK'),
        heldout=metrics(heldout_scores, heldout_targets, 'PAIRWISE_RANK'),
        training_by_query=per_query['training'], heldout_by_query=per_query['heldout'],
        seconds=perf_counter() - tick)
    return model, dict(mode=mode, family=FAMILY, hidden=hidden, parameter_count=model.parameter_count,
        optimized_queries=optimized_queries, active_training_episodes=active_episodes,
        active_training_roots=active_roots, data_loss_weight=active_roots / len(training),
        full_loss_denominator_roots=len(training), initialization='half_parameters',
        optimizer_state='reset_zero_moments', new_optimizer_steps=STEPS,
        inherited_parameter_steps=inherited_steps, parameter_lineage_steps=inherited_steps + STEPS,
        statistics_source_checkpoint=half.checkpoint, statistics_training_episodes=deepcopy(half.training_episodes), checks=checks,
        l2_coefficient=L2_COEFFICIENT, l2_reference_parameters=L2_REFERENCE_PARAMETERS,
        checkpoint=checkpoint, training_episodes=episodes, training_roots=len(training),
        heldout_roots=len(heldout), normalization_training_roots=statistics_roots, uniform_gamma=uniform_gamma,
        training_replica_rows=int(replicas.shape[0] * replicas.shape[1]), conflict_mass_training_roots=statistics_roots,
        total_training_pairs=len(training) * 10,
        models={FAMILY: fit_log}, counts=dict(neural_model_fits=1, optimizer_steps=STEPS,
            optimizer_root_passes=STEPS * active_roots, optimizer_pair_passes=10 * STEPS * active_roots),
        seconds=perf_counter() - start)
