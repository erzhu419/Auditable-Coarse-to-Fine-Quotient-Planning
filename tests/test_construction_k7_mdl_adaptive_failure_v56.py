import pytest

from acfqp.construction_k7_mdl_adaptive_campaign_v56 import (
    run_mdl_adaptive_campaign_v56,
)
from acfqp.construction_k7_mdl_adaptive_failure_v56 import (
    FAILURE_ID,
    freeze_mdl_adaptive_failure_v56,
)


def test_v56_registered_failure_is_frozen_and_same_identity_is_disabled():
    document = freeze_mdl_adaptive_failure_v56()
    assert document["failure_id"] == FAILURE_ID
    assert document["campaign_artifact_returned"] is False
    assert document["failed_family"] == "COUPLED_EXCHANGE"
    assert document["failed_seed"] == 562_101
    assert document["pending_arms"] == ["STRICT_NO_PRIOR"]
    assert document["witness_blind_reachable_frontier_exhausted"] is True
    assert document["same_identity_rerun_forbidden"] is True
    assert document["fresh_successor_identity_required"] is True
    with pytest.raises(Exception, match="same-identity rerun is forbidden"):
        run_mdl_adaptive_campaign_v56()
