"""Model ordering and label reproducibility use one complete-root cohort."""
from collections import Counter
import importlib.util
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("budget_allocation_diagnosis_v86",
    ROOT / "scripts/diagnose_controlled_predictive_budget_allocation_v86.py")
diagnosis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnosis)


class SyntheticSelector:
    def __init__(self, method):
        self.values = {"FROZEN_V85": [6.5, 5.5, 4.5, 3.5],
                       "COVERAGE": [3.5, 4.5, 5.5, 6.5], "REPEAT": [5.0] * 4}[method]

    def select(self, board, query, work):
        work["synthetic_selector_calls"] += 1
        predictions = dict(H2=dict(target=[0.0] * 3, value=0.0))
        predictions.update({option: dict(target=[value, 0.0, 0.0], value=value)
                            for option, value in zip(OPTIONS[1:], self.values)})
        choice, best = "H2", 0.0
        for option, prediction in predictions.items():
            if prediction["value"] > best:
                choice, best = option, prediction["value"]
        return dict(option=choice, value=best, predicted_advantage=predictions[choice]["target"],
                    predictions=predictions)


def entry(episode, first, second, complete=True):
    return dict(root=dict(board=[1] + [0] * 15, query="reward", episode=episode, step=30),
        complete_block=complete,
        pair_deltas={option: [[a, 0.0, 0.0]] * 8 + ([[b, 0.0, 0.0]] * 8 if complete else [])
                     for option, a, b in zip(OPTIONS[1:], first, second)},
        outcomes={"LOST": 80} if complete else {"LOST": 40, "CUTOFF": 1})


def test_common_complete_roots_mean_invariance_and_split_half_noise():
    entries = [entry(1004, [4, 3, 2, 1], [1, 2, 3, 4]),
               entry(1009, [-4, -3, -2, -1], [-4, -3, -2, -1]),
               entry(1014, [900] * 4, [900] * 4, complete=False),
               dict(root=dict(query="reward", episode=1019, board=None),
                    complete_block=False, pair_deltas={})]
    models = {method: SyntheticSelector(method) for method in diagnosis.MODEL_FILES}
    counts = Counter()
    summaries, witnesses, excluded = diagnosis.diagnose_entries(entries, models, 99, counts)
    summary = next(row for row in summaries if row["query"] == "reward")
    assert summary["complete_roots"] == 2 and summary["excluded_roots"] == 2
    assert excluded[0]["root"]["episode"] == 1014 and excluded[0]["replica_counts"] == {
        option: 8 for option in OPTIONS[1:]}
    assert excluded[1]["reason"] == "source_missing_trigger"
    assert excluded[1]["root"]["board"] is None
    assert len(witnesses) == 2 and all(row["root"]["episode"] != 1014 for row in witnesses)
    stability = summary["split_half_reference_stability"]
    assert stability["pairs"] == stability["both_strict_pairs"] == 12
    assert stability["same_strict_order"] == stability["strict_sign_reversals"] == 6
    assert stability["strict_order_agreement"] == 0.5
    duration = summary["split_half_duration_stability"]
    assert duration["pairs"] == 4 and duration["same_strict_order"] == duration["strict_sign_reversals"] == 2
    coverage = summary["methods"]["COVERAGE"]
    frozen = summary["methods"]["FROZEN_V85"]
    repeat = summary["methods"]["REPEAT"]
    assert coverage["candidate_ranking"]["observed_ties"] == 6
    assert coverage["candidate_ranking"]["strict_observed_pairs"] == 6
    assert coverage["candidate_ranking"]["observed_strict_order_accuracy"] == 1
    assert frozen["candidate_ranking"]["observed_strict_order_accuracy"] == 0
    assert repeat["candidate_ranking"]["predicted_ties_on_strict_observed_pairs"] == 6
    assert coverage["same_primitive_duration_ranking"]["observed_strict_order_accuracy"] == 1
    assert coverage["observed_selected_utility_mean"] == 0.75
    assert frozen["observed_selected_utility_mean"] == -0.75
    assert coverage["negative_interventions"] == frozen["negative_interventions"] == 1
    assert coverage["selection_disagreements_with_frozen"] == 2
    for method in summary["methods"].values():
        assert method["roots"] == 2 and method["max_mean_prediction_discrepancy"] == 0
        assert method["full_candidate_mse_components"] == pytest.approx([
            a + b for a, b in zip(method["anchor_mean_squared_error_components"],
                                  method["centered_residual_mse_components"])])
    noisy = witnesses[0]
    assert noisy["retained_mean_targets"]["SPACE_1"] == [2.5, 0.0, 0.0]
    assert noisy["first_half_mean_targets"]["SPACE_1"] == [4, 0.0, 0.0]
    assert noisy["second_half_mean_targets"]["SPACE_1"] == [1, 0.0, 0.0]
    assert noisy["retained_mean_targets"]["H2"] == [0.0] * 3
    assert counts == dict(validation_root_records_read=4, retained_delta_vectors_read=160,
                         synthetic_selector_calls=6)
