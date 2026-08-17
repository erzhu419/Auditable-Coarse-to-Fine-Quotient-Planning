from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_mdl_adaptive_campaign_v56r1 as campaign_v56r1


@pytest.fixture(scope="module")
def campaign():
    value = campaign_v56r1.run_mdl_adaptive_campaign_v56r1()
    assert campaign_v56r1.verify_mdl_adaptive_campaign_v56r1(value) is value
    return value


def test_v56r1_campaign_is_frozen_and_content_addressed(campaign):
    assert campaign.campaign_id == campaign_v56r1.CAMPAIGN_ID
    assert len(campaign.canonical_bytes) == (
        campaign_v56r1.EXPECTED_CANONICAL_BYTE_COUNT
    )
    assert hashlib.sha256(campaign.canonical_bytes).hexdigest() == (
        campaign_v56r1.EXPECTED_CANONICAL_SHA256
    )


def test_v56r1_registered_two_domain_sample_tax(campaign):
    sample = campaign.to_document()["sample_tax"]
    assert sample["factor_prior_on_acquisition_labels"] == 6_011
    assert sample["strict_no_prior_acquisition_labels"] == 7_188
    assert sample["incremental_acquisition_label_reduction"] == 1_177
    assert sample["online_label_reduction_including_local_recovery"] == 1_165
    assert sample["lifetime_label_reduction_after_factor_library_tax"] == 795
    assert sample["diagnostic_break_even_occurrence_count"] == 23
    assert sample["family_projections"]["BALANCED_BATCH_REFINEMENT"][
        "incremental_label_reduction"
    ] == 509
    assert sample["family_projections"]["COUPLED_EXCHANGE"][
        "incremental_label_reduction"
    ] == 668


def test_v56r1_registered_frontier_plans_and_local_recovery(campaign):
    document = campaign.to_document()
    strict_coupled = [
        row
        for row in document["acquisitions"]["STRICT_NO_PRIOR"]
        if row["family"] == "COUPLED_EXCHANGE"
    ]
    assert sum(
        row["stopped_by_exact_reachable_frontier_closure"]
        for row in strict_coupled
    ) == 10
    plans = [
        [(row["family"], row["seed"], row["action_keys"]) for row in document[
            "episodes"
        ][arm]]
        for arm in (
            "ANONYMOUS_FACTOR_PRIOR_ON",
            "STRICT_NO_PRIOR",
            "STRICT_EXACT_CONTEXT",
        )
    ]
    assert plans[0] == plans[1] == plans[2]
    assert len(document["failed_certificates"]) == 12
    assert len(document["local_distinctions"]) == 12
    assert all(
        row["query_after_failed_certificate"]
        for row in document["local_distinctions"]
    )


def test_v56r1_registered_validation_ood_and_claim_locks(campaign):
    document = campaign.to_document()
    assert len(document["isolated_full_frontier_validations"]) == 8
    assert all(
        row["validation_rows_consumed_for_acquisition"] is False
        and row["validation_rows_consumed_for_binding"] is False
        and row["validation_rows_consumed_for_planning"] is False
        for row in document["isolated_full_frontier_validations"]
    )
    assert document["ood_rejection"]["prior_transfer_attempted"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
