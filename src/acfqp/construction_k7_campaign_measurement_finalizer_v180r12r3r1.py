"""Pure finalization of the V180r12r3r1 campaign-measurement terminal.

This module performs no filesystem, process, cgroup, or measurement effects.
It accepts the already closed raw event/evidence population, replays the frozen
ledger kernel, joins the exact OS receipt subset, and materializes only a
``PENDING_INDEPENDENT_REPLAY`` terminal.  It is not a counter-PASS authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_campaign_measurement_ledger_v180r12r3r1 as ledger
from acfqp import construction_k7_domain_registry_extension_v180r12r3r1 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "1.0.0"
SUBJECT_RESULT_RUNTIME_BYTE_CAP = ledger.SUBJECT_RESULT_RUNTIME_BYTE_CAP
FRAME_BYTE_CAP = ledger.FRAME_BYTE_CAP
TERMINAL_SCHEMA = "acfqp.campaign_measurement_terminal.v180r12r3r1"
EVIDENCE_INVENTORY_BUNDLE_SCHEMA = (
    "acfqp.campaign_evidence_inventory_bundle.v180r12r3r1"
)
OS_RECEIPT_BUNDLE_SCHEMA = "acfqp.campaign_os_receipt_bundle.v180r12r3r1"
SUCCESS_ARTIFACT_ORDER = (
    "evidence_inventory",
    "execution_closure",
    "os_receipt",
    "ledger_closure",
)
SUCCESS_ARTIFACT_SCHEMA_ROWS = (
    (
        "evidence_inventory",
        EVIDENCE_INVENTORY_BUNDLE_SCHEMA,
        "campaign_evidence_inventory_bundle_id",
        "campaign_evidence_inventory_bundle",
    ),
    (
        "execution_closure",
        "acfqp.campaign_execution_closure.v180r12r3r1",
        "campaign_execution_closure_id",
        "campaign_execution_closure",
    ),
    (
        "os_receipt",
        OS_RECEIPT_BUNDLE_SCHEMA,
        "campaign_os_receipt_bundle_id",
        "campaign_os_receipt_bundle",
    ),
    (
        "ledger_closure",
        "acfqp.campaign_measurement_ledger_closure.v180r12r3r1",
        "campaign_ledger_closure_id",
        "campaign_ledger_closure",
    ),
)
EVIDENCE_INVENTORY_BUNDLE_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "protocol_id",
        "authorization_id",
        "attempt_id",
        "evidence_document_count",
        "evidence_document_type_counts",
        "ordered_evidence_document_ids",
        "evidence_documents",
        "campaign_evidence_inventory_bundle_id",
    }
)
OS_RECEIPT_BUNDLE_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "protocol_id",
        "authorization_id",
        "attempt_id",
        "campaign_evidence_inventory_bundle_id",
        "os_receipt_document_count",
        "os_receipt_schema_counts",
        "ordered_os_receipt_ids",
        "os_receipt_documents",
        "campaign_os_receipt_bundle_id",
    }
)
TERMINAL_COUNTER_STATUS = "PENDING_INDEPENDENT_REPLAY"
TERMINAL_COUNTER_GATE = "PENDING_INDEPENDENT_REPLAY"
SUCCESS_EVENT_COUNT = 625
SUCCESS_EVIDENCE_DOCUMENT_COUNT = 328

# These twelve documents are the explicit OS boundary duplicated from the
# 328-document inventory.  Their identities remain the registered evidence
# identities; no unregistered wrapper identity is minted.
OS_EVIDENCE_SCHEMA_COUNTS: Mapping[str, int] = {
    "acfqp.campaign_memfd_stage_receipt.v180r12r3r1": 2,
    "acfqp.campaign_fd_visibility_receipt.v180r12r3r1": 4,
    "acfqp.campaign_pidfd_birth_receipt.v180r12r3r1": 2,
    "acfqp.campaign_pidfd_reap_receipt.v180r12r3r1": 2,
    "acfqp.campaign_cgroup_topology_receipt.v180r12r3r1": 1,
    "acfqp.campaign_cgroup_observation_receipt.v180r12r3r1": 1,
}
OS_EVIDENCE_DOCUMENT_COUNT = sum(OS_EVIDENCE_SCHEMA_COUNTS.values())

_IDENTITY_FIELD_BY_SCHEMA = {
    "acfqp.campaign_memfd_stage_receipt.v180r12r3r1": "memfd_stage_receipt_id",
    "acfqp.campaign_fd_visibility_receipt.v180r12r3r1": "fd_visibility_receipt_id",
    "acfqp.campaign_pidfd_birth_receipt.v180r12r3r1": "pidfd_birth_receipt_id",
    "acfqp.campaign_pidfd_reap_receipt.v180r12r3r1": "pidfd_reap_receipt_id",
    "acfqp.campaign_cgroup_topology_receipt.v180r12r3r1": (
        "cgroup_topology_receipt_id"
    ),
    "acfqp.campaign_cgroup_observation_receipt.v180r12r3r1": (
        "cgroup_observation_receipt_id"
    ),
}


class ConstructionK7CampaignMeasurementFinalizerV180R12R3R1Error(ValueError):
    """The closed raw campaign cannot materialize the pending terminal."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CampaignMeasurementFinalizerV180R12R3R1Error(message)


