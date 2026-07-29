from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
from pathlib import Path

import pytest

from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_confirmatory_execution_manifest_v1 as manifest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _temporary_spec(path: str) -> manifest.ComponentRoleSpecV1:
    return manifest.ComponentRoleSpecV1(
        "temporary test component",
        path,
        "temporary-test-protocol-v1",
        manifest.TYPED_NOT_APPLICABLE,
    )


def test_ordered_component_roles_and_binding_profile_are_frozen() -> None:
    expected_roles = (
        "normative specification",
        "preregistration authority",
        "verified source-archive builder and independent verifier",
        "portable-feature consensus authority",
        "target preauthorization selector and selector verifier",
        (
            "registered observer, raw-commitment replay, and "
            "support-epoch-chain verifier"
        ),
        "partial-support confidence authority",
        (
            "public legal-action catalogue and novel-child "
            "cardinality authority"
        ),
        "cold H2 closure and relational/ground model builders",
        "incremental materializer and fresh round-2 authority",
        "exact lazy H2 planner and independent proof verifier",
        "matched direct-ground baseline",
        "independent exact ground evaluator",
        "five-arm confirmatory campaign runner",
        "standalone complete-bundle and endpoint verifier",
        "counter/access-log/accepted-draw reconciliation authority",
        "confirmatory tests and the exact test-command manifest",
        "runtime/dependency lock and interpreter build identity",
    )
    assert manifest.COMPONENT_ROLE_ORDER == expected_roles
    assert tuple(
        item.component_role for item in manifest.COMPONENT_ROLE_SPECS
    ) == expected_roles
    assert len(expected_roles) == len(set(expected_roles)) == 18

    readiness = (
        manifest.inspect_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT
        )
    )
    bindings = readiness.global_bindings
    contexts = prereg.registered_heldout_public_contexts_v2()
    environment = prereg.frozen_heldout_environment_manifest_v1()
    assert bindings["confirmatory_family_generation"] == (
        prereg.CONFIRMATORY_FAMILY_GENERATION
    )
    assert bindings["context_ids"] == [
        item.context_id for item in contexts
    ]
    assert bindings["law_ids"] == [
        item.law_id for item in environment.laws
    ]
    assert bindings["environment_manifest_id"] == environment.manifest_id
    assert bindings[
        "source_reconstruction_recipe_repository_path"
    ] == manifest.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
    assert bindings["arm_order"] == list(prereg.ARM_ORDER)
    assert bindings["terminal_codes"] == list(prereg.TERMINAL_CODES)
    assert bindings["repository_url"] == manifest.REPOSITORY_URL
    assert bindings["target_branch"] == "main"
    assert bindings["component_tree_digest"] == (
        readiness.component_registry.component_tree_digest
    )
    assert bindings["exact_test_command"] == list(
        manifest.EXACT_TEST_COMMAND
    )
    assert bindings["deterministic_environment_settings"] == [
        {"name": name, "value": value}
        for name, value in manifest.DETERMINISTIC_ENVIRONMENT_SETTINGS
    ]
    assert all(
        type(bindings[name]) is str and len(bindings[name]) == 64
        for name in (
            "test_command_manifest_id",
            "runtime_dependency_lock_id",
            "interpreter_build_identity_id",
        )
    )


def test_actual_component_bytes_derive_hashes_and_replay() -> None:
    readiness = (
        manifest.inspect_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT
        )
    )
    assert readiness.component_registry.records
    spec_by_role = {
        item.component_role: item for item in manifest.COMPONENT_ROLE_SPECS
    }
    for record in readiness.component_registry.records:
        data = (
            REPOSITORY_ROOT / record.repository_relative_path
        ).read_bytes()
        assert record.sha256_file_bytes == _sha(data)
        assert record.file_byte_count == len(data)
        assert (
            manifest.verify_component_record_v1(
                REPOSITORY_ROOT,
                spec_by_role[record.component_role],
                record,
            )
            == record
        )
    assert (
        manifest.verify_component_registry_snapshot_v1(
            REPOSITORY_ROOT,
            readiness.component_registry,
        )
        == readiness.component_registry
    )


