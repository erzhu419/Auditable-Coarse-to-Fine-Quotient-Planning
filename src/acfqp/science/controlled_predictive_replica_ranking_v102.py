"""Matched root ranking with observed replica conflict and uniform shrinkage."""
from copy import deepcopy
from time import perf_counter
import numpy as np
from .controlled_predictive_candidate_learning_v100 import (
    HIDDEN, RATE, L2, SEED, PAIRS, initialize, metrics)

STEPS = 1000
FAMILIES = ('MEAN_SIGN', 'REPLICA', 'UNIFORM_SHRINK')


def pair_gamma(utilities, replica_utilities):
    """Conflict mass for each root and pair; every root keeps ten pair slots."""
    y = np.asarray(utilities, dtype=float)
    replicas = np.asarray(replica_utilities, dtype=float)
    return np.stack([np.maximum(0., np.mean(abs(replicas[:, :, i] - replicas[:, :, j]), axis=1)
        - abs(y[:, i] - y[:, j])) for i, j in PAIRS], axis=1)


def objective(parameters, x, y, family, *, replica_utilities=None, uniform_gamma=None):
    """Return mean root-pair loss and gradients, including the matched L2 term."""
    if family not in FAMILIES:
        raise ValueError(f'unknown replica ranking objective {family}')
    gamma = None
    if family == 'REPLICA':
        gamma = pair_gamma(y, replica_utilities)
    elif family == 'UNIFORM_SHRINK':
        if uniform_gamma is None:
            raise ValueError('uniform shrinkage requires the training-only mean conflict mass')
        gamma = np.full((len(x), len(PAIRS)), uniform_gamma)
    w, b, v = parameters
    hidden = np.tanh(x @ w + b)
    scores = hidden @ v
    derivative = np.zeros_like(scores)
    loss = 0.
    size_pairs = len(x) * len(PAIRS)
    for k, (i, j) in enumerate(PAIRS):
        delta = y[:, i] - y[:, j]
        sign, mass = np.sign(delta), np.abs(delta)
        difference = scores[:, i] - scores[:, j]
        margin = sign * difference
        loss += float(np.sum(mass * np.logaddexp(0., -margin))) / size_pairs
        g = -mass * sign * np.exp(-np.logaddexp(0., margin)) / size_pairs
        if gamma is not None:
            loss += float(np.sum(gamma[:, k] * np.logaddexp(difference / 2., -difference / 2.))) / size_pairs
            g += gamma[:, k] * .5 * np.tanh(difference / 2.) / size_pairs
        derivative[:, i] += g
        derivative[:, j] -= g
    hidden_gradient = derivative[:, :, None] * v * (1 - hidden ** 2)
    gradients = [np.einsum('nkd,nkh->dh', x, hidden_gradient), hidden_gradient.sum(axis=(0, 1)),
                 np.einsum('nkh,nk->h', hidden, derivative)]
    size = sum(p.size for p in parameters)
    loss += L2 * sum(float(np.sum(p * p)) for p in parameters) / size
    gradients = [g + 2 * L2 * p / size for g, p in zip(gradients, parameters)]
    return loss, gradients


class CandidateModel:
    def __init__(self, parameters, mean, scale, checkpoint, family, episodes, uniform_gamma):
        self.parameters, self.mean, self.scale = parameters, mean, scale
        self.checkpoint, self.family, self.training_episodes = checkpoint, family, episodes
        self.uniform_gamma = uniform_gamma

    def score_candidates(self, features, work=None):
        x = (np.asarray(features, dtype=float) - self.mean) / self.scale
        w, b, v = self.parameters
        scores = np.tanh(x @ w + b) @ v
        if work is not None:
            work['neural_candidate_predictions'] += len(x)
            work['neural_hidden_activations'] += len(x) * HIDDEN
        return (scores - scores[..., :1]).tolist()

    def to_payload(self):
        return dict(schema='acfqp.replica_ranking_model.v102', checkpoint=self.checkpoint,
            family=self.family, training_episodes=deepcopy(self.training_episodes),
            parameters=[p.tolist() for p in self.parameters], mean=self.mean.tolist(), scale=self.scale.tolist(),
            hidden=HIDDEN, optimizer_steps=STEPS, learning_rate=RATE, l2=L2, initialization_seed=SEED,
            uniform_gamma=self.uniform_gamma, score_semantics='rank_score')

    @classmethod
    def from_payload(cls, row):
        return cls([np.asarray(p) for p in row['parameters']], np.asarray(row['mean']),
            np.asarray(row['scale']), row['checkpoint'], row['family'], deepcopy(row['training_episodes']),
            row['uniform_gamma'])


def fit_models(records, checkpoint):
    start = perf_counter()
    training = [r for r in records if r['episode'] < checkpoint and r['episode'] % 5 != 4]
    heldout = [r for r in records if r['episode'] < checkpoint and r['episode'] % 5 == 4]
    if not training:
        raise ValueError('replica ranking requires complete training roots')
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
    models, logs = {}, {}
    for family in FAMILIES:
        tick = perf_counter()
        parameters = initialize(x.shape[-1])
        args = dict(replica_utilities=replicas, uniform_gamma=uniform_gamma)
        first, _ = objective(parameters, x, y, family, **args)
        first_moment, second_moment = ([np.zeros_like(p) for p in parameters] for _ in range(2))
        for step in range(1, STEPS + 1):
            _, gradients = objective(parameters, x, y, family, **args)
            for i, gradient in enumerate(gradients):
                first_moment[i] = .9 * first_moment[i] + .1 * gradient
                second_moment[i] = .999 * second_moment[i] + .001 * gradient ** 2
                parameters[i] -= RATE * (first_moment[i] / (1 - .9 ** step)) / (
                    np.sqrt(second_moment[i] / (1 - .999 ** step)) + 1e-8)
        final, gradients = objective(parameters, x, y, family, **args)
        model = models[family] = CandidateModel(parameters, mean.copy(), scale.copy(), checkpoint,
            family, deepcopy(episodes), uniform_gamma)
        training_scores = np.asarray([model.score_candidates(r['features']) for r in training])
        heldout_scores = np.asarray([model.score_candidates(r['features']) for r in heldout])
        logs[family] = dict(counts=dict(neural_model_fits=1, optimizer_steps=STEPS,
            diagnostic_candidate_predictions=5 * (len(training) + len(heldout))), initial_loss=first,
            final_loss=final, final_gradient_norm=float(np.sqrt(sum(np.sum(g * g) for g in gradients))),
            parameter_count=sum(p.size for p in parameters), training=metrics(training_scores, y, 'PAIRWISE_RANK'),
            heldout=metrics(heldout_scores, np.asarray([r['utilities'] for r in heldout]), 'PAIRWISE_RANK'),
            seconds=perf_counter() - tick)
    return models, dict(checkpoint=checkpoint, training_episodes=episodes, training_roots=len(training),
        heldout_roots=len(heldout), normalization_training_roots=len(training),
        uniform_gamma=uniform_gamma, training_replica_rows=int(replicas.shape[0] * replicas.shape[1]),
        conflict_mass_training_roots=len(training),
        conflict_pairs=int(np.count_nonzero(gamma > 0)), total_training_pairs=int(gamma.size), models=logs,
        counts=dict(neural_model_fits=3, optimizer_steps=3 * STEPS), seconds=perf_counter() - start)
