"""Check matched actual cost, joint cutoffs and independent suffix interpretation."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("evidence_resampling_analysis_v89", ROOT /
    "scripts/analyze_controlled_predictive_evidence_resampling_v89.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)


def _changes(evaluation):
    result = {}
    for left, right in ANALYSIS.GATE_CONTRASTS:
        old = {ANALYSIS._key(game): game for game in evaluation["methods"][right]["games"]}
        result[f"{left}_minus_{right}"] = [dict(seed=game["seed"], query=game["query"], replica=game["replica"],
            old_option=old[ANALYSIS._key(game)]["selected_option"], new_option=game["selected_option"],
            category=ANALYSIS._gate_category(old[ANALYSIS._key(game)]["selected_option"], game["selected_option"]))
            for game in evaluation["methods"][left]["games"]]
    return result


def _run():
    methods = ["H2_ONLY"] + [f"{variant}_{kind}" for variant in ANALYSIS.VARIANTS for kind in ANALYSIS.KINDS]
    queries = {"reward": {}, "risk_goal": {}}
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], methods=methods, queries=queries,
        evaluation_replicas=5, workers=3, confirmation_replicas=8, training_budget_per_query_allocation=2000),
        lifecycles=[], actual_wall_seconds=10)
    for life in range(3):
        updates = {variant: dict(dataset=dict(roots=24, training_roots=20, heldout_roots=4, records=96),
            update=dict(counts=dict(tree_fits=2, fit_roots=20, fit_candidate_labels=80,
                paired_root_replicas_read=160 if variant == "BASE" else 240)), fitting_seconds=1, export_seconds=0.01)
            for variant in ANALYSIS.VARIANTS}
        allocation = {arm: dict(queries={query: dict(budget=2000, used_transitions=2000,
            branch_work={"sampled_transitions": 2000}, planning_counts={"model_uniform_draws": 8000},
            outcomes={"LOST": 50, "CUTOFF": 1}, branch_trajectories=51, completed_blocks=1, incomplete_blocks=1,
            training_replica_counts={"8": 9, "16": 1}, seconds=2) for query in queries}) for arm in ANALYSIS.ARMS}
        d = [-2, 1, 10][life]
        methods_payload = {}
        for method in methods:
            games = []
            for query in queries:
                for replica, category in enumerate(ANALYSIS.CATEGORIES):
                    old = "H2" if category in ("enabled", "both_h2") else "SPACE_4"
                    new = "H2" if category in ("disabled", "both_h2") else (
                        "SNAKE_4" if category == "changed_fragment" else "SPACE_4")
                    if method == "H2_ONLY":
                        option, extra = None, 0
                    elif method.endswith("_SUPPORTED"):
                        option = new
                        extra = 5 * d if category in ("enabled", "changed_fragment") else 10 * d if category == "same_fragment" else 0
                    else:
                        option = old
                        extra = -5 * d if category in ("disabled", "changed_fragment") else 10 * d if category == "same_fragment" else 0
                    length = 4 if option in ("SPACE_4", "SNAKE_4") else 0
                    games.append(dict(seed=life * 100 + replica, replica=replica, query=query,
                        score=2048 * (100 + extra), utility=100 + extra - (4 if query == "risk_goal" else 0),
                        status="LOST", steps=10, max_rank=8, seconds=0.1,
                        environment_counts={"sampled_transitions": 10}, planning_counts={"model_uniform_draws": 40},
                        selected_option=option, initiation_step=2 if method != "H2_ONLY" else None,
                        fragment_actions=length, duration_budget=length, controller_events=int(method != "H2_ONLY"),
                        selector_checkpoint=12 if method != "H2_ONLY" else None, committed_length_matches=True))
            methods_payload[method] = dict(games=games, costs=dict(evaluation_seconds=1,
                inherited_construction_seconds=0 if method == "H2_ONLY" else 100, new_fitting_seconds=1))
        evaluation = dict(methods=methods_payload, wiring={name: True for name in ANALYSIS.WIRING},
            pairwise_histories={method: dict(pairs=10, identical_to_h2=10 if method == "H2_ONLY" else 4) for method in methods},
            query_response={method: dict(pairs=5, identical_trajectory_pairs=5) for method in methods})
        evaluation["gate_changes"] = _changes(evaluation)
        run["lifecycles"].append(dict(id=life, updates=updates, allocation=allocation,
            confirmation=dict(roots=20, complete_roots=20, incomplete_roots=0, branch_trajectories=800,
                branch_work={"sampled_transitions": 10000}, outcomes={"LOST": 800}, seconds=3),
            inherited=dict(source_work={"sampled_transitions": 10000}, branch_work={"sampled_transitions": 20000},
                historical_unused_v83_fit_counts={"tree_fits": 4}, construction_seconds=100), evaluation=evaluation))
    return run


def test_changed_fragment_and_recovery_are_separate_additive_effects():
    result = ANALYSIS.analyze_run(_run())
    assert result["complete"]
    for variant in ANALYSIS.VARIANTS:
        contrast = f"{variant}_SUPPORTED_minus_{variant}_POINT"
        effect = result["final_comparisons"][contrast]["reward"]
        assert effect["mean_utility_delta"] == 12
        decomposition = result["gate_decomposition"][contrast]["reward"]
        categories = decomposition["categories"]
        assert categories["enabled"]["old"]["mean_utility_contribution"] == 3
        assert categories["disabled"]["old"]["mean_utility_contribution"] == 3
        assert categories["disabled"]["h2"]["mean_utility_contribution"] == 0
        assert categories["changed_fragment"]["old"]["mean_utility_contribution"] == 6
        assert decomposition["summed_contributions"]["old"]["utility"] == effect["mean_utility_delta"]
    assert result["final_comparisons"]["EVIDENCE_SUPPORTED_minus_BALANCED_SUPPORTED"]["reward"]["mean_utility_delta"] == 0


def test_joint_cutoff_keeps_real_sampling_cost_and_partial_training_cost():
    run = _run()
    run["lifecycles"][0]["evaluation"]["methods"]["BASE_POINT"]["games"][0]["status"] = "CUTOFF"
    result = ANALYSIS.analyze_run(run)
    assert result["complete"] and not result["cohort"]["all_evaluation_games_terminal"]
    effect = result["final_comparisons"]["EVIDENCE_SUPPORTED_minus_EVIDENCE_POINT"]["reward"]
    assert effect["mean_utility_delta"] == pytest.approx(73 / 6)
    work = result["actual_executed_work"]
    assert work["new_evaluation_transitions"] == 2100
    assert work["new_acquisition_transitions"] == 24000
    assert work["new_confirmation_transitions"] == 30000
    assert work["newly_sampled_transitions"] == 56100
    assert work["acquisition"]["EVIDENCE"]["counts"]["incomplete_blocks"] == 6
    assert sum(row["tree_fits"] for row in work["new_fit_counts"].values()) == 18
    assert result["inherited"]["branch_work"]["sampled_transitions"] == 60000


def test_wrong_budget_or_changed_training_roster_fails_accounting():
    for defect in ("budget", "root", "extra_fit", "gate", "confirmation"):
        run = _run()
        life = run["lifecycles"][0]
        if defect == "budget":
            life["allocation"]["EVIDENCE"]["queries"]["reward"]["branch_work"]["sampled_transitions"] -= 1
        elif defect == "root":
            life["updates"]["EVIDENCE"]["dataset"]["training_roots"] += 1
        elif defect == "extra_fit":
            life["updates"]["BASE"]["update"]["counts"]["tree_fits"] = 3
        elif defect == "gate":
            life["evaluation"]["gate_changes"]["EVIDENCE_SUPPORTED_minus_BASE_SUPPORTED"][0]["category"] = "disabled"
        else:
            life["confirmation"]["roots"] += 1
        assert not ANALYSIS.analyze_run(run)["complete"], defect


class FixedSelector:
    def with_mode(self, mode):
        return self

    def select(self, board, query):
        return {"option": "SPACE_1"}


def _root(episode, means, n):
    samples = {option: [[mean, 0, 0] for _ in range(n)] for option, mean in zip(ANALYSIS.OPTIONS[1:], means)}
    return dict(query="reward", episode=episode, board=[episode] * 16, n_replicas=n, pair_deltas=samples,
        evidence={option: ANALYSIS.paired_evidence(values, "reward") for option, values in samples.items()})


def _confirmation():
    base = [_root(0, [0, 0, 0, 0], 8), _root(1, [0, 0, 0, 0], 8), _root(4, [0, 0, 0, 0], 8)]
    updated = [_root(0, [1, 1, 1, 1], 16), _root(1, [1, 0, 0, 0], 16), deepcopy(base[2])]
    logs = [dict(root=deepcopy(base[index]), complete_block=True,
        pair_deltas=_root(index, [value] * 4, 8)["pair_deltas"]) for index, value in ((0, 2), (1, -2))]
    data = dict(id=0, roots={"BASE": base, "BALANCED": deepcopy(updated), "EVIDENCE": deepcopy(updated)}, logs=logs,
        updates={variant: dict(update=dict(counts={"paired_root_replicas_read": 16 if variant == "BASE" else 32}))
                 for variant in ANALYSIS.VARIANTS}, selectors={variant: FixedSelector() for variant in ANALYSIS.VARIANTS})
    settings = dict(lifecycles=[0], queries=["reward"], confirmation_replicas=8)
    return [data], settings


def test_confirmation_uses_fresh_fixed_suffixes_and_preserves_root_grouping():
    inputs, settings = _confirmation()
    result = ANALYSIS.diagnose_confirmation(inputs, settings)
    assert result["complete"]
    data = result["newly_positive_confirmation"]["EVIDENCE"]["reward"]
    assert data["newly_positive_candidates"] == data["complete_candidates"] == 5
    assert data["independent_positive_means"] == 4
    assert data["independent_status_counts"] == {"positive": 4, "negative": 1}
    assert data["descriptive_pooled_candidate_mean_utility"] == 1.2
    assert data["equal_lifecycle_root_mean_utility"] == 0
    assert data["lifecycles"][0]["distinct_roots"] == 2
    assert result["learned_choices_on_training_roots"]["EVIDENCE_SUPPORTED"]["reward"]["equal_lifecycle_mean_utility"] == 0
    assert result["label_transitions"]["EVIDENCE"]["reward"]["counts"]["unresolved_to_positive"] == 5


def test_confirmation_cutoff_retains_candidates_without_supplying_labels():
    inputs, settings = _confirmation()
    inputs[0]["logs"][1].update(complete_block=False, pair_deltas={})
    result = ANALYSIS.diagnose_confirmation(inputs, settings)
    assert result["complete"]
    data = result["newly_positive_confirmation"]["EVIDENCE"]["reward"]
    assert data["newly_positive_candidates"] == 5 and data["complete_candidates"] == 4
    assert result["root_checks"][0]["complete_confirmation_roots"] == 1


def test_confirmation_or_heldout_data_cannot_expand_frozen_fit_replica_count():
    for defect in ("fit_replicas", "confirmation_roster", "heldout"):
        inputs, settings = _confirmation()
        data = inputs[0]
        if defect == "fit_replicas":
            data["updates"]["EVIDENCE"]["update"]["counts"]["paired_root_replicas_read"] += 16
        elif defect == "confirmation_roster":
            data["logs"].append(dict(root=data["roots"]["BASE"][2], complete_block=False, pair_deltas={}))
        else:
            data["roots"]["EVIDENCE"][2]["n_replicas"] = 16
        assert not ANALYSIS.diagnose_confirmation(inputs, settings)["complete"], defect


def test_unresolved_positive_confirmation_excludes_negative_to_positive_labels():
    inputs, settings = _confirmation()
    inputs[0]["roots"]["BASE"][0] = _root(0, [-1, 0, 0, 0], 8)
    result = ANALYSIS.diagnose_confirmation(inputs, settings)
    assert result["complete"]
    data = result["newly_positive_confirmation"]["EVIDENCE"]["reward"]
    assert data["newly_positive_candidates"] == 5
    subset = data["unresolved_to_positive"]
    assert subset["candidates"] == subset["complete_candidates"] == 4
    assert subset["independent_positive_means"] == 3
    assert subset["independent_status_counts"] == {"positive": 3, "negative": 1}
    assert subset["descriptive_mean_utility"] == 1
    assert sum(row["unresolved_to_positive"] for row in result["candidate_details"]
               if row["variant"] == "EVIDENCE") == 4