def test_execution_dependency_closure_binds_all_source_tests_and_exact_scripts() -> None:
    registry = manifest.freeze_internal_component_registry_v1(
        REPOSITORY_ROOT
    )
    role_paths = {
        item.repository_relative_path for item in registry.records
    }
    dependency_by_path = {
        item.repository_relative_path: item
        for item in registry.execution_dependency_records
    }
    bound_paths = role_paths | set(dependency_by_path)
    assert {
        item.relative_to(REPOSITORY_ROOT).as_posix()
        for item in (REPOSITORY_ROOT / "src").rglob("*.py")
    }.issubset(bound_paths)
    assert {
        item.relative_to(REPOSITORY_ROOT).as_posix()
        for item in (REPOSITORY_ROOT / "tests").rglob("*.py")
    }.issubset(bound_paths)
    assert set(manifest.execution_env.IMPLEMENTATION_PATHS).issubset(
        bound_paths
    )
    assert set(manifest.PRODUCTION_ENTRYPOINT_PATHS).issubset(bound_paths)
    assert manifest.MANIFEST_AUTHORITY_PATH in bound_paths

    relative_dynamic = dependency_by_path[
        "src/acfqp/abstraction/behavioral.py"
    ]
    assert (
        "LOCAL_IMPORT:src/acfqp/abstraction/__init__.py"
        in relative_dynamic.provenance
    )
    development_path = manifest.DEVELOPMENT_SYNTHETIC_MODULE_PATH
    assert development_path not in role_paths
    assert development_path in dependency_by_path
    assert any(
        item.startswith("LOCAL_IMPORT:tests/")
        for item in dependency_by_path[development_path].provenance
    )


def test_execution_dependency_records_reject_mutation_removal_and_reorder() -> None:
    registry = manifest.freeze_internal_component_registry_v1(
        REPOSITORY_ROOT
    )
    assert len(registry.execution_dependency_records) >= 2
    first = registry.execution_dependency_records[0]
    changed_digest = ("0" if first.sha256_file_bytes[0] != "0" else "1") + (
        first.sha256_file_bytes[1:]
    )
    forged = replace(first, sha256_file_bytes=changed_digest)
    changed = replace(
        registry,
        execution_dependency_records=(
            forged,
            *registry.execution_dependency_records[1:],
        ),
    )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="differs from current repository tree",
    ):
        manifest.verify_component_registry_snapshot_v1(
            REPOSITORY_ROOT,
            changed,
        )
    removed = replace(
        registry,
        execution_dependency_records=(
            registry.execution_dependency_records[1:]
        ),
    )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="differs from current repository tree",
    ):
        manifest.verify_component_registry_snapshot_v1(
            REPOSITORY_ROOT,
            removed,
        )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="dependency closure is reordered",
    ):
        replace(
            registry,
            execution_dependency_records=tuple(
                reversed(registry.execution_dependency_records)
            ),
        )


def test_conservative_closure_covers_variable_import_and_rejects_missing_static_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    for path in ("src/acfqp", "tests", "scripts"):
        (root / path).mkdir(parents=True)
    (root / "src/acfqp/__init__.py").write_text("", encoding="utf-8")
    driver = root / "src/acfqp/driver.py"
    driver.write_text(
        "import importlib\n"
        "module_name = 'acfqp.variable_target'\n"
        "importlib.import_module(module_name)\n",
        encoding="utf-8",
    )
    (root / "src/acfqp/variable_target.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (root / "tests/test_driver.py").write_text(
        "def test_placeholder():\n    assert True\n",
        encoding="utf-8",
    )
    (root / "scripts/runner.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(
        manifest,
        "MANIFEST_AUTHORITY_PATH",
        "src/acfqp/driver.py",
    )
    monkeypatch.setattr(
        manifest.execution_env,
        "IMPLEMENTATION_PATHS",
        ("scripts/runner.py",),
    )
    monkeypatch.setattr(
        manifest,
        "PRODUCTION_ENTRYPOINT_PATHS",
        ("scripts/runner.py",),
    )
    closure = manifest.derive_execution_dependency_closure_v1(root, ())
    target = next(
        item
        for item in closure
        if item.repository_relative_path
        == "src/acfqp/variable_target.py"
    )
    assert "CONSERVATIVE_LOCAL_PYTHON_CLOSURE" in target.provenance

    driver.write_text("import acfqp.missing\n", encoding="utf-8")
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="unresolved local import acfqp.missing",
    ):
        manifest.derive_execution_dependency_closure_v1(root, ())


