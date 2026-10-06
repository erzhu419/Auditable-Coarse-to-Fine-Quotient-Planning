"""Pooled identity, heldout isolation and unchanged half/full optimization."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_fresh_ranking_v105 as old_half
from acfqp.science import controlled_predictive_incremental_ranking_v107 as old_full
from acfqp.science import controlled_predictive_pooled_history_v110 as m

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_pooled_history_v110.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        development_work=dict(WORK), production_neural_model_fits=0, production_optimizer_steps=0,
        environment_transitions=0, model_transitions=0,
        scope='Short-step synthetic learner fits and V105/V107 numerical oracles; no production fitting.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def records(lives=(11, 12, 13)):
    rng = np.random.default_rng(110)
    rows = []
    for life in lives:
        for query in m.QUERIES:
            for episode in (0, 1, 4, 6, 9):
                replicas = rng.normal(size=(4, 5)); replicas[:, 0] = 0
                rows.append(dict(source_life=life, query=query, episode=episode,
                    is_half=episode < 6 or (query == 'reward' and episode == 6),
                    features=rng.normal(size=(5, 121)).tolist(), utilities=replicas.mean(axis=0).tolist(),
                    replica_utilities=replicas.tolist()))
    return rows


def fit(*args, **kwargs):
    model, log = m.fit_stage(*args, **kwargs)
    WORK.update(log['counts'])
    WORK.update(pooled_fits=1, pooled_optimizer_steps=log['new_optimizer_steps'])
    return model, log


def numeric_payload(model):
    payload = model.to_payload()
    payload.pop('training_episodes')
    return payload


@pytest.mark.parametrize('hidden', (4, 16))
def test_single_history_matches_v105_half_and_v107_full(monkeypatch, hidden):
    monkeypatch.setattr(m, 'STEPS', 5)
    monkeypatch.setattr(old_half, 'STEPS', 5)
    monkeypatch.setattr(old_full, 'STEPS', 5)
    rows = records((11,))
    half, half_log = fit(rows, hidden, 'HALF', [11])
    oracle_half, oracle_half_log = old_half.fit_model([r for r in rows if r['is_half']], 256000, hidden)
    WORK.update(neural_model_fits=1, optimizer_steps=5, oracle_fits=1, oracle_optimizer_steps=5,
        diagnostic_candidate_predictions=oracle_half_log['models'][m.FAMILY]['counts']['diagnostic_candidate_predictions'],
        optimizer_root_passes=5 * oracle_half_log['training_roots'],
        optimizer_pair_passes=50 * oracle_half_log['training_roots'],
        optimizer_parameter_updates=5 * oracle_half.parameter_count)
    full, full_log = fit(rows, hidden, 'FULL', [11], half.to_payload())
    oracle_full, oracle_full_log = old_full.fit_update(rows, 512000, oracle_half.to_payload(), 'FROZEN_STATS_WARM')
    WORK.update(neural_model_fits=1, optimizer_steps=5, oracle_fits=1, oracle_optimizer_steps=5,
        diagnostic_candidate_predictions=oracle_full_log['models'][m.FAMILY]['counts']['diagnostic_candidate_predictions'],
        optimizer_root_passes=5 * oracle_full_log['training_roots'],
        optimizer_pair_passes=50 * oracle_full_log['training_roots'],
        optimizer_parameter_updates=5 * oracle_full.parameter_count)
    for model, oracle, actual_log, oracle_log in ((half, oracle_half, half_log, oracle_half_log),
            (full, oracle_full, full_log, oracle_full_log)):
        assert numeric_payload(model) == numeric_payload(oracle)
        for key in ('initial_loss', 'final_loss', 'final_gradient_norm', 'training', 'heldout'):
            assert actual_log['models'][m.FAMILY][key] == oracle_log['models'][m.FAMILY][key]
        assert all(actual_log['checks'].values())
    assert full_log['parameter_lineage_steps'] == 10


def test_cross_history_episode_identity_and_actual_half_membership(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 3)
    rows = records()
    model, log = fit(rows, 4, 'HALF', [11, 12, 13])
    assert log['training_roots'] == 15 and log['heldout_roots'] == 6
    assert log['normalization_training_roots'] == 15
    assert log['training_roster'] == log['statistics_roster']
    assert len({tuple(row) for row in log['training_roster']}) == 15
    assert model.training_episodes['reward'] == [[life, ep] for life in (11, 12, 13) for ep in (0, 1, 6)]
    assert model.training_episodes['risk_goal'] == [[life, ep] for life in (11, 12, 13) for ep in (0, 1)]
    assert log['counts']['optimizer_root_passes'] == 45
    assert log['counts']['optimizer_pair_passes'] == 450
    assert log['counts']['optimizer_parameter_updates'] == 3 * model.parameter_count
    assert log['counts']['diagnostic_candidate_predictions'] == 105
    assert log['models'][m.FAMILY]['training_by_query']['reward']['roots'] == 9
    assert log['models'][m.FAMILY]['training_by_query']['risk_goal']['roots'] == 6
    assert m.CandidateModel.from_payload(model.to_payload()).training_episodes == model.training_episodes


def test_internal_heldout_cannot_change_half_statistics_or_either_fit(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 4)
    rows = records(); changed = deepcopy(rows)
    for row in changed:
        if row['episode'] % 5 == 4:
            row['features'] = (np.asarray(row['features']) * -1000).tolist()
            replicas = np.asarray(row['replica_utilities']) * -1000
            row['replica_utilities'] = replicas.tolist()
            row['utilities'] = replicas.mean(axis=0).tolist()
    half, half_log = fit(rows, 4, 'HALF', [11, 12, 13])
    other_half, other_half_log = fit(changed, 4, 'HALF', [11, 12, 13])
    full, full_log = fit(rows, 4, 'FULL', [11, 12, 13], half.to_payload())
    other_full, other_full_log = fit(changed, 4, 'FULL', [11, 12, 13], other_half.to_payload())
    assert half.to_payload() == other_half.to_payload()
    assert full.to_payload() == other_full.to_payload()
    assert np.array_equal(full.mean, half.mean) and np.array_equal(full.scale, half.scale)
    assert full.uniform_gamma == half.uniform_gamma
    assert full_log['training_roots'] == 18 and full_log['heldout_roots'] == 12
    for log in (half_log, other_half_log, full_log, other_full_log):
        assert all(log['checks'].values())
        assert log['normalization_training_roots'] == 15


def test_full_starts_at_exact_half_parameters_and_resets_adam(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 1)
    rows = records((11,))
    statistics = [r for r in rows if r['is_half'] and r['episode'] % 5 != 4]
    payload = m.CandidateModel([p + .005 for p in m.initialize(121, 16)],
        np.linspace(-1, 1, 121), np.linspace(.7, 1.7, 121), 256000, m.FAMILY,
        m._episodes(statistics), .3, 1000).to_payload()
    saved = deepcopy(payload); original = m.objective; observed = []
    def objective(parameters, *args, **kwargs):
        result = original(parameters, *args, **kwargs)
        observed.append(([p.copy() for p in parameters], [g.copy() for g in result[1]]))
        return result
    monkeypatch.setattr(m, 'objective', objective)
    monkeypatch.setattr(m, 'initialize', lambda *_: pytest.fail('FULL must retain half parameters'))
    full, log = fit(rows, 16, 'FULL', [11], payload)
    assert len(observed) == 3 and payload == saved
    for initial, retained, gradient, updated in zip(observed[0][0], payload['parameters'], observed[0][1], full.parameters):
        assert np.array_equal(initial, retained)
        expected = initial - m.RATE * (.1 * gradient / (1 - .9)) / (
            np.sqrt(.001 * gradient ** 2 / (1 - .999)) + 1e-8)
        assert np.array_equal(updated, expected)
    assert log['initialization'] == 'half_parameters' and log['optimizer_state'] == 'reset_zero_moments'
    assert log['new_optimizer_steps'] == 1 and log['inherited_parameter_steps'] == 1000
    assert log['parameter_lineage_steps'] == 1001


def test_excluded_history_and_repeated_same_history_root_are_rejected():
    rows = records()
    with pytest.raises(ValueError, match='exactly the declared source lives'):
        m.fit_stage(rows, 4, 'HALF', [11, 12])
    with pytest.raises(ValueError, match='exactly the declared source lives'):
        m.fit_stage(rows, 4, 'HALF', [11, 12, 13, 14])
    with pytest.raises(ValueError, match='must be unique'):
        m.fit_stage(rows + [deepcopy(rows[0])], 4, 'HALF', [11, 12, 13])
