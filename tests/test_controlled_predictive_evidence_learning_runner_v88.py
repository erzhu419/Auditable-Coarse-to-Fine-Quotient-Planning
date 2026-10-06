"""Evidence labels change real controller commitments on aligned fresh streams."""
from collections import Counter
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "evidence_runner_v88", ROOT / "scripts/run_controlled_predictive_evidence_learning_v88.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
WORK = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_evidence_learning_v88.runner_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(session_failures=request.session.testsfailed,
        ground_work=dict(WORK), new_tree_fits=0, main_campaign_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def regression_leaf(rewards):
    values = [component for reward in rewards for component in (reward, 0., 0.)]
    return dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.],
        values=[values], samples=[2])


def evidence_leaf(rewards, positive_fractions):
    tree = regression_leaf(rewards)
    tree["frequencies"] = [[[0., 1. - fraction, fraction]
        for fraction in positive_fractions]]
    return tree


def test_evidence_gates_and_histories_on_real_aligned_controller(monkeypatch, tmp_path):
    from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector
    from acfqp.science.controlled_predictive_evidence_fragments_v88 import EvidenceSelector

    old_trees = {
        "COVERAGE": {"reward": regression_leaf([-1., -1., -1., -1.]),
            "risk_goal": regression_leaf([1., 2., 3., 4.])},
        "REPEAT": {"reward": regression_leaf([1., 2., 4., 3.]),
            "risk_goal": regression_leaf([1., 2., 3., 4.])},
    }
    evidence_trees = {
        "COVERAGE": {"reward": evidence_leaf([3., 1., 2., 4.], [1., 0., 0., 0.]),
            "risk_goal": evidence_leaf([1., 2., 3., 4.], [0., 0., 0., 0.])},
        "REPEAT": {"reward": evidence_leaf([1., 2., 4., 3.], [0., 0., 1., 0.]),
            "risk_goal": evidence_leaf([-1., -1., -1., 0.], [1., 1., 1., 1.])},
    }
    deployed = {"H2_ONLY": None}
    for arm in RUNNER.ALLOCATIONS:
        deployed[arm + "_OLD"] = JointSelector(old_trees[arm], 12)
        fitted = EvidenceSelector(evidence_trees[arm], 12)
        for mode in ("POINT", "SUPPORTED"):
            deployed[arm + "_" + mode] = fitted.with_mode(mode)
    before = {name: model.to_payload() for name, model in deployed.items() if model}
    actual = RUNNER.evaluate_game

    def limited(*args, **kwargs):
        row, raw = actual(*args, **kwargs, max_steps=100)
        WORK.update(row["environment_counts"])
        return row, raw

    monkeypatch.setattr(RUNNER, "evaluate_game", limited)
    monkeypatch.setattr(RUNNER, "REPLICAS", 1)
    rule = RUNNER.LearnedDynamics.from_payload(json.loads(
        (RUNNER.SOURCE / "supplied_dynamics.json").read_text()))
    result = RUNNER.evaluate_methods(99, tmp_path, deployed, rule)
    assert all(result["wiring"].values())
    assert {name: model.to_payload() for name, model in deployed.items() if model} == before
    categories = {(contrast, row["query"]): row["category"]
        for contrast, rows in result["gate_changes"].items() for row in rows}
    assert categories["COVERAGE_SUPPORTED_minus_COVERAGE_POINT", "reward"] == "changed_fragment"
    assert categories["COVERAGE_SUPPORTED_minus_COVERAGE_POINT", "risk_goal"] == "disabled"
    assert categories["REPEAT_SUPPORTED_minus_REPEAT_POINT", "reward"] == "same_fragment"
    assert categories["REPEAT_SUPPORTED_minus_REPEAT_POINT", "risk_goal"] == "both_h2"
    assert categories["COVERAGE_SUPPORTED_minus_COVERAGE_OLD", "reward"] == "enabled"
    assert all(category != "enabled" for (contrast, _), category in categories.items()
        if contrast.endswith("_POINT"))
    expected_options = {
        ("COVERAGE_POINT", "reward"): "SNAKE_4",
        ("COVERAGE_SUPPORTED", "reward"): "SPACE_1",
        ("COVERAGE_SUPPORTED", "risk_goal"): "H2",
        ("REPEAT_SUPPORTED", "reward"): "SPACE_4",
        ("REPEAT_SUPPORTED", "risk_goal"): "H2",
    }
    for method, record in result["methods"].items():
        assert len(record["games"]) == 2
        for game in record["games"]:
            assert game["seed"] == 8890000 + 99 * 100
            assert game["planning_counts"]["model_uniform_draws"] == 4 * game["steps"]
            assert game["committed_length_matches"]
            key = method, game["query"]
            if key in expected_options:
                assert game["selected_option"] == expected_options[key]
            if game["selected_option"] not in (None, "H2"):
                assert game["fragment_actions"] == int(game["selected_option"].split("_")[1])


def test_gate_categories_include_candidate_changes_and_missing_trigger():
    assert RUNNER.gate_category(None, None) == "both_h2"
    assert RUNNER.gate_category("H2", "SPACE_1") == "enabled"
    assert RUNNER.gate_category("SNAKE_4", "H2") == "disabled"
    assert RUNNER.gate_category("SPACE_4", "SPACE_4") == "same_fragment"
    assert RUNNER.gate_category("SPACE_1", "SNAKE_4") == "changed_fragment"
