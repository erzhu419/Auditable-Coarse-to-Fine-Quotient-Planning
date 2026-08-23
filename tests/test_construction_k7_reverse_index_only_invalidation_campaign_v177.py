from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_reverse_index_only_invalidation_campaign_v177 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    ConstructionK7ReverseIndexOnlyInvalidationCampaignV177Error,
    run_reverse_index_only_invalidation_campaign_v177,
)
from acfqp.phase3e_ids import loads_canonical_json


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v177_frozen_campaign_identity_and_zero_projection_scan():
    if CAMPAIGN_ID == "0" * 64:
        assert ATTEMPT_TERMINAL_STATE == "UNEXECUTED"
        return
    raw = (FREEZE / "v177_reverse_index_only_invalidation_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["production_full_graph_diff_checks"] == 0
    assert document["accounting"][
        "production_live_dependency_projection_scan_count"
    ] == 0
    assert document["production_live_dependency_projection_scan_present"] is False


def test_v177_frozen_producer_refuses_rerun():
    if CAMPAIGN_ID == "0" * 64:
        return
    with pytest.raises(
        ConstructionK7ReverseIndexOnlyInvalidationCampaignV177Error,
        match="terminal",
    ):
        run_reverse_index_only_invalidation_campaign_v177(b"", b"", b"")
