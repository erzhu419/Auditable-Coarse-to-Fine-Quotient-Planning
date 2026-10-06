"""Joint policy consequences, causal context fields and equal frozen tree recipe."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_context_consequences_v116 as m

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_context_consequences_v116.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        development_work=dict(WORK), environment_transitions=0, model_transitions=0,
        production_tree_fits=0, neural_model_fits=0, optimizer_steps=0,
        scope='Synthetic fixed-policy joint-target trees and inference only; no natural source or evaluation games.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


class ObservedRecord(dict):
    def __getitem__(self, key):
        if key in ('phase', 'p4', 'true_p4', 'module_id'):
            raise AssertionError('unobserved or identity label accessed')
        return super().__getitem__(key)


def records():
    board = [1, 1, 2, 0] + [0] * 12
    return [ObservedRecord(board=board, policy=policy, horizon=30 + i % 2,
        target=[index + (1. if i < 32 else 3.), float(i >= 32), 0.],
        context_p4=.1 if i < 32 else .3, episode=3 * (i // 8) + index, anchor_step=i % 8,
        phase='private', true_p4='private', module_id='private')
        for index, policy in enumerate(m.POLICIES) for i in range(64)]


def fit(rows, mode, context=.1):
    result = m.ConsequenceKnowledge.fit(rows, mode, context)
    WORK.update(result[1]['counts']); WORK.update(consequence_model_fits=1)
    return result


def predict(model, method, *args):
    before = model.counts.copy()
    result = getattr(model, method)(*args)
    WORK.update({key: value - before[key] for key, value in model.counts.items()})
    return result


@pytest.fixture(scope='module')
def fitted():
    rows = records()
    return rows, {mode: fit(rows, mode) for mode in m.MODES}


def test_joint_leaf_means_and_all_completed_records_share_fixed_recipe(fitted):
    rows, models = fitted
    assert len(m.FEATURE_NAMES) == 38
    expected_roster = [{key: row[key] for key in ('episode', 'policy', 'anchor_step', 'horizon')} for row in rows]
    for mode, (model, log) in models.items():
        assert log['training_roster'] == expected_roster and any(r['episode'] == 4 for r in expected_roster)
        assert log['training_records'] == log['counts']['fit_rows'] == log['counts']['feature_rows'] == 192
        assert log['counts']['tree_fits'] == 3
        assert all(row['training_rows'] == 64 for row in log['policies'].values())
        assert log['tree_parameters'] == dict(max_depth=8, min_samples_leaf=16, random_state=7701)
        actual = predict(model, 'predict_many', [rows[0]['board']], 30)
        assert actual.shape == (1, 3, 3)
        expected = [[[index + (1. if mode == 'CONTEXT' else 2.), 0. if mode == 'CONTEXT' else .5, 0.]
            for index in range(3)]]
        assert np.array_equal(actual, expected)
        assert np.all(actual[:, :, 1:] >= 0) and np.all(actual[:, :, 1:].sum(axis=2) <= 1)


def test_record_prediction_uses_only_its_actual_policy_and_explicit_context(fitted):
    rows, models = fitted
    requested = [dict(board=rows[0]['board'], policy=m.POLICIES[index], horizon=30 + index % 2,
        context_p4=-999, target='not a prediction input', phase='private') for index in (2, 0, 1, 2)]
    for mode, (model, _) in models.items():
        before = model.counts.copy()
        actual = predict(model, 'predict_records', requested, .3)
        expected = [[index + (3. if mode == 'CONTEXT' else 2.), 1. if mode == 'CONTEXT' else .5, 0.]
            for index in (2, 0, 1, 2)]
        assert np.array_equal(actual, expected)
        assert model.counts['policy_prediction_rows'] - before['policy_prediction_rows'] == 4
        assert model.counts['tree_apply_rows'] - before['tree_apply_rows'] == 4
        assert model.counts['feature_rows'] - before['feature_rows'] == 4
        assert model.context_p4 == .1


def test_same_context_inputs_produce_identical_tree_parameters():
    rows = records()
    for row in rows:
        row['context_p4'] = .5
    mixed, mixed_log = fit(rows, 'MIXED')
    contextual, context_log = fit(rows, 'CONTEXT')
    assert mixed.trees == contextual.trees
    assert mixed_log['policies'] == context_log['policies']
    assert mixed_log['counts']['tree_fits'] == context_log['counts']['tree_fits'] == 3
    assert mixed_log['counts']['fit_rows'] == context_log['counts']['fit_rows'] == 192


def test_serialized_model_keeps_joint_predictions_and_does_not_retrain(fitted):
    rows, models = fitted
    for mode, (model, _) in models.items():
        payload = model.to_payload(); saved = deepcopy(payload)
        restored = m.ConsequenceKnowledge.from_payload(json.loads(json.dumps(payload)))
        assert restored.to_payload() == payload
        left = predict(model, 'predict_many', [rows[0]['board']] * 2, 31)
        right = predict(restored, 'predict_many', [rows[0]['board']] * 2, 31)
        assert np.array_equal(left, right)
        assert model.to_payload() == restored.to_payload() and payload == saved
        assert 'tree_fits' not in model.counts and 'fit_rows' not in model.counts
