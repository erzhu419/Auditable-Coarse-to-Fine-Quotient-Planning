from pathlib import Path

from acfqp.certified_paid_path_switch_campaign_core_v162 import (
    FALLBACK_FAMILY,
    POSITIVE_FAMILY,
    build_certified_paid_path_switch_occurrence_v162,
    certified_paid_path_switch_campaign_config_v162,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _build(family, seed):
    return build_certified_paid_path_switch_occurrence_v162(
        certified_paid_path_switch_campaign_config_v162(),
        family=family,
        seed=seed,
        episode_indices=(741, 742),
        bank_raw=(FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
        ).read_bytes(),
    )


def test_v162_source_certified_switch_and_exact_fallback_both_plan():
    positive = _build(POSITIVE_FAMILY, 1_047_811)
    fallback = _build(FALLBACK_FAMILY, 1_047_821)
    assert positive["registered_gate"]["passed"] is True
    assert positive["certified_positive_switch"] is True
    assert positive["query_policy_sample_reduction_vs_legacy_path_first"] > 0
    assert fallback["registered_gate"]["passed"] is True
    assert fallback["exact_path_first_fallback"] is True
    assert fallback["query_policy_sample_reduction_vs_legacy_path_first"] == 0
    for row in (positive, fallback):
        assert row["registered_gate"][
            "certificate_failure_only_local_ground_distinctions"
        ] is True
        assert row["registered_gate"][
            "all_executed_actions_have_v109_receipts"
        ] is True
