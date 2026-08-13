from __future__ import annotations

from fractions import Fraction

import pytest

from acfqp import construction_k7_standard_2048_meta_prior_route_campaign_v10 as subject
from acfqp.domains.standard_2048 import state_from_board_v1
from acfqp.phase3e_ids import canonical_json_bytes, content_id


def test_full_registered_sample_tax_result_receipt_is_locked() -> None:
    assert subject.EXPECTED_CAMPAIGN_ID == (
        "6838c6ed5764d1f514247eee98f2d6d7a3992e3a29c0a4ac85ba8182b0afdcd0"
    )
    assert subject.EXPECTED_META_ABSTRACT_ROUTE_COUNT == 24
    assert subject.EXPECTED_META_FALLBACK_ROUTE_COUNT == 40
    assert subject.EXPECTED_OBSERVATION_ABSTRACT_ROUTE_COUNT == 21
    assert subject.EXPECTED_OBSERVATION_FALLBACK_ROUTE_COUNT == 43
    assert subject.EXPECTED_OFFLINE_OBSERVATION_SAVING == 55596
    assert subject.EXPECTED_FACTORED_VIRTUAL_ROW_INVOCATION_COUNT_PER_ARM == 355761
    assert (
        subject.EXPECTED_FACTORED_VIRTUAL_SUPPORT_OUTCOME_COUNT_PER_ARM
        == 7376658
    )
    assert subject.EXPECTED_META_OPERATIONAL_FALLBACK_ROW_COUNT == 289451
    assert subject.EXPECTED_OBSERVATION_OPERATIONAL_FALLBACK_ROW_COUNT == 315755


def test_meta_prior_reduces_offline_observation_tax_without_self_proving_prior() -> None:
    evidence, bounds, lower, upper = subject._observation_evidence(
        "STRUCTURAL_META_PRIOR"
    )
    assert evidence["unique_offline_transition_observation_count"] == 192
    assert evidence["uniform_exchangeability_is_registered_prior"] is True
    assert evidence["uniform_exchangeability_proven_by_finite_samples"] is False
    assert evidence["support_prefix_validation_passed"] is True
    assert (lower, upper) == (Fraction(), Fraction(41, 128))
    for empty_count, categories in bounds.items():
        assert categories == tuple(
            (Fraction(1, empty_count), Fraction(1, empty_count))
            for _ in range(empty_count)
        )


def test_observation_only_arm_replays_v161_without_structural_position_prior() -> None:
    evidence, bounds, lower, upper = subject._observation_evidence(
        "STRICT_OBSERVATION_ONLY"
    )
    assert evidence["unique_offline_transition_observation_count"] == 55788
    assert evidence["structural_uniform_position_prior_used"] is False
    assert evidence["heldout_support_and_intervals_passed"] is True
    assert 0 <= lower <= upper <= 1
    assert any(
        lower_bound != upper_bound
        for categories in bounds.values()
        for lower_bound, upper_bound in categories
    )


def test_h1_certificate_is_factored_exact_rational_and_ground_free(monkeypatch) -> None:
    evidence, bounds, rank_lower, rank_upper = subject._observation_evidence(
        "STRUCTURAL_META_PRIOR"
    )
    operator = subject._operator_document("STRUCTURAL_META_PRIOR", evidence)
    state = state_from_board_v1(subject.pre.PREREGISTERED_INITIAL_BOARDS[0])
    monkeypatch.setattr(subject.pre, "PLANNING_HORIZON", 1)
    rows = subject.v164._LazyOperatorRows(
        operator["meta_prior_factored_operator_id"],
        operator["meta_prior_factored_operator_id"],
        bounds,
        operator["meta_prior_factored_operator_id"],
    )
    bellman = subject._PersistentFactoredBellmanV10(rank_lower, rank_upper)
    certificate = subject._certificate_document(
        "STRUCTURAL_META_PRIOR",
        operator["meta_prior_factored_operator_id"],
        state,
        rows,
        bellman,
    )
    assert certificate["status"] in {
        "CERTIFIED_STRICT_ROOT_INTERVAL_DOMINANCE",
        "FAILED_STRICT_ROOT_INTERVAL_DOMINANCE",
    }
    assert certificate["serialized_state_action_row_count"] == 0
    assert certificate["persistent_state_action_row_count"] == 0
    assert certificate["ground_transition_kernel_accessed"] is False
    assert certificate["cold_direct_accessed"] is False
    assert certificate["target_observation_accessed"] is False
    assert certificate["virtual_row_invocation_count"] > 0
    for row in certificate["root_action_intervals"]:
        assert type(row["score_lower"]) is dict
        assert type(row["score_upper"]) is dict


def test_operator_is_content_addressed_and_row_free() -> None:
    evidence, _, _, _ = subject._observation_evidence("STRUCTURAL_META_PRIOR")
    operator = subject._operator_document("STRUCTURAL_META_PRIOR", evidence)
    payload = {
        key: value
        for key, value in operator.items()
        if key != "meta_prior_factored_operator_id"
    }
    assert operator["meta_prior_factored_operator_id"] == content_id(
        subject.DOMAINS["operator"], payload
    )
    assert operator["state_action_rows_serialized_or_persisted"] is False
    assert operator["successors_generated_lazily_inside_bellman_backup"] is True
    assert operator["ground_transition_kernel_accessed"] is False
    assert operator["open_ended_operator_invention_claimed"] is False


def test_content_addressed_wrapper_rejects_tamper() -> None:
    payload = {"schema": "test-only", "conditional_result": True}
    campaign_id = content_id(subject.DOMAINS["campaign"], payload)
    document = {**payload, "meta_prior_route_campaign_id": campaign_id}
    value = subject.Standard2048MetaPriorRouteCampaignV10(
        subject._ISSUER, canonical_json_bytes(document), campaign_id
    )
    attacked = value.to_document()
    attacked["conditional_result"] = False
    object.__setattr__(value, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(
        subject.ConstructionK7Standard2048MetaPriorRouteCampaignV10Error
    ):
        value.__post_init__()
