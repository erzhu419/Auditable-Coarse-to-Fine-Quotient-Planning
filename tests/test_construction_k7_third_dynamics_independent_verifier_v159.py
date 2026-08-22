from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_third_dynamics_independent_verifier_v159 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_third_dynamics_verification_v159,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _run():
    return freeze_third_dynamics_verification_v159(
        (FREEZE / "v159_third_dynamics_campaign.json").read_bytes(),
        (FREEZE / "v159_third_dynamics_preregistration.json").read_bytes(),
        (FREEZE / "v159_joint_factor_query_classifier_receipt.json").read_bytes(),
        (
            FREEZE / "v159_joint_factor_query_source_preregistration.json"
        ).read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        (FREEZE / "v157_plan_mode_margin_campaign.json").read_bytes(),
        (FREEZE / "v157_plan_mode_margin_verification.json").read_bytes(),
    )


def test_v159_verifier_imports_no_target_or_classifier_producer():
    source = (
        ROOT
        / "src/acfqp/construction_k7_third_dynamics_independent_verifier_v159.py"
    ).read_text()
    imported = {
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    forbidden = (
        "construction_k7_third_dynamics_campaign_v159",
        "construction_k7_third_dynamics_preregistration_v159",
        "third_dynamics_joint_factor_query_campaign_core_v159",
        "joint_factor_query_acquisition_operator_v159",
        "construction_k7_joint_factor_query_classifier_receipt_v159",
    )
    assert not any(
        any(fragment in name for fragment in forbidden) for name in imported
    )


def test_v159_frozen_independent_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V159 independent verification not frozen")
    raw = _run()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["third_dynamics_joint_factor_query_evidence_independently_verified"] is True
    assert document["factor_prior_sample_reduction_within_joint_policy"] == 32
    assert document["target_factorization_audit_labels"] == 3
    assert document["official_scalar_cost"] is None
