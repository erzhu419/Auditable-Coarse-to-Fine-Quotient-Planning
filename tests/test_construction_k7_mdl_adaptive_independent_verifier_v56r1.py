from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_mdl_adaptive_independent_verifier_v56r1 as verifier
from acfqp.construction_k7_mdl_adaptive_campaign_v56r1 import (
    run_mdl_adaptive_campaign_v56r1,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v56r1_verifier_has_no_producer_or_campaign_core_import():
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        "construction_k7_mdl_adaptive_campaign_v56r1" in name
        for name in imported
    )
    assert not any(
        "adaptive_mdl_cross_domain_campaign_core_v56r1" in name
        or "adaptive_mdl_cross_domain_campaign_core_v56" in name
        for name in imported
    )


def test_v56r1_frozen_verification_identity_is_pinned():
    assert verifier.EXPECTED_CAMPAIGN_ID == (
        "0f5032377cd52b021133fe03a4ab4a34613a230bd3ae25efa43e02ca911521a8"
    )
    assert verifier.EXPECTED_CAMPAIGN_BYTE_COUNT == 16_064_927
    assert verifier.EXPECTED_CAMPAIGN_SHA256 == (
        "67188187a8fcda709fdcd287d653c3140a7dcf40618b4588faae355ff761f3e5"
    )
    assert verifier.VERIFICATION_ID == (
        "8aa9de632593f60ae8ac59cac3f0affa25568caf011211271913d8732e66733f"
    )
    assert verifier.EXPECTED_CANONICAL_BYTE_COUNT == 1_984
    assert verifier.EXPECTED_CANONICAL_SHA256 == (
        "ff828ce63c0a6a9acb2e5ad7ce5ca6cf83ed72ece2b2d46391d1c7d9cdcda5cd"
    )


@pytest.fixture(scope="module")
def frozen_evidence():
    campaign = run_mdl_adaptive_campaign_v56r1().canonical_bytes
    verification = verifier.freeze_mdl_adaptive_verification_v56r1(campaign)
    return campaign, verification


def test_v56r1_full_producer_free_semantic_reconstruction(frozen_evidence):
    _, raw = frozen_evidence
    document = loads_canonical_json(raw)
    projection = document["projection"]
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert document["producer_module_imported"] is False
    assert document["campaign_core_module_imported"] is False
    assert document["raw_two_domain_acquisition_sequences_reconstructed"]
    assert document["mdl_candidates_and_both_stop_disjuncts_reconstructed"]
    assert document["receding_abstract_plans_and_outcome_tapes_replayed"]
    assert document["certificate_failure_only_local_recovery_reconstructed"]
    assert document["isolated_full_frontier_validations_reconstructed"]
    assert document["sample_tax_accounting_and_ood_reconstructed"]
    assert document["scientific_projection_exact"]
    assert projection["acquisition_occurrence_count"] == 64
    assert projection["family_occurrence_counts"] == {
        "BALANCED_BATCH_REFINEMENT": 32,
        "COUPLED_EXCHANGE": 32,
    }
    assert projection["factor_prior_on_acquisition_labels"] == 6_011
    assert projection["strict_no_prior_acquisition_labels"] == 7_188
    assert projection["incremental_acquisition_label_reduction"] == 1_177
    assert projection["online_label_reduction_including_local_recovery"] == 1_165
    assert projection["lifetime_label_reduction_after_factor_library_tax"] == 795
    assert projection["diagnostic_break_even_occurrence_count"] == 23
    assert projection["factor_prior_exact_frontier_closure_count"] == 1
    assert projection["strict_no_prior_exact_frontier_closure_count"] == 10
    assert projection["planning_episode_count_all_arms"] == 24
    assert projection["failed_certificate_count"] == 12
    assert projection["local_distinction_count"] == 12
    assert projection["isolated_validation_label_count"] == 1_066
    assert projection["isolated_validation_support_mismatch_count"] == 25
    assert projection["prior_invalidated_candidate_count"] == 41
    assert projection["no_prior_invalidated_candidate_count"] == 53
    assert projection["ood_reusable_count"] == 2
    assert projection["ood_transfer_admitted"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v56r1_independent_verifier_rejects_changed_bytes(frozen_evidence):
    campaign, verification = frozen_evidence
    with pytest.raises(ValueError):
        verifier.verify_mdl_adaptive_campaign_bytes_v56r1(campaign + b" ")
    with pytest.raises(ValueError):
        verifier.verify_mdl_adaptive_verification_bytes_v56r1(
            verification + b" "
        )


def test_v56r1_frozen_verification_replays_without_producer(frozen_evidence):
    _, raw = frozen_evidence
    assert verifier.verify_mdl_adaptive_verification_bytes_v56r1(raw)[
        "verification_id"
    ] == verifier.VERIFICATION_ID
