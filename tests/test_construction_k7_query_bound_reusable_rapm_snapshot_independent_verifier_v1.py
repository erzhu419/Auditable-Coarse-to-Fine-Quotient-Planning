from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_reusable_rapm_snapshot_independent_verifier_v1 as subject
from acfqp import construction_k7_query_bound_reusable_rapm_snapshot_v1 as producer
from acfqp.phase3e_ids import canonical_json_bytes, content_id
from tests.test_construction_k7_query_bound_reusable_rapm_snapshot_v1 import (
    _fresh_id,
    real_final_local_replanning,
    real_overlay_replanning,
    real_query_bound_ground_transaction,
    real_reusable_snapshot,
    real_second_ground_transaction,
    real_second_request,
)


def test_independent_verifier_import_surface_excludes_producer() -> None:
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    assert not any(
        "construction_k7_query_bound_reusable_rapm_snapshot_v1" in name
        for name in imported
    )
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundReusableRAPMIndependentVerifierV1Error",
        "LOCAL_DOMAINS",
        "verify_query_bound_reusable_rapm_bundle_bytes_v1",
        "verify_query_bound_reusable_rapm_snapshot_bytes_v1",
    }


@pytest.fixture(scope="module")
def real_verified_bundle(real_reusable_snapshot):
    _final_local, snapshot = real_reusable_snapshot
    query = producer.freeze_query_bound_reusable_rapm_query_spec_v1(
        snapshot=snapshot,
        logical_occurrence_id=_fresh_id("independent-fresh-occurrence"),
        query_ordinal=4,
    )
    snapshot_bytes = canonical_json_bytes(snapshot.to_document())
    result = producer.run_query_bound_reusable_rapm_query_v1(
        snapshot_bytes=snapshot_bytes,
        query=query,
    )
    result_bytes = canonical_json_bytes(result.to_document())
    verification = subject.verify_query_bound_reusable_rapm_bundle_bytes_v1(
        snapshot_bytes=snapshot_bytes,
        result_bytes=result_bytes,
    )
    return snapshot_bytes, result_bytes, verification


def test_real_bundle_is_independently_replayed_without_ground_access(
    real_verified_bundle,
) -> None:
    _snapshot_bytes, _result_bytes, verification = real_verified_bundle
    assert verification["snapshot_model_and_proof_typed_replay"] is True
    assert verification["fresh_query_exact_abstract_replanning"] is True
    assert verification["new_ground_access_count"] == 0
    assert verification["source_ground_transaction_replay_performed"] is False
    assert verification["source_occurrence_bundle_binding_verified"] is False
    assert verification["persistent_proof_dependency_dag_verified"] is False
    assert verification["plan_certificate_verified"] is False
    assert verification["verification_result"] == (
        "DURABLE_REUSABLE_RAPM_AND_FRESH_QUERY_VERIFIED"
    )


def test_real_snapshot_summary_preserves_explicit_source_limitations(
    real_verified_bundle,
) -> None:
    snapshot_bytes, _result_bytes, verification = real_verified_bundle
    summary = subject.verify_query_bound_reusable_rapm_snapshot_bytes_v1(
        snapshot_bytes
    )
    assert summary["reusable_rapm_snapshot_id"] == verification[
        "reusable_rapm_snapshot_id"
    ]
    assert summary["reusable_row_count"] == 18
    assert summary["changed_row_count"] == 6
    assert summary["preserved_row_count"] == 12
    assert summary["source_occurrence_bundle_binding_present"] is False
    assert summary["portable_source_ground_transaction_replay_present"] is False


def test_independent_verifier_rejects_fully_resigned_claim_flip(
    real_verified_bundle,
) -> None:
    snapshot_bytes, result_bytes, _verification = real_verified_bundle
    from acfqp.phase3e_ids import loads_canonical_json

    result = loads_canonical_json(result_bytes)
    result["new_ground_access_count"] = 1
    payload = dict(result)
    payload.pop("query")
    payload.pop("numerical_proof")
    payload.pop("query_bound_reusable_rapm_query_result_id")
    result["query_bound_reusable_rapm_query_result_id"] = content_id(
        producer.QUERY_RESULT_DOMAIN,
        payload,
    )
    with pytest.raises(
        subject.ConstructionK7QueryBoundReusableRAPMIndependentVerifierV1Error
    ):
        subject.verify_query_bound_reusable_rapm_bundle_bytes_v1(
            snapshot_bytes=snapshot_bytes,
            result_bytes=canonical_json_bytes(result),
        )


def test_independent_verifier_rejects_crossed_snapshot_identity(
    real_verified_bundle,
) -> None:
    snapshot_bytes, result_bytes, _verification = real_verified_bundle
    from acfqp.phase3e_ids import loads_canonical_json

    result = loads_canonical_json(result_bytes)
    result["reusable_rapm_snapshot_id"] = "f" * 64
    payload = dict(result)
    payload.pop("query")
    payload.pop("numerical_proof")
    payload.pop("query_bound_reusable_rapm_query_result_id")
    result["query_bound_reusable_rapm_query_result_id"] = content_id(
        producer.QUERY_RESULT_DOMAIN,
        payload,
    )
    with pytest.raises(
        subject.ConstructionK7QueryBoundReusableRAPMIndependentVerifierV1Error
    ):
        subject.verify_query_bound_reusable_rapm_bundle_bytes_v1(
            snapshot_bytes=snapshot_bytes,
            result_bytes=canonical_json_bytes(result),
        )
