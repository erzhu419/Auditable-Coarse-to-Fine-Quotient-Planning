"""Finite actual-environment suffixes: paired draws, terminal returns, and work."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_counterfactual_outcomes_v143 import run_branch

ROOT = Path(__file__).resolve().parents[1]
QUERY = dict(reward_weight=1., failure_penalty=8., goal_bonus=1.)
SPARSE = [1, 1]+[0]*14
LOSS_ROOT = [1, 1, 3, 4, 5, 6, 7, 8, 9, 10, 9, 10, 8, 7, 6, 5]
ROWS, ORACLE = [], Counter()


class ScriptedFrozenPlanner:
    def __init__(self, actions=()):
        self.actions, self.calls = list(actions), []
        self.counts = Counter(choose_calls=7, value_predictions=11)
        self.weights = np.arange(4.)
        self.weights.flags.writeable = False
        self.updates = 3

    def choose(self, board, query):
        self.calls.append((tuple(board), deepcopy(query)))
        self.counts.update(choose_calls=1, value_predictions=4)
        return dict(action=self.actions[len(self.calls)-1])


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_counterfactual_outcomes_v143.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    environment = sum((Counter(row['result']['environment_counts']) for row in ROWS), Counter())
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        environment_work=dict(environment),
        policy_stub_work=dict(sum((Counter(row['result']['policy_counts']) for row in ROWS), Counter())),
        deterministic_oracle_work=dict(ORACLE),
        newly_sampled_environment_transitions=environment['sampled_transitions'],
        newly_sampled_model_transitions=0,
        scope='Fixed boards and 1-3 action suffixes; no natural games or training.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def branch(*args, **kwargs):
    result = run_branch(*args, **kwargs)
    ROWS.append(result)
    return result


def replay(row, p_four=.1):
    """Reconstruct recorded boards and draws without calling the branch policy."""
    board, rng = tuple(row['root_board']), random.Random(row['seed'])
    boards, afterstates = [board], []
    for action, cell, rank, score in zip(row['actions'], row['spawned_cells'],
                                       row['spawned_ranks'], row['scores'], strict=True):
        after, actual_score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
        ORACLE['explicit_ground_swipe_calls'] += 1
        assert changed and actual_score == score
        empty = [i for i, value in enumerate(after) if not value]
        assert cell == empty[int(rng.random()*len(empty))]
        assert rank == (1 if rng.random() < 1.-p_four else 2)
        ORACLE['replayed_uniform_draws'] += 2
        afterstates.append(after)
        board = list(after); board[cell] = rank; board = tuple(board)
        boards.append(board)
    assert list(boards[-1]) == row['final_board']
    assert list(afterstates[0]) == row['first_afterstate']
    assert list(boards[1]) == row['first_exit']
    result = row['result']
    assert sum(row['scores']) == result['score']
    assert result['steps'] == len(row['actions'])
    assert result['environment_counts']['environment_random_draws'] == 2*result['steps']
    assert result['environment_counts']['sampled_transitions'] == result['steps']
    assert result['environment_counts']['ground_explicit_swipe_calls'] == result['steps']
    assert result['environment_counts']['ground_state_status_calls'] == result['steps']+1
    assert result['forced_action_count'] == result['environment_counts']['forced_actions'] == 1
    assert result['continuation_decisions'] == result['environment_counts'].get('continuation_actions', 0) == result['steps']-1
    assert result['environment_counts'].get('initial_spawns', 0) == 0
    assert result['learning_counts'] == {}
    assert 0. <= result['decision_seconds'] <= result['seconds']
    return boards


def test_same_seed_pairs_uniforms_across_different_vacancy_sets():
    rows = [branch(SPARSE, action, ScriptedFrozenPlanner([continuation]), QUERY, 123, max_steps=2)
            for action, continuation in [('LEFT', 'DOWN'), ('DOWN', 'UP')]]
    for row in rows:
        replay(row)
    assert rows[0]['first_afterstate'].count(0) != rows[1]['first_afterstate'].count(0)
    assert rows[0]['spawned_ranks'] == rows[1]['spawned_ranks']
    assert rows[0]['spawned_cells'] != rows[1]['spawned_cells']


def test_forced_action_then_current_board_query_and_frozen_model():
    planner = ScriptedFrozenPlanner(['UP', 'DOWN'])
    weights, updates, counts = planner.weights.copy(), planner.updates, planner.counts.copy()
    root, query = list(SPARSE), dict(QUERY)
    row = branch(root, 'RIGHT', planner, query, 17, max_steps=3)
    boards = replay(row)
    assert row['actions'] == ['RIGHT', 'UP', 'DOWN']
    assert planner.calls == [(boards[1], query), (boards[2], query)]
    assert row['result']['policy_counts'] == dict(choose_calls=2, value_predictions=8)
    assert planner.counts == counts+Counter(choose_calls=2, value_predictions=8)
    assert np.array_equal(planner.weights, weights) and not planner.weights.flags.writeable
    assert planner.updates == updates and root == SPARSE and query == QUERY


def test_forced_goal_still_spawns_and_has_no_continuation():
    row = branch([10, 10]+[0]*14, 'LEFT', ScriptedFrozenPlanner(), QUERY, 4)
    replay(row)
    assert row['result']['status'] == 'WON'
    assert row['result']['components'] == [1., 0., 1.]
    assert row['result']['utility'] == 2.
    assert row['result']['steps'] == 1 and row['result']['policy_counts'] == {}
    assert row['first_exit'].count(0) == row['first_afterstate'].count(0)-1
    assert row['result']['environment_counts']['ground_status_internal_swipe_calls'] == 4


@pytest.mark.parametrize('penalty', [1., 8.])
def test_loss_is_terminal_and_uses_the_requested_query(penalty):
    query = dict(QUERY, failure_penalty=penalty)
    row = branch(LOSS_ROOT, 'LEFT', ScriptedFrozenPlanner(), query, 4)
    replay(row)
    assert row['result']['status'] == 'LOST'
    assert row['result']['components'] == [4/2048., 1., 0.]
    assert row['result']['utility'] == 4/2048.-penalty
    assert row['result']['steps'] == 1 and row['result']['policy_counts'] == {}
    assert row['result']['environment_counts']['ground_swipe_calls'] == 9


def test_continuation_goal_adds_terminal_bonus_once():
    row = branch([10, 0, 10, 0]+[0]*12, 'DOWN', ScriptedFrozenPlanner(['LEFT']), QUERY, 0)
    replay(row)
    assert row['result']['status'] == 'WON' and row['result']['steps'] == 2
    assert row['scores'] == [0, 2048]
    assert row['result']['components'] == [1., 0., 1.]
    assert row['result']['utility'] == 2.
    assert row['result']['policy_counts']['choose_calls'] == 1


def test_cutoff_keeps_partial_score_but_has_no_terminal_utility():
    row = branch(SPARSE, 'LEFT', ScriptedFrozenPlanner(), QUERY, 71, max_steps=1)
    replay(row)
    assert row['result']['status'] == 'CUTOFF'
    assert row['result']['utility'] is None
    assert row['result']['components'] == [4/2048., 0., 0.]
    assert row['result']['policy_counts'] == {}


@pytest.mark.parametrize('board,action,match', [
    ([1]+[0]*15, 'LEFT', 'illegal action LEFT at step 0'),
    (SPARSE, 'SIDEWAYS', 'is not a valid'),
    ([11]+[0]*15, 'RIGHT', 'root must be ACTIVE'),
])
def test_invalid_first_input_is_not_replaced(board, action, match):
    planner = ScriptedFrozenPlanner()
    with pytest.raises(ValueError, match=match):
        branch(board, action, planner, QUERY, 7)
    assert planner.calls == []
