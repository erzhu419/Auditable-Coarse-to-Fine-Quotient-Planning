from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

import pytest

from acfqp import accounting_v1
from acfqp import construction_accounting_owner_event_candidates_v1 as owner_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_derived_reconciliation_v1 as derived_v1
from acfqp import construction_k7_formal_accounting_materializer_v1 as materializer
from acfqp import construction_k7_semantic_evidence_closure_v1 as closure_v1
from acfqp import construction_shared_resource_resolution_v2 as shared_v2
from acfqp.phase3e_ids import (
    COMPARISON_VECTOR_DOMAIN,
    COUNTER_RECORD_DOMAIN,
    WORK_VECTOR_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _synthetic_complete_closure() -> closure_v1.K7SemanticEvidenceClosureV1:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    context = closure_v1.K7SemanticEvidenceClosureContextV1(
        closure_v1._CONTEXT_ISSUER,  # noqa: SLF001
        registry.registry_id,
        stage.stage_profile_id,
        _id("boundary-profile"),
        _id("execution-profile"),
        _id("occurrence-authority-bundle"),
        _id("occurrence-authority"),
        _id("cutoff-authority"),
        _id("verified-nine-envelope"),
        _id("owner-candidate-set"),
        _id("profile-native-zero-envelope"),
        _id("derived-reconciliation-readiness"),
        _id("production-runtime-envelope"),
        _id("portable-request-replay"),
        _id("source-snapshot"),
        _id("scientific-occurrence"),
        _id("logical-occurrence"),
        _id("route-attempt"),
        _id("decision-point"),
        _id("measurement-window"),
        _id("terminal-closure-observation"),
    )
    shared_paths = set(shared_v2.SHARED_RESOURCE_PATHS)
    owner_paths = {
        row.target_path for row in owner_v1._emittable_boundaries()  # noqa: SLF001
    }
    derived_paths = set(derived_v1.DERIVED_PATHS)
    native_zero_paths = (
        set(registry.required_paths) - shared_paths - owner_paths - derived_paths
    )
    assert (
        len(shared_paths),
        len(owner_paths),
        len(native_zero_paths),
        len(derived_paths),
    ) == (9, 71, 114, 8)

    formulas = {
        row.path: row
        for row in derived_v1.official_k7_reconciliation_formulas_v1()
    }
    positive_owner = min(owner_paths)
    values = {path: 0 for path in registry.required_paths}
    values.update(
        {
            "common.hash_invocations": 7,
            "io.mounted_bytes_peak": 111,
            "memory.working_bytes_peak": 222,
            "process.launches": 2,
            "process.exit_failures": 0,
            "process.exit_successes": 2,
            "route.attempts": 1,
            "route.failures": 1,
            "route.successes": 0,
            "solver.attempts": 0,
            "solver.failures": 0,
            "solver.successes": 0,
            positive_owner: 2,
        }
    )

    resolutions: list[closure_v1.K7SemanticPathResolutionV1] = []
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        primary_id = _id(f"primary:{path}")
        primitive_ids: tuple[str, ...] = ()
        formula_id: str | None = None
        dependency_paths: tuple[str, ...] = ()
        if path in shared_paths:
            kind = closure_v1.SemanticResolutionKindV1.SHARED_RESOURCE_EXACT
        elif path in owner_paths:
            if path == positive_owner:
                kind = closure_v1.SemanticResolutionKindV1.OWNER_EVENT_STREAM
                primitive_ids = (_id(f"primitive:{path}:0"), _id(f"primitive:{path}:1"))
            else:
                kind = closure_v1.SemanticResolutionKindV1.OWNER_WINDOW_ZERO
        elif path in native_zero_paths:
            kind = closure_v1.SemanticResolutionKindV1.PROFILE_NATIVE_ZERO
        else:
            kind = closure_v1.SemanticResolutionKindV1.DERIVED_RECONCILIATION
            formula_id = formulas[path].formula_id
            dependency_paths = formulas[path].closure_dependency_paths
        recorder_id = closure_v1._path_recorder_authority_id(  # noqa: SLF001
            context_id=context.context_id,
            path=path,
            kind=kind,
            primary_id=primary_id,
        )
        resolutions.append(
            closure_v1.K7SemanticPathResolutionV1(
                closure_v1._RESOLUTION_ISSUER,  # noqa: SLF001
                context.context_id,
                path,
                leaf.semantics_id,
                leaf.owner,
                leaf.unit,
                leaf.lane.value,
                leaf.scope,
                leaf.reducer.value,
                leaf.comparison_axis,
                kind,
                values[path],
                primary_id,
                recorder_id,
                primitive_ids,
                formula_id,
                dependency_paths,
            )
        )
    return closure_v1.K7SemanticEvidenceClosureV1(
        closure_v1._CLOSURE_ISSUER,  # noqa: SLF001
        context,
        tuple(resolutions),
    )


@pytest.fixture(scope="module")
def complete_case():
    closure = _synthetic_complete_closure()
    bundle = materializer._materialize_verified_closure(closure)  # noqa: SLF001
    return closure, bundle


@pytest.fixture
def formal_case(monkeypatch, complete_case):
    closure, bundle = complete_case
    sentinel = object()
    replay_calls: list[tuple[bytes, Any]] = []

    def replay(*, raw: bytes, sentinel: Any):
        assert raw == closure.canonical_bytes
        replay_calls.append((raw, sentinel))
        return closure

    monkeypatch.setattr(
        closure_v1,
        "verify_k7_semantic_evidence_closure_bytes_v1",
        replay,
    )
    inputs = {"sentinel": sentinel}
    return closure, inputs, replay_calls, bundle


def _refreeze(
    document: dict[str, Any],
    *,
    native_zero_paths: set[str],
) -> bytes:
    result = deepcopy(document)
    work = result["work_vector"]
    records = work["records"]
    for record in records:
        payload = dict(record)
        payload.pop("counter_record_id", None)
        record["counter_record_id"] = content_id(COUNTER_RECORD_DOMAIN, payload)
    work["counter_record_ids"] = [row["counter_record_id"] for row in records]
    work_payload = {
        key: value
        for key, value in work.items()
        if key not in {"records", "work_vector_id"}
    }
    work["work_vector_id"] = content_id(WORK_VECTOR_DOMAIN, work_payload)

    comparison = result["comparison_vector"]
    comparison["work_vector_id"] = work["work_vector_id"]
    comparison_payload = dict(comparison)
    comparison_payload.pop("comparison_vector_id", None)
    comparison["comparison_vector_id"] = content_id(
        COMPARISON_VECTOR_DOMAIN,
        comparison_payload,
    )

    by_path = {row["path"]: row for row in records}
    proof = result["actual_projection_proof"]
    proof["work_vector_id"] = work["work_vector_id"]
    proof["comparison_vector_id"] = comparison["comparison_vector_id"]
    proof["counter_record_ids"] = work["counter_record_ids"]
    proof["projected_counter_record_ids"] = [
        by_path[path]["counter_record_id"]
        for path in proof["projected_source_paths"]
        if path in by_path
    ]
    proof["profile_native_zero_counter_record_ids"] = [
        by_path[path]["counter_record_id"]
        for path in sorted(native_zero_paths)
        if path in by_path
    ]
    proof_payload = dict(proof)
    proof_payload.pop("formal_actual_projection_proof_id", None)
    proof["formal_actual_projection_proof_id"] = content_id(
        materializer.ACTUAL_PROJECTION_PROOF_V6_DOMAIN,
        proof_payload,
    )

    result["counter_record_ids"] = work["counter_record_ids"]
    bundle_payload = dict(result)
    bundle_payload.pop("formal_accounting_materialization_bundle_id", None)
    result["formal_accounting_materialization_bundle_id"] = content_id(
        materializer.MATERIALIZATION_BUNDLE_V1_DOMAIN,
        bundle_payload,
    )
    return canonical_json_bytes(result)


def test_materializes_exact_v6_records_vector_and_projection_without_v1_registry(
    formal_case,
    monkeypatch,
) -> None:
    closure, inputs, replay_calls, bundle = formal_case

    def forbidden(*_args, **_kwargs):
        raise AssertionError("V1 registry vector API was called")

    monkeypatch.setattr(accounting_v1.CounterRegistryV1, "materialize", forbidden)
    monkeypatch.setattr(accounting_v1.CounterRegistryV1, "validate_vector", forbidden)
    materialized = materializer.materialize_k7_formal_accounting_v1(
        semantic_closure_raw=closure.canonical_bytes,
        closure_replay_inputs=inputs,
    )
    verified = materializer.verify_k7_formal_accounting_materialization_bytes_v1(
        raw=materialized.canonical_bytes,
        semantic_closure_raw=closure.canonical_bytes,
        closure_replay_inputs=inputs,
    )
    registry = registry_v6.official_counter_registry_v6()
    expected_projected = tuple(row.path for row in registry.operational_leaves)
    document = verified.to_document()

    assert len(replay_calls) == 2
    assert verified.bundle_id == materialized.bundle_id == bundle.bundle_id
    assert len(materialized.work_vector.records) == 202
    assert tuple(row.path for row in materialized.work_vector.records) == registry.required_paths
    assert all(row.observed is True for row in materialized.work_vector.records)
    assert len({row.recorder_id for row in materialized.work_vector.records}) == 202
    assert materialized.work_vector.route_kind is accounting_v1.RouteKindEnum.ABSTRACT_FAILED_PREFIX
    assert materialized.comparison_vector.work_vector_id == materialized.work_vector.work_vector_id
    assert materialized.actual_projection_proof.projected_source_paths == expected_projected
    assert materialized.actual_projection_proof.projection_term_count == 182
    assert len(materialized.actual_projection_proof.profile_native_zero_counter_record_ids) == 114
    assert dict(materialized.comparison_vector.values)["peak_mounted_bytes"] == 111
    assert dict(materialized.comparison_vector.values)["peak_working_bytes"] == 222
    assert document["formal_accounting_materialized"] is True
    assert document["official_execution_allowed"] is False
    assert document["counter_completeness_gate_passed"] is False
    assert document["workload_economics_gate_passed"] is False
    assert document["terminal_artifact_issued"] is False
    assert document["certificate_issued"] is False


@pytest.mark.parametrize(
    "attack",
    (
        "missing",
        "duplicate",
        "unknown",
        "wrong_metadata",
        "wrong_lane",
        "projection_injection",
        "actual_mismatch",
    ),
)
def test_portable_verifier_rejects_record_projection_and_actual_attacks(
    formal_case,
    attack: str,
) -> None:
    closure, inputs, _replay_calls, bundle = formal_case
    document = loads_canonical_json(bundle.canonical_bytes)
    assert type(document) is dict
    records = document["work_vector"]["records"]
    native_zero_paths = {
        row.path
        for row in closure.resolutions
        if row.kind is closure_v1.SemanticResolutionKindV1.PROFILE_NATIVE_ZERO
    }
    if attack == "missing":
        records.pop()
    elif attack == "duplicate":
        records[-1] = deepcopy(records[0])
    elif attack == "unknown":
        records[0]["path"] = "unknown.injected_path"
    elif attack == "wrong_metadata":
        records[0]["semantics_id"] = "wrong-semantics-v1"
    elif attack == "wrong_lane":
        records[0]["lane"] = (
            "diagnostic" if records[0]["lane"] == "operational" else "operational"
        )
    elif attack == "projection_injection":
        proof = document["actual_projection_proof"]
        diagnostic_path = next(
            row.path
            for row in registry_v6.official_counter_registry_v6().leaves
            if row.required and row.lane is not accounting_v1.LaneEnum.OPERATIONAL
        )
        proof["projected_source_paths"][0] = diagnostic_path
    else:
        document["comparison_vector"]["values"][0]["value"] += 1

    attacked = _refreeze(document, native_zero_paths=native_zero_paths)
    with pytest.raises(
        materializer.ConstructionK7FormalAccountingMaterializerV1Error,
    ):
        materializer.verify_k7_formal_accounting_materialization_bytes_v1(
            raw=attacked,
            semantic_closure_raw=closure.canonical_bytes,
            closure_replay_inputs=inputs,
        )


def test_duplicate_projection_term_is_rejected_after_full_refreeze(formal_case) -> None:
    closure, inputs, _replay_calls, bundle = formal_case
    document = loads_canonical_json(bundle.canonical_bytes)
    assert type(document) is dict
    proof = document["actual_projection_proof"]
    proof["projected_source_paths"][1] = proof["projected_source_paths"][0]
    native_zero_paths = {
        row.path
        for row in closure.resolutions
        if row.kind is closure_v1.SemanticResolutionKindV1.PROFILE_NATIVE_ZERO
    }
    attacked = _refreeze(document, native_zero_paths=native_zero_paths)
    with pytest.raises(
        materializer.ConstructionK7FormalAccountingMaterializerV1Error,
    ):
        materializer.verify_k7_formal_accounting_materialization_bytes_v1(
            raw=attacked,
            semantic_closure_raw=closure.canonical_bytes,
            closure_replay_inputs=inputs,
        )
