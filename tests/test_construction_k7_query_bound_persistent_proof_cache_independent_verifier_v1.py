from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_persistent_proof_cache_independent_verifier_v1 as subject
from acfqp import construction_k7_query_bound_persistent_proof_cache_v1 as producer
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json
from tests.test_construction_k7_query_bound_persistent_proof_cache_v1 import (
    real_persistent_proof_cache,
)
from tests.test_construction_k7_query_bound_reusable_rapm_source_bundle_binding_v1 import (
    _retained_paths,
)


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_independent_verifier_import_surface_excludes_cache_and_dag_producers() -> None:
    source = Path(subject.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    assert not any(
        name.endswith("construction_k7_query_bound_persistent_proof_cache_v1")
        or name.endswith("construction_k7_query_bound_rapm_proof_dependency_dag_v1")
        for name in imported
    )
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error",
        "LOCAL_DOMAINS",
        "verify_query_bound_persistent_proof_cache_bundle_bytes_v1",
    }


@pytest.fixture(scope="module")
def real_independently_verified_cache(real_persistent_proof_cache):
    _cache, cache_bytes = real_persistent_proof_cache
    query = producer.freeze_query_bound_proof_cache_query_v1(
        cache_bytes=cache_bytes,
        logical_occurrence_id=_fresh_id("independent-cache-fresh-occurrence"),
        query_ordinal=5,
    )
    result = producer.run_query_bound_proof_cache_consumer_v1(
        cache_bytes=cache_bytes,
        query=query,
    )
    result_bytes = canonical_json_bytes(result.to_document())
    preregistration_path, bundle_path = _retained_paths()
    verification = subject.verify_query_bound_persistent_proof_cache_bundle_bytes_v1(
        preregistration_bytes=preregistration_path.read_bytes(),
        bundle_directory=bundle_path,
        cache_bytes=cache_bytes,
        result_bytes=result_bytes,
    )
    return cache_bytes, result_bytes, verification


def test_real_cache_and_fresh_query_are_independently_replayed(
    real_independently_verified_cache,
) -> None:
    _cache_bytes, _result_bytes, verification = real_independently_verified_cache
    assert verification["source_occurrence_complete_bundle_binding_verified"] is True
    assert verification["proof_dependency_dag_verified"] is True
    assert verification["persistent_cache_verified"] is True
    assert verification["fresh_query_consumption_verified"] is True
    assert verification["proof_dependency_node_count"] == 41
    assert verification["evaluation_full_planner_replay_count"] == 3
    assert verification["operational_full_planner_call_count"] == 0
    assert verification["operational_new_ground_access_count"] == 0
    assert verification["evaluation_replay_excluded_from_operational_work"] is True
    assert verification["source_ground_transaction_bytes_replayed"] is False
    assert verification["local_allowed_after_result"] is False
    assert verification["plan_certificate_verified"] is False
    assert verification["next_required_action"] == "DIRECT_GROUND_FALLBACK"
    assert verification["verification_result"] == (
        "PERSISTENT_PROOF_CACHE_AND_FRESH_QUERY_VERIFIED"
    )


def test_independent_result_replay_rejects_fully_resigned_planner_claim(
    real_persistent_proof_cache,
) -> None:
    _cache, cache_bytes = real_persistent_proof_cache
    cache = loads_canonical_json(cache_bytes)
    query = producer.freeze_query_bound_proof_cache_query_v1(
        cache_bytes=cache_bytes,
        logical_occurrence_id=_fresh_id("independent-cache-claim-attack"),
        query_ordinal=6,
    )
    result = producer.run_query_bound_proof_cache_consumer_v1(
        cache_bytes=cache_bytes,
        query=query,
    )
    document = loads_canonical_json(canonical_json_bytes(result.to_document()))
    document["full_planner_call_count"] = 1
    payload = dict(document)
    payload.pop("query")
    payload.pop("query_bound_proof_cache_consumption_id")
    document["query_bound_proof_cache_consumption_id"] = content_id(
        subject.CONSUMPTION_DOMAIN,
        payload,
    )
    target_proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
        canonical_json_bytes(
            cache["proof_dependency_transition"]["target_graph"]["numerical_proof"]
        )
    )
    inventory = tuple(
        (item["role_key"], item["node_id"])
        for item in cache["cached_node_inventory"]
    )
    with pytest.raises(
        subject.ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error
    ):
        subject._verify_consumption(
            result_bytes=canonical_json_bytes(document),
            cache=cache,
            target_proof=target_proof,
            cache_id=cache["query_bound_persistent_proof_cache_id"],
            inventory=inventory,
        )


def test_public_verifier_rejects_unknown_cache_field_before_authority_replay(
    real_persistent_proof_cache,
) -> None:
    _cache, cache_bytes = real_persistent_proof_cache
    cache = loads_canonical_json(cache_bytes)
    cache["unknown_field"] = True
    preregistration_path, bundle_path = _retained_paths()
    with pytest.raises(
        subject.ConstructionK7QueryBoundPersistentProofCacheIndependentVerifierV1Error
    ):
        subject.verify_query_bound_persistent_proof_cache_bundle_bytes_v1(
            preregistration_bytes=preregistration_path.read_bytes(),
            bundle_directory=bundle_path,
            cache_bytes=canonical_json_bytes(cache),
            result_bytes=b"{}",
        )
