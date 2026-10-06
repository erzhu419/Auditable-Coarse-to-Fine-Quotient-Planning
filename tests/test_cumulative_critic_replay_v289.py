"""Finite replay identity and factual-anchor tests; no new environment data."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.cumulative_critic_replay_v289 import assemble_anchor_panel, replay_cumulative
from acfqp.science.native_retained_critic_v287 import fit_retained
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1] / 'reports/cumulative_critic_replay_v289/runtime/tests'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def make_leaf(offset=False):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    source_query = dict(reward_weight=1., failure_penalty=0., goal_bonus=0.) if offset else QUERY
    return QueryTD(QueryParent(source, source_query, QUERY, .25 if offset else .5), 'PRIOR', BUILD)


def dataset():
    return dict(afterstates=np.asarray([[2]+[0]*15, [2,1]+[0]*14, [1,2,1,2]*3+[2,1,2,0],
        [3,3]+[0]*14, [4]+[0]*15, [1,1]+[0]*14, [2,1]+[0]*14,
        [3,3]+[0]*14, [4]+[0]*15], dtype=np.int32),
        rewards=np.asarray([4,8,0,8,16,0,4,8,16], dtype=np.float64)/2048.,
        ends=np.asarray([3,5,7,9], dtype=np.int64),
        terminal_codes=np.asarray([-1,1,-1,1], dtype=np.int32),
        fit_game_count=3, fit_step_end=7)


@pytest.mark.parametrize('offset', [False, True])
def test_per_game_replay_is_bitwise_identical_to_whole_original_mc_fit(offset):
    actual, reference = make_leaf(offset), make_leaf(offset)
    data = dataset(); anchors = np.asarray([0,3,5,7], dtype=np.int64)
    original = fit_retained(reference, data, 'MC', BUILD)
    replay = replay_cumulative(actual, data, anchors, BUILD)
    np.testing.assert_array_equal(actual.weights, reference.weights)
    assert actual.updates == reference.updates == 6
    assert replay['learning_counts'] == original['learning_counts']
    assert replay['first_update'] == original['first_update']
    assert replay['last_update'] == original['last_update']
    for key in set(original['target_counts']) | set(replay['target_counts']):
        if key != 'target_buffer_doubles_peak':
            assert replay['target_counts'].get(key,0) == original['target_counts'].get(key,0)
    assert replay['target_counts']['target_buffer_doubles_peak'] == 3
    assert [s['completed_fit_games'] for s in replay['snapshots']] == [0,1,2,3]
    assert [s['cumulative_fit_steps'] for s in replay['snapshots']] == [0,3,5,7]
    assert [s['cumulative_updates'] for s in replay['snapshots']] == [0,3,4,6]
    expected = [reference.model.value(data['afterstates'][i])
                + reference.failure_shift + reference.success_shift for i in anchors]
    assert replay['snapshots'][-1]['predictions'] == expected
    assert replay['anchor_scoring_counts'] == dict(snapshots=4, value_predictions=16,
        table_lookups=512, prediction_shift_additions=32)
    assert actual.model.counts['value_predictions'] == 6+16
    assert actual.counts['inner_value_predictions'] == 6+16
    assert actual.counts['td_updates'] == 6
    assert replay['callback_calls'] == 0


def test_readonly_callback_does_not_change_update_history_or_anchor_values():
    actual, reference = make_leaf(True), make_leaf(True)
    data = dataset(); anchors = [0,3,7]
    seen = []
    def callback(completed, leaf):
        leaf.freeze()
        seen.append((completed, leaf.updates, leaf.choose(data['afterstates'][7])['value']))
        leaf.weights.flags.writeable = True
    result = replay_cumulative(actual, data, anchors, BUILD, callback)
    plain = replay_cumulative(reference, data, anchors, BUILD)
    np.testing.assert_array_equal(actual.weights, reference.weights)
    assert result['snapshots'] == plain['snapshots']
    assert result['learning_counts'] == plain['learning_counts']
    assert result['first_update'] == plain['first_update'] and result['last_update'] == plain['last_update']
    assert [(game,updates) for game,updates,_ in seen] == [(0,0),(1,3),(2,4),(3,6)]
    assert result['callback_calls'] == 4 and actual.weights.flags.writeable


def test_anchors_have_exact_native_order_suffixes_excluding_current_reward():
    data = dataset()
    data['rewards'] = np.asarray([.1,.2,.3,.4,.5,.6,.7,.8,.9], dtype=np.float64)
    result = assemble_anchor_panel(data, [3,0,7,2])
    rows = result['rows']
    assert [(r['episode'],r['step']) for r in rows] == [(1,3),(0,0),(3,7),(0,2)]
    suffix = -4.
    expected = {}
    for step in range(2,-1,-1):
        expected[step] = suffix
        suffix += float(data['rewards'][step])
    assert rows[0]['target'] == 4.+.5
    assert rows[1]['target'] == expected[0]
    assert rows[2]['target'] == 4.+.9
    assert rows[3]['target'] == -4.
    assert rows[0]['afterstate'] == data['afterstates'][3].tolist()
    assert result['counts'] == dict(suffix_games=3,suffix_target_assignments=7,
        suffix_reward_additions=7,target_buffer_doubles_peak=3,selected_anchors=4)
    with pytest.raises(ValueError, match='winning afterstates'):
        assemble_anchor_panel(data, [4])
