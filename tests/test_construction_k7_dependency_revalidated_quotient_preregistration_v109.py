import copy

import pytest

from acfqp import construction_k7_dependency_revalidated_quotient_preregistration_v109 as v109


def test_v109_preregistration_is_outcome_free_and_keeps_validation_compute_separate():
    registration = v109.verify_dependency_revalidated_quotient_preregistration_v109(
        v109.freeze_dependency_revalidated_quotient_preregistration_v109()
    )
    document = registration.to_document()
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["construction_contract"][
        "reuse_requires_exact_dependency_slice_equality"
    ] is True
    assert document["construction_contract"][
        "cached_plan_is_only_an_action_ordering_heuristic"
    ] is True
    assert document["accounting_contract"]["no_scalar_cost_aggregation"] is True
    assert document["claim_boundary"]["registered_v109_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v109_preregistration_rejects_foreign_copy():
    registration = v109.freeze_dependency_revalidated_quotient_preregistration_v109()
    with pytest.raises(
        v109.ConstructionK7DependencyRevalidatedQuotientPreregistrationV109Error
    ):
        v109.verify_dependency_revalidated_quotient_preregistration_v109(
            copy.copy(registration)
        )
