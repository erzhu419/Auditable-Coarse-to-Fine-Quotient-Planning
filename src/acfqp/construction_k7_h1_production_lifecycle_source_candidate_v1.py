"""Unanchored declarative H1 lifecycle candidate and first-failure prefixes.

This module closes one narrow construction question: what exact sequence of
shared-resource operations is the proposed H1 runtime supposed to execute?
One declarative transition table drives both candidate-prefix replay and
first-failure-prefix analysis.  The candidate binds the complete module bytes,
a normalized AST digest, and the exact source spans of the compiler, replayer,
analyser, and verifier.  It is constructed from the currently imported module
and has no external preregistration anchor, so those hashes are content identity
rather than production source authority.

It does *not* claim that the current live BROKER/WORKER/BUSINESS runtime calls
this table, that the table is complete for production, or that a first failure
ends an attempt.  Post-failure cleanup, common multiplicities, the output-DAG
leaf join, cap-owner semantic identity, native existence/extent evidence, and
the serializer authority remain unbound.  Accordingly no execution authority,
numeric operand, V7 upper, receipt, CounterRecord, WorkVector,
ComparisonVector, terminal classification, or Gate result is issued.
"""

from __future__ import annotations

import ast
from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import hmac
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_h1_execution_topology_profile_v1 as topology_v1
from acfqp import construction_k7_h1_production_output_upper_v1 as output_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_BRANCH_ANALYSIS_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_PROGRAM_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_MANIFEST_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.58"
PROFILE_KEY = "construction_k7_h1_production_lifecycle_source_candidate_v1"

DECLARATIVE_LIFECYCLE_SOURCE_AUTHORITY_PRESENT = False
DECLARATIVE_LIFECYCLE_CANDIDATE_PRESENT = True
COMPLETE_DECLARATIVE_FIRST_FAILURE_PREFIXES_PRESENT = False
COMPLETE_DECLARED_CANDIDATE_FIRST_FAILURE_PREFIXES_PRESENT = True
LIVE_RUNTIME_INTEGRATION_PRESENT = False
PRODUCTION_EXECUTION_AUTHORITY_PRESENT = False
NUMERIC_SHARED_OPERAND_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

SOURCE_MANIFEST_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_MANIFEST_V1_DOMAIN
)
PROGRAM_DOMAIN = CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_PROGRAM_V1_DOMAIN
BRANCH_ANALYSIS_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_BRANCH_ANALYSIS_V1_DOMAIN
)
REPLAY_DOMAIN = CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_REPLAY_V1_DOMAIN
SOURCE_CANDIDATE_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_CANDIDATE_V1_DOMAIN
)

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    SOURCE_MANIFEST_DOMAIN,
    PROGRAM_DOMAIN,
    BRANCH_ANALYSIS_DOMAIN,
    REPLAY_DOMAIN,
    SOURCE_CANDIDATE_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != len(REQUESTED_PHASE3E_DOMAIN_TAGS)
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover - central registry invariant
    raise RuntimeError("H1 lifecycle source-authority domains are not registered")

SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)

SOURCE_BOUND_SYMBOLS = (
    "_semantic_site_templates_v1",
    "_compile_lifecycle_transitions_v1",
    "replay_h1_production_lifecycle_events_v1",
    "_analyze_failure_prefixes_v1",
    "verify_h1_production_lifecycle_source_candidate_bytes_v1",
)

FORBIDDEN_FUTURE_FIELDS = frozenset(
    {
        "decision_point_id",
        "DecisionPoint_id",
        "RouteDecisionContext_id",
        "route_decision_context_id",
        "route_upper_id",
        "route_upper",
        "route_upper_bound_envelope_id",
        "formal_v7_route_upper_id",
        "route_decision_id",
        "route_decision",
        "formal_v7_route_decision_id",
        "marginal_route_decision_id",
        "selected_route",
        "route_decision_freeze_attestation_id",
        "freeze_attestation_id",
        "postrun_result_id",
        "actual_work_vector_id",
        "actual_comparison_vector_id",
    }
)

TYPED_PRODUCTION_BLOCKERS = (
    "EXTERNAL_PREREGISTRATION_SOURCE_ANCHOR_NOT_BOUND",
    "LIVE_BROKER_WORKER_BUSINESS_TRANSITION_DISPATCH_NOT_BOUND",
    "POST_FAILURE_CLEANUP_CONTINUATION_PROGRAM_NOT_BOUND",
    "COMMON_MULTIPLICITY_SOURCE_NOT_BOUND",
    "SHARED_CAP_OWNER_SEMANTIC_IDENTITY_NOT_BOUND",
    "OUTPUT_DAG_ROLE_PRESENCE_BRANCH_JOIN_NOT_BOUND",
    "BROKER_OWNED_NATIVE_CALLBACK_FACTS_NOT_BOUND",
    "NATIVE_EXISTENCE_AMBIGUITY_RESOLUTION_NOT_BOUND",
    "NATIVE_EXTENTS_AND_PHYSICAL_INSTANCE_IDENTITIES_NOT_BOUND",
    "PERSISTENT_ATOMIC_SINGLE_CONSUMPTION_RECEIPT_NOT_BOUND",
    "PRODUCTION_SERIALIZER_SOURCE_AUTHORITY_NOT_BOUND",
    "FALLBACK_CAP_EXHAUSTED_ROUTE_STAGE_BINDING_NOT_BOUND",
    "FORMAL_OPERAND_AND_V7_ROUTE_JOIN_NOT_BOUND",
)


