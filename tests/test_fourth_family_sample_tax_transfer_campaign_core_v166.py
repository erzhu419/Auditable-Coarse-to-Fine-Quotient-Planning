from pathlib import Path

from acfqp.fourth_family_sample_tax_transfer_campaign_core_v166 import (
    MAINTENANCE_FAMILY,
    build_fourth_family_sample_tax_occurrence_v166,
    fourth_family_sample_tax_transfer_campaign_config_v166,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v166_development_identity_runs_new_family_through_full_pipeline():
    config = fourth_family_sample_tax_transfer_campaign_config_v166()
    document = build_fourth_family_sample_tax_occurrence_v166(
        config,
        family=MAINTENANCE_FAMILY,
        seed=1_048_699,
        episode_indices=(939, 940),
        bank_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank.json"
        ).read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
        ).read_bytes(),
    )
    assert document["target_family"] == MAINTENANCE_FAMILY
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "both_arm_receding_episodes_succeed"
    ] is True
    assert document["registered_gate"][
        "all_executed_actions_have_v109_receipts"
    ] is True
    assert document["query_policy_sample_reduction_vs_legacy_path_first"] == 0
    assert document[
        "factor_prior_sample_reduction_within_progressive_policy"
    ] > 0
    assert document["profitability_classifier_issued"] is False
