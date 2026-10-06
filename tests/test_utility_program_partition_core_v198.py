"""Synthetic decision-utility induction and fixed complete-vector decoding."""
from collections import Counter
from copy import deepcopy

import numpy as np
import pytest

from acfqp.science import controlled_predictive_utility_program_partition_v198 as core
from acfqp.science import controlled_predictive_relational_program_learning_v196 as programs


def contract(value, context=0.):
    values = [0.]*81
    values[1], values[4], values[5] = float(value), float(context), float(value)
    return dict(goal_now=False, values=values, words=[])


def root(root_id='fixture', source=0):
    return dict(root_id=root_id, source_id=f'DESIGN_SOURCE:{source:02d}', life=0,
        canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'], immediate_rewards=dict(DOWN=0., LEFT=0.),
        fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT', RIGHT='LEFT', UP='DOWN'),
        program_contracts=dict(DOWN=contract(0), LEFT=contract(1)),
        action_components=dict(DOWN=[0., 1., 0.], LEFT=[.1, 0., 0.]))


def library_and_view(rows, counts=None):
    library = programs.prepare_library(rows, 'FULL')
    return library, core.prepare_training_view(rows, library, counts)


def fit_tree(rows, depth=1, support=4):
    library, view = library_and_view(rows)
    counts = Counter()
    return core._tree_model(library, view, depth, support, counts), library, view, counts


def source_examples():
    return [root(f'fixture:{source:02d}:{index}', source)
            for source in range(36) for index in range(3 if source == 3 else 4)]


def supplied_libraries(rows):
    sources = sorted({row['source_id'] for row in rows})
    result = {f'FOLD_{fold}': programs.prepare_library(
        [row for row in rows if row['source_id'] not in sources[fold::2]], f'FOLD_{fold}') for fold in range(2)}
    result['FULL'] = programs.prepare_library(rows, 'FULL')
    return result


