"""Raw V2 journals for construction hash, integrity, and protocol work.

The recorder freezes exact purpose, obligation, and loaded-source-site
registries before the measurement window starts.  It then appends typed events
with automatic broker-global and path-local sequences.  Each event binds an
authenticated broker observation ID plus canonical input/output artifact IDs.

No API accepts a total.  On close, canonical components are emitted for the
exact schemas required by :mod:`construction_shared_resource_resolution_v2`.
Independent replay derives the three counts and proves exact joins among the
transcripts, registries, source-site attestations, and inclusive cutoff.

This is raw evidence only.  It does not prove that every runtime operation was
captured, does not mark source semantics verified, and cannot issue a
CounterRecord.  Local provisional domains must be registered centrally before
formal promotion.
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
    CONSTRUCTION_SHARED_RESOURCE_BROKER_OBSERVATION_BINDING_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_COMMON_EVENT_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_COMMON_SESSION_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_COMMON_SOURCE_SITE_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_HASH_PURPOSE_V2_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_NAMED_OBLIGATION_V2_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    V075_K7_HASH_EVENT_TRANSCRIPT_V2_DOMAIN,
    V075_K7_HASH_PURPOSE_REGISTRY_V2_DOMAIN,
    V075_K7_INTEGRITY_OBLIGATION_REGISTRY_V2_DOMAIN,
    V075_K7_INTEGRITY_OBLIGATION_TRANSCRIPT_V2_DOMAIN,
    V075_K7_LOADED_HASH_SITE_ATTESTATION_V2_DOMAIN,
    V075_K7_LOADED_INTEGRITY_SITE_ATTESTATION_V2_DOMAIN,
    V075_K7_LOADED_PROTOCOL_SITE_ATTESTATION_V2_DOMAIN,
    V075_K7_OPERATIONAL_CUTOFF_ATTESTATION_V2_DOMAIN,
    V075_K7_PROTOCOL_OBLIGATION_REGISTRY_V2_DOMAIN,
    V075_K7_PROTOCOL_OBLIGATION_TRANSCRIPT_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.16"
PROFILE_KEY = "construction_shared_resource_common_journal_v2"

HASH_PATH = "common.hash_invocations"
INTEGRITY_PATH = "common.integrity_checks"
PROTOCOL_PATH = "common.protocol_checks"
SUPPORTED_PATHS = (HASH_PATH, INTEGRITY_PATH, PROTOCOL_PATH)

CUTOFF_SCHEMA_ID = "acfqp.v075_k7_operational_cutoff_attestation.v2"
HASH_TRANSCRIPT_SCHEMA_ID = "acfqp.v075_k7_hash_event_transcript.v2"
HASH_PURPOSE_REGISTRY_SCHEMA_ID = (
    "acfqp.v075_k7_hash_purpose_registry.v2"
)
HASH_SITE_SCHEMA_ID = "acfqp.v075_k7_loaded_hash_site_attestation.v2"
INTEGRITY_REGISTRY_SCHEMA_ID = (
    "acfqp.v075_k7_integrity_obligation_registry.v2"
)
INTEGRITY_TRANSCRIPT_SCHEMA_ID = (
    "acfqp.v075_k7_integrity_obligation_transcript.v2"
)
INTEGRITY_SITE_SCHEMA_ID = (
    "acfqp.v075_k7_loaded_integrity_site_attestation.v2"
)
PROTOCOL_REGISTRY_SCHEMA_ID = (
    "acfqp.v075_k7_protocol_obligation_registry.v2"
)
PROTOCOL_TRANSCRIPT_SCHEMA_ID = (
    "acfqp.v075_k7_protocol_obligation_transcript.v2"
)
PROTOCOL_SITE_SCHEMA_ID = (
    "acfqp.v075_k7_loaded_protocol_site_attestation.v2"
)

COMMON_SESSION_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_COMMON_SESSION_V2_DOMAIN
)
COMMON_SOURCE_SITE_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_COMMON_SOURCE_SITE_V2_DOMAIN
)
HASH_PURPOSE_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_HASH_PURPOSE_V2_DOMAIN
)
NAMED_OBLIGATION_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_NAMED_OBLIGATION_V2_DOMAIN
)
BROKER_OBSERVATION_BINDING_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_BROKER_OBSERVATION_BINDING_V2_DOMAIN
)
COMMON_EVENT_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_COMMON_EVENT_V2_DOMAIN
)

_COMPONENT_DOMAIN = {
    CUTOFF_SCHEMA_ID: V075_K7_OPERATIONAL_CUTOFF_ATTESTATION_V2_DOMAIN,
    HASH_TRANSCRIPT_SCHEMA_ID: V075_K7_HASH_EVENT_TRANSCRIPT_V2_DOMAIN,
    HASH_PURPOSE_REGISTRY_SCHEMA_ID: V075_K7_HASH_PURPOSE_REGISTRY_V2_DOMAIN,
    HASH_SITE_SCHEMA_ID: V075_K7_LOADED_HASH_SITE_ATTESTATION_V2_DOMAIN,
    INTEGRITY_REGISTRY_SCHEMA_ID: (
        V075_K7_INTEGRITY_OBLIGATION_REGISTRY_V2_DOMAIN
    ),
    INTEGRITY_TRANSCRIPT_SCHEMA_ID: (
        V075_K7_INTEGRITY_OBLIGATION_TRANSCRIPT_V2_DOMAIN
    ),
    INTEGRITY_SITE_SCHEMA_ID: (
        V075_K7_LOADED_INTEGRITY_SITE_ATTESTATION_V2_DOMAIN
    ),
    PROTOCOL_REGISTRY_SCHEMA_ID: (
        V075_K7_PROTOCOL_OBLIGATION_REGISTRY_V2_DOMAIN
    ),
    PROTOCOL_TRANSCRIPT_SCHEMA_ID: (
        V075_K7_PROTOCOL_OBLIGATION_TRANSCRIPT_V2_DOMAIN
    ),
    PROTOCOL_SITE_SCHEMA_ID: (
        V075_K7_LOADED_PROTOCOL_SITE_ATTESTATION_V2_DOMAIN
    ),
}
_COMPONENT_ID_FIELD = {
    CUTOFF_SCHEMA_ID: "operational_cutoff_attestation_id",
    HASH_TRANSCRIPT_SCHEMA_ID: "hash_event_transcript_id",
    HASH_PURPOSE_REGISTRY_SCHEMA_ID: "hash_purpose_registry_id",
    HASH_SITE_SCHEMA_ID: "loaded_hash_site_attestation_id",
    INTEGRITY_REGISTRY_SCHEMA_ID: "integrity_obligation_registry_id",
    INTEGRITY_TRANSCRIPT_SCHEMA_ID: "integrity_obligation_transcript_id",
    INTEGRITY_SITE_SCHEMA_ID: "loaded_integrity_site_attestation_id",
    PROTOCOL_REGISTRY_SCHEMA_ID: "protocol_obligation_registry_id",
    PROTOCOL_TRANSCRIPT_SCHEMA_ID: "protocol_obligation_transcript_id",
    PROTOCOL_SITE_SCHEMA_ID: "loaded_protocol_site_attestation_id",
}

REQUESTED_PHASE3E_DOMAIN_TAGS = tuple(
    sorted(
        {
        COMMON_SESSION_V2_DOMAIN,
        COMMON_SOURCE_SITE_V2_DOMAIN,
        HASH_PURPOSE_V2_DOMAIN,
        NAMED_OBLIGATION_V2_DOMAIN,
        BROKER_OBSERVATION_BINDING_V2_DOMAIN,
        COMMON_EVENT_V2_DOMAIN,
            *_COMPONENT_DOMAIN.values(),
        }
    )
)
if not frozenset(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("common shared-resource journal domains are unregistered")

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_KEY = re.compile(r"^[a-z][a-z0-9_.:-]*$")
_MODULE = re.compile(r"^acfqp(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_SITE_ISSUER = object()
_PURPOSE_ISSUER = object()
_OBLIGATION_ISSUER = object()
_BUNDLE_ISSUER = object()
_REPLAY_ISSUER = object()


class ConstructionSharedResourceCommonJournalV2Error(ValueError):
    """The common-work recorder or raw evidence graph is invalid."""


class CommonJournalSessionStateV2(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class NamedObligationOutcomeV2(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


def _fail(message: str) -> NoReturn:
    raise ConstructionSharedResourceCommonJournalV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceCommonJournalV2Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        _fail(f"{label} must be one canonical identifier")
    return value


def _key(value: Any, label: str) -> str:
    if type(value) is not str or _KEY.fullmatch(value) is None:
        _fail(f"{label} must be one canonical registry key")
    return value


def _source_symbol(module: Any, symbol: Any) -> tuple[str, str]:
    if (
        type(module) is not str
        or _MODULE.fullmatch(module) is None
        or type(symbol) is not str
        or _SYMBOL.fullmatch(symbol) is None
    ):
        _fail("source module/symbol is noncanonical")
    return module, symbol


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


def _ids(values: Any, label: str, *, nonempty: bool) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or (nonempty and not values)
        or tuple(sorted(values)) != values
        or len(set(values)) != len(values)
    ):
        _fail(f"{label} must be a sorted unique tuple")
    for value in values:
        _cid(value, label)
    return values


def _enum(enum_type: type[Enum], value: Any, label: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceCommonJournalV2Error(
            f"{label} is unknown"
        ) from error


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("common raw evidence used an undeclared domain")
    return content_id(domain, dict(payload))


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceCommonJournalV2Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must be one canonical JSON object")
    return value


def _exact_fields(document: Any, fields: set[str], label: str) -> None:
    try:
        require_exact_fields(document, fields, context=label)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceCommonJournalV2Error(
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


_IDENTITY_FIELDS = {
    "live_envelope_id",
    "occurrence_id",
    "route_attempt_id",
    "decision_point_id",
    "measurement_window_id",
}
_COMMON_COMPONENT_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "raw_evidence_only",
    "semantic_source_verified",
    "counter_record_issued",
    "formal_value_authorized",
}


def _component_payload(
    schema_id: str, body: Mapping[str, Any]
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
    schema_id: str, body: Mapping[str, Any]
) -> tuple[str, bytes]:
    payload = _component_payload(schema_id, body)
    artifact_id = _hash(_COMPONENT_DOMAIN[schema_id], payload)
    return artifact_id, canonical_json_bytes(
        {**payload, _COMPONENT_ID_FIELD[schema_id]: artifact_id}
    )


def _replay_component(raw: bytes, schema_id: str) -> dict[str, Any]:
    document = _canonical_object(raw, schema_id)
    if document.get("schema") != schema_id:
        _fail("common component crossed its catalogue schema")
    id_field = _COMPONENT_ID_FIELD[schema_id]
    artifact_id = _cid(document.get(id_field), id_field)
    payload = {key: value for key, value in document.items() if key != id_field}
    if _hash(_COMPONENT_DOMAIN[schema_id], payload) != artifact_id:
        _fail("common component content ID does not replay")
    if (
        payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("profile_key") != PROFILE_KEY
        or payload.get("raw_evidence_only") is not True
        or payload.get("semantic_source_verified") is not False
        or payload.get("counter_record_issued") is not False
        or payload.get("formal_value_authorized") is not False
    ):
        _fail("common raw component attempted to claim formal authority")
    return document


@dataclass(frozen=True, slots=True)
class CommonSourceSiteRegistrationV2:
    _issuer: InitVar[object]
    path: str
    site_key: str
    source_module: str
    source_symbol: str
    source_archive_id: str
    source_sha256: str
    source_byte_count: int
    site_registration_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SITE_ISSUER:
            _fail("common source-site registration is caller-minted")
        if self.path not in SUPPORTED_PATHS:
            _fail("source site path is unsupported")
        _key(self.site_key, "source site key")
        _source_symbol(self.source_module, self.source_symbol)
        _cid(self.source_archive_id, "source archive")
        _sha256(self.source_sha256, "loaded source digest")
        _positive(self.source_byte_count, "loaded source byte count")
        payload = {
            "schema": "acfqp.construction_shared_resource_common_source_site.v2",
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "site_key": self.site_key,
            "source_module": self.source_module,
            "source_symbol": self.source_symbol,
            "source_archive_id": self.source_archive_id,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
        }
        object.__setattr__(
            self,
            "site_registration_id",
            _hash(COMMON_SOURCE_SITE_V2_DOMAIN, payload),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "site_key": self.site_key,
            "source_module": self.source_module,
            "source_symbol": self.source_symbol,
            "source_archive_id": self.source_archive_id,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "site_registration_id": self.site_registration_id,
        }


def freeze_common_source_site_v2(
    *,
    path: str,
    site_key: str,
    source_module: str,
    source_symbol: str,
    source_archive_id: str,
    source_sha256: str,
    source_byte_count: int,
) -> CommonSourceSiteRegistrationV2:
    return CommonSourceSiteRegistrationV2(
        _SITE_ISSUER,
        path,
        site_key,
        source_module,
        source_symbol,
        source_archive_id,
        source_sha256,
        source_byte_count,
    )


@dataclass(frozen=True, slots=True)
class HashPurposeRegistrationV2:
    _issuer: InitVar[object]
    purpose_key: str
    allowed_site_keys: tuple[str, ...]
    purpose_registration_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PURPOSE_ISSUER:
            _fail("hash purpose registration is caller-minted")
        _key(self.purpose_key, "hash purpose key")
        if (
            type(self.allowed_site_keys) is not tuple
            or not self.allowed_site_keys
            or tuple(sorted(self.allowed_site_keys))
            != self.allowed_site_keys
            or len(set(self.allowed_site_keys)) != len(self.allowed_site_keys)
        ):
            _fail("hash purpose site keys must be sorted, nonempty, and unique")
        for value in self.allowed_site_keys:
            _key(value, "hash purpose site key")
        payload = {
            "schema": "acfqp.construction_shared_resource_hash_purpose.v2",
            "schema_version": SCHEMA_VERSION,
            "purpose_key": self.purpose_key,
            "allowed_site_keys": list(self.allowed_site_keys),
        }
        object.__setattr__(
            self,
            "purpose_registration_id",
            _hash(HASH_PURPOSE_V2_DOMAIN, payload),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "purpose_key": self.purpose_key,
            "allowed_site_keys": list(self.allowed_site_keys),
            "purpose_registration_id": self.purpose_registration_id,
        }


def freeze_hash_purpose_v2(
    *, purpose_key: str, allowed_site_keys: tuple[str, ...]
) -> HashPurposeRegistrationV2:
    return HashPurposeRegistrationV2(
        _PURPOSE_ISSUER, purpose_key, allowed_site_keys
    )


@dataclass(frozen=True, slots=True)
class NamedObligationRegistrationV2:
    _issuer: InitVar[object]
    path: str
    obligation_key: str
    site_key: str
    predicate_owner_module: str
    predicate_owner_symbol: str
    obligation_registration_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _OBLIGATION_ISSUER:
            _fail("named obligation registration is caller-minted")
        if self.path not in {INTEGRITY_PATH, PROTOCOL_PATH}:
            _fail("named obligation path is not integrity or protocol")
        _key(self.obligation_key, "obligation key")
        _key(self.site_key, "obligation site key")
        _source_symbol(
            self.predicate_owner_module, self.predicate_owner_symbol
        )
        payload = {
            "schema": "acfqp.construction_shared_resource_named_obligation.v2",
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "obligation_key": self.obligation_key,
            "site_key": self.site_key,
            "predicate_owner_module": self.predicate_owner_module,
            "predicate_owner_symbol": self.predicate_owner_symbol,
        }
        object.__setattr__(
            self,
            "obligation_registration_id",
            _hash(NAMED_OBLIGATION_V2_DOMAIN, payload),
        )

    def to_document(self) -> dict[str, str]:
        return {
            "path": self.path,
            "obligation_key": self.obligation_key,
            "site_key": self.site_key,
            "predicate_owner_module": self.predicate_owner_module,
            "predicate_owner_symbol": self.predicate_owner_symbol,
            "obligation_registration_id": self.obligation_registration_id,
        }


def freeze_named_obligation_v2(
    *,
    path: str,
    obligation_key: str,
    site_key: str,
    predicate_owner_module: str,
    predicate_owner_symbol: str,
) -> NamedObligationRegistrationV2:
    return NamedObligationRegistrationV2(
        _OBLIGATION_ISSUER,
        path,
        obligation_key,
        site_key,
        predicate_owner_module,
        predicate_owner_symbol,
    )


@dataclass(frozen=True, slots=True)
class CommonRawReplayV2:
    _issuer: InitVar[object]
    live_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    hash_invocation_count: int
    integrity_check_count: int
    protocol_check_count: int
    global_event_count: int
    semantic_source_verified: bool = False
    counter_record_issuance_authorized: bool = False

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPLAY_ISSUER:
            _fail("common raw replay is caller-minted")
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
            (self.hash_invocation_count, "hash count"),
            (self.integrity_check_count, "integrity count"),
            (self.protocol_check_count, "protocol count"),
            (self.global_event_count, "global event count"),
        ):
            _nonnegative(value, label)
        if (
            self.semantic_source_verified is not False
            or self.counter_record_issuance_authorized is not False
        ):
            _fail("common raw replay cannot claim formal authority")


@dataclass(frozen=True, slots=True)
class CommonRawEvidenceBundleV2:
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
    hash_transcript_component: resolution_v2.SharedResourceEvidenceComponentV2
    hash_purpose_registry_component: (
        resolution_v2.SharedResourceEvidenceComponentV2
    )
    hash_site_component: resolution_v2.SharedResourceEvidenceComponentV2
    integrity_registry_component: (
        resolution_v2.SharedResourceEvidenceComponentV2
    )
    integrity_transcript_component: (
        resolution_v2.SharedResourceEvidenceComponentV2
    )
    integrity_site_component: resolution_v2.SharedResourceEvidenceComponentV2
    protocol_registry_component: (
        resolution_v2.SharedResourceEvidenceComponentV2
    )
    protocol_transcript_component: (
        resolution_v2.SharedResourceEvidenceComponentV2
    )
    protocol_site_component: resolution_v2.SharedResourceEvidenceComponentV2
    raw_replay: CommonRawReplayV2

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BUNDLE_ISSUER:
            _fail("common raw evidence bundle is caller-minted")
        for value, label in (
            (self.live_envelope_id, "bundle envelope"),
            (self.occurrence_id, "bundle occurrence"),
            (self.route_attempt_id, "bundle attempt"),
            (self.decision_point_id, "bundle decision"),
            (self.measurement_window_id, "bundle window"),
            (self.operational_cutoff_id, "bundle cutoff"),
            (self.session_binding_id, "bundle session"),
        ):
            _cid(value, label)
        components = (
            self.cutoff_component,
            self.hash_transcript_component,
            self.hash_purpose_registry_component,
            self.hash_site_component,
            self.integrity_registry_component,
            self.integrity_transcript_component,
            self.integrity_site_component,
            self.protocol_registry_component,
            self.protocol_transcript_component,
            self.protocol_site_component,
        )
        if any(
            type(item) is not resolution_v2.SharedResourceEvidenceComponentV2
            for item in components
        ) or type(self.raw_replay) is not CommonRawReplayV2:
            _fail("common raw bundle contains a mistyped component")
        _nonnegative(self.measurement_start_sequence, "bundle start sequence")
        _nonnegative(self.operational_cutoff_sequence, "bundle cutoff sequence")
        if self.operational_cutoff_sequence < self.measurement_start_sequence:
            _fail("common raw bundle cutoff precedes its start")
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
            _fail("common raw bundle crossed its replay identity")

    def components_for_path(
        self, path: str
    ) -> tuple[resolution_v2.SharedResourceEvidenceComponentV2, ...]:
        if path == HASH_PATH:
            result = (
                self.cutoff_component,
                self.hash_transcript_component,
                self.hash_purpose_registry_component,
                self.hash_site_component,
            )
        elif path == INTEGRITY_PATH:
            result = (
                self.cutoff_component,
                self.integrity_registry_component,
                self.integrity_transcript_component,
                self.integrity_site_component,
            )
        elif path == PROTOCOL_PATH:
            result = (
                self.cutoff_component,
                self.protocol_registry_component,
                self.protocol_transcript_component,
                self.protocol_site_component,
            )
        else:
            _fail("common bundle requested an unsupported path")
        return tuple(sorted(result, key=lambda item: item.component_key))

    def live_sources_v2(
        self,
    ) -> tuple[resolution_v2.SharedResourceLiveSourceV2, ...]:
        catalogue = {
            row.path: row
            for row in resolution_v2.official_shared_resource_resolution_catalogue_v2()
        }
        result = []
        for path in SUPPORTED_PATHS:
            contract = catalogue[path]
            result.append(
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
        return tuple(result)


class CommonJournalSessionV2:
    """Append-only raw recorder with all registries frozen at construction."""

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
        source_sites: tuple[CommonSourceSiteRegistrationV2, ...],
        hash_purposes: tuple[HashPurposeRegistrationV2, ...],
        integrity_obligations: tuple[NamedObligationRegistrationV2, ...],
        protocol_obligations: tuple[NamedObligationRegistrationV2, ...],
    ) -> None:
        for value, label in (
            (live_envelope_id, "session envelope"),
            (occurrence_id, "session occurrence"),
            (route_attempt_id, "session attempt"),
            (decision_point_id, "session decision"),
            (measurement_window_id, "session window"),
            (operational_cutoff_id, "session cutoff"),
        ):
            _cid(value, label)
        _nonnegative(measurement_start_sequence, "session start sequence")
        if (
            type(source_sites) is not tuple
            or any(type(item) is not CommonSourceSiteRegistrationV2 for item in source_sites)
            or tuple(sorted(source_sites, key=lambda row: (row.path, row.site_key)))
            != source_sites
            or len({(row.path, row.site_key) for row in source_sites})
            != len(source_sites)
        ):
            _fail("source-site registry must be sorted and unique")
        if {row.path for row in source_sites} != set(SUPPORTED_PATHS):
            _fail("source-site registry must cover exactly all common paths")
        if (
            type(hash_purposes) is not tuple
            or not hash_purposes
            or any(type(item) is not HashPurposeRegistrationV2 for item in hash_purposes)
            or tuple(sorted(hash_purposes, key=lambda row: row.purpose_key))
            != hash_purposes
            or len({row.purpose_key for row in hash_purposes}) != len(hash_purposes)
        ):
            _fail("hash-purpose registry must be sorted, nonempty, and unique")
        for obligations, path, label in (
            (integrity_obligations, INTEGRITY_PATH, "integrity"),
            (protocol_obligations, PROTOCOL_PATH, "protocol"),
        ):
            if (
                type(obligations) is not tuple
                or not obligations
                or any(type(item) is not NamedObligationRegistrationV2 for item in obligations)
                or tuple(sorted(obligations, key=lambda row: row.obligation_key))
                != obligations
                or len({row.obligation_key for row in obligations}) != len(obligations)
                or any(row.path != path for row in obligations)
            ):
                _fail(f"{label} obligation registry is malformed")
        sites = {(row.path, row.site_key): row for row in source_sites}
        hash_site_keys = {key for path, key in sites if path == HASH_PATH}
        if any(
            not set(purpose.allowed_site_keys) <= hash_site_keys
            for purpose in hash_purposes
        ):
            _fail("hash purpose references an unregistered source site")
        for obligations in (integrity_obligations, protocol_obligations):
            if any((row.path, row.site_key) not in sites for row in obligations):
                _fail("named obligation references an unregistered source site")
        identity = _identity_document(
            live_envelope_id=live_envelope_id,
            occurrence_id=occurrence_id,
            route_attempt_id=route_attempt_id,
            decision_point_id=decision_point_id,
            measurement_window_id=measurement_window_id,
        )
        binding = {
            "schema": "acfqp.construction_shared_resource_common_session.v2",
            "schema_version": SCHEMA_VERSION,
            **identity,
            "operational_cutoff_id": operational_cutoff_id,
            "measurement_start_sequence": measurement_start_sequence,
            "site_registration_ids": [row.site_registration_id for row in source_sites],
            "hash_purpose_registration_ids": [
                row.purpose_registration_id for row in hash_purposes
            ],
            "integrity_obligation_registration_ids": [
                row.obligation_registration_id for row in integrity_obligations
            ],
            "protocol_obligation_registration_ids": [
                row.obligation_registration_id for row in protocol_obligations
            ],
        }
        self._live_envelope_id = live_envelope_id
        self._occurrence_id = occurrence_id
        self._route_attempt_id = route_attempt_id
        self._decision_point_id = decision_point_id
        self._measurement_window_id = measurement_window_id
        self._operational_cutoff_id = operational_cutoff_id
        self._measurement_start_sequence = measurement_start_sequence
        self._session_binding_id = _hash(COMMON_SESSION_V2_DOMAIN, binding)
        self._source_sites = source_sites
        self._sites = sites
        self._hash_purposes = hash_purposes
        self._hash_purpose_by_key = {row.purpose_key: row for row in hash_purposes}
        self._obligations = {
            INTEGRITY_PATH: integrity_obligations,
            PROTOCOL_PATH: protocol_obligations,
        }
        self._obligation_by_key = {
            path: {row.obligation_key: row for row in rows}
            for path, rows in self._obligations.items()
        }
        self._events: dict[str, list[dict[str, Any]]] = {
            path: [] for path in SUPPORTED_PATHS
        }
        self._path_sequences = {path: 0 for path in SUPPORTED_PATHS}
        self._global_sequence = measurement_start_sequence
        self._global_index: list[dict[str, Any]] = []
        self._authenticated_observation_ids: set[str] = set()
        self._state = CommonJournalSessionStateV2.OPEN
        self._bundle: CommonRawEvidenceBundleV2 | None = None
        self._lock = threading.RLock()

    @property
    def state(self) -> CommonJournalSessionStateV2:
        return self._state

    def _require_open(self) -> None:
        if self._state is not CommonJournalSessionStateV2.OPEN:
            _fail("closed common journal cannot be appended")

    def _next(
        self, path: str, authenticated_broker_observation_id: str
    ) -> tuple[int, int, str]:
        observation_id = _cid(
            authenticated_broker_observation_id,
            "authenticated broker observation",
        )
        if observation_id in self._authenticated_observation_ids:
            _fail("authenticated broker observation ID is duplicated")
        self._authenticated_observation_ids.add(observation_id)
        self._global_sequence += 1
        self._path_sequences[path] += 1
        binding_id = _hash(
            BROKER_OBSERVATION_BINDING_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_broker_observation_binding.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": self._session_binding_id,
                "global_sequence": self._global_sequence,
                "path": path,
                "path_sequence": self._path_sequences[path],
                "authenticated_broker_observation_id": observation_id,
            },
        )
        return self._global_sequence, self._path_sequences[path], binding_id

    def _append(
        self,
        *,
        path: str,
        event_kind: str,
        registry_key: str,
        registration_id: str,
        site_key: str,
        authenticated_broker_observation_id: str,
        input_artifact_ids: tuple[str, ...],
        output_artifact_ids: tuple[str, ...],
        outcome: NamedObligationOutcomeV2 | None,
    ) -> str:
        self._require_open()
        inputs = _ids(input_artifact_ids, "event input IDs", nonempty=True)
        outputs = _ids(output_artifact_ids, "event output IDs", nonempty=True)
        global_sequence, path_sequence, observation_binding_id = self._next(
            path, authenticated_broker_observation_id
        )
        core: dict[str, Any] = {
            "global_sequence": global_sequence,
            "path_sequence": path_sequence,
            "event_kind": event_kind,
            "registry_key": registry_key,
            "registration_id": registration_id,
            "site_key": site_key,
            "site_registration_id": self._sites[(path, site_key)].site_registration_id,
            "authenticated_broker_observation_id": authenticated_broker_observation_id,
            "broker_observation_binding_id": observation_binding_id,
            "input_artifact_ids": list(inputs),
            "output_artifact_ids": list(outputs),
            "outcome": None if outcome is None else outcome.value,
        }
        event_id = _hash(
            COMMON_EVENT_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_common_event.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": self._session_binding_id,
                "path": path,
                **core,
            },
        )
        row = {**core, "event_id": event_id}
        self._events[path].append(row)
        self._global_index.append(
            {
                "global_sequence": global_sequence,
                "path": path,
                "path_sequence": path_sequence,
                "event_kind": event_kind,
                "event_id": event_id,
                "authenticated_broker_observation_id": (
                    authenticated_broker_observation_id
                ),
                "broker_observation_binding_id": observation_binding_id,
            }
        )
        return event_id

    def record_hash_invocation_v2(
        self,
        *,
        purpose_key: str,
        site_key: str,
        authenticated_broker_observation_id: str,
        input_artifact_ids: tuple[str, ...],
        output_artifact_ids: tuple[str, ...],
    ) -> str:
        with self._lock:
            purpose = self._hash_purpose_by_key.get(purpose_key)
            if purpose is None:
                _fail("hash event used an unregistered purpose")
            if site_key not in purpose.allowed_site_keys or (
                HASH_PATH,
                site_key,
            ) not in self._sites:
                _fail("hash event used an unregistered source site")
            return self._append(
                path=HASH_PATH,
                event_kind="HASH_INVOCATION",
                registry_key=purpose_key,
                registration_id=purpose.purpose_registration_id,
                site_key=site_key,
                authenticated_broker_observation_id=(
                    authenticated_broker_observation_id
                ),
                input_artifact_ids=input_artifact_ids,
                output_artifact_ids=output_artifact_ids,
                outcome=None,
            )

    def _record_obligation(
        self,
        *,
        path: str,
        obligation_key: str,
        site_key: str,
        outcome: NamedObligationOutcomeV2,
        authenticated_broker_observation_id: str,
        input_artifact_ids: tuple[str, ...],
        output_artifact_ids: tuple[str, ...],
    ) -> str:
        obligation = self._obligation_by_key[path].get(obligation_key)
        if obligation is None:
            _fail("named check used an unregistered obligation")
        if site_key != obligation.site_key or (path, site_key) not in self._sites:
            _fail("named check used an unregistered source site")
        checked_outcome = _enum(
            NamedObligationOutcomeV2, outcome, "named obligation outcome"
        )
        return self._append(
            path=path,
            event_kind=(
                "INTEGRITY_CHECK" if path == INTEGRITY_PATH else "PROTOCOL_CHECK"
            ),
            registry_key=obligation_key,
            registration_id=obligation.obligation_registration_id,
            site_key=site_key,
            authenticated_broker_observation_id=authenticated_broker_observation_id,
            input_artifact_ids=input_artifact_ids,
            output_artifact_ids=output_artifact_ids,
            outcome=checked_outcome,
        )

    def record_integrity_check_v2(
        self,
        *,
        obligation_key: str,
        site_key: str,
        outcome: NamedObligationOutcomeV2,
        authenticated_broker_observation_id: str,
        input_artifact_ids: tuple[str, ...],
        output_artifact_ids: tuple[str, ...],
    ) -> str:
        with self._lock:
            self._require_open()
            return self._record_obligation(
                path=INTEGRITY_PATH,
                obligation_key=obligation_key,
                site_key=site_key,
                outcome=outcome,
                authenticated_broker_observation_id=(
                    authenticated_broker_observation_id
                ),
                input_artifact_ids=input_artifact_ids,
                output_artifact_ids=output_artifact_ids,
            )

    def record_protocol_check_v2(
        self,
        *,
        obligation_key: str,
        site_key: str,
        outcome: NamedObligationOutcomeV2,
        authenticated_broker_observation_id: str,
        input_artifact_ids: tuple[str, ...],
        output_artifact_ids: tuple[str, ...],
    ) -> str:
        with self._lock:
            self._require_open()
            return self._record_obligation(
                path=PROTOCOL_PATH,
                obligation_key=obligation_key,
                site_key=site_key,
                outcome=outcome,
                authenticated_broker_observation_id=(
                    authenticated_broker_observation_id
                ),
                input_artifact_ids=input_artifact_ids,
                output_artifact_ids=output_artifact_ids,
            )

    def _identity(self) -> dict[str, str]:
        return _identity_document(
            live_envelope_id=self._live_envelope_id,
            occurrence_id=self._occurrence_id,
            route_attempt_id=self._route_attempt_id,
            decision_point_id=self._decision_point_id,
            measurement_window_id=self._measurement_window_id,
        )

    def _coverage_rows(
        self, path: str, key_name: str, registrations: tuple[Any, ...]
    ) -> list[dict[str, Any]]:
        result = []
        for registration in registrations:
            key = getattr(registration, key_name)
            result.append(
                {
                    "registry_key": key,
                    "covered_event_ids": [
                        row["event_id"]
                        for row in self._events[path]
                        if row["registry_key"] == key
                    ],
                }
            )
        return result

    def _site_body(self, path: str) -> dict[str, Any]:
        sites = tuple(row for row in self._source_sites if row.path == path)
        return {
            **self._identity(),
            "operational_cutoff_id": self._operational_cutoff_id,
            "session_binding_id": self._session_binding_id,
            "path": path,
            "loaded_source_sites": [row.to_document() for row in sites],
            "site_event_coverage": [
                {
                    "site_key": site.site_key,
                    "covered_event_ids": [
                        row["event_id"]
                        for row in self._events[path]
                        if row["site_key"] == site.site_key
                    ],
                }
                for site in sites
            ],
            "source_sites_frozen_before_start": True,
        }

    def _transcript_body(self, path: str) -> dict[str, Any]:
        return {
            **self._identity(),
            "operational_cutoff_id": self._operational_cutoff_id,
            "session_binding_id": self._session_binding_id,
            "path": path,
            "measurement_start_sequence": self._measurement_start_sequence,
            "operational_cutoff_sequence": self._global_sequence,
            "path_event_count": len(self._events[path]),
            "events": [dict(row) for row in self._events[path]],
            "raw_derived_event_count": len(self._events[path]),
            "caller_supplied_total_accepted": False,
        }

    def _hash_registry_body(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "operational_cutoff_id": self._operational_cutoff_id,
            "session_binding_id": self._session_binding_id,
            "path": HASH_PATH,
            "purpose_registrations": [row.to_document() for row in self._hash_purposes],
            "purpose_event_coverage": self._coverage_rows(
                HASH_PATH, "purpose_key", self._hash_purposes
            ),
            "registry_frozen_before_start": True,
        }

    def _obligation_registry_body(self, path: str) -> dict[str, Any]:
        rows = self._obligations[path]
        return {
            **self._identity(),
            "operational_cutoff_id": self._operational_cutoff_id,
            "session_binding_id": self._session_binding_id,
            "path": path,
            "obligation_registrations": [row.to_document() for row in rows],
            "obligation_event_coverage": self._coverage_rows(
                path, "obligation_key", rows
            ),
            "registry_frozen_before_start": True,
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
            "authenticated_broker_observation_ids": [
                row["authenticated_broker_observation_id"]
                for row in self._global_index
            ],
            "window_closed": True,
            "cutoff_is_inclusive": True,
        }

    @staticmethod
    def _component(
        schema_id: str, component_key: str, body: Mapping[str, Any]
    ) -> resolution_v2.SharedResourceEvidenceComponentV2:
        artifact_id, raw = _freeze_component_bytes(schema_id, body)
        return resolution_v2.SharedResourceEvidenceComponentV2(
            component_key,
            schema_id,
            artifact_id,
            hashlib.sha256(raw).hexdigest(),
            raw,
        )

    def close_v2(self) -> CommonRawEvidenceBundleV2:
        with self._lock:
            if self._state is CommonJournalSessionStateV2.CLOSED:
                assert self._bundle is not None
                return self._bundle
            cutoff = self._component(
                CUTOFF_SCHEMA_ID, "cutoff_attestation", self._cutoff_body()
            )
            hash_transcript = self._component(
                HASH_TRANSCRIPT_SCHEMA_ID,
                "hash_event_transcript",
                self._transcript_body(HASH_PATH),
            )
            hash_registry = self._component(
                HASH_PURPOSE_REGISTRY_SCHEMA_ID,
                "hash_purpose_registry",
                self._hash_registry_body(),
            )
            hash_sites = self._component(
                HASH_SITE_SCHEMA_ID,
                "loaded_source_site_attestation",
                self._site_body(HASH_PATH),
            )
            integrity_registry = self._component(
                INTEGRITY_REGISTRY_SCHEMA_ID,
                "integrity_obligation_registry",
                self._obligation_registry_body(INTEGRITY_PATH),
            )
            integrity_transcript = self._component(
                INTEGRITY_TRANSCRIPT_SCHEMA_ID,
                "integrity_obligation_transcript",
                self._transcript_body(INTEGRITY_PATH),
            )
            integrity_sites = self._component(
                INTEGRITY_SITE_SCHEMA_ID,
                "loaded_source_site_attestation",
                self._site_body(INTEGRITY_PATH),
            )
            protocol_registry = self._component(
                PROTOCOL_REGISTRY_SCHEMA_ID,
                "protocol_obligation_registry",
                self._obligation_registry_body(PROTOCOL_PATH),
            )
            protocol_transcript = self._component(
                PROTOCOL_TRANSCRIPT_SCHEMA_ID,
                "protocol_obligation_transcript",
                self._transcript_body(PROTOCOL_PATH),
            )
            protocol_sites = self._component(
                PROTOCOL_SITE_SCHEMA_ID,
                "loaded_source_site_attestation",
                self._site_body(PROTOCOL_PATH),
            )
            replay = replay_common_raw_evidence_v2(
                cutoff_bytes=cutoff.raw_bytes,
                hash_transcript_bytes=hash_transcript.raw_bytes,
                hash_purpose_registry_bytes=hash_registry.raw_bytes,
                hash_site_attestation_bytes=hash_sites.raw_bytes,
                integrity_registry_bytes=integrity_registry.raw_bytes,
                integrity_transcript_bytes=integrity_transcript.raw_bytes,
                integrity_site_attestation_bytes=integrity_sites.raw_bytes,
                protocol_registry_bytes=protocol_registry.raw_bytes,
                protocol_transcript_bytes=protocol_transcript.raw_bytes,
                protocol_site_attestation_bytes=protocol_sites.raw_bytes,
            )
            bundle = CommonRawEvidenceBundleV2(
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
                hash_transcript,
                hash_registry,
                hash_sites,
                integrity_registry,
                integrity_transcript,
                integrity_sites,
                protocol_registry,
                protocol_transcript,
                protocol_sites,
                replay,
            )
            self._bundle = bundle
            self._state = CommonJournalSessionStateV2.CLOSED
            return bundle


def _identity_tuple(document: Mapping[str, Any]) -> tuple[str, ...]:
    result = tuple(_cid(document.get(key), key) for key in sorted(_IDENTITY_FIELDS))
    return result + (
        _cid(document.get("operational_cutoff_id"), "cutoff"),
        _cid(document.get("session_binding_id"), "session binding"),
    )


def _replay_site(row: Any, path: str) -> dict[str, Any]:
    fields = {
        "path",
        "site_key",
        "source_module",
        "source_symbol",
        "source_archive_id",
        "source_sha256",
        "source_byte_count",
        "site_registration_id",
    }
    _exact_fields(row, fields, "source-site registration")
    if row["path"] != path:
        _fail("source-site registration crossed its path")
    _key(row["site_key"], "source-site key")
    _source_symbol(row["source_module"], row["source_symbol"])
    _cid(row["source_archive_id"], "source archive")
    _sha256(row["source_sha256"], "source digest")
    _positive(row["source_byte_count"], "source bytes")
    expected = _hash(
        COMMON_SOURCE_SITE_V2_DOMAIN,
        {
            "schema": "acfqp.construction_shared_resource_common_source_site.v2",
            "schema_version": SCHEMA_VERSION,
            "path": path,
            "site_key": row["site_key"],
            "source_module": row["source_module"],
            "source_symbol": row["source_symbol"],
            "source_archive_id": row["source_archive_id"],
            "source_sha256": row["source_sha256"],
            "source_byte_count": row["source_byte_count"],
        },
    )
    if row["site_registration_id"] != expected:
        _fail("source-site registration ID does not replay")
    return dict(row)


def _replay_hash_purpose(row: Any) -> dict[str, Any]:
    fields = {"purpose_key", "allowed_site_keys", "purpose_registration_id"}
    _exact_fields(row, fields, "hash-purpose registration")
    _key(row["purpose_key"], "hash-purpose key")
    sites = row["allowed_site_keys"]
    if (
        type(sites) is not list
        or not sites
        or sorted(sites) != sites
        or len(set(sites)) != len(sites)
    ):
        _fail("hash-purpose site keys are not exact")
    for value in sites:
        _key(value, "hash-purpose site key")
    expected = _hash(
        HASH_PURPOSE_V2_DOMAIN,
        {
            "schema": "acfqp.construction_shared_resource_hash_purpose.v2",
            "schema_version": SCHEMA_VERSION,
            "purpose_key": row["purpose_key"],
            "allowed_site_keys": sites,
        },
    )
    if row["purpose_registration_id"] != expected:
        _fail("hash-purpose registration ID does not replay")
    return dict(row)


def _replay_obligation(row: Any, path: str) -> dict[str, Any]:
    fields = {
        "path",
        "obligation_key",
        "site_key",
        "predicate_owner_module",
        "predicate_owner_symbol",
        "obligation_registration_id",
    }
    _exact_fields(row, fields, "named-obligation registration")
    if row["path"] != path:
        _fail("named obligation crossed its path")
    _key(row["obligation_key"], "obligation key")
    _key(row["site_key"], "obligation site key")
    _source_symbol(row["predicate_owner_module"], row["predicate_owner_symbol"])
    expected = _hash(
        NAMED_OBLIGATION_V2_DOMAIN,
        {
            "schema": "acfqp.construction_shared_resource_named_obligation.v2",
            "schema_version": SCHEMA_VERSION,
            "path": path,
            "obligation_key": row["obligation_key"],
            "site_key": row["site_key"],
            "predicate_owner_module": row["predicate_owner_module"],
            "predicate_owner_symbol": row["predicate_owner_symbol"],
        },
    )
    if row["obligation_registration_id"] != expected:
        _fail("named-obligation registration ID does not replay")
    return dict(row)


def _coverage_map(rows: Any, key_label: str) -> dict[str, list[str]]:
    if type(rows) is not list:
        _fail("registry coverage is not an array")
    result: dict[str, list[str]] = {}
    for row in rows:
        fields = {key_label, "covered_event_ids"}
        _exact_fields(row, fields, "registry coverage row")
        key = _key(row[key_label], key_label)
        event_ids = row["covered_event_ids"]
        if type(event_ids) is not list or len(set(event_ids)) != len(event_ids):
            _fail("registry coverage repeats an event ID")
        for value in event_ids:
            _cid(value, "covered event")
        if key in result:
            _fail("registry coverage repeats a key")
        result[key] = list(event_ids)
    return result


def _replay_path(
    *,
    transcript: Mapping[str, Any],
    registry: Mapping[str, Any],
    sites: Mapping[str, Any],
    path: str,
) -> tuple[int, list[dict[str, Any]]]:
    transcript_id = _COMPONENT_ID_FIELD[transcript["schema"]]
    registry_id = _COMPONENT_ID_FIELD[registry["schema"]]
    site_id = _COMPONENT_ID_FIELD[sites["schema"]]
    transcript_fields = _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | {
        transcript_id,
        "operational_cutoff_id",
        "session_binding_id",
        "path",
        "measurement_start_sequence",
        "operational_cutoff_sequence",
        "path_event_count",
        "events",
        "raw_derived_event_count",
        "caller_supplied_total_accepted",
    }
    site_fields = _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | {
        site_id,
        "operational_cutoff_id",
        "session_binding_id",
        "path",
        "loaded_source_sites",
        "site_event_coverage",
        "source_sites_frozen_before_start",
    }
    if path == HASH_PATH:
        registry_fields = _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | {
            registry_id,
            "operational_cutoff_id",
            "session_binding_id",
            "path",
            "purpose_registrations",
            "purpose_event_coverage",
            "registry_frozen_before_start",
        }
    else:
        registry_fields = _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | {
            registry_id,
            "operational_cutoff_id",
            "session_binding_id",
            "path",
            "obligation_registrations",
            "obligation_event_coverage",
            "registry_frozen_before_start",
        }
    _exact_fields(transcript, transcript_fields, f"{path} transcript")
    _exact_fields(registry, registry_fields, f"{path} registry")
    _exact_fields(sites, site_fields, f"{path} source sites")
    if path == HASH_PATH:
        registration_rows = registry["purpose_registrations"]
        if type(registration_rows) is not list:
            _fail("hash-purpose registrations are not an array")
        registrations = [
            _replay_hash_purpose(row) for row in registration_rows
        ]
        registration_by_key = {
            row["purpose_key"]: row for row in registrations
        }
        coverage = _coverage_map(
            registry["purpose_event_coverage"], "registry_key"
        )
    else:
        registration_rows = registry["obligation_registrations"]
        if type(registration_rows) is not list:
            _fail("named-obligation registrations are not an array")
        registrations = [
            _replay_obligation(row, path) for row in registration_rows
        ]
        registration_by_key = {
            row["obligation_key"]: row for row in registrations
        }
        coverage = _coverage_map(
            registry["obligation_event_coverage"], "registry_key"
        )
    if (
        transcript["path"] != path
        or registry["path"] != path
        or sites["path"] != path
        or _identity_tuple(transcript) != _identity_tuple(registry)
        or _identity_tuple(transcript) != _identity_tuple(sites)
        or transcript["caller_supplied_total_accepted"] is not False
        or registry["registry_frozen_before_start"] is not True
        or sites["source_sites_frozen_before_start"] is not True
    ):
        _fail("common transcript/registry/site binding changed")
    if not registrations or len(registration_by_key) != len(registrations):
        _fail("common registry is empty or repeats a key")
    if set(coverage) != set(registration_by_key):
        _fail("common registry coverage omits or adds a registered key")
    site_rows = [_replay_site(row, path) for row in sites["loaded_source_sites"]]
    site_by_key = {row["site_key"]: row for row in site_rows}
    if not site_rows or len(site_by_key) != len(site_rows):
        _fail("loaded source-site registry is empty or duplicated")
    site_coverage = _coverage_map(sites["site_event_coverage"], "site_key")
    if set(site_coverage) != set(site_by_key):
        _fail("source-site coverage omits or adds a registered site")
    events = transcript["events"]
    if type(events) is not list:
        _fail("common transcript events are not an array")
    _nonnegative(transcript["path_event_count"], "path event count")
    if transcript["path_event_count"] != len(events):
        _fail("common path event count differs from transcript")
    expected_by_registry = {key: [] for key in registration_by_key}
    expected_by_site = {key: [] for key in site_by_key}
    event_ids: set[str] = set()
    observation_ids: set[str] = set()
    event_index: list[dict[str, Any]] = []
    for expected_sequence, raw_row in enumerate(events, start=1):
        fields = {
            "global_sequence",
            "path_sequence",
            "event_kind",
            "registry_key",
            "registration_id",
            "site_key",
            "site_registration_id",
            "authenticated_broker_observation_id",
            "broker_observation_binding_id",
            "input_artifact_ids",
            "output_artifact_ids",
            "outcome",
            "event_id",
        }
        _exact_fields(raw_row, fields, "common event")
        row = dict(raw_row)
        if row["path_sequence"] != expected_sequence:
            _fail("common transcript has a missing, duplicate, or reordered sequence")
        _positive(row["global_sequence"], "common global sequence")
        registration = registration_by_key.get(row["registry_key"])
        site = site_by_key.get(row["site_key"])
        if registration is None:
            _fail("common event used an unregistered purpose or obligation")
        if site is None:
            _fail("common event used an unregistered source site")
        if path == HASH_PATH:
            if (
                row["event_kind"] != "HASH_INVOCATION"
                or row["outcome"] is not None
                or row["site_key"] not in registration["allowed_site_keys"]
                or row["registration_id"]
                != registration["purpose_registration_id"]
            ):
                _fail("hash event crossed its purpose or site")
        else:
            expected_kind = (
                "INTEGRITY_CHECK" if path == INTEGRITY_PATH else "PROTOCOL_CHECK"
            )
            _enum(NamedObligationOutcomeV2, row["outcome"], "obligation outcome")
            if (
                row["event_kind"] != expected_kind
                or row["site_key"] != registration["site_key"]
                or row["registration_id"]
                != registration["obligation_registration_id"]
            ):
                _fail("named check crossed its obligation or site")
        if row["site_registration_id"] != site["site_registration_id"]:
            _fail("common event crossed its source-site registration")
        inputs = row["input_artifact_ids"]
        outputs = row["output_artifact_ids"]
        if type(inputs) is not list or type(outputs) is not list:
            _fail("common event inputs/outputs are not arrays")
        _ids(tuple(inputs), "event inputs", nonempty=True)
        _ids(tuple(outputs), "event outputs", nonempty=True)
        observation_id = _cid(
            row["authenticated_broker_observation_id"],
            "authenticated broker observation",
        )
        expected_binding = _hash(
            BROKER_OBSERVATION_BINDING_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_broker_observation_binding.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": transcript["session_binding_id"],
                "global_sequence": row["global_sequence"],
                "path": path,
                "path_sequence": row["path_sequence"],
                "authenticated_broker_observation_id": observation_id,
            },
        )
        if row["broker_observation_binding_id"] != expected_binding:
            _fail("broker observation binding does not replay")
        core = {key: row[key] for key in fields if key != "event_id"}
        expected_event_id = _hash(
            COMMON_EVENT_V2_DOMAIN,
            {
                "schema": "acfqp.construction_shared_resource_common_event.v2",
                "schema_version": SCHEMA_VERSION,
                "session_binding_id": transcript["session_binding_id"],
                "path": path,
                **core,
            },
        )
        if row["event_id"] != expected_event_id:
            _fail("common event ID does not replay")
        if row["event_id"] in event_ids or observation_id in observation_ids:
            _fail("common transcript repeats an event or broker observation ID")
        event_ids.add(row["event_id"])
        observation_ids.add(observation_id)
        expected_by_registry[row["registry_key"]].append(row["event_id"])
        expected_by_site[row["site_key"]].append(row["event_id"])
        event_index.append(
            {
                "global_sequence": row["global_sequence"],
                "path": path,
                "path_sequence": row["path_sequence"],
                "event_kind": row["event_kind"],
                "event_id": row["event_id"],
                "authenticated_broker_observation_id": observation_id,
                "broker_observation_binding_id": row[
                    "broker_observation_binding_id"
                ],
            }
        )
    if coverage != expected_by_registry:
        _fail("registry coverage has missing, extra, or duplicated events")
    if site_coverage != expected_by_site:
        _fail("source-site coverage has missing, extra, or duplicated events")
    if (
        transcript["raw_derived_event_count"] != len(events)
        or transcript["path_event_count"] != len(events)
    ):
        _fail("common raw event count is under-counted or double-counted")
    return len(events), event_index


def replay_common_raw_evidence_v2(
    *,
    cutoff_bytes: bytes,
    hash_transcript_bytes: bytes,
    hash_purpose_registry_bytes: bytes,
    hash_site_attestation_bytes: bytes,
    integrity_registry_bytes: bytes,
    integrity_transcript_bytes: bytes,
    integrity_site_attestation_bytes: bytes,
    protocol_registry_bytes: bytes,
    protocol_transcript_bytes: bytes,
    protocol_site_attestation_bytes: bytes,
) -> CommonRawReplayV2:
    cutoff = _replay_component(cutoff_bytes, CUTOFF_SCHEMA_ID)
    components = {
        "hash_transcript": _replay_component(
            hash_transcript_bytes, HASH_TRANSCRIPT_SCHEMA_ID
        ),
        "hash_registry": _replay_component(
            hash_purpose_registry_bytes, HASH_PURPOSE_REGISTRY_SCHEMA_ID
        ),
        "hash_sites": _replay_component(
            hash_site_attestation_bytes, HASH_SITE_SCHEMA_ID
        ),
        "integrity_registry": _replay_component(
            integrity_registry_bytes, INTEGRITY_REGISTRY_SCHEMA_ID
        ),
        "integrity_transcript": _replay_component(
            integrity_transcript_bytes, INTEGRITY_TRANSCRIPT_SCHEMA_ID
        ),
        "integrity_sites": _replay_component(
            integrity_site_attestation_bytes, INTEGRITY_SITE_SCHEMA_ID
        ),
        "protocol_registry": _replay_component(
            protocol_registry_bytes, PROTOCOL_REGISTRY_SCHEMA_ID
        ),
        "protocol_transcript": _replay_component(
            protocol_transcript_bytes, PROTOCOL_TRANSCRIPT_SCHEMA_ID
        ),
        "protocol_sites": _replay_component(
            protocol_site_attestation_bytes, PROTOCOL_SITE_SCHEMA_ID
        ),
    }
    cutoff_fields = _COMMON_COMPONENT_FIELDS | _IDENTITY_FIELDS | {
        "operational_cutoff_attestation_id",
        "operational_cutoff_id",
        "session_binding_id",
        "measurement_start_sequence",
        "operational_cutoff_sequence",
        "global_event_count",
        "global_event_index",
        "authenticated_broker_observation_ids",
        "window_closed",
        "cutoff_is_inclusive",
    }
    _exact_fields(cutoff, cutoff_fields, "common cutoff")
    if cutoff["window_closed"] is not True or cutoff["cutoff_is_inclusive"] is not True:
        _fail("common cutoff is not closed and inclusive")
    identity = _identity_tuple(cutoff)
    if any(_identity_tuple(value) != identity for value in components.values()):
        _fail("common raw component crossed occurrence/window identity")
    hash_count, hash_index = _replay_path(
        transcript=components["hash_transcript"],
        registry=components["hash_registry"],
        sites=components["hash_sites"],
        path=HASH_PATH,
    )
    integrity_count, integrity_index = _replay_path(
        transcript=components["integrity_transcript"],
        registry=components["integrity_registry"],
        sites=components["integrity_sites"],
        path=INTEGRITY_PATH,
    )
    protocol_count, protocol_index = _replay_path(
        transcript=components["protocol_transcript"],
        registry=components["protocol_registry"],
        sites=components["protocol_sites"],
        path=PROTOCOL_PATH,
    )
    index = sorted(
        hash_index + integrity_index + protocol_index,
        key=lambda row: row["global_sequence"],
    )
    start = _nonnegative(cutoff["measurement_start_sequence"], "cutoff start")
    end = _nonnegative(cutoff["operational_cutoff_sequence"], "cutoff end")
    count = _nonnegative(cutoff["global_event_count"], "cutoff event count")
    observations = [row["authenticated_broker_observation_id"] for row in index]
    if (
        count != len(index)
        or end != start + count
        or [row["global_sequence"] for row in index]
        != list(range(start + 1, end + 1))
        or cutoff["global_event_index"] != index
        or cutoff["authenticated_broker_observation_ids"] != observations
        or len(set(observations)) != len(observations)
    ):
        _fail("common cutoff hides, duplicates, or reorders an event")
    for key in ("hash_transcript", "integrity_transcript", "protocol_transcript"):
        transcript = components[key]
        if (
            transcript["measurement_start_sequence"] != start
            or transcript["operational_cutoff_sequence"] != end
        ):
            _fail("common path transcript crossed the inclusive cutoff")
    return CommonRawReplayV2(
        _REPLAY_ISSUER,
        cutoff["live_envelope_id"],
        cutoff["occurrence_id"],
        cutoff["route_attempt_id"],
        cutoff["decision_point_id"],
        cutoff["measurement_window_id"],
        cutoff["operational_cutoff_id"],
        hash_count,
        integrity_count,
        protocol_count,
        count,
        False,
        False,
    )


__all__ = [
    "CUTOFF_SCHEMA_ID",
    "CommonJournalSessionStateV2",
    "CommonJournalSessionV2",
    "CommonRawEvidenceBundleV2",
    "CommonRawReplayV2",
    "CommonSourceSiteRegistrationV2",
    "ConstructionSharedResourceCommonJournalV2Error",
    "HASH_PATH",
    "HASH_PURPOSE_REGISTRY_SCHEMA_ID",
    "HASH_SITE_SCHEMA_ID",
    "HASH_TRANSCRIPT_SCHEMA_ID",
    "HashPurposeRegistrationV2",
    "INTEGRITY_PATH",
    "INTEGRITY_REGISTRY_SCHEMA_ID",
    "INTEGRITY_SITE_SCHEMA_ID",
    "INTEGRITY_TRANSCRIPT_SCHEMA_ID",
    "NamedObligationOutcomeV2",
    "NamedObligationRegistrationV2",
    "PROFILE_KEY",
    "PROTOCOL_PATH",
    "PROTOCOL_REGISTRY_SCHEMA_ID",
    "PROTOCOL_SITE_SCHEMA_ID",
    "PROTOCOL_TRANSCRIPT_SCHEMA_ID",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "SUPPORTED_PATHS",
    "freeze_common_source_site_v2",
    "freeze_hash_purpose_v2",
    "freeze_named_obligation_v2",
    "replay_common_raw_evidence_v2",
]
