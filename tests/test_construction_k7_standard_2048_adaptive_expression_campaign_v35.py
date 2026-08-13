from __future__ import annotations

import copy
import os

import pytest

from acfqp import construction_k7_standard_2048_adaptive_expression_campaign_v35 as campaign


FULL = os.environ.get("ACFQP_RUN_ADAPTIVE_2048_V35") == "1"


def test_v34_preexecution_gate_fails_before_any_target_query(monkeypatch: pytest.MonkeyPatch) -> None:
    if campaign.V34_ACCOUNTED_CAMPAIGN_ID != "0" * 64:
        pytest.skip("V34 predecessor is now frozen")

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("target query occurred before V34 verification")

    monkeypatch.setattr(campaign.target, "query_rank_two_probability_v35", forbidden)
    with pytest.raises(
        campaign.ConstructionK7Standard2048AdaptiveExpressionCampaignV35Error,
        match="V34 accounting predecessor",
    ):
        campaign.run_standard_2048_adaptive_expression_campaign_v35()


@pytest.mark.skipif(not FULL, reason="requires registered adaptive acquisition")
def test_first_failed_frontier_acquires_only_local_distinctions() -> None:
    acquired = campaign._acquire_model()  # noqa: SLF001
    assert acquired.failure["frontier_context_count"] > 0
    assert len(acquired.acquisitions) <= 12
    assert len(acquired.acquisitions) < acquired.control[
        "distinct_context_probability_label_count"
    ]
    assert all(
        row["context_belongs_to_previously_frozen_failed_frontier"] is True
        for row in acquired.acquisitions
    )
    assert acquired.proposal["remaining_candidate_count"] == 1
    assert acquired.proof["exact_program_equivalence_proved"] is True
    assert acquired.overlay["serialized_state_action_probability_table_present"] is False


@pytest.mark.skipif(not FULL, reason="requires registered 512-decision-cap campaign")
def test_adaptive_campaign_replays_and_keeps_claims_bounded() -> None:
    value = campaign.run_standard_2048_adaptive_expression_campaign_v35()
    assert campaign.verify_standard_2048_adaptive_expression_campaign_v35(value) is value
    document = value.to_document()
    assert document["certificate_failure_count"] == 1
    assert document["ground_distinction_query_count"] < document[
        "first_frontier_no_prior_label_count"
    ]
    assert document[
        "sample_tax_reduced_on_registered_first_failure_label_axis"
    ] is True
    assert document["all_plans_after_repair_use_proved_reusable_expression_model"] is True
    assert document["all_checkpoint_root_values_and_actions_exactly_equal"] is True
    assert document["counter_records_issued"] is False
    assert document["formal_native_accounting_successor_required"] is True
    assert document["full_standard_2048_game_claimed"] is False
    assert document["automatic_reusable_world_model_goal_completed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


@pytest.mark.skipif(not FULL, reason="requires registered 512-decision-cap campaign")
def test_campaign_identity_tamper_is_rejected() -> None:
    value = campaign.run_standard_2048_adaptive_expression_campaign_v35()
    tampered = copy.copy(value)
    object.__setattr__(tampered, "campaign_id", "f" * 64)
    with pytest.raises(
        campaign.ConstructionK7Standard2048AdaptiveExpressionCampaignV35Error
    ):
        campaign.verify_standard_2048_adaptive_expression_campaign_v35(tampered)
