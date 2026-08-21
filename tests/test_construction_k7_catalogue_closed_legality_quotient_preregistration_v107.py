import copy

import pytest

from acfqp import construction_k7_catalogue_closed_legality_quotient_preregistration_v107 as v107


def test_v107_preregistration_is_outcome_free_source_closed_and_retains_v106():
    registration = (
        v107.verify_catalogue_closed_legality_quotient_preregistration_v107(
            v107.freeze_catalogue_closed_legality_quotient_preregistration_v107()
        )
    )
    document = registration.to_document()
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["frozen_failed_predecessor"]["v106_registered_gate_passed"] is False
    assert document["construction_contract"][
        "complete_anonymous_action_catalogue_is_outcome_free_planner_input"
    ] is True
    assert document["construction_contract"][
        "certificate_local_legality_may_be_absent_when_preloaded_support_suffices"
    ] is True
    assert document["claim_boundary"]["registered_v107_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v107_preregistration_rejects_foreign_copy():
    registration = v107.freeze_catalogue_closed_legality_quotient_preregistration_v107()
    with pytest.raises(
        v107.ConstructionK7CatalogueClosedLegalityQuotientPreregistrationV107Error
    ):
        v107.verify_catalogue_closed_legality_quotient_preregistration_v107(
            copy.copy(registration)
        )
