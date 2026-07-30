"""Portable M1B authority for the observer-signed control graph.

The sole public replay entry accepts only the repository root and two
canonical byte authorities already used by M0/M1A.  It invokes the hardened
M1A replay, reconstructs every present signed-control producer object, checks
all public signatures and the exact head/intent/append recurrence, and then
recomputes the public prefix/closure/reconciliation graph.

This module deliberately distinguishes three facts:

* a present control record was reconstructed from its producer bytes;
* every declared dependency of that record has public semantic authority;
* every role registered for the wider multiround protocol occurred here.

Consequently a root-only occurrence can have a complete control structure and
complete semantics for every *present* role while CHILD/PROMOTION roles remain
``NOT_PRESENT_IN_OCCURRENCE``.  Conversely, present CHILD/PROMOTION semantic
authorities remain structurally replayed but semantically opaque until their
own upstream portable authorities exist.

M1A's closure-verification record is never consumed as a private-replay proof.
No private verifier, salt, environment, signer, or live observer channel is
accepted.  The existing control loader is same-implementation construction
replay, not an independent production verifier, so all production, source,
code, registry, held-out, and certificate locks remain closed.
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
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_signed_batch_graph_authority_v2 as m1a
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_public_graph_semantics_v1 as graph


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.70.0"
PROFILE_KEY = "v075_portable_signed_control_graph_authority_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
PRIVATE_INPUT_CHANNELS_ALLOWED = False
PRIVATE_REPLAY_PERFORMED = False
M1A_PRIVATE_VERIFICATION_CLAIM_CONSUMED = False
INDEPENDENT_CONTROL_VERIFIER_PROVIDED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_M1B_SIGNED_CONTROL_GRAPH_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "M1B_CONTROL_STRUCTURE_REPLAYED_DYNAMIC_SEMANTIC_"
    "AUTHORITIES_MAY_REMAIN_OPAQUE"
)
MAX_OUTPUT_BYTES = 64 * 1024 * 1024

GENERIC_CONTROL_ROLE_ORDER = (
    "SIGNED_CONTROL_JOURNAL_HEAD",
    "SIGNED_APPEND_RECEIPT",
    "CONTROLLED_COMPLETE_SUPPORT_FREEZE",
    "OPEN_CONTROLLED_PREFIX_VERIFICATION",
    "SIGNED_CONTROL_CLOSURE",
    "SIGNED_CONTROL_RECONCILIATION",
    "CONTROLLED_JOURNAL_CLOSURE",
)
ROOT_CONTROL_ROLE_ORDER = (
    "CONTROLLED_ROOT_SEMANTIC_AUTHORITY",
    "CONTROLLED_ROOT_INTENT",
    "CONTROLLED_ROOT_APPEND",
)
CHILD_CONTROL_ROLE_ORDER = (
    "CONTROLLED_CHILD_SEMANTIC_AUTHORITY",
    "CONTROLLED_CHILD_INTENT",
    "CONTROLLED_CHILD_APPEND",
)
PROMOTION_CONTROL_ROLE_ORDER = (
    "CONTROLLED_PROMOTION_SEMANTIC_AUTHORITY",
    "CONTROLLED_PROMOTION_INTENT",
    "CONTROLLED_PROMOTION_APPEND",
)
CONTROL_ROLE_ORDER = (
    *GENERIC_CONTROL_ROLE_ORDER,
    *ROOT_CONTROL_ROLE_ORDER,
    *CHILD_CONTROL_ROLE_ORDER,
    *PROMOTION_CONTROL_ROLE_ORDER,
)
_CONTROL_ROLES = frozenset(CONTROL_ROLE_ORDER)
_OPAQUE_AUTHORITY_ROLES = frozenset(
    {
        "CONTROLLED_CHILD_SEMANTIC_AUTHORITY",
        "CONTROLLED_PROMOTION_SEMANTIC_AUTHORITY",
    }
)
_ROOT_AUTHORITY_ROLE = "CONTROLLED_ROOT_SEMANTIC_AUTHORITY"

_ROLE_ID_FIELD = MappingProxyType(
    {
        "SIGNED_CONTROL_JOURNAL_HEAD": "head_id",
        "SIGNED_APPEND_RECEIPT": "receipt_id",
        "CONTROLLED_COMPLETE_SUPPORT_FREEZE": "freeze_id",
        "OPEN_CONTROLLED_PREFIX_VERIFICATION": "verification_id",
        "SIGNED_CONTROL_CLOSURE": "control_closure_id",
        "SIGNED_CONTROL_RECONCILIATION": "reconciliation_id",
        "CONTROLLED_JOURNAL_CLOSURE": None,
        "CONTROLLED_ROOT_SEMANTIC_AUTHORITY": "binding_id",
        "CONTROLLED_ROOT_INTENT": "intent_id",
        "CONTROLLED_ROOT_APPEND": None,
        "CONTROLLED_CHILD_SEMANTIC_AUTHORITY": "binding_id",
        "CONTROLLED_CHILD_INTENT": "intent_id",
        "CONTROLLED_CHILD_APPEND": None,
        "CONTROLLED_PROMOTION_SEMANTIC_AUTHORITY": "binding_id",
        "CONTROLLED_PROMOTION_INTENT": "intent_id",
        "CONTROLLED_PROMOTION_APPEND": None,
    }
)

DOMAIN_TAGS = MappingProxyType(
    {
        "typed_graph": (
            "acfqp:v075-portable-signed-control-typed-graph:v2"
        ),
        "dependency_dag": (
            "acfqp:v075-portable-m1b-control-dependency-dag:v2"
        ),
        "record_attestation": (
            "acfqp:v075-portable-signed-control-record-attestation:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-signed-control-role-closure:v2"
        ),
        "aggregate": (
            "acfqp:v075-portable-signed-control-graph-authority:v2"
        ),
    }
)

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 M1B content domains overlap")


class V075PortableSignedControlGraphV2InvariantViolation(ValueError):
    """A raw control record, signature, recurrence, or dependency is invalid."""


class V075PortableSignedControlGraphProductionV2NotReady(RuntimeError):
    """M1B cannot authorize production or close opaque semantic authorities."""


class V075PortableControlRoleClosureStatusV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED = (
        "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
    )
    NOT_PRESENT_IN_OCCURRENCE = "NOT_PRESENT_IN_OCCURRENCE"


class _ResolverKindV2(str, Enum):
    UPSTREAM_M0_M1A_PUBLIC = "UPSTREAM_M0_M1A_PUBLIC"
    M1B_ROOT_SEMANTIC_AUTHORITY = "M1B_ROOT_SEMANTIC_AUTHORITY"
    M1B_PUBLIC_CONTROL_STRUCTURE = "M1B_PUBLIC_CONTROL_STRUCTURE"
    M1B_OPAQUE_SEMANTIC_AUTHORITY = (
        "M1B_OPAQUE_SEMANTIC_AUTHORITY"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


def _fail(message: str) -> NoReturn:
    raise V075PortableSignedControlGraphV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableSignedControlGraphV2InvariantViolation(
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
        raise V075PortableSignedControlGraphV2InvariantViolation(
            str(error)
        ) from error


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V075PortableSignedControlGraphV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _raw(value: Any) -> bytes:
    try:
        return canonical_json_bytes(value.to_document())
    except Exception as error:
        raise V075PortableSignedControlGraphV2InvariantViolation(
            "M1B producer object lacks one canonical document"
        ) from error


def _dynamic_kind_from_authority(
    value: control.V075ControlledBatchSemanticAuthorityBindingV2,
) -> str:
    role = value.role
    if (
        role
        is control.V075ControlledBatchSemanticAuthorityRoleV2
        .INITIAL_SCHEDULE_ROW_INTENT
    ):
        return "ROOT"
    if (
        role
        is control.V075ControlledBatchSemanticAuthorityRoleV2
        .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
    ):
        return "CHILD"
    if (
        role
        is control.V075ControlledBatchSemanticAuthorityRoleV2
        .LIVE_PROMOTION_AUTHORIZATION
    ):
        return "PROMOTION"
    _fail("M1B control authority uses an unregistered portable role")


def _record_role_for_authority(
    value: control.V075ControlledBatchSemanticAuthorityBindingV2,
) -> str:
    return f"CONTROLLED_{_dynamic_kind_from_authority(value)}_SEMANTIC_AUTHORITY"


def _record_role_for_intent(
    value: control.V075HeadBoundExactBatchIntentV2,
) -> str:
    return f"CONTROLLED_{_dynamic_kind_from_authority(value.semantic_authority)}_INTENT"


def _record_role_for_append(
    value: control.V075ControlledBatchAppendV2,
) -> str:
    return f"CONTROLLED_{_dynamic_kind_from_authority(value.intent.semantic_authority)}_APPEND"


@dataclass(frozen=True, slots=True)
class _ControlRecordBindingV2:
    record_id: str
    record_index: int
    role: str
    semantic_artifact_id: str
    dependency_record_ids: tuple[str, ...]
    canonical_artifact_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        self._assert_current()

    def _assert_current(self) -> None:
        _cid(self.record_id, "M1B control record")
        _cid(self.semantic_artifact_id, "M1B control semantic artifact")
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _CONTROL_ROLES
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
            or type(self.canonical_artifact_bytes) is not bytes
            or not self.canonical_artifact_bytes
        ):
            _fail("M1B control record binding is malformed")
        for dependency_id in self.dependency_record_ids:
            _cid(dependency_id, "M1B control dependency")
        document = _strict_document(
            self.canonical_artifact_bytes,
            label=f"M1B {self.role} record",
        )
        field_name = _ROLE_ID_FIELD[self.role]
        expected = (
            portable._derived_artifact_id(  # noqa: SLF001
                role=self.role,
                raw=self.canonical_artifact_bytes,
            )
            if field_name is None
            else _cid(
                document.get(field_name),
                f"M1B {self.role} producer identity",
            )
        )
        if expected != self.semantic_artifact_id:
            _fail(f"M1B {self.role} semantic ID differs from producer bytes")

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


@dataclass(frozen=True, slots=True)
class V075PortableControlDependencyNodeV2:
    """One compact, direct-edge, topological dependency decision."""

    record_id: str
    record_index: int
    role: str
    direct_dependency_record_ids: tuple[str, ...]
    resolver_kind: _ResolverKindV2
    producer_structure_replayed: bool
    semantically_resolved: bool

    def _assert_current(self) -> None:
        _cid(self.record_id, "M1B dependency node")
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or type(self.role) is not str
            or not self.role
            or type(self.direct_dependency_record_ids) is not tuple
            or tuple(sorted(set(self.direct_dependency_record_ids)))
            != self.direct_dependency_record_ids
            or type(self.resolver_kind) is not _ResolverKindV2
            or type(self.producer_structure_replayed) is not bool
            or type(self.semantically_resolved) is not bool
        ):
            _fail("M1B dependency node is malformed")
        for dependency_id in self.direct_dependency_record_ids:
            _cid(dependency_id, "M1B dependency edge")
        if (
            self.role in _CONTROL_ROLES
            and not self.producer_structure_replayed
        ):
            _fail("present M1B control node lacks producer reconstruction")
        if (
            self.resolver_kind
            is _ResolverKindV2.M1B_OPAQUE_SEMANTIC_AUTHORITY
            and self.semantically_resolved
        ):
            _fail("opaque M1B semantic authority was upgraded")

    @property
    def local_semantic_authority_resolved(self) -> bool:
        return self.resolver_kind in {
            _ResolverKindV2.UPSTREAM_M0_M1A_PUBLIC,
            _ResolverKindV2.M1B_ROOT_SEMANTIC_AUTHORITY,
            _ResolverKindV2.M1B_PUBLIC_CONTROL_STRUCTURE,
        }

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
            "producer_structure_replayed": (
                self.producer_structure_replayed
            ),
            "local_semantic_authority_resolved": (
                self.local_semantic_authority_resolved
            ),
            "semantically_resolved": self.semantically_resolved,
        }


def _iterative_control_dependency_nodes(
    *,
    records: tuple[Any, ...],
    upstream_public_record_ids: frozenset[str],
    structurally_replayed_control_record_ids: frozenset[str],
    root_semantic_authority_record_ids: frozenset[str],
) -> tuple[V075PortableControlDependencyNodeV2, ...]:
    """Resolve the full record DAG iteratively without materializing closure."""

    if type(records) is not tuple or not records:
        _fail("M1B dependency resolution requires one nonempty record tuple")
    control_ids = {
        item.record_id for item in records if item.role in _CONTROL_ROLES
    }
    if control_ids != set(structurally_replayed_control_record_ids):
        _fail("M1B producer replay does not cover every present control record")
    root_role_ids = {
        item.record_id
        for item in records
        if item.role == _ROOT_AUTHORITY_ROLE
    }
    if not set(root_semantic_authority_record_ids) <= root_role_ids:
        _fail("M1B attempted to upgrade a non-root semantic authority")

    nodes: list[V075PortableControlDependencyNodeV2] = []
    resolved_by_id: dict[str, bool] = {}
    for expected_index, record in enumerate(records):
        try:
            record_id = record.record_id
            record_index = record.index
            role = record.role
            dependencies = tuple(record.dependency_record_ids)
        except (AttributeError, TypeError) as error:
            raise V075PortableSignedControlGraphV2InvariantViolation(
                "M1B dependency record is malformed"
            ) from error
        if (
            record_index != expected_index
            or record_id in resolved_by_id
            or tuple(sorted(set(dependencies))) != dependencies
            or any(value not in resolved_by_id for value in dependencies)
        ):
            _fail("M1B dependency records are duplicated or non-topological")

        if role in _OPAQUE_AUTHORITY_ROLES:
            resolver_kind = (
                _ResolverKindV2.M1B_OPAQUE_SEMANTIC_AUTHORITY
            )
        elif record_id in root_semantic_authority_record_ids:
            resolver_kind = (
                _ResolverKindV2.M1B_ROOT_SEMANTIC_AUTHORITY
            )
        elif record_id in structurally_replayed_control_record_ids:
            resolver_kind = _ResolverKindV2.M1B_PUBLIC_CONTROL_STRUCTURE
        elif record_id in upstream_public_record_ids:
            resolver_kind = _ResolverKindV2.UPSTREAM_M0_M1A_PUBLIC
        else:
            resolver_kind = (
                _ResolverKindV2.NO_REGISTERED_SEMANTIC_AUTHORITY
            )
        local_resolved = resolver_kind in {
            _ResolverKindV2.UPSTREAM_M0_M1A_PUBLIC,
            _ResolverKindV2.M1B_ROOT_SEMANTIC_AUTHORITY,
            _ResolverKindV2.M1B_PUBLIC_CONTROL_STRUCTURE,
        }
        semantically_resolved = local_resolved and all(
            resolved_by_id[value] for value in dependencies
        )
        node = V075PortableControlDependencyNodeV2(
            record_id,
            record_index,
            role,
            dependencies,
            resolver_kind,
            record_id in structurally_replayed_control_record_ids,
            semantically_resolved,
        )
        node._assert_current()
        nodes.append(node)
        resolved_by_id[record_id] = semantically_resolved
    return tuple(nodes)


_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableControlDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    m1a_result_id: str
    typed_graph_id: str
    nodes: tuple[V075PortableControlDependencyNodeV2, ...] = field(
        repr=False
    )
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("M1B dependency DAG is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_dag_id",
            _hash("dependency_dag", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "M1B DAG bundle"),
            (self.m1a_result_id, "M1B DAG M1A result"),
            (self.typed_graph_id, "M1B DAG typed graph"),
        ):
            _cid(value, label)
        if (
            type(self.nodes) is not tuple
            or not self.nodes
            or any(
                type(item) is not V075PortableControlDependencyNodeV2
                for item in self.nodes
            )
            or tuple(item.record_index for item in self.nodes)
            != tuple(range(len(self.nodes)))
            or len({item.record_id for item in self.nodes})
            != len(self.nodes)
        ):
            _fail("M1B dependency DAG is malformed")
        resolved: dict[str, bool] = {}
        for item in self.nodes:
            item._assert_current()
            if any(
                dependency_id not in resolved
                for dependency_id in item.direct_dependency_record_ids
            ):
                _fail("M1B dependency DAG is not topological")
            expected = (
                item.local_semantic_authority_resolved
                and all(
                    resolved[dependency_id]
                    for dependency_id in item.direct_dependency_record_ids
                )
            )
            if item.semantically_resolved is not expected:
                _fail("M1B dependency resolution is stale")
            resolved[item.record_id] = item.semantically_resolved

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_m1b_control_dependency_dag.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m1a_result_id": self.m1a_result_id,
            "m1b_typed_graph_id": self.typed_graph_id,
            "nodes": [item.to_document() for item in self.nodes],
            "node_count": len(self.nodes),
            "edge_count": sum(
                len(item.direct_dependency_record_ids)
                for item in self.nodes
            ),
            "proof_shape": "ITERATIVE_TOPOLOGICAL_DIRECT_EDGE_DAG",
            "transitive_closure_materialized": False,
            "recursive_dependency_walk_used": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._dag_id != _hash("dependency_dag", self._payload()):
            _fail("M1B dependency DAG identity is stale")

    @property
    def dag_id(self) -> str:
        self._assert_current()
        return self._dag_id

    @property
    def nodes_by_id(
        self,
    ) -> Mapping[str, V075PortableControlDependencyNodeV2]:
        self._assert_current()
        return MappingProxyType({item.record_id: item for item in self.nodes})


def _records_by_role(
    bundle: portable.V075PortableOccurrenceEvidenceBundleV2,
) -> Mapping[
    str,
    tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
]:
    grouped: dict[
        str,
        list[portable.V075PortableEvidenceArtifactRecordV2],
    ] = {}
    for record in bundle.records:
        grouped.setdefault(record.role, []).append(record)
    return MappingProxyType(
        {role: tuple(values) for role, values in grouped.items()}
    )


def _sole_record(
    roles: Mapping[
        str,
        tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    ],
    role: str,
) -> portable.V075PortableEvidenceArtifactRecordV2:
    values = roles.get(role, ())
    if len(values) != 1:
        _fail(f"M1B requires exactly one {role} record")
    return values[0]


def _assert_record_equals_producer(
    *,
    record: portable.V075PortableEvidenceArtifactRecordV2,
    value: Any,
) -> None:
    raw = _raw(value)
    if raw != record.canonical_artifact_bytes:
        _fail(f"M1B {record.role} differs from producer reconstruction")
    field_name = _ROLE_ID_FIELD[record.role]
    expected = (
        portable._derived_artifact_id(  # noqa: SLF001
            role=record.role,
            raw=raw,
        )
        if field_name is None
        else _cid(
            value.to_document().get(field_name),
            f"M1B {record.role} producer identity",
        )
    )
    if expected != record.semantic_artifact_id:
        _fail(f"M1B {record.role} producer identity differs")


def _control_record_bindings(
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
) -> tuple[_ControlRecordBindingV2, ...]:
    return tuple(
        _ControlRecordBindingV2(
            item.record_id,
            item.index,
            item.role,
            item.semantic_artifact_id,
            item.dependency_record_ids,
            item.canonical_artifact_bytes,
        )
        for item in records
        if item.role in _CONTROL_ROLES
    )


def _reconstruct_heads(
    *,
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    binding: observer.V075ObserverOpenAuthorityBindingV2,
    expected_entry_count: int,
) -> tuple[control.V075SignedBatchJournalHeadV2, ...]:
    reconstructed: list[control.V075SignedBatchJournalHeadV2] = []
    for record in records:
        document = record.artifact_document
        raw_frontiers = document.get("stream_frontiers")
        if type(raw_frontiers) is not list:
            _fail("M1B signed control head lacks stream frontiers")
        try:
            frontiers = tuple(
                control.V075BatchStreamFrontierV2(
                    item["stream_id"],
                    item["row_binding_id"],
                    item["accepted_draw_cap"],
                    item["accepted_draw_end"],
                    item["batch_count"],
                    item["last_request_id"],
                    item["last_batch_id"],
                )
                for item in raw_frontiers
            )
            head = control.V075SignedBatchJournalHeadV2(
                document["occurrence_id"],
                document["observer_session_public_id"],
                binding,
                document["entry_count"],
                document["tail_entry_id"],
                document["total_accepted_draw_count"],
                frontiers,
                document["observer_signature_hex"],
            )
        except Exception as error:
            if type(error) is V075PortableSignedControlGraphV2InvariantViolation:
                raise
            raise V075PortableSignedControlGraphV2InvariantViolation(
                "M1B signed control head failed producer replay"
            ) from error
        _assert_record_equals_producer(record=record, value=head)
        reconstructed.append(head)
    heads = tuple(sorted(reconstructed, key=lambda item: item.entry_count))
    if (
        len(heads) != expected_entry_count + 1
        or tuple(item.entry_count for item in heads)
        != tuple(range(expected_entry_count + 1))
        or len({item.head_id for item in heads}) != len(heads)
    ):
        _fail("M1B signed control heads are missing, duplicated, or gapped")
    return heads


def _reconstruct_semantic_authorities(
    *,
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
) -> tuple[control.V075ControlledBatchSemanticAuthorityBindingV2, ...]:
    result: list[
        control.V075ControlledBatchSemanticAuthorityBindingV2
    ] = []
    for record in records:
        document = record.artifact_document
        try:
            value = control.freeze_v075_controlled_batch_semantic_authority_v2(
                role=control.V075ControlledBatchSemanticAuthorityRoleV2(
                    document["semantic_authority_role"]
                ),
                schema=(
                    control.V075ControlledBatchSemanticAuthoritySchemaV2(
                        document["semantic_authority_schema"]
                    )
                ),
                semantic_artifact_id=document["semantic_artifact_id"],
                semantic_verification_id=document[
                    "semantic_verification_id"
                ],
                stage=control.V075ControlledBatchStageV2(
                    document["stage"]
                ),
                round_index=document["round_index"],
                support_freeze_id=document["support_freeze_id"],
            )
        except Exception as error:
            raise V075PortableSignedControlGraphV2InvariantViolation(
                "M1B semantic authority failed typed opaque replay"
            ) from error
        if _record_role_for_authority(value) != record.role:
            _fail("M1B semantic authority was role-transplanted")
        _assert_record_equals_producer(record=record, value=value)
        result.append(value)
    return tuple(result)


def _reconstruct_intents(
    *,
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    heads_by_id: Mapping[str, control.V075SignedBatchJournalHeadV2],
    authorities_by_id: Mapping[
        str,
        control.V075ControlledBatchSemanticAuthorityBindingV2,
    ],
    streams_by_id: Mapping[str, graph.V075TransitionStreamIdentityV1],
) -> tuple[control.V075HeadBoundExactBatchIntentV2, ...]:
    result: list[control.V075HeadBoundExactBatchIntentV2] = []
    for record in records:
        document = record.artifact_document
        prior = heads_by_id.get(document.get("prior_head_id"))
        authority = authorities_by_id.get(
            document.get("semantic_authority_binding_id")
        )
        stream = streams_by_id.get(document.get("stream_id"))
        if prior is None or authority is None or stream is None:
            _fail("M1B intent lacks its exact head, authority, or stream")
        try:
            value = control.freeze_v075_head_bound_exact_batch_intent_v2(
                prior_head=prior,
                stream_identity=stream,
                semantic_authority=authority,
                accepted_draw_start=document["accepted_draw_start"],
                accepted_draw_count=document["accepted_draw_count"],
                accepted_draw_cap=document["accepted_draw_cap"],
            )
        except Exception as error:
            raise V075PortableSignedControlGraphV2InvariantViolation(
                "M1B intent failed exact head/stream recurrence"
            ) from error
        if _record_role_for_intent(value) != record.role:
            _fail("M1B intent was role-transplanted")
        _assert_record_equals_producer(record=record, value=value)
        result.append(value)
    return tuple(result)


def _reconstruct_receipts(
    *,
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    binding: observer.V075ObserverOpenAuthorityBindingV2,
) -> tuple[control.V075ObserverSignedBatchAppendReceiptV2, ...]:
    result: list[control.V075ObserverSignedBatchAppendReceiptV2] = []
    for record in records:
        document = record.artifact_document
        try:
            value = control.V075ObserverSignedBatchAppendReceiptV2(
                document["occurrence_id"],
                document["observer_session_public_id"],
                binding,
                document["prior_head_id"],
                document["intent_id"],
                document["semantic_authority_binding_id"],
                document["signed_batch_id"],
                document["signed_batch_request_id"],
                document["journal_entry_id"],
                document["journal_sequence_number"],
                document["resulting_head_id"],
                document["observer_signature_hex"],
            )
        except Exception as error:
            raise V075PortableSignedControlGraphV2InvariantViolation(
                "M1B append receipt failed observer-signature replay"
            ) from error
        _assert_record_equals_producer(record=record, value=value)
        result.append(value)
    receipts = tuple(
        sorted(result, key=lambda item: item.journal_sequence_number)
    )
    if tuple(item.journal_sequence_number for item in receipts) != tuple(
        range(1, len(receipts) + 1)
    ):
        _fail("M1B append receipt sequence is duplicated or gapped")
    return receipts


def _reconstruct_appends(
    *,
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    heads_by_id: Mapping[str, control.V075SignedBatchJournalHeadV2],
    intents_by_id: Mapping[str, control.V075HeadBoundExactBatchIntentV2],
    batches_by_id: Mapping[str, observer.V075SignedObservationBatchV2],
    receipts_by_id: Mapping[
        str,
        control.V075ObserverSignedBatchAppendReceiptV2,
    ],
) -> tuple[control.V075ControlledBatchAppendV2, ...]:
    result: list[control.V075ControlledBatchAppendV2] = []
    for record in records:
        document = record.artifact_document
        prior = heads_by_id.get(document.get("prior_head_id"))
        intent = intents_by_id.get(document.get("intent_id"))
        batch = batches_by_id.get(document.get("signed_batch_id"))
        resulting = heads_by_id.get(document.get("resulting_head_id"))
        receipt = receipts_by_id.get(document.get("append_receipt_id"))
        if any(
            item is None
            for item in (prior, intent, batch, resulting, receipt)
        ):
            _fail("M1B append lacks an exact typed producer dependency")
        try:
            value = control.V075ControlledBatchAppendV2(
                prior,
                intent,
                batch,
                resulting,
                receipt,
            )
        except Exception as error:
            raise V075PortableSignedControlGraphV2InvariantViolation(
                "M1B append failed exact head/intent/batch/receipt replay"
            ) from error
        if _record_role_for_append(value) != record.role:
            _fail("M1B append was role-transplanted")
        _assert_record_equals_producer(record=record, value=value)
        result.append(value)
    appends = tuple(
        sorted(result, key=lambda item: item.resulting_head.entry_count)
    )
    if tuple(item.resulting_head.entry_count for item in appends) != tuple(
        range(1, len(appends) + 1)
    ):
        _fail("M1B append chain is duplicated or gapped")
    return appends


def _validate_root_semantic_authority_bindings(
    *,
    authority_records: tuple[
        portable.V075PortableEvidenceArtifactRecordV2,
        ...,
    ],
    appends: tuple[control.V075ControlledBatchAppendV2, ...],
    m1a_result: m1a.V075PortableSignedBatchGraphReplayV2,
) -> frozenset[str]:
    """Bind every executable ROOT append to the exact ordered M0 witness."""

    m0_graph = m1a_result.typed_graph.m0_result.typed_graph
    executable_kinds = {
        acquisition.V075InitialIntentKindV2.ROOT_DISCOVERY,
        acquisition.V075InitialIntentKindV2.ROOT_VALIDATION,
    }
    expected_witnesses = tuple(
        item
        for item in m0_graph.schedule.intents
        if item.kind in executable_kinds
    )
    root_appends = tuple(
        item
        for item in appends
        if (
            item.intent.semantic_authority.role
            is (
                control.V075ControlledBatchSemanticAuthorityRoleV2
                .INITIAL_SCHEDULE_ROW_INTENT
            )
        )
    )
    actual_authorities = tuple(
        item.intent.semantic_authority for item in root_appends
    )
    root_records = tuple(
        item
        for item in authority_records
        if item.role == _ROOT_AUTHORITY_ROLE
    )
    if any(
        _strict_document(
            item.canonical_artifact_bytes,
            label="M1B ROOT semantic authority binding",
        ).get("binding_id")
        != item.semantic_artifact_id
        for item in root_records
    ):
        _fail("M1B ROOT record semantic ID differs from producer binding ID")
    records_by_binding_id = {
        item.semantic_artifact_id: item for item in root_records
    }
    expected_semantic_artifact_ids = tuple(
        item.intent_id for item in expected_witnesses
    )
    actual_semantic_artifact_ids = tuple(
        item.semantic_artifact_id for item in actual_authorities
    )
    if (
        not expected_witnesses
        or len(root_appends) != len(expected_witnesses)
        or actual_semantic_artifact_ids != expected_semantic_artifact_ids
        or len(set(actual_semantic_artifact_ids))
        != len(actual_semantic_artifact_ids)
        or len(root_records) != len(actual_authorities)
        or len(records_by_binding_id) != len(root_records)
        or set(records_by_binding_id)
        != {item.binding_id for item in actual_authorities}
    ):
        _fail(
            "M1B ordered ROOT semantic authorities do not exactly cover "
            "the executable M0 root schedule"
        )

    for append, authority, witness in zip(
        root_appends,
        actual_authorities,
        expected_witnesses,
        strict=True,
    ):
        intent = append.intent
        stream = intent.stream_identity
        if witness.kind is acquisition.V075InitialIntentKindV2.ROOT_DISCOVERY:
            expected_stage = control.V075ControlledBatchStageV2.ROOT_DISCOVERY
            expected_lane = graph.V075ObservationLaneV1.DISCOVERY
        elif (
            witness.kind
            is acquisition.V075InitialIntentKindV2.ROOT_VALIDATION
        ):
            expected_stage = control.V075ControlledBatchStageV2.ROOT_VALIDATION
            expected_lane = graph.V075ObservationLaneV1.VALIDATION
        else:  # pragma: no cover - excluded above and kept fail closed
            _fail("M1B ROOT semantic authority cites a template-only intent")
        if (
            authority.role
            is not (
                control.V075ControlledBatchSemanticAuthorityRoleV2
                .INITIAL_SCHEDULE_ROW_INTENT
            )
            or authority.schema
            is not (
                control.V075ControlledBatchSemanticAuthoritySchemaV2
                .INITIAL_SCHEDULE_ROW_INTENT
            )
            or authority.semantic_artifact_id != witness.intent_id
            or authority.semantic_verification_id
            != m0_graph.verification.verification_id
            or authority.stage is not expected_stage
            or authority.round_index != 0
            or stream.row_binding != witness.row_binding
            or stream.row_binding_id != witness.row_binding.row_binding_id
            or stream.observer_epoch_index != witness.observer_epoch_index
            or stream.lane is not expected_lane
            or stream.arm != witness.arm.value
            or intent.accepted_draw_start != witness.accepted_draw_start
            or intent.accepted_draw_count != witness.accepted_draw_count
            or intent.accepted_draw_cap != witness.accepted_draw_cap
        ):
            _fail(
                "M1B ROOT semantic authority differs from its exact "
                "M0 row/stage/lane/epoch/draw witness"
            )
    return frozenset(item.record_id for item in root_records)


def _reconstruct_support_freezes(
    *,
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    appends_by_receipt_id: Mapping[
        str,
        control.V075ControlledBatchAppendV2,
    ],
    heads_by_id: Mapping[str, control.V075SignedBatchJournalHeadV2],
    evidence_by_id: Mapping[
        str,
        graph.V075BatchAggregateSupportEvidenceV1,
    ],
) -> tuple[control.V075ControlledCompleteSupportFreezeV2, ...]:
    result: list[control.V075ControlledCompleteSupportFreezeV2] = []
    for record in records:
        document = record.artifact_document
        append = appends_by_receipt_id.get(
            document.get("discovery_append_receipt_id")
        )
        head = heads_by_id.get(document.get("frozen_at_head_id"))
        evidence_ids = document.get("evidence_ids")
        if (
            append is None
            or head is None
            or type(evidence_ids) is not list
            or any(item not in evidence_by_id for item in evidence_ids)
        ):
            _fail("M1B support freeze lacks append/head/evidence dependencies")
        evidence = tuple(evidence_by_id[item] for item in evidence_ids)
        try:
            value = control.V075ControlledCompleteSupportFreezeV2(
                control._REPLAYED_SUPPORT_FREEZE_ISSUER,  # noqa: SLF001
                append,
                head,
                evidence,
                document["observer_signature_hex"],
            )
        except Exception as error:
            raise V075PortableSignedControlGraphV2InvariantViolation(
                "M1B support freeze failed complete-support/signature replay"
            ) from error
        _assert_record_equals_producer(record=record, value=value)
        result.append(value)
    return tuple(
        sorted(
            result,
            key=lambda item: (
                item.frozen_at_head.entry_count,
                item.row_binding_id,
                item.freeze_id,
            ),
        )
    )


def _reconstruct_open_prefixes(
    *,
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    heads_by_id: Mapping[str, control.V075SignedBatchJournalHeadV2],
    appends_by_receipt_id: Mapping[
        str,
        control.V075ControlledBatchAppendV2,
    ],
    freezes_by_id: Mapping[
        str,
        control.V075ControlledCompleteSupportFreezeV2,
    ],
) -> tuple[control.V075OpenControlledBatchPrefixVerificationV2, ...]:
    result: list[
        control.V075OpenControlledBatchPrefixVerificationV2
    ] = []
    for record in records:
        document = record.artifact_document
        head_ids = document.get("head_ids")
        receipt_ids = document.get("append_receipt_ids")
        freeze_ids = document.get("support_freeze_ids")
        if (
            type(head_ids) is not list
            or type(receipt_ids) is not list
            or type(freeze_ids) is not list
            or any(item not in heads_by_id for item in head_ids)
            or any(
                item not in appends_by_receipt_id for item in receipt_ids
            )
            or any(item not in freezes_by_id for item in freeze_ids)
        ):
            _fail("M1B open prefix lacks exact typed members")
        heads = tuple(heads_by_id[item] for item in head_ids)
        appends = tuple(
            appends_by_receipt_id[item] for item in receipt_ids
        )
        freezes = tuple(freezes_by_id[item] for item in freeze_ids)
        try:
            value = control.verify_v075_open_controlled_batch_prefix_v2(
                heads=heads,
                appends=appends,
                support_freezes=freezes,
            )
        except Exception as error:
            raise V075PortableSignedControlGraphV2InvariantViolation(
                "M1B open prefix failed exact public control replay"
            ) from error
        _assert_record_equals_producer(record=record, value=value)
        result.append(value)
    if not result:
        _fail("M1B portable control graph contains no open prefix")
    return tuple(result)


def _reconstruct_control_closure(
    *,
    record: portable.V075PortableEvidenceArtifactRecordV2,
    binding: observer.V075ObserverOpenAuthorityBindingV2,
) -> control.V075ObserverSignedBatchControlClosureV2:
    document = record.artifact_document
    try:
        value = control.V075ObserverSignedBatchControlClosureV2(
            document["occurrence_id"],
            document["observer_session_public_id"],
            binding,
            document["zero_head_id"],
            document["final_head_id"],
            tuple(document["head_ids"]),
            tuple(document["intent_ids"]),
            tuple(document["semantic_authority_binding_ids"]),
            tuple(document["support_freeze_ids"]),
            tuple(document["append_receipt_ids"]),
            document["batch_journal_closure_id"],
            tuple(document["signed_batch_ids"]),
            tuple(document["journal_entry_ids"]),
            document["observer_signature_hex"],
        )
    except Exception as error:
        raise V075PortableSignedControlGraphV2InvariantViolation(
            "M1B control closure failed observer-signature replay"
        ) from error
    _assert_record_equals_producer(record=record, value=value)
    return value


def _reconstruct_final_control_graph(
    *,
    roles: Mapping[
        str,
        tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    ],
    m1a_result: m1a.V075PortableSignedBatchGraphReplayV2,
    heads: tuple[control.V075SignedBatchJournalHeadV2, ...],
    appends: tuple[control.V075ControlledBatchAppendV2, ...],
    freezes: tuple[control.V075ControlledCompleteSupportFreezeV2, ...],
    control_closure: control.V075ObserverSignedBatchControlClosureV2,
) -> tuple[
    control.V075SignedBatchControlReconciliationV2,
    control.V075ControlledBatchJournalClosureV2,
]:
    batch_closure = m1a_result.typed_graph.closure
    try:
        reconciliation = (
            control.verify_v075_controlled_batch_journal_closure_v2(
                batch_closure=batch_closure,
                heads=heads,
                appends=appends,
                control_closure=control_closure,
                support_freezes=freezes,
            )
        )
    except Exception as error:
        raise V075PortableSignedControlGraphV2InvariantViolation(
            "M1B final control graph failed same-implementation replay"
        ) from error
    reconciliation_record = _sole_record(
        roles,
        "SIGNED_CONTROL_RECONCILIATION",
    )
    _assert_record_equals_producer(
        record=reconciliation_record,
        value=reconciliation,
    )
    try:
        closed = control.V075ControlledBatchJournalClosureV2(
            batch_closure,
            heads,
            appends,
            control_closure,
            reconciliation,
            freezes,
        )
    except Exception as error:
        raise V075PortableSignedControlGraphV2InvariantViolation(
            "M1B controlled journal closure failed exact graph replay"
        ) from error
    closed_record = _sole_record(roles, "CONTROLLED_JOURNAL_CLOSURE")
    _assert_record_equals_producer(record=closed_record, value=closed)
    return reconciliation, closed


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableSignedControlTypedGraphV2:
    """In-memory producer-typed view of every present M1B control record."""

    _issuer: InitVar[object]
    bundle_id: str
    public_context_closure_id: str
    occurrence_id: str
    m1a_result: m1a.V075PortableSignedBatchGraphReplayV2 = field(
        repr=False
    )
    heads: tuple[control.V075SignedBatchJournalHeadV2, ...] = field(
        repr=False
    )
    semantic_authorities: tuple[
        control.V075ControlledBatchSemanticAuthorityBindingV2,
        ...,
    ] = field(repr=False)
    intents: tuple[control.V075HeadBoundExactBatchIntentV2, ...] = field(
        repr=False
    )
    receipts: tuple[
        control.V075ObserverSignedBatchAppendReceiptV2,
        ...,
    ] = field(repr=False)
    appends: tuple[control.V075ControlledBatchAppendV2, ...] = field(
        repr=False
    )
    support_freezes: tuple[
        control.V075ControlledCompleteSupportFreezeV2,
        ...,
    ] = field(repr=False)
    open_prefixes: tuple[
        control.V075OpenControlledBatchPrefixVerificationV2,
        ...,
    ] = field(repr=False)
    control_closure: control.V075ObserverSignedBatchControlClosureV2 = field(
        repr=False
    )
    reconciliation: control.V075SignedBatchControlReconciliationV2 = field(
        repr=False
    )
    controlled_closure: control.V075ControlledBatchJournalClosureV2 = field(
        repr=False
    )
    record_bindings: tuple[_ControlRecordBindingV2, ...] = field(
        repr=False
    )
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("M1B typed graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._identity_payload()),
        )

    def _typed_views_by_role(self) -> Mapping[str, tuple[Any, ...]]:
        grouped: dict[str, list[Any]] = {
            role: [] for role in CONTROL_ROLE_ORDER
        }
        grouped["SIGNED_CONTROL_JOURNAL_HEAD"].extend(self.heads)
        grouped["SIGNED_APPEND_RECEIPT"].extend(self.receipts)
        grouped["CONTROLLED_COMPLETE_SUPPORT_FREEZE"].extend(
            self.support_freezes
        )
        grouped["OPEN_CONTROLLED_PREFIX_VERIFICATION"].extend(
            self.open_prefixes
        )
        grouped["SIGNED_CONTROL_CLOSURE"].append(self.control_closure)
        grouped["SIGNED_CONTROL_RECONCILIATION"].append(
            self.reconciliation
        )
        grouped["CONTROLLED_JOURNAL_CLOSURE"].append(
            self.controlled_closure
        )
        for item in self.semantic_authorities:
            grouped[_record_role_for_authority(item)].append(item)
        for item in self.intents:
            grouped[_record_role_for_intent(item)].append(item)
        for item in self.appends:
            grouped[_record_role_for_append(item)].append(item)
        return MappingProxyType(
            {role: tuple(values) for role, values in grouped.items()}
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "M1B typed graph bundle"),
            (
                self.public_context_closure_id,
                "M1B typed graph public context",
            ),
            (self.occurrence_id, "M1B typed graph occurrence"),
        ):
            _cid(value, label)
        typed_sequences = (
            (
                self.heads,
                control.V075SignedBatchJournalHeadV2,
                "heads",
            ),
            (
                self.semantic_authorities,
                control.V075ControlledBatchSemanticAuthorityBindingV2,
                "semantic authorities",
            ),
            (
                self.intents,
                control.V075HeadBoundExactBatchIntentV2,
                "intents",
            ),
            (
                self.receipts,
                control.V075ObserverSignedBatchAppendReceiptV2,
                "receipts",
            ),
            (
                self.appends,
                control.V075ControlledBatchAppendV2,
                "appends",
            ),
            (
                self.support_freezes,
                control.V075ControlledCompleteSupportFreezeV2,
                "support freezes",
            ),
            (
                self.open_prefixes,
                control.V075OpenControlledBatchPrefixVerificationV2,
                "open prefixes",
            ),
        )
        if (
            type(self.m1a_result)
            is not m1a.V075PortableSignedBatchGraphReplayV2
            or any(
                type(values) is not tuple
                or (label != "support freezes" and not values)
                or any(type(item) is not expected for item in values)
                for values, expected, label in typed_sequences
            )
            or type(self.control_closure)
            is not control.V075ObserverSignedBatchControlClosureV2
            or type(self.reconciliation)
            is not control.V075SignedBatchControlReconciliationV2
            or type(self.controlled_closure)
            is not control.V075ControlledBatchJournalClosureV2
            or type(self.record_bindings) is not tuple
            or not self.record_bindings
            or any(
                type(item) is not _ControlRecordBindingV2
                for item in self.record_bindings
            )
            or len({item.record_id for item in self.record_bindings})
            != len(self.record_bindings)
            or tuple(item.record_index for item in self.record_bindings)
            != tuple(sorted(item.record_index for item in self.record_bindings))
        ):
            _fail("M1B typed graph is malformed")
        self.m1a_result._assert_current()  # noqa: SLF001
        if (
            self.m1a_result.bundle_id != self.bundle_id
            or self.m1a_result.public_context_closure_id
            != self.public_context_closure_id
            or self.m1a_result.occurrence_id != self.occurrence_id
            or len(self.heads) != len(self.appends) + 1
            or len(self.intents) != len(self.appends)
            or len(self.receipts) != len(self.appends)
            or self.controlled_closure.batch_closure
            != self.m1a_result.typed_graph.closure
            or self.controlled_closure.heads != self.heads
            or self.controlled_closure.appends != self.appends
            or self.controlled_closure.support_freezes
            != self.support_freezes
            or self.controlled_closure.control_closure
            != self.control_closure
            or self.controlled_closure.reconciliation
            != self.reconciliation
        ):
            _fail("M1B typed graph crossed bundle/context/control identities")

        try:
            exact_prefix = (
                control.verify_v075_open_controlled_batch_prefix_v2(
                    heads=self.heads,
                    appends=self.appends,
                    support_freezes=self.support_freezes,
                )
            )
            exact_reconciliation = (
                control.verify_v075_controlled_batch_journal_closure_v2(
                    batch_closure=self.m1a_result.typed_graph.closure,
                    heads=self.heads,
                    appends=self.appends,
                    control_closure=self.control_closure,
                    support_freezes=self.support_freezes,
                )
            )
        except Exception as error:
            raise V075PortableSignedControlGraphV2InvariantViolation(
                "M1B typed graph failed fresh head/closure replay"
            ) from error
        if (
            exact_reconciliation != self.reconciliation
            or exact_prefix.current_head_id != self.heads[-1].head_id
        ):
            _fail("M1B typed graph replay result changed")

        bindings_by_role: dict[
            str,
            dict[bytes, _ControlRecordBindingV2],
        ] = {}
        for item in self.record_bindings:
            item._assert_current()
            role_bindings = bindings_by_role.setdefault(item.role, {})
            if item.canonical_artifact_bytes in role_bindings:
                _fail("M1B maps two records to the same role/raw bytes")
            role_bindings[item.canonical_artifact_bytes] = item
        views = self._typed_views_by_role()
        if set(bindings_by_role) != {
            role for role, values in views.items() if values
        }:
            _fail("M1B typed graph role coverage differs from raw records")
        for role, values in views.items():
            typed_by_raw = {_raw(item): item for item in values}
            raw_bindings = bindings_by_role.get(role, {})
            if set(typed_by_raw) != set(raw_bindings):
                _fail(f"M1B {role} typed/raw mapping is not one-to-one")
        _validate_root_semantic_authority_bindings(
            authority_records=tuple(
                item
                for item in self.record_bindings
                if item.role
                in {
                    "CONTROLLED_ROOT_SEMANTIC_AUTHORITY",
                    "CONTROLLED_CHILD_SEMANTIC_AUTHORITY",
                    "CONTROLLED_PROMOTION_SEMANTIC_AUTHORITY",
                }
            ),
            appends=self.appends,
            m1a_result=self.m1a_result,
        )

    def _identity_payload(self) -> dict[str, Any]:
        views = self._typed_views_by_role()
        return {
            "schema": "acfqp.v075_portable_signed_control_typed_graph.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "public_context_closure_id": self.public_context_closure_id,
            "occurrence_id": self.occurrence_id,
            # _validate() has already replayed M1A in this validation
            # transaction.  Reusing its checked content IDs here avoids
            # recursively replaying the complete M0/M1A graph for every
            # identity field.
            "m1a_result_id": self.m1a_result._result_id,  # noqa: SLF001
            "m1a_typed_graph_id": (
                self.m1a_result.typed_graph._graph_id  # noqa: SLF001
            ),
            "signed_batch_journal_closure_id": (
                self.m1a_result.typed_graph.closure.closure_id
            ),
            "control_closure_id": self.control_closure.control_closure_id,
            "control_reconciliation_id": (
                self.reconciliation.reconciliation_id
            ),
            "ordered_head_ids": [item.head_id for item in self.heads],
            "ordered_intent_ids": [
                item.intent_id for item in self.intents
            ],
            "ordered_receipt_ids": [
                item.receipt_id for item in self.receipts
            ],
            "ordered_append_receipt_ids": [
                item.receipt.receipt_id for item in self.appends
            ],
            "support_freeze_ids": [
                item.freeze_id for item in self.support_freezes
            ],
            "open_prefix_verification_ids": [
                item.verification_id for item in self.open_prefixes
            ],
            "role_record_ids": {
                role: [
                    item.record_id
                    for item in self.record_bindings
                    if item.role == role
                ]
                for role in CONTROL_ROLE_ORDER
            },
            "role_typed_counts": {
                role: len(values) for role, values in views.items()
            },
            "ordered_record_commitments": [
                item.commitment_document() for item in self.record_bindings
            ],
            "producer_typed_objects_in_memory_only": True,
            "issuer_gate_semantics": "CONSTRUCTION_API_DISCIPLINE_ONLY",
            "same_implementation_control_replay_used": True,
            "independent_control_verifier_provided": False,
            "typed_objects_serialized": False,
            "private_material_serialized": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._graph_id != _hash(
            "typed_graph",
            self._identity_payload(),
        ):
            _fail("M1B typed graph identity is stale")

    @property
    def graph_id(self) -> str:
        self._assert_current()
        return self._graph_id

    def __reduce__(self) -> NoReturn:
        raise TypeError("M1B typed graph is in-memory-only")


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableControlRecordAttestationV2:
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
    direct_dependency_record_ids: tuple[str, ...]
    resolved_direct_dependency_record_ids: tuple[str, ...]
    unresolved_direct_dependency_record_ids: tuple[str, ...]
    unresolved_direct_dependency_roles: tuple[str, ...]
    resolver_kind: _ResolverKindV2
    status: V075PortableControlRoleClosureStatusV2
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.bundle_id, "M1B attestation bundle"),
            (self.typed_graph_id, "M1B attestation typed graph"),
            (self.dependency_dag_id, "M1B attestation dependency DAG"),
            (self.record_id, "M1B attestation record"),
            (self.semantic_artifact_id, "M1B attestation semantic artifact"),
            (
                self.canonical_artifact_sha256,
                "M1B attestation raw digest",
            ),
        ):
            _cid(value, label)
        dependency_sets = (
            self.direct_dependency_record_ids,
            self.resolved_direct_dependency_record_ids,
            self.unresolved_direct_dependency_record_ids,
        )
        if (
            _issuer is not _ATTESTATION_ISSUER
            or type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _CONTROL_ROLES
            or type(self.canonical_artifact_byte_count) is not int
            or self.canonical_artifact_byte_count <= 0
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in dependency_sets
            )
            or set(self.resolved_direct_dependency_record_ids)
            | set(self.unresolved_direct_dependency_record_ids)
            != set(self.direct_dependency_record_ids)
            or set(self.resolved_direct_dependency_record_ids)
            & set(self.unresolved_direct_dependency_record_ids)
            or type(self.unresolved_direct_dependency_roles) is not tuple
            or tuple(sorted(set(self.unresolved_direct_dependency_roles)))
            != self.unresolved_direct_dependency_roles
            or type(self.resolver_kind) is not _ResolverKindV2
            or type(self.status)
            is not V075PortableControlRoleClosureStatusV2
            or self.status
            is V075PortableControlRoleClosureStatusV2
            .NOT_PRESENT_IN_OCCURRENCE
        ):
            _fail("M1B record attestation is malformed")
        for dependency_id in self.direct_dependency_record_ids:
            _cid(dependency_id, "M1B attestation dependency")
        expected_full = (
            self.resolver_kind
            is not _ResolverKindV2.M1B_OPAQUE_SEMANTIC_AUTHORITY
            and not self.unresolved_direct_dependency_record_ids
        )
        if (
            (
                self.status
                is V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
            )
            is not expected_full
        ):
            _fail("M1B record attestation status overclaims dependencies")
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("record_attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_signed_control_record_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m1b_typed_graph_id": self.typed_graph_id,
            "m1b_dependency_dag_id": self.dependency_dag_id,
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
            "direct_dependency_record_ids": list(
                self.direct_dependency_record_ids
            ),
            "resolved_direct_dependency_record_ids": list(
                self.resolved_direct_dependency_record_ids
            ),
            "unresolved_direct_dependency_record_ids": list(
                self.unresolved_direct_dependency_record_ids
            ),
            "unresolved_direct_dependency_roles": list(
                self.unresolved_direct_dependency_roles
            ),
            "resolver_kind": self.resolver_kind.value,
            "status": self.status.value,
            "producer_typed_object_reconstructed": True,
            "canonical_bytes_equal_reconstruction": True,
            "producer_signature_or_content_identity_replayed": True,
            "control_structure_reconstructed": True,
            "same_implementation_control_replay_used": True,
            "independent_control_verifier_provided": False,
            "m1a_private_verification_claim_consumed": False,
            "private_replay_performed": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "portable_semantic_registry_complete": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_material_serialized": False,
        }

    def _assert_current(self) -> None:
        if self._attestation_id != _hash(
            "record_attestation",
            self._payload(),
        ):
            _fail("M1B record attestation identity is stale")

    @property
    def attestation_id(self) -> str:
        self._assert_current()
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "attestation_id": self._attestation_id}


_ROLE_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableControlRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    dependency_dag_id: str
    role: str
    status: V075PortableControlRoleClosureStatusV2
    record_ids: tuple[str, ...]
    attestation_ids: tuple[str, ...]
    unresolved_record_ids: tuple[str, ...]
    unresolved_dependency_record_ids: tuple[str, ...]
    unresolved_dependency_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.bundle_id, "M1B role closure bundle"),
            (self.typed_graph_id, "M1B role closure typed graph"),
            (self.dependency_dag_id, "M1B role closure DAG"),
        ):
            _cid(value, label)
        id_sequences = (
            self.record_ids,
            self.attestation_ids,
            self.unresolved_record_ids,
            self.unresolved_dependency_record_ids,
        )
        if (
            _issuer is not _ROLE_CLOSURE_ISSUER
            or self.role not in _CONTROL_ROLES
            or type(self.status)
            is not V075PortableControlRoleClosureStatusV2
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in id_sequences
            )
            or type(self.unresolved_dependency_roles) is not tuple
            or tuple(sorted(set(self.unresolved_dependency_roles)))
            != self.unresolved_dependency_roles
        ):
            _fail("M1B role closure is malformed")
        for values in id_sequences:
            for value in values:
                _cid(value, "M1B role closure member")
        absent = (
            self.status
            is V075PortableControlRoleClosureStatusV2
            .NOT_PRESENT_IN_OCCURRENCE
        )
        full = (
            self.status
            is V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
        )
        if (
            absent
            != (
                not self.record_ids
                and not self.attestation_ids
                and not self.unresolved_record_ids
                and not self.unresolved_dependency_record_ids
                and not self.unresolved_dependency_roles
            )
            or (not absent and len(self.record_ids) != len(self.attestation_ids))
            or (full and (self.unresolved_record_ids
                          or self.unresolved_dependency_record_ids
                          or self.unresolved_dependency_roles))
            or (
                not absent
                and not full
                and not self.unresolved_record_ids
            )
        ):
            _fail("M1B role closure status does not match its evidence")
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    @property
    def present_in_occurrence(self) -> bool:
        return bool(self.record_ids)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_control_role_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m1b_typed_graph_id": self.typed_graph_id,
            "m1b_dependency_dag_id": self.dependency_dag_id,
            "role": self.role,
            "status": self.status.value,
            "present_in_occurrence": self.present_in_occurrence,
            "record_ids": list(self.record_ids),
            "attestation_ids": list(self.attestation_ids),
            "record_count": len(self.record_ids),
            "unresolved_record_ids": list(self.unresolved_record_ids),
            "unresolved_dependency_record_ids": list(
                self.unresolved_dependency_record_ids
            ),
            "unresolved_dependency_roles": list(
                self.unresolved_dependency_roles
            ),
            "present_record_structure_reconstructed": (
                self.present_in_occurrence
            ),
            "absence_is_not_native_zero": not self.present_in_occurrence,
            "absence_is_not_completion_evidence": not self.present_in_occurrence,
            "same_implementation_control_replay_used": (
                self.present_in_occurrence
            ),
            "independent_control_verifier_provided": False,
        }

    def _assert_current(self) -> None:
        if self._closure_id != _hash("role_closure", self._payload()):
            _fail("M1B role closure identity is stale")

    @property
    def closure_id(self) -> str:
        self._assert_current()
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "closure_id": self._closure_id}


def _build_record_attestations(
    *,
    bundle: portable.V075PortableOccurrenceEvidenceBundleV2,
    typed_graph: V075PortableSignedControlTypedGraphV2,
    dag: V075PortableControlDependencyDAGV2,
) -> tuple[V075PortableControlRecordAttestationV2, ...]:
    typed_graph._assert_current()  # noqa: SLF001
    dag._assert_current()  # noqa: SLF001
    typed_graph_id = typed_graph._graph_id  # noqa: SLF001
    dependency_dag_id = dag._dag_id  # noqa: SLF001
    nodes = {item.record_id: item for item in dag.nodes}
    by_id = {item.record_id: item for item in bundle.records}
    result: list[V075PortableControlRecordAttestationV2] = []
    for record in bundle.records:
        if record.role not in _CONTROL_ROLES:
            continue
        node = nodes[record.record_id]
        resolved = tuple(
            dependency_id
            for dependency_id in record.dependency_record_ids
            if nodes[dependency_id].semantically_resolved
        )
        unresolved = tuple(
            dependency_id
            for dependency_id in record.dependency_record_ids
            if not nodes[dependency_id].semantically_resolved
        )
        unresolved_roles = tuple(
            sorted({by_id[item].role for item in unresolved})
        )
        status = (
            V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
            if node.semantically_resolved
            else V075PortableControlRoleClosureStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        result.append(
            V075PortableControlRecordAttestationV2(
                _ATTESTATION_ISSUER,
                bundle.bundle_id,
                typed_graph_id,
                dependency_dag_id,
                record.record_id,
                record.index,
                record.role,
                record.semantic_artifact_id,
                hashlib.sha256(
                    record.canonical_artifact_bytes
                ).hexdigest(),
                len(record.canonical_artifact_bytes),
                record.dependency_record_ids,
                resolved,
                unresolved,
                unresolved_roles,
                node.resolver_kind,
                status,
            )
        )
    return tuple(result)


def _build_role_closures(
    *,
    bundle_id: str,
    typed_graph_id: str,
    dependency_dag_id: str,
    records: tuple[Any, ...],
    attestations: tuple[V075PortableControlRecordAttestationV2, ...],
) -> tuple[V075PortableControlRoleClosureV2, ...]:
    attestation_by_record = {
        item.record_id: item for item in attestations
    }
    result: list[V075PortableControlRoleClosureV2] = []
    for role in CONTROL_ROLE_ORDER:
        role_records = tuple(
            sorted(
                (
                    item
                    for item in records
                    if item.role == role
                ),
                key=lambda item: item.record_id,
            )
        )
        if not role_records:
            status = (
                V075PortableControlRoleClosureStatusV2
                .NOT_PRESENT_IN_OCCURRENCE
            )
            role_attestations: tuple[
                V075PortableControlRecordAttestationV2,
                ...,
            ] = ()
        else:
            role_attestations = tuple(
                attestation_by_record[item.record_id]
                for item in role_records
            )
            status = (
                V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
                if all(
                    item.status
                    is V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
                    for item in role_attestations
                )
                else V075PortableControlRoleClosureStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
        unresolved_items = tuple(
            item
            for item in role_attestations
            if item.status
            is not V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
        )
        result.append(
            V075PortableControlRoleClosureV2(
                _ROLE_CLOSURE_ISSUER,
                bundle_id,
                typed_graph_id,
                dependency_dag_id,
                role,
                status,
                tuple(item.record_id for item in role_records),
                tuple(
                    sorted(
                        item.attestation_id for item in role_attestations
                    )
                ),
                tuple(item.record_id for item in unresolved_items),
                tuple(
                    sorted(
                        {
                            dependency_id
                            for item in unresolved_items
                            for dependency_id in (
                                item.unresolved_direct_dependency_record_ids
                            )
                        }
                    )
                ),
                tuple(
                    sorted(
                        {
                            dependency_role
                            for item in unresolved_items
                            for dependency_role in (
                                item.unresolved_direct_dependency_roles
                            )
                        }
                    )
                ),
            )
        )
    return tuple(result)


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableSignedControlGraphReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075PortableSignedControlTypedGraphV2 = field(repr=False)
    dependency_dag: V075PortableControlDependencyDAGV2 = field(repr=False)
    attestations: tuple[
        V075PortableControlRecordAttestationV2,
        ...,
    ]
    role_closures: tuple[V075PortableControlRoleClosureV2, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("M1B replay result is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "M1B result bundle"),
            (self.occurrence_id, "M1B result occurrence"),
            (
                self.public_context_closure_id,
                "M1B result public context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph)
            is not V075PortableSignedControlTypedGraphV2
            or type(self.dependency_dag)
            is not V075PortableControlDependencyDAGV2
            or type(self.attestations) is not tuple
            or not self.attestations
            or any(
                type(item) is not V075PortableControlRecordAttestationV2
                for item in self.attestations
            )
            or type(self.role_closures) is not tuple
            or any(
                type(item) is not V075PortableControlRoleClosureV2
                for item in self.role_closures
            )
            or tuple(item.role for item in self.role_closures)
            != CONTROL_ROLE_ORDER
            or len({item.record_id for item in self.attestations})
            != len(self.attestations)
        ):
            _fail("M1B replay result is malformed")
        self.typed_graph._assert_current()
        self.dependency_dag._assert_current()
        typed_graph_id = self.typed_graph._graph_id  # noqa: SLF001
        dependency_dag_id = self.dependency_dag._dag_id  # noqa: SLF001
        if (
            self.typed_graph.bundle_id != self.bundle_id
            or self.typed_graph.occurrence_id != self.occurrence_id
            or self.typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or self.dependency_dag.bundle_id != self.bundle_id
            or self.dependency_dag.m1a_result_id
            != self.typed_graph.m1a_result._result_id  # noqa: SLF001
            or self.dependency_dag.typed_graph_id
            != typed_graph_id
        ):
            _fail("M1B replay result crossed authority identities")
        bindings = {
            item.record_id: item
            for item in self.typed_graph.record_bindings
        }
        attestation_by_id = {
            item.record_id: item for item in self.attestations
        }
        nodes = {
            item.record_id: item for item in self.dependency_dag.nodes
        }
        if set(bindings) != set(attestation_by_id):
            _fail("M1B attestations differ from exact control records")
        recomputed_attestations: list[
            V075PortableControlRecordAttestationV2
        ] = []
        for record_id, binding in bindings.items():
            item = attestation_by_id[record_id]
            node = nodes.get(record_id)
            if node is None:
                _fail("M1B control record is absent from dependency DAG")
            binding._assert_current()
            item._assert_current()
            resolved = tuple(
                dependency_id
                for dependency_id in binding.dependency_record_ids
                if nodes[dependency_id].semantically_resolved
            )
            unresolved = tuple(
                dependency_id
                for dependency_id in binding.dependency_record_ids
                if not nodes[dependency_id].semantically_resolved
            )
            unresolved_roles = tuple(
                sorted(
                    {
                        nodes[dependency_id].role
                        for dependency_id in unresolved
                    }
                )
            )
            expected_status = (
                V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
                if node.semantically_resolved
                else V075PortableControlRoleClosureStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
            if (
                item.bundle_id != self.bundle_id
                or item.typed_graph_id != typed_graph_id
                or item.dependency_dag_id != dependency_dag_id
                or item.record_index != binding.record_index
                or item.role != binding.role
                or item.semantic_artifact_id
                != binding.semantic_artifact_id
                or item.canonical_artifact_sha256
                != hashlib.sha256(
                    binding.canonical_artifact_bytes
                ).hexdigest()
                or item.canonical_artifact_byte_count
                != len(binding.canonical_artifact_bytes)
                or item.direct_dependency_record_ids
                != binding.dependency_record_ids
                or item.resolved_direct_dependency_record_ids != resolved
                or item.unresolved_direct_dependency_record_ids
                != unresolved
                or item.unresolved_direct_dependency_roles
                != unresolved_roles
                or item.resolver_kind is not node.resolver_kind
                or item.status is not expected_status
            ):
                _fail("M1B attestation differs from graph/DAG reconstruction")
            recomputed_attestations.append(
                V075PortableControlRecordAttestationV2(
                    _ATTESTATION_ISSUER,
                    self.bundle_id,
                    typed_graph_id,
                    dependency_dag_id,
                    binding.record_id,
                    binding.record_index,
                    binding.role,
                    binding.semantic_artifact_id,
                    hashlib.sha256(
                        binding.canonical_artifact_bytes
                    ).hexdigest(),
                    len(binding.canonical_artifact_bytes),
                    binding.dependency_record_ids,
                    resolved,
                    unresolved,
                    unresolved_roles,
                    node.resolver_kind,
                    expected_status,
                )
            )

        expected_role_closures = _build_role_closures(
            bundle_id=self.bundle_id,
            typed_graph_id=typed_graph_id,
            dependency_dag_id=dependency_dag_id,
            records=tuple(
                sorted(
                    self.typed_graph.record_bindings,
                    key=lambda item: item.record_index,
                )
            ),
            attestations=tuple(recomputed_attestations),
        )
        if (
            tuple(item.to_document() for item in self.role_closures)
            != tuple(item.to_document() for item in expected_role_closures)
        ):
            _fail("M1B role closure summary is stale or overclaims")

        verification_ids = {
            item.record_id
            for item in self.typed_graph.m1a_result.typed_graph.record_bindings
            if item.role == m1a.M1A_VERIFICATION_ROLE
        }
        if (
            len(verification_ids) != 1
            or any(
                verification_id
                in item.resolved_direct_dependency_record_ids
                for item in self.attestations
                for verification_id in verification_ids
            )
        ):
            _fail("M1B consumed M1A's unresolved private verification claim")

    @property
    def control_structure_complete(self) -> bool:
        return bool(self.attestations) and all(
            item.to_document()["control_structure_reconstructed"]
            for item in self.attestations
        )

    @property
    def present_roles_semantically_complete(self) -> bool:
        return all(
            item.status
            is V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
            for item in self.role_closures
            if item.present_in_occurrence
        )

    @property
    def all_registered_roles_covered(self) -> bool:
        return all(item.present_in_occurrence for item in self.role_closures)

    def _payload(self) -> dict[str, Any]:
        role_statuses = {
            item.role: item.status.value for item in self.role_closures
        }
        absent_roles = [
            item.role
            for item in self.role_closures
            if not item.present_in_occurrence
        ]
        unresolved_present_roles = [
            item.role
            for item in self.role_closures
            if item.present_in_occurrence
            and item.status
            is not V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
        ]
        return {
            "schema": (
                "acfqp.v075_portable_signed_control_graph_replay.v2"
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
            "m0_result_id": (
                self.typed_graph.m1a_result.typed_graph.m0_result._result_id
            ),
            "m1a_result_id": (
                self.typed_graph.m1a_result._result_id  # noqa: SLF001
            ),
            "m1a_typed_graph_id": (
                self.typed_graph.m1a_result.typed_graph._graph_id
            ),
            "m1b_typed_graph_id": (
                self.typed_graph._graph_id  # noqa: SLF001
            ),
            "m1b_dependency_dag_id": (
                self.dependency_dag._dag_id  # noqa: SLF001
            ),
            "dependency_node_count": len(self.dependency_dag.nodes),
            "dependency_edge_count": sum(
                len(item.direct_dependency_record_ids)
                for item in self.dependency_dag.nodes
            ),
            "dependency_proof_shape": (
                "ITERATIVE_TOPOLOGICAL_DIRECT_EDGE_DAG"
            ),
            "transitive_closure_materialized": False,
            "recursive_dependency_walk_used": False,
            "control_role_order": list(CONTROL_ROLE_ORDER),
            "role_closure_statuses": role_statuses,
            "role_closure_ids": [
                item._closure_id for item in self.role_closures  # noqa: SLF001
            ],
            "present_role_count": sum(
                item.present_in_occurrence for item in self.role_closures
            ),
            "registered_role_count": len(CONTROL_ROLE_ORDER),
            "absent_roles": absent_roles,
            "unresolved_present_roles": unresolved_present_roles,
            "control_record_ids": [
                item.record_id for item in self.attestations
            ],
            "control_attestation_ids": [
                item._attestation_id for item in self.attestations  # noqa: SLF001
            ],
            "control_record_count": len(self.attestations),
            "control_structure_complete": (
                self.control_structure_complete
            ),
            "present_roles_semantically_complete": (
                self.present_roles_semantically_complete
            ),
            "all_registered_roles_covered": (
                self.all_registered_roles_covered
            ),
            "all_registered_roles_semantically_complete": (
                self.all_registered_roles_covered
                and self.present_roles_semantically_complete
            ),
            "not_present_is_not_native_zero": True,
            "not_present_is_not_completion_evidence": True,
            "root_semantic_authority_resolved_against_m0": True,
            "child_semantic_authority_status": (
                "NOT_PRESENT_OR_OPAQUE_DEFERRED"
            ),
            "promotion_semantic_authority_status": (
                "NOT_PRESENT_OR_OPAQUE_DEFERRED"
            ),
            "m1a_closure_verification_status": (
                "UNRESOLVED_PRIVATE_REPLAY_CLAIM"
            ),
            "m1a_private_verification_claim_consumed": False,
            "private_replay_performed": False,
            "private_verifier_called": False,
            "private_input_channels_allowed": False,
            "producer_typed_control_objects_reconstructed": True,
            "public_control_signatures_replayed": True,
            "head_intent_append_recurrence_replayed": True,
            "same_implementation_control_replay_used": True,
            "independent_control_verifier_provided": False,
            "opaque_semantic_authority_upgraded": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "portable_semantic_registry_complete": False,
            "observer_opened": False,
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
            _fail("M1B replay result identity is stale")

    @property
    def result_id(self) -> str:
        self._assert_current()
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            **self._payload(),
            "role_closures": [
                item.to_document() for item in self.role_closures
            ],
            "attestations": [
                item.to_document() for item in self.attestations
            ],
            "result_id": self._result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_OUTPUT_BYTES:
            _fail("M1B replay result exceeds its output byte cap")
        return raw


def _upstream_public_record_ids(
    result: m1a.V075PortableSignedBatchGraphReplayV2,
) -> frozenset[str]:
    """Use M1A's compact recomputation, never a cached aggregate flag."""

    result._assert_current()  # noqa: SLF001
    nodes = result.dependency_resolution_dag.nodes
    resolved = {
        item.record_id for item in nodes if item.jointly_resolved
    }
    verification_ids = {
        item.record_id
        for item in result.typed_graph.record_bindings
        if item.role == m1a.M1A_VERIFICATION_ROLE
    }
    if (
        len(verification_ids) != 1
        or resolved & verification_ids
    ):
        _fail("M1B upstream set attempts to consume private verification")
    return frozenset(resolved)


