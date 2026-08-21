from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_auto_calibrated_archive_independent_verifier_v135 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_auto_calibrated_archive_verification_v135,
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
        (ROOT / "v135_auto_calibrated_archive_dictionary.json").read_bytes(),
        tuple((ROOT / name).read_bytes() for name in SOURCE_FILES),
    )


def test_v135_independently_reconstructs_threshold_grid_and_dictionary():
    raw = freeze_auto_calibrated_archive_verification_v135(*_inputs())
    document = loads_canonical_json(raw)
    assert document["producer_free_threshold_grid_reconstruction"] is True
    assert document["producer_free_dictionary_reconstruction"] is True
    assert document["source_archive_cardinality"] == 4
    assert document["support_threshold_search_row_count"] > 1
    assert document["selected_minimum_distinct_artifact_support"] == 3
    assert document["selected_minimum_distinct_schema_pair_support"] == 2
    assert document["selected_template_count"] == 3
    assert document["selected_summed_weakest_leave_one_prefix_gain_bits"] == 4_891
    assert document["support_thresholds_supplied_by_caller"] is False
    assert document["target_outcomes_accessed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v135_verifier_import_surface_excludes_v135_and_v132_producers():
    path = (
        Path(__file__).resolve().parents[1]
        / "src/acfqp/construction_k7_auto_calibrated_archive_independent_verifier_v135.py"
    )
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        name.endswith("auto_calibrated_archive_dictionary_v135")
        or name.endswith("opaque_source_archive_dictionary_v132")
        for name in imported
    )


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V135 verification not frozen")
def test_v135_frozen_independent_verification_bytes():
    raw = (ROOT / "v135_auto_calibrated_archive_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
