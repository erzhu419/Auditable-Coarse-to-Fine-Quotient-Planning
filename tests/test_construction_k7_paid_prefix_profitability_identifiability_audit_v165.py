from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_paid_prefix_profitability_identifiability_audit_v165 import (
    AUDIT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    freeze_paid_prefix_profitability_identifiability_audit_v165,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_paid_prefix_profitability_identifiability_audit_v165(
        (FREEZE / "v163_safe_paid_path_sample_tax_campaign.json").read_bytes(),
        (FREEZE / "v163_safe_paid_path_sample_tax_verification.json").read_bytes(),
        (FREEZE / "v164_sample_tax_replication_campaign.json").read_bytes(),
        (FREEZE / "v164_sample_tax_replication_verification.json").read_bytes(),
    )


def test_v165_registered_source_only_identifiability_result():
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["source_occurrence_count"] == 20
    assert document["strictly_profitable_occurrence_count"] == 3
    assert document["zero_reduction_occurrence_count"] == 17
    assert document["mixed_profitability_signature_count"] >= 1
    assert document[
        "perfect_deterministic_classifier_exists_in_registered_signature_space"
    ] is False
    assert document["profitability_classifier_issued"] is False
    assert document["new_target_outcomes_accessed"] is False
    assert document["official_scalar_cost"] is None


def test_v165_frozen_audit_identity():
    if AUDIT_ID == "0" * 64:
        pytest.skip("V165 audit not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["audit_id"] == AUDIT_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
