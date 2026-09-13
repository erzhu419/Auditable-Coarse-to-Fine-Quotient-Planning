from collections import Counter
import json

from acfqp.science.controlled_predictive_challenges_v6 import declared_cases_v6
from acfqp.science.controlled_predictive_cohort_v7 import (
    build_cohort_roster_v7, cases_v7, freeze_cohort_roster_v7,
)
from acfqp.science.controlled_predictive_comparison_v3 import refinement_cases


def test_all_frozen_v6_inputs_and_h2_are_retained_with_input_only_fit_roles():
    """An omitted case or a fitted holdout would change the intended denominator."""
    cases = cases_v7()
    original = declared_cases_v6()
    assert len(cases) == 16
    assert [(case.name, case.board, case.horizon) for case in cases[:15]] == [
        (case.name, case.board, case.horizon) for case in original]
    assert (cases[-1].name, cases[-1].board, cases[-1].horizon) == (
        refinement_cases()[0].name, refinement_cases()[0].board, 2)
    assert Counter(case.role for case in cases) == {
        "TRAIN": 3, "VALIDATION_DIAGNOSTIC": 3,
        "FIT_HELD_OUT_DEVELOPMENT": 6, "EXPOSED_REGRESSION": 4,
    }
    for case in cases[:12]:
        index = int(case.name.rsplit("_", 1)[1])
        assert case.role == ["TRAIN", "VALIDATION_DIAGNOSTIC",
                             "FIT_HELD_OUT_DEVELOPMENT", "FIT_HELD_OUT_DEVELOPMENT"][index]


def test_frozen_roster_distinguishes_fit_holdouts_from_unseen_research(tmp_path):
    """Labeling previously studied roots as unseen would overstate transfer evidence."""
    roster = build_cohort_roster_v7()
    assert roster["historical_exposure"] == "ALL_ROOTS_PREVIOUSLY_EXPOSED_IN_DEVELOPMENT"
    assert not roster["encoder_fitted_or_v7_outcomes_evaluated"]
    assert not roster["validation_used_for_model_selection"]
    assert not roster["new_board_discovery_performed"]
    assert not roster["original_deferred_24_case_cohort_loaded_or_executed"]
    assert roster["all_declared_cases_retained"]
    path = tmp_path / "roster.json"
    freeze_cohort_roster_v7(path)
    assert json.loads(path.read_text()) == json.loads(json.dumps(roster))
