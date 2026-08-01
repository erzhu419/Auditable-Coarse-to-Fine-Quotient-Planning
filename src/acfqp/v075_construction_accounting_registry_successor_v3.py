"""Contract-1.86 successor-registry closure for V0-075 accounting.

The authority consumes an exact independent verification of contract 1.85,
then materializes the additive v3 registry, its ten-stage profile, the
99-term shared-resource projection, and the complete 87-path legacy
migration partition.  It executes no occurrence and emits no work evidence.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.construction_accounting_registry_v3 import (
    EXPECTED_LEGACY_DISTINCT_PATH_COUNT,
    EXPECTED_V3_LEAF_COUNT,
    EXPECTED_V3_OPERATIONAL_LEAF_COUNT,
    EXPECTED_V3_REQUIRED_LEAF_COUNT,
    EXPECTED_V3_STAGE_COUNT,
    freeze_construction_accounting_registry_successor_v3,
    official_actual_projection_profile_v3,
    official_comparison_profile_v3,
    official_counter_registry_v3,
    official_legacy_migration_profile_v3,
    official_stage_profile_v3,
)
from acfqp.phase3e_ids import (
    V075_CONSTRUCTION_ACCOUNTING_REGISTRY_SUCCESSOR_V3_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp import (
    v075_construction_accounting_schema_independent_verifier_v2
    as schema_verifier,
)


SCHEMA_VERSION = "3.0.0"
PROPOSED_CONTRACT_VERSION = "1.86.0"
PROFILE_KEY = "v075_construction_accounting_registry_successor_v3"
UPSTREAM_PROFILE_KEY = (
    "v075_construction_accounting_schema_independent_verifier_v2"
)
TERMINAL_SCOPE = "CONSTRUCTION_ACCOUNTING_SUCCESSOR_SCHEMA_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_ACCOUNTING_V3_SUCCESSOR_FROZEN_"
    "LIVE_OPERATION_SITE_INSTRUMENTATION_LOCKED"
)

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

_REPLAY_MISMATCH = (
    "contract-1.86 construction-accounting successor replay mismatch"
)
_SUCCESSOR_ISSUER = object()


class V075ConstructionAccountingSuccessorV3Violation(ValueError):
    """The verified v2 schema or additive successor changed."""


class V075ConstructionAccountingSuccessorProductionV3NotReady(RuntimeError):
    """The successor schema cannot authorize live or scientific execution."""


def _fail(message: str) -> NoReturn:
    raise V075ConstructionAccountingSuccessorV3Violation(message)


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > 64 * 1024 * 1024:
        _fail(f"{label} bytes are absent or exceed the cap")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V075ConstructionAccountingSuccessorV3Violation(
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
        schema_verifier
        .V075ConstructionAccountingSchemaIndependentVerificationV2
    ),
    schema_closure_bytes: bytes,
) -> dict[str, Any]:
    if (
        type(upstream)
        is not (
            schema_verifier
            .V075ConstructionAccountingSchemaIndependentVerificationV2
        )
    ):
        _fail("successor requires exact independent contract 1.85")
    document = _strict_document(
        schema_closure_bytes, label="verified contract-1.85 schema"
    )
    if (
        document.get("closure_id") != upstream.closure_id
        or hashlib.sha256(schema_closure_bytes).hexdigest()
        != upstream.closure_sha256
        or len(schema_closure_bytes) != upstream.closure_byte_count
        or document.get("counter_registry_id")
        != upstream.counter_registry_id
        or document.get("stage_profile_id") != upstream.stage_profile_id
        or document.get("comparison_profile_id")
        != upstream.comparison_profile_id
        or document.get("actual_projection_profile_id")
        != upstream.actual_projection_profile_id
        or document.get("v2_leaf_count") != 69
        or document.get("v2_operational_leaf_count") != 53
        or document.get("v2_required_leaf_count") != 62
        or document.get("legacy_custom_distinct_path_count") != 87
        or document.get("critical_live_recorder_gap_list_is_exhaustive")
        is not False
        or document.get("legacy_custom_paths_native_semantics_complete")
        is not False
        or document.get("unmapped_operation_requires_registry_revision")
        is not True
        or document.get("live_counter_record_count") != 0
        or document.get("work_vector_count") != 0
        or document.get("official_execution_allowed") is not False
        or document.get("fresh_heldout_accessed") is not False
    ):
        _fail("contract-1.85 schema identity or locked semantics changed")
    return document


@dataclass(frozen=True, slots=True)
class V075ConstructionAccountingRegistrySuccessorV3:
    _issuer: InitVar[object]
    upstream_closure_id: str
    upstream_verification_id: str
    multiround_result_id: str
    terminal_derivation_registry_id: str
    counter_registry: Mapping[str, Any]
    stage_profile: Mapping[str, Any]
    comparison_profile: Mapping[str, Any]
    actual_projection_profile: Mapping[str, Any]
    legacy_migration_profile: Mapping[str, Any]
    _successor_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SUCCESSOR_ISSUER:
            _fail("construction accounting successor is caller-minted")
        for value in (
            self.upstream_closure_id,
            self.upstream_verification_id,
            self.multiround_result_id,
            self.terminal_derivation_registry_id,
        ):
            parse_content_id(value)
        exact = freeze_construction_accounting_registry_successor_v3()
        for value, label in (
            (self.counter_registry, "counter_registry"),
            (self.stage_profile, "stage_profile"),
            (self.comparison_profile, "comparison_profile"),
            (
                self.actual_projection_profile,
                "actual_projection_profile",
            ),
            (
                self.legacy_migration_profile,
                "legacy_migration_profile",
            ),
        ):
            if type(value) is not dict or value != exact[label]:
                _fail(f"{label} differs from exact successor schema")
        for field_name in (
            "counter_registry",
            "stage_profile",
            "comparison_profile",
            "actual_projection_profile",
            "legacy_migration_profile",
        ):
            object.__setattr__(
                self,
                field_name,
                _freeze_json(getattr(self, field_name)),
            )
        object.__setattr__(
            self,
            "_successor_id",
            content_id(
                V075_CONSTRUCTION_ACCOUNTING_REGISTRY_SUCCESSOR_V3_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        migration = self.legacy_migration_profile
        return {
            "schema": (
                "acfqp.v075_construction_accounting_registry_successor.v3"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "upstream_profile_key": UPSTREAM_PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "upstream_closure_id": self.upstream_closure_id,
            "upstream_verification_id": self.upstream_verification_id,
            "multiround_result_id": self.multiround_result_id,
            "multiround_status": "CHILD_ACTION_ROW_CAP_EXCEEDED",
            "terminal_derivation_registry_id": (
                self.terminal_derivation_registry_id
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
            "legacy_migration_profile": _thaw_json(migration),
            "legacy_migration_profile_id": migration[
                "migration_profile_id"
            ],
            "v2_prefix_leaf_count": 69,
            "v2_prefix_preserved_exactly": True,
            "v3_addition_count": 47,
            "v3_leaf_count": EXPECTED_V3_LEAF_COUNT,
            "v3_operational_leaf_count": (
                EXPECTED_V3_OPERATIONAL_LEAF_COUNT
            ),
            "v3_required_leaf_count": EXPECTED_V3_REQUIRED_LEAF_COUNT,
            "registered_stage_count": EXPECTED_V3_STAGE_COUNT,
            "projection_term_count": (
                EXPECTED_V3_OPERATIONAL_LEAF_COUNT
            ),
            "legacy_catalogue_entry_count": 95,
            "legacy_distinct_path_count": (
                EXPECTED_LEGACY_DISTINCT_PATH_COUNT
            ),
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

    @property
    def successor_id(self) -> str:
        return self._successor_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "successor_id": self.successor_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "construction accounting successor closures are in-memory-only"
        )


def materialize_v075_construction_accounting_registry_successor_v3(
    *,
    upstream: (
        schema_verifier
        .V075ConstructionAccountingSchemaIndependentVerificationV2
    ),
    schema_closure_bytes: bytes,
) -> V075ConstructionAccountingRegistrySuccessorV3:
    """Bind the exact additive successor to independently verified 1.85."""

    try:
        schema = _verify_upstream(
            upstream=upstream,
            schema_closure_bytes=schema_closure_bytes,
        )
        registry = official_counter_registry_v3()
        stage = official_stage_profile_v3(registry)
        comparison = official_comparison_profile_v3(registry)
        actual = official_actual_projection_profile_v3(
            registry, comparison
        )
        migration = official_legacy_migration_profile_v3(registry)
        if (
            registry.registry_id != EXPECTED_COUNTER_REGISTRY_V3_ID
            or stage.stage_profile_id != EXPECTED_STAGE_PROFILE_V3_ID
            or comparison.comparison_profile_id
            != EXPECTED_COMPARISON_PROFILE_V3_ID
            or actual.actual_projection_profile_id
            != EXPECTED_ACTUAL_PROJECTION_PROFILE_V3_ID
            or migration.migration_profile_id
            != EXPECTED_LEGACY_MIGRATION_PROFILE_V3_ID
        ):
            _fail("registered construction-accounting v3 identities changed")
        frozen = freeze_construction_accounting_registry_successor_v3()
        return V075ConstructionAccountingRegistrySuccessorV3(
            _SUCCESSOR_ISSUER,
            upstream.closure_id,
            upstream.verification_id,
            schema["multiround_result_id"],
            schema["terminal_derivation_registry_id"],
            frozen["counter_registry"],
            frozen["stage_profile"],
            frozen["comparison_profile"],
            frozen["actual_projection_profile"],
            frozen["legacy_migration_profile"],
        )
    except Exception:
        raise V075ConstructionAccountingSuccessorV3Violation(
            _REPLAY_MISMATCH
        ) from None


def assert_v075_construction_accounting_successor_production_gate_v3(
    successor: V075ConstructionAccountingRegistrySuccessorV3,
) -> NoReturn:
    if type(successor) is not V075ConstructionAccountingRegistrySuccessorV3:
        _fail("production gate rejects successor duck types")
    _ = successor.successor_id
    raise V075ConstructionAccountingSuccessorProductionV3NotReady(
        "contract 1.86 repairs registry/stage coverage only; live native "
        "operation-site instrumentation, lifecycle attestations, vectors, "
        "typed terminal/occurrence/campaign closure, production, fresh "
        "science and certificates remain locked"
    )


__all__ = [
    "EXPECTED_ACTUAL_PROJECTION_PROFILE_V3_ID",
    "EXPECTED_COMPARISON_PROFILE_V3_ID",
    "EXPECTED_COUNTER_REGISTRY_V3_ID",
    "EXPECTED_LEGACY_MIGRATION_PROFILE_V3_ID",
    "EXPECTED_STAGE_PROFILE_V3_ID",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "V075ConstructionAccountingRegistrySuccessorV3",
    "V075ConstructionAccountingSuccessorProductionV3NotReady",
    "V075ConstructionAccountingSuccessorV3Violation",
    "assert_v075_construction_accounting_successor_production_gate_v3",
    "materialize_v075_construction_accounting_registry_successor_v3",
]
