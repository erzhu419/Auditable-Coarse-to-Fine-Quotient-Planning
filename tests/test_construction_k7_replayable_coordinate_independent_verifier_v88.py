import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_replayable_coordinate_independent_verifier_v88 import (
    VERIFICATION_ID,
    ConstructionK7ReplayableCoordinateIndependentVerifierV88Error,
    verify_replayable_coordinate_campaign_bytes_v88,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v88_verifier_rejects_foreign_bytes():
    with pytest.raises(ConstructionK7ReplayableCoordinateIndependentVerifierV88Error):
        verify_replayable_coordinate_campaign_bytes_v88(b"{}")


def test_v88_verifier_has_no_campaign_producer_import():
    path = Path("src/acfqp/construction_k7_replayable_coordinate_independent_verifier_v88.py")
    imports = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("replayable_coordinate_campaign_v88" in row for row in imports)
    assert not any("generic_coordinate_alignment_v60" in row for row in imports)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REPLAYABLE_COORDINATE_V88") != "1",
    reason="explicit V88 producer-free reconstruction",
)
def test_v88_reconstructs_all_alignments_from_embedded_rows():
    raw = Path(".tmp/exact-freeze/v88_replayable_coordinate_campaign.json").read_bytes()
    result = loads_canonical_json(verify_replayable_coordinate_campaign_bytes_v88(raw))
    assert result["independently_rederived_alignment_count"] == 6
    assert result["every_alignment_rederived_from_embedded_raw_rows"] is True
    assert result["registered_target_gate_verified"] is True
    assert result["sample_tax_reduction_verified"] is False
    assert result["official_scalar_cost"] is None


def test_v88_verification_identity_is_frozen():
    assert VERIFICATION_ID == "e176b3b775511c2c98e650e99fdb183555833ca5c4638bc7fc5d4b6f998be327"
