"""Pure witnesses for local rank information, source-only encoding and utility."""
from collections import Counter
from copy import deepcopy

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from acfqp.science import controlled_predictive_shared_consequences_v179 as old
from acfqp.science import controlled_predictive_rank_layout_consequences_v182 as core


WEIGHTS = np.asarray([[.25, -.1, .1], [.02, -.01, .01], [.04, -.02, .02],
                      [.03, -.03, .03], [.1, -.04, .04], [.07, -.03, .03]])


def layout(board=None, aggregate=None):
    """Independent cache fixture with all physical zero-inclusive token sites."""
    board = list(board if board is not None else [0]*16)
    return dict(aggregate=list(aggregate if aggregate is not None else [0.]*6),
        tokens=[['cell', i, rank] for i, rank in enumerate(board)]
        + [['horizontal', 4*r+c, board[4*r+c], board[4*r+c+1]] for r in range(4) for c in range(3)]
        + [['vertical', 4*r+c, board[4*r+c], board[4*(r+1)+c]] for r in range(3) for c in range(4)])


def examples():
    rows = []
    for source in range(12):
        for index in range(4):
            ordinal = source*4+index
            feature = [0.]*6
            feature[ordinal % 6] = 1.
            features = dict(DOWN=layout(aggregate=feature), LEFT=layout())
            rewards = dict(DOWN=(ordinal % 3)/2048., LEFT=1/2048.)
            offset = np.asarray([10.+ordinal, .5, .5])
            components = {}
            for action, record in features.items():
                vector = offset+np.asarray(record['aggregate']) @ WEIGHTS
                vector[0] += rewards[action]
                components[action] = vector.tolist()
            rows.append(dict(root_id=f'root:{ordinal:02d}', life=0, source_id=f'DESIGN_SOURCE:{source:02d}',
                canonical_board=[0]*16, legal_actions=['DOWN', 'LEFT'], immediate_rewards=rewards,
                layout_features=features, action_components=components,
                fallback_action='LEFT', action_map=dict(DOWN='UP', LEFT='RIGHT')))
    return rows


def test_local_ranks_break_aggregate_alias_and_zero_gaps_remain_physical_tokens():
    low = core.action_features_from_root(dict(canonical_board=[1, 1, 0, 0]*3+[0]*4))
    high = core.action_features_from_root(dict(canonical_board=[7, 7, 0, 0]*3+[0]*4))
    assert low['RIGHT']['aggregate'] == high['RIGHT']['aggregate'] == [0, 13, 2, 0, 0, 0]
    assert low['RIGHT']['tokens'] != high['RIGHT']['tokens']
    gap = core.action_features_from_root(dict(canonical_board=[1, 0, 1, 0]+[0]*12))['DOWN']
    assert gap['aggregate'][2] == 1  # The retained aggregate compresses gaps.
    assert ['horizontal', 12, 1, 0] in gap['tokens']
    assert ['horizontal', 13, 0, 1] in gap['tokens']
    assert ['horizontal', 12, 1, 1] not in gap['tokens']
    assert ['cell', 0, 0] in gap['tokens'] and len(gap['tokens']) == 40


def test_one_swipe_per_action_and_rotation_preserve_original_aggregate_semantics(monkeypatch):
    root = dict(canonical_board=[1, 1, 0, 0]*3+[0]*4)
    old_features = old.action_features_from_root(root)
    calls, swipe = [], ground.swipe_board_v1
    def counted(board, action):
        calls.append(action.value)
        return swipe(board, action)
    monkeypatch.setattr(core.ground, 'swipe_board_v1', counted)
    counts = Counter()
    features = core.action_features_from_root(root, counts)
    assert calls == list(core.ACTIONS) and counts['layout_ground_swipe_calls'] == 4
    assert {a: record['aggregate'] for a, record in features.items()} == old_features
    assert counts['layout_tokens_formed'] == 40*len(features)
    rotated = ground.transform_board_v1(tuple(root['canonical_board']), D4Transform.ROTATE_90)
    transported = core.action_features_from_root(dict(canonical_board=rotated))
    for action, record in features.items():
        moved = ground.transform_action_v1(ground.Swipe2048Action(action), D4Transform.ROTATE_90).value
        assert transported[moved] == record


