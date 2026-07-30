"""Independent verifier for the contract-1.84 accounting foundation.

The verifier never imports or invokes the producer.  It first replays raw
contract 1.83, then independently reconstructs the exact Phase-3E identities,
five historical V0-075 custom catalogues, reserved v2 leaves, immutable
67-role boundary, and terminal derivation.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import accounting_v1 as accounting
from acfqp import actual_accounting_v1 as actual
from acfqp import routing_v1 as routing
from acfqp import v075_batch_native_statistical_backend_v1 as batch_native
from acfqp import v075_integrated_direct_occurrence_pipeline_v1 as direct
from acfqp import v075_learned_support_quotient_planners_v1 as planner
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import (
    v075_observer_signed_multiround_occurrence_runner_v2
    as multiround_owner,
)
from acfqp import v075_portable_semantic_registry_v2 as portable_registry
from acfqp import v075_route_native_backend_core_v1 as route_core
from acfqp import (
    v075_construction_source_code_provenance_independent_verifier_v2
    as source_verifier,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.84.0"
PROFILE_KEY = (
    "v075_construction_native_accounting_foundation_"
    "independent_verifier_v2"
)
PRODUCER_PROFILE_KEY = "v075_construction_native_accounting_foundation_v2"
UPSTREAM_PROFILE_KEY = "v075_construction_source_code_provenance_v2"
COUNTER_REGISTRY_V2_KEY = "acfqp_counter_registry_v2"
EXPECTED_COUNTER_REGISTRY_V1_ID = (
    "27063139cc8c1f66416a9b285373d610"
    "67ee22d16370f394a419f85878b63a88"
)
EXPECTED_COMPARISON_PROFILE_V1_ID = (
    "5e2d71272e3865dac05f6e7cf62a4d4"
    "ec3e13ff93eb0fb1bbeb82e15b4407847"
)
EXPECTED_ACTUAL_PROJECTION_PROFILE_V1_ID = (
    "05964f14967c1b569eff929f54e35ff7"
    "4e2e422e9e839e9c02880d6b5b961275"
)
EXPECTED_CUSTOM_CATALOGUE_DIGESTS = MappingProxyType(
    {
        "route_core": (
            23,
            "f737e2f788817174127f607450c386a1"
            "db7b3568f253e5abdecd17b07eb6af27",
        ),
        "batch_native": (
            17,
            "e410bd7abfc7ad9407843b3e68ded641"
            "16d33813b8aec093ce64bc16b86cd17b",
        ),
        "planner": (
            15,
            "472ad30f6395df0466709878b76a187d"
            "23635744424a05c85b8dc06a40ccf517",
        ),
        "worker": (
            22,
            "6d2b59b870a2ce20dca63c0fb8fe00b"
            "b01942f3309a280034ff8ba310dc1e643",
        ),
        "direct": (
            18,
            "5daf4bcfb0a9b6e873979032215045824"
            "7c1bcb533f535ce52766a0825ed51b5",
        ),
    }
)
EXPECTED_PORTABLE_SEMANTIC_REGISTRY_ID = (
    "44a273cb6390dfc36102922c23083fa9"
    "e46ac830c15e47f9851f2140dee9b027"
)
EXPECTED_MULTIROUND_SOURCE_PROFILE = (
    "v075_observer_signed_multiround_occurrence_runner_v2"
)
EXPECTED_LEGACY_CUSTOM_DISTINCT_PATH_COUNT = 87
EXPECTED_GENERIC_TERMINAL_MAPPING = (
    ("ABSTRACT_CERTIFIED", "PLAN_CERTIFICATE"),
    (
        "ATTEMPT_BUDGET_EXHAUSTED",
        "ATTEMPT_CLOSURE_NONCERTIFICATE",
    ),
    ("CACHED_EXACT_INFEASIBLE", "INFEASIBILITY_CERTIFICATE"),
    (
        "FALLBACK_CAP_EXHAUSTED",
        "ATTEMPT_CLOSURE_NONCERTIFICATE",
    ),
    (
        "FULL_GROUND_EXACT_INFEASIBLE",
        "INFEASIBILITY_CERTIFICATE",
    ),
    ("FULL_GROUND_FALLBACK", "PLAN_CERTIFICATE"),
    ("INTEGRITY_FAILURE", "ATTEMPT_CLOSURE_NONCERTIFICATE"),
    ("LOCAL_GROUND_RECOVERY", "PLAN_CERTIFICATE"),
    ("PROTOCOL_FAILURE", "ATTEMPT_CLOSURE_NONCERTIFICATE"),
    ("REBUILD_REQUIRED", "ATTEMPT_CLOSURE_NONCERTIFICATE"),
)

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
LOADED_SOURCE_RECEIPT_COMPLETE = False
ALL_PATH_NATIVE_ACCOUNTING_COMPLETE = False
TERMINAL_CAMPAIGN_CLOSURE_COMPLETE = False
COMPLETE_BUNDLE_VERIFIER_COMPLETE = False
COUNTER_COMPLETENESS_GATE_PASSED = False
ACCOUNTING_GATE_PASSED = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

_DOMAINS = MappingProxyType(
    {
        "boundary": "acfqp:v075-accounting-boundary-profile:v2",
        "coverage": "acfqp:v075-counter-coverage-matrix:v2",
        "role_registry": "acfqp:v075-accounting-role-registry:v2",
        "terminal_registry": (
            "acfqp:v075-terminal-derivation-registry:v2"
        ),
        "readiness": (
            "acfqp:v075-accounting-readiness-attestation:v2"
        ),
        "verification": (
            "acfqp:v075-accounting-readiness-independent-verification:v2"
        ),
    }
)

_REPLAY_MISMATCH = (
    "independent construction accounting verification did not match "
    "registered evidence"
)


class V075ConstructionNativeAccountingIndependentV2Violation(ValueError):
    """Raw provenance or independently reconstructed accounting changed."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionNativeAccountingIndependentV2Violation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ConstructionNativeAccountingIndependentV2Violation(
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
        raise V075ConstructionNativeAccountingIndependentV2Violation(
            str(error)
        ) from error


