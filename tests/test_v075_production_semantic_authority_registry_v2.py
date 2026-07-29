from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_production_semantic_authority_registry_v2 as semantic


def _registry() -> semantic.V075ProductionSemanticAuthorityRegistryV2:
    return semantic.freeze_v075_production_semantic_authority_registry_v2()


def test_v2_freezes_complete_unique_acyclic_production_role_graph() -> None:
    registry = _registry()

    assert tuple(item.role for item in registry.role_specs) == tuple(
        semantic.V075ProductionSemanticRoleV2
    )
    assert len(registry.role_specs) == 23
    assert len({item.spec_id for item in registry.role_specs}) == 23
    assert len(
        {
            domain
            for item in registry.role_specs
            for domain in item.artifact_domains
        }
    ) == sum(len(item.artifact_domains) for item in registry.role_specs)
    assert len(
        {
            schema
            for item in registry.role_specs
            for schema in item.artifact_schemas
        }
    ) == sum(len(item.artifact_schemas) for item in registry.role_specs)
    for item in registry.role_specs:
        document = item.to_document()
        assert document["semantic_verifier_module"].endswith(
            "v075_production_semantic_authority_registry_v2"
        )
        assert document["verifier_function"].startswith("verify_v075_")
        assert document["implementation_repository_path"].startswith(
            "src/acfqp/v075_"
        )
        assert (
            document["implementation_blob_binding"]
            == "MANIFEST_SHA256_REQUIRED"
        )
        assert document["caller_self_attestation_allowed"] is False
        assert (
            document["artifact_semantic_attestation_allowed"] is False
        )
        assert (
            document["verifier_scope"]
            == "STATIC_IMPLEMENTATION_SURFACE_ONLY"
        )


def test_current_required_surfaces_close_but_v2_preopen_blocks_campaign() -> None:
    registry = _registry()
    audit = (
        semantic.verify_v075_production_semantic_authority_registry_v2(
            registry
        )
    )

    assert audit.registry_id == registry.registry_id
    assert audit.verification_id == audit.audit_id
    assert audit.static_dependency_closure_valid is True
    assert audit.all_required_surfaces_ready is True
    assert audit.preopen_v2_migration_ready is False
    assert "PREOPEN_V2_MIGRATION_NOT_READY" in audit.blockers
    assert audit.production_semantic_chain_ready is False
    runner = audit.role_records[-1]
    if runner.module_exists:
        assert runner.status is semantic.V075StaticRoleReadinessV2.READY
        assert audit.runner_ready is True
    else:
        assert (
            runner.status
            is semantic.V075StaticRoleReadinessV2
            .OPTIONAL_NOT_READY_MODULE_ABSENT
        )
        assert audit.runner_ready is False

    document = audit.to_document()
    assert document["target_opened"] is False
    assert document["private_material_imported"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["artifact_semantic_attestation_allowed"] is False
    assert document["role_specific_artifact_replay_still_required"] is True


def test_serialized_domains_are_declared_and_signer_is_explicitly_exempt(
) -> None:
    audit = semantic.verify_v075_production_semantic_authority_registry_v2()
    records = {item.role: item for item in audit.role_records}

    for spec, record in zip(
        _registry().role_specs,
        audit.role_records,
        strict=True,
    ):
        if spec.serialized_artifact_role and record.module_exists:
            assert record.artifact_declarations_verified is True
            assert record.artifact_declaration_exempt is False
            assert record.missing_artifact_declarations == ()
    signer_spec = _registry().role_specs[
        list(semantic.V075ProductionSemanticRoleV2).index(
            semantic.V075ProductionSemanticRoleV2.PRIVATE_SIGNER_RUNTIME
        )
    ]
    signer = records[
        semantic.V075ProductionSemanticRoleV2.PRIVATE_SIGNER_RUNTIME
    ]
    assert signer_spec.artifact_schemas == ()
    assert signer_spec.artifact_domains == ()
    assert signer_spec.artifact_schema is None
    assert signer_spec.artifact_domain is None
    assert signer.artifact_declaration_exempt is True
    assert signer.artifact_declarations_verified is True


def test_legacy_aggregate_flags_are_diagnostic_not_current_authority() -> None:
    audit = semantic.verify_v075_production_semantic_authority_registry_v2()
    records = {item.role: item for item in audit.role_records}

    for role in (
        semantic.V075ProductionSemanticRoleV2.MULTISTAGE_LIFECYCLE,
        semantic.V075ProductionSemanticRoleV2.BATCH_NATIVE_BACKEND,
        semantic.V075ProductionSemanticRoleV2.BATCH_NATIVE_PLANNER,
        semantic.V075ProductionSemanticRoleV2.BATCH_NATIVE_TOTAL_LIFT,
    ):
        record = records[role]
        assert record.status is semantic.V075StaticRoleReadinessV2.READY
        assert record.legacy_aggregate_facts
        assert all(value is False for _name, value in record.legacy_aggregate_facts)
        assert (
            record.to_document()[
                "legacy_aggregate_facts_are_readiness_authority"
            ]
            is False
        )


def test_missing_role_is_rejected_by_exact_registry_replay() -> None:
    canonical = _registry()
    incomplete = semantic.V075ProductionSemanticAuthorityRegistryV2(
        canonical.role_specs[:-1]
    )

    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityV2InvariantViolation,
        match="exact frozen",
    ):
        semantic.verify_v075_production_semantic_authority_registry_v2(
            incomplete
        )


