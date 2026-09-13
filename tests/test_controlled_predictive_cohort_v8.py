import json

from acfqp.science.controlled_predictive_cohort_v7 import cases_v7
from acfqp.science.controlled_predictive_cohort_v8 import (
    build_cohort_roster_v8, cases_v8, freeze_cohort_roster_v8,
)


def test_primary_retains_all_frozen_v7_inputs_and_fit_roles():
    """A changed board or omitted regression would invalidate the paired comparison."""
    cases = cases_v8()
    assert cases == cases_v7()
    assert len(cases) == 16
    roster = build_cohort_roster_v8()
    primary = roster["scenarios"][0]
    assert primary["name"] == "PRIMARY_V7_SPLIT"
    assert primary["evaluation_case_names"] == [case.name for case in cases]
    assert primary["source_case_names"] == [case.name for case in cases if case.role == "TRAIN"]
    assert primary["case_splits"] == {case.name: case.split for case in cases}
    assert primary["target_family"] is None


def test_each_lofo_excludes_all_target_family_variants_from_encoder_sources():
    """A target-family source would leak into the intended family-fit holdout."""
    cases = {case.name: case for case in cases_v8()}
    roster = build_cohort_roster_v8()
    assert roster["scenario_count"] == 4
    assert roster["scenario_case_evaluation_count"] == 34
    target_names = []
    target_families = []
    for scenario in roster["scenarios"][1:]:
        family = scenario["target_family"]
        target_families.append(family)
        assert scenario["name"] == f"LOFO_{family}"
        sources = scenario["source_case_names"]
        assert len(sources) == 2
        assert all(cases[name].family != family and cases[name].role == "TRAIN" for name in sources)
        targets = [name for name, split in scenario["case_splits"].items() if split == "FAMILY_HELD_OUT"]
        assert targets == [name for name, case in cases.items() if case.family == family]
        assert len(targets) == 4
        assert not set(sources) & set(targets)
        assert scenario["evaluation_case_names"] == sources + targets
        assert len(set(scenario["evaluation_case_names"])) == 6
        target_names.extend(targets)
    assert len(set(target_families)) == 3
    assert len(target_names) == len(set(target_names)) == 12


def test_roster_records_pre_fit_status_and_historical_exposure(tmp_path):
    """Fit holdouts must not be described as new roots or a new research sample."""
    payload = build_cohort_roster_v8()
    assert not payload["v8_encoders_fitted_or_outcomes_evaluated"]
    assert payload["historical_exposure"] == "ALL_ROOTS_AND_FAMILIES_PREVIOUSLY_EXPOSED_IN_DEVELOPMENT"
    assert not payload["new_board_discovery_performed"]
    assert not payload["boards_or_symmetries_changed"]
    assert not payload["original_deferred_24_case_cohort_loaded_or_executed"]
    assert payload["target_empirical_kernels_used_for_model_compilation"]
    path = tmp_path / "roster.json"
    freeze_cohort_roster_v8(path)
    assert json.loads(path.read_text()) == json.loads(json.dumps(payload))
