from pathlib import Path

from acfqp.fourth_family_plan_mode_set_campaign_core_v167 import (
    MAINTENANCE_FAMILY,
    V166_FAILURE_ID,
    build_fourth_family_plan_mode_set_occurrence_v167,
    fourth_family_plan_mode_set_campaign_config_v167,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v167_development_identity_runs_with_receipt_set_gate():
    document = build_fourth_family_plan_mode_set_occurrence_v167(
        fourth_family_plan_mode_set_campaign_config_v167(),
        family=MAINTENANCE_FAMILY,
        seed=1_048_799,
        episode_indices=(945, 946),
        bank_raw=(FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
        ).read_bytes(),
    )
    assert document["registered_gate"]["passed"] is True
    assert document["failed_v166_attempt_id"] == V166_FAILURE_ID
    assert all(document["registered_plan_mode_sets"])
    assert document["registered_gate"][
        "all_executed_actions_have_v109_receipts"
    ] is True
    assert document[
        "plan_mode_set_annotation_changes_planner_or_execution"
    ] is False
    assert document["query_policy_classifier_is_model_planning_or_certificate_authority"] is False
    assert document["complete_world_model_synthesized"] is False
