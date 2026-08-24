from pathlib import Path

from acfqp import construction_k7_v34_retained_recovery_evidence_freeze_v180r11 as freeze


ROOT = Path(__file__).resolve().parents[1] / ".tmp" / "exact-freeze"


def test_v180r11_retained_finish_forward_is_frozen_and_replayed() -> None:
    verification = freeze.verify_retained_v34_recovery_evidence_v180r11(ROOT)
    assert verification["v34_retained_terminal_id"] == freeze.EXPECTED_TERMINAL_ID
    assert verification["verification_id"] == freeze.EXPECTED_VERIFICATION_ID
    assert verification["operational_work_vector_count"] == 45
    assert verification["counter_record_count"] == 45 * 269
    assert verification["scientific_occurrence_rerun"] is False
    assert verification["single_terminal_path_verified"] is True
    assert verification["all_ten_paths_verified"] is False
    assert verification["official_execution_allowed"] is False
