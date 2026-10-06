"""Check paired labels, held-out coverage and immutable evaluation evidence."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from scripts import analyze_controlled_predictive_paired_ntuple_v130 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_paired_ntuple_v130.analysis_checks.json'
    log = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    log['attempts'].append(dict(failures=request.session.testsfailed-before,
        environment_samples=0, model_samples=0, model_updates=0,
        scope='synthetic paired labels, held-out coverage and accounting fixtures'))
    path.write_text(json.dumps(log, indent=2)+'\n')


def test_paired_gap_metrics_keep_noise_and_zero_labels():
    labels = [[1.]*4+[-1.]*4, [-2.]*8, [0.]*8]
    result = analysis.gap_statistics([1., -2., 0.], labels)
    assert result['action_pairs'] == 3
    assert result['rmse'] == pytest.approx(np.sqrt(1/3))
    assert result['sign_agreement'] == 2
    assert result['half_label_rmse'] == pytest.approx(np.sqrt(4/3))
    assert result['half_label_sign_agreement'] == 2
    assert analysis.gap_statistics([], [])['rmse'] is None


def test_first_choice_and_changed_continuation_decompose_paired_returns():
    parent = np.arange(8, dtype=float)
    first = parent+2
    full = parent-1
    result = analysis.heldout_differences(parent, first, full)
    assert result['paired']['first_only_minus_parent']['mean'] == 2
    assert result['paired']['full_update_minus_first_only']['mean'] == -3
    assert result['paired']['full_update_minus_parent']['mean'] == -1
    assert result['paired']['full_update_minus_parent']['mc_se'] == 0


def test_heldout_aggregation_keeps_missing_slots_and_equal_life_weights():
    cases = []
    for query in analysis.QUERIES:
        for life in analysis.LIVES:
            for i in range(16):
                available = i <= life
                row = dict(life=life, query=query, available=available, complete=True)
                if available:
                    row.update(analysis.heldout_differences(np.zeros(8), np.full(8, life), np.full(8, 2*life)))
                cases.append(row)
    result = analysis.aggregate_heldout(cases)
    assert result['four_life_means']['risk1']['paired']['full_update_minus_parent']['mean'] == 3
    assert sum(r['missing'] for r in result['lifecycles']) == 108
    changed = deepcopy(cases)
    changed[0]['complete'] = False
    assert not analysis.aggregate_heldout(changed)['four_life_means']['risk1']['complete']


def test_feature_accounting_merges_shared_addresses_and_counts_goal_bypass():
    same = dict(eligible=True, afterstate=[1]*16, reference_afterstate=[1]*16)
    result = analysis.expected_pair_counts([same])
    assert result['pair_feature_occurrences'] == 64
    assert result['pair_distinct_addresses'] == 4
    assert result['pair_updates'] == 0 and result['unidentifiable_pairs'] == 1
    goal = dict(same, reference_afterstate=[11]+[0]*15)
    result = analysis.expected_pair_counts([goal])
    assert result['pair_feature_occurrences'] == 32
    assert result['pair_table_updates'] == 4
    assert result['pair_update_occurrences'] == 32
    assert result['pair_terminal_goal_bypasses'] == 1


def test_fixed_parent_and_frozen_predictions_preserve_goals_and_residual_identity():
    root = dict(root_id=0, life=0, query='risk1', split='TRAIN', board=[10, 10]+[0]*14)
    rows = {}
    for action in ('DOWN', 'LEFT', 'RIGHT', 'UP'):
        after, score, changed = analysis.ground.swipe_board_v1(tuple(root['board']), analysis.ground.Swipe2048Action(action))
        if changed:
            goal = max(after) >= 11
            rows[action] = dict(afterstate=list(after), score=score, anchor_value=score/2048.,
                value=score/2048.+(1 if goal else -.5), success_probability=1. if goal else .25)
    choice = min(rows, key=lambda a: (-rows[a]['value'], a))
    root.update(actions=sorted(rows), parent=dict(action=choice, action_values=rows))
    source = dict(counts={'reward': dict(constant=.25)})
    assert analysis.parent_prediction_valid(root, source)
    methods = dict(PARENT=deepcopy(root['parent']))
    for kind in ('PRIOR', 'SCRATCH'):
        values = {}
        for action, row in rows.items():
            base = row['value'] if kind == 'PRIOR' else analysis.scratch_value(row, 'risk1')
            values[action] = dict(row, base_value=base, residual=0., value=base)
        methods[kind] = dict(action=min(values, key=lambda a: (-values[a]['value'], a)), action_values=values)
    frozen = dict(root_id=0, query='risk1', split='TRAIN', methods=methods)
    assert analysis.frozen_prediction_valid(root, frozen)
    frozen['methods']['PRIOR']['action_values'][choice]['residual'] = 1.
    assert not analysis.frozen_prediction_valid(root, frozen)


def test_full_game_cutoff_suppresses_only_affected_primary_comparison():
    indexed = {}
    for life in analysis.LIVES:
        for query in analysis.QUERIES:
            for method in analysis.METHODS:
                for replica in range(16):
                    indexed[(life, query, method, replica)] = dict(result=dict(status='LOST',
                        utility=life+int(method == 'PRIOR'), score=4, steps=1))
    valid = {k: True for k in indexed}
    result = analysis.full_game_summary(indexed, valid)
    assert result['comparisons']['PRIOR_minus_PARENT']['risk1']['mean'] == 1
    assert result['comparisons']['PRIOR_minus_PARENT']['risk1']['positive'] == 4
    indexed[(0, 'risk1', 'PRIOR', 0)]['result']['status'] = 'CUTOFF'
    result = analysis.full_game_summary(indexed, valid)
    assert result['comparisons']['PRIOR_minus_PARENT']['risk1']['mean'] is None
    assert result['comparisons']['PRIOR_minus_PARENT']['risk8']['mean'] == 1