class ConstructionK7H1ProductionLifecycleSourceCandidateV1Error(ValueError):
    """The source manifest, state machine, replay, or prefix proof failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1ProductionLifecycleSourceCandidateV1Error(message)


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{label} must be one nonempty exact string")
    return value


def _unique_strings(
    value: Any, label: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or (not allow_empty and not value)
        or len(value) != len(set(value))
        or any(type(item) is not str or not item for item in value)
    ):
        _fail(f"{label} must be one unique exact string tuple")
    return value


def _reject_future_fields(value: Any) -> None:
    if type(value) is dict:
        bad = FORBIDDEN_FUTURE_FIELDS & set(value)
        if bad:
            _fail(f"future authority field is forbidden: {sorted(bad)[0]}")
        for child in value.values():
            _reject_future_fields(child)
    elif type(value) is list:
        for child in value:
            _reject_future_fields(child)


class H1LifecycleOperationV1(str, Enum):
    MEMORY_BIND = "MEMORY_BIND"
    COMMON_HASH = "COMMON_HASH"
    COMMON_INTEGRITY = "COMMON_INTEGRITY"
    COMMON_PROTOCOL = "COMMON_PROTOCOL"
    OUTPUT_RESERVE = "OUTPUT_RESERVE"
    STAGE_INPUT = "STAGE_INPUT"
    MOUNT_OPEN = "MOUNT_OPEN"
    LAUNCH_CHILD = "LAUNCH_CHILD"
    READ_INPUT = "READ_INPUT"
    READ_BUSINESS_RESULT = "READ_BUSINESS_RESULT"
    DESCENDANT_REAP = "DESCENDANT_REAP"
    SAME_OFD_PEAK_READ = "SAME_OFD_PEAK_READ"
    MOUNT_CLOSE = "MOUNT_CLOSE"
    OUTPUT_ROLE_READBACK = "OUTPUT_ROLE_READBACK"
    OUTPUT_FINALIZE = "OUTPUT_FINALIZE"
    OUTPUT_CLOSE = "OUTPUT_CLOSE"


class H1LifecycleOutcomeV1(str, Enum):
    SUCCESS = "SUCCESS"
    CAP_REJECTED_BEFORE_SIDE_EFFECT = "CAP_REJECTED_BEFORE_SIDE_EFFECT"
    CALLBACK_FAILED_AFTER_ADMISSION = "CALLBACK_FAILED_AFTER_ADMISSION"
    NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION = (
        "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION"
    )
    OBSERVED_UPPER_BOUND_VIOLATION = "OBSERVED_UPPER_BOUND_VIOLATION"
    CLEANUP_FAILED = "CLEANUP_FAILED"
    PROTOCOL_FAILED = "PROTOCOL_FAILED"


class H1NativeExistenceV1(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    KNOWN_NOT_STARTED = "KNOWN_NOT_STARTED"
    MAY_HAVE_STARTED = "MAY_HAVE_STARTED"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True, slots=True)
class H1FailureEdgeV1:
    outcome: H1LifecycleOutcomeV1
    current_site_admitted: bool
    side_effect_may_have_started: bool
    native_existence: H1NativeExistenceV1
    provisional_primary_cause_class: str
    provisional_primary_cause_code: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "outcome", H1LifecycleOutcomeV1(self.outcome))
            object.__setattr__(
                self, "native_existence", H1NativeExistenceV1(self.native_existence)
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ProductionLifecycleSourceCandidateV1Error(
                "lifecycle failure edge has an invalid enum"
            ) from error
        if self.outcome is H1LifecycleOutcomeV1.SUCCESS:
            _fail("SUCCESS is not a failure edge")
        if (
            type(self.current_site_admitted) is not bool
            or type(self.side_effect_may_have_started) is not bool
            or not _nonempty(
                self.provisional_primary_cause_class,
                "provisional primary cause class",
            )
            or not _nonempty(
                self.provisional_primary_cause_code,
                "provisional primary cause code",
            )
        ):
            _fail("lifecycle failure edge is malformed")
        if self.provisional_primary_cause_class not in {
            "CAP_EXHAUSTION",
            "PROTOCOL_FAILURE",
        }:
            _fail("H1 first-failure cause class is invalid")

    def to_document(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "current_site_admitted": self.current_site_admitted,
            "side_effect_may_have_started": self.side_effect_may_have_started,
            "native_existence": self.native_existence.value,
            "provisional_primary_cause_class": (
                self.provisional_primary_cause_class
            ),
            "provisional_primary_cause_code": self.provisional_primary_cause_code,
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
            "certificate_issued": False,
            "infeasibility_certified": False,
        }


@dataclass(frozen=True, slots=True)
class _SiteTemplateV1:
    site_key: str
    phase: str
    operation: H1LifecycleOperationV1
    resource_path: str | None
    owner_role: str
    intended_owner_method_string: str
    reservation_edge: bool
    ambiguity_role: str | None = None


@dataclass(frozen=True, slots=True)
class H1LifecycleTransitionV1:
    ordinal: int
    site_key: str
    phase: str
    operation: H1LifecycleOperationV1
    resource_path: str | None
    owner_role: str
    intended_owner_method_string: str
    from_state: str
    success_state: str
    reservation_edge: bool
    ambiguity_role: str | None
    failure_edges: tuple[H1FailureEdgeV1, ...]

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "operation", H1LifecycleOperationV1(self.operation))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ProductionLifecycleSourceCandidateV1Error(
                "lifecycle transition operation is invalid"
            ) from error
        if type(self.ordinal) is not int or self.ordinal <= 0:
            _fail("lifecycle ordinal must be a positive exact integer")
        for label, value in (
            ("site key", self.site_key),
            ("phase", self.phase),
            ("owner role", self.owner_role),
            ("intended owner method string", self.intended_owner_method_string),
            ("from state", self.from_state),
            ("success state", self.success_state),
        ):
            _nonempty(value, label)
        if self.resource_path is not None and self.resource_path not in SHARED_RESOURCE_PATHS:
            _fail("lifecycle transition names an unknown shared-resource path")
        if type(self.reservation_edge) is not bool:
            _fail("reservation-edge marker must be exact bool")
        if self.reservation_edge and self.resource_path is None:
            _fail("a reservation edge must name its shared-resource path")
        if (
            type(self.failure_edges) is not tuple
            or not self.failure_edges
            or any(type(edge) is not H1FailureEdgeV1 for edge in self.failure_edges)
            or len({edge.outcome for edge in self.failure_edges})
            != len(self.failure_edges)
        ):
            _fail("lifecycle failure edges must be nonempty and unique")
        ambiguous = any(
            edge.outcome
            is H1LifecycleOutcomeV1.NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION
            for edge in self.failure_edges
        )
        if ambiguous != (self.ambiguity_role is not None):
            _fail("native ambiguity edge and ambiguity role disagree")
        if self.ambiguity_role is not None and self.ambiguity_role not in {
            "MEMORY_HIERARCHY",
            "MOUNT",
            "WORKER",
            "BUSINESS",
        }:
            _fail("lifecycle ambiguity role is invalid")

    def to_document(self) -> dict[str, Any]:
        ambiguity: Any = (
            self.ambiguity_role
            if self.ambiguity_role is not None
            else {"kind": "NOT_APPLICABLE", "reason": "NO_NATIVE_AMBIGUITY_EDGE"}
        )
        return {
            "ordinal": self.ordinal,
            "site_key": self.site_key,
            "phase": self.phase,
            "operation": self.operation.value,
            "resource_path": (
                self.resource_path
                if self.resource_path is not None
                else {"kind": "NOT_APPLICABLE", "reason": "NO_SHARED_COST_LEAF"}
            ),
            "owner_role": self.owner_role,
            "intended_owner_method_string": self.intended_owner_method_string,
            "owner_method_semantic_identity_bound": False,
            "from_state": self.from_state,
            "success_state": self.success_state,
            "reservation_edge": self.reservation_edge,
            "ambiguity_role": ambiguity,
            "failure_edges": [edge.to_document() for edge in self.failure_edges],
        }


def _cap_edge() -> H1FailureEdgeV1:
    return H1FailureEdgeV1(
        H1LifecycleOutcomeV1.CAP_REJECTED_BEFORE_SIDE_EFFECT,
        False,
        False,
        H1NativeExistenceV1.KNOWN_NOT_STARTED,
        "CAP_EXHAUSTION",
        "SHARED_CAP_EXHAUSTED",
    )


def _callback_edge(*, admitted: bool = True) -> H1FailureEdgeV1:
    return H1FailureEdgeV1(
        H1LifecycleOutcomeV1.CALLBACK_FAILED_AFTER_ADMISSION,
        admitted,
        True,
        H1NativeExistenceV1.MAY_HAVE_STARTED,
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )


def _ambiguous_edge() -> H1FailureEdgeV1:
    return H1FailureEdgeV1(
        H1LifecycleOutcomeV1.NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION,
        True,
        True,
        H1NativeExistenceV1.AMBIGUOUS,
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )


def _overrun_edge(*, admitted: bool = True) -> H1FailureEdgeV1:
    return H1FailureEdgeV1(
        H1LifecycleOutcomeV1.OBSERVED_UPPER_BOUND_VIOLATION,
        admitted,
        True,
        H1NativeExistenceV1.NOT_APPLICABLE,
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )


def _cleanup_edge() -> H1FailureEdgeV1:
    return H1FailureEdgeV1(
        H1LifecycleOutcomeV1.CLEANUP_FAILED,
        False,
        True,
        H1NativeExistenceV1.MAY_HAVE_STARTED,
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )


def _protocol_edge() -> H1FailureEdgeV1:
    return H1FailureEdgeV1(
        H1LifecycleOutcomeV1.PROTOCOL_FAILED,
        False,
        False,
        H1NativeExistenceV1.NOT_APPLICABLE,
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )


def _failure_edges_for_v1(
    template: _SiteTemplateV1,
) -> tuple[H1FailureEdgeV1, ...]:
    operation = template.operation
    if operation in {
        H1LifecycleOperationV1.MEMORY_BIND,
        H1LifecycleOperationV1.MOUNT_OPEN,
        H1LifecycleOperationV1.LAUNCH_CHILD,
    }:
        return (_cap_edge(), _ambiguous_edge())
    if operation is H1LifecycleOperationV1.OUTPUT_RESERVE:
        return (_cap_edge(),)
    if operation in {
        H1LifecycleOperationV1.COMMON_HASH,
        H1LifecycleOperationV1.COMMON_INTEGRITY,
        H1LifecycleOperationV1.COMMON_PROTOCOL,
    }:
        return (_cap_edge(), _callback_edge())
    if operation in {
        H1LifecycleOperationV1.STAGE_INPUT,
        H1LifecycleOperationV1.READ_INPUT,
        H1LifecycleOperationV1.READ_BUSINESS_RESULT,
        H1LifecycleOperationV1.OUTPUT_ROLE_READBACK,
    }:
        return (_cap_edge(), _callback_edge(), _overrun_edge())
    if operation is H1LifecycleOperationV1.SAME_OFD_PEAK_READ:
        return (_callback_edge(admitted=False), _overrun_edge(admitted=False))
    if operation is H1LifecycleOperationV1.MOUNT_CLOSE:
        return (_cleanup_edge(),)
    if operation is H1LifecycleOperationV1.DESCENDANT_REAP:
        return (_protocol_edge(),)
    if operation is H1LifecycleOperationV1.OUTPUT_FINALIZE:
        return (
            _callback_edge(admitted=False),
            _overrun_edge(admitted=False),
            _protocol_edge(),
        )
    if operation is H1LifecycleOperationV1.OUTPUT_CLOSE:
        return (_protocol_edge(),)
    _fail("lifecycle operation lacks a failure-edge declaration")


def _semantic_site_templates_v1() -> tuple[_SiteTemplateV1, ...]:
    """Return the single ordered lifecycle source used by replay and analysis."""

    topology = topology_v1.official_h1_execution_topology_profile_v1()
    rows: list[_SiteTemplateV1] = [
        _SiteTemplateV1(
            "memory:bind-working-hierarchy",
            "PRELAUNCH_RESERVATION",
            H1LifecycleOperationV1.MEMORY_BIND,
            "memory.working_bytes_peak",
            "BROKER",
            "H1SharedCapOwnerV2.bind_working_hierarchy",
            True,
            "MEMORY_HIERARCHY",
        ),
        _SiteTemplateV1(
            "common:preflight-hash",
            "PRELAUNCH_AUDIT",
            H1LifecycleOperationV1.COMMON_HASH,
            "common.hash_invocations",
            "BROKER",
            "H1SharedCapOwnerV2.record_hash_invocation",
            True,
        ),
        _SiteTemplateV1(
            "common:preflight-integrity",
            "PRELAUNCH_AUDIT",
            H1LifecycleOperationV1.COMMON_INTEGRITY,
            "common.integrity_checks",
            "BROKER",
            "H1SharedCapOwnerV2.record_integrity_check",
            True,
        ),
        _SiteTemplateV1(
            "common:preflight-protocol",
            "PRELAUNCH_AUDIT",
            H1LifecycleOperationV1.COMMON_PROTOCOL,
            "common.protocol_checks",
            "BROKER",
            "H1SharedCapOwnerV2.record_protocol_check",
            True,
        ),
        _SiteTemplateV1(
            "output:reserve-route-wide",
            "PRELAUNCH_RESERVATION",
            H1LifecycleOperationV1.OUTPUT_RESERVE,
            "io.output_bytes",
            "BROKER",
            "H1SharedCapOwnerV2.begin_route_output",
            True,
        ),
    ]
    for grant in topology.sealed_inputs:
        role = grant.role.value
        target = f"{role}:{grant.input_role}"
        rows.append(
            _SiteTemplateV1(
                f"stage:{target}",
                "PRELAUNCH_INPUT_ADMISSION",
                H1LifecycleOperationV1.STAGE_INPUT,
                "io.staged_bytes",
                "BROKER",
                "H1SharedCapOwnerV2.stage_registered_payload",
                True,
            )
        )
        rows.append(
            _SiteTemplateV1(
                f"mount-open:{target}",
                "PRELAUNCH_INPUT_ADMISSION",
                H1LifecycleOperationV1.MOUNT_OPEN,
                "io.mounted_bytes_peak",
                "BROKER",
                "H1SharedCapOwnerV2.open_mounted_payload",
                True,
                "MOUNT",
            )
        )
    rows.append(
        _SiteTemplateV1(
            "launch:WORKER",
            "CHILD_LAUNCH",
            H1LifecycleOperationV1.LAUNCH_CHILD,
            "process.launches",
            "BROKER",
            "H1SharedCapOwnerV2.launch_registered_role",
            True,
            "WORKER",
        )
    )
    for grant in topology.sealed_inputs:
        if grant.role.value == "WORKER":
            rows.append(
                _SiteTemplateV1(
                    f"read:WORKER:{grant.input_role}",
                    "WORKER_INPUT_REPLAY",
                    H1LifecycleOperationV1.READ_INPUT,
                    "io.read_bytes",
                    "WORKER",
                    "H1SharedCapOwnerV2.read_registered_payload",
                    True,
                )
            )
    rows.append(
        _SiteTemplateV1(
            "launch:BUSINESS",
            "CHILD_LAUNCH",
            H1LifecycleOperationV1.LAUNCH_CHILD,
            "process.launches",
            "BROKER",
            "H1SharedCapOwnerV2.launch_registered_role",
            True,
            "BUSINESS",
        )
    )
    for grant in topology.sealed_inputs:
        if grant.role.value == "BUSINESS":
            rows.append(
                _SiteTemplateV1(
                    f"read:BUSINESS:{grant.input_role}",
                    "BUSINESS_INPUT_REPLAY",
                    H1LifecycleOperationV1.READ_INPUT,
                    "io.read_bytes",
                    "BUSINESS",
                    "H1SharedCapOwnerV2.read_registered_payload",
                    True,
                )
            )
    for role in ("BUSINESS", "BROKER", "WORKER"):
        rows.append(
            _SiteTemplateV1(
                f"read:business-result:{role}",
                "BUSINESS_RESULT_HANDOFF",
                H1LifecycleOperationV1.READ_BUSINESS_RESULT,
                "io.read_bytes",
                role,
                "H1SharedCapOwnerV2.read_registered_payload",
                True,
            )
        )
    rows.extend(
        (
            _SiteTemplateV1(
                "process:reap-known-descendants",
                "POST_CHILD_CLEANUP",
                H1LifecycleOperationV1.DESCENDANT_REAP,
                None,
                "BROKER",
                "H1SharedCapOwnerV2.mark_trusted_descendants_reaped",
                False,
            ),
            _SiteTemplateV1(
                "memory:read-retained-same-ofd-peak",
                "POST_CHILD_CLEANUP",
                H1LifecycleOperationV1.SAME_OFD_PEAK_READ,
                "memory.working_bytes_peak",
                "BROKER",
                "H1SharedCapOwnerV2.read_working_bytes_peak",
                False,
            ),
        )
    )
    for grant in reversed(topology.sealed_inputs):
        role = grant.role.value
        target = f"{role}:{grant.input_role}"
        rows.append(
            _SiteTemplateV1(
                f"mount-close:{target}",
                "POST_CHILD_CLEANUP",
                H1LifecycleOperationV1.MOUNT_CLOSE,
                "io.mounted_bytes_peak",
                "BROKER",
                "H1SharedCapOwnerV2.close_mounted_payload",
                False,
            )
        )
    for role in output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES:
        rows.append(
            _SiteTemplateV1(
                f"readback:output-role:{role}",
                "OUTPUT_SERIALIZATION",
                H1LifecycleOperationV1.OUTPUT_ROLE_READBACK,
                "io.read_bytes",
                "BROKER",
                "H1SharedCapOwnerV2.read_registered_payload",
                True,
            )
        )
    rows.extend(
        (
            _SiteTemplateV1(
                "output:finalize-route-wide",
                "OUTPUT_FINALIZATION",
                H1LifecycleOperationV1.OUTPUT_FINALIZE,
                "io.output_bytes",
                "BROKER",
                "H1SharedCapOwnerV2.finalize_route_output",
                False,
            ),
            _SiteTemplateV1(
                "output:close-owner",
                "OUTPUT_FINALIZATION",
                H1LifecycleOperationV1.OUTPUT_CLOSE,
                None,
                "BROKER",
                "H1SharedCapOwnerV2.close",
                False,
            ),
        )
    )
    result = tuple(rows)
    if len({row.site_key for row in result}) != len(result):
        _fail("declarative lifecycle contains a duplicate site key")
    return result


def _compile_lifecycle_transitions_v1() -> tuple[H1LifecycleTransitionV1, ...]:
    """Compile source templates into a deterministic linear state machine."""

    rows: list[H1LifecycleTransitionV1] = []
    state = "STATE_INITIAL"
    for ordinal, template in enumerate(_semantic_site_templates_v1(), start=1):
        next_state = f"STATE_AFTER_{template.site_key}"
        rows.append(
            H1LifecycleTransitionV1(
                ordinal,
                template.site_key,
                template.phase,
                template.operation,
                template.resource_path,
                template.owner_role,
                template.intended_owner_method_string,
                state,
                next_state,
                template.reservation_edge,
                template.ambiguity_role,
                _failure_edges_for_v1(template),
            )
        )
        state = next_state
    return tuple(rows)


def _output_role_presence_sets_v1() -> tuple[tuple[str, ...], ...]:
    """Return the distinct serializer-template role sets in source order."""

    dag = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
    rows: list[tuple[str, ...]] = []
    for leaf in dag.leaves:
        if leaf.present_roles not in rows:
            rows.append(leaf.present_roles)
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class H1SourceSpanV1:
    symbol: str
    start_line: int
    end_line: int
    source_byte_count: int
    source_sha256: str

    def to_document(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "source_byte_count": self.source_byte_count,
            "source_sha256": self.source_sha256,
        }


def _source_fingerprint_payload_v1(source_bytes: bytes) -> dict[str, Any]:
    if type(source_bytes) is not bytes or not source_bytes:
        _fail("lifecycle module source must be nonempty exact bytes")
    try:
        text = source_bytes.decode("utf-8", errors="strict")
        tree = ast.parse(text, filename="construction_k7_h1_production_lifecycle_source_candidate_v1.py")
    except (UnicodeDecodeError, SyntaxError) as error:
        raise ConstructionK7H1ProductionLifecycleSourceCandidateV1Error(
            "lifecycle module source is not valid UTF-8 Python"
        ) from error
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    lines = source_bytes.splitlines(keepends=True)
    spans: list[H1SourceSpanV1] = []
    for symbol in SOURCE_BOUND_SYMBOLS:
        node = functions.get(symbol)
        if node is None or node.end_lineno is None:
            _fail(f"source-bound lifecycle symbol is missing: {symbol}")
        source_slice = b"".join(lines[node.lineno - 1 : node.end_lineno])
        spans.append(
            H1SourceSpanV1(
                symbol,
                node.lineno,
                node.end_lineno,
                len(source_slice),
                hashlib.sha256(source_slice).hexdigest(),
            )
        )
    return {
        "schema": "acfqp.h1_production_lifecycle_source_manifest.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "module": "acfqp.construction_k7_h1_production_lifecycle_source_candidate_v1",
        "repository_relative_path": (
            "src/acfqp/construction_k7_h1_production_lifecycle_source_candidate_v1.py"
        ),
        "whole_source_byte_count": len(source_bytes),
        "whole_source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "normalized_ast_sha256": hashlib.sha256(
            ast.dump(tree, annotate_fields=True, include_attributes=False).encode("utf-8")
        ).hexdigest(),
        "source_spans": [span.to_document() for span in spans],
        "source_bound_symbols": list(SOURCE_BOUND_SYMBOLS),
        "complete_module_bytes_bound": True,
        "normalized_ast_bound": True,
        "exact_function_source_spans_bound": True,
    }


def derive_h1_production_lifecycle_source_manifest_id_v1(
    source_bytes: bytes,
) -> str:
    """Derive the source-manifest ID for exact bytes without blessing them."""

    return content_id(SOURCE_MANIFEST_DOMAIN, _source_fingerprint_payload_v1(source_bytes))


_SOURCE_ISSUER = object()
_PROGRAM_ISSUER = object()
_ANALYSIS_ISSUER = object()
_CANDIDATE_ISSUER = object()
_REPLAY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1ProductionLifecycleSourceManifestV1:
    _issuer: InitVar[object]
    payload_bytes: bytes = field(repr=False)
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_ISSUER or type(self.payload_bytes) is not bytes:
            _fail("lifecycle source manifest is caller-minted")
        try:
            payload = loads_canonical_json(self.payload_bytes)
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ProductionLifecycleSourceCandidateV1Error(
                "lifecycle source manifest payload is not canonical"
            ) from error
        if type(payload) is not dict:
            _fail("lifecycle source manifest payload must be one object")
        _reject_future_fields(payload)
        object.__setattr__(
            self,
            "_manifest_id",
            content_id(SOURCE_MANIFEST_DOMAIN, payload),
        )

    @property
    def payload(self) -> dict[str, Any]:
        payload = loads_canonical_json(self.payload_bytes)
        if type(payload) is not dict:  # pragma: no cover - construction invariant
            _fail("lifecycle source manifest payload changed type")
        return payload

    @property
    def manifest_id(self) -> str:
        return self._manifest_id

    def to_document(self) -> dict[str, Any]:
        return {
            **dict(self.payload),
            "h1_production_lifecycle_source_manifest_id": self.manifest_id,
        }


@dataclass(frozen=True, slots=True)
class H1ProductionLifecycleProgramV1:
    _issuer: InitVar[object]
    source_manifest_id: str
    execution_topology_profile_id: str
    output_branch_dag_id: str
    transitions: tuple[H1LifecycleTransitionV1, ...]
    _program_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        topology = topology_v1.official_h1_execution_topology_profile_v1()
        output = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
        if (
            _issuer is not _PROGRAM_ISSUER
            or self.source_manifest_id != _OFFICIAL_SOURCE_MANIFEST.manifest_id
            or self.execution_topology_profile_id != topology.profile_id
            or self.output_branch_dag_id != output.dag_id
            or self.transitions != _compile_lifecycle_transitions_v1()
        ):
            _fail("declarative lifecycle program is caller-minted or changed")
        if (
            tuple(row.ordinal for row in self.transitions)
            != tuple(range(1, len(self.transitions) + 1))
            or len({row.site_key for row in self.transitions}) != len(self.transitions)
            or self.transitions[0].operation is not H1LifecycleOperationV1.MEMORY_BIND
            or self.transitions[-1].operation is not H1LifecycleOperationV1.OUTPUT_CLOSE
            or any(
                current.success_state != following.from_state
                for current, following in zip(self.transitions, self.transitions[1:])
            )
        ):
            _fail("declarative lifecycle state chain is incomplete")
        paths = {row.resource_path for row in self.transitions if row.resource_path}
        if paths != set(SHARED_RESOURCE_PATHS):
            _fail("declarative lifecycle does not cover exactly the nine shared paths")
        role_sets = _output_role_presence_sets_v1()
        if (
            len(role_sets) <= 1
            or tuple(output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES) not in role_sets
        ):
            _fail("serializer-template role-presence universe changed unexpectedly")
        object.__setattr__(self, "_program_id", content_id(PROGRAM_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_production_lifecycle_program.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_production_lifecycle_source_manifest_id": self.source_manifest_id,
            "h1_execution_topology_profile_id": self.execution_topology_profile_id,
            "h1_production_output_branch_dag_id": self.output_branch_dag_id,
            "shared_resource_paths": list(SHARED_RESOURCE_PATHS),
            "transition_count": len(self.transitions),
            "transitions": [row.to_document() for row in self.transitions],
            "single_table_drives_replay_and_failure_analysis": True,
            "shared_path_partition_scope": "DECLARATIVE_CANDIDATE_TABLE_ONLY",
            "candidate_table_partition_totality_present": True,
            "production_shared_path_partition_authority_present": False,
            "common_multiplicity_source_bound": False,
            "memory_binding_is_first": True,
            "output_reservation_precedes_first_launch": True,
            "all_mount_opens_precede_first_launch": True,
            "all_mount_closes_follow_descendant_reap": True,
            "mount_admission_universe": "SEALED_INPUT_TARGETS_ONLY",
            "created_output_roles_are_not_mounted_payload_admissions": True,
            "same_ofd_peak_read_follows_descendant_reap": True,
            "output_finalize_follows_mount_cleanup": True,
            "worker_then_business_launch_order": True,
            "worker_and_business_ambiguity_edges_present_in_candidate": True,
            "intended_owner_methods_are_strings_only": True,
            "shared_cap_owner_semantic_identity_bound": False,
            "owner_order_compatibility_claimed": False,
            "output_dag_role_presence_sets": [
                list(row) for row in _output_role_presence_sets_v1()
            ],
            "output_dag_role_presence_set_count": len(
                _output_role_presence_sets_v1()
            ),
            "linear_output_readback_roles": list(
                output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES
            ),
            "linear_all_roles_matches_every_output_dag_leaf": False,
            "output_dag_leaf_join_bound": False,
            "output_read_lifecycle_complete": False,
            "numeric_ceiling_declared": False,
            "numeric_operand_issued": False,
            "live_runtime_integration_present": False,
            "production_execution_authority_present": False,
        }

    @property
    def program_id(self) -> str:
        if content_id(PROGRAM_DOMAIN, self._payload()) != self._program_id:
            _fail("declarative lifecycle program changed")
        return self._program_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_production_lifecycle_program_id": self.program_id}

    @property
    def by_site(self) -> dict[str, H1LifecycleTransitionV1]:
        return {row.site_key: row for row in self.transitions}


@dataclass(frozen=True, slots=True)
class H1ResourcePrefixV1:
    path: str
    attempted_site_prefix: tuple[str, ...]
    admitted_site_prefix: tuple[str, ...]
    completed_site_prefix: tuple[str, ...]
    unreached_site_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.path not in SHARED_RESOURCE_PATHS:
            _fail("resource prefix names an unknown shared path")
        for label, value in (
            ("attempted prefix", self.attempted_site_prefix),
            ("admitted prefix", self.admitted_site_prefix),
            ("completed prefix", self.completed_site_prefix),
            ("unreached keys", self.unreached_site_keys),
        ):
            _unique_strings(value, label, allow_empty=True)
        if not set(self.completed_site_prefix) <= set(self.attempted_site_prefix):
            _fail("completed resource prefix is not attempted")
        if not set(self.admitted_site_prefix) <= set(self.attempted_site_prefix):
            _fail("admitted resource prefix is not attempted")
        if set(self.attempted_site_prefix) & set(self.unreached_site_keys):
            _fail("a resource site cannot be attempted and unreached")

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "attempted_site_prefix": list(self.attempted_site_prefix),
            "admitted_site_prefix": list(self.admitted_site_prefix),
            "completed_site_prefix": list(self.completed_site_prefix),
            "unreached_site_keys": list(self.unreached_site_keys),
            "partition_scope": "DECLARATIVE_CANDIDATE_TABLE_ONLY",
            "production_source_multiplicity_bound": False,
            "missing_as_zero_allowed": False,
            "wildcard_allowed": False,
        }


@dataclass(frozen=True, slots=True)
class H1LifecycleBranchV1:
    branch_key: str
    first_failure_outcome: H1LifecycleOutcomeV1 | None
    failed_site_key: str | None
    failed_edge: H1FailureEdgeV1 | None
    successful_site_prefix: tuple[str, ...]
    attempted_site_prefix: tuple[str, ...]
    resource_prefixes: tuple[H1ResourcePrefixV1, ...]

    def __post_init__(self) -> None:
        _nonempty(self.branch_key, "lifecycle branch key")
        if self.first_failure_outcome is not None:
            try:
                object.__setattr__(
                    self,
                    "first_failure_outcome",
                    H1LifecycleOutcomeV1(self.first_failure_outcome),
                )
            except (TypeError, ValueError) as error:
                raise ConstructionK7H1ProductionLifecycleSourceCandidateV1Error(
                    "lifecycle first-failure outcome is invalid"
                ) from error
            if self.first_failure_outcome is H1LifecycleOutcomeV1.SUCCESS:
                _fail("SUCCESS cannot be a first-failure outcome")
        _unique_strings(
            self.successful_site_prefix, "successful site prefix", allow_empty=True
        )
        _unique_strings(
            self.attempted_site_prefix, "attempted site prefix", allow_empty=True
        )
        if (
            type(self.resource_prefixes) is not tuple
            or tuple(row.path for row in self.resource_prefixes)
            != SHARED_RESOURCE_PATHS
            or any(type(row) is not H1ResourcePrefixV1 for row in self.resource_prefixes)
        ):
            _fail("lifecycle branch lacks the exact nine resource prefixes")
        success = self.first_failure_outcome is None
        if success:
            if (
                self.failed_site_key is not None
                or self.failed_edge is not None
                or self.successful_site_prefix != self.attempted_site_prefix
            ):
                _fail("full-success branch contains a failure edge")
        elif (
            self.failed_site_key is None
            or type(self.failed_edge) is not H1FailureEdgeV1
            or self.failed_edge.outcome is not self.first_failure_outcome
            or not self.attempted_site_prefix
            or self.attempted_site_prefix[-1] != self.failed_site_key
            or self.successful_site_prefix != self.attempted_site_prefix[:-1]
        ):
            _fail("failure branch is not one exact first-failure prefix")

    def to_document(self) -> dict[str, Any]:
        failed_site: Any = (
            self.failed_site_key
            if self.failed_site_key is not None
            else {"kind": "NOT_APPLICABLE", "reason": "FULL_SUCCESS"}
        )
        failed_edge: Any = (
            self.failed_edge.to_document()
            if self.failed_edge is not None
            else {"kind": "NOT_APPLICABLE", "reason": "FULL_SUCCESS"}
        )
        return {
            "branch_key": self.branch_key,
            "branch_kind": (
                "FULL_SUCCESS"
                if self.first_failure_outcome is None
                else "FIRST_FAILURE_PREFIX"
            ),
            "first_failure_outcome": (
                self.first_failure_outcome.value
                if self.first_failure_outcome is not None
                else {"kind": "NOT_APPLICABLE", "reason": "FULL_SUCCESS"}
            ),
            "failed_site_key": failed_site,
            "failed_edge": failed_edge,
            "successful_site_prefix": list(self.successful_site_prefix),
            "attempted_site_prefix": list(self.attempted_site_prefix),
            "resource_prefixes": [row.to_document() for row in self.resource_prefixes],
            "prefix_derived_from_transition_table": True,
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
        }


def _resource_prefixes_v1(
    transitions: tuple[H1LifecycleTransitionV1, ...],
    completed: tuple[H1LifecycleTransitionV1, ...],
    current: H1LifecycleTransitionV1 | None,
    edge: H1FailureEdgeV1 | None,
) -> tuple[H1ResourcePrefixV1, ...]:
    completed_keys = {row.site_key for row in completed}
    attempted_keys = set(completed_keys)
    if current is not None:
        attempted_keys.add(current.site_key)
    admitted_keys = {
        row.site_key for row in completed if row.reservation_edge
    }
    if current is not None and edge is not None and edge.current_site_admitted:
        admitted_keys.add(current.site_key)
    rows: list[H1ResourcePrefixV1] = []
    for path in SHARED_RESOURCE_PATHS:
        universe = tuple(row.site_key for row in transitions if row.resource_path == path)
        rows.append(
            H1ResourcePrefixV1(
                path,
                tuple(key for key in universe if key in attempted_keys),
                tuple(key for key in universe if key in admitted_keys),
                tuple(key for key in universe if key in completed_keys),
                tuple(key for key in universe if key not in attempted_keys),
            )
        )
    return tuple(rows)


def _analyze_failure_prefixes_v1(
    program: H1ProductionLifecycleProgramV1,
) -> tuple[H1LifecycleBranchV1, ...]:
    """Enumerate every first failure edge plus the all-success branch."""

    if type(program) is not H1ProductionLifecycleProgramV1:
        _fail("failure-prefix analysis requires the exact lifecycle program")
    transitions = program.transitions
    branches: list[H1LifecycleBranchV1] = []
    for index, transition in enumerate(transitions):
        completed = transitions[:index]
        successful_keys = tuple(row.site_key for row in completed)
        for edge in transition.failure_edges:
            branches.append(
                H1LifecycleBranchV1(
                    f"FAIL:{transition.site_key}:{edge.outcome.value}",
                    edge.outcome,
                    transition.site_key,
                    edge,
                    successful_keys,
                    (*successful_keys, transition.site_key),
                    _resource_prefixes_v1(
                        transitions, completed, transition, edge
                    ),
                )
            )
    all_keys = tuple(row.site_key for row in transitions)
    branches.append(
        H1LifecycleBranchV1(
            "SUCCESS:COMPLETE_LIFECYCLE",
            None,
            None,
            None,
            all_keys,
            all_keys,
            _resource_prefixes_v1(transitions, transitions, None, None),
        )
    )
    if len({row.branch_key for row in branches}) != len(branches):
        _fail("failure-prefix analysis produced duplicate branches")
    return tuple(branches)


@dataclass(frozen=True, slots=True)
class H1LifecycleBranchAnalysisV1:
    _issuer: InitVar[object]
    program_id: str
    branches: tuple[H1LifecycleBranchV1, ...]
    _analysis_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ANALYSIS_ISSUER
            or self.program_id != _OFFICIAL_PROGRAM.program_id
            or self.branches != _analyze_failure_prefixes_v1(_OFFICIAL_PROGRAM)
        ):
            _fail("lifecycle branch analysis is caller-minted or incomplete")
        expected_count = 1 + sum(
            len(row.failure_edges) for row in _OFFICIAL_PROGRAM.transitions
        )
        if len(self.branches) != expected_count:
            _fail("lifecycle branch count is not derived from failure edges")
        object.__setattr__(
            self, "_analysis_id", content_id(BRANCH_ANALYSIS_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_production_lifecycle_branch_analysis.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_production_lifecycle_program_id": self.program_id,
            "branch_count": len(self.branches),
            "branch_count_formula": "ONE_PLUS_SUM_FAILURE_EDGES_OVER_TRANSITIONS",
            "branches": [row.to_document() for row in self.branches],
            "first_failure_prefixes_complete_for_declared_candidate_edges": True,
            "production_failure_edge_completeness_claimed": False,
            "shared_path_partitions_relative_to_candidate_table_only": True,
            "post_failure_cleanup_continuation_program_bound": False,
            "complete_attempt_branches_issued": False,
            "live_runtime_branch_completeness_claimed": False,
        }

    @property
    def analysis_id(self) -> str:
        if content_id(BRANCH_ANALYSIS_DOMAIN, self._payload()) != self._analysis_id:
            _fail("lifecycle branch analysis changed")
        return self._analysis_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_production_lifecycle_branch_analysis_id": self.analysis_id,
        }

    @property
    def by_key(self) -> dict[str, H1LifecycleBranchV1]:
        return {row.branch_key: row for row in self.branches}


@dataclass(frozen=True, slots=True)
class H1LifecycleEventV1:
    site_key: str
    outcome: H1LifecycleOutcomeV1

    def __post_init__(self) -> None:
        _nonempty(self.site_key, "lifecycle event site")
        try:
            object.__setattr__(self, "outcome", H1LifecycleOutcomeV1(self.outcome))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1ProductionLifecycleSourceCandidateV1Error(
                "lifecycle replay outcome is invalid"
            ) from error


@dataclass(frozen=True, slots=True)
class H1LifecycleReplayV1:
    _issuer: InitVar[object]
    program_id: str
    consumed_events: tuple[H1LifecycleEventV1, ...]
    successful_site_prefix: tuple[str, ...]
    first_failure_outcome: H1LifecycleOutcomeV1 | None
    full_success_reached: bool
    next_site_key: str | None
    _replay_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPLAY_ISSUER:
            _fail("lifecycle replay result is caller-minted")
        if (
            self.program_id != _OFFICIAL_PROGRAM.program_id
            or type(self.consumed_events) is not tuple
            or any(type(row) is not H1LifecycleEventV1 for row in self.consumed_events)
        ):
            _fail("lifecycle replay result crossed its program or event schema")
        _unique_strings(
            self.successful_site_prefix,
            "replay successful site prefix",
            allow_empty=True,
        )
        if self.first_failure_outcome is not None:
            try:
                object.__setattr__(
                    self,
                    "first_failure_outcome",
                    H1LifecycleOutcomeV1(self.first_failure_outcome),
                )
            except (TypeError, ValueError) as error:
                raise ConstructionK7H1ProductionLifecycleSourceCandidateV1Error(
                    "lifecycle replay first-failure outcome is invalid"
                ) from error
            if self.first_failure_outcome is H1LifecycleOutcomeV1.SUCCESS:
                _fail("SUCCESS cannot be a replay first-failure outcome")
        if type(self.full_success_reached) is not bool:
            _fail("lifecycle replay full-success marker must be exact bool")
        if self.full_success_reached and (
            self.first_failure_outcome is not None or self.next_site_key is not None
        ):
            _fail("full-success replay cannot contain failure or next-site state")
        if self.first_failure_outcome is not None and self.next_site_key is not None:
            _fail("first-failure replay cannot authorize a next normal site")
        if (
            self.first_failure_outcome is None
            and not self.full_success_reached
            and self.next_site_key is None
        ):
            _fail("nonterminal replay prefix must expose its next candidate site")
        if self.next_site_key is not None:
            _nonempty(self.next_site_key, "replay next candidate site")
        object.__setattr__(self, "_replay_id", content_id(REPLAY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_production_lifecycle_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_production_lifecycle_program_id": self.program_id,
            "consumed_events": [
                {"site_key": row.site_key, "outcome": row.outcome.value}
                for row in self.consumed_events
            ],
            "successful_site_prefix": list(self.successful_site_prefix),
            "first_failure_outcome": (
                self.first_failure_outcome.value
                if self.first_failure_outcome is not None
                else {"kind": "NOT_APPLICABLE", "reason": "NO_FAILURE_OBSERVED"}
            ),
            "full_success_reached": self.full_success_reached,
            "next_site_key": (
                self.next_site_key
                if self.next_site_key is not None
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "NO_NEXT_NORMAL_CANDIDATE_SITE",
                }
            ),
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
        }

    @property
    def replay_id(self) -> str:
        return self._replay_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_production_lifecycle_replay_id": self.replay_id}


def replay_h1_production_lifecycle_events_v1(
    events: tuple[H1LifecycleEventV1, ...],
    *,
    program: H1ProductionLifecycleProgramV1 | None = None,
) -> H1LifecycleReplayV1:
    """Replay a candidate-table prefix against the analyser's same table."""

    selected = _OFFICIAL_PROGRAM if program is None else program
    if selected is not _OFFICIAL_PROGRAM:
        _fail("lifecycle replay accepts only the issuer-retained program candidate")
    if type(events) is not tuple or any(
        type(event) is not H1LifecycleEventV1 for event in events
    ):
        _fail("lifecycle replay requires one exact event tuple")
    successful: list[str] = []
    first_failure: H1LifecycleOutcomeV1 | None = None
    for index, event in enumerate(events):
        if first_failure is not None:
            _fail("normal lifecycle replay cannot continue after a first failure")
        if index >= len(selected.transitions):
            _fail("lifecycle replay contains events after full success")
        transition = selected.transitions[index]
        if event.site_key != transition.site_key:
            _fail("lifecycle replay skipped, reordered, or invented a site")
        if event.outcome is H1LifecycleOutcomeV1.SUCCESS:
            successful.append(event.site_key)
            continue
        if event.outcome not in {edge.outcome for edge in transition.failure_edges}:
            _fail("lifecycle replay used an outcome absent from the transition edge")
        first_failure = event.outcome
    full_success = first_failure is None and len(events) == len(selected.transitions)
    if first_failure is not None or full_success:
        next_site = None
    else:
        next_site = selected.transitions[len(events)].site_key
    return H1LifecycleReplayV1(
        _REPLAY_ISSUER,
        selected.program_id,
        events,
        tuple(successful),
        first_failure,
        full_success,
        next_site,
    )


