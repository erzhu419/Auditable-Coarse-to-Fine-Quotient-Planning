from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import pickle
from types import SimpleNamespace
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_construction_native_accounting_foundation_v2 as authority
from acfqp import (
    v075_construction_native_accounting_foundation_independent_verifier_v2
    as independent,
)


_DOMAINS = {
    "boundary": "acfqp:v075-accounting-boundary-profile:v2",
    "coverage": "acfqp:v075-counter-coverage-matrix:v2",
    "role_registry": "acfqp:v075-accounting-role-registry:v2",
    "terminal_registry": "acfqp:v075-terminal-derivation-registry:v2",
    "readiness": "acfqp:v075-accounting-readiness-attestation:v2",
}


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _hash(role: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        _DOMAINS[role].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


class _FakeRaw183:
    def __init__(self) -> None:
        self.closure_id = _id("source-closure")
        self.semantic_terminal_closure_id = _id("terminal-closure")
        self.repository_closure_id = _id("repository-closure")
        self.source_archive_binding_id = _id("archive-binding")
        self.provenance_dag_id = _id("provenance-dag")
        self.verification_id = _id("raw-183-verification")


def _raw_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, Any], _FakeRaw183]:
    upstream = _FakeRaw183()
    monkeypatch.setattr(
        authority.source_verifier,
        "V075ConstructionSourceCodeProvenanceIndependentVerificationV2",
        _FakeRaw183,
    )
    monkeypatch.setattr(
        authority.source_verifier,
        "verify_v075_construction_source_code_provenance_bytes_v2",
        lambda **_kwargs: upstream,
    )
    bundle_id = _id("portable-bundle")
    context_id = _id("public-context")
    result_id = _id("multiround-result")
    result_bytes = canonical_json_bytes(
        {
            "result_id": result_id,
            "status": "CHILD_ACTION_ROW_CAP_EXCEEDED",
        }
    )
    bundle_bytes = canonical_json_bytes(
        {
            "bundle_id": bundle_id,
            "artifact_records": [
                {
                    "role": "MULTIROUND_RESULT",
                    "semantic_artifact_id": result_id,
                    "canonical_artifact_bytes_hex": result_bytes.hex(),
                }
            ],
        }
    )
    source_bytes = canonical_json_bytes(
        {
            "closure_id": upstream.closure_id,
            "semantic_terminal_closure_id": (
                upstream.semantic_terminal_closure_id
            ),
            "repository_closure_id": upstream.repository_closure_id,
            "source_archive_binding_id": upstream.source_archive_binding_id,
            "provenance_dag_id": upstream.provenance_dag_id,
            "portable_bundle_id": bundle_id,
            "public_context_closure_id": context_id,
            "source_archive_binding": {
                "binding_id": upstream.source_archive_binding_id,
                "runtime_source_closure_id": _id("runtime-source"),
                "source_archive_id": _id("source-archive"),
                "runtime_lock_id": _id("runtime-lock"),
                "compile_verification_id": _id("compile-verification"),
            },
        }
    )
    return (
        {
            "source_code_provenance_bytes": source_bytes,
            "repository_root": "/unused/raw-183-already-verified",
            "portable_bundle_bytes": bundle_bytes,
            "public_context_closure_bytes": b"public-context",
            "private_generation_seed": b"private-seed",
            "private_salt": b"private-salt",
        },
        upstream,
    )


def _produce(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, Any], authority.V075AccountingReadinessAttestationV2]:
    inputs, _upstream = _raw_inputs(monkeypatch)
    return (
        inputs,
        authority.replay_v075_construction_native_accounting_foundation_v2(
            **inputs
        ),
    )


def _rehash_component(
    document: dict[str, Any],
    *,
    field: str,
    id_field: str,
    role: str,
) -> None:
    component = document[field]
    payload = {key: value for key, value in component.items() if key != id_field}
    component[id_field] = _hash(role, payload)
    document[f"{field}_id"] = component[id_field]


def _rehash_readiness(document: dict[str, Any]) -> bytes:
    payload = {
        key: value for key, value in document.items() if key != "attestation_id"
    }
    document["attestation_id"] = _hash("readiness", payload)
    return canonical_json_bytes(document)


