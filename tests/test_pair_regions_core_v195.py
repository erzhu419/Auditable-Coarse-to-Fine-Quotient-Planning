"""Synthetic witnesses for learned applicability regions and shared SOURCE CV."""
from collections import Counter
from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_pair_regions_v195 as core


def board(value):
    return [value]+[0]*15


def root(root_id='fixture', source=0, first=0, second=1):
    return dict(root_id=root_id, source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'], immediate_rewards=dict(DOWN=0., LEFT=0.),
        fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT', RIGHT='LEFT', UP='DOWN'),
        raw_afterstates=dict(DOWN=board(first), LEFT=board(second)),
        action_components=dict(DOWN=[1., .2, .3], LEFT=[0., .5, .5]))


def four_sources():
    return [root(f'fixture:{index}', index//2) for index in range(4)]


def examples():
    return [root(f'fixture:{source:02d}:{index}', source)
            for source in range(36) for index in range(3 if source == 3 else 4)]


def source_mass_library():
    first, second, forced = root('a'), root('b', 1), root('c', 1)
    second['legal_actions'].append('UP'); second['raw_afterstates']['UP'] = board(1)
    second['immediate_rewards']['UP'] = .3
    second['action_components']['UP'] = [.3, .5, .5]
    second['immediate_rewards']['DOWN'] = .5
    second['action_components']['DOWN'] = [1.5, .2, .3]
    forced['legal_actions'] = ['DOWN']; forced['action_components'] = {'DOWN': [1., .2, .3]}
    forced['fallback_action'] = 'DOWN'
    return core.prepare_library([first, second, forced], 'FULL')


def test_raw_cache_reads_positioned_cells_once_without_world_evolution():
    tiles = [index % 12 for index in range(16)]
    tokens = [['cell', index, rank] for index, rank in reversed(list(enumerate(tiles)))]
    observed = dict(legal_actions=['DOWN'], layout_features={'DOWN': {'tokens': [['row', 0, 1], *tokens]}})
    counts = core.cache_roots([observed])
    assert observed['raw_afterstates']['DOWN'] == tiles
    assert counts['raw_afterstate_cell_tokens'] == 16
    assert counts['raw_afterstates_extracted'] == 1
    again = core.cache_roots([observed])
    assert again['raw_afterstate_cache_hits'] == 1
    assert again.get('raw_afterstates_extracted', 0) == 0


def test_source_equal_mass_includes_forced_roots_and_complete_ordered_tails():
    library = source_mass_library()
    assert library['root_ids'] == ['a', 'b', 'c']
    assert library['source_root_counts'] == {'DESIGN_SOURCE:00': 1, 'DESIGN_SOURCE:01': 2}
    assert 'training_outcomes' not in library
    rows = library['prototypes']
    assert len(rows) == 8 and all(len(row['features32']) == 32 for row in rows)
    assert sum(row['root_mass'] for row in rows if row['source_id'].endswith(':00')) == 1.
    assert sum(row['root_mass'] for row in rows if row['source_id'].endswith(':01')) == pytest.approx(.5)
    assert not any(row['root_id'] == 'c' for row in rows)
    for row in rows:
        reverse = next(other for other in rows if other['root_id'] == row['root_id'] and other['actions'] == row['actions'][::-1])
        assert reverse['features32'] == row['features32'][16:]+row['features32'][:16]
        assert reverse['tail_difference'] == pytest.approx([-value for value in row['tail_difference']])
    forward = next(row for row in rows if row['root_id'] == 'b' and row['actions'] == ['DOWN', 'UP'])
    assert forward['tail_difference'] == pytest.approx([1., -.3, -.2])


def test_tree_learns_full_vector_and_support_counts_can_overlap_children():
    library = core.prepare_library(four_sources(), 'FULL')
    counts = Counter()
    model = core._tree_model(library, 1, 4, counts)
    tree = model['tree']
    assert tree['root_count'] == 4 and tree['source_count'] == 2
    assert tree['kind'] == 'split' and tree['feature'] == 0 and tree['threshold'] == 0
    assert tree['left']['root_count'] == tree['right']['root_count'] == 4
    assert tree['left']['source_count'] == tree['right']['source_count'] == 2
    assert tree['left']['mean'] == pytest.approx([1., -.3, -.2])
    assert tree['right']['mean'] == pytest.approx([-1., .3, .2])
    assert tree['left']['prototype_indices'] == [0, 2, 4, 6]
    assert tree['right']['prototype_indices'] == [1, 3, 5, 7]
    assert counts['tree_predictors_fitted'] == counts['new_predictors_fitted'] == 1
    decision = core.choose_action(model, core._observable(root('query')), library)
    assert decision['estimated_pairs']['DOWN|LEFT']['estimated_tail_delta'] == pytest.approx([1., -.3, -.2])
    assert decision['canonical_action'] == 'DOWN'
    unsupported = core._tree_model(library, 6, 8, Counter())
    assert unsupported['tree']['kind'] == 'leaf'


def test_raw_neighbors_use_source_mass_nonnegative_weights_and_reward_once():
    library = source_mass_library()
    model = core._raw_model(library, 8, Counter())
    observed = root('query'); observed['immediate_rewards'] = dict(DOWN=.7, LEFT=.2)
    decision = core.choose_action(model, core._observable(observed), library)
    forward = decision['estimated_pairs']['DOWN|LEFT']['forward']
    weights = forward['neighbors']
    assert all(row['weight'] >= 0. for row in weights)
    assert sum(row['weight'] for row in weights) == pytest.approx(1.)
    a = next(row for row in weights if row['prototype_index'] == 0)
    b = next(row for row in weights if row['prototype_index'] == 2)
    assert a['distance'] == b['distance'] == 0.
    assert a['weight']/b['weight'] == pytest.approx(6.)
    one = core.choose_action(core._raw_model(library, 1, Counter()), core._observable(observed), library)
    assert one['predicted_pairs']['DOWN|LEFT'] == pytest.approx([1.5, -.3, -.2])
    assert one['projection_residual_sse'] == pytest.approx(0.)
    assert one['work']['pair_reward_additions'] == 2


def test_two_direction_predictions_are_antisymmetrized_before_projection():
    library = core.prepare_library(four_sources(), 'FULL')
    model = core._tree_model(library, 1, 4, Counter())
    observed = root('query', first=0, second=0)
    observed['immediate_rewards'] = dict(DOWN=0., LEFT=.5)
    decision = core.choose_action(model, core._observable(observed), library)
    pair = decision['estimated_pairs']['DOWN|LEFT']
    assert pair['forward']['components'] == pair['reverse']['components'] == pytest.approx([1., -.3, -.2])
    assert pair['estimated_tail_delta'] == [0., 0., 0.]
    assert pair['projected_tail_delta'] == [0., 0., 0.]
    assert decision['canonical_action'] == 'LEFT'


def test_forced_and_epsilon_ties_keep_canonical_action_order():
    library = core.prepare_library([root('source')], 'FULL')
    model = core._raw_model(library, 8, Counter())
    observed = root('query', first=0, second=0)
    observed['legal_actions'] = ['LEFT', 'DOWN']
    observed['immediate_rewards'] = dict(DOWN=0., LEFT=core.EPSILON/2)
    assert core.choose_action(model, core._observable(observed), library)['canonical_action'] == 'DOWN'
    observed['immediate_rewards']['LEFT'] = 2*core.EPSILON
    assert core.choose_action(model, core._observable(observed), library)['canonical_action'] == 'LEFT'
    observed['legal_actions'] = ['DOWN']; observed['fallback_action'] = 'DOWN'
    observed['immediate_rewards']['DOWN'] = .9
    forced = core.choose_action(model, core._observable(observed), library)
    assert forced['canonical_action'] == 'DOWN' and forced['actual_action'] == 'UP'
    assert forced['predicted_components']['DOWN'] == [.9, 0., 0.]
    assert forced['estimated_pairs'] == forced['predicted_pairs'] == {}
    assert forced['projection_residual_sse'] == forced['projection_residual_max'] == 0.


def test_source_actual_utility_selects_configs_and_shared_queries_strip_labels(monkeypatch):
    rows = examples()
    for observed in rows:
        last = 2 if observed['source_id'].endswith(':03') else 3
        good = observed['root_id'].endswith(':'+str(last))
        observed['immediate_rewards'] = dict(DOWN=0., LEFT=0. if good else .5)
        observed['action_components'] = dict(DOWN=[2. if good else .2, 0., 0.],
            LEFT=[observed['immediate_rewards']['LEFT'], 0., 0.])
        observed.update(oracle_action='UP', teacher_action_native='UP')
    before, calls = deepcopy(rows), Counter()
    deciding = core._decision
    def label_free(model, observed, library, query, counts):
        assert not {'action_components', 'oracle_action', 'teacher_action_native'} & set(observed)
        calls['decisions'] += 1
        return deciding(model, observed, library, query, counts)
    monkeypatch.setattr(core, '_decision', label_free)
    result = core.fit_models(rows+[dict(life=1)])
    assert rows == before and calls['decisions'] == 11*143
    selection, models, libraries, costs = result['selection'], result['models'], result['libraries'], result['costs']
    assert selection['TREE32']['selected_depth'] == 1 and selection['TREE32']['selected_min_leaf_roots'] == 4
    assert selection['TREE32']['selected_utility'] == pytest.approx((35*.65+.8)/36)
    assert selection['RAW32']['selected_k'] == 1
    assert selection['RAW32']['selected_utility'] == pytest.approx((35*.875+1.)/36)
    assert selection['RAW32']['candidates'][1]['utility'] == pytest.approx((35*.65+.8)/36)
    assert set(libraries) == {'FOLD_0', 'FOLD_1', 'FULL'}
    assert costs['shared_library_preparations'] == 3
    assert costs['query_input_roots'] == 143
    assert costs['tree_predictors_fitted'] == costs['tree_fit_attempts'] == 17
    assert costs['raw_predictor_configurations'] == 7 and costs['new_predictors_fitted'] == 24
    assert costs['heldout_action_vector_reads'] == 11*143
    assert costs['new_linear_solves'] == costs['new_eigen_decompositions'] == costs['new_svd_decompositions'] == 0
    assert all(model['library_id'] == 'FULL' and 'library' not in model for model in models.values())
    for arm in selection.values():
        for fold in arm['folds']:
            assert 'library' not in fold
            assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
        for candidate in arm['candidates']:
            for fold in candidate['fold_results']:
                assert 'library' not in fold and 'prototypes' not in fold
                assert all(set(row) == {'root_id', 'source_id', 'canonical_action', 'components', 'utility'} for row in fold['choices'])


def test_selected_full_tree_failure_retains_completed_fits_and_shared_libraries(monkeypatch):
    moments = core._moments
    def fail_full(prototypes, indices, counts):
        result = moments(prototypes, indices, counts)
        if len(prototypes) == 286 and len(indices) == 286:
            raise ArithmeticError('synthetic selected-full-tree moment failure')
        return result
    monkeypatch.setattr(core, '_moments', fail_full)
    with pytest.raises(core.PairExecutionError) as raised:
        core.fit_models(examples())
    record = raised.value.record
    assert record['operation'] == 'joint_source_selection'
    assert record['costs']['shared_library_attempts'] == record['costs']['shared_library_preparations'] == 3
    assert record['costs']['tree_fit_attempts'] == 17 and record['costs']['tree_predictors_fitted'] == 16
    assert record['costs']['raw_predictor_configurations'] == 6
    assert record['costs']['new_predictors_fitted'] == 22
    assert record['costs']['tree_moment_sample_reads'] > 286
    assert record['costs']['query_input_roots'] == 143
