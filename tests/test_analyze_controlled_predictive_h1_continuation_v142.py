"""Finite paired rosters, retained diagnostics and query-H1 cost equations."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_h1_continuation_v142 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_h1_continuation_v142.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before,
        tests_run=sum(Path(str(item.path)).resolve() == Path(__file__).resolve() for item in request.session.items),
        environment_samples=0, model_samples=0,
        scope='finite 256-game pairing, cutoff suppression, equal game/history fixed-root errors and complete H1 accounting'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def rows():
    indexed = {}
    for life in analysis.LIVES:
        for query in analysis.QUERIES:
            for method in analysis.METHODS:
                for replica in range(analysis.REPLICAS):
                    benefit = {'H2': 0, 'SHALLOW': 1, 'LEARNED64': 3, 'H1_CONT': 5}[method]*(life+1)
                    indexed[(life, query, method, replica)] = dict(result=dict(
                        status='LOST', utility=10*life+replica+benefit, score=4, steps=1))
    return indexed


def choice(left, right):
    return dict(action='LEFT' if left >= right else 'RIGHT', value=max(left, right),
        action_values=dict(LEFT=dict(value=left), RIGHT=dict(value=right)))


def test_256_games_pair_new_method_against_all_three_retained_methods():
    indexed = rows(); result = analysis.full_game_comparison(indexed, {key: True for key in indexed})
    assert len(indexed) == 256 and result['complete']
    assert result['comparisons']['H1_CONT-LEARNED64']['risk1']['mean'] == 5
    assert result['comparisons']['H1_CONT-SHALLOW']['risk8']['mean'] == 10
    assert result['comparisons']['H1_CONT-H2']['risk1']['mean'] == 12.5


def test_cutoff_and_missing_retained_games_preserve_roster_and_suppress_returns():
    indexed = rows(); valid = {key: True for key in indexed}
    indexed[(0, 'risk1', 'H1_CONT', 0)]['result']['status'] = 'CUTOFF'
    del indexed[(3, 'risk8', 'LEARNED64', 7)]
    result = analysis.full_game_comparison(indexed, valid)
    assert not result['complete']
    assert result['methods']['H1_CONT']['risk1']['lifecycles'][0]['games'] == 8
    assert result['methods']['H1_CONT']['risk1']['lifecycles'][0]['statuses']['CUTOFF'] == 1
    assert result['comparisons']['H1_CONT-SHALLOW']['risk1']['mean'] is None
    assert result['comparisons']['H1_CONT-LEARNED64']['risk8']['mean'] is None
    assert result['comparisons']['H1_CONT-H2']['risk8']['mean'] == 12.5


def test_fixed_root_errors_separate_common_bias_from_action_order():
    offset = analysis.action_metrics(choice(3, 1), choice(13, 11))
    reversed_order = analysis.action_metrics(choice(3, 1), choice(1, 3))
    assert offset['signed_q_error'] == offset['absolute_q_error'] == 10
    assert offset['centered_absolute_q_error'] == offset['h2_proxy_regret'] == 0
    assert reversed_order['greedy_disagreement'] == 1 and reversed_order['h2_proxy_regret'] == 2
    incomplete = choice(1, 3); del incomplete['action_values']['LEFT']
    with pytest.raises(ValueError, match='roster'): analysis.action_metrics(choice(3, 1), incomplete)


def test_fixed_roots_average_each_game_and_history_equally():
    indexed = {}
    for life in analysis.LIVES:
        for query in analysis.QUERIES:
            for replica in range(analysis.REPLICAS):
                for step in range(1 if replica else 20):
                    good = analysis.action_metrics(choice(3, 1), choice(3, 1))
                    worse = analysis.action_metrics(choice(3, 1), choice(1, 3) if replica == 0 else choice(3, 1))
                    indexed[(life, query, replica, 32*step)] = dict(SHALLOW=good, LEARNED64=worse, H1_CONT=good)
    result = analysis.conditional_comparison(indexed)
    assert result['roots'] == 216
    assert result['methods']['LEARNED64']['risk1']['means']['greedy_disagreement'] == .125
    assert result['comparisons']['H1_CONT-LEARNED64']['risk8']['means']['h2_proxy_regret'] == -.25
    del indexed[(3, 'risk8', 7, 0)]
    assert analysis.conditional_comparison(indexed)['methods']['H1_CONT']['risk8']['means']['h2_proxy_regret'] is None


def budget_fixture(empty=2, terminal=None):
    calls = 1 if empty == 1 or terminal else 3
    actions = 0 if terminal == 'LOST' else calls
    bootstrap = 0 if terminal else 1
    legal = 1+(0 if terminal == 'LOST' else 2*calls)+2*bootstrap
    predictions = (0 if terminal == 'LOST' else 2*calls-int(terminal == 'WON'))+2*bootstrap
    samples = 1+actions-int(terminal == 'WON')
    used = 4*(calls+bootstrap)
    options = dict(DOWN=dict(afterstate=[0]*empty+[1, 2]*7+[1]*(2-empty), budget=8*empty, used=used, rollouts=1))
    counts = dict(choose_calls=1, root_swipe_calls=4, root_legal_actions=1, root_goal_actions=0,
        model_swipe_budget=4+8*empty, model_swipes_used=4+used, learned_swipe_calls=4+used,
        program_swipe_calls=4, continuation_swipe_calls=4*calls, bootstrap_swipe_calls=4*bootstrap,
        root_empty_cell_reads=16, line_lookup_calls=16, line_hits=16, composition_line_gathers=16,
        composition_line_scatters=16, line_misses=0, line_bound_output_cells=64, line_zero_mask_rank_reads=64,
        line_guard_rank_reads=0, line_guard_checks=0, line_table_lookups=4*used, table_lookups=32*predictions,
        learned_terminal_checks=1+legal+bootstrap+calls, legal_swipes=legal, leaf_choose_calls=bootstrap,
        continuation_choose_calls=calls, continuation_value_predictions=predictions-2*bootstrap,
        value_predictions=predictions, continuation_terminal_goal_states=0,
        rollout_terminal_loss_states=int(terminal == 'LOST'), continuation_terminal_loss_states=int(terminal == 'LOST'),
        rollout_terminal_goal_states=int(terminal == 'WON'), rollouts_started=1, rollout_actions=actions,
        model_sampled_transitions=samples, simulation_uniform_draws=2*samples, simulation_rng_initializations=1,
        spawn_empty_cell_reads=16*samples, spawn_board_writes=samples, rollout_reward_additions=actions,
        rollout_mean_additions=1)
    return counts, options


@pytest.mark.parametrize('empty', [1, 2])
def test_h1_selection_and_bootstrap_have_separate_complete_costs(empty):
    counts, options = budget_fixture(empty)
    assert all(analysis.h1_counts_valid(counts, options).values())
    assert counts['continuation_choose_calls'] == (1 if empty == 1 else 3)


@pytest.mark.parametrize('terminal', ['WON', 'LOST'])
def test_terminal_continuation_preserves_cost_and_skips_bootstrap(terminal):
    counts, options = budget_fixture(terminal=terminal)
    assert all(analysis.h1_counts_valid(counts, options).values())
    assert counts['bootstrap_swipe_calls'] == 0 and counts['model_sampled_transitions'] == 1


def test_hidden_sampling_tree_and_fitting_are_detected():
    counts, options = budget_fixture(); counts['simulation_uniform_draws'] -= 1
    assert not analysis.h1_counts_valid(counts, options)['h1_sampling']
    counts, options = budget_fixture(); counts['tree_calls'] = 1
    assert not analysis.h1_counts_valid(counts, options)['h1_no_tree']
    counts, options = budget_fixture(); counts['compiled_programs'] = 1
    assert not analysis.h1_counts_valid(counts, options)['no_evaluation_fitting']


def test_extra_h1_steps_and_missing_prediction_cost_are_detected():
    counts, options = budget_fixture(1); counts['continuation_choose_calls'] = 3
    assert not analysis.h1_counts_valid(counts, options)['h1_continuation']
    counts, options = budget_fixture(); counts['table_lookups'] -= 32
    assert not analysis.h1_counts_valid(counts, options)['h1_composition']
    counts, options = budget_fixture(); options['DOWN']['used'] += 4
    assert not analysis.h1_counts_valid(counts, options)['h1_budget']


def test_all_root_actions_and_true_immediate_rewards_are_checked():
    board = [1, 1]+[0]*14; options = {}
    for action in ('DOWN', 'LEFT', 'RIGHT', 'UP'):
        after, score, changed = analysis.v140.ground.swipe_board_v1(tuple(board), analysis.v140.ground.Swipe2048Action(action))
        if changed:
            options[action] = dict(afterstate=list(after), score=score, tail_value=0., value=score/2048.)
    chosen = min(options, key=lambda action: (-options[action]['value'], action))
    record = dict(status='ACTIVE', action=chosen, value=options[chosen]['value'], action_values=options)
    assert all(analysis.root_choice_checks(board, record, 'risk1').values())
    damaged = deepcopy(record); del damaged['action_values']['DOWN']
    assert not analysis.root_choice_checks(board, damaged, 'risk1')['complete_root_action_values']
    damaged = deepcopy(record); damaged['action_values']['LEFT']['score'] += 4
    assert not analysis.root_choice_checks(board, damaged, 'risk1')['root_action_values']
