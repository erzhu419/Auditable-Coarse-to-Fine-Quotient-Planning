"""Synthetic witnesses for fixed products and matched SOURCE-only selection."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from math import sqrt

import numpy as np
import pytest

from acfqp.science import controlled_predictive_mechanism_interactions_v188 as core


TAIL = np.asarray([1., -.2, .2])


def layout(active=False):
    return dict(aggregate=[float(active), 0., 0., 0., 0., 0.],
        tokens=[['cell', i, 0] for i in range(16)]
        + [['horizontal', 4*r+c, 0, 0] for r in range(4) for c in range(3)]
        + [['vertical', 4*r+c, 0, 0] for r in range(3) for c in range(4)])


def root(root_id='synthetic', source=0):
    return dict(root_id=root_id, source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'],
        immediate_rewards=dict(DOWN=0., LEFT=0.), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT'),
        layout_features=dict(DOWN=layout(True), LEFT=layout()),
        action_features=dict(DOWN=[1., 0., 0., 0., 0., 0.], LEFT=[0.]*6),
        action_components=dict(DOWN=[1., .3, .7], LEFT=[0., .5, .5]))


def examples():
    return [root(f'synthetic:{source:02d}:{index}', source)
            for source in range(36) for index in range(3 if source == 3 else 4)]


def fit(rows, mode, lambda_value):
    design = core.prepare_design(rows, mode)
    costs = Counter(design['work'])
    decomposition = core.ridge._decompose(design, costs)
    fitted = core.ridge._filter(design, decomposition, lambda_value)
    return core._model(design, decomposition, fitted, lambda_value, []), design


def inference_models():
    support = dict(action_root_ids={a: ['a', 'b', 'c', 'd'] for a in core.ACTIONS},
        pair_root_ids={f'{a}|{b}': ['a', 'b', 'c', 'd'] for a, b in combinations(core.ACTIONS, 2)},
        connected_components=[list(core.ACTIONS)])
    models = {}
    for mode, columns in (('LINEAR', 6), ('INTERACT', 26)):
        weights = [[0., 0., 0.] for _ in range(columns)]
        weights[0][0] = 1.
        models[mode] = dict(mode=mode, life=0, coefficients=weights, **deepcopy(support))
    for mode in ('RIDGE', 'LAYOUT'):
        weights = [[0., 0., 0.] for _ in range(46)]
        weights[0][0] = 1.
        models[mode] = dict(life=0, coefficients=weights, vocabulary=sorted(layout()['tokens'], key=tuple),
                            **deepcopy(support))
    for mode in ('SHARED', 'OLD_SHARED'):
        weights = [[0., 0., 0.] for _ in range(6)]
        weights[0][0] = -1. if mode == 'OLD_SHARED' else 1.
        models[mode] = dict(life=0, coefficients=weights, **deepcopy(support))
    leaf = dict(leaf_id=0, coefficients={a: [0., 0., 0.] for a in core.ACTIONS}, **deepcopy(support))
    models['ONE'] = dict(mode='ONE_LATE', life=0, groups={'ALL': 0}, leaves=[leaf])
    return models


def test_products_use_frozen_physical_scales_and_omit_binary_goal_square():
    work = Counter()
    observed = dict(action_features={'DOWN': [1, 16, 12, 12, 12, 12]})
    values = core.action_features_from_root(observed, work)['DOWN']
    expected_pairs = [(i, j) for i in range(6) for j in range(i, 6) if (i, j) != (0, 0)]
    assert list(core.PRODUCT_PAIRS) == expected_pairs and len(values) == 26
    assert values[:6] == [1., 16., 12., 12., 12., 12.]
    assert values[6:] == pytest.approx([sqrt(core.BOUNDS[i]*core.BOUNDS[j]) for i, j in expected_pairs])
    assert values[6] == 4. and values[11] == 16.
    goal_only = core.action_features_from_root(dict(action_features={'DOWN': [1, 0, 0, 0, 0, 0]}))['DOWN']
    assert goal_only[0] == 1. and goal_only[6:] == [0.]*20
    assert work['mechanism_product_feature_multiplications'] == work['mechanism_product_normalizations'] == 20
    assert core._basis('INTERACT')['aggregate_scaling'] == 'UNCHANGED'
    assert core._basis('LINEAR')['products'] == [] and core._basis('LINEAR')['columns'] == 6


def test_cached_linear_reads_only_six_columns_and_interactions_never_swipe(monkeypatch):
    observed = root()
    def forbidden(*args, **kwargs):
        raise AssertionError('mechanism cache repeated a deterministic ground swipe')
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', forbidden)
    work = core.cache_roots([observed])
    assert len(observed['interaction_features']['DOWN']) == 26
    assert work['layout_feature_cache_hits'] == 1
    assert work['mechanism_product_feature_multiplications'] == 40
    linear_work, interaction_work = Counter(), Counter()
    linear = core.action_features_from_root(observed, linear_work, 'LINEAR')
    interaction = core.action_features_from_root(observed, interaction_work)
    assert linear == {a: vector[:6] for a, vector in interaction.items()}
    assert linear_work['mechanism_cached_feature_reads'] == 12
    assert interaction_work['mechanism_cached_feature_reads'] == 52
    assert 'mechanism_product_feature_multiplications' not in linear_work
    assert 'mechanism_product_feature_multiplications' not in interaction_work
    fallback_cache = deepcopy(observed)
    fallback_cache.pop('interaction_features'); fallback_cache.pop('action_features')
    assert core.action_features_from_root(fallback_cache) == interaction


def test_root_weighted_full_vectors_first_reward_and_common_offsets_are_preserved():
    rows = [root(f'weighted:{i}') for i in range(8)]
    for index, observed in enumerate(rows):
        observed['immediate_rewards'] = dict(DOWN=(index % 3)/2048., LEFT=1/2048.)
        offset = np.asarray([3.+index, .5, .5])
        down, left = offset+TAIL, offset.copy()
        down[0] += observed['immediate_rewards']['DOWN']; left[0] += observed['immediate_rewards']['LEFT']
        observed['action_components'] = dict(DOWN=down.tolist(), LEFT=left.tolist())
        if index % 2:
            observed['legal_actions'].append('UP')
            observed['action_features']['UP'] = [0.]*6
            observed['immediate_rewards']['UP'] = observed['immediate_rewards']['LEFT']
            observed['action_components']['UP'] = left.tolist()
            observed['action_map']['UP'] = 'DOWN'
    for mode, columns in (('LINEAR', 6), ('INTERACT', 26)):
        model, design = fit(rows, mode, 1.)
        assert design['X'].shape == (16, columns) and design['Y'].shape == (16, 3)
        assert model['coefficients'][0] == pytest.approx(TAIL*5/11)
        assert model['penalty'] == pytest.approx(np.sum((TAIL*5/11)**2))
        assert model['objective'] == pytest.approx(model['loss']/8+model['penalty'])
        assert 'vocabulary' not in model and model['constants']['columns'] == columns
        for label in design['fit_labels']:
            assert sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.)
            for pair in label['pairs']:
                assert pair['components'] == pytest.approx(TAIL if pair['actions'][0] == 'DOWN' else np.zeros(3))
        observed = deepcopy(rows[0])
        observed['immediate_rewards'] = dict(DOWN=0., LEFT=.8)
        decision = core.choose_action(model, observed)
        assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
        assert decision['predicted_components']['DOWN'] == pytest.approx(TAIL*5/11)
        assert decision['predicted_components']['LEFT'] == pytest.approx([.8, 0., 0.], abs=1e-12)
        assert 'coverage' not in decision
        shifted = deepcopy(rows)
        for item in shifted:
            for action in item['legal_actions']:
                item['action_components'][action] = (np.asarray(item['action_components'][action])+[100., .1, -.1]).tolist()
        changed, _ = fit(shifted, mode, 1.)
        assert np.asarray(changed['coefficients']) == pytest.approx(np.asarray(model['coefficients']), abs=1e-12)


def test_shared_mechanism_product_recovers_a_contrast_the_linear_basis_cannot():
    rows = []
    for index, (vacancies, merge_count) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]*2):
        observed = root(f'interaction:{index}')
        observed['action_features']['DOWN'] = [0., vacancies, merge_count, 0., 0., 0.]
        target = TAIL*(vacancies*merge_count/sqrt(16*12))
        observed['action_components'] = dict(DOWN=(target+[0., .5, .5]).tolist(), LEFT=[0., .5, .5])
        rows.append(observed)
    linear, _ = fit(rows, 'LINEAR', 0.)
    interaction, _ = fit(rows, 'INTERACT', 0.)
    assert linear['loss'] > 1e-6
    assert interaction['loss'] < 1e-24 and interaction['rank'] == 3
    for observed in rows:
        decision = core.choose_action(interaction, observed)
        expected = np.asarray(observed['action_components']['DOWN'])-observed['action_components']['LEFT']
        assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx(expected, abs=1e-12)


def test_both_arms_use_source_heldout_actual_utility_and_one_shared_feature_cache(monkeypatch):
    rows = examples()
    for observed in rows:
        good = observed['root_id'].endswith(':0')
        observed['immediate_rewards'] = dict(DOWN=0., LEFT=0. if good else .5)
        observed['action_components'] = dict(DOWN=[2. if good else .2, 0., 0.],
                                            LEFT=[observed['immediate_rewards']['LEFT'], 0., 0.])
        observed.update(oracle_action='UP', teacher_action_native='UP', action_component_fractions={'secret': []})
    before = deepcopy(rows)
    calls = dict(svd=0, filters=0, modes=[])
    svd, filtering, preparing, chooser = core.ridge.np.linalg.svd, core.ridge._filter, core.prepare_design, core.choose_action
    def counted_svd(*args, **kwargs):
        calls['svd'] += 1
        return svd(*args, **kwargs)
    def counted_filter(*args, **kwargs):
        calls['filters'] += 1
        return filtering(*args, **kwargs)
    def counted_prepare(examples, mode='INTERACT', life=0):
        calls['modes'].append(mode)
        return preparing(examples, mode, life)
    allowed = {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards',
               'fallback_action', 'action_map', 'layout_features', 'action_features', 'interaction_features'}
    def observable_only(payload, observed, counts=None):
        assert set(observed) == allowed
        return chooser(payload, observed, counts)
    def forbidden(*args, **kwargs):
        raise AssertionError('SOURCE-selected mechanism fit recomputed an afterstate')
    monkeypatch.setattr(core.ridge.np.linalg, 'svd', counted_svd)
    monkeypatch.setattr(core.ridge, '_filter', counted_filter)
    monkeypatch.setattr(core, 'prepare_design', counted_prepare)
    monkeypatch.setattr(core, 'choose_action', observable_only)
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', forbidden)
    result = core.fit_models(rows+[dict(life=1, root_id='excluded-before-labels')])
    assert rows == before and calls == dict(svd=6, filters=26, modes=['LINEAR']*3+['INTERACT']*3)
    assert result['costs']['ridge_svd_decompositions'] == 6
    assert result['costs']['ridge_predictors_fitted'] == result['costs']['new_predictors_fitted'] == 26
    assert result['costs']['heldout_action_vector_reads'] == 12*143
    assert result['cache_counts']['mechanism_feature_maps_derived'] == 143
    assert result['costs']['mechanism_product_feature_multiplications'] == 40*143
    for mode in core.MODES:
        selection, model = result['selections'][mode], result['models'][mode]
        assert 'model' not in selection and selection['selected_lambda'] == 1.
        zero, shrunk = selection['candidates'][0], selection['candidates'][-1]
        assert zero['utility'] == pytest.approx((35*.65+.8)/36)
        assert shrunk['utility'] == pytest.approx((35*.875+1.)/36)
        assert shrunk['fold_results'][0]['loss'] > zero['fold_results'][0]['loss']
        assert zero['utility'] != pytest.approx(np.mean([choice['utility']
            for fold in zero['fold_results'] for choice in fold['choices']]))
        assert selection['costs']['ridge_predictors_fitted'] == 13
        assert len(selection['source_folds'][0]) == len(selection['source_folds'][1]) == 18
        assert model['source_root_counts']['DESIGN_SOURCE:03'] == 3 and len(model['root_ids']) == 143
        for fold in selection['folds']:
            assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
            assert set(fold['design']['source_ids']) == set(fold['train_sources'])
            assert len(fold['design']['action_root_ids']['DOWN']) == (71 if fold['fold'] == 0 else 72)
            assert 'X' not in fold['design'] and 'Y' not in fold['design']


def test_grid_ties_keep_first_lambda_and_later_failure_retains_completed_arm(monkeypatch):
    result = core.fit_models(examples())
    assert all(selection['selected_lambda'] == 0. for selection in result['selections'].values())
    svd, attempts = core.ridge.np.linalg.svd, []
    def fail_fourth(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 4:
            raise np.linalg.LinAlgError('synthetic INTERACT decomposition failure')
        return svd(*args, **kwargs)
    monkeypatch.setattr(core.ridge.np.linalg, 'svd', fail_fourth)
    with pytest.raises(core.ridge.RegularizationExecutionError) as raised:
        core.fit_models(examples())
    record = raised.value.record
    assert record['operation'] == 'INTERACT:svd'
    assert record['costs']['ridge_svd_attempts'] == 4 and record['costs']['ridge_svd_decompositions'] == 3
    assert record['costs']['ridge_predictors_fitted'] == 13 and record['costs']['ridge_design_preparations'] == 4
    assert record['costs']['mechanism_product_feature_multiplications'] == 40*143


def test_observable_inference_support_and_eight_mode_dispatch_use_cached_features(monkeypatch):
    observed, models = root(), inference_models()
    observed['immediate_rewards']['LEFT'] = .25
    observed.update(oracle_action='UP', teacher_action_native='UP', action_component_fractions={'secret': []})
    def forbidden(*args, **kwargs):
        raise AssertionError('cached decisions performed an extra ground swipe')
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', forbidden)
    core.cache_roots([observed])
    before = deepcopy(models)
    allowed = {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards',
               'fallback_action', 'action_map', 'layout_features', 'action_features', 'interaction_features'}
    chooser = core.choose_action
    def checked(payload, current, counts=None):
        assert set(current) == allowed
        return chooser(payload, current, counts)
    monkeypatch.setattr(core, 'choose_action', checked)
    for module in (core.layout, core.shared, core.exact):
        chooser_control = module.choose_action
        def checked_control(payload, current, chooser_control=chooser_control):
            assert set(current) == allowed
            return chooser_control(payload, current)
        monkeypatch.setattr(module, 'choose_action', checked_control)
    choices, work = core.freeze_choices([observed], models)
    assert models == before and set(choices) == {*core.MODEL_NAMES, 'FALLBACK'}
    for mode in ('INTERACT', 'LINEAR', 'RIDGE', 'LAYOUT', 'SHARED'):
        assert choices[mode][0]['canonical_action'] == 'DOWN' and choices[mode][0]['actual_action'] == 'UP'
    for mode in ('OLD_SHARED', 'ONE', 'FALLBACK'):
        assert choices[mode][0]['canonical_action'] == 'LEFT' and choices[mode][0]['actual_action'] == 'RIGHT'
    assert work['mechanism_frozen_model_choices'] == 7 and work['mechanism_frozen_fallback_choices'] == 1
    assert work['mechanism_cached_feature_reads'] == 64
    assert work['mechanism_prediction_feature_reads'] == 192
    inference = core._observable(observed)
    decision = chooser(models['INTERACT'], inference)
    observed['action_components'] = {'DOWN': [-999., 1., 0.], 'LEFT': [999., 0., 1.]}
    assert chooser(models['INTERACT'], core._observable(observed)) == decision
    unsupported = deepcopy(models['INTERACT'])
    unsupported['action_root_ids']['DOWN'] = ['a', 'b', 'c']
    assert chooser(unsupported, inference)['reason'] == 'insufficient_action_support'
    unsupported['action_root_ids']['DOWN'].append('d')
    unsupported['connected_components'] = [['DOWN'], ['LEFT'], ['RIGHT'], ['UP']]
    assert chooser(unsupported, inference)['reason'] == 'disconnected_required_actions'
    inference['legal_actions'] = ['DOWN']; inference['fallback_action'] = 'DOWN'
    unsupported['action_root_ids']['DOWN'] = []
    assert chooser(unsupported, inference)['reason'] == 'single_legal_action'


def test_fresh_seed_range_and_original_board_geometry_use_mock_rng_only(monkeypatch):
    seeds = []
    class FixtureRandom:
        def __init__(self, seed):
            seeds.append(seed)
        def randint(self, lower, upper):
            assert (lower, upper) == (1, 10)
            return 3
        def sample(self, population, count):
            return list(population)[:count]
    monkeypatch.setattr(core.random, 'Random', FixtureRandom)
    cases = core.cohort_cases()
    assert len(cases) == 96 and seeds == list(range(1880200, 1880296))
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    for ordinal, case in enumerate(cases):
        replica, index = divmod(ordinal, 24)
        first, second = edges[index]
        assert case['name'] == f'v188_target_r{replica:02d}_{index:02d}'
        assert case['split'] == 'TARGET' and case['horizon'] == 3
        assert case['board'][first] == case['board'][second] == 1+index % 10
        assert case['board'].count(0) == case['vacancies'] == index % 3
