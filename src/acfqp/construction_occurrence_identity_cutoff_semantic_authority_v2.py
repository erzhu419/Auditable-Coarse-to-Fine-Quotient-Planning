"""Positive K7 occurrence-identity and operational-cutoff authorities.

The historical :mod:`construction_occurrence_identity_cutoff_join_v1` objects
are deliberately structural.  This successor does not relabel them.  It
replays the V1 roots, then joins them to four independently held production
authorities:

* a freshly reconstructed successor request;
* an exact K7 production broker runtime envelope;
* the exact nine-path shared-resource replay envelope; and
* the production durable-output source bytes.

The resulting authorities are narrow prerequisites for a future atomic
202-path materializer.  They do not issue CounterRecords or vectors.  A V3
shared-resource envelope by itself is insufficient: the positive path
requires an exact production runtime envelope and production-adopted output.

The V1 marker sequence is a *global closure index*, not a renumbering of the
nine independent source-local journals.  Every path authorization represents
one independently replayed source-local event stream.  The four post-cutoff
markers name the exact output accounting/provenance components; replay proves
that their bytes are absent from the durable eight-role output total.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Iterable, Mapping, NoReturn

from acfqp import construction_accounting_owner_event_candidates_v1 as owner_events_v1
from acfqp import construction_accounting_evidence_closure_v1 as closure_v1
from acfqp import construction_accounting_partial_native_v1 as partial_v1
from acfqp import construction_occurrence_identity_cutoff_join_v1 as join_v1
from acfqp import construction_shared_resource_live_envelope_v3 as live_v3
from acfqp import construction_shared_resource_output_journal_v2 as output_v2
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import construction_shared_resource_verified_envelope_v1 as verified_v1
from acfqp import v075_k7_production_broker_runtime_v2 as runtime_v2
from acfqp import v075_k7_production_role_manifest_v2 as role_manifest_v2
from acfqp import v075_k7_broker_worker_entry_v1 as worker_v1
from acfqp import v075_k7_child_business_bundle_v1 as child_bundle_v1
from acfqp import v075_k7_root_cap_owned_partial_runner_v1 as owned_v1
from acfqp import v075_k7_successor_portable_replay_v1 as request_replay_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OCCURRENCE_CUTOFF_SEMANTIC_AUTHORITY_BUNDLE_V2_DOMAIN as AUTHORITY_BUNDLE_V2_DOMAIN,
    CONSTRUCTION_K7_OCCURRENCE_IDENTITY_SEMANTIC_AUTHORITY_V2_DOMAIN as OCCURRENCE_AUTHORITY_V2_DOMAIN,
    CONSTRUCTION_K7_OPERATIONAL_CUTOFF_SEMANTIC_AUTHORITY_V2_DOMAIN as CUTOFF_AUTHORITY_V2_DOMAIN,
    CONSTRUCTION_K7_PRODUCTION_MEASUREMENT_CUTOFF_V2_DOMAIN as MEASUREMENT_CUTOFF_V2_DOMAIN,
    CONSTRUCTION_K7_PRODUCTION_MEASUREMENT_START_V2_DOMAIN as MEASUREMENT_START_V2_DOMAIN,
    CONSTRUCTION_K7_PRODUCTION_TERMINAL_CLOSURE_V2_DOMAIN as TERMINAL_CLOSURE_V2_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.25"
PROFILE_KEY = "construction_occurrence_identity_cutoff_semantic_authority_v2"

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    OCCURRENCE_AUTHORITY_V2_DOMAIN,
    CUTOFF_AUTHORITY_V2_DOMAIN,
    AUTHORITY_BUNDLE_V2_DOMAIN,
    MEASUREMENT_START_V2_DOMAIN,
    MEASUREMENT_CUTOFF_V2_DOMAIN,
    TERMINAL_CLOSURE_V2_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS))
    != len(REQUESTED_PHASE3E_DOMAIN_TAGS)
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover
    raise RuntimeError("occurrence/cutoff semantic authority domains are not central and unique")

GLOBAL_START_SEQUENCE = 0
GLOBAL_TERMINAL_SEQUENCE = 1
GLOBAL_FIRST_SOURCE_SEQUENCE = 2
GLOBAL_CUTOFF_SEQUENCE = (
    GLOBAL_FIRST_SOURCE_SEQUENCE + len(resolution_v2.SHARED_RESOURCE_PATHS)
)

_OCCURRENCE_ISSUER = object()
_CUTOFF_ISSUER = object()
_BUNDLE_ISSUER = object()


class ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error(ValueError):
    """A production identity, source event, cutoff, or tail was crossed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS or domain not in PHASE3E_DOMAIN_TAGS:
        _fail("semantic authority used a noncentral domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must be one canonical object")
    return value


def _runtime_request_payload(
    *,
    kind: str,
    runtime_envelope_id: str,
    request_replay_id: str,
    request_id: str,
    route_identity_id: str,
) -> dict[str, Any]:
    return {
        "schema": f"acfqp.construction_k7_production_{kind}.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "production_runtime_envelope_id": runtime_envelope_id,
        "portable_request_replay_id": request_replay_id,
        "request_id": request_id,
        "route_identity_id": route_identity_id,
    }


@dataclass(frozen=True, slots=True)
class _ValidatedRuntimeRequestV2:
    runtime_id: str
    request_replay_id: str
    request_id: str
    route_identity_id: str
    broker_transcript_id: str
    frame_observation_ids: tuple[str, ...]
    operational_output_id: str
    cgroup_cleanup_complete: bool
    resource_cleanup_complete: bool


def _validate_runtime_request(
    *,
    runtime_envelope: Any,
    request_replay: Any,
) -> _ValidatedRuntimeRequestV2:
    if type(runtime_envelope) is not runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2:
        _fail("positive authority requires one exact real production runtime envelope")
    if (
        type(request_replay)
        is not request_replay_v1.V075K7SuccessorPortableRequestReplayV1
    ):
        _fail("positive authority requires one exact independent request replay")
    try:
        runtime_document = runtime_envelope.to_document()
        request = request_replay.request
        replay_id = request_replay.replay_id
        route = request.route_identity
        runtime_id = _cid(
            runtime_document.get("production_broker_runtime_envelope_id"),
            "production runtime envelope",
        )
    except Exception as error:
        raise ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error(
            "production runtime or request replay is stale"
        ) from error
    if (
        runtime_envelope.binding.request_id != request.request_id
        or runtime_envelope.binding.route_identity_id != route.route_identity_id
    ):
        _fail("production runtime crossed its request or route identity")
    return _ValidatedRuntimeRequestV2(
        runtime_id,
        replay_id,
        request.request_id,
        route.route_identity_id,
        runtime_envelope.transcript.transcript_id,
        tuple(row.observation_id for row in runtime_envelope.frame_observations),
        runtime_envelope.operational_output_id,
        runtime_envelope.cgroup_cleanup_complete,
        runtime_envelope.resource_cleanup_complete,
    )


def _derive_runtime_marker_id_from_snapshot_v2(
    *,
    snapshot: _ValidatedRuntimeRequestV2,
    kind: str,
    domain: str,
) -> str:
    return _local_id(
        domain,
        _runtime_request_payload(
            kind=kind,
            runtime_envelope_id=snapshot.runtime_id,
            request_replay_id=snapshot.request_replay_id,
            request_id=snapshot.request_id,
            route_identity_id=snapshot.route_identity_id,
        ),
    )


