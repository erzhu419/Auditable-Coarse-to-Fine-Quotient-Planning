"""Independent verifier for contract-1.87 operation ownership.

The verifier does not import the v4 registry implementation or its producer.
It replays contract 1.86 from the complete required inputs, treats the
verified embedded v3 profiles as bytes, and independently reconstructs the
eight-leaf additive registry, stage ownership and 106-term projections.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V4_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V4_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V4_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V4_DOMAIN,
    V075_CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_SUCCESSOR_V4_DOMAIN,
    V075_CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_VERIFICATION_V4_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp import (
    v075_construction_accounting_registry_successor_independent_verifier_v3
    as upstream_verifier,
)


SCHEMA_VERSION = "4.0.0"
PROPOSED_CONTRACT_VERSION = "1.87.0"
PROFILE_KEY = (
    "v075_construction_accounting_operation_ownership_"
    "independent_verifier_v4"
)
PRODUCER_PROFILE_KEY = (
    "v075_construction_accounting_operation_ownership_successor_v4"
)
UPSTREAM_PROFILE_KEY = (
    "v075_construction_accounting_registry_successor_"
    "independent_verifier_v3"
)
MAX_BYTES = 64 * 1024 * 1024

EXPECTED_COUNTER_REGISTRY_V3_ID = (
    "09e48ea7f3c666de5e58bcb024e074cd"
    "887739daff598a4bf13c2e8a1a5e552e"
)
EXPECTED_COUNTER_REGISTRY_V4_ID = (
    "edc4da61f6a7c638fdef3c40259f2d55"
    "8156758970dabbf023ca41948fbda2b0"
)
EXPECTED_STAGE_PROFILE_V4_ID = (
    "4fdcdd32126d70d90fec7534248f1652"
    "e16a605b1027fb848b41e3d59051e1b0"
)
EXPECTED_COMPARISON_PROFILE_V4_ID = (
    "9aaf15120ed4188fb863bf5cb3ed76f0c"
    "33fc79978257830e7f00d1134b0135b"
)
EXPECTED_ACTUAL_PROJECTION_PROFILE_V4_ID = (
    "5144a7031ded3131f8929c5087c95c88"
    "23830c2935e4a42471e95428df4f0e73"
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


def _leaf(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    scope: str,
    *,
    lane: str = "operational",
    comparison_axis: str | None = "nonkernel_compute_events",
) -> dict[str, Any]:
    return {
        "path": path,
        "semantics_id": semantics_id,
        "owner": owner,
        "unit": unit,
        "lane": lane,
        "scope": scope,
        "reducer": "sum",
        "comparison_axis": comparison_axis,
        "required": True,
    }


_INITIAL_SCOPE = "construction_occurrence_initial_build_epoch"
_CHECKPOINT_SCOPE = "construction_occurrence_open_checkpoint_replanning"
_CLOSURE_SCOPE = (
    "construction_occurrence_closed_reconciliation_and_terminalization"
)
_ADDITIONS = {
    row["path"]: row
    for row in (
        _leaf(
            "build.initial_outcome_projections",
            "v075-outcome-projection-v4-initial-build",
            "v075_batch_native_planning_backend_v2",
            "outcome_projections",
            _INITIAL_SCOPE,
        ),
        _leaf(
            "build.initial_proposal_entries_bound",
            "v075-proposal-entry-binding-v4-initial-build",
            "v075_source_prior_adapter_v1",
            "proposal_entries",
            _INITIAL_SCOPE,
        ),
        _leaf(
            "build.open_checkpoint_outcome_projections",
            "v075-outcome-projection-v4-open-checkpoint",
            "v075_batch_native_planning_backend_v2",
            "outcome_projections",
            _CHECKPOINT_SCOPE,
        ),
        _leaf(
            "build.open_checkpoint_proposal_entries_bound",
            "v075-proposal-entry-binding-v4-open-checkpoint",
            "v075_source_prior_adapter_v1",
            "proposal_entries",
            _CHECKPOINT_SCOPE,
        ),
        _leaf(
            "closure.reconciliation_private_replay_ground_steps",
            "v075-private-replay-ground-step-v4-closed-reconciliation",
            "v075_private_observer_boundary_v2",
            "ground_steps",
            _CLOSURE_SCOPE,
            comparison_axis="kernel_transition_calls",
        ),
        _leaf(
            "closure.reconciliation_private_replay_random_word_calls",
            "v075-private-replay-random-word-call-v4-closed-reconciliation",
            "v075_private_observer_boundary_v2",
            "random_word_calls",
            _CLOSURE_SCOPE,
        ),
        _leaf(
            "closure.reconciliation_private_replay_rejections",
            "v075-private-replay-rejection-v4-closed-reconciliation",
            "v075_private_observer_boundary_v2",
            "rejections",
            _CLOSURE_SCOPE,
            lane="diagnostic",
            comparison_axis=None,
        ),
        _leaf(
            "closure.reconciliation_private_replay_outcome_aggregate_rows",
            "v075-private-replay-outcome-aggregate-row-v4-closed-reconciliation",
            "v075_private_observer_boundary_v2",
            "aggregate_rows",
            _CLOSURE_SCOPE,
        ),
    )
}
_STAGE_ADDITIONS = {
    "INITIAL_MODEL_BUILD": {
        "build.initial_outcome_projections",
        "build.initial_proposal_entries_bound",
    },
    "OPEN_CHECKPOINT_REPLANNING": {
        "build.open_checkpoint_outcome_projections",
        "build.open_checkpoint_proposal_entries_bound",
    },
    "CLOSED_RECONCILIATION_AND_TERMINALIZATION": {
        "closure.reconciliation_private_replay_ground_steps",
        "closure.reconciliation_private_replay_random_word_calls",
        "closure.reconciliation_private_replay_rejections",
        "closure.reconciliation_private_replay_outcome_aggregate_rows",
    },
}

_REPLAY_MISMATCH = (
    "independent contract-1.87 operation-ownership replay mismatch"
)
_VERIFICATION_ISSUER = object()


class V075ConstructionAccountingOperationOwnershipIndependentV4Violation(
    ValueError
):
    """Upstream replay, embedded v4 profiles, or outer locks are invalid."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionAccountingOperationOwnershipIndependentV4Violation(
        message
    )


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        _fail(f"{label} bytes are absent or exceed the cap")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionAccountingOperationOwnershipIndependentV4Violation(
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
        raise V075ConstructionAccountingOperationOwnershipIndependentV4Violation(
            f"{label} cannot be canonically re-hashed"
        ) from error
    if claimed != actual or actual != expected_id:
        _fail(f"{label} identity changed")


def _verify_registry(
    registry: Mapping[str, Any],
    upstream_registry: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    _rehash_embedded(
        registry,
        id_field="counter_registry_id",
        domain=CONSTRUCTION_COUNTER_REGISTRY_V4_DOMAIN,
        expected_id=EXPECTED_COUNTER_REGISTRY_V4_ID,
        label="v4 counter registry",
    )
    leaves = registry.get("leaves")
    base_leaves = upstream_registry.get("leaves")
    if (
        registry.get("schema") != "acfqp.counter_registry.v4"
        or registry.get("schema_version") != SCHEMA_VERSION
        or registry.get("counter_registry_key")
        != "acfqp_counter_registry_v4"
        or registry.get("v3_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V3_ID
        or registry.get("v3_prefix_preserved_exactly") is not True
        or registry.get(
            "v3_acquisition_paths_remain_valid_and_registered"
        )
        is not True
        or registry.get(
            "native_zero_required_when_registered_path_did_not_execute"
        )
        is not True
        or type(leaves) is not list
        or len(leaves) != 124
        or type(base_leaves) is not list
        or len(base_leaves) != 116
    ):
        _fail("v4 registry shape or v3 binding changed")
    by_path: dict[str, dict[str, Any]] = {}
    for row in leaves:
        if (
            type(row) is not dict
            or type(row.get("path")) is not str
            or row["path"] in by_path
        ):
            _fail("v4 registry leaf is malformed or duplicated")
        by_path[row["path"]] = row
    if list(by_path) != sorted(by_path):
        _fail("v4 registry leaves are not path-sorted")
    base = {row["path"]: row for row in base_leaves}
    if len(base) != 116 or any(by_path[path] != row for path, row in base.items()):
        _fail("v4 registry did not preserve the exact v3 prefix")
    additions = set(by_path) - set(base)
    if additions != set(_ADDITIONS) or any(
        by_path[path] != expected for path, expected in _ADDITIONS.items()
    ):
        _fail("v4 exact eight-leaf additive catalogue changed")
    operational = {
        path
        for path, row in by_path.items()
        if row.get("lane") == "operational"
    }
    required = {
        path for path, row in by_path.items() if row.get("required") is True
    }
    if len(operational) != 106 or len(required) != 117:
        _fail("v4 operational/required cardinality changed")
    return by_path, operational


def _stage_rows(profile: Mapping[str, Any], *, label: str) -> dict[str, set[str]]:
    rows = profile.get("rules")
    if type(rows) is not list or len(rows) != 10:
        _fail(f"{label} stage rows changed")
    by_stage: dict[str, set[str]] = {}
    for row in rows:
        if (
            type(row) is not dict
            or set(row) != {"stage_kind", "allowed_nonzero_paths"}
            or type(row.get("stage_kind")) is not str
            or type(row.get("allowed_nonzero_paths")) is not list
            or row["stage_kind"] in by_stage
            or row["allowed_nonzero_paths"]
            != sorted(set(row["allowed_nonzero_paths"]))
        ):
            _fail(f"{label} stage rule is malformed")
        by_stage[row["stage_kind"]] = set(row["allowed_nonzero_paths"])
    if tuple(sorted(by_stage)) != _STAGES:
        _fail(f"{label} stage vocabulary changed")
    return by_stage


def _verify_stage(
    stage: Mapping[str, Any],
    upstream_stage: Mapping[str, Any],
    known_paths: set[str],
) -> None:
    _rehash_embedded(
        stage,
        id_field="stage_profile_id",
        domain=CONSTRUCTION_STAGE_PROFILE_V4_DOMAIN,
        expected_id=EXPECTED_STAGE_PROFILE_V4_ID,
        label="v4 stage profile",
    )
    if (
        stage.get("schema") != "acfqp.construction_stage_profile.v4"
        or stage.get("schema_version") != SCHEMA_VERSION
        or stage.get("profile_key") != "construction_stage_exclusivity_v4"
        or stage.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V4_ID
        or stage.get("v3_stage_profile_id")
        != upstream_stage.get("stage_profile_id")
        or stage.get(
            "v3_stage_ownership_preserved_exactly"
        )
        is not True
        or stage.get(
            "build_projection_and_prior_binding_owned_by_build_stages"
        )
        is not True
        or stage.get(
            "closed_private_replay_owned_by_closed_reconciliation"
        )
        is not True
        or stage.get(
            "v3_acquisition_paths_remain_valid_and_registered"
        )
        is not True
    ):
        _fail("v4 stage profile shape changed")
    base = _stage_rows(upstream_stage, label="verified v3")
    current = _stage_rows(stage, label="v4")
    for kind in _STAGES:
        if current[kind] != base[kind] | _STAGE_ADDITIONS.get(kind, set()):
            _fail("v4 exact additive stage ownership changed")
        if not current[kind] <= known_paths:
            _fail("v4 stage profile references an unknown path")


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
        domain=CONSTRUCTION_COMPARISON_PROFILE_V4_DOMAIN,
        expected_id=EXPECTED_COMPARISON_PROFILE_V4_ID,
        label="v4 comparison profile",
    )
    _rehash_embedded(
        actual,
        id_field="actual_projection_profile_id",
        domain=CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V4_DOMAIN,
        expected_id=EXPECTED_ACTUAL_PROJECTION_PROFILE_V4_ID,
        label="v4 actual projection profile",
    )
    terms = comparison.get("terms")
    expected = _expected_terms(leaves)
    axes = comparison.get("axes")
    if (
        comparison.get("schema") != "acfqp.comparison_profile.v4"
        or comparison.get("schema_version") != SCHEMA_VERSION
        or comparison.get("profile_key")
        != "comparison_profile_shared_resources_v4"
        or comparison.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V4_ID
        or comparison.get("scalar_cost_defined") is not False
        or axes != upstream_comparison.get("axes")
        or type(axes) is not list
        or tuple(row.get("name") for row in axes if type(row) is dict)
        != _SHARED_AXES
        or terms != expected
        or len(expected) != 106
        or {row["source_leaf"] for row in expected} != operational
    ):
        _fail("v4 exact comparison projection changed")
    if (
        actual.get("schema") != "acfqp.actual_projection_profile.v4"
        or actual.get("schema_version") != SCHEMA_VERSION
        or actual.get("profile_key")
        != "actual_projection_construction_v4"
        or actual.get("counter_registry_id")
        != EXPECTED_COUNTER_REGISTRY_V4_ID
        or actual.get("comparison_profile_id")
        != EXPECTED_COMPARISON_PROFILE_V4_ID
        or actual.get("terms") != expected
        or actual.get("caller_supplied_actual_comparison_allowed")
        is not False
    ):
        _fail("v4 exact actual-projection profile changed")


def _expected_outer(
    *,
    upstream: (
        upstream_verifier
        .V075ConstructionAccountingSuccessorIndependentVerificationV3
    ),
    upstream_document: Mapping[str, Any],
    registry: Mapping[str, Any],
    stage: Mapping[str, Any],
    comparison: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v075_construction_accounting_operation_ownership_"
            "successor.v4"
        ),
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "upstream_profile_key": UPSTREAM_PROFILE_KEY,
        "terminal_scope": (
            "CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_SCHEMA_ONLY"
        ),
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": (
            "CONSTRUCTION_ACCOUNTING_V4_OPERATION_OWNERSHIP_FROZEN_"
            "LIVE_EVIDENCE_LOCKED"
        ),
        "upstream_successor_id": upstream.successor_id,
        "upstream_verification_id": upstream.verification_id,
        "upstream_closure_id": upstream.upstream_closure_id,
        "upstream_schema_verification_id": upstream.upstream_verification_id,
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
        "upstream_legacy_migration_profile_id": (
            upstream.legacy_migration_profile_id
        ),
        "counter_registry": registry,
        "counter_registry_id": EXPECTED_COUNTER_REGISTRY_V4_ID,
        "stage_profile": stage,
        "stage_profile_id": EXPECTED_STAGE_PROFILE_V4_ID,
        "comparison_profile": comparison,
        "comparison_profile_id": EXPECTED_COMPARISON_PROFILE_V4_ID,
        "actual_projection_profile": actual,
        "actual_projection_profile_id": (
            EXPECTED_ACTUAL_PROJECTION_PROFILE_V4_ID
        ),
        "v3_prefix_leaf_count": 116,
        "v3_prefix_preserved_exactly": True,
        "v4_addition_count": 8,
        "v4_leaf_count": 124,
        "v4_operational_leaf_count": 106,
        "v4_required_leaf_count": 117,
        "registered_stage_count": 10,
        "projection_term_count": 106,
        "build_projection_and_prior_binding_owned_by_build_stages": True,
        "closed_private_replay_owned_by_closed_reconciliation": True,
        "v3_acquisition_paths_remain_valid_and_registered": True,
        "native_zero_required_when_registered_path_did_not_execute": True,
        "failed_audit_owned_no_full_replay_route_registered": True,
        "failed_audit_owned_no_full_replay_route_live_evidenced": False,
        "owned_root_cap_result_audit_host_full_replay_allowed": False,
        "owned_root_cap_no_full_replay_runner_wired": False,
        "legacy_v2_portable_replay_default_unchanged": True,
        "legacy_summary_translation_allowed": False,
        "operation_site_instrumentation_complete": False,
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
class V075ConstructionAccountingOperationOwnershipIndependentVerificationV4:
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
        ):
            parse_content_id(value)
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.successor_byte_count) is not int
            or self.successor_byte_count <= 0
        ):
            _fail("independent operation-ownership verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(
                V075_CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_VERIFICATION_V4_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_accounting_operation_ownership_"
                "independent_verification.v4"
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
            "actual_projection_profile_id": (
                self.actual_projection_profile_id
            ),
            "producer_imported": False,
            "producer_entry_called": False,
            "construction_accounting_v4_core_imported": False,
            "construction_accounting_v4_core_entry_called": False,
            "upstream_contract_186_replayed_exactly": True,
            "embedded_profile_ids_rehashed_independently": True,
            "v3_prefix_compared_from_verified_upstream_bytes": True,
            "eight_additions_checked_independently": True,
            "stage_ownership_checked_independently": True,
            "projection_106_terms_checked_independently": True,
            "owned_root_cap_result_audit_host_full_replay_allowed": False,
            "owned_root_cap_no_full_replay_runner_wired": False,
            "legacy_v2_portable_replay_default_unchanged": True,
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
            "independent operation-ownership verifications are in-memory-only"
        )


