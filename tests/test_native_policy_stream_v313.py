"""Actual head callbacks, immutable batches, DIRECT values and physical execution."""
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_ntuple_td_v120 import ACTIONS, NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_linear_win_v311 import LinearWinLeaf, fit_linear, predict_components as linear_predict
from acfqp.science.native_policy_stream_v313 import NativePolicyStream, choose_direct, evaluate_direct
from acfqp.science.native_split_risk_v301 import SplitLeaf, fit_split, predict_components as local_predict
from acfqp.science.native_value_stream_v286 import NativeValueStream

BUILD = Path(__file__).resolve().parents[1] / 'reports/closed_loop_v313/runtime/tests/native'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def actor(kind, fitted=False):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 7 * .002
    template = QueryTD(QueryParent(source, QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    leaf = SplitLeaf(template, 'LOCAL_RISK', BUILD) if kind == 'LOCAL' else LinearWinLeaf(template, BUILD)
    if fitted:
        boards = [[1, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [2, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [3, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [4, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [1, 2, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [2, 2, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
        data = dict(afterstates=np.asarray(boards, dtype=np.int32),
            rewards=np.asarray([.1, .2, .3, .4, .5, .6]), ends=np.asarray([2, 4, 6], dtype=np.int64),
            terminal_codes=np.asarray([-1, 1, -1], dtype=np.int32), fit_game_count=2, fit_step_end=4)
        fitted_receipt = (fit_split if kind == 'LOCAL' else fit_linear)(leaf, data, BUILD)
        assert fitted_receipt['trained_afterstates'] == leaf.updates == 3
    leaf.freeze()
    return template, leaf


def second(leaf):
    return leaf.risk_weights if leaf.kind == 'LOCAL_RISK' else leaf.win_weights


def literal_direct(leaf, board):
    if max(board) >= leaf.radix:
        return None, {}, 4.
    values = {}
    predict = local_predict if leaf.kind == 'LOCAL_RISK' else linear_predict
    for action in ACTIONS:
        after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
        if changed:
            tail = 4. if max(after) >= leaf.radix else predict(leaf, after)['combined_prediction']
            values[action] = score / 2048. + tail
    chosen = max(values, key=values.get) if values else None
    return chosen, values, values[chosen] if chosen else -4.


@pytest.mark.parametrize('kind', ['LOCAL', 'LINEAR'])
def test_neutral_head_collector_matches_source_h2(kind):
    template, leaf = actor(kind)
    collector, baseline = NativePolicyStream(leaf, 313001, BUILD), NativeValueStream(template, 313001, BUILD)
    try:
        actual = collector.advance(.375, .1, 64)
        expected = baseline.advance(template, 0, template, .375, .1, 64, max_postaction=64)
        for key in ('start', 'end', 'raw_spawns', 'actions', 'scores', 'completed_games', 'counts'):
            assert actual[key] == expected[key]
        assert [r['h2_value'] for r in actual['action_records']] == [r['h2_value'] for r in expected['action_records']]
    finally:
        collector.close()
        baseline.close()


@pytest.mark.parametrize('kind', ['LOCAL', 'LINEAR'])
def test_fitted_actual_head_actions_values_and_chunks_remain_frozen(kind):
    _, leaf = actor(kind, fitted=True)
    original = [leaf.reward_weights.copy(), second(leaf).copy()]
    whole, chunked = NativePolicyStream(leaf, 313002, BUILD), NativePolicyStream(leaf, 313002, BUILD)
    try:
        receipt = whole.advance(.375, .5, 63)
        chunks = [chunked.advance(.375, .5, size) for size in (1, 1, 3, 5, 17, 36)]
        assert chunks[0]['end']['status'] == 'INITIALIZING' and chunks[0]['actions'] == []
        for key in ('raw_spawns', 'actions', 'scores', 'completed_games'):
            assert receipt[key] == [item for chunk in chunks for item in chunk[key]]
        assert whole.state() == chunked.state()
        assert whole.counts == chunked.counts and whole.representation_counts == chunked.representation_counts
        planning, representation = Counter(), Counter()
        board, episode, index = tuple(receipt['start']['board']), receipt['start']['episode'], 0
        for spawn in receipt['raw_spawns']:
            if spawn['episode'] != episode:
                episode, board = spawn['episode'], (0,) * 16
            if spawn['kind'] == 'POST_ACTION':
                record = receipt['action_records'][index]
                assert record['preboard'] == list(board)
                chosen = leaf.choose(board, .375)
                assert chosen['action'] == receipt['actions'][index]
                assert chosen['value'] == record['h2_value']
                assert {a:r['value'] for a,r in chosen['action_values'].items()} == record['action_values']
                planning.update(chosen['counts'])
                representation.update(chosen['representation_counts'])
                board, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(chosen['action']))
                assert changed and score == receipt['scores'][index]
                index += 1
            assert board[spawn['cell']] == 0
            board = list(board)
            board[spawn['cell']] = spawn['rank']
            board = tuple(board)
        assert list(board) == receipt['end']['board']
        assert dict(planning) == receipt['counts']['planning']
        assert dict(representation) == receipt['representation_counts']
        assert receipt['end']['random_draw_position'] == 126
        assert receipt['counts']['environment']['raw_tile_productions'] == 63
        assert receipt['counts']['learning'] == {} and receipt['updates'] == []
        assert leaf.updates == 3
        for current, saved in zip((leaf.reward_weights, second(leaf)), original):
            np.testing.assert_array_equal(current, saved)
            assert not current.flags.writeable
    finally:
        whole.close()
        chunked.close()


@pytest.mark.parametrize('kind', ['LOCAL', 'LINEAR'])
def test_direct_native_values_order_and_terminal_bypasses_match_literal(kind):
    _, leaf = actor(kind, fitted=True)
    boards = [(1, 2, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (3, 3, 0, 0) + (0,) * 12,
        (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1),
        (4,) + (0,) * 15]
    for board in boards:
        expected, values, maximum = literal_direct(leaf, board)
        actual = choose_direct(leaf, board, BUILD)
        assert actual['action'] == expected and actual['value'] == maximum
        assert {a:r['value'] for a,r in actual['action_values'].items()} == values
        assert not actual['counts'].get('generated_spawn_outcomes', 0)
        assert not actual['counts'].get('second_ply_swipe_calls', 0)
        if max(board) >= leaf.radix:
            assert actual['representation_counts'] == {} and actual['status'] == 'WON'
        if not values and max(board) < leaf.radix:
            assert actual['status'] == 'LOST' and actual['representation_counts'] == {}


@pytest.mark.parametrize('kind', ['LOCAL', 'LINEAR'])
def test_direct_full_native_games_replay_same_rng_and_actual_head(kind):
    _, leaf = actor(kind, fitted=True)
    stream = NativePolicyStream(leaf, 313003, BUILD)
    before = [leaf.reward_weights.copy(), second(leaf).copy()]
    try:
        seeds = [313004, 313005]
        result = evaluate_direct(leaf, .375, .5, seeds, BUILD, max_steps=512)
        for seed, actual in zip(seeds, result['game_summaries']):
            draws = stream.common_draws(seed, 514)
            board, score, raw, steps = (0,) * 16, 0, 0, 0
            def spawn(board):
                nonlocal raw
                empty = [i for i, value in enumerate(board) if not value]
                board = list(board)
                board[empty[int(draws[raw, 0] * len(empty))]] = 1 if draws[raw, 1] < .5 else 2
                raw += 1
                return tuple(board)
            board = spawn(spawn(board))
            while max(board) < 4 and ground.legal_actions_v1(board) and steps < 512:
                chosen, _, _ = literal_direct(leaf, board)
                after, gained, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(chosen))
                assert changed
                board, score, steps = spawn(after), score + gained, steps + 1
            status = 'WON' if max(board) >= 4 else 'LOST' if not ground.legal_actions_v1(board) else 'CUTOFF'
            assert actual == dict(seed=seed, score=score, steps=steps, status=status,
                final_board=list(board), utility=score / 2048. + (4. if status == 'WON' else -4. if status == 'LOST' else 0.))
        counts = result['counts']
        steps = sum(g['steps'] for g in result['game_summaries'])
        assert counts['environment']['raw_tile_productions'] == steps + 4
        assert counts['environment']['environment_random_draws'] == 2 * (steps + 4)
        assert counts['planning']['choose_calls'] == steps
        assert not counts['planning'].get('generated_spawn_outcomes', 0)
        assert leaf.updates == 3
        for current, saved in zip((leaf.reward_weights, second(leaf)), before):
            np.testing.assert_array_equal(current, saved)
    finally:
        stream.close()


def test_actor_unfreeze_between_chunks_is_rejected():
    _, leaf = actor('LINEAR', fitted=True)
    stream = NativePolicyStream(leaf, 313006, BUILD)
    try:
        stream.advance(.375, .1, 2)
        leaf.win_weights.flags.writeable = True
        with pytest.raises(ValueError, match='both actor heads frozen'):
            stream.advance(.375, .1, 2)
    finally:
        stream.close()
