"""Independent verifier for the contract-1.86 accounting successor.

This module does not import the v3 construction-accounting core or its
producer authority.  It first executes the exact contract-1.85 independent
verifier, reuses only the independently verified v2/foundation bytes, then
re-hashes and validates every embedded v3 profile and the outer closure.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V3_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V3_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V3_DOMAIN,
    CONSTRUCTION_LEGACY_MIGRATION_PROFILE_V3_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V3_DOMAIN,
    V075_CONSTRUCTION_ACCOUNTING_REGISTRY_SUCCESSOR_V3_DOMAIN,
    V075_CONSTRUCTION_ACCOUNTING_REGISTRY_SUCCESSOR_VERIFICATION_V3_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp import (
    v075_construction_accounting_schema_independent_verifier_v2
    as upstream_verifier,
)


SCHEMA_VERSION = "3.0.0"
PROPOSED_CONTRACT_VERSION = "1.86.0"
PROFILE_KEY = (
    "v075_construction_accounting_registry_successor_"
    "independent_verifier_v3"
)
PRODUCER_PROFILE_KEY = "v075_construction_accounting_registry_successor_v3"
UPSTREAM_PROFILE_KEY = (
    "v075_construction_accounting_schema_independent_verifier_v2"
)
MAX_BYTES = 64 * 1024 * 1024

EXPECTED_COUNTER_REGISTRY_V3_ID = (
    "09e48ea7f3c666de5e58bcb024e074cd"
    "887739daff598a4bf13c2e8a1a5e552e"
)
EXPECTED_STAGE_PROFILE_V3_ID = (
    "d7f04727e9742047df2baadeb721675d"
    "2b59ad9464977af457eb6472b58fd5a6"
)
EXPECTED_COMPARISON_PROFILE_V3_ID = (
    "cb0cd03d6ea5b45b79a66f6f057ed278"
    "fe21431caf05fc1f4430f4cb8b2e11b2"
)
EXPECTED_ACTUAL_PROJECTION_PROFILE_V3_ID = (
    "1b04b5f148fc8bb173a1482d7e420709"
    "7c1c7e0c54e6398c366163253f139266"
)
EXPECTED_LEGACY_MIGRATION_PROFILE_V3_ID = (
    "dc8e34ec371195d60f20ee928228555b"
    "0b35164745a6bec3b5ecae3d749006ab"
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
_DISPOSITION_COUNTS = {
    "DECOMPOSE_AT_NATIVE_SITES": 18,
    "DERIVE_OR_DIAGNOSE_FROM_PRIMITIVES": 51,
    "REGISTER_NEW_OPERATIONAL_FAMILY": 11,
    "REINSTRUMENT_EXISTING_FAMILY": 7,
}
_NEW_OPERATIONAL = frozenset(
    {
        "adaptive.cells_compiled",
        "adaptive.concretizer_ground_actions",
        "adaptive.semantic_actions_compiled",
        "common.confidence_event_evaluations",
        "common.deterministic_tie_breaks",
        "common.dominance_comparisons",
        "common.exact_likelihood_comparisons",
        "common.interval_lp_allocations",
        "common.outcome_projections",
        "discovery.child_catalogues",
        "source.proposal_entries_bound",
    }
)
_REINSTRUMENT = frozenset(
    {
        "common.accepted_draws_consumed",
        "common.interval_row_evaluations",
        "common.log_search_evaluations",
        "common.policy_assignments_evaluated",
        "common.signed_batches_retained",
        "common.statistical_rows_built",
        "support.rows_frozen",
    }
)
_DECOMPOSE = frozenset(
    {
        "common.aggregate_support_evidence_verified",
        "common.capability_attestation_verifications",
        "common.capability_refs_consumed",
        "common.learned_support_graph_checks",
        "common.open_lifecycle_checks",
        "common.pre_sampling_identity_checks",
        "common.public_batch_verifications",
        "common.request_bytes_read",
        "common.request_checks",
        "common.request_reconstructions",
        "common.schedule_checks",
        "common.sequence_verifications",
        "common.total_lift_authority_bindings",
        "integrity.no_persistence_checks",
        "planning.checkpoints_evaluated",
        "source.adapter_payload_reads",
        "source_prior.adapter_reads",
        "source_prior.read_bytes",
    }
)

_REPLAY_MISMATCH = (
    "independent contract-1.86 accounting successor replay mismatch"
)
_VERIFICATION_ISSUER = object()


class V075ConstructionAccountingSuccessorIndependentV3Violation(ValueError):
    """Upstream replay, embedded profile, partition, or closure is invalid."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionAccountingSuccessorIndependentV3Violation(message)


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        _fail(f"{label} bytes are absent or exceed the cap")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionAccountingSuccessorIndependentV3Violation(
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
) -> str:
    if type(document) is not dict or id_field not in document:
        _fail(f"{label} is not one complete object")
    payload = dict(document)
    claimed = payload.pop(id_field)
    try:
        actual = content_id(domain, payload)
    except (TypeError, ValueError) as error:
        raise V075ConstructionAccountingSuccessorIndependentV3Violation(
            f"{label} cannot be canonically re-hashed"
        ) from error
    if claimed != actual or actual != expected_id:
        _fail(f"{label} identity changed")
    return actual


