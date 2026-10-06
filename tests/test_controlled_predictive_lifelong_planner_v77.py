"""Small policy-composition and horizon fixtures, with no campaign data."""
from collections import Counter
from fractions import Fraction
import importlib.util
from pathlib import Path
import random
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def module(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'src/acfqp/science' / filename)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


PLANNER = module('controlled_predictive_lifelong_planner_v77.py', 'v77_planner_test')
DYNAMICS = module('controlled_predictive_relational_dynamics_v69.py', 'v77_dynamics_test')


def board(tag):
    return (tag,) + (0,) * 15


class TinyRule:
    goal_rank = 11
    spawn_location = 'uniform'
    spawn_distribution = ((1, Fraction(1)),)

    def classify(self, state, work):
        if state[0] == 1:
            return 'ACTIVE', (('LEFT', board(2), 0), ('RIGHT', board(3), 0))
        if state[0] in (2, 3):
            return 'ACTIVE', (('LEFT', board(state[0] + 2), 0),)
        return 'LOST', ()


class Knowledge:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def predict_many(self, boards, horizon):
        self.calls.append((tuple(boards), horizon))
        return [self.rows[item[0]] for item in boards]


def test_complete_policy_vectors_and_query_recombination():
    knowledge = Knowledge({2: [(2, 1, 0), (0, 0, 0), (0, 0, 0)],
                           3: [(0.5, 0, 0)] * 3})
    result = PLANNER.choose(board(1), {'failure_penalty': 3}, knowledge,
                            TinyRule(), random.Random(7), depth=1)
    assert result['action'] == 'RIGHT'
    assert result['action_values']['LEFT']['metrics'] == {'reward': 0, 'failure': 0, 'success': 0}
    assert result['policy'] == 'GREEDY'
    assert result['counts']['policy_vectors'] == 6
    assert len(knowledge.calls) == 1 and knowledge.calls[0][1] == 31
    no_risk = PLANNER.choose(board(1), {'failure_penalty': 0}, knowledge,
                             TinyRule(), random.Random(7), depth=1)
    assert no_risk['action'] == 'LEFT'
    assert no_risk['metrics']['failure'] == 1


def test_depth_two_uses_batched_leaf_values_and_shared_spawn_draws():
    knowledge = Knowledge({2: [(5, 0, 0)] * 3, 3: [(0, 0, 0)] * 3,
                           4: [(0, 0, 0)] * 3, 5: [(1, 0, 0)] * 3})
    query = {'reward_weight': 1}
    direct_rng, plan_rng = random.Random(13), random.Random(13)
    direct = PLANNER.choose(board(1), query, knowledge, TinyRule(), direct_rng, depth=1)
    plan = PLANNER.choose(board(1), query, knowledge, TinyRule(), plan_rng, depth=2)
    assert direct['action'] == 'LEFT' and plan['action'] == 'RIGHT'
    assert direct_rng.getstate() == plan_rng.getstate()
    assert len(knowledge.calls) == 2 and knowledge.calls[1][1] == 30
    assert plan['counts']['predicted_afterstates'] == 4
    assert plan['counts']['model_spawn_samples'] == 4
    for left, right in zip(plan['action_values']['LEFT']['branches'],
                           plan['action_values']['RIGHT']['branches']):
        assert left['board'][1:] == right['board'][1:]
        assert left['policy'] == right['policy'] == 'GREEDY'


def test_h2_cutoff_includes_second_spawn_failure_and_terminal_short_circuit():
    rule = DYNAMICS.LearnedDynamics(
        DYNAMICS.RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform')
    state = (1, 1, 3, 3, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6)
    result = PLANNER.choose(state, {'failure_penalty': 1}, None, rule, random.Random(4))
    saw_failure = False
    for candidate in result['action_values'].values():
        for branch in candidate['branches']:
            if branch['action'] is None:
                continue
            moved, score, changed = rule.swipe(branch['board'], branch['action'])
            assert changed
            expected_failure = expected_success = 0.0
            for probability, child, _ in rule.successors_from_afterstate(moved, score):
                status, _ = rule.classify(child)
                expected_failure += float(probability) * (status == 'LOST')
                expected_success += float(probability) * (status == 'WON')
            assert branch['metrics']['reward'] == score / 2048
            assert branch['metrics']['failure'] == pytest.approx(expected_failure)
            assert branch['metrics']['success'] == pytest.approx(expected_success)
            saw_failure |= expected_failure > 0
    assert saw_failure and result['counts']['h2_cutoff_contracts'] > 0
    rng = random.Random(9)
    before = rng.getstate()
    work = Counter()
    won = PLANNER.choose(board(11), {}, None, rule, rng, work=work)
    assert won['action'] is None and won['metrics']['success'] == 1
    assert rng.getstate() == before and work['model_uniform_draws'] == 0
    for policy in PLANNER.POLICIES:
        assert PLANNER.policy_action(board(11), policy, rule) is None
