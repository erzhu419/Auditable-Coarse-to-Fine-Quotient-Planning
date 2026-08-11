from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_accounted_continuation_v1 as continuation_v1
from acfqp import construction_k7_query_bound_persistent_proof_cache_v1 as subject
from acfqp import construction_k7_query_bound_rapm_proof_dependency_dag_v1 as dag_v1
from acfqp import construction_k7_query_bound_reusable_rapm_snapshot_v1 as snapshot_v1
from acfqp import construction_k7_query_bound_reusable_rapm_source_bundle_binding_v1 as binding_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)
from tests.test_construction_k7_query_bound_reusable_rapm_source_bundle_binding_v1 import (
    _retained_paths,
    _role_bytes,
)


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_domains_and_public_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 4
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundPersistentProofCacheV1Error",
        "LOCAL_DOMAINS",
        "QueryBoundPersistentProofCacheV1",
        "QueryBoundProofCacheConsumptionV1",
        "QueryBoundProofCacheNoReuseControlV1",
        "QueryBoundProofCacheQueryV1",
        "freeze_query_bound_proof_cache_query_v1",
        "load_query_bound_persistent_proof_cache_bytes_v1",
        "materialize_query_bound_persistent_proof_cache_bytes_v1",
        "materialize_query_bound_persistent_proof_cache_v1",
        "run_query_bound_proof_cache_consumer_v1",
        "run_query_bound_proof_cache_no_reuse_control_v1",
        "verify_query_bound_proof_cache_consumption_bytes_v1",
    }


@pytest.fixture(scope="module")
def real_persistent_proof_cache():
    retained = os.environ.get("ACFQP_RETAINED_PERSISTENT_PROOF_CACHE_INPUTS")
    if retained:
        retained_root = Path(retained)
        retained_inputs = (
            retained_root / "SOURCE_BUNDLE_BINDING.json",
            retained_root / "REUSABLE_RAPM_SNAPSHOT.json",
            retained_root / "PROOF_DEPENDENCY_TRANSITION.json",
        )
        if all(path.is_file() for path in retained_inputs):
            cache = subject.materialize_query_bound_persistent_proof_cache_bytes_v1(
                binding_bytes=retained_inputs[0].read_bytes(),
                snapshot_bytes=retained_inputs[1].read_bytes(),
                transition_bytes=retained_inputs[2].read_bytes(),
            )
            return cache, canonical_json_bytes(cache.to_document())
    preregistration_path, bundle_path = _retained_paths()
    preregistration_bytes = preregistration_path.read_bytes()
    preregistration = loads_canonical_json(preregistration_bytes)
    business = loads_canonical_json(
        (bundle_path / "BUSINESS_RESULT.json").read_bytes()
    )
    inputs = _role_bytes(
        preregistration,
        occurrence_id=business["occurrence_id"],
    )
    continuation = continuation_v1.run_query_bound_accounted_continuation_v1(
        source_trace_bytes=inputs["SOURCE_TRACE"],
        build_epoch_envelope_bytes=inputs["BUILD_EPOCH_ENVELOPE"],
        root_query_result_bytes=inputs["ROOT_QUERY_RESULT"],
        overlay_bytes=inputs["RECOVERY_OVERLAY"],
        request_bytes=inputs["RECOVERY_REQUEST"],
    )
    snapshot = snapshot_v1.freeze_query_bound_reusable_rapm_snapshot_v1(
        continuation.final_local_replanning
    )
    binding = binding_v1.bind_query_bound_reusable_rapm_source_bundle_v1(
        preregistration_bytes=preregistration_bytes,
        bundle_directory=bundle_path,
        snapshot_bytes=canonical_json_bytes(snapshot.to_document()),
    )
    transition = dag_v1.freeze_query_bound_rapm_proof_dependency_transition_v1(
        continuation.final_local_replanning
    )
    if retained:
        retained_root = Path(retained)
        retained_root.mkdir(parents=True, exist_ok=True)
        (retained_root / "SOURCE_BUNDLE_BINDING.json").write_bytes(
            canonical_json_bytes(binding.to_document())
        )
        (retained_root / "REUSABLE_RAPM_SNAPSHOT.json").write_bytes(
            canonical_json_bytes(snapshot.to_document())
        )
        (retained_root / "PROOF_DEPENDENCY_TRANSITION.json").write_bytes(
            canonical_json_bytes(transition.to_document())
        )
    cache = subject.materialize_query_bound_persistent_proof_cache_v1(
        binding=binding,
        snapshot=snapshot,
        transition=transition,
    )
    cache_bytes = canonical_json_bytes(cache.to_document())
    return cache, cache_bytes