@dataclass(frozen=True, slots=True)
class H1ProductionLifecycleSourceCandidateV1:
    _issuer: InitVar[object]
    source_manifest: H1ProductionLifecycleSourceManifestV1
    program: H1ProductionLifecycleProgramV1
    branch_analysis: H1LifecycleBranchAnalysisV1
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CANDIDATE_ISSUER
            or self.source_manifest is not _OFFICIAL_SOURCE_MANIFEST
            or self.program is not _OFFICIAL_PROGRAM
            or self.branch_analysis is not _OFFICIAL_BRANCH_ANALYSIS
        ):
            _fail("lifecycle source candidate is caller-minted")
        object.__setattr__(
            self, "_candidate_id", content_id(SOURCE_CANDIDATE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_production_lifecycle_source_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_production_lifecycle_source_manifest": self.source_manifest.to_document(),
            "h1_production_lifecycle_program": self.program.to_document(),
            "h1_production_lifecycle_branch_analysis": (
                self.branch_analysis.to_document()
            ),
            "declarative_lifecycle_source_authority_present": False,
            "declarative_lifecycle_candidate_present": True,
            "first_failure_prefixes_complete_for_declared_candidate_edges": True,
            "production_failure_edge_completeness_claimed": False,
            "post_failure_cleanup_continuation_program_bound": False,
            "complete_attempt_branches_issued": False,
            "exact_module_source_bytes_bound": True,
            "exact_ast_and_function_spans_bound": True,
            "source_content_identity_present": True,
            "external_preregistration_anchor_present": False,
            "fresh_import_can_self_mint_new_candidate_identity": True,
            "live_runtime_integration_present": False,
            "production_execution_authority_present": False,
            "common_multiplicity_source_bound": False,
            "shared_cap_owner_semantic_identity_bound": False,
            "owner_order_compatibility_claimed": False,
            "output_dag_leaf_join_bound": False,
            "output_read_lifecycle_complete": False,
            "fallback_cap_exhausted_route_stage_binding_bound": False,
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
            "typed_production_blockers": list(TYPED_PRODUCTION_BLOCKERS),
            "numeric_ceiling_declared": False,
            "numeric_shared_operand_issued": False,
            "formal_v7_route_authority_present": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
        }

    @property
    def candidate_id(self) -> str:
        if content_id(SOURCE_CANDIDATE_DOMAIN, self._payload()) != self._candidate_id:
            _fail("lifecycle source candidate changed")
        return self._candidate_id

    @property
    def authority_id(self) -> str:
        """Deprecated unsafe alias; this profile issues no source authority."""

        _fail(
            "deprecated lifecycle authority_id is unavailable: use candidate_id"
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_production_lifecycle_source_candidate_id": self.candidate_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _current_module_source_bytes_v1() -> bytes:
    return Path(__file__).resolve().read_bytes()


def _verify_current_source_manifest_v1() -> None:
    current = _source_fingerprint_payload_v1(_current_module_source_bytes_v1())
    if not hmac.compare_digest(
        canonical_json_bytes(current), canonical_json_bytes(_OFFICIAL_SOURCE_MANIFEST.payload)
    ):
        _fail("lifecycle module source bytes changed after candidate construction")


def verify_h1_production_lifecycle_source_candidate_bytes_v1(
    data: bytes,
) -> H1ProductionLifecycleSourceCandidateV1:
    """Parse and compare a candidate against the currently loaded source."""

    if type(data) is not bytes:
        _fail("lifecycle source candidate verification requires exact bytes")
    try:
        document = loads_canonical_json(data)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1ProductionLifecycleSourceCandidateV1Error(
            "lifecycle source candidate bytes are not canonical JSON"
        ) from error
    if type(document) is not dict:
        _fail("lifecycle source candidate document must be one object")
    _reject_future_fields(document)
    _verify_current_source_manifest_v1()
    expected = _REGISTERED_SOURCE_CANDIDATE.to_document()
    if document != expected or not hmac.compare_digest(
        canonical_json_bytes(document), _REGISTERED_SOURCE_CANDIDATE.canonical_bytes
    ):
        _fail(
            "lifecycle source candidate differs from the current "
            "source-derived candidate"
        )
    return _REGISTERED_SOURCE_CANDIDATE


_OFFICIAL_SOURCE_MANIFEST = H1ProductionLifecycleSourceManifestV1(
    _SOURCE_ISSUER,
    canonical_json_bytes(
        _source_fingerprint_payload_v1(_current_module_source_bytes_v1())
    ),
)
_OFFICIAL_PROGRAM = H1ProductionLifecycleProgramV1(
    _PROGRAM_ISSUER,
    _OFFICIAL_SOURCE_MANIFEST.manifest_id,
    topology_v1.official_h1_execution_topology_profile_v1().profile_id,
    output_v1.registered_h1_production_output_branch_dag_candidate_v1().dag_id,
    _compile_lifecycle_transitions_v1(),
)
_OFFICIAL_BRANCH_ANALYSIS = H1LifecycleBranchAnalysisV1(
    _ANALYSIS_ISSUER,
    _OFFICIAL_PROGRAM.program_id,
    _analyze_failure_prefixes_v1(_OFFICIAL_PROGRAM),
)
_REGISTERED_SOURCE_CANDIDATE = H1ProductionLifecycleSourceCandidateV1(
    _CANDIDATE_ISSUER,
    _OFFICIAL_SOURCE_MANIFEST,
    _OFFICIAL_PROGRAM,
    _OFFICIAL_BRANCH_ANALYSIS,
)


def registered_h1_production_lifecycle_source_candidate_v1(
) -> H1ProductionLifecycleSourceCandidateV1:
    _verify_current_source_manifest_v1()
    return _REGISTERED_SOURCE_CANDIDATE


def registered_h1_production_lifecycle_program_candidate_v1(
) -> H1ProductionLifecycleProgramV1:
    _verify_current_source_manifest_v1()
    return _OFFICIAL_PROGRAM


def registered_h1_production_lifecycle_branch_analysis_candidate_v1(
) -> H1LifecycleBranchAnalysisV1:
    _verify_current_source_manifest_v1()
    return _OFFICIAL_BRANCH_ANALYSIS


class H1ProductionLifecycleSourceAuthorityV1:
    """Unavailable compatibility role; this contract issues no authority."""

    def __new__(cls, *args: Any, **kwargs: Any) -> NoReturn:
        del args, kwargs
        _fail(
            "production lifecycle source authority is unavailable; "
            "use the explicitly nonauthorizing candidate API"
        )

    @property
    def authority_id(self) -> NoReturn:
        _fail("production lifecycle source authority_id is unavailable")


def official_h1_production_lifecycle_source_authority_v1(
) -> NoReturn:
    """Fail closed: the registered object is only an unanchored candidate."""

    _fail("production lifecycle source authority is unavailable in this contract")


def official_h1_production_lifecycle_program_v1() -> NoReturn:
    """Fail closed: use the candidate-specific program accessor."""

    _fail("official lifecycle program authority is unavailable in this contract")


def official_h1_production_lifecycle_branch_analysis_v1(
) -> NoReturn:
    """Fail closed: use the candidate-specific analysis accessor."""

    _fail("official lifecycle branch-analysis authority is unavailable")


def verify_h1_production_lifecycle_source_authority_bytes_v1(
    data: bytes,
) -> NoReturn:
    """Fail closed: candidate bytes cannot be verified under an authority role."""

    del data
    _fail("production lifecycle source authority verification is unavailable")


__all__ = (
    "BRANCH_ANALYSIS_DOMAIN",
    "COMPLETE_DECLARATIVE_FIRST_FAILURE_PREFIXES_PRESENT",
    "COMPLETE_DECLARED_CANDIDATE_FIRST_FAILURE_PREFIXES_PRESENT",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7H1ProductionLifecycleSourceCandidateV1Error",
    "DECLARATIVE_LIFECYCLE_SOURCE_AUTHORITY_PRESENT",
    "DECLARATIVE_LIFECYCLE_CANDIDATE_PRESENT",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "H1FailureEdgeV1",
    "H1LifecycleBranchAnalysisV1",
    "H1LifecycleBranchV1",
    "H1LifecycleEventV1",
    "H1LifecycleOperationV1",
    "H1LifecycleOutcomeV1",
    "H1LifecycleReplayV1",
    "H1LifecycleTransitionV1",
    "H1NativeExistenceV1",
    "H1ProductionLifecycleProgramV1",
    "H1ProductionLifecycleSourceAuthorityV1",
    "H1ProductionLifecycleSourceCandidateV1",
    "H1ProductionLifecycleSourceManifestV1",
    "H1ResourcePrefixV1",
    "LIVE_RUNTIME_INTEGRATION_PRESENT",
    "NUMERIC_SHARED_OPERAND_ISSUED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "PRODUCTION_EXECUTION_AUTHORITY_PRESENT",
    "PROGRAM_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REPLAY_DOMAIN",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "SHARED_RESOURCE_PATHS",
    "SOURCE_CANDIDATE_DOMAIN",
    "SOURCE_BOUND_SYMBOLS",
    "SOURCE_MANIFEST_DOMAIN",
    "TYPED_PRODUCTION_BLOCKERS",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "derive_h1_production_lifecycle_source_manifest_id_v1",
    "official_h1_production_lifecycle_branch_analysis_v1",
    "official_h1_production_lifecycle_program_v1",
    "official_h1_production_lifecycle_source_authority_v1",
    "registered_h1_production_lifecycle_branch_analysis_candidate_v1",
    "registered_h1_production_lifecycle_program_candidate_v1",
    "registered_h1_production_lifecycle_source_candidate_v1",
    "replay_h1_production_lifecycle_events_v1",
    "verify_h1_production_lifecycle_source_authority_bytes_v1",
    "verify_h1_production_lifecycle_source_candidate_bytes_v1",
)
