"""Actual-transition budgets, complete paired blocks and weighted root means."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random

import pytest

from acfqp.science import controlled_predictive_budgeted_fragments_v86 as module
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


ROOT = Path(__file__).resolve().parents[1]
LEDGER = Counter()
BASE_SEED = 86990000
LENGTHS = dict(zip(module.OPTIONS, (2, 3, 1, 4, 2)))


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_budgeted_fragments_v86.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Mock variable-length blocks plus one five-transition terminal fixture; no campaign sampling.",
        main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


class FakeController:
    calls = []

    def __init__(self, selector, query, rule, rng, mode="FRAGMENT", immediate=False, fixed_option=None):
        self.rng, self.option = rng, fixed_option or "H2"
        self.work, self.events = Counter(), []
        self.fragment_actions, self.remaining_actions = 0, 0
        self.initiation_step, self.selected_option = None, None
        self.finished_fragment = False

    def choose(self, board, step):
        draws = [self.rng.random() for _ in range(4)]
        self.calls.append(dict(option=self.option, step=step, draws=draws))
        self.work["model_uniform_draws"] += 4
        return self.option


def root():
    return dict(board=[1] * 10 + [0] * 6, query="risk_goal", episode=3, step=20, source_seed=BASE_SEED)


@pytest.fixture
def fake_rollout(monkeypatch):
    calls = []
    FakeController.calls = []
    monkeypatch.setattr(module, "FragmentController", FakeController)

    def rollout(board, seed, actor, max_steps):
        controller = actor.__self__
        option, replica = controller.option, seed - BASE_SEED
        length = min(LENGTHS[option], max_steps)
        before = len(FakeController.calls)
        for step in range(length):
            assert actor(board, step) == option
        status = "CUTOFF" if length < LENGTHS[option] else (
            "WON" if option == "SPACE_1" and replica == 0 else "LOST")
        score = 100 * (replica + 1) + (2048 * (replica + 1) if option == "SPACE_1" else 0)
        calls.append(dict(seed=seed, option=option, cap=max_steps, length=length,
                          draws=FakeController.calls[before:]))
        return dict(status=status, return_score=score, steps_count=length, steps=[],
                    work={"sampled_transitions": length})

    monkeypatch.setattr(module, "rollout_from_board", rollout)
    return calls


def test_variable_lengths_use_actual_remaining_and_retain_incomplete_block(fake_rollout):
    rows, raw, log = module.sample_root(root(), None, BASE_SEED, remaining=15, replicas=2)
    assert [call["cap"] for call in fake_rollout] == [15, 13, 10, 9, 5, 3, 1]
    assert sum(call["length"] for call in fake_rollout) == 15
    assert len(raw) == log["trajectories"] == 7
    assert raw[-1]["game"]["status"] == "CUTOFF"
    assert log["ground_work"]["sampled_transitions"] == 15 and log["unused_budget"] == 0
    assert log["budget_exhausted"] and not log["complete_block"] and log["censored_root"]
    assert rows == [] and log["pair_deltas"] == {}


def test_exact_last_terminal_action_can_complete_a_block_at_zero_budget(fake_rollout):
    rows, raw, log = module.sample_root(root(), None, BASE_SEED, remaining=12, replicas=1)
    assert len(rows) == 4 and len(raw) == len(fake_rollout) == 5
    assert log["complete_block"] and log["budget_exhausted"] and log["unused_budget"] == 0
    assert log["ground_work"]["sampled_transitions"] == 12
    assert not log["censored_root"]


def test_terminal_blocks_pair_seeds_and_model_draws_and_use_whole_rfs_means(fake_rollout):
    rows, raw, log = module.sample_root(root(), None, BASE_SEED, remaining=30, replicas=2)
    assert log["complete_block"] and len(raw) == 10 and log["unused_budget"] == 6
    assert log["ground_work"]["sampled_transitions"] == 24 and log["model_uniform_draws"] == 96
    selected = next(row for row in rows if row["option"] == "SPACE_1")
    assert selected["target"] == [1.5, -0.5, 0.5]
    assert log["pair_deltas"]["SPACE_1"] == [[1, -1, 1], [2, 0, 0]]
    for replica in range(2):
        rng = random.Random(BASE_SEED + replica + 1_000_000_000_000)
        expected = [[rng.random() for _ in range(4)] for _ in range(4)]
        for item in fake_rollout[5 * replica:5 * replica + 5]:
            assert item["seed"] == BASE_SEED + replica
            assert [call["draws"] for call in item["draws"]] == expected[:item["length"]]


def test_per_trajectory_cap_excludes_labels_even_with_budget_left(fake_rollout):
    rows, raw, log = module.sample_root(root(), None, BASE_SEED, remaining=100, replicas=1, max_steps=3)
    assert len(raw) == 5 and log["unused_budget"] == 89
    assert log["outcomes"]["CUTOFF"] == 1
    assert not log["complete_block"] and not log["budget_exhausted"]
    assert rows == [] and log["pair_deltas"] == {}


def test_zero_budget_never_starts_source_or_branch_environment(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("zero budget must not start a trajectory")
    monkeypatch.setattr(module, "run_episode", forbidden)
    monkeypatch.setattr(module, "rollout_from_board", forbidden)
    selected, raw, log = module.collect_source(99, 3, "reward", None, BASE_SEED, remaining=0)
    assert selected is raw is None and log["games"] == 0 and log["unused_budget"] == 0
    rows, raw, log = module.sample_root(root(), None, BASE_SEED, remaining=0)
    assert rows == raw == [] and log["trajectories"] == 0 and log["unused_budget"] == 0
    assert not log["complete_block"]


def test_source_capture_uses_first_trigger_and_charges_cap_before_branching(monkeypatch):
    monkeypatch.setattr(module, "FragmentController", FakeController)
    FakeController.calls = []
    boards = [tuple([1] * (16 - empty) + [0] * empty) for empty in (14, 7, 6, 5, 4)]

    def source(seed, actor, max_steps):
        assert seed == BASE_SEED and max_steps == 3
        for step, board in enumerate(boards[:max_steps]):
            actor(board, step)
        return dict(status="CUTOFF", return_score=10, steps_count=max_steps, steps=[],
                    work={"sampled_transitions": max_steps})

    monkeypatch.setattr(module, "run_episode", source)
    selected, raw, log = module.collect_source(99, 3, "reward", None, BASE_SEED, remaining=3)
    assert selected["board"] == list(boards[2]) and selected["step"] == 2
    assert raw["game"]["status"] == "CUTOFF" and log["unused_budget"] == 0
    assert log["ground_work"]["sampled_transitions"] == 3
    assert log["planning_counts"]["model_uniform_draws"] == 12
    rng = random.Random(BASE_SEED + 1_000_000)
    assert FakeController.calls[0]["draws"] == [rng.random() for _ in range(4)]


def test_weighted_means_preserve_rfs_root_identity_and_inputs():
    original = [dict(board=root()["board"], query="risk_goal", episode=3, option=option,
                     target=[i, -i / 8, i / 8]) for i, option in enumerate(module.OPTIONS[1:])]
    extra = [dict(row, target=[row["target"][0] + 3, 0.5, -0.5]) for row in reversed(original)]
    before = deepcopy((original, extra))
    combined = module.combine_rows(original, extra, original_replicas=16, extra_replicas=8)
    assert (original, extra) == before
    assert len(combined) == 4
    for i, row in enumerate(combined):
        assert row["option"] == original[i]["option"] and row["episode"] == 3
        assert row["board"] == root()["board"] and row["query"] == "risk_goal"
        assert row["target"] == pytest.approx([i + 1, (-2 * i + 4) / 24, (2 * i - 4) / 24])


def test_real_terminal_block_uses_exactly_five_transitions_and_aligned_draws():
    rule = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")
    sample = dict(root(), board=[10] * 16)
    rows, raw, log = module.sample_root(sample, rule, BASE_SEED + 100, remaining=5, replicas=1)
    LEDGER.update({"ground_" + key: value for key, value in log["ground_work"].items()})
    LEDGER.update({"planning_" + key: value for key, value in log["planning_counts"].items()})
    assert log["ground_work"]["sampled_transitions"] == 5 and log["unused_budget"] == 0
    assert log["complete_block"] and log["outcomes"] == {"WON": 5}
    assert len(rows) == 4 and all(row["target"] == [0, 0, 0] for row in rows)
    assert all(item["game"]["return_score"] == 16_384 for item in raw)
    assert log["model_uniform_draws"] == 20
    assert all(item["planning_counts"]["model_uniform_draws"] == 4 for item in raw)
