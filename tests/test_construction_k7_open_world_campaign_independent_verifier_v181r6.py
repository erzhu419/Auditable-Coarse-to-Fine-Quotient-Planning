from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_open_world_campaign_independent_verifier_v181r6 as verifier
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp" / "exact-freeze"


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


def _frozen_inputs() -> tuple[bytes, tuple[bytes, ...]]:
    campaign = (FREEZE / "v181r6_open_world_campaign.json").read_bytes()
    checkpoints = tuple(
        path.read_bytes()
        for path in sorted(
            (FREEZE / "v181r6_open_world_progress").glob("checkpoint-*.json")
        )
    )
    return campaign, checkpoints


def test_frozen_campaign_replays_without_producer_import() -> None:
    campaign, checkpoints = _frozen_inputs()
    result = verifier.freeze_open_world_campaign_verification_v181r6(
        campaign,
        checkpoints,
    )
    assert result.verification_id == verifier.EXPECTED_VERIFICATION_ID
    assert len(campaign) == verifier.EXPECTED_CAMPAIGN_BYTE_COUNT
    assert hashlib.sha256(campaign).hexdigest() == verifier.EXPECTED_CAMPAIGN_SHA256
    assert len(result.canonical_bytes) == verifier.EXPECTED_VERIFICATION_BYTE_COUNT
    assert (
        hashlib.sha256(result.canonical_bytes).hexdigest()
        == verifier.EXPECTED_VERIFICATION_SHA256
    )
    document = result.to_document()
    assert document["prior_labels_avoided"] == 32
    assert document["bounded_sample_tax_reduction_independently_verified"] is True
    assert (
        document["weight_agnostic_total_work_dominance_independently_verified"]
        is True
    )


def test_retained_verification_bytes_are_an_exact_replay() -> None:
    campaign, checkpoints = _frozen_inputs()
    replay = verifier.freeze_open_world_campaign_verification_v181r6(
        campaign,
        checkpoints,
    )
    retained = (
        FREEZE / "v181r6_open_world_campaign_verification.json"
    ).read_bytes()
    assert retained == replay.canonical_bytes
    assert canonical_json_bytes(replay.to_document()) == retained
