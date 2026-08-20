from acfqp.construction_k7_three_family_failure_v76 import (
    freeze_three_family_failure_v76,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v76_failure_preserves_source_abstention_before_targets():
    document = loads_canonical_json(freeze_three_family_failure_v76())
    assert document["campaign_issued"] is False
    assert document["failed_family"] == "BALANCED_BATCH_REFINEMENT"
    assert document["failed_source_seed"] == 751_102
    assert document["target_execution_started"] is False
    assert document["same_identity_rerun_allowed"] is False
    assert document["registered_gate_evaluated"] is False
