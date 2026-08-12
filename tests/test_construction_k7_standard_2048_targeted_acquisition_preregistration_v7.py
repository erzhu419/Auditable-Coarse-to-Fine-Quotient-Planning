from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_affine_meta_prior_v4 as v158
from acfqp import construction_k7_standard_2048_exchangeability_preregistration_v5 as v159
from acfqp import construction_k7_standard_2048_frontier_acquisition_preregistration_v6 as v160
from acfqp import (
    construction_k7_standard_2048_targeted_acquisition_preregistration_v7
    as subject,
)
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def preregistration():
    return subject.freeze_standard_2048_targeted_acquisition_preregistration_v7()


def test_no_observation_or_target_outcome_has_been_read(preregistration) -> None:
    document = preregistration.to_document()
    assert document["episode_count"] == 8
    assert document["decision_count"] == 128
    assert document["outcome_fields_present"] is False
    assert document["raw_observation_streams_generated"] is False
    assert document["target_execution_performed"] is False
    assert document["algorithm_implementation_present"] is False


def test_v160_is_explicitly_development_only(preregistration) -> None:
    document = preregistration.to_document()
    assert document["predecessor_v160_preregistration_id"] == (
        v160.freeze_standard_2048_frontier_acquisition_preregistration_v6().preregistration_id
    )
    assert document["v160_used_for_development_only"] is True
    assert document["v160_not_eligible_as_v161_confirmatory_evidence"] is True


def test_target_boards_are_d4_disjoint_from_all_development_fixtures(
    preregistration,
) -> None:
    old = {
        canonicalize_state_v1(state_from_board_v1(board))[0].board
        for board in (
            *v158.CONFIRMATORY_INITIAL_BOARDS,
            *v159.PREREGISTERED_INITIAL_BOARDS,
            *v160.PREREGISTERED_INITIAL_BOARDS,
        )
    }
    new = {
        canonicalize_state_v1(state_from_board_v1(tuple(board)))[0].board
        for board in preregistration.to_document()["preregistered_initial_boards"]
    }
    assert len(new) == 8
    assert old.isdisjoint(new)


def test_raw_stream_and_radius_formula_are_exact(preregistration) -> None:
    document = preregistration.to_document()
    assert document["source_seed"] == subject.SOURCE_SEED
    assert document["validation_seed"] == subject.VALIDATION_SEED
    assert document["targeted_source_levels"] == [8, 16, 64, 256, 1024, 4096, 8192]
    assert document["radius_squared_numerator"] == 8
    assert document["radius_grid_denominator"] == 65536
    assert document["position_radius_rule"].startswith("CEIL_SQRT_8_DIV")
    assert document["rank_radius_rule"].startswith("CEIL_SQRT_8_DIV")


def test_frontier_selector_is_fully_frozen(preregistration) -> None:
    arm = preregistration.to_document()["frontier_conditioned_arm"]
    assert arm["candidate_selection"] == (
        "MAXIMIZE_MINIMUM_ENDPOINT_PAIRWISE_MARGIN_THEN_ACTION_ORDER"
    )
    assert arm["blocker_selection"] == (
        "MOST_NEGATIVE_PAIRWISE_MARGIN_FOR_SELECTED_CANDIDATE"
    )
    assert arm["upgrade_rule"] == (
        "EACH_FRONTIER_CARDINALITY_TO_NEXT_TARGETED_SOURCE_LEVEL"
    )
    assert arm["unaffected_cardinalities_reused"] is True


def test_matched_controls_caps_domains_and_claims_are_frozen(preregistration) -> None:
    document = preregistration.to_document()
    assert document["maximum_unique_offline_transition_observation_count"] == 147456
    assert document["matched_global_prefix_control"][
        "failed_certificate_upgrades_all_cardinalities_to_next_global_level"
    ] is True
    assert document["matched_cold_direct_control"][
        "no_certificate_acquisition_or_route_authority"
    ] is True
    assert set(document["future_content_domains"].values()) <= PHASE3E_DOMAIN_TAGS
    assert document["external_timestamp_authority_present"] is False
    assert document["formal_confirmatory_gate_claimed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False


def test_tamper_is_rejected(preregistration) -> None:
    original = preregistration.canonical_bytes
    attacked = preregistration.to_document()
    attacked["frontier_conditioned_arm"]["unaffected_cardinalities_reused"] = False
    object.__setattr__(preregistration, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048TargetedAcquisitionPreregistrationV7Error
    ):
        preregistration.__post_init__()
    object.__setattr__(preregistration, "canonical_bytes", original)
    preregistration.__post_init__()
