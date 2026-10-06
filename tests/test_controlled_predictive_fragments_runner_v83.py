"""Bounded real-runner integration on development-only paired streams."""
from collections import Counter
from fractions import Fraction
import importlib.util
import json
from pathlib import Path

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_fragments_v83 import Selector, QUERIES
from acfqp.science.controlled_predictive_relational_dynamics_v69 import (
    LearnedDynamics, RewriteProgram,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fragments_runner_v83",
    ROOT / "scripts/run_controlled_predictive_fragments_v83.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
LEDGER = Counter()
EVALUATIONS = []


@pytest.fixture(scope="module", autouse=True)
def retain_development_work(request):
    patch = pytest.MonkeyPatch()
    for name in ("swipe_board_v1", "state_from_board_v1", "step_v1"):
        original = getattr(ground, name)

        def counted(*args, _function=original, _name=name, **kwargs):
            LEDGER[_name] += 1
            return _function(*args, **kwargs)

        patch.setattr(ground, name, counted)
    yield
    patch.undo()
    path = ROOT / "reports/controlled_predictive_fragments_v83.runner_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, failures=request.session.testsfailed,
        scope="Synthetic fit and actual paired games; lifecycle 99, replica 99 only.",
        main_campaign_calls=0, work=dict(LEDGER), evaluations=EVALUATIONS))
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print("V83_RUNNER_DEVELOPMENT_WORK=" + json.dumps(dict(LEDGER), sort_keys=True))


def test_paired_runner_trigger_commitment_frozen_identity_and_rng():
    board = [1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0]
    targets = {"SPACE_1": [0.5, 0, 0], "SNAKE_1": [-0.2, 0, 0],
               "SPACE_4": [2, 0, 0], "SNAKE_4": [-1, 0, 0]}
    rows = [dict(board=board, query=query, option=option, target=target, episode=0)
            for query in QUERIES for option, target in targets.items() for _ in range(8)]
    selector, fit = Selector.fit(rows, checkpoint=6)
    LEDGER.update(fit["counts"])
    saved = json.loads(json.dumps(selector.to_payload()))
    frozen = Selector.from_payload(saved)
    assert selector.select(board, "reward")["option"] == "SPACE_4"
    rule = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")

    def play(method, model, limit):
        row, raw = runner.evaluate_game(method, model, rule, 99, 99, "reward", max_steps=limit)
        LEDGER.update(row["environment_counts"])
        LEDGER.update(row["planning_counts"])
        EVALUATIONS.append(dict(method=method, limit=limit, **row))
        return row, raw

    limit = 80
    results = {"H2_ONLY": play("H2_ONLY", None, limit)}
    h2_steps = results["H2_ONLY"][1]["episode"]["steps"]
    trigger = next((i for i, step in enumerate(h2_steps)
                    if step["board"].count(0) <= runner.TRIGGER_EMPTY_CELLS), None)
    if trigger is None:
        limit = 120
        results["H2_ONLY"] = play("H2_ONLY", None, limit)
        h2_steps = results["H2_ONLY"][1]["episode"]["steps"]
        trigger = next((i for i, step in enumerate(h2_steps)
                        if step["board"].count(0) <= runner.TRIGGER_EMPTY_CELLS), None)
    assert trigger is not None and trigger + 4 < len(h2_steps)
    for method in runner.METHODS[1:]:
        model = (Selector.from_payload(frozen.to_payload() if method == "FROZEN_6" else saved)
                 if method in ("ONE_STEP", "FRAGMENT", "FROZEN_6") else None)
        before = model.to_payload() if model else None
        results[method] = play(method, model, limit)
        assert model is None or model.to_payload() == before

    assert selector.to_payload() == frozen.to_payload() == saved
    for method, (row, raw) in results.items():
        assert row["seed"] == 8_390_000 + 99 * 100 + 99
        assert row["planning_counts"]["model_uniform_draws"] == 4 * row["steps"]
        assert row["committed_length_matches"]
        if method == "H2_ONLY":
            assert row["controller_events"] == 0 and row["fragment_actions"] == 0
            assert row["initiation_step"] is None
            continue
        assert raw["episode"]["steps"][:trigger] == h2_steps[:trigger]
        assert raw["episode"]["steps"][trigger]["board"] == h2_steps[trigger]["board"]
        assert row["initiation_step"] == trigger and row["controller_events"] == 1
        duration = 1 if method == "ONE_STEP" else 4
        assert row["selected_option"] == f"SPACE_{duration}"
        assert row["fragment_actions"] == row["duration_budget"] == duration
        assert raw["action_paths"] == ["fragment" if trigger <= i < trigger + duration else "H2"
                                       for i in range(row["steps"])]
        assert row["planning_counts"]["dummy_model_uniform_draws"] == 4 * duration
    assert results["FRAGMENT"][1]["episode"]["steps"] == results["FROZEN_6"][1]["episode"]["steps"]
    assert results["FRAGMENT"][1]["episode"]["steps"] == results["FIXED_SPACE4"][1]["episode"]["steps"]
