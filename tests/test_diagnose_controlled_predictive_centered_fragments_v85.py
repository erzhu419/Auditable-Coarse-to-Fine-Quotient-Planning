"""Invariant common means can coexist with changed and improved option ranking."""
from collections import Counter
import importlib.util
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("centered_fragment_diagnosis_v85",
    ROOT / "scripts/diagnose_controlled_predictive_centered_fragments_v85.py")
diagnosis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnosis)


class SyntheticSelector:
    def __init__(self, centered):
        self.centered = centered

    def select(self, board, query, allowed=None, work=None):
        work["synthetic_selector_calls"] += 1
        rewards = [3.5, 4.5, 5.5, 6.5] if self.centered else [6.5, 5.5, 4.5, 3.5]
        predictions = dict(H2=dict(target=[0.0] * 3, value=0.0))
        for option, reward in zip(OPTIONS[1:], rewards):
            if allowed is None or option in allowed:
                target = [reward, 0.25, 0.1]
                predictions[option] = dict(target=target, value=diagnosis.utility(target, query))
        chosen, best = "H2", 0.0
        for option, prediction in predictions.items():
            if prediction["value"] > best:
                chosen, best = option, prediction["value"]
        return dict(option=chosen, value=best, predicted_advantage=predictions[chosen]["target"],
                    predictions=predictions)


def test_common_mean_residual_decomposition_and_ranking_disagreement():
    rows = [dict(query="reward", episode=episode, board=[1] + [0] * 15,
                 option=option, target=[value, 0.0, 0.0])
            for episode, observed in ((0, [1, 2, 3, 4]), (4, [-4, -3, -2, -1]))
            for option, value in zip(OPTIONS[1:], observed)]
    counts = Counter()
    summaries, witnesses = diagnosis.diagnose_rows(rows, SyntheticSelector(True),
        SyntheticSelector(False), 99, 6, counts)
    train = next(row for row in summaries if row["query"] == "reward" and row["split"] == "training")
    held = next(row for row in summaries if row["query"] == "reward" and row["split"] == "heldout")
    assert train["roots"] == held["roots"] == 1
    assert train["max_mean_prediction_discrepancy"] == 0
    assert train["max_mean_prediction_discrepancy_components"] == [0.0] * 3
    assert train["anchor_mean_estimation_error_mean"] == pytest.approx([2.5, 0.25, 0.1])
    assert train["anchor_mean_squared_error_components"] == pytest.approx([6.25, 0.0625, 0.01])
    centered = train["methods"]["CENTERED"]
    joint = train["methods"]["JOINT"]
    one = train["methods"]["CENTERED_ONE_STEP"]
    assert centered["centered_residual_mse_components"] == pytest.approx([0.0] * 3)
    assert joint["centered_residual_mse_components"] == pytest.approx([5.0, 0.0, 0.0])
    for method in (centered, joint):
        assert method["full_candidate_mse_components"] == pytest.approx([
            a + b for a, b in zip(train["anchor_mean_squared_error_components"],
                                  method["centered_residual_mse_components"])])
    assert centered["selected_options"] == {"SNAKE_4": 1}
    assert joint["selected_options"] == {"SPACE_1": 1}
    assert one["selected_options"] == {"SNAKE_1": 1}
    assert centered["observed_selected_utility_mean"] == 4
    assert joint["observed_selected_utility_mean"] == 1
    assert one["observed_selected_utility_mean"] == 2
    assert centered["candidate_ranking"]["observed_strict_order_accuracy"] == 1
    assert joint["candidate_ranking"]["observed_strict_order_accuracy"] == 0
    assert centered["ranking_disagreements_with_joint"] == 6
    assert centered["duration_ranking_disagreements_with_joint"] == 2
    assert centered["selection_disagreements_with_joint"] == 1
    assert centered["same_primitive_duration_ranking"]["concordant"] == 2
    assert one["candidate_ranking"] == centered["candidate_ranking"]
    assert held["methods"]["CENTERED"]["negative_interventions"] == 1
    witness = next(row for row in witnesses if row["episode"] == 0)
    assert witness["anchor_candidate_prediction_mean"] == pytest.approx([5.0, 0.25, 0.1])
    assert witness["observed_candidate_mean"] == [2.5, 0.0, 0.0]
    assert witness["retained_mean_targets"]["H2"] == [0.0] * 3
    assert witness["methods"]["CENTERED_ONE_STEP"]["candidate_pairs"] == witness["methods"]["CENTERED"]["candidate_pairs"]
    assert counts == dict(retained_option_rows_read=8, synthetic_selector_calls=6)
