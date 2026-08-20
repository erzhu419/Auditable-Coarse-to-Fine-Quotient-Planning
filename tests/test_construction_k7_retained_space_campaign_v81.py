import os

import pytest

from acfqp.construction_k7_retained_space_campaign_v81 import (
    ConstructionK7RetainedSpaceCampaignV81Error,
    run_retained_space_campaign_v81,
    verify_retained_space_campaign_v81,
)


def test_v81_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7RetainedSpaceCampaignV81Error):
        verify_retained_space_campaign_v81(object())


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_RETAINED_SPACE_V81") != "1",
    reason="explicit preregistered V81 source-only execution",
)
def test_v81_runs_exact_frozen_source_gate():
    document = run_retained_space_campaign_v81().to_document()
    assert document["preregistration_id"]
    assert document["registered_gate"]["actual_source_member_count"] == 2
    assert document["registered_gate"]["fresh_target_outcome_count"] == 0
    assert document["target_execution_performed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
