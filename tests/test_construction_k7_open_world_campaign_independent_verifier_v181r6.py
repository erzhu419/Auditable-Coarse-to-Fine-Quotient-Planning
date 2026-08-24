from __future__ import annotations

import ast
from pathlib import Path

from acfqp import construction_k7_open_world_campaign_independent_verifier_v181r6 as verifier


def _acquisition(*, arm: str, credit: int, archive_references: int) -> dict:
    return {
        "compiled_model": {
            "archive_reference_count": archive_references,
            "archive_mdl_discount_used": False,
            "archive_reference_revalidated_on_current_rows": True,
        },
        "block_history": [
            {
                "stable_confirmation_count": 1,
                "revalidated_prior_confirmation_credit": credit,
                "effective_confirmation_count": 1 + credit,
            }
        ],
        "stable_confirmation_count": 1 if credit else 2,
        "revalidated_prior_confirmation_credit": credit,
        "effective_confirmation_count": 2,
        "stopped": True,
        "same_synthesizer_and_stop_rule": True,
        "same_confidence_formula_both_arms": True,
        "archive_mdl_discount_used": False,
        "prior_credit_revalidated_on_all_current_rows": True,
    }


def test_safe_prior_credit_is_reconstructed_without_producer_import() -> None:
    assert verifier._verify_acquisition(
        _acquisition(
            arm="REUSED_SUBPROGRAM_PRIOR",
            credit=1,
            archive_references=2,
        ),
        "REUSED_SUBPROGRAM_PRIOR",
    )
    assert verifier._verify_acquisition(
        _acquisition(
            arm="EMPTY_ARCHIVE_NO_PRIOR",
            credit=0,
            archive_references=0,
        ),
        "EMPTY_ARCHIVE_NO_PRIOR",
    )


def test_prior_credit_or_mdl_claim_mutation_is_rejected() -> None:
    row = _acquisition(
        arm="REUSED_SUBPROGRAM_PRIOR",
        credit=1,
        archive_references=2,
    )
    row["compiled_model"]["archive_mdl_discount_used"] = True
    assert verifier._verify_acquisition(row, "REUSED_SUBPROGRAM_PRIOR") is False


def test_verifier_does_not_import_campaign_producer() -> None:
    path = Path(verifier.__file__)
    tree = ast.parse(path.read_text())
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_open_world_campaign_v181r6" not in imported


def test_outcome_identity_is_not_filled_before_campaign_completion() -> None:
    assert verifier.EXPECTED_CAMPAIGN_ID == "0" * 64
    assert verifier.EXPECTED_VERIFICATION_ID == "0" * 64
