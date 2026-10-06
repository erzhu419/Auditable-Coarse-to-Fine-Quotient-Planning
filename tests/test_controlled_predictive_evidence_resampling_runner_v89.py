"""Actual V89 controller commitments and independent confirmation ordering."""
from collections import Counter
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "evidence_resampling_runner_v89",
    ROOT / "scripts/run_controlled_predictive_evidence_resampling_v89.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
WORK = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_evidence_resampling_v89.runner_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(session_failures=request.session.testsfailed,
        ground_work=dict(WORK), new_tree_fits=0, main_campaign_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def evidence_leaf(rewards, positive_fractions):
    return dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.],
        values=[[component for reward in rewards for component in (reward, 0., 0.)]],
        samples=[2], frequencies=[[[0., 1. - fraction, fraction]
            for fraction in positive_fractions]])


def deployed_models():
    from acfqp.science.controlled_predictive_evidence_fragments_v88 import EvidenceSelector

    trees = {
        "BASE": {
            "reward": evidence_leaf([-1., -1., -1., -1.], [1., 1., 1., 1.]),
            "risk_goal": evidence_leaf([1., 2., 3., 4.], [0., 0., 0., 1.]),
        },
        "BALANCED": {
            "reward": evidence_leaf([3., 1., 2., 4.], [1., 0., 0., 0.]),
            "risk_goal": evidence_leaf([1., 2., 3., 4.], [0., 0., 0., 0.]),
        },
        "EVIDENCE": {
            "reward": evidence_leaf([1., 2., 4., 3.], [0., 0., 1., 0.]),
            "risk_goal": evidence_leaf([-1., -1., -1., 0.], [1., 1., 1., 1.]),
        },
    }
    deployed = {"H2_ONLY": None}
    for variant, candidate_trees in trees.items():
        fitted = EvidenceSelector(candidate_trees, 12)
        for mode in ("POINT", "SUPPORTED"):
            deployed[variant + "_" + mode] = fitted.with_mode(mode)
    return deployed


def test_allocation_gates_and_histories_on_real_aligned_controller(monkeypatch, tmp_path):
    deployed = deployed_models()
    before = {name: model.to_payload() for name, model in deployed.items() if model}
    actual = RUNNER.evaluate_game

    def limited(*args, **kwargs):
        row, raw = actual(*args, **kwargs, max_steps=100)
        WORK.update(row["environment_counts"])
        return row, raw

    monkeypatch.setattr(RUNNER, "evaluate_game", limited)
    monkeypatch.setattr(RUNNER, "REPLICAS", 1)
    payload = json.loads((ROOT / "reports/controlled_predictive_evidence_learning_v88"
        / "supplied_dynamics.json").read_text())
    rule = RUNNER.LearnedDynamics.from_payload(payload)
    result = RUNNER.evaluate_methods(99, tmp_path, deployed, rule)
    assert all(result["wiring"].values())
    assert {name: model.to_payload() for name, model in deployed.items() if model} == before
    categories = {(contrast, row["query"]): row["category"]
        for contrast, rows in result["gate_changes"].items() for row in rows}
    expected = {
        ("BASE_SUPPORTED_minus_BASE_POINT", "reward"): "both_h2",
        ("BASE_SUPPORTED_minus_BASE_POINT", "risk_goal"): "same_fragment",
        ("BALANCED_SUPPORTED_minus_BALANCED_POINT", "reward"): "changed_fragment",
        ("BALANCED_SUPPORTED_minus_BALANCED_POINT", "risk_goal"): "disabled",
        ("EVIDENCE_SUPPORTED_minus_EVIDENCE_POINT", "reward"): "same_fragment",
        ("EVIDENCE_SUPPORTED_minus_EVIDENCE_POINT", "risk_goal"): "both_h2",
        ("BALANCED_SUPPORTED_minus_BASE_SUPPORTED", "reward"): "enabled",
        ("BALANCED_SUPPORTED_minus_BASE_SUPPORTED", "risk_goal"): "disabled",
        ("EVIDENCE_SUPPORTED_minus_BASE_SUPPORTED", "reward"): "enabled",
        ("EVIDENCE_SUPPORTED_minus_BASE_SUPPORTED", "risk_goal"): "disabled",
        ("EVIDENCE_SUPPORTED_minus_BALANCED_SUPPORTED", "reward"): "changed_fragment",
        ("EVIDENCE_SUPPORTED_minus_BALANCED_SUPPORTED", "risk_goal"): "both_h2",
    }
    assert categories == expected
    expected_options = {
        ("BASE_SUPPORTED", "reward"): "H2",
        ("BASE_SUPPORTED", "risk_goal"): "SNAKE_4",
        ("BALANCED_POINT", "reward"): "SNAKE_4",
        ("BALANCED_SUPPORTED", "reward"): "SPACE_1",
        ("BALANCED_SUPPORTED", "risk_goal"): "H2",
        ("EVIDENCE_SUPPORTED", "reward"): "SPACE_4",
        ("EVIDENCE_SUPPORTED", "risk_goal"): "H2",
    }
    assert set(result["methods"]) == set(deployed)
    for method, record in result["methods"].items():
        assert len(record["games"]) == 2
        for game in record["games"]:
            assert game["seed"] == 8990000 + 99 * 100
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


