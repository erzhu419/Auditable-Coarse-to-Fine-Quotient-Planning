import copy

import pytest

from acfqp import construction_k7_fourth_family_inventory_preregistration_v118 as pre


def test_v118_preregistration_freezes_transfer_and_unfavourable_sample_boundary():
    value = pre.freeze_fourth_family_inventory_preregistration_v118()
    document = value.to_document()
    assert document["source_closure"][
        "frozen_before_any_registered_v118_target_outcome"
    ] is True
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["sample_tax_contract"][
        "unfavourable_development_result_retained"
    ] is True
    assert document["sample_tax_contract"]["sample_efficiency_improvement_claimed"] is False
    assert document["claim_boundary"]["arbitrary_unseen_domain_transfer_claimed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v118_preregistration_rejects_copy():
    value = pre.freeze_fourth_family_inventory_preregistration_v118()
    with pytest.raises(
        pre.ConstructionK7FourthFamilyInventoryPreregistrationV118Error
    ):
        pre.verify_fourth_family_inventory_preregistration_v118(copy.copy(value))
