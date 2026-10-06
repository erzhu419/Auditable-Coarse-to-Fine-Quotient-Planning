"""Three pure synthetic witnesses for occurrence pooling and SOURCE selection."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
import math

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_position_shared_v187 as audit


def cached_layout(board=None, active=False):
    board = list(board if board is not None else [0]*16)
    tokens = [['cell', cell, value] for cell, value in enumerate(board)]
    tokens += [['horizontal', 4*row+column, board[4*row+column], board[4*row+column+1]]
               for row in range(4) for column in range(3)]
    tokens += [['vertical', 4*row+column, board[4*row+column], board[4*(row+1)+column]]
               for row in range(3) for column in range(4)]
    return dict(aggregate=[float(active), 0., 0., 0., 0., 0.], tokens=tokens)


def source_examples():
    rows = []
    for source in range(36):
        board = [1+source % 10]+[0]*15
        legal = ['LEFT', 'DOWN', 'UP'] if source % 2 else ['LEFT', 'DOWN']
        row = dict(root_id=f'synthetic:{source:02d}', source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
            canonical_board=[0]*16, legal_actions=legal,
            immediate_rewards=dict(DOWN=0., LEFT=.25), fallback_action='LEFT',
            action_map=dict(DOWN='UP', LEFT='RIGHT'),
            layout_features=dict(DOWN=cached_layout(board, True), LEFT=cached_layout(board)),
            action_components=dict(DOWN=[1., .3, .7], LEFT=[.25, .5, .5]),
            teacher_action_native='UP', oracle_action='UP', action_component_fractions={'unused': [[99, 1]]})
        if source % 2:
            row['immediate_rewards']['UP'] = .25
            row['action_map']['UP'] = 'LEFT'
            row['layout_features']['UP'] = cached_layout(board)
            row['action_components']['UP'] = [.25, .5, .5]
        rows.append(row)
    extra = deepcopy(rows[0])
    extra.update(root_id='synthetic:00:extra')
    extra['action_components']['DOWN'] = [.1, 1., 0.]
    return list(reversed(rows))+[extra, dict(life=1, root_id='other-teacher', source_id='ignored')]


def test_projection_preserves_zero_order_axis_occurrences_and_uses_frozen_cache():
    from acfqp.science import controlled_predictive_position_shared_v187 as core

    board = [1, 0, 2, 0]+[0]*12
    root = dict(layout_features={'DOWN': cached_layout(board)})
    original = deepcopy(root)
    work, production_work = Counter(), Counter()
    features = audit.action_features_from_root(root, work)
    production = core.action_features_from_root(root, production_work)
    assert audit.same(features, production) and audit.same(production, features)
    assert root == original
    projected = features['DOWN']['tokens']
    assert projected == [[token[0], *token[2:]] for token in original['layout_features']['DOWN']['tokens']]
    assert projected[:16] == [['cell', rank] for rank in board]
    assert projected[16:19] == [['horizontal', 1, 0], ['horizontal', 0, 2], ['horizontal', 2, 0]]
    assert projected[28] == ['vertical', 1, 0]
    assert len(projected) == 40 and projected.count(['cell', 0]) == 14
    assert projected.count(['horizontal', 0, 0]) == 9 and projected.count(['vertical', 0, 0]) == 10
    assert work == production_work == Counter(pool_aggregate_values_copied=6,
        pool_token_occurrences_read=40, pool_token_kind_reads=40, pool_rank_values_copied=64,
        pool_positions_discarded=40, pool_feature_maps_derived=1)
    vocabulary = [list(token) for token in sorted({tuple(token) for token in projected}
        -{('cell', 2), ('vertical', 0, 0)})]
    indexed = {tuple(token): column+6 for column, token in enumerate(vocabulary)}
    encode_work, production_encode_work = Counter(), Counter()
    encoded, coverage = audit.encode_action(features['DOWN'], indexed, encode_work)
    production_encoded, production_coverage = core._encode(features['DOWN'], indexed, production_encode_work)
    assert audit.same(encoded, production_encoded) and audit.same(production_encoded, encoded)
    assert coverage == production_coverage == dict(total_tokens=40, known_tokens=29, unknown_tokens=11)
    assert encoded[indexed['cell', 0]] == pytest.approx(14*.25)
    assert encoded[indexed['cell', 1]] == pytest.approx(.25)
    assert encoded[indexed['horizontal', 0, 0]] == pytest.approx(9/math.sqrt(12))
    assert encoded[indexed['horizontal', 1, 0]] == pytest.approx(1/math.sqrt(12))
    assert encoded[indexed['vertical', 1, 0]] == pytest.approx(1/math.sqrt(12))
    assert set(encoded) == set(range(6)) | set(indexed.values())
    assert encode_work == production_encode_work == Counter(token_lookups=40,
        unknown_token_entries=11, known_token_entries=29, token_weight_loads=29,
        pool_occurrence_accumulations=29, pool_duplicate_occurrences=21,
        encoded_actions=1, aggregate_values_read=6)
    # A pooled cache alone is sufficient: no board or old layout is available to swipe.
    cached_root = dict(pooled_features=deepcopy(features))
    cache_work, production_cache_work = Counter(), Counter()
    cached = audit.action_features_from_root(cached_root, cache_work)
    assert audit.same(cached, core.action_features_from_root(cached_root, production_cache_work))
    assert cache_work == production_cache_work == Counter(pool_feature_cache_hits=1,
        pool_cached_aggregate_reads=6, pool_cached_token_occurrences=40, pool_cached_token_values=104)
    cached['DOWN']['tokens'][0][1] = 10
    assert cached_root['pooled_features'] == features


def test_36_group_selection_rebuilds_fold_vocab_support_full_vector_sse_and_costs(monkeypatch):
    from acfqp.science import controlled_predictive_position_shared_v187 as core

    rows = source_examples()
    production = core.select_regularization(rows)
    observed_keys, original_choose = [], audit.choose_action
    def observable_only(model, root, counts=None):
        observed_keys.append(set(root))
        assert not {'action_components', 'action_component_fractions', 'teacher_action_native', 'oracle_action'} & set(root)
        return original_choose(model, root, counts)
    monkeypatch.setattr(audit, 'choose_action', observable_only)
    actual, solver_work = audit.select_regularization(rows, saved_selection=production,
                                                      saved_model=production['model'])
    assert audit.same(actual, production) and audit.same(production, actual)
    assert actual['costs'] == production['costs']
    assert actual['model']['fit_counts'] == production['model']['fit_counts']
    assert actual['model']['feature_counts'] == production['model']['feature_counts']
    assert actual['model']['encoder_counts'] == production['model']['encoder_counts']
    assert len(observed_keys) == 6*37
    assert all(keys <= {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
        'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'pooled_features'} for keys in observed_keys)
    sources = [f'DESIGN_SOURCE:{source:02d}' for source in range(36)]
    assert actual['source_folds'] == [sources[::2], sources[1::2]]
    assert [len(fold) for fold in actual['source_folds']] == [18, 18]
    assert actual['lambdas'] == [0., .0001, .001, .01, .1, 1.]
    assert actual['selected_lambda'] == 0.
    assert actual['selected_utility'] == pytest.approx(571/720)
    assert [candidate['utility'] for candidate in actual['candidates']] == pytest.approx([571/720]*6)
    for index, fold in enumerate(actual['folds']):
        assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
        assert fold['design']['source_ids'] == fold['train_sources']
        assert set(fold['design']['root_ids']).isdisjoint(row['root_id'] for row in rows
            if row['life'] == 0 and row['source_id'] in fold['heldout_sources'])
        for key in ('prepare_counts', 'feature_counts', 'encoder_counts', 'work',
                    'action_root_ids', 'pair_root_ids', 'connected_components'):
            assert fold['design'][key] == production['folds'][index]['design'][key]
    first, second = actual['folds']
    assert ['cell', 1] not in first['design']['vocabulary'] and ['cell', 2] in first['design']['vocabulary']
    assert first['design']['shape'] == [54, 24] and second['design']['shape'] == [19, 24]
    assert len(first['design']['action_root_ids']['UP']) == 18
    assert second['design']['action_root_ids']['UP'] == []
    assert second['design']['pair_root_ids']['DOWN|UP'] == []
    zero = actual['candidates'][0]
    first_choices = zero['fold_results'][0]['choices']
    second_choices = zero['fold_results'][1]['choices']
    assert all(choice['decision']['canonical_action'] == 'DOWN' for choice in first_choices)
    assert all(choice['decision']['canonical_action'] == 'LEFT' and choice['decision']['fallback']
        and choice['decision']['reason'] == 'insufficient_action_support' for choice in second_choices)
    assert all(entry['unknown_tokens'] == 3 for choice in first_choices
        for entry in choice['decision']['coverage'].values())
    extra = next(choice for choice in first_choices if choice['root_id'] == 'synthetic:00:extra')
    assert extra['components'] == [.1, 1., 0.] and extra['utility'] == pytest.approx(-.9)
    group_zero = next(group for group in zero['group_records'] if group['source_id'] == sources[0])
    assert group_zero['roots'] == 2 and group_zero['components'] == pytest.approx([.55, .65, .35])
    assert group_zero['utility'] == pytest.approx(.25)
    assert sum(choice['utility'] for choice in first_choices+second_choices)/37 == pytest.approx(28.8/37)
    assert actual['selected_utility'] != pytest.approx(28.8/37)
    model = actual['model']
    assert model['representation'] == 'POSITION_SHARED_OCCURRENCE_SUM'
    assert model['rank'] == 1 and model['constants']['columns'] == 39
    assert np.asarray(model['coefficients'])[0] == pytest.approx([301/310, -11/62, 11/62], abs=1e-12)
    assert np.asarray(model['coefficients'])[1:].ravel().tolist() == pytest.approx([0.]*114, abs=1e-12)
    assert model['loss'] == pytest.approx(537/310)
    assert model['root_mean_loss'] == pytest.approx(537/11470)
    assert model['objective'] == pytest.approx(model['root_mean_loss']) and model['penalty'] == 0.
    assert len(model['fit_residuals']) == 73 and len(model['root_ids']) == 37
    assert all(sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.) for label in model['fit_labels'])
    assert all(len(row['components']) == 3 for row in model['fit_residuals'])
    assert actual['costs']['ridge_design_preparations'] == actual['costs']['ridge_svd_decompositions'] == 3
    assert actual['costs']['ridge_coefficient_filters'] == actual['costs']['ridge_predictors_fitted'] == 13
    assert actual['costs']['new_predictors_fitted'] == 13
    assert actual['costs']['source_fold_assignments'] == 36 and actual['costs']['regularization_candidates'] == 6
    assert actual['costs']['regularization_group_mean_reads'] == 216
    assert actual['costs']['regularization_score_comparisons'] == 6
    assert solver_work['zero_minimum_norm_lstsq_solves'] == 3 and solver_work['positive_column_normal_solves'] == 10
    assert solver_work['independent_coefficient_arrays_checked'] == solver_work['independent_coefficient_arrays_passed'] == 13


def test_choices_and_summary_use_full_consequences_rewards_and_replica_gain_records():
    from acfqp.science import controlled_predictive_position_shared_v187 as core

    vocabulary = [['cell', 0], ['horizontal', 0, 0], ['vertical', 0, 0]]
    model = dict(life=0, vocabulary=vocabulary, coefficients=[[1., .8, 0.]]+[[0.]*3 for _ in range(8)],
        action_root_ids={action: ['support:0', 'support:1', 'support:2', 'support:3'] for action in audit.ACTIONS},
        pair_root_ids={f'{first}|{second}': ['support:0', 'support:1', 'support:2', 'support:3']
                       for first, second in combinations(audit.ACTIONS, 2)}, connected_components=[list(audit.ACTIONS)])
    current = dict(life=0, legal_actions=['LEFT', 'DOWN'], immediate_rewards=dict(DOWN=.25, LEFT=1.),
        fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT'),
        layout_features=dict(DOWN=cached_layout(active=True), LEFT=cached_layout()),
        action_components=dict(DOWN=[999., 0., 1.], LEFT=[0., 1., 0.]))
    decision = audit.choose_action(model, current)
    production = core.choose_action(model, current)
    assert audit.same(decision, production) and audit.same(production, decision)
    assert decision['work'] == production['work'] and decision['feature_work'] == production['feature_work']
    assert decision['predicted_components']['DOWN'] == pytest.approx([1.25, .8, 0.])
    assert decision['predicted_components']['LEFT'] == pytest.approx([1., 0., 0.])
    assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
    success = deepcopy(model); success['coefficients'][0] = [0., 0., 1.]
    assert audit.choose_action(success, current)['canonical_action'] == 'DOWN'
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
            selected.append(dict(root_id=identity, canonical_action='LEFT' if name == 'POOL' else 'DOWN',
                fallback=name == 'POOL' and index == 1, decision=dict(
                    predicted_components=dict(LEFT=[999., 0., 0.]),
                    coverage={'LEFT': dict(total_tokens=40, known_tokens=39, unknown_tokens=1)} if name == 'POOL' else {})))
    selection = dict(selected_lambda=0., selected_utility=.8,
        candidates=[dict(lambda_value=value, utility=.8) for value in (0., .0001, .001, .01, .1, 1.)])
    fitted = dict(vocabulary=vocabulary, constants=dict(columns=9), rank=1, root_mean_loss=.125)
    result = audit.summarize(roots, labels, choices, selection, fitted)
    assert result['schema'] == 'acfqp.position_shared.v187.summary' and result['complete'] is True
    assert result['roots'] == 4
    assert result['SOURCE'] == dict(roots=4, design_groups=2, selected_lambda=0., source_heldout_utility=.8,
        source_selection=[dict(lambda_value=value, utility=.8) for value in (0., .0001, .001, .01, .1, 1.)],
        vocabulary_tokens=3, columns=9, source_rank=1, source_root_mean_loss=.125)
    assert set(result['models']) == set((*audit.MODEL_NAMES, 'FALLBACK', 'ORACLE'))
    assert result['models']['POOL']['components'] == pytest.approx([1.5, 0., .5])
    assert result['models']['POOL']['utility'] == pytest.approx(2.)
    assert result['models']['POOL']['positive_regret_roots'] == 2 and result['models']['POOL']['fallback_roots'] == 1
    assert result['models']['ORACLE']['components'] == pytest.approx([11/4, 3/8, 1/8])
    assert result['root_records'][2]['models']['ORACLE']['action'] == 'DOWN'
    assert set(result['comparisons']) == {'POOL_MINUS_'+name for name in ('RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')}
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
    assert [row['comparisons']['POOL_MINUS_RIDGE']['utility'] for row in result['replicas']] == pytest.approx([1., -1.])
    assert result['whole_cohort_positive_vs_ridge_and_old_shared'] is True
    assert result['all_replicas_positive_vs_ridge_and_old_shared'] is False
    assert result['oracle_minus_one'] == pytest.approx(1.) and result['oracle_minus_pool'] == pytest.approx(.5)
    assert result['headroom_closed_fraction'] == pytest.approx(.5)
    assert result['feature_coverage'] == dict(total_tokens=160, known_tokens=156, unknown_tokens=4)
    assert (result['new_environment_samples'], result['new_source_games'],
            result['new_native_weight_updates'], result['new_predictors_fitted']) == (0, 0, 0, 13)
