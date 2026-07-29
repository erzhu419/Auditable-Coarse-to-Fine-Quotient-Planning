from __future__ import annotations

from dataclasses import fields, replace
import inspect
from pathlib import Path
from typing import Any

import pytest

from acfqp import v072_confirmatory_execution_manifest_v1 as manifest
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_source_reconstruction_recipe_v1 as recipe_v1
from tests.test_verified_source_acquisition_archive_independent_verifier_v2 import (
    miniature_source_archive,
)
from tests.test_v072_source_reconstruction_recipe_v1 import (
    mechanics_recipe,
    mechanics_source,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _unsafe_clone(value: Any, **changes: Any) -> Any:
    cloned = object.__new__(type(value))
    for item in fields(value):
        object.__setattr__(
            cloned,
            item.name,
            changes.get(item.name, getattr(value, item.name)),
        )
    return cloned


@pytest.fixture(scope="module")
def source_readiness(miniature_source_archive):
    source_campaign, source_verification, _ = miniature_source_archive
    return (
        manifest.inspect_confirmatory_execution_manifest_readiness_with_source_v1(
            REPOSITORY_ROOT,
            source_campaign=source_campaign,
            source_verification=source_verification,
        )
    )


def test_zero_argument_source_path_remains_missing_and_typed() -> None:
    readiness = (
        manifest.inspect_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT
        )
    )
    assert readiness.missing_applicable_bindings == (
        "source_reconstruction_recipe_id",
        "source_archive_id",
        "source_archive_verification_attestation_id",
    )
    for field_name in readiness.missing_applicable_bindings:
        assert readiness.global_bindings[field_name]["kind"] == (
            "MISSING_APPLICABLE_ID"
        )
    assert (
        manifest.SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER
        in readiness.finalization_blockers
    )


def test_typed_source_campaign_populates_only_dual_replayed_source_ids(
    miniature_source_archive,
    source_readiness,
) -> None:
    source_campaign, source_verification, _ = miniature_source_archive
    readiness = source_readiness
    component = readiness._source_archive_component
    assert component is not None
    assert readiness.global_bindings[
        "source_reconstruction_recipe_id"
    ]["kind"] == "MISSING_APPLICABLE_ID"
    assert readiness.missing_applicable_bindings == (
        "source_reconstruction_recipe_id",
    )
    assert readiness.global_bindings["source_archive_id"] == (
        component.archive.archive_id
    )
    assert readiness.global_bindings[
        "source_archive_verification_attestation_id"
    ] == component.independent_attestation.verification_id
    assert (
        manifest.verify_confirmatory_execution_manifest_readiness_with_source_v1(
            REPOSITORY_ROOT,
            source_campaign=source_campaign,
            source_verification=source_verification,
            claimed=readiness,
        )
        == readiness
    )

    # This in-memory source fixture validates archive mechanics only.  It is
    # not the production persistence route; recipe replay and execution stay
    # locked.
    document = readiness.to_document()
    assert (
        manifest.SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER
        in readiness.finalization_blockers
    )
    assert document["final_manifest_id"] is None
    assert document["anchor_id"] is None
    assert document["target_execution_allowed"] is False
    assert document["registered_observations_generated"] == 0
    assert manifest.FINALIZATION_ENABLED is True


def test_source_path_accepts_no_archive_component_or_caller_id(
    miniature_source_archive,
) -> None:
    source_campaign, source_verification, archive = miniature_source_archive
    signature = inspect.signature(
        manifest.inspect_confirmatory_execution_manifest_readiness_with_source_v1
    )
    assert tuple(signature.parameters) == (
        "repository_root",
        "source_campaign",
        "source_verification",
    )
    assert all(
        name not in signature.parameters
        for name in (
            "archive",
            "archive_id",
            "source_archive_id",
            "component",
            "attestation_id",
        )
    )
    with pytest.raises(TypeError):
        (
            manifest
            .inspect_confirmatory_execution_manifest_readiness_with_source_v1(
                REPOSITORY_ROOT,
                source_campaign=source_campaign,
                source_verification=source_verification,
                archive=archive,  # type: ignore[call-arg]
            )
        )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="exact campaign and verification types",
    ):
        (
            manifest
            .inspect_confirmatory_execution_manifest_readiness_with_source_v1(
                REPOSITORY_ROOT,
                source_campaign=archive,  # type: ignore[arg-type]
                source_verification=source_verification,
            )
        )