def test_source_only_vocabulary_keeps_aggregates_unscaled_and_one_full_vector_solve():
    rows = examples()
    foreign = dict(root_id='foreign', life=1, layout_features=dict(DOWN=layout([99]*16)))
    fitted = core.fit_model(rows+[foreign])
    assert fitted['vocabulary'] == sorted(fitted['vocabulary'], key=tuple)
    assert len(fitted['vocabulary']) == 40 and all(99 not in token for token in fitted['vocabulary'])
    assert np.asarray(fitted['coefficients'][:6]) == pytest.approx(WEIGHTS, abs=1e-12)
    assert np.asarray(fitted['coefficients'][6:]) == pytest.approx(np.zeros((40, 3)), abs=1e-12)
    assert fitted['rank'] == 6 and fitted['loss'] < 1e-24
    assert fitted['fit_counts']['layout_lstsq_solves'] == 1
    assert fitted['fit_counts']['layout_pair_rows'] == 48
    assert fitted['encoder_counts']['token_lookups'] == 48*2*40
    assert fitted['feature_counts']['layout_feature_cache_hits'] == 48
    assert 'layout_ground_swipe_calls' not in fitted['feature_counts']
    assert len(fitted['training_outcomes'][0]['canonical_board']) == 16
    assert fitted['constants']['token_weights']['cell'] == .25
    for block, count in (('cell', 16), ('horizontal', 12), ('vertical', 12)):
        assert count*core.TOKEN_WEIGHTS[block]**2 == pytest.approx(1.)


def test_root_pair_weights_preserve_varying_legality_and_complete_residual_vectors():
    rows = examples()
    for ordinal, root in enumerate(rows):
        three = ordinal % 4 >= 2
        legal = ['DOWN', 'LEFT', 'UP'] if three else ['DOWN', 'LEFT']
        root['legal_actions'] = legal
        root['layout_features'] = {a: layout(aggregate=[0., float(a == 'DOWN'), 0., 0., 0., 0.]) for a in legal}
        root['immediate_rewards'] = {a: 0. for a in legal}
        root['action_components'] = {a: [10.+(2. if not three and a == 'DOWN' else 0.),
            .5-(.4 if not three and a == 'DOWN' else 0.),
            .5+(.4 if not three and a == 'DOWN' else 0.)] for a in legal}
    fitted = core.fit_model(rows)
    assert fitted['coefficients'][1] == pytest.approx([1.2, -.24, .24])
    assert fitted['component_losses'] == pytest.approx([38.4, 1.536, 1.536])
    assert fitted['fit_counts']['layout_pair_rows'] == 96
    for label in fitted['fit_labels']:
        assert sum(pair['weight'] for pair in label['pairs']) == pytest.approx(1.)
        assert 'suffixes' not in label
    residual = next(row for row in fitted['fit_residuals'] if row['root_id'] == 'root:00')
    assert residual['components'] == pytest.approx([2., -.4, .4])
    assert residual['residual_components'] == pytest.approx([-.8, .16, -.16])
    assert sum(row['weighted_loss'] for row in fitted['fit_residuals']) == pytest.approx(fitted['loss'])


def test_rank_tokens_learn_shared_contrasts_while_common_vectors_and_reward_cancel():
    rows = examples()
    for root in rows:
        root['layout_features'] = dict(DOWN=layout([1]+[0]*15), LEFT=layout([2]+[0]*15))
        root['action_components'] = dict(DOWN=[10.+root['immediate_rewards']['DOWN']+2., .1, .9],
                                        LEFT=[10.+root['immediate_rewards']['LEFT'], .5, .5])
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
    root['immediate_rewards'] = dict(DOWN=.25, LEFT=.5)
    decision = core.choose_action(original, root)
    assert decision['canonical_action'] == 'DOWN' and not decision['fallback']
    assert decision['predicted_pairs']['DOWN|LEFT'] == pytest.approx([1.75, -.4, .4])
    assert decision['predicted_components']['DOWN'][1] < 0.  # Relative vectors are not probabilities.
    assert all(column >= 6 for pair in original['fit_residuals'] for column, _ in pair['design'])
    assert original['rank'] == 1 and original['loss'] < 1e-24


