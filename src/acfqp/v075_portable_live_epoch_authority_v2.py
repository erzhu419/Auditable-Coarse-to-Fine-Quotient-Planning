"""Public M2 authority for V0-075 live row sources and model epochs.

This construction-only cut starts with the hardened contract-1.74 lifecycle
replay.  It reconstructs every live epoch from the current public occurrence
and signed-control prefix graph through the producer's tightly scoped
``_build_epoch`` portable path.  Callers cannot provide a typed epoch.

Live row-source bindings are complete public projections.  A live model epoch
remains structurally unresolved because the separately registered numerical
model and numerical planning proof have no public semantic authority in this
cut.  No signer, private input, B3, kernel, J0, held-out, or K7 authority is
accepted.
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
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_portable_construction_lifecycle_authority_v2 as m2_life
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.75.0"
PROFILE_KEY = "v075_portable_live_epoch_authority_v2"

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
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_M2_LIVE_EPOCH_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "M2_LIVE_ROW_SOURCES_REPLAYED_NUMERICAL_MODEL_AND_PROOF_"
    "FRONTIER_UNRESOLVED"
)
MAX_OUTPUT_BYTES = 64 * 1024 * 1024

ROLE_ORDER = (
    "LIVE_ROW_SOURCE_BINDING",
    "LIVE_MODEL_EPOCH",
)
_ROLE_SET = frozenset(ROLE_ORDER)
_ROLE_SCHEMA = MappingProxyType(
    {
        "LIVE_ROW_SOURCE_BINDING": (
            "acfqp.v075_live_model_row_source_binding.v2"
        ),
        "LIVE_MODEL_EPOCH": (
            "acfqp.v075_live_incremental_model_epoch.v2"
        ),
    }
)
_ROLE_ID_FIELD = MappingProxyType(
    {
        "LIVE_ROW_SOURCE_BINDING": "binding_id",
        "LIVE_MODEL_EPOCH": "model_epoch_id",
    }
)
_UNRESOLVED_FRONTIER_ROLES = (
    "NUMERICAL_MODEL",
    "NUMERICAL_PLANNING_PROOF",
)

DOMAIN_TAGS = MappingProxyType(
    {
        "typed_graph": "acfqp:v075-portable-live-epoch-typed-graph:v2",
        "dependency_dag": (
            "acfqp:v075-portable-live-epoch-dependency-dag:v2"
        ),
        "record_attestation": (
            "acfqp:v075-portable-live-epoch-record-attestation:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-live-epoch-role-closure:v2"
        ),
        "aggregate": "acfqp:v075-portable-live-epoch-authority:v2",
    }
)

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 live-epoch consumer domains overlap")


class V075PortableLiveEpochV2InvariantViolation(ValueError):
    """A live epoch, row source, identity, or proof frontier was invalid."""


class V075PortableLiveEpochProductionV2NotReady(RuntimeError):
    """This public construction cut cannot authorize production."""


class V075PortableLiveEpochRoleStatusV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED = (
        "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
    )
    NOT_PRESENT_IN_OCCURRENCE = "NOT_PRESENT_IN_OCCURRENCE"


class V075PortableLiveEpochResolverKindV2(str, Enum):
    UPSTREAM_M2_CONSTRUCTION_LIFECYCLE = (
        "UPSTREAM_M2_CONSTRUCTION_LIFECYCLE"
    )
    M2_LIVE_ROW_SOURCE_BINDING = "M2_LIVE_ROW_SOURCE_BINDING"
    M2_LIVE_MODEL_EPOCH_PUBLIC_PROJECTION = (
        "M2_LIVE_MODEL_EPOCH_PUBLIC_PROJECTION"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


def _fail(message: str) -> NoReturn:
    raise V075PortableLiveEpochV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableLiveEpochV2InvariantViolation(
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
        raise V075PortableLiveEpochV2InvariantViolation(str(error)) from error


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V075PortableLiveEpochV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _raw(value: Any) -> bytes:
    return canonical_json_bytes(value.to_document())


def _control_graph(
    upstream: m2_life.V075PortableConstructionLifecycleReplayV2,
    *,
    _upstream_already_current: bool = False,
) -> Any:
    if (
        type(upstream)
        is not m2_life.V075PortableConstructionLifecycleReplayV2
    ):
        _fail("live-epoch authority requires exact hardened 1.74 replay")
    if not _upstream_already_current:
        upstream._assert_current()  # noqa: SLF001
    return (
        upstream.typed_graph.m2_lineage_result.typed_graph.m2_result
        .typed_graph.m1b_result.typed_graph
    )


def _m0_graph(
    upstream: m2_life.V075PortableConstructionLifecycleReplayV2,
    *,
    _upstream_already_current: bool = False,
) -> Any:
    graph = _control_graph(
        upstream,
        _upstream_already_current=_upstream_already_current,
    )
    return graph.m1a_result.typed_graph.m0_result.typed_graph


def _route_for_occurrence(occurrence: Any) -> planning.V075PlanningRouteV2:
    if type(occurrence.arm) is not worker.V075WorkerArmV1:
        _fail("live epoch occurrence arm is not exact")
    return (
        planning.V075PlanningRouteV2.MATCHED_DIRECT_GROUND
        if occurrence.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        else planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
    )


_RECORD_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class _LiveEpochRecordBindingV2:
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
            _fail("live-epoch record binding is caller-minted")
        self._assert_current()

    def _assert_current(self) -> None:
        _cid(self.record_id, "live-epoch record")
        _cid(self.semantic_artifact_id, "live-epoch semantic artifact")
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _ROLE_SET
            or self.artifact_schema != _ROLE_SCHEMA[self.role]
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
        ):
            _fail("live-epoch record binding is malformed")
        for value in self.dependency_record_ids:
            _cid(value, "live-epoch portable dependency")
        document = _strict_document(
            self.canonical_artifact_bytes,
            label=f"live-epoch {self.role}",
        )
        if (
            document.get("schema") != self.artifact_schema
            or document.get(_ROLE_ID_FIELD[self.role])
            != self.semantic_artifact_id
        ):
            _fail("live-epoch record bytes are role/schema-transplanted")
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
            _fail("live-epoch portable record ID is stale or rehashed")

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


def _binding_from_record(record: Any) -> _LiveEpochRecordBindingV2:
    return _LiveEpochRecordBindingV2(
        _RECORD_BINDING_ISSUER,
        record.record_id,
        record.index,
        record.role,
        record.artifact_schema,
        record.semantic_artifact_id,
        tuple(record.dependency_record_ids),
        record.canonical_artifact_bytes,
    )


def _prefix_is_strict_parent(parent: Any, child: Any) -> bool:
    return (
        len(parent.receipt_ids) < len(child.receipt_ids)
        and child.head_ids[: len(parent.head_ids)] == parent.head_ids
        and child.receipt_ids[: len(parent.receipt_ids)]
        == parent.receipt_ids
        and child.support_freeze_ids[: len(parent.support_freeze_ids)]
        == parent.support_freeze_ids
        and child.zero_head_id == parent.zero_head_id
        and child.occurrence_id == parent.occurrence_id
    )


def _derive_parent_epoch_ids(
    epoch_prefixes: Mapping[str, Any],
) -> Mapping[str, str | None]:
    result: dict[str, str | None] = {}
    for epoch_id, prefix in epoch_prefixes.items():
        candidates = tuple(
            (other_id, other)
            for other_id, other in epoch_prefixes.items()
            if other_id != epoch_id
            and _prefix_is_strict_parent(other, prefix)
        )
        if not candidates:
            result[epoch_id] = None
            continue
        maximum = max(len(item[1].receipt_ids) for item in candidates)
        nearest = tuple(
            item for item in candidates if len(item[1].receipt_ids) == maximum
        )
        if len(nearest) != 1:
            _fail("live epoch prefixes have no unique immediate parent")
        result[epoch_id] = nearest[0][0]
    roots = tuple(value for value in result.values() if value is None)
    if len(roots) != 1:
        _fail("live epoch prefix graph must have one root")
    return MappingProxyType(result)


def _reconstruct_live_epochs(
    *,
    upstream: m2_life.V075PortableConstructionLifecycleReplayV2,
    record_bindings: tuple[_LiveEpochRecordBindingV2, ...],
    _upstream_already_current: bool = False,
) -> tuple[live_model.V075LiveIncrementalModelEpochV2, ...]:
    """Rebuild epochs from the current 1.74 occurrence/control graph only."""

    if type(record_bindings) is not tuple:
        _fail("live epoch reconstruction registry is malformed")
    epoch_bindings = tuple(
        item for item in record_bindings if item.role == "LIVE_MODEL_EPOCH"
    )
    if (
        not epoch_bindings
        or len(epoch_bindings) > live_model.MAX_MODEL_EPOCHS
    ):
        _fail("live epoch registry is empty or over cap")
    graph = _control_graph(
        upstream,
        _upstream_already_current=_upstream_already_current,
    )
    occurrence = _m0_graph(
        upstream,
        _upstream_already_current=True,
    ).occurrence
    route = _route_for_occurrence(occurrence)
    prefixes: dict[str, Any] = {}
    for item in graph.open_prefixes:
        if item.verification_id in prefixes:
            _fail("open-prefix registry is duplicated")
        prefixes[item.verification_id] = item
    append_by_receipt = {
        item.receipt.receipt_id: item for item in graph.appends
    }
    freeze_by_id = {item.freeze_id: item for item in graph.support_freezes}
    if (
        len(append_by_receipt) != len(graph.appends)
        or len(freeze_by_id) != len(graph.support_freezes)
    ):
        _fail("current signed-control registries are duplicated")

    documents: dict[str, dict[str, Any]] = {}
    epoch_prefixes: dict[str, Any] = {}
    binding_by_id: dict[str, _LiveEpochRecordBindingV2] = {}
    for binding in epoch_bindings:
        binding._assert_current()
        document = _strict_document(
            binding.canonical_artifact_bytes,
            label="live model epoch",
        )
        epoch_id = binding.semantic_artifact_id
        prefix = prefixes.get(document.get("open_prefix_verification_id"))
        if prefix is None:
            _fail("live epoch lacks its exact current open prefix")
        if (
            document.get("occurrence_id") != occurrence.occurrence_id
            or document.get("context_id") != occurrence.context_id
            or document.get("arm") != occurrence.arm.value
            or document.get("route") != route.value
            or document.get("head_id") != prefix.current_head_id
            or document.get("append_receipt_ids")
            != list(prefix.receipt_ids)
            or document.get("support_freeze_ids")
            != list(prefix.support_freeze_ids)
            or tuple(
                append_by_receipt.get(value) for value in prefix.receipt_ids
            )
            != prefix.appends
            or tuple(
                freeze_by_id.get(value)
                for value in prefix.support_freeze_ids
            )
            != prefix.support_freezes
        ):
            _fail(
                "live epoch occurrence, prefix, appends, freezes, or route "
                "was transplanted"
            )
        if epoch_id in documents:
            _fail("live epoch identity is duplicated")
        documents[epoch_id] = document
        epoch_prefixes[epoch_id] = prefix
        binding_by_id[epoch_id] = binding

    parents = _derive_parent_epoch_ids(epoch_prefixes)
    for epoch_id, document in documents.items():
        if document.get("parent_epoch_id") != parents[epoch_id]:
            _fail("live epoch claimed parent differs from prefix order")

    pending = set(documents)
    rebuilt: dict[
        str,
        live_model.V075LiveIncrementalModelEpochV2,
    ] = {}
    while pending:
        ready = tuple(
            sorted(
                (
                    epoch_id
                    for epoch_id in pending
                    if parents[epoch_id] is None
                    or parents[epoch_id] in rebuilt
                ),
                key=lambda value: (
                    len(epoch_prefixes[value].receipt_ids),
                    binding_by_id[value].record_index,
                    value,
                ),
            )
        )
        if not ready:
            _fail("live epoch parent graph is cyclic or incomplete")
        for epoch_id in ready:
            prefix = epoch_prefixes[epoch_id]
            parent_id = parents[epoch_id]
            try:
                expected = live_model._build_epoch(  # noqa: SLF001
                    occurrence_identity=occurrence,
                    controlled_appends=prefix.appends,
                    support_freezes=prefix.support_freezes,
                    open_prefix_verification=prefix,
                    route=route,
                    parent_epoch=(
                        None if parent_id is None else rebuilt[parent_id]
                    ),
                    replay_parent=False,
                    register_operational=False,
                    portable_prefix_replay=True,
                )
            except Exception as error:
                raise V075PortableLiveEpochV2InvariantViolation(
                    "live epoch portable reconstruction failed"
                ) from error
            binding = binding_by_id[epoch_id]
            if (
                expected.model_epoch_id != epoch_id
                or expected.canonical_bytes
                != binding.canonical_artifact_bytes
                or expected.parent_epoch_id != parent_id
                or expected.open_prefix_verification.verification_id
                != prefix.verification_id
            ):
                _fail(
                    "live epoch bytes, source, model, proof, or identity "
                    "differ from exact portable reconstruction"
                )
            rebuilt[epoch_id] = expected
            pending.remove(epoch_id)
    return tuple(
        rebuilt[item.semantic_artifact_id] for item in epoch_bindings
    )


def _expected_row_source_bytes(
    epochs: tuple[live_model.V075LiveIncrementalModelEpochV2, ...],
) -> Mapping[str, bytes]:
    result: dict[str, bytes] = {}
    for epoch in epochs:
        for source in epoch.row_sources:
            raw = _raw(source)
            prior = result.get(source.binding_id)
            if prior is not None and prior != raw:
                _fail("one live row-source ID maps to different exact bytes")
            result[source.binding_id] = raw
    if not result:
        _fail("live row-source union is empty")
    return MappingProxyType(dict(sorted(result.items())))


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableLiveEpochTypedGraphV2:
    """Exact public epoch reconstruction bound to the hardened 1.74 graph."""

    _issuer: InitVar[object]
    bundle_id: str
    public_context_closure_id: str
    occurrence_id: str
    m2_lifecycle_result: (
        m2_life.V075PortableConstructionLifecycleReplayV2
    ) = field(repr=False)
    epochs: tuple[
        live_model.V075LiveIncrementalModelEpochV2,
        ...,
    ] = field(repr=False)
    record_bindings: tuple[_LiveEpochRecordBindingV2, ...] = field(
        repr=False
    )
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("M2 live-epoch typed graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._identity_payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "live-epoch typed graph bundle"),
            (
                self.public_context_closure_id,
                "live-epoch typed graph context",
            ),
            (self.occurrence_id, "live-epoch typed graph occurrence"),
        ):
            _cid(value, label)
        if (
            type(self.m2_lifecycle_result)
            is not m2_life.V075PortableConstructionLifecycleReplayV2
            or type(self.epochs) is not tuple
            or not self.epochs
            or any(
                type(item)
                is not live_model.V075LiveIncrementalModelEpochV2
                for item in self.epochs
            )
            or type(self.record_bindings) is not tuple
            or not self.record_bindings
            or any(
                type(item) is not _LiveEpochRecordBindingV2
                for item in self.record_bindings
            )
            or tuple(item.record_index for item in self.record_bindings)
            != tuple(
                sorted(item.record_index for item in self.record_bindings)
            )
            or len({item.record_id for item in self.record_bindings})
            != len(self.record_bindings)
        ):
            _fail("M2 live-epoch typed graph is malformed")
        self.m2_lifecycle_result._assert_current()  # noqa: SLF001
        occurrence = _m0_graph(
            self.m2_lifecycle_result,
            _upstream_already_current=True,
        ).occurrence
        if (
            self.m2_lifecycle_result.bundle_id != self.bundle_id
            or self.m2_lifecycle_result.public_context_closure_id
            != self.public_context_closure_id
            or self.m2_lifecycle_result.occurrence_id != self.occurrence_id
            or occurrence.occurrence_id != self.occurrence_id
        ):
            _fail("M2 live-epoch typed graph crossed hardened identities")

        expected_epochs = _reconstruct_live_epochs(
            upstream=self.m2_lifecycle_result,
            record_bindings=self.record_bindings,
            _upstream_already_current=True,
        )
        if tuple(
            (
                item.model_epoch_id,
                item.canonical_bytes,
                item.parent_epoch_id,
            )
            for item in self.epochs
        ) != tuple(
            (
                item.model_epoch_id,
                item.canonical_bytes,
                item.parent_epoch_id,
            )
            for item in expected_epochs
        ):
            _fail("M2 live-epoch reconstruction changed")

        expected_rows = _expected_row_source_bytes(self.epochs)
        expected_epoch_bytes = {
            item.model_epoch_id: item.canonical_bytes
            for item in self.epochs
        }
        actual_rows: dict[str, bytes] = {}
        actual_epochs: dict[str, bytes] = {}
        upstream_nodes = {
            item.record_id: item
            for item in self.m2_lifecycle_result.dependency_dag.nodes
        }
        for binding in self.record_bindings:
            binding._assert_current()
            node = upstream_nodes.get(binding.record_id)
            if (
                node is None
                or node.record_index != binding.record_index
                or node.role != binding.role
                or node.portable_declared_dependency_record_ids
                != binding.dependency_record_ids
            ):
                _fail("live-epoch record differs from hardened 1.74 spine")
            target = (
                actual_rows
                if binding.role == "LIVE_ROW_SOURCE_BINDING"
                else actual_epochs
            )
            if binding.semantic_artifact_id in target:
                _fail("live-epoch semantic artifact is duplicated")
            target[binding.semantic_artifact_id] = (
                binding.canonical_artifact_bytes
            )
        if (
            actual_rows != dict(expected_rows)
            or actual_epochs != expected_epoch_bytes
        ):
            _fail(
                "live row-source union or epoch bytes differ from exact "
                "portable reconstruction"
            )

    def _identity_payload(self) -> dict[str, Any]:
        rows = _expected_row_source_bytes(self.epochs)
        return {
            "schema": "acfqp.v075_portable_live_epoch_typed_graph.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "public_context_closure_id": self.public_context_closure_id,
            "occurrence_id": self.occurrence_id,
            "hardened_m2_lifecycle_result_id": (
                self.m2_lifecycle_result._result_id  # noqa: SLF001
            ),
            "hardened_m2_lifecycle_dependency_dag_id": (
                self.m2_lifecycle_result.dependency_dag._dag_id  # noqa: SLF001
            ),
            "ordered_epoch_ids": [
                item.model_epoch_id for item in self.epochs
            ],
            "epoch_parent_ids": [
                item.parent_epoch_id for item in self.epochs
            ],
            "row_source_union_ids": list(rows),
            "ordered_record_commitments": [
                item.commitment_document() for item in self.record_bindings
            ],
            "portable_build_epoch_flags": {
                "replay_parent": False,
                "register_operational": False,
                "portable_prefix_replay": True,
            },
            "caller_supplied_typed_epoch_accepted": False,
            "row_source_union_byte_exact": True,
            "numerical_model_semantic_authority_claimed": False,
            "numerical_proof_semantic_authority_claimed": False,
            "private_replay_performed": False,
            "private_material_serialized": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._graph_id != _hash("typed_graph", self._identity_payload()):
            _fail("M2 live-epoch typed graph identity is stale")

    @property
    def graph_id(self) -> str:
        self._assert_current()
        return self._graph_id

    def __reduce__(self) -> NoReturn:
        raise TypeError("M2 live-epoch typed graph is in-memory-only")


@dataclass(frozen=True, slots=True)
class V075PortableLiveEpochDependencyNodeV2:
    record_id: str
    record_index: int
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    resolver_kind: V075PortableLiveEpochResolverKindV2
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
        _cid(self.record_id, "live-epoch dependency node")
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
            is not V075PortableLiveEpochResolverKindV2
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
            _fail("live-epoch dependency node is malformed")
        for value in (
            *self.effective_dependency_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "live-epoch dependency edge")

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
) -> V075PortableLiveEpochResolverKindV2:
    return {
        "LIVE_ROW_SOURCE_BINDING": (
            V075PortableLiveEpochResolverKindV2
            .M2_LIVE_ROW_SOURCE_BINDING
        ),
        "LIVE_MODEL_EPOCH": (
            V075PortableLiveEpochResolverKindV2
            .M2_LIVE_MODEL_EPOCH_PUBLIC_PROJECTION
        ),
    }[role]


def _iterative_live_epoch_dependency_nodes(
    *,
    upstream_nodes: tuple[Any, ...],
    locally_replayed_record_ids: frozenset[str],
) -> tuple[V075PortableLiveEpochDependencyNodeV2, ...]:
    """Extend both 1.74 dependency lanes iteratively to arbitrary depth."""

    if (
        type(upstream_nodes) is not tuple
        or not upstream_nodes
        or type(locally_replayed_record_ids) is not frozenset
    ):
        _fail("live-epoch dependency replay requires a nonempty DAG")
    upstream_by_id: dict[str, Any] = {}
    upstream_role: dict[str, str] = {}
    upstream_depth: dict[str, int] = {}
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
            upstream_local = item.local_semantic_authority_resolved
            upstream_resolved = item.semantically_resolved
        except (AttributeError, TypeError) as error:
            raise V075PortableLiveEpochV2InvariantViolation(
                "live-epoch upstream dependency node is malformed"
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
            or any(
                value not in upstream_by_id
                for value in portable_dependencies
            )
            or type(upstream_local) is not bool
            or type(upstream_resolved) is not bool
        ):
            _fail(
                "live-epoch upstream dependency DAG or lane split is invalid"
            )
        upstream_by_id[record_id] = item
        upstream_role[record_id] = role
        upstream_depth[record_id] = 1 + max(
            (
                upstream_depth[value]
                for value in portable_dependencies
            ),
            default=0,
        )
    for value in locally_replayed_record_ids:
        _cid(value, "live-epoch local replay record")
    if not locally_replayed_record_ids <= upstream_by_id.keys():
        _fail("live-epoch local registry contains foreign records")
    for item in upstream_nodes:
        for dependency_id in (
            item.authority_local_semantic_dependency_record_ids
        ):
            if dependency_id not in upstream_by_id:
                _fail("live-epoch inherited authority-local edge is foreign")

    nodes: list[V075PortableLiveEpochDependencyNodeV2] = []
    resolved_by_id: dict[str, bool] = {}
    frontier_by_id: dict[str, tuple[str, ...]] = {}
    role_by_id: dict[str, str] = {}
    depth_by_id: dict[str, int] = {}
    for upstream in upstream_nodes:
        record_id = upstream.record_id
        role = upstream.role
        portable_dependencies = tuple(
            upstream.portable_declared_dependency_record_ids
        )
        semantic_dependencies = tuple(
            upstream.authority_local_semantic_dependency_record_ids
        )
        effective_dependencies = tuple(
            upstream.effective_dependency_record_ids
        )
        if record_id in locally_replayed_record_ids:
            if role not in _ROLE_SET:
                _fail("local live-epoch record has a foreign role")
            resolver = _target_resolver_kind(role)
            local_resolved = True
        elif upstream.local_semantic_authority_resolved:
            resolver = (
                V075PortableLiveEpochResolverKindV2
                .UPSTREAM_M2_CONSTRUCTION_LIFECYCLE
            )
            local_resolved = True
        else:
            resolver = (
                V075PortableLiveEpochResolverKindV2
                .NO_REGISTERED_SEMANTIC_AUTHORITY
            )
            local_resolved = False
        semantically_resolved = (
            local_resolved
            and all(
                resolved_by_id[value]
                for value in portable_dependencies
            )
            and all(
                upstream_by_id[value].semantically_resolved
                for value in semantic_dependencies
            )
        )
        if semantically_resolved:
            frontier: tuple[str, ...] = ()
        elif not local_resolved:
            frontier = (record_id,)
        else:
            unresolved: set[str] = set()
            for dependency_id in portable_dependencies:
                unresolved.update(frontier_by_id[dependency_id])
            for dependency_id in semantic_dependencies:
                unresolved.update(
                    upstream_by_id[
                        dependency_id
                    ].unresolved_frontier_record_ids
                )
            frontier = tuple(sorted(unresolved))
            if not frontier:
                _fail("unresolved live-epoch node lacks a proof frontier")
        frontier_roles = tuple(
            sorted(
                {
                    (
                        role
                        if value == record_id
                        else role_by_id.get(
                            value,
                            upstream_role.get(value),
                        )
                    )
                    for value in frontier
                }
            )
        )
        depth = 1 + max(
            (
                *(depth_by_id[value] for value in portable_dependencies),
                *(
                    upstream_depth[value]
                    for value in semantic_dependencies
                ),
            ),
            default=0,
        )
        node = V075PortableLiveEpochDependencyNodeV2(
            record_id,
            upstream.record_index,
            role,
            portable_dependencies,
            semantic_dependencies,
            effective_dependencies,
            resolver,
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
class V075PortableLiveEpochDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    m2_lifecycle_result: (
        m2_life.V075PortableConstructionLifecycleReplayV2
    ) = field(repr=False)
    typed_graph_id: str
    locally_replayed_record_ids: tuple[str, ...]
    nodes: tuple[V075PortableLiveEpochDependencyNodeV2, ...] = field(
        repr=False
    )
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("M2 live-epoch dependency DAG is caller-minted")
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
        _cid(self.bundle_id, "live-epoch DAG bundle")
        _cid(self.typed_graph_id, "live-epoch DAG typed graph")
        if (
            type(self.m2_lifecycle_result)
            is not m2_life.V075PortableConstructionLifecycleReplayV2
            or type(self.locally_replayed_record_ids) is not tuple
            or tuple(sorted(set(self.locally_replayed_record_ids)))
            != self.locally_replayed_record_ids
            or type(self.nodes) is not tuple
            or not self.nodes
        ):
            _fail("M2 live-epoch dependency DAG is malformed")
        if not _upstream_already_current:
            self.m2_lifecycle_result._assert_current()  # noqa: SLF001
        expected = _iterative_live_epoch_dependency_nodes(
            upstream_nodes=self.m2_lifecycle_result.dependency_dag.nodes,
            locally_replayed_record_ids=frozenset(
                self.locally_replayed_record_ids
            ),
        )
        for item in self.nodes:
            item._assert_current()
        if (
            self.m2_lifecycle_result.bundle_id != self.bundle_id
            or tuple(item.to_document() for item in self.nodes)
            != tuple(item.to_document() for item in expected)
        ):
            _fail("M2 live-epoch dependency DAG is stale or transplanted")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_live_epoch_dependency_dag.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "hardened_m2_lifecycle_result_id": (
                self.m2_lifecycle_result._result_id  # noqa: SLF001
            ),
            "hardened_m2_lifecycle_dependency_dag_id": (
                self.m2_lifecycle_result.dependency_dag._dag_id  # noqa: SLF001
            ),
            "m2_live_epoch_typed_graph_id": self.typed_graph_id,
            "locally_replayed_record_ids": list(
                self.locally_replayed_record_ids
            ),
            "nodes": [item.to_document() for item in self.nodes],
            "node_count": len(self.nodes),
            "portable_declared_edge_count": sum(
                len(item.portable_declared_dependency_record_ids)
                for item in self.nodes
            ),
            "inherited_authority_local_edge_count": sum(
                len(item.authority_local_semantic_dependency_record_ids)
                for item in self.nodes
            ),
            "maximum_dependency_depth": max(
                item.dependency_depth for item in self.nodes
            ),
            "upstream_dependency_lanes_preserved_byte_exact": True,
            "proof_shape": "ITERATIVE_TWO_LANE_DEPENDENCY_DAG",
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
            _fail("M2 live-epoch dependency DAG identity is stale")

    @property
    def dag_id(self) -> str:
        self._assert_current()
        return self._dag_id

    @property
    def nodes_by_id(
        self,
    ) -> Mapping[str, V075PortableLiveEpochDependencyNodeV2]:
        self._assert_current()
        return MappingProxyType({item.record_id: item for item in self.nodes})


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableLiveEpochRecordAttestationV2:
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
    resolver_kind: V075PortableLiveEpochResolverKindV2
    status: V075PortableLiveEpochRoleStatusV2
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("M2 live-epoch attestation is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("record_attestation", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "live-epoch attestation bundle"),
            (self.typed_graph_id, "live-epoch attestation graph"),
            (self.dependency_dag_id, "live-epoch attestation DAG"),
            (self.record_id, "live-epoch attestation record"),
            (
                self.semantic_artifact_id,
                "live-epoch attestation semantic artifact",
            ),
            (
                self.canonical_artifact_sha256,
                "live-epoch attestation digest",
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
            is not V075PortableLiveEpochResolverKindV2
            or type(self.status) is not V075PortableLiveEpochRoleStatusV2
            or self.status
            is V075PortableLiveEpochRoleStatusV2.NOT_PRESENT_IN_OCCURRENCE
        ):
            _fail("M2 live-epoch attestation is malformed")
        expected = (
            V075PortableLiveEpochRoleStatusV2.FULL_PUBLIC
            if not self.unresolved_frontier_record_ids
            else V075PortableLiveEpochRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        if self.status is not expected:
            _fail("M2 live-epoch attestation overclaims semantics")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_live_epoch_record_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m2_live_epoch_typed_graph_id": self.typed_graph_id,
            "m2_live_epoch_dependency_dag_id": self.dependency_dag_id,
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
            "private_replay_performed": False,
            "official_execution_allowed": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._attestation_id != _hash(
            "record_attestation",
            self._payload(),
        ):
            _fail("M2 live-epoch attestation identity is stale")

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
    dag: V075PortableLiveEpochDependencyDAGV2,
    bindings: tuple[_LiveEpochRecordBindingV2, ...],
    _dag_already_current: bool = False,
) -> tuple[V075PortableLiveEpochRecordAttestationV2, ...]:
    if not _dag_already_current:
        dag._assert_current()
    nodes = {item.record_id: item for item in dag.nodes}
    result = []
    for binding in bindings:
        binding._assert_current()
        node = nodes.get(binding.record_id)
        if node is None:
            _fail("live-epoch attestation record is absent from the DAG")
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
            V075PortableLiveEpochRoleStatusV2.FULL_PUBLIC
            if node.semantically_resolved
            else V075PortableLiveEpochRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        result.append(
            V075PortableLiveEpochRecordAttestationV2(
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
class V075PortableLiveEpochRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    dependency_dag_id: str
    role: str
    status: V075PortableLiveEpochRoleStatusV2
    record_ids: tuple[str, ...]
    attestation_ids: tuple[str, ...]
    unresolved_record_ids: tuple[str, ...]
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("M2 live-epoch role closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "live-epoch role closure bundle"),
            (self.typed_graph_id, "live-epoch role closure graph"),
            (self.dependency_dag_id, "live-epoch role closure DAG"),
        ):
            _cid(value, label)
        ordered_sequences = (
            self.record_ids,
            self.attestation_ids,
            self.unresolved_record_ids,
        )
        if (
            self.role not in _ROLE_SET
            or type(self.status) is not V075PortableLiveEpochRoleStatusV2
            or any(
                type(values) is not tuple
                or len(set(values)) != len(values)
                for values in ordered_sequences
            )
            or type(self.unresolved_frontier_record_ids) is not tuple
            or tuple(sorted(set(self.unresolved_frontier_record_ids)))
            != self.unresolved_frontier_record_ids
            or len(self.record_ids) != len(self.attestation_ids)
            or not set(self.unresolved_record_ids) <= set(self.record_ids)
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
        ):
            _fail("M2 live-epoch role closure is malformed")
        for value in (
            *self.record_ids,
            *self.attestation_ids,
            *self.unresolved_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "M2 live-epoch role closure identity")
        expected = (
            V075PortableLiveEpochRoleStatusV2.NOT_PRESENT_IN_OCCURRENCE
            if not self.record_ids
            else (
                V075PortableLiveEpochRoleStatusV2.FULL_PUBLIC
                if not self.unresolved_record_ids
                else V075PortableLiveEpochRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
        )
        if self.status is not expected:
            _fail("M2 live-epoch role closure status is inconsistent")
        if (
            self.status is V075PortableLiveEpochRoleStatusV2.FULL_PUBLIC
            and (
                self.unresolved_frontier_record_ids
                or self.unresolved_frontier_roles
            )
        ):
            _fail("full live-epoch role carries an unresolved frontier")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_live_epoch_role_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "m2_live_epoch_typed_graph_id": self.typed_graph_id,
            "m2_live_epoch_dependency_dag_id": self.dependency_dag_id,
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
            _fail("M2 live-epoch role closure identity is stale")

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
    bindings: tuple[_LiveEpochRecordBindingV2, ...],
    attestations: tuple[V075PortableLiveEpochRecordAttestationV2, ...],
    _attestations_already_current: bool = False,
) -> tuple[V075PortableLiveEpochRoleClosureV2, ...]:
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
            if item.status is not V075PortableLiveEpochRoleStatusV2.FULL_PUBLIC
        )
        status = (
            V075PortableLiveEpochRoleStatusV2.NOT_PRESENT_IN_OCCURRENCE
            if not role_bindings
            else (
                V075PortableLiveEpochRoleStatusV2.FULL_PUBLIC
                if not unresolved
                else V075PortableLiveEpochRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
        )
        result.append(
            V075PortableLiveEpochRoleClosureV2(
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
class V075PortableLiveEpochReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075PortableLiveEpochTypedGraphV2 = field(repr=False)
    dependency_dag: V075PortableLiveEpochDependencyDAGV2 = field(
        repr=False
    )
    attestations: tuple[V075PortableLiveEpochRecordAttestationV2, ...]
    role_closures: tuple[V075PortableLiveEpochRoleClosureV2, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("M2 live-epoch result is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "live-epoch result bundle"),
            (self.occurrence_id, "live-epoch result occurrence"),
            (
                self.public_context_closure_id,
                "live-epoch result context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph) is not V075PortableLiveEpochTypedGraphV2
            or type(self.dependency_dag)
            is not V075PortableLiveEpochDependencyDAGV2
            or type(self.attestations) is not tuple
            or any(
                type(item) is not V075PortableLiveEpochRecordAttestationV2
                for item in self.attestations
            )
            or tuple(item.record_index for item in self.attestations)
            != tuple(
                sorted(item.record_index for item in self.attestations)
            )
            or type(self.role_closures) is not tuple
            or tuple(item.role for item in self.role_closures) != ROLE_ORDER
            or any(
                type(item) is not V075PortableLiveEpochRoleClosureV2
                for item in self.role_closures
            )
        ):
            _fail("M2 live-epoch result is malformed")
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
            or self.dependency_dag.m2_lifecycle_result
            is not self.typed_graph.m2_lifecycle_result
        ):
            _fail("M2 live-epoch result crossed authority identities")
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
            _fail("M2 live-epoch attestations are stale or transplanted")
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
            _fail("M2 live-epoch role closures are stale or overclaim")
        status_by_role = {
            item.role: item.status for item in self.role_closures
        }
        if (
            status_by_role["LIVE_ROW_SOURCE_BINDING"]
            is not V075PortableLiveEpochRoleStatusV2.FULL_PUBLIC
            or status_by_role["LIVE_MODEL_EPOCH"]
            is not V075PortableLiveEpochRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        ):
            _fail("M2 live-epoch result has an invalid normative closure")

        nodes = {
            item.record_id: item for item in self.dependency_dag.nodes
        }
        row_closure = self.role_closures[0]
        epoch_closure = self.role_closures[1]
        epoch_record_ids = set(epoch_closure.record_ids)
        expected_frontier: set[str] = set()
        for record_id in epoch_record_ids:
            node = nodes[record_id]
            if (
                node.local_semantic_authority_resolved is not True
                or node.resolver_kind
                is not V075PortableLiveEpochResolverKindV2
                .M2_LIVE_MODEL_EPOCH_PUBLIC_PROJECTION
                or node.unresolved_frontier_roles
                != _UNRESOLVED_FRONTIER_ROLES
            ):
                _fail("live epoch local projection or frontier is invalid")
            expected_frontier.update(node.unresolved_frontier_record_ids)
        if (
            row_closure.unresolved_frontier_record_ids
            or row_closure.unresolved_frontier_roles
            or epoch_closure.unresolved_frontier_record_ids
            != tuple(sorted(expected_frontier))
            or epoch_closure.unresolved_frontier_roles
            != _UNRESOLVED_FRONTIER_ROLES
            or any(
                nodes[value].role not in _UNRESOLVED_FRONTIER_ROLES
                or nodes[value].semantically_resolved
                for value in expected_frontier
            )
        ):
            _fail(
                "M2 live epoch consumed or altered the exact numerical "
                "model/proof frontier"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_live_epoch_authority.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "hardened_m2_lifecycle_result_id": (
                self.typed_graph.m2_lifecycle_result._result_id  # noqa: SLF001
            ),
            "m2_live_epoch_typed_graph_id": self.typed_graph._graph_id,
            "m2_live_epoch_dependency_dag_id": (
                self.dependency_dag._dag_id
            ),
            "role_order": list(ROLE_ORDER),
            "role_statuses": {
                item.role: item.status.value for item in self.role_closures
            },
            "epoch_ids": [
                item.model_epoch_id for item in self.typed_graph.epochs
            ],
            "row_source_binding_ids": list(
                _expected_row_source_bytes(self.typed_graph.epochs)
            ),
            "record_attestation_ids": [
                item._attestation_id for item in self.attestations
            ],
            "role_closure_ids": [
                item._closure_id for item in self.role_closures
            ],
            "root_final_epoch_deduplicated_by_portable_identity": True,
            "upstream_three_edge_views_preserved": True,
            "live_row_source_semantics_complete": True,
            "live_epoch_public_projection_complete": True,
            "numerical_model_semantics_complete": False,
            "numerical_proof_semantics_complete": False,
            "hardened_1_74_called_before_local_bundle_replay": True,
            "trusted_operational_registry_accessed": False,
            "operational_parent_validation_called": False,
            "claimed_typed_epoch_input_accepted": False,
            "signer_input_consumed": False,
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
            _fail("M2 live-epoch result identity is stale")

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
            _fail("M2 live-epoch result exceeds output byte cap")
        return raw


def replay_v075_portable_live_epoch_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
) -> V075PortableLiveEpochReplayV2:
    """Replay live epochs from raw public authorities, starting with 1.74."""

    if (
        type(portable_bundle_bytes) is not bytes
        or type(public_context_closure_bytes) is not bytes
    ):
        _fail("M2 live epoch accepts canonical raw byte authorities only")
    try:
        upstream = (
            m2_life.replay_v075_portable_construction_lifecycle_v2(
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=public_context_closure_bytes,
            )
        )
    except Exception as error:
        raise V075PortableLiveEpochV2InvariantViolation(
            "M2 live epoch hardened 1.74 replay failed"
        ) from error
    try:
        bundle = (
            portable
            .verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
    except Exception as error:
        raise V075PortableLiveEpochV2InvariantViolation(
            "M2 live epoch portable bundle replay failed after 1.74"
        ) from error
    if (
        bundle.bundle_id != upstream.bundle_id
        or bundle.occurrence_id != upstream.occurrence_id
    ):
        _fail("M2 live-epoch raw authorities were transplanted")

    target_records = tuple(
        item for item in bundle.records if item.role in _ROLE_SET
    )
    bindings = tuple(_binding_from_record(item) for item in target_records)
    epochs = _reconstruct_live_epochs(
        upstream=upstream,
        record_bindings=bindings,
        _upstream_already_current=True,
    )
    typed_graph = V075PortableLiveEpochTypedGraphV2(
        _TYPED_GRAPH_ISSUER,
        bundle.bundle_id,
        upstream.public_context_closure_id,
        bundle.occurrence_id,
        upstream,
        epochs,
        bindings,
    )
    local_ids = tuple(sorted(item.record_id for item in bindings))
    nodes = _iterative_live_epoch_dependency_nodes(
        upstream_nodes=upstream.dependency_dag.nodes,
        locally_replayed_record_ids=frozenset(local_ids),
    )
    dag = V075PortableLiveEpochDependencyDAGV2(
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
    return V075PortableLiveEpochReplayV2(
        _RESULT_ISSUER,
        bundle.bundle_id,
        bundle.occurrence_id,
        upstream.public_context_closure_id,
        typed_graph,
        dag,
        attestations,
        role_closures,
    )


def open_v075_production_from_portable_live_epoch_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortableLiveEpochProductionV2NotReady(
        "M2 live epoch closes row-source semantics and reconstructs the "
        "epoch public projection, but numerical model/proof authority, "
        "source authority, code provenance, and the remaining registry "
        "are incomplete"
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
    "V075PortableLiveEpochDependencyDAGV2",
    "V075PortableLiveEpochDependencyNodeV2",
    "V075PortableLiveEpochProductionV2NotReady",
    "V075PortableLiveEpochRecordAttestationV2",
    "V075PortableLiveEpochReplayV2",
    "V075PortableLiveEpochResolverKindV2",
    "V075PortableLiveEpochRoleClosureV2",
    "V075PortableLiveEpochRoleStatusV2",
    "V075PortableLiveEpochTypedGraphV2",
    "V075PortableLiveEpochV2InvariantViolation",
    "open_v075_production_from_portable_live_epoch_v2",
    "replay_v075_portable_live_epoch_v2",
]
