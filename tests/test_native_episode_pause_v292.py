"""Real terminal pauses and DIRECT execution, before the V292 campaign."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_value_stream_v286 import NativeValueStream

BUILD = Path(__file__).resolve().parents[1]/'reports/natural_episode_v292/native_tests'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def leaf(goal=4):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', goal)
    value = NtupleValue(rule, BUILD)
    result = QueryTD(QueryParent(value, QUERY, QUERY, .5), 'PRIOR', BUILD)
    result.freeze()
    return result


@pytest.mark.parametrize('depth', [1, 2])
def test_terminal_pause_excludes_next_game_initialization_and_choice(depth):
    frozen = leaf()
    paused = NativeValueStream(frozen, 29200011, BUILD)
    whole = NativeValueStream(frozen, 29200011, BUILD)
    try:
        first = paused.advance(frozen, 0, frozen, .1, 1., 64, depth=depth, stop_on_game_end=True)
        all_games = whole.advance(frozen, 0, frozen, .1, 1., 64, depth=depth)
        assert len(first['completed_games']) == 1
        game = first['completed_games'][0]
        assert game['status'] == 'WON' and first['end']['raw_tiles'] == game['end_raw'] < 64
        assert first['raw_spawns'] == all_games['raw_spawns'][:game['end_raw']]
        assert first['actions'] == all_games['actions'][:game['steps']]
        assert first['counts']['environment']['episodes_started'] == 1
        assert first['counts']['planning']['choose_calls'] == game['steps']
        assert first['updates'] == [] and not first['counts']['learning']
        follow = paused.advance(frozen, 0, None, .1, 1., 2, depth=depth, stop_on_game_end=True)
        assert follow['actions'] == [] and follow['end']['episode'] == game['episode']+1
        assert first['end'] == follow['start'] and follow['end']['raw_tiles'] == game['end_raw']+2
        assert frozen.updates == 0
    finally:
        paused.close(); whole.close()


def test_direct_training_matches_literal_query_policy_and_actual_ground_feedback():
    frozen = leaf(goal=11)
    stream = NativeValueStream(frozen, 29200012, BUILD)
    try:
        actual = stream.advance(frozen, 0, None, .37, .5, 18, depth=1, stop_on_game_end=True)
        board, actions, scores, spawns = [0]*16, [], [], []
        for index, (cell_draw, rank_draw) in enumerate(stream.common_draws(29200012, 18)):
            if index >= 2:
                action = frozen.choose(board)['action']
                after, gained, changed = ground.swipe_board_v1(tuple(board), ground.Swipe2048Action(action))
                assert changed
                actions.append(action); scores.append(gained)
            else:
                after = board
            empty = [cell for cell, value in enumerate(after) if not value]
            cell = empty[int(cell_draw*len(empty))]
            rank = 1 if rank_draw < .5 else 2
            board = list(after); board[cell] = rank
            spawns.append(dict(episode=0, kind='INITIAL' if index < 2 else 'POST_ACTION', cell=cell, rank=rank))
        assert actual['raw_spawns'] == spawns
        assert actual['actions'] == actions and actual['scores'] == scores
        assert actual['end']['board'] == board and actual['updates'] == []
        assert not actual['counts']['learning'] and frozen.updates == 0
        assert actual['counts']['planning'].get('generated_spawn_outcomes', 0) == 0
    finally:
        stream.close()
