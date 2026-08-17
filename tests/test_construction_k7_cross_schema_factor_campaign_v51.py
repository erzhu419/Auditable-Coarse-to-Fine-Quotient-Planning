from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_cross_schema_factor_campaign_v51 as campaign
from acfqp import construction_k7_cross_schema_factor_preregistration_v51 as pre


@pytest.fixture(scope="module")
def frozen_campaign():
    return campaign.run_cross_schema_factor_campaign_v51()


def test_v51_campaign_is_frozen_and_content_addressed(frozen_campaign) -> None:
    assert campaign.verify_cross_schema_factor_campaign_v51(frozen_campaign) is frozen_campaign
    assert frozen_campaign.campaign_id == campaign.CAMPAIGN_ID
    assert len(frozen_campaign.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen_campaign.canonical_bytes).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert frozen_campaign.to_document()["preregistration_id"] == pre.PREREGISTRATION_ID


def test_v51_campaign_observes_cross_schema_factor_composition(frozen_campaign) -> None:
    document = frozen_campaign.to_document()
    library = document["inherited_factor_library"]
    model = document["higher_order_partial_stochastic_world_model"]["factor_composed_model"]
    assert library["source_schema_pairs"] == [[7, 5], [9, 6]]
    assert len(library["cross_schema_subprograms"]) == 3
    assert model["reused_factor_count"] == 5
    assert model["all_reused_factors_originated_in_multiple_source_schema_pairs"] is True
    assert all(row["success"] for row in document["structural_episodes"])
    assert all(row["success"] for row in document["strict_episodes"])


def test_v51_campaign_is_certificate_first_and_reduces_cumulative_tax(
    frozen_campaign,
) -> None:
    document = frozen_campaign.to_document()
    assert len(document["failed_certificates"]) == 8
    assert len(document["local_distinctions"]) == 8
    assert all(
        row["ground_query_performed_before_failure"] is False
        for row in document["failed_certificates"]
    )
    assert all(
        row["query_after_failed_certificate"] is True
        for row in document["local_distinctions"]
    )
    tax = document["sample_tax"]
    assert tax["cumulative_structural_labels"] == 660
    assert tax["cumulative_strict_labels"] == 814
    assert tax["cumulative_label_reduction"] == 154
    assert document["ood_rejection"]["prior_transfer_attempted"] is False
    assert document["ood_rejection"]["ood_outcome_execution_performed"] is False


def test_v51_campaign_keeps_all_work_axes_and_official_gates_separate(
    frozen_campaign,
) -> None:
    document = frozen_campaign.to_document()
    assert document["accounting"] == {
        "historical_factor_library_source_labels": 370,
        "new_domain_source_labels": 213,
        "target_layout_labels": 20,
        "local_ground_labels": 8,
        "structural_execution_steps": 38,
        "strict_execution_steps": 38,
        "factor_boundary_compute_events": 26,
        "fallback_atomic_synthesis_compute_events": 3_634_386,
        "structural_planning_compute_events": 902,
        "strict_planning_compute_events": 702,
        "certificate_compute_events": 8,
        "all_axes_separate": True,
    }
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