def _verified_legacy_paths(
    foundation: Mapping[str, Any],
) -> tuple[set[str], dict[str, set[str]]]:
    coverage = foundation.get("coverage_matrix")
    rows = coverage.get("rows") if type(coverage) is dict else None
    if type(rows) is not list:
        _fail("verified foundation coverage rows are absent")
    by_path: dict[str, set[str]] = {}
    entry_count = 0
    for row in rows:
        if (
            type(row) is dict
            and row.get("legacy_custom_counter") is True
        ):
            if (
                row.get("classification") != "NOT_INSTRUMENTED"
                or row.get("target_path") is not None
                or type(row.get("source_path")) is not str
                or type(row.get("source_family")) is not str
            ):
                _fail("verified legacy coverage row changed")
            entry_count += 1
            by_path.setdefault(row["source_path"], set()).add(
                row["source_family"]
            )
    if entry_count != 95 or len(by_path) != 87:
        _fail("verified legacy catalogue cardinality changed")
    return set(by_path), by_path


def _verify_registry(
    registry: Mapping[str, Any],
    upstream_schema: Mapping[str, Any],
) -> tuple[set[str], set[str]]:
    _rehash_embedded(
        registry,
        id_field="counter_registry_id",
        domain=CONSTRUCTION_COUNTER_REGISTRY_V3_DOMAIN,
        expected_id=EXPECTED_COUNTER_REGISTRY_V3_ID,
        label="v3 counter registry",
    )
    leaves = registry.get("leaves")
    upstream_registry = upstream_schema.get("counter_registry")
    upstream_leaves = (
        upstream_registry.get("leaves")
        if type(upstream_registry) is dict
        else None
    )
    if (
        registry.get("schema") != "acfqp.counter_registry.v3"
        or registry.get("schema_version") != SCHEMA_VERSION
        or registry.get("counter_registry_key")
        != "acfqp_counter_registry_v3"
        or registry.get("v2_registry_id")
        != upstream_schema.get("counter_registry_id")
        or registry.get("v2_prefix_preserved_exactly") is not True
        or type(leaves) is not list
        or len(leaves) != 116
        or type(upstream_leaves) is not list
        or len(upstream_leaves) != 69
    ):
        _fail("v3 registry shape or v2 binding changed")
    by_path: dict[str, dict[str, Any]] = {}
    for row in leaves:
        if (
            type(row) is not dict
            or type(row.get("path")) is not str
            or row["path"] in by_path
        ):
            _fail("v3 registry leaf is malformed or duplicated")
        by_path[row["path"]] = row
    if list(by_path) != sorted(by_path):
        _fail("v3 registry leaves are not path-sorted")
    upstream_by_path = {row["path"]: row for row in upstream_leaves}
    if any(by_path[path] != row for path, row in upstream_by_path.items()):
        _fail("v3 registry mutated one v2 leaf")
    additions = set(by_path) - set(upstream_by_path)
    if len(additions) != 47:
        _fail("v3 additive path count changed")
    operational = {
        path
        for path, row in by_path.items()
        if row.get("lane") == "operational"
    }
    required = {
        path for path, row in by_path.items() if row.get("required") is True
    }
    if len(operational) != 99 or len(required) != 109:
        _fail("v3 operational/required cardinality changed")
    if (
        "audit.failed_child_catalogues_built" not in additions
        or not {
            "acquisition.incremental_observer_accepted_draws",
            "build.open_checkpoint_dominance_comparisons",
        }
        <= additions
    ):
        _fail("v3 critical additive paths are absent")
    for path in operational:
        row = by_path[path]
        if (
            row.get("required") is not True
            or row.get("reducer") not in {"sum", "max"}
            or row.get("comparison_axis") not in _SHARED_AXES
        ):
            _fail("v3 operational metadata is incomplete")
    return set(by_path), operational


