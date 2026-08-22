from pathlib import Path

from acfqp.online_typed_plan_receipt_campaign_core_v172 import (
    RESERVOIR_DISPATCH_FAMILY,
    build_online_typed_plan_receipt_occurrence_v172,
    online_typed_plan_receipt_campaign_config_v172,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v172_fresh_occurrence_issues_receipts_online_and_reduces_labels():
    config = online_typed_plan_receipt_campaign_config_v172()
    occurrence = build_online_typed_plan_receipt_occurrence_v172(
        config,
        family=RESERVOIR_DISPATCH_FAMILY,
        seed=1_069_799,
        episode_indices=(973, 974, 975, 976),
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
    assert occurrence["registered_gate"]["passed"] is True
    assert occurrence["factor_prior_sample_reduction_within_progressive_policy"] > 0
    assert occurrence["online_plan_issuance_receipt_count"] > 0
    assert occurrence["online_execution_join_receipt_count"] == sum(
        sequence["execution_step_count"]
        for sequence in (
            occurrence["progressive_prior_sequence"],
            occurrence["progressive_strict_sequence"],
        )
    )
    assert occurrence["online_receipts_change_planning_or_execution"] is False
    assert occurrence["online_receipts_are_model_or_safety_authority"] is False
