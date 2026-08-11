"""Independent bytes verifier for retrospective query-bound campaign analysis."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from itertools import permutations
import hashlib
import math
from pathlib import Path
import stat
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.accounting_v1 import ReducerEnum, SHARED_AXES
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as bundle_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_SPEC_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_VERIFICATION_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_VECTOR_PREFIX_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_query_bound_campaign_analysis_independent_verifier_v1"
PRODUCER_PROFILE_KEY = "construction_k7_query_bound_campaign_analysis_v1"
PROPOSED_CONTRACT_VERSION = "2.0.99"
ANALYSIS_MODE = "RETROSPECTIVE_ACCOUNTING_ONLY_NOT_PREREGISTERED"
SCALAR_GATE_STATUS = "NOT_RUN"
MAX_EXPLICIT_PERMUTATIONS = 100_000
INPUT_ROLE_ORDER = (
    "SOURCE_TRACE",
    "BUILD_EPOCH_ENVELOPE",
    "ROOT_QUERY_RESULT",
    "RECOVERY_OVERLAY",
    "RECOVERY_REQUEST",
)

SPEC_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_SPEC_V1_DOMAIN
ROW_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
PREFIX_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_VECTOR_PREFIX_V1_DOMAIN
ANALYSIS_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_V1_DOMAIN
VERIFICATION_PROFILE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_VERIFICATION_PROFILE_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_VERIFICATION_V1_DOMAIN
)

_VERIFICATION_ISSUER = object()


class ConstructionK7QueryBoundCampaignAnalysisIndependentVerifierV1Error(ValueError):
    """The analysis bytes or one independently replayed occurrence diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignAnalysisIndependentVerifierV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignAnalysisIndependentVerifierV1Error(
            f"{label} must be one content ID"
        ) from error


def _exact(document: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != fields:
        _fail(f"{label} field set changed")
    return document


def _replay(document: dict[str, Any], id_field: str, domain: str, label: str) -> str:
    payload = dict(document)
    observed = payload.pop(id_field, None)
    if observed != content_id(domain, payload):
        _fail(f"{label} content ID changed")
    return _cid(observed, label)


def _canonical(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail("campaign analysis bytes are absent")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignAnalysisIndependentVerifierV1Error(
            "campaign analysis bytes are not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("campaign analysis bytes are not one canonical object")
    return document


def _read_role(directory: Path, role: str) -> tuple[bytes, dict[str, Any]]:
    if directory.is_symlink():
        _fail("campaign occurrence directory must not be a symbolic link")
    root = directory.resolve(strict=True)
    info = root.stat()
    if root.is_symlink() or not root.is_dir() or stat.S_IMODE(info.st_mode) & 0o077:
        _fail("campaign occurrence directory is not private and real")
    path = root / f"{role}.json"
    item = path.stat()
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(item.st_mode) & 0o177:
        _fail(f"campaign {role} role is not one private regular file")
    raw = path.read_bytes()
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"campaign {role} role is not canonical JSON")
    return raw, document


SPEC_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "analysis_mode",
    "comparison_profile_id",
    "ordered_logical_occurrence_ids",
    "logical_occurrence_count",
    "permutation_cap",
    "campaign_preregistration_present",
    "posthoc_occurrence_deletion_allowed",
    "official_scalar_cost",
    "official_N_break_even",
    "scalar_gate_status",
    "official_execution_allowed",
    "campaign_analysis_spec_id",
}
ROW_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "campaign_analysis_spec_id",
    "occurrence_index",
    "logical_occurrence_id",
    "complete_bundle_verification_id",
    "operational_trace_id",
    "shared_measurement_id",
    "shared_resource_receipt_set_id",
    "runtime_preparation_id",
    "runtime_tree_id",
    "source_closure_id",
    "source_trace_sha256",
    "build_epoch_envelope_sha256",
    "work_vector_ids",
    "comparison_vector_ids",
    "actual_projection_proof_ids",
    "occurrence_comparison_values",
    "io.output_bytes",
    "role_digests",
    "construction_terminal_class",
    "construction_terminal_code",
    "scientific_planner_recomputed_by_campaign",
    "official_execution_allowed",
    "campaign_occurrence_row_id",
}
PREFIX_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "campaign_analysis_spec_id",
    "comparison_profile_id",
    "full_order",
    "prefix_length",
    "prefix_occurrence_ids",
    "values",
    "official_scalar_cost",
    "official_N_break_even",
    "scalar_gate_status",
    "campaign_vector_prefix_id",
}
ANALYSIS_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "analysis_mode",
    "campaign_analysis_spec",
    "campaign_analysis_spec_id",
    "comparison_profile_id",
    "occurrence_rows",
    "vector_prefix_totals",
    "logical_occurrence_count",
    "closure_denominator",
    "certification_coverage_denominator",
    "economics_cost_denominator",
    "enumerated_order_count",
    "order_enumeration_complete",
    "observed_construction_plan_terminal_count",
    "independently_recomputed_scientific_plan_certificate_count",
    "shared_build_epoch_input_digest_consistent",
    "shared_runtime_tree_and_source_closure_consistent",
    "all_occurrence_accounting_bundles_independently_replayed",
    "scientific_planner_recomputed_by_campaign",
    "source_bytes_embedded_or_externally_anchored",
    "accounting_campaign_analysis_only",
    "campaign_preregistration_present",
    "scientific_campaign_closure_issued",
    "certificate_coverage_gate_status",
    "counter_completeness_gate_status",
    "workload_economics_gate_status",
    "official_scalar_cost",
    "official_N_break_even",
    "scalar_gate_status",
    "official_execution_allowed",
    "query_bound_campaign_analysis_id",
}


