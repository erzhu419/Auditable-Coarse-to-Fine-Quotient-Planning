import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_successor_version_space_campaign_v72r1 import (
    run_successor_version_space_campaign_v72r1,
)
from acfqp.construction_k7_successor_version_space_independent_verifier_v72r1 import (
    verify_successor_version_space_campaign_bytes_v72r1,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v72r1_verifier_source_has_no_producer_core_v41_or_v39_import():
    path = Path(
        "src/acfqp/construction_k7_successor_version_space_independent_verifier_v72r1.py"
    )
    tree = ast.parse(path.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any("campaign_v72r1" in name for name in imported)
    assert not any("campaign_core_v72" in name for name in imported)
    assert not any("generic_learned_successor_support_acquisition_v41" in name for name in imported)
    assert not any("generic_relation_covering_schedule_v39" in name for name in imported)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V72R1") != "1",
    reason="explicit producer-free V72r1 reconstruction",
)
def test_v72r1_producer_free_reconstruction_matches_frozen_campaign():
    campaign = run_successor_version_space_campaign_v72r1()
    raw = verify_successor_version_space_campaign_bytes_v72r1(
        campaign.canonical_bytes
    )
    document = loads_canonical_json(raw)
    assert document["status"] == "PRODUCER_FREE_SUCCESSOR_VERSION_SPACE_EVIDENCE_VERIFIED"
    assert document["successor_version_space_arm_histories_reconstructed"] == 12
    assert document["prior_minus_strict_labels"] == -33
    assert document["official_scalar_cost"] is None


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V72R1") != "1",
    reason="explicit producer-free V72r1 reconstruction",
)
def test_v72r1_verifier_rejects_tampered_campaign_bytes():
    raw = bytearray(run_successor_version_space_campaign_v72r1().canonical_bytes)
    raw[-2] = ord("0") if raw[-2] != ord("0") else ord("1")
    with pytest.raises(Exception):
        verify_successor_version_space_campaign_bytes_v72r1(bytes(raw))
