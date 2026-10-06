"""Pure witnesses for action sharing, complete vectors and root pair weights."""
from collections import Counter
from copy import deepcopy

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from acfqp.science import controlled_predictive_shared_consequences_v179 as core


WEIGHTS = np.asarray([[.25, -.1, .1], [.02, -.01, .01], [.04, -.02, .02],
                      [.03, -.03, .03], [.1, -.04, .04], [.07, -.03, .03]])


def examples():
    """Full-rank synthetic contrast system with varying shared root offsets."""
    rows = []
    for source in range(12):
        for index in range(4):
            ordinal = source*4+index
            feature = [0.]*6
            feature[ordinal % 6] = 1.
            features = dict(DOWN=feature, LEFT=[0.]*6)
            rewards = dict(DOWN=(ordinal % 3)/2048., LEFT=1/2048.)
            offset = np.asarray([10.+ordinal, .5, .5])
            components = {}
            for action, vector in features.items():
                full = offset+np.asarray(vector) @ WEIGHTS
                full[0] += rewards[action]
                components[action] = full.tolist()
            rows.append(dict(root_id=f'root:{ordinal:02d}', life=0, source_id=f'DESIGN_SOURCE:{source:02d}',
                canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'], immediate_rewards=rewards,
                action_features=features, action_components=components,
                fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT')))
    return rows


def test_unique_rotations_align_action_with_down_and_swap_row_column_geometry():
    for action in core.ACTIONS:
        matches = [rotation for rotation in core.ROTATIONS if ground.transform_action_v1(
            ground.Swipe2048Action(action), rotation) == ground.Swipe2048Action.DOWN]
        assert len(matches) == 1 and 'reflect' not in matches[0].value
    root = dict(canonical_board=[1, 1, 0, 0]*3+[0]*4)
    features = core.action_features_from_root(root)
    assert features['RIGHT'] == [0, 13, 2, 0, 0, 0]
    rotated = ground.transform_board_v1(tuple(root['canonical_board']), D4Transform.ROTATE_90)
    rotated_features = core.action_features_from_root(dict(canonical_board=rotated))
    for action, vector in features.items():
        transported = ground.transform_action_v1(ground.Swipe2048Action(action), D4Transform.ROTATE_90).value
        assert rotated_features[transported] == vector


def test_feature_goal_event_pending_pairs_and_illegal_action_mask_have_actual_work():
    reached = core.action_features_from_root(dict(canonical_board=[10, 10, 0, 0]+[0]*12))
    pending = core.action_features_from_root(dict(canonical_board=[9, 9, 10, 0]+[0]*12))
    assert reached['RIGHT'] == [1, 15, 0, 0, 0, 0]
    assert pending['RIGHT'] == [0, 14, 0, 1, 0, 1]
    counts = Counter()
    features = core.action_features_from_root(dict(canonical_board=[1, 0, 0, 0]+[0]*12), counts)
    assert set(features) == {'DOWN', 'RIGHT'}
    assert counts['shared_ground_swipe_calls'] == 4 and counts['shared_afterstate_rotations'] == 2
    assert counts['shared_goal_tile_reads'] == counts['shared_vacancy_tile_reads'] == 32
    assert counts['shared_line_tile_reads'] == 64 and counts['shared_adjacent_slots_inspected'] == 48


def test_one_shared_solve_recovers_full_vector_coefficients_and_new_action_feature_order():
    rows = examples()
    fitted = core.fit_model(rows)
    assert np.asarray(fitted['coefficients']) == pytest.approx(WEIGHTS, abs=1e-12)
    assert fitted['rank'] == 6 and len(fitted['singular_values']) == 6
    assert fitted['loss'] < 1e-24 and fitted['component_losses'] == pytest.approx([0., 0., 0.], abs=1e-24)
    assert fitted['fit_counts']['shared_lstsq_solves'] == 1
    assert fitted['fit_counts']['shared_pair_rows'] == 48
    assert fitted['fit_counts']['shared_design_matrix_cells'] == 288
    assert fitted['feature_counts']['shared_feature_cache_hits'] == 48
    assert 'shared_ground_swipe_calls' not in fitted['feature_counts']
    root = deepcopy(rows[0])
    root['action_features'] = dict(DOWN=[0.]*6, LEFT=[1., 0., 0., 0., 0., 0.])
    root['immediate_rewards'] = dict(DOWN=0., LEFT=0.)
    decision = core.choose_action(fitted, root)
    assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
    assert not decision['fallback']  # No fixed DOWN bias follows the training action ID.
    assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx(-WEIGHTS[0])
    assert decision['predicted_components']['LEFT'][1] < 0.  # Relative, not clipped probability.


def test_root_pair_normalization_handles_varying_legal_sets_without_triple_root_weight():
    rows = examples()
    for ordinal, root in enumerate(rows):
        three = ordinal % 4 >= 2
        legal = ['DOWN', 'LEFT', 'UP'] if three else ['DOWN', 'LEFT']
        root['legal_actions'] = legal
        root['action_features'] = {action: [0., 1. if action == 'DOWN' else 0., 0., 0., 0., 0.] for action in legal}
        root['immediate_rewards'] = {action: 0. for action in legal}
        root['action_components'] = {action: [10.+(2. if not three and action == 'DOWN' else 0.), .5, .5] for action in legal}
    fitted = core.fit_model(rows)
    assert fitted['coefficients'][1] == pytest.approx([1.2, 0., 0.])
    assert fitted['rank'] == 1 and fitted['component_losses'] == pytest.approx([38.4, 0., 0.])
    for label in fitted['fit_labels']:
        assert sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.)
    assert fitted['fit_counts']['shared_pair_rows'] == 96
    assert all('suffixes' not in label for label in fitted['fit_labels'])
    residual = next(row for row in fitted['fit_residuals'] if row['root_id'] == 'root:00')
    assert residual['components'] == [2., 0., 0.]
    assert residual['residual_components'] == pytest.approx([-.8, 0., 0.])
    assert sum(row['weighted_loss'] for row in fitted['fit_residuals']) == pytest.approx(fitted['loss'])


def test_root_common_vector_offsets_cancel_and_immediate_reward_is_subtracted_then_added_once():
    rows = examples()
    original = core.fit_model(rows)
    shifted = deepcopy(rows)
    for root in shifted:
        for action in root['legal_actions']:
            root['action_components'][action] = [root['action_components'][action][0]+100.,
                                                root['action_components'][action][1]+.1,
                                                root['action_components'][action][2]-.1]
    changed = core.fit_model(shifted)
    assert np.asarray(changed['coefficients']) == pytest.approx(np.asarray(original['coefficients']), abs=1e-12)
    root = deepcopy(rows[0])
    root['action_features'] = dict(DOWN=[0.]*6, LEFT=[0.]*6)
    root['immediate_rewards'] = dict(DOWN=.25, LEFT=.5)
    decision = core.choose_action(original, root)
    assert decision['canonical_action'] == 'LEFT'
    assert decision['predicted_components']['LEFT'] == [.5, 0., 0.]
    assert decision['predicted_pairs']['DOWN|LEFT'] == [-.25, 0., 0.]


def test_full_vector_utility_and_lexical_ties_choose_one_action_without_component_maxima():
    model = core.fit_model(examples())
    model['coefficients'] = [[0., 0., 0.] for _ in range(6)]
    model['coefficients'][0] = [2., 3., 0.]
    model['coefficients'][1] = [0., 0., 1.]
    root = deepcopy(examples()[0])
    root['action_features'] = dict(DOWN=[1., 0., 0., 0., 0., 0.], LEFT=[0., 1., 0., 0., 0., 0.])
    root['immediate_rewards'] = dict(DOWN=0., LEFT=0.)
    decision = core.choose_action(model, root)
    assert decision['canonical_action'] == 'LEFT'
    assert decision['predicted_components'] == dict(DOWN=[2., 3., 0.], LEFT=[0., 0., 1.])
    root['action_features']['LEFT'] = list(root['action_features']['DOWN'])
    assert core.choose_action(model, root)['canonical_action'] == 'DOWN'


def test_insufficient_support_keeps_observable_fallback_even_with_best_shared_prediction():
    model = core.fit_model(examples())
    root = deepcopy(examples()[0])
    root.update(legal_actions=['DOWN', 'LEFT', 'RIGHT'], fallback_action='LEFT',
                immediate_rewards=dict(DOWN=0., LEFT=1., RIGHT=0.),
                action_features=dict(DOWN=[0.]*6, LEFT=[0.]*6, RIGHT=[1.]*6))
    root['oracle_action'], root['teacher_action'] = 'RIGHT', 'RIGHT'
    decision = core.choose_action(model, root)
    assert decision['fallback'] and decision['canonical_action'] == 'LEFT'
    assert decision['reason'] == 'insufficient_action_support' and not decision['support']['complete']
    assert decision['predicted_components']['RIGHT'][0] != 0.


def test_disconnected_singleton_training_has_zero_minimum_norm_model_and_single_legal_forcing():
    rows = examples()
    for ordinal, root in enumerate(rows):
        legal = ['DOWN'] if ordinal % 2 else ['LEFT']
        root['legal_actions'] = legal
        root['action_components'] = {action: root['action_components'][action] for action in legal}
    fitted = core.fit_model(rows)
    assert fitted['rank'] == 0 and fitted['singular_values'] == []
    assert np.asarray(fitted['coefficients']) == pytest.approx(np.zeros((6, 3)))
    root = deepcopy(examples()[0])
    decision = core.choose_action(fitted, root)
    assert decision['fallback'] and decision['reason'] == 'disconnected_required_actions'
    root.update(legal_actions=['UP'], fallback_action='UP', immediate_rewards=dict(UP=0.),
                action_features=dict(UP=[0.]*6), action_map=dict(UP='DOWN'))
    forced = core.choose_action(fitted, root)
    assert not forced['fallback'] and forced['canonical_action'] == 'UP' and forced['reason'] == 'single_legal_action'


def test_cached_fit_and_decisions_do_not_repeat_afterstate_work_or_read_target_labels(monkeypatch):
    rows = examples()
    def forbidden(*args, **kwargs):
        raise AssertionError('cached model repeated a ground swipe')
    monkeypatch.setattr(core.ground, 'swipe_board_v1', forbidden)
    model = core.fit_model(rows)
    root, counts = deepcopy(rows[0]), Counter()
    before = core.choose_action(model, root, counts)
    root['action_components'] = dict(DOWN=[1e9, 0., 1.], LEFT=[-1e9, 1., 0.])
    assert core.choose_action(model, root) == before
    assert counts['shared_feature_cache_hits'] == 1 and counts['shared_cached_feature_reads'] == 12
    assert 'shared_ground_swipe_calls' not in counts
    assert len(model['training_outcomes'][0]['canonical_board']) == 16
