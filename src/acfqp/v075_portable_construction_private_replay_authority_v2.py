"""Portable construction-private replay authority for V0-075.

This construction-only authority starts with the hardened contract-1.77
planning replay.  Only after that public replay succeeds does it accept the
ephemeral generation seed and salt needed to regenerate the registered
private environment.  The regenerated opaque commitment must equal the
commitment already bound by the public context, authorization, namespace,
observer-open binding, and occurrence.

The private values never become fields, documents, logs, exception text,
content identities, or emitted secret digests.  This authority does not hash
them directly; they are consumed only by the frozen cryptographic generator,
commitment sealer, and issuer-owned public producer APIs for:

* the exact batch-journal closure verification;
* the exact construction lineage;
* the exact construction lifecycle; and
* the exact construction lifecycle byte verification.

The returned object is in-memory-only and contains only nonsecret typed
producer results and public/content-addressed summaries.  It deliberately
does not compile the construction planning input.  Aggregate currentness has
no no-argument shortcut: callers must supply the same five raw authorities to
``assert_current`` so the complete raw/private replay is executed again.
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
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle
from acfqp import v075_batched_observer_authority_v2 as lineage
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_planning_authority_v2 as m2_planning
from acfqp import v075_portable_public_context_closure_v2 as public_context
from acfqp import v075_private_environment_generation_profile_v1 as generation
from acfqp import v075_private_observer_boundary_v2 as observer


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.78.0"
PROFILE_KEY = "v075_portable_construction_private_replay_authority_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
PRIVATE_REPLAY_INPUTS_ACCEPTED = True
CONSTRUCTION_EPHEMERAL_PRIVATE_INPUT_REQUIRED = True
PRODUCTION_PRIVATE_INPUT_CHANNEL_ALLOWED = False
PRIVATE_REPLAY_PERFORMED = True
B3_INPUT_ALLOWED = False
K7_INPUT_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
J0_ACCESS_ALLOWED = False
OBSERVER_OPEN_ALLOWED = False
OPERATIONAL_REGISTRIES_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_PRIVATE_REPLAY_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_PRIVATE_REPLAY_COMPLETE_"
    "CONSTRUCTION_PLANNING_INPUT_AUTHORITY_UNRESOLVED"
)
MAX_DEPENDENCY_NODES = 4096
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_PRIVATE_GENERATION_SEED_BYTES = 4096
MAX_PRIVATE_SALT_BYTES = 4096

ROLE_ORDER = (
    "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",
    "CONSTRUCTION_LINEAGE",
    "CONSTRUCTION_LIFECYCLE",
    "CONSTRUCTION_LIFECYCLE_VERIFICATION",
    "CONSTRUCTION_PLANNING_INPUT",
)
PRIVATE_REPLAY_ROLE_ORDER = ROLE_ORDER[:4]
_ROLE_SET = frozenset(ROLE_ORDER)
_PRIVATE_ROLE_SET = frozenset(PRIVATE_REPLAY_ROLE_ORDER)

_ROLE_SCHEMA = MappingProxyType(
    {
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": (
            "acfqp.v075_observer_batch_journal_closure_verification.v2"
        ),
        "CONSTRUCTION_LINEAGE": (
            "acfqp.v075_batch_occurrence_lineage.v2"
        ),
        "CONSTRUCTION_LIFECYCLE": (
            "acfqp.v075_batch_occurrence_lifecycle.v2"
        ),
        "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
            "acfqp.v075_batch_occurrence_lifecycle_verification.v2"
        ),
        "CONSTRUCTION_PLANNING_INPUT": (
            "acfqp.v075_batch_planning_construction_input.v2"
        ),
    }
)

DOMAIN_TAGS = MappingProxyType(
    {
        "record_binding": (
            "acfqp:v075-portable-private-replay-record-binding:v2"
        ),
        "source_binding": (
            "acfqp:v075-portable-private-replay-source-binding:v2"
        ),
        "typed_graph": (
            "acfqp:v075-portable-private-replay-typed-graph:v2"
        ),
        "dependency_dag": (
            "acfqp:v075-portable-private-replay-dependency-dag:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-private-replay-role-closure:v2"
        ),
        "aggregate": (
            "acfqp:v075-portable-construction-private-replay-authority:v2"
        ),
    }
)

_PRIVATE_MISMATCH = (
    "construction private replay did not match the registered public context"
)


class V075PortableConstructionPrivateReplayV2InvariantViolation(ValueError):
    """A raw authority, private replay, or transitive closure was invalid."""


class V075PortableConstructionPrivateReplayProductionV2NotReady(RuntimeError):
    """This construction-only replay cannot authorize production."""


class V075ConstructionPrivateReplayRoleStatusV2(str, Enum):
    FULL_CONSTRUCTION_PRIVATE_REPLAY = (
        "FULL_CONSTRUCTION_PRIVATE_REPLAY"
    )
    FULL_CONSTRUCTION_TRANSITIVE = "FULL_CONSTRUCTION_TRANSITIVE"
    STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED = (
        "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
    )


class V075ConstructionPrivateReplayResolverKindV2(str, Enum):
    UPSTREAM_M2_PLANNING = "UPSTREAM_M2_PLANNING"
    CONSTRUCTION_PRIVATE_CLOSURE_REPLAY = (
        "CONSTRUCTION_PRIVATE_CLOSURE_REPLAY"
    )
    CONSTRUCTION_LINEAGE_TRANSITIVE = (
        "CONSTRUCTION_LINEAGE_TRANSITIVE"
    )
    CONSTRUCTION_LIFECYCLE_TRANSITIVE = (
        "CONSTRUCTION_LIFECYCLE_TRANSITIVE"
    )
    CONSTRUCTION_LIFECYCLE_VERIFICATION_TRANSITIVE = (
        "CONSTRUCTION_LIFECYCLE_VERIFICATION_TRANSITIVE"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


class V075ConstructionPrivateReplayAuthorityScopeV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    FULL_CONSTRUCTION_PRIVATE_REPLAY = (
        "FULL_CONSTRUCTION_PRIVATE_REPLAY"
    )
    FULL_CONSTRUCTION_TRANSITIVE = "FULL_CONSTRUCTION_TRANSITIVE"
    UNRESOLVED = "UNRESOLVED"


def _fail(message: str) -> NoReturn:
    raise V075PortableConstructionPrivateReplayV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableConstructionPrivateReplayV2InvariantViolation(
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
        raise V075PortableConstructionPrivateReplayV2InvariantViolation(
            "construction private replay public identity is malformed"
        ) from error


def _raw(value: Any) -> bytes:
    return canonical_json_bytes(value.to_document())


def _public_context_resolution(
    *,
    repository_root: str | Path,
    public_context_closure_bytes: bytes,
) -> tuple[
    public_context.V075PortablePublicContextEvidenceClosureV2,
    public_context.V075PortablePublicContextRawResolutionV2,
]:
    closure = (
        public_context
        .verify_v075_portable_public_context_evidence_closure_bytes_v2(
            repository_root=repository_root,
            raw=public_context_closure_bytes,
        )
    )
    records = {item.role: item for item in closure.dependency_records}
    roles = tuple(public_context.V075PortablePublicContextDependencyRoleV2)
    if set(records) != set(roles):
        _fail(_PRIVATE_MISMATCH)
    resolution = (
        public_context.resolve_v075_portable_public_context_raw_dependencies_v2(
            repository_root=repository_root,
            source_manifest_bytes=canonical_json_bytes(
                closure.source_manifest.to_document()
            ),
            namespace_bytes=records[roles[0]].canonical_artifact_bytes,
            observer_open_authorization_bytes=(
                records[roles[1]].canonical_artifact_bytes
            ),
            private_reveal_verification_attestation_bytes=(
                records[roles[2]].canonical_artifact_bytes
            ),
        )
    )
    if (
        tuple(item.to_document() for item in resolution.records)
        != tuple(item.to_document() for item in closure.dependency_records)
        or tuple(item.to_document() for item in resolution.attestations)
        != tuple(
            item.to_document() for item in closure.dependency_attestations
        )
    ):
        _fail(_PRIVATE_MISMATCH)
    return closure, resolution


def _hardened_graphs(
    upstream: m2_planning.V075PortablePlanningReplayV2,
) -> tuple[Any, Any, Any]:
    """Return exact root, M1A, and M0 graphs from the hardened 1.77 chain."""

    if type(upstream) is not m2_planning.V075PortablePlanningReplayV2:
        _fail("construction private replay requires exact hardened 1.77")
    _ = upstream.result_id
    try:
        dynamic = upstream.typed_graph.m2_dynamic_child_result
        live_epoch_result = dynamic.typed_graph.m2_live_epoch_result
        lifecycle_result = (
            live_epoch_result.typed_graph.m2_lifecycle_result
        )
        lineage_result = (
            lifecycle_result.typed_graph.m2_lineage_result
        )
        root_result = lineage_result.typed_graph.m2_result
        root_graph = root_result.typed_graph
        control_graph = root_graph.m1b_result.typed_graph
        m1a_graph = control_graph.m1a_result.typed_graph
        m0_graph = m1a_graph.m0_result.typed_graph
    except (AttributeError, TypeError) as error:
        raise V075PortableConstructionPrivateReplayV2InvariantViolation(
            "hardened 1.77 omitted its exact public producer graph"
        ) from error
    if (
        root_graph.occurrence.occurrence_id != upstream.occurrence_id
        or m1a_graph.closure.occurrence_id != upstream.occurrence_id
        or m0_graph.occurrence.occurrence_id != upstream.occurrence_id
        or root_graph.occurrence != m0_graph.occurrence
    ):
        _fail("hardened 1.77 producer graph crossed occurrence identities")
    return root_graph, m1a_graph, m0_graph


_RECORD_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPrivateReplayRecordBindingV2:
    _issuer: InitVar[object]
    record_id: str
    record_index: int
    role: str
    artifact_schema: str
    semantic_artifact_id: str
    dependency_record_ids: tuple[str, ...]
    canonical_artifact_bytes: bytes = field(repr=False)
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RECORD_BINDING_ISSUER:
            _fail("private replay record binding is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_binding_id",
            _hash("record_binding", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.record_id, "private replay portable record")
        _cid(
            self.semantic_artifact_id,
            "private replay semantic artifact",
        )
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _ROLE_SET
            or self.artifact_schema != _ROLE_SCHEMA[self.role]
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
            or type(self.canonical_artifact_bytes) is not bytes
            or not self.canonical_artifact_bytes
        ):
            _fail("private replay record binding is malformed")
        for dependency in self.dependency_record_ids:
            _cid(dependency, "private replay portable dependency")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_private_replay_record_binding.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "artifact_schema": self.artifact_schema,
            "semantic_artifact_id": self.semantic_artifact_id,
            "dependency_record_ids": list(self.dependency_record_ids),
            "canonical_artifact_sha256": hashlib.sha256(
                self.canonical_artifact_bytes
            ).hexdigest(),
            "canonical_artifact_byte_count": len(
                self.canonical_artifact_bytes
            ),
        }

    @property
    def binding_id(self) -> str:
        self._validate()
        if self._binding_id != _hash("record_binding", self._payload()):
            _fail("private replay record binding identity is stale")
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


def _record_binding(
    record: portable.V075PortableEvidenceArtifactRecordV2,
) -> V075ConstructionPrivateReplayRecordBindingV2:
    if type(record) is not portable.V075PortableEvidenceArtifactRecordV2:
        _fail("private replay rejects a caller-created portable record")
    return V075ConstructionPrivateReplayRecordBindingV2(
        _RECORD_BINDING_ISSUER,
        record.record_id,
        record.index,
        record.role,
        record.artifact_schema,
        record.semantic_artifact_id,
        tuple(record.dependency_record_ids),
        record.canonical_artifact_bytes,
    )


_SOURCE_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPrivateReplaySourceBindingV2:
    _issuer: InitVar[object]
    target_record_id: str
    target_role: str
    target_semantic_artifact_id: str
    resolver_kind: V075ConstructionPrivateReplayResolverKindV2
    source_dependency_record_ids: tuple[str, ...]
    public_context_record_ids: tuple[str, ...]
    public_context_semantic_artifact_ids: tuple[str, ...]
    public_context_closure_id: str
    private_generation_profile_id: str
    opaque_environment_commitment_id: str
    observer_open_authorization_id: str
    target_tape_namespace_id: str
    occurrence_id: str
    signed_batch_journal_closure_id: str
    producer_artifact_sha256: str
    producer_artifact_byte_count: int
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_BINDING_ISSUER:
            _fail("construction private replay source is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_binding_id",
            _hash("source_binding", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.target_record_id, "private replay source target"),
            (
                self.target_semantic_artifact_id,
                "private replay source semantic artifact",
            ),
            (
                self.public_context_closure_id,
                "private replay public context",
            ),
            (
                self.private_generation_profile_id,
                "private generation profile",
            ),
            (
                self.opaque_environment_commitment_id,
                "private replay public commitment",
            ),
            (
                self.observer_open_authorization_id,
                "private replay authorization",
            ),
            (
                self.target_tape_namespace_id,
                "private replay namespace",
            ),
            (self.occurrence_id, "private replay occurrence"),
            (
                self.signed_batch_journal_closure_id,
                "private replay batch closure",
            ),
            (
                self.producer_artifact_sha256,
                "private replay producer bytes",
            ),
        ):
            _cid(value, label)
        sequences = (
            self.source_dependency_record_ids,
            self.public_context_record_ids,
            self.public_context_semantic_artifact_ids,
        )
        if (
            self.target_role not in _PRIVATE_ROLE_SET
            or type(self.resolver_kind)
            is not V075ConstructionPrivateReplayResolverKindV2
            or self.resolver_kind is not _resolver_for_role(self.target_role)
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in sequences
            )
            or len(self.public_context_record_ids) != 3
            or len(self.public_context_semantic_artifact_ids) != 3
            or type(self.producer_artifact_byte_count) is not int
            or self.producer_artifact_byte_count <= 0
        ):
            _fail("construction private replay source binding is malformed")
        for value in (
            *self.source_dependency_record_ids,
            *self.public_context_record_ids,
            *self.public_context_semantic_artifact_ids,
        ):
            _cid(value, "construction private replay source")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_private_replay_source_binding.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "target_record_id": self.target_record_id,
            "target_role": self.target_role,
            "target_semantic_artifact_id": (
                self.target_semantic_artifact_id
            ),
            "resolver_kind": self.resolver_kind.value,
            "source_dependency_record_ids": list(
                self.source_dependency_record_ids
            ),
            "public_context_record_ids": list(
                self.public_context_record_ids
            ),
            "public_context_semantic_artifact_ids": list(
                self.public_context_semantic_artifact_ids
            ),
            "public_context_closure_id": self.public_context_closure_id,
            "private_generation_profile_id": (
                self.private_generation_profile_id
            ),
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment_id
            ),
            "observer_open_authorization_id": (
                self.observer_open_authorization_id
            ),
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "occurrence_id": self.occurrence_id,
            "signed_batch_journal_closure_id": (
                self.signed_batch_journal_closure_id
            ),
            "producer_artifact_sha256": self.producer_artifact_sha256,
            "producer_artifact_byte_count": (
                self.producer_artifact_byte_count
            ),
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
        }

    @property
    def binding_id(self) -> str:
        self._validate()
        if self._binding_id != _hash("source_binding", self._payload()):
            _fail("construction private replay source identity is stale")
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


def _resolver_for_role(
    role: str,
) -> V075ConstructionPrivateReplayResolverKindV2:
    mapping = {
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": (
            V075ConstructionPrivateReplayResolverKindV2
            .CONSTRUCTION_PRIVATE_CLOSURE_REPLAY
        ),
        "CONSTRUCTION_LINEAGE": (
            V075ConstructionPrivateReplayResolverKindV2
            .CONSTRUCTION_LINEAGE_TRANSITIVE
        ),
        "CONSTRUCTION_LIFECYCLE": (
            V075ConstructionPrivateReplayResolverKindV2
            .CONSTRUCTION_LIFECYCLE_TRANSITIVE
        ),
        "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
            V075ConstructionPrivateReplayResolverKindV2
            .CONSTRUCTION_LIFECYCLE_VERIFICATION_TRANSITIVE
        ),
    }
    try:
        return mapping[role]
    except KeyError as error:
        raise V075PortableConstructionPrivateReplayV2InvariantViolation(
            "private replay source role is not registered"
        ) from error


def _build_source_bindings(
    *,
    target_bindings: tuple[
        V075ConstructionPrivateReplayRecordBindingV2,
        ...,
    ],
    context_closure: (
        public_context.V075PortablePublicContextEvidenceClosureV2
    ),
    generation_profile: (
        generation.V075PrivateEnvironmentGenerationProfileV1
    ),
    occurrence_id: str,
    batch_closure_id: str,
    producer_raw_by_role: Mapping[str, bytes],
) -> tuple[V075ConstructionPrivateReplaySourceBindingV2, ...]:
    by_role = {item.role: item for item in target_bindings}
    if set(by_role) != _ROLE_SET:
        _fail("private replay five-role registry is incomplete")
    source_dependencies = {
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": (),
        "CONSTRUCTION_LINEAGE": (
            by_role[
                "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION"
            ].record_id,
        ),
        "CONSTRUCTION_LIFECYCLE": (
            by_role["CONSTRUCTION_LINEAGE"].record_id,
        ),
        "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
            by_role["CONSTRUCTION_LIFECYCLE"].record_id,
        ),
    }
    public_records = tuple(context_closure.dependency_records)
    public_record_ids = tuple(sorted(item.record_id for item in public_records))
    public_semantic_ids = tuple(
        sorted(item.semantic_artifact_id for item in public_records)
    )
    authorization_record = next(
        item
        for item in public_records
        if item.role
        is public_context.V075PortablePublicContextDependencyRoleV2
        .OBSERVER_OPEN_AUTHORIZATION
    )
    namespace_record = next(
        item
        for item in public_records
        if item.role
        is public_context.V075PortablePublicContextDependencyRoleV2
        .PUBLIC_TARGET_TAPE_NAMESPACE
    )
    result = []
    for role in PRIVATE_REPLAY_ROLE_ORDER:
        target = by_role[role]
        raw = producer_raw_by_role[role]
        result.append(
            V075ConstructionPrivateReplaySourceBindingV2(
                _SOURCE_BINDING_ISSUER,
                target.record_id,
                role,
                target.semantic_artifact_id,
                _resolver_for_role(role),
                tuple(sorted(source_dependencies[role])),
                public_record_ids,
                public_semantic_ids,
                context_closure.closure_id,
                generation_profile.profile_id,
                context_closure.opaque_environment_commitment_id,
                authorization_record.semantic_artifact_id,
                namespace_record.semantic_artifact_id,
                occurrence_id,
                batch_closure_id,
                hashlib.sha256(raw).hexdigest(),
                len(raw),
            )
        )
    return tuple(result)


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPrivateReplayTypedGraphV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    hardened_planning_result: (
        m2_planning.V075PortablePlanningReplayV2
    ) = field(repr=False)
    public_context_resolution: (
        public_context.V075PortablePublicContextRawResolutionV2
    ) = field(repr=False)
    private_generation_profile: (
        generation.V075PrivateEnvironmentGenerationProfileV1
    ) = field(repr=False)
    closure_verification: (
        observer.V075ObserverBatchClosureVerificationV2
    ) = field(repr=False)
    construction_lineage: lineage.V075BatchOccurrenceLineageV2 = field(
        repr=False
    )
    construction_lifecycle: (
        lifecycle.V075BatchOccurrenceLifecycleClosureV2
    ) = field(repr=False)
    construction_lifecycle_verification: (
        lifecycle.V075BatchOccurrenceLifecycleVerificationV2
    ) = field(repr=False)
    target_record_bindings: tuple[
        V075ConstructionPrivateReplayRecordBindingV2,
        ...,
    ] = field(repr=False)
    source_bindings: tuple[
        V075ConstructionPrivateReplaySourceBindingV2,
        ...,
    ]
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("construction private replay typed graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._payload()),
        )

    def _producer_raw(self) -> Mapping[str, bytes]:
        return MappingProxyType(
            {
                "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": _raw(
                    self.closure_verification
                ),
                "CONSTRUCTION_LINEAGE": (
                    self.construction_lineage.canonical_bytes
                ),
                "CONSTRUCTION_LIFECYCLE": (
                    self.construction_lifecycle.canonical_bytes
                ),
                "CONSTRUCTION_LIFECYCLE_VERIFICATION": _raw(
                    self.construction_lifecycle_verification
                ),
            }
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "private replay graph bundle"),
            (self.occurrence_id, "private replay graph occurrence"),
            (
                self.public_context_closure_id,
                "private replay graph public context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.hardened_planning_result)
            is not m2_planning.V075PortablePlanningReplayV2
            or type(self.public_context_resolution)
            is not public_context.V075PortablePublicContextRawResolutionV2
            or type(self.private_generation_profile)
            is not generation.V075PrivateEnvironmentGenerationProfileV1
            or type(self.closure_verification)
            is not observer.V075ObserverBatchClosureVerificationV2
            or type(self.construction_lineage)
            is not lineage.V075BatchOccurrenceLineageV2
            or self.construction_lineage.scope
            is not lineage.V075BatchOccurrenceAuthorityScopeV2
            .CONSTRUCTION_ONLY
            or type(self.construction_lifecycle)
            is not lifecycle.V075BatchOccurrenceLifecycleClosureV2
            or self.construction_lifecycle.scope
            is not lifecycle.V075BatchLifecycleAuthorityScopeV2
            .CONSTRUCTION_ONLY
            or type(self.construction_lifecycle_verification)
            is not lifecycle.V075BatchOccurrenceLifecycleVerificationV2
            or self.construction_lifecycle_verification.scope
            is not lifecycle.V075BatchLifecycleAuthorityScopeV2
            .CONSTRUCTION_ONLY
            or type(self.target_record_bindings) is not tuple
            or tuple(item.role for item in self.target_record_bindings)
            != ROLE_ORDER
            or any(
                type(item)
                is not V075ConstructionPrivateReplayRecordBindingV2
                for item in self.target_record_bindings
            )
            or type(self.source_bindings) is not tuple
            or tuple(item.target_role for item in self.source_bindings)
            != PRIVATE_REPLAY_ROLE_ORDER
            or any(
                type(item)
                is not V075ConstructionPrivateReplaySourceBindingV2
                for item in self.source_bindings
            )
        ):
            _fail("construction private replay typed graph is malformed")
        resolution = self.public_context_resolution
        expected_profile = (
            generation
            .freeze_v075_private_environment_generation_profile_v1()
        )
        if (
            self.hardened_planning_result.bundle_id != self.bundle_id
            or self.hardened_planning_result.occurrence_id
            != self.occurrence_id
            or self.hardened_planning_result.public_context_closure_id
            != self.public_context_closure_id
            or self.construction_lineage.occurrence_identity.occurrence_id
            != self.occurrence_id
            or self.construction_lineage.closure_verification
            != self.closure_verification
            or self.closure_verification.closure_id
            != self.construction_lineage.closure.closure_id
            or self.closure_verification.occurrence_id
            != self.occurrence_id
            or self.closure_verification.batch_ids
            != tuple(
                item.batch.batch_id
                for item in self.construction_lineage.closure.entries
            )
            or self.closure_verification.observer_open_binding_id
            != (
                self.construction_lineage.closure.authority_binding.binding_id
            )
            or self.closure_verification.observer_open_authorization_id
            != (
                self.construction_lineage.closure.authority_binding
                .authorization_id
            )
            or self.closure_verification.private_reveal_attestation_id
            != (
                self.construction_lineage.closure.authority_binding
                .private_reveal_attestation_id
            )
            or self.closure_verification.replayed_batch_count
            != len(self.construction_lineage.closure.entries)
            or self.construction_lifecycle.occurrence_id
            != self.occurrence_id
            or self.construction_lifecycle_verification.occurrence_id
            != self.occurrence_id
            or self.private_generation_profile != expected_profile
            or resolution.namespace.family
            != self.private_generation_profile.family
            or resolution.authorization.opaque_environment_commitment
            != resolution.namespace.environment_commitment
            or (
                self.construction_lineage.closure.authority_binding.namespace
            )
            != resolution.namespace
            or (
                self.construction_lineage.closure.authority_binding
                .authorization_id
            )
            != resolution.authorization.authorization_id
            or (
                self.construction_lineage.closure.authority_binding
                .private_reveal_attestation_id
            )
            != resolution.reveal_attestation.attestation_id
            or self.construction_lifecycle.lineage_id
            != self.construction_lineage.lineage_id
            or (
                self.construction_lifecycle_verification
                .lifecycle_closure_id
            )
            != self.construction_lifecycle.closure_id
        ):
            _fail("construction private replay crossed hardened identities")
        producer = self._producer_raw()
        by_role = {item.role: item for item in self.target_record_bindings}
        if set(by_role) != _ROLE_SET:
            _fail("construction private replay target registry changed")
        semantic_ids = {
            "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": (
                self.closure_verification.verification_id
            ),
            "CONSTRUCTION_LINEAGE": self.construction_lineage.lineage_id,
            "CONSTRUCTION_LIFECYCLE": (
                self.construction_lifecycle.closure_id
            ),
            "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
                self.construction_lifecycle_verification.verification_id
            ),
        }
        for role in PRIVATE_REPLAY_ROLE_ORDER:
            if (
                by_role[role].semantic_artifact_id != semantic_ids[role]
                or by_role[role].canonical_artifact_bytes
                != producer[role]
            ):
                _fail("private producer bytes differ from portable singleton")
        sources = {item.target_role: item for item in self.source_bindings}
        if set(sources) != _PRIVATE_ROLE_SET:
            _fail("construction private replay source registry changed")
        expected_source_dependencies = {
            "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": (),
            "CONSTRUCTION_LINEAGE": (
                by_role[
                    "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION"
                ].record_id,
            ),
            "CONSTRUCTION_LIFECYCLE": (
                by_role["CONSTRUCTION_LINEAGE"].record_id,
            ),
            "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
                by_role["CONSTRUCTION_LIFECYCLE"].record_id,
            ),
        }
        for role in PRIVATE_REPLAY_ROLE_ORDER:
            source = sources[role]
            if (
                source.target_record_id != by_role[role].record_id
                or source.target_semantic_artifact_id
                != semantic_ids[role]
                or source.source_dependency_record_ids
                != tuple(sorted(expected_source_dependencies[role]))
                or source.producer_artifact_sha256
                != hashlib.sha256(producer[role]).hexdigest()
                or source.producer_artifact_byte_count
                != len(producer[role])
                or source.public_context_record_ids
                != tuple(
                    sorted(
                        item.record_id for item in resolution.records
                    )
                )
                or source.public_context_semantic_artifact_ids
                != tuple(
                    sorted(
                        item.semantic_artifact_id
                        for item in resolution.records
                    )
                )
                or source.public_context_closure_id
                != self.public_context_closure_id
                or source.private_generation_profile_id
                != self.private_generation_profile.profile_id
                or source.opaque_environment_commitment_id
                != (
                    resolution.namespace.environment_commitment.commitment_id
                )
                or source.observer_open_authorization_id
                != resolution.authorization.authorization_id
                or source.target_tape_namespace_id
                != resolution.namespace.target_tape_namespace_id
                or source.occurrence_id != self.occurrence_id
                or source.signed_batch_journal_closure_id
                != self.construction_lineage.closure.closure_id
            ):
                _fail("construction private replay source binding changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_private_replay_typed_graph.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "hardened_planning_result_id": (
                self.hardened_planning_result.result_id
            ),
            "private_generation_profile_id": (
                self.private_generation_profile.profile_id
            ),
            "opaque_environment_commitment_id": (
                self.public_context_resolution.namespace
                .environment_commitment.commitment_id
            ),
            "observer_open_authorization_id": (
                self.public_context_resolution.authorization.authorization_id
            ),
            "target_tape_namespace_id": (
                self.public_context_resolution.namespace
                .target_tape_namespace_id
            ),
            "closure_verification_id": (
                self.closure_verification.verification_id
            ),
            "construction_lineage_id": (
                self.construction_lineage.lineage_id
            ),
            "construction_lifecycle_id": (
                self.construction_lifecycle.closure_id
            ),
            "construction_lifecycle_verification_id": (
                self.construction_lifecycle_verification.verification_id
            ),
            "target_record_binding_ids": [
                item.binding_id for item in self.target_record_bindings
            ],
            "source_binding_ids": [
                item.binding_id for item in self.source_bindings
            ],
            "exact_singleton_private_role_registries": True,
            "issuer_owned_public_producer_apis_used": True,
            "construction_planning_input_compiler_called": False,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
        }

    @property
    def graph_id(self) -> str:
        self._validate()
        if self._graph_id != _hash("typed_graph", self._payload()):
            _fail("construction private replay graph identity is stale")
        return self._graph_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "typed_graph_id": self.graph_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "construction private replay typed graph is in-memory-only"
        )


@dataclass(frozen=True, slots=True)
class V075ConstructionPrivateReplayDependencyNodeV2:
    record_id: str
    record_index: int
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    source_binding_id: str | None
    resolver_kind: V075ConstructionPrivateReplayResolverKindV2
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    authority_scope: V075ConstructionPrivateReplayAuthorityScopeV2
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    dependency_depth: int

    def __post_init__(self) -> None:
        _cid(self.record_id, "private replay dependency node")
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
            is not V075ConstructionPrivateReplayResolverKindV2
            or type(self.local_semantic_authority_resolved) is not bool
            or type(self.semantically_resolved) is not bool
            or type(self.authority_scope)
            is not V075ConstructionPrivateReplayAuthorityScopeV2
            or type(self.dependency_depth) is not int
            or not 0 < self.dependency_depth <= MAX_DEPENDENCY_NODES
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
            or (
                self.semantically_resolved
                != (
                    self.authority_scope
                    is not V075ConstructionPrivateReplayAuthorityScopeV2
                    .UNRESOLVED
                )
            )
        ):
            _fail("construction private replay dependency node is malformed")
        if self.source_binding_id is not None:
            _cid(self.source_binding_id, "private replay dependency source")
        for value in (
            *self.effective_dependency_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "private replay dependency edge")

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


def _iterative_dependency_nodes(
    *,
    upstream_nodes: tuple[Any, ...],
    source_bindings: tuple[
        V075ConstructionPrivateReplaySourceBindingV2,
        ...,
    ],
) -> tuple[V075ConstructionPrivateReplayDependencyNodeV2, ...]:
    if (
        type(upstream_nodes) is not tuple
        or not upstream_nodes
        or len(upstream_nodes) > MAX_DEPENDENCY_NODES
        or type(source_bindings) is not tuple
        or tuple(item.target_role for item in source_bindings)
        != PRIVATE_REPLAY_ROLE_ORDER
    ):
        _fail("construction private replay requires one bounded exact DAG")
    upstream_by_id: dict[str, Any] = {}
    for expected_index, item in enumerate(upstream_nodes):
        if (
            item.record_index != expected_index
            or item.record_id in upstream_by_id
        ):
            _fail("construction private replay upstream DAG is malformed")
        upstream_by_id[item.record_id] = item
    binding_by_target = {
        item.target_record_id: item for item in source_bindings
    }
    if len(binding_by_target) != len(source_bindings):
        _fail("construction private replay source target is duplicated")
    all_ids = set(upstream_by_id)
    role_by_id = {
        record_id: item.role
        for record_id, item in upstream_by_id.items()
    }
    if set(binding_by_target) != {
        record_id
        for record_id, role in role_by_id.items()
        if role in _PRIVATE_ROLE_SET
    }:
        _fail("construction private replay source coverage is not exact")
    private_record_by_role = {
        role: record_id
        for record_id, role in role_by_id.items()
        if role in _PRIVATE_ROLE_SET
    }
    expected_source_dependencies = {
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": (),
        "CONSTRUCTION_LINEAGE": (
            private_record_by_role[
                "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION"
            ],
        ),
        "CONSTRUCTION_LIFECYCLE": (
            private_record_by_role["CONSTRUCTION_LINEAGE"],
        ),
        "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
            private_record_by_role["CONSTRUCTION_LIFECYCLE"],
        ),
    }
    if any(
        binding.source_dependency_record_ids
        != tuple(sorted(expected_source_dependencies[binding.target_role]))
        for binding in source_bindings
    ):
        _fail("construction private replay source dependency is transplanted")

    portable_by_id: dict[str, tuple[str, ...]] = {}
    local_by_id: dict[str, tuple[str, ...]] = {}
    effective_by_id: dict[str, tuple[str, ...]] = {}
    resolver_by_id: dict[
        str, V075ConstructionPrivateReplayResolverKindV2
    ] = {}
    local_resolved_by_id: dict[str, bool] = {}
    source_id_by_id: dict[str, str | None] = {}
    for record_id, upstream in upstream_by_id.items():
        portable_dependencies = tuple(
            upstream.portable_declared_dependency_record_ids
        )
        inherited_local = tuple(
            upstream.authority_local_semantic_dependency_record_ids
        )
        if (
            tuple(sorted(set(portable_dependencies)))
            != portable_dependencies
            or tuple(sorted(set(inherited_local))) != inherited_local
        ):
            _fail("construction private replay dependency lanes changed")
        binding = binding_by_target.get(record_id)
        added = (
            ()
            if binding is None
            else binding.source_dependency_record_ids
        )
        local_dependencies = tuple(
            sorted(set(inherited_local) | set(added))
        )
        effective_dependencies = tuple(
            sorted(
                set(portable_dependencies) | set(local_dependencies)
            )
        )
        if (
            record_id in effective_dependencies
            or any(value not in all_ids for value in effective_dependencies)
        ):
            _fail("construction private replay dependency edge is foreign")
        role = role_by_id[record_id]
        if binding is not None:
            resolver = binding.resolver_kind
            local_resolved = True
            source_id = binding.binding_id
        elif role == "CONSTRUCTION_PLANNING_INPUT":
            resolver = (
                V075ConstructionPrivateReplayResolverKindV2
                .NO_REGISTERED_SEMANTIC_AUTHORITY
            )
            local_resolved = False
            source_id = None
        else:
            resolver = (
                V075ConstructionPrivateReplayResolverKindV2
                .UPSTREAM_M2_PLANNING
            )
            local_resolved = bool(
                upstream.local_semantic_authority_resolved
            )
            source_id = upstream.source_binding_id
        portable_by_id[record_id] = portable_dependencies
        local_by_id[record_id] = local_dependencies
        effective_by_id[record_id] = effective_dependencies
        resolver_by_id[record_id] = resolver
        local_resolved_by_id[record_id] = local_resolved
        source_id_by_id[record_id] = source_id

    indegree = {
        record_id: len(dependencies)
        for record_id, dependencies in effective_by_id.items()
    }
    successors = {record_id: [] for record_id in all_ids}
    for record_id, dependencies in effective_by_id.items():
        for dependency in dependencies:
            successors[dependency].append(record_id)
    ready = [
        (upstream_by_id[record_id].record_index, record_id)
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
                    (upstream_by_id[successor].record_index, successor),
                )
    if len(order) != len(all_ids):
        _fail("construction private replay effective DAG contains a cycle")

    resolved_by_id: dict[str, bool] = {}
    scope_by_id: dict[
        str, V075ConstructionPrivateReplayAuthorityScopeV2
    ] = {}
    frontier_by_id: dict[str, tuple[str, ...]] = {}
    depth_by_id: dict[str, int] = {}
    node_by_id: dict[
        str, V075ConstructionPrivateReplayDependencyNodeV2
    ] = {}
    for record_id in order:
        dependencies = effective_by_id[record_id]
        resolved = local_resolved_by_id[record_id] and all(
            resolved_by_id[value] for value in dependencies
        )
        role = role_by_id[record_id]
        if (
            role == "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION"
            and any(
                scope_by_id[value]
                is not V075ConstructionPrivateReplayAuthorityScopeV2
                .FULL_PUBLIC
                for value in dependencies
            )
        ):
            _fail("private closure verification depends on nonpublic scope")
        if not resolved:
            scope = (
                V075ConstructionPrivateReplayAuthorityScopeV2.UNRESOLVED
            )
        elif role == "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION":
            scope = (
                V075ConstructionPrivateReplayAuthorityScopeV2
                .FULL_CONSTRUCTION_PRIVATE_REPLAY
            )
        elif role in {
            "CONSTRUCTION_LINEAGE",
            "CONSTRUCTION_LIFECYCLE",
            "CONSTRUCTION_LIFECYCLE_VERIFICATION",
        }:
            scope = (
                V075ConstructionPrivateReplayAuthorityScopeV2
                .FULL_CONSTRUCTION_TRANSITIVE
            )
        elif any(
            scope_by_id[value]
            is not V075ConstructionPrivateReplayAuthorityScopeV2.FULL_PUBLIC
            for value in dependencies
        ):
            scope = (
                V075ConstructionPrivateReplayAuthorityScopeV2
                .FULL_CONSTRUCTION_TRANSITIVE
            )
        else:
            scope = (
                V075ConstructionPrivateReplayAuthorityScopeV2.FULL_PUBLIC
            )
        if resolved:
            frontier: tuple[str, ...] = ()
        elif not local_resolved_by_id[record_id]:
            frontier = (record_id,)
        else:
            unresolved: set[str] = set()
            for dependency in dependencies:
                unresolved.update(frontier_by_id[dependency])
            frontier = tuple(sorted(unresolved))
            if not frontier:
                _fail("unresolved private replay node lacks exact frontier")
        depth = 1 + max(
            (depth_by_id[value] for value in dependencies),
            default=0,
        )
        if depth > MAX_DEPENDENCY_NODES:
            _fail("construction private replay dependency depth exceeded")
        node = V075ConstructionPrivateReplayDependencyNodeV2(
            record_id,
            upstream_by_id[record_id].record_index,
            role_by_id[record_id],
            portable_by_id[record_id],
            local_by_id[record_id],
            effective_by_id[record_id],
            source_id_by_id[record_id],
            resolver_by_id[record_id],
            local_resolved_by_id[record_id],
            resolved,
            scope,
            frontier,
            tuple(sorted({role_by_id[value] for value in frontier})),
            depth,
        )
        node_by_id[record_id] = node
        resolved_by_id[record_id] = resolved
        scope_by_id[record_id] = scope
        frontier_by_id[record_id] = frontier
        depth_by_id[record_id] = depth
    return tuple(
        node_by_id[item.record_id]
        for item in sorted(
            upstream_nodes,
            key=lambda value: value.record_index,
        )
    )


_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPrivateReplayDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    hardened_planning_result: (
        m2_planning.V075PortablePlanningReplayV2
    ) = field(repr=False)
    source_bindings: tuple[
        V075ConstructionPrivateReplaySourceBindingV2,
        ...,
    ]
    nodes: tuple[V075ConstructionPrivateReplayDependencyNodeV2, ...]
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("construction private replay DAG is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_dag_id",
            _hash("dependency_dag", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.bundle_id, "construction private replay DAG bundle")
        _cid(self.typed_graph_id, "construction private replay DAG graph")
        if (
            type(self.hardened_planning_result)
            is not m2_planning.V075PortablePlanningReplayV2
            or type(self.source_bindings) is not tuple
            or type(self.nodes) is not tuple
            or not self.nodes
            or any(
                type(item)
                is not V075ConstructionPrivateReplayDependencyNodeV2
                for item in self.nodes
            )
        ):
            _fail("construction private replay DAG is malformed")
        expected = _iterative_dependency_nodes(
            upstream_nodes=self.hardened_planning_result.dependency_dag.nodes,
            source_bindings=self.source_bindings,
        )
        if tuple(item.to_document() for item in self.nodes) != tuple(
            item.to_document() for item in expected
        ):
            _fail("construction private replay DAG is stale")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_private_replay_dependency_dag.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "typed_graph_id": self.typed_graph_id,
            "hardened_planning_result_id": (
                self.hardened_planning_result.result_id
            ),
            "source_binding_ids": [
                item.binding_id for item in self.source_bindings
            ],
            "nodes": [item.to_document() for item in self.nodes],
            "portable_declared_dependency_lane_preserved": True,
            "authority_local_dependency_lane_preserved": True,
            "effective_dependency_lane_recomputed": True,
            "iterative_kahn_walk_used": True,
            "maximum_dependency_nodes": MAX_DEPENDENCY_NODES,
        }

    @property
    def dag_id(self) -> str:
        self._validate()
        if self._dag_id != _hash("dependency_dag", self._payload()):
            _fail("construction private replay DAG identity is stale")
        return self._dag_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "dependency_dag_id": self.dag_id}


_ROLE_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionPrivateReplayRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    dependency_dag_id: str
    role: str
    record_ids: tuple[str, ...]
    status: V075ConstructionPrivateReplayRoleStatusV2
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("construction private replay closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.bundle_id, "private replay role closure bundle")
        _cid(self.dependency_dag_id, "private replay role closure DAG")
        if (
            self.role not in _ROLE_SET
            or type(self.record_ids) is not tuple
            or len(self.record_ids) != 1
            or tuple(sorted(set(self.record_ids))) != self.record_ids
            or type(self.status)
            is not V075ConstructionPrivateReplayRoleStatusV2
            or tuple(sorted(set(self.unresolved_frontier_record_ids)))
            != self.unresolved_frontier_record_ids
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
            or (
                self.status
                is not V075ConstructionPrivateReplayRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
                and (
                    self.unresolved_frontier_record_ids
                    or self.unresolved_frontier_roles
                )
            )
        ):
            _fail("construction private replay role closure is malformed")
        _cid(self.record_ids[0], "private replay role closure record")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_private_replay_role_closure.v2"
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
            _fail("construction private replay closure identity is stale")
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}


def _build_role_closures(
    *,
    bundle_id: str,
    dependency_dag_id: str,
    nodes: tuple[V075ConstructionPrivateReplayDependencyNodeV2, ...],
) -> tuple[V075ConstructionPrivateReplayRoleClosureV2, ...]:
    result = []
    for role in ROLE_ORDER:
        members = tuple(item for item in nodes if item.role == role)
        if len(members) != 1:
            _fail(f"construction private replay role {role} is not singleton")
        member = members[0]
        if role == "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION":
            status = (
                V075ConstructionPrivateReplayRoleStatusV2
                .FULL_CONSTRUCTION_PRIVATE_REPLAY
            )
            expected_scope = (
                V075ConstructionPrivateReplayAuthorityScopeV2
                .FULL_CONSTRUCTION_PRIVATE_REPLAY
            )
        elif role in {
            "CONSTRUCTION_LINEAGE",
            "CONSTRUCTION_LIFECYCLE",
            "CONSTRUCTION_LIFECYCLE_VERIFICATION",
        }:
            status = (
                V075ConstructionPrivateReplayRoleStatusV2
                .FULL_CONSTRUCTION_TRANSITIVE
            )
            expected_scope = (
                V075ConstructionPrivateReplayAuthorityScopeV2
                .FULL_CONSTRUCTION_TRANSITIVE
            )
        else:
            status = (
                V075ConstructionPrivateReplayRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
            expected_scope = (
                V075ConstructionPrivateReplayAuthorityScopeV2.UNRESOLVED
            )
        if member.authority_scope is not expected_scope:
            _fail(
                f"construction private replay role {role} has wrong scope"
            )
        if (
            role == "CONSTRUCTION_PLANNING_INPUT"
            and (
                member.semantically_resolved
                or member.unresolved_frontier_roles
                != ("CONSTRUCTION_PLANNING_INPUT",)
            )
        ):
            _fail("construction planning input was falsely authorized")
        if (
            role != "CONSTRUCTION_PLANNING_INPUT"
            and not member.semantically_resolved
        ):
            _fail(f"construction private replay did not close role {role}")
        result.append(
            V075ConstructionPrivateReplayRoleClosureV2(
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
class V075PortableConstructionPrivateReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075ConstructionPrivateReplayTypedGraphV2 = field(
        repr=False
    )
    dependency_dag: V075ConstructionPrivateReplayDependencyDAGV2 = field(
        repr=False
    )
    role_closures: tuple[
        V075ConstructionPrivateReplayRoleClosureV2,
        ...,
    ]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("construction private replay result is caller-minted")
        self._validate_structure()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate_structure(self) -> None:
        for value, label in (
            (self.bundle_id, "private replay result bundle"),
            (self.occurrence_id, "private replay result occurrence"),
            (
                self.public_context_closure_id,
                "private replay result public context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph)
            is not V075ConstructionPrivateReplayTypedGraphV2
            or type(self.dependency_dag)
            is not V075ConstructionPrivateReplayDependencyDAGV2
            or type(self.role_closures) is not tuple
            or tuple(item.role for item in self.role_closures) != ROLE_ORDER
            or any(
                type(item)
                is not V075ConstructionPrivateReplayRoleClosureV2
                for item in self.role_closures
            )
            or self.typed_graph.bundle_id != self.bundle_id
            or self.typed_graph.occurrence_id != self.occurrence_id
            or self.typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or self.dependency_dag.bundle_id != self.bundle_id
            or self.dependency_dag.typed_graph_id
            != self.typed_graph.graph_id
            or self.dependency_dag.hardened_planning_result
            is not self.typed_graph.hardened_planning_result
            or self.dependency_dag.source_bindings
            != self.typed_graph.source_bindings
        ):
            _fail("construction private replay result is malformed")
        expected = _build_role_closures(
            bundle_id=self.bundle_id,
            dependency_dag_id=self.dependency_dag.dag_id,
            nodes=self.dependency_dag.nodes,
        )
        if tuple(item.to_document() for item in self.role_closures) != tuple(
            item.to_document() for item in expected
        ):
            _fail("construction private replay role closures are stale")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_construction_private_replay.v2"
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
            "raw_private_replay_performed": True,
            "construction_ephemeral_private_input_required": True,
            "production_private_input_channel_allowed": False,
            "aggregate_currentness_requires_explicit_raw_replay": True,
            "no_argument_currentness_claim_available": False,
            "construction_planning_input_semantic_authority_claimed": False,
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
        self._validate_structure()
        if self._result_id != _hash("aggregate", self._payload()):
            _fail("construction private replay result identity is stale")
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
        """Rerun all raw/private producers; no stored-secret shortcut exists."""

        replayed = replay_v075_portable_construction_private_replay_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
            private_generation_seed=private_generation_seed,
            private_salt=private_salt,
        )
        if replayed.to_document() != self.to_document():
            _fail("construction private replay currentness check changed")

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "construction private replay result is in-memory-only"
        )


def replay_v075_portable_construction_private_replay_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075PortableConstructionPrivateReplayV2:
    """Replay the exact private construction producer chain from raw inputs."""

    # This must remain the first authority call.  In particular, the bundle,
    # context, generation seed, and salt are not inspected locally first.
    try:
        upstream = m2_planning.replay_v075_portable_planning_authority_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
        )
    except Exception as error:
        raise V075PortableConstructionPrivateReplayV2InvariantViolation(
            "construction private replay hardened 1.77 replay failed"
        ) from error

    try:
        upstream._assert_current()  # noqa: SLF001
        if (
            type(private_generation_seed) is not bytes
            or not 0
            < len(private_generation_seed)
            <= MAX_PRIVATE_GENERATION_SEED_BYTES
            or type(private_salt) is not bytes
            or not 0 < len(private_salt) <= MAX_PRIVATE_SALT_BYTES
        ):
            _fail(_PRIVATE_MISMATCH)
        bundle = (
            portable
            .verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
        context_closure, resolution = _public_context_resolution(
            repository_root=repository_root,
            public_context_closure_bytes=public_context_closure_bytes,
        )
        generation_profile = (
            generation
            .freeze_v075_private_environment_generation_profile_v1()
        )
        generated_environment = (
            generation.generate_v075_private_environment_v1(
                profile=generation_profile,
                secret_generation_seed=private_generation_seed,
            )
        )
        regenerated_commitment = (
            generation.seal_v075_generated_private_environment_commitment_v1(
                generated_environment=generated_environment,
                secret_salt=private_salt,
            )
        )
        root_graph, m1a_graph, m0_graph = _hardened_graphs(upstream)
        binding = m1a_graph.b1_result.observer_open_binding
        if (
            bundle.bundle_id != upstream.bundle_id
            or bundle.occurrence_id != upstream.occurrence_id
            or context_closure.closure_id
            != upstream.public_context_closure_id
            or regenerated_commitment
            != resolution.authorization.opaque_environment_commitment
            or regenerated_commitment
            != resolution.namespace.environment_commitment
            or regenerated_commitment.commitment_id
            != context_closure.opaque_environment_commitment_id
            or regenerated_commitment.commitment_id
            != resolution.anchor.opaque_environment_commitment_id
            or generated_environment.family != resolution.namespace.family
            or binding.namespace != resolution.namespace
            or binding.authorization_id
            != resolution.authorization.authorization_id
            or binding.private_reveal_attestation_id
            != resolution.reveal_attestation.attestation_id
            or binding.remote_main_anchor_id != resolution.anchor.anchor_id
            or m1a_graph.closure.authority_binding != binding
            or root_graph.occurrence != m0_graph.occurrence
        ):
            _fail(_PRIVATE_MISMATCH)

        exact_lineage = (
            lineage.freeze_v075_construction_batch_occurrence_lineage_v2(
                occurrence_identity=root_graph.occurrence,
                closure=m1a_graph.closure,
                authority=resolution.authorization,
                namespace=resolution.namespace,
                known_stream_identities=m1a_graph.used_streams,
                private_salt=private_salt,
                private_environment=(
                    generated_environment.secret_laws_for_commitment()
                ),
            )
        )
        frozen_lifecycle = (
            lifecycle.freeze_v075_construction_batch_occurrence_lifecycle_v2(
                lineage=exact_lineage,
                lineage_bytes=exact_lineage.canonical_bytes,
                batch_closure_bytes=m1a_graph.closure.canonical_bytes,
            )
        )
        (
            exact_lifecycle,
            exact_lifecycle_verification,
        ) = lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2(
            lifecycle_bytes=frozen_lifecycle.canonical_bytes,
            lineage_bytes=exact_lineage.canonical_bytes,
            batch_closure_bytes=m1a_graph.closure.canonical_bytes,
            known_stream_identities=m1a_graph.used_streams,
        )
        if (
            exact_lifecycle.canonical_bytes
            != frozen_lifecycle.canonical_bytes
        ):
            _fail(_PRIVATE_MISMATCH)
        upstream._assert_current()  # noqa: SLF001

        records_by_role = {
            role: tuple(
                item for item in bundle.records if item.role == role
            )
            for role in ROLE_ORDER
        }
        if any(
            len(records_by_role[role]) != 1 for role in ROLE_ORDER
        ):
            _fail(_PRIVATE_MISMATCH)
        target_records = tuple(
            records_by_role[role][0] for role in ROLE_ORDER
        )
        target_bindings = tuple(
            _record_binding(item) for item in target_records
        )
        producer_raw = MappingProxyType(
            {
                "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": _raw(
                    exact_lineage.closure_verification
                ),
                "CONSTRUCTION_LINEAGE": exact_lineage.canonical_bytes,
                "CONSTRUCTION_LIFECYCLE": (
                    exact_lifecycle.canonical_bytes
                ),
                "CONSTRUCTION_LIFECYCLE_VERIFICATION": _raw(
                    exact_lifecycle_verification
                ),
            }
        )
        by_role = {item.role: item for item in target_bindings}
        semantic_ids = {
            "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": (
                exact_lineage.closure_verification.verification_id
            ),
            "CONSTRUCTION_LINEAGE": exact_lineage.lineage_id,
            "CONSTRUCTION_LIFECYCLE": exact_lifecycle.closure_id,
            "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
                exact_lifecycle_verification.verification_id
            ),
        }
        if any(
            by_role[role].canonical_artifact_bytes != producer_raw[role]
            or by_role[role].semantic_artifact_id != semantic_ids[role]
            for role in PRIVATE_REPLAY_ROLE_ORDER
        ):
            _fail(_PRIVATE_MISMATCH)
        source_bindings = _build_source_bindings(
            target_bindings=target_bindings,
            context_closure=context_closure,
            generation_profile=generation_profile,
            occurrence_id=upstream.occurrence_id,
            batch_closure_id=m1a_graph.closure.closure_id,
            producer_raw_by_role=producer_raw,
        )
        typed_graph = V075ConstructionPrivateReplayTypedGraphV2(
            _TYPED_GRAPH_ISSUER,
            bundle.bundle_id,
            bundle.occurrence_id,
            context_closure.closure_id,
            upstream,
            resolution,
            generation_profile,
            exact_lineage.closure_verification,
            exact_lineage,
            exact_lifecycle,
            exact_lifecycle_verification,
            target_bindings,
            source_bindings,
        )
        nodes = _iterative_dependency_nodes(
            upstream_nodes=upstream.dependency_dag.nodes,
            source_bindings=source_bindings,
        )
        dag = V075ConstructionPrivateReplayDependencyDAGV2(
            _DAG_ISSUER,
            bundle.bundle_id,
            typed_graph.graph_id,
            upstream,
            source_bindings,
            nodes,
        )
        role_closures = _build_role_closures(
            bundle_id=bundle.bundle_id,
            dependency_dag_id=dag.dag_id,
            nodes=nodes,
        )
        result = V075PortableConstructionPrivateReplayV2(
            _RESULT_ISSUER,
            bundle.bundle_id,
            bundle.occurrence_id,
            context_closure.closure_id,
            typed_graph,
            dag,
            role_closures,
        )
        if len(canonical_json_bytes(result.to_document())) > MAX_OUTPUT_BYTES:
            _fail("construction private replay public summary exceeds its cap")
        return result
    except V075PortableConstructionPrivateReplayV2InvariantViolation:
        raise
    except Exception:
        # Do not retain a cause whose message or representation could expose a
        # private input.  Every private mismatch intentionally has one error.
        raise V075PortableConstructionPrivateReplayV2InvariantViolation(
            _PRIVATE_MISMATCH
        ) from None


def assert_v075_portable_construction_private_replay_production_gate_v2(
    result: V075PortableConstructionPrivateReplayV2,
) -> NoReturn:
    if type(result) is not V075PortableConstructionPrivateReplayV2:
        _fail("construction private replay gate rejects duck-typed results")
    _ = result.result_id
    raise V075PortableConstructionPrivateReplayProductionV2NotReady(
        "contract 1.78 is construction-only; planning input, source "
        "authority, code provenance, accounting, and production gates remain "
        "open"
    )


__all__ = [
    "B3_INPUT_ALLOWED",
    "CODE_PROVENANCE_COMPLETE",
    "CONSTRUCTION_EPHEMERAL_PRIVATE_INPUT_REQUIRED",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "J0_ACCESS_ALLOWED",
    "K7_INPUT_ALLOWED",
    "KERNEL_ACCESS_ALLOWED",
    "MAX_DEPENDENCY_NODES",
    "MAX_OUTPUT_BYTES",
    "MAX_PRIVATE_GENERATION_SEED_BYTES",
    "MAX_PRIVATE_SALT_BYTES",
    "OBSERVER_OPEN_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OPERATIONAL_REGISTRIES_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRIVATE_REPLAY_INPUTS_ACCEPTED",
    "PRIVATE_REPLAY_PERFORMED",
    "PRIVATE_REPLAY_ROLE_ORDER",
    "PRODUCTION_PRIVATE_INPUT_CHANNEL_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "V075ConstructionPrivateReplayDependencyDAGV2",
    "V075ConstructionPrivateReplayDependencyNodeV2",
    "V075ConstructionPrivateReplayAuthorityScopeV2",
    "V075ConstructionPrivateReplayRecordBindingV2",
    "V075ConstructionPrivateReplayResolverKindV2",
    "V075ConstructionPrivateReplayRoleClosureV2",
    "V075ConstructionPrivateReplayRoleStatusV2",
    "V075ConstructionPrivateReplaySourceBindingV2",
    "V075ConstructionPrivateReplayTypedGraphV2",
    "V075PortableConstructionPrivateReplayProductionV2NotReady",
    "V075PortableConstructionPrivateReplayV2",
    "V075PortableConstructionPrivateReplayV2InvariantViolation",
    "assert_v075_portable_construction_private_replay_production_gate_v2",
    "replay_v075_portable_construction_private_replay_v2",
]
