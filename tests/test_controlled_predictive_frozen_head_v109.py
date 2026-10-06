"""Freeze representation exactly while retaining joint data loss and complete L2."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_incremental_ranking_v107 as old
from acfqp.science import controlled_predictive_frozen_head_v109 as m
from acfqp.science.controlled_predictive_capacity_ranking_v103 import initialize

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_frozen_head_v109.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before, development_work=dict(WORK),
        production_neural_model_fits=0, production_optimizer_steps=0, environment_transitions=0, model_transitions=0,
        scope='Short-step synthetic fits; half payload lineage is fixture metadata, not executed fitting.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def track(log):
    WORK.update(neural_model_fits=1, optimizer_steps=log['new_optimizer_steps'])
    n = log['models']['UNIFORM_SHRINK']['counts']['diagnostic_candidate_predictions']
    WORK['diagnostic_candidate_predictions'] += n
    WORK['diagnostic_hidden_activations'] += n * log['hidden']
    WORK['optimizer_parameter_updates'] += log['counts'].get('optimizer_parameter_updates', log['new_optimizer_steps'] * log['parameter_count'])


def records():
    rng = np.random.default_rng(109); rows = []
    for query in ('reward', 'risk_goal'):
        for episode in (0, 1, 4, 6, 8):
            replicas = rng.normal(size=(4, 5)); replicas[:, 0] = 0
            rows.append(dict(query=query, episode=episode, features=rng.normal(size=(5, 121)).tolist(),
                utilities=replicas.mean(axis=0).tolist(), replica_utilities=replicas.tolist()))
    return rows


def half_payload(hidden):
    return m.CandidateModel([p + .005 for p in initialize(121, hidden)], np.linspace(-1, 1, 121),
        np.linspace(.7, 1.7, 121), 3, 'UNIFORM_SHRINK', {'reward': [0], 'risk_goal': [1]},
        1.3, optimizer_steps=7).to_payload()


def inputs(rows, payload):
    training = [row for row in rows if row['episode'] < 7 and row['episode'] % 5 != 4]
    x = (np.asarray([row['features'] for row in training]) - payload['mean']) / payload['scale']
    y = np.asarray([row['utilities'] for row in training])
    return x, y


@pytest.mark.parametrize('hidden', (4, 16))
def test_multiple_head_updates_keep_w_and_bias_exact_with_actual_counts(monkeypatch, hidden):
    monkeypatch.setattr(m, 'STEPS', 10)
    rows = records(); payload = half_payload(hidden); saved = deepcopy(payload)
    model, log = m.fit_update(rows, 7, payload); track(log)
    assert payload == saved and all(log['checks'].values())
    assert all(np.array_equal(model.parameters[i], payload['parameters'][i]) for i in (0, 1))
    assert not np.array_equal(model.parameters[2], payload['parameters'][2])
    assert log['parameter_count'] == 123 * hidden and log['trainable_parameter_count'] == hidden
    assert log['frozen_parameter_count'] == 122 * hidden and log['updated_parameter_indices'] == [2]
    assert log['counts']['optimizer_parameter_updates'] == 10 * hidden
    assert log['counts']['optimizer_root_passes'] == 60 and log['counts']['optimizer_pair_passes'] == 600
    x, y = inputs(rows, payload)
    loss, gradients = m.objective(model.parameters, x, y, 'UNIFORM_SHRINK', uniform_gamma=payload['uniform_gamma'])
    WORK['direct_objective_evaluations'] += 1
    detail = log['models']['UNIFORM_SHRINK']
    assert detail['final_loss'] == loss
    assert detail['final_gradient_norm'] == np.linalg.norm(gradients[2])
    assert detail['final_full_gradient_norm'] == np.sqrt(sum(np.sum(g * g) for g in gradients))
    assert detail['final_full_gradient_norm'] > detail['final_gradient_norm']
    assert detail['gradient_norm_semantics'] == 'updated_parameters_only'
    assert detail['training_by_query']['reward']['roots'] == detail['training_by_query']['risk_goal']['roots'] == 3


def test_full_oracle_matches_original_v107_warm_trajectory(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 6); monkeypatch.setattr(old, 'STEPS', 6)
    rows = records(); payload = half_payload(16)
    model, log = m.fit_update(rows, 7, payload, 'FULL'); track(log)
    expected, previous = old.fit_update(rows, 7, payload, 'FROZEN_STATS_WARM'); track(previous)
    assert model.to_payload() == expected.to_payload()
    for key in ('initial_loss', 'final_loss', 'final_gradient_norm', 'training', 'heldout'):
        assert log['models']['UNIFORM_SHRINK'][key] == previous['models']['UNIFORM_SHRINK'][key]
    assert log['updated_parameter_indices'] == [0, 1, 2] and log['trainable_parameter_count'] == 1968


def test_head_first_step_uses_original_gradient_and_reports_full_l2(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 1)
    rows = records(); payload = half_payload(4); x, y = inputs(rows, payload)
    parameters = [np.asarray(p) for p in payload['parameters']]
    initial, gradients = m.objective(parameters, x, y, 'UNIFORM_SHRINK', uniform_gamma=payload['uniform_gamma'])
    WORK['direct_objective_evaluations'] += 1
    model, log = m.fit_update(rows, 7, payload); track(log)
    gradient = gradients[2]
    expected = parameters[2] - .01 * (.1 * gradient / (1 - .9)) / (np.sqrt(.001 * gradient ** 2 / (1 - .999)) + 1e-8)
    assert np.array_equal(model.parameters[2], expected)
    assert all(np.array_equal(a, b) for a, b in zip(model.parameters[:2], parameters[:2]))
    assert log['models']['UNIFORM_SHRINK']['initial_loss'] == initial
    w, b, v = model.parameters; scores = np.tanh(x @ w + b) @ v; data = 0.
    for i in range(5):
        for j in range(i + 1, 5):
            delta = y[:, i] - y[:, j]; difference = scores[:, i] - scores[:, j]
            data += np.sum(abs(delta) * np.logaddexp(0, -np.sign(delta) * difference)
                + payload['uniform_gamma'] * np.logaddexp(difference / 2, -difference / 2)) / (len(x) * 10)
    hidden_penalty = .001 * sum(float(np.sum(p * p)) for p in parameters[:2]) / 1968
    full_penalty = hidden_penalty + .001 * float(np.sum(v * v)) / 1968
    assert log['models']['UNIFORM_SHRINK']['final_loss'] == pytest.approx(data + full_penalty, rel=1e-13)
    assert hidden_penalty > 0 and log['optimizer_state'] == 'reset_zero_moments'
    assert log['new_optimizer_steps'] == 1 and log['inherited_parameter_steps'] == 7 and log['parameter_lineage_steps'] == 8


def test_fixed_statistics_full_queries_and_heldout_isolation(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 8)
    calls = []; original = m.CandidateModel.score_candidates
    def score(model, features, work=None):
        calls.append(1)
        return original(model, features, work)
    monkeypatch.setattr(m.CandidateModel, 'score_candidates', score)
    rows = records(); payload = half_payload(4); saved = deepcopy(payload)
    model, log = m.fit_update(rows, 7, payload); track(log)
    changed = deepcopy(rows)
    for row in changed:
        if row['episode'] in (4, 8):
            row['features'] = (np.asarray(row['features']) * 10000).tolist()
            replicas = np.asarray(row['replica_utilities']) * 10000
            row['replica_utilities'] = replicas.tolist(); row['utilities'] = replicas.mean(axis=0).tolist()
    other, altered = m.fit_update(changed, 7, payload); track(altered)
    assert model.to_payload() == other.to_payload() and payload == saved
    assert model.training_episodes == {'reward': [0, 1, 6], 'risk_goal': [0, 1, 6]}
    assert log['active_training_episodes'] == model.training_episodes
    assert log['optimized_queries'] == ['reward', 'risk_goal'] and log['data_loss_weight'] == 1
    assert log['training_roots'] == log['active_training_roots'] == log['full_loss_denominator_roots'] == 6
    assert np.array_equal(model.mean, payload['mean']) and np.array_equal(model.scale, payload['scale'])
    assert model.uniform_gamma == payload['uniform_gamma']
    assert log['normalization_training_roots'] == log['conflict_mass_training_roots'] == 2
    assert all(log['checks'].values()) and all(altered['checks'].values())
    assert len(calls) == 16  # Six training plus two heldout roots per fit; query diagnostics reuse scores.
