"""Synthetic feature and residual-LMS checks; no retained roots or native calls."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_policy_modules_v151 import RootConsequences
from acfqp.science.controlled_predictive_module_semantics_v156 import (
    SCHEMA, ResidualLMS, build_local_features, build_semantic_features)

TEMP = Path(__file__).resolve().parents[1]/'reports/v156_runtime_tmp'
FEATURE_WORK, REFERENCE_WORK = Counter(), Counter()
MODELS = []
BOARD = [5, 1, 1, 0, 2, 2, 0, 0, 0, 3, 3, 0, 0, 0, 0, 4]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'core_checks.json'; data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    work = sum((m.counts for m in MODELS), Counter())
    data['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, feature_work=dict(FEATURE_WORK), reference_feature_work=dict(REFERENCE_WORK),
        synthetic_learner_work=dict(work), synthetic_real_update_calls=work['update_calls'],
        production_root_reads=0, environment_samples=0, model_samples=0, native_planner_calls=0))
    path.write_text(json.dumps(data, indent=2)+'\n')


def learner(kind='SEMANTIC'):
    model = ResidualLMS(kind); MODELS.append(model); return model


def local(board):
    features, work = build_local_features(board); FEATURE_WORK.update(work); return features, work


def semantic(board, choices, query):
    features, work = build_semantic_features(board, choices, query); FEATURE_WORK.update(work); return features, work


def choices():
    exits = {'LEFT': dict(afterstate=[2]*8+[0]*8, score=4),
             'RIGHT': dict(afterstate=[2]*6+[0]*10, score=12),
             'UP': dict(afterstate=[2]*4+[0]*12, score=0)}
    one = {action: dict(exits[action], value=value) for action, value in dict(LEFT=9., RIGHT=3., UP=6.).items()}
    eight = {action: dict(exits[action], value=value) for action, value in dict(LEFT=17., RIGHT=34., UP=0.).items()}
    return dict(risk1=dict(action='LEFT', action_values=one), risk8=dict(action='RIGHT', action_values=eight))


def test_local_features_and_construction_counts_equal_v151_root_features():
    for board in ([1, 1]+[0]*14, BOARD, [i % 11 for i in range(16)]):
        reference = RootConsequences(); expected = reference._features(board)
        REFERENCE_WORK.update(reference.counts)
        actual, work = local(board)
        assert actual == expected and work == dict(reference.counts)
        assert actual[-1] == 1 and sum(actual.values()) == 41
        assert list(actual) == sorted(actual)
        assert 'predictions' not in work and 'root_predictions' not in work


def test_semantic_features_match_fixed_structure_and_target_critic_algebra():
    policies = choices(); before = deepcopy(policies)
    features, work = semantic(BOARD, policies, 'risk1')
    expected = {0: 1., 1: .5, 2: .75, 3: 5/11., 4: 1., 5: 3/24., 6: 1.,
        7: -2., 8: 1., 9: 3., 10: 2/16., 11: 8/2064.}
    assert features == pytest.approx(expected) and policies == before
    assert work == dict(feature_board_reads=48, feature_rank_reads=16+16+4+48+32,
        feature_occurrences=12, teacher_action_value_reads=3, feature_nonzero_addresses=12)
    other_target, _ = semantic(BOARD, policies, 'risk8')
    expected.update({7: -1., 8: 1., 9: 2., 10: -2/16., 11: -8/2064.})
    assert other_target == pytest.approx(expected)


def test_other_teacher_only_supplies_action_and_same_action_keeps_nonzero_features():
    policies = choices(); reference, _ = semantic(BOARD, policies, 'risk1')
    policies['risk8'].update(value=1e9, afterstate=[10]*16, score=1e8)
    policies['risk8']['action_values'] = {'RIGHT': dict(value=-1e9, afterstate=[0]*16, score=-1e8)}
    altered, _ = semantic(BOARD, policies, 'risk1')
    assert altered == reference
    policies['risk8']['action'] = 'LEFT'
    same, _ = semantic(BOARD, policies, 'risk1')
    assert same[0] == 1. and same[9] == 3. and len(same) > 1
    assert not {6, 7, 10, 11}.intersection(same)
    assert all(value != 0. for value in same.values())
    # The one-legal-action contract explicitly defines the top-two gap as zero.
    policies['risk1']['action_values'] = {'LEFT': policies['risk1']['action_values']['LEFT']}
    single, work = semantic(BOARD, policies, 'risk1')
    assert single[2] == .25 and 8 not in single and single[9] == 3.
    assert work['teacher_action_value_reads'] == 1


def test_sparse_lms_uses_normalized_signed_features_and_exact_address_accounting():
    model = learner(); features = {11: .5, 0: 1., 4: -2.}; target = [.5, -.1, .2]
    assert model.state() == dict(feature_kind='SEMANTIC', weights=[], updates=0, frozen=False)
    result = model.update(features, target, alpha=.1)
    assert result['denominator'] == 5.25 and result['prediction'] == [0., 0., 0.]
    for address, value in features.items():
        assert model.weights[address] == pytest.approx([.1*value*y/5.25 for y in target])
    expected = dict(predictions=1, feature_entries_read=9, weight_address_reads=6, component_weight_reads=18,
        allocated_weight_addresses=3, update_calls=1, weight_address_updates=3, component_weight_updates=9)
    assert dict(model.counts) == expected and result['work'] == expected
    assert model.predict(dict(reversed(list(features.items())))) == pytest.approx([.1*y for y in target])
    assert model.updates == 1 and model.counts['predictions'] == 2
    assert model.counts['feature_entries_read'] == 12 and model.counts['component_weight_reads'] == 27


def test_residual_target_reconstructs_labels_while_old_prediction_stays_external():
    model = learner('LOCAL'); features, _ = local(BOARD)
    old, labels = [4., .4, .6], [3., .1, .9]; before = list(old)
    residual = [label-base for label, base in zip(labels, old)]
    model.update(features, residual, alpha=1.)
    fitted = model.predict(features)
    assert fitted == pytest.approx(residual)
    assert [base+correction for base, correction in zip(old, fitted)] == pytest.approx(labels)
    assert old == before and 'old_prediction' not in model.state()
    zero = learner('LOCAL'); assert zero.predict(features) == [0., 0., 0.]
    assert not zero.weights and zero.updates == 0


def test_payload_freeze_and_load_preserve_state_and_charge_only_actual_runtime_work():
    model = learner(); features = {0: 1., 7: -.25}; model.update(features, [1., -.5, .25])
    model.freeze(); frozen = model.state(); counts_before = dict(model.counts)
    with pytest.raises(RuntimeError, match='frozen'): model.update(features, [0., 0., 0.])
    assert model.state() == frozen and dict(model.counts) == counts_before
    payload = model.to_payload(); n = len(model.weights)
    assert payload['schema'] == SCHEMA and payload['weights'] == sorted(payload['weights'])
    assert payload['storage'] == dict(weight_addresses=n, weight_parameters=3*n, numeric_weight_bytes=24*n, numeric_address_bytes=8*n)
    assert payload['counts']['checkpoint_saves'] == 1 and payload['counts']['checkpoint_saved_parameters'] == 3*n
    restored = ResidualLMS.from_payload(deepcopy(payload)); MODELS.append(restored)
    assert restored.state() == frozen
    assert restored.counts == Counter(checkpoint_loads=1, checkpoint_loaded_addresses=n, checkpoint_loaded_parameters=3*n)
    assert restored.predict(features) == pytest.approx(model.predict(features))
    assert restored.state() == frozen
    with pytest.raises(RuntimeError, match='frozen'): restored.update(features, [0., 0., 0.])
