from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_unified_factor_prior_ablation_campaign_v129 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    run_unified_factor_prior_ablation_campaign_v129,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    return source, (ROOT / "v128_third_family_owned_sequence_campaign.json").read_bytes(), (ROOT / "v128_third_family_owned_sequence_verification.json").read_bytes()


def test_v129_frozen_campaign_identity_sample_tax_and_claim_locks():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("registered V129 outcome has not been executed")
    raw = (ROOT / "v129_unified_factor_prior_ablation_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["registered_workload_sample_efficiency_improvement_observed"] is True
    assert document["accounting"]["acquisition_labels_avoided_by_factor_prior"] > 0
    assert document["sample_efficiency_improvement_claim_scope"] == "ONLY_THE_PREREGISTERED_V129_THREE_FAMILY_WORKLOAD"
    assert document["official_scalar_cost"] is None


@pytest.mark.skipif(CAMPAIGN_ID != "0" * 64, reason="frozen identity is never rerun")
def test_v129_registered_campaign_runs_only_before_freeze():
    assert run_unified_factor_prior_ablation_campaign_v129(*_inputs()).to_document()["registered_gate"]["passed"] is True
