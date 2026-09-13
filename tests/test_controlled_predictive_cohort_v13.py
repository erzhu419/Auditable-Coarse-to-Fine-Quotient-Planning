import json

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v12 import cases_v12
from acfqp.science.controlled_predictive_cohort_v13 import (
    V12_ROSTER, build_cohort_roster_v13, cases_v13, freeze_cohort_roster_v13,
)


def test_v13_retains_all_roots_queries_and_primary_labels_without_source_or_lofo_duplicates():
    source = json.loads((DEFAULT_REPORTS_DIR / V12_ROSTER).read_text())
    primary = next(s for s in source["scenarios"] if s["name"] == "PRIMARY_V7_SPLIT")
    roster = build_cohort_roster_v13()
    assert cases_v13() == cases_v12()
    for key in ("cases", "sample_seeds", "queries", "historical_exposure"):
        assert roster[key] == source[key]
    assert roster["initial_query_order"] == list(source["queries"])
    assert roster["initial_query_order"][:2] == ["risk_0", "risk_0_05"]
    assert roster["historical_primary_case_splits"] == primary["case_splits"]
    assert roster["scenarios"] == [primary | {"source_case_names": []}]
    assert (roster["case_count"], roster["case_seed_count"], roster["query_execution_context_count"]) == (16, 48, 480)
    assert not roster["lofo_scenarios_reexecuted"]
    assert not roster["source_fitting_enabled"] and not roster["source_priority_enabled"]
    assert roster["source_fees"] == 0


def test_stage_separation_episode_budgets_and_unchanged_row_stream_are_frozen(tmp_path):
    roster = build_cohort_roster_v13()
    assert roster["initial_shared_row_cap"] == 32
    assert roster["total_episode_row_cap"] == 128
    assert roster["online_per_decision_quota"] == "(128 - observed_rows) // remaining_horizon"
    assert roster["samples_per_acquired_row"] == 256
    assert roster["row_stream"]["version"] == "V12_UNCHANGED"
    assert not roster["row_stream"]["cross_method_prewarming"]
    assert roster["stage_a"]["row_checkpoints"] == [32, 128]
    assert roster["stage_a"]["update_modes"] == ["full_recompute", "incremental"]
    assert roster["stage_b"]["execution_arms"] == ["upfront_full", "upfront_incremental", "online_full", "online_incremental"]
    assert roster["stage_b"]["reference_arms"] == ["frozen32", "full_state_empirical", "exact_empirical_quotient"]
    assert roster["single_active_query_for_upfront_and_online"]
    assert not roster["v13_target_acquisition_execution_or_outcomes_evaluated"]
    assert not roster["original_deferred_24_case_cohort_loaded_or_executed"]
    target = tmp_path / "roster.json"
    freeze_cohort_roster_v13(target)
    assert json.loads(target.read_text()) == roster