def test_sse_split_is_rejected_when_it_cannot_improve_actual_decisions():
    rows = [root(f'fixture:{index}', index//2) for index in range(4)]
    for observed in rows:
        observed['action_components'] = dict(DOWN=[1., 0., 0.], LEFT=[0., 0., 0.])
    model, library, view, counts = fit_tree(rows)
    old = programs._tree_model(library, 'PROGRAM', 1, 4, Counter())
    assert old['tree']['kind'] == 'split' and old['tree']['improvement'] > 0.
    assert model['tree']['kind'] == 'leaf'
    assert counts['tree_supported_split_candidates'] > 0 and counts['tree_splits_built'] == 0
    assert core._training_utility(np.zeros((4, 4, 3)), view, Counter()) == 1.
    assert core.choose_action(model, programs._observable(root('query')), library)['canonical_action'] == 'DOWN'


def test_complete_rfs_risk_changes_the_split_and_reward_is_added_once():
    rows = [root(f'fixture:{index}', index//2) for index in range(8)]
    for observed in rows:
        observed['action_components'] = dict(DOWN=[1.2, 1., .1], LEFT=[.4, 0., .2])
    model, library, _, counts = fit_tree(rows)
    tree = model['tree']
    assert tree['kind'] == 'split' and tree['feature'] == 1 and tree['threshold'] == 0.
    assert tree['training_utility_before'] == pytest.approx(.3)
    assert tree['training_utility_after'] == pytest.approx(.6)
    assert tree['improvement'] == pytest.approx(.3)
    assert tree['left']['mean'] == pytest.approx([.8, 1., -.1])
    assert tree['right']['mean'] == pytest.approx([-.8, -1., .1])
    observed = root('query'); observed['immediate_rewards'] = dict(DOWN=.1, LEFT=.3)
    observed['action_components'] = {'irrelevant_TARGET_truth': [999., 999., 999.]}
    decision = core.choose_action(model, programs._observable(observed), library)
    assert decision['canonical_action'] == 'LEFT'
    assert decision['estimated_pairs']['DOWN|LEFT']['estimated_tail_delta'] == pytest.approx([.8, 1., -.1])
    assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx([.6, 1., -.1])
    assert decision['work']['pair_reward_additions'] == 2
    assert counts['training_decoder_epsilon_checks'] == 4*counts['training_root_decisions']


def test_preorder_context_rejects_two_joint_changes_without_single_step_gain():
    rows = [root(f'fixture:{index:02d}', index//2) for index in range(16)]
    for index, observed in enumerate(rows):
        context = int(index >= 8)
        observed['program_contracts'] = dict(DOWN=contract(0, context), LEFT=contract(1, context))
        observed['action_components'] = dict(DOWN=[.2, 0., 0.] if context else [0., 1., 0.], LEFT=[0., 0., 0.])
    model, library, _, _ = fit_tree(rows, depth=6)
    tree = model['tree']
    assert tree['kind'] == 'split' and tree['feature'] == 1
    assert tree['training_utility_before'] == pytest.approx(-.4)
    assert tree['training_utility_after'] == pytest.approx(0.)
    assert tree['left']['kind'] == tree['right']['kind'] == 'leaf'
    assert core.choose_action(model, programs._observable(rows[-1]), library)['canonical_action'] == 'LEFT'
    # Simultaneously refining both sides would fix the remaining group, but
    # neither refinement alone earns gain in the frozen greedy whole-tree state.
    joint = deepcopy(model)
    joint['tree']['left'] = dict(kind='split', feature=4, threshold=0.,
        left=dict(kind='leaf', node_id=3, mean=[0., 1., 0.]),
        right=dict(kind='leaf', node_id=4, mean=[.2, 0., 0.]))
    joint['tree']['right'] = dict(kind='split', feature=4, threshold=0.,
        left=dict(kind='leaf', node_id=5, mean=[0., -1., 0.]),
        right=dict(kind='leaf', node_id=6, mean=[-.2, 0., 0.]))
    assert core.choose_action(joint, programs._observable(rows[-1]), library)['canonical_action'] == 'DOWN'


@pytest.mark.parametrize('action_count', [3, 4])
def test_incidence_matches_full_direction_projection_and_exact_actions(action_count):
    rows = [root(f'fixture:{index}', index//2) for index in range(4)]
    legal = list(core.ACTIONS[:action_count])
    for observed in rows:
        observed['legal_actions'] = legal
        observed['program_contracts'] = {action: contract(index) for index, action in enumerate(legal)}
        observed['immediate_rewards'] = {action: .05*(index+1) for index, action in enumerate(legal)}
        observed['action_components'] = {action: [.2*index, .1*index, .3*index] for index, action in enumerate(legal)}
    library, view = library_and_view(rows)
    left = [index for index, row in enumerate(library['prototypes']) if row['features162'][1] <= 0.]
    right = [index for index in range(len(library['prototypes'])) if index not in left]
    mean, left_mean, right_mean = np.array([.05, .03, .07]), np.array([-.3, .4, -.2]), np.array([.5, -.1, .6])
    left_h, right_h = core._incidence(view, left, Counter()), core._incidence(view, right, Counter())
    theta = left_h[:, :, None]*(left_mean-mean)+right_h[:, :, None]*(right_mean-mean)
    model = programs._base_model('UTILITY', library)
    model['tree'] = dict(kind='split', feature=1, threshold=0.,
        left=dict(kind='leaf', node_id=1, mean=left_mean.tolist()),
        right=dict(kind='leaf', node_id=2, mean=right_mean.tolist()))
    selected = core._training_actions(theta, view, Counter())
    actual_values = []
    for index, observed in enumerate(rows):
        decision = programs.choose_action(model, programs._observable(observed), library)
        assert core.ACTIONS[selected[index]] == decision['canonical_action']
        for action in legal:
            column = core.ACTIONS.index(action)
            expected = theta[index, column].copy(); expected[0] += observed['immediate_rewards'][action]
            assert decision['predicted_components'][action] == pytest.approx(expected.tolist(), abs=core.EPSILON)
        truth = observed['action_components'][decision['canonical_action']]
        actual_values.append(truth[0]-truth[1]+truth[2])
    assert core._training_utility(theta, view, Counter()) == pytest.approx(sum(actual_values)/4)


def test_forced_group_denominators_child_support_and_epsilon_order():
    first, second, forced = root('a'), root('b', 1), root('c', 1)
    first['action_components'] = dict(DOWN=[2., 0., 0.], LEFT=[0., 0., 0.])
    second['action_components'] = dict(DOWN=[4., 0., 0.], LEFT=[0., 0., 0.])
    forced['legal_actions'] = ['DOWN']; forced['fallback_action'] = 'DOWN'
    forced['action_components'] = dict(DOWN=[8., 0., 0.])
    library, view = library_and_view([first, second, forced])
    assert view['root_weights'].tolist() == [.5, .25, .25]
    theta = np.zeros((3, 4, 3))
    assert core._training_utility(theta, view, Counter()) == 4.
    view['rewards'][0, 1] = core.EPSILON/2
    assert core.ACTIONS[core._training_actions(theta, view, Counter())[0]] == 'DOWN'
    view['rewards'][0, 1] = 2*core.EPSILON
    assert core.ACTIONS[core._training_actions(theta, view, Counter())[0]] == 'LEFT'
    single_source = [root(f'fixture:{index}', 0) for index in range(4)]
    model, _, _, _ = fit_tree(single_source)
    assert model['tree']['kind'] == 'leaf'
    two_sources = [root(f'fixture:{index}', index//2) for index in range(4)]
    model, _, _, _ = fit_tree(two_sources, support=8)
    assert model['tree']['kind'] == 'leaf'
    assert library['source_root_counts'] == {'DESIGN_SOURCE:00': 1, 'DESIGN_SOURCE:01': 2}


def test_source_actual_cv_fits_seventeen_and_keeps_libraries_and_decoder_label_free(monkeypatch):
    rows = source_examples(); libraries = supplied_libraries(rows)
    before_rows, before_libraries = deepcopy(rows), deepcopy(libraries)
    calls, deciding = Counter(), programs._decision
    def label_free(model, observable, library, query, counts):
        assert not {'action_components', 'oracle_action', 'teacher_action_native'} & set(observable)
        calls['heldout_decisions'] += 1
        return deciding(model, observable, library, query, counts)
    monkeypatch.setattr(programs, '_decision', label_free)
    result = core.fit_models(rows+[dict(life=1)], libraries)
    assert rows == before_rows and libraries == before_libraries
    assert set(result) == {'models', 'selection', 'costs'}
    selected, costs = result['selection']['UTILITY'], result['costs']
    assert selected['selected_depth'] == 1 and selected['selected_min_leaf_roots'] == 4
    assert selected['selected_utility'] == pytest.approx(.1)
    assert calls['heldout_decisions'] == 8*143
    assert costs['tree_fit_attempts'] == costs['tree_predictors_fitted'] == costs['new_predictors_fitted'] == 17
    assert costs['UTILITY_tree_fit_attempts'] == costs['UTILITY_tree_predictors_fitted'] == 17
    assert costs['training_view_preparations'] == 3 and costs['training_view_roots'] == 286
    assert costs['query_input_roots'] == 143 and costs['shared_library_preparations'] == 0
    assert costs['heldout_action_vector_reads'] == 8*143
    assert costs['new_environment_samples'] == costs['new_source_games'] == costs['new_native_weight_updates'] == 0
    assert result['models']['UTILITY']['library_id'] == 'FULL'
    for candidate in selected['candidates']:
        for fold in candidate['fold_results']:
            assert 'prototypes' not in fold and 'library' not in fold
            assert all(set(choice) == {'root_id', 'source_id', 'canonical_action', 'components', 'utility'}
                       for choice in fold['choices'])


def test_full_fit_failure_retains_sixteen_completed_fits_and_paid_prefix_work(monkeypatch):
    rows = source_examples(); libraries = supplied_libraries(rows)
    moments = core._moments
    def fail_full(prototypes, indices, counts):
        result = moments(prototypes, indices, counts)
        if len(prototypes) == 286 and len(indices) == 286:
            raise ArithmeticError('synthetic selected-full moment failure')
        return result
    monkeypatch.setattr(core, '_moments', fail_full)
    with pytest.raises(core.PairExecutionError) as raised:
        core.fit_models(rows, libraries)
    record = raised.value.record
    assert record['operation'] == 'utility_source_selection'
    assert record['costs']['tree_fit_attempts'] == record['costs']['UTILITY_tree_fit_attempts'] == 17
    assert record['costs']['tree_predictors_fitted'] == record['costs']['new_predictors_fitted'] == 16
    assert record['costs']['training_view_preparations'] == 3
    assert record['costs']['query_input_roots'] == 143
    assert record['costs']['tree_prefix_sample_updates'] > 0
    assert record['costs']['training_actual_component_reads'] > 0
    assert record['costs']['shared_library_preparations'] == 0
