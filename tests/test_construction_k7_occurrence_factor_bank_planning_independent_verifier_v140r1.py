from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_occurrence_factor_bank_planning_independent_verifier_v140r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_occurrence_factor_bank_planning_verification_v140r1,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
SOURCE_FILES = (
    "v134_packet_batching_transfer_campaign.json",
    "v136_auto_calibrated_archive_planning_campaign.json",
    "v138_heterogeneous_cohort_planning_campaign.json",
)


def _inputs():
    return (
        (ROOT / "v140r1_occurrence_factor_bank_planning_campaign.json").read_bytes(),
        (ROOT / "v140r1_occurrence_factor_bank_planning_preregistration.json").read_bytes(),
        (ROOT / "v139_occurrence_factor_bank.json").read_bytes(),
        (ROOT / "v139_occurrence_factor_bank_verification.json").read_bytes(),
        (ROOT / "v140_occurrence_factor_bank_planning_failure.json").read_bytes(),
        tuple((ROOT / name).read_bytes() for name in SOURCE_FILES),
    )


@pytest.fixture(scope="module")
def verification():
    return loads_canonical_json(
        freeze_occurrence_factor_bank_planning_verification_v140r1(*_inputs())
    )


def test_v140r1_independently_rebuilds_factor_bank_acquisition_and_plans(verification):
    assert verification[
        "producer_free_v139_occurrence_factor_bank_reconstruction"
    ] is True
    assert verification[
        "producer_free_v140_failed_predecessor_preservation_verified"
    ] is True
    assert verification["producer_free_path_first_acquisition_reconstruction"] is True
    assert verification[
        "producer_free_model_epoch_receipt_and_plan_reconstruction"
    ] is True
    assert verification["verified_factor_bank_receipt_reaches_compiled_planner"] is True
    assert len(verification["verified_occurrences"]) == 4
    assert verification[
        "registered_workload_sample_efficiency_improvement_independently_verified"
    ] is True
    assert verification["official_scalar_cost"] is None
    assert verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v140r1_verifier_import_surface_excludes_v140r1_producers():
    path = (
        Path(__file__).resolve().parents[1]
        / "src/acfqp/construction_k7_occurrence_factor_bank_planning_independent_verifier_v140r1.py"
    )
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        name.endswith("construction_k7_occurrence_factor_bank_planning_campaign_v140r1")
        or name.endswith("occurrence_factor_bank_planning_campaign_core_v140r1")
        or name.endswith("occurrence_factor_bank_acquisition_v140r1")
        for name in imported
    )


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V140r1 verification not frozen")
def test_v140r1_frozen_independent_verification_bytes():
    raw = (ROOT / "v140r1_occurrence_factor_bank_planning_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
