from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp import construction_k7_standard_2048_fresh_board_support_world_model_v2 as base
from acfqp import construction_k7_standard_2048_h3_reuse_campaign_v8 as subject
from acfqp.domains.standard_2048 import state_from_board_v1
from acfqp.phase3e_ids import canonical_json_bytes, content_id


def _fixture():
    source_id = "a" * 64
    validation_id = "b" * 64
    proposal = subject._support_proposal(source_id, validation_id)
    interval, bounds, rank_lower, rank_upper = subject._interval_binding(
        source_id, validation_id, proposal["support_proposal_id"]
    )
    return source_id, validation_id, proposal, interval, bounds, rank_lower, rank_upper


def test_full_registered_negative_result_receipt_is_locked() -> None:
    assert subject.EXPECTED_CAMPAIGN_ID == (
        "e4cd9db57964ace8ba639a41fb76acda8c7e994a02de1e3e0bfa642fe5300b4e"
    )
    assert subject.EXPECTED_PARTIAL_ROW_COUNT == 63135
    assert subject.EXPECTED_SUPPORT_OUTCOME_COUNT == 1447682
    assert subject.EXPECTED_EXACT_EQUIVALENT_DECISION_COUNT == 31
    assert subject.EXPECTED_MISMATCH_COUNT == 1


def test_fast_frontier_is_exactly_the_v2_frontier() -> None:
    _, _, proposal, interval, bounds, _, _ = _fixture()
    state = state_from_board_v1(subject.pre.PREREGISTERED_INITIAL_BOARDS[0])
    rows = {}
    assert subject._missing_frontier(rows, state) == base._missing_frontier(
        rows, state, subject.pre.PLANNING_HORIZON
    )
    for key in subject._missing_frontier(rows, state):
        rows[key] = subject._materialize_row(
            key,
            interval["partial_dynamics_interval_id"],
            proposal["support_proposal_id"],
            bounds,
        )
    assert subject._missing_frontier(rows, state) == base._missing_frontier(
        rows, state, subject.pre.PLANNING_HORIZON
    )


def test_materialization_sets_registered_zero_without_global_monkeypatch() -> None:
    _, _, proposal, interval, bounds, _, _ = _fixture()
    state = state_from_board_v1(subject.pre.PREREGISTERED_INITIAL_BOARDS[0])
    key = subject._missing_frontier({}, state)[0]
    original = base.UNKNOWN_SUPPORT_MASS_UPPER
    row = subject._materialize_row(
        key,
        interval["partial_dynamics_interval_id"],
        proposal["support_proposal_id"],
        bounds,
    )
    assert row.unknown_support_mass_upper == 0
    assert base.UNKNOWN_SUPPORT_MASS_UPPER == original == Fraction(1, 128)


def test_incremental_model_document_is_byte_exact_v2() -> None:
    source_id, validation_id, proposal, interval, bounds, _, _ = _fixture()
    state = state_from_board_v1(subject.pre.PREREGISTERED_INITIAL_BOARDS[0])
    rows = {}
    key = subject._missing_frontier(rows, state)[0]
    rows[key] = subject._materialize_row(
        key,
        interval["partial_dynamics_interval_id"],
        proposal["support_proposal_id"],
        bounds,
    )
    cache = subject._IncrementalModelDocuments(
        source_id,
        validation_id,
        proposal["support_proposal_id"],
        interval["partial_dynamics_interval_id"],
    )
    expected = base._model_document(
        rows,
        source_id,
        validation_id,
        proposal["support_proposal_id"],
        interval["partial_dynamics_interval_id"],
    )
    assert cache.document(rows) == expected
    assert cache.document(rows) is cache.document(rows)


def test_persistent_closed_subproof_is_exactly_v2(monkeypatch) -> None:
    _, _, proposal, interval, bounds, rank_lower, rank_upper = _fixture()
    state = state_from_board_v1(subject.pre.PREREGISTERED_INITIAL_BOARDS[0])
    monkeypatch.setattr(subject.pre, "PLANNING_HORIZON", 1)
    rows = {}
    for key in subject._missing_frontier(rows, state):
        rows[key] = subject._materialize_row(
            key,
            interval["partial_dynamics_interval_id"],
            proposal["support_proposal_id"],
            bounds,
        )
    cache = subject._PersistentRobustSubproofs(rank_lower, rank_upper)
    actual = cache.solve(rows, state)
    expected = base._solve_robust(rows, state, 1, rank_lower, rank_upper)
    assert actual == expected
    assert cache.solve(rows, state) == expected
    assert cache.cache_hits > 0


def test_content_addressed_wrapper_rejects_tamper() -> None:
    payload = {"schema": "test-only", "negative_result": True}
    campaign_id = content_id(subject.DOMAINS["campaign"], payload)
    document = {**payload, "h3_reuse_campaign_id": campaign_id}
    value = subject.Standard2048H3ReuseCampaignV8(
        subject._ISSUER, canonical_json_bytes(document), campaign_id
    )
    attacked = value.to_document()
    attacked["negative_result"] = False
    object.__setattr__(value, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(subject.ConstructionK7Standard2048H3ReuseCampaignV8Error):
        value.__post_init__()
