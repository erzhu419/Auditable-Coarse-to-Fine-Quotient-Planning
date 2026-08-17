from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_layout_factorization_campaign_v50r1 as campaign
from acfqp import construction_k7_layout_factorization_preregistration_v50r1 as pre


@pytest.fixture(scope="module")
def frozen_campaign():
    return campaign.run_layout_factorization_campaign_v50r1()


def test_v50r1_campaign_is_frozen_and_content_addressed(frozen_campaign) -> None:
    assert campaign.verify_layout_factorization_campaign_v50r1(frozen_campaign) is frozen_campaign
    assert frozen_campaign.campaign_id == campaign.CAMPAIGN_ID
    assert len(frozen_campaign.canonical_bytes) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen_campaign.canonical_bytes).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert frozen_campaign.to_document()["preregistration_id"] == pre.PREREGISTRATION_ID


def test_v50r1_campaign_observes_safe_two_domain_world_models(frozen_campaign) -> None:
    document = frozen_campaign.to_document()
    assert set(document["world_models"]) == {
        "STOCHASTIC_MODULAR_ROUTING",
        "STOCHASTIC_INVENTORY_ASSEMBLY",
    }
    assert all(
        model["terminal_next_status_column_candidates_excluded"] is True
        and model["terminal_self_next_dependency_count"] == 0
        and model["compiled_program"]["terminal_self_next_dependency_count"] == 0
        for model in document["world_models"].values()
    )
    assert all(
        row["success"]
        for row in document["structural_episodes"] + document["strict_episodes"]
    )


def test_v50r1_campaign_is_certificate_first_and_reduces_sample_tax(
    frozen_campaign,
) -> None:
    document = frozen_campaign.to_document()
    assert len(document["failed_certificates"]) == len(document["local_distinctions"]) == 4
    assert all(
        row["ground_query_performed_before_failure"] is False
        for row in document["failed_certificates"]
    )
    assert all(
        row["query_after_failed_certificate"] is True
        for row in document["local_distinctions"]
    )
    tax = document["sample_tax"]
    assert tax["structural_total_support_labels"] == 419
    assert tax["strict_target_support_labels"] == 579
    assert tax["diagnostic_break_even_occurrences"] == 12
    assert document["ood_rejection"]["prior_transfer_attempted"] is False
    assert document["ood_rejection"]["ood_outcome_execution_performed"] is False


def test_v50r1_campaign_keeps_official_and_economics_gates_locked(
    frozen_campaign,
) -> None:
    document = frozen_campaign.to_document()
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
