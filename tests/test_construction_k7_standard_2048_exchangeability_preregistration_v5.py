from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_affine_meta_prior_v4 as v158
from acfqp import construction_k7_standard_2048_exchangeability_preregistration_v5 as subject
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def preregistration():
    return subject.freeze_standard_2048_exchangeability_preregistration_v5()


def test_targets_and_algorithm_are_frozen_without_outcomes(preregistration) -> None:
    document = preregistration.to_document()
    assert document["episode_count"] == 8
    assert document["decision_count"] == 96
    assert len(document["preregistered_initial_boards"]) == 8
    assert len(document["preregistered_episode_seeds"]) == 8
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False
    assert document["algorithm_implementation_present"] is False


def test_new_boards_are_distinct_from_v158_under_d4(preregistration) -> None:
    old = {
        canonicalize_state_v1(state_from_board_v1(board))[0].board
        for board in v158.CONFIRMATORY_INITIAL_BOARDS
    }
    new = {
        canonicalize_state_v1(state_from_board_v1(tuple(board)))[0].board
        for board in preregistration.to_document()["preregistered_initial_boards"]
    }
    assert len(new) == 8
    assert old.isdisjoint(new)


def test_matched_arms_share_prefixes_caps_and_fallback(preregistration) -> None:
    document = preregistration.to_document()
    assert document["source_checkpoints_per_cardinality"] == [8, 32, 128, 512, 2048, 8192]
    assert document["validation_checkpoints_per_cardinality"] == [4, 16, 64, 256, 1024]
    assert document["nested_prefix_observations_charged_once"] is True
    assert document["maximum_offline_transition_observation_count"] == 147456
    assert document["strict_no_prior_arm"]["same_prefixes_radii_cap_and_fallback"] is True
    assert document["matched_cold_direct_control"]["no_route_or_stopping_authority"] is True


def test_future_domains_are_disjoint_and_registered(preregistration) -> None:
    document = preregistration.to_document()
    domains = set(document["future_content_domains"].values())
    assert len(domains) == 5
    assert domains <= PHASE3E_DOMAIN_TAGS


def test_claim_boundaries_are_frozen(preregistration) -> None:
    document = preregistration.to_document()
    assert document["external_timestamp_authority_present"] is False
    assert document["formal_confirmatory_gate_claimed"] is False
    assert document["full_standard_2048_game_claimed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_preregistration_tamper_is_rejected(preregistration) -> None:
    original = preregistration.canonical_bytes
    attacked = preregistration.to_document()
    attacked["target_execution_performed"] = True
    object.__setattr__(preregistration, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048ExchangeabilityPreregistrationV5Error
    ):
        preregistration.__post_init__()
    object.__setattr__(preregistration, "canonical_bytes", original)
    preregistration.__post_init__()
