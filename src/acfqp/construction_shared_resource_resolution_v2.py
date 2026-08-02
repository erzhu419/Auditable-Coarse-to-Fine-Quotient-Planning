"""Typed internal resolutions for the nine construction shared resources.

This module is the fail-closed boundary between a future live K7 production
broker envelope and formal V6 accounting.  It deliberately does **not** issue
``CounterRecord``, ``WorkVector`` or ``ComparisonVector`` artifacts.

The historical V1 receipt and evidence-closure layers only establish
structural coverage.  They cannot be relabelled as V2 semantic evidence.  A
V2 resolution can become ``VERIFIED_EXACT`` only after a path-specific replay
implementation has independently recomputed the value from the exact live
source bytes and its required provenance.  No such replay implementation is
installed by this construction slice, so well-formed live inputs currently
resolve to an explicit typed pending state.

The fixed catalogue records, for every shared path:

* the exact V6 owner, semantics, unit, scope and reducer;
* the required live source family;
* the exact evidence-component schemas;
* the provenance obligations which a future semantic replay must prove; and
* the stable verifier key under which that replay will be installed.

Raw evidence carries no reported numeric value.  This prevents a source claim
from becoming an actual merely because it was copied into a newer wrapper.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import re
from typing import Any, NoReturn

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_evidence_closure_v1 as closure_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.10"
PROFILE_KEY = "construction_shared_resource_resolution_v2"
LIVE_ENVELOPE_SCHEMA_ID = "acfqp.v075_k7_production_attempt_envelope.v2"

SHARED_RESOURCE_PATHS = receipts_v1.SHARED_RESOURCE_PATHS

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_COMPONENT_KEY = re.compile(r"^[a-z][a-z0-9_]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_RESOLUTION_ISSUER = object()
_RESOLUTION_SET_ISSUER = object()


class ConstructionSharedResourceResolutionV2Error(ValueError):
    """The live input, catalogue, or internal resolution is invalid."""


class SharedResourceExactSourceKindV2(str, Enum):
    HASH_EVENT_TRANSCRIPT = "HASH_EVENT_TRANSCRIPT"
    INTEGRITY_OBLIGATION_TRANSCRIPT = (
        "INTEGRITY_OBLIGATION_TRANSCRIPT"
    )
    PROTOCOL_OBLIGATION_TRANSCRIPT = "PROTOCOL_OBLIGATION_TRANSCRIPT"
    MOUNT_VISIBILITY_JOURNAL = "MOUNT_VISIBILITY_JOURNAL"
    DURABLE_OUTPUT_FIXED_POINT = "DURABLE_OUTPUT_FIXED_POINT"
    READ_TRANSFER_JOURNAL = "READ_TRANSFER_JOURNAL"
    STAGED_TRANSFER_JOURNAL = "STAGED_TRANSFER_JOURNAL"
    SAME_OFD_WORKING_PEAK = "SAME_OFD_WORKING_PEAK"
    BROKER_PROCESS_LIFECYCLE_JOURNAL = (
        "BROKER_PROCESS_LIFECYCLE_JOURNAL"
    )


class SharedResourceProvenanceProofKindV2(str, Enum):
    OCCURRENCE_IDENTITY_BINDING = "OCCURRENCE_IDENTITY_BINDING"
    CLOSED_INCLUSIVE_CUTOFF = "CLOSED_INCLUSIVE_CUTOFF"
    BROKER_AUTHENTICATED_SEQUENCE = "BROKER_AUTHENTICATED_SEQUENCE"
    FROZEN_SOURCE_SITE_COVERAGE = "FROZEN_SOURCE_SITE_COVERAGE"
    REGISTERED_PURPOSE_COVERAGE = "REGISTERED_PURPOSE_COVERAGE"
    REGISTERED_OBLIGATION_COVERAGE = "REGISTERED_OBLIGATION_COVERAGE"
    EXACT_TRANSFER_CHARGE_KEY_COVERAGE = (
        "EXACT_TRANSFER_CHARGE_KEY_COVERAGE"
    )
    EXCLUSIVE_DURABLE_WRITER_COMMIT = (
        "EXCLUSIVE_DURABLE_WRITER_COMMIT"
    )
    UNIQUE_PAYLOAD_VISIBILITY_INTERVALS = (
        "UNIQUE_PAYLOAD_VISIBILITY_INTERVALS"
    )
    SAME_OFD_PRE_POST_CGROUP_PEAK = "SAME_OFD_PRE_POST_CGROUP_PEAK"
    DESCENDANT_FREE_POST_REAP = "DESCENDANT_FREE_POST_REAP"
    PIDFD_SCM_DIRECT_REAP = "PIDFD_SCM_DIRECT_REAP"
    NO_DESCENDANT_LAUNCH = "NO_DESCENDANT_LAUNCH"


class SharedResourceResolutionStatusV2(str, Enum):
    PENDING_LIVE_EVIDENCE = "PENDING_LIVE_EVIDENCE"
    VERIFIED_EXACT = "VERIFIED_EXACT"


class SharedResourcePendingReasonV2(str, Enum):
    SOURCE_PATH_ABSENT = "SOURCE_PATH_ABSENT"
    REQUIRED_COMPONENTS_ABSENT = "REQUIRED_COMPONENTS_ABSENT"
    SEMANTIC_REPLAYER_NOT_INSTALLED = "SEMANTIC_REPLAYER_NOT_INSTALLED"


class SharedResourceReplayAvailabilityV2(str, Enum):
    NOT_INSTALLED = "NOT_INSTALLED"
    INSTALLED = "INSTALLED"


def _fail(message: str) -> NoReturn:
    raise ConstructionSharedResourceResolutionV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceResolutionV2Error(
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


def _enum(enum_type: type[Enum], value: Any, label: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceResolutionV2Error(
            f"{label} is unknown"
        ) from error


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must contain nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceResolutionV2Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must be one canonical JSON object")
    return value


@dataclass(frozen=True, slots=True)
class SharedResourceRequiredComponentV2:
    component_key: str
    source_schema_id: str

    def __post_init__(self) -> None:
        if (
            type(self.component_key) is not str
            or _COMPONENT_KEY.fullmatch(self.component_key) is None
        ):
            _fail("required component key is noncanonical")
        _identifier(self.source_schema_id, "required component schema")
        if not self.source_schema_id.endswith(".v2"):
            _fail("V2 live component schema must be an explicit V2 schema")

    def to_document(self) -> dict[str, str]:
        return {
            "component_key": self.component_key,
            "source_schema_id": self.source_schema_id,
        }


@dataclass(frozen=True, slots=True)
class SharedResourcePathContractV2:
    """One immutable path-specific semantic replay contract."""

    path: str
    owner: str
    semantics_id: str
    unit: str
    scope: str
    reducer: ReducerEnum
    exact_source_kind: SharedResourceExactSourceKindV2
    required_components: tuple[SharedResourceRequiredComponentV2, ...]
    required_provenance: tuple[SharedResourceProvenanceProofKindV2, ...]
    semantic_verifier_key: str
    replay_availability: SharedResourceReplayAvailabilityV2 = (
        SharedResourceReplayAvailabilityV2.NOT_INSTALLED
    )

    def __post_init__(self) -> None:
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        if self.path not in SHARED_RESOURCE_PATHS or leaf is None:
            _fail("path contract names an unknown shared-resource path")
        reducer = _enum(ReducerEnum, self.reducer, "path reducer")
        source_kind = _enum(
            SharedResourceExactSourceKindV2,
            self.exact_source_kind,
            "exact source kind",
        )
        availability = _enum(
            SharedResourceReplayAvailabilityV2,
            self.replay_availability,
            "semantic replay availability",
        )
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "exact_source_kind", source_kind)
        object.__setattr__(self, "replay_availability", availability)
        if (
            self.owner != leaf.owner
            or self.semantics_id != leaf.semantics_id
            or self.unit != leaf.unit
            or self.scope != leaf.scope
            or reducer is not leaf.reducer
            or not leaf.required
            or leaf.lane.value != "operational"
        ):
            _fail("path contract metadata differs from official V6")
        if (
            type(self.required_components) is not tuple
            or not self.required_components
            or any(
                type(item) is not SharedResourceRequiredComponentV2
                for item in self.required_components
            )
            or tuple(
                sorted(
                    self.required_components,
                    key=lambda item: item.component_key,
                )
            )
            != self.required_components
            or len({item.component_key for item in self.required_components})
            != len(self.required_components)
        ):
            _fail("required evidence components must be sorted and unique")
        if (
            type(self.required_provenance) is not tuple
            or not self.required_provenance
            or len(set(self.required_provenance))
            != len(self.required_provenance)
        ):
            _fail("required provenance proofs must be nonempty and unique")
        for item in self.required_provenance:
            _enum(
                SharedResourceProvenanceProofKindV2,
                item,
                "required provenance proof",
            )
        required_common = {
            SharedResourceProvenanceProofKindV2.OCCURRENCE_IDENTITY_BINDING,
            SharedResourceProvenanceProofKindV2.CLOSED_INCLUSIVE_CUTOFF,
        }
        if not required_common <= set(self.required_provenance):
            _fail("path contract omits identity or cutoff provenance")
        _identifier(self.semantic_verifier_key, "semantic verifier key")
        if availability is not SharedResourceReplayAvailabilityV2.NOT_INSTALLED:
            _fail("this slice must not claim an installed semantic replayer")

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "owner": self.owner,
            "semantics_id": self.semantics_id,
            "unit": self.unit,
            "scope": self.scope,
            "reducer": self.reducer.value,
            "exact_source_kind": self.exact_source_kind.value,
            "required_components": [
                item.to_document() for item in self.required_components
            ],
            "required_provenance": [
                item.value for item in self.required_provenance
            ],
            "semantic_verifier_key": self.semantic_verifier_key,
            "replay_availability": self.replay_availability.value,
        }


def _components(
    *rows: tuple[str, str],
) -> tuple[SharedResourceRequiredComponentV2, ...]:
    return tuple(
        sorted(
            (
                SharedResourceRequiredComponentV2(key, schema)
                for key, schema in rows
            ),
            key=lambda item: item.component_key,
        )
    )


_IDENTITY_AND_CUTOFF = (
    SharedResourceProvenanceProofKindV2.OCCURRENCE_IDENTITY_BINDING,
    SharedResourceProvenanceProofKindV2.CLOSED_INCLUSIVE_CUTOFF,
)


_PATH_SOURCE_BLUEPRINTS: dict[
    str,
    tuple[
        SharedResourceExactSourceKindV2,
        tuple[SharedResourceRequiredComponentV2, ...],
        tuple[SharedResourceProvenanceProofKindV2, ...],
        str,
    ],
] = {
    "common.hash_invocations": (
        SharedResourceExactSourceKindV2.HASH_EVENT_TRANSCRIPT,
        _components(
            (
                "cutoff_attestation",
                "acfqp.v075_k7_operational_cutoff_attestation.v2",
            ),
            (
                "hash_event_transcript",
                "acfqp.v075_k7_hash_event_transcript.v2",
            ),
            (
                "hash_purpose_registry",
                "acfqp.v075_k7_hash_purpose_registry.v2",
            ),
            (
                "loaded_source_site_attestation",
                "acfqp.v075_k7_loaded_hash_site_attestation.v2",
            ),
        ),
        _IDENTITY_AND_CUTOFF
        + (
            SharedResourceProvenanceProofKindV2.BROKER_AUTHENTICATED_SEQUENCE,
            SharedResourceProvenanceProofKindV2.FROZEN_SOURCE_SITE_COVERAGE,
            SharedResourceProvenanceProofKindV2.REGISTERED_PURPOSE_COVERAGE,
        ),
        "verify_hash_invocations_exact_v2",
    ),
    "common.integrity_checks": (
        SharedResourceExactSourceKindV2.INTEGRITY_OBLIGATION_TRANSCRIPT,
        _components(
            (
                "cutoff_attestation",
                "acfqp.v075_k7_operational_cutoff_attestation.v2",
            ),
            (
                "integrity_obligation_registry",
                "acfqp.v075_k7_integrity_obligation_registry.v2",
            ),
            (
                "integrity_obligation_transcript",
                "acfqp.v075_k7_integrity_obligation_transcript.v2",
            ),
            (
                "loaded_source_site_attestation",
                "acfqp.v075_k7_loaded_integrity_site_attestation.v2",
            ),
        ),
        _IDENTITY_AND_CUTOFF
        + (
            SharedResourceProvenanceProofKindV2.BROKER_AUTHENTICATED_SEQUENCE,
            SharedResourceProvenanceProofKindV2.FROZEN_SOURCE_SITE_COVERAGE,
            SharedResourceProvenanceProofKindV2.REGISTERED_OBLIGATION_COVERAGE,
        ),
        "verify_integrity_checks_exact_v2",
    ),
    "common.protocol_checks": (
        SharedResourceExactSourceKindV2.PROTOCOL_OBLIGATION_TRANSCRIPT,
        _components(
            (
                "cutoff_attestation",
                "acfqp.v075_k7_operational_cutoff_attestation.v2",
            ),
            (
                "loaded_source_site_attestation",
                "acfqp.v075_k7_loaded_protocol_site_attestation.v2",
            ),
            (
                "protocol_obligation_registry",
                "acfqp.v075_k7_protocol_obligation_registry.v2",
            ),
            (
                "protocol_obligation_transcript",
                "acfqp.v075_k7_protocol_obligation_transcript.v2",
            ),
        ),
        _IDENTITY_AND_CUTOFF
        + (
            SharedResourceProvenanceProofKindV2.BROKER_AUTHENTICATED_SEQUENCE,
            SharedResourceProvenanceProofKindV2.FROZEN_SOURCE_SITE_COVERAGE,
            SharedResourceProvenanceProofKindV2.REGISTERED_OBLIGATION_COVERAGE,
        ),
        "verify_protocol_checks_exact_v2",
    ),
    "io.mounted_bytes_peak": (
        SharedResourceExactSourceKindV2.MOUNT_VISIBILITY_JOURNAL,
        _components(
            (
                "cutoff_attestation",
                "acfqp.v075_k7_operational_cutoff_attestation.v2",
            ),
            (
                "mount_payload_registry",
                "acfqp.v075_k7_mount_payload_registry.v2",
            ),
            (
                "mount_visibility_journal",
                "acfqp.v075_k7_mount_visibility_journal.v2",
            ),
        ),
        _IDENTITY_AND_CUTOFF
        + (
            SharedResourceProvenanceProofKindV2.UNIQUE_PAYLOAD_VISIBILITY_INTERVALS,
        ),
        "verify_mounted_bytes_peak_exact_v2",
    ),
    "io.output_bytes": (
        SharedResourceExactSourceKindV2.DURABLE_OUTPUT_FIXED_POINT,
        _components(
            (
                "durable_output_fixed_point",
                "acfqp.v075_k7_durable_output_fixed_point.v2",
            ),
            (
                "exclusive_writer_attestation",
                "acfqp.v075_k7_exclusive_writer_attestation.v2",
            ),
            (
                "operational_cutoff_attestation",
                "acfqp.v075_k7_operational_cutoff_attestation.v2",
            ),
            (
                "output_manifest",
                "acfqp.v075_k7_eight_role_output_manifest.v2",
            ),
        ),
        _IDENTITY_AND_CUTOFF
        + (
            SharedResourceProvenanceProofKindV2.EXCLUSIVE_DURABLE_WRITER_COMMIT,
        ),
        "verify_output_bytes_exact_v2",
    ),
    "io.read_bytes": (
        SharedResourceExactSourceKindV2.READ_TRANSFER_JOURNAL,
        _components(
            (
                "cutoff_attestation",
                "acfqp.v075_k7_operational_cutoff_attestation.v2",
            ),
            (
                "read_transfer_journal",
                "acfqp.v075_k7_read_transfer_journal.v2",
            ),
            (
                "transfer_charge_registry",
                "acfqp.v075_k7_transfer_charge_registry.v2",
            ),
        ),
        _IDENTITY_AND_CUTOFF
        + (
            SharedResourceProvenanceProofKindV2.BROKER_AUTHENTICATED_SEQUENCE,
            SharedResourceProvenanceProofKindV2.EXACT_TRANSFER_CHARGE_KEY_COVERAGE,
        ),
        "verify_read_bytes_exact_v2",
    ),
    "io.staged_bytes": (
        SharedResourceExactSourceKindV2.STAGED_TRANSFER_JOURNAL,
        _components(
            (
                "cutoff_attestation",
                "acfqp.v075_k7_operational_cutoff_attestation.v2",
            ),
            (
                "staged_transfer_journal",
                "acfqp.v075_k7_staged_transfer_journal.v2",
            ),
            (
                "transfer_charge_registry",
                "acfqp.v075_k7_transfer_charge_registry.v2",
            ),
        ),
        _IDENTITY_AND_CUTOFF
        + (
            SharedResourceProvenanceProofKindV2.BROKER_AUTHENTICATED_SEQUENCE,
            SharedResourceProvenanceProofKindV2.EXACT_TRANSFER_CHARGE_KEY_COVERAGE,
        ),
        "verify_staged_bytes_exact_v2",
    ),
    "memory.working_bytes_peak": (
        SharedResourceExactSourceKindV2.SAME_OFD_WORKING_PEAK,
        _components(
            (
                "cgroup_empty_attestation",
                "acfqp.v075_k7_cgroup_empty_attestation.v2",
            ),
            (
                "memory_peak_post_read",
                "acfqp.v075_k7_memory_peak_post_read.v2",
            ),
            (
                "memory_peak_pre_read",
                "acfqp.v075_k7_memory_peak_pre_read.v2",
            ),
            (
                "same_ofd_attestation",
                "acfqp.v075_k7_same_ofd_attestation.v2",
            ),
        ),
        _IDENTITY_AND_CUTOFF
        + (
            SharedResourceProvenanceProofKindV2.SAME_OFD_PRE_POST_CGROUP_PEAK,
            SharedResourceProvenanceProofKindV2.DESCENDANT_FREE_POST_REAP,
        ),
        "verify_working_bytes_peak_exact_v2",
    ),
    "process.launches": (
        SharedResourceExactSourceKindV2.BROKER_PROCESS_LIFECYCLE_JOURNAL,
        _components(
            (
                "cutoff_attestation",
                "acfqp.v075_k7_operational_cutoff_attestation.v2",
            ),
            (
                "no_spawn_attestation",
                "acfqp.v075_k7_no_spawn_attestation.v2",
            ),
            (
                "pidfd_reap_attestation",
                "acfqp.v075_k7_pidfd_reap_attestation.v2",
            ),
            (
                "process_lifecycle_journal",
                "acfqp.v075_k7_process_lifecycle_journal.v2",
            ),
        ),
        _IDENTITY_AND_CUTOFF
        + (
            SharedResourceProvenanceProofKindV2.BROKER_AUTHENTICATED_SEQUENCE,
            SharedResourceProvenanceProofKindV2.PIDFD_SCM_DIRECT_REAP,
            SharedResourceProvenanceProofKindV2.NO_DESCENDANT_LAUNCH,
        ),
        "verify_process_launches_exact_v2",
    ),
}


def _build_official_catalogue() -> tuple[SharedResourcePathContractV2, ...]:
    registry = registry_v6.official_counter_registry_v6()
    rows: list[SharedResourcePathContractV2] = []
    for path in SHARED_RESOURCE_PATHS:
        leaf = registry.by_path[path]
        source, components, provenance, verifier_key = (
            _PATH_SOURCE_BLUEPRINTS[path]
        )
        rows.append(
            SharedResourcePathContractV2(
                path=path,
                owner=leaf.owner,
                semantics_id=leaf.semantics_id,
                unit=leaf.unit,
                scope=leaf.scope,
                reducer=leaf.reducer,
                exact_source_kind=source,
                required_components=components,
                required_provenance=provenance,
                semantic_verifier_key=verifier_key,
            )
        )
    return tuple(rows)


_OFFICIAL_CATALOGUE = _build_official_catalogue()


def official_shared_resource_resolution_catalogue_v2(
) -> tuple[SharedResourcePathContractV2, ...]:
    """Return the immutable nine-path exact-source catalogue."""

    return _OFFICIAL_CATALOGUE


def official_shared_resource_catalogue_fingerprint_v2() -> str:
    """Return an internal digest, not a formal content-addressed artifact ID."""

    payload = {
        "schema": "acfqp.construction_shared_resource_resolution_catalogue.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "contracts": [item.to_document() for item in _OFFICIAL_CATALOGUE],
        "internal_only": True,
        "formal_artifact_id": None,
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedResourceEvidenceComponentV2:
    """One immutable raw evidence component; it contains no numeric actual."""

    component_key: str
    source_schema_id: str
    source_artifact_id: str
    source_bytes_sha256: str
    raw_bytes: bytes = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            type(self.component_key) is not str
            or _COMPONENT_KEY.fullmatch(self.component_key) is None
        ):
            _fail("live evidence component key is noncanonical")
        _identifier(self.source_schema_id, "live component schema")
        _cid(self.source_artifact_id, "live component artifact")
        if (
            type(self.source_bytes_sha256) is not str
            or _SHA256.fullmatch(self.source_bytes_sha256) is None
        ):
            _fail("live component digest is not lowercase SHA-256")
        document = _canonical_object(self.raw_bytes, "live component bytes")
        if document.get("schema") != self.source_schema_id:
            _fail("live component schema label differs from its bytes")
        if hashlib.sha256(self.raw_bytes).hexdigest() != self.source_bytes_sha256:
            _fail("live component digest differs from its bytes")
        if self.source_schema_id.endswith(".v1"):
            _fail("historical V1 evidence cannot be relabelled as V2")
        false_authority_flags = {
            "source_evidence_semantics_verified",
            "numeric_value_authorized",
            "numeric_projection_allowed",
            "formal_vector_authorized",
            "current_live_accounting_closed",
        }
        if any(document.get(key) is False for key in false_authority_flags):
            _fail("explicitly unverified source bytes cannot be relabelled")

    def to_internal_document(self) -> dict[str, Any]:
        return {
            "component_key": self.component_key,
            "source_schema_id": self.source_schema_id,
            "source_artifact_id": self.source_artifact_id,
            "source_bytes_sha256": self.source_bytes_sha256,
            "source_byte_count": len(self.raw_bytes),
            "raw_bytes_embedded_in_resolution": False,
        }


@dataclass(frozen=True, slots=True)
class SharedResourceLiveSourceV2:
    """One path's broker/supervisor source bundle before semantic replay."""

    live_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    path: str
    exact_source_kind: SharedResourceExactSourceKindV2
    provenance_claims: tuple[SharedResourceProvenanceProofKindV2, ...]
    covered_start_sequence: int
    covered_cutoff_sequence: int
    components: tuple[SharedResourceEvidenceComponentV2, ...] = field(
        repr=False
    )

    def __post_init__(self) -> None:
        for value, label in (
            (self.live_envelope_id, "source live envelope"),
            (self.occurrence_id, "source occurrence"),
            (self.route_attempt_id, "source route attempt"),
            (self.decision_point_id, "source decision point"),
            (self.measurement_window_id, "source measurement window"),
            (self.operational_cutoff_id, "source operational cutoff"),
        ):
            _cid(value, label)
        if self.path not in SHARED_RESOURCE_PATHS:
            _fail("live source names an unknown shared-resource path")
        source_kind = _enum(
            SharedResourceExactSourceKindV2,
            self.exact_source_kind,
            "live exact source kind",
        )
        object.__setattr__(self, "exact_source_kind", source_kind)
        if (
            type(self.provenance_claims) is not tuple
            or len(set(self.provenance_claims))
            != len(self.provenance_claims)
        ):
            _fail("live provenance claims must be a unique tuple")
        for item in self.provenance_claims:
            _enum(
                SharedResourceProvenanceProofKindV2,
                item,
                "live provenance claim",
            )
        _nonnegative(self.covered_start_sequence, "source start sequence")
        _nonnegative(self.covered_cutoff_sequence, "source cutoff sequence")
        if self.covered_cutoff_sequence < self.covered_start_sequence:
            _fail("live source cutoff precedes its start")
        if (
            type(self.components) is not tuple
            or any(
                type(item) is not SharedResourceEvidenceComponentV2
                for item in self.components
            )
            or tuple(
                sorted(self.components, key=lambda item: item.component_key)
            )
            != self.components
            or len({item.component_key for item in self.components})
            != len(self.components)
        ):
            _fail("live components must be content-key sorted and unique")


