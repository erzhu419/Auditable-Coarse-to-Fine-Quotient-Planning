"""Finite replay timing, terminal labels and unchanged native joint updates."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import controlled_predictive_terminal_supervision_v137 as core
from acfqp.science.controlled_predictive_bellman_consequences_v136 import PolicyComponents
from acfqp.science.controlled_predictive_contextual_ntuple_v134 import ConditionalQueryTD
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/controlled_predictive_terminal_supervision_v137_build'
MODELS, NATIVE_MODELS, SOURCES, REPLAYS = [], [], [], []
FIXTURE_WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_terminal_supervision_v137.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        model_work=dict(sum((model.counts for model in MODELS+NATIVE_MODELS), Counter())),
        setup_work=dict(sum((model.setup_counts for model in NATIVE_MODELS+SOURCES), Counter())),
        replay_work=dict(sum((Counter(row['replay_counts']) for row in REPLAYS), Counter())),
        fixture_work=dict(FIXTURE_WORK), newly_sampled_environment_transitions=0,
        newly_sampled_model_transitions=0,
        scope='Finite recorded boards and unchanged native updates; no natural-game sampling.'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2)+'\n')


class Components:
    """Two interacting parameters make predicting after update observably wrong."""
    def __init__(self):
        self.radix, self.reward_intercept = 11, .3
        self.weights, self.updates, self.counts, self.events = [.4, -.2], 0, Counter(), []
        MODELS.append(self)

    def prediction(self, board):
        if max(board) >= self.radix:
            return dict(raw_reward=0., reward=0., success=1.)
        raw = self.weights[0]+sum(board)*.01
        return dict(raw_reward=raw, reward=raw+self.reward_intercept,
            success=1./(1.+math.exp(-self.weights[1])))

    def value(self, board):
        self.events.append(('value', tuple(board)))
        self.counts['value_calls'] += 1
        return self.prediction(board)

    def update(self, board, target_reward, target_success):
        assert max(board) < self.radix
        self.events.append(('update', tuple(board)))
        value = self.prediction(board)
        raw_target = target_reward-self.reward_intercept
        reward_error = raw_target-value['raw_reward']
        success_error = target_success-value['success']
        self.weights[0] += .0025*reward_error
        self.weights[1] += .0025*success_error
        self.updates += 1
        self.counts.update(td_updates=1, reward_td_updates=1, success_td_updates=1)
        return dict(pre_raw_reward=value['raw_reward'], pre_reward=value['reward'],
            pre_success=value['success'], target_reward=target_reward,
            target_success=target_success, raw_reward_target=raw_target,
            reward_error=reward_error, success_error=success_error, work=dict(td_updates=1))

    def choose(self, *args, **kwargs):
        raise AssertionError('retained replay must never choose an action')


def episode(status):
    if status == 'WON':
        initial = [8, 8, 9, 10]+[0]*12
        actions, cells, ranks = ['LEFT']*3, [4, 8, 12], [1]*3
    else:
        initial = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 1, 2, 1, 0]
        actions, cells, ranks = ['RIGHT'], [12], [2]
    board, scores, afterstates = tuple(initial), [], []
    for action, cell, rank in zip(actions, cells, ranks):
        after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
        FIXTURE_WORK['swipes'] += 1
        assert changed and after[cell] == 0
        afterstates.append(after); scores.append(score)
        board = list(after); board[cell] = rank; board = tuple(board)
    row = dict(episode=0, seed=137, status=status, start_step=0, end_step=len(actions),
        pending_before=None, pending_after=None, start_board=initial, end_board=list(board),
        actions=actions, scores=scores, spawned_cells=cells, spawned_ranks=ranks,
        return_score=sum(scores))
    return row, afterstates


def add_td_source(row, afterstates, model):
    """Write source records in the original V136 pending-update schedule."""
    row['next_components'], row['joint_updates'], row['terminal_update'] = [], [], None
    row['updates_before'] = model.updates
    pending = None
    for board, score in zip(afterstates, row['scores']):
        prediction = model.value(board)
        update = None if pending is None else model.update(pending,
            score/2048.+prediction['reward'], prediction['success'])
        row['next_components'].append(prediction)
        row['joint_updates'].append(update)
        pending = None if max(board) >= model.radix else board
    if row['status'] == 'LOST':
        row['terminal_update'] = model.update(pending, 0., 0.)
        row['terminal_update']['afterstate'] = list(pending)
    row['updates_after'] = model.updates
    return row


def run(model, row, method):
    result = core.replay_episode(model, row, method)
    REPLAYS.append(result)
    return result


def test_td_predicts_before_previous_update_and_retains_winning_action_score():
    row, boards = episode('WON')
    original = Components()
    add_td_source(row, boards, original)
    model = Components()
    result = run(model, row, 'TD')
    assert [event[0] for event in model.events] == ['value', 'value', 'update', 'value', 'update']
    assert model.events[2][1] == boards[0] and model.events[4][1] == boards[1]
    first, last = result['updates']
    assert first['target_reward'] == .5+result['predictions'][1][0]
    assert first['target_success'] == result['predictions'][1][1]
    assert last['target_reward'] == 1. and last['target_success'] == 1.
    assert result['predictions'][-1] == [0., 1.]
    assert model.weights == original.weights
    assert result['td_source_comparison'] == dict(prediction_values_compared=6,
        prediction_values_matched=6, update_values_compared=16, update_values_matched=16, mismatches=0)


def test_terminal_targets_exclude_own_score_include_winning_score_and_never_fit_goal():
    row, boards = episode('WON')
    model = Components()
    result = run(model, row, 'TERMINAL')
    assert [update['target_reward'] for update in result['updates']] == [1.5, 1.]
    assert [update['target_success'] for update in result['updates']] == [1., 1.]
    assert model.events == [('update', boards[0]), ('update', boards[1])]
    assert result['predictions'] == [] and result['td_source_comparison'] is None
    assert result['target_counts'] == dict(suffix_score_additions=3, terminal_labels=2, eligible_targets=2)


@pytest.mark.parametrize('status', ['WON', 'LOST'])
def test_matched_eligible_update_order_loss_boundary_and_zero_sampling(status):
    row, boards = episode(status)
    add_td_source(row, boards, Components())
    td, terminal = Components(), Components()
    left, right = run(td, row, 'TD'), run(terminal, row, 'TERMINAL')
    expected = len(boards)-int(status == 'WON')
    assert left['eligible_updates'] == right['eligible_updates'] == td.updates == terminal.updates == expected
    assert [board for kind, board in td.events if kind == 'update'] == [board for _, board in terminal.events]
    for result in (left, right):
        assert result['replay_counts']['replay_swipes'] == result['steps']
        assert result['replay_counts']['replayed_transitions'] == result['steps']
        assert result['replay_counts']['replayed_spawn_events'] == result['steps']
        assert result['replay_counts']['newly_sampled_environment_transitions'] == 0
        assert result['replay_counts']['newly_sampled_model_transitions'] == 0
    if status == 'LOST':
        assert left['updates'] == right['updates']
        assert left['updates'][-1]['target_reward'] == left['updates'][-1]['target_success'] == 0.
        assert left['target_counts']['terminal_boundary_targets'] == 1


def test_source_numeric_mismatch_is_reported_and_does_not_change_replay_targets():
    row, boards = episode('WON')
    add_td_source(row, boards, Components())
    row['next_components'][1]['success'] += .01
    row['joint_updates'][1]['pre_reward'] += .01
    result = run(Components(), row, 'TD')
    assert result['td_source_comparison']['mismatches'] == 2
    assert result['td_source_comparison']['first_mismatch']['field'] == 'success'
    assert result['updates'][0]['target_success'] != row['next_components'][1]['success']


@pytest.mark.parametrize('change', [dict(status='ACTIVE'), dict(status='CUTOFF'),
    dict(start_step=1), dict(pending_before=[1]*16)])
def test_incomplete_source_is_rejected_before_learning(change):
    row, _ = episode('WON'); row.update(change)
    model = Components()
    with pytest.raises(ValueError, match='complete terminal episode'):
        core.replay_episode(model, row, 'TERMINAL')
    assert model.updates == 0 and not model.counts


def test_recorded_scores_and_endboard_are_checked_before_any_fit():
    row, _ = episode('WON')
    for field in ('scores', 'end_board'):
        broken = deepcopy(row); broken[field][0] += 1
        model = Components()
        with pytest.raises(ValueError, match='score|end board'):
            core.replay_episode(model, broken, 'TERMINAL')
        assert model.updates == 0


def native(representation):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 3)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    source.weights.flags.writeable = False
    SOURCES.append(source)
    query = dict(reward_weight=1., failure_penalty=1., goal_bonus=1.)
    parent = QueryParent(source, query, query, .5)
    leaf = QueryTD(parent, 'PRIOR', BUILD) if representation == 'SINGLE' else ConditionalQueryTD(parent, representation, BUILD)
    leaf.freeze(); SOURCES.append(leaf)
    model = PolicyComponents(leaf, BUILD); NATIVE_MODELS.append(model)
    return model


@pytest.mark.parametrize('representation', ['SINGLE', 'CAPACITY'])
def test_native_joint_update_is_unchanged_and_equal_on_terminal_loss(representation):
    row, boards = episode('LOST')
    original, td, terminal = (native(representation) for _ in range(3))
    add_td_source(row, boards, original)
    left, right = run(td, row, 'TD'), run(terminal, row, 'TERMINAL')
    np.testing.assert_array_equal(td.weights, original.weights)
    np.testing.assert_array_equal(terminal.weights, original.weights)
    assert left['updates'] == right['updates']
    assert left['td_source_comparison']['mismatches'] == 0
    for result in (left, right):
        assert result['model_counts']['reward_td_updates'] == result['model_counts']['success_td_updates'] == 1
        assert result['model_counts']['reward_table_update_occurrences'] == 32
        assert result['model_counts']['success_table_update_occurrences'] == 32
