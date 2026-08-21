import copy

import pytest

from acfqp import construction_k7_three_family_incremental_successor_preregistration_v114 as prereg


def test_v114_preregistration_is_outcome_free_three_family_contract():
    frozen = prereg.verify_three_family_incremental_successor_preregistration_v114(
        prereg.freeze_three_family_incremental_successor_preregistration_v114()
    )
    document = frozen.to_document()
    assert document["identity_contract"]["two_occurrences_per_family"] is True
    assert document["construction_contract"][
        "coupled_exchange_was_absent_from_v113_registered_targets"
    ] is True
    assert document["claim_boundary"]["registered_v114_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v114_preregistration_rejects_foreign_copy():
    frozen = prereg.freeze_three_family_incremental_successor_preregistration_v114()
    with pytest.raises(
        prereg.ConstructionK7ThreeFamilyIncrementalSuccessorPreregistrationV114Error
    ):
        prereg.verify_three_family_incremental_successor_preregistration_v114(
            copy.copy(frozen)
        )
