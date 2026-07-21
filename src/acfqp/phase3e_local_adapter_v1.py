"""Post-freeze adapter for the real Phase-3D safe-chain local route.

The adapter consumes a frozen Phase-3E LOCAL decision, then and only then
materializes the authorized slice, compiles the sparse capability, launches
the existing bubblewrap worker with ``operational_no_full_replay=True``,
stitches its overlay, and runs the sound ground post-audit.  Every ground step
is mirrored into the FQ13 access log and every registered native operation is
recorded in the selected transaction's WorkVector.

This remains a scoped, non-official safe-chain trust root.  The isolated worker
attests its finite working-set limit, which is charged as peak working capacity;
the in-process compiler, stitcher, and post-auditor are still trusted components
and the official Phase 3E completeness/economics locks remain closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
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
    RouteKindEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.local_recovery import PatchedAuditKernelView, audit_hybrid_policy
from acfqp.general_local_solver import (
    AUTHORIZED_EXHAUSTED,
    CERTIFIED,
    SEARCH_CAP_EXHAUSTED,
)
from acfqp.native_recorder_v1 import NativeCounterRecorderV1
from acfqp.phase3d import (
    PROJECT_ROOT,
    SAFE_CHAIN_SEARCH_LIMITS,
    SafeChainPreparedEstimateContext,
    _EXECUTABLE_PREPARED_ESTIMATE_DERIVATION_AUTHORITY,
    _canonical_bytes,
    _derive_safe_chain_access_logged_estimate_v1,
    _execute_safe_chain_local_preparation,
    _general_request,
    _overlay_from_result,
    _run_fresh_general_solver,
)
from acfqp.phase3e_ids import (
    PHASE3D_LOCAL_PARENT_BINDING_DOMAIN,
    content_id,
)
from acfqp.phase3e_local_preselection_v1 import (
    LOCAL_MOUNTED_BYTES_UPPER,
    LOCAL_OUTPUT_BYTES_UPPER,
    LOCAL_READ_BYTES_UPPER,
    LOCAL_STAGED_BYTES_UPPER,
    LOCAL_WORKING_BYTES_UPPER,
    SafeChainLocalCardinalityBoundV1,
    safe_chain_local_context_identity_v1,
    safe_chain_local_selected_plan_id_v1,
    safe_chain_local_threshold_profile_id_v1,
)
from acfqp.phase3e_local_semantics_v1 import (
    FrozenThresholdProfileV1,
    LocalSolverOutcome,
    LocalTransactionResultV1,
    PostAuditCertificateV1,
    PostAuditOutcome,
    TrustedLocalExecutionV1,
    _seal_trusted_execution_v1,
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
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TransactionV1,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    require_semantic_verification_result_v1,
    semantic_verifier_spec_v1,
    verify_local_transaction_result_semantics_v1,
    verify_post_audit_semantics_v1,
)


class Phase3ELocalAdapterV1Error(Phase3ERunnerV1Error):
    """The local adapter was invoked before freeze or with stale authority."""


SAFE_CHAIN_LOCAL_EXECUTOR_SEMANTICS_ID = (
    "phase3e-safe-chain-selected-local-executor-v1"
)
SAFE_CHAIN_LOCAL_RUNTIME_ENTRYPOINT = "acfqp/general_local_runtime.py"


def _binding_id(role: str, legacy_id: Any) -> str:
    return content_id(
        PHASE3D_LOCAL_PARENT_BINDING_DOMAIN,
        {
            "schema": "acfqp.phase3d_local_parent_binding.v1",
            "role": role,
            "legacy_id": legacy_id,
        },
    )


class _AccessLoggedLocalKernelV1:
    """Delegate selected-route transitions while recording exact access."""

    def __init__(self, kernel: Any, controller: FailClosedAccessController) -> None:
        self._kernel = kernel
        self._controller = controller
        self.step_calls = 0
        self.positive_outcome_rows = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._kernel, name)

    def step(self, state: Any, action: Any) -> Any:
        self._controller.record(AccessOperation.KERNEL_STEP, AccessRouteScope.LOCAL)
        self.step_calls += 1
        outcomes = self._kernel.step(state, action)
        self._controller.record(
            AccessOperation.GROUND_OUTCOME_ENUMERATION,
            AccessRouteScope.LOCAL,
        )
        self.positive_outcome_rows += sum(
            Fraction(getattr(row, "probability", 0)) > 0 for row in outcomes
        )
        return outcomes


@dataclass(frozen=True, slots=True)
class SafeChainLocalExecutorInputsV1:
    prepared_local: SafeChainPreparedEstimateContext
    context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    transaction: TransactionV1
    local_upper: RouteUpperBoundEnvelopeV1
    cardinality: CardinalityEvidenceV1
    cardinality_bound: SafeChainLocalCardinalityBoundV1
    cap_profile: RouteCapProfileV1
    threshold_profile: FrozenThresholdProfileV1
    route_decision_result: object
    local_upper_result: object
    causal_result: object
    cardinality_result: object
    runtime_factory_cardinality: RuntimeFactoryCardinalityV1 | None = None


def _require_authority(inputs: SafeChainLocalExecutorInputsV1) -> None:
    decision = require_semantic_verification_result_v1(
        inputs.route_decision_result, SemanticRole.ROUTE_DECISION
    )
    upper = require_semantic_verification_result_v1(
        inputs.local_upper_result, SemanticRole.ROUTE_UPPER
    )
    causal = require_semantic_verification_result_v1(
        inputs.causal_result, SemanticRole.CAUSAL_SEARCH
    )
    cardinality = require_semantic_verification_result_v1(
        inputs.cardinality_result, SemanticRole.CARDINALITY_EVIDENCE
    )
    if (
        decision.outcome != RouteSelection.LOCAL.value
        or decision.artifact.selected_upper_id
        != inputs.local_upper.route_upper_bound_envelope_id
        or upper.artifact != inputs.local_upper
        or causal.artifact.causal_evidence_id
        != inputs.decision_point.causal_evidence_id
        or cardinality.artifact != inputs.cardinality
    ):
        raise Phase3ELocalAdapterV1Error(
            "local execution authority does not bind the selected LOCAL route"
        )


def _validate_inputs(inputs: SafeChainLocalExecutorInputsV1) -> None:
    _require_authority(inputs)
    prepared = inputs.prepared_local
    if not isinstance(prepared, SafeChainPreparedEstimateContext):
        raise Phase3ELocalAdapterV1Error(
            "safe-chain local executor requires prepared Phase-3D estimate context"
        )
    identities = safe_chain_local_context_identity_v1(prepared.world)
    context = inputs.context
    if any(
        getattr(context, field) != identities[field]
        for field in ("structural_id", "query_id", "build_epoch_id")
    ):
        raise Phase3ELocalAdapterV1Error(
            "local context does not bind the frozen safe-chain parent"
        )
    if (
        context.selected_plan_id != safe_chain_local_selected_plan_id_v1(prepared)
        or context.threshold_profile_id
        != safe_chain_local_threshold_profile_id_v1(prepared)
        or inputs.threshold_profile.threshold_profile_id
        != context.threshold_profile_id
        or inputs.threshold_profile.query_id != context.query_id
    ):
        raise Phase3ELocalAdapterV1Error(
            "local plan/threshold identity differs from preselection authority"
        )
    point = inputs.decision_point
    transaction = inputs.transaction
    if (
        point.route_decision_context_id != context.route_decision_context_id
        or transaction.logical_occurrence_id != context.logical_occurrence_id
        or transaction.route_attempt_id != context.route_attempt_id
        or transaction.decision_point_id != point.decision_point_id
        or transaction.transaction_index != point.transaction_index
        or transaction.frontier_snapshot_id != point.frontier_snapshot_id
        or transaction.route_cap_profile_id != inputs.cap_profile.route_cap_profile_id
        or inputs.local_upper.transaction_id != transaction.transaction_id
        or inputs.local_upper.cardinality_evidence_id
        != inputs.cardinality.cardinality_evidence_id
        or inputs.cardinality_bound.transaction_id != transaction.transaction_id
        or (
            inputs.runtime_factory_cardinality is not None
            and inputs.runtime_factory_cardinality.runtime_factory_cardinality_id
            not in inputs.cardinality_bound.source_artifact_ids
        )
    ):
        raise Phase3ELocalAdapterV1Error(
            "local context/point/transaction/upper/cardinality chain is stale"
        )
    inputs.cardinality_bound.validate_against_cap(inputs.cap_profile)


def _compiler_native_counts(evidence: Mapping[str, Any]) -> tuple[int, int, int]:
    recovery = evidence["recovery_input_compilation"]
    enumeration = evidence["enumeration"]
    recovery_counts = recovery["counts"]
    enum_counts = enumeration["counts"]
    input_records = (
        int(evidence["source_node_count"])
        + int(evidence["source_abstract_realization_row_count"])
        + int(recovery_counts["slice_cells"])
        + int(recovery_counts["slice_members"])
        + int(recovery_counts["slice_actions"])
        + int(recovery_counts["slice_successor_rows"])
    )
    expanded_forms = (
        int(evidence["source_reward_form_count"])
        + int(evidence["source_failure_form_count"])
        + int(evidence["retained_reward_form_count"])
        + int(evidence["retained_failure_form_count"])
    )
    domain_assignments = int(enum_counts["reward_domain_assignments"]) + int(
        enum_counts["failure_domain_assignments"]
    )
    return input_records, expanded_forms, domain_assignments


def _worker_io_counts(
    capability: Mapping[str, Any],
    sparse_slice: Mapping[str, Any],
    request: Mapping[str, Any],
    result: Mapping[str, Any],
    attestation: Mapping[str, Any],
    runtime_source_root: Path | None = None,
) -> tuple[int, int, int, int, int]:
    input_bytes = sum(
        len(_canonical_bytes(document))
        for document in (capability, sparse_slice, request)
    )
    source_root = PROJECT_ROOT / "src" if runtime_source_root is None else Path(
        runtime_source_root
    )
    runtime_bytes = sum(
        (source_root / "acfqp" / name).stat().st_size
        for name in ("general_local_solver.py", "general_local_runtime.py")
    )
    output_bytes = len(_canonical_bytes(result)) + len(_canonical_bytes(attestation))
    # Host validation reads the two newly written outputs as well as the three
    # immutable worker inputs.  Staging accounts runtime+input copies once.
    read_bytes = input_bytes + output_bytes
    staged_bytes = input_bytes + runtime_bytes
    mounted_peak = staged_bytes + output_bytes
    # The comparison profile permits a verified peak or the frozen working-set
    # cap.  Charging the attested cap keeps the legacy Phase 3D attestation
    # replay-exact while remaining a sound Phase 3E capacity account.
    working_peak = int(attestation["working_set_limit_bytes"])
    return read_bytes, staged_bytes, output_bytes, mounted_peak, working_peak


def _worker_input_resource_counts(
    capability: Mapping[str, Any],
    sparse_slice: Mapping[str, Any],
    request: Mapping[str, Any],
    runtime_source_root: Path | None = None,
) -> tuple[int, int]:
    """Return conservative pre-launch read and staging traffic.

    These bytes are known before the process launch and therefore remain
    chargeable even if the isolated child or its supervisor fails before
    producing an output artifact.
    """

    input_bytes = sum(
        len(_canonical_bytes(document))
        for document in (capability, sparse_slice, request)
    )
    source_root = PROJECT_ROOT / "src" if runtime_source_root is None else Path(
        runtime_source_root
    )
    runtime_bytes = sum(
        (source_root / "acfqp" / name).stat().st_size
        for name in ("general_local_solver.py", "general_local_runtime.py")
    )
    return input_bytes, input_bytes + runtime_bytes


def safe_chain_local_executor_configuration_id_v1(
    inputs: SafeChainLocalExecutorInputsV1,
) -> str:
    """Bind a sealed executor recipe to one exact local authority chain."""

    payload = {
            "schema": "acfqp.phase3e_safe_chain_local_executor_configuration.v1",
            "route_decision_context_id": (
                inputs.context.route_decision_context_id
            ),
            "decision_point_id": inputs.decision_point.decision_point_id,
            "transaction_id": inputs.transaction.transaction_id,
            "selected_upper_id": (
                inputs.local_upper.route_upper_bound_envelope_id
            ),
            "cardinality_evidence_id": inputs.cardinality.cardinality_evidence_id,
            "route_cap_profile_id": inputs.cap_profile.route_cap_profile_id,
            "threshold_profile_id": inputs.threshold_profile.threshold_profile_id,
        }
    if inputs.runtime_factory_cardinality is not None:
        payload["runtime_factory_cardinality_id"] = (
            inputs.runtime_factory_cardinality.runtime_factory_cardinality_id
        )
    return content_id(PHASE3D_LOCAL_PARENT_BINDING_DOMAIN, payload)


def _verify_local_route_semantics_v1(
    *,
    inputs: SafeChainLocalExecutorInputsV1,
    semantic_execution: TrustedLocalExecutionV1,
    binding: AttestationContextV1,
    verification_records: tuple[CounterRecordV1, ...],
    registry: CounterRegistryV1,
) -> tuple[object, ...]:
    """Exact constructor-owned semantic dispatcher; never reruns the solver."""

    if (
        not isinstance(semantic_execution, TrustedLocalExecutionV1)
        or not isinstance(binding, AttestationContextV1)
        or type(verification_records) is not tuple
        or not all(isinstance(row, CounterRecordV1) for row in verification_records)
    ):
        raise Phase3ELocalAdapterV1Error(
            "deferred local semantic dispatcher received an invalid target set"
        )
    expected_count = 1 + int(semantic_execution.post_audit is not None)
    if len(verification_records) != expected_count:
        raise Phase3ELocalAdapterV1Error(
            "deferred local semantic dispatcher received an invalid target count"
        )
    local_result = verify_local_transaction_result_semantics_v1(
        semantic_execution,
        context=inputs.context,
        decision_point=inputs.decision_point,
        transaction=inputs.transaction,
        cap_profile=inputs.cap_profile,
        binding=binding,
        verification_work_record=verification_records[0],
        registry=registry,
    )
    results: list[object] = [local_result]
    if semantic_execution.post_audit is not None:
        results.append(
            verify_post_audit_semantics_v1(
                semantic_execution,
                local_solver_result=local_result,
                context=inputs.context,
                decision_point=inputs.decision_point,
                transaction=inputs.transaction,
                cap_profile=inputs.cap_profile,
                binding=binding,
                verification_work_record=verification_records[1],
                registry=registry,
            )
        )
    return tuple(results)


@dataclass(frozen=True, slots=True)
class AuthorizedSafeChainLocalExecutorV1:
    """Callable supplied as ``run_phase3e(..., local_executor=...)``."""

    inputs: SafeChainLocalExecutorInputsV1
    registry: CounterRegistryV1 | None = None
    comparison_profile: ComparisonProfileV1 | None = None
    # ``None`` is the historical Phase-3D compatibility path.  The sealed
    # Phase-3E profile always supplies a verified private runtime-tree lease.
    runtime_source_root: Path | None = None
    runtime_tree_id: str | None = None
    executor_recipe_id: str | None = None

    def __call__(
        self,
        prepared: PreparedPhase3ERunV1,
        controller: FailClosedAccessController,
        recorder: NativeCounterRecorderV1,
    ) -> Phase3ERouteExecutionV1:
        owned_recorder: NativeCounterRecorderV1 | None = None
        try:
            registry = self.registry or official_counter_registry_v1()
            profile = self.comparison_profile or official_comparison_profile_v1(
                registry
            )
            owned_recorder = NativeCounterRecorderV1(
                subject_id=self.inputs.transaction.transaction_id,
                route_kind=RouteKindEnum.LOCAL_ATTEMPT,
                work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
                registry=registry,
                comparison_profile=profile,
                recorder_id="phase3e-safe-chain-selected-local-executor-v1",
            )
            return self._execute(
                prepared,
                controller,
                recorder,
                owned_recorder,
                registry,
                profile,
            )
        except Exception as error:
            # Preserve every local operation observed by this adapter.  The
            # runner-owned recorder intentionally stays empty, so exporting
            # this exact failed seal cannot double count the selected attempt.
            if owned_recorder is not None and owned_recorder.sealed_work is None:
                values = owned_recorder.values
                if values["process.launches"] > (
                    values["process.exit_successes"]
                    + values["process.exit_failures"]
                ):
                    owned_recorder.add("process.exit_failures")
                if values["solver.attempts"] > (
                    values["solver.successes"] + values["solver.failures"]
                ):
                    owned_recorder.add("solver.failures")
            if owned_recorder is not None and getattr(
                error, "partial_recorded_work", None
            ) is None:
                partial = owned_recorder.seal_route_failure()
                try:
                    setattr(error, "partial_recorded_work", partial)
                except (AttributeError, TypeError):
                    wrapped = Phase3ELocalAdapterV1Error(
                        f"local selected-route execution failed: {error}"
                    )
                    wrapped.partial_recorded_work = partial
                    raise wrapped from error
            raise

    def _execute(
        self,
        prepared: PreparedPhase3ERunV1,
        controller: FailClosedAccessController,
        recorder: NativeCounterRecorderV1,
        owned_recorder: NativeCounterRecorderV1,
        registry: CounterRegistryV1,
        profile: ComparisonProfileV1,
    ) -> Phase3ERouteExecutionV1:
        inputs = self.inputs
        _validate_inputs(inputs)
        if (
            prepared.context != inputs.context
            or prepared.decision_point != inputs.decision_point
            or prepared.authorization.decision_result is not inputs.route_decision_result
            or prepared.authorization.selected_upper_result is not inputs.local_upper_result
        ):
            raise Phase3ELocalAdapterV1Error(
                "runner preparation differs from local executor authority inputs"
            )
        if self.runtime_source_root is not None and (
            self.runtime_tree_id is None
            or self.executor_recipe_id is None
            or getattr(prepared, "runtime_tree_id", None) != self.runtime_tree_id
            or getattr(prepared, "executor_recipe_id", None)
            != self.executor_recipe_id
        ):
            raise Phase3ELocalAdapterV1Error(
                "sealed local runtime IDs differ from the prepared run"
            )
        if (
            not isinstance(recorder, NativeCounterRecorderV1)
            or recorder.route_kind is not RouteKindEnum.LOCAL_ATTEMPT
            or recorder.work_scope is not ActualWorkScope.MARGINAL_ROUTE_EXECUTION
            or any(recorder.values.values())
        ):
            raise Phase3ELocalAdapterV1Error(
                "local executor requires an untouched LOCAL execution recorder"
            )
        # The adapter owns the selected-route ledger because it must seal that
        # exact vector before minting the local-result/post-audit provenance.
        # Keep the runner's injection recorder untouched; run_phase3e rejects
        # mixed ownership and independently validates this returned vector.
        recorder = owned_recorder
        freeze = controller.freeze_attestation
        if freeze is None or freeze.selected_route is not RouteSelection.LOCAL:
            raise Phase3ELocalAdapterV1Error(
                "local route cannot execute before a frozen LOCAL decision"
            )

        logged_kernel = _AccessLoggedLocalKernelV1(
            inputs.prepared_local.world.kernel, controller
        )
        executable_prepared = _derive_safe_chain_access_logged_estimate_v1(
            inputs.prepared_local,
            access_logged_kernel=logged_kernel,
            authority=_EXECUTABLE_PREPARED_ESTIMATE_DERIVATION_AUTHORITY,
        )

        controller.record(
            AccessOperation.LOCAL_SLICE_MATERIALIZATION,
            AccessRouteScope.LOCAL,
        )
        try:
            local_context = _execute_safe_chain_local_preparation(executable_prepared)
        except Exception:
            recorder.add(
                "local.materialization_ground_steps", logged_kernel.step_calls
            )
            recorder.add(
                "local.materialization_outcome_rows",
                logged_kernel.positive_outcome_rows,
            )
            raise
        material_steps = logged_kernel.step_calls
        material_rows = logged_kernel.positive_outcome_rows
        recorder.add("local.materialization_ground_steps", material_steps)
        recorder.add("local.materialization_outcome_rows", material_rows)
        if (material_steps, material_rows) != (16, 64):
            raise Phase3ELocalAdapterV1Error(
                "safe-chain materialization native counts changed"
            )
        controller.record(
            AccessOperation.LOCAL_CAPABILITY_COMPILATION,
            AccessRouteScope.LOCAL,
        )
        capability_binding_id = _binding_id(
            "compiled_capability", local_context.capability["capability_id"]
        )
        controller.record(
            AccessOperation.LOCAL_CAPABILITY_ARTIFACT,
            AccessRouteScope.LOCAL,
            artifact_id=capability_binding_id,
        )
        compiler_input, compiler_forms, compiler_domains = _compiler_native_counts(
            local_context.capability_evidence
        )
        recorder.add("local.compiler_input_records", compiler_input)
        recorder.add("local.compiler_expanded_forms", compiler_forms)
        recorder.add("local.compiler_domain_assignments", compiler_domains)

        occurrence_id = (
            "phase3e-local-occurrence:" + inputs.transaction.transaction_id
        )
        request = _general_request(
            occurrence_id=occurrence_id,
            capability=local_context.capability,
            ground_slice=local_context.sparse_slice,
            limits=SAFE_CHAIN_SEARCH_LIMITS,
        )
        input_read_bytes, staged_bytes = _worker_input_resource_counts(
            local_context.capability,
            local_context.sparse_slice,
            request,
            self.runtime_source_root,
        )
        recorder.add("io.read_bytes", input_read_bytes)
        recorder.add("io.staged_bytes", staged_bytes)
        recorder.observe_peak("io.mounted_bytes_peak", staged_bytes)
        recorder.observe_peak("memory.working_bytes_peak", LOCAL_WORKING_BYTES_UPPER)
        controller.record(
            AccessOperation.LOCAL_WORKER_LAUNCH,
            AccessRouteScope.LOCAL,
        )
        recorder.add("process.launches")
        recorder.add("solver.attempts")
        worker_result, runtime_attestation = _run_fresh_general_solver(
            local_context.capability,
            local_context.sparse_slice,
            request,
            operational_no_full_replay=True,
            runtime_source_root=self.runtime_source_root,
        )
        recorder.add("process.exit_successes")
        read_bytes, full_staged_bytes, output_bytes, mounted_peak, working_peak = (
            _worker_io_counts(
                local_context.capability,
                local_context.sparse_slice,
                request,
                worker_result,
                runtime_attestation,
                self.runtime_source_root,
            )
        )
        if full_staged_bytes != staged_bytes or read_bytes != (
            input_read_bytes + output_bytes
        ):
            raise Phase3ELocalAdapterV1Error(
                "isolated local resource accounting decomposition changed"
            )
        recorder.add("io.read_bytes", output_bytes)
        recorder.add("io.output_bytes", output_bytes)
        recorder.observe_peak("io.mounted_bytes_peak", mounted_peak)
        recorder.observe_peak("memory.working_bytes_peak", working_peak)
        worker_binding_id = _binding_id(
            "isolated_worker_result", worker_result["result_id"]
        )
        runtime_binding_id = _binding_id(
            "isolated_runtime_attestation", runtime_attestation["attestation_id"]
        )
        controller.record(
            AccessOperation.LOCAL_WORKER_RESULT_ARTIFACT,
            AccessRouteScope.LOCAL,
            artifact_id=worker_binding_id,
        )

        status = worker_result["status"]
        if status == CERTIFIED:
            solver_outcome = LocalSolverOutcome.CANDIDATE_FOUND
        elif status == SEARCH_CAP_EXHAUSTED:
            solver_outcome = LocalSolverOutcome.SEARCH_CAP_EXHAUSTED
        elif status == AUTHORIZED_EXHAUSTED:
            solver_outcome = LocalSolverOutcome.NO_FEASIBLE_ASSIGNMENT
        else:
            raise Phase3ELocalAdapterV1Error(
                f"unregistered general-local worker status {status!r}"
            )
        counters = worker_result["counters"]
        recorder.add("local.solver_subset_evaluations", counters["subset_evaluations"])
        recorder.add("local.solver_policy_assignments", counters["policy_assignments"])
        recorder.add("local.solver_frontier_points", counters["peak_root_frontier_points"])
        recorder.add("local.solver_dominance_comparisons", counters["dominance_comparisons"])
        recorder.add("local.solver_affine_term_evaluations", counters["affine_term_evaluations"])
        recorder.add(
            "solver.successes"
            if solver_outcome is not LocalSolverOutcome.SEARCH_CAP_EXHAUSTED
            else "solver.failures"
        )
        if solver_outcome is LocalSolverOutcome.SEARCH_CAP_EXHAUSTED:
            recorder.add("control.cap_rejections", 1)

        overlay = None
        post_audit = None
        overlay_binding: str | TypedNotApplicable = TypedNotApplicable(
            "local solver produced no candidate overlay"
        )
        stitched_binding: str | TypedNotApplicable = TypedNotApplicable(
            "local solver produced no stitched plan"
        )
        audit_issue_set_id = None
        post_steps = post_rows = 0
        if solver_outcome is LocalSolverOutcome.CANDIDATE_FOUND:
            controller.record(
                AccessOperation.LOCAL_PATCH_STITCH,
                AccessRouteScope.LOCAL,
            )
            overlay = _overlay_from_result(local_context, worker_result)
            overlay_binding = _binding_id("hybrid_overlay", overlay.overlay_id)
            stitched_binding = content_id(
                PHASE3D_LOCAL_PARENT_BINDING_DOMAIN,
                {
                    "schema": "acfqp.phase3e_stitched_plan_binding.v1",
                    "base_selected_plan_id": inputs.context.selected_plan_id,
                    "overlay_binding_id": overlay_binding,
                    "worker_result_binding_id": worker_binding_id,
                    "reusable_rapm_id": prepared.reusable_rapm_id,
                },
            )
            controller.record(
                AccessOperation.LOCAL_STITCH_ARTIFACT,
                AccessRouteScope.LOCAL,
                artifact_id=stitched_binding,
            )
            controller.record(
                AccessOperation.LOCAL_POSTAUDIT,
                AccessRouteScope.LOCAL,
            )
            post_kernel = PatchedAuditKernelView(
                logged_kernel,
                tuple((row.state, row.action) for row in overlay.decisions),
            )
            try:
                audit = audit_hybrid_policy(
                    post_kernel,
                    local_context.query,
                    local_context.world.models.envelope,
                    overlay,
                    regret_tolerance=inputs.threshold_profile.regret_tolerance,
                    unrestricted_reward_upper=local_context.unrestricted_reward_upper,
                )
            finally:
                post_steps = logged_kernel.step_calls - material_steps
                post_rows = logged_kernel.positive_outcome_rows - material_rows
                recorder.add("local.postaudit_ground_steps", post_steps)
                recorder.add("local.postaudit_outcome_rows", post_rows)
            audit_issue_set_id = content_id(
                PHASE3D_LOCAL_PARENT_BINDING_DOMAIN,
                {
                    "schema": "acfqp.phase3e_postaudit_issue_set.v1",
                    "issues": [
                        {
                            "code": issue.code,
                            "cell": repr(issue.cell),
                            "remaining": issue.remaining,
                            "detail": issue.detail,
                        }
                        for issue in audit.issues
                    ],
                },
            )
        else:
            audit = None

        cap_paths = (
            "local.materialization_ground_steps",
            "local.materialization_outcome_rows",
            "local.compiler_input_records",
            "local.compiler_expanded_forms",
            "local.compiler_domain_assignments",
            "local.solver_subset_evaluations",
            "local.solver_policy_assignments",
            "local.solver_frontier_points",
            "local.solver_dominance_comparisons",
            "local.solver_affine_term_evaluations",
            "local.postaudit_ground_steps",
            "local.postaudit_outcome_rows",
        )
        recorder.add(
            "control.cap_checks",
            sum(recorder.values[path] for path in cap_paths) + 6,
        )
        certified = bool(audit is not None and audit.certified)
        recorder.record_route_completion(success=certified)
        native = recorder.seal()
        actual = dict(native.work_vector.values)
        upper = dict(inputs.cardinality_bound.operational_upper_values(inputs.cap_profile, registry))
        exceeded = tuple(
            path
            for path in upper
            if path in actual and actual[path] > upper[path]
        )
        if exceeded:
            raise Phase3ELocalAdapterV1Error(
                "local actual native work exceeds preregistered source bound: "
                + ", ".join(exceeded)
            )
        if (
            read_bytes > LOCAL_READ_BYTES_UPPER
            or staged_bytes > LOCAL_STAGED_BYTES_UPPER
            or output_bytes > LOCAL_OUTPUT_BYTES_UPPER
            or mounted_peak > LOCAL_MOUNTED_BYTES_UPPER
            or working_peak > LOCAL_WORKING_BYTES_UPPER
        ):
            raise Phase3ELocalAdapterV1Error(
                "isolated local process exceeded its preregistered resource envelope"
            )

        local_result = LocalTransactionResultV1(
            inputs.context.route_decision_context_id,
            inputs.decision_point.decision_point_id,
            inputs.transaction.transaction_id,
            inputs.context.route_attempt_id,
            inputs.context.query_id,
            inputs.context.selected_plan_id,
            inputs.cap_profile.route_cap_profile_id,
            inputs.local_upper.route_upper_bound_envelope_id,
            native.work_vector.work_vector_id,
            capability_binding_id,
            worker_binding_id,
            runtime_binding_id,
            overlay_binding,
            stitched_binding,
            solver_outcome,
            bool(worker_result["search_complete"]),
            worker_result.get("cap_reason"),
        )
        if audit is not None:
            assert isinstance(overlay_binding, str)
            assert isinstance(stitched_binding, str)
            assert audit_issue_set_id is not None
            post_audit = PostAuditCertificateV1(
                inputs.context.route_decision_context_id,
                inputs.decision_point.decision_point_id,
                inputs.transaction.transaction_id,
                inputs.context.route_attempt_id,
                inputs.context.query_id,
                inputs.context.selected_plan_id,
                inputs.context.threshold_profile_id,
                local_result.local_transaction_result_id,
                native.work_vector.work_vector_id,
                overlay_binding,
                stitched_binding,
                audit_issue_set_id,
                PostAuditOutcome.CERTIFIED if audit.certified else PostAuditOutcome.FAILED,
                audit.lifted_reward_lower,
                audit.lifted_failure_upper,
                audit.regret_upper,
                post_steps,
                post_rows,
            )
        semantic_execution: TrustedLocalExecutionV1 = _seal_trusted_execution_v1(
            local_result=local_result,
            post_audit=post_audit,
            work_vector=native.work_vector,
            threshold_profile=inputs.threshold_profile if post_audit is not None else None,
        )
        # FQ10 forbids a host-side second solver run.  These authorities replay
        # the sealed local result, native WorkVector, cap/context bindings and
        # (when present) the sound post-audit artifact.  Their exact operational
        # checks are charged later by the runner's verification suffix.
        binding = AttestationContextV1(
            inputs.context,
            inputs.decision_point.decision_point_id,
            inputs.transaction.transaction_id,
            len(controller.snapshot().events),
        )

        def verification_record(role: SemanticRole) -> CounterRecordV1:
            spec = semantic_verifier_spec_v1(role)
            return CounterRecordV1.observe(
                registry,
                spec.verification_counter_path,
                1,
                recorder_id=(
                    "phase3e-safe-chain-selected-local-"
                    f"{role.value.lower()}-semantic-verifier-v1"
                ),
            )

        semantic_results: tuple[object, ...]
        deferred = prepared.two_stage_accounting_profile
        if deferred:
            # The runner first freezes the exact verification charge plan and
            # only then invokes the constructor-owned dispatcher below.
            semantic_results = ()
        else:
            records = (
                verification_record(SemanticRole.LOCAL_SOLVER_RESULT),
            ) + (
                (verification_record(SemanticRole.POST_AUDIT),)
                if post_audit is not None
                else ()
            )
            semantic_results = _verify_local_route_semantics_v1(
                inputs=inputs,
                semantic_execution=semantic_execution,
                binding=binding,
                verification_records=records,
                registry=registry,
            )
        artifact_id = (
            local_result.local_transaction_result_id
            if post_audit is None
            else post_audit.post_audit_certificate_id
        )
        outcome = (
            local_result.outcome.value
            if post_audit is None
            else post_audit.outcome.value
        )
        if post_audit is not None:
            controller.record(
                AccessOperation.LOCAL_POSTAUDIT_ARTIFACT,
                AccessRouteScope.LOCAL,
                artifact_id=artifact_id,
            )
        return Phase3ERouteExecutionV1(
            artifact_id,
            certified,
            bool(post_audit is not None and not certified),
            native,
            semantic_execution,
            outcome,
            semantic_results,
            semantic_verification_deferred=deferred,
        )


@dataclass(frozen=True, slots=True)
class SafeChainLocalPostFreezeConstructorV1:
    """Create the real local executor only from a verified post-freeze lease."""

    inputs: SafeChainLocalExecutorInputsV1
    registry: CounterRegistryV1 | None = None
    comparison_profile: ComparisonProfileV1 | None = None

    @property
    def runtime_factory_cardinality_v1(self) -> RuntimeFactoryCardinalityV1 | None:
        return self.inputs.runtime_factory_cardinality

    @property
    def executor_configuration_id_v1(self) -> str:
        return safe_chain_local_executor_configuration_id_v1(self.inputs)

    @property
    def selected_upper_id_v1(self) -> str:
        return self.inputs.local_upper.route_upper_bound_envelope_id

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
        """Replay exact local semantics after the runner freezes its charges."""

        if (
            not isinstance(execution, Phase3ERouteExecutionV1)
            or not isinstance(binding, AttestationContextV1)
            or not isinstance(execution.semantic_execution, TrustedLocalExecutionV1)
        ):
            raise Phase3ELocalAdapterV1Error(
                "deferred local verifier received a foreign route execution"
            )
        registry = self.registry or official_counter_registry_v1()
        return _verify_local_route_semantics_v1(
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
        """Verify exactly one frozen local obligation in causal order."""

        if (
            not isinstance(execution, Phase3ERouteExecutionV1)
            or not isinstance(binding, AttestationContextV1)
            or not isinstance(execution.semantic_execution, TrustedLocalExecutionV1)
            or not isinstance(verification_record, CounterRecordV1)
            or type(prior_results) is not tuple
        ):
            raise Phase3ELocalAdapterV1Error(
                "incremental local verifier received a foreign target"
            )
        semantic = execution.semantic_execution
        registry = self.registry or official_counter_registry_v1()
        if role is SemanticRole.LOCAL_SOLVER_RESULT:
            if prior_results:
                raise Phase3ELocalAdapterV1Error(
                    "local-result verification must be the first obligation"
                )
            return verify_local_transaction_result_semantics_v1(
                semantic,
                context=self.inputs.context,
                decision_point=self.inputs.decision_point,
                transaction=self.inputs.transaction,
                cap_profile=self.inputs.cap_profile,
                binding=binding,
                verification_work_record=verification_record,
                registry=registry,
            )
        if role is SemanticRole.POST_AUDIT:
            if len(prior_results) != 1:
                raise Phase3ELocalAdapterV1Error(
                    "post-audit verification requires one prior local result"
                )
            local_result = require_semantic_verification_result_v1(
                prior_results[0], SemanticRole.LOCAL_SOLVER_RESULT
            )
            return verify_post_audit_semantics_v1(
                semantic,
                local_solver_result=local_result,
                context=self.inputs.context,
                decision_point=self.inputs.decision_point,
                transaction=self.inputs.transaction,
                cap_profile=self.inputs.cap_profile,
                binding=binding,
                verification_work_record=verification_record,
                registry=registry,
            )
        raise Phase3ELocalAdapterV1Error(
            "incremental local verifier received an unregistered role"
        )

    def construct_after_freeze(
        self,
        grant: PostFreezeConstructionGrantV1,
    ) -> AuthorizedSafeChainLocalExecutorV1:
        if type(grant) is not PostFreezeConstructionGrantV1:
            raise Phase3ELocalAdapterV1Error(
                "sealed local construction requires a typed post-freeze grant"
            )
        recipe: ExecutorRecipeV1 = grant.recipe
        if (
            recipe.selected_route is not RouteSelection.LOCAL
            or recipe.executor_semantics_id
            != SAFE_CHAIN_LOCAL_EXECUTOR_SEMANTICS_ID
            or recipe.entrypoint_relative_path
            != SAFE_CHAIN_LOCAL_RUNTIME_ENTRYPOINT
            or recipe.executor_configuration_id
            != safe_chain_local_executor_configuration_id_v1(self.inputs)
        ):
            raise Phase3ELocalAdapterV1Error(
                "sealed local recipe differs from its trusted authority inputs"
            )
        # The sealed factory performs and accounts for the exact pre-lease
        # verification pass.  Replaying it here would be an unregistered fifth
        # runtime-tree read and would double-charge construction work.
        return AuthorizedSafeChainLocalExecutorV1(
            self.inputs,
            self.registry,
            self.comparison_profile,
            grant.runtime_tree.root,
            recipe.runtime_tree_id,
            recipe.executor_recipe_id,
        )


__all__ = [
    "AuthorizedSafeChainLocalExecutorV1",
    "Phase3ELocalAdapterV1Error",
    "SAFE_CHAIN_LOCAL_EXECUTOR_SEMANTICS_ID",
    "SAFE_CHAIN_LOCAL_RUNTIME_ENTRYPOINT",
    "SafeChainLocalExecutorInputsV1",
    "SafeChainLocalPostFreezeConstructorV1",
    "safe_chain_local_executor_configuration_id_v1",
]
