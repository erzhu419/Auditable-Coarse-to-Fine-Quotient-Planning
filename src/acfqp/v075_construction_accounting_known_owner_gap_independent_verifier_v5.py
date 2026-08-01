"""Independent verifier for contract-1.89 known-owner-gap accounting.

The verifier imports neither the V5 registry implementation nor its producer.
It first performs the complete independent contract-1.87 replay, then treats
the verified embedded V4 profiles as bytes and reconstructs the 27 additions,
stage ownership, and 133 coefficient-one projection terms independently.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V5_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V5_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V5_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V5_DOMAIN,
    V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_SUCCESSOR_V5_DOMAIN,
    V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_VERIFICATION_V5_DOMAIN,
    V075_K7_ROOT_CAP_OPERATION_SITE_AUDIT_V2_DOMAIN,
    V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp import (
    v075_construction_accounting_operation_ownership_independent_verifier_v4
    as upstream_verifier,
)


SCHEMA_VERSION = "5.0.0"
PROPOSED_CONTRACT_VERSION = "1.89.0"
PROFILE_KEY = (
    "v075_construction_accounting_known_owner_gap_"
    "independent_verifier_v5"
)
PRODUCER_PROFILE_KEY = (
    "v075_construction_accounting_known_owner_gap_successor_v5"
)
UPSTREAM_PROFILE_KEY = (
    "v075_construction_accounting_operation_ownership_"
    "independent_verifier_v4"
)
MAX_BYTES = 64 * 1024 * 1024

EXPECTED_COUNTER_REGISTRY_V4_ID = (
    "edc4da61f6a7c638fdef3c40259f2d55"
    "8156758970dabbf023ca41948fbda2b0"
)
EXPECTED_COUNTER_REGISTRY_V5_ID = (
    "cf1e63f677fa6f9831213b8b48ca88e1"
    "a8d489276af5d30029951670cfe6736f"
)
EXPECTED_STAGE_PROFILE_V5_ID = (
    "db5b8336d8ff0f8c64175f7563b7a974"
    "df7cf9ec6fb0212e934616aed071ab04"
)
EXPECTED_COMPARISON_PROFILE_V5_ID = (
    "e60f162e689e84853335065db9213d13"
    "9bc1498855a63f0b2e8cfbc464e2a00e"
)
EXPECTED_ACTUAL_PROJECTION_PROFILE_V5_ID = (
    "d28e9cd3ae00d21d22af98ccf2c59da"
    "8217bcb4f023b3afb524c93cda59fb1f0"
)
EXPECTED_STRICT_OWNER_MANIFEST_V2_ID = (
    "c71405162a49093abe8f2325943c77e0"
    "b49ec9c0850660e67ac271f14bc11688"
)
EXPECTED_STRICT_OWNER_MANIFEST_V1_ID = (
    "4c56d53027aeb2d15a726be05d6ad7c8"
    "a17e4be3a123d194881040c575d96d27"
)
EXPECTED_STRICT_OWNER_MANIFEST_V2_SHA256 = (
    "18cae67b2d580adaac78fb9062bd94d6"
    "3c4f28738fe20b72db2ece0718032f80"
)
EXPECTED_STRICT_OWNER_MANIFEST_V2_BYTE_COUNT = 45_623

_SHARED_AXES = (
    "kernel_transition_calls",
    "nonkernel_compute_events",
    "output_bytes",
    "peak_mounted_bytes",
    "peak_working_bytes",
    "process_launches",
    "read_bytes",
    "staged_bytes",
)
_STAGES = (
    "CLOSED_RECONCILIATION_AND_TERMINALIZATION",
    "DIRECT_FALLBACK",
    "FAILED_ABSTRACT_PREFIX",
    "INITIAL_ACQUISITION",
    "INITIAL_MODEL_BUILD",
    "LOCAL_ATTEMPT",
    "OPEN_CHECKPOINT_REPLANNING",
    "OPEN_INCREMENTAL_ACQUISITION",
    "PREOPEN_COMMON_PREFIX",
    "REBUILD",
)


def _leaf(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    scope: str,
) -> dict[str, Any]:
    return {
        "path": path,
        "semantics_id": semantics_id,
        "owner": owner,
        "unit": unit,
        "lane": "operational",
        "scope": scope,
        "reducer": "sum",
        "comparison_axis": "nonkernel_compute_events",
        "required": True,
    }


_INITIAL_SCOPE = "construction_occurrence_initial_build_epoch"
_FAILED_SCOPE = "construction_occurrence_failed_abstract_prefix"
_CLOSED_SCOPE = (
    "construction_occurrence_closed_reconciliation_and_terminalization"
)
_BATCH_FAMILIES = (
    ("typed_record_replays", "typed-record-replay", "typed_record_replays"),
    ("row_behaviors_compiled", "row-behavior-compile", "row_behaviors"),
    ("quotient_cells_compiled", "quotient-cell-compile", "quotient_cells"),
    ("semantic_options_compiled", "semantic-option-compile", "semantic_options"),
    (
        "concretizer_ground_actions_bound",
        "concretizer-ground-action-bind",
        "ground_actions",
    ),
    (
        "interval_greedy_allocation_steps",
        "interval-greedy-allocation-step",
        "greedy_allocation_steps",
    ),
    ("policy_order_comparisons", "policy-order-comparison", "comparisons"),
    (
        "frontier_obligations_built",
        "frontier-obligation-build",
        "frontier_obligations",
    ),
)


def _batch_rows(
    *, path_prefix: str, semantics_suffix: str, scope: str
) -> tuple[dict[str, Any], ...]:
    return tuple(
        _leaf(
            f"{path_prefix}_batch_v2_{path_suffix}",
            f"v075-batch-v2-{family}-v5-{semantics_suffix}",
            "v075_batch_native_planning_backend_v2",
            unit,
            scope,
        )
        for path_suffix, family, unit in _BATCH_FAMILIES
    )


_ADDITION_ROWS = (
    *_batch_rows(
        path_prefix="build.initial",
        semantics_suffix="initial-build",
        scope=_INITIAL_SCOPE,
    ),
    _leaf(
        "build.initial_live_model_support_descriptors_compiled",
        "v075-live-model-support-descriptor-compile-v5-initial-build",
        "v075_live_incremental_model_authority_v2",
        "support_descriptors",
        _INITIAL_SCOPE,
    ),
    *_batch_rows(
        path_prefix="closure.reconciliation",
        semantics_suffix="closed-reconciliation",
        scope=_CLOSED_SCOPE,
    ),
    _leaf(
        "closure.reconciliation_batch_v2_support_descriptors_compiled",
        "v075-batch-v2-support-descriptor-compile-v5-closed-reconciliation",
        "v075_batch_native_planning_backend_v2",
        "support_descriptors",
        _CLOSED_SCOPE,
    ),
    _leaf(
        "audit.dynamic_root_rows_scanned",
        "v075-dynamic-root-row-scan-v5-failed-abstract-audit",
        "v075_live_dynamic_acquisition_authority_v2",
        "root_rows",
        _FAILED_SCOPE,
    ),
    _leaf(
        "audit.dynamic_support_descriptors_scanned",
        "v075-dynamic-support-descriptor-scan-v5-failed-abstract-audit",
        "v075_live_dynamic_acquisition_authority_v2",
        "support_descriptors",
        _FAILED_SCOPE,
    ),
    _leaf(
        "audit.dynamic_causal_edges_built",
        "v075-dynamic-causal-edge-build-v5-failed-abstract-audit",
        "v075_live_dynamic_acquisition_authority_v2",
        "causal_edges",
        _FAILED_SCOPE,
    ),
    _leaf(
        "audit.dynamic_child_action_rows_built",
        "v075-dynamic-child-action-row-build-v5-failed-abstract-audit",
        "v075_live_dynamic_acquisition_authority_v2",
        "child_action_rows",
        _FAILED_SCOPE,
    ),
    _leaf(
        "audit.dynamic_row_cap_checks",
        "v075-dynamic-child-row-cap-check-v5-failed-abstract-audit",
        "v075_live_dynamic_acquisition_authority_v2",
        "cap_checks",
        _FAILED_SCOPE,
    ),
    _leaf(
        "audit.dynamic_child_closure_attestations",
        "v075-dynamic-child-closure-attestation-v5-failed-abstract-audit",
        "v075_live_dynamic_acquisition_authority_v2",
        "attestations",
        _FAILED_SCOPE,
    ),
    _leaf(
        "build.initial_live_model_outcome_projections",
        "v075-live-model-outcome-projection-v5-initial-build",
        "v075_live_incremental_model_authority_v2",
        "outcome_projections",
        _INITIAL_SCOPE,
    ),
    _leaf(
        "closure.reconciliation_batch_v2_model_rows_built",
        "v075-batch-v2-model-row-build-v5-closed-reconciliation",
        "v075_batch_native_planning_backend_v2",
        "model_rows",
        _CLOSED_SCOPE,
    ),
    _leaf(
        "closure.reconciliation_batch_v2_row_evidence_bindings_built",
        "v075-batch-v2-row-evidence-binding-build-v5-closed-reconciliation",
        "v075_batch_native_planning_backend_v2",
        "row_evidence_bindings",
        _CLOSED_SCOPE,
    ),
)
_ADDITIONS = {row["path"]: row for row in _ADDITION_ROWS}
if len(_ADDITIONS) != 27:  # pragma: no cover - import-time invariant
    raise RuntimeError("independent V5 addition catalogue changed")

_STAGE_ADDITIONS = {
    "INITIAL_MODEL_BUILD": {
        path for path in _ADDITIONS if path.startswith("build.initial")
    },
    "FAILED_ABSTRACT_PREFIX": {
        path for path in _ADDITIONS if path.startswith("audit.dynamic")
    },
    "CLOSED_RECONCILIATION_AND_TERMINALIZATION": {
        path
        for path in _ADDITIONS
        if path.startswith("closure.reconciliation")
    },
}

_REPLAY_MISMATCH = (
    "independent contract-1.89 known-owner-gap replay mismatch"
)
_VERIFICATION_ISSUER = object()


class V075ConstructionAccountingKnownOwnerGapIndependentV5Violation(
    ValueError
):
    """Upstream replay, embedded V5 profiles, or outer locks are invalid."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionAccountingKnownOwnerGapIndependentV5Violation(
        message
    )


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        _fail(f"{label} bytes are absent or exceed the cap")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionAccountingKnownOwnerGapIndependentV5Violation(
            f"{label} is not strict UTF-8 JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _rehash_embedded(
    document: Mapping[str, Any],
    *,
    id_field: str,
    domain: str,
    expected_id: str,
    label: str,
) -> None:
    if type(document) is not dict or id_field not in document:
        _fail(f"{label} is not one complete object")
    payload = dict(document)
    claimed = payload.pop(id_field)
    try:
        actual = content_id(domain, payload)
    except (TypeError, ValueError) as error:
        raise V075ConstructionAccountingKnownOwnerGapIndependentV5Violation(
            f"{label} cannot be canonically re-hashed"
        ) from error
    if claimed != actual or actual != expected_id:
        _fail(f"{label} identity changed")


