"""Fixed-cohort replay uncertainty counts each shared training root once."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("leaf_replay_analysis_v90",
    ROOT / "scripts/analyze_controlled_predictive_leaf_replay_v90.py")
ANALYZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZER)


def fixture():
    values = {"t0": [-3., -1.], "t1": [-1., 1.], "t2": [-5., -3.],
        "c0": [1., 3.], "c1": [-1., 1.], "c2": [3., 5.]}
    roots = [dict(id=name, kind="target" if name.startswith("t") else "training",
        life=0 if name in ("t0", "t1", "c0") else 2, query="reward", leaf=4,
        option="SNAKE_4", board=[1, 0] * 8, v89_utility_delta=-2552 / 2048,
        v89_score_delta=-2552) for name in values]
    cohort = dict(targets=[root for root in roots if root["kind"] == "target"],
        controls=[root for root in roots if root["kind"] == "training"], checks={"frozen": True}, groups=[])
    for life, targets, training in ((0, ["t0", "t1"], ["c0"]), (2, ["t2"], ["c1", "c2"])):
        cohort["groups"].append(dict(id=f"life_{life}_reward_leaf_4", life=life, query="reward", leaf=4,
            option="SNAKE_4", target_ids=targets, training_ids=training,
            predicted_target=[5., 0., 0.], predicted_utility=5., positive_fraction=1.))
    logs = []
    for index, (root_id, utilities) in enumerate(values.items()):
        logs.append(dict(root_id=root_id, requested_replicas=2, complete_pairs=2,
            pairs=[dict(replica=replica, seed=10000 + index * 100 + replica, complete_pair=True,
                target=[utility, 0., 0.], candidate_status="LOST", reference_status="LOST")
                for replica, utility in enumerate(utilities)],
            ground_work={"sampled_transitions": 24}, planning_counts={"model_uniform_draws": 96},
            outcomes={"LOST": 4}, trajectories=4, seconds=1.,
            wiring={key: True for key in ANALYZER.WIRING}))
    run = dict(status="complete", settings={"replicas": 2, "max_steps": 10, "workers": 3},
        roots=logs, actual_wall_seconds=4., inherited={"v89_transitions": 12345})
    return run, cohort


def test_shared_controls_have_unique_weights_and_variance():
    run, cohort = fixture()
    result = ANALYZER.analyze_run(run, cohort)
    assert result["complete"] and result["primary_estimable"]
    overall = result["overall"]
    assert overall["target_weights"] == pytest.approx({"t0": 1 / 3, "t1": 1 / 3, "t2": 1 / 3})
    assert overall["training_weights"] == pytest.approx({"c0": 2 / 3, "c1": 1 / 6, "c2": 1 / 6})
    assert overall["target"]["mean_utility"] == pytest.approx(-2.)
    assert overall["target"]["variance_of_mean"] == pytest.approx(1 / 3)
    assert overall["training"]["mean_utility"] == pytest.approx(2.)
    assert overall["training"]["variance_of_mean"] == pytest.approx(1 / 2)
    assert overall["difference"]["mean_utility"] == pytest.approx(-4.)
    assert overall["difference"]["variance_of_mean"] == pytest.approx(5 / 6)
    assert overall["difference"]["standard_error"] == pytest.approx((5 / 6) ** .5)
    assert overall["opposite_mean_signs"]
    assert overall["opposite_two_se_signs"]
    assert overall["target"]["mean_score_delta"] == pytest.approx(-4096.)
    assert overall["training"]["roots"] == 3


def test_opposite_signs_also_detect_positive_targets_and_negative_training():
    run, cohort = fixture()
    for root in run["roots"]:
        for pair in root["pairs"]:
            pair["target"][0] *= -1
    result = ANALYZER.analyze_run(run, cohort)
    assert result["complete"] and result["primary_estimable"]
    overall = result["overall"]
    assert overall["target"]["mean_utility"] == pytest.approx(2.)
    assert overall["training"]["mean_utility"] == pytest.approx(-2.)
    assert overall["opposite_mean_signs"]
    assert overall["opposite_two_se_signs"]


def test_equal_leaf_numbers_stay_separate_across_lives():
    run, cohort = fixture()
    result = ANALYZER.analyze_run(run, cohort)
    groups = {group["life"]: group for group in result["groups"]}
    assert set(groups) == {0, 2}
    assert groups[0]["leaf"] == groups[2]["leaf"] == 4
    assert groups[0]["target"]["mean_utility"] == -1.
    assert groups[2]["target"]["mean_utility"] == -4.
    assert groups[0]["target"]["variance_of_mean"] == pytest.approx(.5)
    assert groups[2]["training"]["variance_of_mean"] == pytest.approx(.5)
    cohort["groups"][1]["training_ids"] = ["c0", "c2"]
    result = ANALYZER.analyze_run(run, cohort)
    assert not result["complete"]
    assert not result["cohort_checks"]["life_specific_leaf_groups"]


def test_cutoff_keeps_cost_but_does_not_drop_root_from_primary():
    run, cohort = fixture()
    row = next(row for row in run["roots"] if row["root_id"] == "c0")
    row["pairs"][1].update(complete_pair=False, target=None, candidate_status="CUTOFF")
    row.update(complete_pairs=1, outcomes={"LOST": 3, "CUTOFF": 1})
    result = ANALYZER.analyze_run(run, cohort)
    assert result["complete"]
    assert not result["primary_estimable"]
    assert not result["overall"]["estimable"]
    assert result["overall"]["training"] is None
    assert result["overall"]["difference"] is None
    assert result["overall"]["training_weights"]["c0"] == pytest.approx(2 / 3)
    affected = next(row for row in result["root_statistics"] if row["id"] == "c0")
    assert affected["estimate"] is None
    assert affected["complete_pairs_descriptive"]["n"] == 1
    assert result["work"]["sampled_transitions"] == 144
    assert result["work"]["trajectories"] == 24
    assert result["work"]["incomplete_pairs"] == 1
    assert result["work"]["outcomes"]["CUTOFF"] == 1


def test_complete_roster_counts_and_model_draws_detect_execution_mismatch():
    run, cohort = fixture()
    result = ANALYZER.analyze_run(run, cohort)
    assert result["work"]["planned_trajectories"] == 24
    assert result["work"]["complete_pairs"] == result["work"]["requested_pairs"] == 12
    assert result["work"]["new_tree_fits"] == result["work"]["new_source_games"] == 0
    assert result["inherited"] == {"v89_transitions": 12345}
    run["roots"][0]["planning_counts"]["model_uniform_draws"] -= 1
    result = ANALYZER.analyze_run(run, cohort)
    assert not result["complete"]
    assert not result["cohort_checks"]["transition_and_model_draw_counts_match"]


def test_reusing_suffix_seed_across_roots_invalidates_independence():
    run, cohort = fixture()
    run["roots"][1]["pairs"][0]["seed"] = run["roots"][0]["pairs"][0]["seed"]
    result = ANALYZER.analyze_run(run, cohort)
    assert not result["complete"]
    assert not result["cohort_checks"]["independent_root_seed_rosters"]


def test_selected_old_outcomes_never_enter_fresh_estimates():
    run, cohort = fixture()
    before = ANALYZER.analyze_run(run, cohort)
    changed = deepcopy(cohort)
    for root in changed["targets"]:
        root["v89_utility_delta"] = 1000.
        root["v89_score_delta"] = 2048000.
    after = ANALYZER.analyze_run(run, changed)
    assert before["overall"]["target"] == after["overall"]["target"]
    assert before["overall"]["training"] == after["overall"]["training"]
    assert before["overall"]["difference"] == after["overall"]["difference"]
    assert before["overall"]["old_v89_selected_target_mean_score_delta"] == -2552.
    assert after["overall"]["old_v89_selected_target_mean_score_delta"] == 2048000.
