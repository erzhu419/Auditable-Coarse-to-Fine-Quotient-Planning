"""Matched scalar utility and pairwise ranking objectives on whole root groups."""
from copy import deepcopy
from time import perf_counter
import numpy as np

HIDDEN, STEPS, RATE, L2, SEED = 16, 1000, .01, .001, 10001
FAMILIES = ('UTILITY_MSE', 'PAIRWISE_RANK')
PAIRS = tuple((i, j) for i in range(5) for j in range(i + 1, 5))


def initialize(dim):
    rng = np.random.default_rng(SEED)
    return [rng.normal(0, np.sqrt(2 / (dim + HIDDEN)), (dim, HIDDEN)),
            np.zeros(HIDDEN), rng.normal(0, np.sqrt(2 / (HIDDEN + 1)), HIDDEN)]


def objective(parameters, x, y, family):
    """Return the objective and exact gradients; all ten pairs retain their slots."""
    w, b, v = parameters
    hidden = np.tanh(x @ w + b)
    scores = hidden @ v
    derivative = np.zeros_like(scores)
    if family == 'UTILITY_MSE':
        error = scores - scores[:, :1] - y
        loss = float(np.mean(error ** 2))
        derivative = 2 * error / error.size
        derivative[:, 0] -= derivative.sum(axis=1)
    elif family == 'PAIRWISE_RANK':
        loss = 0.
        for i, j in PAIRS:
            delta = y[:, i] - y[:, j]
            sign, mass = np.sign(delta), np.abs(delta)
            margin = sign * (scores[:, i] - scores[:, j])
            loss += float(np.sum(mass * np.logaddexp(0., -margin))) / (len(x) * len(PAIRS))
            g = -mass * sign * np.exp(-np.logaddexp(0., margin)) / (len(x) * len(PAIRS))
            derivative[:, i] += g
            derivative[:, j] -= g
    else:
        raise ValueError(f'unknown candidate objective {family}')
    hidden_gradient = derivative[:, :, None] * v * (1 - hidden ** 2)
    gradients = [np.einsum('nkd,nkh->dh', x, hidden_gradient),
                 hidden_gradient.sum(axis=(0, 1)), np.einsum('nkh,nk->h', hidden, derivative)]
    size = sum(p.size for p in parameters)
    loss += L2 * sum(float(np.sum(p * p)) for p in parameters) / size
    gradients = [g + 2 * L2 * p / size for g, p in zip(gradients, parameters)]
    return loss, gradients


class CandidateModel:
    def __init__(self, parameters, mean, scale, checkpoint, family, episodes):
        self.parameters, self.mean, self.scale = parameters, mean, scale
        self.checkpoint, self.family, self.training_episodes = checkpoint, family, episodes

    def score_candidates(self, features, work=None):
        x = (np.asarray(features, dtype=float) - self.mean) / self.scale
        w, b, v = self.parameters
        scores = np.tanh(x @ w + b) @ v
        if work is not None:
            work['neural_candidate_predictions'] += len(x)
            work['neural_hidden_activations'] += len(x) * HIDDEN
        return (scores - scores[..., :1]).tolist()

    def to_payload(self):
        return dict(schema='acfqp.candidate_model.v100', checkpoint=self.checkpoint,
            family=self.family, training_episodes=deepcopy(self.training_episodes),
            parameters=[p.tolist() for p in self.parameters], mean=self.mean.tolist(), scale=self.scale.tolist(),
            hidden=HIDDEN, optimizer_steps=STEPS, learning_rate=RATE, l2=L2, initialization_seed=SEED,
            score_semantics='rank_score' if self.family == 'PAIRWISE_RANK' else 'utility_estimate')

    @classmethod
    def from_payload(cls, row):
        return cls([np.asarray(p) for p in row['parameters']], np.asarray(row['mean']),
                   np.asarray(row['scale']), row['checkpoint'], row['family'], deepcopy(row['training_episodes']))


def metrics(scores, targets, family):
    if not len(scores):
        return dict(roots=0, pairwise_weighted_error=None, selected_empirical_regret=None)
    error = mass = 0.
    for i, j in PAIRS:
        delta = targets[:, i] - targets[:, j]
        margin = np.sign(delta) * (scores[:, i] - scores[:, j])
        weights = abs(delta)
        mass += float(weights.sum())
        error += float(np.sum(weights * ((margin < 0) + .5 * (margin == 0))))
    chosen = np.argmax(scores, axis=1)
    result = dict(roots=len(scores), pairwise_weighted_error=error / mass if mass else 0.,
        selected_empirical_regret=float(np.mean(targets.max(axis=1) - targets[np.arange(len(scores)), chosen])))
    if family == 'UTILITY_MSE':
        result['utility_mse'] = float(np.mean((scores - targets) ** 2))
    return result


def fit_models(records, checkpoint):
    start = perf_counter()
    training = [r for r in records if r['episode'] < checkpoint and r['episode'] % 5 != 4]
    heldout = [r for r in records if r['episode'] < checkpoint and r['episode'] % 5 == 4]
    if not training:
        raise ValueError('candidate learning requires complete training roots')
    x = np.asarray([r['features'] for r in training], dtype=float)
    y = np.asarray([r['utilities'] for r in training], dtype=float)
    if x.ndim != 3 or x.shape[1] != 5 or y.shape != x.shape[:2] or not np.all(y[:, 0] == 0):
        raise ValueError('training groups require five candidates with H2 first and zero reference utility')
    mean, scale = x.mean(axis=(0, 1)), x.std(axis=(0, 1))
    scale[scale == 0] = 1.
    x = (x - mean) / scale
    episodes = {q: sorted({r['episode'] for r in training if r['query'] == q}) for q in ('reward', 'risk_goal')}
    models, logs = {}, {}
    for family in FAMILIES:
        tick = perf_counter()
        parameters = initialize(x.shape[-1])
        first, _ = objective(parameters, x, y, family)
        first_moment, second_moment = ([np.zeros_like(p) for p in parameters] for _ in range(2))
        for step in range(1, STEPS + 1):
            _, gradients = objective(parameters, x, y, family)
            for i, gradient in enumerate(gradients):
                first_moment[i] = .9 * first_moment[i] + .1 * gradient
                second_moment[i] = .999 * second_moment[i] + .001 * gradient ** 2
                parameters[i] -= RATE * (first_moment[i] / (1 - .9 ** step)) / (
                    np.sqrt(second_moment[i] / (1 - .999 ** step)) + 1e-8)
        final, gradients = objective(parameters, x, y, family)
        model = models[family] = CandidateModel(parameters, mean.copy(), scale.copy(), checkpoint, family, deepcopy(episodes))
        training_scores = np.asarray([model.score_candidates(r['features']) for r in training])
        heldout_scores = np.asarray([model.score_candidates(r['features']) for r in heldout])
        logs[family] = dict(counts=dict(neural_model_fits=1, optimizer_steps=STEPS,
            diagnostic_candidate_predictions=5 * (len(training) + len(heldout))), initial_loss=first,
            final_loss=final, final_gradient_norm=float(np.sqrt(sum(np.sum(g * g) for g in gradients))),
            parameter_count=sum(p.size for p in parameters), training=metrics(training_scores, y, family),
            heldout=metrics(heldout_scores, np.asarray([r['utilities'] for r in heldout]), family),
            seconds=perf_counter() - tick)
    return models, dict(checkpoint=checkpoint, training_episodes=episodes, training_roots=len(training),
        heldout_roots=len(heldout), normalization_training_roots=len(training), models=logs,
        counts=dict(neural_model_fits=2, optimizer_steps=2 * STEPS), seconds=perf_counter() - start)
