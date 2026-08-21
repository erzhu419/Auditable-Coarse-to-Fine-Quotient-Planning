from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_robust_factor_dictionary_campaign_v131r2 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v131r2_frozen_campaign_identity_robust_dictionary_and_claim_locks():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("registered V131R2 outcome has not been executed")
    raw = (ROOT / "v131r2_robust_factor_dictionary_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["robust_factor_dictionary_selected_template_count"] == 3
    assert document["registered_gate"][
        "robust_dictionary_cardinality_not_preregistered"
    ] is True
    assert document[
        "registered_workload_sample_efficiency_improvement_observed"
    ] is True
    assert document["accounting"][
        "acquisition_labels_avoided_by_normalized_factor_prior"
    ] > 0
    assert all(
        row["accounting"][
            "acquisition_labels_avoided_by_normalized_factor_prior"
        ]
        > 0
        for row in document["target_occurrences"]
    )
    assert document[
        "fixed_two_to_library_cardinality_prior_multiplier_present"
    ] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