def _verify_spec(document: Any) -> tuple[str, tuple[str, ...], int, str]:
    spec = _exact(document, SPEC_FIELDS, "campaign analysis spec")
    spec_id = _replay(spec, "campaign_analysis_spec_id", SPEC_DOMAIN, "campaign analysis spec")
    occurrences = spec["ordered_logical_occurrence_ids"]
    count = spec["logical_occurrence_count"]
    cap = spec["permutation_cap"]
    profile = registry_v6.official_comparison_profile_v6(
        registry_v6.official_counter_registry_v6()
    )
    if (
        spec["schema"] != "acfqp.construction_k7_query_bound_campaign_analysis_spec.v1"
        or spec["schema_version"] != SCHEMA_VERSION
        or spec["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or spec["profile_key"] != PRODUCER_PROFILE_KEY
        or spec["analysis_mode"] != ANALYSIS_MODE
        or spec["comparison_profile_id"] != profile.comparison_profile_id
        or type(occurrences) is not list
        or type(count) is not int
        or count != len(occurrences)
        or count < 2
        or len(set(occurrences)) != count
        or type(cap) is not int
        or not (math.factorial(count) <= cap <= MAX_EXPLICIT_PERMUTATIONS)
        or spec["campaign_preregistration_present"] is not False
        or spec["posthoc_occurrence_deletion_allowed"] is not False
        or spec["official_scalar_cost"] is not None
        or spec["official_N_break_even"] is not None
        or spec["scalar_gate_status"] != SCALAR_GATE_STATUS
        or spec["official_execution_allowed"] is not False
    ):
        _fail("campaign analysis spec semantics changed")
    for occurrence_id in occurrences:
        _cid(occurrence_id, "registered occurrence")
    return spec_id, tuple(occurrences), cap, profile.comparison_profile_id


def _axis_values(rows: Any, label: str) -> tuple[tuple[str, int], ...]:
    if type(rows) is not list:
        _fail(f"{label} must be one list")
    values: list[tuple[str, int]] = []
    for candidate in rows:
        row = _exact(candidate, {"axis", "value"}, f"{label} row")
        if type(row["value"]) is not int or row["value"] < 0:
            _fail(f"{label} value is invalid")
        values.append((row["axis"], row["value"]))
    if tuple(axis for axis, _value in values) != SHARED_AXES:
        _fail(f"{label} axis order changed")
    return tuple(values)


def _row_document(
    *,
    spec_id: str,
    expected_occurrence_id: str,
    index: int,
    directory: str | Path,
) -> tuple[dict[str, Any], tuple[tuple[str, int], ...]]:
    root = Path(directory)
    verification = bundle_v1.verify_query_bound_complete_bundle_directory_v1(root)
    business_raw, business = _read_role(root, "BUSINESS_RESULT")
    comparison_raw, comparison = _read_role(root, "COMPARISON_VECTOR")
    digests = dict(verification.role_digests)
    if (
        verification.occurrence_id != expected_occurrence_id
        or hashlib.sha256(business_raw).hexdigest() != digests["BUSINESS_RESULT"]
        or hashlib.sha256(comparison_raw).hexdigest() != digests["COMPARISON_VECTOR"]
    ):
        _fail("campaign bundle crossed its expected occurrence or role digest")
    preparation = business.get("runtime_preparation")
    request = business.get("supervised_request")
    if type(preparation) is not dict or type(request) is not dict:
        _fail("campaign business result omitted its preparation or request")
    manifest = preparation.get("runtime_manifest")
    source = preparation.get("source_closure")
    inventory = request.get("input_inventory")
    if type(manifest) is not dict or type(source) is not dict or type(inventory) is not list:
        _fail("campaign runtime or input identity is malformed")
    by_role: dict[str, dict[str, Any]] = {}
    for candidate in inventory:
        row = _exact(candidate, {"role", "filename", "byte_count", "sha256"}, "campaign input row")
        if row["role"] in by_role or type(row["byte_count"]) is not int or row["byte_count"] <= 0:
            _fail("campaign input inventory is duplicated or invalid")
        _cid(row["sha256"], "campaign input digest")
        by_role[row["role"]] = row
    if tuple(by_role) != INPUT_ROLE_ORDER:
        _fail("campaign input role order changed")
    values = _axis_values(
        comparison.get("occurrence_reducer_exact_comparison_values"),
        "occurrence comparison aggregate",
    )
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_occurrence_row.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "campaign_analysis_spec_id": spec_id,
        "occurrence_index": index,
        "logical_occurrence_id": verification.occurrence_id,
        "complete_bundle_verification_id": verification.verification_id,
        "operational_trace_id": verification.operational_trace_id,
        "shared_measurement_id": verification.shared_measurement_id,
        "shared_resource_receipt_set_id": verification.shared_receipt_set_id,
        "runtime_preparation_id": _cid(preparation.get("query_bound_runtime_preparation_id"), "runtime preparation"),
        "runtime_tree_id": _cid(manifest.get("runtime_tree_id"), "runtime tree"),
        "source_closure_id": _cid(source.get("closure_id"), "source closure"),
        "source_trace_sha256": by_role["SOURCE_TRACE"]["sha256"],
        "build_epoch_envelope_sha256": by_role["BUILD_EPOCH_ENVELOPE"]["sha256"],
        "work_vector_ids": list(verification.work_vector_ids),
        "comparison_vector_ids": list(verification.comparison_vector_ids),
        "actual_projection_proof_ids": list(verification.projection_proof_ids),
        "occurrence_comparison_values": [
            {"axis": axis, "value": value} for axis, value in values
        ],
        "io.output_bytes": verification.output_bytes,
        "role_digests": [
            {"artifact_role": role, "bytes_sha256": digest}
            for role, digest in verification.role_digests
        ],
        "construction_terminal_class": "PLAN_CERTIFICATE",
        "construction_terminal_code": "FULL_GROUND_FALLBACK",
        "scientific_planner_recomputed_by_campaign": False,
        "official_execution_allowed": False,
    }
    row_id = content_id(ROW_DOMAIN, payload)
    return {**payload, "campaign_occurrence_row_id": row_id}, values


