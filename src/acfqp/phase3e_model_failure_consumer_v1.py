"""Production-shaped H2 model-failure consumer for the Phase-3E vertical slice.

The module closes two deliberately separate accounting boundaries.

First, an executor-minted ``ABSTRACT_FAILED_PREFIX`` is sealed before the
``ABSTRACT_AUDIT`` semantic check.  The audit check is then admitted only as
the exact suffix of that predecision two-stage plan.  A bare WorkVector,
serialized execution artifact, audit hash, or attestation is never sufficient.

Second, the retained failed-prefix authority and an already-open ground
handoff are consumed to prepare both marginal routes.  Cardinalities, uppers,
and the route decision are semantically verified after their own charge plan
is frozen.  The function returns a ``PreparedPhase3ERunV1`` and exactly one
inert sealed factory for the selected route.  It does not plan, audit, call a
ground transition, materialize a slice, compile, launch a route worker, or
resolve the runtime CAS.

This is the safe-chain H=2 V0 authority/execution bridge only.  Its observable
non-hash route-preparation operations and every causal candidate are retained
in an ordered post-core trace.  They are not backfilled into the
decision-point-bound failed-prefix WorkVector: point/upper/decision evidence
does not exist until after that core is frozen, so doing so would create an
identity cycle or predeclare unobserved work.  Until an occurrence-level
post-core component is supported, the incremental WorkVector is retained but
explicitly not charged to occurrence totals.  Ground-handoff construction,
the already-sealed abstract-audit replay, content-ID hashes, and accounting
sealing remain an explicit exclusion boundary.  The bridge therefore remains
non-official and cannot be used as counter-completeness or workload-economics
evidence.
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
from acfqp.access_protocol_v1 import (
    AccessOperation,
    PRESELECTION_READ_OPERATIONS,
)
from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRecordV1,
    CounterRegistryV1,
    LaneEnum,
    RouteKindEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    official_actual_projection_profile_v1,
)
from acfqp.native_recorder_v1 import RecordedWorkV1
from acfqp.phase3d import (
    SafeChainPreparedEstimateContext,
    prepare_safe_chain_estimate_from_verified_model_failure_v1,
    require_verified_model_estimate_binding_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    SEALED_ROUTE_CAP_PROFILE_KEY,
    build_ground_fallback_cardinality_evidence_v1,
    derive_safe_chain_fallback_cardinality_bound_v1,
    derive_safe_chain_fallback_cardinality_source_v1,
)
from acfqp.phase3e_ground_handoff_v1 import (
    GroundBindingAfterFailedAuditV1,
    require_ground_binding_after_failed_audit_v1,
)
from acfqp.phase3e_isolated_fallback_v1 import (
    ISOLATED_FALLBACK_EXECUTOR_SEMANTICS_ID,
    ISOLATED_FALLBACK_RUNTIME_ENTRYPOINT,
    IsolatedFallbackPostFreezeConstructorV1,
    IsolatedGroundFallbackExecutorInputsV1,
    isolated_ground_fallback_executor_configuration_id_v1,
)
from acfqp.phase3e_local_adapter_v1 import (
    SAFE_CHAIN_LOCAL_EXECUTOR_SEMANTICS_ID,
    SAFE_CHAIN_LOCAL_RUNTIME_ENTRYPOINT,
    SafeChainLocalExecutorInputsV1,
    SafeChainLocalPostFreezeConstructorV1,
    safe_chain_local_executor_configuration_id_v1,
)
from acfqp.phase3e_local_preselection_v1 import (
    build_safe_chain_local_cardinality_evidence_v1,
    derive_safe_chain_local_cardinality_bound_v1,
    derive_safe_chain_local_frontier_and_causal_v1,
    derive_safe_chain_local_preselection_source_v1,
)
from acfqp.phase3e_local_semantics_v1 import FrozenThresholdProfileV1
from acfqp.phase3e_model_only_executor_v1 import (
    ModelOnlyQueryExecutionV1,
    verify_model_only_failed_prefix_execution_v1,
)
from acfqp.phase3e_model_only_v1 import ModelOnlyOutcome
from acfqp.phase3e_model_failure_preparation_accounting_v1 import (
    ModelFailurePreparationAccountingV1,
    ModelFailurePreparationEventRecorderV1,
    PreparationEventKind,
    derive_model_failure_preparation_accounting_v1,
    verify_model_failure_preparation_accounting_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    LOCAL_QUERY_KEY,
    ModelOnlyRAPMSourceV1,
)
from acfqp.phase3e_runner_v1 import (
    Phase3EDecisionAuthorizationV1,
    Phase3EPreselectionReadV1,
    Phase3ERunResultV1,
    PreparedPhase3ERunV1,
    run_phase3e,
)
from acfqp.phase3e_sealed_executor_v1 import (
    ExecutorRecipeV1,
    RuntimeFactoryCardinalityV1,
    RuntimeTreeCASV1,
    RuntimeTreeManifestV1,
    SealedPostFreezeExecutorFactoryV1,
    require_sealed_executor_factory_v1,
)
from acfqp.phase3e_two_stage_accounting_v1 import (
    AccountingCoreStage,
    SealedAccountingCoreV1,
    TwoStageAccountingClosureV1,
    VerificationChargeObligationV1,
    VerificationChargePlanV1,
    derive_two_stage_accounting_v1,
    seal_accounting_core_v1,
)
from acfqp.phase3e_ids import (
    MODEL_ONLY_FAILED_PREFIX_ACCOUNTING_AUTHORITY_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp.route_upper_formula_v1 import (
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    TransactionV1,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationResultV1,
    derive_guarded_marginal_route_decision_v1,
    require_semantic_verification_result_v1,
    semantic_verifier_spec_v1,
    verify_abstract_plan_audit_semantics_v1,
    verify_marginal_route_decision_semantics_v1,
    verify_route_upper_semantics_v1,
    verify_safe_chain_fallback_cardinality_semantics_v1,
    verify_safe_chain_local_cardinality_semantics_v1,
    verify_safe_chain_local_causal_semantics_v1,
    verify_typed_attestation_v1,
)


FAILED_PREFIX_AUDIT_DECISION_NA = (
    "model-only failed audit precedes the Phase-3E route decision"
)
FAILED_PREFIX_AUDIT_TRANSACTION_NA = (
    "model-only failed audit precedes every local transaction"
)
COMMON_PREFIX_TRANSACTION_NA = (
    "common route-estimation prefix has no marginal local transaction"
)
FALLBACK_TRANSACTION_NA = (
    "direct fallback has no local transaction"
)
ROUTE_VERIFIER_RECORDER_PREFIX = "phase3e-model-failure-consumer"
MODEL_FAILURE_CONSUMER_STATUS = (
    "NONOFFICIAL_MODEL_FAILURE_ROUTE_BRIDGE_EXECUTED"
)
MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS = (
    "GROUND_HANDOFF_OPERATIONAL_WORK_NOT_NATIVE_ACCOUNTED",
    "MODEL_FAILURE_ROUTE_PREPARATION_OPERATIONAL_WORK_NOT_NATIVE_ACCOUNTED",
    "ABSTRACT_AUDIT_REPLAY_NOT_EVENT_GRAIN_ACCOUNTED",
    "CONTENT_ID_HASH_INVOCATIONS_NOT_GLOBALLY_HOOKED",
)


class Phase3EModelFailureConsumerV1Error(ValueError):
    """A failed-prefix, ground, route, runtime, or accounting binding failed."""


def _official_profiles_v1(
    registry: CounterRegistryV1 | None,
    profile: ComparisonProfileV1 | None,
) -> tuple[CounterRegistryV1, ComparisonProfileV1]:
    trusted_registry = registry or official_counter_registry_v1()
    if type(trusted_registry) is not CounterRegistryV1:
        raise Phase3EModelFailureConsumerV1Error(
            "model-failure consumer requires CounterRegistryV1"
        )
    trusted_registry.validate_official_catalogue()
    official_registry = official_counter_registry_v1()
    if trusted_registry != official_registry:
        raise Phase3EModelFailureConsumerV1Error(
            "model-failure consumer requires the exact official registry"
        )
    trusted_profile = profile or official_comparison_profile_v1(
        trusted_registry
    )
    if type(trusted_profile) is not ComparisonProfileV1:
        raise Phase3EModelFailureConsumerV1Error(
            "model-failure consumer requires ComparisonProfileV1"
        )
    trusted_profile.validate(trusted_registry)
    if trusted_profile != official_comparison_profile_v1(trusted_registry):
        raise Phase3EModelFailureConsumerV1Error(
            "model-failure consumer requires the exact official profile"
        )
    return trusted_registry, trusted_profile


def _verification_record_v1(
    role: SemanticRole,
    instance: str,
    registry: CounterRegistryV1,
) -> CounterRecordV1:
    spec = semantic_verifier_spec_v1(role)
    return CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(LaneEnum.OPERATIONAL),
        1,
        recorder_id=(
            f"{ROUTE_VERIFIER_RECORDER_PREFIX}-{instance}-"
            f"{role.value.lower()}-verifier-v1"
        ),
    )


@dataclass(frozen=True, slots=True)
class ModelOnlyFailedPrefixChargePreparationV1:
    """Core and charge plan frozen before ABSTRACT_AUDIT verification."""

    operational_execution_id: str
    audit_binding: AttestationContextV1
    verification_work_record: CounterRecordV1
    core: SealedAccountingCoreV1
    plan: VerificationChargePlanV1

    def __post_init__(self) -> None:
        parse_content_id(self.operational_execution_id)
        if (
            type(self.audit_binding) is not AttestationContextV1
            or type(self.verification_work_record) is not CounterRecordV1
            or type(self.core) is not SealedAccountingCoreV1
            or type(self.plan) is not VerificationChargePlanV1
        ):
            raise Phase3EModelFailureConsumerV1Error(
                "failed-prefix charge preparation contains an untyped member"
            )
        if (
            not isinstance(self.audit_binding.decision_point_id, TypedNotApplicable)
            or not isinstance(self.audit_binding.transaction_id, TypedNotApplicable)
            or self.audit_binding.verification_lane is not LaneEnum.OPERATIONAL
            or self.plan.accounting_core_seal_id
            != self.core.accounting_core_seal_id
        ):
            raise Phase3EModelFailureConsumerV1Error(
                "failed-prefix audit was not preregistered before a decision"
            )


def freeze_model_only_failed_prefix_charge_v1(
    execution: ModelOnlyQueryExecutionV1,
    *,
    audit_binding: AttestationContextV1,
    verification_work_record: CounterRecordV1,
    plan_frozen_at_protocol_step: int,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> ModelOnlyFailedPrefixChargePreparationV1:
    """Freeze the one-obligation audit charge plan before invoking its verifier."""

    retained = verify_model_only_failed_prefix_execution_v1(execution)
    trusted_registry, trusted_profile = _official_profiles_v1(
        registry, comparison_profile
    )
    result = retained.model_only_result
    if (
        type(audit_binding) is not AttestationContextV1
        or audit_binding.route_context != result.route_context
        or not isinstance(audit_binding.decision_point_id, TypedNotApplicable)
        or not isinstance(audit_binding.transaction_id, TypedNotApplicable)
        or audit_binding.verification_lane is not LaneEnum.OPERATIONAL
        or audit_binding.verified_at_protocol_step
        <= plan_frozen_at_protocol_step
    ):
        raise Phase3EModelFailureConsumerV1Error(
            "ABSTRACT_AUDIT binding must be operational, predecision, and after plan freeze"
        )
    actual_profile = official_actual_projection_profile_v1(
        trusted_registry, trusted_profile
    )
    core = seal_accounting_core_v1(
        recorded_work=retained.recorded_work,
        binding=audit_binding,
        core_stage=AccountingCoreStage.COMMON_PREFIX,
        registry=trusted_registry,
        comparison_profile=trusted_profile,
        actual_profile=actual_profile,
    )
    obligation = VerificationChargeObligationV1.for_role(
        ordinal=0,
        artifact_id=result.audit.audit_id,
        role=SemanticRole.ABSTRACT_AUDIT,
        expected_result="FAIL",
        verified_at_protocol_step=audit_binding.verified_at_protocol_step,
        verification_work_record=verification_work_record,
        binding=audit_binding,
    )
    plan = VerificationChargePlanV1.for_core(
        core,
        plan_frozen_at_protocol_step=plan_frozen_at_protocol_step,
        obligations=(obligation,),
    )
    return ModelOnlyFailedPrefixChargePreparationV1(
        retained.operational_execution_id,
        audit_binding,
        verification_work_record,
        core,
        plan,
    )


_FAILED_PREFIX_ACCOUNTING_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class _FailedPrefixAccountingMintV1:
    execution: ModelOnlyQueryExecutionV1 = field(repr=False, compare=False)
    audit_authority: SemanticVerificationResultV1 = field(
        repr=False, compare=False
    )
    closure: TwoStageAccountingClosureV1 = field(repr=False, compare=False)
    public_identity: tuple[tuple[str, str], ...]
    issuer: object = field(repr=False, compare=False)


_FAILED_PREFIX_PUBLIC_FIELDS = (
    "operational_execution_id",
    "model_only_result_id",
    "route_decision_context_id",
    "abstract_audit_id",
    "abstract_audit_attestation_id",
    "verification_work_record_id",
    "accounting_core_seal_id",
    "verification_charge_plan_id",
    "aggregate_work_vector_id",
    "aggregate_comparison_vector_id",
    "verification_charge_manifest_id",
    "verification_charge_receipt_id",
)


@dataclass(frozen=True, slots=True)
class ModelOnlyFailedPrefixAccountingAuthorityV1:
    """Opaque live authority for one fully charged model-only FAIL prefix."""

    operational_execution_id: str
    model_only_result_id: str
    route_decision_context_id: str
    abstract_audit_id: str
    abstract_audit_attestation_id: str
    verification_work_record_id: str
    accounting_core_seal_id: str
    verification_charge_plan_id: str
    aggregate_work_vector_id: str
    aggregate_comparison_vector_id: str
    verification_charge_manifest_id: str
    verification_charge_receipt_id: str
    _mint: _FailedPrefixAccountingMintV1 = field(repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_FAILED_PREFIX_ACCOUNTING_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise Phase3EModelFailureConsumerV1Error(
                    "failed-prefix accounting is a copied or modified live authority"
                ) from error
        if (
            type(self._mint) is not _FailedPrefixAccountingMintV1
            or self._mint.issuer is not _FAILED_PREFIX_ACCOUNTING_AUTHORITY
        ):
            raise Phase3EModelFailureConsumerV1Error(
                "failed-prefix accounting authority lacks its live mint"
            )
        public_identity = tuple(
            (name, getattr(self, name)) for name in _FAILED_PREFIX_PUBLIC_FIELDS
        )
        if public_identity != self._mint.public_identity:
            raise Phase3EModelFailureConsumerV1Error(
                "failed-prefix accounting public identity differs from its mint"
            )
        for name, value in public_identity:
            try:
                parse_content_id(value)
            except ValueError as error:
                raise Phase3EModelFailureConsumerV1Error(
                    f"{name} must be a full content ID"
                ) from error
        execution = verify_model_only_failed_prefix_execution_v1(
            self._mint.execution
        )
        audit = require_semantic_verification_result_v1(
            self._mint.audit_authority, SemanticRole.ABSTRACT_AUDIT
        )
        verify_typed_attestation_v1(audit.attestation, authority_result=audit)
        closure = self._mint.closure
        if (
            audit.outcome != "FAIL"
            or audit.artifact != execution.model_only_result.audit
            or audit.binding.route_context
            != execution.model_only_result.route_context
            or execution.operational_execution_id
            != self.operational_execution_id
            or execution.model_only_result.result_id != self.model_only_result_id
            or execution.model_only_result.route_context.route_decision_context_id
            != self.route_decision_context_id
            or audit.attestation.artifact_id != self.abstract_audit_id
            or audit.attestation.verification_attestation_id
            != self.abstract_audit_attestation_id
            or audit.verification_work_record.record_id
            != self.verification_work_record_id
            or closure.core.accounting_core_seal_id
            != self.accounting_core_seal_id
            or closure.plan.verification_charge_plan_id
            != self.verification_charge_plan_id
            or closure.aggregate_work.work_vector.work_vector_id
            != self.aggregate_work_vector_id
            or closure.aggregate_work.comparison_vector.comparison_vector_id
            != self.aggregate_comparison_vector_id
            or closure.manifest.verification_charge_manifest_id
            != self.verification_charge_manifest_id
            or closure.receipt.verification_charge_receipt_id
            != self.verification_charge_receipt_id
            or closure.core.core_work_vector_id
            != execution.recorded_work.work_vector.work_vector_id
            or closure.aggregate_work.work_vector.route_kind
            is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
            or closure.aggregate_work.actual_projection_proof.work_scope
            is not ActualWorkScope.COMMON_PREFIX
        ):
            raise Phase3EModelFailureConsumerV1Error(
                "failed-prefix accounting authority retains a spliced chain"
            )

    def __copy__(self) -> object:
        raise Phase3EModelFailureConsumerV1Error(
            "failed-prefix accounting live authority cannot be copied"
        )

    def __deepcopy__(self, memo: dict[int, object]) -> object:
        raise Phase3EModelFailureConsumerV1Error(
            "failed-prefix accounting live authority cannot be deep-copied"
        )

    def __reduce_ex__(self, protocol: int) -> object:
        raise Phase3EModelFailureConsumerV1Error(
            "failed-prefix accounting live authority cannot be serialized"
        )

    @property
    def execution(self) -> ModelOnlyQueryExecutionV1:
        return self._mint.execution

    @property
    def audit_authority(self) -> SemanticVerificationResultV1:
        return self._mint.audit_authority

    @property
    def closure(self) -> TwoStageAccountingClosureV1:
        return self._mint.closure

    @property
    def aggregate_work(self) -> RecordedWorkV1:
        return self._mint.closure.aggregate_work

    @property
    def failed_prefix_accounting_authority_id(self) -> str:
        return content_id(
            MODEL_ONLY_FAILED_PREFIX_ACCOUNTING_AUTHORITY_DOMAIN,
            {
                "schema": "acfqp.model_only_failed_prefix_accounting_authority.v1",
                **dict(
                    (name, getattr(self, name))
                    for name in _FAILED_PREFIX_PUBLIC_FIELDS
                ),
            },
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.model_only_failed_prefix_accounting_authority.v1",
            **dict((name, getattr(self, name)) for name in _FAILED_PREFIX_PUBLIC_FIELDS),
            "failed_prefix_accounting_authority_id": (
                self.failed_prefix_accounting_authority_id
            ),
        }


def mint_model_only_failed_prefix_accounting_authority_v1(
    execution: ModelOnlyQueryExecutionV1,
    *,
    abstract_audit_authority: SemanticVerificationResultV1,
    charge_preparation: ModelOnlyFailedPrefixChargePreparationV1,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> ModelOnlyFailedPrefixAccountingAuthorityV1:
    """Close the preregistered audit suffix and mint an opaque continuation."""

    retained = verify_model_only_failed_prefix_execution_v1(execution)
    trusted_registry, trusted_profile = _official_profiles_v1(
        registry, comparison_profile
    )
    if type(charge_preparation) is not ModelOnlyFailedPrefixChargePreparationV1:
        raise Phase3EModelFailureConsumerV1Error(
            "failed-prefix mint requires its typed pre-verification charge plan"
        )
    audit = require_semantic_verification_result_v1(
        abstract_audit_authority, SemanticRole.ABSTRACT_AUDIT
    )
    verify_typed_attestation_v1(audit.attestation, authority_result=audit)
    if (
        audit.outcome != "FAIL"
        or audit.artifact != retained.model_only_result.audit
        or audit.binding != charge_preparation.audit_binding
        or audit.verification_work_record
        != charge_preparation.verification_work_record
        or charge_preparation.operational_execution_id
        != retained.operational_execution_id
    ):
        raise Phase3EModelFailureConsumerV1Error(
            "ABSTRACT_AUDIT authority differs from the frozen prefix obligation"
        )
    expected_preparation = freeze_model_only_failed_prefix_charge_v1(
        retained,
        audit_binding=audit.binding,
        verification_work_record=audit.verification_work_record,
        plan_frozen_at_protocol_step=(
            charge_preparation.plan.plan_frozen_at_protocol_step
        ),
        registry=trusted_registry,
        comparison_profile=trusted_profile,
    )
    if expected_preparation != charge_preparation:
        raise Phase3EModelFailureConsumerV1Error(
            "failed-prefix core or charge plan was substituted"
        )
    closure = derive_two_stage_accounting_v1(
        core=charge_preparation.core,
        core_work=retained.recorded_work,
        plan=charge_preparation.plan,
        semantic_results=(audit,),
        route_context=retained.model_only_result.route_context,
        registry=trusted_registry,
        comparison_profile=trusted_profile,
        actual_profile=official_actual_projection_profile_v1(
            trusted_registry, trusted_profile
        ),
    )
    public = {
        "operational_execution_id": retained.operational_execution_id,
        "model_only_result_id": retained.model_only_result.result_id,
        "route_decision_context_id": (
            retained.model_only_result.route_context.route_decision_context_id
        ),
        "abstract_audit_id": audit.attestation.artifact_id,
        "abstract_audit_attestation_id": (
            audit.attestation.verification_attestation_id
        ),
        "verification_work_record_id": audit.verification_work_record.record_id,
        "accounting_core_seal_id": closure.core.accounting_core_seal_id,
        "verification_charge_plan_id": closure.plan.verification_charge_plan_id,
        "aggregate_work_vector_id": (
            closure.aggregate_work.work_vector.work_vector_id
        ),
        "aggregate_comparison_vector_id": (
            closure.aggregate_work.comparison_vector.comparison_vector_id
        ),
        "verification_charge_manifest_id": (
            closure.manifest.verification_charge_manifest_id
        ),
        "verification_charge_receipt_id": (
            closure.receipt.verification_charge_receipt_id
        ),
    }
    mint = _FailedPrefixAccountingMintV1(
        retained,
        audit,
        closure,
        tuple((name, public[name]) for name in _FAILED_PREFIX_PUBLIC_FIELDS),
        _FAILED_PREFIX_ACCOUNTING_AUTHORITY,
    )
    authority = ModelOnlyFailedPrefixAccountingAuthorityV1(
        **public,
        _mint=mint,
    )
    return bind_runtime_authority_v1(
        authority,
        issuer=_FAILED_PREFIX_ACCOUNTING_AUTHORITY,
    )


def verify_and_mint_model_only_failed_prefix_accounting_authority_v1(
    execution: ModelOnlyQueryExecutionV1,
    *,
    source: ModelOnlyRAPMSourceV1,
    plan_frozen_at_protocol_step: int = 1,
    verified_at_protocol_step: int = 2,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> ModelOnlyFailedPrefixAccountingAuthorityV1:
    """Honest convenience path: freeze, verify ABSTRACT_AUDIT, then mint."""

    retained = verify_model_only_failed_prefix_execution_v1(execution)
    trusted_registry, trusted_profile = _official_profiles_v1(
        registry, comparison_profile
    )
    binding = AttestationContextV1(
        retained.model_only_result.route_context,
        TypedNotApplicable(FAILED_PREFIX_AUDIT_DECISION_NA),
        TypedNotApplicable(FAILED_PREFIX_AUDIT_TRANSACTION_NA),
        verified_at_protocol_step,
        LaneEnum.OPERATIONAL,
    )
    record = _verification_record_v1(
        SemanticRole.ABSTRACT_AUDIT,
        "failed-prefix",
        trusted_registry,
    )
    preparation = freeze_model_only_failed_prefix_charge_v1(
        retained,
        audit_binding=binding,
        verification_work_record=record,
        plan_frozen_at_protocol_step=plan_frozen_at_protocol_step,
        registry=trusted_registry,
        comparison_profile=trusted_profile,
    )
    audit = verify_abstract_plan_audit_semantics_v1(
        retained.model_only_result.audit,
        source=source,
        model_only_result=retained.model_only_result,
        binding=binding,
        verification_work_record=record,
        registry=trusted_registry,
    )
    return mint_model_only_failed_prefix_accounting_authority_v1(
        retained,
        abstract_audit_authority=audit,
        charge_preparation=preparation,
        registry=trusted_registry,
        comparison_profile=trusted_profile,
    )


def require_model_only_failed_prefix_accounting_authority_v1(
    authority: object,
) -> ModelOnlyFailedPrefixAccountingAuthorityV1:
    if type(authority) is not ModelOnlyFailedPrefixAccountingAuthorityV1:
        raise Phase3EModelFailureConsumerV1Error(
            "a retained failed-prefix accounting authority is required; bare work is forbidden"
        )
    try:
        require_runtime_authority_v1(
            authority,
            issuer=_FAILED_PREFIX_ACCOUNTING_AUTHORITY,
        )
    except ValueError as error:
        raise Phase3EModelFailureConsumerV1Error(
            "failed-prefix accounting is not the retained minted instance"
        ) from error
    authority.__post_init__()
    return authority


def official_safe_chain_fallback_cap_profile_v1() -> GroundFallbackCapProfileV1:
    """Return the finite sealed cap frozen for the safe-chain H2 fallback."""

    return GroundFallbackCapProfileV1(
        max_states_expanded=20,
        max_actions_evaluated=48,
        max_ground_steps=48,
        max_outcome_rows=192,
        max_bellman_backups=5_696,
        max_composed_candidates=5_696,
        max_cap_checks=5_815,
        max_positive_outcomes_per_step=4,
        reserved_route_cap_checks=3,
        profile_key=SEALED_ROUTE_CAP_PROFILE_KEY,
    )


@dataclass(frozen=True, slots=True)
class ModelFailureRouteAuthoritiesV1:
    """Retained exact preselection artifacts and semantic authorities."""

    prepared_local: SafeChainPreparedEstimateContext = field(repr=False)
    frontier: object
    causal: object
    transaction: TransactionV1
    local_source: object = field(repr=False)
    local_bound: object
    local_cardinality: object
    local_formula: object
    local_upper: object
    causal_result: SemanticVerificationResultV1 = field(repr=False)
    local_cardinality_result: SemanticVerificationResultV1 = field(repr=False)
    local_upper_result: SemanticVerificationResultV1 = field(repr=False)
    fallback_source: object = field(repr=False)
    fallback_bound: object
    fallback_cardinality: object
    fallback_formula: object
    fallback_upper: object
    fallback_cardinality_result: SemanticVerificationResultV1 = field(repr=False)
    fallback_upper_result: SemanticVerificationResultV1 = field(repr=False)
    decision: MarginalRouteDecisionV1
    decision_result: SemanticVerificationResultV1 = field(repr=False)


@dataclass(frozen=True, slots=True)
class _PreparedConsumerMintV1:
    failed_prefix_authority: ModelOnlyFailedPrefixAccountingAuthorityV1 = field(
        repr=False, compare=False
    )
    ground_binding: GroundBindingAfterFailedAuditV1 = field(
        repr=False, compare=False
    )
    runtime_manifest: RuntimeTreeManifestV1 = field(repr=False, compare=False)
    runtime_cardinality: RuntimeFactoryCardinalityV1 = field(
        repr=False, compare=False
    )
    route_authorities: ModelFailureRouteAuthoritiesV1 = field(
        repr=False, compare=False
    )
    route_preparation_accounting: ModelFailurePreparationAccountingV1 = field(
        repr=False, compare=False
    )
    prepared: PreparedPhase3ERunV1 = field(repr=False, compare=False)
    selected_recipe: ExecutorRecipeV1 = field(repr=False, compare=False)
    selected_factory: SealedPostFreezeExecutorFactoryV1 = field(
        repr=False, compare=False
    )
    runtime_cas: RuntimeTreeCASV1 = field(repr=False, compare=False)
    public_identity: tuple[tuple[str, str], ...]
    issuer: object = field(repr=False, compare=False)


_PREPARED_CONSUMER_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class PreparedModelFailureConsumerV1:
    """Validated preparation plus the one selected, still-inert factory."""

    failed_prefix_authority: ModelOnlyFailedPrefixAccountingAuthorityV1
    ground_binding_id: str
    runtime_manifest: RuntimeTreeManifestV1
    runtime_cardinality: RuntimeFactoryCardinalityV1
    route_authorities: ModelFailureRouteAuthoritiesV1
    route_preparation_accounting: ModelFailurePreparationAccountingV1
    prepared: PreparedPhase3ERunV1
    selected_recipe: ExecutorRecipeV1
    selected_factory: SealedPostFreezeExecutorFactoryV1 = field(
        repr=False, compare=False
    )
    _mint: _PreparedConsumerMintV1 = field(repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )
    accounting_status: str = MODEL_FAILURE_CONSUMER_STATUS
    accounting_blockers: tuple[str, ...] = (
        MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS
    )
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_PREPARED_CONSUMER_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise Phase3EModelFailureConsumerV1Error(
                    "prepared model-failure consumer is a copied or modified live authority"
                ) from error
        if (
            type(self._mint) is not _PreparedConsumerMintV1
            or self._mint.issuer is not _PREPARED_CONSUMER_AUTHORITY
        ):
            raise Phase3EModelFailureConsumerV1Error(
                "prepared model-failure consumer lacks its live mint"
            )
        if (
            self.accounting_status != MODEL_FAILURE_CONSUMER_STATUS
            or self.accounting_blockers
            != MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS
            or self.official_execution_allowed is not False
        ):
            raise Phase3EModelFailureConsumerV1Error(
                "model-failure consumer cannot hide its native-accounting blockers"
            )
        if (
            self.failed_prefix_authority
            is not self._mint.failed_prefix_authority
            or self.runtime_manifest is not self._mint.runtime_manifest
            or self.runtime_cardinality is not self._mint.runtime_cardinality
            or self.route_authorities is not self._mint.route_authorities
            or self.route_preparation_accounting
            is not self._mint.route_preparation_accounting
            or self.prepared is not self._mint.prepared
            or self.selected_recipe is not self._mint.selected_recipe
            or self.selected_factory is not self._mint.selected_factory
        ):
            raise Phase3EModelFailureConsumerV1Error(
                "prepared consumer live members differ from its retained mint"
            )
        expected_public = (
            (
                "failed_prefix_accounting_authority_id",
                self.failed_prefix_authority.failed_prefix_accounting_authority_id,
            ),
            ("ground_binding_id", self.ground_binding_id),
            ("runtime_tree_id", self.runtime_manifest.runtime_tree_id),
            (
                "runtime_factory_cardinality_id",
                self.runtime_cardinality.runtime_factory_cardinality_id,
            ),
            (
                "route_decision_id",
                self.route_authorities.decision.route_decision_id,
            ),
            (
                "model_failure_preparation_accounting_id",
                self.route_preparation_accounting.model_failure_preparation_accounting_id,
            ),
            ("executor_recipe_id", self.selected_recipe.executor_recipe_id),
        )
        if expected_public != self._mint.public_identity:
            raise Phase3EModelFailureConsumerV1Error(
                "prepared consumer public identity differs from its mint"
            )

    def __copy__(self) -> object:
        raise Phase3EModelFailureConsumerV1Error(
            "prepared model-failure consumer live authority cannot be copied"
        )

    def __deepcopy__(self, memo: dict[int, object]) -> object:
        raise Phase3EModelFailureConsumerV1Error(
            "prepared model-failure consumer live authority cannot be deep-copied"
        )

    def __reduce_ex__(self, protocol: int) -> object:
        raise Phase3EModelFailureConsumerV1Error(
            "prepared model-failure consumer live authority cannot be serialized"
        )

    @property
    def ground_binding(self) -> GroundBindingAfterFailedAuditV1:
        return self._mint.ground_binding

    @property
    def selected_route(self) -> RouteSelection:
        return self.route_authorities.decision.selected_route

    def validate_before_run(
        self,
        *,
        registry: CounterRegistryV1 | None = None,
        comparison_profile: ComparisonProfileV1 | None = None,
    ) -> None:
        try:
            require_runtime_authority_v1(
                self,
                issuer=_PREPARED_CONSUMER_AUTHORITY,
            )
        except ValueError as error:
            raise Phase3EModelFailureConsumerV1Error(
                "prepared model-failure consumer is not the retained minted instance"
            ) from error
        trusted_registry, trusted_profile = _official_profiles_v1(
            registry, comparison_profile
        )
        prefix = require_model_only_failed_prefix_accounting_authority_v1(
            self.failed_prefix_authority
        )
        ground = require_ground_binding_after_failed_audit_v1(
            self._mint.ground_binding
        )
        factory = require_sealed_executor_factory_v1(self.selected_factory)
        route_preparation = verify_model_failure_preparation_accounting_v1(
            self.route_preparation_accounting,
            registry=trusted_registry,
            comparison_profile=trusted_profile,
        )
        if (
            ground.ground_binding_id != self.ground_binding_id
            or ground.semantic_authority is not prefix.audit_authority
            or self.runtime_cardinality
            != RuntimeFactoryCardinalityV1.from_manifest(self.runtime_manifest)
            or factory.runtime_cas != self._mint.runtime_cas
            or factory.recipe != self.selected_recipe
            or self.selected_recipe.selected_route is not self.selected_route
            or route_preparation.source_prefix is not prefix.aggregate_work
            or self.prepared.common_prefix_work is not prefix.aggregate_work
            or route_preparation.trace.route_decision_context_id
            != self.prepared.context.route_decision_context_id
            or route_preparation.trace.causal_evidence_id
            != self.route_authorities.causal.causal_evidence_id
            or route_preparation.trace.events[-1].evidence_id
            != self.route_authorities.decision.route_decision_id
            or self.prepared.runtime_tree_id != self.runtime_manifest.runtime_tree_id
            or self.prepared.executor_recipe_id
            != self.selected_recipe.executor_recipe_id
            or factory.construction_accounting is not None
        ):
            raise Phase3EModelFailureConsumerV1Error(
                "prepared consumer/factory/prefix authority chain is stale or already invoked"
            )
        self.selected_recipe.validate_runtime(self.runtime_manifest)
        decision, _upper, common_closure = self.prepared.validate(
            trusted_registry, trusted_profile
        )
        if (
            common_closure is None
            or decision != self.route_authorities.decision
            or decision.selected_route is not self.selected_route
        ):
            raise Phase3EModelFailureConsumerV1Error(
                "prepared runner validation changed the selected route"
            )


def _preselection_reads_v1(
    *,
    context: RouteDecisionContextV1,
    point: DecisionPointV1,
    reusable_rapm_id: str,
    failed_certificate_id: str,
    action_catalogue_id: str,
    selected_upper: Any,
) -> tuple[Phase3EPreselectionReadV1, ...]:
    values = {
        AccessOperation.READ_FROZEN_RAPM: reusable_rapm_id,
        AccessOperation.READ_FROZEN_BUILD_EPOCH: context.build_epoch_id,
        AccessOperation.READ_FAILED_CERTIFICATE: failed_certificate_id,
        AccessOperation.READ_SELECTED_PLAN: context.selected_plan_id,
        AccessOperation.READ_ACTION_CATALOGUE: action_catalogue_id,
        AccessOperation.READ_FRONTIER_IDENTITIES: point.frontier_snapshot_id,
        AccessOperation.READ_PROOF_CIRCUIT_METADATA: point.causal_evidence_id,
        AccessOperation.READ_PREREGISTERED_CARDINALITIES: (
            selected_upper.cardinality_evidence_id
        ),
        AccessOperation.READ_CAP_REGISTRY: selected_upper.route_cap_profile_id,
        AccessOperation.READ_FORMULA_REGISTRY: selected_upper.formula_id,
        AccessOperation.READ_PROFILE_REGISTRY: context.comparison_profile_id,
    }
    return tuple(
        Phase3EPreselectionReadV1(operation, values[operation])
        for operation in PRESELECTION_READ_OPERATIONS
    )


def prepare_phase3e_from_model_failure_v1(
    failed_prefix_authority: ModelOnlyFailedPrefixAccountingAuthorityV1,
    ground_binding: GroundBindingAfterFailedAuditV1,
    *,
    runtime_manifest: RuntimeTreeManifestV1,
    runtime_cardinality: RuntimeFactoryCardinalityV1,
    runtime_cas: RuntimeTreeCASV1,
    local_cap_profile: RouteCapProfileV1 | None = None,
    fallback_cap_profile: GroundFallbackCapProfileV1 | None = None,
    source_frozen_at_protocol_step: int = 10,
    common_plan_frozen_at_protocol_step: int = 20,
    verified_at_protocol_step: int = 21,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> PreparedModelFailureConsumerV1:
    """Prepare the H2 model-failure route decision without route execution."""

    trusted_registry, trusted_profile = _official_profiles_v1(
        registry, comparison_profile
    )
    prefix = require_model_only_failed_prefix_accounting_authority_v1(
        failed_prefix_authority
    )
    ground = require_ground_binding_after_failed_audit_v1(ground_binding)
    if type(runtime_manifest) is not RuntimeTreeManifestV1:
        raise Phase3EModelFailureConsumerV1Error(
            "consumer requires a prebuilt RuntimeTreeManifestV1"
        )
    if type(runtime_cardinality) is not RuntimeFactoryCardinalityV1:
        raise Phase3EModelFailureConsumerV1Error(
            "consumer requires prebuilt RuntimeFactoryCardinalityV1"
        )
    if type(runtime_cas) is not RuntimeTreeCASV1:
        raise Phase3EModelFailureConsumerV1Error(
            "consumer requires a typed runtime CAS handle"
        )
    parsed_manifest = RuntimeTreeManifestV1.from_dict(runtime_manifest.to_dict())
    parsed_cardinality = RuntimeFactoryCardinalityV1.from_dict(
        runtime_cardinality.to_dict()
    )
    if (
        parsed_manifest != runtime_manifest
        or parsed_cardinality != runtime_cardinality
        or runtime_cardinality
        != RuntimeFactoryCardinalityV1.from_manifest(runtime_manifest)
    ):
        raise Phase3EModelFailureConsumerV1Error(
            "runtime cardinality differs from its prebuilt manifest"
        )
    execution = prefix.execution
    result = execution.model_only_result
    if (
        result.outcome is not ModelOnlyOutcome.FAIL
        or result.source_lease.query_key != LOCAL_QUERY_KEY
        or result.route_context != prefix.audit_authority.binding.route_context
        or result.result_id != ground.model_only_result_id
        or ground.semantic_authority is not prefix.audit_authority
        or prefix.aggregate_work.work_vector.subject_id
        != result.route_context.route_attempt_id
        or prefix.aggregate_work.work_vector.route_kind
        is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
    ):
        raise Phase3EModelFailureConsumerV1Error(
            "consumer requires one exact accounted safe-chain H2 FAIL handoff"
        )

    context = result.route_context
    preparation_events = ModelFailurePreparationEventRecorderV1(
        route_decision_context_id=context.route_decision_context_id,
        route_attempt_id=context.route_attempt_id,
        source_prefix_work_vector_id=(
            prefix.aggregate_work.work_vector.work_vector_id
        ),
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "official-accounting-profiles-validated",
        trusted_profile.comparison_profile_id,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "failed-prefix-authority-validated",
        prefix.failed_prefix_accounting_authority_id,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "ground-binding-authority-validated",
        ground.ground_binding_id,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "runtime-input-types-validated",
        runtime_manifest.runtime_tree_id,
    )
    preparation_events.observe(
        PreparationEventKind.INTEGRITY_CHECK,
        "runtime-manifest-roundtrip-validated",
        runtime_manifest.runtime_tree_id,
    )
    preparation_events.observe(
        PreparationEventKind.INTEGRITY_CHECK,
        "runtime-cardinality-roundtrip-validated",
        runtime_cardinality.runtime_factory_cardinality_id,
    )
    preparation_events.observe(
        PreparationEventKind.INTEGRITY_CHECK,
        "runtime-manifest-cardinality-binding-validated",
        runtime_cardinality.runtime_factory_cardinality_id,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "failed-query-chain-validated",
        result.result_id,
    )

    prepared_local = prepare_safe_chain_estimate_from_verified_model_failure_v1(
        ground,
        model_only_result=result,
        abstract_audit_authority=prefix.audit_authority,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "prepared-estimate-derived-from-failed-authority",
        ground.ground_binding_id,
    )
    verified_model_binding = require_verified_model_estimate_binding_v1(
        prepared_local
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "verified-model-estimate-binding-replayed",
        verified_model_binding.ground_binding_id,
    )
    local_cap = local_cap_profile or RouteCapProfileV1()
    fallback_cap = (
        fallback_cap_profile or official_safe_chain_fallback_cap_profile_v1()
    )
    if (
        type(local_cap) is not RouteCapProfileV1
        or type(fallback_cap) is not GroundFallbackCapProfileV1
    ):
        raise Phase3EModelFailureConsumerV1Error(
            "consumer cap profiles require their exact V1 types"
        )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "route-cap-profile-types-validated",
        local_cap.route_cap_profile_id,
    )
    if (
        type(source_frozen_at_protocol_step) is not int
        or type(common_plan_frozen_at_protocol_step) is not int
        or type(verified_at_protocol_step) is not int
        or source_frozen_at_protocol_step < 0
        or common_plan_frozen_at_protocol_step
        <= source_frozen_at_protocol_step
        or verified_at_protocol_step
        <= common_plan_frozen_at_protocol_step
    ):
        raise Phase3EModelFailureConsumerV1Error(
            "route preparation protocol steps are not strictly ordered"
        )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "protocol-step-order-validated",
        context.route_decision_context_id,
    )

    frontier, causal = derive_safe_chain_local_frontier_and_causal_v1(
        prepared=prepared_local,
        context=context,
        cap_profile=local_cap,
        frontier_stage=1,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "causal-frontier-derived",
        frontier.frontier_snapshot_id,
    )
    preparation_events.observe_causal_candidates(
        causal_evidence_id=causal.causal_evidence_id,
        evaluated_candidate_count=causal.evaluated_candidate_count,
    )
    if causal.evaluated_candidate_count > dict(local_cap.limits)[
        "max_causal_candidate_evaluations"
    ]:
        raise Phase3EModelFailureConsumerV1Error(
            "causal evaluation count exceeds the selected local cap"
        )
    preparation_events.observe(
        PreparationEventKind.CAP_CHECK,
        "causal-evaluation-cap-checked",
        causal.causal_evidence_id,
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        1,
        frontier.frontier_snapshot_id,
        causal.causal_evidence_id,
        prefix.aggregate_work.work_vector.work_vector_id,
    )
    transaction = TransactionV1(
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        1,
        frontier.frontier_snapshot_id,
        local_cap.route_cap_profile_id,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "decision-point-transaction-bound",
        transaction.transaction_id,
    )
    local_source = derive_safe_chain_local_preselection_source_v1(
        prepared=prepared_local,
        context=context,
        frontier=frontier,
        causal=causal,
        decision_point=point,
        transaction=transaction,
        cap_profile=local_cap,
        frozen_at_protocol_step=source_frozen_at_protocol_step,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "local-cardinality-source-derived",
        local_source.source_artifact_id,
    )
    local_bound = derive_safe_chain_local_cardinality_bound_v1(
        source=local_source,
        cap_profile=local_cap,
        registry=trusted_registry,
        runtime_factory_cardinality=runtime_cardinality,
    )
    preparation_events.observe(
        PreparationEventKind.CAP_CHECK,
        "local-cardinality-bound-cap-checked",
        local_bound.local_cardinality_bound_id,
    )
    local_cardinality = build_safe_chain_local_cardinality_evidence_v1(
        context=context,
        decision_point=point,
        transaction=transaction,
        cap_profile=local_cap,
        bound=local_bound,
    )
    preparation_events.observe(
        PreparationEventKind.CAP_CHECK,
        "local-cardinality-evidence-cap-checked",
        local_cardinality.cardinality_evidence_id,
    )
    local_formula = official_route_upper_formula_v1(
        RouteKind.LOCAL_ATTEMPT,
        registry=trusted_registry,
        profile=trusted_profile,
        cap_profile=local_cap,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "local-upper-formula-bound",
        local_formula.formula_id,
    )
    local_upper, local_proof = derive_route_upper_v1(
        context=context,
        decision_point=point,
        cardinality=local_cardinality,
        cap_profile=local_cap,
        registry=trusted_registry,
        profile=trusted_profile,
        formula=local_formula,
        transaction=transaction,
        causal=causal,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "local-upper-derived",
        local_upper.route_upper_bound_envelope_id,
    )

    fallback_source = derive_safe_chain_fallback_cardinality_source_v1(
        world=ground.world,
        context=context,
        decision_point=point,
        cap_profile=fallback_cap,
        frozen_at_protocol_step=source_frozen_at_protocol_step,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "fallback-cardinality-source-derived",
        fallback_source.source_artifact_id,
    )
    fallback_bound = derive_safe_chain_fallback_cardinality_bound_v1(
        source=fallback_source,
        cap_profile=fallback_cap,
        runtime_factory_cardinality=runtime_cardinality,
    )
    preparation_events.observe(
        PreparationEventKind.CAP_CHECK,
        "fallback-cardinality-bound-cap-checked",
        fallback_bound.ground_fallback_cardinality_bound_id,
    )
    fallback_cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=point,
        cap_profile=fallback_cap,
        bound=fallback_bound,
    )
    preparation_events.observe(
        PreparationEventKind.CAP_CHECK,
        "fallback-cardinality-evidence-cap-checked",
        fallback_cardinality.cardinality_evidence_id,
    )
    fallback_formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=trusted_registry,
        profile=trusted_profile,
        cap_profile=fallback_cap,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "fallback-upper-formula-bound",
        fallback_formula.formula_id,
    )
    fallback_upper, fallback_proof = derive_route_upper_v1(
        context=context,
        decision_point=point,
        cardinality=fallback_cardinality,
        cap_profile=fallback_cap,
        registry=trusted_registry,
        profile=trusted_profile,
        formula=fallback_formula,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "fallback-upper-derived",
        fallback_upper.route_upper_bound_envelope_id,
    )

    # The raw artifacts and strict selector determine every obligation ID
    # before any semantic verifier below is invoked.
    raw_decision = MarginalRouteDecisionV1.select(
        point,
        fallback_upper,
        causal=causal,
        local_upper=local_upper,
    )
    preparation_events.observe(
        PreparationEventKind.PROTOCOL_CHECK,
        "marginal-route-decision-derived",
        raw_decision.route_decision_id,
    )
    preparation_trace = preparation_events.seal(
        causal_evidence_id=causal.causal_evidence_id,
        causal_candidate_count=causal.evaluated_candidate_count,
    )
    route_preparation_accounting = (
        derive_model_failure_preparation_accounting_v1(
            trace=preparation_trace,
            source_prefix=prefix.aggregate_work,
            registry=trusted_registry,
            comparison_profile=trusted_profile,
        )
    )
    local_binding = AttestationContextV1(
        context,
        point.decision_point_id,
        transaction.transaction_id,
        verified_at_protocol_step,
        LaneEnum.OPERATIONAL,
    )
    fallback_binding = AttestationContextV1(
        context,
        point.decision_point_id,
        TypedNotApplicable(FALLBACK_TRANSACTION_NA),
        verified_at_protocol_step,
        LaneEnum.OPERATIONAL,
    )
    common_core = seal_accounting_core_v1(
        recorded_work=prefix.aggregate_work,
        binding=AttestationContextV1(
            context,
            point.decision_point_id,
            TypedNotApplicable(COMMON_PREFIX_TRANSACTION_NA),
            common_plan_frozen_at_protocol_step,
            LaneEnum.OPERATIONAL,
        ),
        core_stage=AccountingCoreStage.COMMON_PREFIX,
        registry=trusted_registry,
        comparison_profile=trusted_profile,
        actual_profile=official_actual_projection_profile_v1(
            trusted_registry, trusted_profile
        ),
    )
    obligation_specs = (
        (SemanticRole.CAUSAL_SEARCH, causal.causal_evidence_id, "FOUND", local_binding, "local-causal"),
        (SemanticRole.CARDINALITY_EVIDENCE, local_cardinality.cardinality_evidence_id, "VALID", local_binding, "local-cardinality"),
        (SemanticRole.ROUTE_UPPER, local_upper.route_upper_bound_envelope_id, "VALID", local_binding, "local-upper"),
        (SemanticRole.CARDINALITY_EVIDENCE, fallback_cardinality.cardinality_evidence_id, "VALID", fallback_binding, "fallback-cardinality"),
        (SemanticRole.ROUTE_UPPER, fallback_upper.route_upper_bound_envelope_id, "VALID", fallback_binding, "fallback-upper"),
        (SemanticRole.ROUTE_DECISION, raw_decision.route_decision_id, raw_decision.selected_route.value, local_binding, "route-decision"),
    )
    records = tuple(
        _verification_record_v1(role, instance, trusted_registry)
        for role, _artifact_id, _outcome, _binding, instance in obligation_specs
    )
    common_plan = VerificationChargePlanV1.for_core(
        common_core,
        plan_frozen_at_protocol_step=common_plan_frozen_at_protocol_step,
        obligations=tuple(
            VerificationChargeObligationV1.for_role(
                ordinal=index,
                artifact_id=artifact_id,
                role=role,
                expected_result=outcome,
                verified_at_protocol_step=verified_at_protocol_step,
                verification_work_record=records[index],
                binding=binding,
            )
            for index, (role, artifact_id, outcome, binding, _instance) in enumerate(
                obligation_specs
            )
        ),
    )

    causal_result = verify_safe_chain_local_causal_semantics_v1(
        causal,
        source=local_source,
        frozen_world=ground.world,
        context=context,
        frontier=frontier,
        decision_point=point,
        transaction=transaction,
        cap_profile=local_cap,
        binding=local_binding,
        verification_work_record=records[0],
        registry=trusted_registry,
        verified_prepared=prepared_local,
    )
    local_cardinality_result = verify_safe_chain_local_cardinality_semantics_v1(
        local_cardinality,
        source=local_source,
        bound=local_bound,
        causal_result=causal_result,
        frozen_world=ground.world,
        context=context,
        frontier=frontier,
        decision_point=point,
        transaction=transaction,
        cap_profile=local_cap,
        binding=local_binding,
        verification_work_record=records[1],
        registry=trusted_registry,
        runtime_factory_cardinality=runtime_cardinality,
        runtime_manifest=runtime_manifest,
        verified_prepared=prepared_local,
    )
    local_upper_result = verify_route_upper_semantics_v1(
        local_upper,
        derivation_proof=local_proof,
        cardinality_result=local_cardinality_result,
        context=context,
        decision_point=point,
        cap_profile=local_cap,
        formula=local_formula,
        transaction=transaction,
        causal=causal,
        binding=local_binding,
        verification_work_record=records[2],
        registry=trusted_registry,
    )
    fallback_cardinality_result = (
        verify_safe_chain_fallback_cardinality_semantics_v1(
            fallback_cardinality,
            source=fallback_source,
            bound=fallback_bound,
            frozen_world=ground.world,
            context=context,
            decision_point=point,
            cap_profile=fallback_cap,
            binding=fallback_binding,
            verification_work_record=records[3],
            registry=trusted_registry,
            runtime_factory_cardinality=runtime_cardinality,
            runtime_manifest=runtime_manifest,
            verified_ground_binding=ground,
        )
    )
    fallback_upper_result = verify_route_upper_semantics_v1(
        fallback_upper,
        derivation_proof=fallback_proof,
        cardinality_result=fallback_cardinality_result,
        context=context,
        decision_point=point,
        cap_profile=fallback_cap,
        formula=fallback_formula,
        transaction=None,
        causal=None,
        binding=fallback_binding,
        verification_work_record=records[4],
        registry=trusted_registry,
    )
    decision = derive_guarded_marginal_route_decision_v1(
        context=context,
        decision_point=point,
        fallback_upper_result=fallback_upper_result,
        local_upper_result=local_upper_result,
        causal_result=causal_result,
        binding=local_binding,
    )
    if decision != raw_decision:
        raise Phase3EModelFailureConsumerV1Error(
            "semantic route authorities changed the preregistered decision"
        )
    decision_result = verify_marginal_route_decision_semantics_v1(
        decision,
        context=context,
        decision_point=point,
        fallback_upper_result=fallback_upper_result,
        causal_result=causal_result,
        local_upper_result=local_upper_result,
        binding=local_binding,
        verification_work_record=records[5],
        registry=trusted_registry,
    )
    charged_results = (
        causal_result,
        local_cardinality_result,
        local_upper_result,
        fallback_cardinality_result,
        fallback_upper_result,
        decision_result,
    )
    selected_upper = (
        local_upper
        if decision.selected_route is RouteSelection.LOCAL
        else fallback_upper
    )
    selected_upper_result = (
        local_upper_result
        if decision.selected_route is RouteSelection.LOCAL
        else fallback_upper_result
    )
    authorization = Phase3EDecisionAuthorizationV1(
        decision_result,
        selected_upper_result,
        charged_results,
    )

    threshold = FrozenThresholdProfileV1(
        context.query_id,
        prepared_local.pre_audit.regret_tolerance,
        prepared_local.pre_audit.risk_tolerance,
    )
    if threshold.threshold_profile_id != context.threshold_profile_id:
        raise Phase3EModelFailureConsumerV1Error(
            "verified model threshold identity changed during route preparation"
        )
    if decision.selected_route is RouteSelection.LOCAL:
        local_inputs = SafeChainLocalExecutorInputsV1(
            prepared_local,
            context,
            point,
            transaction,
            local_upper,
            local_cardinality,
            local_bound,
            local_cap,
            threshold,
            decision_result,
            local_upper_result,
            causal_result,
            local_cardinality_result,
            runtime_cardinality,
        )
        recipe = ExecutorRecipeV1(
            runtime_manifest.runtime_tree_id,
            RouteSelection.LOCAL,
            SAFE_CHAIN_LOCAL_EXECUTOR_SEMANTICS_ID,
            SAFE_CHAIN_LOCAL_RUNTIME_ENTRYPOINT,
            safe_chain_local_executor_configuration_id_v1(local_inputs),
        )
        constructor = SafeChainLocalPostFreezeConstructorV1(
            local_inputs, trusted_registry, trusted_profile
        )
    else:
        fallback_inputs = IsolatedGroundFallbackExecutorInputsV1(
            ground.world,
            context,
            point,
            fallback_upper,
            fallback_cardinality,
            fallback_bound,
            fallback_cap,
            decision_result,
            fallback_upper_result,
            fallback_cardinality_result,
            runtime_cardinality,
        )
        recipe = ExecutorRecipeV1(
            runtime_manifest.runtime_tree_id,
            RouteSelection.FALLBACK,
            ISOLATED_FALLBACK_EXECUTOR_SEMANTICS_ID,
            ISOLATED_FALLBACK_RUNTIME_ENTRYPOINT,
            isolated_ground_fallback_executor_configuration_id_v1(
                fallback_inputs
            ),
        )
        constructor = IsolatedFallbackPostFreezeConstructorV1(
            fallback_inputs, trusted_registry, trusted_profile
        )
    recipe.validate_runtime(runtime_manifest)
    selected_factory = SealedPostFreezeExecutorFactoryV1(
        recipe,
        runtime_cas,
        constructor,
        registry=trusted_registry,
        comparison_profile=trusted_profile,
    )
    reads = _preselection_reads_v1(
        context=context,
        point=point,
        reusable_rapm_id=ground.portable_rapm_id,
        failed_certificate_id=result.audit.audit_id,
        action_catalogue_id=ground.bound_ground_action_catalogue_id,
        selected_upper=selected_upper,
    )
    prepared = PreparedPhase3ERunV1(
        context,
        point,
        ground.portable_rapm_id,
        result.audit.audit_id,
        ground.bound_ground_action_catalogue_id,
        reads,
        prefix.aggregate_work,
        authorization,
        runtime_tree_id=runtime_manifest.runtime_tree_id,
        executor_recipe_id=recipe.executor_recipe_id,
        sealed_executor_profile=True,
        two_stage_accounting_profile=True,
        common_accounting_core=common_core,
        common_verification_charge_plan=common_plan,
    )
    authorities = ModelFailureRouteAuthoritiesV1(
        prepared_local,
        frontier,
        causal,
        transaction,
        local_source,
        local_bound,
        local_cardinality,
        local_formula,
        local_upper,
        causal_result,
        local_cardinality_result,
        local_upper_result,
        fallback_source,
        fallback_bound,
        fallback_cardinality,
        fallback_formula,
        fallback_upper,
        fallback_cardinality_result,
        fallback_upper_result,
        decision,
        decision_result,
    )
    public_identity = (
        (
            "failed_prefix_accounting_authority_id",
            prefix.failed_prefix_accounting_authority_id,
        ),
        ("ground_binding_id", ground.ground_binding_id),
        ("runtime_tree_id", runtime_manifest.runtime_tree_id),
        (
            "runtime_factory_cardinality_id",
            runtime_cardinality.runtime_factory_cardinality_id,
        ),
        ("route_decision_id", decision.route_decision_id),
        (
            "model_failure_preparation_accounting_id",
            route_preparation_accounting.model_failure_preparation_accounting_id,
        ),
        ("executor_recipe_id", recipe.executor_recipe_id),
    )
    wrapper = PreparedModelFailureConsumerV1(
        prefix,
        ground.ground_binding_id,
        runtime_manifest,
        runtime_cardinality,
        authorities,
        route_preparation_accounting,
        prepared,
        recipe,
        selected_factory,
        _PreparedConsumerMintV1(
            prefix,
            ground,
            runtime_manifest,
            runtime_cardinality,
            authorities,
            route_preparation_accounting,
            prepared,
            recipe,
            selected_factory,
            runtime_cas,
            public_identity,
            _PREPARED_CONSUMER_AUTHORITY,
        ),
    )
    wrapper = bind_runtime_authority_v1(
        wrapper,
        issuer=_PREPARED_CONSUMER_AUTHORITY,
    )
    wrapper.validate_before_run(
        registry=trusted_registry,
        comparison_profile=trusted_profile,
    )
    return wrapper


def run_prepared_model_failure_consumer_v1(
    prepared_consumer: PreparedModelFailureConsumerV1,
    *,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> Phase3ERunResultV1:
    """Execute exactly the selected sealed route after validating the bridge.

    The nonselected callback is a rejection-only trap, not a second factory or
    executor.  Reaching it is therefore both observable and fatal.  Success is
    still non-official because ``prepared_consumer.accounting_blockers`` remain
    attached to the preparation boundary.
    """

    if type(prepared_consumer) is not PreparedModelFailureConsumerV1:
        raise Phase3EModelFailureConsumerV1Error(
            "run requires a retained PreparedModelFailureConsumerV1"
        )
    trusted_registry, trusted_profile = _official_profiles_v1(
        registry, comparison_profile
    )
    prepared_consumer.validate_before_run(
        registry=trusted_registry,
        comparison_profile=trusted_profile,
    )

    def reject_unselected_route(*_args: object, **_kwargs: object) -> object:
        raise Phase3EModelFailureConsumerV1Error(
            "runner accessed the nonselected model-failure route"
        )

    if prepared_consumer.selected_route is RouteSelection.LOCAL:
        local_executor = prepared_consumer.selected_factory
        fallback_executor = reject_unselected_route
    else:
        local_executor = reject_unselected_route
        fallback_executor = prepared_consumer.selected_factory
    result = run_phase3e(
        prepared_consumer.prepared,
        local_executor=local_executor,
        fallback_executor=fallback_executor,
        registry=trusted_registry,
        comparison_profile=trusted_profile,
    )
    if (
        result.selected_route is not prepared_consumer.selected_route
        or result.decision != prepared_consumer.route_authorities.decision
        or result.common_prefix_work
        is not prepared_consumer.failed_prefix_authority.aggregate_work
        or result.runtime_tree_id
        != prepared_consumer.runtime_manifest.runtime_tree_id
        or result.executor_recipe_id
        != prepared_consumer.selected_recipe.executor_recipe_id
        or result.sealed_executor_profile is not True
        or result.two_stage_accounting_profile is not True
        or result.common_two_stage_accounting is None
        or result.selected_two_stage_accounting is None
    ):
        raise Phase3EModelFailureConsumerV1Error(
            "selected-route result differs from the prepared model-failure chain"
        )
    return result


__all__ = [
    "MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS",
    "MODEL_FAILURE_CONSUMER_STATUS",
    "ModelFailureRouteAuthoritiesV1",
    "ModelOnlyFailedPrefixAccountingAuthorityV1",
    "ModelOnlyFailedPrefixChargePreparationV1",
    "Phase3EModelFailureConsumerV1Error",
    "PreparedModelFailureConsumerV1",
    "freeze_model_only_failed_prefix_charge_v1",
    "mint_model_only_failed_prefix_accounting_authority_v1",
    "official_safe_chain_fallback_cap_profile_v1",
    "prepare_phase3e_from_model_failure_v1",
    "require_model_only_failed_prefix_accounting_authority_v1",
    "run_prepared_model_failure_consumer_v1",
    "verify_and_mint_model_only_failed_prefix_accounting_authority_v1",
]
