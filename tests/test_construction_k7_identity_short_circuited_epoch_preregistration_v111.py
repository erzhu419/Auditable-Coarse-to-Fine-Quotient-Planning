import copy

import pytest

from acfqp import construction_k7_identity_short_circuited_epoch_preregistration_v111 as v111


def test_v111_preregistration_is_outcome_free_and_separates_all_axes():
    registration = v111.verify_identity_short_circuited_epoch_preregistration_v111(
        v111.freeze_identity_short_circuited_epoch_preregistration_v111()
    )
    document = registration.to_document()
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["construction_contract"][
        "same_graph_identity_skips_full_graph_and_dependency_scan"
    ] is True
    assert document["construction_contract"][
        "exact_query_local_certificate_remains_only_safety_authority"
    ] is True
    accounting = document["accounting_contract"]
    assert accounting["model_epoch_identity_checks_separate"] is True
    assert accounting["full_model_epoch_diff_checks_separate"] is True
    assert accounting["reverse_dependency_index_lookups_separate"] is True
    assert accounting["per_hit_dependency_validation_checks_separate"] is True
    assert accounting["no_scalar_cost_aggregation"] is True
    boundary = document["claim_boundary"]
    assert boundary["registered_v111_target_outcome_observed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v111_preregistration_rejects_foreign_copy():
    registration = v111.freeze_identity_short_circuited_epoch_preregistration_v111()
    with pytest.raises(
        v111.ConstructionK7IdentityShortCircuitedEpochPreregistrationV111Error
    ):
        v111.verify_identity_short_circuited_epoch_preregistration_v111(
            copy.copy(registration)
        )
