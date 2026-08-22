from pathlib import Path

from acfqp.sixth_family_complete_plan_receipt_campaign_core_v171 import (
    RESERVOIR_DISPATCH_FAMILY,
    build_sixth_family_complete_plan_receipt_occurrence_v171,
    sixth_family_complete_plan_receipt_campaign_config_v171,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v171_development_identity_has_complete_taxonomy_and_sample_reduction():
    document = build_sixth_family_complete_plan_receipt_occurrence_v171(
        sixth_family_complete_plan_receipt_campaign_config_v171(),
        family=RESERVOIR_DISPATCH_FAMILY,
        seed=1_059_798,
        episode_indices=(960, 961),
        bank_raw=(FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
        ).read_bytes(),
    )
    assert document["registered_gate"]["passed"] is True
    assert document["target_family"] == RESERVOIR_DISPATCH_FAMILY
    assert document["factor_prior_sample_reduction_within_progressive_policy"] > 0
    assert document["typed_plan_receipt_count"] > 0
    assert document["execution_join_receipt_count"] == 2 * document["accounting"][
        "progressive_prior_execution_steps"
    ]
    assert document["registered_gate"]["every_abstract_plan_instance_typed"] is True
    assert document["registered_gate"]["every_executed_action_exactly_joined"] is True
    assert document["v170_taxonomy_annotation_changes_planning_or_execution"] is False
