import os

import pytest

from acfqp.construction_k7_coordinate_aligned_target_campaign_v87r1 import (
    CAMPAIGN_ID,
    run_coordinate_aligned_target_campaign_v87r1,
    verify_coordinate_aligned_target_campaign_v87r1,
)


def test_v87r1_campaign_identity_is_frozen():
    assert CAMPAIGN_ID == (
        "33e9d49933e8b2d94169911170732b178095ce55fe52258c6ccfb9d425990739"
    )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_COORDINATE_ALIGNED_V87R1") != "1",
    reason="explicit fresh V87r1 target campaign",
)
def test_v87r1_real_campaign_runs_once():
    value = verify_coordinate_aligned_target_campaign_v87r1(
        run_coordinate_aligned_target_campaign_v87r1()
    )
    document = value.to_document()
    assert len(document["target_occurrences"]) == 6
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"][
        "actual_coordinate_aligned_completed_target_count"
    ] == 6
    assert document["v87_failure_preserved_and_not_overwritten"] is True
    assert document["sample_tax_reduction_verified"] is False
    assert document["official_scalar_cost"] is None
