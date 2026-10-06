"""Pure witnesses for position sharing, occurrence sums and SOURCE-only learning."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from math import sqrt

import numpy as np
import pytest

from acfqp.science import controlled_predictive_position_shared_v187 as core


TAIL = np.asarray([1., -.2, .2])


def layout(board=None, active=False):
    board = [0]*16 if board is None else board
    return dict(aggregate=[float(active), 0., 0., 0., 0., 0.],
        tokens=[['cell', i, rank] for i, rank in enumerate(board)]
        + [['horizontal', 4*r+c, board[4*r+c], board[4*r+c+1]] for r in range(4) for c in range(3)]
        + [['vertical', 4*r+c, board[4*r+c], board[4*(r+1)+c]] for r in range(3) for c in range(4)])


def root(root_id='synthetic', source=0):
    return dict(root_id=root_id, source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'],
        immediate_rewards=dict(DOWN=0., LEFT=0.), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT'),
        layout_features=dict(DOWN=layout(active=True), LEFT=layout()),
        action_features=dict(DOWN=[1., 0., 0., 0., 0., 0.], LEFT=[0.]*6),
        action_components=dict(DOWN=[1., .3, .7], LEFT=[0., .5, .5]))


def examples():
    return [root(f'synthetic:{source:02d}:{index}', source)
            for source in range(36) for index in range(3 if source == 3 else 4)]


def fit(rows, lambda_value):
    design = core.prepare_design(rows)
    costs = Counter(design['work'])
    decomposition = core.ridge._decompose(design, costs)
    fitted = core.ridge._filter(design, decomposition, lambda_value)
    payload = core.ridge._model(design, decomposition, fitted, lambda_value)
    payload.update(schema=core.SCHEMA+'.model', mode='POOL', representation=core.REPRESENTATION)
    return payload, design


def inference_models():
    support = dict(action_root_ids={a: ['a', 'b', 'c', 'd'] for a in core.ACTIONS},
        pair_root_ids={f'{a}|{b}': ['a', 'b', 'c', 'd'] for a, b in combinations(core.ACTIONS, 2)},
        connected_components=[list(core.ACTIONS)])
    vocabulary = [list(t) for t in sorted({tuple(t) for t in
        core.action_features_from_root(root())['DOWN']['tokens']})]
    coefficients = [[0., 0., 0.] for _ in range(6+len(vocabulary))]
    coefficients[0][0] = 1.
    models = dict(POOL=dict(life=0, vocabulary=vocabulary, coefficients=coefficients, **deepcopy(support)))
    for name in ('RIDGE', 'LAYOUT'):
        weights = [[0., 0., 0.] for _ in range(46)]
        weights[0][0] = 1.
        models[name] = dict(life=0, vocabulary=sorted(layout()['tokens'], key=tuple),
                            coefficients=weights, **deepcopy(support))
    for name in ('SHARED', 'OLD_SHARED'):
        weights = [[0., 0., 0.] for _ in range(6)]
        weights[0][0] = -1. if name == 'OLD_SHARED' else 1.
        models[name] = dict(life=0, coefficients=weights, **deepcopy(support))
    leaf = dict(leaf_id=0, coefficients={a: [0., 0., 0.] for a in core.ACTIONS}, **deepcopy(support))
    models['ONE'] = dict(life=0, mode='ONE_LATE', groups={'ALL': 0}, leaves=[leaf])
    return models


def test_occurrences_accumulate_and_location_sharing_preserves_axis_order_and_zeros():
    observed = root()
    work = Counter()
    pooled = core.action_features_from_root(observed, work)['LEFT']
    vocabulary = [list(t) for t in sorted({tuple(t) for t in pooled['tokens']})]
    indexed = core._index(vocabulary, work)
    encoded, coverage = core._encode(pooled, indexed, work)
    assert vocabulary == [['cell', 0], ['horizontal', 0, 0], ['vertical', 0, 0]]
    assert encoded[indexed['cell', 0]] == 4.  # 16 occurrences, not one overwritten token.
    assert encoded[indexed['horizontal', 0, 0]] == pytest.approx(sqrt(12))
    assert encoded[indexed['vertical', 0, 0]] == pytest.approx(sqrt(12))
    assert coverage == dict(known_tokens=40, unknown_tokens=0, total_tokens=40)
    assert work['pool_occurrence_accumulations'] == 40 and work['pool_duplicate_occurrences'] == 37
    first, second = [0]*16, [0]*16
    first[5:7], second[9:11] = [1, 2], [1, 2]
    a = core.action_features_from_root(dict(layout_features={'DOWN': layout(first)}))['DOWN']
    b = core.action_features_from_root(dict(layout_features={'DOWN': layout(second)}))['DOWN']
    assert layout(first)['tokens'] != layout(second)['tokens']
    assert Counter(map(tuple, a['tokens'])) == Counter(map(tuple, b['tokens']))
    flipped = core.action_features_from_root(dict(layout_features={'DOWN': layout([0]*5+[2, 1]+[0]*9)}))['DOWN']
    assert Counter(map(tuple, a['tokens'])) != Counter(map(tuple, flipped['tokens']))
    keys = set(map(tuple, a['tokens']))
    assert ('horizontal', 1, 2) in keys and ('vertical', 0, 1) in keys
    assert ('horizontal', 0, 1) in keys and ('cell', 0) in keys
    assert work['pool_positions_discarded'] == 80 and 'layout_ground_swipe_calls' not in work


def test_complete_pair_vectors_root_weights_and_ridge_scale_are_unchanged():
    rows = [root(f'weighted:{i}') for i in range(8)]
    for index, observed in enumerate(rows):
        observed['immediate_rewards'] = dict(DOWN=(index % 3)/2048., LEFT=1/2048.)
        offset = np.asarray([3.+index, .5, .5])
        down, left = offset+TAIL, offset.copy()
        down[0] += observed['immediate_rewards']['DOWN']; left[0] += observed['immediate_rewards']['LEFT']
        observed['action_components'] = dict(DOWN=down.tolist(), LEFT=left.tolist())
        if index % 2:
            observed['legal_actions'].append('UP')
            observed['layout_features']['UP'] = layout()
            observed['immediate_rewards']['UP'] = observed['immediate_rewards']['LEFT']
            observed['action_components']['UP'] = left.tolist()
            observed['action_map']['UP'] = 'DOWN'
    zero, design = fit(rows, 0.)
    ridge, _ = fit(rows, 1.)
    assert zero['rank'] == 1 and zero['coefficients'][0] == pytest.approx(TAIL)
    # Four two-action roots plus four three-action roots: X'X=20/3, N=8.
    assert ridge['coefficients'][0] == pytest.approx(TAIL*5/11)
    assert ridge['penalty'] == pytest.approx(np.sum((TAIL*5/11)**2))
    assert ridge['objective'] == pytest.approx(ridge['loss']/8+ridge['penalty'])
    assert design['X'].shape == (16, 9) and design['Y'].shape == (16, 3)
    for label in design['fit_labels']:
        assert sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.)
        for pair in label['pairs']:
            expected = TAIL if pair['actions'][0] == 'DOWN' else np.zeros(3)
            assert pair['components'] == pytest.approx(expected)
    shifted = deepcopy(rows)
    for observed in shifted:
        for action in observed['legal_actions']:
            observed['action_components'][action] = (np.asarray(observed['action_components'][action])+[100., .1, -.1]).tolist()
    same, _ = fit(shifted, 1.)
    assert np.asarray(same['coefficients']) == pytest.approx(np.asarray(ridge['coefficients']), abs=1e-12)


def test_unknown_occurrences_are_zero_without_novelty_fallback_and_reward_is_added_once():
    observed, model = root(), inference_models()['POOL']
    model['coefficients'][0] = (TAIL*.5).tolist()
    observed['layout_features']['DOWN'] = layout([10]*16, active=True)
    observed['immediate_rewards']['LEFT'] = .8
    observed.update(oracle_action='DOWN', action_component_fractions={'secret': []})
    frozen = deepcopy(model)
    decision = core.choose_action(model, observed)
    assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
    assert not decision['fallback'] and decision['support']['complete']
    assert decision['coverage']['DOWN'] == dict(known_tokens=0, unknown_tokens=40, total_tokens=40)
    assert decision['coverage']['LEFT'] == dict(known_tokens=40, unknown_tokens=0, total_tokens=40)
    assert decision['predicted_components']['DOWN'] == pytest.approx([.5, -.1, .1])
    assert decision['predicted_components']['LEFT'] == pytest.approx([.8, 0., 0.])
    assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx([-.3, -.1, .1])
    observed['action_components'] = {'DOWN': [999., 0., 1.], 'LEFT': [-999., 1., 0.]}
    assert core.choose_action(model, observed) == decision and model == frozen
    unsupported = deepcopy(model)
    unsupported['action_root_ids']['LEFT'] = ['a', 'b', 'c']
    assert core.choose_action(unsupported, observed)['reason'] == 'insufficient_action_support'
    unsupported['action_root_ids']['LEFT'].append('d')
    unsupported['connected_components'] = [['DOWN'], ['LEFT'], ['RIGHT'], ['UP']]
    assert core.choose_action(unsupported, observed)['reason'] == 'disconnected_required_actions'
    observed['legal_actions'] = ['DOWN']; observed['fallback_action'] = 'DOWN'
    unsupported['action_root_ids']['DOWN'] = []
    forced = core.choose_action(unsupported, observed)
    assert forced['reason'] == 'single_legal_action' and not forced['fallback']


def test_fold_vocab_support_and_label_boundary_with_only_three_svd_thirteen_filters(monkeypatch):
    rows = examples()
    for observed in rows:
        source = int(observed['source_id'].rsplit(':', 1)[1])
        board = ([1, 2] if source % 2 == 0 else [2, 1])+[0]*14
        observed['layout_features'] = dict(DOWN=layout(board, True), LEFT=layout(board))
        observed.update(oracle_action='RIGHT', teacher_action_native='RIGHT',
                        action_component_fractions={'secret': []})
        if source % 2 == 0:
            observed['legal_actions'].append('RIGHT')
            observed['layout_features']['RIGHT'] = layout(board)
            observed['immediate_rewards']['RIGHT'] = 0.
            observed['action_components']['RIGHT'] = list(observed['action_components']['LEFT'])
            observed['action_map']['RIGHT'] = 'LEFT'
    before = deepcopy(rows)
    calls = dict(svd=0, filters=0)
    svd, filtering, chooser = core.ridge.np.linalg.svd, core.ridge._filter, core.choose_action
    def counted_svd(*args, **kwargs):
        calls['svd'] += 1
        return svd(*args, **kwargs)
    def counted_filter(*args, **kwargs):
        calls['filters'] += 1
        return filtering(*args, **kwargs)
    allowed = {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
               'immediate_rewards', 'fallback_action', 'action_map', 'layout_features'}
    def observed_only(payload, observed, counts=None):
        assert set(observed) == allowed
        return chooser(payload, observed, counts)
    def forbidden(*args, **kwargs):
        raise AssertionError('position sharing repeated a ground swipe')
    monkeypatch.setattr(core.ridge.np.linalg, 'svd', counted_svd)
    monkeypatch.setattr(core.ridge, '_filter', counted_filter)
    monkeypatch.setattr(core, 'choose_action', observed_only)
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', forbidden)
    selection = core.select_regularization(rows+[dict(life=1, root_id='unread-other-history')])
    assert rows == before
    assert calls == dict(svd=3, filters=13)
    assert selection['costs']['ridge_predictors_fitted'] == selection['costs']['new_predictors_fitted'] == 13
    assert selection['costs']['heldout_action_vector_reads'] == 6*143
    assert len(selection['source_folds'][0]) == len(selection['source_folds'][1]) == 18
    assert selection['selected_lambda'] == 0.  # Every grid value makes the same supported actions.
    assert selection['model']['mode'] == 'POOL' and selection['model']['representation'] == core.REPRESENTATION
    assert len(selection['model']['root_ids']) == 143
    assert selection['model']['source_root_counts']['DESIGN_SOURCE:03'] == 3
    assert 'unread-other-history' not in selection['model']['root_ids']
    assert all('pooled_features' in observed for observed in selection['model']['training_outcomes'])
    for fold in selection['folds']:
        design = fold['design']
        assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
        assert set(design['source_ids']) == set(fold['train_sources'])
        heldout_pair = ['horizontal', 1, 2] if fold['fold'] == 0 else ['horizontal', 2, 1]
        assert heldout_pair not in design['vocabulary']
        assert 'X' not in design and 'Y' not in design
        assert 'right' not in fold['decomposition'] and 'left' not in fold['decomposition']
    for candidate in selection['candidates']:
        for choice in candidate['fold_results'][0]['choices']:
            assert choice['decision']['fallback'] and choice['decision']['canonical_action'] == 'LEFT'
            assert choice['decision']['support']['action_root_counts']['RIGHT'] == 0


def test_selection_uses_equal_source_actual_utility_instead_of_fit_sse():
    rows = examples()
    for observed in rows:
        good = observed['root_id'].endswith(':0')
        observed['immediate_rewards'] = dict(DOWN=0., LEFT=0. if good else .5)
        observed['action_components'] = dict(DOWN=[2. if good else .2, 0., 0.],
                                            LEFT=[observed['immediate_rewards']['LEFT'], 0., 0.])
    selection = core.select_regularization(rows)
    zero, shrunk = selection['candidates'][0], selection['candidates'][-1]
    assert selection['selected_lambda'] == 1.
    assert zero['utility'] == pytest.approx((35*.65+.8)/36)
    assert shrunk['utility'] == selection['selected_utility'] == pytest.approx((35*.875+1.)/36)
    assert shrunk['fold_results'][0]['loss'] > zero['fold_results'][0]['loss']
    assert zero['utility'] != pytest.approx(np.mean([choice['utility']
        for fold in zero['fold_results'] for choice in fold['choices']]))
    for fold in shrunk['fold_results']:
        for choice in fold['choices']:
            assert choice['decision']['canonical_action'] == ('DOWN' if choice['root_id'].endswith(':0') else 'LEFT')


def test_cached_choices_dispatch_controls_exactly_and_never_read_labels_or_swipe(monkeypatch):
    observed, models = root(), inference_models()
    observed['immediate_rewards']['LEFT'] = .25
    observed.update(oracle_action='DOWN', teacher_action_native='DOWN', action_component_fractions={'secret': []})
    before = deepcopy(models)
    def forbidden(*args, **kwargs):
        raise AssertionError('cached features or choices recomputed a ground swipe')
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', forbidden)
    cache_work = core.cache_roots([observed])
    assert cache_work['layout_feature_cache_hits'] == cache_work['pool_feature_maps_derived'] == 1
    assert cache_work['pool_positions_discarded'] == 80
    allowed = {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards',
               'fallback_action', 'action_map', 'layout_features', 'action_features', 'pooled_features'}
    chooser = core.choose_action
    def checked_pool(payload, current, counts=None):
        assert set(current) == allowed
        return chooser(payload, current, counts)
    monkeypatch.setattr(core, 'choose_action', checked_pool)
    for module in (core.layout, core.shared, core.exact):
        chooser_control = module.choose_action
        def checked_control(payload, current, chooser_control=chooser_control):
            assert set(current) == allowed
            return chooser_control(payload, current)
        monkeypatch.setattr(module, 'choose_action', checked_control)
    choices, work = core.freeze_choices([observed], models)
    assert models == before and set(choices) == {*core.MODEL_NAMES, 'FALLBACK'}
    for mode in ('POOL', 'RIDGE', 'LAYOUT', 'SHARED'):
        assert choices[mode][0]['canonical_action'] == 'DOWN' and choices[mode][0]['actual_action'] == 'UP'
    for mode in ('OLD_SHARED', 'ONE', 'FALLBACK'):
        assert choices[mode][0]['canonical_action'] == 'LEFT' and choices[mode][0]['actual_action'] == 'RIGHT'
    assert work['pool_frozen_model_choices'] == 6 and work['pool_frozen_fallback_choices'] == 1
    assert work['pool_feature_cache_hits'] == 1 and work['layout_feature_cache_hits'] == 2
    assert work['shared_feature_cache_hits'] == 2
    assert 'layout_ground_swipe_calls' not in work and 'shared_ground_swipe_calls' not in work


def test_fresh_roster_seed_shape_is_checked_with_mock_rng_only(monkeypatch):
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
    assert len(cases) == 96 and seeds == list(range(1870200, 1870296))
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    for ordinal, case in enumerate(cases):
        replica, index = divmod(ordinal, 24)
        first, second = edges[index]
        assert case['name'] == f'v187_target_r{replica:02d}_{index:02d}'
        assert case['split'] == 'TARGET' and case['horizon'] == 3
        assert case['board'][first] == case['board'][second] == 1+index % 10
        assert case['board'].count(0) == case['vacancies'] == index % 3


def test_unresolved_svd_retains_paid_preparation_without_scientific_result(monkeypatch):
    def fail(*args, **kwargs):
        raise np.linalg.LinAlgError('synthetic position-sharing SVD failure')
    monkeypatch.setattr(core.ridge.np.linalg, 'svd', fail)
    with pytest.raises(core.ridge.RegularizationExecutionError) as raised:
        core.select_regularization(examples())
    record = raised.value.record
    assert record['operation'] == 'svd'
    assert record['costs']['ridge_svd_attempts'] == 1
    assert record['costs'].get('ridge_svd_decompositions', 0) == 0
    assert record['costs']['ridge_design_preparations'] == 1
    assert record['costs']['pool_feature_maps_derived'] == 71
    assert 'synthetic position-sharing SVD failure' in record['error']