def _verify_rejects(
    *,
    inputs: dict[str, Any],
    attacked_document: dict[str, Any],
) -> None:
    with pytest.raises(
        independent.V075ConstructionNativeAccountingIndependentV2Violation
    ):
        independent.verify_v075_construction_native_accounting_foundation_bytes_v2(
            foundation_bytes=_rehash_readiness(attacked_document),
            **inputs,
        )


def test_signatures_and_exact_synthetic_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = (
        "source_code_provenance_bytes",
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
        "private_generation_seed",
        "private_salt",
    )
    assert tuple(
        inspect.signature(
            authority
            .replay_v075_construction_native_accounting_foundation_v2
        ).parameters
    ) == raw
    assert tuple(
        inspect.signature(
            independent
            .verify_v075_construction_native_accounting_foundation_bytes_v2
        ).parameters
    ) == ("foundation_bytes", *raw)

    inputs, attestation = _produce(monkeypatch)
    verification = (
        independent
        .verify_v075_construction_native_accounting_foundation_bytes_v2(
            foundation_bytes=attestation.canonical_bytes,
            **inputs,
        )
    )
    document = attestation.to_document()
    counts = document["coverage_matrix"]["classification_counts"]
    assert counts == {
        "EXACT_EXISTING_LEAF": 49,
        "RESERVED_V2_PATH_NAME": 13,
        "NOT_INSTRUMENTED": 95,
    }
    rows = document["coverage_matrix"]["rows"]
    assert len(rows) == 157
    custom_families = {
        "V075_ROUTE_CORE_HISTORICAL_CUSTOM",
        "V075_BATCH_NATIVE_HISTORICAL_CUSTOM",
        "V075_PLANNER_HISTORICAL_CUSTOM",
        "V075_REGISTERED_WORKER_HISTORICAL_CUSTOM",
        "V075_DIRECT_HISTORICAL_CUSTOM",
    }
    assert {
        row["source_family"] for row in rows if row["legacy_custom_counter"]
    } == custom_families
    assert all(
        row["classification"] == "NOT_INSTRUMENTED"
        and row["target_path"] is None
        and not row["definition_registered_in_v1"]
        and not row["counter_record_v1_compatible"]
        and not row["currently_instrumented_for_registry_v2"]
        for row in rows
        if row["source_family"] in custom_families
    )
    assert {
        row["source_path"]
        for row in rows
        if row["classification"] == "RESERVED_V2_PATH_NAME"
    } == {
        "build.initial_interval_log_search_evaluations",
        "build.initial_interval_row_evaluations",
        "build.initial_model_rows_built",
        "build.initial_policy_assignments_evaluated",
        "build.initial_semantic_record_replays",
        "build.initial_semantic_role_closures",
        "build.initial_source_units_compiled",
        "acquisition.initial_observer_accepted_draws",
        "acquisition.initial_observer_random_word_calls",
        "acquisition.initial_observer_rejections",
        "acquisition.initial_outcome_aggregate_rows",
        "acquisition.initial_signed_batches",
        "acquisition.initial_support_freezes",
    }
    assert document["role_registry"]["portable_role_count"] == 67
    assert document["terminal_registry"]["specific_derivations"] == [
        {
            "source_profile": (
                "v075_observer_signed_multiround_occurrence_runner_v2"
            ),
            "source_cause": "CHILD_ACTION_ROW_CAP_EXCEEDED",
            "derived_terminal_scope": "ROUTE_ATTEMPT",
            "derived_terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "derived_terminal_code": "ATTEMPT_BUDGET_EXHAUSTED",
            "specific_cause_retained": True,
            "infeasibility_mapping_allowed": False,
            "caller_terminal_self_report_authoritative": False,
        }
    ]
    assert (
        document["coverage_matrix"][
            "current_root_only_counter_record_count"
        ]
        == 0
    )
    assert (
        document["coverage_matrix"][
            "legacy_custom_exact_path_intersection_with_v1"
        ]
        == 0
    )
    coverage = document["coverage_matrix"]
    boundary = document["boundary_profile"]
    for payload in (boundary, coverage):
        assert payload["reserved_v2_path_intersection_with_v1"] == 0
        assert (
            payload["reserved_v2_path_intersection_with_legacy_custom"]
            == 0
        )
        assert payload["legacy_custom_distinct_path_count"] == 87
    assert coverage["current_root_only_missing_recorder_path_count"] == 11
    assert len(coverage["current_root_only_missing_recorder_paths"]) == 11
    assert coverage["planned_counter_semantics_frozen"] is False
    assert (
        document["boundary_profile"]["base_counter_registry_id"]
        == authority.EXPECTED_COUNTER_REGISTRY_V1_ID
    )
    assert (
        document["boundary_profile"]["base_comparison_profile_id"]
        == authority.EXPECTED_COMPARISON_PROFILE_V1_ID
    )
    assert (
        document["boundary_profile"][
            "base_actual_projection_profile_id"
        ]
        == authority.EXPECTED_ACTUAL_PROJECTION_PROFILE_V1_ID
    )
    assert document["portable_bundle_id"] == _id("portable-bundle")
    assert document["public_context_closure_id"] == _id("public-context")
    assert verification.attestation_id == attestation.attestation_id
    assert verification.attestation_sha256 == hashlib.sha256(
        attestation.canonical_bytes
    ).hexdigest()


