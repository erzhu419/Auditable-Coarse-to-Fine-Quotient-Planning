"""Three pure synthetic witnesses for mechanism products and matched controls."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
import math

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_mechanism_interactions_v188 as audit


def source_examples():
    rows = []
    for source in range(36):
        legal = ['LEFT', 'DOWN', 'UP'] if source % 2 else ['LEFT', 'DOWN']
        row = dict(root_id=f'synthetic:{source:02d}', source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
            canonical_board=[0]*16, legal_actions=legal, immediate_rewards=dict(DOWN=0., LEFT=.25),
            fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT'),
            action_features=dict(DOWN=[0., 1., 0., 0., 0., 0.], LEFT=[0.]*6),
            action_components=dict(DOWN=[1., .3, .7], LEFT=[.25, .5, .5]),
            teacher_action_native='UP', oracle_action='UP', action_component_fractions={'unused': [[99, 1]]})
        if source % 2:
            row['immediate_rewards']['UP'] = .25
            row['action_map']['UP'] = 'LEFT'
            row['action_features']['UP'] = [0.]*6
            row['action_components']['UP'] = [.25, .5, .5]
        rows.append(row)
    extra = deepcopy(rows[0]); extra['root_id'] = 'synthetic:00:extra'
    extra['action_components']['DOWN'] = [.1, 1., 0.]
    return list(reversed(rows))+[extra, dict(life=1, root_id='other-teacher', source_id='ignored')]


def test_products_have_fixed_scale_order_and_read_only_six_or_26_feature_caches():
    from acfqp.science import controlled_predictive_mechanism_interactions_v188 as core

    pairs = [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5),
             (1, 1), (1, 2), (1, 3), (1, 4), (1, 5),
             (2, 2), (2, 3), (2, 4), (2, 5), (3, 3),
             (3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]
    bounds, aggregate = [1., 16., 12., 12., 12., 12.], [1., 16., 12., 6., 3., 0.]
    expected = aggregate+[aggregate[first]*aggregate[second]/math.sqrt(bounds[first]*bounds[second])
                          for first, second in pairs]
    root = dict(action_features=dict(DOWN=list(aggregate)))
    original, work, production_work = deepcopy(root), Counter(), Counter()
    features = audit.action_features_from_root(root, work, mode='INTERACT')
    production = core.action_features_from_root(root, production_work, mode='INTERACT')
    assert audit.same(features, production) and audit.same(production, features)
    assert root == original and work == production_work
    assert work == Counter(mechanism_aggregate_cache_hits=1, mechanism_base_feature_reads=6,
        mechanism_aggregate_values_copied=6, mechanism_product_feature_multiplications=20,
        mechanism_product_normalizer_reads=20, mechanism_product_normalizations=20,
        mechanism_feature_maps_derived=1)
    assert len(features['DOWN']) == 26 and features['DOWN'] == pytest.approx(expected)
    assert features['DOWN'][:6] == aggregate
    assert features['DOWN'][6] == 4. and features['DOWN'][11] == 16.
    assert features['DOWN'][16] == 12. and features['DOWN'][21] == 1.5
    assert features['DOWN'][23] == .75 and features['DOWN'][25] == 0.
    assert list(audit.PRODUCT_PAIRS) == list(core.PRODUCT_PAIRS) == pairs
    assert (0, 0) not in audit.PRODUCT_PAIRS
    linear_work, production_linear_work = Counter(), Counter()
    linear = audit.action_features_from_root(root, linear_work, mode='LINEAR')
    assert linear == core.action_features_from_root(root, production_linear_work, mode='LINEAR') == {'DOWN': aggregate}
    assert linear_work == production_linear_work
    assert linear_work == Counter(mechanism_aggregate_cache_hits=1, mechanism_base_feature_reads=6,
        mechanism_aggregate_values_copied=6, mechanism_feature_maps_derived=1)
    # The 26-value cache is sufficient without a board or a six-value source cache.
    cached_root = dict(interaction_features=dict(DOWN=list(expected)))
    cached_work, production_cached_work = Counter(), Counter()
    cached = audit.action_features_from_root(cached_root, cached_work, mode='INTERACT')
    assert audit.same(cached, core.action_features_from_root(cached_root, production_cached_work, mode='INTERACT'))
    assert cached_work == production_cached_work
    assert cached_work == Counter(mechanism_feature_cache_hits=1, mechanism_cached_feature_reads=26)
    cached_linear_work = Counter()
    assert audit.action_features_from_root(cached_root, cached_linear_work, mode='LINEAR') == {'DOWN': aggregate}
    assert cached_linear_work == Counter(mechanism_feature_cache_hits=1, mechanism_cached_feature_reads=6)
    assert not any('swipe' in key for key in work+linear_work+cached_work)
    cached['DOWN'][0] = 0.
    assert cached_root['interaction_features']['DOWN'] == expected


def test_both_controls_share_source_folds_actual_vector_selection_and_26_certified_fits(monkeypatch):
    from acfqp.science import controlled_predictive_mechanism_interactions_v188 as core

    rows = source_examples()
    production = core.fit_models(rows)
    observed, original_choose = [], audit.choose_action
    def observable_only(model, root, counts=None):
        observed.append((model['mode'], set(root)))
        assert not {'action_components', 'action_component_fractions', 'teacher_action_native', 'oracle_action'} & set(root)
        return original_choose(model, root, counts)
    monkeypatch.setattr(audit, 'choose_action', observable_only)
    actual, solver_work = audit.fit_models(rows, saved_selections=production['selections'],
                                         saved_models=production['models'])
    assert audit.same(actual, production) and audit.same(production, actual)
    assert actual['costs'] == production['costs']
    assert actual['cache_counts'] == production['cache_counts'] == dict(
        mechanism_aggregate_cache_hits=37, mechanism_base_feature_reads=552,
        mechanism_aggregate_values_copied=552, mechanism_product_feature_multiplications=1840,
        mechanism_product_normalizer_reads=1840, mechanism_product_normalizations=1840,
        mechanism_feature_maps_derived=37)
    assert set(actual['models']) == {'LINEAR', 'INTERACT'}
    assert Counter(mode for mode, _ in observed) == Counter(LINEAR=6*37, INTERACT=6*37)
    assert all(keys <= {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
        'immediate_rewards', 'fallback_action', 'action_map', 'action_features', 'interaction_features'} for _, keys in observed)
    sources = [f'DESIGN_SOURCE:{source:02d}' for source in range(36)]
    expected_tail = np.asarray([301/310, -11/62, 11/62])
    for mode, dimensions in (('LINEAR', 6), ('INTERACT', 26)):
        selection, model = actual['selections'][mode], actual['models'][mode]
        reference = production['selections'][mode]
        assert selection['costs'] == reference['costs']
        assert model['fit_counts'] == production['models'][mode]['fit_counts']
        assert selection['source_folds'] == [sources[::2], sources[1::2]]
        assert selection['lambdas'] == [0., .0001, .001, .01, .1, 1.]
        assert selection['selected_lambda'] == 0.
        assert selection['selected_utility'] == pytest.approx(571/720)
        assert [candidate['utility'] for candidate in selection['candidates']] == pytest.approx([571/720]*6)
        for index, fold in enumerate(selection['folds']):
            assert len(fold['train_sources']) == len(fold['heldout_sources']) == 18
            assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
            assert fold['design']['source_ids'] == fold['train_sources']
            assert fold['design']['shape'] == [54 if index == 0 else 19, dimensions]
            for key in ('prepare_counts', 'feature_counts', 'work', 'action_root_ids',
                        'pair_root_ids', 'connected_components'):
                assert fold['design'][key] == reference['folds'][index]['design'][key]
        assert len(selection['folds'][0]['design']['action_root_ids']['UP']) == 18
        assert selection['folds'][1]['design']['action_root_ids']['UP'] == []
        assert selection['folds'][1]['design']['pair_root_ids']['DOWN|UP'] == []
        zero = selection['candidates'][0]
        first, second = [result['choices'] for result in zero['fold_results']]
        assert all(choice['decision']['canonical_action'] == 'DOWN' for choice in first)
        assert all(choice['decision']['canonical_action'] == 'LEFT' and choice['decision']['fallback']
            and choice['decision']['reason'] == 'insufficient_action_support' for choice in second)
        extra = next(choice for choice in first if choice['root_id'] == 'synthetic:00:extra')
        assert extra['components'] == [.1, 1., 0.] and extra['utility'] == pytest.approx(-.9)
        group = next(group for group in zero['group_records'] if group['source_id'] == sources[0])
        assert group['roots'] == 2 and group['components'] == pytest.approx([.55, .65, .35])
        assert group['utility'] == pytest.approx(.25)
        assert sum(choice['utility'] for choice in first+second)/37 == pytest.approx(28.8/37)
        assert selection['selected_utility'] != pytest.approx(28.8/37)
        expected = np.zeros((dimensions, 3))
        expected[1] = expected_tail if mode == 'LINEAR' else expected_tail*256/257
        if mode == 'INTERACT':
            expected[11] = expected_tail*16/257
        assert np.asarray(model['coefficients']) == pytest.approx(expected, abs=1e-12)
        assert model['constants']['columns'] == dimensions and model['rank'] == 1
        assert len(model['root_ids']) == 37 and len(model['fit_residuals']) == 73
        assert model['loss'] == pytest.approx(537/310)
        assert model['root_mean_loss'] == pytest.approx(537/11470)
        assert model['objective'] == pytest.approx(model['root_mean_loss']) and model['penalty'] == 0.
        assert all(sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.) for label in model['fit_labels'])
        assert all(len(record['components']) == 3 for record in model['fit_residuals'])
        assert selection['costs']['ridge_design_preparations'] == selection['costs']['ridge_svd_decompositions'] == 3
        assert selection['costs']['ridge_coefficient_filters'] == selection['costs']['ridge_predictors_fitted'] == 13
        assert selection['costs']['mechanism_feature_cache_hits'] == 296
        assert selection['costs']['mechanism_cached_feature_reads'] == dimensions*736
    assert actual['costs']['ridge_design_preparations'] == actual['costs']['ridge_svd_decompositions'] == 6
    assert actual['costs']['ridge_coefficient_filters'] == actual['costs']['ridge_predictors_fitted'] == 26
    assert actual['costs']['new_predictors_fitted'] == 26
    assert solver_work['zero_minimum_norm_lstsq_solves'] == 6
    assert solver_work['positive_column_normal_solves'] == 20
    assert solver_work['independent_coefficient_arrays_checked'] == solver_work['independent_coefficient_arrays_passed'] == 26


def test_interaction_decisions_and_full_vector_summary_keep_replica_losses_and_concentration():
    from acfqp.science import controlled_predictive_mechanism_interactions_v188 as core

    model = dict(life=0, mode='INTERACT', coefficients=[[0.]*3 for _ in range(26)],
        action_root_ids={action: ['support:0', 'support:1', 'support:2', 'support:3'] for action in audit.ACTIONS},
        pair_root_ids={f'{first}|{second}': ['support:0', 'support:1', 'support:2', 'support:3']
                       for first, second in combinations(audit.ACTIONS, 2)}, connected_components=[list(audit.ACTIONS)])
    model['coefficients'][11] = [16., 12.8, 0.]
    current = dict(life=0, legal_actions=['LEFT', 'DOWN'], immediate_rewards=dict(DOWN=.25, LEFT=1.),
        fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT'),
        action_features=dict(DOWN=[0., 1., 0., 0., 0., 0.], LEFT=[0.]*6),
        action_components=dict(DOWN=[999., 0., 1.], LEFT=[0., 1., 0.]))
    decision, production = audit.choose_action(model, current), core.choose_action(model, current)
    assert audit.same(decision, production) and audit.same(production, decision)
    assert decision['work'] == production['work'] and decision['feature_work'] == production['feature_work']
    assert decision['predicted_components']['DOWN'] == pytest.approx([1.25, .8, 0.])
    assert decision['predicted_components']['LEFT'] == pytest.approx([1., 0., 0.])
    assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
    success = deepcopy(model); success['coefficients'][11] = [0., 0., 16.]
    assert audit.choose_action(success, current)['canonical_action'] == 'DOWN'
    linear = deepcopy(model); linear.update(mode='LINEAR', coefficients=[[0.]*3 for _ in range(6)])
    assert audit.choose_action(linear, current)['canonical_action'] == 'LEFT'
    success['action_root_ids']['DOWN'] = []
    fallback = audit.choose_action(success, current)
    assert fallback['fallback'] is True and fallback['canonical_action'] == 'LEFT'
    assert fallback['reason'] == 'insufficient_action_support'

    roots = dict(SOURCE=[dict(source_id=f'source:{index//2}') for index in range(4)], TARGET=[])
    labels, choices = [], {name: [] for name in (*audit.MODEL_NAMES, 'FALLBACK')}
    for index, (replica, gain) in enumerate(((0, 4.), (0, -1.), (0, 0.), (1, -1.))):
        identity = f'synthetic-target:{index}'
        roots['TARGET'].append(dict(root_id=identity, replica=replica, stratum=index, legal_actions=['DOWN', 'LEFT']))
        labels.append(dict(root_id=identity, oracle_action='LEFT',
                           action_components=dict(DOWN=[2., .5, 0.], LEFT=[gain+1., 0., .5])))
        for name, selected in choices.items():
            selected.append(dict(root_id=identity, canonical_action='LEFT' if name == 'INTERACT' else 'DOWN',
                fallback=name == 'INTERACT' and index == 1,
                decision=dict(predicted_components=dict(LEFT=[999., 0., 0.]))))
    grid = (0., .0001, .001, .01, .1, 1.)
    selection = dict(LINEAR=dict(selected_lambda=.1, selected_utility=.5,
        candidates=[dict(lambda_value=value, utility=utility) for value, utility in zip(grid, (.1, .2, .3, .4, .5, .45))]),
        INTERACT=dict(selected_lambda=.01, selected_utility=.8,
        candidates=[dict(lambda_value=value, utility=utility) for value, utility in zip(grid, (.3, .4, .5, .8, .6, .7))]))
    fitted = dict(LINEAR=dict(constants=dict(columns=6), rank=1, root_mean_loss=.25),
                  INTERACT=dict(constants=dict(columns=26), rank=2, root_mean_loss=.125))
    result = audit.summarize(roots, labels, choices, selection, fitted)
    assert result['schema'] == 'acfqp.mechanism_interactions.v188.summary' and result['complete'] is True
    assert result['roots'] == 4 and result['SOURCE']['roots'] == 4 and result['SOURCE']['design_groups'] == 2
    assert result['SOURCE']['learners'] == {name: dict(selected_lambda=selection[name]['selected_lambda'],
        source_heldout_utility=selection[name]['selected_utility'], source_selection=selection[name]['candidates'],
        columns=fitted[name]['constants']['columns'], source_rank=fitted[name]['rank'],
        source_root_mean_loss=fitted[name]['root_mean_loss']) for name in ('LINEAR', 'INTERACT')}
    assert set(result['models']) == set((*audit.MODEL_NAMES, 'FALLBACK', 'ORACLE'))
    assert result['models']['INTERACT']['components'] == pytest.approx([1.5, 0., .5])
    assert result['models']['INTERACT']['utility'] == pytest.approx(2.)
    assert result['models']['INTERACT']['positive_regret_roots'] == 2 and result['models']['INTERACT']['fallback_roots'] == 1
    assert result['models']['LINEAR']['components'] == pytest.approx([2., .5, 0.])
    assert result['models']['ORACLE']['components'] == pytest.approx([11/4, 3/8, 1/8])
    assert result['root_records'][2]['models']['ORACLE']['action'] == 'DOWN'
    assert set(result['comparisons']) == {'INTERACT_MINUS_'+name for name in ('LINEAR', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')}
    for effect in result['comparisons'].values():
        assert effect['components'] == pytest.approx([-.5, -.5, .5]) and effect['utility'] == pytest.approx(.5)
        assert (effect['improved_roots'], effect['worsened_roots'], effect['equal_value_roots']) == (1, 2, 1)
        assert (effect['action_changes'], effect['new_error_roots'], effect['resolved_error_roots']) == (4, 2, 1)
        assert (effect['positive_gain_sum'], effect['negative_gain_sum']) == pytest.approx((4., -2.))
        assert effect['largest_gain_root'] == 'synthetic-target:0' and effect['largest_gain'] == 4.
        assert effect['largest_gain_share_of_positive'] == 1.
        assert effect['largest_loss_root'] == 'synthetic-target:1' and effect['largest_loss'] == -1.
        assert [row['utility'] for row in effect['root_records']] == pytest.approx([4., -1., 0., -1.])
    assert [(row['replica'], row['roots']) for row in result['replicas']] == [(0, 3), (1, 1)]
    assert [row['comparisons']['INTERACT_MINUS_LINEAR']['utility'] for row in result['replicas']] == pytest.approx([1., -1.])
    assert result['whole_cohort_positive_vs_linear_ridge_old_shared'] is True
    assert result['all_replicas_positive_vs_linear_ridge_old_shared'] is False
    assert result['oracle_minus_one'] == pytest.approx(1.) and result['oracle_minus_interact'] == pytest.approx(.5)
    assert result['headroom_closed_fraction'] == pytest.approx(.5)
    assert 'feature_coverage' not in result
    assert (result['new_environment_samples'], result['new_source_games'],
            result['new_native_weight_updates'], result['new_predictors_fitted']) == (0, 0, 0, 26)
