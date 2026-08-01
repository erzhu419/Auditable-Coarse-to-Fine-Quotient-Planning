from __future__ import annotations

import ast
import copy
import inspect
import pickle
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import (
    v075_construction_accounting_known_owner_gap_successor_v5 as authority,
)
from acfqp import v075_k7_root_cap_operation_site_manifest_v2 as manifest_v2
from test_v075_construction_accounting_operation_ownership_independent_verifier_v4 import (
    _verify_v4,
)


def _freeze_v5(monkeypatch: pytest.MonkeyPatch):
    inputs, foundation, schema, registry_successor, prior, upstream = (
        _verify_v4(monkeypatch)
    )
    manifest = manifest_v2.official_k7_root_cap_operation_site_manifest_v2()
    manifest_bytes = canonical_json_bytes(manifest.to_document())
    successor = (
        authority
        .materialize_v075_construction_accounting_known_owner_gap_successor_v5(
            upstream=upstream,
            operation_ownership_successor_bytes=prior.canonical_bytes,
            strict_owner_manifest_id=manifest.manifest_id,
            strict_owner_manifest_bytes=manifest_bytes,
        )
    )
    return (
        inputs,
        foundation,
        schema,
        registry_successor,
        prior,
        upstream,
        successor,
    )


def test_exact_known_owner_gap_successor_and_all_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    *_prefix, successor = _freeze_v5(monkeypatch)
    document = successor.to_document()
    assert document["proposed_contract_version"] == "1.89.0"
    assert document["v4_prefix_leaf_count"] == 124
    assert document["v4_prefix_preserved_exactly"] is True
    assert document["v5_addition_count"] == 27
    assert document["v5_leaf_count"] == 151
    assert document["v5_operational_leaf_count"] == 133
    assert document["v5_required_leaf_count"] == 144
    assert document["registered_stage_count"] == 10
    assert document["projection_term_count"] == 133
    assert document["initial_batch_v2_family_count"] == 8
    assert document["initial_live_model_family_count"] == 2
    assert document["failed_dynamic_family_count"] == 6
    assert document["closed_batch_v2_family_count"] == 11
    assert document["owner_stage_family_buckets_nonoverlapping"] is True
    assert sum(
        document[field]
        for field in (
            "initial_batch_v2_family_count",
            "initial_live_model_family_count",
            "failed_dynamic_family_count",
            "closed_batch_v2_family_count",
        )
    ) == document["v5_addition_count"] == 27
    assert document[
        "greedy_allocation_event_boundary_schema_frozen"
    ] is True
    assert document["runtime_greedy_allocation_instrumented"] is False
    assert document[
        "support_descriptor_compile_distinct_from_typed_replay"
    ] is True
    assert document[
        "v4_owner_mismatch_paths_native_zero_on_registered_k7_path"
    ] is True
    assert document["minimal_known_owner_gap_closure_only"] is True
    assert document["operation_family_completeness_claimed"] is False
    assert document["runtime_owner_match_verified"] is False
    assert document["runtime_stage_attribution_verified"] is False
    assert document["operation_event_boundary_profile_complete"] is False
    assert document["strict_owner_manifest_id"] == (
        authority.EXPECTED_STRICT_OWNER_MANIFEST_V2_ID
    )
    assert document["strict_owner_v1_manifest_id"] == (
        authority.EXPECTED_STRICT_OWNER_MANIFEST_V1_ID
    )
    assert document[
        "strict_owner_manifest_v2_bound_from_canonical_bytes"
    ] is True
    for field in (
        "operation_site_instrumentation_complete",
        "operation_sites_wired",
        "derived_formula_registry_complete",
        "hash_check_io_peak_granularity_profile_complete",
        "typed_route_attempt_terminal_complete",
        "logical_occurrence_closure_complete",
        "campaign_closure_complete",
        "complete_bundle_verifier_complete",
        "counter_completeness_gate_passed",
        "accounting_gate_passed",
        "official_execution_allowed",
        "production_authorizing",
        "fresh_heldout_accessed",
        "scientific_endpoint_credit_allowed",
        "plan_certificate",
        "infeasibility_certificate",
    ):
        assert document[field] is False
    for field in (
        "live_operation_event_count",
        "live_counter_record_count",
        "work_vector_count",
        "comparison_vector_count",
        "actual_projection_proof_count",
    ):
        assert document[field] == 0
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert canonical_json_bytes(document) == successor.canonical_bytes
    with pytest.raises(TypeError):
        successor.counter_registry["leaves"][0]["owner"] = "forged"