def _strict_document(
    raw: bytes,
    *,
    label: str,
    byte_cap: int = 128 * 1024 * 1024,
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
                f"{label} contains forbidden constant {item}"
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionNativeAccountingIndependentV2Violation(
            f"{label} is not strict UTF-8 JSON"
        ) from error
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != raw
    ):
        _fail(f"{label} is not canonical")
    return document


def _sequence_digest(values: tuple[str, ...]) -> str:
    return hashlib.sha256(canonical_json_bytes(list(values))).hexdigest()


_INITIAL_BUILD_PATHS = tuple(
    sorted(
        (
            "build.initial_interval_log_search_evaluations",
            "build.initial_interval_row_evaluations",
            "build.initial_model_rows_built",
            "build.initial_policy_assignments_evaluated",
            "build.initial_semantic_record_replays",
            "build.initial_semantic_role_closures",
            "build.initial_source_units_compiled",
        )
    )
)
_INITIAL_ACQUISITION_PATHS = tuple(
    sorted(
        (
            "acquisition.initial_observer_accepted_draws",
            "acquisition.initial_observer_random_word_calls",
            "acquisition.initial_observer_rejections",
            "acquisition.initial_outcome_aggregate_rows",
            "acquisition.initial_signed_batches",
            "acquisition.initial_support_freezes",
        )
    )
)
_RESERVED_V2_PATHS = tuple(
    sorted((*_INITIAL_BUILD_PATHS, *_INITIAL_ACQUISITION_PATHS))
)
_CRITICAL_GAPS = (
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
_COMPANION_ROLES = (
    ("ACCOUNTING_BOUNDARY_PROFILE", "acfqp.v075_accounting_boundary_profile.v2", "PRESENT_FOUNDATION"),
    ("ACCOUNTING_READINESS_ATTESTATION", "acfqp.v075_accounting_readiness_attestation.v2", "PRESENT_FOUNDATION"),
    ("ACCOUNTING_ROLE_REGISTRY", "acfqp.v075_accounting_role_registry.v2", "PRESENT_FOUNDATION"),
    ("ACTUAL_PROJECTION", "acfqp.actual_projection.v2", "FUTURE_REQUIRED"),
    ("CAMPAIGN_CLOSURE", "acfqp.v075_campaign_closure.v2", "FUTURE_REQUIRED"),
    ("COMPLETE_BUNDLE_VERIFICATION", "acfqp.v075_complete_bundle_verification.v2", "FUTURE_REQUIRED"),
    ("COUNTER_COVERAGE_MATRIX", "acfqp.v075_counter_coverage_matrix.v2", "PRESENT_FOUNDATION"),
    ("COUNTER_REGISTRY_V2", "acfqp.counter_registry.v2", "FUTURE_REQUIRED"),
    ("LOADED_SOURCE_RECEIPT", "acfqp.v075_loaded_source_receipt.v2", "FUTURE_REQUIRED"),
    ("LOGICAL_OCCURRENCE_CLOSURE", "acfqp.v075_logical_occurrence_closure.v2", "FUTURE_REQUIRED"),
    ("OCCURRENCE_WORK_VECTOR", "acfqp.work_vector.v2", "FUTURE_REQUIRED"),
    ("TERMINAL_ARTIFACT", "acfqp.terminal_artifact.v2", "FUTURE_REQUIRED"),
    ("TERMINAL_DERIVATION_REGISTRY", "acfqp.v075_terminal_derivation_registry.v2", "PRESENT_FOUNDATION"),
)


def _coverage_rows(
    registry: accounting.CounterRegistryV1,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for leaf in registry.leaves:
        rows.append(
            {
                "source_family": "PHASE3E_COUNTER_REGISTRY_V1",
                "source_schema": "acfqp.counter_record.v1",
                "source_path": leaf.path,
                "classification": "EXACT_EXISTING_LEAF",
                "target_path": leaf.path,
                "legacy_custom_counter": False,
                "definition_registered_in_v1": True,
                "counter_record_v1_compatible": True,
                "currently_instrumented_for_registry_v2": False,
            }
        )
    for path in _RESERVED_V2_PATHS:
        rows.append(
            {
                "source_family": "RESERVED_COUNTER_REGISTRY_V2",
                "source_schema": "acfqp.counter_registry.v2",
                "source_path": path,
                "classification": "RESERVED_V2_PATH_NAME",
                "target_path": path,
                "legacy_custom_counter": False,
                "definition_registered_in_v1": False,
                "counter_record_v1_compatible": False,
                "currently_instrumented_for_registry_v2": False,
            }
        )
    for family, schema, paths in (
        (
            "V075_ROUTE_CORE_HISTORICAL_CUSTOM",
            "acfqp.v075_route_native_backend_counter.v1",
            route_core.COUNTER_PATHS,
        ),
        (
            "V075_BATCH_NATIVE_HISTORICAL_CUSTOM",
            "acfqp.v075_batch_native_backend_counter.v1",
            batch_native.BATCH_NATIVE_COUNTER_PATHS,
        ),
        (
            "V075_PLANNER_HISTORICAL_CUSTOM",
            "acfqp.v075_support_planner_counter.v1",
            planner.PLANNER_COUNTER_PATHS,
        ),
        (
            "V075_REGISTERED_WORKER_HISTORICAL_CUSTOM",
            "acfqp.v075_registered_worker_counter.v1",
            worker.REGISTERED_COUNTER_PATHS,
        ),
        (
            "V075_DIRECT_HISTORICAL_CUSTOM",
            "acfqp.v075_integrated_direct_counter.v1",
            direct.DIRECT_PIPELINE_COUNTER_PATHS,
        ),
    ):
        for path in paths:
            rows.append(
                {
                    "source_family": family,
                    "source_schema": schema,
                    "source_path": path,
                    "classification": "NOT_INSTRUMENTED",
                    "target_path": None,
                    "legacy_custom_counter": True,
                    "definition_registered_in_v1": False,
                    "counter_record_v1_compatible": False,
                    "currently_instrumented_for_registry_v2": False,
                }
            )
    return sorted(rows, key=lambda row: (row["source_family"], row["source_path"]))


def _extract_upstream(
    *,
    upstream: (
        source_verifier
        .V075ConstructionSourceCodeProvenanceIndependentVerificationV2
    ),
    source_code_provenance_bytes: bytes,
    portable_bundle_bytes: bytes,
) -> dict[str, Any]:
    source = _strict_document(
        source_code_provenance_bytes,
        label="verified source provenance",
    )
    for field, expected in (
        ("closure_id", upstream.closure_id),
        (
            "semantic_terminal_closure_id",
            upstream.semantic_terminal_closure_id,
        ),
        ("repository_closure_id", upstream.repository_closure_id),
        ("source_archive_binding_id", upstream.source_archive_binding_id),
        ("provenance_dag_id", upstream.provenance_dag_id),
    ):
        if source.get(field) != expected:
            _fail(f"source provenance {field} changed")
    archive = source.get("source_archive_binding")
    if type(archive) is not dict:
        _fail("source archive binding is absent")
    for field in (
        "runtime_source_closure_id",
        "source_archive_id",
        "runtime_lock_id",
        "compile_verification_id",
    ):
        _cid(archive.get(field), f"archive {field}")
    if archive.get("binding_id") != upstream.source_archive_binding_id:
        _fail("nested source archive binding identity changed")
    portable_bundle_id = _cid(
        source.get("portable_bundle_id"),
        "source-bound portable bundle",
    )
    public_context_closure_id = _cid(
        source.get("public_context_closure_id"),
        "source-bound public context closure",
    )
    bundle = _strict_document(
        portable_bundle_bytes,
        label="verified portable bundle",
        byte_cap=512 * 1024 * 1024,
    )
    records = bundle.get("artifact_records")
    if type(records) is not list:
        _fail("portable artifact records are absent")
    if bundle.get("bundle_id") != portable_bundle_id:
        _fail("portable bundle identity differs from source provenance")
    selected = [
        row
        for row in records
        if type(row) is dict and row.get("role") == "MULTIROUND_RESULT"
    ]
    if len(selected) != 1:
        _fail("portable multiround result is not singular")
    raw_hex = selected[0].get("canonical_artifact_bytes_hex")
    if type(raw_hex) is not str:
        _fail("portable multiround result bytes are absent")
    try:
        raw = bytes.fromhex(raw_hex)
    except ValueError as error:
        raise V075ConstructionNativeAccountingIndependentV2Violation(
            "portable multiround result is not hexadecimal"
        ) from error
    if raw.hex() != raw_hex:
        _fail("portable multiround result is not lowercase hexadecimal")
    result = _strict_document(
        raw,
        label="verified multiround result",
        byte_cap=64 * 1024 * 1024,
    )
    result_id = _cid(result.get("result_id"), "multiround result")
    if (
        selected[0].get("semantic_artifact_id") != result_id
        or result.get("status") != "CHILD_ACTION_ROW_CAP_EXCEEDED"
    ):
        _fail("registered root-only cap terminal changed")
    return {
        "source": source,
        "archive": archive,
        "portable_bundle_id": portable_bundle_id,
        "public_context_closure_id": public_context_closure_id,
        "multiround_result_id": result_id,
        "multiround_status": result["status"],
    }


def _reconstruct_document(
    *,
    upstream: (
        source_verifier
        .V075ConstructionSourceCodeProvenanceIndependentVerificationV2
    ),
    source_code_provenance_bytes: bytes,
    portable_bundle_bytes: bytes,
) -> dict[str, Any]:
    bound = _extract_upstream(
        upstream=upstream,
        source_code_provenance_bytes=source_code_provenance_bytes,
        portable_bundle_bytes=portable_bundle_bytes,
    )
    registry = accounting.official_counter_registry_v1()
    registry.validate_official_catalogue()
    comparison = accounting.official_comparison_profile_v1(registry)
    projection = actual.official_actual_projection_profile_v1(
        registry, comparison
    )
    if (
        registry.registry_id
        != EXPECTED_COUNTER_REGISTRY_V1_ID
        or comparison.comparison_profile_id
        != EXPECTED_COMPARISON_PROFILE_V1_ID
        or projection.actual_projection_profile_id
        != EXPECTED_ACTUAL_PROJECTION_PROFILE_V1_ID
        or len(registry.leaves) != 49
        or len(registry.operational_leaves) != 34
    ):
        _fail("exact accounting_v1 identity changed")
    base_paths = {leaf.path for leaf in registry.leaves}
    custom_catalogues = {
        "route_core": route_core.COUNTER_PATHS,
        "batch_native": batch_native.BATCH_NATIVE_COUNTER_PATHS,
        "planner": planner.PLANNER_COUNTER_PATHS,
        "worker": worker.REGISTERED_COUNTER_PATHS,
        "direct": direct.DIRECT_PIPELINE_COUNTER_PATHS,
    }
    reserved_paths = set(_RESERVED_V2_PATHS)
    legacy_custom_paths = set().union(
        *(set(paths) for paths in custom_catalogues.values())
    )
    if (
        any(base_paths & set(paths) for paths in custom_catalogues.values())
        or reserved_paths & base_paths
        or reserved_paths & legacy_custom_paths
        or len(legacy_custom_paths)
        != EXPECTED_LEGACY_CUSTOM_DISTINCT_PATH_COUNT
    ):
        _fail("legacy custom paths overlap the exact v1 registry")
    for name, paths in custom_catalogues.items():
        if (
            len(paths),
            _sequence_digest(paths),
        ) != EXPECTED_CUSTOM_CATALOGUE_DIGESTS[name]:
            _fail("legacy custom catalogue identity changed")
    rebuild = tuple(
        sorted(
            leaf.path
            for leaf in registry.leaves
            if leaf.path.startswith("rebuild.")
        )
    )
    boundary_payload = {
        "schema": "acfqp.v075_accounting_boundary_profile.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "base_counter_registry_key": accounting.COUNTER_REGISTRY_KEY,
        "base_counter_registry_id": registry.registry_id,
        "base_comparison_profile_key": accounting.COMPARISON_PROFILE_KEY,
        "base_comparison_profile_id": comparison.comparison_profile_id,
        "base_actual_projection_profile_key": (
            actual.ACTUAL_PROJECTION_PROFILE_KEY
        ),
        "base_actual_projection_profile_id": (
            projection.actual_projection_profile_id
        ),
        "base_leaf_count": len(registry.leaves),
        "base_operational_leaf_count": len(registry.operational_leaves),
        "future_counter_registry_key": COUNTER_REGISTRY_V2_KEY,
        "counter_registry_v1_mutation_allowed": False,
        "legacy_custom_counter_as_counter_record_allowed": False,
        "caller_custom_total_as_counter_record_allowed": False,
        "initial_build_paths": list(_INITIAL_BUILD_PATHS),
        "initial_acquisition_paths": list(_INITIAL_ACQUISITION_PATHS),
        "rebuild_paths": list(rebuild),
        "initial_build_is_rebuild": False,
        "initial_acquisition_is_rebuild": False,
        "reserved_v2_path_intersection_with_v1": 0,
        "reserved_v2_path_intersection_with_legacy_custom": 0,
        "legacy_custom_distinct_path_count": (
            EXPECTED_LEGACY_CUSTOM_DISTINCT_PATH_COUNT
        ),
        "counter_registry_v2_materialized": False,
    }
    boundary = {
        **boundary_payload,
        "profile_id": _hash("boundary", boundary_payload),
    }
    rows = _coverage_rows(registry)
    counts = {
        label: sum(row["classification"] == label for row in rows)
        for label in (
            "EXACT_EXISTING_LEAF",
            "RESERVED_V2_PATH_NAME",
            "NOT_INSTRUMENTED",
        )
    }
    coverage_payload = {
        "schema": "acfqp.v075_counter_coverage_matrix.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "boundary_profile_id": boundary["profile_id"],
        "base_counter_registry_key": accounting.COUNTER_REGISTRY_KEY,
        "future_counter_registry_key": COUNTER_REGISTRY_V2_KEY,
        "route_core_source_schema": (
            "acfqp.v075_route_native_backend_counter.v1"
        ),
        "route_core_source_path_count": len(route_core.COUNTER_PATHS),
        "route_core_source_path_digest": _sequence_digest(
            route_core.COUNTER_PATHS
        ),
        "batch_native_source_schema": (
            "acfqp.v075_batch_native_backend_counter.v1"
        ),
        "batch_native_source_path_count": len(
            batch_native.BATCH_NATIVE_COUNTER_PATHS
        ),
        "batch_native_source_path_digest": _sequence_digest(
            batch_native.BATCH_NATIVE_COUNTER_PATHS
        ),
        "planner_source_schema": "acfqp.v075_support_planner_counter.v1",
        "planner_source_path_count": len(planner.PLANNER_COUNTER_PATHS),
        "planner_source_path_digest": _sequence_digest(
            planner.PLANNER_COUNTER_PATHS
        ),
        "worker_source_schema": "acfqp.v075_registered_worker_counter.v1",
        "worker_source_path_count": len(worker.REGISTERED_COUNTER_PATHS),
        "worker_source_path_digest": _sequence_digest(
            worker.REGISTERED_COUNTER_PATHS
        ),
        "direct_source_schema": "acfqp.v075_integrated_direct_counter.v1",
        "direct_source_path_count": len(
            direct.DIRECT_PIPELINE_COUNTER_PATHS
        ),
        "direct_source_path_digest": _sequence_digest(
            direct.DIRECT_PIPELINE_COUNTER_PATHS
        ),
        "classification_counts": counts,
        "rows": rows,
        "classification_semantics": {
            "EXACT_EXISTING_LEAF": (
                "DEFINED_IN_EXACT_COUNTER_REGISTRY_V1_BUT_NOT_PRESENT_"
                "IN_CURRENT_ROOT_ONLY_BUNDLE"
            ),
            "RESERVED_V2_PATH_NAME": (
                "PATH_NAMESPACE_RESERVATION_ONLY_SEMANTICS_NOT_FROZEN"
            ),
            "NOT_INSTRUMENTED": (
                "NO_CURRENT_ROOT_ONLY_COUNTER_RECORD_EVIDENCE"
            ),
        },
        "current_root_only_counter_record_count": 0,
        "current_root_only_missing_recorder_path_count": len(
            _CRITICAL_GAPS
        ),
        "current_root_only_missing_recorder_paths": list(_CRITICAL_GAPS),
        "current_root_only_missing_recorder_path_digest": (
            _sequence_digest(_CRITICAL_GAPS)
        ),
        "historical_custom_catalogues_present_in_current_bundle": False,
        "historical_custom_catalogue_counts_and_digests_frozen": True,
        "legacy_custom_exact_path_intersection_with_v1": 0,
        "reserved_v2_path_intersection_with_v1": 0,
        "reserved_v2_path_intersection_with_legacy_custom": 0,
        "legacy_custom_distinct_path_count": (
            EXPECTED_LEGACY_CUSTOM_DISTINCT_PATH_COUNT
        ),
        "legacy_custom_counter_documents_are_counter_records": False,
        "custom_totals_are_counter_records": False,
        "counter_registry_v2_materialized": False,
        "planned_counter_semantics_frozen": False,
        "all_path_native_accounting_complete": False,
    }
    coverage = {
        **coverage_payload,
        "matrix_id": _hash("coverage", coverage_payload),
    }
    portable = portable_registry.freeze_v075_portable_semantic_registry_v2()
    portable_names = tuple(item.role for item in portable.declarations)
    if (
        portable.registry_id != EXPECTED_PORTABLE_SEMANTIC_REGISTRY_ID
        or len(portable_names) != 67
    ):
        _fail("portable role count changed")
    companion_rows = [
        {"role": role, "schema": schema, "presence": presence}
        for role, schema, presence in sorted(_COMPANION_ROLES)
    ]
    role_payload = {
        "schema": "acfqp.v075_accounting_role_registry.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "portable_semantic_registry_id": portable.registry_id,
        "portable_role_count": len(portable_names),
        "portable_role_names_digest": _sequence_digest(portable_names),
        "portable_role_names": list(portable_names),
        "portable_registry_modified": False,
        "companion_role_scope": (
            "OUTER_ACCOUNTING_AND_CLOSURE_COMPANIONS_ONLY"
        ),
        "companion_roles": companion_rows,
    }
    role_registry = {
        **role_payload,
        "registry_id": _hash("role_registry", role_payload),
    }
    generic_mapping = tuple(
        sorted(
            (
                code.value,
                routing._TERMINAL_CLASS_BY_CODE[code].value,  # noqa: SLF001
            )
            for code in routing.TerminalCode
        )
    )
    if (
        generic_mapping != EXPECTED_GENERIC_TERMINAL_MAPPING
        or multiround_owner.PROFILE_KEY
        != EXPECTED_MULTIROUND_SOURCE_PROFILE
        or multiround_owner.V075ObserverSignedMultiroundTerminalStatusV2
        .CHILD_ACTION_ROW_CAP_EXCEEDED.value
        != "CHILD_ACTION_ROW_CAP_EXCEEDED"
    ):
        _fail("specific cap cause changed")
    terminal_payload = {
        "schema": "acfqp.v075_terminal_derivation_registry.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "generic_terminal_artifact_schema": "acfqp.terminal_artifact.v1",
        "generic_terminal_mapping": [
            {"terminal_code": code, "terminal_class": terminal_class}
            for code, terminal_class in generic_mapping
        ],
        "specific_derivations": [
            {
                "source_profile": EXPECTED_MULTIROUND_SOURCE_PROFILE,
                "source_cause": "CHILD_ACTION_ROW_CAP_EXCEEDED",
                "derived_terminal_scope": "ROUTE_ATTEMPT",
                "derived_terminal_class": (
                    "ATTEMPT_CLOSURE_NONCERTIFICATE"
                ),
                "derived_terminal_code": "ATTEMPT_BUDGET_EXHAUSTED",
                "specific_cause_retained": True,
                "infeasibility_mapping_allowed": False,
                "caller_terminal_self_report_authoritative": False,
            }
        ],
        "terminal_classification_must_be_recomputed": True,
        "campaign_closure_materialized": False,
    }
    terminal_registry = {
        **terminal_payload,
        "registry_id": _hash("terminal_registry", terminal_payload),
    }
    source = bound["source"]
    archive = bound["archive"]
    readiness_payload = {
        "schema": "acfqp.v075_accounting_readiness_attestation.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "upstream_profile_key": UPSTREAM_PROFILE_KEY,
        "terminal_scope": "CONSTRUCTION_NATIVE_ACCOUNTING_FOUNDATION_ONLY",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": (
            "CONSTRUCTION_ACCOUNTING_BOUNDARY_FROZEN_"
            "ALL_PATH_ACCOUNTING_AND_CAMPAIGN_CLOSURE_LOCKED"
        ),
        "source_code_provenance_id": upstream.closure_id,
        "source_code_provenance_sha256": hashlib.sha256(
            source_code_provenance_bytes
        ).hexdigest(),
        "source_code_provenance_byte_count": len(
            source_code_provenance_bytes
        ),
        "upstream_verification_id": upstream.verification_id,
        "portable_bundle_id": bound["portable_bundle_id"],
        "public_context_closure_id": bound["public_context_closure_id"],
        "semantic_terminal_closure_id": (
            upstream.semantic_terminal_closure_id
        ),
        "repository_closure_id": upstream.repository_closure_id,
        "source_archive_binding_id": upstream.source_archive_binding_id,
        "provenance_dag_id": upstream.provenance_dag_id,
        "runtime_source_closure_id": archive["runtime_source_closure_id"],
        "source_archive_id": archive["source_archive_id"],
        "runtime_lock_id": archive["runtime_lock_id"],
        "compile_verification_id": archive["compile_verification_id"],
        "multiround_result_id": bound["multiround_result_id"],
        "multiround_status": bound["multiround_status"],
        "boundary_profile": boundary,
        "boundary_profile_id": boundary["profile_id"],
        "coverage_matrix": coverage,
        "coverage_matrix_id": coverage["matrix_id"],
        "role_registry": role_registry,
        "role_registry_id": role_registry["registry_id"],
        "terminal_registry": terminal_registry,
        "terminal_registry_id": terminal_registry["registry_id"],
        "raw_contract_183_replayed_first": True,
        "counter_registry_v2_key_frozen": True,
        "counter_registry_v1_mutated": False,
        "custom_totals_accepted_as_counter_records": False,
        "initial_build_and_acquisition_separate_from_rebuild": True,
        "portable_67_role_registry_modified": False,
        "outer_companion_accounting_roles_only": True,
        "raw_input_identity_binding": (
            "TRANSITIVE_THROUGH_EXACT_1_83_VERIFICATION_WITHOUT_"
            "DIRECT_PRIVATE_SEED_OR_SALT_HASHING"
        ),
        "raw_contract_183_prefix_accounting_lane": (
            "PROVENANCE_EVALUATION_PREFIX_EXCLUDED_FROM_ACTUAL"
        ),
        "raw_contract_183_prefix_live_counter_records_present": False,
        "raw_contract_183_prefix_subprocess_io_hash_peak_work_fully_accounted": False,
        "full_live_from_start_accounting_requires_later_contract": True,
        "all_path_native_accounting_complete": False,
        "terminal_campaign_closure_complete": False,
        "complete_bundle_verifier_complete": False,
        "loaded_source_receipt_complete": False,
        "source_authority_complete": False,
        "code_provenance_complete": False,
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
    }
    return {
        **readiness_payload,
        "attestation_id": _hash("readiness", readiness_payload),
    }


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionNativeAccountingIndependentVerificationV2:
    _issuer: InitVar[object]
    attestation_id: str
    attestation_sha256: str
    attestation_byte_count: int
    source_code_provenance_id: str
    boundary_profile_id: str
    coverage_matrix_id: str
    role_registry_id: str
    terminal_registry_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.attestation_id, "accounting attestation"),
            (self.attestation_sha256, "accounting attestation bytes"),
            (self.source_code_provenance_id, "source provenance"),
            (self.boundary_profile_id, "accounting boundary"),
            (self.coverage_matrix_id, "counter coverage"),
            (self.role_registry_id, "accounting roles"),
            (self.terminal_registry_id, "terminal derivation"),
        ):
            _cid(value, label)
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.attestation_byte_count) is not int
            or self.attestation_byte_count <= 0
        ):
            _fail("independent accounting verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_accounting_readiness_independent_"
                "verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "producer_profile_key": PRODUCER_PROFILE_KEY,
            "attestation_id": self.attestation_id,
            "attestation_sha256": self.attestation_sha256,
            "attestation_byte_count": self.attestation_byte_count,
            "source_code_provenance_id": (
                self.source_code_provenance_id
            ),
            "boundary_profile_id": self.boundary_profile_id,
            "coverage_matrix_id": self.coverage_matrix_id,
            "role_registry_id": self.role_registry_id,
            "terminal_registry_id": self.terminal_registry_id,
            "producer_imported": False,
            "producer_entry_called": False,
            "producer_issuer_used": False,
            "independent_source_catalogue_replay": True,
            "current_root_only_counter_record_count": 0,
            "all_path_native_accounting_complete": False,
            "terminal_campaign_closure_complete": False,
            "complete_bundle_verifier_complete": False,
            "loaded_source_receipt_complete": False,
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
            "independent accounting verifications are in-memory-only"
        )


