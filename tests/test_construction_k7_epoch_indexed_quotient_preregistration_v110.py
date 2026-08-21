import copy

import pytest

from acfqp import construction_k7_epoch_indexed_quotient_preregistration_v110 as v110


def test_v110_preregistration_is_outcome_free_and_keeps_maintenance_axes_separate():
    registration = v110.verify_epoch_indexed_quotient_preregistration_v110(
        v110.freeze_epoch_indexed_quotient_preregistration_v110()
    )
    document = registration.to_document()
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["construction_contract"][
        "retained_cache_hits_do_not_rescan_dependency_rows"
    ] is True
    assert document["construction_contract"][
        "exact_query_local_certificate_remains_only_safety_authority"
    ] is True
    accounting = document["accounting_contract"]
    assert accounting["model_epoch_diff_checks_separate"] is True
    assert accounting["reverse_dependency_index_lookups_separate"] is True
    assert accounting["per_hit_dependency_validation_checks_separate"] is True
    assert accounting["no_scalar_cost_aggregation"] is True
    boundary = document["claim_boundary"]
    assert boundary["registered_v110_target_outcome_observed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v110_preregistration_rejects_foreign_copy():
    registration = v110.freeze_epoch_indexed_quotient_preregistration_v110()
    with pytest.raises(
        v110.ConstructionK7EpochIndexedQuotientPreregistrationV110Error
    ):
        v110.verify_epoch_indexed_quotient_preregistration_v110(
            copy.copy(registration)
        )
