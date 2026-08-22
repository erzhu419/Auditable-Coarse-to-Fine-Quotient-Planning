import hashlib

from acfqp.construction_k7_sample_tax_replication_preregistration_v164 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_sample_tax_replication_preregistration_v164,
)


def test_v164_preregistration_is_outcome_free_and_exact():
    frozen = freeze_sample_tax_replication_preregistration_v164()
    document = frozen.to_document()
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "query_policy_strict_aggregate_sample_reduction_required"
    ] is True
    assert document["registered_gate"][
        "factor_prior_strict_aggregate_sample_reduction_required"
    ] is True
    assert document["frozen_v163_independent_verification"][
        "producer_free_verified"
    ] is True
