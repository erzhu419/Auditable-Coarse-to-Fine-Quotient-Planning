from __future__ import annotations

import ast
import copy
import inspect
import pickle

import pytest

from acfqp.phase3e_ids import (
    CONSTRUCTION_COMPARISON_PROFILE_V5_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V5_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V5_DOMAIN,
    V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_SUCCESSOR_V5_DOMAIN,
    canonical_json_bytes,
    content_id,
)
from acfqp import (
    v075_construction_accounting_known_owner_gap_independent_verifier_v5
    as verifier,
)
from acfqp import v075_k7_root_cap_operation_site_manifest_v2 as manifest_v2
from test_v075_construction_accounting_known_owner_gap_successor_v5 import (
    _freeze_v5,
)


def _verify_v5(monkeypatch: pytest.MonkeyPatch):
    (
        inputs,
        foundation,
        schema,
        registry_successor,
        operation_successor,
        _upstream,
        successor,
    ) = _freeze_v5(monkeypatch)
    manifest = manifest_v2.official_k7_root_cap_operation_site_manifest_v2()
    manifest_bytes = canonical_json_bytes(manifest.to_document())
    verification = (
        verifier
        .verify_v075_construction_accounting_known_owner_gap_bytes_v5(
            successor_bytes=successor.canonical_bytes,
            operation_ownership_successor_bytes=(
                operation_successor.canonical_bytes
            ),
            strict_owner_manifest_id=manifest.manifest_id,
            strict_owner_manifest_bytes=manifest_bytes,
            registry_successor_bytes=registry_successor.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    )
    return (
        inputs,
        foundation,
        schema,
        registry_successor,
        operation_successor,
        successor,
        verification,
    )


def _rehash_embedded(
    document: dict,
    *,
    id_field: str,
    domain: str,
) -> str:
    payload = copy.deepcopy(document)
    payload.pop(id_field)
    selected = content_id(domain, payload)
    document[id_field] = selected
    return selected


def _rehash_outer(document: dict) -> bytes:
    payload = copy.deepcopy(document)
    payload.pop("successor_id")
    document["successor_id"] = content_id(
        V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_SUCCESSOR_V5_DOMAIN,
        payload,
    )
    return canonical_json_bytes(document)


def _reject_attacked_successor(
    *,
    attacked: dict,
    inputs: dict,
    foundation,
    schema,
    registry_successor,
    operation_successor,
) -> None:
    manifest = manifest_v2.official_k7_root_cap_operation_site_manifest_v2()
    with pytest.raises(
        verifier.V075ConstructionAccountingKnownOwnerGapIndependentV5Violation
    ):
        verifier.verify_v075_construction_accounting_known_owner_gap_bytes_v5(
            successor_bytes=_rehash_outer(attacked),
            operation_ownership_successor_bytes=(
                operation_successor.canonical_bytes
            ),
            strict_owner_manifest_id=manifest.manifest_id,
            strict_owner_manifest_bytes=canonical_json_bytes(
                manifest.to_document()
            ),
            registry_successor_bytes=registry_successor.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )


def test_independent_v5_verification_and_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    *_prefix, successor, verification = _verify_v5(monkeypatch)
    document = verification.to_document()
    assert document["successor_id"] == successor.successor_id
    assert document["counter_registry_id"] == (
        verifier.EXPECTED_COUNTER_REGISTRY_V5_ID
    )
    assert document["stage_profile_id"] == (
        verifier.EXPECTED_STAGE_PROFILE_V5_ID
    )
    assert document["comparison_profile_id"] == (
        verifier.EXPECTED_COMPARISON_PROFILE_V5_ID
    )
    assert document["actual_projection_profile_id"] == (
        verifier.EXPECTED_ACTUAL_PROJECTION_PROFILE_V5_ID
    )
    assert document["producer_imported"] is False
    assert document["producer_entry_called"] is False
    assert document["construction_accounting_v5_core_imported"] is False
    assert document[
        "construction_accounting_v5_core_entry_called"
    ] is False
    assert document["upstream_contract_187_replayed_exactly"] is True
    assert document[
        "v4_prefix_compared_from_verified_upstream_bytes"
    ] is True
    assert document[
        "twenty_seven_additions_checked_independently"
    ] is True
    assert document[
        "greedy_allocation_boundary_schema_checked_independently"
    ] is True
    assert document[
        "descriptor_compile_owner_schema_checked_independently"
    ] is True
    assert document["stage_assignment_schema_checked_independently"] is True
    assert document["runtime_owner_match_verified"] is False
    assert document["runtime_stage_attribution_verified"] is False
    assert document["operation_event_boundary_profile_complete"] is False
    assert document["strict_owner_manifest_id"] == (
        verifier.EXPECTED_STRICT_OWNER_MANIFEST_V2_ID
    )
    assert document["strict_owner_manifest_rehashed_independently"] is True
    assert document["strict_owner_site_audits_rehashed_independently"] is True
    assert document["projection_133_terms_checked_independently"] is True
    assert document["minimal_known_owner_gap_closure_only"] is True
    assert document["operation_family_completeness_claimed"] is False
    assert document["operation_site_instrumentation_complete"] is False
    assert document["official_execution_allowed"] is False
    assert document["fresh_heldout_accessed"] is False
    with pytest.raises(TypeError):
        pickle.dumps(verification)


@pytest.mark.parametrize(
    ("section", "mutator"),
    (
        (
            "counter_registry",
            lambda value: value["leaves"][-1].__setitem__("unit", "forged"),
        ),
        (
            "stage_profile",
            lambda value: value["rules"][0]["allowed_nonzero_paths"].append(
                "forged.path"
            ),
        ),
        (
            "comparison_profile",
            lambda value: value["terms"][-1].__setitem__("coefficient", 2),
        ),
        (
            "actual_projection_profile",
            lambda value: value["terms"][-1].__setitem__(
                "target_axis", "read_bytes"
            ),
        ),
    ),
)
def test_embedded_v5_profile_tampering_fails(
    monkeypatch: pytest.MonkeyPatch,
    section: str,
    mutator,
) -> None:
    (
        inputs,
        foundation,
        schema,
        registry_successor,
        operation_successor,
        successor,
        _verification,
    ) = _verify_v5(monkeypatch)
    manifest = manifest_v2.official_k7_root_cap_operation_site_manifest_v2()
    attacked = copy.deepcopy(successor.to_document())
    mutator(attacked[section])
    with pytest.raises(
        verifier.V075ConstructionAccountingKnownOwnerGapIndependentV5Violation
    ):
        verifier.verify_v075_construction_accounting_known_owner_gap_bytes_v5(
            successor_bytes=canonical_json_bytes(attacked),
            operation_ownership_successor_bytes=(
                operation_successor.canonical_bytes
            ),
            strict_owner_manifest_id=manifest.manifest_id,
            strict_owner_manifest_bytes=canonical_json_bytes(
                manifest.to_document()
            ),
            registry_successor_bytes=registry_successor.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )


def test_outer_lock_and_upstream_prefix_tampering_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        inputs,
        foundation,
        schema,
        registry_successor,
        operation_successor,
        successor,
        _verification,
    ) = _verify_v5(monkeypatch)
    manifest = manifest_v2.official_k7_root_cap_operation_site_manifest_v2()
    manifest_bytes = canonical_json_bytes(manifest.to_document())
    attacked = copy.deepcopy(successor.to_document())
    attacked["official_execution_allowed"] = True
    with pytest.raises(
        verifier.V075ConstructionAccountingKnownOwnerGapIndependentV5Violation
    ):
        verifier.verify_v075_construction_accounting_known_owner_gap_bytes_v5(
            successor_bytes=canonical_json_bytes(attacked),
            operation_ownership_successor_bytes=(
                operation_successor.canonical_bytes
            ),
            strict_owner_manifest_id=manifest.manifest_id,
            strict_owner_manifest_bytes=manifest_bytes,
            registry_successor_bytes=registry_successor.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )

    attacked_upstream = copy.deepcopy(operation_successor.to_document())
    attacked_upstream["counter_registry"]["leaves"][0]["unit"] = "forged"
    with pytest.raises(
        verifier.V075ConstructionAccountingKnownOwnerGapIndependentV5Violation
    ):
        verifier.verify_v075_construction_accounting_known_owner_gap_bytes_v5(
            successor_bytes=successor.canonical_bytes,
            operation_ownership_successor_bytes=canonical_json_bytes(
                attacked_upstream
            ),
            strict_owner_manifest_id=manifest.manifest_id,
            strict_owner_manifest_bytes=manifest_bytes,
            registry_successor_bytes=registry_successor.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )


