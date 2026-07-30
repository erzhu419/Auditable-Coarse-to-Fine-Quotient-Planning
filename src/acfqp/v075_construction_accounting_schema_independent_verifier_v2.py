"""Independent verifier for the contract-1.85 accounting-schema closure.

This verifier deliberately does not import or invoke either
``construction_accounting_v2`` or its schema-closure producer.  It replays
contract 1.84 first, takes the immutable official accounting-v1 catalogue as
an exact prefix, independently reconstructs the twenty additive v2 leaves,
the eight stage rules, and both projection profiles as plain documents, and
then compares the claimed canonical bytes byte-for-byte.

The result is schema-only evidence.  It contains no live CounterRecord,
WorkVector, terminal, occurrence, campaign, production, or scientific
authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import accounting_v1 as accounting
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import (
    v075_construction_native_accounting_foundation_independent_verifier_v2
    as foundation_verifier,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.85.0"
PROFILE_KEY = (
    "v075_construction_accounting_schema_independent_verifier_v2"
)
PRODUCER_PROFILE_KEY = (
    "v075_construction_accounting_schema_closure_v2"
)
UPSTREAM_PROFILE_KEY = (
    "v075_construction_native_accounting_foundation_"
    "independent_verifier_v2"
)

EXPECTED_BASE_COUNTER_REGISTRY_ID = (
    "27063139cc8c1f66416a9b285373d610"
    "67ee22d16370f394a419f85878b63a88"
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

EXPECTED_V2_LEAF_COUNT = 69
EXPECTED_V2_OPERATIONAL_LEAF_COUNT = 53
EXPECTED_V2_REQUIRED_LEAF_COUNT = 62
EXPECTED_STAGE_COUNT = 8
EXPECTED_SHARED_AXIS_COUNT = 8

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
LIVE_FROM_STAGE_START_INSTRUMENTATION_COMPLETE = False
ALL_PATH_NATIVE_ACCOUNTING_COMPLETE = False
TYPED_ROUTE_ATTEMPT_TERMINAL_COMPLETE = False
LOGICAL_OCCURRENCE_CLOSURE_COMPLETE = False
CAMPAIGN_CLOSURE_COMPLETE = False
COMPLETE_BUNDLE_VERIFIER_COMPLETE = False
COUNTER_COMPLETENESS_GATE_PASSED = False
ACCOUNTING_GATE_PASSED = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

_DOMAINS = MappingProxyType(
    {
        "counter_registry": "acfqp:counter-registry:v2",
        "stage_profile": "acfqp:construction-stage-profile:v2",
        "comparison_profile": "acfqp:comparison-profile:v2",
        "actual_projection_profile": (
            "acfqp:actual-projection-profile:v2"
        ),
        "closure": (
            "acfqp:v075-construction-accounting-schema-closure:v2"
        ),
        "verification": (
            "acfqp:v075-construction-accounting-schema-"
            "independent-verification:v2"
        ),
    }
)

_REPLAY_MISMATCH = (
    "independent contract-1.85 construction-accounting schema replay "
    "did not match registered evidence"
)


class V075ConstructionAccountingSchemaIndependentV2Violation(ValueError):
    """The raw foundation or independently reconstructed schema changed."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionAccountingSchemaIndependentV2Violation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ConstructionAccountingSchemaIndependentV2Violation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            _DOMAINS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ConstructionAccountingSchemaIndependentV2Violation(
            str(error)
        ) from error


def _strict_document(
    raw: bytes,
    *,
    label: str,
    byte_cap: int = 64 * 1024 * 1024,
) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > byte_cap:
        _fail(f"{label} bytes are absent, mistyped, or over cap")

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"{label} contains duplicate JSON keys")
            result[key] = value
        return result

    try:
        document = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=no_duplicates,
            parse_constant=lambda item: _fail(
                f"{label} contains forbidden numeric constant {item}"
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionAccountingSchemaIndependentV2Violation(
            f"{label} is not strict UTF-8 JSON"
        ) from error
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != raw
    ):
        _fail(f"{label} is not one canonical JSON object")
    return document


def _leaf(
    *,
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    lane: str,
    scope: str,
    reducer: str = "sum",
    comparison_axis: str | None,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "path": path,
        "semantics_id": semantics_id,
        "owner": owner,
        "unit": unit,
        "lane": lane,
        "scope": scope,
        "reducer": reducer,
        "comparison_axis": comparison_axis,
        "required": required,
    }


