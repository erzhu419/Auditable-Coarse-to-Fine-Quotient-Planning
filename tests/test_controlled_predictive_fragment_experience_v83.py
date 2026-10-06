"""Source-trigger timing, paired option returns and whole-root censoring."""
from collections import Counter
from fractions import Fraction
import json
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import controlled_predictive_fragment_experience_v83 as experience
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
    print("V83_FRAGMENT_EXPERIENCE_DEVELOPMENT_WORK=" + json.dumps(dict(LEDGER), sort_keys=True))


class FakeController:
    calls = []

    def __init__(self, selector, query, rule, rng, mode="FRAGMENT", immediate=False, fixed_option=None):
        self.query, self.rng, self.mode, self.option = query, rng, mode, fixed_option
        self.events, self.work = [], Counter()
        self.fragment_actions, self.remaining_actions = 0, 0
        self.initiation_step, self.selected_option = None, None
        self.finished_fragment = False
        assert mode == "H2_ONLY" or immediate

    def choose(self, board, step):
        draws = [self.rng.random() for _ in range(4)]
        self.calls.append(dict(query=self.query, option=self.option, step=step, draws=draws))
        self.work["model_uniform_draws"] += 4
        self.work["controller_active_decisions"] += 1
        return self.option or "H2"


def root():
    return dict(board=[1] * 10 + [0] * 6, query="risk_goal", episode=3,
                step=10, source_seed=9_290_003)


def test_source_keeps_first_trigger_and_completes_whole_game(monkeypatch):
    FakeController.calls = []
    monkeypatch.setattr(experience, "FragmentController", FakeController)
    boards = [tuple([1] * (16 - empty) + [0] * empty) for empty in (14, 7, 6, 5)]

    def run_episode(seed, actor, max_steps):
        assert seed == 8_300_000 + 99 * 10_000 + 3
        for step, board in enumerate(boards):
            assert actor(board, step) == "H2"
        return dict(status="LOST", return_score=100, steps_count=4, steps=[],
                    work={"sampled_transitions": 4})

    monkeypatch.setattr(experience, "run_episode", run_episode)
    selected, raw, log = experience.collect_source(99, 3, "risk_goal", None)
    assert selected == dict(board=list(boards[2]), query="risk_goal", episode=3,
                            step=2, source_seed=9_290_003)
    assert len(FakeController.calls) == 4
    expected = random.Random(10_290_003)
    assert FakeController.calls[0]["draws"] == [expected.random() for _ in range(4)]
    assert log["ground_work"]["sampled_transitions"] == 4
    assert log["planning_counts"]["model_uniform_draws"] == 16
    assert raw["game"]["status"] == "LOST" and log["roots"] == 1


def test_source_without_trigger_retains_full_cost(monkeypatch):
    monkeypatch.setattr(experience, "FragmentController", FakeController)

    def run_episode(seed, actor, max_steps):
        actor(tuple([1] * 9 + [0] * 7), 0)
        return dict(status="CUTOFF", return_score=0, steps_count=1, steps=[],
                    work={"sampled_transitions": 1})

    monkeypatch.setattr(experience, "run_episode", run_episode)
    selected, raw, log = experience.collect_source(99, 3, "reward", None, max_steps=1)
    assert selected is None and log["roots"] == 0
    assert log["outcomes"] == {"CUTOFF": 1}
    assert raw["game"]["steps_count"] == log["ground_work"]["sampled_transitions"] == 1


def test_options_act_at_root_with_paired_streams_and_averaged_full_returns(monkeypatch):
    FakeController.calls = []
    monkeypatch.setattr(experience, "FragmentController", FakeController)
    trajectories = []

    def rollout(board, seed, actor, max_steps):
        before = len(FakeController.calls)
        option = actor(board, 0)
        actor(board, 1)
        replica = seed % 100
        first_score = 2048 * (replica + 1) if option == "SPACE_1" else 0
        later_score = 100 * (replica + 1)
        status = "WON" if option == "SPACE_1" and replica == 0 else "LOST"
        trajectories.append((seed, FakeController.calls[before:]))
        return dict(status=status, return_score=first_score + later_score,
            steps=[dict(score=first_score), dict(score=later_score)], steps_count=2,
            work={"sampled_transitions": 2})

    monkeypatch.setattr(experience, "rollout_from_board", rollout)
    rows, raw, log = experience.sample_root(root(), None, 99, replicas=2)
    assert len(rows) == 4 and len(raw) == 10
    selected = next(row for row in rows if row["option"] == "SPACE_1")
    assert selected == dict(board=root()["board"], query="risk_goal", episode=3,
                            option="SPACE_1", target=[1.5, -0.5, 0.5])
    assert log["pair_deltas"]["SPACE_1"] == [[1.0, -1.0, 1.0], [2.0, 0.0, 0.0]]
    for replica in range(2):
        seed = 8_310_000_000 + 99 * 10_000_000 + 100_000 + 300 + replica
        rng = random.Random(seed + 1_000_000_000_000)
        expected = [[rng.random() for _ in range(4)] for _ in range(2)]
        for value, calls in trajectories[replica * 5:replica * 5 + 5]:
            assert value == seed
            assert [call["draws"] for call in calls] == expected
            assert [call["step"] for call in calls] == [0, 1]
    assert log["ground_work"] == {"sampled_transitions": 20}
    assert log["model_uniform_draws"] == 80
    assert log["outcomes"] == {"LOST": 9, "WON": 1}


def test_one_cutoff_censors_all_root_labels_and_keeps_cost(monkeypatch):
    monkeypatch.setattr(experience, "FragmentController", FakeController)

    def rollout(board, seed, actor, max_steps):
        option = actor(board, 0)
        return dict(status="CUTOFF" if option == "SNAKE_4" and seed % 100 == 1 else "LOST",
                    return_score=100, steps_count=1, steps=[], work={"sampled_transitions": 1})

    monkeypatch.setattr(experience, "rollout_from_board", rollout)
    rows, raw, log = experience.sample_root(root(), None, 99, replicas=2)
    assert rows == [] and log["pair_deltas"] == {} and log["censored_root"]
    assert len(raw) == log["trajectories"] == log["ground_work"]["sampled_transitions"] == 10
    assert log["outcomes"] == {"LOST": 9, "CUTOFF": 1}


def test_real_options_consume_four_draws_on_terminal_first_action():
    rule = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")
    sample = root()
    sample["board"] = [10] * 16
    rows, raw, log = experience.sample_root(sample, rule, 99, replicas=1, max_steps=2)
    LEDGER.update(log["ground_work"])
    assert len(rows) == 4 and all(row["target"] == [0.0] * 3 for row in rows)
    assert log["outcomes"] == {"WON": 5}
    assert log["ground_work"]["sampled_transitions"] == 5
    assert log["model_uniform_draws"] == 20
    assert all(item["game"]["return_score"] == 16_384 for item in raw)
    assert all(item["controller"]["initiation_step"] == 0 for item in raw)
    assert all(item["planning_counts"]["model_uniform_draws"] == 4 for item in raw)
