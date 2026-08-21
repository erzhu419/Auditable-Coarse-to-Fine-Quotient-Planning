from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_heterogeneous_archive_independent_verifier_v137 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_heterogeneous_archive_verification_v137,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
SOURCE_FILES = (
    "v116_cross_epoch_program_branch_campaign.json",
    "v117_dependency_derived_program_branch_campaign.json",
    "v118_fourth_family_inventory_campaign.json",
    "v119_source_unseen_residual_campaign.json",
    "v134_packet_batching_transfer_campaign.json",
)


def _inputs():
    return (
        (ROOT / "v137_heterogeneous_archive_cohort_dictionary.json").read_bytes(),
        tuple((ROOT / name).read_bytes() for name in SOURCE_FILES),
    )


@pytest.fixture(scope="module")
def verification():
    return loads_canonical_json(
        freeze_heterogeneous_archive_verification_v137(*_inputs())
    )


def test_v137_independently_reconstructs_cohort_search(verification):
    assert verification["producer_free_full_and_leave_one_cohort_search"] is True
    assert verification["producer_free_auto_calibration_reconstruction"] is True
    assert verification["complete_source_archive_cardinality"] == 5
    assert verification["selected_cohort_cardinality"] == 4
    assert len(verification["excluded_archive_artifact_sha256s"]) == 1
    assert verification["incompatible_sources_recorded_not_silently_dropped"] is True
    assert verification["target_outcomes_accessed"] is False
    assert verification["official_scalar_cost"] is None


def test_v137_verifier_import_surface_excludes_v137_and_v135_producers():
    path = (
        Path(__file__).resolve().parents[1]
        / "src/acfqp/construction_k7_heterogeneous_archive_independent_verifier_v137.py"
    )
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        name.endswith("heterogeneous_archive_cohort_dictionary_v137")
        or name.endswith("auto_calibrated_archive_dictionary_v135")
        for name in imported
    )


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V137 verification not frozen")
def test_v137_frozen_independent_verification_bytes():
    raw = (ROOT / "v137_heterogeneous_archive_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
