import os

import pytest

from acfqp.construction_k7_total_residual_sample_tax_campaign_v63r1 import (
    run_total_residual_sample_tax_campaign_v63r1,
    verify_total_residual_sample_tax_campaign_v63r1,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V63R1") != "1",
    reason="explicit preregistered V63r1 outcome execution",
)


def test_v63r1_registered_campaign_retains_all_and_reduces_aggregate_labels():
    value = verify_total_residual_sample_tax_campaign_v63r1(
        run_total_residual_sample_tax_campaign_v63r1()
    )
    document = value.to_document()
    assert len(document["occurrences"]) == 12
    assert document["sample_tax"]["target_residual_label_reduction"] > 0
    assert document["all_registered_occurrences_retained_including_abstentions"] is True
    assert document["statistical_residual_proposal_used_as_safety_authority"] is False
    assert document["official_N_break_even"] is None
