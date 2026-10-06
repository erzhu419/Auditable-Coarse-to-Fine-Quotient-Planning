"""Frozen statistics, parameter initialization and reset-Adam update semantics."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_fresh_ranking_v105 as old
from acfqp.science import controlled_predictive_incremental_ranking_v107 as m

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_incremental_ranking_v107.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before, development_work=dict(WORK),
        production_neural_model_fits=0, production_optimizer_steps=0, environment_transitions=0, model_transitions=0,
        scope='Short-step synthetic fits; half payloads have synthetic lineage metadata and are not newly fitted.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def records():
    rng = np.random.default_rng(107); rows = []
    for query in ('reward', 'risk_goal'):
        for episode in (0, 1, 4, 6, 8):
            replicas = rng.normal(size=(4, 5)); replicas[:, 0] = 0
            rows.append(dict(query=query, episode=episode, features=rng.normal(size=(5, 121)).tolist(),
                utilities=replicas.mean(axis=0).tolist(), replica_utilities=replicas.tolist()))
    return rows


def half_payload(rows, hidden, same_stats=False):
    mean, scale, gamma = np.linspace(-1., 1., 121), np.linspace(.7, 1.7, 121), 1.3
    if same_stats:
        train = [r for r in rows if r['episode'] < 7 and r['episode'] % 5 != 4]
        features = np.asarray([r['features'] for r in train])
        mean, scale = features.mean(axis=(0, 1)), features.std(axis=(0, 1))
        gamma = float(old.pair_gamma([r['utilities'] for r in train], [r['replica_utilities'] for r in train]).mean())
    parameters = [p + .005 for p in m.initialize(121, hidden)]
    return m.CandidateModel(parameters, mean, scale, 3, 'UNIFORM_SHRINK',
        {'reward': [0], 'risk_goal': [1]}, gamma, optimizer_steps=7).to_payload()


@pytest.mark.parametrize('hidden', (4, 16))
def test_scratch_matches_original_recipe_when_statistics_are_the_same(monkeypatch, hidden):
    monkeypatch.setattr(m, 'STEPS', 6); monkeypatch.setattr(old, 'STEPS', 6)
    rows = records(); payload = half_payload(rows, hidden, same_stats=True)
    actual, log = m.fit_update(rows, 7, payload, 'FROZEN_STATS_SCRATCH')
    expected, expected_log = old.fit_model(rows, 7, hidden)
    WORK.update(neural_model_fits=2, optimizer_steps=12, update_fits=1, update_steps=6, oracle_fits=1, oracle_steps=6)
    assert actual.to_payload() == expected.to_payload()
    assert all(log['checks'].values())
    for key in ('initial_loss', 'final_loss', 'final_gradient_norm', 'training', 'heldout'):
        assert log['models']['UNIFORM_SHRINK'][key] == expected_log['models']['UNIFORM_SHRINK'][key]
    assert log['new_optimizer_steps'] == log['parameter_lineage_steps'] == 6
    assert log['inherited_parameter_steps'] == 0


@pytest.mark.parametrize('mode', m.MODES)
def test_half_statistics_and_full_roster_are_fixed_with_heldout_isolation(monkeypatch, mode):
    monkeypatch.setattr(m, 'STEPS', 8)
    rows = records(); payload = half_payload(rows, 4); saved = deepcopy(payload)
    model, log = m.fit_update(rows, 7, payload, mode)
    changed = deepcopy(rows)
    for row in changed:
        if row['episode'] in (4, 8):
            row['features'] = (np.asarray(row['features']) * 10000).tolist()
            replicas = np.asarray(row['replica_utilities']) * 10000
            row['replica_utilities'] = replicas.tolist(); row['utilities'] = replicas.mean(axis=0).tolist()
    other, alternate = m.fit_update(changed, 7, payload, mode)
    WORK.update(neural_model_fits=2, optimizer_steps=16, update_fits=2, update_steps=16)
    assert payload == saved and model.to_payload() == other.to_payload()
    assert np.array_equal(model.mean, payload['mean']) and np.array_equal(model.scale, payload['scale'])
    assert model.uniform_gamma == payload['uniform_gamma']
    assert log['normalization_training_roots'] == log['conflict_mass_training_roots'] == 2
    assert log['statistics_training_episodes'] == {'reward': [0], 'risk_goal': [1]}
    assert log['training_roots'] == 6 and log['heldout_roots'] == 2 and log['total_training_pairs'] == 60
    assert log['training_episodes'] == {'reward': [0, 1, 6], 'risk_goal': [0, 1, 6]}
    assert log['statistics_source_checkpoint'] == 3 and log['checkpoint'] == 7
    assert all(log['checks'].values()) and all(alternate['checks'].values())
    assert log['inherited_parameter_steps'] == (7 if mode.endswith('WARM') else 0)
    assert log['parameter_lineage_steps'] == 8 + log['inherited_parameter_steps']


def test_warm_starts_at_copied_half_parameters_with_zero_adam_moments(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 1)
    rows = records(); payload = half_payload(rows, 16); saved = deepcopy(payload)
    original_objective = m.objective; observed = []
    def objective(parameters, x, y, family, **kwargs):
        result = original_objective(parameters, x, y, family, **kwargs)
        observed.append(([p.copy() for p in parameters], [g.copy() for g in result[1]]))
        return result
    monkeypatch.setattr(m, 'objective', objective)
    monkeypatch.setattr(m, 'initialize', lambda *_: pytest.fail('warm mode must not initialize new parameters'))
    model, log = m.fit_update(rows, 7, payload, 'FROZEN_STATS_WARM')
    WORK.update(neural_model_fits=1, optimizer_steps=1, update_fits=1, update_steps=1)
    assert payload == saved and len(observed) == 3
    for parameter, saved_parameter, gradient, final in zip(observed[0][0], payload['parameters'], observed[0][1], model.parameters):
        assert np.array_equal(parameter, saved_parameter)
        first = .1 * gradient; second = .001 * gradient ** 2
        expected = parameter - .01 * (first / (1 - .9)) / (np.sqrt(second / (1 - .999)) + 1e-8)
        assert np.array_equal(final, expected)
    assert log['optimizer_state'] == 'reset_zero_moments' and all(log['checks'].values())
    assert log['new_optimizer_steps'] == 1 and log['inherited_parameter_steps'] == 7 and log['parameter_lineage_steps'] == 8
    assert log['counts'] == dict(neural_model_fits=1, optimizer_steps=1)
    work = Counter(); model.score_candidates(rows[0]['features'], work)
    assert work == dict(neural_candidate_predictions=5, neural_hidden_activations=80)