def test_incomplete_strict_recipe_reports_exact_blocker_without_runner_access(
    tmp_path: Path,
    mechanics_recipe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = (tmp_path / "source-recipe.json").resolve()
    path.write_bytes(
        recipe_v1.render_source_reconstruction_recipe_v1(
            mechanics_recipe
        )
    )
    calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("real source runner was reached")

    monkeypatch.setattr(
        recipe_v1.campaign_v1,
        "run_observation_support_campaign_v1",
        forbidden,
    )
    monkeypatch.setattr(
        manifest,
        "_fixed_source_recipe_path_v1",
        lambda _root: path,
    )
    monkeypatch.setattr(
        manifest,
        "_source_recipe_git_status_v1",
        lambda _root: (False, False),
    )
    readiness = (
        manifest
        .inspect_confirmatory_execution_manifest_readiness_with_source_recipe_v1(
            REPOSITORY_ROOT,
        )
    )
    assert calls == 0
    assert readiness.global_bindings[
        "source_reconstruction_recipe_id"
    ] == mechanics_recipe.recipe_id
    assert readiness.missing_applicable_bindings == (
        "source_archive_id",
        "source_archive_verification_attestation_id",
    )
    assert recipe_v1.INCOMPLETE_BLOCKER in readiness.finalization_blockers
    assert (
        manifest.SOURCE_RECONSTRUCTION_RECIPE_NOT_TRACKED_BLOCKER
        in readiness.finalization_blockers
    )
    assert (
        manifest.SOURCE_RECONSTRUCTION_RECIPE_NOT_SUPPLIED_BLOCKER
        not in readiness.finalization_blockers
    )
    assert readiness.target_execution_allowed is False
    assert readiness.to_document()["registered_observations_generated"] == 0


def test_recipe_manifest_api_accepts_no_runner_ids_or_source_objects() -> None:
    inspect_signature = inspect.signature(
        manifest
        .inspect_confirmatory_execution_manifest_readiness_with_source_recipe_v1
    )
    verify_signature = inspect.signature(
        manifest
        .verify_confirmatory_execution_manifest_readiness_with_source_recipe_v1
    )
    assert tuple(inspect_signature.parameters) == (
        "repository_root",
    )
    assert tuple(verify_signature.parameters) == (
        "repository_root",
        "claimed",
    )
    forbidden = {
        "runner",
        "expected_ids",
        "source_recipe_path",
        "source_campaign",
        "source_verification",
        "archive",
        "component",
        "attestation_id",
    }
    assert forbidden.isdisjoint(inspect_signature.parameters)
    assert forbidden.isdisjoint(verify_signature.parameters)
    with pytest.raises(TypeError):
        (
            manifest
            .inspect_confirmatory_execution_manifest_readiness_with_source_recipe_v1(
                REPOSITORY_ROOT,
                source_recipe_path=Path("/tmp/arbitrary-recipe.json"),
            )
        )


def test_production_recipe_path_is_fixed_unignored_and_manifest_bound() -> None:
    expected = (
        REPOSITORY_ROOT
        / manifest.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
    )
    assert manifest._fixed_source_recipe_path_v1(
        REPOSITORY_ROOT
    ) == expected
    ignored, tracked = manifest._source_recipe_git_status_v1(
        REPOSITORY_ROOT
    )
    assert ignored is False
    if not expected.exists():
        assert tracked is False
    readiness = (
        manifest.inspect_confirmatory_execution_manifest_readiness_v1(
            REPOSITORY_ROOT
        )
    )
    assert readiness.global_bindings[
        "source_reconstruction_recipe_repository_path"
    ] == "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json"


def test_fixed_recipe_path_rejects_symlink_and_ignored_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    specs = root / "specs"
    specs.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    (specs / "V072_SOURCE_RECONSTRUCTION_RECIPE.json").symlink_to(
        outside
    )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="contains a symlink",
    ):
        manifest._fixed_source_recipe_path_v1(root.resolve())

    monkeypatch.setattr(
        manifest,
        "_fixed_source_recipe_path_v1",
        lambda _root: outside,
    )
    monkeypatch.setattr(
        manifest,
        "_source_recipe_git_status_v1",
        lambda _root: (True, False),
    )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="is ignored",
    ):
        (
            manifest
            .inspect_confirmatory_execution_manifest_readiness_with_source_recipe_v1(
                REPOSITORY_ROOT
            )
        )


