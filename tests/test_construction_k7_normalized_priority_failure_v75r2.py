from acfqp.construction_k7_normalized_priority_failure_v75r2 import (
    freeze_normalized_priority_failure_v75r2,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v75r2_failure_preserves_failed_arm_aggregation_error():
    document = loads_canonical_json(freeze_normalized_priority_failure_v75r2())
    assert document["campaign_issued"] is False
    assert document["target_process_pool_completed_before_failure"] is True
    assert document["partial_target_outcomes_recovered_or_claimed"] is False
    assert document["registered_gate_evaluated"] is False
    assert document["same_identity_rerun_allowed"] is False
    assert document["corrective_successor_requires_fresh_target_identities"] is True
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
