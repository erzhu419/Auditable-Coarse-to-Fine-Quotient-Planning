"""A pooled improvement must not erase a lifecycle-level counterexample."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v77_analysis", ROOT /
    "scripts/analyze_controlled_predictive_lifelong_v77.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
CALLS = []


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_lifelong_v77.analysis_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        synthetic_analysis_calls=len(CALLS), main_campaign_calls=0, ground_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def test_lifecycle_counterexample_and_cumulative_cost_attribution():
    methods = ["H2_ONLY", "FROZEN_PLAN", "FIXED_PLAN", "REVISED_PLAN", "REVISED_DIRECT"]
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], checkpoints=[5, 10],
        queries={"reward": {}}, methods=methods, evaluation_replicas=2), lifecycles=[], actual_wall_seconds=20)
    for life in range(3):
        checkpoints = []
        for episodes in (5, 10):
            per_method = {}
            for method in methods:
                value = ([-1, 0, 5] if episodes == 5 else [-2, 1, 10])[life] if method == "REVISED_PLAN" else 0
                games = [dict(seed=10 * life + replica, replica=replica, query="reward",
                    status="CUTOFF" if (life, episodes, method, replica) == (0, 10, "REVISED_PLAN", 0) else "LOST",
                    score=value, utility=value, steps=2, max_rank=1, seconds=0.1,
                    environment_counts={"sampled_transitions": 2},
                    planning_counts={"model_spawn_samples": 4}, prediction_counts={}) for replica in range(2)]
                per_method[method] = dict(games=games, costs=dict(total_seconds=1 if episodes == 5 else 3))
            checkpoints.append(dict(episodes=episodes, source_summary=dict(episodes=episodes, records=episodes * 3,
                work={"sampled_transitions": episodes * 2}, policy_work={}, seconds=1.0,
                warmup_seconds=0.5, outcomes={"LOST": episodes}, by_policy={}, exact_teacher_calls=0),
                initialization={"counts": {"tree_fits": 3}}, updates={}, models={}, methods=per_method))
        run["lifecycles"].append(dict(id=life, checkpoints=checkpoints))
    CALLS.append("counterexample")
    result = ANALYSIS.analyze_run(run)
    comparison = result["final_revised_plan_minus_comparator"]["FIXED_PLAN"]["reward"]
    assert comparison["mean_delta"] == 3
    assert comparison["lifecycle_mean_deltas"] == [-2, 1, 10]
    assert comparison["positive_lifecycles"] == 2
    assert not result["signals"]["quality_gain_over_fixed_all_lifecycles_by_query"]["reward"]
    assert not result["cohort"]["all_games_terminal"]
    assert result["cohort"]["fixed_controls_unchanged"]
    assert result["actual_executed_work"]["tree_fits"] == 9
    assert result["actual_executed_work"]["source_sampled_transitions"] == 60
    assert result["checkpoints"][-1]["methods"]["FIXED_PLAN"]["cumulative_costs"]["totals"]["total_seconds"] == 9
    # A changed frozen control makes the longitudinal comparison invalid.
    changed = run["lifecycles"][0]["checkpoints"][-1]["methods"]["FROZEN_PLAN"]["games"][0]
    changed["score"] = 1
    CALLS.append("frozen_control_drift")
    drifted = ANALYSIS.analyze_run(run)
    assert not drifted["complete"]
    assert not drifted["cohort"]["fixed_controls_unchanged"]
