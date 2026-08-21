import hashlib

from acfqp import construction_k7_total_label_meta_prior_preregistration_v94 as pre


def test_v94_preregistration_freezes_fresh_total_label_gate():
    value = pre.verify_total_label_meta_prior_preregistration_v94(
        pre.freeze_total_label_meta_prior_preregistration_v94()
    )
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert document["identity_contract"]["target_seeds"] == [971_101, 971_102]
    assert document["construction_contract"]["source_meta_prior_odds"] == 16
    assert document["registered_gate"][
        "meta_prior_total_labels_must_not_exceed_direct_on_any_target"
    ] is True
    assert document["registered_gate"][
        "meta_prior_total_labels_must_be_strictly_lower_than_direct_in_aggregate"
    ] is True
    assert document["claim_boundary"][
        "sample_tax_reduction_verified_on_registered_target_workload"
    ] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
