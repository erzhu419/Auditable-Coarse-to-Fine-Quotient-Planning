import os

import pytest

from acfqp.construction_k7_residual_amortization_campaign_v64 import (
    run_residual_amortization_campaign_v64,
    verify_residual_amortization_campaign_v64,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V64") != "1",
    reason="explicit preregistered V64 outcome execution",
)


def test_v64_registered_campaign_amortizes_offline_label_tax():
    value = verify_residual_amortization_campaign_v64(
        run_residual_amortization_campaign_v64()
    )
    document = value.to_document()
    assert document["target_occurrence_count"] == 72
    assert document["offline_tax_amortized_on_fresh_registered_occurrences"] is True
    assert document["observed_lifetime_label_saving"] >= 0
    assert document["statistical_residual_proposal_used_as_safety_authority"] is False
    assert document["official_N_break_even"] is None
