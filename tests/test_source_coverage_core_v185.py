"""Synthetic coverage coordination; no actual V185 seed is sampled here."""
from copy import deepcopy
from itertools import combinations

import numpy as np
import pytest

from acfqp.science import controlled_predictive_source_coverage_v185 as core


TAIL = np.asarray([1., -.2, .2])


def layout(active=False):
    tokens = [['cell', i, 0] for i in range(16)]
    tokens += [['horizontal', 4*r+c, 0, 0] for r in range(4) for c in range(3)]
    tokens += [['vertical', 4*r+c, 0, 0] for r in range(3) for c in range(4)]
    return dict(aggregate=[float(active), 0., 0., 0., 0., 0.], tokens=tokens)


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


def inference_models():
    actions = core.exact.ACTIONS
    support = dict(action_root_ids={action: ['a', 'b', 'c', 'd'] for action in actions},
        pair_root_ids={f'{a}|{b}': ['a', 'b', 'c', 'd'] for a, b in combinations(actions, 2)},
        connected_components=[list(actions)])
    vocabulary = sorted(layout()['tokens'], key=tuple)
    models = {}
    for name in ('RIDGE', 'LAYOUT', 'OLD_RIDGE', 'OLD_LAYOUT'):
        coefficients = [[0., 0., 0.] for _ in range(46)]
        coefficients[0][0] = -1. if name.startswith('OLD_') else 1.
        models[name] = dict(life=0, vocabulary=vocabulary, coefficients=coefficients, **deepcopy(support))
    for name in ('SHARED', 'OLD_SHARED'):
        coefficients = [[0., 0., 0.] for _ in range(6)]
        coefficients[0][0] = -1. if name.startswith('OLD_') else 1.
        models[name] = dict(life=0, coefficients=coefficients, **deepcopy(support))
    leaf = dict(leaf_id=0, coefficients={a: [0., 0., 0.] for a in actions}, **deepcopy(support))
    models['ONE'] = dict(life=0, mode='ONE_LATE', groups={'ALL': 0}, leaves=[leaf])
    return models


def test_separate_frozen_seed_ranges_and_geometry_with_mock_rng_only(monkeypatch):
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
    source, target = core.cohort_cases('SOURCE'), core.cohort_cases('TARGET')
    assert seeds == list(range(1850100, 1850196))+list(range(1850200, 1850296))
    assert len(source) == len(target) == 96
    assert {row['seed'] for row in source}.isdisjoint(row['seed'] for row in target)
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    for cohort, split in ((source, 'SOURCE'), (target, 'TARGET')):
        for ordinal, case in enumerate(cohort):
            replica, index = divmod(ordinal, 24)
            first, second = edges[index]
            assert case['split'] == split and case['horizon'] == 3
            assert case['name'] == f'v185_{split.lower()}_r{replica:02d}_{index:02d}'
            assert case['board'][first] == case['board'][second] == 1+index % 10
            assert case['board'].count(0) == case['vacancies'] == index % 3


def test_new_source_group_offsets_leave_old_parity_intact_and_target_distinct():
    cases = [dict(name=f'synthetic:{i}', horizon=3, board=[1, 1, 0, 0]+[0]*12,
                  split=split, replica=replica, stratum=stratum, seed=17+i)
             for i, (split, replica, stratum) in enumerate((('SOURCE', 0, 0), ('SOURCE', 0, 4),
                 ('SOURCE', 3, 23), ('TARGET', 2, 5)))]
    roots, work = core.observe_roots(cases)
    assert [row['source_id'] for row in roots] == ['DESIGN_SOURCE:12', 'DESIGN_SOURCE:13',
                                                  'DESIGN_SOURCE:35', 'FRESH_REPLICA:02']
    assert [row['cohort'] for row in roots] == ['SOURCE', 'SOURCE', 'SOURCE', 'TARGET']
    assert all(row['split'] == case['split'] for row, case in zip(roots, cases))
    assert work['root_ground_swipe_calls'] == 16


def test_inherited_cached_features_are_reused_without_swipes_or_scoring(monkeypatch):
    observed = root()
    def forbidden(*args, **kwargs):
        raise AssertionError('cache reuse performed an unpaid swipe or policy choice')
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', forbidden)
    monkeypatch.setattr(core.layout, 'choose_action', forbidden)
    work = core.cache_roots([observed])
    assert observed['action_features'] == {a: value['aggregate'] for a, value in observed['layout_features'].items()}
    assert work['layout_feature_cache_hits'] == 1
    assert work['shared_feature_maps_derived'] == 1 and work['shared_aggregate_cache_values_copied'] == 12
    assert 'layout_ground_swipe_calls' not in work


