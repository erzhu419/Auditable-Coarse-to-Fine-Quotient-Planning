import hashlib
import os

import pytest

from acfqp.construction_k7_residual_sample_tax_campaign_v63 import (
    REGISTERED_FAILURE_ID,
    registered_failure_document_v63,
    run_residual_sample_tax_campaign_v63,
    verify_residual_sample_tax_campaign_v63,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V63") != "1",
    reason="explicit preregistered V63 outcome execution",
)


def test_v63_registered_campaign_closes_matched_sample_tax_gate():
    if REGISTERED_FAILURE_ID:
        failure = registered_failure_document_v63()
        assert failure["registered_failure_id"] == REGISTERED_FAILURE_ID
        assert failure["same_identity_rerun_allowed"] is False
        with pytest.raises(Exception):
            run_residual_sample_tax_campaign_v63()
        return
    value = verify_residual_sample_tax_campaign_v63(
        run_residual_sample_tax_campaign_v63()
    )
    document = value.to_document()
    assert document["sample_tax"]["target_residual_label_reduction"] > 0
    assert all(
        row["residual_label_reduction"] > 0
        for row in document["sample_tax"]["family_projections"].values()
    )
    assert document["all_ground_queries_followed_failed_certificates"] is True
    assert document["statistical_residual_proposal_used_as_safety_authority"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_N_break_even"] is None
    assert len(document["occurrences"]) == 12
    assert len(hashlib.sha256(value.canonical_bytes).hexdigest()) == 64
