from pathlib import Path
import hashlib

from acfqp.episode_scoped_plan_receipt_set_audit_v169 import (
    AUDIT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    freeze_episode_scoped_plan_receipt_set_audit_v169,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v169_enumerates_all_v168_episodes_and_observes_mixed_and_none():
    frozen = freeze_episode_scoped_plan_receipt_set_audit_v169(
        (FREEZE / "v168_fifth_family_total_plan_receipt_set_campaign.json").read_bytes()
    )
    document = frozen.to_document()
    assert len(document["receipt_set_rows"]) == 16
    assert document["receipt_set_histogram"] == {
        "DIRECT_ONLY": 2,
        "MEMOIZED_ONLY": 0,
        "MIXED": 2,
        "NONE": 12,
    }
    assert document["registered_gate"]["passed"] is True
    assert document["favorable_window_selected"] is False
    assert document[
        "episode_receipt_set_annotation_is_model_planning_or_certificate_authority"
    ] is False


def test_v169_frozen_audit_bytes():
    raw = (FREEZE / "v169_episode_scoped_plan_receipt_set_audit.json").read_bytes()
    frozen = freeze_episode_scoped_plan_receipt_set_audit_v169(
        (FREEZE / "v168_fifth_family_total_plan_receipt_set_campaign.json").read_bytes()
    )
    assert frozen.canonical_bytes == raw
    assert frozen.audit_id == AUDIT_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
