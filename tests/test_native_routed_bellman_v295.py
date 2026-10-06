"""Finite mixed-module references; no environment or formal RNG acquisition."""
from collections import Counter
from fractions import Fraction
import math
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import native_conditional_bellman_v294 as base
from acfqp.science import native_routed_bellman_v295 as routed
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1] / 'reports/routed_bellman_v295/runtime/tests'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def template(offset=False):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    source_query = dict(reward_weight=1., failure_penalty=0., goal_bonus=0.) if offset else QUERY
    result = QueryTD(QueryParent(source, source_query, QUERY, .25 if offset else .5), 'PRIOR', BUILD)
    result.freeze()
    return result


def game():
    return dict(afterstates=np.asarray([[2]+[0]*15, [2]+[0]*15,
        [2, 1]+[0]*14, [2]+[0]*15, [4]+[0]*15], dtype=np.int32),
        rewards=np.asarray([4, 8, 4, 8, 16], dtype=np.float64)/2048.,
        model_p_four=np.asarray([.1, .5, .2, .4, .7]),
        module_ids=np.asarray([0, 1, 0, 1, 2], dtype=np.int64), terminal_code=1)


def init(head, module):
    head.residuals[:] = (np.arange(head.residuals.size).reshape(head.residuals.shape) % 7 + module) * .002


def expected_control(head, board, probability):
    leaf, _ = base.materialize(head, probability, BUILD)
    empty = [i for i, rank in enumerate(board) if not rank]
    target = 0.
    for cell in empty:
        for rank in (1, 2):
            spawned = list(board); spawned[cell] = rank
            target += ((1.-probability if rank == 1 else probability)/len(empty))*leaf.choose(spawned)['value']
    return target


@pytest.mark.parametrize('offset', [False, True])
def test_single_expert_exactly_reproduces_v294_operator_weights_and_samples(offset):
    source = template(offset)
    ordinary, expert = base.ResidualHead(source, True, BUILD), base.ResidualHead(source, True, BUILD)
    init(ordinary, 0); np.copyto(expert.residuals, ordinary.residuals)
    data = game(); data['module_ids'][:] = 0
    original_source = source.weights.copy()
    expected = base.fit_episode(ordinary, data, 'EXPECTED_CONTROL', BUILD)
    actual = routed.fit_routed_episode({0: expert}, data, BUILD)
    np.testing.assert_array_equal(expert.residuals, ordinary.residuals)
    np.testing.assert_array_equal(source.weights, original_source)
    assert actual['first_sample'] == expected['first_sample']
    assert actual['last_sample'] == expected['last_sample']
    assert actual['learning_counts'] == expected['learning_counts']
    assert actual['target_counts'] == expected['target_counts']
    assert actual['prediction_counts'] == expected['prediction_counts']
    assert actual['by_module']['0']['first_sample'] == actual['first_sample']
    assert actual['by_module']['0']['last_sample'] == actual['last_sample']
    assert expert.updates == ordinary.updates == 4
    assert actual['module_updates'] == {'0': 4}
    assert actual['dense_expert_weight_stack_bytes'] == 0
    assert actual['residual_pointer_array_bytes'] == np.dtype(np.uintp).itemsize


