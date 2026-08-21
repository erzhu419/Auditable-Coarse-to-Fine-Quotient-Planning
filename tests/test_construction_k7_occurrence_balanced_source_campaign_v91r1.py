import os

import pytest

from acfqp import construction_k7_occurrence_balanced_source_campaign_v91r1 as campaign


def test_v91r1_frozen_runner_refuses_same_identity_reexecution():
    if (
        campaign.CAMPAIGN_ID == "0" * 64
        and campaign.FROZEN_FAILURE_ID == "0" * 64
    ):
        pytest.skip("V91r1 registered outcome not frozen yet")
    with pytest.raises(
        campaign.ConstructionK7OccurrenceBalancedSourceCampaignV91R1Error,
        match="same identity will not be rerun",
    ):
        campaign.run_occurrence_balanced_source_campaign_v91r1()


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V91R1") != "1",
    reason="explicit one-shot V91r1 registered execution",
)
def test_v91r1_registered_execution_once():
    result = campaign.run_occurrence_balanced_source_campaign_v91r1()
    assert result.campaign_id == result.to_document()["campaign_id"]