@dataclass(frozen=True, slots=True)
class SharedResourceLiveEnvelopeV2:
    """Typed adapter input for a future production-attempt live envelope."""

    live_envelope_schema_id: str
    live_envelope_id: str
    counter_registry_id: str
    stage_profile_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    measurement_start_sequence: int
    operational_cutoff_sequence: int
    catalogue_fingerprint: str
    sources: tuple[SharedResourceLiveSourceV2, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if self.live_envelope_schema_id != LIVE_ENVELOPE_SCHEMA_ID:
            _fail("live envelope uses an unregistered adapter schema")
        for value, label in (
            (self.live_envelope_id, "live envelope"),
            (self.counter_registry_id, "live counter registry"),
            (self.stage_profile_id, "live stage profile"),
            (self.occurrence_id, "live occurrence"),
            (self.route_attempt_id, "live route attempt"),
            (self.decision_point_id, "live decision point"),
            (self.measurement_window_id, "live measurement window"),
            (self.operational_cutoff_id, "live operational cutoff"),
        ):
            _cid(value, label)
        registry = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage.stage_profile_id
        ):
            _fail("live envelope is not bound to official V6 registry/stage")
        _nonnegative(self.measurement_start_sequence, "measurement start")
        _nonnegative(self.operational_cutoff_sequence, "operational cutoff")
        if self.operational_cutoff_sequence < self.measurement_start_sequence:
            _fail("live envelope cutoff precedes its measurement start")
        if (
            type(self.catalogue_fingerprint) is not str
            or _SHA256.fullmatch(self.catalogue_fingerprint) is None
            or self.catalogue_fingerprint
            != official_shared_resource_catalogue_fingerprint_v2()
        ):
            _fail("live envelope is not bound to the fixed nine-path catalogue")
        if (
            type(self.sources) is not tuple
            or any(
                type(item) is not SharedResourceLiveSourceV2
                for item in self.sources
            )
        ):
            _fail("live envelope sources have the wrong runtime type")
        expected_order = {path: index for index, path in enumerate(SHARED_RESOURCE_PATHS)}
        paths = tuple(item.path for item in self.sources)
        if (
            len(set(paths)) != len(paths)
            or tuple(sorted(paths, key=expected_order.__getitem__)) != paths
        ):
            _fail("live envelope sources must be canonical-path ordered and unique")
        for source in self.sources:
            if (
                source.live_envelope_id != self.live_envelope_id
                or source.occurrence_id != self.occurrence_id
                or source.route_attempt_id != self.route_attempt_id
                or source.decision_point_id != self.decision_point_id
                or source.measurement_window_id != self.measurement_window_id
                or source.operational_cutoff_id != self.operational_cutoff_id
                or source.covered_start_sequence
                != self.measurement_start_sequence
                or source.covered_cutoff_sequence
                != self.operational_cutoff_sequence
            ):
                _fail("live source crossed its envelope identity or cutoff")


