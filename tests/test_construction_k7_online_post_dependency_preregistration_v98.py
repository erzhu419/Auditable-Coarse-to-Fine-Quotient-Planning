import copy
import pickle

import pytest

from acfqp import construction_k7_online_post_dependency_preregistration_v98 as subject


def test_v98_preregistration_is_outcome_free_and_source_closed():
    frozen = subject.freeze_online_post_dependency_preregistration_v98()
    verified = subject.verify_online_post_dependency_preregistration_v98(frozen)
    document = verified.to_document()
    assert document["identity_contract"]["target_seeds"] == [
        1_003_101,
        1_003_102,
        1_003_103,
        1_003_104,
    ]
    assert document["source_closure"][
        "frozen_before_any_registered_v98_target_outcome"
    ] is True
    assert document["registered_gate"][
        "aggregate_activation_labels_must_be_strictly_below_no_prior"
    ] is True
    assert document["claim_boundary"][
        "registered_v98_target_outcome_observed"
    ] is False
    assert document["claim_boundary"][
        "structural_prior_model_activation_sample_tax_advantage_verified"
    ] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v98_preregistration_rejects_foreign_copies():
    frozen = subject.freeze_online_post_dependency_preregistration_v98()
    with pytest.raises(Exception):
        subject.verify_online_post_dependency_preregistration_v98(copy.copy(frozen))
    with pytest.raises(Exception):
        subject.verify_online_post_dependency_preregistration_v98(
            pickle.loads(pickle.dumps(frozen))
        )
