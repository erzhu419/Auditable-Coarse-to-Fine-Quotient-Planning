"""Independent directory verifier for a preregistered query-bound campaign."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_campaign_analysis_independent_verifier_v1 as analysis_v1
from acfqp import construction_k7_query_bound_campaign_preregistration_independent_verifier_v1 as prereg_v1
from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as bundle_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_OCCURRENCE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_VERIFICATION_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_VERIFICATION_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.101"
PROFILE_KEY = (
    "construction_k7_query_bound_preregistered_campaign_independent_verifier_v1"
)
PRODUCER_PROFILE_KEY = "construction_k7_query_bound_preregistered_campaign_runner_v1"
SCALAR_GATE_STATUS = "NOT_RUN"
PREREGISTRATION_FILENAME = "CAMPAIGN_PREREGISTRATION.json"
ANALYSIS_FILENAME = "RETROSPECTIVE_ACCOUNTING_ANALYSIS.json"
RESULT_FILENAME = "PREREGISTERED_CAMPAIGN_RESULT.json"
EVENT_FILENAME_TEMPLATE = "{index:04d}_COMMIT_EVENT.json"
OCCURRENCE_DIRECTORY_TEMPLATE = "occurrence-{index:04d}"
INPUT_ROLES = (
    ("SOURCE_TRACE", "source_trace.json"),
    ("BUILD_EPOCH_ENVELOPE", "build_epoch_envelope.json"),
    ("ROOT_QUERY_RESULT", "root_query_result.json"),
    ("RECOVERY_OVERLAY", "recovery_overlay.json"),
    ("RECOVERY_REQUEST", "recovery_request.json"),
)

EVENT_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN
)
OCCURRENCE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_OCCURRENCE_V1_DOMAIN
)
RESULT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_RESULT_V1_DOMAIN
VERIFICATION_PROFILE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_VERIFICATION_PROFILE_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_VERIFICATION_V1_DOMAIN
)
_VERIFICATION_ISSUER = object()


class ConstructionK7QueryBoundPreregisteredCampaignIndependentVerifierV1Error(
    ValueError
):
    """A durable event, registered bundle, vector analysis, or lock diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundPreregisteredCampaignIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundPreregisteredCampaignIndependentVerifierV1Error(
            f"{label} must be one content ID"
        ) from error


def _exact(document: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != fields:
        _fail(f"{label} field set changed")
    return document


def _canonical_file(root: Path, relative: str, label: str) -> tuple[bytes, dict[str, Any]]:
    path = root / relative
    try:
        info = path.stat()
    except OSError as error:
        raise ConstructionK7QueryBoundPreregisteredCampaignIndependentVerifierV1Error(
            f"{label} is absent"
        ) from error
    if (
        path.is_symlink()
        or not path.is_file()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) & 0o177
    ):
        _fail(f"{label} is not one private regular file")
    raw = path.read_bytes()
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundPreregisteredCampaignIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return raw, document