@dataclass(frozen=True, slots=True)
class SharedResourceResolutionV2:
    """Internal result; verified values require the private replay issuer."""

    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    live_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    path: str
    exact_source_kind: SharedResourceExactSourceKindV2
    required_provenance: tuple[SharedResourceProvenanceProofKindV2, ...]
    semantic_verifier_key: str
    status: SharedResourceResolutionStatusV2
    pending_reason: SharedResourcePendingReasonV2 | None
    exact_value: int | None
    present_component_keys: tuple[str, ...]
    missing_component_keys: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]
    source_bytes_sha256: tuple[str, ...]
    semantic_verifier_id: str | None
    source_bytes_replayed: bool
    provenance_replayed: bool
    complete_window_verified: bool
    identity_binding_verified: bool
    reducer_verified: bool
    counter_record_issuance_authorized: bool = False

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESOLUTION_ISSUER:
            _fail("shared-resource resolution is caller-minted")
        for value, label in (
            (self.counter_registry_id, "resolution counter registry"),
            (self.stage_profile_id, "resolution stage profile"),
            (self.live_envelope_id, "resolution live envelope"),
            (self.occurrence_id, "resolution occurrence"),
            (self.route_attempt_id, "resolution route attempt"),
            (self.decision_point_id, "resolution decision point"),
            (self.measurement_window_id, "resolution measurement window"),
            (self.operational_cutoff_id, "resolution operational cutoff"),
        ):
            _cid(value, label)
        if self.path not in SHARED_RESOURCE_PATHS:
            _fail("resolution names an unknown shared-resource path")
        source_kind = _enum(
            SharedResourceExactSourceKindV2,
            self.exact_source_kind,
            "resolution source kind",
        )
        status = _enum(
            SharedResourceResolutionStatusV2,
            self.status,
            "resolution status",
        )
        object.__setattr__(self, "exact_source_kind", source_kind)
        object.__setattr__(self, "status", status)
        pending = (
            None
            if self.pending_reason is None
            else _enum(
                SharedResourcePendingReasonV2,
                self.pending_reason,
                "pending reason",
            )
        )
        object.__setattr__(self, "pending_reason", pending)
        _identifier(self.semantic_verifier_key, "resolution verifier key")
        for values, label in (
            (self.present_component_keys, "present component keys"),
            (self.missing_component_keys, "missing component keys"),
            (self.source_artifact_ids, "source artifact IDs"),
            (self.source_bytes_sha256, "source byte digests"),
        ):
            if type(values) is not tuple or len(set(values)) != len(values):
                _fail(f"{label} must be a unique tuple")
        for value in self.source_artifact_ids:
            _cid(value, "resolution source artifact")
        for value in self.source_bytes_sha256:
            if type(value) is not str or _SHA256.fullmatch(value) is None:
                _fail("resolution source digest is invalid")
        flags = (
            self.source_bytes_replayed,
            self.provenance_replayed,
            self.complete_window_verified,
            self.identity_binding_verified,
            self.reducer_verified,
            self.counter_record_issuance_authorized,
        )
        if any(type(value) is not bool for value in flags):
            _fail("resolution verification flags must be exact bools")
        if self.counter_record_issuance_authorized is not False:
            _fail("this internal slice cannot authorize CounterRecord issuance")
        if status is SharedResourceResolutionStatusV2.PENDING_LIVE_EVIDENCE:
            if (
                pending is None
                or self.exact_value is not None
                or self.semantic_verifier_id is not None
                or any(flags[:-1])
            ):
                _fail("pending resolution carries verified or numeric authority")
        else:
            if (
                pending is not None
                or type(self.exact_value) is not int
                or self.exact_value < 0
                or self.semantic_verifier_id is None
                or not all(flags[:-1])
                or self.missing_component_keys
            ):
                _fail("VERIFIED_EXACT lacks complete semantic replay authority")
            _cid(self.semantic_verifier_id, "semantic verifier")

    @property
    def eligible_as_verified_shared_resolution(self) -> bool:
        return self.status is SharedResourceResolutionStatusV2.VERIFIED_EXACT

    def to_internal_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_resolution.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "live_envelope_id": self.live_envelope_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "measurement_window_id": self.measurement_window_id,
            "operational_cutoff_id": self.operational_cutoff_id,
            "path": self.path,
            "exact_source_kind": self.exact_source_kind.value,
            "required_provenance": [item.value for item in self.required_provenance],
            "semantic_verifier_key": self.semantic_verifier_key,
            "status": self.status.value,
            "pending_reason": (
                None if self.pending_reason is None else self.pending_reason.value
            ),
            "exact_value": self.exact_value,
            "present_component_keys": list(self.present_component_keys),
            "missing_component_keys": list(self.missing_component_keys),
            "source_artifact_ids": list(self.source_artifact_ids),
            "source_bytes_sha256": list(self.source_bytes_sha256),
            "semantic_verifier_id": self.semantic_verifier_id,
            "source_bytes_replayed": self.source_bytes_replayed,
            "provenance_replayed": self.provenance_replayed,
            "complete_window_verified": self.complete_window_verified,
            "identity_binding_verified": self.identity_binding_verified,
            "reducer_verified": self.reducer_verified,
            "eligible_as_verified_shared_resolution": (
                self.eligible_as_verified_shared_resolution
            ),
            "counter_record_issuance_authorized": False,
            "counter_record_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vector_authorized": False,
            "internal_only": True,
        }