def test_cross_role_and_cross_version_profile_transplants_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        inputs,
        foundation,
        schema,
        registry_successor,
        operation_successor,
        successor,
        _verification,
    ) = _verify_v5(monkeypatch)

    cross_role = copy.deepcopy(successor.to_document())
    cross_role["actual_projection_profile"] = copy.deepcopy(
        cross_role["comparison_profile"]
    )
    cross_role["actual_projection_profile_id"] = cross_role[
        "comparison_profile_id"
    ]
    _reject_attacked_successor(
        attacked=cross_role,
        inputs=inputs,
        foundation=foundation,
        schema=schema,
        registry_successor=registry_successor,
        operation_successor=operation_successor,
    )

    cross_version = copy.deepcopy(successor.to_document())
    v4_registry = copy.deepcopy(
        operation_successor.to_document()["counter_registry"]
    )
    cross_version["counter_registry"] = v4_registry
    cross_version["counter_registry_id"] = v4_registry[
        "counter_registry_id"
    ]
    _reject_attacked_successor(
        attacked=cross_version,
        inputs=inputs,
        foundation=foundation,
        schema=schema,
        registry_successor=registry_successor,
        operation_successor=operation_successor,
    )


def test_unknown_top_level_field_fails_after_outer_rehash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        inputs,
        foundation,
        schema,
        registry_successor,
        operation_successor,
        successor,
        _verification,
    ) = _verify_v5(monkeypatch)
    attacked = copy.deepcopy(successor.to_document())
    attacked["unknown_top_level_field"] = "forged"
    _reject_attacked_successor(
        attacked=attacked,
        inputs=inputs,
        foundation=foundation,
        schema=schema,
        registry_successor=registry_successor,
        operation_successor=operation_successor,
    )


