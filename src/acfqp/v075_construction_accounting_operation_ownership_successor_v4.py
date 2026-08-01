"""Contract-1.87 operation-ownership closure for V0-075 accounting.

This schema-only authority consumes the exact independent verification of
contract 1.86 and freezes the additive v4 registry discovered by the K7
operation-site audit.  It executes no occurrence and issues no work record.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.construction_accounting_registry_v4 import (
    EXPECTED_V3_LEAF_COUNT,
    EXPECTED_V3_OPERATIONAL_LEAF_COUNT,
    EXPECTED_V3_REQUIRED_LEAF_COUNT,
    EXPECTED_V4_ADDITION_COUNT,
    EXPECTED_V4_LEAF_COUNT,
    EXPECTED_V4_OPERATIONAL_LEAF_COUNT,
    EXPECTED_V4_REQUIRED_LEAF_COUNT,
    EXPECTED_V4_STAGE_COUNT,
    freeze_construction_accounting_registry_v4,
    official_actual_projection_profile_v4,
    official_comparison_profile_v4,
    official_counter_registry_v4,
    official_stage_profile_v4,
)
from acfqp.phase3e_ids import (
    V075_CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_SUCCESSOR_V4_DOMAIN,
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
    "v075_construction_accounting_operation_ownership_successor_v4"
)
UPSTREAM_PROFILE_KEY = (
    "v075_construction_accounting_registry_successor_"
    "independent_verifier_v3"
)
TERMINAL_SCOPE = "CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_SCHEMA_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_ACCOUNTING_V4_OPERATION_OWNERSHIP_FROZEN_"
    "LIVE_EVIDENCE_LOCKED"
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

_REPLAY_MISMATCH = (
    "contract-1.87 construction-accounting operation-ownership replay "
    "mismatch"
)
_SUCCESSOR_ISSUER = object()


class V075ConstructionAccountingOperationOwnershipV4Violation(ValueError):
    """The independently verified 1.86 input or v4 closure changed."""


class V075ConstructionAccountingOperationOwnershipProductionV4NotReady(
    RuntimeError
):
    """The v4 ownership schema cannot authorize live execution."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionAccountingOperationOwnershipV4Violation(message)


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > 64 * 1024 * 1024:
        _fail(f"{label} bytes are absent or exceed the cap")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionAccountingOperationOwnershipV4Violation(
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
        .V075ConstructionAccountingSuccessorIndependentVerificationV3
    ),
    registry_successor_bytes: bytes,
) -> dict[str, Any]:
    if (
        type(upstream)
        is not (
            upstream_verifier
            .V075ConstructionAccountingSuccessorIndependentVerificationV3
        )
    ):
        _fail("operation-ownership successor requires exact independent 1.86")
    document = _strict_document(
        registry_successor_bytes,
        label="verified contract-1.86 registry successor",
    )
    if (
        document.get("successor_id") != upstream.successor_id
        or hashlib.sha256(registry_successor_bytes).hexdigest()
        != upstream.successor_sha256
        or len(registry_successor_bytes) != upstream.successor_byte_count
        or document.get("upstream_closure_id")
        != upstream.upstream_closure_id
        or document.get("upstream_verification_id")
        != upstream.upstream_verification_id
        or document.get("counter_registry_id")
        != upstream.counter_registry_id
        or document.get("stage_profile_id") != upstream.stage_profile_id
        or document.get("comparison_profile_id")
        != upstream.comparison_profile_id
        or document.get("actual_projection_profile_id")
        != upstream.actual_projection_profile_id
        or document.get("legacy_migration_profile_id")
        != upstream.legacy_migration_profile_id
        or document.get("v3_leaf_count") != EXPECTED_V3_LEAF_COUNT
        or document.get("v3_operational_leaf_count")
        != EXPECTED_V3_OPERATIONAL_LEAF_COUNT
        or document.get("v3_required_leaf_count")
        != EXPECTED_V3_REQUIRED_LEAF_COUNT
        or document.get("operation_site_instrumentation_complete")
        is not False
        or document.get("derived_formula_registry_complete") is not False
        or document.get("live_counter_record_count") != 0
        or document.get("official_execution_allowed") is not False
        or document.get("fresh_heldout_accessed") is not False
    ):
        _fail("contract-1.86 identity or locked semantics changed")
    return document


