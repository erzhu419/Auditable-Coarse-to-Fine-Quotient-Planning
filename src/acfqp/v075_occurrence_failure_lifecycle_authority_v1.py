"""Typed failure closure for an incomplete V0-075 observer lifecycle.

The successful multistage lifecycle deliberately refuses to close before a
registered validation checkpoint.  A process, protocol, timeout, or direct
physical-row-cap failure can nevertheless occur before that checkpoint.  This
module provides a separate, fail-closed authority for that case.  It does not
relax the successful lifecycle:

* the exact controller, batched adapter, and private observer session are
  checked by object identity inside the trusted boundary;
* every completed signed batch, lifecycle event, frozen aggregate-support
  fact, result reference, and native work reference is retained;
* every completed batch is publicly verified, sequence verified, and exactly
  replayed through a scope-specific private verifier;
* the otherwise-empty underlying per-draw journal is uniquely closed and
  independently replayed; and
* the only terminal class emitted here is
  ``ATTEMPT_CLOSURE_NONCERTIFICATE``.

No secret law, salt, kernel, stream, random word, or accepted-draw identity is
placed in the portable artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_occurrence_failure_lifecycle_authority_v1"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TARGET_EXECUTION_OPENED = False
PLAN_CERTIFICATE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ALLOWED = False

_SIGNING_DOMAIN = (
    b"acfqp:v075-occurrence-failure-lifecycle-closure-signing:v1"
)
_AUTHORITY_ISSUER = object()
_REFERENCE_ISSUER = object()
_EXECUTION_ISSUER = object()
_CLOSURE_ISSUER = object()
_VERIFICATION_ISSUER = object()

DOMAIN_TAGS = {
    "work": "acfqp:v075-occurrence-failure-native-work:v1",
    "reference": "acfqp:v075-occurrence-failure-artifact-reference:v1",
    "construction_result": (
        "acfqp:v075-construction-occurrence-failure-result:v1"
    ),
    "execution": "acfqp:v075-occurrence-failure-execution-evidence:v1",
    "closure": "acfqp:v075-occurrence-failure-lifecycle-closure:v1",
    "verification": (
        "acfqp:v075-occurrence-failure-lifecycle-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 failure-lifecycle domains must be unique")


class V075OccurrenceFailureLifecycleInvariantViolation(ValueError):
    """A controller, prefix, work, replay, or terminal invariant failed."""


def _fail(message: str) -> None:
    raise V075OccurrenceFailureLifecycleInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075OccurrenceFailureLifecycleInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075OccurrenceFailureLifecycleInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 128
        or any(
            not (
                character.isupper()
                or character.isdigit()
                or character == "_"
            )
            for character in value
        )
    ):
        _fail(f"{field_name} must be one bounded uppercase token")
    return value


class V075OccurrenceFailureTerminalCodeV1(str, Enum):
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    PROCESS_FAILURE = "PROCESS_FAILURE"
    TIMEOUT = "TIMEOUT"
    DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED = (
        "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED"
    )


class V075FailureArtifactRoleV1(str, Enum):
    CONSTRUCTION_RESULT = "CONSTRUCTION_RESULT"
    CONSTRUCTION_WORK = "CONSTRUCTION_WORK"
    PRODUCTION_IPC_RESULT = "PRODUCTION_IPC_RESULT"
    PRODUCTION_IPC_CHILD_RESULT = "PRODUCTION_IPC_CHILD_RESULT"
    PRODUCTION_IPC_JOURNAL = "PRODUCTION_IPC_JOURNAL"
    PRODUCTION_IPC_WORK = "PRODUCTION_IPC_WORK"


@dataclass(frozen=True, slots=True)
class V075OccurrenceFailureActualWorkV1:
    """Complete native IPC work shape; every field is explicit and observed."""

    process_launches: int
    child_messages: int
    parent_messages: int
    batch_intents: int
    support_freeze_intents: int
    round_begin_intents: int
    accepted_draws: int
    outcome_aggregates: int
    child_bytes_read: int
    parent_bytes_written: int
    protocol_checks: int
    host_operational_planner_replays: int
    child_exit_code: int | None
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        counters = (
            self.process_launches,
            self.child_messages,
            self.parent_messages,
            self.batch_intents,
            self.support_freeze_intents,
            self.round_begin_intents,
            self.accepted_draws,
            self.outcome_aggregates,
            self.child_bytes_read,
            self.parent_bytes_written,
            self.protocol_checks,
            self.host_operational_planner_replays,
        )
        if (
            any(type(value) is not int or value < 0 for value in counters)
            or self.process_launches != 1
            or self.host_operational_planner_replays != 0
            or type(self.child_exit_code) not in {int, type(None)}
        ):
            _fail("failure lifecycle native work is incomplete or malformed")
        object.__setattr__(self, "_work_id", _hash("work", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_occurrence_failure_native_work.v1",
            "schema_version": SCHEMA_VERSION,
            "process_launches": self.process_launches,
            "child_messages": self.child_messages,
            "parent_messages": self.parent_messages,
            "batch_intents": self.batch_intents,
            "support_freeze_intents": self.support_freeze_intents,
            "round_begin_intents": self.round_begin_intents,
            "accepted_draws": self.accepted_draws,
            "outcome_aggregates": self.outcome_aggregates,
            "child_bytes_read": self.child_bytes_read,
            "parent_bytes_written": self.parent_bytes_written,
            "protocol_checks": self.protocol_checks,
            "host_operational_planner_replays": (
                self.host_operational_planner_replays
            ),
            "child_exit_code": self.child_exit_code,
            "all_native_fields_observed": True,
            "missing_work_inferred_as_zero": False,
            "operational_lane": True,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class V075FailureArtifactReferenceV1:
    _issuer: object = field(repr=False, compare=False)
    role: V075FailureArtifactRoleV1
    artifact_id: str
    _reference_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.artifact_id, "failure source artifact")
        if (
            self._issuer is not _REFERENCE_ISSUER
            or type(self.role) is not V075FailureArtifactRoleV1
        ):
            _fail("failure artifact reference was caller-minted")
        object.__setattr__(
            self,
            "_reference_id",
            _hash("reference", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_occurrence_failure_artifact_reference.v1",
            "schema_version": SCHEMA_VERSION,
            "artifact_role": self.role.value,
            "artifact_id": self.artifact_id,
        }

    @property
    def reference_id(self) -> str:
        return self._reference_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "reference_id": self.reference_id}


@dataclass(frozen=True, slots=True)
class V075OccurrenceFailureExecutionEvidenceV1:
    """Exact source result plus its complete native operational work."""

    _issuer: object = field(repr=False, compare=False)
    authority_scope: lifecycle.V075LifecycleAuthorityScopeV1
    occurrence_id: str
    arm: worker.V075WorkerArmV1
    route: str
    source_status: str
    terminal_code: V075OccurrenceFailureTerminalCodeV1
    source_profile_id: str
    actual_work: V075OccurrenceFailureActualWorkV1
    references: tuple[V075FailureArtifactReferenceV1, ...]
    construction_fixture: bool
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "failure execution occurrence")
        _cid(self.source_profile_id, "failure execution profile")
        _token(self.route, "failure execution route")
        _token(self.source_status, "failure execution status")
        if (
            self._issuer is not _EXECUTION_ISSUER
            or type(self.authority_scope)
            is not lifecycle.V075LifecycleAuthorityScopeV1
            or type(self.arm) is not worker.V075WorkerArmV1
            or type(self.terminal_code)
            is not V075OccurrenceFailureTerminalCodeV1
            or type(self.actual_work)
            is not V075OccurrenceFailureActualWorkV1
            or type(self.references) is not tuple
            or not self.references
            or any(
                type(item) is not V075FailureArtifactReferenceV1
                for item in self.references
            )
            or tuple(item.role.value for item in self.references)
            != tuple(
                sorted(item.role.value for item in self.references)
            )
            or len({item.role for item in self.references})
            != len(self.references)
            or type(self.construction_fixture) is not bool
        ):
            _fail("failure execution evidence is malformed")
        roles = {item.role for item in self.references}
        if self.construction_fixture:
            expected = {
                V075FailureArtifactRoleV1.CONSTRUCTION_RESULT,
                V075FailureArtifactRoleV1.CONSTRUCTION_WORK,
            }
            if (
                self.authority_scope
                is not lifecycle.V075LifecycleAuthorityScopeV1
                .CONSTRUCTION_ONLY
                or roles != expected
            ):
                _fail("construction failure execution roles are incomplete")
        else:
            required = {
                V075FailureArtifactRoleV1.PRODUCTION_IPC_RESULT,
                V075FailureArtifactRoleV1.PRODUCTION_IPC_JOURNAL,
                V075FailureArtifactRoleV1.PRODUCTION_IPC_WORK,
            }
            allowed = required | {
                V075FailureArtifactRoleV1.PRODUCTION_IPC_CHILD_RESULT
            }
            if (
                self.authority_scope
                is not lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
                or not required <= roles
                or not roles <= allowed
            ):
                _fail("production failure execution roles are incomplete")
        direct_cap = (
            self.terminal_code
            is V075OccurrenceFailureTerminalCodeV1
            .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED
        )
        if (
            direct_cap
            != (
                self.route == "MATCHED_DIRECT_GROUND"
                and self.source_status == "NONCERTIFICATE"
                and self.actual_work.child_exit_code == 0
            )
            or (
                not direct_cap
                and self.source_status != "FAILED"
            )
            or (
                not self.construction_fixture
                and direct_cap
                and V075FailureArtifactRoleV1
                .PRODUCTION_IPC_CHILD_RESULT not in roles
            )
        ):
            _fail("failure execution status/route/code disagree")
        object.__setattr__(
            self,
            "_evidence_id",
            _hash("execution", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_occurrence_failure_execution_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "authority_scope": self.authority_scope.value,
            "occurrence_id": self.occurrence_id,
            "arm": self.arm.value,
            "route": self.route,
            "source_status": self.source_status,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": self.terminal_code.value,
            "source_profile_id": self.source_profile_id,
            "actual_work_id": self.actual_work.work_id,
            "reference_ids": [
                item.reference_id for item in self.references
            ],
            "work_reference_ids": [
                item.reference_id
                for item in self.references
                if item.role
                in {
                    V075FailureArtifactRoleV1.CONSTRUCTION_WORK,
                    V075FailureArtifactRoleV1.PRODUCTION_IPC_WORK,
                }
            ],
            "result_reference_ids": [
                item.reference_id
                for item in self.references
                if item.role
                in {
                    V075FailureArtifactRoleV1.CONSTRUCTION_RESULT,
                    V075FailureArtifactRoleV1.PRODUCTION_IPC_RESULT,
                    V075FailureArtifactRoleV1
                    .PRODUCTION_IPC_CHILD_RESULT,
                }
            ],
            "construction_fixture": self.construction_fixture,
            "all_emitted_work_references_retained": True,
            "all_emitted_result_references_retained": True,
            "missing_work_inferred_as_zero": False,
        }

    @property
    def evidence_id(self) -> str:
        return self._evidence_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actual_work": self.actual_work.to_document(),
            "references": [item.to_document() for item in self.references],
            "evidence_id": self.evidence_id,
        }


def _reference(
    role: V075FailureArtifactRoleV1,
    artifact_id: str,
) -> V075FailureArtifactReferenceV1:
    return V075FailureArtifactReferenceV1(
        _REFERENCE_ISSUER,
        role,
        artifact_id,
    )


def issue_v075_construction_failure_execution_fixture_v1(
    *,
    open_lifecycle_binding: lifecycle.V075OpenMultistageLifecycleBindingV1,
    terminal_code: V075OccurrenceFailureTerminalCodeV1,
    actual_work: V075OccurrenceFailureActualWorkV1,
) -> V075OccurrenceFailureExecutionEvidenceV1:
    """Issue exact-type construction evidence without impersonating IPC."""

    if (
        type(open_lifecycle_binding)
        is not lifecycle.V075OpenMultistageLifecycleBindingV1
        or open_lifecycle_binding.authority_scope
        is not lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
        or type(terminal_code)
        is not V075OccurrenceFailureTerminalCodeV1
        or type(actual_work) is not V075OccurrenceFailureActualWorkV1
    ):
        _fail("construction failure fixture inputs are foreign or mistyped")
    route = (
        "MATCHED_DIRECT_GROUND"
        if open_lifecycle_binding.arm
        is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        else "ADAPTIVE_QUOTIENT"
    )
    status = (
        "NONCERTIFICATE"
        if terminal_code
        is V075OccurrenceFailureTerminalCodeV1
        .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED
        else "FAILED"
    )
    result_id = _hash(
        "construction_result",
        {
            "schema": "acfqp.v075_construction_occurrence_failure_result.v1",
            "schema_version": SCHEMA_VERSION,
            "open_lifecycle_binding_id": open_lifecycle_binding.binding_id,
            "occurrence_id": open_lifecycle_binding.occurrence_id,
            "arm": open_lifecycle_binding.arm.value,
            "route": route,
            "status": status,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": terminal_code.value,
            "actual_work_id": actual_work.work_id,
            "construction_fixture": True,
            "scientific_plan_certificate": False,
            "infeasibility_certificate": False,
        },
    )
    references = tuple(
        sorted(
            (
                _reference(
                    V075FailureArtifactRoleV1.CONSTRUCTION_RESULT,
                    result_id,
                ),
                _reference(
                    V075FailureArtifactRoleV1.CONSTRUCTION_WORK,
                    actual_work.work_id,
                ),
            ),
            key=lambda item: item.role.value,
        )
    )
    return V075OccurrenceFailureExecutionEvidenceV1(
        _EXECUTION_ISSUER,
        lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY,
        open_lifecycle_binding.occurrence_id,
        open_lifecycle_binding.arm,
        route,
        status,
        terminal_code,
        open_lifecycle_binding.binding_id,
        actual_work,
        references,
        True,
    )


def freeze_v075_production_failure_execution_evidence_v1(
    *,
    ipc_result: Any,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
) -> V075OccurrenceFailureExecutionEvidenceV1:
    """Bind an exact production IPC failure without importing it at startup."""

    from acfqp import v075_production_occurrence_ipc_v1 as ipc

    if (
        type(ipc_result) is not ipc.V075ProductionOccurrenceIPCResultV1
        or type(controller)
        is not lifecycle.V075ParentOwnedMultistageObserverLifecycleV1
        or controller.open_binding.authority_scope
        is not lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
        or ipc_result.authority_scope != "PRODUCTION"
        or ipc_result.occurrence_id
        != controller.open_binding.occurrence_id
        or ipc_result.observed_batches != controller.batches
        or ipc_result.status not in {"FAILED", "NONCERTIFICATE"}
    ):
        _fail("production IPC failure is untyped, successful, or transplanted")
    try:
        terminal_code = V075OccurrenceFailureTerminalCodeV1(
            ipc_result.terminal_code
        )
    except ValueError as error:
        raise V075OccurrenceFailureLifecycleInvariantViolation(
            "production IPC terminal is not a registered failure code"
        ) from error
    work = ipc_result.actual_work
    if type(work) is not ipc.V075ProductionIPCActualWorkV1:
        _fail("production IPC actual work is missing or duck-typed")
    normalized = V075OccurrenceFailureActualWorkV1(
        process_launches=work.process_launches,
        child_messages=work.child_messages,
        parent_messages=work.parent_messages,
        batch_intents=work.batch_intents,
        support_freeze_intents=work.support_freeze_intents,
        round_begin_intents=work.round_begin_intents,
        accepted_draws=work.accepted_draws,
        outcome_aggregates=work.outcome_aggregates,
        child_bytes_read=work.child_bytes_read,
        parent_bytes_written=work.parent_bytes_written,
        protocol_checks=work.protocol_checks,
        host_operational_planner_replays=(
            work.host_operational_planner_replays
        ),
        child_exit_code=work.child_exit_code,
    )
    reference_values = [
        _reference(
            V075FailureArtifactRoleV1.PRODUCTION_IPC_RESULT,
            ipc_result.result_id,
        ),
        _reference(
            V075FailureArtifactRoleV1.PRODUCTION_IPC_JOURNAL,
            ipc_result.journal_id,
        ),
        _reference(
            V075FailureArtifactRoleV1.PRODUCTION_IPC_WORK,
            work.work_id,
        ),
    ]
    if ipc_result.child_result_id is not None:
        reference_values.append(
            _reference(
                V075FailureArtifactRoleV1.PRODUCTION_IPC_CHILD_RESULT,
                ipc_result.child_result_id,
            )
        )
    return V075OccurrenceFailureExecutionEvidenceV1(
        _EXECUTION_ISSUER,
        lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION,
        ipc_result.occurrence_id,
        controller.open_binding.arm,
        ipc_result.route,
        ipc_result.status,
        terminal_code,
        ipc_result.profile_id,
        normalized,
        tuple(sorted(reference_values, key=lambda item: item.role.value)),
        False,
    )


def _closure_signing_payload(
    *,
    open_binding: lifecycle.V075OpenMultistageLifecycleBindingV1,
    terminal_code: V075OccurrenceFailureTerminalCodeV1,
    abort_stage: str,
    execution_evidence_id: str,
    event_ids: tuple[str, ...],
    batch_ids: tuple[str, ...],
    support_evidence_ids: tuple[str, ...],
    public_verification_ids: tuple[str, ...],
    sequence_verification_ids: tuple[str, ...],
    private_replay_verification_ids: tuple[str, ...],
    underlying_closure_id: str,
    underlying_closure_verification_id: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_occurrence_failure_lifecycle_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "authority_scope": open_binding.authority_scope.value,
        "open_lifecycle_binding_id": open_binding.binding_id,
        "occurrence_id": open_binding.occurrence_id,
        "context_id": open_binding.context_id,
        "arm": open_binding.arm.value,
        "target_tape_namespace_id": (
            open_binding.target_tape_namespace_id
        ),
        "observer_session_public_id": open_binding.session_public_id,
        "observer_open_binding_id": open_binding.observer_open_binding_id,
        "route_cap_profile_id": open_binding.route_cap_profile_id,
        "terminal_scope": "ROUTE_ATTEMPT",
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": terminal_code.value,
        "abort_stage": abort_stage,
        "execution_evidence_id": execution_evidence_id,
        "event_ids": list(event_ids),
        "batch_ids_in_emission_order": list(batch_ids),
        "aggregate_support_evidence_ids": list(support_evidence_ids),
        "public_verification_ids": list(public_verification_ids),
        "sequence_verification_ids": list(sequence_verification_ids),
        "private_replay_verification_ids": list(
            private_replay_verification_ids
        ),
        "underlying_session_closure_id": underlying_closure_id,
        "underlying_closure_verification_id": (
            underlying_closure_verification_id
        ),
        "all_emitted_public_batches_retained": True,
        "all_emitted_lifecycle_events_retained": True,
        "all_emitted_support_evidence_retained": True,
        "all_work_and_result_references_retained": True,
        "missing_work_inferred_as_zero": False,
        "scientific_plan_certificate": False,
        "infeasibility_certificate": False,
        "private_law_serialized": False,
        "private_salt_serialized": False,
        "private_kernel_serialized": False,
        "random_words_serialized": False,
        "accepted_draw_indices_serialized": False,
    }


def occurrence_failure_closure_signing_bytes_v1(
    **values: Any,
) -> bytes:
    return (
        _SIGNING_DOMAIN
        + b"\x00"
        + canonical_json_bytes(_closure_signing_payload(**values))
    )


@dataclass(frozen=True, slots=True)
class V075OccurrenceFailureLifecycleClosureV1:
    _issuer: object = field(repr=False, compare=False)
    open_binding: lifecycle.V075OpenMultistageLifecycleBindingV1
    terminal_code: V075OccurrenceFailureTerminalCodeV1
    abort_stage: str
    execution_evidence: V075OccurrenceFailureExecutionEvidenceV1
    events: tuple[lifecycle.V075MultistageLifecycleEventV1, ...]
    batches: tuple[batched.V075SignedBatchedObservationV1, ...]
    aggregate_support_evidence: tuple[
        graph.V075BatchAggregateSupportEvidenceV1, ...
    ]
    public_verifications: tuple[
        batched.V075BatchedObservationPublicVerificationV1, ...
    ]
    sequence_verifications: tuple[
        batched.V075BatchedObservationSequenceVerificationV1, ...
    ]
    private_replay_verifications: tuple[
        batched.V075BatchedObservationPrivateReplayVerificationV1, ...
    ]
    underlying_closure: observer.V075ObserverJournalClosureV1
    underlying_closure_verification: (
        observer.V075ObserverClosureVerificationV1
    )
    observer_signature_hex: str
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _token(self.abort_stage, "failure abort stage")
        if (
            self._issuer is not _CLOSURE_ISSUER
            or type(self.open_binding)
            is not lifecycle.V075OpenMultistageLifecycleBindingV1
            or type(self.terminal_code)
            is not V075OccurrenceFailureTerminalCodeV1
            or type(self.execution_evidence)
            is not V075OccurrenceFailureExecutionEvidenceV1
            or self.execution_evidence.authority_scope
            is not self.open_binding.authority_scope
            or self.execution_evidence.occurrence_id
            != self.open_binding.occurrence_id
            or self.execution_evidence.arm is not self.open_binding.arm
            or self.execution_evidence.terminal_code is not self.terminal_code
            or type(self.events) is not tuple
            or any(
                type(item) is not lifecycle.V075MultistageLifecycleEventV1
                for item in self.events
            )
            or type(self.batches) is not tuple
            or any(
                type(item) is not batched.V075SignedBatchedObservationV1
                for item in self.batches
            )
            or type(self.aggregate_support_evidence) is not tuple
            or any(
                type(item)
                is not graph.V075BatchAggregateSupportEvidenceV1
                for item in self.aggregate_support_evidence
            )
            or type(self.public_verifications) is not tuple
            or type(self.sequence_verifications) is not tuple
            or type(self.private_replay_verifications) is not tuple
            or type(self.underlying_closure)
            is not observer.V075ObserverJournalClosureV1
            or type(self.underlying_closure_verification)
            is not observer.V075ObserverClosureVerificationV1
        ):
            _fail("failure lifecycle closure is malformed or transplanted")
        signing_values = self._signing_values()
        if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=(
                self.open_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=occurrence_failure_closure_signing_bytes_v1(
                **signing_values
            ),
            signature_hex=self.observer_signature_hex,
        ):
            _fail("failure lifecycle closure signature is invalid")
        object.__setattr__(
            self,
            "_closure_id",
            _hash(
                "closure",
                {
                    **_closure_signing_payload(**signing_values),
                    "observer_signature_hex": self.observer_signature_hex,
                    "observer_signature_verified": True,
                },
            ),
        )

    def _signing_values(self) -> dict[str, Any]:
        return {
            "open_binding": self.open_binding,
            "terminal_code": self.terminal_code,
            "abort_stage": self.abort_stage,
            "execution_evidence_id": self.execution_evidence.evidence_id,
            "event_ids": tuple(item.event_id for item in self.events),
            "batch_ids": tuple(item.batch_id for item in self.batches),
            "support_evidence_ids": tuple(
                item.evidence_id for item in self.aggregate_support_evidence
            ),
            "public_verification_ids": tuple(
                item.verification_id for item in self.public_verifications
            ),
            "sequence_verification_ids": tuple(
                item.verification_id for item in self.sequence_verifications
            ),
            "private_replay_verification_ids": tuple(
                item.verification_id
                for item in self.private_replay_verifications
            ),
            "underlying_closure_id": self.underlying_closure.closure_id,
            "underlying_closure_verification_id": (
                self.underlying_closure_verification.verification_id
            ),
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {
            **_closure_signing_payload(**self._signing_values()),
            "open_lifecycle_binding": self.open_binding.to_document(),
            "execution_evidence": self.execution_evidence.to_document(),
            "events": [item.to_document() for item in self.events],
            "signed_public_batches": [
                item.to_document() for item in self.batches
            ],
            "aggregate_support_evidence": [
                item.to_document()
                for item in self.aggregate_support_evidence
            ],
            "public_verifications": [
                item.to_document() for item in self.public_verifications
            ],
            "sequence_verifications": [
                item.to_document() for item in self.sequence_verifications
            ],
            "private_replay_verifications": [
                item.to_document()
                for item in self.private_replay_verifications
            ],
            "underlying_observer_closure": (
                self.underlying_closure.to_document()
            ),
            "underlying_observer_closure_verification": (
                self.underlying_closure_verification.to_document()
            ),
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "closure_id": self.closure_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


@dataclass(frozen=True, slots=True)
class V075OccurrenceFailureLifecycleVerificationV1:
    _issuer: object = field(repr=False, compare=False)
    closure_id: str
    execution_evidence_id: str
    terminal_code: V075OccurrenceFailureTerminalCodeV1
    batch_count: int
    event_count: int
    support_evidence_count: int
    accepted_draw_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.closure_id, "failure lifecycle closure")
        _cid(self.execution_evidence_id, "failure execution evidence")
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.terminal_code)
            is not V075OccurrenceFailureTerminalCodeV1
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.batch_count,
                    self.event_count,
                    self.support_evidence_count,
                    self.accepted_draw_count,
                )
            )
        ):
            _fail("failure lifecycle verification was caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_occurrence_failure_lifecycle_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "closure_id": self.closure_id,
            "execution_evidence_id": self.execution_evidence_id,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": self.terminal_code.value,
            "batch_count": self.batch_count,
            "event_count": self.event_count,
            "support_evidence_count": self.support_evidence_count,
            "accepted_draw_count": self.accepted_draw_count,
            "controller_session_identity_verified": True,
            "event_hash_chain_replayed": True,
            "partial_phase_causality_replayed": True,
            "all_signed_batches_replayed": True,
            "all_stream_sequences_replayed": True,
            "all_private_batch_intervals_replayed": True,
            "underlying_observer_journal_replayed": True,
            "native_work_reconciled": True,
            "missing_work_inferred_as_zero": False,
            "scientific_plan_certificate": False,
            "infeasibility_certificate": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


@dataclass(frozen=True, slots=True)
class V075SealedOccurrenceFailureLifecycleV1:
    closure: V075OccurrenceFailureLifecycleClosureV1
    verification: V075OccurrenceFailureLifecycleVerificationV1

    def __post_init__(self) -> None:
        if (
            type(self.closure)
            is not V075OccurrenceFailureLifecycleClosureV1
            or type(self.verification)
            is not V075OccurrenceFailureLifecycleVerificationV1
            or self.verification.closure_id != self.closure.closure_id
            or self.verification.execution_evidence_id
            != self.closure.execution_evidence.evidence_id
        ):
            _fail("sealed failure lifecycle is not verifier-issued")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_sealed_occurrence_failure_lifecycle.v1",
            "schema_version": SCHEMA_VERSION,
            "closure": self.closure.to_document(),
            "verification": self.verification.to_document(),
            "closure_id": self.closure.closure_id,
            "verification_id": self.verification.verification_id,
        }


def _expected_batch_verifications(
    batches: tuple[batched.V075SignedBatchedObservationV1, ...],
) -> tuple[
    tuple[batched.V075BatchedObservationPublicVerificationV1, ...],
    tuple[batched.V075BatchedObservationSequenceVerificationV1, ...],
]:
    public_values = tuple(
        sorted(
            (
                batched.verify_v075_signed_batched_observation_v1(item)
                for item in batches
            ),
            key=lambda item: item.batch_id,
        )
    )
    groups: dict[str, list[batched.V075SignedBatchedObservationV1]] = {}
    for item in batches:
        groups.setdefault(
            item.request.stream_identity.stream_id,
            [],
        ).append(item)
    sequence_values = tuple(
        sorted(
            (
                batched.verify_v075_batched_observation_sequence_v1(
                    tuple(items)
                )
                for items in groups.values()
            ),
            key=lambda item: item.stream_id,
        )
    )
    return public_values, sequence_values


_EVENT_PHASE = {
    lifecycle.V075LifecycleEventKindV1.DISCOVERY_BATCH: 0,
    lifecycle.V075LifecycleEventKindV1.SUPPORT_FREEZE: 1,
    lifecycle.V075LifecycleEventKindV1.VALIDATION_BATCH: 2,
    lifecycle.V075LifecycleEventKindV1.ADAPTIVE_DISCOVERY_BATCH: 0,
    lifecycle.V075LifecycleEventKindV1.ADAPTIVE_SUPPORT_FREEZE: 1,
    lifecycle.V075LifecycleEventKindV1.ADAPTIVE_VALIDATION_BATCH: 2,
}


def _verify_partial_public_prefix(
    *,
    open_binding: lifecycle.V075OpenMultistageLifecycleBindingV1,
    events: tuple[lifecycle.V075MultistageLifecycleEventV1, ...],
    batches: tuple[batched.V075SignedBatchedObservationV1, ...],
    evidence: tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
) -> None:
    if (
        tuple(item.sequence_number for item in events)
        != tuple(range(1, len(events) + 1))
        or tuple(item.previous_event_id for item in events)
        != tuple(
            lifecycle._INITIAL_EVENT_ID
            if index == 0
            else events[index - 1].event_id
            for index in range(len(events))
        )
        or len({item.batch_id for item in batches}) != len(batches)
        or len({item.request.request_id for item in batches}) != len(batches)
        or any(
            (
                item.request.session_public_id,
                item.request.observer_open_binding,
                item.request.stream_identity.context_id,
                item.request.stream_identity.arm,
            )
            != (
                open_binding.session_public_id,
                open_binding.observer_open_binding,
                open_binding.context_id,
                open_binding.arm.value,
            )
            for item in batches
        )
    ):
        _fail("failure lifecycle event/batch prefix is gapped or transplanted")
    batch_events = tuple(item for item in events if item.batch_id is not None)
    if (
        tuple(item.batch_id for item in batch_events)
        != tuple(item.batch_id for item in batches)
        or tuple(item.request_id for item in batch_events)
        != tuple(item.request.request_id for item in batches)
    ):
        _fail("failure lifecycle omitted or reordered an emitted batch event")
    for event, batch in zip(batch_events, batches, strict=True):
        lane = batch.request.stream_identity.lane
        if (
            event.stream_id != batch.request.stream_identity.stream_id
            or event.row_binding_id
            != batch.request.stream_identity.row_binding_id
            or event.accepted_draw_count
            != batch.request.accepted_draw_count
            or (
                lane is graph.V075ObservationLaneV1.DISCOVERY
                and event.kind
                not in {
                    lifecycle.V075LifecycleEventKindV1.DISCOVERY_BATCH,
                    lifecycle.V075LifecycleEventKindV1
                    .ADAPTIVE_DISCOVERY_BATCH,
                }
            )
            or (
                lane is graph.V075ObservationLaneV1.VALIDATION
                and event.kind
                not in {
                    lifecycle.V075LifecycleEventKindV1.VALIDATION_BATCH,
                    lifecycle.V075LifecycleEventKindV1
                    .ADAPTIVE_VALIDATION_BATCH,
                }
            )
        ):
            _fail("failure lifecycle batch event differs from its signed batch")
    evidence_by_id = {item.evidence_id: item for item in evidence}
    batch_by_id = {item.batch_id: item for item in batches}
    if (
        len(evidence_by_id) != len(evidence)
        or tuple(evidence_by_id) != tuple(
            item.evidence_id for item in evidence
        )
        or tuple(evidence_by_id) != tuple(sorted(evidence_by_id))
    ):
        _fail("failure lifecycle support evidence is duplicated or unsorted")
    for item in evidence:
        source = batch_by_id.get(item.discovery_batch_id)
        outcomes = {} if source is None else {
            outcome.outcome_id: outcome for outcome in source.outcomes
        }
        outcome = outcomes.get(item.discovery_outcome_id)
        if (
            source is None
            or source.request.request_id != item.discovery_request_id
            or source.request.stream_identity.lane
            is not graph.V075ObservationLaneV1.DISCOVERY
            or source.request.stream_identity.row_binding != item.row_binding
            or item.namespace != open_binding.namespace
            or outcome is None
            or outcome.count != item.discovery_outcome_count
            or item.observed_state
            != graph.V075SymbolicGraphStateV1(
                item.row_binding.context,
                outcome.next_ranks,
                outcome.failure,
            )
        ):
            _fail("failure support evidence is foreign or not batch-derived")
    phase_by_round: dict[int, int] = {}
    seen_rounds: set[int] = set()
    batch_sequence: dict[str, int] = {}
    frozen_epoch: dict[str, tuple[int, tuple[str, ...]]] = {}
    for event in events:
        seen_rounds.add(event.adaptive_round_index)
        phase = _EVENT_PHASE[event.kind]
        prior = phase_by_round.get(event.adaptive_round_index, 0)
        if phase < prior:
            _fail("failure lifecycle phase regressed before abort")
        phase_by_round[event.adaptive_round_index] = phase
        if event.batch_id is not None:
            batch_sequence[event.batch_id] = event.sequence_number
        if event.kind in {
            lifecycle.V075LifecycleEventKindV1.SUPPORT_FREEZE,
            lifecycle.V075LifecycleEventKindV1.ADAPTIVE_SUPPORT_FREEZE,
        }:
            if (
                event.support_epoch_id is None
                or event.support_epoch_id in frozen_epoch
                or any(
                    evidence_by_id.get(value) is None
                    for value in event.aggregate_support_evidence_ids
                )
                or any(
                    batch_sequence.get(value, 10**18)
                    >= event.sequence_number
                    for value in event.source_discovery_batch_ids
                )
            ):
                _fail("failure lifecycle support freeze is retrospective")
            frozen_epoch[event.support_epoch_id] = (
                event.sequence_number,
                event.aggregate_support_evidence_ids,
            )
        if event.kind in {
            lifecycle.V075LifecycleEventKindV1.VALIDATION_BATCH,
            lifecycle.V075LifecycleEventKindV1.ADAPTIVE_VALIDATION_BATCH,
        }:
            prior_freeze = frozen_epoch.get(event.support_epoch_id or "")
            if (
                prior_freeze is None
                or prior_freeze[0] >= event.sequence_number
                or prior_freeze[1]
                != event.aggregate_support_evidence_ids
            ):
                _fail("failure lifecycle validation lacks its prior freeze")
    if seen_rounds and seen_rounds != set(range(max(seen_rounds) + 1)):
        _fail("failure lifecycle adaptive rounds are gapped")


def _verify_work_prefix(
    *,
    open_binding: lifecycle.V075OpenMultistageLifecycleBindingV1,
    terminal_code: V075OccurrenceFailureTerminalCodeV1,
    abort_stage: str,
    execution_evidence: V075OccurrenceFailureExecutionEvidenceV1,
    events: tuple[lifecycle.V075MultistageLifecycleEventV1, ...],
    batches: tuple[batched.V075SignedBatchedObservationV1, ...],
    evidence: tuple[graph.V075BatchAggregateSupportEvidenceV1, ...],
) -> None:
    work = execution_evidence.actual_work
    support_event_count = sum(
        item.kind
        in {
            lifecycle.V075LifecycleEventKindV1.SUPPORT_FREEZE,
            lifecycle.V075LifecycleEventKindV1.ADAPTIVE_SUPPORT_FREEZE,
        }
        for item in events
    )
    maximum_round = max(
        (item.adaptive_round_index for item in events),
        default=0,
    )
    if (
        work.accepted_draws
        != sum(
            item.request.accepted_draw_count for item in batches
        )
        or work.outcome_aggregates
        != sum(len(item.outcomes) for item in batches)
        or work.batch_intents < len(batches)
        or work.child_messages < len(batches)
        or work.parent_messages < len(batches)
        or work.support_freeze_intents < support_event_count
        or work.round_begin_intents < maximum_round
    ):
        _fail("failure native work omits completed observer/protocol work")
    if (
        terminal_code
        is V075OccurrenceFailureTerminalCodeV1
        .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED
    ):
        if (
            abort_stage != "DIRECT_ROOT_DISCOVERY"
            or open_binding.arm
            is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or not batches
            or evidence
            or any(
                item.request.stream_identity.lane
                is not graph.V075ObservationLaneV1.DISCOVERY
                or item.request.stream_identity.row_binding
                .remaining_horizon
                != 2
                for item in batches
            )
            or any(
                item.kind
                not in {
                    lifecycle.V075LifecycleEventKindV1.DISCOVERY_BATCH,
                }
                for item in events
            )
        ):
            _fail("direct physical cap must close one root-only prefix")


def _verify_work_and_terminal(
    closure: V075OccurrenceFailureLifecycleClosureV1,
) -> None:
    _verify_work_prefix(
        open_binding=closure.open_binding,
        terminal_code=closure.terminal_code,
        abort_stage=closure.abort_stage,
        execution_evidence=closure.execution_evidence,
        events=closure.events,
        batches=closure.batches,
        evidence=closure.aggregate_support_evidence,
    )


def _verify_common(
    closure: V075OccurrenceFailureLifecycleClosureV1,
) -> V075OccurrenceFailureLifecycleVerificationV1:
    if type(closure) is not V075OccurrenceFailureLifecycleClosureV1:
        _fail("failure lifecycle verifier requires one exact closure")
    _verify_partial_public_prefix(
        open_binding=closure.open_binding,
        events=closure.events,
        batches=closure.batches,
        evidence=closure.aggregate_support_evidence,
    )
    expected_public, expected_sequences = _expected_batch_verifications(
        closure.batches
    )
    if (
        closure.public_verifications != expected_public
        or closure.sequence_verifications != expected_sequences
        or tuple(
            sorted(
                item.batch_id
                for item in closure.private_replay_verifications
            )
        )
        != tuple(sorted(item.batch_id for item in closure.batches))
        or any(
            (
                item.request_id,
                item.observer_open_binding_id,
                item.replayed_draw_count,
            )
            != (
                batch.request.request_id,
                closure.open_binding.observer_open_binding_id,
                batch.request.accepted_draw_count,
            )
            for item, batch in (
                (
                    next(
                        replay
                        for replay in closure.private_replay_verifications
                        if replay.batch_id == batch.batch_id
                    ),
                    batch,
                )
                for batch in closure.batches
            )
        )
    ):
        _fail("failure lifecycle batch verification registry is incomplete")
    if (
        closure.underlying_closure.entries
        or closure.underlying_closure.session_public_id
        != closure.open_binding.session_public_id
        or closure.underlying_closure.authority_binding
        != closure.open_binding.observer_open_binding
        or closure.underlying_closure_verification.closure_id
        != closure.underlying_closure.closure_id
        or closure.underlying_closure_verification.observer_open_binding_id
        != closure.open_binding.observer_open_binding_id
        or closure.underlying_closure_verification.replayed_record_count != 0
        or closure.underlying_closure_verification.replayed_stream_count != 0
    ):
        _fail("failure lifecycle underlying observer closure is not exact")
    _verify_work_and_terminal(closure)
    signing_values = closure._signing_values()
    if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=(
            closure.open_binding.namespace.signer_registry
            .observer_evidence_key
        ),
        message=occurrence_failure_closure_signing_bytes_v1(
            **signing_values
        ),
        signature_hex=closure.observer_signature_hex,
    ):
        _fail("failure lifecycle signature replay failed")
    expected_id = _hash(
        "closure",
        {
            **_closure_signing_payload(**signing_values),
            "observer_signature_hex": closure.observer_signature_hex,
            "observer_signature_verified": True,
        },
    )
    if expected_id != closure.closure_id:
        _fail("failure lifecycle closure content identity changed")
    return V075OccurrenceFailureLifecycleVerificationV1(
        _VERIFICATION_ISSUER,
        closure.closure_id,
        closure.execution_evidence.evidence_id,
        closure.terminal_code,
        len(closure.batches),
        len(closure.events),
        len(closure.aggregate_support_evidence),
        sum(
            item.request.accepted_draw_count for item in closure.batches
        ),
    )


class V075OccurrenceFailureLifecycleAuthorityV1:
    """Single-use trusted wrapper over one exact incomplete lifecycle."""

    __slots__ = (
        "_batched_session",
        "_closed",
        "_controller",
        "_observer_session",
        "_open_binding",
    )

    def __init__(
        self,
        controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
        issuer: object,
    ) -> None:
        if (
            issuer is not _AUTHORITY_ISSUER
            or type(controller)
            is not lifecycle.V075ParentOwnedMultistageObserverLifecycleV1
            or getattr(controller, "_closed", True)
        ):
            _fail("failure authority requires one exact open controller")
        batch_session = getattr(controller, "_batched_session", None)
        observer_session = getattr(batch_session, "_session", None)
        if (
            type(batch_session)
            is not batched.V075PrivateBatchedObserverSessionV1
            or type(observer_session)
            is not observer.V075PrivateObserverSessionV1
            or getattr(observer_session, "_closed", True)
            or observer_session.journal_entries
            or controller.batches != batch_session.batches
            or controller.open_binding.session_public_id
            != batch_session.session_public_id
            or controller.open_binding.observer_open_binding
            != observer_session.authority_binding
        ):
            _fail("failure authority controller/session identity is not exact")
        self._controller = controller
        self._batched_session = batch_session
        self._observer_session = observer_session
        self._open_binding = controller.open_binding
        self._closed = False

    @property
    def open_binding(
        self,
    ) -> lifecycle.V075OpenMultistageLifecycleBindingV1:
        return self._open_binding

    def _require_live_graph(self) -> None:
        if (
            self._closed
            or getattr(self._controller, "_closed", True)
            or getattr(self._observer_session, "_closed", True)
            or getattr(self._controller, "_batched_session", None)
            is not self._batched_session
            or getattr(self._batched_session, "_session", None)
            is not self._observer_session
            or self._controller.open_binding != self._open_binding
            or self._controller.batches != self._batched_session.batches
            or self._observer_session.journal_entries
        ):
            _fail("failure authority was closed or its session was replaced")

    def _seal(
        self,
        *,
        execution_evidence: V075OccurrenceFailureExecutionEvidenceV1,
        abort_stage: str,
        private_replays: tuple[
            batched.V075BatchedObservationPrivateReplayVerificationV1,
            ...,
        ],
        underlying_closure: observer.V075ObserverJournalClosureV1,
        underlying_verification: observer.V075ObserverClosureVerificationV1,
    ) -> V075SealedOccurrenceFailureLifecycleV1:
        if (
            self._closed
            or getattr(self._controller, "_closed", True)
            or not getattr(self._observer_session, "_closed", False)
            or getattr(self._controller, "_batched_session", None)
            is not self._batched_session
            or getattr(self._batched_session, "_session", None)
            is not self._observer_session
            or self._controller.open_binding != self._open_binding
            or self._controller.batches != self._batched_session.batches
        ):
            _fail("failure authority post-close session identity changed")
        _token(abort_stage, "failure abort stage")
        batches = self._controller.batches
        events = self._controller.events
        evidence = self._controller.aggregate_support_evidence
        if (
            type(execution_evidence)
            is not V075OccurrenceFailureExecutionEvidenceV1
            or execution_evidence.authority_scope
            is not self._open_binding.authority_scope
            or execution_evidence.occurrence_id
            != self._open_binding.occurrence_id
            or execution_evidence.arm is not self._open_binding.arm
        ):
            _fail("failure execution evidence was transplanted")
        _verify_partial_public_prefix(
            open_binding=self._open_binding,
            events=events,
            batches=batches,
            evidence=evidence,
        )
        _verify_work_prefix(
            open_binding=self._open_binding,
            terminal_code=execution_evidence.terminal_code,
            abort_stage=abort_stage,
            execution_evidence=execution_evidence,
            events=events,
            batches=batches,
            evidence=evidence,
        )
        public_values, sequence_values = _expected_batch_verifications(
            batches
        )
        if (
            type(private_replays) is not tuple
            or len(private_replays) != len(batches)
            or {
                item.batch_id for item in private_replays
            }
            != {item.batch_id for item in batches}
            or underlying_closure.session_public_id
            != self._open_binding.session_public_id
            or underlying_closure.authority_binding
            != self._open_binding.observer_open_binding
            or underlying_closure.entries
            or underlying_verification.closure_id
            != underlying_closure.closure_id
            or underlying_verification.observer_open_binding_id
            != self._open_binding.observer_open_binding_id
            or underlying_verification.replayed_record_count != 0
            or underlying_verification.replayed_stream_count != 0
        ):
            _fail("failure lifecycle replay/underlying closure is incomplete")
        signing_values = {
            "open_binding": self._open_binding,
            "terminal_code": execution_evidence.terminal_code,
            "abort_stage": abort_stage,
            "execution_evidence_id": execution_evidence.evidence_id,
            "event_ids": tuple(item.event_id for item in events),
            "batch_ids": tuple(item.batch_id for item in batches),
            "support_evidence_ids": tuple(
                item.evidence_id for item in evidence
            ),
            "public_verification_ids": tuple(
                item.verification_id for item in public_values
            ),
            "sequence_verification_ids": tuple(
                item.verification_id for item in sequence_values
            ),
            "private_replay_verification_ids": tuple(
                item.verification_id
                for item in sorted(
                    private_replays,
                    key=lambda value: value.batch_id,
                )
            ),
            "underlying_closure_id": underlying_closure.closure_id,
            "underlying_closure_verification_id": (
                underlying_verification.verification_id
            ),
        }
        try:
            signature = observer._sign(
                signer=getattr(self._observer_session, "_signer", None),
                expected_key=(
                    self._open_binding.namespace.signer_registry
                    .observer_evidence_key
                ),
                message=occurrence_failure_closure_signing_bytes_v1(
                    **signing_values
                ),
            )
        except observer.V075PrivateObserverBoundaryInvariantViolation as error:
            raise V075OccurrenceFailureLifecycleInvariantViolation(
                str(error)
            ) from error
        closure = V075OccurrenceFailureLifecycleClosureV1(
            _CLOSURE_ISSUER,
            self._open_binding,
            execution_evidence.terminal_code,
            abort_stage,
            execution_evidence,
            events,
            batches,
            evidence,
            public_values,
            sequence_values,
            tuple(
                sorted(private_replays, key=lambda value: value.batch_id)
            ),
            underlying_closure,
            underlying_verification,
            signature,
        )
        verification = _verify_common(closure)
        self._closed = True
        setattr(self._controller, "_closed", True)
        return V075SealedOccurrenceFailureLifecycleV1(
            closure,
            verification,
        )

    def close_construction_v1(
        self,
        *,
        authority: observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1,
        private_environment: (
            batched.V075ConstructionBatchReplayEnvironmentFixtureV1
        ),
        execution_evidence: V075OccurrenceFailureExecutionEvidenceV1,
        abort_stage: str,
    ) -> V075SealedOccurrenceFailureLifecycleV1:
        self._require_live_graph()
        if (
            type(authority)
            is not observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1
            or type(private_environment)
            is not batched
            .V075ConstructionBatchReplayEnvironmentFixtureV1
            or private_environment.namespace != authority.namespace
            or execution_evidence.construction_fixture is not True
            or self._open_binding.authority_scope
            is not lifecycle.V075LifecycleAuthorityScopeV1
            .CONSTRUCTION_ONLY
        ):
            _fail("construction failure close rejects production/duck inputs")
        replays = tuple(
            batched
            .verify_v075_construction_batched_observation_private_replay_v1(
                claimed=item,
                authority=authority,
                private_environment=private_environment,
            )
            for item in self._controller.batches
        )
        _verify_partial_public_prefix(
            open_binding=self._open_binding,
            events=self._controller.events,
            batches=self._controller.batches,
            evidence=self._controller.aggregate_support_evidence,
        )
        _verify_work_prefix(
            open_binding=self._open_binding,
            terminal_code=execution_evidence.terminal_code,
            abort_stage=abort_stage,
            execution_evidence=execution_evidence,
            events=self._controller.events,
            batches=self._controller.batches,
            evidence=self._controller.aggregate_support_evidence,
        )
        underlying_closure = self._observer_session.close_v1()
        underlying_verification = (
            observer.verify_construction_private_observer_journal_closure_v1(
                closure=underlying_closure,
                authority=authority,
                private_salt=private_environment.private_salt,
                private_environment=private_environment.private_environment,
            )
        )
        return self._seal(
            execution_evidence=execution_evidence,
            abort_stage=abort_stage,
            private_replays=replays,
            underlying_closure=underlying_closure,
            underlying_verification=underlying_verification,
        )

    def close_production_v1(
        self,
        *,
        authority: Any,
        namespace: public.V075PublicTargetTapeNamespaceV1,
        private_salt: bytes,
        private_environment: private_env.V075PrivateGeneratedEnvironmentV1,
        execution_evidence: V075OccurrenceFailureExecutionEvidenceV1,
        abort_stage: str,
    ) -> V075SealedOccurrenceFailureLifecycleV1:
        """Production-only close; exact authority typing is downstream."""

        self._require_live_graph()
        if (
            type(namespace) is not public.V075PublicTargetTapeNamespaceV1
            or type(private_environment)
            is not private_env.V075PrivateGeneratedEnvironmentV1
            or namespace != self._open_binding.namespace
            or private_environment.family != namespace.family
            or execution_evidence.construction_fixture is not False
            or self._open_binding.authority_scope
            is not lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
        ):
            _fail("production failure close rejects construction/duck inputs")
        replays = tuple(
            batched
            .verify_v075_production_batched_observation_private_replay_v1(
                claimed=item,
                authority=authority,
                namespace=namespace,
                private_salt=private_salt,
                private_environment=private_environment,
            )
            for item in self._controller.batches
        )
        _verify_partial_public_prefix(
            open_binding=self._open_binding,
            events=self._controller.events,
            batches=self._controller.batches,
            evidence=self._controller.aggregate_support_evidence,
        )
        _verify_work_prefix(
            open_binding=self._open_binding,
            terminal_code=execution_evidence.terminal_code,
            abort_stage=abort_stage,
            execution_evidence=execution_evidence,
            events=self._controller.events,
            batches=self._controller.batches,
            evidence=self._controller.aggregate_support_evidence,
        )
        underlying_closure = self._observer_session.close_v1()
        underlying_verification = (
            observer.verify_private_observer_journal_closure_v1(
                closure=underlying_closure,
                authority=authority,
                namespace=namespace,
                private_salt=private_salt,
                private_environment=(
                    private_environment.secret_laws_for_commitment()
                ),
            )
        )
        return self._seal(
            execution_evidence=execution_evidence,
            abort_stage=abort_stage,
            private_replays=replays,
            underlying_closure=underlying_closure,
            underlying_verification=underlying_verification,
        )


def open_v075_occurrence_failure_lifecycle_authority_v1(
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
) -> V075OccurrenceFailureLifecycleAuthorityV1:
    return V075OccurrenceFailureLifecycleAuthorityV1(
        controller,
        _AUTHORITY_ISSUER,
    )


def verify_v075_construction_occurrence_failure_lifecycle_v1(
    *,
    closure: V075OccurrenceFailureLifecycleClosureV1,
    authority: observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1,
    private_environment: (
        batched.V075ConstructionBatchReplayEnvironmentFixtureV1
    ),
) -> V075OccurrenceFailureLifecycleVerificationV1:
    """Independently replay a construction-only failure closure."""

    if (
        type(closure) is not V075OccurrenceFailureLifecycleClosureV1
        or closure.open_binding.authority_scope
        is not lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
        or closure.execution_evidence.construction_fixture is not True
        or type(authority)
        is not observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1
        or type(private_environment)
        is not batched.V075ConstructionBatchReplayEnvironmentFixtureV1
        or private_environment.namespace != authority.namespace
    ):
        _fail("construction failure verifier rejects production/duck inputs")
    expected_replays = tuple(
        sorted(
            (
                batched
                .verify_v075_construction_batched_observation_private_replay_v1(
                    claimed=item,
                    authority=authority,
                    private_environment=private_environment,
                )
                for item in closure.batches
            ),
            key=lambda item: item.batch_id,
        )
    )
    expected_underlying = (
        observer.verify_construction_private_observer_journal_closure_v1(
            closure=closure.underlying_closure,
            authority=authority,
            private_salt=private_environment.private_salt,
            private_environment=private_environment.private_environment,
        )
    )
    if (
        closure.private_replay_verifications != expected_replays
        or closure.underlying_closure_verification != expected_underlying
    ):
        _fail("construction failure private replay registry differs")
    return _verify_common(closure)


def verify_v075_production_occurrence_failure_lifecycle_v1(
    *,
    closure: V075OccurrenceFailureLifecycleClosureV1,
    authority: Any,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    private_salt: bytes,
    private_environment: private_env.V075PrivateGeneratedEnvironmentV1,
) -> V075OccurrenceFailureLifecycleVerificationV1:
    """Independently replay a production-only failure closure."""

    if (
        type(closure) is not V075OccurrenceFailureLifecycleClosureV1
        or closure.open_binding.authority_scope
        is not lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
        or closure.execution_evidence.construction_fixture is not False
        or type(namespace) is not public.V075PublicTargetTapeNamespaceV1
        or namespace != closure.open_binding.namespace
        or type(private_environment)
        is not private_env.V075PrivateGeneratedEnvironmentV1
        or private_environment.family != namespace.family
    ):
        _fail("production failure verifier rejects construction/duck inputs")
    expected_replays = tuple(
        sorted(
            (
                batched
                .verify_v075_production_batched_observation_private_replay_v1(
                    claimed=item,
                    authority=authority,
                    namespace=namespace,
                    private_salt=private_salt,
                    private_environment=private_environment,
                )
                for item in closure.batches
            ),
            key=lambda item: item.batch_id,
        )
    )
    expected_underlying = observer.verify_private_observer_journal_closure_v1(
        closure=closure.underlying_closure,
        authority=authority,
        namespace=namespace,
        private_salt=private_salt,
        private_environment=private_environment.secret_laws_for_commitment(),
    )
    if (
        closure.private_replay_verifications != expected_replays
        or closure.underlying_closure_verification != expected_underlying
    ):
        _fail("production failure private replay registry differs")
    return _verify_common(closure)


__all__ = [
    "DOMAIN_TAGS",
    "INFEASIBILITY_CERTIFICATE_ALLOWED",
    "PLAN_CERTIFICATE_ALLOWED",
    "PROFILE_KEY",
    "TARGET_EXECUTION_OPENED",
    "TERMINAL_CLASS",
    "V075FailureArtifactReferenceV1",
    "V075FailureArtifactRoleV1",
    "V075OccurrenceFailureActualWorkV1",
    "V075OccurrenceFailureExecutionEvidenceV1",
    "V075OccurrenceFailureLifecycleAuthorityV1",
    "V075OccurrenceFailureLifecycleClosureV1",
    "V075OccurrenceFailureLifecycleInvariantViolation",
    "V075OccurrenceFailureLifecycleVerificationV1",
    "V075OccurrenceFailureTerminalCodeV1",
    "V075SealedOccurrenceFailureLifecycleV1",
    "freeze_v075_production_failure_execution_evidence_v1",
    "issue_v075_construction_failure_execution_fixture_v1",
    "occurrence_failure_closure_signing_bytes_v1",
    "open_v075_occurrence_failure_lifecycle_authority_v1",
    "verify_v075_construction_occurrence_failure_lifecycle_v1",
    "verify_v075_production_occurrence_failure_lifecycle_v1",
]
