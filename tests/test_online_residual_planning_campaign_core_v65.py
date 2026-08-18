import pytest

from acfqp.online_residual_planning_campaign_core_v65 import (
    OnlineResidualPlanningCampaignCoreV65Error,
)


def test_v65_has_typed_registered_gate_failure():
    assert issubclass(OnlineResidualPlanningCampaignCoreV65Error, ValueError)


def test_v65_rejects_empty_occurrence_inventory():
    from acfqp.online_residual_planning_campaign_core_v65 import (
        build_online_residual_planning_campaign_document_v65,
    )

    with pytest.raises(OnlineResidualPlanningCampaignCoreV65Error):
        build_online_residual_planning_campaign_document_v65(
            {
                "target_seeds": {},
                "target_occurrence_count": 1,
                "worker_count": 1,
                "offline_library_labels": 204,
            },
            "a" * 64,
            "b" * 64,
            "c" * 64,
            {},
            {},
        )
