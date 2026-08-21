import copy

import pytest

from acfqp import construction_k7_legality_conditioned_quotient_preregistration_v106 as v106


def test_v106_preregistration_is_outcome_free_and_source_closed():
    registration = v106.verify_legality_conditioned_quotient_preregistration_v106(
        v106.freeze_legality_conditioned_quotient_preregistration_v106()
    )
    document = registration.to_document()
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["construction_contract"][
        "certified_legality_visible_to_abstract_planner_as_initial_action_constraint"
    ] is True
    assert document["construction_contract"][
        "ground_transition_accessed_during_abstract_search"
    ] is False
    assert document["registered_gate"][
        "every_occurrence_quotient_orders_at_least_three_quarters_of_actions"
    ] is True
    assert document["claim_boundary"]["registered_v106_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v106_preregistration_rejects_foreign_copy():
    registration = v106.freeze_legality_conditioned_quotient_preregistration_v106()
    with pytest.raises(
        v106.ConstructionK7LegalityConditionedQuotientPreregistrationV106Error
    ):
        v106.verify_legality_conditioned_quotient_preregistration_v106(
            copy.copy(registration)
        )
