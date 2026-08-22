import ast
import hashlib
from pathlib import Path

import pytest

from acfqp.construction_k7_fourth_family_plan_mode_set_independent_verifier_v167 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    ConstructionK7FourthFamilyPlanModeSetIndependentVerifierV167Error,
    freeze_fourth_family_plan_mode_set_verification_v167,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def _inputs(campaign=None):
    return (
        (FREEZE / "v167_fourth_family_plan_mode_set_campaign.json").read_bytes()
        if campaign is None
        else campaign,
        (FREEZE / "v167_fourth_family_plan_mode_set_preregistration.json").read_bytes(),
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        (FREEZE / "v166_fourth_family_sample_tax_failure.json").read_bytes(),
    )


def test_v167_verifier_has_no_v167_producer_or_core_import():
    path = (
        ROOT
        / "src/acfqp/construction_k7_fourth_family_plan_mode_set_independent_verifier_v167.py"
    )
    tree = ast.parse(path.read_text())
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.fourth_family_plan_mode_set_campaign_core_v167" not in imported
    assert (
        "acfqp.construction_k7_fourth_family_plan_mode_set_campaign_v167"
        not in imported
    )


def test_v167_frozen_producer_free_verification():
    raw = freeze_fourth_family_plan_mode_set_verification_v167(*_inputs())
    frozen = (FREEZE / "v167_fourth_family_plan_mode_set_verification.json").read_bytes()
    assert raw == frozen
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document[
        "fourth_family_factor_prior_sample_tax_transfer_independently_verified"
    ] is True
    assert document["query_policy_labels_avoided_vs_exact_path_first"] == 0
    assert document["factor_prior_labels_avoided_within_same_query_policy"] == 46
    assert document["new_family_factor_prior_labels_avoided"] == 21
    assert document["query_policy_or_plan_mode_annotation_is_safety_authority"] is False
    assert document["complete_world_model_claimed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v167_verifier_rejects_frozen_campaign_tamper_before_reconstruction():
    document = loads_canonical_json(_inputs()[0])
    document["official_execution_allowed"] = True
    campaign = canonical_json_bytes(document)
    with pytest.raises(
        ConstructionK7FourthFamilyPlanModeSetIndependentVerifierV167Error,
        match="frozen campaign changed",
    ):
        freeze_fourth_family_plan_mode_set_verification_v167(
            *_inputs(campaign)
        )