def test_exact_ids_and_upstream_bindings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    *_prefix, prior, upstream, successor = _freeze_v5(monkeypatch)
    document = successor.to_document()
    assert document["upstream_successor_id"] == prior.successor_id
    assert document["upstream_verification_id"] == upstream.verification_id
    assert document["counter_registry_id"] == (
        authority.EXPECTED_COUNTER_REGISTRY_V5_ID
    )
    assert document["stage_profile_id"] == (
        authority.EXPECTED_STAGE_PROFILE_V5_ID
    )
    assert document["comparison_profile_id"] == (
        authority.EXPECTED_COMPARISON_PROFILE_V5_ID
    )
    assert document["actual_projection_profile_id"] == (
        authority.EXPECTED_ACTUAL_PROJECTION_PROFILE_V5_ID
    )
    assert document["strict_owner_manifest_id"] == (
        authority.EXPECTED_STRICT_OWNER_MANIFEST_V2_ID
    )


def test_signature_is_exact_and_tampering_or_duck_type_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    *_prefix, prior, upstream, _successor = _freeze_v5(monkeypatch)
    assert tuple(
        inspect.signature(
            authority
            .materialize_v075_construction_accounting_known_owner_gap_successor_v5
        ).parameters
    ) == (
        "upstream",
        "operation_ownership_successor_bytes",
        "strict_owner_manifest_id",
        "strict_owner_manifest_bytes",
    )
    manifest = manifest_v2.official_k7_root_cap_operation_site_manifest_v2()
    manifest_bytes = canonical_json_bytes(manifest.to_document())
    attacked = copy.deepcopy(prior.to_document())
    attacked["v4_leaf_count"] = 123
    with pytest.raises(
        authority.V075ConstructionAccountingKnownOwnerGapV5Violation
    ):
        authority.materialize_v075_construction_accounting_known_owner_gap_successor_v5(
            upstream=upstream,
            operation_ownership_successor_bytes=canonical_json_bytes(attacked),
            strict_owner_manifest_id=manifest.manifest_id,
            strict_owner_manifest_bytes=manifest_bytes,
        )
    with pytest.raises(
        authority.V075ConstructionAccountingKnownOwnerGapV5Violation
    ):
        authority.materialize_v075_construction_accounting_known_owner_gap_successor_v5(
            upstream=SimpleNamespace(**upstream.to_document()),
            operation_ownership_successor_bytes=prior.canonical_bytes,
            strict_owner_manifest_id=manifest.manifest_id,
            strict_owner_manifest_bytes=manifest_bytes,
        )


def test_strict_owner_manifest_tamper_transplant_and_missing_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    *_prefix, prior, upstream, _successor = _freeze_v5(monkeypatch)
    manifest = manifest_v2.official_k7_root_cap_operation_site_manifest_v2()
    attacked = copy.deepcopy(manifest.to_document())
    attacked["v1_direct_native_semantic_audit_passed"] = True
    with pytest.raises(
        authority.V075ConstructionAccountingKnownOwnerGapV5Violation
    ):
        authority.materialize_v075_construction_accounting_known_owner_gap_successor_v5(
            upstream=upstream,
            operation_ownership_successor_bytes=prior.canonical_bytes,
            strict_owner_manifest_id=manifest.manifest_id,
            strict_owner_manifest_bytes=canonical_json_bytes(attacked),
        )
    with pytest.raises(
        authority.V075ConstructionAccountingKnownOwnerGapV5Violation
    ):
        authority.materialize_v075_construction_accounting_known_owner_gap_successor_v5(
            upstream=upstream,
            operation_ownership_successor_bytes=prior.canonical_bytes,
            strict_owner_manifest_id="0" * 64,
            strict_owner_manifest_bytes=canonical_json_bytes(
                manifest.to_document()
            ),
        )
    with pytest.raises(TypeError):
        authority.materialize_v075_construction_accounting_known_owner_gap_successor_v5(
            upstream=upstream,
            operation_ownership_successor_bytes=prior.canonical_bytes,
        )


def test_successor_is_in_memory_and_production_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    *_prefix, successor = _freeze_v5(monkeypatch)
    with pytest.raises(TypeError):
        pickle.dumps(successor)
    with pytest.raises(
        authority.V075ConstructionAccountingKnownOwnerGapProductionV5NotReady
    ):
        authority.assert_v075_construction_accounting_known_owner_gap_production_gate_v5(
            successor
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
