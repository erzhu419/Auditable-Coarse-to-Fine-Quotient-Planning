"""Single-family equivalence, fresh initialization and heldout isolation."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_capacity_ranking_v103 as old
from acfqp.science import controlled_predictive_fresh_ranking_v105 as m

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_fresh_ranking_v105.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        development_work=dict(WORK), production_neural_model_fits=0, production_optimizer_steps=0,
        environment_transitions=0, model_transitions=0,
        scope='Synthetic short-step models only; V103 three-family oracle runs use eight optimizer steps.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def records():
    rng = np.random.default_rng(105); result = []
    for query in ('reward', 'risk_goal'):
        for episode in (0, 1, 4, 6, 8):
            samples = rng.normal(size=(4, 5)); samples[:, 0] = 0
            features = rng.normal(size=(5, 121)); features[:, 120] = 1
            result.append(dict(query=query, episode=episode, features=features.tolist(),
                utilities=samples.mean(axis=0).tolist(), replica_utilities=samples.tolist()))
    return result


@pytest.mark.parametrize('hidden', (4, 16))
@pytest.mark.parametrize('checkpoint', (2, 7))
def test_single_family_matches_v103_exactly_for_both_ages_and_widths(monkeypatch, hidden, checkpoint):
    monkeypatch.setattr(m, 'STEPS', 8); monkeypatch.setattr(old, 'STEPS', 8)
    rows = records(); model, log = m.fit_model(rows, checkpoint, hidden)
    previous, previous_log = old.fit_models(rows, checkpoint, hidden)
    WORK.update(neural_model_fits=4, optimizer_steps=32, v105_neural_model_fits=1,
        v105_optimizer_steps=8, v103_oracle_neural_model_fits=3, v103_oracle_optimizer_steps=24)
    assert model.to_payload() == previous['UNIFORM_SHRINK'].to_payload()
    assert log['counts'] == dict(neural_model_fits=1, optimizer_steps=8)
    assert set(log['models']) == {'UNIFORM_SHRINK'}
    for key in ('initial_loss', 'final_loss', 'final_gradient_norm', 'training', 'heldout'):
        assert log['models']['UNIFORM_SHRINK'][key] == previous_log['models']['UNIFORM_SHRINK'][key]
    for key in ('uniform_gamma', 'training_episodes', 'normalization_training_roots', 'training_replica_rows'):
        assert log[key] == previous_log[key]
    assert log['parameter_count'] == hidden * 123 and log['l2_coefficient'] == .001 / 1968
    assert model.scale[120] == 1
    work = Counter(); model.score_candidates(rows[0]['features'], work)
    assert work == dict(neural_candidate_predictions=5, neural_hidden_activations=5 * hidden)
    restored = m.CandidateModel.from_payload(model.to_payload())
    assert restored.to_payload() == model.to_payload()


def test_only_uniform_family_runs_and_heldout_future_do_not_change_fit(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 10)
    calls = []; original = m.objective
    def objective(parameters, x, y, family, **kwargs):
        calls.append(family)
        return original(parameters, x, y, family, **kwargs)
    monkeypatch.setattr(m, 'objective', objective)
    rows = records(); model, log = m.fit_model(rows, 7, 4)
    changed = deepcopy(rows)
    for row in changed:
        if row['episode'] in (4, 8):
            row['features'] = (np.asarray(row['features']) * 10000).tolist()
            samples = np.asarray(row['replica_utilities']) * 10000
            row['replica_utilities'] = samples.tolist(); row['utilities'] = samples.mean(axis=0).tolist()
    other, other_log = m.fit_model(changed, 7, 4)
    WORK.update(neural_model_fits=2, optimizer_steps=20, v105_neural_model_fits=2, v105_optimizer_steps=20)
    assert calls == ['UNIFORM_SHRINK'] * 24
    assert model.to_payload() == other.to_payload()
    assert log['uniform_gamma'] == other_log['uniform_gamma']
    assert log['training_roots'] == log['normalization_training_roots'] == log['conflict_mass_training_roots'] == 6
    assert log['heldout_roots'] == 2 and log['training_replica_rows'] == 24
    assert log['training_episodes'] == {'reward': [0, 1, 6], 'risk_goal': [0, 1, 6]}
