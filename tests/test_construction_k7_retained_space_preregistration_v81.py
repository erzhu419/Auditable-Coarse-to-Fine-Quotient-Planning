import pytest

from acfqp.construction_k7_retained_space_preregistration_v81 import (
    ConstructionK7RetainedSpacePreregistrationV81Error,
    SOURCE_POOL_SEEDS,
    freeze_retained_space_preregistration_v81,
    verify_retained_space_preregistration_v81,
)


def test_v81_preregisters_version_space_retention_before_outcomes():
    value = verify_retained_space_preregistration_v81(
        freeze_retained_space_preregistration_v81()
    )
    document = value.to_document()
    assert tuple(document["identity_contract"]["source_pool_seeds"]) == (
        SOURCE_POOL_SEEDS
    )
    assert document["identity_contract"]["fresh_target_identities_registered"] == []
    assert document["failure_driven_successor_contract"][
        "v80_zero_projected_successor_consensus_preserved"
    ] is True
    assert document["construction_contract"][
        "residual_successor_consensus_used_before_issuance"
    ] is False
    assert document["construction_contract"][
        "every_batch_exact_residual_proposal_jointly_compiled"
    ] is True
    assert document["registered_gate"]["target_execution_forbidden_in_this_slice"] is True
    assert document["claim_boundary"]["sample_tax_reduction_verified"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["fresh_registered_v81_execution_performed"] is False


def test_v81_preregistration_rejects_foreign_values():
    with pytest.raises(ConstructionK7RetainedSpacePreregistrationV81Error):
        verify_retained_space_preregistration_v81(object())
