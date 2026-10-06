"""Variable root coverage preserves the frozen paired learner's weight semantics."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_boundary_weighting_v97 import redistribute_weights
from acfqp.science.controlled_predictive_paired_bellman_value_v96 import QUERIES, fit_models


ROOT = Path(__file__).resolve().parents[1]
OPTIONS = ("SPACE_1", "SNAKE_1", "SPACE_4", "SNAKE_4")
EPISODES = (0, 3, 4, 5, 7, 8, 9, 10, 12, 13, 14)
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_root_coverage_learning_v98.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Small synthetic paired trees only; no source extraction or campaign.",
        ground_sampled_transitions=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def data(replicas=4):
    rows = []
    for query in QUERIES:
        for episode in EPISODES:
            for option_index, option in enumerate(OPTIONS):
                for replica in range(replicas):
                    for offset in range(3):
                        reference = [1] * 10 + [0] * 6
                        candidate = list(reference)
                        candidate[(episode + option_index + offset) % 10] = 2 + replica % 2
                        target = [1 + episode * .05 + option_index * .1 + replica * .05 + offset * .2,
                                  ((episode + option_index + replica) % 3) * .1,
                                  -((episode + option_index + replica) % 3) * .1]
                        next_candidate = list(candidate)
                        next_candidate[(episode + option_index + offset + 1) % 10] = 2
                        rows.append(dict(query=query, episode=episode, option=option, replica=replica,
                            step=4 + 16 * offset, weight=1 / 32,
                            candidate_board=candidate, reference_board=reference,
                            candidate_active=True, reference_active=True,
                            next_candidate_board=next_candidate, next_reference_board=list(reference),
                            next_candidate_active=offset < 2, next_reference_active=offset < 2,
                            target=target, n_target=target if offset == 2 else [target[0] / 3, 0, 0]))
    return rows


def fit(rows, cutoff):
    models, log = fit_models(rows, checkpoint=cutoff, iterations=2)
    LEDGER.update(log["counts"])
    return models, log


def compare_models(first, second, weight_scale=1):
    counts = Counter()
    probes = data()[:6]
    for name in ("PAIR_MC", "PAIR_FQE"):
        assert first[name].training_episodes == second[name].training_episodes
        for query in QUERIES:
            left, right = first[name].trees[query], second[name].trees[query]
            for field in left:
                if field == "weighted_samples":
                    np.testing.assert_array_equal(np.asarray(left[field]) * weight_scale, right[field])
                else:
                    assert left[field] == right[field]
            for row in probes:
                prediction = first[name].predict_pair(row["candidate_board"], row["reference_board"],
                    True, True, query, counts)
                assert prediction == second[name].predict_pair(row["candidate_board"], row["reference_board"],
                    True, True, query, counts)
    LEDGER.update({"comparison_" + key: value for key, value in counts.items()})


@pytest.mark.parametrize("replicas", (4, 8))
def test_variable_replica_groups_keep_the_fixed_boundary_mass_and_episode_units(replicas):
    original = data(replicas)
    before = deepcopy(original)
    weighted, log = redistribute_weights(original, checkpoint=8)
    eligible = [episode for episode in EPISODES if episode < 8 and episode % 5 != 4]
    expected_groups = len(QUERIES) * len(eligible) * len(OPTIONS) * replicas
    assert original == before
    assert log["counts"]["groups"] == expected_groups
    assert log["totals"]["prior_total_mass"] == log["totals"]["new_total_mass"] == expected_groups * 3 / 32
    assert log["totals"]["new_boundary_share"] == .5
    assert log["eligible_episodes"] == {query: eligible for query in QUERIES}
    for old, row in zip(original, weighted):
        if row["episode"] not in eligible:
            assert row == old
        else:
            assert row["weight"] == (3 / 64 if row["step"] == 4 else 3 / 128)
    # Alternative 1/(4R) normalization is one global scale within each arm.
    assert (1 / (4 * replicas)) / (1 / 32) == 8 / replicas


@pytest.fixture(scope="module", params=(8, 13))
def boundary_case(request):
    cutoff = request.param
    weighted, _ = redistribute_weights(data(), checkpoint=cutoff)
    baseline = fit(weighted, cutoff)
    normalized = [dict(row, weight=row["weight"] * 2) for row in weighted]
    scaled = fit(normalized, cutoff)
    poisoned = deepcopy(weighted)
    for row in poisoned:
        if row["episode"] >= cutoff or row["episode"] % 5 == 4:
            row.update(target=[1e8, -1e8, 1e8], n_target=[-1e8, 1e8, -1e8],
                       next_candidate_active=False, next_reference_active=False)
    excluded_changed = fit(poisoned, cutoff)
    return cutoff, baseline, scaled, excluded_changed


def test_boundary_mc_and_fixed_bellman_predictions_ignore_global_weight_scale(boundary_case):
    _, (baseline, log), (scaled, scaled_log), _ = boundary_case
    compare_models(baseline, scaled, weight_scale=2)
    assert log["counts"]["tree_fits"] == scaled_log["counts"]["tree_fits"] == 6
    assert log["PAIR_FQE"]["counts"]["tree_fits"] == 4
    assert log["PAIR_FQE"]["initialization"] == "PAIR_MC"


def test_arbitrary_episode_cutoffs_exclude_future_and_heldout_from_all_updates(boundary_case):
    cutoff, (baseline, log), _, (changed, changed_log) = boundary_case
    expected = [episode for episode in EPISODES if episode < cutoff and episode % 5 != 4]
    compare_models(baseline, changed)
    assert log["training_episodes"] == {query: expected for query in QUERIES}
    for query in QUERIES:
        assert log["heldout"]["queries"][query]["episodes"] == [
            episode for episode in EPISODES if episode < cutoff and episode % 5 == 4]
        assert log["heldout"]["queries"][query]["PAIR_MC"]["utility_mse"] != (
            changed_log["heldout"]["queries"][query]["PAIR_MC"]["utility_mse"])


def test_unweighted_paired_learner_has_the_same_global_normalization_invariance():
    original = data()
    baseline, _ = fit(original, 8)
    normalized, _ = fit([dict(row, weight=row["weight"] * 2) for row in original], 8)
    compare_models(baseline, normalized, weight_scale=2)


def test_runner_cumulative_rows_keep_uniform_and_boundary_fits_separate_and_load_both_ages(tmp_path, monkeypatch):
    specification = importlib.util.spec_from_file_location("coverage_runner_v98",
        ROOT / "scripts/run_controlled_predictive_root_coverage_v98.py")
    runner = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(runner)
    monkeypatch.setattr(runner, "BUDGETS", (20, 40))
    monkeypatch.setattr(runner.LearnedDynamics, "from_payload", lambda payload: object())
    acquisition_calls, fit_calls = [], []

    def acquire(life, replicas, rule, budget, cursor, folder):
        acquisition_calls.append((life, replicas, budget, cursor))
        episode, next_cursor = (0, 2) if cursor == 0 else (3, 8)
        batch = [row for row in data(replicas) if row["episode"] == episode]
        return batch, next_cursor, dict(completed_roots=[dict(query=q, episode=episode) for q in QUERIES],
            used_transitions=budget)

    class Frozen:
        family = "PAIR_FQE"
        def __init__(self, checkpoint, marker):
            self.checkpoint, self.marker = checkpoint, marker
        def to_payload(self):
            return dict(checkpoint=self.checkpoint, marker=self.marker, family=self.family)

    def learner(rows, checkpoint, iterations):
        fit_calls.append(dict(rows=deepcopy(rows), checkpoint=checkpoint, iterations=iterations))
        return {"PAIR_FQE": Frozen(checkpoint, len(fit_calls))}, dict(counts=dict(tree_fits=0))

    monkeypatch.setattr(runner, "acquire_batch", acquire)
    monkeypatch.setattr(runner, "fit_models", learner)
    result = runner.construct_allocation(9, 4, tmp_path, {})
    LEDGER.update(mock_acquisition_batches=len(acquisition_calls), mock_fit_calls=len(fit_calls))
    assert acquisition_calls == [(9, 4, 20, 0), (9, 4, 20, 2)]
    assert [call["checkpoint"] for call in fit_calls] == [2, 2, 5, 5]
    assert all(call["iterations"] == 128 for call in fit_calls)
    assert [len(call["rows"]) for call in fit_calls] == [96, 96, 192, 192]
    assert result["new_training_environment_transitions"] == 40
    for uniform, boundary in (fit_calls[:2], fit_calls[2:]):
        assert all(row["weight"] == 1 / 32 for row in uniform["rows"])
        assert all(row["weight"] == (3 / 64 if row["step"] == 4 else 3 / 128)
                   for row in boundary["rows"])
        assert [{k: v for k, v in row.items() if k != "weight"} for row in uniform["rows"]] == [
            {k: v for k, v in row.items() if k != "weight"} for row in boundary["rows"]]
    metadata = result["model_metadata"]
    assert len(metadata) == 4
    monkeypatch.setattr(runner, "METHODS", ("H2_ONLY",) + tuple(metadata))
    monkeypatch.setattr(runner.PairedBellmanValue, "from_payload",
        lambda payload: Frozen(payload["checkpoint"], payload["marker"]))
    deployed = {}
    def evaluate(life, budget, folder, values, rule):
        assert budget == 40
        deployed.update(values)
        return {}, [], []
    monkeypatch.setattr(runner, "evaluate_checkpoint", evaluate)
    monkeypatch.setattr(runner, "validate_roots", lambda *args: {})
    runner.lifecycle_evaluation(9, tmp_path, {}, [result])
    LEDGER.update(mock_evaluation_calls=1)
    assert deployed.pop("H2_ONLY") is None
    for name, model in deployed.items():
        frozen = name.endswith("_FROZEN_HALF")
        assert model.checkpoint == metadata[name]["episode_cutoff"] == (2 if frozen else 5)
        assert metadata[name]["budget"] == (20 if frozen else 40)
        assert model.marker == (1 if frozen else 3) + int("BOUNDARY" in name)
