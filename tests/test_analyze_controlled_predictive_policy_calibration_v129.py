"""Detect label leakage, altered proposals, incomplete cohorts and false precision."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_policy_calibration_v129 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_policy_calibration_v129.analysis_checks.json'
    log = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    log['attempts'].append(dict(failures=request.session.testsfailed-before, environment_samples=0,
        model_samples=0, model_updates=0, scope='synthetic calibration, candidate, paired-panel and accounting fixtures'))
    path.write_text(json.dumps(log, indent=2)+'\n')


def snapshot(life=0):
    return dict(life=life, rule={}, training_trace=str(ROOT/'reports/controlled_predictive_policy_consequences_v126'/f'life_{life}'/'training.jsonl.gz'),
        models={p: dict(path=str(ROOT/'reports/controlled_predictive_ntuple_learning_v120'/f'life_{life}'/p/'checkpoint_4096.npz'),
            updates=42, nonzero_weights=7) for p in analysis.POLICIES},
        counts={p: dict(path=str(ROOT/'reports/controlled_predictive_anchored_success_v127'/f'life_{life}'/p/'checkpoint_1024.npz'),
            updates=100, successes=10, constant=.1) for p in analysis.POLICIES})


def original(life=0, policy='reward', episode=0, method='TRAIN', replica=0):
    seed = analysis.old.train_seed(life, policy, episode) if method == 'TRAIN' else (
        analysis.root_seed(life, replica) if method.startswith('ROOT_') else analysis.outer_seed(life, replica))
    return dict(life=life, policy=policy, query=policy, method=method, replica=replica,
        episode_index=episode, seed=seed, eval_id=f'{life}/{method}/{replica}',
        initial_board=[1, 1]+[0]*14, initial_spawns=[dict(cell=0, rank=1), dict(cell=1, rank=1)],
        final_board=[1]*16, actions=['LEFT', 'UP'], scores=[4, 16], spawned_cells=[2, 3], spawned_ranks=[1, 1],
        result=dict(score=20, steps=2, status='LOST', components=[20/2048, 1., 0.], seconds=.1,
            utility=analysis.old.utility(20, 'LOST', policy),
            environment_counts=dict(sampled_transitions=2, initial_spawns=2,
                environment_random_draws=8, ground_explicit_swipe_calls=2),
            policy_counts=dict(choose_calls=2), source_updates_before=42, source_updates_after=42))


def fit_row(source):
    total = float(analysis.calibration_targets(source['scores'], 'LOST', source['policy']).sum())
    return dict(life=source['life'], policy=source['policy'], episode_index=source['episode_index'], source_seed=source['seed'],
        replay_counts=dict(replay_games=1, replay_swipe_calls=2, replay_line_table_lookups=8, replay_recorded_spawns=2),
        replay_seconds=.1, fit=dict(status='LOST', observed_afterstates=2, n=2, analytic_goals=0,
            censored_afterstates=0, target_sum=total, anchor_sum=total-2, residual_sum=2., offset_after=1., seconds=.1,
            work=dict(calibration_games=1, calibration_observed_afterstates=2, calibration_samples=2,
                source_tail_predictions=2, source_table_lookups=64)))


def control(life=0, method='UNCAL_LEARNED', query='risk1', replica=0):
    value = original(life, method=method, replica=replica); value.update(query=query, policy=None,
        eval_id=f'{life}/{method}/{query}/{replica}')
    state = analysis.expected_state(snapshot(life)); shifted = method.startswith('CAL_')
    value.update(actions=['LEFT']*2, candidate_actions=[['LEFT', 'DOWN']]*2,
        candidate_values=[[2., 1.]]*2, comparison_values=[[3., 2.] if shifted else [2., 1.]]*2,
        candidate_goals=[[False, False]]*2, policy_indices=[0, 0])
    value['result'].update(utility=analysis.old.utility(20, 'LOST', query), policy_counts={},
        model_state_before=state, model_state_after=deepcopy(state),
        learning_counts=dict(choose_calls=4, source_choose_calls=4),
        controller_counts=dict(candidate_evaluations=4, policy_comparisons=2, offset_additions=4))
    return value


def test_suffix_targets_include_current_reward_and_exclude_analytic_goal():
    assert np.array_equal(analysis.calibration_targets([4, 16], 'LOST', 'risk_goal'), [20/2048-4, 16/2048-4])
    assert np.array_equal(analysis.calibration_targets([4, 2048], 'WON', 'risk_goal'), [2052/2048+4])
    assert len(analysis.calibration_targets([4, 16], 'CUTOFF', 'reward')) == 0


def test_fit_statistics_are_bound_to_original_query_labels_and_order():
    sources = [original(policy=p) for p in analysis.POLICIES]; rows = [fit_row(s) for s in sources]
    found = analysis.inspect_fit(rows, sources, 0, episodes=1)
    assert all(found['checks'].values()) and found['policies']['risk_goal']['offset'] == 1.
    rows[1]['fit']['target_sum'] += 8
    assert not analysis.inspect_fit(rows, sources, 0, episodes=1)['checks']['fit_source_targets']
    rows[0]['source_seed'] += 1
    assert not analysis.inspect_fit(rows, sources, 0, episodes=1)['checks']['fit_roster']


def test_calibration_only_compares_fixed_candidates_and_never_shifts_goals():
    candidates = [dict(policy='reward', policy_index=0, action='LEFT', value=9., afterstate=[11]+[0]*15),
        dict(policy='risk_goal', policy_index=1, action='DOWN', value=8., afterstate=[1]*16)]
    before = deepcopy(candidates)
    assert analysis.candidate_choice(candidates, dict(reward=100., risk_goal=0.))['action'] == 'LEFT'
    chosen = analysis.candidate_choice(candidates, dict(reward=0., risk_goal=2.))
    assert chosen['policy'] == 'risk_goal' and chosen['comparison_value'] == 10.
    assert candidates == before


def test_control_logs_reconcile_selection_readonly_counts_and_shared_proposals():
    source = snapshot(); offsets = {p: 1. for p in analysis.POLICIES}
    a, b = control(), control(method='CAL_LEARNED')
    assert analysis.control_valid(a, source, offsets) and analysis.control_valid(b, source, offsets)
    assert analysis.same_prefix_proposals(a, b)
    b['candidate_values'][0] = [2.1, 1.]
    assert not analysis.same_prefix_proposals(a, b)
    assert not analysis.control_valid(b, source, offsets)
    a['result']['model_state_after'][0]['count_successes'] += 1
    assert not analysis.control_valid(a, source, offsets)


def test_shared_panel_cases_keep_paired_replica_covariance():
    values = np.arange(8, dtype=float)
    cases = [dict(life=l, available=True, root_id=l) for l in analysis.LIVES for _ in range(8)]
    rows = [dict(life=l, root_id=l, query='risk1', mode='LEARNED', complete=True,
        replica_values=dict(cal_minus_uncal=values.tolist())) for l in analysis.LIVES]
    found = analysis.aggregate_panel(cases, rows, ('query', 'mode'))
    assert found['four_life_means'][0]['paired']['cal_minus_uncal'] == analysis.paired_summary(values)
    rows[0]['complete'] = False
    assert not analysis.aggregate_panel(cases, rows, ('query', 'mode'))['four_life_means'][0]['complete']


def test_missing_control_game_propagates_none_without_refunding_other_rows():
    indexed, valid = {}, {}
    for life in analysis.LIVES:
        for method in analysis.METHODS+analysis.FROZEN:
            for query in ((method[7:],) if method in analysis.FROZEN else analysis.QUERIES):
                for rep in range(8):
                    row = original(life, query, method=method, replica=rep) if method in analysis.FROZEN else control(life, method, query, rep)
                    key = life, method, query, rep; indexed[key], valid[key] = row, True
    assert len(indexed) == 320
    valid[(0, 'CAL_LEARNED', 'risk8', 0)] = False
    report = analysis.control_summary(indexed, valid)
    assert report['comparisons']['CAL_LEARNED_minus_UNCAL_LEARNED']['risk8']['mean_deltas']['utility'] is None
    assert report['methods']['UNCAL_LEARNED']['risk8']['complete']