@dataclass(frozen=True, slots=True)
class SharedResourceResolutionSetV2:
    _issuer: InitVar[object]
    live_envelope: SharedResourceLiveEnvelopeV2 = field(repr=False)
    catalogue_fingerprint: str
    resolutions: tuple[SharedResourceResolutionV2, ...]

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESOLUTION_SET_ISSUER
            or type(self.live_envelope) is not SharedResourceLiveEnvelopeV2
            or type(self.resolutions) is not tuple
            or tuple(item.path for item in self.resolutions)
            != SHARED_RESOURCE_PATHS
            or any(
                type(item) is not SharedResourceResolutionV2
                for item in self.resolutions
            )
        ):
            _fail("resolution set is caller-minted or lacks the nine paths")
        if self.catalogue_fingerprint != (
            official_shared_resource_catalogue_fingerprint_v2()
        ):
            _fail("resolution set crossed its fixed catalogue")
        envelope = self.live_envelope
        for item in self.resolutions:
            if (
                item.counter_registry_id != envelope.counter_registry_id
                or item.stage_profile_id != envelope.stage_profile_id
                or item.live_envelope_id != envelope.live_envelope_id
                or item.occurrence_id != envelope.occurrence_id
                or item.route_attempt_id != envelope.route_attempt_id
                or item.decision_point_id != envelope.decision_point_id
                or item.measurement_window_id
                != envelope.measurement_window_id
                or item.operational_cutoff_id
                != envelope.operational_cutoff_id
            ):
                _fail("resolution set contains a transplanted path resolution")

    @property
    def all_nine_verified_exact(self) -> bool:
        return all(
            item.status is SharedResourceResolutionStatusV2.VERIFIED_EXACT
            for item in self.resolutions
        )

    @property
    def pending_live_fields(self) -> dict[str, tuple[str, ...]]:
        return {
            item.path: item.missing_component_keys
            for item in self.resolutions
            if item.status
            is SharedResourceResolutionStatusV2.PENDING_LIVE_EVIDENCE
        }

    def to_internal_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_resolution_set.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "live_envelope_id": self.live_envelope.live_envelope_id,
            "counter_registry_id": self.live_envelope.counter_registry_id,
            "stage_profile_id": self.live_envelope.stage_profile_id,
            "catalogue_fingerprint": self.catalogue_fingerprint,
            "resolutions": [
                item.to_internal_document() for item in self.resolutions
            ],
            "all_nine_verified_exact": self.all_nine_verified_exact,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "actual_projection_proof_issued": False,
            "formal_vector_authorized": False,
            "internal_only": True,
        }