def _cid(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256 identity")
    return value


def _canonical_document(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty exact bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7CampaignMeasurementFinalizerV180R12R3R1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} must be one canonical JSON object")
    return document


def _canonical_document_sequence(
    values: Sequence[bytes], *, expected_count: int, label: str
) -> tuple[dict[str, Any], ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        _fail(f"{label} must be one exact byte sequence")
    if len(values) != expected_count:
        _fail(f"{label} must contain exactly {expected_count} documents")
    return tuple(
        _canonical_document(value, f"{label} row {index}")
        for index, value in enumerate(values)
    )


def _os_document_identity(document: Mapping[str, Any]) -> str:
    schema = document.get("schema")
    identity_field = _IDENTITY_FIELD_BY_SCHEMA.get(schema)
    if identity_field is None:
        _fail("OS receipt schema is outside the exact twelve-document boundary")
    return _cid(document.get(identity_field), "OS receipt identity")


def _validate_os_receipts(
    os_receipt_documents: Sequence[bytes],
    inventory: ledger.CampaignEvidenceInventoryV180R12R3R1,
) -> tuple[dict[str, Any], ...]:
    supplied = _canonical_document_sequence(
        os_receipt_documents,
        expected_count=OS_EVIDENCE_DOCUMENT_COUNT,
        label="campaign OS receipt documents",
    )
    supplied_ids = tuple(_os_document_identity(row) for row in supplied)
    if supplied_ids != tuple(sorted(set(supplied_ids))):
        _fail("campaign OS receipt identities must be sorted and unique")
    supplied_counts = {
        schema: sum(row.get("schema") == schema for row in supplied)
        for schema in OS_EVIDENCE_SCHEMA_COUNTS
    }
    if supplied_counts != dict(OS_EVIDENCE_SCHEMA_COUNTS):
        _fail("campaign OS receipt exact typed denominator changed")
    expected = tuple(
        sorted(
            (
                document
                for document in inventory.documents
                if document.get("schema") in OS_EVIDENCE_SCHEMA_COUNTS
            ),
            key=_os_document_identity,
        )
    )
    if supplied != expected:
        _fail("campaign OS receipts differ from the registered evidence inventory")
    return supplied


def _evidence_inventory_bundle_bytes(
    campaign_ledger: ledger.CampaignMeasurementLedgerV180R12R3R1,
) -> bytes:
    inventory = campaign_ledger.evidence_inventory
    documents = list(inventory.documents)
    ordered_ids = [identity for identity, _raw in inventory.rows]
    payload = {
        "schema": EVIDENCE_INVENTORY_BUNDLE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "protocol_id": campaign_ledger.state.protocol_id,
        "authorization_id": campaign_ledger.state.authorization_id,
        "attempt_id": campaign_ledger.state.attempt_id,
        "evidence_document_count": SUCCESS_EVIDENCE_DOCUMENT_COUNT,
        "evidence_document_type_counts": dict(ledger.EVIDENCE_DOCUMENT_TYPE_COUNTS),
        "ordered_evidence_document_ids": ordered_ids,
        "evidence_documents": documents,
    }
    document = {
        **payload,
        "campaign_evidence_inventory_bundle_id": (
            domains.extension_content_id_v180r12r3r1(
                domains.CONSTRUCTION_K7_CAMPAIGN_EVIDENCE_INVENTORY_BUNDLE_V180R12R3R1_DOMAIN,
                payload,
            )
        ),
    }
    return canonical_json_bytes(document)


def _os_receipt_bundle_bytes(
    campaign_ledger: ledger.CampaignMeasurementLedgerV180R12R3R1,
    os_receipts: Sequence[Mapping[str, Any]],
    *,
    evidence_inventory_bundle_id: str,
) -> bytes:
    payload = {
        "schema": OS_RECEIPT_BUNDLE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "protocol_id": campaign_ledger.state.protocol_id,
        "authorization_id": campaign_ledger.state.authorization_id,
        "attempt_id": campaign_ledger.state.attempt_id,
        "campaign_evidence_inventory_bundle_id": _cid(
            evidence_inventory_bundle_id,
            "campaign evidence inventory bundle ID",
        ),
        "os_receipt_document_count": OS_EVIDENCE_DOCUMENT_COUNT,
        "os_receipt_schema_counts": dict(OS_EVIDENCE_SCHEMA_COUNTS),
        "ordered_os_receipt_ids": [
            _os_document_identity(row) for row in os_receipts
        ],
        "os_receipt_documents": [dict(row) for row in os_receipts],
    }
    document = {
        **payload,
        "campaign_os_receipt_bundle_id": domains.extension_content_id_v180r12r3r1(
            domains.CONSTRUCTION_K7_CAMPAIGN_OS_RECEIPT_BUNDLE_V180R12R3R1_DOMAIN,
            payload,
        ),
    }
    return canonical_json_bytes(document)


def _success_artifact_bytes(
    campaign_ledger: ledger.CampaignMeasurementLedgerV180R12R3R1,
    os_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, bytes]:
    inventory_raw = _evidence_inventory_bundle_bytes(campaign_ledger)
    inventory_document = _canonical_document(
        inventory_raw, "campaign evidence inventory bundle"
    )
    execution_document = campaign_ledger.evidence_inventory.one(
        "acfqp.campaign_execution_closure.v180r12r3r1"
    )
    execution_raw = canonical_json_bytes(execution_document)
    os_raw = _os_receipt_bundle_bytes(
        campaign_ledger,
        os_receipts,
        evidence_inventory_bundle_id=inventory_document[
            "campaign_evidence_inventory_bundle_id"
        ],
    )
    artifacts = {
        "evidence_inventory": inventory_raw,
        "execution_closure": execution_raw,
        "os_receipt": os_raw,
        "ledger_closure": campaign_ledger.canonical_bytes,
    }
    if tuple(artifacts) != SUCCESS_ARTIFACT_ORDER:
        _fail("campaign success artifact order changed")
    return artifacts


def _terminal_payload(
    campaign_ledger: ledger.CampaignMeasurementLedgerV180R12R3R1,
    os_receipts: Sequence[Mapping[str, Any]],
    success_artifacts: Mapping[str, bytes],
    *,
    output_bytes_fixed_point: int,
) -> dict[str, Any]:
    closure = campaign_ledger.to_document()
    attempt_record = campaign_ledger.evidence_inventory.one(
        "acfqp.campaign_attempt_record.v180r12r3r1"
    )
    source_manifest = campaign_ledger.evidence_inventory.one(
        "acfqp.campaign_native_zero_source_manifest.v180r12r3r1"
    )
    closure_bytes = success_artifacts["ledger_closure"]
    inventory_bytes = success_artifacts["evidence_inventory"]
    inventory_document = _canonical_document(
        inventory_bytes, "campaign evidence inventory bundle"
    )
    execution_bytes = success_artifacts["execution_closure"]
    os_bundle_bytes = success_artifacts["os_receipt"]
    os_bundle_document = _canonical_document(
        os_bundle_bytes, "campaign OS receipt bundle"
    )
    return {
        "schema": TERMINAL_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "scope": ledger.CAMPAIGN_SCOPE_KIND,
        "scope_model": ledger.CAMPAIGN_SCOPE_MODEL,
        "protocol_id": campaign_ledger.state.protocol_id,
        "authorization_id": campaign_ledger.state.authorization_id,
        "authorization_evidence_id": attempt_record[
            "authorization_evidence_id"
        ],
        "attempt_id": campaign_ledger.state.attempt_id,
        "prelaunch_materialization_terminal_id": attempt_record[
            "prelaunch_materialization_terminal_id"
        ],
        "prelaunch_launch_manifest_sha256": attempt_record[
            "prelaunch_launch_manifest_sha256"
        ],
        "precompiled_source_bundle_sha256": source_manifest[
            "precompiled_source_bundle_sha256"
        ],
        "prelaunch_launch_rule_id": attempt_record[
            "prelaunch_launch_rule_id"
        ],
        "measurement_launch_attempt_id": attempt_record[
            "measurement_launch_attempt_id"
        ],
        "subject_id": campaign_ledger.subject_id,
        "campaign_operation_manifest_id": closure[
            "campaign_operation_manifest_id"
        ],
        "native_zero_source_manifest_id": closure[
            "native_zero_source_manifest_id"
        ],
        "native_zero_import_inventory_id": closure[
            "native_zero_import_inventory_id"
        ],
        "campaign_execution_closure_id": closure[
            "campaign_execution_closure_id"
        ],
        "campaign_execution_closure_byte_count": len(execution_bytes),
        "campaign_execution_closure_sha256": hashlib.sha256(
            execution_bytes
        ).hexdigest(),
        "campaign_evidence_inventory_bundle_id": inventory_document[
            "campaign_evidence_inventory_bundle_id"
        ],
        "campaign_evidence_inventory_bundle_byte_count": len(inventory_bytes),
        "campaign_evidence_inventory_bundle_sha256": hashlib.sha256(
            inventory_bytes
        ).hexdigest(),
        "campaign_os_receipt_bundle_id": os_bundle_document[
            "campaign_os_receipt_bundle_id"
        ],
        "campaign_os_receipt_bundle_byte_count": len(os_bundle_bytes),
        "campaign_os_receipt_bundle_sha256": hashlib.sha256(
            os_bundle_bytes
        ).hexdigest(),
        "campaign_ledger_closure_id": campaign_ledger.campaign_ledger_closure_id,
        "campaign_ledger_closure_byte_count": len(closure_bytes),
        "campaign_ledger_closure_sha256": hashlib.sha256(closure_bytes).hexdigest(),
        "campaign_measurement_ledger": closure,
        "os_receipt_documents": [dict(row) for row in os_receipts],
        "os_receipt_ids": [_os_document_identity(row) for row in os_receipts],
        "os_receipt_schema_counts": dict(OS_EVIDENCE_SCHEMA_COUNTS),
        "event_count": SUCCESS_EVENT_COUNT,
        "evidence_document_count": SUCCESS_EVIDENCE_DOCUMENT_COUNT,
        "os_receipt_document_count": OS_EVIDENCE_DOCUMENT_COUNT,
        "campaign_path_receipt_count": 9,
        "campaign_counter_record_count": 9,
        "campaign_work_vector_count": 1,
        "campaign_comparison_vector_count": 1,
        "campaign_projection_proof_count": 1,
        "campaign_native_zero_attestation_count": 1,
        "predecessor_occurrence_authoritative_receipt_count": 90,
        "successor_campaign_authoritative_receipt_count": 9,
        "combined_successor_authoritative_receipt_count": 99,
        "authoritative_receipt_arithmetic_90_plus_9_equals_99": True,
        "raw_event_evidence_and_os_receipts_replayed": True,
        "route_free_campaign_accounting": True,
        "all_nine_campaign_paths_strictly_positive": True,
        "independent_native_zero_attestation_present": True,
        "independent_verification_present": False,
        "V180R12R3R1_CAMPAIGN_COUNTER_CLOSURE_STATUS": TERMINAL_COUNTER_STATUS,
        "COUNTER_COMPLETENESS_GATE": TERMINAL_COUNTER_GATE,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "v180r13_weight_agnostic_economics_input_ready": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "scientific_success_claimed": False,
        "output_bytes_fixed_point": output_bytes_fixed_point,
    }


TERMINAL_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "scope",
        "scope_model",
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "attempt_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "precompiled_source_bundle_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
        "subject_id",
        "campaign_operation_manifest_id",
        "native_zero_source_manifest_id",
        "native_zero_import_inventory_id",
        "campaign_execution_closure_id",
        "campaign_execution_closure_byte_count",
        "campaign_execution_closure_sha256",
        "campaign_evidence_inventory_bundle_id",
        "campaign_evidence_inventory_bundle_byte_count",
        "campaign_evidence_inventory_bundle_sha256",
        "campaign_os_receipt_bundle_id",
        "campaign_os_receipt_bundle_byte_count",
        "campaign_os_receipt_bundle_sha256",
        "campaign_ledger_closure_id",
        "campaign_ledger_closure_byte_count",
        "campaign_ledger_closure_sha256",
        "campaign_measurement_ledger",
        "os_receipt_documents",
        "os_receipt_ids",
        "os_receipt_schema_counts",
        "event_count",
        "evidence_document_count",
        "os_receipt_document_count",
        "campaign_path_receipt_count",
        "campaign_counter_record_count",
        "campaign_work_vector_count",
        "campaign_comparison_vector_count",
        "campaign_projection_proof_count",
        "campaign_native_zero_attestation_count",
        "predecessor_occurrence_authoritative_receipt_count",
        "successor_campaign_authoritative_receipt_count",
        "combined_successor_authoritative_receipt_count",
        "authoritative_receipt_arithmetic_90_plus_9_equals_99",
        "raw_event_evidence_and_os_receipts_replayed",
        "route_free_campaign_accounting",
        "all_nine_campaign_paths_strictly_positive",
        "independent_native_zero_attestation_present",
        "independent_verification_present",
        "V180R12R3R1_CAMPAIGN_COUNTER_CLOSURE_STATUS",
        "COUNTER_COMPLETENESS_GATE",
        "WORKLOAD_ECONOMICS_GATE",
        "SCALAR_CALIBRATION_GATE",
        "BREAK_EVEN_GATE",
        "OFFICIAL_EXECUTION_GATE",
        "v180r13_weight_agnostic_economics_input_ready",
        "official_scalar_cost",
        "official_N_break_even",
        "official_execution_allowed",
        "scientific_success_claimed",
        "output_bytes_fixed_point",
        "campaign_measurement_terminal_id",
    }
)


