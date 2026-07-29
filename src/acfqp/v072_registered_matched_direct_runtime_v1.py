"""Registered matched-direct H=2 occurrence runtime for V0-072.

The production entry point accepts only an exact campaign authority chain, its
identical remote-main anchor, one anchor-bound matched-direct occurrence plan,
and one registered public context.  It accepts no transcript, law,
probability, outcome, status, count, terminal, policy, planner result, resource
limit, or callback from a caller.

One internally minted persistent accumulator acquires the complete ground row
inventory.  At each frozen checkpoint the runtime appends only the new suffix,
independently replays the resulting inventory/model, runs the exact lazy
GROUND_DIRECT solver, and independently verifies every solved proof.  It stops
at the first sound certificate, at typed exact-search exhaustion, or after the
registered maximum checkpoint.  Acquisition and independent replay remain
separate work lanes.

The route-runtime result and its independent verifier are implemented here.
Conversion into the private evaluator terminal adapter intentionally remains a
separate, explicit blocker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import exact_lazy_h2_independent_verifier_v1 as lazy_independent
from acfqp import exact_lazy_h2_robust_planner_v1 as lazy
from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_v1 as cold
from acfqp import v072_cold_h2_model_builders_v1 as cold_builder
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_independent_exact_ground_evaluator_v1 as evaluator
from acfqp import v072_registered_campaign_consumer_v1 as consumer


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_matched_direct_occurrence_runtime_v1"
ARM = "MATCHED_DIRECT_GROUND"
CHECKPOINTS = prereg.DIRECT_VALIDATION_CHECKPOINTS
DISCOVERY_DRAWS_PER_ROW = (
    prereg.INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
)
DIRECT_CHECKPOINT_CAP_TERMINAL_CODE = (
    prereg.DIRECT_CHECKPOINT_CAP_TERMINAL_CODE
)
DIRECT_CHECKPOINT_CAP_PREREG_AMENDMENT_BLOCKER = (
    "DIRECT_CHECKPOINT_CAP_EXHAUSTED_TERMINAL_CODE_NOT_IN_PREREGISTRATION"
)
DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED = (
    DIRECT_CHECKPOINT_CAP_TERMINAL_CODE in prereg.TERMINAL_CODES
)
REGISTERED_RUNTIME_ENABLED = DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED
REGISTERED_RUNTIME_STATUS = (
    "IMPLEMENTED_VERIFIED_RESULT_TERMINAL_ADAPTER_BLOCKED"
    if DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED
    else "IMPLEMENTED_PREREG_TERMINAL_CODE_AMENDMENT_BLOCKED"
)

TERMINAL_ADAPTER_DEPENDENCY_BLOCKER = (
    "REGISTERED_MATCHED_DIRECT_VERIFIED_RUNTIME_RESULT_ADAPTER_NOT_INTEGRATED"
)
EVALUATOR_TERMINAL_MINT_DEPENDENCY_BLOCKER = (
    TERMINAL_ADAPTER_DEPENDENCY_BLOCKER
)
_RUNTIME_BLOCKERS = (
    (TERMINAL_ADAPTER_DEPENDENCY_BLOCKER,)
    if DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED
    else (
        DIRECT_CHECKPOINT_CAP_PREREG_AMENDMENT_BLOCKER,
        TERMINAL_ADAPTER_DEPENDENCY_BLOCKER,
    )
)
REGISTERED_EXACT_LAZY_RESOURCE_LIMITS = (
    lazy.ExactLazyH2ResourceLimitsV1()
)


class V072RegisteredMatchedDirectRuntimeInvariantViolation(ValueError):
    """An anchor, occurrence, prefix, schedule, or accounting invariant failed."""


class RegisteredMatchedDirectRuntimeLockedV1(RuntimeError):
    """Production target access is unavailable or unauthorized."""

    def __init__(
        self,
        message: str,
        *,
        access_audit: "RegisteredMatchedDirectAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.access_audit = access_audit


class RegisteredMatchedDirectDependencyBlockedV1(RuntimeError):
    """An exact post-anchor production dependency has no authority yet."""

    def __init__(
        self,
        message: str,
        *,
        occurrence_plan: "RegisteredMatchedDirectOccurrencePlanV1",
        dependency_protocol: (
            "RegisteredMatchedDirectDependencyProtocolV1"
        ),
        access_audit: "RegisteredMatchedDirectAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.occurrence_plan = occurrence_plan
        self.dependency_protocol = dependency_protocol
        self.access_audit = access_audit


DOMAIN_TAGS = {
    "access": "acfqp:v072-registered-matched-direct-access-audit:v1",
    "dependency": (
        "acfqp:v072-registered-matched-direct-dependency-protocol:v1"
    ),
    "occurrence": (
        "acfqp:v072-registered-matched-direct-occurrence-plan:v1"
    ),
    "synthetic_prefix": (
        "acfqp:v072-registration-disjoint-direct-prefix:v1"
    ),
    "synthetic_checkpoint": (
        "acfqp:v072-registration-disjoint-direct-checkpoint:v1"
    ),
    "synthetic_work": (
        "acfqp:v072-registration-disjoint-direct-checkpoint-work:v1"
    ),
    "synthetic_record": (
        "acfqp:v072-registration-disjoint-direct-checkpoint-record:v1"
    ),
    "synthetic_run": (
        "acfqp:v072-registration-disjoint-direct-schedule-run:v1"
    ),
    "decision": (
        "acfqp:v072-registered-matched-direct-ground-decision:v1"
    ),
    "policy": (
        "acfqp:v072-registered-matched-direct-deterministic-policy:v1"
    ),
    "checkpoint_record": (
        "acfqp:v072-registered-matched-direct-runtime-checkpoint-record:v1"
    ),
    "occurrence_result": (
        "acfqp:v072-registered-matched-direct-occurrence-result:v1"
    ),
    "occurrence_verification": (
        "acfqp:v072-registered-matched-direct-occurrence-verification:v1"
    ),
    "terminal_bundle": (
        "acfqp:v072-registered-matched-direct-evaluator-terminal-bundle:v1"
    ),
}


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectAccessAuditV1:
    anchor_checks: int = 0
    occurrence_identity_checks: int = 0
    authority_chain_verifications: int = 0
    inventory_accumulator_open_calls: int = 0
    inventory_checkpoint_acquisition_calls: int = 0
    inventory_checkpoint_verification_calls: int = 0
    observer_inventory_calls: int = 0
    acquisition_stream_opens: int = 0
    acquisition_draw_calls: int = 0
    independent_replay_stream_opens: int = 0
    independent_replay_draw_calls: int = 0
    observer_stream_opens: int = 0
    observer_draw_calls: int = 0
    accepted_observations: int = 0
    confidence_accumulator_calls: int = 0
    direct_model_build_calls: int = 0
    direct_model_verification_calls: int = 0
    ground_planner_calls: int = 0
    proof_verification_calls: int = 0
    evaluator_terminal_mint_calls: int = 0

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0
            for value in (
                getattr(self, name)
                for name in self.__dataclass_fields__
            )
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "registered matched-direct access counters are malformed"
            )
        if (
            self.observer_stream_opens
            != (
                self.acquisition_stream_opens
                + self.independent_replay_stream_opens
            )
            or self.observer_draw_calls
            != (
                self.acquisition_draw_calls
                + self.independent_replay_draw_calls
            )
            or self.accepted_observations != self.acquisition_draw_calls
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "online acquisition and independent replay access were mixed"
            )

    @property
    def observer_or_target_access_started(self) -> bool:
        return any(
            (
                self.observer_inventory_calls,
                self.inventory_accumulator_open_calls,
                self.inventory_checkpoint_acquisition_calls,
                self.inventory_checkpoint_verification_calls,
                self.observer_stream_opens,
                self.observer_draw_calls,
                self.acquisition_stream_opens,
                self.acquisition_draw_calls,
                self.independent_replay_stream_opens,
                self.independent_replay_draw_calls,
                self.accepted_observations,
                self.confidence_accumulator_calls,
                self.direct_model_build_calls,
                self.direct_model_verification_calls,
                self.ground_planner_calls,
                self.proof_verification_calls,
                self.evaluator_terminal_mint_calls,
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_access_audit.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
            "online_sample_evidence_draws": self.acquisition_draw_calls,
            "independent_replay_draws_enter_online_sample_evidence": False,
            "observer_or_target_access_started": (
                self.observer_or_target_access_started
            ),
        }

    @property
    def audit_id(self) -> str:
        return _content_id("access", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


ZERO_ACCESS_AUDIT = RegisteredMatchedDirectAccessAuditV1()


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectDependencyProtocolV1:
    """Exact runtime/terminal boundary; never an injected implementation."""

    target_accumulator_module: str = (
        "acfqp.v072_registered_matched_direct_complete_inventory_v1"
    )
    target_accumulator_type: str = (
        "RegisteredMatchedDirectCompleteInventoryAccumulatorV1"
    )
    target_accumulator_entrypoint: str = (
        "open_registered_matched_direct_complete_inventory_accumulator_v1"
    )
    direct_inventory_type: str = (
        "RegisteredMatchedDirectCompleteInventoryCheckpointV1"
    )
    direct_inventory_entrypoint: str = (
        "acquire_registered_matched_direct_complete_inventory_checkpoint_v1"
    )
    direct_inventory_verifier: str = (
        "verify_registered_matched_direct_complete_inventory_checkpoint_v1"
    )
    confidence_projection_entrypoint: str = (
        "acfqp.v072_registered_matched_direct_complete_inventory_v1."
        "acquire_registered_matched_direct_complete_inventory_checkpoint_v1"
    )
    cold_direct_builder_entrypoint: str = (
        "acfqp.v072_registered_matched_direct_complete_inventory_v1."
        "build_registered_matched_direct_cold_snapshot_v1"
    )
    cold_direct_independent_verifier_entrypoint: str = (
        "acfqp.v072_registered_matched_direct_complete_inventory_v1."
        "verify_registered_matched_direct_cold_snapshot_independently_v1"
    )
    ground_planner_entrypoint: str = (
        "acfqp.exact_lazy_h2_robust_planner_v1."
        "solve_exact_lazy_ground_direct_h2_v1"
    )
    proof_verifier_entrypoint: str = (
        "acfqp.exact_lazy_h2_independent_verifier_v1."
        "verify_exact_lazy_h2_solve_result_v1"
    )
    evaluator_terminal_factory_entrypoint: str = (
        "acfqp.v072_registered_operational_terminal_authority_v1."
        "derive_registered_operational_terminal_authority_v1"
    )
    blockers: tuple[str, ...] = _RUNTIME_BLOCKERS
    dependency_available: bool = (
        DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED
    )
    terminal_adapter_available: bool = False

    def __post_init__(self) -> None:
        if (
            self.target_accumulator_module
            != (
                "acfqp.v072_registered_matched_direct_complete_"
                "inventory_v1"
            )
            or self.target_accumulator_type
            != "RegisteredMatchedDirectCompleteInventoryAccumulatorV1"
            or self.target_accumulator_entrypoint
            != (
                "open_registered_matched_direct_complete_inventory_"
                "accumulator_v1"
            )
            or self.direct_inventory_type
            != "RegisteredMatchedDirectCompleteInventoryCheckpointV1"
            or self.direct_inventory_entrypoint
            != (
                "acquire_registered_matched_direct_complete_"
                "inventory_checkpoint_v1"
            )
            or self.direct_inventory_verifier
            != (
                "verify_registered_matched_direct_complete_"
                "inventory_checkpoint_v1"
            )
            or self.confidence_projection_entrypoint
            != (
                "acfqp.v072_registered_matched_direct_complete_inventory_v1."
                "acquire_registered_matched_direct_complete_inventory_"
                "checkpoint_v1"
            )
            or self.cold_direct_builder_entrypoint
            != (
                "acfqp.v072_registered_matched_direct_complete_inventory_v1."
                "build_registered_matched_direct_cold_snapshot_v1"
            )
            or self.cold_direct_independent_verifier_entrypoint
            != (
                "acfqp.v072_registered_matched_direct_complete_inventory_v1."
                "verify_registered_matched_direct_cold_snapshot_"
                "independently_v1"
            )
            or self.ground_planner_entrypoint
            != (
                "acfqp.exact_lazy_h2_robust_planner_v1."
                "solve_exact_lazy_ground_direct_h2_v1"
            )
            or self.proof_verifier_entrypoint
            != (
                "acfqp.exact_lazy_h2_independent_verifier_v1."
                "verify_exact_lazy_h2_solve_result_v1"
            )
            or self.evaluator_terminal_factory_entrypoint
            != (
                "acfqp.v072_registered_operational_terminal_authority_v1."
                "derive_registered_operational_terminal_authority_v1"
            )
            or self.blockers != _RUNTIME_BLOCKERS
            or self.dependency_available
            is not DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED
            or self.terminal_adapter_available is not False
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "registered matched-direct dependency protocol changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_dependency_protocol.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "target_accumulator_module": self.target_accumulator_module,
            "target_accumulator_type": (
                self.target_accumulator_type
            ),
            "target_accumulator_entrypoint": (
                self.target_accumulator_entrypoint
            ),
            "direct_inventory_type": self.direct_inventory_type,
            "direct_inventory_entrypoint": self.direct_inventory_entrypoint,
            "direct_inventory_verifier": self.direct_inventory_verifier,
            "confidence_projection_entrypoint": (
                self.confidence_projection_entrypoint
            ),
            "cold_direct_builder_entrypoint": (
                self.cold_direct_builder_entrypoint
            ),
            "cold_direct_independent_verifier_entrypoint": (
                self.cold_direct_independent_verifier_entrypoint
            ),
            "ground_planner_entrypoint": self.ground_planner_entrypoint,
            "proof_verifier_entrypoint": self.proof_verifier_entrypoint,
            "evaluator_terminal_factory_entrypoint": (
                self.evaluator_terminal_factory_entrypoint
            ),
            "blockers": list(self.blockers),
            "dependency_available": self.dependency_available,
            "terminal_adapter_available": False,
            "direct_checkpoint_cap_terminal_code": (
                DIRECT_CHECKPOINT_CAP_TERMINAL_CODE
            ),
            "direct_checkpoint_cap_terminal_registered": (
                DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED
            ),
            "injected_callback_allowed": False,
            "caller_transcript_allowed": False,
            "caller_law_or_probabilities_allowed": False,
            "caller_status_policy_or_count_allowed": False,
            "caller_resource_limits_allowed": False,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("dependency", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


def inspect_registered_matched_direct_dependency_protocol_v1(
) -> RegisteredMatchedDirectDependencyProtocolV1:
    return RegisteredMatchedDirectDependencyProtocolV1()


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectOccurrencePlanV1:
    """Anchor-bound direct arm identity within the fixed 15 occurrences."""

    anchor_id: str
    context_id: str
    context_key: str
    context_ordinal: int
    arm_ordinal: int
    occurrence_ordinal: int
    arm: str = ARM
    maximum_checkpoint: int = CHECKPOINTS[-1]
    replacement_allowed: bool = False
    early_skip_allowed: bool = False
    _plan_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.anchor_id, "matched-direct occurrence anchor")
        _cid(self.context_id, "matched-direct occurrence context")
        contexts = prereg.registered_heldout_public_contexts_v2()
        expected_arm_ordinal = prereg.ARM_ORDER.index(ARM)
        if (
            type(self.context_ordinal) is not int
            or self.context_ordinal not in range(len(contexts))
            or contexts[self.context_ordinal].context_id != self.context_id
            or contexts[self.context_ordinal].context_key != self.context_key
            or self.arm != ARM
            or self.arm_ordinal != expected_arm_ordinal
            or self.occurrence_ordinal
            != (
                self.context_ordinal * len(prereg.ARM_ORDER)
                + expected_arm_ordinal
            )
            or self.maximum_checkpoint != CHECKPOINTS[-1]
            or self.replacement_allowed is not False
            or self.early_skip_allowed is not False
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "matched-direct occurrence is outside the fixed "
                "context-major 3 x 5 schedule"
            )
        object.__setattr__(
            self,
            "_plan_id",
            _content_id("occurrence", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_occurrence_plan.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "anchor_id": self.anchor_id,
            "confirmatory_family_generation": (
                prereg.CONFIRMATORY_FAMILY_GENERATION
            ),
            "context_id": self.context_id,
            "context_key": self.context_key,
            "context_ordinal": self.context_ordinal,
            "arm": ARM,
            "arm_ordinal": self.arm_ordinal,
            "occurrence_ordinal": self.occurrence_ordinal,
            "checkpoint_order": list(CHECKPOINTS),
            "discovery_draws_per_row": DISCOVERY_DRAWS_PER_ROW,
            "maximum_checkpoint": self.maximum_checkpoint,
            "replacement_allowed": False,
            "early_skip_allowed": False,
            "crn_draw_discount": 0,
        }

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "plan_id": self.plan_id}


def registered_matched_direct_occurrence_plan_v1(
    *,
    anchor: final_authority.V072RemoteMainAnchorV1,
    context: prereg.HeldoutPublicGraphContextV2,
) -> RegisteredMatchedDirectOccurrencePlanV1:
    canonical_anchor = _require_anchor_without_observer_access(anchor)
    canonical_context = _require_context_without_observer_access(context)
    contexts = prereg.registered_heldout_public_contexts_v2()
    context_ordinal = contexts.index(canonical_context)
    arm_ordinal = prereg.ARM_ORDER.index(ARM)
    return RegisteredMatchedDirectOccurrencePlanV1(
        canonical_anchor.anchor_id,
        canonical_context.context_id,
        canonical_context.context_key,
        context_ordinal,
        arm_ordinal,
        context_ordinal * len(prereg.ARM_ORDER) + arm_ordinal,
    )


class RegistrationDisjointDirectCheckpointStatusV1(str, Enum):
    CERTIFIED = "CERTIFIED"
    NOT_CERTIFIED = "NOT_CERTIFIED"
    SOLVER_RESOURCE_EXHAUSTED = "SOLVER_RESOURCE_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class RegistrationDisjointDirectRowPrefixV1:
    row_key: str
    checkpoint: int
    previous_prefix_id: str | None
    cumulative_accepted_draws: int
    _prefix_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.previous_prefix_id is not None:
            _cid(self.previous_prefix_id, "synthetic direct parent prefix")
        if (
            type(self.row_key) is not str
            or not self.row_key.startswith("SYNTHETIC_DISJOINT_ROW_")
            or self.checkpoint not in CHECKPOINTS
            or type(self.cumulative_accepted_draws) is not int
            or self.cumulative_accepted_draws
            != DISCOVERY_DRAWS_PER_ROW + self.checkpoint
            or (
                self.checkpoint == CHECKPOINTS[0]
                and self.previous_prefix_id is not None
            )
            or (
                self.checkpoint != CHECKPOINTS[0]
                and self.previous_prefix_id is None
            )
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "registration-disjoint row prefix is malformed"
            )
        object.__setattr__(
            self,
            "_prefix_id",
            _content_id("synthetic_prefix", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_direct_row_prefix.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "row_key": self.row_key,
            "checkpoint": self.checkpoint,
            "previous_prefix_id": self.previous_prefix_id,
            "cumulative_accepted_draws": self.cumulative_accepted_draws,
            "registered_target_evidence": False,
        }

    @property
    def prefix_id(self) -> str:
        return self._prefix_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prefix_id": self.prefix_id}


@dataclass(frozen=True, slots=True)
class RegistrationDisjointDirectCheckpointV1:
    checkpoint: int
    row_prefixes: tuple[RegistrationDisjointDirectRowPrefixV1, ...]
    status: RegistrationDisjointDirectCheckpointStatusV1
    _checkpoint_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.checkpoint not in CHECKPOINTS
            or type(self.row_prefixes) is not tuple
            or not self.row_prefixes
            or any(
                type(item) is not RegistrationDisjointDirectRowPrefixV1
                or item.checkpoint != self.checkpoint
                for item in self.row_prefixes
            )
            or tuple(item.row_key for item in self.row_prefixes)
            != tuple(sorted({item.row_key for item in self.row_prefixes}))
            or type(self.status)
            is not RegistrationDisjointDirectCheckpointStatusV1
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "registration-disjoint checkpoint is partial or malformed"
            )
        object.__setattr__(
            self,
            "_checkpoint_id",
            _content_id("synthetic_checkpoint", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_direct_checkpoint.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "checkpoint": self.checkpoint,
            "row_prefix_ids": [
                item.prefix_id for item in self.row_prefixes
            ],
            "status": self.status.value,
            "registered_target_evidence": False,
        }

    @property
    def checkpoint_id(self) -> str:
        return self._checkpoint_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_prefixes": [
                item.to_document() for item in self.row_prefixes
            ],
            "checkpoint_id": self.checkpoint_id,
        }


@dataclass(frozen=True, slots=True)
class RegistrationDisjointDirectCheckpointWorkV1:
    checkpoint: int
    row_count: int
    discovery_new_draws: int
    validation_new_draws: int
    accepted_new_draws: int
    cumulative_accepted_draws: int
    complete_row_prefix_replays: int
    direct_model_builds: int = 1
    direct_model_independent_verifications: int = 1
    exact_lazy_ground_planner_calls: int = 1
    independent_lazy_proof_verifications: int = 1
    source_prior_reads: int = 0
    quotient_model_builds: int = 0
    quotient_planner_calls: int = 0
    local_recovery_calls: int = 0
    crn_draw_discount: int = 0
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        previous = (
            0
            if self.checkpoint == CHECKPOINTS[0]
            else CHECKPOINTS[CHECKPOINTS.index(self.checkpoint) - 1]
        )
        expected_discovery = (
            self.row_count * DISCOVERY_DRAWS_PER_ROW
            if self.checkpoint == CHECKPOINTS[0]
            else 0
        )
        expected_validation = self.row_count * (self.checkpoint - previous)
        if (
            self.checkpoint not in CHECKPOINTS
            or type(self.row_count) is not int
            or self.row_count <= 0
            or any(
                type(value) is not int or value < 0
                for value in (
                    getattr(self, name)
                    for name in self.__dataclass_fields__
                    if name != "_work_id"
                )
            )
            or self.discovery_new_draws != expected_discovery
            or self.validation_new_draws != expected_validation
            or self.accepted_new_draws
            != expected_discovery + expected_validation
            or self.cumulative_accepted_draws
            != self.row_count
            * (DISCOVERY_DRAWS_PER_ROW + self.checkpoint)
            or self.complete_row_prefix_replays != self.row_count
            or any(
                value != 1
                for value in (
                    self.direct_model_builds,
                    self.direct_model_independent_verifications,
                    self.exact_lazy_ground_planner_calls,
                    self.independent_lazy_proof_verifications,
                )
            )
            or any(
                value != 0
                for value in (
                    self.source_prior_reads,
                    self.quotient_model_builds,
                    self.quotient_planner_calls,
                    self.local_recovery_calls,
                    self.crn_draw_discount,
                )
            )
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "registration-disjoint direct work is undercounted"
            )
        object.__setattr__(
            self,
            "_work_id",
            _content_id("synthetic_work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_direct_checkpoint_work.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
                if name != "_work_id"
            },
            "registered_target_evidence": False,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class RegistrationDisjointDirectCheckpointRecordV1:
    checkpoint: RegistrationDisjointDirectCheckpointV1
    work: RegistrationDisjointDirectCheckpointWorkV1
    _record_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.checkpoint)
            is not RegistrationDisjointDirectCheckpointV1
            or type(self.work)
            is not RegistrationDisjointDirectCheckpointWorkV1
            or self.work.checkpoint != self.checkpoint.checkpoint
            or self.work.row_count != len(self.checkpoint.row_prefixes)
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "registration-disjoint checkpoint/work binding is stale"
            )
        object.__setattr__(
            self,
            "_record_id",
            _content_id(
                "synthetic_record",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_direct_"
                        "checkpoint_record.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "checkpoint_id": self.checkpoint.checkpoint_id,
                    "work_id": self.work.work_id,
                },
            ),
        )

    @property
    def record_id(self) -> str:
        return self._record_id

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_direct_"
                "checkpoint_record.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "checkpoint": self.checkpoint.to_document(),
            "work": self.work.to_document(),
            "record_id": self.record_id,
        }


@dataclass(frozen=True, slots=True)
class RegistrationDisjointDirectScheduleRunV1:
    records: tuple[RegistrationDisjointDirectCheckpointRecordV1, ...]
    terminal_status: RegistrationDisjointDirectCheckpointStatusV1
    stopped_checkpoint: int
    total_accepted_draws: int
    row_count: int
    source_prior_reads: int = 0
    quotient_planner_calls: int = 0
    local_recovery_calls: int = 0
    crn_draw_discount: int = 0
    _run_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        statuses = tuple(item.checkpoint.status for item in self.records)
        checkpoints = tuple(
            item.checkpoint.checkpoint for item in self.records
        )
        terminal_positions = tuple(
            index
            for index, status in enumerate(statuses)
            if status
            is not RegistrationDisjointDirectCheckpointStatusV1.NOT_CERTIFIED
        )
        if (
            type(self.records) is not tuple
            or not self.records
            or any(
                type(item)
                is not RegistrationDisjointDirectCheckpointRecordV1
                for item in self.records
            )
            or checkpoints != CHECKPOINTS[: len(checkpoints)]
            or terminal_positions not in ((), (len(self.records) - 1,))
            or (
                not terminal_positions
                and checkpoints[-1] != CHECKPOINTS[-1]
            )
            or self.terminal_status is not statuses[-1]
            or self.stopped_checkpoint != checkpoints[-1]
            or self.row_count
            != len(self.records[0].checkpoint.row_prefixes)
            or self.total_accepted_draws
            != self.row_count
            * (DISCOVERY_DRAWS_PER_ROW + self.stopped_checkpoint)
            or any(
                value != 0
                for value in (
                    self.source_prior_reads,
                    self.quotient_planner_calls,
                    self.local_recovery_calls,
                    self.crn_draw_discount,
                )
            )
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "registration-disjoint direct run stopped early, skipped, "
                "or undercounted"
            )
        expected_rows = tuple(
            item.row_key
            for item in self.records[0].checkpoint.row_prefixes
        )
        previous_by_row: dict[
            str,
            RegistrationDisjointDirectRowPrefixV1,
        ] = {}
        for record in self.records:
            prefixes = record.checkpoint.row_prefixes
            if tuple(item.row_key for item in prefixes) != expected_rows:
                raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                    "direct checkpoint replaced or omitted a row"
                )
            for prefix in prefixes:
                previous = previous_by_row.get(prefix.row_key)
                if (
                    (previous is None and prefix.previous_prefix_id is not None)
                    or (
                        previous is not None
                        and prefix.previous_prefix_id != previous.prefix_id
                    )
                ):
                    raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                        "direct row transcript is not one append-only prefix"
                    )
                previous_by_row[prefix.row_key] = prefix
        object.__setattr__(
            self,
            "_run_id",
            _content_id("synthetic_run", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_direct_schedule_run.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "record_ids": [item.record_id for item in self.records],
            "terminal_status": self.terminal_status.value,
            "stopped_checkpoint": self.stopped_checkpoint,
            "total_accepted_draws": self.total_accepted_draws,
            "row_count": self.row_count,
            "source_prior_reads": 0,
            "quotient_planner_calls": 0,
            "local_recovery_calls": 0,
            "crn_draw_discount": 0,
            "registered_target_evidence": False,
        }

    @property
    def run_id(self) -> str:
        return self._run_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "records": [item.to_document() for item in self.records],
            "run_id": self.run_id,
        }


def run_registration_disjoint_direct_schedule_core_v1(
    *,
    checkpoints: tuple[RegistrationDisjointDirectCheckpointV1, ...],
) -> RegistrationDisjointDirectScheduleRunV1:
    """Validate full synchronous prefixes and derive all work/stopping fields."""

    if (
        type(checkpoints) is not tuple
        or not checkpoints
        or any(
            type(item) is not RegistrationDisjointDirectCheckpointV1
            for item in checkpoints
        )
    ):
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "registration-disjoint core requires exact checkpoint types"
        )
    records = []
    for index, checkpoint in enumerate(checkpoints):
        previous = 0 if index == 0 else checkpoints[index - 1].checkpoint
        row_count = len(checkpoint.row_prefixes)
        discovery = (
            row_count * DISCOVERY_DRAWS_PER_ROW if index == 0 else 0
        )
        validation = row_count * (checkpoint.checkpoint - previous)
        work = RegistrationDisjointDirectCheckpointWorkV1(
            checkpoint.checkpoint,
            row_count,
            discovery,
            validation,
            discovery + validation,
            row_count
            * (DISCOVERY_DRAWS_PER_ROW + checkpoint.checkpoint),
            row_count,
        )
        records.append(
            RegistrationDisjointDirectCheckpointRecordV1(
                checkpoint,
                work,
            )
        )
    final = checkpoints[-1]
    return RegistrationDisjointDirectScheduleRunV1(
        tuple(records),
        final.status,
        final.checkpoint,
        len(final.row_prefixes)
        * (DISCOVERY_DRAWS_PER_ROW + final.checkpoint),
        len(final.row_prefixes),
    )


class RegisteredMatchedDirectCheckpointStatusV1(str, Enum):
    CERTIFIED = "CERTIFIED"
    NOT_CERTIFIED = "NOT_CERTIFIED"
    SOLVER_RESOURCE_EXHAUSTED = "SOLVER_RESOURCE_EXHAUSTED"


class RegisteredMatchedDirectTerminalClassV1(str, Enum):
    PLAN_CERTIFICATE = "PLAN_CERTIFICATE"
    ATTEMPT_CLOSURE_NONCERTIFICATE = "ATTEMPT_CLOSURE_NONCERTIFICATE"


class RegisteredMatchedDirectTerminalCodeV1(str, Enum):
    CONDITIONAL_PLAN_CERTIFICATE = "CONDITIONAL_PLAN_CERTIFICATE"
    DIRECT_CHECKPOINT_CAP_EXHAUSTED_NONCERTIFICATE = (
        DIRECT_CHECKPOINT_CAP_TERMINAL_CODE
    )
    EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE = (
        "EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE"
    )


def _counter_document(
    value: lazy.ExactLazyH2SearchCountersV1,
) -> dict[str, int]:
    if type(value) is not lazy.ExactLazyH2SearchCountersV1:
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "exact lazy counter record is malformed"
        )
    return {
        "branch_nodes": value.branch_nodes,
        "complete_policies": value.complete_policies,
        "root_bound_evaluations": value.root_bound_evaluations,
        "pruned_branches": value.pruned_branches,
        "root_actions_considered": value.root_actions_considered,
        "relevant_decision_units": value.relevant_decision_units,
        "irrelevant_decision_units": value.irrelevant_decision_units,
    }


def _solve_result_document(
    value: lazy.ExactLazyH2SolveResultV1,
) -> dict[str, Any]:
    if type(value) is not lazy.ExactLazyH2SolveResultV1:
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "exact lazy solve result is malformed"
        )
    if value.status is lazy.ExactLazyH2SolveStatus.SOLVED:
        if (
            type(value.audit) is not robust.RobustPlanAuditV1
            or type(value.trace) is not lazy.ExactLazyH2SearchTraceV1
            or value.exhaustion is not None
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "solved direct result lacks its exact audit/proof"
            )
        return {
            "status": value.status.value,
            "solver_kind": value.solver_kind.value,
            "audit_id": value.audit.audit_id,
            "original_proof_id": value.trace.original_proof.proof_id,
            "zero_other_proof_id": (
                None
                if value.trace.zero_other_counterfactual_proof is None
                else (
                    value.trace.zero_other_counterfactual_proof.proof_id
                )
            ),
            "original_counters": _counter_document(
                value.trace.original
            ),
            "zero_other_counters": (
                None
                if value.trace.zero_other_counterfactual is None
                else _counter_document(
                    value.trace.zero_other_counterfactual
                )
            ),
        }
    exhaustion = value.exhaustion
    if (
        value.status
        is not lazy.ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED
        or type(exhaustion) is not lazy.ExactLazyH2ResourceExhaustionV1
        or value.audit is not None
        or value.trace is not None
    ):
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "direct resource closure lacks typed exact exhaustion"
        )
    return {
        "status": value.status.value,
        "solver_kind": value.solver_kind.value,
        "exhaustion": {
            "phase": exhaustion.phase.value,
            "code": exhaustion.code.value,
            "observed": exhaustion.observed,
            "limit": exhaustion.limit,
            "counters": _counter_document(exhaustion.counters),
            "terminal_code": exhaustion.terminal_code,
            "approximate_audit_emitted": False,
        },
    }


def _action_triple(value: Any, field_name: str) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
    ):
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            f"{field_name} must be one exact integer action triple"
        )
    return value


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectGroundDecisionV1:
    occurrence_plan_id: str
    context_id: str
    state_semantic_id: str
    state_record_id: str
    ground_state_id: str
    state_ranks: tuple[int, ...]
    remaining_horizon: int
    selected_action_semantic_id: str
    selected_action_record_id: str
    selected_ground_action_id: str
    action: tuple[int, int, int]
    deterministic: bool = True
    _decision_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_plan_id, "decision occurrence"),
            (self.context_id, "decision context"),
            (self.state_semantic_id, "decision semantic state"),
            (self.state_record_id, "decision state record"),
            (self.ground_state_id, "decision ground state"),
            (
                self.selected_action_semantic_id,
                "decision semantic action",
            ),
            (
                self.selected_action_record_id,
                "decision action record",
            ),
            (
                self.selected_ground_action_id,
                "decision ground action",
            ),
        ):
            _cid(value, label)
        _action_triple(self.action, "direct deterministic decision")
        registered_context = next(
            (
                item
                for item in prereg.registered_heldout_public_contexts_v2()
                if item.context_id == self.context_id
            ),
            None,
        )
        replayed_state = (
            observer.HeldoutSymbolicGraphStateV2(self.state_ranks)
            if (
                type(self.state_ranks) is tuple
                and len(self.state_ranks) == 7
                and all(
                    type(rank) is int
                    and 0 <= rank <= prereg.RANK_CAP
                    for rank in self.state_ranks
                )
            )
            else None
        )
        replayed_catalogue = (
            observer.legal_action_catalogue_v2(
                registered_context,
                replayed_state,
                self.remaining_horizon,
            )
            if (
                type(registered_context)
                is prereg.HeldoutPublicGraphContextV2
                and type(replayed_state)
                is observer.HeldoutSymbolicGraphStateV2
                and type(self.remaining_horizon) is int
                and self.remaining_horizon in (1, prereg.HORIZON)
            )
            else None
        )
        replayed_row_binding = (
            observer.observation_row_binding_v2(
                registered_context,
                replayed_catalogue,
                self.action,
            )
            if (
                type(replayed_catalogue)
                is observer.HeldoutLegalActionCatalogueV2
                and self.action in replayed_catalogue.actions
            )
            else None
        )
        if (
            type(self.state_ranks) is not tuple
            or len(self.state_ranks) != 7
            or any(
                type(rank) is not int or not 0 <= rank <= prereg.RANK_CAP
                for rank in self.state_ranks
            )
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, prereg.HORIZON)
            or type(replayed_state)
            is not observer.HeldoutSymbolicGraphStateV2
            or replayed_state.state_id != self.state_semantic_id
            or type(replayed_row_binding)
            is not observer.HeldoutObservationRowBindingV2
            or replayed_row_binding.row_binding_id
            != self.selected_action_semantic_id
            or self.deterministic is not True
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "direct deterministic ground decision is malformed"
            )
        object.__setattr__(
            self,
            "_decision_id",
            _content_id("decision", self._payload()),
        )

    @property
    def semantic_key(
        self,
    ) -> tuple[tuple[int, ...], tuple[int, int, int]]:
        return self.state_ranks, self.action

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_ground_decision.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_plan_id": self.occurrence_plan_id,
            "context_id": self.context_id,
            "state_semantic_id": self.state_semantic_id,
            "state_record_id": self.state_record_id,
            "ground_state_id": self.ground_state_id,
            "state_ranks": list(self.state_ranks),
            "remaining_horizon": self.remaining_horizon,
            "selected_action_semantic_id": (
                self.selected_action_semantic_id
            ),
            "selected_action_record_id": (
                self.selected_action_record_id
            ),
            "selected_ground_action_id": (
                self.selected_ground_action_id
            ),
            "action": list(self.action),
            "deterministic": True,
            "randomized_policy": False,
        }

    @property
    def decision_id(self) -> str:
        return self._decision_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


_POLICY_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectDeterministicPolicyV1:
    """Exact adapter-ready policy derived only from a verified ground audit."""

    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    final_preregistration_id: str
    occurrence_plan_id: str
    context_id: str
    checkpoint_id: str
    direct_snapshot_id: str
    planner_model_id: str
    threshold_profile_id: str
    audit_id: str
    root_decision: RegisteredMatchedDirectGroundDecisionV1
    child_decisions: tuple[RegisteredMatchedDirectGroundDecisionV1, ...]
    deterministic_finite_horizon_markov: bool = True
    _policy_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authority_chain_id, "policy authority chain"),
            (self.anchor_id, "policy anchor"),
            (
                self.final_preregistration_id,
                "policy final preregistration",
            ),
            (self.occurrence_plan_id, "policy occurrence"),
            (self.context_id, "policy context"),
            (self.checkpoint_id, "policy checkpoint"),
            (self.direct_snapshot_id, "policy snapshot"),
            (self.planner_model_id, "policy model"),
            (self.threshold_profile_id, "policy threshold"),
            (self.audit_id, "policy audit"),
        ):
            _cid(value, label)
        if (
            self._minting_capability is not _POLICY_SENTINEL
            or type(self.root_decision)
            is not RegisteredMatchedDirectGroundDecisionV1
            or self.root_decision.remaining_horizon != prereg.HORIZON
            or self.root_decision.occurrence_plan_id
            != self.occurrence_plan_id
            or self.root_decision.context_id != self.context_id
            or type(self.child_decisions) is not tuple
            or any(
                type(item) is not RegisteredMatchedDirectGroundDecisionV1
                or item.remaining_horizon != 1
                or item.occurrence_plan_id != self.occurrence_plan_id
                or item.context_id != self.context_id
                for item in self.child_decisions
            )
            or tuple(
                item.semantic_key for item in self.child_decisions
            )
            != tuple(
                sorted(
                    {
                        item.semantic_key
                        for item in self.child_decisions
                    }
                )
            )
            or len(
                {
                    item.ground_state_id for item in self.child_decisions
                }
            )
            != len(self.child_decisions)
            or self.deterministic_finite_horizon_markov is not True
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "direct policy is caller-minted, incomplete, or nondeterministic"
            )
        object.__setattr__(
            self,
            "_policy_id",
            _content_id("policy", self._payload()),
        )

    @property
    def root_action(self) -> tuple[int, int, int]:
        return self.root_decision.action

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_deterministic_policy.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "occurrence_plan_id": self.occurrence_plan_id,
            "context_id": self.context_id,
            "checkpoint_id": self.checkpoint_id,
            "direct_snapshot_id": self.direct_snapshot_id,
            "planner_model_id": self.planner_model_id,
            "threshold_profile_id": self.threshold_profile_id,
            "audit_id": self.audit_id,
            "root_decision_id": self.root_decision.decision_id,
            "child_decision_ids": [
                item.decision_id for item in self.child_decisions
            ],
            "root_action": list(self.root_action),
            "deterministic_finite_horizon_markov": True,
            "policy_randomization_allowed": False,
            "adapter_ready_evaluator_semantics": True,
        }

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "root_decision": self.root_decision.to_document(),
            "child_decisions": [
                item.to_document() for item in self.child_decisions
            ],
            "policy_id": self.policy_id,
        }


def _decision_from_catalogue_assignment_v1(
    *,
    occurrence_plan_id: str,
    context_id: str,
    catalogue: cold.ColdPublicCatalogueV1,
    assignment: robust.RobustPolicyAssignmentV1,
) -> RegisteredMatchedDirectGroundDecisionV1:
    if (
        type(catalogue) is not cold.ColdPublicCatalogueV1
        or type(assignment) is not robust.RobustPolicyAssignmentV1
        or assignment.scope is not robust.PolicyScope.GROUND_STATE
        or assignment.remaining_horizon != catalogue.remaining_horizon
    ):
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "ground-direct audit contains a non-ground assignment"
        )
    state_id = cold_builder.ground_state_id_v1(
        context_id,
        catalogue.state,
        catalogue.remaining_horizon,
    )
    if assignment.scope_key != state_id:
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "ground-direct assignment is bound to the wrong state"
        )
    actions = {
        cold_builder.ground_action_id_v1(
            context_id,
            catalogue.state,
            catalogue.remaining_horizon,
            action,
        ): action
        for action in catalogue.actions
    }
    selected = actions.get(assignment.selected_action_key)
    if selected is None:
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "ground-direct assignment selects an unregistered action"
        )
    ranks = tuple(catalogue.state.document["ranks"])
    action = tuple(selected.document["action"])
    return RegisteredMatchedDirectGroundDecisionV1(
        occurrence_plan_id,
        context_id,
        catalogue.state.semantic_state_id,
        catalogue.state.state_record_id,
        state_id,
        ranks,
        catalogue.remaining_horizon,
        selected.semantic_action_id,
        selected.action_record_id,
        assignment.selected_action_key,
        _action_triple(action, "cold public selected action"),
    )


def _derive_deterministic_policy_v1(
    *,
    checkpoint_artifact: Any,
    audit: robust.RobustPlanAuditV1,
) -> RegisteredMatchedDirectDeterministicPolicyV1:
    from acfqp import (
        v072_registered_matched_direct_complete_inventory_v1 as inventory,
    )

    if (
        type(checkpoint_artifact)
        is not inventory.RegisteredMatchedDirectCompleteInventoryCheckpointV1
        or type(audit) is not robust.RobustPlanAuditV1
        or audit.solver_kind is not robust.RobustSolverKind.GROUND_DIRECT
        or audit.model_id
        != checkpoint_artifact.direct_snapshot.planner_model.model_id
        or audit.threshold_profile_id
        != (
            checkpoint_artifact.direct_snapshot
            .threshold_profile.threshold_profile_id
        )
    ):
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "deterministic policy requires one exact ground-direct audit"
        )
    closure = checkpoint_artifact.closure_bundle
    catalogues = (
        closure.root_catalogue,
        *closure.child_catalogues,
    )
    assignments = {
        (item.scope_key, item.remaining_horizon): item
        for item in audit.assignments
    }
    if (
        len(assignments) != len(audit.assignments)
        or len(assignments) != len(catalogues)
    ):
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "ground-direct audit does not assign each reachable state once"
        )
    decisions = []
    for catalogue in catalogues:
        ground_state_id = cold_builder.ground_state_id_v1(
            closure.context_id,
            catalogue.state,
            catalogue.remaining_horizon,
        )
        assignment = assignments.get(
            (ground_state_id, catalogue.remaining_horizon)
        )
        if assignment is None:
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "ground-direct audit omits one reachable state"
            )
        decisions.append(
            _decision_from_catalogue_assignment_v1(
                occurrence_plan_id=(
                    checkpoint_artifact.occurrence_plan_id
                ),
                context_id=closure.context_id,
                catalogue=catalogue,
                assignment=assignment,
            )
        )
    roots = tuple(
        item for item in decisions if item.remaining_horizon == prereg.HORIZON
    )
    children = tuple(
        sorted(
            (
                item
                for item in decisions
                if item.remaining_horizon == 1
            ),
            key=lambda item: item.semantic_key,
        )
    )
    if (
        len(roots) != 1
        or roots[0].ground_state_id
        != checkpoint_artifact.direct_snapshot.planner_model.root_state_id
    ):
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "ground-direct audit has no unique registered root decision"
        )
    return RegisteredMatchedDirectDeterministicPolicyV1(
        _POLICY_SENTINEL,
        checkpoint_artifact.authority_chain_id,
        checkpoint_artifact.anchor_id,
        checkpoint_artifact.final_preregistration_id,
        checkpoint_artifact.occurrence_plan_id,
        checkpoint_artifact.context_id,
        checkpoint_artifact.checkpoint_id,
        checkpoint_artifact.direct_snapshot.snapshot_id,
        checkpoint_artifact.direct_snapshot.planner_model.model_id,
        (
            checkpoint_artifact.direct_snapshot
            .threshold_profile.threshold_profile_id
        ),
        audit.audit_id,
        roots[0],
        children,
    )


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectCheckpointRecordV1:
    inventory_checkpoint: Any
    planner_result: lazy.ExactLazyH2SolveResultV1
    proof_verification: (
        lazy_independent.ExactLazyH2IndependentVerificationV1 | None
    )
    status: RegisteredMatchedDirectCheckpointStatusV1
    deterministic_policy: (
        RegisteredMatchedDirectDeterministicPolicyV1 | None
    )
    _record_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from acfqp import (
            v072_registered_matched_direct_complete_inventory_v1
            as inventory,
        )

        checkpoint_type = (
            inventory
            .RegisteredMatchedDirectCompleteInventoryCheckpointV1
        )
        solved = (
            type(self.planner_result) is lazy.ExactLazyH2SolveResultV1
            and self.planner_result.status
            is lazy.ExactLazyH2SolveStatus.SOLVED
        )
        audit = (
            self.planner_result.audit
            if type(self.planner_result)
            is lazy.ExactLazyH2SolveResultV1
            else None
        )
        expected_status = (
            RegisteredMatchedDirectCheckpointStatusV1
            .SOLVER_RESOURCE_EXHAUSTED
            if not solved
            else (
                RegisteredMatchedDirectCheckpointStatusV1.CERTIFIED
                if (
                    type(audit) is robust.RobustPlanAuditV1
                    and audit.status is robust.RobustAuditStatus.CERTIFIED
                )
                else RegisteredMatchedDirectCheckpointStatusV1.NOT_CERTIFIED
            )
        )
        snapshot = (
            self.inventory_checkpoint.direct_snapshot
            if type(self.inventory_checkpoint) is checkpoint_type
            else None
        )
        if (
            type(self.inventory_checkpoint) is not checkpoint_type
            or type(self.planner_result)
            is not lazy.ExactLazyH2SolveResultV1
            or self.planner_result.solver_kind
            is not robust.RobustSolverKind.GROUND_DIRECT
            or type(self.status)
            is not RegisteredMatchedDirectCheckpointStatusV1
            or self.status is not expected_status
            or snapshot is None
            or (
                solved
                and (
                    type(audit) is not robust.RobustPlanAuditV1
                    or type(self.proof_verification)
                    is not (
                        lazy_independent
                        .ExactLazyH2IndependentVerificationV1
                    )
                    or self.proof_verification.audit_id
                    != audit.audit_id
                    or self.proof_verification.model_id
                    != snapshot.planner_model.model_id
                    or self.proof_verification.threshold_profile_id
                    != snapshot.threshold_profile.threshold_profile_id
                    or type(self.deterministic_policy)
                    is not RegisteredMatchedDirectDeterministicPolicyV1
                    or self.deterministic_policy.audit_id
                    != audit.audit_id
                    or self.deterministic_policy.checkpoint_id
                    != self.inventory_checkpoint.checkpoint_id
                )
            )
            or (
                not solved
                and (
                    self.planner_result.status
                    is not (
                        lazy.ExactLazyH2SolveStatus
                        .EXACT_DP_RESOURCE_EXHAUSTED
                    )
                    or self.planner_result.exhaustion is None
                    or self.proof_verification is not None
                    or self.deterministic_policy is not None
                )
            )
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "direct checkpoint/model/solve/proof/policy chain is invalid"
            )
        object.__setattr__(
            self,
            "_record_id",
            _content_id("checkpoint_record", self._payload()),
        )

    @property
    def checkpoint(self) -> int:
        return self.inventory_checkpoint.checkpoint

    def _payload(self) -> dict[str, Any]:
        audit = self.planner_result.audit
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_runtime_"
                "checkpoint_record.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "inventory_checkpoint_id": (
                self.inventory_checkpoint.checkpoint_id
            ),
            "inventory_work_id": self.inventory_checkpoint.work.work_id,
            "direct_snapshot_id": (
                self.inventory_checkpoint.direct_snapshot.snapshot_id
            ),
            "model_attestation_id": (
                self.inventory_checkpoint.model_attestation.attestation_id
            ),
            "planner_result": _solve_result_document(
                self.planner_result
            ),
            "audit_id": None if audit is None else audit.audit_id,
            "proof_verification_id": (
                None
                if self.proof_verification is None
                else self.proof_verification.verification_id
            ),
            "deterministic_policy_id": (
                None
                if self.deterministic_policy is None
                else self.deterministic_policy.policy_id
            ),
            "status": self.status.value,
            "exact_ground_direct_only": True,
            "approximation_used": False,
        }

    @property
    def record_id(self) -> str:
        return self._record_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "proof_verification": (
                None
                if self.proof_verification is None
                else self.proof_verification.to_document()
            ),
            "deterministic_policy": (
                None
                if self.deterministic_policy is None
                else self.deterministic_policy.to_document()
            ),
            "record_id": self.record_id,
        }


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectOccurrenceResultV1:
    authority_chain_id: str
    anchor_id: str
    final_preregistration_id: str
    occurrence_plan_id: str
    context_id: str
    checkpoint_records: tuple[
        RegisteredMatchedDirectCheckpointRecordV1, ...
    ]
    terminal_class: RegisteredMatchedDirectTerminalClassV1
    terminal_code: RegisteredMatchedDirectTerminalCodeV1
    stopped_checkpoint: int
    physical_row_count: int
    acquisition_sample_total: int
    deterministic_verifier_replay_total: int
    exact_lazy_ground_planner_calls: int
    independent_lazy_proof_verifications: int
    selected_policy: (
        RegisteredMatchedDirectDeterministicPolicyV1 | None
    )
    access_audit: RegisteredMatchedDirectAccessAuditV1
    terminal_adapter_blocker: str = TERMINAL_ADAPTER_DEPENDENCY_BLOCKER
    terminal_adapter_invocations: int = 0
    source_prior_reads: int = 0
    quotient_model_builds: int = 0
    quotient_planner_calls: int = 0
    local_recovery_calls: int = 0
    fallback_calls: int = 0
    exact_ground_evaluator_calls: int = 0
    crn_draw_discount: int = 0
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authority_chain_id, "direct result authority chain"),
            (self.anchor_id, "direct result anchor"),
            (
                self.final_preregistration_id,
                "direct result final preregistration",
            ),
            (self.occurrence_plan_id, "direct result occurrence"),
            (self.context_id, "direct result context"),
        ):
            _cid(value, label)
        if (
            type(self.checkpoint_records) is not tuple
            or not self.checkpoint_records
            or any(
                type(item) is not RegisteredMatchedDirectCheckpointRecordV1
                for item in self.checkpoint_records
            )
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "direct occurrence result has no exact checkpoint prefix"
            )
        checkpoints = tuple(
            item.checkpoint for item in self.checkpoint_records
        )
        certified = tuple(
            item
            for item in self.checkpoint_records
            if item.status
            is RegisteredMatchedDirectCheckpointStatusV1.CERTIFIED
        )
        exhausted = tuple(
            item
            for item in self.checkpoint_records
            if item.status
            is (
                RegisteredMatchedDirectCheckpointStatusV1
                .SOLVER_RESOURCE_EXHAUSTED
            )
        )
        expected_terminal = (
            (
                RegisteredMatchedDirectTerminalClassV1.PLAN_CERTIFICATE,
                (
                    RegisteredMatchedDirectTerminalCodeV1
                    .CONDITIONAL_PLAN_CERTIFICATE
                ),
            )
            if certified
            else (
                (
                    RegisteredMatchedDirectTerminalClassV1
                    .ATTEMPT_CLOSURE_NONCERTIFICATE
                ),
                (
                    RegisteredMatchedDirectTerminalCodeV1
                    .EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE
                    if exhausted
                    else (
                        RegisteredMatchedDirectTerminalCodeV1
                        .DIRECT_CHECKPOINT_CAP_EXHAUSTED_NONCERTIFICATE
                    )
                ),
            )
        )
        final = self.checkpoint_records[-1]
        final_checkpoint = final.inventory_checkpoint
        row_ids = final_checkpoint.stable_row_binding_ids
        solved_count = sum(
            item.planner_result.status
            is lazy.ExactLazyH2SolveStatus.SOLVED
            for item in self.checkpoint_records
        )
        if (
            checkpoints != CHECKPOINTS[: len(checkpoints)]
            or len(certified) > 1
            or (
                certified
                and certified[0] is not self.checkpoint_records[-1]
            )
            or len(exhausted) > 1
            or (
                exhausted
                and exhausted[0] is not self.checkpoint_records[-1]
            )
            or (
                not certified
                and not exhausted
                and checkpoints[-1] != CHECKPOINTS[-1]
            )
            or (self.terminal_class, self.terminal_code)
            != expected_terminal
            or self.terminal_code.value not in prereg.TERMINAL_CODES
            or self.stopped_checkpoint != checkpoints[-1]
            or self.physical_row_count != len(row_ids)
            or self.acquisition_sample_total
            != final_checkpoint.work.acquisition_sample_total
            or self.deterministic_verifier_replay_total
            != (
                final_checkpoint.work
                .deterministic_verifier_replay_total
            )
            or self.exact_lazy_ground_planner_calls
            != len(self.checkpoint_records)
            or self.independent_lazy_proof_verifications != solved_count
            or (
                bool(certified)
                != (
                    type(self.selected_policy)
                    is RegisteredMatchedDirectDeterministicPolicyV1
                )
            )
            or (
                certified
                and self.selected_policy
                != self.checkpoint_records[-1].deterministic_policy
            )
            or type(self.access_audit)
            is not RegisteredMatchedDirectAccessAuditV1
            or self.access_audit.ground_planner_calls
            != len(self.checkpoint_records)
            or self.access_audit.proof_verification_calls != solved_count
            or self.access_audit.evaluator_terminal_mint_calls != 0
            or self.terminal_adapter_blocker
            != TERMINAL_ADAPTER_DEPENDENCY_BLOCKER
            or self.terminal_adapter_invocations != 0
            or any(
                value != 0
                for value in (
                    self.source_prior_reads,
                    self.quotient_model_builds,
                    self.quotient_planner_calls,
                    self.local_recovery_calls,
                    self.fallback_calls,
                    self.exact_ground_evaluator_calls,
                    self.crn_draw_discount,
                )
            )
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "direct result stopped early, undercounted, or crossed routes"
            )
        prior = None
        for record in self.checkpoint_records:
            checkpoint = record.inventory_checkpoint
            if (
                checkpoint.authority_chain_id != self.authority_chain_id
                or checkpoint.anchor_id != self.anchor_id
                or checkpoint.final_preregistration_id
                != self.final_preregistration_id
                or checkpoint.occurrence_plan_id
                != self.occurrence_plan_id
                or checkpoint.context_id != self.context_id
                or checkpoint.stable_row_binding_ids != row_ids
                or (
                    prior is None
                    and checkpoint.previous_checkpoint_id is not None
                )
                or (
                    prior is not None
                    and checkpoint.previous_checkpoint_id
                    != prior.checkpoint_id
                )
            ):
                raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                    "direct result checkpoint lineage is stale or transplanted"
                )
            if prior is not None:
                if tuple(
                    item.previous_prefix_id for item in checkpoint.row_prefixes
                ) != tuple(
                    item.prefix_id for item in prior.row_prefixes
                ):
                    raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                        "direct result row prefixes are not append-only"
                    )
            prior = checkpoint
        object.__setattr__(
            self,
            "_result_id",
            _content_id("occurrence_result", self._payload()),
        )

    @property
    def certified(self) -> bool:
        return (
            self.terminal_class
            is RegisteredMatchedDirectTerminalClassV1.PLAN_CERTIFICATE
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_occurrence_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "occurrence_plan_id": self.occurrence_plan_id,
            "context_id": self.context_id,
            "arm": ARM,
            "checkpoint_record_ids": [
                item.record_id for item in self.checkpoint_records
            ],
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "stopped_checkpoint": self.stopped_checkpoint,
            "physical_row_count": self.physical_row_count,
            "acquisition_sample_total": self.acquisition_sample_total,
            "deterministic_verifier_replay_total": (
                self.deterministic_verifier_replay_total
            ),
            "acquisition_and_replay_lanes_separate": True,
            "checkpoint_totals_summed": False,
            "exact_lazy_ground_planner_calls": (
                self.exact_lazy_ground_planner_calls
            ),
            "independent_lazy_proof_verifications": (
                self.independent_lazy_proof_verifications
            ),
            "selected_policy_id": (
                None
                if self.selected_policy is None
                else self.selected_policy.policy_id
            ),
            "access_audit_id": self.access_audit.audit_id,
            "terminal_adapter_blocker": self.terminal_adapter_blocker,
            "terminal_adapter_invocations": 0,
            "source_prior_reads": 0,
            "quotient_model_builds": 0,
            "quotient_planner_calls": 0,
            "local_recovery_calls": 0,
            "fallback_calls": 0,
            "exact_ground_evaluator_calls": 0,
            "crn_draw_discount": 0,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "checkpoint_records": [
                item.to_document() for item in self.checkpoint_records
            ],
            "selected_policy": (
                None
                if self.selected_policy is None
                else self.selected_policy.to_document()
            ),
            "access_audit": self.access_audit.to_document(),
            "result_id": self.result_id,
        }


_OCCURRENCE_VERIFICATION_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectOccurrenceIndependentVerificationV1:
    _minting_capability: object
    occurrence_result_id: str
    checkpoint_record_ids: tuple[str, ...]
    inventory_checkpoint_ids: tuple[str, ...]
    proof_verification_ids: tuple[str, ...]
    deterministic_policy_ids: tuple[str, ...]
    selected_policy_id: str | None
    stopped_checkpoint: int
    acquisition_sample_total: int
    deterministic_verifier_replay_total: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_result_id, "verified direct result"),
            *(
                (item, "verified direct checkpoint record")
                for item in self.checkpoint_record_ids
            ),
            *(
                (item, "verified direct inventory checkpoint")
                for item in self.inventory_checkpoint_ids
            ),
            *(
                (item, "verified direct lazy proof")
                for item in self.proof_verification_ids
            ),
            *(
                (item, "verified direct deterministic policy")
                for item in self.deterministic_policy_ids
            ),
        ):
            _cid(value, label)
        if self.selected_policy_id is not None:
            _cid(self.selected_policy_id, "verified selected direct policy")
        if (
            self._minting_capability
            is not _OCCURRENCE_VERIFICATION_SENTINEL
            or not self.checkpoint_record_ids
            or len(self.checkpoint_record_ids)
            != len(self.inventory_checkpoint_ids)
            or self.stopped_checkpoint not in CHECKPOINTS
            or type(self.acquisition_sample_total) is not int
            or self.acquisition_sample_total <= 0
            or type(self.deterministic_verifier_replay_total) is not int
            or self.deterministic_verifier_replay_total <= 0
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "independent direct occurrence verification is malformed"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _content_id("occurrence_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_occurrence_"
                "independent_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_result_id": self.occurrence_result_id,
            "checkpoint_record_ids": list(self.checkpoint_record_ids),
            "inventory_checkpoint_ids": list(
                self.inventory_checkpoint_ids
            ),
            "proof_verification_ids": list(
                self.proof_verification_ids
            ),
            "deterministic_policy_ids": list(
                self.deterministic_policy_ids
            ),
            "selected_policy_id": self.selected_policy_id,
            "stopped_checkpoint": self.stopped_checkpoint,
            "acquisition_sample_total": self.acquisition_sample_total,
            "deterministic_verifier_replay_total": (
                self.deterministic_verifier_replay_total
            ),
            "complete_inventory_replayed": True,
            "exact_lazy_proofs_replayed": True,
            "deterministic_policy_rederived": True,
            "production_planner_called": False,
            "observer_or_target_access": 0,
            "execution_lane": "EVALUATION_INDEPENDENT_RUNTIME_REPLAY",
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def _recompute_occurrence_access_audit_v1(
    result: RegisteredMatchedDirectOccurrenceResultV1,
) -> RegisteredMatchedDirectAccessAuditV1:
    final_checkpoint = result.checkpoint_records[-1].inventory_checkpoint
    row_count = len(final_checkpoint.stable_row_binding_ids)
    checkpoint_count = len(result.checkpoint_records)
    acquisition_draws = (
        final_checkpoint.work.acquisition_sample_total
    )
    replay_draws = (
        final_checkpoint.work.deterministic_verifier_replay_total
    )
    solved_count = sum(
        item.planner_result.status is lazy.ExactLazyH2SolveStatus.SOLVED
        for item in result.checkpoint_records
    )
    stream_opens = 2 * row_count
    return RegisteredMatchedDirectAccessAuditV1(
        anchor_checks=1,
        occurrence_identity_checks=1,
        authority_chain_verifications=1,
        inventory_accumulator_open_calls=1,
        inventory_checkpoint_acquisition_calls=checkpoint_count,
        inventory_checkpoint_verification_calls=checkpoint_count,
        observer_inventory_calls=(
            2 + len(final_checkpoint.closure_bundle.child_catalogues)
        ),
        acquisition_stream_opens=stream_opens,
        acquisition_draw_calls=acquisition_draws,
        independent_replay_stream_opens=stream_opens,
        independent_replay_draw_calls=replay_draws,
        observer_stream_opens=2 * stream_opens,
        observer_draw_calls=acquisition_draws + replay_draws,
        accepted_observations=acquisition_draws,
        confidence_accumulator_calls=row_count * checkpoint_count,
        direct_model_build_calls=checkpoint_count,
        direct_model_verification_calls=2 * checkpoint_count,
        ground_planner_calls=checkpoint_count,
        proof_verification_calls=solved_count,
        evaluator_terminal_mint_calls=0,
    )


def verify_registered_matched_direct_occurrence_result_v1(
    result: RegisteredMatchedDirectOccurrenceResultV1,
) -> RegisteredMatchedDirectOccurrenceIndependentVerificationV1:
    """Replay every inventory, proof, policy, lineage, and terminal claim."""

    from acfqp import (
        v072_registered_matched_direct_complete_inventory_v1 as inventory,
    )

    if type(result) is not RegisteredMatchedDirectOccurrenceResultV1:
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "direct result verifier requires the exact result type"
        )
    proof_ids: list[str] = []
    policy_ids: list[str] = []
    for record in result.checkpoint_records:
        replayed_checkpoint = (
            inventory
            .verify_registered_matched_direct_complete_inventory_checkpoint_v1(
                checkpoint_artifact=record.inventory_checkpoint
            )
        )
        if replayed_checkpoint != record.inventory_checkpoint:
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "direct inventory replay differs from the runtime record"
            )
        if (
            record.planner_result.status
            is lazy.ExactLazyH2SolveStatus.SOLVED
        ):
            replayed_proof = (
                lazy_independent.verify_exact_lazy_h2_solve_result_v1(
                    replayed_checkpoint.direct_snapshot.planner_model,
                    replayed_checkpoint.direct_snapshot.threshold_profile,
                    record.planner_result,
                )
            )
            replayed_policy = _derive_deterministic_policy_v1(
                checkpoint_artifact=replayed_checkpoint,
                audit=record.planner_result.audit,
            )
            if (
                replayed_proof != record.proof_verification
                or replayed_policy != record.deterministic_policy
            ):
                raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                    "direct proof or deterministic policy replay differs"
                )
            proof_ids.append(replayed_proof.verification_id)
            policy_ids.append(replayed_policy.policy_id)
        elif (
            record.proof_verification is not None
            or record.deterministic_policy is not None
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "resource-exhausted direct record carries a policy/proof"
            )
        replayed_record = RegisteredMatchedDirectCheckpointRecordV1(
            record.inventory_checkpoint,
            record.planner_result,
            record.proof_verification,
            record.status,
            record.deterministic_policy,
        )
        if replayed_record.record_id != record.record_id:
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "direct checkpoint record content commitment changed"
            )
    replayed_access_audit = _recompute_occurrence_access_audit_v1(result)
    if replayed_access_audit != result.access_audit:
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "direct occurrence native access accounting differs"
        )
    replayed_result = RegisteredMatchedDirectOccurrenceResultV1(
        result.authority_chain_id,
        result.anchor_id,
        result.final_preregistration_id,
        result.occurrence_plan_id,
        result.context_id,
        result.checkpoint_records,
        result.terminal_class,
        result.terminal_code,
        result.stopped_checkpoint,
        result.physical_row_count,
        result.acquisition_sample_total,
        result.deterministic_verifier_replay_total,
        result.exact_lazy_ground_planner_calls,
        result.independent_lazy_proof_verifications,
        result.selected_policy,
        replayed_access_audit,
        result.terminal_adapter_blocker,
        result.terminal_adapter_invocations,
        result.source_prior_reads,
        result.quotient_model_builds,
        result.quotient_planner_calls,
        result.local_recovery_calls,
        result.fallback_calls,
        result.exact_ground_evaluator_calls,
        result.crn_draw_discount,
    )
    if replayed_result.result_id != result.result_id:
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "direct occurrence result content commitment changed"
        )
    selected_policy_id = (
        None
        if result.selected_policy is None
        else result.selected_policy.policy_id
    )
    if (
        result.certified
        and (
            not policy_ids
            or selected_policy_id != policy_ids[-1]
        )
    ):
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "certified direct result does not select its final verified policy"
        )
    return RegisteredMatchedDirectOccurrenceIndependentVerificationV1(
        _OCCURRENCE_VERIFICATION_SENTINEL,
        result.result_id,
        tuple(item.record_id for item in result.checkpoint_records),
        tuple(
            item.inventory_checkpoint.checkpoint_id
            for item in result.checkpoint_records
        ),
        tuple(proof_ids),
        tuple(policy_ids),
        selected_policy_id,
        result.stopped_checkpoint,
        result.acquisition_sample_total,
        result.deterministic_verifier_replay_total,
    )


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectEvaluatorTerminalBundleV1:
    """Future runtime output; evaluator-owned types remain privately minted."""

    occurrence_plan_id: str
    runtime_result_id: str
    operational_terminal: evaluator.RegisteredOccurrenceOperationalTerminalV1
    selected_policy: evaluator.RegisteredOperationalSelectedPolicyV1
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.occurrence_plan_id, "direct terminal occurrence")
        _cid(self.runtime_result_id, "direct terminal runtime result")
        if (
            type(self.operational_terminal)
            is not evaluator.RegisteredOccurrenceOperationalTerminalV1
            or type(self.selected_policy)
            is not evaluator.RegisteredOperationalSelectedPolicyV1
            or self.operational_terminal.selected_policy_id
            != self.selected_policy.selected_policy_id
        ):
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "matched-direct evaluator terminal/policy is unminted or stale"
            )
        object.__setattr__(
            self,
            "_bundle_id",
            _content_id(
                "terminal_bundle",
                {
                    "schema": (
                        "acfqp.v072_registered_matched_direct_evaluator_"
                        "terminal_bundle.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "occurrence_plan_id": self.occurrence_plan_id,
                    "runtime_result_id": self.runtime_result_id,
                    "operational_terminal_id": (
                        self.operational_terminal.terminal_id
                    ),
                    "selected_policy_id": (
                        self.selected_policy.selected_policy_id
                    ),
                },
            ),
        )

    @property
    def bundle_id(self) -> str:
        return self._bundle_id


def _require_anchor_without_observer_access(
    anchor: Any,
) -> final_authority.V072RemoteMainAnchorV1:
    if (
        type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or final_authority.REMOTE_MAIN_ANCHOR_AUTHORITY_ENABLED is not True
        or anchor.target_execution_allowed is not True
        or type(anchor.claim) is not final_authority.V072RemoteMainAnchorClaimV1
        or anchor.claim.verification_scope
        is not (
            final_authority.RemoteMainAnchorVerificationScopeV1
            .REGISTERED_PRODUCTION_CANDIDATE
        )
    ):
        raise RegisteredMatchedDirectRuntimeLockedV1(
            "registered matched-direct runtime requires the exact enabled "
            "V072RemoteMainAnchorV1",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    return anchor


def _require_context_without_observer_access(
    context: Any,
) -> prereg.HeldoutPublicGraphContextV2:
    contexts = prereg.registered_heldout_public_contexts_v2()
    if (
        type(context) is not prereg.HeldoutPublicGraphContextV2
        or context not in contexts
    ):
        raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
            "registered matched-direct runtime requires one exact public "
            "context"
        )
    return context


def _require_production_identity_without_observer_access(
    *,
    authority_chain: Any,
    anchor: Any,
    occurrence_plan: Any,
    context: Any,
) -> tuple[
    consumer.RegisteredCampaignAuthorityChainV1,
    final_authority.V072RemoteMainAnchorV1,
    RegisteredMatchedDirectOccurrencePlanV1,
    prereg.HeldoutPublicGraphContextV2,
]:
    canonical_anchor = _require_anchor_without_observer_access(anchor)
    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or authority_chain.remote_main_anchor is not canonical_anchor
        or type(occurrence_plan)
        is not RegisteredMatchedDirectOccurrencePlanV1
        or type(context) is not prereg.HeldoutPublicGraphContextV2
    ):
        raise RegisteredMatchedDirectRuntimeLockedV1(
            "registered matched-direct runtime requires one exact "
            "chain/anchor/plan/context identity",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    try:
        (
            _source_recipe_id,
            _manifest_id,
            final_preregistration_id,
            anchor_id,
            _anchor_attestation_id,
        ) = consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (
        consumer.RegisteredCampaignAuthorityGateLockedV1,
        ValueError,
    ) as error:
        raise RegisteredMatchedDirectRuntimeLockedV1(
            "registered matched-direct authority chain replay failed before "
            "observer access",
            access_audit=ZERO_ACCESS_AUDIT,
        ) from error
    try:
        canonical_context = _require_context_without_observer_access(
            context
        )
    except V072RegisteredMatchedDirectRuntimeInvariantViolation as error:
        raise RegisteredMatchedDirectRuntimeLockedV1(
            "registered matched-direct context is outside the registry",
            access_audit=ZERO_ACCESS_AUDIT,
        ) from error
    if (
        occurrence_plan.anchor_id != anchor_id
        or occurrence_plan.anchor_id != canonical_anchor.anchor_id
        or occurrence_plan.context_id != canonical_context.context_id
        or occurrence_plan.context_key != canonical_context.context_key
        or occurrence_plan.arm != ARM
        or occurrence_plan.maximum_checkpoint != CHECKPOINTS[-1]
        or occurrence_plan.replacement_allowed is not False
        or occurrence_plan.early_skip_allowed is not False
        or canonical_anchor.claim.final_preregistration_id
        != final_preregistration_id
    ):
        raise RegisteredMatchedDirectRuntimeLockedV1(
            "registered matched-direct occurrence identity is stale or "
            "transplanted",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    return (
        authority_chain,
        canonical_anchor,
        occurrence_plan,
        canonical_context,
    )


def run_registered_matched_direct_occurrence_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: RegisteredMatchedDirectOccurrencePlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
) -> RegisteredMatchedDirectOccurrenceResultV1:
    """Run the frozen synchronous direct schedule from internal observations."""

    (
        canonical_chain,
        canonical_anchor,
        canonical_plan,
        canonical_context,
    ) = _require_production_identity_without_observer_access(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=occurrence_plan,
        context=context,
    )
    dependency = inspect_registered_matched_direct_dependency_protocol_v1()
    if (
        REGISTERED_RUNTIME_ENABLED is not True
        or dependency.dependency_available is not True
    ):
        raise RegisteredMatchedDirectDependencyBlockedV1(
            "registered matched-direct target remains unopened; blockers="
            + ",".join(dependency.blockers),
            occurrence_plan=canonical_plan,
            dependency_protocol=dependency,
            access_audit=RegisteredMatchedDirectAccessAuditV1(
                anchor_checks=1,
                occurrence_identity_checks=1,
                authority_chain_verifications=1,
            ),
        )
    from acfqp import (
        v072_registered_matched_direct_complete_inventory_v1 as inventory,
    )
    from acfqp import (
        v072_registered_campaign_attempt_journal_v1 as attempt_journal,
    )

    accumulator = (
        inventory
        .open_registered_matched_direct_complete_inventory_accumulator_v1(
            authority_chain=canonical_chain,
            anchor=canonical_anchor,
            occurrence_plan=canonical_plan,
            context=canonical_context,
        )
    )
    journal = attempt_journal.active_attempt_journal_v1(
        authority_chain=canonical_chain,
    )
    records: list[RegisteredMatchedDirectCheckpointRecordV1] = []
    for checkpoint in CHECKPOINTS:
        checkpoint_artifact = (
            inventory
            .acquire_registered_matched_direct_complete_inventory_checkpoint_v1(
                accumulator=accumulator,
                checkpoint=checkpoint,
            )
        )
        replayed_checkpoint = (
            inventory
            .verify_registered_matched_direct_complete_inventory_checkpoint_v1(
                checkpoint_artifact=checkpoint_artifact
            )
        )
        if replayed_checkpoint != checkpoint_artifact:
            raise V072RegisteredMatchedDirectRuntimeInvariantViolation(
                "runtime inventory checkpoint independent replay differs"
            )
        snapshot = checkpoint_artifact.direct_snapshot
        planner_result = lazy.solve_exact_lazy_ground_direct_h2_v1(
            snapshot.planner_model,
            snapshot.threshold_profile,
            limits=REGISTERED_EXACT_LAZY_RESOURCE_LIMITS,
        )
        proof_verification = None
        policy = None
        if planner_result.status is lazy.ExactLazyH2SolveStatus.SOLVED:
            proof_verification = (
                lazy_independent.verify_exact_lazy_h2_solve_result_v1(
                    snapshot.planner_model,
                    snapshot.threshold_profile,
                    planner_result,
                )
            )
            assert planner_result.audit is not None
            policy = _derive_deterministic_policy_v1(
                checkpoint_artifact=checkpoint_artifact,
                audit=planner_result.audit,
            )
        status = (
            (
                RegisteredMatchedDirectCheckpointStatusV1
                .SOLVER_RESOURCE_EXHAUSTED
            )
            if planner_result.status
            is lazy.ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED
            else (
                RegisteredMatchedDirectCheckpointStatusV1.CERTIFIED
                if (
                    planner_result.audit is not None
                    and planner_result.audit.status
                    is robust.RobustAuditStatus.CERTIFIED
                )
                else RegisteredMatchedDirectCheckpointStatusV1.NOT_CERTIFIED
            )
        )
        record = RegisteredMatchedDirectCheckpointRecordV1(
            checkpoint_artifact,
            planner_result,
            proof_verification,
            status,
            policy,
        )
        records.append(record)
        if journal is not None:
            journal.commit_direct_checkpoint(
                context_id=canonical_context.context_id,
                checkpoint_record=record,
            )
        if status is not RegisteredMatchedDirectCheckpointStatusV1.NOT_CERTIFIED:
            break
    final = records[-1]
    terminal_code = (
        (
            RegisteredMatchedDirectTerminalCodeV1
            .CONDITIONAL_PLAN_CERTIFICATE
        )
        if final.status
        is RegisteredMatchedDirectCheckpointStatusV1.CERTIFIED
        else (
            RegisteredMatchedDirectTerminalCodeV1
            .EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE
            if final.status
            is (
                RegisteredMatchedDirectCheckpointStatusV1
                .SOLVER_RESOURCE_EXHAUSTED
            )
            else (
                RegisteredMatchedDirectTerminalCodeV1
                .DIRECT_CHECKPOINT_CAP_EXHAUSTED_NONCERTIFICATE
            )
        )
    )
    terminal_class = (
        RegisteredMatchedDirectTerminalClassV1.PLAN_CERTIFICATE
        if terminal_code
        is (
            RegisteredMatchedDirectTerminalCodeV1
            .CONDITIONAL_PLAN_CERTIFICATE
        )
        else (
            RegisteredMatchedDirectTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
        )
    )
    inventory_audit = accumulator.access_audit
    solved_count = sum(
        item.planner_result.status is lazy.ExactLazyH2SolveStatus.SOLVED
        for item in records
    )
    access_audit = RegisteredMatchedDirectAccessAuditV1(
        anchor_checks=1,
        occurrence_identity_checks=1,
        authority_chain_verifications=1,
        inventory_accumulator_open_calls=1,
        inventory_checkpoint_acquisition_calls=len(records),
        inventory_checkpoint_verification_calls=len(records),
        observer_inventory_calls=inventory_audit.public_inventory_calls,
        acquisition_stream_opens=(
            inventory_audit.acquisition_stream_opens
        ),
        acquisition_draw_calls=inventory_audit.acquisition_draw_calls,
        independent_replay_stream_opens=(
            inventory_audit.replay_stream_opens
        ),
        independent_replay_draw_calls=(
            inventory_audit.replay_draw_calls
        ),
        observer_stream_opens=(
            inventory_audit.acquisition_stream_opens
            + inventory_audit.replay_stream_opens
        ),
        observer_draw_calls=(
            inventory_audit.acquisition_draw_calls
            + inventory_audit.replay_draw_calls
        ),
        accepted_observations=inventory_audit.acquisition_draw_calls,
        confidence_accumulator_calls=(
            accumulator.row_count * len(records)
        ),
        direct_model_build_calls=len(records),
        direct_model_verification_calls=2 * len(records),
        ground_planner_calls=len(records),
        proof_verification_calls=solved_count,
        evaluator_terminal_mint_calls=0,
    )
    final_checkpoint = final.inventory_checkpoint
    return RegisteredMatchedDirectOccurrenceResultV1(
        canonical_chain.chain_id,
        canonical_anchor.anchor_id,
        canonical_anchor.claim.final_preregistration_id,
        canonical_plan.plan_id,
        canonical_context.context_id,
        tuple(records),
        terminal_class,
        terminal_code,
        final.checkpoint,
        accumulator.row_count,
        final_checkpoint.work.acquisition_sample_total,
        (
            final_checkpoint.work
            .deterministic_verifier_replay_total
        ),
        len(records),
        solved_count,
        (
            final.deterministic_policy
            if terminal_class
            is RegisteredMatchedDirectTerminalClassV1.PLAN_CERTIFICATE
            else None
        ),
        access_audit,
    )


__all__ = [
    "ARM",
    "CHECKPOINTS",
    "DIRECT_CHECKPOINT_CAP_PREREG_AMENDMENT_BLOCKER",
    "DIRECT_CHECKPOINT_CAP_TERMINAL_CODE",
    "DIRECT_CHECKPOINT_CAP_TERMINAL_REGISTERED",
    "DISCOVERY_DRAWS_PER_ROW",
    "EVALUATOR_TERMINAL_MINT_DEPENDENCY_BLOCKER",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_EXACT_LAZY_RESOURCE_LIMITS",
    "REGISTERED_RUNTIME_ENABLED",
    "REGISTERED_RUNTIME_STATUS",
    "RegisteredMatchedDirectAccessAuditV1",
    "RegisteredMatchedDirectCheckpointRecordV1",
    "RegisteredMatchedDirectCheckpointStatusV1",
    "RegisteredMatchedDirectDependencyBlockedV1",
    "RegisteredMatchedDirectDependencyProtocolV1",
    "RegisteredMatchedDirectDeterministicPolicyV1",
    "RegisteredMatchedDirectEvaluatorTerminalBundleV1",
    "RegisteredMatchedDirectGroundDecisionV1",
    "RegisteredMatchedDirectOccurrenceIndependentVerificationV1",
    "RegisteredMatchedDirectOccurrencePlanV1",
    "RegisteredMatchedDirectOccurrenceResultV1",
    "RegisteredMatchedDirectRuntimeLockedV1",
    "RegisteredMatchedDirectTerminalClassV1",
    "RegisteredMatchedDirectTerminalCodeV1",
    "RegistrationDisjointDirectCheckpointRecordV1",
    "RegistrationDisjointDirectCheckpointStatusV1",
    "RegistrationDisjointDirectCheckpointV1",
    "RegistrationDisjointDirectCheckpointWorkV1",
    "RegistrationDisjointDirectRowPrefixV1",
    "RegistrationDisjointDirectScheduleRunV1",
    "SCHEMA_VERSION",
    "TERMINAL_ADAPTER_DEPENDENCY_BLOCKER",
    "V072RegisteredMatchedDirectRuntimeInvariantViolation",
    "ZERO_ACCESS_AUDIT",
    "inspect_registered_matched_direct_dependency_protocol_v1",
    "registered_matched_direct_occurrence_plan_v1",
    "run_registered_matched_direct_occurrence_v1",
    "run_registration_disjoint_direct_schedule_core_v1",
    "verify_registered_matched_direct_occurrence_result_v1",
]