def test_three_shared_decompositions_fourteen_filters_and_one_shared_solve(monkeypatch):
    rows = examples()
    calls = dict(svd=0, lstsq=0, filters=[])
    svd, lstsq, filter_coefficients = core.ridge.np.linalg.svd, core.np.linalg.lstsq, core.ridge._filter
    def counted_svd(*args, **kwargs):
        calls['svd'] += 1
        return svd(*args, **kwargs)
    def counted_lstsq(*args, **kwargs):
        calls['lstsq'] += 1
        return lstsq(*args, **kwargs)
    def counted_filter(design, decomposition, lambda_value):
        calls['filters'].append((id(design), id(decomposition), lambda_value))
        return filter_coefficients(design, decomposition, lambda_value)
    monkeypatch.setattr(core.ridge.np.linalg, 'svd', counted_svd)
    monkeypatch.setattr(core.np.linalg, 'lstsq', counted_lstsq)
    monkeypatch.setattr(core.ridge, '_filter', counted_filter)
    result = core.fit_expanded(rows+[dict(life=1, root_id='unread-target')])
    selection, costs = result['selection'], result['costs']
    assert calls['svd'] == 3 and calls['lstsq'] == 1 and len(calls['filters']) == 14
    assert calls['filters'][-1][:2] == calls['filters'][-2][:2]
    assert calls['filters'][-1][2] == calls['filters'][-2][2] == 0.  # Explicit extra filter even at zero.
    assert costs['ridge_svd_decompositions'] == 3 and costs['ridge_coefficient_filters'] == 14
    assert costs['shared_lstsq_solves'] == 1 and costs['new_predictors_fitted'] == 15
    assert costs['ridge_design_preparations'] == 3 and costs['heldout_action_vector_reads'] == 6*143
    assert len(selection['source_folds'][0]) == len(selection['source_folds'][1]) == 18
    assert selection['source_folds'][0][:6] == [f'DESIGN_SOURCE:{i:02d}' for i in range(0, 12, 2)]
    assert selection['selected_lambda'] == 0.
    assert all(candidate['utility'] == pytest.approx(1.4) for candidate in selection['candidates'])
    for model in result['models'].values():
        assert len(model['root_ids']) == 143 and len(model['source_ids']) == 36
        assert model['source_root_counts']['DESIGN_SOURCE:03'] == 3
        assert 'unread-target' not in model['root_ids']
    assert np.asarray(result['models']['RIDGE']['coefficients']) == pytest.approx(
        np.asarray(result['models']['LAYOUT']['coefficients']), abs=1e-12)
    shared = result['models']['SHARED']
    assert shared['coefficients'][0] == pytest.approx(TAIL)
    assert shared['rank'] == 1 and shared['loss'] < 1e-24
    assert all(column < 6 for row in shared['fit_residuals'] for column, _ in row['design'])


def test_seven_frozen_models_use_current_cached_observables_without_labels(monkeypatch):
    observed, frozen = root(), inference_models()
    observed['immediate_rewards']['LEFT'] = .25
    observed.update(oracle_action='UP', teacher_action_native='UP',
                    action_component_fractions={'secret': []})
    before = deepcopy(frozen)
    allowed = {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
               'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'action_features'}
    for module in (core.layout, core.shared, core.exact):
        chooser = module.choose_action
        def checked(model, current, chooser=chooser):
            assert set(current) == allowed
            return chooser(model, current)
        monkeypatch.setattr(module, 'choose_action', checked)
    def forbidden(*args, **kwargs):
        raise AssertionError('a frozen cached choice repeated a ground swipe')
    monkeypatch.setattr(core.layout.ground, 'swipe_board_v1', forbidden)
    choices, work = core.freeze_choices([observed], frozen)
    assert frozen == before and set(choices) == {*core.MODEL_NAMES, 'FALLBACK'}
    for name in ('RIDGE', 'LAYOUT', 'SHARED'):
        assert choices[name][0]['canonical_action'] == 'DOWN'
        assert choices[name][0]['actual_action'] == 'UP'
    for name in ('OLD_RIDGE', 'OLD_LAYOUT', 'OLD_SHARED', 'ONE', 'FALLBACK'):
        assert choices[name][0]['canonical_action'] == 'LEFT'
        assert choices[name][0]['actual_action'] == 'RIGHT'
    assert work['coverage_model_choices'] == 7 and work['coverage_fallback_choices'] == 1
    assert work['layout_feature_cache_hits'] == 4 and work['shared_feature_cache_hits'] == 2
    assert 'layout_ground_swipe_calls' not in work and 'shared_ground_swipe_calls' not in work


def test_failed_shared_solve_retains_all_already_paid_ridge_work(monkeypatch):
    def fail(*args, **kwargs):
        raise np.linalg.LinAlgError('synthetic SHARED failure')
    monkeypatch.setattr(core.np.linalg, 'lstsq', fail)
    with pytest.raises(core.ridge.RegularizationExecutionError) as raised:
        core.fit_expanded(examples())
    record = raised.value.record
    assert record['operation'] == 'shared_lstsq'
    assert record['costs']['ridge_svd_decompositions'] == 3
    assert record['costs']['ridge_coefficient_filters'] == record['costs']['ridge_predictors_fitted'] == 14
    assert record['costs']['shared_lstsq_attempts'] == 1
    assert record['costs'].get('shared_lstsq_solves', 0) == 0
