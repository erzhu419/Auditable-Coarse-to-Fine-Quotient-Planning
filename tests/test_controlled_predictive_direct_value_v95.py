"""Model-only candidate paths, terminal absorption, and execution RNG isolation."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random

import pytest

from acfqp.science import controlled_predictive_direct_value_v95 as module
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


ROOT = Path(__file__).resolve().parents[1]
BOARD = [1] * 10 + [0] * 6
SEED = 395_990_000_000
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_direct_value_v95.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Supplied-model prefix simulation and synthetic value predictions; no environment kernel calls.",
        ground_sampled_transitions=0, tree_fits=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def rule(deterministic=False):
    distribution = ((1, Fraction(1)),) if deterministic else ((1, Fraction(9, 10)), (2, Fraction(1, 10)))
    return LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"), distribution, "uniform")


class Value:
    def __init__(self, scale=1, checkpoint=12):
        self.scale, self.checkpoint, self.calls = scale, checkpoint, []

    def predict(self, board, query, work=None):
        self.calls.append((tuple(board), query))
        if work is not None:
            work["synthetic_value_predictions"] += 1
        return [self.scale * sum(board) / 100, .8, .2]


def charge(selector):
    for name in ("model_work", "planning_counts", "value_counts"):
        LEDGER.update({name + "_" + key: value for key, value in selector.last_log[name].items()})


def test_prefix_streams_are_identical_across_value_models_and_saved_checkpoints(monkeypatch):
    from acfqp.domains import standard_2048 as ground
    def forbidden(*args, **kwargs):
        raise AssertionError("direct selection must not invoke the actual environment kernel")
    monkeypatch.setattr(ground, "swipe_board_v1", forbidden)
    selectors = [module.DirectSelector(Value(scale, checkpoint), rule(), SEED, replicas=1)
                 for scale, checkpoint in ((1, 12), (5, 12), (3, 6))]
    source = deepcopy(BOARD)
    histories = []
    for selector in selectors:
        work = Counter(model_uniform_draws=99)
        selection = selector.select(BOARD, "reward", work=work)
        charge(selector)
        assert selector.checkpoint in (6, 12) and len(selector.last_prefixes) == 5
        assert all(selector.last_log["wiring"].values())
        assert selector.last_log["outcomes"] == {"ACTIVE": 5}
        assert work["model_uniform_draws"] == 99
        assert work["candidate_model_uniform_draws"] == 80
        assert work["candidate_spawn_uniform_draws"] == 40
        assert work["candidate_synthetic_transitions"] == 20
        assert selection["predictions"]["H2"] == dict(target=[0, 0, 0], value=0)
        histories.append([{key: value for key, value in prefix.items() if key not in ("tail", "completed")}
                          for prefix in selector.last_prefixes])
    assert histories[0] == histories[1] == histories[2]
    assert BOARD == source


def test_winning_swipe_spawns_before_terminal_classification_and_never_bootstraps():
    value = Value()
    selector = module.DirectSelector(value, rule(), SEED + 100, replicas=1)
    selector.select([10] * 16, "risk_goal")
    charge(selector)
    assert value.calls == []
    assert selector.last_log["outcomes"] == {"WON": 5}
    assert selector.last_log["model_work"]["synthetic_transitions"] == 5
    for prefix in selector.last_prefixes:
        assert prefix["steps_count"] == 1 and len(prefix["controller"]["events"]) == 1
        assert prefix["steps"][0]["afterstate"] != prefix["final_board"]
        assert sum(rank != 0 for rank in prefix["final_board"]) == sum(
            rank != 0 for rank in prefix["steps"][0]["afterstate"]) + 1
        assert prefix["tail"] == [0, 0, 0] and prefix["direct"][1:] == [0, 1]
        assert prefix["completed"] == prefix["direct"]


def test_lost_prefix_absorbs_before_remaining_fragment_actions():
    board = [1, 1, 4, 5, 3, 2, 3, 2, 1, 3, 2, 3, 3, 2, 3, 2]
    selector = module.DirectSelector(Value(), rule(deterministic=True), SEED + 200, replicas=1)
    selector.select(board, "reward")
    charge(selector)
    selected = {row["option"]: row for row in selector.last_prefixes}
    for option in ("SPACE_1", "SPACE_4"):
        prefix = selected[option]
        assert prefix["status"] == "LOST" and prefix["steps_count"] == 1
        assert prefix["direct"][1:] == [1, 0] and prefix["tail"] == [0, 0, 0]
        assert prefix["controller"]["fragment_actions"] == 1
    assert all(selector.last_log["wiring"].values())


def test_real_actor_rng_consumes_only_its_four_draws_after_direct_selection():
    selector = module.DirectSelector(Value(), rule(), SEED + 300, replicas=1)
    actor_rng = random.Random(9501)
    expected = random.Random(9501)
    for _ in range(4):
        expected.random()
    actor = module.FragmentController(selector, "reward", rule(), actor_rng)
    actor.choose(BOARD, 0)
    charge(selector)
    LEDGER.update({"actor_" + name: value for name, value in actor.work.items() if not name.startswith("candidate_")})
    assert actor_rng.getstate() == expected.getstate()
    assert actor.work["model_uniform_draws"] == 4
    assert actor.work["candidate_model_uniform_draws"] == 80
    assert len(actor.events) == 1


def test_exact_zero_and_positive_ties_use_frozen_candidate_order(monkeypatch):
    # Terminal synthetic paths isolate mean pairing and selection from simulation.
    def simulate(board, query, option, replica, spawn_seed, rule):
        reward = 0 if option == "H2" else board[0]
        return dict(option=option, replica=replica, status="WON", steps_count=1,
            steps=[dict(status="WON")], action_paths=["H2" if option == "H2" else "fragment"],
            controller=dict(events=[{}], initiation_step=0, selected_option=option,
                            fragment_actions=0 if option == "H2" else 1),
            model_work=dict(spawn_uniform_draws=2), planning_counts=dict(model_uniform_draws=4),
            direct=[reward, 0, 1])
    monkeypatch.setattr(module, "_simulate_prefix", simulate)
    selector = module.DirectSelector(Value(), None, SEED, replicas=2)
    for reward, expected in ((0, "H2"), (1, "SPACE_1"), (-1, "H2")):
        result = selector.select([reward] + BOARD[1:], "reward", tuple(reversed(module.OPTIONS)))
        assert result["option"] == expected
    result = selector.select([1] + BOARD[1:], "reward", ("H2", "SNAKE_4"))
    assert result["option"] == "SNAKE_4"
    assert list(result["predictions"]) == ["H2", "SNAKE_4"]
    assert len(selector.last_prefixes) == 10