@dataclass(frozen=True, slots=True)
class V075ConstructionAccountingOperationOwnershipSuccessorV4:
    _issuer: InitVar[object]
    upstream_successor_id: str
    upstream_verification_id: str
    upstream_closure_id: str
    upstream_schema_verification_id: str
    multiround_result_id: str
    terminal_derivation_registry_id: str
    upstream_counter_registry_id: str
    upstream_stage_profile_id: str
    upstream_comparison_profile_id: str
    upstream_actual_projection_profile_id: str
    upstream_legacy_migration_profile_id: str
    counter_registry: Mapping[str, Any]
    stage_profile: Mapping[str, Any]
    comparison_profile: Mapping[str, Any]
    actual_projection_profile: Mapping[str, Any]
    _successor_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SUCCESSOR_ISSUER:
            _fail("operation-ownership successor is caller-minted")
        for value in (
            self.upstream_successor_id,
            self.upstream_verification_id,
            self.upstream_closure_id,
            self.upstream_schema_verification_id,
            self.multiround_result_id,
            self.terminal_derivation_registry_id,
            self.upstream_counter_registry_id,
            self.upstream_stage_profile_id,
            self.upstream_comparison_profile_id,
            self.upstream_actual_projection_profile_id,
            self.upstream_legacy_migration_profile_id,
        ):
            parse_content_id(value)
        exact = freeze_construction_accounting_registry_v4()
        for value, label in (
            (self.counter_registry, "counter_registry"),
            (self.stage_profile, "stage_profile"),
            (self.comparison_profile, "comparison_profile"),
            (self.actual_projection_profile, "actual_projection_profile"),
        ):
            if type(value) is not dict or value != exact[label]:
                _fail(f"{label} differs from exact v4 ownership schema")
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
                V075_CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_SUCCESSOR_V4_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_accounting_operation_ownership_"
                "successor.v4"
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
            "upstream_closure_id": self.upstream_closure_id,
            "upstream_schema_verification_id": (
                self.upstream_schema_verification_id
            ),
            "multiround_result_id": self.multiround_result_id,
            "multiround_status": "CHILD_ACTION_ROW_CAP_EXCEEDED",
            "terminal_derivation_registry_id": (
                self.terminal_derivation_registry_id
            ),
            "upstream_counter_registry_id": (
                self.upstream_counter_registry_id
            ),
            "upstream_stage_profile_id": self.upstream_stage_profile_id,
            "upstream_comparison_profile_id": (
                self.upstream_comparison_profile_id
            ),
            "upstream_actual_projection_profile_id": (
                self.upstream_actual_projection_profile_id
            ),
            "upstream_legacy_migration_profile_id": (
                self.upstream_legacy_migration_profile_id
            ),
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
            "v3_prefix_leaf_count": EXPECTED_V3_LEAF_COUNT,
            "v3_prefix_preserved_exactly": True,
            "v4_addition_count": EXPECTED_V4_ADDITION_COUNT,
            "v4_leaf_count": EXPECTED_V4_LEAF_COUNT,
            "v4_operational_leaf_count": (
                EXPECTED_V4_OPERATIONAL_LEAF_COUNT
            ),
            "v4_required_leaf_count": EXPECTED_V4_REQUIRED_LEAF_COUNT,
            "registered_stage_count": EXPECTED_V4_STAGE_COUNT,
            "projection_term_count": EXPECTED_V4_OPERATIONAL_LEAF_COUNT,
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

    @property
    def successor_id(self) -> str:
        return self._successor_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "successor_id": self.successor_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("operation-ownership successors are in-memory-only")


def materialize_v075_construction_accounting_operation_ownership_successor_v4(
    *,
    upstream: (
        upstream_verifier
        .V075ConstructionAccountingSuccessorIndependentVerificationV3
    ),
    registry_successor_bytes: bytes,
) -> V075ConstructionAccountingOperationOwnershipSuccessorV4:
    """Bind the exact additive v4 profiles to independent contract 1.86."""

    try:
        verified = _verify_upstream(
            upstream=upstream,
            registry_successor_bytes=registry_successor_bytes,
        )
        registry = official_counter_registry_v4()
        stage = official_stage_profile_v4(registry)
        comparison = official_comparison_profile_v4(registry)
        actual = official_actual_projection_profile_v4(
            registry, comparison
        )
        if (
            registry.registry_id != EXPECTED_COUNTER_REGISTRY_V4_ID
            or stage.stage_profile_id != EXPECTED_STAGE_PROFILE_V4_ID
            or comparison.comparison_profile_id
            != EXPECTED_COMPARISON_PROFILE_V4_ID
            or actual.actual_projection_profile_id
            != EXPECTED_ACTUAL_PROJECTION_PROFILE_V4_ID
        ):
            _fail("registered construction-accounting v4 identities changed")
        frozen = freeze_construction_accounting_registry_v4()
        return V075ConstructionAccountingOperationOwnershipSuccessorV4(
            _SUCCESSOR_ISSUER,
            upstream.successor_id,
            upstream.verification_id,
            upstream.upstream_closure_id,
            upstream.upstream_verification_id,
            verified["multiround_result_id"],
            verified["terminal_derivation_registry_id"],
            upstream.counter_registry_id,
            upstream.stage_profile_id,
            upstream.comparison_profile_id,
            upstream.actual_projection_profile_id,
            upstream.legacy_migration_profile_id,
            frozen["counter_registry"],
            frozen["stage_profile"],
            frozen["comparison_profile"],
            frozen["actual_projection_profile"],
        )
    except Exception:
        raise V075ConstructionAccountingOperationOwnershipV4Violation(
            _REPLAY_MISMATCH
        ) from None


def assert_v075_construction_accounting_operation_ownership_production_gate_v4(
    successor: V075ConstructionAccountingOperationOwnershipSuccessorV4,
) -> NoReturn:
    if type(successor) is not V075ConstructionAccountingOperationOwnershipSuccessorV4:
        _fail("production gate rejects operation-ownership duck types")
    _ = successor.successor_id
    raise V075ConstructionAccountingOperationOwnershipProductionV4NotReady(
        "contract 1.87 freezes operation ownership only; live native "
        "records, formula/site/hash-I/O-peak closure, all-path accounting, "
        "production, fresh science and certificates remain locked"
    )


__all__ = [
    "EXPECTED_ACTUAL_PROJECTION_PROFILE_V4_ID",
    "EXPECTED_COMPARISON_PROFILE_V4_ID",
    "EXPECTED_COUNTER_REGISTRY_V4_ID",
    "EXPECTED_STAGE_PROFILE_V4_ID",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "V075ConstructionAccountingOperationOwnershipProductionV4NotReady",
    "V075ConstructionAccountingOperationOwnershipSuccessorV4",
    "V075ConstructionAccountingOperationOwnershipV4Violation",
    "assert_v075_construction_accounting_operation_ownership_production_gate_v4",
    "materialize_v075_construction_accounting_operation_ownership_successor_v4",
]
