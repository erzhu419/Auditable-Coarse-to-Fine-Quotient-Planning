from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_affine_meta_prior_v4 as v158
from acfqp import construction_k7_standard_2048_exchangeability_preregistration_v5 as v159
from acfqp import construction_k7_standard_2048_factored_operator_preregistration_v9 as subject
from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as v156
from acfqp import construction_k7_standard_2048_frontier_acquisition_preregistration_v6 as v160
from acfqp import construction_k7_standard_2048_h3_reuse_preregistration_v8 as v162
from acfqp import construction_k7_standard_2048_targeted_acquisition_preregistration_v7 as v161
from acfqp.domains.standard_2048 import canonicalize_state_v1, state_from_board_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


@pytest.fixture(scope="module")
def preregistration():
    return subject.freeze_standard_2048_factored_operator_preregistration_v9()


def test_fresh_workload_is_outcome_free(preregistration) -> None:
    document = preregistration.to_document()
    assert preregistration.preregistration_id == subject.PREREGISTRATION_ID
    assert document["planning_horizon"] == 3
    assert document["episode_count"] == 4
    assert document["decision_count"] == 32
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False
    assert document["factored_operator_implementation_present"] is False


def test_target_boards_are_d4_disjoint_from_all_development_boards(
    preregistration,
) -> None:
    old = {
        canonicalize_state_v1(state_from_board_v1(board))[0].board
        for board in (
            *v156.REGISTERED_FRESH_BOARDS,
            *v158.CONFIRMATORY_INITIAL_BOARDS,
            *v159.PREREGISTERED_INITIAL_BOARDS,
            *v160.PREREGISTERED_INITIAL_BOARDS,
            *v161.PREREGISTERED_INITIAL_BOARDS,
            *v162.PREREGISTERED_INITIAL_BOARDS,
        )
    }
    new = {
        canonicalize_state_v1(state_from_board_v1(tuple(board)))[0].board
        for board in preregistration.to_document()["preregistered_initial_boards"]
    }
    assert len(new) == 4
    assert old.isdisjoint(new)


def test_factored_and_explicit_semantics_are_frozen(preregistration) -> None:
    document = preregistration.to_document()
    operator = document["factored_operator_semantics"]
    control = document["matched_explicit_row_control"]
    assert operator["state_action_rows_serialized_or_persisted"] is False
    assert operator["successors_generated_lazily_inside_bellman_backup"] is True
    assert operator["unknown_support_mass_within_registered_family"] == 0
    assert control["same_support_proposal_and_intervals"] is True
    assert control["same_exact_rational_robust_bellman_recurrence"] is True
    assert control["rows_materialized_only_in_evaluation_control"] is True


def test_sample_tax_axes_are_not_conflated(preregistration) -> None:
    document = preregistration.to_document()
    assert document["reused_offline_observation_count"] == 55788
    assert document["additional_offline_observation_budget"] == 0
    boundary = document["sample_tax_claim_boundary"]
    assert boundary["offline_acquisition_tax_measured"] is True
    assert boundary["serialized_local_distinction_tax_measured"] is True
    assert boundary["bellman_compute_tax_measured_separately"] is True
    assert boundary["total_operational_work_saving_claimed"] is False


def test_claims_and_domains_remain_closed(preregistration) -> None:
    document = preregistration.to_document()
    assert set(document["future_content_domains"].values()) <= PHASE3E_DOMAIN_TAGS
    assert len(document["future_content_domains"]) == len(
        set(document["future_content_domains"].values())
    )
    assert document["formal_confirmatory_gate_claimed"] is False
    assert document["full_standard_2048_game_claimed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_is_rejected(preregistration) -> None:
    original = preregistration.canonical_bytes
    attacked = preregistration.to_document()
    attacked["factored_operator_semantics"][
        "state_action_rows_serialized_or_persisted"
    ] = True
    object.__setattr__(preregistration, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048FactoredOperatorPreregistrationV9Error
    ):
        preregistration.__post_init__()
    object.__setattr__(preregistration, "canonical_bytes", original)
    preregistration.__post_init__()
