"""Independent verifier for the V6 operation-boundary schema bundle.

This module intentionally imports none of the V6 registry, V3 boundary,
partial-native transcript, or producer-runtime implementations.  It consumes
canonical bytes, independently replays every domain-separated identity, and
checks the exact additive catalogue, stage routing, projection, boundary, and
partial-chain locks.  A successful result is schema evidence only: it is not
a CounterRecord, WorkVector, ComparisonVector, certificate, or Gate result.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
import re
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    V075_CONSTRUCTION_ACCOUNTING_OPERATION_BOUNDARY_VERIFICATION_V6_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "6.0.0"
PROFILE_KEY = (
    "v075_construction_accounting_operation_boundary_"
    "independent_verifier_v6"
)
MAX_BYTES = 64 * 1024 * 1024

V5_REGISTRY_DOMAIN = "acfqp:counter-registry:v5"
V6_REGISTRY_DOMAIN = "acfqp:counter-registry:v6"
V6_STAGE_DOMAIN = "acfqp:construction-stage-profile:v6"
V6_COMPARISON_DOMAIN = "acfqp:comparison-profile:v6"
V6_ACTUAL_DOMAIN = "acfqp:actual-projection-profile:v6"
BOUNDARY_DOMAIN = "acfqp:v075-k7-root-cap-operation-boundary:v3"
BOUNDARY_MANIFEST_DOMAIN = (
    "acfqp:v075-k7-root-cap-operation-boundary-manifest:v3"
)
TRANSCRIPT_START_DOMAIN = (
    "acfqp:construction-partial-native-occurrence-start:v1"
)
TRANSCRIPT_STAGE_START_DOMAIN = (
    "acfqp:construction-partial-native-stage-start:v1"
)
TRANSCRIPT_EVENT_DOMAIN = (
    "acfqp:construction-partial-native-operation-event:v1"
)
TRANSCRIPT_STAGE_COMPLETION_DOMAIN = (
    "acfqp:construction-partial-native-stage-completion:v1"
)
TRANSCRIPT_COMPLETION_DOMAIN = (
    "acfqp:construction-partial-native-occurrence-completion:v1"
)
TRANSCRIPT_ABORT_DOMAIN = (
    "acfqp:construction-partial-native-occurrence-abort:v1"
)
TRANSCRIPT_DOMAIN = (
    "acfqp:construction-partial-native-occurrence-transcript:v1"
)
VERIFICATION_DOMAIN = (
    V075_CONSTRUCTION_ACCOUNTING_OPERATION_BOUNDARY_VERIFICATION_V6_DOMAIN
)

EXPECTED_V5_REGISTRY_ID = (
    "cf1e63f677fa6f9831213b8b48ca88e1"
    "a8d489276af5d30029951670cfe6736f"
)
EXPECTED_V6_REGISTRY_ID = (
    "77c735d8a02c932180352c1a12905165"
    "c22014f359dd59fe470a1397585f4a1e"
)
EXPECTED_V6_STAGE_ID = (
    "d0c4fbd140e5c8d8ed8c28974f6a209d"
    "2a892b35f9042f2c0717625cb8458c74"
)
EXPECTED_V6_COMPARISON_ID = (
    "d815846f6814ba535e669e722f4bcba37"
    "af8061f56b364ddb31def4dcdc4a308"
)
EXPECTED_V6_ACTUAL_ID = (
    "2281e1fc2e0091e4d55ab0e4490f5b10"
    "f7f2d76315c54785c1aff92ef49725a7"
)
EXPECTED_BOUNDARY_MANIFEST_ID = (
    "086420d44a80152828fbaaa64c2ff8112"
    "2eb65921559c42a17da3f53ab59eb90"
)
EXPECTED_V2_MANIFEST_ID = (
    "c71405162a49093abe8f2325943c77e0"
    "b49ec9c0850660e67ac271f14bc11688"
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
_FIVE_STAGE_PLAN = (
    "PREOPEN_COMMON_PREFIX",
    "INITIAL_ACQUISITION",
    "INITIAL_MODEL_BUILD",
    "FAILED_ABSTRACT_PREFIX",
    "CLOSED_RECONCILIATION_AND_TERMINALIZATION",
)
_UNUSED_STAGES = (
    "OPEN_INCREMENTAL_ACQUISITION",
    "OPEN_CHECKPOINT_REPLANNING",
    "LOCAL_ATTEMPT",
    "DIRECT_FALLBACK",
    "REBUILD",
)
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
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")

_ENGINE = "h2_graph_transition_engine_v1"
_PRIVATE = "v075_private_observer_boundary_v2"
_LIVE_MODEL = "v075_live_incremental_model_authority_v2"
_PLANNING = "v075_batch_native_planning_backend_v2"
_SEQUENTIAL = "sequential_bernoulli_acquisition_v1"

_INITIAL_ACQUISITION_SCOPE = (
    "construction_occurrence_initial_acquisition_prefix"
)
_OPEN_ACQUISITION_SCOPE = (
    "construction_occurrence_open_incremental_acquisition"
)
_INITIAL_BUILD_SCOPE = "construction_occurrence_initial_build_epoch"
_OPEN_CHECKPOINT_SCOPE = (
    "construction_occurrence_open_checkpoint_replanning"
)
_CLOSED_SCOPE = (
    "construction_occurrence_closed_reconciliation_and_terminalization"
)

_CLASSIFICATION_COUNTS = {
    "V6_NATIVE_BOUNDARY_SCHEMA_ONLY": 27,
    "V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY": 6,
    "V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY": 43,
    "V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY": 13,
    "OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO": 43,
    "LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN": 16,
    "LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN": 2,
}
_LIVE_EVENT_CLASSIFICATIONS = {
    "V6_NATIVE_BOUNDARY_SCHEMA_ONLY",
    "V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY",
    "V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY",
    "V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY",
}

_ROOT_ACTIVE_V4_PATHS = {
    "acquisition.initial_outcome_aggregate_rows",
    "acquisition.initial_support_freezes",
    "audit.failed_child_catalogues_built",
    "build.initial_confidence_event_evaluations",
    "build.initial_interval_row_evaluations",
    "build.initial_model_rows_built",
    "build.initial_policy_assignments_evaluated",
    "build.initial_source_units_compiled",
    "closure.reconciliation_confidence_event_evaluations",
    "closure.reconciliation_interval_row_evaluations",
    "closure.reconciliation_outcome_projections",
    "closure.reconciliation_policy_assignments_evaluated",
    "closure.reconciliation_private_replay_outcome_aggregate_rows",
}
_OPEN_V4_PATHS = {
    "acquisition.incremental_outcome_aggregate_rows",
    "acquisition.incremental_support_freezes",
    "build.open_checkpoint_confidence_event_evaluations",
    "build.open_checkpoint_interval_row_evaluations",
    "build.open_checkpoint_model_rows_built",
    "build.open_checkpoint_policy_assignments_evaluated",
    "build.open_checkpoint_source_units_compiled",
}
_V4_COMMON_PENDING = {
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "process.launches",
}
_V4_CAPACITY_PENDING = {
    "io.mounted_bytes_peak",
    "memory.working_bytes_peak",
}

_LEGACY_REPLACEMENTS = {
    "acquisition.initial_observer_accepted_draws": (
        "acquisition.initial_engine_ground_draws",
    ),
    "acquisition.initial_observer_random_word_calls": (
        "acquisition.initial_engine_random_word_calls",
    ),
    "acquisition.initial_observer_rejections": (
        "acquisition.initial_engine_rejections",
    ),
    "acquisition.initial_signed_batches": (
        "acquisition.initial_signed_batches_committed",
        "acquisition.initial_signed_batches_materialized",
    ),
    "acquisition.incremental_observer_accepted_draws": (
        "acquisition.incremental_engine_ground_draws",
    ),
    "acquisition.incremental_observer_random_word_calls": (
        "acquisition.incremental_engine_random_word_calls",
    ),
    "acquisition.incremental_observer_rejections": (
        "acquisition.incremental_engine_rejections",
    ),
    "acquisition.incremental_signed_batches": (
        "acquisition.incremental_signed_batches_committed",
        "acquisition.incremental_signed_batches_materialized",
    ),
    "build.initial_exact_likelihood_comparisons": (
        "build.initial_sequential_exact_likelihood_comparisons",
    ),
    "build.initial_interval_log_search_evaluations": (
        "build.initial_sequential_interval_log_search_evaluations",
    ),
    "build.open_checkpoint_exact_likelihood_comparisons": (
        "build.open_checkpoint_sequential_exact_likelihood_comparisons",
    ),
    "build.open_checkpoint_interval_log_search_evaluations": (
        "build.open_checkpoint_sequential_interval_log_search_evaluations",
    ),
    "build.open_checkpoint_outcome_projections": (
        "build.open_checkpoint_live_model_outcome_projections",
    ),
    "closure.reconciliation_private_replay_ground_steps": (
        "closure.reconciliation_engine_ground_draws",
    ),
    "closure.reconciliation_private_replay_random_word_calls": (
        "closure.reconciliation_engine_random_word_calls",
    ),
    "closure.reconciliation_private_replay_rejections": (
        "closure.reconciliation_engine_rejections",
    ),
    "closure.reconciliation_exact_likelihood_comparisons": (
        "closure.reconciliation_sequential_exact_likelihood_comparisons",
    ),
    "closure.reconciliation_interval_log_search_evaluations": (
        "closure.reconciliation_sequential_interval_log_search_evaluations",
    ),
}


class V075ConstructionAccountingOperationBoundaryIndependentV6Violation(
    ValueError
):
    """The canonical schema bundle or partial-native transcript is invalid."""


_Violation = V075ConstructionAccountingOperationBoundaryIndependentV6Violation


def _fail(message: str) -> NoReturn:
    raise V075ConstructionAccountingOperationBoundaryIndependentV6Violation(
        message
    )


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        _fail(f"{label} bytes are absent or exceed the cap")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionAccountingOperationBoundaryIndependentV6Violation(
            f"{label} is not strict UTF-8 JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _exact_keys(value: Any, expected: set[str], *, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        _fail(f"{label} has missing or unknown fields")
    return value


def _rehash(
    document: Mapping[str, Any],
    *,
    id_field: str,
    domain: str,
    label: str,
    expected_id: str | None = None,
) -> str:
    if type(document) is not dict or id_field not in document:
        _fail(f"{label} has no identity")
    payload = dict(document)
    claimed = payload.pop(id_field)
    try:
        parse_content_id(claimed)
        actual = content_id(domain, payload)
    except (TypeError, ValueError) as error:
        raise V075ConstructionAccountingOperationBoundaryIndependentV6Violation(
            f"{label} cannot be independently re-hashed"
        ) from error
    if claimed != actual or (expected_id is not None and actual != expected_id):
        _fail(f"{label} identity changed")
    return actual


def _leaf(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    scope: str,
    *,
    lane: str = "operational",
    axis: str | None = "nonkernel_compute_events",
) -> dict[str, Any]:
    return {
        "path": path,
        "semantics_id": semantics_id,
        "owner": owner,
        "unit": unit,
        "lane": lane,
        "scope": scope,
        "reducer": "sum",
        "comparison_axis": axis,
        "required": True,
    }


def _observation_rows(
    *, prefix: str, semantics_stage: str, scope: str
) -> tuple[dict[str, Any], ...]:
    return (
        _leaf(
            f"acquisition.{prefix}_engine_ground_draws",
            f"v075-engine-ground-draw-v6-{semantics_stage}",
            _ENGINE,
            "ground_draws",
            scope,
            axis="kernel_transition_calls",
        ),
        _leaf(
            f"acquisition.{prefix}_engine_random_word_calls",
            f"v075-engine-random-word-call-v6-{semantics_stage}",
            _ENGINE,
            "random_word_calls",
            scope,
        ),
        _leaf(
            f"acquisition.{prefix}_engine_rejections",
            f"v075-engine-rejection-v6-{semantics_stage}",
            _ENGINE,
            "rejections",
            scope,
            lane="diagnostic",
            axis=None,
        ),
        _leaf(
            f"acquisition.{prefix}_engine_stream_initialization_merges",
            f"v075-engine-stream-init-merge-v6-{semantics_stage}",
            _ENGINE,
            "merge_calls",
            scope,
            axis="kernel_transition_calls",
        ),
        _leaf(
            f"acquisition.{prefix}_observer_accumulator_updates",
            f"v075-observer-accumulator-update-v6-{semantics_stage}",
            _PRIVATE,
            "accumulator_updates",
            scope,
        ),
        _leaf(
            f"acquisition.{prefix}_signed_batches_materialized",
            f"v075-signed-batch-materialize-v6-{semantics_stage}",
            _PRIVATE,
            "signed_batches",
            scope,
        ),
        _leaf(
            f"acquisition.{prefix}_signed_batches_committed",
            f"v075-signed-batch-journal-commit-v6-{semantics_stage}",
            _PRIVATE,
            "journal_commits",
            scope,
        ),
    )


def _confidence_rows(
    *,
    prefix: str,
    semantics_stage: str,
    scope: str,
    row_source: bool,
) -> tuple[dict[str, Any], ...]:
    rows = [
        _leaf(
            f"{prefix}_sequential_exact_likelihood_comparisons",
            f"v075-sequential-exact-likelihood-comparison-v6-{semantics_stage}",
            _SEQUENTIAL,
            "likelihood_comparisons",
            scope,
        ),
        _leaf(
            f"{prefix}_sequential_interval_log_search_evaluations",
            f"v075-sequential-log-search-evaluation-v6-{semantics_stage}",
            _SEQUENTIAL,
            "log_search_evaluations",
            scope,
        ),
        _leaf(
            f"{prefix}_confidence_cache_lookups",
            f"v075-confidence-cache-lookup-v6-{semantics_stage}",
            _SEQUENTIAL,
            "cache_lookups",
            scope,
        ),
        _leaf(
            f"{prefix}_confidence_cache_hits",
            f"v075-confidence-cache-hit-v6-{semantics_stage}",
            _SEQUENTIAL,
            "cache_hits",
            scope,
            lane="diagnostic",
            axis=None,
        ),
        _leaf(
            f"{prefix}_confidence_cache_misses",
            f"v075-confidence-cache-miss-v6-{semantics_stage}",
            _SEQUENTIAL,
            "cache_misses",
            scope,
            lane="diagnostic",
            axis=None,
        ),
        _leaf(
            f"{prefix}_batch_v2_replay_checkpoint_evaluations",
            f"v075-batch-v2-replay-checkpoint-evaluation-v6-{semantics_stage}",
            _PLANNING,
            "checkpoint_replays",
            scope,
        ),
        _leaf(
            f"{prefix}_batch_v2_replay_interval_reconstructions",
            f"v075-batch-v2-replay-interval-reconstruction-v6-{semantics_stage}",
            _PLANNING,
            "interval_reconstructions",
            scope,
        ),
        _leaf(
            f"{prefix}_batch_v2_option_metric_evaluations",
            f"v075-batch-v2-option-metric-evaluation-v6-{semantics_stage}",
            _PLANNING,
            "option_metric_evaluations",
            scope,
        ),
        _leaf(
            f"{prefix}_batch_v2_policy_assignment_cap_checks",
            f"v075-batch-v2-policy-assignment-cap-check-v6-{semantics_stage}",
            _PLANNING,
            "cap_checks",
            scope,
        ),
    ]
    if row_source:
        rows.append(
            _leaf(
                f"{prefix}_live_model_row_source_bindings_built",
                f"v075-live-model-row-source-binding-build-v6-{semantics_stage}",
                _LIVE_MODEL,
                "row_source_bindings",
                scope,
            )
        )
    return tuple(rows)


_OPEN_BATCH_FAMILIES = (
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
    (
        "support_descriptors_compiled",
        "support-descriptor-compile",
        "support_descriptors",
    ),
)


def _open_checkpoint_rows() -> tuple[dict[str, Any], ...]:
    rows = []
    for suffix, semantics, unit in _OPEN_BATCH_FAMILIES:
        live = suffix == "support_descriptors_compiled"
        rows.append(
            _leaf(
                (
                    "build.open_checkpoint_live_model_"
                    "support_descriptors_compiled"
                    if live
                    else f"build.open_checkpoint_batch_v2_{suffix}"
                ),
                (
                    "v075-live-model-support-descriptor-compile-v6-"
                    "open-checkpoint"
                    if live
                    else f"v075-batch-v2-{semantics}-v6-open-checkpoint"
                ),
                _LIVE_MODEL if live else _PLANNING,
                unit,
                _OPEN_CHECKPOINT_SCOPE,
            )
        )
    rows.append(
        _leaf(
            "build.open_checkpoint_live_model_outcome_projections",
            "v075-live-model-outcome-projection-v6-open-checkpoint",
            _LIVE_MODEL,
            "outcome_projections",
            _OPEN_CHECKPOINT_SCOPE,
        )
    )
    return tuple(rows)


def _closed_replay_rows() -> tuple[dict[str, Any], ...]:
    return (
        _leaf(
            "closure.reconciliation_engine_ground_draws",
            "v075-engine-ground-draw-v6-closed-private-replay",
            _ENGINE,
            "ground_draws",
            _CLOSED_SCOPE,
            axis="kernel_transition_calls",
        ),
        _leaf(
            "closure.reconciliation_engine_random_word_calls",
            "v075-engine-random-word-call-v6-closed-private-replay",
            _ENGINE,
            "random_word_calls",
            _CLOSED_SCOPE,
        ),
        _leaf(
            "closure.reconciliation_engine_rejections",
            "v075-engine-rejection-v6-closed-private-replay",
            _ENGINE,
            "rejections",
            _CLOSED_SCOPE,
            lane="diagnostic",
            axis=None,
        ),
        _leaf(
            "closure.reconciliation_engine_stream_initialization_merges",
            "v075-engine-stream-init-merge-v6-closed-private-replay",
            _ENGINE,
            "merge_calls",
            _CLOSED_SCOPE,
            axis="kernel_transition_calls",
        ),
        _leaf(
            "closure.reconciliation_private_replay_accumulator_updates",
            "v075-private-replay-accumulator-update-v6-closed-reconciliation",
            _PRIVATE,
            "accumulator_updates",
            _CLOSED_SCOPE,
        ),
    )


def _addition_catalogue() -> dict[str, dict[str, Any]]:
    rows = (
        *_observation_rows(
            prefix="initial",
            semantics_stage="initial-acquisition",
            scope=_INITIAL_ACQUISITION_SCOPE,
        ),
        *_observation_rows(
            prefix="incremental",
            semantics_stage="open-incremental-acquisition",
            scope=_OPEN_ACQUISITION_SCOPE,
        ),
        *_confidence_rows(
            prefix="build.initial",
            semantics_stage="initial-build",
            scope=_INITIAL_BUILD_SCOPE,
            row_source=True,
        ),
        *_open_checkpoint_rows(),
        *_confidence_rows(
            prefix="build.open_checkpoint",
            semantics_stage="open-checkpoint",
            scope=_OPEN_CHECKPOINT_SCOPE,
            row_source=True,
        ),
        *_closed_replay_rows(),
        *_confidence_rows(
            prefix="closure.reconciliation",
            semantics_stage="closed-reconciliation",
            scope=_CLOSED_SCOPE,
            row_source=False,
        ),
    )
    result = {row["path"]: row for row in rows}
    if len(result) != 58:  # pragma: no cover - import invariant
        raise RuntimeError("independent V6 addition catalogue changed")
    return result


_ADDITIONS = _addition_catalogue()


def _stage_for_path(path: str) -> str:
    if path.startswith("acquisition.initial_"):
        return "INITIAL_ACQUISITION"
    if path.startswith("acquisition.incremental_"):
        return "OPEN_INCREMENTAL_ACQUISITION"
    if path.startswith("build.initial_"):
        return "INITIAL_MODEL_BUILD"
    if path.startswith("build.open_checkpoint_"):
        return "OPEN_CHECKPOINT_REPLANNING"
    if path.startswith("audit.dynamic_"):
        return "FAILED_ABSTRACT_PREFIX"
    if path.startswith("closure.reconciliation_"):
        return "CLOSED_RECONCILIATION_AND_TERMINALIZATION"
    _fail(f"counter path {path!r} has no registered construction stage")


def _verify_v5_registry(raw: bytes) -> dict[str, Any]:
    document = _strict_document(raw, label="V5 counter registry")
    _rehash(
        document,
        id_field="counter_registry_id",
        domain=V5_REGISTRY_DOMAIN,
        label="V5 counter registry",
        expected_id=EXPECTED_V5_REGISTRY_ID,
    )
    leaves = document.get("leaves")
    if (
        document.get("schema") != "acfqp.counter_registry.v5"
        or document.get("schema_version") != "5.0.0"
        or document.get("counter_registry_key") != "acfqp_counter_registry_v5"
        or type(leaves) is not list
        or len(leaves) != 151
    ):
        _fail("V5 counter registry shape changed")
    paths = [row.get("path") for row in leaves if type(row) is dict]
    if len(paths) != 151 or paths != sorted(set(paths)):
        _fail("V5 counter registry leaves are malformed or reordered")
    return document


_REGISTRY_KEYS = {
    "schema",
    "schema_version",
    "counter_registry_key",
    "v5_registry_id",
    "leaves",
    "v5_leaf_documents_preserved_exactly",
    "owner_correction_addition_count",
    "primitive_engine_and_sequential_owners_frozen",
    "confidence_cache_lookup_is_operational",
    "confidence_cache_hit_miss_are_diagnostic",
    "exact_and_log_work_counts_cache_miss_computation_only",
    "open_incremental_and_checkpoint_stage_schema_supported",
    "legacy_mismatched_paths_deleted_or_relabelled",
    "runtime_operation_emitters_installed",
    "runtime_owner_match_verified",
    "runtime_stage_attribution_verified",
    "operation_family_completeness_claimed",
    "official_execution_allowed",
    "counter_completeness_gate_passed",
    "workload_economics_gate_passed",
    "counter_registry_id",
}


def _verify_registry(
    raw: bytes, v5: Mapping[str, Any]
) -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
    set[str],
    set[str],
]:
    document = _strict_document(raw, label="V6 counter registry")
    _exact_keys(document, _REGISTRY_KEYS, label="V6 counter registry")
    _rehash(
        document,
        id_field="counter_registry_id",
        domain=V6_REGISTRY_DOMAIN,
        label="V6 counter registry",
        expected_id=EXPECTED_V6_REGISTRY_ID,
    )
    locks = {
        "v5_leaf_documents_preserved_exactly": True,
        "primitive_engine_and_sequential_owners_frozen": True,
        "confidence_cache_lookup_is_operational": True,
        "confidence_cache_hit_miss_are_diagnostic": True,
        "exact_and_log_work_counts_cache_miss_computation_only": True,
        "open_incremental_and_checkpoint_stage_schema_supported": True,
        "legacy_mismatched_paths_deleted_or_relabelled": False,
        "runtime_operation_emitters_installed": False,
        "runtime_owner_match_verified": False,
        "runtime_stage_attribution_verified": False,
        "operation_family_completeness_claimed": False,
        "official_execution_allowed": False,
        "counter_completeness_gate_passed": False,
        "workload_economics_gate_passed": False,
    }
    leaves = document.get("leaves")
    if (
        document.get("schema") != "acfqp.counter_registry.v6"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("counter_registry_key") != "acfqp_counter_registry_v6"
        or document.get("v5_registry_id") != EXPECTED_V5_REGISTRY_ID
        or document.get("owner_correction_addition_count") != 58
        or any(document.get(key) is not expected for key, expected in locks.items())
        or type(leaves) is not list
        or len(leaves) != 209
    ):
        _fail("V6 registry identity, cardinality, or locks changed")
    by_path: dict[str, dict[str, Any]] = {}
    for row in leaves:
        if (
            type(row) is not dict
            or set(row)
            != {
                "path",
                "semantics_id",
                "owner",
                "unit",
                "lane",
                "scope",
                "reducer",
                "comparison_axis",
                "required",
            }
            or type(row.get("path")) is not str
            or row["path"] in by_path
        ):
            _fail("V6 registry leaf is malformed or duplicated")
        by_path[row["path"]] = row
    if list(by_path) != sorted(by_path):
        _fail("V6 registry leaves are not path-sorted")
    v5_by_path = {row["path"]: row for row in v5["leaves"]}
    if len(v5_by_path) != 151 or any(
        by_path.get(path) != row for path, row in v5_by_path.items()
    ):
        _fail("V6 did not preserve all 151 V5 leaf documents exactly")
    additions = set(by_path) - set(v5_by_path)
    if additions != set(_ADDITIONS) or any(
        by_path[path] != expected for path, expected in _ADDITIONS.items()
    ):
        _fail("V6 exact 58-leaf addition catalogue changed")
    operational = {
        path for path, row in by_path.items() if row["lane"] == "operational"
    }
    required = {path for path, row in by_path.items() if row["required"] is True}
    if len(operational) != 182 or len(required) != 202:
        _fail("V6 operational or required cardinality changed")
    v5_additions = {
        path
        for path, row in v5_by_path.items()
        if "-v5-" in row["semantics_id"]
    }
    v4_paths = set(v5_by_path) - v5_additions
    v4_required = {
        path for path in v4_paths if v5_by_path[path]["required"] is True
    }
    if (
        len(v5_additions) != 27
        or len(v4_paths) != 124
        or len(v4_required) != 117
    ):
        _fail("independent V4/V5 prefix cardinalities changed")
    return document, by_path, operational, v4_required


_STAGE_KEYS = {
    "schema",
    "schema_version",
    "profile_key",
    "counter_registry_id",
    "v5_stage_profile_id",
    "rules",
    "v5_stage_ownership_preserved_exactly",
    "open_incremental_owner_corrections_routed",
    "open_checkpoint_owner_corrections_routed",
    "runtime_owner_match_verified",
    "runtime_stage_attribution_verified",
    "stage_profile_id",
}


def _verify_stage(
    raw: bytes, by_path: Mapping[str, Mapping[str, Any]]
) -> dict[str, set[str]]:
    document = _strict_document(raw, label="V6 stage profile")
    _exact_keys(document, _STAGE_KEYS, label="V6 stage profile")
    _rehash(
        document,
        id_field="stage_profile_id",
        domain=V6_STAGE_DOMAIN,
        label="V6 stage profile",
        expected_id=EXPECTED_V6_STAGE_ID,
    )
    if (
        document.get("schema") != "acfqp.construction_stage_profile.v6"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("profile_key") != "construction_stage_exclusivity_v6"
        or document.get("counter_registry_id") != EXPECTED_V6_REGISTRY_ID
        or document.get("v5_stage_ownership_preserved_exactly") is not True
        or document.get("open_incremental_owner_corrections_routed") is not True
        or document.get("open_checkpoint_owner_corrections_routed") is not True
        or document.get("runtime_owner_match_verified") is not False
        or document.get("runtime_stage_attribution_verified") is not False
    ):
        _fail("V6 stage profile identities or locks changed")
    rows = document.get("rules")
    if type(rows) is not list or len(rows) != 10:
        _fail("V6 stage profile cardinality changed")
    result: dict[str, set[str]] = {}
    for row in rows:
        _exact_keys(
            row,
            {"stage_kind", "allowed_nonzero_paths"},
            label="V6 stage rule",
        )
        stage = row["stage_kind"]
        paths = row["allowed_nonzero_paths"]
        if (
            stage not in _STAGES
            or stage in result
            or type(paths) is not list
            or paths != sorted(set(paths))
            or any(path not in by_path for path in paths)
        ):
            _fail("V6 stage rule is malformed or misrouted")
        result[stage] = set(paths)
    if tuple(result) != _STAGES:
        _fail("V6 stage rules are reordered or incomplete")
    for path in _ADDITIONS:
        expected_stage = _stage_for_path(path)
        if sum(path in paths for paths in result.values()) != 1 or path not in result[
            expected_stage
        ]:
            _fail("V6 addition is not routed to exactly one expected stage")
    expected_addition_counts = {
        "INITIAL_ACQUISITION": 7,
        "OPEN_INCREMENTAL_ACQUISITION": 7,
        "INITIAL_MODEL_BUILD": 10,
        "OPEN_CHECKPOINT_REPLANNING": 20,
        "CLOSED_RECONCILIATION_AND_TERMINALIZATION": 14,
    }
    if any(
        len(set(_ADDITIONS) & result[stage]) != count
        for stage, count in expected_addition_counts.items()
    ):
        _fail("V6 exact stage-addition cardinalities changed")
    return result


def _expected_terms(
    by_path: Mapping[str, Mapping[str, Any]]
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
        for path, row in by_path.items()
        if row["lane"] == "operational"
    ]


def _verify_projections(
    comparison_raw: bytes,
    actual_raw: bytes,
    by_path: Mapping[str, Mapping[str, Any]],
    operational: set[str],
) -> None:
    comparison = _strict_document(comparison_raw, label="V6 comparison profile")
    actual = _strict_document(actual_raw, label="V6 actual projection profile")
    _exact_keys(
        comparison,
        {
            "schema",
            "schema_version",
            "profile_key",
            "counter_registry_id",
            "axes",
            "terms",
            "scalar_cost_defined",
            "comparison_profile_id",
        },
        label="V6 comparison profile",
    )
    _exact_keys(
        actual,
        {
            "schema",
            "schema_version",
            "profile_key",
            "counter_registry_id",
            "comparison_profile_id",
            "terms",
            "caller_supplied_actual_comparison_allowed",
            "actual_projection_profile_id",
        },
        label="V6 actual projection profile",
    )
    _rehash(
        comparison,
        id_field="comparison_profile_id",
        domain=V6_COMPARISON_DOMAIN,
        label="V6 comparison profile",
        expected_id=EXPECTED_V6_COMPARISON_ID,
    )
    _rehash(
        actual,
        id_field="actual_projection_profile_id",
        domain=V6_ACTUAL_DOMAIN,
        label="V6 actual projection profile",
        expected_id=EXPECTED_V6_ACTUAL_ID,
    )
    terms = _expected_terms(by_path)
    axes = comparison.get("axes")
    if (
        comparison.get("schema") != "acfqp.comparison_profile.v6"
        or comparison.get("schema_version") != SCHEMA_VERSION
        or comparison.get("profile_key") != "comparison_profile_shared_resources_v6"
        or comparison.get("counter_registry_id") != EXPECTED_V6_REGISTRY_ID
        or comparison.get("scalar_cost_defined") is not False
        or type(axes) is not list
        or tuple(row.get("name") for row in axes if type(row) is dict)
        != _SHARED_AXES
        or comparison.get("terms") != terms
        or len(terms) != 182
        or {row["source_leaf"] for row in terms} != operational
    ):
        _fail("V6 comparison projection is incomplete or changed")
    if (
        actual.get("schema") != "acfqp.actual_projection_profile.v6"
        or actual.get("schema_version") != SCHEMA_VERSION
        or actual.get("profile_key") != "actual_projection_construction_v6"
        or actual.get("counter_registry_id") != EXPECTED_V6_REGISTRY_ID
        or actual.get("comparison_profile_id") != EXPECTED_V6_COMPARISON_ID
        or actual.get("terms") != terms
        or actual.get("caller_supplied_actual_comparison_allowed") is not False
    ):
        _fail("V6 actual projection profile is incomplete or changed")


_BOUNDARY_KEYS = {
    "schema",
    "schema_version",
    "boundary_key",
    "dispatch_key",
    "stage",
    "classification",
    "target_path",
    "registered_owner",
    "reducer",
    "operation_source_module",
    "operation_source_symbol",
    "operation_boundary",
    "cache_semantics",
    "count_rule",
    "failure_rule",
    "replacement_paths",
    "emittable_in_this_fixture",
    "emitter_installed",
    "runtime_evidence_issued",
    "caller_returned_summary_allowed",
    "artifact_cardinality_backfill_allowed",
    "boundary_id",
}


def _expected_cache(path: str) -> str:
    if path in _LEGACY_REPLACEMENTS:
        path = _LEGACY_REPLACEMENTS[path][0]
    if "sequential_exact_likelihood_comparisons" in path or (
        "sequential_interval_log_search_evaluations" in path
    ):
        return "MISS_COMPUTATION_ONLY"
    if path.endswith("confidence_cache_lookups"):
        return "LOOKUP_ATTEMPT"
    if path.endswith("confidence_cache_hits"):
        return "HIT_CLASSIFICATION_ONLY"
    if path.endswith("confidence_cache_misses"):
        return "MISS_CLASSIFICATION_ONLY"
    return "NOT_CACHE_RELATED"


def _verify_boundary_manifest(
    raw: bytes,
    by_path: Mapping[str, Mapping[str, Any]],
    stages: Mapping[str, set[str]],
    v4_required: set[str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    document = _strict_document(raw, label="K7 operation-boundary manifest V3")
    _exact_keys(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "scope_key",
            "registered_topology",
            "registered_context_key",
            "registered_arm",
            "registered_route",
            "registered_terminal_status",
            "v2_manifest_id",
            "counter_registry_id",
            "stage_profile_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "stage_plan",
            "forbidden_unused_stages",
            "legacy_native_zero_forbidden_paths",
            "root_active_v4_owner_matched_paths",
            "open_v4_owner_matched_paths",
            "unmapped_v4_required_paths_by_reason",
            "classification_counts",
            "boundaries",
            "runtime_dispatch_selector",
            "caller_supplied_stage_dispatch_allowed",
            "stage_dispatch_context_must_be_active",
            "emittable_stage_dispatch_pairs_are_unique",
            "native_zero_stage_dispatch_pairs_are_disjoint",
            "v5_leaf_documents_preserved_exactly",
            "all_v5_addition_paths_have_exact_boundary_sites",
            "all_24_root_owner_matched_v4_paths_accounted_for",
            "open_child_promotion_v4_analogues_catalogued",
            "typed_record_replay_has_seven_owner_local_helpers",
            "greedy_allocation_binds_extreme_and_extreme_bounds",
            "zero_addition_break_iteration_is_counted",
            "old_mismatched_paths_deleted",
            "old_mismatched_paths_native_zero_for_this_profile",
            "open_stages_supported_by_v6_registry",
            "open_stages_executed_by_this_fixture",
            "returned_summary_charging_allowed",
            "artifact_cardinality_backfill_allowed",
            "cache_hit_exact_or_log_computation_charged",
            "confidence_cache_access_wrapper_required",
            "confidence_cache_info_before_after_required",
            "confidence_cache_body_entry_marker_required",
            "official_cache_lifecycle",
            "process_global_warm_cache_reuse_allowed",
            "beta_binomial_cache_accounting",
            "beta_binomial_cache_requires_same_cold_isolated_epoch",
            "runtime_emitters_installed",
            "live_operation_event_count",
            "all_site_completeness_claimed",
            "official_execution_allowed",
            "scientific_endpoint_credit_allowed",
            "counter_completeness_gate_passed",
            "workload_economics_gate_passed",
            "manifest_id",
        },
        label="K7 operation-boundary manifest V3",
    )
    _rehash(
        document,
        id_field="manifest_id",
        domain=BOUNDARY_MANIFEST_DOMAIN,
        label="K7 operation-boundary manifest V3",
        expected_id=EXPECTED_BOUNDARY_MANIFEST_ID,
    )
    expected_locks = {
        "v5_leaf_documents_preserved_exactly": True,
        "all_v5_addition_paths_have_exact_boundary_sites": True,
        "all_24_root_owner_matched_v4_paths_accounted_for": True,
        "open_child_promotion_v4_analogues_catalogued": True,
        "typed_record_replay_has_seven_owner_local_helpers": True,
        "greedy_allocation_binds_extreme_and_extreme_bounds": True,
        "zero_addition_break_iteration_is_counted": True,
        "old_mismatched_paths_deleted": False,
        "old_mismatched_paths_native_zero_for_this_profile": True,
        "open_stages_supported_by_v6_registry": True,
        "open_stages_executed_by_this_fixture": False,
        "returned_summary_charging_allowed": False,
        "artifact_cardinality_backfill_allowed": False,
        "cache_hit_exact_or_log_computation_charged": False,
        "caller_supplied_stage_dispatch_allowed": False,
        "stage_dispatch_context_must_be_active": True,
        "emittable_stage_dispatch_pairs_are_unique": True,
        "native_zero_stage_dispatch_pairs_are_disjoint": True,
        "confidence_cache_info_before_after_required": True,
        "confidence_cache_body_entry_marker_required": True,
        "process_global_warm_cache_reuse_allowed": False,
        "beta_binomial_cache_requires_same_cold_isolated_epoch": True,
        "runtime_emitters_installed": False,
        "all_site_completeness_claimed": False,
        "official_execution_allowed": False,
        "scientific_endpoint_credit_allowed": False,
        "counter_completeness_gate_passed": False,
        "workload_economics_gate_passed": False,
    }
    boundaries = document.get("boundaries")
    unmapped = document.get("unmapped_v4_required_paths_by_reason")
    if (
        document.get("schema")
        != "acfqp.v075_k7_root_cap_operation_boundary_manifest.v3"
        or document.get("schema_version") != "3.0.0"
        or document.get("profile_key")
        != "v075_nonfresh_k7_root_cap_operation_boundary_manifest_v3"
        or document.get("scope_key")
        != "NONFRESH_K7_NO_PRIOR_ADAPTIVE_QUOTIENT_ROOT_CAP"
        or document.get("registered_topology") != "K7"
        or document.get("registered_context_key")
        != "heldout_graph_k7_confirmatory_v1"
        or document.get("registered_arm") != "NO_PRIOR"
        or document.get("registered_route") != "ADAPTIVE_QUOTIENT"
        or document.get("registered_terminal_status")
        != "CHILD_ACTION_ROW_CAP_EXCEEDED"
        or document.get("v2_manifest_id") != EXPECTED_V2_MANIFEST_ID
        or document.get("counter_registry_id") != EXPECTED_V6_REGISTRY_ID
        or document.get("stage_profile_id") != EXPECTED_V6_STAGE_ID
        or document.get("comparison_profile_id") != EXPECTED_V6_COMPARISON_ID
        or document.get("actual_projection_profile_id") != EXPECTED_V6_ACTUAL_ID
        or tuple(document.get("stage_plan", ())) != _FIVE_STAGE_PLAN
        or tuple(document.get("forbidden_unused_stages", ())) != _UNUSED_STAGES
        or document.get("legacy_native_zero_forbidden_paths")
        != sorted(_LEGACY_REPLACEMENTS)
        or document.get("root_active_v4_owner_matched_paths")
        != sorted(_ROOT_ACTIVE_V4_PATHS)
        or document.get("open_v4_owner_matched_paths")
        != sorted(_OPEN_V4_PATHS)
        or document.get("classification_counts") != _CLASSIFICATION_COUNTS
        or document.get("runtime_dispatch_selector")
        != ["trusted_active_construction_stage_contextvar", "dispatch_key"]
        or document.get("confidence_cache_access_wrapper_required")
        != "_outer_confidence_bounds_accounted_v2"
        or document.get("official_cache_lifecycle")
        != "ISOLATED_COLD_CACHE_EPOCH_PER_OCCURRENCE_OR_REPLAY"
        or document.get("beta_binomial_cache_accounting")
        != (
            "INTERNAL_TO_ONE_REGISTERED_EXACT_COMPARISON_EVENT_"
            "NO_SEPARATE_V6_CHARGE"
        )
        or document.get("live_operation_event_count") != 0
        or any(document.get(key) is not value for key, value in expected_locks.items())
        or type(boundaries) is not list
        or len(boundaries) != 150
        or type(unmapped) is not dict
        or set(unmapped)
        != {
            "COMMON_SUM_PENDING_HOOK",
            "CAPACITY_PEAK_PENDING_HOOK",
            "DERIVED_ONLY_RECONCILIATION",
            "NATIVE_ZERO_NOT_EXECUTED_OR_OUTSIDE_ROOT_CAP",
        }
    ):
        _fail("K7 boundary manifest identity, cardinality, or locks changed")
    unmapped_sets: dict[str, set[str]] = {}
    for reason, paths in unmapped.items():
        if (
            type(paths) is not list
            or paths != sorted(set(paths))
            or any(path not in v4_required for path in paths)
        ):
            _fail("unmapped V4 path partition is malformed")
        unmapped_sets[reason] = set(paths)
    if any(
        left < right and bool(unmapped_sets[left] & unmapped_sets[right])
        for left in unmapped_sets
        for right in unmapped_sets
    ):
        _fail("unmapped V4 reason buckets overlap")
    by_key: dict[str, dict[str, Any]] = {}
    counts = {key: 0 for key in _CLASSIFICATION_COUNTS}
    path_counts: dict[str, int] = {}
    ids: set[str] = set()
    emittable_dispatch_pairs: list[tuple[str, str]] = []
    native_zero_dispatch_pairs: set[tuple[str, str]] = set()
    source_by_dispatch: dict[str, tuple[str, str, str, str]] = {}
    for boundary in boundaries:
        _exact_keys(boundary, _BOUNDARY_KEYS, label="K7 operation boundary")
        boundary_id = _rehash(
            boundary,
            id_field="boundary_id",
            domain=BOUNDARY_DOMAIN,
            label="K7 operation boundary",
        )
        key = boundary["boundary_key"]
        dispatch_key = boundary["dispatch_key"]
        path = boundary["target_path"]
        stage = boundary["stage"]
        classification = boundary["classification"]
        replacements = boundary["replacement_paths"]
        if (
            type(key) is not str
            or key in by_key
            or type(dispatch_key) is not str
            or _IDENTIFIER.fullmatch(dispatch_key) is None
            or boundary_id in ids
            or path not in by_path
            or stage not in stages
            or path not in stages[stage]
            or classification not in counts
            or boundary["registered_owner"] != by_path[path]["owner"]
            or boundary["reducer"] != by_path[path]["reducer"]
            or boundary["cache_semantics"] != _expected_cache(path)
            or boundary["emitter_installed"] is not False
            or boundary["runtime_evidence_issued"] is not False
            or boundary["caller_returned_summary_allowed"] is not False
            or boundary["artifact_cardinality_backfill_allowed"] is not False
            or type(replacements) is not list
            or replacements != sorted(set(replacements))
        ):
            _fail("K7 operation boundary path, owner, stage, or cache rule changed")
        source_owner = boundary["operation_source_module"].rsplit(".", 1)[-1]
        expected_replacements = list(_LEGACY_REPLACEMENTS.get(path, ()))
        legacy = classification.startswith("LEGACY_")
        if key.startswith("v6."):
            expected_classification = (
                "OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO"
                if stage in _UNUSED_STAGES
                else (
                    "V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY"
                    if by_path[path]["lane"] == "diagnostic"
                    else "V6_NATIVE_BOUNDARY_SCHEMA_ONLY"
                )
            )
        elif key.startswith("v5."):
            expected_classification = (
                "V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY"
            )
        elif key.startswith("v4-owner."):
            expected_classification = (
                "OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO"
                if stage in _UNUSED_STAGES
                else "V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY"
            )
        elif key.startswith("legacy-zero."):
            expected_classification = (
                "LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN"
                if path.endswith("signed_batches")
                else "LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN"
            )
        else:
            _fail("K7 operation boundary has an unknown key family")
        if classification != expected_classification:
            _fail("K7 per-boundary classification changed")
        if legacy:
            if replacements != expected_replacements or any(
                by_path[replacement]["owner"] != source_owner
                for replacement in replacements
            ):
                _fail("legacy boundary replacement set or primitive owner changed")
            semantic_split = path.endswith("signed_batches")
            if semantic_split != (
                classification
                == "LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN"
            ):
                _fail("legacy semantic-split classification changed")
            if semantic_split != (source_owner == boundary["registered_owner"]):
                _fail("legacy mismatch owner relation changed")
        elif replacements or source_owner != boundary["registered_owner"]:
            _fail("native boundary is not owned by its primitive source")
        outside = classification == "OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO"
        if outside and stage not in _UNUSED_STAGES:
            _fail("outside-fixture native-zero stage rule changed")
        if stage in _UNUSED_STAGES and not outside and not legacy:
            _fail("unused stage contains an emittable fixture boundary")
        emittable = classification in _LIVE_EVENT_CLASSIFICATIONS
        if boundary["emittable_in_this_fixture"] is not emittable:
            _fail("boundary emittable classification lock changed")
        pair = (stage, dispatch_key)
        source_signature = (
            boundary["operation_source_module"],
            boundary["operation_source_symbol"],
            boundary["operation_boundary"],
            boundary["cache_semantics"],
        )
        existing_source = source_by_dispatch.setdefault(
            dispatch_key, source_signature
        )
        if existing_source != source_signature:
            _fail("one dispatch key names multiple primitive boundaries")
        if emittable:
            emittable_dispatch_pairs.append(pair)
        else:
            native_zero_dispatch_pairs.add(pair)
        if any(
            type(boundary.get(name)) is not str or not boundary[name]
            for name in (
                "operation_source_module",
                "operation_source_symbol",
                "operation_boundary",
                "count_rule",
                "failure_rule",
            )
        ):
            _fail("operation boundary source or event rule is malformed")
        by_key[key] = boundary
        ids.add(boundary_id)
        counts[classification] += 1
        path_counts[path] = path_counts.get(path, 0) + 1
    if [row["boundary_key"] for row in boundaries] != sorted(by_key):
        _fail("K7 operation boundaries are reordered")
    if counts != _CLASSIFICATION_COUNTS:
        _fail("K7 operation-boundary classification counts changed")
    if (
        len(set(emittable_dispatch_pairs)) != len(emittable_dispatch_pairs)
        or bool(set(emittable_dispatch_pairs) & native_zero_dispatch_pairs)
    ):
        _fail("K7 stage-dispatch pairs are ambiguous or cross-classified")
    for prefix in ("build.initial", "build.open_checkpoint", "closure.reconciliation"):
        if (
            path_counts.get(f"{prefix}_batch_v2_typed_record_replays") != 7
            or path_counts.get(
                f"{prefix}_batch_v2_interval_greedy_allocation_steps"
            )
            != 2
            or path_counts.get(f"{prefix}_batch_v2_policy_order_comparisons")
            != 2
            or path_counts.get(
                f"{prefix}_sequential_interval_log_search_evaluations"
            )
            != 2
        ):
            _fail("K7 multisite boundary cardinality changed")
    if not set(_ADDITIONS) <= set(path_counts) or not set(
        _LEGACY_REPLACEMENTS
    ) <= set(path_counts):
        _fail("K7 V6 or legacy boundary coverage is incomplete")
    represented_v4 = set(path_counts) & v4_required
    expected_represented_v4 = (
        _ROOT_ACTIVE_V4_PATHS
        | _OPEN_V4_PATHS
        | set(_LEGACY_REPLACEMENTS)
    )
    unmapped_union = set().union(*unmapped_sets.values())
    derived_v4 = {
        path for path in v4_required if by_path[path]["lane"] == "derived_only"
    }
    expected_native_zero = v4_required - (
        represented_v4
        | _V4_COMMON_PENDING
        | _V4_CAPACITY_PENDING
        | derived_v4
    )
    if (
        represented_v4 != expected_represented_v4
        or any(path_counts[path] != 1 for path in represented_v4)
        or bool(represented_v4 & unmapped_union)
        or represented_v4 | unmapped_union != v4_required
        or unmapped_sets["COMMON_SUM_PENDING_HOOK"] != _V4_COMMON_PENDING
        or unmapped_sets["CAPACITY_PEAK_PENDING_HOOK"]
        != _V4_CAPACITY_PENDING
        or unmapped_sets["DERIVED_ONLY_RECONCILIATION"] != derived_v4
        or unmapped_sets["NATIVE_ZERO_NOT_EXECUTED_OR_OUTSIDE_ROOT_CAP"]
        != expected_native_zero
    ):
        _fail("V4 required-path accounting partition changed or is incomplete")
    return document, by_key


_UNAVAILABLE = {
    "kind": "NOT_AVAILABLE_INCOMPLETE_SITE_COVERAGE",
    "reason": (
        "operation-site coverage is incomplete; absent native work is unknown"
    ),
}
_NA_KIND = "NOT_APPLICABLE"


def _typed_na(value: Any, reason: str) -> bool:
    return type(value) is dict and value == {"kind": _NA_KIND, "reason": reason}


_COMMON_NODE_KEYS = {
    "occurrence_start_id",
    "occurrence_id",
    "counter_registry_id",
    "stage_profile_id",
    "boundary_profile_id",
    "chain_sequence",
    "predecessor_chain_id",
}


def _verify_partial_transcript(
    raw: bytes,
    boundaries: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str, int]:
    document = _strict_document(raw, label="partial-native transcript")
    _exact_keys(
        document,
        {
            "schema",
            "schema_version",
            "occurrence_start",
            "chain_nodes",
            "terminal_kind",
            "occurrence_completion_id",
            "occurrence_abort_id",
            "counter_records",
            "work_vector",
            "comparison_vector",
            "actual_projection",
            "coverage_state",
            "absent_native_events_inferred_zero",
            "official_execution_allowed",
            "partial_native_transcript_id",
        },
        label="partial-native transcript",
    )
    transcript_id = _rehash(
        document,
        id_field="partial_native_transcript_id",
        domain=TRANSCRIPT_DOMAIN,
        label="partial-native transcript",
    )
    if (
        document.get("schema")
        != "acfqp.construction_partial_native_occurrence_transcript.v1"
        or document.get("schema_version") != "1.0.0"
        or document.get("coverage_state") != "PARTIAL_NATIVE_ONLY"
        or document.get("absent_native_events_inferred_zero") is not False
        or document.get("official_execution_allowed") is not False
        or any(
            document.get(field) != _UNAVAILABLE
            for field in (
                "counter_records",
                "work_vector",
                "comparison_vector",
                "actual_projection",
            )
        )
    ):
        _fail("partial-native transcript accounting locks changed")
    start = _exact_keys(
        document.get("occurrence_start"),
        {
            "schema",
            "schema_version",
            "occurrence_id",
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
            "recorder_id",
            "stage_plan",
            "predecessor_chain_id",
            "chain_sequence",
            "coverage_state",
            "occurrence_start_id",
        },
        label="partial-native occurrence start",
    )
    start_id = _rehash(
        start,
        id_field="occurrence_start_id",
        domain=TRANSCRIPT_START_DOMAIN,
        label="partial-native occurrence start",
    )
    occurrence_id = start.get("occurrence_id")
    try:
        parse_content_id(occurrence_id)
    except ValueError as error:
        raise V075ConstructionAccountingOperationBoundaryIndependentV6Violation(
            "partial-native occurrence identity is malformed"
        ) from error
    if (
        start.get("schema")
        != "acfqp.construction_partial_native_occurrence_start.v1"
        or start.get("schema_version") != "1.0.0"
        or start.get("counter_registry_id") != EXPECTED_V6_REGISTRY_ID
        or start.get("stage_profile_id") != EXPECTED_V6_STAGE_ID
        or start.get("boundary_profile_id") != EXPECTED_BOUNDARY_MANIFEST_ID
        or type(start.get("recorder_id")) is not str
        or _IDENTIFIER.fullmatch(start["recorder_id"]) is None
        or tuple(start.get("stage_plan", ())) != _FIVE_STAGE_PLAN
        or not _typed_na(start.get("predecessor_chain_id"), "CHAIN_GENESIS")
        or start.get("chain_sequence") != 0
        or start.get("coverage_state") != "PARTIAL_NATIVE_ONLY"
    ):
        _fail("partial-native occurrence-start identity or plan changed")

    nodes = document.get("chain_nodes")
    if type(nodes) is not list or not nodes:
        _fail("partial-native transcript has no terminal chain")
    predecessor = start_id
    active_stage: str | None = None
    completed = 0
    stage_events = 0
    total_events = 0
    event_ids: list[str] = []
    terminal_seen = False
    terminal_id = ""
    for sequence, node_value in enumerate(nodes, 1):
        if type(node_value) is not dict:
            _fail("partial-native chain node is not an object")
        schema = node_value.get("schema")
        definitions = {
            "acfqp.construction_partial_native_stage_start.v1": (
                TRANSCRIPT_STAGE_START_DOMAIN,
                "stage_start_id",
                _COMMON_NODE_KEYS
                | {"schema", "schema_version", "stage_index", "stage_kind"},
            ),
            "acfqp.construction_partial_native_operation_event.v1": (
                TRANSCRIPT_EVENT_DOMAIN,
                "operation_event_id",
                _COMMON_NODE_KEYS
                | {
                    "schema",
                    "schema_version",
                    "stage_index",
                    "stage_kind",
                    "stage_event_sequence",
                    "site_id",
                    "path",
                    "reducer",
                    "amount",
                },
            ),
            "acfqp.construction_partial_native_stage_completion.v1": (
                TRANSCRIPT_STAGE_COMPLETION_DOMAIN,
                "stage_completion_id",
                _COMMON_NODE_KEYS
                | {
                    "schema",
                    "schema_version",
                    "stage_index",
                    "stage_kind",
                    "stage_event_count",
                    "total_event_count",
                    "output_bindings",
                },
            ),
            "acfqp.construction_partial_native_occurrence_completion.v1": (
                TRANSCRIPT_COMPLETION_DOMAIN,
                "occurrence_completion_id",
                _COMMON_NODE_KEYS
                | {
                    "schema",
                    "schema_version",
                    "completed_stage_count",
                    "total_event_count",
                    "emitted_event_ids",
                },
            ),
            "acfqp.construction_partial_native_occurrence_abort.v1": (
                TRANSCRIPT_ABORT_DOMAIN,
                "occurrence_abort_id",
                _COMMON_NODE_KEYS
                | {
                    "schema",
                    "schema_version",
                    "completed_stage_count",
                    "total_event_count",
                    "emitted_event_ids",
                    "aborted_stage_index",
                    "aborted_stage_kind",
                    "exception_module",
                    "exception_qualname",
                    "reason",
                },
            ),
        }
        if schema not in definitions:
            _fail("partial-native chain node schema is unknown")
        domain, id_field, keys = definitions[schema]
        _exact_keys(node_value, keys | {id_field}, label="partial-native chain node")
        node_id = _rehash(
            node_value,
            id_field=id_field,
            domain=domain,
            label="partial-native chain node",
        )
        if terminal_seen:
            _fail("partial-native terminal node is not final")
        if (
            node_value.get("schema_version") != "1.0.0"
            or node_value.get("chain_sequence") != sequence
            or node_value.get("predecessor_chain_id") != predecessor
            or node_value.get("occurrence_start_id") != start_id
            or node_value.get("occurrence_id") != occurrence_id
            or node_value.get("counter_registry_id") != EXPECTED_V6_REGISTRY_ID
            or node_value.get("stage_profile_id") != EXPECTED_V6_STAGE_ID
            or node_value.get("boundary_profile_id")
            != EXPECTED_BOUNDARY_MANIFEST_ID
        ):
            _fail("partial-native chain is reordered or cross-identity")
        if schema.endswith("stage_start.v1"):
            expected_stage = _FIVE_STAGE_PLAN[completed] if completed < 5 else None
            if (
                active_stage is not None
                or node_value.get("stage_index") != completed + 1
                or node_value.get("stage_kind") != expected_stage
            ):
                _fail("partial-native stage start violates the exact lifecycle")
            active_stage = expected_stage
            stage_events = 0
        elif schema.endswith("operation_event.v1"):
            site = node_value.get("site_id")
            boundary = boundaries.get(site)
            if (
                active_stage is None
                or node_value.get("stage_index") != completed + 1
                or node_value.get("stage_kind") != active_stage
                or node_value.get("stage_event_sequence") != stage_events + 1
                or boundary is None
                or boundary["classification"] not in _LIVE_EVENT_CLASSIFICATIONS
                or boundary["stage"] != active_stage
                or boundary["target_path"] != node_value.get("path")
                or boundary["reducer"] != node_value.get("reducer")
                or node_value.get("reducer") != "sum"
                or type(node_value.get("amount")) is not int
                or node_value["amount"] <= 0
            ):
                _fail(
                    "partial-native operation site, stage, reducer, or "
                    "amount changed"
                )
            stage_events += 1
            total_events += 1
            event_ids.append(node_id)
        elif schema.endswith("stage_completion.v1"):
            outputs = node_value.get("output_bindings")
            if type(outputs) is not list:
                _fail("partial-native stage outputs are malformed")
            output_pairs = []
            for output in outputs:
                _exact_keys(
                    output,
                    {"role", "artifact_id"},
                    label="partial-native stage output",
                )
                try:
                    parse_content_id(output["artifact_id"])
                except (KeyError, ValueError) as error:
                    raise _Violation(
                        "partial-native output artifact identity is malformed"
                    ) from error
                if (
                    type(output.get("role")) is not str
                    or _IDENTIFIER.fullmatch(output["role"]) is None
                ):
                    _fail("partial-native output role is malformed")
                output_pairs.append((output["role"], output["artifact_id"]))
            if (
                active_stage is None
                or node_value.get("stage_index") != completed + 1
                or node_value.get("stage_kind") != active_stage
                or node_value.get("stage_event_count") != stage_events
                or node_value.get("total_event_count") != total_events
                or output_pairs != sorted(set(output_pairs))
                or len({role for role, _artifact_id in output_pairs})
                != len(output_pairs)
            ):
                _fail("partial-native stage completion does not replay its stage")
            completed += 1
            active_stage = None
            stage_events = 0
        elif schema.endswith("occurrence_completion.v1"):
            if (
                active_stage is not None
                or completed != 5
                or node_value.get("completed_stage_count") != 5
                or node_value.get("total_event_count") != total_events
                or node_value.get("emitted_event_ids") != event_ids
            ):
                _fail("partial-native completion precedes exact stage closure")
            terminal_seen = True
            terminal_id = node_id
            if (
                document.get("terminal_kind") != "COMPLETED"
                or document.get("occurrence_completion_id") != node_id
                or not _typed_na(
                    document.get("occurrence_abort_id"),
                    "OCCURRENCE_COMPLETED_WITHOUT_ABORT",
                )
            ):
                _fail("partial-native completion typed terminal binding changed")
        elif schema.endswith("occurrence_abort.v1"):
            if (
                node_value.get("completed_stage_count") != completed
                or node_value.get("total_event_count") != total_events
                or node_value.get("emitted_event_ids") != event_ids
                or type(node_value.get("reason")) is not str
                or _IDENTIFIER.fullmatch(node_value["reason"]) is None
            ):
                _fail("partial-native abort does not preserve exact progress")
            if active_stage is None:
                if not (
                    _typed_na(
                        node_value.get("aborted_stage_index"),
                        "NO_ACTIVE_STAGE_AT_ABORT",
                    )
                    and _typed_na(
                        node_value.get("aborted_stage_kind"),
                        "NO_ACTIVE_STAGE_AT_ABORT",
                    )
                ):
                    _fail("between-stage abort lacks typed-null stage fields")
            elif (
                node_value.get("aborted_stage_index") != completed + 1
                or node_value.get("aborted_stage_kind") != active_stage
            ):
                _fail("active-stage abort identity changed")
            module = node_value.get("exception_module")
            qualname = node_value.get("exception_qualname")
            typed_exception = any(
                _typed_na(module, reason) and _typed_na(qualname, reason)
                for reason in (
                    "NO_EXCEPTION_TYPE",
                    "UNREPRESENTABLE_EXCEPTION_TYPE",
                )
            )
            concrete_exception = (
                type(module) is str
                and type(qualname) is str
                and 0 < len(module) <= 512
                and 0 < len(qualname) <= 512
                and all(33 <= ord(character) <= 126 for character in module)
                and all(
                    33 <= ord(character) <= 126 for character in qualname
                )
            )
            if not (typed_exception or concrete_exception):
                _fail("partial-native abort exception binding changed")
            terminal_seen = True
            terminal_id = node_id
            if (
                document.get("terminal_kind") != "ABORTED"
                or document.get("occurrence_abort_id") != node_id
                or not _typed_na(
                    document.get("occurrence_completion_id"),
                    "OCCURRENCE_ABORTED_WITHOUT_COMPLETION",
                )
            ):
                _fail("partial-native abort typed terminal binding changed")
        predecessor = node_id
    if not terminal_seen or terminal_id != predecessor:
        _fail("partial-native transcript lacks a final terminal node")
    return transcript_id, occurrence_id, total_events


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionAccountingOperationBoundaryIndependentVerificationV6:
    _issuer: InitVar[object]
    v5_registry_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundary_manifest_id: str
    operation_boundary_count: int
    partial_native_transcript_id: str
    occurrence_id: str
    partial_native_event_count: int
    bundle_sha256: str
    bundle_byte_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value in (
            self.v5_registry_id,
            self.counter_registry_id,
            self.stage_profile_id,
            self.comparison_profile_id,
            self.actual_projection_profile_id,
            self.boundary_manifest_id,
            self.partial_native_transcript_id,
            self.occurrence_id,
            self.bundle_sha256,
        ):
            parse_content_id(value)
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.operation_boundary_count) is not int
            or self.operation_boundary_count <= 0
            or type(self.partial_native_event_count) is not int
            or self.partial_native_event_count < 0
            or type(self.bundle_byte_count) is not int
            or self.bundle_byte_count <= 0
        ):
            _fail("independent V6 verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_accounting_operation_boundary_"
                "independent_verification.v6"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "v5_registry_id": self.v5_registry_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "operation_boundary_count": self.operation_boundary_count,
            "partial_native_transcript_id": self.partial_native_transcript_id,
            "occurrence_id": self.occurrence_id,
            "partial_native_event_count": self.partial_native_event_count,
            "bundle_sha256": self.bundle_sha256,
            "bundle_byte_count": self.bundle_byte_count,
            "producer_modules_imported": False,
            "v5_leaf_documents_replayed_from_canonical_bytes": True,
            "v6_fifty_eight_additions_reconstructed_independently": True,
            "v6_stage_routing_replayed_independently": True,
            "v6_projection_182_terms_replayed_independently": True,
            "v4_117_required_paths_partitioned_independently": True,
            "v4_20_owner_matched_boundaries_verified": True,
            "unmapped_v4_reason_buckets_verified": True,
            "all_operation_boundary_ids_rehashed_independently": True,
            "boundary_path_owner_stage_replacement_cache_rules_replayed": True,
            "partial_native_hash_chain_replayed_independently": True,
            "partial_native_accounting_outputs_typed_unavailable": True,
            "partial_native_absence_inferred_zero": False,
            "partial_native_is_live_accounting_evidence": False,
            "counter_record_count": 0,
            "work_vector_count": 0,
            "comparison_vector_count": 0,
            "actual_projection_proof_count": 0,
            "runtime_operation_emitters_complete": False,
            "runtime_owner_match_verified": False,
            "runtime_stage_attribution_verified": False,
            "all_site_completeness_claimed": False,
            "production_authorizing": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": "NOT_RUN",
            "workload_economics_gate_status": "NOT_RUN",
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("independent V6 verifications are in-memory-only")


def verify_v075_construction_accounting_operation_boundary_bundle_v6(
    *,
    v5_counter_registry_bytes: bytes,
    counter_registry_bytes: bytes,
    stage_profile_bytes: bytes,
    comparison_profile_bytes: bytes,
    actual_projection_profile_bytes: bytes,
    boundary_manifest_bytes: bytes,
    partial_native_transcript_bytes: bytes,
) -> V075ConstructionAccountingOperationBoundaryIndependentVerificationV6:
    """Independently replay one schema bundle and one partial transcript."""

    try:
        v5 = _verify_v5_registry(v5_counter_registry_bytes)
        registry, by_path, operational, v4_required = _verify_registry(
            counter_registry_bytes, v5
        )
        stages = _verify_stage(stage_profile_bytes, by_path)
        _verify_projections(
            comparison_profile_bytes,
            actual_projection_profile_bytes,
            by_path,
            operational,
        )
        manifest, boundaries = _verify_boundary_manifest(
            boundary_manifest_bytes, by_path, stages, v4_required
        )
        transcript_id, occurrence_id, event_count = _verify_partial_transcript(
            partial_native_transcript_bytes, boundaries
        )
        bundle_parts = (
            v5_counter_registry_bytes,
            counter_registry_bytes,
            stage_profile_bytes,
            comparison_profile_bytes,
            actual_projection_profile_bytes,
            boundary_manifest_bytes,
            partial_native_transcript_bytes,
        )
        bundle_bytes = b"".join(
            len(part).to_bytes(8, "big") + part for part in bundle_parts
        )
        return V075ConstructionAccountingOperationBoundaryIndependentVerificationV6(
            _VERIFICATION_ISSUER,
            v5["counter_registry_id"],
            registry["counter_registry_id"],
            EXPECTED_V6_STAGE_ID,
            EXPECTED_V6_COMPARISON_ID,
            EXPECTED_V6_ACTUAL_ID,
            manifest["manifest_id"],
            len(boundaries),
            transcript_id,
            occurrence_id,
            event_count,
            hashlib.sha256(bundle_bytes).hexdigest(),
            len(bundle_bytes),
        )
    except V075ConstructionAccountingOperationBoundaryIndependentV6Violation:
        raise
    except Exception:
        raise V075ConstructionAccountingOperationBoundaryIndependentV6Violation(
            "independent V6 operation-boundary bundle replay mismatch"
        ) from None


__all__ = [
    "EXPECTED_BOUNDARY_MANIFEST_ID",
    "EXPECTED_V5_REGISTRY_ID",
    "EXPECTED_V6_ACTUAL_ID",
    "EXPECTED_V6_COMPARISON_ID",
    "EXPECTED_V6_REGISTRY_ID",
    "EXPECTED_V6_STAGE_ID",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "V075ConstructionAccountingOperationBoundaryIndependentV6Violation",
    "V075ConstructionAccountingOperationBoundaryIndependentVerificationV6",
    "VERIFICATION_DOMAIN",
    "verify_v075_construction_accounting_operation_boundary_bundle_v6",
]
