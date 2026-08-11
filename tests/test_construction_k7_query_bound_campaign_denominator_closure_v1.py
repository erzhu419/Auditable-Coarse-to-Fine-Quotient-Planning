from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_campaign_denominator_closure_independent_verifier_v1 as independent
from acfqp import construction_k7_query_bound_campaign_denominator_closure_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes, content_id


def test_public_surfaces_and_domains_are_additive() -> None:
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundCampaignDenominatorClosureV1Error",
        "QueryBoundCampaignDenominatorClosureV1",
        "QueryBoundCampaignTerminalRowV1",
        "close_query_bound_preregistered_campaign_directory_v1",
    }
    assert set(independent.__all__) == {
        "ConstructionK7QueryBoundCampaignDenominatorClosureIndependentVerifierV1Error",
        "QueryBoundCampaignDenominatorClosureVerificationV1",
        "verify_query_bound_campaign_denominator_closure_bytes_v1",
    }
    assert {
        subject.CLOSURE_DOMAIN,
        independent.VERIFICATION_PROFILE_DOMAIN,
        independent.VERIFICATION_DOMAIN,
    }.issubset(PHASE3E_DOMAIN_TAGS)


def test_closure_is_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundCampaignDenominatorClosureV1Error
    ):
        subject.QueryBoundCampaignDenominatorClosureV1(
            object(),
            "1" * 64,
            b"{}",
            "2" * 64,
            {},
            "3" * 64,
            "4" * 64,
            "5" * 64,
            "6" * 64,
            "7" * 64,
            "8" * 64,
            "9" * 64,
            ("a" * 64,),
            (),
        )


def test_independent_verifier_does_not_import_closure_or_campaign_producer() -> None:
    tree = ast.parse(Path(independent.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert (
        "acfqp.construction_k7_query_bound_campaign_denominator_closure_v1"
        not in imported
    )
    assert (
        "acfqp.construction_k7_query_bound_preregistered_campaign_runner_v1"
        not in imported
    )


def test_independent_verification_is_not_caller_mintable() -> None:
    with pytest.raises(
        independent.ConstructionK7QueryBoundCampaignDenominatorClosureIndependentVerifierV1Error
    ):
        independent.QueryBoundCampaignDenominatorClosureVerificationV1(
            object(),
            "1" * 64,
            "2" * 64,
            "3" * 64,
            1,
            "4" * 64,
            "5" * 64,
            "6" * 64,
            "7" * 64,
            ("8" * 64,),
            ("9" * 64,),
            ("a" * 64,),
        )


def test_real_complete_campaign_closes_denominator_and_rejects_claim_upgrade() -> None:
    configured = os.environ.get("ACFQP_QUERY_BOUND_PREREGISTERED_CAMPAIGN_DIRECTORY")
    if not configured:
        pytest.skip("set ACFQP_QUERY_BOUND_PREREGISTERED_CAMPAIGN_DIRECTORY")
    root = Path(configured)
    closure = subject.close_query_bound_preregistered_campaign_directory_v1(root)
    document = closure.to_document()
    assert document["logical_occurrence_count"] == 2
    assert document["closure_denominator"] == 2
    assert document["certification_coverage_denominator"] == 2
    assert document["economics_cost_denominator"] == 2
    assert document["plan_certificate_count"] == 2
    assert document["infeasibility_certificate_count"] == 0
    assert document["noncertificate_count"] == 0
    assert document["construction_certificate_coverage_status"] == "PASS"
    assert document["official_certificate_coverage_gate_status"] == "NOT_RUN"
    assert document["campaign_denominator_closure_issued"] is True
    assert document["scientific_campaign_closure_issued"] is False
    assert document["failure_path_campaign_closure_present"] is False
    assert document["campaign_orchestration_work_vector_present"] is False
    assert document["official_execution_allowed"] is False
    verification = independent.verify_query_bound_campaign_denominator_closure_bytes_v1(
        closure.canonical_bytes,
        campaign_directory=root,
    )
    assert verification.campaign_result_id == closure.campaign_result_id
    assert len(verification.occurrence_row_ids) == 2

    attacked = document.copy()
    attacked["scientific_campaign_closure_issued"] = True
    payload = dict(attacked)
    payload.pop("query_bound_campaign_denominator_closure_id")
    attacked["query_bound_campaign_denominator_closure_id"] = content_id(
        subject.CLOSURE_DOMAIN,
        payload,
    )
    with pytest.raises(
        independent.ConstructionK7QueryBoundCampaignDenominatorClosureIndependentVerifierV1Error
    ):
        independent.verify_query_bound_campaign_denominator_closure_bytes_v1(
            canonical_json_bytes(attacked),
            campaign_directory=root,
        )
