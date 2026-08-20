import os

import pytest

from acfqp.construction_k7_successor_version_space_campaign_v72r1 import (
    run_successor_version_space_campaign_v72r1,
    verify_successor_version_space_campaign_v72r1,
)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V72R1") != "1",
    reason="explicit preregistered V72r1 successor campaign",
)
def test_v72r1_registered_campaign_is_frozen():
    value = verify_successor_version_space_campaign_v72r1(
        run_successor_version_space_campaign_v72r1()
    )
    document = value.to_document()
    assert len(document["occurrences"]) == 6
    assert document["registered_gate"]["zero_heldout_failed_proposals_in_both_arms"] is True
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["all_axes_separate"] is True
    assert document["official_scalar_cost"] is None


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V72R1") != "1",
    reason="explicit preregistered V72r1 successor campaign",
)
def test_v72r1_retains_matched_arms_and_ood_controls():
    document = run_successor_version_space_campaign_v72r1().to_document()
    for occurrence in document["occurrences"]:
        assert occurrence["same_target_query_pool_in_both_arms"] is True
        assert occurrence["same_query_schedule_in_both_arms"] is True
        assert occurrence["same_v41_version_space_and_stop_engine_in_both_arms"] is True
        assert occurrence["incompatible_schema_ood_control"]["status"] == "INCOMPATIBLE_SCHEMA_REJECTED"
