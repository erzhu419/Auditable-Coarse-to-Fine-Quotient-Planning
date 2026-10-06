"""Shared shifts change H2 gates while preserving exact source candidate ranks."""
from collections import Counter
import importlib.util
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("mean_update_diagnosis_v87",
    ROOT / "scripts/diagnose_controlled_predictive_mean_update_v87.py")
diagnosis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnosis)


class SyntheticSelector:
    def __init__(self, updated):
        self.updated = updated

    def select(self, board, query, work):
        work["synthetic_selector_calls"] += 1
        index = board[0]
        base = [-1, -2, -3, -4] if index in (1, 3) else [1, 0, -1, -2]
        shift = {1: 2, 2: -2, 3: -1, 4: 1}[index] if self.updated else 0
        predictions = {"H2": dict(target=[0.0] * 3, value=0.0)}
        if self.updated:
            predictions["H2"]["ranking_value"] = 0.0
        for option, original in zip(OPTIONS[1:], base):
            predictions[option] = dict(target=[original + shift, 0.0, 0.0], value=original + shift)
            if self.updated:
                predictions[option]["ranking_value"] = original
        winner = OPTIONS[1]
        selected = winner if predictions[winner]["value"] > 0 else "H2"
        return dict(option=selected, value=predictions[selected]["value"],
                    predicted_advantage=predictions[selected]["target"], predictions=predictions)


def test_mean_error_gate_changes_ranking_invariance_and_common_exclusion():
    entries = [dict(root=dict(board=[index] + [0] * 15, query="reward", episode=1004 + index * 5),
                    complete_block=True, pair_deltas={option: [[value, 0.0, 0.0]] * 16
                        for option, value in zip(OPTIONS[1:], [0.5, 0.0, -0.5, -1.0])})
               for index in range(1, 5)]
    entries.append(dict(root=dict(board=None, query="reward", episode=1034),
                        complete_block=False, pair_deltas={}))
    selectors = {method: SyntheticSelector(method.endswith("_MEAN")) for method in diagnosis.MODEL_FILES}
    counts = Counter()
    witnesses, excluded = diagnosis.diagnose_entries(entries, selectors, 99, counts)
    summary = diagnosis.summarize(witnesses, excluded, "reward", "all")
    assert summary["complete_roots"] == 4 and summary["excluded_roots"] == 1
    assert excluded[0]["reason"] == "source_missing_trigger"
    for family in diagnosis.FAMILIES:
        comparison = summary["comparisons"][family]
        assert comparison["max_candidate_pair_vector_difference_change"] == 0
        assert comparison["exact_original_ranking_disagreements"] == 0
        assert comparison["original_ranking_value_mismatches"] == 0
        assert comparison["non_h2_winner_disagreements"] == 0
        assert comparison["max_residual_mse_change"] == 0
        assert {name: group["roots"] for name, group in comparison["gates"].items()} == {
            "enabled": 1, "disabled": 1, "both_h2": 1, "same_fragment": 1}
        assert comparison["gates"]["enabled"]["observed_utility_delta_vs_old_mean"] == 0.5
        assert comparison["gates"]["enabled"]["updated_observed_utility_vs_h2_mean"] == 0.5
        assert comparison["gates"]["disabled"]["observed_utility_delta_vs_old_mean"] == -0.5
        assert comparison["gates"]["disabled"]["updated_observed_utility_vs_h2_mean"] == 0
        old = summary["methods"][family + "_OLD"]
        updated = summary["methods"][family + "_MEAN"]
        assert old["centered_residual_mse_components"] == updated["centered_residual_mse_components"]
        assert old["original_candidate_ranking"] == updated["original_candidate_ranking"]
    before = witnesses[0]["methods"]["COVERAGE_OLD"]
    after = witnesses[0]["methods"]["COVERAGE_MEAN"]
    assert before["option"] == "H2" and after["option"] == "SPACE_1"
    assert before["mean_estimation_error"] == [-2.25, 0.0, 0.0]
    assert after["mean_estimation_error"] == [-0.25, 0.0, 0.0]
    for choice in (before, after):
        assert choice["full_candidate_mse_components"] == pytest.approx([
            a * a + b for a, b in zip(choice["mean_estimation_error"], choice["centered_residual_mse_components"])])
    assert counts == dict(retained_root_records_read=5, retained_delta_vectors_read=256,
                         synthetic_selector_calls=16)
