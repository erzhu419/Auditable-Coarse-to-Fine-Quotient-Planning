"""Occurrence and terminal closure for one prepared H2 model-failure route.

The preparation bridge in :mod:`acfqp.phase3e_model_failure_consumer_v1`
freezes exactly one selected sealed executor.  This module consumes that live
preparation through :func:`acfqp.phase3e_occurrence_runner_v1.run_phase3e_occurrence_v1`.
The nonselected route remains a rejection-only callback and no continuation
planner is installed.

A certified route is not classified from a status string.  The complete
marginal WorkVector/projection, selected upper and decision, route-specific
semantic results, access log, freeze attestation, and sealed-executor merge
chain are independently replayed into a live ``TerminalArtifactV1`` authority.
The surrounding occurrence result retains the ordered common-prefix and route
components, so terminal evidence cannot erase work that precedes the marginal
route.

This remains deliberately non-official.  In particular, the preparation
bridge's native-accounting blockers are immutable inputs to every closure and
the counter-completeness/workload-economics gates remain locked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.access_protocol_v1 import ProtocolSequenceProfileV1
from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRecordV1,
    CounterRegistryV1,
    LaneEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.phase3e_ids import (
    MODEL_FAILURE_OCCURRENCE_CLOSURE_DOMAIN,
    content_id,
)
from acfqp.phase3e_model_failure_consumer_v1 import (
    MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS,
    MODEL_FAILURE_CONSUMER_STATUS,
    Phase3EModelFailureConsumerV1Error,
    PreparedModelFailureConsumerV1,
)
from acfqp.phase3e_occurrence_accounting_v1 import (
    OccurrenceWorkComponentKind,
)
from acfqp.phase3e_occurrence_runner_v1 import (
    OccurrenceClosureCodeV1,
    Phase3EOccurrenceRunResultV1,
    run_phase3e_occurrence_v1,
)
from acfqp.phase3e_runner_v1 import (
    COUNTER_COMPLETENESS_GATE_STATUS,
    OFFICIAL_N_BREAK_EVEN,
    OFFICIAL_SCALAR_COST,
    WORKLOAD_ECONOMICS_GATE_STATUS,
    Phase3ERouteExecutorV1,
)
from acfqp.routing_v1 import (
    RouteSelection,
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationResultV1,
    TerminalRouteEvidenceBundleV1,
    require_semantic_verification_result_v1,
    require_terminal_classification_result_v1,
    semantic_verifier_spec_v1,
    verify_actual_projection_semantics_v1,
    verify_terminal_classification_semantics_v1,
    verify_work_vector_semantics_v1,
)


MODEL_FAILURE_OCCURRENCE_STATUS = (
    "NONOFFICIAL_MODEL_FAILURE_OCCURRENCE_CLOSED"
)


class Phase3EModelFailureOccurrenceV1Error(ValueError):
    """A selected-route, occurrence, terminal, or blocker binding failed."""


def _official_profiles_v1(
    registry: CounterRegistryV1 | None,
    profile: ComparisonProfileV1 | None,
) -> tuple[CounterRegistryV1, ComparisonProfileV1]:
    trusted_registry = registry or official_counter_registry_v1()
    if type(trusted_registry) is not CounterRegistryV1:
        raise Phase3EModelFailureOccurrenceV1Error(
            "model-failure occurrence requires CounterRegistryV1"
        )
    trusted_registry.validate_official_catalogue()
    if trusted_registry != official_counter_registry_v1():
        raise Phase3EModelFailureOccurrenceV1Error(
            "model-failure occurrence requires the exact official registry"
        )
    trusted_profile = profile or official_comparison_profile_v1(
        trusted_registry
    )
    if type(trusted_profile) is not ComparisonProfileV1:
        raise Phase3EModelFailureOccurrenceV1Error(
            "model-failure occurrence requires ComparisonProfileV1"
        )
    trusted_profile.validate(trusted_registry)
    if trusted_profile != official_comparison_profile_v1(trusted_registry):
        raise Phase3EModelFailureOccurrenceV1Error(
            "model-failure occurrence requires the exact official profile"
        )
    return trusted_registry, trusted_profile


def _evaluation_record_v1(
    role: SemanticRole,
    label: str,
    registry: CounterRegistryV1,
) -> CounterRecordV1:
    return CounterRecordV1.observe(
        registry,
        semantic_verifier_spec_v1(role).counter_path_for_lane(
            LaneEnum.EVALUATION
        ),
        1,
        recorder_id=(
            "phase3e-model-failure-occurrence-"
            f"{label}-{role.value.lower()}-evaluation-v1"
        ),
    )


def _route_semantic_result_v1(
    result: Any,
    role: SemanticRole,
) -> SemanticVerificationResultV1:
    matches: list[SemanticVerificationResultV1] = []
    for candidate in result.route_execution.semantic_verification_results:
        try:
            matches.append(
                require_semantic_verification_result_v1(candidate, role)
            )
        except ValueError:
            continue
    if len(matches) != 1:
        raise Phase3EModelFailureOccurrenceV1Error(
            f"selected route lacks exactly one live {role.value} authority"
        )
    return matches[0]


def _terminal_contract_v1(
    closure: OccurrenceClosureCodeV1,
) -> tuple[TerminalClass, TerminalCode, tuple[SemanticRole, ...]]:
    if closure is OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY:
        return (
            TerminalClass.PLAN_CERTIFICATE,
            TerminalCode.LOCAL_GROUND_RECOVERY,
            (SemanticRole.LOCAL_SOLVER_RESULT, SemanticRole.POST_AUDIT),
        )
    if closure is OccurrenceClosureCodeV1.FULL_GROUND_FALLBACK:
        return (
            TerminalClass.PLAN_CERTIFICATE,
            TerminalCode.FULL_GROUND_FALLBACK,
            (SemanticRole.GROUND_FALLBACK,),
        )
    if closure is OccurrenceClosureCodeV1.FULL_GROUND_EXACT_INFEASIBLE:
        return (
            TerminalClass.INFEASIBILITY_CERTIFICATE,
            TerminalCode.FULL_GROUND_EXACT_INFEASIBLE,
            (SemanticRole.GROUND_FALLBACK,),
        )
    raise Phase3EModelFailureOccurrenceV1Error(
        "noncertificate occurrence cannot mint a route plan terminal"
    )


def _mint_successful_terminal_v1(
    prepared_consumer: PreparedModelFailureConsumerV1,
    occurrence: Phase3EOccurrenceRunResultV1,
    *,
    registry: CounterRegistryV1,
) -> tuple[TerminalArtifactV1, SemanticVerificationResultV1]:
    terminal_class, terminal_code, route_roles = _terminal_contract_v1(
        occurrence.closure_code
    )
    if len(occurrence.decision_runs) != 1:
        raise Phase3EModelFailureOccurrenceV1Error(
            "single-factory occurrence certificate requires exactly one decision run"
        )
    run = occurrence.decision_runs[0]
    context = prepared_consumer.prepared.context
    point = prepared_consumer.prepared.decision_point
    if (
        run.selected_route is not prepared_consumer.selected_route
        or run.decision != prepared_consumer.route_authorities.decision
        or run.selected_upper.route_upper_bound_envelope_id
        != run.decision.selected_upper_id
        or run.common_prefix_work
        is not prepared_consumer.failed_prefix_authority.aggregate_work
        or run.runtime_tree_id
        != prepared_consumer.runtime_manifest.runtime_tree_id
        or run.executor_recipe_id
        != prepared_consumer.selected_recipe.executor_recipe_id
        or run.sealed_executor_profile is not True
        or run.two_stage_accounting_profile is not True
    ):
        raise Phase3EModelFailureOccurrenceV1Error(
            "successful occurrence route differs from its retained preparation"
        )
    expected_route = (
        RouteSelection.LOCAL
        if terminal_code is TerminalCode.LOCAL_GROUND_RECOVERY
        else RouteSelection.FALLBACK
    )
    if run.selected_route is not expected_route:
        raise Phase3EModelFailureOccurrenceV1Error(
            "occurrence closure and selected route disagree"
        )

    binding = AttestationContextV1(
        context,
        point.decision_point_id,
        run.selected_upper.transaction_id,
        len(run.access_log.events) + 1,
        LaneEnum.EVALUATION,
    )
    aggregate = run.aggregate_marginal_work
    work_result = verify_work_vector_semantics_v1(
        aggregate.aggregate_work_vector,
        binding=binding,
        verification_work_record=_evaluation_record_v1(
            SemanticRole.WORK_VECTOR, "aggregate", registry
        ),
        registry=registry,
    )
    actual_result = verify_actual_projection_semantics_v1(
        vector=aggregate.aggregate_work_vector,
        claimed_comparison=aggregate.aggregate_comparison_vector,
        projection_proof=aggregate.aggregate_projection_proof,
        binding=binding,
        verification_work_record=_evaluation_record_v1(
            SemanticRole.ACTUAL_PROJECTION, "aggregate", registry
        ),
        registry=registry,
    )
    if expected_route is RouteSelection.LOCAL:
        selected_upper_result = (
            prepared_consumer.route_authorities.local_upper_result
        )
    else:
        selected_upper_result = (
            prepared_consumer.route_authorities.fallback_upper_result
        )
    selected_upper_result = require_semantic_verification_result_v1(
        selected_upper_result, SemanticRole.ROUTE_UPPER
    )
    decision_result = require_semantic_verification_result_v1(
        prepared_consumer.route_authorities.decision_result,
        SemanticRole.ROUTE_DECISION,
    )
    route_results = tuple(
        _route_semantic_result_v1(run, role) for role in route_roles
    )
    evidence_results = (
        work_result,
        actual_result,
        selected_upper_result,
        decision_result,
        *route_results,
    )
    terminal = TerminalArtifactV1(
        "LOGICAL_OCCURRENCE",
        terminal_class,
        terminal_code,
        context.route_decision_context_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        run.selected_upper.transaction_id,
        aggregate.aggregate_work_vector.work_vector_id,
        tuple(
            sorted(
                row.attestation.verification_attestation_id
                for row in evidence_results
            )
        ),
        aggregate.aggregate_comparison_vector.comparison_vector_id,
        aggregate.aggregate_projection_proof.actual_projection_proof_id,
        aggregate.aggregation_proof.marginal_work_aggregation_proof_id,
        run.freeze_attestation.route_decision_freeze_attestation_id,
        run.access_log.access_event_log_id,
    )
    route_evidence = TerminalRouteEvidenceBundleV1(
        run.selected_route_work,
        run.verification_suffix_work,
        aggregate,
        run.access_log,
        run.freeze_attestation,
        ProtocolSequenceProfileV1(),
        run.selected_work_result,
        sealed_executor_profile=True,
        sealed_executor_construction_accounting=(
            run.route_execution.sealed_executor_construction_accounting
        ),
        sealed_delegate_execution_work=(
            run.route_execution.delegate_execution_work
        ),
        sealed_executor_execution_merge_proof=(
            run.route_execution.sealed_executor_execution_merge_proof
        ),
    )
    terminal_result = verify_terminal_classification_semantics_v1(
        terminal,
        evidence_results=evidence_results,
        route_evidence=route_evidence,
        binding=binding,
        verification_work_record=_evaluation_record_v1(
            SemanticRole.TERMINAL_CLASSIFICATION, "terminal", registry
        ),
        registry=registry,
    )
    verified_terminal, _attestation = require_terminal_classification_result_v1(
        terminal_result
    )
    if verified_terminal != terminal:
        raise Phase3EModelFailureOccurrenceV1Error(
            "terminal semantic replay changed the occurrence classification"
        )
    return terminal, terminal_result


@dataclass(frozen=True, slots=True)
class _ModelFailureOccurrenceMintV1:
    prepared_consumer: PreparedModelFailureConsumerV1 = field(
        repr=False, compare=False
    )
    occurrence: Phase3EOccurrenceRunResultV1 = field(
        repr=False, compare=False
    )
    terminal_artifact: TerminalArtifactV1 | None = field(
        repr=False, compare=False
    )
    terminal_result: SemanticVerificationResultV1 | None = field(
        repr=False, compare=False
    )
    public_identity: tuple[tuple[str, str], ...]
    issuer: object = field(repr=False, compare=False)


_MODEL_FAILURE_OCCURRENCE_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class ModelFailureOccurrenceClosureV1:
    """Opaque closure retaining the exact preparation and occurrence history."""

    prepared_consumer: PreparedModelFailureConsumerV1 = field(
        repr=False, compare=False
    )
    occurrence: Phase3EOccurrenceRunResultV1
    terminal_artifact: TerminalArtifactV1 | None
    terminal_result: SemanticVerificationResultV1 | None = field(
        repr=False, compare=False
    )
    _mint: _ModelFailureOccurrenceMintV1 = field(
        repr=False, compare=False
    )
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )
    status: str = MODEL_FAILURE_OCCURRENCE_STATUS
    source_accounting_status: str = MODEL_FAILURE_CONSUMER_STATUS
    accounting_blockers: tuple[str, ...] = (
        MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS
    )
    official_execution_allowed: bool = False
    official_scalar_cost: None = OFFICIAL_SCALAR_COST
    official_N_break_even: None = OFFICIAL_N_BREAK_EVEN
    workload_economics_gate_status: str = WORKLOAD_ECONOMICS_GATE_STATUS
    counter_completeness_gate_status: str = COUNTER_COMPLETENESS_GATE_STATUS
    counter_completeness_certified: bool = False

    def __post_init__(self) -> None:
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_MODEL_FAILURE_OCCURRENCE_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise Phase3EModelFailureOccurrenceV1Error(
                    "model-failure occurrence is a copied or modified live authority"
                ) from error
        if (
            type(self._mint) is not _ModelFailureOccurrenceMintV1
            or self._mint.issuer is not _MODEL_FAILURE_OCCURRENCE_AUTHORITY
            or self.prepared_consumer is not self._mint.prepared_consumer
            or self.occurrence is not self._mint.occurrence
            or self.terminal_artifact is not self._mint.terminal_artifact
            or self.terminal_result is not self._mint.terminal_result
        ):
            raise Phase3EModelFailureOccurrenceV1Error(
                "model-failure occurrence live members differ from its retained mint"
            )
        if (
            self.status != MODEL_FAILURE_OCCURRENCE_STATUS
            or self.source_accounting_status != MODEL_FAILURE_CONSUMER_STATUS
            or self.accounting_blockers
            != MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate_status
            != WORKLOAD_ECONOMICS_GATE_STATUS
            or self.counter_completeness_gate_status
            != COUNTER_COMPLETENESS_GATE_STATUS
            or self.counter_completeness_certified is not False
        ):
            raise Phase3EModelFailureOccurrenceV1Error(
                "model-failure occurrence cannot hide accounting blockers or unlock gates"
            )
        if (
            self.occurrence.official_execution_allowed is not False
            or self.occurrence.counter_completeness_gate_status
            != COUNTER_COMPLETENESS_GATE_STATUS
            or self.occurrence.occurrence_work.logical_occurrence_id
            != self.prepared_consumer.prepared.context.logical_occurrence_id
            or self.occurrence.occurrence_work.route_attempt_id
            != self.prepared_consumer.prepared.context.route_attempt_id
            or not self.occurrence.work_components
            or self.occurrence.work_components[0].component_kind
            is not OccurrenceWorkComponentKind.COMMON_PREFIX
            or self.occurrence.work_components[0].route_context
            != self.prepared_consumer.prepared.context
            or self.occurrence.work_components[0].decision_point
            != self.prepared_consumer.prepared.decision_point
        ):
            raise Phase3EModelFailureOccurrenceV1Error(
                "model-failure occurrence work/history differs from its preparation"
            )
        certificate = self.occurrence.closure_code in {
            OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY,
            OccurrenceClosureCodeV1.FULL_GROUND_FALLBACK,
            OccurrenceClosureCodeV1.FULL_GROUND_EXACT_INFEASIBLE,
        }
        if certificate:
            if (
                type(self.terminal_artifact) is not TerminalArtifactV1
                or type(self.terminal_result) is not SemanticVerificationResultV1
            ):
                raise Phase3EModelFailureOccurrenceV1Error(
                    "certificate occurrence lacks typed terminal authority"
                )
            verified, _attestation = require_terminal_classification_result_v1(
                self.terminal_result
            )
            if verified != self.terminal_artifact:
                raise Phase3EModelFailureOccurrenceV1Error(
                    "certificate occurrence terminal authority is stale"
                )
        elif self.terminal_artifact is not None or self.terminal_result is not None:
            raise Phase3EModelFailureOccurrenceV1Error(
                "noncertificate occurrence cannot carry a plan terminal"
            )
        terminal_id = self.authoritative_terminal_id
        expected_identity = (
            (
                "failed_prefix_accounting_authority_id",
                self.prepared_consumer.failed_prefix_authority
                .failed_prefix_accounting_authority_id,
            ),
            (
                "route_decision_id",
                self.prepared_consumer.route_authorities.decision
                .route_decision_id,
            ),
            (
                "occurrence_work_aggregate_id",
                self.occurrence.occurrence_work
                .phase3e_occurrence_work_aggregate_id,
            ),
            ("terminal_id", terminal_id),
        )
        if expected_identity != self._mint.public_identity:
            raise Phase3EModelFailureOccurrenceV1Error(
                "model-failure occurrence public identity differs from its mint"
            )

    def __copy__(self) -> object:
        raise Phase3EModelFailureOccurrenceV1Error(
            "model-failure occurrence live authority cannot be copied"
        )

    def __deepcopy__(self, memo: dict[int, object]) -> object:
        raise Phase3EModelFailureOccurrenceV1Error(
            "model-failure occurrence live authority cannot be deep-copied"
        )

    @property
    def authoritative_terminal_id(self) -> str:
        if self.terminal_artifact is not None:
            return self.terminal_artifact.terminal_artifact_id
        if self.occurrence.occurrence_failure_terminal is not None:
            return (
                self.occurrence.occurrence_failure_terminal
                .occurrence_failure_terminal_id
            )
        if self.occurrence.occurrence_terminal is not None:
            return self.occurrence.occurrence_terminal.occurrence_terminal_artifact_id
        raise Phase3EModelFailureOccurrenceV1Error(
            "closed occurrence lacks any typed terminal evidence"
        )

    @property
    def model_failure_occurrence_closure_id(self) -> str:
        return content_id(
            MODEL_FAILURE_OCCURRENCE_CLOSURE_DOMAIN,
            {
                "schema": "acfqp.model_failure_occurrence_closure.v1",
                "status": self.status,
                "source_accounting_status": self.source_accounting_status,
                "accounting_blockers": list(self.accounting_blockers),
                "official_execution_allowed": False,
                "counter_completeness_certified": False,
                "failed_prefix_accounting_authority_id": (
                    self.prepared_consumer.failed_prefix_authority
                    .failed_prefix_accounting_authority_id
                ),
                "route_decision_id": (
                    self.prepared_consumer.route_authorities.decision
                    .route_decision_id
                ),
                "closure_code": self.occurrence.closure_code.value,
                "occurrence_work_aggregate_id": (
                    self.occurrence.occurrence_work
                    .phase3e_occurrence_work_aggregate_id
                ),
                "component_ref_ids": [
                    row.occurrence_work_component_ref_id
                    for row in self.occurrence.occurrence_work.component_refs
                ],
                "terminal_id": self.authoritative_terminal_id,
            },
        )


def run_prepared_model_failure_occurrence_v1(
    prepared_consumer: PreparedModelFailureConsumerV1,
    *,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> ModelFailureOccurrenceClosureV1:
    """Run the one selected factory and close its complete logical occurrence."""

    if type(prepared_consumer) is not PreparedModelFailureConsumerV1:
        raise Phase3EModelFailureOccurrenceV1Error(
            "occurrence run requires a retained PreparedModelFailureConsumerV1"
        )
    trusted_registry, trusted_profile = _official_profiles_v1(
        registry, comparison_profile
    )
    try:
        prepared_consumer.validate_before_run(
            registry=trusted_registry,
            comparison_profile=trusted_profile,
        )
    except Phase3EModelFailureConsumerV1Error as error:
        raise Phase3EModelFailureOccurrenceV1Error(str(error)) from error

    def reject_unselected_route(*_args: object, **_kwargs: object) -> object:
        raise Phase3EModelFailureOccurrenceV1Error(
            "occurrence runner accessed the nonselected model-failure route"
        )

    selected_factory: Phase3ERouteExecutorV1 = prepared_consumer.selected_factory
    if prepared_consumer.selected_route is RouteSelection.LOCAL:
        local_executor = selected_factory
        fallback_executor = reject_unselected_route
    else:
        local_executor = reject_unselected_route
        fallback_executor = selected_factory
    occurrence = run_phase3e_occurrence_v1(
        prepared_consumer.prepared,
        local_executor=local_executor,
        fallback_executor=fallback_executor,
        second_transaction_planner=None,
        fresh_fallback_planner=None,
        registry=trusted_registry,
        comparison_profile=trusted_profile,
    )
    if type(occurrence) is not Phase3EOccurrenceRunResultV1:
        raise Phase3EModelFailureOccurrenceV1Error(
            "occurrence runner returned an untyped result"
        )
    if occurrence.closure_code in {
        OccurrenceClosureCodeV1.LOCAL_GROUND_RECOVERY,
        OccurrenceClosureCodeV1.FULL_GROUND_FALLBACK,
        OccurrenceClosureCodeV1.FULL_GROUND_EXACT_INFEASIBLE,
    }:
        terminal, terminal_result = _mint_successful_terminal_v1(
            prepared_consumer,
            occurrence,
            registry=trusted_registry,
        )
    else:
        terminal = None
        terminal_result = None
    terminal_id = (
        terminal.terminal_artifact_id
        if terminal is not None
        else (
            occurrence.occurrence_failure_terminal.occurrence_failure_terminal_id
            if occurrence.occurrence_failure_terminal is not None
            else occurrence.occurrence_terminal.occurrence_terminal_artifact_id
            if occurrence.occurrence_terminal is not None
            else None
        )
    )
    if terminal_id is None:
        raise Phase3EModelFailureOccurrenceV1Error(
            "occurrence closed without typed terminal evidence"
        )
    public_identity = (
        (
            "failed_prefix_accounting_authority_id",
            prepared_consumer.failed_prefix_authority
            .failed_prefix_accounting_authority_id,
        ),
        (
            "route_decision_id",
            prepared_consumer.route_authorities.decision.route_decision_id,
        ),
        (
            "occurrence_work_aggregate_id",
            occurrence.occurrence_work.phase3e_occurrence_work_aggregate_id,
        ),
        ("terminal_id", terminal_id),
    )
    closure = ModelFailureOccurrenceClosureV1(
        prepared_consumer,
        occurrence,
        terminal,
        terminal_result,
        _ModelFailureOccurrenceMintV1(
            prepared_consumer,
            occurrence,
            terminal,
            terminal_result,
            public_identity,
            _MODEL_FAILURE_OCCURRENCE_AUTHORITY,
        ),
    )
    return bind_runtime_authority_v1(
        closure,
        issuer=_MODEL_FAILURE_OCCURRENCE_AUTHORITY,
    )


def require_model_failure_occurrence_closure_v1(
    closure: object,
) -> ModelFailureOccurrenceClosureV1:
    """Require the exact owner-bound closure returned by the occurrence runner."""

    if type(closure) is not ModelFailureOccurrenceClosureV1:
        raise Phase3EModelFailureOccurrenceV1Error(
            "model-failure occurrence requires its exact live closure type"
        )
    try:
        require_runtime_authority_v1(
            closure,
            issuer=_MODEL_FAILURE_OCCURRENCE_AUTHORITY,
        )
    except ValueError as error:
        raise Phase3EModelFailureOccurrenceV1Error(
            "model-failure occurrence is not the retained minted instance"
        ) from error
    return closure


__all__ = [
    "MODEL_FAILURE_OCCURRENCE_STATUS",
    "ModelFailureOccurrenceClosureV1",
    "Phase3EModelFailureOccurrenceV1Error",
    "require_model_failure_occurrence_closure_v1",
    "run_prepared_model_failure_occurrence_v1",
]
