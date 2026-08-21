import copy

import pytest

from acfqp import construction_k7_memoized_catalogue_quotient_preregistration_v108 as v108


def test_v108_preregistration_is_outcome_free_and_keeps_cost_axes_separate():
    registration = v108.verify_memoized_catalogue_quotient_preregistration_v108(
        v108.freeze_memoized_catalogue_quotient_preregistration_v108()
    )
    document = registration.to_document()
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["construction_contract"][
        "memoized_and_no_cache_actions_receipts_and_labels_must_match_exactly"
    ] is True
    assert document["registered_gate"][
        "every_occurrence_planning_compute_strictly_reduced"
    ] is True
    assert document["accounting_contract"]["no_scalar_cost_aggregation"] is True
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v108_preregistration_rejects_foreign_copy():
    registration = v108.freeze_memoized_catalogue_quotient_preregistration_v108()
    with pytest.raises(
        v108.ConstructionK7MemoizedCatalogueQuotientPreregistrationV108Error
    ):
        v108.verify_memoized_catalogue_quotient_preregistration_v108(
            copy.copy(registration)
        )
