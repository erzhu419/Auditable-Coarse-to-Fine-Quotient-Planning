from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_certificate_delta_only_invalidation_campaign_v176 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    ConstructionK7CertificateDeltaOnlyInvalidationCampaignV176Error,
    run_certificate_delta_only_invalidation_campaign_v176,
)
from acfqp.phase3e_ids import loads_canonical_json


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v176_frozen_campaign_identity_and_zero_production_control():
    if CAMPAIGN_ID == "0" * 64:
        assert ATTEMPT_TERMINAL_STATE == "UNEXECUTED"
        return
    raw = (FREEZE / "v176_certificate_delta_only_invalidation_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["production_full_graph_diff_checks"] == 0
    assert document["production_full_graph_diff_control_present"] is False


def test_v176_frozen_producer_refuses_rerun():
    if CAMPAIGN_ID == "0" * 64:
        return
    with pytest.raises(
        ConstructionK7CertificateDeltaOnlyInvalidationCampaignV176Error,
        match="terminal",
    ):
        run_certificate_delta_only_invalidation_campaign_v176(b"", b"", b"")
