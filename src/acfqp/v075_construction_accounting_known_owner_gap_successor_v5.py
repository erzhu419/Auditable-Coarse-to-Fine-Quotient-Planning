"""Contract-1.89 schema authority for the known K7 owner gaps.

The authority consumes exact independent contract-1.87 evidence and freezes
the immutable additive V5 profiles.  It installs no hook, executes no K7
occurrence, and emits no accounting evidence.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.construction_accounting_registry_v5 import (
    EXPECTED_V4_LEAF_COUNT,
    EXPECTED_V4_OPERATIONAL_LEAF_COUNT,
    EXPECTED_V4_REQUIRED_LEAF_COUNT,
    EXPECTED_V5_ADDITION_COUNT,
    EXPECTED_V5_LEAF_COUNT,
    EXPECTED_V5_OPERATIONAL_LEAF_COUNT,
    EXPECTED_V5_REQUIRED_LEAF_COUNT,
    EXPECTED_V5_STAGE_COUNT,
    freeze_construction_accounting_registry_v5,
    official_actual_projection_profile_v5,
    official_comparison_profile_v5,
    official_counter_registry_v5,
    official_stage_profile_v5,
)
from acfqp.phase3e_ids import (
    V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_SUCCESSOR_V5_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp import (
    v075_construction_accounting_operation_ownership_independent_verifier_v4
    as upstream_verifier,
)
from acfqp import v075_k7_root_cap_operation_site_manifest_v2 as site_manifest_v2


SCHEMA_VERSION = "5.0.0"
PROPOSED_CONTRACT_VERSION = "1.89.0"
PROFILE_KEY = "v075_construction_accounting_known_owner_gap_successor_v5"
UPSTREAM_PROFILE_KEY = (
    "v075_construction_accounting_operation_ownership_"
    "independent_verifier_v4"
)
TERMINAL_SCOPE = "CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_SCHEMA_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_ACCOUNTING_V5_KNOWN_OWNER_GAPS_FROZEN_"
    "LIVE_EVIDENCE_LOCKED"
)

EXPECTED_COUNTER_REGISTRY_V5_ID = (
    "cf1e63f677fa6f9831213b8b48ca88e1"
    "a8d489276af5d30029951670cfe6736f"
)
EXPECTED_COUNTER_REGISTRY_V4_ID = (
    "edc4da61f6a7c638fdef3c40259f2d55"
    "8156758970dabbf023ca41948fbda2b0"
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

_REPLAY_MISMATCH = (
    "contract-1.89 construction-accounting known-owner-gap replay mismatch"
)
_SUCCESSOR_ISSUER = object()


class V075ConstructionAccountingKnownOwnerGapV5Violation(ValueError):
    """The verified 1.87 input or additive V5 schema changed."""


class V075ConstructionAccountingKnownOwnerGapProductionV5NotReady(
    RuntimeError
):
    """The known-gap schema cannot authorize live execution."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionAccountingKnownOwnerGapV5Violation(message)


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > 64 * 1024 * 1024:
        _fail(f"{label} bytes are absent or exceed the cap")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionAccountingKnownOwnerGapV5Violation(
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
        return {key: _thaw_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    return value


def _verify_upstream(
    *,
    upstream: (
        upstream_verifier
        .V075ConstructionAccountingOperationOwnershipIndependentVerificationV4
    ),
    operation_ownership_successor_bytes: bytes,
) -> dict[str, Any]:
    if type(upstream) is not (
        upstream_verifier
        .V075ConstructionAccountingOperationOwnershipIndependentVerificationV4
    ):
        _fail("known-owner-gap successor requires exact independent 1.87")
    document = _strict_document(
        operation_ownership_successor_bytes,
        label="verified contract-1.87 operation-ownership successor",
    )
    if (
        document.get("successor_id") != upstream.successor_id
        or hashlib.sha256(operation_ownership_successor_bytes).hexdigest()
        != upstream.successor_sha256
        or len(operation_ownership_successor_bytes)
        != upstream.successor_byte_count
        or document.get("upstream_successor_id")
        != upstream.upstream_successor_id
        or document.get("upstream_verification_id")
        != upstream.upstream_verification_id
        or document.get("counter_registry_id")
        != upstream.counter_registry_id
        or document.get("stage_profile_id") != upstream.stage_profile_id
        or document.get("comparison_profile_id")
        != upstream.comparison_profile_id
        or document.get("actual_projection_profile_id")
        != upstream.actual_projection_profile_id
        or document.get("v4_leaf_count") != EXPECTED_V4_LEAF_COUNT
        or document.get("v4_operational_leaf_count")
        != EXPECTED_V4_OPERATIONAL_LEAF_COUNT
        or document.get("v4_required_leaf_count")
        != EXPECTED_V4_REQUIRED_LEAF_COUNT
        or document.get("operation_site_instrumentation_complete") is not False
        or document.get("live_counter_record_count") != 0
        or document.get("official_execution_allowed") is not False
        or document.get("fresh_heldout_accessed") is not False
    ):
        _fail("contract-1.87 identity or locked semantics changed")
    return document


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
    official = site_manifest_v2.official_k7_root_cap_operation_site_manifest_v2()
    official.validate_official()
    official_document = official.to_document()
    expected_counts = {
        "DIRECT_VALID_OWNER_MATCHED": 9,
        "NATIVE_ZERO_NOT_EXECUTED": 13,
        "REQUIRED_PENDING_HOOK": 10,
        "DERIVED_ONLY_RECONCILIATION": 1,
        "MISSING_COUNTER_FAMILY": 10,
    }
    if (
        strict_owner_manifest_id != EXPECTED_STRICT_OWNER_MANIFEST_V2_ID
        or strict_owner_manifest_id != official.manifest_id
        or document != official_document
        or canonical_json_bytes(official_document)
        != strict_owner_manifest_bytes
        or hashlib.sha256(strict_owner_manifest_bytes).hexdigest()
        != EXPECTED_STRICT_OWNER_MANIFEST_V2_SHA256
        or len(strict_owner_manifest_bytes)
        != EXPECTED_STRICT_OWNER_MANIFEST_V2_BYTE_COUNT
        or document.get("v1_operation_site_manifest_id")
        != EXPECTED_STRICT_OWNER_MANIFEST_V1_ID
        or document.get("v1_direct_native_semantic_audit_passed") is not False
        or document.get("v1_sink_imported_or_reused") is not False
        or document.get("site_count") != 43
        or document.get("classification_counts") != expected_counts
        or document.get("native_emitter_installed") is not False
        or document.get("operation_site_instrumentation_complete") is not False
        or document.get("counter_family_complete") is not False
        or document.get("live_operation_event_count") != 0
        or document.get("live_counter_record_count") != 0
        or document.get("official_execution_allowed") is not False
        or document.get("fresh_heldout_accessed") is not False
        or document.get("counter_completeness_gate_passed") is not False
        or document.get("workload_economics_gate_passed") is not False
    ):
        _fail("contract-1.88 strict-owner manifest changed")
    return document


@dataclass(frozen=True, slots=True)
class V075ConstructionAccountingKnownOwnerGapSuccessorV5:
    _issuer: InitVar[object]
    upstream_successor_id: str
    upstream_verification_id: str
    upstream_registry_successor_id: str
    upstream_registry_verification_id: str
    multiround_result_id: str
    terminal_derivation_registry_id: str
    upstream_counter_registry_id: str
    upstream_stage_profile_id: str
    upstream_comparison_profile_id: str
    upstream_actual_projection_profile_id: str
    strict_owner_manifest_id: str
    strict_owner_manifest_sha256: str
    strict_owner_manifest_byte_count: int
    strict_owner_v1_manifest_id: str
    counter_registry: Mapping[str, Any]
    stage_profile: Mapping[str, Any]
    comparison_profile: Mapping[str, Any]
    actual_projection_profile: Mapping[str, Any]
    _successor_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SUCCESSOR_ISSUER:
            _fail("known-owner-gap successor is caller-minted")
        for value in (
            self.upstream_successor_id,
            self.upstream_verification_id,
            self.upstream_registry_successor_id,
            self.upstream_registry_verification_id,
            self.multiround_result_id,
            self.terminal_derivation_registry_id,
            self.upstream_counter_registry_id,
            self.upstream_stage_profile_id,
            self.upstream_comparison_profile_id,
            self.upstream_actual_projection_profile_id,
            self.strict_owner_manifest_id,
            self.strict_owner_manifest_sha256,
            self.strict_owner_v1_manifest_id,
        ):
            parse_content_id(value)
        if (
            type(self.strict_owner_manifest_byte_count) is not int
            or self.strict_owner_manifest_byte_count <= 0
        ):
            _fail("strict-owner manifest byte count is invalid")
        exact = freeze_construction_accounting_registry_v5()
        for value, label in (
            (self.counter_registry, "counter_registry"),
            (self.stage_profile, "stage_profile"),
            (self.comparison_profile, "comparison_profile"),
            (self.actual_projection_profile, "actual_projection_profile"),
        ):
            if type(value) is not dict or value != exact[label]:
                _fail(f"{label} differs from exact V5 known-gap schema")
        for field_name in (
            "counter_registry",
            "stage_profile",
            "comparison_profile",
            "actual_projection_profile",
        ):
            object.__setattr__(
                self, field_name, _freeze_json(getattr(self, field_name))
            )
        object.__setattr__(
            self,
            "_successor_id",
            content_id(
                V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_SUCCESSOR_V5_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_accounting_known_owner_gap_"
                "successor.v5"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "upstream_profile_key": UPSTREAM_PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "upstream_successor_id": self.upstream_successor_id,
            "upstream_verification_id": self.upstream_verification_id,
            "upstream_registry_successor_id": (
                self.upstream_registry_successor_id
            ),
            "upstream_registry_verification_id": (
                self.upstream_registry_verification_id
            ),
            "multiround_result_id": self.multiround_result_id,
            "multiround_status": "CHILD_ACTION_ROW_CAP_EXCEEDED",
            "terminal_derivation_registry_id": (
                self.terminal_derivation_registry_id
            ),
            "upstream_counter_registry_id": self.upstream_counter_registry_id,
            "upstream_stage_profile_id": self.upstream_stage_profile_id,
            "upstream_comparison_profile_id": (
                self.upstream_comparison_profile_id
            ),
            "upstream_actual_projection_profile_id": (
                self.upstream_actual_projection_profile_id
            ),
            "strict_owner_manifest_id": self.strict_owner_manifest_id,
            "strict_owner_manifest_sha256": self.strict_owner_manifest_sha256,
            "strict_owner_manifest_byte_count": (
                self.strict_owner_manifest_byte_count
            ),
            "strict_owner_v1_manifest_id": self.strict_owner_v1_manifest_id,
            "strict_owner_manifest_v2_bound_from_canonical_bytes": True,
            "counter_registry": _thaw_json(self.counter_registry),
            "counter_registry_id": self.counter_registry[
                "counter_registry_id"
            ],
            "stage_profile": _thaw_json(self.stage_profile),
            "stage_profile_id": self.stage_profile["stage_profile_id"],
            "comparison_profile": _thaw_json(self.comparison_profile),
            "comparison_profile_id": self.comparison_profile[
                "comparison_profile_id"
            ],
            "actual_projection_profile": _thaw_json(
                self.actual_projection_profile
            ),
            "actual_projection_profile_id": self.actual_projection_profile[
                "actual_projection_profile_id"
            ],
            "v4_prefix_leaf_count": EXPECTED_V4_LEAF_COUNT,
            "v4_prefix_preserved_exactly": True,
            "v5_addition_count": EXPECTED_V5_ADDITION_COUNT,
            "v5_leaf_count": EXPECTED_V5_LEAF_COUNT,
            "v5_operational_leaf_count": EXPECTED_V5_OPERATIONAL_LEAF_COUNT,
            "v5_required_leaf_count": EXPECTED_V5_REQUIRED_LEAF_COUNT,
            "registered_stage_count": EXPECTED_V5_STAGE_COUNT,
            "projection_term_count": EXPECTED_V5_OPERATIONAL_LEAF_COUNT,
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

    @property
    def successor_id(self) -> str:
        return self._successor_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "successor_id": self.successor_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("known-owner-gap successors are in-memory-only")


def materialize_v075_construction_accounting_known_owner_gap_successor_v5(
    *,
    upstream: (
        upstream_verifier
        .V075ConstructionAccountingOperationOwnershipIndependentVerificationV4
    ),
    operation_ownership_successor_bytes: bytes,
    strict_owner_manifest_id: str,
    strict_owner_manifest_bytes: bytes,
) -> V075ConstructionAccountingKnownOwnerGapSuccessorV5:
    """Bind exact V5 profiles to independent contract-1.87 evidence."""

    try:
        verified = _verify_upstream(
            upstream=upstream,
            operation_ownership_successor_bytes=(
                operation_ownership_successor_bytes
            ),
        )
        strict_owner = _verify_strict_owner_manifest(
            strict_owner_manifest_id=strict_owner_manifest_id,
            strict_owner_manifest_bytes=strict_owner_manifest_bytes,
        )
        registry = official_counter_registry_v5()
        stage = official_stage_profile_v5(registry)
        comparison = official_comparison_profile_v5(registry)
        actual = official_actual_projection_profile_v5(
            registry, comparison
        )
        if (
            registry.v4_registry_id != EXPECTED_COUNTER_REGISTRY_V4_ID
            or registry.v4_registry_id != upstream.counter_registry_id
            or strict_owner["counter_registry_id"]
            != EXPECTED_COUNTER_REGISTRY_V4_ID
            or registry.registry_id != EXPECTED_COUNTER_REGISTRY_V5_ID
            or stage.stage_profile_id != EXPECTED_STAGE_PROFILE_V5_ID
            or comparison.comparison_profile_id
            != EXPECTED_COMPARISON_PROFILE_V5_ID
            or actual.actual_projection_profile_id
            != EXPECTED_ACTUAL_PROJECTION_PROFILE_V5_ID
        ):
            _fail("registered construction-accounting V5 identities changed")
        frozen = freeze_construction_accounting_registry_v5()
        return V075ConstructionAccountingKnownOwnerGapSuccessorV5(
            _SUCCESSOR_ISSUER,
            upstream.successor_id,
            upstream.verification_id,
            upstream.upstream_successor_id,
            upstream.upstream_verification_id,
            verified["multiround_result_id"],
            verified["terminal_derivation_registry_id"],
            upstream.counter_registry_id,
            upstream.stage_profile_id,
            upstream.comparison_profile_id,
            upstream.actual_projection_profile_id,
            strict_owner_manifest_id,
            hashlib.sha256(strict_owner_manifest_bytes).hexdigest(),
            len(strict_owner_manifest_bytes),
            strict_owner["v1_operation_site_manifest_id"],
            frozen["counter_registry"],
            frozen["stage_profile"],
            frozen["comparison_profile"],
            frozen["actual_projection_profile"],
        )
    except Exception:
        raise V075ConstructionAccountingKnownOwnerGapV5Violation(
            _REPLAY_MISMATCH
        ) from None


def assert_v075_construction_accounting_known_owner_gap_production_gate_v5(
    successor: V075ConstructionAccountingKnownOwnerGapSuccessorV5,
) -> NoReturn:
    if type(successor) is not V075ConstructionAccountingKnownOwnerGapSuccessorV5:
        _fail("production gate rejects known-owner-gap duck types")
    _ = successor.successor_id
    raise V075ConstructionAccountingKnownOwnerGapProductionV5NotReady(
        "contract 1.89 freezes only the minimal known owner gaps; operation "
        "hooks, common/hash/I/O/process/peak work, formulas, typed closures, "
        "all-path accounting, production, fresh science and certificates "
        "remain locked"
    )


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
    "V075ConstructionAccountingKnownOwnerGapProductionV5NotReady",
    "V075ConstructionAccountingKnownOwnerGapSuccessorV5",
    "V075ConstructionAccountingKnownOwnerGapV5Violation",
    "assert_v075_construction_accounting_known_owner_gap_production_gate_v5",
    "materialize_v075_construction_accounting_known_owner_gap_successor_v5",
]
