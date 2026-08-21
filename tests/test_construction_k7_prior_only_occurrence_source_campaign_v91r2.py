import os

import pytest

from acfqp import construction_k7_prior_only_occurrence_source_campaign_v91r2 as campaign


def test_v91r2_frozen_runner_refuses_same_identity_reexecution():
    if campaign.CAMPAIGN_ID == "0" * 64:
        pytest.skip("V91r2 registered outcome not frozen yet")
    with pytest.raises(
        campaign.ConstructionK7PriorOnlyOccurrenceSourceCampaignV91R2Error,
        match="same identity will not be rerun",
    ):
        campaign.run_prior_only_occurrence_source_campaign_v91r2()


def test_v91r2_campaign_identity_is_frozen():
    assert campaign.CAMPAIGN_ID == (
        "3a3d634361c16438ce9fe74f961a0c57f31f8476e8118869531fe849f68b42a6"
    )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V91R2") != "1",
    reason="explicit one-shot V91r2 registered execution",
)
def test_v91r2_registered_execution_once():
    value = campaign.run_prior_only_occurrence_source_campaign_v91r2()
    assert value.campaign_id == value.to_document()["campaign_id"]
