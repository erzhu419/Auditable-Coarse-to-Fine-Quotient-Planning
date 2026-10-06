"""Finite paired-return and planner-accounting fixtures without sampling."""
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_frozen_leaf_planning_v135 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_frozen_leaf_planning_v135.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before, tests_run=len(request.session.items),
        environment_samples=0, model_samples=0, model_updates=0,
        scope='synthetic paired terminal returns and explicit model-enumeration work'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def rows():
    result = {}
    for life in analysis.LIVES:
        for query in analysis.QUERIES:
            for representation in analysis.REPRESENTATIONS:
                for mode in analysis.MODES:
                    for replica in range(analysis.REPLICAS):
                        delta = (life+1)*(1 if representation == 'SINGLE' else -1)
                        value = replica+10*life+int(mode == 'H2')*delta
                        result[(life, query, representation, mode, replica)] = dict(
                            result=dict(status='LOST', utility=value, score=4, steps=1))
    return result


def test_planning_is_paired_inside_each_frozen_representation_and_history():
    indexed = rows(); result = analysis.full_game_comparison(indexed, {key: True for key in indexed})
    assert result['complete']
    assert result['comparisons']['SINGLE']['risk1']['mean'] == 2.5
    assert result['comparisons']['SINGLE']['risk8']['positive'] == 4
    assert result['comparisons']['CAPACITY']['risk1']['mean'] == -2.5
    assert result['comparisons']['CAPACITY']['risk8']['negative'] == 4
    assert result['comparisons']['CAPACITY']['risk8']['lifecycles'][2]['replica_deltas'] == [-3]*16


def test_missing_or_cutoff_game_does_not_change_the_other_comparison():
    indexed = rows(); valid = {key: True for key in indexed}
    indexed[(0, 'risk1', 'SINGLE', 'H2', 0)]['result']['status'] = 'CUTOFF'
    del indexed[(3, 'risk8', 'CAPACITY', 'DIRECT', 0)]
    result = analysis.full_game_comparison(indexed, valid)
    assert not result['complete']
    assert result['comparisons']['SINGLE']['risk1']['mean'] is None
    assert result['comparisons']['CAPACITY']['risk8']['mean'] is None
    assert result['comparisons']['CAPACITY']['risk1']['mean'] == -2.5
    assert result['comparisons']['SINGLE']['risk8']['mean'] == 2.5


def test_readout_invalid_game_prevents_terminal_claim_without_dropping_its_row():
    indexed = rows(); valid = {key: True for key in indexed}
    valid[(1, 'risk8', 'SINGLE', 'H2', 3)] = False
    result = analysis.full_game_comparison(indexed, valid)
    cell = result['methods']['SINGLE']['H2']['risk8']['lifecycles'][1]
    assert cell['games'] == 16 and cell['means']['utility'] is None
    assert result['comparisons']['SINGLE']['risk8']['mean'] is None


@pytest.mark.parametrize('representation', ['SINGLE', 'CAPACITY'])
@pytest.mark.parametrize('mode', ['DIRECT', 'H2'])
def test_enumeration_and_leaf_accounting_remain_distinct_from_random_sampling(representation, mode):
    counts = dict(choose_calls=2, root_swipe_calls=8, root_legal_actions=6, root_goal_actions=1,
        learned_swipe_calls=8, line_table_lookups=32, learned_terminal_checks=8,
        legal_swipes=6, value_predictions=5, terminal_goal_bypasses=1)
    if mode == 'H2':
        counts.update(generated_spawn_outcomes=20, expanded_postspawn_states=20, leaf_choose_calls=20,
            expectimax_probability_products=20, expectimax_probability_sums=20,
            spawn_rank1_outcomes=10, spawn_rank2_outcomes=10, second_ply_swipe_calls=80,
            learned_swipe_calls=88, line_table_lookups=352, legal_swipes=66,
            terminal_goal_bypasses=3, learned_terminal_checks=88, value_predictions=58)
    counts['table_lookups'] = 32*counts['value_predictions']
    if representation == 'CAPACITY':
        occurrences = 32*counts['value_predictions']
        counts.update(bank_0_prediction_occurrences=occurrences//2, bank_1_prediction_occurrences=occurrences//2,
            context_cell_reads=occurrences, context_bank_selections=occurrences,
            context_bank_offset_additions=occurrences)
    assert analysis.planning_counts_valid(counts, mode, representation, 2, 6)
    broken = dict(counts); broken['model_spawn_samples'] = 1
    assert not analysis.planning_counts_valid(broken, mode, representation, 2, 6)
    broken = dict(counts); broken['leaf_choose_calls'] = counts.get('leaf_choose_calls', 0)+1
    assert not analysis.planning_counts_valid(broken, mode, representation, 2, 6)
    broken = dict(counts); broken['table_lookups'] += 1
    assert not analysis.planning_counts_valid(broken, mode, representation, 2, 6)


def test_work_ratios_report_per_decision_and_total_separately():
    direct = dict(steps=10, decision_seconds=1., policy_counts=dict(value_predictions=40, learned_swipe_calls=40))
    planned = dict(steps=20, decision_seconds=4., policy_counts=dict(value_predictions=400, learned_swipe_calls=840))
    result = analysis.work_ratios(direct, planned)
    assert result['steps_ratio'] == 2
    assert result['leaf_predictions']['total_ratio'] == 10
    assert result['leaf_predictions']['per_decision_ratio'] == 5
    assert result['learned_swipes']['total_ratio'] == 21
    assert result['learned_swipes']['per_decision_ratio'] == 10.5
    assert result['decision_seconds']['total_ratio'] == 4
    assert result['decision_seconds']['per_decision_ratio'] == 2


def test_planner_uses_frozen_empirical_spawn_law_not_environment_probability():
    source = dict(rule=dict(spawn_distribution=[[1, 8075, 9026], [2, 951, 9026]]))
    probabilities = analysis.expected_spawn_probabilities(source)
    assert probabilities == [8075/9026, 951/9026]
    assert probabilities != [.9, .1]
