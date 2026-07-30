"""V0-075 V2 construction control and locked production protocol.

The construction entry emits only a noncertificate control artifact.  Its
generic backend is post-acquisition and cannot stand in for the missing
arm-specific five-arm acquisition lifecycle.

The production signature reserves canonical-byte inputs for all portable
artifacts while keeping the salt and generated private environment in memory.
Its body is structurally non-executable: it unconditionally raises NOT_READY
until a later ledger revision implements and verifies both the five-arm
acquisition terminal and the V2 lifecycle.  No constant flip can mint a
production result or scientific endpoint credit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping, NoReturn

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_statistical_backend_v1 as identity_backend
from acfqp import v075_batch_native_total_lift_authority_v2 as total_lift
from acfqp import v075_batched_observer_authority_v2 as batched
from acfqp import v075_private_environment_generation_profile_v1 as generation
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.45.0"
PROFILE_KEY = "v075_production_occurrence_authority_v2"

MAX_STREAM_REGISTRY_BYTES = 16 * 1024 * 1024
MAX_CONSTRUCTION_CONTROL_BYTES = 64 * 1024 * 1024

PRODUCTION_ENTRY_PORTABLE_INPUTS_BYTES_ONLY = True
PER_DRAW_RECORD_INPUT_ALLOWED = False
LEGACY_AUTHORITY_PROJECTION_ALLOWED = False
OFFICIAL_EXECUTION_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
GENERIC_POST_ACQUISITION_COMPILER_ONLY = True
UPSTREAM_FIVE_ARM_ACQUISITION_TERMINAL_REQUIRED = True
PRODUCTION_BLOCKER = (
    "V2_FIVE_ARM_ACQUISITION_AND_LIFECYCLE_TERMINAL_NOT_BOUND"
)

DOMAIN_TAGS = {
    "stream_registry": "acfqp:v075-v2-compact-stream-registry:v1",
    "stream_registry_verification": (
        "acfqp:v075-v2-compact-stream-registry-verification:v1"
    ),
    "construction_control": (
        "acfqp:v075-v2-construction-occurrence-control:v1"
    ),
    "verification": (
        "acfqp:v075-v2-construction-occurrence-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 V2 occurrence content domains overlap")


class V075ProductionOccurrenceV2InvariantViolation(ValueError):
    """A byte artifact, identity, stream, lift, or terminal was invalid."""


class V075ProductionOccurrenceV2NotReady(RuntimeError):
    """The five-arm acquisition/lifecycle terminal is not yet integrated."""


def _fail(message: str) -> None:
    raise V075ProductionOccurrenceV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ProductionOccurrenceV2InvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ProductionOccurrenceV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _strict_load(raw: bytes, *, cap: int, label: str) -> Any:
    if type(raw) is not bytes or not raw or len(raw) > cap:
        _fail(f"{label} bytes are empty, mistyped, or over cap")
    try:
        value = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075ProductionOccurrenceV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if canonical_json_bytes(value) != raw:
        _fail(f"{label} is not canonical JSON")
    return value


def _stream_entry_document(
    value: graph.V075TransitionStreamIdentityV1,
) -> dict[str, Any]:
    row = value.row_binding
    epochs = []
    for epoch in value.pairing_authority.support_chain.epochs:
        evidence = []
        for item in epoch.evidence:
            if type(item) is not graph.V075BatchAggregateSupportEvidenceV1:
                _fail("V2 compact registry rejects per-draw support evidence")
            evidence.append(
                {
                    "schema": "acfqp.v075_v2_compact_batch_support.v1",
                    "observed_ranks": list(item.observed_state.ranks),
                    "observed_failure": item.observed_state.failure,
                    "source_observer_epoch_index": (
                        item.source_observer_epoch_index
                    ),
                    "discovery_request_id": item.discovery_request_id,
                    "discovery_batch_id": item.discovery_batch_id,
                    "discovery_outcome_id": item.discovery_outcome_id,
                    "discovery_outcome_count": item.discovery_outcome_count,
                    "observer_signature_hex": item.observer_signature_hex,
                }
            )
        epochs.append(
            {
                "epoch_index": epoch.epoch_index,
                "evidence": evidence,
            }
        )
    return {
        "schema": "acfqp.v075_v2_compact_stream_entry.v1",
        "stream_id": value.stream_id,
        "context_id": value.context_id,
        "source_ranks": list(row.catalogue.state.ranks),
        "source_failure": row.catalogue.state.failure,
        "remaining_horizon": row.remaining_horizon,
        "action": list(row.action),
        "arm": value.arm,
        "epochs": epochs,
    }


def freeze_v075_compact_stream_registry_bytes_v2(
    *,
    occurrence_identity: (
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    ),
    streams: Iterable[graph.V075TransitionStreamIdentityV1],
) -> bytes:
    """Serialize only the public graph needed for exact stream replay."""

    try:
        occurrence = (
            identity_backend.replay_v075_batch_native_occurrence_identity_v1(
                occurrence_identity
            )
        )
    except identity_backend.V075BatchNativeBackendInvariantViolation as error:
        raise V075ProductionOccurrenceV2InvariantViolation(
            "V2 stream registry occurrence identity is invalid"
        ) from error
    try:
        canonical = tuple(
            sorted(tuple(streams), key=lambda item: item.stream_id)
        )
    except (AttributeError, TypeError) as error:
        raise V075ProductionOccurrenceV2InvariantViolation(
            "V2 stream registry is not concrete"
        ) from error
    if (
        not canonical
        or any(
            type(item) is not graph.V075TransitionStreamIdentityV1
            for item in canonical
        )
        or len({item.stream_id for item in canonical}) != len(canonical)
        or len({item.target_tape_namespace_id for item in canonical}) != 1
        or len({item.context_id for item in canonical}) != 1
        or len({item.arm for item in canonical}) != 1
        or canonical[0].target_tape_namespace_id
        != occurrence.target_tape_namespace_id
        or canonical[0].context_id != occurrence.context_id
        or canonical[0].arm != occurrence.arm.value
    ):
        _fail(
            "V2 compact stream registry is empty, mixed, duplicated, "
            "or occurrence-transplanted"
        )
    payload = {
        "schema": "acfqp.v075_v2_compact_stream_registry.v1",
        "schema_version": SCHEMA_VERSION,
        "target_tape_namespace_id": canonical[0].target_tape_namespace_id,
        "occurrence_id": occurrence.occurrence_id,
        "context_id": occurrence.context_id,
        "arm": occurrence.arm.value,
        "stream_ids": [item.stream_id for item in canonical],
        "streams": [_stream_entry_document(item) for item in canonical],
        "per_draw_support_evidence_allowed": False,
        "private_material_serialized": False,
    }
    document = {
        **payload,
        "registry_id": _hash("stream_registry", payload),
    }
    raw = canonical_json_bytes(document)
    if len(raw) > MAX_STREAM_REGISTRY_BYTES:
        _fail("V2 compact stream registry exceeds its byte cap")
    return raw


_STREAM_REGISTRY_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075StreamRegistryVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    registry_id: str
    target_tape_namespace_id: str
    occurrence_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    stream_ids: tuple[str, ...]
    canonical_bytes_sha256: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.registry_id, "V2 stream registry")
        _cid(self.target_tape_namespace_id, "V2 stream registry namespace")
        _cid(self.occurrence_id, "V2 stream registry occurrence")
        _cid(self.context_id, "V2 stream registry context")
        _cid(self.canonical_bytes_sha256, "V2 stream registry bytes")
        if (
            self._issuer is not _STREAM_REGISTRY_VERIFICATION_ISSUER
            or type(self.arm) is not worker.V075WorkerArmV1
            or type(self.stream_ids) is not tuple
            or not self.stream_ids
            or self.stream_ids != tuple(sorted(set(self.stream_ids)))
            or any(_cid(item, "V2 compact stream") != item for item in self.stream_ids)
        ):
            _fail("V2 stream registry verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("stream_registry_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_v2_compact_stream_registry_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "registry_id": self.registry_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "stream_ids": list(self.stream_ids),
            "canonical_bytes_sha256": self.canonical_bytes_sha256,
            "semantic_reconstruction_verified": True,
            "per_draw_support_evidence_used": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def load_v075_compact_stream_registry_bytes_v2(
    *,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    occurrence_identity: (
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    ),
    raw: bytes,
) -> tuple[
    tuple[graph.V075TransitionStreamIdentityV1, ...],
    V075StreamRegistryVerificationV2,
]:
    """Reconstruct every typed stream from one compact canonical registry."""

    if type(namespace) is not namespace_v2.V075PublicTargetTapeNamespaceV2:
        _fail("V2 stream registry requires one exact V2 namespace")
    try:
        occurrence = (
            identity_backend.replay_v075_batch_native_occurrence_identity_v1(
                occurrence_identity
            )
        )
    except identity_backend.V075BatchNativeBackendInvariantViolation as error:
        raise V075ProductionOccurrenceV2InvariantViolation(
            "V2 stream registry occurrence identity is invalid"
        ) from error
    if occurrence.target_tape_namespace_id != namespace.target_tape_namespace_id:
        _fail("V2 stream registry occurrence uses a foreign namespace")
    item = _strict_load(
        raw,
        cap=MAX_STREAM_REGISTRY_BYTES,
        label="V2 compact stream registry",
    )
    expected_keys = {
        "schema",
        "schema_version",
        "target_tape_namespace_id",
        "occurrence_id",
        "context_id",
        "arm",
        "stream_ids",
        "streams",
        "per_draw_support_evidence_allowed",
        "private_material_serialized",
        "registry_id",
    }
    if (
        type(item) is not dict
        or set(item) != expected_keys
        or item["schema"] != "acfqp.v075_v2_compact_stream_registry.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["target_tape_namespace_id"]
        != namespace.target_tape_namespace_id
        or item["occurrence_id"] != occurrence.occurrence_id
        or item["context_id"] != occurrence.context_id
        or item["arm"] != occurrence.arm.value
        or item["per_draw_support_evidence_allowed"] is not False
        or item["private_material_serialized"] is not False
        or type(item["stream_ids"]) is not list
        or type(item["streams"]) is not list
        or not item["streams"]
    ):
        _fail("V2 compact stream registry schema or namespace changed")
    contexts = {
        context.context_id: context
        for context in namespace.family.replicate_contexts
    }
    replayed = []
    try:
        for entry in item["streams"]:
            if (
                type(entry) is not dict
                or set(entry)
                != {
                    "schema",
                    "stream_id",
                    "context_id",
                    "source_ranks",
                    "source_failure",
                    "remaining_horizon",
                    "action",
                    "arm",
                    "epochs",
                }
                or entry["schema"]
                != "acfqp.v075_v2_compact_stream_entry.v1"
            ):
                _fail("V2 compact stream entry schema changed")
            context = contexts[entry["context_id"]]
            state = graph.V075SymbolicGraphStateV1(
                context,
                tuple(entry["source_ranks"]),
                entry["source_failure"],
            )
            catalogue = graph.V075LegalActionCatalogueV1(
                context,
                state,
                entry["remaining_horizon"],
                graph.legal_action_triples_v1(
                    context,
                    state.ranks,
                    state.failure,
                ),
            )
            row = graph.observation_row_binding_v1(
                context,
                catalogue,
                tuple(entry["action"]),
            )
            epochs = []
            for epoch_doc in entry["epochs"]:
                if (
                    type(epoch_doc) is not dict
                    or set(epoch_doc) != {"epoch_index", "evidence"}
                    or type(epoch_doc["evidence"]) is not list
                ):
                    _fail("V2 compact support epoch is malformed")
                evidence = []
                for evidence_doc in epoch_doc["evidence"]:
                    if (
                        type(evidence_doc) is not dict
                        or set(evidence_doc)
                        != {
                            "schema",
                            "observed_ranks",
                            "observed_failure",
                            "source_observer_epoch_index",
                            "discovery_request_id",
                            "discovery_batch_id",
                            "discovery_outcome_id",
                            "discovery_outcome_count",
                            "observer_signature_hex",
                        }
                        or evidence_doc["schema"]
                        != "acfqp.v075_v2_compact_batch_support.v1"
                    ):
                        _fail("V2 compact support evidence is malformed")
                    observed = graph.V075SymbolicGraphStateV1(
                        context,
                        tuple(evidence_doc["observed_ranks"]),
                        evidence_doc["observed_failure"],
                    )
                    evidence.append(
                        graph.bind_batch_aggregate_support_evidence_v1(
                            namespace=namespace,
                            row_binding=row,
                            observed_state=observed,
                            source_observer_epoch_index=(
                                evidence_doc[
                                    "source_observer_epoch_index"
                                ]
                            ),
                            discovery_request_id=(
                                evidence_doc["discovery_request_id"]
                            ),
                            discovery_batch_id=(
                                evidence_doc["discovery_batch_id"]
                            ),
                            discovery_outcome_id=(
                                evidence_doc["discovery_outcome_id"]
                            ),
                            discovery_outcome_count=(
                                evidence_doc["discovery_outcome_count"]
                            ),
                            observer_signature_hex=(
                                evidence_doc["observer_signature_hex"]
                            ),
                        )
                    )
                epoch = graph.derive_shared_support_epoch_v1(
                    namespace=namespace,
                    row_binding=row,
                    epoch_index=epoch_doc["epoch_index"],
                    evidence=tuple(evidence),
                    parent=None if not epochs else epochs[-1],
                )
                epochs.append(epoch)
            chain = graph.freeze_shared_support_chain_v1(
                namespace=namespace,
                row_binding=row,
                epochs=tuple(epochs),
            )
            pairing = graph.freeze_five_arm_pairing_authority_v1(
                namespace=namespace,
                row_binding=row,
                support_chain=chain,
            )
            stream = graph.derive_transition_stream_identity_v1(
                pairing_authority=pairing,
                arm=entry["arm"],
            )
            if (
                stream.stream_id != entry["stream_id"]
                or _stream_entry_document(stream) != entry
            ):
                _fail("V2 compact stream differs from semantic reconstruction")
            replayed.append(stream)
    except (
        KeyError,
        TypeError,
        ValueError,
        graph.V075PublicGraphSemanticsInvariantViolation,
    ) as error:
        if type(error) is V075ProductionOccurrenceV2InvariantViolation:
            raise
        raise V075ProductionOccurrenceV2InvariantViolation(
            "V2 compact stream semantic replay failed"
        ) from error
    streams = tuple(sorted(replayed, key=lambda value: value.stream_id))
    payload = {key: value for key, value in item.items() if key != "registry_id"}
    registry_id = _hash("stream_registry", payload)
    if (
        item["registry_id"] != registry_id
        or item["stream_ids"] != [value.stream_id for value in streams]
        or len(streams) != len({value.stream_id for value in streams})
        or freeze_v075_compact_stream_registry_bytes_v2(
            occurrence_identity=occurrence,
            streams=streams,
        )
        != raw
    ):
        _fail("V2 compact stream registry ID, order, or bytes changed")
    return (
        streams,
        V075StreamRegistryVerificationV2(
            _STREAM_REGISTRY_VERIFICATION_ISSUER,
            registry_id,
            namespace.target_tape_namespace_id,
            occurrence.occurrence_id,
            occurrence.context_id,
            occurrence.arm,
            tuple(item["stream_ids"]),
            hashlib.sha256(raw).hexdigest(),
        ),
    )


def _load_occurrence_identity_bytes(
    *,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    raw: bytes,
    expected_arm: worker.V075WorkerArmV1,
    source_prior_transport_bytes: bytes | None,
) -> identity_backend.V075BatchNativeOccurrenceIdentityV1:
    try:
        return (
            identity_backend
            .load_v075_batch_native_occurrence_identity_bytes_from_namespace_v2(
                repository_root=repository_root,
                namespace=namespace,
                raw=raw,
                expected_arm=expected_arm,
                source_prior_transport_bytes=source_prior_transport_bytes,
            )
        )
    except identity_backend.V075BatchNativeBackendInvariantViolation as error:
        raise V075ProductionOccurrenceV2InvariantViolation(
            "V2 occurrence identity semantic replay failed"
        ) from error


class V075OccurrenceTerminalClassV2(str, Enum):
    ATTEMPT_CLOSURE_NONCERTIFICATE = "ATTEMPT_CLOSURE_NONCERTIFICATE"


class V075OccurrenceTerminalCodeV2(str, Enum):
    CONSTRUCTION_CONTROL_ONLY = "CONSTRUCTION_CONTROL_ONLY"


def _terminal(
    scope: total_lift.V075V2BackendScope,
    status: total_lift.V075V2TotalLiftStatus,
) -> tuple[V075OccurrenceTerminalClassV2, V075OccurrenceTerminalCodeV2]:
    if (
        scope is not total_lift.V075V2BackendScope.CONSTRUCTION_ONLY
        or type(status) is not total_lift.V075V2TotalLiftStatus
    ):
        _fail(
            "V2 occurrence terminal classifier has no production issuance "
            "path"
        )
    return (
        V075OccurrenceTerminalClassV2.ATTEMPT_CLOSURE_NONCERTIFICATE,
        V075OccurrenceTerminalCodeV2.CONSTRUCTION_CONTROL_ONLY,
    )


_CONSTRUCTION_CONTROL_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionOccurrenceControlV2:
    _issuer: object = field(repr=False, compare=False)
    scope: total_lift.V075V2BackendScope
    occurrence_identity: (
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    )
    lineage_id: str
    lineage_verification_id: str
    stream_registry_verification_id: str | None
    backend_id: str
    total_lift_result_id: str
    total_lift_status: total_lift.V075V2TotalLiftStatus
    terminal_class: V075OccurrenceTerminalClassV2
    terminal_code: V075OccurrenceTerminalCodeV2
    _control_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            identity = (
                identity_backend.replay_v075_batch_native_occurrence_identity_v1(
                    self.occurrence_identity
                )
            )
        except identity_backend.V075BatchNativeBackendInvariantViolation as error:
            raise V075ProductionOccurrenceV2InvariantViolation(str(error)) from error
        for value, label in (
            (self.lineage_id, "V2 occurrence lineage"),
            (
                self.lineage_verification_id,
                "V2 occurrence lineage verification",
            ),
            (self.backend_id, "V2 occurrence backend"),
            (self.total_lift_result_id, "V2 occurrence total lift"),
        ):
            _cid(value, label)
        if self.stream_registry_verification_id is not None:
            _cid(
                self.stream_registry_verification_id,
                "V2 occurrence stream registry verification",
            )
        expected_terminal = _terminal(
            self.scope,
            self.total_lift_status,
        )
        if (
            self._issuer is not _CONSTRUCTION_CONTROL_ISSUER
            or self.scope is not total_lift.V075V2BackendScope.CONSTRUCTION_ONLY
            or type(self.total_lift_status)
            is not total_lift.V075V2TotalLiftStatus
            or type(self.terminal_class) is not V075OccurrenceTerminalClassV2
            or type(self.terminal_code) is not V075OccurrenceTerminalCodeV2
            or (self.terminal_class, self.terminal_code) != expected_terminal
            or self.stream_registry_verification_id is not None
            or identity.occurrence_id != self.occurrence_identity.occurrence_id
        ):
            _fail("V2 occurrence result is caller-minted or misclassified")
        object.__setattr__(
            self,
            "_control_id",
            _hash("construction_control", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_v2_construction_occurrence_control.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "occurrence_identity": self.occurrence_identity.to_document(),
            "occurrence_id": self.occurrence_identity.occurrence_id,
            "lineage_id": self.lineage_id,
            "lineage_verification_id": self.lineage_verification_id,
            "stream_registry_verification_id": (
                self.stream_registry_verification_id
            ),
            "backend_id": self.backend_id,
            "total_lift_result_id": self.total_lift_result_id,
            "total_lift_status": self.total_lift_status.value,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "identity_bound": True,
            "lineage_bound": True,
            "backend_bound": True,
            "exact_total_lift_bound": True,
            "compiler_role": "POST_ACQUISITION_GENERIC",
            "arm_specific_acquisition_semantics_claimed": False,
            "upstream_v2_lifecycle_bound": False,
            "five_arm_campaign_ready": False,
            "aggregate_only": True,
            "per_draw_record_count": 0,
            "authority_version": "V2",
            "namespace_version": "V2",
            "legacy_projection_used": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def control_id(self) -> str:
        return self._control_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _issue_occurrence(
    *,
    issuer: object,
    lineage: batched.V075BatchOccurrenceLineageV2,
    lineage_verification_id: str,
    stream_registry_verification_id: str | None,
    backend: total_lift.V075V2StatisticalBackendResult,
    lift: total_lift.V075V2TotalLiftResult,
) -> V075ConstructionOccurrenceControlV2:
    if (
        backend.lineage_id != lineage.lineage_id
        or lift.backend_id != backend.backend_id
        or lift.lineage_id != lineage.lineage_id
        or lift.occurrence_id != lineage.occurrence_identity.occurrence_id
    ):
        _fail("V2 occurrence inputs were transplanted")
    terminal_class, terminal_code = _terminal(
        backend.scope,
        lift.status,
    )
    return V075ConstructionOccurrenceControlV2(
        issuer,
        backend.scope,
        lineage.occurrence_identity,
        lineage.lineage_id,
        lineage_verification_id,
        stream_registry_verification_id,
        backend.backend_id,
        lift.result_id,
        lift.status,
        terminal_class,
        terminal_code,
    )


def execute_v075_construction_occurrence_v2(
    *,
    lineage: batched.V075BatchOccurrenceLineageV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> tuple[
    total_lift.V075V2StatisticalBackendResult,
    total_lift.V075V2TotalLiftResult,
    V075ConstructionOccurrenceControlV2,
]:
    """Construction control, separate from the byte-only production entry."""

    if (
        type(lineage) is not batched.V075BatchOccurrenceLineageV2
        or lineage.scope
        is not batched.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail("construction occurrence rejects production or duck lineage")
    backend, lift = (
        total_lift.build_v075_construction_backend_and_total_lift_v2(
            lineage=lineage,
            private_salt=private_salt,
            private_environment=private_environment,
        )
    )
    result = _issue_occurrence(
        issuer=_CONSTRUCTION_CONTROL_ISSUER,
        lineage=lineage,
        lineage_verification_id=(
            lineage.closure_verification.verification_id
        ),
        stream_registry_verification_id=None,
        backend=backend,
        lift=lift,
    )
    return backend, lift, result


def execute_v075_production_occurrence_bytes_v2(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    occurrence_identity_bytes: bytes,
    source_prior_transport_bytes: bytes | None = None,
    compact_stream_registry_bytes: bytes,
    batch_closure_bytes: bytes,
    verified_acquisition_terminal_bytes: bytes,
    verified_lifecycle_bytes: bytes,
    verified_lifecycle_verification_bytes: bytes,
    private_salt: bytes,
    private_environment: generation.V075PrivateGeneratedEnvironmentV1,
) -> NoReturn:
    """Structurally locked until five-arm acquisition + V2 lifecycle bind.

    Merely changing a module constant cannot open this path.  A later ledger
    revision must replace this function with an implementation that
    independently replays the registered arm-specific acquisition terminal
    and production V2 lifecycle before any backend or total-lift issuance.
    """

    raise V075ProductionOccurrenceV2NotReady(PRODUCTION_BLOCKER)


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075OccurrenceVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    occurrence_control_id: str
    occurrence_id: str
    backend_id: str
    total_lift_result_id: str
    terminal_class: V075OccurrenceTerminalClassV2
    terminal_code: V075OccurrenceTerminalCodeV2
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_control_id, "verified V2 occurrence control"),
            (self.occurrence_id, "verified V2 occurrence"),
            (self.backend_id, "verified V2 backend"),
            (self.total_lift_result_id, "verified V2 total lift"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.terminal_class) is not V075OccurrenceTerminalClassV2
            or type(self.terminal_code) is not V075OccurrenceTerminalCodeV2
        ):
            _fail("V2 occurrence verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_v2_construction_occurrence_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_control_id": self.occurrence_control_id,
            "occurrence_id": self.occurrence_id,
            "backend_id": self.backend_id,
            "total_lift_result_id": self.total_lift_result_id,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "identity_lineage_backend_lift_recomputed": True,
            "canonical_result_bytes_replayed": True,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_construction_occurrence_bytes_v2(
    *,
    lineage: batched.V075BatchOccurrenceLineageV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
    claimed_backend_bytes: bytes,
    claimed_total_lift_bytes: bytes,
    claimed_occurrence_bytes: bytes,
) -> tuple[
    V075ConstructionOccurrenceControlV2,
    V075OccurrenceVerificationV2,
]:
    """Independently replay one complete construction occurrence chain."""

    _strict_load(
        claimed_occurrence_bytes,
        cap=MAX_CONSTRUCTION_CONTROL_BYTES,
        label="claimed V2 construction occurrence control",
    )
    backend, lift = total_lift.verify_v075_construction_total_lift_bytes_v2(
        lineage=lineage,
        private_salt=private_salt,
        private_environment=private_environment,
        claimed_backend_bytes=claimed_backend_bytes,
        claimed_total_lift_bytes=claimed_total_lift_bytes,
    )
    expected = _issue_occurrence(
        issuer=_CONSTRUCTION_CONTROL_ISSUER,
        lineage=lineage,
        lineage_verification_id=(
            lineage.closure_verification.verification_id
        ),
        stream_registry_verification_id=None,
        backend=backend,
        lift=lift,
    )
    if (
        type(claimed_occurrence_bytes) is not bytes
        or claimed_occurrence_bytes != expected.canonical_bytes
    ):
        _fail("claimed V2 occurrence bytes differ from exact recomputation")
    return (
        expected,
        V075OccurrenceVerificationV2(
            _VERIFICATION_ISSUER,
            expected.control_id,
            expected.occurrence_identity.occurrence_id,
            expected.backend_id,
            expected.total_lift_result_id,
            expected.terminal_class,
            expected.terminal_code,
        ),
    )


__all__ = [
    "LEGACY_AUTHORITY_PROJECTION_ALLOWED",
    "GENERIC_POST_ACQUISITION_COMPILER_ONLY",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PER_DRAW_RECORD_INPUT_ALLOWED",
    "PRODUCTION_ENTRY_PORTABLE_INPUTS_BYTES_ONLY",
    "PROFILE_KEY",
    "PRODUCTION_BLOCKER",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "V075OccurrenceTerminalClassV2",
    "V075OccurrenceTerminalCodeV2",
    "V075OccurrenceVerificationV2",
    "V075ConstructionOccurrenceControlV2",
    "V075ProductionOccurrenceV2InvariantViolation",
    "V075ProductionOccurrenceV2NotReady",
    "V075StreamRegistryVerificationV2",
    "UPSTREAM_FIVE_ARM_ACQUISITION_TERMINAL_REQUIRED",
    "execute_v075_construction_occurrence_v2",
    "execute_v075_production_occurrence_bytes_v2",
    "freeze_v075_compact_stream_registry_bytes_v2",
    "load_v075_compact_stream_registry_bytes_v2",
    "verify_v075_construction_occurrence_bytes_v2",
]