def _verify_stage(
    stage: Mapping[str, Any],
    known_paths: set[str],
) -> None:
    _rehash_embedded(
        stage,
        id_field="stage_profile_id",
        domain=CONSTRUCTION_STAGE_PROFILE_V3_DOMAIN,
        expected_id=EXPECTED_STAGE_PROFILE_V3_ID,
        label="v3 stage profile",
    )
    rules = stage.get("rules")
    if (
        stage.get("schema")
        != "acfqp.construction_stage_profile.v3"
        or stage.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V3_ID
        or stage.get(
            "initial_build_owns_root_epoch_compile_and_plan"
        )
        is not True
        or stage.get(
            "failed_abstract_prefix_owns_verified_child_audit_only"
        )
        is not True
        or stage.get(
            "interval_row_path_uses_registered_row_behavior_unit"
        )
        is not True
        or type(rules) is not list
        or len(rules) != 10
    ):
        _fail("v3 stage profile shape changed")
    by_stage: dict[str, set[str]] = {}
    for row in rules:
        if (
            type(row) is not dict
            or set(row)
            != {"stage_kind", "allowed_nonzero_paths"}
            or type(row["stage_kind"]) is not str
            or type(row["allowed_nonzero_paths"]) is not list
            or row["stage_kind"] in by_stage
            or row["allowed_nonzero_paths"]
            != sorted(set(row["allowed_nonzero_paths"]))
        ):
            _fail("v3 stage rule is malformed")
        by_stage[row["stage_kind"]] = set(
            row["allowed_nonzero_paths"]
        )
    if tuple(sorted(by_stage)) != _STAGES:
        _fail("v3 stage set changed")
    if any(not paths <= known_paths for paths in by_stage.values()):
        _fail("v3 stage rule references an unknown path")
    if (
        "acquisition.incremental_observer_accepted_draws"
        not in by_stage["OPEN_INCREMENTAL_ACQUISITION"]
        or "build.open_checkpoint_dominance_comparisons"
        not in by_stage["OPEN_CHECKPOINT_REPLANNING"]
        or "audit.failed_child_catalogues_built"
        not in by_stage["FAILED_ABSTRACT_PREFIX"]
        or "audit.failed_child_catalogues_built"
        in by_stage["INITIAL_ACQUISITION"]
    ):
        _fail("v3 stage ownership changed")


def _verify_projection(
    comparison: Mapping[str, Any],
    actual: Mapping[str, Any],
    operational: set[str],
) -> None:
    _rehash_embedded(
        comparison,
        id_field="comparison_profile_id",
        domain=CONSTRUCTION_COMPARISON_PROFILE_V3_DOMAIN,
        expected_id=EXPECTED_COMPARISON_PROFILE_V3_ID,
        label="v3 comparison profile",
    )
    _rehash_embedded(
        actual,
        id_field="actual_projection_profile_id",
        domain=CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V3_DOMAIN,
        expected_id=EXPECTED_ACTUAL_PROJECTION_PROFILE_V3_ID,
        label="v3 actual projection profile",
    )
    axes = comparison.get("axes")
    terms = comparison.get("terms")
    actual_terms = actual.get("terms")
    if (
        comparison.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V3_ID
        or comparison.get("scalar_cost_defined") is not False
        or type(axes) is not list
        or tuple(row.get("name") for row in axes if type(row) is dict)
        != _SHARED_AXES
        or type(terms) is not list
        or len(terms) != 99
        or actual.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V3_ID
        or actual.get("comparison_profile_id")
        != EXPECTED_COMPARISON_PROFILE_V3_ID
        or actual.get("caller_supplied_actual_comparison_allowed")
        is not False
        or actual_terms != terms
    ):
        _fail("v3 comparison/actual profile shape changed")
    source_paths: list[str] = []
    for row in terms:
        if (
            type(row) is not dict
            or row.get("coefficient") != 1
            or row.get("source_lane") != "operational"
            or row.get("target_axis") not in _SHARED_AXES
            or row.get("reducer") not in {"sum", "max"}
            or type(row.get("source_leaf")) is not str
        ):
            _fail("v3 projection term changed")
        source_paths.append(row["source_leaf"])
    if len(set(source_paths)) != 99 or set(source_paths) != operational:
        _fail("v3 operational projection is incomplete or duplicated")


