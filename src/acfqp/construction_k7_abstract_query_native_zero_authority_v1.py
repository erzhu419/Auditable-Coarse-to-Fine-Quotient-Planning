"""Sound query-segment native-zero authority for one abstract-only PASS.

This additive authority closes exactly the work that is genuinely absent from
the sealed *query* execution:

* 23 LOCAL/FALLBACK/REBUILD/control leaves already proved zero by the exact
  ``ABSTRACT_CERTIFIED`` forbidden-stage predecessor; and
* 60 optional incremental/checkpoint/audit leaves whose complete operation
  source set is absent from the isolated private runtime tree.

It deliberately does **not** set the 100 required initial acquisition, model
build, and closed-reconciliation leaves to zero.  Those costs belong to the
reused BuildEpoch and must be supplied by an actual construction-work
authority before a complete occurrence or campaign can be claimed.  This is
the accounting boundary that prevents model reuse from erasing sample tax.

The result is 83 fresh V6 ``CounterRecordV1`` objects and a total formal-record
progress of 101/202 when joined with the existing query-owner, lifecycle, and
shared-resource authorities.  No WorkVector, terminal, certificate, campaign
closure, or official Gate is issued here.
"""

from __future__ import annotations

import ast
from dataclasses import InitVar, dataclass, field
from enum import Enum
from functools import lru_cache
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_accounted_shared_authority_v2 as shared_v2
from acfqp import construction_k7_abstract_certified_accounting_coverage_v1 as coverage_v1
from acfqp import construction_k7_abstract_certified_lifecycle_reconciliation_authority_v1 as lifecycle_v1
from acfqp import construction_k7_abstract_certified_native_zero_closure_v1 as zero_v1
from acfqp import construction_k7_abstract_certified_query_owner_authority_v1 as owner_v1
from acfqp import construction_k7_abstract_pass_production_native_accounting_v1 as retained_v1
from acfqp import construction_k7_all_path_accounting_profile_v1 as all_path_v1
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3
from acfqp.accounting_v1 import CounterRecordV1, ReducerEnum
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_ENVELOPE_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_RESOLUTION_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_RUNTIME_WINDOW_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.phase3e_model_only_accounted_executor_v2 import (
    ACCOUNTED_RUNTIME_SOURCE_PATHS,
    PENDING_SHARED_PATH,
    AccountedModelOnlyExecutionV2,
    require_accounted_model_only_execution_v2,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ModelOnlyRAPMSourceV1,
    require_model_only_source_authority_v1,
)
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.82"
PROFILE_KEY = "construction_k7_abstract_query_native_zero_authority_v1"

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_PRIOR_FORMAL_RECORD_COUNT = 18
EXPECTED_PREDECESSOR_NATIVE_ZERO_COUNT = 23
EXPECTED_OPTIONAL_RUNTIME_EXCLUSION_COUNT = 60
EXPECTED_NEW_FORMAL_RECORD_COUNT = 83
EXPECTED_COMBINED_FORMAL_RECORD_COUNT = 101
EXPECTED_REQUIRED_BUILD_EPOCH_PATH_COUNT = 100
EXPECTED_REMAINING_PATH_COUNT = 101
EXPECTED_RUNTIME_SOURCE_COUNT = len(ACCOUNTED_RUNTIME_SOURCE_PATHS)
EXPECTED_EXCLUDED_OPERATION_MODULE_COUNT = 10

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

