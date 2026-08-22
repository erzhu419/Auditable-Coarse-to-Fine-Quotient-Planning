import hashlib

import pytest

from acfqp.construction_k7_progressive_raw_prefix_source_preregistration_v160 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    SOURCE_PREREGISTRATION_ID,
    freeze_progressive_raw_prefix_source_preregistration_v160,
)


def test_v160_source_preregistration_is_outcome_free_and_frozen():
    if SOURCE_PREREGISTRATION_ID == "0" * 64:
        pytest.skip("V160 source preregistration not frozen")
    receipt = freeze_progressive_raw_prefix_source_preregistration_v160()
    document = receipt.to_document()
    assert receipt.source_preregistration_id == SOURCE_PREREGISTRATION_ID
    assert len(receipt.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(receipt.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["claim_boundary"]["source_outcomes_accessed"] is False
    assert document["registered_source_gate"][
        "no_named_initial_or_catalogue_support_primitive"
    ] is True
    assert document["registered_source_gate"][
        "full_initial_action_frontier_must_not_be_required"
    ] is True
