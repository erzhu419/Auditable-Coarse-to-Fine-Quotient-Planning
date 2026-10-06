"""Retain horizon reversals, incomplete pairs, censoring and counterfactual scope."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v79_analysis", ROOT /
    "scripts/analyze_controlled_predictive_terminal_v79.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
CALLS = []


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_terminal_v79.analysis_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        synthetic_analysis_calls=len(CALLS), main_campaign_calls=0, ground_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def _run():
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], checkpoints=[39, 75],
        queries={"reward": {}, "risk_goal": {}}), lifecycles=[], actual_wall_seconds=20)
    for life in range(3):
        stages = []
        for checkpoint in (39, 75):
            rows = []
            for stratum in ("old", "new"):
                for query in ("reward", "risk_goal"):
                    for model in ("incumbent", "candidate"):
                        short = 10 if model == "incumbent" else 9
                        full = 20 if model == "incumbent" else [21, 22, 23][life]
                        rows.append(dict(stratum=stratum, root=dict(episode=4, step=4, board=[1]*16),
                            query=query, replica=0, seed=100*life+checkpoint, model=model,
                            short=dict(score=short*2048, utility=short, steps=32, status="CUTOFF",
                                work={"sampled_transitions": 32}),
                            full=dict(score=full*2048, utility=full, steps=34, status="LOST"),
                            extension=dict(work={"sampled_transitions": 2},
                                planning_counts={"model_spawn_samples": 4},
                                prediction_counts={"prediction_rows": 8}, seconds=0.1)))
            stages.append(dict(episodes=checkpoint, trajectories=rows, expected_trajectories=8))
        run["lifecycles"].append(dict(id=life, stages=stages))
    return run


def _analyze(run, label, source=None):
    CALLS.append(label)
    return ANALYSIS.analyze_run(run, source)


def test_horizon_reversal_is_lifecycle_averaged_and_work_is_separate():
    result = _analyze(_run(), "full_terminal")
    assert result["complete"]
    assert result["cohort"]["trajectories"] == 48
    assert result["cohort"]["pairs"] == 24
    assert result["cohort"]["all_full_outcomes_terminal"]
    assert result["cohort"]["status_transitions"] == {"CUTOFF->LOST": 48}
    final = result["checkpoints"][-1]["strata"]["new"]["reward"]
    assert final["lifecycle_means"]["mean_short_utility_delta"] == -1
    assert final["lifecycle_means"]["mean_full_utility_delta"] == 2
    assert final["lifecycle_means"]["mean_suffix_utility_delta"] == 3
    assert final["lifecycle_mean_sign_reversals"] == 3
    assert all(row["strict_sign_reversals"] == 1 for row in final["lifecycles"])
    assert result["acceptance_summary"]["reconstructed_short"] == dict(accepted=0, rejected=6, unresolved=0)
    assert result["acceptance_summary"]["hypothetical_full"] == dict(accepted=6, rejected=0, unresolved=0)
    work = result["actual_executed_work"]
    assert work["inherited_prefix_counts"]["sampled_transitions"] == 48*32
    assert work["new_extension_counts"]["sampled_transitions"] == 48*2
    assert work["new_planning_counts"]["model_spawn_samples"] == 48*4


def test_censored_outcomes_remain_complete_execution_without_terminal_verdict():
    run = _run()
    run["lifecycles"][0]["stages"][0]["trajectories"][0]["full"]["status"] = "CUTOFF"
    result = _analyze(run, "censored")
    assert result["complete"]
    assert not result["cohort"]["all_full_outcomes_terminal"]
    assert result["acceptance_events"][0]["hypothetical_full_rule"]["accepted"] is None
    assert result["acceptance_events"][0]["short_rule"]["accepted"] is False
    assert result["acceptance_summary"]["hypothetical_full"]["unresolved"] == 1


def test_missing_and_duplicate_trajectories_have_no_acceptance_verdict():
    missing = _run()
    missing["lifecycles"][0]["stages"][0]["trajectories"].pop()
    result = _analyze(missing, "missing")
    assert not result["complete"]
    assert result["cohort"]["pairing_problems"]
    assert result["acceptance_events"][0]["short_rule"]["accepted"] is None
    duplicate = _run()
    rows = duplicate["lifecycles"][0]["stages"][0]["trajectories"]
    rows[1] = deepcopy(rows[0])
    result = _analyze(duplicate, "duplicate")
    assert not result["complete"]
    assert result["cohort"]["pairing_problems"][0]["model_counts"] == {"incumbent": 2}


def test_natural_comparison_requires_actual_candidate_and_incumbent_alignment():
    source = dict(settings={"evaluation_replicas": 1}, lifecycles=[])
    for life in range(3):
        methods = {method: dict(games=[dict(seed=life, replica=0, query=query,
            score=2048*value, utility=value) for query in ("reward", "risk_goal")])
            for method, value in (("MSE_PLAN", 3), ("FROZEN_PLAN", 1))}
        source["lifecycles"].append(dict(id=life, stages=[dict(episodes=39,
            decision_acceptance={"accepted": life == 1}), dict(episodes=75,
            mse_acceptance={"accepted": life != 2}, methods=methods)]))
    result = _analyze(_run(), "natural_alignment", source)
    natural = result["retained_natural_comparison"]["queries"]["reward"]
    assert not natural["complete"]
    assert [r["mean_utility_delta"] for r in natural["lifecycles"]] == [2, None, None]
    assert natural["mean_utility_delta"] is None
