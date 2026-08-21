from pathlib import Path
import hashlib

import pytest

from acfqp.construction_k7_generic_quotient_compiler_campaign_v123r1 import (
    CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    run_generic_quotient_compiler_campaign_v123r1,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    sources = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    return (
        sources,
        (ROOT / "v122_generic_factor_planner_campaign.json").read_bytes(),
        (ROOT / "v122_generic_factor_planner_verification.json").read_bytes(),
        (ROOT / "v123_generic_quotient_compiler_failure.json").read_bytes(),
    )


def test_v123r1_frozen_campaign_identity_and_claim_locks():
    if CAMPAIGN_ID == "0" * 64:
        pytest.skip("registered V123r1 outcome has not been executed")
    raw = (ROOT / "v123r1_generic_quotient_compiler_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["campaign_id"] == CAMPAIGN_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_gate"]["passed"] is True
    assert document["same_failed_v123_identity_rerun"] is False
    assert document["legacy_shape_specific_model_builder_used_as_planning_input"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


@pytest.mark.skipif(CAMPAIGN_ID != "0" * 64, reason="frozen identity is never rerun")
def test_v123r1_registered_campaign_runs_only_before_freeze():
    value = run_generic_quotient_compiler_campaign_v123r1(*_inputs())
    assert value.to_document()["registered_gate"]["passed"] is True
