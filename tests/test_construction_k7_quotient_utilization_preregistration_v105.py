import copy

import pytest

from acfqp import construction_k7_quotient_utilization_preregistration_v105 as v105


def test_v105_preregistration_is_outcome_free_and_source_closed():
    registration = v105.verify_quotient_utilization_preregistration_v105(
        v105.freeze_quotient_utilization_preregistration_v105()
    )
    document = registration.to_document()
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["construction_contract"][
        "observation_derived_projected_graph_enters_real_engine_action_order"
    ] is True
    assert document["claim_boundary"]["registered_v105_target_outcome_observed"] is False
    assert document["claim_boundary"]["complete_ground_world_model_synthesized"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v105_preregistration_rejects_foreign_copy():
    registration = v105.freeze_quotient_utilization_preregistration_v105()
    with pytest.raises(v105.ConstructionK7QuotientUtilizationPreregistrationV105Error):
        v105.verify_quotient_utilization_preregistration_v105(
            copy.copy(registration)
        )
