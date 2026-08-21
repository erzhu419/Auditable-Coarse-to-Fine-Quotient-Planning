from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_standalone_generic_owned_independent_verifier_v126 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_standalone_generic_owned_verification_v126,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    names = (
        "v126_standalone_generic_owned_campaign.json",
        "v125_standalone_generic_model_campaign.json",
        "v125_standalone_generic_model_verification.json",
        "v124_cross_family_generic_compiler_campaign.json",
        "v124_cross_family_generic_compiler_verification.json",
        "v123r1_generic_quotient_compiler_campaign.json",
        "v123r1_generic_quotient_compiler_verification.json",
        "v122_generic_factor_planner_campaign.json",
        "v122_generic_factor_planner_verification.json",
        "v123_generic_quotient_compiler_failure.json",
        "v121r1_generic_subprogram_campaign.json",
        "v121_generic_artifact_subprogram_campaign.json",
        "v121r1_generic_subprogram_verification.json",
    )
    return (*tuple((ROOT / name).read_bytes() for name in names), source)


def test_v126_producer_free_rebuilds_owned_loop_models_receipts_and_plans():
    raw = freeze_standalone_generic_owned_verification_v126(*_inputs())
    document = loads_canonical_json(raw)
    assert document["registered_gate_independently_verified"] is True
    assert document["producer_free_owned_episode_loop_reconstruction"] is True
    assert sum(row["independently_rebuilt_v125_model_epoch_count"] for row in document["verified_occurrences"]) == 12
    assert sum(row["independently_rebuilt_v125_receipt_count"] for row in document["verified_occurrences"]) == 16
    assert document["retained_v113_sequence_orchestration_present"] is False
    assert document["retained_v119_sequence_orchestration_present"] is False
    assert document["official_scalar_cost"] is None


def test_v126_verifier_import_surface_excludes_v126_producers_and_sequence():
    path = Path(__file__).resolve().parents[1] / "src/acfqp/construction_k7_standalone_generic_owned_independent_verifier_v126.py"
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = (
        "construction_k7_standalone_generic_owned_campaign_v126",
        "standalone_generic_owned_campaign_core_v126",
        "standalone_generic_owned_sequence_v126",
        "standalone_generic_model_epoch_v125",
    )
    assert not any(name.endswith(suffix) for name in imported for suffix in forbidden)


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V126 verification is not frozen")
def test_v126_frozen_verification_bytes():
    raw = (ROOT / "v126_standalone_generic_owned_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
