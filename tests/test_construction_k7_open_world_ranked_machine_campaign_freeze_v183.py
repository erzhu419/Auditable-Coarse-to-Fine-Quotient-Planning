from pathlib import Path

from acfqp import construction_k7_open_world_ranked_machine_campaign_freeze_v183 as freeze


ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / ".tmp" / "exact-freeze" / "v183_ranked_machine_campaign"


def test_v183_campaign_and_producer_free_replay_are_frozen() -> None:
    verification = freeze.verify_retained_open_world_ranked_machine_campaign_v183(
        RETAINED
    )
    assert verification["campaign_id"] == freeze.EXPECTED_CAMPAIGN_ID
    assert verification["verification_id"] == freeze.EXPECTED_VERIFICATION_ID
    assert verification["prior_target_total_labels"] == 19
    assert verification["no_prior_target_total_labels"] == 25
    assert verification["target_labels_avoided"] == 6
    assert verification["producer_module_imported"] is False
    assert verification["broad_iid_sample_efficiency_claimed"] is False
    assert verification["arbitrary_domain_transfer_claimed"] is False
    assert verification["total_work_dominance_claimed"] is False
    assert verification["official_execution_allowed"] is False
