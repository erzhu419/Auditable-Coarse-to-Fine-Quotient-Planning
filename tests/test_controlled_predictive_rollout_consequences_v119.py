"""Detect backend, policy tie, target horizon and common-draw mismatches."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_lifelong_experience_v77 import targets
from acfqp.science.controlled_predictive_lifelong_planner_v77 import POLICIES, _spawn, policy_action
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.controlled_predictive_rollout_consequences_v119 import RolloutKnowledge

ROOT = Path(__file__).resolve().parents[1]
WORK, REFERENCE_WORK, SETUP_WORK = Counter(), Counter(), Counter()
SETUP_SECONDS = []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_rollout_consequences_v119.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed-before,
        development_work=dict(WORK), reference_model_work=dict(REFERENCE_WORK),
        setup_work=dict(SETUP_WORK), setup_seconds=sum(SETUP_SECONDS),
        newly_sampled_environment_transitions=0, tree_fits=0, optimizer_steps=0,
        scope='Synthetic boards and supplied learned rules; compiled and Python model rollouts only.'))
    path.write_text(json.dumps(log, indent=2)+'\n')


def rule(goal=6, location='uniform', distribution=None, reward='output_value'):
    return LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', reward),
        distribution or ((1, Fraction(7, 10)), (2, Fraction(3, 10))), location, goal)


def provider(dynamics, replicas=4, seed=119001):
    result = RolloutKnowledge(dynamics, replicas, seed,
        ROOT / 'reports/controlled_predictive_rollout_consequences_v119_build')
    SETUP_WORK.update(result.setup_counts)
    SETUP_SECONDS.append(result.setup_seconds)
    return result


def prediction(model, boards, horizon):
    before = model.counts.copy()
    result = model.predict_many(boards, horizon)
    WORK.update(model.counts-before)
    return result


def reference(boards, horizon, dynamics, draws):
    result = np.zeros((len(boards), 3, 3), dtype=float)
    for index, initial in enumerate(boards):
        for policy_index, policy in enumerate(POLICIES):
            for trajectory in draws:
                board = tuple(initial)
                for step, pair in enumerate(trajectory):
                    board = _spawn(board, pair, dynamics, REFERENCE_WORK)
                    status, _ = dynamics.classify(board, REFERENCE_WORK)
                    if status != 'ACTIVE':
                        result[index, policy_index, 1 if status == 'LOST' else 2] += 1
                        break
                    if step == horizon:
                        break
                    action = policy_action(board, policy, dynamics, REFERENCE_WORK)
                    board, score, changed = dynamics.swipe(board, action, REFERENCE_WORK)
                    assert changed
                    result[index, policy_index, 0] += score/2048
                    REFERENCE_WORK['rollout_actions'] += 1
    return result/len(draws)


def test_compiled_rollouts_match_reference_policies_and_supplied_program():
    boards = [
        (1, 0, 0, 0) + (0,)*12,
        (1, 1, 2, 0, 2, 3, 1, 0, 0, 2, 2, 0, 3, 0, 1, 0),
        (1, 2, 3, 4, 2, 3, 4, 1, 3, 4, 1, 2, 4, 1, 1, 0),
        (4, 4, 3, 2, 1, 2, 1, 2, 2, 1, 2, 1, 0, 0, 1, 0),
    ]
    # GREEDY and SPACE ties on the sparse board must preserve sorted action names.
    assert policy_action(boards[0], 'GREEDY', rule(), REFERENCE_WORK) == 'DOWN'
    assert policy_action(boards[0], 'SPACE', rule(), REFERENCE_WORK) == 'DOWN'
    for dynamics in (rule(), rule(location='first'), rule(location='last', reward='count')):
        model = provider(dynamics)
        for horizon in (0, 1, 7, 30):
            expected = reference(boards, horizon, dynamics, model.common_draws(horizon))
            np.testing.assert_array_equal(prediction(model, boards, horizon), expected)


def test_initial_spawn_and_final_spawn_terminals_match_observed_targets():
    dynamics = rule(goal=3, distribution=((1, Fraction(1)),), location='first')
    boards = [(1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 0),
              (2, 2, 0, 0) + (0,)*12,
              (3, 0, 0, 0) + (0,)*12]
    zero = provider(dynamics, replicas=1)
    predictions = prediction(zero, boards, 0)
    np.testing.assert_array_equal(predictions[0], [[0, 1, 0]]*3)
    np.testing.assert_array_equal(predictions[1], [[0, 0, 0]]*3)
    np.testing.assert_array_equal(predictions[2], [[0, 0, 1]]*3)
    model = provider(dynamics, replicas=1)
    draws = model.common_draws(1)
    predicted = prediction(model, [boards[1]], 1)
    for policy_index, policy in enumerate(POLICIES):
        initial = boards[1]
        spawned = _spawn(initial, draws[0, 0], dynamics, REFERENCE_WORK)
        action = policy_action(spawned, policy, dynamics, REFERENCE_WORK)
        moved, score, _ = dynamics.swipe(spawned, action, REFERENCE_WORK)
        final = _spawn(moved, draws[0, 1], dynamics, REFERENCE_WORK)
        status, _ = dynamics.classify(final, REFERENCE_WORK)
        episode = dict(steps=[dict(afterstate=initial, score=999*2048, status='ACTIVE'),
                              dict(afterstate=moved, score=score, status=status)])
        rows = targets(episode, policy, 0, stride=1, horizons=(1,))
        expected = next(row['target'] for row in rows if row['anchor_step'] == 0)
        np.testing.assert_array_equal(predicted[0, policy_index], expected)
    assert model.counts['model_spawn_samples'] == 6
    assert model.counts['rollout_actions'] == 3
    assert np.all(predicted[0, :, 0] < 1)  # Excludes the anchor's score.


def test_budget_prefix_and_call_seeds_are_independent_of_rollout_consumption():
    small, large = provider(rule(), 4, 99119), provider(rule(), 16, 99119)
    board = [(1, 1, 0, 0)+(0,)*12]
    for horizon in (7, 3):
        np.testing.assert_array_equal(small.common_draws(horizon), large.common_draws(horizon)[:4])
        first = prediction(small, board, horizon)
        prediction(large, board, horizon)
        # The small estimate is the same four rollout prefixes under the large stream.
        reference_large = provider(rule(), 16, 99119)
        reference_large.call_index = small.call_index-1
        expected = reference(board, horizon, rule(), reference_large.common_draws(horizon)[:4])
        np.testing.assert_array_equal(first, expected)
    assert small.counts['policy_vector_rollouts'] == 24
    assert large.counts['policy_vector_rollouts'] == 96
    assert small.counts['model_uniform_draws'] == 4*(8+4)*2
    assert large.counts['model_uniform_draws'] == 16*(8+4)*2


def test_common_draws_share_leaf_predictions_and_empty_batches():
    model = provider(rule(), replicas=4)
    board = (1, 2, 1, 0)+(0,)*12
    values = prediction(model, [board, board], 7)
    np.testing.assert_array_equal(values[0], values[1])
    assert model.counts['policy_prediction_rows'] == 6
    assert prediction(model, [], 0).shape == (0, 3, 3)
