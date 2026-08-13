from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp import construction_k7_standard_2048_factored_operator_campaign_v9 as subject
from acfqp import construction_k7_standard_2048_h3_reuse_campaign_v8 as v163
from acfqp.domains.standard_2048 import state_from_board_v1
from acfqp.phase3e_ids import canonical_json_bytes, content_id


def _fixture():
    source_id = "a" * 64
    validation_id = "b" * 64
    proposal = v163._support_proposal(source_id, validation_id)
    interval, bounds, rank_lower, rank_upper = v163._interval_binding(
        source_id, validation_id, proposal["support_proposal_id"]
    )
    operator = subject._operator_document(
        source_id, validation_id, proposal, interval
    )
    return proposal, interval, bounds, rank_lower, rank_upper, operator


def test_full_registered_factored_result_receipt_is_locked() -> None:
    assert subject.EXPECTED_CAMPAIGN_ID == (
        "48c920ec560529c433b81cb24c784f52b67e6ce2acf9ad746edda8b5635e40d8"
    )
    assert subject.EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT == 105434
    assert (
        subject.EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_EVALUATION_COUNT
        == 2359184
    )
    assert subject.EXPECTED_CLOSED_SUBPROOF_CACHE_HIT_COUNT == 2192777
    assert subject.EXPECTED_EXPLICIT_MATERIALIZED_ROW_COUNT == 178268
    assert subject.EXPECTED_EXPLICIT_MATERIALIZED_SUPPORT_OUTCOME_COUNT == 4031972
    assert subject.EXPECTED_EXACT_LABEL_IDENTICAL_DECISION_COUNT == 21
    assert subject.EXPECTED_EXACT_VALUE_EQUIVALENT_DECISION_COUNT == 31
    assert subject.EXPECTED_EXACT_QUALITY_MISMATCH_COUNT == 1


def test_lazy_operator_row_is_semantically_exact_without_row_artifact() -> None:
    proposal, interval, bounds, _, _, operator = _fixture()
    state = state_from_board_v1(subject.pre.PREREGISTERED_INITIAL_BOARDS[0])
    key = v163._missing_frontier({}, state)[0]
    rows = subject._LazyOperatorRows(
        interval["partial_dynamics_interval_id"],
        proposal["support_proposal_id"],
        bounds,
        operator["factored_spawn_operator_id"],
    )
    actual = rows.get(key)
    explicit = v163._materialize_row(
        key,
        interval["partial_dynamics_interval_id"],
        proposal["support_proposal_id"],
        bounds,
    )
    assert actual.outcomes == explicit.outcomes
    assert actual.support_outcome_count == explicit.support_outcome_count
    assert actual.unknown_support_mass_upper == explicit.unknown_support_mass_upper == 0
    assert actual.row_id == operator["factored_spawn_operator_id"]
    assert not hasattr(actual, "to_document")
    assert rows.invocation_count == 1
    assert rows.support_outcome_evaluation_count == explicit.support_outcome_count


def test_factored_h1_matches_explicit_exact_rational_control(monkeypatch) -> None:
    proposal, interval, bounds, rank_lower, rank_upper, operator = _fixture()
    state = state_from_board_v1(subject.pre.PREREGISTERED_INITIAL_BOARDS[0])
    monkeypatch.setattr(subject.pre, "PLANNING_HORIZON", 1)
    monkeypatch.setattr(v163.pre, "PLANNING_HORIZON", 1)
    rows = subject._LazyOperatorRows(
        interval["partial_dynamics_interval_id"],
        proposal["support_proposal_id"],
        bounds,
        operator["factored_spawn_operator_id"],
    )
    cache = v163._PersistentRobustSubproofs(rank_lower, rank_upper)
    factored = subject._factored_plan(
        rows, cache, state, operator["factored_spawn_operator_id"]
    )
    explicit = subject._explicit_control(
        state,
        interval["partial_dynamics_interval_id"],
        proposal["support_proposal_id"],
        bounds,
        rank_lower,
        rank_upper,
    )
    assert factored["selected_action"] == explicit["selected_action"]
    assert factored["robust_score_lower"] == explicit["robust_score_lower"]
    assert factored["robust_score_upper"] == explicit["robust_score_upper"]
    assert (
        factored["robust_loss_probability_upper"]
        == explicit["robust_loss_probability_upper"]
    )
    assert factored["serialized_state_action_row_count"] == 0
    assert factored["persistent_state_action_row_count"] == 0
    assert explicit["materialized_state_action_row_count"] > 0


def test_operator_identity_and_claim_boundary_are_content_addressed() -> None:
    proposal, interval, _, _, _, operator = _fixture()
    payload = {
        key: value
        for key, value in operator.items()
        if key != "factored_spawn_operator_id"
    }
    assert operator["factored_spawn_operator_id"] == content_id(
        subject.DOMAINS["operator"], payload
    )
    assert operator["state_action_rows_serialized_or_persisted"] is False
    assert operator["successors_generated_lazily_inside_bellman_backup"] is True
    assert operator["support_proposal_id"] == proposal["support_proposal_id"]
    assert (
        operator["partial_dynamics_interval_id"]
        == interval["partial_dynamics_interval_id"]
    )
    assert operator["open_ended_operator_invention_claimed"] is False


def test_exact_rationals_are_not_replaced_by_float() -> None:
    assert subject._fraction({"numerator": 1, "denominator": 3}) == Fraction(1, 3)
    with pytest.raises(
        subject.ConstructionK7Standard2048FactoredOperatorCampaignV9Error
    ):
        subject._fraction(1 / 3)


def test_content_addressed_wrapper_rejects_tamper() -> None:
    payload = {"schema": "test-only", "registered_positive_result": True}
    campaign_id = content_id(subject.DOMAINS["campaign"], payload)
    document = {**payload, "factored_operator_campaign_id": campaign_id}
    value = subject.Standard2048FactoredOperatorCampaignV9(
        subject._ISSUER, canonical_json_bytes(document), campaign_id
    )
    attacked = value.to_document()
    attacked["registered_positive_result"] = False
    object.__setattr__(value, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048FactoredOperatorCampaignV9Error
    ):
        value.__post_init__()
