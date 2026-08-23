from pathlib import Path

from acfqp.cross_family_branch_complete_online_receipt_core_v173r1 import (
    PACKET_FAMILY,
    RESERVOIR_FAMILY,
    build_cross_family_branch_complete_campaign_v173r1,
    cross_family_branch_complete_campaign_config_v173r1,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v173r1_dev_cross_family_cohort_is_branch_complete():
    config = cross_family_branch_complete_campaign_config_v173r1()
    config.update(
        target_occurrences=[
            {"family": PACKET_FAMILY, "seed": 1_099_799},
            {"family": RESERVOIR_FAMILY, "seed": 1_109_799},
        ],
        target_episode_indices=(1_013, 1_014, 1_015, 1_016),
        target_worker_count=2,
        required_target_occurrence_count=2,
    )
    campaign = build_cross_family_branch_complete_campaign_v173r1(
        config,
        preregistration_id="d" * 64,
        bank_raw=(FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
        ).read_bytes(),
        v172r1_campaign_raw=(
            FREEZE / "v172r1_online_typed_plan_receipt_campaign.json"
        ).read_bytes(),
        v172r1_verification_raw=(
            FREEZE / "v172r1_online_typed_plan_receipt_verification.json"
        ).read_bytes(),
        v173_failure_raw=(
            FREEZE / "v173_branch_complete_online_receipt_failure.json"
        ).read_bytes(),
    )
    assert campaign["registered_gate"]["passed"] is True
    assert all(count > 0 for count in campaign["online_typed_plan_source_histogram"].values())
    assert campaign["accounting"]["factor_prior_labels_avoided"] > 0
