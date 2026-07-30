"""Construction-only native-accounting boundary for V0-075.

Contract 1.84 starts by independently replaying the exact raw contract-1.83
source/code-provenance artifact.  It then freezes the accounting boundary
without executing an occurrence, opening an observer, reading target data, or
minting a work vector or terminal certificate.

This is deliberately a *foundation*.  It inventories the existing Phase-3E
registry and five V0-075 custom counter catalogues, reserves a new
``acfqp_counter_registry_v2`` instead of mutating v1, separates initial
BUILD/ACQUISITION from REBUILD, and freezes terminal derivation.  Legacy
custom counters remain legacy custom counters: neither their individual
documents nor caller totals are accepted as ``CounterRecordV1`` evidence.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
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
from acfqp import v075_route_native_backend_core_v1 as route_core
from acfqp import v075_portable_semantic_registry_v2 as portable_registry
from acfqp import (
    v075_construction_source_code_provenance_independent_verifier_v2
    as source_verifier,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.84.0"
PROFILE_KEY = "v075_construction_native_accounting_foundation_v2"
UPSTREAM_PROFILE_KEY = (
    "v075_construction_source_code_provenance_v2"
)

COUNTER_REGISTRY_V2_KEY = "acfqp_counter_registry_v2"
COUNTER_REGISTRY_V1_MUTATION_ALLOWED = False
LEGACY_CUSTOM_COUNTER_AS_COUNTER_RECORD_ALLOWED = False
CALLER_CUSTOM_TOTAL_AS_COUNTER_RECORD_ALLOWED = False
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
OBSERVER_OPEN_ALLOWED = False
TARGET_ACCESS_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
PLANNER_WORKER_LAUNCH_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_NATIVE_ACCOUNTING_FOUNDATION_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_ACCOUNTING_BOUNDARY_FROZEN_"
    "ALL_PATH_ACCOUNTING_AND_CAMPAIGN_CLOSURE_LOCKED"
)

DOMAIN_TAGS = MappingProxyType(
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
    }
)

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("contract 1.84 content domains overlap")

_REPLAY_MISMATCH = (
    "construction native-accounting foundation did not match registered "
    "evidence"
)


class V075ConstructionNativeAccountingFoundationV2Violation(ValueError):
    """Raw provenance or construction accounting replay failed."""


class V075ConstructionNativeAccountingProductionV2NotReady(RuntimeError):
    """The construction foundation cannot authorize production."""


class V075CounterCoverageClassificationV2(str, Enum):
    EXACT_EXISTING_LEAF = "EXACT_EXISTING_LEAF"
    RESERVED_V2_PATH_NAME = "RESERVED_V2_PATH_NAME"
    NOT_INSTRUMENTED = "NOT_INSTRUMENTED"


class V075AccountingRolePresenceV2(str, Enum):
    PRESENT_FOUNDATION = "PRESENT_FOUNDATION"
    FUTURE_REQUIRED = "FUTURE_REQUIRED"


def _fail(message: str) -> NoReturn:
    raise V075ConstructionNativeAccountingFoundationV2Violation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ConstructionNativeAccountingFoundationV2Violation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _text(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        _fail(f"{label} must be canonical nonempty text")
    return value


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ConstructionNativeAccountingFoundationV2Violation(
            str(error)
        ) from error


def _sequence_digest(values: tuple[str, ...]) -> str:
    return hashlib.sha256(canonical_json_bytes(list(values))).hexdigest()


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
        raise V075ConstructionNativeAccountingFoundationV2Violation(
            f"{label} is not strict UTF-8 JSON"
        ) from error
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != raw
    ):
        _fail(f"{label} is not one canonical JSON object")
    return document


@dataclass(frozen=True, slots=True)
class V075CounterCoverageRowV2:
    source_family: str
    source_schema: str
    source_path: str
    classification: V075CounterCoverageClassificationV2
    target_path: str | None
    legacy_custom_counter: bool
    definition_registered_in_v1: bool
    counter_record_v1_compatible: bool
    currently_instrumented_for_registry_v2: bool

    def __post_init__(self) -> None:
        _text(self.source_family, "coverage source family")
        _text(self.source_schema, "coverage source schema")
        _text(self.source_path, "coverage source path")
        try:
            classification = V075CounterCoverageClassificationV2(
                self.classification
            )
        except (TypeError, ValueError) as error:
            raise V075ConstructionNativeAccountingFoundationV2Violation(
                "unknown coverage classification"
            ) from error
        object.__setattr__(self, "classification", classification)
        if self.target_path is not None:
            _text(self.target_path, "coverage target path")
        for value in (
            self.legacy_custom_counter,
            self.definition_registered_in_v1,
            self.counter_record_v1_compatible,
            self.currently_instrumented_for_registry_v2,
        ):
            if type(value) is not bool:
                _fail("coverage flags must be exact booleans")
        if classification is V075CounterCoverageClassificationV2.EXACT_EXISTING_LEAF:
            if (
                self.target_path != self.source_path
                or self.legacy_custom_counter
                or not self.definition_registered_in_v1
                or not self.counter_record_v1_compatible
                or self.currently_instrumented_for_registry_v2
            ):
                _fail("exact-existing coverage row changed semantics")
        elif (
            classification
            is V075CounterCoverageClassificationV2.RESERVED_V2_PATH_NAME
        ):
            if (
                self.target_path is None
                or self.legacy_custom_counter
                or self.definition_registered_in_v1
                or self.counter_record_v1_compatible
                or self.currently_instrumented_for_registry_v2
            ):
                _fail("reserved v2 leaf falsely claims instrumentation")
        else:
            if self.currently_instrumented_for_registry_v2:
                _fail("not-instrumented row is malformed")
            if self.legacy_custom_counter:
                if (
                    self.target_path is not None
                    or self.definition_registered_in_v1
                    or self.counter_record_v1_compatible
                ):
                    _fail("historical custom row acquired native semantics")
            elif (
                self.target_path != self.source_path
                or not self.definition_registered_in_v1
                or not self.counter_record_v1_compatible
            ):
                _fail("missing-recorder row lost its existing v1 definition")

    def to_document(self) -> dict[str, Any]:
        return {
            "source_family": self.source_family,
            "source_schema": self.source_schema,
            "source_path": self.source_path,
            "classification": self.classification.value,
            "target_path": self.target_path,
            "legacy_custom_counter": self.legacy_custom_counter,
            "definition_registered_in_v1": self.definition_registered_in_v1,
            "counter_record_v1_compatible": (
                self.counter_record_v1_compatible
            ),
            "currently_instrumented_for_registry_v2": (
                self.currently_instrumented_for_registry_v2
            ),
        }


@dataclass(frozen=True, slots=True)
class V075AccountingBoundaryProfileV2:
    base_counter_registry_id: str
    base_comparison_profile_id: str
    base_actual_projection_profile_id: str
    base_leaf_count: int
    base_operational_leaf_count: int
    future_counter_registry_key: str
    initial_build_paths: tuple[str, ...]
    initial_acquisition_paths: tuple[str, ...]
    rebuild_paths: tuple[str, ...]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.base_counter_registry_id, "base counter registry")
        _cid(self.base_comparison_profile_id, "base comparison profile")
        _cid(
            self.base_actual_projection_profile_id,
            "base actual projection profile",
        )
        if (
            type(self.base_leaf_count) is not int
            or self.base_leaf_count <= 0
            or type(self.base_operational_leaf_count) is not int
            or not 0 < self.base_operational_leaf_count <= self.base_leaf_count
            or self.future_counter_registry_key != COUNTER_REGISTRY_V2_KEY
            or self.base_counter_registry_id
            != EXPECTED_COUNTER_REGISTRY_V1_ID
            or self.base_comparison_profile_id
            != EXPECTED_COMPARISON_PROFILE_V1_ID
            or self.base_actual_projection_profile_id
            != EXPECTED_ACTUAL_PROJECTION_PROFILE_V1_ID
            or self.base_leaf_count != 49
            or self.base_operational_leaf_count != 34
        ):
            _fail("accounting boundary cardinality or registry key changed")
        for rows, label in (
            (self.initial_build_paths, "initial build"),
            (self.initial_acquisition_paths, "initial acquisition"),
            (self.rebuild_paths, "rebuild"),
        ):
            if (
                type(rows) is not tuple
                or tuple(sorted(rows)) != rows
                or len(set(rows)) != len(rows)
                or not rows
            ):
                _fail(f"{label} paths must be nonempty unique and sorted")
            for path in rows:
                _text(path, f"{label} path")
        if (
            set(self.initial_build_paths) & set(self.rebuild_paths)
            or set(self.initial_acquisition_paths) & set(self.rebuild_paths)
            or set(self.initial_build_paths)
            & set(self.initial_acquisition_paths)
            or any(path.startswith("rebuild.") for path in self.initial_build_paths)
            or any(
                path.startswith("rebuild.")
                for path in self.initial_acquisition_paths
            )
        ):
            _fail("initial BUILD/ACQUISITION was aliased to REBUILD")
        base = accounting.official_counter_registry_v1()
        comparison = accounting.official_comparison_profile_v1(base)
        projection = actual.official_actual_projection_profile_v1(
            base, comparison
        )
        reserved_paths = set(
            (*self.initial_build_paths, *self.initial_acquisition_paths)
        )
        base_paths = {leaf.path for leaf in base.leaves}
        legacy_custom_paths = set().union(
            set(route_core.COUNTER_PATHS),
            set(batch_native.BATCH_NATIVE_COUNTER_PATHS),
            set(planner.PLANNER_COUNTER_PATHS),
            set(worker.REGISTERED_COUNTER_PATHS),
            set(direct.DIRECT_PIPELINE_COUNTER_PATHS),
        )
        if (
            self.base_counter_registry_id != base.registry_id
            or self.base_comparison_profile_id
            != comparison.comparison_profile_id
            or self.base_actual_projection_profile_id
            != projection.actual_projection_profile_id
            or self.base_leaf_count != len(base.leaves)
            or self.base_operational_leaf_count
            != len(base.operational_leaves)
            or self.initial_build_paths
            != tuple(sorted(_INITIAL_BUILD_PATHS))
            or self.initial_acquisition_paths
            != tuple(sorted(_INITIAL_ACQUISITION_PATHS))
            or self.rebuild_paths
            != tuple(
                sorted(
                    leaf.path
                    for leaf in base.leaves
                    if leaf.path.startswith("rebuild.")
                )
            )
            or len(legacy_custom_paths)
            != EXPECTED_LEGACY_CUSTOM_DISTINCT_PATH_COUNT
            or reserved_paths & base_paths
            or reserved_paths & legacy_custom_paths
        ):
            _fail("accounting boundary differs from exact authorities")
        object.__setattr__(self, "_profile_id", _hash("boundary", self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_accounting_boundary_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "base_counter_registry_key": accounting.COUNTER_REGISTRY_KEY,
            "base_counter_registry_id": self.base_counter_registry_id,
            "base_comparison_profile_key": (
                accounting.COMPARISON_PROFILE_KEY
            ),
            "base_comparison_profile_id": self.base_comparison_profile_id,
            "base_actual_projection_profile_key": (
                actual.ACTUAL_PROJECTION_PROFILE_KEY
            ),
            "base_actual_projection_profile_id": (
                self.base_actual_projection_profile_id
            ),
            "base_leaf_count": self.base_leaf_count,
            "base_operational_leaf_count": self.base_operational_leaf_count,
            "future_counter_registry_key": self.future_counter_registry_key,
            "counter_registry_v1_mutation_allowed": False,
            "legacy_custom_counter_as_counter_record_allowed": False,
            "caller_custom_total_as_counter_record_allowed": False,
            "initial_build_paths": list(self.initial_build_paths),
            "initial_acquisition_paths": list(
                self.initial_acquisition_paths
            ),
            "rebuild_paths": list(self.rebuild_paths),
            "initial_build_is_rebuild": False,
            "initial_acquisition_is_rebuild": False,
            "reserved_v2_path_intersection_with_v1": 0,
            "reserved_v2_path_intersection_with_legacy_custom": 0,
            "legacy_custom_distinct_path_count": (
                EXPECTED_LEGACY_CUSTOM_DISTINCT_PATH_COUNT
            ),
            "counter_registry_v2_materialized": False,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


@dataclass(frozen=True, slots=True)
class V075CounterCoverageMatrixV2:
    boundary_profile_id: str
    route_core_source_path_digest: str
    batch_native_source_path_digest: str
    planner_source_path_digest: str
    worker_source_path_digest: str
    direct_source_path_digest: str
    rows: tuple[V075CounterCoverageRowV2, ...]
    _matrix_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.boundary_profile_id, "coverage boundary")
        _cid(self.route_core_source_path_digest, "route-core path digest")
        _cid(self.batch_native_source_path_digest, "batch path digest")
        _cid(self.planner_source_path_digest, "planner path digest")
        _cid(self.worker_source_path_digest, "worker path digest")
        _cid(self.direct_source_path_digest, "direct path digest")
        if (
            type(self.rows) is not tuple
            or not self.rows
            or any(type(row) is not V075CounterCoverageRowV2 for row in self.rows)
            or tuple(
                (row.source_family, row.source_path) for row in self.rows
            )
            != tuple(
                sorted(
                    (row.source_family, row.source_path)
                    for row in self.rows
                )
            )
            or len(
                {(row.source_family, row.source_path) for row in self.rows}
            )
            != len(self.rows)
        ):
            _fail("counter coverage rows are incomplete or reordered")
        exact = tuple(
            row for row in self.rows
            if row.classification
            is V075CounterCoverageClassificationV2.EXACT_EXISTING_LEAF
        )
        reserved = tuple(
            row for row in self.rows
            if row.classification
            is V075CounterCoverageClassificationV2.RESERVED_V2_PATH_NAME
        )
        missing = tuple(
            row for row in self.rows
            if row.classification
            is V075CounterCoverageClassificationV2.NOT_INSTRUMENTED
        )
        base = accounting.official_counter_registry_v1()
        base_paths = {leaf.path for leaf in base.leaves}
        custom_catalogues = (
            route_core.COUNTER_PATHS,
            batch_native.BATCH_NATIVE_COUNTER_PATHS,
            planner.PLANNER_COUNTER_PATHS,
            worker.REGISTERED_COUNTER_PATHS,
            direct.DIRECT_PIPELINE_COUNTER_PATHS,
        )
        reserved_paths = {
            row.source_path
            for row in reserved
        }
        legacy_custom_paths = set().union(
            *(set(paths) for paths in custom_catalogues)
        )
        if (
            len(exact) != len(base.leaves)
            or {row.source_path for row in exact}
            != base_paths
            or len(reserved)
            != len(_RESERVED_COUNTER_REGISTRY_V2_PATHS)
            or not missing
            or _sequence_digest(route_core.COUNTER_PATHS)
            != self.route_core_source_path_digest
            or _sequence_digest(batch_native.BATCH_NATIVE_COUNTER_PATHS)
            != self.batch_native_source_path_digest
            or _sequence_digest(planner.PLANNER_COUNTER_PATHS)
            != self.planner_source_path_digest
            or _sequence_digest(worker.REGISTERED_COUNTER_PATHS)
            != self.worker_source_path_digest
            or _sequence_digest(direct.DIRECT_PIPELINE_COUNTER_PATHS)
            != self.direct_source_path_digest
            or any(base_paths & set(paths) for paths in custom_catalogues)
            or reserved_paths & base_paths
            or reserved_paths & legacy_custom_paths
            or len(legacy_custom_paths)
            != EXPECTED_LEGACY_CUSTOM_DISTINCT_PATH_COUNT
            or (
                len(route_core.COUNTER_PATHS),
                self.route_core_source_path_digest,
            )
            != EXPECTED_CUSTOM_CATALOGUE_DIGESTS["route_core"]
            or (
                len(batch_native.BATCH_NATIVE_COUNTER_PATHS),
                self.batch_native_source_path_digest,
            )
            != EXPECTED_CUSTOM_CATALOGUE_DIGESTS["batch_native"]
            or (
                len(planner.PLANNER_COUNTER_PATHS),
                self.planner_source_path_digest,
            )
            != EXPECTED_CUSTOM_CATALOGUE_DIGESTS["planner"]
            or (
                len(worker.REGISTERED_COUNTER_PATHS),
                self.worker_source_path_digest,
            )
            != EXPECTED_CUSTOM_CATALOGUE_DIGESTS["worker"]
            or (
                len(direct.DIRECT_PIPELINE_COUNTER_PATHS),
                self.direct_source_path_digest,
            )
            != EXPECTED_CUSTOM_CATALOGUE_DIGESTS["direct"]
        ):
            _fail("counter coverage catalogue changed")
        if self.rows != _coverage_rows(base):
            _fail("counter coverage rows differ from exact source catalogues")
        object.__setattr__(self, "_matrix_id", _hash("coverage", self._payload()))

    def _payload(self) -> dict[str, Any]:
        counts = {
            item.value: sum(
                row.classification is item for row in self.rows
            )
            for item in V075CounterCoverageClassificationV2
        }
        return {
            "schema": "acfqp.v075_counter_coverage_matrix.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "boundary_profile_id": self.boundary_profile_id,
            "base_counter_registry_key": accounting.COUNTER_REGISTRY_KEY,
            "future_counter_registry_key": COUNTER_REGISTRY_V2_KEY,
            "route_core_source_schema": (
                "acfqp.v075_route_native_backend_counter.v1"
            ),
            "route_core_source_path_count": len(route_core.COUNTER_PATHS),
            "route_core_source_path_digest": (
                self.route_core_source_path_digest
            ),
            "batch_native_source_schema": (
                "acfqp.v075_batch_native_backend_counter.v1"
            ),
            "batch_native_source_path_count": len(
                batch_native.BATCH_NATIVE_COUNTER_PATHS
            ),
            "batch_native_source_path_digest": (
                self.batch_native_source_path_digest
            ),
            "planner_source_schema": (
                "acfqp.v075_support_planner_counter.v1"
            ),
            "planner_source_path_count": len(planner.PLANNER_COUNTER_PATHS),
            "planner_source_path_digest": self.planner_source_path_digest,
            "worker_source_schema": (
                "acfqp.v075_registered_worker_counter.v1"
            ),
            "worker_source_path_count": len(
                worker.REGISTERED_COUNTER_PATHS
            ),
            "worker_source_path_digest": self.worker_source_path_digest,
            "direct_source_schema": (
                "acfqp.v075_integrated_direct_counter.v1"
            ),
            "direct_source_path_count": len(
                direct.DIRECT_PIPELINE_COUNTER_PATHS
            ),
            "direct_source_path_digest": self.direct_source_path_digest,
            "classification_counts": counts,
            "rows": [row.to_document() for row in self.rows],
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
                _CURRENT_ROOT_ONLY_CRITICAL_RECORDER_GAPS
            ),
            "current_root_only_missing_recorder_paths": list(
                _CURRENT_ROOT_ONLY_CRITICAL_RECORDER_GAPS
            ),
            "current_root_only_missing_recorder_path_digest": (
                _sequence_digest(_CURRENT_ROOT_ONLY_CRITICAL_RECORDER_GAPS)
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

    @property
    def matrix_id(self) -> str:
        return self._matrix_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "matrix_id": self.matrix_id}


@dataclass(frozen=True, slots=True)
class V075AccountingRoleDeclarationV2:
    role: str
    schema: str
    presence: V075AccountingRolePresenceV2

    def __post_init__(self) -> None:
        _text(self.role, "accounting companion role")
        _text(self.schema, "accounting companion schema")
        try:
            presence = V075AccountingRolePresenceV2(self.presence)
        except (TypeError, ValueError) as error:
            raise V075ConstructionNativeAccountingFoundationV2Violation(
                "unknown companion role presence"
            ) from error
        object.__setattr__(self, "presence", presence)

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "schema": self.schema,
            "presence": self.presence.value,
        }


@dataclass(frozen=True, slots=True)
class V075AccountingRoleRegistryV2:
    portable_semantic_registry_id: str
    portable_role_names: tuple[str, ...]
    companion_roles: tuple[V075AccountingRoleDeclarationV2, ...]
    _registry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(
            self.portable_semantic_registry_id,
            "portable semantic registry",
        )
        if (
            type(self.portable_role_names) is not tuple
            or self.portable_semantic_registry_id
            != EXPECTED_PORTABLE_SEMANTIC_REGISTRY_ID
            or len(self.portable_role_names) != 67
            or tuple(sorted(self.portable_role_names))
            != self.portable_role_names
            or len(set(self.portable_role_names)) != 67
            or type(self.companion_roles) is not tuple
            or not self.companion_roles
            or tuple(item.role for item in self.companion_roles)
            != tuple(sorted(item.role for item in self.companion_roles))
            or len({item.role for item in self.companion_roles})
            != len(self.companion_roles)
            or any(
                type(item) is not V075AccountingRoleDeclarationV2
                for item in self.companion_roles
            )
            or set(self.portable_role_names)
            & {item.role for item in self.companion_roles}
        ):
            _fail("outer accounting role registry is malformed")
        expected_present = {
            "ACCOUNTING_BOUNDARY_PROFILE",
            "ACCOUNTING_READINESS_ATTESTATION",
            "ACCOUNTING_ROLE_REGISTRY",
            "COUNTER_COVERAGE_MATRIX",
            "TERMINAL_DERIVATION_REGISTRY",
        }
        actual_present = {
            item.role
            for item in self.companion_roles
            if item.presence
            is V075AccountingRolePresenceV2.PRESENT_FOUNDATION
        }
        if actual_present != expected_present:
            _fail("foundation companion role presence changed")
        portable = portable_registry.freeze_v075_portable_semantic_registry_v2()
        expected_companions = tuple(
            V075AccountingRoleDeclarationV2(
                role,
                schema,
                (
                    V075AccountingRolePresenceV2.PRESENT_FOUNDATION
                    if present
                    else V075AccountingRolePresenceV2.FUTURE_REQUIRED
                ),
            )
            for role, schema, present in sorted(_COMPANION_ROLES)
        )
        if (
            self.portable_semantic_registry_id != portable.registry_id
            or self.portable_role_names
            != tuple(item.role for item in portable.declarations)
            or self.companion_roles != expected_companions
        ):
            _fail("accounting role registry differs from exact outer roles")
        object.__setattr__(
            self, "_registry_id", _hash("role_registry", self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_accounting_role_registry.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_semantic_registry_id": (
                self.portable_semantic_registry_id
            ),
            "portable_role_count": len(self.portable_role_names),
            "portable_role_names_digest": _sequence_digest(
                self.portable_role_names
            ),
            "portable_role_names": list(self.portable_role_names),
            "portable_registry_modified": False,
            "companion_role_scope": (
                "OUTER_ACCOUNTING_AND_CLOSURE_COMPANIONS_ONLY"
            ),
            "companion_roles": [
                item.to_document() for item in self.companion_roles
            ],
        }

    @property
    def registry_id(self) -> str:
        return self._registry_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}


@dataclass(frozen=True, slots=True)
class V075TerminalDerivationRegistryV2:
    generic_terminal_mapping: tuple[tuple[str, str], ...]
    specific_cause: str
    specific_terminal_scope: str
    specific_derived_class: str
    specific_derived_code: str
    _registry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.generic_terminal_mapping) is not tuple
            or self.generic_terminal_mapping
            != EXPECTED_GENERIC_TERMINAL_MAPPING
            or len(
                {code for code, _class in self.generic_terminal_mapping}
            )
            != len(self.generic_terminal_mapping)
            or {code for code, _class in self.generic_terminal_mapping}
            != {item.value for item in routing.TerminalCode}
            or any(
                routing._TERMINAL_CLASS_BY_CODE[  # noqa: SLF001
                    routing.TerminalCode(code)
                ].value
                != terminal_class
                for code, terminal_class in self.generic_terminal_mapping
            )
            or self.specific_cause
            != multiround_owner.V075ObserverSignedMultiroundTerminalStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED.value
            or multiround_owner.PROFILE_KEY
            != EXPECTED_MULTIROUND_SOURCE_PROFILE
            or self.specific_terminal_scope != "ROUTE_ATTEMPT"
            or self.specific_derived_class
            != routing.TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE.value
            or self.specific_derived_code
            != routing.TerminalCode.ATTEMPT_BUDGET_EXHAUSTED.value
        ):
            _fail("terminal derivation registry changed")
        object.__setattr__(
            self,
            "_registry_id",
            _hash("terminal_registry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_terminal_derivation_registry.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "generic_terminal_artifact_schema": (
                "acfqp.terminal_artifact.v1"
            ),
            "generic_terminal_mapping": [
                {"terminal_code": code, "terminal_class": terminal_class}
                for code, terminal_class in self.generic_terminal_mapping
            ],
            "specific_derivations": [
                {
                    "source_profile": (
                        EXPECTED_MULTIROUND_SOURCE_PROFILE
                    ),
                    "source_cause": self.specific_cause,
                    "derived_terminal_scope": self.specific_terminal_scope,
                    "derived_terminal_class": self.specific_derived_class,
                    "derived_terminal_code": self.specific_derived_code,
                    "specific_cause_retained": True,
                    "infeasibility_mapping_allowed": False,
                    "caller_terminal_self_report_authoritative": False,
                }
            ],
            "terminal_classification_must_be_recomputed": True,
            "campaign_closure_materialized": False,
        }

    @property
    def registry_id(self) -> str:
        return self._registry_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}


_READINESS_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075AccountingReadinessAttestationV2:
    _issuer: InitVar[object]
    source_code_provenance_id: str
    source_code_provenance_sha256: str
    source_code_provenance_byte_count: int
    upstream_verification_id: str
    portable_bundle_id: str
    public_context_closure_id: str
    semantic_terminal_closure_id: str
    repository_closure_id: str
    source_archive_binding_id: str
    provenance_dag_id: str
    runtime_source_closure_id: str
    source_archive_id: str
    runtime_lock_id: str
    compile_verification_id: str
    multiround_result_id: str
    multiround_status: str
    boundary_profile: V075AccountingBoundaryProfileV2
    coverage_matrix: V075CounterCoverageMatrixV2
    role_registry: V075AccountingRoleRegistryV2
    terminal_registry: V075TerminalDerivationRegistryV2
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.source_code_provenance_id, "source provenance closure"),
            (self.source_code_provenance_sha256, "source provenance bytes"),
            (self.upstream_verification_id, "source provenance verification"),
            (self.portable_bundle_id, "portable occurrence bundle"),
            (self.public_context_closure_id, "public context closure"),
            (self.semantic_terminal_closure_id, "semantic terminal closure"),
            (self.repository_closure_id, "repository closure"),
            (self.source_archive_binding_id, "source archive binding"),
            (self.provenance_dag_id, "source provenance DAG"),
            (self.runtime_source_closure_id, "runtime source closure"),
            (self.source_archive_id, "deterministic source archive"),
            (self.runtime_lock_id, "runtime lock"),
            (self.compile_verification_id, "sealed compile verification"),
            (self.multiround_result_id, "multiround result"),
        ):
            _cid(value, label)
        if (
            _issuer is not _READINESS_ISSUER
            or type(self.source_code_provenance_byte_count) is not int
            or self.source_code_provenance_byte_count <= 0
            or self.multiround_status != "CHILD_ACTION_ROW_CAP_EXCEEDED"
            or type(self.boundary_profile)
            is not V075AccountingBoundaryProfileV2
            or type(self.coverage_matrix)
            is not V075CounterCoverageMatrixV2
            or type(self.role_registry)
            is not V075AccountingRoleRegistryV2
            or type(self.terminal_registry)
            is not V075TerminalDerivationRegistryV2
            or self.coverage_matrix.boundary_profile_id
            != self.boundary_profile.profile_id
        ):
            _fail("accounting readiness attestation is caller-minted")
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("readiness", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_accounting_readiness_attestation.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "upstream_profile_key": UPSTREAM_PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "source_code_provenance_id": self.source_code_provenance_id,
            "source_code_provenance_sha256": (
                self.source_code_provenance_sha256
            ),
            "source_code_provenance_byte_count": (
                self.source_code_provenance_byte_count
            ),
            "upstream_verification_id": self.upstream_verification_id,
            "portable_bundle_id": self.portable_bundle_id,
            "public_context_closure_id": self.public_context_closure_id,
            "semantic_terminal_closure_id": (
                self.semantic_terminal_closure_id
            ),
            "repository_closure_id": self.repository_closure_id,
            "source_archive_binding_id": self.source_archive_binding_id,
            "provenance_dag_id": self.provenance_dag_id,
            "runtime_source_closure_id": self.runtime_source_closure_id,
            "source_archive_id": self.source_archive_id,
            "runtime_lock_id": self.runtime_lock_id,
            "compile_verification_id": self.compile_verification_id,
            "multiround_result_id": self.multiround_result_id,
            "multiround_status": self.multiround_status,
            "boundary_profile": self.boundary_profile.to_document(),
            "boundary_profile_id": self.boundary_profile.profile_id,
            "coverage_matrix": self.coverage_matrix.to_document(),
            "coverage_matrix_id": self.coverage_matrix.matrix_id,
            "role_registry": self.role_registry.to_document(),
            "role_registry_id": self.role_registry.registry_id,
            "terminal_registry": self.terminal_registry.to_document(),
            "terminal_registry_id": self.terminal_registry.registry_id,
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
            "raw_contract_183_prefix_subprocess_io_hash_peak_"
            "work_fully_accounted": False,
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

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("accounting readiness attestations are in-memory-only")


_INITIAL_BUILD_PATHS = (
    "build.initial_interval_log_search_evaluations",
    "build.initial_interval_row_evaluations",
    "build.initial_model_rows_built",
    "build.initial_policy_assignments_evaluated",
    "build.initial_semantic_record_replays",
    "build.initial_semantic_role_closures",
    "build.initial_source_units_compiled",
)
_INITIAL_ACQUISITION_PATHS = (
    "acquisition.initial_observer_accepted_draws",
    "acquisition.initial_observer_random_word_calls",
    "acquisition.initial_observer_rejections",
    "acquisition.initial_outcome_aggregate_rows",
    "acquisition.initial_signed_batches",
    "acquisition.initial_support_freezes",
)
_RESERVED_COUNTER_REGISTRY_V2_PATHS = tuple(
    sorted((*_INITIAL_BUILD_PATHS, *_INITIAL_ACQUISITION_PATHS))
)
_CURRENT_ROOT_ONLY_CRITICAL_RECORDER_GAPS = (
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
    ("ACCOUNTING_BOUNDARY_PROFILE", "acfqp.v075_accounting_boundary_profile.v2", True),
    ("ACCOUNTING_READINESS_ATTESTATION", "acfqp.v075_accounting_readiness_attestation.v2", True),
    ("ACCOUNTING_ROLE_REGISTRY", "acfqp.v075_accounting_role_registry.v2", True),
    ("COMPLETE_BUNDLE_VERIFICATION", "acfqp.v075_complete_bundle_verification.v2", False),
    ("COUNTER_COVERAGE_MATRIX", "acfqp.v075_counter_coverage_matrix.v2", True),
    ("COUNTER_REGISTRY_V2", "acfqp.counter_registry.v2", False),
    ("LOADED_SOURCE_RECEIPT", "acfqp.v075_loaded_source_receipt.v2", False),
    ("LOGICAL_OCCURRENCE_CLOSURE", "acfqp.v075_logical_occurrence_closure.v2", False),
    ("OCCURRENCE_WORK_VECTOR", "acfqp.work_vector.v2", False),
    ("ACTUAL_PROJECTION", "acfqp.actual_projection.v2", False),
    ("CAMPAIGN_CLOSURE", "acfqp.v075_campaign_closure.v2", False),
    ("TERMINAL_ARTIFACT", "acfqp.terminal_artifact.v2", False),
    ("TERMINAL_DERIVATION_REGISTRY", "acfqp.v075_terminal_derivation_registry.v2", True),
)


def _coverage_rows(
    registry: accounting.CounterRegistryV1,
) -> tuple[V075CounterCoverageRowV2, ...]:
    rows: list[V075CounterCoverageRowV2] = []
    for leaf in registry.leaves:
        rows.append(
            V075CounterCoverageRowV2(
                "PHASE3E_COUNTER_REGISTRY_V1",
                "acfqp.counter_record.v1",
                leaf.path,
                V075CounterCoverageClassificationV2.EXACT_EXISTING_LEAF,
                leaf.path,
                False,
                True,
                True,
                False,
            )
        )
    for path in _RESERVED_COUNTER_REGISTRY_V2_PATHS:
        rows.append(
            V075CounterCoverageRowV2(
                "RESERVED_COUNTER_REGISTRY_V2",
                "acfqp.counter_registry.v2",
                path,
                V075CounterCoverageClassificationV2.RESERVED_V2_PATH_NAME,
                path,
                False,
                False,
                False,
                False,
            )
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
                V075CounterCoverageRowV2(
                    family,
                    schema,
                    path,
                    V075CounterCoverageClassificationV2.NOT_INSTRUMENTED,
                    None,
                    True,
                    False,
                    False,
                    False,
                )
            )
    return tuple(sorted(rows, key=lambda row: (row.source_family, row.source_path)))


def _freeze_after_raw_183(
    *,
    upstream: (
        source_verifier
        .V075ConstructionSourceCodeProvenanceIndependentVerificationV2
    ),
    source_code_provenance_bytes: bytes,
    portable_bundle_bytes: bytes,
) -> V075AccountingReadinessAttestationV2:
    if (
        type(upstream)
        is not source_verifier
        .V075ConstructionSourceCodeProvenanceIndependentVerificationV2
    ):
        _fail("accounting foundation requires exact raw contract 1.83")
    source_document = _strict_document(
        source_code_provenance_bytes,
        label="verified source/code provenance",
    )
    if (
        source_document.get("closure_id") != upstream.closure_id
        or source_document.get("semantic_terminal_closure_id")
        != upstream.semantic_terminal_closure_id
        or source_document.get("repository_closure_id")
        != upstream.repository_closure_id
        or source_document.get("source_archive_binding_id")
        != upstream.source_archive_binding_id
        or source_document.get("provenance_dag_id")
        != upstream.provenance_dag_id
    ):
        _fail("upstream provenance component identities changed")
    archive_binding = source_document.get("source_archive_binding")
    if type(archive_binding) is not dict:
        _fail("source provenance omitted its archive binding")
    for field_name in (
        "runtime_source_closure_id",
        "source_archive_id",
        "runtime_lock_id",
        "compile_verification_id",
    ):
        _cid(
            archive_binding.get(field_name),
            f"source archive {field_name}",
        )
    if archive_binding.get("binding_id") != upstream.source_archive_binding_id:
        _fail("nested source archive binding identity changed")
    portable_bundle_id = _cid(
        source_document.get("portable_bundle_id"),
        "source-bound portable bundle",
    )
    public_context_closure_id = _cid(
        source_document.get("public_context_closure_id"),
        "source-bound public context closure",
    )
    bundle_document = _strict_document(
        portable_bundle_bytes,
        label="verified portable occurrence bundle",
        byte_cap=512 * 1024 * 1024,
    )
    records = bundle_document.get("artifact_records")
    if type(records) is not list:
        _fail("portable bundle omitted artifact records")
    if bundle_document.get("bundle_id") != portable_bundle_id:
        _fail("portable bundle identity differs from source provenance")
    multiround_rows = [
        row
        for row in records
        if type(row) is dict and row.get("role") == "MULTIROUND_RESULT"
    ]
    if len(multiround_rows) != 1:
        _fail("portable bundle lacks one multiround result")
    multiround_row = multiround_rows[0]
    raw_hex = multiround_row.get("canonical_artifact_bytes_hex")
    if type(raw_hex) is not str:
        _fail("multiround result bytes are absent")
    try:
        multiround_raw = bytes.fromhex(raw_hex)
    except ValueError as error:
        raise V075ConstructionNativeAccountingFoundationV2Violation(
            "multiround result bytes are not hexadecimal"
        ) from error
    if multiround_raw.hex() != raw_hex:
        _fail("multiround result bytes are not lowercase hexadecimal")
    multiround_document = _strict_document(
        multiround_raw,
        label="verified multiround result",
        byte_cap=64 * 1024 * 1024,
    )
    multiround_result_id = _cid(
        multiround_document.get("result_id"),
        "multiround result",
    )
    if (
        multiround_row.get("semantic_artifact_id")
        != multiround_result_id
        or multiround_document.get("status")
        != "CHILD_ACTION_ROW_CAP_EXCEEDED"
    ):
        _fail("registered root-only cap terminal changed")
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
        _fail("exact accounting_v1 registry identity changed")
    boundary = V075AccountingBoundaryProfileV2(
        registry.registry_id,
        comparison.comparison_profile_id,
        projection.actual_projection_profile_id,
        len(registry.leaves),
        len(registry.operational_leaves),
        COUNTER_REGISTRY_V2_KEY,
        tuple(sorted(_INITIAL_BUILD_PATHS)),
        tuple(sorted(_INITIAL_ACQUISITION_PATHS)),
        tuple(
            sorted(
                leaf.path
                for leaf in registry.leaves
                if leaf.path.startswith("rebuild.")
            )
        ),
    )
    coverage = V075CounterCoverageMatrixV2(
        boundary.profile_id,
        _sequence_digest(route_core.COUNTER_PATHS),
        _sequence_digest(batch_native.BATCH_NATIVE_COUNTER_PATHS),
        _sequence_digest(planner.PLANNER_COUNTER_PATHS),
        _sequence_digest(worker.REGISTERED_COUNTER_PATHS),
        _sequence_digest(direct.DIRECT_PIPELINE_COUNTER_PATHS),
        _coverage_rows(registry),
    )
    portable = portable_registry.freeze_v075_portable_semantic_registry_v2()
    if portable.registry_id != EXPECTED_PORTABLE_SEMANTIC_REGISTRY_ID:
        _fail("portable 67-role registry identity changed")
    if multiround_owner.PROFILE_KEY != EXPECTED_MULTIROUND_SOURCE_PROFILE:
        _fail("multiround source profile identity changed")
    role_registry = V075AccountingRoleRegistryV2(
        portable.registry_id,
        tuple(item.role for item in portable.declarations),
        tuple(
            V075AccountingRoleDeclarationV2(
                role,
                schema,
                (
                    V075AccountingRolePresenceV2.PRESENT_FOUNDATION
                    if present
                    else V075AccountingRolePresenceV2.FUTURE_REQUIRED
                ),
            )
            for role, schema, present in sorted(_COMPANION_ROLES)
        ),
    )
    generic_mapping = tuple(
        sorted(
            (
                code.value,
                routing._TERMINAL_CLASS_BY_CODE[code].value,  # noqa: SLF001
            )
            for code in routing.TerminalCode
        )
    )
    terminal_registry = V075TerminalDerivationRegistryV2(
        generic_mapping,
        "CHILD_ACTION_ROW_CAP_EXCEEDED",
        "ROUTE_ATTEMPT",
        routing.TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE.value,
        routing.TerminalCode.ATTEMPT_BUDGET_EXHAUSTED.value,
    )
    return V075AccountingReadinessAttestationV2(
        _READINESS_ISSUER,
        upstream.closure_id,
        hashlib.sha256(source_code_provenance_bytes).hexdigest(),
        len(source_code_provenance_bytes),
        upstream.verification_id,
        portable_bundle_id,
        public_context_closure_id,
        upstream.semantic_terminal_closure_id,
        upstream.repository_closure_id,
        upstream.source_archive_binding_id,
        upstream.provenance_dag_id,
        archive_binding["runtime_source_closure_id"],
        archive_binding["source_archive_id"],
        archive_binding["runtime_lock_id"],
        archive_binding["compile_verification_id"],
        multiround_result_id,
        "CHILD_ACTION_ROW_CAP_EXCEEDED",
        boundary,
        coverage,
        role_registry,
        terminal_registry,
    )


def replay_v075_construction_native_accounting_foundation_v2(
    *,
    source_code_provenance_bytes: bytes,
    repository_root: str,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075AccountingReadinessAttestationV2:
    """Replay raw contract 1.83 first, then freeze the accounting boundary."""

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
        return _freeze_after_raw_183(
            upstream=upstream,
            source_code_provenance_bytes=source_code_provenance_bytes,
            portable_bundle_bytes=portable_bundle_bytes,
        )
    except Exception:
        raise V075ConstructionNativeAccountingFoundationV2Violation(
            _REPLAY_MISMATCH
        ) from None


def assert_v075_construction_native_accounting_production_gate_v2(
    attestation: V075AccountingReadinessAttestationV2,
) -> NoReturn:
    if type(attestation) is not V075AccountingReadinessAttestationV2:
        _fail("construction accounting gate rejects duck types")
    _ = attestation.attestation_id
    raise V075ConstructionNativeAccountingProductionV2NotReady(
        "contract 1.84 freezes an accounting foundation only; registry-v2 "
        "instrumentation, all-path work, terminal/campaign closure, loaded "
        "source receipt, complete-bundle verification, production, fresh "
        "held-out execution, science, and certificates remain locked"
    )


__all__ = [
    "ACCOUNTING_GATE_PASSED",
    "ALL_PATH_NATIVE_ACCOUNTING_COMPLETE",
    "CALLER_CUSTOM_TOTAL_AS_COUNTER_RECORD_ALLOWED",
    "COMPLETE_BUNDLE_VERIFIER_COMPLETE",
    "COUNTER_COMPLETENESS_GATE_PASSED",
    "COUNTER_REGISTRY_V1_MUTATION_ALLOWED",
    "COUNTER_REGISTRY_V2_KEY",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "LEGACY_CUSTOM_COUNTER_AS_COUNTER_RECORD_ALLOWED",
    "LOADED_SOURCE_RECEIPT_COMPLETE",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_AUTHORITY_COMPLETE",
    "TERMINAL_CAMPAIGN_CLOSURE_COMPLETE",
    "V075AccountingBoundaryProfileV2",
    "V075AccountingReadinessAttestationV2",
    "V075AccountingRoleDeclarationV2",
    "V075AccountingRolePresenceV2",
    "V075AccountingRoleRegistryV2",
    "V075ConstructionNativeAccountingFoundationV2Violation",
    "V075ConstructionNativeAccountingProductionV2NotReady",
    "V075CounterCoverageClassificationV2",
    "V075CounterCoverageMatrixV2",
    "V075CounterCoverageRowV2",
    "V075TerminalDerivationRegistryV2",
    "assert_v075_construction_native_accounting_production_gate_v2",
    "replay_v075_construction_native_accounting_foundation_v2",
]