def test_real_source_bound_proof_cache_is_persistent_and_structurally_replayable(
    real_persistent_proof_cache,
) -> None:
    cache, cache_bytes = real_persistent_proof_cache
    replayed = subject.load_query_bound_persistent_proof_cache_bytes_v1(
        cache_bytes
    )
    document = replayed.to_document()
    assert replayed.cache_id == cache.cache_id
    assert document["cached_proof_node_count"] == 41
    assert document["persistent_cross_query_cache_materialized"] is True
    assert document["fresh_query_cache_consumer_present"] is True
    assert document["online_structural_replay_without_planner_supported"] is True
    assert document["fresh_query_ground_access_authority_present"] is False
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False


def test_fresh_occurrence_consumes_all_nodes_without_planner_or_ground(
    real_persistent_proof_cache,
    monkeypatch,
) -> None:
    _cache, cache_bytes = real_persistent_proof_cache
    query = subject.freeze_query_bound_proof_cache_query_v1(
        cache_bytes=cache_bytes,
        logical_occurrence_id=_fresh_id("persistent-cache-fresh-occurrence"),
        query_ordinal=2,
    )

    def forbidden_planner(*_args, **_kwargs):
        raise AssertionError("operational cache consumer called full planner")

    monkeypatch.setattr(
        subject.planning_v2,
        "plan_v075_construction_numerical_model_v2",
        forbidden_planner,
    )
    result = subject.run_query_bound_proof_cache_consumer_v1(
        cache_bytes=cache_bytes,
        query=query,
    )
    result_bytes = canonical_json_bytes(result.to_document())
    replayed = subject.verify_query_bound_proof_cache_consumption_bytes_v1(
        cache_bytes=cache_bytes,
        result_bytes=result_bytes,
    )
    document = replayed.to_document()
    assert document["proof_node_reuse_count"] == 41
    assert document["proof_node_compute_count"] == 0
    assert document["full_planner_call_count"] == 0
    assert document["new_ground_access_count"] == 0
    assert document["exact_cached_certificate_failure_replayed"] is True
    assert document["query_local_ground_recovery_eligible"] is True
    assert document["query_local_ground_recovery_executed_here"] is False
    assert document["plan_certificate_issued"] is False


def test_matched_no_reuse_control_recomputes_identical_proof(
    real_persistent_proof_cache,
) -> None:
    _cache, cache_bytes = real_persistent_proof_cache
    query = subject.freeze_query_bound_proof_cache_query_v1(
        cache_bytes=cache_bytes,
        logical_occurrence_id=_fresh_id("persistent-cache-no-reuse-control"),
        query_ordinal=3,
    )
    control = subject.run_query_bound_proof_cache_no_reuse_control_v1(
        cache_bytes=cache_bytes,
        query=query,
    )
    document = control.to_document()
    assert document["cached_numerical_proof_id"] == (
        document["recomputed_numerical_proof_id"]
    )
    assert document["full_planner_call_count"] == 1
    assert document["proof_node_compute_count"] == 41
    assert document["proof_node_reuse_count"] == 0
    assert document["proof_bytes_match_cache"] is True
    assert document["evaluation_only"] is True
    assert document["operational_route_work"] is False


