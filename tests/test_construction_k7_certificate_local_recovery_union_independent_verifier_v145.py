from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_certificate_local_recovery_union_independent_verifier_v145 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_certificate_local_recovery_union_verification_v145,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
SOURCE_FILES = (
    "v134_packet_batching_transfer_campaign.json",
    "v136_auto_calibrated_archive_planning_campaign.json",
    "v138_heterogeneous_cohort_planning_campaign.json",
    "v140r1_occurrence_factor_bank_planning_campaign.json",
)


def _inputs():
    return (
        (ROOT / "v145_certificate_local_recovery_union_campaign.json").read_bytes(),
        (ROOT / "v145_certificate_local_recovery_union_preregistration.json").read_bytes(),
        (ROOT / "v144r2_fifth_family_factor_bank_transfer_campaign.json").read_bytes(),
        (ROOT / "v144r2_fifth_family_factor_bank_transfer_failure.json").read_bytes(),
        (ROOT / "v144r1_fifth_family_factor_bank_transfer_campaign.json").read_bytes(),
        (ROOT / "v144r1_fifth_family_factor_bank_transfer_failure.json").read_bytes(),
        (ROOT / "v141_occurrence_factor_bank_update.json").read_bytes(),
        (ROOT / "v141_occurrence_factor_bank_update_verification.json").read_bytes(),
        tuple((ROOT / name).read_bytes() for name in SOURCE_FILES),
    )


@pytest.fixture(scope="module")
def verification():
    return loads_canonical_json(
        freeze_certificate_local_recovery_union_verification_v145(*_inputs())
    )


def test_v145_independently_rebuilds_acquisition_models_recovery_and_plans(verification):
    assert verification["producer_free_v141_factor_bank_reconstruction"] is True
    assert verification[
        "producer_free_witness_blind_acquisition_and_stop_reconstruction"
    ] is True
    assert verification["producer_free_relational_expression_lowering_reconstruction"] is True
    assert verification[
        "producer_free_model_epoch_and_local_recovery_receipt_reconstruction"
    ] is True
    assert verification["producer_free_abstract_plan_support_reconstruction"] is True
    assert verification[
        "certificate_failure_local_recovery_union_independently_verified"
    ] is True
    assert len(verification["verified_occurrences"]) == 6
    assert verification["verified_accounting"][
        "acquisition_labels_avoided_by_occurrence_factor_bank_update_prior"
    ] == 48
    assert verification["official_scalar_cost"] is None
    assert verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v145_verifier_import_surface_excludes_producers():
    path = Path(__file__).resolve().parents[1] / "src/acfqp/construction_k7_certificate_local_recovery_union_independent_verifier_v145.py"
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = (
        "construction_k7_certificate_local_recovery_union_campaign_v145",
        "certificate_local_recovery_union_campaign_core_v145",
        "fifth_family_factor_bank_transfer_acquisition_v144",
        "generic_relational_factor_execution_projection_v144",
        "certificate_local_relational_overlay_sequence_v144r1",
    )
    assert not any(name.endswith(suffix) for name in imported for suffix in forbidden)


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V145 verification not frozen")
def test_v145_frozen_verification_bytes():
    raw = (ROOT / "v145_certificate_local_recovery_union_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
