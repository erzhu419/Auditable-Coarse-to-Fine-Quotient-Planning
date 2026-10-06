"""Unchanged half experience and exact reset-Adam continuation."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_pooled_history_v110 as old
from acfqp.science import controlled_predictive_half_continuation_v111 as m

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_half_continuation_v111.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        development_work=dict(WORK), production_neural_model_fits=0, production_optimizer_steps=0,
        environment_transitions=0, model_transitions=0,
        scope='Short-step synthetic fits and V110 numerical oracles; half payloads are constructed, not fitted.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def records():
    rng = np.random.default_rng(111); rows = []
    for life in (11, 12, 13):
        for query in old.QUERIES:
            for episode in (0, 1, 4, 6, 9):
                replicas = rng.normal(size=(4, 5)); replicas[:, 0] = 0
                rows.append(dict(source_life=life, query=query, episode=episode,
                    is_half=episode < 6 or (query == 'reward' and episode == 6),
                    features=rng.normal(size=(5, 121)).tolist(), utilities=replicas.mean(axis=0).tolist(),
                    replica_utilities=replicas.tolist()))
    return rows


def half_payload(rows, hidden):
    training = [r for r in rows if r['is_half'] and r['episode'] % 5 != 4]
    return old.CandidateModel([p + .005 for p in old.initialize(121, hidden)],
        np.linspace(-1, 1, 121), np.linspace(.7, 1.7, 121), 256000, old.FAMILY,
        old._episodes(training), .3, 1000).to_payload()


def fit(rows, hidden, payload):
    model, log = m.fit_continuation(rows, hidden, [11, 12, 13], payload)
    WORK.update(log['counts']); WORK.update(continuation_fits=1, continuation_optimizer_steps=m.STEPS)
    return model, log


def without_seconds(log):
    result = deepcopy(log)
    result.pop('seconds')
    result['models'][m.FAMILY].pop('seconds')
    return result


@pytest.mark.parametrize('hidden', (4, 16))
def test_exact_v110_full_update_when_source_data_is_only_half(monkeypatch, hidden):
    monkeypatch.setattr(m, 'STEPS', 5); monkeypatch.setattr(old, 'STEPS', 5)
    rows = records(); payload = half_payload(rows, hidden)
    actual, log = fit(rows, hidden, payload)
    oracle, oracle_log = old.fit_stage([r for r in rows if r['is_half']], hidden, 'FULL', [11, 12, 13], payload)
    WORK.update(oracle_log['counts']); WORK.update(oracle_fits=1, oracle_optimizer_steps=5)
    expected = oracle.to_payload(); expected['checkpoint'] = 256000
    assert actual.to_payload() == expected
    assert log['stage'] == 'HALF_CONTINUED' and log['checkpoint'] == 256000
    actual_fit = deepcopy(log['models'][m.FAMILY]); actual_fit.pop('seconds')
    expected_fit = deepcopy(oracle_log['models'][m.FAMILY]); expected_fit.pop('seconds')
    assert actual_fit == expected_fit
    assert log['training_roots'] == log['normalization_training_roots'] == 15
    assert log['heldout_roots'] == 6
    assert log['counts']['diagnostic_candidate_predictions'] == 105
    assert log['new_optimizer_steps'] == 5 and log['inherited_parameter_steps'] == 1000
    assert log['parameter_lineage_steps'] == 1005 and all(log['checks'].values())


def test_second_batch_cannot_change_parameters_statistics_or_any_metric(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 4)
    rows = records(); changed = deepcopy(rows); payload = half_payload(rows, 4)
    for row in changed:
        if not row['is_half']:
            row['features'] = (np.asarray(row['features']) * -1000).tolist()
            replicas = np.asarray(row['replica_utilities']) * -1000
            row['replica_utilities'] = replicas.tolist(); row['utilities'] = replicas.mean(axis=0).tolist()
    model, log = fit(rows, 4, payload)
    other, other_log = fit(changed, 4, payload)
    assert model.to_payload() == other.to_payload()
    assert without_seconds(log) == without_seconds(other_log)
    assert log['training_roster'] == log['statistics_roster']
    assert [11, 'reward', 6] in log['training_roster']
    assert [11, 'risk_goal', 6] not in log['training_roster']


def test_internal_heldout_isolated_and_excluded_history_rejected(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 3)
    rows = records(); changed = deepcopy(rows); payload = half_payload(rows, 4)
    for row in changed:
        if row['episode'] % 5 == 4:
            row['features'] = (np.asarray(row['features']) * -1000).tolist()
            replicas = np.asarray(row['replica_utilities']) * -1000
            row['replica_utilities'] = replicas.tolist(); row['utilities'] = replicas.mean(axis=0).tolist()
    actual, log = fit(rows, 4, payload)
    other, other_log = fit(changed, 4, payload)
    assert actual.to_payload() == other.to_payload()
    assert log['models'][m.FAMILY]['training'] == other_log['models'][m.FAMILY]['training']
    contaminated = deepcopy(rows[-1]); contaminated['source_life'] = 14
    assert not contaminated['is_half']
    with pytest.raises(ValueError, match='exactly the declared source lives'):
        m.fit_continuation(rows + [contaminated], 4, [11, 12, 13], payload)
    wrong = deepcopy(payload); wrong['training_episodes']['reward'][0][0] = 14
    with pytest.raises(ValueError, match='actual half training roster'):
        m.fit_continuation(rows, 4, [11, 12, 13], wrong)


def test_copied_half_parameters_and_zero_adam_first_step(monkeypatch):
    monkeypatch.setattr(m, 'STEPS', 1)
    rows = records(); payload = half_payload(rows, 16); saved = deepcopy(payload)
    original = m.objective; observed = []
    def objective(parameters, *args, **kwargs):
        result = original(parameters, *args, **kwargs)
        observed.append(([p.copy() for p in parameters], [g.copy() for g in result[1]]))
        return result
    monkeypatch.setattr(m, 'objective', objective)
    model, log = fit(rows, 16, payload)
    assert len(observed) == 3 and payload == saved
    for initial, retained, gradient, updated in zip(observed[0][0], payload['parameters'], observed[0][1], model.parameters):
        assert np.array_equal(initial, retained)
        expected = initial - m.RATE * (.1 * gradient / (1 - .9)) / (
            np.sqrt(.001 * gradient ** 2 / (1 - .999)) + 1e-8)
        assert np.array_equal(updated, expected)
    assert log['initialization'] == 'half_parameters'
    assert log['optimizer_state'] == 'reset_zero_moments'
    assert log['parameter_lineage_steps'] == 1001
    assert np.array_equal(model.mean, payload['mean']) and np.array_equal(model.scale, payload['scale'])
    assert model.uniform_gamma == payload['uniform_gamma']
