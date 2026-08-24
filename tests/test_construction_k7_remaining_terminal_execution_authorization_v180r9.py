import hashlib
from pathlib import Path

from acfqp import construction_k7_remaining_terminal_execution_authorization_v180r9 as authorization
from acfqp import construction_k7_remaining_terminal_evidence_freeze_v180r9 as evidence_freeze
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]


def test_v180r9_authorization_is_outcome_free_and_source_closed() -> None:
    frozen = authorization.freeze_remaining_terminal_execution_authorization_v180r9()
    document = frozen.to_document()
    assert document["execution_authorization_id"] == authorization.EXPECTED_AUTHORIZATION_ID
    assert len(frozen.canonical_bytes) == authorization.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == authorization.EXPECTED_CANONICAL_SHA256
    assert canonical_json_bytes(document) == frozen.canonical_bytes
    assert document["fresh_controlled_execution_started"] is False
    assert document["production_outcome_accessed"] is False
    assert len(document["ordered_terminal_codes"]) == 6
    assert len(document["event_manifests"]) == 6
    assert document["actual_worker_process_count"] == 0
    assert document["official_execution_allowed"] is False
    for fact in document["source_facts"]:
        raw = (ROOT / fact["relative_path"]).read_bytes()
        assert len(raw) == fact["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == fact["sha256"]


def test_v180r9_output_root_is_absent_or_exactly_frozen_after_execution() -> None:
    document = authorization.freeze_remaining_terminal_execution_authorization_v180r9().to_document()
    output_root = ROOT / document["output_root_relative_path"]
    if not output_root.exists():
        return
    assert set(path.name for path in output_root.iterdir()) == {
        "TERMINAL.json",
        "VERIFICATION.json",
    }
    evidence_freeze.verify_frozen_remaining_terminal_evidence_v180r9(
        (output_root / "TERMINAL.json").read_bytes(),
        (output_root / "VERIFICATION.json").read_bytes(),
    )
