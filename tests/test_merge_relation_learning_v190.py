"""Synthetic witnesses for the fixed relation learner and SOURCE-only selection."""
from collections import Counter
from copy import deepcopy
from itertools import combinations

import numpy as np
import pytest

from acfqp.science import controlled_predictive_merge_relation_learning_v190 as core


TAIL = np.asarray([1., -.2, .2])


def root(root_id='fixture', source=0):
    down = [1.]+[0.]*97
    return dict(root_id=root_id, source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'],
        immediate_rewards=dict(DOWN=0., LEFT=0.), fallback_action='LEFT',
        action_map=dict(DOWN='UP', LEFT='RIGHT'),
        fixture_features=dict(DOWN=down, LEFT=[0.]*98),
        action_components=dict(DOWN=[1., .3, .7], LEFT=[0., .5, .5]))


def examples():
    return [root(f'fixture:{source:02d}:{index}', source)
            for source in range(36) for index in range(3 if source == 3 else 4)]


@pytest.fixture
def encoder(monkeypatch):
    def read(observed, counts=None):
        cached = 'relation_features' in observed
        result = deepcopy(observed['relation_features' if cached else 'fixture_features'])
        if counts is not None:
            counts.update(fixture_cache_hits=int(cached), fixture_maps_derived=int(not cached),
                          fixture_feature_reads=98*len(result))
        return result
    monkeypatch.setattr(core.relation, 'action_features_from_root', read)


def test_design_preserves_pair_weight_complete_tails_and_forced_root_normalization(encoder):
    rows = [root(f'weighted:{index}') for index in range(5)]
    for index, observed in enumerate(rows):
        observed['immediate_rewards'] = dict(DOWN=index/2048., LEFT=1/2048.)
        offset = np.asarray([3.+index, .5, .5])
        observed['action_components'] = dict(
            DOWN=(offset+TAIL+[observed['immediate_rewards']['DOWN'], 0., 0.]).tolist(),
            LEFT=(offset+[observed['immediate_rewards']['LEFT'], 0., 0.]).tolist())
        if index < 2:
            observed['legal_actions'].append('UP')
            observed['fixture_features']['UP'] = [0.]*98
            observed['immediate_rewards']['UP'] = observed['immediate_rewards']['LEFT']
            observed['action_components']['UP'] = observed['action_components']['LEFT'].copy()
            observed['action_map']['UP'] = 'DOWN'
    rows[-1]['legal_actions'] = ['DOWN']
    rows[-1]['action_components'] = {'DOWN': rows[-1]['action_components']['DOWN']}
    rows[-1]['fallback_action'] = 'DOWN'
    before = deepcopy(rows)
    design = core.prepare_design(rows)
    costs = Counter(design['work'])
    decomposition = core.ridge._decompose(design, costs)
    fitted = core.ridge._filter(design, decomposition, 1.)
    model = core._model(design, decomposition, fitted, 1., [])
    assert rows == before and design['X'].shape == (8, 98) and design['Y'].shape == (8, 3)
    assert len(design['roots']) == 5 and model['coefficients'][0] == pytest.approx(TAIL*2/5)
    assert model['objective'] == pytest.approx(model['loss']/5+model['penalty'])
    assert len(model['feature_names']) == model['constants']['columns'] == 98
    assert 'vocabulary' not in model and model['schema'] == core.SCHEMA+'.model'
    assert model['training_outcomes'][-1]['root_id'] == rows[-1]['root_id']
    for label in design['fit_labels'][:-1]:
        assert sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.)
        for pair in label['pairs']:
            expected = TAIL if pair['actions'][0] == 'DOWN' else np.zeros(3)
            assert pair['components'] == pytest.approx(expected)
    assert design['fit_labels'][-1]['pairs'] == []