@dataclass(frozen=True, slots=True)
class PendingCampaignMeasurementTerminalV180R12R3R1:
    """Canonical pending terminal; it deliberately cannot assert counter PASS."""

    _canonical_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        document = _canonical_document(
            self._canonical_bytes, "pending campaign measurement terminal"
        )
        payload = dict(document)
        identity = _cid(
            payload.pop("campaign_measurement_terminal_id", None),
            "campaign measurement terminal ID",
        )
        if (
            frozenset(document) != TERMINAL_FIELDS
            or document.get("schema") != TERMINAL_SCHEMA
            or document.get("schema_version") != SCHEMA_VERSION
            or document.get("output_bytes_fixed_point") != len(self._canonical_bytes)
            or identity
            != domains.extension_content_id_v180r12r3r1(
                domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R3R1_DOMAIN,
                payload,
            )
            or document.get("V180R12R3R1_CAMPAIGN_COUNTER_CLOSURE_STATUS")
            != TERMINAL_COUNTER_STATUS
            or document.get("COUNTER_COMPLETENESS_GATE") != TERMINAL_COUNTER_GATE
            or document.get("independent_verification_present") is not False
        ):
            _fail("pending campaign measurement terminal identity or gate changed")
        _success_artifact_bytes_from_terminal(document)

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_bytes

    @property
    def document(self) -> dict[str, Any]:
        return _canonical_document(
            self._canonical_bytes, "pending campaign measurement terminal"
        )

    @property
    def terminal_id(self) -> str:
        return self.document["campaign_measurement_terminal_id"]

    @property
    def evidence_inventory_bundle_bytes(self) -> bytes:
        return _success_artifact_bytes_from_terminal(self.document)[
            "evidence_inventory"
        ]

    @property
    def execution_closure_bytes(self) -> bytes:
        return _success_artifact_bytes_from_terminal(self.document)[
            "execution_closure"
        ]

    @property
    def os_receipt_bundle_bytes(self) -> bytes:
        return _success_artifact_bytes_from_terminal(self.document)["os_receipt"]

    @property
    def ledger_closure_bytes(self) -> bytes:
        return _success_artifact_bytes_from_terminal(self.document)[
            "ledger_closure"
        ]

    @property
    def success_artifact_bytes(self) -> Mapping[str, bytes]:
        return _success_artifact_bytes_from_terminal(self.document)


