from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_opaque_archive_planning_independent_verifier_v133 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_opaque_archive_planning_verification_v133,
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
        (ROOT / "v133_opaque_archive_planning_campaign.json").read_bytes(),
        (ROOT / "v133_opaque_archive_planning_preregistration.json").read_bytes(),
        (ROOT / "v132_opaque_source_archive_dictionary.json").read_bytes(),
        (ROOT / "v132_opaque_source_archive_verification.json").read_bytes(),
        tuple((ROOT / name).read_bytes() for name in SOURCE_FILES),
    )


def test_v133_producer_free_rebuilds_receipt_acquisition_models_and_plans():
    raw = freeze_opaque_archive_planning_verification_v133(*_inputs())
    document = loads_canonical_json(raw)
    assert document["producer_free_v132_dictionary_reconstruction"] is True
    assert document["producer_free_path_first_acquisition_reconstruction"] is True
    assert document[
        "producer_free_model_epoch_receipt_and_plan_reconstruction"
    ] is True
    assert document["verified_dictionary_receipt_reaches_compiled_planner"] is True
    assert document[
        "registered_workload_sample_efficiency_improvement_independently_verified"
    ] is True
    assert document["verified_accounting"][
        "acquisition_labels_avoided_by_opaque_archive_prior"
    ] == 46
    assert document["fixed_source_campaign_inventory_reintroduced"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v133_verifier_import_surface_excludes_v133_producers():
    path = (
        Path(__file__).resolve().parents[1]
        / "src/acfqp/construction_k7_opaque_archive_planning_independent_verifier_v133.py"
    )
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = (
        "construction_k7_opaque_archive_planning_campaign_v133",
        "construction_k7_opaque_archive_planning_preregistration_v133",
        "opaque_archive_planning_campaign_core_v133",
        "opaque_archive_factor_acquisition_v133",
    )
    assert not any(
        name.endswith(suffix) for name in imported for suffix in forbidden
    )


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V133 verification not frozen")
def test_v133_frozen_independent_verification_bytes():
    raw = (ROOT / "v133_opaque_archive_planning_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