def _root(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_symlink():
        _fail("campaign directory must not be a symbolic link")
    root = candidate.resolve(strict=True)
    info = root.stat()
    if not root.is_dir() or not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
        _fail("campaign directory is not one private real directory")
    return root


EVENT_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "event_index",
    "event_kind",
    "previous_event_id",
    "query_bound_campaign_preregistration_id",
    "subject_id",
    "subject_relative_path",
    "subject_bytes_sha256",
    "subject_byte_count",
    "occurrence_index",
    "logical_occurrence_id",
    "subject_committed_before_event",
    "file_fsync_complete",
    "directory_fsync_complete",
    "official_execution_allowed",
    "campaign_commit_event_id",
}
OCCURRENCE_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "query_bound_campaign_preregistration_id",
    "campaign_workload_spec_id",
    "occurrence_index",
    "preregistered_occurrence_spec_id",
    "logical_occurrence_id",
    "output_directory_name",
    "complete_bundle_verification_id",
    "operational_trace_id",
    "shared_measurement_id",
    "shared_resource_receipt_set_id",
    "work_vector_ids",
    "comparison_vector_ids",
    "actual_projection_proof_ids",
    "io.output_bytes",
    "output_manifest_sha256",
    "output_manifest_byte_count",
    "campaign_commit_event_id",
    "registered_inputs_consumed_exactly_once",
    "construction_terminal_class",
    "construction_terminal_code",
    "scientific_planner_recomputed_by_campaign_verifier",
    "official_execution_allowed",
    "preregistered_campaign_occurrence_id",
}
RESULT_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "query_bound_campaign_preregistration_id",
    "campaign_preregistration_verification_id",
    "campaign_workload_spec_id",
    "runtime_preparation_id",
    "runtime_tree_id",
    "source_closure_id",
    "preregistration_bytes_sha256",
    "preregistration_byte_count",
    "commit_events",
    "executed_occurrences",
    "accounting_analysis_id",
    "accounting_analysis_verification_id",
    "accounting_analysis_bytes_hex",
    "logical_occurrence_count",
    "closure_denominator",
    "certification_coverage_denominator",
    "economics_cost_denominator",
    "campaign_preregistration_present",
    "preregistration_committed_before_first_occurrence",
    "all_registered_occurrences_executed_exactly_once",
    "posthoc_occurrence_deletion_observed",
    "posthoc_occurrence_insertion_observed",
    "registered_scientific_inputs_consumed",
    "embedded_source_archive_bound_to_runtime",
    "scientific_planner_executed_for_every_occurrence",
    "all_occurrence_accounting_bundles_independently_replayed",
    "scientific_planner_recomputed_by_campaign_verifier",
    "accounting_campaign_execution_evidence",
    "scientific_campaign_closure_issued",
    "failure_path_campaign_closure_present",
    "campaign_orchestration_work_vector_present",
    "certificate_coverage_gate_status",
    "counter_completeness_gate_status",
    "workload_economics_gate_status",
    "official_scalar_cost",
    "official_N_break_even",
    "scalar_gate_status",
    "official_execution_allowed",
    "preregistered_campaign_result_id",
}


def _event_document(
    *,
    index: int,
    kind: str,
    previous_event_id: str | None,
    preregistration_id: str,
    subject_id: str,
    subject_relative_path: str,
    subject_raw: bytes,
    occurrence_index: int | None,
    logical_occurrence_id: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_commit_event.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "event_index": index,
        "event_kind": kind,
        "previous_event_id": previous_event_id,
        "query_bound_campaign_preregistration_id": preregistration_id,
        "subject_id": subject_id,
        "subject_relative_path": subject_relative_path,
        "subject_bytes_sha256": hashlib.sha256(subject_raw).hexdigest(),
        "subject_byte_count": len(subject_raw),
        "occurrence_index": occurrence_index,
        "logical_occurrence_id": logical_occurrence_id,
        "subject_committed_before_event": True,
        "file_fsync_complete": True,
        "directory_fsync_complete": True,
        "official_execution_allowed": False,
    }
    return {**payload, "campaign_commit_event_id": content_id(EVENT_DOMAIN, payload)}


