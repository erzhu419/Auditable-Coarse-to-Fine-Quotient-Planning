"""Post-freeze bubblewrap supervisor for the safe-chain direct fallback.

Route estimation uses the registered finite resource profile in
``phase3e_fallback_v1`` and performs no ground transition or worker launch.
Only after a semantically verified FALLBACK decision is frozen does this
module stage the runtime, launch one network/filesystem-isolated Python
process, validate its strict output/attestation, and mint the existing opaque
``GROUND_FALLBACK`` authority without a host-side solver replay.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

from acfqp.access_protocol_v1 import (
    AccessOperation,
    AccessRouteScope,
    FailClosedAccessController,
)
from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRecordV1,
    CounterRegistryV1,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import NativeCounterRecorderV1
from acfqp.phase3e_fallback_adapter_v1 import adapt_ground_fallback_execution_v1
from acfqp.phase3e_fallback_runtime_v1 import (
    ATTESTATION_SCHEMA,
    OUTPUT_SCHEMA,
    IsolatedGroundFallbackRequestV1,
    _tree_measurement,
)
from acfqp.phase3e_fallback_v1 import (
    FALLBACK_FROZEN_BUNDLE_BYTES_CAP,
    FALLBACK_ISOLATION_PROFILE_ID,
    FALLBACK_MOUNTED_BYTES_UPPER,
    FALLBACK_OUTPUT_BYTES_CAP,
    FALLBACK_READ_BYTES_UPPER,
    FALLBACK_REQUEST_BYTES_CAP,
    FALLBACK_RUNTIME_SOURCE_BYTES_CAP,
    FALLBACK_STAGED_BYTES_UPPER,
    FALLBACK_WORKING_BYTES_CAP,
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
    GroundFallbackResultV1,
    GroundFallbackV1Error,
    _seal_isolated_ground_fallback_execution_v1,
    reconstruct_safe_chain_policy_from_signature_v1,
    safe_chain_fallback_context_identity_v1,
)
from acfqp.phase3e_ids import (
    GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
    GROUND_FALLBACK_ISOLATED_ATTESTATION_DOMAIN,
    GROUND_FALLBACK_ISOLATED_OUTPUT_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    require_exact_fields,
)
from acfqp.phase3e_runner_v1 import (
    Phase3ERouteExecutionV1,
    Phase3ERunnerV1Error,
    PreparedPhase3ERunV1,
)
from acfqp.phase3e_sealed_executor_v1 import (
    ExecutorRecipeV1,
    PostFreezeConstructionGrantV1,
    RuntimeFactoryCardinalityV1,
)
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteDecisionContextV1,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    require_semantic_verification_result_v1,
    semantic_verifier_spec_v1,
    verify_ground_fallback_semantics_v1,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SOURCE_ROOT = PROJECT_ROOT / "src"
RECORDER_ID = "phase3e_isolated_ground_fallback_supervisor_v1"
ISOLATED_FALLBACK_EXECUTOR_SEMANTICS_ID = (
    "phase3e-isolated-ground-fallback-executor-v1"
)
ISOLATED_FALLBACK_RUNTIME_ENTRYPOINT = (
    "acfqp/phase3e_fallback_runtime_v1.py"
)


class Phase3EIsolatedFallbackV1Error(Phase3ERunnerV1Error):
    """Isolation, authority, schema, accounting, or attestation failed."""


@dataclass(frozen=True, slots=True)
class IsolatedGroundFallbackExecutorInputsV1:
    frozen_world: Any
    context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    fallback_upper: RouteUpperBoundEnvelopeV1
    cardinality: CardinalityEvidenceV1
    cardinality_bound: GroundFallbackCardinalityBoundV1
    cap_profile: GroundFallbackCapProfileV1
    route_decision_result: object
    fallback_upper_result: object
    cardinality_result: object
    runtime_factory_cardinality: RuntimeFactoryCardinalityV1 | None = None


def isolated_ground_fallback_executor_configuration_id_v1(
    inputs: IsolatedGroundFallbackExecutorInputsV1,
) -> str:
    """Bind one sealed recipe to the exact fallback authority chain."""

    payload = {
            "schema": "acfqp.phase3e_isolated_fallback_executor_configuration.v1",
            "route_decision_context_id": (
                inputs.context.route_decision_context_id
            ),
            "decision_point_id": inputs.decision_point.decision_point_id,
            "selected_upper_id": (
                inputs.fallback_upper.route_upper_bound_envelope_id
            ),
            "cardinality_evidence_id": inputs.cardinality.cardinality_evidence_id,
            "cardinality_bound_id": (
                inputs.cardinality_bound.ground_fallback_cardinality_bound_id
            ),
            "ground_fallback_cap_profile_id": (
                inputs.cap_profile.ground_fallback_cap_profile_id
            ),
        }
    if inputs.runtime_factory_cardinality is not None:
        payload["runtime_factory_cardinality_id"] = (
            inputs.runtime_factory_cardinality.runtime_factory_cardinality_id
        )
    return content_id(GROUND_FALLBACK_PARENT_BINDING_DOMAIN, payload)


def _system_mounts() -> tuple[str, ...]:
    mounts: list[str] = []
    for path in ("/usr", "/lib", "/lib64"):
        if Path(path).exists():
            mounts.extend(("--ro-bind", path, path))
    return tuple(mounts)


def _isolated_python() -> str:
    candidate = shutil.which("python3", path="/usr/bin:/bin")
    if candidate is None:
        raise Phase3EIsolatedFallbackV1Error(
            "isolated fallback requires system Python under /usr/bin or /bin"
        )
    return str(Path(candidate).resolve())


def _copy_runtime_source(
    destination: Path,
    runtime_source_root: Path | None = None,
) -> None:
    """Stage the complete Python package payload, excluding caches/non-code."""

    source_root = (
        RUNTIME_SOURCE_ROOT
        if runtime_source_root is None
        else Path(runtime_source_root)
    )
    package_source = source_root / "acfqp"
    if package_source.is_symlink() or not package_source.is_dir():
        raise Phase3EIsolatedFallbackV1Error(
            "isolated fallback runtime snapshot is invalid"
        )
    package_target = destination / "acfqp"
    for source in sorted(package_source.rglob("*.py")):
        if source.is_symlink() or not source.is_file():
            raise Phase3EIsolatedFallbackV1Error(
                "isolated fallback runtime snapshot contains a non-regular file"
            )
        relative = source.relative_to(package_source)
        target = package_target / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _authorize(inputs: IsolatedGroundFallbackExecutorInputsV1) -> MarginalRouteDecisionV1:
    decision_result = require_semantic_verification_result_v1(
        inputs.route_decision_result, SemanticRole.ROUTE_DECISION
    )
    upper_result = require_semantic_verification_result_v1(
        inputs.fallback_upper_result, SemanticRole.ROUTE_UPPER
    )
    cardinality_result = require_semantic_verification_result_v1(
        inputs.cardinality_result, SemanticRole.CARDINALITY_EVIDENCE
    )
    if (
        decision_result.outcome != RouteSelection.FALLBACK.value
        or upper_result.outcome != "VALID"
        or cardinality_result.outcome != "VALID"
    ):
        raise Phase3EIsolatedFallbackV1Error(
            "isolated fallback lacks valid route/cardinality/upper authority"
        )
    decision = decision_result.artifact
    if not isinstance(decision, MarginalRouteDecisionV1):
        raise Phase3EIsolatedFallbackV1Error(
            "route-decision authority carries another artifact"
        )
    if (
        decision.selected_route is not RouteSelection.FALLBACK
        or decision.decision_point_id != inputs.decision_point.decision_point_id
        or decision.selected_upper_id
        != inputs.fallback_upper.route_upper_bound_envelope_id
        or upper_result.artifact != inputs.fallback_upper
        or cardinality_result.artifact != inputs.cardinality
    ):
        raise Phase3EIsolatedFallbackV1Error(
            "isolated fallback authority chain is stale or selected another route"
        )
    inputs.fallback_upper.validate_bindings(
        inputs.context, inputs.decision_point, inputs.cardinality
    )
    inputs.cardinality_bound.validate_against_cap(inputs.cap_profile)
    if (
        inputs.cardinality_bound.route_decision_context_id
        != inputs.context.route_decision_context_id
        or inputs.cardinality_bound.decision_point_id
        != inputs.decision_point.decision_point_id
        or inputs.cardinality_bound.ground_fallback_cardinality_bound_id
        not in inputs.cardinality.source_artifact_ids
        or (
            inputs.runtime_factory_cardinality is not None
            and inputs.runtime_factory_cardinality.runtime_factory_cardinality_id
            not in inputs.cardinality_bound.source_artifact_ids
        )
    ):
        raise Phase3EIsolatedFallbackV1Error(
            "isolated fallback cardinality bound is stale"
        )
    expected_counts = dict(
        inputs.cardinality_bound.operational_count_values()
    )
    expected_counts["control.cap_rejections"] = (
        inputs.cardinality_bound.cap_rejection_upper(inputs.cap_profile)
    )
    if inputs.cardinality.counts != tuple(sorted(expected_counts.items())):
        raise Phase3EIsolatedFallbackV1Error(
            "isolated fallback cardinality evidence differs from source projection"
        )
    return decision


def _build_request(
    inputs: IsolatedGroundFallbackExecutorInputsV1,
) -> IsolatedGroundFallbackRequestV1:
    identities = safe_chain_fallback_context_identity_v1(inputs.frozen_world)
    if any(
        getattr(inputs.context, name) != identities[name]
        for name in ("structural_id", "query_id", "build_epoch_id")
    ):
        raise Phase3EIsolatedFallbackV1Error(
            "fallback context does not bind the frozen safe-chain world"
        )
    query = inputs.frozen_world.queries[1].query
    return IsolatedGroundFallbackRequestV1(
        inputs.context.route_decision_context_id,
        inputs.decision_point.decision_point_id,
        inputs.route_decision_result.artifact.route_decision_id,
        inputs.fallback_upper.route_upper_bound_envelope_id,
        inputs.context.route_attempt_id,
        identities["structural_id"],
        identities["query_id"],
        identities["build_epoch_id"],
        identities["bound_ground_action_catalogue_id"],
        identities["portable_rapm_id"],
        inputs.frozen_world.source_manifest_sha256,
        inputs.frozen_world.queries[1].query_key,
        Fraction(query.delta),
        inputs.cap_profile.to_dict(),
        FALLBACK_ISOLATION_PROFILE_ID,
    )


def _strict_attestation(
    document: Mapping[str, Any],
    *,
    request: IsolatedGroundFallbackRequestV1,
    request_raw: bytes,
    output_document: Mapping[str, Any],
    output_raw: bytes,
    runtime_measurement: tuple[int, str, tuple[str, ...]],
    bundle_measurement: tuple[int, str, tuple[str, ...]],
) -> int:
    expected = {
        "schema", "schema_version", "request_id", "output_id",
        "request_sha256", "output_sha256", "runtime_source_tree_sha256",
        "runtime_source_tree_bytes", "runtime_source_files",
        "phase3c_bundle_tree_sha256", "phase3c_bundle_bytes",
        "phase3c_bundle_files", "input_regular_files",
        "output_regular_files_before", "isolation_backend",
        "network_namespace_unshared", "python_site_disabled",
        "project_checkout_visible", "visible_forbidden_roots",
        "loaded_acfqp_modules", "loaded_module_origins",
        "unexpected_module_origins", "working_set_limit_bytes",
        "peak_working_bytes", "python_implementation", "python_version",
        "python_executable", "hash_seed", "official_execution_allowed",
        "attestation_id",
    }
    require_exact_fields(document, expected, context="isolated fallback attestation")
    payload = dict(document)
    attestation_id = payload.pop("attestation_id")
    runtime_bytes, runtime_sha, runtime_files = runtime_measurement
    bundle_bytes, bundle_sha, bundle_files = bundle_measurement
    checks = (
        document["schema"] == ATTESTATION_SCHEMA,
        document["schema_version"] == "1.0.0",
        attestation_id
        == content_id(GROUND_FALLBACK_ISOLATED_ATTESTATION_DOMAIN, payload),
        document["request_id"] == request.request_id,
        document["output_id"] == output_document["output_id"],
        document["request_sha256"] == hashlib.sha256(request_raw).hexdigest(),
        document["output_sha256"] == hashlib.sha256(output_raw).hexdigest(),
        document["runtime_source_tree_sha256"] == runtime_sha,
        document["runtime_source_tree_bytes"] == runtime_bytes,
        document["runtime_source_files"] == list(runtime_files),
        document["phase3c_bundle_tree_sha256"] == bundle_sha,
        document["phase3c_bundle_bytes"] == bundle_bytes,
        document["phase3c_bundle_files"] == list(bundle_files),
        document["input_regular_files"] == ["request.json"],
        document["output_regular_files_before"] == [],
        document["isolation_backend"]
        == "bubblewrap_mount_and_network_namespace",
        document["network_namespace_unshared"] is True,
        document["python_site_disabled"] is True,
        document["project_checkout_visible"] is False,
        document["visible_forbidden_roots"] == [],
        type(document["loaded_acfqp_modules"]) is list,
        bool(document["loaded_acfqp_modules"]),
        type(document["loaded_module_origins"]) is list,
        bool(document["loaded_module_origins"]),
        document["unexpected_module_origins"] == [],
        document["working_set_limit_bytes"] == FALLBACK_WORKING_BYTES_CAP,
        document["hash_seed"] == "0",
        document["official_execution_allowed"] is False,
    )
    peak = document["peak_working_bytes"]
    if not all(checks) or type(peak) is not int or not 0 < peak <= FALLBACK_WORKING_BYTES_CAP:
        raise Phase3EIsolatedFallbackV1Error(
            "isolated fallback runtime attestation failed strict replay"
        )
    return peak


def _run_worker(
    inputs: IsolatedGroundFallbackExecutorInputsV1,
    request: IsolatedGroundFallbackRequestV1,
    registry: CounterRegistryV1,
    controller: FailClosedAccessController,
    recorder: NativeCounterRecorderV1,
    runtime_source_root: Path | None = None,
) -> GroundFallbackExecutionV1:
    bubblewrap = shutil.which("bwrap")
    if bubblewrap is None:
        raise Phase3EIsolatedFallbackV1Error(
            "isolated fallback requires bubblewrap"
        )
    bundle = Path(inputs.frozen_world.source_bundle).resolve()
    with tempfile.TemporaryDirectory(prefix="acfqp-phase3e-fallback-") as temporary:
        root = Path(temporary)
        runtime_root = root / "runtime-source"
        input_root = root / "input"
        output_root = root / "output"
        runtime_root.mkdir()
        input_root.mkdir()
        output_root.mkdir()
        _copy_runtime_source(runtime_root, runtime_source_root)
        request_raw = canonical_json_bytes(request.to_dict())
        request_path = input_root / "request.json"
        request_path.write_bytes(request_raw)
        runtime_measurement = _tree_measurement(runtime_root)
        bundle_measurement = _tree_measurement(bundle)
        if (
            runtime_measurement[0] > FALLBACK_RUNTIME_SOURCE_BYTES_CAP
            or bundle_measurement[0] > FALLBACK_FROZEN_BUNDLE_BYTES_CAP
            or len(request_raw) > FALLBACK_REQUEST_BYTES_CAP
        ):
            raise Phase3EIsolatedFallbackV1Error(
                "selected fallback payload exceeds its preregistered resource cap"
            )
        staged = runtime_measurement[0] + bundle_measurement[0] + len(request_raw)
        recorder.add("io.read_bytes", staged)
        recorder.add("io.staged_bytes", staged)
        recorder.observe_peak("io.mounted_bytes_peak", staged)
        recorder.observe_peak(
            "memory.working_bytes_peak", FALLBACK_WORKING_BYTES_CAP
        )
        output_path = output_root / "result.json"
        attestation_path = output_root / "attestation.json"
        controller.record(
            AccessOperation.FALLBACK_WORKER_LAUNCH, AccessRouteScope.FALLBACK
        )
        recorder.add("process.launches")
        try:
            process = subprocess.run(
                (
                    bubblewrap,
                    "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
                    *_system_mounts(),
                    "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                    "--ro-bind", str(runtime_root), "/runtime-source",
                    "--ro-bind", str(bundle), "/phase3c",
                    "--ro-bind", str(input_root), "/input",
                    "--dir", "/output", "--bind", str(output_root), "/output",
                    "--chdir", "/output",
                    "--setenv", "PATH", "/usr/bin:/bin",
                    "--setenv", "LANG", "C.UTF-8",
                    "--setenv", "PYTHONHASHSEED", "0",
                    "--setenv", "ACFQP_FORBIDDEN_ROOTS", str(PROJECT_ROOT),
                    _isolated_python(), "-I", "-B", "-S",
                    "/runtime-source/acfqp/phase3e_fallback_runtime_v1.py",
                    "--runtime-source", "/runtime-source",
                    "--phase3c-bundle", "/phase3c",
                    "--request", "/input/request.json",
                    "--output", "/output/result.json",
                    "--attestation", "/output/attestation.json",
                ),
                cwd=output_root,
                env={"PATH": "/usr/bin:/bin"},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
                check=False,
            )
        except Exception:
            recorder.add("process.exit_failures")
            raise
        if process.returncode != 0 or process.stdout or process.stderr:
            recorder.add("process.exit_failures")
            raise Phase3EIsolatedFallbackV1Error(
                "isolated fallback worker failed: "
                f"rc={process.returncode}, stdout={process.stdout!r}, "
                f"stderr={process.stderr!r}"
            )
        recorder.add("process.exit_successes")
        output_raw = output_path.read_bytes()
        attestation_raw = attestation_path.read_bytes()
        output = loads_canonical_json(output_raw)
        attestation = loads_canonical_json(attestation_raw)
        if not isinstance(output, Mapping) or not isinstance(attestation, Mapping):
            raise Phase3EIsolatedFallbackV1Error(
                "isolated fallback output roots must be objects"
            )
        require_exact_fields(
            output,
            {
                "schema", "schema_version", "request_id", "ground_fallback_result",
                "work_vector", "output_id",
            },
            context="isolated fallback output",
        )
        output_payload = dict(output)
        output_id = output_payload.pop("output_id")
        if (
            output["schema"] != OUTPUT_SCHEMA
            or output["schema_version"] != "1.0.0"
            or output["request_id"] != request.request_id
            or output_id
            != content_id(GROUND_FALLBACK_ISOLATED_OUTPUT_DOMAIN, output_payload)
        ):
            raise Phase3EIsolatedFallbackV1Error(
                "isolated fallback output schema/content ID mismatch"
            )
        peak = _strict_attestation(
            attestation,
            request=request,
            request_raw=request_raw,
            output_document=output,
            output_raw=output_raw,
            runtime_measurement=runtime_measurement,
            bundle_measurement=bundle_measurement,
        )
        total_output = len(output_raw) + len(attestation_raw)
        read = staged + total_output
        mounted = staged + total_output
        if (
            total_output > FALLBACK_OUTPUT_BYTES_CAP
            or staged > FALLBACK_STAGED_BYTES_UPPER
            or read > FALLBACK_READ_BYTES_UPPER
            or mounted > FALLBACK_MOUNTED_BYTES_UPPER
        ):
            raise Phase3EIsolatedFallbackV1Error(
                "isolated fallback actual I/O exceeds its preregistered upper"
            )
        recorder.add("io.read_bytes", total_output)
        recorder.add("io.output_bytes", total_output)
        recorder.observe_peak("io.mounted_bytes_peak", mounted)
        recorder.observe_peak("memory.working_bytes_peak", peak)

        raw_result = GroundFallbackResultV1.from_dict(
            output["ground_fallback_result"]
        )
        raw_work = WorkVectorV1.from_dict(output["work_vector"], registry)
        registry.validate_vector(raw_work)
        if (
            raw_result.work_vector_id != raw_work.work_vector_id
            or raw_result.route_decision_context_id
            != inputs.context.route_decision_context_id
            or raw_result.decision_point_id != inputs.decision_point.decision_point_id
            or raw_result.route_attempt_id != inputs.context.route_attempt_id
            or raw_result.query_id != inputs.context.query_id
            or raw_result.ground_fallback_cap_profile_id
            != inputs.cap_profile.ground_fallback_cap_profile_id
            or raw_result.route_decision_id != request.route_decision_id
            or raw_result.selected_upper_id != request.selected_upper_id
        ):
            raise Phase3EIsolatedFallbackV1Error(
                "isolated worker result differs from its frozen request"
            )
        raw_values = raw_work.values
        for path in (
            "process.launches", "process.exit_successes", "process.exit_failures",
            "io.read_bytes", "io.staged_bytes", "io.output_bytes",
            "io.mounted_bytes_peak", "memory.working_bytes_peak",
        ):
            if raw_values[path] != 0:
                raise Phase3EIsolatedFallbackV1Error(
                    "worker attempted to self-report supervisor resource counters"
                )
        supervisor_paths = {
            "process.launches", "process.exit_successes", "process.exit_failures",
            "io.read_bytes", "io.staged_bytes", "io.output_bytes",
            "io.mounted_bytes_peak", "memory.working_bytes_peak",
        }
        for path, value in raw_values.items():
            if path in supervisor_paths or value == 0:
                continue
            if registry.by_path[path].reducer is ReducerEnum.MAX:
                recorder.observe_peak(path, value)
            else:
                recorder.add(path, value)
        final_work = recorder.seal().work_vector
        final_result = dataclasses.replace(
            raw_result,
            work_vector_id=final_work.work_vector_id,
        )
        selected_policy = (
            reconstruct_safe_chain_policy_from_signature_v1(
                inputs.frozen_world, final_result.selected_policy_signature
            )
            if final_result.outcome is GroundFallbackOutcome.FEASIBLE_CERTIFIED
            else None
        )
        execution = GroundFallbackExecutionV1(
            final_result, final_work, selected_policy
        )
        upper = dict(
            inputs.cardinality_bound.operational_upper_values(
                inputs.cap_profile, registry
            )
        )
        exceeded = tuple(
            path for path, actual in final_work.values.items()
            if path in upper and actual > upper[path]
        )
        if exceeded:
            raise Phase3EIsolatedFallbackV1Error(
                "isolated fallback actual WorkVector exceeds pre-execution upper: "
                + ", ".join(exceeded)
            )
        return _seal_isolated_ground_fallback_execution_v1(
            execution,
            constraint_delta=request.constraint_delta,
            isolated_request_id=request.request_id,
            isolated_output_id=output_id,
            isolated_attestation_id=attestation["attestation_id"],
        )


def _verify_fallback_route_semantics_v1(
    *,
    inputs: IsolatedGroundFallbackExecutorInputsV1,
    semantic_execution: GroundFallbackExecutionV1,
    binding: AttestationContextV1,
    verification_records: tuple[CounterRecordV1, ...],
    registry: CounterRegistryV1,
) -> tuple[object, ...]:
    """Exact constructor-owned fallback dispatcher; never reruns the solver."""

    if (
        not isinstance(semantic_execution, GroundFallbackExecutionV1)
        or not isinstance(binding, AttestationContextV1)
        or type(verification_records) is not tuple
        or len(verification_records) != 1
        or not isinstance(verification_records[0], CounterRecordV1)
    ):
        raise Phase3EIsolatedFallbackV1Error(
            "deferred fallback semantic dispatcher received an invalid target set"
        )
    return (
        verify_ground_fallback_semantics_v1(
            semantic_execution,
            cap_profile=inputs.cap_profile,
            binding=binding,
            verification_work_record=verification_records[0],
            registry=registry,
        ),
    )


def _finalize_isolated_fallback_execution_v1(
    *,
    inputs: IsolatedGroundFallbackExecutorInputsV1,
    controller: FailClosedAccessController,
    execution: GroundFallbackExecutionV1,
    registry: CounterRegistryV1,
    profile: ComparisonProfileV1,
    defer_semantics: bool,
) -> Phase3ERouteExecutionV1:
    """Bind a successful isolated output to access and semantic authority."""

    # These selected-route events are attested by the strict worker output,
    # not produced by a host kernel replay.  Recording them after process
    # return preserves FQ13 ordering while keeping access/counter replay exact.
    for _ in range(execution.work_vector.value("fallback.ground_steps")):
        controller.record(AccessOperation.KERNEL_STEP, AccessRouteScope.FALLBACK)
        controller.record(
            AccessOperation.GROUND_OUTCOME_ENUMERATION,
            AccessRouteScope.FALLBACK,
        )
    controller.record(
        AccessOperation.FALLBACK_RESULT_ARTIFACT,
        AccessRouteScope.FALLBACK,
        artifact_id=execution.result.ground_fallback_result_id,
    )
    binding = AttestationContextV1(
        inputs.context,
        inputs.decision_point.decision_point_id,
        TypedNotApplicable("direct fallback has no local transaction"),
        len(controller.snapshot().events) + 1,
    )
    semantic_results: tuple[object, ...]
    if defer_semantics:
        semantic_results = ()
    else:
        spec = semantic_verifier_spec_v1(SemanticRole.GROUND_FALLBACK)
        verification_record = CounterRecordV1.observe(
            registry,
            spec.verification_counter_path,
            1,
            recorder_id="phase3e_isolated_ground_fallback_semantic_verifier_v1",
        )
        semantic_results = _verify_fallback_route_semantics_v1(
            inputs=inputs,
            semantic_execution=execution,
            binding=binding,
            verification_records=(verification_record,),
            registry=registry,
        )
    return adapt_ground_fallback_execution_v1(
        execution,
        registry=registry,
        comparison_profile=profile,
        semantic_verification_results=semantic_results,
        semantic_verification_deferred=defer_semantics,
    )


def _raise_with_partial_fallback_work_v1(
    error: Exception,
    recorder: NativeCounterRecorderV1,
) -> None:
    if getattr(error, "partial_recorded_work", None) is not None:
        raise error
    partial = recorder.seal_route_failure()
    try:
        setattr(error, "partial_recorded_work", partial)
    except (AttributeError, TypeError):
        wrapped = Phase3EIsolatedFallbackV1Error(
            f"isolated fallback selected-route execution failed: {error}"
        )
        wrapped.partial_recorded_work = partial
        raise wrapped from error
    raise error


@dataclass(frozen=True, slots=True)
class AuthorizedIsolatedGroundFallbackExecutorV1:
    """Runner callable implementing the official isolated fallback profile."""

    inputs: IsolatedGroundFallbackExecutorInputsV1
    registry: CounterRegistryV1 | None = None
    comparison_profile: ComparisonProfileV1 | None = None
    # Historical callers use ``None``.  The sealed profile injects a verified
    # route-private runtime-tree lease after decision freeze.
    runtime_source_root: Path | None = None
    runtime_tree_id: str | None = None
    executor_recipe_id: str | None = None

    def __call__(
        self,
        prepared: PreparedPhase3ERunV1,
        controller: FailClosedAccessController,
        recorder: NativeCounterRecorderV1,
    ) -> Phase3ERouteExecutionV1:
        registry = self.registry or official_counter_registry_v1()
        profile = self.comparison_profile or official_comparison_profile_v1(registry)
        inputs = self.inputs
        owned_recorder: NativeCounterRecorderV1 | None = None
        _authorize(inputs)
        if (
            prepared.context != inputs.context
            or prepared.decision_point != inputs.decision_point
            or prepared.authorization.decision_result is not inputs.route_decision_result
            or prepared.authorization.selected_upper_result
            is not inputs.fallback_upper_result
        ):
            raise Phase3EIsolatedFallbackV1Error(
                "prepared run differs from isolated fallback authority inputs"
            )
        if self.runtime_source_root is not None and (
            self.runtime_tree_id is None
            or self.executor_recipe_id is None
            or getattr(prepared, "runtime_tree_id", None) != self.runtime_tree_id
            or getattr(prepared, "executor_recipe_id", None)
            != self.executor_recipe_id
        ):
            raise Phase3EIsolatedFallbackV1Error(
                "sealed fallback runtime IDs differ from the prepared run"
            )
        if (
            not isinstance(recorder, NativeCounterRecorderV1)
            or recorder.route_kind is not RouteKindEnum.DIRECT_FALLBACK
            or recorder.work_scope is not ActualWorkScope.MARGINAL_ROUTE_EXECUTION
            or any(recorder.values.values())
        ):
            raise Phase3EIsolatedFallbackV1Error(
                "isolated fallback requires an untouched fallback recorder"
            )
        freeze = controller.freeze_attestation
        if freeze is None or freeze.selected_route is not RouteSelection.FALLBACK:
            raise Phase3EIsolatedFallbackV1Error(
                "isolated fallback cannot launch before a frozen FALLBACK decision"
            )
        owned_recorder = NativeCounterRecorderV1(
            subject_id=inputs.context.route_attempt_id,
            route_kind=RouteKindEnum.DIRECT_FALLBACK,
            work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            registry=registry,
            comparison_profile=profile,
            recorder_id=RECORDER_ID,
        )
        request = _build_request(inputs)
        try:
            execution = _run_worker(
                inputs,
                request,
                registry,
                controller,
                owned_recorder,
                self.runtime_source_root,
            )
            return _finalize_isolated_fallback_execution_v1(
                inputs=inputs,
                controller=controller,
                execution=execution,
                registry=registry,
                profile=profile,
                defer_semantics=prepared.two_stage_accounting_profile,
            )
        except Exception as error:
            _raise_with_partial_fallback_work_v1(error, owned_recorder)
            raise AssertionError("partial fallback failure helper returned")


@dataclass(frozen=True, slots=True)
class IsolatedFallbackPostFreezeConstructorV1:
    """Create the fallback supervisor only from a verified runtime lease."""

    inputs: IsolatedGroundFallbackExecutorInputsV1
    registry: CounterRegistryV1 | None = None
    comparison_profile: ComparisonProfileV1 | None = None

    @property
    def runtime_factory_cardinality_v1(self) -> RuntimeFactoryCardinalityV1 | None:
        return self.inputs.runtime_factory_cardinality

    @property
    def executor_configuration_id_v1(self) -> str:
        return isolated_ground_fallback_executor_configuration_id_v1(self.inputs)

    @property
    def selected_upper_id_v1(self) -> str:
        return self.inputs.fallback_upper.route_upper_bound_envelope_id

    @property
    def selected_cardinality_evidence_id_v1(self) -> str:
        return self.inputs.cardinality.cardinality_evidence_id

    @property
    def selected_cardinality_source_artifact_ids_v1(self) -> tuple[str, ...]:
        return self.inputs.cardinality_bound.source_artifact_ids

    def deferred_route_verifier_v1(
        self,
        execution: Phase3ERouteExecutionV1,
        binding: object,
        verification_records: tuple[CounterRecordV1, ...],
    ) -> tuple[object, ...]:
        """Replay exact fallback semantics after charge-plan freeze."""

        if (
            not isinstance(execution, Phase3ERouteExecutionV1)
            or not isinstance(binding, AttestationContextV1)
            or not isinstance(
                execution.semantic_execution, GroundFallbackExecutionV1
            )
        ):
            raise Phase3EIsolatedFallbackV1Error(
                "deferred fallback verifier received a foreign route execution"
            )
        registry = self.registry or official_counter_registry_v1()
        return _verify_fallback_route_semantics_v1(
            inputs=self.inputs,
            semantic_execution=execution.semantic_execution,
            binding=binding,
            verification_records=verification_records,
            registry=registry,
        )

    def deferred_route_verifier_step_v1(
        self,
        execution: Phase3ERouteExecutionV1,
        binding: object,
        role: object,
        verification_record: CounterRecordV1,
        prior_results: tuple[object, ...],
    ) -> object:
        if role is not SemanticRole.GROUND_FALLBACK or prior_results:
            raise Phase3EIsolatedFallbackV1Error(
                "incremental fallback verifier received an invalid obligation"
            )
        return self.deferred_route_verifier_v1(
            execution, binding, (verification_record,)
        )[0]

    def construct_after_freeze(
        self,
        grant: PostFreezeConstructionGrantV1,
    ) -> AuthorizedIsolatedGroundFallbackExecutorV1:
        if type(grant) is not PostFreezeConstructionGrantV1:
            raise Phase3EIsolatedFallbackV1Error(
                "sealed fallback construction requires a typed post-freeze grant"
            )
        recipe: ExecutorRecipeV1 = grant.recipe
        if (
            recipe.selected_route is not RouteSelection.FALLBACK
            or recipe.executor_semantics_id
            != ISOLATED_FALLBACK_EXECUTOR_SEMANTICS_ID
            or recipe.entrypoint_relative_path
            != ISOLATED_FALLBACK_RUNTIME_ENTRYPOINT
            or recipe.executor_configuration_id
            != isolated_ground_fallback_executor_configuration_id_v1(self.inputs)
        ):
            raise Phase3EIsolatedFallbackV1Error(
                "sealed fallback recipe differs from its trusted authority inputs"
            )
        # The sealed factory owns the exact pre/post lease verification and
        # its WorkVector.  A second constructor-side replay would be unmetered
        # duplicate runtime I/O.
        return AuthorizedIsolatedGroundFallbackExecutorV1(
            self.inputs,
            self.registry,
            self.comparison_profile,
            grant.runtime_tree.root,
            recipe.runtime_tree_id,
            recipe.executor_recipe_id,
        )


__all__ = [
    "AuthorizedIsolatedGroundFallbackExecutorV1",
    "ISOLATED_FALLBACK_EXECUTOR_SEMANTICS_ID",
    "ISOLATED_FALLBACK_RUNTIME_ENTRYPOINT",
    "IsolatedGroundFallbackExecutorInputsV1",
    "IsolatedFallbackPostFreezeConstructorV1",
    "Phase3EIsolatedFallbackV1Error",
    "isolated_ground_fallback_executor_configuration_id_v1",
]