def _verify_strict_owner_manifest(
    *,
    strict_owner_manifest_id: str,
    strict_owner_manifest_bytes: bytes,
) -> dict[str, Any]:
    parse_content_id(strict_owner_manifest_id)
    document = _strict_document(
        strict_owner_manifest_bytes,
        label="contract-1.88 strict-owner operation-site manifest",
    )
    payload = dict(document)
    claimed = payload.pop("manifest_id", None)
    try:
        actual = content_id(
            V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V2_DOMAIN,
            payload,
        )
    except (TypeError, ValueError) as error:
        raise V075ConstructionAccountingKnownOwnerGapIndependentV5Violation(
            "strict-owner manifest cannot be canonically re-hashed"
        ) from error
    expected_counts = {
        "DIRECT_VALID_OWNER_MATCHED": 9,
        "NATIVE_ZERO_NOT_EXECUTED": 13,
        "REQUIRED_PENDING_HOOK": 10,
        "DERIVED_ONLY_RECONCILIATION": 1,
        "MISSING_COUNTER_FAMILY": 10,
    }
    sites = document.get("sites")
    if (
        claimed != actual
        or actual != strict_owner_manifest_id
        or actual != EXPECTED_STRICT_OWNER_MANIFEST_V2_ID
        or hashlib.sha256(strict_owner_manifest_bytes).hexdigest()
        != EXPECTED_STRICT_OWNER_MANIFEST_V2_SHA256
        or len(strict_owner_manifest_bytes)
        != EXPECTED_STRICT_OWNER_MANIFEST_V2_BYTE_COUNT
        or document.get("schema")
        != "acfqp.v075_k7_root_cap_operation_site_manifest.v2"
        or document.get("schema_version") != "2.0.0"
        or document.get("v1_operation_site_manifest_id")
        != EXPECTED_STRICT_OWNER_MANIFEST_V1_ID
        or document.get("v1_direct_native_semantic_audit_passed") is not False
        or document.get("v1_sink_imported_or_reused") is not False
        or document.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V4_ID
        or document.get("site_count") != 43
        or document.get("classification_counts") != expected_counts
        or type(sites) is not list
        or len(sites) != 43
        or document.get("native_emitter_installed") is not False
        or document.get("derived_only_reconciliation_issues_native_record")
        is not False
        or document.get("missing_counter_families_have_leaf") is not False
        or document.get("missing_counter_families_have_emitter") is not False
        or document.get("operation_site_instrumentation_complete") is not False
        or document.get("counter_family_complete") is not False
        or document.get("hash_check_io_peak_granularity_profile_complete")
        is not False
        or document.get("live_operation_event_count") != 0
        or document.get("live_counter_record_count") != 0
        or document.get("work_vector_count") != 0
        or document.get("comparison_vector_count") != 0
        or document.get("actual_projection_proof_count") != 0
        or document.get("caller_totals_allowed") is not False
        or document.get("legacy_summary_translation_allowed") is not False
        or document.get("fresh_heldout_accessed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("scientific_endpoint_credit_allowed") is not False
        or document.get("counter_completeness_gate_passed") is not False
        or document.get("workload_economics_gate_passed") is not False
    ):
        _fail("strict-owner manifest identity, classification, or locks changed")
    required_site_keys = {
        "schema",
        "schema_version",
        "scope_key",
        "counter_registry_id",
        "stage_profile_id",
        "site_key",
        "stages",
        "classification",
        "target_paths",
        "reducer",
        "operation_source_module",
        "operation_source_symbol",
        "emitter_module",
        "emitter_symbol",
        "missing_counter_family",
        "audit_basis",
        "caller_totals_allowed",
        "live_evidence_issuer",
        "site_audit_id",
    }
    seen_keys: set[str] = set()
    seen_ids: set[str] = set()
    observed_counts = {key: 0 for key in expected_counts}
    for site in sites:
        if type(site) is not dict or set(site) != required_site_keys:
            _fail("strict-owner site audit is malformed")
        site_payload = dict(site)
        site_id = site_payload.pop("site_audit_id")
        try:
            exact_site_id = content_id(
                V075_K7_ROOT_CAP_OPERATION_SITE_AUDIT_V2_DOMAIN,
                site_payload,
            )
        except (TypeError, ValueError) as error:
            raise V075ConstructionAccountingKnownOwnerGapIndependentV5Violation(
                "strict-owner site audit cannot be canonically re-hashed"
            ) from error
        classification = site.get("classification")
        site_key = site.get("site_key")
        if (
            site_id != exact_site_id
            or site_id in seen_ids
            or type(site_key) is not str
            or site_key in seen_keys
            or classification not in observed_counts
            or site.get("counter_registry_id")
            != EXPECTED_COUNTER_REGISTRY_V4_ID
            or site.get("emitter_module") is not None
            or site.get("emitter_symbol") is not None
            or site.get("caller_totals_allowed") is not False
            or site.get("live_evidence_issuer") is not False
        ):
            _fail("strict-owner site audit identity or lock changed")
        seen_ids.add(site_id)
        seen_keys.add(site_key)
        observed_counts[classification] += 1
    if (
        [site["site_key"] for site in sites] != sorted(seen_keys)
        or observed_counts != expected_counts
    ):
        _fail("strict-owner site ordering or classification counts changed")
    return document


def _verify_registry(
    registry: Mapping[str, Any],
    upstream_registry: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    _rehash_embedded(
        registry,
        id_field="counter_registry_id",
        domain=CONSTRUCTION_COUNTER_REGISTRY_V5_DOMAIN,
        expected_id=EXPECTED_COUNTER_REGISTRY_V5_ID,
        label="V5 counter registry",
    )
    leaves = registry.get("leaves")
    base_leaves = upstream_registry.get("leaves")
    if (
        registry.get("schema") != "acfqp.counter_registry.v5"
        or registry.get("schema_version") != SCHEMA_VERSION
        or registry.get("counter_registry_key") != "acfqp_counter_registry_v5"
        or registry.get("v4_registry_id") != EXPECTED_COUNTER_REGISTRY_V4_ID
        or registry.get("v4_prefix_preserved_exactly") is not True
        or registry.get("known_owner_gap_addition_count") != 27
        or registry.get(
            "greedy_allocation_event_boundary_schema_frozen"
        ) is not True
        or registry.get("runtime_greedy_allocation_instrumented") is not False
        or registry.get(
            "support_descriptor_compile_distinct_from_typed_replay"
        )
        is not True
        or registry.get(
            "v4_owner_mismatch_paths_native_zero_on_registered_k7_path"
        )
        is not True
        or registry.get("minimal_known_owner_gap_closure_only") is not True
        or registry.get("operation_family_completeness_claimed") is not False
        or registry.get("runtime_owner_match_verified") is not False
        or registry.get("runtime_stage_attribution_verified") is not False
        or registry.get("operation_event_boundary_profile_complete") is not False
        or registry.get(
            "native_zero_required_when_registered_path_did_not_execute"
        )
        is not True
        or type(leaves) is not list
        or len(leaves) != 151
        or type(base_leaves) is not list
        or len(base_leaves) != 124
    ):
        _fail("V5 registry shape or V4 binding changed")
    by_path: dict[str, dict[str, Any]] = {}
    for row in leaves:
        if (
            type(row) is not dict
            or type(row.get("path")) is not str
            or row["path"] in by_path
        ):
            _fail("V5 registry leaf is malformed or duplicated")
        by_path[row["path"]] = row
    if list(by_path) != sorted(by_path):
        _fail("V5 registry leaves are not path-sorted")
    base = {row["path"]: row for row in base_leaves}
    if len(base) != 124 or any(
        by_path[path] != row for path, row in base.items()
    ):
        _fail("V5 registry did not preserve exact V4 leaf documents")
    additions = set(by_path) - set(base)
    if additions != set(_ADDITIONS) or any(
        by_path[path] != expected for path, expected in _ADDITIONS.items()
    ):
        _fail("V5 exact 27-leaf additive catalogue changed")
    operational = {
        path
        for path, row in by_path.items()
        if row.get("lane") == "operational"
    }
    required = {
        path for path, row in by_path.items() if row.get("required") is True
    }
    if len(operational) != 133 or len(required) != 144:
        _fail("V5 operational/required cardinality changed")
    return by_path, operational


def _stage_rows(
    profile: Mapping[str, Any], *, label: str
) -> dict[str, set[str]]:
    rows = profile.get("rules")
    if type(rows) is not list or len(rows) != 10:
        _fail(f"{label} stage rows changed")
    result: dict[str, set[str]] = {}
    for row in rows:
        if (
            type(row) is not dict
            or set(row) != {"stage_kind", "allowed_nonzero_paths"}
            or type(row.get("stage_kind")) is not str
            or type(row.get("allowed_nonzero_paths")) is not list
            or row["stage_kind"] in result
            or row["allowed_nonzero_paths"]
            != sorted(set(row["allowed_nonzero_paths"]))
        ):
            _fail(f"{label} stage rule is malformed")
        result[row["stage_kind"]] = set(row["allowed_nonzero_paths"])
    if tuple(sorted(result)) != _STAGES:
        _fail(f"{label} stage vocabulary changed")
    return result


def _verify_stage(
    stage: Mapping[str, Any],
    upstream_stage: Mapping[str, Any],
    known_paths: set[str],
) -> None:
    _rehash_embedded(
        stage,
        id_field="stage_profile_id",
        domain=CONSTRUCTION_STAGE_PROFILE_V5_DOMAIN,
        expected_id=EXPECTED_STAGE_PROFILE_V5_ID,
        label="V5 stage profile",
    )
    if (
        stage.get("schema") != "acfqp.construction_stage_profile.v5"
        or stage.get("schema_version") != SCHEMA_VERSION
        or stage.get("profile_key") != "construction_stage_exclusivity_v5"
        or stage.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V5_ID
        or stage.get("v4_stage_profile_id")
        != upstream_stage.get("stage_profile_id")
        or stage.get("v4_stage_ownership_preserved_exactly") is not True
        or stage.get(
            "batch_v2_initial_and_closed_stage_assignment_schema_frozen"
        ) is not True
        or stage.get(
            "dynamic_child_failed_prefix_assignment_schema_frozen"
        ) is not True
        or stage.get(
            "owner_correction_stage_assignment_schema_frozen"
        ) is not True
        or stage.get("runtime_owner_match_verified") is not False
        or stage.get("runtime_stage_attribution_verified") is not False
    ):
        _fail("V5 stage profile shape changed")
    base = _stage_rows(upstream_stage, label="verified V4")
    current = _stage_rows(stage, label="V5")
    for kind in _STAGES:
        if current[kind] != base[kind] | _STAGE_ADDITIONS.get(kind, set()):
            _fail("V5 exact additive stage ownership changed")
        if not current[kind] <= known_paths:
            _fail("V5 stage profile references an unknown path")


def _expected_terms(
    leaves: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "source_leaf": path,
            "target_axis": row["comparison_axis"],
            "coefficient": 1,
            "source_lane": row["lane"],
            "source_semantics_id": row["semantics_id"],
            "reducer": row["reducer"],
        }
        for path, row in leaves.items()
        if row.get("lane") == "operational"
    ]


def _verify_projection(
    comparison: Mapping[str, Any],
    actual: Mapping[str, Any],
    upstream_comparison: Mapping[str, Any],
    leaves: Mapping[str, Mapping[str, Any]],
    operational: set[str],
) -> None:
    _rehash_embedded(
        comparison,
        id_field="comparison_profile_id",
        domain=CONSTRUCTION_COMPARISON_PROFILE_V5_DOMAIN,
        expected_id=EXPECTED_COMPARISON_PROFILE_V5_ID,
        label="V5 comparison profile",
    )
    _rehash_embedded(
        actual,
        id_field="actual_projection_profile_id",
        domain=CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V5_DOMAIN,
        expected_id=EXPECTED_ACTUAL_PROJECTION_PROFILE_V5_ID,
        label="V5 actual projection profile",
    )
    expected = _expected_terms(leaves)
    axes = comparison.get("axes")
    if (
        comparison.get("schema") != "acfqp.comparison_profile.v5"
        or comparison.get("schema_version") != SCHEMA_VERSION
        or comparison.get("profile_key")
        != "comparison_profile_shared_resources_v5"
        or comparison.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V5_ID
        or comparison.get("scalar_cost_defined") is not False
        or axes != upstream_comparison.get("axes")
        or type(axes) is not list
        or tuple(row.get("name") for row in axes if type(row) is dict)
        != _SHARED_AXES
        or comparison.get("terms") != expected
        or len(expected) != 133
        or {row["source_leaf"] for row in expected} != operational
    ):
        _fail("V5 exact comparison projection changed")
    if (
        actual.get("schema") != "acfqp.actual_projection_profile.v5"
        or actual.get("schema_version") != SCHEMA_VERSION
        or actual.get("profile_key") != "actual_projection_construction_v5"
        or actual.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V5_ID
        or actual.get("comparison_profile_id")
        != EXPECTED_COMPARISON_PROFILE_V5_ID
        or actual.get("terms") != expected
        or actual.get("caller_supplied_actual_comparison_allowed") is not False
    ):
        _fail("V5 exact actual-projection profile changed")


def _expected_outer(
    *,
    upstream: (
        upstream_verifier
        .V075ConstructionAccountingOperationOwnershipIndependentVerificationV4
    ),
    upstream_document: Mapping[str, Any],
    registry: Mapping[str, Any],
    stage: Mapping[str, Any],
    comparison: Mapping[str, Any],
    actual: Mapping[str, Any],
    strict_owner: Mapping[str, Any],
    strict_owner_manifest_bytes: bytes,
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v075_construction_accounting_known_owner_gap_successor.v5"
        ),
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "upstream_profile_key": UPSTREAM_PROFILE_KEY,
        "terminal_scope": "CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_SCHEMA_ONLY",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": (
            "CONSTRUCTION_ACCOUNTING_V5_KNOWN_OWNER_GAPS_FROZEN_"
            "LIVE_EVIDENCE_LOCKED"
        ),
        "upstream_successor_id": upstream.successor_id,
        "upstream_verification_id": upstream.verification_id,
        "upstream_registry_successor_id": upstream.upstream_successor_id,
        "upstream_registry_verification_id": upstream.upstream_verification_id,
        "multiround_result_id": upstream_document["multiround_result_id"],
        "multiround_status": "CHILD_ACTION_ROW_CAP_EXCEEDED",
        "terminal_derivation_registry_id": (
            upstream_document["terminal_derivation_registry_id"]
        ),
        "upstream_counter_registry_id": upstream.counter_registry_id,
        "upstream_stage_profile_id": upstream.stage_profile_id,
        "upstream_comparison_profile_id": upstream.comparison_profile_id,
        "upstream_actual_projection_profile_id": (
            upstream.actual_projection_profile_id
        ),
        "strict_owner_manifest_id": EXPECTED_STRICT_OWNER_MANIFEST_V2_ID,
        "strict_owner_manifest_sha256": hashlib.sha256(
            strict_owner_manifest_bytes
        ).hexdigest(),
        "strict_owner_manifest_byte_count": len(strict_owner_manifest_bytes),
        "strict_owner_v1_manifest_id": (
            strict_owner["v1_operation_site_manifest_id"]
        ),
        "strict_owner_manifest_v2_bound_from_canonical_bytes": True,
        "counter_registry": registry,
        "counter_registry_id": EXPECTED_COUNTER_REGISTRY_V5_ID,
        "stage_profile": stage,
        "stage_profile_id": EXPECTED_STAGE_PROFILE_V5_ID,
        "comparison_profile": comparison,
        "comparison_profile_id": EXPECTED_COMPARISON_PROFILE_V5_ID,
        "actual_projection_profile": actual,
        "actual_projection_profile_id": (
            EXPECTED_ACTUAL_PROJECTION_PROFILE_V5_ID
        ),
        "v4_prefix_leaf_count": 124,
        "v4_prefix_preserved_exactly": True,
        "v5_addition_count": 27,
        "v5_leaf_count": 151,
        "v5_operational_leaf_count": 133,
        "v5_required_leaf_count": 144,
        "registered_stage_count": 10,
        "projection_term_count": 133,
        "initial_batch_v2_family_count": 8,
        "initial_live_model_family_count": 2,
        "failed_dynamic_family_count": 6,
        "closed_batch_v2_family_count": 11,
        "owner_stage_family_buckets_nonoverlapping": True,
        "greedy_allocation_event_boundary_schema_frozen": True,
        "runtime_greedy_allocation_instrumented": False,
        "support_descriptor_compile_distinct_from_typed_replay": True,
        "v4_owner_mismatch_paths_native_zero_on_registered_k7_path": True,
        "minimal_known_owner_gap_closure_only": True,
        "operation_family_completeness_claimed": False,
        "runtime_owner_match_verified": False,
        "runtime_stage_attribution_verified": False,
        "operation_event_boundary_profile_complete": False,
        "operation_site_instrumentation_complete": False,
        "operation_sites_wired": False,
        "derived_formula_registry_complete": False,
        "hash_check_io_peak_granularity_profile_complete": False,
        "live_operation_event_count": 0,
        "live_counter_record_count": 0,
        "work_vector_count": 0,
        "comparison_vector_count": 0,
        "actual_projection_proof_count": 0,
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
        "observer_opened": False,
        "target_accessed": False,
        "kernel_accessed": False,
        "planner_worker_launched": False,
        "plan_certificate": False,
        "infeasibility_certificate": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "workload_economics_gate_status": "NOT_RUN",
        "counter_completeness_gate_status": "NOT_RUN",
    }


