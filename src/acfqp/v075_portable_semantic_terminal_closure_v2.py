"""Construction-only terminal semantic overlay for portable V0-075 evidence.

Contract 1.82 does not replace or mutate the contract-1.63 semantic registry.
It first replays the exact five-input contract-1.81 construction authority,
then joins its fully resolved typed DAG to the independently replayed
67-role registry and shape/content-ID attestation set.

Every record present in the verified occurrence receives one immutable
``FULL_TYPED_REPLAY`` overlay.  Every declared role absent from that
occurrence receives an explicit ``NOT_PRESENT_IN_VERIFIED_OCCURRENCE`` role
closure.  This closes only the composite construction view: source archive,
code provenance, accounting, production, science, and certificate gates all
remain locked.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import heapq
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_public_context_closure_v2 as public_context
from acfqp import v075_portable_semantic_registry_v2 as semantic
from acfqp import (
    v075_portable_construction_multiround_result_authority_v2
    as construction,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.82.0"
PROFILE_KEY = "v075_portable_semantic_terminal_closure_v2"
UPSTREAM_PROFILE_KEY = (
    "v075_portable_construction_multiround_result_authority_v2"
)
SEMANTIC_REGISTRY_PROFILE_KEY = "v075_portable_semantic_registry_v2"

CONSTRUCTION_SEMANTIC_TERMINAL_OVERLAY_COMPLETE = True
CONSTRUCTION_PRESENT_RECORD_TYPED_REPLAY_COMPLETE = True
CONSTRUCTION_DECLARED_ROLE_CLOSURE_COMPLETE = True
CONSTRUCTION_PORTABLE_SEMANTIC_REGISTRY_COMPLETE = True
CONSTRUCTION_DEPENDENCY_AWARE_TYPED_OBJECT_REPLAY_COMPLETE = True
CONSTRUCTION_COMPLETE_OCCURRENCE_BUNDLE_SEMANTIC_REPLAY_COMPLETE = True

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
ACCOUNTING_GATE_PASSED = False
PORTABLE_SEMANTIC_REGISTRY_PRODUCTION_COMPLETE = False
SEMANTIC_REGISTRY_REPLAY_COMPLETE = False
DEPENDENCY_AWARE_TYPED_OBJECT_REPLAY_COMPLETE = False
COMPLETE_OCCURRENCE_BUNDLE_SEMANTIC_REPLAY_COMPLETE = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
B3_INPUT_ALLOWED = False
K7_INPUT_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
J0_ACCESS_ALLOWED = False
OBSERVER_OPEN_ALLOWED = False
WORKER_LAUNCH_ALLOWED = False
OPERATIONAL_REGISTRIES_ALLOWED = False
PRODUCTION_PRIVATE_INPUT_CHANNEL_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_SEMANTIC_TERMINAL_OVERLAY_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_SEMANTIC_TERMINAL_OVERLAY_COMPLETE_"
    "PRODUCTION_AND_SCIENCE_GATES_LOCKED"
)
MAX_DEPENDENCY_NODES = 4096
MAX_CLAIMED_BYTES = 128 * 1024 * 1024
MAX_OUTPUT_BYTES = 128 * 1024 * 1024
EXPECTED_DECLARED_ROLE_COUNT = 67

DOMAIN_TAGS = MappingProxyType(
    {
        "record_overlay": (
            "acfqp:v075-portable-semantic-terminal-record-overlay:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-semantic-terminal-role-closure:v2"
        ),
        "terminal": (
            "acfqp:v075-portable-semantic-terminal-closure:v2"
        ),
    }
)

_REPLAY_MISMATCH = (
    "portable semantic terminal closure did not match registered evidence"
)


class V075PortableSemanticTerminalClosureV2InvariantViolation(ValueError):
    """Raw replay, semantic join, DAG closure, or claimed bytes failed."""


class V075PortableSemanticTerminalClosureProductionV2NotReady(RuntimeError):
    """The construction-only terminal overlay cannot authorize production."""


class V075PortableSemanticTerminalRoleStatusV2(str, Enum):
    FULL_TYPED_REPLAY = "FULL_TYPED_REPLAY"
    NOT_PRESENT_IN_VERIFIED_OCCURRENCE = (
        "NOT_PRESENT_IN_VERIFIED_OCCURRENCE"
    )


def _fail(message: str) -> NoReturn:
    raise V075PortableSemanticTerminalClosureV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableSemanticTerminalClosureV2InvariantViolation(
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
        raise V075PortableSemanticTerminalClosureV2InvariantViolation(
            "semantic terminal public identity is malformed"
        ) from error


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_CLAIMED_BYTES
    ):
        _fail(f"{label} is empty, mistyped, or over its byte cap")

    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"{label} contains a duplicate JSON key")
            result[key] = value
        return result

    try:
        document = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=unique_pairs,
            parse_constant=lambda value: _fail(
                f"{label} contains forbidden numeric constant {value}"
            ),
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        if type(error) is V075PortableSemanticTerminalClosureV2InvariantViolation:
            raise
        raise V075PortableSemanticTerminalClosureV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


def _typed_null(reason: str) -> dict[str, str]:
    return {"kind": "NOT_APPLICABLE", "reason": reason}


def _source_manifest(
    replayed: construction.V075PortableConstructionMultiroundResultReplayV2,
) -> public_context.V075PortablePublicContextSourceManifestV2:
    if (
        type(replayed)
        is not construction
        .V075PortableConstructionMultiroundResultReplayV2
    ):
        _fail("semantic terminal closure requires exact raw contract 1.81")
    _ = replayed.result_id
    try:
        private_graph = (
            replayed.typed_graph.closed_replay.typed_graph
            .planning_input_replay.typed_graph.private_replay_result
            .typed_graph
        )
        resolution = private_graph.public_context_resolution
        manifest = resolution.source_manifest
    except (AttributeError, TypeError) as error:
        raise V075PortableSemanticTerminalClosureV2InvariantViolation(
            "raw contract 1.81 omitted its public-context source manifest"
        ) from error
    if (
        type(resolution)
        is not public_context.V075PortablePublicContextRawResolutionV2
        or type(manifest)
        is not public_context.V075PortablePublicContextSourceManifestV2
        or resolution.repository_binding.source_manifest_id
        != manifest.manifest_id
    ):
        _fail("public-context source manifest identity is stale")
    _cid(manifest.manifest_id, "public-context source manifest")
    return manifest


def _verify_fresh_inputs(
    *,
    replayed: construction.V075PortableConstructionMultiroundResultReplayV2,
    portable_bundle_bytes: bytes,
) -> tuple[
    portable.V075PortableOccurrenceEvidenceBundleV2,
    semantic.V075PortableSemanticRegistryV2,
    semantic.V075PortableSemanticAttestationSetV2,
    public_context.V075PortablePublicContextSourceManifestV2,
]:
    manifest = _source_manifest(replayed)
    bundle = portable.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
        portable_bundle_bytes
    )
    registry = semantic.freeze_v075_portable_semantic_registry_v2()
    old_set = (
        semantic.attest_v075_portable_occurrence_evidence_bundle_bytes_v2(
            bundle_bytes=portable_bundle_bytes,
            source_manifest_id=manifest.manifest_id,
        )
    )
    empty_registry = replayed.typed_graph.empty_role_registry
    present_roles = frozenset(item.role for item in bundle.records)
    absent_roles = tuple(
        item.role
        for item in registry.declarations
        if item.role not in present_roles
    )
    if (
        type(bundle)
        is not portable.V075PortableOccurrenceEvidenceBundleV2
        or type(registry) is not semantic.V075PortableSemanticRegistryV2
        or type(old_set)
        is not semantic.V075PortableSemanticAttestationSetV2
        or bundle.bundle_id != replayed.bundle_id
        or bundle.occurrence_id != replayed.occurrence_id
        or len(registry.declarations) != EXPECTED_DECLARED_ROLE_COUNT
        or tuple(item.role for item in registry.declarations)
        != tuple(sorted(portable.ROLE_SCHEMA_REGISTRY))
        or {
            item.role: item.artifact_schema
            for item in registry.declarations
        }
        != dict(portable.ROLE_SCHEMA_REGISTRY)
        or old_set.registry_id != registry.registry_id
        or old_set.static_surface_registry_id
        != registry.static_surface_registry_id
        or old_set.portable_bundle_id != bundle.bundle_id
        or old_set.portable_bundle_sha256
        != hashlib.sha256(portable_bundle_bytes).hexdigest()
        or old_set.source_manifest_id != manifest.manifest_id
        or len(old_set.attestations) != len(bundle.records)
        or len({item.record_id for item in old_set.attestations})
        != len(old_set.attestations)
        or tuple(
            (item.record_id, item.record_index, item.role)
            for item in old_set.attestations
        )
        != tuple(
            (item.record_id, item.index, item.role)
            for item in bundle.records
        )
        or type(empty_registry)
        is not construction.V075ConstructionRootOnlyEmptyRoleRegistryV2
        or empty_registry.portable_bundle_id != bundle.bundle_id
        or empty_registry.roles != construction.ROOT_ONLY_EMPTY_ROLE_ORDER
        or empty_registry.role_counts
        != tuple(
            (role, 0) for role in construction.ROOT_ONLY_EMPTY_ROLE_ORDER
        )
        or absent_roles != construction.ROOT_ONLY_EMPTY_ROLE_ORDER
        or len(present_roles) != (
            EXPECTED_DECLARED_ROLE_COUNT
            - len(construction.ROOT_ONLY_EMPTY_ROLE_ORDER)
        )
    ):
        _fail("fresh bundle and old semantic attestation set diverged")
    return bundle, registry, old_set, manifest


def _validate_exact_resolved_dag(
    *,
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    nodes: tuple[
        construction.V075ConstructionMultiroundResultDependencyNodeV2,
        ...,
    ],
) -> None:
    if (
        type(records) is not tuple
        or not records
        or type(nodes) is not tuple
        or len(records) != len(nodes)
        or len(nodes) > MAX_DEPENDENCY_NODES
        or any(
            type(item)
            is not portable.V075PortableEvidenceArtifactRecordV2
            for item in records
        )
        or any(
            type(item)
            is not construction
            .V075ConstructionMultiroundResultDependencyNodeV2
            for item in nodes
        )
    ):
        _fail("semantic terminal closure requires one bounded exact DAG")
    record_by_id = {item.record_id: item for item in records}
    node_by_id: dict[
        str,
        construction.V075ConstructionMultiroundResultDependencyNodeV2,
    ] = {}
    scope_enum = construction.V075ConstructionMultiroundResultAuthorityScopeV2
    for expected_index, (record, node) in enumerate(
        zip(records, nodes, strict=True)
    ):
        portable_lane = tuple(
            node.portable_declared_dependency_record_ids
        )
        local_lane = tuple(
            node.authority_local_semantic_dependency_record_ids
        )
        effective_lane = tuple(node.effective_dependency_record_ids)
        if (
            record.index != expected_index
            or node.record_index != expected_index
            or node.record_id != record.record_id
            or node.role != record.role
            or record.record_id in node_by_id
            or tuple(sorted(set(portable_lane))) != portable_lane
            or tuple(sorted(set(local_lane))) != local_lane
            or tuple(sorted(set(effective_lane))) != effective_lane
            or set(effective_lane)
            != set(portable_lane) | set(local_lane)
            or record.record_id in effective_lane
            or node.local_semantic_authority_resolved is not True
            or node.semantically_resolved is not True
            or node.authority_scope is scope_enum.UNRESOLVED
            or node.unresolved_frontier_record_ids
            or node.unresolved_frontier_roles
        ):
            _fail("present record lacks one exact resolved typed DAG node")
        node_by_id[record.record_id] = node
    all_ids = set(record_by_id)
    if set(node_by_id) != all_ids:
        _fail("typed DAG record coverage is incomplete or substituted")
    indegree: dict[str, int] = {}
    successors = {record_id: [] for record_id in all_ids}
    for record_id, node in node_by_id.items():
        dependencies = tuple(node.effective_dependency_record_ids)
        if any(item not in all_ids for item in dependencies):
            _fail("typed DAG contains a foreign dependency")
        indegree[record_id] = len(dependencies)
        for dependency in dependencies:
            successors[dependency].append(record_id)
    ready = [
        (node_by_id[record_id].record_index, record_id)
        for record_id, degree in indegree.items()
        if degree == 0
    ]
    heapq.heapify(ready)
    visited = 0
    while ready:
        _index, record_id = heapq.heappop(ready)
        visited += 1
        for successor in successors[record_id]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(
                    ready,
                    (node_by_id[successor].record_index, successor),
                )
    if visited != len(nodes):
        _fail("semantic terminal effective dependency graph is cyclic")


_OVERLAY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableSemanticTerminalRecordOverlayV2:
    """Construction typed-replay overlay for exactly one present record."""

    _issuer: InitVar[object]
    portable_bundle_id: str
    semantic_registry_id: str
    static_surface_registry_id: str
    old_attestation_set_id: str
    source_manifest_id: str
    construction_replay_id: str
    construction_typed_graph_id: str
    construction_dependency_dag_id: str
    declaration_id: str
    old_attestation_id: str
    legacy_declaration_replay_status: (
        semantic.V075PortableSemanticReplayStatusV2
    )
    legacy_attestation_replay_status: (
        semantic.V075PortableSemanticReplayStatusV2
    )
    record_index: int
    record_id: str
    role: str
    artifact_schema: str
    semantic_artifact_id: str
    canonical_artifact_sha256: str
    canonical_artifact_byte_count: int
    dependency_node_sha256: str
    source_binding_id: str | None
    resolver_kind: (
        construction.V075ConstructionMultiroundResultResolverKindV2
    )
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    authority_scope: (
        construction.V075ConstructionMultiroundResultAuthorityScopeV2
    )
    dependency_depth: int
    status: V075PortableSemanticTerminalRoleStatusV2
    _overlay_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _OVERLAY_ISSUER:
            _fail("semantic terminal record overlay is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_overlay_id",
            _hash("record_overlay", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.portable_bundle_id, "overlay portable bundle"),
            (self.semantic_registry_id, "overlay semantic registry"),
            (
                self.static_surface_registry_id,
                "overlay static surface registry",
            ),
            (self.old_attestation_set_id, "overlay old attestation set"),
            (self.source_manifest_id, "overlay source manifest"),
            (self.construction_replay_id, "overlay construction replay"),
            (
                self.construction_typed_graph_id,
                "overlay construction typed graph",
            ),
            (
                self.construction_dependency_dag_id,
                "overlay construction DAG",
            ),
            (self.declaration_id, "overlay declaration"),
            (self.old_attestation_id, "overlay old attestation"),
            (self.record_id, "overlay record"),
            (self.semantic_artifact_id, "overlay semantic artifact"),
            (
                self.canonical_artifact_sha256,
                "overlay artifact bytes",
            ),
            (self.dependency_node_sha256, "overlay dependency node"),
        ):
            _cid(value, label)
        if self.source_binding_id is not None:
            _cid(self.source_binding_id, "overlay source binding")
        lanes = (
            self.portable_declared_dependency_record_ids,
            self.authority_local_semantic_dependency_record_ids,
            self.effective_dependency_record_ids,
        )
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or type(self.role) is not str
            or portable.ROLE_SCHEMA_REGISTRY.get(self.role)
            != self.artifact_schema
            or type(self.semantic_artifact_id) is not str
            or type(self.canonical_artifact_byte_count) is not int
            or self.canonical_artifact_byte_count <= 0
            or type(self.resolver_kind)
            is not construction
            .V075ConstructionMultiroundResultResolverKindV2
            or self.resolver_kind
            is construction.V075ConstructionMultiroundResultResolverKindV2
            .NO_REGISTERED_SEMANTIC_AUTHORITY
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in lanes
            )
            or set(self.effective_dependency_record_ids)
            != set(self.portable_declared_dependency_record_ids)
            | set(self.authority_local_semantic_dependency_record_ids)
            or self.record_id in self.effective_dependency_record_ids
            or type(self.authority_scope)
            is not construction
            .V075ConstructionMultiroundResultAuthorityScopeV2
            or self.authority_scope
            is construction.V075ConstructionMultiroundResultAuthorityScopeV2
            .UNRESOLVED
            or type(self.dependency_depth) is not int
            or not 0 < self.dependency_depth <= MAX_DEPENDENCY_NODES
            or type(self.legacy_declaration_replay_status)
            is not semantic.V075PortableSemanticReplayStatusV2
            or type(self.legacy_attestation_replay_status)
            is not semantic.V075PortableSemanticReplayStatusV2
            or self.legacy_declaration_replay_status
            is not self.legacy_attestation_replay_status
            or self.status
            is not V075PortableSemanticTerminalRoleStatusV2
            .FULL_TYPED_REPLAY
        ):
            _fail("semantic terminal record overlay is malformed")
        for value in self.effective_dependency_record_ids:
            _cid(value, "overlay dependency record")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_semantic_terminal_record_overlay.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.portable_bundle_id,
            "semantic_registry_id": self.semantic_registry_id,
            "static_surface_registry_id": self.static_surface_registry_id,
            "static_surface_used_as_artifact_semantic_evidence": False,
            "old_attestation_set_id": self.old_attestation_set_id,
            "source_manifest_id": self.source_manifest_id,
            "construction_replay_id": self.construction_replay_id,
            "construction_typed_graph_id": (
                self.construction_typed_graph_id
            ),
            "construction_dependency_dag_id": (
                self.construction_dependency_dag_id
            ),
            "declaration_id": self.declaration_id,
            "old_shape_content_attestation_id": (
                self.old_attestation_id
            ),
            "legacy_declaration_replay_status": (
                self.legacy_declaration_replay_status.value
            ),
            "legacy_attestation_replay_status": (
                self.legacy_attestation_replay_status.value
            ),
            "legacy_semantic_replay_status_relabelled": False,
            "record_index": self.record_index,
            "record_id": self.record_id,
            "role": self.role,
            "artifact_schema": self.artifact_schema,
            "semantic_artifact_id": self.semantic_artifact_id,
            "canonical_artifact_sha256": (
                self.canonical_artifact_sha256
            ),
            "canonical_artifact_byte_count": (
                self.canonical_artifact_byte_count
            ),
            "construction_dependency_node_sha256": (
                self.dependency_node_sha256
            ),
            "construction_source_binding_id": (
                self.source_binding_id
                if self.source_binding_id is not None
                else _typed_null(
                    "UPSTREAM_RESOLVED_NODE_HAS_NO_LOCAL_BINDING_ID"
                )
            ),
            "resolver_kind": self.resolver_kind.value,
            "portable_declared_dependency_record_ids": list(
                self.portable_declared_dependency_record_ids
            ),
            "authority_local_semantic_dependency_record_ids": list(
                self.authority_local_semantic_dependency_record_ids
            ),
            "effective_dependency_record_ids": list(
                self.effective_dependency_record_ids
            ),
            "effective_lane_is_exact_union": True,
            "authority_scope": self.authority_scope.value,
            "authority_scope_preserved_per_record": True,
            "dependency_depth": self.dependency_depth,
            "status": self.status.value,
            "typed_object_replay_complete": True,
            "unresolved_frontier_record_ids": [],
            "unresolved_frontier_roles": [],
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def overlay_id(self) -> str:
        self._validate()
        if self._overlay_id != _hash("record_overlay", self._payload()):
            _fail("semantic terminal record overlay identity is stale")
        return self._overlay_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "overlay_id": self.overlay_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("semantic terminal record overlay is in-memory-only")


_ROLE_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableSemanticTerminalRoleClosureV2:
    """Present-record coverage or exact absence for one declared role."""

    _issuer: InitVar[object]
    portable_bundle_id: str
    semantic_registry_id: str
    declaration_id: str
    declaration_ordinal: int
    role: str
    artifact_schema: str
    status: V075PortableSemanticTerminalRoleStatusV2
    record_ids: tuple[str, ...]
    overlay_ids: tuple[str, ...]
    legacy_attestation_ids: tuple[str, ...]
    dependency_node_sha256s: tuple[str, ...]
    record_authority_scopes: tuple[tuple[str, str], ...]
    absence_evidence_registry_id: str | None
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("semantic terminal role closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.portable_bundle_id, "role closure bundle"),
            (self.semantic_registry_id, "role closure registry"),
            (self.declaration_id, "role closure declaration"),
        ):
            _cid(value, label)
        if self.absence_evidence_registry_id is not None:
            _cid(
                self.absence_evidence_registry_id,
                "role closure absence registry",
            )
        if (
            type(self.declaration_ordinal) is not int
            or not 0 <= self.declaration_ordinal < EXPECTED_DECLARED_ROLE_COUNT
            or type(self.role) is not str
            or portable.ROLE_SCHEMA_REGISTRY.get(self.role)
            != self.artifact_schema
            or type(self.status)
            is not V075PortableSemanticTerminalRoleStatusV2
            or type(self.record_ids) is not tuple
            or type(self.overlay_ids) is not tuple
            or type(self.legacy_attestation_ids) is not tuple
            or type(self.dependency_node_sha256s) is not tuple
            or type(self.record_authority_scopes) is not tuple
            or len(self.record_ids) != len(self.overlay_ids)
            or len(self.record_ids) != len(self.legacy_attestation_ids)
            or len(self.record_ids) != len(self.dependency_node_sha256s)
            or len(self.record_ids) != len(self.record_authority_scopes)
            or len(set(self.record_ids)) != len(self.record_ids)
            or len(set(self.overlay_ids)) != len(self.overlay_ids)
            or len(set(self.legacy_attestation_ids))
            != len(self.legacy_attestation_ids)
            or tuple(item[0] for item in self.record_authority_scopes)
            != self.record_ids
            or any(
                type(item) is not tuple
                or len(item) != 2
                or item[1]
                not in {
                    scope.value
                    for scope in construction
                    .V075ConstructionMultiroundResultAuthorityScopeV2
                    if scope
                    is not construction
                    .V075ConstructionMultiroundResultAuthorityScopeV2
                    .UNRESOLVED
                }
                for item in self.record_authority_scopes
            )
            or (
                self.status
                is V075PortableSemanticTerminalRoleStatusV2
                .FULL_TYPED_REPLAY
                and not self.record_ids
            )
            or (
                self.status
                is V075PortableSemanticTerminalRoleStatusV2
                .FULL_TYPED_REPLAY
                and self.absence_evidence_registry_id is not None
            )
            or (
                self.status
                is V075PortableSemanticTerminalRoleStatusV2
                .NOT_PRESENT_IN_VERIFIED_OCCURRENCE
                and (
                    self.record_ids
                    or self.overlay_ids
                    or self.legacy_attestation_ids
                    or self.dependency_node_sha256s
                    or self.record_authority_scopes
                    or self.absence_evidence_registry_id is None
                )
            )
        ):
            _fail("semantic terminal role closure is malformed")
        for value in (
            *self.record_ids,
            *self.overlay_ids,
            *self.legacy_attestation_ids,
            *self.dependency_node_sha256s,
        ):
            _cid(value, "role closure record or overlay")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_semantic_terminal_role_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.portable_bundle_id,
            "semantic_registry_id": self.semantic_registry_id,
            "declaration_id": self.declaration_id,
            "declaration_ordinal": self.declaration_ordinal,
            "role": self.role,
            "artifact_schema": self.artifact_schema,
            "status": self.status.value,
            "record_ids": list(self.record_ids),
            "overlay_ids": list(self.overlay_ids),
            "legacy_shape_content_attestation_ids": list(
                self.legacy_attestation_ids
            ),
            "construction_dependency_node_sha256s": list(
                self.dependency_node_sha256s
            ),
            "record_authority_scopes": [
                {"record_id": record_id, "authority_scope": scope}
                for record_id, scope in self.record_authority_scopes
            ],
            "authority_scope_flattened": False,
            "present_record_count": len(self.record_ids),
            "absence_evidence_registry_id": (
                self.absence_evidence_registry_id
                if self.absence_evidence_registry_id is not None
                else _typed_null("ROLE_IS_PRESENT")
            ),
            "absence_derived_from_verified_bundle": (
                self.status
                is V075PortableSemanticTerminalRoleStatusV2
                .NOT_PRESENT_IN_VERIFIED_OCCURRENCE
            ),
            "absence_derived_from_fresh_181_empty_role_registry": (
                self.status
                is V075PortableSemanticTerminalRoleStatusV2
                .NOT_PRESENT_IN_VERIFIED_OCCURRENCE
            ),
            "caller_claimed_nulls_used_as_absence_evidence": False,
        }

    @property
    def closure_id(self) -> str:
        self._validate()
        if self._closure_id != _hash("role_closure", self._payload()):
            _fail("semantic terminal role closure identity is stale")
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("semantic terminal role closure is in-memory-only")


_TERMINAL_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableSemanticTerminalClosureV2:
    """Complete construction overlay over all present records and 67 roles."""

    _issuer: InitVar[object]
    portable_bundle_id: str
    portable_bundle_sha256: str
    occurrence_id: str
    public_context_closure_id: str
    source_manifest_id: str
    source_manifest_sha256: str
    source_manifest_byte_count: int
    semantic_registry_id: str
    static_surface_registry_id: str
    old_attestation_set_id: str
    construction_replay_id: str
    construction_typed_graph_id: str
    construction_dependency_dag_id: str
    empty_role_registry_id: str
    construction_replay: (
        construction.V075PortableConstructionMultiroundResultReplayV2
    ) = field(repr=False)
    semantic_registry: semantic.V075PortableSemanticRegistryV2 = field(
        repr=False
    )
    legacy_attestation_set: (
        semantic.V075PortableSemanticAttestationSetV2
    ) = field(repr=False)
    source_manifest: (
        public_context.V075PortablePublicContextSourceManifestV2
    ) = field(repr=False)
    record_overlays: tuple[
        V075PortableSemanticTerminalRecordOverlayV2, ...
    ]
    role_closures: tuple[
        V075PortableSemanticTerminalRoleClosureV2, ...
    ]
    _terminal_closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TERMINAL_ISSUER:
            _fail("semantic terminal closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_terminal_closure_id",
            _hash("terminal", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.portable_bundle_id, "terminal bundle"),
            (self.portable_bundle_sha256, "terminal bundle bytes"),
            (self.occurrence_id, "terminal occurrence"),
            (self.public_context_closure_id, "terminal public context"),
            (self.source_manifest_id, "terminal source manifest"),
            (self.source_manifest_sha256, "terminal source manifest bytes"),
            (self.semantic_registry_id, "terminal semantic registry"),
            (
                self.static_surface_registry_id,
                "terminal static surface registry",
            ),
            (self.old_attestation_set_id, "terminal old attestation set"),
            (self.construction_replay_id, "terminal construction replay"),
            (
                self.construction_typed_graph_id,
                "terminal construction typed graph",
            ),
            (
                self.construction_dependency_dag_id,
                "terminal construction DAG",
            ),
            (self.empty_role_registry_id, "terminal empty role registry"),
        ):
            _cid(value, label)
        expected_roles = tuple(sorted(portable.ROLE_SCHEMA_REGISTRY))
        if (
            type(self.source_manifest_byte_count) is not int
            or self.source_manifest_byte_count <= 0
            or type(self.construction_replay)
            is not construction
            .V075PortableConstructionMultiroundResultReplayV2
            or type(self.semantic_registry)
            is not semantic.V075PortableSemanticRegistryV2
            or type(self.legacy_attestation_set)
            is not semantic.V075PortableSemanticAttestationSetV2
            or type(self.source_manifest)
            is not public_context.V075PortablePublicContextSourceManifestV2
            or type(self.record_overlays) is not tuple
            or not self.record_overlays
            or len(self.record_overlays) > MAX_DEPENDENCY_NODES
            or any(
                type(item)
                is not V075PortableSemanticTerminalRecordOverlayV2
                for item in self.record_overlays
            )
            or tuple(item.record_index for item in self.record_overlays)
            != tuple(range(len(self.record_overlays)))
            or len({item.record_id for item in self.record_overlays})
            != len(self.record_overlays)
            or len({item.overlay_id for item in self.record_overlays})
            != len(self.record_overlays)
            or type(self.role_closures) is not tuple
            or len(self.role_closures) != EXPECTED_DECLARED_ROLE_COUNT
            or tuple(item.role for item in self.role_closures)
            != expected_roles
            or any(
                type(item)
                is not V075PortableSemanticTerminalRoleClosureV2
                for item in self.role_closures
            )
            or len({item.closure_id for item in self.role_closures})
            != len(self.role_closures)
        ):
            _fail("semantic terminal aggregate is malformed")
        _ = self.construction_replay.result_id
        manifest_bytes = self.source_manifest.canonical_bytes
        empty_registry = (
            self.construction_replay.typed_graph.empty_role_registry
        )
        if (
            self.construction_replay.bundle_id != self.portable_bundle_id
            or self.construction_replay.occurrence_id != self.occurrence_id
            or self.construction_replay.public_context_closure_id
            != self.public_context_closure_id
            or self.construction_replay.result_id
            != self.construction_replay_id
            or self.construction_replay.typed_graph.graph_id
            != self.construction_typed_graph_id
            or self.construction_replay.dependency_dag.dag_id
            != self.construction_dependency_dag_id
            or self.semantic_registry.registry_id
            != self.semantic_registry_id
            or self.semantic_registry.static_surface_registry_id
            != self.static_surface_registry_id
            or self.legacy_attestation_set.registry_id
            != self.semantic_registry_id
            or self.legacy_attestation_set.static_surface_registry_id
            != self.static_surface_registry_id
            or self.legacy_attestation_set.attestation_set_id
            != self.old_attestation_set_id
            or self.legacy_attestation_set.portable_bundle_id
            != self.portable_bundle_id
            or self.legacy_attestation_set.portable_bundle_sha256
            != self.portable_bundle_sha256
            or self.legacy_attestation_set.source_manifest_id
            != self.source_manifest_id
            or self.source_manifest.manifest_id != self.source_manifest_id
            or hashlib.sha256(manifest_bytes).hexdigest()
            != self.source_manifest_sha256
            or len(manifest_bytes) != self.source_manifest_byte_count
            or type(empty_registry)
            is not construction.V075ConstructionRootOnlyEmptyRoleRegistryV2
            or empty_registry.registry_id != self.empty_role_registry_id
            or empty_registry.portable_bundle_id != self.portable_bundle_id
            or empty_registry.roles
            != construction.ROOT_ONLY_EMPTY_ROLE_ORDER
            or empty_registry.role_counts
            != tuple(
                (role, 0)
                for role in construction.ROOT_ONLY_EMPTY_ROLE_ORDER
            )
            or tuple(
                (item.record_id, item.record_index, item.role)
                for item in self.legacy_attestation_set.attestations
            )
            != tuple(
                (item.record_id, item.record_index, item.role)
                for item in self.record_overlays
            )
        ):
            _fail("semantic terminal fresh authority graph is stale")
        old_by_record = {
            item.record_id: item
            for item in self.legacy_attestation_set.attestations
        }
        declaration_by_role = self.semantic_registry.by_role
        for overlay in self.record_overlays:
            old = old_by_record[overlay.record_id]
            declaration = declaration_by_role[overlay.role]
            if (
                overlay.portable_bundle_id != self.portable_bundle_id
                or overlay.semantic_registry_id
                != self.semantic_registry_id
                or overlay.static_surface_registry_id
                != self.static_surface_registry_id
                or overlay.old_attestation_set_id
                != self.old_attestation_set_id
                or overlay.source_manifest_id != self.source_manifest_id
                or overlay.construction_replay_id
                != self.construction_replay_id
                or overlay.construction_typed_graph_id
                != self.construction_typed_graph_id
                or overlay.construction_dependency_dag_id
                != self.construction_dependency_dag_id
                or overlay.declaration_id != declaration.declaration_id
                or overlay.old_attestation_id != old.attestation_id
                or overlay.legacy_declaration_replay_status
                is not declaration.semantic_replay_status
                or overlay.legacy_attestation_replay_status
                is not old.semantic_replay_status
            ):
                _fail("semantic terminal overlay identity was transplanted")
        by_role: dict[
            str, list[V075PortableSemanticTerminalRecordOverlayV2]
        ] = {role: [] for role in expected_roles}
        for overlay in self.record_overlays:
            if overlay.role not in by_role:
                _fail("semantic terminal overlay role is undeclared")
            by_role[overlay.role].append(overlay)
        closure_by_role = {item.role: item for item in self.role_closures}
        for role in expected_roles:
            members = tuple(by_role[role])
            closure = closure_by_role[role]
            declaration = declaration_by_role[role]
            expected_status = (
                V075PortableSemanticTerminalRoleStatusV2.FULL_TYPED_REPLAY
                if members
                else (
                    V075PortableSemanticTerminalRoleStatusV2
                    .NOT_PRESENT_IN_VERIFIED_OCCURRENCE
                )
            )
            if (
                closure.portable_bundle_id != self.portable_bundle_id
                or closure.semantic_registry_id
                != self.semantic_registry_id
                or closure.declaration_id != declaration.declaration_id
                or closure.declaration_ordinal != declaration.ordinal
                or closure.artifact_schema != declaration.artifact_schema
                or closure.status is not expected_status
                or closure.record_ids
                != tuple(item.record_id for item in members)
                or closure.overlay_ids
                != tuple(item.overlay_id for item in members)
                or closure.legacy_attestation_ids
                != tuple(item.old_attestation_id for item in members)
                or closure.dependency_node_sha256s
                != tuple(item.dependency_node_sha256 for item in members)
                or closure.record_authority_scopes
                != tuple(
                    (item.record_id, item.authority_scope.value)
                    for item in members
                )
                or closure.absence_evidence_registry_id
                != (
                    None
                    if members
                    else self.empty_role_registry_id
                )
                or (
                    members
                    and (
                        closure.declaration_id
                        != members[0].declaration_id
                        or closure.artifact_schema
                        != members[0].artifact_schema
                        or any(
                            item.declaration_id
                            != closure.declaration_id
                            or item.artifact_schema
                            != closure.artifact_schema
                            for item in members
                        )
                    )
                )
            ):
                _fail("semantic terminal role coverage is stale or flattened")
        covered = tuple(
            record_id
            for closure in self.role_closures
            for record_id in closure.record_ids
        )
        if sorted(covered) != sorted(
            item.record_id for item in self.record_overlays
        ):
            _fail("semantic terminal role closures omit or duplicate records")
        absent_roles = tuple(
            item.role
            for item in self.role_closures
            if item.status
            is (
                V075PortableSemanticTerminalRoleStatusV2
                .NOT_PRESENT_IN_VERIFIED_OCCURRENCE
            )
        )
        if (
            tuple(item.declaration_ordinal for item in self.role_closures)
            != tuple(range(EXPECTED_DECLARED_ROLE_COUNT))
            or absent_roles != construction.ROOT_ONLY_EMPTY_ROLE_ORDER
            or len(self.role_closures) - len(absent_roles) != 49
            or sum(count for _scope, count in self._scope_histogram())
            != len(self.record_overlays)
        ):
            _fail("semantic terminal role partition or scope histogram changed")

    def _scope_histogram(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            (
                scope.value,
                sum(
                    item.authority_scope is scope
                    for item in self.record_overlays
                ),
            )
            for scope in (
                construction
                .V075ConstructionMultiroundResultAuthorityScopeV2
            )
            if scope
            is not (
                construction
                .V075ConstructionMultiroundResultAuthorityScopeV2
                .UNRESOLVED
            )
        )

    def _payload(self) -> dict[str, Any]:
        present_roles = tuple(
            item.role
            for item in self.role_closures
            if item.status
            is V075PortableSemanticTerminalRoleStatusV2.FULL_TYPED_REPLAY
        )
        absent_roles = tuple(
            item.role
            for item in self.role_closures
            if item.status
            is (
                V075PortableSemanticTerminalRoleStatusV2
                .NOT_PRESENT_IN_VERIFIED_OCCURRENCE
            )
        )
        return {
            "schema": "acfqp.v075_portable_semantic_terminal_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "upstream_profile_key": UPSTREAM_PROFILE_KEY,
            "semantic_registry_profile_key": (
                SEMANTIC_REGISTRY_PROFILE_KEY
            ),
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.portable_bundle_id,
            "portable_bundle_sha256": self.portable_bundle_sha256,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": (
                self.public_context_closure_id
            ),
            "source_manifest_id": self.source_manifest_id,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_manifest_byte_count": self.source_manifest_byte_count,
            "semantic_registry_id": self.semantic_registry_id,
            "static_surface_registry_id": self.static_surface_registry_id,
            "static_surface_used_as_artifact_semantic_evidence": False,
            "old_shape_content_attestation_set_id": (
                self.old_attestation_set_id
            ),
            "construction_replay_id": self.construction_replay_id,
            "construction_typed_graph_id": (
                self.construction_typed_graph_id
            ),
            "construction_dependency_dag_id": (
                self.construction_dependency_dag_id
            ),
            "root_only_empty_role_registry_id": (
                self.empty_role_registry_id
            ),
            "record_overlay_ids": [
                item.overlay_id for item in self.record_overlays
            ],
            "role_closure_ids": [
                item.closure_id for item in self.role_closures
            ],
            "record_count": len(self.record_overlays),
            "declared_role_count": len(self.role_closures),
            "legacy_complete_record_count": sum(
                item.legacy_attestation_replay_status
                is semantic.V075PortableSemanticReplayStatusV2.COMPLETE
                for item in self.record_overlays
            ),
            "legacy_incomplete_record_count": sum(
                item.legacy_attestation_replay_status
                is semantic.V075PortableSemanticReplayStatusV2.INCOMPLETE
                for item in self.record_overlays
            ),
            "legacy_registry_complete_role_count": sum(
                item.semantic_replay_status
                is semantic.V075PortableSemanticReplayStatusV2.COMPLETE
                for item in self.semantic_registry.declarations
            ),
            "legacy_registry_incomplete_role_count": sum(
                item.semantic_replay_status
                is semantic.V075PortableSemanticReplayStatusV2.INCOMPLETE
                for item in self.semantic_registry.declarations
            ),
            "legacy_registry_statuses_preserved": True,
            "present_roles": list(present_roles),
            "absent_roles": list(absent_roles),
            "authority_scope_histogram": [
                {"authority_scope": scope, "record_count": count}
                for scope, count in self._scope_histogram()
            ],
            "authority_scope_histogram_native_zeros_included": True,
            "authority_scope_histogram_record_count": sum(
                count for _scope, count in self._scope_histogram()
            ),
            "present_record_overlay_status": (
                V075PortableSemanticTerminalRoleStatusV2
                .FULL_TYPED_REPLAY.value
            ),
            "absent_role_status": (
                V075PortableSemanticTerminalRoleStatusV2
                .NOT_PRESENT_IN_VERIFIED_OCCURRENCE.value
            ),
            "all_present_records_covered_once": True,
            "all_declared_roles_closed_once": True,
            "effective_dependency_lane_exact_union": True,
            "iterative_kahn_walk_used": True,
            "maximum_dependency_nodes": MAX_DEPENDENCY_NODES,
            "all_present_nodes_semantically_resolved": True,
            "all_present_frontiers_empty": True,
            "authority_scopes_preserved_per_record": True,
            "authority_scope_flattened": False,
            "raw_contract_181_replayed_first": True,
            "old_semantic_registry_mutated": False,
            "construction_semantic_terminal_overlay_complete": True,
            "construction_present_record_typed_replay_complete": True,
            "construction_declared_role_closure_complete": True,
            "construction_portable_semantic_registry_complete": True,
            "construction_dependency_aware_typed_object_replay_complete": (
                True
            ),
            (
                "construction_complete_occurrence_bundle_"
                "semantic_replay_complete"
            ): True,
            "semantic_registry_replay_complete": False,
            "dependency_aware_typed_object_replay_complete": False,
            "complete_occurrence_bundle_semantic_replay_complete": False,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
            "fresh_heldout_accessed": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "accounting_gate_passed": False,
            "portable_semantic_registry_production_complete": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def terminal_closure_id(self) -> str:
        self._validate()
        if self._terminal_closure_id != _hash(
            "terminal",
            self._payload(),
        ):
            _fail("semantic terminal aggregate identity is stale")
        return self._terminal_closure_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "record_overlays": [
                item.to_document() for item in self.record_overlays
            ],
            "role_closures": [
                item.to_document() for item in self.role_closures
            ],
            "terminal_closure_id": self.terminal_closure_id,
        }

    def assert_current(
        self,
        *,
        repository_root: str | Path,
        portable_bundle_bytes: bytes,
        public_context_closure_bytes: bytes,
        private_generation_seed: bytes,
        private_salt: bytes,
    ) -> None:
        replayed = replay_v075_portable_semantic_terminal_closure_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
            private_generation_seed=private_generation_seed,
            private_salt=private_salt,
        )
        if replayed.to_document() != self.to_document():
            _fail("semantic terminal currentness check changed")

    def __reduce__(self) -> NoReturn:
        raise TypeError("semantic terminal closure is in-memory-only")


def _build_record_overlays(
    *,
    replayed: construction.V075PortableConstructionMultiroundResultReplayV2,
    bundle: portable.V075PortableOccurrenceEvidenceBundleV2,
    registry: semantic.V075PortableSemanticRegistryV2,
    old_set: semantic.V075PortableSemanticAttestationSetV2,
    source_manifest_id: str,
) -> tuple[V075PortableSemanticTerminalRecordOverlayV2, ...]:
    nodes = replayed.dependency_dag.nodes
    _validate_exact_resolved_dag(records=bundle.records, nodes=nodes)
    declarations = registry.by_role
    old_by_record = {
        item.record_id: item for item in old_set.attestations
    }
    node_by_record = {item.record_id: item for item in nodes}
    if (
        len(old_by_record) != len(bundle.records)
        or len(node_by_record) != len(bundle.records)
    ):
        _fail("semantic terminal source registries omit or duplicate records")
    result = []
    for record in bundle.records:
        declaration = declarations.get(record.role)
        old = old_by_record.get(record.record_id)
        node = node_by_record.get(record.record_id)
        raw = record.canonical_artifact_bytes
        if (
            declaration is None
            or type(old)
            is not semantic.V075PortableRecordSemanticAttestationV2
            or type(node)
            is not construction
            .V075ConstructionMultiroundResultDependencyNodeV2
            or old.record_index != record.index
            or old.role != record.role
            or old.artifact_schema != record.artifact_schema
            or old.semantic_artifact_id != record.semantic_artifact_id
            or old.declaration_id != declaration.declaration_id
            or old.canonical_artifact_sha256
            != hashlib.sha256(raw).hexdigest()
            or old.canonical_artifact_byte_count != len(raw)
            or node.record_index != record.index
            or node.role != record.role
        ):
            _fail("record, declaration, old attestation, and DAG node diverged")
        result.append(
            V075PortableSemanticTerminalRecordOverlayV2(
                _OVERLAY_ISSUER,
                bundle.bundle_id,
                registry.registry_id,
                registry.static_surface_registry_id,
                old_set.attestation_set_id,
                source_manifest_id,
                replayed.result_id,
                replayed.typed_graph.graph_id,
                replayed.dependency_dag.dag_id,
                declaration.declaration_id,
                old.attestation_id,
                declaration.semantic_replay_status,
                old.semantic_replay_status,
                record.index,
                record.record_id,
                record.role,
                record.artifact_schema,
                record.semantic_artifact_id,
                hashlib.sha256(raw).hexdigest(),
                len(raw),
                hashlib.sha256(
                    canonical_json_bytes(node.to_document())
                ).hexdigest(),
                node.source_binding_id,
                node.resolver_kind,
                tuple(node.portable_declared_dependency_record_ids),
                tuple(
                    node.authority_local_semantic_dependency_record_ids
                ),
                tuple(node.effective_dependency_record_ids),
                node.authority_scope,
                node.dependency_depth,
                (
                    V075PortableSemanticTerminalRoleStatusV2
                    .FULL_TYPED_REPLAY
                ),
            )
        )
    return tuple(result)


def _build_role_closures(
    *,
    bundle_id: str,
    registry: semantic.V075PortableSemanticRegistryV2,
    overlays: tuple[V075PortableSemanticTerminalRecordOverlayV2, ...],
    empty_role_registry_id: str,
) -> tuple[V075PortableSemanticTerminalRoleClosureV2, ...]:
    by_role: dict[
        str, list[V075PortableSemanticTerminalRecordOverlayV2]
    ] = {item.role: [] for item in registry.declarations}
    for overlay in overlays:
        try:
            by_role[overlay.role].append(overlay)
        except KeyError as error:
            raise V075PortableSemanticTerminalClosureV2InvariantViolation(
                "present overlay has no old registry declaration"
            ) from error
    result = []
    for declaration in registry.declarations:
        members = tuple(by_role[declaration.role])
        result.append(
            V075PortableSemanticTerminalRoleClosureV2(
                _ROLE_CLOSURE_ISSUER,
                bundle_id,
                registry.registry_id,
                declaration.declaration_id,
                declaration.ordinal,
                declaration.role,
                declaration.artifact_schema,
                (
                    V075PortableSemanticTerminalRoleStatusV2
                    .FULL_TYPED_REPLAY
                    if members
                    else (
                        V075PortableSemanticTerminalRoleStatusV2
                        .NOT_PRESENT_IN_VERIFIED_OCCURRENCE
                    )
                ),
                tuple(item.record_id for item in members),
                tuple(item.overlay_id for item in members),
                tuple(item.old_attestation_id for item in members),
                tuple(item.dependency_node_sha256 for item in members),
                tuple(
                    (item.record_id, item.authority_scope.value)
                    for item in members
                ),
                None if members else empty_role_registry_id,
            )
        )
    return tuple(result)


def _close_after_raw_181(
    *,
    replayed: construction.V075PortableConstructionMultiroundResultReplayV2,
    portable_bundle_bytes: bytes,
) -> V075PortableSemanticTerminalClosureV2:
    bundle, registry, old_set, manifest = _verify_fresh_inputs(
        replayed=replayed,
        portable_bundle_bytes=portable_bundle_bytes,
    )
    overlays = _build_record_overlays(
        replayed=replayed,
        bundle=bundle,
        registry=registry,
        old_set=old_set,
        source_manifest_id=manifest.manifest_id,
    )
    closures = _build_role_closures(
        bundle_id=bundle.bundle_id,
        registry=registry,
        overlays=overlays,
        empty_role_registry_id=(
            replayed.typed_graph.empty_role_registry.registry_id
        ),
    )
    manifest_bytes = manifest.canonical_bytes
    terminal = V075PortableSemanticTerminalClosureV2(
        _TERMINAL_ISSUER,
        bundle.bundle_id,
        hashlib.sha256(portable_bundle_bytes).hexdigest(),
        replayed.occurrence_id,
        replayed.public_context_closure_id,
        manifest.manifest_id,
        hashlib.sha256(manifest_bytes).hexdigest(),
        len(manifest_bytes),
        registry.registry_id,
        registry.static_surface_registry_id,
        old_set.attestation_set_id,
        replayed.result_id,
        replayed.typed_graph.graph_id,
        replayed.dependency_dag.dag_id,
        replayed.typed_graph.empty_role_registry.registry_id,
        replayed,
        registry,
        old_set,
        manifest,
        overlays,
        closures,
    )
    if len(terminal.canonical_bytes) > MAX_OUTPUT_BYTES:
        _fail("semantic terminal closure exceeds its output byte cap")
    return terminal


def replay_v075_portable_semantic_terminal_closure_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075PortableSemanticTerminalClosureV2:
    """Replay raw contract 1.81 first, then close the semantic overlay."""

    # Strict first operation: no argument is inspected, parsed, hashed, or
    # retained before exact raw contract 1.81 succeeds.
    try:
        replayed = (
            construction
            .replay_v075_portable_construction_multiround_result_v2(
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=public_context_closure_bytes,
                private_generation_seed=private_generation_seed,
                private_salt=private_salt,
            )
        )
        return _close_after_raw_181(
            replayed=replayed,
            portable_bundle_bytes=portable_bundle_bytes,
        )
    except Exception:
        raise V075PortableSemanticTerminalClosureV2InvariantViolation(
            _REPLAY_MISMATCH
        ) from None


def verify_v075_portable_semantic_terminal_closure_bytes_v2(
    *,
    closure_bytes: bytes,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075PortableSemanticTerminalClosureV2:
    """Replay raw 1.81 before parsing and comparing one claimed closure."""

    # The claimed bytes are deliberately untouched until raw 1.81 succeeds.
    try:
        replayed = (
            construction
            .replay_v075_portable_construction_multiround_result_v2(
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=public_context_closure_bytes,
                private_generation_seed=private_generation_seed,
                private_salt=private_salt,
            )
        )
        document = _strict_document(
            closure_bytes,
            label="portable semantic terminal closure",
        )
        if (
            document.get("construction_semantic_terminal_overlay_complete")
            is not True
            or document.get(
                "construction_present_record_typed_replay_complete"
            )
            is not True
            or document.get(
                "construction_declared_role_closure_complete"
            )
            is not True
            or document.get(
                "construction_portable_semantic_registry_complete"
            )
            is not True
            or document.get(
                "construction_dependency_aware_typed_object_replay_complete"
            )
            is not True
            or document.get(
                "construction_complete_occurrence_bundle_"
                "semantic_replay_complete"
            )
            is not True
            or document.get("semantic_registry_replay_complete") is not False
            or document.get(
                "dependency_aware_typed_object_replay_complete"
            )
            is not False
            or document.get(
                "complete_occurrence_bundle_semantic_replay_complete"
            )
            is not False
            or document.get("source_authority_complete") is not False
            or document.get("code_provenance_complete") is not False
            or document.get("accounting_gate_passed") is not False
            or document.get("official_execution_allowed") is not False
            or document.get("production_authorizing") is not False
            or document.get("scientific_endpoint_credit_allowed") is not False
            or document.get("fresh_heldout_accessed") is not False
            or document.get("plan_certificate") is not False
            or document.get("infeasibility_certificate") is not False
        ):
            _fail("claimed semantic terminal closure changes locked gates")
        expected = _close_after_raw_181(
            replayed=replayed,
            portable_bundle_bytes=portable_bundle_bytes,
        )
        if closure_bytes != expected.canonical_bytes:
            _fail(
                "claimed semantic terminal closure is stale, incomplete, "
                "flattened, substituted, or caller-authored"
            )
        return expected
    except Exception:
        raise V075PortableSemanticTerminalClosureV2InvariantViolation(
            _REPLAY_MISMATCH
        ) from None


def assert_v075_portable_semantic_terminal_production_gate_v2(
    closure: V075PortableSemanticTerminalClosureV2,
) -> NoReturn:
    if type(closure) is not V075PortableSemanticTerminalClosureV2:
        _fail("semantic terminal production gate rejects duck types")
    _ = closure.terminal_closure_id
    raise V075PortableSemanticTerminalClosureProductionV2NotReady(
        "contract 1.82 closes only the composite construction overlay; "
        "source, code, accounting, production, science, and certificate "
        "gates remain locked"
    )


__all__ = [
    "ACCOUNTING_GATE_PASSED",
    "CODE_PROVENANCE_COMPLETE",
    "CONSTRUCTION_DECLARED_ROLE_CLOSURE_COMPLETE",
    "CONSTRUCTION_COMPLETE_OCCURRENCE_BUNDLE_SEMANTIC_REPLAY_COMPLETE",
    "CONSTRUCTION_DEPENDENCY_AWARE_TYPED_OBJECT_REPLAY_COMPLETE",
    "CONSTRUCTION_PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "CONSTRUCTION_PRESENT_RECORD_TYPED_REPLAY_COMPLETE",
    "CONSTRUCTION_SEMANTIC_TERMINAL_OVERLAY_COMPLETE",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "V075PortableSemanticTerminalClosureProductionV2NotReady",
    "V075PortableSemanticTerminalClosureV2",
    "V075PortableSemanticTerminalClosureV2InvariantViolation",
    "V075PortableSemanticTerminalRecordOverlayV2",
    "V075PortableSemanticTerminalRoleClosureV2",
    "V075PortableSemanticTerminalRoleStatusV2",
    "assert_v075_portable_semantic_terminal_production_gate_v2",
    "replay_v075_portable_semantic_terminal_closure_v2",
    "verify_v075_portable_semantic_terminal_closure_bytes_v2",
]
