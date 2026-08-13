from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_affine_meta_prior_v4 as v158
from acfqp import construction_k7_standard_2048_exchangeability_preregistration_v5 as v159
from acfqp import construction_k7_standard_2048_factored_operator_preregistration_v9 as v164
from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as v156
from acfqp import construction_k7_standard_2048_h3_reuse_preregistration_v8 as v162
from acfqp import construction_k7_standard_2048_long_episode_preregistration_v11 as subject
from acfqp import construction_k7_standard_2048_meta_prior_route_preregistration_v10 as v166
from acfqp import construction_k7_standard_2048_targeted_acquisition_preregistration_v7 as v161
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def preregistration():
    return subject.freeze_standard_2048_long_episode_preregistration_v11()


def test_workload_is_outcome_free_and_uses_real_two_tile_starts(
    preregistration,
) -> None:
    document = preregistration.to_document()
    assert preregistration.preregistration_id == subject.PREREGISTRATION_ID
    assert document["planning_horizon"] == 3
    assert document["maximum_decisions_per_episode"] == 32
    assert document["episode_count"] == 4
    assert document["maximum_decision_count"] == 128
    assert all(
        sum(rank != 0 for rank in board) == 2
        and set(board) <= {0, 1, 2}
        for board in document["preregistered_initial_boards"]
    )
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False
    assert document["long_episode_implementation_present"] is False


def test_target_boards_are_d4_disjoint_from_all_development(
    preregistration,
) -> None:
    old = {
        canonicalize_state_v1(state_from_board_v1(board))[0].board
        for board in (
            *v156.REGISTERED_FRESH_BOARDS,
            *v158.CONFIRMATORY_INITIAL_BOARDS,
            *v159.PREREGISTERED_INITIAL_BOARDS,
            *v161.PREREGISTERED_INITIAL_BOARDS,
            *v162.PREREGISTERED_INITIAL_BOARDS,
            *v164.PREREGISTERED_INITIAL_BOARDS,
            *v166.PREREGISTERED_INITIAL_BOARDS,
        )
    }
    new = {
        canonicalize_state_v1(state_from_board_v1(tuple(board)))[0].board
        for board in preregistration.to_document()["preregistered_initial_boards"]
    }
    assert len(new) == 4
    assert old.isdisjoint(new)


def test_dynamics_identity_accept_and_no_transfer_are_distinct(
    preregistration,
) -> None:
    document = preregistration.to_document()
    accepted = document["accepted_dynamics_identity"]
    ood = document["ood_no_transfer_identity"]
    assert accepted["dynamics_identity_id"] != ood["dynamics_identity_id"]
    assert accepted["semantics"]["registered_family_member"] is True
    assert ood["semantics"]["registered_family_member"] is False
    policy = document["operator_reuse_policy"]
    assert policy["exact_accepted_dynamics_identity_required"] is True
    assert policy["identity_mismatch_action"] == "NO_TRANSFER_BEFORE_OPERATOR_ACCESS"
    assert policy["identity_match_not_sufficient_for_certificate"] is True


def test_sample_route_and_claim_boundaries_are_frozen(preregistration) -> None:
    document = preregistration.to_document()
    policy = document["operator_reuse_policy"]
    assert policy["offline_observation_count_charged_once"] == 192
    assert policy["additional_model_acquisition_observation_budget"] == 0
    assert policy["factored_state_action_rows_serialized_or_persisted"] is False
    route = document["route_protocol"]
    assert route["abstract_route_requires_strict_root_interval_dominance"] is True
    assert route["certificate_failure_route"] == "COLD_EXACT_DIRECT_GROUND_FALLBACK"
    assert route["ground_transition_access_before_certificate_freeze"] is False
    assert document["ood_generalization_claimed"] is False
    assert document["full_standard_2048_game_claimed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert set(document["future_content_domains"].values()) <= PHASE3E_DOMAIN_TAGS


def test_tamper_is_rejected(preregistration) -> None:
    original = preregistration.canonical_bytes
    attacked = preregistration.to_document()
    attacked["operator_reuse_policy"]["identity_mismatch_action"] = "TRANSFER"
    object.__setattr__(preregistration, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048LongEpisodePreregistrationV11Error
    ):
        preregistration.__post_init__()
    object.__setattr__(preregistration, "canonical_bytes", original)
    subject.verify_standard_2048_long_episode_preregistration_v11(
        preregistration
    )
