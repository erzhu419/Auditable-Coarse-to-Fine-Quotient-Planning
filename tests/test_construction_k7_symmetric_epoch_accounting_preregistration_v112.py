import copy

import pytest

from acfqp import construction_k7_symmetric_epoch_accounting_preregistration_v112 as v112


def test_v112_preregistration_is_outcome_free_and_symmetric():
    registration = v112.verify_symmetric_epoch_accounting_preregistration_v112(
        v112.freeze_symmetric_epoch_accounting_preregistration_v112()
    )
    document = registration.to_document()
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["construction_contract"][
        "full_diff_baseline_charged_same_graph_identity_checks"
    ] is True
    assert document["construction_contract"][
        "no_algorithm_action_outcome_label_or_step_changed_by_accounting_successor"
    ] is True
    assert document["accounting_contract"][
        "both_identity_and_full_diff_arms_charge_graph_identity_checks"
    ] is True
    assert document["accounting_contract"]["no_scalar_cost_aggregation"] is True
    boundary = document["claim_boundary"]
    assert boundary["registered_v112_target_outcome_observed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v112_preregistration_rejects_foreign_copy():
    registration = v112.freeze_symmetric_epoch_accounting_preregistration_v112()
    with pytest.raises(
        v112.ConstructionK7SymmetricEpochAccountingPreregistrationV112Error
    ):
        v112.verify_symmetric_epoch_accounting_preregistration_v112(
            copy.copy(registration)
        )
