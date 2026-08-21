import hashlib

from acfqp import construction_k7_agreement_shielded_preregistration_v99 as pre


def test_v99_preregistration_freezes_cross_family_shield_gate():
    value = pre.verify_agreement_shielded_preregistration_v99(
        pre.freeze_agreement_shielded_preregistration_v99()
    )
    document = value.to_document()
    assert document["identity_contract"]["target_occurrences"] == [
        {"family": "BALANCED_BATCH_REFINEMENT", "seed": 1_005_101},
        {"family": "BALANCED_BATCH_REFINEMENT", "seed": 1_005_102},
        {"family": "MAINTENANCE_CASCADE", "seed": 1_005_103},
        {"family": "MAINTENANCE_CASCADE", "seed": 1_005_104},
    ]
    assert document["source_closure"][
        "frozen_before_any_registered_v99_target_outcome"
    ] is True
    assert document["registered_gate"][
        "strict_incompatible_schema_no_transfer_required"
    ] is True
    assert document["claim_boundary"][
        "registered_v99_target_outcome_observed"
    ] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert (
        hashlib.sha256(value.canonical_bytes).hexdigest()
        == pre.EXPECTED_CANONICAL_SHA256
    )