@pytest.mark.parametrize(
    ("section", "id_field", "domain", "mutator"),
    (
        (
            "counter_registry",
            "counter_registry_id",
            CONSTRUCTION_COUNTER_REGISTRY_V5_DOMAIN,
            lambda value: value["leaves"][-1].__setitem__(
                "unknown_leaf_field", "forged"
            ),
        ),
        (
            "stage_profile",
            "stage_profile_id",
            CONSTRUCTION_STAGE_PROFILE_V5_DOMAIN,
            lambda value: value["rules"][-1].__setitem__(
                "unknown_rule_field", "forged"
            ),
        ),
        (
            "comparison_profile",
            "comparison_profile_id",
            CONSTRUCTION_COMPARISON_PROFILE_V5_DOMAIN,
            lambda value: value["terms"][-1].__setitem__(
                "unknown_term_field", "forged"
            ),
        ),
    ),
)
def test_unknown_embedded_fields_fail_after_profile_and_outer_rehash(
    monkeypatch: pytest.MonkeyPatch,
    section: str,
    id_field: str,
    domain: str,
    mutator,
) -> None:
    (
        inputs,
        foundation,
        schema,
        registry_successor,
        operation_successor,
        successor,
        _verification,
    ) = _verify_v5(monkeypatch)
    attacked = copy.deepcopy(successor.to_document())
    mutator(attacked[section])
    attacked[id_field] = _rehash_embedded(
        attacked[section], id_field=id_field, domain=domain
    )
    _reject_attacked_successor(
        attacked=attacked,
        inputs=inputs,
        foundation=foundation,
        schema=schema,
        registry_successor=registry_successor,
        operation_successor=operation_successor,
    )


def test_strict_owner_manifest_tamper_transplant_and_missing_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        inputs,
        foundation,
        schema,
        registry_successor,
        operation_successor,
        successor,
        _verification,
    ) = _verify_v5(monkeypatch)
    manifest = manifest_v2.official_k7_root_cap_operation_site_manifest_v2()
    manifest_document = manifest.to_document()
    attacked = copy.deepcopy(manifest_document)
    attacked["sites"][0]["site_audit_id"] = "0" * 64
    with pytest.raises(
        verifier.V075ConstructionAccountingKnownOwnerGapIndependentV5Violation
    ):
        verifier.verify_v075_construction_accounting_known_owner_gap_bytes_v5(
            successor_bytes=successor.canonical_bytes,
            operation_ownership_successor_bytes=(
                operation_successor.canonical_bytes
            ),
            strict_owner_manifest_id=manifest.manifest_id,
            strict_owner_manifest_bytes=canonical_json_bytes(attacked),
            registry_successor_bytes=registry_successor.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    with pytest.raises(
        verifier.V075ConstructionAccountingKnownOwnerGapIndependentV5Violation
    ):
        verifier.verify_v075_construction_accounting_known_owner_gap_bytes_v5(
            successor_bytes=successor.canonical_bytes,
            operation_ownership_successor_bytes=(
                operation_successor.canonical_bytes
            ),
            strict_owner_manifest_id="0" * 64,
            strict_owner_manifest_bytes=canonical_json_bytes(
                manifest_document
            ),
            registry_successor_bytes=registry_successor.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    with pytest.raises(TypeError):
        verifier.verify_v075_construction_accounting_known_owner_gap_bytes_v5(
            successor_bytes=successor.canonical_bytes,
            operation_ownership_successor_bytes=(
                operation_successor.canonical_bytes
            ),
            registry_successor_bytes=registry_successor.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )


def test_verifier_signature_and_import_independence() -> None:
    assert tuple(
        inspect.signature(
            verifier
            .verify_v075_construction_accounting_known_owner_gap_bytes_v5
        ).parameters
    ) == (
        "successor_bytes",
        "operation_ownership_successor_bytes",
        "strict_owner_manifest_id",
        "strict_owner_manifest_bytes",
        "registry_successor_bytes",
        "schema_closure_bytes",
        "foundation_bytes",
        "source_code_provenance_bytes",
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
        "private_generation_seed",
        "private_salt",
    )
    tree = ast.parse(inspect.getsource(verifier))
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
    assert not any(
        name.endswith("construction_accounting_registry_v5")
        or name.endswith(
            "v075_construction_accounting_known_owner_gap_successor_v5"
        )
        or name.endswith("v075_k7_root_cap_operation_site_manifest_v2")
        for name in imported
    )
    source = inspect.getsource(verifier)
    assert "official_counter_registry_v5" not in source
    assert (
        "materialize_v075_construction_accounting_known_owner_gap_successor_v5"
        not in source
    )
