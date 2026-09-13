import json

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v10 import cases_v10
from acfqp.science.controlled_predictive_cohort_v11 import (
    V10_ROSTER, build_cohort_roster_v11, cases_v11, freeze_cohort_roster_v11,
)


def test_block_runtime_preserves_exact_inputs_budget_queries_and_source_fit_scope():
    """Changed inputs would confound the fixed-block runtime comparison."""
    source = json.loads((DEFAULT_REPORTS_DIR / V10_ROSTER).read_text())
    roster = build_cohort_roster_v11()
    assert cases_v11() == cases_v10()
    for key in ("cases", "scenarios", "split_label_scope", "historical_exposure",
                "samples_per_action_row", "sample_seeds", "queries"):
        assert roster[key] == source[key]
    assert (roster["case_count"], roster["scenario_count"], roster["scenario_case_evaluation_count"]) == (16, 4, 34)
    assert roster["samples_per_action_row"] == 256
    assert roster["sample_seeds"] == [832101, 832102, 832103]
    assert len(roster["queries"]) == 10
    assert roster["evaluation_target_data_adaptation_permitted"]


def test_roster_freezes_block_structure_and_active_only_storage_before_outcomes(tmp_path):
    """A hidden cross-state cache would change the declared memory/computation scope."""
    roster = build_cohort_roster_v11()
    assert roster["paired_runtime_implementations"] == ["V9_EAGER", "V11_FIXED_FEATURE_BLOCKS"]
    assert roster["feature_block_sizes"] == [7, 6, 6, 6, 6]
    assert roster["intermediate_storage_scope"] == "ACTIVE_STATE_ONLY_PER_STATE"
    assert not any(roster[key] for key in ("all_state_board_cache", "cross_state_cache", "global_cache"))
    assert not roster["v11_runtime_comparison_or_outcomes_evaluated"]
    assert not roster["queries_changed"]
    assert not roster["boards_or_symmetries_changed"]
    assert not roster["original_deferred_24_case_cohort_loaded_or_executed"]
    path = tmp_path / "roster.json"
    freeze_cohort_roster_v11(path)
    assert json.loads(path.read_text()) == roster