# These twenty rows are intentionally literal and independent of the
# producer/core implementation.
_ADDITIVE_V2_LEAVES = tuple(
    sorted(
        (
            _leaf(
                path="acquisition.initial_observer_accepted_draws",
                semantics_id="v075-initial-observer-accepted-draw-v2",
                owner="v075_private_observer_boundary_v2",
                unit="accepted_draws",
                lane="operational",
                scope=(
                    "construction_occurrence_initial_acquisition_prefix"
                ),
                comparison_axis="kernel_transition_calls",
            ),
            _leaf(
                path="acquisition.initial_observer_random_word_calls",
                semantics_id=(
                    "v075-initial-observer-random-word-call-v2"
                ),
                owner="v075_private_observer_boundary_v2",
                unit="random_word_calls",
                lane="operational",
                scope=(
                    "construction_occurrence_initial_acquisition_prefix"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="acquisition.initial_observer_rejections",
                semantics_id="v075-initial-observer-rejection-v2",
                owner="v075_private_observer_boundary_v2",
                unit="rejections",
                lane="diagnostic",
                scope=(
                    "construction_occurrence_initial_acquisition_prefix"
                ),
                comparison_axis=None,
            ),
            _leaf(
                path="acquisition.initial_outcome_aggregate_rows",
                semantics_id=(
                    "v075-initial-outcome-aggregate-row-materialization-v2"
                ),
                owner="v075_private_observer_boundary_v2",
                unit="aggregate_rows",
                lane="operational",
                scope=(
                    "construction_occurrence_initial_acquisition_prefix"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="acquisition.initial_signed_batches",
                semantics_id=(
                    "v075-initial-signed-batch-materialization-v2"
                ),
                owner="v075_private_observer_boundary_v2",
                unit="signed_batches",
                lane="operational",
                scope=(
                    "construction_occurrence_initial_acquisition_prefix"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="acquisition.initial_support_freezes",
                semantics_id=(
                    "v075-initial-support-freeze-materialization-v2"
                ),
                owner=(
                    "v075_observer_signed_batch_control_authority_v2"
                ),
                unit="support_freezes",
                lane="operational",
                scope=(
                    "construction_occurrence_initial_acquisition_prefix"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="build.initial_interval_log_search_evaluations",
                semantics_id="v075-initial-interval-log-search-eval-v2",
                owner="v075_batch_native_planning_backend_v2",
                unit="log_search_evaluations",
                lane="operational",
                scope="construction_occurrence_initial_build_epoch",
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="build.initial_interval_row_evaluations",
                semantics_id="v075-initial-interval-row-eval-v2",
                owner="v075_batch_native_planning_backend_v2",
                unit="row_behavior_evaluations",
                lane="operational",
                scope="construction_occurrence_initial_build_epoch",
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="build.initial_model_rows_built",
                semantics_id="v075-initial-model-row-build-v2",
                owner="v075_live_incremental_model_authority_v2",
                unit="model_rows",
                lane="operational",
                scope="construction_occurrence_initial_build_epoch",
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="build.initial_policy_assignments_evaluated",
                semantics_id="v075-initial-policy-assignment-eval-v2",
                owner="v075_batch_native_planning_backend_v2",
                unit="policy_assignments",
                lane="operational",
                scope="construction_occurrence_initial_build_epoch",
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="build.initial_semantic_record_replays",
                semantics_id="v075-initial-semantic-record-replay-v2",
                owner="v075_semantic_replay_instrumentation_v2",
                unit="record_replays",
                lane="operational",
                scope="construction_occurrence_initial_build_epoch",
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="build.initial_semantic_role_closures",
                semantics_id="v075-initial-semantic-role-closure-v2",
                owner="v075_semantic_replay_instrumentation_v2",
                unit="role_closures",
                lane="operational",
                scope="construction_occurrence_initial_build_epoch",
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="build.initial_source_units_compiled",
                semantics_id="v075-initial-row-source-unit-compile-v2",
                owner="v075_live_incremental_model_authority_v2",
                unit="row_source_units",
                lane="operational",
                scope="construction_occurrence_initial_build_epoch",
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path=(
                    "closure.reconciliation_interval_log_search_"
                    "evaluations"
                ),
                semantics_id=(
                    "v075-closed-reconciliation-interval-log-search-"
                    "eval-v2"
                ),
                owner="v075_batch_native_planning_backend_v2",
                unit="log_search_evaluations",
                lane="operational",
                scope=(
                    "construction_occurrence_closed_reconciliation_"
                    "and_terminalization"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path=(
                    "closure.reconciliation_interval_row_evaluations"
                ),
                semantics_id=(
                    "v075-closed-reconciliation-interval-row-eval-v2"
                ),
                owner="v075_batch_native_planning_backend_v2",
                unit="row_behavior_evaluations",
                lane="operational",
                scope=(
                    "construction_occurrence_closed_reconciliation_"
                    "and_terminalization"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="closure.reconciliation_model_rows_built",
                semantics_id=(
                    "v075-closed-reconciliation-model-row-build-v2"
                ),
                owner="v075_live_incremental_model_authority_v2",
                unit="model_rows",
                lane="operational",
                scope=(
                    "construction_occurrence_closed_reconciliation_"
                    "and_terminalization"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path=(
                    "closure.reconciliation_policy_assignments_evaluated"
                ),
                semantics_id=(
                    "v075-closed-reconciliation-policy-assignment-eval-v2"
                ),
                owner="v075_batch_native_planning_backend_v2",
                unit="policy_assignments",
                lane="operational",
                scope=(
                    "construction_occurrence_closed_reconciliation_"
                    "and_terminalization"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="closure.reconciliation_semantic_record_replays",
                semantics_id=(
                    "v075-closed-reconciliation-semantic-record-replay-v2"
                ),
                owner="v075_semantic_replay_instrumentation_v2",
                unit="record_replays",
                lane="operational",
                scope=(
                    "construction_occurrence_closed_reconciliation_"
                    "and_terminalization"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="closure.reconciliation_semantic_role_closures",
                semantics_id=(
                    "v075-closed-reconciliation-semantic-role-closure-v2"
                ),
                owner="v075_semantic_replay_instrumentation_v2",
                unit="role_closures",
                lane="operational",
                scope=(
                    "construction_occurrence_closed_reconciliation_"
                    "and_terminalization"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
            _leaf(
                path="closure.reconciliation_source_units_compiled",
                semantics_id=(
                    "v075-closed-reconciliation-row-source-unit-compile-v2"
                ),
                owner="v075_live_incremental_model_authority_v2",
                unit="row_source_units",
                lane="operational",
                scope=(
                    "construction_occurrence_closed_reconciliation_"
                    "and_terminalization"
                ),
                comparison_axis="nonkernel_compute_events",
            ),
        ),
        key=lambda row: row["path"],
    )
)

_COMMON_RUNTIME_PATHS = frozenset(
    {
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
    }
)
_ROUTE_RECONCILIATION_PATHS = frozenset(
    {
        "route.attempts",
        "route.failures",
        "route.successes",
        "solver.attempts",
        "solver.failures",
        "solver.successes",
    }
)
_CLOSED_RECONCILIATION_OPERATION_PATHS = (
    "closure.reconciliation_interval_log_search_evaluations",
    "closure.reconciliation_interval_row_evaluations",
    "closure.reconciliation_model_rows_built",
    "closure.reconciliation_policy_assignments_evaluated",
    "closure.reconciliation_semantic_record_replays",
    "closure.reconciliation_semantic_role_closures",
    "closure.reconciliation_source_units_compiled",
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

_AXES = (
    {
        "name": "kernel_transition_calls",
        "unit": "calls",
        "reducer": "sum",
        "semantics": "Authoritative ground-kernel transition evaluations.",
    },
    {
        "name": "nonkernel_compute_events",
        "unit": "registered_events",
        "reducer": "sum",
        "semantics": (
            "Registered non-kernel, non-process compute events."
        ),
    },
    {
        "name": "output_bytes",
        "unit": "bytes",
        "reducer": "sum",
        "semantics": (
            "New result, trace, certificate, counter, and manifest bytes."
        ),
    },
    {
        "name": "peak_mounted_bytes",
        "unit": "bytes",
        "reducer": "max",
        "semantics": (
            "Peak simultaneously mounted payload within a decision point."
        ),
    },
    {
        "name": "peak_working_bytes",
        "unit": "bytes",
        "reducer": "max",
        "semantics": "Verified peak or frozen working-set capacity.",
    },
    {
        "name": "process_launches",
        "unit": "launches",
        "reducer": "sum",
        "semantics": "New OS or isolated worker process launches.",
    },
    {
        "name": "read_bytes",
        "unit": "bytes",
        "reducer": "sum",
        "semantics": (
            "Bytes read from pre-existing artifacts, models, queries, "
            "or capabilities."
        ),
    },
    {
        "name": "staged_bytes",
        "unit": "bytes",
        "reducer": "sum",
        "semantics": (
            "Bytes copied or bound into the execution sandbox."
        ),
    },
)


def _prefix_paths(
    required_paths: tuple[str, ...], *prefixes: str
) -> frozenset[str]:
    return frozenset(
        path
        for path in required_paths
        if any(path.startswith(prefix) for prefix in prefixes)
    )


def _reconstruct_schema_documents() -> dict[str, dict[str, Any]]:
    """Independently reconstruct the four exact producer schema documents."""

    base = accounting.official_counter_registry_v1()
    base.validate_official_catalogue()
    if (
        base.registry_id != EXPECTED_BASE_COUNTER_REGISTRY_ID
        or len(base.leaves) != 49
        or len(base.operational_leaves) != 34
        or len(_ADDITIVE_V2_LEAVES) != 20
    ):
        _fail("immutable accounting-v1 prefix or additive rows changed")
    base_rows = tuple(row.to_dict() for row in base.leaves)
    new_paths = {row["path"] for row in _ADDITIVE_V2_LEAVES}
    if new_paths & {row["path"] for row in base_rows}:
        _fail("additive v2 paths overlap the accounting-v1 prefix")
    leaves = tuple(
        sorted(
            (*base_rows, *_ADDITIVE_V2_LEAVES),
            key=lambda row: row["path"],
        )
    )
    operational = tuple(
        row for row in leaves if row["lane"] == "operational"
    )
    required_paths = tuple(
        row["path"] for row in leaves if row["required"] is True
    )
    if (
        len(leaves) != EXPECTED_V2_LEAF_COUNT
        or len(operational) != EXPECTED_V2_OPERATIONAL_LEAF_COUNT
        or len(required_paths) != EXPECTED_V2_REQUIRED_LEAF_COUNT
        or sum(
            row["lane"] == "diagnostic"
            and row["path"]
            == "acquisition.initial_observer_rejections"
            for row in leaves
        )
        != 1
    ):
        _fail("construction v2 leaf cardinality/lane changed")

    registry_payload = {
        "schema": "acfqp.counter_registry.v2",
        "schema_version": SCHEMA_VERSION,
        "registry_key": "acfqp_counter_registry_v2",
        "base_counter_registry_id": base.registry_id,
        "base_registry_is_immutable_exact_prefix": True,
        "leaves": list(leaves),
    }
    registry_id = _hash("counter_registry", registry_payload)
    registry = {
        **registry_payload,
        "counter_registry_id": registry_id,
    }

    initial_build = frozenset(
        {
            "build.initial_interval_log_search_evaluations",
            "build.initial_interval_row_evaluations",
            "build.initial_model_rows_built",
            "build.initial_policy_assignments_evaluated",
            "build.initial_semantic_record_replays",
            "build.initial_semantic_role_closures",
            "build.initial_source_units_compiled",
        }
    )
    abstract = frozenset(
        {
            "common.abstract_audit_obligations",
            "common.abstract_bellman_backups",
        }
    )
    stage_sets = {
        "PREOPEN_COMMON_PREFIX": _COMMON_RUNTIME_PATHS,
        "INITIAL_ACQUISITION": (
            _COMMON_RUNTIME_PATHS
            | _prefix_paths(required_paths, "acquisition.")
        ),
        "INITIAL_MODEL_BUILD": _COMMON_RUNTIME_PATHS | initial_build,
        "FAILED_ABSTRACT_PREFIX": _COMMON_RUNTIME_PATHS | abstract,
        "CLOSED_RECONCILIATION_AND_TERMINALIZATION": (
            _COMMON_RUNTIME_PATHS
            | frozenset(
                {
                    "route.attempts",
                    "route.failures",
                    "route.successes",
                }
            )
            | _prefix_paths(required_paths, "closure.")
        ),
        "LOCAL_ATTEMPT": (
            _COMMON_RUNTIME_PATHS
            | _ROUTE_RECONCILIATION_PATHS
            | _prefix_paths(required_paths, "local.", "control.")
        ),
        "DIRECT_FALLBACK": (
            _COMMON_RUNTIME_PATHS
            | _ROUTE_RECONCILIATION_PATHS
            | _prefix_paths(required_paths, "fallback.", "control.")
        ),
        "REBUILD": (
            _COMMON_RUNTIME_PATHS
            | _prefix_paths(required_paths, "rebuild.")
        ),
    }
    rules = [
        {
            "stage_kind": stage,
            "allowed_nonzero_paths": sorted(paths),
        }
        for stage, paths in sorted(stage_sets.items())
    ]
    if (
        len(rules) != EXPECTED_STAGE_COUNT
        or any(
            not set(row["allowed_nonzero_paths"])
            <= set(required_paths)
            for row in rules
        )
    ):
        _fail("construction stage rules changed")
    stage_payload = {
        "schema": "acfqp.construction_stage_profile.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "construction_stage_exclusivity_v2",
        "counter_registry_id": registry_id,
        "rules": rules,
    }
    stage = {
        **stage_payload,
        "stage_profile_id": _hash("stage_profile", stage_payload),
    }

    axes = [dict(row) for row in _AXES]
    axis_reducers = {
        row["name"]: row["reducer"] for row in axes
    }
    terms = [
        {
            "source_leaf": row["path"],
            "target_axis": row["comparison_axis"],
            "coefficient": 1,
            "source_lane": "operational",
            "source_semantics_id": row["semantics_id"],
            "reducer": axis_reducers[row["comparison_axis"]],
        }
        for row in operational
    ]
    comparison_payload = {
        "schema": "acfqp.comparison_profile.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "comparison_profile_shared_resources_v2",
        "counter_registry_id": registry_id,
        "axes": axes,
        "terms": terms,
    }
    comparison = {
        **comparison_payload,
        "comparison_profile_id": _hash(
            "comparison_profile", comparison_payload
        ),
    }
    actual_payload = {
        "schema": "acfqp.actual_projection_profile.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": "actual_projection_construction_v2",
        "counter_registry_id": registry_id,
        "comparison_profile_id": comparison["comparison_profile_id"],
        "terms": terms,
    }
    actual = {
        **actual_payload,
        "actual_projection_profile_id": _hash(
            "actual_projection_profile", actual_payload
        ),
    }
    if (
        registry_id != EXPECTED_COUNTER_REGISTRY_V2_ID
        or stage["stage_profile_id"] != EXPECTED_STAGE_PROFILE_V2_ID
        or comparison["comparison_profile_id"]
        != EXPECTED_COMPARISON_PROFILE_V2_ID
        or actual["actual_projection_profile_id"]
        != EXPECTED_ACTUAL_PROJECTION_PROFILE_V2_ID
        or len(axes) != EXPECTED_SHARED_AXIS_COUNT
        or len(terms) != EXPECTED_V2_OPERATIONAL_LEAF_COUNT
    ):
        _fail("independently reconstructed schema identities changed")
    return {
        "counter_registry": registry,
        "stage_profile": stage,
        "comparison_profile": comparison,
        "actual_projection_profile": actual,
    }


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
        _fail("schema replay requires exact independent contract 1.84")
    foundation = _strict_document(
        foundation_bytes,
        label="verified accounting foundation",
    )
    if (
        foundation.get("attestation_id") != upstream.attestation_id
        or hashlib.sha256(foundation_bytes).hexdigest()
        != upstream.attestation_sha256
        or len(foundation_bytes) != upstream.attestation_byte_count
        or foundation.get("boundary_profile_id")
        != upstream.boundary_profile_id
        or foundation.get("coverage_matrix_id")
        != upstream.coverage_matrix_id
        or foundation.get("role_registry_id")
        != upstream.role_registry_id
        or foundation.get("terminal_registry_id")
        != upstream.terminal_registry_id
    ):
        _fail("contract-1.84 foundation binding changed")
    boundary = foundation.get("boundary_profile")
    coverage = foundation.get("coverage_matrix")
    if (
        type(boundary) is not dict
        or type(coverage) is not dict
        or boundary.get("future_counter_registry_key")
        != "acfqp_counter_registry_v2"
        or boundary.get("counter_registry_v2_materialized") is not False
        or coverage.get("counter_registry_v2_materialized") is not False
        or coverage.get("planned_counter_semantics_frozen") is not False
        or foundation.get("all_path_native_accounting_complete")
        is not False
        or foundation.get("terminal_campaign_closure_complete")
        is not False
        or foundation.get("official_execution_allowed") is not False
        or foundation.get("fresh_heldout_accessed") is not False
        or foundation.get("observer_opened") is not False
        or foundation.get("target_accessed") is not False
        or foundation.get("multiround_status")
        != "CHILD_ACTION_ROW_CAP_EXCEEDED"
    ):
        _fail("contract-1.84 locked semantics changed")
    _cid(foundation.get("multiround_result_id"), "multiround result")
    _cid(
        foundation.get("terminal_registry_id"),
        "terminal derivation registry",
    )
    return foundation


def _reconstruct_closure_document(
    *,
    upstream: (
        foundation_verifier
        .V075ConstructionNativeAccountingIndependentVerificationV2
    ),
    foundation_bytes: bytes,
) -> dict[str, Any]:
    foundation = _verify_foundation_binding(
        upstream=upstream,
        foundation_bytes=foundation_bytes,
    )
    frozen = _reconstruct_schema_documents()
    registry = frozen["counter_registry"]
    stage = frozen["stage_profile"]
    comparison = frozen["comparison_profile"]
    actual = frozen["actual_projection_profile"]
    payload = {
        "schema": (
            "acfqp.v075_construction_accounting_schema_closure.v2"
        ),
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "upstream_profile_key": UPSTREAM_PROFILE_KEY,
        "terminal_scope": "CONSTRUCTION_ACCOUNTING_SCHEMA_ONLY",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": (
            "CONSTRUCTION_ACCOUNTING_V2_SCHEMA_FROZEN_"
            "LIVE_ACCOUNTING_AND_OCCURRENCE_CLOSURE_LOCKED"
        ),
        "upstream_attestation_id": upstream.attestation_id,
        "upstream_verification_id": upstream.verification_id,
        "multiround_result_id": foundation["multiround_result_id"],
        "multiround_status": "CHILD_ACTION_ROW_CAP_EXCEEDED",
        "terminal_derivation_registry_id": (
            foundation["terminal_registry_id"]
        ),
        "counter_registry": registry,
        "counter_registry_id": registry["counter_registry_id"],
        "stage_profile": stage,
        "stage_profile_id": stage["stage_profile_id"],
        "comparison_profile": comparison,
        "comparison_profile_id": comparison["comparison_profile_id"],
        "actual_projection_profile": actual,
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
        "registered_stage_count": EXPECTED_STAGE_COUNT,
        "shared_axis_count": EXPECTED_SHARED_AXIS_COUNT,
        "projection_term_count": EXPECTED_V2_OPERATIONAL_LEAF_COUNT,
        "reserved_initial_path_count": 13,
        "closed_reconciliation_operation_path_count": 7,
        "closed_reconciliation_operation_paths": list(
            _CLOSED_RECONCILIATION_OPERATION_PATHS
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
    return {**payload, "closure_id": _hash("closure", payload)}


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionAccountingSchemaIndependentVerificationV2:
    _issuer: InitVar[object]
    closure_id: str
    closure_sha256: str
    closure_byte_count: int
    upstream_attestation_id: str
    upstream_verification_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.closure_id, "schema closure"),
            (self.closure_sha256, "schema closure bytes"),
            (self.upstream_attestation_id, "upstream attestation"),
            (self.upstream_verification_id, "upstream verification"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (
                self.actual_projection_profile_id,
                "actual projection profile",
            ),
        ):
            _cid(value, label)
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.closure_byte_count) is not int
            or self.closure_byte_count <= 0
        ):
            _fail("independent schema verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_accounting_schema_"
                "independent_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "producer_profile_key": PRODUCER_PROFILE_KEY,
            "closure_id": self.closure_id,
            "closure_sha256": self.closure_sha256,
            "closure_byte_count": self.closure_byte_count,
            "upstream_attestation_id": self.upstream_attestation_id,
            "upstream_verification_id": self.upstream_verification_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": (
                self.actual_projection_profile_id
            ),
            "producer_imported": False,
            "producer_entry_called": False,
            "construction_accounting_core_imported": False,
            "construction_accounting_core_entry_called": False,
            "accounting_v1_exact_prefix_replayed": True,
            "additive_v2_leaf_metadata_reconstructed_independently": True,
            "stage_rules_reconstructed_independently": True,
            "profiles_reconstructed_as_plain_documents": True,
            "live_counter_record_count": 0,
            "work_vector_count": 0,
            "comparison_vector_count": 0,
            "actual_projection_proof_count": 0,
            "live_from_stage_start_instrumentation_complete": False,
            "all_path_native_accounting_complete": False,
            "typed_route_attempt_terminal_complete": False,
            "logical_occurrence_closure_complete": False,
            "campaign_closure_complete": False,
            "complete_bundle_verifier_complete": False,
            "counter_completeness_gate_passed": False,
            "accounting_gate_passed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "fresh_heldout_accessed": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "independent schema verifications are in-memory-only"
        )


def verify_v075_construction_accounting_schema_bytes_v2(
    *,
    closure_bytes: bytes,
    foundation_bytes: bytes,
    source_code_provenance_bytes: bytes,
    repository_root: str,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075ConstructionAccountingSchemaIndependentVerificationV2:
    """Replay raw 1.84, then independently verify canonical contract 1.85."""

    try:
        upstream = (
            foundation_verifier
            .verify_v075_construction_native_accounting_foundation_bytes_v2(
                foundation_bytes=foundation_bytes,
                source_code_provenance_bytes=(
                    source_code_provenance_bytes
                ),
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=(
                    public_context_closure_bytes
                ),
                private_generation_seed=private_generation_seed,
                private_salt=private_salt,
            )
        )
        claimed = _strict_document(
            closure_bytes,
            label="claimed construction-accounting schema closure",
        )
        expected = _reconstruct_closure_document(
            upstream=upstream,
            foundation_bytes=foundation_bytes,
        )
        expected_bytes = canonical_json_bytes(expected)
        if claimed != expected or closure_bytes != expected_bytes:
            _fail("claimed accounting schema closure differs from replay")
        return V075ConstructionAccountingSchemaIndependentVerificationV2(
            _VERIFICATION_ISSUER,
            _cid(expected["closure_id"], "schema closure"),
            hashlib.sha256(expected_bytes).hexdigest(),
            len(expected_bytes),
            _cid(
                expected["upstream_attestation_id"],
                "upstream attestation",
            ),
            _cid(
                expected["upstream_verification_id"],
                "upstream verification",
            ),
            _cid(expected["counter_registry_id"], "counter registry"),
            _cid(expected["stage_profile_id"], "stage profile"),
            _cid(
                expected["comparison_profile_id"],
                "comparison profile",
            ),
            _cid(
                expected["actual_projection_profile_id"],
                "actual projection profile",
            ),
        )
    except Exception:
        raise V075ConstructionAccountingSchemaIndependentV2Violation(
            _REPLAY_MISMATCH
        ) from None


__all__ = [
    "ACCOUNTING_GATE_PASSED",
    "ALL_PATH_NATIVE_ACCOUNTING_COMPLETE",
    "CAMPAIGN_CLOSURE_COMPLETE",
    "COMPLETE_BUNDLE_VERIFIER_COMPLETE",
    "COUNTER_COMPLETENESS_GATE_PASSED",
    "EXPECTED_ACTUAL_PROJECTION_PROFILE_V2_ID",
    "EXPECTED_COMPARISON_PROFILE_V2_ID",
    "EXPECTED_COUNTER_REGISTRY_V2_ID",
    "EXPECTED_STAGE_PROFILE_V2_ID",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "LIVE_FROM_STAGE_START_INSTRUMENTATION_COMPLETE",
    "LOGICAL_OCCURRENCE_CLOSURE_COMPLETE",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "TYPED_ROUTE_ATTEMPT_TERMINAL_COMPLETE",
    "V075ConstructionAccountingSchemaIndependentV2Violation",
    "V075ConstructionAccountingSchemaIndependentVerificationV2",
    "verify_v075_construction_accounting_schema_bytes_v2",
]
