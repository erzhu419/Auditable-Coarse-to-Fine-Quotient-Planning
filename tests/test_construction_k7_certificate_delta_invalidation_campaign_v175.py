from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_certificate_delta_invalidation_campaign_v175 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    EXPECTED_FAILURE_CANONICAL_BYTE_COUNT,
    EXPECTED_FAILURE_CANONICAL_SHA256,
    FAILURE_ID,
    ConstructionK7CertificateDeltaInvalidationCampaignV175Error,
    run_certificate_delta_invalidation_campaign_v175,
)
from acfqp.phase3e_ids import loads_canonical_json


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v175_frozen_campaign_identity_and_delta_gates():
    if CAMPAIGN_ID == "0" * 64:
        assert ATTEMPT_TERMINAL_STATE == "FROZEN_INPUT_IDENTITY_REJECTION"
        return
    raw = (FREEZE / "v175_certificate_delta_invalidation_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["delta_receipts"] > 0
    assert document["accounting"]["delta_transition_joins"] > 0
    assert document["accounting"]["full_graph_diff_checks_avoided"] > 0
    assert document["registered_gate"][
        "zero_full_graph_scan_on_every_invalidation_decision"
    ] is True


def test_v175_frozen_failure_preserves_classifier_identity_rejection():
    raw = (FREEZE / "v175_certificate_delta_invalidation_failure.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["failure_id"] == FAILURE_ID
    assert len(raw) == EXPECTED_FAILURE_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_FAILURE_CANONICAL_SHA256
    assert document["preregistration_id"] == (
        "40d357786fc0f8921c76198c868b6b497fe066791edea086a4a0c1920399a076"
    )
    assert document["target_occurrence_constructed_count"] == 0
    assert document["target_outcomes_accessed"] is False
    assert document["same_preregistration_identity_may_be_rerun"] is False
    assert document["fresh_successor_identity_required"] is True


def test_v175_frozen_producer_refuses_rerun():
    if CAMPAIGN_ID == "0" * 64:
        return
    with pytest.raises(
        ConstructionK7CertificateDeltaInvalidationCampaignV175Error,
        match="terminal",
    ):
        run_certificate_delta_invalidation_campaign_v175(b"", b"", b"", b"", b"")
