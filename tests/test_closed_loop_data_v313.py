"""Actual complete-game batches, paid tails, version receipts and action probes."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import closed_loop_data_v313 as data
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_linear_win_v311 import LinearWinLeaf
from acfqp.science.native_policy_stream_v313 import NativePolicyStream
from acfqp.science.native_split_risk_v301 import SplitLeaf

BUILD = Path(__file__).resolve().parents[1] / 'reports/closed_loop_v313/runtime/tests/data'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def actor(kind):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 11)
    template = QueryTD(QueryParent(NtupleValue(rule, BUILD), QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    leaf = SplitLeaf(template, 'LOCAL_RISK', BUILD) if kind == 'LOCAL' else LinearWinLeaf(template, BUILD)
    leaf.freeze()
    return leaf


@pytest.mark.parametrize('kind', ['LOCAL', 'LINEAR'])
def test_actual_batch_complete_suffixes_paid_tail_and_probes(kind):
    leaf, rows = actor(kind), []
    version = dict(bank_id=0, round=1, fitted_batches=[], updates=0)
    result = data.acquire_policy_data(leaf, 0, 0, f'CLOSED_{kind}', .375, .1,
        313200000000, 'A_R1', rows.append, BUILD, raw_budget=4096,
        actor_version=version, task='A')
    dataset, acquired = result['dataset'], result['acquisition']
    games = dataset['games']
    assert len(games) >= 2 and dataset['fit_game_count'] == 4 * len(games) // 5
    assert all(g['status'] in ('WON', 'LOST') for g in games)
    assert len(dataset['afterstates']) == sum(g['steps'] for g in games)
    assert dataset['fit_step_end'] == sum(g['steps'] for g in games[:dataset['fit_game_count']])
    assert [int(code) for code in dataset['terminal_codes']] == [1 if g['status'] == 'WON' else -1 for g in games]
    costs = dataset['costs']
    assert costs['fit_raw_tiles'] + costs['heldout_raw_tiles'] + costs['excluded_tail_raw_tiles'] == 4096
    assert costs['full_batch_raw_tiles'] == 4096 and 'full_A_raw_tiles' not in costs
    assert costs['full_batch_acquisition_counts'] == acquired['training']['counts']
    assert acquired['training']['after_stream']['random_draw_position'] == 8192
    train = [row for row in rows if row['kind'] == 'TRAIN']
    assert sum(len(row['raw_spawns']) for row in train) == 4096
    assert all(row['task'] == 'A' and row['batch_id'] == 'A_R1' and row['actor_version'] == version for row in rows)
    assert all(len(row['action_records']) == len(row['actions']) for row in train)
    assert all(not row['counts']['learning'] and not row['td_examples'] for row in train)
    assert acquired['actor_head_updates_before'] == acquired['actor_head_updates_after'] == leaf.updates == 0
    assert acquired['collector_policy_kind'] == leaf.kind and acquired['actor_version'] == version
    probes = acquired['policy_probes']
    assert len(probes['first']) == len(probes['last']) == 8
    assert probes['first'][0]['raw_index'] == 2
    assert probes['last'][-1]['raw_index'] < 4096
    for probe in probes['first'] + probes['last']:
        chosen = leaf.choose(probe['preboard'], .375)
        assert chosen['action'] == probe['chosen_action'] and chosen['value'] == probe['h2_value']
        assert {a:r['value'] for a,r in chosen['action_values'].items()} == probe['action_values']
    assert rows[-1]['policy_probes'] == probes
    assert dataset['fit_memory']['observations_seen'] == dataset['fit_end_raw']
    assert dataset['actor_memory_A_end']['observations_seen'] == 4096
    assert not leaf.reward_weights.flags.writeable
    assert not (leaf.risk_weights if kind == 'LOCAL' else leaf.win_weights).flags.writeable
    assert acquired['cpu_seconds'] >= acquired['native_setup_cpu_seconds'] > 0


def test_cutoff_row_is_saved_and_no_factual_label_is_returned(monkeypatch):
    leaf, rows = actor('LINEAR'), []
    class OneStepStream(NativePolicyStream):
        def __init__(self, *args, **kwargs):
            kwargs['max_steps'] = 1
            super().__init__(*args, **kwargs)
    monkeypatch.setattr(data, 'NativePolicyStream', OneStepStream)
    with pytest.raises(ValueError, match='cutoffs'):
        data.acquire_policy_data(leaf, 0, 0, 'CLOSED_LINEAR', .375, .1,
            313200000001, 'A_R2', rows.append, BUILD, raw_budget=256,
            actor_version=dict(bank_id=0, round=2, updates=0), task='A')
    assert rows and rows[0]['kind'] == 'TRAIN'
    assert any(g['status'] == 'CUTOFF' for g in rows[0]['completed_games'])
    assert rows[0]['counts']['learning'] == {} and leaf.updates == 0
    assert np.all(leaf.win_weights == 1. / 64.)
