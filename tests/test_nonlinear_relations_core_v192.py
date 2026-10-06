"""Synthetic mechanism, weighting, selection and failure witnesses for V192."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from math import exp

import numpy as np
import pytest

from acfqp.science import controlled_predictive_nonlinear_relations_v192 as core


def feature(value):
    return [float(value)]+[0.]*97


def root(root_id='fixture', source=0, first=1., second=0.):
    return dict(root_id=root_id, source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'],
        immediate_rewards=dict(DOWN=0., LEFT=0.), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT'),
        relation_features=dict(DOWN=feature(first), LEFT=feature(second)),
        action_components=dict(DOWN=[1., .3, .7], LEFT=[0., .5, .5]))


def examples():
    return [root(f'fixture:{source:02d}:{index}', source)
            for source in range(36) for index in range(3 if source == 3 else 4)]


def fit(rows, gamma=1., lambda_value=.0001):
    design = core.prepare_design(rows)
    costs = Counter(design['work'])
    decomposition = core._decompose(design, gamma, costs)
    fitted = core._filter(design, decomposition, lambda_value, costs)
    return design, decomposition, fitted, core._model(design, decomposition, fitted, lambda_value, []), costs


def test_complete_pairs_forced_roots_and_direct_shifted_solution():
    rows = [root(f'weighted:{index}') for index in range(5)]
    tail = np.asarray([1., -.2, .2])
    for index, observed in enumerate(rows):
        observed['immediate_rewards'] = dict(DOWN=index/2048., LEFT=1/2048.)
        offset = np.asarray([3.+index, .5, .5])
        observed['action_components'] = dict(
            DOWN=(offset+tail+[observed['immediate_rewards']['DOWN'], 0., 0.]).tolist(),
            LEFT=(offset+[observed['immediate_rewards']['LEFT'], 0., 0.]).tolist())
        if index < 2:
            observed['legal_actions'].append('UP')
            observed['relation_features']['UP'] = feature(0.)
            observed['immediate_rewards']['UP'] = observed['immediate_rewards']['LEFT']
            observed['action_components']['UP'] = observed['action_components']['LEFT'].copy()
            observed['action_map']['UP'] = 'DOWN'
    rows[-1]['legal_actions'] = ['DOWN']
    rows[-1]['action_components'] = {'DOWN': rows[-1]['action_components']['DOWN']}
    rows[-1]['fallback_action'] = 'DOWN'
    before = deepcopy(rows)
    design, decomposition, fitted, model, costs = fit(rows, lambda_value=1.)
    assert rows == before and design['X'].shape == (11, 98) and design['Y'].shape == (8, 3)
    direct = np.linalg.solve(decomposition['H']+5*np.eye(8), design['Y'])
    assert np.asarray(model['dual_coefficients']) == pytest.approx(direct, abs=1e-12)
    assert model['rkhs_energy'] == pytest.approx(np.sum(direct*(decomposition['H']@direct)))
    assert model['objective'] == pytest.approx(model['loss']/5+model['penalty'])
    assert model['constants']['columns'] == 98 and model['constants']['intercept'] is False
    assert len(model['centers']) == 11 and len(model['coefficients']) == 11
    assert len(model['training_outcomes']) == 5
    assert costs['new_predictors_fitted'] == costs['nonlinear_predictors_fitted'] == 1
    for label in design['fit_labels'][:-1]:
        assert sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.)
        for pair in label['pairs']:
            assert pair['components'] == pytest.approx(tail if pair['actions'][0] == 'DOWN' else np.zeros(3))
    assert design['fit_labels'][-1]['pairs'] == []


def test_rbf_represents_two_opposing_linear_orderings():
    rows = []
    for index in range(8):
        observed = root(f'nonlinear:{index}', index, first=0. if index < 4 else 2., second=1.)
        observed['action_components'] = dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.])
        rows.append(observed)
    design, decomposition, fitted, model, _ = fit(rows)
    # A linear score cannot make both -w and +w positive. Shared RBF can.
    for observed in rows:
        decision = core.choose_action(model, core._observable(observed))
        assert decision['canonical_action'] == 'DOWN' and not decision['fallback']
        assert decision['predicted_pairs']['DOWN|LEFT'][0] > .99
        assert decision['predicted_pairs']['DOWN|LEFT'][1:] == pytest.approx([0., 0.])
    assert fitted['root_mean_loss'] < 1e-6
    assert model['rank'] == 2


def test_bandwidth_uses_only_nonzero_distances_of_training_centers():
    train = root(first=0., second=2.)
    train['legal_actions'].append('UP')
    train['relation_features']['UP'] = feature(2.)
    train['immediate_rewards']['UP'] = 0.
    train['action_components']['UP'] = [0., .5, .5]
    train['action_map']['UP'] = 'DOWN'
    design = core.prepare_design([train])
    assert design['median_squared_distance'] == 4.
    assert design['prepare_counts']['nonlinear_median_distance_values'] == 2
    excluded = dict(life=1, root_id='other-teacher-without-features')
    again = core.prepare_design([train, excluded])
    assert again['median_squared_distance'] == 4.
    assert again['root_ids'] == ['fixture']
    heldout = root('heldout', 1, first=10000., second=20000.)
    assert core.prepare_design([train, heldout])['median_squared_distance'] != 4.
    costs = Counter()
    K, H = core._kernel_and_gram(design, .25, costs)
    assert K[0, 1] == pytest.approx(exp(-.25))
    assert K[1, 2] == 1. and H.shape == (3, 3)
    assert costs['nonlinear_kernel_exponentials'] == 3


def test_source_selection_uses_equal_group_actual_utility_and_first_grid_tie(monkeypatch):
    rows = examples()
    for observed in rows:
        good = observed['root_id'].endswith(':0')
        observed['immediate_rewards'] = dict(DOWN=0., LEFT=0. if good else .5)
        observed['action_components'] = dict(DOWN=[2. if good else .2, 0., 0.],
                                            LEFT=[observed['immediate_rewards']['LEFT'], 0., 0.])
        observed.update(oracle_action='UP', teacher_action_native='UP', action_component_fractions={'secret': []})
    before = deepcopy(rows)
    calls = Counter()
    eigen, chooser = core.np.linalg.eigh, core.choose_action
    def counted_eigen(*args, **kwargs):
        calls['eigh'] += 1
        return eigen(*args, **kwargs)
    def observable_only(payload, observed, counts=None):
        assert set(observed) == {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
            'immediate_rewards', 'fallback_action', 'action_map', 'relation_features'}
        calls['decisions'] += 1
        return chooser(payload, observed, counts)
    monkeypatch.setattr(core.np.linalg, 'eigh', counted_eigen)
    monkeypatch.setattr(core, 'choose_action', observable_only)
    result = core.fit_model(rows+[dict(life=1, root_id='excluded-before-labels')])
    assert rows == before and calls == dict(eigh=7, decisions=15*143)
    assert result['costs']['nonlinear_design_preparations'] == 3
    assert result['costs']['nonlinear_predictors_fitted'] == result['costs']['new_predictors_fitted'] == 31
    assert result['costs']['heldout_action_vector_reads'] == 15*143
    selection, model = result['selection'], result['model']
    assert selection['selected_gamma'] == .25 and selection['selected_lambda'] == 1.
    assert selection['selected_utility'] == pytest.approx((35*.875+1.)/36)
    weak, shrunk = selection['candidates'][0], selection['candidates'][4]
    assert weak['utility'] == pytest.approx((35*.65+.8)/36)
    assert shrunk['fold_results'][0]['loss'] > weak['fold_results'][0]['loss']
    assert weak['utility'] != pytest.approx(np.mean([choice['utility']
        for fold in weak['fold_results'] for choice in fold['choices']]))
    assert len(selection['source_folds'][0]) == len(selection['source_folds'][1]) == 18
    assert model['source_root_counts']['DESIGN_SOURCE:03'] == 3 and len(model['root_ids']) == 143
    for fold in selection['folds']:
        assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
        assert set(fold['design']['source_ids']) == set(fold['train_sources'])
        assert 'X' not in fold['design'] and 'Y' not in fold['design'] and 'D' not in fold['design']
        assert len(fold['decompositions']) == 3


def support():
    return dict(action_root_ids={a: ['a', 'b', 'c', 'd'] for a in core.ACTIONS},
        pair_root_ids={f'{a}|{b}': ['a', 'b', 'c', 'd'] for a, b in combinations(core.ACTIONS, 2)},
        connected_components=[list(core.ACTIONS)])


def test_inference_reward_once_python_kernel_and_support_fallback():
    observed = root()
    observed['immediate_rewards']['LEFT'] = 1.2
    payload = dict(life=0, gamma=1., median_squared_distance=1.,
        centers=[dict(features=feature(1.))], coefficients=[[1., .2, .3]], **support())
    counts = Counter()
    decision = core.choose_action(payload, core._observable(observed), counts)
    assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
    assert decision['predicted_components']['DOWN'] == pytest.approx([1., .2, .3])
    assert decision['predicted_components']['LEFT'] == pytest.approx([1.2+exp(-1.), .2*exp(-1.), .3*exp(-1.)])
    assert counts['nonlinear_reward_additions'] == 2
    assert counts['nonlinear_prediction_distance_pairs'] == 2
    assert counts['nonlinear_prediction_distance_subtractions'] == 196
    observed['action_components'] = {'DOWN': [999., 0., 1.], 'LEFT': [-999., 1., 0.]}
    assert core.choose_action(payload, core._observable(observed)) == decision
    payload['action_root_ids']['DOWN'] = ['a', 'b', 'c']
    assert core.choose_action(payload, core._observable(observed))['reason'] == 'insufficient_action_support'
    payload['action_root_ids']['DOWN'].append('d')
    payload['connected_components'] = [['DOWN'], ['LEFT'], ['RIGHT'], ['UP']]
    assert core.choose_action(payload, core._observable(observed))['reason'] == 'disconnected_required_actions'
    observed['legal_actions'] = ['DOWN']; observed['fallback_action'] = 'DOWN'
    payload['action_root_ids']['DOWN'] = []
    assert core.choose_action(payload, core._observable(observed))['reason'] == 'single_legal_action'


def test_epsilon_ties_follow_actions_order_and_model_cache_is_required():
    observed = root()
    observed['immediate_rewards'] = dict(DOWN=0., LEFT=core.EPSILON/2)
    payload = dict(life=0, gamma=1., median_squared_distance=1.,
        centers=[dict(features=feature(0.))], coefficients=[[0., 0., 0.]], **support())
    decision = core.choose_action(payload, core._observable(observed))
    assert decision['canonical_action'] == 'DOWN'
    observed['immediate_rewards']['LEFT'] = 2*core.EPSILON
    assert core.choose_action(payload, core._observable(observed))['canonical_action'] == 'LEFT'
    observed.pop('relation_features')
    with pytest.raises(KeyError):
        core.choose_action(payload, observed)


def test_final_eigen_failure_retains_all_paid_fold_predictors(monkeypatch):
    eigen, attempts = core.np.linalg.eigh, []
    def fail_last(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 7:
            raise np.linalg.LinAlgError('synthetic final SOURCE eigen failure')
        return eigen(*args, **kwargs)
    def cheap_heldout(model, rows):
        records = [dict(source_id=source, roots=sum(r['source_id'] == source for r in rows),
                        components=[1., 0., 0.], utility=1.) for source in sorted({r['source_id'] for r in rows})]
        return records, [], {}
    monkeypatch.setattr(core.np.linalg, 'eigh', fail_last)
    monkeypatch.setattr(core, '_heldout', cheap_heldout)
    with pytest.raises(core.RegularizationExecutionError) as raised:
        core.fit_model(examples())
    record = raised.value.record
    assert record['operation'] == 'NONLINEAR:eigh'
    assert record['costs']['nonlinear_eigh_attempts'] == 7
    assert record['costs']['nonlinear_eigh_decompositions'] == 6
    assert record['costs']['nonlinear_predictors_fitted'] == record['costs']['new_predictors_fitted'] == 30
    assert record['costs']['nonlinear_design_preparations'] == 3
    assert record['costs']['nonlinear_kernel_matrices'] == 7
    assert record['costs']['nonlinear_distance_coordinate_subtractions'] > 0
