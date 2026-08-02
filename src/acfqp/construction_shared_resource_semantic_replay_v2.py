"""Fixed semantic replay authority for the nine V6 shared resources.

The raw journal modules deliberately stop short of semantic accounting
authority.  This module is the next, still internal, boundary: it accepts one
exact :class:`SharedResourceLiveSourceV2`, replays its centrally registered
component identities and raw semantics, and returns one issuer-owned exact
value.  It never accepts a reported value or a caller-supplied verifier.

The result is not a CounterRecord and cannot authorize CounterRecord,
WorkVector, or ComparisonVector issuance.  There is intentionally no
all-nine-envelope helper here.  The current source families may close over
different subwindows, so pretending that their nine values share one global
window would be unsound.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
import hashlib
import hmac
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_common_journal_v2 as common_v2
from acfqp import construction_shared_resource_output_journal_v2 as output_v2
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import (
    construction_shared_resource_transfer_mount_journal_v2 as transfer_v2,
)
from acfqp import (
    construction_shared_resource_working_process_evidence_v2 as working_v2,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_SHARED_RESOURCE_SEMANTIC_VERIFIER_V2_DOMAIN,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.20"
PROFILE_KEY = "construction_shared_resource_semantic_replay_v2"
ALL_NINE_REPLAY_SUPPORTED = False
ALL_NINE_REPLAY_BLOCKER = (
    "the nine live sources do not yet prove one common global measurement "
    "window; replay is intentionally source-local"
)

_RESULT_ISSUER = object()
SEMANTIC_VERIFIER_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_SEMANTIC_VERIFIER_V2_DOMAIN
)
_IDENTITY_FIELDS = (
    "live_envelope_id",
    "occurrence_id",
    "route_attempt_id",
    "decision_point_id",
    "measurement_window_id",
)


class ConstructionSharedResourceSemanticReplayV2Error(ValueError):
    """A source cannot be promoted to one exact shared-resource value."""


def _fail(message: str) -> NoReturn:
    raise ConstructionSharedResourceSemanticReplayV2Error(message)


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _canonical_object(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceSemanticReplayV2Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict:
        _fail(f"{label} must contain one JSON object")
    return document


@dataclass(frozen=True, slots=True)
class SharedResourceSemanticReplayResultV2:
    """One exact, source-local semantic replay result."""

    _issuer: InitVar[object]
    path: str
    exact_value: int
    reducer: ReducerEnum
    semantic_verifier_key: str
    semantic_verifier_id: str
    raw_replayer_module: str
    raw_replayer_symbol: str
    live_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    covered_start_sequence: int
    covered_cutoff_sequence: int
    exact_source_kind: resolution_v2.SharedResourceExactSourceKindV2
    required_provenance: tuple[
        resolution_v2.SharedResourceProvenanceProofKindV2, ...
    ]
    component_keys: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]
    source_bytes_sha256: tuple[str, ...]
    source_artifact_ids_replayed: bool
    source_bytes_replayed: bool
    provenance_replayed: bool
    complete_window_verified: bool
    identity_binding_verified: bool
    reducer_verified: bool
    raw_replayer_invoked: bool
    semantic_source_verified: bool
    counter_record_issuance_authorized: bool = False

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("semantic replay result is caller-minted")
        contract = _CONTRACT_BY_PATH.get(self.path)
        if contract is None:
            _fail("semantic replay result names an unknown path")
        _nonnegative(self.exact_value, "exact shared-resource value")
        try:
            reducer = ReducerEnum(self.reducer)
            source_kind = resolution_v2.SharedResourceExactSourceKindV2(
                self.exact_source_kind
            )
        except (TypeError, ValueError) as error:
            raise ConstructionSharedResourceSemanticReplayV2Error(
                "semantic replay result enum is invalid"
            ) from error
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "exact_source_kind", source_kind)
        for value in (
            self.semantic_verifier_id,
            self.live_envelope_id,
            self.occurrence_id,
            self.route_attempt_id,
            self.decision_point_id,
            self.measurement_window_id,
            self.operational_cutoff_id,
            *self.source_artifact_ids,
        ):
            try:
                parse_content_id(value)
            except (TypeError, ValueError) as error:
                raise ConstructionSharedResourceSemanticReplayV2Error(
                    "semantic replay result contains an invalid identity"
                ) from error
        _nonnegative(self.covered_start_sequence, "covered start sequence")
        _nonnegative(self.covered_cutoff_sequence, "covered cutoff sequence")
        if self.covered_cutoff_sequence < self.covered_start_sequence:
            _fail("semantic replay result cutoff precedes its start")
        if (
            self.reducer is not contract.reducer
            or self.semantic_verifier_key != contract.semantic_verifier_key
            or self.exact_source_kind is not contract.exact_source_kind
            or self.required_provenance != contract.required_provenance
            or self.component_keys
            != tuple(item.component_key for item in contract.required_components)
            or len(self.source_artifact_ids) != len(self.component_keys)
            or len(self.source_bytes_sha256) != len(self.component_keys)
        ):
            _fail("semantic replay result crossed its fixed path contract")
        for digest in self.source_bytes_sha256:
            if (
                type(digest) is not str
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                _fail("semantic replay result contains an invalid source digest")
        proof_flags = (
            self.source_artifact_ids_replayed,
            self.source_bytes_replayed,
            self.provenance_replayed,
            self.complete_window_verified,
            self.identity_binding_verified,
            self.reducer_verified,
            self.raw_replayer_invoked,
            self.semantic_source_verified,
        )
        if any(value is not True for value in proof_flags):
            _fail("exact semantic replay lacks one required proof flag")
        if self.counter_record_issuance_authorized is not False:
            _fail("semantic replay cannot authorize CounterRecord issuance")

    def to_internal_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_semantic_replay.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "path": self.path,
            "exact_value": self.exact_value,
            "reducer": self.reducer.value,
            "semantic_verifier_key": self.semantic_verifier_key,
            "semantic_verifier_id": self.semantic_verifier_id,
            "raw_replayer_module": self.raw_replayer_module,
            "raw_replayer_symbol": self.raw_replayer_symbol,
            "live_envelope_id": self.live_envelope_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "measurement_window_id": self.measurement_window_id,
            "operational_cutoff_id": self.operational_cutoff_id,
            "covered_start_sequence": self.covered_start_sequence,
            "covered_cutoff_sequence": self.covered_cutoff_sequence,
            "exact_source_kind": self.exact_source_kind.value,
            "required_provenance": [
                item.value for item in self.required_provenance
            ],
            "component_keys": list(self.component_keys),
            "source_artifact_ids": list(self.source_artifact_ids),
            "source_bytes_sha256": list(self.source_bytes_sha256),
            "source_artifact_ids_replayed": True,
            "source_bytes_replayed": True,
            "provenance_replayed": True,
            "complete_window_verified": True,
            "identity_binding_verified": True,
            "reducer_verified": True,
            "raw_replayer_invoked": True,
            "semantic_source_verified": True,
            "counter_record_issuance_authorized": False,
            "counter_record_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vector_authorized": False,
            "formal_artifact_id": None,
            "source_local_only": True,
            "internal_only": True,
        }


_CONTRACT_BY_PATH = {
    item.path: item
    for item in resolution_v2.official_shared_resource_resolution_catalogue_v2()
}


def _source_family(path: str) -> str:
    if path in {common_v2.HASH_PATH, common_v2.INTEGRITY_PATH, common_v2.PROTOCOL_PATH}:
        return "common"
    if path in {transfer_v2.READ_PATH, transfer_v2.STAGED_PATH, transfer_v2.MOUNTED_PATH}:
        return "transfer_mount"
    if path == output_v2.OUTPUT_PATH:
        return "output"
    if path in {working_v2.MEMORY_PATH, working_v2.PROCESS_PATH}:
        return "working_process"
    _fail("shared-resource path has no fixed raw source family")


def _component_domain_and_id_field(
    family: str,
    schema_id: str,
) -> tuple[str, str | None]:
    try:
        if family == "common":
            return (
                common_v2._COMPONENT_DOMAIN[schema_id],  # noqa: SLF001
                common_v2._COMPONENT_ID_FIELD[schema_id],  # noqa: SLF001
            )
        if family == "transfer_mount":
            return (
                transfer_v2._COMPONENT_DOMAIN[schema_id],  # noqa: SLF001
                transfer_v2._COMPONENT_ID_FIELD[schema_id],  # noqa: SLF001
            )
        if family == "output":
            return (
                output_v2._COMPONENT_DOMAIN[schema_id],  # noqa: SLF001
                output_v2._COMPONENT_ID_FIELD[schema_id],  # noqa: SLF001
            )
        if family == "working_process":
            return (
                working_v2._COMPONENT_DOMAIN[schema_id],  # noqa: SLF001
                None,
            )
    except KeyError as error:
        raise ConstructionSharedResourceSemanticReplayV2Error(
            "component schema has no central domain registration"
        ) from error
    _fail("component source family is invalid")


def _replay_central_component(
    component: resolution_v2.SharedResourceEvidenceComponentV2,
    *,
    family: str,
) -> dict[str, Any]:
    if type(component) is not resolution_v2.SharedResourceEvidenceComponentV2:
        _fail("semantic replay contains a foreign evidence component")
    document = _canonical_object(component.raw_bytes, component.component_key)
    if document.get("schema") != component.source_schema_id:
        _fail("component schema differs from its canonical bytes")
    digest = hashlib.sha256(component.raw_bytes).hexdigest()
    if not hmac.compare_digest(digest, component.source_bytes_sha256):
        _fail("component SHA-256 differs from its canonical bytes")
    domain, id_field = _component_domain_and_id_field(
        family, component.source_schema_id
    )
    if id_field is None:
        expected_id = content_id(domain, document)
    else:
        embedded_id = document.get(id_field)
        try:
            parse_content_id(embedded_id)
        except (TypeError, ValueError) as error:
            raise ConstructionSharedResourceSemanticReplayV2Error(
                "component embedded content ID is invalid"
            ) from error
        payload = {key: value for key, value in document.items() if key != id_field}
        expected_id = content_id(domain, payload)
        if not hmac.compare_digest(expected_id, embedded_id):
            _fail("component embedded central content ID does not replay")
    if not hmac.compare_digest(expected_id, component.source_artifact_id):
        _fail("component wrapper artifact ID differs from central replay")
    if family == "working_process":
        # The working/process family stores its central ID in the wrapper
        # rather than as an embedded field.  Its fixed raw parser additionally
        # checks every authority-boundary flag before path semantics run.
        document = working_v2._canonical_object(  # noqa: SLF001
            component.raw_bytes, component.source_schema_id
        )
    return document


def _validate_source_contract(
    source: Any,
) -> tuple[
    resolution_v2.SharedResourcePathContractV2,
    str,
    dict[str, dict[str, Any]],
]:
    if type(source) is not resolution_v2.SharedResourceLiveSourceV2:
        _fail("semantic replay requires one exact SharedResourceLiveSourceV2")
    contract = _CONTRACT_BY_PATH.get(source.path)
    if contract is None:
        _fail("semantic replay source names an unknown path")
    expected_components = tuple(
        (item.component_key, item.source_schema_id)
        for item in contract.required_components
    )
    actual_components = tuple(
        (item.component_key, item.source_schema_id) for item in source.components
    )
    if actual_components != expected_components:
        _fail("source components are missing, extra, reordered, or mistyped")
    if (
        source.exact_source_kind is not contract.exact_source_kind
        or source.provenance_claims != contract.required_provenance
    ):
        _fail("source kind or required provenance differs from the catalogue")
    for value in (
        source.live_envelope_id,
        source.occurrence_id,
        source.route_attempt_id,
        source.decision_point_id,
        source.measurement_window_id,
        source.operational_cutoff_id,
    ):
        try:
            parse_content_id(value)
        except (TypeError, ValueError) as error:
            raise ConstructionSharedResourceSemanticReplayV2Error(
                "source identity is stale or malformed"
            ) from error
    start = _nonnegative(source.covered_start_sequence, "source start sequence")
    cutoff = _nonnegative(source.covered_cutoff_sequence, "source cutoff sequence")
    if cutoff < start:
        _fail("source cutoff precedes its start")
    family = _source_family(source.path)
    documents: dict[str, dict[str, Any]] = {}
    for component in source.components:
        document = _replay_central_component(component, family=family)
        for field in _IDENTITY_FIELDS:
            if document.get(field) != getattr(source, field):
                _fail("component crossed its source identity")
        if document.get("operational_cutoff_id") != source.operational_cutoff_id:
            _fail("component crossed its source operational cutoff")
        if (
            "measurement_start_sequence" in document
            and document["measurement_start_sequence"] != start
        ):
            _fail("component crossed its source start sequence")
        if (
            "operational_cutoff_sequence" in document
            and document["operational_cutoff_sequence"] != cutoff
        ):
            _fail("component crossed its source cutoff sequence")
        documents[component.component_key] = document
    return contract, family, documents


def _validate_global_index(
    *,
    cutoff: Mapping[str, Any],
    source: resolution_v2.SharedResourceLiveSourceV2,
    expected_path_rows: list[dict[str, Any]],
    allowed_paths: frozenset[str],
    common_observations: bool,
) -> None:
    if cutoff.get("window_closed") is not True or cutoff.get("cutoff_is_inclusive") is not True:
        _fail("source cutoff is not closed and inclusive")
    index = cutoff.get("global_event_index")
    if type(index) is not list or any(type(row) is not dict for row in index):
        _fail("source cutoff global event index is malformed")
    start = source.covered_start_sequence
    end = source.covered_cutoff_sequence
    if (
        cutoff.get("measurement_start_sequence") != start
        or cutoff.get("operational_cutoff_sequence") != end
        or cutoff.get("global_event_count") != len(index)
        or end != start + len(index)
        or [row.get("global_sequence") for row in index]
        != list(range(start + 1, end + 1))
    ):
        _fail("source cutoff hides, duplicates, or reorders an event")
    selected_rows: list[dict[str, Any]] = []
    per_path_sequences: dict[str, list[int]] = {path: [] for path in allowed_paths}
    event_ids: set[str] = set()
    observations: list[str] = []
    for row in index:
        path = row.get("path")
        if path not in allowed_paths:
            _fail("source cutoff contains an event from another source family")
        expected_fields = {
            "global_sequence",
            "path",
            "path_sequence",
            "event_kind",
            "event_id",
        }
        if common_observations:
            expected_fields |= {
                "authenticated_broker_observation_id",
                "broker_observation_binding_id",
            }
        if set(row) != expected_fields:
            _fail("source cutoff event-index row has unknown or missing fields")
        sequence = _positive(row["path_sequence"], "path sequence")
        per_path_sequences[path].append(sequence)
        try:
            event_id = parse_content_id(row["event_id"])
        except (TypeError, ValueError) as error:
            raise ConstructionSharedResourceSemanticReplayV2Error(
                "source cutoff contains an invalid event identity"
            ) from error
        if event_id in event_ids:
            _fail("source cutoff repeats an event identity")
        event_ids.add(event_id)
        if common_observations:
            try:
                observation = parse_content_id(
                    row["authenticated_broker_observation_id"]
                )
                parse_content_id(row["broker_observation_binding_id"])
            except (TypeError, ValueError) as error:
                raise ConstructionSharedResourceSemanticReplayV2Error(
                    "source cutoff contains an invalid observation identity"
                ) from error
            observations.append(observation)
        if path == source.path:
            selected_rows.append(dict(row))
    for sequences in per_path_sequences.values():
        if sequences != list(range(1, len(sequences) + 1)):
            _fail("source cutoff contains a missing or reordered path sequence")
    if selected_rows != expected_path_rows:
        _fail("source cutoff differs from its replayed path transcript")
    if common_observations:
        if (
            cutoff.get("authenticated_broker_observation_ids") != observations
            or len(set(observations)) != len(observations)
        ):
            _fail("source cutoff observation index is missing or duplicated")


def _replay_common_path(
    source: resolution_v2.SharedResourceLiveSourceV2,
    documents: Mapping[str, dict[str, Any]],
) -> tuple[int, str, str]:
    cutoff = common_v2._replay_component(  # noqa: SLF001
        next(
            item.raw_bytes
            for item in source.components
            if item.component_key == "cutoff_attestation"
        ),
        common_v2.CUTOFF_SCHEMA_ID,
    )
    common_v2._exact_fields(  # noqa: SLF001
        cutoff,
        common_v2._COMMON_COMPONENT_FIELDS  # noqa: SLF001
        | common_v2._IDENTITY_FIELDS  # noqa: SLF001
        | {
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
        },
        "source-local common cutoff",
    )
    if source.path == common_v2.HASH_PATH:
        transcript_key = "hash_event_transcript"
        registry_key = "hash_purpose_registry"
        site_key = "loaded_source_site_attestation"
    elif source.path == common_v2.INTEGRITY_PATH:
        transcript_key = "integrity_obligation_transcript"
        registry_key = "integrity_obligation_registry"
        site_key = "loaded_source_site_attestation"
    else:
        transcript_key = "protocol_obligation_transcript"
        registry_key = "protocol_obligation_registry"
        site_key = "loaded_source_site_attestation"
    transcript_component = next(
        item for item in source.components if item.component_key == transcript_key
    )
    registry_component = next(
        item for item in source.components if item.component_key == registry_key
    )
    site_component = next(
        item for item in source.components if item.component_key == site_key
    )
    transcript = common_v2._replay_component(  # noqa: SLF001
        transcript_component.raw_bytes, transcript_component.source_schema_id
    )
    registry = common_v2._replay_component(  # noqa: SLF001
        registry_component.raw_bytes, registry_component.source_schema_id
    )
    sites = common_v2._replay_component(  # noqa: SLF001
        site_component.raw_bytes, site_component.source_schema_id
    )
    count, event_index = common_v2._replay_path(  # noqa: SLF001
        transcript=transcript,
        registry=registry,
        sites=sites,
        path=source.path,
    )
    if (
        transcript.get("measurement_start_sequence")
        != source.covered_start_sequence
        or transcript.get("operational_cutoff_sequence")
        != source.covered_cutoff_sequence
    ):
        _fail("common transcript crossed its source-local window")
    _validate_global_index(
        cutoff=cutoff,
        source=source,
        expected_path_rows=event_index,
        allowed_paths=frozenset(
            {common_v2.HASH_PATH, common_v2.INTEGRITY_PATH, common_v2.PROTOCOL_PATH}
        ),
        common_observations=True,
    )
    return (
        count,
        common_v2.__name__,
        "_replay_path",
    )


def _replay_transfer_path(
    source: resolution_v2.SharedResourceLiveSourceV2,
    documents: Mapping[str, dict[str, Any]],
) -> tuple[int, str, str]:
    component_by_key = {item.component_key: item for item in source.components}
    cutoff_component = component_by_key["cutoff_attestation"]
    cutoff = transfer_v2._replay_component_bytes(  # noqa: SLF001
        cutoff_component.raw_bytes, cutoff_component.source_schema_id
    )
    transfer_v2._exact_fields(  # noqa: SLF001
        cutoff,
        transfer_v2._COMMON_COMPONENT_FIELDS  # noqa: SLF001
        | transfer_v2._IDENTITY_FIELDS  # noqa: SLF001
        | {
            "operational_cutoff_attestation_id",
            "operational_cutoff_id",
            "session_binding_id",
            "measurement_start_sequence",
            "operational_cutoff_sequence",
            "global_event_count",
            "global_event_index",
            "window_closed",
            "cutoff_is_inclusive",
        },
        "source-local transfer/mount cutoff",
    )
    if source.path == transfer_v2.READ_PATH:
        journal_key = "read_transfer_journal"
        registry_key = "transfer_charge_registry"
        operation = transfer_v2.TransferOperationKindV2.READ
        replay_symbol = "_replay_transfer_path"
    elif source.path == transfer_v2.STAGED_PATH:
        journal_key = "staged_transfer_journal"
        registry_key = "transfer_charge_registry"
        operation = transfer_v2.TransferOperationKindV2.STAGE
        replay_symbol = "_replay_transfer_path"
    else:
        journal_key = "mount_visibility_journal"
        registry_key = "mount_payload_registry"
        operation = None
        replay_symbol = "_replay_mount"
    journal_component = component_by_key[journal_key]
    registry_component = component_by_key[registry_key]
    journal = transfer_v2._replay_component_bytes(  # noqa: SLF001
        journal_component.raw_bytes, journal_component.source_schema_id
    )
    registry = transfer_v2._replay_component_bytes(  # noqa: SLF001
        registry_component.raw_bytes, registry_component.source_schema_id
    )
    if operation is None:
        value, event_index = transfer_v2._replay_mount(  # noqa: SLF001
            payload_registry=registry,
            journal=journal,
        )
    else:
        value, event_index, _purposes = transfer_v2._replay_transfer_path(  # noqa: SLF001
            journal=journal,
            registry=registry,
            path=source.path,
            operation_kind=operation,
        )
    if (
        journal.get("measurement_start_sequence")
        != source.covered_start_sequence
        or journal.get("operational_cutoff_sequence")
        != source.covered_cutoff_sequence
    ):
        _fail("transfer/mount journal crossed its source-local window")
    _validate_global_index(
        cutoff=cutoff,
        source=source,
        expected_path_rows=event_index,
        allowed_paths=frozenset(
            {transfer_v2.READ_PATH, transfer_v2.STAGED_PATH, transfer_v2.MOUNTED_PATH}
        ),
        common_observations=False,
    )
    return value, transfer_v2.__name__, replay_symbol


def _replay_output_path(
    source: resolution_v2.SharedResourceLiveSourceV2,
    documents: Mapping[str, dict[str, Any]],
) -> tuple[int, str, str]:
    components = {item.component_key: item.raw_bytes for item in source.components}
    replay = output_v2.replay_production_output_exact_semantic_evidence_v2(
        fixed_point_bytes=components["durable_output_fixed_point"],
        exclusive_writer_bytes=components["exclusive_writer_attestation"],
        cutoff_bytes=components["operational_cutoff_attestation"],
        output_manifest_bytes=components["output_manifest"],
    )
    if getattr(replay, "production_semantic_eligible", False) is not True:
        _fail("synthetic construction output cannot become an exact value")
    if any(
        getattr(replay, field) != getattr(source, field)
        for field in (*_IDENTITY_FIELDS, "operational_cutoff_id")
    ):
        _fail("output raw replay crossed its source identity")
    return (
        replay.raw_output_bytes,
        output_v2.__name__,
        "replay_production_output_exact_semantic_evidence_v2",
    )


def _require_working_exact(
    documents: Mapping[str, dict[str, Any]],
) -> None:
    values = tuple(documents.values())
    if not values:
        _fail("working/process semantic replay lacks components")
    first = values[0]
    if (
        first.get("closure_kind")
        != working_v2.WorkingProcessClosureKindV2.EXACT.value
        or first.get("failure_reason") is not None
        or any(
            item.get("closure_kind") != first["closure_kind"]
            or item.get("failure_reason") is not None
            for item in values
        )
    ):
        _fail("failure-prefix working/process evidence cannot become exact")


def _validate_working_documents(
    documents: Mapping[str, dict[str, Any]],
) -> None:
    for document in documents.values():
        schema = document["schema"]
        try:
            expected = (
                working_v2._BASE_COMPONENT_KEYS  # noqa: SLF001
                | working_v2._SCHEMA_BODY_KEYS[schema]  # noqa: SLF001
            )
            working_v2._exact_fields(  # noqa: SLF001
                document, expected, schema
            )
        except KeyError as error:
            raise ConstructionSharedResourceSemanticReplayV2Error(
                "working/process component schema is not registered"
            ) from error
    first = next(iter(documents.values()))
    shared = (
        *_IDENTITY_FIELDS,
        "operational_cutoff_id",
        "measurement_start_sequence",
        "operational_cutoff_sequence",
        "closure_kind",
        "failure_reason",
    )
    if any(
        any(document.get(key) != first.get(key) for key in shared)
        for document in documents.values()
    ):
        _fail("working/process components crossed identity or cutoff")


def _replay_working_memory_path(
    source: resolution_v2.SharedResourceLiveSourceV2,
    documents: Mapping[str, dict[str, Any]],
) -> tuple[int, str, str]:
    _validate_working_documents(documents)
    _require_working_exact(documents)
    pre = documents["memory_peak_pre_read"]
    post = documents["memory_peak_post_read"]
    same = documents["same_ofd_attestation"]
    empty = documents["cgroup_empty_attestation"]
    start = source.covered_start_sequence
    cutoff = source.covered_cutoff_sequence
    try:
        parsed_pre = working_v2._parse_peak(  # noqa: SLF001
            pre["raw_read_ascii"].encode("ascii"), "semantic pre peak"
        )
        parsed_post = working_v2._parse_peak(  # noqa: SLF001
            post["raw_read_ascii"].encode("ascii"), "semantic post peak"
        )
    except (AttributeError, UnicodeError) as error:
        raise ConstructionSharedResourceSemanticReplayV2Error(
            "working peak raw reads are malformed"
        ) from error
    retained = pre["retained_memory_peak_ofd_identity"]
    expected_roles = list(working_v2.EXPECTED_ROLES)
    if (
        pre["read_ordinal"] != 1
        or pre["read_sequence"] != start
        or pre["reset_write_ascii"] != "0"
        or parsed_pre != pre["parsed_peak_bytes"]
        or pre["parsed_peak_bytes"] != 0
        or pre["no_baseline_subtraction"] is not True
        or post["read_ordinal"] != 2
        or post["read_performed"] is not True
        or post["read_sequence"] != cutoff - 1
        or parsed_post != post["parsed_peak_bytes"]
        or post["parsed_peak_bytes"] < pre["parsed_peak_bytes"]
        or post["raw_derived_max_bytes"]
        != max(pre["parsed_peak_bytes"], post["parsed_peak_bytes"])
        or post["after_output_commit"] is not True
        or post["after_direct_pidfd_reap_roles"] != expected_roles
        or post["after_descendant_free_scan"] is not True
        or post["no_baseline_subtraction"] is not True
        or same["retained_memory_peak_ofd_identity"] != retained
        or same["named_memory_peak_initial_identity"] != retained
        or same["named_memory_peak_final_identity"] != retained
        or same["reset_pre_post_same_retained_fd"] is not True
        or same["pre_read_sequence"] != start
        or same["post_read_sequence"] != post["read_sequence"]
        or same["ofd_replacement_detected"] is not False
        or empty["pre_reset_cgroup_procs"] != []
        or empty["pre_reset_nr_descendants"] != 0
        or empty["pre_reset_nr_dying_descendants"] != 0
        or empty["post_reap_scan_performed"] is not True
        or empty["post_reap_cgroup_procs"] != []
        or empty["post_reap_nr_descendants"] != 0
        or empty["post_reap_nr_dying_descendants"] != 0
        or empty["direct_reaped_roles"] != expected_roles
    ):
        _fail("working-byte MAX does not replay from one exact same-OFD window")
    return (
        post["raw_derived_max_bytes"],
        __name__,
        "_replay_working_memory_path",
    )


def _replay_working_process_path(
    source: resolution_v2.SharedResourceLiveSourceV2,
    documents: Mapping[str, dict[str, Any]],
) -> tuple[int, str, str]:
    _validate_working_documents(documents)
    _require_working_exact(documents)
    cutoff = documents["cutoff_attestation"]
    no_spawn = documents["no_spawn_attestation"]
    reaps = documents["pidfd_reap_attestation"]
    journal = documents["process_lifecycle_journal"]
    start = source.covered_start_sequence
    end = source.covered_cutoff_sequence
    events = journal["events"]
    if type(events) is not list or any(type(row) is not dict for row in events):
        _fail("process lifecycle events are not one raw object list")
    sequences = tuple(row.get("sequence") for row in events)
    if (
        sequences != tuple(range(start, start + len(events)))
        or journal["event_count"] != len(events)
        or journal["last_event_sequence"] != end - 1
        or cutoff["last_included_event_sequence"] != end - 1
        or cutoff["included_event_count"] != len(events)
        or end != start + len(events)
        or cutoff["closed_inclusive"] is not True
        or cutoff["cutoff_auto_assigned"] is not True
        or cutoff["post_cutoff_append_allowed"] is not False
    ):
        _fail("process cutoff hides, skips, or duplicates a lifecycle event")
    expected_cutoff_id = working_v2._domain_id(  # noqa: SLF001
        working_v2._COMPONENT_DOMAIN[working_v2.CUTOFF_SCHEMA_ID],  # noqa: SLF001
        {
            "schema": working_v2.CUTOFF_SCHEMA_ID,
            "schema_version": working_v2.SCHEMA_VERSION,
            **{key: journal[key] for key in working_v2._IDENTITY_KEYS},  # noqa: SLF001
            "measurement_start_sequence": start,
            "operational_cutoff_sequence": end,
            "last_included_event_sequence": end - 1,
            "included_event_count": len(events),
            "closure_kind": journal["closure_kind"],
            "failure_reason": journal["failure_reason"],
        },
    )
    if source.operational_cutoff_id != expected_cutoff_id:
        _fail("process operational cutoff identity does not replay")
    event_kinds = {item.value for item in working_v2.LifecycleEventKindV2}
    for event in events:
        payload = dict(event)
        event_id = payload.pop("raw_event_id", None)
        if (
            event.get("kind") not in event_kinds
            or event_id
            != working_v2._domain_id(  # noqa: SLF001
                working_v2.WORKING_PROCESS_EVENT_V2_DOMAIN, payload
            )
        ):
            _fail("process lifecycle raw event ID does not replay")
    clone_events = [
        row
        for row in events
        if row["kind"]
        == working_v2.LifecycleEventKindV2.NATIVE_POSITIVE_CLONE_WRITE_AHEAD.value
    ]
    clone_roles = tuple(row.get("role") for row in clone_events)
    if (
        clone_roles != working_v2.EXPECTED_ROLES
        or any(
            type(row.get("pid")) is not int
            or row["pid"] <= 0
            or row.get("native_clone_result") != row["pid"]
            or row.get("native_write_ahead_edge") != 1
            or row.get("cgroup_membership_observed") is not True
            for row in clone_events
        )
        or journal["positive_clone_roles"] != list(clone_roles)
        or journal["raw_derived_process_launches_lower_bound"]
        != len(clone_events)
    ):
        _fail("process launches differ from two positive native clone edges")
    edge_by_role = {row["role"]: row for row in clone_events}
    auth_by_role: dict[str, list[dict[str, Any]]] = {
        role: [] for role in clone_roles
    }
    frame_author_by_role = dict(working_v2.manifest_v2.FRAME_AUTHOR_VECTOR)
    authenticated_ids: set[str] = set()
    for row in events:
        if row["kind"] != working_v2.LifecycleEventKindV2.AUTHENTICATED_SCM_FRAME.value:
            continue
        role = row.get("role")
        edge = edge_by_role.get(role)
        frame_id = row.get("authenticated_broker_frame_id")
        if (
            edge is None
            or row.get("pid") != edge["pid"]
            or row.get("scm_sender_pid") != edge["pid"]
            or row.get("pidfd_identity") != edge["pidfd_identity"]
            or row.get("sequence") <= edge["sequence"]
            or frame_author_by_role.get(row.get("frame_role")) != role
            or type(row.get("frame_sequence")) is not int
            or type(frame_id) is not str
            or frame_id in authenticated_ids
        ):
            _fail("authenticated SCM frame crossed its native process edge")
        try:
            parse_content_id(frame_id)
        except (TypeError, ValueError) as error:
            raise ConstructionSharedResourceSemanticReplayV2Error(
                "authenticated SCM frame identity is invalid"
            ) from error
        auth_by_role[role].append(row)
        authenticated_ids.add(frame_id)
    no_spawn_rows = no_spawn["role_attestations"]
    journal_no_spawn = [
        row
        for row in events
        if row["kind"] == working_v2.LifecycleEventKindV2.POSTEXEC_NO_SPAWN.value
    ]
    if type(no_spawn_rows) is not list:
        _fail("no-spawn role attestations are not a list")
    no_spawn_by_role: dict[str, dict[str, Any]] = {}
    for row in no_spawn_rows:
        if type(row) is not dict or row.get("role") in no_spawn_by_role:
            _fail("no-spawn role is malformed or duplicated")
        role = row.get("role")
        edge = edge_by_role.get(role)
        matching = [item for item in journal_no_spawn if item.get("role") == role]
        projection = (
            {}
            if len(matching) != 1
            else {key: value for key, value in matching[0].items() if key != "raw_event_id"}
        )
        if (
            edge is None
            or len(matching) != 1
            or projection != row
            or row.get("pid") != edge["pid"]
            or row.get("pidfd_identity") != edge["pidfd_identity"]
            or row.get("sequence") <= edge["sequence"]
            or row.get("postexec_filter_sha256")
            != working_v2._postexec_filter_sha256()  # noqa: SLF001
            or row.get("clone_fork_vfork_denied") is not True
            or row.get("execve_execveat_denied") is not True
            or row.get("seccomp_tsync_completed") is not True
        ):
            _fail("postexec no-spawn replay is forged or crossed")
        try:
            parse_content_id(row.get("attestation_source_id"))
        except (TypeError, ValueError) as error:
            raise ConstructionSharedResourceSemanticReplayV2Error(
                "no-spawn attestation identity is invalid"
            ) from error
        no_spawn_by_role[role] = row
    if (
        len(journal_no_spawn) != len(no_spawn_rows)
        or no_spawn["postexec_filter_sha256"]
        != working_v2._postexec_filter_sha256()  # noqa: SLF001
    ):
        _fail("no-spawn component crossed its fixed process filter")
    reap_rows = reaps["direct_reaps"]
    journal_reaps = [
        row
        for row in events
        if row["kind"] == working_v2.LifecycleEventKindV2.DIRECT_PIDFD_REAP.value
    ]
    if type(reap_rows) is not list:
        _fail("PIDfd direct reaps are not a list")
    reap_by_role: dict[str, dict[str, Any]] = {}
    for row in reap_rows:
        if type(row) is not dict or row.get("role") in reap_by_role:
            _fail("PIDfd direct-reap role is malformed or duplicated")
        role = row.get("role")
        edge = edge_by_role.get(role)
        expected_auth = auth_by_role.get(role, [])
        matching = [item for item in journal_reaps if item.get("role") == role]
        projection = (
            {}
            if len(matching) != 1
            else {key: value for key, value in matching[0].items() if key != "raw_event_id"}
        )
        if (
            edge is None
            or not expected_auth
            or len(matching) != 1
            or any(row.get(key) != value for key, value in projection.items())
            or row.get("pid") != edge["pid"]
            or row.get("wait_si_pid") != edge["pid"]
            or row.get("authenticated_scm_sender_pid") != edge["pid"]
            or row.get("pidfd_identity") != edge["pidfd_identity"]
            or row.get("wait_idtype") != "P_PIDFD"
            or row.get("wait_options") != "WEXITED"
            or row.get("direct_child_reaped") is not True
            or row.get("authenticated_frame_ids")
            != [item["authenticated_broker_frame_id"] for item in expected_auth]
        ):
            _fail("direct PIDfd reap crossed process or frame identity")
        reap_by_role[role] = row
    output_events = [
        row
        for row in events
        if row["kind"] == working_v2.LifecycleEventKindV2.OUTPUT_COMMITTED.value
    ]
    output_commit_id = journal["output_commit_id"]
    if (
        len(journal_reaps) != len(reap_rows)
        or len(output_events) != 1
        or output_events[0].get("role") is not None
        or output_events[0].get("output_commit_id") != output_commit_id
    ):
        _fail("process reap or output-commit journal is incomplete")
    try:
        parse_content_id(output_commit_id)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceSemanticReplayV2Error(
            "process output-commit identity is invalid"
        ) from error
    expected_roles = working_v2.EXPECTED_ROLES
    if (
        set(auth_by_role) != set(expected_roles)
        or any(not auth_by_role[role] for role in expected_roles)
        or tuple(no_spawn_by_role) != expected_roles
        or tuple(reap_by_role) != expected_roles
        or no_spawn["expected_roles"] != list(expected_roles)
        or reaps["expected_roles"] != list(expected_roles)
        or journal["expected_roles"] != list(expected_roles)
        or no_spawn["complete_role_coverage"] is not True
        or reaps["complete_role_coverage"] is not True
        or journal["raw_derived_process_launches_sum"] != 2
        or journal["failure_prefix_cannot_be_exact"] is not False
        or any(
            output_events[0]["sequence"] >= reap_by_role[role]["sequence"]
            for role in expected_roles
        )
    ):
        _fail("exact process replay lacks two complete distinct roles")
    return 2, __name__, "_replay_working_process_path"


def _semantic_verifier_id(
    *,
    contract: resolution_v2.SharedResourcePathContractV2,
    raw_module: str,
    raw_symbol: str,
) -> str:
    payload = {
        "schema": "acfqp.construction_shared_resource_semantic_verifier.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "catalogue_fingerprint": (
            resolution_v2.official_shared_resource_catalogue_fingerprint_v2()
        ),
        "path": contract.path,
        "semantic_verifier_key": contract.semantic_verifier_key,
        "reducer": contract.reducer.value,
        "raw_replayer_module": raw_module,
        "raw_replayer_symbol": raw_symbol,
        "counter_record_issuance_authorized": False,
    }
    return content_id(SEMANTIC_VERIFIER_V2_DOMAIN, payload)


def _verify_expected_path(
    source: Any,
    expected_path: str,
) -> SharedResourceSemanticReplayResultV2:
    contract, family, documents = _validate_source_contract(source)
    if source.path != expected_path:
        _fail("path-specific verifier received another shared-resource path")
    registry = registry_v6.official_counter_registry_v6()
    leaf = registry.by_path.get(source.path)
    if (
        leaf is None
        or leaf.reducer is not contract.reducer
        or not leaf.required
        or leaf.lane.value != "operational"
    ):
        _fail("path reducer or operational ownership differs from official V6")
    try:
        if family == "common":
            value, raw_module, raw_symbol = _replay_common_path(source, documents)
        elif family == "transfer_mount":
            value, raw_module, raw_symbol = _replay_transfer_path(source, documents)
        elif family == "output":
            value, raw_module, raw_symbol = _replay_output_path(source, documents)
        elif source.path == working_v2.MEMORY_PATH:
            value, raw_module, raw_symbol = _replay_working_memory_path(
                source, documents
            )
        else:
            value, raw_module, raw_symbol = _replay_working_process_path(
                source, documents
            )
    except ConstructionSharedResourceSemanticReplayV2Error:
        raise
    except (
        common_v2.ConstructionSharedResourceCommonJournalV2Error,
        transfer_v2.ConstructionSharedResourceTransferMountJournalV2Error,
        output_v2.ConstructionSharedResourceOutputJournalV2Error,
        working_v2.ConstructionSharedResourceWorkingProcessEvidenceV2Error,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise ConstructionSharedResourceSemanticReplayV2Error(
            f"{source.path} raw semantic replay failed"
        ) from error
    _nonnegative(value, source.path)
    components = source.components
    return SharedResourceSemanticReplayResultV2(
        _RESULT_ISSUER,
        source.path,
        value,
        contract.reducer,
        contract.semantic_verifier_key,
        _semantic_verifier_id(
            contract=contract,
            raw_module=raw_module,
            raw_symbol=raw_symbol,
        ),
        raw_module,
        raw_symbol,
        source.live_envelope_id,
        source.occurrence_id,
        source.route_attempt_id,
        source.decision_point_id,
        source.measurement_window_id,
        source.operational_cutoff_id,
        source.covered_start_sequence,
        source.covered_cutoff_sequence,
        contract.exact_source_kind,
        contract.required_provenance,
        tuple(item.component_key for item in components),
        tuple(item.source_artifact_id for item in components),
        tuple(item.source_bytes_sha256 for item in components),
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
    )


def verify_hash_invocations_exact_v2(
    source: Any,
) -> SharedResourceSemanticReplayResultV2:
    return _verify_expected_path(source, common_v2.HASH_PATH)


def verify_integrity_checks_exact_v2(
    source: Any,
) -> SharedResourceSemanticReplayResultV2:
    return _verify_expected_path(source, common_v2.INTEGRITY_PATH)


def verify_protocol_checks_exact_v2(
    source: Any,
) -> SharedResourceSemanticReplayResultV2:
    return _verify_expected_path(source, common_v2.PROTOCOL_PATH)


def verify_mounted_bytes_peak_exact_v2(
    source: Any,
) -> SharedResourceSemanticReplayResultV2:
    return _verify_expected_path(source, transfer_v2.MOUNTED_PATH)


def verify_output_bytes_exact_v2(
    source: Any,
) -> SharedResourceSemanticReplayResultV2:
    return _verify_expected_path(source, output_v2.OUTPUT_PATH)


def verify_read_bytes_exact_v2(
    source: Any,
) -> SharedResourceSemanticReplayResultV2:
    return _verify_expected_path(source, transfer_v2.READ_PATH)


def verify_staged_bytes_exact_v2(
    source: Any,
) -> SharedResourceSemanticReplayResultV2:
    return _verify_expected_path(source, transfer_v2.STAGED_PATH)


def verify_working_bytes_peak_exact_v2(
    source: Any,
) -> SharedResourceSemanticReplayResultV2:
    return _verify_expected_path(source, working_v2.MEMORY_PATH)


def verify_process_launches_exact_v2(
    source: Any,
) -> SharedResourceSemanticReplayResultV2:
    return _verify_expected_path(source, working_v2.PROCESS_PATH)


_DISPATCH = {
    (common_v2.HASH_PATH, "verify_hash_invocations_exact_v2"):
        verify_hash_invocations_exact_v2,
    (common_v2.INTEGRITY_PATH, "verify_integrity_checks_exact_v2"):
        verify_integrity_checks_exact_v2,
    (common_v2.PROTOCOL_PATH, "verify_protocol_checks_exact_v2"):
        verify_protocol_checks_exact_v2,
    (transfer_v2.MOUNTED_PATH, "verify_mounted_bytes_peak_exact_v2"):
        verify_mounted_bytes_peak_exact_v2,
    (output_v2.OUTPUT_PATH, "verify_output_bytes_exact_v2"):
        verify_output_bytes_exact_v2,
    (transfer_v2.READ_PATH, "verify_read_bytes_exact_v2"):
        verify_read_bytes_exact_v2,
    (transfer_v2.STAGED_PATH, "verify_staged_bytes_exact_v2"):
        verify_staged_bytes_exact_v2,
    (working_v2.MEMORY_PATH, "verify_working_bytes_peak_exact_v2"):
        verify_working_bytes_peak_exact_v2,
    (working_v2.PROCESS_PATH, "verify_process_launches_exact_v2"):
        verify_process_launches_exact_v2,
}


def verify_shared_resource_source_exact_v2(
    source: Any,
) -> SharedResourceSemanticReplayResultV2:
    """Dispatch one source only through its fixed catalogue verifier."""

    if type(source) is not resolution_v2.SharedResourceLiveSourceV2:
        _fail("semantic replay requires one exact SharedResourceLiveSourceV2")
    contract = _CONTRACT_BY_PATH.get(source.path)
    if contract is None:
        _fail("semantic replay source path is not registered")
    verifier = _DISPATCH.get((source.path, contract.semantic_verifier_key))
    if verifier is None:
        _fail("fixed catalogue verifier dispatch is incomplete")
    return verifier(source)


if set(_CONTRACT_BY_PATH) != {path for path, _key in _DISPATCH}:
    raise RuntimeError("semantic replay dispatch does not cover the exact nine paths")


__all__ = [
    "ALL_NINE_REPLAY_BLOCKER",
    "ALL_NINE_REPLAY_SUPPORTED",
    "ConstructionSharedResourceSemanticReplayV2Error",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SEMANTIC_VERIFIER_V2_DOMAIN",
    "SCHEMA_VERSION",
    "SharedResourceSemanticReplayResultV2",
    "verify_hash_invocations_exact_v2",
    "verify_integrity_checks_exact_v2",
    "verify_mounted_bytes_peak_exact_v2",
    "verify_output_bytes_exact_v2",
    "verify_process_launches_exact_v2",
    "verify_protocol_checks_exact_v2",
    "verify_read_bytes_exact_v2",
    "verify_shared_resource_source_exact_v2",
    "verify_staged_bytes_exact_v2",
    "verify_working_bytes_peak_exact_v2",
]
