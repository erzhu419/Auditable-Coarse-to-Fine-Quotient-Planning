from pathlib import Path
import hashlib

from acfqp.construction_k7_packet_batching_transfer_preregistration_v134 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_packet_batching_transfer_preregistration_v134,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_packet_batching_transfer_preregistration_v134(
        (ROOT / "v132_opaque_source_archive_dictionary.json").read_bytes(),
        (ROOT / "v132_opaque_source_archive_verification.json").read_bytes(),
        (ROOT / "v133_opaque_archive_planning_campaign.json").read_bytes(),
        (ROOT / "v133_opaque_archive_planning_verification.json").read_bytes(),
    )


def test_v134_preregisters_source_unseen_domain_before_outcomes():
    registration = _freeze()
    document = registration.to_document()
    assert document["registered_gate"][
        "v132_dictionary_predates_target_domain_implementation"
    ] is True
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["registered_v134_target_outcome_observed"] is False
    assert len(document["target_occurrences"]) == 4
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v134_frozen_preregistration_bytes_when_registered():
    registration = _freeze()
    if PREREGISTRATION_ID != "0" * 64:
        assert registration.preregistration_id == PREREGISTRATION_ID
        assert len(registration.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(registration.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
