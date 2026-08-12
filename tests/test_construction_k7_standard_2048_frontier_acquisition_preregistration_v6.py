from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_affine_meta_prior_v4 as v158
from acfqp import construction_k7_standard_2048_exchangeability_preregistration_v5 as v159
from acfqp import (
    construction_k7_standard_2048_frontier_acquisition_preregistration_v6
    as subject,
)
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def preregistration():
    return subject.freeze_standard_2048_frontier_acquisition_preregistration_v6()


def test_target_and_algorithm_are_outcome_free(preregistration) -> None:
    document = preregistration.to_document()
    assert document["episode_count"] == 8
    assert document["decision_count"] == 128
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False
    assert document["algorithm_implementation_present"] is False


def test_boards_are_d4_disjoint_from_v158_and_v159(preregistration) -> None:
    old = {
        canonicalize_state_v1(state_from_board_v1(board))[0].board
        for board in (*v158.CONFIRMATORY_INITIAL_BOARDS, *v159.PREREGISTERED_INITIAL_BOARDS)
    }
    new = {
        canonicalize_state_v1(state_from_board_v1(tuple(board)))[0].board
        for board in preregistration.to_document()["preregistered_initial_boards"]
    }
    assert len(new) == 8
    assert old.isdisjoint(new)


def test_frontier_policy_and_matched_control_are_frozen(preregistration) -> None:
    document = preregistration.to_document()
    arm = document["frontier_conditioned_arm"]
    assert arm["initial_global_checkpoint_per_cardinality"] == 8
    assert arm["unaffected_rows_reused_without_resampling"] is True
    assert arm["all_acquired_rows_charged_once_by_unique_raw_record_identity"] is True
    assert arm["hard_cap_route"] == "COLD_GROUND_FALLBACK"
    assert document["matched_global_prefix_control"]["policy"] == (
        "V159_GLOBAL_PER_CARDINALITY_ESCALATION"
    )
    assert document["matched_cold_direct_control"]["no_acquisition_or_route_authority"] is True


def test_budget_and_negative_result_policy_are_frozen(preregistration) -> None:
    document = preregistration.to_document()
    assert document["maximum_unique_offline_transition_observation_count"] == 147456
    assert document["if_sample_reduction_fails"] == (
        "REPORT_PREREGISTERED_NEGATIVE_RESULT_AND_PRESERVE_FALLBACK"
    )
    assert set(document["future_content_domains"].values()) <= PHASE3E_DOMAIN_TAGS


def test_claims_stay_closed(preregistration) -> None:
    document = preregistration.to_document()
    assert document["external_timestamp_authority_present"] is False
    assert document["formal_confirmatory_gate_claimed"] is False
    assert document["full_standard_2048_game_claimed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_is_rejected(preregistration) -> None:
    original = preregistration.canonical_bytes
    attacked = preregistration.to_document()
    attacked["algorithm_implementation_present"] = True
    object.__setattr__(preregistration, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048FrontierAcquisitionPreregistrationV6Error
    ):
        preregistration.__post_init__()
    object.__setattr__(preregistration, "canonical_bytes", original)
    preregistration.__post_init__()
