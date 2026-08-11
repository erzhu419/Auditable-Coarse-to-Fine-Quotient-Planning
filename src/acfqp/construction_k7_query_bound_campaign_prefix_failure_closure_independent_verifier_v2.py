"""Independent replay of nonempty query-bound campaign failure prefixes."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_campaign_preregistration_independent_verifier_v1 as prereg_v1
from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as bundle_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_V2_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_VERIFICATION_PROFILE_V2_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_VERIFICATION_V2_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.104"
PRODUCER_PROFILE_KEY = "construction_k7_query_bound_campaign_prefix_failure_closure_v2"
PROFILE_KEY = (
    "construction_k7_query_bound_campaign_prefix_failure_closure_independent_verifier_v2"
)
CLOSURE_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_V2_DOMAIN
EVENT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN
VERIFICATION_PROFILE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_VERIFICATION_PROFILE_V2_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_VERIFICATION_V2_DOMAIN
)
EXECUTION_DIRECTORY_NAME = "campaign"
FAILURE_FILENAME = "CAMPAIGN_PREFIX_FAILURE_CLOSURE.json"
PREREGISTRATION_FILENAME = "CAMPAIGN_PREREGISTRATION.json"
EVENT_FILENAME_TEMPLATE = "{index:04d}_COMMIT_EVENT.json"
OCCURRENCE_DIRECTORY_TEMPLATE = "occurrence-{index:04d}"
INPUT_ROLES = (
    ("SOURCE_TRACE", "source_trace.json"),
    ("BUILD_EPOCH_ENVELOPE", "build_epoch_envelope.json"),
    ("ROOT_QUERY_RESULT", "root_query_result.json"),
    ("RECOVERY_OVERLAY", "recovery_overlay.json"),
    ("RECOVERY_REQUEST", "recovery_request.json"),
)
_ISSUER = object()


class ConstructionK7QueryBoundCampaignPrefixFailureClosureIndependentVerifierV2Error(
    ValueError
):
    """The completed prefix, pending suffix, or closure changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignPrefixFailureClosureIndependentVerifierV2Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignPrefixFailureClosureIndependentVerifierV2Error(
            f"{label} must be one content ID"
        ) from error


def _private_directory(path: Path, label: str) -> Path:
    if path.is_symlink():
        _fail(f"{label} must not be a symbolic link")
    root = path.resolve(strict=True)
    info = root.stat()
    if (
        not root.is_dir()
        or not stat.S_ISDIR(info.st_mode)
        or stat.S_IMODE(info.st_mode) & 0o077
    ):
        _fail(f"{label} must be one private real directory")
    return root


def _canonical_file(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} is absent or not one regular file")
    info = path.stat()
    if stat.S_IMODE(info.st_mode) & 0o177:
        _fail(f"{label} is not private")
    raw = path.read_bytes()
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignPrefixFailureClosureIndependentVerifierV2Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return raw, document


def _first_event(preregistration_id: str, preregistration_raw: bytes) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_commit_event.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "2.0.101",
        "profile_key": "construction_k7_query_bound_preregistered_campaign_runner_v1",
        "event_index": 1,
        "event_kind": "PREREGISTRATION_COMMITTED",
        "previous_event_id": None,
        "query_bound_campaign_preregistration_id": preregistration_id,
        "subject_id": preregistration_id,
        "subject_relative_path": PREREGISTRATION_FILENAME,
        "subject_bytes_sha256": hashlib.sha256(preregistration_raw).hexdigest(),
        "subject_byte_count": len(preregistration_raw),
        "occurrence_index": None,
        "logical_occurrence_id": None,
        "subject_committed_before_event": True,
        "file_fsync_complete": True,
        "directory_fsync_complete": True,
        "official_execution_allowed": False,
    }
    return {**payload, "campaign_commit_event_id": content_id(EVENT_DOMAIN, payload)}


