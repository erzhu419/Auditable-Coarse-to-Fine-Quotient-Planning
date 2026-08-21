import pytest

from acfqp.construction_k7_applicability_target_preregistration_v87 import (
    ConstructionK7ApplicabilityTargetPreregistrationV87Error,
    TARGET_SEEDS,
    freeze_applicability_target_preregistration_v87,
    verify_applicability_target_preregistration_v87,
)


def test_v87_preregistration_fixes_fresh_targets_and_primary_ordering_gate():
    document = freeze_applicability_target_preregistration_v87().to_document()
    assert document["identity_contract"]["target_seeds"] == list(TARGET_SEEDS)
    assert document["source_closure"][
        "frozen_before_any_registered_v87_target_outcome"
    ] is True
    gate = document["registered_gate"]
    assert gate[
        "every_successful_abstract_output_must_be_accepted_as_legal"
    ] is True
    assert gate[
        "accepted_abstract_orderings_must_cover_every_execution_step"
    ] is True
    assert gate["target_sample_reduction_required"] is False
    boundary = document["claim_boundary"]
    assert boundary["multi_step_planning_primarily_in_abstract_model_claimed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v87_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7ApplicabilityTargetPreregistrationV87Error):
        verify_applicability_target_preregistration_v87(object())
