"""Check causal contrasts, complete-triplet censoring and independent-life weighting."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("analysis_v82", ROOT /
    "scripts/analyze_controlled_predictive_policy_effects_v82.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
CALLS = []


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_policy_effects_v82.analysis_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        synthetic_analysis_calls=len(CALLS), main_campaign_calls=0, ground_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def _run():
    query = dict(reward_weight=1.0, failure_penalty=4.0, goal_bonus=4.0)
    result = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], roots_per_query_per_lifecycle=2,
        queries={"risk_goal": query}, replicas=4, methods=list(ANALYSIS.METHODS)),
        lifecycles=[], actual_wall_seconds=30)
    for life in range(3):
        roots = []
        for index in range(2):
            first = [-2, 1, 10][life] * (index + 1)
            games = []
            for replica in range(4):
                for method in ANALYSIS.METHODS:
                    score = 100 * 2048 + (0 if method == "PARENT" else first * 2048)
                    score += -3 * 2048 if method == "FULL_UPDATE" else 0
                    status = "WON" if method == "FULL_UPDATE" else "LOST"
                    games.append(dict(method=method, replica=replica, query="risk_goal",
                        env_seed=life * 100 + index * 10 + replica, model_seed=replica + 1000,
                        continuation_iteration=1 if method == "FULL_UPDATE" else 0,
                        score=score, status=status, utility=score / 2048 + (4 if status == "WON" else -4),
                        steps=5, max_rank=11, seconds=0.1,
                        environment_counts={"sampled_transitions": 5}, planning_counts={"model_spawn_samples": 16}))
            roots.append(dict(root=dict(query="risk_goal", episode=4, step=index + 2, root_index=index,
                reference_action="UP", selected_action="LEFT", predicted_advantage=[2, 0, 0],
                old_observed_advantage=[1, 0, 0]), games=games, work={"sampled_transitions": 60},
                wiring=dict(same_first_transition_first_full=True, no_override_parent_first_identical=None)))
        result["lifecycles"].append(dict(id=life, roots=roots))
    return result


def _analyze(run, label):
    CALLS.append(label)
    return ANALYSIS.analyze_run(run)


def test_three_effects_include_terminal_risk_and_average_roots_before_lives():
    run = _run()
    result = _analyze(run, "three_effects")
    assert result["complete"]
    query = result["paired_effects"]["risk_goal"]
    assert [row["effects"]["FIRST_ONLY_minus_PARENT"]["mean_utility_delta"]
            for row in query["lifecycles"]] == [-3, 1.5, 15]
    effects = query["effects"]
    assert effects["FIRST_ONLY_minus_PARENT"]["mean_utility_delta"] == 4.5
    assert effects["FULL_UPDATE_minus_FIRST_ONLY"]["mean_score_delta"] == -6144
    assert effects["FULL_UPDATE_minus_FIRST_ONLY"]["mean_utility_delta"] == 5
    assert effects["FULL_UPDATE_minus_PARENT"]["mean_utility_delta"] == 9.5
    assert result["root_diagnostics"]["negative_overrides"] == 2
    assert result["root_diagnostics"]["old_to_fresh_sign_reversals"] == 2
    assert result["root_diagnostics"]["predicted_to_fresh_sign_reversals"] == 2
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 360


def test_cutoff_excludes_entire_triplet_without_pooling_remaining_replicas():
    run = _run()
    # Leave one complete triplet on life 0 root 0; retain all four on root 1.
    root = run["lifecycles"][0]["roots"][0]
    for game in root["games"]:
        if game["method"] == "FULL_UPDATE" and game["replica"] < 3:
            game["status"] = "CUTOFF"
    result = _analyze(run, "censored_triplets")
    assert result["complete"]
    assert result["cohort"]["censored_triplets"] == 3
    assert result["cohort"]["complete_triplets"] == 21
    assert result["roots"][0]["complete_replicas"] == [3]
    assert result["paired_effects"]["risk_goal"]["effects"]["FIRST_ONLY_minus_PARENT"]["mean_utility_delta"] == 4.5
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 360
    for game in root["games"]:
        if game["method"] == "FULL_UPDATE":
            game["status"] = "CUTOFF"
    empty = _analyze(run, "no_complete_triplet_in_root")
    assert empty["paired_effects"]["risk_goal"]["effects"]["FIRST_ONLY_minus_PARENT"]["mean_utility_delta"] is None


def test_pairing_and_continuation_errors_do_not_silently_form_valid_effects():
    for name in ("missing", "duplicate", "seed", "continuation", "wiring"):
        run = deepcopy(_run())
        root = run["lifecycles"][0]["roots"][0]
        games = root["games"]
        if name == "missing":
            games.pop()
        elif name == "duplicate":
            games[-1] = deepcopy(games[0])
        elif name == "seed":
            games[0]["env_seed"] += 1
        elif name == "continuation":
            games[0]["continuation_iteration"] = 1
        else:
            root["wiring"]["same_first_transition_first_full"] = False
        result = _analyze(run, name)
        assert not result["complete"]
        if name != "wiring":
            assert result["roots"][0]["complete_triplets"] == 0
            assert result["paired_effects"]["risk_goal"]["effects"]["FIRST_ONLY_minus_PARENT"]["mean_utility_delta"] is None
