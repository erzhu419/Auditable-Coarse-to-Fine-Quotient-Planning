from pathlib import Path

from acfqp.progressive_raw_prefix_campaign_core_v160 import (
    POSITIVE_FAMILY,
    build_progressive_raw_prefix_occurrence_v160,
    progressive_raw_prefix_campaign_config_v160,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v160_source_identity_smoke_runs_abstract_planning_and_local_recovery():
    config = progressive_raw_prefix_campaign_config_v160()
    row = build_progressive_raw_prefix_occurrence_v160(
        config,
        family=POSITIVE_FAMILY,
        seed=1_047_811,
        episode_indices=(721, 722),
        bank_raw=(FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v160_progressive_raw_prefix_classifier_receipt.json"
        ).read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["query_policy_sample_reduction_vs_legacy_path_first"] > 0
    assert row["registered_gate"][
        "certificate_failure_only_local_ground_distinctions"
    ] is True
    assert row["registered_gate"][
        "planner_consumes_compiled_model_without_raw_rows"
    ] is True
    assert row["official_scalar_cost"] is None
