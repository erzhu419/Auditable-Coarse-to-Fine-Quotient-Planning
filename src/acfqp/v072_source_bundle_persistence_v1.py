"""Canonical persistence envelope for the V0-072 source evidence graph.

This revision persistently binds the complete in-memory object snapshots and
all six authoritative semantic documents.  The loader strictly replays JSON
bytes, role order, content identities, runtime types, and cross-role links.

It deliberately does *not* claim typed reconstruction of the old V0-068
campaign graph.  Those classes do not yet expose a complete parser family.
The fixed parser registry therefore records each missing typed parser and the
public typed-replay entry point fails closed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import stat
from types import SimpleNamespace
from typing import Any

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import observation_support_campaign_v1 as campaign_v1
from acfqp import verified_source_acquisition_archive_v2 as archive_v2
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as independent_v2,
)
from acfqp import v072_verified_source_archive_component_v1 as component_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_canonical_source_bundle_persistence_v1"
PERSISTENCE_STAGE = "DEVELOPMENT_ONLY_UNSCALABLE_OBJECT_SNAPSHOT"
TYPED_REPLAY_BLOCKER = (
    "FULL_TYPED_SOURCE_BUNDLE_DESERIALIZATION_AND_REPLAY_NOT_IMPLEMENTED"
)
MAX_DEVELOPMENT_SNAPSHOT_PHYSICAL_DRAWS = 200_000

ROLE_ORDER = (
    "SOURCE_CAMPAIGN",
    "SOURCE_CAMPAIGN_VERIFICATION",
    "DERIVED_SOURCE_ARCHIVE",
    "PRODUCTION_ARCHIVE_VERIFICATION",
    "INDEPENDENT_ARCHIVE_ATTESTATION",
    "VERIFIED_SOURCE_ARCHIVE_COMPONENT",
)

ENTRY_DOMAIN = "acfqp:v072-canonical-source-bundle-entry:v1"
BUNDLE_DOMAIN = "acfqp:v072-canonical-source-bundle-envelope:v1"
PARSER_DOMAIN = "acfqp:v072-source-bundle-parser-registration:v1"
PARSER_REGISTRY_DOMAIN = "acfqp:v072-source-bundle-parser-registry:v1"


class V072SourceBundlePersistenceInvariantViolation(ValueError):
    """The canonical source bundle is malformed, altered, or overstated."""


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
    except (TypeError, ValueError) as error:
        raise V072SourceBundlePersistenceInvariantViolation(str(error)) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + encoded
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072SourceBundlePersistenceInvariantViolation(
            f"{field_name} is not one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        raise V072SourceBundlePersistenceInvariantViolation(
            f"{field_name} is not canonical nonempty text"
        )
    return value


def _runtime_type(value_or_type: Any) -> str:
    cls = value_or_type if isinstance(value_or_type, type) else type(value_or_type)
    return f"{cls.__module__}.{cls.__qualname__}"


_ROLE_SPEC = {
    "SOURCE_CAMPAIGN": (
        campaign_v1.ObservationSupportCampaignV1,
        "acfqp.observation_support_campaign.v1",
        "campaign_id",
    ),
    "SOURCE_CAMPAIGN_VERIFICATION": (
        campaign_v1.ObservationSupportCampaignVerificationV1,
        "acfqp.observation_support_campaign_verification.v1",
        "verification_id",
    ),
    "DERIVED_SOURCE_ARCHIVE": (
        archive_v2.VerifiedSourceAcquisitionArchiveV2,
        "acfqp.verified_source_acquisition_archive.v2",
        "archive_id",
    ),
    "PRODUCTION_ARCHIVE_VERIFICATION": (
        archive_v2.VerifiedSourceAcquisitionArchiveVerificationV2,
        "acfqp.verified_source_acquisition_archive_verification.v2",
        "verification_id",
    ),
    "INDEPENDENT_ARCHIVE_ATTESTATION": (
        independent_v2.IndependentSourceAcquisitionArchiveVerificationV2,
        (
            "acfqp.independent_source_acquisition_archive_verification.v2"
        ),
        "verification_id",
    ),
    "VERIFIED_SOURCE_ARCHIVE_COMPONENT": (
        component_v1.V072VerifiedSourceArchiveComponentV1,
        "acfqp.v072_verified_source_archive_component.v1",
        "component_id",
    ),
}


@dataclass(frozen=True, slots=True)
class SourceBundleParserRegistrationV1:
    role: str
    authoritative_schema_id: str
    runtime_type: str
    parser_id: str
    typed_loader_available: bool = False
    unavailable_reason: str = TYPED_REPLAY_BLOCKER

    def __post_init__(self) -> None:
        if (
            self.role not in ROLE_ORDER
            or self.authoritative_schema_id != _ROLE_SPEC[self.role][1]
            or self.runtime_type != _runtime_type(_ROLE_SPEC[self.role][0])
            or self.typed_loader_available is not False
            or self.unavailable_reason != TYPED_REPLAY_BLOCKER
        ):
            raise V072SourceBundlePersistenceInvariantViolation(
                "source parser registration is malformed or overclaims"
            )
        _cid(self.parser_id, "source parser registration")
        if self.parser_id != _content_id(PARSER_DOMAIN, self._payload()):
            raise V072SourceBundlePersistenceInvariantViolation(
                "source parser registration ID differs from its payload"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_source_bundle_parser_registration.v1",
            "schema_version": SCHEMA_VERSION,
            "role": self.role,
            "authoritative_schema_id": self.authoritative_schema_id,
            "runtime_type": self.runtime_type,
            "typed_loader_available": False,
            "unavailable_reason": TYPED_REPLAY_BLOCKER,
        }

    @classmethod
    def frozen(cls, role: str) -> "SourceBundleParserRegistrationV1":
        expected_type, schema_id, _ = _ROLE_SPEC[role]
        payload = {
            "schema": "acfqp.v072_source_bundle_parser_registration.v1",
            "schema_version": SCHEMA_VERSION,
            "role": role,
            "authoritative_schema_id": schema_id,
            "runtime_type": _runtime_type(expected_type),
            "typed_loader_available": False,
            "unavailable_reason": TYPED_REPLAY_BLOCKER,
        }
        return cls(
            role,
            schema_id,
            _runtime_type(expected_type),
            _content_id(PARSER_DOMAIN, payload),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "parser_id": self.parser_id}


PARSER_REGISTRY = tuple(
    SourceBundleParserRegistrationV1.frozen(role) for role in ROLE_ORDER
)
PARSER_REGISTRY_ID = _content_id(
    PARSER_REGISTRY_DOMAIN,
    {
        "schema": "acfqp.v072_source_bundle_parser_registry.v1",
        "schema_version": SCHEMA_VERSION,
        "ordered_parser_ids": [item.parser_id for item in PARSER_REGISTRY],
        "typed_replay_ready": False,
        "typed_replay_blocker": TYPED_REPLAY_BLOCKER,
    },
)


def source_bundle_parser_registry_document_v1() -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_source_bundle_parser_registry.v1",
        "schema_version": SCHEMA_VERSION,
        "ordered_parser_ids": [item.parser_id for item in PARSER_REGISTRY],
        "registrations": [item.to_document() for item in PARSER_REGISTRY],
        "typed_replay_ready": False,
        "typed_replay_blocker": TYPED_REPLAY_BLOCKER,
        "parser_registry_id": PARSER_REGISTRY_ID,
    }


def _snapshot_sort_key(value: Any) -> bytes:
    return canonical_json_bytes(value)


def _complete_object_snapshot(
    value: Any,
    *,
    active: set[int] | None = None,
) -> Any:
    """Encode every initialized field without pickle or caller type metadata."""

    if active is None:
        active = set()
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise V072SourceBundlePersistenceInvariantViolation(
                "non-finite float is forbidden in a source snapshot"
            )
        return {
            "kind": "FINITE_FLOAT",
            "hex": value.hex(),
        }
    if type(value) is Fraction:
        return {
            "kind": "FRACTION",
            "value": {
                "numerator": value.numerator,
                "denominator": value.denominator,
            },
        }
    if isinstance(value, Enum):
        return {
            "kind": "ENUM",
            "runtime_type": _runtime_type(value),
            "name": value.name,
        }
    if type(value) is bytes:
        return {
            "kind": "BYTES",
            "hex": value.hex(),
        }

    marker = id(value)
    if marker in active:
        raise V072SourceBundlePersistenceInvariantViolation(
            "cyclic source object graphs are not persistable"
        )
    active.add(marker)
    try:
        if isinstance(value, Mapping):
            items = [
                {
                    "key": _complete_object_snapshot(key, active=active),
                    "value": _complete_object_snapshot(item, active=active),
                }
                for key, item in value.items()
            ]
            items.sort(key=_snapshot_sort_key)
            return {"kind": "MAPPING", "items": items}
        if type(value) in (tuple, list):
            return {
                "kind": "TUPLE" if type(value) is tuple else "LIST",
                "items": [
                    _complete_object_snapshot(item, active=active)
                    for item in value
                ],
            }
        if type(value) in (set, frozenset):
            items = [
                _complete_object_snapshot(item, active=active)
                for item in value
            ]
            items.sort(key=_snapshot_sort_key)
            return {
                "kind": "FROZENSET"
                if type(value) is frozenset
                else "SET",
                "items": items,
            }

        names: list[str] = []
        if is_dataclass(value):
            names.extend(item.name for item in fields(value))
        if isinstance(value, SimpleNamespace):
            names.extend(vars(value))
        for cls in type(value).__mro__:
            slots = getattr(cls, "__slots__", ())
            if type(slots) is str:
                slots = (slots,)
            names.extend(
                item
                for item in slots
                if item not in {"__dict__", "__weakref__"}
            )
        if hasattr(value, "__dict__"):
            names.extend(vars(value))
        ordered_names = tuple(sorted(set(names)))
        attributes = []
        missing = []
        for name in ordered_names:
            try:
                item = getattr(value, name)
            except AttributeError:
                missing.append(name)
                continue
            attributes.append(
                {
                    "name": name,
                    "value": _complete_object_snapshot(item, active=active),
                }
            )
        if not attributes and not missing:
            raise V072SourceBundlePersistenceInvariantViolation(
                f"unsupported source snapshot type: {_runtime_type(value)}"
            )
        return {
            "kind": "TYPED_OBJECT",
            "runtime_type": _runtime_type(value),
            "attributes": attributes,
            "uninitialized_declared_fields": missing,
        }
    finally:
        active.remove(marker)


def _semantic_document(value: Any) -> dict[str, Any]:
    method = getattr(value, "to_document", None)
    if not callable(method):
        raise V072SourceBundlePersistenceInvariantViolation(
            "source artifact lacks its authoritative document"
        )
    document = method()
    if type(document) is not dict:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source artifact document is not one plain object"
        )
    canonical_json_bytes(document)
    return document


@dataclass(frozen=True, slots=True)
class CanonicalSourceBundleEntryV1:
    role: str
    authoritative_schema_id: str
    runtime_type: str
    semantic_identity_field: str
    semantic_identity: str
    semantic_document: Mapping[str, Any]
    full_typed_snapshot: Any

    def __post_init__(self) -> None:
        if self.role not in ROLE_ORDER:
            raise V072SourceBundlePersistenceInvariantViolation(
                "source bundle entry role is unknown"
            )
        expected_type, expected_schema, expected_identity_field = _ROLE_SPEC[
            self.role
        ]
        if (
            self.authoritative_schema_id != expected_schema
            or self.runtime_type != _runtime_type(expected_type)
            or self.semantic_identity_field != expected_identity_field
            or type(self.semantic_document) is not dict
            or set(self.semantic_document).isdisjoint(
                {"schema", self.semantic_identity_field}
            )
            or self.semantic_document.get("schema") != expected_schema
            or self.semantic_document.get(self.semantic_identity_field)
            != self.semantic_identity
        ):
            raise V072SourceBundlePersistenceInvariantViolation(
                "source bundle entry schema, type, or identity changed"
            )
        _cid(self.semantic_identity, "source entry semantic identity")
        snapshot = self.full_typed_snapshot
        if (
            type(snapshot) is not dict
            or snapshot.get("kind") != "TYPED_OBJECT"
            or snapshot.get("runtime_type") != self.runtime_type
        ):
            raise V072SourceBundlePersistenceInvariantViolation(
                "source entry lacks its complete typed object snapshot"
            )
        canonical_json_bytes(dict(self.semantic_document))
        canonical_json_bytes(snapshot)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_canonical_source_bundle_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "role": self.role,
            "authoritative_schema_id": self.authoritative_schema_id,
            "runtime_type": self.runtime_type,
            "semantic_identity_field": self.semantic_identity_field,
            "semantic_identity": self.semantic_identity,
            "semantic_document": dict(self.semantic_document),
            "full_typed_snapshot": self.full_typed_snapshot,
            "parser_id": PARSER_REGISTRY[
                ROLE_ORDER.index(self.role)
            ].parser_id,
        }

    @property
    def entry_id(self) -> str:
        return _content_id(ENTRY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


def _entry(role: str, value: Any) -> CanonicalSourceBundleEntryV1:
    expected_type, schema_id, identity_field = _ROLE_SPEC[role]
    if type(value) is not expected_type:
        raise V072SourceBundlePersistenceInvariantViolation(
            f"{role} is not its exact registered runtime type"
        )
    document = _semantic_document(value)
    identity = getattr(value, identity_field)
    return CanonicalSourceBundleEntryV1(
        role,
        schema_id,
        _runtime_type(value),
        identity_field,
        identity,
        document,
        _complete_object_snapshot(value),
    )


@dataclass(frozen=True, slots=True)
class CanonicalSourceBundleEnvelopeV1:
    entries: tuple[CanonicalSourceBundleEntryV1, ...]
    source_campaign_id: str
    source_campaign_verification_id: str
    source_archive_id: str
    independent_attestation_id: str
    component_id: str
    parser_registry_id: str = PARSER_REGISTRY_ID
    typed_replay_ready: bool = False
    typed_replay_blocker: str = TYPED_REPLAY_BLOCKER

    def __post_init__(self) -> None:
        if (
            type(self.entries) is not tuple
            or tuple(item.role for item in self.entries) != ROLE_ORDER
            or any(
                type(item) is not CanonicalSourceBundleEntryV1
                for item in self.entries
            )
            or self.parser_registry_id != PARSER_REGISTRY_ID
            or self.typed_replay_ready is not False
            or self.typed_replay_blocker != TYPED_REPLAY_BLOCKER
        ):
            raise V072SourceBundlePersistenceInvariantViolation(
                "source bundle envelope is reordered, incomplete, or overclaims"
            )
        by_role = {item.role: item for item in self.entries}
        campaign_id = by_role["SOURCE_CAMPAIGN"].semantic_identity
        verification_id = by_role[
            "SOURCE_CAMPAIGN_VERIFICATION"
        ].semantic_identity
        archive_id = by_role["DERIVED_SOURCE_ARCHIVE"].semantic_identity
        independent_id = by_role[
            "INDEPENDENT_ARCHIVE_ATTESTATION"
        ].semantic_identity
        component_id = by_role[
            "VERIFIED_SOURCE_ARCHIVE_COMPONENT"
        ].semantic_identity
        for value, name in (
            (self.source_campaign_id, "source campaign"),
            (
                self.source_campaign_verification_id,
                "source campaign verification",
            ),
            (self.source_archive_id, "source archive"),
            (self.independent_attestation_id, "independent attestation"),
            (self.component_id, "source component"),
        ):
            _cid(value, name)
        archive_document = by_role[
            "DERIVED_SOURCE_ARCHIVE"
        ].semantic_document
        production_document = by_role[
            "PRODUCTION_ARCHIVE_VERIFICATION"
        ].semantic_document
        independent_document = by_role[
            "INDEPENDENT_ARCHIVE_ATTESTATION"
        ].semantic_document
        component_document = by_role[
            "VERIFIED_SOURCE_ARCHIVE_COMPONENT"
        ].semantic_document
        if (
            self.source_campaign_id != campaign_id
            or self.source_campaign_verification_id != verification_id
            or self.source_archive_id != archive_id
            or self.independent_attestation_id != independent_id
            or self.component_id != component_id
            or archive_document.get("source_campaign_id") != campaign_id
            or archive_document.get("source_campaign_verification_id")
            != verification_id
            or production_document.get("archive_id") != archive_id
            or production_document.get("replayed_archive_id") != archive_id
            or independent_document.get("archive_id") != archive_id
            or independent_document.get(
                "independently_recomputed_archive_id"
            )
            != archive_id
            or component_document.get("archive_id") != archive_id
            or component_document.get(
                "independent_archive_transform_attestation_id"
            )
            != independent_id
        ):
            raise V072SourceBundlePersistenceInvariantViolation(
                "source bundle cross-role identity graph does not close"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_canonical_source_bundle_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "persistence_stage": PERSISTENCE_STAGE,
            "ordered_roles": list(ROLE_ORDER),
            "ordered_entry_ids": [item.entry_id for item in self.entries],
            "source_campaign_id": self.source_campaign_id,
            "source_campaign_verification_id": (
                self.source_campaign_verification_id
            ),
            "source_archive_id": self.source_archive_id,
            "independent_attestation_id": self.independent_attestation_id,
            "component_id": self.component_id,
            "parser_registry_id": PARSER_REGISTRY_ID,
            "typed_replay_ready": False,
            "typed_replay_blocker": TYPED_REPLAY_BLOCKER,
            "real_source_snapshot_persistence_allowed": False,
            "official_source_persistence_claimed": False,
        }

    @property
    def bundle_id(self) -> str:
        return _content_id(BUNDLE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "entries": [item.to_document() for item in self.entries],
            "parser_registry": source_bundle_parser_registry_document_v1(),
            "bundle_id": self.bundle_id,
        }


def freeze_canonical_source_bundle_envelope_v1(
    *,
    source_campaign: campaign_v1.ObservationSupportCampaignV1,
    source_verification: campaign_v1.ObservationSupportCampaignVerificationV1,
) -> CanonicalSourceBundleEnvelopeV1:
    """Derive every downstream artifact; no caller IDs or artifacts enter."""

    if (
        type(source_campaign) is not campaign_v1.ObservationSupportCampaignV1
        or type(source_verification)
        is not campaign_v1.ObservationSupportCampaignVerificationV1
    ):
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle requires exact campaign and verification objects"
        )
    counters = getattr(source_campaign, "counters", None)
    physical_draws = getattr(
        counters,
        "physical_unique_observer_draws",
        None,
    )
    if (
        type(physical_draws) is int
        and physical_draws > MAX_DEVELOPMENT_SNAPSHOT_PHYSICAL_DRAWS
    ):
        raise V072SourceBundlePersistenceInvariantViolation(
            "full source object snapshot is statically undeployable; "
            "use the deterministic reconstruction recipe"
        )
    try:
        archive = archive_v2.freeze_verified_source_acquisition_archive_v2(
            source_campaign=source_campaign,
            source_verification=source_verification,
        )
        production = archive_v2.verify_verified_source_acquisition_archive_v2(
            source_campaign=source_campaign,
            source_verification=source_verification,
            claimed=archive,
        )
        independent = (
            independent_v2
            .verify_source_acquisition_archive_independently_v2(
                source_campaign=source_campaign,
                source_verification=source_verification,
                claimed=archive,
            )
        )
        component = component_v1.bind_v072_verified_source_archive_component_v1(
            archive=archive,
            production_verification=production,
            independent_attestation=independent,
        )
    except (
        archive_v2.VerifiedSourceAcquisitionArchiveInvariantViolation,
        independent_v2.IndependentSourceArchiveVerificationViolation,
        component_v1.V072VerifiedSourceArchiveComponentInvariantViolation,
    ) as error:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle derivation failed exact production/independent replay"
        ) from error
    entries = tuple(
        _entry(role, value)
        for role, value in zip(
            ROLE_ORDER,
            (
                source_campaign,
                source_verification,
                archive,
                production,
                independent,
                component,
            ),
            strict=True,
        )
    )
    return CanonicalSourceBundleEnvelopeV1(
        entries,
        source_campaign.campaign_id,
        source_verification.verification_id,
        archive.archive_id,
        independent.verification_id,
        component.component_id,
    )


def render_canonical_source_bundle_v1(
    envelope: CanonicalSourceBundleEnvelopeV1,
) -> bytes:
    if type(envelope) is not CanonicalSourceBundleEnvelopeV1:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle renderer requires the exact envelope type"
        )
    return canonical_json_bytes(envelope.to_document())


def _safe_output_path(path: str | os.PathLike[str]) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle output path must be absolute"
        )
    parent = candidate.parent.resolve(strict=True)
    if not parent.is_dir():
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle output parent is not a directory"
        )
    cursor = Path(candidate.anchor)
    for part in candidate.parts[1:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise V072SourceBundlePersistenceInvariantViolation(
                "source bundle output path contains a symlink"
            )
    if candidate.exists() or candidate.is_symlink():
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle writer never overwrites an existing path"
        )
    canonical_candidate = parent / candidate.name
    if canonical_candidate != candidate:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle output path is noncanonical"
        )
    return canonical_candidate


def write_canonical_source_bundle_v1(
    path: str | os.PathLike[str],
    *,
    source_campaign: campaign_v1.ObservationSupportCampaignV1,
    source_verification: campaign_v1.ObservationSupportCampaignVerificationV1,
) -> CanonicalSourceBundleEnvelopeV1:
    output = _safe_output_path(path)
    envelope = freeze_canonical_source_bundle_envelope_v1(
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    data = render_canonical_source_bundle_v1(envelope)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(output, flags, 0o600)
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return envelope


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise V072SourceBundlePersistenceInvariantViolation(
                f"duplicate source bundle JSON key: {key}"
            )
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise V072SourceBundlePersistenceInvariantViolation(
        f"non-finite source bundle JSON token: {value}"
    )


def _read_regular_file(path: Path) -> bytes:
    if path.is_symlink():
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle input is a symlink"
        )
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise V072SourceBundlePersistenceInvariantViolation(
                "source bundle input is not a regular file"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle input changed during read"
        )
    data = b"".join(chunks)
    if len(data) != after.st_size:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle input byte count changed"
        )
    return data


def _safe_input_path(path: str | os.PathLike[str]) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle input path must be absolute"
        )
    cursor = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise V072SourceBundlePersistenceInvariantViolation(
                "source bundle input path contains a symlink"
            )
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as error:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle input cannot be read"
        ) from error
    if resolved != candidate or not resolved.is_file():
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle input path is noncanonical or not a file"
        )
    return resolved


def _exact_keys(
    document: Mapping[str, Any],
    expected: set[str],
    label: str,
) -> None:
    if type(document) is not dict or set(document) != expected:
        raise V072SourceBundlePersistenceInvariantViolation(
            f"{label} schema keys changed"
        )


def _parse_entry(document: Any) -> CanonicalSourceBundleEntryV1:
    expected_keys = {
        "schema",
        "schema_version",
        "role",
        "authoritative_schema_id",
        "runtime_type",
        "semantic_identity_field",
        "semantic_identity",
        "semantic_document",
        "full_typed_snapshot",
        "parser_id",
        "entry_id",
    }
    _exact_keys(document, expected_keys, "source bundle entry")
    role = document["role"]
    if role not in ROLE_ORDER:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle entry role is unknown"
        )
    if (
        document["schema"]
        != "acfqp.v072_canonical_source_bundle_entry.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["parser_id"]
        != PARSER_REGISTRY[ROLE_ORDER.index(role)].parser_id
    ):
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle entry protocol identity changed"
        )
    entry = CanonicalSourceBundleEntryV1(
        role,
        document["authoritative_schema_id"],
        document["runtime_type"],
        document["semantic_identity_field"],
        document["semantic_identity"],
        document["semantic_document"],
        document["full_typed_snapshot"],
    )
    if document["entry_id"] != entry.entry_id:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle entry content ID differs from bytes"
        )
    return entry


def _parse_envelope_document(
    document: Any,
) -> CanonicalSourceBundleEnvelopeV1:
    expected_keys = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "persistence_stage",
        "ordered_roles",
        "ordered_entry_ids",
        "source_campaign_id",
        "source_campaign_verification_id",
        "source_archive_id",
        "independent_attestation_id",
        "component_id",
        "parser_registry_id",
        "typed_replay_ready",
        "typed_replay_blocker",
        "real_source_snapshot_persistence_allowed",
        "official_source_persistence_claimed",
        "entries",
        "parser_registry",
        "bundle_id",
    }
    _exact_keys(document, expected_keys, "source bundle envelope")
    if (
        document["schema"]
        != "acfqp.v072_canonical_source_bundle_envelope.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["persistence_stage"] != PERSISTENCE_STAGE
        or document["ordered_roles"] != list(ROLE_ORDER)
        or document["parser_registry"]
        != source_bundle_parser_registry_document_v1()
        or document["parser_registry_id"] != PARSER_REGISTRY_ID
        or document["typed_replay_ready"] is not False
        or document["typed_replay_blocker"] != TYPED_REPLAY_BLOCKER
        or document["real_source_snapshot_persistence_allowed"] is not False
        or document["official_source_persistence_claimed"] is not False
        or type(document["entries"]) is not list
    ):
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle envelope protocol or parser registry changed"
        )
    entries = tuple(_parse_entry(item) for item in document["entries"])
    envelope = CanonicalSourceBundleEnvelopeV1(
        entries,
        document["source_campaign_id"],
        document["source_campaign_verification_id"],
        document["source_archive_id"],
        document["independent_attestation_id"],
        document["component_id"],
    )
    if (
        document["ordered_entry_ids"]
        != [item.entry_id for item in entries]
        or document["bundle_id"] != envelope.bundle_id
        or envelope.to_document() != document
    ):
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle envelope identity differs from replay"
        )
    return envelope


def load_canonical_source_bundle_envelope_v1(
    path: str | os.PathLike[str],
) -> CanonicalSourceBundleEnvelopeV1:
    candidate = _safe_input_path(path)
    try:
        data = _read_regular_file(candidate)
    except (FileNotFoundError, OSError) as error:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle input cannot be read"
        ) from error
    try:
        document = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        V072SourceBundlePersistenceInvariantViolation,
    ) as error:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle is not strict canonical JSON"
        ) from error
    if canonical_json_bytes(document) != data:
        raise V072SourceBundlePersistenceInvariantViolation(
            "source bundle bytes are not canonical JSON"
        )
    return _parse_envelope_document(document)


def replay_typed_source_bundle_v1(
    envelope: CanonicalSourceBundleEnvelopeV1,
) -> None:
    if type(envelope) is not CanonicalSourceBundleEnvelopeV1:
        raise V072SourceBundlePersistenceInvariantViolation(
            "typed replay requires the exact source envelope type"
        )
    raise V072SourceBundlePersistenceInvariantViolation(
        TYPED_REPLAY_BLOCKER
    )


__all__ = [
    "CanonicalSourceBundleEntryV1",
    "CanonicalSourceBundleEnvelopeV1",
    "MAX_DEVELOPMENT_SNAPSHOT_PHYSICAL_DRAWS",
    "PARSER_REGISTRY",
    "PARSER_REGISTRY_ID",
    "PERSISTENCE_STAGE",
    "PROFILE_KEY",
    "ROLE_ORDER",
    "SourceBundleParserRegistrationV1",
    "TYPED_REPLAY_BLOCKER",
    "V072SourceBundlePersistenceInvariantViolation",
    "freeze_canonical_source_bundle_envelope_v1",
    "load_canonical_source_bundle_envelope_v1",
    "render_canonical_source_bundle_v1",
    "replay_typed_source_bundle_v1",
    "source_bundle_parser_registry_document_v1",
    "write_canonical_source_bundle_v1",
]
