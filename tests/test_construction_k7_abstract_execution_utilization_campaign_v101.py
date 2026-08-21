import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_abstract_execution_utilization_campaign_v101 as campaign
from acfqp.phase3e_ids import loads_canonical_json


def test_v101_frozen_failure_will_not_rerun_the_same_identity():
    assert campaign.pre.PREREGISTRATION_ID == (
        "336139087db95530d912e3a3b027d14eb0e8aa4cbfc350fd979245107cc9ac9e"
    )
    assert campaign.CAMPAIGN_ID == (
        "f6cafbcdb148095f351202764d97550b1fda115e290dd8de3f205f62762ae155"
    )
    with pytest.raises(
        campaign.ConstructionK7AbstractExecutionUtilizationCampaignV101Error
    ):
        campaign.run_abstract_execution_utilization_campaign_v101(
            b"", b"", b"", b""
        )


def test_v101_exact_registered_failure_is_preserved():
    raw = Path(
        ".tmp/exact-freeze/v101_abstract_execution_utilization_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"]["passed_target_occurrence_count"] == 3
    assert document["registered_gate"][
        "every_occurrence_abstract_orders_strict_majority_of_executed_actions"
    ] is True
    assert document["accounting"]["meta_abstract_execution_match_count"] == 50
    assert document["accounting"]["meta_execution_step_count"] == 74
    failed = [
        row for row in document["target_occurrences"]
        if row["registered_gate"]["passed"] is False
    ]
    assert len(failed) == 1
    assert failed[0]["seed"] == 1_011_102
    assert failed[0]["frozen_v100_sequence_wide_observation"][
        "sequence_wide_path_coverage"
    ]["persistent_sequence_disagreement_abstention_count"] == 0
    assert document["complete_world_model_synthesized"] is False