def test_unseen_tokens_are_zero_without_novelty_fallback_and_reward_is_added_once():
    fitted = core.fit_model(examples())
    fitted['coefficients'] = [[0., 0., 0.]]*6+[[100., -100., 100.]]*len(fitted['vocabulary'])
    root = deepcopy(examples()[0])
    root['layout_features'] = dict(DOWN=layout([99]*16), LEFT=layout([99]*16))
    root['immediate_rewards'] = dict(DOWN=.25, LEFT=.5)
    decision = core.choose_action(fitted, root)
    assert decision['canonical_action'] == 'LEFT' and not decision['fallback']
    assert decision['predicted_components'] == dict(DOWN=[.25, 0., 0.], LEFT=[.5, 0., 0.])
    assert decision['predicted_pairs']['DOWN|LEFT'] == [-.25, 0., 0.]
    for coverage in decision['coverage'].values():
        assert coverage == dict(known_tokens=0, unknown_tokens=40, total_tokens=40)
    assert decision['work']['unknown_token_entries'] == 80
    assert 'known_token_entries' not in decision['work']


def test_full_vector_utility_and_fixed_ties_select_one_action():
    fitted = core.fit_model(examples())
    fitted['coefficients'] = [[0., 0., 0.] for _ in fitted['coefficients']]
    fitted['coefficients'][0], fitted['coefficients'][1] = [2., 3., 0.], [0., 0., 1.]
    root = deepcopy(examples()[0])
    root['layout_features'] = dict(DOWN=layout(aggregate=[1., 0., 0., 0., 0., 0.]),
                                 LEFT=layout(aggregate=[0., 1., 0., 0., 0., 0.]))
    root['immediate_rewards'] = dict(DOWN=0., LEFT=0.)
    decision = core.choose_action(fitted, root)
    assert decision['canonical_action'] == 'LEFT' and decision['actual_action'] == 'RIGHT'
    assert decision['predicted_components'] == dict(DOWN=[2., 3., 0.], LEFT=[0., 0., 1.])
    root['layout_features']['LEFT'] = deepcopy(root['layout_features']['DOWN'])
    assert core.choose_action(fitted, root)['canonical_action'] == 'DOWN'


def test_support_fallback_disconnected_actions_and_single_legal_forcing():
    fitted = core.fit_model(examples())
    root = deepcopy(examples()[0])
    root.update(legal_actions=['DOWN', 'LEFT', 'RIGHT'], fallback_action='LEFT',
                immediate_rewards=dict(DOWN=0., LEFT=1., RIGHT=0.),
                layout_features=dict(DOWN=layout(), LEFT=layout(), RIGHT=layout([99]*16)))
    root['oracle_action'], root['teacher_action'] = 'RIGHT', 'RIGHT'
    missing = core.choose_action(fitted, root)
    assert missing['fallback'] and missing['canonical_action'] == 'LEFT'
    assert missing['reason'] == 'insufficient_action_support'
    assert not missing['support']['complete']
    root = deepcopy(examples()[0])
    disconnected = deepcopy(fitted)
    disconnected['connected_components'] = [['DOWN'], ['LEFT'], ['RIGHT'], ['UP']]
    assert core.choose_action(disconnected, root)['reason'] == 'disconnected_required_actions'
    root.update(legal_actions=['UP'], fallback_action='UP', immediate_rewards=dict(UP=0.),
                layout_features=dict(UP=layout()), action_map=dict(UP='DOWN'))
    forced = core.choose_action(fitted, root)
    assert not forced['fallback'] and forced['canonical_action'] == 'UP'
    assert forced['reason'] == 'single_legal_action' and forced['actual_action'] == 'DOWN'


def test_cached_fit_and_choice_never_repeat_swipes_or_read_decision_labels(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('cached layout repeated a ground swipe')
    monkeypatch.setattr(core.ground, 'swipe_board_v1', forbidden)
    fitted = core.fit_model(examples())
    root, counts = deepcopy(examples()[0]), Counter()
    before = core.choose_action(fitted, root, counts)
    root['action_components'] = dict(DOWN=[1e9, 0., 1.], LEFT=[-1e9, 1., 0.])
    root['oracle_action'] = root['teacher_action'] = 'LEFT'
    assert core.choose_action(fitted, root) == before
    assert counts['layout_feature_cache_hits'] == 1
    assert counts['layout_cached_token_records'] == 80
    assert counts['token_lookups'] == 80 and counts['encoded_actions'] == 2
    assert 'layout_ground_swipe_calls' not in counts
