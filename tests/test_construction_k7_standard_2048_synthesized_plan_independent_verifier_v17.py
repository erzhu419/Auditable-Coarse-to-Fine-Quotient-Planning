from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_synthesized_plan_campaign_v17 as producer
from acfqp import construction_k7_standard_2048_synthesized_plan_independent_verifier_v17 as verifier
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CAMPAIGN_V17_DOMAIN,
    canonical_json_bytes,
    content_id,
)


@pytest.fixture(scope="module")
def campaign_and_verification():
    campaign = producer.run_standard_2048_synthesized_plan_campaign_v17()
    verification = verifier.verify_standard_2048_synthesized_plan_bytes_independently_v17(
        campaign.canonical_bytes
    )
    return campaign, verification


def _resign(document: dict) -> bytes:
    payload = {
        key: value
        for key, value in document.items()
        if key != "synthesized_plan_campaign_id"
    }
    document["synthesized_plan_campaign_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CAMPAIGN_V17_DOMAIN,
        payload,
    )
    return canonical_json_bytes(document)


def test_independent_verifier_imports_no_v17_producer_or_preregistration() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    assert "acfqp.construction_k7_standard_2048_synthesized_plan_campaign_v17" not in imports
    assert "acfqp.construction_k7_standard_2048_synthesized_plan_preregistration_v17" not in imports


def test_all_model_certificates_targets_and_controls_replay(campaign_and_verification) -> None:
    campaign, verification = campaign_and_verification
    assert verification.campaign_id == campaign.campaign_id
    document = verification.to_document()
    assert document["v16_independent_world_model_identity_bound"] is True
    assert document["all_128_synthesized_h3_certificates_independently_replayed"] is True
    assert document["all_128_target_transitions_independently_replayed"] is True
    assert document["all_cold_ground_root_values_independently_replayed"] is True
    assert document["all_root_action_values_and_selected_actions_exactly_equal"] is True
    assert document["local_ground_recovery_count"] == 0


def test_claim_boundary_remains_scoped(campaign_and_verification) -> None:
    _, verification = campaign_and_verification
    document = verification.to_document()
    assert document["registered_observation_axis_reduction_independently_verified"] is True
    assert document["target_planning_or_full_game_completed"] is False
    assert document["broad_sample_efficiency_or_total_work_saving_verified"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


@pytest.mark.parametrize("attack", ("certificate", "route", "target", "sample", "claim"))
def test_fully_resigned_attacks_are_rejected_before_replay(
    campaign_and_verification, attack: str
) -> None:
    campaign, _ = campaign_and_verification
    document = copy.deepcopy(campaign.to_document())
    if attack == "certificate":
        certificate = document["episodes"][0]["decisions"][0]["certificate"]
        certificate["selected_action"] = (
            "UP" if certificate["selected_action"] != "UP" else "DOWN"
        )
    elif attack == "route":
        document["episodes"][0]["decisions"][0]["route"] = "GROUND"
    elif attack == "target":
        document["episodes"][0]["decisions"][0]["executed_next_state"]["board_ranks"][0] = 19
    elif attack == "sample":
        document["registered_offline_observation_difference"] = 999999
    else:
        document["full_standard_2048_game_completed"] = True
    with pytest.raises(
        verifier.ConstructionK7Standard2048SynthesizedPlanIndependentVerifierV17Error
    ):
        verifier.verify_standard_2048_synthesized_plan_bytes_independently_v17(
            _resign(document)
        )


def test_verification_cannot_be_caller_minted(campaign_and_verification) -> None:
    _, verification = campaign_and_verification
    with pytest.raises(
        verifier.ConstructionK7Standard2048SynthesizedPlanIndependentVerifierV17Error
    ):
        verifier.Standard2048SynthesizedPlanIndependentVerificationV17(
            object(),
            verification.canonical_bytes,
            verification.verification_id,
            verification.campaign_id,
        )
