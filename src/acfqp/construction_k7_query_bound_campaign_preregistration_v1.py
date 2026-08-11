"""Self-contained pre-execution registration for query-bound campaigns.

The registration freezes one source-closed runtime, every canonical scientific
input byte, the complete ordered logical-occurrence denominator, and the vector
comparison profile before a campaign runner is allowed to execute anything.
It embeds a deterministic source archive and a deduplicated input-blob table so
that a later verifier need not trust the mutable repository checkout.

This slice issues no occurrence result and no campaign certificate.  It is the
precondition for a later fresh runner, not retrospective evidence and not an
official Phase-3E execution authorization.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import math
from pathlib import Path
import stat
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import _v075_construction_source_runtime_v2 as source_runtime
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import construction_k7_query_bound_supervised_executor_v1 as executor_v1
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_INPUT_BLOB_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTERED_OCCURRENCE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_WORKLOAD_SPEC_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.100"
PROFILE_KEY = "construction_k7_query_bound_campaign_preregistration_v1"
REGISTRATION_STAGE = "PRE_EXECUTION_INPUT_RUNTIME_AND_DENOMINATOR_FREEZE"
SCALAR_GATE_STATUS = "NOT_RUN"
MAX_EXPLICIT_PERMUTATIONS = 100_000
COMMON_INPUT_ROLES = ("SOURCE_TRACE", "BUILD_EPOCH_ENVELOPE")
OCCURRENCE_SPECIFIC_INPUT_ROLES = (
    "ROOT_QUERY_RESULT",
    "RECOVERY_OVERLAY",
    "RECOVERY_REQUEST",
)
INPUT_ROLE_ORDER = tuple(role for role, _filename in executor_v1.INPUT_ROLES)
INPUT_FILENAME_BY_ROLE = dict(executor_v1.INPUT_ROLES)

INPUT_BLOB_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_INPUT_BLOB_V1_DOMAIN
OCCURRENCE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTERED_OCCURRENCE_V1_DOMAIN
)
WORKLOAD_SPEC_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_WORKLOAD_SPEC_V1_DOMAIN
PREREGISTRATION_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_V1_DOMAIN

_BLOB_ISSUER = object()
_OCCURRENCE_ISSUER = object()
_WORKLOAD_ISSUER = object()
_PREREGISTRATION_ISSUER = object()


class ConstructionK7QueryBoundCampaignPreregistrationV1Error(ValueError):
    """A source byte, input chain, denominator, or frozen identity diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignPreregistrationV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignPreregistrationV1Error(
            f"{label} must be one content ID"
        ) from error


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are absent")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignPreregistrationV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignOccurrenceInputsV1:
    """Caller-supplied bytes; semantic authority is issued only by preregister."""

    source_trace_bytes: bytes = field(repr=False)
    build_epoch_envelope_bytes: bytes = field(repr=False)
    root_query_result_bytes: bytes = field(repr=False)
    overlay_bytes: bytes = field(repr=False)
    request_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        for role, raw in self.role_bytes:
            _canonical_object(raw, f"campaign input {role}")

    @property
    def role_bytes(self) -> tuple[tuple[str, bytes], ...]:
        return (
            ("SOURCE_TRACE", self.source_trace_bytes),
            ("BUILD_EPOCH_ENVELOPE", self.build_epoch_envelope_bytes),
            ("ROOT_QUERY_RESULT", self.root_query_result_bytes),
            ("RECOVERY_OVERLAY", self.overlay_bytes),
            ("RECOVERY_REQUEST", self.request_bytes),
        )


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignInputBlobV1:
    _issuer: InitVar[object]
    canonical_bytes: bytes = field(repr=False)
    _blob_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BLOB_ISSUER:
            _fail("campaign input blob is caller-minted")
        _canonical_object(self.canonical_bytes, "campaign input blob")
        object.__setattr__(self, "_blob_id", content_id(INPUT_BLOB_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_input_blob.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "canonical_json_bytes_hex": self.canonical_bytes.hex(),
            "byte_count": len(self.canonical_bytes),
            "sha256": hashlib.sha256(self.canonical_bytes).hexdigest(),
        }

    @property
    def blob_id(self) -> str:
        expected = content_id(INPUT_BLOB_DOMAIN, self._payload())
        if expected != self._blob_id:
            _fail("campaign input blob changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_input_blob_id": self.blob_id}


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignPreregisteredOccurrenceV1:
    _issuer: InitVar[object]
    occurrence_index: int
    logical_occurrence_id: str
    query_ordinal: int
    role_blobs: tuple[tuple[str, QueryBoundCampaignInputBlobV1], ...]
    _occurrence_spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _OCCURRENCE_ISSUER
            or type(self.occurrence_index) is not int
            or self.occurrence_index <= 0
            or type(self.query_ordinal) is not int
            or self.query_ordinal < 0
            or tuple(role for role, _blob in self.role_blobs) != INPUT_ROLE_ORDER
            or any(
                type(blob) is not QueryBoundCampaignInputBlobV1
                for _role, blob in self.role_blobs
            )
        ):
            _fail("preregistered occurrence is caller-minted or malformed")
        _cid(self.logical_occurrence_id, "preregistered logical occurrence")
        for _role, blob in self.role_blobs:
            _ = blob.blob_id
        object.__setattr__(
            self,
            "_occurrence_spec_id",
            content_id(OCCURRENCE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.construction_k7_query_bound_campaign_"
                "preregistered_occurrence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_index": self.occurrence_index,
            "logical_occurrence_id": self.logical_occurrence_id,
            "query_ordinal": self.query_ordinal,
            "input_roles": [
                {
                    "role": role,
                    "filename": INPUT_FILENAME_BY_ROLE[role],
                    "campaign_input_blob_id": blob.blob_id,
                    "sha256": hashlib.sha256(blob.canonical_bytes).hexdigest(),
                    "byte_count": len(blob.canonical_bytes),
                }
                for role, blob in self.role_blobs
            ],
            "all_scientific_inputs_frozen_before_execution": True,
            "execution_result_present": False,
            "official_execution_allowed": False,
        }

    @property
    def occurrence_spec_id(self) -> str:
        expected = content_id(OCCURRENCE_DOMAIN, self._payload())
        if expected != self._occurrence_spec_id:
            _fail("preregistered occurrence changed after issuance")
        return expected

    @property
    def input_bytes_by_role(self) -> dict[str, bytes]:
        return {role: blob.canonical_bytes for role, blob in self.role_blobs}

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "preregistered_occurrence_spec_id": self.occurrence_spec_id,
        }


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignWorkloadSpecV1:
    _issuer: InitVar[object]
    comparison_profile_id: str
    occurrences: tuple[QueryBoundCampaignPreregisteredOccurrenceV1, ...]
    permutation_cap: int
    _workload_spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        count = len(self.occurrences)
        if (
            _issuer is not _WORKLOAD_ISSUER
            or count < 2
            or tuple(row.occurrence_index for row in self.occurrences)
            != tuple(range(1, count + 1))
            or len({row.logical_occurrence_id for row in self.occurrences}) != count
            or len({row.occurrence_spec_id for row in self.occurrences}) != count
            or type(self.permutation_cap) is not int
            or not (
                math.factorial(count)
                <= self.permutation_cap
                <= MAX_EXPLICIT_PERMUTATIONS
            )
        ):
            _fail("campaign workload spec is incomplete, duplicated, or over cap")
        _cid(self.comparison_profile_id, "campaign comparison profile")
        object.__setattr__(
            self,
            "_workload_spec_id",
            content_id(WORKLOAD_SPEC_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_workload_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "comparison_profile_id": self.comparison_profile_id,
            "ordered_logical_occurrence_ids": [
                row.logical_occurrence_id for row in self.occurrences
            ],
            "ordered_occurrence_spec_ids": [
                row.occurrence_spec_id for row in self.occurrences
            ],
            "logical_occurrence_count": len(self.occurrences),
            "permutation_cap": self.permutation_cap,
            "registration_order_is_denominator_order": True,
            "posthoc_occurrence_deletion_allowed": False,
            "posthoc_occurrence_insertion_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "scalar_gate_status": SCALAR_GATE_STATUS,
            "official_execution_allowed": False,
        }

    @property
    def workload_spec_id(self) -> str:
        expected = content_id(WORKLOAD_SPEC_DOMAIN, self._payload())
        if expected != self._workload_spec_id:
            _fail("campaign workload spec changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_workload_spec_id": self.workload_spec_id}


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignPreregistrationV1:
    _issuer: InitVar[object]
    runtime_preparation: executor_v1.QueryBoundRuntimePreparationV1 = field(
        repr=False,
        compare=False,
    )
    source_archive: source_runtime.ConstructionSourceArchiveV2 = field(
        repr=False,
        compare=False,
    )
    source_module_bytes: tuple[tuple[str, bytes], ...] = field(
        repr=False,
        compare=False,
    )
    input_blobs: tuple[QueryBoundCampaignInputBlobV1, ...]
    occurrences: tuple[QueryBoundCampaignPreregisteredOccurrenceV1, ...]
    workload_spec: QueryBoundCampaignWorkloadSpecV1
    _preregistration_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PREREGISTRATION_ISSUER
            or type(self.runtime_preparation)
            is not executor_v1.QueryBoundRuntimePreparationV1
            or type(self.source_archive)
            is not source_runtime.ConstructionSourceArchiveV2
            or type(self.workload_spec) is not QueryBoundCampaignWorkloadSpecV1
            or self.occurrences != self.workload_spec.occurrences
            or tuple(blob.blob_id for blob in self.input_blobs)
            != tuple(sorted({blob.blob_id for blob in self.input_blobs}))
            or tuple(name for name, _raw in self.source_module_bytes)
            != self.runtime_preparation.source_closure.module_names
        ):
            _fail("campaign preregistration is caller-minted or malformed")
        _ = self.runtime_preparation.preparation_id
        if (
            self.source_archive.source_closure_id
            != self.runtime_preparation.source_closure.closure_id
            or self.source_archive.entries
            != self.runtime_preparation.source_closure.modules
        ):
            _fail("campaign source archive crossed its runtime preparation")
        known = {blob.blob_id: blob for blob in self.input_blobs}
        if any(
            blob.blob_id not in known
            for occurrence in self.occurrences
            for _role, blob in occurrence.role_blobs
        ):
            _fail("campaign occurrence references an unregistered input blob")
        object.__setattr__(
            self,
            "_preregistration_id",
            content_id(PREREGISTRATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "registration_stage": REGISTRATION_STAGE,
            "runtime_preparation": self.runtime_preparation.to_document(),
            "runtime_preparation_id": self.runtime_preparation.preparation_id,
            "runtime_tree_id": self.runtime_preparation.manifest.runtime_tree_id,
            "source_closure_id": self.runtime_preparation.source_closure.closure_id,
            "source_archive": self.source_archive.to_document(),
            "source_archive_bytes_hex": self.source_archive.archive_bytes.hex(),
            "source_bytes_embedded": True,
            "input_blobs": [blob.to_document() for blob in self.input_blobs],
            "preregistered_occurrences": [
                row.to_document() for row in self.occurrences
            ],
            "campaign_workload_spec": self.workload_spec.to_document(),
            "campaign_workload_spec_id": self.workload_spec.workload_spec_id,
            "ordered_logical_occurrence_ids": [
                row.logical_occurrence_id for row in self.occurrences
            ],
            "logical_occurrence_count": len(self.occurrences),
            "campaign_preregistration_present": True,
            "preregistration_contains_execution_result": False,
            "execution_started_by_this_api": False,
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
    def preregistration_id(self) -> str:
        expected = content_id(PREREGISTRATION_DOMAIN, self._payload())
        if expected != self._preregistration_id:
            _fail("campaign preregistration changed after issuance")
        return expected

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query_bound_campaign_preregistration_id": self.preregistration_id,
        }


def _source_archive(
    *,
    repository_root: Path,
    preparation: executor_v1.QueryBoundRuntimePreparationV1,
) -> tuple[
    source_runtime.ConstructionSourceArchiveV2,
    tuple[tuple[str, bytes], ...],
]:
    module_rows: list[tuple[str, bytes]] = []
    for entry in preparation.source_closure.modules:
        path = repository_root / "src" / entry.relative_path
        if path.is_symlink() or not path.is_file():
            _fail("campaign source archive contains a linked or absent source")
        info = path.stat()
        raw = path.read_bytes()
        if (
            not stat.S_ISREG(info.st_mode)
            or len(raw) != entry.source_byte_count
            or hashlib.sha256(raw).hexdigest() != entry.source_sha256
        ):
            _fail("campaign source bytes differ from runtime source closure")
        module_rows.append((entry.module_name, raw))
    sources = dict(module_rows)
    archive = source_runtime.build_deterministic_source_archive_v2(
        closure=preparation.source_closure,
        module_sources=sources,
    )
    return archive, tuple(module_rows)


def _semantic_occurrence(
    *,
    index: int,
    supplied: QueryBoundCampaignOccurrenceInputsV1,
    blobs_by_digest: dict[str, QueryBoundCampaignInputBlobV1],
) -> QueryBoundCampaignPreregisteredOccurrenceV1:
    if type(supplied) is not QueryBoundCampaignOccurrenceInputsV1:
        _fail("campaign occurrence input has a foreign type")
    root = query_v1.verify_reusable_abstract_query_result_bytes_v1(
        source_trace_bytes=supplied.source_trace_bytes,
        build_epoch_envelope_bytes=supplied.build_epoch_envelope_bytes,
        result_bytes=supplied.root_query_result_bytes,
    )
    request = request_v1.verify_query_bound_recovery_request_bytes_v1(
        source_trace_bytes=supplied.source_trace_bytes,
        build_epoch_envelope_bytes=supplied.build_epoch_envelope_bytes,
        root_query_result_bytes=supplied.root_query_result_bytes,
        overlay_bytes=supplied.overlay_bytes,
        request_bytes=supplied.request_bytes,
    )
    if request.logical_occurrence_id != root.query.logical_occurrence_id:
        _fail("campaign occurrence crossed its root query and recovery request")
    role_blobs: list[tuple[str, QueryBoundCampaignInputBlobV1]] = []
    for role, raw in supplied.role_bytes:
        digest = hashlib.sha256(raw).hexdigest()
        blob = blobs_by_digest.get(digest)
        if blob is None:
            blob = QueryBoundCampaignInputBlobV1(_BLOB_ISSUER, raw)
            blobs_by_digest[digest] = blob
        elif blob.canonical_bytes != raw:
            _fail("campaign input digest collision changed canonical bytes")
        role_blobs.append((role, blob))
    return QueryBoundCampaignPreregisteredOccurrenceV1(
        _OCCURRENCE_ISSUER,
        index,
        root.query.logical_occurrence_id,
        root.query.query_ordinal,
        tuple(role_blobs),
    )


def preregister_query_bound_campaign_v1(
    *,
    repository_root: str | Path,
    runtime_cas_root: str | Path,
    occurrence_inputs: Sequence[QueryBoundCampaignOccurrenceInputsV1],
    permutation_cap: int,
) -> QueryBoundCampaignPreregistrationV1:
    """Freeze source, inputs, identities, and denominator without execution."""

    root = Path(repository_root).resolve(strict=True)
    supplied = tuple(occurrence_inputs)
    if len(supplied) < 2:
        _fail("campaign preregistration requires at least two occurrences")
    supplied_fingerprints = tuple(
        tuple(hashlib.sha256(raw).hexdigest() for _role, raw in row.role_bytes)
        if type(row) is QueryBoundCampaignOccurrenceInputsV1
        else ()
        for row in supplied
    )
    if (
        any(not row for row in supplied_fingerprints)
        or len(set(supplied_fingerprints)) != len(supplied_fingerprints)
    ):
        _fail("campaign preregistration contains a duplicate or foreign input")
    preparation = executor_v1.prepare_query_bound_accounted_runtime_v1(
        repository_root=root,
        runtime_cas_root=runtime_cas_root,
    )
    archive, source_rows = _source_archive(
        repository_root=root,
        preparation=preparation,
    )
    blobs_by_digest: dict[str, QueryBoundCampaignInputBlobV1] = {}
    occurrences = tuple(
        _semantic_occurrence(
            index=index,
            supplied=row,
            blobs_by_digest=blobs_by_digest,
        )
        for index, row in enumerate(supplied, start=1)
    )
    for role in COMMON_INPUT_ROLES:
        if len(
            {
                dict(row.role_blobs)[role].blob_id
                for row in occurrences
            }
        ) != 1:
            _fail(f"campaign occurrences do not share one {role} input")
    for role in OCCURRENCE_SPECIFIC_INPUT_ROLES:
        if len(
            {
                dict(row.role_blobs)[role].blob_id
                for row in occurrences
            }
        ) != len(occurrences):
            _fail(f"campaign occurrence-specific {role} input is duplicated")
    profile = registry_v6.official_comparison_profile_v6(
        registry_v6.official_counter_registry_v6()
    )
    workload = QueryBoundCampaignWorkloadSpecV1(
        _WORKLOAD_ISSUER,
        profile.comparison_profile_id,
        occurrences,
        permutation_cap,
    )
    blobs = tuple(sorted(blobs_by_digest.values(), key=lambda row: row.blob_id))
    return QueryBoundCampaignPreregistrationV1(
        _PREREGISTRATION_ISSUER,
        preparation,
        archive,
        source_rows,
        blobs,
        occurrences,
        workload,
    )


def verify_query_bound_campaign_preregistration_v1(
    claimed: QueryBoundCampaignPreregistrationV1,
) -> QueryBoundCampaignPreregistrationV1:
    """Recompute process-local source archive, input chains, and all IDs."""

    if type(claimed) is not QueryBoundCampaignPreregistrationV1:
        _fail("campaign preregistration verifier received a foreign result")
    sources = dict(claimed.source_module_bytes)
    expected_archive = source_runtime.build_deterministic_source_archive_v2(
        closure=claimed.runtime_preparation.source_closure,
        module_sources=sources,
    )
    if (
        expected_archive.to_document() != claimed.source_archive.to_document()
        or expected_archive.archive_bytes != claimed.source_archive.archive_bytes
    ):
        _fail("campaign embedded source archive differs from exact replay")
    rebuilt_blobs: dict[str, QueryBoundCampaignInputBlobV1] = {}
    try:
        rebuilt_occurrences = tuple(
            _semantic_occurrence(
                index=index,
                supplied=QueryBoundCampaignOccurrenceInputsV1(
                    row.input_bytes_by_role["SOURCE_TRACE"],
                    row.input_bytes_by_role["BUILD_EPOCH_ENVELOPE"],
                    row.input_bytes_by_role["ROOT_QUERY_RESULT"],
                    row.input_bytes_by_role["RECOVERY_OVERLAY"],
                    row.input_bytes_by_role["RECOVERY_REQUEST"],
                ),
                blobs_by_digest=rebuilt_blobs,
            )
            for index, row in enumerate(claimed.occurrences, start=1)
        )
    except ConstructionK7QueryBoundCampaignPreregistrationV1Error:
        raise
    except Exception as error:
        raise ConstructionK7QueryBoundCampaignPreregistrationV1Error(
            "campaign preregistered scientific input failed exact replay"
        ) from error
    rebuilt_workload = QueryBoundCampaignWorkloadSpecV1(
        _WORKLOAD_ISSUER,
        claimed.workload_spec.comparison_profile_id,
        rebuilt_occurrences,
        claimed.workload_spec.permutation_cap,
    )
    rebuilt_blobs_tuple = tuple(
        sorted(rebuilt_blobs.values(), key=lambda row: row.blob_id)
    )
    expected = QueryBoundCampaignPreregistrationV1(
        _PREREGISTRATION_ISSUER,
        claimed.runtime_preparation,
        expected_archive,
        claimed.source_module_bytes,
        rebuilt_blobs_tuple,
        rebuilt_occurrences,
        rebuilt_workload,
    )
    if claimed.to_document() != expected.to_document():
        _fail("campaign preregistration differs from exact process-local replay")
    return claimed


__all__ = (
    "ConstructionK7QueryBoundCampaignPreregistrationV1Error",
    "MAX_EXPLICIT_PERMUTATIONS",
    "QueryBoundCampaignInputBlobV1",
    "QueryBoundCampaignOccurrenceInputsV1",
    "QueryBoundCampaignPreregisteredOccurrenceV1",
    "QueryBoundCampaignPreregistrationV1",
    "QueryBoundCampaignWorkloadSpecV1",
    "preregister_query_bound_campaign_v1",
    "verify_query_bound_campaign_preregistration_v1",
)
