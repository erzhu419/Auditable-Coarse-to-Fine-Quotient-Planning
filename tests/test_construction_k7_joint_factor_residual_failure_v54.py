import pytest

from acfqp.construction_k7_joint_factor_residual_campaign_v54 import (
    run_joint_factor_residual_campaign_v54,
)
from acfqp.construction_k7_joint_factor_residual_failure_v54 import (
    FAILURE_ID,
    freeze_joint_factor_residual_failure_v54,
)


def test_v54_registered_failure_is_frozen_and_same_identity_is_disabled():
    document = freeze_joint_factor_residual_failure_v54()
    assert document["failure_id"] == FAILURE_ID
    assert document["campaign_artifact_returned"] is False
    assert document["failure_stage"] == "HELD_OUT_ANONYMOUS_LAYOUT_CALIBRATION"
    assert document["same_identity_rerun_forbidden"] is True
    assert document["fresh_successor_identity_required"] is True
    with pytest.raises(Exception, match="same-identity rerun is forbidden"):
        run_joint_factor_residual_campaign_v54()
