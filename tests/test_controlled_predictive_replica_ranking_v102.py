"""Validate conflict decomposition, exact baseline, gradients and training isolation."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_candidate_learning_v100 as old
from acfqp.science import controlled_predictive_replica_ranking_v102 as m

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_replica_ranking_v102.checks.json'
    row = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    row['attempts'].append(dict(failures=request.session.testsfailed - before, work=dict(WORK),
        new_environment_transitions=0, new_synthetic_transitions=0,
        scope='Synthetic gradient, replica identity and small isolated neural fits.'))
    path.write_text(json.dumps(row, indent=2) + '\n')


def inputs():
    rng = np.random.default_rng(102)
    x = rng.normal(size=(3, 5, 4))
    replicas = rng.normal(size=(3, 4, 5)); replicas[:, :, 0] = 0
    return x, replicas.mean(axis=1), replicas


@pytest.mark.parametrize('family', m.FAMILIES)
def test_all_objective_gradients(family):
    x, y, replicas = inputs(); parameters = m.initialize(4)
    args = dict(replica_utilities=replicas, uniform_gamma=float(m.pair_gamma(y, replicas).mean()))
    _, gradients = m.objective(parameters, x, y, family, **args)
    WORK['objective_evaluations'] += 1
    for p, index in [(0, (2, 3)), (0, (0, 0)), (1, (3,)), (2, (4,))]:
        original = parameters[p][index]; eps = 1e-6
        parameters[p][index] = original + eps
        upper = m.objective(parameters, x, y, family, **args)[0]
        parameters[p][index] = original - eps
        lower = m.objective(parameters, x, y, family, **args)[0]
        parameters[p][index] = original
        WORK['objective_evaluations'] += 2
        assert gradients[p][index] == pytest.approx((upper - lower) / (2 * eps), rel=2e-5, abs=1e-7)


def test_mean_sign_is_exact_v100_rank_objective():
    x, y, _ = inputs(); parameters = m.initialize(4)
    actual, gradients = m.objective(parameters, x, y, 'MEAN_SIGN')
    expected, old_gradients = old.objective(parameters, x, y, 'PAIRWISE_RANK')
    WORK['objective_evaluations'] += 2
    assert actual == expected
    assert all(np.array_equal(a, b) for a, b in zip(gradients, old_gradients))


def test_replica_loss_equals_raw_per_replica_weighted_logistic():
    x, y, replicas = inputs(); parameters = m.initialize(4)
    actual, _ = m.objective(parameters, x, y, 'REPLICA', replica_utilities=replicas)
    w, b, v = parameters; scores = np.tanh(x @ w + b) @ v
    raw = 0.
    for i, j in m.PAIRS:
        delta = replicas[:, :, i] - replicas[:, :, j]
        raw += np.mean(abs(delta) * np.logaddexp(0., -np.sign(delta) *
            (scores[:, i] - scores[:, j])[:, None])) / len(m.PAIRS)
    raw += m.L2 * sum(np.sum(p * p) for p in parameters) / sum(p.size for p in parameters)
    WORK['objective_evaluations'] += 1
    assert actual == pytest.approx(raw, rel=1e-13, abs=1e-13)


def test_same_sign_replicas_equal_mean_sign_and_zero_uniform():
    x, _, _ = inputs(); y = np.tile([0., 2., -2., 4., -4.], (3, 1))
    replicas = np.stack((y * .5, y * 1.5), axis=1); parameters = m.initialize(4)
    assert np.array_equal(m.pair_gamma(y, replicas), np.zeros((3, 10)))
    loss, gradients = m.objective(parameters, x, y, 'MEAN_SIGN')
    for family in ('REPLICA', 'UNIFORM_SHRINK'):
        result, other = m.objective(parameters, x, y, family, replica_utilities=replicas, uniform_gamma=0.)
        assert result == loss
        assert all(np.array_equal(a, b) for a, b in zip(gradients, other))
    WORK['objective_evaluations'] += 3


def test_zero_mean_conflict_shrinks_scores_but_true_ties_do_not(monkeypatch):
    monkeypatch.setattr(m, 'L2', 0.)
    x = np.arange(5, dtype=float).reshape(1, 5, 1)
    y = np.zeros((1, 5)); samples = np.stack((x[:, :, 0], -x[:, :, 0]), axis=1)
    parameters = [np.ones((1, 16)) * .1, np.zeros(16), np.ones(16)]
    loss, gradients = m.objective(parameters, x, y, 'REPLICA', replica_utilities=samples)
    tie_loss, tie_gradients = m.objective(parameters, x, y, 'REPLICA', replica_utilities=np.zeros_like(samples))
    zero = [parameters[0], parameters[1], np.zeros(16)]
    zero_loss, zero_gradients = m.objective(zero, x, y, 'REPLICA', replica_utilities=samples)
    WORK['objective_evaluations'] += 3
    assert loss > zero_loss > 0 and np.all(gradients[2] > 0)
    assert all(np.all(g == 0) for g in zero_gradients)
    assert tie_loss == 0 and all(np.all(g == 0) for g in tie_gradients)


def records():
    rng = np.random.default_rng(31); rows = []
    for query in ('reward', 'risk_goal'):
        for episode in (0, 1, 4, 6):
            samples = rng.normal(size=(4, 5)); samples[:, 0] = 0
            rows.append(dict(query=query, episode=episode, features=rng.normal(size=(5, 4)).tolist(),
                utilities=samples.mean(axis=0).tolist(), replica_utilities=samples.tolist()))
    return rows


def test_heldout_future_cannot_change_gamma_normalization_or_model(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 12)
    rows = records(); models, log = m.fit_models(rows, 5)
    changed = deepcopy(rows)
    for row in changed:
        if row['episode'] in (4, 6):
            row['features'] = (np.asarray(row['features']) * 1e5).tolist()
            samples = np.asarray(row['replica_utilities']) * 1e4
            row['replica_utilities'] = samples.tolist(); row['utilities'] = samples.mean(axis=0).tolist()
    other, alternate_log = m.fit_models(changed, 5)
    WORK.update(neural_model_fits=6, optimizer_steps=72)
    assert log['uniform_gamma'] == alternate_log['uniform_gamma']
    assert log['normalization_training_roots'] == log['conflict_mass_training_roots'] == 4
    assert log['training_replica_rows'] == 16 and log['total_training_pairs'] == 40
    assert log['training_episodes'] == {'reward': [0, 1], 'risk_goal': [0, 1]}
    train = [row for row in rows if row['episode'] in (0, 1)]
    expected = m.pair_gamma([row['utilities'] for row in train], [row['replica_utilities'] for row in train])
    assert log['uniform_gamma'] == expected.mean()
    for family in m.FAMILIES:
        assert models[family].to_payload() == other[family].to_payload()
        assert 'utility_mse' not in log['models'][family]['heldout']


def test_age_payloads_keep_own_parameters_gamma_and_counter_semantics(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 8)
    rows = records(); half, half_log = m.fit_models(rows, 1)
    saved_half = {family: model.to_payload() for family, model in half.items()}
    full, full_log = m.fit_models(rows, 7)
    WORK.update(neural_model_fits=6, optimizer_steps=48)
    assert half_log['training_roots'] == 2 and full_log['training_roots'] == 6
    for family in m.FAMILIES:
        assert half[family].to_payload() == saved_half[family]
        assert half[family].checkpoint == 1 and full[family].checkpoint == 7
        assert half[family].training_episodes != full[family].training_episodes
        restored = m.CandidateModel.from_payload(saved_half[family]); work = Counter()
        scores = restored.score_candidates(rows[0]['features'], work)
        assert scores == half[family].score_candidates(rows[0]['features']) and scores[0] == 0
        assert work == dict(neural_candidate_predictions=5, neural_hidden_activations=80)
        assert saved_half[family]['score_semantics'] == 'rank_score'
