"""Joint-oracle identity, masked data loss with one L2, and fixed-statistics isolation."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_incremental_ranking_v107 as old
from acfqp.science import controlled_predictive_query_update_v108 as m
from acfqp.science.controlled_predictive_capacity_ranking_v103 import initialize

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_query_update_v108.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before, development_work=dict(WORK),
        production_neural_model_fits=0, production_optimizer_steps=0, environment_transitions=0, model_transitions=0,
        scope='Short-step synthetic fits and analytic objectives; synthetic half lineage was not fitted here.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def track(log):
    WORK.update(neural_model_fits=1, optimizer_steps=log['new_optimizer_steps'])
    n = log['models']['UNIFORM_SHRINK']['counts']['diagnostic_candidate_predictions']
    WORK['diagnostic_candidate_predictions'] += n
    WORK['diagnostic_hidden_activations'] += n * log['hidden']


def records():
    rng = np.random.default_rng(108); rows = []
    for query, episodes in (('reward', (0, 1, 4, 6, 8)), ('risk_goal', (0, 4, 6, 8))):
        for episode in episodes:
            replicas = rng.normal(size=(4, 5)); replicas[:, 0] = 0
            rows.append(dict(query=query, episode=episode, features=rng.normal(size=(5, 121)).tolist(),
                utilities=replicas.mean(axis=0).tolist(), replica_utilities=replicas.tolist()))
    return rows


def half_payload(hidden):
    return m.CandidateModel([p + .005 for p in initialize(121, hidden)], np.linspace(-1, 1, 121),
        np.linspace(.7, 1.7, 121), 3, 'UNIFORM_SHRINK', {'reward': [0], 'risk_goal': [0]},
        1.3, optimizer_steps=7).to_payload()


@pytest.mark.parametrize('hidden', (4, 16))
def test_joint_matches_frozen_v107_warm_trajectory_exactly(monkeypatch, hidden):
    monkeypatch.setattr(m, 'STEPS', 6); monkeypatch.setattr(old, 'STEPS', 6)
    rows = records(); payload = half_payload(hidden); saved = deepcopy(payload)
    actual, log = m.fit_update(rows, 7, payload, 'JOINT'); track(log)
    expected, original = old.fit_update(rows, 7, payload, 'FROZEN_STATS_WARM'); track(original)
    assert actual.to_payload() == expected.to_payload() and payload == saved
    for key in ('initial_loss', 'final_loss', 'final_gradient_norm', 'training', 'heldout'):
        assert log['models']['UNIFORM_SHRINK'][key] == original['models']['UNIFORM_SHRINK'][key]
    assert log['data_loss_weight'] == 1 and log['active_training_roots'] == log['training_roots'] == 5
    assert log['counts']['optimizer_root_passes'] == 30 and log['counts']['optimizer_pair_passes'] == 300
    assert all(log['checks'].values())


def test_masked_loss_gradient_preserves_full_denominator_and_one_l2():
    rng = np.random.default_rng(18); x = rng.normal(size=(3, 5, 6)); y = rng.normal(size=(3, 5)); y[:, 0] = 0
    parameters = initialize(6, 4); active = np.asarray([True, False, True]); gamma = .9
    loss, gradients = m.masked_objective(parameters, x, y, active, gamma)
    WORK['direct_objective_evaluations'] += 1
    w, b, v = parameters; scores = np.tanh(x @ w + b) @ v; data = 0.
    for root in (0, 2):
        for i in range(5):
            for j in range(i + 1, 5):
                delta = y[root, i] - y[root, j]; difference = scores[root, i] - scores[root, j]
                data += (abs(delta) * np.logaddexp(0, -np.sign(delta) * difference)
                    + gamma * np.logaddexp(difference / 2, -difference / 2)) / 30
    penalty = m.L2 * sum(float(np.sum(p * p)) for p in parameters) / 1968
    assert loss == pytest.approx(data + penalty, rel=1e-13)
    for p, index in ((0, (2, 3)), (0, (0, 0)), (1, (3,)), (2, (1,))):
        value = parameters[p][index]; eps = 1e-6
        parameters[p][index] = value + eps; upper = m.masked_objective(parameters, x, y, active, gamma)[0]
        parameters[p][index] = value - eps; lower = m.masked_objective(parameters, x, y, active, gamma)[0]
        parameters[p][index] = value
        WORK['direct_objective_evaluations'] += 2
        assert gradients[p][index] == pytest.approx((upper - lower) / (2 * eps), rel=2e-5, abs=1e-7)
    other, other_gradients = m.masked_objective(parameters, x, y, ~active, gamma)
    joint, joint_gradients = m.masked_objective(parameters, x, y, np.ones(3, dtype=bool), gamma)
    WORK['direct_objective_evaluations'] += 2
    assert loss + other - penalty == pytest.approx(joint, rel=1e-13)
    for a, b, c, p in zip(gradients, other_gradients, joint_gradients, parameters):
        assert np.allclose(a + b - 2 * m.L2 * p / 1968, c, rtol=1e-12, atol=1e-14)


def test_other_query_labels_and_heldout_do_not_change_either_masked_fit(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 8)
    calls = []; original_score = m.CandidateModel.score_candidates
    def score(model, features, work=None):
        calls.append(1)
        return original_score(model, features, work)
    monkeypatch.setattr(m.CandidateModel, 'score_candidates', score)
    rows = records(); payload = half_payload(4); saved = deepcopy(payload)
    for mode, query, count in (('REWARD_ONLY', 'reward', 3), ('RISK_ONLY', 'risk_goal', 2)):
        actual, log = m.fit_update(rows, 7, payload, mode); track(log)
        changed = deepcopy(rows)
        for row in changed:
            if row['query'] != query or row['episode'] in (4, 8):
                row['features'] = (np.asarray(row['features']) * 10000).tolist()
                replicas = np.asarray(row['replica_utilities']) * 10000
                row['replica_utilities'] = replicas.tolist(); row['utilities'] = replicas.mean(axis=0).tolist()
        other, altered = m.fit_update(changed, 7, payload, mode); track(altered)
        assert actual.to_payload() == other.to_payload() and payload == saved
        assert log['optimized_queries'] == [query] and set(log['active_training_episodes']) == {query}
        assert log['data_loss_weight'] == count / 5 and log['full_loss_denominator_roots'] == 5
        assert log['active_training_roots'] == count and log['training_roots'] == 5
        assert actual.training_episodes == {'reward': [0, 1, 6], 'risk_goal': [0, 6]}
        assert log['normalization_training_roots'] == log['conflict_mass_training_roots'] == 2
        assert actual.uniform_gamma == payload['uniform_gamma']
        assert np.array_equal(actual.mean, payload['mean']) and np.array_equal(actual.scale, payload['scale'])
        assert log['counts']['optimizer_root_passes'] == 8 * count
        assert log['models']['UNIFORM_SHRINK']['counts']['optimizer_pair_passes'] == 80 * count
        assert all(log['checks'].values())
        detail = log['models']['UNIFORM_SHRINK']
        assert detail['training_by_query']['reward']['roots'] == 3 and detail['training_by_query']['risk_goal']['roots'] == 2
    assert len(calls) == 4 * 7  # Five training and two heldout scores once per fit, including per-query diagnostics.


def test_warm_parameters_lineage_and_zero_adam_first_step(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 1)
    rows = records(); payload = half_payload(16); saved = deepcopy(payload); observed = []
    original = m.masked_objective
    def masked(parameters, *args):
        value = original(parameters, *args)
        observed.append(([p.copy() for p in parameters], [g.copy() for g in value[1]]))
        return value
    monkeypatch.setattr(m, 'masked_objective', masked)
    model, log = m.fit_update(rows, 7, payload, 'REWARD_ONLY'); track(log)
    assert payload == saved and len(observed) == 3
    for p, source, gradient, final in zip(observed[0][0], payload['parameters'], observed[0][1], model.parameters):
        assert np.array_equal(p, source)
        expected = p - .01 * (.1 * gradient / (1 - .9)) / (np.sqrt(.001 * gradient ** 2 / (1 - .999)) + 1e-8)
        assert np.array_equal(final, expected)
    assert log['new_optimizer_steps'] == 1 and log['inherited_parameter_steps'] == 7 and log['parameter_lineage_steps'] == 8
    assert log['optimizer_state'] == 'reset_zero_moments' and all(log['checks'].values())
    work = Counter(); model.score_candidates(rows[0]['features'], work)
    WORK['direct_candidate_predictions'] += work['neural_candidate_predictions']
    WORK['direct_hidden_activations'] += work['neural_hidden_activations']
    assert work == dict(neural_candidate_predictions=5, neural_hidden_activations=80)
