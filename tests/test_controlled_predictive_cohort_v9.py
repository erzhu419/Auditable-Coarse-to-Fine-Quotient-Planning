import json

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v8 import cases_v8
from acfqp.science.controlled_predictive_cohort_v9 import (
    V8_ROSTER, build_cohort_roster_v9, cases_v9, freeze_cohort_roster_v9,
)


def test_v9_retains_exact_v8_inputs_source_roles_and_evaluation_assignments():
    """Changing a root or split would break the intended paired adaptation comparison."""
    source = json.loads((DEFAULT_REPORTS_DIR / V8_ROSTER).read_text())
    roster = build_cohort_roster_v9()
    assert cases_v9() == cases_v8()
    assert roster["cases"] == source["cases"]
    assert roster["scenarios"] == source["scenarios"]
    assert roster["case_count"] == 16
    assert roster["scenario_count"] == 4
    assert roster["scenario_case_evaluation_count"] == 34
    assert [(len(item["source_case_names"]), len(item["evaluation_case_names"]))
            for item in roster["scenarios"]] == [(3, 16), (2, 6), (2, 6), (2, 6)]


def test_scope_permits_target_adaptation_without_promoting_source_holdouts_to_unseen_roots(tmp_path):
    """Old fit-holdout labels must not hide the newly permitted target-data adaptation."""
    roster = build_cohort_roster_v9()
    assert roster["evaluation_target_data_adaptation_permitted"]
    assert roster["source_fit_roles_and_scenarios_unchanged"]
    assert not roster["v9_source_fits_target_adaptation_or_outcomes_evaluated"]
    assert roster["historical_exposure"] == "ALL_ROOTS_AND_FAMILIES_PREVIOUSLY_EXPOSED_IN_DEVELOPMENT"
    assert "excluded from adaptation" in roster["split_label_scope"]
    assert not roster["new_board_discovery_performed"]
    assert not roster["boards_or_symmetries_changed"]
    assert not roster["original_deferred_24_case_cohort_loaded_or_executed"]
    destination = tmp_path / "roster.json"
    freeze_cohort_roster_v9(destination)
    assert json.loads(destination.read_text()) == roster
