"""Check fixed-penalty capacity comparison and retained query interactions."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_replica_ranking_v102 as old
from acfqp.science import controlled_predictive_capacity_ranking_v103 as m

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_capacity_ranking_v103.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failures=request.session.testsfailed - before, work=dict(WORK),
        new_environment_transitions=0, new_synthetic_transitions=0,
        scope='Synthetic gradients, frozen-wide identity, small narrow fits and query interaction.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def inputs(dim=6):
    rng = np.random.default_rng(103)
    x = rng.normal(size=(3, 5, dim))
    replicas = rng.normal(size=(3, 4, 5)); replicas[:, :, 0] = 0
    y = replicas.mean(axis=1)
    return x, y, dict(replica_utilities=replicas, uniform_gamma=float(m.pair_gamma(y, replicas).mean()))


@pytest.mark.parametrize('hidden', (4, 16))
@pytest.mark.parametrize('family', m.FAMILIES)
def test_both_widths_objective_gradient(hidden, family):
    x, y, args = inputs(); parameters = m.initialize(6, hidden)
    _, gradients = m.objective(parameters, x, y, family, **args)
    WORK['objective_evaluations'] += 1
    for p, index in [(0, (2, 3)), (0, (0, 0)), (1, (3,)), (2, (1,))]:
        original = parameters[p][index]; eps = 1e-6
        parameters[p][index] = original + eps
        upper = m.objective(parameters, x, y, family, **args)[0]
        parameters[p][index] = original - eps
        lower = m.objective(parameters, x, y, family, **args)[0]
        parameters[p][index] = original
        WORK['objective_evaluations'] += 2
        assert gradients[p][index] == pytest.approx((upper - lower) / (2 * eps), rel=2e-5, abs=1e-7)


@pytest.mark.parametrize('family', m.FAMILIES)
def test_wide_initialization_loss_and_gradient_are_exact_v102(family):
    x, y, args = inputs(121)
    parameters = m.initialize(121, 16); previous = old.initialize(121)
    assert all(np.array_equal(a, b) for a, b in zip(parameters, previous))
    actual, gradients = m.objective(parameters, x, y, family, **args)
    expected, old_gradients = old.objective(previous, x, y, family, **args)
    WORK['objective_evaluations'] += 2
    assert actual == expected
    assert all(np.array_equal(a, b) for a, b in zip(gradients, old_gradients))


def test_narrow_penalty_keeps_frozen_per_parameter_coefficient():
    parameters = m.initialize(121, 4); x = np.zeros((1, 5, 121)); y = np.zeros((1, 5))
    loss, gradients = m.objective(parameters, x, y, 'MEAN_SIGN')
    WORK['objective_evaluations'] += 1
    assert sum(p.size for p in parameters) == 492
    assert loss == m.L2 * sum(float(np.sum(p * p)) for p in parameters) / 1968
    assert all(np.array_equal(g, 2 * m.L2 * p / 1968) for g, p in zip(gradients, parameters))
    assert loss != m.L2 * sum(float(np.sum(p * p)) for p in parameters) / 492


def records():
    rng = np.random.default_rng(32); result = []
    for query in ('reward', 'risk_goal'):
        for episode in (0, 1, 4, 6):
            samples = rng.normal(size=(4, 5)); samples[:, 0] = 0
            result.append(dict(query=query, episode=episode, features=rng.normal(size=(5, 121)).tolist(),
                utilities=samples.mean(axis=0).tolist(), replica_utilities=samples.tolist()))
    return result


def test_heldout_future_excluded_from_narrow_normalization_and_conflict(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 12)
    rows = records(); models, log = m.fit_models(rows, 5)
    changed = deepcopy(rows)
    for row in changed:
        if row['episode'] in (4, 6):
            row['features'] = (np.asarray(row['features']) * 10000).tolist()
            samples = np.asarray(row['replica_utilities']) * 10000
            row['replica_utilities'] = samples.tolist(); row['utilities'] = samples.mean(axis=0).tolist()
    other, alternate = m.fit_models(changed, 5)
    WORK.update(neural_model_fits=6, optimizer_steps=72)
    assert log['hidden'] == 4 and log['parameter_count'] == 492
    assert log['l2_coefficient'] == .001 / 1968
    assert log['normalization_training_roots'] == log['conflict_mass_training_roots'] == 4
    assert log['uniform_gamma'] == alternate['uniform_gamma']
    train = [row for row in rows if row['episode'] in (0, 1)]
    expected = old.pair_gamma([row['utilities'] for row in train], [row['replica_utilities'] for row in train])
    assert log['uniform_gamma'] == float(expected.mean())
    for family in m.FAMILIES:
        assert models[family].to_payload() == other[family].to_payload()
        assert models[family].hidden == log['models'][family]['hidden'] == 4
        assert 'utility_mse' not in log['models'][family]['heldout']


def test_new_and_frozen_payloads_preserve_actual_width_and_score_counts():
    x, _, _ = inputs(121); features = x[0]
    for hidden in (4, 16):
        parameters = m.initialize(121, hidden)
        if hidden == 16:
            previous = old.CandidateModel(parameters, np.zeros(121), np.ones(121), 14,
                'REPLICA', {'reward': [0, 1], 'risk_goal': [0, 1]}, .7)
            restored = m.CandidateModel.from_payload(previous.to_payload())
            assert restored.score_candidates(features) == previous.score_candidates(features)
        else:
            restored = m.CandidateModel(parameters, np.zeros(121), np.ones(121), 14,
                'REPLICA', {'reward': [0, 1], 'risk_goal': [0, 1]}, .7, 12)
        payload = restored.to_payload(); again = m.CandidateModel.from_payload(payload); work = Counter()
        assert again.to_payload() == payload
        assert again.score_candidates(features, work) == restored.score_candidates(features)
        assert work == dict(neural_candidate_predictions=5, neural_hidden_activations=5 * hidden)
        assert payload['hidden'] == hidden and payload['parameter_count'] == (121 + 2) * hidden
        assert payload['l2_coefficient'] == .001 / 1968
        assert payload['optimizer_steps'] == (1000 if hidden == 16 else 12)


def test_narrow_head_keeps_shared_query_candidate_interaction():
    # Direct reward is candidate-dependent, while the failure coefficient is shared within a root.
    x = np.zeros((5, 121)); x[:, 113] = np.arange(5)
    risk = x.copy(); risk[:, 119] = -4
    w = np.zeros((121, 4)); w[119, 0] = -.5; w[113, :2] = 1
    model = m.CandidateModel([w, np.zeros(4), np.array([1., -.5, 0., 0.])],
        np.zeros(121), np.ones(121), 14, 'REPLICA', {}, .7)
    assert np.argmax(model.score_candidates(x)) == 4
    assert np.argmax(model.score_candidates(risk)) == 0
    # A scalar linear head on the same inputs cancels the shared query coefficient.
    linear = np.arange(121, dtype=float)
    assert np.array_equal(x @ linear - (x @ linear)[0], risk @ linear - (risk @ linear)[0])
