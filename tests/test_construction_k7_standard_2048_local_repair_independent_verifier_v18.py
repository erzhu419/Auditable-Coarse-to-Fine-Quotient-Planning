from __future__ import annotations

import ast
import copy
from fractions import Fraction
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_local_repair_campaign_v18 as producer
from acfqp import construction_k7_standard_2048_local_repair_independent_verifier_v18 as verifier
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CAMPAIGN_V18_DOMAIN,
    canonical_json_bytes,
    content_id,
)
from acfqp.domains.standard_2048 import Swipe2048Action, state_from_board_v1


@pytest.fixture(scope="module")
def campaign_and_verification():
    campaign = producer.run_standard_2048_local_repair_campaign_v18()
    verification = verifier.verify_standard_2048_local_repair_bytes_independently_v18(
        campaign.canonical_bytes
    )
    return campaign, verification


def _resign(document: dict) -> bytes:
    payload = {key: value for key, value in document.items() if key != "local_repair_campaign_id"}
    document["local_repair_campaign_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CAMPAIGN_V18_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_independent_verifier_imports_no_v18_producer_or_preregistration() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    assert "acfqp.construction_k7_standard_2048_local_repair_campaign_v18" not in imports
    assert "acfqp.construction_k7_standard_2048_local_repair_preregistration_v18" not in imports
    assert "acfqp.construction_k7_standard_2048_local_dynamics_kernel_v18" not in imports


def test_failure_repair_plans_and_targets_replay(campaign_and_verification) -> None:
    campaign, verification = campaign_and_verification
    assert verification.campaign_id == campaign.campaign_id
    document = verification.to_document()
    assert document["base_failure_before_ground_independently_verified"] is True
    assert document["two_adaptive_ground_distinctions_independently_replayed"] is True
    assert document["unique_reusable_program_overlay_independently_recovered"] is True
    assert document["all_12_repaired_abstract_h3_plans_independently_replayed"] is True
    assert document["all_12_target_transitions_independently_replayed"] is True
    assert document["all_root_values_and_actions_match_cold_target_ground"] is True


def test_public_independent_target_primitives_replay_registered_root() -> None:
    state = state_from_board_v1(
        (1, 2, 4, 4, 3, 4, 4, 0, 3, 2, 3, 2, 6, 3, 1, 1)
    )
    frontier = verifier.independently_replay_structural_frontier_v18(state)
    assert frontier == tuple(range(1, 9))
    assert verifier.independently_replay_rank_two_probability_v18(4) == Fraction(1, 5)
    assert verifier.independently_replay_rank_two_probability_v18(5) == Fraction(1, 10)
    rows = verifier.apply_independently_replayed_target_outcomes_v18(
        state, Swipe2048Action.LEFT
    )
    assert sum(row.probability for row in rows) == 1
    roots = verifier.independently_replay_target_root_values_v18(state)
    assert tuple(row[0] for row in roots) == ("UP", "DOWN", "LEFT", "RIGHT")


def test_sample_and_claim_boundaries_remain_scoped(campaign_and_verification) -> None:
    _, verification = campaign_and_verification
    document = verification.to_document()
    assert document["registered_program_prior_query_difference_verified"] == 3
    assert document["broad_sample_efficiency_or_total_work_saving_verified"] is False
    assert document["full_game_or_broad_world_model_verified"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


@pytest.mark.parametrize("attack", ("order", "query", "overlay", "certificate", "target", "claim"))
def test_fully_resigned_attacks_are_rejected(
    campaign_and_verification, attack: str
) -> None:
    campaign, _ = campaign_and_verification
    document = copy.deepcopy(campaign.to_document())
    first = document["episodes"][0]["decisions"][0]
    if attack == "order":
        first["base_failure"]["ground_probability_query_count_before_failure"] = 1
    elif attack == "query":
        first["local_acquisitions"][0]["queried_empty_count"] = 4
    elif attack == "overlay":
        document["persistent_local_repair_overlay"]["selected_override_threshold"] = 5
    elif attack == "certificate":
        first["certificate"]["selected_action"] = "DOWN"
    elif attack == "target":
        first["executed_next_state"]["board_ranks"][0] = 19
    else:
        document["broad_world_model_synthesis_completed"] = True
    with pytest.raises(
        verifier.ConstructionK7Standard2048LocalRepairIndependentVerifierV18Error
    ):
        verifier.verify_standard_2048_local_repair_bytes_independently_v18(
            _resign(document)
        )


def test_verification_cannot_be_caller_minted(campaign_and_verification) -> None:
    _, verification = campaign_and_verification
    with pytest.raises(
        verifier.ConstructionK7Standard2048LocalRepairIndependentVerifierV18Error
    ):
        verifier.Standard2048LocalRepairIndependentVerificationV18(
            object(),
            verification.canonical_bytes,
            verification.verification_id,
            verification.campaign_id,
        )
