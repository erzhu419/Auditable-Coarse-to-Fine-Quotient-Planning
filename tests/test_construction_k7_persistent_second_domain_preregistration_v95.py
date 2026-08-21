import hashlib

from acfqp import construction_k7_persistent_second_domain_preregistration_v95 as pre


def test_v95_preregistration_freezes_fresh_persistent_second_domain_gate():
    value = pre.verify_persistent_second_domain_preregistration_v95(
        pre.freeze_persistent_second_domain_preregistration_v95()
    )
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert document["identity_contract"]["target_seeds"] == [982_101, 982_102]
    assert document["identity_contract"]["target_episode_indices"] == [15, 16]
    assert document["construction_contract"][
        "acquisition_rows_paid_once_and_persisted_across_queries"
    ] is True
    assert document["registered_gate"][
        "second_query_must_require_zero_new_certificate_labels"
    ] is True
    assert document["claim_boundary"][
        "sample_tax_reduction_replicated_in_second_registered_domain"
    ] is False
    assert document["claim_boundary"]["official_execution_allowed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
