"""Synthetic checks for policy-conditioned MC values and whole-vector GPI."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_policy_consequences_v126 import (
    ALPHA, PolicyConsequences, choose_gpi, mc_targets, query_value)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/controlled_predictive_policy_consequences_v126_build'
BOARD = [1, 1, 0, 0] + [0] * 12
GOAL = [4] + [0] * 15
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
MODELS, REFERENCES = [], []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_policy_consequences_v126.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    work = sum((m.counts for m in MODELS), Counter())
    reference = sum((m.counts for m in REFERENCES), Counter())
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before, core_work=dict(work), reference_work=dict(reference),
        setup_counts=dict(sum((m.setup_counts for m in MODELS + REFERENCES), Counter())),
        setup_seconds=sum(m.setup_seconds for m in MODELS + REFERENCES), newly_sampled_environment_transitions=0,
        vector_optimizer_steps=work['mc_updates'], scalar_optimizer_steps=work['component_updates'] + reference['td_updates'],
        scope='Synthetic boards, fixed target arrays and policy fixtures only. No environment sampling.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def rule():
    return LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)


def model():
    result = PolicyConsequences(rule(), BUILD)
    MODELS.append(result)
    return result


def test_mc_targets_exclude_current_reward_and_count_terminal_once():
    assert mc_targets([4, 8, 16], 'LOST') == [[24/2048, 1., 0.], [16/2048, 1., 0.], [0., 1., 0.]]
    assert mc_targets([4, 8, 16], 'WON') == [[24/2048, 0., 1.], [16/2048, 0., 1.], [0., 0., 1.]]
    assert mc_targets([4, 8, 16], 'CUTOFF') == []


def test_native_joint_prediction_and_updates_equal_three_scalar_heads():
    result = model()
    references = [NtupleValue(rule(), BUILD) for _ in range(3)]
    REFERENCES.extend(references)
    for head, reference in enumerate(references):
        reference.weights[:] = np.arange(reference.weights.size).reshape(reference.weights.shape) % 13 * .0001 * (head + 1)
        result.weights[head] = reference.weights
    np.testing.assert_array_equal(result.value(BOARD), [m.value(BOARD) for m in references])
    target = [2., .25, .75]
    errors = result.update(BOARD, target)
    expected = [m.update(BOARD, target[h], ALPHA) for h, m in enumerate(references)]
    np.testing.assert_array_equal(errors, expected)
    for head, reference in enumerate(references):
        np.testing.assert_array_equal(result.weights[head], reference.weights)
    assert result.counts['mc_updates'] == 1
    assert result.counts['table_update_occurrences'] == 96


def test_fit_chronology_and_analytic_goal_exclusion_match_explicit_updates():
    result, reference = model(), model()
    boards, scores = [BOARD, list(reversed(BOARD)), GOAL], [4, 8, 16]
    for board, target in zip(boards[:-1], mc_targets(scores, 'WON')[:-1]):
        reference.update(board, target)
    fit = result.train_episode(boards, scores, 'WON')
    assert fit == dict(status='WON', observed_afterstates=3, updates=2, analytic_goals=1,
        censored_afterstates=0, target_sums=[40/2048, 0., 2.], head_updates=[2, 2, 2])
    np.testing.assert_array_equal(result.weights, reference.weights)


def test_cutoff_censors_entire_game_without_partial_return_fitting():
    result = model(); before = result.weights.copy()
    fit = result.train_episode([BOARD, BOARD], [4, 8], 'CUTOFF')
    assert fit['updates'] == 0 and fit['censored_afterstates'] == 2
    assert fit['target_sums'] == [0., 0., 0.]
    assert result.updates == 0
    np.testing.assert_array_equal(result.weights, before)


def test_action_scores_added_once_and_goals_bypass_native_features():
    result = model()
    board = [3, 3, 0, 0] + [0] * 12
    choice = result.choose(board, QUERY)
    assert choice['score'] == 16
    assert choice['consequences'] == [0., 0., 1.]
    assert choice['value'] == 4. + 16/2048
    before = result.counts.copy()
    assert result.vectors([GOAL, BOARD])[0] == [0., 0., 1.]
    assert result.counts['component_predictions'] - before['component_predictions'] == 3
    assert query_value(2048, [2., .25, .75], QUERY) == 5.


def test_gpi_selects_whole_policy_vector_and_lexicographic_ties():
    class Fixed:
        def __init__(self, rows): self.rows = rows
        def choose(self, board, query):
            values = {a: dict(afterstate=BOARD, score=0, consequences=v,
                value=query_value(0, v, query)) for a, v in self.rows.items()}
            action = max(values, key=lambda a: values[a]['value'])
            return dict(action=action, **values[action], action_values=values, status='ACTIVE')
    # Mixing max reward from policy0 with min failure from policy1 would claim10.
    policies = [Fixed({'LEFT': [10., 1., 0.], 'DOWN': [6., .5, 0.]}),
                Fixed({'LEFT': [0., 0., 0.], 'DOWN': [6., .5, 0.]})]
    choice = choose_gpi(policies, BOARD, dict(reward_weight=1., failure_penalty=10., goal_bonus=0.))
    assert choice['action'] == 'DOWN' and choice['policy_index'] == 0
    assert choice['consequences'] == [6., .5, 0.]
    assert choice['value'] == 1.
    tied = [Fixed({'LEFT': [1., 0., 0.]}), Fixed({'DOWN': [1., 0., 0.]})]
    assert choose_gpi(tied, BOARD, {})['action'] == 'DOWN'


def test_saved_joint_heads_preserve_exact_sparse_values_and_metadata():
    result = model(); result.train_episode([BOARD], [4], 'LOST')
    saved = result.save(BUILD / 'synthetic_roundtrip.npz')
    with np.load(saved['path'], allow_pickle=False) as data:
        meta = json.loads(str(data['metadata']))
        restored = np.zeros(result.weights.size)
        restored[data['indices']] = data['values']
        np.testing.assert_array_equal(restored.reshape(result.weights.shape), result.weights)
        assert meta['schema'] == 'acfqp.policy_consequences.v126'
        assert meta['components'] == ['reward', 'failure', 'success']
        assert meta['updates'] == 1 and meta['head_updates'] == [1, 1, 1]
        assert saved['parameter_count'] == result.weights.size


def test_readonly_evaluation_makes_choices_without_parameter_changes():
    result = model(); result.update(BOARD, [2., .5, .5])
    before = result.weights.copy(); updates = result.updates
    result.weights.flags.writeable = False
    result.choose(BOARD, QUERY); result.vectors([BOARD, GOAL])
    with pytest.raises(RuntimeError, match='cannot update'):
        result.update(BOARD, [0., 1., 0.])
    assert result.updates == updates
    np.testing.assert_array_equal(result.weights, before)
