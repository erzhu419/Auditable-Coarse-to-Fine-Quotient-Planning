import os

import pytest

from acfqp.construction_k7_successor_version_space_campaign_v72 import (
    run_successor_version_space_campaign_v72,
    verify_successor_version_space_campaign_v72,
)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V72") != "1",
    reason="explicit preregistered V72 successor-version-space campaign",
)
def test_v72_registered_campaign_is_frozen_and_retains_all_outcomes():
    value = verify_successor_version_space_campaign_v72(
        run_successor_version_space_campaign_v72()
    )
    document = value.to_document()
    assert len(document["occurrences"]) == 6
    assert document["registered_gate"]["zero_heldout_failed_proposals_in_both_arms"] is True
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["all_axes_separate"] is True
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V72") != "1",
    reason="explicit preregistered V72 successor-version-space campaign",
)
def test_v72_matched_arms_share_queries_schedule_and_guard():
    document = run_successor_version_space_campaign_v72().to_document()
    for occurrence in document["occurrences"]:
        assert occurrence["same_target_query_pool_in_both_arms"] is True
        assert occurrence["same_query_schedule_in_both_arms"] is True
        assert occurrence["same_v41_version_space_and_stop_engine_in_both_arms"] is True
        assert occurrence["only_terminal_program_prior_switched"] is True
        assert occurrence["incompatible_schema_ood_control"]["status"] == "INCOMPATIBLE_SCHEMA_REJECTED"
