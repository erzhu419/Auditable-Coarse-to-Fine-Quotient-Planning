from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_plan_mode_margin_independent_verifier_v157 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_plan_mode_margin_verification_v157,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_plan_mode_margin_verification_v157(
        (FREEZE / "v157_plan_mode_margin_campaign.json").read_bytes(),
        (FREEZE / "v157_plan_mode_margin_preregistration.json").read_bytes(),
        (FREEZE / "v156_structural_margin_query_guard_receipt.json").read_bytes(),
        (FREEZE / "v157_plan_mode_correction_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        (FREEZE / "v156_structural_margin_guarded_campaign.json").read_bytes(),
        (FREEZE / "v156_structural_margin_guarded_failure.json").read_bytes(),
    )


def test_v157_verifier_imports_no_v157_or_v156_producer_core_or_operator():
    source = (ROOT / "src/acfqp/construction_k7_plan_mode_margin_independent_verifier_v157.py").read_text()
    imported = {node.module or "" for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)}
    forbidden = (
        "construction_k7_plan_mode_margin_campaign_v157",
        "plan_mode_margin_campaign_core_v157",
        "structural_margin_guarded_campaign_core_v156",
        "structural_margin_guarded_acquisition_operator_v156",
    )
    assert not any(any(fragment in name for fragment in forbidden) for name in imported)


def test_v157_frozen_independent_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V157 independent verification not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["registered_plan_mode_corrected_margin_evidence_independently_verified"] is True
    assert document["guard_sample_reduction_vs_legacy_prior"] == 383
    assert document["factor_prior_sample_reduction_within_guarded_operator"] == 20
    assert document["official_scalar_cost"] is None
