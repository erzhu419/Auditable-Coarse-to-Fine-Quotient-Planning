"""Portable construction multiround-result replay authority for V0-075.

Contract 1.81 starts with the exact five-input contract-1.80 replay.  That raw
authority is the first operation.  The current profile is deliberately
narrow: it accepts only the root-only
``CHILD_ACTION_ROW_CAP_EXCEEDED`` terminal path.  The fresh portable bundle
must contain no child-execution, controlled-child, controlled-promotion, or
promotion artifacts.

All producer parents are selected from the fresh 1.80 typed graph.  The owner
replays ROOT_EXECUTION from the exact controlled root prefix and then freezes
the multiround result with every optional child/promotion input explicitly
empty.  The portable MULTIROUND_RESULT target is not used to choose any
parent; it is consulted only for the final byte-and-identity comparison.

This remains an in-memory construction cut.  Private inputs are passed only
to raw 1.80, are not retained or serialized, are not directly hashed here,
and do not produce a secret digest.  Currentness requires another explicit
five-input raw replay.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import heapq
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import (
    v075_observer_signed_multiround_occurrence_runner_v2 as owner,
)
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import (
    v075_portable_construction_closed_reconciliation_authority_v2
    as closed_authority,
)
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.81.0"
PROFILE_KEY = "v075_portable_construction_multiround_result_authority_v2"
ROOT_ONLY_PROFILE_KEY = (
    "v075_root_only_child_action_row_cap_exceeded_replay_v2"
)

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
CONSTRUCTION_EPHEMERAL_PRIVATE_INPUT_REQUIRED = True
CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY_REQUIRED = True
CONSTRUCTION_ROOT_EXECUTION_REPLAYED = True
CONSTRUCTION_MULTIROUND_RESULT_REPLAYED = True
ROOT_ONLY_CAP_PROFILE_REPLAYED = True
PRODUCTION_PRIVATE_INPUT_CHANNEL_ALLOWED = False
PRODUCTION_MULTIROUND_RESULT_ALLOWED = False
B3_INPUT_ALLOWED = False
K7_INPUT_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
J0_ACCESS_ALLOWED = False
OBSERVER_OPEN_ALLOWED = False
WORKER_LAUNCH_ALLOWED = False
OPERATIONAL_REGISTRIES_ALLOWED = False
ACCOUNTING_GATE_PASSED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_MULTIROUND_RESULT_REPLAY_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_MULTIROUND_RESULT_REPLAY_COMPLETE_"
    "PRODUCTION_AND_SCIENCE_GATES_LOCKED"
)
MAX_DEPENDENCY_NODES = 4096
MAX_OUTPUT_BYTES = 64 * 1024 * 1024

ROLE_ORDER = (
    "CONSTRUCTION_PLANNING_INPUT",
    "CLOSED_RECONCILIATION",
    "MULTIROUND_RESULT",
)
SOURCE_ROLE_ORDER = tuple(
    sorted(
        (
            "CLOSED_RECONCILIATION",
            "DYNAMIC_CHILD_CLOSURE",
            "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
            "INITIAL_ACQUISITION_SCHEDULE",
            "INITIAL_ACQUISITION_VERIFICATION",
            "LIVE_MODEL_EPOCH",
            "NUMERICAL_MODEL",
            "NUMERICAL_PLANNING_PROOF",
            "OPEN_CONTROLLED_PREFIX_VERIFICATION",
            "ROOT_EXECUTION",
        )
    )
)
ROOT_ONLY_EMPTY_ROLE_ORDER = tuple(
    sorted(
        (
            "CONTROLLED_CHILD_APPEND",
            "CONTROLLED_CHILD_INTENT",
            "CONTROLLED_CHILD_SEMANTIC_AUTHORITY",
            "CONTROLLED_PROMOTION_APPEND",
            "CONTROLLED_PROMOTION_INTENT",
            "CONTROLLED_PROMOTION_SEMANTIC_AUTHORITY",
            "DYNAMIC_CHILD_DISCOVERY_INTENT",
            "DYNAMIC_CHILD_EXECUTED_ROW",
            "DYNAMIC_CHILD_EXECUTION_LEDGER",
            "DYNAMIC_CHILD_EXECUTION_VERIFICATION",
            "DYNAMIC_CHILD_REPLANNING_BARRIER",
            "DYNAMIC_CHILD_REPLANNING_BARRIER_VERIFICATION",
            "DYNAMIC_CHILD_VALIDATION_TEMPLATE",
            "LIVE_PROMOTION_DECISION",
            "LIVE_PROMOTION_DECISION_VERIFICATION",
            "LIVE_PROMOTION_INTENT",
            "LIVE_PROMOTION_REPLANNING_BARRIER",
            "LIVE_PROMOTION_REPLANNING_BARRIER_VERIFICATION",
        )
    )
)
_ROLE_SET = frozenset(ROLE_ORDER)
_SOURCE_ROLE_SET = frozenset(SOURCE_ROLE_ORDER)
_EMPTY_ROLE_SET = frozenset(ROOT_ONLY_EMPTY_ROLE_ORDER)

DOMAIN_TAGS = MappingProxyType(
    {
        "empty_role_registry": (
            "acfqp:v075-portable-construction-root-only-empty-roles:v2"
        ),
        "source_binding": (
            "acfqp:v075-portable-construction-multiround-result-source:v2"
        ),
        "typed_graph": (
            "acfqp:v075-portable-construction-multiround-result-graph:v2"
        ),
        "dependency_dag": (
            "acfqp:v075-portable-construction-multiround-result-dag:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-construction-multiround-result-closure:v2"
        ),
        "aggregate": (
            "acfqp:v075-portable-construction-multiround-result-authority:v2"
        ),
    }
)

_REPLAY_MISMATCH = (
    "construction multiround-result replay did not match registered evidence"
)


class V075PortableConstructionMultiroundResultV2InvariantViolation(
    ValueError
):
    """Raw replay, owner replay, root-only profile, or DAG closure failed."""


class V075PortableConstructionMultiroundResultProductionV2NotReady(
    RuntimeError
):
    """Contract 1.81 cannot authorize a production occurrence."""


class V075ConstructionMultiroundResultRoleStatusV2(str, Enum):
    FULL_CONSTRUCTION_COMPILER_REPLAY = (
        "FULL_CONSTRUCTION_COMPILER_REPLAY"
    )
    FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY = (
        "FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY"
    )
    FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY = (
        "FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY"
    )


class V075ConstructionMultiroundResultResolverKindV2(str, Enum):
    UPSTREAM_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY = (
        "UPSTREAM_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY"
    )
    CONSTRUCTION_MULTIROUND_RESULT_OWNER_REPLAY = (
        "CONSTRUCTION_MULTIROUND_RESULT_OWNER_REPLAY"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


class V075ConstructionMultiroundResultAuthorityScopeV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    FULL_CONSTRUCTION_PRIVATE_REPLAY = (
        "FULL_CONSTRUCTION_PRIVATE_REPLAY"
    )
    FULL_CONSTRUCTION_COMPILER_REPLAY = (
        "FULL_CONSTRUCTION_COMPILER_REPLAY"
    )
    FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY = (
        "FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY"
    )
    FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY = (
        "FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY"
    )
    FULL_CONSTRUCTION_TRANSITIVE = "FULL_CONSTRUCTION_TRANSITIVE"
    UNRESOLVED = "UNRESOLVED"


def _fail(message: str) -> NoReturn:
    raise V075PortableConstructionMultiroundResultV2InvariantViolation(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise (
            V075PortableConstructionMultiroundResultV2InvariantViolation(
                f"{label} must be one lowercase SHA-256 content ID"
            )
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise (
            V075PortableConstructionMultiroundResultV2InvariantViolation(
                "multiround-result public identity is malformed"
            )
        ) from error


def _raw(value: Any) -> bytes:
    return canonical_json_bytes(value.to_document())


def _portable_record(
    records: tuple[Any, ...],
    *,
    role: str,
    semantic_id: str | None = None,
    expected_raw: bytes | None = None,
    label: str,
) -> Any:
    if type(records) is not tuple:
        _fail(f"{label} registry is malformed")
    if semantic_id is not None:
        semantic_id = _cid(semantic_id, label)
    matches = tuple(
        item
        for item in records
        if getattr(item, "role", None) == role
        and (
            semantic_id is None
            or getattr(item, "semantic_artifact_id", None) == semantic_id
        )
    )
    if len(matches) != 1:
        _fail(f"{label} is absent, duplicated, or role-transplanted")
    record = matches[0]
    if (
        expected_raw is not None
        and getattr(record, "canonical_artifact_bytes", None) != expected_raw
    ):
        _fail(f"{label} bytes differ from the exact producer")
    return record


def _unique_by_id(
    values: tuple[Any, ...],
    *,
    semantic_id: str,
    identity_attribute: str,
    label: str,
) -> Any:
    semantic_id = _cid(semantic_id, label)
    matches = tuple(
        item
        for item in values
        if getattr(item, identity_attribute, None) == semantic_id
    )
    if len(matches) != 1:
        _fail(f"{label} is absent or duplicated")
    return matches[0]


_EMPTY_REGISTRY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionRootOnlyEmptyRoleRegistryV2:
    _issuer: InitVar[object]
    portable_bundle_id: str
    roles: tuple[str, ...]
    role_counts: tuple[tuple[str, int], ...]
    _registry_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _EMPTY_REGISTRY_ISSUER:
            _fail("root-only empty-role registry is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_registry_id",
            _hash("empty_role_registry", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.portable_bundle_id, "root-only empty-role bundle")
        if (
            type(self.roles) is not tuple
            or self.roles != ROOT_ONLY_EMPTY_ROLE_ORDER
            or type(self.role_counts) is not tuple
            or self.role_counts != tuple((role, 0) for role in self.roles)
            or any(role not in portable.ROLE_SCHEMA_REGISTRY for role in self.roles)
        ):
            _fail("root-only empty-role registry is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_root_only_empty_role_registry.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "root_only_profile_key": ROOT_ONLY_PROFILE_KEY,
            "portable_bundle_id": self.portable_bundle_id,
            "roles": list(self.roles),
            "role_counts": [
                {"role": role, "count": count}
                for role, count in self.role_counts
            ],
            "fresh_bundle_role_absence_verified": True,
            "caller_claimed_nulls_used_as_absence_evidence": False,
        }

    @property
    def registry_id(self) -> str:
        self._validate()
        if self._registry_id != _hash(
            "empty_role_registry",
            self._payload(),
        ):
            _fail("root-only empty-role registry identity is stale")
        return self._registry_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("root-only empty-role registry is in-memory-only")


def _freeze_empty_role_registry(
    *,
    bundle: portable.V075PortableOccurrenceEvidenceBundleV2,
) -> V075ConstructionRootOnlyEmptyRoleRegistryV2:
    if (
        type(bundle)
        is not portable.V075PortableOccurrenceEvidenceBundleV2
    ):
        _fail("root-only profile requires one exact fresh portable bundle")
    counts = tuple(
        (
            role,
            sum(item.role == role for item in bundle.records),
        )
        for role in ROOT_ONLY_EMPTY_ROLE_ORDER
    )
    if any(count != 0 for _role, count in counts):
        _fail("root-only profile contains child or promotion work")
    return V075ConstructionRootOnlyEmptyRoleRegistryV2(
        _EMPTY_REGISTRY_ISSUER,
        bundle.bundle_id,
        ROOT_ONLY_EMPTY_ROLE_ORDER,
        counts,
    )


def _exact_chain(
    replayed: (
        closed_authority
        .V075PortableConstructionClosedReconciliationReplayV2
    ),
) -> tuple[Any, ...]:
    """Extract every root-only parent from the fresh 1.80 typed graph."""

    if (
        type(replayed)
        is not closed_authority
        .V075PortableConstructionClosedReconciliationReplayV2
    ):
        _fail("multiround result requires exact raw contract 1.80")
    _ = replayed.result_id
    try:
        closed_graph = replayed.typed_graph
        input_replay = closed_graph.planning_input_replay
        input_graph = input_replay.typed_graph
        private_result = input_graph.private_replay_result
        hardened = private_result.typed_graph.hardened_planning_result
        dynamic_result = hardened.typed_graph.m2_dynamic_child_result
        dynamic_graph = dynamic_result.typed_graph
        live_result = dynamic_graph.m2_live_epoch_result
        lifecycle_result = live_result.typed_graph.m2_lifecycle_result
        lineage_result = lifecycle_result.typed_graph.m2_lineage_result
        root_result = lineage_result.typed_graph.m2_result
        root_graph = root_result.typed_graph
        m1b_result = root_graph.m1b_result
        m1b_graph = m1b_result.typed_graph
        m1a_graph = m1b_graph.m1a_result.typed_graph
        m0_graph = m1a_graph.m0_result.typed_graph
        schedule = m0_graph.schedule
        schedule_verification = m0_graph.verification
        namespace = (
            private_result.typed_graph.public_context_resolution.namespace
        )
        controlled_namespace = (
            m1b_graph.controlled_closure.batch_closure.authority_binding
            .namespace
        )
        root_view = root_graph.root_execution
        prefix = _unique_by_id(
            m1b_graph.open_prefixes,
            semantic_id=root_view.open_prefix_verification_id,
            identity_attribute="verification_id",
            label="root-only controlled root prefix",
        )
        child_closure = dynamic_graph.closure
        child_verification = dynamic_graph.verification
        root_epoch = child_closure.source_epoch
        final_epoch = closed_graph.final_epoch
        final_model = closed_graph.final_model
        final_proof = closed_graph.final_proof
        reconciliation = closed_graph.reconciliation
    except (
        AttributeError,
        TypeError,
        V075PortableConstructionMultiroundResultV2InvariantViolation,
    ) as error:
        if (
            type(error)
            is V075PortableConstructionMultiroundResultV2InvariantViolation
        ):
            raise
        raise (
            V075PortableConstructionMultiroundResultV2InvariantViolation(
                "contract 1.80 omitted its exact root-only producer graph"
            )
        ) from error
    if (
        type(schedule) is not acquisition.V075InitialAcquisitionScheduleV2
        or type(schedule_verification)
        is not acquisition.V075InitialAcquisitionVerificationV2
        or type(namespace) is not namespace_v2.V075PublicTargetTapeNamespaceV2
        or type(controlled_namespace)
        is not namespace_v2.V075PublicTargetTapeNamespaceV2
        or namespace.target_tape_namespace_id
        != controlled_namespace.target_tape_namespace_id
        or namespace.canonical_bytes != controlled_namespace.canonical_bytes
        or type(prefix)
        is not control.V075OpenControlledBatchPrefixVerificationV2
        or type(root_epoch)
        is not live_model.V075LiveIncrementalModelEpochV2
        or type(final_epoch)
        is not live_model.V075LiveIncrementalModelEpochV2
        or type(final_model) is not planning.V075NumericalModelV2
        or type(final_proof)
        is not planning.V075NumericalPlanningProofV2
        or type(child_closure)
        is not dynamic.V075LiveDynamicChildClosureV2
        or type(child_verification)
        is not dynamic.V075LiveDynamicChildClosureVerificationV2
        or type(reconciliation)
        is not owner.V075ObserverSignedClosedReconciliationV2
        or schedule is not closed_graph.schedule
        or schedule.occurrence.occurrence_id != replayed.occurrence_id
        or schedule_verification.schedule_id != schedule.schedule_id
        or schedule_verification.occurrence_id != replayed.occurrence_id
        or namespace.target_tape_namespace_id
        != schedule.occurrence.target_tape_namespace_id
        or child_closure.status
        is not (
            dynamic.V075LiveDynamicChildClosureStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        )
        or child_verification.status is not child_closure.status
        or child_verification.closure_id != child_closure.closure_id
        or child_closure.discovery_intents
        or child_closure.validation_templates
        or root_epoch.model_epoch_id != final_epoch.model_epoch_id
        or _raw(root_epoch) != _raw(final_epoch)
        or final_epoch.model.model_id != final_model.model_id
        or _raw(final_epoch.model) != _raw(final_model)
        or final_epoch.proof.proof_id != final_proof.proof_id
        or _raw(final_epoch.proof) != _raw(final_proof)
        or reconciliation.final_epoch.model_epoch_id
        != final_epoch.model_epoch_id
        or _raw(reconciliation.final_epoch) != _raw(final_epoch)
        or prefix.verification_id
        != root_epoch.open_prefix_verification.verification_id
        or _raw(prefix) != _raw(root_epoch.open_prefix_verification)
        or prefix.heads != m1b_graph.controlled_closure.heads
        or prefix.appends != m1b_graph.controlled_closure.appends
        or prefix.support_freezes
        != m1b_graph.controlled_closure.support_freezes
        or prefix.current_head_id
        != m1b_graph.controlled_closure.control_closure.final_head_id
    ):
        _fail("contract 1.80 is not the exact root-only cap profile")
    return (
        hardened,
        root_graph,
        m1b_graph,
        dynamic_graph,
        schedule,
        schedule_verification,
        namespace,
        prefix,
        root_view,
        root_epoch,
        child_closure,
        child_verification,
        final_epoch,
        final_model,
        final_proof,
        reconciliation,
    )


def _exact_portable_sources(
    *,
    records: tuple[Any, ...],
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    schedule_verification: acquisition.V075InitialAcquisitionVerificationV2,
    prefix: control.V075OpenControlledBatchPrefixVerificationV2,
    root_execution: owner.V075ObserverSignedRootExecutionV2,
    root_epoch: live_model.V075LiveIncrementalModelEpochV2,
    child_closure: dynamic.V075LiveDynamicChildClosureV2,
    child_verification: dynamic.V075LiveDynamicChildClosureVerificationV2,
    final_model: planning.V075NumericalModelV2,
    final_proof: planning.V075NumericalPlanningProofV2,
    reconciliation: owner.V075ObserverSignedClosedReconciliationV2,
) -> tuple[Any, ...]:
    values = (
        _portable_record(
            records,
            role="CLOSED_RECONCILIATION",
            semantic_id=reconciliation.reconciliation_id,
            expected_raw=_raw(reconciliation),
            label="multiround closed reconciliation source",
        ),
        _portable_record(
            records,
            role="DYNAMIC_CHILD_CLOSURE",
            semantic_id=child_closure.closure_id,
            expected_raw=_raw(child_closure),
            label="multiround child closure source",
        ),
        _portable_record(
            records,
            role="DYNAMIC_CHILD_CLOSURE_VERIFICATION",
            semantic_id=child_verification.verification_id,
            expected_raw=_raw(child_verification),
            label="multiround child verification source",
        ),
        _portable_record(
            records,
            role="INITIAL_ACQUISITION_SCHEDULE",
            semantic_id=schedule.schedule_id,
            expected_raw=_raw(schedule),
            label="multiround schedule source",
        ),
        _portable_record(
            records,
            role="INITIAL_ACQUISITION_VERIFICATION",
            semantic_id=schedule_verification.verification_id,
            expected_raw=_raw(schedule_verification),
            label="multiround schedule verification source",
        ),
        _portable_record(
            records,
            role="LIVE_MODEL_EPOCH",
            semantic_id=root_epoch.model_epoch_id,
            expected_raw=_raw(root_epoch),
            label="multiround root/final epoch source",
        ),
        _portable_record(
            records,
            role="NUMERICAL_MODEL",
            semantic_id=final_model.model_id,
            expected_raw=_raw(final_model),
            label="multiround final model source",
        ),
        _portable_record(
            records,
            role="NUMERICAL_PLANNING_PROOF",
            semantic_id=final_proof.proof_id,
            expected_raw=_raw(final_proof),
            label="multiround final proof source",
        ),
        _portable_record(
            records,
            role="OPEN_CONTROLLED_PREFIX_VERIFICATION",
            semantic_id=prefix.verification_id,
            expected_raw=_raw(prefix),
            label="multiround root prefix source",
        ),
        _portable_record(
            records,
            role="ROOT_EXECUTION",
            semantic_id=root_execution.execution_id,
            expected_raw=_raw(root_execution),
            label="multiround root execution source",
        ),
    )
    by_role = {item.role: item for item in values}
    if set(by_role) != _SOURCE_ROLE_SET or len(by_role) != len(values):
        _fail("multiround source registry is incomplete")
    return tuple(by_role[role] for role in SOURCE_ROLE_ORDER)


_SOURCE_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionMultiroundResultSourceBindingV2:
    _issuer: InitVar[object]
    target_record_id: str
    target_semantic_artifact_id: str
    source_records: tuple[tuple[str, str], ...]
    portable_bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    closed_replay_result_id: str
    empty_role_registry_id: str
    target_tape_namespace_id: str
    schedule_id: str
    schedule_verification_id: str
    controlled_root_prefix_verification_id: str
    root_execution_id: str
    root_model_epoch_id: str
    child_closure_id: str
    child_closure_verification_id: str
    final_numerical_model_id: str
    final_proof_id: str
    closed_reconciliation_id: str
    producer_artifact_sha256: str
    producer_artifact_byte_count: int
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_BINDING_ISSUER:
            _fail("multiround-result source is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_binding_id",
            _hash("source_binding", self._payload()),
        )

    @property
    def source_dependency_record_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(record_id for _role, record_id in self.source_records)
        )

    def _validate(self) -> None:
        for value, label in (
            (self.target_record_id, "multiround target record"),
            (
                self.target_semantic_artifact_id,
                "multiround target semantic artifact",
            ),
            (self.portable_bundle_id, "multiround portable bundle"),
            (self.occurrence_id, "multiround occurrence"),
            (self.public_context_closure_id, "multiround context"),
            (self.closed_replay_result_id, "multiround upstream replay"),
            (self.empty_role_registry_id, "multiround empty roles"),
            (self.target_tape_namespace_id, "multiround namespace"),
            (self.schedule_id, "multiround schedule"),
            (
                self.schedule_verification_id,
                "multiround schedule verification",
            ),
            (
                self.controlled_root_prefix_verification_id,
                "multiround root prefix",
            ),
            (self.root_execution_id, "multiround root execution"),
            (self.root_model_epoch_id, "multiround root epoch"),
            (self.child_closure_id, "multiround child closure"),
            (
                self.child_closure_verification_id,
                "multiround child verification",
            ),
            (self.final_numerical_model_id, "multiround final model"),
            (self.final_proof_id, "multiround final proof"),
            (
                self.closed_reconciliation_id,
                "multiround closed reconciliation",
            ),
            (
                self.producer_artifact_sha256,
                "multiround result bytes",
            ),
        ):
            _cid(value, label)
        if (
            type(self.source_records) is not tuple
            or tuple(sorted(self.source_records)) != self.source_records
            or tuple(role for role, _record_id in self.source_records)
            != SOURCE_ROLE_ORDER
            or len({record_id for _role, record_id in self.source_records})
            != len(self.source_records)
            or any(
                role not in _SOURCE_ROLE_SET
                for role, _record_id in self.source_records
            )
            or any(
                role == "MULTIROUND_RESULT"
                for role, _record_id in self.source_records
            )
            or type(self.producer_artifact_byte_count) is not int
            or self.producer_artifact_byte_count <= 0
        ):
            _fail("multiround-result source binding is malformed")
        for _role, record_id in self.source_records:
            _cid(record_id, "multiround source record")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_multiround_result_source_binding.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "root_only_profile_key": ROOT_ONLY_PROFILE_KEY,
            "target_record_id": self.target_record_id,
            "target_role": "MULTIROUND_RESULT",
            "target_semantic_artifact_id": (
                self.target_semantic_artifact_id
            ),
            "resolver_kind": (
                V075ConstructionMultiroundResultResolverKindV2
                .CONSTRUCTION_MULTIROUND_RESULT_OWNER_REPLAY.value
            ),
            "source_records": [
                {"role": role, "record_id": record_id}
                for role, record_id in self.source_records
            ],
            "source_dependency_record_ids": list(
                self.source_dependency_record_ids
            ),
            "portable_bundle_id": self.portable_bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "closed_replay_result_id": self.closed_replay_result_id,
            "empty_role_registry_id": self.empty_role_registry_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "schedule_id": self.schedule_id,
            "schedule_verification_id": self.schedule_verification_id,
            "controlled_root_prefix_verification_id": (
                self.controlled_root_prefix_verification_id
            ),
            "root_execution_id": self.root_execution_id,
            "root_model_epoch_id": self.root_model_epoch_id,
            "child_closure_id": self.child_closure_id,
            "child_closure_verification_id": (
                self.child_closure_verification_id
            ),
            "final_numerical_model_id": self.final_numerical_model_id,
            "final_proof_id": self.final_proof_id,
            "closed_reconciliation_id": self.closed_reconciliation_id,
            "producer_artifact_sha256": self.producer_artifact_sha256,
            "producer_artifact_byte_count": self.producer_artifact_byte_count,
            "target_used_only_for_final_comparison": True,
            "child_optional_inputs_empty": True,
            "promotion_inputs_empty": True,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
        }

    @property
    def binding_id(self) -> str:
        self._validate()
        if self._binding_id != _hash("source_binding", self._payload()):
            _fail("multiround-result source identity is stale")
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("multiround-result source is in-memory-only")


def _build_source_binding(
    *,
    replayed: (
        closed_authority
        .V075PortableConstructionClosedReconciliationReplayV2
    ),
    target_record: portable.V075PortableEvidenceArtifactRecordV2,
    source_records: tuple[
        portable.V075PortableEvidenceArtifactRecordV2, ...
    ],
    empty_registry: V075ConstructionRootOnlyEmptyRoleRegistryV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    schedule_verification: acquisition.V075InitialAcquisitionVerificationV2,
    prefix: control.V075OpenControlledBatchPrefixVerificationV2,
    root_execution: owner.V075ObserverSignedRootExecutionV2,
    root_epoch: live_model.V075LiveIncrementalModelEpochV2,
    child_closure: dynamic.V075LiveDynamicChildClosureV2,
    child_verification: dynamic.V075LiveDynamicChildClosureVerificationV2,
    final_model: planning.V075NumericalModelV2,
    final_proof: planning.V075NumericalPlanningProofV2,
    reconciliation: owner.V075ObserverSignedClosedReconciliationV2,
    result: owner.V075ObserverSignedMultiroundResultV2,
) -> V075ConstructionMultiroundResultSourceBindingV2:
    by_role = {item.role: item for item in source_records}
    if (
        type(target_record)
        is not portable.V075PortableEvidenceArtifactRecordV2
        or any(
            type(item)
            is not portable.V075PortableEvidenceArtifactRecordV2
            for item in source_records
        )
        or tuple(by_role) != SOURCE_ROLE_ORDER
    ):
        _fail("multiround portable source records are not exact")
    raw = _raw(result)
    return V075ConstructionMultiroundResultSourceBindingV2(
        _SOURCE_BINDING_ISSUER,
        target_record.record_id,
        target_record.semantic_artifact_id,
        tuple((item.role, item.record_id) for item in source_records),
        replayed.bundle_id,
        replayed.occurrence_id,
        replayed.public_context_closure_id,
        replayed.result_id,
        empty_registry.registry_id,
        namespace.target_tape_namespace_id,
        schedule.schedule_id,
        schedule_verification.verification_id,
        prefix.verification_id,
        root_execution.execution_id,
        root_epoch.model_epoch_id,
        child_closure.closure_id,
        child_verification.verification_id,
        final_model.model_id,
        final_proof.proof_id,
        reconciliation.reconciliation_id,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionMultiroundResultTypedGraphV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    closed_replay: (
        closed_authority
        .V075PortableConstructionClosedReconciliationReplayV2
    ) = field(repr=False)
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2 = field(
        repr=False
    )
    schedule: acquisition.V075InitialAcquisitionScheduleV2 = field(
        repr=False
    )
    schedule_verification: acquisition.V075InitialAcquisitionVerificationV2 = (
        field(repr=False)
    )
    controlled_root_prefix: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ) = field(repr=False)
    root_execution: owner.V075ObserverSignedRootExecutionV2 = field(
        repr=False
    )
    root_epoch: live_model.V075LiveIncrementalModelEpochV2 = field(
        repr=False
    )
    child_closure: dynamic.V075LiveDynamicChildClosureV2 = field(
        repr=False
    )
    child_closure_verification: (
        dynamic.V075LiveDynamicChildClosureVerificationV2
    ) = field(repr=False)
    final_epoch: live_model.V075LiveIncrementalModelEpochV2 = field(
        repr=False
    )
    final_model: planning.V075NumericalModelV2 = field(repr=False)
    final_proof: planning.V075NumericalPlanningProofV2 = field(repr=False)
    reconciliation: owner.V075ObserverSignedClosedReconciliationV2 = field(
        repr=False
    )
    multiround_result: owner.V075ObserverSignedMultiroundResultV2 = field(
        repr=False
    )
    target_record: portable.V075PortableEvidenceArtifactRecordV2 = field(
        repr=False
    )
    source_records: tuple[
        portable.V075PortableEvidenceArtifactRecordV2, ...
    ] = field(repr=False)
    empty_role_registry: V075ConstructionRootOnlyEmptyRoleRegistryV2
    source_binding: V075ConstructionMultiroundResultSourceBindingV2
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("multiround-result graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "multiround graph bundle"),
            (self.occurrence_id, "multiround graph occurrence"),
            (self.public_context_closure_id, "multiround graph context"),
        ):
            _cid(value, label)
        if (
            type(self.closed_replay)
            is not closed_authority
            .V075PortableConstructionClosedReconciliationReplayV2
            or type(self.namespace)
            is not namespace_v2.V075PublicTargetTapeNamespaceV2
            or type(self.schedule)
            is not acquisition.V075InitialAcquisitionScheduleV2
            or type(self.schedule_verification)
            is not acquisition.V075InitialAcquisitionVerificationV2
            or type(self.controlled_root_prefix)
            is not control.V075OpenControlledBatchPrefixVerificationV2
            or type(self.root_execution)
            is not owner.V075ObserverSignedRootExecutionV2
            or type(self.root_epoch)
            is not live_model.V075LiveIncrementalModelEpochV2
            or type(self.child_closure)
            is not dynamic.V075LiveDynamicChildClosureV2
            or type(self.child_closure_verification)
            is not dynamic.V075LiveDynamicChildClosureVerificationV2
            or type(self.final_epoch)
            is not live_model.V075LiveIncrementalModelEpochV2
            or type(self.final_model) is not planning.V075NumericalModelV2
            or type(self.final_proof)
            is not planning.V075NumericalPlanningProofV2
            or type(self.reconciliation)
            is not owner.V075ObserverSignedClosedReconciliationV2
            or type(self.multiround_result)
            is not owner.V075ObserverSignedMultiroundResultV2
            or type(self.target_record)
            is not portable.V075PortableEvidenceArtifactRecordV2
            or type(self.source_records) is not tuple
            or any(
                type(item)
                is not portable.V075PortableEvidenceArtifactRecordV2
                for item in self.source_records
            )
            or type(self.empty_role_registry)
            is not V075ConstructionRootOnlyEmptyRoleRegistryV2
            or type(self.source_binding)
            is not V075ConstructionMultiroundResultSourceBindingV2
        ):
            _fail("multiround-result graph is malformed")
        _ = self.closed_replay.result_id
        _ = self.empty_role_registry.registry_id
        _ = self.source_binding.binding_id
        (
            _hardened,
            _root_graph,
            _m1b_graph,
            _dynamic_graph,
            exact_schedule,
            exact_schedule_verification,
            exact_namespace,
            exact_prefix,
            root_view,
            exact_root_epoch,
            exact_child_closure,
            exact_child_verification,
            exact_final_epoch,
            exact_final_model,
            exact_final_proof,
            exact_reconciliation,
        ) = _exact_chain(self.closed_replay)
        raw_result = _raw(self.multiround_result)
        source_by_role = {item.role: item for item in self.source_records}
        claimed_sources = dict(self.source_binding.source_records)
        if (
            len(source_by_role) != len(self.source_records)
            or tuple(source_by_role) != SOURCE_ROLE_ORDER
            or set(claimed_sources) != _SOURCE_ROLE_SET
            or any(
                claimed_sources[role] != source_by_role[role].record_id
                for role in SOURCE_ROLE_ORDER
            )
            or self.closed_replay.bundle_id != self.bundle_id
            or self.closed_replay.occurrence_id != self.occurrence_id
            or self.closed_replay.public_context_closure_id
            != self.public_context_closure_id
            or self.namespace is not exact_namespace
            or self.schedule is not exact_schedule
            or self.schedule_verification is not exact_schedule_verification
            or self.controlled_root_prefix is not exact_prefix
            or self.root_epoch is not exact_root_epoch
            or self.child_closure is not exact_child_closure
            or self.child_closure_verification
            is not exact_child_verification
            or self.final_epoch is not exact_final_epoch
            or self.final_model is not exact_final_model
            or self.final_proof is not exact_final_proof
            or self.reconciliation is not exact_reconciliation
            or self.empty_role_registry.portable_bundle_id != self.bundle_id
            or self.source_binding.portable_bundle_id != self.bundle_id
            or self.source_binding.occurrence_id != self.occurrence_id
            or self.source_binding.public_context_closure_id
            != self.public_context_closure_id
            or self.source_binding.closed_replay_result_id
            != self.closed_replay.result_id
            or self.source_binding.empty_role_registry_id
            != self.empty_role_registry.registry_id
            or self.root_execution.execution_id != root_view.execution_id
            or _raw(self.root_execution) != root_view.canonical_bytes
            or self.target_record.role != "MULTIROUND_RESULT"
            or self.target_record.record_id
            != self.source_binding.target_record_id
            or self.target_record.semantic_artifact_id
            != self.multiround_result.result_id
            or self.target_record.semantic_artifact_id
            != self.source_binding.target_semantic_artifact_id
            or self.target_record.canonical_artifact_bytes != raw_result
            or self.source_binding.producer_artifact_sha256
            != hashlib.sha256(raw_result).hexdigest()
            or self.source_binding.producer_artifact_byte_count
            != len(raw_result)
        ):
            _fail("multiround-result graph crossed exact producer identities")
        if (
            self.multiround_result.status
            is not (
                owner.V075ObserverSignedMultiroundTerminalStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            )
            or self.multiround_result.child_closure_status
            is not (
                dynamic.V075LiveDynamicChildClosureStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            )
            or self.multiround_result.child_execution_ledger_id is not None
            or self.multiround_result.child_execution_verification_id
            is not None
            or self.multiround_result.child_replanning_barrier_id is not None
            or (
                self.multiround_result
                .child_replanning_barrier_verification_id
                is not None
            )
            or self.multiround_result.promotion_decision_ids
            or self.multiround_result.promotion_decision_verification_ids
            or self.multiround_result.promotion_replanning_barrier_ids
            or (
                self.multiround_result
                .promotion_replanning_barrier_verification_ids
            )
        ):
            _fail("owner multiround result is not the root-only cap profile")
        expected_raw_by_role = {
            "CLOSED_RECONCILIATION": _raw(self.reconciliation),
            "DYNAMIC_CHILD_CLOSURE": _raw(self.child_closure),
            "DYNAMIC_CHILD_CLOSURE_VERIFICATION": _raw(
                self.child_closure_verification
            ),
            "INITIAL_ACQUISITION_SCHEDULE": _raw(self.schedule),
            "INITIAL_ACQUISITION_VERIFICATION": _raw(
                self.schedule_verification
            ),
            "LIVE_MODEL_EPOCH": _raw(self.root_epoch),
            "NUMERICAL_MODEL": _raw(self.final_model),
            "NUMERICAL_PLANNING_PROOF": _raw(self.final_proof),
            "OPEN_CONTROLLED_PREFIX_VERIFICATION": _raw(
                self.controlled_root_prefix
            ),
            "ROOT_EXECUTION": _raw(self.root_execution),
        }
        expected_semantic_by_role = {
            "CLOSED_RECONCILIATION": self.reconciliation.reconciliation_id,
            "DYNAMIC_CHILD_CLOSURE": self.child_closure.closure_id,
            "DYNAMIC_CHILD_CLOSURE_VERIFICATION": (
                self.child_closure_verification.verification_id
            ),
            "INITIAL_ACQUISITION_SCHEDULE": self.schedule.schedule_id,
            "INITIAL_ACQUISITION_VERIFICATION": (
                self.schedule_verification.verification_id
            ),
            "LIVE_MODEL_EPOCH": self.root_epoch.model_epoch_id,
            "NUMERICAL_MODEL": self.final_model.model_id,
            "NUMERICAL_PLANNING_PROOF": self.final_proof.proof_id,
            "OPEN_CONTROLLED_PREFIX_VERIFICATION": (
                self.controlled_root_prefix.verification_id
            ),
            "ROOT_EXECUTION": self.root_execution.execution_id,
        }
        if any(
            source_by_role[role].canonical_artifact_bytes
            != expected_raw_by_role[role]
            or source_by_role[role].semantic_artifact_id
            != expected_semantic_by_role[role]
            for role in SOURCE_ROLE_ORDER
        ):
            _fail("multiround-result source record was transplanted")
        if (
            self.source_binding.target_tape_namespace_id
            != self.namespace.target_tape_namespace_id
            or self.source_binding.schedule_id != self.schedule.schedule_id
            or self.source_binding.schedule_verification_id
            != self.schedule_verification.verification_id
            or self.source_binding.controlled_root_prefix_verification_id
            != self.controlled_root_prefix.verification_id
            or self.source_binding.root_execution_id
            != self.root_execution.execution_id
            or self.source_binding.root_model_epoch_id
            != self.root_epoch.model_epoch_id
            or self.source_binding.child_closure_id
            != self.child_closure.closure_id
            or self.source_binding.child_closure_verification_id
            != self.child_closure_verification.verification_id
            or self.source_binding.final_numerical_model_id
            != self.final_model.model_id
            or self.source_binding.final_proof_id
            != self.final_proof.proof_id
            or self.source_binding.closed_reconciliation_id
            != self.reconciliation.reconciliation_id
        ):
            _fail("multiround-result source claim changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_multiround_result_typed_graph.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "root_only_profile_key": ROOT_ONLY_PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "closed_replay_result_id": self.closed_replay.result_id,
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "schedule_id": self.schedule.schedule_id,
            "schedule_verification_id": (
                self.schedule_verification.verification_id
            ),
            "controlled_root_prefix_verification_id": (
                self.controlled_root_prefix.verification_id
            ),
            "root_execution_id": self.root_execution.execution_id,
            "root_model_epoch_id": self.root_epoch.model_epoch_id,
            "child_closure_id": self.child_closure.closure_id,
            "child_closure_verification_id": (
                self.child_closure_verification.verification_id
            ),
            "final_model_epoch_id": self.final_epoch.model_epoch_id,
            "final_numerical_model_id": self.final_model.model_id,
            "final_proof_id": self.final_proof.proof_id,
            "closed_reconciliation_id": (
                self.reconciliation.reconciliation_id
            ),
            "multiround_result_id": self.multiround_result.result_id,
            "target_record_id": self.target_record.record_id,
            "ordered_source_record_ids": [
                item.record_id for item in self.source_records
            ],
            "empty_role_registry_id": (
                self.empty_role_registry.registry_id
            ),
            "source_binding_id": self.source_binding.binding_id,
            "owner_root_execution_replayed": True,
            "owner_multiround_result_replayed": True,
            "target_used_only_for_final_comparison": True,
            "root_epoch_equals_final_epoch": True,
            "child_optional_inputs_empty": True,
            "promotion_inputs_empty": True,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
        }

    @property
    def graph_id(self) -> str:
        self._validate()
        if self._graph_id != _hash("typed_graph", self._payload()):
            _fail("multiround-result graph identity is stale")
        return self._graph_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "typed_graph_id": self.graph_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("multiround-result graph is in-memory-only")


@dataclass(frozen=True, slots=True)
class V075ConstructionMultiroundResultDependencyNodeV2:
    record_id: str
    record_index: int
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    source_binding_id: str | None
    resolver_kind: V075ConstructionMultiroundResultResolverKindV2
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    authority_scope: V075ConstructionMultiroundResultAuthorityScopeV2
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    dependency_depth: int

    def __post_init__(self) -> None:
        _cid(self.record_id, "multiround dependency node")
        sequences = (
            self.portable_declared_dependency_record_ids,
            self.authority_local_semantic_dependency_record_ids,
            self.effective_dependency_record_ids,
            self.unresolved_frontier_record_ids,
            self.unresolved_frontier_roles,
        )
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in sequences
            )
            or set(self.effective_dependency_record_ids)
            != set(self.portable_declared_dependency_record_ids)
            | set(self.authority_local_semantic_dependency_record_ids)
            or type(self.resolver_kind)
            is not V075ConstructionMultiroundResultResolverKindV2
            or type(self.local_semantic_authority_resolved) is not bool
            or type(self.semantically_resolved) is not bool
            or type(self.authority_scope)
            is not V075ConstructionMultiroundResultAuthorityScopeV2
            or type(self.dependency_depth) is not int
            or not 0 < self.dependency_depth <= MAX_DEPENDENCY_NODES
            or self.semantically_resolved
            != (
                self.authority_scope
                is not V075ConstructionMultiroundResultAuthorityScopeV2
                .UNRESOLVED
            )
            or (
                self.semantically_resolved
                and (
                    self.unresolved_frontier_record_ids
                    or self.unresolved_frontier_roles
                )
            )
            or (
                not self.semantically_resolved
                and not self.unresolved_frontier_record_ids
            )
        ):
            _fail("multiround dependency node is malformed")
        if self.source_binding_id is not None:
            _cid(self.source_binding_id, "multiround dependency source")
        for value in (
            *self.effective_dependency_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "multiround dependency edge")

    def to_document(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "portable_declared_dependency_record_ids": list(
                self.portable_declared_dependency_record_ids
            ),
            "authority_local_semantic_dependency_record_ids": list(
                self.authority_local_semantic_dependency_record_ids
            ),
            "effective_dependency_record_ids": list(
                self.effective_dependency_record_ids
            ),
            "source_binding_id": self.source_binding_id,
            "resolver_kind": self.resolver_kind.value,
            "local_semantic_authority_resolved": (
                self.local_semantic_authority_resolved
            ),
            "semantically_resolved": self.semantically_resolved,
            "authority_scope": self.authority_scope.value,
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
            "dependency_depth": self.dependency_depth,
        }


def _scope_from_upstream(
    value: Any,
) -> V075ConstructionMultiroundResultAuthorityScopeV2:
    raw = getattr(getattr(value, "authority_scope", None), "value", None)
    try:
        return V075ConstructionMultiroundResultAuthorityScopeV2(raw)
    except ValueError:
        _fail("multiround upstream authority scope is unknown")


def _iterative_dependency_nodes(
    *,
    upstream_nodes: tuple[Any, ...],
    source_binding: V075ConstructionMultiroundResultSourceBindingV2,
) -> tuple[V075ConstructionMultiroundResultDependencyNodeV2, ...]:
    if (
        type(upstream_nodes) is not tuple
        or not upstream_nodes
        or len(upstream_nodes) > MAX_DEPENDENCY_NODES
    ):
        _fail("multiround result requires one bounded exact DAG")
    if (
        type(source_binding)
        is not V075ConstructionMultiroundResultSourceBindingV2
    ):
        _fail("multiround-result source binding is not exact")
    _ = source_binding.binding_id
    by_id: dict[str, Any] = {}
    for expected_index, item in enumerate(upstream_nodes):
        portable_lane = tuple(
            item.portable_declared_dependency_record_ids
        )
        local_lane = tuple(
            item.authority_local_semantic_dependency_record_ids
        )
        effective_lane = tuple(item.effective_dependency_record_ids)
        if (
            item.record_index != expected_index
            or item.record_id in by_id
            or tuple(sorted(set(portable_lane))) != portable_lane
            or tuple(sorted(set(local_lane))) != local_lane
            or tuple(sorted(set(effective_lane))) != effective_lane
            or set(effective_lane)
            != set(portable_lane) | set(local_lane)
        ):
            _fail("multiround upstream DAG lanes are malformed")
        by_id[item.record_id] = item
    all_ids = set(by_id)
    role_by_id = {
        record_id: item.role for record_id, item in by_id.items()
    }
    targets = tuple(
        record_id
        for record_id, role in role_by_id.items()
        if role == "MULTIROUND_RESULT"
    )
    if targets != (source_binding.target_record_id,):
        _fail("multiround-result source target is transplanted")
    source_pairs = dict(source_binding.source_records)
    if (
        set(source_pairs) != _SOURCE_ROLE_SET
        or any(
            source_pairs[role] not in all_ids
            or role_by_id[source_pairs[role]] != role
            for role in SOURCE_ROLE_ORDER
        )
        or source_binding.target_record_id
        in source_binding.source_dependency_record_ids
    ):
        _fail("multiround-result source registry is transplanted")

    portable_by_id: dict[str, tuple[str, ...]] = {}
    local_by_id: dict[str, tuple[str, ...]] = {}
    effective_by_id: dict[str, tuple[str, ...]] = {}
    local_resolved_by_id: dict[str, bool] = {}
    resolver_by_id: dict[
        str, V075ConstructionMultiroundResultResolverKindV2
    ] = {}
    source_id_by_id: dict[str, str | None] = {}
    upstream_scope_by_id: dict[
        str, V075ConstructionMultiroundResultAuthorityScopeV2
    ] = {}
    for record_id, upstream in by_id.items():
        portable_dependencies = tuple(
            upstream.portable_declared_dependency_record_ids
        )
        inherited_local = tuple(
            upstream.authority_local_semantic_dependency_record_ids
        )
        role = role_by_id[record_id]
        if role == "MULTIROUND_RESULT":
            added = source_binding.source_dependency_record_ids
            local_resolved = True
            resolver = (
                V075ConstructionMultiroundResultResolverKindV2
                .CONSTRUCTION_MULTIROUND_RESULT_OWNER_REPLAY
            )
            source_id = source_binding.binding_id
        else:
            added = ()
            local_resolved = bool(
                upstream.local_semantic_authority_resolved
            )
            resolver = (
                V075ConstructionMultiroundResultResolverKindV2
                .UPSTREAM_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY
                if local_resolved
                else V075ConstructionMultiroundResultResolverKindV2
                .NO_REGISTERED_SEMANTIC_AUTHORITY
            )
            source_id = upstream.source_binding_id
        local_dependencies = tuple(
            sorted(set(inherited_local) | set(added))
        )
        effective_dependencies = tuple(
            sorted(set(portable_dependencies) | set(local_dependencies))
        )
        if (
            record_id in effective_dependencies
            or any(item not in all_ids for item in effective_dependencies)
        ):
            _fail("multiround-result dependency edge is foreign")
        portable_by_id[record_id] = portable_dependencies
        local_by_id[record_id] = local_dependencies
        effective_by_id[record_id] = effective_dependencies
        local_resolved_by_id[record_id] = local_resolved
        resolver_by_id[record_id] = resolver
        source_id_by_id[record_id] = source_id
        upstream_scope_by_id[record_id] = _scope_from_upstream(upstream)

    indegree = {
        record_id: len(dependencies)
        for record_id, dependencies in effective_by_id.items()
    }
    successors = {record_id: [] for record_id in all_ids}
    for record_id, dependencies in effective_by_id.items():
        for dependency in dependencies:
            successors[dependency].append(record_id)
    ready = [
        (by_id[record_id].record_index, record_id)
        for record_id, degree in indegree.items()
        if degree == 0
    ]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        _index, record_id = heapq.heappop(ready)
        order.append(record_id)
        for successor in successors[record_id]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(
                    ready,
                    (by_id[successor].record_index, successor),
                )
    if len(order) != len(all_ids):
        _fail("multiround-result effective DAG contains a cycle")

    scopes = V075ConstructionMultiroundResultAuthorityScopeV2
    resolved: dict[str, bool] = {}
    scope_by_id: dict[
        str, V075ConstructionMultiroundResultAuthorityScopeV2
    ] = {}
    frontiers: dict[str, tuple[str, ...]] = {}
    depths: dict[str, int] = {}
    nodes: dict[str, V075ConstructionMultiroundResultDependencyNodeV2] = {}
    for record_id in order:
        dependencies = effective_by_id[record_id]
        is_resolved = local_resolved_by_id[record_id] and all(
            resolved[item] for item in dependencies
        )
        role = role_by_id[record_id]
        inherited_scope = upstream_scope_by_id[record_id]
        if not is_resolved:
            scope = scopes.UNRESOLVED
        elif role == "MULTIROUND_RESULT":
            scope = scopes.FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY
        elif inherited_scope is not scopes.UNRESOLVED:
            scope = inherited_scope
        elif any(
            scope_by_id[item] is not scopes.FULL_PUBLIC
            for item in dependencies
        ):
            scope = scopes.FULL_CONSTRUCTION_TRANSITIVE
        else:
            scope = scopes.FULL_PUBLIC
        if is_resolved:
            frontier: tuple[str, ...] = ()
        elif not local_resolved_by_id[record_id]:
            frontier = (record_id,)
        else:
            unresolved: set[str] = set()
            for dependency in dependencies:
                unresolved.update(frontiers[dependency])
            frontier = tuple(sorted(unresolved))
            if not frontier:
                _fail("unresolved multiround node lacks exact frontier")
        depth = 1 + max(
            (depths[item] for item in dependencies),
            default=0,
        )
        if depth > MAX_DEPENDENCY_NODES:
            _fail("multiround-result dependency depth exceeded")
        node = V075ConstructionMultiroundResultDependencyNodeV2(
            record_id,
            by_id[record_id].record_index,
            role,
            portable_by_id[record_id],
            local_by_id[record_id],
            effective_by_id[record_id],
            source_id_by_id[record_id],
            resolver_by_id[record_id],
            local_resolved_by_id[record_id],
            is_resolved,
            scope,
            frontier,
            tuple(sorted({role_by_id[item] for item in frontier})),
            depth,
        )
        nodes[record_id] = node
        resolved[record_id] = is_resolved
        scope_by_id[record_id] = scope
        frontiers[record_id] = frontier
        depths[record_id] = depth
    return tuple(
        nodes[item.record_id]
        for item in sorted(
            upstream_nodes,
            key=lambda value: value.record_index,
        )
    )


_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionMultiroundResultDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    closed_replay: (
        closed_authority
        .V075PortableConstructionClosedReconciliationReplayV2
    ) = field(repr=False)
    source_binding: V075ConstructionMultiroundResultSourceBindingV2
    nodes: tuple[V075ConstructionMultiroundResultDependencyNodeV2, ...]
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("multiround-result DAG is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_dag_id",
            _hash("dependency_dag", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.bundle_id, "multiround DAG bundle")
        _cid(self.typed_graph_id, "multiround DAG graph")
        if (
            type(self.closed_replay)
            is not closed_authority
            .V075PortableConstructionClosedReconciliationReplayV2
            or type(self.source_binding)
            is not V075ConstructionMultiroundResultSourceBindingV2
            or type(self.nodes) is not tuple
            or not self.nodes
            or any(
                type(item)
                is not V075ConstructionMultiroundResultDependencyNodeV2
                for item in self.nodes
            )
        ):
            _fail("multiround-result DAG is malformed")
        expected = _iterative_dependency_nodes(
            upstream_nodes=self.closed_replay.dependency_dag.nodes,
            source_binding=self.source_binding,
        )
        if tuple(item.to_document() for item in self.nodes) != tuple(
            item.to_document() for item in expected
        ):
            _fail("multiround-result DAG is stale")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_multiround_result_dependency_dag.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "root_only_profile_key": ROOT_ONLY_PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "typed_graph_id": self.typed_graph_id,
            "closed_replay_result_id": self.closed_replay.result_id,
            "source_binding_id": self.source_binding.binding_id,
            "nodes": [item.to_document() for item in self.nodes],
            "portable_declared_dependency_lane_preserved": True,
            "authority_local_dependency_lane_preserved": True,
            "effective_dependency_lane_recomputed": True,
            "authority_scope_lattice_propagated": True,
            "iterative_kahn_walk_used": True,
            "maximum_dependency_nodes": MAX_DEPENDENCY_NODES,
        }

    @property
    def dag_id(self) -> str:
        self._validate()
        if self._dag_id != _hash("dependency_dag", self._payload()):
            _fail("multiround-result DAG identity is stale")
        return self._dag_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "dependency_dag_id": self.dag_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("multiround-result DAG is in-memory-only")


_ROLE_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionMultiroundResultRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    dependency_dag_id: str
    role: str
    record_ids: tuple[str, ...]
    status: V075ConstructionMultiroundResultRoleStatusV2
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("multiround-result closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.bundle_id, "multiround role closure bundle")
        _cid(self.dependency_dag_id, "multiround role closure DAG")
        if (
            self.role not in _ROLE_SET
            or type(self.record_ids) is not tuple
            or len(self.record_ids) != 1
            or type(self.status)
            is not V075ConstructionMultiroundResultRoleStatusV2
            or self.unresolved_frontier_record_ids
            or self.unresolved_frontier_roles
        ):
            _fail("multiround-result role closure is malformed")
        _cid(self.record_ids[0], "multiround role closure record")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_multiround_result_role_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "root_only_profile_key": ROOT_ONLY_PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "dependency_dag_id": self.dependency_dag_id,
            "role": self.role,
            "record_ids": list(self.record_ids),
            "status": self.status.value,
            "unresolved_frontier_record_ids": [],
            "unresolved_frontier_roles": [],
        }

    @property
    def closure_id(self) -> str:
        self._validate()
        if self._closure_id != _hash("role_closure", self._payload()):
            _fail("multiround-result role closure identity is stale")
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("multiround-result role closure is in-memory-only")


def _build_role_closures(
    *,
    bundle_id: str,
    dependency_dag_id: str,
    nodes: tuple[V075ConstructionMultiroundResultDependencyNodeV2, ...],
) -> tuple[V075ConstructionMultiroundResultRoleClosureV2, ...]:
    statuses = V075ConstructionMultiroundResultRoleStatusV2
    scopes = V075ConstructionMultiroundResultAuthorityScopeV2
    expected = {
        "CONSTRUCTION_PLANNING_INPUT": (
            statuses.FULL_CONSTRUCTION_COMPILER_REPLAY,
            scopes.FULL_CONSTRUCTION_COMPILER_REPLAY,
        ),
        "CLOSED_RECONCILIATION": (
            statuses.FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY,
            scopes.FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY,
        ),
        "MULTIROUND_RESULT": (
            statuses.FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY,
            scopes.FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY,
        ),
    }
    result = []
    for role in ROLE_ORDER:
        members = tuple(item for item in nodes if item.role == role)
        if len(members) != 1:
            _fail(f"multiround-result role {role} is not singleton")
        member = members[0]
        status, scope = expected[role]
        if (
            not member.semantically_resolved
            or member.authority_scope is not scope
            or member.unresolved_frontier_record_ids
            or member.unresolved_frontier_roles
        ):
            _fail(f"multiround-result role {role} did not close exactly")
        result.append(
            V075ConstructionMultiroundResultRoleClosureV2(
                _ROLE_CLOSURE_ISSUER,
                bundle_id,
                dependency_dag_id,
                role,
                (member.record_id,),
                status,
                (),
                (),
            )
        )
    return tuple(result)


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableConstructionMultiroundResultReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075ConstructionMultiroundResultTypedGraphV2 = field(
        repr=False
    )
    dependency_dag: V075ConstructionMultiroundResultDependencyDAGV2 = field(
        repr=False
    )
    role_closures: tuple[
        V075ConstructionMultiroundResultRoleClosureV2, ...
    ]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("multiround-result replay is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "multiround result bundle"),
            (self.occurrence_id, "multiround result occurrence"),
            (self.public_context_closure_id, "multiround result context"),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph)
            is not V075ConstructionMultiroundResultTypedGraphV2
            or type(self.dependency_dag)
            is not V075ConstructionMultiroundResultDependencyDAGV2
            or type(self.role_closures) is not tuple
            or tuple(item.role for item in self.role_closures) != ROLE_ORDER
            or any(
                type(item)
                is not V075ConstructionMultiroundResultRoleClosureV2
                for item in self.role_closures
            )
            or self.typed_graph.bundle_id != self.bundle_id
            or self.typed_graph.occurrence_id != self.occurrence_id
            or self.typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or self.dependency_dag.bundle_id != self.bundle_id
            or self.dependency_dag.typed_graph_id
            != self.typed_graph.graph_id
            or self.dependency_dag.closed_replay
            is not self.typed_graph.closed_replay
            or self.dependency_dag.source_binding
            is not self.typed_graph.source_binding
        ):
            _fail("multiround-result replay is malformed")
        expected = _build_role_closures(
            bundle_id=self.bundle_id,
            dependency_dag_id=self.dependency_dag.dag_id,
            nodes=self.dependency_dag.nodes,
        )
        if tuple(item.to_document() for item in self.role_closures) != tuple(
            item.to_document() for item in expected
        ):
            _fail("multiround-result closures are stale")
        if (
            self._remaining_unresolved_frontier_record_ids()
            or self._remaining_unresolved_frontier_roles()
        ):
            _fail("multiround-result replay retained an unresolved frontier")

    def _remaining_unresolved_frontier_record_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    record_id
                    for node in self.dependency_dag.nodes
                    for record_id in node.unresolved_frontier_record_ids
                }
            )
        )

    def _remaining_unresolved_frontier_roles(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    role
                    for node in self.dependency_dag.nodes
                    for role in node.unresolved_frontier_roles
                }
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_construction_multiround_result_replay.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "root_only_profile_key": ROOT_ONLY_PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "typed_graph_id": self.typed_graph.graph_id,
            "dependency_dag_id": self.dependency_dag.dag_id,
            "multiround_result_id": (
                self.typed_graph.multiround_result.result_id
            ),
            "role_statuses": {
                item.role: item.status.value for item in self.role_closures
            },
            "role_closure_ids": [
                item.closure_id for item in self.role_closures
            ],
            "remaining_unresolved_frontier_record_ids": list(
                self._remaining_unresolved_frontier_record_ids()
            ),
            "remaining_unresolved_frontier_roles": list(
                self._remaining_unresolved_frontier_roles()
            ),
            "raw_contract_180_replayed_first": True,
            "owner_root_execution_replayed": True,
            "owner_multiround_result_replayed": True,
            "root_only_empty_roles_verified_from_fresh_bundle": True,
            "aggregate_currentness_requires_explicit_raw_replay": True,
            "no_argument_currentness_claim_available": False,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "portable_semantic_registry_complete": False,
            "fresh_heldout_accessed": False,
            "accounting_gate_passed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def result_id(self) -> str:
        self._validate()
        if self._result_id != _hash("aggregate", self._payload()):
            _fail("multiround-result replay identity is stale")
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}

    def assert_current(
        self,
        *,
        repository_root: str | Path,
        portable_bundle_bytes: bytes,
        public_context_closure_bytes: bytes,
        private_generation_seed: bytes,
        private_salt: bytes,
    ) -> None:
        replayed = replay_v075_portable_construction_multiround_result_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
            private_generation_seed=private_generation_seed,
            private_salt=private_salt,
        )
        if replayed.to_document() != self.to_document():
            _fail("multiround-result currentness check changed")

    def __reduce__(self) -> NoReturn:
        raise TypeError("multiround-result replay is in-memory-only")


def replay_v075_portable_construction_multiround_result_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075PortableConstructionMultiroundResultReplayV2:
    """Replay raw 1.80 first, then the root-only owner terminal producers."""

    # This is the first operation.  No argument is inspected, type-checked,
    # parsed, hashed, or retained before raw contract 1.80 succeeds.
    try:
        upstream = (
            closed_authority
            .replay_v075_portable_construction_closed_reconciliation_v2(
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=public_context_closure_bytes,
                private_generation_seed=private_generation_seed,
                private_salt=private_salt,
            )
        )
        (
            _hardened,
            _root_graph,
            _m1b_graph,
            _dynamic_graph,
            schedule,
            schedule_verification,
            namespace,
            prefix,
            root_view,
            root_epoch,
            child_closure,
            child_verification,
            final_epoch,
            final_model,
            final_proof,
            reconciliation,
        ) = _exact_chain(upstream)
        bundle = (
            portable.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
        if (
            type(bundle)
            is not portable.V075PortableOccurrenceEvidenceBundleV2
            or bundle.bundle_id != upstream.bundle_id
            or bundle.occurrence_id != upstream.occurrence_id
        ):
            _fail(_REPLAY_MISMATCH)
        empty_registry = _freeze_empty_role_registry(bundle=bundle)
        root_execution = owner.replay_v075_construction_root_execution_v2(
            repository_root=repository_root,
            namespace=namespace,
            schedule=schedule,
            schedule_verification=schedule_verification,
            controlled_root_prefix=prefix,
            root_execution_bytes=root_view.canonical_bytes,
        )
        if (
            type(root_execution)
            is not owner.V075ObserverSignedRootExecutionV2
            or root_execution.execution_id != root_view.execution_id
            or _raw(root_execution) != root_view.canonical_bytes
        ):
            _fail(_REPLAY_MISMATCH)
        source_records = _exact_portable_sources(
            records=bundle.records,
            schedule=schedule,
            schedule_verification=schedule_verification,
            prefix=prefix,
            root_execution=root_execution,
            root_epoch=root_epoch,
            child_closure=child_closure,
            child_verification=child_verification,
            final_model=final_model,
            final_proof=final_proof,
            reconciliation=reconciliation,
        )
        multiround_result = (
            owner.freeze_v075_construction_multiround_result_v2(
                repository_root=repository_root,
                namespace=namespace,
                schedule=schedule,
                schedule_verification=schedule_verification,
                controlled_root_prefix=prefix,
                root_execution_bytes=root_view.canonical_bytes,
                root_epoch=root_epoch,
                child_closure=child_closure,
                child_closure_verification=child_verification,
                final_epoch=final_epoch,
                reconciliation=reconciliation,
                child_execution_ledger=None,
                child_execution_verification=None,
                child_replanning_barrier=None,
                child_replanning_barrier_verification=None,
                promotion_decisions=(),
                promotion_decision_verifications=(),
                promotion_replanning_barriers=(),
                promotion_replanning_barrier_verifications=(),
            )
        )
        if (
            type(multiround_result)
            is not owner.V075ObserverSignedMultiroundResultV2
            or multiround_result.status
            is not (
                owner.V075ObserverSignedMultiroundTerminalStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            )
        ):
            _fail(_REPLAY_MISMATCH)
        # The target is deliberately selected only after every parent and
        # owner result has been fixed.  It cannot steer producer selection.
        target = _portable_record(
            bundle.records,
            role="MULTIROUND_RESULT",
            label="portable multiround-result target",
        )
        if (
            target.semantic_artifact_id != multiround_result.result_id
            or target.canonical_artifact_bytes != _raw(multiround_result)
        ):
            _fail(_REPLAY_MISMATCH)
        source_binding = _build_source_binding(
            replayed=upstream,
            target_record=target,
            source_records=source_records,
            empty_registry=empty_registry,
            namespace=namespace,
            schedule=schedule,
            schedule_verification=schedule_verification,
            prefix=prefix,
            root_execution=root_execution,
            root_epoch=root_epoch,
            child_closure=child_closure,
            child_verification=child_verification,
            final_model=final_model,
            final_proof=final_proof,
            reconciliation=reconciliation,
            result=multiround_result,
        )
        graph = V075ConstructionMultiroundResultTypedGraphV2(
            _TYPED_GRAPH_ISSUER,
            upstream.bundle_id,
            upstream.occurrence_id,
            upstream.public_context_closure_id,
            upstream,
            namespace,
            schedule,
            schedule_verification,
            prefix,
            root_execution,
            root_epoch,
            child_closure,
            child_verification,
            final_epoch,
            final_model,
            final_proof,
            reconciliation,
            multiround_result,
            target,
            source_records,
            empty_registry,
            source_binding,
        )
        nodes = _iterative_dependency_nodes(
            upstream_nodes=upstream.dependency_dag.nodes,
            source_binding=source_binding,
        )
        dag = V075ConstructionMultiroundResultDependencyDAGV2(
            _DAG_ISSUER,
            upstream.bundle_id,
            graph.graph_id,
            upstream,
            source_binding,
            nodes,
        )
        closures = _build_role_closures(
            bundle_id=upstream.bundle_id,
            dependency_dag_id=dag.dag_id,
            nodes=nodes,
        )
        result = V075PortableConstructionMultiroundResultReplayV2(
            _RESULT_ISSUER,
            upstream.bundle_id,
            upstream.occurrence_id,
            upstream.public_context_closure_id,
            graph,
            dag,
            closures,
        )
        if len(canonical_json_bytes(result.to_document())) > MAX_OUTPUT_BYTES:
            _fail("multiround-result public summary exceeds cap")
        return result
    except Exception:
        # Raw/private mismatch details are uniformly suppressed so secret
        # values cannot escape through nested exception messages or reprs.
        raise (
            V075PortableConstructionMultiroundResultV2InvariantViolation(
                _REPLAY_MISMATCH
            )
        ) from None


def assert_v075_portable_construction_multiround_result_production_gate_v2(
    result: V075PortableConstructionMultiroundResultReplayV2,
) -> NoReturn:
    if type(result) is not V075PortableConstructionMultiroundResultReplayV2:
        _fail("multiround-result gate rejects duck-typed results")
    _ = result.result_id
    raise V075PortableConstructionMultiroundResultProductionV2NotReady(
        "contract 1.81 is construction-only; source/code provenance, "
        "accounting, production, and scientific gates remain open"
    )