def _occurrence_event(
    *,
    event_index: int,
    previous_event_id: str,
    preregistration_id: str,
    bundle_verification_id: str,
    directory_name: str,
    manifest_raw: bytes,
    occurrence_index: int,
    logical_occurrence_id: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_commit_event.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "2.0.101",
        "profile_key": "construction_k7_query_bound_preregistered_campaign_runner_v1",
        "event_index": event_index,
        "event_kind": "OCCURRENCE_COMMITTED",
        "previous_event_id": previous_event_id,
        "query_bound_campaign_preregistration_id": preregistration_id,
        "subject_id": bundle_verification_id,
        "subject_relative_path": f"{directory_name}/OUTPUT_MANIFEST.json",
        "subject_bytes_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "subject_byte_count": len(manifest_raw),
        "occurrence_index": occurrence_index,
        "logical_occurrence_id": logical_occurrence_id,
        "subject_committed_before_event": True,
        "file_fsync_complete": True,
        "directory_fsync_complete": True,
        "official_execution_allowed": False,
    }
    return {**payload, "campaign_commit_event_id": content_id(EVENT_DOMAIN, payload)}


def _registered_inventory(
    preregistration: dict[str, Any],
    occurrence_index: int,
) -> list[dict[str, Any]]:
    blobs = {
        row["campaign_input_blob_id"]: bytes.fromhex(row["canonical_json_bytes_hex"])
        for row in preregistration["input_blobs"]
    }
    occurrence = preregistration["preregistered_occurrences"][occurrence_index - 1]
    result: list[dict[str, Any]] = []
    for offset, (role, filename) in enumerate(INPUT_ROLES):
        source = occurrence["input_roles"][offset]
        if source["role"] != role:
            _fail("registered input role order changed")
        raw = blobs[source["campaign_input_blob_id"]]
        result.append(
            {
                "role": role,
                "filename": filename,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _completed_row(
    *,
    registered: dict[str, Any],
    verification: bundle_v1.QueryBoundCompleteBundleVerificationV1,
    event_id: str,
) -> dict[str, Any]:
    return {
        "occurrence_index": registered["occurrence_index"],
        "preregistered_occurrence_spec_id": registered[
            "preregistered_occurrence_spec_id"
        ],
        "logical_occurrence_id": registered["logical_occurrence_id"],
        "failure_position": "COMPLETED_BEFORE_LATER_CAMPAIGN_FAILURE",
        "complete_bundle_verification_id": verification.verification_id,
        "operational_trace_id": verification.operational_trace_id,
        "shared_measurement_id": verification.shared_measurement_id,
        "shared_resource_receipt_set_id": verification.shared_receipt_set_id,
        "work_vector_ids": list(verification.work_vector_ids),
        "comparison_vector_ids": list(verification.comparison_vector_ids),
        "actual_projection_proof_ids": list(verification.projection_proof_ids),
        "io.output_bytes": verification.output_bytes,
        "campaign_commit_event_id": event_id,
        "terminal_scope": "LOGICAL_OCCURRENCE",
        "terminal_class": "PLAN_CERTIFICATE",
        "terminal_code": "FULL_GROUND_FALLBACK",
        "closure_denominator_included": True,
        "certification_denominator_included": True,
        "economics_denominator_included": True,
    }


def _pending_row(registered: dict[str, Any], *, started: bool) -> dict[str, Any]:
    position = "STARTED_WITHOUT_COMMIT" if started else "NOT_STARTED_AFTER_PREFIX_FAILURE"
    reason = (
        "this occurrence began but no complete bundle event committed"
        if started
        else "campaign protocol failure closed before this occurrence began"
    )
    missing = {
        "kind": "NOT_AVAILABLE_DUE_TO_PROTOCOL_FAILURE",
        "reason": reason,
    }
    return {
        "occurrence_index": registered["occurrence_index"],
        "preregistered_occurrence_spec_id": registered[
            "preregistered_occurrence_spec_id"
        ],
        "logical_occurrence_id": registered["logical_occurrence_id"],
        "failure_position": position,
        "complete_bundle_verification_id": dict(missing),
        "occurrence_work_vector_id": dict(missing),
        "terminal_scope": "LOGICAL_OCCURRENCE",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "PROTOCOL_FAILURE",
        "closure_denominator_included": True,
        "certification_denominator_included": True,
        "economics_denominator_included": True,
    }


def _partial_inventory(directory: Path | None) -> list[dict[str, Any]]:
    if directory is None:
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        info = path.stat()
        if (
            path.is_symlink()
            or not path.is_file()
            or not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            _fail("pending occurrence contains a non-private artifact")
        raw = path.read_bytes()
        rows.append(
            {
                "relative_name": path.name,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "mode": stat.S_IMODE(info.st_mode),
            }
        )
    return rows


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignPrefixFailureClosureVerificationV2:
    _issuer: InitVar[object]
    verification_profile_id: str
    closure_id: str
    closure_bytes_sha256: str
    closure_byte_count: int
    preregistration_id: str
    preregistration_verification_id: str
    workload_spec_id: str
    committed_event_ids: tuple[str, ...]
    completed_bundle_verification_ids: tuple[str, ...]
    logical_occurrence_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or len(self.logical_occurrence_ids) < 2
            or not self.completed_bundle_verification_ids
            or len(self.completed_bundle_verification_ids) >= len(self.logical_occurrence_ids)
            or len(self.committed_event_ids)
            != len(self.completed_bundle_verification_ids) + 1
            or type(self.closure_byte_count) is not int
            or self.closure_byte_count <= 0
        ):
            _fail("prefix-failure verification is caller-minted or incomplete")
        for value, label in (
            (self.verification_profile_id, "verification profile"),
            (self.closure_id, "prefix-failure closure"),
            (self.closure_bytes_sha256, "closure bytes"),
            (self.preregistration_id, "campaign preregistration"),
            (self.preregistration_verification_id, "preregistration verification"),
            (self.workload_spec_id, "campaign workload"),
            *((value, "campaign event") for value in self.committed_event_ids),
            *((value, "bundle verification") for value in self.completed_bundle_verification_ids),
            *((value, "logical occurrence") for value in self.logical_occurrence_ids),
        ):
            _cid(value, label)
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_prefix_failure_closure_verification.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": self.verification_profile_id,
            "query_bound_campaign_prefix_failure_closure_id": self.closure_id,
            "closure_bytes_sha256": self.closure_bytes_sha256,
            "closure_byte_count": self.closure_byte_count,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "campaign_preregistration_verification_id": self.preregistration_verification_id,
            "campaign_workload_spec_id": self.workload_spec_id,
            "committed_campaign_event_ids": list(self.committed_event_ids),
            "completed_bundle_verification_ids": list(self.completed_bundle_verification_ids),
            "registered_logical_occurrence_ids": list(self.logical_occurrence_ids),
            "durable_nonempty_prefix_replayed": True,
            "all_completed_bundles_independently_replayed": True,
            "pending_suffix_inventory_replayed": True,
            "full_registered_denominator_recomputed": True,
            "producer_modules_imported": False,
            "portable_failure_cause_authority": False,
            "scientific_campaign_closure_issued": False,
            "campaign_orchestration_work_vector_present": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        expected = content_id(VERIFICATION_DOMAIN, self._payload())
        if expected != self._verification_id:
            _fail("prefix-failure verification changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query_bound_campaign_prefix_failure_closure_verification_id": (
                self.verification_id
            ),
        }


def verify_query_bound_campaign_prefix_failure_closure_bytes_v2(
    closure_bytes: bytes,
    *,
    wrapper_directory: str | Path,
) -> QueryBoundCampaignPrefixFailureClosureVerificationV2:
    """Rebuild the durable completed prefix and retained failed suffix."""

    wrapper = _private_directory(Path(wrapper_directory), "prefix-failure wrapper")
    if {path.name for path in wrapper.iterdir()} != {
        EXECUTION_DIRECTORY_NAME,
        FAILURE_FILENAME,
    }:
        _fail("prefix-failure wrapper inventory changed")
    stored_raw, claimed = _canonical_file(wrapper / FAILURE_FILENAME, "prefix-failure closure")
    if stored_raw != closure_bytes:
        _fail("supplied prefix-failure closure differs from durable bytes")
    execution = _private_directory(
        wrapper / EXECUTION_DIRECTORY_NAME,
        "partial campaign execution",
    )
    prereg_raw, preregistration = _canonical_file(
        execution / PREREGISTRATION_FILENAME,
        "campaign preregistration",
    )
    prereg_verification = prereg_v1.verify_query_bound_campaign_preregistration_bytes_v1(
        prereg_raw
    )
    _first_raw, first_claim = _canonical_file(
        execution / EVENT_FILENAME_TEMPLATE.format(index=1),
        "campaign preregistration event",
    )
    first = _first_event(prereg_verification.preregistration_id, prereg_raw)
    if first_claim != first:
        _fail("campaign preregistration event changed")
    events = [first]
    completed_rows: list[dict[str, Any]] = []
    bundle_ids: list[str] = []
    registered_rows = preregistration["preregistered_occurrences"]
    for registered in registered_rows:
        occurrence_index = registered["occurrence_index"]
        event_index = occurrence_index + 1
        event_path = execution / EVENT_FILENAME_TEMPLATE.format(index=event_index)
        if not event_path.exists():
            break
        directory_name = OCCURRENCE_DIRECTORY_TEMPLATE.format(index=occurrence_index)
        directory = execution / directory_name
        verification = bundle_v1.verify_query_bound_complete_bundle_directory_v1(directory)
        manifest_raw, _manifest = _canonical_file(
            directory / "OUTPUT_MANIFEST.json",
            "completed occurrence manifest",
        )
        _business_raw, business = _canonical_file(
            directory / "BUSINESS_RESULT.json",
            "completed occurrence business result",
        )
        preparation = business.get("runtime_preparation")
        request = business.get("supervised_request")
        if (
            type(preparation) is not dict
            or type(request) is not dict
            or verification.occurrence_id != registered["logical_occurrence_id"]
            or business.get("occurrence_id") != registered["logical_occurrence_id"]
            or preparation.get("query_bound_runtime_preparation_id")
            != preregistration["runtime_preparation_id"]
            or preparation.get("runtime_manifest", {}).get("runtime_tree_id")
            != preregistration["runtime_tree_id"]
            or preparation.get("source_closure", {}).get("closure_id")
            != preregistration["source_closure_id"]
            or request.get("input_inventory")
            != _registered_inventory(preregistration, occurrence_index)
        ):
            _fail("completed bundle crossed its preregistered source or inputs")
        _event_raw, event_claim = _canonical_file(event_path, "occurrence commit event")
        event = _occurrence_event(
            event_index=event_index,
            previous_event_id=events[-1]["campaign_commit_event_id"],
            preregistration_id=prereg_verification.preregistration_id,
            bundle_verification_id=verification.verification_id,
            directory_name=directory_name,
            manifest_raw=manifest_raw,
            occurrence_index=occurrence_index,
            logical_occurrence_id=registered["logical_occurrence_id"],
        )
        if event_claim != event:
            _fail("completed occurrence event changed")
        events.append(event)
        bundle_ids.append(verification.verification_id)
        completed_rows.append(
            _completed_row(
                registered=registered,
                verification=verification,
                event_id=event["campaign_commit_event_id"],
            )
        )
    completed = len(completed_rows)
    total = len(registered_rows)
    if not (1 <= completed < total):
        _fail("V2 requires a nonempty incomplete occurrence prefix")
    pending_name = OCCURRENCE_DIRECTORY_TEMPLATE.format(index=completed + 1)
    pending_path = execution / pending_name
    pending_directory = (
        _private_directory(pending_path, "pending occurrence")
        if pending_path.exists()
        else None
    )
    rows = list(completed_rows)
    for registered in registered_rows[completed:]:
        rows.append(
            _pending_row(
                registered,
                started=(
                    registered["occurrence_index"] == completed + 1
                    and pending_directory is not None
                ),
            )
        )
    expected_entries = {
        PREREGISTRATION_FILENAME,
        *(EVENT_FILENAME_TEMPLATE.format(index=i) for i in range(1, completed + 2)),
        *(OCCURRENCE_DIRECTORY_TEMPLATE.format(index=i) for i in range(1, completed + 1)),
    }
    if pending_directory is not None:
        expected_entries.add(pending_name)
    if {path.name for path in execution.iterdir()} != expected_entries:
        _fail("partial campaign root inventory changed")
    inventory = _partial_inventory(pending_directory)
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_prefix_failure_closure.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "query_bound_campaign_preregistration_id": prereg_verification.preregistration_id,
        "campaign_preregistration_verification_id": prereg_verification.verification_id,
        "campaign_workload_spec_id": prereg_verification.workload_spec_id,
        "preregistration_bytes_sha256": hashlib.sha256(prereg_raw).hexdigest(),
        "preregistration_byte_count": len(prereg_raw),
        "committed_campaign_event_ids": [
            event["campaign_commit_event_id"] for event in events
        ],
        "completed_occurrence_count": completed,
        "pending_occurrence_directory": (
            pending_name if pending_directory is not None else None
        ),
        "pending_occurrence_inventory": inventory,
        "occurrence_rows": rows,
        "logical_occurrence_count": total,
        "closure_denominator": total,
        "certification_coverage_denominator": total,
        "economics_cost_denominator": total,
        "plan_certificate_count": completed,
        "infeasibility_certificate_count": 0,
        "noncertificate_count": total - completed,
        "construction_certificate_coverage_status": "FAIL",
        "official_certificate_coverage_gate_status": "NOT_RUN",
        "all_registered_occurrences_retained": True,
        "completed_occurrence_certificates_retained": True,
        "campaign_denominator_closure_issued": True,
        "failure_path_campaign_closure_present": True,
        "scientific_campaign_closure_issued": False,
        "campaign_orchestration_work_vector_present": False,
        "official_run_valid": False,
        "portable_failure_cause_authority": False,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "scalar_gate_status": "NOT_RUN",
        "official_execution_allowed": False,
    }
    closure_id = content_id(CLOSURE_DOMAIN, payload)
    expected = {**payload, "query_bound_campaign_prefix_failure_closure_id": closure_id}
    if claimed != expected:
        _fail("campaign prefix-failure closure differs from independent replay")
    profile_payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_prefix_failure_closure_verification_profile.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "producer_import_forbidden": True,
        "nonempty_completed_prefix_required": True,
        "incomplete_registered_suffix_required": True,
        "all_completed_bundles_replayed": True,
        "full_registered_denominator_required": True,
        "portable_failure_cause_authority_required": False,
        "official_execution_allowed": False,
    }
    profile_id = content_id(VERIFICATION_PROFILE_DOMAIN, profile_payload)
    return QueryBoundCampaignPrefixFailureClosureVerificationV2(
        _ISSUER,
        profile_id,
        closure_id,
        hashlib.sha256(closure_bytes).hexdigest(),
        len(closure_bytes),
        prereg_verification.preregistration_id,
        prereg_verification.verification_id,
        prereg_verification.workload_spec_id,
        tuple(event["campaign_commit_event_id"] for event in events),
        tuple(bundle_ids),
        prereg_verification.occurrence_ids,
    )


__all__ = (
    "ConstructionK7QueryBoundCampaignPrefixFailureClosureIndependentVerifierV2Error",
    "QueryBoundCampaignPrefixFailureClosureVerificationV2",
    "verify_query_bound_campaign_prefix_failure_closure_bytes_v2",
)