@pytest.mark.parametrize("life", [0, 1])
def test_confirmation_follows_every_fit_and_export_and_never_enters_fits(monkeypatch, tmp_path, life):
    source = tmp_path / "source"
    output = tmp_path / "output"
    output.mkdir()
    for checkpoint in (6, 12):
        stage = source / f"life_{life}" / f"checkpoint_{checkpoint}"
        stage.mkdir(parents=True)
        (stage / "root_logs.json").write_text("[]\n")
        with gzip.open(stage / "new_rows.jsonl.gz", "wt"):
            pass
    monkeypatch.setattr(RUNNER, "SOURCE", source)
    base_roots = [dict(query=query, episode=episode, board=[0] * 16, origin="BASE")
        for query in RUNNER.QUERIES for episode in (0, 4)]
    events, fit_inputs = [], []
    deployed = deployed_models()
    monkeypatch.setattr(RUNNER, "reconstruct_roots", lambda logs, extra, rows:
        (deepcopy(base_roots), {"retained_means_match": True}))

    def fit(roots, checkpoint):
        variant = roots[0]["origin"]
        assert variant in ("BASE", "BALANCED", "EVIDENCE")
        assert checkpoint == 12
        fit_inputs.append(deepcopy(roots))
        events.append(("fit", variant))
        return deployed[variant + "_SUPPORTED"], dict(seconds=1., counts={"tree_fits": 2})

    def acquire(lifecycle, arm, roots, rule, folder, budget):
        assert lifecycle == life and budget == RUNNER.BUDGET
        assert roots == base_roots
        assert (output / f"life_{life}" / "base_selector.json").exists()
        events.append(("acquire", arm))
        changed = deepcopy(roots)
        for root in changed:
            root["origin"] = arm
        return changed, dict(acquisition_seconds=2.)

    def confirm(lifecycle, roots, rule, folder, replicas):
        assert lifecycle == life and replicas == 8
        assert roots == base_roots
        stage = output / f"life_{life}"
        learning = json.loads((stage / "learning.json").read_text())
        assert set(learning["updates"]) == {"BASE", "BALANCED", "EVIDENCE"}
        for variant in ("BASE", "BALANCED", "EVIDENCE"):
            assert ("fit", variant) in events
            exported = json.loads((stage / f"{variant.lower()}_selector.json").read_text())
            assert exported == deployed[variant + "_SUPPORTED"].to_payload()
        events.append(("confirmation", None))
        # A conspicuous confirmation-side sentinel must never appear in a fit input.
        for root in roots:
            root["origin"] = "CONFIRMATION_ONLY"
        return dict(seconds=999., branch_work={"sampled_transitions": 17})

    def evaluate(lifecycle, folder, models, rule):
        assert events[-1] == ("confirmation", None)
        assert set(models) == set(deployed)
        events.append(("evaluate", None))
        return dict(methods={name: dict(costs={"evaluation_seconds": .25}) for name in models})

    monkeypatch.setattr(RUNNER.EvidenceSelector, "fit", fit)
    monkeypatch.setattr(RUNNER, "acquire_allocation", acquire)
    monkeypatch.setattr(RUNNER, "collect_confirmation", confirm)
    monkeypatch.setattr(RUNNER, "evaluate_methods", evaluate)
    prior_stage = dict(source=dict(work={"sampled_transitions": 3}, seconds=5.),
        branches=dict(work={"sampled_transitions": 7}, seconds=11.),
        update=dict(counts={"tree_fits": 2}, seconds=13.))
    payload = json.loads((ROOT / "reports/controlled_predictive_evidence_learning_v88"
        / "supplied_dynamics.json").read_text())
    result = RUNNER.lifecycle_run(life, output, payload, {"checkpoints": [prior_stage, prior_stage]})
    expected_arms = ("BALANCED", "EVIDENCE") if life == 0 else ("EVIDENCE", "BALANCED")
    assert events == [("fit", "BASE"), ("acquire", expected_arms[0]), ("fit", expected_arms[0]),
        ("acquire", expected_arms[1]), ("fit", expected_arms[1]), ("confirmation", None), ("evaluate", None)]
    assert len(fit_inputs) == 3
    assert all(root["origin"] != "CONFIRMATION_ONLY" for roots in fit_inputs for root in roots)
    assert result["inherited"]["source_work"]["sampled_transitions"] == 6
    assert result["inherited"]["branch_work"]["sampled_transitions"] == 14
    assert result["inherited"]["construction_seconds"] == 32.
    assert result["inherited"]["historical_unused_v83_fitting_seconds"] == 26.
    assert result["confirmation"]["branch_work"]["sampled_transitions"] == 17
    for method, record in result["evaluation"]["methods"].items():
        costs = record["costs"]
        assert not any("confirmation" in name or "historical_unused" in name for name in costs)
        assert costs["total_seconds"] == sum(value for name, value in costs.items() if name != "total_seconds")
        if method != "H2_ONLY":
            assert costs["inherited_acquisition_seconds"] == 32.
            assert costs["base_fitting_seconds"] == 1.
            if not method.startswith("BASE_"):
                assert costs["acquisition_seconds"] == 2.
