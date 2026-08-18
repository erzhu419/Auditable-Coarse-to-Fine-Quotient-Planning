import pytest

from acfqp.construction_k7_universal_mixture_campaign_v58 import (
    run_universal_mixture_campaign_v58,
)
from acfqp.construction_k7_universal_mixture_failure_v58 import (
    FAILURE_ID,
    freeze_universal_mixture_failure_v58,
)


def test_v58_registered_failure_is_frozen_and_same_identity_is_disabled():
    document = freeze_universal_mixture_failure_v58()
    assert document["failure_id"] == FAILURE_ID
    assert document["campaign_artifact_returned"] is False
    assert document["failed_family"] == "MAINTENANCE_CASCADE"
    assert document["failed_seed"] == 583_110
    assert document["pending_arms"] == ["STRICT_NO_PRIOR"]
    assert document["same_identity_rerun_forbidden"] is True
    assert document["fresh_successor_identity_required"] is True
    assert document["successor_must_not_restore_frontier_exhaustion_stop"] is True
    with pytest.raises(Exception, match="rerun forbidden"):
        run_universal_mixture_campaign_v58()