def verify_v075_construction_accounting_operation_ownership_bytes_v4(
    *,
    successor_bytes: bytes,
    registry_successor_bytes: bytes,
    schema_closure_bytes: bytes,
    foundation_bytes: bytes,
    source_code_provenance_bytes: bytes,
    repository_root: str,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075ConstructionAccountingOperationOwnershipIndependentVerificationV4:
    """Replay contract 1.86 and independently verify contract 1.87."""

    try:
        upstream = (
            upstream_verifier
            .verify_v075_construction_accounting_registry_successor_bytes_v3(
                successor_bytes=registry_successor_bytes,
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
            successor_bytes, label="contract-1.87 operation ownership"
        )
        upstream_document = _strict_document(
            registry_successor_bytes,
            label="verified contract-1.86 registry successor",
        )
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
            _fail("upstream or v4 embedded profiles are absent")
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
        )
        expected_id = content_id(
            V075_CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_SUCCESSOR_V4_DOMAIN,
            expected,
        )
        if (
            successor != {**expected, "successor_id": expected_id}
            or canonical_json_bytes(successor) != successor_bytes
        ):
            _fail("operation-ownership outer closure changed")
        return V075ConstructionAccountingOperationOwnershipIndependentVerificationV4(
            _VERIFICATION_ISSUER,
            expected_id,
            hashlib.sha256(successor_bytes).hexdigest(),
            len(successor_bytes),
            upstream.successor_id,
            upstream.verification_id,
            EXPECTED_COUNTER_REGISTRY_V4_ID,
            EXPECTED_STAGE_PROFILE_V4_ID,
            EXPECTED_COMPARISON_PROFILE_V4_ID,
            EXPECTED_ACTUAL_PROJECTION_PROFILE_V4_ID,
        )
    except Exception:
        raise V075ConstructionAccountingOperationOwnershipIndependentV4Violation(
            _REPLAY_MISMATCH
        ) from None


__all__ = [
    "EXPECTED_ACTUAL_PROJECTION_PROFILE_V4_ID",
    "EXPECTED_COMPARISON_PROFILE_V4_ID",
    "EXPECTED_COUNTER_REGISTRY_V4_ID",
    "EXPECTED_STAGE_PROFILE_V4_ID",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "V075ConstructionAccountingOperationOwnershipIndependentV4Violation",
    "V075ConstructionAccountingOperationOwnershipIndependentVerificationV4",
    "verify_v075_construction_accounting_operation_ownership_bytes_v4",
]
