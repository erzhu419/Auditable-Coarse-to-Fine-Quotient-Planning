from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_auto_calibrated_archive_planning_independent_verifier_v136 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_auto_calibrated_archive_planning_verification_v136,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
SOURCE_FILES = (
    "v116_cross_epoch_program_branch_campaign.json",
    "v117_dependency_derived_program_branch_campaign.json",
    "v118_fourth_family_inventory_campaign.json",
    "v119_source_unseen_residual_campaign.json",
)


def _inputs():
    return (
        (ROOT / "v136_auto_calibrated_archive_planning_campaign.json").read_bytes(),
        (ROOT / "v136_auto_calibrated_archive_planning_preregistration.json").read_bytes(),
        (ROOT / "v135_auto_calibrated_archive_dictionary.json").read_bytes(),
        (ROOT / "v135_auto_calibrated_archive_verification.json").read_bytes(),
        tuple((ROOT / name).read_bytes() for name in SOURCE_FILES),
    )


@pytest.fixture(scope="module")
def verification():
    return loads_canonical_json(
        freeze_auto_calibrated_archive_planning_verification_v136(*_inputs())
    )


def test_v136_independently_rebuilds_calibration_acquisition_and_plans(verification):
    assert verification[
        "producer_free_v135_threshold_grid_and_dictionary_reconstruction"
    ] is True
    assert verification["producer_free_path_first_acquisition_reconstruction"] is True
    assert verification[
        "producer_free_model_epoch_receipt_and_plan_reconstruction"
    ] is True
    assert verification["verified_dictionary_receipt_reaches_compiled_planner"] is True
    assert len(verification["verified_occurrences"]) == 4
    assert verification[
        "registered_workload_sample_efficiency_improvement_independently_verified"
    ] is True
    assert verification["official_scalar_cost"] is None
    assert verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v136_verifier_import_surface_excludes_v136_producers():
    path = (
        Path(__file__).resolve().parents[1]
        / "src/acfqp/construction_k7_auto_calibrated_archive_planning_independent_verifier_v136.py"
    )
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        name.endswith("construction_k7_auto_calibrated_archive_planning_campaign_v136")
        or name.endswith("auto_calibrated_archive_planning_campaign_core_v136")
        or name.endswith("auto_calibrated_archive_factor_acquisition_v136")
        for name in imported
    )


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V136 verification not frozen")
def test_v136_frozen_independent_verification_bytes():
    raw = (ROOT / "v136_auto_calibrated_archive_planning_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
