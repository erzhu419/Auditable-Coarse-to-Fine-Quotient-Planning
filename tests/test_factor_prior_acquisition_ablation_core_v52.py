from __future__ import annotations

import pytest

from acfqp import phase3e_ids as ids
from acfqp.factor_prior_acquisition_ablation_core_v52 import (
    build_factor_prior_acquisition_ablation_document_v52,
)


def _domains():
    return {
        "preregistration": ids.CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_PREREGISTRATION_V52_DOMAIN,
        "acquisition": ids.CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_ACQUISITION_V52_DOMAIN,
        "failed_certificate": ids.CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_FAILED_CERTIFICATE_V52_DOMAIN,
        "distinction": ids.CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_LOCAL_DISTINCTION_V52_DOMAIN,
        "episode": ids.CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_EPISODE_V52_DOMAIN,
        "sample_tax": ids.CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_SAMPLE_TAX_V52_DOMAIN,
        "campaign": ids.CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_CAMPAIGN_V52_DOMAIN,
        "verification": ids.CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_VERIFICATION_V52_DOMAIN,
    }


def _config():
    return {
        "domains": _domains(),
        "terminal_tokens": {"A": 9_001, "F": 9_007, "S": 9_011},
        "target_zone_count": 10,
        "target_repair_base": 7,
        "target_seeds": tuple(range(529_101, 529_117)),
        "maximum_prior_layout_labels": 32,
        "maximum_relation_output_candidate": 64,
        "maximum_no_prior_labels_per_occurrence": 2_048,
        "minimum_reused_factor_count": 5,
        "historical_factor_prior_labels": 583,
        "maximum_registered_break_even_occurrences": 16,
    }


@pytest.fixture(scope="module")
def document():
    return build_factor_prior_acquisition_ablation_document_v52(
        _config(), "d" * 64
    )


def test_v52_domains_are_registered_and_disjoint() -> None:
    values = set(_domains().values())
    assert len(values) == 8
    assert all(ids.require_registered_domain_tag(value) == value for value in values)


def test_v52_factor_prior_and_no_prior_arms_are_matched(document) -> None:
    assert len(document["factor_prior_episodes"]) == 16
    assert len(document["no_prior_episodes"]) == 16
    assert all(row["success"] for row in document["factor_prior_episodes"])
    assert all(row["success"] for row in document["no_prior_episodes"])
    assert [row["seed"] for row in document["factor_prior_episodes"]] == [
        row["seed"] for row in document["no_prior_episodes"]
    ]
    assert all(
        row["factor_library_accessed"] is False
        and row["compiled_prior_accessed"] is False
        for row in document["no_prior_acquisitions"]
    )


def test_v52_certificate_first_recovery_and_sample_tax(document) -> None:
    assert document["failed_certificates"]
    assert len(document["failed_certificates"]) == len(document["local_distinctions"])
    assert all(
        row["ground_query_performed_before_failure"] is False
        for row in document["failed_certificates"]
    )
    assert all(
        row["query_after_failed_certificate"] is True
        for row in document["local_distinctions"]
    )
    tax = document["sample_tax"]
    assert tax["historical_factor_prior_labels"] == 583
    assert tax["cumulative_label_reduction"] > 0
    assert tax["registered_break_even_occurrence_count"] <= 16


def test_v52_accounting_and_claims_remain_bounded(document) -> None:
    assert document["accounting"]["all_axes_separate"] is True
    assert document["claim_boundary"][
        "individual_factor_only_causal_effect_claimed"
    ] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