def _validate_catalogue(
    selected: tuple[SharedResourcePathContractV2, ...] | None,
) -> tuple[SharedResourcePathContractV2, ...]:
    catalogue = _OFFICIAL_CATALOGUE if selected is None else selected
    if (
        type(catalogue) is not tuple
        or any(type(item) is not SharedResourcePathContractV2 for item in catalogue)
        or tuple(item.path for item in catalogue) != SHARED_RESOURCE_PATHS
        or tuple(item.to_document() for item in catalogue)
        != tuple(item.to_document() for item in _OFFICIAL_CATALOGUE)
    ):
        _fail("semantic verification requires the exact fixed nine-path catalogue")
    return catalogue


def _pending_resolution(
    *,
    envelope: SharedResourceLiveEnvelopeV2,
    contract: SharedResourcePathContractV2,
    source: SharedResourceLiveSourceV2 | None,
    reason: SharedResourcePendingReasonV2,
    missing: tuple[str, ...],
) -> SharedResourceResolutionV2:
    components = () if source is None else source.components
    return SharedResourceResolutionV2(
        _RESOLUTION_ISSUER,
        envelope.counter_registry_id,
        envelope.stage_profile_id,
        envelope.live_envelope_id,
        envelope.occurrence_id,
        envelope.route_attempt_id,
        envelope.decision_point_id,
        envelope.measurement_window_id,
        envelope.operational_cutoff_id,
        contract.path,
        contract.exact_source_kind,
        contract.required_provenance,
        contract.semantic_verifier_key,
        SharedResourceResolutionStatusV2.PENDING_LIVE_EVIDENCE,
        reason,
        None,
        tuple(item.component_key for item in components),
        missing,
        tuple(item.source_artifact_id for item in components),
        tuple(item.source_bytes_sha256 for item in components),
        None,
        False,
        False,
        False,
        False,
        False,
        False,
    )