def verify_v075_construction_native_accounting_foundation_bytes_v2(
    *,
    foundation_bytes: bytes,
    source_code_provenance_bytes: bytes,
    repository_root: str,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075ConstructionNativeAccountingIndependentVerificationV2:
    """Replay raw 1.83 first, then independently verify contract 1.84."""

    try:
        upstream = (
            source_verifier
            .verify_v075_construction_source_code_provenance_bytes_v2(
                closure_bytes=source_code_provenance_bytes,
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=public_context_closure_bytes,
                private_generation_seed=private_generation_seed,
                private_salt=private_salt,
            )
        )
        claimed = _strict_document(
            foundation_bytes,
            label="claimed accounting foundation",
        )
        expected = _reconstruct_document(
            upstream=upstream,
            source_code_provenance_bytes=source_code_provenance_bytes,
            portable_bundle_bytes=portable_bundle_bytes,
        )
        expected_bytes = canonical_json_bytes(expected)
        if claimed != expected or foundation_bytes != expected_bytes:
            _fail("claimed accounting foundation differs from replay")
        return V075ConstructionNativeAccountingIndependentVerificationV2(
            _VERIFICATION_ISSUER,
            _cid(expected["attestation_id"], "accounting attestation"),
            hashlib.sha256(expected_bytes).hexdigest(),
            len(expected_bytes),
            _cid(expected["source_code_provenance_id"], "source provenance"),
            _cid(expected["boundary_profile_id"], "accounting boundary"),
            _cid(expected["coverage_matrix_id"], "counter coverage"),
            _cid(expected["role_registry_id"], "accounting roles"),
            _cid(expected["terminal_registry_id"], "terminal derivation"),
        )
    except Exception:
        raise V075ConstructionNativeAccountingIndependentV2Violation(
            _REPLAY_MISMATCH
        ) from None


__all__ = [
    "ACCOUNTING_GATE_PASSED",
    "ALL_PATH_NATIVE_ACCOUNTING_COMPLETE",
    "COMPLETE_BUNDLE_VERIFIER_COMPLETE",
    "COUNTER_COMPLETENESS_GATE_PASSED",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "LOADED_SOURCE_RECEIPT_COMPLETE",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "TERMINAL_CAMPAIGN_CLOSURE_COMPLETE",
    "V075ConstructionNativeAccountingIndependentV2Violation",
    "V075ConstructionNativeAccountingIndependentVerificationV2",
    "verify_v075_construction_native_accounting_foundation_bytes_v2",
]
