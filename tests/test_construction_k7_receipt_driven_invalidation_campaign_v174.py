from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_receipt_driven_invalidation_campaign_v174 import (
    ATTEMPT_TERMINAL_STATE,
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    ConstructionK7ReceiptDrivenInvalidationCampaignV174Error,
    run_receipt_driven_invalidation_campaign_v174,
)
from acfqp.phase3e_ids import loads_canonical_json


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v174_frozen_campaign_identity_and_gates():
    if CAMPAIGN_ID == "0" * 64:
        assert ATTEMPT_TERMINAL_STATE == "UNEXECUTED"
        return
    raw = (FREEZE / "v174_receipt_driven_invalidation_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["graph_dependency_invalidations"] > 0
    assert document["accounting"]["graph_dependency_retentions"] > 0
    assert document["accounting"]["compiled_program_invalidations"] > 0
    assert document["accounting"]["incrementally_revalidated_plan_receipts"] > 0


def test_v174_frozen_producer_refuses_rerun():
    if CAMPAIGN_ID == "0" * 64:
        return
    with pytest.raises(
        ConstructionK7ReceiptDrivenInvalidationCampaignV174Error,
        match="terminal",
    ):
        run_receipt_driven_invalidation_campaign_v174(b"", b"", b"", b"", b"")