_LEGACY_UNVERIFIED_TYPES = (
    receipts_v1.SharedResourceSourceEvidenceV1,
    receipts_v1.SharedResourceReceiptV1,
    receipts_v1.SharedResourceReceiptSetV1,
    closure_v1.RequiredPathResolutionV1,
    closure_v1.EvidenceClosureV1,
    closure_v1.EvidenceClosureCoverageReplayV1,
)


def verify_v075_k7_shared_resource_semantics_v2(
    live_envelope: Any,
    *,
    catalogue: tuple[SharedResourcePathContractV2, ...] | None = None,
) -> SharedResourceResolutionSetV2:
    """Verify the typed boundary and return nine fail-closed resolutions.

    This function intentionally has no ``reported_values`` argument and no
    caller-supplied verifier callback.  Historical receipts/closures and
    arbitrary mappings are rejected.  Complete V2 raw components remain
    pending until their fixed path-specific replay implementation is added.
    """

    if type(live_envelope) in _LEGACY_UNVERIFIED_TYPES:
        _fail("historical unverified receipt/closure cannot be relabelled as V2")
    if type(live_envelope) is not SharedResourceLiveEnvelopeV2:
        _fail("semantic verification requires the typed live-envelope adapter")
    selected = _validate_catalogue(catalogue)
    if live_envelope.catalogue_fingerprint != (
        official_shared_resource_catalogue_fingerprint_v2()
    ):
        _fail("live envelope crossed the fixed catalogue")
    by_path = {item.path: item for item in live_envelope.sources}
    resolutions: list[SharedResourceResolutionV2] = []
    for contract in selected:
        source = by_path.get(contract.path)
        required = {
            item.component_key: item.source_schema_id
            for item in contract.required_components
        }
        if source is None:
            resolutions.append(
                _pending_resolution(
                    envelope=live_envelope,
                    contract=contract,
                    source=None,
                    reason=SharedResourcePendingReasonV2.SOURCE_PATH_ABSENT,
                    missing=tuple(sorted(required)),
                )
            )
            continue
        if source.exact_source_kind is not contract.exact_source_kind:
            _fail(f"{contract.path} live source kind differs from catalogue")
        if source.provenance_claims != contract.required_provenance:
            _fail(f"{contract.path} provenance claims differ from catalogue")
        present = {item.component_key: item for item in source.components}
        unexpected = set(present) - set(required)
        if unexpected:
            _fail(f"{contract.path} contains unregistered evidence components")
        for key in set(present) & set(required):
            if present[key].source_schema_id != required[key]:
                _fail(f"{contract.path} component schema differs from catalogue")
        missing = tuple(sorted(set(required) - set(present)))
        if missing:
            reason = SharedResourcePendingReasonV2.REQUIRED_COMPONENTS_ABSENT
        else:
            # No semantic replayer is installed in this slice.  Do not turn
            # structurally complete bytes into a numeric actual.
            reason = (
                SharedResourcePendingReasonV2.SEMANTIC_REPLAYER_NOT_INSTALLED
            )
        resolutions.append(
            _pending_resolution(
                envelope=live_envelope,
                contract=contract,
                source=source,
                reason=reason,
                missing=missing,
            )
        )
    return SharedResourceResolutionSetV2(
        _RESOLUTION_SET_ISSUER,
        live_envelope,
        official_shared_resource_catalogue_fingerprint_v2(),
        tuple(resolutions),
    )


__all__ = [
    "ConstructionSharedResourceResolutionV2Error",
    "LIVE_ENVELOPE_SCHEMA_ID",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SHARED_RESOURCE_PATHS",
    "SharedResourceEvidenceComponentV2",
    "SharedResourceExactSourceKindV2",
    "SharedResourceLiveEnvelopeV2",
    "SharedResourceLiveSourceV2",
    "SharedResourcePathContractV2",
    "SharedResourcePendingReasonV2",
    "SharedResourceProvenanceProofKindV2",
    "SharedResourceReplayAvailabilityV2",
    "SharedResourceRequiredComponentV2",
    "SharedResourceResolutionSetV2",
    "SharedResourceResolutionStatusV2",
    "SharedResourceResolutionV2",
    "official_shared_resource_catalogue_fingerprint_v2",
    "official_shared_resource_resolution_catalogue_v2",
    "verify_v075_k7_shared_resource_semantics_v2",
]