def test_source_selection_uses_equal_group_actual_utility_and_one_relation_cache(encoder, monkeypatch):
    rows = examples()
    for observed in rows:
        good = observed['root_id'].endswith(':0')
        observed['immediate_rewards'] = dict(DOWN=0., LEFT=0. if good else .5)
        observed['action_components'] = dict(DOWN=[2. if good else .2, 0., 0.],
                                            LEFT=[observed['immediate_rewards']['LEFT'], 0., 0.])
        observed.update(oracle_action='UP', teacher_action_native='UP', action_component_fractions={'secret': []})
    before = deepcopy(rows)
    calls = dict(svd=0, filters=0)
    svd, filtering, chooser = core.ridge.np.linalg.svd, core.ridge._filter, core.choose_action
    def counted_svd(*args, **kwargs):
        calls['svd'] += 1
        return svd(*args, **kwargs)
    def counted_filter(*args, **kwargs):
        calls['filters'] += 1
        return filtering(*args, **kwargs)
    def observable_only(payload, observed, counts=None):
        assert set(observed) == {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
            'immediate_rewards', 'fallback_action', 'action_map', 'relation_features'}
        return chooser(payload, observed, counts)
    monkeypatch.setattr(core.ridge.np.linalg, 'svd', counted_svd)
    monkeypatch.setattr(core.ridge, '_filter', counted_filter)
    monkeypatch.setattr(core, 'choose_action', observable_only)
    result = core.fit_model(rows+[dict(life=1, root_id='excluded-before-labels')])
    assert rows == before and calls == dict(svd=3, filters=13)
    assert result['cache_counts']['fixture_maps_derived'] == 143
    assert result['costs']['fixture_maps_derived'] == 143
    assert result['costs']['ridge_svd_decompositions'] == 3
    assert result['costs']['ridge_predictors_fitted'] == result['costs']['new_predictors_fitted'] == 13
    assert result['costs']['heldout_action_vector_reads'] == 6*143
    selection, model = result['selection'], result['model']
    assert 'model' not in selection and selection['selected_lambda'] == 1.
    zero, shrunk = selection['candidates'][0], selection['candidates'][-1]
    assert zero['utility'] == pytest.approx((35*.65+.8)/36)
    assert shrunk['utility'] == pytest.approx((35*.875+1.)/36)
    assert shrunk['fold_results'][0]['loss'] > zero['fold_results'][0]['loss']
    assert zero['utility'] != pytest.approx(np.mean([choice['utility']
        for fold in zero['fold_results'] for choice in fold['choices']]))
    assert len(selection['source_folds'][0]) == len(selection['source_folds'][1]) == 18
    assert model['source_root_counts']['DESIGN_SOURCE:03'] == 3 and len(model['root_ids']) == 143
    for fold in selection['folds']:
        assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
        assert set(fold['design']['source_ids']) == set(fold['train_sources'])
        assert len(fold['design']['action_root_ids']['DOWN']) == (71 if fold['fold'] == 0 else 72)
        assert 'X' not in fold['design'] and 'Y' not in fold['design']


def test_cached_inference_adds_first_reward_once_and_preserves_support_fallbacks(encoder):
    observed = root()
    observed['relation_features'] = observed.pop('fixture_features')
    observed['immediate_rewards']['LEFT'] = 1.2
    support = dict(action_root_ids={a: ['a', 'b', 'c', 'd'] for a in core.ACTIONS},
        pair_root_ids={f'{a}|{b}': ['a', 'b', 'c', 'd'] for a, b in combinations(core.ACTIONS, 2)},
        connected_components=[list(core.ACTIONS)])
    payload = dict(life=0, coefficients=[[1., .2, .3]]+[[0., 0., 0.] for _ in range(97)], **support)
    counts = Counter()
    decision = core.choose_action(payload, core._observable(observed), counts)
    assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
    assert decision['predicted_components']['DOWN'] == pytest.approx([1., .2, .3])
    assert decision['predicted_components']['LEFT'] == pytest.approx([1.2, 0., 0.])
    assert counts['relation_reward_additions'] == 2 and counts['fixture_cache_hits'] == 1
    assert 'coverage' not in decision
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


def test_grid_ties_keep_first_lambda_and_final_failure_retains_paid_folds(encoder, monkeypatch):
    result = core.fit_model(examples())
    assert result['selection']['selected_lambda'] == 0.
    assert len({round(row['utility'], 12) for row in result['selection']['candidates']}) == 1
    svd, attempts = core.ridge.np.linalg.svd, []
    def fail_third(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 3:
            raise np.linalg.LinAlgError('synthetic final SOURCE decomposition failure')
        return svd(*args, **kwargs)
    monkeypatch.setattr(core.ridge.np.linalg, 'svd', fail_third)
    with pytest.raises(core.ridge.RegularizationExecutionError) as raised:
        core.fit_model(examples())
    record = raised.value.record
    assert record['operation'] == 'RELATION:svd'
    assert record['costs']['ridge_svd_attempts'] == 3 and record['costs']['ridge_svd_decompositions'] == 2
    assert record['costs']['ridge_predictors_fitted'] == 12 and record['costs']['ridge_design_preparations'] == 3
    assert record['costs']['fixture_maps_derived'] == 143