def _verify_migration(
    migration: Mapping[str, Any],
    known_paths: set[str],
    legacy_paths: set[str],
    legacy_sources: Mapping[str, set[str]],
) -> None:
    _rehash_embedded(
        migration,
        id_field="migration_profile_id",
        domain=CONSTRUCTION_LEGACY_MIGRATION_PROFILE_V3_DOMAIN,
        expected_id=EXPECTED_LEGACY_MIGRATION_PROFILE_V3_ID,
        label="v3 legacy migration profile",
    )
    rows = migration.get("rows")
    if (
        migration.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V3_ID
        or migration.get("legacy_catalogue_entry_count") != 95
        or migration.get("legacy_distinct_path_count") != 87
        or migration.get("disposition_counts") != _DISPOSITION_COUNTS
        or migration.get("legacy_summary_translation_allowed")
        is not False
        or migration.get("operation_site_instrumentation_complete")
        is not False
        or migration.get("derived_formula_registry_complete") is not False
        or type(rows) is not list
        or len(rows) != 87
    ):
        _fail("v3 legacy migration profile shape changed")
    by_path: dict[str, dict[str, Any]] = {}
    for row in rows:
        if (
            type(row) is not dict
            or type(row.get("legacy_path")) is not str
            or row["legacy_path"] in by_path
            or row.get("historical_summary_translation_allowed") is not False
            or type(row.get("source_catalogues")) is not list
            or type(row.get("target_paths")) is not list
            or not set(row["target_paths"]) <= known_paths
        ):
            _fail("v3 migration row is malformed")
        by_path[row["legacy_path"]] = row
    if set(by_path) != legacy_paths or list(by_path) != sorted(by_path):
        _fail("v3 migration path coverage changed")
    expected_disposition = {
        **{
            path: "REGISTER_NEW_OPERATIONAL_FAMILY"
            for path in _NEW_OPERATIONAL
        },
        **{
            path: "REINSTRUMENT_EXISTING_FAMILY"
            for path in _REINSTRUMENT
        },
        **{path: "DECOMPOSE_AT_NATIVE_SITES" for path in _DECOMPOSE},
    }
    for path, row in by_path.items():
        expected = expected_disposition.get(
            path, "DERIVE_OR_DIAGNOSE_FROM_PRIMITIVES"
        )
        if (
            row.get("disposition") != expected
            or set(row["source_catalogues"])
            != legacy_sources[path]
            or (
                expected == "DERIVE_OR_DIAGNOSE_FROM_PRIMITIVES"
                and row["target_paths"] != []
            )
        ):
            _fail("v3 migration disposition/source binding changed")
    if (
        set(expected_disposition) != (
            _NEW_OPERATIONAL | _REINSTRUMENT | _DECOMPOSE
        )
        or len(_NEW_OPERATIONAL) != 11
        or len(_REINSTRUMENT) != 7
        or len(_DECOMPOSE) != 18
    ):
        _fail("independent migration partition constants changed")