def _prefix_documents(
    *,
    spec_id: str,
    comparison_profile_id: str,
    occurrence_ids: tuple[str, ...],
    values_by_occurrence: Mapping[str, tuple[tuple[str, int], ...]],
) -> list[dict[str, Any]]:
    profile = registry_v6.official_comparison_profile_v6(
        registry_v6.official_counter_registry_v6()
    )
    reducers = {axis.name: axis.reducer for axis in profile.axes}
    result: list[dict[str, Any]] = []
    for order in permutations(occurrence_ids):
        current = {axis: 0 for axis in SHARED_AXES}
        for length, occurrence_id in enumerate(order, start=1):
            source = dict(values_by_occurrence[occurrence_id])
            for axis in SHARED_AXES:
                current[axis] = (
                    current[axis] + source[axis]
                    if reducers[axis] is ReducerEnum.SUM
                    else max(current[axis], source[axis])
                )
            payload = {
                "schema": "acfqp.construction_k7_query_bound_campaign_vector_prefix.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": PRODUCER_PROFILE_KEY,
                "campaign_analysis_spec_id": spec_id,
                "comparison_profile_id": comparison_profile_id,
                "full_order": list(order),
                "prefix_length": length,
                "prefix_occurrence_ids": list(order[:length]),
                "values": [
                    {"axis": axis, "value": current[axis]} for axis in SHARED_AXES
                ],
                "official_scalar_cost": None,
                "official_N_break_even": None,
                "scalar_gate_status": SCALAR_GATE_STATUS,
            }
            result.append(
                {
                    **payload,
                    "campaign_vector_prefix_id": content_id(PREFIX_DOMAIN, payload),
                }
            )
    return sorted(result, key=lambda row: (row["prefix_length"], row["full_order"]))


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignAnalysisVerificationV1:
    _issuer: InitVar[object]
    verification_profile_id: str
    campaign_analysis_id: str
    campaign_analysis_spec_id: str
    occurrence_ids: tuple[str, ...]
    occurrence_row_ids: tuple[str, ...]
    vector_prefix_ids: tuple[str, ...]
    bundle_verification_ids: tuple[str, ...]
    analysis_bytes_sha256: str
    analysis_byte_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or len(self.occurrence_ids) < 2
            or len(set(self.occurrence_ids)) != len(self.occurrence_ids)
            or len(self.occurrence_row_ids) != len(self.occurrence_ids)
            or len(self.bundle_verification_ids) != len(self.occurrence_ids)
            or type(self.analysis_byte_count) is not int
            or self.analysis_byte_count <= 0
        ):
            _fail("campaign analysis verification is caller-minted or malformed")
        for value, label in (
            (self.verification_profile_id, "verification profile"),
            (self.campaign_analysis_id, "campaign analysis"),
            (self.campaign_analysis_spec_id, "campaign analysis spec"),
            (self.analysis_bytes_sha256, "analysis bytes digest"),
            *((value, "occurrence") for value in self.occurrence_ids),
            *((value, "occurrence row") for value in self.occurrence_row_ids),
            *((value, "vector prefix") for value in self.vector_prefix_ids),
            *((value, "bundle verification") for value in self.bundle_verification_ids),
        ):
            _cid(value, label)
        object.__setattr__(self, "_verification_id", content_id(VERIFICATION_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_analysis_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": self.verification_profile_id,
            "query_bound_campaign_analysis_id": self.campaign_analysis_id,
            "campaign_analysis_spec_id": self.campaign_analysis_spec_id,
            "ordered_logical_occurrence_ids": list(self.occurrence_ids),
            "campaign_occurrence_row_ids": list(self.occurrence_row_ids),
            "campaign_vector_prefix_ids": list(self.vector_prefix_ids),
            "complete_bundle_verification_ids": list(self.bundle_verification_ids),
            "analysis_bytes_sha256": self.analysis_bytes_sha256,
            "analysis_byte_count": self.analysis_byte_count,
            "producer_module_imported": False,
            "all_occurrence_bundles_independently_replayed": True,
            "all_vector_prefixes_recomputed": True,
            "campaign_preregistration_present": False,
            "scientific_campaign_closure_issued": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "scalar_gate_status": SCALAR_GATE_STATUS,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        expected = content_id(VERIFICATION_DOMAIN, self._payload())
        if expected != self._verification_id:
            _fail("campaign analysis verification changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_analysis_verification_id": self.verification_id}


def verify_query_bound_campaign_analysis_bytes_v1(
    analysis_bytes: bytes,
    *,
    bundle_directories: Sequence[str | Path],
) -> QueryBoundCampaignAnalysisVerificationV1:
    analysis = _exact(_canonical(analysis_bytes), ANALYSIS_FIELDS, "campaign analysis")
    analysis_id = _replay(
        analysis,
        "query_bound_campaign_analysis_id",
        ANALYSIS_DOMAIN,
        "campaign analysis",
    )
    spec_id, occurrence_ids, _cap, comparison_profile_id = _verify_spec(
        analysis["campaign_analysis_spec"]
    )
    directories = tuple(bundle_directories)
    if len(directories) != len(occurrence_ids):
        _fail("campaign verification bundle count differs from denominator")
    expected_rows: list[dict[str, Any]] = []
    values_by_occurrence: dict[str, tuple[tuple[str, int], ...]] = {}
    for index, (occurrence_id, directory) in enumerate(
        zip(occurrence_ids, directories, strict=True), start=1
    ):
        row, values = _row_document(
            spec_id=spec_id,
            expected_occurrence_id=occurrence_id,
            index=index,
            directory=directory,
        )
        expected_rows.append(row)
        values_by_occurrence[occurrence_id] = values
    expected_prefixes = _prefix_documents(
        spec_id=spec_id,
        comparison_profile_id=comparison_profile_id,
        occurrence_ids=occurrence_ids,
        values_by_occurrence=values_by_occurrence,
    )
    rows = analysis["occurrence_rows"]
    prefixes = analysis["vector_prefix_totals"]
    if type(rows) is not list or any(type(row) is not dict or set(row) != ROW_FIELDS for row in rows):
        _fail("campaign occurrence row inventory changed")
    if type(prefixes) is not list or any(type(row) is not dict or set(row) != PREFIX_FIELDS for row in prefixes):
        _fail("campaign prefix inventory changed")
    if rows != expected_rows or prefixes != expected_prefixes:
        _fail("campaign rows or vector prefixes differ from bundle replay")
    count = len(occurrence_ids)
    shared_fields = (
        "runtime_preparation_id",
        "runtime_tree_id",
        "source_closure_id",
        "source_trace_sha256",
        "build_epoch_envelope_sha256",
    )
    if any(len({row[field] for row in rows}) != 1 for field in shared_fields):
        _fail("campaign shared runtime or BuildEpoch identity changed")
    if (
        analysis["schema"] != "acfqp.construction_k7_query_bound_campaign_analysis.v1"
        or analysis["schema_version"] != SCHEMA_VERSION
        or analysis["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or analysis["profile_key"] != PRODUCER_PROFILE_KEY
        or analysis["analysis_mode"] != ANALYSIS_MODE
        or analysis["campaign_analysis_spec_id"] != spec_id
        or analysis["comparison_profile_id"] != comparison_profile_id
        or analysis["logical_occurrence_count"] != count
        or analysis["closure_denominator"] != count
        or analysis["certification_coverage_denominator"] != count
        or analysis["economics_cost_denominator"] != count
        or analysis["enumerated_order_count"] != math.factorial(count)
        or analysis["order_enumeration_complete"] is not True
        or analysis["observed_construction_plan_terminal_count"] != count
        or analysis["independently_recomputed_scientific_plan_certificate_count"] != 0
        or analysis["shared_build_epoch_input_digest_consistent"] is not True
        or analysis["shared_runtime_tree_and_source_closure_consistent"] is not True
        or analysis["all_occurrence_accounting_bundles_independently_replayed"] is not True
        or analysis["scientific_planner_recomputed_by_campaign"] is not False
        or analysis["source_bytes_embedded_or_externally_anchored"] is not False
        or analysis["accounting_campaign_analysis_only"] is not True
        or analysis["campaign_preregistration_present"] is not False
        or analysis["scientific_campaign_closure_issued"] is not False
        or analysis["certificate_coverage_gate_status"] != "NOT_RUN"
        or analysis["counter_completeness_gate_status"] != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
        or analysis["workload_economics_gate_status"] != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
        or analysis["official_scalar_cost"] is not None
        or analysis["official_N_break_even"] is not None
        or analysis["scalar_gate_status"] != SCALAR_GATE_STATUS
        or analysis["official_execution_allowed"] is not False
    ):
        _fail("campaign analysis boundary or denominator changed")
    profile_payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_analysis_verification_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "producer_import_forbidden": True,
        "minimum_occurrence_count": 2,
        "complete_order_enumeration_required": True,
        "scientific_planner_recomputation_required": False,
        "campaign_preregistration_required_for_this_retrospective_profile": False,
        "official_execution_allowed": False,
    }
    profile_id = content_id(VERIFICATION_PROFILE_DOMAIN, profile_payload)
    return QueryBoundCampaignAnalysisVerificationV1(
        _VERIFICATION_ISSUER,
        profile_id,
        analysis_id,
        spec_id,
        occurrence_ids,
        tuple(row["campaign_occurrence_row_id"] for row in rows),
        tuple(row["campaign_vector_prefix_id"] for row in prefixes),
        tuple(row["complete_bundle_verification_id"] for row in rows),
        hashlib.sha256(analysis_bytes).hexdigest(),
        len(analysis_bytes),
    )


__all__ = (
    "ConstructionK7QueryBoundCampaignAnalysisIndependentVerifierV1Error",
    "QueryBoundCampaignAnalysisVerificationV1",
    "verify_query_bound_campaign_analysis_bytes_v1",
)
