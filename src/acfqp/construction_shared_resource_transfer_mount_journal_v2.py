"""Raw transfer and mount journals for three shared-resource paths.

This construction slice emits canonical V2 source components for:

* ``io.read_bytes``;
* ``io.staged_bytes``; and
* ``io.mounted_bytes_peak``.

The recorder never accepts a caller-supplied total.  Read and staged totals
are derived from individually identified transfers.  Repeated staging is a
new transfer with a new charge key and is charged again.  Mounted capacity is
derived from open/close visibility intervals; at every event boundary the
same payload identity is counted once even when multiple live intervals make
it visible to different roles.

Every operation receives an automatic continuous global sequence and an
automatic continuous path-local sequence.  Payloads and purposes are frozen
before use, all rows are occurrence/attempt/decision/window bound, and a
closed session cannot be appended to.  The public replay routine checks the
raw arithmetic and cross-component joins, but its result remains explicitly
non-semantic and cannot authorize a CounterRecord.

The domains in this independently mergeable slice use the normative
domain-separated hash algorithm locally.  They must be registered centrally
before these raw components are promoted into formal artifacts.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import re
import threading
from typing import Any, Mapping, NoReturn

from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_SHARED_RESOURCE_MOUNT_EVENT_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_MOUNT_INTERVAL_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_CHARGE_KEY_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_EVENT_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_ID_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_MOUNT_SESSION_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_PAYLOAD_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_PURPOSE_V2_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    V075_K7_MOUNT_PAYLOAD_REGISTRY_V2_DOMAIN,
    V075_K7_MOUNT_VISIBILITY_JOURNAL_V2_DOMAIN,
    V075_K7_OPERATIONAL_CUTOFF_ATTESTATION_V2_DOMAIN,
    V075_K7_READ_TRANSFER_JOURNAL_V2_DOMAIN,
    V075_K7_STAGED_TRANSFER_JOURNAL_V2_DOMAIN,
    V075_K7_TRANSFER_CHARGE_REGISTRY_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.14"
PROFILE_KEY = "construction_shared_resource_transfer_mount_journal_v2"

READ_PATH = "io.read_bytes"
STAGED_PATH = "io.staged_bytes"
MOUNTED_PATH = "io.mounted_bytes_peak"
SUPPORTED_PATHS = (MOUNTED_PATH, READ_PATH, STAGED_PATH)

CUTOFF_SCHEMA_ID = "acfqp.v075_k7_operational_cutoff_attestation.v2"
READ_JOURNAL_SCHEMA_ID = "acfqp.v075_k7_read_transfer_journal.v2"
STAGED_JOURNAL_SCHEMA_ID = "acfqp.v075_k7_staged_transfer_journal.v2"
TRANSFER_REGISTRY_SCHEMA_ID = "acfqp.v075_k7_transfer_charge_registry.v2"
MOUNT_PAYLOAD_REGISTRY_SCHEMA_ID = (
    "acfqp.v075_k7_mount_payload_registry.v2"
)
MOUNT_JOURNAL_SCHEMA_ID = "acfqp.v075_k7_mount_visibility_journal.v2"

TRANSFER_MOUNT_SESSION_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_MOUNT_SESSION_V2_DOMAIN
)
TRANSFER_PURPOSE_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_PURPOSE_V2_DOMAIN
)
TRANSFER_PAYLOAD_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_PAYLOAD_V2_DOMAIN
)
TRANSFER_ID_V2_DOMAIN = CONSTRUCTION_SHARED_RESOURCE_TRANSFER_ID_V2_DOMAIN
TRANSFER_CHARGE_KEY_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_CHARGE_KEY_V2_DOMAIN
)
TRANSFER_EVENT_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_TRANSFER_EVENT_V2_DOMAIN
)
MOUNT_INTERVAL_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_MOUNT_INTERVAL_V2_DOMAIN
)
MOUNT_EVENT_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_MOUNT_EVENT_V2_DOMAIN
)
CUTOFF_COMPONENT_V2_DOMAIN = (
    V075_K7_OPERATIONAL_CUTOFF_ATTESTATION_V2_DOMAIN
)
READ_JOURNAL_COMPONENT_V2_DOMAIN = (
    V075_K7_READ_TRANSFER_JOURNAL_V2_DOMAIN
)
STAGED_JOURNAL_COMPONENT_V2_DOMAIN = (
    V075_K7_STAGED_TRANSFER_JOURNAL_V2_DOMAIN
)
TRANSFER_REGISTRY_COMPONENT_V2_DOMAIN = (
    V075_K7_TRANSFER_CHARGE_REGISTRY_V2_DOMAIN
)
MOUNT_PAYLOAD_REGISTRY_COMPONENT_V2_DOMAIN = (
    V075_K7_MOUNT_PAYLOAD_REGISTRY_V2_DOMAIN
)
MOUNT_JOURNAL_COMPONENT_V2_DOMAIN = (
    V075_K7_MOUNT_VISIBILITY_JOURNAL_V2_DOMAIN
)

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    TRANSFER_MOUNT_SESSION_V2_DOMAIN,
    TRANSFER_PURPOSE_V2_DOMAIN,
    TRANSFER_PAYLOAD_V2_DOMAIN,
    TRANSFER_ID_V2_DOMAIN,
    TRANSFER_CHARGE_KEY_V2_DOMAIN,
    TRANSFER_EVENT_V2_DOMAIN,
    MOUNT_INTERVAL_V2_DOMAIN,
    MOUNT_EVENT_V2_DOMAIN,
    CUTOFF_COMPONENT_V2_DOMAIN,
    READ_JOURNAL_COMPONENT_V2_DOMAIN,
    STAGED_JOURNAL_COMPONENT_V2_DOMAIN,
    TRANSFER_REGISTRY_COMPONENT_V2_DOMAIN,
    MOUNT_PAYLOAD_REGISTRY_COMPONENT_V2_DOMAIN,
    MOUNT_JOURNAL_COMPONENT_V2_DOMAIN,
)
if not frozenset(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("transfer/mount journal domains are unregistered")

_COMPONENT_DOMAIN = {
    CUTOFF_SCHEMA_ID: CUTOFF_COMPONENT_V2_DOMAIN,
    READ_JOURNAL_SCHEMA_ID: READ_JOURNAL_COMPONENT_V2_DOMAIN,
    STAGED_JOURNAL_SCHEMA_ID: STAGED_JOURNAL_COMPONENT_V2_DOMAIN,
    TRANSFER_REGISTRY_SCHEMA_ID: TRANSFER_REGISTRY_COMPONENT_V2_DOMAIN,
    MOUNT_PAYLOAD_REGISTRY_SCHEMA_ID: (
        MOUNT_PAYLOAD_REGISTRY_COMPONENT_V2_DOMAIN
    ),
    MOUNT_JOURNAL_SCHEMA_ID: MOUNT_JOURNAL_COMPONENT_V2_DOMAIN,
}
_COMPONENT_ID_FIELD = {
    CUTOFF_SCHEMA_ID: "operational_cutoff_attestation_id",
    READ_JOURNAL_SCHEMA_ID: "read_transfer_journal_id",
    STAGED_JOURNAL_SCHEMA_ID: "staged_transfer_journal_id",
    TRANSFER_REGISTRY_SCHEMA_ID: "transfer_charge_registry_id",
    MOUNT_PAYLOAD_REGISTRY_SCHEMA_ID: "mount_payload_registry_id",
    MOUNT_JOURNAL_SCHEMA_ID: "mount_visibility_journal_id",
}

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_PURPOSE = re.compile(r"^[a-z][a-z0-9_.:-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_PURPOSE_ISSUER = object()
_PAYLOAD_ISSUER = object()
_INTERVAL_ISSUER = object()
_BUNDLE_ISSUER = object()
_REPLAY_ISSUER = object()


class ConstructionSharedResourceTransferMountJournalV2Error(ValueError):
    """The recorder state or one raw evidence graph is invalid."""


class TransferMountSessionStateV2(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class TransferOperationKindV2(str, Enum):
    READ = "READ"
    STAGE = "STAGE"


class MountVisibilityEventKindV2(str, Enum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"


def _fail(message: str) -> NoReturn:
    raise ConstructionSharedResourceTransferMountJournalV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceTransferMountJournalV2Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        _fail(f"{label} must be one canonical identifier")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        _fail(f"{label} must be one lowercase SHA-256 digest")
    return value


def _enum(enum_type: type[Enum], value: Any, label: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceTransferMountJournalV2Error(
            f"{label} is unknown"
        ) from error


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("transfer/mount evidence used an undeclared domain")
    return content_id(domain, dict(payload))


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceTransferMountJournalV2Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must be one canonical JSON object")
    return value


def _exact_fields(
    document: Mapping[str, Any], fields: set[str] | frozenset[str], label: str
) -> None:
    try:
        require_exact_fields(document, fields, context=label)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceTransferMountJournalV2Error(
            f"{label} fields are not exact"
        ) from error


def _identity_document(
    *,
    live_envelope_id: str,
    occurrence_id: str,
    route_attempt_id: str,
    decision_point_id: str,
    measurement_window_id: str,
) -> dict[str, str]:
    return {
        "live_envelope_id": live_envelope_id,
        "occurrence_id": occurrence_id,
        "route_attempt_id": route_attempt_id,
        "decision_point_id": decision_point_id,
        "measurement_window_id": measurement_window_id,
    }


_IDENTITY_FIELDS = frozenset(
    {
        "live_envelope_id",
        "occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "measurement_window_id",
    }
)


def _component_payload(
    schema_id: str,
    body: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": schema_id,
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        **dict(body),
        "raw_evidence_only": True,
        "semantic_source_verified": False,
        "counter_record_issued": False,
        "formal_value_authorized": False,
    }


def _freeze_component_bytes(
    schema_id: str,
    body: Mapping[str, Any],
) -> tuple[str, bytes]:
    payload = _component_payload(schema_id, body)
    artifact_id = _hash(_COMPONENT_DOMAIN[schema_id], payload)
    document = {**payload, _COMPONENT_ID_FIELD[schema_id]: artifact_id}
    return artifact_id, canonical_json_bytes(document)


def _replay_component_bytes(
    raw: bytes,
    schema_id: str,
) -> dict[str, Any]:
    document = _canonical_object(raw, schema_id)
    if document.get("schema") != schema_id:
        _fail("raw component schema crossed its catalogue role")
    id_field = _COMPONENT_ID_FIELD[schema_id]
    artifact_id = _cid(document.get(id_field), id_field)
    payload = {key: value for key, value in document.items() if key != id_field}
    if _hash(_COMPONENT_DOMAIN[schema_id], payload) != artifact_id:
        _fail("raw component content ID does not replay")
    if (
        payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("profile_key") != PROFILE_KEY
        or payload.get("raw_evidence_only") is not True
        or payload.get("semantic_source_verified") is not False
        or payload.get("counter_record_issued") is not False
        or payload.get("formal_value_authorized") is not False
    ):
        _fail("raw component attempted to claim formal authority")
    return document


@dataclass(frozen=True, slots=True)
class TransferMountPurposeRegistrationV2:
    """A purpose frozen before the first transfer/visibility event."""

    _issuer: InitVar[object]
    path: str
    purpose_key: str
    payload_role: str
    source_role: str
    target_role: str
    purpose_registration_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PURPOSE_ISSUER:
            _fail("transfer/mount purpose is caller-minted")
        if self.path not in SUPPORTED_PATHS:
            _fail("purpose path is not a supported shared resource")
        if type(self.purpose_key) is not str or _PURPOSE.fullmatch(
            self.purpose_key
        ) is None:
            _fail("purpose key is noncanonical")
        for value, label in (
            (self.payload_role, "payload role"),
            (self.source_role, "source role"),
            (self.target_role, "target role"),
        ):
            _identifier(value, label)
        payload = {
            "schema": "acfqp.construction_shared_resource_transfer_purpose.v2",
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "purpose_key": self.purpose_key,
            "payload_role": self.payload_role,
            "source_role": self.source_role,
            "target_role": self.target_role,
        }
        object.__setattr__(
            self,
            "purpose_registration_id",
            _hash(TRANSFER_PURPOSE_V2_DOMAIN, payload),
        )

    def to_document(self) -> dict[str, str]:
        return {
            "path": self.path,
            "purpose_key": self.purpose_key,
            "payload_role": self.payload_role,
            "source_role": self.source_role,
            "target_role": self.target_role,
            "purpose_registration_id": self.purpose_registration_id,
        }


def freeze_transfer_mount_purpose_v2(
    *,
    path: str,
    purpose_key: str,
    payload_role: str,
    source_role: str,
    target_role: str,
) -> TransferMountPurposeRegistrationV2:
    return TransferMountPurposeRegistrationV2(
        _PURPOSE_ISSUER,
        path,
        purpose_key,
        payload_role,
        source_role,
        target_role,
    )


@dataclass(frozen=True, slots=True)
class TransferMountPayloadV2:
    """Process-local payload authority; raw bytes never enter evidence docs."""

    _issuer: InitVar[object]
    session_binding_id: str
    payload_role: str
    payload_sha256: str
    payload_byte_count: int
    payload_identity_id: str
    _raw_bytes: bytes = field(repr=False, compare=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PAYLOAD_ISSUER:
            _fail("transfer/mount payload is caller-minted")
        _cid(self.session_binding_id, "payload session binding")
        _identifier(self.payload_role, "payload role")
        _sha256(self.payload_sha256, "payload digest")
        _nonnegative(self.payload_byte_count, "payload byte count")
        _cid(self.payload_identity_id, "payload identity")
        if type(self._raw_bytes) is not bytes:
            _fail("payload raw bytes are mistyped")
        if (
            len(self._raw_bytes) != self.payload_byte_count
            or hashlib.sha256(self._raw_bytes).hexdigest()
            != self.payload_sha256
        ):
            _fail("payload metadata differs from its raw bytes")
        expected = _hash(
            TRANSFER_PAYLOAD_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_payload.v2",
                "schema_version": SCHEMA_VERSION,
                "payload_role": self.payload_role,
                "payload_sha256": self.payload_sha256,
                "payload_byte_count": self.payload_byte_count,
            },
        )
        if expected != self.payload_identity_id:
            _fail("payload identity does not replay")

    def public_document(self) -> dict[str, Any]:
        return {
            "payload_identity_id": self.payload_identity_id,
            "payload_role": self.payload_role,
            "payload_sha256": self.payload_sha256,
            "payload_byte_count": self.payload_byte_count,
        }


@dataclass(frozen=True, slots=True)
class MountVisibilityHandleV2:
    _issuer: InitVar[object]
    session_binding_id: str
    visibility_interval_id: str
    payload_identity_id: str
    purpose_key: str

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _INTERVAL_ISSUER:
            _fail("mount visibility handle is caller-minted")
        _cid(self.session_binding_id, "visibility session binding")
        _cid(self.visibility_interval_id, "visibility interval")
        _cid(self.payload_identity_id, "visibility payload")
        if type(self.purpose_key) is not str or _PURPOSE.fullmatch(
            self.purpose_key
        ) is None:
            _fail("visibility purpose key is noncanonical")


@dataclass(frozen=True, slots=True)
class TransferMountRawReplayV2:
    """Arithmetic replay result without semantic-completeness authority."""

    _issuer: InitVar[object]
    live_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    read_bytes_sum: int
    staged_bytes_sum: int
    mounted_unique_payload_bytes_peak: int
    global_event_count: int
    semantic_source_verified: bool = False
    counter_record_issuance_authorized: bool = False

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPLAY_ISSUER:
            _fail("raw replay result is caller-minted")
        for value, label in (
            (self.live_envelope_id, "replay live envelope"),
            (self.occurrence_id, "replay occurrence"),
            (self.route_attempt_id, "replay attempt"),
            (self.decision_point_id, "replay decision"),
            (self.measurement_window_id, "replay window"),
            (self.operational_cutoff_id, "replay cutoff"),
        ):
            _cid(value, label)
        for value, label in (
            (self.read_bytes_sum, "replayed read bytes"),
            (self.staged_bytes_sum, "replayed staged bytes"),
            (
                self.mounted_unique_payload_bytes_peak,
                "replayed mounted peak",
            ),
            (self.global_event_count, "replayed event count"),
        ):
            _nonnegative(value, label)
        if (
            self.semantic_source_verified is not False
            or self.counter_record_issuance_authorized is not False
        ):
            _fail("raw arithmetic replay cannot claim semantic authority")


@dataclass(frozen=True, slots=True)
class TransferMountRawEvidenceBundleV2:
    """Issuer-owned closed raw component set for the three paths."""

    _issuer: InitVar[object]
    live_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    measurement_start_sequence: int
    operational_cutoff_sequence: int
    session_binding_id: str
    cutoff_component: resolution_v2.SharedResourceEvidenceComponentV2
    read_journal_component: resolution_v2.SharedResourceEvidenceComponentV2
    read_charge_registry_component: (
        resolution_v2.SharedResourceEvidenceComponentV2
    )
    staged_journal_component: (
        resolution_v2.SharedResourceEvidenceComponentV2
    )
    staged_charge_registry_component: (
        resolution_v2.SharedResourceEvidenceComponentV2
    )
    mount_payload_registry_component: (
        resolution_v2.SharedResourceEvidenceComponentV2
    )
    mount_journal_component: (
        resolution_v2.SharedResourceEvidenceComponentV2
    )
    raw_replay: TransferMountRawReplayV2

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BUNDLE_ISSUER:
            _fail("transfer/mount raw bundle is caller-minted")
        for value, label in (
            (self.live_envelope_id, "bundle live envelope"),
            (self.occurrence_id, "bundle occurrence"),
            (self.route_attempt_id, "bundle attempt"),
            (self.decision_point_id, "bundle decision"),
            (self.measurement_window_id, "bundle window"),
            (self.operational_cutoff_id, "bundle cutoff"),
            (self.session_binding_id, "bundle session binding"),
        ):
            _cid(value, label)
        _nonnegative(self.measurement_start_sequence, "bundle start sequence")
        _nonnegative(self.operational_cutoff_sequence, "bundle cutoff sequence")
        if self.operational_cutoff_sequence < self.measurement_start_sequence:
            _fail("bundle cutoff precedes start")
        components = (
            self.cutoff_component,
            self.read_journal_component,
            self.read_charge_registry_component,
            self.staged_journal_component,
            self.staged_charge_registry_component,
            self.mount_payload_registry_component,
            self.mount_journal_component,
        )
        if any(
            type(item) is not resolution_v2.SharedResourceEvidenceComponentV2
            for item in components
        ) or type(self.raw_replay) is not TransferMountRawReplayV2:
            _fail("bundle contains a mistyped raw component or replay")
        if (
            self.raw_replay.live_envelope_id != self.live_envelope_id
            or self.raw_replay.occurrence_id != self.occurrence_id
            or self.raw_replay.route_attempt_id != self.route_attempt_id
            or self.raw_replay.decision_point_id != self.decision_point_id
            or self.raw_replay.measurement_window_id
            != self.measurement_window_id
            or self.raw_replay.operational_cutoff_id
            != self.operational_cutoff_id
        ):
            _fail("bundle raw replay crossed its identity")

    def components_for_path(
        self, path: str
    ) -> tuple[resolution_v2.SharedResourceEvidenceComponentV2, ...]:
        if path == READ_PATH:
            rows = (
                self.cutoff_component,
                self.read_journal_component,
                self.read_charge_registry_component,
            )
        elif path == STAGED_PATH:
            rows = (
                self.cutoff_component,
                self.staged_journal_component,
                self.staged_charge_registry_component,
            )
        elif path == MOUNTED_PATH:
            rows = (
                self.cutoff_component,
                self.mount_payload_registry_component,
                self.mount_journal_component,
            )
        else:
            _fail("raw bundle requested an unsupported shared-resource path")
        return tuple(sorted(rows, key=lambda item: item.component_key))

    def live_sources_v2(
        self,
    ) -> tuple[resolution_v2.SharedResourceLiveSourceV2, ...]:
        catalogue = {
            row.path: row
            for row in resolution_v2.official_shared_resource_resolution_catalogue_v2()
        }
        rows = []
        for path in SUPPORTED_PATHS:
            contract = catalogue[path]
            rows.append(
                resolution_v2.SharedResourceLiveSourceV2(
                    self.live_envelope_id,
                    self.occurrence_id,
                    self.route_attempt_id,
                    self.decision_point_id,
                    self.measurement_window_id,
                    self.operational_cutoff_id,
                    path,
                    contract.exact_source_kind,
                    contract.required_provenance,
                    self.measurement_start_sequence,
                    self.operational_cutoff_sequence,
                    self.components_for_path(path),
                )
            )
        return tuple(rows)

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_transfer_mount_raw_bundle.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **_identity_document(
                live_envelope_id=self.live_envelope_id,
                occurrence_id=self.occurrence_id,
                route_attempt_id=self.route_attempt_id,
                decision_point_id=self.decision_point_id,
                measurement_window_id=self.measurement_window_id,
            ),
            "operational_cutoff_id": self.operational_cutoff_id,
            "measurement_start_sequence": self.measurement_start_sequence,
            "operational_cutoff_sequence": self.operational_cutoff_sequence,
            "session_binding_id": self.session_binding_id,
            "component_artifact_ids": [
                item.source_artifact_id
                for item in (
                    self.cutoff_component,
                    self.read_journal_component,
                    self.read_charge_registry_component,
                    self.staged_journal_component,
                    self.staged_charge_registry_component,
                    self.mount_payload_registry_component,
                    self.mount_journal_component,
                )
            ],
            "raw_replayed_read_bytes": self.raw_replay.read_bytes_sum,
            "raw_replayed_staged_bytes": self.raw_replay.staged_bytes_sum,
            "raw_replayed_mounted_peak": (
                self.raw_replay.mounted_unique_payload_bytes_peak
            ),
            "raw_evidence_only": True,
            "semantic_source_verified": False,
            "counter_record_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_value_authorized": False,
        }


class TransferMountJournalSessionV2:
    """Process-local append authority for one live measurement window."""

    def __init__(
        self,
        *,
        live_envelope_id: str,
        occurrence_id: str,
        route_attempt_id: str,
        decision_point_id: str,
        measurement_window_id: str,
        operational_cutoff_id: str,
        measurement_start_sequence: int,
        purposes: tuple[TransferMountPurposeRegistrationV2, ...],
    ) -> None:
        for value, label in (
            (live_envelope_id, "session live envelope"),
            (occurrence_id, "session occurrence"),
            (route_attempt_id, "session route attempt"),
            (decision_point_id, "session decision point"),
            (measurement_window_id, "session window"),
            (operational_cutoff_id, "session cutoff"),
        ):
            _cid(value, label)
        _nonnegative(measurement_start_sequence, "session start sequence")
        if (
            type(purposes) is not tuple
            or not purposes
            or any(
                type(item) is not TransferMountPurposeRegistrationV2
                for item in purposes
            )
            or tuple(
                sorted(purposes, key=lambda item: (item.path, item.purpose_key))
            )
            != purposes
            or len({(item.path, item.purpose_key) for item in purposes})
            != len(purposes)
        ):
            _fail("session purposes must be nonempty, sorted, and unique")
        if not set(SUPPORTED_PATHS) <= {item.path for item in purposes}:
            _fail("session must register at least one purpose for every path")
        identity = _identity_document(
            live_envelope_id=live_envelope_id,
            occurrence_id=occurrence_id,
            route_attempt_id=route_attempt_id,
            decision_point_id=decision_point_id,
            measurement_window_id=measurement_window_id,
        )
        binding_payload = {
            "schema": "acfqp.construction_shared_resource_transfer_mount_session.v2",
            "schema_version": SCHEMA_VERSION,
            **identity,
            "operational_cutoff_id": operational_cutoff_id,
            "measurement_start_sequence": measurement_start_sequence,
            "purpose_registration_ids": [
                item.purpose_registration_id for item in purposes
            ],
        }
        self._live_envelope_id = live_envelope_id
        self._occurrence_id = occurrence_id
        self._route_attempt_id = route_attempt_id
        self._decision_point_id = decision_point_id
        self._measurement_window_id = measurement_window_id
        self._operational_cutoff_id = operational_cutoff_id
        self._measurement_start_sequence = measurement_start_sequence
        self._session_binding_id = _hash(
            TRANSFER_MOUNT_SESSION_V2_DOMAIN, binding_payload
        )
        self._purposes = purposes
        self._purpose_by_key = {
            (item.path, item.purpose_key): item for item in purposes
        }
        self._payloads: dict[str, TransferMountPayloadV2] = {}
        self._read_rows: list[dict[str, Any]] = []
        self._staged_rows: list[dict[str, Any]] = []
        self._mount_rows: list[dict[str, Any]] = []
        self._global_index: list[dict[str, Any]] = []
        self._path_sequences = {path: 0 for path in SUPPORTED_PATHS}
        self._global_sequence = measurement_start_sequence
        self._open_intervals: dict[str, dict[str, Any]] = {}
        self._closed_interval_ids: set[str] = set()
        self._state = TransferMountSessionStateV2.OPEN
        self._bundle: TransferMountRawEvidenceBundleV2 | None = None
        self._lock = threading.RLock()

    @property
    def state(self) -> TransferMountSessionStateV2:
        return self._state

    @property
    def session_binding_id(self) -> str:
        return self._session_binding_id

    def _require_open(self) -> None:
        if self._state is not TransferMountSessionStateV2.OPEN:
            _fail("closed transfer/mount journal cannot be appended")

    def _purpose(
        self, path: str, purpose_key: str
    ) -> TransferMountPurposeRegistrationV2:
        if type(purpose_key) is not str:
            _fail("purpose key is mistyped")
        purpose = self._purpose_by_key.get((path, purpose_key))
        if purpose is None:
            _fail("operation used an unknown or wrong-path purpose")
        return purpose

    def _payload(self, value: Any) -> TransferMountPayloadV2:
        if (
            type(value) is not TransferMountPayloadV2
            or value.session_binding_id != self._session_binding_id
            or self._payloads.get(value.payload_identity_id) is not value
        ):
            _fail("payload was transplanted from another session")
        return value

    def register_payload_v2(
        self, *, payload_role: str, raw_bytes: bytes
    ) -> TransferMountPayloadV2:
        with self._lock:
            self._require_open()
            _identifier(payload_role, "registered payload role")
            if type(raw_bytes) is not bytes:
                _fail("registered payload bytes are mistyped")
            digest = hashlib.sha256(raw_bytes).hexdigest()
            byte_count = len(raw_bytes)
            payload_id = _hash(
                TRANSFER_PAYLOAD_V2_DOMAIN,
                {
                    "schema": "acfqp.construction_shared_resource_payload.v2",
                    "schema_version": SCHEMA_VERSION,
                    "payload_role": payload_role,
                    "payload_sha256": digest,
                    "payload_byte_count": byte_count,
                },
            )
            if payload_id in self._payloads:
                _fail("payload identity is already registered in this session")
            payload = TransferMountPayloadV2(
                _PAYLOAD_ISSUER,
                self._session_binding_id,
                payload_role,
                digest,
                byte_count,
                payload_id,
                raw_bytes,
            )
            self._payloads[payload_id] = payload
            return payload

    def _next_sequence(self, path: str) -> tuple[int, int]:
        self._global_sequence += 1
        self._path_sequences[path] += 1
        return self._global_sequence, self._path_sequences[path]

    def _append_global(
        self,
        *,
        global_sequence: int,
        path: str,
        path_sequence: int,
        event_kind: str,
        event_id: str,
    ) -> None:
        self._global_index.append(
            {
                "global_sequence": global_sequence,
                "path": path,
                "path_sequence": path_sequence,
                "event_kind": event_kind,
                "event_id": event_id,
            }
        )

    def _record_transfer(
        self,
        *,
        path: str,
        operation_kind: TransferOperationKindV2,
        payload: TransferMountPayloadV2,
        purpose: TransferMountPurposeRegistrationV2,
        byte_offset: int,
        transfer_byte_count: int,
    ) -> str:
        global_sequence, path_sequence = self._next_sequence(path)
        transfer_payload = {
            "schema": "acfqp.construction_shared_resource_transfer_id.v2",
            "schema_version": SCHEMA_VERSION,
            "session_binding_id": self._session_binding_id,
            "path": path,
            "operation_kind": operation_kind.value,
            "global_sequence": global_sequence,
            "path_sequence": path_sequence,
            "payload_identity_id": payload.payload_identity_id,
            "purpose_registration_id": purpose.purpose_registration_id,
            "byte_offset": byte_offset,
            "transfer_byte_count": transfer_byte_count,
        }
        transfer_id = _hash(TRANSFER_ID_V2_DOMAIN, transfer_payload)
        charge_key = _hash(
            TRANSFER_CHARGE_KEY_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_transfer_charge_key.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": self._session_binding_id,
                "path": path,
                "transfer_id": transfer_id,
                "payload_identity_id": payload.payload_identity_id,
                "purpose_registration_id": purpose.purpose_registration_id,
            },
        )
        core = {
            "global_sequence": global_sequence,
            "path_sequence": path_sequence,
            "operation_kind": operation_kind.value,
            "transfer_id": transfer_id,
            "charge_key": charge_key,
            "purpose_key": purpose.purpose_key,
            "purpose_registration_id": purpose.purpose_registration_id,
            "payload_identity_id": payload.payload_identity_id,
            "payload_role": payload.payload_role,
            "payload_sha256": payload.payload_sha256,
            "payload_byte_count": payload.payload_byte_count,
            "source_role": purpose.source_role,
            "target_role": purpose.target_role,
            "byte_offset": byte_offset,
            "transfer_byte_count": transfer_byte_count,
        }
        event_id = _hash(
            TRANSFER_EVENT_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_transfer_event.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": self._session_binding_id,
                "path": path,
                **core,
            },
        )
        row = {**core, "event_id": event_id}
        target = self._read_rows if path == READ_PATH else self._staged_rows
        target.append(row)
        self._append_global(
            global_sequence=global_sequence,
            path=path,
            path_sequence=path_sequence,
            event_kind=operation_kind.value,
            event_id=event_id,
        )
        return transfer_id

    def record_read_v2(
        self,
        *,
        payload: TransferMountPayloadV2,
        purpose_key: str,
        byte_offset: int,
        returned_bytes: bytes,
    ) -> str:
        """Record one actual returned slice; no numeric count is accepted."""

        with self._lock:
            self._require_open()
            checked = self._payload(payload)
            purpose = self._purpose(READ_PATH, purpose_key)
            if purpose.payload_role != checked.payload_role:
                _fail("read purpose does not authorize this payload role")
            _nonnegative(byte_offset, "read byte offset")
            if type(returned_bytes) is not bytes:
                _fail("read returned bytes are mistyped")
            end = byte_offset + len(returned_bytes)
            if (
                end > checked.payload_byte_count
                or checked._raw_bytes[byte_offset:end] != returned_bytes
            ):
                _fail("read bytes do not match the registered payload slice")
            return self._record_transfer(
                path=READ_PATH,
                operation_kind=TransferOperationKindV2.READ,
                payload=checked,
                purpose=purpose,
                byte_offset=byte_offset,
                transfer_byte_count=len(returned_bytes),
            )

    def record_stage_v2(
        self,
        *,
        payload: TransferMountPayloadV2,
        purpose_key: str,
    ) -> str:
        """Record one whole-payload stage/bind; repetitions charge again."""

        with self._lock:
            self._require_open()
            checked = self._payload(payload)
            purpose = self._purpose(STAGED_PATH, purpose_key)
            if purpose.payload_role != checked.payload_role:
                _fail("stage purpose does not authorize this payload role")
            return self._record_transfer(
                path=STAGED_PATH,
                operation_kind=TransferOperationKindV2.STAGE,
                payload=checked,
                purpose=purpose,
                byte_offset=0,
                transfer_byte_count=checked.payload_byte_count,
            )

    def _active_unique_payload_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    row["payload_identity_id"]
                    for row in self._open_intervals.values()
                }
            )
        )

    def _active_unique_byte_count(self) -> int:
        return sum(
            self._payloads[payload_id].payload_byte_count
            for payload_id in self._active_unique_payload_ids()
        )

    def open_mount_visibility_v2(
        self,
        *,
        payload: TransferMountPayloadV2,
        purpose_key: str,
    ) -> MountVisibilityHandleV2:
        with self._lock:
            self._require_open()
            checked = self._payload(payload)
            purpose = self._purpose(MOUNTED_PATH, purpose_key)
            if purpose.payload_role != checked.payload_role:
                _fail("mount purpose does not authorize this payload role")
            global_sequence, path_sequence = self._next_sequence(MOUNTED_PATH)
            interval_id = _hash(
                MOUNT_INTERVAL_V2_DOMAIN,
                {
                    "schema": "acfqp.construction_shared_resource_mount_interval.v2",
                    "schema_version": SCHEMA_VERSION,
                    "session_binding_id": self._session_binding_id,
                    "global_open_sequence": global_sequence,
                    "path_open_sequence": path_sequence,
                    "payload_identity_id": checked.payload_identity_id,
                    "purpose_registration_id": purpose.purpose_registration_id,
                },
            )
            interval = {
                "visibility_interval_id": interval_id,
                "payload_identity_id": checked.payload_identity_id,
                "purpose_key": purpose.purpose_key,
                "purpose_registration_id": purpose.purpose_registration_id,
                "payload_role": checked.payload_role,
                "payload_sha256": checked.payload_sha256,
                "payload_byte_count": checked.payload_byte_count,
                "source_role": purpose.source_role,
                "target_role": purpose.target_role,
            }
            self._open_intervals[interval_id] = interval
            self._append_mount_row(
                global_sequence=global_sequence,
                path_sequence=path_sequence,
                event_kind=MountVisibilityEventKindV2.OPEN,
                interval=interval,
            )
            return MountVisibilityHandleV2(
                _INTERVAL_ISSUER,
                self._session_binding_id,
                interval_id,
                checked.payload_identity_id,
                purpose.purpose_key,
            )

    def _append_mount_row(
        self,
        *,
        global_sequence: int,
        path_sequence: int,
        event_kind: MountVisibilityEventKindV2,
        interval: Mapping[str, Any],
    ) -> None:
        active_ids = self._active_unique_payload_ids()
        active_bytes = self._active_unique_byte_count()
        core = {
            "global_sequence": global_sequence,
            "path_sequence": path_sequence,
            "event_kind": event_kind.value,
            **dict(interval),
        }
        event_id = _hash(
            MOUNT_EVENT_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_mount_event.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": self._session_binding_id,
                **core,
            },
        )
        self._mount_rows.append(
            {
                **core,
                "active_unique_payload_ids_after_event": list(active_ids),
                "raw_unique_payload_bytes_after_event": active_bytes,
                "event_id": event_id,
            }
        )
        self._append_global(
            global_sequence=global_sequence,
            path=MOUNTED_PATH,
            path_sequence=path_sequence,
            event_kind=event_kind.value,
            event_id=event_id,
        )

    def close_mount_visibility_v2(
        self, handle: MountVisibilityHandleV2
    ) -> None:
        with self._lock:
            self._require_open()
            if (
                type(handle) is not MountVisibilityHandleV2
                or handle.session_binding_id != self._session_binding_id
            ):
                _fail("visibility handle was transplanted from another session")
            interval = self._open_intervals.pop(
                handle.visibility_interval_id, None
            )
            if interval is None:
                if handle.visibility_interval_id in self._closed_interval_ids:
                    _fail("visibility interval was closed more than once")
                _fail("visibility interval is unknown")
            if (
                interval["payload_identity_id"] != handle.payload_identity_id
                or interval["purpose_key"] != handle.purpose_key
            ):
                _fail("visibility handle crossed its interval")
            self._closed_interval_ids.add(handle.visibility_interval_id)
            global_sequence, path_sequence = self._next_sequence(MOUNTED_PATH)
            self._append_mount_row(
                global_sequence=global_sequence,
                path_sequence=path_sequence,
                event_kind=MountVisibilityEventKindV2.CLOSE,
                interval=interval,
            )

    def _identity(self) -> dict[str, str]:
        return _identity_document(
            live_envelope_id=self._live_envelope_id,
            occurrence_id=self._occurrence_id,
            route_attempt_id=self._route_attempt_id,
            decision_point_id=self._decision_point_id,
            measurement_window_id=self._measurement_window_id,
        )

    def _journal_body(
        self, path: str, rows: list[dict[str, Any]]
    ) -> dict[str, Any]:
        raw_sum = sum(row["transfer_byte_count"] for row in rows)
        return {
            **self._identity(),
            "operational_cutoff_id": self._operational_cutoff_id,
            "session_binding_id": self._session_binding_id,
            "path": path,
            "measurement_start_sequence": self._measurement_start_sequence,
            "operational_cutoff_sequence": self._global_sequence,
            "path_event_count": len(rows),
            "events": [dict(row) for row in rows],
            "raw_derived_sum_bytes": raw_sum,
            "caller_supplied_total_accepted": False,
        }

    def _charge_registry_body(
        self, path: str, rows: list[dict[str, Any]]
    ) -> dict[str, Any]:
        purposes = tuple(item for item in self._purposes if item.path == path)
        charges = [
            {
                "transfer_id": row["transfer_id"],
                "charge_key": row["charge_key"],
                "purpose_key": row["purpose_key"],
                "purpose_registration_id": row["purpose_registration_id"],
                "payload_identity_id": row["payload_identity_id"],
                "payload_sha256": row["payload_sha256"],
                "payload_byte_count": row["payload_byte_count"],
                "transfer_byte_count": row["transfer_byte_count"],
            }
            for row in rows
        ]
        return {
            **self._identity(),
            "operational_cutoff_id": self._operational_cutoff_id,
            "session_binding_id": self._session_binding_id,
            "path": path,
            "purpose_registrations": [item.to_document() for item in purposes],
            "charge_rows": charges,
            "each_transfer_charged_exactly_once": True,
            "repeated_staging_uses_distinct_charge_key": True,
        }

    def _mount_payload_registry_body(self) -> dict[str, Any]:
        purposes = tuple(
            item for item in self._purposes if item.path == MOUNTED_PATH
        )
        payloads = tuple(
            sorted(
                (item.public_document() for item in self._payloads.values()),
                key=lambda row: row["payload_identity_id"],
            )
        )
        return {
            **self._identity(),
            "operational_cutoff_id": self._operational_cutoff_id,
            "session_binding_id": self._session_binding_id,
            "path": MOUNTED_PATH,
            "payloads": list(payloads),
            "visibility_purpose_registrations": [
                item.to_document() for item in purposes
            ],
            "same_identity_counted_once_per_event_boundary": True,
        }

    def _mount_journal_body(self) -> dict[str, Any]:
        peak = max(
            (
                row["raw_unique_payload_bytes_after_event"]
                for row in self._mount_rows
            ),
            default=0,
        )
        return {
            **self._identity(),
            "operational_cutoff_id": self._operational_cutoff_id,
            "session_binding_id": self._session_binding_id,
            "path": MOUNTED_PATH,
            "measurement_start_sequence": self._measurement_start_sequence,
            "operational_cutoff_sequence": self._global_sequence,
            "path_event_count": len(self._mount_rows),
            "events": [dict(row) for row in self._mount_rows],
            "open_interval_count_at_cutoff": len(self._open_intervals),
            "raw_derived_unique_payload_peak_bytes": peak,
            "caller_supplied_total_accepted": False,
        }

    def _cutoff_body(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "operational_cutoff_id": self._operational_cutoff_id,
            "session_binding_id": self._session_binding_id,
            "measurement_start_sequence": self._measurement_start_sequence,
            "operational_cutoff_sequence": self._global_sequence,
            "global_event_count": len(self._global_index),
            "global_event_index": [dict(row) for row in self._global_index],
            "window_closed": True,
            "cutoff_is_inclusive": True,
        }

    @staticmethod
    def _component(
        schema_id: str,
        component_key: str,
        body: Mapping[str, Any],
    ) -> resolution_v2.SharedResourceEvidenceComponentV2:
        artifact_id, raw = _freeze_component_bytes(schema_id, body)
        return resolution_v2.SharedResourceEvidenceComponentV2(
            component_key,
            schema_id,
            artifact_id,
            hashlib.sha256(raw).hexdigest(),
            raw,
        )

    def close_v2(self) -> TransferMountRawEvidenceBundleV2:
        with self._lock:
            if self._state is TransferMountSessionStateV2.CLOSED:
                assert self._bundle is not None
                return self._bundle
            if self._open_intervals:
                _fail("cannot close raw evidence with unclosed visibility intervals")
            cutoff = self._component(
                CUTOFF_SCHEMA_ID,
                "cutoff_attestation",
                self._cutoff_body(),
            )
            read_journal = self._component(
                READ_JOURNAL_SCHEMA_ID,
                "read_transfer_journal",
                self._journal_body(READ_PATH, self._read_rows),
            )
            read_registry = self._component(
                TRANSFER_REGISTRY_SCHEMA_ID,
                "transfer_charge_registry",
                self._charge_registry_body(READ_PATH, self._read_rows),
            )
            staged_journal = self._component(
                STAGED_JOURNAL_SCHEMA_ID,
                "staged_transfer_journal",
                self._journal_body(STAGED_PATH, self._staged_rows),
            )
            staged_registry = self._component(
                TRANSFER_REGISTRY_SCHEMA_ID,
                "transfer_charge_registry",
                self._charge_registry_body(STAGED_PATH, self._staged_rows),
            )
            mount_payloads = self._component(
                MOUNT_PAYLOAD_REGISTRY_SCHEMA_ID,
                "mount_payload_registry",
                self._mount_payload_registry_body(),
            )
            mount_journal = self._component(
                MOUNT_JOURNAL_SCHEMA_ID,
                "mount_visibility_journal",
                self._mount_journal_body(),
            )
            replay = replay_transfer_mount_raw_evidence_v2(
                cutoff_bytes=cutoff.raw_bytes,
                read_journal_bytes=read_journal.raw_bytes,
                read_charge_registry_bytes=read_registry.raw_bytes,
                staged_journal_bytes=staged_journal.raw_bytes,
                staged_charge_registry_bytes=staged_registry.raw_bytes,
                mount_payload_registry_bytes=mount_payloads.raw_bytes,
                mount_journal_bytes=mount_journal.raw_bytes,
            )
            bundle = TransferMountRawEvidenceBundleV2(
                _BUNDLE_ISSUER,
                self._live_envelope_id,
                self._occurrence_id,
                self._route_attempt_id,
                self._decision_point_id,
                self._measurement_window_id,
                self._operational_cutoff_id,
                self._measurement_start_sequence,
                self._global_sequence,
                self._session_binding_id,
                cutoff,
                read_journal,
                read_registry,
                staged_journal,
                staged_registry,
                mount_payloads,
                mount_journal,
                replay,
            )
            self._bundle = bundle
            self._state = TransferMountSessionStateV2.CLOSED
            return bundle


def _purpose_from_document(row: Any, expected_path: str) -> dict[str, Any]:
    if type(row) is not dict:
        _fail("purpose registration row is not an object")
    fields = {
        "path",
        "purpose_key",
        "payload_role",
        "source_role",
        "target_role",
        "purpose_registration_id",
    }
    _exact_fields(row, fields, "purpose registration")
    if row["path"] != expected_path:
        _fail("purpose registration crossed its path")
    for key in ("payload_role", "source_role", "target_role"):
        _identifier(row[key], f"purpose {key}")
    if type(row["purpose_key"]) is not str or _PURPOSE.fullmatch(
        row["purpose_key"]
    ) is None:
        _fail("purpose registry contains a noncanonical key")
    expected = _hash(
        TRANSFER_PURPOSE_V2_DOMAIN,
        {
            "schema": "acfqp.construction_shared_resource_transfer_purpose.v2",
            "schema_version": SCHEMA_VERSION,
            "path": row["path"],
            "purpose_key": row["purpose_key"],
            "payload_role": row["payload_role"],
            "source_role": row["source_role"],
            "target_role": row["target_role"],
        },
    )
    if _cid(row["purpose_registration_id"], "purpose ID") != expected:
        _fail("purpose registration ID does not replay")
    return dict(row)


def _payload_from_document(row: Any) -> dict[str, Any]:
    if type(row) is not dict:
        _fail("payload registry row is not an object")
    fields = {
        "payload_identity_id",
        "payload_role",
        "payload_sha256",
        "payload_byte_count",
    }
    _exact_fields(row, fields, "payload registry row")
    _identifier(row["payload_role"], "registered payload role")
    _sha256(row["payload_sha256"], "registered payload digest")
    _nonnegative(row["payload_byte_count"], "registered payload byte count")
    expected = _hash(
        TRANSFER_PAYLOAD_V2_DOMAIN,
        {
            "schema": "acfqp.construction_shared_resource_payload.v2",
            "schema_version": SCHEMA_VERSION,
            "payload_role": row["payload_role"],
            "payload_sha256": row["payload_sha256"],
            "payload_byte_count": row["payload_byte_count"],
        },
    )
    if _cid(row["payload_identity_id"], "registered payload ID") != expected:
        _fail("payload identity does not replay")
    return dict(row)


def _identity_tuple(document: Mapping[str, Any]) -> tuple[str, ...]:
    result = tuple(_cid(document.get(key), key) for key in sorted(_IDENTITY_FIELDS))
    _cid(document.get("operational_cutoff_id"), "operational cutoff")
    _cid(document.get("session_binding_id"), "session binding")
    return result + (
        document["operational_cutoff_id"],
        document["session_binding_id"],
    )


_COMMON_COMPONENT_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "raw_evidence_only",
    "semantic_source_verified",
    "counter_record_issued",
    "formal_value_authorized",
}


def _replay_transfer_path(
    *,
    journal: Mapping[str, Any],
    registry: Mapping[str, Any],
    path: str,
    operation_kind: TransferOperationKindV2,
) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]]]:
    journal_fields = _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | {
        _COMPONENT_ID_FIELD[journal["schema"]],
        "operational_cutoff_id",
        "session_binding_id",
        "path",
        "measurement_start_sequence",
        "operational_cutoff_sequence",
        "path_event_count",
        "events",
        "raw_derived_sum_bytes",
        "caller_supplied_total_accepted",
    }
    registry_fields = _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | {
        "transfer_charge_registry_id",
        "operational_cutoff_id",
        "session_binding_id",
        "path",
        "purpose_registrations",
        "charge_rows",
        "each_transfer_charged_exactly_once",
        "repeated_staging_uses_distinct_charge_key",
    }
    _exact_fields(journal, journal_fields, f"{path} journal")
    _exact_fields(registry, registry_fields, f"{path} charge registry")
    if (
        journal["path"] != path
        or registry["path"] != path
        or _identity_tuple(journal) != _identity_tuple(registry)
        or journal["caller_supplied_total_accepted"] is not False
        or registry["each_transfer_charged_exactly_once"] is not True
        or registry["repeated_staging_uses_distinct_charge_key"] is not True
    ):
        _fail("transfer journal/registry binding or raw authority flags changed")
    purposes_raw = registry["purpose_registrations"]
    if type(purposes_raw) is not list or not purposes_raw:
        _fail("transfer charge registry lacks its frozen purposes")
    purposes = [_purpose_from_document(row, path) for row in purposes_raw]
    purpose_by_key = {row["purpose_key"]: row for row in purposes}
    if len(purpose_by_key) != len(purposes):
        _fail("transfer purpose registry repeats a purpose key")
    events = journal["events"]
    charges = registry["charge_rows"]
    if type(events) is not list or type(charges) is not list:
        _fail("transfer events or charges are not arrays")
    _nonnegative(journal["path_event_count"], "transfer path event count")
    if journal["path_event_count"] != len(events):
        _fail("transfer path event count differs from its rows")
    transfer_ids: set[str] = set()
    event_ids: set[str] = set()
    charge_keys: set[str] = set()
    expected_charges: list[dict[str, Any]] = []
    replayed_sum = 0
    event_index: list[dict[str, Any]] = []
    for expected_sequence, raw_row in enumerate(events, start=1):
        if type(raw_row) is not dict:
            _fail("transfer event row is not an object")
        fields = {
            "global_sequence",
            "path_sequence",
            "operation_kind",
            "transfer_id",
            "charge_key",
            "purpose_key",
            "purpose_registration_id",
            "payload_identity_id",
            "payload_role",
            "payload_sha256",
            "payload_byte_count",
            "source_role",
            "target_role",
            "byte_offset",
            "transfer_byte_count",
            "event_id",
        }
        _exact_fields(raw_row, fields, "transfer event")
        row = dict(raw_row)
        if row["path_sequence"] != expected_sequence:
            _fail("transfer journal has a missing or repeated path sequence")
        _positive(row["global_sequence"], "transfer global sequence")
        if row["operation_kind"] != operation_kind.value:
            _fail("transfer operation kind crossed its path")
        purpose = purpose_by_key.get(row["purpose_key"])
        if purpose is None:
            _fail("transfer row used an unknown purpose")
        if (
            row["purpose_registration_id"]
            != purpose["purpose_registration_id"]
            or row["payload_role"] != purpose["payload_role"]
            or row["source_role"] != purpose["source_role"]
            or row["target_role"] != purpose["target_role"]
        ):
            _fail("transfer row crossed its purpose registration")
        _cid(row["payload_identity_id"], "transfer payload")
        _sha256(row["payload_sha256"], "transfer payload digest")
        _nonnegative(row["payload_byte_count"], "transfer payload bytes")
        _nonnegative(row["byte_offset"], "transfer byte offset")
        _nonnegative(row["transfer_byte_count"], "transfer byte count")
        if row["byte_offset"] + row["transfer_byte_count"] > row[
            "payload_byte_count"
        ]:
            _fail("transfer byte interval exceeds its payload")
        if path == STAGED_PATH and (
            row["byte_offset"] != 0
            or row["transfer_byte_count"] != row["payload_byte_count"]
        ):
            _fail("staged transfer is not one whole-payload charge")
        expected_payload_id = _hash(
            TRANSFER_PAYLOAD_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_payload.v2",
                "schema_version": SCHEMA_VERSION,
                "payload_role": row["payload_role"],
                "payload_sha256": row["payload_sha256"],
                "payload_byte_count": row["payload_byte_count"],
            },
        )
        if row["payload_identity_id"] != expected_payload_id:
            _fail("transfer payload identity does not replay")
        expected_transfer_id = _hash(
            TRANSFER_ID_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_transfer_id.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": journal["session_binding_id"],
                "path": path,
                "operation_kind": operation_kind.value,
                "global_sequence": row["global_sequence"],
                "path_sequence": row["path_sequence"],
                "payload_identity_id": row["payload_identity_id"],
                "purpose_registration_id": row["purpose_registration_id"],
                "byte_offset": row["byte_offset"],
                "transfer_byte_count": row["transfer_byte_count"],
            },
        )
        if row["transfer_id"] != expected_transfer_id:
            _fail("transfer ID does not replay")
        expected_charge_key = _hash(
            TRANSFER_CHARGE_KEY_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_transfer_charge_key.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": journal["session_binding_id"],
                "path": path,
                "transfer_id": row["transfer_id"],
                "payload_identity_id": row["payload_identity_id"],
                "purpose_registration_id": row["purpose_registration_id"],
            },
        )
        if row["charge_key"] != expected_charge_key:
            _fail("transfer charge key does not replay")
        event_core = {
            key: row[key]
            for key in fields
            if key != "event_id"
        }
        expected_event_id = _hash(
            TRANSFER_EVENT_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_transfer_event.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": journal["session_binding_id"],
                "path": path,
                **event_core,
            },
        )
        if row["event_id"] != expected_event_id:
            _fail("transfer event ID does not replay")
        if (
            row["transfer_id"] in transfer_ids
            or row["event_id"] in event_ids
            or row["charge_key"] in charge_keys
        ):
            _fail("transfer journal repeats an event, transfer, or charge ID")
        transfer_ids.add(row["transfer_id"])
        event_ids.add(row["event_id"])
        charge_keys.add(row["charge_key"])
        replayed_sum += row["transfer_byte_count"]
        expected_charges.append(
            {
                "transfer_id": row["transfer_id"],
                "charge_key": row["charge_key"],
                "purpose_key": row["purpose_key"],
                "purpose_registration_id": row["purpose_registration_id"],
                "payload_identity_id": row["payload_identity_id"],
                "payload_sha256": row["payload_sha256"],
                "payload_byte_count": row["payload_byte_count"],
                "transfer_byte_count": row["transfer_byte_count"],
            }
        )
        event_index.append(
            {
                "global_sequence": row["global_sequence"],
                "path": path,
                "path_sequence": row["path_sequence"],
                "event_kind": operation_kind.value,
                "event_id": row["event_id"],
            }
        )
    if charges != expected_charges:
        _fail("transfer charge registry has a missing, duplicate, or extra charge")
    if journal["raw_derived_sum_bytes"] != replayed_sum:
        _fail("raw transfer sum is under-counted or double-counted")
    return replayed_sum, event_index, purposes


def _replay_mount(
    *,
    payload_registry: Mapping[str, Any],
    journal: Mapping[str, Any],
) -> tuple[int, list[dict[str, Any]]]:
    registry_fields = _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | {
        "mount_payload_registry_id",
        "operational_cutoff_id",
        "session_binding_id",
        "path",
        "payloads",
        "visibility_purpose_registrations",
        "same_identity_counted_once_per_event_boundary",
    }
    journal_fields = _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | {
        "mount_visibility_journal_id",
        "operational_cutoff_id",
        "session_binding_id",
        "path",
        "measurement_start_sequence",
        "operational_cutoff_sequence",
        "path_event_count",
        "events",
        "open_interval_count_at_cutoff",
        "raw_derived_unique_payload_peak_bytes",
        "caller_supplied_total_accepted",
    }
    _exact_fields(payload_registry, registry_fields, "mount payload registry")
    _exact_fields(journal, journal_fields, "mount visibility journal")
    if (
        payload_registry["path"] != MOUNTED_PATH
        or journal["path"] != MOUNTED_PATH
        or _identity_tuple(payload_registry) != _identity_tuple(journal)
        or payload_registry[
            "same_identity_counted_once_per_event_boundary"
        ]
        is not True
        or journal["caller_supplied_total_accepted"] is not False
    ):
        _fail("mount registry/journal binding or authority flags changed")
    payload_rows = payload_registry["payloads"]
    purpose_rows = payload_registry["visibility_purpose_registrations"]
    events = journal["events"]
    if (
        type(payload_rows) is not list
        or type(purpose_rows) is not list
        or not purpose_rows
        or type(events) is not list
    ):
        _fail("mount payloads, purposes, or events have the wrong type")
    payloads = [_payload_from_document(row) for row in payload_rows]
    payload_by_id = {row["payload_identity_id"]: row for row in payloads}
    if len(payload_by_id) != len(payloads):
        _fail("mount payload registry repeats a payload identity")
    purposes = [
        _purpose_from_document(row, MOUNTED_PATH) for row in purpose_rows
    ]
    purpose_by_key = {row["purpose_key"]: row for row in purposes}
    if len(purpose_by_key) != len(purposes):
        _fail("mount purpose registry repeats a purpose key")
    _nonnegative(journal["path_event_count"], "mount event count")
    if journal["path_event_count"] != len(events):
        _fail("mount event count differs from its rows")
    open_intervals: dict[str, str] = {}
    closed_intervals: set[str] = set()
    event_ids: set[str] = set()
    peak = 0
    event_index: list[dict[str, Any]] = []
    for expected_sequence, raw_row in enumerate(events, start=1):
        if type(raw_row) is not dict:
            _fail("mount event row is not an object")
        fields = {
            "global_sequence",
            "path_sequence",
            "event_kind",
            "visibility_interval_id",
            "payload_identity_id",
            "purpose_key",
            "purpose_registration_id",
            "payload_role",
            "payload_sha256",
            "payload_byte_count",
            "source_role",
            "target_role",
            "active_unique_payload_ids_after_event",
            "raw_unique_payload_bytes_after_event",
            "event_id",
        }
        _exact_fields(raw_row, fields, "mount event")
        row = dict(raw_row)
        if row["path_sequence"] != expected_sequence:
            _fail("mount journal has a missing or repeated path sequence")
        _positive(row["global_sequence"], "mount global sequence")
        event_kind = _enum(
            MountVisibilityEventKindV2,
            row["event_kind"],
            "mount event kind",
        )
        interval_id = _cid(row["visibility_interval_id"], "mount interval")
        payload = payload_by_id.get(row["payload_identity_id"])
        purpose = purpose_by_key.get(row["purpose_key"])
        if payload is None:
            _fail("mount event references an unknown payload")
        if purpose is None:
            _fail("mount event used an unknown purpose")
        if (
            row["purpose_registration_id"]
            != purpose["purpose_registration_id"]
            or row["payload_role"] != purpose["payload_role"]
            or row["payload_role"] != payload["payload_role"]
            or row["payload_sha256"] != payload["payload_sha256"]
            or row["payload_byte_count"] != payload["payload_byte_count"]
            or row["source_role"] != purpose["source_role"]
            or row["target_role"] != purpose["target_role"]
        ):
            _fail("mount row crossed its payload or purpose")
        if event_kind is MountVisibilityEventKindV2.OPEN:
            if interval_id in open_intervals or interval_id in closed_intervals:
                _fail("mount interval ID is duplicated")
            expected_interval_id = _hash(
                MOUNT_INTERVAL_V2_DOMAIN,
                {
                    "schema": "acfqp.construction_shared_resource_mount_interval.v2",
                    "schema_version": SCHEMA_VERSION,
                    "session_binding_id": journal["session_binding_id"],
                    "global_open_sequence": row["global_sequence"],
                    "path_open_sequence": row["path_sequence"],
                    "payload_identity_id": row["payload_identity_id"],
                    "purpose_registration_id": row[
                        "purpose_registration_id"
                    ],
                },
            )
            if interval_id != expected_interval_id:
                _fail("mount interval ID does not replay")
            open_intervals[interval_id] = row["payload_identity_id"]
        else:
            opened_payload = open_intervals.pop(interval_id, None)
            if opened_payload is None:
                _fail("mount close lacks one unique prior open")
            if opened_payload != row["payload_identity_id"]:
                _fail("mount close crossed its opened payload")
            closed_intervals.add(interval_id)
        core = {
            key: row[key]
            for key in fields
            if key
            not in {
                "active_unique_payload_ids_after_event",
                "raw_unique_payload_bytes_after_event",
                "event_id",
            }
        }
        expected_event_id = _hash(
            MOUNT_EVENT_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_mount_event.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": journal["session_binding_id"],
                **core,
            },
        )
        if row["event_id"] != expected_event_id:
            _fail("mount event ID does not replay")
        if row["event_id"] in event_ids:
            _fail("mount journal repeats an event ID")
        event_ids.add(row["event_id"])
        unique_ids = sorted(set(open_intervals.values()))
        unique_bytes = sum(payload_by_id[item]["payload_byte_count"] for item in unique_ids)
        if (
            row["active_unique_payload_ids_after_event"] != unique_ids
            or row["raw_unique_payload_bytes_after_event"] != unique_bytes
        ):
            _fail("mounted bytes were double-counted or under-counted")
        peak = max(peak, unique_bytes)
        event_index.append(
            {
                "global_sequence": row["global_sequence"],
                "path": MOUNTED_PATH,
                "path_sequence": row["path_sequence"],
                "event_kind": event_kind.value,
                "event_id": row["event_id"],
            }
        )
    if open_intervals or journal["open_interval_count_at_cutoff"] != 0:
        _fail("mount visibility journal has an unclosed interval")
    if journal["raw_derived_unique_payload_peak_bytes"] != peak:
        _fail("mounted peak was double-counted or under-counted")
    return peak, event_index


def replay_transfer_mount_raw_evidence_v2(
    *,
    cutoff_bytes: bytes,
    read_journal_bytes: bytes,
    read_charge_registry_bytes: bytes,
    staged_journal_bytes: bytes,
    staged_charge_registry_bytes: bytes,
    mount_payload_registry_bytes: bytes,
    mount_journal_bytes: bytes,
) -> TransferMountRawReplayV2:
    """Replay raw structure/arithmetic without asserting capture completeness."""

    cutoff = _replay_component_bytes(cutoff_bytes, CUTOFF_SCHEMA_ID)
    read_journal = _replay_component_bytes(
        read_journal_bytes, READ_JOURNAL_SCHEMA_ID
    )
    read_registry = _replay_component_bytes(
        read_charge_registry_bytes, TRANSFER_REGISTRY_SCHEMA_ID
    )
    staged_journal = _replay_component_bytes(
        staged_journal_bytes, STAGED_JOURNAL_SCHEMA_ID
    )
    staged_registry = _replay_component_bytes(
        staged_charge_registry_bytes, TRANSFER_REGISTRY_SCHEMA_ID
    )
    mount_payloads = _replay_component_bytes(
        mount_payload_registry_bytes, MOUNT_PAYLOAD_REGISTRY_SCHEMA_ID
    )
    mount_journal = _replay_component_bytes(
        mount_journal_bytes, MOUNT_JOURNAL_SCHEMA_ID
    )
    cutoff_fields = _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | {
        "operational_cutoff_attestation_id",
        "operational_cutoff_id",
        "session_binding_id",
        "measurement_start_sequence",
        "operational_cutoff_sequence",
        "global_event_count",
        "global_event_index",
        "window_closed",
        "cutoff_is_inclusive",
    }
    _exact_fields(cutoff, cutoff_fields, "operational cutoff attestation")
    if cutoff["window_closed"] is not True or cutoff["cutoff_is_inclusive"] is not True:
        _fail("operational cutoff is not one closed inclusive window")
    identity = _identity_tuple(cutoff)
    for component in (
        read_journal,
        read_registry,
        staged_journal,
        staged_registry,
        mount_payloads,
        mount_journal,
    ):
        if _identity_tuple(component) != identity:
            _fail("raw evidence component crossed occurrence/window identity")
    read_sum, read_index, _read_purposes = _replay_transfer_path(
        journal=read_journal,
        registry=read_registry,
        path=READ_PATH,
        operation_kind=TransferOperationKindV2.READ,
    )
    staged_sum, staged_index, _stage_purposes = _replay_transfer_path(
        journal=staged_journal,
        registry=staged_registry,
        path=STAGED_PATH,
        operation_kind=TransferOperationKindV2.STAGE,
    )
    mounted_peak, mount_index = _replay_mount(
        payload_registry=mount_payloads,
        journal=mount_journal,
    )
    event_index = sorted(
        read_index + staged_index + mount_index,
        key=lambda row: row["global_sequence"],
    )
    start = _nonnegative(
        cutoff["measurement_start_sequence"], "cutoff start sequence"
    )
    end = _nonnegative(
        cutoff["operational_cutoff_sequence"], "cutoff sequence"
    )
    count = _nonnegative(cutoff["global_event_count"], "global event count")
    if (
        count != len(event_index)
        or end != start + count
        or [row["global_sequence"] for row in event_index]
        != list(range(start + 1, end + 1))
        or cutoff["global_event_index"] != event_index
    ):
        _fail("global event sequence is missing, repeated, or reordered")
    for journal in (read_journal, staged_journal, mount_journal):
        if (
            journal["measurement_start_sequence"] != start
            or journal["operational_cutoff_sequence"] != end
        ):
            _fail("path journal crossed the global measurement window")
    return TransferMountRawReplayV2(
        _REPLAY_ISSUER,
        cutoff["live_envelope_id"],
        cutoff["occurrence_id"],
        cutoff["route_attempt_id"],
        cutoff["decision_point_id"],
        cutoff["measurement_window_id"],
        cutoff["operational_cutoff_id"],
        read_sum,
        staged_sum,
        mounted_peak,
        count,
        False,
        False,
    )


__all__ = [
    "CUTOFF_SCHEMA_ID",
    "ConstructionSharedResourceTransferMountJournalV2Error",
    "MOUNTED_PATH",
    "MOUNT_JOURNAL_SCHEMA_ID",
    "MOUNT_PAYLOAD_REGISTRY_SCHEMA_ID",
    "MountVisibilityEventKindV2",
    "MountVisibilityHandleV2",
    "PROFILE_KEY",
    "READ_JOURNAL_SCHEMA_ID",
    "READ_PATH",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "STAGED_JOURNAL_SCHEMA_ID",
    "STAGED_PATH",
    "SUPPORTED_PATHS",
    "TRANSFER_REGISTRY_SCHEMA_ID",
    "TransferMountJournalSessionV2",
    "TransferMountPayloadV2",
    "TransferMountPurposeRegistrationV2",
    "TransferMountRawEvidenceBundleV2",
    "TransferMountRawReplayV2",
    "TransferMountSessionStateV2",
    "TransferOperationKindV2",
    "freeze_transfer_mount_purpose_v2",
    "replay_transfer_mount_raw_evidence_v2",
]
