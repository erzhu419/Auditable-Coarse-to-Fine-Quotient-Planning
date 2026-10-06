"""Pure witnesses for ridge scaling, heldout utility and the label boundary."""
from copy import deepcopy

import numpy as np
import pytest

from acfqp.science import controlled_predictive_rank_layout_consequences_v182 as old
from acfqp.science import controlled_predictive_source_regularization_v183 as core


TAIL = np.asarray([1., -.2, .2])


def layout(rank=0, active=False):
    board = [rank]+[0]*15
    return dict(aggregate=[float(active), 0., 0., 0., 0., 0.],
        tokens=[['cell', i, value] for i, value in enumerate(board)]
        + [['horizontal', 4*r+c, board[4*r+c], board[4*r+c+1]] for r in range(4) for c in range(3)]
        + [['vertical', 4*r+c, board[4*r+c], board[4*(r+1)+c]] for r in range(3) for c in range(4)])


def examples():
    rows = []
    for source in range(12):
        for index in range(4):
            ordinal = 4*source+index
            rewards = dict(DOWN=(ordinal % 3)/2048., LEFT=1/2048.)
            offset = np.asarray([3.+ordinal, .5, .5])
            down, left = offset+TAIL, offset.copy()
            down[0] += rewards['DOWN']; left[0] += rewards['LEFT']
            rows.append(dict(root_id=f'root:{ordinal:02d}', life=0, source_id=f'DESIGN_SOURCE:{source:02d}',
                canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'], immediate_rewards=rewards,
                layout_features=dict(DOWN=layout(active=True), LEFT=layout()),
                action_components=dict(DOWN=down.tolist(), LEFT=left.tolist()),
                fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT')))
    return rows


def policy_counterexample():
    rows = examples()
    for index, root in enumerate(rows):
        good = index % 4 == 0
        root['immediate_rewards'] = dict(DOWN=0., LEFT=0. if good else .5)
        root['action_components'] = dict(DOWN=[2. if good else .2, 0., 0.],
                                        LEFT=[root['immediate_rewards']['LEFT'], 0., 0.])
    return rows


def test_zero_matches_frozen_minimum_norm_coefficients_and_full_vectors():
    rows = examples()
    reference = old.fit_model(rows)
    fitted = core.fit_model(rows, 0.)
    assert np.asarray(fitted['coefficients']) == pytest.approx(np.asarray(reference['coefficients']), abs=1e-12)
    assert fitted['rank'] == reference['rank'] == 1
    assert fitted['coefficients'][0] == pytest.approx(TAIL)
    assert fitted['loss'] < 1e-24 and fitted['penalty'] == 0.
    assert fitted['fit_counts']['ridge_svd_decompositions'] == 1
    assert fitted['fit_counts']['ridge_coefficient_filters'] == 1
    assert fitted['mode'] == 'RIDGE'


def test_root_mean_penalty_shrinkage_uses_roots_not_number_of_pairs():
    rows = examples()
    for index, root in enumerate(rows):
        if index % 2:
            root['legal_actions'].append('UP')
            root['layout_features']['UP'] = layout()
            root['immediate_rewards']['UP'] = root['immediate_rewards']['LEFT']
            root['action_components']['UP'] = list(root['action_components']['LEFT'])
    fitted = core.fit_model(rows, 1.)
    # 24 two-action roots contribute1, 24 three-action roots contribute2/3:
    # X'X=40 and the root-mean objective adds48*lambda, giving40/88.
    assert fitted['coefficients'][0] == pytest.approx(TAIL*5/11)
    assert fitted['fit_counts']['paired_vector_labels'] == 96
    for label in fitted['fit_labels']:
        assert sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.)
    assert fitted['penalty'] == pytest.approx(np.sum((TAIL*5/11)**2))
    assert fitted['objective'] == pytest.approx(fitted['loss']/48+fitted['penalty'])


def test_relative_vectors_cancel_common_offsets_and_add_exact_reward_once():
    rows = examples()
    original = core.fit_model(rows, 1.)
    shifted = deepcopy(rows)
    for root in shifted:
        for action in root['legal_actions']:
            root['action_components'][action] = [root['action_components'][action][0]+100.,
                root['action_components'][action][1]+.1, root['action_components'][action][2]-.1]
    changed = core.fit_model(shifted, 1.)
    assert np.asarray(changed['coefficients']) == pytest.approx(np.asarray(original['coefficients']), abs=1e-12)
    root = deepcopy(rows[0])
    root['immediate_rewards'] = dict(DOWN=0., LEFT=.8)
    decision = core.choose_action(original, root)
    assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
    assert decision['predicted_components']['DOWN'] == pytest.approx([.5, -.1, .1])
    assert decision['predicted_components']['LEFT'] == pytest.approx([.8, 0., 0.], abs=1e-12)
    assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx([-.3, -.1, .1])


def test_fold_vocabulary_and_support_exclude_heldout_groups_and_other_lives():
    rows = examples()
    for root in rows:
        source = int(root['source_id'].rsplit(':', 1)[1])
        root['layout_features'] = dict(DOWN=layout(source+1, True), LEFT=layout(source+1))
    selection = core.select_regularization(rows+[dict(life=1, root_id='other-life')])
    assert selection['source_folds'] == [[f'DESIGN_SOURCE:{i:02d}' for i in range(0, 12, 2)],
                                         [f'DESIGN_SOURCE:{i:02d}' for i in range(1, 12, 2)]]
    for fold in selection['folds']:
        design = fold['design']
        assert len(design['root_ids']) == 24
        assert set(fold['train_sources']).isdisjoint(fold['heldout_sources'])
        assert set(design['source_ids']) == set(fold['train_sources'])
        assert len(design['action_root_ids']['DOWN']) == len(design['action_root_ids']['LEFT']) == 24
        assert 'X' not in design and 'Y' not in design
        assert 'left' not in fold['decomposition'] and 'right' not in fold['decomposition']
        for source in fold['heldout_sources']:
            rank = int(source.rsplit(':', 1)[1])+1
            assert ['cell', 0, rank] not in design['vocabulary']
    assert all(root_id != 'other-life' for root_id in selection['model']['root_ids'])
    assert len(selection['model']['root_ids']) == 48


def test_actual_heldout_policy_utility_selects_ridge_despite_higher_training_sse():
    selection = core.select_regularization(policy_counterexample())
    assert selection['selected_lambda'] == 1.
    assert selection['selected_utility'] == pytest.approx(.875)
    zero, ridge = selection['candidates'][0], selection['candidates'][-1]
    assert zero['utility'] == pytest.approx(.65)
    assert ridge['fold_results'][0]['loss'] > zero['fold_results'][0]['loss']
    for fold in ridge['fold_results']:
        for choice in fold['choices']:
            ordinal = int(choice['root_id'].rsplit(':', 1)[1])
            assert choice['decision']['canonical_action'] == ('DOWN' if ordinal % 4 == 0 else 'LEFT')
    assert selection['costs']['ridge_svd_decompositions'] == 3
    assert selection['costs']['ridge_coefficient_filters'] == 13
    assert selection['costs']['ridge_predictors_fitted'] == 13
    assert selection['costs']['heldout_action_vector_reads'] == 6*48


def test_equal_source_weighting_and_exact_grid_ties_are_preserved():
    rows = policy_counterexample()
    rows = [root for root in rows if root['source_id'] != 'DESIGN_SOURCE:00' or root['root_id'] == 'root:00']
    selection = core.select_regularization(rows)
    zero = selection['candidates'][0]
    assert zero['utility'] == pytest.approx((2.+11*.65)/12)
    root_mean = np.mean([choice['utility'] for fold in zero['fold_results'] for choice in fold['choices']])
    assert zero['utility'] != pytest.approx(root_mean)
    tied_rows = examples()
    for root in tied_rows:
        root['layout_features'] = dict(DOWN=layout(), LEFT=layout())
    tied = core.select_regularization(tied_rows)
    assert len({round(candidate['utility'], 12) for candidate in tied['candidates']}) == 1
    assert tied['selected_lambda'] == core.LAMBDAS[0] == 0.


def test_training_only_support_and_explicit_observable_label_boundary(monkeypatch):
    rows = examples()
    for root in rows:
        source = int(root['source_id'].rsplit(':', 1)[1])
        root.update(oracle_action='RIGHT', teacher_action_native='RIGHT',
                    action_component_fractions={'DOWN': ['secret']})
        if source % 2 == 0:
            root['legal_actions'].append('RIGHT')
            root['layout_features']['RIGHT'] = layout()
            root['immediate_rewards']['RIGHT'] = 0.
            root['action_components']['RIGHT'] = [100., 0., 1.]
    chooser = core.choose_action
    observed_keys = {'root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
                     'immediate_rewards', 'fallback_action', 'layout_features', 'action_map'}
    def observable_only(model, root, counts=None):
        assert set(root) == observed_keys
        return chooser(model, root, counts)
    def forbidden(*args, **kwargs):
        raise AssertionError('regularization recomputed cached afterstates')
    monkeypatch.setattr(core, 'choose_action', observable_only)
    monkeypatch.setattr(old.ground, 'swipe_board_v1', forbidden)
    selection = core.select_regularization(rows)
    for candidate in selection['candidates']:
        even_heldout = candidate['fold_results'][0]
        for choice in even_heldout['choices']:
            assert choice['decision']['fallback']
            assert choice['decision']['canonical_action'] == 'LEFT'
            assert choice['decision']['support']['action_root_counts']['RIGHT'] == 0
            assert choice['decision']['reason'] == 'insufficient_action_support'
    assert 'layout_ground_swipe_calls' not in selection['costs']


def test_solver_failure_retains_attempt_cost_instead_of_a_scientific_result(monkeypatch):
    def fail(*args, **kwargs):
        raise np.linalg.LinAlgError('synthetic SVD failure')
    monkeypatch.setattr(core.np.linalg, 'svd', fail)
    with pytest.raises(core.RegularizationExecutionError) as raised:
        core.select_regularization(examples())
    record = raised.value.record
    assert record['operation'] == 'svd'
    assert record['costs']['ridge_svd_attempts'] == 1
    assert record['costs'].get('ridge_svd_decompositions', 0) == 0
    assert record['costs']['ridge_design_preparations'] == 1
    assert 'synthetic SVD failure' in record['error']
