"""Public M2 lineage authority for the V0-075 portable occurrence graph.

This construction-only cut starts with the hardened M2 root-boundary replay,
then adds exact public semantic authorities for three registered roles:

* ``BATCH_PUBLIC_VERIFICATION``;
* ``BATCH_SEQUENCE_VERIFICATION``;
* ``CONSTRUCTION_LINEAGE``.

The first two roles are reconstructed from the signed batches already exposed
by M1A.  The construction-lineage *document* is reconstructed field by field
from M0, M1A, and the verified public-context commitments.  Its private-law
closure-verification dependency is deliberately not consumed, so the lineage
role remains structurally unresolved.  This module never accepts a private
salt, private environment, private verification object, or held-out input.
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
from acfqp import v075_batched_observer_authority_v2 as lineage
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_public_context_closure_v2 as public_context
from acfqp import v075_portable_root_boundary_authority_v2 as m2
from acfqp import v075_portable_signed_batch_graph_authority_v2 as m1a


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.73.0"
PROFILE_KEY = "v075_portable_public_lineage_authority_v2"

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
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_M2_PUBLIC_LINEAGE_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "M2_PUBLIC_LINEAGE_REPLAYED_PRIVATE_CLOSURE_VERIFICATION_UNRESOLVED"
)
MAX_OUTPUT_BYTES = 64 * 1024 * 1024

ROLE_ORDER = (
    "BATCH_PUBLIC_VERIFICATION",
    "BATCH_SEQUENCE_VERIFICATION",
    "CONSTRUCTION_LINEAGE",
)
_ROLE_SET = frozenset(ROLE_ORDER)
_ROLE_SCHEMA = MappingProxyType(
    {
        "BATCH_PUBLIC_VERIFICATION": (
            "acfqp.v075_batch_public_verification.v2"
        ),
        "BATCH_SEQUENCE_VERIFICATION": (
            "acfqp.v075_batch_sequence_verification.v2"
        ),
        "CONSTRUCTION_LINEAGE": (
            "acfqp.v075_batch_occurrence_lineage.v2"
        ),
    }
)
_ROLE_ID_FIELD = MappingProxyType(
    {
        "BATCH_PUBLIC_VERIFICATION": "verification_id",
        "BATCH_SEQUENCE_VERIFICATION": "verification_id",
        "CONSTRUCTION_LINEAGE": "lineage_id",
    }
)
_CONTEXT_ROLE_ORDER = (
    "PUBLIC_TARGET_TAPE_NAMESPACE",
    "OBSERVER_OPEN_AUTHORIZATION",
    "PRIVATE_REVEAL_VERIFICATION_ATTESTATION",
)

DOMAIN_TAGS = MappingProxyType(
    {
        "typed_graph": (
            "acfqp:v075-portable-public-lineage-typed-graph:v2"
        ),
        "dependency_dag": (
            "acfqp:v075-portable-public-lineage-dependency-dag:v2"
        ),
        "record_attestation": (
            "acfqp:v075-portable-public-lineage-record-attestation:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-public-lineage-role-closure:v2"
        ),
        "aggregate": (
            "acfqp:v075-portable-public-lineage-authority:v2"
        ),
    }
)

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 M2 public-lineage content domains overlap")


class V075PortablePublicLineageV2InvariantViolation(ValueError):
    """A raw role, public replay, identity, or dependency was invalid."""


class V075PortablePublicLineageProductionV2NotReady(RuntimeError):
    """The public-lineage construction cut cannot authorize production."""


class V075PortablePublicLineageRoleStatusV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED = (
        "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
    )
    NOT_PRESENT_IN_OCCURRENCE = "NOT_PRESENT_IN_OCCURRENCE"


class V075PortablePublicLineageResolverKindV2(str, Enum):
    UPSTREAM_M2_PUBLIC = "UPSTREAM_M2_PUBLIC"
    M2_BATCH_PUBLIC_VERIFICATION = "M2_BATCH_PUBLIC_VERIFICATION"
    M2_BATCH_SEQUENCE_VERIFICATION = "M2_BATCH_SEQUENCE_VERIFICATION"
    M2_CONSTRUCTION_LINEAGE_PUBLIC_PROJECTION = (
        "M2_CONSTRUCTION_LINEAGE_PUBLIC_PROJECTION"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


def _fail(message: str) -> NoReturn:
    raise V075PortablePublicLineageV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortablePublicLineageV2InvariantViolation(
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
        raise V075PortablePublicLineageV2InvariantViolation(
            str(error)
        ) from error


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V075PortablePublicLineageV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _raw(value: Any) -> bytes:
    return canonical_json_bytes(value.to_document())


def _context_commitments(
    closure: public_context.V075PortablePublicContextEvidenceClosureV2,
) -> tuple[tuple[str, str, str], ...]:
    if (
        type(closure)
        is not public_context.V075PortablePublicContextEvidenceClosureV2
    ):
        _fail("public-lineage context closure has a foreign producer type")
    result: list[tuple[str, str, str]] = []
    for expected_role, record in zip(
        _CONTEXT_ROLE_ORDER,
        closure.dependency_records,
        strict=True,
    ):
        role = getattr(record.role, "value", record.role)
        if role != expected_role:
            _fail("public-lineage context dependency order changed")
        result.append(
            (
                role,
                _cid(
                    record.semantic_artifact_id,
                    f"public-lineage {role} semantic artifact",
                ),
                hashlib.sha256(record.canonical_artifact_bytes).hexdigest(),
            )
        )
    return tuple(result)


def _group_batches_by_stream(
    batches: tuple[Any, ...],
) -> dict[str, tuple[Any, ...]]:
    grouped: dict[str, list[Any]] = {}
    for batch in batches:
        grouped.setdefault(
            batch.request.stream_identity.stream_id,
            [],
        ).append(batch)
    return {key: tuple(values) for key, values in grouped.items()}


def _replay_public_verifications(
    batches: tuple[Any, ...],
) -> tuple[lineage.V075BatchPublicVerificationV2, ...]:
    try:
        return tuple(
            lineage.verify_v075_signed_observation_batch_v2(batch)
            for batch in batches
        )
    except Exception as error:
        raise V075PortablePublicLineageV2InvariantViolation(
            "M2 public batch verification replay failed"
        ) from error


def _replay_sequence_verifications(
    batches: tuple[Any, ...],
) -> tuple[lineage.V075BatchSequenceVerificationV2, ...]:
    groups = _group_batches_by_stream(batches)
    if not groups:
        _fail("M2 public-lineage sequence registry is empty")
    try:
        return tuple(
            lineage.verify_v075_observation_batch_sequence_v2(
                groups[stream_id]
            )
            for stream_id in sorted(groups)
        )
    except Exception as error:
        raise V075PortablePublicLineageV2InvariantViolation(
            "M2 public batch-sequence replay failed"
        ) from error


def _m1a_graph(
    upstream: m2.V075PortableRootBoundaryReplayV2,
    *,
    _upstream_already_current: bool = False,
) -> Any:
    if type(upstream) is not m2.V075PortableRootBoundaryReplayV2:
        _fail("public-lineage authority requires the exact hardened M2 type")
    if not _upstream_already_current:
        upstream._assert_current()  # noqa: SLF001
    return (
        upstream.typed_graph.m1b_result.typed_graph.m1a_result.typed_graph
    )


def _private_verification_binding(graph: Any) -> Any:
    matches = tuple(
        item
        for item in graph.record_bindings
        if item.role == m1a.M1A_VERIFICATION_ROLE
    )
    if len(matches) != 1:
        _fail("M2 public lineage requires one unresolved M1A verification")
    return matches[0]


def _expected_construction_lineage_document(
    *,
    upstream: m2.V075PortableRootBoundaryReplayV2,
    public_verifications: tuple[
        lineage.V075BatchPublicVerificationV2,
        ...,
    ],
    sequence_verifications: tuple[
        lineage.V075BatchSequenceVerificationV2,
        ...,
    ],
    context_commitments: tuple[tuple[str, str, str], ...],
    _upstream_already_current: bool = False,
) -> dict[str, Any]:
    """Derive the exact public lineage payload without private-law replay."""

    graph = _m1a_graph(
        upstream,
        _upstream_already_current=_upstream_already_current,
    )
    m0_graph = graph.m0_result.typed_graph
    occurrence = m0_graph.occurrence
    closure = graph.closure
    batches = graph.batches
    verification_binding = _private_verification_binding(graph)
    commitments = {
        role: (semantic_id, digest)
        for role, semantic_id, digest in context_commitments
    }
    if tuple(commitments) != _CONTEXT_ROLE_ORDER:
        _fail("public-lineage context commitments are incomplete or reordered")
    namespace_id, namespace_sha256 = commitments[
        "PUBLIC_TARGET_TAPE_NAMESPACE"
    ]
    authorization_id, authorization_sha256 = commitments[
        "OBSERVER_OPEN_AUTHORIZATION"
    ]
    reveal_id, reveal_sha256 = commitments[
        "PRIVATE_REVEAL_VERIFICATION_ATTESTATION"
    ]
    binding = closure.authority_binding
    if (
        occurrence.occurrence_id != upstream.occurrence_id
        or closure.occurrence_id != upstream.occurrence_id
        or occurrence.target_tape_namespace_id
        != binding.namespace.target_tape_namespace_id
        or namespace_id != occurrence.target_tape_namespace_id
        or authorization_id != binding.authorization_id
        or reveal_id != binding.private_reveal_attestation_id
        or hashlib.sha256(
            canonical_json_bytes(binding.namespace.to_document())
        ).hexdigest()
        != namespace_sha256
        or any(
            item.request.occurrence_id != occurrence.occurrence_id
            or item.request.stream_identity.target_tape_namespace_id
            != occurrence.target_tape_namespace_id
            or item.request.stream_identity.context_id
            != occurrence.context_id
            or item.request.stream_identity.arm != occurrence.arm.value
            for item in batches
        )
        or tuple(item.batch_id for item in batches)
        != tuple(item.batch_id for item in public_verifications)
    ):
        _fail("M2 public lineage crossed occurrence/context/batch identities")
    groups = _group_batches_by_stream(batches)
    if tuple(sorted(groups)) != tuple(
        item.stream_id for item in sequence_verifications
    ):
        _fail(
            "M2 public lineage sequence registry differs from signed batches"
        )

    payload: dict[str, Any] = {
        "schema": "acfqp.v075_batch_occurrence_lineage.v2",
        "schema_version": lineage.SCHEMA_VERSION,
        "proposed_contract_version": lineage.PROPOSED_CONTRACT_VERSION,
        "profile_key": lineage.PROFILE_KEY,
        "scope": (
            lineage.V075BatchOccurrenceAuthorityScopeV2
            .CONSTRUCTION_ONLY.value
        ),
        "occurrence_identity": occurrence.to_document(),
        "occurrence_id": occurrence.occurrence_id,
        "target_tape_namespace_id": occurrence.target_tape_namespace_id,
        "context_id": occurrence.context_id,
        "arm": occurrence.arm.value,
        "observer_session_public_id": closure.session_public_id,
        "observer_open_binding_id": binding.binding_id,
        "observer_open_authorization_id": binding.authorization_id,
        "private_reveal_attestation_id": (
            binding.private_reveal_attestation_id
        ),
        "remote_main_anchor_id": binding.remote_main_anchor_id,
        "closure_id": closure.closure_id,
        # Only the content identity is linked.  The private replay payload is
        # neither read nor instantiated by this authority.
        "closure_verification_id": (
            verification_binding.semantic_artifact_id
        ),
        "journal_entry_ids": [
            item.entry_id for item in closure.entries
        ],
        "batch_ids": [item.batch_id for item in batches],
        "batch_public_verification_ids": [
            item.verification_id for item in public_verifications
        ],
        "batch_sequence_verification_ids": [
            item.verification_id for item in sequence_verifications
        ],
        "accepted_draw_count": sum(
            item.request.accepted_draw_count for item in batches
        ),
        "batch_count": len(batches),
        "stream_count": len(sequence_verifications),
        "rsa_batch_signature_count": len(batches),
        "rsa_closure_signature_count": 1,
        "per_draw_record_count": 0,
        "per_draw_signature_count": 0,
        "private_reveal_attestation_bytes_sha256": reveal_sha256,
        "authorization_bytes_sha256": authorization_sha256,
        "namespace_bytes_sha256": namespace_sha256,
        "closure_bytes_sha256": hashlib.sha256(
            closure.canonical_bytes
        ).hexdigest(),
        "production_authority_bytes_replayed": False,
        "authority_version": "V2",
        "namespace_version": "V2",
        "legacy_v1_authority_projection_used": False,
        "legacy_v1_namespace_projection_used": False,
        "private_material_serialized": False,
        "official_execution_unlocked": False,
        "scientific_endpoint_credit_allowed": False,
    }
    return {
        **payload,
        "lineage_id": lineage._hash(  # noqa: SLF001
            "occurrence_lineage",
            payload,
        ),
    }


_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class _PublicLineageRecordBindingV2:
    _issuer: InitVar[object]
    record_id: str
    record_index: int
    role: str
    artifact_schema: str
    semantic_artifact_id: str
    dependency_record_ids: tuple[str, ...]
    canonical_artifact_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BINDING_ISSUER:
            _fail("public-lineage record binding is caller-minted")
        self._assert_current()

    def _assert_current(self) -> None:
        _cid(self.record_id, "public-lineage record")
        _cid(self.semantic_artifact_id, "public-lineage semantic artifact")
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _ROLE_SET
            or self.artifact_schema != _ROLE_SCHEMA[self.role]
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
        ):
            _fail("public-lineage record binding is malformed")
        for value in self.dependency_record_ids:
            _cid(value, "public-lineage record dependency")
        document = _strict_document(
            self.canonical_artifact_bytes,
            label=f"public-lineage {self.role}",
        )
        if (
            document.get("schema") != self.artifact_schema
            or document.get(_ROLE_ID_FIELD[self.role])
            != self.semantic_artifact_id
        ):
            _fail("public-lineage record bytes are schema/role-transplanted")
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
            _fail("public-lineage portable record ID is stale or rehashed")

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


def _binding_from_record(record: Any) -> _PublicLineageRecordBindingV2:
    return _PublicLineageRecordBindingV2(
        _BINDING_ISSUER,
        record.record_id,
        record.index,
        record.role,
        record.artifact_schema,
        record.semantic_artifact_id,
        tuple(record.dependency_record_ids),
        record.canonical_artifact_bytes,
    )


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePublicLineageTypedGraphV2:
    _issuer: InitVar[object]
    bundle_id: str
    public_context_closure_id: str
    occurrence_id: str
    repository_root: str = field(repr=False)
    public_context_closure_bytes: bytes = field(repr=False)
    m2_result: m2.V075PortableRootBoundaryReplayV2 = field(repr=False)
    context_commitments: tuple[tuple[str, str, str], ...]
    public_verifications: tuple[
        lineage.V075BatchPublicVerificationV2,
        ...,
    ] = field(repr=False)
    sequence_verifications: tuple[
        lineage.V075BatchSequenceVerificationV2,
        ...,
    ] = field(repr=False)
    record_bindings: tuple[_PublicLineageRecordBindingV2, ...] = field(
        repr=False
    )
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("M2 public-lineage typed graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._identity_payload()),
        )

    def _expected_documents_by_role(
        self,
        *,
        _upstream_already_current: bool = False,
    ) -> Mapping[str, dict[str, bytes]]:
        lineage_document = _expected_construction_lineage_document(
            upstream=self.m2_result,
            public_verifications=self.public_verifications,
            sequence_verifications=self.sequence_verifications,
            context_commitments=self.context_commitments,
            _upstream_already_current=_upstream_already_current,
        )
        return MappingProxyType(
            {
                "BATCH_PUBLIC_VERIFICATION": {
                    item.verification_id: _raw(item)
                    for item in self.public_verifications
                },
                "BATCH_SEQUENCE_VERIFICATION": {
                    item.verification_id: _raw(item)
                    for item in self.sequence_verifications
                },
                "CONSTRUCTION_LINEAGE": {
                    lineage_document["lineage_id"]: canonical_json_bytes(
                        lineage_document
                    )
                },
            }
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "public-lineage typed graph bundle"),
            (
                self.public_context_closure_id,
                "public-lineage typed graph context",
            ),
            (self.occurrence_id, "public-lineage typed graph occurrence"),
        ):
            _cid(value, label)
        if (
            type(self.m2_result)
            is not m2.V075PortableRootBoundaryReplayV2
            or type(self.repository_root) is not str
            or not self.repository_root
            or type(self.public_context_closure_bytes) is not bytes
            or not self.public_context_closure_bytes
            or type(self.context_commitments) is not tuple
            or tuple(item[0] for item in self.context_commitments)
            != _CONTEXT_ROLE_ORDER
            or any(
                type(item) is not tuple
                or len(item) != 3
                or type(item[0]) is not str
                for item in self.context_commitments
            )
            or type(self.public_verifications) is not tuple
            or not self.public_verifications
            or any(
                type(item) is not lineage.V075BatchPublicVerificationV2
                for item in self.public_verifications
            )
            or type(self.sequence_verifications) is not tuple
            or not self.sequence_verifications
            or any(
                type(item) is not lineage.V075BatchSequenceVerificationV2
                for item in self.sequence_verifications
            )
            or type(self.record_bindings) is not tuple
            or not self.record_bindings
            or any(
                type(item) is not _PublicLineageRecordBindingV2
                for item in self.record_bindings
            )
            or tuple(item.record_index for item in self.record_bindings)
            != tuple(
                sorted(item.record_index for item in self.record_bindings)
            )
            or len({item.record_id for item in self.record_bindings})
            != len(self.record_bindings)
        ):
            _fail("M2 public-lineage typed graph is malformed")
        self.m2_result._assert_current()  # noqa: SLF001
        try:
            context_closure = (
                public_context
                .verify_v075_portable_public_context_evidence_closure_bytes_v2(
                    repository_root=Path(self.repository_root),
                    raw=self.public_context_closure_bytes,
                )
            )
        except Exception as error:
            raise V075PortablePublicLineageV2InvariantViolation(
                "M2 public-lineage context bytes changed on replay"
            ) from error
        if (
            self.m2_result.bundle_id != self.bundle_id
            or self.m2_result.public_context_closure_id
            != self.public_context_closure_id
            or self.m2_result.occurrence_id != self.occurrence_id
            or context_closure.closure_id
            != self.public_context_closure_id
            or _context_commitments(context_closure)
            != self.context_commitments
        ):
            _fail("M2 public-lineage typed graph crossed M2 identities")
        for role, semantic_id, digest in self.context_commitments:
            if role not in _CONTEXT_ROLE_ORDER:
                _fail("M2 public-lineage context role is unknown")
            _cid(semantic_id, f"M2 public-lineage {role} semantic ID")
            _cid(digest, f"M2 public-lineage {role} byte digest")

        graph = _m1a_graph(
            self.m2_result,
            _upstream_already_current=True,
        )
        expected_public = _replay_public_verifications(graph.batches)
        expected_sequences = _replay_sequence_verifications(graph.batches)
        if (
            tuple(item.to_document() for item in self.public_verifications)
            != tuple(item.to_document() for item in expected_public)
            or tuple(
                item.to_document() for item in self.sequence_verifications
            )
            != tuple(item.to_document() for item in expected_sequences)
        ):
            _fail("M2 public-lineage producer replay changed")

        expected = self._expected_documents_by_role(
            _upstream_already_current=True,
        )
        actual: dict[str, dict[str, bytes]] = {
            role: {} for role in ROLE_ORDER
        }
        m2_nodes = {
            item.record_id: item
            for item in self.m2_result.dependency_dag.nodes
        }
        for binding in self.record_bindings:
            binding._assert_current()
            node = m2_nodes.get(binding.record_id)
            if (
                node is None
                or node.record_index != binding.record_index
                or node.role != binding.role
                or node.direct_dependency_record_ids
                != binding.dependency_record_ids
            ):
                _fail(
                    "M2 public-lineage record binding differs from the "
                    "hardened M2 spine"
                )
            by_id = actual[binding.role]
            if binding.semantic_artifact_id in by_id:
                _fail("M2 public-lineage semantic artifact is duplicated")
            by_id[binding.semantic_artifact_id] = (
                binding.canonical_artifact_bytes
            )
        if actual != expected:
            _fail(
                "M2 public-lineage records differ from exact public producer "
                "reconstruction"
            )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_public_lineage_typed_graph.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "public_context_closure_id": self.public_context_closure_id,
            "public_context_closure_sha256": hashlib.sha256(
                self.public_context_closure_bytes
            ).hexdigest(),
            "public_context_closure_byte_count": len(
                self.public_context_closure_bytes
            ),
            "occurrence_id": self.occurrence_id,
            "hardened_m2_result_id": self.m2_result._result_id,  # noqa: SLF001
            "hardened_m2_dependency_dag_id": (
                self.m2_result.dependency_dag._dag_id  # noqa: SLF001
            ),
            "context_commitments": [
                {
                    "role": role,
                    "semantic_artifact_id": semantic_id,
                    "canonical_artifact_sha256": digest,
                }
                for role, semantic_id, digest in self.context_commitments
            ],
            "batch_public_verification_ids": [
                item.verification_id for item in self.public_verifications
            ],
            "batch_sequence_verification_ids": [
                item.verification_id for item in self.sequence_verifications
            ],
            "construction_lineage_ids": [
                item.semantic_artifact_id
                for item in self.record_bindings
                if item.role == "CONSTRUCTION_LINEAGE"
            ],
            "ordered_record_commitments": [
                item.commitment_document() for item in self.record_bindings
            ],
            "batch_signatures_publicly_replayed": True,
            "stream_prefixes_publicly_replayed": True,
            "construction_lineage_public_payload_reconstructed": True,
            "private_closure_verification_payload_read": False,
            "private_replay_performed": False,
            "private_material_serialized": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._graph_id != _hash("typed_graph", self._identity_payload()):
            _fail("M2 public-lineage typed graph identity is stale")

    @property
    def graph_id(self) -> str:
        self._assert_current()
        return self._graph_id

    def __reduce__(self) -> NoReturn:
        raise TypeError("M2 public-lineage typed graph is in-memory-only")


@dataclass(frozen=True, slots=True)
class V075PortablePublicLineageDependencyNodeV2:
    record_id: str
    record_index: int
    role: str
    direct_dependency_record_ids: tuple[str, ...]
    resolver_kind: V075PortablePublicLineageResolverKindV2
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    dependency_depth: int

    def _assert_current(self) -> None:
        _cid(self.record_id, "public-lineage dependency node")
        sequences = (
            self.direct_dependency_record_ids,
            self.unresolved_frontier_record_ids,
        )
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
            or type(self.resolver_kind)
            is not V075PortablePublicLineageResolverKindV2
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
            _fail("M2 public-lineage dependency node is malformed")
        for value in (*self.direct_dependency_record_ids,
                      *self.unresolved_frontier_record_ids):
            _cid(value, "M2 public-lineage dependency edge")

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
) -> V075PortablePublicLineageResolverKindV2:
    return {
        "BATCH_PUBLIC_VERIFICATION": (
            V075PortablePublicLineageResolverKindV2
            .M2_BATCH_PUBLIC_VERIFICATION
        ),
        "BATCH_SEQUENCE_VERIFICATION": (
            V075PortablePublicLineageResolverKindV2
            .M2_BATCH_SEQUENCE_VERIFICATION
        ),
        "CONSTRUCTION_LINEAGE": (
            V075PortablePublicLineageResolverKindV2
            .M2_CONSTRUCTION_LINEAGE_PUBLIC_PROJECTION
        ),
    }[role]


def _iterative_public_lineage_dependency_nodes(
    *,
    upstream_nodes: tuple[Any, ...],
    locally_replayed_record_ids: frozenset[str],
) -> tuple[V075PortablePublicLineageDependencyNodeV2, ...]:
    """Extend the M2 direct-edge DAG iteratively; supports 4096-deep chains."""

    if (
        type(upstream_nodes) is not tuple
        or not upstream_nodes
        or type(locally_replayed_record_ids) is not frozenset
    ):
        _fail("M2 public-lineage dependency replay requires a nonempty DAG")
    for value in locally_replayed_record_ids:
        _cid(value, "M2 public-lineage local replay record")
    nodes: list[V075PortablePublicLineageDependencyNodeV2] = []
    resolved_by_id: dict[str, bool] = {}
    frontier_by_id: dict[str, tuple[str, ...]] = {}
    role_by_id: dict[str, str] = {}
    depth_by_id: dict[str, int] = {}
    for expected_index, upstream in enumerate(upstream_nodes):
        try:
            record_id = upstream.record_id
            record_index = upstream.record_index
            role = upstream.role
            dependencies = tuple(upstream.direct_dependency_record_ids)
            upstream_local = upstream.local_semantic_authority_resolved
            upstream_resolved = upstream.semantically_resolved
        except (AttributeError, TypeError) as error:
            raise V075PortablePublicLineageV2InvariantViolation(
                "M2 public-lineage upstream dependency node is malformed"
            ) from error
        if (
            record_index != expected_index
            or record_id in resolved_by_id
            or type(upstream_local) is not bool
            or type(upstream_resolved) is not bool
            or tuple(sorted(set(dependencies))) != dependencies
            or any(value not in resolved_by_id for value in dependencies)
        ):
            _fail(
                "M2 public-lineage dependency DAG is duplicated or "
                "non-topological"
            )
        if record_id in locally_replayed_record_ids:
            if role not in _ROLE_SET:
                _fail("local public-lineage record has a foreign role")
            resolver_kind = _target_resolver_kind(role)
            local_resolved = True
        elif upstream_local:
            resolver_kind = (
                V075PortablePublicLineageResolverKindV2.UPSTREAM_M2_PUBLIC
            )
            local_resolved = True
        else:
            resolver_kind = (
                V075PortablePublicLineageResolverKindV2
                .NO_REGISTERED_SEMANTIC_AUTHORITY
            )
            local_resolved = False
        semantically_resolved = local_resolved and all(
            resolved_by_id[value] for value in dependencies
        )
        if semantically_resolved:
            frontier: tuple[str, ...] = ()
        elif not local_resolved:
            frontier = (record_id,)
        else:
            frontier = tuple(
                sorted(
                    {
                        value
                        for dependency_id in dependencies
                        for value in frontier_by_id[dependency_id]
                    }
                )
            )
            if not frontier:
                _fail("unresolved public-lineage node has no proof frontier")
        depth = 1 + max(
            (depth_by_id[value] for value in dependencies),
            default=0,
        )
        node = V075PortablePublicLineageDependencyNodeV2(
            record_id,
            record_index,
            role,
            dependencies,
            resolver_kind,
            local_resolved,
            semantically_resolved,
            frontier,
            tuple(
                sorted(
                    {
                        role if value == record_id else role_by_id[value]
                        for value in frontier
                    }
                )
            ),
            depth,
        )
        node._assert_current()
        nodes.append(node)
        resolved_by_id[record_id] = semantically_resolved
        frontier_by_id[record_id] = frontier
        role_by_id[record_id] = role
        depth_by_id[record_id] = depth
    if not locally_replayed_record_ids <= resolved_by_id.keys():
        _fail("M2 public-lineage local registry contains foreign records")
    return tuple(nodes)


_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePublicLineageDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    m2_result: m2.V075PortableRootBoundaryReplayV2 = field(repr=False)
    typed_graph_id: str
    locally_replayed_record_ids: tuple[str, ...]
    nodes: tuple[V075PortablePublicLineageDependencyNodeV2, ...] = field(
        repr=False
    )
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("M2 public-lineage dependency DAG is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_dag_id",
            _hash("dependency_dag", self._payload()),
        )

    def _validate(self, *, _m2_already_current: bool = False) -> None:
        _cid(self.bundle_id, "public-lineage DAG bundle")
        _cid(self.typed_graph_id, "public-lineage DAG typed graph")
        if (
            type(self.m2_result)
            is not m2.V075PortableRootBoundaryReplayV2
            or type(self.locally_replayed_record_ids) is not tuple
            or tuple(sorted(set(self.locally_replayed_record_ids)))
            != self.locally_replayed_record_ids
            or type(self.nodes) is not tuple
            or not self.nodes
        ):
            _fail("M2 public-lineage dependency DAG is malformed")
        if not _m2_already_current:
            self.m2_result._assert_current()  # noqa: SLF001
        expected = _iterative_public_lineage_dependency_nodes(
            upstream_nodes=self.m2_result.dependency_dag.nodes,
            locally_replayed_record_ids=frozenset(
                self.locally_replayed_record_ids
            ),
        )
        for item in self.nodes:
            item._assert_current()
        if (
            self.m2_result.bundle_id != self.bundle_id
            or tuple(item.to_document() for item in self.nodes)
            != tuple(item.to_document() for item in expected)
        ):
            _fail("M2 public-lineage dependency DAG is stale or transplanted")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_public_lineage_dependency_dag.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "hardened_m2_result_id": self.m2_result._result_id,  # noqa: SLF001
            "hardened_m2_dependency_dag_id": (
                self.m2_result.dependency_dag._dag_id  # noqa: SLF001
            ),
            "m2_public_lineage_typed_graph_id": self.typed_graph_id,
            "locally_replayed_record_ids": list(
                self.locally_replayed_record_ids
            ),
            "nodes": [item.to_document() for item in self.nodes],
            "node_count": len(self.nodes),
            "edge_count": sum(
                len(item.direct_dependency_record_ids)
                for item in self.nodes
            ),
            "maximum_dependency_depth": max(
                item.dependency_depth for item in self.nodes
            ),
            "proof_shape": "ITERATIVE_TOPOLOGICAL_DIRECT_EDGE_DAG",
            "transitive_unresolved_frontier_derived": True,
            "transitive_closure_materialized": False,
            "recursive_dependency_walk_used": False,
        }

    def _assert_current(
        self,
        *,
        _m2_already_current: bool = False,
    ) -> None:
        self._validate(_m2_already_current=_m2_already_current)
        if self._dag_id != _hash("dependency_dag", self._payload()):
            _fail("M2 public-lineage dependency DAG identity is stale")

    @property
    def dag_id(self) -> str:
        self._assert_current()
        return self._dag_id

    @property
    def nodes_by_id(
        self,
    ) -> Mapping[str, V075PortablePublicLineageDependencyNodeV2]:
        self._assert_current()
        return MappingProxyType({item.record_id: item for item in self.nodes})


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePublicLineageRecordAttestationV2:
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
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    resolver_kind: V075PortablePublicLineageResolverKindV2
    status: V075PortablePublicLineageRoleStatusV2
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("M2 public-lineage attestation is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("record_attestation", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "public-lineage attestation bundle"),
            (self.typed_graph_id, "public-lineage attestation graph"),
            (self.dependency_dag_id, "public-lineage attestation DAG"),
            (self.record_id, "public-lineage attestation record"),
            (
                self.semantic_artifact_id,
                "public-lineage attestation artifact",
            ),
            (
                self.canonical_artifact_sha256,
                "public-lineage attestation digest",
            ),
        ):
            _cid(value, label)
        sequences = (
            self.direct_dependency_record_ids,
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
            or (
                set(self.resolved_direct_dependency_record_ids)
                | set(self.unresolved_direct_dependency_record_ids)
                != set(self.direct_dependency_record_ids)
            )
            or (
                set(self.resolved_direct_dependency_record_ids)
                & set(self.unresolved_direct_dependency_record_ids)
            )
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
            or type(self.resolver_kind)
            is not V075PortablePublicLineageResolverKindV2
            or type(self.status)
            is not V075PortablePublicLineageRoleStatusV2
            or self.status
            is V075PortablePublicLineageRoleStatusV2
            .NOT_PRESENT_IN_OCCURRENCE
        ):
            _fail("M2 public-lineage attestation is malformed")
        expected = (
            V075PortablePublicLineageRoleStatusV2.FULL_PUBLIC
            if not self.unresolved_frontier_record_ids
            else V075PortablePublicLineageRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        if self.status is not expected:
            _fail("M2 public-lineage attestation overclaims semantics")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_public_lineage_record_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m2_public_lineage_typed_graph_id": self.typed_graph_id,
            "m2_public_lineage_dependency_dag_id": self.dependency_dag_id,
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "semantic_artifact_id": self.semantic_artifact_id,
            "canonical_artifact_sha256": self.canonical_artifact_sha256,
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
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
            "resolver_kind": self.resolver_kind.value,
            "status": self.status.value,
            "producer_canonical_bytes_reconstructed": True,
            "producer_content_id_recomputed": True,
            "private_closure_verification_payload_read": False,
            "private_replay_performed": False,
            "official_execution_allowed": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._attestation_id != _hash(
            "record_attestation",
            self._payload(),
        ):
            _fail("M2 public-lineage attestation identity is stale")

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
    dag: V075PortablePublicLineageDependencyDAGV2,
    bindings: tuple[_PublicLineageRecordBindingV2, ...],
    _dag_already_current: bool = False,
) -> tuple[V075PortablePublicLineageRecordAttestationV2, ...]:
    if not _dag_already_current:
        dag._assert_current()
    nodes = {item.record_id: item for item in dag.nodes}
    result = []
    for binding in bindings:
        binding._assert_current()
        node = nodes[binding.record_id]
        resolved = tuple(
            value
            for value in binding.dependency_record_ids
            if nodes[value].semantically_resolved
        )
        unresolved = tuple(
            value
            for value in binding.dependency_record_ids
            if not nodes[value].semantically_resolved
        )
        status = (
            V075PortablePublicLineageRoleStatusV2.FULL_PUBLIC
            if node.semantically_resolved
            else V075PortablePublicLineageRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        result.append(
            V075PortablePublicLineageRecordAttestationV2(
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
                binding.dependency_record_ids,
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
class V075PortablePublicLineageRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    dependency_dag_id: str
    role: str
    status: V075PortablePublicLineageRoleStatusV2
    record_ids: tuple[str, ...]
    attestation_ids: tuple[str, ...]
    unresolved_record_ids: tuple[str, ...]
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("M2 public-lineage role closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "public-lineage closure bundle"),
            (self.typed_graph_id, "public-lineage closure graph"),
            (self.dependency_dag_id, "public-lineage closure DAG"),
        ):
            _cid(value, label)
        sequences = (
            self.record_ids,
            self.attestation_ids,
            self.unresolved_record_ids,
            self.unresolved_frontier_record_ids,
        )
        if (
            self.role not in _ROLE_SET
            or type(self.status)
            is not V075PortablePublicLineageRoleStatusV2
            or any(
                type(values) is not tuple
                or len(set(values)) != len(values)
                for values in sequences
            )
            or len(self.record_ids) != len(self.attestation_ids)
            or not set(self.unresolved_record_ids) <= set(self.record_ids)
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
        ):
            _fail("M2 public-lineage role closure is malformed")
        for value in (
            *self.record_ids,
            *self.attestation_ids,
            *self.unresolved_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "M2 public-lineage role closure identity")
        expected = (
            V075PortablePublicLineageRoleStatusV2
            .NOT_PRESENT_IN_OCCURRENCE
            if not self.record_ids
            else (
                V075PortablePublicLineageRoleStatusV2.FULL_PUBLIC
                if not self.unresolved_record_ids
                else V075PortablePublicLineageRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
        )
        if self.status is not expected:
            _fail("M2 public-lineage role closure status is inconsistent")
        if (
            self.status
            is V075PortablePublicLineageRoleStatusV2.FULL_PUBLIC
            and (
                self.unresolved_frontier_record_ids
                or self.unresolved_frontier_roles
            )
        ):
            _fail("full public-lineage role closure carries an unresolved set")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_public_lineage_role_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m2_public_lineage_typed_graph_id": self.typed_graph_id,
            "m2_public_lineage_dependency_dag_id": self.dependency_dag_id,
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
            _fail("M2 public-lineage role closure identity is stale")

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
    bindings: tuple[_PublicLineageRecordBindingV2, ...],
    attestations: tuple[
        V075PortablePublicLineageRecordAttestationV2,
        ...,
    ],
    _attestations_already_current: bool = False,
) -> tuple[V075PortablePublicLineageRoleClosureV2, ...]:
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
            is not V075PortablePublicLineageRoleStatusV2.FULL_PUBLIC
        )
        status = (
            V075PortablePublicLineageRoleStatusV2
            .NOT_PRESENT_IN_OCCURRENCE
            if not role_bindings
            else (
                V075PortablePublicLineageRoleStatusV2.FULL_PUBLIC
                if not unresolved
                else V075PortablePublicLineageRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
        )
        result.append(
            V075PortablePublicLineageRoleClosureV2(
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
class V075PortablePublicLineageReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075PortablePublicLineageTypedGraphV2 = field(repr=False)
    dependency_dag: V075PortablePublicLineageDependencyDAGV2 = field(
        repr=False
    )
    attestations: tuple[
        V075PortablePublicLineageRecordAttestationV2,
        ...,
    ]
    role_closures: tuple[V075PortablePublicLineageRoleClosureV2, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("M2 public-lineage result is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "public-lineage result bundle"),
            (self.occurrence_id, "public-lineage result occurrence"),
            (
                self.public_context_closure_id,
                "public-lineage result context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph)
            is not V075PortablePublicLineageTypedGraphV2
            or type(self.dependency_dag)
            is not V075PortablePublicLineageDependencyDAGV2
            or type(self.attestations) is not tuple
            or any(
                type(item)
                is not V075PortablePublicLineageRecordAttestationV2
                for item in self.attestations
            )
            or tuple(item.record_index for item in self.attestations)
            != tuple(
                sorted(item.record_index for item in self.attestations)
            )
            or type(self.role_closures) is not tuple
            or tuple(item.role for item in self.role_closures) != ROLE_ORDER
            or any(
                type(item) is not V075PortablePublicLineageRoleClosureV2
                for item in self.role_closures
            )
        ):
            _fail("M2 public-lineage result is malformed")
        self.typed_graph._assert_current()
        self.dependency_dag._assert_current(_m2_already_current=True)
        graph_id = self.typed_graph._graph_id
        dag_id = self.dependency_dag._dag_id
        if (
            self.typed_graph.bundle_id != self.bundle_id
            or self.typed_graph.occurrence_id != self.occurrence_id
            or self.typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or self.dependency_dag.bundle_id != self.bundle_id
            or self.dependency_dag.typed_graph_id != graph_id
            or self.dependency_dag.m2_result
            is not self.typed_graph.m2_result
        ):
            _fail("M2 public-lineage result crossed authority identities")
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
            _fail("M2 public-lineage attestations are stale or transplanted")
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
            _fail("M2 public-lineage role closures are stale or overclaim")
        status_by_role = {
            item.role: item.status for item in self.role_closures
        }
        if (
            status_by_role["BATCH_PUBLIC_VERIFICATION"]
            is not V075PortablePublicLineageRoleStatusV2.FULL_PUBLIC
            or status_by_role["BATCH_SEQUENCE_VERIFICATION"]
            is not V075PortablePublicLineageRoleStatusV2.FULL_PUBLIC
            or status_by_role["CONSTRUCTION_LINEAGE"]
            is not V075PortablePublicLineageRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        ):
            _fail("M2 public-lineage result has an invalid normative closure")
        private_ids = {
            item.record_id
            for item in (
                self.typed_graph.m2_result.typed_graph.m1b_result.typed_graph
                .m1a_result.typed_graph.record_bindings
            )
            if item.role == m1a.M1A_VERIFICATION_ROLE
        }
        nodes = {
            item.record_id: item for item in self.dependency_dag.nodes
        }
        if (
            len(private_ids) != 1
            or any(nodes[value].semantically_resolved for value in private_ids)
            or not private_ids
            <= set(
                next(
                    item
                    for item in self.role_closures
                    if item.role == "CONSTRUCTION_LINEAGE"
                ).unresolved_frontier_record_ids
            )
        ):
            _fail("M2 public-lineage result consumed private verification")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_public_lineage_authority.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "hardened_m2_result_id": (
                self.typed_graph.m2_result._result_id  # noqa: SLF001
            ),
            "m2_public_lineage_typed_graph_id": self.typed_graph._graph_id,
            "m2_public_lineage_dependency_dag_id": (
                self.dependency_dag._dag_id
            ),
            "role_order": list(ROLE_ORDER),
            "role_statuses": {
                item.role: item.status.value for item in self.role_closures
            },
            "record_attestation_ids": [
                item._attestation_id for item in self.attestations
            ],
            "role_closure_ids": [
                item._closure_id for item in self.role_closures
            ],
            "batch_public_verification_semantics_complete": True,
            "batch_sequence_verification_semantics_complete": True,
            "construction_lineage_public_projection_complete": True,
            "construction_lineage_private_law_replay_complete": False,
            "hardened_m2_called_before_local_bundle_replay": True,
            "private_verifier_called": False,
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
            _fail("M2 public-lineage result identity is stale")

    @property
    def result_id(self) -> str:
        self._assert_current()
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            **self._payload(),
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
            _fail("M2 public-lineage result exceeds output byte cap")
        return raw


def replay_v075_portable_public_lineage_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
) -> V075PortablePublicLineageReplayV2:
    """Replay public lineage roles from raw authorities, starting with M2."""

    if (
        type(portable_bundle_bytes) is not bytes
        or type(public_context_closure_bytes) is not bytes
    ):
        _fail("M2 public lineage accepts canonical raw byte authorities only")
    try:
        upstream = m2.replay_v075_portable_root_boundary_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
        )
    except Exception as error:
        raise V075PortablePublicLineageV2InvariantViolation(
            "M2 public lineage hardened root-boundary replay failed"
        ) from error
    try:
        bundle = (
            portable
            .verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
        context_closure = (
            public_context
            .verify_v075_portable_public_context_evidence_closure_bytes_v2(
                repository_root=repository_root,
                raw=public_context_closure_bytes,
            )
        )
    except Exception as error:
        raise V075PortablePublicLineageV2InvariantViolation(
            "M2 public lineage raw bundle/context replay failed after M2"
        ) from error
    if (
        bundle.bundle_id != upstream.bundle_id
        or bundle.occurrence_id != upstream.occurrence_id
        or context_closure.closure_id
        != upstream.public_context_closure_id
    ):
        _fail("M2 public-lineage raw authorities were transplanted")

    graph = _m1a_graph(upstream, _upstream_already_current=True)
    public_verifications = _replay_public_verifications(graph.batches)
    sequence_verifications = _replay_sequence_verifications(graph.batches)
    context_commitments = _context_commitments(context_closure)
    target_records = tuple(
        item for item in bundle.records if item.role in _ROLE_SET
    )
    bindings = tuple(_binding_from_record(item) for item in target_records)
    typed_graph = V075PortablePublicLineageTypedGraphV2(
        _TYPED_GRAPH_ISSUER,
        bundle.bundle_id,
        context_closure.closure_id,
        bundle.occurrence_id,
        str(Path(repository_root).resolve()),
        public_context_closure_bytes,
        upstream,
        context_commitments,
        public_verifications,
        sequence_verifications,
        bindings,
    )
    local_ids = tuple(sorted(item.record_id for item in bindings))
    nodes = _iterative_public_lineage_dependency_nodes(
        upstream_nodes=upstream.dependency_dag.nodes,
        locally_replayed_record_ids=frozenset(local_ids),
    )
    dag = V075PortablePublicLineageDependencyDAGV2(
        _DAG_ISSUER,
        bundle.bundle_id,
        upstream,
        typed_graph._graph_id,
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
    return V075PortablePublicLineageReplayV2(
        _RESULT_ISSUER,
        bundle.bundle_id,
        bundle.occurrence_id,
        context_closure.closure_id,
        typed_graph,
        dag,
        attestations,
        role_closures,
    )


def open_v075_production_from_portable_public_lineage_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortablePublicLineageProductionV2NotReady(
        "M2 public lineage closes two public verification roles and the "
        "lineage public projection, but private closure verification, source "
        "authority, code provenance, and the remaining semantic registry are "
        "still incomplete"
    )


__all__ = [
    "CODE_PROVENANCE_COMPLETE",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
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
    "V075PortablePublicLineageDependencyDAGV2",
    "V075PortablePublicLineageDependencyNodeV2",
    "V075PortablePublicLineageProductionV2NotReady",
    "V075PortablePublicLineageRecordAttestationV2",
    "V075PortablePublicLineageReplayV2",
    "V075PortablePublicLineageResolverKindV2",
    "V075PortablePublicLineageRoleClosureV2",
    "V075PortablePublicLineageRoleStatusV2",
    "V075PortablePublicLineageTypedGraphV2",
    "V075PortablePublicLineageV2InvariantViolation",
    "open_v075_production_from_portable_public_lineage_v2",
    "replay_v075_portable_public_lineage_v2",
]