def _success_artifact_bytes_from_terminal(
    terminal: Mapping[str, Any],
) -> dict[str, bytes]:
    closure = terminal.get("campaign_measurement_ledger")
    os_receipts = terminal.get("os_receipt_documents")
    if type(closure) is not dict or type(os_receipts) is not list:
        _fail("pending terminal lacks its exact success artifact population")
    try:
        state = ledger.replay_campaign_event_chain_v180r12r3r1(
            closure["events"],
            max_event_count=closure["max_event_count"],
            max_event_byte_count=closure["max_event_byte_count"],
            max_ledger_byte_count=closure["max_ledger_byte_count"],
        )
        inventory = ledger.CampaignEvidenceInventoryV180R12R3R1.from_documents(
            closure["evidence_documents"]
        )
        campaign_ledger = ledger.derive_campaign_measurement_ledger_v180r12r3r1(
            state,
            subject_id=closure["subject_id"],
            evidence_documents_by_id=inventory.documents_by_id,
            expected_native_zero_source_manifest_id=closure[
                "native_zero_source_manifest_id"
            ],
            expected_native_zero_import_inventory_id=closure[
                "native_zero_import_inventory_id"
            ],
        )
    except (KeyError, TypeError, ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error) as error:
        raise ConstructionK7CampaignMeasurementFinalizerV180R12R3R1Error(
            "pending terminal success artifacts cannot be independently rematerialized"
        ) from error
    artifacts = _success_artifact_bytes(campaign_ledger, os_receipts)
    inventory = _canonical_document(
        artifacts["evidence_inventory"], "campaign evidence inventory bundle"
    )
    os_bundle = _canonical_document(
        artifacts["os_receipt"], "campaign OS receipt bundle"
    )
    execution = _canonical_document(
        artifacts["execution_closure"], "campaign execution closure"
    )
    ledger_closure = _canonical_document(
        artifacts["ledger_closure"], "campaign ledger closure"
    )
    facts = (
        (
            "campaign_evidence_inventory_bundle_id",
            inventory["campaign_evidence_inventory_bundle_id"],
            "campaign_evidence_inventory_bundle_byte_count",
            "campaign_evidence_inventory_bundle_sha256",
            artifacts["evidence_inventory"],
        ),
        (
            "campaign_execution_closure_id",
            execution["campaign_execution_closure_id"],
            "campaign_execution_closure_byte_count",
            "campaign_execution_closure_sha256",
            artifacts["execution_closure"],
        ),
        (
            "campaign_os_receipt_bundle_id",
            os_bundle["campaign_os_receipt_bundle_id"],
            "campaign_os_receipt_bundle_byte_count",
            "campaign_os_receipt_bundle_sha256",
            artifacts["os_receipt"],
        ),
        (
            "campaign_ledger_closure_id",
            ledger_closure["campaign_ledger_closure_id"],
            "campaign_ledger_closure_byte_count",
            "campaign_ledger_closure_sha256",
            artifacts["ledger_closure"],
        ),
    )
    if any(
        terminal.get(id_field) != expected_id
        or terminal.get(count_field) != len(raw)
        or terminal.get(sha_field) != hashlib.sha256(raw).hexdigest()
        for id_field, expected_id, count_field, sha_field, raw in facts
    ):
        _fail("pending terminal success artifact facts changed")
    return artifacts


