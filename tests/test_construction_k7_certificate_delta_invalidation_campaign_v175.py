from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_certificate_delta_invalidation_campaign_v175 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    ConstructionK7CertificateDeltaInvalidationCampaignV175Error,
    run_certificate_delta_invalidation_campaign_v175,
)
from acfqp.phase3e_ids import loads_canonical_json


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v175_frozen_campaign_identity_and_delta_gates():
    if CAMPAIGN_ID == "0" * 64:
        assert ATTEMPT_TERMINAL_STATE == "UNEXECUTED"
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


def test_v175_frozen_producer_refuses_rerun():
    if CAMPAIGN_ID == "0" * 64:
        return
    with pytest.raises(
        ConstructionK7CertificateDeltaInvalidationCampaignV175Error,
        match="terminal",
    ):
        run_certificate_delta_invalidation_campaign_v175(b"", b"", b"", b"", b"")
