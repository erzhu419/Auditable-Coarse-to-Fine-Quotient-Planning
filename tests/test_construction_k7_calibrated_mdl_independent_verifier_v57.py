from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_calibrated_mdl_independent_verifier_v57 as verifier
from acfqp.construction_k7_calibrated_mdl_campaign_v57 import (
    run_calibrated_mdl_campaign_v57,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v57_verifier_has_no_v57_producer_or_campaign_core_import():
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        "construction_k7_calibrated_mdl_campaign_v57" in name
        for name in imported
    )
    assert not any(
        "calibrated_mdl_three_domain_campaign_core_v57" in name
        for name in imported
    )


def test_v57_frozen_verification_identity_is_pinned():
    assert verifier.EXPECTED_CAMPAIGN_ID == (
        "744e764a35cb7ba4955852fa62c30978b7aac35d0761b7054cb64298be1fd92b"
    )
    assert verifier.EXPECTED_CAMPAIGN_BYTE_COUNT == 25_640_858
    assert verifier.EXPECTED_CAMPAIGN_SHA256 == (
        "3fc9f09eac87e1ea2180a1b6a5523694aed5c1dc41438a7484e6a9dc9f925588"
    )
    assert verifier.VERIFICATION_ID == (
        "f38218a0a527dd4411bf1d105162f563eae1800d68bab6d9b821cb0e693d1469"
    )
    assert verifier.EXPECTED_CANONICAL_BYTE_COUNT == 2_100
    assert verifier.EXPECTED_CANONICAL_SHA256 == (
        "fb79bcfc0e73a44254b9d9db32af0cc8d86293db84871026b59f80737ecbc86d"
    )


@pytest.fixture(scope="module")
def frozen_evidence():
    campaign = run_calibrated_mdl_campaign_v57().canonical_bytes
    verification = verifier.freeze_calibrated_mdl_verification_v57(campaign)
    return campaign, verification


def test_v57_full_producer_free_semantic_reconstruction(frozen_evidence):
    _, raw = frozen_evidence
    document = loads_canonical_json(raw)
    projection = document["projection"]
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert document["producer_module_imported"] is False
    assert document["campaign_core_module_imported"] is False
    assert document["prior_producer_free_ground_and_planning_primitives_reused"]
    assert document["raw_three_domain_acquisition_sequences_reconstructed"]
    assert document["calibrated_eprocess_and_mdl_stops_reconstructed"]
    assert document["reachable_frontier_exhaustion_stop_consumed"] is False
    assert document["receding_abstract_plans_and_outcome_tapes_replayed"]
    assert document["certificate_failure_only_local_recovery_reconstructed"]
    assert document["isolated_full_frontier_validations_reconstructed"]
    assert document["sample_tax_accounting_and_ood_reconstructed"]
    assert document["scientific_projection_exact"]
    assert projection["acquisition_occurrence_count"] == 96
    assert projection["family_occurrence_counts"] == {
        "BALANCED_BATCH_REFINEMENT": 32,
        "COUPLED_EXCHANGE": 32,
        "MAINTENANCE_CASCADE": 32,
    }
    assert projection["factor_prior_on_acquisition_labels"] == 7_630
    assert projection["strict_no_prior_acquisition_labels"] == 9_192
    assert projection["incremental_acquisition_label_reduction"] == 1_562
    assert projection["online_label_reduction_including_local_recovery"] == 1_557
    assert projection["lifetime_label_reduction_after_factor_library_tax"] == 1_187
    assert projection["diagnostic_break_even_occurrence_count"] == 44
    assert projection["planning_episode_count_all_arms"] == 36
    assert projection["failed_certificate_count"] == 11
    assert projection["local_distinction_count"] == 11
    assert projection["isolated_validation_label_count"] == 1_726
    assert projection["isolated_validation_support_mismatch_count"] == 45
    assert projection["prior_invalidated_candidate_count"] == 43
    assert projection["no_prior_invalidated_candidate_count"] == 59
    assert projection["ood_reusable_count"] == 2
    assert projection["ood_transfer_admitted"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v57_independent_verifier_rejects_changed_bytes(frozen_evidence):
    campaign, verification = frozen_evidence
    with pytest.raises(ValueError):
        verifier.verify_calibrated_mdl_campaign_bytes_v57(campaign + b" ")
    with pytest.raises(ValueError):
        verifier.verify_calibrated_mdl_verification_bytes_v57(
            verification + b" "
        )


def test_v57_frozen_verification_replays_without_producer(frozen_evidence):
    _, raw = frozen_evidence
    assert verifier.verify_calibrated_mdl_verification_bytes_v57(raw)[
        "verification_id"
    ] == verifier.VERIFICATION_ID