def test_role_reorder_missing_and_duplicate_attacks_fail_closed() -> None:
    registry = (
        manifest.inspect_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT
        ).component_registry
    )
    assert len(registry.records) >= 2
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="reordered, missing, or duplicated",
    ):
        replace(registry, records=tuple(reversed(registry.records)))
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="reordered, missing, or duplicated",
    ):
        replace(registry, records=registry.records[:-1])
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="reordered, missing, or duplicated",
    ):
        replace(
            registry,
            records=(*registry.records, registry.records[-1]),
        )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="reordered, missing, or duplicated",
    ):
        replace(
            registry,
            missing_roles=(
                registry.missing_roles[1:]
                if registry.missing_roles
                else (manifest.COMPONENT_ROLE_ORDER[-1],)
            ),
        )


def test_caller_hash_is_not_an_api_and_mutated_bytes_fail_replay(
    tmp_path: Path,
) -> None:
    parameters = inspect.signature(
        manifest.derive_component_record_v1
    ).parameters
    assert "sha256_file_bytes" not in parameters
    assert "digest" not in parameters

    root = tmp_path / "repo"
    root.mkdir()
    component = root / "component.py"
    component.write_bytes(b"first bytes\n")
    spec = _temporary_spec("component.py")
    with pytest.raises(TypeError):
        manifest.derive_component_record_v1(
            root,
            spec,
            sha256_file_bytes="0" * 64,  # type: ignore[call-arg]
        )
    record = manifest.derive_component_record_v1(root, spec)
    assert record.sha256_file_bytes == _sha(b"first bytes\n")
    component.write_bytes(b"changed bytes\n")
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="differs from current repository bytes",
    ):
        manifest.verify_component_record_v1(root, spec, record)
    replayed = manifest.derive_component_record_v1(root, spec)
    assert replayed.record_id != record.record_id
    assert replayed.sha256_file_bytes != record.sha256_file_bytes


def test_path_traversal_and_symlink_escape_are_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="traverses",
    ):
        _temporary_spec("../outside.py")
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="repo-relative",
    ):
        _temporary_spec(r"inside\\component.py")

    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_bytes(b"outside\n")
    inside = root / "inside"
    inside.mkdir()
    (inside / "component.py").symlink_to(outside)
    spec = _temporary_spec("inside/component.py")
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="symlink",
    ):
        manifest.derive_component_record_v1(root, spec)


def test_null_applicable_id_retired_id_and_development_module_are_rejected() -> None:
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="null or untyped",
    ):
        manifest.ComponentRecordV1(
            "temporary test component",
            "component.py",
            "a" * 64,
            1,
            "temporary-test-protocol-v1",
            None,  # type: ignore[arg-type]
        )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="retired development identity",
    ):
        manifest.ComponentRecordV1(
            "temporary test component",
            "component.py",
            "a" * 64,
            1,
            "temporary-test-protocol-v1",
            prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS[0],
        )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="development synthetic module",
    ):
        manifest.ComponentRoleSpecV1(
            "temporary test component",
            manifest.DEVELOPMENT_SYNTHETIC_MODULE_PATH,
            "temporary-test-protocol-v1",
            manifest.TYPED_NOT_APPLICABLE,
        )
    readiness = (
        manifest.inspect_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT
        )
    )
    assert all(
        item.repository_relative_path
        != manifest.DEVELOPMENT_SYNTHETIC_MODULE_PATH
        for item in readiness.component_registry.records
    )
    assert readiness.global_bindings[
        "retired_development_ids_excluded"
    ] == list(prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS)