def test_raw_183_runs_before_claim_is_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def raw(**_kwargs: Any) -> Any:
        calls.append("raw-1.83")
        raise RuntimeError("private marker")

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        calls.append("claim")
        raise AssertionError("claim was read before raw 1.83")

    monkeypatch.setattr(
        independent.source_verifier,
        "verify_v075_construction_source_code_provenance_bytes_v2",
        raw,
    )
    monkeypatch.setattr(independent, "_strict_document", forbidden)
    with pytest.raises(
        independent.V075ConstructionNativeAccountingIndependentV2Violation
    ) as captured:
        independent.verify_v075_construction_native_accounting_foundation_bytes_v2(
            foundation_bytes=b"claimed",
            source_code_provenance_bytes=b"source",
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=b"seed",
            private_salt=b"salt",
        )
    assert calls == ["raw-1.83"]
    assert "private marker" not in str(captured.value)
    assert captured.value.__cause__ is None


def test_independent_ast_excludes_producer_freezer_and_issuer() -> None:
    source = inspect.getsource(independent)
    tree = ast.parse(source)
    forbidden_names = {
        "_freeze_after_raw_183",
        "_READINESS_ISSUER",
        "replay_v075_construction_native_accounting_foundation_v2",
        "V075AccountingReadinessAttestationV2",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "acfqp":
            assert all(
                alias.name
                != "v075_construction_native_accounting_foundation_v2"
                for alias in node.names
            )
        if isinstance(node, ast.Call):
            function = node.func
            called = (
                function.attr
                if isinstance(function, ast.Attribute)
                else function.id if isinstance(function, ast.Name) else None
            )
            assert called not in forbidden_names
    assert not forbidden_names.intersection(source.split())


@pytest.mark.parametrize(
    "attack",
    ("missing", "duplicate", "relabel", "custom_substitution"),
)
def test_coverage_attacks_fail_after_coherent_rehash(
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    inputs, attestation = _produce(monkeypatch)
    document = copy.deepcopy(attestation.to_document())
    coverage = document["coverage_matrix"]
    rows = coverage["rows"]
    custom_index = next(
        index
        for index, row in enumerate(rows)
        if row["source_family"] == "V075_ROUTE_CORE_HISTORICAL_CUSTOM"
    )
    if attack == "missing":
        rows.pop(custom_index)
    elif attack == "duplicate":
        rows.append(copy.deepcopy(rows[custom_index]))
    elif attack == "relabel":
        rows[custom_index]["source_family"] = (
            "V075_ROUTE_CORE_HISTORICAL_CUSTOM_RELABELLED"
        )
    else:
        row = rows[custom_index]
        row.update(
            {
                "source_schema": "acfqp.counter_record.v1",
                "source_path": "fallback.ground_steps",
                "classification": "EXACT_EXISTING_LEAF",
                "target_path": "fallback.ground_steps",
                "legacy_custom_counter": False,
                "definition_registered_in_v1": True,
                "counter_record_v1_compatible": True,
            }
        )
    rows.sort(key=lambda row: (row["source_family"], row["source_path"]))
    coverage["classification_counts"] = {
        label: sum(row["classification"] == label for row in rows)
        for label in (
            "EXACT_EXISTING_LEAF",
            "RESERVED_V2_PATH_NAME",
            "NOT_INSTRUMENTED",
        )
    }
    _rehash_component(
        document,
        field="coverage_matrix",
        id_field="matrix_id",
        role="coverage",
    )
    _verify_rejects(inputs=inputs, attacked_document=document)


def test_counter_registry_v1_mutation_claim_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, attestation = _produce(monkeypatch)
    document = copy.deepcopy(attestation.to_document())
    document["boundary_profile"]["counter_registry_v1_mutation_allowed"] = True
    _rehash_component(
        document,
        field="boundary_profile",
        id_field="profile_id",
        role="boundary",
    )
    document["coverage_matrix"]["boundary_profile_id"] = document[
        "boundary_profile_id"
    ]
    _rehash_component(
        document,
        field="coverage_matrix",
        id_field="matrix_id",
        role="coverage",
    )
    _verify_rejects(inputs=inputs, attacked_document=document)


def test_legacy_custom_catalogue_drift_and_v1_overlap_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, _upstream = _raw_inputs(monkeypatch)
    monkeypatch.setattr(
        authority.route_core,
        "COUNTER_PATHS",
        (
            *authority.route_core.COUNTER_PATHS,
            "common.hash_invocations",
        ),
    )
    with pytest.raises(
        authority.V075ConstructionNativeAccountingFoundationV2Violation
    ):
        authority.replay_v075_construction_native_accounting_foundation_v2(
            **inputs
        )


def test_reserved_v2_path_collision_fails_in_both_replays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, attestation = _produce(monkeypatch)
    collided = tuple(
        sorted(
            (
                *authority._INITIAL_BUILD_PATHS,  # noqa: SLF001
                "common.hash_invocations",
            )
        )
    )
    monkeypatch.setattr(authority, "_INITIAL_BUILD_PATHS", collided)
    with pytest.raises(
        authority.V075ConstructionNativeAccountingFoundationV2Violation
    ):
        authority.replay_v075_construction_native_accounting_foundation_v2(
            **inputs
        )
    monkeypatch.setattr(
        independent,
        "_INITIAL_BUILD_PATHS",
        tuple(
            sorted(
                (
                    *independent._INITIAL_BUILD_PATHS,  # noqa: SLF001
                    "common.hash_invocations",
                )
            )
        ),
    )
    with pytest.raises(
        independent.V075ConstructionNativeAccountingIndependentV2Violation
    ):
        independent.verify_v075_construction_native_accounting_foundation_bytes_v2(
            foundation_bytes=attestation.canonical_bytes,
            **inputs,
        )


def test_multiround_source_profile_drift_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, attestation = _produce(monkeypatch)
    monkeypatch.setattr(
        authority.multiround_owner,
        "PROFILE_KEY",
        "drifted_multiround_owner",
    )
    with pytest.raises(
        authority.V075ConstructionNativeAccountingFoundationV2Violation
    ):
        authority.replay_v075_construction_native_accounting_foundation_v2(
            **inputs
        )
    monkeypatch.setattr(
        independent.multiround_owner,
        "PROFILE_KEY",
        "drifted_multiround_owner",
    )
    with pytest.raises(
        independent.V075ConstructionNativeAccountingIndependentV2Violation
    ):
        independent.verify_v075_construction_native_accounting_foundation_bytes_v2(
            foundation_bytes=attestation.canonical_bytes,
            **inputs,
        )


def test_terminal_cap_cannot_be_relabelled_infeasible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, attestation = _produce(monkeypatch)
    document = copy.deepcopy(attestation.to_document())
    derivation = document["terminal_registry"]["specific_derivations"][0]
    derivation.update(
        {
            "derived_terminal_class": "INFEASIBILITY_CERTIFICATE",
            "derived_terminal_code": "FULL_GROUND_EXACT_INFEASIBLE",
            "infeasibility_mapping_allowed": True,
        }
    )
    _rehash_component(
        document,
        field="terminal_registry",
        id_field="registry_id",
        role="terminal_registry",
    )
    _verify_rejects(inputs=inputs, attacked_document=document)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("repository_closure_id", _id("stale-repository")),
        ("portable_bundle_id", _id("stale-bundle")),
        ("runtime_source_closure_id", _id("stale-runtime-source")),
        ("multiround_result_id", _id("stale-multiround")),
    ),
)
def test_stale_upstream_component_identity_fails(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    inputs, attestation = _produce(monkeypatch)
    document = copy.deepcopy(attestation.to_document())
    document[field] = value
    _verify_rejects(inputs=inputs, attacked_document=document)


@pytest.mark.parametrize("attack", ("portable_overlap", "self_reference"))
def test_role_overlap_and_self_reference_fail(
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    inputs, attestation = _produce(monkeypatch)
    document = copy.deepcopy(attestation.to_document())
    roles = document["role_registry"]
    if attack == "portable_overlap":
        roles["companion_roles"][0]["role"] = roles["portable_role_names"][0]
        roles["companion_roles"].sort(key=lambda row: row["role"])
    else:
        roles["portable_semantic_registry_id"] = roles["registry_id"]
    _rehash_component(
        document,
        field="role_registry",
        id_field="registry_id",
        role="role_registry",
    )
    _verify_rejects(inputs=inputs, attacked_document=document)


@pytest.mark.parametrize(
    "field",
    (
        "all_path_native_accounting_complete",
        "terminal_campaign_closure_complete",
        "complete_bundle_verifier_complete",
        "loaded_source_receipt_complete",
        "source_authority_complete",
        "code_provenance_complete",
        "counter_completeness_gate_passed",
        "accounting_gate_passed",
        "official_execution_allowed",
        "production_authorizing",
        "fresh_heldout_accessed",
        "scientific_endpoint_credit_allowed",
        "plan_certificate",
        "infeasibility_certificate",
    ),
)
def test_locked_completion_and_science_overclaims_fail(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    inputs, attestation = _produce(monkeypatch)
    document = copy.deepcopy(attestation.to_document())
    document[field] = True
    _verify_rejects(inputs=inputs, attacked_document=document)


def test_portable_multiround_cap_identity_is_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, attestation = _produce(monkeypatch)
    bundle = copy.deepcopy(json.loads(inputs["portable_bundle_bytes"]))
    result = json.loads(
        bytes.fromhex(
            bundle["artifact_records"][0]["canonical_artifact_bytes_hex"]
        )
    )
    result["status"] = "FEASIBLE_CERTIFIED"
    bundle["artifact_records"][0]["canonical_artifact_bytes_hex"] = (
        canonical_json_bytes(result).hex()
    )
    attacked_inputs = {
        **inputs,
        "portable_bundle_bytes": canonical_json_bytes(bundle),
    }
    with pytest.raises(
        independent.V075ConstructionNativeAccountingIndependentV2Violation
    ):
        independent.verify_v075_construction_native_accounting_foundation_bytes_v2(
            foundation_bytes=attestation.canonical_bytes,
            **attacked_inputs,
        )


def test_pickle_caller_mint_and_production_gates_stay_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, attestation = _produce(monkeypatch)
    verification = (
        independent
        .verify_v075_construction_native_accounting_foundation_bytes_v2(
            foundation_bytes=attestation.canonical_bytes,
            **inputs,
        )
    )
    with pytest.raises(TypeError, match="in-memory-only"):
        pickle.dumps(attestation)
    with pytest.raises(TypeError, match="in-memory-only"):
        pickle.dumps(verification)
    with pytest.raises(
        authority.V075ConstructionNativeAccountingProductionV2NotReady
    ):
        authority.assert_v075_construction_native_accounting_production_gate_v2(
            attestation
        )
    with pytest.raises(
        authority.V075ConstructionNativeAccountingFoundationV2Violation,
        match="duck types",
    ):
        authority.assert_v075_construction_native_accounting_production_gate_v2(
            SimpleNamespace()
        )


def test_all_module_level_locks_are_closed() -> None:
    for module in (authority, independent):
        for name in (
            "OFFICIAL_EXECUTION_ALLOWED",
            "PRODUCTION_AUTHORIZING",
            "SOURCE_AUTHORITY_COMPLETE",
            "CODE_PROVENANCE_COMPLETE",
            "LOADED_SOURCE_RECEIPT_COMPLETE",
            "ALL_PATH_NATIVE_ACCOUNTING_COMPLETE",
            "TERMINAL_CAMPAIGN_CLOSURE_COMPLETE",
            "COMPLETE_BUNDLE_VERIFIER_COMPLETE",
            "COUNTER_COMPLETENESS_GATE_PASSED",
            "ACCOUNTING_GATE_PASSED",
            "FRESH_HELDOUT_ACCESS_ALLOWED",
            "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
            "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
            "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
        ):
            assert getattr(module, name) is False
