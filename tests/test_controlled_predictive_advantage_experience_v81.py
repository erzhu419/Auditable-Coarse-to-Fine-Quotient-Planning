"""Small pairing, continuation, complete-return and censoring checks."""
from collections import Counter
from fractions import Fraction
import json
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import controlled_predictive_advantage_experience_v81 as experience
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


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
    print("V81_ADVANTAGE_EXPERIENCE_DEVELOPMENT_WORK=" + json.dumps(dict(LEDGER), sort_keys=True))


class TinyRule:
    def classify(self, board, work):
        work["learned_terminal_checks"] += 1
        return "ACTIVE", tuple((action, board, 0) for action in ("RIGHT", "LEFT"))


def root(query="risk_goal"):
    return dict(board=[1, 1] + [0] * 14, reference_action="LEFT",
                query=query, episode=7, step=24)


def test_paired_streams_force_once_and_keep_same_parent(monkeypatch):
    calls, trajectories = [], []

    class Parent:
        def choose(self, board, query, rule, rng, work):
            calls.append((board, query, rng.random()))
            work["model_uniform_draws"] += 1
            work["parent_calls"] += 1
            return dict(action="UP")

    parent = Parent()

    def rollout(board, seed, actor, max_steps):
        before = len(calls)
        first = actor(board, 0)
        assert len(calls) == before
        assert actor(board, 1) == actor(board, 2) == "UP"
        trajectories.append((seed, first, list(calls[before:])))
        return dict(status="LOST", return_score=0, work={}, steps_count=3, steps=[])

    monkeypatch.setattr(experience, "rollout_from_board", rollout)
    _, raw, log = experience.sample_root(root(), parent, TinyRule(), 2, 3, 4)
    assert len(raw) == 4
    for replica in range(2):
        seed = 8_110_000_000 + 2 * 10_000_000 + 3 * 1_000_000 + 100_000 + 4 * 100 + replica
        left, right = trajectories[replica * 2:replica * 2 + 2]
        assert left[0] == right[0] == seed
        assert left[1] == "LEFT" and right[1] == "RIGHT"
        expected = random.Random(seed + 1_000_000_000_000)
        expected_draws = [expected.random(), expected.random()]
        assert left[2] == right[2]
        assert [item[2] for item in left[2]] == expected_draws
        assert all(item[1] == "risk_goal" for item in left[2])
    assert log["model_rng_streams"] == 4
    assert log["model_uniform_draws"] == log["continuation_work"]["parent_calls"] == 8
    assert log["known_model_counts"] == {"learned_terminal_checks": 1}


def test_complete_reward_and_terminal_vector_paired_before_averaging(monkeypatch):
    def rollout(board, seed, actor, max_steps):
        action = actor(board, 0)
        replica = seed % 100
        # Each candidate differs only in the forced first-action reward.
        # Status variation also tests joint R/F/S pairing within a replica.
        first_score = 2048 if action == "RIGHT" else 0
        later_score = 100 if replica == 0 else 1000
        status = "WON" if replica == 0 and action == "RIGHT" else "LOST"
        return dict(status=status, return_score=first_score + later_score,
                    steps=[dict(score=first_score), dict(score=later_score)],
                    steps_count=2, work={"sampled_transitions": 2})

    monkeypatch.setattr(experience, "rollout_from_board", rollout)
    rows, raw, log = experience.sample_root(root("reward"), None, TinyRule(), 0, 1, 0)
    assert len(rows) == 1
    assert rows[0] == dict(board=root()["board"], query="reward", reference_action="LEFT",
        action="RIGHT", target=[1.0, -0.5, 0.5], episode=7, iteration=1,
        step=24, root_index=0, replicas=2)
    assert log["pair_deltas"] == {"RIGHT": [[1.0, -1.0, 1.0], [1.0, 0.0, 0.0]]}
    assert len(raw) == 4 and log["ground_work"]["sampled_transitions"] == 8
    assert log["outcomes"] == {"LOST": 3, "WON": 1}


def test_one_cutoff_censors_entire_root_but_retains_all_work(monkeypatch):
    def rollout(board, seed, actor, max_steps):
        action = actor(board, 0)
        return dict(status="CUTOFF" if seed % 100 == 1 and action == "RIGHT" else "LOST",
            return_score=10, work={"sampled_transitions": 3}, steps_count=3, steps=[])

    monkeypatch.setattr(experience, "rollout_from_board", rollout)
    rows, raw, log = experience.sample_root(root(), None, TinyRule(), 0, 1, 0)
    assert rows == [] and log["pair_deltas"] == {}
    assert log["censored_root"] and len(raw) == 4
    assert log["rows"] == 0 and log["trajectories"] == 4
    assert log["outcomes"] == {"LOST": 3, "CUTOFF": 1}
    assert log["ground_work"]["sampled_transitions"] == 12


def test_real_terminal_first_moves_never_call_continuation_parent():
    class Parent:
        def choose(self, *args, **kwargs):
            raise AssertionError("terminal first action must not invoke parent")

    rule = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")
    start = dict(board=[10] * 16, reference_action="LEFT", query="reward", episode=0, step=0)
    rows, raw, log = experience.sample_root(start, Parent(), rule, 99, 1, 0, max_steps=2)
    LEDGER.update(log["ground_work"])
    assert len(rows) == 3 and len(raw) == 8
    assert all(row["target"] == [0.0, 0.0, 0.0] for row in rows)
    assert log["outcomes"] == {"WON": 8}
    assert log["ground_work"]["sampled_transitions"] == 8
    assert log["ground_work"]["environment_random_draws"] == 16
    assert log["model_uniform_draws"] == 0 and log["continuation_work"] == {}
    assert all(item["game"]["return_score"] == 16_384 for item in raw)
