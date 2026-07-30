"""Public M2 authority for the V0-075 dynamic-child proposal closure.

This construction-only cut begins with the hardened contract-1.75 live-epoch
replay.  It then asks the producer's raw-byte dynamic-child verifier to rebuild
the child closure from the exact replayed source epoch and the public namespace.
No operational epoch registry, legacy child authority, observer, worker,
kernel, J0, held-out, K7, signer, or private input is accepted.

The producer closure contains several scalar causal identities which are not
standalone portable records.  This authority therefore emits content-addressed
source bindings.  In particular, every causal edge and child state is tied back
to the exact source numerical row, support descriptor, row-source binding,
observation-row binding, and support freeze.  Every present target role also
depends explicitly on the source LIVE_MODEL_EPOCH, NUMERICAL_MODEL, and
NUMERICAL_PLANNING_PROOF records.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import heapq
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_portable_live_epoch_authority_v2 as m2_epoch
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.76.0"
PROFILE_KEY = "v075_portable_dynamic_child_proposal_authority_v2"

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
KERNEL_ACCESS_ALLOWED = False
J0_ACCESS_ALLOWED = False
SIGNER_INPUT_ALLOWED = False
OBSERVER_ACCESS_ALLOWED = False
OBSERVER_INPUT_ALLOWED = False
WORKER_ACCESS_ALLOWED = False
WORKER_INPUT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_M2_DYNAMIC_CHILD_PROPOSAL_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "M2_DYNAMIC_CHILD_PROPOSAL_REPLAYED_NUMERICAL_MODEL_AND_PROOF_"
    "FRONTIER_UNRESOLVED"
)
MAX_OUTPUT_BYTES = 64 * 1024 * 1024

ROLE_ORDER = (
    "DYNAMIC_CHILD_CAUSAL_EDGE",
    "DYNAMIC_CHILD_STATE",
    "DYNAMIC_CHILD_DISCOVERY_INTENT",
    "DYNAMIC_CHILD_VALIDATION_TEMPLATE",
    "DYNAMIC_CHILD_CLOSURE",
    "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
)
_ROLE_SET = frozenset(ROLE_ORDER)
_PRESENT_ROOT_ONLY_ROLES = frozenset(
    {
        "DYNAMIC_CHILD_CAUSAL_EDGE",
        "DYNAMIC_CHILD_STATE",
        "DYNAMIC_CHILD_CLOSURE",
        "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
    }
)
_ABSENT_ROOT_ONLY_ROLES = frozenset(
    {
        "DYNAMIC_CHILD_DISCOVERY_INTENT",
        "DYNAMIC_CHILD_VALIDATION_TEMPLATE",
    }
)
_ROLE_SCHEMA = MappingProxyType(
    {
        "DYNAMIC_CHILD_CAUSAL_EDGE": (
            "acfqp.v075_live_dynamic_child_causal_edge.v2"
        ),
        "DYNAMIC_CHILD_STATE": (
            "acfqp.v075_live_dynamic_child_state.v2"
        ),
        "DYNAMIC_CHILD_DISCOVERY_INTENT": (
            "acfqp.v075_live_dynamic_child_acquisition_intent.v2"
        ),
        "DYNAMIC_CHILD_VALIDATION_TEMPLATE": (
            "acfqp.v075_live_dynamic_child_validation_intent_template.v2"
        ),
        "DYNAMIC_CHILD_CLOSURE": (
            "acfqp.v075_live_dynamic_child_closure.v2"
        ),
        "DYNAMIC_CHILD_CLOSURE_VERIFICATION": (
            "acfqp.v075_live_dynamic_child_closure_verification.v2"
        ),
    }
)
_ROLE_ID_FIELD = MappingProxyType(
    {
        "DYNAMIC_CHILD_CAUSAL_EDGE": "edge_id",
        "DYNAMIC_CHILD_STATE": "child_binding_id",
        "DYNAMIC_CHILD_DISCOVERY_INTENT": "intent_id",
        "DYNAMIC_CHILD_VALIDATION_TEMPLATE": "template_id",
        "DYNAMIC_CHILD_CLOSURE": "closure_id",
        "DYNAMIC_CHILD_CLOSURE_VERIFICATION": "verification_id",
    }
)
_SOURCE_ROLE_SCHEMA = MappingProxyType(
    {
        "LIVE_MODEL_EPOCH": (
            "acfqp.v075_live_incremental_model_epoch.v2"
        ),
        "NUMERICAL_MODEL": (
            "acfqp.v075_batch_planning_numerical_model.v2"
        ),
        "NUMERICAL_PLANNING_PROOF": (
            "acfqp.v075_batch_planning_numerical_proof.v2"
        ),
        "LIVE_ROW_SOURCE_BINDING": (
            "acfqp.v075_live_model_row_source_binding.v2"
        ),
    }
)
_SOURCE_ROLE_ID_FIELD = MappingProxyType(
    {
        "LIVE_MODEL_EPOCH": "model_epoch_id",
        "NUMERICAL_MODEL": "model_id",
        "NUMERICAL_PLANNING_PROOF": "proof_id",
        "LIVE_ROW_SOURCE_BINDING": "binding_id",
    }
)
_SOURCE_FRONTIER_ROLES = (
    "NUMERICAL_MODEL",
    "NUMERICAL_PLANNING_PROOF",
)

DOMAIN_TAGS = MappingProxyType(
    {
        "edge_source_commitment": (
            "acfqp:v075-portable-dynamic-child-edge-source-commitment:v2"
        ),
        "source_binding": (
            "acfqp:v075-portable-dynamic-child-source-binding:v2"
        ),
        "typed_graph": (
            "acfqp:v075-portable-dynamic-child-proposal-typed-graph:v2"
        ),
        "dependency_dag": (
            "acfqp:v075-portable-dynamic-child-proposal-dependency-dag:v2"
        ),
        "record_attestation": (
            "acfqp:v075-portable-dynamic-child-proposal-"
            "record-attestation:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-dynamic-child-proposal-role-closure:v2"
        ),
        "aggregate": (
            "acfqp:v075-portable-dynamic-child-proposal-authority:v2"
        ),
    }
)

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 dynamic-child consumer domains overlap")


class V075PortableDynamicChildProposalV2InvariantViolation(ValueError):
    """A child proposal, source binding, or dependency proof was invalid."""


class V075PortableDynamicChildProposalProductionV2NotReady(RuntimeError):
    """This public construction cut cannot authorize production."""


class V075PortableDynamicChildProposalRoleStatusV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED = (
        "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
    )
    NOT_PRESENT_IN_OCCURRENCE = "NOT_PRESENT_IN_OCCURRENCE"


class V075PortableDynamicChildProposalResolverKindV2(str, Enum):
    UPSTREAM_M2_LIVE_EPOCH = "UPSTREAM_M2_LIVE_EPOCH"
    M2_DYNAMIC_CHILD_EXACT_PRODUCER_REPLAY = (
        "M2_DYNAMIC_CHILD_EXACT_PRODUCER_REPLAY"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


def _fail(message: str) -> NoReturn:
    raise V075PortableDynamicChildProposalV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableDynamicChildProposalV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _optional_cid(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _cid(value, label)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PortableDynamicChildProposalV2InvariantViolation(
            str(error)
        ) from error


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V075PortableDynamicChildProposalV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _raw(value: Any) -> bytes:
    return canonical_json_bytes(value.to_document())


def _namespace(
    upstream: m2_epoch.V075PortableLiveEpochReplayV2,
    *,
    _upstream_already_current: bool = False,
) -> Any:
    if type(upstream) is not m2_epoch.V075PortableLiveEpochReplayV2:
        _fail("dynamic-child authority requires exact hardened 1.75 replay")
    if not _upstream_already_current:
        upstream._assert_current()  # noqa: SLF001
    try:
        lifecycle = upstream.typed_graph.m2_lifecycle_result
        control_graph = (
            lifecycle.typed_graph.m2_lineage_result.typed_graph.m2_result
            .typed_graph.m1b_result.typed_graph
        )
        namespace = (
            control_graph.m1a_result.typed_graph.m0_result.typed_graph
            .namespace
        )
    except AttributeError as error:
        raise V075PortableDynamicChildProposalV2InvariantViolation(
            "hardened 1.75 graph has no exact public namespace"
        ) from error
    return namespace


_RECORD_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class _PortableRecordBindingV2:
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
            _fail("dynamic-child record binding is caller-minted")
        self._assert_current()

    def _assert_current(self) -> None:
        _cid(self.record_id, "dynamic-child portable record")
        _cid(
            self.semantic_artifact_id,
            "dynamic-child portable semantic artifact",
        )
        schemas = {**_ROLE_SCHEMA, **_SOURCE_ROLE_SCHEMA}
        id_fields = {**_ROLE_ID_FIELD, **_SOURCE_ROLE_ID_FIELD}
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in schemas
            or self.artifact_schema != schemas[self.role]
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
        ):
            _fail("dynamic-child portable record binding is malformed")
        for value in self.dependency_record_ids:
            _cid(value, "dynamic-child portable dependency")
        document = _strict_document(
            self.canonical_artifact_bytes,
            label=f"dynamic-child {self.role}",
        )
        if (
            document.get("schema") != self.artifact_schema
            or document.get(id_fields[self.role])
            != self.semantic_artifact_id
        ):
            _fail("dynamic-child record bytes are role/schema-transplanted")
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
            _fail("dynamic-child portable record ID is stale or rehashed")

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


def _binding_from_record(record: Any) -> _PortableRecordBindingV2:
    return _PortableRecordBindingV2(
        _RECORD_BINDING_ISSUER,
        record.record_id,
        record.index,
        record.role,
        record.artifact_schema,
        record.semantic_artifact_id,
        tuple(record.dependency_record_ids),
        record.canonical_artifact_bytes,
    )


_EDGE_SOURCE_COMMITMENT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableDynamicChildEdgeSourceCommitmentV2:
    """Exact scalar source graph for one child causal edge."""

    _issuer: InitVar[object]
    edge_id: str
    child_state_id: str
    parent_numerical_row_id: str
    parent_row_binding_id: str
    support_descriptor_id: str
    row_source_binding_id: str
    row_source_record_id: str
    support_freeze_id: str
    source_model_epoch_id: str
    source_numerical_model_id: str
    source_proof_id: str
    _commitment_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _EDGE_SOURCE_COMMITMENT_ISSUER:
            _fail("dynamic-child edge source commitment is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_commitment_id",
            _hash("edge_source_commitment", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.edge_id, "edge-source edge"),
            (self.child_state_id, "edge-source child state"),
            (self.parent_numerical_row_id, "edge-source numerical row"),
            (self.parent_row_binding_id, "edge-source row binding"),
            (self.support_descriptor_id, "edge-source descriptor"),
            (self.row_source_binding_id, "edge-source live row source"),
            (self.row_source_record_id, "edge-source live row record"),
            (self.support_freeze_id, "edge-source support freeze"),
            (self.source_model_epoch_id, "edge-source model epoch"),
            (self.source_numerical_model_id, "edge-source model"),
            (self.source_proof_id, "edge-source proof"),
        ):
            _cid(value, label)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_dynamic_child_"
                "edge_source_commitment.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "edge_id": self.edge_id,
            "child_state_id": self.child_state_id,
            "parent_numerical_row_id": self.parent_numerical_row_id,
            "parent_row_binding_id": self.parent_row_binding_id,
            "support_descriptor_id": self.support_descriptor_id,
            "row_source_binding_id": self.row_source_binding_id,
            "row_source_record_id": self.row_source_record_id,
            "support_freeze_id": self.support_freeze_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_numerical_model_id": self.source_numerical_model_id,
            "source_proof_id": self.source_proof_id,
            "numerical_row_exactly_looked_up": True,
            "support_descriptor_exactly_looked_up": True,
            "row_source_exactly_looked_up": True,
            "row_binding_identity_cross_checked": True,
            "support_freeze_identity_cross_checked": True,
            "other_event_instantiated": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._commitment_id != _hash(
            "edge_source_commitment",
            self._payload(),
        ):
            _fail("dynamic-child edge source commitment is stale")

    @property
    def commitment_id(self) -> str:
        self._assert_current()
        return self._commitment_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "commitment_id": self._commitment_id}


_SOURCE_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableDynamicChildSourceBindingV2:
    """Authority-local edge from one target record to its exact source epoch."""

    _issuer: InitVar[object]
    target_record_id: str
    target_role: str
    target_semantic_artifact_id: str
    source_closure_id: str
    source_model_epoch_id: str
    source_model_epoch_record_id: str
    source_numerical_model_id: str
    source_numerical_model_record_id: str
    source_proof_id: str
    source_proof_record_id: str
    source_frontier_id: str | None
    source_head_id: str
    occurrence_id: str
    context_id: str
    target_child_state_id: str | None
    edge_source_commitments: tuple[
        V075PortableDynamicChildEdgeSourceCommitmentV2,
        ...,
    ]
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_BINDING_ISSUER:
            _fail("dynamic-child source binding is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_binding_id",
            _hash("source_binding", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.target_record_id, "child-source target record"),
            (
                self.target_semantic_artifact_id,
                "child-source target artifact",
            ),
            (self.source_closure_id, "child-source closure"),
            (self.source_model_epoch_id, "child-source epoch"),
            (self.source_model_epoch_record_id, "child-source epoch record"),
            (self.source_numerical_model_id, "child-source model"),
            (
                self.source_numerical_model_record_id,
                "child-source model record",
            ),
            (self.source_proof_id, "child-source proof"),
            (self.source_proof_record_id, "child-source proof record"),
            (self.source_head_id, "child-source head"),
            (self.occurrence_id, "child-source occurrence"),
            (self.context_id, "child-source context"),
        ):
            _cid(value, label)
        _optional_cid(self.source_frontier_id, "child-source frontier")
        _optional_cid(self.target_child_state_id, "child-source child state")
        if (
            self.target_role not in _ROLE_SET
            or type(self.edge_source_commitments) is not tuple
            or any(
                type(item)
                is not V075PortableDynamicChildEdgeSourceCommitmentV2
                for item in self.edge_source_commitments
            )
            or tuple(
                item.commitment_id for item in self.edge_source_commitments
            )
            != tuple(
                sorted(
                    {
                        item.commitment_id
                        for item in self.edge_source_commitments
                    }
                )
            )
            or any(
                item.source_model_epoch_id != self.source_model_epoch_id
                or item.source_numerical_model_id
                != self.source_numerical_model_id
                or item.source_proof_id != self.source_proof_id
                for item in self.edge_source_commitments
            )
        ):
            _fail("dynamic-child source binding is malformed")
        edge_role = self.target_role == "DYNAMIC_CHILD_CAUSAL_EDGE"
        state_role = self.target_role == "DYNAMIC_CHILD_STATE"
        if (
            edge_role
            and (
                len(self.edge_source_commitments) != 1
                or self.edge_source_commitments[0].edge_id
                != self.target_semantic_artifact_id
                or self.target_child_state_id
                != self.edge_source_commitments[0].child_state_id
            )
        ):
            _fail("dynamic-child edge binding lost its exact source scalar")
        if (
            state_role
            and (
                not self.edge_source_commitments
                or self.target_child_state_id is None
                or any(
                    item.child_state_id != self.target_child_state_id
                    for item in self.edge_source_commitments
                )
            )
        ):
            _fail("dynamic-child state binding lost a causal source edge")
        if (
            not edge_role
            and not state_role
            and (
                self.target_child_state_id is not None
                or self.edge_source_commitments
            )
        ):
            _fail("non-edge child role contains foreign edge source scalars")

    @property
    def source_dependency_record_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    self.source_model_epoch_record_id,
                    self.source_numerical_model_record_id,
                    self.source_proof_record_id,
                }
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_dynamic_child_source_binding.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "target_record_id": self.target_record_id,
            "target_role": self.target_role,
            "target_semantic_artifact_id": (
                self.target_semantic_artifact_id
            ),
            "source_closure_id": self.source_closure_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_model_epoch_record_id": (
                self.source_model_epoch_record_id
            ),
            "source_numerical_model_id": self.source_numerical_model_id,
            "source_numerical_model_record_id": (
                self.source_numerical_model_record_id
            ),
            "source_proof_id": self.source_proof_id,
            "source_proof_record_id": self.source_proof_record_id,
            "source_frontier_id": self.source_frontier_id,
            "source_head_id": self.source_head_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "target_child_state_id": self.target_child_state_id,
            "edge_source_commitment_ids": [
                item.commitment_id
                for item in self.edge_source_commitments
            ],
            "edge_source_commitments": [
                item.to_document()
                for item in self.edge_source_commitments
            ],
            "source_dependency_record_ids": list(
                self.source_dependency_record_ids
            ),
            "source_epoch_model_proof_identity_bound": True,
            "nonportable_edge_scalars_explicitly_bound": (
                self.target_role
                in {
                    "DYNAMIC_CHILD_CAUSAL_EDGE",
                    "DYNAMIC_CHILD_STATE",
                }
            ),
            "operational_registry_accessed": False,
            "official_execution_allowed": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._binding_id != _hash("source_binding", self._payload()):
            _fail("dynamic-child source binding identity is stale")

    @property
    def binding_id(self) -> str:
        self._assert_current()
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "binding_id": self._binding_id}


def _insert_exact_member(
    target: dict[str, tuple[bytes, Any]],
    *,
    semantic_id: str,
    value: Any,
    label: str,
) -> None:
    _cid(semantic_id, label)
    raw = _raw(value)
    prior = target.get(semantic_id)
    if prior is not None and prior[0] != raw:
        _fail(f"one {label} ID maps to different exact bytes")
    if prior is not None:
        _fail(f"{label} registry contains a duplicate semantic member")
    target[semantic_id] = (raw, value)


def _expected_target_members(
    closure: dynamic.V075LiveDynamicChildClosureV2,
    verification: dynamic.V075LiveDynamicChildClosureVerificationV2,
) -> Mapping[str, Mapping[str, tuple[bytes, Any]]]:
    if (
        type(closure) is not dynamic.V075LiveDynamicChildClosureV2
        or type(verification)
        is not dynamic.V075LiveDynamicChildClosureVerificationV2
        or verification.closure_id != closure.closure_id
    ):
        _fail("dynamic-child producer replay returned foreign typed objects")
    result: dict[str, dict[str, tuple[bytes, Any]]] = {
        role: {} for role in ROLE_ORDER
    }
    for child in closure.child_states:
        for edge in child.causal_edges:
            _insert_exact_member(
                result["DYNAMIC_CHILD_CAUSAL_EDGE"],
                semantic_id=edge.edge_id,
                value=edge,
                label="dynamic child causal edge",
            )
        _insert_exact_member(
            result["DYNAMIC_CHILD_STATE"],
            semantic_id=child.child_binding_id,
            value=child,
            label="dynamic child state",
        )
    for intent in closure.discovery_intents:
        _insert_exact_member(
            result["DYNAMIC_CHILD_DISCOVERY_INTENT"],
            semantic_id=intent.intent_id,
            value=intent,
            label="dynamic child discovery intent",
        )
    for template in closure.validation_templates:
        _insert_exact_member(
            result["DYNAMIC_CHILD_VALIDATION_TEMPLATE"],
            semantic_id=template.template_id,
            value=template,
            label="dynamic child validation template",
        )
    _insert_exact_member(
        result["DYNAMIC_CHILD_CLOSURE"],
        semantic_id=closure.closure_id,
        value=closure,
        label="dynamic child closure",
    )
    _insert_exact_member(
        result["DYNAMIC_CHILD_CLOSURE_VERIFICATION"],
        semantic_id=verification.verification_id,
        value=verification,
        label="dynamic child closure verification",
    )
    return MappingProxyType(
        {
            role: MappingProxyType(dict(sorted(result[role].items())))
            for role in ROLE_ORDER
        }
    )


def _validate_target_registry(
    *,
    target_bindings: tuple[_PortableRecordBindingV2, ...],
    expected_members: Mapping[
        str,
        Mapping[str, tuple[bytes, Any]],
    ],
) -> None:
    if (
        type(target_bindings) is not tuple
        or any(
            type(item) is not _PortableRecordBindingV2
            or item.role not in _ROLE_SET
            for item in target_bindings
        )
        or tuple(item.record_index for item in target_bindings)
        != tuple(sorted(item.record_index for item in target_bindings))
        or len({item.record_id for item in target_bindings})
        != len(target_bindings)
    ):
        _fail("dynamic-child target registry is malformed")
    for item in target_bindings:
        item._assert_current()
    for role in ROLE_ORDER:
        actual = {
            item.semantic_artifact_id: item.canonical_artifact_bytes
            for item in target_bindings
            if item.role == role
        }
        role_bindings = tuple(
            item for item in target_bindings if item.role == role
        )
        if len(actual) != len(role_bindings):
            _fail(f"{role} portable registry duplicates one semantic ID")
        expected = {
            semantic_id: raw
            for semantic_id, (raw, _value) in expected_members[role].items()
        }
        if actual != expected:
            _fail(
                f"{role} portable registry differs from exact producer replay"
            )


def _unique_epoch(
    upstream: m2_epoch.V075PortableLiveEpochReplayV2,
    source_epoch_id: str,
    *,
    _upstream_already_current: bool = False,
) -> live_model.V075LiveIncrementalModelEpochV2:
    _cid(source_epoch_id, "dynamic-child source epoch")
    if type(upstream) is not m2_epoch.V075PortableLiveEpochReplayV2:
        _fail("dynamic-child source epoch requires exact hardened 1.75")
    if not _upstream_already_current:
        upstream._assert_current()  # noqa: SLF001
    matches = tuple(
        item
        for item in upstream.typed_graph.epochs
        if item.model_epoch_id == source_epoch_id
    )
    if len(matches) != 1:
        _fail("dynamic-child source epoch is absent or duplicated")
    return matches[0]


def _exact_source_record_bindings(
    *,
    all_records: tuple[Any, ...],
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    closure: dynamic.V075LiveDynamicChildClosureV2,
) -> tuple[_PortableRecordBindingV2, ...]:
    if (
        type(all_records) is not tuple
        or type(epoch) is not live_model.V075LiveIncrementalModelEpochV2
        or type(closure) is not dynamic.V075LiveDynamicChildClosureV2
        or closure.source_epoch.model_epoch_id != epoch.model_epoch_id
    ):
        _fail("dynamic-child source record selection is malformed")
    edge_source_ids = {
        edge.row_source_binding_id
        for child in closure.child_states
        for edge in child.causal_edges
    }
    source_by_id = {
        item.binding_id: item for item in epoch.row_sources
    }
    if not edge_source_ids <= source_by_id.keys():
        _fail("dynamic-child edge cites a foreign live row source")
    expected: dict[tuple[str, str], bytes] = {
        ("LIVE_MODEL_EPOCH", epoch.model_epoch_id): epoch.canonical_bytes,
        ("NUMERICAL_MODEL", epoch.model.model_id): _raw(epoch.model),
        (
            "NUMERICAL_PLANNING_PROOF",
            epoch.proof.proof_id,
        ): _raw(epoch.proof),
        **{
            ("LIVE_ROW_SOURCE_BINDING", source_id): _raw(
                source_by_id[source_id]
            )
            for source_id in edge_source_ids
        },
    }
    selected: list[_PortableRecordBindingV2] = []
    for (role, semantic_id), expected_bytes in sorted(expected.items()):
        matches = tuple(
            item
            for item in all_records
            if item.role == role
            and item.semantic_artifact_id == semantic_id
        )
        if len(matches) != 1:
            _fail(
                f"exact {role} source record is absent or duplicated"
            )
        binding = _binding_from_record(matches[0])
        if binding.canonical_artifact_bytes != expected_bytes:
            _fail(f"exact {role} source record bytes differ from source epoch")
        selected.append(binding)
    return tuple(sorted(selected, key=lambda item: item.record_index))


def _source_record(
    source_records: tuple[_PortableRecordBindingV2, ...],
    *,
    role: str,
    semantic_id: str,
) -> _PortableRecordBindingV2:
    matches = tuple(
        item
        for item in source_records
        if item.role == role
        and item.semantic_artifact_id == semantic_id
    )
    if len(matches) != 1:
        _fail(f"dynamic-child source {role} is absent or duplicated")
    matches[0]._assert_current()
    return matches[0]


def _edge_source_commitment(
    *,
    edge: dynamic.V075LiveDynamicChildCausalEdgeV2,
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    source_records: tuple[_PortableRecordBindingV2, ...],
) -> V075PortableDynamicChildEdgeSourceCommitmentV2:
    if type(edge) is not dynamic.V075LiveDynamicChildCausalEdgeV2:
        _fail("dynamic-child scalar source is not an exact causal edge")
    rows = tuple(
        item
        for item in epoch.model.rows
        if item.row_id == edge.parent_numerical_row_id
    )
    if len(rows) != 1:
        _fail("dynamic-child parent numerical row is absent or duplicated")
    row = rows[0]
    descriptors = tuple(
        item
        for item in row.support
        if item.descriptor_id == edge.support_descriptor_id
    )
    sources = tuple(
        item
        for item in epoch.row_sources
        if item.binding_id == edge.row_source_binding_id
    )
    freezes = tuple(
        item
        for item in epoch.support_freezes
        if item.freeze_id == edge.support_freeze_id
    )
    if (
        len(descriptors) != 1
        or len(sources) != 1
        or len(freezes) != 1
    ):
        _fail(
            "dynamic-child descriptor, row source, or support freeze "
            "is absent or duplicated"
        )
    descriptor = descriptors[0]
    source = sources[0]
    if (
        row.remaining_horizon != 2
        or row.row_binding_id != edge.parent_row_binding_id
        or descriptor.next_state_id != edge.child_state_id
        or descriptor.failure
        or descriptor.terminal
        or source.numerical_row_id != row.row_id
        or source.row_binding_id != row.row_binding_id
        or source.support_freeze_id != edge.support_freeze_id
    ):
        _fail(
            "dynamic-child edge scalar identities differ from exact "
            "epoch row/descriptor/source/freeze graph"
        )
    source_record = _source_record(
        source_records,
        role="LIVE_ROW_SOURCE_BINDING",
        semantic_id=source.binding_id,
    )
    if source_record.canonical_artifact_bytes != _raw(source):
        _fail("dynamic-child edge live row source bytes changed")
    return V075PortableDynamicChildEdgeSourceCommitmentV2(
        _EDGE_SOURCE_COMMITMENT_ISSUER,
        edge.edge_id,
        edge.child_state_id,
        edge.parent_numerical_row_id,
        edge.parent_row_binding_id,
        edge.support_descriptor_id,
        edge.row_source_binding_id,
        source_record.record_id,
        edge.support_freeze_id,
        epoch.model_epoch_id,
        epoch.model.model_id,
        epoch.proof.proof_id,
    )


def _build_source_bindings(
    *,
    target_bindings: tuple[_PortableRecordBindingV2, ...],
    source_records: tuple[_PortableRecordBindingV2, ...],
    expected_members: Mapping[
        str,
        Mapping[str, tuple[bytes, Any]],
    ],
    closure: dynamic.V075LiveDynamicChildClosureV2,
    verification: dynamic.V075LiveDynamicChildClosureVerificationV2,
    epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> tuple[V075PortableDynamicChildSourceBindingV2, ...]:
    _validate_target_registry(
        target_bindings=target_bindings,
        expected_members=expected_members,
    )
    epoch_record = _source_record(
        source_records,
        role="LIVE_MODEL_EPOCH",
        semantic_id=epoch.model_epoch_id,
    )
    model_record = _source_record(
        source_records,
        role="NUMERICAL_MODEL",
        semantic_id=epoch.model.model_id,
    )
    proof_record = _source_record(
        source_records,
        role="NUMERICAL_PLANNING_PROOF",
        semantic_id=epoch.proof.proof_id,
    )
    if (
        epoch_record.canonical_artifact_bytes != epoch.canonical_bytes
        or model_record.canonical_artifact_bytes != _raw(epoch.model)
        or proof_record.canonical_artifact_bytes != _raw(epoch.proof)
        or closure.source_epoch.model_epoch_id != epoch.model_epoch_id
        or verification.source_model_epoch_id != epoch.model_epoch_id
        or verification.source_proof_id != epoch.proof.proof_id
        or verification.source_head_id != epoch.head_id
    ):
        _fail("dynamic-child source epoch/model/proof graph changed")
    frontier = epoch.proof.failed_frontier
    result: list[V075PortableDynamicChildSourceBindingV2] = []
    for target in target_bindings:
        value = expected_members[target.role][
            target.semantic_artifact_id
        ][1]
        if target.role == "DYNAMIC_CHILD_CAUSAL_EDGE":
            edges = (value,)
            child_state_id = value.child_state_id
        elif target.role == "DYNAMIC_CHILD_STATE":
            edges = value.causal_edges
            child_state_id = value.state.state_id
        else:
            edges = ()
            child_state_id = None
        edge_commitments = tuple(
            sorted(
                (
                    _edge_source_commitment(
                        edge=edge,
                        epoch=epoch,
                        source_records=source_records,
                    )
                    for edge in edges
                ),
                key=lambda item: item.commitment_id,
            )
        )
        result.append(
            V075PortableDynamicChildSourceBindingV2(
                _SOURCE_BINDING_ISSUER,
                target.record_id,
                target.role,
                target.semantic_artifact_id,
                closure.closure_id,
                epoch.model_epoch_id,
                epoch_record.record_id,
                epoch.model.model_id,
                model_record.record_id,
                epoch.proof.proof_id,
                proof_record.record_id,
                (
                    None
                    if frontier is None
                    else frontier.frontier_id
                ),
                epoch.head_id,
                epoch.occurrence_identity.occurrence_id,
                epoch.context_id,
                child_state_id,
                edge_commitments,
            )
        )
    result_tuple = tuple(
        sorted(result, key=lambda item: item.target_record_id)
    )
    if (
        len(result_tuple) != len(target_bindings)
        or {
            item.target_record_id for item in result_tuple
        }
        != {item.record_id for item in target_bindings}
    ):
        _fail("dynamic-child source binding coverage is not all-or-none")
    return result_tuple


def _validate_exact_source_records(
    *,
    source_records: tuple[_PortableRecordBindingV2, ...],
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    closure: dynamic.V075LiveDynamicChildClosureV2,
) -> None:
    edge_source_ids = {
        edge.row_source_binding_id
        for child in closure.child_states
        for edge in child.causal_edges
    }
    source_by_id = {
        item.binding_id: item for item in epoch.row_sources
    }
    expected = {
        ("LIVE_MODEL_EPOCH", epoch.model_epoch_id): epoch.canonical_bytes,
        ("NUMERICAL_MODEL", epoch.model.model_id): _raw(epoch.model),
        (
            "NUMERICAL_PLANNING_PROOF",
            epoch.proof.proof_id,
        ): _raw(epoch.proof),
        **{
            ("LIVE_ROW_SOURCE_BINDING", source_id): _raw(
                source_by_id[source_id]
            )
            for source_id in edge_source_ids
        },
    }
    actual: dict[tuple[str, str], bytes] = {}
    if (
        type(source_records) is not tuple
        or any(
            type(item) is not _PortableRecordBindingV2
            or item.role not in _SOURCE_ROLE_SCHEMA
            for item in source_records
        )
        or tuple(item.record_index for item in source_records)
        != tuple(sorted(item.record_index for item in source_records))
    ):
        _fail("dynamic-child exact source record registry is malformed")
    for item in source_records:
        item._assert_current()
        key = (item.role, item.semantic_artifact_id)
        if key in actual:
            _fail("dynamic-child exact source record is duplicated")
        actual[key] = item.canonical_artifact_bytes
    if actual != expected:
        _fail("dynamic-child exact source record registry changed")


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableDynamicChildProposalTypedGraphV2:
    """Exact producer replay plus portable/source identity bindings."""

    _issuer: InitVar[object]
    bundle_id: str
    public_context_closure_id: str
    occurrence_id: str
    m2_live_epoch_result: m2_epoch.V075PortableLiveEpochReplayV2 = field(
        repr=False
    )
    closure: dynamic.V075LiveDynamicChildClosureV2 = field(repr=False)
    verification: dynamic.V075LiveDynamicChildClosureVerificationV2 = field(
        repr=False
    )
    target_record_bindings: tuple[_PortableRecordBindingV2, ...] = field(
        repr=False
    )
    source_record_bindings: tuple[_PortableRecordBindingV2, ...] = field(
        repr=False
    )
    source_bindings: tuple[
        V075PortableDynamicChildSourceBindingV2,
        ...,
    ] = field(repr=False)
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("M2 dynamic-child typed graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._identity_payload()),
        )

    def _validate(
        self,
        *,
        _upstream_already_current: bool = False,
    ) -> None:
        for value, label in (
            (self.bundle_id, "dynamic-child typed graph bundle"),
            (
                self.public_context_closure_id,
                "dynamic-child typed graph context closure",
            ),
            (self.occurrence_id, "dynamic-child typed graph occurrence"),
        ):
            _cid(value, label)
        if (
            type(self.m2_live_epoch_result)
            is not m2_epoch.V075PortableLiveEpochReplayV2
            or type(self.closure)
            is not dynamic.V075LiveDynamicChildClosureV2
            or type(self.verification)
            is not dynamic.V075LiveDynamicChildClosureVerificationV2
            or type(self.target_record_bindings) is not tuple
            or type(self.source_record_bindings) is not tuple
            or type(self.source_bindings) is not tuple
            or any(
                type(item)
                is not V075PortableDynamicChildSourceBindingV2
                for item in self.source_bindings
            )
            or tuple(
                item.target_record_id for item in self.source_bindings
            )
            != tuple(
                sorted(
                    item.target_record_id
                    for item in self.source_bindings
                )
            )
        ):
            _fail("M2 dynamic-child typed graph is malformed")
        if not _upstream_already_current:
            self.m2_live_epoch_result._assert_current()  # noqa: SLF001
        upstream = self.m2_live_epoch_result
        if (
            upstream.bundle_id != self.bundle_id
            or upstream.occurrence_id != self.occurrence_id
            or upstream.public_context_closure_id
            != self.public_context_closure_id
        ):
            _fail("M2 dynamic-child typed graph crossed 1.75 identities")

        source_epoch_id = self.closure.source_epoch.model_epoch_id
        epoch = _unique_epoch(
            upstream,
            source_epoch_id,
            _upstream_already_current=True,
        )
        closure_bindings = tuple(
            item
            for item in self.target_record_bindings
            if item.role == "DYNAMIC_CHILD_CLOSURE"
        )
        if len(closure_bindings) != 1:
            _fail("dynamic-child closure portable role is not singleton")
        try:
            replayed_closure, replayed_verification = (
                dynamic.verify_v075_live_dynamic_child_closure_bytes_v2(
                    source_epoch=epoch,
                    namespace=_namespace(
                        upstream,
                        _upstream_already_current=True,
                    ),
                    claimed_bytes=(
                        closure_bindings[0].canonical_artifact_bytes
                    ),
                )
            )
        except Exception as error:
            raise V075PortableDynamicChildProposalV2InvariantViolation(
                "dynamic-child exact producer byte replay failed"
            ) from error
        if (
            replayed_closure.canonical_bytes
            != self.closure.canonical_bytes
            or replayed_verification.to_document()
            != self.verification.to_document()
            or replayed_closure.source_epoch.model_epoch_id
            != epoch.model_epoch_id
        ):
            _fail("dynamic-child stored producer replay is stale")

        expected_members = _expected_target_members(
            replayed_closure,
            replayed_verification,
        )
        _validate_target_registry(
            target_bindings=self.target_record_bindings,
            expected_members=expected_members,
        )
        _validate_exact_source_records(
            source_records=self.source_record_bindings,
            epoch=epoch,
            closure=replayed_closure,
        )

        upstream_nodes = {
            item.record_id: item
            for item in upstream.dependency_dag.nodes
        }
        for binding in (
            *self.target_record_bindings,
            *self.source_record_bindings,
        ):
            node = upstream_nodes.get(binding.record_id)
            if (
                node is None
                or node.record_index != binding.record_index
                or node.role != binding.role
                or node.portable_declared_dependency_record_ids
                != binding.dependency_record_ids
            ):
                _fail(
                    "dynamic-child record differs from hardened 1.75 spine"
                )

        expected_source_bindings = _build_source_bindings(
            target_bindings=self.target_record_bindings,
            source_records=self.source_record_bindings,
            expected_members=expected_members,
            closure=replayed_closure,
            verification=replayed_verification,
            epoch=epoch,
        )
        for item in self.source_bindings:
            item._assert_current()
        if tuple(
            (item.to_document(), item.binding_id)
            for item in self.source_bindings
        ) != tuple(
            (item.to_document(), item.binding_id)
            for item in expected_source_bindings
        ):
            _fail(
                "dynamic-child source bindings are omitted, reordered, "
                "stale, or transplanted"
            )

        members_by_role = {
            role: tuple(expected_members[role]) for role in ROLE_ORDER
        }
        if (
            replayed_closure.status
            is not dynamic.V075LiveDynamicChildClosureStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
            or not members_by_role["DYNAMIC_CHILD_CAUSAL_EDGE"]
            or not members_by_role["DYNAMIC_CHILD_STATE"]
            or members_by_role["DYNAMIC_CHILD_DISCOVERY_INTENT"]
            or members_by_role["DYNAMIC_CHILD_VALIDATION_TEMPLATE"]
            or len(members_by_role["DYNAMIC_CHILD_CLOSURE"]) != 1
            or len(
                members_by_role[
                    "DYNAMIC_CHILD_CLOSURE_VERIFICATION"
                ]
            )
            != 1
        ):
            _fail(
                "M2 dynamic-child root-only proposal registry differs "
                "from the preregistered cap-exceeded cut"
            )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_dynamic_child_proposal_typed_graph.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "public_context_closure_id": self.public_context_closure_id,
            "occurrence_id": self.occurrence_id,
            "hardened_m2_live_epoch_result_id": (
                self.m2_live_epoch_result._result_id  # noqa: SLF001
            ),
            "hardened_m2_live_epoch_dependency_dag_id": (
                self.m2_live_epoch_result.dependency_dag._dag_id  # noqa: SLF001
            ),
            "source_model_epoch_id": (
                self.closure.source_epoch.model_epoch_id
            ),
            "source_numerical_model_id": (
                self.closure.source_epoch.model.model_id
            ),
            "source_proof_id": self.closure.source_epoch.proof.proof_id,
            "dynamic_child_closure_id": self.closure.closure_id,
            "dynamic_child_closure_verification_id": (
                self.verification.verification_id
            ),
            "ordered_target_record_commitments": [
                item.commitment_document()
                for item in self.target_record_bindings
            ],
            "ordered_source_record_commitments": [
                item.commitment_document()
                for item in self.source_record_bindings
            ],
            "source_binding_ids": [
                item.binding_id for item in self.source_bindings
            ],
            "source_bindings": [
                item.to_document() for item in self.source_bindings
            ],
            "six_role_registry_byte_exact_including_empty": True,
            "producer_raw_byte_replay_complete": True,
            "source_epoch_exact_lookup": True,
            "source_epoch_model_proof_records_exact": True,
            "present_target_source_binding_all_or_none": True,
            "edge_state_nonportable_scalars_exact": True,
            "operational_registry_accessed": False,
            "legacy_child_authority_accessed": False,
            "observer_execution_performed": False,
            "worker_execution_performed": False,
            "private_replay_performed": False,
            "private_material_serialized": False,
        }

    def _assert_current(
        self,
        *,
        _upstream_already_current: bool = False,
    ) -> None:
        self._validate(
            _upstream_already_current=_upstream_already_current,
        )
        if self._graph_id != _hash(
            "typed_graph",
            self._identity_payload(),
        ):
            _fail("M2 dynamic-child typed graph identity is stale")

    @property
    def graph_id(self) -> str:
        self._assert_current()
        return self._graph_id

    def __reduce__(self) -> NoReturn:
        raise TypeError("M2 dynamic-child typed graph is in-memory-only")


@dataclass(frozen=True, slots=True)
class V075PortableDynamicChildProposalDependencyNodeV2:
    record_id: str
    record_index: int
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    source_binding_id: str | None
    resolver_kind: V075PortableDynamicChildProposalResolverKindV2
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    dependency_depth: int

    def _assert_current(self) -> None:
        _cid(self.record_id, "dynamic-child dependency node")
        _optional_cid(
            self.source_binding_id,
            "dynamic-child dependency source binding",
        )
        sequences = (
            self.portable_declared_dependency_record_ids,
            self.authority_local_semantic_dependency_record_ids,
            self.effective_dependency_record_ids,
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
            or set(self.effective_dependency_record_ids)
            != (
                set(self.portable_declared_dependency_record_ids)
                | set(
                    self.authority_local_semantic_dependency_record_ids
                )
            )
            or type(self.resolver_kind)
            is not V075PortableDynamicChildProposalResolverKindV2
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
            or (
                self.source_binding_id is not None
                and (
                    self.role not in _ROLE_SET
                    or not self.local_semantic_authority_resolved
                    or self.resolver_kind
                    is not V075PortableDynamicChildProposalResolverKindV2
                    .M2_DYNAMIC_CHILD_EXACT_PRODUCER_REPLAY
                )
            )
        ):
            _fail("dynamic-child dependency node is malformed")
        for value in (
            *self.effective_dependency_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "dynamic-child dependency edge")

    @property
    def direct_dependency_record_ids(self) -> tuple[str, ...]:
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
            "source_binding_id": self.source_binding_id,
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


def _iterative_dynamic_child_dependency_nodes(
    *,
    upstream_nodes: tuple[Any, ...],
    locally_replayed_record_ids: frozenset[str],
    source_dependency_record_ids_by_target: Mapping[
        str,
        tuple[str, ...],
    ],
    source_binding_ids_by_target: Mapping[str, str],
) -> tuple[V075PortableDynamicChildProposalDependencyNodeV2, ...]:
    """Extend all three 1.75 lanes with forward-safe, iterative replay."""

    if (
        type(upstream_nodes) is not tuple
        or not upstream_nodes
        or type(locally_replayed_record_ids) is not frozenset
        or not isinstance(source_dependency_record_ids_by_target, Mapping)
        or not isinstance(source_binding_ids_by_target, Mapping)
    ):
        _fail("dynamic-child dependency replay requires a nonempty DAG")
    source_dependencies = dict(source_dependency_record_ids_by_target)
    source_binding_ids = dict(source_binding_ids_by_target)
    if (
        set(source_dependencies) != set(locally_replayed_record_ids)
        or set(source_binding_ids) != set(locally_replayed_record_ids)
    ):
        _fail("dynamic-child local source binding coverage is not all-or-none")

    upstream_by_id: dict[str, Any] = {}
    record_index_by_id: dict[str, int] = {}
    role_by_id: dict[str, str] = {}
    portable_by_id: dict[str, tuple[str, ...]] = {}
    inherited_local_by_id: dict[str, tuple[str, ...]] = {}
    upstream_local_resolved: dict[str, bool] = {}
    for expected_index, item in enumerate(upstream_nodes):
        try:
            record_id = item.record_id
            record_index = item.record_index
            role = item.role
            portable_dependencies = tuple(
                item.portable_declared_dependency_record_ids
            )
            semantic_dependencies = tuple(
                item.authority_local_semantic_dependency_record_ids
            )
            effective_dependencies = tuple(
                item.effective_dependency_record_ids
            )
            local_resolved = item.local_semantic_authority_resolved
        except (AttributeError, TypeError) as error:
            raise V075PortableDynamicChildProposalV2InvariantViolation(
                "dynamic-child upstream dependency node is malformed"
            ) from error
        if (
            record_index != expected_index
            or record_id in upstream_by_id
            or tuple(sorted(set(portable_dependencies)))
            != portable_dependencies
            or tuple(sorted(set(semantic_dependencies)))
            != semantic_dependencies
            or tuple(sorted(set(effective_dependencies)))
            != effective_dependencies
            or set(effective_dependencies)
            != set(portable_dependencies) | set(semantic_dependencies)
            or type(local_resolved) is not bool
        ):
            _fail(
                "dynamic-child upstream dependency DAG or lane split "
                "is invalid"
            )
        _cid(record_id, "dynamic-child upstream node")
        upstream_by_id[record_id] = item
        record_index_by_id[record_id] = record_index
        role_by_id[record_id] = role
        portable_by_id[record_id] = portable_dependencies
        inherited_local_by_id[record_id] = semantic_dependencies
        upstream_local_resolved[record_id] = local_resolved

    all_ids = set(upstream_by_id)
    for target_id in locally_replayed_record_ids:
        _cid(target_id, "dynamic-child local replay record")
        if target_id not in all_ids or role_by_id[target_id] not in _ROLE_SET:
            _fail("dynamic-child local registry contains foreign records")
        dependencies = source_dependencies[target_id]
        binding_id = source_binding_ids[target_id]
        if (
            type(dependencies) is not tuple
            or tuple(sorted(set(dependencies))) != dependencies
            or len(dependencies) != 3
        ):
            _fail(
                "dynamic-child target lacks exact epoch/model/proof "
                "source edges"
            )
        _cid(binding_id, "dynamic-child local source binding")
        if (
            any(value not in all_ids for value in dependencies)
            or {
                role_by_id[value] for value in dependencies
            }
            != {
                "LIVE_MODEL_EPOCH",
                "NUMERICAL_MODEL",
                "NUMERICAL_PLANNING_PROOF",
            }
        ):
            _fail(
                "dynamic-child local source edges do not name exact "
                "epoch/model/proof records"
            )

    authority_local_by_id: dict[str, tuple[str, ...]] = {}
    effective_by_id: dict[str, tuple[str, ...]] = {}
    for record_id in upstream_by_id:
        extra = source_dependencies.get(record_id, ())
        authority_local = tuple(
            sorted(
                set(inherited_local_by_id[record_id]) | set(extra)
            )
        )
        effective = tuple(
            sorted(set(portable_by_id[record_id]) | set(authority_local))
        )
        if any(value not in all_ids for value in effective):
            _fail("dynamic-child dependency graph cites a foreign record")
        if record_id in effective:
            _fail("dynamic-child dependency graph contains a self-edge")
        authority_local_by_id[record_id] = authority_local
        effective_by_id[record_id] = effective

    successors: dict[str, list[str]] = {
        record_id: [] for record_id in upstream_by_id
    }
    indegree = {
        record_id: len(effective_by_id[record_id])
        for record_id in upstream_by_id
    }
    for record_id, dependencies in effective_by_id.items():
        for dependency_id in dependencies:
            successors[dependency_id].append(record_id)
    ready: list[tuple[int, str]] = [
        (record_index_by_id[record_id], record_id)
        for record_id, degree in indegree.items()
        if degree == 0
    ]
    heapq.heapify(ready)
    topological: list[str] = []
    while ready:
        _index, record_id = heapq.heappop(ready)
        topological.append(record_id)
        for successor_id in successors[record_id]:
            indegree[successor_id] -= 1
            if indegree[successor_id] == 0:
                heapq.heappush(
                    ready,
                    (record_index_by_id[successor_id], successor_id),
                )
    if len(topological) != len(upstream_by_id):
        _fail("dynamic-child effective dependency graph contains a cycle")

    resolved_by_id: dict[str, bool] = {}
    frontier_by_id: dict[str, tuple[str, ...]] = {}
    depth_by_id: dict[str, int] = {}
    built_by_id: dict[
        str,
        V075PortableDynamicChildProposalDependencyNodeV2,
    ] = {}
    for record_id in topological:
        role = role_by_id[record_id]
        dependencies = effective_by_id[record_id]
        if record_id in locally_replayed_record_ids:
            resolver = (
                V075PortableDynamicChildProposalResolverKindV2
                .M2_DYNAMIC_CHILD_EXACT_PRODUCER_REPLAY
            )
            local_resolved = True
            source_binding_id = source_binding_ids[record_id]
        elif upstream_local_resolved[record_id]:
            resolver = (
                V075PortableDynamicChildProposalResolverKindV2
                .UPSTREAM_M2_LIVE_EPOCH
            )
            local_resolved = True
            source_binding_id = None
        else:
            resolver = (
                V075PortableDynamicChildProposalResolverKindV2
                .NO_REGISTERED_SEMANTIC_AUTHORITY
            )
            local_resolved = False
            source_binding_id = None
        semantically_resolved = local_resolved and all(
            resolved_by_id[value] for value in dependencies
        )
        if semantically_resolved:
            frontier: tuple[str, ...] = ()
        elif not local_resolved:
            frontier = (record_id,)
        else:
            unresolved: set[str] = set()
            for dependency_id in dependencies:
                unresolved.update(frontier_by_id[dependency_id])
            frontier = tuple(sorted(unresolved))
            if not frontier:
                _fail(
                    "unresolved dynamic-child node lacks a proof frontier"
                )
        frontier_roles = tuple(
            sorted({role_by_id[value] for value in frontier})
        )
        depth = 1 + max(
            (depth_by_id[value] for value in dependencies),
            default=0,
        )
        node = V075PortableDynamicChildProposalDependencyNodeV2(
            record_id,
            record_index_by_id[record_id],
            role,
            portable_by_id[record_id],
            authority_local_by_id[record_id],
            effective_by_id[record_id],
            source_binding_id,
            resolver,
            local_resolved,
            semantically_resolved,
            frontier,
            frontier_roles,
            depth,
        )
        node._assert_current()
        built_by_id[record_id] = node
        resolved_by_id[record_id] = semantically_resolved
        frontier_by_id[record_id] = frontier
        depth_by_id[record_id] = depth
    return tuple(
        built_by_id[record_id]
        for record_id in sorted(
            built_by_id,
            key=record_index_by_id.__getitem__,
        )
    )


def _source_dependency_maps(
    source_bindings: tuple[
        V075PortableDynamicChildSourceBindingV2,
        ...,
    ],
) -> tuple[Mapping[str, tuple[str, ...]], Mapping[str, str]]:
    dependencies: dict[str, tuple[str, ...]] = {}
    binding_ids: dict[str, str] = {}
    for item in source_bindings:
        item._assert_current()
        if item.target_record_id in dependencies:
            _fail("dynamic-child target has duplicate source bindings")
        dependencies[item.target_record_id] = (
            item.source_dependency_record_ids
        )
        binding_ids[item.target_record_id] = item.binding_id
    return (
        MappingProxyType(dict(sorted(dependencies.items()))),
        MappingProxyType(dict(sorted(binding_ids.items()))),
    )


_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableDynamicChildProposalDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    m2_live_epoch_result: m2_epoch.V075PortableLiveEpochReplayV2 = field(
        repr=False
    )
    typed_graph_id: str
    locally_replayed_record_ids: tuple[str, ...]
    source_bindings: tuple[
        V075PortableDynamicChildSourceBindingV2,
        ...,
    ] = field(repr=False)
    nodes: tuple[
        V075PortableDynamicChildProposalDependencyNodeV2,
        ...,
    ] = field(repr=False)
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("M2 dynamic-child dependency DAG is caller-minted")
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
        _cid(self.bundle_id, "dynamic-child DAG bundle")
        _cid(self.typed_graph_id, "dynamic-child DAG typed graph")
        if (
            type(self.m2_live_epoch_result)
            is not m2_epoch.V075PortableLiveEpochReplayV2
            or type(self.locally_replayed_record_ids) is not tuple
            or tuple(sorted(set(self.locally_replayed_record_ids)))
            != self.locally_replayed_record_ids
            or type(self.source_bindings) is not tuple
            or type(self.nodes) is not tuple
            or not self.nodes
        ):
            _fail("M2 dynamic-child dependency DAG is malformed")
        if not _upstream_already_current:
            self.m2_live_epoch_result._assert_current()  # noqa: SLF001
        dependency_map, binding_map = _source_dependency_maps(
            self.source_bindings
        )
        expected = _iterative_dynamic_child_dependency_nodes(
            upstream_nodes=self.m2_live_epoch_result.dependency_dag.nodes,
            locally_replayed_record_ids=frozenset(
                self.locally_replayed_record_ids
            ),
            source_dependency_record_ids_by_target=dependency_map,
            source_binding_ids_by_target=binding_map,
        )
        for item in self.nodes:
            item._assert_current()
        if (
            self.m2_live_epoch_result.bundle_id != self.bundle_id
            or tuple(item.to_document() for item in self.nodes)
            != tuple(item.to_document() for item in expected)
        ):
            _fail("M2 dynamic-child dependency DAG is stale or transplanted")

    def _payload(self) -> dict[str, Any]:
        inherited_local_edge_count = sum(
            len(item.authority_local_semantic_dependency_record_ids)
            for item in self.m2_live_epoch_result.dependency_dag.nodes
        )
        return {
            "schema": (
                "acfqp.v075_portable_dynamic_child_proposal_"
                "dependency_dag.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "hardened_m2_live_epoch_result_id": (
                self.m2_live_epoch_result._result_id  # noqa: SLF001
            ),
            "hardened_m2_live_epoch_dependency_dag_id": (
                self.m2_live_epoch_result.dependency_dag._dag_id  # noqa: SLF001
            ),
            "m2_dynamic_child_typed_graph_id": self.typed_graph_id,
            "locally_replayed_record_ids": list(
                self.locally_replayed_record_ids
            ),
            "source_binding_ids": [
                item.binding_id for item in self.source_bindings
            ],
            "nodes": [item.to_document() for item in self.nodes],
            "node_count": len(self.nodes),
            "portable_declared_edge_count": sum(
                len(item.portable_declared_dependency_record_ids)
                for item in self.nodes
            ),
            "inherited_authority_local_edge_count": (
                inherited_local_edge_count
            ),
            "authority_local_edge_count_after_source_binding": sum(
                len(item.authority_local_semantic_dependency_record_ids)
                for item in self.nodes
            ),
            "maximum_dependency_depth": max(
                item.dependency_depth for item in self.nodes
            ),
            "upstream_three_dependency_lanes_preserved": True,
            "portable_and_local_duplicate_edges_preserved_by_lane": True,
            "effective_edges_are_set_union_only": True,
            "proof_shape": "ITERATIVE_FORWARD_SAFE_THREE_LANE_DAG",
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
            _fail("M2 dynamic-child dependency DAG identity is stale")

    @property
    def dag_id(self) -> str:
        self._assert_current()
        return self._dag_id

    @property
    def nodes_by_id(
        self,
    ) -> Mapping[
        str,
        V075PortableDynamicChildProposalDependencyNodeV2,
    ]:
        self._assert_current()
        return MappingProxyType({item.record_id: item for item in self.nodes})


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableDynamicChildProposalRecordAttestationV2:
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
    source_binding_id: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    resolved_direct_dependency_record_ids: tuple[str, ...]
    unresolved_direct_dependency_record_ids: tuple[str, ...]
    resolver_kind: V075PortableDynamicChildProposalResolverKindV2
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    dependency_depth: int
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("dynamic-child record attestation is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("record_attestation", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "dynamic-child attestation bundle"),
            (self.typed_graph_id, "dynamic-child attestation graph"),
            (self.dependency_dag_id, "dynamic-child attestation DAG"),
            (self.record_id, "dynamic-child attestation record"),
            (
                self.semantic_artifact_id,
                "dynamic-child attestation artifact",
            ),
            (
                self.source_binding_id,
                "dynamic-child attestation source binding",
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
        try:
            digest_ok = (
                len(self.canonical_artifact_sha256) == 64
                and int(self.canonical_artifact_sha256, 16) >= 0
                and self.canonical_artifact_sha256
                == self.canonical_artifact_sha256.lower()
            )
        except (TypeError, ValueError):
            digest_ok = False
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _ROLE_SET
            or not digest_ok
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
                | set(
                    self.authority_local_semantic_dependency_record_ids
                )
            )
            or set(self.resolved_direct_dependency_record_ids)
            | set(self.unresolved_direct_dependency_record_ids)
            != set(self.effective_dependency_record_ids)
            or set(self.resolved_direct_dependency_record_ids)
            & set(self.unresolved_direct_dependency_record_ids)
            or self.resolver_kind
            is not V075PortableDynamicChildProposalResolverKindV2
            .M2_DYNAMIC_CHILD_EXACT_PRODUCER_REPLAY
            or self.local_semantic_authority_resolved is not True
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
            _fail("dynamic-child record attestation is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_dynamic_child_proposal_"
                "record_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m2_dynamic_child_typed_graph_id": self.typed_graph_id,
            "m2_dynamic_child_dependency_dag_id": self.dependency_dag_id,
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "semantic_artifact_id": self.semantic_artifact_id,
            "canonical_artifact_sha256": self.canonical_artifact_sha256,
            "canonical_artifact_byte_count": (
                self.canonical_artifact_byte_count
            ),
            "source_binding_id": self.source_binding_id,
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
            "producer_raw_byte_replay_complete": True,
            "source_epoch_model_proof_edges_explicit": True,
            "official_execution_allowed": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._attestation_id != _hash(
            "record_attestation",
            self._payload(),
        ):
            _fail("dynamic-child record attestation identity is stale")

    @property
    def attestation_id(self) -> str:
        self._assert_current()
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            **self._payload(),
            "attestation_id": self._attestation_id,
        }


def _build_attestations(
    *,
    bundle_id: str,
    typed_graph_id: str,
    dag: V075PortableDynamicChildProposalDependencyDAGV2,
    target_bindings: tuple[_PortableRecordBindingV2, ...],
    _dag_already_current: bool = False,
) -> tuple[V075PortableDynamicChildProposalRecordAttestationV2, ...]:
    if not _dag_already_current:
        dag._assert_current()
    nodes = {item.record_id: item for item in dag.nodes}
    source_binding_by_target = {
        item.target_record_id: item for item in dag.source_bindings
    }
    result: list[
        V075PortableDynamicChildProposalRecordAttestationV2
    ] = []
    for binding in target_bindings:
        binding._assert_current()
        node = nodes.get(binding.record_id)
        source_binding = source_binding_by_target.get(binding.record_id)
        if (
            node is None
            or source_binding is None
            or node.source_binding_id != source_binding.binding_id
        ):
            _fail(
                "dynamic-child attestation target lacks node/source binding"
            )
        resolved_direct = tuple(
            sorted(
                dependency_id
                for dependency_id in node.effective_dependency_record_ids
                if nodes[dependency_id].semantically_resolved
            )
        )
        unresolved_direct = tuple(
            sorted(
                set(node.effective_dependency_record_ids)
                - set(resolved_direct)
            )
        )
        result.append(
            V075PortableDynamicChildProposalRecordAttestationV2(
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
                source_binding.binding_id,
                node.portable_declared_dependency_record_ids,
                node.authority_local_semantic_dependency_record_ids,
                node.effective_dependency_record_ids,
                resolved_direct,
                unresolved_direct,
                node.resolver_kind,
                node.local_semantic_authority_resolved,
                node.semantically_resolved,
                node.unresolved_frontier_record_ids,
                node.unresolved_frontier_roles,
                node.dependency_depth,
            )
        )
    return tuple(sorted(result, key=lambda item: item.record_index))


_ROLE_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableDynamicChildProposalRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    dependency_dag_id: str
    role: str
    status: V075PortableDynamicChildProposalRoleStatusV2
    record_ids: tuple[str, ...]
    attestation_ids: tuple[str, ...]
    source_binding_ids: tuple[str, ...]
    unresolved_record_ids: tuple[str, ...]
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("dynamic-child role closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "dynamic-child role closure bundle"),
            (self.typed_graph_id, "dynamic-child role closure graph"),
            (self.dependency_dag_id, "dynamic-child role closure DAG"),
        ):
            _cid(value, label)
        sequences = (
            self.record_ids,
            self.attestation_ids,
            self.source_binding_ids,
            self.unresolved_record_ids,
            self.unresolved_frontier_record_ids,
        )
        if (
            self.role not in _ROLE_SET
            or type(self.status)
            is not V075PortableDynamicChildProposalRoleStatusV2
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in sequences
            )
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
            or not set(self.unresolved_record_ids) <= set(self.record_ids)
            or len(self.record_ids) != len(self.attestation_ids)
            or len(self.record_ids) != len(self.source_binding_ids)
        ):
            _fail("dynamic-child role closure is malformed")
        absent = (
            self.status
            is V075PortableDynamicChildProposalRoleStatusV2
            .NOT_PRESENT_IN_OCCURRENCE
        )
        full = (
            self.status
            is V075PortableDynamicChildProposalRoleStatusV2.FULL_PUBLIC
        )
        structural = (
            self.status
            is V075PortableDynamicChildProposalRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        if (
            absent
            != (
                not self.record_ids
                and not self.attestation_ids
                and not self.source_binding_ids
                and not self.unresolved_record_ids
                and not self.unresolved_frontier_record_ids
                and not self.unresolved_frontier_roles
            )
            or full
            != (
                bool(self.record_ids)
                and not self.unresolved_record_ids
                and not self.unresolved_frontier_record_ids
                and not self.unresolved_frontier_roles
            )
            or structural
            != (
                bool(self.record_ids)
                and bool(self.unresolved_record_ids)
                and bool(self.unresolved_frontier_record_ids)
                and bool(self.unresolved_frontier_roles)
            )
        ):
            _fail("dynamic-child role closure tri-state is false")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_dynamic_child_proposal_role_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m2_dynamic_child_typed_graph_id": self.typed_graph_id,
            "m2_dynamic_child_dependency_dag_id": self.dependency_dag_id,
            "role": self.role,
            "status": self.status.value,
            "record_ids": list(self.record_ids),
            "attestation_ids": list(self.attestation_ids),
            "source_binding_ids": list(self.source_binding_ids),
            "unresolved_record_ids": list(self.unresolved_record_ids),
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
            "producer_registry_complete_for_role": True,
            "official_execution_allowed": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._closure_id != _hash("role_closure", self._payload()):
            _fail("dynamic-child role closure identity is stale")

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
    target_bindings: tuple[_PortableRecordBindingV2, ...],
    attestations: tuple[
        V075PortableDynamicChildProposalRecordAttestationV2,
        ...,
    ],
    _attestations_already_current: bool = False,
) -> tuple[V075PortableDynamicChildProposalRoleClosureV2, ...]:
    by_record = {item.record_id: item for item in attestations}
    if len(by_record) != len(attestations):
        _fail("dynamic-child attestation registry is duplicated")
    if not _attestations_already_current:
        for item in attestations:
            item._assert_current()
    result: list[V075PortableDynamicChildProposalRoleClosureV2] = []
    for role in ROLE_ORDER:
        role_bindings = tuple(
            item for item in target_bindings if item.role == role
        )
        role_attestations = tuple(
            by_record[item.record_id] for item in role_bindings
        )
        unresolved = tuple(
            item
            for item in role_attestations
            if not item.semantically_resolved
        )
        if not role_bindings:
            status = (
                V075PortableDynamicChildProposalRoleStatusV2
                .NOT_PRESENT_IN_OCCURRENCE
            )
        elif unresolved:
            status = (
                V075PortableDynamicChildProposalRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
        else:
            status = (
                V075PortableDynamicChildProposalRoleStatusV2.FULL_PUBLIC
            )
        result.append(
            V075PortableDynamicChildProposalRoleClosureV2(
                _ROLE_CLOSURE_ISSUER,
                bundle_id,
                typed_graph_id,
                dependency_dag_id,
                role,
                status,
                tuple(
                    sorted(item.record_id for item in role_bindings)
                ),
                tuple(
                    sorted(
                        item._attestation_id
                        for item in role_attestations
                    )
                ),
                tuple(
                    sorted(
                        item.source_binding_id
                        for item in role_attestations
                    )
                ),
                tuple(
                    sorted(item.record_id for item in unresolved)
                ),
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
class V075PortableDynamicChildProposalReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075PortableDynamicChildProposalTypedGraphV2 = field(
        repr=False
    )
    dependency_dag: (
        V075PortableDynamicChildProposalDependencyDAGV2
    ) = field(repr=False)
    attestations: tuple[
        V075PortableDynamicChildProposalRecordAttestationV2,
        ...,
    ]
    role_closures: tuple[
        V075PortableDynamicChildProposalRoleClosureV2,
        ...,
    ]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("M2 dynamic-child result is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "dynamic-child result bundle"),
            (self.occurrence_id, "dynamic-child result occurrence"),
            (
                self.public_context_closure_id,
                "dynamic-child result context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph)
            is not V075PortableDynamicChildProposalTypedGraphV2
            or type(self.dependency_dag)
            is not V075PortableDynamicChildProposalDependencyDAGV2
            or type(self.attestations) is not tuple
            or any(
                type(item)
                is not V075PortableDynamicChildProposalRecordAttestationV2
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
                is not V075PortableDynamicChildProposalRoleClosureV2
                for item in self.role_closures
            )
        ):
            _fail("M2 dynamic-child result is malformed")
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
            or self.dependency_dag.m2_live_epoch_result
            is not self.typed_graph.m2_live_epoch_result
            or self.dependency_dag.source_bindings
            != self.typed_graph.source_bindings
        ):
            _fail("M2 dynamic-child result crossed authority identities")

        expected_attestations = _build_attestations(
            bundle_id=self.bundle_id,
            typed_graph_id=graph_id,
            dag=self.dependency_dag,
            target_bindings=self.typed_graph.target_record_bindings,
            _dag_already_current=True,
        )
        for item in self.attestations:
            item._assert_current()
        if tuple(
            (item.to_document(), item._attestation_id)
            for item in self.attestations
        ) != tuple(
            (item.to_document(), item._attestation_id)
            for item in expected_attestations
        ):
            _fail("M2 dynamic-child attestations are stale or transplanted")

        expected_closures = _build_role_closures(
            bundle_id=self.bundle_id,
            typed_graph_id=graph_id,
            dependency_dag_id=dag_id,
            target_bindings=self.typed_graph.target_record_bindings,
            attestations=self.attestations,
            _attestations_already_current=True,
        )
        for item in self.role_closures:
            item._assert_current()
        if tuple(
            (item.to_document(), item._closure_id)
            for item in self.role_closures
        ) != tuple(
            (item.to_document(), item._closure_id)
            for item in expected_closures
        ):
            _fail("M2 dynamic-child role closures are stale or overclaim")

        status = V075PortableDynamicChildProposalRoleStatusV2
        expected_statuses = {
            role: (
                status.STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
                if role in _PRESENT_ROOT_ONLY_ROLES
                else status.NOT_PRESENT_IN_OCCURRENCE
            )
            for role in ROLE_ORDER
        }
        actual_statuses = {
            item.role: item.status for item in self.role_closures
        }
        if actual_statuses != expected_statuses:
            _fail(
                "M2 dynamic-child role status is not exact four-"
                "structural/two-absent root closure"
            )

        nodes = {
            item.record_id: item for item in self.dependency_dag.nodes
        }
        source_by_target = {
            item.target_record_id: item
            for item in self.typed_graph.source_bindings
        }
        if (
            len(source_by_target)
            != len(self.typed_graph.target_record_bindings)
            or set(source_by_target)
            != {
                item.record_id
                for item in self.typed_graph.target_record_bindings
            }
        ):
            _fail("M2 dynamic-child source binding coverage changed")
        for target in self.typed_graph.target_record_bindings:
            node = nodes[target.record_id]
            source = source_by_target[target.record_id]
            expected_frontier = tuple(
                sorted(
                    (
                        source.source_numerical_model_record_id,
                        source.source_proof_record_id,
                    )
                )
            )
            if (
                node.local_semantic_authority_resolved is not True
                or node.semantically_resolved
                or node.resolver_kind
                is not V075PortableDynamicChildProposalResolverKindV2
                .M2_DYNAMIC_CHILD_EXACT_PRODUCER_REPLAY
                or node.source_binding_id != source.binding_id
                or node.unresolved_frontier_record_ids
                != expected_frontier
                or node.unresolved_frontier_roles
                != _SOURCE_FRONTIER_ROLES
                or not {
                    source.source_model_epoch_record_id,
                    source.source_numerical_model_record_id,
                    source.source_proof_record_id,
                }
                <= set(
                    node.authority_local_semantic_dependency_record_ids
                )
            ):
                _fail(
                    "M2 dynamic-child target consumed, stopped before, "
                    "or widened the exact model/proof frontier"
                )
        if any(
            item.status is status.FULL_PUBLIC
            for item in self.role_closures
        ):
            _fail("M2 dynamic-child target role falsely claims FULL_PUBLIC")

    def _payload(self) -> dict[str, Any]:
        closure = self.typed_graph.closure
        return {
            "schema": (
                "acfqp.v075_portable_dynamic_child_proposal_authority.v2"
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
            "hardened_m2_live_epoch_result_id": (
                self.typed_graph.m2_live_epoch_result._result_id  # noqa: SLF001
            ),
            "m2_dynamic_child_typed_graph_id": (
                self.typed_graph._graph_id
            ),
            "m2_dynamic_child_dependency_dag_id": (
                self.dependency_dag._dag_id
            ),
            "source_model_epoch_id": (
                closure.source_epoch.model_epoch_id
            ),
            "source_numerical_model_id": (
                closure.source_epoch.model.model_id
            ),
            "source_proof_id": closure.source_epoch.proof.proof_id,
            "dynamic_child_closure_id": closure.closure_id,
            "dynamic_child_closure_verification_id": (
                self.typed_graph.verification.verification_id
            ),
            "dynamic_child_status": closure.status.value,
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
            "source_binding_ids": [
                item.binding_id
                for item in self.typed_graph.source_bindings
            ],
            "hardened_1_75_called_before_local_bundle_replay": True,
            "producer_byte_verifier_only": True,
            "six_role_registry_byte_exact_including_empty": True,
            "four_structural_two_absent": True,
            "model_and_proof_exact_frontier": True,
            "upstream_three_dependency_lanes_preserved": True,
            "edge_state_scalar_source_graph_complete": True,
            "trusted_operational_registry_accessed": False,
            "operational_child_freeze_called": False,
            "legacy_child_authority_called": False,
            "claimed_typed_epoch_input_accepted": False,
            "signer_input_consumed": False,
            "observer_input_consumed": False,
            "worker_input_consumed": False,
            "private_input_consumed": False,
            "b3_input_consumed": False,
            "kernel_accessed": False,
            "j0_accessed": False,
            "k7_input_consumed": False,
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
            _fail("M2 dynamic-child result identity is stale")

    @property
    def result_id(self) -> str:
        self._assert_current()
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            **self._payload(),
            "source_bindings": [
                item.to_document()
                for item in self.typed_graph.source_bindings
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
            _fail("M2 dynamic-child result exceeds output byte cap")
        return raw

    def __reduce__(self) -> NoReturn:
        raise TypeError("M2 dynamic-child result is in-memory-only")


def replay_v075_portable_dynamic_child_proposal_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
) -> V075PortableDynamicChildProposalReplayV2:
    """Replay the root dynamic-child proposal from raw public authorities."""

    if (
        type(portable_bundle_bytes) is not bytes
        or type(public_context_closure_bytes) is not bytes
    ):
        _fail("M2 dynamic child accepts canonical raw byte authorities only")
    try:
        upstream = m2_epoch.replay_v075_portable_live_epoch_v2(
            repository_root=repository_root,
            portable_bundle_bytes=portable_bundle_bytes,
            public_context_closure_bytes=public_context_closure_bytes,
        )
    except Exception as error:
        raise V075PortableDynamicChildProposalV2InvariantViolation(
            "M2 dynamic child hardened 1.75 replay failed"
        ) from error
    try:
        bundle = (
            portable
            .verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
    except Exception as error:
        raise V075PortableDynamicChildProposalV2InvariantViolation(
            "M2 dynamic child portable bundle replay failed after 1.75"
        ) from error
    if (
        bundle.bundle_id != upstream.bundle_id
        or bundle.occurrence_id != upstream.occurrence_id
    ):
        _fail("M2 dynamic-child raw authorities were transplanted")

    target_records = tuple(
        item for item in bundle.records if item.role in _ROLE_SET
    )
    target_bindings = tuple(
        _binding_from_record(item) for item in target_records
    )
    closure_bindings = tuple(
        item
        for item in target_bindings
        if item.role == "DYNAMIC_CHILD_CLOSURE"
    )
    if len(closure_bindings) != 1:
        _fail("M2 dynamic-child closure record must be exact singleton")
    closure_document = _strict_document(
        closure_bindings[0].canonical_artifact_bytes,
        label="M2 dynamic-child claimed closure",
    )
    source_epoch_id = closure_document.get("source_model_epoch_id")
    epoch = _unique_epoch(
        upstream,
        source_epoch_id,
        _upstream_already_current=True,
    )
    try:
        closure, verification = (
            dynamic.verify_v075_live_dynamic_child_closure_bytes_v2(
                source_epoch=epoch,
                namespace=_namespace(
                    upstream,
                    _upstream_already_current=True,
                ),
                claimed_bytes=(
                    closure_bindings[0].canonical_artifact_bytes
                ),
            )
        )
    except Exception as error:
        raise V075PortableDynamicChildProposalV2InvariantViolation(
            "M2 dynamic child exact producer byte replay failed"
        ) from error

    expected_members = _expected_target_members(closure, verification)
    _validate_target_registry(
        target_bindings=target_bindings,
        expected_members=expected_members,
    )
    source_records = _exact_source_record_bindings(
        all_records=tuple(bundle.records),
        epoch=epoch,
        closure=closure,
    )
    source_bindings = _build_source_bindings(
        target_bindings=target_bindings,
        source_records=source_records,
        expected_members=expected_members,
        closure=closure,
        verification=verification,
        epoch=epoch,
    )
    typed_graph = V075PortableDynamicChildProposalTypedGraphV2(
        _TYPED_GRAPH_ISSUER,
        bundle.bundle_id,
        upstream.public_context_closure_id,
        bundle.occurrence_id,
        upstream,
        closure,
        verification,
        target_bindings,
        source_records,
        source_bindings,
    )
    local_ids = tuple(
        sorted(item.record_id for item in target_bindings)
    )
    dependency_map, binding_map = _source_dependency_maps(
        source_bindings
    )
    nodes = _iterative_dynamic_child_dependency_nodes(
        upstream_nodes=upstream.dependency_dag.nodes,
        locally_replayed_record_ids=frozenset(local_ids),
        source_dependency_record_ids_by_target=dependency_map,
        source_binding_ids_by_target=binding_map,
    )
    dag = V075PortableDynamicChildProposalDependencyDAGV2(
        _DAG_ISSUER,
        bundle.bundle_id,
        upstream,
        typed_graph._graph_id,
        local_ids,
        source_bindings,
        nodes,
    )
    attestations = _build_attestations(
        bundle_id=bundle.bundle_id,
        typed_graph_id=typed_graph._graph_id,
        dag=dag,
        target_bindings=target_bindings,
    )
    role_closures = _build_role_closures(
        bundle_id=bundle.bundle_id,
        typed_graph_id=typed_graph._graph_id,
        dependency_dag_id=dag._dag_id,
        target_bindings=target_bindings,
        attestations=attestations,
    )
    return V075PortableDynamicChildProposalReplayV2(
        _RESULT_ISSUER,
        bundle.bundle_id,
        bundle.occurrence_id,
        upstream.public_context_closure_id,
        typed_graph,
        dag,
        attestations,
        role_closures,
    )


def open_v075_production_from_portable_dynamic_child_proposal_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortableDynamicChildProposalProductionV2NotReady(
        "M2 dynamic child closes the cap-exceeded root proposal "
        "projection, but numerical model/proof, source authority, code "
        "provenance, and the remaining portable registry are incomplete"
    )


__all__ = [
    "B3_INPUT_ALLOWED",
    "CODE_PROVENANCE_COMPLETE",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "J0_ACCESS_ALLOWED",
    "K7_INPUT_ALLOWED",
    "KERNEL_ACCESS_ALLOWED",
    "MAX_OUTPUT_BYTES",
    "OBSERVER_ACCESS_ALLOWED",
    "OBSERVER_INPUT_ALLOWED",
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
    "SIGNER_INPUT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "V075PortableDynamicChildEdgeSourceCommitmentV2",
    "V075PortableDynamicChildProposalDependencyDAGV2",
    "V075PortableDynamicChildProposalDependencyNodeV2",
    "V075PortableDynamicChildProposalProductionV2NotReady",
    "V075PortableDynamicChildProposalRecordAttestationV2",
    "V075PortableDynamicChildProposalReplayV2",
    "V075PortableDynamicChildProposalResolverKindV2",
    "V075PortableDynamicChildProposalRoleClosureV2",
    "V075PortableDynamicChildProposalRoleStatusV2",
    "V075PortableDynamicChildProposalTypedGraphV2",
    "V075PortableDynamicChildProposalV2InvariantViolation",
    "V075PortableDynamicChildSourceBindingV2",
    "WORKER_ACCESS_ALLOWED",
    "WORKER_INPUT_ALLOWED",
    "open_v075_production_from_portable_dynamic_child_proposal_v2",
    "replay_v075_portable_dynamic_child_proposal_v2",
]
