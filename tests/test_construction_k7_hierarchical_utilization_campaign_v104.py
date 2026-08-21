import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_hierarchical_utilization_campaign_v104 as campaign


def test_v104_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(campaign.ConstructionK7HierarchicalUtilizationCampaignV104Error):
        campaign.run_hierarchical_utilization_campaign_v104(b"", b"", b"", b"")


def test_v104_exact_success_is_preserved():
    raw = Path(".tmp/exact-freeze/v104_hierarchical_utilization_campaign.json").read_bytes()
    document = campaign.loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"]["passed_target_occurrence_count"] == 4
    assert document["accounting"]["meta_abstract_model_ordered_execution_count"] == 67
    assert document["accounting"]["meta_full_post_dependency_world_model_match_count"] == 12
    assert document["accounting"]["meta_compiled_partial_world_model_fallback_match_count"] == 55
    assert document["accounting"]["meta_exact_certificate_policy_only_count"] == 0
    assert document["partial_world_model_primary_ordering_verified"] is True
    assert document["full_post_dependency_world_model_primary_ordering_verified"] is False
    assert document["complete_world_model_synthesized"] is False
