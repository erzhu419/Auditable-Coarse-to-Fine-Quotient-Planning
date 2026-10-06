"""Finite independent target, queue and paired-return audit checks."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_multistep_query_td_v133 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_multistep_query_td_v133.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before,
        environment_samples=0, model_samples=0, model_updates=0,
        scope='independent hand-computed multi-step targets, retained queue protocol and complete paired curves'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def curve_rows():
    indexed = {}
    for life in analysis.LIVES:
        for query in analysis.QUERIES:
            for method in analysis.METHODS:
                for age in analysis.CHECKPOINTS:
                    for replica in range(analysis.REPLICAS):
                        delta = (life+1)*(analysis.CHECKPOINTS.index(age)-1)
                        utility = life+replica+int(method == 'MULTI')*delta
                        indexed[(life, query, method, age, replica)] = dict(
                            result=dict(status='LOST', utility=utility, score=4, steps=1))
    return indexed


def test_all_ages_are_retained_and_final_pairing_weights_all_lives_equally():
    rows = curve_rows(); result = analysis.full_game_curve(rows, {k: True for k in rows})
    assert result['complete'] and result['primary_checkpoint'] == 524288
    assert [r['comparisons']['MULTI_minus_SINGLE']['risk1']['mean'] for r in result['curve']] == [-2.5, 0, 2.5, 5]
    assert result['primary']['comparisons']['MULTI_minus_PARENT']['risk8']['positive'] == 4
    assert result['primary']['comparisons']['MULTI_minus_SINGLE']['risk8']['lifecycles'][2]['replica_deltas'] == [6]*16


def test_cutoff_or_missing_return_suppresses_affected_mean_without_reweighting():
    rows = curve_rows(); valid = {k: True for k in rows}
    rows[(0, 'risk1', 'MULTI', 524288, 0)]['result']['status'] = 'CUTOFF'
    del rows[(3, 'risk8', 'SINGLE', 32768, 0)]
    result = analysis.full_game_curve(rows, valid)
    assert not result['complete']
    assert result['primary']['comparisons']['MULTI_minus_PARENT']['risk1']['mean'] is None
    assert result['primary']['comparisons']['MULTI_minus_PARENT']['risk8']['mean'] == 5
    assert result['curve'][1]['comparisons']['MULTI_minus_SINGLE']['risk8']['mean'] is None


@pytest.mark.parametrize('query,kind,bootstrap,expected', [
    ('risk1', 'BOOTSTRAP', 3., 3.5), ('risk8', 'BOOTSTRAP', -2., -1.5),
    ('risk1', 'WIN_BOUNDARY', None, 2.5), ('risk8', 'WIN_BOUNDARY', None, 9.5),
    ('risk1', 'LOSS', None, .5), ('risk8', 'LOSS', None, -6.5)])
def test_target_excludes_source_reward_and_counts_endpoint_exactly_once(query, kind, bootstrap, expected):
    # The 999 source reward must never leak into its afterstate target.
    assert analysis.expected_target([999, 1024, 2048], 0, 2, kind, query, bootstrap) == expected


def fixtures():
    source = dict(counts=dict(reward=dict(constant=.25)))
    a = [2]+[0]*15; b = [2, 2]+[0]*14
    queue = [dict(step=0, afterstate=a, score_prefix=4), dict(step=1, afterstate=b, score_prefix=12)]
    first = dict(episode=0, seed=analysis.training_seed(0, 'risk1', 0), start_step=0, end_step=2,
        start_board=[1, 1]+[0]*14, end_board=[2, 2, 1]+[0]*13,
        actions=['LEFT', 'LEFT'], scores=[4, 8], spawned_cells=[1, 2], spawned_ranks=[1, 1],
        chosen_values=[1.5, 2.5], chosen_raw_values=[2., 3.], queue_before=[], queue_after=queue,
        update_records=[], censored_updates=0, censored_last_update=False,
        pending_before=None, pending_after=None, updates_before=0, updates_after=0,
        cumulative_updates=0, cumulative_transitions=2, status='ACTIVE', budget_status='BUDGET_END',
        horizon=2, start_return_score=0, return_score=12, seconds=.01,
        target_counts=dict(queue_appends=2), initial_spawns=[dict(cell=0, rank=1), dict(cell=1, rank=1)],
        environment_counts=dict(sampled_transitions=2, initial_spawns=2, environment_random_draws=8,
            ground_explicit_swipe_calls=2, ground_state_status_calls=3, ground_status_internal_swipe_calls=12),
        model_counts=dict(choose_calls=2, inner_choose_calls=2))
    end = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1]
    c = list(end); c[0] = 0
    def update(entry, phase, category, reward, tail):
        target = reward/2048.+tail
        return dict(start_step=entry['step'], end_step=2, afterstate=entry['afterstate'], phase=phase,
            type=category, reward_score=reward, tail=tail, target=target, raw_target=target+.5,
            error=.75, work=dict(td_updates=1))
    c_entry = dict(step=2, afterstate=c, score_prefix=12)
    second = dict(episode=0, seed=first['seed'], start_step=2, end_step=3,
        start_board=first['end_board'], end_board=end, actions=['RIGHT'], scores=[0],
        spawned_cells=[0], spawned_ranks=[1], chosen_values=[1.25], chosen_raw_values=[1.75],
        queue_before=deepcopy(queue), queue_after=[], censored_updates=0, censored_last_update=False,
        pending_before=None, pending_after=None, updates_before=0, updates_after=3,
        cumulative_updates=3, cumulative_transitions=3, status='LOST', budget_status='EPISODE_END',
        horizon=2, start_return_score=12, return_score=12, seconds=.01,
        target_counts=dict(queue_appends=1, queue_removals=3, target_constructions=3,
            bootstrap_updates=1, loss_updates=2),
        update_records=[update(queue[0], 'PRE_ACTION', 'BOOTSTRAP', 8, 1.25),
            update(queue[1], 'POST_TERMINAL', 'LOSS', 0, -1.), update(c_entry, 'POST_TERMINAL', 'LOSS', 0, -1.)],
        environment_counts=dict(sampled_transitions=1, initial_spawns=0, environment_random_draws=2,
            ground_explicit_swipe_calls=1, ground_state_status_calls=1, ground_status_internal_swipe_calls=4),
        model_counts=dict(choose_calls=1, inner_choose_calls=1, td_updates=3, inner_td_updates=3,
            inner_table_update_occurrences=96, inner_table_updates=24))
    return first, second, source, update


def test_pause_carries_whole_queue_and_loss_closes_every_action_once():
    first, second, source, _ = fixtures()
    assert all(analysis.multi_segment_checks(first, None, 'risk1', source, horizon=2).values())
    assert all(analysis.multi_segment_checks(second, first, 'risk1', source, horizon=2).values())
    broken = deepcopy(second); broken['update_records'][1]['start_step'] = 0
    assert not analysis.multi_segment_checks(broken, first, 'risk1', source, horizon=2)['queue_semantics']
    broken = deepcopy(second); broken['queue_before'][0]['score_prefix'] += 4
    assert not analysis.multi_segment_checks(broken, first, 'risk1', source, horizon=2)['segment_continuity']


def test_winning_mature_target_and_terminal_flush_include_winning_score_once():
    first, row, source, update = fixtures(); queue = first['queue_after']
    row.update(status='WON', end_board=[11, 1]+[0]*14, scores=[2048], return_score=2060,
        spawned_cells=[1], chosen_values=[2.], chosen_raw_values=[1.], updates_after=2, cumulative_updates=2,
        update_records=[update(queue[0], 'PRE_ACTION', 'WIN_BOUNDARY', 8, 2.),
            update(queue[1], 'POST_TERMINAL', 'WIN_BOUNDARY', 2048, 1.)])
    row['environment_counts']['ground_status_internal_swipe_calls'] = 0
    row['model_counts'].update(td_updates=2, inner_td_updates=2, inner_table_update_occurrences=64, inner_table_updates=16)
    row['target_counts'] = dict(queue_removals=2, target_constructions=2, win_boundary_updates=2)
    assert all(analysis.multi_segment_checks(row, first, 'risk1', source, horizon=2).values())
    broken = deepcopy(row); broken['update_records'][0]['target'] += 1.
    assert not analysis.multi_segment_checks(broken, first, 'risk1', source, horizon=2)['td_targets']


def test_real_cutoff_censors_remaining_queue_without_terminal_updates(monkeypatch):
    first, row, source, _ = fixtures(); monkeypatch.setattr(analysis, 'MAX_STEPS', 3)
    end = [2, 2, 1]+[0]*13; after = list(end); after[2] = 0
    row.update(status='CUTOFF', end_board=end, spawned_cells=[2], censored_last_update=True,
        censored_updates=2, censored_queue=[deepcopy(first['queue_after'][1]),
            dict(step=2, afterstate=after, score_prefix=12)], update_records=row['update_records'][:1],
        updates_after=1, cumulative_updates=1)
    row['model_counts'].update(td_updates=1, inner_td_updates=1, inner_table_update_occurrences=32, inner_table_updates=8)
    row['target_counts'] = dict(queue_appends=1, queue_removals=1, target_constructions=1,
        bootstrap_updates=1, censored_updates=2)
    assert all(analysis.multi_segment_checks(row, first, 'risk1', source, horizon=2).values())
    broken = deepcopy(row); broken['censored_updates'] = 1
    assert not analysis.multi_segment_checks(broken, first, 'risk1', source, horizon=2)['queue_semantics']
