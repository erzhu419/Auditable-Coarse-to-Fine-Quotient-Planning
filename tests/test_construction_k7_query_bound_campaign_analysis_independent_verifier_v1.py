from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_campaign_analysis_v1 as producer
from acfqp import construction_k7_query_bound_campaign_analysis_independent_verifier_v1 as subject
from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as bundle_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


def test_public_surface_is_one_bytes_verifier() -> None:
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundCampaignAnalysisIndependentVerifierV1Error",
        "QueryBoundCampaignAnalysisVerificationV1",
        "verify_query_bound_campaign_analysis_bytes_v1",
    }


def test_verifier_source_does_not_import_campaign_producer() -> None:
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert "acfqp.construction_k7_query_bound_campaign_analysis_v1" not in imported


def test_verification_result_is_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundCampaignAnalysisIndependentVerifierV1Error
    ):
        subject.QueryBoundCampaignAnalysisVerificationV1(
            object(),
            "1" * 64,
            "2" * 64,
            "3" * 64,
            ("4" * 64, "5" * 64),
            ("6" * 64, "7" * 64),
            ("8" * 64,),
            ("9" * 64, "a" * 64),
            "b" * 64,
            1,
        )


@pytest.fixture(scope="module")
def real_analysis_bytes():
    supplied = os.environ.get("ACFQP_QUERY_BOUND_CAMPAIGN_BUNDLES")
    if not supplied:
        pytest.skip("set ACFQP_QUERY_BOUND_CAMPAIGN_BUNDLES to two bundle directories")
    directories = tuple(Path(value) for value in supplied.split(os.pathsep) if value)
    verifications = tuple(
        bundle_v1.verify_query_bound_complete_bundle_directory_v1(directory)
        for directory in directories
    )
    spec = producer.freeze_query_bound_campaign_analysis_spec_v1(
        ordered_occurrence_ids=tuple(row.occurrence_id for row in verifications),
        permutation_cap=producer.MAX_EXPLICIT_PERMUTATIONS,
    )
    analysis = producer.analyze_query_bound_campaign_bundles_v1(
        spec,
        bundle_directories=directories,
    )
    return analysis.canonical_bytes, directories


def test_real_analysis_bytes_replay_without_campaign_producer(
    real_analysis_bytes,
) -> None:
    raw, directories = real_analysis_bytes
    verified = subject.verify_query_bound_campaign_analysis_bytes_v1(
        raw,
        bundle_directories=directories,
    )
    document = verified.to_document()
    assert document["all_occurrence_bundles_independently_replayed"] is True
    assert document["all_vector_prefixes_recomputed"] is True
    assert document["producer_module_imported"] is False
    assert document["campaign_preregistration_present"] is False
    assert document["scientific_campaign_closure_issued"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False


def test_independent_replay_rejects_resigned_prefix_value(
    real_analysis_bytes,
) -> None:
    raw, directories = real_analysis_bytes
    document = loads_canonical_json(raw)
    prefix = document["vector_prefix_totals"][0]
    prefix["values"][0]["value"] += 1
    prefix_payload = dict(prefix)
    prefix_payload.pop("campaign_vector_prefix_id")
    prefix["campaign_vector_prefix_id"] = content_id(
        producer.PREFIX_DOMAIN,
        prefix_payload,
    )
    analysis_payload = dict(document)
    analysis_payload.pop("query_bound_campaign_analysis_id")
    document["query_bound_campaign_analysis_id"] = content_id(
        CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_V1_DOMAIN,
        analysis_payload,
    )
    with pytest.raises(
        subject.ConstructionK7QueryBoundCampaignAnalysisIndependentVerifierV1Error
    ):
        subject.verify_query_bound_campaign_analysis_bytes_v1(
            canonical_json_bytes(document),
            bundle_directories=directories,
        )
