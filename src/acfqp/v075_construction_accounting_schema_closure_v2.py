"""Contract-1.85 construction-accounting schema closure.

The closure consumes an exact, issuer-backed independent verification of the
contract-1.84 foundation.  It materializes the additive v2 registry and its
stage/comparison/projection profiles.  It deliberately emits no CounterRecord,
WorkVector, terminal, occurrence closure, or campaign closure.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.construction_accounting_v2 import (
    EXPECTED_V2_LEAF_COUNT,
    EXPECTED_V2_OPERATIONAL_LEAF_COUNT,
    EXPECTED_V2_REQUIRED_LEAF_COUNT,
    StageKindV2,
    freeze_construction_accounting_schema_v2,
    official_actual_projection_profile_v2,
    official_comparison_profile_v2,
    official_counter_registry_v2,
    official_stage_profile_v2,
)
from acfqp.phase3e_ids import (
    V075_CONSTRUCTION_ACCOUNTING_SCHEMA_CLOSURE_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp import (
    v075_construction_native_accounting_foundation_independent_verifier_v2
    as foundation_verifier,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.85.0"
PROFILE_KEY = "v075_construction_accounting_schema_closure_v2"
UPSTREAM_PROFILE_KEY = (
    "v075_construction_native_accounting_foundation_"
    "independent_verifier_v2"
)
TERMINAL_SCOPE = "CONSTRUCTION_ACCOUNTING_SCHEMA_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_ACCOUNTING_V2_SCHEMA_FROZEN_"
    "LIVE_ACCOUNTING_AND_OCCURRENCE_CLOSURE_LOCKED"
)

EXPECTED_COUNTER_REGISTRY_V2_ID = (
    "8277a7ae8d32e117dc9b8f1c6d06c213"
    "f7b0a15981c1d60d37ec98d2ae1516bc"
)
EXPECTED_STAGE_PROFILE_V2_ID = (
    "8684dd5ad689ec160f390eeb1a3ca446"
    "7603c2c9c46734719fecf29796e57f63"
)
EXPECTED_COMPARISON_PROFILE_V2_ID = (
    "74c635f0d1c0f6e151de6f982b279b2"
    "73f4165ab809d671fc1562784b1f9b509"
)
EXPECTED_ACTUAL_PROJECTION_PROFILE_V2_ID = (
    "e0e0e19f6a91fef66161b5b168a72f2"
    "03b7c9e70fa9b2a0c8cb73abd062ad6e3"
)

_CRITICAL_LIVE_RECORDER_GAPS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.exit_failures",
    "process.exit_successes",
    "process.launches",
)
_CLOSURE_OPERATION_PATHS = (
    "closure.reconciliation_interval_log_search_evaluations",
    "closure.reconciliation_interval_row_evaluations",
    "closure.reconciliation_model_rows_built",
    "closure.reconciliation_policy_assignments_evaluated",
    "closure.reconciliation_semantic_record_replays",
    "closure.reconciliation_semantic_role_closures",
    "closure.reconciliation_source_units_compiled",
)
_REPLAY_MISMATCH = (
    "contract-1.85 construction-accounting schema replay mismatch"
)


class V075ConstructionAccountingSchemaV2Violation(ValueError):
    """The verified foundation or accounting schema changed."""


class V075ConstructionAccountingSchemaProductionV2NotReady(RuntimeError):
    """The schema-only cut cannot authorize live or scientific execution."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionAccountingSchemaV2Violation(message)


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > 64 * 1024 * 1024:
        _fail(f"{label} bytes are absent or exceed the cap")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionAccountingSchemaV2Violation(
            f"{label} is not strict UTF-8 JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _thaw_json(item)
            for key, item in value.items()
        }
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    return value


def _verify_foundation_binding(
    *,
    upstream: (
        foundation_verifier
        .V075ConstructionNativeAccountingIndependentVerificationV2
    ),
    foundation_bytes: bytes,
) -> dict[str, Any]:
    if (
        type(upstream)
        is not foundation_verifier
        .V075ConstructionNativeAccountingIndependentVerificationV2
    ):
        _fail("schema closure requires exact independent contract 1.84")
    document = _strict_document(
        foundation_bytes, label="verified accounting foundation"
    )
    if (
        document.get("attestation_id") != upstream.attestation_id
        or hashlib.sha256(foundation_bytes).hexdigest()
        != upstream.attestation_sha256
        or len(foundation_bytes) != upstream.attestation_byte_count
        or document.get("boundary_profile_id")
        != upstream.boundary_profile_id
        or document.get("coverage_matrix_id")
        != upstream.coverage_matrix_id
        or document.get("role_registry_id") != upstream.role_registry_id
        or document.get("terminal_registry_id")
        != upstream.terminal_registry_id
    ):
        _fail("contract-1.84 foundation identity changed")
    boundary = document.get("boundary_profile")
    coverage = document.get("coverage_matrix")
    if (
        type(boundary) is not dict
        or type(coverage) is not dict
        or boundary.get("future_counter_registry_key")
        != "acfqp_counter_registry_v2"
        or boundary.get("counter_registry_v2_materialized") is not False
        or coverage.get("counter_registry_v2_materialized") is not False
        or coverage.get("planned_counter_semantics_frozen") is not False
        or document.get("all_path_native_accounting_complete") is not False
        or document.get("terminal_campaign_closure_complete") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("fresh_heldout_accessed") is not False
        or document.get("observer_opened") is not False
        or document.get("target_accessed") is not False
    ):
        _fail("contract-1.84 locked foundation semantics changed")
    parse_content_id(document.get("multiround_result_id"))
    parse_content_id(document.get("terminal_registry_id"))
    if document.get("multiround_status") != "CHILD_ACTION_ROW_CAP_EXCEEDED":
        _fail("registered root-only terminal cause changed")
    return document


