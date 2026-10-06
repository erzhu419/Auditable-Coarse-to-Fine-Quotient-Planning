"""Finite paired rosters, conditional ranking errors and SHALLOW cost checks."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_shallow_sampling_v141 as analysis
from tests.test_analyze_controlled_predictive_program_planning_v140 import budget_fixture as deep_budget_fixture

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_shallow_sampling_v141.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before,
        tests_run=sum(Path(str(item.path)).resolve() == Path(__file__).resolve() for item in request.session.items),
        environment_samples=0, model_samples=0,
        scope='finite logical roster, censored returns, equal game/history conditional errors, shallow sampling and cost equations'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def rows():
    indexed = {}
    for life in analysis.LIVES:
        for query in analysis.QUERIES:
            for method in analysis.METHODS:
                for replica in range(analysis.REPLICAS):
                    benefit = {'H2': 0, 'SHALLOW': 1, 'LEARNED64': 3}[method]*(life+1)
                    indexed[(life, query, method, replica)] = dict(result=dict(
                        status='LOST', utility=10*life+replica+benefit, score=4, steps=1))
    return indexed


def test_192_games_pair_inside_histories_without_recounting_baselines():
    indexed = rows(); output = analysis.full_game_comparison(indexed, {key: True for key in indexed})
    assert len(indexed) == 192 and output['complete']
    assert output['comparisons']['LEARNED64-SHALLOW']['risk1']['mean'] == 5
    assert output['comparisons']['SHALLOW-H2']['risk8']['mean'] == 2.5
    assert output['comparisons']['LEARNED64-H2']['risk1']['mean'] == 7.5


def test_cutoff_and_missing_games_suppress_affected_complete_return_only():
    indexed = rows(); valid = {key: True for key in indexed}
    indexed[(0, 'risk1', 'SHALLOW', 0)]['result']['status'] = 'CUTOFF'
    del indexed[(3, 'risk8', 'LEARNED64', 7)]
    output = analysis.full_game_comparison(indexed, valid)
    assert not output['complete']
    assert output['methods']['SHALLOW']['risk1']['lifecycles'][0]['games'] == 8
    assert output['methods']['SHALLOW']['risk1']['lifecycles'][0]['statuses']['CUTOFF'] == 1
    assert output['comparisons']['LEARNED64-SHALLOW']['risk1']['mean'] is None
    assert output['comparisons']['LEARNED64-H2']['risk8']['mean'] is None
    assert output['comparisons']['LEARNED64-H2']['risk1']['mean'] == 7.5


def choice(left, right):
    action = 'LEFT' if left >= right else 'RIGHT'
    return dict(action=action, value=max(left, right),
        action_values=dict(LEFT=dict(value=left), RIGHT=dict(value=right)))


def test_shared_q_offset_does_not_become_action_ranking_error():
    result = analysis.action_metrics(choice(3, 1), choice(13, 11))
    assert result['signed_q_error'] == result['absolute_q_error'] == 10
    assert result['centered_absolute_q_error'] == result['centered_squared_q_error'] == 0
    assert result['h2_proxy_regret'] == result['greedy_disagreement'] == 0


def test_reversed_ranking_has_positive_frozen_proxy_regret():
    result = analysis.action_metrics(choice(3, 1), choice(1, 3))
    assert result['signed_q_error'] == 0 and result['h2_proxy_regret'] == 2
    assert result['centered_absolute_q_error'] == 2 and result['centered_squared_q_error'] == 4
    assert result['greedy_disagreement'] == 1
    incomplete = choice(1, 3); del incomplete['action_values']['LEFT']
    with pytest.raises(ValueError, match='roster'): analysis.action_metrics(choice(3, 1), incomplete)


def test_conditional_roots_average_by_game_then_by_history():
    indexed = {}
    for life in analysis.LIVES:
        for query in analysis.QUERIES:
            for replica in range(analysis.REPLICAS):
                for step in range(1 if replica else 20):
                    indexed[(life, query, replica, 32*step)] = dict(
                        SHALLOW=analysis.action_metrics(choice(3, 1), choice(3, 1)),
                        LEARNED64=analysis.action_metrics(choice(3, 1), choice(1, 3) if replica == 0 else choice(3, 1)))
    result = analysis.conditional_comparison(indexed)
    assert result['roots'] == 216
    assert result['methods']['LEARNED64']['risk1']['means']['greedy_disagreement'] == .125
    assert result['learned_minus_shallow']['risk8']['means']['h2_proxy_regret'] == .25
    del indexed[(3, 'risk8', 7, 0)]
    assert analysis.conditional_comparison(indexed)['methods']['LEARNED64']['risk8']['means']['h2_proxy_regret'] is None


def shallow_budget_fixture():
    counts, options = deep_budget_fixture()
    options['DOWN']['used'] = 4
    counts.update(program_swipe_calls=4, bootstrap_swipe_calls=4, model_swipes_used=8, learned_swipe_calls=8,
        legal_swipes=4, learned_terminal_checks=6, line_lookup_calls=16, line_hits=16,
        composition_line_gathers=16, composition_line_scatters=16, line_bound_output_cells=64,
        line_zero_mask_rank_reads=64, tree_calls=0, tree_order_reads=0, feature_board_reads=0,
        feature_neighbor_comparisons=0, feature_predicate_values=0, tree_predicate_checks=0,
        rollout_actions=0, model_sampled_transitions=1, simulation_uniform_draws=2,
        spawn_empty_cell_reads=16, spawn_board_writes=1, rollout_reward_additions=0)
    return counts, options


def test_shallow_one_sample_uses_four_h1_swipes_below_shared_ceiling():
    counts, options = shallow_budget_fixture()
    assert all(analysis.shallow_counts_valid(counts, options).values())
    assert counts['model_swipes_used'] < counts['model_swipe_budget']


def test_unreported_sampling_and_hidden_program_continuation_fail():
    counts, options = shallow_budget_fixture(); counts['simulation_uniform_draws'] = 1
    assert not analysis.shallow_counts_valid(counts, options)['shallow_sampling']
    counts, options = shallow_budget_fixture(); counts['tree_calls'] = 1
    assert not analysis.shallow_counts_valid(counts, options)['shallow_no_program_continuation']
    counts, options = shallow_budget_fixture(); counts['compiled_programs'] = 1
    assert not analysis.shallow_counts_valid(counts, options)['no_evaluation_fitting']


def test_changed_sample_allocation_and_missing_local_program_are_detected():
    counts, options = shallow_budget_fixture(); options['DOWN']['rollouts'] = 2
    assert not analysis.shallow_counts_valid(counts, options)['shallow_budget']
    counts, options = shallow_budget_fixture(); counts['line_misses'] = 1
    assert not analysis.shallow_counts_valid(counts, options)['shallow_composition']


def test_all_legal_root_options_and_rewards_are_checked():
    board = [1, 1]+[0]*14; options = {}
    for action in ('DOWN', 'LEFT', 'RIGHT', 'UP'):
        after, score, changed = analysis.previous.ground.swipe_board_v1(tuple(board),
            analysis.previous.ground.Swipe2048Action(action))
        if changed:
            cap = 8*after.count(0); samples = max(1, cap//16)
            options[action] = dict(afterstate=list(after), score=score, tail_value=0., value=score/2048.,
                budget=cap, rollouts=samples, used=4*samples)
    selected = min(options, key=lambda action: (-options[action]['value'], action))
    record = dict(status='ACTIVE', action=selected, value=options[selected]['value'], action_values=options, work={})
    checks = analysis.choice_checks(board, record, 'risk1', 'SHALLOW')
    assert checks['complete_root_action_values'] and checks['root_action_values'] and checks['greedy_choice']
    changed = deepcopy(record); del changed['action_values']['DOWN']
    assert not analysis.choice_checks(board, changed, 'risk1', 'SHALLOW')['complete_root_action_values']
    changed = deepcopy(record); changed['action_values']['LEFT']['score'] += 4
    assert not analysis.choice_checks(board, changed, 'risk1', 'SHALLOW')['root_action_values']