@dataclass(frozen=True, slots=True)
class V075ConstructionAccountingKnownOwnerGapIndependentVerificationV5:
    _issuer: InitVar[object]
    successor_id: str
    successor_sha256: str
    successor_byte_count: int
    upstream_successor_id: str
    upstream_verification_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    strict_owner_manifest_id: str
    strict_owner_manifest_sha256: str
    strict_owner_manifest_byte_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value in (
            self.successor_id,
            self.successor_sha256,
            self.upstream_successor_id,
            self.upstream_verification_id,
            self.counter_registry_id,
            self.stage_profile_id,
            self.comparison_profile_id,
            self.actual_projection_profile_id,
            self.strict_owner_manifest_id,
            self.strict_owner_manifest_sha256,
        ):
            parse_content_id(value)
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.successor_byte_count) is not int
            or self.successor_byte_count <= 0
            or type(self.strict_owner_manifest_byte_count) is not int
            or self.strict_owner_manifest_byte_count <= 0
        ):
            _fail("independent known-owner-gap verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(
                V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_VERIFICATION_V5_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_accounting_known_owner_gap_"
                "independent_verification.v5"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "producer_profile_key": PRODUCER_PROFILE_KEY,
            "successor_id": self.successor_id,
            "successor_sha256": self.successor_sha256,
            "successor_byte_count": self.successor_byte_count,
            "upstream_successor_id": self.upstream_successor_id,
            "upstream_verification_id": self.upstream_verification_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "strict_owner_manifest_id": self.strict_owner_manifest_id,
            "strict_owner_manifest_sha256": (
                self.strict_owner_manifest_sha256
            ),
            "strict_owner_manifest_byte_count": (
                self.strict_owner_manifest_byte_count
            ),
            "strict_owner_manifest_rehashed_independently": True,
            "strict_owner_site_audits_rehashed_independently": True,
            "producer_imported": False,
            "producer_entry_called": False,
            "construction_accounting_v5_core_imported": False,
            "construction_accounting_v5_core_entry_called": False,
            "upstream_contract_187_replayed_exactly": True,
            "embedded_profile_ids_rehashed_independently": True,
            "v4_prefix_compared_from_verified_upstream_bytes": True,
            "twenty_seven_additions_checked_independently": True,
            "greedy_allocation_boundary_schema_checked_independently": True,
            "descriptor_compile_owner_schema_checked_independently": True,
            "stage_assignment_schema_checked_independently": True,
            "projection_133_terms_checked_independently": True,
            "minimal_known_owner_gap_closure_only": True,
            "operation_family_completeness_claimed": False,
            "runtime_owner_match_verified": False,
            "runtime_stage_attribution_verified": False,
            "operation_event_boundary_profile_complete": False,
            "operation_site_instrumentation_complete": False,
            "live_counter_record_count": 0,
            "work_vector_count": 0,
            "all_path_native_accounting_complete": False,
            "official_execution_allowed": False,
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
            "independent known-owner-gap verifications are in-memory-only"
        )