def replay_v075_portable_signed_control_graph_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
) -> V075PortableSignedControlGraphReplayV2:
    """Replay M1B from raw public authorities and no private channels."""

    if (
        type(portable_bundle_bytes) is not bytes
        or type(public_context_closure_bytes) is not bytes
    ):
        _fail("M1B accepts canonical raw byte authorities only")
    try:
        bundle = (
            portable
            .verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
    except Exception as error:
        raise V075PortableSignedControlGraphV2InvariantViolation(
            "M1B portable bundle failed raw replay"
        ) from error
    try:
        m1a_result = m1a.replay_v075_portable_signed_batch_graph_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
        )
    except Exception as error:
        raise V075PortableSignedControlGraphV2InvariantViolation(
            "M1B hardened M1A authority failed raw replay"
        ) from error
    if (
        bundle.bundle_id != m1a_result.bundle_id
        or bundle.occurrence_id != m1a_result.occurrence_id
    ):
        _fail("M1B portable bundle and M1A identities differ")
    roles = _records_by_role(bundle)
    for role in GENERIC_CONTROL_ROLE_ORDER:
        if not roles.get(role):
            _fail(f"M1B portable occurrence omits mandatory {role}")

    binding = m1a_result.typed_graph.b1_result.observer_open_binding
    batch_closure = m1a_result.typed_graph.closure
    heads = _reconstruct_heads(
        records=roles["SIGNED_CONTROL_JOURNAL_HEAD"],
        binding=binding,
        expected_entry_count=len(batch_closure.entries),
    )
    heads_by_id = {item.head_id: item for item in heads}
    if len(heads_by_id) != len(heads):
        _fail("M1B signed heads alias one identity")

    authority_records = tuple(
        item
        for role in (
            "CONTROLLED_ROOT_SEMANTIC_AUTHORITY",
            "CONTROLLED_CHILD_SEMANTIC_AUTHORITY",
            "CONTROLLED_PROMOTION_SEMANTIC_AUTHORITY",
        )
        for item in roles.get(role, ())
    )
    authorities = _reconstruct_semantic_authorities(
        records=authority_records,
    )
    authorities_by_id = {
        item.binding_id: item for item in authorities
    }
    if not authorities or len(authorities_by_id) != len(authorities):
        _fail("M1B semantic authorities are empty or identity-aliased")

    intent_records = tuple(
        item
        for role in (
            "CONTROLLED_ROOT_INTENT",
            "CONTROLLED_CHILD_INTENT",
            "CONTROLLED_PROMOTION_INTENT",
        )
        for item in roles.get(role, ())
    )
    intents = _reconstruct_intents(
        records=intent_records,
        heads_by_id=heads_by_id,
        authorities_by_id=authorities_by_id,
        streams_by_id=(
            m1a_result.typed_graph.m0_result.typed_graph.streams_by_id
        ),
    )
    intents_by_id = {item.intent_id: item for item in intents}
    if not intents or len(intents_by_id) != len(intents):
        _fail("M1B intents are empty or identity-aliased")

    receipts = _reconstruct_receipts(
        records=roles["SIGNED_APPEND_RECEIPT"],
        binding=binding,
    )
    receipts_by_id = {item.receipt_id: item for item in receipts}
    if len(receipts_by_id) != len(receipts):
        _fail("M1B receipts alias one identity")
    batches_by_id = {
        item.batch_id: item for item in m1a_result.typed_graph.batches
    }
    if len(batches_by_id) != len(m1a_result.typed_graph.batches):
        _fail("M1B M1A batches alias one identity")

    append_records = tuple(
        item
        for role in (
            "CONTROLLED_ROOT_APPEND",
            "CONTROLLED_CHILD_APPEND",
            "CONTROLLED_PROMOTION_APPEND",
        )
        for item in roles.get(role, ())
    )
    appends = _reconstruct_appends(
        records=append_records,
        heads_by_id=heads_by_id,
        intents_by_id=intents_by_id,
        batches_by_id=batches_by_id,
        receipts_by_id=receipts_by_id,
    )
    appends_by_receipt_id = {
        item.receipt.receipt_id: item for item in appends
    }
    if (
        not appends
        or len(appends_by_receipt_id) != len(appends)
        or len(appends) != len(batch_closure.entries)
    ):
        _fail("M1B appends are missing, aliased, or journal-incomplete")
    root_authority_record_ids = _validate_root_semantic_authority_bindings(
        authority_records=authority_records,
        appends=appends,
        m1a_result=m1a_result,
    )

    freezes = _reconstruct_support_freezes(
        records=roles["CONTROLLED_COMPLETE_SUPPORT_FREEZE"],
        appends_by_receipt_id=appends_by_receipt_id,
        heads_by_id=heads_by_id,
        evidence_by_id=(
            m1a_result.typed_graph.m0_result.typed_graph.evidence_by_id
        ),
    )
    freezes_by_id = {item.freeze_id: item for item in freezes}
    if len(freezes_by_id) != len(freezes):
        _fail("M1B support freezes alias one identity")

    for authority in authorities:
        if (
            authority.support_freeze_id is not None
            and authority.support_freeze_id not in freezes_by_id
        ):
            _fail("M1B validation semantic authority cites a foreign freeze")

    open_prefixes = _reconstruct_open_prefixes(
        records=roles["OPEN_CONTROLLED_PREFIX_VERIFICATION"],
        heads_by_id=heads_by_id,
        appends_by_receipt_id=appends_by_receipt_id,
        freezes_by_id=freezes_by_id,
    )
    control_closure = _reconstruct_control_closure(
        record=_sole_record(roles, "SIGNED_CONTROL_CLOSURE"),
        binding=binding,
    )
    reconciliation, controlled_closure = _reconstruct_final_control_graph(
        roles=roles,
        m1a_result=m1a_result,
        heads=heads,
        appends=appends,
        freezes=freezes,
        control_closure=control_closure,
    )
    bindings = _control_record_bindings(bundle.records)
    typed_graph = V075PortableSignedControlTypedGraphV2(
        _TYPED_GRAPH_ISSUER,
        bundle.bundle_id,
        m1a_result.public_context_closure_id,
        bundle.occurrence_id,
        m1a_result,
        heads,
        authorities,
        intents,
        receipts,
        appends,
        freezes,
        open_prefixes,
        control_closure,
        reconciliation,
        controlled_closure,
        bindings,
    )

    nodes = _iterative_control_dependency_nodes(
        records=bundle.records,
        upstream_public_record_ids=_upstream_public_record_ids(m1a_result),
        structurally_replayed_control_record_ids=frozenset(
            item.record_id for item in bindings
        ),
        root_semantic_authority_record_ids=root_authority_record_ids,
    )
    dag = V075PortableControlDependencyDAGV2(
        _DAG_ISSUER,
        bundle.bundle_id,
        m1a_result._result_id,  # noqa: SLF001
        typed_graph._graph_id,  # noqa: SLF001
        nodes,
    )
    attestations = _build_record_attestations(
        bundle=bundle,
        typed_graph=typed_graph,
        dag=dag,
    )
    role_closures = _build_role_closures(
        bundle_id=bundle.bundle_id,
        typed_graph_id=typed_graph._graph_id,  # noqa: SLF001
        dependency_dag_id=dag._dag_id,  # noqa: SLF001
        records=bundle.records,
        attestations=attestations,
    )
    return V075PortableSignedControlGraphReplayV2(
        _RESULT_ISSUER,
        bundle.bundle_id,
        bundle.occurrence_id,
        m1a_result.public_context_closure_id,
        typed_graph,
        dag,
        attestations,
        role_closures,
    )