def _expected_outer(
    *,
    upstream: (
        upstream_verifier
        .V075ConstructionAccountingSchemaIndependentVerificationV2
    ),
    upstream_schema: Mapping[str, Any],
    registry: Mapping[str, Any],
    stage: Mapping[str, Any],
    comparison: Mapping[str, Any],
    actual: Mapping[str, Any],
    migration: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v075_construction_accounting_registry_successor.v3"
        ),
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "upstream_profile_key": UPSTREAM_PROFILE_KEY,
        "terminal_scope": "CONSTRUCTION_ACCOUNTING_SUCCESSOR_SCHEMA_ONLY",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": (
            "CONSTRUCTION_ACCOUNTING_V3_SUCCESSOR_FROZEN_"
            "LIVE_OPERATION_SITE_INSTRUMENTATION_LOCKED"
        ),
        "upstream_closure_id": upstream.closure_id,
        "upstream_verification_id": upstream.verification_id,
        "multiround_result_id": upstream_schema["multiround_result_id"],
        "multiround_status": "CHILD_ACTION_ROW_CAP_EXCEEDED",
        "terminal_derivation_registry_id": (
            upstream_schema["terminal_derivation_registry_id"]
        ),
        "counter_registry": registry,
        "counter_registry_id": EXPECTED_COUNTER_REGISTRY_V3_ID,
        "stage_profile": stage,
        "stage_profile_id": EXPECTED_STAGE_PROFILE_V3_ID,
        "comparison_profile": comparison,
        "comparison_profile_id": EXPECTED_COMPARISON_PROFILE_V3_ID,
        "actual_projection_profile": actual,
        "actual_projection_profile_id": (
            EXPECTED_ACTUAL_PROJECTION_PROFILE_V3_ID
        ),
        "legacy_migration_profile": migration,
        "legacy_migration_profile_id": (
            EXPECTED_LEGACY_MIGRATION_PROFILE_V3_ID
        ),
        "v2_prefix_leaf_count": 69,
        "v2_prefix_preserved_exactly": True,
        "v3_addition_count": 47,
        "v3_leaf_count": 116,
        "v3_operational_leaf_count": 99,
        "v3_required_leaf_count": 109,
        "registered_stage_count": 10,
        "projection_term_count": 99,
        "legacy_catalogue_entry_count": 95,
        "legacy_distinct_path_count": 87,
        "legacy_reinstrument_existing_count": 7,
        "legacy_decompose_native_count": 18,
        "legacy_derive_or_diagnose_count": 51,
        "legacy_new_operational_family_count": 11,
        "open_incremental_acquisition_stage_registered": True,
        "open_checkpoint_replanning_stage_registered": True,
        "initial_build_owns_root_epoch_compile_and_plan": True,
        "failed_abstract_prefix_owns_verified_child_audit_only": True,
        "interval_row_path_uses_registered_row_behavior_unit": True,
        "legacy_summary_translation_allowed": False,
        "operation_site_instrumentation_complete": False,
        "derived_formula_registry_complete": False,
        "hash_check_io_peak_granularity_profile_complete": False,
        "stage_start_attestation_semantics_frozen": False,
        "stage_completion_attestation_semantics_frozen": False,
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
class V075ConstructionAccountingSuccessorIndependentVerificationV3:
    _issuer: InitVar[object]
    successor_id: str
    successor_sha256: str
    successor_byte_count: int
    upstream_closure_id: str
    upstream_verification_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    legacy_migration_profile_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value in (
            self.successor_id,
            self.successor_sha256,
            self.upstream_closure_id,
            self.upstream_verification_id,
            self.counter_registry_id,
            self.stage_profile_id,
            self.comparison_profile_id,
            self.actual_projection_profile_id,
            self.legacy_migration_profile_id,
        ):
            parse_content_id(value)
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.successor_byte_count) is not int
            or self.successor_byte_count <= 0
        ):
            _fail("independent successor verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(
                V075_CONSTRUCTION_ACCOUNTING_REGISTRY_SUCCESSOR_VERIFICATION_V3_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_accounting_registry_successor_"
                "independent_verification.v3"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "producer_profile_key": PRODUCER_PROFILE_KEY,
            "successor_id": self.successor_id,
            "successor_sha256": self.successor_sha256,
            "successor_byte_count": self.successor_byte_count,
            "upstream_closure_id": self.upstream_closure_id,
            "upstream_verification_id": self.upstream_verification_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": (
                self.actual_projection_profile_id
            ),
            "legacy_migration_profile_id": (
                self.legacy_migration_profile_id
            ),
            "producer_imported": False,
            "producer_entry_called": False,
            "construction_accounting_v3_core_imported": False,
            "construction_accounting_v3_core_entry_called": False,
            "embedded_profile_ids_rehashed_independently": True,
            "v2_prefix_compared_from_verified_upstream_bytes": True,
            "legacy_paths_rebuilt_from_verified_foundation_rows": True,
            "legacy_disposition_partition_checked_independently": True,
            "stage_ownership_checked_independently": True,
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
            "independent successor verifications are in-memory-only"
        )


