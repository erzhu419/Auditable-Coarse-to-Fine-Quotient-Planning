"""Real fixed-actor boards are retained once, in order, including the paid tail."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import greedy_target_data_v317 as data
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_policy_stream_v313 import NativePolicyStream
from acfqp.science.native_split_risk_v301 import SplitLeaf

BUILD = Path(__file__).resolve().parents[1] / 'reports/greedy_targets_v317/runtime/tests/data'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def actor():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 11)
    template = QueryTD(QueryParent(NtupleValue(rule, BUILD), QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    leaf = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    leaf.freeze()
    return leaf


def test_actual_postspawn_complete_prefix_and_paid_tail_use_one_existing_replay(monkeypatch):
    leaf, rows, swipes = actor(), [], []
    original = data._swipe
    def counted_swipe(*args):
        swipes.append(1)
        return original(*args)
    monkeypatch.setattr(data, '_swipe', counted_swipe)
    version = dict(file='FIRST_LOCAL_v0.npz', version=0, updates=0)
    result = data.acquire_policy_data(leaf, 0, 0, 'FIXED_FIRST', .375, .1,
        317500100000, 'A_R1', rows.append, BUILD, raw_budget=4096, actor_version=version, task='A')
    dataset, acquisition = result['dataset'], result['acquisition']
    train = [row for row in rows if row['kind'] == 'TRAIN']
    postspawns = [spawn for row in train for spawn in row['raw_spawns'] if spawn['kind'] == 'POST_ACTION']
    complete = len(dataset['afterstates'])
    assert dataset['postspawn_boards'].shape == dataset['afterstates'].shape == (complete, 16)
    assert dataset['postspawn_boards'].dtype == np.int32
    for after, observed, spawn in zip(dataset['afterstates'], dataset['postspawn_boards'], postspawns):
        expected = after.copy()
        assert expected[spawn['cell']] == 0
        expected[spawn['cell']] = spawn['rank']
        np.testing.assert_array_equal(observed, expected)
    assert len(swipes) == len(postspawns)
    assert len(postspawns) - complete == dataset['costs']['excluded_tail_steps']
    processing = acquisition['reconstruction']['counts']
    assert processing['observed_postspawn_boards'] == len(postspawns)
    assert processing['observed_postspawn_cells'] == 16 * len(postspawns)
    assert dataset['costs']['postspawn_board_array_bytes'] == dataset['postspawn_boards'].nbytes == 64 * complete
    assert dataset['costs']['fit_raw_tiles'] + dataset['costs']['heldout_raw_tiles'] + dataset['costs']['excluded_tail_raw_tiles'] == 4096
    assert complete == sum(game['steps'] for game in dataset['games'])
    assert all(row['actor_version'] == version and row['stream_seed'] == 317500100000 for row in rows)
    assert leaf.updates == acquisition['actor_head_updates_before'] == acquisition['actor_head_updates_after'] == 0
    assert not leaf.reward_weights.flags.writeable and not leaf.risk_weights.flags.writeable


def test_cutoff_is_retained_before_rejecting_false_terminal_training_labels(monkeypatch):
    leaf, rows = actor(), []
    class OneStepStream(NativePolicyStream):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, max_steps=1, **{key:value for key,value in kwargs.items() if key != 'max_steps'})
    monkeypatch.setattr(data, 'NativePolicyStream', OneStepStream)
    with pytest.raises(ValueError, match='cutoffs'):
        data.acquire_policy_data(leaf, 0, 0, 'FIXED_FIRST', .375, .1,
            317500100001, 'A_R2', rows.append, BUILD, raw_budget=256,
            actor_version=dict(version=0, updates=0), task='A')
    assert any(game['status'] == 'CUTOFF' for game in rows[0]['completed_games'])
    assert rows[0]['counts']['learning'] == {} and leaf.updates == 0
