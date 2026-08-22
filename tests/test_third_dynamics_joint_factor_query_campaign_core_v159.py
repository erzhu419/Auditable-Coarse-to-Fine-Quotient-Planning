from pathlib import Path

from acfqp.third_dynamics_joint_factor_query_campaign_core_v159 import (
    build_third_dynamics_joint_factor_query_occurrence_v159,
    third_dynamics_campaign_config_v159,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v159_nonformal_third_dynamics_smoke():
    row = build_third_dynamics_joint_factor_query_occurrence_v159(
        third_dynamics_campaign_config_v159(),
        seed=1_048_993,
        episode_indices=(805, 806, 807, 808),
        bank_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank.json"
        ).read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v159_joint_factor_query_classifier_receipt.json"
        ).read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["registered_gate"]["v158_metadata_classifier_false_positive_observed"] is True
    assert row["registered_gate"]["joint_factor_classifier_selected_safe_fallback"] is True
    assert row["registered_gate"]["paid_raw_factorization_corroborates_fallback"] is True
    assert row["registered_gate"]["bounded_target_factorization_audit_labels"] is True
    assert row["accounting"]["additional_target_factorization_probe_labels"] <= 1
    assert row["guard_sample_reduction_vs_legacy_path_first"] == 0
    assert row["factor_prior_sample_reduction_within_joint_policy"] >= 0
    assert row["official_scalar_cost"] is None
