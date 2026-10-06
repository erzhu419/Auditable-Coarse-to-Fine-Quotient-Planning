"""Synthetic labels and controller commitments; no environment transitions."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
import random

import numpy as np
import pytest

from acfqp.science import controlled_predictive_fragments_v83 as module
from acfqp.science.controlled_predictive_relational_dynamics_v69 import (
    LearnedDynamics, RewriteProgram,
)


ROOT = Path(__file__).resolve().parents[1]
LEDGER = Counter()
EARLY = (1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3)
TRIGGER = (1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0)
RULE = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
    ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_fragments_v83.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic paired targets and known-rule controller calls; no environment transitions.",
        ground_calls=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def fake_h2(self, board, query, rule, rng, work=None):
    for _ in range(4):
        rng.random()
    work["model_uniform_draws"] += 4
    work["test_h2_calls"] += 1
    return dict(action="LEFT")


class FixedSelector:
    def __init__(self, option):
        self.option, self.calls = option, []

    def select(self, board, query, allowed=None, work=None):
        self.calls.append((tuple(board), query, allowed))
        return dict(option=self.option, predicted_advantage=[1, 0, 0], value=1,
                    predictions={})


def leaf(value):
    return dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.0],
                values=[value], samples=[16])


def test_features_bind_primitive_and_duration_without_sampling():
    counts = Counter()
    for option in module.OPTIONS[1:]:
        vector = module.fragment_features(TRIGGER, option, counts)
        primitive, duration = option.split("_")
        assert len(vector) == len(module.FEATURE_NAMES) == 39
        assert vector[:36] == module.features(TRIGGER, 30)[:-1]
        assert vector[36:] == (primitive == "SPACE", primitive == "SNAKE", int(duration) / 4)
    assert counts == dict(fragment_feature_rows=4, board_feature_rows=4)
    LEDGER.update(counts)


@pytest.fixture(scope="module")
def fitted():
    targets = {"SPACE_1": [1, 0.2, 0], "SNAKE_1": [0.5, 0, 0],
               "SPACE_4": [2, 1, 0.1], "SNAKE_4": [-1, 0, 0]}
    rows = [dict(board=list(TRIGGER), query=query, option=option, episode=episode,
                 target=[999, 999, 999] if episode == 4 else targets[option])
            for query in module.QUERIES for episode in range(5)
            for option in module.OPTIONS[1:] for _ in range(8)]
    rows.append(dict(board=list(TRIGGER), query="reward", option="H2", episode=0,
                     target=[999, 999, 999]))
    seen = []
    real_fit = module._fit

    def capture(x, y, counts):
        seen.append((x.copy(), y.copy()))
        return real_fit(x, y, counts)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "_fit", capture)
        selector, log = module.Selector.fit(rows, checkpoint=5)
    LEDGER.update(log["counts"])
    return selector, log, targets, seen


def test_fit_uses_one_joint_tree_per_query_and_excludes_heldout_reference(fitted):
    selector, log, targets, seen = fitted
    assert log["training_records"] == 256 and log["heldout_records"] == 64
    assert log["reference_records_excluded"] == 1
    assert log["counts"]["tree_fits"] == len(selector.trees) == len(seen) == 2
    for x, y in seen:
        assert x.shape == (128, 39) and y.shape == (128, 3)
        assert set(map(tuple, y)) == set(map(tuple, targets.values()))
    expected_mse = np.mean([(np.asarray(target) - 999) ** 2
                            for target in targets.values()], axis=0)
    for query in module.QUERIES:
        np.testing.assert_allclose(log["queries"][query]["heldout_mse_components"], expected_mse)


def test_complete_vector_selection_one_step_restriction_and_roundtrip(fitted):
    selector, _, targets, _ = fitted
    payload = json.loads(json.dumps(selector.to_payload()))
    restored = module.Selector.from_payload(payload)
    counts = Counter()
    reward = selector.select(TRIGGER, "reward", work=counts)
    risk = selector.select(TRIGGER, "risk_goal", work=counts)
    one = selector.select(TRIGGER, "reward", module.ONE_STEP_OPTIONS, counts)
    assert reward["option"] == "SPACE_4" and risk["option"] == "SNAKE_1"
    np.testing.assert_allclose(reward["predicted_advantage"], targets["SPACE_4"])
    assert risk["predictions"]["SPACE_4"]["value"] == pytest.approx(-1.6)
    assert one["option"] == "SPACE_1"
    assert tuple(one["predictions"]) == module.ONE_STEP_OPTIONS
    assert restored.select(TRIGGER, "reward", work=counts) == reward
    assert restored.select(TRIGGER, "risk_goal", work=counts) == risk
    assert selector.to_payload() == restored.to_payload() == payload
    # Strictly positive selection and stable option order are part of the policy.
    zero = module.Selector({q: leaf([0, 0, 0]) for q in module.QUERIES}, 0)
    assert zero.select(TRIGGER, "reward", work=counts)["option"] == "H2"
    tie = module.Selector({q: leaf([1, 0, 0]) for q in module.QUERIES}, 0)
    assert tie.select(TRIGGER, "reward", work=counts)["option"] == "SPACE_1"
    assert "model_uniform_draws" not in counts
    LEDGER.update(counts)


def test_four_action_commitment_selects_once_then_permanently_returns_to_h2(monkeypatch):
    monkeypatch.setattr(module.Policy, "choose", fake_h2)
    selector = FixedSelector("SNAKE_4")
    rng, expected = random.Random(830001), random.Random(830001)
    controller = module.FragmentController(selector, "reward", RULE, rng)
    for step in range(2):
        assert controller.choose(EARLY, step) == "LEFT"
    primitive = module.planner.policy_action(TRIGGER, "SNAKE", RULE)
    for step in range(2, 6):
        assert controller.choose(TRIGGER, step) == primitive
    for step in range(6, 9):
        assert controller.choose(TRIGGER, step) == "LEFT"
    for _ in range(36):
        expected.random()
    assert rng.getstate() == expected.getstate()
    assert len(selector.calls) == len(controller.events) == 1
    assert controller.initiation_step == 2 and controller.selected_option == "SNAKE_4"
    assert controller.fragment_actions == 4 and controller.remaining_actions == 0
    assert controller.finished_fragment and controller.work["test_h2_calls"] == 5
    assert controller.work["dummy_model_uniform_draws"] == 16
    assert controller.work["model_uniform_draws"] == 36
    LEDGER.update(controller.work)


def test_h2_choice_rejects_intervention_permanently_and_baseline_never_selects(monkeypatch):
    monkeypatch.setattr(module.Policy, "choose", fake_h2)
    selector = FixedSelector("H2")
    selected = module.FragmentController(selector, "reward", RULE, random.Random(830002))
    baseline = module.FragmentController(selector, "reward", RULE, random.Random(830002),
                                         mode="H2_ONLY")
    for step in range(6):
        assert selected.choose(TRIGGER, step) == baseline.choose(TRIGGER, step) == "LEFT"
    assert len(selector.calls) == len(selected.events) == 1
    assert baseline.events == [] and baseline.selected_option is None
    assert selected.selected_option == "H2" and selected.finished_fragment
    assert selected.fragment_actions == baseline.fragment_actions == 0
    assert selected.rng.getstate() == baseline.rng.getstate()
    LEDGER.update(selected.work)
    LEDGER.update(baseline.work)


@pytest.mark.parametrize("option", module.OPTIONS)
def test_immediate_fixed_branches_obey_duration_and_rng_alignment(monkeypatch, option):
    monkeypatch.setattr(module.Policy, "choose", fake_h2)
    controller = module.FragmentController(None, "reward", RULE, random.Random(830003),
                                         immediate=True, fixed_option=option)
    for step in range(6):
        controller.choose(EARLY, step)
    duration = 0 if option == "H2" else int(option.split("_")[1])
    assert controller.fragment_actions == duration
    assert controller.work["test_h2_calls"] == 6 - duration
    assert controller.work["model_uniform_draws"] == 24
    assert controller.work["dummy_model_uniform_draws"] == 4 * duration
    assert controller.initiation_step == 0 and len(controller.events) == 1
    before = controller.rng.getstate()
    assert controller.choose((11,) + (0,) * 15, 6) is None
    assert controller.rng.getstate() == before
    LEDGER.update(controller.work)


def test_real_h2_prefix_identical_until_trigger_and_one_step_has_one_action():
    selector = FixedSelector("SPACE_1")
    intervention = module.FragmentController(selector, "risk_goal", RULE,
                                            random.Random(830004), mode="ONE_STEP")
    baseline = module.FragmentController(None, "risk_goal", RULE,
                                        random.Random(830004), mode="H2_ONLY")
    for step in range(3):
        assert intervention.choose(EARLY, step) == baseline.choose(EARLY, step)
    assert intervention.rng.getstate() == baseline.rng.getstate()
    assert selector.calls == [] and intervention.events == []
    intervention.choose(TRIGGER, 3)
    baseline.choose(TRIGGER, 3)
    assert selector.calls[0][2] == module.ONE_STEP_OPTIONS
    assert intervention.fragment_actions == 1 and intervention.finished_fragment
    assert intervention.rng.getstate() == baseline.rng.getstate()
    assert intervention.work["model_uniform_draws"] == baseline.work["model_uniform_draws"] == 16
    LEDGER.update(intervention.work)
    LEDGER.update(baseline.work)
