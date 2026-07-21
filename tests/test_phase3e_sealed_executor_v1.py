from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import shutil
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    RouteKindEnum,
    SHARED_AXES,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    official_actual_projection_profile_v1,
)
from acfqp.access_protocol_v1 import (
    AccessOperation,
    FailClosedAccessController,
    RouteDecisionFreezeAttestationV1,
)
from acfqp.phase3e_sealed_executor_v1 import (
    ExecutorRecipeV1,
    OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE,
    OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY,
    Phase3ESealedExecutorV1Error,
    RuntimeIntegrityProbeConstructorV1,
    RuntimeFactoryCardinalityV1,
    RuntimeManifestCapProfileV1,
    RuntimeTreeCASV1,
    RuntimeTreeManifestV1,
    SealedExecutorConstructionReceiptV1,
    SealedExecutorExecutionMergeProofV1,
    SealedExecutorFailureEvidenceV1,
    SealedExecutorFailureMergeProofV1,
    MergedSealedRouteFailureWorkV1,
    SealedPostFreezeExecutorFactoryV1,
    TrustedConstructorRegistryV1,
    merge_sealed_factory_execution_work_v1,
    merge_sealed_factory_failure_work_v1,
    require_sealed_executor_factory_v1,
    runtime_factory_upper_values_v1,
    verify_sealed_factory_failure_merge_v1,
)
from acfqp.marginal_accounting_v1 import derive_marginal_work_aggregate_v1
from acfqp.native_recorder_v1 import (
    NativeCounterRecorderV1,
    derive_failed_recorded_work_v1,
)
from acfqp.phase3e_runner_v1 import (
    Phase3ERunnerV1Error,
    UpperBoundViolationError,
    _check_authoritative_upper,
    run_phase3e,
)
from acfqp.routing_v1 import (
    MarginalRouteDecisionV1,
    RouteComparison,
    RouteSelection,
    TypedNotApplicable,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _source_tree(root: Path, *, worker: bytes = b"print('snapshot')\n") -> Path:
    source = root / "live-checkout" / "src"
    package = source / "acfqp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_bytes(b"")
    (package / "worker.py").write_bytes(worker)
    return source


def _recipe(manifest: RuntimeTreeManifestV1) -> ExecutorRecipeV1:
    return ExecutorRecipeV1(
        manifest.runtime_tree_id,
        RouteSelection.FALLBACK,
        "phase3e-runtime-integrity-probe-v1",
        "acfqp/worker.py",
        _id("executor-configuration"),
    )


def _frozen_invocation(recipe: ExecutorRecipeV1):
    attempt_id = _id("attempt")
    point_id = _id("point")
    decision = MarginalRouteDecisionV1(
        point_id,
        TypedNotApplicable("probe has no causal authority"),
        TypedNotApplicable("probe has no local upper"),
        _id("fallback-upper"),
        RouteSelection.FALLBACK,
        RouteComparison.MISSING_LOCAL_UPPER,
        _id("fallback-upper"),
    )
    controller = FailClosedAccessController(attempt_id, point_id)
    freeze = RouteDecisionFreezeAttestationV1(
        attempt_id,
        point_id,
        decision.route_decision_id,
        _id("decision-verification"),
        recipe.selected_route,
        controller.profile.protocol_sequence_profile_id,
        controller.snapshot().access_event_log_id,
        0,
    )
    prepared = SimpleNamespace(
        context=SimpleNamespace(route_attempt_id=attempt_id),
        decision_point=SimpleNamespace(decision_point_id=point_id),
        runtime_tree_id=recipe.runtime_tree_id,
        executor_recipe_id=recipe.executor_recipe_id,
    )
    # Low-level factory tests establish only the post-freeze runtime boundary;
    # route-decision semantic replay is covered by the integrated runner tests.
    controller._decision = decision
    controller._freeze = freeze
    return prepared, controller


class _ReadingConstructor:
    def __init__(self) -> None:
        self.construct_calls = 0
        self.execute_calls = 0
        self.lease_roots: list[Path] = []

    def construct_after_freeze(self, grant):
        self.construct_calls += 1
        grant.runtime_tree.verify()
        root = grant.runtime_tree.root
        self.lease_roots.append(root)
        payload = (root / grant.recipe.entrypoint_relative_path).read_bytes()

        def execute(_prepared, _controller, _recorder):
            self.execute_calls += 1
            assert root.exists()
            return payload

        return execute


def test_snapshot_round_trip_is_canonical_and_ignores_later_live_checkout_edits(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    manifest = cas.snapshot_build_tree(source)
    assert RuntimeTreeManifestV1.from_dict(manifest.to_dict()) == manifest
    assert cas.snapshot_build_tree(source) == manifest

    # Runtime execution is resolved from the immutable snapshot, never from
    # the checkout path used by the build epoch.
    (source / "acfqp" / "worker.py").write_bytes(b"raise SystemExit('attack')\n")
    recipe = _recipe(manifest)
    factory = SealedPostFreezeExecutorFactoryV1(
        recipe, cas, RuntimeIntegrityProbeConstructorV1()
    )
    prepared, controller = _frozen_invocation(recipe)
    assert factory(prepared, controller, object()) == manifest.runtime_tree_id.encode()
    accounting = factory.construction_accounting
    assert accounting is not None
    assert accounting.receipt.runtime_tree_id == manifest.runtime_tree_id
    assert accounting.receipt.total_bytes == manifest.total_bytes
    assert accounting.receipt.file_count == manifest.file_count
    assert (
        SealedExecutorConstructionReceiptV1.from_dict(
            accounting.receipt.to_dict()
        )
        == accounting.receipt
    )
    assert TrustedConstructorRegistryV1.from_dict(
        OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY.to_dict()
    ) == OFFICIAL_TRUSTED_CONSTRUCTOR_REGISTRY
    assert type(OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE).from_dict(
        OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE.to_dict()
    ) == OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE
    injected = accounting.receipt.to_dict()
    injected["foreign"] = 1
    with pytest.raises(ValueError, match="field"):
        SealedExecutorConstructionReceiptV1.from_dict(injected)
    assert accounting.recorded_work.work_vector.value("io.staged_bytes") == (
        manifest.total_bytes
    )
    assert [event.operation for event in controller.snapshot().events] == [
        AccessOperation.RESOLVE_RUNTIME_CAS,
        AccessOperation.OPEN_RUNTIME_PRIVATE_LEASE,
        AccessOperation.CONSTRUCT_SELECTED_EXECUTOR,
    ]


def test_factory_does_not_construct_before_freeze_and_is_fail_closed_single_use(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    recipe = _recipe(cas.snapshot_build_tree(source))
    factory = SealedPostFreezeExecutorFactoryV1(
        recipe, cas, RuntimeIntegrityProbeConstructorV1()
    )
    prepared, _controller = _frozen_invocation(recipe)

    with pytest.raises(
        Phase3ESealedExecutorV1Error,
        match="forbidden before a typed route freeze",
    ):
        factory(
            prepared,
            SimpleNamespace(freeze_attestation=None),
            object(),
        )
    with pytest.raises(Phase3ESealedExecutorV1Error, match="single-use"):
        factory(prepared, _controller, object())


@pytest.mark.parametrize("foreign_field", ("runtime_tree_id", "executor_recipe_id"))
def test_factory_rejects_foreign_prepared_runtime_or_recipe_before_construction(
    tmp_path: Path,
    foreign_field: str,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    recipe = _recipe(cas.snapshot_build_tree(source))
    factory = SealedPostFreezeExecutorFactoryV1(
        recipe, cas, RuntimeIntegrityProbeConstructorV1()
    )
    prepared, controller = _frozen_invocation(recipe)
    setattr(prepared, foreign_field, _id(f"foreign-{foreign_field}"))
    with pytest.raises(Phase3ESealedExecutorV1Error, match="foreign|another"):
        factory(prepared, controller, object())
    assert factory.construction_accounting is None
    failure = factory.failure_evidence
    assert failure is not None
    assert SealedExecutorFailureEvidenceV1.from_dict(failure.to_dict()) == failure


def test_cas_tamper_and_unregistered_extra_file_fail_before_construction(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    manifest = cas.snapshot_build_tree(source)
    runtime_file = cas.object_root(manifest.runtime_tree_id) / "tree/acfqp/worker.py"
    runtime_file.chmod(0o644)
    runtime_file.write_bytes(b"print('CAS attack')\n")
    with pytest.raises(
        Phase3ESealedExecutorV1Error,
        match="differs from manifest|preregistered byte limit",
    ):
        cas.resolve(manifest.runtime_tree_id)

    # Restore the registered bytes, then demonstrate that adding a file is
    # also rejected rather than silently broadening the executable payload.
    runtime_file.write_bytes(b"print('snapshot')\n")
    (runtime_file.parent / "foreign.py").write_bytes(b"pass\n")
    with pytest.raises(Phase3ESealedExecutorV1Error, match="file set differs"):
        cas.resolve(manifest.runtime_tree_id)


def test_snapshot_rejects_symlinked_runtime_payload(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_bytes(b"print('foreign')\n")
    (source / "acfqp" / "linked.py").symlink_to(outside)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    with pytest.raises(Phase3ESealedExecutorV1Error, match="symlinks"):
        cas.snapshot_build_tree(source)


def test_foreign_object_key_and_live_checkout_cannot_be_resolved_as_the_cas(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    manifest = cas.snapshot_build_tree(source)
    foreign_id = _id("foreign-tree-key")
    shutil.copytree(cas.object_root(manifest.runtime_tree_id), cas.object_root(foreign_id))
    with pytest.raises(Phase3ESealedExecutorV1Error, match="foreign runtime tree"):
        cas.resolve(foreign_id)

    live_as_cas = RuntimeTreeCASV1(source.resolve())
    with pytest.raises(Phase3ESealedExecutorV1Error, match="absent"):
        live_as_cas.resolve(manifest.runtime_tree_id)

    cas_alias = tmp_path / "cas-alias"
    cas_alias.symlink_to(cas.root, target_is_directory=True)
    with pytest.raises(Phase3ESealedExecutorV1Error, match="symlink or alias"):
        RuntimeTreeCASV1(cas_alias)


def test_missing_recipe_entrypoint_and_lease_mutation_fail_closed(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    manifest = cas.snapshot_build_tree(source)
    missing = replace(_recipe(manifest), entrypoint_relative_path="acfqp/missing.py")
    prepared, controller = _frozen_invocation(missing)
    with pytest.raises(
        Phase3ESealedExecutorV1Error,
        match="route/entrypoint differs",
    ):
        SealedPostFreezeExecutorFactoryV1(
            missing, cas, RuntimeIntegrityProbeConstructorV1()
        )

    class MutatingConstructor:
        def construct_after_freeze(self, grant):
            path = grant.runtime_tree.root / "acfqp/worker.py"

            def execute(*_args):
                path.chmod(0o644)
                path.write_bytes(b"mutated\n")
                return object()

            return execute

    recipe = _recipe(manifest)
    prepared, controller = _frozen_invocation(recipe)
    with pytest.raises(
        Phase3ESealedExecutorV1Error,
        match="arbitrary, subclassed, or closure",
    ):
        SealedPostFreezeExecutorFactoryV1(
            recipe, cas, MutatingConstructor()
        )


def test_new_profile_rejects_an_arbitrary_preconstructed_legacy_callable() -> None:
    with pytest.raises(Phase3ESealedExecutorV1Error, match="legacy executors"):
        require_sealed_executor_factory_v1(lambda *_args: None)


def test_main_runner_rejects_legacy_selected_callable_under_sealed_profile(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    recipe = _recipe(cas.snapshot_build_tree(source))

    class PreparedStub:
        sealed_executor_profile = True
        two_stage_accounting_profile = False
        runtime_tree_id = recipe.runtime_tree_id
        executor_recipe_id = recipe.executor_recipe_id

        def validate(self, _registry, _profile):
            return SimpleNamespace(selected_route=RouteSelection.FALLBACK), object()

    with pytest.raises(Phase3ERunnerV1Error, match="legacy executors"):
        run_phase3e(  # type: ignore[arg-type]
            PreparedStub(),
            local_executor=lambda *_args: None,
            fallback_executor=lambda *_args: None,
        )

    # A sealed factory for another recipe is rejected before its constructor
    # or CAS resolver can be invoked.
    foreign = replace(recipe, executor_configuration_id=_id("foreign-config"))
    factory = SealedPostFreezeExecutorFactoryV1(
        foreign, cas, RuntimeIntegrityProbeConstructorV1()
    )
    with pytest.raises(Phase3ERunnerV1Error, match="prepared runtime bindings"):
        run_phase3e(  # type: ignore[arg-type]
            PreparedStub(),
            local_executor=lambda *_args: None,
            fallback_executor=factory,
        )
    assert factory.construction_accounting is None


def test_recipe_round_trip_and_route_mismatch_fail_before_constructor(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    recipe = _recipe(cas.snapshot_build_tree(source))
    assert ExecutorRecipeV1.from_dict(recipe.to_dict()) == recipe
    prepared, controller = _frozen_invocation(recipe)
    controller._freeze = replace(
        controller.freeze_attestation,
        selected_route=RouteSelection.LOCAL,
    )
    with pytest.raises(Phase3ESealedExecutorV1Error, match="route differs"):
        SealedPostFreezeExecutorFactoryV1(
            recipe, cas, RuntimeIntegrityProbeConstructorV1()
        )(
            prepared, controller, object()
        )


def test_factory_work_merges_once_and_omitting_it_violates_selected_upper(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    manifest = cas.snapshot_build_tree(source)
    recipe = _recipe(manifest)
    factory = SealedPostFreezeExecutorFactoryV1(
        recipe, cas, RuntimeIntegrityProbeConstructorV1()
    )
    prepared, controller = _frozen_invocation(recipe)
    factory(prepared, controller, object())
    accounting = factory.construction_accounting
    assert accounting is not None

    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    subject = prepared.context.route_attempt_id
    delegate_recorder = NativeCounterRecorderV1(
        subject_id=subject,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="test-sealed-delegate-v1",
    )
    delegate_recorder.record_route_completion(success=True)
    delegate = delegate_recorder.seal()
    merged = merge_sealed_factory_execution_work_v1(
        factory_accounting=accounting,
        delegate_work=delegate,
        registry=registry,
        comparison_profile=profile,
    )
    merged_values = merged.recorded_work.work_vector.values
    assert merged_values["io.staged_bytes"] == manifest.total_bytes
    assert merged_values["route.attempts"] == 1
    assert SealedExecutorExecutionMergeProofV1.from_dict(
        merged.merge_proof.to_dict()
    ) == merged.merge_proof
    actual_factory = accounting.recorded_work.work_vector.values
    for path, bound in runtime_factory_upper_values_v1().items():
        assert actual_factory[path] <= bound

    suffix_recorder = NativeCounterRecorderV1(
        subject_id=subject,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="test-sealed-empty-suffix-v1",
    )
    suffix = suffix_recorder.seal()
    aggregate = derive_marginal_work_aggregate_v1(
        subject_id=subject,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        execution=(
            merged.recorded_work.work_vector,
            merged.recorded_work.comparison_vector,
            merged.recorded_work.actual_projection_proof,
        ),
        verification_suffix=(
            suffix.work_vector,
            suffix.comparison_vector,
            suffix.actual_projection_proof,
        ),
        registry=registry,
        comparison_profile=profile,
        actual_profile=official_actual_projection_profile_v1(registry, profile),
    )
    # An upper built from the delegate alone omits all CAS construction work.
    omitted = {
        axis: delegate.comparison_vector.value(axis) for axis in SHARED_AXES
    }
    with pytest.raises(UpperBoundViolationError, match="authoritative upper"):
        _check_authoritative_upper(
            aggregate,
            SimpleNamespace(upper_bounds=tuple(sorted(omitted.items()))),
        )


def test_security_boundaries_reject_mock_and_subclass_authorities(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    manifest = cas.snapshot_build_tree(source)
    recipe = _recipe(manifest)

    with pytest.raises(Phase3ESealedExecutorV1Error, match="legacy executors"):
        require_sealed_executor_factory_v1(
            Mock(spec=SealedPostFreezeExecutorFactoryV1)
        )

    class EvilFactory(SealedPostFreezeExecutorFactoryV1):
        pass

    evil_factory = EvilFactory(
        recipe, cas, RuntimeIntegrityProbeConstructorV1()
    )
    with pytest.raises(Phase3ESealedExecutorV1Error, match="legacy executors"):
        require_sealed_executor_factory_v1(evil_factory)

    class EvilCAS(RuntimeTreeCASV1):
        pass

    with pytest.raises(Phase3ESealedExecutorV1Error, match="typed runtime CAS"):
        SealedPostFreezeExecutorFactoryV1(
            recipe,
            EvilCAS((tmp_path / "evil-cas").resolve()),
            RuntimeIntegrityProbeConstructorV1(),
        )

    registry = official_counter_registry_v1()
    official_profile = official_comparison_profile_v1(registry)

    class EvilComparisonProfile(ComparisonProfileV1):
        def validate(self, _registry):
            return None

    evil_profile = EvilComparisonProfile(
        official_profile.profile_key,
        official_profile.schema_version,
        official_profile.counter_registry_id,
        official_profile.axes,
        official_profile.terms,
    )
    with pytest.raises(Phase3ESealedExecutorV1Error, match="exact comparison"):
        SealedPostFreezeExecutorFactoryV1(
            recipe,
            cas,
            RuntimeIntegrityProbeConstructorV1(),
            comparison_profile=evil_profile,
        )

    class EvilCap(RuntimeManifestCapProfileV1):
        pass

    with pytest.raises(Phase3ESealedExecutorV1Error, match="cap profile"):
        SealedPostFreezeExecutorFactoryV1(
            recipe,
            cas,
            RuntimeIntegrityProbeConstructorV1(),
            runtime_cap_profile=EvilCap(),
        )


def test_runtime_cardinality_and_failure_merge_proofs_are_strict_and_exact(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    manifest = cas.snapshot_build_tree(source)
    cardinality = RuntimeFactoryCardinalityV1.from_manifest(manifest)
    assert RuntimeFactoryCardinalityV1.from_dict(cardinality.to_dict()) == cardinality
    injected = cardinality.to_dict()
    injected["foreign"] = 1
    with pytest.raises(ValueError, match="field"):
        RuntimeFactoryCardinalityV1.from_dict(injected)

    recipe = _recipe(manifest)
    factory = SealedPostFreezeExecutorFactoryV1(
        recipe, cas, RuntimeIntegrityProbeConstructorV1()
    )
    prepared, controller = _frozen_invocation(recipe)
    factory(prepared, controller, object())
    construction = factory.construction_accounting
    assert construction is not None
    assert dict(construction.receipt.counter_values) == dict(
        cardinality.upper_values()
    )
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    delegate_recorder = NativeCounterRecorderV1(
        subject_id=prepared.context.route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="test-sealed-failed-delegate-v1",
    )
    delegate_recorder.observe_peak("io.mounted_bytes_peak", 4096)
    delegate_recorder.observe_peak("memory.working_bytes_peak", 8192)
    delegate_recorder.record_route_completion(success=False)
    delegate = delegate_recorder.seal()
    merged = merge_sealed_factory_failure_work_v1(
        factory_partial_work=construction.recorded_work,
        delegate_partial_work=delegate,
        registry=registry,
        comparison_profile=profile,
    )
    assert merged.recorded_work.work_vector.value("io.mounted_bytes_peak") == (
        construction.recorded_work.work_vector.value("io.mounted_bytes_peak")
        + 4096
    )
    assert merged.recorded_work.work_vector.value("memory.working_bytes_peak") == (
        construction.recorded_work.work_vector.value("memory.working_bytes_peak")
        + 8192
    )
    assert SealedExecutorFailureMergeProofV1.from_dict(
        merged.merge_proof.to_dict()
    ) == merged.merge_proof
    verify_sealed_factory_failure_merge_v1(
        merged,
        factory_partial_work=construction.recorded_work,
        delegate_partial_work=delegate,
        registry=registry,
        comparison_profile=profile,
    )
    attacked = MergedSealedRouteFailureWorkV1(
        merged.recorded_work,
        replace(
            merged.merge_proof,
            factory_partial_work_vector_id=_id("foreign-factory-work"),
        ),
    )
    with pytest.raises(Phase3ESealedExecutorV1Error, match="does not replay"):
        verify_sealed_factory_failure_merge_v1(
            attacked,
            factory_partial_work=construction.recorded_work,
            delegate_partial_work=delegate,
            registry=registry,
            comparison_profile=profile,
        )

    factory_only = merge_sealed_factory_failure_work_v1(
        factory_partial_work=construction.recorded_work,
        delegate_partial_work=None,
        registry=registry,
        comparison_profile=profile,
    )
    document = factory_only.merge_proof.to_dict()
    assert type(document["delegate_partial_work_vector_id"]) is dict
    document["delegate_partial_work_vector_id"] = None
    with pytest.raises((TypeError, ValueError)):
        SealedExecutorFailureMergeProofV1.from_dict(document)

    changed_reason = TypedNotApplicable("substituted typed-null reason")
    reason_attack = MergedSealedRouteFailureWorkV1(
        factory_only.recorded_work,
        replace(
            factory_only.merge_proof,
            delegate_partial_work_vector_id=changed_reason,
            delegate_partial_comparison_vector_id=changed_reason,
            delegate_partial_projection_proof_id=changed_reason,
        ),
    )
    with pytest.raises(Phase3ESealedExecutorV1Error, match="does not replay"):
        verify_sealed_factory_failure_merge_v1(
            reason_attack,
            factory_partial_work=construction.recorded_work,
            delegate_partial_work=None,
            registry=registry,
            comparison_profile=profile,
        )


def test_late_failure_uses_factory_delegate_failure_merge_as_unique_owner(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path)
    cas = RuntimeTreeCASV1((tmp_path / "cas").resolve())
    manifest = cas.snapshot_build_tree(source)
    recipe = _recipe(manifest)
    factory = SealedPostFreezeExecutorFactoryV1(
        recipe, cas, RuntimeIntegrityProbeConstructorV1()
    )
    prepared, controller = _frozen_invocation(recipe)
    factory(prepared, controller, object())
    construction = factory.construction_accounting
    assert construction is not None

    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    delegate_recorder = NativeCounterRecorderV1(
        subject_id=prepared.context.route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
        recorder_id="test-sealed-success-before-late-failure-v1",
    )
    delegate_recorder.observe_peak("io.mounted_bytes_peak", 4096)
    delegate_recorder.observe_peak("memory.working_bytes_peak", 8192)
    delegate_recorder.record_route_completion(success=True)
    delegate = delegate_recorder.seal()
    successful_execution = merge_sealed_factory_execution_work_v1(
        factory_accounting=construction,
        delegate_work=delegate,
        registry=registry,
        comparison_profile=profile,
    )

    # A verifier or upper check may fail only after the sealed delegate has
    # returned successfully.  Re-labelling the already merged success vector
    # retains its success-merge provenance and is not the canonical replay of
    # the two owned components.
    relabelled_success = derive_failed_recorded_work_v1(
        successful_execution.recorded_work,
        registry=registry,
        comparison_profile=profile,
    )
    canonical_failure = merge_sealed_factory_failure_work_v1(
        factory_partial_work=construction.recorded_work,
        delegate_partial_work=delegate,
        registry=registry,
        comparison_profile=profile,
    )
    assert relabelled_success.work_vector.values == (
        canonical_failure.recorded_work.work_vector.values
    )
    assert relabelled_success.work_vector.work_vector_id != (
        canonical_failure.recorded_work.work_vector.work_vector_id
    )
    verify_sealed_factory_failure_merge_v1(
        canonical_failure,
        factory_partial_work=construction.recorded_work,
        delegate_partial_work=delegate,
        registry=registry,
        comparison_profile=profile,
    )