def open_v075_production_from_portable_signed_control_graph_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortableSignedControlGraphProductionV2NotReady(
        "M1B replays the public control structure with the producer's "
        "same-implementation verifier; CHILD/PROMOTION semantic authorities, "
        "independent verification, source/code authority, and the production "
        "registry remain incomplete"
    )


__all__ = [
    "CHILD_CONTROL_ROLE_ORDER",
    "CODE_PROVENANCE_COMPLETE",
    "CONTROL_ROLE_ORDER",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "GENERIC_CONTROL_ROLE_ORDER",
    "INDEPENDENT_CONTROL_VERIFIER_PROVIDED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "M1A_PRIVATE_VERIFICATION_CLAIM_CONSUMED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRIVATE_INPUT_CHANNELS_ALLOWED",
    "PRIVATE_REPLAY_PERFORMED",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROMOTION_CONTROL_ROLE_ORDER",
    "PROPOSED_CONTRACT_VERSION",
    "ROOT_CONTROL_ROLE_ORDER",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "V075PortableControlDependencyDAGV2",
    "V075PortableControlDependencyNodeV2",
    "V075PortableControlRecordAttestationV2",
    "V075PortableControlRoleClosureStatusV2",
    "V075PortableControlRoleClosureV2",
    "V075PortableSignedControlGraphProductionV2NotReady",
    "V075PortableSignedControlGraphReplayV2",
    "V075PortableSignedControlGraphV2InvariantViolation",
    "V075PortableSignedControlTypedGraphV2",
    "open_v075_production_from_portable_signed_control_graph_v2",
    "replay_v075_portable_signed_control_graph_v2",
]
