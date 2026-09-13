from dataclasses import asdict
import json

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v9 import cases_v9
from acfqp.science.controlled_predictive_cohort_v10 import (
    V9_ROSTER, build_cohort_roster_v10, cases_v10, freeze_cohort_roster_v10,
)
from acfqp.science.controlled_predictive_comparison_v3 import COMPARISON_QUERIES, PROBE_QUERIES


def test_runtime_comparison_keeps_exact_v9_roots_scenarios_and_information_scope():
    """A changed cohort or target-data permission would confound runtime attribution."""
    source = json.loads((DEFAULT_REPORTS_DIR / V9_ROSTER).read_text())
    roster = build_cohort_roster_v10()
    assert cases_v10() == cases_v9()
    assert roster["cases"] == source["cases"]
    assert roster["scenarios"] == source["scenarios"]
    assert roster["split_label_scope"] == source["split_label_scope"]
    assert roster["historical_exposure"] == source["historical_exposure"]
    assert (roster["case_count"], roster["scenario_count"], roster["scenario_case_evaluation_count"]) == (16, 4, 34)
    assert roster["evaluation_target_data_adaptation_permitted"]
    assert roster["source_fit_roles_and_scenarios_unchanged"]


def test_runtime_pair_budget_and_queries_are_frozen_before_outcomes(tmp_path):
    """Different observations or query weights would cease to be a runtime-only comparison."""
    roster = build_cohort_roster_v10()
    assert roster["comparison_scope"] == "RUNTIME_OPTIMIZATION_ONLY"
    assert roster["paired_runtime_implementations"] == ["V9_EAGER", "V10_LAZY"]
    assert roster["samples_per_action_row"] == 256
    assert roster["sample_seeds"] == [832101, 832102, 832103]
    assert roster["queries"] == {name: asdict(query) for name, query in {**COMPARISON_QUERIES, **PROBE_QUERIES}.items()}
    assert len(roster["queries"]) == 10
    assert not roster["queries_changed"]
    assert not roster["v10_runtime_comparison_or_outcomes_evaluated"]
    assert not roster["boards_or_symmetries_changed"]
    assert not roster["original_deferred_24_case_cohort_loaded_or_executed"]
    path = tmp_path / "roster.json"
    freeze_cohort_roster_v10(path)
    assert json.loads(path.read_text()) == roster