def test_consumption_replay_rejects_resigned_compute_claim(
    real_persistent_proof_cache,
) -> None:
    _cache, cache_bytes = real_persistent_proof_cache
    query = subject.freeze_query_bound_proof_cache_query_v1(
        cache_bytes=cache_bytes,
        logical_occurrence_id=_fresh_id("persistent-cache-claim-change"),
        query_ordinal=4,
    )
    result = subject.run_query_bound_proof_cache_consumer_v1(
        cache_bytes=cache_bytes,
        query=query,
    )
    document = loads_canonical_json(canonical_json_bytes(result.to_document()))
    document["proof_node_compute_count"] = 1
    payload = dict(document)
    payload.pop("query")
    payload.pop("query_bound_proof_cache_consumption_id")
    document["query_bound_proof_cache_consumption_id"] = content_id(
        subject.CONSUMPTION_DOMAIN,
        payload,
    )
    with pytest.raises(
        subject.ConstructionK7QueryBoundPersistentProofCacheV1Error
    ):
        subject.verify_query_bound_proof_cache_consumption_bytes_v1(
            cache_bytes=cache_bytes,
            result_bytes=canonical_json_bytes(document),
        )


def test_cache_replay_rejects_fully_resigned_transition_claim(
    real_persistent_proof_cache,
) -> None:
    _cache, cache_bytes = real_persistent_proof_cache
    document = loads_canonical_json(cache_bytes)
    transition = document["proof_dependency_transition"]
    transition["persistent_cross_query_cache_materialized"] = True
    transition_payload = dict(transition)
    transition_payload.pop("source_graph")
    transition_payload.pop("target_graph")
    transition_payload.pop("query_bound_rapm_proof_dependency_transition_id")
    transition["query_bound_rapm_proof_dependency_transition_id"] = content_id(
        dag_v1.TRANSITION_DOMAIN,
        transition_payload,
    )
    transition_bytes = canonical_json_bytes(transition)
    document["proof_dependency_transition_id"] = transition[
        "query_bound_rapm_proof_dependency_transition_id"
    ]
    document["proof_dependency_transition_sha256"] = hashlib.sha256(
        transition_bytes
    ).hexdigest()
    document["proof_dependency_transition_byte_count"] = len(transition_bytes)
    cache_payload = dict(document)
    cache_payload.pop("source_bundle_binding")
    cache_payload.pop("reusable_rapm_snapshot")
    cache_payload.pop("proof_dependency_transition")
    cache_payload.pop("query_bound_persistent_proof_cache_id")
    document["query_bound_persistent_proof_cache_id"] = content_id(
        subject.CACHE_DOMAIN,
        cache_payload,
    )
    with pytest.raises(
        subject.ConstructionK7QueryBoundPersistentProofCacheV1Error
    ):
        subject.load_query_bound_persistent_proof_cache_bytes_v1(
            canonical_json_bytes(document)
        )


def test_fresh_query_cannot_reuse_source_occurrence(
    real_persistent_proof_cache,
) -> None:
    cache, cache_bytes = real_persistent_proof_cache
    binding = loads_canonical_json(cache.source_bundle_binding_bytes)
    with pytest.raises(
        subject.ConstructionK7QueryBoundPersistentProofCacheV1Error
    ):
        subject.freeze_query_bound_proof_cache_query_v1(
            cache_bytes=cache_bytes,
            logical_occurrence_id=binding["logical_occurrence_id"],
            query_ordinal=2,
        )


def test_cache_and_query_are_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundPersistentProofCacheV1Error
    ):
        subject.QueryBoundPersistentProofCacheV1(
            object(),
            b"{}",
            b"{}",
            b"{}",
            object(),
            b"{}",
            (),
        )
    with pytest.raises(
        subject.ConstructionK7QueryBoundPersistentProofCacheV1Error
    ):
        subject.QueryBoundProofCacheQueryV1(
            object(),
            *("0" * 64 for _ in range(4)),
            2,
            "0" * 64,
        )
