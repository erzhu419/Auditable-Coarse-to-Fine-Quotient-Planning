"""Portable M1A authority for the observer-signed batch graph.

The only public entry point accepts three raw authorities: a repository root,
one portable occurrence bundle, and one public-context closure.  It crosses
the portable, M0, and B1 raw replay boundaries before reconstructing the
issuer-backed signed-batch journal closure with the exact M0 stream set.

Six public roles are replayed completely.  The closure-verification record is
retained and structurally checked, but its exact-native replay claim remains
unresolved because that claim requires private environment and salt material.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_portable_observer_open_binding_authority_v2 as b1
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_public_semantic_replay_v2 as m0
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_public_graph_semantics_v1 as graph


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.67.0"
PROFILE_KEY = "v075_portable_signed_batch_graph_authority_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
M1A_ROLE_SEMANTICS_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
OBSERVER_OPEN_ALLOWED = False
PRIVATE_INPUT_CHANNELS_ALLOWED = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_M1A_SIGNED_BATCH_GRAPH_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "M1A_SIGNED_BATCH_GRAPH_REPLAYED_PRIVATE_CLOSURE_"
    "VERIFICATION_INCOMPLETE"
)
MAX_OUTPUT_BYTES = 64 * 1024 * 1024

M1A_ROLE_ORDER = (
    "OBSERVER_OPEN_BINDING",
    "SIGNED_BATCH_REQUEST",
    "SIGNED_BATCH_OUTCOME",
    "SIGNED_OBSERVATION_BATCH",
    "SIGNED_BATCH_JOURNAL_ENTRY",
    "SIGNED_BATCH_JOURNAL_CLOSURE",
    "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",
)
M1A_COMPLETE_ROLE_ORDER = M1A_ROLE_ORDER[:-1]
M1A_VERIFICATION_ROLE = M1A_ROLE_ORDER[-1]
_M1A_ROLES = frozenset(M1A_ROLE_ORDER)
_M1A_COMPLETE_ROLES = frozenset(M1A_COMPLETE_ROLE_ORDER)
_M1A_ROLE_SEMANTIC_ID_FIELD = MappingProxyType(
    {
        "OBSERVER_OPEN_BINDING": "binding_id",
        "SIGNED_BATCH_REQUEST": "request_id",
        # The portable table deliberately gives each distinct aggregate raw
        # document its own role-bound semantic ID.  `outcome_id` excludes
        # count/reward_sum and therefore is not a unique record identity.
        "SIGNED_BATCH_OUTCOME": None,
        "SIGNED_OBSERVATION_BATCH": "batch_id",
        "SIGNED_BATCH_JOURNAL_ENTRY": "entry_id",
        "SIGNED_BATCH_JOURNAL_CLOSURE": "closure_id",
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": "verification_id",
    }
)

DOMAIN_TAGS = MappingProxyType(
    {
        "typed_graph": (
            "acfqp:v075-portable-signed-batch-typed-graph:v2"
        ),
        "dependency_resolution_dag": (
            "acfqp:v075-portable-m1a-dependency-resolution-dag:v2"
        ),
        "record_attestation": (
            "acfqp:v075-portable-signed-batch-record-attestation:v2"
        ),
        "aggregate": (
            "acfqp:v075-portable-signed-batch-graph-authority:v2"
        ),
    }
)


class V075PortableSignedBatchGraphV2InvariantViolation(ValueError):
    """One raw authority, typed edge, recurrence, or signature is invalid."""


class V075PortableSignedBatchGraphProductionV2NotReady(RuntimeError):
    """M1A cannot authorize production while private replay is unresolved."""


class V075PortableM1ARoleReplayStatusV2(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE_DEPENDENCY_CLOSURE = "INCOMPLETE_DEPENDENCY_CLOSURE"
    UNRESOLVED_PRIVATE_REPLAY_CLAIM = (
        "UNRESOLVED_PRIVATE_REPLAY_CLAIM"
    )


def _fail(message: str) -> NoReturn:
    raise V075PortableSignedBatchGraphV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableSignedBatchGraphV2InvariantViolation(
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
        raise V075PortableSignedBatchGraphV2InvariantViolation(
            str(error)
        ) from error


def _raw(value: Any) -> bytes:
    return canonical_json_bytes(value.to_document())


def _producer_semantic_artifact_id(*, role: str, raw: bytes) -> str:
    field_name = _M1A_ROLE_SEMANTIC_ID_FIELD[role]
    if field_name is None:
        return portable._derived_artifact_id(role=role, raw=raw)
    document = _strict_document(raw, label=f"M1A {role} producer")
    return _cid(document.get(field_name), f"M1A {role} producer semantic ID")


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V075PortableSignedBatchGraphV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


def _sole_record(
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    role: str,
) -> portable.V075PortableEvidenceArtifactRecordV2:
    matches = tuple(item for item in records if item.role == role)
    if len(matches) != 1:
        _fail(f"portable bundle must contain exactly one {role} record")
    return matches[0]


def _used_stream_ids_from_closure_raw(raw: bytes) -> tuple[str, ...]:
    document = _strict_document(raw, label="M1A signed-batch closure")
    entries = document.get("entries")
    if type(entries) is not list or not entries:
        _fail("M1A closure contains no signed-batch entries")
    try:
        stream_ids = {
            _cid(
                item["batch"]["request"]["stream_id"],
                "M1A closure request stream",
            )
            for item in entries
        }
    except (KeyError, TypeError) as error:
        raise V075PortableSignedBatchGraphV2InvariantViolation(
            "M1A closure entry/request structure is malformed"
        ) from error
    if not stream_ids:
        _fail("M1A closure uses no prereplayed transition stream")
    return tuple(sorted(stream_ids))


def _unique_by_raw(values: tuple[Any, ...]) -> tuple[Any, ...]:
    by_raw: dict[bytes, Any] = {}
    for value in values:
        raw = _raw(value)
        prior = by_raw.setdefault(raw, value)
        if type(prior) is not type(value):
            _fail("M1A nested canonical bytes cross producer types")
    return tuple(by_raw[key] for key in sorted(by_raw))


def _closure_views(
    closure: observer.V075ObserverBatchJournalClosureV2,
) -> dict[str, tuple[Any, ...]]:
    entries = closure.entries
    batches = tuple(item.batch for item in entries)
    requests = tuple(item.request for item in batches)
    outcome_occurrences = tuple(
        outcome for batch in batches for outcome in batch.outcomes
    )
    return {
        "OBSERVER_OPEN_BINDING": (closure.authority_binding,),
        "SIGNED_BATCH_REQUEST": _unique_by_raw(requests),
        "SIGNED_BATCH_OUTCOME": _unique_by_raw(outcome_occurrences),
        "SIGNED_OBSERVATION_BATCH": _unique_by_raw(batches),
        "SIGNED_BATCH_JOURNAL_ENTRY": _unique_by_raw(entries),
        "SIGNED_BATCH_JOURNAL_CLOSURE": (closure,),
    }


def _verification_projection(
    *,
    record: portable.V075PortableEvidenceArtifactRecordV2,
    closure: observer.V075ObserverBatchJournalClosureV2,
) -> dict[str, Any]:
    """Check all public fields without endorsing the private replay claim."""

    document = _strict_document(
        record.canonical_artifact_bytes,
        label="M1A closure verification",
    )
    requests = tuple(entry.batch.request for entry in closure.entries)
    binding = closure.authority_binding
    expected = {
        "schema": (
            "acfqp.v075_observer_batch_journal_closure_verification.v2"
        ),
        "schema_version": observer.SCHEMA_VERSION,
        "closure_id": closure.closure_id,
        "occurrence_id": closure.occurrence_id,
        "batch_ids": [entry.batch.batch_id for entry in closure.entries],
        "observer_open_binding_id": binding.binding_id,
        "observer_open_authorization_id": binding.authorization_id,
        "private_reveal_attestation_id": (
            binding.private_reveal_attestation_id
        ),
        "remote_main_anchor_id": binding.remote_main_anchor_id,
        "target_tape_namespace_id": (
            binding.namespace.target_tape_namespace_id
        ),
        "verification_result": "EXACT_BATCH_NATIVE_V2_REPLAY_VERIFIED",
        "replayed_batch_count": len(closure.entries),
        "replayed_draw_count": sum(
            item.accepted_draw_count for item in requests
        ),
        "replayed_stream_count": len(
            {item.stream_identity.stream_id for item in requests}
        ),
        "per_draw_records_replayed": 0,
        "authority_version": "V2",
        "namespace_version": "V2",
        "legacy_v1_projection_used": False,
        "private_material_serialized": False,
        "verification_id": record.semantic_artifact_id,
    }
    if document != expected:
        _fail(
            "M1A closure-verification public projection differs from "
            "the reconstructed journal"
        )
    return document


@dataclass(frozen=True, slots=True)
class _M1ARecordBindingV2:
    record_id: str
    record_index: int
    role: str
    semantic_artifact_id: str
    dependency_record_ids: tuple[str, ...]
    canonical_artifact_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        self._assert_current()

    def _assert_current(self) -> None:
        _cid(self.record_id, "M1A graph record")
        _cid(self.semantic_artifact_id, "M1A graph semantic artifact")
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _M1A_ROLES
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
            or type(self.canonical_artifact_bytes) is not bytes
            or not self.canonical_artifact_bytes
        ):
            _fail("M1A graph record binding is malformed")
        for dependency_id in self.dependency_record_ids:
            _cid(dependency_id, "M1A graph record dependency")
        _strict_document(
            self.canonical_artifact_bytes,
            label=f"M1A {self.role} record",
        )
        if (
            _producer_semantic_artifact_id(
                role=self.role,
                raw=self.canonical_artifact_bytes,
            )
            != self.semantic_artifact_id
        ):
            _fail(
                f"M1A {self.role} semantic ID differs from producer bytes"
            )

    def commitment_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "semantic_artifact_id": self.semantic_artifact_id,
            "dependency_record_ids": list(self.dependency_record_ids),
            "canonical_artifact_sha256": hashlib.sha256(
                self.canonical_artifact_bytes
            ).hexdigest(),
            "canonical_artifact_byte_count": len(
                self.canonical_artifact_bytes
            ),
        }


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableSignedBatchTypedGraphV2:
    """Issuer-backed, in-memory-only view of the exact M0+B1+M1A graph."""

    _issuer: InitVar[object]
    bundle_id: str
    public_context_closure_id: str
    occurrence_id: str
    m0_result: m0.V075PortablePublicSemanticReplayResultV2 = field(
        repr=False
    )
    b1_result: b1.V075PortableObserverOpenBindingReplayV2 = field(
        repr=False
    )
    used_streams: tuple[graph.V075TransitionStreamIdentityV1, ...] = field(
        repr=False
    )
    closure: observer.V075ObserverBatchJournalClosureV2 = field(
        repr=False
    )
    record_bindings: tuple[_M1ARecordBindingV2, ...] = field(repr=False)
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.bundle_id, "M1A typed graph bundle"),
            (
                self.public_context_closure_id,
                "M1A typed graph public context",
            ),
            (self.occurrence_id, "M1A typed graph occurrence"),
        ):
            _cid(value, label)
        if (
            _issuer is not _TYPED_GRAPH_ISSUER
            or type(self.m0_result)
            is not m0.V075PortablePublicSemanticReplayResultV2
            or type(self.b1_result)
            is not b1.V075PortableObserverOpenBindingReplayV2
            or type(self.used_streams) is not tuple
            or not self.used_streams
            or any(
                type(item) is not graph.V075TransitionStreamIdentityV1
                for item in self.used_streams
            )
            or tuple(item.stream_id for item in self.used_streams)
            != tuple(
                sorted({item.stream_id for item in self.used_streams})
            )
            or type(self.closure)
            is not observer.V075ObserverBatchJournalClosureV2
            or type(self.record_bindings) is not tuple
            or not self.record_bindings
            or any(
                type(item) is not _M1ARecordBindingV2
                for item in self.record_bindings
            )
            or tuple(item.record_index for item in self.record_bindings)
            != tuple(
                sorted(item.record_index for item in self.record_bindings)
            )
            or len({item.record_id for item in self.record_bindings})
            != len(self.record_bindings)
        ):
            _fail("M1A typed graph is caller-minted or malformed")
        for item in self.record_bindings:
            item._assert_current()
        self._validate_exact_graph()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._identity_payload()),
        )

    def _validate_exact_graph(self) -> None:
        m0_graph = self.m0_result.typed_graph
        binding = self.b1_result.observer_open_binding
        if (
            self.m0_result.bundle_id != self.bundle_id
            or self.m0_result.public_context_closure_id
            != self.public_context_closure_id
            or self.m0_result.occurrence_id != self.occurrence_id
            or self.b1_result.public_context_closure_id
            != self.public_context_closure_id
            or binding.namespace != m0_graph.namespace
            or self.closure.occurrence_id != self.occurrence_id
            or self.closure.authority_binding != binding
        ):
            _fail("M1A typed graph crossed bundle/context identities")
        stream_ids = tuple(item.stream_id for item in self.used_streams)
        if any(
            m0_graph.streams_by_id.get(item.stream_id) != item
            for item in self.used_streams
        ):
            _fail("M1A typed graph contains a non-M0 stream")
        try:
            replayed = observer.load_observer_batch_journal_closure_bytes_v2(
                raw=self.closure.canonical_bytes,
                authority_binding=binding,
                known_stream_identities=self.used_streams,
            )
        except Exception as error:
            raise V075PortableSignedBatchGraphV2InvariantViolation(
                "M1A typed closure failed fresh producer replay"
            ) from error
        if (
            replayed.canonical_bytes != self.closure.canonical_bytes
            or stream_ids
            != tuple(
                sorted(
                    {
                        entry.batch.request.stream_identity.stream_id
                        for entry in replayed.entries
                    }
                )
            )
        ):
            _fail("M1A typed closure or exact used-stream set is stale")

        views = _closure_views(replayed)
        bound_by_role: dict[str, dict[bytes, _M1ARecordBindingV2]] = {}
        for item in self.record_bindings:
            item._assert_current()
            role_bindings = bound_by_role.setdefault(item.role, {})
            if item.canonical_artifact_bytes in role_bindings:
                _fail("M1A typed graph maps two records to the same bytes")
            role_bindings[item.canonical_artifact_bytes] = item
        if set(bound_by_role) != _M1A_ROLES:
            _fail("M1A typed graph omits one registered M1A role")
        for role, typed_values in views.items():
            typed_by_raw = {_raw(value): value for value in typed_values}
            if set(typed_by_raw) != set(bound_by_role[role]):
                _fail(
                    f"M1A {role} records are not one-to-one with typed views"
                )
            for raw in typed_by_raw:
                if (
                    bound_by_role[role][raw].semantic_artifact_id
                    != _producer_semantic_artifact_id(
                        role=role,
                        raw=raw,
                    )
                ):
                    _fail(
                        f"M1A {role} record differs from producer semantic ID"
                    )
        verification_bindings = bound_by_role[M1A_VERIFICATION_ROLE]
        if len(verification_bindings) != 1:
            _fail("M1A requires one closure-verification raw record")
        verification = next(iter(verification_bindings.values()))
        _verification_projection(
            record=_record_proxy(verification),
            closure=replayed,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_signed_batch_typed_graph.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "public_context_closure_id": self.public_context_closure_id,
            "occurrence_id": self.occurrence_id,
            "m0_result_id": self.m0_result.result_id,
            "m0_typed_graph_id": self.m0_result.typed_graph.graph_id,
            "b1_result_id": self.b1_result.result_id,
            "observer_open_binding_id": (
                self.b1_result.observer_open_binding.binding_id
            ),
            "used_stream_ids": [
                item.stream_id for item in self.used_streams
            ],
            "signed_batch_journal_closure_id": self.closure.closure_id,
            "role_record_ids": {
                role: [
                    item.record_id
                    for item in self.record_bindings
                    if item.role == role
                ]
                for role in M1A_ROLE_ORDER
            },
            "ordered_record_commitments": [
                item.commitment_document() for item in self.record_bindings
            ],
            "outcome_record_key": "NESTED_CANONICAL_BYTES",
            "outcome_id_is_unique_record_key": False,
            "in_memory_only": True,
            "issuer_gate_semantics": "CONSTRUCTION_API_DISCIPLINE_ONLY",
            "python_process_security_boundary": False,
            "typed_objects_serialized": False,
            "private_material_serialized": False,
        }

    def _assert_current(self) -> None:
        self._validate_exact_graph()
        if self._graph_id != _hash("typed_graph", self._identity_payload()):
            _fail("M1A typed graph content identity is stale")

    @property
    def graph_id(self) -> str:
        self._assert_current()
        return self._graph_id

    @property
    def entries(
        self,
    ) -> tuple[observer.V075ObserverBatchJournalEntryV2, ...]:
        self._assert_current()
        return self.closure.entries

    @property
    def batches(
        self,
    ) -> tuple[observer.V075SignedObservationBatchV2, ...]:
        return tuple(item.batch for item in self.entries)

    @property
    def requests(
        self,
    ) -> tuple[observer.V075BatchObservationRequestV2, ...]:
        return tuple(item.request for item in self.batches)

    @property
    def outcome_occurrences(
        self,
    ) -> tuple[observer.V075BatchOutcomeAggregateV2, ...]:
        return tuple(
            outcome for batch in self.batches for outcome in batch.outcomes
        )

    @property
    def unique_outcomes(
        self,
    ) -> tuple[observer.V075BatchOutcomeAggregateV2, ...]:
        return _unique_by_raw(self.outcome_occurrences)

    @property
    def outcomes_by_batch_id(
        self,
    ) -> Mapping[str, tuple[observer.V075BatchOutcomeAggregateV2, ...]]:
        return MappingProxyType(
            {item.batch_id: item.outcomes for item in self.batches}
        )

    @property
    def outcome_records_by_outcome_id(
        self,
    ) -> Mapping[str, tuple[str, ...]]:
        """Diagnostic multimap; outcome_id is deliberately not a key."""

        record_by_raw = {
            item.canonical_artifact_bytes: item.record_id
            for item in self.record_bindings
            if item.role == "SIGNED_BATCH_OUTCOME"
        }
        grouped: dict[str, set[str]] = {}
        for item in self.unique_outcomes:
            grouped.setdefault(item.outcome_id, set()).add(
                record_by_raw[_raw(item)]
            )
        return MappingProxyType(
            {
                outcome_id: tuple(sorted(record_ids))
                for outcome_id, record_ids in sorted(grouped.items())
            }
        )

    @property
    def verification_projection(self) -> Mapping[str, Any]:
        self._assert_current()
        item = next(
            value
            for value in self.record_bindings
            if value.role == M1A_VERIFICATION_ROLE
        )
        document = _verification_projection(
            record=_record_proxy(item),
            closure=self.closure,
        )
        return MappingProxyType(document)

    def __reduce__(self) -> NoReturn:
        raise TypeError("M1A typed graph is in-memory-only")


class _RecordProxy:
    """Internal shape adapter used only for verification projection."""

    __slots__ = (
        "canonical_artifact_bytes",
        "semantic_artifact_id",
    )

    def __init__(self, binding: _M1ARecordBindingV2) -> None:
        self.canonical_artifact_bytes = binding.canonical_artifact_bytes
        self.semantic_artifact_id = binding.semantic_artifact_id


def _record_proxy(binding: _M1ARecordBindingV2) -> Any:
    return _RecordProxy(binding)


class _M1AResolverKindV2(str, Enum):
    M0_PUBLIC_TYPED_RECONSTRUCTION = "M0_PUBLIC_TYPED_RECONSTRUCTION"
    M1A_PUBLIC_PRODUCER_RECONSTRUCTION = (
        "M1A_PUBLIC_PRODUCER_RECONSTRUCTION"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = "NO_REGISTERED_SEMANTIC_AUTHORITY"


@dataclass(frozen=True, slots=True)
class _M1ADependencyResolutionNodeV2:
    record_id: str
    record_index: int
    role: str
    direct_dependency_record_ids: tuple[str, ...]
    resolver_kind: _M1AResolverKindV2
    jointly_resolved: bool

    def _assert_current(self) -> None:
        _cid(self.record_id, "M1A dependency DAG record")
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or type(self.role) is not str
            or not self.role
            or type(self.direct_dependency_record_ids) is not tuple
            or tuple(sorted(set(self.direct_dependency_record_ids)))
            != self.direct_dependency_record_ids
            or type(self.resolver_kind) is not _M1AResolverKindV2
            or type(self.jointly_resolved) is not bool
        ):
            _fail("M1A compact dependency node is malformed")
        for dependency_id in self.direct_dependency_record_ids:
            _cid(dependency_id, "M1A dependency DAG edge")

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "direct_dependency_record_ids": list(
                self.direct_dependency_record_ids
            ),
            "resolver_kind": self.resolver_kind.value,
            "jointly_resolved": self.jointly_resolved,
        }


_DEPENDENCY_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class _M1ADependencyResolutionDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    m0_result_id: str
    typed_graph_id: str
    nodes: tuple[_M1ADependencyResolutionNodeV2, ...] = field(repr=False)
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DEPENDENCY_DAG_ISSUER:
            _fail("M1A compact dependency DAG is caller-minted")
        self._validate_structure()
        object.__setattr__(
            self,
            "_dag_id",
            _hash("dependency_resolution_dag", self._identity_payload()),
        )

    def _validate_structure(self) -> None:
        for value, label in (
            (self.bundle_id, "M1A dependency DAG bundle"),
            (self.m0_result_id, "M1A dependency DAG M0 result"),
            (self.typed_graph_id, "M1A dependency DAG typed graph"),
        ):
            _cid(value, label)
        if (
            type(self.nodes) is not tuple
            or not self.nodes
            or any(
                type(item) is not _M1ADependencyResolutionNodeV2
                for item in self.nodes
            )
            or tuple(item.record_index for item in self.nodes)
            != tuple(range(len(self.nodes)))
            or len({item.record_id for item in self.nodes}) != len(self.nodes)
        ):
            _fail("M1A compact dependency DAG is malformed")
        resolved_by_id: dict[str, bool] = {}
        for item in self.nodes:
            item._assert_current()
            if any(
                dependency_id not in resolved_by_id
                for dependency_id in item.direct_dependency_record_ids
            ):
                _fail("M1A compact dependency DAG is not topological")
            expected = (
                item.resolver_kind
                is not _M1AResolverKindV2.NO_REGISTERED_SEMANTIC_AUTHORITY
                and all(
                    resolved_by_id[dependency_id]
                    for dependency_id in item.direct_dependency_record_ids
                )
            )
            if item.jointly_resolved is not expected:
                _fail("M1A compact dependency resolution is inconsistent")
            resolved_by_id[item.record_id] = item.jointly_resolved

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_m1a_dependency_resolution_dag.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m0_result_id": self.m0_result_id,
            "m1a_typed_graph_id": self.typed_graph_id,
            "nodes": [item.to_document() for item in self.nodes],
            "node_count": len(self.nodes),
            "edge_count": sum(
                len(item.direct_dependency_record_ids) for item in self.nodes
            ),
            "proof_shape": "ITERATIVE_TOPOLOGICAL_DIRECT_EDGE_DAG",
            "transitive_closure_materialized": False,
        }

    def _assert_current(self) -> None:
        self._validate_structure()
        if self._dag_id != _hash(
            "dependency_resolution_dag",
            self._identity_payload(),
        ):
            _fail("M1A compact dependency DAG identity is stale")

    @property
    def dag_id(self) -> str:
        self._assert_current()
        return self._dag_id

    @property
    def nodes_by_id(self) -> Mapping[str, _M1ADependencyResolutionNodeV2]:
        self._assert_current()
        return MappingProxyType({item.record_id: item for item in self.nodes})

    def summary_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            "dependency_resolution_dag_id": self._dag_id,
            "dependency_resolution_node_count": len(self.nodes),
            "dependency_resolution_edge_count": sum(
                len(item.direct_dependency_record_ids) for item in self.nodes
            ),
            "dependency_proof_shape": (
                "ITERATIVE_TOPOLOGICAL_DIRECT_EDGE_DAG"
            ),
            "transitive_closure_materialized": False,
        }


def _iterative_dependency_resolution_nodes(
    *,
    records: tuple[Any, ...],
    m0_authority_record_ids: frozenset[str],
    m1a_authority_record_ids: frozenset[str],
) -> tuple[_M1ADependencyResolutionNodeV2, ...]:
    """Resolve one topological DAG without recursion or closure expansion."""

    if type(records) is not tuple or not records:
        _fail("M1A dependency resolution requires one nonempty record tuple")
    nodes: list[_M1ADependencyResolutionNodeV2] = []
    resolved_by_id: dict[str, bool] = {}
    for expected_index, record in enumerate(records):
        try:
            record_id = record.record_id
            record_index = record.index
            role = record.role
            dependencies = tuple(record.dependency_record_ids)
        except (AttributeError, TypeError) as error:
            raise V075PortableSignedBatchGraphV2InvariantViolation(
                "M1A dependency resolution record is malformed"
            ) from error
        if (
            record_index != expected_index
            or record_id in resolved_by_id
            or tuple(sorted(set(dependencies))) != dependencies
            or any(value not in resolved_by_id for value in dependencies)
        ):
            _fail("M1A dependency records are duplicated or non-topological")
        if record_id in m0_authority_record_ids:
            resolver_kind = (
                _M1AResolverKindV2.M0_PUBLIC_TYPED_RECONSTRUCTION
            )
        elif record_id in m1a_authority_record_ids:
            resolver_kind = (
                _M1AResolverKindV2.M1A_PUBLIC_PRODUCER_RECONSTRUCTION
            )
        else:
            resolver_kind = (
                _M1AResolverKindV2.NO_REGISTERED_SEMANTIC_AUTHORITY
            )
        jointly_resolved = (
            resolver_kind
            is not _M1AResolverKindV2.NO_REGISTERED_SEMANTIC_AUTHORITY
            and all(resolved_by_id[value] for value in dependencies)
        )
        node = _M1ADependencyResolutionNodeV2(
            record_id,
            record_index,
            role,
            dependencies,
            resolver_kind,
            jointly_resolved,
        )
        node._assert_current()
        nodes.append(node)
        resolved_by_id[record_id] = jointly_resolved
    return tuple(nodes)


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableM1ARecordSemanticAttestationV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    dependency_resolution_dag_id: str
    record_id: str
    record_index: int
    role: str
    semantic_artifact_id: str
    canonical_artifact_sha256: str
    canonical_artifact_byte_count: int
    declared_direct_dependency_record_ids: tuple[str, ...]
    joint_authority_resolved_direct_dependency_record_ids: tuple[str, ...]
    unresolved_dependency_frontier_record_ids: tuple[str, ...]
    unresolved_dependency_roles: tuple[str, ...]
    status: V075PortableM1ARoleReplayStatusV2
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("M1A record attestation is caller-minted")
        self._validate_structure()
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("record_attestation", self._payload_unchecked()),
        )

    def _validate_structure(self) -> None:
        for value, label in (
            (self.bundle_id, "M1A attestation bundle"),
            (self.typed_graph_id, "M1A typed graph"),
            (
                self.dependency_resolution_dag_id,
                "M1A dependency resolution DAG",
            ),
            (self.record_id, "M1A record"),
            (self.semantic_artifact_id, "M1A semantic artifact"),
            (self.canonical_artifact_sha256, "M1A artifact bytes"),
        ):
            _cid(value, label)
        sequences = (
            self.declared_direct_dependency_record_ids,
            self.joint_authority_resolved_direct_dependency_record_ids,
            self.unresolved_dependency_frontier_record_ids,
        )
        unresolved = set(self.unresolved_dependency_frontier_record_ids)
        expected_status = (
            V075PortableM1ARoleReplayStatusV2
            .UNRESOLVED_PRIVATE_REPLAY_CLAIM
            if self.role == M1A_VERIFICATION_ROLE
            else V075PortableM1ARoleReplayStatusV2
            .INCOMPLETE_DEPENDENCY_CLOSURE
            if unresolved
            else V075PortableM1ARoleReplayStatusV2.COMPLETE
        )
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _M1A_ROLES
            or type(self.canonical_artifact_byte_count) is not int
            or self.canonical_artifact_byte_count <= 0
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in sequences
            )
            or any(
                _cid(value, "M1A dependency record") != value
                for values in sequences
                for value in values
            )
            or tuple(sorted(set(self.unresolved_dependency_roles)))
            != self.unresolved_dependency_roles
            or set(
                self.joint_authority_resolved_direct_dependency_record_ids
            )
            | unresolved
            != set(self.declared_direct_dependency_record_ids)
            or set(
                self.joint_authority_resolved_direct_dependency_record_ids
            )
            & unresolved
            or self.status is not expected_status
        ):
            _fail("M1A record attestation is malformed or overclaims")

    def _payload_unchecked(self) -> dict[str, Any]:
        declared_direct_dependency_frontier_resolved = not (
            self.unresolved_dependency_frontier_record_ids
        )
        return {
            "schema": (
                "acfqp.v075_portable_m1a_record_semantic_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m1a_typed_graph_id": self.typed_graph_id,
            "dependency_resolution_dag_id": (
                self.dependency_resolution_dag_id
            ),
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "semantic_artifact_id": self.semantic_artifact_id,
            "canonical_artifact_sha256": (
                self.canonical_artifact_sha256
            ),
            "canonical_artifact_byte_count": (
                self.canonical_artifact_byte_count
            ),
            "declared_direct_dependency_record_ids": list(
                self.declared_direct_dependency_record_ids
            ),
            "joint_authority_resolved_direct_dependency_record_ids": list(
                self.joint_authority_resolved_direct_dependency_record_ids
            ),
            "unresolved_dependency_frontier_record_ids": list(
                self.unresolved_dependency_frontier_record_ids
            ),
            "unresolved_dependency_roles": list(
                self.unresolved_dependency_roles
            ),
            "declared_direct_dependency_frontier_resolved": (
                declared_direct_dependency_frontier_resolved
            ),
            "dependency_proof_shape": (
                "ITERATIVE_TOPOLOGICAL_DIRECT_EDGE_DAG"
            ),
            "transitive_closure_materialized": False,
            "semantic_replay_status": self.status.value,
            "producer_typed_object_reconstructed": (
                self.role != M1A_VERIFICATION_ROLE
            ),
            "public_structural_projection_replayed": True,
            "private_native_replay_claim_verified": False,
            "canonical_bytes_equal_reconstruction": (
                self.role != M1A_VERIFICATION_ROLE
            ),
            "outcome_mapping_key": (
                "NESTED_CANONICAL_BYTES"
                if self.role == "SIGNED_BATCH_OUTCOME"
                else "ROLE_SEMANTIC_ID"
            ),
            "outcome_id_used_as_unique_record_key": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_material_serialized": False,
        }

    def _assert_current(self) -> None:
        self._validate_structure()
        if self._attestation_id != _hash(
            "record_attestation",
            self._payload_unchecked(),
        ):
            _fail("M1A record attestation content identity is stale")

    @property
    def attestation_id(self) -> str:
        self._assert_current()
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            **self._payload_unchecked(),
            "attestation_id": self._attestation_id,
        }


def _record_bindings(
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
) -> tuple[_M1ARecordBindingV2, ...]:
    return tuple(
        _M1ARecordBindingV2(
            item.record_id,
            item.index,
            item.role,
            item.semantic_artifact_id,
            item.dependency_record_ids,
            item.canonical_artifact_bytes,
        )
        for item in records
        if item.role in _M1A_ROLES
    )


def _resolved_m0_record_ids(
    *,
    bundle: portable.V075PortableOccurrenceEvidenceBundleV2,
    m0_result: m0.V075PortablePublicSemanticReplayResultV2,
) -> set[str]:
    result = {item.record_id for item in m0_result.attestations}
    occurrence_records = tuple(
        item for item in bundle.records if item.role == "OCCURRENCE_IDENTITY"
    )
    if (
        len(occurrence_records) != 1
        or occurrence_records[0].semantic_artifact_id
        != m0_result.typed_graph.occurrence.occurrence_id
        or occurrence_records[0].canonical_artifact_bytes
        != _raw(m0_result.typed_graph.occurrence)
    ):
        _fail("M1A cannot bind the exact M0 occurrence record")
    result.add(occurrence_records[0].record_id)
    return result


def _build_dependency_resolution_dag(
    *,
    bundle: portable.V075PortableOccurrenceEvidenceBundleV2,
    m0_result: m0.V075PortablePublicSemanticReplayResultV2,
    typed_graph: V075PortableSignedBatchTypedGraphV2,
) -> _M1ADependencyResolutionDAGV2:
    m0_authority_record_ids = frozenset(
        _resolved_m0_record_ids(bundle=bundle, m0_result=m0_result)
    )
    m1a_authority_record_ids = frozenset(
        item.record_id
        for item in bundle.records
        if item.role in _M1A_COMPLETE_ROLES
    )
    nodes = _iterative_dependency_resolution_nodes(
        records=bundle.records,
        m0_authority_record_ids=m0_authority_record_ids,
        m1a_authority_record_ids=m1a_authority_record_ids,
    )
    return _M1ADependencyResolutionDAGV2(
        _DEPENDENCY_DAG_ISSUER,
        bundle.bundle_id,
        m0_result.result_id,
        typed_graph.graph_id,
        nodes,
    )


def _build_attestations(
    *,
    bundle: portable.V075PortableOccurrenceEvidenceBundleV2,
    typed_graph: V075PortableSignedBatchTypedGraphV2,
    dependency_resolution_dag: _M1ADependencyResolutionDAGV2,
) -> tuple[V075PortableM1ARecordSemanticAttestationV2, ...]:
    by_id = {item.record_id: item for item in bundle.records}
    typed_graph._assert_current()
    dependency_resolution_dag._assert_current()
    typed_graph_id = typed_graph._graph_id
    dependency_resolution_dag_id = dependency_resolution_dag._dag_id
    resolution_by_id = dependency_resolution_dag.nodes_by_id
    result = []
    for record in bundle.records:
        if record.role not in _M1A_ROLES:
            continue
        direct = tuple(sorted(record.dependency_record_ids))
        resolved_direct = tuple(
            value
            for value in direct
            if resolution_by_id[value].jointly_resolved
        )
        unresolved_frontier = tuple(
            value
            for value in direct
            if not resolution_by_id[value].jointly_resolved
        )
        unresolved_roles = tuple(
            sorted({by_id[value].role for value in unresolved_frontier})
        )
        if record.role == M1A_VERIFICATION_ROLE:
            status = (
                V075PortableM1ARoleReplayStatusV2
                .UNRESOLVED_PRIVATE_REPLAY_CLAIM
            )
        elif unresolved_frontier:
            status = (
                V075PortableM1ARoleReplayStatusV2
                .INCOMPLETE_DEPENDENCY_CLOSURE
            )
        else:
            status = V075PortableM1ARoleReplayStatusV2.COMPLETE
        result.append(
            V075PortableM1ARecordSemanticAttestationV2(
                _ATTESTATION_ISSUER,
                bundle.bundle_id,
                typed_graph_id,
                dependency_resolution_dag_id,
                record.record_id,
                record.index,
                record.role,
                record.semantic_artifact_id,
                hashlib.sha256(
                    record.canonical_artifact_bytes
                ).hexdigest(),
                len(record.canonical_artifact_bytes),
                direct,
                resolved_direct,
                unresolved_frontier,
                unresolved_roles,
                status,
            )
        )
    return tuple(result)


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableSignedBatchGraphReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075PortableSignedBatchTypedGraphV2 = field(repr=False)
    dependency_resolution_dag: _M1ADependencyResolutionDAGV2 = field(
        repr=False
    )
    attestations: tuple[
        V075PortableM1ARecordSemanticAttestationV2,
        ...,
    ]
    m0_unresolved_dependency_record_ids_before_join: tuple[str, ...]
    m0_dependency_record_ids_discharged: tuple[str, ...]
    m0_unresolved_dependency_record_ids_after_join: tuple[str, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("M1A aggregate is caller-minted")
        self._validate_current_content()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload_unchecked()),
        )

    def _validate_current_content(self) -> None:
        for value, label in (
            (self.bundle_id, "M1A result bundle"),
            (self.occurrence_id, "M1A result occurrence"),
            (
                self.public_context_closure_id,
                "M1A result public context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph)
            is not V075PortableSignedBatchTypedGraphV2
            or type(self.dependency_resolution_dag)
            is not _M1ADependencyResolutionDAGV2
        ):
            _fail("M1A aggregate carries an untyped graph or dependency DAG")
        self.typed_graph._assert_current()
        self.dependency_resolution_dag._assert_current()
        typed_graph_id = self.typed_graph._graph_id
        dependency_dag_id = self.dependency_resolution_dag._dag_id
        sequences = (
            self.m0_unresolved_dependency_record_ids_before_join,
            self.m0_dependency_record_ids_discharged,
            self.m0_unresolved_dependency_record_ids_after_join,
        )
        if (
            self.typed_graph.bundle_id != self.bundle_id
            or self.typed_graph.occurrence_id != self.occurrence_id
            or self.typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or type(self.attestations) is not tuple
            or not self.attestations
            or any(
                type(item)
                is not V075PortableM1ARecordSemanticAttestationV2
                for item in self.attestations
            )
            or tuple(item.record_index for item in self.attestations)
            != tuple(
                sorted(item.record_index for item in self.attestations)
            )
            or len({item.record_id for item in self.attestations})
            != len(self.attestations)
            or {item.role for item in self.attestations} != _M1A_ROLES
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in sequences
            )
            or set(self.m0_dependency_record_ids_discharged)
            | set(self.m0_unresolved_dependency_record_ids_after_join)
            != set(self.m0_unresolved_dependency_record_ids_before_join)
            or set(self.m0_dependency_record_ids_discharged)
            & set(self.m0_unresolved_dependency_record_ids_after_join)
            or any(
                item.bundle_id != self.bundle_id
                or item.typed_graph_id != typed_graph_id
                or item.dependency_resolution_dag_id
                != dependency_dag_id
                for item in self.attestations
            )
        ):
            _fail("M1A aggregate is incomplete, stale, or overclaims")
        if (
            self.dependency_resolution_dag.bundle_id != self.bundle_id
            or self.dependency_resolution_dag.m0_result_id
            != self.typed_graph.m0_result.result_id
            or self.dependency_resolution_dag.typed_graph_id
            != typed_graph_id
        ):
            _fail("M1A dependency DAG was transplanted")
        self._assert_attestation_binding()
        self._assert_join_fields()

    def _assert_attestation_binding(self) -> None:
        bindings = {
            item.record_id: item for item in self.typed_graph.record_bindings
        }
        attestations = {item.record_id: item for item in self.attestations}
        if set(bindings) != set(attestations):
            _fail("M1A attestations differ from exact graph records")
        resolution_by_id = self.dependency_resolution_dag.nodes_by_id
        for record_id, binding in bindings.items():
            binding._assert_current()
            item = attestations[record_id]
            item._assert_current()
            node = resolution_by_id.get(record_id)
            if node is None:
                _fail("M1A record is absent from dependency resolution DAG")
            resolved_direct = tuple(
                value
                for value in binding.dependency_record_ids
                if resolution_by_id[value].jointly_resolved
            )
            unresolved_frontier = tuple(
                value
                for value in binding.dependency_record_ids
                if not resolution_by_id[value].jointly_resolved
            )
            unresolved_roles = tuple(
                sorted(
                    {
                        resolution_by_id[value].role
                        for value in unresolved_frontier
                    }
                )
            )
            if (
                item.record_index != binding.record_index
                or item.role != binding.role
                or item.semantic_artifact_id
                != binding.semantic_artifact_id
                or item.canonical_artifact_sha256
                != hashlib.sha256(
                    binding.canonical_artifact_bytes
                ).hexdigest()
                or item.canonical_artifact_byte_count
                != len(binding.canonical_artifact_bytes)
                or item.declared_direct_dependency_record_ids
                != binding.dependency_record_ids
                or (
                    item
                    .joint_authority_resolved_direct_dependency_record_ids
                    != resolved_direct
                )
                or item.unresolved_dependency_frontier_record_ids
                != unresolved_frontier
                or item.unresolved_dependency_roles != unresolved_roles
                or node.record_index != binding.record_index
                or node.role != binding.role
                or node.direct_dependency_record_ids
                != binding.dependency_record_ids
            ):
                _fail(
                    "M1A attestation differs from graph record or compact DAG"
                )

    def _assert_join_fields(self) -> None:
        m0_unresolved = tuple(
            sorted(
                {
                    dependency_id
                    for item in self.typed_graph.m0_result.attestations
                    for dependency_id in (
                        item.unresolved_dependency_record_ids
                    )
                }
            )
        )
        complete_m1a_record_ids = {
            item.record_id
            for item in self.attestations
            if item.status is V075PortableM1ARoleReplayStatusV2.COMPLETE
        }
        discharged = tuple(
            value
            for value in m0_unresolved
            if value in complete_m1a_record_ids
        )
        remaining = tuple(
            value
            for value in m0_unresolved
            if value not in complete_m1a_record_ids
        )
        if (
            self.m0_unresolved_dependency_record_ids_before_join
            != m0_unresolved
            or self.m0_dependency_record_ids_discharged != discharged
            or self.m0_unresolved_dependency_record_ids_after_join
            != remaining
        ):
            _fail("M1A joined M0 dependency discharge is stale")

    def _payload_unchecked(self) -> dict[str, Any]:
        role_statuses = {
            role: sorted(
                {
                    item.status.value
                    for item in self.attestations
                    if item.role == role
                }
            )
            for role in M1A_ROLE_ORDER
        }
        complete_public_roles = all(
            all(
                item.status is V075PortableM1ARoleReplayStatusV2.COMPLETE
                for item in self.attestations
                if item.role == role
            )
            for role in M1A_COMPLETE_ROLE_ORDER
        )
        unresolved = sorted(
            {
                dependency_id
                for item in self.attestations
                for dependency_id in (
                    item.unresolved_dependency_frontier_record_ids
                )
            }
        )
        unresolved_roles = sorted(
            {
                role
                for item in self.attestations
                for role in item.unresolved_dependency_roles
            }
        )
        return {
            "schema": (
                "acfqp.v075_portable_signed_batch_graph_replay.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": (
                self.public_context_closure_id
            ),
            "m0_result_id": self.typed_graph.m0_result.result_id,
            "m0_typed_graph_id": (
                self.typed_graph.m0_result.typed_graph.graph_id
            ),
            "b1_result_id": self.typed_graph.b1_result.result_id,
            "m1a_typed_graph_id": self.typed_graph.graph_id,
            **self.dependency_resolution_dag.summary_document(),
            "observer_open_binding_id": (
                self.typed_graph.b1_result.observer_open_binding.binding_id
            ),
            "signed_batch_journal_closure_id": (
                self.typed_graph.closure.closure_id
            ),
            "used_stream_ids": [
                item.stream_id for item in self.typed_graph.used_streams
            ],
            "m1a_role_order": list(M1A_ROLE_ORDER),
            "m1a_record_ids": [
                item.record_id for item in self.attestations
            ],
            "m1a_attestation_ids": [
                item.attestation_id for item in self.attestations
            ],
            "m1a_record_count": len(self.attestations),
            "role_replay_statuses": role_statuses,
            "six_public_role_semantics_complete": complete_public_roles,
            "signed_batch_journal_closure_verification_status": (
                V075PortableM1ARoleReplayStatusV2
                .UNRESOLVED_PRIVATE_REPLAY_CLAIM.value
            ),
            "closure_verification_public_projection_replayed": True,
            "closure_verification_private_native_replay_complete": False,
            "m0_unresolved_dependency_record_ids_before_join": list(
                self.m0_unresolved_dependency_record_ids_before_join
            ),
            "m0_dependency_record_ids_discharged": list(
                self.m0_dependency_record_ids_discharged
            ),
            "m0_unresolved_dependency_record_ids_after_join": list(
                self.m0_unresolved_dependency_record_ids_after_join
            ),
            "joined_m0_m1a_dependency_discharge_complete": (
                not self.m0_unresolved_dependency_record_ids_after_join
            ),
            "unresolved_dependency_frontier_record_ids": unresolved,
            "unresolved_dependency_roles": unresolved_roles,
            "all_m1a_declared_dependency_frontiers_resolved": (
                not unresolved
            ),
            "m1a_role_semantics_complete": False,
            "outcome_record_key": "NESTED_CANONICAL_BYTES",
            "outcome_id_is_unique_record_key": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "portable_semantic_registry_complete": False,
            "observer_opened": False,
            "private_input_channels_allowed": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_material_serialized": False,
        }

    @property
    def result_id(self) -> str:
        self._assert_current()
        return self._result_id

    @property
    def canonical_bytes(self) -> bytes:
        self._assert_current()
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_OUTPUT_BYTES:
            _fail("M1A replay result exceeds its output byte cap")
        return raw

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            **self._payload_unchecked(),
            "result_id": self._result_id,
        }

    def _assert_current(self) -> None:
        self._validate_current_content()
        if self._result_id != _hash(
            "aggregate",
            self._payload_unchecked(),
        ):
            _fail("M1A aggregate content identity is stale")


def replay_v075_portable_signed_batch_graph_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
) -> V075PortableSignedBatchGraphReplayV2:
    """Replay M1A from raw public authorities and no private inputs."""

    if (
        type(portable_bundle_bytes) is not bytes
        or type(public_context_closure_bytes) is not bytes
    ):
        _fail("M1A accepts canonical raw bytes only")
    try:
        bundle = (
            portable
            .verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
    except Exception as error:
        raise V075PortableSignedBatchGraphV2InvariantViolation(
            "M1A portable bundle failed raw replay"
        ) from error

    try:
        m0_result = m0.replay_v075_portable_public_semantics_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
        )
    except Exception as error:
        raise V075PortableSignedBatchGraphV2InvariantViolation(
            "M1A M0 authority failed raw replay"
        ) from error
    if (
        bundle.bundle_id != m0_result.bundle_id
        or bundle.occurrence_id != m0_result.occurrence_id
    ):
        _fail("M1A portable and M0 authorities differ")

    binding_record = _sole_record(bundle.records, "OBSERVER_OPEN_BINDING")
    try:
        b1_result = b1.replay_v075_portable_observer_open_binding_v2(
            repository_root=repository_root,
            public_context_closure_bytes=public_context_closure_bytes,
            observer_open_binding_bytes=(
                binding_record.canonical_artifact_bytes
            ),
        )
    except Exception as error:
        raise V075PortableSignedBatchGraphV2InvariantViolation(
            "M1A B1 authority failed raw replay"
        ) from error
    if (
        b1_result.public_context_closure_id
        != m0_result.public_context_closure_id
        or b1_result.observer_open_binding.binding_id
        != binding_record.semantic_artifact_id
    ):
        _fail("M1A B1 authority was transplanted")

    closure_record = _sole_record(
        bundle.records,
        "SIGNED_BATCH_JOURNAL_CLOSURE",
    )
    used_stream_ids = _used_stream_ids_from_closure_raw(
        closure_record.canonical_artifact_bytes
    )
    streams_by_id = m0_result.typed_graph.streams_by_id
    if any(stream_id not in streams_by_id for stream_id in used_stream_ids):
        _fail("M1A closure references a stream absent from M0")
    used_streams = tuple(
        streams_by_id[stream_id] for stream_id in used_stream_ids
    )
    try:
        closure = observer.load_observer_batch_journal_closure_bytes_v2(
            raw=closure_record.canonical_artifact_bytes,
            authority_binding=b1_result.observer_open_binding,
            known_stream_identities=used_streams,
        )
    except Exception as error:
        raise V075PortableSignedBatchGraphV2InvariantViolation(
            "M1A signed-batch closure failed issuer-backed raw replay"
        ) from error
    if (
        closure.closure_id != closure_record.semantic_artifact_id
        or closure.occurrence_id != bundle.occurrence_id
    ):
        _fail("M1A signed-batch closure crossed occurrence identity")

    verification_record = _sole_record(
        bundle.records,
        M1A_VERIFICATION_ROLE,
    )
    _verification_projection(
        record=verification_record,
        closure=closure,
    )
    role_set = {
        item.role for item in bundle.records if item.role in _M1A_ROLES
    }
    if role_set != _M1A_ROLES:
        _fail("portable bundle omits one M1A role")

    typed_graph = V075PortableSignedBatchTypedGraphV2(
        _TYPED_GRAPH_ISSUER,
        bundle.bundle_id,
        m0_result.public_context_closure_id,
        bundle.occurrence_id,
        m0_result,
        b1_result,
        used_streams,
        closure,
        _record_bindings(bundle.records),
    )
    dependency_resolution_dag = _build_dependency_resolution_dag(
        bundle=bundle,
        m0_result=m0_result,
        typed_graph=typed_graph,
    )
    attestations = _build_attestations(
        bundle=bundle,
        typed_graph=typed_graph,
        dependency_resolution_dag=dependency_resolution_dag,
    )

    m0_unresolved = tuple(
        sorted(
            {
                dependency_id
                for item in m0_result.attestations
                for dependency_id in item.unresolved_dependency_record_ids
            }
        )
    )
    complete_m1a_record_ids = {
        item.record_id
        for item in attestations
        if item.status is V075PortableM1ARoleReplayStatusV2.COMPLETE
    }
    discharged = tuple(
        value for value in m0_unresolved if value in complete_m1a_record_ids
    )
    remaining = tuple(
        value for value in m0_unresolved if value not in complete_m1a_record_ids
    )
    return V075PortableSignedBatchGraphReplayV2(
        _RESULT_ISSUER,
        bundle.bundle_id,
        bundle.occurrence_id,
        m0_result.public_context_closure_id,
        typed_graph,
        dependency_resolution_dag,
        attestations,
        m0_unresolved,
        discharged,
        remaining,
    )


def open_v075_production_from_portable_signed_batch_graph_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortableSignedBatchGraphProductionV2NotReady(
        "M1A public signed-batch graph replay is complete for six roles, "
        "but exact closure verification still requires private native replay"
    )


__all__ = [
    "CODE_PROVENANCE_COMPLETE",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "M1A_COMPLETE_ROLE_ORDER",
    "M1A_ROLE_ORDER",
    "M1A_ROLE_SEMANTICS_COMPLETE",
    "M1A_VERIFICATION_ROLE",
    "MAX_OUTPUT_BYTES",
    "OBSERVER_OPEN_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRIVATE_INPUT_CHANNELS_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "V075PortableM1ARecordSemanticAttestationV2",
    "V075PortableM1ARoleReplayStatusV2",
    "V075PortableSignedBatchGraphProductionV2NotReady",
    "V075PortableSignedBatchGraphReplayV2",
    "V075PortableSignedBatchGraphV2InvariantViolation",
    "V075PortableSignedBatchTypedGraphV2",
    "open_v075_production_from_portable_signed_batch_graph_v2",
    "replay_v075_portable_signed_batch_graph_v2",
]
