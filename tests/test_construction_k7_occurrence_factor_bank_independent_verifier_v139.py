from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_occurrence_factor_bank_independent_verifier_v139 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_occurrence_factor_bank_verification_v139,
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
        (ROOT / "v139_occurrence_factor_bank.json").read_bytes(),
        tuple((ROOT / name).read_bytes() for name in SOURCE_FILES),
    )


def test_v139_independently_reconstructs_occurrence_factor_bank():
    raw = freeze_occurrence_factor_bank_verification_v139(*_inputs())
    document = loads_canonical_json(raw)
    assert document[
        "producer_free_campaign_occurrence_candidate_reconstruction"
    ] is True
    assert document[
        "producer_free_support_threshold_and_factor_bank_reconstruction"
    ] is True
    assert document["source_occurrence_archive_cardinality"] == 12
    assert document["selected_minimum_distinct_occurrence_support"] == 7
    assert document["selected_template_count"] == 5
    assert document["selected_cross_schema_template_count"] == 5
    assert document["robust_candidate_schema_decoded"] is True
    assert document["new_target_outcomes_accessed"] is False
    assert document["official_scalar_cost"] is None


def test_v139_verifier_import_surface_excludes_v139_producer():
    path = (
        Path(__file__).resolve().parents[1]
        / "src/acfqp/construction_k7_occurrence_factor_bank_independent_verifier_v139.py"
    )
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(name.endswith("occurrence_factor_bank_v139") for name in imported)


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V139 verification not frozen")
def test_v139_frozen_independent_verification_bytes():
    raw = (ROOT / "v139_occurrence_factor_bank_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
