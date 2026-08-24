from pathlib import Path

from acfqp import construction_k7_open_world_fair_expression_campaign_freeze_v184 as freeze


ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / ".tmp" / "exact-freeze" / "v184_fair_expression_campaign"


def test_v184_campaign_and_producer_free_replay_are_frozen() -> None:
    verification = freeze.verify_retained_open_world_fair_expression_campaign_v184(
        RETAINED
    )
    assert verification["campaign_id"] == freeze.EXPECTED_CAMPAIGN_ID
    assert verification["verification_id"] == freeze.EXPECTED_VERIFICATION_ID
    assert verification["prior_target_total_labels"] == 72
    assert verification["no_prior_target_total_labels"] == 88
    assert verification["target_labels_avoided"] == 16
    assert verification["componentwise_target_work_dominance_observed"] is True
    assert verification["producer_module_imported"] is False
    assert verification["new_primitive_opcode_invented"] is False
    assert verification["broad_iid_sample_efficiency_claimed"] is False
    assert verification["arbitrary_domain_transfer_claimed"] is False
    assert verification["official_execution_allowed"] is False