def test_dependency_cycle_or_forward_edge_is_rejected() -> None:
    specs = list(semantic.canonical_v075_production_semantic_role_specs_v2())
    specs[0] = replace(
        specs[0],
        prerequisite_roles=(
            semantic.V075ProductionSemanticRoleV2
            .COMPLETE_BUNDLE_ENDPOINT,
        ),
    )

    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityV2InvariantViolation,
        match="cyclic or forward",
    ):
        semantic.V075ProductionSemanticAuthorityRegistryV2(tuple(specs))


@pytest.mark.parametrize("field", ["artifact_domains", "artifact_schemas"])
def test_cross_role_schema_or_domain_collision_is_rejected(
    field: str,
) -> None:
    specs = list(semantic.canonical_v075_production_semantic_role_specs_v2())
    collision = getattr(specs[0], field)[0]
    replacement = list(getattr(specs[1], field))
    replacement[0] = collision
    specs[1] = replace(specs[1], **{field: tuple(replacement)})

    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityV2InvariantViolation,
        match="collision",
    ):
        semantic.V075ProductionSemanticAuthorityRegistryV2(tuple(specs))


def test_unknown_verifier_and_producer_self_attestation_are_rejected() -> None:
    canonical = list(
        semantic.canonical_v075_production_semantic_role_specs_v2()
    )
    unknown = list(canonical)
    unknown[0] = replace(
        unknown[0],
        semantic_verifier_id="verify_v075_unknown_semantic_surface_v2",
    )
    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityV2InvariantViolation,
        match="unknown verifier",
    ):
        semantic.V075ProductionSemanticAuthorityRegistryV2(tuple(unknown))

    self_attested = list(canonical)
    self_attested[0] = replace(
        self_attested[0],
        semantic_verifier_module=self_attested[0].producer_module,
    )
    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityV2InvariantViolation,
        match="self-attestation",
    ):
        semantic.V075ProductionSemanticAuthorityRegistryV2(
            tuple(self_attested)
        )


def test_stale_or_caller_edited_readiness_document_is_rejected() -> None:
    audit = semantic.verify_v075_production_semantic_authority_registry_v2()
    assert (
        semantic.load_and_verify_v075_production_semantic_readiness_v2(
            audit.to_canonical_bytes()
        )
        == audit
    )
    forged = audit.to_document()
    forged["production_semantic_chain_ready"] = True
    forged["blockers"] = []

    with pytest.raises(
        semantic.V075ProductionSemanticAuthorityV2InvariantViolation,
        match="stale, forged, or self-attested",
    ):
        semantic.load_and_verify_v075_production_semantic_readiness_v2(
            canonical_json_bytes(forged)
        )


def test_static_verification_never_imports_producer_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = __import__

    def guarded_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name.startswith("acfqp.v075_"):
            raise AssertionError(f"producer import attempted: {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", guarded_import)
    audit = semantic.verify_v075_production_semantic_authority_registry_v2()

    assert audit.static_dependency_closure_valid is True
    assert all(
        item.to_document()["source_imported"] is False
        for item in audit.role_records
    )


def test_literal_safety_lock_drift_is_detected_without_import(
    tmp_path: Path,
) -> None:
    package_root = tmp_path / "acfqp"
    package_root.mkdir()
    for spec in _registry().role_specs:
        source = (
            Path(semantic.__file__).resolve().parent
            / f"{spec.producer_module.split('.', 1)[1]}.py"
        )
        destination = package_root / source.name
        if source.is_file():
            destination.symlink_to(source)

    endpoint = package_root / "v075_production_complete_bundle_endpoint_v1.py"
    endpoint.unlink()
    endpoint.write_text(
        "\n".join(
            (
                "PRODUCTION_COMPLETE_BUNDLE_PROTOCOL_STATUS = 'STALE'",
                "PRODUCTION_ENDPOINT_VERIFICATION_ALLOWED = True",
                "TARGET_EXECUTION_OPENED = False",
                "PRIVATE_TARGET_INPUTS_ACCEPTED = False",
                "CALLER_VERDICTS_ACCEPTED = False",
                "CALLER_TOTALS_ACCEPTED = False",
                "OFFICIAL_EXECUTION_ALLOWED = False",
                "OFFICIAL_SCALAR_COST = None",
                "OFFICIAL_N_BREAK_EVEN = None",
                "WORKLOAD_ECONOMICS_GATE_STATUS = 'NOT_RUN'",
                "COUNTER_COMPLETENESS_GATE_STATUS = 'NOT_RUN'",
                (
                    "def verify_v075_production_complete_bundle_"
                    "endpoint_v1(): pass"
                ),
            )
        ),
        encoding="utf-8",
    )

    audit = (
        semantic.verify_v075_production_semantic_authority_registry_v2(
            package_root=package_root
        )
    )
    endpoint_record = {
        item.role: item for item in audit.role_records
    }[semantic.V075ProductionSemanticRoleV2.COMPLETE_BUNDLE_ENDPOINT]
    assert (
        endpoint_record.status
        is semantic.V075StaticRoleReadinessV2.REQUIRED_NOT_READY
    )
    assert endpoint_record.mismatched_constants == (
        "PRODUCTION_COMPLETE_BUNDLE_PROTOCOL_STATUS",
    )
    assert audit.all_required_surfaces_ready is False


def test_registry_document_is_canonical_and_does_not_claim_economics() -> None:
    document = _registry().to_document()
    roundtrip = json.loads(
        canonical_json_bytes(document).decode("utf-8")
    )

    assert roundtrip == document
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