def _derive_terminal_closure_id_from_snapshot_v2(
    snapshot: _ValidatedRuntimeRequestV2,
) -> str:
    payload = {
        **_runtime_request_payload(
            kind="terminal_closure",
            runtime_envelope_id=snapshot.runtime_id,
            request_replay_id=snapshot.request_replay_id,
            request_id=snapshot.request_id,
            route_identity_id=snapshot.route_identity_id,
        ),
        "outer_attempt_broker_ipc_transcript_id": snapshot.broker_transcript_id,
        "authenticated_frame_observation_ids": list(snapshot.frame_observation_ids),
        "operational_output_id": snapshot.operational_output_id,
        "direct_children_reaped": True,
        "cgroup_cleanup_complete": snapshot.cgroup_cleanup_complete,
        "resource_cleanup_complete": snapshot.resource_cleanup_complete,
    }
    return _local_id(TERMINAL_CLOSURE_V2_DOMAIN, payload)


def derive_k7_production_measurement_start_id_v2(
    *,
    runtime_envelope: runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2,
    request_replay: request_replay_v1.V075K7SuccessorPortableRequestReplayV1,
) -> str:
    snapshot = _validate_runtime_request(
        runtime_envelope=runtime_envelope,
        request_replay=request_replay,
    )
    return _derive_runtime_marker_id_from_snapshot_v2(
        snapshot=snapshot,
        kind="measurement_start",
        domain=MEASUREMENT_START_V2_DOMAIN,
    )


def derive_k7_production_measurement_cutoff_id_v2(
    *,
    runtime_envelope: runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2,
    request_replay: request_replay_v1.V075K7SuccessorPortableRequestReplayV1,
) -> str:
    snapshot = _validate_runtime_request(
        runtime_envelope=runtime_envelope,
        request_replay=request_replay,
    )
    return _derive_runtime_marker_id_from_snapshot_v2(
        snapshot=snapshot,
        kind="measurement_cutoff",
        domain=MEASUREMENT_CUTOFF_V2_DOMAIN,
    )


def derive_k7_production_terminal_closure_id_v2(
    *,
    runtime_envelope: runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2,
    request_replay: request_replay_v1.V075K7SuccessorPortableRequestReplayV1,
) -> str:
    snapshot = _validate_runtime_request(
        runtime_envelope=runtime_envelope,
        request_replay=request_replay,
    )
    return _derive_terminal_closure_id_from_snapshot_v2(snapshot)


@dataclass(frozen=True, slots=True)
class K7SourceLocalReplayRowV2:
    path: str
    path_authorization_id: str
    semantic_verifier_id: str
    source_operational_cutoff_id: str
    source_local_start_sequence: int
    source_local_cutoff_sequence: int
    source_artifact_ids: tuple[str, ...]
    source_bytes_sha256: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.path not in resolution_v2.SHARED_RESOURCE_PATHS:
            _fail("source-local replay row names an unknown path")
        for value, label in (
            (self.path_authorization_id, "path authorization"),
            (self.semantic_verifier_id, "semantic verifier"),
            (self.source_operational_cutoff_id, "source operational cutoff"),
            *((value, "source artifact") for value in self.source_artifact_ids),
        ):
            _cid(value, label)
        _nonnegative(self.source_local_start_sequence, "source local start")
        _nonnegative(self.source_local_cutoff_sequence, "source local cutoff")
        if self.source_local_cutoff_sequence < self.source_local_start_sequence:
            _fail("source-local cutoff precedes its start")
        if (
            type(self.source_artifact_ids) is not tuple
            or not self.source_artifact_ids
            or type(self.source_bytes_sha256) is not tuple
            or len(self.source_bytes_sha256) != len(self.source_artifact_ids)
            or any(
                type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
                for value in self.source_bytes_sha256
            )
        ):
            _fail("source-local replay row has incomplete source bytes")

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "path_authorization_id": self.path_authorization_id,
            "semantic_verifier_id": self.semantic_verifier_id,
            "source_operational_cutoff_id": self.source_operational_cutoff_id,
            "source_local_start_sequence": self.source_local_start_sequence,
            "source_local_cutoff_sequence": self.source_local_cutoff_sequence,
            "source_artifact_ids": list(self.source_artifact_ids),
            "source_bytes_sha256": list(self.source_bytes_sha256),
            "source_event_bytes_independently_replayed": True,
            "source_local_closed_interval_verified": True,
        }


@dataclass(frozen=True, slots=True)
class K7PostCutoffTailRowV2:
    tail_kind: str
    marker_sequence: int
    component_key: str
    source_schema_id: str
    source_artifact_id: str
    source_bytes_sha256: str
    source_byte_count: int

    def __post_init__(self) -> None:
        if self.tail_kind not in {"ACCOUNTING_TAIL", "PROVENANCE_TAIL"}:
            _fail("post-cutoff tail kind is invalid")
        _nonnegative(self.marker_sequence, "tail marker sequence")
        _cid(self.source_artifact_id, "tail source artifact")
        if (
            type(self.component_key) is not str
            or not self.component_key
            or type(self.source_schema_id) is not str
            or not self.source_schema_id
            or type(self.source_bytes_sha256) is not str
            or len(self.source_bytes_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.source_bytes_sha256
            )
        ):
            _fail("post-cutoff tail component metadata is invalid")
        _nonnegative(self.source_byte_count, "tail source byte count")
        if self.source_byte_count <= 0:
            _fail("post-cutoff tail component must retain nonempty bytes")

    def to_document(self) -> dict[str, Any]:
        return {
            "tail_kind": self.tail_kind,
            "marker_sequence": self.marker_sequence,
            "component_key": self.component_key,
            "source_schema_id": self.source_schema_id,
            "source_artifact_id": self.source_artifact_id,
            "source_bytes_sha256": self.source_bytes_sha256,
            "source_byte_count": self.source_byte_count,
            "excluded_from_io_output_bytes": True,
        }