def test_current_tree_emits_only_content_addressed_nonauthorizing_readiness() -> None:
    first = manifest.inspect_confirmatory_execution_manifest_readiness_v1(
        REPOSITORY_ROOT
    )
    second = manifest.inspect_confirmatory_execution_manifest_readiness_v1(
        REPOSITORY_ROOT
    )
    assert first == second
    assert first.readiness_id == second.readiness_id
    assert first.status == "NONAUTHORIZING_READINESS"
    assert first.target_execution_allowed is False
    assert first.anchor_id is None
    expected_missing = tuple(
        item.component_role
        for item in manifest.COMPONENT_ROLE_SPECS
        if not (
            REPOSITORY_ROOT / item.repository_relative_path
        ).is_file()
    )
    assert first.missing_component_roles == expected_missing
    assert first.missing_applicable_bindings == (
        "source_reconstruction_recipe_id",
        "source_archive_id",
        "source_archive_verification_attestation_id",
    )
    document = first.to_document()
    assert document["final_manifest_id"] is None
    assert document["anchor_id"] is None
    assert document["target_execution_allowed"] is False
    assert document["registered_observations_generated"] == 0
    assert all(
        item.startswith(("MISSING_", "CANONICAL_", "FINALIZATION_"))
        for item in first.finalization_blockers
    )
    assert (
        manifest.SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER
        in first.finalization_blockers
    )
    assert (
        manifest.verify_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT,
            first,
        )
        == first
    )


def test_readiness_rejects_identity_valid_but_wrong_frozen_bindings() -> None:
    readiness = (
        manifest.inspect_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT
        )
    )
    wrong_bindings = dict(readiness.global_bindings)
    wrong_bindings["context_ids"] = ["a" * 64] * 3
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="differ from frozen authorities",
    ):
        replace(readiness, global_bindings=wrong_bindings)


def test_incomplete_finalize_and_direct_schema_construction_fail_closed() -> None:
    readiness = (
        manifest.inspect_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT
        )
    )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="prerequisites are incomplete",
    ):
        manifest.finalize_confirmatory_execution_manifest_v1(
            REPOSITORY_ROOT
        )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="internally minted",
    ):
        manifest.ConfirmatoryExecutionManifestV1(
            object(),
            readiness,
        )
    assert manifest.FINALIZATION_ENABLED is True
    assert manifest.TARGET_EXECUTION_ALLOWED is False


def test_manifest_dependency_is_one_way_and_contains_no_final_prereg_id() -> None:
    readiness = (
        manifest.inspect_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT
        )
    )
    bindings = readiness.global_bindings
    assert bindings["final_preregistration_id_embedded"] is False
    assert bindings["future_binding_direction"] == (
        "FINAL_PREREGISTRATION_BINDS_MANIFEST_ID_ONE_WAY"
    )
    assert "final_preregistration_id" not in bindings
    assert "preregistration_id" not in bindings
    encoded = repr(readiness.to_document())
    draft_id = (
        prereg.freeze_transfer_guided_acquisition_preregistration_v1()
        .preregistration_id
    )
    assert draft_id not in encoded


def test_finalization_and_write_signatures_accept_no_ids_or_status() -> None:
    finalize_signature = inspect.signature(
        manifest.finalize_confirmatory_execution_manifest_v1
    )
    write_signature = inspect.signature(
        manifest.write_confirmatory_execution_manifest_v1
    )
    assert tuple(finalize_signature.parameters) == ("repository_root",)
    assert tuple(write_signature.parameters) == ("repository_root",)
    forbidden = {
        "manifest_id",
        "preregistration_id",
        "status",
        "global_bindings",
        "component_registry",
        "source_recipe_path",
        "source_campaign",
        "attestation_id",
        "output_path",
    }
    assert forbidden.isdisjoint(finalize_signature.parameters)
    assert forbidden.isdisjoint(write_signature.parameters)


def test_canonical_artifact_writer_is_idempotent_and_rejects_overwrite(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / "specs").mkdir(parents=True)
    document = {"schema": "synthetic", "value": 1}
    first = manifest._write_canonical_artifact_v1(
        root.resolve(),
        "specs/final.json",
        document,
    )
    second = manifest._write_canonical_artifact_v1(
        root.resolve(),
        "specs/final.json",
        document,
    )
    assert first == second
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="differs",
    ):
        manifest._write_canonical_artifact_v1(
            root.resolve(),
            "specs/final.json",
            {"schema": "synthetic", "value": 2},
        )
    linked = root / "specs/linked.json"
    linked.symlink_to(first)
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="symlink",
    ):
        manifest._write_canonical_artifact_v1(
            root.resolve(),
            "specs/linked.json",
            document,
        )
