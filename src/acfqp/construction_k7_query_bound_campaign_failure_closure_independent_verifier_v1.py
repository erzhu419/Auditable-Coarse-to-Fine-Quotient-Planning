"""Independent replay of bounded query-bound campaign failure closures."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_campaign_preregistration_independent_verifier_v1 as prereg_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_VERIFICATION_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.103"
PRODUCER_PROFILE_KEY = "construction_k7_query_bound_campaign_failure_closure_v1"
PROFILE_KEY = (
    "construction_k7_query_bound_campaign_failure_closure_independent_verifier_v1"
)
CLOSURE_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_V1_DOMAIN
EVENT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN
VERIFICATION_PROFILE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_VERIFICATION_PROFILE_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_VERIFICATION_V1_DOMAIN
)
EXECUTION_DIRECTORY_NAME = "campaign"
PREREGISTRATION_FILENAME = "CAMPAIGN_PREREGISTRATION.json"
EVENT_FILENAME = "0001_COMMIT_EVENT.json"
FAILURE_FILENAME = "CAMPAIGN_FAILURE_CLOSURE.json"
_ISSUER = object()


class ConstructionK7QueryBoundCampaignFailureClosureIndependentVerifierV1Error(
    ValueError
):
    """The durable incomplete prefix or failure closure changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignFailureClosureIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignFailureClosureIndependentVerifierV1Error(
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
        raise ConstructionK7QueryBoundCampaignFailureClosureIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return raw, document


def _first_event(
    preregistration_id: str,
    preregistration_bytes: bytes,
) -> dict[str, Any]:
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
        "subject_bytes_sha256": hashlib.sha256(preregistration_bytes).hexdigest(),
        "subject_byte_count": len(preregistration_bytes),
        "occurrence_index": None,
        "logical_occurrence_id": None,
        "subject_committed_before_event": True,
        "file_fsync_complete": True,
        "directory_fsync_complete": True,
        "official_execution_allowed": False,
    }
    return {**payload, "campaign_commit_event_id": content_id(EVENT_DOMAIN, payload)}


