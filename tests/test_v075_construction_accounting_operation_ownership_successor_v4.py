from __future__ import annotations

import ast
import copy
import inspect
import pickle
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import (
    v075_construction_accounting_operation_ownership_successor_v4
    as authority,
)
from test_v075_construction_accounting_registry_successor_independent_verifier_v3 import (
    _verify as _verify_v3,
)


def _freeze_v4(monkeypatch: pytest.MonkeyPatch):
    inputs, foundation, schema, registry_successor, upstream = _verify_v3(
        monkeypatch
    )
    successor = (
        authority
        .materialize_v075_construction_accounting_operation_ownership_successor_v4(
            upstream=upstream,
            registry_successor_bytes=registry_successor.canonical_bytes,
        )
    )
    return inputs, foundation, schema, registry_successor, upstream, successor


def test_exact_operation_ownership_successor_and_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    *_prefix, successor = _freeze_v4(monkeypatch)
    document = successor.to_document()
    assert document["proposed_contract_version"] == "1.87.0"
    assert document["v3_prefix_leaf_count"] == 116
    assert document["v3_prefix_preserved_exactly"] is True
    assert document["v4_addition_count"] == 8
    assert document["v4_leaf_count"] == 124
    assert document["v4_operational_leaf_count"] == 106
    assert document["v4_required_leaf_count"] == 117
    assert document["registered_stage_count"] == 10
    assert document["projection_term_count"] == 106
    assert document[
        "build_projection_and_prior_binding_owned_by_build_stages"
    ] is True
    assert document[
        "closed_private_replay_owned_by_closed_reconciliation"
    ] is True
    assert document[
        "failed_audit_owned_no_full_replay_route_registered"
    ] is True
    assert document[
        "failed_audit_owned_no_full_replay_route_live_evidenced"
    ] is False
    assert document[
        "owned_root_cap_result_audit_host_full_replay_allowed"
    ] is False
    assert document["owned_root_cap_no_full_replay_runner_wired"] is False
    assert document["legacy_v2_portable_replay_default_unchanged"] is True
    assert document["operation_site_instrumentation_complete"] is False
    assert document["derived_formula_registry_complete"] is False
    assert document[
        "hash_check_io_peak_granularity_profile_complete"
    ] is False
    assert document["live_operation_event_count"] == 0
    assert document["live_counter_record_count"] == 0
    assert document["work_vector_count"] == 0
    assert document["official_execution_allowed"] is False
    assert document["fresh_heldout_accessed"] is False
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert canonical_json_bytes(document) == successor.canonical_bytes
    with pytest.raises(TypeError):
        successor.counter_registry["leaves"][0]["owner"] = "forged"


def test_operation_ownership_ids_and_upstream_bindings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inputs, _foundation, _schema, prior, upstream, successor = _freeze_v4(
        monkeypatch
    )
    document = successor.to_document()
    assert document["upstream_successor_id"] == prior.successor_id
    assert document["upstream_verification_id"] == upstream.verification_id
    assert document["counter_registry_id"] == (
        authority.EXPECTED_COUNTER_REGISTRY_V4_ID
    )
    assert document["stage_profile_id"] == (
        authority.EXPECTED_STAGE_PROFILE_V4_ID
    )
    assert document["comparison_profile_id"] == (
        authority.EXPECTED_COMPARISON_PROFILE_V4_ID
    )
    assert document["actual_projection_profile_id"] == (
        authority.EXPECTED_ACTUAL_PROJECTION_PROFILE_V4_ID
    )


def test_signature_requires_exact_verified_186() -> None:
    assert tuple(
        inspect.signature(
            authority
            .materialize_v075_construction_accounting_operation_ownership_successor_v4
        ).parameters
    ) == ("upstream", "registry_successor_bytes")


def test_tampered_or_duck_typed_upstream_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inputs, _foundation, _schema, prior, upstream, _successor = _freeze_v4(
        monkeypatch
    )
    attacked = copy.deepcopy(prior.to_document())
    attacked["v3_leaf_count"] = 115
    with pytest.raises(
        authority.V075ConstructionAccountingOperationOwnershipV4Violation
    ):
        authority.materialize_v075_construction_accounting_operation_ownership_successor_v4(
            upstream=upstream,
            registry_successor_bytes=canonical_json_bytes(attacked),
        )
    with pytest.raises(
        authority.V075ConstructionAccountingOperationOwnershipV4Violation
    ):
        authority.materialize_v075_construction_accounting_operation_ownership_successor_v4(
            upstream=SimpleNamespace(**upstream.to_document()),
            registry_successor_bytes=prior.canonical_bytes,
        )


def test_successor_is_in_memory_and_production_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    *_prefix, successor = _freeze_v4(monkeypatch)
    with pytest.raises(TypeError):
        pickle.dumps(successor)
    with pytest.raises(
        authority.V075ConstructionAccountingOperationOwnershipProductionV4NotReady
    ):
        authority.assert_v075_construction_accounting_operation_ownership_production_gate_v4(
            successor
        )
    with pytest.raises(
        authority.V075ConstructionAccountingOperationOwnershipV4Violation
    ):
        authority.assert_v075_construction_accounting_operation_ownership_production_gate_v4(
            SimpleNamespace(successor_id=successor.successor_id)
        )


def test_authority_has_no_live_execution_imports() -> None:
    tree = ast.parse(inspect.getsource(authority))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden = (
        "private_observer",
        "occurrence_runner",
        "production_campaign",
        "fresh_campaign",
        "ground",
        "kernel",
    )
    assert not any(
        token in name for name in imported for token in forbidden
    )
