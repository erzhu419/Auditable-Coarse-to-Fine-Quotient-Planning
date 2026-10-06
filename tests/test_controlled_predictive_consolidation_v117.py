"""Conserved leaf budget, causal bank routing and joint consequences."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_consolidation_v117 as m

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_consolidation_v117.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        development_work=dict(WORK), environment_transitions=0, model_transitions=0,
        production_tree_fits=0, neural_model_fits=0, optimizer_steps=0,
        scope='Synthetic source labels, fixed-budget trees and bank inference; no validation use or natural games.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


class CausalRecord(dict):
    def __getitem__(self, key):
        if key in ('phase', 'true_p4', 'context_p4', 'validation'):
            raise AssertionError('non-causal or unrequested metadata was read')
        return super().__getitem__(key)


def records():
    return [CausalRecord(board=[1, 1, 2, 0] + [0] * 12, horizon=30 + index % 2,
        policy=policy, context_module_id=module, target=[pi + float(module), float(module == 5), float(module == 9)],
        episode=pi * 10000 + module * 100 + index // 2, anchor_step=index % 2,
        phase='private', true_p4='private', context_p4='unused', validation='private')
        for pi, policy in enumerate(m.POLICIES) for module in (2, 5, 9)
        if not (policy == 'SNAKE' and module == 9) for index in range(32)]


def fit(rows, mode, module_id=2):
    model, log = m.BankKnowledge.fit(rows, mode, module_id)
    WORK.update(log['counts']); WORK.update(bank_fits=1)
    return model, log


def predict(model, method, *args):
    before = model.counts.copy()
    result = getattr(model, method)(*args)
    WORK.update({key: value - before[key] for key, value in model.counts.items()})
    return result


@pytest.fixture(scope='module')
def fitted():
    rows = records()
    return rows, {mode: fit(rows, mode) for mode in m.MODES}


def test_budget_is_conserved_per_policy_and_saved_causal_groups_are_used(fitted):
    rows, models = fitted
    roster = [{key: r[key] for key in ('episode', 'policy', 'anchor_step', 'horizon', 'context_module_id')} for r in rows]
    for mode, (_, log) in models.items():
        assert log['training_roster'] == roster
        assert log['feature_dim'] == 37 and 'context_p4' not in log['feature_names']
        assert log['counts']['fit_rows'] == log['counts']['feature_rows'] == len(rows)
        for policy in m.POLICIES:
            allocation = log['group_allocations'][policy]
            assert sum(row['leaf_allowance'] for row in allocation) == 256
            assert sum(row['actual_leaves'] for row in allocation) <= 256
            assert sum(row['actual_nodes'] for row in allocation) <= 511
            if mode == 'SPLIT' and policy != 'SNAKE':
                assert [(r['module_id'], r['leaf_allowance']) for r in allocation] == [(2, 86), (5, 85), (9, 85)]
            elif mode == 'SPLIT':
                assert [(r['module_id'], r['leaf_allowance']) for r in allocation] == [(2, 128), (5, 128)]
            else:
                assert len(allocation) == 1 and allocation[0]['module_id'] is None
        assert log['tree_parameters'] == dict(max_depth=8, min_samples_leaf=16, random_state=7701)


def test_joint_policy_inference_and_unavailable_branches_are_distinct(fitted):
    rows, models = fitted; split = models['SPLIT'][0]; shared = models['SHARED'][0]
    assert split.can_route(2) and not split.can_route(9) and not split.can_route(999)
    assert shared.can_route(2) and shared.can_route(9) and shared.can_route(999)
    actual = predict(split, 'predict_many', [rows[0]['board']], 30)
    assert actual.shape == (1, 3, 3)
    assert np.array_equal(actual, [[[2., 0., 0.], [3., 0., 0.], [4., 0., 0.]]])
    requested = [dict(board=rows[0]['board'], horizon=31, policy=policy, context_module_id=module)
        for policy, module in (('GREEDY', 9), ('SNAKE', 9), ('SPACE', 999), ('SNAKE', 5))]
    before = split.counts.copy()
    values = predict(split, 'predict_records', requested)
    assert values == [[9., 0., 1.], None, None, [7., 1., 0.]]
    assert split.counts['predicted_record_rows'] - before['predicted_record_rows'] == 2
    assert split.counts['unavailable_record_rows'] - before['unavailable_record_rows'] == 2
    assert split.counts['tree_apply_rows'] - before['tree_apply_rows'] == 2
    assert all(row is not None for row in predict(shared, 'predict_records', requested))
    missing = m.BankKnowledge.from_payload(split.to_payload()); missing.counts.clear(); missing.module_id = 999
    assert predict(missing, 'predict_many', [rows[0]['board']], 30) is None
    assert missing.counts['unavailable_planning_boards'] == 1 and missing.counts['policy_prediction_rows'] == 0


def test_one_leaf_allowance_is_a_joint_mean_and_overbudget_fit_is_refused():
    base = records()[0]
    rows = [dict(base, policy=policy, context_module_id=module, episode=module,
        target=[float(module), .25, .5]) for policy in m.POLICIES for module in range(256)]
    model, log = fit(rows, 'SPLIT', 255)
    assert log['counts']['tree_fits'] == 0
    assert log['counts']['constant_leaf_models'] == 768
    assert log['counts']['feature_rows'] == 0 and log['counts']['fit_rows'] == 768
    for policy in m.POLICIES:
        assert all(row['leaf_allowance'] == row['actual_leaves'] == row['actual_nodes'] == 1
            and row['constant_leaf'] for row in log['group_allocations'][policy])
    actual = predict(model, 'predict_many', [base['board']], 30)
    assert np.array_equal(actual, [[[255., .25, .5]] * 3])
    with pytest.raises(ValueError, match='leaf budget unavailable'):
        m.BankKnowledge.fit(rows + [dict(base, context_module_id=256)], 'SPLIT', 0)
    with pytest.raises(ValueError, match='no completed source records'):
        m.BankKnowledge.fit([r for r in rows if r['policy'] != 'SNAKE'], 'SHARED', 0)


def test_single_module_is_identical_to_shared_under_the_same_budget():
    rows = [r for r in records() if r['context_module_id'] == 2]
    shared, left = fit(rows, 'SHARED')
    split, right = fit(rows, 'SPLIT')
    for policy in m.POLICIES:
        assert shared.trees[policy]['shared'] == split.trees[policy]['2']
        assert left['group_allocations'][policy][0]['leaf_allowance'] == right['group_allocations'][policy][0]['leaf_allowance'] == 256


def test_payload_restores_routing_and_predictions_without_fitting(fitted):
    rows, models = fitted
    requested = [dict(board=rows[0]['board'], horizon=30, policy='GREEDY', context_module_id=2)]
    for model, _ in models.values():
        payload = model.to_payload(); saved = deepcopy(payload)
        restored = m.BankKnowledge.from_payload(json.loads(json.dumps(payload)))
        assert restored.to_payload() == payload
        assert predict(model, 'predict_records', requested) == predict(restored, 'predict_records', requested)
        assert model.to_payload() == restored.to_payload() and payload == saved
        assert 'tree_fits' not in model.counts and 'fit_rows' not in model.counts
