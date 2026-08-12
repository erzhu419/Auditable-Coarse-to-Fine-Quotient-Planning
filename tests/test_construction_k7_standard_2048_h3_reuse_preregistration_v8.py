from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_affine_meta_prior_v4 as v158
from acfqp import construction_k7_standard_2048_exchangeability_preregistration_v5 as v159
from acfqp import construction_k7_standard_2048_frontier_acquisition_preregistration_v6 as v160
from acfqp import construction_k7_standard_2048_h3_reuse_preregistration_v8 as subject
from acfqp import construction_k7_standard_2048_targeted_acquisition_preregistration_v7 as v161
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def preregistration():
    return subject.freeze_standard_2048_h3_reuse_preregistration_v8()


def test_h3_workload_is_outcome_free(preregistration) -> None:
    document = preregistration.to_document()
    assert document["planning_horizon"] == 3
    assert document["episode_count"] == 4
    assert document["decision_count"] == 32
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False
    assert document["algorithm_implementation_present"] is False


def test_boards_are_d4_disjoint_from_all_development_fixtures(preregistration) -> None:
    old = {
        canonicalize_state_v1(state_from_board_v1(board))[0].board
        for board in (
            *v158.CONFIRMATORY_INITIAL_BOARDS,
            *v159.PREREGISTERED_INITIAL_BOARDS,
            *v160.PREREGISTERED_INITIAL_BOARDS,
            *v161.PREREGISTERED_INITIAL_BOARDS,
        )
    }
    new = {
        canonicalize_state_v1(state_from_board_v1(tuple(board)))[0].board
        for board in preregistration.to_document()["preregistered_initial_boards"]
    }
    assert len(new) == 4
    assert old.isdisjoint(new)


def test_targeted_archive_reuse_and_once_only_charge_are_frozen(preregistration) -> None:
    document = preregistration.to_document()
    assert document["predecessor_v161_campaign_id"] == subject.PREDECESSOR_V161_CAMPAIGN_ID
    assert document["reuse_targeted_raw_streams_and_final_count_vector"] is True
    assert document["reuse_v161_source_and_validation_archive_identities"] is True
    assert document["offline_observations_charged_once_at_shared_campaign_level"] is True
    assert document["unknown_support_mass_upper_within_registered_support_family"] == 0
    assert document[
        "full_empty_cell_support_is_conditional_on_registered_candidate_family"
    ] is True
    assert document["open_ended_support_completeness_claimed"] is False
    assert document["v161_final_source_counts_by_cardinality"][8:] == [
        256, 8192, 8192, 8192, 8192, 8192, 8192, 8
    ]


def test_certificate_failure_recovery_protocol_is_frozen(preregistration) -> None:
    protocol = preregistration.to_document()["persistent_partial_world_model_protocol"]
    assert protocol["audit_before_ground_support_materialization"] is True
    assert protocol["failed_proof_frontier_only_materialization"] is True
    assert protocol["maximum_recovery_transactions_per_decision"] == 4
    assert protocol["rows_reused_across_decisions_and_episodes"] is True
    assert protocol["certificate_or_recovery_failure_route"] == "COLD_GROUND_FALLBACK"


def test_claims_and_domains_are_closed(preregistration) -> None:
    document = preregistration.to_document()
    assert set(document["future_content_domains"].values()) <= PHASE3E_DOMAIN_TAGS
    assert document["formal_confirmatory_gate_claimed"] is False
    assert document["full_standard_2048_game_claimed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_is_rejected(preregistration) -> None:
    original = preregistration.canonical_bytes
    attacked = preregistration.to_document()
    attacked["persistent_partial_world_model_protocol"][
        "audit_before_ground_support_materialization"
    ] = False
    object.__setattr__(preregistration, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(subject.ConstructionK7Standard2048H3ReusePreregistrationV8Error):
        preregistration.__post_init__()
    object.__setattr__(preregistration, "canonical_bytes", original)
    preregistration.__post_init__()