WINDOW_DOMAIN = CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_RUNTIME_WINDOW_V1_DOMAIN
RESOLUTION_DOMAIN = CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_RESOLUTION_V1_DOMAIN
ENVELOPE_DOMAIN = CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_ENVELOPE_V1_DOMAIN
REPLAY_DOMAIN = CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_REPLAY_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {WINDOW_DOMAIN, RESOLUTION_DOMAIN, ENVELOPE_DOMAIN, REPLAY_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("abstract query native-zero domains are not central")

MODEL_ONLY_RUNTIME_COUNTER_ALLOWLIST = (
    "common.abstract_audit_obligations",
    "common.abstract_bellman_backups",
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
)

_CONSTRUCTION_PREFIXES = ("acquisition.", "audit.", "build.", "closure.")
_WINDOW_ISSUER = object()
_RESOLUTION_ISSUER = object()
_ENVELOPE_ISSUER = object()


class ConstructionK7AbstractQueryNativeZeroAuthorityV1Error(ValueError):
    """The query runtime, stage partition, or zero evidence changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractQueryNativeZeroAuthorityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractQueryNativeZeroAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _same(left: Any, right: Any, label: str) -> None:
    try:
        matched = canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractQueryNativeZeroAuthorityV1Error(
            f"{label} is not canonical"
        ) from error
    if not matched:
        _fail(f"{label} crossed its exact root")


class QueryZeroProofKindV1(str, Enum):
    FORBIDDEN_ROUTE_PREDECESSOR = "FORBIDDEN_ROUTE_PREDECESSOR"
    OPTIONAL_STAGE_PRIVATE_RUNTIME_EXCLUSION = (
        "OPTIONAL_STAGE_PRIVATE_RUNTIME_EXCLUSION"
    )


class QueryZeroReplayOutcomeV1(str, Enum):
    VERIFIED = "QUERY_SEGMENT_83_NATIVE_ZERO_RECORDS_VERIFIED"
    DOCUMENT_BLOCKED = "QUERY_SEGMENT_NATIVE_ZERO_DOCUMENT_BLOCKED"


@dataclass(frozen=True, slots=True, order=True)
class RuntimeSourceFactV1:
    relative_path: str
    source_sha256: str
    source_byte_count: int
    operation_gateway_call_count: int

    def __post_init__(self) -> None:
        if (
            type(self.relative_path) is not str
            or not self.relative_path.startswith("acfqp/")
            or not self.relative_path.endswith(".py")
            or type(self.source_sha256) is not str
            or len(self.source_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.source_sha256)
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
            or type(self.operation_gateway_call_count) is not int
            or self.operation_gateway_call_count != 0
        ):
            _fail("runtime source fact is malformed or contains an accounting gateway")

    def to_document(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "operation_gateway_call_count": self.operation_gateway_call_count,
        }


@dataclass(frozen=True, slots=True)
class AbstractQueryZeroRuntimeWindowV1:
    _issuer: InitVar[object]
    accounted_measurement_id: str
    runtime_preparation_id: str
    runtime_tree_id: str
    operational_execution_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    route_decision_context_id: str
    all_path_accounting_profile_id: str
    stage_profile_id: str
    operation_boundary_manifest_v3_id: str
    runtime_sources: tuple[RuntimeSourceFactV1, ...]
    runtime_counter_allowlist: tuple[str, ...]
    excluded_operation_modules: tuple[str, ...]
    optional_zero_paths: tuple[str, ...]
    required_build_epoch_paths: tuple[str, ...]
    _window_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _WINDOW_ISSUER:
            _fail("abstract query runtime window is caller-minted")
        for value, label in (
            (self.accounted_measurement_id, "accounted measurement"),
            (self.runtime_preparation_id, "runtime preparation"),
            (self.runtime_tree_id, "runtime tree"),
            (self.operational_execution_id, "operational execution"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.route_decision_context_id, "route context"),
            (self.all_path_accounting_profile_id, "all-path profile"),
            (self.stage_profile_id, "stage profile"),
            (self.operation_boundary_manifest_v3_id, "operation-boundary manifest"),
        ):
            _cid(value, label)
        sources = tuple(self.runtime_sources)
        allowlist = tuple(self.runtime_counter_allowlist)
        excluded = tuple(self.excluded_operation_modules)
        optional = tuple(self.optional_zero_paths)
        required = tuple(self.required_build_epoch_paths)
        object.__setattr__(self, "runtime_sources", sources)
        object.__setattr__(self, "runtime_counter_allowlist", allowlist)
        object.__setattr__(self, "excluded_operation_modules", excluded)
        object.__setattr__(self, "optional_zero_paths", optional)
        object.__setattr__(self, "required_build_epoch_paths", required)
        runtime_paths = tuple(row.relative_path for row in sources)
        runtime_modules = {
            path[:-3].replace("/", ".") for path in runtime_paths
        }
        if (
            len(sources) != EXPECTED_RUNTIME_SOURCE_COUNT
            or runtime_paths != ACCOUNTED_RUNTIME_SOURCE_PATHS
            or any(type(row) is not RuntimeSourceFactV1 for row in sources)
            or allowlist != MODEL_ONLY_RUNTIME_COUNTER_ALLOWLIST
            or excluded != tuple(sorted(set(excluded)))
            or len(excluded) != EXPECTED_EXCLUDED_OPERATION_MODULE_COUNT
            or runtime_modules & set(excluded)
            or optional != tuple(sorted(set(optional)))
            or len(optional) != EXPECTED_OPTIONAL_RUNTIME_EXCLUSION_COUNT
            or required != tuple(sorted(set(required)))
            or len(required) != EXPECTED_REQUIRED_BUILD_EPOCH_PATH_COUNT
            or set(optional) & set(required)
            or any(not path.startswith(_CONSTRUCTION_PREFIXES) for path in optional + required)
        ):
            _fail("abstract query runtime exclusion window changed")
        object.__setattr__(self, "_window_id", content_id(WINDOW_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_query_zero_runtime_window.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "accounted_measurement_id": self.accounted_measurement_id,
            "runtime_preparation_id": self.runtime_preparation_id,
            "runtime_tree_id": self.runtime_tree_id,
            "operational_execution_id": self.operational_execution_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "route_decision_context_id": self.route_decision_context_id,
            "all_path_accounting_profile_id": self.all_path_accounting_profile_id,
            "stage_profile_id": self.stage_profile_id,
            "operation_boundary_manifest_v3_id": self.operation_boundary_manifest_v3_id,
            "runtime_sources": [row.to_document() for row in self.runtime_sources],
            "runtime_counter_allowlist": list(self.runtime_counter_allowlist),
            "excluded_operation_modules": list(self.excluded_operation_modules),
            "optional_zero_paths": list(self.optional_zero_paths),
            "required_build_epoch_paths": list(self.required_build_epoch_paths),
            "python_isolated_flag_required": True,
            "private_regular_package_runtime_required": True,
            "runtime_operation_gateway_call_count": 0,
            "excluded_operation_module_present_in_runtime": False,
            "missing_event_used_as_zero_evidence": False,
            "runtime_exclusion_is_complete_transitive_source_evidence": True,
            "required_build_epoch_cost_included_here": False,
        }

    @property
    def window_id(self) -> str:
        current = content_id(WINDOW_DOMAIN, self._payload())
        if current != self._window_id:
            _fail("abstract query runtime window changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "abstract_query_zero_runtime_window_id": self.window_id}


@dataclass(frozen=True, slots=True, order=True)
class AbstractQueryNativeZeroResolutionV1:
    _issuer: InitVar[object]
    runtime_window_id: str
    zero_value_closure_id: str
    path: str
    semantics_id: str
    registered_owner: str
    unit: str
    scope: str
    reducer: ReducerEnum
    stage_contexts: tuple[tuple[str, str], ...]
    proof_kind: QueryZeroProofKindV1
    predecessor_zero_proof_id: str | None
    operation_boundary_ids: tuple[str, ...]
    excluded_source_modules: tuple[str, ...]
    _resolution_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESOLUTION_ISSUER:
            _fail("abstract query native-zero resolution is caller-minted")
        _cid(self.runtime_window_id, "runtime window")
        _cid(self.zero_value_closure_id, "zero-value closure")
        if self.predecessor_zero_proof_id is not None:
            _cid(self.predecessor_zero_proof_id, "predecessor zero proof")
        for value in self.operation_boundary_ids:
            _cid(value, "operation boundary")
        try:
            reducer = ReducerEnum(self.reducer)
            proof_kind = QueryZeroProofKindV1(self.proof_kind)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractQueryNativeZeroAuthorityV1Error(
                "native-zero resolution enum changed"
            ) from error
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "proof_kind", proof_kind)
        stages = tuple(self.stage_contexts)
        boundaries = tuple(self.operation_boundary_ids)
        modules = tuple(self.excluded_source_modules)
        object.__setattr__(self, "stage_contexts", stages)
        object.__setattr__(self, "operation_boundary_ids", boundaries)
        object.__setattr__(self, "excluded_source_modules", modules)
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        if (
            leaf is None
            or leaf.semantics_id != self.semantics_id
            or leaf.owner != self.registered_owner
            or leaf.unit != self.unit
            or leaf.scope != self.scope
            or leaf.reducer is not reducer
            or stages != tuple(sorted(set(stages)))
            or not stages
            or boundaries != tuple(sorted(set(boundaries)))
            or modules != tuple(sorted(set(modules)))
        ):
            _fail("native-zero resolution changed its registered leaf or evidence")
        if proof_kind is QueryZeroProofKindV1.FORBIDDEN_ROUTE_PREDECESSOR:
            if (
                self.predecessor_zero_proof_id is None
                or modules
                or not boundaries
                or any(disposition != "FORBIDDEN" for _stage, disposition in stages)
            ):
                _fail("forbidden route zero lacks predecessor proof")
        elif (
            self.predecessor_zero_proof_id is not None
            or not modules
            or any(disposition != "OPTIONAL_REPEATABLE" for _stage, disposition in stages)
        ):
            _fail("optional-stage zero lacks private-runtime exclusion")
        object.__setattr__(
            self, "_resolution_id", content_id(RESOLUTION_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_query_native_zero_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "runtime_window_id": self.runtime_window_id,
            "zero_value_closure_id": self.zero_value_closure_id,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "registered_owner": self.registered_owner,
            "unit": self.unit,
            "scope": self.scope,
            "reducer": self.reducer.value,
            "stage_contexts": [
                {"stage_kind": stage, "disposition": disposition}
                for stage, disposition in self.stage_contexts
            ],
            "proof_kind": self.proof_kind.value,
            "predecessor_zero_proof_id": self.predecessor_zero_proof_id,
            "operation_boundary_ids": list(self.operation_boundary_ids),
            "excluded_source_modules": list(self.excluded_source_modules),
            "proved_value": 0,
            "formal_v6_counter_record_authorized": True,
            "missing_event_inferred_zero": False,
            "legacy_v1_record_relabelled_as_v6": False,
            "required_build_epoch_work_zeroed": False,
            "ground_access_performed": False,
        }

    @property
    def resolution_id(self) -> str:
        current = content_id(RESOLUTION_DOMAIN, self._payload())
        if current != self._resolution_id:
            _fail("native-zero resolution changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "abstract_query_native_zero_resolution_id": self.resolution_id}


@dataclass(frozen=True, slots=True)
class AbstractQueryNativeZeroEnvelopeV1:
    _issuer: InitVar[object]
    source_lease_id: str
    coverage_report_id: str
    zero_value_closure_id: str
    retained_inventory_id: str
    query_owner_envelope_id: str
    lifecycle_envelope_id: str
    shared_envelope_id: str
    runtime_window: AbstractQueryZeroRuntimeWindowV1
    resolutions: tuple[AbstractQueryNativeZeroResolutionV1, ...]
    counter_records: tuple[CounterRecordV1, ...]
    _envelope_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ENVELOPE_ISSUER
            or type(self.runtime_window) is not AbstractQueryZeroRuntimeWindowV1
            or any(type(row) is not AbstractQueryNativeZeroResolutionV1 for row in self.resolutions)
            or any(type(row) is not CounterRecordV1 for row in self.counter_records)
        ):
            _fail("abstract query native-zero envelope is caller-minted")
        for value, label in (
            (self.source_lease_id, "source lease"),
            (self.coverage_report_id, "coverage report"),
            (self.zero_value_closure_id, "zero-value closure"),
            (self.retained_inventory_id, "retained inventory"),
            (self.query_owner_envelope_id, "query-owner envelope"),
            (self.lifecycle_envelope_id, "lifecycle envelope"),
            (self.shared_envelope_id, "shared envelope"),
        ):
            _cid(value, label)
        resolutions = tuple(self.resolutions)
        records = tuple(self.counter_records)
        object.__setattr__(self, "resolutions", resolutions)
        object.__setattr__(self, "counter_records", records)
        expected_paths = tuple(
            sorted(
                set(self.runtime_window.optional_zero_paths)
                | {
                    row.path
                    for row in resolutions
                    if row.proof_kind is QueryZeroProofKindV1.FORBIDDEN_ROUTE_PREDECESSOR
                }
            )
        )
        if (
            len(expected_paths) != EXPECTED_NEW_FORMAL_RECORD_COUNT
            or tuple(row.path for row in resolutions) != expected_paths
            or tuple(row.path for row in records) != expected_paths
            or any(row.runtime_window_id != self.runtime_window.window_id for row in resolutions)
            or any(
                row.zero_value_closure_id != self.zero_value_closure_id
                for row in resolutions
            )
        ):
            _fail("abstract query native-zero record inventory changed")
        registry = registry_v6.official_counter_registry_v6()
        by_path = {row.path: row for row in resolutions}
        for record in records:
            resolution = by_path[record.path]
            record.verify_against(registry.by_path[record.path])
            if (
                record.counter_registry_id != registry.registry_id
                or record.value != 0
                or record.observed is not True
                or record.recorder_id != resolution.resolution_id
                or CounterRecordV1.from_dict(record.to_dict()) != record
            ):
                _fail("native-zero CounterRecord crossed its exact resolution")
        object.__setattr__(self, "_envelope_id", content_id(ENVELOPE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        forbidden_count = sum(
            row.proof_kind is QueryZeroProofKindV1.FORBIDDEN_ROUTE_PREDECESSOR
            for row in self.resolutions
        )
        optional_count = len(self.resolutions) - forbidden_count
        return {
            "schema": "acfqp.construction_k7_abstract_query_native_zero_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_code_assessed": TerminalCode.ABSTRACT_CERTIFIED.value,
            "source_lease_id": self.source_lease_id,
            "coverage_report_id": self.coverage_report_id,
            "zero_value_closure_id": self.zero_value_closure_id,
            "retained_inventory_id": self.retained_inventory_id,
            "query_owner_envelope_id": self.query_owner_envelope_id,
            "lifecycle_envelope_id": self.lifecycle_envelope_id,
            "shared_envelope_id": self.shared_envelope_id,
            "runtime_window": self.runtime_window.to_document(),
            "resolutions": [row.to_document() for row in self.resolutions],
            "formal_v6_counter_records": [row.to_dict() for row in self.counter_records],
            "required_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "prior_formal_v6_counter_record_count": EXPECTED_PRIOR_FORMAL_RECORD_COUNT,
            "predecessor_native_zero_materialization_count": forbidden_count,
            "new_optional_runtime_exclusion_count": optional_count,
            "new_formal_v6_counter_record_count": len(self.counter_records),
            "combined_formal_v6_counter_record_count": EXPECTED_COMBINED_FORMAL_RECORD_COUNT,
            "required_build_epoch_path_count_remaining": EXPECTED_REQUIRED_BUILD_EPOCH_PATH_COUNT,
            "required_build_epoch_paths_remaining": list(self.runtime_window.required_build_epoch_paths),
            "pending_output_fixed_point_path": PENDING_SHARED_PATH,
            "remaining_required_path_authority_count": EXPECTED_REMAINING_PATH_COUNT,
            "required_initial_acquisition_build_reconciliation_zeroed": False,
            "build_epoch_cost_charged_to_query_segment": False,
            "build_epoch_cost_authority_present": False,
            "sample_tax_erased_by_model_reuse": False,
            "complete_202_counter_record_chain_present": False,
            "formal_v6_work_vector_id": None,
            "formal_v6_comparison_vector_id": None,
            "terminal_artifact_id": None,
            "logical_occurrence_closure_id": None,
            "campaign_closure_id": None,
            "certificate_issued": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_n_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        }

    @property
    def envelope_id(self) -> str:
        current = content_id(ENVELOPE_DOMAIN, self._payload())
        if current != self._envelope_id:
            _fail("abstract query native-zero envelope changed after issuance")
        return current

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "abstract_query_native_zero_envelope_id": self.envelope_id}


@dataclass(frozen=True, slots=True)
class AbstractQueryNativeZeroReplayV1:
    outcome: QueryZeroReplayOutcomeV1
    envelope_id: str | None
    blocker_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            outcome = QueryZeroReplayOutcomeV1(self.outcome)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractQueryNativeZeroAuthorityV1Error(
                "native-zero replay outcome changed"
            ) from error
        object.__setattr__(self, "outcome", outcome)
        blockers = tuple(self.blocker_codes)
        object.__setattr__(self, "blocker_codes", blockers)
        if outcome is QueryZeroReplayOutcomeV1.VERIFIED:
            if self.envelope_id is None or blockers:
                _fail("verified native-zero replay is inconsistent")
            _cid(self.envelope_id, "native-zero envelope")
        elif self.envelope_id is not None or not blockers:
            _fail("blocked native-zero replay lacks one typed blocker")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_query_native_zero_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "outcome": self.outcome.value,
            "abstract_query_native_zero_envelope_id": self.envelope_id,
            "blocker_codes": list(self.blocker_codes),
            "exact_root_replay_performed": True,
            "runtime_tree_rescanned": self.outcome is QueryZeroReplayOutcomeV1.VERIFIED,
            "formal_v6_work_vector_issued": False,
            "terminal_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def replay_id(self) -> str:
        return content_id(REPLAY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "abstract_query_native_zero_replay_id": self.replay_id}


def _stage_contexts_by_path() -> dict[str, tuple[tuple[str, str], ...]]:
    registry = registry_v6.official_counter_registry_v6()
    stages = registry_v6.official_stage_profile_v6(registry)
    profile = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    rule = profile.terminal_path_rule_by_code[TerminalCode.ABSTRACT_CERTIFIED]
    dispositions = {
        row.stage_kind: row.disposition.value for row in rule.stage_plan
    }
    result: dict[str, tuple[tuple[str, str], ...]] = {}
    for path in registry.required_paths:
        contexts = tuple(
            sorted(
                (stage.value, dispositions[stage])
                for stage, stage_rule in stages.by_stage.items()
                if path in stage_rule.allowed_nonzero_paths
            )
        )
        if contexts:
            result[path] = contexts
    return result


@lru_cache(maxsize=1)
def _official_partition() -> tuple[
    tuple[str, ...], tuple[str, ...], tuple[str, ...], dict[str, tuple[tuple[str, str], ...]]
]:
    registry = registry_v6.official_counter_registry_v6()
    contexts = _stage_contexts_by_path()
    prior_paths = (
        set(owner_v1.OWNER_PATHS)
        | set(lifecycle_v1.LIFECYCLE_PATHS)
        | set(shared_v2.NEW_FORMAL_SHARED_PATHS)
    )
    candidates = set(registry.required_paths) - prior_paths - {PENDING_SHARED_PATH}
    forbidden = tuple(
        sorted(
            path
            for path in candidates
            if contexts[path]
            and all(disposition == "FORBIDDEN" for _stage, disposition in contexts[path])
        )
    )
    optional = tuple(
        sorted(
            path
            for path in candidates
            if path.startswith(_CONSTRUCTION_PREFIXES)
            and contexts[path]
            and all(
                disposition == "OPTIONAL_REPEATABLE"
                for _stage, disposition in contexts[path]
            )
        )
    )
    required = tuple(sorted(candidates - set(forbidden) - set(optional)))
    if (
        len(prior_paths) != EXPECTED_PRIOR_FORMAL_RECORD_COUNT
        or len(forbidden) != EXPECTED_PREDECESSOR_NATIVE_ZERO_COUNT
        or len(optional) != EXPECTED_OPTIONAL_RUNTIME_EXCLUSION_COUNT
        or len(required) != EXPECTED_REQUIRED_BUILD_EPOCH_PATH_COUNT
        or any(not path.startswith(_CONSTRUCTION_PREFIXES) for path in required)
        or set(forbidden) | set(optional) | set(required) != candidates
    ):
        _fail("ABSTRACT_CERTIFIED 23/60/100 query/build partition changed")
    return forbidden, optional, required, contexts


def _operation_evidence_for_optional_paths(
    optional_paths: tuple[str, ...],
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], str]:
    registry = registry_v6.official_counter_registry_v6()
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    boundaries: dict[str, tuple[str, ...]] = {}
    modules: dict[str, tuple[str, ...]] = {}
    for path in optional_paths:
        rows = manifest.by_path.get(path, ())
        boundaries[path] = tuple(sorted(row.boundary_id for row in rows))
        source_modules = {f"acfqp.{registry.by_path[path].owner}"}
        source_modules.update(row.operation_source_module for row in rows)
        modules[path] = tuple(sorted(source_modules))
        if not modules[path]:
            _fail(f"optional path lacks an operation source: {path}")
    return boundaries, modules, manifest.manifest_id


class _GatewayVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.count = 0

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Attribute) and node.func.attr == "emit_owned_operation_v1":
            self.count += 1
        self.generic_visit(node)


def _extract_worker_counter_allowlist(tree: ast.Module) -> tuple[str, ...]:
    matches: list[tuple[str, ...]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "count":
            continue
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Compare)
                and len(child.ops) == 1
                and isinstance(child.ops[0], ast.NotIn)
                and len(child.comparators) == 1
                and isinstance(child.comparators[0], (ast.Set, ast.Tuple))
            ):
                values = tuple(
                    sorted(
                        element.value
                        for element in child.comparators[0].elts
                        if isinstance(element, ast.Constant)
                        and type(element.value) is str
                    )
                )
                if len(values) == len(child.comparators[0].elts):
                    matches.append(values)
    if matches != [MODEL_ONLY_RUNTIME_COUNTER_ALLOWLIST]:
        _fail("model-only worker counter allowlist changed")
    return matches[0]


def _scan_private_runtime(
    accounted: AccountedModelOnlyExecutionV2,
    excluded_modules: tuple[str, ...],
) -> tuple[tuple[RuntimeSourceFactV1, ...], tuple[str, ...]]:
    preparation = accounted.preparation
    if (
        preparation.source_paths != ACCOUNTED_RUNTIME_SOURCE_PATHS
        or tuple(row.relative_path for row in preparation.manifest.entries)
        != ACCOUNTED_RUNTIME_SOURCE_PATHS
    ):
        _fail("accounted private runtime source inventory changed")
    excluded_paths = {module.replace(".", "/") + ".py" for module in excluded_modules}
    if excluded_paths & set(preparation.source_paths):
        _fail("optional construction operation source entered the query runtime")
    resolved = preparation.runtime_cas.resolve(
        preparation.manifest.runtime_tree_id,
        cap_profile=preparation.cap_profile,
    )
    if resolved.manifest != preparation.manifest:
        _fail("runtime CAS resolved another private tree")
    facts: list[RuntimeSourceFactV1] = []
    allowlist: tuple[str, ...] | None = None
    with resolved.open_private_lease() as lease:
        for entry in preparation.manifest.entries:
            target = lease.root / entry.relative_path
            if target.is_symlink() or not target.is_file():
                _fail("private runtime member disappeared during exclusion replay")
            raw = target.read_bytes()
            if (
                len(raw) != entry.size_bytes
                or hashlib.sha256(raw).hexdigest() != entry.sha256
            ):
                _fail("private runtime source bytes changed")
            try:
                tree = ast.parse(raw, filename=entry.relative_path)
            except (SyntaxError, ValueError) as error:
                raise ConstructionK7AbstractQueryNativeZeroAuthorityV1Error(
                    "private runtime source is not valid Python"
                ) from error
            visitor = _GatewayVisitor()
            visitor.visit(tree)
            if visitor.count:
                _fail("query runtime contains a construction operation gateway")
            if entry.relative_path == "acfqp/phase3e_model_only_accounted_runtime_v2.py":
                allowlist = _extract_worker_counter_allowlist(tree)
            facts.append(
                RuntimeSourceFactV1(
                    entry.relative_path,
                    entry.sha256,
                    entry.size_bytes,
                    visitor.count,
                )
            )
    if allowlist is None or tuple(facts) != tuple(sorted(facts, key=lambda row: row.relative_path)):
        _fail("private runtime worker or canonical source order is missing")
    return tuple(facts), allowlist


def _exact_roots(
    source: ModelOnlyRAPMSourceV1,
    accounted_execution: AccountedModelOnlyExecutionV2,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_envelope: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
    shared_envelope: shared_v2.AbstractAccountedSharedEnvelopeV2,
) -> tuple[
    AccountedModelOnlyExecutionV2,
    coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
    shared_v2.AbstractAccountedSharedEnvelopeV2,
]:
    try:
        require_model_only_source_authority_v1(source)
        accounted = require_accounted_model_only_execution_v2(accounted_execution)
    except ValueError as error:
        raise ConstructionK7AbstractQueryNativeZeroAuthorityV1Error(
            f"native-zero authority requires live exact roots: {error}"
        ) from error
    execution = accounted.execution
    report = coverage_v1.audit_abstract_certified_accounting_coverage_v1(execution)
    _same(report.to_document(), coverage_report.to_document(), "coverage report")
    zeros = zero_v1.close_abstract_certified_zero_value_subset_v1(execution, report)
    _same(zeros.to_document(), zero_closure.to_document(), "zero-value closure")
    inventory = retained_v1.inventory_abstract_pass_retained_v1_accounting_v1(
        execution, report, zeros
    )
    _same(inventory.to_document(), retained_inventory.to_document(), "retained inventory")
    owner = owner_v1.issue_abstract_certified_query_owner_authority_v1(
        execution, report, zeros, inventory
    )
    _same(owner.to_document(), query_owner_envelope.to_document(), "query-owner envelope")
    lifecycle = lifecycle_v1.issue_abstract_certified_lifecycle_reconciliation_authority_v1(
        source, execution, report, zeros, inventory, owner
    )
    _same(lifecycle.to_document(), lifecycle_envelope.to_document(), "lifecycle envelope")
    shared = shared_v2.issue_abstract_accounted_shared_authority_v2(
        source, accounted, report, zeros, inventory, owner, lifecycle
    )
    _same(shared.to_document(), shared_envelope.to_document(), "shared envelope")
    return accounted, report, zeros, inventory, owner, lifecycle, shared


def _build_from_exact_roots(
    source: ModelOnlyRAPMSourceV1,
    accounted: AccountedModelOnlyExecutionV2,
    report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zeros: zero_v1.AbstractCertifiedZeroValueClosureV1,
    inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    owner: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
    shared: shared_v2.AbstractAccountedSharedEnvelopeV2,
) -> AbstractQueryNativeZeroEnvelopeV1:
    forbidden_paths, optional_paths, required_paths, contexts = _official_partition()
    predecessor = {row.path: row for row in zeros.native_zero_proofs}
    if set(predecessor) != set(forbidden_paths):
        _fail("predecessor forbidden-route zero set changed")
    boundary_ids, modules_by_path, boundary_manifest_id = (
        _operation_evidence_for_optional_paths(optional_paths)
    )
    excluded_modules = tuple(
        sorted({module for modules in modules_by_path.values() for module in modules})
    )
    runtime_sources, allowlist = _scan_private_runtime(accounted, excluded_modules)
    profile = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    stage_profile = registry_v6.official_stage_profile_v6(
        registry_v6.official_counter_registry_v6()
    )
    measurement = accounted.measurement
    result = accounted.execution.model_only_result
    if (
        result.outcome.value != "PASS"
        or result.ground_binding_required
        or measurement.operational_execution_id
        != accounted.execution.operational_execution_id
        or measurement.result_id != result.result_id
        or shared.measurement_id != measurement.measurement_id
    ):
        _fail("runtime exclusion does not belong to one strict abstract PASS")
    window = AbstractQueryZeroRuntimeWindowV1(
        _WINDOW_ISSUER,
        measurement.measurement_id,
        accounted.preparation.preparation_id,
        accounted.preparation.manifest.runtime_tree_id,
        accounted.execution.operational_execution_id,
        result.logical_occurrence.logical_occurrence_id,
        result.route_attempt.route_attempt_id,
        result.route_context.route_decision_context_id,
        profile.profile_id,
        stage_profile.stage_profile_id,
        boundary_manifest_id,
        runtime_sources,
        allowlist,
        excluded_modules,
        optional_paths,
        required_paths,
    )
    registry = registry_v6.official_counter_registry_v6()
    resolutions: list[AbstractQueryNativeZeroResolutionV1] = []
    records: list[CounterRecordV1] = []
    for path in tuple(sorted(set(forbidden_paths) | set(optional_paths))):
        leaf = registry.by_path[path]
        if path in predecessor:
            proof = predecessor[path]
            resolution = AbstractQueryNativeZeroResolutionV1(
                _RESOLUTION_ISSUER,
                window.window_id,
                zeros.closure_id,
                path,
                leaf.semantics_id,
                leaf.owner,
                leaf.unit,
                leaf.scope,
                leaf.reducer,
                contexts[path],
                QueryZeroProofKindV1.FORBIDDEN_ROUTE_PREDECESSOR,
                proof.proof_id,
                proof.operation_boundary_site_ids,
                (),
            )
        else:
            resolution = AbstractQueryNativeZeroResolutionV1(
                _RESOLUTION_ISSUER,
                window.window_id,
                zeros.closure_id,
                path,
                leaf.semantics_id,
                leaf.owner,
                leaf.unit,
                leaf.scope,
                leaf.reducer,
                contexts[path],
                QueryZeroProofKindV1.OPTIONAL_STAGE_PRIVATE_RUNTIME_EXCLUSION,
                None,
                boundary_ids[path],
                modules_by_path[path],
            )
        resolutions.append(resolution)
        records.append(
            CounterRecordV1.observe(
                registry,
                path,
                0,
                recorder_id=resolution.resolution_id,
            )
        )
    return AbstractQueryNativeZeroEnvelopeV1(
        _ENVELOPE_ISSUER,
        source.lease.source_lease_id,
        report.report_id,
        zeros.closure_id,
        inventory.inventory_id,
        owner.envelope_id,
        lifecycle.envelope_id,
        shared.envelope_id,
        window,
        tuple(resolutions),
        tuple(records),
    )


def issue_abstract_query_native_zero_authority_v1(
    source: ModelOnlyRAPMSourceV1,
    accounted_execution: AccountedModelOnlyExecutionV2,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_envelope: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
    shared_envelope: shared_v2.AbstractAccountedSharedEnvelopeV2,
) -> AbstractQueryNativeZeroEnvelopeV1:
    roots = _exact_roots(
        source,
        accounted_execution,
        coverage_report,
        zero_closure,
        retained_inventory,
        query_owner_envelope,
        lifecycle_envelope,
        shared_envelope,
    )
    return _build_from_exact_roots(source, *roots)


def verify_abstract_query_native_zero_authority_bytes_v1(
    *,
    source: ModelOnlyRAPMSourceV1,
    accounted_execution: AccountedModelOnlyExecutionV2,
    coverage_report: coverage_v1.AbstractCertifiedAccountingCoverageReportV1,
    zero_closure: zero_v1.AbstractCertifiedZeroValueClosureV1,
    retained_inventory: retained_v1.AbstractPassRetainedV1EvidenceInventoryV1,
    query_owner_envelope: owner_v1.AbstractCertifiedQueryOwnerEnvelopeV1,
    lifecycle_envelope: lifecycle_v1.AbstractCertifiedLifecycleEnvelopeV1,
    shared_envelope: shared_v2.AbstractAccountedSharedEnvelopeV2,
    raw: bytes | str,
) -> AbstractQueryNativeZeroReplayV1:
    try:
        document = loads_canonical_json(raw)
        if type(document) is not dict:
            _fail("native-zero envelope must be one canonical object")
        payload = dict(document)
        claimed_id = payload.pop("abstract_query_native_zero_envelope_id", None)
        _cid(claimed_id, "claimed native-zero envelope")
        if content_id(ENVELOPE_DOMAIN, payload) != claimed_id:
            _fail("native-zero envelope content identity changed")
        roots = _exact_roots(
            source,
            accounted_execution,
            coverage_report,
            zero_closure,
            retained_inventory,
            query_owner_envelope,
            lifecycle_envelope,
            shared_envelope,
        )
        expected = _build_from_exact_roots(source, *roots)
        _same(document, expected.to_document(), "native-zero envelope document")
    except (ConstructionK7AbstractQueryNativeZeroAuthorityV1Error, TypeError, ValueError):
        return AbstractQueryNativeZeroReplayV1(
            QueryZeroReplayOutcomeV1.DOCUMENT_BLOCKED,
            None,
            ("EXACT_ROOT_OR_DOCUMENT_REPLAY_FAILED",),
        )
    return AbstractQueryNativeZeroReplayV1(
        QueryZeroReplayOutcomeV1.VERIFIED,
        expected.envelope_id,
        (),
    )


__all__ = [
    "AbstractQueryNativeZeroEnvelopeV1",
    "AbstractQueryNativeZeroReplayV1",
    "AbstractQueryNativeZeroResolutionV1",
    "AbstractQueryZeroRuntimeWindowV1",
    "ConstructionK7AbstractQueryNativeZeroAuthorityV1Error",
    "EXPECTED_COMBINED_FORMAL_RECORD_COUNT",
    "EXPECTED_NEW_FORMAL_RECORD_COUNT",
    "EXPECTED_OPTIONAL_RUNTIME_EXCLUSION_COUNT",
    "EXPECTED_PREDECESSOR_NATIVE_ZERO_COUNT",
    "EXPECTED_REQUIRED_BUILD_EPOCH_PATH_COUNT",
    "LOCAL_DOMAINS",
    "MODEL_ONLY_RUNTIME_COUNTER_ALLOWLIST",
    "QueryZeroProofKindV1",
    "QueryZeroReplayOutcomeV1",
    "RuntimeSourceFactV1",
    "issue_abstract_query_native_zero_authority_v1",
    "verify_abstract_query_native_zero_authority_bytes_v1",
]
