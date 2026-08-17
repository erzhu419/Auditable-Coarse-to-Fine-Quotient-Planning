from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_factor_prior_ablation_campaign_v52 as campaign
from acfqp import construction_k7_factor_prior_ablation_preregistration_v52 as pre


@pytest.fixture(scope="module")
def frozen_campaign():
    return campaign.run_factor_prior_ablation_campaign_v52()


def test_v52_campaign_is_frozen_and_content_addressed(frozen_campaign) -> None:
    assert campaign.verify_factor_prior_ablation_campaign_v52(frozen_campaign) is frozen_campaign
    assert frozen_campaign.campaign_id == campaign.CAMPAIGN_ID
    assert len(frozen_campaign.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen_campaign.canonical_bytes).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert frozen_campaign.to_document()["preregistration_id"] == pre.PREREGISTRATION_ID


def test_v52_campaign_has_successful_matched_cross_domain_arms(frozen_campaign) -> None:
    document = frozen_campaign.to_document()
    assert len(document["factor_prior_episodes"]) == 16
    assert len(document["no_prior_episodes"]) == 16
    assert all(row["success"] for row in document["factor_prior_episodes"])
    assert all(row["success"] for row in document["no_prior_episodes"])
    assert [row["execution_steps"] for row in document["factor_prior_episodes"]] == [
        row["execution_steps"] for row in document["no_prior_episodes"]
    ]
    assert all(
        row["factor_library_accessed"] is False
        and row["compiled_prior_accessed"] is False
        for row in document["no_prior_acquisitions"]
    )


def test_v52_campaign_confirms_amortized_sample_reduction(frozen_campaign) -> None:
    document = frozen_campaign.to_document()
    tax = document["sample_tax"]
    assert tax["historical_factor_prior_labels"] == 583
    assert tax["factor_prior_target_labels"] == 50
    assert tax["factor_prior_cumulative_labels"] == 633
    assert tax["no_prior_cumulative_labels"] == 11_387
    assert tax["cumulative_label_reduction"] == 10_754
    assert tax["registered_break_even_occurrence_count"] == 1
    assert len(document["failed_certificates"]) == len(document["local_distinctions"]) == 8


def test_v52_campaign_keeps_accounting_and_official_gates_separate(
    frozen_campaign,
) -> None:
    document = frozen_campaign.to_document()
    assert document["accounting"]["all_axes_separate"] is True
    assert document["claim_boundary"]["individual_factor_only_causal_effect_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
