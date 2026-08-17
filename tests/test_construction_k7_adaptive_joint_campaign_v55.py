import dataclasses
import hashlib

import pytest

from acfqp.construction_k7_adaptive_joint_campaign_v55 import (
    AdaptiveJointCampaignV55,
    run_adaptive_joint_campaign_v55,
    verify_adaptive_joint_campaign_v55,
)


@pytest.fixture(scope="module")
def campaign():
    return verify_adaptive_joint_campaign_v55(run_adaptive_joint_campaign_v55())


def test_v55_campaign_freezes_registered_identity_and_adaptive_joint_models(campaign):
    assert campaign.campaign_id == (
        "ea85860f499ac631a7f3e6b306974be2a2d7c9de88cde3cf492380ebd59ec589"
    )
    assert len(campaign.canonical_bytes) == 2_027_913
    assert hashlib.sha256(campaign.canonical_bytes).hexdigest() == (
        "38363f222d1b4047e4ce6f2fd5e6c4aea595709b473e9aed44d90fd54245128a"
    )
    document = campaign.to_document()
    assert document["full_frontier_target_layout_calibration_consumed"] is False
    assert document["shared_residual_scaffold_consumed"] is False
    assert document["predeclared_reusable_factor_slots_consumed"] is False
    for rows in document["acquisitions"].values():
        assert len(rows) == 128
        assert all(row["candidate"]["factorable_reusable_count"] == 3 for row in rows)
        assert all(row["candidate"]["factorable_novel_count"] == 1 for row in rows)
        assert all(row["candidate"]["residual_schema_bound_count"] == 2 for row in rows)


def test_v55_campaign_reduces_sample_tax_with_only_the_prior_weight_switched(campaign):
    sample = campaign.to_document()["sample_tax"]
    assert sample["factor_prior_on_acquisition_labels"] == 10_240
    assert sample["strict_no_prior_acquisition_labels"] == 10_760
    assert sample["incremental_acquisition_label_reduction"] == 520
    assert sample["factor_prior_on_local_recovery_labels"] == 16
    assert sample["strict_no_prior_local_recovery_labels"] == 14
    assert sample["online_label_reduction_including_local_recovery"] == 518
    assert sample["lifetime_label_reduction_after_factor_library_tax"] == 148
    assert sample["diagnostic_break_even_occurrence_count"] == 92
    assert sample["same_synthesizer_and_stopping_formula"] is True
    assert sample["only_factor_prior_initial_weight_switched"] is True
    assert sample["official_break_even_claimed"] is False


def test_v55_campaign_plans_match_and_all_local_queries_follow_failure(campaign):
    document = campaign.to_document()
    action_rows = [
        [row["action_keys"] for row in document["episodes"][arm]]
        for arm in (
            "ANONYMOUS_FACTOR_PRIOR_ON",
            "STRICT_NO_PRIOR",
            "STRICT_EXACT_CONTEXT",
        )
    ]
    assert action_rows[0] == action_rows[1] == action_rows[2]
    assert all(
        row["success"]
        for values in document["episodes"].values()
        for row in values
    )
    assert len(document["failed_certificates"]) == 30
    assert len(document["local_distinctions"]) == 30
    assert all(
        row["query_after_failed_certificate"]
        for row in document["local_distinctions"]
    )


def test_v55_campaign_reports_honest_partial_dynamics_and_strict_ood(campaign):
    document = campaign.to_document()
    assert len(document["isolated_full_frontier_validations"]) == 8
    for validation in document["isolated_full_frontier_validations"]:
        assert validation["validation_rows_consumed_for_acquisition"] is False
        assert validation["validation_rows_consumed_for_binding"] is False
        assert validation["validation_rows_consumed_for_planning"] is False
        assert validation["honest_partial_dynamics_reported"] is True
    assert document["ood_rejection"]["factorable_reusable_count"] == 2
    assert document["ood_rejection"]["outcome"] == (
        "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER"
    )
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v55_campaign_rejects_foreign_values(campaign):
    with pytest.raises(dataclasses.FrozenInstanceError):
        campaign.campaign_id = "f" * 64
    with pytest.raises(Exception):
        AdaptiveJointCampaignV55(object(), campaign.canonical_bytes, campaign.campaign_id)
    with pytest.raises(Exception):
        verify_adaptive_joint_campaign_v55(object())
