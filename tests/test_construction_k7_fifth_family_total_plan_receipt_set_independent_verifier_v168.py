import ast
import hashlib
from pathlib import Path

import pytest

from acfqp.construction_k7_fifth_family_total_plan_receipt_set_independent_verifier_v168 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    RECEIPT_SET_TRUTH_TABLE,
    VERIFICATION_ID,
    ConstructionK7FifthFamilyTotalPlanReceiptSetIndependentVerifierV168Error,
    freeze_fifth_family_total_plan_receipt_set_verification_v168,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _inputs(campaign=None):
    return (
        (
            FREEZE / "v168_fifth_family_total_plan_receipt_set_campaign.json"
        ).read_bytes()
        if campaign is None
        else campaign,
        (
            FREEZE
            / "v168_fifth_family_total_plan_receipt_set_preregistration.json"
        ).read_bytes(),
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        (FREEZE / "v167_fourth_family_plan_mode_set_campaign.json").read_bytes(),
        (
            FREEZE / "v167_fourth_family_plan_mode_set_verification.json"
        ).read_bytes(),
    )


def test_v168_verifier_has_no_v168_producer_or_core_import():
    path = (
        ROOT
        / "src/acfqp/construction_k7_fifth_family_total_plan_receipt_set_independent_verifier_v168.py"
    )
    tree = ast.parse(path.read_text())
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.fifth_family_total_plan_receipt_set_campaign_core_v168" not in imported
    assert (
        "acfqp.construction_k7_fifth_family_total_plan_receipt_set_campaign_v168"
        not in imported
    )


def test_v168_truth_table_covers_direct_memoized_mixed_and_none():
    assert [row["receipt_set_class"] for row in RECEIPT_SET_TRUTH_TABLE] == [
        "DIRECT_ONLY",
        "MEMOIZED_ONLY",
        "MIXED",
        "NONE",
    ]
    assert RECEIPT_SET_TRUTH_TABLE[-1][
        "none_defers_to_v109_and_query_local_certificate"
    ] is True


def test_v168_frozen_producer_free_verification():
    if VERIFICATION_ID == "0" * 64:
        pytest.skip("V168 verification not frozen")
    raw = freeze_fifth_family_total_plan_receipt_set_verification_v168(*_inputs())
    frozen = (
        FREEZE
        / "v168_fifth_family_total_plan_receipt_set_verification.json"
    ).read_bytes()
    assert raw == frozen
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document[
        "fifth_family_factor_prior_sample_tax_transfer_independently_verified"
    ] is True
    assert document["query_policy_labels_avoided_vs_exact_path_first"] == 0
    assert document["factor_prior_labels_avoided_within_same_query_policy"] == 16
    assert document["query_policy_or_receipt_set_annotation_is_safety_authority"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v168_rejects_frozen_campaign_tamper_before_reconstruction():
    document = loads_canonical_json(_inputs()[0])
    document["official_execution_allowed"] = True
    with pytest.raises(
        ConstructionK7FifthFamilyTotalPlanReceiptSetIndependentVerifierV168Error,
        match="frozen campaign changed",
    ):
        freeze_fifth_family_total_plan_receipt_set_verification_v168(
            *_inputs(canonical_json_bytes(document))
        )
