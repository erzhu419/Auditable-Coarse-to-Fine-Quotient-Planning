import os

import pytest

from acfqp.construction_k7_permutation_matched_sample_tax_campaign_v89 import (
    CAMPAIGN_ID,
    run_permutation_matched_sample_tax_campaign_v89,
)


def test_v89_campaign_identity_starts_unfrozen():
    assert CAMPAIGN_ID == "0" * 64


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_PERMUTATION_MATCHED_V89") != "1",
    reason="explicit fresh V89 campaign",
)
def test_v89_real_campaign_runs_once():
    document = run_permutation_matched_sample_tax_campaign_v89().to_document()
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"]["matched_ground_execution_identical"] is True
    assert document["sample_tax_reduction_verified"] is True
    assert document["sample_tax_measurement"]["target_labels_avoided"] > 0
    assert document["official_scalar_cost"] is None
