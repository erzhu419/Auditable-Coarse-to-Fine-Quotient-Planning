import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_coordinate_aligned_target_independent_verifier_v87r1 import (
    VERIFICATION_ID,
    ConstructionK7CoordinateAlignedTargetIndependentVerifierV87R1Error,
    verify_coordinate_aligned_target_campaign_bytes_v87r1,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v87r1_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(
        ConstructionK7CoordinateAlignedTargetIndependentVerifierV87R1Error
    ):
        verify_coordinate_aligned_target_campaign_bytes_v87r1(b"{}")


def test_v87r1_independent_verifier_import_surface_excludes_producers():
    path = Path(
        "src/acfqp/construction_k7_coordinate_aligned_target_independent_verifier_v87r1.py"
    )
    tree = ast.parse(path.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(
        "coordinate_aligned_target_campaign" in row
        or "generic_coordinate_alignment" in row
        or "generic_coordinate_aligned_certificate" in row
        for row in imports
    )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_COORDINATE_ALIGNED_V87R1") != "1",
    reason="explicit producer-free V87r1 replay",
)
def test_v87r1_independent_verifier_replays_frozen_campaign():
    raw = Path(
        ".tmp/exact-freeze/v87r1_coordinate_aligned_target_campaign.json"
    ).read_bytes()
    result = loads_canonical_json(
        verify_coordinate_aligned_target_campaign_bytes_v87r1(raw)
    )
    assert result["coordinate_aligned_completed_target_count"] == 6
    assert result["registered_target_gate_verified"] is True
    assert result["alignment_content_id_and_input_hash_replayed"] is True
    assert result["alignment_rederived_from_embedded_raw_rows"] is False
    assert result["sample_tax_reduction_verified"] is False
    assert result["official_scalar_cost"] is None


def test_v87r1_verification_identity_is_frozen():
    assert VERIFICATION_ID == (
        "9a5fdb135fcebe2e4a31077e7a542d9af2338ecb1c2d76eda1e3f4f72eedd29d"
    )
