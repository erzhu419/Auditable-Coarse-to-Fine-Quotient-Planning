"""Fixed paired streams, retained cutoffs, and actual fragment commitments."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random

import pytest

from acfqp.science import controlled_predictive_leaf_replay_v90 as module
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


ROOT = Path(__file__).resolve().parents[1]
LEDGER = Counter()
SEED = 110_990_000_000


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_leaf_replay_v90.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Short real paired suffixes plus synthetic terminal/cutoff outcomes; no campaign sampling.",
        main_campaign_calls=0, new_tree_fits=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def root():
    return dict(id="development-target", kind="target", life=99, query="reward",
                leaf=1, option="SNAKE_4", board=[1] * 10 + [0] * 6)


def rule():
    return LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")


def charge(log):
    LEDGER.update({"ground_" + key: value for key, value in log["ground_work"].items()})
    LEDGER.update({"planning_" + key: value for key, value in log["planning_counts"].items()})


def without_seconds(value):
    if isinstance(value, dict):
        return {key: without_seconds(item) for key, item in value.items() if key != "seconds"}
    if isinstance(value, list):
        return [without_seconds(item) for item in value]
    return value


def test_real_pairs_preserve_stream_prefix_and_execute_full_commitment():
    sample = root()
    before = deepcopy(sample)
    short, short_log = module.sample_pair_root(sample, rule(), SEED, replicas=1, max_steps=20)
    extended, log = module.sample_pair_root(sample, rule(), SEED, replicas=2, max_steps=20)
    charge(short_log)
    charge(log)
    assert sample == before
    assert log["ground_work"]["sampled_transitions"] == 80
    assert log["complete_pairs"] == 0 and log["outcomes"] == {"CUTOFF": 4}
    assert all(pair["target"] is None for pair in log["pairs"])
    assert without_seconds(short) == without_seconds(extended[:2])
    assert short_log["pairs"] == log["pairs"][:1]
    assert [row["option"] for row in extended] == ["H2", "SNAKE_4", "SNAKE_4", "H2"]
    assert all(log["wiring"].values())
    for row in extended:
        assert row["env_seed"] == SEED + row["replica"]
        assert row["model_seed"] == row["env_seed"] + 1_000_000_000_000
        expected = ["H2"] * 20 if row["option"] == "H2" else ["fragment"] * 4 + ["H2"] * 16
        assert row["action_paths"] == expected
        assert row["planning_counts"]["model_uniform_draws"] == 80
        assert row["planning_counts"].get("selector_decisions", 0) == 0


def test_real_terminal_shortening_retains_complete_paired_rfs():
    sample = dict(root(), board=[10] * 16)
    raw, log = module.sample_pair_root(sample, rule(), SEED + 100, replicas=1)
    charge(log)
    assert log["ground_work"]["sampled_transitions"] == 2
    assert log["complete_pairs"] == 1 and log["pairs"][0]["target"] == [0, 0, 0]
    assert log["outcomes"] == {"WON": 2} and all(log["wiring"].values())
    assert raw[1]["action_paths"] == ["fragment"]
    assert raw[1]["controller"]["fragment_actions"] == 1
    assert raw[1]["controller"]["remaining_actions"] == 3


def test_incomplete_pair_keeps_all_work_and_does_not_stop_later_replicas(monkeypatch):
    calls = []

    class Controller:
        def __init__(self, selector, query, rule, rng, immediate, fixed_option):
            assert selector is None and immediate
            self.option, self.rng = fixed_option, rng
            self.work, self.events = Counter(), []
            self.fragment_actions, self.remaining_actions = 0, 0
            self.initiation_step, self.selected_option = None, None
            self.finished_fragment = False

        def choose(self, board, step):
            if self.selected_option is None:
                self.selected_option, self.initiation_step = self.option, step
                self.events.append(dict(step=step, option=self.option))
                self.remaining_actions = 0 if self.option == "H2" else 4
            if self.remaining_actions:
                self.fragment_actions += 1
                self.remaining_actions -= 1
            self.finished_fragment = self.remaining_actions == 0
            draws = [self.rng.random() for _ in range(4)]
            self.work["model_uniform_draws"] += 4
            calls[-1]["draws"].append(draws)
            return "left"

    def rollout(board, seed, actor, max_steps):
        # Closures expose the fixed controller only through this returned action;
        # arm identity follows the sampler's specified alternating order.
        replica = seed - SEED
        position = len(calls) % 2
        candidate = position == (1 if replica % 2 == 0 else 0)
        calls.append(dict(seed=seed, candidate=candidate, draws=[]))
        length = 2 if candidate else 1
        for step in range(length):
            assert actor(board, step) == "left"
        status = "CUTOFF" if candidate and replica == 1 else "WON" if candidate else "LOST"
        return dict(status=status, return_score=2048 * (replica + 1) if candidate else 0,
                    steps_count=length, steps=[], work={"sampled_transitions": length})

    monkeypatch.setattr(module, "FragmentController", Controller)
    monkeypatch.setattr(module, "rollout_from_board", rollout)
    raw, log = module.sample_pair_root(root(), None, SEED, replicas=3, max_steps=2)
    assert len(raw) == log["trajectories"] == 6
    assert log["ground_work"]["sampled_transitions"] == 9
    assert log["complete_pairs"] == 2
    assert [pair["target"] for pair in log["pairs"]] == [[1, -1, 1], None, [3, -1, 1]]
    assert all(log["wiring"].values())
    for replica in range(3):
        rng = random.Random(SEED + replica + 1_000_000_000_000)
        draws = [[rng.random() for _ in range(4)] for _ in range(2)]
        for call in calls[2 * replica:2 * replica + 2]:
            assert call["draws"] == draws[:len(call["draws"])]
