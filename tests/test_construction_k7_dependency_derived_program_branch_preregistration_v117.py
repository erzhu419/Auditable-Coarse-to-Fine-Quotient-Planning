import copy

import pytest

from acfqp import construction_k7_dependency_derived_program_branch_preregistration_v117 as pre


def test_v117_preregistration_is_frozen_before_outcomes():
    value = pre.freeze_dependency_derived_program_branch_preregistration_v117()
    document = value.to_document()
    assert document["preregistration_id"] == value.preregistration_id
    assert document["source_closure"][
        "frozen_before_any_registered_v117_target_outcome"
    ] is True
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["claim_boundary"]["registered_v117_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v117_preregistration_rejects_copy():
    value = pre.freeze_dependency_derived_program_branch_preregistration_v117()
    with pytest.raises(
        pre.ConstructionK7DependencyDerivedProgramBranchPreregistrationV117Error
    ):
        pre.verify_dependency_derived_program_branch_preregistration_v117(
            copy.copy(value)
        )
