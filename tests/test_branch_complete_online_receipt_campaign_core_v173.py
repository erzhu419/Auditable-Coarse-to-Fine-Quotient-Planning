from pathlib import Path

from acfqp.branch_complete_online_receipt_campaign_core_v173 import (
    PACKET_BATCHING_FAMILY,
    branch_complete_online_receipt_campaign_config_v173,
    build_branch_complete_online_receipt_occurrence_v173,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v173_dev_packet_occurrence_exercises_online_receipt_branches():
    config = branch_complete_online_receipt_campaign_config_v173()
    row = build_branch_complete_online_receipt_occurrence_v173(
        config,
        family=PACKET_BATCHING_FAMILY,
        seed=1_089_799,
        episode_indices=(993, 994, 995, 996),
        bank_raw=(FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
        ).read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["online_typed_plan_source_histogram"][
        "DIRECT_COMPILED_PROGRAM_ORDER"
    ] > 0
    assert row["online_typed_plan_source_histogram"][
        "OBSERVATION_DERIVED_QUOTIENT_ORDER"
    ] > 0
    assert row["online_typed_plan_source_histogram"][
        "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE"
    ] > 0
    assert row["factor_prior_sample_reduction_within_progressive_policy"] > 0