def _partial_inventory(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        info = path.stat()
        if (
            path.is_symlink()
            or not path.is_file()
            or not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            _fail("partial occurrence contains a non-regular artifact")
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


def _missing(reason: str) -> dict[str, str]:
    return {
        "kind": "NOT_AVAILABLE_DUE_TO_PROTOCOL_FAILURE",
        "reason": reason,
    }


def _occurrence_rows(preregistration: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in preregistration["preregistered_occurrences"]:
        started = row["occurrence_index"] == 1
        position = (
            "STARTED_WITHOUT_COMMIT"
            if started
            else "NOT_STARTED_AFTER_CAMPAIGN_FAILURE"
        )
        reason = (
            "the first occurrence began but no complete bundle event committed"
            if started
            else "campaign protocol failure closed before this occurrence began"
        )
        result.append(
            {
                "occurrence_index": row["occurrence_index"],
                "preregistered_occurrence_spec_id": row[
                    "preregistered_occurrence_spec_id"
                ],
                "logical_occurrence_id": row["logical_occurrence_id"],
                "failure_position": position,
                "complete_bundle_verification_id": _missing(reason),
                "occurrence_work_vector_id": _missing(reason),
                "terminal_scope": "LOGICAL_OCCURRENCE",
                "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
                "terminal_code": "PROTOCOL_FAILURE",
                "closure_denominator_included": True,
                "certification_denominator_included": True,
                "economics_denominator_included": True,
            }
        )
    return result


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignFailureClosureVerificationV1:
    _issuer: InitVar[object]
    verification_profile_id: str
    closure_id: str
    closure_bytes_sha256: str
    closure_byte_count: int
    preregistration_id: str
    preregistration_verification_id: str
    workload_spec_id: str
    first_event_id: str
    logical_occurrence_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or len(self.logical_occurrence_ids) < 2
            or type(self.closure_byte_count) is not int
            or self.closure_byte_count <= 0
        ):
            _fail("campaign failure verification is caller-minted or incomplete")
        for value, label in (
            (self.verification_profile_id, "verification profile"),
            (self.closure_id, "failure closure"),
            (self.closure_bytes_sha256, "failure closure bytes"),
            (self.preregistration_id, "campaign preregistration"),
            (self.preregistration_verification_id, "preregistration verification"),
            (self.workload_spec_id, "campaign workload"),
            (self.first_event_id, "first commit event"),
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
            "schema": "acfqp.construction_k7_query_bound_campaign_failure_closure_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": self.verification_profile_id,
            "query_bound_campaign_failure_closure_id": self.closure_id,
            "closure_bytes_sha256": self.closure_bytes_sha256,
            "closure_byte_count": self.closure_byte_count,
            "query_bound_campaign_preregistration_id": self.preregistration_id,
            "campaign_preregistration_verification_id": self.preregistration_verification_id,
            "campaign_workload_spec_id": self.workload_spec_id,
            "first_commit_event_id": self.first_event_id,
            "registered_logical_occurrence_ids": list(self.logical_occurrence_ids),
            "durable_preregistration_prefix_replayed": True,
            "partial_occurrence_inventory_replayed": True,
            "full_registered_denominator_recomputed": True,
            "noncertificate_classification_recomputed": True,
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
            _fail("campaign failure verification changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query_bound_campaign_failure_closure_verification_id": (
                self.verification_id
            ),
        }


def verify_query_bound_campaign_failure_closure_bytes_v1(
    closure_bytes: bytes,
    *,
    wrapper_directory: str | Path,
) -> QueryBoundCampaignFailureClosureVerificationV1:
    """Replay the durable first-occurrence failure prefix and denominator."""

    wrapper = _private_directory(Path(wrapper_directory), "failure wrapper")
    if {path.name for path in wrapper.iterdir()} != {
        EXECUTION_DIRECTORY_NAME,
        FAILURE_FILENAME,
    }:
        _fail("failure wrapper inventory changed")
    stored_raw, claimed = _canonical_file(
        wrapper / FAILURE_FILENAME,
        "campaign failure closure",
    )
    if stored_raw != closure_bytes:
        _fail("supplied failure closure differs from the durable closure")
    execution = _private_directory(
        wrapper / EXECUTION_DIRECTORY_NAME,
        "partial campaign execution",
    )
    if {path.name for path in execution.iterdir()} != {
        PREREGISTRATION_FILENAME,
        EVENT_FILENAME,
        "occurrence-0001",
    }:
        _fail("partial campaign execution inventory changed")
    prereg_raw, preregistration = _canonical_file(
        execution / PREREGISTRATION_FILENAME,
        "campaign preregistration",
    )
    prereg_verification = prereg_v1.verify_query_bound_campaign_preregistration_bytes_v1(
        prereg_raw
    )
    event_raw, event = _canonical_file(execution / EVENT_FILENAME, "first commit event")
    expected_event = _first_event(prereg_verification.preregistration_id, prereg_raw)
    if event != expected_event:
        _fail("first commit event changed")
    occurrence_directory = _private_directory(
        execution / "occurrence-0001",
        "partial first occurrence",
    )
    inventory = _partial_inventory(occurrence_directory)
    rows = _occurrence_rows(preregistration)
    count = len(rows)
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_failure_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "query_bound_campaign_preregistration_id": prereg_verification.preregistration_id,
        "campaign_preregistration_verification_id": prereg_verification.verification_id,
        "campaign_workload_spec_id": prereg_verification.workload_spec_id,
        "preregistration_bytes_sha256": hashlib.sha256(prereg_raw).hexdigest(),
        "preregistration_byte_count": len(prereg_raw),
        "first_commit_event_id": event["campaign_commit_event_id"],
        "first_commit_event_sha256": hashlib.sha256(event_raw).hexdigest(),
        "first_commit_event_byte_count": len(event_raw),
        "supported_failure_phase": "BEFORE_FIRST_OCCURRENCE_COMMIT",
        "failure_witness_kind": "IN_PROCESS_RUNNER_EXCEPTION_AND_DURABLE_INCOMPLETE_PREFIX",
        "portable_failure_cause_authority": False,
        "partial_occurrence_directory": "occurrence-0001",
        "partial_occurrence_inventory": inventory,
        "occurrence_rows": rows,
        "logical_occurrence_count": count,
        "closure_denominator": count,
        "certification_coverage_denominator": count,
        "economics_cost_denominator": count,
        "plan_certificate_count": 0,
        "infeasibility_certificate_count": 0,
        "noncertificate_count": count,
        "construction_certificate_coverage_status": "FAIL",
        "official_certificate_coverage_gate_status": "NOT_RUN",
        "all_registered_occurrences_retained": True,
        "campaign_denominator_closure_issued": True,
        "failure_path_campaign_closure_present": True,
        "scientific_campaign_closure_issued": False,
        "campaign_orchestration_work_vector_present": False,
        "official_run_valid": False,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "scalar_gate_status": "NOT_RUN",
        "official_execution_allowed": False,
    }
    closure_id = content_id(CLOSURE_DOMAIN, payload)
    expected = {**payload, "query_bound_campaign_failure_closure_id": closure_id}
    if claimed != expected:
        _fail("campaign failure closure differs from independent replay")
    profile_payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_failure_closure_verification_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "producer_import_forbidden": True,
        "bounded_failure_phase": "BEFORE_FIRST_OCCURRENCE_COMMIT",
        "durable_preregistration_prefix_required": True,
        "full_registered_denominator_required": True,
        "portable_failure_cause_authority_required": False,
        "official_execution_allowed": False,
    }
    profile_id = content_id(VERIFICATION_PROFILE_DOMAIN, profile_payload)
    return QueryBoundCampaignFailureClosureVerificationV1(
        _ISSUER,
        profile_id,
        closure_id,
        hashlib.sha256(closure_bytes).hexdigest(),
        len(closure_bytes),
        prereg_verification.preregistration_id,
        prereg_verification.verification_id,
        prereg_verification.workload_spec_id,
        event["campaign_commit_event_id"],
        prereg_verification.occurrence_ids,
    )


__all__ = (
    "ConstructionK7QueryBoundCampaignFailureClosureIndependentVerifierV1Error",
    "QueryBoundCampaignFailureClosureVerificationV1",
    "verify_query_bound_campaign_failure_closure_bytes_v1",
)
