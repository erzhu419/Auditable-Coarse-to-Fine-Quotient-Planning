from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_opaque_source_archive_independent_verifier_v132 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_opaque_source_archive_verification_v132,
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
        (ROOT / "v132_opaque_source_archive_dictionary.json").read_bytes(),
        tuple((ROOT / name).read_bytes() for name in SOURCE_FILES),
    )


def test_v132_independently_reconstructs_opaque_archive_dictionary():
    raw = freeze_opaque_source_archive_verification_v132(*_inputs())
    document = loads_canonical_json(raw)
    assert document["producer_free_dictionary_reconstruction"] is True
    assert document["opaque_content_addressed_archive_reconstruction"] is True
    assert document["source_archive_cardinality"] == 4
    assert document["selected_template_count"] == 3
    assert document[
        "every_selected_template_leave_one_artifact_positive_gain_verified"
    ] is True
    assert document["fixed_source_campaign_inventory_embedded_in_verifier"] is False
    assert document["target_outcomes_accessed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v132_verifier_import_surface_excludes_v132_producer():
    path = (
        Path(__file__).resolve().parents[1]
        / "src/acfqp/construction_k7_opaque_source_archive_independent_verifier_v132.py"
    )
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        name.endswith("opaque_source_archive_dictionary_v132") for name in imported
    )


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V132 verification not frozen")
def test_v132_frozen_independent_verification_bytes():
    raw = (ROOT / "v132_opaque_source_archive_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
