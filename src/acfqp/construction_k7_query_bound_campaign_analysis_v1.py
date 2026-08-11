"""Retrospective vector-only analysis of verified query-bound occurrences.

This additive consumer never treats already produced bundles as a preregistered
campaign.  It independently verifies every eight-role occurrence directory,
requires one shared source trace, BuildEpoch input, runtime tree, and source
closure, and enumerates reducer-exact vector prefixes for every finite order.
Scientific campaign closure, scalar cost, break-even, and official gates remain
locked until a future runner freezes the workload before any occurrence runs.
"""

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
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_VECTOR_PREFIX_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.99"
PROFILE_KEY = "construction_k7_query_bound_campaign_analysis_v1"
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

_SPEC_ISSUER = object()
_ROW_ISSUER = object()
_PREFIX_ISSUER = object()
_ANALYSIS_ISSUER = object()


class ConstructionK7QueryBoundCampaignAnalysisV1Error(ValueError):
    """A bundle, identity join, vector prefix, or locked claim diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignAnalysisV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignAnalysisV1Error(
            f"{label} must be one content ID"
        ) from error


def _exact(document: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != fields:
        _fail(f"{label} field set changed")
    return document


def _axis_values(values: Sequence[tuple[str, int]], label: str) -> tuple[tuple[str, int], ...]:
    rows = tuple(values)
    if tuple(axis for axis, _value in rows) != SHARED_AXES:
        _fail(f"{label} axis order changed")
    if any(type(value) is not int or value < 0 for _axis, value in rows):
        _fail(f"{label} contains a non-exact or negative value")
    return rows


def _axis_rows(values: Sequence[tuple[str, int]]) -> list[dict[str, Any]]:
    return [{"axis": axis, "value": value} for axis, value in values]


def _read_canonical_role(directory: Path, role: str) -> tuple[bytes, dict[str, Any]]:
    if directory.is_symlink():
        _fail("campaign occurrence directory must not be a symbolic link")
    root = directory.resolve(strict=True)
    root_info = root.stat()
    if root.is_symlink() or not root.is_dir() or stat.S_IMODE(root_info.st_mode) & 0o077:
        _fail("campaign occurrence directory must be private and real")
    path = root / f"{role}.json"
    info = path.stat()
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(info.st_mode) & 0o177:
        _fail(f"campaign {role} role is not one private regular file")
    raw = path.read_bytes()
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignAnalysisV1Error(
            f"campaign {role} role is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"campaign {role} role is not one canonical object")
    return raw, document


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignAnalysisSpecV1:
    _issuer: InitVar[object]
    comparison_profile_id: str
    ordered_occurrence_ids: tuple[str, ...]
    permutation_cap: int
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        required = math.factorial(len(self.ordered_occurrence_ids))
        if (
            _issuer is not _SPEC_ISSUER
            or type(self.ordered_occurrence_ids) is not tuple
            or len(self.ordered_occurrence_ids) < 2
            or len(set(self.ordered_occurrence_ids)) != len(self.ordered_occurrence_ids)
            or type(self.permutation_cap) is not int
            or self.permutation_cap <= 0
            or self.permutation_cap > MAX_EXPLICIT_PERMUTATIONS
            or required > self.permutation_cap
        ):
            _fail("campaign analysis spec is caller-minted, duplicated, or over cap")
        expected_profile = registry_v6.official_comparison_profile_v6(
            registry_v6.official_counter_registry_v6()
        ).comparison_profile_id
        if self.comparison_profile_id != expected_profile:
            _fail("campaign analysis spec crossed its comparison profile")
        _cid(self.comparison_profile_id, "comparison profile")
        for occurrence_id in self.ordered_occurrence_ids:
            _cid(occurrence_id, "campaign occurrence")
        object.__setattr__(self, "_spec_id", content_id(SPEC_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_analysis_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "analysis_mode": ANALYSIS_MODE,
            "comparison_profile_id": self.comparison_profile_id,
            "ordered_logical_occurrence_ids": list(self.ordered_occurrence_ids),
            "logical_occurrence_count": len(self.ordered_occurrence_ids),
            "permutation_cap": self.permutation_cap,
            "campaign_preregistration_present": False,
            "posthoc_occurrence_deletion_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "scalar_gate_status": SCALAR_GATE_STATUS,
            "official_execution_allowed": False,
        }

    @property
    def spec_id(self) -> str:
        expected = content_id(SPEC_DOMAIN, self._payload())
        if expected != self._spec_id:
            _fail("campaign analysis spec changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_analysis_spec_id": self.spec_id}


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignOccurrenceRowV1:
    _issuer: InitVar[object]
    campaign_analysis_spec_id: str
    occurrence_index: int
    logical_occurrence_id: str
    complete_bundle_verification_id: str
    operational_trace_id: str
    shared_measurement_id: str
    shared_receipt_set_id: str
    runtime_preparation_id: str
    runtime_tree_id: str
    source_closure_id: str
    source_trace_sha256: str
    build_epoch_envelope_sha256: str
    work_vector_ids: tuple[str, ...]
    comparison_vector_ids: tuple[str, ...]
    projection_proof_ids: tuple[str, ...]
    aggregate_values: tuple[tuple[str, int], ...]
    output_bytes: int
    role_digests: tuple[tuple[str, str], ...]
    _row_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ROW_ISSUER
            or type(self.occurrence_index) is not int
            or self.occurrence_index <= 0
            or len(self.work_vector_ids) != 3
            or len(self.comparison_vector_ids) != 3
            or len(self.projection_proof_ids) != 3
            or type(self.output_bytes) is not int
            or self.output_bytes <= 0
            or tuple(role for role, _digest in self.role_digests) != bundle_v1.ROLE_ORDER
        ):
            _fail("campaign occurrence row is caller-minted or malformed")
        for value, label in (
            (self.campaign_analysis_spec_id, "campaign analysis spec"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.complete_bundle_verification_id, "bundle verification"),
            (self.operational_trace_id, "operational trace"),
            (self.shared_measurement_id, "shared measurement"),
            (self.shared_receipt_set_id, "shared receipt set"),
            (self.runtime_preparation_id, "runtime preparation"),
            (self.runtime_tree_id, "runtime tree"),
            (self.source_closure_id, "source closure"),
            (self.source_trace_sha256, "source trace digest"),
            (self.build_epoch_envelope_sha256, "BuildEpoch digest"),
            *((item, "work vector") for item in self.work_vector_ids),
            *((item, "comparison vector") for item in self.comparison_vector_ids),
            *((item, "projection proof") for item in self.projection_proof_ids),
            *((item, "role digest") for _role, item in self.role_digests),
        ):
            _cid(value, label)
        object.__setattr__(self, "aggregate_values", _axis_values(self.aggregate_values, "occurrence aggregate"))
        object.__setattr__(self, "_row_id", content_id(ROW_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_occurrence_row.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_analysis_spec_id": self.campaign_analysis_spec_id,
            "occurrence_index": self.occurrence_index,
            "logical_occurrence_id": self.logical_occurrence_id,
            "complete_bundle_verification_id": self.complete_bundle_verification_id,
            "operational_trace_id": self.operational_trace_id,
            "shared_measurement_id": self.shared_measurement_id,
            "shared_resource_receipt_set_id": self.shared_receipt_set_id,
            "runtime_preparation_id": self.runtime_preparation_id,
            "runtime_tree_id": self.runtime_tree_id,
            "source_closure_id": self.source_closure_id,
            "source_trace_sha256": self.source_trace_sha256,
            "build_epoch_envelope_sha256": self.build_epoch_envelope_sha256,
            "work_vector_ids": list(self.work_vector_ids),
            "comparison_vector_ids": list(self.comparison_vector_ids),
            "actual_projection_proof_ids": list(self.projection_proof_ids),
            "occurrence_comparison_values": _axis_rows(self.aggregate_values),
            "io.output_bytes": self.output_bytes,
            "role_digests": [
                {"artifact_role": role, "bytes_sha256": digest}
                for role, digest in self.role_digests
            ],
            "construction_terminal_class": "PLAN_CERTIFICATE",
            "construction_terminal_code": "FULL_GROUND_FALLBACK",
            "scientific_planner_recomputed_by_campaign": False,
            "official_execution_allowed": False,
        }

    @property
    def row_id(self) -> str:
        expected = content_id(ROW_DOMAIN, self._payload())
        if expected != self._row_id:
            _fail("campaign occurrence row changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_occurrence_row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignVectorPrefixV1:
    _issuer: InitVar[object]
    campaign_analysis_spec_id: str
    comparison_profile_id: str
    full_order: tuple[str, ...]
    prefix_length: int
    values: tuple[tuple[str, int], ...]
    _prefix_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PREFIX_ISSUER
            or not self.full_order
            or len(set(self.full_order)) != len(self.full_order)
            or type(self.prefix_length) is not int
            or not (1 <= self.prefix_length <= len(self.full_order))
        ):
            _fail("campaign vector prefix is caller-minted or malformed")
        _cid(self.campaign_analysis_spec_id, "campaign analysis spec")
        _cid(self.comparison_profile_id, "comparison profile")
        for occurrence_id in self.full_order:
            _cid(occurrence_id, "prefix occurrence")
        object.__setattr__(self, "values", _axis_values(self.values, "campaign vector prefix"))
        object.__setattr__(self, "_prefix_id", content_id(PREFIX_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_vector_prefix.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_analysis_spec_id": self.campaign_analysis_spec_id,
            "comparison_profile_id": self.comparison_profile_id,
            "full_order": list(self.full_order),
            "prefix_length": self.prefix_length,
            "prefix_occurrence_ids": list(self.full_order[: self.prefix_length]),
            "values": _axis_rows(self.values),
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "scalar_gate_status": SCALAR_GATE_STATUS,
        }

    @property
    def prefix_id(self) -> str:
        expected = content_id(PREFIX_DOMAIN, self._payload())
        if expected != self._prefix_id:
            _fail("campaign vector prefix changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_vector_prefix_id": self.prefix_id}


def _require_shared_reuse(
    rows: tuple[QueryBoundCampaignOccurrenceRowV1, ...],
) -> None:
    for attribute, label in (
        ("runtime_preparation_id", "runtime preparation"),
        ("runtime_tree_id", "runtime tree"),
        ("source_closure_id", "source closure"),
        ("source_trace_sha256", "source trace"),
        ("build_epoch_envelope_sha256", "BuildEpoch input"),
    ):
        if len({getattr(row, attribute) for row in rows}) != 1:
            _fail(f"campaign does not reuse one {label}")


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignAnalysisV1:
    _issuer: InitVar[object]
    spec: QueryBoundCampaignAnalysisSpecV1 = field(repr=False, compare=False)
    rows: tuple[QueryBoundCampaignOccurrenceRowV1, ...]
    prefixes: tuple[QueryBoundCampaignVectorPrefixV1, ...]
    _analysis_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        count = len(self.spec.ordered_occurrence_ids)
        order_count = math.factorial(count)
        if (
            _issuer is not _ANALYSIS_ISSUER
            or type(self.spec) is not QueryBoundCampaignAnalysisSpecV1
            or tuple(row.occurrence_index for row in self.rows) != tuple(range(1, count + 1))
            or tuple(row.logical_occurrence_id for row in self.rows) != self.spec.ordered_occurrence_ids
            or any(row.campaign_analysis_spec_id != self.spec.spec_id for row in self.rows)
            or len(self.prefixes) != order_count * count
            or tuple(sorted(self.prefixes, key=lambda row: (row.prefix_length, row.full_order))) != self.prefixes
            or any(row.campaign_analysis_spec_id != self.spec.spec_id for row in self.prefixes)
            or any(
                row.comparison_profile_id != self.spec.comparison_profile_id
                for row in self.prefixes
            )
        ):
            _fail("campaign analysis is caller-minted or incomplete")
        _require_shared_reuse(self.rows)
        for values, label in (
            (tuple(row.row_id for row in self.rows), "occurrence row"),
            (tuple(row.complete_bundle_verification_id for row in self.rows), "bundle verification"),
            (tuple(row.operational_trace_id for row in self.rows), "operational trace"),
            (tuple(row.shared_measurement_id for row in self.rows), "shared measurement"),
            (tuple(row.shared_receipt_set_id for row in self.rows), "shared receipt set"),
            (
                tuple(value for row in self.rows for value in row.work_vector_ids),
                "work vector",
            ),
            (
                tuple(value for row in self.rows for value in row.comparison_vector_ids),
                "comparison vector",
            ),
            (
                tuple(value for row in self.rows for value in row.projection_proof_ids),
                "projection proof",
            ),
            (tuple(row.prefix_id for row in self.prefixes), "vector prefix"),
        ):
            if len(set(values)) != len(values):
                _fail(f"campaign analysis repeats one {label}")
        object.__setattr__(self, "_analysis_id", content_id(ANALYSIS_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        count = len(self.rows)
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_analysis.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "analysis_mode": ANALYSIS_MODE,
            "campaign_analysis_spec": self.spec.to_document(),
            "campaign_analysis_spec_id": self.spec.spec_id,
            "comparison_profile_id": self.spec.comparison_profile_id,
            "occurrence_rows": [row.to_document() for row in self.rows],
            "vector_prefix_totals": [row.to_document() for row in self.prefixes],
            "logical_occurrence_count": count,
            "closure_denominator": count,
            "certification_coverage_denominator": count,
            "economics_cost_denominator": count,
            "enumerated_order_count": math.factorial(count),
            "order_enumeration_complete": True,
            "observed_construction_plan_terminal_count": count,
            "independently_recomputed_scientific_plan_certificate_count": 0,
            "shared_build_epoch_input_digest_consistent": True,
            "shared_runtime_tree_and_source_closure_consistent": True,
            "all_occurrence_accounting_bundles_independently_replayed": True,
            "scientific_planner_recomputed_by_campaign": False,
            "source_bytes_embedded_or_externally_anchored": False,
            "accounting_campaign_analysis_only": True,
            "campaign_preregistration_present": False,
            "scientific_campaign_closure_issued": False,
            "certificate_coverage_gate_status": "NOT_RUN",
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "scalar_gate_status": SCALAR_GATE_STATUS,
            "official_execution_allowed": False,
        }

    @property
    def analysis_id(self) -> str:
        expected = content_id(ANALYSIS_DOMAIN, self._payload())
        if expected != self._analysis_id:
            _fail("campaign analysis changed after issuance")
        return expected

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_bound_campaign_analysis_id": self.analysis_id}


def freeze_query_bound_campaign_analysis_spec_v1(
    *, ordered_occurrence_ids: Sequence[str], permutation_cap: int
) -> QueryBoundCampaignAnalysisSpecV1:
    profile = registry_v6.official_comparison_profile_v6(
        registry_v6.official_counter_registry_v6()
    )
    return QueryBoundCampaignAnalysisSpecV1(
        _SPEC_ISSUER,
        profile.comparison_profile_id,
        tuple(ordered_occurrence_ids),
        permutation_cap,
    )


def _bundle_row(
    spec: QueryBoundCampaignAnalysisSpecV1,
    index: int,
    directory: str | Path,
) -> QueryBoundCampaignOccurrenceRowV1:
    root = Path(directory)
    verification = bundle_v1.verify_query_bound_complete_bundle_directory_v1(root)
    business_raw, business = _read_canonical_role(root, "BUSINESS_RESULT")
    comparison_raw, comparison = _read_canonical_role(root, "COMPARISON_VECTOR")
    digests = dict(verification.role_digests)
    if (
        hashlib.sha256(business_raw).hexdigest() != digests["BUSINESS_RESULT"]
        or hashlib.sha256(comparison_raw).hexdigest() != digests["COMPARISON_VECTOR"]
    ):
        _fail("campaign role bytes crossed complete-bundle verification")
    if verification.occurrence_id != spec.ordered_occurrence_ids[index - 1]:
        _fail("campaign bundle order differs from analysis spec")
    preparation = business.get("runtime_preparation")
    request = business.get("supervised_request")
    if type(preparation) is not dict or type(request) is not dict:
        _fail("campaign business result omitted preparation or request")
    manifest = preparation.get("runtime_manifest")
    source = preparation.get("source_closure")
    inventory = request.get("input_inventory")
    if type(manifest) is not dict or type(source) is not dict or type(inventory) is not list:
        _fail("campaign runtime or input identity is malformed")
    inventory_by_role: dict[str, dict[str, Any]] = {}
    for candidate in inventory:
        row = _exact(candidate, {"role", "filename", "byte_count", "sha256"}, "campaign input inventory row")
        if row["role"] in inventory_by_role:
            _fail("campaign input inventory repeats a role")
        _cid(row["sha256"], "campaign input digest")
        if type(row["byte_count"]) is not int or row["byte_count"] <= 0:
            _fail("campaign input byte count is invalid")
        inventory_by_role[row["role"]] = row
    if tuple(inventory_by_role) != INPUT_ROLE_ORDER:
        _fail("campaign input inventory role order changed")
    axis_rows = comparison.get("occurrence_reducer_exact_comparison_values")
    if type(axis_rows) is not list:
        _fail("campaign occurrence comparison aggregate is absent")
    values: list[tuple[str, int]] = []
    for candidate in axis_rows:
        row = _exact(candidate, {"axis", "value"}, "campaign occurrence axis row")
        values.append((row["axis"], row["value"]))
    return QueryBoundCampaignOccurrenceRowV1(
        _ROW_ISSUER,
        spec.spec_id,
        index,
        verification.occurrence_id,
        verification.verification_id,
        verification.operational_trace_id,
        verification.shared_measurement_id,
        verification.shared_receipt_set_id,
        _cid(preparation.get("query_bound_runtime_preparation_id"), "runtime preparation"),
        _cid(manifest.get("runtime_tree_id"), "runtime tree"),
        _cid(source.get("closure_id"), "source closure"),
        inventory_by_role["SOURCE_TRACE"]["sha256"],
        inventory_by_role["BUILD_EPOCH_ENVELOPE"]["sha256"],
        verification.work_vector_ids,
        verification.comparison_vector_ids,
        verification.projection_proof_ids,
        tuple(values),
        verification.output_bytes,
        verification.role_digests,
    )


def _prefixes(
    spec: QueryBoundCampaignAnalysisSpecV1,
    rows: tuple[QueryBoundCampaignOccurrenceRowV1, ...],
) -> tuple[QueryBoundCampaignVectorPrefixV1, ...]:
    profile = registry_v6.official_comparison_profile_v6(
        registry_v6.official_counter_registry_v6()
    )
    reducers = {axis.name: axis.reducer for axis in profile.axes}
    by_occurrence = {row.logical_occurrence_id: dict(row.aggregate_values) for row in rows}
    result: list[QueryBoundCampaignVectorPrefixV1] = []
    for order in permutations(spec.ordered_occurrence_ids):
        current = {axis: 0 for axis in SHARED_AXES}
        for length, occurrence_id in enumerate(order, start=1):
            values = by_occurrence[occurrence_id]
            for axis in SHARED_AXES:
                if reducers[axis] is ReducerEnum.SUM:
                    current[axis] += values[axis]
                else:
                    current[axis] = max(current[axis], values[axis])
            result.append(
                QueryBoundCampaignVectorPrefixV1(
                    _PREFIX_ISSUER,
                    spec.spec_id,
                    spec.comparison_profile_id,
                    tuple(order),
                    length,
                    tuple((axis, current[axis]) for axis in SHARED_AXES),
                )
            )
    return tuple(sorted(result, key=lambda row: (row.prefix_length, row.full_order)))


def analyze_query_bound_campaign_bundles_v1(
    spec: QueryBoundCampaignAnalysisSpecV1,
    *,
    bundle_directories: Sequence[str | Path],
) -> QueryBoundCampaignAnalysisV1:
    if type(spec) is not QueryBoundCampaignAnalysisSpecV1:
        _fail("campaign analysis requires one exact spec")
    # Re-read the frozen content ID instead of re-running __post_init__: the
    # latter would re-baseline a caller-tampered frozen object.
    _ = spec.spec_id
    directories = tuple(bundle_directories)
    if len(directories) != len(spec.ordered_occurrence_ids):
        _fail("campaign bundle count differs from analysis denominator")
    rows = tuple(_bundle_row(spec, index, directory) for index, directory in enumerate(directories, start=1))
    result = QueryBoundCampaignAnalysisV1(
        _ANALYSIS_ISSUER,
        spec,
        rows,
        _prefixes(spec, rows),
    )
    return verify_query_bound_campaign_analysis_v1(
        result,
        spec=spec,
        bundle_directories=directories,
    )


def verify_query_bound_campaign_analysis_v1(
    claimed: QueryBoundCampaignAnalysisV1,
    *,
    spec: QueryBoundCampaignAnalysisSpecV1,
    bundle_directories: Sequence[str | Path],
) -> QueryBoundCampaignAnalysisV1:
    if type(claimed) is not QueryBoundCampaignAnalysisV1:
        _fail("campaign analysis verifier received a foreign result")
    expected_rows = tuple(
        _bundle_row(spec, index, directory)
        for index, directory in enumerate(tuple(bundle_directories), start=1)
    )
    expected = QueryBoundCampaignAnalysisV1(
        _ANALYSIS_ISSUER,
        spec,
        expected_rows,
        _prefixes(spec, expected_rows),
    )
    if claimed.to_document() != expected.to_document():
        _fail("campaign analysis differs from independently replayed bundles")
    return claimed


__all__ = (
    "ANALYSIS_MODE",
    "ConstructionK7QueryBoundCampaignAnalysisV1Error",
    "MAX_EXPLICIT_PERMUTATIONS",
    "QueryBoundCampaignAnalysisSpecV1",
    "QueryBoundCampaignAnalysisV1",
    "QueryBoundCampaignOccurrenceRowV1",
    "QueryBoundCampaignVectorPrefixV1",
    "analyze_query_bound_campaign_bundles_v1",
    "freeze_query_bound_campaign_analysis_spec_v1",
    "verify_query_bound_campaign_analysis_v1",
)