def verify_v075_construction_accounting_known_owner_gap_bytes_v5(
    *,
    successor_bytes: bytes,
    operation_ownership_successor_bytes: bytes,
    strict_owner_manifest_id: str,
    strict_owner_manifest_bytes: bytes,
    registry_successor_bytes: bytes,
    schema_closure_bytes: bytes,
    foundation_bytes: bytes,
    source_code_provenance_bytes: bytes,
    repository_root: str,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075ConstructionAccountingKnownOwnerGapIndependentVerificationV5:
    """Replay contract 1.87 and independently verify contract 1.89."""

    try:
        upstream = (
            upstream_verifier
            .verify_v075_construction_accounting_operation_ownership_bytes_v4(
                successor_bytes=operation_ownership_successor_bytes,
                registry_successor_bytes=registry_successor_bytes,
                schema_closure_bytes=schema_closure_bytes,
                foundation_bytes=foundation_bytes,
                source_code_provenance_bytes=source_code_provenance_bytes,
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=public_context_closure_bytes,
                private_generation_seed=private_generation_seed,
                private_salt=private_salt,
            )
        )
        successor = _strict_document(
            successor_bytes, label="contract-1.89 known-owner-gap successor"
        )
        strict_owner = _verify_strict_owner_manifest(
            strict_owner_manifest_id=strict_owner_manifest_id,
            strict_owner_manifest_bytes=strict_owner_manifest_bytes,
        )
        upstream_document = _strict_document(
            operation_ownership_successor_bytes,
            label="verified contract-1.87 operation ownership",
        )
        if (
            upstream_document.get("successor_id") != upstream.successor_id
            or hashlib.sha256(operation_ownership_successor_bytes).hexdigest()
            != upstream.successor_sha256
            or len(operation_ownership_successor_bytes)
            != upstream.successor_byte_count
        ):
            _fail("verified contract-1.87 bytes changed")
        upstream_registry = upstream_document.get("counter_registry")
        upstream_stage = upstream_document.get("stage_profile")
        upstream_comparison = upstream_document.get("comparison_profile")
        registry = successor.get("counter_registry")
        stage = successor.get("stage_profile")
        comparison = successor.get("comparison_profile")
        actual = successor.get("actual_projection_profile")
        if not all(
            type(value) is dict
            for value in (
                upstream_registry,
                upstream_stage,
                upstream_comparison,
                registry,
                stage,
                comparison,
                actual,
            )
        ):
            _fail("upstream or V5 embedded profiles are absent")
        if (
            registry.get("v4_registry_id")
            != upstream.counter_registry_id
            or upstream.counter_registry_id != EXPECTED_COUNTER_REGISTRY_V4_ID
            or strict_owner["counter_registry_id"]
            != upstream.counter_registry_id
        ):
            _fail("V5, strict-owner, and verified V4 registry bindings differ")
        leaves, operational = _verify_registry(registry, upstream_registry)
        _verify_stage(stage, upstream_stage, set(leaves))
        _verify_projection(
            comparison,
            actual,
            upstream_comparison,
            leaves,
            operational,
        )
        expected = _expected_outer(
            upstream=upstream,
            upstream_document=upstream_document,
            registry=registry,
            stage=stage,
            comparison=comparison,
            actual=actual,
            strict_owner=strict_owner,
            strict_owner_manifest_bytes=strict_owner_manifest_bytes,
        )
        expected_id = content_id(
            V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_SUCCESSOR_V5_DOMAIN,
            expected,
        )
        if (
            successor != {**expected, "successor_id": expected_id}
            or canonical_json_bytes(successor) != successor_bytes
        ):
            _fail("known-owner-gap outer closure changed")
        return V075ConstructionAccountingKnownOwnerGapIndependentVerificationV5(
            _VERIFICATION_ISSUER,
            expected_id,
            hashlib.sha256(successor_bytes).hexdigest(),
            len(successor_bytes),
            upstream.successor_id,
            upstream.verification_id,
            EXPECTED_COUNTER_REGISTRY_V5_ID,
            EXPECTED_STAGE_PROFILE_V5_ID,
            EXPECTED_COMPARISON_PROFILE_V5_ID,
            EXPECTED_ACTUAL_PROJECTION_PROFILE_V5_ID,
            EXPECTED_STRICT_OWNER_MANIFEST_V2_ID,
            hashlib.sha256(strict_owner_manifest_bytes).hexdigest(),
            len(strict_owner_manifest_bytes),
        )
    except Exception:
        raise V075ConstructionAccountingKnownOwnerGapIndependentV5Violation(
            _REPLAY_MISMATCH
        ) from None


__all__ = [
    "EXPECTED_ACTUAL_PROJECTION_PROFILE_V5_ID",
    "EXPECTED_COMPARISON_PROFILE_V5_ID",
    "EXPECTED_COUNTER_REGISTRY_V5_ID",
    "EXPECTED_STRICT_OWNER_MANIFEST_V1_ID",
    "EXPECTED_STRICT_OWNER_MANIFEST_V2_BYTE_COUNT",
    "EXPECTED_STRICT_OWNER_MANIFEST_V2_ID",
    "EXPECTED_STRICT_OWNER_MANIFEST_V2_SHA256",
    "EXPECTED_STAGE_PROFILE_V5_ID",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "V075ConstructionAccountingKnownOwnerGapIndependentV5Violation",
    "V075ConstructionAccountingKnownOwnerGapIndependentVerificationV5",
    "verify_v075_construction_accounting_known_owner_gap_bytes_v5",
]
