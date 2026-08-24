from pathlib import Path

from acfqp import construction_k7_open_world_total_machine_campaign_freeze_v182r2 as freeze


ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / ".tmp" / "v182r2-open-world-total-machine-campaign"


def test_v182r2_campaign_and_independent_verification_are_frozen() -> None:
    result = freeze.verify_retained_open_world_total_machine_campaign_v182r2(
        RETAINED
    )
    assert result["campaign_id"] == freeze.EXPECTED_CAMPAIGN_ID
    assert result["verification_id"] == freeze.EXPECTED_VERIFICATION_ID
    assert result["target_labels_avoided"] == 6
    assert result["all_registered_episodes_terminal"] is True
    assert result["finite_carrier_totality_not_unbounded_totality"] is True
    assert result["official_execution_allowed"] is False
