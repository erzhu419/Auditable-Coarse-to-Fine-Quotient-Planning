from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_matched_repair_campaign_v19 as producer
from acfqp import construction_k7_standard_2048_matched_repair_independent_verifier_v19 as verifier
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CAMPAIGN_V19_DOMAIN,
    canonical_json_bytes,
    content_id,
)


@pytest.fixture(scope="module")
def campaign_and_verification():
    campaign = producer.run_standard_2048_matched_repair_campaign_v19()
    verification = verifier.verify_standard_2048_matched_repair_bytes_independently_v19(
        campaign.canonical_bytes
    )
    return campaign, verification


def _resign(document: dict) -> bytes:
    payload = {key: value for key, value in document.items() if key != "matched_repair_campaign_id"}
    document["matched_repair_campaign_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CAMPAIGN_V19_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_independent_verifier_imports_no_v19_producer_or_preregistration() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    assert "acfqp.construction_k7_standard_2048_matched_repair_campaign_v19" not in imports
    assert "acfqp.construction_k7_standard_2048_matched_repair_preregistration_v19" not in imports
    assert "acfqp.construction_k7_standard_2048_local_dynamics_kernel_v18" not in imports


def test_matched_acquisition_plans_and_targets_replay(campaign_and_verification) -> None:
    campaign, verification = campaign_and_verification
    assert verification.campaign_id == campaign.campaign_id
    document = verification.to_document()
    assert document["program_prior_four_queries_independently_replayed"] is True
    assert document["no_prior_ten_queries_independently_replayed"] is True
    assert document["strict_six_query_reduction_independently_verified"] is True
    assert document["both_12_decision_arms_independently_replanned"] is True
    assert document["all_12_shared_target_transitions_independently_replayed"] is True
    assert document["all_root_values_and_actions_match_independent_target_ground"] is True


def test_claim_boundary_remains_scoped(campaign_and_verification) -> None:
    _, verification = campaign_and_verification
    document = verification.to_document()
    assert document["broad_sample_efficiency_or_total_work_saving_verified"] is False
    assert document["full_game_or_broad_world_model_verified"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


@pytest.mark.parametrize(
    "attack",
    ("program_query", "table_query", "failure_order", "overlay", "certificate", "target", "saving", "claim"),
)
def test_fully_resigned_attacks_are_rejected(campaign_and_verification, attack: str) -> None:
    campaign, _ = campaign_and_verification
    document = copy.deepcopy(campaign.to_document())
    first = document["episodes"][0]["decisions"][0]
    if attack == "program_query":
        first["program_prior_arm"]["acquisitions"][0]["queried_empty_count"] = 1
    elif attack == "table_query":
        first["no_prior_table_arm"]["acquisitions"][0]["queried_empty_count"] = 2
    elif attack == "failure_order":
        first["program_prior_arm"]["failure"]["ground_query_count_before_failure"] = 1
    elif attack == "overlay":
        first["program_prior_arm"]["overlay"]["selected_candidate_key"] = "NO_OVERRIDE"
    elif attack == "certificate":
        original = first["program_prior_arm"]["certificate"]["selected_action"]
        first["program_prior_arm"]["certificate"]["selected_action"] = "UP" if original != "UP" else "DOWN"
    elif attack == "target":
        first["executed_next_state"]["board_ranks"][0] = 19
    elif attack == "saving":
        document["strict_ground_distinction_query_reduction"] = 999
    else:
        document["broad_world_model_synthesis_completed"] = True
    with pytest.raises(
        verifier.ConstructionK7Standard2048MatchedRepairIndependentVerifierV19Error
    ):
        verifier.verify_standard_2048_matched_repair_bytes_independently_v19(
            _resign(document)
        )


def test_verification_cannot_be_caller_minted(campaign_and_verification) -> None:
    _, verification = campaign_and_verification
    with pytest.raises(
        verifier.ConstructionK7Standard2048MatchedRepairIndependentVerifierV19Error
    ):
        verifier.Standard2048MatchedRepairIndependentVerificationV19(
            object(), verification.canonical_bytes, verification.verification_id,
            verification.campaign_id,
        )
