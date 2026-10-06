"""Synthetic native checks for replay, bounded counts and exact scalar anchors."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_anchored_success_v127 import AnchoredSuccess, choose_gpi
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/controlled_predictive_anchored_success_v127_build'
BOARD = [1, 1, 0, 0] + [0] * 12
OTHER = [2, 0, 1, 0] + [0] * 12
GOAL = [4] + [0] * 15
REWARD = dict(reward_weight=1., failure_penalty=0., goal_bonus=0.)
RISK = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
MODELS, SOURCES = [], []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_anchored_success_v127.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    work = sum((m.counts for m in MODELS), Counter())
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before, core_work=dict(work),
        source_work=dict(sum((m.counts for m in SOURCES), Counter())),
        setup_counts=dict(sum((m.setup_counts for m in MODELS + SOURCES), Counter())),
        newly_sampled_environment_transitions=0,
        fitted_afterstates=work['success_observation_updates'], unique_feature_updates=work['unique_feature_updates'],
        scope='Synthetic boards and retained-record fixtures only. Core source-prefixed counters overlap source_work.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def model(query=REWARD):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    source.weights.flags.writeable = False
    SOURCES.append(source)
    result = AnchoredSuccess(source, query, BUILD)
    MODELS.append(result)
    return result


def trace():
    final = [2, 0, 0, 1] + [0] * 10 + [2, 0]
    return dict(initial_board=BOARD, actions=['LEFT', 'UP'], spawned_cells=[15, 14],
        spawned_ranks=[1, 2], scores=[4, 0], final_board=final)


def test_native_replay_matches_afterstates_without_source_search_or_sampling():
    result = model(); before = result.source.counts.copy()
    boards = result.replay(trace())
    np.testing.assert_array_equal(boards, [[2] + [0] * 15, [2, 0, 0, 1] + [0] * 12])
    assert result.counts['replay_swipe_calls'] == 2
    assert result.counts['replay_line_table_lookups'] == 8
    assert result.counts['replay_recorded_spawns'] == 2
    assert result.source.counts == before


def test_replay_rejects_score_spawn_and_final_board_disagreement():
    result = model()
    for field, value, reason in [('scores', [8, 0], 'score'),
            ('spawned_cells', [0, 14], 'spawn'), ('final_board', [0] * 16, 'final board')]:
        row = deepcopy(trace()); row[field] = value
        with pytest.raises(ValueError, match=reason): result.replay(row)


def test_one_board_updates_each_unique_feature_once_and_preserves_global_counts():
    result = model()
    indices = result.source.feature_indices(BOARD)
    unique = np.unique(indices)
    assert len(unique) < len(indices)
    fit = result.train_episode([BOARD, GOAL], 'WON')
    assert fit['updates'] == fit['success_afterstates'] == 1
    assert fit['unique_feature_updates'] == len(unique)
    assert result.updates == result.successes == 1
    assert int(result.visits.sum()) == int(result.wins.sum()) == len(unique)
    np.testing.assert_array_equal(result.visits.reshape(-1)[unique], np.ones(len(unique), dtype=np.uint64))
    assert result.probabilities([BOARD, GOAL]) == [1., 1.]


def test_bounded_probability_matches_occurrence_average_with_empirical_global_prior():
    result = model()
    assert result.global_success_rate == .5
    assert result.probabilities([BOARD, GOAL]) == [.5, 1.]
    result.train_episode([BOARD, GOAL], 'WON')
    result.train_episode([OTHER, OTHER], 'LOST')
    assert result.global_success_rate == 1/3
    indices = result.source.feature_indices(BOARD)
    v, w = result.visits.reshape(-1), result.wins.reshape(-1)
    expected = sum((float(w[i]) + 1/3) / (float(v[i]) + 1) for i in indices) / 32
    assert result.probabilities([BOARD])[0] == expected
    assert all(0 <= x <= 1 for x in result.probabilities([BOARD, OTHER, GOAL]))


def test_cutoff_and_readonly_evaluation_never_modify_count_arrays():
    result = model(); visits, wins = result.visits.copy(), result.wins.copy()
    fit = result.train_episode([BOARD, OTHER], 'CUTOFF')
    assert fit['updates'] == 0 and fit['censored_afterstates'] == 2
    assert result.updates == result.successes == 0
    result.visits.flags.writeable = False; result.wins.flags.writeable = False
    result.probabilities([BOARD]); result.choose(BOARD, RISK)
    with pytest.raises(RuntimeError, match='cannot be updated'):
        result.train_episode([BOARD], 'LOST')
    np.testing.assert_array_equal(result.visits, visits)
    np.testing.assert_array_equal(result.wins, wins)


def test_own_query_preserves_source_action_values_without_probability_readout():
    for query in (REWARD, RISK):
        result = model(query); result.train_episode([BOARD, GOAL], 'WON')
        for board in (BOARD, OTHER, [3, 3] + [0] * 14, GOAL):
            expected = result.source.choose(board, query)
            for mode in ('LEARNED', 'CONSTANT'):
                actual = result.choose(board, query, mode=mode)
                assert actual['action'] == expected['action']
                assert actual['value'] == expected['value']
                for action, row in expected['action_values'].items():
                    assert all(actual['action_values'][action][key] == value for key, value in row.items())
                    assert actual['action_values'][action]['success_probability'] is None
        assert result.counts['success_predictions'] == result.counts['constant_probability_predictions'] == 0


def test_cross_query_values_follow_scalar_anchor_and_analytic_goal():
    result = model(RISK)
    result.train_episode([BOARD, GOAL], 'WON'); result.train_episode([OTHER], 'LOST')
    query = dict(reward_weight=1., failure_penalty=1., goal_bonus=1.)
    source = result.source.choose(BOARD, RISK)
    actual = result.choose(BOARD, query)
    for action, row in actual['action_values'].items():
        assert row['anchor_value'] == source['action_values'][action]['value']
        assert row['value'] == row['anchor_value'] + 3 - 6 * row['success_probability']
    constant = result.choose(BOARD, query, mode='CONSTANT')
    assert all(row['success_probability'] == .5 for row in constant['action_values'].values())
    goal_choice = result.choose([3, 3] + [0] * 14, dict(reward_weight=1., failure_penalty=8., goal_bonus=8.))
    assert goal_choice['value'] == 16/2048 + 8
    assert goal_choice['success_probability'] == 1.


def test_gpi_selects_actual_scalar_policy_branch_and_action_ties():
    models = [model(REWARD), model(RISK)]
    for item in models: item.train_episode([BOARD, GOAL], 'WON')
    query = dict(reward_weight=1., failure_penalty=1., goal_bonus=1.)
    choices = [item.choose(BOARD, query) for item in models]
    best = min(((-row['value'], action, index) for index, choice in enumerate(choices)
                for action, row in choice['action_values'].items()))
    actual = choose_gpi(models, BOARD, query)
    assert (actual['value'], actual['action'], actual['policy_index']) == (-best[0], best[1], best[2])
    assert actual['anchor_value'] == choices[best[2]]['action_values'][best[1]]['anchor_value']


def test_saved_counts_keep_shared_sparse_addresses_and_prefix_metadata():
    result = model(); result.train_episode([BOARD, GOAL], 'WON'); result.train_episode([OTHER], 'LOST')
    saved = result.save(BUILD / 'synthetic_roundtrip.npz')
    with np.load(saved['path'], allow_pickle=False) as data:
        meta = json.loads(str(data['metadata']))
        assert meta['schema'] == 'acfqp.anchored_success.v127'
        assert meta['updates'] == 2 and meta['successes'] == 1 and meta['global_success_rate'] == .5
        visits = np.zeros(result.visits.size, dtype=np.uint64); wins = visits.copy()
        visits[data['indices']] = data['visits']; wins[data['indices']] = data['wins']
        np.testing.assert_array_equal(visits.reshape(result.visits.shape), result.visits)
        np.testing.assert_array_equal(wins.reshape(result.wins.shape), result.wins)
        assert np.all(data['wins'] <= data['visits'])
