from acfqp.combined_model_planning_campaign_core_v66 import (
    CombinedModelPlanningCampaignCoreV66Error,
)


def test_v66_has_typed_registered_gate_failure():
    assert issubclass(CombinedModelPlanningCampaignCoreV66Error, ValueError)