def _materialize_terminal_bytes(
    campaign_ledger: ledger.CampaignMeasurementLedgerV180R12R3R1,
    os_receipts: Sequence[Mapping[str, Any]],
) -> bytes:
    success_artifacts = _success_artifact_bytes(campaign_ledger, os_receipts)
    fixed_point = 0
    for _iteration in range(32):
        payload = _terminal_payload(
            campaign_ledger,
            os_receipts,
            success_artifacts,
            output_bytes_fixed_point=fixed_point,
        )
        document = {
            **payload,
            "campaign_measurement_terminal_id": (
                domains.extension_content_id_v180r12r3r1(
                    domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R3R1_DOMAIN,
                    payload,
                )
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == fixed_point:
            return raw
        fixed_point = len(raw)
    _fail("pending campaign measurement terminal byte fixed point did not converge")


def finalize_campaign_measurement_terminal_v180r12r3r1(
    *,
    event_documents: Sequence[bytes],
    evidence_documents: Sequence[bytes],
    os_receipt_documents: Sequence[bytes],
    expected_protocol_id: str,
    expected_authorization_id: str,
    expected_authorization_evidence_id: str,
    expected_attempt_id: str,
    expected_prelaunch_materialization_terminal_id: str,
    expected_prelaunch_launch_manifest_sha256: str,
    expected_precompiled_source_bundle_sha256: str,
    expected_prelaunch_launch_rule_id: str,
    expected_measurement_launch_attempt_id: str,
    expected_subject_id: str,
    expected_native_zero_source_manifest_id: str,
    expected_native_zero_import_inventory_id: str,
    max_event_count: int,
    max_event_byte_count: int,
    max_ledger_byte_count: int,
) -> PendingCampaignMeasurementTerminalV180R12R3R1:
    """Replay closed raw inputs and return a pending terminal without effects."""

    for value, label in (
        (expected_protocol_id, "expected protocol ID"),
        (expected_authorization_id, "expected authorization ID"),
        (
            expected_authorization_evidence_id,
            "expected authorization-evidence ID",
        ),
        (expected_attempt_id, "expected attempt ID"),
        (
            expected_prelaunch_materialization_terminal_id,
            "expected prelaunch materialization-terminal ID",
        ),
        (
            expected_prelaunch_launch_manifest_sha256,
            "expected prelaunch launch-manifest SHA-256",
        ),
        (
            expected_precompiled_source_bundle_sha256,
            "expected precompiled source-bundle SHA-256",
        ),
        (
            expected_prelaunch_launch_rule_id,
            "expected prelaunch launch-rule ID",
        ),
        (
            expected_measurement_launch_attempt_id,
            "expected measurement launch-attempt ID",
        ),
        (expected_subject_id, "expected subject ID"),
        (
            expected_native_zero_source_manifest_id,
            "expected native-zero source manifest ID",
        ),
        (
            expected_native_zero_import_inventory_id,
            "expected native-zero import inventory ID",
        ),
    ):
        _cid(value, label)
    raw_events = _canonical_document_sequence(
        event_documents,
        expected_count=SUCCESS_EVENT_COUNT,
        label="campaign event documents",
    )
    raw_evidence = _canonical_document_sequence(
        evidence_documents,
        expected_count=SUCCESS_EVIDENCE_DOCUMENT_COUNT,
        label="campaign evidence documents",
    )
    try:
        state = ledger.replay_campaign_event_chain_v180r12r3r1(
            raw_events,
            max_event_count=max_event_count,
            max_event_byte_count=max_event_byte_count,
            max_ledger_byte_count=max_ledger_byte_count,
        )
        inventory = ledger.CampaignEvidenceInventoryV180R12R3R1.from_documents(
            raw_evidence
        )
    except ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error as error:
        raise ConstructionK7CampaignMeasurementFinalizerV180R12R3R1Error(
            "campaign raw population failed exact pending-terminal replay"
        ) from error
    if (
        state.protocol_id != expected_protocol_id
        or state.authorization_id != expected_authorization_id
        or state.attempt_id != expected_attempt_id
    ):
        _fail("campaign event context differs from the expected one-shot identity")
    if tuple(raw_evidence) != inventory.documents:
        _fail("campaign evidence documents must be sorted by registered identity")
    os_receipts = _validate_os_receipts(os_receipt_documents, inventory)
    try:
        campaign_ledger = ledger.derive_campaign_measurement_ledger_v180r12r3r1(
            state,
            subject_id=expected_subject_id,
            evidence_documents_by_id=inventory.documents_by_id,
            expected_native_zero_source_manifest_id=(
                expected_native_zero_source_manifest_id
            ),
            expected_native_zero_import_inventory_id=(
                expected_native_zero_import_inventory_id
            ),
        )
    except ledger.ConstructionK7CampaignMeasurementLedgerV180R12R3R1Error as error:
        raise ConstructionK7CampaignMeasurementFinalizerV180R12R3R1Error(
            "campaign raw ledger failed exact pending-terminal replay"
        ) from error
    attempt_record = campaign_ledger.evidence_inventory.one(
        "acfqp.campaign_attempt_record.v180r12r3r1"
    )
    source_manifest = campaign_ledger.evidence_inventory.one(
        "acfqp.campaign_native_zero_source_manifest.v180r12r3r1"
    )
    if (
        attempt_record.get("authorization_evidence_id")
        != expected_authorization_evidence_id
        or attempt_record.get("prelaunch_materialization_terminal_id")
        != expected_prelaunch_materialization_terminal_id
        or attempt_record.get("prelaunch_launch_manifest_sha256")
        != expected_prelaunch_launch_manifest_sha256
        or attempt_record.get("prelaunch_launch_rule_id")
        != expected_prelaunch_launch_rule_id
        or attempt_record.get("measurement_launch_attempt_id")
        != expected_measurement_launch_attempt_id
        or source_manifest.get("precompiled_source_bundle_sha256")
        != expected_precompiled_source_bundle_sha256
    ):
        _fail("campaign attempt authorization/source-bound transport provenance changed")
    return PendingCampaignMeasurementTerminalV180R12R3R1(
        _materialize_terminal_bytes(campaign_ledger, os_receipts)
    )


__all__ = (
    "FRAME_BYTE_CAP",
    "ConstructionK7CampaignMeasurementFinalizerV180R12R3R1Error",
    "EVIDENCE_INVENTORY_BUNDLE_FIELDS",
    "EVIDENCE_INVENTORY_BUNDLE_SCHEMA",
    "OS_EVIDENCE_DOCUMENT_COUNT",
    "OS_EVIDENCE_SCHEMA_COUNTS",
    "OS_RECEIPT_BUNDLE_FIELDS",
    "OS_RECEIPT_BUNDLE_SCHEMA",
    "SUCCESS_ARTIFACT_ORDER",
    "SUCCESS_ARTIFACT_SCHEMA_ROWS",
    "SUBJECT_RESULT_RUNTIME_BYTE_CAP",
    "PendingCampaignMeasurementTerminalV180R12R3R1",
    "SUCCESS_EVENT_COUNT",
    "SUCCESS_EVIDENCE_DOCUMENT_COUNT",
    "TERMINAL_COUNTER_GATE",
    "TERMINAL_COUNTER_STATUS",
    "TERMINAL_FIELDS",
    "TERMINAL_SCHEMA",
    "finalize_campaign_measurement_terminal_v180r12r3r1",
)
