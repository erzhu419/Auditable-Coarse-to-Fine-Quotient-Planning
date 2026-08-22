from pathlib import Path

from acfqp.paid_path_continuation_campaign_core_v161 import (
    FALLBACK_FAMILY,
    build_paid_path_continuation_occurrence_v161,
    paid_path_continuation_campaign_config_v161,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v161_source_fallback_occurrence_is_exact_and_plans_abstractly():
    row = build_paid_path_continuation_occurrence_v161(
        paid_path_continuation_campaign_config_v161(),
        family=FALLBACK_FAMILY,
        seed=1_047_821,
        episode_indices=(721, 722),
        bank_raw=(FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
        ).read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["query_policy_sample_reduction_vs_legacy_path_first"] == 0
    assert row["registered_gate"][
        "fallback_prior_bytes_labels_and_id_match_legacy"
    ] is True
    assert row["registered_gate"][
        "certificate_failure_only_local_ground_distinctions"
    ] is True
    assert row["v160_failure_preserved_not_reclassified"] is True
