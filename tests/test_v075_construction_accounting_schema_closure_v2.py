from __future__ import annotations

import ast
import copy
import inspect
import pickle
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import construction_accounting_v2 as accounting_core
from acfqp import (
    v075_construction_accounting_schema_closure_v2 as authority,
)
from acfqp import (
    v075_construction_accounting_schema_independent_verifier_v2
    as independent,
)
from acfqp import (
    v075_construction_native_accounting_foundation_independent_verifier_v2
    as foundation_independent,
)
from test_v075_construction_native_accounting_foundation_v2 import _produce


def _freeze(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    dict[str, object],
    object,
    object,
    authority.V075ConstructionAccountingSchemaClosureV2,
]:
    inputs, foundation = _produce(monkeypatch)
    upstream = (
        foundation_independent
        .verify_v075_construction_native_accounting_foundation_bytes_v2(
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    )
    closure = authority.materialize_v075_construction_accounting_schema_v2(
        upstream=upstream,
        foundation_bytes=foundation.canonical_bytes,
    )
    return inputs, foundation, upstream, closure


def test_exact_schema_closure_and_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, foundation, upstream, closure = _freeze(monkeypatch)
    document = closure.to_document()

    assert document["upstream_attestation_id"] == upstream.attestation_id
    assert document["v2_leaf_count"] == 69
    assert document["v2_operational_leaf_count"] == 53
    assert document["v2_required_leaf_count"] == 62
    assert document["registered_stage_count"] == 8
    assert document["shared_axis_count"] == 8
    assert document["projection_term_count"] == 53
    assert document["reserved_initial_path_count"] == 13
    assert document["closed_reconciliation_operation_path_count"] == 7
    assert document["observer_rejection_lane"] == "diagnostic"
    assert document["observer_rejection_projected"] is False
    assert document["accepted_draw_projection_axis"] == (
        "kernel_transition_calls"
    )
    assert document["counter_registry_id"] == (
        authority.EXPECTED_COUNTER_REGISTRY_V2_ID
    )
    assert document["stage_profile_id"] == (
        authority.EXPECTED_STAGE_PROFILE_V2_ID
    )
    assert document["comparison_profile_id"] == (
        authority.EXPECTED_COMPARISON_PROFILE_V2_ID
    )
    assert document["actual_projection_profile_id"] == (
        authority.EXPECTED_ACTUAL_PROJECTION_PROFILE_V2_ID
    )
    assert document["live_counter_record_count"] == 0
    assert document["work_vector_count"] == 0
    assert document["comparison_vector_count"] == 0
    assert document["actual_projection_proof_count"] == 0
    assert document["critical_live_recorder_gap_count"] == 11
    assert (
        document["critical_live_recorder_gap_list_is_exhaustive"] is False
    )
    assert document["legacy_custom_distinct_path_count"] == 87
    assert (
        document["legacy_custom_paths_native_semantics_complete"] is False
    )
    assert document["unmapped_operation_requires_registry_revision"] is True
    assert document["stage_start_attestation_semantics_frozen"] is False
    assert (
        document["stage_completion_attestation_semantics_frozen"] is False
    )
    assert document["all_path_native_accounting_complete"] is False
    assert document["typed_route_attempt_terminal_complete"] is False
    assert document["logical_occurrence_closure_complete"] is False
    assert document["campaign_closure_complete"] is False
    assert document["official_execution_allowed"] is False
    assert document["fresh_heldout_accessed"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert canonical_json_bytes(document) == closure.canonical_bytes
    with pytest.raises(TypeError):
        closure.counter_registry["counter_registry_id"] = "f" * 64
    with pytest.raises(TypeError):
        closure.counter_registry["leaves"][0]["owner"] = "forged"
    verification = (
        independent.verify_v075_construction_accounting_schema_bytes_v2(
            closure_bytes=closure.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    )
    assert verification.closure_id == closure.closure_id
    assert verification.counter_registry_id == (
        authority.EXPECTED_COUNTER_REGISTRY_V2_ID
    )
    assert verification.to_document()[
        "construction_accounting_core_imported"
    ] is False


def test_signature_requires_verified_foundation_not_raw_secrets() -> None:
    assert tuple(
        inspect.signature(
            authority.materialize_v075_construction_accounting_schema_v2
        ).parameters
    ) == ("upstream", "foundation_bytes")


def test_stale_or_tampered_foundation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, foundation = _produce(monkeypatch)
    upstream = (
        foundation_independent
        .verify_v075_construction_native_accounting_foundation_bytes_v2(
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    )
    attacked = copy.deepcopy(foundation.to_document())
    attacked["all_path_native_accounting_complete"] = True
    with pytest.raises(
        authority.V075ConstructionAccountingSchemaV2Violation
    ):
        authority.materialize_v075_construction_accounting_schema_v2(
            upstream=upstream,
            foundation_bytes=canonical_json_bytes(attacked),
        )

    with pytest.raises(
        authority.V075ConstructionAccountingSchemaV2Violation
    ):
        authority.materialize_v075_construction_accounting_schema_v2(
            upstream=SimpleNamespace(
                **upstream.to_document(),
            ),
            foundation_bytes=foundation.canonical_bytes,
        )


def test_registered_schema_identity_drift_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, foundation = _produce(monkeypatch)
    upstream = (
        foundation_independent
        .verify_v075_construction_native_accounting_foundation_bytes_v2(
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    )
    monkeypatch.setattr(
        authority,
        "EXPECTED_COUNTER_REGISTRY_V2_ID",
        "f" * 64,
    )
    with pytest.raises(
        authority.V075ConstructionAccountingSchemaV2Violation
    ):
        authority.materialize_v075_construction_accounting_schema_v2(
            upstream=upstream,
            foundation_bytes=foundation.canonical_bytes,
        )


def test_closure_is_in_memory_only_and_production_gate_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inputs, _foundation, _upstream, closure = _freeze(monkeypatch)
    with pytest.raises(TypeError):
        pickle.dumps(closure)
    with pytest.raises(
        authority.V075ConstructionAccountingSchemaProductionV2NotReady
    ):
        authority.assert_v075_construction_accounting_schema_production_gate_v2(
            closure
        )
    with pytest.raises(
        authority.V075ConstructionAccountingSchemaV2Violation
    ):
        authority.assert_v075_construction_accounting_schema_production_gate_v2(
            SimpleNamespace(closure_id=closure.closure_id)
        )


def test_authority_has_no_observer_kernel_or_target_execution_imports() -> None:
    tree = ast.parse(inspect.getsource(authority))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert not any(
        fragment in name
        for name in imported
        for fragment in (
            "private_observer_boundary",
            "kernel",
            "production_campaign_runner",
            "registered_occurrence_worker",
        )
    )


def test_independent_replay_does_not_import_or_call_producer_or_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, foundation, _upstream, closure = _freeze(monkeypatch)

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("producer/core entry was called")

    monkeypatch.setattr(
        authority,
        "materialize_v075_construction_accounting_schema_v2",
        forbidden,
    )
    monkeypatch.setattr(
        accounting_core,
        "freeze_construction_accounting_schema_v2",
        forbidden,
    )
    verification = (
        independent.verify_v075_construction_accounting_schema_bytes_v2(
            closure_bytes=closure.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    )
    assert verification.closure_id == closure.closure_id

    source = inspect.getsource(independent)
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert not any(
        name.endswith("construction_accounting_v2")
        or name.endswith(
            "v075_construction_accounting_schema_closure_v2"
        )
        for name in imported
    )


def test_independent_replay_rejects_outer_rehash_overclaim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, foundation, _upstream, closure = _freeze(monkeypatch)
    attacked = copy.deepcopy(closure.to_document())
    attacked["all_path_native_accounting_complete"] = True
    attacked.pop("closure_id")
    from acfqp.phase3e_ids import (  # local import keeps test namespace small
        V075_CONSTRUCTION_ACCOUNTING_SCHEMA_CLOSURE_V2_DOMAIN,
        content_id,
    )

    attacked["closure_id"] = content_id(
        V075_CONSTRUCTION_ACCOUNTING_SCHEMA_CLOSURE_V2_DOMAIN,
        attacked,
    )
    with pytest.raises(
        independent.V075ConstructionAccountingSchemaIndependentV2Violation
    ):
        independent.verify_v075_construction_accounting_schema_bytes_v2(
            closure_bytes=canonical_json_bytes(attacked),
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )


def test_independent_verification_is_in_memory_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, foundation, _upstream, closure = _freeze(monkeypatch)
    verification = (
        independent.verify_v075_construction_accounting_schema_bytes_v2(
            closure_bytes=closure.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    )
    with pytest.raises(TypeError):
        pickle.dumps(verification)
    document = verification.to_document()
    assert document["live_counter_record_count"] == 0
    assert document["all_path_native_accounting_complete"] is False
    assert document["official_execution_allowed"] is False
    assert document["fresh_heldout_accessed"] is False
