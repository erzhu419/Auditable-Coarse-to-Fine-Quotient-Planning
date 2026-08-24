from pathlib import Path

from acfqp import construction_k7_open_world_machine_failure_freeze_v182r1 as failure


ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / ".tmp" / "v182r1-open-world-machine-campaign"


def test_v182r1_failure_and_partial_progress_are_frozen() -> None:
    result = failure.verify_retained_open_world_machine_failure_v182r1(RETAINED)
    assert result["failure_id"] == failure.EXPECTED_FAILURE_ID
    assert result["failure_preserved"] is True
    assert result["same_identity_rerun_forbidden"] is True
    assert result["scientific_success_claimed"] is False
    assert len(result["progress_checkpoint_ids"]) == 3
