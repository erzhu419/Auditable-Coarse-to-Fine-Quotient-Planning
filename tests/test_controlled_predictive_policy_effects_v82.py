"""V82 routing, random-stream coupling and full-return accounting checks."""
from collections import Counter
from fractions import Fraction
import json
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import controlled_predictive_policy_effects_v82 as effects
from acfqp.science.controlled_predictive_relational_dynamics_v69 import (
    LearnedDynamics, RewriteProgram,
)


LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def count_development_ground():
    patch = pytest.MonkeyPatch()
    for name in ("swipe_board_v1", "state_from_board_v1", "step_v1"):
        original = getattr(ground, name)

        def counted(*args, _function=original, _name=name, **kwargs):
            LEDGER[_name] += 1
            return _function(*args, **kwargs)

        patch.setattr(ground, name, counted)
    yield
    patch.undo()
    print("V82_POLICY_EFFECTS_DEVELOPMENT_WORK=" + json.dumps(dict(LEDGER), sort_keys=True))


def root(selected="RIGHT", query="risk_goal"):
    return dict(board=[1, 1] + [0] * 14, query=query, episode=4, step=24,
                root_index=7, reference_action="LEFT", selected_action=selected,
                predicted_advantage=[1.0, 0.0, 0.0])


def test_forced_root_streams_and_continuation_routing(monkeypatch):
    calls, trajectories = [], []

    class Policy:
        def __init__(self, iteration, action):
            self.iteration, self.action = iteration, action

        def choose(self, board, query, rule, rng, work):
            calls.append((self.iteration, query, rng.random()))
            work["model_uniform_draws"] += 1
            work["policy_calls"] += 1
            return dict(action=self.action)

    def rollout(board, seed, actor, max_steps):
        before = len(calls)
        first = actor(board, 0)
        assert len(calls) == before
        later = [actor(board, i) for i in (1, 2)]
        trajectories.append((seed, first, later, calls[before:]))
        return dict(return_score=2048, status="LOST", steps_count=3,
                    final_board=list(board), steps=[], work={"sampled_transitions": 3}, seconds=0.0)

    monkeypatch.setattr(effects, "rollout_from_board", rollout)
    games, raw, log = effects.sample_triplet(root(), Policy(0, "UP"), Policy(1, "DOWN"),
                                           None, 99, 3)
    seed = 8_210_000_000 + 99 * 10_000_000 + 100_000 + 700 + 3
    expected = random.Random(seed + 1_000_000_000_000)
    draws = [expected.random(), expected.random()]
    assert [item[1] for item in trajectories] == ["LEFT", "RIGHT", "RIGHT"]
    assert [item[2] for item in trajectories] == [["UP", "UP"], ["UP", "UP"], ["DOWN", "DOWN"]]
    for index, trajectory in enumerate(trajectories):
        assert trajectory[0] == seed
        assert [call[2] for call in trajectory[3]] == draws
        assert all(call[:2] == (int(index == 2), "risk_goal") for call in trajectory[3])
    assert [games[arm]["continuation_iteration"] for arm in effects.ARMS] == [0, 0, 1]
    assert all(game["utility"] == -3 for game in games.values())
    assert [item["method"] for item in raw] == list(effects.ARMS)
    assert log["ground_work"] == {"sampled_transitions": 9}
    assert log["planning_counts"] == {"model_uniform_draws": 6, "policy_calls": 6}
    assert log["model_uniform_draws"] == 6 and log["model_rng_streams"] == 3


def test_terminal_reward_includes_forced_action_without_policy_call():
    class NoCall:
        iteration = 0

        def choose(self, *args, **kwargs):
            raise AssertionError("terminal first action must not invoke a policy")

    sample = root(query="reward")
    sample["board"] = [10] * 16
    games, raw, log = effects.sample_triplet(sample, NoCall(), NoCall(), None,
                                           99, 4, max_steps=2)
    LEDGER.update(log["ground_work"])
    assert log["outcomes"] == {"WON": 3}
    assert log["ground_work"]["sampled_transitions"] == 3
    assert log["ground_work"]["environment_random_draws"] == 6
    assert log["model_uniform_draws"] == 0
    assert all(game["score"] == 16_384 and game["utility"] == 8 for game in games.values())
    assert raw[1]["game"]["steps"][0] == raw[2]["game"]["steps"][0]


def test_no_override_parent_and_first_only_match_complete_trajectory():
    class LegalPolicy:
        def __init__(self, iteration):
            self.iteration = iteration

        def choose(self, board, query, rule, rng, work):
            _, moves = rule.classify(board, work)
            work["model_uniform_draws"] += 1
            return dict(action=moves[int(rng.random() * len(moves))][0])

    rule = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")
    games, raw, log = effects.sample_triplet(root(selected="LEFT"),
        LegalPolicy(0), LegalPolicy(1), rule, 99, 5, max_steps=3)
    LEDGER.update(log["ground_work"])
    assert raw[0]["game"]["steps"] == raw[1]["game"]["steps"]
    assert raw[1]["game"]["steps"][0] == raw[2]["game"]["steps"][0]
    assert games["PARENT"]["score"] == games["FIRST_ONLY"]["score"]
    assert log["outcomes"] == {"CUTOFF": 3} and log["censored_triplet"]
    assert log["ground_work"]["sampled_transitions"] == 9
    assert log["ground_work"]["environment_random_draws"] == 18
    assert log["model_uniform_draws"] == 6
