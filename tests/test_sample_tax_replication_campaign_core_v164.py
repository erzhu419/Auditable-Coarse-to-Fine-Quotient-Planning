from pathlib import Path

from acfqp.sample_tax_replication_campaign_core_v164 import (
    POSITIVE_FAMILY,
    build_sample_tax_replication_occurrence_v164,
    sample_tax_replication_campaign_config_v164,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v164_source_wrapper_retains_planning_and_v163_identity():
    row = build_sample_tax_replication_occurrence_v164(
        sample_tax_replication_campaign_config_v164(),
        family=POSITIVE_FAMILY,
        seed=1_048_503,
        episode_indices=(901, 902),
        bank_raw=(FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
        ).read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["query_policy_sample_reduction_vs_legacy_path_first"] > 0
    assert row["registered_gate"][
        "certificate_failure_only_local_ground_distinctions"
    ] is True
    assert row["registered_gate"]["all_executed_actions_have_v109_receipts"] is True
    assert len(row["source_v163_occurrence_id"]) == 64
