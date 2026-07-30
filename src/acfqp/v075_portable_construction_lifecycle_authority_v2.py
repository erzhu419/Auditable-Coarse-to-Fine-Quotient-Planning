"""Public M2 construction-lifecycle authority for V0-075.

The authority starts from the hardened contract-1.73 public-lineage replay,
then reconstructs the five construction-lifecycle registry roles from exact
public M1A bytes.  The lifecycle producer's unregistered nested support-source
documents do not create portable transport edges, so this cut additionally
freezes explicit authority-local proof edges to the exact M1A request, batch,
and role-derived outcome records.

Support evidence, support freezes, and lifecycle events are complete public
projections.  The lifecycle closure and its verification remain structurally
unresolved because both transitively bind the unresolved M1A private closure
verification through ``CONSTRUCTION_LINEAGE``.  No B3, private input, target,
production verifier, or held-out authority is accepted.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_public_lineage_authority_v2 as m2_lineage
from acfqp import v075_portable_signed_batch_graph_authority_v2 as m1a


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.74.0"
PROFILE_KEY = "v075_portable_construction_lifecycle_authority_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
PRIVATE_INPUT_CHANNELS_ALLOWED = False
PRIVATE_REPLAY_PERFORMED = False
B3_INPUT_ALLOWED = False
K7_INPUT_ALLOWED = False
M1A_PRIVATE_VERIFICATION_CLAIM_CONSUMED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_M2_CONSTRUCTION_LIFECYCLE_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "M2_CONSTRUCTION_LIFECYCLE_PUBLIC_LEAVES_REPLAYED_"
    "PRIVATE_LINEAGE_FRONTIER_UNRESOLVED"
)
MAX_OUTPUT_BYTES = 64 * 1024 * 1024

ROLE_ORDER = (
    "LIFECYCLE_SUPPORT_EVIDENCE",
    "LIFECYCLE_SUPPORT_FREEZE",
    "LIFECYCLE_EVENT",
    "CONSTRUCTION_LIFECYCLE",
    "CONSTRUCTION_LIFECYCLE_VERIFICATION",
)
_ROLE_SET = frozenset(ROLE_ORDER)
_FULL_PUBLIC_ROLES = frozenset(ROLE_ORDER[:3])
_STRUCTURAL_ROLES = frozenset(ROLE_ORDER[3:])
_ROLE_SCHEMA = MappingProxyType(
    {
        "LIFECYCLE_SUPPORT_EVIDENCE": (
            "acfqp.v075_batch_support_evidence.v2"
        ),
        "LIFECYCLE_SUPPORT_FREEZE": (
            "acfqp.v075_batch_support_freeze.v2"
        ),
        "LIFECYCLE_EVENT": "acfqp.v075_batch_lifecycle_event.v2",
        "CONSTRUCTION_LIFECYCLE": (
            "acfqp.v075_batch_occurrence_lifecycle.v2"
        ),
        "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
            "acfqp.v075_batch_occurrence_lifecycle_verification.v2"
        ),
    }
)
_ROLE_ID_FIELD = MappingProxyType(
    {
        "LIFECYCLE_SUPPORT_EVIDENCE": "evidence_id",
        "LIFECYCLE_SUPPORT_FREEZE": "freeze_id",
        "LIFECYCLE_EVENT": "event_id",
        "CONSTRUCTION_LIFECYCLE": "closure_id",
        "CONSTRUCTION_LIFECYCLE_VERIFICATION": "verification_id",
    }
)
_SOURCE_RECORD_ROLES = frozenset(
    {
        "SIGNED_BATCH_REQUEST",
        "SIGNED_OBSERVATION_BATCH",
        "SIGNED_BATCH_OUTCOME",
    }
)

DOMAIN_TAGS = MappingProxyType(
    {
        "support_source_binding": (
            "acfqp:v075-lifecycle-support-source-binding:v2"
        ),
        "typed_graph": (
            "acfqp:v075-portable-construction-lifecycle-typed-graph:v2"
        ),
        "dependency_dag": (
            "acfqp:v075-portable-construction-lifecycle-dependency-dag:v2"
        ),
        "record_attestation": (
            "acfqp:v075-portable-construction-lifecycle-record-"
            "attestation:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-construction-lifecycle-role-closure:v2"
        ),
        "aggregate": (
            "acfqp:v075-portable-construction-lifecycle-authority:v2"
        ),
    }
)

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 lifecycle consumer content domains overlap")


class V075PortableConstructionLifecycleV2InvariantViolation(ValueError):
    """A lifecycle record, source edge, identity, or closure was invalid."""


class V075PortableConstructionLifecycleProductionV2NotReady(RuntimeError):
    """This construction-only public cut cannot authorize production."""


class V075PortableConstructionLifecycleRoleStatusV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED = (
        "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
    )
    NOT_PRESENT_IN_OCCURRENCE = "NOT_PRESENT_IN_OCCURRENCE"


class V075PortableConstructionLifecycleResolverKindV2(str, Enum):
    UPSTREAM_M2_PUBLIC_LINEAGE = "UPSTREAM_M2_PUBLIC_LINEAGE"
    M2_LIFECYCLE_SUPPORT_EVIDENCE = "M2_LIFECYCLE_SUPPORT_EVIDENCE"
    M2_LIFECYCLE_SUPPORT_FREEZE = "M2_LIFECYCLE_SUPPORT_FREEZE"
    M2_LIFECYCLE_EVENT = "M2_LIFECYCLE_EVENT"
    M2_CONSTRUCTION_LIFECYCLE_PUBLIC_PROJECTION = (
        "M2_CONSTRUCTION_LIFECYCLE_PUBLIC_PROJECTION"
    )
    M2_CONSTRUCTION_LIFECYCLE_VERIFICATION_PUBLIC_PROJECTION = (
        "M2_CONSTRUCTION_LIFECYCLE_VERIFICATION_PUBLIC_PROJECTION"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


def _fail(message: str) -> NoReturn:
    raise V075PortableConstructionLifecycleV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableConstructionLifecycleV2InvariantViolation(
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
        raise V075PortableConstructionLifecycleV2InvariantViolation(
            str(error)
        ) from error


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V075PortableConstructionLifecycleV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _raw(value: Any) -> bytes:
    return canonical_json_bytes(value.to_document())


def _m1a_graph(
    upstream: m2_lineage.V075PortablePublicLineageReplayV2,
    *,
    _upstream_already_current: bool = False,
) -> Any:
    if (
        type(upstream)
        is not m2_lineage.V075PortablePublicLineageReplayV2
    ):
        _fail("lifecycle authority requires exact hardened 1.73 replay")
    if not _upstream_already_current:
        upstream._assert_current()  # noqa: SLF001
    return (
        upstream.typed_graph.m2_result.typed_graph.m1b_result.typed_graph
        .m1a_result.typed_graph
    )


_RECORD_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class _LifecycleRecordBindingV2:
    _issuer: InitVar[object]
    record_id: str
    record_index: int
    role: str
    artifact_schema: str
    semantic_artifact_id: str
    dependency_record_ids: tuple[str, ...]
    canonical_artifact_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RECORD_BINDING_ISSUER:
            _fail("lifecycle record binding is caller-minted")
        self._assert_current()

    def _assert_current(self) -> None:
        _cid(self.record_id, "lifecycle record")
        _cid(self.semantic_artifact_id, "lifecycle semantic artifact")
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _ROLE_SET
            or self.artifact_schema != _ROLE_SCHEMA[self.role]
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
        ):
            _fail("lifecycle record binding is malformed")
        for value in self.dependency_record_ids:
            _cid(value, "lifecycle portable dependency")
        document = _strict_document(
            self.canonical_artifact_bytes,
            label=f"lifecycle {self.role}",
        )
        if (
            document.get("schema") != self.artifact_schema
            or document.get(_ROLE_ID_FIELD[self.role])
            != self.semantic_artifact_id
        ):
            _fail("lifecycle record bytes are role/schema-transplanted")
        domain = portable._record_domain(self.role)  # noqa: SLF001
        payload = {
            "schema": "acfqp.v075_portable_evidence_artifact_record.v2",
            "schema_version": portable.SCHEMA_VERSION,
            "profile_key": portable.PROFILE_KEY,
            "index": self.record_index,
            "role": self.role,
            "artifact_schema": self.artifact_schema,
            "artifact_domain_tag": domain,
            "semantic_artifact_id": self.semantic_artifact_id,
            "dependency_record_ids": list(self.dependency_record_ids),
            "canonical_artifact_bytes_hex": (
                self.canonical_artifact_bytes.hex()
            ),
            "raw_bytes_complete": True,
            "private_material_serialized": False,
            "official_execution_allowed": False,
        }
        if portable._hash(domain, payload) != self.record_id:  # noqa: SLF001
            _fail("lifecycle portable record ID is stale or rehashed")

    def commitment_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
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


def _binding_from_record(record: Any) -> _LifecycleRecordBindingV2:
    return _LifecycleRecordBindingV2(
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
class V075LifecycleSupportSourceBindingV2:
    """One explicit proof edge from lifecycle evidence to exact M1A rows."""

    _issuer: InitVar[object]
    support_evidence_record_id: str
    support_evidence_id: str
    source_ordinal: int
    discovery_batch_id: str
    discovery_request_id: str
    discovery_outcome_id: str
    discovery_outcome_count: int
    discovery_reward_numerator: int
    discovery_reward_denominator: int
    signed_request_record_id: str
    signed_batch_record_id: str
    signed_outcome_record_id: str
    signed_request_sha256: str
    signed_batch_sha256: str
    signed_outcome_sha256: str
    source_aggregate_sha256: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_BINDING_ISSUER:
            _fail("lifecycle support-source binding is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_binding_id",
            _hash("support_source_binding", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (
                self.support_evidence_record_id,
                "support-source evidence record",
            ),
            (self.support_evidence_id, "support-source evidence"),
            (self.discovery_batch_id, "support-source batch"),
            (self.discovery_request_id, "support-source request"),
            (self.discovery_outcome_id, "support-source outcome"),
            (self.signed_request_record_id, "support-source request record"),
            (self.signed_batch_record_id, "support-source batch record"),
            (self.signed_outcome_record_id, "support-source outcome record"),
            (self.signed_request_sha256, "support-source request digest"),
            (self.signed_batch_sha256, "support-source batch digest"),
            (self.signed_outcome_sha256, "support-source outcome digest"),
            (
                self.source_aggregate_sha256,
                "support-source aggregate digest",
            ),
        ):
            _cid(value, label)
        if (
            type(self.source_ordinal) is not int
            or self.source_ordinal < 0
            or type(self.discovery_outcome_count) is not int
            or self.discovery_outcome_count <= 0
            or type(self.discovery_reward_numerator) is not int
            or self.discovery_reward_numerator < 0
            or type(self.discovery_reward_denominator) is not int
            or self.discovery_reward_denominator <= 0
            or len(set(self.semantic_source_record_ids)) != 3
        ):
            _fail("lifecycle support-source binding is malformed")
        reward = Fraction(
            self.discovery_reward_numerator,
            self.discovery_reward_denominator,
        )
        if (
            reward.numerator != self.discovery_reward_numerator
            or reward.denominator != self.discovery_reward_denominator
        ):
            _fail("lifecycle support-source reward is not reduced")

    @property
    def semantic_source_record_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                (
                    self.signed_request_record_id,
                    self.signed_batch_record_id,
                    self.signed_outcome_record_id,
                )
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_lifecycle_support_source_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "support_evidence_record_id": self.support_evidence_record_id,
            "support_evidence_id": self.support_evidence_id,
            "source_ordinal": self.source_ordinal,
            "discovery_batch_id": self.discovery_batch_id,
            "discovery_request_id": self.discovery_request_id,
            "discovery_outcome_id": self.discovery_outcome_id,
            "discovery_outcome_count": self.discovery_outcome_count,
            "discovery_reward": {
                "numerator": self.discovery_reward_numerator,
                "denominator": self.discovery_reward_denominator,
            },
            "signed_request_record_id": self.signed_request_record_id,
            "signed_batch_record_id": self.signed_batch_record_id,
            "signed_outcome_record_id": self.signed_outcome_record_id,
            "semantic_source_record_ids": list(
                self.semantic_source_record_ids
            ),
            "signed_request_sha256": self.signed_request_sha256,
            "signed_batch_sha256": self.signed_batch_sha256,
            "signed_outcome_sha256": self.signed_outcome_sha256,
            "source_aggregate_sha256": self.source_aggregate_sha256,
            "portable_declared_edge": False,
            "authority_local_exact_semantic_edge": True,
            "private_replay_performed": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._binding_id != _hash(
            "support_source_binding",
            self._payload(),
        ):
            _fail("lifecycle support-source binding identity is stale")

    @property
    def binding_id(self) -> str:
        self._assert_current()
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "binding_id": self._binding_id}


def _m1a_record_maps(graph: Any) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[bytes, Any],
]:
    request_records: dict[str, Any] = {}
    batch_records: dict[str, Any] = {}
    outcome_records: dict[bytes, Any] = {}
    for item in graph.record_bindings:
        if item.role == "SIGNED_BATCH_REQUEST":
            target = request_records
            key: Any = item.semantic_artifact_id
        elif item.role == "SIGNED_OBSERVATION_BATCH":
            target = batch_records
            key = item.semantic_artifact_id
        elif item.role == "SIGNED_BATCH_OUTCOME":
            target = outcome_records
            key = item.canonical_artifact_bytes
        else:
            continue
        if key in target:
            _fail("M1A lifecycle source record is duplicated")
        target[key] = item
    if not request_records or not batch_records or not outcome_records:
        _fail("M1A lifecycle source registry is incomplete")
    return request_records, batch_records, outcome_records


def _derive_support_source_bindings(
    *,
    graph: Any,
    closure: lifecycle.V075BatchOccurrenceLifecycleClosureV2,
    target_bindings: tuple[_LifecycleRecordBindingV2, ...],
) -> tuple[V075LifecycleSupportSourceBindingV2, ...]:
    evidence_records = {
        item.semantic_artifact_id: item
        for item in target_bindings
        if item.role == "LIFECYCLE_SUPPORT_EVIDENCE"
    }
    if len(evidence_records) != len(closure.support_evidence):
        _fail("lifecycle support-evidence record registry is incomplete")
    request_records, batch_records, outcome_records = _m1a_record_maps(graph)
    batches = {item.batch_id: item for item in graph.batches}
    if len(batches) != len(graph.batches):
        _fail("M1A lifecycle batch registry is duplicated")
    result: list[V075LifecycleSupportSourceBindingV2] = []
    for evidence in closure.support_evidence:
        evidence_record = evidence_records.get(evidence.evidence_id)
        if evidence_record is None:
            _fail("lifecycle support evidence lacks its portable record")
        for ordinal, source in enumerate(evidence.source_aggregates):
            batch = batches.get(source.discovery_batch_id)
            request_record = request_records.get(
                source.discovery_request_id
            )
            batch_record = batch_records.get(source.discovery_batch_id)
            if (
                batch is None
                or request_record is None
                or batch_record is None
                or batch.request.request_id != source.discovery_request_id
            ):
                _fail("lifecycle support source was request/batch-transplanted")
            outcomes = tuple(
                item
                for item in batch.outcomes
                if item.outcome_id == source.discovery_outcome_id
                and item.count == source.discovery_outcome_count
                and item.reward_sum == source.discovery_reward_sum
            )
            if len(outcomes) != 1:
                _fail(
                    "lifecycle support source count/reward/outcome differs "
                    "from the exact signed batch"
                )
            outcome = outcomes[0]
            outcome_raw = _raw(outcome)
            outcome_record = outcome_records.get(outcome_raw)
            if outcome_record is None:
                _fail("lifecycle support source lacks role-derived outcome")
            source_raw = canonical_json_bytes(source.to_document())
            reward = source.discovery_reward_sum
            result.append(
                V075LifecycleSupportSourceBindingV2(
                    _SOURCE_BINDING_ISSUER,
                    evidence_record.record_id,
                    evidence.evidence_id,
                    ordinal,
                    source.discovery_batch_id,
                    source.discovery_request_id,
                    source.discovery_outcome_id,
                    source.discovery_outcome_count,
                    reward.numerator,
                    reward.denominator,
                    request_record.record_id,
                    batch_record.record_id,
                    outcome_record.record_id,
                    hashlib.sha256(
                        request_record.canonical_artifact_bytes
                    ).hexdigest(),
                    hashlib.sha256(
                        batch_record.canonical_artifact_bytes
                    ).hexdigest(),
                    hashlib.sha256(outcome_raw).hexdigest(),
                    hashlib.sha256(source_raw).hexdigest(),
                )
            )
    if not result:
        _fail("lifecycle support-source binding registry is empty")
    return tuple(result)


def _assert_exact_support_source_bindings(
    *,
    claimed: tuple[V075LifecycleSupportSourceBindingV2, ...],
    expected: tuple[V075LifecycleSupportSourceBindingV2, ...],
) -> None:
    if (
        type(claimed) is not tuple
        or type(expected) is not tuple
        or not claimed
        or any(
            type(item) is not V075LifecycleSupportSourceBindingV2
            for item in claimed
        )
    ):
        _fail("lifecycle support-source binding registry is malformed")
    for item in claimed:
        item._assert_current()
    if tuple(
        (item._payload(), item._binding_id) for item in claimed
    ) != tuple(
        (item._payload(), item._binding_id) for item in expected
    ):
        _fail(
            "lifecycle support-source binding was omitted, transplanted, "
            "or reordered"
        )


def _additional_source_edges(
    bindings: tuple[V075LifecycleSupportSourceBindingV2, ...],
) -> Mapping[str, tuple[str, ...]]:
    grouped: dict[str, set[str]] = {}
    for item in bindings:
        item._assert_current()
        grouped.setdefault(item.support_evidence_record_id, set()).update(
            item.semantic_source_record_ids
        )
    return MappingProxyType(
        {
            key: tuple(sorted(values))
            for key, values in sorted(grouped.items())
        }
    )


def _private_verification_binding(graph: Any) -> Any:
    matches = tuple(
        item
        for item in graph.record_bindings
        if item.role == m1a.M1A_VERIFICATION_ROLE
    )
    if len(matches) != 1:
        _fail("lifecycle authority requires one unresolved M1A verification")
    return matches[0]


def _construction_lineage_binding(
    upstream: m2_lineage.V075PortablePublicLineageReplayV2,
) -> Any:
    matches = tuple(
        item
        for item in upstream.typed_graph.record_bindings
        if item.role == "CONSTRUCTION_LINEAGE"
    )
    if len(matches) != 1:
        _fail("lifecycle authority requires one exact construction lineage")
    return matches[0]


def _replay_lifecycle(
    *,
    upstream: m2_lineage.V075PortablePublicLineageReplayV2,
    lifecycle_bytes: bytes,
    _upstream_already_current: bool = False,
) -> tuple[
    lifecycle.V075BatchOccurrenceLifecycleClosureV2,
    lifecycle.V075BatchOccurrenceLifecycleVerificationV2,
]:
    graph = _m1a_graph(
        upstream,
        _upstream_already_current=_upstream_already_current,
    )
    lineage_binding = _construction_lineage_binding(upstream)
    try:
        return lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2(
            lifecycle_bytes=lifecycle_bytes,
            lineage_bytes=lineage_binding.canonical_artifact_bytes,
            batch_closure_bytes=graph.closure.canonical_bytes,
            known_stream_identities=graph.used_streams,
        )
    except Exception as error:
        raise V075PortableConstructionLifecycleV2InvariantViolation(
            "M2 construction-lifecycle public byte replay failed"
        ) from error


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableConstructionLifecycleTypedGraphV2:
    """Exact lifecycle reconstruction bound to the hardened 1.73 spine."""

    _issuer: InitVar[object]
    bundle_id: str
    public_context_closure_id: str
    occurrence_id: str
    m2_lineage_result: (
        m2_lineage.V075PortablePublicLineageReplayV2
    ) = field(repr=False)
    lifecycle_closure: (
        lifecycle.V075BatchOccurrenceLifecycleClosureV2
    ) = field(repr=False)
    lifecycle_verification: (
        lifecycle.V075BatchOccurrenceLifecycleVerificationV2
    ) = field(repr=False)
    support_source_bindings: tuple[
        V075LifecycleSupportSourceBindingV2,
        ...,
    ] = field(repr=False)
    record_bindings: tuple[_LifecycleRecordBindingV2, ...] = field(
        repr=False
    )
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("M2 construction-lifecycle typed graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._identity_payload()),
        )

    def _expected_documents_by_role(self) -> Mapping[str, dict[str, bytes]]:
        return MappingProxyType(
            {
                "LIFECYCLE_SUPPORT_EVIDENCE": {
                    item.evidence_id: _raw(item)
                    for item in self.lifecycle_closure.support_evidence
                },
                "LIFECYCLE_SUPPORT_FREEZE": {
                    item.freeze_id: _raw(item)
                    for item in self.lifecycle_closure.support_freezes
                },
                "LIFECYCLE_EVENT": {
                    item.event_id: _raw(item)
                    for item in self.lifecycle_closure.events
                },
                "CONSTRUCTION_LIFECYCLE": {
                    self.lifecycle_closure.closure_id: (
                        self.lifecycle_closure.canonical_bytes
                    )
                },
                "CONSTRUCTION_LIFECYCLE_VERIFICATION": {
                    self.lifecycle_verification.verification_id: _raw(
                        self.lifecycle_verification
                    )
                },
            }
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "construction-lifecycle typed graph bundle"),
            (
                self.public_context_closure_id,
                "construction-lifecycle typed graph context",
            ),
            (
                self.occurrence_id,
                "construction-lifecycle typed graph occurrence",
            ),
        ):
            _cid(value, label)
        if (
            type(self.m2_lineage_result)
            is not m2_lineage.V075PortablePublicLineageReplayV2
            or type(self.lifecycle_closure)
            is not lifecycle.V075BatchOccurrenceLifecycleClosureV2
            or type(self.lifecycle_verification)
            is not lifecycle.V075BatchOccurrenceLifecycleVerificationV2
            or type(self.support_source_bindings) is not tuple
            or not self.support_source_bindings
            or any(
                type(item) is not V075LifecycleSupportSourceBindingV2
                for item in self.support_source_bindings
            )
            or type(self.record_bindings) is not tuple
            or not self.record_bindings
            or any(
                type(item) is not _LifecycleRecordBindingV2
                for item in self.record_bindings
            )
            or tuple(item.record_index for item in self.record_bindings)
            != tuple(
                sorted(item.record_index for item in self.record_bindings)
            )
            or len({item.record_id for item in self.record_bindings})
            != len(self.record_bindings)
        ):
            _fail("M2 construction-lifecycle typed graph is malformed")
        self.m2_lineage_result._assert_current()  # noqa: SLF001
        if (
            self.m2_lineage_result.bundle_id != self.bundle_id
            or self.m2_lineage_result.public_context_closure_id
            != self.public_context_closure_id
            or self.m2_lineage_result.occurrence_id != self.occurrence_id
            or self.lifecycle_closure.occurrence_id != self.occurrence_id
            or self.lifecycle_verification.occurrence_id
            != self.occurrence_id
            or self.lifecycle_verification.lifecycle_closure_id
            != self.lifecycle_closure.closure_id
            or self.lifecycle_verification.scope
            is not lifecycle.V075BatchLifecycleAuthorityScopeV2
            .CONSTRUCTION_ONLY
            or (
                self.lifecycle_verification
                .upstream_production_lineage_verification_id
                is not None
            )
            or self.lifecycle_verification.to_document().get(
                "typed_public_streams_semantically_replayed"
            )
            is not False
        ):
            _fail("M2 construction lifecycle crossed hardened identities")

        lifecycle_records = tuple(
            item
            for item in self.record_bindings
            if item.role == "CONSTRUCTION_LIFECYCLE"
        )
        if len(lifecycle_records) != 1:
            _fail("construction lifecycle must have one closure record")
        expected_closure, expected_verification = _replay_lifecycle(
            upstream=self.m2_lineage_result,
            lifecycle_bytes=(
                lifecycle_records[0].canonical_artifact_bytes
            ),
            _upstream_already_current=True,
        )
        if (
            self.lifecycle_closure.canonical_bytes
            != expected_closure.canonical_bytes
            or self.lifecycle_verification.to_document()
            != expected_verification.to_document()
        ):
            _fail("M2 construction-lifecycle replay result changed")

        expected = self._expected_documents_by_role()
        actual: dict[str, dict[str, bytes]] = {
            role: {} for role in ROLE_ORDER
        }
        upstream_nodes = {
            item.record_id: item
            for item in self.m2_lineage_result.dependency_dag.nodes
        }
        for binding in self.record_bindings:
            binding._assert_current()
            node = upstream_nodes.get(binding.record_id)
            if (
                node is None
                or node.record_index != binding.record_index
                or node.role != binding.role
                or node.direct_dependency_record_ids
                != binding.dependency_record_ids
            ):
                _fail(
                    "lifecycle record differs from hardened 1.73 spine"
                )
            by_id = actual[binding.role]
            if binding.semantic_artifact_id in by_id:
                _fail("lifecycle semantic artifact is duplicated")
            by_id[binding.semantic_artifact_id] = (
                binding.canonical_artifact_bytes
            )
        if actual != expected:
            _fail(
                "lifecycle records differ from exact public reconstruction"
            )
        if (
            not all(actual[role] for role in _FULL_PUBLIC_ROLES)
            or len(actual["CONSTRUCTION_LIFECYCLE"]) != 1
            or len(actual["CONSTRUCTION_LIFECYCLE_VERIFICATION"]) != 1
        ):
            _fail("lifecycle five-role registry is incomplete")

        graph = _m1a_graph(
            self.m2_lineage_result,
            _upstream_already_current=True,
        )
        expected_sources = _derive_support_source_bindings(
            graph=graph,
            closure=self.lifecycle_closure,
            target_bindings=self.record_bindings,
        )
        _assert_exact_support_source_bindings(
            claimed=self.support_source_bindings,
            expected=expected_sources,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_construction_lifecycle_typed_graph.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "public_context_closure_id": self.public_context_closure_id,
            "occurrence_id": self.occurrence_id,
            "hardened_m2_public_lineage_result_id": (
                self.m2_lineage_result._result_id  # noqa: SLF001
            ),
            "hardened_m2_public_lineage_dependency_dag_id": (
                self.m2_lineage_result.dependency_dag._dag_id  # noqa: SLF001
            ),
            "lifecycle_closure_id": self.lifecycle_closure.closure_id,
            "lifecycle_verification_id": (
                self.lifecycle_verification.verification_id
            ),
            "support_source_binding_ids": [
                item._binding_id for item in self.support_source_bindings
            ],
            "ordered_record_commitments": [
                item.commitment_document() for item in self.record_bindings
            ],
            "authority_local_support_source_edges_complete": True,
            "support_evidence_publicly_replayed": True,
            "support_freezes_publicly_replayed": True,
            "lifecycle_events_publicly_replayed": True,
            "construction_lifecycle_public_projection_replayed": True,
            "construction_lifecycle_verification_public_projection_replayed": (
                True
            ),
            "private_law_closure_verification_consumed": False,
            "private_replay_performed": False,
            "private_material_serialized": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._graph_id != _hash("typed_graph", self._identity_payload()):
            _fail("M2 construction-lifecycle typed graph identity is stale")

    @property
    def graph_id(self) -> str:
        self._assert_current()
        return self._graph_id

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "M2 construction-lifecycle typed graph is in-memory-only"
        )


@dataclass(frozen=True, slots=True)
class V075PortableConstructionLifecycleDependencyNodeV2:
    record_id: str
    record_index: int
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    resolver_kind: V075PortableConstructionLifecycleResolverKindV2
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    dependency_depth: int

    def _assert_current(self) -> None:
        sequences = (
            self.portable_declared_dependency_record_ids,
            self.authority_local_semantic_dependency_record_ids,
            self.effective_dependency_record_ids,
            self.unresolved_frontier_record_ids,
        )
        _cid(self.record_id, "construction-lifecycle dependency node")
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or type(self.role) is not str
            or not self.role
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in sequences
            )
            or set(self.effective_dependency_record_ids)
            != (
                set(self.portable_declared_dependency_record_ids)
                | set(self.authority_local_semantic_dependency_record_ids)
            )
            or type(self.resolver_kind)
            is not V075PortableConstructionLifecycleResolverKindV2
            or type(self.local_semantic_authority_resolved) is not bool
            or type(self.semantically_resolved) is not bool
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
            or type(self.dependency_depth) is not int
            or self.dependency_depth <= 0
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
            _fail("construction-lifecycle dependency node is malformed")
        for value in (
            *self.effective_dependency_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "construction-lifecycle dependency edge")

    @property
    def direct_dependency_record_ids(self) -> tuple[str, ...]:
        """Compatibility spelling for the portable transport DAG."""

        return self.portable_declared_dependency_record_ids

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
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
            "resolver_kind": self.resolver_kind.value,
            "local_semantic_authority_resolved": (
                self.local_semantic_authority_resolved
            ),
            "semantically_resolved": self.semantically_resolved,
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
            "dependency_depth": self.dependency_depth,
        }


def _target_resolver_kind(
    role: str,
) -> V075PortableConstructionLifecycleResolverKindV2:
    return {
        "LIFECYCLE_SUPPORT_EVIDENCE": (
            V075PortableConstructionLifecycleResolverKindV2
            .M2_LIFECYCLE_SUPPORT_EVIDENCE
        ),
        "LIFECYCLE_SUPPORT_FREEZE": (
            V075PortableConstructionLifecycleResolverKindV2
            .M2_LIFECYCLE_SUPPORT_FREEZE
        ),
        "LIFECYCLE_EVENT": (
            V075PortableConstructionLifecycleResolverKindV2
            .M2_LIFECYCLE_EVENT
        ),
        "CONSTRUCTION_LIFECYCLE": (
            V075PortableConstructionLifecycleResolverKindV2
            .M2_CONSTRUCTION_LIFECYCLE_PUBLIC_PROJECTION
        ),
        "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
            V075PortableConstructionLifecycleResolverKindV2
            .M2_CONSTRUCTION_LIFECYCLE_VERIFICATION_PUBLIC_PROJECTION
        ),
    }[role]


def _upstream_resolver_kind(
    upstream_local: bool,
) -> V075PortableConstructionLifecycleResolverKindV2:
    if upstream_local:
        return (
            V075PortableConstructionLifecycleResolverKindV2
            .UPSTREAM_M2_PUBLIC_LINEAGE
        )
    return (
        V075PortableConstructionLifecycleResolverKindV2
        .NO_REGISTERED_SEMANTIC_AUTHORITY
    )


def _iterative_construction_lifecycle_dependency_nodes(
    *,
    upstream_nodes: tuple[Any, ...],
    locally_replayed_record_ids: frozenset[str],
    authority_local_source_edges: Mapping[str, tuple[str, ...]],
) -> tuple[V075PortableConstructionLifecycleDependencyNodeV2, ...]:
    """Extend the hardened DAG without recursion, including semantic edges."""

    if (
        type(upstream_nodes) is not tuple
        or not upstream_nodes
        or type(locally_replayed_record_ids) is not frozenset
        or not isinstance(authority_local_source_edges, Mapping)
    ):
        _fail("construction-lifecycle dependency replay is malformed")
    upstream_by_id: dict[str, Any] = {}
    upstream_role: dict[str, str] = {}
    upstream_depth_by_id: dict[str, int] = {}
    for expected_index, item in enumerate(upstream_nodes):
        try:
            record_id = item.record_id
            record_index = item.record_index
            role = item.role
            dependencies = tuple(item.direct_dependency_record_ids)
            upstream_local = item.local_semantic_authority_resolved
            upstream_resolved = item.semantically_resolved
        except (AttributeError, TypeError) as error:
            raise V075PortableConstructionLifecycleV2InvariantViolation(
                "construction-lifecycle upstream node is malformed"
            ) from error
        if (
            record_index != expected_index
            or record_id in upstream_by_id
            or tuple(sorted(set(dependencies))) != dependencies
            or any(value not in upstream_by_id for value in dependencies)
            or type(upstream_local) is not bool
            or type(upstream_resolved) is not bool
        ):
            _fail(
                "construction-lifecycle upstream DAG is duplicated or "
                "non-topological"
            )
        upstream_by_id[record_id] = item
        upstream_role[record_id] = role
        upstream_depth_by_id[record_id] = 1 + max(
            (
                upstream_depth_by_id[value]
                for value in dependencies
            ),
            default=0,
        )

    for value in locally_replayed_record_ids:
        _cid(value, "construction-lifecycle local replay record")
    if not locally_replayed_record_ids <= upstream_by_id.keys():
        _fail("construction-lifecycle local registry has foreign records")
    normalized_edges: dict[str, tuple[str, ...]] = {}
    for target_id, source_ids in authority_local_source_edges.items():
        _cid(target_id, "construction-lifecycle semantic-edge target")
        if (
            target_id not in locally_replayed_record_ids
            or upstream_role.get(target_id)
            != "LIFECYCLE_SUPPORT_EVIDENCE"
            or type(source_ids) is not tuple
            or not source_ids
            or tuple(sorted(set(source_ids))) != source_ids
        ):
            _fail("lifecycle support-source edge registry is malformed")
        for source_id in source_ids:
            source = upstream_by_id.get(source_id)
            if (
                source is None
                or source.role not in _SOURCE_RECORD_ROLES
                or source.semantically_resolved is not True
            ):
                _fail(
                    "lifecycle support-source edge is foreign or unresolved"
                )
        normalized_edges[target_id] = source_ids

    support_ids = {
        value
        for value in locally_replayed_record_ids
        if upstream_role[value] == "LIFECYCLE_SUPPORT_EVIDENCE"
    }
    if set(normalized_edges) != support_ids:
        _fail("lifecycle support-source edges are omitted or transplanted")

    nodes: list[V075PortableConstructionLifecycleDependencyNodeV2] = []
    resolved_by_id: dict[str, bool] = {}
    frontier_by_id: dict[str, tuple[str, ...]] = {}
    role_by_id: dict[str, str] = {}
    depth_by_id: dict[str, int] = {}
    for upstream in upstream_nodes:
        record_id = upstream.record_id
        role = upstream.role
        portable_dependencies = tuple(
            upstream.direct_dependency_record_ids
        )
        semantic_sources = normalized_edges.get(record_id, ())
        effective_dependencies = tuple(
            sorted(set(portable_dependencies) | set(semantic_sources))
        )
        if record_id in locally_replayed_record_ids:
            if role not in _ROLE_SET:
                _fail("local construction-lifecycle role is foreign")
            resolver_kind = _target_resolver_kind(role)
            local_resolved = True
        else:
            local_resolved = upstream.local_semantic_authority_resolved
            if type(local_resolved) is not bool:
                _fail("upstream local semantic status is malformed")
            resolver_kind = _upstream_resolver_kind(local_resolved)

        portable_resolved = all(
            resolved_by_id[value] for value in portable_dependencies
        )
        source_resolved = all(
            upstream_by_id[value].semantically_resolved
            for value in semantic_sources
        )
        semantically_resolved = (
            local_resolved and portable_resolved and source_resolved
        )
        if semantically_resolved:
            frontier: tuple[str, ...] = ()
        elif not local_resolved:
            frontier = (record_id,)
        else:
            unresolved: set[str] = set()
            for dependency_id in portable_dependencies:
                unresolved.update(frontier_by_id[dependency_id])
            for dependency_id in semantic_sources:
                source = upstream_by_id[dependency_id]
                unresolved.update(source.unresolved_frontier_record_ids)
            frontier = tuple(sorted(unresolved))
            if not frontier:
                _fail(
                    "unresolved construction-lifecycle node lacks frontier"
                )
        frontier_roles = tuple(
            sorted(
                {
                    (
                        role
                        if value == record_id
                        else role_by_id.get(value, upstream_role.get(value))
                    )
                    for value in frontier
                }
            )
        )
        if any(value is None for value in frontier_roles):
            _fail("construction-lifecycle frontier role is unknown")
        depth = 1 + max(
            (
                *(
                    depth_by_id[value]
                    for value in portable_dependencies
                ),
                *(
                    upstream_depth_by_id[value]
                    for value in semantic_sources
                ),
            ),
            default=0,
        )
        node = V075PortableConstructionLifecycleDependencyNodeV2(
            record_id,
            upstream.record_index,
            role,
            portable_dependencies,
            semantic_sources,
            effective_dependencies,
            resolver_kind,
            local_resolved,
            semantically_resolved,
            frontier,
            frontier_roles,
            depth,
        )
        node._assert_current()
        nodes.append(node)
        resolved_by_id[record_id] = semantically_resolved
        frontier_by_id[record_id] = frontier
        role_by_id[record_id] = role
        depth_by_id[record_id] = depth
    return tuple(nodes)


_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableConstructionLifecycleDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    m2_lineage_result: (
        m2_lineage.V075PortablePublicLineageReplayV2
    ) = field(repr=False)
    typed_graph_id: str
    support_source_bindings: tuple[
        V075LifecycleSupportSourceBindingV2,
        ...,
    ] = field(repr=False)
    locally_replayed_record_ids: tuple[str, ...]
    nodes: tuple[
        V075PortableConstructionLifecycleDependencyNodeV2,
        ...,
    ] = field(repr=False)
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("construction-lifecycle dependency DAG is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_dag_id",
            _hash("dependency_dag", self._payload()),
        )

    def _validate(
        self,
        *,
        _upstream_already_current: bool = False,
    ) -> None:
        _cid(self.bundle_id, "construction-lifecycle DAG bundle")
        _cid(self.typed_graph_id, "construction-lifecycle typed graph")
        if (
            type(self.m2_lineage_result)
            is not m2_lineage.V075PortablePublicLineageReplayV2
            or type(self.support_source_bindings) is not tuple
            or not self.support_source_bindings
            or any(
                type(item) is not V075LifecycleSupportSourceBindingV2
                for item in self.support_source_bindings
            )
            or type(self.locally_replayed_record_ids) is not tuple
            or tuple(sorted(set(self.locally_replayed_record_ids)))
            != self.locally_replayed_record_ids
            or type(self.nodes) is not tuple
            or not self.nodes
        ):
            _fail("construction-lifecycle dependency DAG is malformed")
        if not _upstream_already_current:
            self.m2_lineage_result._assert_current()  # noqa: SLF001
        edges = _additional_source_edges(self.support_source_bindings)
        expected = _iterative_construction_lifecycle_dependency_nodes(
            upstream_nodes=self.m2_lineage_result.dependency_dag.nodes,
            locally_replayed_record_ids=frozenset(
                self.locally_replayed_record_ids
            ),
            authority_local_source_edges=edges,
        )
        for item in self.nodes:
            item._assert_current()
        if (
            self.m2_lineage_result.bundle_id != self.bundle_id
            or tuple(item.to_document() for item in self.nodes)
            != tuple(item.to_document() for item in expected)
        ):
            _fail(
                "construction-lifecycle dependency DAG is stale or "
                "transplanted"
            )

    def _payload(self) -> dict[str, Any]:
        source_edges = _additional_source_edges(
            self.support_source_bindings
        )
        return {
            "schema": (
                "acfqp.v075_portable_construction_lifecycle_dependency_dag.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "hardened_m2_public_lineage_result_id": (
                self.m2_lineage_result._result_id  # noqa: SLF001
            ),
            "hardened_m2_public_lineage_dependency_dag_id": (
                self.m2_lineage_result.dependency_dag._dag_id  # noqa: SLF001
            ),
            "m2_construction_lifecycle_typed_graph_id": self.typed_graph_id,
            "locally_replayed_record_ids": list(
                self.locally_replayed_record_ids
            ),
            "support_source_binding_ids": [
                item._binding_id for item in self.support_source_bindings
            ],
            "authority_local_source_edges": [
                {
                    "support_evidence_record_id": target_id,
                    "authority_local_semantic_dependency_record_ids": list(
                        source_ids
                    ),
                }
                for target_id, source_ids in source_edges.items()
            ],
            "nodes": [item.to_document() for item in self.nodes],
            "node_count": len(self.nodes),
            "portable_edge_count": sum(
                len(item.portable_declared_dependency_record_ids)
                for item in self.nodes
            ),
            "authority_local_semantic_edge_count": sum(
                len(item.authority_local_semantic_dependency_record_ids)
                for item in self.nodes
            ),
            "maximum_dependency_depth": max(
                item.dependency_depth for item in self.nodes
            ),
            "proof_shape": (
                "ITERATIVE_TOPOLOGICAL_PORTABLE_DAG_PLUS_EXACT_"
                "AUTHORITY_LOCAL_SOURCE_EDGES"
            ),
            "transitive_unresolved_frontier_derived": True,
            "recursive_dependency_walk_used": False,
        }

    def _assert_current(
        self,
        *,
        _upstream_already_current: bool = False,
    ) -> None:
        self._validate(
            _upstream_already_current=_upstream_already_current,
        )
        if self._dag_id != _hash("dependency_dag", self._payload()):
            _fail("construction-lifecycle dependency DAG identity is stale")

    @property
    def dag_id(self) -> str:
        self._assert_current()
        return self._dag_id

    @property
    def nodes_by_id(
        self,
    ) -> Mapping[
        str,
        V075PortableConstructionLifecycleDependencyNodeV2,
    ]:
        self._assert_current()
        return MappingProxyType({item.record_id: item for item in self.nodes})


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableConstructionLifecycleRecordAttestationV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    dependency_dag_id: str
    record_id: str
    record_index: int
    role: str
    semantic_artifact_id: str
    canonical_artifact_sha256: str
    canonical_artifact_byte_count: int
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    resolved_direct_dependency_record_ids: tuple[str, ...]
    unresolved_direct_dependency_record_ids: tuple[str, ...]
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    resolver_kind: V075PortableConstructionLifecycleResolverKindV2
    status: V075PortableConstructionLifecycleRoleStatusV2
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("construction-lifecycle attestation is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("record_attestation", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "lifecycle attestation bundle"),
            (self.typed_graph_id, "lifecycle attestation graph"),
            (self.dependency_dag_id, "lifecycle attestation DAG"),
            (self.record_id, "lifecycle attestation record"),
            (
                self.semantic_artifact_id,
                "lifecycle attestation semantic artifact",
            ),
            (
                self.canonical_artifact_sha256,
                "lifecycle attestation digest",
            ),
        ):
            _cid(value, label)
        sequences = (
            self.portable_declared_dependency_record_ids,
            self.authority_local_semantic_dependency_record_ids,
            self.effective_dependency_record_ids,
            self.resolved_direct_dependency_record_ids,
            self.unresolved_direct_dependency_record_ids,
            self.unresolved_frontier_record_ids,
        )
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _ROLE_SET
            or type(self.canonical_artifact_byte_count) is not int
            or self.canonical_artifact_byte_count <= 0
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in sequences
            )
            or set(self.effective_dependency_record_ids)
            != (
                set(self.portable_declared_dependency_record_ids)
                | set(self.authority_local_semantic_dependency_record_ids)
            )
            or (
                set(self.resolved_direct_dependency_record_ids)
                | set(self.unresolved_direct_dependency_record_ids)
            )
            != set(self.effective_dependency_record_ids)
            or (
                set(self.resolved_direct_dependency_record_ids)
                & set(self.unresolved_direct_dependency_record_ids)
            )
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
            or type(self.resolver_kind)
            is not V075PortableConstructionLifecycleResolverKindV2
            or type(self.status)
            is not V075PortableConstructionLifecycleRoleStatusV2
            or self.status
            is V075PortableConstructionLifecycleRoleStatusV2
            .NOT_PRESENT_IN_OCCURRENCE
        ):
            _fail("construction-lifecycle attestation is malformed")
        expected = (
            V075PortableConstructionLifecycleRoleStatusV2.FULL_PUBLIC
            if not self.unresolved_frontier_record_ids
            else V075PortableConstructionLifecycleRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        if self.status is not expected:
            _fail("construction-lifecycle attestation overclaims semantics")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_construction_lifecycle_"
                "record_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m2_construction_lifecycle_typed_graph_id": self.typed_graph_id,
            "m2_construction_lifecycle_dependency_dag_id": (
                self.dependency_dag_id
            ),
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "semantic_artifact_id": self.semantic_artifact_id,
            "canonical_artifact_sha256": self.canonical_artifact_sha256,
            "canonical_artifact_byte_count": (
                self.canonical_artifact_byte_count
            ),
            "portable_declared_dependency_record_ids": list(
                self.portable_declared_dependency_record_ids
            ),
            "authority_local_semantic_dependency_record_ids": list(
                self.authority_local_semantic_dependency_record_ids
            ),
            "effective_dependency_record_ids": list(
                self.effective_dependency_record_ids
            ),
            "resolved_direct_dependency_record_ids": list(
                self.resolved_direct_dependency_record_ids
            ),
            "unresolved_direct_dependency_record_ids": list(
                self.unresolved_direct_dependency_record_ids
            ),
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
            "resolver_kind": self.resolver_kind.value,
            "status": self.status.value,
            "authority_local_support_source_edges_checked": (
                self.role == "LIFECYCLE_SUPPORT_EVIDENCE"
            ),
            "private_replay_performed": False,
            "official_execution_allowed": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._attestation_id != _hash(
            "record_attestation",
            self._payload(),
        ):
            _fail("construction-lifecycle attestation identity is stale")

    @property
    def attestation_id(self) -> str:
        self._assert_current()
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "attestation_id": self._attestation_id}


def _build_attestations(
    *,
    bundle_id: str,
    typed_graph_id: str,
    dag: V075PortableConstructionLifecycleDependencyDAGV2,
    bindings: tuple[_LifecycleRecordBindingV2, ...],
    _dag_already_current: bool = False,
) -> tuple[V075PortableConstructionLifecycleRecordAttestationV2, ...]:
    if not _dag_already_current:
        dag._assert_current()
    nodes = {item.record_id: item for item in dag.nodes}
    result = []
    for binding in bindings:
        binding._assert_current()
        node = nodes.get(binding.record_id)
        if node is None:
            _fail("lifecycle attestation record is absent from the DAG")
        resolved = tuple(
            value
            for value in node.effective_dependency_record_ids
            if nodes[value].semantically_resolved
        )
        unresolved = tuple(
            value
            for value in node.effective_dependency_record_ids
            if not nodes[value].semantically_resolved
        )
        status = (
            V075PortableConstructionLifecycleRoleStatusV2.FULL_PUBLIC
            if node.semantically_resolved
            else V075PortableConstructionLifecycleRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        result.append(
            V075PortableConstructionLifecycleRecordAttestationV2(
                _ATTESTATION_ISSUER,
                bundle_id,
                typed_graph_id,
                dag._dag_id,
                binding.record_id,
                binding.record_index,
                binding.role,
                binding.semantic_artifact_id,
                hashlib.sha256(
                    binding.canonical_artifact_bytes
                ).hexdigest(),
                len(binding.canonical_artifact_bytes),
                node.portable_declared_dependency_record_ids,
                node.authority_local_semantic_dependency_record_ids,
                node.effective_dependency_record_ids,
                resolved,
                unresolved,
                node.unresolved_frontier_record_ids,
                node.unresolved_frontier_roles,
                node.resolver_kind,
                status,
            )
        )
    return tuple(result)


_ROLE_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableConstructionLifecycleRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    dependency_dag_id: str
    role: str
    status: V075PortableConstructionLifecycleRoleStatusV2
    record_ids: tuple[str, ...]
    attestation_ids: tuple[str, ...]
    unresolved_record_ids: tuple[str, ...]
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("construction-lifecycle role closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "lifecycle role closure bundle"),
            (self.typed_graph_id, "lifecycle role closure graph"),
            (self.dependency_dag_id, "lifecycle role closure DAG"),
        ):
            _cid(value, label)
        sequences = (
            self.record_ids,
            self.attestation_ids,
            self.unresolved_record_ids,
        )
        if (
            self.role not in _ROLE_SET
            or type(self.status)
            is not V075PortableConstructionLifecycleRoleStatusV2
            or any(
                type(values) is not tuple
                or len(set(values)) != len(values)
                for values in sequences
            )
            or type(self.unresolved_frontier_record_ids) is not tuple
            or tuple(sorted(set(self.unresolved_frontier_record_ids)))
            != self.unresolved_frontier_record_ids
            or len(self.record_ids) != len(self.attestation_ids)
            or not set(self.unresolved_record_ids) <= set(self.record_ids)
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
        ):
            _fail("construction-lifecycle role closure is malformed")
        for value in (
            *self.record_ids,
            *self.attestation_ids,
            *self.unresolved_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "construction-lifecycle role closure identity")
        expected = (
            V075PortableConstructionLifecycleRoleStatusV2
            .NOT_PRESENT_IN_OCCURRENCE
            if not self.record_ids
            else (
                V075PortableConstructionLifecycleRoleStatusV2.FULL_PUBLIC
                if not self.unresolved_record_ids
                else V075PortableConstructionLifecycleRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
        )
        if self.status is not expected:
            _fail("construction-lifecycle role status is inconsistent")
        if (
            self.status
            is V075PortableConstructionLifecycleRoleStatusV2.FULL_PUBLIC
            and (
                self.unresolved_frontier_record_ids
                or self.unresolved_frontier_roles
            )
        ):
            _fail("full lifecycle role carries an unresolved frontier")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_construction_lifecycle_role_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m2_construction_lifecycle_typed_graph_id": self.typed_graph_id,
            "m2_construction_lifecycle_dependency_dag_id": (
                self.dependency_dag_id
            ),
            "role": self.role,
            "status": self.status.value,
            "record_ids": list(self.record_ids),
            "attestation_ids": list(self.attestation_ids),
            "unresolved_record_ids": list(self.unresolved_record_ids),
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
            "private_replay_performed": False,
            "official_execution_allowed": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._closure_id != _hash("role_closure", self._payload()):
            _fail("construction-lifecycle role closure identity is stale")

    @property
    def closure_id(self) -> str:
        self._assert_current()
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "closure_id": self._closure_id}


def _build_role_closures(
    *,
    bundle_id: str,
    typed_graph_id: str,
    dependency_dag_id: str,
    bindings: tuple[_LifecycleRecordBindingV2, ...],
    attestations: tuple[
        V075PortableConstructionLifecycleRecordAttestationV2,
        ...,
    ],
    _attestations_already_current: bool = False,
) -> tuple[V075PortableConstructionLifecycleRoleClosureV2, ...]:
    if not _attestations_already_current:
        for item in attestations:
            item._assert_current()
    by_record = {item.record_id: item for item in attestations}
    result = []
    for role in ROLE_ORDER:
        role_bindings = tuple(
            item for item in bindings if item.role == role
        )
        role_attestations = tuple(
            by_record[item.record_id] for item in role_bindings
        )
        unresolved = tuple(
            item
            for item in role_attestations
            if item.status
            is not V075PortableConstructionLifecycleRoleStatusV2.FULL_PUBLIC
        )
        status = (
            V075PortableConstructionLifecycleRoleStatusV2
            .NOT_PRESENT_IN_OCCURRENCE
            if not role_bindings
            else (
                V075PortableConstructionLifecycleRoleStatusV2.FULL_PUBLIC
                if not unresolved
                else V075PortableConstructionLifecycleRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
        )
        result.append(
            V075PortableConstructionLifecycleRoleClosureV2(
                _ROLE_CLOSURE_ISSUER,
                bundle_id,
                typed_graph_id,
                dependency_dag_id,
                role,
                status,
                tuple(item.record_id for item in role_bindings),
                tuple(
                    item._attestation_id for item in role_attestations
                ),
                tuple(item.record_id for item in unresolved),
                tuple(
                    sorted(
                        {
                            value
                            for item in unresolved
                            for value in (
                                item.unresolved_frontier_record_ids
                            )
                        }
                    )
                ),
                tuple(
                    sorted(
                        {
                            value
                            for item in unresolved
                            for value in item.unresolved_frontier_roles
                        }
                    )
                ),
            )
        )
    return tuple(result)


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableConstructionLifecycleReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075PortableConstructionLifecycleTypedGraphV2 = field(
        repr=False
    )
    dependency_dag: (
        V075PortableConstructionLifecycleDependencyDAGV2
    ) = field(repr=False)
    attestations: tuple[
        V075PortableConstructionLifecycleRecordAttestationV2,
        ...,
    ]
    role_closures: tuple[
        V075PortableConstructionLifecycleRoleClosureV2,
        ...,
    ]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("construction-lifecycle result is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "construction-lifecycle result bundle"),
            (
                self.occurrence_id,
                "construction-lifecycle result occurrence",
            ),
            (
                self.public_context_closure_id,
                "construction-lifecycle result context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph)
            is not V075PortableConstructionLifecycleTypedGraphV2
            or type(self.dependency_dag)
            is not V075PortableConstructionLifecycleDependencyDAGV2
            or type(self.attestations) is not tuple
            or any(
                type(item)
                is not V075PortableConstructionLifecycleRecordAttestationV2
                for item in self.attestations
            )
            or tuple(item.record_index for item in self.attestations)
            != tuple(
                sorted(item.record_index for item in self.attestations)
            )
            or type(self.role_closures) is not tuple
            or tuple(item.role for item in self.role_closures) != ROLE_ORDER
            or any(
                type(item)
                is not V075PortableConstructionLifecycleRoleClosureV2
                for item in self.role_closures
            )
        ):
            _fail("construction-lifecycle result is malformed")
        self.typed_graph._assert_current()
        self.dependency_dag._assert_current(
            _upstream_already_current=True,
        )
        graph_id = self.typed_graph._graph_id
        dag_id = self.dependency_dag._dag_id
        if (
            self.typed_graph.bundle_id != self.bundle_id
            or self.typed_graph.occurrence_id != self.occurrence_id
            or self.typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or self.dependency_dag.bundle_id != self.bundle_id
            or self.dependency_dag.typed_graph_id != graph_id
            or self.dependency_dag.m2_lineage_result
            is not self.typed_graph.m2_lineage_result
            or self.dependency_dag.support_source_bindings
            != self.typed_graph.support_source_bindings
        ):
            _fail("construction-lifecycle result crossed identities")
        expected_attestations = _build_attestations(
            bundle_id=self.bundle_id,
            typed_graph_id=graph_id,
            dag=self.dependency_dag,
            bindings=self.typed_graph.record_bindings,
            _dag_already_current=True,
        )
        for item in self.attestations:
            item._assert_current()
        if tuple(
            (item._payload(), item._attestation_id)
            for item in self.attestations
        ) != tuple(
            (item._payload(), item._attestation_id)
            for item in expected_attestations
        ):
            _fail(
                "construction-lifecycle attestations are stale or "
                "transplanted"
            )
        expected_closures = _build_role_closures(
            bundle_id=self.bundle_id,
            typed_graph_id=graph_id,
            dependency_dag_id=dag_id,
            bindings=self.typed_graph.record_bindings,
            attestations=self.attestations,
            _attestations_already_current=True,
        )
        for item in self.role_closures:
            item._assert_current()
        if tuple(
            (item._payload(), item._closure_id)
            for item in self.role_closures
        ) != tuple(
            (item._payload(), item._closure_id)
            for item in expected_closures
        ):
            _fail("construction-lifecycle role closures are stale")
        status_by_role = {
            item.role: item.status for item in self.role_closures
        }
        if (
            any(
                status_by_role[role]
                is not V075PortableConstructionLifecycleRoleStatusV2
                .FULL_PUBLIC
                for role in _FULL_PUBLIC_ROLES
            )
            or any(
                status_by_role[role]
                is not V075PortableConstructionLifecycleRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
                for role in _STRUCTURAL_ROLES
            )
        ):
            _fail("construction-lifecycle normative closure is invalid")

        private = _private_verification_binding(
            _m1a_graph(
                self.typed_graph.m2_lineage_result,
                _upstream_already_current=True,
            )
        )
        private_frontier = (private.record_id,)
        private_roles = (private.role,)
        for role_closure in self.role_closures:
            if role_closure.role in _FULL_PUBLIC_ROLES:
                if (
                    role_closure.unresolved_frontier_record_ids
                    or role_closure.unresolved_frontier_roles
                ):
                    _fail("full lifecycle leaf carries private frontier")
            elif (
                role_closure.unresolved_frontier_record_ids
                != private_frontier
                or role_closure.unresolved_frontier_roles != private_roles
            ):
                _fail(
                    "construction lifecycle did not preserve the exact "
                    "private M1A frontier"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_construction_lifecycle_authority.v2"
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
            "hardened_m2_public_lineage_result_id": (
                self.typed_graph.m2_lineage_result._result_id  # noqa: SLF001
            ),
            "m2_construction_lifecycle_typed_graph_id": (
                self.typed_graph._graph_id
            ),
            "m2_construction_lifecycle_dependency_dag_id": (
                self.dependency_dag._dag_id
            ),
            "role_order": list(ROLE_ORDER),
            "role_statuses": {
                item.role: item.status.value for item in self.role_closures
            },
            "support_source_binding_ids": [
                item._binding_id
                for item in self.typed_graph.support_source_bindings
            ],
            "record_attestation_ids": [
                item._attestation_id for item in self.attestations
            ],
            "role_closure_ids": [
                item._closure_id for item in self.role_closures
            ],
            "support_source_edges_exact_and_complete": True,
            "lifecycle_public_leaf_semantics_complete": True,
            "construction_lifecycle_public_projection_complete": True,
            "construction_lifecycle_private_lineage_complete": False,
            "hardened_1_73_called_before_local_bundle_replay": True,
            "production_lifecycle_verifier_called": False,
            "private_verifier_called": False,
            "b3_input_consumed": False,
            "k7_input_consumed": False,
            "private_input_channels_allowed": False,
            "private_replay_performed": False,
            "m1a_private_verification_claim_consumed": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "portable_semantic_registry_complete": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_material_serialized": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._result_id != _hash("aggregate", self._payload()):
            _fail("construction-lifecycle result identity is stale")

    @property
    def result_id(self) -> str:
        self._assert_current()
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            **self._payload(),
            "support_source_bindings": [
                item.to_document()
                for item in self.typed_graph.support_source_bindings
            ],
            "attestations": [
                item.to_document() for item in self.attestations
            ],
            "role_closures": [
                item.to_document() for item in self.role_closures
            ],
            "result_id": self._result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_OUTPUT_BYTES:
            _fail("construction-lifecycle result exceeds output byte cap")
        return raw


def replay_v075_portable_construction_lifecycle_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
) -> V075PortableConstructionLifecycleReplayV2:
    """Replay lifecycle roles from raw public authorities, starting at 1.73."""

    if (
        type(portable_bundle_bytes) is not bytes
        or type(public_context_closure_bytes) is not bytes
    ):
        _fail(
            "M2 construction lifecycle accepts canonical raw byte "
            "authorities only"
        )
    try:
        upstream = m2_lineage.replay_v075_portable_public_lineage_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
        )
    except Exception as error:
        raise V075PortableConstructionLifecycleV2InvariantViolation(
            "M2 construction lifecycle hardened 1.73 replay failed"
        ) from error
    try:
        bundle = (
            portable
            .verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
    except Exception as error:
        raise V075PortableConstructionLifecycleV2InvariantViolation(
            "M2 construction lifecycle portable bundle replay failed "
            "after hardened 1.73"
        ) from error
    if (
        bundle.bundle_id != upstream.bundle_id
        or bundle.occurrence_id != upstream.occurrence_id
    ):
        _fail("construction-lifecycle raw authorities were transplanted")

    target_records = tuple(
        item for item in bundle.records if item.role in _ROLE_SET
    )
    bindings = tuple(_binding_from_record(item) for item in target_records)
    lifecycle_records = tuple(
        item
        for item in bindings
        if item.role == "CONSTRUCTION_LIFECYCLE"
    )
    if len(lifecycle_records) != 1:
        _fail("construction lifecycle requires one raw lifecycle closure")
    closure, verification = _replay_lifecycle(
        upstream=upstream,
        lifecycle_bytes=lifecycle_records[0].canonical_artifact_bytes,
        _upstream_already_current=True,
    )
    graph = _m1a_graph(upstream, _upstream_already_current=True)
    support_sources = _derive_support_source_bindings(
        graph=graph,
        closure=closure,
        target_bindings=bindings,
    )
    typed_graph = V075PortableConstructionLifecycleTypedGraphV2(
        _TYPED_GRAPH_ISSUER,
        bundle.bundle_id,
        upstream.public_context_closure_id,
        bundle.occurrence_id,
        upstream,
        closure,
        verification,
        support_sources,
        bindings,
    )
    local_ids = tuple(sorted(item.record_id for item in bindings))
    nodes = _iterative_construction_lifecycle_dependency_nodes(
        upstream_nodes=upstream.dependency_dag.nodes,
        locally_replayed_record_ids=frozenset(local_ids),
        authority_local_source_edges=_additional_source_edges(
            support_sources
        ),
    )
    dag = V075PortableConstructionLifecycleDependencyDAGV2(
        _DAG_ISSUER,
        bundle.bundle_id,
        upstream,
        typed_graph._graph_id,
        support_sources,
        local_ids,
        nodes,
    )
    attestations = _build_attestations(
        bundle_id=bundle.bundle_id,
        typed_graph_id=typed_graph._graph_id,
        dag=dag,
        bindings=bindings,
    )
    role_closures = _build_role_closures(
        bundle_id=bundle.bundle_id,
        typed_graph_id=typed_graph._graph_id,
        dependency_dag_id=dag._dag_id,
        bindings=bindings,
        attestations=attestations,
    )
    return V075PortableConstructionLifecycleReplayV2(
        _RESULT_ISSUER,
        bundle.bundle_id,
        bundle.occurrence_id,
        upstream.public_context_closure_id,
        typed_graph,
        dag,
        attestations,
        role_closures,
    )


def open_v075_production_from_portable_construction_lifecycle_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortableConstructionLifecycleProductionV2NotReady(
        "M2 construction lifecycle closes three public leaf roles and the "
        "two public projection documents, but their private M1A lineage "
        "frontier, source authority, code provenance, and remaining "
        "portable semantic registry are incomplete"
    )


__all__ = [
    "B3_INPUT_ALLOWED",
    "CODE_PROVENANCE_COMPLETE",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "K7_INPUT_ALLOWED",
    "M1A_PRIVATE_VERIFICATION_CLAIM_CONSUMED",
    "MAX_OUTPUT_BYTES",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRIVATE_INPUT_CHANNELS_ALLOWED",
    "PRIVATE_REPLAY_PERFORMED",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "V075LifecycleSupportSourceBindingV2",
    "V075PortableConstructionLifecycleDependencyDAGV2",
    "V075PortableConstructionLifecycleDependencyNodeV2",
    "V075PortableConstructionLifecycleProductionV2NotReady",
    "V075PortableConstructionLifecycleRecordAttestationV2",
    "V075PortableConstructionLifecycleReplayV2",
    "V075PortableConstructionLifecycleResolverKindV2",
    "V075PortableConstructionLifecycleRoleClosureV2",
    "V075PortableConstructionLifecycleRoleStatusV2",
    "V075PortableConstructionLifecycleTypedGraphV2",
    "V075PortableConstructionLifecycleV2InvariantViolation",
    "open_v075_production_from_portable_construction_lifecycle_v2",
    "replay_v075_portable_construction_lifecycle_v2",
]
