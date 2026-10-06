"""Continue the pooled half model on unchanged half experience."""
from copy import deepcopy
from time import perf_counter
import numpy as np
from .controlled_predictive_candidate_learning_v100 import metrics
from .controlled_predictive_capacity_ranking_v103 import (
    CandidateModel, RATE, L2_COEFFICIENT, L2_REFERENCE_PARAMETERS,
    objective)

STEPS = 1000
FAMILY = 'UNIFORM_SHRINK'
STAGE = 'HALF_CONTINUED'
CHECKPOINT = 256000
QUERIES = ('reward', 'risk_goal')


def _roster(records):
    return [[r['source_life'], r['query'], r['episode']] for r in records]


def _episodes(records):
    return {query: sorted([[r['source_life'], r['episode']] for r in records
        if r['query'] == query]) for query in QUERIES}


def fit_continuation(records, hidden, source_lives, half_payload):
    """Retain half data, parameters and statistics, with newly reset Adam moments."""
    start = perf_counter()
    if hidden not in (4, 16):
        raise ValueError('half continuation requires width 4 or 16')
    source_lives = list(source_lives)
    if (not source_lives or len(source_lives) != len(set(source_lives))
            or {r['source_life'] for r in records} != set(source_lives)):
        raise ValueError('records must contain exactly the declared source lives')
    roster = _roster(records)
    if len({tuple(key) for key in roster}) != len(roster):
        raise ValueError('pooled root identity (source_life, query, episode) must be unique')
    if any(r['query'] not in QUERIES or type(r['is_half']) is not bool for r in records):
        raise ValueError('records require supported queries and an actual half-batch membership')
    selected = [r for r in records if r['is_half']]
    training = [r for r in selected if r['episode'] % 5 != 4]
    heldout = [r for r in selected if r['episode'] % 5 == 4]
    statistics = [r for r in records if r['is_half'] and r['episode'] % 5 != 4]
    if not training or not statistics:
        raise ValueError('pooled ranking requires complete half and stage training roots')
    x = np.asarray([r['features'] for r in training], dtype=float)
    y = np.asarray([r['utilities'] for r in training], dtype=float)
    replicas = np.asarray([r['replica_utilities'] for r in training], dtype=float)
    if (x.shape != (len(training), 5, 121) or y.shape != (len(training), 5)
            or replicas.shape != (len(training), 4, 5) or not np.all(replicas[:, :, 0] == 0)
            or not np.allclose(replicas.mean(axis=1), y, rtol=1e-10, atol=1e-12)):
        raise ValueError('five-candidate roots require four paired replicas averaging to targets')
    episodes, statistics_episodes = _episodes(training), _episodes(statistics)
    half = CandidateModel.from_payload(half_payload)
    if (half.family != FAMILY or half.hidden != hidden or half.checkpoint != CHECKPOINT
            or half.training_episodes != statistics_episodes):
        raise ValueError('HALF payload must match the source pool, width and actual half training roster')
    mean, scale, uniform_gamma = half.mean.copy(), half.scale.copy(), half.uniform_gamma
    parameters = [p.copy() for p in half.parameters]
    inherited_steps = half.optimizer_steps
    expected_initial = half.parameters
    checks = dict(source_pool_exact=True, unique_cross_history_roots=True,
        actual_half_membership=True,
        initial_parameters_from_half_or_original=all(np.array_equal(a, b)
            for a, b in zip(parameters, expected_initial)))
    x = (x - mean) / scale
    tick = perf_counter()
    args = dict(replica_utilities=replicas, uniform_gamma=uniform_gamma)
    first, _ = objective(parameters, x, y, FAMILY, **args)
    first_moment, second_moment = ([np.zeros_like(p) for p in parameters] for _ in range(2))
    checks['optimizer_moments_reset'] = all(np.all(m == 0) for m in first_moment + second_moment)
    for step in range(1, STEPS + 1):
        _, gradients = objective(parameters, x, y, FAMILY, **args)
        for i, gradient in enumerate(gradients):
            first_moment[i] = .9 * first_moment[i] + .1 * gradient
            second_moment[i] = .999 * second_moment[i] + .001 * gradient ** 2
            parameters[i] -= RATE * (first_moment[i] / (1 - .9 ** step)) / (
                np.sqrt(second_moment[i] / (1 - .999 ** step)) + 1e-8)
    final, gradients = objective(parameters, x, y, FAMILY, **args)
    model = CandidateModel(parameters, mean.copy(), scale.copy(), CHECKPOINT,
        FAMILY, deepcopy(episodes), uniform_gamma, STEPS)
    checks['stage_training_roster'] = model.training_episodes == episodes
    checks['half_statistics_training_only'] = not any(r['episode'] % 5 == 4 for r in statistics)
    checks['frozen_half_statistics'] = (np.array_equal(model.mean, half.mean)
        and np.array_equal(model.scale, half.scale) and model.uniform_gamma == half.uniform_gamma)
    checks['unchanged_half_training_roster'] = model.training_episodes == half.training_episodes
    training_scores = np.asarray([model.score_candidates(r['features']) for r in training])
    heldout_scores = np.asarray([model.score_candidates(r['features']) for r in heldout])
    heldout_targets = np.asarray([r['utilities'] for r in heldout])
    per_query = {}
    for label, rows, scores, targets in (('training', training, training_scores, y),
            ('heldout', heldout, heldout_scores, heldout_targets)):
        per_query[label] = {}
        for query in QUERIES:
            mask = np.asarray([r['query'] == query for r in rows], dtype=bool)
            per_query[label][query] = metrics(scores[mask], targets[mask], 'PAIRWISE_RANK')
    counts = dict(neural_model_fits=1, optimizer_steps=STEPS,
        optimizer_root_passes=STEPS * len(training), optimizer_pair_passes=10 * STEPS * len(training),
        optimizer_parameter_updates=STEPS * model.parameter_count, diagnostic_candidate_predictions=5 * (len(training) + len(heldout)))
    fit_log = dict(counts=counts.copy(), initial_loss=first, final_loss=final,
        final_gradient_norm=float(np.sqrt(sum(np.sum(g * g) for g in gradients))),
        hidden=hidden, parameter_count=model.parameter_count, l2_coefficient=L2_COEFFICIENT,
        training=metrics(training_scores, y, 'PAIRWISE_RANK'),
        heldout=metrics(heldout_scores, heldout_targets, 'PAIRWISE_RANK'),
        training_by_query=per_query['training'], heldout_by_query=per_query['heldout'],
        seconds=perf_counter() - tick)
    return model, dict(source_lives=source_lives, stage=STAGE, family=FAMILY, hidden=hidden,
        checkpoint=CHECKPOINT, parameter_count=model.parameter_count,
        initialization='half_parameters',
        optimizer_state='reset_zero_moments', new_optimizer_steps=STEPS,
        inherited_parameter_steps=inherited_steps, parameter_lineage_steps=inherited_steps + STEPS,
        training_roster=_roster(training), heldout_roster=_roster(heldout), statistics_roster=_roster(statistics),
        training_episodes=episodes, statistics_training_episodes=statistics_episodes,
        statistics_source_checkpoint=CHECKPOINT, training_roots=len(training), heldout_roots=len(heldout),
        normalization_training_roots=len(statistics), uniform_gamma=uniform_gamma,
        training_replica_rows=int(replicas.shape[0] * replicas.shape[1]),
        conflict_mass_training_roots=len(statistics), total_training_pairs=10 * len(training),
        l2_coefficient=L2_COEFFICIENT, l2_reference_parameters=L2_REFERENCE_PARAMETERS,
        models={FAMILY: fit_log}, counts=counts, checks=checks, seconds=perf_counter() - start)
