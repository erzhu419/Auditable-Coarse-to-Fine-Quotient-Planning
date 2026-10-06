"""Synthetic complete-vector learning from frozen program-word contracts."""
from collections import Counter
from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_relational_program_learning_v196 as core


def contract(value, goal=0.):
    return dict(goal_now=goal, values=[goal, float(value)]+[0.]*79, words=[])


def root(root_id='fixture', source=0, first=0, second=1):
    return dict(root_id=root_id, source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'], immediate_rewards=dict(DOWN=0., LEFT=0.),
        fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT', RIGHT='LEFT', UP='DOWN'),
        program_contracts=dict(DOWN=contract(first), LEFT=contract(second)),
        action_components=dict(DOWN=[1., .2, .3], LEFT=[0., .5, .5]))


def four_sources():
    return [root(f'fixture:{index}', index//2) for index in range(4)]


def examples():
    return [root(f'fixture:{source:02d}:{index}', source)
            for source in range(36) for index in range(3 if source == 3 else 4)]


def mass_rows():
    first, second, forced = root('a'), root('b', 1), root('c', 1)
    second['legal_actions'].append('UP'); second['program_contracts']['UP'] = contract(1)
    second['immediate_rewards']['UP'] = .3
    second['action_components']['UP'] = [.3, .5, .5]
    second['immediate_rewards']['DOWN'] = .5
    second['action_components']['DOWN'] = [1.5, .2, .3]
    forced['legal_actions'] = ['DOWN']; forced['action_components'] = {'DOWN': [1., .2, .3]}
    forced['fallback_action'] = 'DOWN'
    return [first, second, forced]


def mass_library():
    return core.prepare_library(mass_rows(), 'FULL')


def test_shared_162_library_keeps_full_tail_and_equal_source_forced_denominator():
    library = mass_library()
    assert len(library['feature_names']) == 162
    assert library['root_ids'] == ['a', 'b', 'c']
    assert library['source_root_counts'] == {'DESIGN_SOURCE:00': 1, 'DESIGN_SOURCE:01': 2}
    assert 'training_outcomes' not in library
    rows = library['prototypes']
    assert len(rows) == 8 and all(len(row['features162']) == 162 for row in rows)
    assert sum(row['root_mass'] for row in rows if row['source_id'].endswith(':00')) == 1.
    assert sum(row['root_mass'] for row in rows if row['source_id'].endswith(':01')) == pytest.approx(.5)
    assert not any(row['root_id'] == 'c' for row in rows)
    for row in rows:
        reverse = next(other for other in rows if other['root_id'] == row['root_id'] and other['actions'] == row['actions'][::-1])
        assert reverse['features162'] == row['features162'][81:]+row['features162'][:81]
        assert reverse['tail_difference'] == pytest.approx([-value for value in row['tail_difference']])
    forward = next(row for row in rows if row['root_id'] == 'b' and row['actions'] == ['DOWN', 'UP'])
    assert forward['tail_difference'] == pytest.approx([1., -.3, -.2])


def test_program_learns_word_applicability_while_terminal_view_is_constant():
    library = core.prepare_library(four_sources(), 'FULL')
    counts = Counter()
    program = core._tree_model(library, 'PROGRAM', 1, 4, counts)
    terminal = core._tree_model(library, 'TERMINAL', 1, 4, counts)
    tree = program['tree']
    assert tree['kind'] == 'split' and tree['feature'] == 1 and tree['threshold'] == 0.
    assert tree['left']['root_count'] == tree['right']['root_count'] == 4
    assert tree['left']['source_count'] == tree['right']['source_count'] == 2
    assert tree['left']['mean'] == pytest.approx([1., -.3, -.2])
    assert tree['right']['mean'] == pytest.approx([-1., .3, .2])
    assert terminal['tree']['kind'] == 'leaf' and terminal['input_columns'] == [0, 81]
    assert terminal['constants']['columns'] == 2 and program['constants']['columns'] == 162
    assert all('cell' not in name for name in program['feature_names'])
    observed = root('query'); observed['immediate_rewards']['LEFT'] = .5
    assert core.choose_action(program, core._observable(observed), library)['canonical_action'] == 'DOWN'
    assert core.choose_action(terminal, core._observable(observed), library)['canonical_action'] == 'LEFT'
    assert counts['PROGRAM_tree_predictors_fitted'] == counts['TERMINAL_tree_predictors_fitted'] == 1


def test_terminal_second_logical_feature_reads_global_column_81():
    rows = []
    for index in range(8):
        observed = root(f'fixture:{index}', index//2)
        if index < 4:
            observed['program_contracts'] = dict(DOWN=contract(0, 0), LEFT=contract(1, 0))
            observed['action_components'] = dict(DOWN=[0., 0., 0.], LEFT=[0., 0., 0.])
        else:
            observed['program_contracts'] = dict(DOWN=contract(0, 0), LEFT=contract(1, 1))
            observed['action_components'] = dict(DOWN=[1., 0., 1.], LEFT=[0., 0., 1.])
        rows.append(observed)
    library = core.prepare_library(rows, 'FULL')
    model = core._tree_model(library, 'TERMINAL', 2, 4, Counter())
    assert model['tree']['feature'] == 0
    assert model['tree']['left']['kind'] == 'split' and model['tree']['left']['feature'] == 1
    observed = root('query')
    observed['program_contracts'] = dict(DOWN=contract(0, 0), LEFT=contract(1, 1))
    decision = core.choose_action(model, core._observable(observed), library)
    assert decision['estimated_pairs']['DOWN|LEFT']['estimated_tail_delta'] == pytest.approx([1., 0., 0.])


def test_neighbor_dyadic_distances_match_ordered_python_sum_and_root_mass():
    rows = mass_rows()
    for index, observed in enumerate(rows):
        for action_index, action in enumerate(observed['legal_actions']):
            # Scores are integer multiples of 1/2048, as in the frozen trace.
            for column in range(4, 81, 4):
                observed['program_contracts'][action]['values'][column] = (2*index+action_index+column)/2048.
    library = core.prepare_library(rows, 'FULL')
    observed = root('query')
    counts = Counter()
    query = core._query(core._observable(observed), counts)
    matrix = core._prototype_matrix(library, counts)
    core._neighbor_geometry(query, library, counts, matrix)
    for direction in ('forward', 'reverse'):
        values = query['pairs']['DOWN|LEFT'][direction]
        expected = sorted((sum((values[c]-row['features162'][c])**2 for c in range(162)), index)
                          for index, row in enumerate(library['prototypes']))
        assert query['pairs']['DOWN|LEFT'][direction+'_neighbors'] == expected
    model = core._neighbor_model(library, 8, counts)
    prediction = core._neighbor_direction(model, query['pairs']['DOWN|LEFT']['forward_neighbors'], library, counts)
    assert all(row['weight'] >= 0. for row in prediction['neighbors'])
    assert sum(row['weight'] for row in prediction['neighbors']) == pytest.approx(1.)
    a = next(row for row in prediction['neighbors'] if row['prototype_index'] == 0)
    b = next(row for row in prediction['neighbors'] if row['prototype_index'] == 2)
    assert a['weight']/b['weight'] == pytest.approx(6.)
    assert counts['neighbor_distance_component_squares'] == 2*8*162


def test_directional_antisymmetry_complete_rfs_and_first_reward_once():
    library = core.prepare_library(four_sources(), 'FULL')
    model = core._tree_model(library, 'PROGRAM', 1, 4, Counter())
    observed = root('query'); observed['immediate_rewards'] = dict(DOWN=.7, LEFT=.2)
    decision = core.choose_action(model, core._observable(observed), library)
    assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx([1.5, -.3, -.2])
    assert decision['projection_residual_sse'] == pytest.approx(0.)
    assert decision['work']['pair_reward_additions'] == 2
    observed['program_contracts']['LEFT'] = contract(0)
    observed['immediate_rewards'] = dict(DOWN=0., LEFT=.5)
    same = core.choose_action(model, core._observable(observed), library)
    pair = same['estimated_pairs']['DOWN|LEFT']
    assert pair['forward']['components'] == pair['reverse']['components'] == pytest.approx([1., -.3, -.2])
    assert pair['estimated_tail_delta'] == [0., 0., 0.]
    assert same['canonical_action'] == 'LEFT'


def test_forced_and_epsilon_decisions_keep_canonical_order():
    library = core.prepare_library([root('source')], 'FULL')
    model = core._neighbor_model(library, 8, Counter())
    observed = root('query', first=0, second=0)
    observed['legal_actions'] = ['LEFT', 'DOWN']
    observed['immediate_rewards'] = dict(DOWN=0., LEFT=core.EPSILON/2)
    assert core.choose_action(model, core._observable(observed), library)['canonical_action'] == 'DOWN'
    observed['immediate_rewards']['LEFT'] = 2*core.EPSILON
    assert core.choose_action(model, core._observable(observed), library)['canonical_action'] == 'LEFT'
    observed['legal_actions'] = ['DOWN']; observed['fallback_action'] = 'DOWN'
    observed['immediate_rewards']['DOWN'] = .9
    forced = core.choose_action(model, core._observable(observed), library)
    assert forced['predicted_components']['DOWN'] == [.9, 0., 0.]
    assert forced['estimated_pairs'] == forced['predicted_pairs'] == {}
    assert forced['projection_residual_sse'] == forced['projection_residual_max'] == 0.


def test_three_source_arms_select_actual_utility_and_reuse_libraries_and_queries(monkeypatch):
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
    assert rows == before and calls['decisions'] == 19*143
    selection, models, libraries, costs = result['selection'], result['models'], result['libraries'], result['costs']
    assert selection['PROGRAM']['selected_depth'] == selection['TERMINAL']['selected_depth'] == 1
    assert selection['PROGRAM']['selected_min_leaf_roots'] == selection['TERMINAL']['selected_min_leaf_roots'] == 4
    assert selection['PROGRAM']['selected_utility'] == pytest.approx((35*.65+.8)/36)
    assert selection['TERMINAL']['selected_utility'] == pytest.approx((35*.875+1.)/36)
    assert selection['PROGRAM_NEIGHBOR']['selected_k'] == 1
    assert selection['PROGRAM_NEIGHBOR']['selected_utility'] == pytest.approx((35*.875+1.)/36)
    assert set(libraries) == {'FOLD_0', 'FOLD_1', 'FULL'}
    assert costs['shared_library_preparations'] == 3 and costs['query_input_roots'] == 143
    assert costs['neighbor_matrix_preparations'] == 2
    assert costs['tree_predictors_fitted'] == costs['tree_fit_attempts'] == 34
    assert costs['PROGRAM_tree_predictors_fitted'] == costs['TERMINAL_tree_predictors_fitted'] == 17
    assert costs['neighbor_predictor_configurations'] == 7 and costs['new_predictors_fitted'] == 41
    assert costs['heldout_action_vector_reads'] == 19*143
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


def test_selected_full_program_failure_preserves_thirty_eight_completed_instances(monkeypatch):
    moments = core._moments
    def fail_full(prototypes, indices, counts):
        result = moments(prototypes, indices, counts)
        if len(prototypes) == 286 and len(indices) == 286:
            raise ArithmeticError('synthetic selected-full-program moment failure')
        return result
    monkeypatch.setattr(core, '_moments', fail_full)
    with pytest.raises(core.PairExecutionError) as raised:
        core.fit_models(examples())
    record = raised.value.record
    assert record['operation'] == 'joint_source_selection'
    assert record['costs']['shared_library_preparations'] == 3
    assert record['costs']['tree_fit_attempts'] == 33 and record['costs']['tree_predictors_fitted'] == 32
    assert record['costs']['PROGRAM_tree_fit_attempts'] == 17
    assert record['costs']['PROGRAM_tree_predictors_fitted'] == record['costs']['TERMINAL_tree_predictors_fitted'] == 16
    assert record['costs']['neighbor_predictor_configurations'] == 6
    assert record['costs']['new_predictors_fitted'] == 38
    assert record['costs']['tree_moment_sample_reads'] > 286
    assert record['costs']['query_input_roots'] == 143
