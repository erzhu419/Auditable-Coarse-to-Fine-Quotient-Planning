import copy

import pytest

from acfqp import construction_k7_incremental_abstract_successor_preregistration_v113 as prereg


def test_v113_preregistration_is_outcome_free_and_fresh():
    frozen = prereg.verify_incremental_abstract_successor_preregistration_v113(
        prereg.freeze_incremental_abstract_successor_preregistration_v113()
    )
    document = frozen.to_document()
    assert document["preregistration_id"] == frozen.preregistration_id
    assert document["source_closure"][
        "frozen_before_any_registered_v113_target_outcome"
    ] is True
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["construction_contract"][
        "abstract_planner_consumes_compiled_model_without_raw_transition_argument"
    ] is True
    assert document["claim_boundary"]["registered_v113_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v113_preregistration_rejects_foreign_copy():
    frozen = prereg.freeze_incremental_abstract_successor_preregistration_v113()
    with pytest.raises(
        prereg.ConstructionK7IncrementalAbstractSuccessorPreregistrationV113Error
    ):
        prereg.verify_incremental_abstract_successor_preregistration_v113(
            copy.copy(frozen)
        )