def _registered_input_inventory(
    preregistration: dict[str, Any], occurrence_index: int
) -> list[dict[str, Any]]:
    blobs = {
        row["campaign_input_blob_id"]: bytes.fromhex(row["canonical_json_bytes_hex"])
        for row in preregistration["input_blobs"]
    }
    occurrence = preregistration["preregistered_occurrences"][occurrence_index - 1]
    result: list[dict[str, Any]] = []
    for expected_role, expected_filename in INPUT_ROLES:
        source = occurrence["input_roles"][len(result)]
        raw = blobs[source["campaign_input_blob_id"]]
        result.append(
            {
                "role": expected_role,
                "filename": expected_filename,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _occurrence_document(
    *,
    root: Path,
    preregistration: dict[str, Any],
    preregistration_id: str,
    workload_spec_id: str,
    occurrence_index: int,
    commit_event: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    registered = preregistration["preregistered_occurrences"][occurrence_index - 1]
    directory_name = OCCURRENCE_DIRECTORY_TEMPLATE.format(index=occurrence_index)
    directory = root / directory_name
    verification = bundle_v1.verify_query_bound_complete_bundle_directory_v1(directory)
    manifest_raw, _manifest = _canonical_file(
        directory,
        "OUTPUT_MANIFEST.json",
        "occurrence output manifest",
    )
    business_raw, business = _canonical_file(
        directory,
        "BUSINESS_RESULT.json",
        "occurrence business result",
    )
    preparation = business.get("runtime_preparation")
    request = business.get("supervised_request")
    if type(preparation) is not dict or type(request) is not dict:
        _fail("occurrence business result omitted runtime preparation or request")
    expected_inventory = _registered_input_inventory(preregistration, occurrence_index)
    if (
        verification.occurrence_id != registered["logical_occurrence_id"]
        or business.get("occurrence_id") != registered["logical_occurrence_id"]
        or preparation.get("query_bound_runtime_preparation_id")
        != preregistration["runtime_preparation_id"]
        or preparation.get("runtime_manifest", {}).get("runtime_tree_id")
        != preregistration["runtime_tree_id"]
        or preparation.get("source_closure", {}).get("closure_id")
        != preregistration["source_closure_id"]
        or request.get("input_inventory") != expected_inventory
        or hashlib.sha256(business_raw).hexdigest()
        != dict(verification.role_digests)["BUSINESS_RESULT"]
    ):
        _fail("occurrence bundle differs from preregistered source or inputs")
    payload = {
        "schema": "acfqp.construction_k7_query_bound_preregistered_campaign_occurrence.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "query_bound_campaign_preregistration_id": preregistration_id,
        "campaign_workload_spec_id": workload_spec_id,
        "occurrence_index": occurrence_index,
        "preregistered_occurrence_spec_id": registered[
            "preregistered_occurrence_spec_id"
        ],
        "logical_occurrence_id": registered["logical_occurrence_id"],
        "output_directory_name": directory_name,
        "complete_bundle_verification_id": verification.verification_id,
        "operational_trace_id": verification.operational_trace_id,
        "shared_measurement_id": verification.shared_measurement_id,
        "shared_resource_receipt_set_id": verification.shared_receipt_set_id,
        "work_vector_ids": list(verification.work_vector_ids),
        "comparison_vector_ids": list(verification.comparison_vector_ids),
        "actual_projection_proof_ids": list(verification.projection_proof_ids),
        "io.output_bytes": verification.output_bytes,
        "output_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "output_manifest_byte_count": len(manifest_raw),
        "campaign_commit_event_id": commit_event["campaign_commit_event_id"],
        "registered_inputs_consumed_exactly_once": True,
        "construction_terminal_class": "PLAN_CERTIFICATE",
        "construction_terminal_code": "FULL_GROUND_FALLBACK",
        "scientific_planner_recomputed_by_campaign_verifier": False,
        "official_execution_allowed": False,
    }
    row_id = content_id(OCCURRENCE_DOMAIN, payload)
    return {**payload, "preregistered_campaign_occurrence_id": row_id}, verification.verification_id


@dataclass(frozen=True, slots=True)
class QueryBoundPreregisteredCampaignVerificationV1:
    _issuer: InitVar[object]
    verification_profile_id: str
    campaign_result_id: str
    preregistration_id: str
    preregistration_verification_id: str
    workload_spec_id: str
    event_ids: tuple[str, ...]
    occurrence_row_ids: tuple[str, ...]
    bundle_verification_ids: tuple[str, ...]
    accounting_analysis_id: str
    accounting_analysis_verification_id: str
    result_bytes_sha256: str
    result_byte_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or len(self.occurrence_row_ids) < 2
            or len(self.bundle_verification_ids) != len(self.occurrence_row_ids)
            or len(self.event_ids) != len(self.occurrence_row_ids) + 2
            or type(self.result_byte_count) is not int
            or self.result_byte_count <= 0
        ):
            _fail("campaign verification is caller-minted or malformed")
        for value, label in (
            (self.verification_profile_id, "verification profile"),
            (self.campaign_result_id, "campaign result"),
            (self.preregistration_id, "campaign preregistration"),
            (self.preregistration_verification_id, "preregistration verification"),
            (self.workload_spec_id, "campaign workload"),
            (self.accounting_analysis_id, "accounting analysis"),
            (self.accounting_analysis_verification_id, "analysis verification"),
            (self.result_bytes_sha256, "campaign result bytes"),
            *((value, "campaign event") for value in self.event_ids),
            *((value, "campaign occurrence row") for value in self.occurrence_row_ids),
            *((value, "bundle verification") for value in self.bundle_verification_ids),
        ):
            _cid(value, label)
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_preregistered_campaign_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": self.verification_profile_id,
            "preregistered_campaign_result_id": self.campaign_result_id,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "campaign_preregistration_verification_id": self.preregistration_verification_id,
            "campaign_workload_spec_id": self.workload_spec_id,
            "campaign_commit_event_ids": list(self.event_ids),
            "preregistered_campaign_occurrence_ids": list(self.occurrence_row_ids),
            "complete_bundle_verification_ids": list(self.bundle_verification_ids),
            "accounting_analysis_id": self.accounting_analysis_id,
            "accounting_analysis_verification_id": self.accounting_analysis_verification_id,
            "result_bytes_sha256": self.result_bytes_sha256,
            "result_byte_count": self.result_byte_count,
            "producer_modules_imported": False,
            "durable_preregistration_first_sequence_replayed": True,
            "all_registered_occurrence_directories_replayed": True,
            "all_registered_input_inventory_joins_replayed": True,
            "all_vector_prefixes_recomputed": True,
            "scientific_planner_recomputed_by_this_verifier": False,
            "scientific_campaign_closure_issued": False,
            "campaign_orchestration_work_vector_present": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        expected = content_id(VERIFICATION_DOMAIN, self._payload())
        if expected != self._verification_id:
            _fail("campaign verification changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "preregistered_campaign_verification_id": self.verification_id,
        }


def verify_query_bound_preregistered_campaign_directory_v1(
    campaign_directory: str | Path,
) -> QueryBoundPreregisteredCampaignVerificationV1:
    """Replay the preregistration, event chain, bundles, prefixes, and result."""

    root = _root(campaign_directory)
    preregistration_raw, preregistration = _canonical_file(
        root,
        PREREGISTRATION_FILENAME,
        "campaign preregistration",
    )
    prereg_verification = prereg_v1.verify_query_bound_campaign_preregistration_bytes_v1(
        preregistration_raw
    )
    preregistration_id = prereg_verification.preregistration_id
    workload_spec_id = prereg_verification.workload_spec_id
    occurrence_ids = prereg_verification.occurrence_ids
    count = len(occurrence_ids)
    event_documents: list[dict[str, Any]] = []
    previous_event_id: str | None = None
    first_raw = preregistration_raw
    first_expected = _event_document(
        index=1,
        kind="PREREGISTRATION_COMMITTED",
        previous_event_id=None,
        preregistration_id=preregistration_id,
        subject_id=preregistration_id,
        subject_relative_path=PREREGISTRATION_FILENAME,
        subject_raw=first_raw,
        occurrence_index=None,
        logical_occurrence_id=None,
    )
    event_raw, event_claim = _canonical_file(
        root,
        EVENT_FILENAME_TEMPLATE.format(index=1),
        "campaign preregistration commit event",
    )
    if _exact(event_claim, EVENT_FIELDS, "campaign event") != first_expected:
        _fail("campaign preregistration commit event changed")
    del event_raw
    event_documents.append(first_expected)
    previous_event_id = first_expected["campaign_commit_event_id"]
    occurrence_documents: list[dict[str, Any]] = []
    bundle_verification_ids: list[str] = []
    for occurrence_index, occurrence_id in enumerate(occurrence_ids, start=1):
        directory_name = OCCURRENCE_DIRECTORY_TEMPLATE.format(index=occurrence_index)
        manifest_raw, _manifest = _canonical_file(
            root / directory_name,
            "OUTPUT_MANIFEST.json",
            "campaign occurrence output manifest",
        )
        event_index = occurrence_index + 1
        event_expected = _event_document(
            index=event_index,
            kind="OCCURRENCE_COMMITTED",
            previous_event_id=previous_event_id,
            preregistration_id=preregistration_id,
            subject_id="0" * 64,
            subject_relative_path=f"{directory_name}/OUTPUT_MANIFEST.json",
            subject_raw=manifest_raw,
            occurrence_index=occurrence_index,
            logical_occurrence_id=occurrence_id,
        )
        _event_raw, event_claim = _canonical_file(
            root,
            EVENT_FILENAME_TEMPLATE.format(index=event_index),
            "campaign occurrence commit event",
        )
        event_claim = _exact(event_claim, EVENT_FIELDS, "campaign event")
        # The subject is the independently recomputed bundle verification ID;
        # fill it only after replaying the directory.
        occurrence_document, bundle_verification_id = _occurrence_document(
            root=root,
            preregistration=preregistration,
            preregistration_id=preregistration_id,
            workload_spec_id=workload_spec_id,
            occurrence_index=occurrence_index,
            commit_event=event_claim,
        )
        event_expected["subject_id"] = bundle_verification_id
        event_payload = dict(event_expected)
        event_payload.pop("campaign_commit_event_id")
        event_expected["campaign_commit_event_id"] = content_id(
            EVENT_DOMAIN,
            event_payload,
        )
        # Rebuild the row now that the exact event ID is known.
        occurrence_document["campaign_commit_event_id"] = event_expected[
            "campaign_commit_event_id"
        ]
        row_payload = dict(occurrence_document)
        row_payload.pop("preregistered_campaign_occurrence_id")
        occurrence_document["preregistered_campaign_occurrence_id"] = content_id(
            OCCURRENCE_DOMAIN,
            row_payload,
        )
        if event_claim != event_expected:
            _fail("campaign occurrence commit event changed")
        event_documents.append(event_expected)
        occurrence_documents.append(occurrence_document)
        bundle_verification_ids.append(bundle_verification_id)
        previous_event_id = event_expected["campaign_commit_event_id"]
    analysis_raw, _analysis_document = _canonical_file(
        root,
        ANALYSIS_FILENAME,
        "campaign accounting analysis",
    )
    bundle_directories = tuple(
        root / OCCURRENCE_DIRECTORY_TEMPLATE.format(index=index)
        for index in range(1, count + 1)
    )
    analysis_verification = analysis_v1.verify_query_bound_campaign_analysis_bytes_v1(
        analysis_raw,
        bundle_directories=bundle_directories,
    )
    analysis_document = loads_canonical_json(analysis_raw)
    analysis_id = analysis_document["query_bound_campaign_analysis_id"]
    final_event_index = count + 2
    final_event_expected = _event_document(
        index=final_event_index,
        kind="ACCOUNTING_ANALYSIS_COMMITTED",
        previous_event_id=previous_event_id,
        preregistration_id=preregistration_id,
        subject_id=analysis_id,
        subject_relative_path=ANALYSIS_FILENAME,
        subject_raw=analysis_raw,
        occurrence_index=None,
        logical_occurrence_id=None,
    )
    _final_event_raw, final_event_claim = _canonical_file(
        root,
        EVENT_FILENAME_TEMPLATE.format(index=final_event_index),
        "campaign analysis commit event",
    )
    if _exact(final_event_claim, EVENT_FIELDS, "campaign event") != final_event_expected:
        _fail("campaign analysis commit event changed")
    event_documents.append(final_event_expected)
    result_raw, result_claim = _canonical_file(
        root,
        RESULT_FILENAME,
        "preregistered campaign result",
    )
    result_claim = _exact(result_claim, RESULT_FIELDS, "preregistered campaign result")
    payload = {
        "schema": "acfqp.construction_k7_query_bound_preregistered_campaign_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "query_bound_campaign_preregistration_id": preregistration_id,
        "campaign_preregistration_verification_id": prereg_verification.verification_id,
        "campaign_workload_spec_id": workload_spec_id,
        "runtime_preparation_id": prereg_verification.runtime_preparation_id,
        "runtime_tree_id": prereg_verification.runtime_tree_id,
        "source_closure_id": prereg_verification.source_closure_id,
        "preregistration_bytes_sha256": hashlib.sha256(preregistration_raw).hexdigest(),
        "preregistration_byte_count": len(preregistration_raw),
        "commit_events": event_documents,
        "executed_occurrences": occurrence_documents,
        "accounting_analysis_id": analysis_id,
        "accounting_analysis_verification_id": analysis_verification.verification_id,
        "accounting_analysis_bytes_hex": analysis_raw.hex(),
        "logical_occurrence_count": count,
        "closure_denominator": count,
        "certification_coverage_denominator": count,
        "economics_cost_denominator": count,
        "campaign_preregistration_present": True,
        "preregistration_committed_before_first_occurrence": True,
        "all_registered_occurrences_executed_exactly_once": True,
        "posthoc_occurrence_deletion_observed": False,
        "posthoc_occurrence_insertion_observed": False,
        "registered_scientific_inputs_consumed": True,
        "embedded_source_archive_bound_to_runtime": True,
        "scientific_planner_executed_for_every_occurrence": True,
        "all_occurrence_accounting_bundles_independently_replayed": True,
        "scientific_planner_recomputed_by_campaign_verifier": False,
        "accounting_campaign_execution_evidence": True,
        "scientific_campaign_closure_issued": False,
        "failure_path_campaign_closure_present": False,
        "campaign_orchestration_work_vector_present": False,
        "certificate_coverage_gate_status": "NOT_RUN",
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "scalar_gate_status": SCALAR_GATE_STATUS,
        "official_execution_allowed": False,
    }
    result_id = content_id(RESULT_DOMAIN, payload)
    expected_result = {**payload, "preregistered_campaign_result_id": result_id}
    if result_claim != expected_result:
        _fail("preregistered campaign result differs from full directory replay")
    expected_root_entries = {
        PREREGISTRATION_FILENAME,
        ANALYSIS_FILENAME,
        RESULT_FILENAME,
        *(EVENT_FILENAME_TEMPLATE.format(index=index) for index in range(1, count + 3)),
        *(OCCURRENCE_DIRECTORY_TEMPLATE.format(index=index) for index in range(1, count + 1)),
    }
    if {path.name for path in root.iterdir()} != expected_root_entries:
        _fail("campaign root artifact inventory changed")
    verification_profile_payload = {
        "schema": "acfqp.construction_k7_query_bound_preregistered_campaign_verification_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "producer_import_forbidden": True,
        "preregistration_must_be_first_event": True,
        "all_registered_occurrences_required": True,
        "all_bundle_directories_independently_replayed": True,
        "all_vector_prefixes_recomputed": True,
        "scientific_planner_recomputation_required": False,
        "official_execution_allowed": False,
    }
    verification_profile_id = content_id(
        VERIFICATION_PROFILE_DOMAIN,
        verification_profile_payload,
    )
    return QueryBoundPreregisteredCampaignVerificationV1(
        _VERIFICATION_ISSUER,
        verification_profile_id,
        result_id,
        preregistration_id,
        prereg_verification.verification_id,
        workload_spec_id,
        tuple(row["campaign_commit_event_id"] for row in event_documents),
        tuple(
            row["preregistered_campaign_occurrence_id"]
            for row in occurrence_documents
        ),
        tuple(bundle_verification_ids),
        analysis_id,
        analysis_verification.verification_id,
        hashlib.sha256(result_raw).hexdigest(),
        len(result_raw),
    )


__all__ = (
    "ConstructionK7QueryBoundPreregisteredCampaignIndependentVerifierV1Error",
    "QueryBoundPreregisteredCampaignVerificationV1",
    "verify_query_bound_preregistered_campaign_directory_v1",
)
