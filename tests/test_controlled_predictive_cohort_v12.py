import json

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v11 import cases_v11
from acfqp.science.controlled_predictive_cohort_v12 import (
    V11_ROSTER, build_cohort_roster_v12, cases_v12, freeze_cohort_roster_v12,
)


def test_v12_preserves_roots_scenarios_and_queries_but_uses_all_queries_for_construction():
    source = json.loads((DEFAULT_REPORTS_DIR / V11_ROSTER).read_text())
    roster = build_cohort_roster_v12()
    assert cases_v12() == cases_v11()
    for key in ("cases", "scenarios", "historical_exposure", "queries", "sample_seeds"):
        assert roster[key] == source[key]
    assert (roster["case_count"], roster["scenario_count"], roster["scenario_case_evaluation_count"]) == (16, 4, 34)
    assert len(roster["query_roles"]) == 10
    assert set(roster["query_roles"].values()) == {"CONSTRUCTION_AND_EVALUATION"}
    assert roster["probe_or_query_holdout_roles"] == []


def test_nested_acquisition_budgets_and_prior_only_information_scope_are_frozen(tmp_path):
    roster = build_cohort_roster_v12()
    assert roster["row_budgets"] == [8, 32, 128]
    assert roster["budgets_are_nested"]
    assert roster["samples_per_acquired_row"] == 256
    assert roster["partial_arms"] == ["bfs", "query_interval", "source_priority", "shuffled_source_priority"]
    assert roster["full_row_benchmark_arms"] == ["full_state_empirical", "exact_empirical_quotient"]
    assert not roster["v12_source_fits_partial_acquisition_or_outcomes_evaluated"]
    assert not roster["original_deferred_24_case_cohort_loaded_or_executed"]
    destination = tmp_path / "roster.json"
    freeze_cohort_roster_v12(destination)
    assert json.loads(destination.read_text()) == roster