def verify_v075_construction_accounting_registry_successor_bytes_v3(
    *,
    successor_bytes: bytes,
    schema_closure_bytes: bytes,
    foundation_bytes: bytes,
    source_code_provenance_bytes: bytes,
    repository_root: str,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075ConstructionAccountingSuccessorIndependentVerificationV3:
    """Replay exact 1.85, then independently verify the v3 successor."""

    try:
        upstream = (
            upstream_verifier
            .verify_v075_construction_accounting_schema_bytes_v2(
                closure_bytes=schema_closure_bytes,
                foundation_bytes=foundation_bytes,
                source_code_provenance_bytes=source_code_provenance_bytes,
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=(
                    public_context_closure_bytes
                ),
                private_generation_seed=private_generation_seed,
                private_salt=private_salt,
            )
        )
        successor = _strict_document(
            successor_bytes, label="contract-1.86 successor"
        )
        upstream_schema = _strict_document(
            schema_closure_bytes, label="verified contract-1.85 schema"
        )
        foundation = _strict_document(
            foundation_bytes, label="verified contract-1.84 foundation"
        )
        legacy_paths, legacy_sources = _verified_legacy_paths(foundation)
        registry = successor.get("counter_registry")
        stage = successor.get("stage_profile")
        comparison = successor.get("comparison_profile")
        actual = successor.get("actual_projection_profile")
        migration = successor.get("legacy_migration_profile")
        if not all(
            type(value) is dict
            for value in (
                registry,
                stage,
                comparison,
                actual,
                migration,
            )
        ):
            _fail("successor embedded profiles are absent")
        known, operational = _verify_registry(registry, upstream_schema)
        _verify_stage(stage, known)
        _verify_projection(comparison, actual, operational)
        _verify_migration(
            migration,
            known,
            legacy_paths,
            legacy_sources,
        )
        expected = _expected_outer(
            upstream=upstream,
            upstream_schema=upstream_schema,
            registry=registry,
            stage=stage,
            comparison=comparison,
            actual=actual,
            migration=migration,
        )
        expected_id = content_id(
            V075_CONSTRUCTION_ACCOUNTING_REGISTRY_SUCCESSOR_V3_DOMAIN,
            expected,
        )
        if (
            successor != {**expected, "successor_id": expected_id}
            or canonical_json_bytes(successor) != successor_bytes
        ):
            _fail("successor outer closure differs from independent replay")
        return (
            V075ConstructionAccountingSuccessorIndependentVerificationV3(
                _VERIFICATION_ISSUER,
                expected_id,
                hashlib.sha256(successor_bytes).hexdigest(),
                len(successor_bytes),
                upstream.closure_id,
                upstream.verification_id,
                EXPECTED_COUNTER_REGISTRY_V3_ID,
                EXPECTED_STAGE_PROFILE_V3_ID,
                EXPECTED_COMPARISON_PROFILE_V3_ID,
                EXPECTED_ACTUAL_PROJECTION_PROFILE_V3_ID,
                EXPECTED_LEGACY_MIGRATION_PROFILE_V3_ID,
            )
        )
    except Exception:
        raise V075ConstructionAccountingSuccessorIndependentV3Violation(
            _REPLAY_MISMATCH
        ) from None


__all__ = [
    "EXPECTED_ACTUAL_PROJECTION_PROFILE_V3_ID",
    "EXPECTED_COMPARISON_PROFILE_V3_ID",
    "EXPECTED_COUNTER_REGISTRY_V3_ID",
    "EXPECTED_LEGACY_MIGRATION_PROFILE_V3_ID",
    "EXPECTED_STAGE_PROFILE_V3_ID",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "V075ConstructionAccountingSuccessorIndependentV3Violation",
    "V075ConstructionAccountingSuccessorIndependentVerificationV3",
    "verify_v075_construction_accounting_registry_successor_bytes_v3",
]