@dataclass(frozen=True, slots=True)
class K7OccurrenceIdentitySemanticAuthorityV2:
    _issuer: InitVar[object]
    structural_identity_join_id: str
    owned_partial_result_id: str
    partial_native_transcript_id: str
    transcript_terminal_id: str
    transcript_document_sha256: str
    ordered_chain_node_ids: tuple[str, ...]
    portable_request_replay_id: str
    request_id: str
    route_identity_id: str
    production_runtime_envelope_id: str
    source_v3_envelope_id: str
    verified_nine_source_envelope_id: str
    owner_event_candidate_set_id: str
    owner_event_execution_binding_id: str
    production_role_manifest_id: str
    source_snapshot_id: str
    source_archive_sha256: str
    source_archive_byte_count: int
    scientific_occurrence_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    execution_profile_id: str
    schedule_id: str
    terminal_status: str
    terminal_kind: str
    route_attempt_outcome: str
    route_attempt_count: int
    route_success_count: int
    route_failure_count: int
    terminal_closure_observation_id: str
    runtime_business_result_id: str
    runtime_business_result_sha256: str
    runtime_business_result_byte_count: int
    operational_output_sha256: str
    _authority_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _OCCURRENCE_ISSUER:
            _fail("occurrence semantic authority is caller-minted")
        for value, label in (
            (self.structural_identity_join_id, "structural identity join"),
            (self.owned_partial_result_id, "owned partial result"),
            (self.partial_native_transcript_id, "partial transcript"),
            (self.transcript_terminal_id, "transcript terminal"),
            (self.portable_request_replay_id, "portable request replay"),
            (self.request_id, "request"),
            (self.route_identity_id, "route identity"),
            (self.production_runtime_envelope_id, "production runtime"),
            (self.source_v3_envelope_id, "source V3 envelope"),
            (self.verified_nine_source_envelope_id, "verified nine-source envelope"),
            (self.owner_event_candidate_set_id, "owner event candidate set"),
            (self.owner_event_execution_binding_id, "owner event execution binding"),
            (self.production_role_manifest_id, "production role manifest"),
            (self.source_snapshot_id, "source snapshot"),
            (self.scientific_occurrence_id, "scientific occurrence"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.decision_point_id, "decision point"),
            (self.measurement_window_id, "measurement window"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.boundary_profile_id, "boundary profile"),
            (self.execution_profile_id, "execution profile"),
            (self.schedule_id, "schedule"),
            (self.terminal_closure_observation_id, "terminal closure"),
            (self.runtime_business_result_id, "runtime business result"),
        ):
            _cid(value, label)
        if (
            type(self.transcript_document_sha256) is not str
            or len(self.transcript_document_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.transcript_document_sha256
            )
            or type(self.ordered_chain_node_ids) is not tuple
            or not self.ordered_chain_node_ids
        ):
            _fail("occurrence authority lacks the exact owner transcript bytes/order")
        for value, label in (
            (self.runtime_business_result_sha256, "runtime business-result digest"),
            (self.operational_output_sha256, "operational-output digest"),
        ):
            if (
                type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                _fail(f"{label} is invalid")
        _nonnegative(self.runtime_business_result_byte_count, "runtime business-result bytes")
        _nonnegative(self.source_archive_byte_count, "source archive bytes")
        for value, label in (
            (self.route_attempt_count, "route attempt count"),
            (self.route_success_count, "route success count"),
            (self.route_failure_count, "route failure count"),
        ):
            _nonnegative(value, label)
        for value, label in (
            (self.source_archive_sha256, "source-archive digest"),
        ):
            if (
                type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                _fail(f"{label} is invalid")
        if (
            self.runtime_business_result_byte_count <= 0
            or self.source_archive_byte_count <= 0
            or self.terminal_status != "CHILD_ACTION_ROW_CAP_EXCEEDED"
            or self.terminal_kind != "COMPLETED"
            or self.route_attempt_outcome != "FAILURE"
            or self.route_attempt_count != 1
            or self.route_success_count != 0
            or self.route_failure_count != 1
            or self.route_attempt_count
            != self.route_success_count + self.route_failure_count
        ):
            _fail("registered terminal/route outcome or source sizes changed")
        for value in self.ordered_chain_node_ids:
            _cid(value, "ordered chain node")
        object.__setattr__(
            self,
            "_authority_id",
            _local_id(OCCURRENCE_AUTHORITY_V2_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_occurrence_identity_semantic_authority.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "structural_identity_join_id": self.structural_identity_join_id,
            "owned_partial_result_id": self.owned_partial_result_id,
            "partial_native_transcript_id": self.partial_native_transcript_id,
            "transcript_terminal_id": self.transcript_terminal_id,
            "transcript_document_sha256": self.transcript_document_sha256,
            "ordered_chain_node_ids": list(self.ordered_chain_node_ids),
            "portable_request_replay_id": self.portable_request_replay_id,
            "request_id": self.request_id,
            "route_identity_id": self.route_identity_id,
            "production_runtime_envelope_id": self.production_runtime_envelope_id,
            "source_v3_envelope_id": self.source_v3_envelope_id,
            "verified_nine_source_envelope_id": (
                self.verified_nine_source_envelope_id
            ),
            "owner_event_candidate_set_id": self.owner_event_candidate_set_id,
            "owner_event_execution_binding_id": (
                self.owner_event_execution_binding_id
            ),
            "production_role_manifest_id": self.production_role_manifest_id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_archive_sha256": self.source_archive_sha256,
            "source_archive_byte_count": self.source_archive_byte_count,
            "scientific_occurrence_id": self.scientific_occurrence_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "measurement_window_id": self.measurement_window_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "execution_profile_id": self.execution_profile_id,
            "schedule_id": self.schedule_id,
            "terminal_status": self.terminal_status,
            "terminal_kind": self.terminal_kind,
            "route_attempt_outcome": self.route_attempt_outcome,
            "route_attempt_count": self.route_attempt_count,
            "route_success_count": self.route_success_count,
            "route_failure_count": self.route_failure_count,
            "terminal_closure_observation_id": self.terminal_closure_observation_id,
            "runtime_business_result_id": self.runtime_business_result_id,
            "runtime_business_result_sha256": self.runtime_business_result_sha256,
            "runtime_business_result_byte_count": self.runtime_business_result_byte_count,
            "operational_output_sha256": self.operational_output_sha256,
            "scientific_to_logical_occurrence_mapping_replayed": True,
            "route_graph_identity_replayed": True,
            "production_runtime_request_binding_replayed": True,
            "owner_partial_transcript_chain_semantics_replayed": True,
            "owner_partial_transcript_exact_bytes_and_order_bound": True,
            "owner_event_candidate_semantic_authority_verified": True,
            "owner_event_source_archive_and_manifest_bound": True,
            "runtime_embedded_business_result_bytes_replayed": True,
            "runtime_embedded_owned_result_exact_document_equal": True,
            "runtime_embedded_partial_transcript_exact_document_equal": True,
            "real_production_runtime_envelope_required": True,
            "real_production_runtime_envelope_verified": True,
            "positive_semantic_identity_authority": True,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vector_authorized": False,
            "central_domain_registration_complete": True,
        }

    @property
    def authority_id(self) -> str:
        if _local_id(OCCURRENCE_AUTHORITY_V2_DOMAIN, self._payload()) != self._authority_id:
            _fail("occurrence semantic authority changed after issuance")
        return self._authority_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_identity_semantic_authority_id": self.authority_id}


@dataclass(frozen=True, slots=True)
class K7OperationalCutoffSemanticAuthorityV2:
    _issuer: InitVar[object]
    occurrence_authority_id: str
    structural_cutoff_attestation_id: str
    measurement_start_marker_id: str
    measurement_cutoff_marker_id: str
    measurement_window_id: str
    terminal_closure_observation_id: str
    global_start_sequence: int
    global_terminal_sequence: int
    global_cutoff_sequence: int
    source_rows: tuple[K7SourceLocalReplayRowV2, ...]
    tail_rows: tuple[K7PostCutoffTailRowV2, ...]
    charged_output_bytes: int
    tail_component_bytes_excluded: int
    durable_output_event_ids: tuple[str, ...]
    _authority_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CUTOFF_ISSUER:
            _fail("operational cutoff semantic authority is caller-minted")
        for value, label in (
            (self.occurrence_authority_id, "occurrence authority"),
            (self.structural_cutoff_attestation_id, "structural cutoff"),
            (self.measurement_start_marker_id, "measurement start"),
            (self.measurement_cutoff_marker_id, "measurement cutoff"),
            (self.measurement_window_id, "measurement window"),
            (self.terminal_closure_observation_id, "terminal closure"),
            *((value, "durable output event") for value in self.durable_output_event_ids),
        ):
            _cid(value, label)
        for value, label in (
            (self.global_start_sequence, "global start sequence"),
            (self.global_terminal_sequence, "global terminal sequence"),
            (self.global_cutoff_sequence, "global cutoff sequence"),
            (self.charged_output_bytes, "charged output bytes"),
            (self.tail_component_bytes_excluded, "excluded tail bytes"),
        ):
            _nonnegative(value, label)
        if (
            self.global_start_sequence != GLOBAL_START_SEQUENCE
            or self.global_terminal_sequence != GLOBAL_TERMINAL_SEQUENCE
            or self.global_cutoff_sequence != GLOBAL_CUTOFF_SEQUENCE
            or type(self.source_rows) is not tuple
            or tuple(row.path for row in self.source_rows)
            != resolution_v2.SHARED_RESOURCE_PATHS
            or any(type(row) is not K7SourceLocalReplayRowV2 for row in self.source_rows)
            or len({row.path_authorization_id for row in self.source_rows})
            != len(resolution_v2.SHARED_RESOURCE_PATHS)
            or type(self.tail_rows) is not tuple
            or len(self.tail_rows) != 4
            or any(type(row) is not K7PostCutoffTailRowV2 for row in self.tail_rows)
            or tuple(row.marker_sequence for row in self.tail_rows)
            != tuple(range(GLOBAL_CUTOFF_SEQUENCE + 1, GLOBAL_CUTOFF_SEQUENCE + 5))
            or tuple(row.tail_kind for row in self.tail_rows)
            != (
                "ACCOUNTING_TAIL",
                "ACCOUNTING_TAIL",
                "PROVENANCE_TAIL",
                "PROVENANCE_TAIL",
            )
            or self.charged_output_bytes <= 0
            or self.tail_component_bytes_excluded <= 0
            or type(self.durable_output_event_ids) is not tuple
            or len(self.durable_output_event_ids) != len(output_v2.ROLE_ORDER)
            or len(set(self.durable_output_event_ids)) != len(self.durable_output_event_ids)
            or set(self.durable_output_event_ids)
            & {row.source_artifact_id for row in self.tail_rows}
        ):
            _fail("operational cutoff authority is incomplete or crossed")
        object.__setattr__(
            self,
            "_authority_id",
            _local_id(CUTOFF_AUTHORITY_V2_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_operational_cutoff_semantic_authority.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_identity_semantic_authority_id": self.occurrence_authority_id,
            "structural_cutoff_attestation_id": self.structural_cutoff_attestation_id,
            "measurement_start_marker_id": self.measurement_start_marker_id,
            "measurement_cutoff_marker_id": self.measurement_cutoff_marker_id,
            "measurement_window_id": self.measurement_window_id,
            "terminal_closure_observation_id": self.terminal_closure_observation_id,
            "global_start_sequence": self.global_start_sequence,
            "global_terminal_sequence": self.global_terminal_sequence,
            "global_cutoff_sequence": self.global_cutoff_sequence,
            "global_sequence_semantics": "SOURCE_CLOSURE_INDEX_NOT_LOCAL_EVENT_RENUMBERING",
            "source_local_replays": [row.to_document() for row in self.source_rows],
            "post_cutoff_tail_components": [row.to_document() for row in self.tail_rows],
            "charged_output_bytes": self.charged_output_bytes,
            "tail_component_bytes_excluded": self.tail_component_bytes_excluded,
            "durable_output_event_ids": list(self.durable_output_event_ids),
            "exact_source_sequences_independently_replayed": True,
            "post_cutoff_business_work_absence_verified": True,
            "post_cutoff_tail_output_byte_exclusion_verified": True,
            "production_output_first_role_verified": True,
            "positive_semantic_cutoff_authority": True,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vector_authorized": False,
            "central_domain_registration_complete": True,
        }

    @property
    def authority_id(self) -> str:
        if _local_id(CUTOFF_AUTHORITY_V2_DOMAIN, self._payload()) != self._authority_id:
            _fail("operational cutoff authority changed after issuance")
        return self._authority_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operational_cutoff_semantic_authority_id": self.authority_id}


@dataclass(frozen=True, slots=True)
class K7OccurrenceCutoffSemanticAuthorityBundleV2:
    _issuer: InitVar[object]
    occurrence_authority: K7OccurrenceIdentitySemanticAuthorityV2
    cutoff_authority: K7OperationalCutoffSemanticAuthorityV2
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BUNDLE_ISSUER
            or type(self.occurrence_authority)
            is not K7OccurrenceIdentitySemanticAuthorityV2
            or type(self.cutoff_authority)
            is not K7OperationalCutoffSemanticAuthorityV2
            or self.cutoff_authority.occurrence_authority_id
            != self.occurrence_authority.authority_id
        ):
            _fail("occurrence/cutoff authority bundle is caller-minted or crossed")
        object.__setattr__(
            self,
            "_bundle_id",
            _local_id(AUTHORITY_BUNDLE_V2_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_occurrence_cutoff_semantic_authority_bundle.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_identity_semantic_authority_id": (
                self.occurrence_authority.authority_id
            ),
            "operational_cutoff_semantic_authority_id": (
                self.cutoff_authority.authority_id
            ),
            "positive_semantic_authorities_issued": True,
            "eligible_for_202_path_atomic_materializer_prerequisite": True,
            "counter_records_issued": False,
            "formal_vector_authorized": False,
            "real_production_runtime_envelope_required": True,
            "central_domain_registration_complete": True,
        }

    @property
    def bundle_id(self) -> str:
        if _local_id(AUTHORITY_BUNDLE_V2_DOMAIN, self._payload()) != self._bundle_id:
            _fail("occurrence/cutoff authority bundle changed after issuance")
        return self._bundle_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_cutoff_semantic_authority_bundle_id": self.bundle_id}


@dataclass(frozen=True, slots=True)
class _ValidatedPositiveContextV2:
    runtime_id: str
    request_replay_id: str
    source_envelope_id: str
    verified_envelope_id: str
    terminal_closure_id: str
    start_marker_id: str
    cutoff_marker_id: str
    source_rows: tuple[K7SourceLocalReplayRowV2, ...]
    tail_rows: tuple[K7PostCutoffTailRowV2, ...]
    charged_output_bytes: int
    durable_output_event_ids: tuple[str, ...]
    runtime_business_result_id: str
    runtime_business_result_sha256: str
    runtime_business_result_byte_count: int
    operational_output_sha256: str
    owner_event_candidate_set_id: str
    owner_event_execution_binding_id: str
    production_role_manifest_id: str
    source_snapshot_id: str
    source_archive_sha256: str
    source_archive_byte_count: int


def _validate_runtime_business_join(
    *,
    runtime_envelope: runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2,
    request_replay: request_replay_v1.V075K7SuccessorPortableRequestReplayV1,
    owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
    operational_output_bytes: Any,
) -> tuple[
    str,
    str,
    int,
    str,
    bytes,
    child_bundle_v1.V075K7ChildBusinessBundleV1,
]:
    if type(operational_output_bytes) is not bytes or not operational_output_bytes:
        _fail("positive authority requires independently held operational-output bytes")
    try:
        # One complete private validator call already authenticates the outer
        # document and performs the nested business-bundle replay.  Retain its
        # immutable primitive facts in this frame instead of constructing a
        # public wrapper and then triggering the same full replay again from
        # ``to_document`` and ``output_id``.
        output_frame = worker_v1._validate_output_document_for_issuance_v1(  # noqa: SLF001
            operational_output_bytes,
            expected_request_replay=request_replay,
            expected_binding=runtime_envelope.binding,
        )
        output_document = loads_canonical_json(operational_output_bytes)
        if type(output_document) is not dict:  # full validator proves this
            _fail("runtime operational output is not one canonical object")
        business_document = output_document["business_result"]
        business_raw = canonical_json_bytes(business_document)
        output_id, validated_output_sha, business_id = output_frame.output_facts
        verified_business_bundle = output_frame.verified_business_bundle
    except Exception as error:
        raise ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error(
            "runtime operational output or embedded business result failed public replay"
        ) from error
    business_sha = hashlib.sha256(business_raw).hexdigest()
    output_sha = hashlib.sha256(operational_output_bytes).hexdigest()
    if (
        output_id != runtime_envelope.operational_output_id
        or validated_output_sha != output_sha
        or output_frame.business_raw != business_raw
        or output_frame.request_object_id != id(request_replay)
        or output_frame.binding_object_id != id(runtime_envelope.binding)
        or output_sha != runtime_envelope.output_sha256
        or len(operational_output_bytes) != runtime_envelope.output_byte_count
        or business_id != runtime_envelope.business_result_id
        or business_sha != runtime_envelope.business_result_sha256
        or len(business_raw) != runtime_envelope.business_result_byte_count
        or output_document.get("business_result_id") != business_id
        or output_document.get("business_result_sha256") != business_sha
        or output_document.get("business_result_byte_count") != len(business_raw)
        or business_document.get("owned_partial_result_id") != owned_result.wrapper_id
        or business_document.get("owned_partial_result") != owned_result.to_document()
        or business_document.get("partial_native_transcript_id")
        != owned_result.transcript.transcript_id
        or business_document.get("partial_native_transcript")
        != owned_result.transcript.to_document()
        or business_document["owned_partial_result"].get("terminal_status")
        != "CHILD_ACTION_ROW_CAP_EXCEEDED"
        or business_document["partial_native_transcript"].get("terminal_kind")
        != "COMPLETED"
    ):
        _fail("runtime business bytes do not contain the exact owner result/transcript")
    return (
        business_id,
        business_sha,
        len(business_raw),
        output_sha,
        business_raw,
        verified_business_bundle,
    )


def _validate_owner_event_authority(
    *,
    owner_event_candidates: Any,
    role_manifest: Any,
    runtime_envelope: runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2,
    request_replay: request_replay_v1.V075K7SuccessorPortableRequestReplayV1,
    owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
    runtime_business_result_id: str,
    business_bundle_raw: bytes,
    verified_business_bundle: child_bundle_v1.V075K7ChildBusinessBundleV1,
) -> tuple[str, str, str, str, str, int]:
    """Bind the independently derived 71-path owner semantic authority.

    The candidate set is issuer-owned and was constructed from the immutable
    production source archive plus the exact business-result transcript.  This
    layer does not weakly reinterpret those event nodes; it verifies the typed
    authority and joins every execution identity to the raw runtime/business
    replay performed above.
    """

    if type(owner_event_candidates) is not owner_events_v1.OwnerEventCandidateSetV1:
        _fail("positive authority requires one exact owner event candidate set")
    if type(role_manifest) is not role_manifest_v2.K7ProductionRoleManifestV2:
        _fail("positive authority requires one exact production role manifest")
    try:
        expected_candidates = (
            owner_events_v1._derive_v075_k7_owner_event_candidates_from_verified_bundle_v1(  # noqa: SLF001
                role_manifest=role_manifest,
                runtime_envelope=runtime_envelope,
                request_replay=request_replay,
                verified_business_bundle=verified_business_bundle,
            )
        )
        candidate_document = (
            owner_events_v1._verify_owner_event_candidate_set_document_v1(  # noqa: SLF001
                owner_event_candidates
            )
        )
        expected_document = expected_candidates.to_document()
        expected_binding_document = (
            expected_candidates.execution_binding.to_document()
        )
        binding = owner_event_candidates.execution_binding
        binding_document = binding.to_document()
    except Exception as error:
        raise ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error(
            "owner event candidate semantic authority failed replay"
        ) from error
    request = request_replay.request
    route = request.route_identity
    transcript = owned_result.transcript
    transport = request.profile.accounted_profile.transport_profile
    if (
        expected_document["owner_event_candidate_set_id"]
        != candidate_document["owner_event_candidate_set_id"]
        or expected_document != candidate_document
        or expected_binding_document != binding_document
        or role_manifest.request_id != request.request_id
        or role_manifest.route_identity_id != route.route_identity_id
        or role_manifest.request.canonical_bytes != request.canonical_bytes
        or role_manifest.source_snapshot_id != transport.source_snapshot_id
        or role_manifest.source_archive_sha256 != transport.source_archive_sha256
        or role_manifest.source_archive_byte_count != transport.source_archive_byte_count
        or owner_event_candidates.partial_native_transcript_id
        != transcript.transcript_id
        or owner_event_candidates.partial_native_terminal_id
        != transcript.nodes[-1].chain_id
        or owner_event_candidates.partial_native_terminal_id
        != candidate_document["partial_native_terminal_id"]
        or binding.request_id != request.request_id
        or binding.route_identity_id != route.route_identity_id
        or binding.scientific_occurrence_id != request.scientific_occurrence_id
        or binding.scientific_occurrence_id != transcript.start.occurrence_id
        or binding.phase3e_logical_occurrence_id
        != request.occurrence_mapping.phase3e_logical_occurrence_id
        or binding.production_role_manifest_id != runtime_envelope.manifest_id
        or binding.production_runtime_envelope_id != runtime_envelope.envelope_id
        or binding.broker_transcript_id != runtime_envelope.transcript.transcript_id
        or binding.business_bundle_id != runtime_business_result_id
        or binding.business_bundle_id != runtime_envelope.business_result_id
        or any(
            row.execution_binding_id != binding.binding_id
            or row.partial_native_transcript_id != transcript.transcript_id
            for row in owner_event_candidates.site_closures
        )
        or any(
            row.execution_binding_id != binding.binding_id
            or row.partial_native_transcript_id != transcript.transcript_id
            for row in owner_event_candidates.path_candidates
        )
        or binding_document["source_snapshot_id"] != binding.source_snapshot_id
        or binding_document["source_archive_sha256"]
        != binding.source_archive_sha256
        or binding_document["source_archive_byte_count"]
        != binding.source_archive_byte_count
    ):
        _fail("owner event candidate set crossed transcript/runtime/business/source identity")
    return (
        candidate_document["owner_event_candidate_set_id"],
        binding_document["owner_event_execution_binding_id"],
        binding.production_role_manifest_id,
        binding.source_snapshot_id,
        binding.source_archive_sha256,
        binding.source_archive_byte_count,
    )


def _tail_components(
    bundle: output_v2.OutputRawEvidenceBundleV2,
) -> tuple[tuple[str, Any], ...]:
    return (
        ("ACCOUNTING_TAIL", bundle.fixed_point_component),
        ("ACCOUNTING_TAIL", bundle.cutoff_component),
        ("PROVENANCE_TAIL", bundle.exclusive_writer_component),
        ("PROVENANCE_TAIL", bundle.output_manifest_component),
    )


def _validate_output_source(
    *,
    runtime_envelope: runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2,
    source_envelope: live_v3.K7ProductionSharedResourceEnvelopeV3,
    output_authorization: (
        verified_v1.K7ValidatedSharedResourcePathSnapshotV1 | None
    ),
    output_bundle: Any,
) -> tuple[
    tuple[K7PostCutoffTailRowV2, ...],
    int,
    tuple[str, ...],
]:
    if type(output_bundle) is not output_v2.OutputRawEvidenceBundleV2:
        _fail("cutoff authority requires one exact production output evidence bundle")
    components = (
        output_bundle.fixed_point_component,
        output_bundle.exclusive_writer_component,
        output_bundle.cutoff_component,
        output_bundle.output_manifest_component,
    )
    try:
        replay = output_v2.replay_production_output_exact_semantic_evidence_v2(
            fixed_point_bytes=components[0].raw_bytes,
            exclusive_writer_bytes=components[1].raw_bytes,
            cutoff_bytes=components[2].raw_bytes,
            output_manifest_bytes=components[3].raw_bytes,
        )
        live_source = output_bundle.live_source_v2()
    except Exception as error:
        raise ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error(
            "production output source bytes failed independent replay"
        ) from error
    if output_authorization is None:
        _fail("verified nine-source envelope lacks io.output_bytes")
    live_source_component_bytes = tuple(
        canonical_json_bytes(component.to_internal_document())
        for component in live_source.components
    )
    if (
        replay.live_envelope_id != runtime_envelope.envelope_id
        or replay.live_envelope_id != source_envelope.production_runtime_envelope_id
        or replay.occurrence_id != source_envelope.occurrence_id
        or replay.route_attempt_id != source_envelope.route_attempt_id
        or replay.decision_point_id != source_envelope.decision_point_id
        or replay.measurement_window_id != source_envelope.measurement_window_id
        or replay.operational_cutoff_id
        != output_authorization.source_operational_cutoff_id
        or output_authorization.path != output_v2.OUTPUT_PATH
        or live_source.path != output_v2.OUTPUT_PATH
        or live_source_component_bytes
        != output_authorization.source_component_canonical_bytes
        or output_authorization.exact_value != replay.raw_output_bytes
    ):
        _fail("production output bundle was transplanted across runtime/source context")
    manifest = _canonical_object(
        output_bundle.output_manifest_component.raw_bytes,
        "independently held output manifest",
    )
    writer = _canonical_object(
        output_bundle.exclusive_writer_component.raw_bytes,
        "independently held exclusive-writer evidence",
    )
    role_rows = manifest.get("role_artifacts")
    writer_rows = writer.get("durable_write_events")
    if (
        type(role_rows) is not list
        or type(writer_rows) is not list
        or role_rows != writer_rows
        or [row.get("artifact_role") for row in role_rows]
        != list(output_v2.ROLE_ORDER)
    ):
        _fail("output durable source events are missing, reordered, or crossed")
    durable_ids = tuple(
        _cid(row.get("durable_write_event_id"), "durable output event")
        for row in role_rows
    )
    first = role_rows[0]
    parent_output = runtime_envelope.frame_observations[3]
    if (
        first.get("broker_operational_output_id")
        != runtime_envelope.operational_output_id
        or first.get("artifact_sha256") != runtime_envelope.output_sha256
        or first.get("artifact_byte_extent") != runtime_envelope.output_byte_count
        or first.get("authenticated_parent_output_observation_id")
        != parent_output.observation_id
        or first.get("parent_output_frame_id") != parent_output.frame.frame_id
        or parent_output.frame.payload.get("output_sha256")
        != runtime_envelope.output_sha256
        or parent_output.frame.payload.get("output_byte_count")
        != runtime_envelope.output_byte_count
    ):
        _fail("production output first role crossed its runtime PARENT_OUTPUT authority")
    tail_rows = tuple(
        K7PostCutoffTailRowV2(
            tail_kind=kind,
            marker_sequence=GLOBAL_CUTOFF_SEQUENCE + index,
            component_key=component.component_key,
            source_schema_id=component.source_schema_id,
            source_artifact_id=component.source_artifact_id,
            source_bytes_sha256=component.source_bytes_sha256,
            source_byte_count=len(component.raw_bytes),
        )
        for index, (kind, component) in enumerate(
            _tail_components(output_bundle), start=1
        )
    )
    if set(durable_ids) & {row.source_artifact_id for row in tail_rows}:
        _fail("post-cutoff evidence tail was charged as a durable output event")
    if sum(row.get("artifact_byte_extent", -1) for row in role_rows) != replay.raw_output_bytes:
        _fail("durable output total includes or omits non-role bytes")
    return tail_rows, replay.raw_output_bytes, durable_ids


def _validate_positive_context_once_v2(
    *,
    identity_join: join_v1.ConstructionOccurrenceIdentityJoinV1,
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
    runtime_envelope: runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2,
    request_replay: request_replay_v1.V075K7SuccessorPortableRequestReplayV1,
    source_envelope: live_v3.K7ProductionSharedResourceEnvelopeV3,
    verified_envelope: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    output_bundle: output_v2.OutputRawEvidenceBundleV2,
    owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
    operational_output_bytes: bytes,
    owner_event_candidates: owner_events_v1.OwnerEventCandidateSetV1,
    role_manifest: role_manifest_v2.K7ProductionRoleManifestV2,
) -> _ValidatedPositiveContextV2:
    if (
        type(identity_join) is not join_v1.ConstructionOccurrenceIdentityJoinV1
        or type(receipt_set) is not receipts_v1.SharedResourceReceiptSetV1
    ):
        _fail("positive context requires the exact historical structural roots")
    runtime_snapshot = _validate_runtime_request(
        runtime_envelope=runtime_envelope,
        request_replay=request_replay,
    )
    runtime_id = runtime_snapshot.runtime_id
    replay_id = runtime_snapshot.request_replay_id
    if type(source_envelope) is not live_v3.K7ProductionSharedResourceEnvelopeV3:
        _fail("positive context requires one exact V3 nine-source envelope")
    if (
        type(verified_envelope)
        is not verified_v1.K7VerifiedNineSharedResourceEnvelopeV1
    ):
        _fail("positive context requires one exact verified nine-source envelope")
    try:
        nine_source_snapshot = (
            verified_v1.validate_k7_verified_nine_shared_resource_pair_once_v1(
                source_envelope=source_envelope,
                supplied_verified_envelope=verified_envelope,
            )
        )
    except Exception as error:
        raise ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error(
            "nine source-local event streams failed independent replay"
        ) from error
    source_envelope_id = nine_source_snapshot.source_v3_envelope_id
    output_authorization = next(
        (
            row
            for row in nine_source_snapshot.supplied_authorizations
            if row.path == output_v2.OUTPUT_PATH
        ),
        None,
    )
    if output_authorization is None:
        _fail("verified nine-source envelope lacks io.output_bytes")
    request = request_replay.request
    route = request.route_identity
    logical_occurrence_id = route.logical_occurrence.logical_occurrence_id
    route_attempt_id = route.route_attempt.route_attempt_id
    decision_point_id = route.decision_point.decision_point_id
    expected_terminal = _derive_terminal_closure_id_from_snapshot_v2(
        runtime_snapshot
    )
    expected_start = _derive_runtime_marker_id_from_snapshot_v2(
        snapshot=runtime_snapshot,
        kind="measurement_start",
        domain=MEASUREMENT_START_V2_DOMAIN,
    )
    expected_cutoff = _derive_runtime_marker_id_from_snapshot_v2(
        snapshot=runtime_snapshot,
        kind="measurement_cutoff",
        domain=MEASUREMENT_CUTOFF_V2_DOMAIN,
    )
    route_profile = route.profile
    window = receipt_set.window
    if (
        identity_join.occurrence_id != request.scientific_occurrence_id
        or identity_join.route_attempt_id != route_attempt_id
        or identity_join.decision_point_id != decision_point_id
        or identity_join.counter_registry_id != route_profile.counter_registry_id
        or identity_join.stage_profile_id != route_profile.stage_profile_id
        or identity_join.boundary_profile_id != route_profile.boundary_manifest_id
        or identity_join.execution_profile_id != route_profile.execution_profile_id
        or identity_join.shared_resource_measurement_window_id != window.window_id
        or source_envelope.production_runtime_envelope_id != runtime_id
        or source_envelope.counter_registry_id != identity_join.counter_registry_id
        or source_envelope.stage_profile_id != identity_join.stage_profile_id
        or source_envelope.occurrence_id != logical_occurrence_id
        or source_envelope.route_attempt_id != route_attempt_id
        or source_envelope.decision_point_id != decision_point_id
        or source_envelope.measurement_window_id != window.window_id
        or source_envelope.production_runtime_replay_id != replay_id
        or source_envelope.terminal_closure_observation_id != expected_terminal
        or window.start_marker_id != expected_start
        or window.cutoff_marker_id != expected_cutoff
        or window.start_sequence != GLOBAL_START_SEQUENCE
        or window.cutoff_sequence != GLOBAL_CUTOFF_SEQUENCE
        or window.state is not receipts_v1.MeasurementWindowStateV1.CLOSED
    ):
        _fail("scientific/logical occurrence, route, window, or runtime identity is stale")
    source_rows = tuple(
        K7SourceLocalReplayRowV2(
            path=row.path,
            path_authorization_id=row.authorization_id,
            semantic_verifier_id=row.semantic_verifier_id,
            source_operational_cutoff_id=row.source_operational_cutoff_id,
            source_local_start_sequence=row.source_local_start_sequence,
            source_local_cutoff_sequence=row.source_local_cutoff_sequence,
            source_artifact_ids=row.source_artifact_ids,
            source_bytes_sha256=row.source_bytes_sha256,
        )
        for row in nine_source_snapshot.supplied_authorizations
    )
    tail_rows, charged_output, durable_ids = _validate_output_source(
        runtime_envelope=runtime_envelope,
        source_envelope=source_envelope,
        output_authorization=output_authorization,
        output_bundle=output_bundle,
    )
    (
        business_id,
        business_sha,
        business_size,
        operational_sha,
        business_raw,
        verified_business_bundle,
    ) = (
        _validate_runtime_business_join(
            runtime_envelope=runtime_envelope,
            request_replay=request_replay,
            owned_result=owned_result,
            operational_output_bytes=operational_output_bytes,
        )
    )
    (
        owner_candidate_set_id,
        owner_execution_binding_id,
        production_role_manifest_id,
        source_snapshot_id,
        source_archive_sha256,
        source_archive_byte_count,
    ) = _validate_owner_event_authority(
        owner_event_candidates=owner_event_candidates,
        role_manifest=role_manifest,
        runtime_envelope=runtime_envelope,
        request_replay=request_replay,
        owned_result=owned_result,
        runtime_business_result_id=business_id,
        business_bundle_raw=business_raw,
        verified_business_bundle=verified_business_bundle,
    )
    return _ValidatedPositiveContextV2(
        runtime_id,
        replay_id,
        source_envelope_id,
        nine_source_snapshot.supplied_verified_envelope_id,
        expected_terminal,
        expected_start,
        expected_cutoff,
        source_rows,
        tail_rows,
        charged_output,
        durable_ids,
        business_id,
        business_sha,
        business_size,
        operational_sha,
        owner_candidate_set_id,
        owner_execution_binding_id,
        production_role_manifest_id,
        source_snapshot_id,
        source_archive_sha256,
        source_archive_byte_count,
    )


def _validate_positive_context(
    *,
    identity_join: join_v1.ConstructionOccurrenceIdentityJoinV1,
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
    runtime_envelope: runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2,
    request_replay: request_replay_v1.V075K7SuccessorPortableRequestReplayV1,
    source_envelope: live_v3.K7ProductionSharedResourceEnvelopeV3,
    verified_envelope: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    output_bundle: output_v2.OutputRawEvidenceBundleV2,
    owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
    operational_output_bytes: bytes,
    owner_event_candidates: owner_events_v1.OwnerEventCandidateSetV1,
    role_manifest: role_manifest_v2.K7ProductionRoleManifestV2,
) -> _ValidatedPositiveContextV2:
    """Replay one positive context without a cross-verifier memo scope."""

    return _validate_positive_context_once_v2(
        identity_join=identity_join,
        receipt_set=receipt_set,
        runtime_envelope=runtime_envelope,
        request_replay=request_replay,
        source_envelope=source_envelope,
        verified_envelope=verified_envelope,
        output_bundle=output_bundle,
        owned_result=owned_result,
        operational_output_bytes=operational_output_bytes,
        owner_event_candidates=owner_event_candidates,
        role_manifest=role_manifest,
    )


def _markers_from_validated_context(
    *,
    identity_join: join_v1.ConstructionOccurrenceIdentityJoinV1,
    context: _ValidatedPositiveContextV2,
) -> tuple[join_v1.OperationalSequenceMarkerV1, ...]:
    """Build structural marker rows without replaying validated inputs again."""

    rows: list[join_v1.OperationalSequenceMarkerV1] = [
        join_v1.OperationalSequenceMarkerV1(
            GLOBAL_START_SEQUENCE,
            join_v1.OperationalSequenceKindV1.WINDOW_START,
            "k7.production.measurement.start.v2",
            context.start_marker_id,
        ),
        join_v1.OperationalSequenceMarkerV1(
            GLOBAL_TERMINAL_SEQUENCE,
            join_v1.OperationalSequenceKindV1.TRANSCRIPT_TERMINAL,
            "k7.partial.transcript.terminal.v2",
            identity_join.transcript_terminal_id,
        ),
    ]
    rows.extend(
        join_v1.OperationalSequenceMarkerV1(
            GLOBAL_FIRST_SOURCE_SEQUENCE + index,
            join_v1.OperationalSequenceKindV1.BUSINESS_WORK,
            f"k7.shared_resource.{row.path}",
            row.path_authorization_id,
        )
        for index, row in enumerate(context.source_rows)
    )
    rows.append(
        join_v1.OperationalSequenceMarkerV1(
            GLOBAL_CUTOFF_SEQUENCE,
            join_v1.OperationalSequenceKindV1.OPERATIONAL_CUTOFF,
            "k7.production.measurement.cutoff.v2",
            context.cutoff_marker_id,
        )
    )
    rows.extend(
        join_v1.OperationalSequenceMarkerV1(
            row.marker_sequence,
            join_v1.OperationalSequenceKindV1(row.tail_kind),
            f"k7.output_evidence.{row.component_key}",
            row.source_artifact_id,
        )
        for row in context.tail_rows
    )
    return tuple(rows)


def expected_k7_positive_cutoff_markers_v2(
    *,
    identity_join: join_v1.ConstructionOccurrenceIdentityJoinV1,
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
    runtime_envelope: runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2,
    request_replay: request_replay_v1.V075K7SuccessorPortableRequestReplayV1,
    source_envelope: live_v3.K7ProductionSharedResourceEnvelopeV3,
    verified_envelope: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    output_bundle: output_v2.OutputRawEvidenceBundleV2,
    owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
    operational_output_bytes: bytes,
    owner_event_candidates: owner_events_v1.OwnerEventCandidateSetV1,
    role_manifest: role_manifest_v2.K7ProductionRoleManifestV2,
) -> tuple[join_v1.OperationalSequenceMarkerV1, ...]:
    """Validate once and derive the only eligible positive V2 marker sequence."""

    context = _validate_positive_context(
        identity_join=identity_join,
        receipt_set=receipt_set,
        runtime_envelope=runtime_envelope,
        request_replay=request_replay,
        source_envelope=source_envelope,
        verified_envelope=verified_envelope,
        output_bundle=output_bundle,
        owned_result=owned_result,
        operational_output_bytes=operational_output_bytes,
        owner_event_candidates=owner_event_candidates,
        role_manifest=role_manifest,
    )
    return _markers_from_validated_context(
        identity_join=identity_join,
        context=context,
    )


def _verify_structural_roots(
    *,
    identity_join: join_v1.ConstructionOccurrenceIdentityJoinV1,
    cutoff_attestation: join_v1.OperationalCutoffAttestationV1,
    owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
    evidence_closure: closure_v1.EvidenceClosureV1,
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
) -> tuple[str, tuple[str, ...]]:
    try:
        expected_join = join_v1.freeze_construction_occurrence_identity_join_v1(
            owned_result=owned_result,
            evidence_closure=evidence_closure,
            receipt_set=receipt_set,
        )
        if (
            expected_join != identity_join
            or expected_join.identity_join_id != identity_join.identity_join_id
        ):
            _fail("historical structural identity join was transplanted")
        join_v1.verify_operational_cutoff_attestation_v1(
            cutoff_attestation,
            identity_join=identity_join,
            receipt_set=receipt_set,
        )
        # Do not inherit the weaker child-business-bundle transcript check.
        # Replay the owner-held typed chain directly, including every node's
        # content identity and sequential predecessor relation, and bind its
        # exact canonical document bytes into the successor authority.
        transcript = owned_result.transcript
        partial_v1.verify_partial_native_occurrence_transcript_v1(transcript)
        transcript_raw = canonical_json_bytes(transcript.to_document())
        replayed_document = loads_canonical_json(transcript_raw)
        if (
            type(replayed_document) is not dict
            or replayed_document != transcript.to_document()
            or transcript.nodes[-1].chain_id != identity_join.transcript_terminal_id
        ):
            _fail("owner partial transcript bytes or terminal identity changed")
        return (
            hashlib.sha256(transcript_raw).hexdigest(),
            tuple(row.chain_id for row in transcript.nodes),
        )
    except ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error:
        raise
    except Exception as error:
        raise ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error(
            "historical structural join/cutoff roots failed deterministic replay"
        ) from error


def _issue_k7_occurrence_cutoff_semantic_authorities_v2(
    *,
    identity_join: join_v1.ConstructionOccurrenceIdentityJoinV1,
    cutoff_attestation: join_v1.OperationalCutoffAttestationV1,
    owned_result: owned_v1.V075K7RootCapOwnedPartialResultV1,
    evidence_closure: closure_v1.EvidenceClosureV1,
    receipt_set: receipts_v1.SharedResourceReceiptSetV1,
    runtime_envelope: runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2,
    request_replay: request_replay_v1.V075K7SuccessorPortableRequestReplayV1,
    source_envelope: live_v3.K7ProductionSharedResourceEnvelopeV3,
    verified_envelope: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    output_bundle: output_v2.OutputRawEvidenceBundleV2,
    operational_output_bytes: bytes,
    owner_event_candidates: owner_events_v1.OwnerEventCandidateSetV1,
    role_manifest: role_manifest_v2.K7ProductionRoleManifestV2,
) -> K7OccurrenceCutoffSemanticAuthorityBundleV2:
    transcript_sha256, ordered_chain_node_ids = _verify_structural_roots(
        identity_join=identity_join,
        cutoff_attestation=cutoff_attestation,
        owned_result=owned_result,
        evidence_closure=evidence_closure,
        receipt_set=receipt_set,
    )
    context = _validate_positive_context(
        identity_join=identity_join,
        receipt_set=receipt_set,
        runtime_envelope=runtime_envelope,
        request_replay=request_replay,
        source_envelope=source_envelope,
        verified_envelope=verified_envelope,
        output_bundle=output_bundle,
        owned_result=owned_result,
        operational_output_bytes=operational_output_bytes,
        owner_event_candidates=owner_event_candidates,
        role_manifest=role_manifest,
    )
    expected_markers = _markers_from_validated_context(
        identity_join=identity_join,
        context=context,
    )
    if cutoff_attestation.markers != expected_markers:
        _fail("structural marker sequence differs from independently replayed source events")
    request = request_replay.request
    route = request.route_identity
    if (
        request.schedule_id != owned_result.result.schedule_id
        or identity_join.execution_terminal_status
        != "CHILD_ACTION_ROW_CAP_EXCEEDED"
        or identity_join.transcript_terminal_kind != "COMPLETED"
    ):
        _fail("production request or registered terminal outcome crossed the owner result")
    occurrence = K7OccurrenceIdentitySemanticAuthorityV2(
        _OCCURRENCE_ISSUER,
        identity_join.identity_join_id,
        owned_result.wrapper_id,
        owned_result.transcript.transcript_id,
        identity_join.transcript_terminal_id,
        transcript_sha256,
        ordered_chain_node_ids,
        context.request_replay_id,
        request.request_id,
        route.route_identity_id,
        context.runtime_id,
        context.source_envelope_id,
        context.verified_envelope_id,
        context.owner_event_candidate_set_id,
        context.owner_event_execution_binding_id,
        context.production_role_manifest_id,
        context.source_snapshot_id,
        context.source_archive_sha256,
        context.source_archive_byte_count,
        request.scientific_occurrence_id,
        route.logical_occurrence.logical_occurrence_id,
        route.route_attempt.route_attempt_id,
        route.decision_point.decision_point_id,
        receipt_set.window.window_id,
        identity_join.counter_registry_id,
        identity_join.stage_profile_id,
        identity_join.boundary_profile_id,
        identity_join.execution_profile_id,
        request.schedule_id,
        "CHILD_ACTION_ROW_CAP_EXCEEDED",
        "COMPLETED",
        "FAILURE",
        1,
        0,
        1,
        context.terminal_closure_id,
        context.runtime_business_result_id,
        context.runtime_business_result_sha256,
        context.runtime_business_result_byte_count,
        context.operational_output_sha256,
    )
    cutoff = K7OperationalCutoffSemanticAuthorityV2(
        _CUTOFF_ISSUER,
        occurrence.authority_id,
        cutoff_attestation.cutoff_attestation_id,
        context.start_marker_id,
        context.cutoff_marker_id,
        receipt_set.window.window_id,
        context.terminal_closure_id,
        GLOBAL_START_SEQUENCE,
        GLOBAL_TERMINAL_SEQUENCE,
        GLOBAL_CUTOFF_SEQUENCE,
        context.source_rows,
        context.tail_rows,
        context.charged_output_bytes,
        sum(row.source_byte_count for row in context.tail_rows),
        context.durable_output_event_ids,
    )
    return K7OccurrenceCutoffSemanticAuthorityBundleV2(
        _BUNDLE_ISSUER,
        occurrence,
        cutoff,
    )


def issue_k7_occurrence_cutoff_semantic_authorities_v2(
    **kwargs: Any,
) -> K7OccurrenceCutoffSemanticAuthorityBundleV2:
    """Issue both positive authorities from independently replayed inputs."""

    return _issue_k7_occurrence_cutoff_semantic_authorities_v2(**kwargs)


def replay_k7_occurrence_cutoff_semantic_authorities_v2(
    authority_bundle: Any,
    **kwargs: Any,
) -> K7OccurrenceCutoffSemanticAuthorityBundleV2:
    """Recompute the authorities from independently held roots and sources."""

    if type(authority_bundle) is not K7OccurrenceCutoffSemanticAuthorityBundleV2:
        _fail("authority replay requires one exact issued authority bundle")
    expected = _issue_k7_occurrence_cutoff_semantic_authorities_v2(**kwargs)
    if (
        authority_bundle.bundle_id != expected.bundle_id
        or authority_bundle.to_document() != expected.to_document()
        or authority_bundle.occurrence_authority.to_document()
        != expected.occurrence_authority.to_document()
        or authority_bundle.cutoff_authority.to_document()
        != expected.cutoff_authority.to_document()
    ):
        _fail("occurrence/cutoff semantic authority differs from independent replay")
    return expected


__all__ = (
    "AUTHORITY_BUNDLE_V2_DOMAIN",
    "CUTOFF_AUTHORITY_V2_DOMAIN",
    "ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error",
    "GLOBAL_CUTOFF_SEQUENCE",
    "GLOBAL_FIRST_SOURCE_SEQUENCE",
    "GLOBAL_START_SEQUENCE",
    "GLOBAL_TERMINAL_SEQUENCE",
    "K7OccurrenceCutoffSemanticAuthorityBundleV2",
    "K7OccurrenceIdentitySemanticAuthorityV2",
    "K7OperationalCutoffSemanticAuthorityV2",
    "K7PostCutoffTailRowV2",
    "K7SourceLocalReplayRowV2",
    "MEASUREMENT_CUTOFF_V2_DOMAIN",
    "MEASUREMENT_START_V2_DOMAIN",
    "OCCURRENCE_AUTHORITY_V2_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "TERMINAL_CLOSURE_V2_DOMAIN",
    "derive_k7_production_measurement_cutoff_id_v2",
    "derive_k7_production_measurement_start_id_v2",
    "derive_k7_production_terminal_closure_id_v2",
    "expected_k7_positive_cutoff_markers_v2",
    "issue_k7_occurrence_cutoff_semantic_authorities_v2",
    "replay_k7_occurrence_cutoff_semantic_authorities_v2",
)
