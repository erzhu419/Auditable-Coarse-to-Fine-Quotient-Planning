from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_affine_meta_prior_v4 as v158
from acfqp import construction_k7_standard_2048_exchangeability_preregistration_v5 as v159
from acfqp import construction_k7_standard_2048_factored_operator_preregistration_v9 as v164
from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as v156
from acfqp import construction_k7_standard_2048_h3_reuse_preregistration_v8 as v162
from acfqp import construction_k7_standard_2048_meta_prior_route_preregistration_v10 as subject
from acfqp import construction_k7_standard_2048_targeted_acquisition_preregistration_v7 as v161
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def preregistration():
    return subject.freeze_standard_2048_meta_prior_route_preregistration_v10()


def test_fresh_workload_is_outcome_free(preregistration) -> None:
    document = preregistration.to_document()
    assert preregistration.preregistration_id == subject.PREREGISTRATION_ID
    assert document["planning_horizon"] == 3
    assert document["episode_count"] == 4
    assert document["decision_count_per_arm"] == 64
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False
    assert document["meta_route_implementation_present"] is False


def test_target_boards_are_d4_disjoint_from_development(preregistration) -> None:
    old = {
        canonicalize_state_v1(state_from_board_v1(board))[0].board
        for board in (
            *v156.REGISTERED_FRESH_BOARDS,
            *v158.CONFIRMATORY_INITIAL_BOARDS,
            *v159.PREREGISTERED_INITIAL_BOARDS,
            *v161.PREREGISTERED_INITIAL_BOARDS,
            *v162.PREREGISTERED_INITIAL_BOARDS,
            *v164.PREREGISTERED_INITIAL_BOARDS,
        )
    }
    new = {
        canonicalize_state_v1(state_from_board_v1(tuple(board)))[0].board
        for board in preregistration.to_document()["preregistered_initial_boards"]
    }
    assert len(new) == 4
    assert old.isdisjoint(new)


def test_sample_tax_arms_and_prior_boundary_are_frozen(preregistration) -> None:
    arms = preregistration.to_document()["matched_arms"]
    meta = arms["STRUCTURAL_META_PRIOR"]
    observed = arms["STRICT_OBSERVATION_ONLY"]
    assert meta["unique_offline_transition_observation_count"] == 192
    assert observed["unique_offline_transition_observation_count"] == 55788
    assert meta["prior_training_observation_count"] == 0
    assert meta["uniform_exchangeability_is_registered_prior"] is True
    assert meta["uniform_exchangeability_proven_by_finite_samples"] is False
    assert observed["structural_uniform_position_prior_used"] is False


def test_certificate_failure_is_the_only_ground_route(preregistration) -> None:
    document = preregistration.to_document()
    route = document["route_protocol"]
    assert route["abstract_route_only_after_certificate"] is True
    assert route["certificate_failure_route"] == "COLD_EXACT_DIRECT_GROUND_FALLBACK"
    assert route["ground_access_before_certificate_freeze"] is False
    assert route["matched_cold_direct_has_no_certificate_or_route_authority"] is True
    factored = document["shared_factored_execution_semantics"]
    assert factored["state_action_rows_serialized_or_persisted"] is False
    assert factored["exact_rational_arithmetic_required"] is True


def test_cost_axes_and_claims_are_not_conflated(preregistration) -> None:
    document = preregistration.to_document()
    axes = document["sample_tax_axes"]
    assert axes["scalar_combination_forbidden"] is True
    assert axes["offline_acquisition_observations"] == "SEPARATE_INTEGER_COUNT"
    assert axes["ground_fallback_rows_and_outcomes"] == "SEPARATE_INTEGER_COUNTS"
    assert set(document["future_content_domains"].values()) <= PHASE3E_DOMAIN_TAGS
    assert document["prior_guaranteed_correct_outside_registered_family"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_is_rejected(preregistration) -> None:
    original = preregistration.canonical_bytes
    attacked = preregistration.to_document()
    attacked["matched_arms"]["STRUCTURAL_META_PRIOR"][
        "uniform_exchangeability_proven_by_finite_samples"
    ] = True
    object.__setattr__(preregistration, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048MetaPriorRoutePreregistrationV10Error
    ):
        preregistration.__post_init__()
    object.__setattr__(preregistration, "canonical_bytes", original)
    subject.verify_standard_2048_meta_prior_route_preregistration_v10(
        preregistration
    )