def test_recipe_path_orders_strict_load_real_replay_and_identity_closure(
    tmp_path: Path,
    mechanics_recipe,
    miniature_source_archive,
    source_readiness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = (tmp_path / "source-recipe.json").resolve()
    path.write_bytes(
        recipe_v1.render_source_reconstruction_recipe_v1(
            mechanics_recipe
        )
    )
    source_campaign, source_verification, _ = miniature_source_archive
    component = source_readiness._source_archive_component
    assert component is not None
    replay = recipe_v1.SourceReconstructionReplayV1(
        mechanics_recipe.recipe_id,
        source_campaign,
        source_verification,
        component.archive,
        component.production_verification,
        component.independent_attestation,
        component,
    )
    events: list[str] = []

    def strict_load(candidate):
        assert Path(candidate) == path
        events.append("strict_canonical_recipe_load")
        return mechanics_recipe

    def real_replay(repository_root, recipe):
        assert Path(repository_root) == REPOSITORY_ROOT
        assert recipe is mechanics_recipe
        events.append("real_source_graph_replay")
        return replay

    monkeypatch.setattr(
        recipe_v1.SourceReconstructionRecipeV1,
        "replay_ready",
        property(lambda _self: True),
    )
    monkeypatch.setattr(
        recipe_v1,
        "load_source_reconstruction_recipe_v1",
        strict_load,
    )
    monkeypatch.setattr(
        recipe_v1,
        "replay_source_reconstruction_recipe_v1",
        real_replay,
    )
    monkeypatch.setattr(
        manifest,
        "_fixed_source_recipe_path_v1",
        lambda _root: path,
    )
    monkeypatch.setattr(
        manifest,
        "_source_recipe_git_status_v1",
        lambda _root: (False, True),
    )
    readiness = (
        manifest
        .inspect_confirmatory_execution_manifest_readiness_with_source_recipe_v1(
            REPOSITORY_ROOT,
        )
    )
    assert events == [
        "strict_canonical_recipe_load",
        "real_source_graph_replay",
    ]
    assert readiness.missing_applicable_bindings == ()
    assert readiness._source_reconstruction_replay is replay
    assert readiness._source_archive_component is component
    assert readiness.global_bindings[
        "source_reconstruction_recipe_id"
    ] == mechanics_recipe.recipe_id
    assert readiness.global_bindings[
        "source_archive_id"
    ] == component.archive.archive_id
    assert (
        recipe_v1.INCOMPLETE_BLOCKER
        not in readiness.finalization_blockers
    )
    assert (
        manifest.SOURCE_RECONSTRUCTION_RECIPE_REPLAY_FAILED_BLOCKER
        not in readiness.finalization_blockers
    )
    assert readiness.finalization_blockers == ()
    assert readiness.target_execution_allowed is False
    assert readiness.to_document()["registered_observations_generated"] == 0


def test_complete_recipe_mints_manifest_then_one_way_preregistration(
    tmp_path: Path,
    mechanics_recipe,
    miniature_source_archive,
    source_readiness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = (tmp_path / "source-recipe.json").resolve()
    path.write_bytes(
        recipe_v1.render_source_reconstruction_recipe_v1(
            mechanics_recipe
        )
    )
    source_campaign, source_verification, _ = miniature_source_archive
    component = source_readiness._source_archive_component
    assert component is not None
    replay = recipe_v1.SourceReconstructionReplayV1(
        mechanics_recipe.recipe_id,
        source_campaign,
        source_verification,
        component.archive,
        component.production_verification,
        component.independent_attestation,
        component,
    )
    monkeypatch.setattr(
        recipe_v1.SourceReconstructionRecipeV1,
        "replay_ready",
        property(lambda _self: True),
    )
    monkeypatch.setattr(
        recipe_v1,
        "load_source_reconstruction_recipe_v1",
        lambda _path: mechanics_recipe,
    )
    monkeypatch.setattr(
        recipe_v1,
        "replay_source_reconstruction_recipe_v1",
        lambda _root, _recipe: replay,
    )
    monkeypatch.setattr(
        manifest,
        "_fixed_source_recipe_path_v1",
        lambda _root: path,
    )
    monkeypatch.setattr(
        manifest,
        "_source_recipe_git_status_v1",
        lambda _root: (False, True),
    )
    final_manifest = manifest.finalize_confirmatory_execution_manifest_v1(
        REPOSITORY_ROOT
    )
    assert final_manifest.global_bindings[
        "source_reconstruction_recipe_id"
    ] == mechanics_recipe.recipe_id
    assert "final_preregistration_id" not in final_manifest.global_bindings
    assert "preregistration_id" not in final_manifest.global_bindings

    writes: list[tuple[str, dict[str, Any]]] = []

    def capture_write(
        _root: Path,
        relative_path: str,
        document: Any,
    ) -> Path:
        writes.append((relative_path, dict(document)))
        return _root / relative_path

    monkeypatch.setattr(
        manifest,
        "finalize_confirmatory_execution_manifest_v1",
        lambda _root: final_manifest,
    )
    monkeypatch.setattr(
        manifest,
        "_write_canonical_artifact_v1",
        capture_write,
    )
    assert (
        manifest.write_confirmatory_execution_manifest_v1(
            REPOSITORY_ROOT
        )
        == final_manifest
    )
    final_preregistration = (
        final_authority.finalize_v072_final_preregistration_v1(
            REPOSITORY_ROOT
        )
    )
    logical = (
        final_authority.verify_v072_final_preregistration_documents_v1(
            manifest_document=final_manifest.to_document(),
            final_preregistration_document=(
                final_preregistration.to_document()
            ),
        )
    )
    assert logical.manifest_id == final_manifest.manifest_id
    assert logical.final_preregistration_id == (
        final_preregistration.final_preregistration_id
    )
    assert final_preregistration.manifest is final_manifest
    assert [item[0] for item in writes] == [
        manifest.FINAL_MANIFEST_REPOSITORY_PATH,
        manifest.FINAL_MANIFEST_REPOSITORY_PATH,
        final_authority.FINAL_PREREGISTRATION_REPOSITORY_PATH,
    ]
    assert final_authority.FINAL_PREREGISTRATION_ENABLED is True


def test_final_preregistration_uses_recipe_path_and_never_snapshot_envelope(
    tmp_path: Path,
    mechanics_recipe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = (tmp_path / "source-recipe.json").resolve()
    path.write_bytes(
        recipe_v1.render_source_reconstruction_recipe_v1(
            mechanics_recipe
        )
    )
    signature = inspect.signature(
        final_authority.inspect_v072_final_preregistration_readiness_v1
    )
    assert tuple(signature.parameters) == ("repository_root",)
    assert "source_bundle_path" not in signature.parameters
    assert "v072_source_bundle_persistence_v1" not in inspect.getsource(
        manifest
    )
    assert "v072_source_bundle_persistence_v1" not in inspect.getsource(
        final_authority
    )
    calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("real source runner was reached")

    monkeypatch.setattr(
        recipe_v1.campaign_v1,
        "run_observation_support_campaign_v1",
        forbidden,
    )
    monkeypatch.setattr(
        manifest,
        "_fixed_source_recipe_path_v1",
        lambda _root: path,
    )
    monkeypatch.setattr(
        manifest,
        "_source_recipe_git_status_v1",
        lambda _root: (False, False),
    )
    readiness = (
        final_authority.inspect_v072_final_preregistration_readiness_v1(
            REPOSITORY_ROOT,
        )
    )
    assert calls == 0
    assert (
        readiness.source_reconstruction_recipe_id
        == mechanics_recipe.recipe_id
    )
    assert recipe_v1.INCOMPLETE_BLOCKER in readiness.finalization_blockers
    assert readiness.target_execution_allowed is False
    assert readiness.registered_observer_calls == 0
    with pytest.raises(
        final_authority.V072FinalPreregistrationLockedV1
    ):
        final_authority.finalize_v072_final_preregistration_v1(
            REPOSITORY_ROOT,
        )
    assert calls == 0


def test_source_path_orders_production_and_independent_replay_before_binding(
    miniature_source_archive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_campaign, source_verification, _ = miniature_source_archive
    events: list[str] = []
    inside_production_verifier = False
    original_freeze = (
        manifest.source_archive_v2
        .freeze_verified_source_acquisition_archive_v2
    )
    original_production_verify = (
        manifest.source_archive_v2
        .verify_verified_source_acquisition_archive_v2
    )
    original_independent_verify = (
        manifest.source_archive_independent_v2
        .verify_source_acquisition_archive_independently_v2
    )
    original_bind = (
        manifest.source_archive_component_v1
        .bind_v072_verified_source_archive_component_v1
    )

    def freeze_wrapper(*args, **kwargs):
        if not inside_production_verifier:
            events.append("production_freeze")
        return original_freeze(*args, **kwargs)

    def production_wrapper(*args, **kwargs):
        nonlocal inside_production_verifier
        events.append("production_verify")
        inside_production_verifier = True
        try:
            return original_production_verify(*args, **kwargs)
        finally:
            inside_production_verifier = False

    def independent_wrapper(*args, **kwargs):
        events.append("independent_verify")
        return original_independent_verify(*args, **kwargs)

    def bind_wrapper(*args, **kwargs):
        events.append("typed_component_bind")
        return original_bind(*args, **kwargs)

    monkeypatch.setattr(
        manifest.source_archive_v2,
        "freeze_verified_source_acquisition_archive_v2",
        freeze_wrapper,
    )
    monkeypatch.setattr(
        manifest.source_archive_v2,
        "verify_verified_source_acquisition_archive_v2",
        production_wrapper,
    )
    monkeypatch.setattr(
        manifest.source_archive_independent_v2,
        "verify_source_acquisition_archive_independently_v2",
        independent_wrapper,
    )
    monkeypatch.setattr(
        manifest.source_archive_component_v1,
        "bind_v072_verified_source_archive_component_v1",
        bind_wrapper,
    )
    manifest.inspect_confirmatory_execution_manifest_readiness_with_source_v1(
        REPOSITORY_ROOT,
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    assert events == [
        "production_freeze",
        "production_verify",
        "independent_verify",
        "typed_component_bind",
    ]


def test_mismatched_source_verification_and_forged_readiness_fail_closed(
    miniature_source_archive,
    source_readiness,
) -> None:
    source_campaign, source_verification, _ = miniature_source_archive
    mismatched = _unsafe_clone(
        source_verification,
        replayed_campaign_id="f" * 64,
    )
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="dual replay",
    ):
        (
            manifest
            .inspect_confirmatory_execution_manifest_readiness_with_source_v1(
                REPOSITORY_ROOT,
                source_campaign=source_campaign,
                source_verification=mismatched,
            )
        )

    forged_bindings = dict(source_readiness.global_bindings)
    forged_bindings["source_archive_id"] = "e" * 64
    with pytest.raises(
        manifest.V072ConfirmatoryExecutionManifestV1InvariantViolation,
        match="frozen authorities",
    ):
        replace(source_readiness, global_bindings=forged_bindings)
