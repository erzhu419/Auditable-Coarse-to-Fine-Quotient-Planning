from __future__ import annotations

import pytest

from acfqp import phase3e_ids as ids
from acfqp.factor_prior_single_switch_core_v53 import (
    build_factor_prior_single_switch_document_v53,
)


def _domains():
    return {
        "preregistration": ids.CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_PREREGISTRATION_V53_DOMAIN,
        "acquisition": ids.CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_ACQUISITION_V53_DOMAIN,
        "program": ids.CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_PROGRAM_V53_DOMAIN,
        "failed_certificate": ids.CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_FAILED_CERTIFICATE_V53_DOMAIN,
        "distinction": ids.CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_LOCAL_DISTINCTION_V53_DOMAIN,
        "episode": ids.CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_EPISODE_V53_DOMAIN,
        "sample_tax": ids.CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_SAMPLE_TAX_V53_DOMAIN,
        "campaign": ids.CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_CAMPAIGN_V53_DOMAIN,
        "verification": ids.CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_VERIFICATION_V53_DOMAIN,
    }


@pytest.fixture(scope="module")
def document():
    return build_factor_prior_single_switch_document_v53(
        {
            "domains": _domains(),
            "terminal_tokens": {"A": 9_001, "F": 9_007, "S": 9_011},
            "target_zone_count": 10,
            "target_repair_base": 8,
            "target_seeds": (539_101,),
            "maximum_synthesis_labels_per_arm": 1_024,
            "layout_confirmation_count": 2,
            "factor_prior_weight": 64,
            "posterior_threshold_numerator": 4,
            "posterior_threshold_denominator": 5,
            "posterior_confirmation_count": 1,
            "minimum_post_layout_confirmation_labels": 2,
            "maximum_relation_output_candidate": 64,
            "shared_residual_scaffold_labels": 213,
            "factor_library_labels": 370,
            "planning_validation_seed_count": 1,
            "require_incremental_reduction": True,
        },
        "d" * 64,
    )


def test_v53_domains_are_registered(document) -> None:
    assert len(set(_domains().values())) == 9
    assert all(ids.require_registered_domain_tag(value) == value for value in _domains().values())
    assert document["campaign_id"]


def test_v53_single_switch_reduces_labels_without_changing_program_or_plan(document) -> None:
    on = document["acquisitions"]["FACTOR_SIGNATURE_PRIOR_ON"][0]
    off = document["acquisitions"]["FACTOR_SIGNATURE_PRIOR_OFF"][0]
    assert on["ground_support_labels"] == 4
    assert off["ground_support_labels"] == 5
    assert on["compiled_program"]["compiled_assignments"] == off[
        "compiled_program"
    ]["compiled_assignments"]
    on_episode = document["episodes"]["FACTOR_SIGNATURE_PRIOR_ON"][0]
    off_episode = document["episodes"]["FACTOR_SIGNATURE_PRIOR_OFF"][0]
    assert on_episode["success"] is True
    assert off_episode["success"] is True
    assert on_episode["action_keys"] == off_episode["action_keys"]


def test_v53_certificate_recovery_and_claim_boundary(document) -> None:
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
    assert document["sample_tax"]["incremental_target_label_reduction"] == 1
    assert document["claim_boundary"][
        "factor_prior_single_variable_causal_ablation_observed"
    ] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
