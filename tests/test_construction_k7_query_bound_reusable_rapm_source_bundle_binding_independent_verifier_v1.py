from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_reusable_rapm_source_bundle_binding_independent_verifier_v1 as subject
from acfqp import construction_k7_query_bound_reusable_rapm_source_bundle_binding_v1 as producer
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json
from tests.test_construction_k7_query_bound_reusable_rapm_source_bundle_binding_v1 import (
    real_source_bundle_binding,
)


def test_verifier_import_surface_excludes_binding_producer() -> None:
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any(
        "reusable_rapm_source_bundle_binding_v1" in name
        for name in imported
    )
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundReusableRAPMSourceBundleBindingIndependentVerifierV1Error",
        "LOCAL_DOMAINS",
        "verify_query_bound_reusable_rapm_source_bundle_binding_bytes_v1",
    }


@pytest.fixture(scope="module")
def real_independent_source_binding(real_source_bundle_binding):
    preregistration, bundle, snapshot, binding = real_source_bundle_binding
    binding_bytes = canonical_json_bytes(binding.to_document())
    verification = (
        subject.verify_query_bound_reusable_rapm_source_bundle_binding_bytes_v1(
            preregistration_bytes=preregistration,
            bundle_directory=bundle,
            snapshot_bytes=snapshot,
            binding_bytes=binding_bytes,
        )
    )
    return preregistration, bundle, snapshot, binding_bytes, verification


def test_real_binding_is_independently_replayed(
    real_independent_source_binding,
) -> None:
    _preregistration, _bundle, _snapshot, _binding, verification = (
        real_independent_source_binding
    )
    assert verification["preregistration_bundle_snapshot_join_replayed"] is True
    assert verification[
        "source_occurrence_complete_bundle_binding_verified"
    ] is True
    assert verification["source_ground_transaction_replay_performed"] is False
    assert verification["persistent_proof_dependency_dag_verified"] is False
    assert verification["plan_certificate_verified"] is False
    assert verification["verification_result"] == (
        "REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_VERIFIED"
    )


def test_independent_verifier_rejects_resigned_source_model_join_claim(
    real_independent_source_binding,
) -> None:
    preregistration, bundle, snapshot, binding_bytes, _verification = (
        real_independent_source_binding
    )
    binding = loads_canonical_json(binding_bytes)
    binding["source_numerical_model_identity_joined_to_bundle"] = True
    payload = dict(binding)
    payload.pop("query_bound_reusable_rapm_source_bundle_binding_id")
    binding["query_bound_reusable_rapm_source_bundle_binding_id"] = content_id(
        producer.BINDING_DOMAIN,
        payload,
    )
    with pytest.raises(
        subject.ConstructionK7QueryBoundReusableRAPMSourceBundleBindingIndependentVerifierV1Error
    ):
        subject.verify_query_bound_reusable_rapm_source_bundle_binding_bytes_v1(
            preregistration_bytes=preregistration,
            bundle_directory=bundle,
            snapshot_bytes=snapshot,
            binding_bytes=canonical_json_bytes(binding),
        )
