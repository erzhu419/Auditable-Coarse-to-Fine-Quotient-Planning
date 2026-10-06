"""Finite checks for paired curves and TD target/accounting interpretation."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_online_query_td_v131 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_online_query_td_v131.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before,
        environment_samples=0, model_samples=0, model_updates=0,
        scope='synthetic frozen curve, transition-budget, pause and TD-target fixtures'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def full_curve_rows():
    indexed = {}
    for life in analysis.LIVES:
        for query in analysis.QUERIES:
            for method in analysis.METHODS:
                for checkpoint in analysis.CHECKPOINTS:
                    for replica in range(analysis.REPLICAS):
                        improvement = (life+1)*(analysis.CHECKPOINTS.index(checkpoint)-1)
                        value = 3*life+replica+int(method == 'PRIOR')*improvement
                        indexed[(life, query, method, checkpoint, replica)] = dict(
                            result=dict(status='LOST', utility=value, score=4, steps=1))
    return indexed


def test_full_curve_keeps_each_age_and_final_primary_with_equal_life_pairs():
    rows = full_curve_rows(); valid = {k: True for k in rows}
    result = analysis.full_game_curve(rows, valid)
    assert result['complete']
    assert [r['checkpoint'] for r in result['curve']] == list(analysis.CHECKPOINTS)
    assert result['primary_checkpoint'] == 524288
    values = [r['comparisons']['PRIOR_minus_PARENT']['risk1']['mean'] for r in result['curve']]
    assert values == [-2.5, 0., 2.5, 5.]
    assert result['primary']['comparisons']['PRIOR_minus_PARENT']['risk1']['positive'] == 4
    assert result['primary']['comparisons']['PRIOR_minus_PARENT']['risk1']['lifecycles'][2]['replica_deltas'] == [6]*16


def test_missing_or_cutoff_returns_do_not_silently_reweight_histories():
    rows = full_curve_rows(); valid = {k: True for k in rows}
    rows[(0, 'risk1', 'PRIOR', 524288, 0)]['result']['status'] = 'CUTOFF'
    del rows[(3, 'risk8', 'SCRATCH', 32768, 0)]
    result = analysis.full_game_curve(rows, valid)
    assert not result['complete']
    assert result['primary']['comparisons']['PRIOR_minus_PARENT']['risk1']['mean'] is None
    assert result['primary']['comparisons']['PRIOR_minus_PARENT']['risk8']['mean'] == 5
    assert result['curve'][1]['comparisons']['PRIOR_minus_SCRATCH']['risk8']['mean'] is None


def test_declared_parent_offsets_exclude_inherited_values_from_scratch():
    source = dict(counts=dict(reward=dict(constant=.25), risk_goal=dict(constant=.75)))
    assert analysis.expected_offset(source, 'risk1', 'PRIOR') == -.5
    assert analysis.expected_offset(source, 'risk8', 'PRIOR') == 2.
    assert analysis.expected_offset(source, 'risk8', 'SCRATCH') == 0.


def segment_fixture(previous=None):
    first = previous is None; updates = 0 if first else 1
    initial = [1, 1]+[0]*14
    end = [2, 1]+[0]*14 if first else [1]+[0]*11+[2, 1, 0, 0]
    cell = 1 if first else 0; after = list(end); after[cell] = 0
    source = dict(counts=dict(reward=dict(constant=.25)))
    row = dict(episode=0, seed=analysis.training_seed(0, 'risk1', 0),
        start_step=0 if first else 1, end_step=1 if first else 2,
        start_board=initial if first else previous['end_board'], end_board=end,
        actions=['LEFT' if first else 'DOWN'], scores=[4 if first else 0],
        spawned_cells=[cell], spawned_ranks=[1], chosen_values=[1.5], chosen_raw_values=[2.],
        td_targets=[None if first else 1.5], raw_td_targets=[None if first else 2.],
        td_errors=[None if first else .5], terminal_update=None,
        pending_before=None if first else previous['pending_after'], pending_after=after,
        updates_before=0, updates_after=updates, cumulative_updates=updates,
        cumulative_transitions=1 if first else 2, status='ACTIVE', budget_status='BUDGET_END',
        censored_last_update=False, return_score=4, seconds=.01,
        environment_counts=dict(sampled_transitions=1, initial_spawns=2*first,
            environment_random_draws=2+4*first, ground_explicit_swipe_calls=1,
            ground_state_status_calls=1+first, ground_status_internal_swipe_calls=4*(1+first)),
        model_counts=dict(choose_calls=1, inner_choose_calls=1, td_updates=updates,
            inner_td_updates=updates, inner_table_update_occurrences=32*updates,
            inner_table_updates=8*updates))
    if first: row['initial_spawns'] = [dict(cell=0, rank=1), dict(cell=1, rank=1)]
    return row, source


def test_active_budget_boundary_preserves_pending_and_updates_on_resume():
    first, source = segment_fixture(); second, _ = segment_fixture(first)
    assert all(analysis.segment_checks(first, None, 'risk1', 'PRIOR', source).values())
    assert all(analysis.segment_checks(second, first, 'risk1', 'PRIOR', source).values())
    broken = deepcopy(second); broken['pending_before'] = None
    assert not analysis.segment_checks(broken, first, 'risk1', 'PRIOR', source)['segment_continuity']
    broken = deepcopy(second); broken['raw_td_targets'][0] = 2.5
    assert not analysis.segment_checks(broken, first, 'risk1', 'PRIOR', source)['td_targets']


def test_real_loss_has_last_td_target_but_budget_pause_is_not_loss():
    row, source = segment_fixture()
    row.update(status='LOST', budget_status='EPISODE_END', pending_after=None,
        updates_after=1, cumulative_updates=1,
        end_board=[1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1],
        spawned_cells=[0])
    after = list(row['end_board']); after[0] = 0
    row['terminal_update'] = dict(target=-1., raw_target=-.5, error=-2.,
        afterstate=after, work=dict(td_updates=1))
    row['model_counts'].update(td_updates=1, inner_td_updates=1,
        inner_table_update_occurrences=32, inner_table_updates=8)
    assert all(analysis.segment_checks(row, None, 'risk1', 'PRIOR', source).values())
    broken = deepcopy(row); broken['terminal_update']['raw_target'] = -1.
    assert not analysis.segment_checks(broken, None, 'risk1', 'PRIOR', source)['td_targets']
    broken = deepcopy(row); broken['status'] = 'ACTIVE'; broken['budget_status'] = 'BUDGET_END'
    assert not analysis.segment_checks(broken, None, 'risk1', 'PRIOR', source)['td_targets']
