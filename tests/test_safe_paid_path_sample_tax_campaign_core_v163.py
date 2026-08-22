from pathlib import Path

from acfqp.safe_paid_path_sample_tax_campaign_core_v163 import (
    POSITIVE_FAMILY,
    build_safe_paid_path_sample_tax_occurrence_v163,
    safe_paid_path_sample_tax_campaign_config_v163,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v163_historical_zero_benefit_switch_is_safe_and_plans():
    row = build_safe_paid_path_sample_tax_occurrence_v163(
        safe_paid_path_sample_tax_campaign_config_v163(),
        family=POSITIVE_FAMILY,
        seed=1_048_401,
        episode_indices=(881, 882),
        bank_raw=(FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
        ).read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["certified_positive_switch"] is True
    assert row["query_policy_sample_reduction_vs_legacy_path_first"] == 0
    assert row["factor_prior_sample_reduction_within_progressive_policy"] > 0
    assert row["registered_gate"][
        "certificate_failure_only_local_ground_distinctions"
    ] is True
    assert row["registered_gate"]["all_executed_actions_have_v109_receipts"] is True
    assert row["query_policy_strict_sample_reduction_claimed"] is False
