from __future__ import annotations

import pytest

from acfqp import construction_k7_standard_2048_long_episode_campaign_v11 as subject
from acfqp.domains.standard_2048 import state_from_board_v1
from acfqp.phase3e_ids import canonical_json_bytes, content_id


def test_full_registered_long_episode_result_receipt_is_locked() -> None:
    assert subject.EXPECTED_CAMPAIGN_ID == (
        "158dfab7d25c70d46aabc98620d4bccd55ff5f2a39c354aa6ca918346e191fdd"
    )
    assert subject.EXPECTED_DECISION_COUNT == 128
    assert subject.EXPECTED_ABSTRACT_ROUTE_COUNT == 49
    assert subject.EXPECTED_FALLBACK_ROUTE_COUNT == 79
    assert subject.EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT == 719879
    assert subject.EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_COUNT == 14840614
    assert subject.EXPECTED_CLOSED_SUBPROOF_CACHE_HIT_COUNT == 12855414
    assert subject.EXPECTED_OPERATIONAL_FALLBACK_ROW_COUNT == 607858
    assert subject.EXPECTED_OPERATIONAL_FALLBACK_OUTCOME_COUNT == 13268726
    assert subject.EXPECTED_EVALUATION_DIRECT_ROW_COUNT == 349125
    assert subject.EXPECTED_EVALUATION_DIRECT_OUTCOME_COUNT == 7055406
    assert subject.EXPECTED_MAXIMUM_FINAL_BOARD_TILE_RANK == 6


def test_ood_identity_fails_before_operator_target_or_ground_access() -> None:
    no_transfer = subject._ood_no_transfer_document()
    assert no_transfer["status"] == "NO_TRANSFER_DYNAMICS_IDENTITY_MISMATCH"
    assert no_transfer["identity_match"] is False
    assert no_transfer["operator_binding_created"] is False
    assert no_transfer["operator_accessed"] is False
    assert no_transfer["target_execution_performed"] is False
    assert no_transfer["target_observation_accessed"] is False
    assert no_transfer["ground_transition_accessed"] is False
    assert no_transfer["route_decision_created"] is False
    payload = {
        key: value for key, value in no_transfer.items() if key != "long_no_transfer_id"
    }
    assert no_transfer["long_no_transfer_id"] == content_id(
        subject.DOMAINS["no_transfer"], payload
    )


def test_in_family_binding_reuses_192_observations_and_zero_rows() -> None:
    binding, bounds, lower, upper = subject._operator_binding_document()
    assert binding["binding_status"] == "EXACT_DYNAMICS_IDENTITY_BOUND"
    assert binding["accepted_dynamics_identity"]["semantics"][
        "registered_family_member"
    ] is True
    assert binding["offline_observation_count"] == 192
    assert binding["additional_model_acquisition_observation_count"] == 0
    assert binding["state_action_rows_serialized_or_persisted"] is False
    assert binding["identity_match_is_not_a_route_certificate"] is True
    assert len(bounds) == 16
    assert 0 <= lower <= upper <= 1


def test_h1_certificate_remains_ground_free(monkeypatch) -> None:
    binding, bounds, lower, upper = subject._operator_binding_document()
    state = state_from_board_v1(subject.pre.PREREGISTERED_INITIAL_BOARDS[0])
    monkeypatch.setattr(subject.pre, "PLANNING_HORIZON", 1)
    monkeypatch.setattr(subject.v167.pre, "PLANNING_HORIZON", 1)
    rows = subject.v164._LazyOperatorRows(
        binding["long_operator_binding_id"],
        binding["long_operator_binding_id"],
        bounds,
        binding["long_operator_binding_id"],
    )
    bellman = subject.v167._PersistentFactoredBellmanV10(lower, upper)
    certificate = subject._certificate_document(
        state, binding["long_operator_binding_id"], rows, bellman
    )
    assert certificate["status"] in {
        "CERTIFIED_STRICT_ROOT_INTERVAL_DOMINANCE",
        "FAILED_STRICT_ROOT_INTERVAL_DOMINANCE",
    }
    assert certificate["ground_transition_accessed"] is False
    assert certificate["cold_direct_accessed"] is False
    assert certificate["target_observation_accessed"] is False
    assert certificate["serialized_state_action_row_count"] == 0
    assert certificate["persistent_state_action_row_count"] == 0


def test_content_addressed_wrapper_rejects_tamper() -> None:
    payload = {"schema": "test-only", "long_result": True}
    campaign_id = content_id(subject.DOMAINS["campaign"], payload)
    document = {**payload, "long_episode_campaign_id": campaign_id}
    value = subject.Standard2048LongEpisodeCampaignV11(
        subject._ISSUER, canonical_json_bytes(document), campaign_id
    )
    attacked = value.to_document()
    attacked["long_result"] = False
    object.__setattr__(value, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048LongEpisodeCampaignV11Error
    ):
        value.__post_init__()
