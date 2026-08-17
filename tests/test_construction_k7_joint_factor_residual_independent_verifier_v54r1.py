from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_joint_factor_residual_independent_verifier_v54r1 as verifier
from acfqp.construction_k7_joint_factor_residual_campaign_v54r1 import (
    run_joint_factor_residual_campaign_v54r1,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v54r1_independent_verifier_has_no_producer_or_campaign_core_import() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        "construction_k7_joint_factor_residual_campaign_v54r1" in name
        for name in imported
    )
    assert not any(
        "joint_factor_residual_campaign_core_v54r1" in name for name in imported
    )


def test_v54r1_frozen_verification_identity_is_pinned() -> None:
    assert verifier.EXPECTED_CAMPAIGN_ID == (
        "48f49e489e1cc5dfc98ec14c23565f66edfa93d51e15ca23f66f4668cc377223"
    )
    assert verifier.EXPECTED_CAMPAIGN_BYTE_COUNT == 129_902
    assert verifier.EXPECTED_CAMPAIGN_SHA256 == (
        "9bf6f766b95fb18a81a7b69df037f9b61dba2f342579356636cc784d6955cfd9"
    )
    assert verifier.VERIFICATION_ID == (
        "a4d71d1f6517c032e8f7f14b4fd8b2e6ab9560ca96bd4741e2d5874ad06b5acc"
    )
    assert verifier.EXPECTED_CANONICAL_BYTE_COUNT == 1_407
    assert verifier.EXPECTED_CANONICAL_SHA256 == (
        "110a27f75bc293776d3daece348bdae020128d67bea29dc235c3d81263565a70"
    )


@pytest.fixture(scope="module")
def frozen_evidence() -> tuple[bytes, bytes]:
    campaign = run_joint_factor_residual_campaign_v54r1().canonical_bytes
    verification = verifier.freeze_joint_factor_residual_verification_v54r1(campaign)
    return campaign, verification


def test_v54r1_full_producer_free_semantic_reconstruction(frozen_evidence) -> None:
    _, raw = frozen_evidence
    document = loads_canonical_json(raw)
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert document["producer_module_imported"] is False
    assert document["campaign_core_module_imported"] is False
    assert document["raw_source_observations_reconstructed"] is True
    assert document["complete_anonymous_program_reconstructed"] is True
    assert document["factorable_residual_classification_reconstructed"] is True
    assert document[
        "held_out_layouts_plans_certificates_and_local_distinctions_reconstructed"
    ] is True
    assert document["strict_ood_program_and_rejection_reconstructed"] is True
    assert document["scientific_projection_exact"] is True
    assert document["projection"]["factorable_reusable_count"] == 3
    assert document["projection"]["factorable_novel_count"] == 1
    assert document["projection"]["residual_schema_bound_count"] == 2
    assert document["projection"]["source_support_labels"] == 121
    assert document["projection"]["target_layout_support_labels"] == 556
    assert document["projection"]["local_ground_support_labels"] == 8
    assert document["projection"]["failed_certificate_count"] == 8
    assert document["projection"]["held_out_episode_count"] == 8
    assert document["projection"]["matched_execution_steps"] == 48
    assert document["projection"]["ood_reusable_count"] == 2
    assert document["projection"]["ood_transfer_admitted"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v54r1_independent_verifier_rejects_changed_bytes(frozen_evidence) -> None:
    campaign, verification = frozen_evidence
    with pytest.raises(ValueError):
        verifier.verify_joint_factor_residual_campaign_bytes_v54r1(campaign + b" ")
    with pytest.raises(ValueError):
        verifier.verify_joint_factor_residual_verification_bytes_v54r1(
            verification + b" "
        )


def test_v54r1_frozen_verification_replays_without_campaign_producer(
    frozen_evidence,
) -> None:
    _, raw = frozen_evidence
    assert (
        verifier.verify_joint_factor_residual_verification_bytes_v54r1(raw)[
            "verification_id"
        ]
        == verifier.VERIFICATION_ID
    )
