"""Actual ground replay, full risk policy, and raw-budget continuity."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_policy_stream_v306 import NativePolicyStream
from acfqp.science.native_split_risk_v301 import QUERY, SplitLeaf
from acfqp.science.native_value_stream_v286 import NativeValueStream

BUILD = Path(__file__).resolve().parents[1]/'reports/policy_alignment_v306/runtime/tests/native'


def actors(risk=False):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9,10)), (2, Fraction(1,10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    template = QueryTD(QueryParent(source, QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    leaf = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    if risk:
        leaf.risk_weights[:] = np.random.default_rng(306001).normal(0., .4, leaf.risk_weights.shape)
    leaf.freeze()
    return template, leaf


def replay_policy(leaf, receipt, model_p):
    board = tuple(receipt['start']['board'])
    action_index = 0
    records = receipt['action_records']
    for spawn in receipt['raw_spawns']:
        if spawn['kind'] == 'INITIAL':
            if spawn['episode'] != receipt['start']['episode'] and (not action_index or
                    spawn['episode'] != records[action_index-1]['episode']):
                # Initial tiles reset only when the preceding board was terminal.
                if max(board)>=leaf.radix or not ground.legal_actions_v1(board):
                    board = (0,)*16
        else:
            chosen = leaf.choose(board, model_p)
            assert chosen['action'] == receipt['actions'][action_index]
            assert chosen['value'] == records[action_index]['h2_value']
            after, score, changed = ground.swipe_board_v1(board,
                ground.Swipe2048Action(chosen['action']))
            assert changed and score == receipt['scores'][action_index]
            board = after
            action_index += 1
        assert board[spawn['cell']] == 0
        board = list(board)
        board[spawn['cell']] = spawn['rank']
        board = tuple(board)
    assert action_index == len(receipt['actions'])
    assert list(board) == receipt['end']['board']


def test_zero_risk_actor_exactly_matches_source_h2_physical_stream():
    template, leaf = actors()
    split = NativePolicyStream(leaf, 306001, BUILD)
    source = NativeValueStream(template, 306001, BUILD)
    try:
        actual = split.advance(.37, .1, 256)
        expected = source.advance(template, 0, template, .37, .1, 256, max_postaction=256)
        for key in ('start', 'end', 'raw_spawns', 'actions', 'scores', 'completed_games', 'counts'):
            assert actual[key] == expected[key]
        assert [r['h2_value'] for r in actual['action_records']] == [
            r['h2_value'] for r in expected['action_records']]
        assert actual['updates'] == [] and template.updates == leaf.updates == 0
        assert actual['representation_counts']['risk_sigmoid_evaluations'] > 0
        assert actual['completed_games'] and all(g['status'] in ('WON', 'LOST') for g in actual['completed_games'])
        assert actual['end']['raw_tiles'] == 256
        assert actual['end']['random_draw_position'] == 512
    finally:
        source.close()
        split.close()


def test_current_risk_changes_actions_and_every_actual_choice_matches_full_split_policy():
    _, learned = actors(True)
    _, original = actors()
    current = NativePolicyStream(learned, 306002, BUILD)
    baseline = NativePolicyStream(original, 306002, BUILD)
    reward_before, risk_before = learned.reward_weights.copy(), learned.risk_weights.copy()
    try:
        actual = current.advance(.1, .1, 128)
        source = baseline.advance(.1, .1, 128)
        assert actual['actions'] != source['actions']
        replay_policy(learned, actual, .1)
        np.testing.assert_array_equal(learned.reward_weights, reward_before)
        np.testing.assert_array_equal(learned.risk_weights, risk_before)
        assert learned.updates == 0 and actual['counts']['learning'] == {}
        assert not learned.reward_weights.flags.writeable and not learned.risk_weights.flags.writeable
    finally:
        current.close()
        baseline.close()


@pytest.mark.parametrize('risk', [False, True])
def test_partial_initialization_and_chunks_preserve_exact_raw_stream(risk):
    _, leaf = actors(risk)
    whole, chunked = NativePolicyStream(leaf, 306003, BUILD), NativePolicyStream(leaf, 306003, BUILD)
    try:
        actual = whole.advance(.1, .1, 202)
        chunks = [chunked.advance(.1, .1, n) for n in (1, 1, 3, 5, 64, 128)]
        assert chunks[0]['end']['status'] == 'INITIALIZING'
        assert chunks[0]['end']['initial_count'] == 1 and chunks[0]['actions'] == []
        assert chunks[1]['end']['status'] == 'ACTIVE' and chunks[1]['actions'] == []
        for key in ('raw_spawns', 'actions', 'scores', 'completed_games'):
            assert actual[key] == [r for chunk in chunks for r in chunk[key]]
        assert whole.state() == chunked.state()
        assert whole.counts == chunked.counts
        assert whole.representation_counts == chunked.representation_counts
        assert whole.counts['environment']['raw_tile_productions'] == 202
        assert whole.counts['environment']['environment_random_draws'] == 404
        assert whole.counts['environment']['initial_spawns']+whole.counts['environment']['post_action_spawns'] == 202
        draws = whole.common_draws(306003, 202)
        assert [r['rank'] for r in actual['raw_spawns']] == [1 if x<.9 else 2 for x in draws[:,1]]
        assert whole.counts['learning'] == {}
    finally:
        whole.close()
        chunked.close()


def test_cutoff_remains_an_explicit_unfitted_completed_game():
    _, leaf = actors(True)
    stream = NativePolicyStream(leaf, 306004, BUILD, max_steps=1)
    try:
        actual = stream.advance(.1, .1, 3)
        assert actual['end']['status'] == 'CUTOFF'
        assert actual['end']['pending_afterstate'] is None and actual['end']['pending_bank_id'] is None
        assert actual['completed_games'][0]['status'] == 'CUTOFF'
        assert actual['counts']['environment']['cutoff_games'] == 1
        assert actual['counts']['learning'] == {} and actual['updates'] == []
    finally:
        stream.close()


def test_collector_requires_both_actor_heads_frozen():
    _, leaf = actors()
    leaf.risk_weights.flags.writeable = True
    with pytest.raises(ValueError, match='both actor heads frozen'):
        NativePolicyStream(leaf, 306005, BUILD)
