from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_adaptive_joint_independent_verifier_v55 as verifier
from acfqp.construction_k7_adaptive_joint_campaign_v55 import (
    run_adaptive_joint_campaign_v55,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v55_independent_verifier_has_no_producer_or_campaign_core_import():
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        "construction_k7_adaptive_joint_campaign_v55" in name
        for name in imported
    )
    assert not any(
        "adaptive_joint_factor_residual_campaign_core_v55" in name
        for name in imported
    )


def test_v55_frozen_verification_identity_is_pinned():
    assert verifier.EXPECTED_CAMPAIGN_ID == (
        "ea85860f499ac631a7f3e6b306974be2a2d7c9de88cde3cf492380ebd59ec589"
    )
    assert verifier.EXPECTED_CAMPAIGN_BYTE_COUNT == 2_027_913
    assert verifier.EXPECTED_CAMPAIGN_SHA256 == (
        "38363f222d1b4047e4ce6f2fd5e6c4aea595709b473e9aed44d90fd54245128a"
    )
    assert verifier.VERIFICATION_ID == (
        "ec6fe8ee01a663030ffdd146613d1f4231000f27bae0773f47c15b6d398fd1f6"
    )
    assert verifier.EXPECTED_CANONICAL_BYTE_COUNT == 1_470
    assert verifier.EXPECTED_CANONICAL_SHA256 == (
        "4f09b2f96c970465a531e80e14827ae228ccd45460a297c893f43542229905ed"
    )


@pytest.fixture(scope="module")
def frozen_evidence():
    campaign = run_adaptive_joint_campaign_v55().canonical_bytes
    verification = verifier.freeze_adaptive_joint_verification_v55(campaign)
    return campaign, verification


def test_v55_full_producer_free_semantic_reconstruction(frozen_evidence):
    _, raw = frozen_evidence
    document = loads_canonical_json(raw)
    projection = document["projection"]
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert document["producer_module_imported"] is False
    assert document["campaign_core_module_imported"] is False
    assert document["raw_acquisition_sequences_reconstructed"] is True
    assert document["joint_candidates_and_stop_points_reconstructed"] is True
    assert document["matched_plans_and_outcome_tapes_replayed"] is True
    assert document["isolated_full_frontier_validations_reconstructed"] is True
    assert document["sample_tax_and_ood_reconstructed"] is True
    assert document["scientific_projection_exact"] is True
    assert projection["acquisition_occurrence_count"] == 128
    assert projection["factor_prior_on_acquisition_labels"] == 10_240
    assert projection["strict_no_prior_acquisition_labels"] == 10_760
    assert projection["incremental_acquisition_label_reduction"] == 520
    assert projection["online_label_reduction_including_local_recovery"] == 518
    assert projection["lifetime_label_reduction_after_factor_library_tax"] == 148
    assert projection["diagnostic_break_even_occurrence_count"] == 92
    assert projection["planning_episode_count_all_arms"] == 24
    assert projection["failed_certificate_count"] == 30
    assert projection["isolated_validation_label_count"] == 1_063
    assert projection["isolated_validation_support_mismatch_count"] == 58
    assert projection["prior_candidate_reset_count"] == 0
    assert projection["no_prior_candidate_reset_count"] == 3
    assert projection["ood_reusable_count"] == 2
    assert projection["ood_transfer_admitted"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v55_independent_verifier_rejects_changed_bytes(frozen_evidence):
    campaign, verification = frozen_evidence
    with pytest.raises(ValueError):
        verifier.verify_adaptive_joint_campaign_bytes_v55(campaign + b" ")
    with pytest.raises(ValueError):
        verifier.verify_adaptive_joint_verification_bytes_v55(
            verification + b" "
        )


def test_v55_frozen_verification_replays_without_scientific_producer(
    frozen_evidence,
):
    _, raw = frozen_evidence
    assert verifier.verify_adaptive_joint_verification_bytes_v55(raw)[
        "verification_id"
    ] == verifier.VERIFICATION_ID
