from pathlib import Path

from acfqp.fifth_family_total_plan_receipt_set_campaign_core_v168 import (
    PACKET_BATCHING_FAMILY,
    V166_FAILURE_ID,
    build_fifth_family_total_plan_receipt_set_occurrence_v168,
    fifth_family_total_plan_receipt_set_campaign_config_v168,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v168_development_packet_identity_runs_with_total_receipt_set_gate():
    document = build_fifth_family_total_plan_receipt_set_occurrence_v168(
        fifth_family_total_plan_receipt_set_campaign_config_v168(),
        family=PACKET_BATCHING_FAMILY,
        seed=1_049_799,
        episode_indices=(951, 952),
        bank_raw=(FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        classifier_receipt_raw=(
            FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
        ).read_bytes(),
    )
    assert document["registered_gate"]["passed"] is True
    assert document["target_family"] == PACKET_BATCHING_FAMILY
    assert document["failed_v166_attempt_id"] == V166_FAILURE_ID
    assert len(document["registered_plan_receipt_set_classes"]) == 2
    assert all(
        name in {"DIRECT_ONLY", "MEMOIZED_ONLY", "MIXED", "NONE"}
        for name in document["registered_plan_receipt_set_classes"]
    )
    assert document["registered_gate"][
        "none_receipt_set_is_nonfailure_v109_certificate_fallback"
    ] is True
    assert document["registered_gate"][
        "all_executed_actions_have_v109_receipts"
    ] is True
    assert document[
        "plan_mode_set_annotation_changes_planner_or_execution"
    ] is False
