"""Small policy-iteration integration with disjoint development game seeds."""
from collections import Counter
from fractions import Fraction
import importlib.util
import json
from pathlib import Path

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_policy_advantage_v81 import Policy, QUERIES, improve
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.controlled_predictive_target_horizon_v80 import ConsequenceModel


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v81_runner_integration",
    ROOT / "scripts/run_controlled_predictive_policy_iteration_v81.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
RULE = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
    ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")
COUNTS = {name: Counter() for name in ("ground_calls", "environment", "planning", "fitting")}


@pytest.fixture(scope="module", autouse=True)
def retain_development_work(request):
    patch = pytest.MonkeyPatch()
    for name in ("swipe_board_v1", "state_from_board_v1", "step_v1"):
        original = getattr(ground, name)

        def counted(*args, _function=original, _name=name, **kwargs):
            COUNTS["ground_calls"][_name] += 1
            return _function(*args, **kwargs)

        patch.setattr(ground, name, counted)
    yield
    patch.undo()
    payload = dict(test_module=__file__, tests=3, session_failures=request.session.testsfailed,
        attempts=1, scope="Synthetic fitting and five three-step natural games; lifecycle 99, replica 99.",
        full_support_teacher_calls=COUNTS["ground_calls"].get("step_v1", 0),
        main_campaign_games=0, counts={key: dict(value) for key, value in COUNTS.items()})
    (ROOT / "reports/controlled_predictive_policy_iteration_v81.runner_checks.json").write_text(
        json.dumps(payload, indent=2) + "\n")
    print("V81_RUNNER_DEVELOPMENT_WORK=" + json.dumps(payload["counts"], sort_keys=True))


def synthetic_rows(iteration, value):
    return [dict(board=[1, 1] + [0] * 13 + [3], query=query, episode=episode,
        action="RIGHT", reference_action="LEFT", target=[value, 0.0, 0.0],
        iteration=iteration, step=episode, root_index=episode, replicas=2)
        for query in QUERIES for episode in range(5) for _ in range(8)]


@pytest.fixture(scope="module")
def fitted():
    base = Policy.base()
    base_payload = base.to_payload()
    old_rows = synthetic_rows(1, 0.5)
    first, first_log = improve(base, old_rows, 1, RULE)
    first_payload = first.to_payload()
    new_rows = synthetic_rows(2, -0.25)
    second, second_log = improve(first, old_rows + new_rows, 2, RULE)
    COUNTS["fitting"].update(first_log["counts"])
    COUNTS["fitting"].update(second_log["counts"])
    return base, base_payload, first, first_payload, second, second_log


def test_serialized_iterations_keep_parent_and_fit_only_current_round(fitted, tmp_path):
    base, base_payload, first, first_payload, second, second_log = fitted
    for name, policy in (("first", first), ("second", second)):
        path = tmp_path / f"{name}.json"
        RUNNER.save(path, policy.to_payload())
        restored = Policy.from_payload(json.loads(path.read_text()))
        assert restored.to_payload() == policy.to_payload()
    assert base.to_payload() == base_payload
    assert first.to_payload() == first_payload
    assert second.parent.to_payload() == first_payload
    assert second.parent is not first
    assert second_log["input_records"] == 160
    assert second_log["current_iteration_records"] == second_log["other_iteration_records_excluded"] == 80
    assert second_log["training_records"] == 64 and second_log["heldout_records"] == 16
    assert second_log["counts"]["tree_fits"] == 2
    assert all(record["training_target_mean"] == [-0.25, 0.0, 0.0]
               for record in second_log["queries"].values())


def reference_model(scope):
    value = [0.0, float(scope == "TERMINAL"), 0.0]
    tree = dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.0],
                values=[value], samples=[16])
    return ConsequenceModel(scope, {policy: dict(tree) for policy in RUNNER.planner.POLICIES}, 75)


def test_five_natural_game_arms_pair_p1_and_consume_four_model_draws(fitted):
    _, _, first, first_payload, _, _ = fitted
    models = dict(H2_ONLY=Policy.base(), CURRENT=Policy.from_payload(first_payload),
        FROZEN_1=Policy.from_payload(first_payload), SHORT_REF=reference_model("SHORT"),
        TERMINAL_REF=reference_model("TERMINAL"))
    games = {}
    for method in RUNNER.METHODS:
        row, raw = RUNNER.evaluate_game(method, models[method], RULE,
            lifecycle=99, replica=99, query_name="reward", max_steps=3)
        COUNTS["environment"].update(row["environment_counts"])
        COUNTS["planning"].update(row["planning_counts"])
        games[method] = raw
        assert row["seed"] == 8_190_000 + 99 * 100 + 99
        assert row["status"] == "CUTOFF" and row["steps"] == 3
        assert row["planning_counts"]["model_uniform_draws"] == 4 * row["decisions"] == 12
        assert row["environment_counts"]["sampled_transitions"] == 3
        assert row["environment_counts"]["environment_random_draws"] == 10
        assert row["environment_counts"]["initial_spawns"] == 2
    assert games["CURRENT"]["episode"]["steps"] == games["FROZEN_1"]["episode"]["steps"]
    assert games["CURRENT"]["decisions"] == games["FROZEN_1"]["decisions"]
    assert first.to_payload() == first_payload
    assert models["CURRENT"].to_payload() == models["FROZEN_1"].to_payload() == first_payload


def test_root_reference_is_executed_action_not_parent_reference():
    steps = [dict(board=[index] + [0] * 15, action="RIGHT", reference_action="LEFT")
             for index in range(6)]
    roots = RUNNER.select_roots(dict(steps=steps), "risk_goal", 9)
    assert roots == [dict(board=steps[index]["board"], reference_action="RIGHT",
        query="risk_goal", episode=9, step=index) for index in (2, 4)]