_SCHEMA_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionAccountingSchemaClosureV2:
    _issuer: InitVar[object]
    upstream_attestation_id: str
    upstream_verification_id: str
    multiround_result_id: str
    terminal_derivation_registry_id: str
    counter_registry: Mapping[str, Any]
    stage_profile: Mapping[str, Any]
    comparison_profile: Mapping[str, Any]
    actual_projection_profile: Mapping[str, Any]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value in (
            self.upstream_attestation_id,
            self.upstream_verification_id,
            self.multiround_result_id,
            self.terminal_derivation_registry_id,
        ):
            parse_content_id(value)
        if _issuer is not _SCHEMA_ISSUER:
            _fail("construction accounting schema closure is caller-minted")
        exact = freeze_construction_accounting_schema_v2()
        for value, label in (
            (self.counter_registry, "counter_registry"),
            (self.stage_profile, "stage_profile"),
            (self.comparison_profile, "comparison_profile"),
            (self.actual_projection_profile, "actual_projection_profile"),
        ):
            if type(value) is not dict or value != exact[label]:
                _fail(f"{label} differs from the exact frozen schema")
        for field_name in (
            "counter_registry",
            "stage_profile",
            "comparison_profile",
            "actual_projection_profile",
        ):
            object.__setattr__(
                self,
                field_name,
                _freeze_json(getattr(self, field_name)),
            )
        object.__setattr__(
            self,
            "_closure_id",
            content_id(
                V075_CONSTRUCTION_ACCOUNTING_SCHEMA_CLOSURE_V2_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        registry = self.counter_registry
        stage = self.stage_profile
        comparison = self.comparison_profile
        actual = self.actual_projection_profile
        return {
            "schema": "acfqp.v075_construction_accounting_schema_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "upstream_profile_key": UPSTREAM_PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "upstream_attestation_id": self.upstream_attestation_id,
            "upstream_verification_id": self.upstream_verification_id,
            "multiround_result_id": self.multiround_result_id,
            "multiround_status": "CHILD_ACTION_ROW_CAP_EXCEEDED",
            "terminal_derivation_registry_id": (
                self.terminal_derivation_registry_id
            ),
            "counter_registry": _thaw_json(registry),
            "counter_registry_id": registry["counter_registry_id"],
            "stage_profile": _thaw_json(stage),
            "stage_profile_id": stage["stage_profile_id"],
            "comparison_profile": _thaw_json(comparison),
            "comparison_profile_id": comparison["comparison_profile_id"],
            "actual_projection_profile": _thaw_json(actual),
            "actual_projection_profile_id": (
                actual["actual_projection_profile_id"]
            ),
            "base_v1_leaf_count": 49,
            "base_v1_operational_leaf_count": 34,
            "v2_leaf_count": EXPECTED_V2_LEAF_COUNT,
            "v2_operational_leaf_count": (
                EXPECTED_V2_OPERATIONAL_LEAF_COUNT
            ),
            "v2_required_leaf_count": EXPECTED_V2_REQUIRED_LEAF_COUNT,
            "registered_stage_count": len(StageKindV2),
            "shared_axis_count": 8,
            "projection_term_count": EXPECTED_V2_OPERATIONAL_LEAF_COUNT,
            "reserved_initial_path_count": 13,
            "closed_reconciliation_operation_path_count": len(
                _CLOSURE_OPERATION_PATHS
            ),
            "closed_reconciliation_operation_paths": list(
                _CLOSURE_OPERATION_PATHS
            ),
            "observer_rejection_lane": "diagnostic",
            "observer_rejection_projected": False,
            "accepted_draw_projection_axis": "kernel_transition_calls",
            "base_counter_registry_v1_mutated": False,
            "legacy_custom_counters_accepted_as_native_records": False,
            "caller_summary_totals_accepted_as_native_records": False,
            "initial_build_is_rebuild": False,
            "initial_acquisition_is_rebuild": False,
            "closure_recomputation_reuses_initial_counter_paths": False,
            "all_operational_leaves_project_exactly_once": True,
            "projection_coefficients_are_one": True,
            "scalar_cost_defined": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "stage_recorder_must_open_before_owned_stage": True,
            "stage_start_attestation_semantics_frozen": False,
            "stage_completion_attestation_semantics_frozen": False,
            "live_counter_record_count": 0,
            "work_vector_count": 0,
            "comparison_vector_count": 0,
            "actual_projection_proof_count": 0,
            "critical_live_recorder_gap_count": len(
                _CRITICAL_LIVE_RECORDER_GAPS
            ),
            "critical_live_recorder_gaps": list(
                _CRITICAL_LIVE_RECORDER_GAPS
            ),
            "critical_live_recorder_gap_list_is_exhaustive": False,
            "legacy_custom_distinct_path_count": 87,
            "legacy_custom_paths_native_semantics_complete": False,
            "unmapped_operation_requires_registry_revision": True,
            "counter_registry_v2_materialized": True,
            "planned_counter_semantics_frozen": True,
            "stage_profile_v2_materialized": True,
            "comparison_profile_v2_materialized": True,
            "actual_projection_profile_v2_materialized": True,
            "live_from_stage_start_instrumentation_complete": False,
            "all_path_native_accounting_complete": False,
            "typed_route_attempt_terminal_complete": False,
            "logical_occurrence_closure_complete": False,
            "campaign_closure_complete": False,
            "complete_bundle_verifier_complete": False,
            "loaded_source_receipt_complete": False,
            "counter_completeness_gate_passed": False,
            "accounting_gate_passed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "fresh_heldout_accessed": False,
            "scientific_endpoint_credit_allowed": False,
            "observer_opened": False,
            "target_accessed": False,
            "kernel_accessed": False,
            "planner_worker_launched": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "workload_economics_gate_status": "NOT_RUN",
            "counter_completeness_gate_status": "NOT_RUN",
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "construction accounting schema closures are in-memory-only"
        )


def materialize_v075_construction_accounting_schema_v2(
    *,
    upstream: (
        foundation_verifier
        .V075ConstructionNativeAccountingIndependentVerificationV2
    ),
    foundation_bytes: bytes,
) -> V075ConstructionAccountingSchemaClosureV2:
    """Bind the exact v2 schema to an independently verified 1.84 cut."""

    try:
        foundation = _verify_foundation_binding(
            upstream=upstream,
            foundation_bytes=foundation_bytes,
        )
        registry = official_counter_registry_v2()
        stage = official_stage_profile_v2(registry)
        comparison = official_comparison_profile_v2(registry)
        actual = official_actual_projection_profile_v2(
            registry, comparison
        )
        if (
            registry.registry_id != EXPECTED_COUNTER_REGISTRY_V2_ID
            or stage.stage_profile_id != EXPECTED_STAGE_PROFILE_V2_ID
            or comparison.comparison_profile_id
            != EXPECTED_COMPARISON_PROFILE_V2_ID
            or actual.actual_projection_profile_id
            != EXPECTED_ACTUAL_PROJECTION_PROFILE_V2_ID
        ):
            _fail("registered construction-accounting v2 identities changed")
        frozen = freeze_construction_accounting_schema_v2()
        return V075ConstructionAccountingSchemaClosureV2(
            _SCHEMA_ISSUER,
            upstream.attestation_id,
            upstream.verification_id,
            foundation["multiround_result_id"],
            foundation["terminal_registry_id"],
            frozen["counter_registry"],
            frozen["stage_profile"],
            frozen["comparison_profile"],
            frozen["actual_projection_profile"],
        )
    except Exception:
        raise V075ConstructionAccountingSchemaV2Violation(
            _REPLAY_MISMATCH
        ) from None


def assert_v075_construction_accounting_schema_production_gate_v2(
    closure: V075ConstructionAccountingSchemaClosureV2,
) -> NoReturn:
    if type(closure) is not V075ConstructionAccountingSchemaClosureV2:
        _fail("production gate rejects construction-accounting duck types")
    _ = closure.closure_id
    raise V075ConstructionAccountingSchemaProductionV2NotReady(
        "contract 1.85 freezes schemas only; live from-stage-start records, "
        "stage/attempt aggregation, typed terminal and occurrence/campaign "
        "closure, complete-bundle verification, production, fresh held-out "
        "execution, science, and certificates remain locked"
    )


__all__ = [
    "EXPECTED_ACTUAL_PROJECTION_PROFILE_V2_ID",
    "EXPECTED_COMPARISON_PROFILE_V2_ID",
    "EXPECTED_COUNTER_REGISTRY_V2_ID",
    "EXPECTED_STAGE_PROFILE_V2_ID",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "V075ConstructionAccountingSchemaClosureV2",
    "V075ConstructionAccountingSchemaProductionV2NotReady",
    "V075ConstructionAccountingSchemaV2Violation",
    "assert_v075_construction_accounting_schema_production_gate_v2",
    "materialize_v075_construction_accounting_schema_v2",
]
