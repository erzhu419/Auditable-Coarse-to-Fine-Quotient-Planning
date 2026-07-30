"""Portable construction planning-input replay authority for V0-075.

Contract 1.79 starts from the five raw inputs accepted by contract 1.78.
The raw 1.78 replay is the only upstream gate and is executed before this
module inspects any argument or typed object.  Its fresh construction lineage
and lifecycle, together with the exact M0 schedule carried by the hardened
chain, are passed to the registered construction compiler.

The compiler result must equal the sole portable
``CONSTRUCTION_PLANNING_INPUT`` record byte-for-byte.  Its nested numerical
model must also equal the corresponding standalone model in contract 1.77's
exact all-epoch registry.  Schedule, occurrence, arm, route, lineage,
lifecycle, lifecycle verification, and every row-evidence binding are checked
against the fresh typed producer graph.

This remains a construction-only, in-memory replay.  This module does not
retain or serialize either private input, does not directly hash either one,
and does not emit a secret digest.  The frozen upstream private mechanisms
may cryptographically consume those ephemeral inputs.  Currentness always
requires another explicit five-input raw replay.
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
from acfqp import (
    v075_portable_construction_private_replay_authority_v2 as private_replay,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.79.0"
PROFILE_KEY = "v075_portable_construction_planning_input_authority_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
CONSTRUCTION_EPHEMERAL_PRIVATE_INPUT_REQUIRED = True
CONSTRUCTION_PRIVATE_REPLAY_REQUIRED = True
CONSTRUCTION_PLANNING_INPUT_COMPILER_REPLAYED = True
PRODUCTION_PRIVATE_INPUT_CHANNEL_ALLOWED = False
PRODUCTION_COMPILER_ALLOWED = False
B3_INPUT_ALLOWED = False
K7_INPUT_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
J0_ACCESS_ALLOWED = False
OBSERVER_OPEN_ALLOWED = False
WORKER_LAUNCH_ALLOWED = False
OPERATIONAL_REGISTRIES_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_PLANNING_INPUT_REPLAY_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_PLANNING_INPUT_REPLAY_COMPLETE_"
    "DOWNSTREAM_PRODUCER_AUTHORITIES_UNRESOLVED"
)
MAX_DEPENDENCY_NODES = 4096
MAX_OUTPUT_BYTES = 64 * 1024 * 1024

ROLE_ORDER = (
    "CONSTRUCTION_PLANNING_INPUT",
    "CLOSED_RECONCILIATION",
    "MULTIROUND_RESULT",
)
SOURCE_ROLE_ORDER = (
    "CONSTRUCTION_LIFECYCLE",
    "CONSTRUCTION_LIFECYCLE_VERIFICATION",
    "CONSTRUCTION_LINEAGE",
    "INITIAL_ACQUISITION_SCHEDULE",
    "NUMERICAL_MODEL",
    "OCCURRENCE_IDENTITY",
)
_ROLE_SET = frozenset(ROLE_ORDER)
_SOURCE_ROLE_SET = frozenset(SOURCE_ROLE_ORDER)

DOMAIN_TAGS = MappingProxyType(
    {
        "source_binding": (
            "acfqp:v075-portable-construction-planning-input-source:v2"
        ),
        "typed_graph": (
            "acfqp:v075-portable-construction-planning-input-graph:v2"
        ),
        "dependency_dag": (
            "acfqp:v075-portable-construction-planning-input-dag:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-construction-planning-input-closure:v2"
        ),
        "aggregate": (
            "acfqp:v075-portable-construction-planning-input-authority:v2"
        ),
    }
)

_REPLAY_MISMATCH = (
    "construction planning-input replay did not match registered evidence"
)


class V075PortableConstructionPlanningInputV2InvariantViolation(ValueError):
    """The raw private/compiler replay or its exact dependency graph failed."""


class V075PortableConstructionPlanningInputProductionV2NotReady(RuntimeError):
    """Contract 1.79 cannot authorize a production occurrence."""


class V075ConstructionPlanningInputRoleStatusV2(str, Enum):
    FULL_CONSTRUCTION_COMPILER_REPLAY = (
        "FULL_CONSTRUCTION_COMPILER_REPLAY"
    )
    STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED = (
        "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
    )


class V075ConstructionPlanningInputResolverKindV2(str, Enum):
    UPSTREAM_CONSTRUCTION_PRIVATE_REPLAY = (
        "UPSTREAM_CONSTRUCTION_PRIVATE_REPLAY"
    )
    CONSTRUCTION_PLANNING_INPUT_COMPILER_REPLAY = (
        "CONSTRUCTION_PLANNING_INPUT_COMPILER_REPLAY"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


class V075ConstructionPlanningInputAuthorityScopeV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    FULL_CONSTRUCTION_PRIVATE_REPLAY = (
        "FULL_CONSTRUCTION_PRIVATE_REPLAY"
    )
    FULL_CONSTRUCTION_COMPILER_REPLAY = (
        "FULL_CONSTRUCTION_COMPILER_REPLAY"
    )
    FULL_CONSTRUCTION_TRANSITIVE = "FULL_CONSTRUCTION_TRANSITIVE"
    UNRESOLVED = "UNRESOLVED"


def _fail(message: str) -> NoReturn:
    raise V075PortableConstructionPlanningInputV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableConstructionPlanningInputV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PortableConstructionPlanningInputV2InvariantViolation(
            "construction planning-input public identity is malformed"
        ) from error


def _raw(value: Any) -> bytes:
    return canonical_json_bytes(value.to_document())


def _exact_hardened_parts(
    replayed: private_replay.V075PortableConstructionPrivateReplayV2,
) -> tuple[Any, Any, Any, acquisition.V075InitialAcquisitionScheduleV2]:
    """Extract exact 1.77 planning, M0 graph, and M0 schedule from 1.78."""

    if (
        type(replayed)
        is not private_replay.V075PortableConstructionPrivateReplayV2
    ):
        _fail("planning-input replay requires exact raw contract 1.78")
    _ = replayed.result_id
    try:
        hardened = replayed.typed_graph.hardened_planning_result
        dynamic = hardened.typed_graph.m2_dynamic_child_result
        live_epoch = dynamic.typed_graph.m2_live_epoch_result
        lifecycle_result = live_epoch.typed_graph.m2_lifecycle_result
        lineage_result = lifecycle_result.typed_graph.m2_lineage_result
        root_result = lineage_result.typed_graph.m2_result
        root_graph = root_result.typed_graph
        m1a_graph = root_graph.m1b_result.typed_graph.m1a_result.typed_graph
        m0_result = m1a_graph.m0_result
        m0_graph = m0_result.typed_graph
        schedule = m0_graph.schedule
    except (AttributeError, TypeError) as error:
        raise V075PortableConstructionPlanningInputV2InvariantViolation(
            "contract 1.78 omitted its exact hardened producer chain"
        ) from error
    if (
        type(schedule) is not acquisition.V075InitialAcquisitionScheduleV2
        or hardened.bundle_id != replayed.bundle_id
        or hardened.occurrence_id != replayed.occurrence_id
        or root_graph.occurrence != m0_graph.occurrence
        or schedule.occurrence != m0_graph.occurrence
        or schedule.occurrence.occurrence_id != replayed.occurrence_id
        or m1a_graph.closure
        != replayed.typed_graph.construction_lineage.closure
    ):
        _fail("contract 1.78 hardened schedule crossed producer identities")
    return hardened, m0_result, m0_graph, schedule


def _sole_by_role(values: tuple[Any, ...], role: str, label: str) -> Any:
    matches = tuple(item for item in values if item.role == role)
    if len(matches) != 1:
        _fail(f"{label} role {role} is absent or duplicated")
    return matches[0]


def _sole_model_binding(hardened: Any, model_id: str) -> tuple[Any, Any]:
    models = tuple(
        item for item in hardened.typed_graph.models
        if item.model_id == model_id
    )
    bindings = tuple(
        item
        for item in hardened.typed_graph.target_record_bindings
        if item.role == "NUMERICAL_MODEL"
        and item.semantic_artifact_id == model_id
    )
    if (
        len(models) != 1
        or len(bindings) != 1
        or bindings[0].canonical_artifact_bytes != _raw(models[0])
    ):
        _fail("compiled nested model is absent from exact 1.77 registry")
    return models[0], bindings[0]


def _m0_attestation(m0_result: Any, role: str, semantic_id: str) -> Any:
    matches = tuple(
        item
        for item in m0_result.attestations
        if item.role == role and item.semantic_artifact_id == semantic_id
    )
    if len(matches) != 1:
        _fail(f"exact M0 {role} attestation is absent or duplicated")
    return matches[0]


def _validate_complete_row_evidence(
    *,
    compiled: planning.V075ConstructionPlanningInputV2,
    lineage: Any,
    lifecycle: Any,
) -> None:
    """Bind every compiler evidence row to fresh lineage/lifecycle objects."""

    batches = tuple(lineage.batches)
    freezes = tuple(lifecycle.support_freezes)
    if (
        not compiled.evidence_bindings
        or len(compiled.evidence_bindings) != len(compiled.model.rows)
    ):
        _fail("construction planning input lacks complete row evidence")
    row_ids = tuple(item.row_id for item in compiled.model.rows)
    if tuple(
        item.numerical_row_id for item in compiled.evidence_bindings
    ) != row_ids:
        _fail("construction planning row evidence order changed")
    for evidence in compiled.evidence_bindings:
        row_batches = tuple(
            item
            for item in batches
            if (
                item.request.stream_identity.row_binding.row_binding_id
                == evidence.row_binding_id
            )
        )
        row_freezes = tuple(
            item
            for item in freezes
            if item.row_binding_id == evidence.row_binding_id
        )
        discovery_ids = tuple(
            sorted(
                item.batch_id
                for item in row_batches
                if item.request.stream_identity.lane.value == "DISCOVERY"
            )
        )
        validation_ids = tuple(
            sorted(
                item.batch_id
                for item in row_batches
                if (
                    item.request.stream_identity.lane.value == "VALIDATION"
                    and (
                        item.request.stream_identity.observer_epoch_index
                        == evidence.latest_validation_epoch_index
                    )
                )
            )
        )
        freeze_matches = tuple(
            item
            for item in row_freezes
            if item.freeze_id == evidence.support_freeze_id
        )
        if (
            not row_batches
            or len(freeze_matches) != 1
            or evidence.discovery_batch_ids != discovery_ids
            or evidence.latest_validation_batch_ids != validation_ids
            or evidence.latest_validation_epoch_index != 1
            or evidence.lifecycle_closure_id != lifecycle.closure_id
            or freeze_matches[0].validation_epoch_index
            != evidence.latest_validation_epoch_index
            or tuple(
                sorted(freeze_matches[0].source_discovery_batch_ids)
            )
            != discovery_ids
        ):
            _fail("construction planning row evidence is incomplete or stale")


def _evidence_summary(
    value: planning.V075ConstructionPlanningInputV2,
) -> dict[str, tuple[str, ...]]:
    return {
        "numerical_row_ids": tuple(
            item.numerical_row_id for item in value.evidence_bindings
        ),
        "row_binding_ids": tuple(
            sorted(item.row_binding_id for item in value.evidence_bindings)
        ),
        "support_freeze_ids": tuple(
            sorted(item.support_freeze_id for item in value.evidence_bindings)
        ),
        "discovery_batch_ids": tuple(
            sorted(
                {
                    batch
                    for item in value.evidence_bindings
                    for batch in item.discovery_batch_ids
                }
            )
        ),
        "validation_batch_ids": tuple(
            sorted(
                {
                    batch
                    for item in value.evidence_bindings
                    for batch in item.latest_validation_batch_ids
                }
            )
        ),
        "row_evidence_binding_ids": tuple(
            item.binding_id for item in value.evidence_bindings
        ),
    }


_SOURCE_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPlanningInputSourceBindingV2:
    _issuer: InitVar[object]
    target_record_id: str
    target_semantic_artifact_id: str
    source_records: tuple[tuple[str, str], ...]
    portable_bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    target_tape_namespace_id: str
    repository_binding_id: str
    source_manifest_id: str
    private_replay_result_id: str
    hardened_planning_result_id: str
    schedule_id: str
    lineage_id: str
    lifecycle_closure_id: str
    lifecycle_verification_id: str
    numerical_model_id: str
    arm: str
    route: str
    numerical_row_ids: tuple[str, ...]
    row_binding_ids: tuple[str, ...]
    support_freeze_ids: tuple[str, ...]
    discovery_batch_ids: tuple[str, ...]
    validation_batch_ids: tuple[str, ...]
    row_evidence_binding_ids: tuple[str, ...]
    producer_artifact_sha256: str
    producer_artifact_byte_count: int
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_BINDING_ISSUER:
            _fail("construction planning-input source is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_binding_id",
            _hash("source_binding", self._payload()),
        )

    @property
    def source_dependency_record_ids(self) -> tuple[str, ...]:
        return tuple(sorted(record_id for _role, record_id in self.source_records))

    def _validate(self) -> None:
        for value, label in (
            (self.target_record_id, "planning-input target record"),
            (
                self.target_semantic_artifact_id,
                "planning-input target semantic artifact",
            ),
            (self.portable_bundle_id, "planning-input portable bundle"),
            (self.occurrence_id, "planning-input occurrence"),
            (
                self.public_context_closure_id,
                "planning-input public context",
            ),
            (
                self.target_tape_namespace_id,
                "planning-input target namespace",
            ),
            (
                self.repository_binding_id,
                "planning-input repository binding",
            ),
            (self.source_manifest_id, "planning-input source manifest"),
            (
                self.private_replay_result_id,
                "planning-input private replay",
            ),
            (
                self.hardened_planning_result_id,
                "planning-input hardened planning replay",
            ),
            (self.schedule_id, "planning-input schedule"),
            (self.lineage_id, "planning-input lineage"),
            (self.lifecycle_closure_id, "planning-input lifecycle"),
            (
                self.lifecycle_verification_id,
                "planning-input lifecycle verification",
            ),
            (self.numerical_model_id, "planning-input numerical model"),
            (
                self.producer_artifact_sha256,
                "planning-input compiler bytes",
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
            or self.arm not in {
                "ADAPTIVE_QUOTIENT",
                "MATCHED_DIRECT_GROUND",
            }
            or self.route not in {
                "ADAPTIVE_QUOTIENT",
                "MATCHED_DIRECT_GROUND",
            }
            or (self.arm == "MATCHED_DIRECT_GROUND")
            != (self.route == "MATCHED_DIRECT_GROUND")
            or type(self.producer_artifact_byte_count) is not int
            or self.producer_artifact_byte_count <= 0
        ):
            _fail("construction planning-input source binding is malformed")
        for role, record_id in self.source_records:
            if role not in _SOURCE_ROLE_SET:
                _fail("construction planning-input source role is unknown")
            _cid(record_id, "planning-input source record")
        sequences = (
            self.numerical_row_ids,
            self.row_binding_ids,
            self.support_freeze_ids,
            self.discovery_batch_ids,
            self.validation_batch_ids,
            self.row_evidence_binding_ids,
        )
        if (
            any(type(values) is not tuple or not values for values in sequences)
            or any(
                tuple(sorted(set(values))) != values
                for values in sequences[1:5]
            )
            or len(set(self.numerical_row_ids))
            != len(self.numerical_row_ids)
            or len(set(self.row_evidence_binding_ids))
            != len(self.row_evidence_binding_ids)
            or len(self.numerical_row_ids)
            != len(self.row_evidence_binding_ids)
        ):
            _fail("construction planning-input evidence summary is malformed")
        for values in sequences:
            for value in values:
                _cid(value, "construction planning-input evidence")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_planning_input_source_binding.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "target_record_id": self.target_record_id,
            "target_role": "CONSTRUCTION_PLANNING_INPUT",
            "target_semantic_artifact_id": self.target_semantic_artifact_id,
            "resolver_kind": (
                V075ConstructionPlanningInputResolverKindV2
                .CONSTRUCTION_PLANNING_INPUT_COMPILER_REPLAY.value
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
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "repository_binding_id": self.repository_binding_id,
            "source_manifest_id": self.source_manifest_id,
            "private_replay_result_id": self.private_replay_result_id,
            "hardened_planning_result_id": (
                self.hardened_planning_result_id
            ),
            "schedule_id": self.schedule_id,
            "lineage_id": self.lineage_id,
            "lifecycle_closure_id": self.lifecycle_closure_id,
            "lifecycle_verification_id": self.lifecycle_verification_id,
            "numerical_model_id": self.numerical_model_id,
            "arm": self.arm,
            "route": self.route,
            "numerical_row_ids": list(self.numerical_row_ids),
            "row_binding_ids": list(self.row_binding_ids),
            "support_freeze_ids": list(self.support_freeze_ids),
            "discovery_batch_ids": list(self.discovery_batch_ids),
            "validation_batch_ids": list(self.validation_batch_ids),
            "row_evidence_binding_ids": list(
                self.row_evidence_binding_ids
            ),
            "producer_artifact_sha256": self.producer_artifact_sha256,
            "producer_artifact_byte_count": self.producer_artifact_byte_count,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
        }

    @property
    def binding_id(self) -> str:
        self._validate()
        if self._binding_id != _hash("source_binding", self._payload()):
            _fail("construction planning-input source identity is stale")
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "construction planning-input source binding is in-memory-only"
        )


def _exact_source_records(
    *,
    replayed: private_replay.V075PortableConstructionPrivateReplayV2,
    m0_result: Any,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    compiled: planning.V075ConstructionPlanningInputV2,
    model_binding: Any,
) -> tuple[tuple[str, str], ...]:
    """Recompute the only six producer records consumed by the compiler."""

    target_by_role = {
        item.role: item
        for item in replayed.typed_graph.target_record_bindings
    }
    if set(target_by_role) != set(private_replay.ROLE_ORDER):
        _fail("contract 1.78 target registry changed")
    occurrence_attestation = _m0_attestation(
        m0_result, "OCCURRENCE_IDENTITY", compiled.occurrence_id
    )
    schedule_attestation = _m0_attestation(
        m0_result, "INITIAL_ACQUISITION_SCHEDULE", schedule.schedule_id
    )
    schedule_raw = _raw(schedule)
    occurrence_raw = _raw(schedule.occurrence)
    if (
        schedule_attestation.canonical_artifact_sha256
        != hashlib.sha256(schedule_raw).hexdigest()
        or schedule_attestation.canonical_artifact_byte_count
        != len(schedule_raw)
        or occurrence_attestation.canonical_artifact_sha256
        != hashlib.sha256(occurrence_raw).hexdigest()
        or occurrence_attestation.canonical_artifact_byte_count
        != len(occurrence_raw)
    ):
        _fail("exact M0 schedule or occurrence bytes changed")
    if (
        model_binding.role != "NUMERICAL_MODEL"
        or model_binding.semantic_artifact_id != compiled.model.model_id
        or model_binding.canonical_artifact_bytes != _raw(compiled.model)
    ):
        _fail("construction compiler selected a foreign model record")
    return tuple(
        sorted(
            (
                (
                    "CONSTRUCTION_LIFECYCLE",
                    target_by_role["CONSTRUCTION_LIFECYCLE"].record_id,
                ),
                (
                    "CONSTRUCTION_LIFECYCLE_VERIFICATION",
                    target_by_role[
                        "CONSTRUCTION_LIFECYCLE_VERIFICATION"
                    ].record_id,
                ),
                (
                    "CONSTRUCTION_LINEAGE",
                    target_by_role["CONSTRUCTION_LINEAGE"].record_id,
                ),
                (
                    "INITIAL_ACQUISITION_SCHEDULE",
                    schedule_attestation.record_id,
                ),
                ("NUMERICAL_MODEL", model_binding.record_id),
                ("OCCURRENCE_IDENTITY", occurrence_attestation.record_id),
            )
        )
    )


def _assert_exact_record_bindings(
    *,
    target: Any,
    expected_target: Any,
    model_binding: Any,
    expected_model_binding: Any,
) -> None:
    if (
        type(target) is not type(expected_target)
        or target is not expected_target
        or type(model_binding) is not type(expected_model_binding)
        or model_binding is not expected_model_binding
    ):
        _fail("construction planning-input record binding is transplanted")
    _ = target.binding_id
    model_binding._assert_current()  # noqa: SLF001


def _build_source_binding(
    *,
    replayed: private_replay.V075PortableConstructionPrivateReplayV2,
    hardened: Any,
    m0_result: Any,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    compiled: planning.V075ConstructionPlanningInputV2,
    target: Any,
    model_binding: Any,
) -> V075ConstructionPlanningInputSourceBindingV2:
    expected_target = _sole_by_role(
        replayed.typed_graph.target_record_bindings,
        "CONSTRUCTION_PLANNING_INPUT",
        "private replay target",
    )
    _expected_model, expected_model_binding = _sole_model_binding(
        hardened,
        compiled.model.model_id,
    )
    _assert_exact_record_bindings(
        target=target,
        expected_target=expected_target,
        model_binding=model_binding,
        expected_model_binding=expected_model_binding,
    )
    sources = _exact_source_records(
        replayed=replayed,
        m0_result=m0_result,
        schedule=schedule,
        compiled=compiled,
        model_binding=model_binding,
    )
    summary = _evidence_summary(compiled)
    raw = _raw(compiled)
    resolution = replayed.typed_graph.public_context_resolution
    return V075ConstructionPlanningInputSourceBindingV2(
        _SOURCE_BINDING_ISSUER,
        target.record_id,
        target.semantic_artifact_id,
        sources,
        replayed.bundle_id,
        replayed.occurrence_id,
        replayed.public_context_closure_id,
        resolution.namespace.target_tape_namespace_id,
        resolution.repository_binding.binding_id,
        resolution.source_manifest.manifest_id,
        replayed.result_id,
        hardened.result_id,
        compiled.schedule_id,
        compiled.lineage_id,
        compiled.lifecycle_closure_id,
        compiled.lifecycle_verification_id,
        compiled.model.model_id,
        compiled.arm.value,
        compiled.route.value,
        summary["numerical_row_ids"],
        summary["row_binding_ids"],
        summary["support_freeze_ids"],
        summary["discovery_batch_ids"],
        summary["validation_batch_ids"],
        summary["row_evidence_binding_ids"],
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )


def _assert_exact_source_binding(
    actual: Any,
    expected: V075ConstructionPlanningInputSourceBindingV2,
) -> None:
    if (
        type(actual) is not V075ConstructionPlanningInputSourceBindingV2
        or type(expected)
        is not V075ConstructionPlanningInputSourceBindingV2
        or actual.to_document() != expected.to_document()
    ):
        _fail("construction planning-input source metadata is stale")


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPlanningInputTypedGraphV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    private_replay_result: (
        private_replay.V075PortableConstructionPrivateReplayV2
    ) = field(repr=False)
    schedule: acquisition.V075InitialAcquisitionScheduleV2 = field(
        repr=False
    )
    standalone_numerical_model: planning.V075NumericalModelV2 = field(
        repr=False
    )
    construction_planning_input: (
        planning.V075ConstructionPlanningInputV2
    ) = field(repr=False)
    target_record_binding: Any = field(repr=False)
    numerical_model_record_binding: Any = field(repr=False)
    source_binding: V075ConstructionPlanningInputSourceBindingV2
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("construction planning-input graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "planning-input graph bundle"),
            (self.occurrence_id, "planning-input graph occurrence"),
            (
                self.public_context_closure_id,
                "planning-input graph public context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.private_replay_result)
            is not private_replay.V075PortableConstructionPrivateReplayV2
            or type(self.schedule)
            is not acquisition.V075InitialAcquisitionScheduleV2
            or type(self.standalone_numerical_model)
            is not planning.V075NumericalModelV2
            or type(self.construction_planning_input)
            is not planning.V075ConstructionPlanningInputV2
            or type(self.source_binding)
            is not V075ConstructionPlanningInputSourceBindingV2
        ):
            _fail("construction planning-input graph is malformed")
        _ = self.private_replay_result.result_id
        _ = self.source_binding.binding_id
        value = self.construction_planning_input
        hardened, m0_result, _m0_graph, expected_schedule = (
            _exact_hardened_parts(self.private_replay_result)
        )
        expected_target = _sole_by_role(
            self.private_replay_result.typed_graph.target_record_bindings,
            "CONSTRUCTION_PLANNING_INPUT",
            "private replay target",
        )
        expected_model, expected_model_binding = _sole_model_binding(
            hardened,
            value.model.model_id,
        )
        if (
            self.schedule is not expected_schedule
            or self.standalone_numerical_model is not expected_model
        ):
            _fail("construction planning-input exact producer was transplanted")
        _assert_exact_record_bindings(
            target=self.target_record_binding,
            expected_target=expected_target,
            model_binding=self.numerical_model_record_binding,
            expected_model_binding=expected_model_binding,
        )
        expected_source_binding = _build_source_binding(
            replayed=self.private_replay_result,
            hardened=hardened,
            m0_result=m0_result,
            schedule=expected_schedule,
            compiled=value,
            target=expected_target,
            model_binding=expected_model_binding,
        )
        _assert_exact_source_binding(
            self.source_binding,
            expected_source_binding,
        )
        if (
            self.private_replay_result.bundle_id != self.bundle_id
            or self.private_replay_result.occurrence_id != self.occurrence_id
            or self.private_replay_result.public_context_closure_id
            != self.public_context_closure_id
            or value.occurrence_id != self.occurrence_id
            or value.schedule_id != self.schedule.schedule_id
            or value.model.model_id
            != self.standalone_numerical_model.model_id
            or _raw(value.model) != _raw(self.standalone_numerical_model)
            or self.target_record_binding.role
            != "CONSTRUCTION_PLANNING_INPUT"
            or self.target_record_binding.record_id
            != self.source_binding.target_record_id
            or self.target_record_binding.semantic_artifact_id
            != value.input_id
            or self.target_record_binding.canonical_artifact_bytes
            != _raw(value)
            or self.numerical_model_record_binding.role
            != "NUMERICAL_MODEL"
            or self.numerical_model_record_binding.semantic_artifact_id
            != value.model.model_id
            or self.numerical_model_record_binding.canonical_artifact_bytes
            != _raw(value.model)
            or self.source_binding.target_semantic_artifact_id
            != value.input_id
            or self.source_binding.producer_artifact_sha256
            != hashlib.sha256(_raw(value)).hexdigest()
            or self.source_binding.producer_artifact_byte_count
            != len(_raw(value))
        ):
            _fail("construction planning-input graph crossed exact records")
        lineage = self.private_replay_result.typed_graph.construction_lineage
        lifecycle = (
            self.private_replay_result.typed_graph.construction_lifecycle
        )
        resolution = (
            self.private_replay_result.typed_graph.public_context_resolution
        )
        verification = (
            self.private_replay_result.typed_graph
            .construction_lifecycle_verification
        )
        identity = lineage.occurrence_identity
        expected_route = (
            planning.V075PlanningRouteV2.MATCHED_DIRECT_GROUND
            if identity.arm.value == "MATCHED_DIRECT_GROUND"
            else planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        )
        if (
            value.lineage_id != lineage.lineage_id
            or value.lifecycle_closure_id != lifecycle.closure_id
            or value.lifecycle_verification_id
            != verification.verification_id
            or value.target_tape_namespace_id
            != identity.target_tape_namespace_id
            or self.source_binding.target_tape_namespace_id
            != resolution.namespace.target_tape_namespace_id
            or self.source_binding.repository_binding_id
            != resolution.repository_binding.binding_id
            or self.source_binding.source_manifest_id
            != resolution.source_manifest.manifest_id
            or value.arm is not identity.arm
            or value.route is not expected_route
            or self.schedule.occurrence != identity
        ):
            _fail("construction compiler crossed schedule or private replay")
        _validate_complete_row_evidence(
            compiled=value,
            lineage=lineage,
            lifecycle=lifecycle,
        )
        summary = _evidence_summary(value)
        for key, expected in summary.items():
            if getattr(self.source_binding, key) != expected:
                _fail("construction planning-input evidence binding changed")

    def _payload(self) -> dict[str, Any]:
        value = self.construction_planning_input
        return {
            "schema": (
                "acfqp.v075_construction_planning_input_typed_graph.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "private_replay_result_id": (
                self.private_replay_result.result_id
            ),
            "schedule_id": self.schedule.schedule_id,
            "construction_lineage_id": value.lineage_id,
            "construction_lifecycle_id": value.lifecycle_closure_id,
            "construction_lifecycle_verification_id": (
                value.lifecycle_verification_id
            ),
            "construction_planning_input_id": value.input_id,
            "standalone_numerical_model_id": (
                self.standalone_numerical_model.model_id
            ),
            "target_record_id": self.target_record_binding.record_id,
            "numerical_model_record_id": (
                self.numerical_model_record_binding.record_id
            ),
            "source_binding_id": self.source_binding.binding_id,
            "complete_row_evidence_bindings_verified": True,
            "construction_compiler_replayed": True,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
        }

    @property
    def graph_id(self) -> str:
        self._validate()
        if self._graph_id != _hash("typed_graph", self._payload()):
            _fail("construction planning-input graph identity is stale")
        return self._graph_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "typed_graph_id": self.graph_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "construction planning-input graph is in-memory-only"
        )


@dataclass(frozen=True, slots=True)
class V075ConstructionPlanningInputDependencyNodeV2:
    record_id: str
    record_index: int
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    source_binding_id: str | None
    resolver_kind: V075ConstructionPlanningInputResolverKindV2
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    authority_scope: V075ConstructionPlanningInputAuthorityScopeV2
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    dependency_depth: int

    def __post_init__(self) -> None:
        _cid(self.record_id, "planning-input dependency node")
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
            != set(self.portable_declared_dependency_record_ids) | set(
                self.authority_local_semantic_dependency_record_ids
            )
            or type(self.resolver_kind)
            is not V075ConstructionPlanningInputResolverKindV2
            or type(self.local_semantic_authority_resolved) is not bool
            or type(self.semantically_resolved) is not bool
            or type(self.authority_scope)
            is not V075ConstructionPlanningInputAuthorityScopeV2
            or type(self.dependency_depth) is not int
            or not 0 < self.dependency_depth <= MAX_DEPENDENCY_NODES
            or self.semantically_resolved
            != (
                self.authority_scope
                is not V075ConstructionPlanningInputAuthorityScopeV2
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
            _fail("construction planning-input dependency node is malformed")
        if self.source_binding_id is not None:
            _cid(self.source_binding_id, "planning-input dependency source")
        for value in (
            *self.effective_dependency_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "planning-input dependency edge")

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


def _upstream_scope_value(item: Any) -> str:
    scope = getattr(item, "authority_scope", None)
    return getattr(scope, "value", "UNRESOLVED")


def _iterative_dependency_nodes(
    *,
    upstream_nodes: tuple[Any, ...],
    source_binding: V075ConstructionPlanningInputSourceBindingV2,
) -> tuple[V075ConstructionPlanningInputDependencyNodeV2, ...]:
    if (
        type(upstream_nodes) is not tuple
        or not upstream_nodes
        or len(upstream_nodes) > MAX_DEPENDENCY_NODES
    ):
        _fail("construction planning-input requires one bounded exact DAG")
    if (
        type(source_binding)
        is not V075ConstructionPlanningInputSourceBindingV2
    ):
        _fail("construction planning-input source binding is not exact")
    _ = source_binding.binding_id
    by_id: dict[str, Any] = {}
    for expected_index, item in enumerate(upstream_nodes):
        if (
            item.record_index != expected_index
            or item.record_id in by_id
        ):
            _fail("construction planning-input upstream DAG is malformed")
        by_id[item.record_id] = item
    all_ids = set(by_id)
    role_by_id = {record_id: item.role for record_id, item in by_id.items()}
    inputs = tuple(
        record_id
        for record_id, role in role_by_id.items()
        if role == "CONSTRUCTION_PLANNING_INPUT"
    )
    if inputs != (source_binding.target_record_id,):
        _fail("construction planning-input source target is transplanted")
    source_pairs = dict(source_binding.source_records)
    if (
        set(source_pairs) != _SOURCE_ROLE_SET
        or any(
            source_pairs[role] not in all_ids
            or role_by_id[source_pairs[role]] != role
            for role in SOURCE_ROLE_ORDER
        )
    ):
        _fail("construction planning-input source registry is transplanted")

    portable_by_id: dict[str, tuple[str, ...]] = {}
    local_by_id: dict[str, tuple[str, ...]] = {}
    effective_by_id: dict[str, tuple[str, ...]] = {}
    local_resolved_by_id: dict[str, bool] = {}
    resolver_by_id: dict[
        str, V075ConstructionPlanningInputResolverKindV2
    ] = {}
    source_id_by_id: dict[str, str | None] = {}
    inherited_scope_by_id: dict[str, str] = {}
    for record_id, upstream in by_id.items():
        portable_dependencies = tuple(
            upstream.portable_declared_dependency_record_ids
        )
        inherited_local = tuple(
            upstream.authority_local_semantic_dependency_record_ids
        )
        inherited_effective = tuple(
            upstream.effective_dependency_record_ids
        )
        if (
            tuple(sorted(set(portable_dependencies)))
            != portable_dependencies
            or tuple(sorted(set(inherited_local))) != inherited_local
            or tuple(sorted(set(inherited_effective)))
            != inherited_effective
            or set(inherited_effective)
            != set(portable_dependencies) | set(inherited_local)
        ):
            _fail("construction planning-input dependency lanes changed")
        role = role_by_id[record_id]
        if role == "CONSTRUCTION_PLANNING_INPUT":
            added = source_binding.source_dependency_record_ids
            resolver = (
                V075ConstructionPlanningInputResolverKindV2
                .CONSTRUCTION_PLANNING_INPUT_COMPILER_REPLAY
            )
            local_resolved = True
            source_id = source_binding.binding_id
        else:
            added = ()
            local_resolved = bool(
                upstream.local_semantic_authority_resolved
            )
            resolver = (
                V075ConstructionPlanningInputResolverKindV2
                .UPSTREAM_CONSTRUCTION_PRIVATE_REPLAY
                if local_resolved
                else V075ConstructionPlanningInputResolverKindV2
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
            _fail("construction planning-input dependency edge is foreign")
        portable_by_id[record_id] = portable_dependencies
        local_by_id[record_id] = local_dependencies
        effective_by_id[record_id] = effective_dependencies
        local_resolved_by_id[record_id] = local_resolved
        resolver_by_id[record_id] = resolver
        source_id_by_id[record_id] = source_id
        inherited_scope_by_id[record_id] = _upstream_scope_value(upstream)

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
                    ready, (by_id[successor].record_index, successor)
                )
    if len(order) != len(all_ids):
        _fail("construction planning-input effective DAG contains a cycle")

    resolved: dict[str, bool] = {}
    scopes: dict[str, V075ConstructionPlanningInputAuthorityScopeV2] = {}
    frontiers: dict[str, tuple[str, ...]] = {}
    depths: dict[str, int] = {}
    nodes: dict[str, V075ConstructionPlanningInputDependencyNodeV2] = {}
    for record_id in order:
        dependencies = effective_by_id[record_id]
        is_resolved = local_resolved_by_id[record_id] and all(
            resolved[item] for item in dependencies
        )
        role = role_by_id[record_id]
        if not is_resolved:
            scope = V075ConstructionPlanningInputAuthorityScopeV2.UNRESOLVED
        elif role == "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION":
            scope = (
                V075ConstructionPlanningInputAuthorityScopeV2
                .FULL_CONSTRUCTION_PRIVATE_REPLAY
            )
        elif role == "CONSTRUCTION_PLANNING_INPUT":
            scope = (
                V075ConstructionPlanningInputAuthorityScopeV2
                .FULL_CONSTRUCTION_COMPILER_REPLAY
            )
        elif (
            role
            in {
                "CONSTRUCTION_LINEAGE",
                "CONSTRUCTION_LIFECYCLE",
                "CONSTRUCTION_LIFECYCLE_VERIFICATION",
            }
            or inherited_scope_by_id[record_id]
            == "FULL_CONSTRUCTION_TRANSITIVE"
            or any(
                scopes[item]
                is not V075ConstructionPlanningInputAuthorityScopeV2
                .FULL_PUBLIC
                for item in dependencies
            )
        ):
            scope = (
                V075ConstructionPlanningInputAuthorityScopeV2
                .FULL_CONSTRUCTION_TRANSITIVE
            )
        elif inherited_scope_by_id[record_id] == (
            "FULL_CONSTRUCTION_PRIVATE_REPLAY"
        ):
            scope = (
                V075ConstructionPlanningInputAuthorityScopeV2
                .FULL_CONSTRUCTION_PRIVATE_REPLAY
            )
        else:
            scope = V075ConstructionPlanningInputAuthorityScopeV2.FULL_PUBLIC
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
                _fail("unresolved planning-input node lacks exact frontier")
        depth = 1 + max(
            (depths[item] for item in dependencies), default=0
        )
        if depth > MAX_DEPENDENCY_NODES:
            _fail("construction planning-input dependency depth exceeded")
        node = V075ConstructionPlanningInputDependencyNodeV2(
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
        scopes[record_id] = scope
        frontiers[record_id] = frontier
        depths[record_id] = depth
    return tuple(
        nodes[item.record_id]
        for item in sorted(
            upstream_nodes, key=lambda value: value.record_index
        )
    )


_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPlanningInputDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    private_replay_result: (
        private_replay.V075PortableConstructionPrivateReplayV2
    ) = field(repr=False)
    source_binding: V075ConstructionPlanningInputSourceBindingV2
    nodes: tuple[V075ConstructionPlanningInputDependencyNodeV2, ...]
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("construction planning-input DAG is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_dag_id",
            _hash("dependency_dag", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.bundle_id, "construction planning-input DAG bundle")
        _cid(self.typed_graph_id, "construction planning-input DAG graph")
        if (
            type(self.private_replay_result)
            is not private_replay.V075PortableConstructionPrivateReplayV2
            or type(self.source_binding)
            is not V075ConstructionPlanningInputSourceBindingV2
            or type(self.nodes) is not tuple
            or not self.nodes
            or any(
                type(item)
                is not V075ConstructionPlanningInputDependencyNodeV2
                for item in self.nodes
            )
        ):
            _fail("construction planning-input DAG is malformed")
        expected = _iterative_dependency_nodes(
            upstream_nodes=self.private_replay_result.dependency_dag.nodes,
            source_binding=self.source_binding,
        )
        if tuple(item.to_document() for item in self.nodes) != tuple(
            item.to_document() for item in expected
        ):
            _fail("construction planning-input DAG is stale")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_planning_input_dependency_dag.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "typed_graph_id": self.typed_graph_id,
            "private_replay_result_id": (
                self.private_replay_result.result_id
            ),
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
            _fail("construction planning-input DAG identity is stale")
        return self._dag_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "dependency_dag_id": self.dag_id}


_ROLE_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPlanningInputRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    dependency_dag_id: str
    role: str
    record_ids: tuple[str, ...]
    status: V075ConstructionPlanningInputRoleStatusV2
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("construction planning-input closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.bundle_id, "planning-input closure bundle")
        _cid(self.dependency_dag_id, "planning-input closure DAG")
        if (
            self.role not in _ROLE_SET
            or type(self.record_ids) is not tuple
            or len(self.record_ids) != 1
            or type(self.status)
            is not V075ConstructionPlanningInputRoleStatusV2
            or tuple(sorted(set(self.unresolved_frontier_record_ids)))
            != self.unresolved_frontier_record_ids
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
            or (
                self.status
                is V075ConstructionPlanningInputRoleStatusV2
                .FULL_CONSTRUCTION_COMPILER_REPLAY
                and (
                    self.unresolved_frontier_record_ids
                    or self.unresolved_frontier_roles
                )
            )
            or (
                self.status
                is V075ConstructionPlanningInputRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
                and not self.unresolved_frontier_record_ids
            )
        ):
            _fail("construction planning-input role closure is malformed")
        _cid(self.record_ids[0], "planning-input closure record")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_planning_input_role_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "dependency_dag_id": self.dependency_dag_id,
            "role": self.role,
            "record_ids": list(self.record_ids),
            "status": self.status.value,
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
        }

    @property
    def closure_id(self) -> str:
        self._validate()
        if self._closure_id != _hash("role_closure", self._payload()):
            _fail("construction planning-input closure identity is stale")
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}


def _build_role_closures(
    *,
    bundle_id: str,
    dependency_dag_id: str,
    nodes: tuple[V075ConstructionPlanningInputDependencyNodeV2, ...],
) -> tuple[V075ConstructionPlanningInputRoleClosureV2, ...]:
    result = []
    statuses = V075ConstructionPlanningInputRoleStatusV2
    for role in ROLE_ORDER:
        members = tuple(item for item in nodes if item.role == role)
        if len(members) != 1:
            _fail(f"construction planning-input role {role} is not singleton")
        member = members[0]
        if role == "CONSTRUCTION_PLANNING_INPUT":
            status = statuses.FULL_CONSTRUCTION_COMPILER_REPLAY
            if (
                not member.semantically_resolved
                or member.authority_scope
                is not V075ConstructionPlanningInputAuthorityScopeV2
                .FULL_CONSTRUCTION_COMPILER_REPLAY
            ):
                _fail("construction planning input did not close")
        else:
            status = statuses.STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            if (
                member.semantically_resolved
                or member.authority_scope
                is not V075ConstructionPlanningInputAuthorityScopeV2
                .UNRESOLVED
                or member.unresolved_frontier_record_ids
                != (member.record_id,)
                or member.unresolved_frontier_roles != (role,)
            ):
                _fail(f"downstream producer role {role} was falsely closed")
        result.append(
            V075ConstructionPlanningInputRoleClosureV2(
                _ROLE_CLOSURE_ISSUER,
                bundle_id,
                dependency_dag_id,
                role,
                (member.record_id,),
                status,
                member.unresolved_frontier_record_ids,
                member.unresolved_frontier_roles,
            )
        )
    return tuple(result)


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableConstructionPlanningInputReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075ConstructionPlanningInputTypedGraphV2 = field(
        repr=False
    )
    dependency_dag: V075ConstructionPlanningInputDependencyDAGV2 = field(
        repr=False
    )
    role_closures: tuple[
        V075ConstructionPlanningInputRoleClosureV2, ...
    ]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("construction planning-input result is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "planning-input result bundle"),
            (self.occurrence_id, "planning-input result occurrence"),
            (
                self.public_context_closure_id,
                "planning-input result public context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph)
            is not V075ConstructionPlanningInputTypedGraphV2
            or type(self.dependency_dag)
            is not V075ConstructionPlanningInputDependencyDAGV2
            or type(self.role_closures) is not tuple
            or tuple(item.role for item in self.role_closures) != ROLE_ORDER
            or any(
                type(item)
                is not V075ConstructionPlanningInputRoleClosureV2
                for item in self.role_closures
            )
            or self.typed_graph.bundle_id != self.bundle_id
            or self.typed_graph.occurrence_id != self.occurrence_id
            or self.typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or self.dependency_dag.bundle_id != self.bundle_id
            or self.dependency_dag.typed_graph_id
            != self.typed_graph.graph_id
            or self.dependency_dag.private_replay_result
            is not self.typed_graph.private_replay_result
            or self.dependency_dag.source_binding
            != self.typed_graph.source_binding
        ):
            _fail("construction planning-input result is malformed")
        expected = _build_role_closures(
            bundle_id=self.bundle_id,
            dependency_dag_id=self.dependency_dag.dag_id,
            nodes=self.dependency_dag.nodes,
        )
        if tuple(item.to_document() for item in self.role_closures) != tuple(
            item.to_document() for item in expected
        ):
            _fail("construction planning-input closures are stale")

    def _payload(self) -> dict[str, Any]:
        unresolved = tuple(
            sorted(
                {
                    role
                    for item in self.dependency_dag.nodes
                    if not item.semantically_resolved
                    for role in item.unresolved_frontier_roles
                }
            )
        )
        return {
            "schema": (
                "acfqp.v075_portable_construction_planning_input_replay.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "typed_graph_id": self.typed_graph.graph_id,
            "dependency_dag_id": self.dependency_dag.dag_id,
            "role_statuses": {
                item.role: item.status.value for item in self.role_closures
            },
            "role_closure_ids": [
                item.closure_id for item in self.role_closures
            ],
            "remaining_unresolved_frontier_roles": list(unresolved),
            "raw_contract_178_replayed": True,
            "construction_compiler_replayed": True,
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
            _fail("construction planning-input result identity is stale")
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
        replayed = replay_v075_portable_construction_planning_input_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
            private_generation_seed=private_generation_seed,
            private_salt=private_salt,
        )
        if replayed.to_document() != self.to_document():
            _fail("construction planning-input currentness check changed")

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "construction planning-input replay is in-memory-only"
        )


def replay_v075_portable_construction_planning_input_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075PortableConstructionPlanningInputReplayV2:
    """Replay raw 1.78, then the sole registered construction compiler."""

    # This is deliberately the first operation.  Do not inspect, type-check,
    # parse, hash, or retain any of the five inputs before raw 1.78 succeeds.
    try:
        private_result = (
            private_replay
            .replay_v075_portable_construction_private_replay_v2(
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=public_context_closure_bytes,
                private_generation_seed=private_generation_seed,
                private_salt=private_salt,
            )
        )
        hardened, m0_result, _m0_graph, schedule = (
            _exact_hardened_parts(private_result)
        )
        lineage = private_result.typed_graph.construction_lineage
        lifecycle = private_result.typed_graph.construction_lifecycle
        compiled = planning.compile_v075_construction_planning_input_v2(
            repository_root=repository_root,
            schedule=schedule,
            lineage=lineage,
            lifecycle=lifecycle,
        )
        if type(compiled) is not planning.V075ConstructionPlanningInputV2:
            _fail(_REPLAY_MISMATCH)
        target = _sole_by_role(
            private_result.typed_graph.target_record_bindings,
            "CONSTRUCTION_PLANNING_INPUT",
            "private replay target",
        )
        if (
            target.semantic_artifact_id != compiled.input_id
            or target.canonical_artifact_bytes != _raw(compiled)
        ):
            _fail(_REPLAY_MISMATCH)
        standalone_model, model_binding = _sole_model_binding(
            hardened, compiled.model.model_id
        )
        if _raw(compiled.model) != _raw(standalone_model):
            _fail(_REPLAY_MISMATCH)
        _validate_complete_row_evidence(
            compiled=compiled,
            lineage=lineage,
            lifecycle=lifecycle,
        )
        source_binding = _build_source_binding(
            replayed=private_result,
            hardened=hardened,
            m0_result=m0_result,
            schedule=schedule,
            compiled=compiled,
            target=target,
            model_binding=model_binding,
        )
        graph = V075ConstructionPlanningInputTypedGraphV2(
            _TYPED_GRAPH_ISSUER,
            private_result.bundle_id,
            private_result.occurrence_id,
            private_result.public_context_closure_id,
            private_result,
            schedule,
            standalone_model,
            compiled,
            target,
            model_binding,
            source_binding,
        )
        nodes = _iterative_dependency_nodes(
            upstream_nodes=private_result.dependency_dag.nodes,
            source_binding=source_binding,
        )
        dag = V075ConstructionPlanningInputDependencyDAGV2(
            _DAG_ISSUER,
            private_result.bundle_id,
            graph.graph_id,
            private_result,
            source_binding,
            nodes,
        )
        closures = _build_role_closures(
            bundle_id=private_result.bundle_id,
            dependency_dag_id=dag.dag_id,
            nodes=nodes,
        )
        result = V075PortableConstructionPlanningInputReplayV2(
            _RESULT_ISSUER,
            private_result.bundle_id,
            private_result.occurrence_id,
            private_result.public_context_closure_id,
            graph,
            dag,
            closures,
        )
        if len(canonical_json_bytes(result.to_document())) > MAX_OUTPUT_BYTES:
            _fail("construction planning-input public summary exceeds cap")
        return result
    except Exception:
        # Compiler and private-replay failures intentionally share one public
        # message and suppress their causes, which might contain private data.
        raise V075PortableConstructionPlanningInputV2InvariantViolation(
            _REPLAY_MISMATCH
        ) from None


def assert_v075_portable_construction_planning_input_production_gate_v2(
    result: V075PortableConstructionPlanningInputReplayV2,
) -> NoReturn:
    if type(result) is not V075PortableConstructionPlanningInputReplayV2:
        _fail("construction planning-input gate rejects duck-typed results")
    _ = result.result_id
    raise V075PortableConstructionPlanningInputProductionV2NotReady(
        "contract 1.79 is construction-only; downstream reconciliation, "
        "source/code provenance, accounting, and production gates remain open"
    )


__all__ = [
    "B3_INPUT_ALLOWED",
    "CODE_PROVENANCE_COMPLETE",
    "CONSTRUCTION_EPHEMERAL_PRIVATE_INPUT_REQUIRED",
    "CONSTRUCTION_PLANNING_INPUT_COMPILER_REPLAYED",
    "CONSTRUCTION_PRIVATE_REPLAY_REQUIRED",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "J0_ACCESS_ALLOWED",
    "K7_INPUT_ALLOWED",
    "KERNEL_ACCESS_ALLOWED",
    "MAX_DEPENDENCY_NODES",
    "MAX_OUTPUT_BYTES",
    "OBSERVER_OPEN_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OPERATIONAL_REGISTRIES_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRODUCTION_AUTHORIZING",
    "PRODUCTION_COMPILER_ALLOWED",
    "PRODUCTION_PRIVATE_INPUT_CHANNEL_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "SOURCE_ROLE_ORDER",
    "V075ConstructionPlanningInputAuthorityScopeV2",
    "V075ConstructionPlanningInputDependencyDAGV2",
    "V075ConstructionPlanningInputDependencyNodeV2",
    "V075ConstructionPlanningInputResolverKindV2",
    "V075ConstructionPlanningInputRoleClosureV2",
    "V075ConstructionPlanningInputRoleStatusV2",
    "V075ConstructionPlanningInputSourceBindingV2",
    "V075ConstructionPlanningInputTypedGraphV2",
    "V075PortableConstructionPlanningInputProductionV2NotReady",
    "V075PortableConstructionPlanningInputReplayV2",
    "V075PortableConstructionPlanningInputV2InvariantViolation",
    "WORKER_LAUNCH_ALLOWED",
    "assert_v075_portable_construction_planning_input_production_gate_v2",
    "replay_v075_portable_construction_planning_input_v2",
]