def test_mixed_experts_use_global_denominator_and_all_game_start_predictions():
    source = template()
    heads = {module: base.ResidualHead(source, True, BUILD) for module in range(3)}
    for module, head in heads.items():
        init(head, module); head.updates = 5*module
    before = {m: head.residuals.copy() for m, head in heads.items()}
    source_before = source.weights.copy()
    data = game()
    denominators, records = Counter(), []
    for step, board in enumerate(data['afterstates']):
        if max(board) >= source.radix:
            continue
        module, probability = int(data['module_ids'][step]), float(data['model_p_four'][step])
        head = heads[module]
        features = list(map(int, source.model.feature_indices(board)))
        denominators.update(features)
        prediction = base.predict(head, np.asarray([board]), [probability], BUILD)['predictions'][0]
        target = expected_control(head, board, probability)
        records.append((step, module, probability, features, prediction, target))
    gradients = {m: [{a: 0. for a in denominators} for _ in range(2)] for m in heads}
    touched = {m: set() for m in heads}
    for _, module, probability, features, prediction, target in records:
        norm = math.sqrt((1.-probability)**2+probability**2)
        coefficients = ((1.-probability)/norm, probability/norm)
        touched[module].update(features)
        for address in features:
            for bank in range(2):
                gradients[module][bank][address] += coefficients[bank]*(target-prediction)
    reference = {m: array.copy() for m, array in before.items()}
    for module in heads:
        flat = reference[module].reshape(2, -1)
        for bank in range(2):
            for address in sorted(touched[module]):
                flat[bank, address] += .0025*gradients[module][bank][address]/denominators[address]
    actual = routed.fit_routed_episode(heads, data, BUILD)
    for module, head in heads.items():
        np.testing.assert_allclose(head.residuals, reference[module], rtol=0., atol=2e-15)
    np.testing.assert_array_equal(heads[2].residuals, before[2])
    np.testing.assert_array_equal(source.weights, source_before)
    assert actual['module_updates'] == {'0': 2, '1': 2, '2': 0}
    assert [heads[m].updates for m in heads] == [2, 7, 10]
    assert actual['by_module']['2']['first_sample'] is None
    assert actual['by_module']['2']['new_value_updates'] == 10
    assert actual['by_module']['1']['old_value_updates'] == 5
    assert actual['learning_counts']['table_updates'] == 2*sum(map(len, touched.values()))
    assert actual['consolidation_counts']['address_occurrence_count_visits'] == 128
    assert actual['counts']['routed_expert_parameter_commits'] == 2
    assert actual['counts']['routed_expert_address_pairs'] == sum(map(len, touched.values()))
    for module in (0, 1):
        entries = [r for r in records if r[1] == module]
        for key, row in (('first_sample', entries[0]), ('last_sample', entries[-1])):
            step, _, probability, _, prediction, target = row
            receipt = actual['by_module'][str(module)][key]
            assert receipt['step'] == step and receipt['model_p_four'] == probability
            assert receipt['prediction_before_update'] == prediction
            assert receipt['target'] == pytest.approx(target, abs=2e-14)
    # Independent per-module calls would silently change the normalization.
    wrong = base.ResidualHead(source, True, BUILD); np.copyto(wrong.residuals, before[0])
    keep = data['module_ids'] == 0
    subset = {k: v[keep] for k, v in data.items() if isinstance(v, np.ndarray)}
    subset['terminal_code'] = data['terminal_code']
    base.fit_episode(wrong, subset, 'EXPECTED_CONTROL', BUILD)
    assert not np.array_equal(wrong.residuals, heads[0].residuals)
    assert source.updates == 0 and not source.weights.flags.writeable


def test_route_selects_only_the_observed_expert_and_does_not_use_factual_suffix():
    source = template()
    left = {m: base.ResidualHead(source, True, BUILD) for m in range(2)}
    right = {m: base.ResidualHead(source, True, BUILD) for m in range(2)}
    for module in left:
        init(left[module], module); np.copyto(right[module].residuals, left[module].residuals)
    data = game(); data['module_ids'][-1] = 1
    changed = dict(data, rewards=data['rewards']+500., terminal_code=-1)
    a = routed.fit_routed_episode(left, data, BUILD)
    b = routed.fit_routed_episode(right, changed, BUILD)
    for module in left:
        np.testing.assert_array_equal(left[module].residuals, right[module].residuals)
    assert a['first_sample'] == b['first_sample'] and a['last_sample'] == b['last_sample']
    assert a['by_module'] == b['by_module']
    assert a['target_counts']['skipped_winning_afterstates'] == 1
    assert a['target_counts']['expected_control_targets'] == 4
    assert a['counts']['routed_sample_expert_reads'] == 4
