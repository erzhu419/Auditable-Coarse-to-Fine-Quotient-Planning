from __future__ import annotations

import ast
import copy
import inspect
import pickle
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import (
    v075_construction_accounting_registry_successor_v3 as authority,
)
from acfqp import (
    v075_construction_accounting_schema_independent_verifier_v2
    as schema_independent,
)
from test_v075_construction_accounting_schema_closure_v2 import (
    _freeze as _freeze_v2,
)


def _freeze(
    monkeypatch: pytest.MonkeyPatch,
):
    inputs, foundation, _foundation_verification, schema = _freeze_v2(
        monkeypatch
    )
    upstream = (
        schema_independent
        .verify_v075_construction_accounting_schema_bytes_v2(
            closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    )
    successor = (
        authority
        .materialize_v075_construction_accounting_registry_successor_v3(
            upstream=upstream,
            schema_closure_bytes=schema.canonical_bytes,
        )
    )
    return inputs, foundation, schema, upstream, successor


def test_exact_successor_and_all_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inputs, _foundation, schema, upstream, successor = _freeze(
        monkeypatch
    )
    document = successor.to_document()
    assert document["upstream_closure_id"] == schema.closure_id
    assert document["upstream_verification_id"] == upstream.verification_id
    assert document["v2_prefix_leaf_count"] == 69
    assert document["v2_prefix_preserved_exactly"] is True
    assert document["v3_addition_count"] == 47
    assert document["v3_leaf_count"] == 116
    assert document["v3_operational_leaf_count"] == 99
    assert document["v3_required_leaf_count"] == 109
    assert document["registered_stage_count"] == 10
    assert document["projection_term_count"] == 99
    assert document["legacy_catalogue_entry_count"] == 95
    assert document["legacy_distinct_path_count"] == 87
    assert document["legacy_reinstrument_existing_count"] == 7
    assert document["legacy_decompose_native_count"] == 18
    assert document["legacy_derive_or_diagnose_count"] == 51
    assert document["legacy_new_operational_family_count"] == 11
    assert document[
        "open_incremental_acquisition_stage_registered"
    ] is True
    assert document[
        "open_checkpoint_replanning_stage_registered"
    ] is True
    assert document["legacy_summary_translation_allowed"] is False
    assert document["operation_site_instrumentation_complete"] is False
    assert document["derived_formula_registry_complete"] is False
    assert document[
        "hash_check_io_peak_granularity_profile_complete"
    ] is False
    assert document["stage_start_attestation_semantics_frozen"] is False
    assert document["stage_completion_attestation_semantics_frozen"] is False
    assert document["live_counter_record_count"] == 0
    assert document["work_vector_count"] == 0
    assert document["official_execution_allowed"] is False
    assert document["fresh_heldout_accessed"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert canonical_json_bytes(document) == successor.canonical_bytes
    with pytest.raises(TypeError):
        successor.counter_registry["leaves"][0]["owner"] = "forged"


def test_successor_ids_are_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    *_prefix, successor = _freeze(monkeypatch)
    document = successor.to_document()
    assert document["counter_registry_id"] == (
        authority.EXPECTED_COUNTER_REGISTRY_V3_ID
    )
    assert document["stage_profile_id"] == (
        authority.EXPECTED_STAGE_PROFILE_V3_ID
    )
    assert document["comparison_profile_id"] == (
        authority.EXPECTED_COMPARISON_PROFILE_V3_ID
    )
    assert document["actual_projection_profile_id"] == (
        authority.EXPECTED_ACTUAL_PROJECTION_PROFILE_V3_ID
    )
    assert document["legacy_migration_profile_id"] == (
        authority.EXPECTED_LEGACY_MIGRATION_PROFILE_V3_ID
    )


def test_signature_requires_verified_185_not_raw_secrets() -> None:
    assert tuple(
        inspect.signature(
            authority
            .materialize_v075_construction_accounting_registry_successor_v3
        ).parameters
    ) == ("upstream", "schema_closure_bytes")


def test_tampered_or_duck_typed_upstream_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inputs, _foundation, schema, upstream, _successor = _freeze(
        monkeypatch
    )
    attacked = copy.deepcopy(schema.to_document())
    attacked["legacy_custom_distinct_path_count"] = 86
    with pytest.raises(
        authority.V075ConstructionAccountingSuccessorV3Violation
    ):
        authority.materialize_v075_construction_accounting_registry_successor_v3(
            upstream=upstream,
            schema_closure_bytes=canonical_json_bytes(attacked),
        )
    with pytest.raises(
        authority.V075ConstructionAccountingSuccessorV3Violation
    ):
        authority.materialize_v075_construction_accounting_registry_successor_v3(
            upstream=SimpleNamespace(**upstream.to_document()),
            schema_closure_bytes=schema.canonical_bytes,
        )


def test_successor_is_in_memory_and_production_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    *_prefix, successor = _freeze(monkeypatch)
    with pytest.raises(TypeError):
        pickle.dumps(successor)
    with pytest.raises(
        authority.V075ConstructionAccountingSuccessorProductionV3NotReady
    ):
        authority.assert_v075_construction_accounting_successor_production_gate_v3(
            successor
        )
    with pytest.raises(
        authority.V075ConstructionAccountingSuccessorV3Violation
    ):
        authority.assert_v075_construction_accounting_successor_production_gate_v3(
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
        token in name
        for name in imported
        for token in forbidden
    )
