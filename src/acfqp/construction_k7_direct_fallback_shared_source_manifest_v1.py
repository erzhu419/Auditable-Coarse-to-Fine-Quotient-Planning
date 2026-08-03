"""Exact construction manifest for nine direct-fallback shared paths.

This module freezes the successor production owner sites, their local
admission/side-effect ordering, cross-site happens-before edges, and a typed
aggregate-evidence *schema*.  It intentionally does not accept numeric
operands or issue an aggregate upper: output fixed-point, read/staging groups,
mount intervals, cgroup hierarchy evidence, and launch cardinalities do not
yet have production semantic authorities.

All artifacts are issuer-retained and content sealed.  The public byte
verifier accepts only the exact registered manifest.  Nothing here authorizes
execution, a V7 route decision, CounterRecords, or a Gate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import hmac
import re
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_cap_authority_v1 as cap_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_DIRECT_FALLBACK_AGGREGATE_CAP_FORMULA_SPEC_V1_DOMAIN,
    CONSTRUCTION_K7_DIRECT_FALLBACK_MANIFEST_BOUND_CAP_JOIN_V1_DOMAIN,
    CONSTRUCTION_K7_DIRECT_FALLBACK_SHARED_SOURCE_MANIFEST_V1_DOMAIN,
    CONSTRUCTION_K7_DIRECT_FALLBACK_SHARED_SOURCE_SITE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.2.0"
PROPOSED_CONTRACT_VERSION = "2.0.48"
PROFILE_KEY = "construction_k7_direct_fallback_shared_source_manifest_v1"
CONSTRUCTION_ONLY = True
OFFICIAL_EXECUTION_ALLOWED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
PRODUCTION_OWNER_WIRING_COMPLETE = False
NUMERICAL_AGGREGATE_CAP_CANDIDATE_ISSUED = False
BLOCKER = "V7_FORMAL_ROUTE_DECISION_AUTHORITY_MISSING"

SHARED_RESOURCE_PATHS = cap_v1.SHARED_RESOURCE_PATHS
EXPECTED_PATH_COUNT = 9
CANONICAL_OWNER_CONTROL_CAP_CHECKS_UPPER = 56
FAILURE_PATH_CONTROL_CAP_REJECTIONS_REQUIRED = True

SOURCE_SITE_DOMAIN = (
    CONSTRUCTION_K7_DIRECT_FALLBACK_SHARED_SOURCE_SITE_V1_DOMAIN
)
SOURCE_MANIFEST_DOMAIN = (
    CONSTRUCTION_K7_DIRECT_FALLBACK_SHARED_SOURCE_MANIFEST_V1_DOMAIN
)
AGGREGATE_FORMULA_SPEC_DOMAIN = (
    CONSTRUCTION_K7_DIRECT_FALLBACK_AGGREGATE_CAP_FORMULA_SPEC_V1_DOMAIN
)
MANIFEST_BOUND_CAP_JOIN_DOMAIN = (
    CONSTRUCTION_K7_DIRECT_FALLBACK_MANIFEST_BOUND_CAP_JOIN_V1_DOMAIN
)
REQUESTED_PHASE3E_DOMAIN_TAGS = (
    SOURCE_SITE_DOMAIN,
    SOURCE_MANIFEST_DOMAIN,
    AGGREGATE_FORMULA_SPEC_DOMAIN,
    MANIFEST_BOUND_CAP_JOIN_DOMAIN,
)

_SITE_ISSUER = object()
_FORMULA_ISSUER = object()
_MANIFEST_ISSUER = object()
_JOIN_ISSUER = object()
_LIVE_SITES: dict[int, tuple["DirectFallbackSharedSourceSiteV1", bytes]] = {}
_LIVE_FORMULAS: dict[int, tuple["AggregateCapFormulaSpecV1", bytes]] = {}
_LIVE_MANIFESTS: dict[
    int, tuple["DirectFallbackSharedSourceManifestV1", bytes]
] = {}
_LIVE_JOINS: dict[
    int, tuple["ManifestBoundSharedCapProfileJoinV1", bytes]
] = {}

_HISTORICAL_CAP_FACTORY = cap_v1.freeze_direct_fallback_shared_cap_profile_v1
_HISTORICAL_PROFILE_REQUIRE = cap_v1._require_live_profile

_EXACT_MANIFEST_DOCUMENT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "counter_registry_id",
        "stage_profile_id",
        "comparison_profile_id",
        "sites",
        "aggregate_cap_evidence_schema",
        "cross_site_ordering",
        "canonical_owner_control_cap_checks_upper",
        "every_shared_admission_requires_one_nonrecursive_control_cap_check",
        "failure_path_control_cap_rejection_upper_required",
        "numeric_aggregate_cap_candidate_issued",
        "source_site_count",
        "source_site_manifest_semantically_verified",
        "production_owner_sites_wired",
        "aggregate_cardinality_evidence_verified",
        "formal_v7_route_decision_authority_present",
        "formal_actual_compliance_eligible",
        "official_execution_allowed",
        "construction_only",
        "blocker",
        "source_site_manifest_id",
    }
)
_EXACT_SOURCE_SITE_DOCUMENT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "profile_key",
        "path",
        "site_key",
        "reducer",
        "unit",
        "admission_primitive",
        "successor_owner_module",
        "successor_owner_symbol",
        "downstream_module",
        "downstream_symbol",
        "operation_steps",
        "successor_owner_symbol_resolved",
        "live_owner_wiring_verified",
        "construction_only",
        "source_site_id",
    }
)

_KEY = re.compile(r"^[a-z][a-z0-9_.:-]*$")
_MODULE = re.compile(r"^acfqp(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


class ConstructionK7DirectFallbackSharedSourceManifestV1Error(ValueError):
    """A source site, formula schema, ordering edge, or seal is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DirectFallbackSharedSourceManifestV1Error(message)


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _key(value: Any, label: str) -> str:
    if type(value) is not str or _KEY.fullmatch(value) is None:
        _fail(f"{label} must be one canonical key")
    return value


def _source_symbol(module: Any, symbol: Any) -> None:
    if (
        type(module) is not str
        or _MODULE.fullmatch(module) is None
        or type(symbol) is not str
        or _SYMBOL.fullmatch(symbol) is None
    ):
        _fail("source module/symbol is noncanonical")


def _retain(
    registry: dict[int, tuple[Any, bytes]], value: Any, raw: bytes
) -> None:
    registry[id(value)] = (value, raw)


def _require_retained(
    registry: dict[int, tuple[Any, bytes]],
    value: Any,
    raw: bytes,
    label: str,
) -> None:
    retained = registry.get(id(value))
    if retained is None or retained[0] is not value:
        _fail(f"{label} is not a live issuer-retained artifact")
    if not hmac.compare_digest(raw, retained[1]):
        _fail(f"{label} changed after issuance")


class SharedAdmissionPrimitiveV1(str, Enum):
    SUM_RESERVATION = "SUM_RESERVATION"
    BOUNDED_READ = "BOUNDED_READ"
    NAMED_SANDBOX_INGRESS = "NAMED_SANDBOX_INGRESS"
    DISTINCT_PAYLOAD_MOUNT_LIFECYCLE = "DISTINCT_PAYLOAD_MOUNT_LIFECYCLE"
    MAX_OBSERVATION = "MAX_OBSERVATION"


class AggregateFormulaKindV1(str, Enum):
    SUM_TYPED_COUNTS = "SUM_TYPED_COUNTS"
    SUM_PAIRED_COUNT_TIMES_EXTENT = "SUM_PAIRED_COUNT_TIMES_EXTENT"
    UNIQUE_PAYLOAD_INTERVAL_SWEEP_MAX = "UNIQUE_PAYLOAD_INTERVAL_SWEEP_MAX"
    VERIFIED_ROUTE_OUTPUT_FIXED_POINT = "VERIFIED_ROUTE_OUTPUT_FIXED_POINT"
    MIN_OUTER_CAP_AND_SUM_ROLE_CAPS = "MIN_OUTER_CAP_AND_SUM_ROLE_CAPS"


class AggregateOperandRoleV1(str, Enum):
    SHARED_ADMISSION_COUNT = "SHARED_ADMISSION_COUNT"
    REGISTERED_EVENT_COUNT = "REGISTERED_EVENT_COUNT"
    UNIT_ONE = "UNIT_ONE"
    READ_OPERATION_COUNT = "READ_OPERATION_COUNT"
    READ_EXTENT_UPPER_BYTES = "READ_EXTENT_UPPER_BYTES"
    SANDBOX_INGRESS_COUNT = "SANDBOX_INGRESS_COUNT"
    SANDBOX_PAYLOAD_EXTENT_UPPER_BYTES = (
        "SANDBOX_PAYLOAD_EXTENT_UPPER_BYTES"
    )
    PAYLOAD_IDENTITY = "PAYLOAD_IDENTITY"
    PAYLOAD_EXTENT_BYTES = "PAYLOAD_EXTENT_BYTES"
    VISIBILITY_OPEN_SEQUENCE = "VISIBILITY_OPEN_SEQUENCE"
    VISIBILITY_CLOSE_SEQUENCE = "VISIBILITY_CLOSE_SEQUENCE"
    OUTPUT_FIXED_POINT_RESULT_ID = "OUTPUT_FIXED_POINT_RESULT_ID"
    OUTPUT_ROLE = "OUTPUT_ROLE"
    OUTPUT_ROLE_EXTENT_UPPER_BYTES = "OUTPUT_ROLE_EXTENT_UPPER_BYTES"
    CGROUP_HIERARCHY_ID = "CGROUP_HIERARCHY_ID"
    CGROUP_ROLE = "CGROUP_ROLE"
    OUTER_CGROUP_CAP_BYTES = "OUTER_CGROUP_CAP_BYTES"
    ROLE_CGROUP_CAP_BYTES = "ROLE_CGROUP_CAP_BYTES"
    SAME_OFD_PEAK_PLAN_ID = "SAME_OFD_PEAK_PLAN_ID"
    PRODUCTION_ROLE = "PRODUCTION_ROLE"
    FIXED_ROLE_LAUNCH_COUNT = "FIXED_ROLE_LAUNCH_COUNT"


@dataclass(frozen=True, slots=True)
class SourceOperationStepV1:
    ordinal: int
    step_key: str
    semantics: str

    def __post_init__(self) -> None:
        _positive(self.ordinal, "operation-step ordinal")
        _key(self.step_key, "operation-step key")
        if type(self.semantics) is not str or not self.semantics:
            _fail("operation-step semantics must be nonempty")

    def to_document(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "step_key": self.step_key,
            "semantics": self.semantics,
        }


@dataclass(frozen=True, slots=True)
class DirectFallbackSharedSourceSiteV1:
    _issuer: InitVar[object]
    path: str
    site_key: str
    reducer: ReducerEnum
    unit: str
    admission_primitive: SharedAdmissionPrimitiveV1
    successor_owner_module: str
    successor_owner_symbol: str
    downstream_module: str
    downstream_symbol: str
    operation_steps: tuple[SourceOperationStepV1, ...]
    source_site_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SITE_ISSUER:
            _fail("shared source site is caller-minted")
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        if leaf is None or self.path not in SHARED_RESOURCE_PATHS:
            _fail("shared source site names an unknown V6 path")
        try:
            object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
            object.__setattr__(
                self,
                "admission_primitive",
                SharedAdmissionPrimitiveV1(self.admission_primitive),
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackSharedSourceManifestV1Error(
                "shared source-site enum is invalid"
            ) from error
        if self.reducer is not leaf.reducer or self.unit != leaf.unit:
            _fail("shared source site changed the official V6 reducer or unit")
        _key(self.site_key, "source-site key")
        _source_symbol(self.successor_owner_module, self.successor_owner_symbol)
        _source_symbol(self.downstream_module, self.downstream_symbol)
        if (
            type(self.operation_steps) is not tuple
            or not self.operation_steps
            or any(type(row) is not SourceOperationStepV1 for row in self.operation_steps)
            or tuple(row.ordinal for row in self.operation_steps)
            != tuple(range(1, len(self.operation_steps) + 1))
            or len({row.step_key for row in self.operation_steps})
            != len(self.operation_steps)
        ):
            _fail("source-site operation steps must be unique and contiguous")
        object.__setattr__(
            self, "source_site_id", content_id(SOURCE_SITE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_shared_source_site.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "path": self.path,
            "site_key": self.site_key,
            "reducer": self.reducer.value,
            "unit": self.unit,
            "admission_primitive": self.admission_primitive.value,
            "successor_owner_module": self.successor_owner_module,
            "successor_owner_symbol": self.successor_owner_symbol,
            "downstream_module": self.downstream_module,
            "downstream_symbol": self.downstream_symbol,
            "operation_steps": [row.to_document() for row in self.operation_steps],
            "successor_owner_symbol_resolved": False,
            "live_owner_wiring_verified": False,
            "construction_only": True,
        }

    def _unchecked_document(self) -> dict[str, Any]:
        return {**self._payload(), "source_site_id": self.source_site_id}

    def to_document(self) -> dict[str, Any]:
        raw = canonical_json_bytes(self._unchecked_document())
        _require_retained(_LIVE_SITES, self, raw, "shared source site")
        if content_id(SOURCE_SITE_DOMAIN, self._payload()) != self.source_site_id:
            _fail("shared source site failed content-ID replay")
        return self._unchecked_document()


@dataclass(frozen=True, slots=True)
class AggregateOperandGroupSpecV1:
    group_key_semantics: str
    required_operand_roles: tuple[AggregateOperandRoleV1, ...]
    required_exact_group_count: int | None
    group_completeness_semantics: str

    def __post_init__(self) -> None:
        _key(self.group_key_semantics, "aggregate group-key semantics")
        if self.required_exact_group_count is not None:
            _positive(
                self.required_exact_group_count,
                "aggregate required exact group count",
            )
        _key(
            self.group_completeness_semantics,
            "aggregate group-completeness semantics",
        )
        try:
            roles = tuple(
                AggregateOperandRoleV1(role)
                for role in self.required_operand_roles
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackSharedSourceManifestV1Error(
                "aggregate operand role is invalid"
            ) from error
        if (
            type(self.required_operand_roles) is not tuple
            or not roles
            or tuple(sorted(roles, key=lambda role: role.value)) != roles
            or len(set(roles)) != len(roles)
        ):
            _fail("aggregate operand roles must be sorted, unique, and nonempty")
        object.__setattr__(self, "required_operand_roles", roles)

    def to_document(self) -> dict[str, Any]:
        return {
            "group_key_semantics": self.group_key_semantics,
            "required_operand_roles": [
                role.value for role in self.required_operand_roles
            ],
            "required_exact_group_count": self.required_exact_group_count,
            "group_completeness_semantics": self.group_completeness_semantics,
            "each_group_requires_exactly_one_of_each_typed_role": True,
            "zero_multiplicity_placeholder_allowed": False,
        }


@dataclass(frozen=True, slots=True)
class AggregateCapFormulaSpecV1:
    _issuer: InitVar[object]
    path: str
    reducer: ReducerEnum
    formula_kind: AggregateFormulaKindV1
    operand_groups: tuple[AggregateOperandGroupSpecV1, ...]
    semantic_authority_requirement: str
    v6_candidate_reuse_blocker: str
    formula_spec_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _FORMULA_ISSUER:
            _fail("aggregate formula spec is caller-minted")
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        if leaf is None or self.path not in SHARED_RESOURCE_PATHS:
            _fail("aggregate formula names an unknown V6 path")
        try:
            object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
            object.__setattr__(
                self, "formula_kind", AggregateFormulaKindV1(self.formula_kind)
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackSharedSourceManifestV1Error(
                "aggregate formula enum is invalid"
            ) from error
        if self.reducer is not leaf.reducer:
            _fail("aggregate formula changed the official V6 reducer")
        _key(self.semantic_authority_requirement, "semantic authority requirement")
        _key(self.v6_candidate_reuse_blocker, "V6 candidate reuse blocker")
        if (
            type(self.operand_groups) is not tuple
            or not self.operand_groups
            or any(
                type(group) is not AggregateOperandGroupSpecV1
                for group in self.operand_groups
            )
            or tuple(
                sorted(self.operand_groups, key=lambda group: group.group_key_semantics)
            )
            != self.operand_groups
            or len({group.group_key_semantics for group in self.operand_groups})
            != len(self.operand_groups)
        ):
            _fail("aggregate operand groups must be sorted, unique, and nonempty")
        admission_groups = tuple(
            group
            for group in self.operand_groups
            if AggregateOperandRoleV1.SHARED_ADMISSION_COUNT
            in group.required_operand_roles
        )
        if (
            len(admission_groups) != 1
            or admission_groups[0].required_operand_roles
            != (AggregateOperandRoleV1.SHARED_ADMISSION_COUNT,)
            or admission_groups[0].required_exact_group_count != 1
        ):
            _fail("each path requires one isolated path-specific admission-total group")
        object.__setattr__(
            self,
            "formula_spec_id",
            content_id(AGGREGATE_FORMULA_SPEC_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_aggregate_cap_formula_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "reducer": self.reducer.value,
            "formula_kind": self.formula_kind.value,
            "operand_groups": [group.to_document() for group in self.operand_groups],
            "semantic_authority_requirement": self.semantic_authority_requirement,
            "v6_candidate_reuse_blocker": self.v6_candidate_reuse_blocker,
            "count_and_extent_must_share_one_group_key": True,
            "operand_evidence_reuse_across_paths_allowed": False,
            "shared_admission_operand_reuse_allowed": False,
            "hard_cap_applied_only_after_semantic_formula_replay": True,
            "numeric_candidate_issued": False,
            "construction_only": True,
        }

    def _unchecked_document(self) -> dict[str, Any]:
        return {**self._payload(), "aggregate_cap_formula_spec_id": self.formula_spec_id}

    def to_document(self) -> dict[str, Any]:
        raw = canonical_json_bytes(self._unchecked_document())
        _require_retained(_LIVE_FORMULAS, self, raw, "aggregate formula spec")
        if (
            content_id(AGGREGATE_FORMULA_SPEC_DOMAIN, self._payload())
            != self.formula_spec_id
        ):
            _fail("aggregate formula spec failed content-ID replay")
        return self._unchecked_document()


@dataclass(frozen=True, slots=True)
class CrossSiteOrderingEdgeV1:
    predecessor: str
    successor: str
    semantics: str

    def __post_init__(self) -> None:
        _key(self.predecessor, "ordering predecessor")
        _key(self.successor, "ordering successor")
        if self.predecessor == self.successor:
            _fail("cross-site ordering edge cannot be reflexive")
        if type(self.semantics) is not str or not self.semantics:
            _fail("cross-site ordering semantics must be nonempty")

    def to_document(self) -> dict[str, str]:
        return {
            "predecessor": self.predecessor,
            "successor": self.successor,
            "semantics": self.semantics,
        }


@dataclass(frozen=True, slots=True)
class DirectFallbackSharedSourceManifestV1:
    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    sites: tuple[DirectFallbackSharedSourceSiteV1, ...]
    aggregate_formulas: tuple[AggregateCapFormulaSpecV1, ...]
    cross_site_ordering: tuple[CrossSiteOrderingEdgeV1, ...]
    manifest_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _MANIFEST_ISSUER:
            _fail("shared source manifest is caller-minted")
        registry = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage.stage_profile_id
            or self.comparison_profile_id != comparison.comparison_profile_id
        ):
            _fail("shared source manifest is not bound to official V6 identities")
        if (
            type(self.sites) is not tuple
            or len(self.sites) != EXPECTED_PATH_COUNT
            or any(type(row) is not DirectFallbackSharedSourceSiteV1 for row in self.sites)
            or tuple(row.path for row in self.sites) != SHARED_RESOURCE_PATHS
            or len({row.source_site_id for row in self.sites}) != EXPECTED_PATH_COUNT
            or type(self.aggregate_formulas) is not tuple
            or len(self.aggregate_formulas) != EXPECTED_PATH_COUNT
            or tuple(row.path for row in self.aggregate_formulas)
            != SHARED_RESOURCE_PATHS
        ):
            _fail("shared source manifest must cover the canonical nine paths once")
        for site in self.sites:
            site.to_document()
        for formula in self.aggregate_formulas:
            formula.to_document()
        if (
            type(self.cross_site_ordering) is not tuple
            or not self.cross_site_ordering
            or any(type(row) is not CrossSiteOrderingEdgeV1 for row in self.cross_site_ordering)
            or tuple(sorted(self.cross_site_ordering, key=lambda row: (row.predecessor, row.successor)))
            != self.cross_site_ordering
        ):
            _fail("cross-site ordering must be one sorted nonempty edge tuple")
        step_keys = {
            f"{site.site_key}:{step.step_key}"
            for site in self.sites
            for step in site.operation_steps
        }
        edges = {(row.predecessor, row.successor) for row in self.cross_site_ordering}
        if (
            len(edges) != len(self.cross_site_ordering)
            or any(node not in step_keys for edge in edges for node in edge)
            or _has_cycle(step_keys, edges)
        ):
            _fail("cross-site ordering is duplicate, foreign, or cyclic")
        object.__setattr__(
            self, "manifest_id", content_id(SOURCE_MANIFEST_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_shared_source_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "sites": [row.to_document() for row in self.sites],
            "aggregate_cap_evidence_schema": [
                row.to_document() for row in self.aggregate_formulas
            ],
            "cross_site_ordering": [
                row.to_document() for row in self.cross_site_ordering
            ],
            "canonical_owner_control_cap_checks_upper": (
                CANONICAL_OWNER_CONTROL_CAP_CHECKS_UPPER
            ),
            "every_shared_admission_requires_one_nonrecursive_control_cap_check": True,
            "failure_path_control_cap_rejection_upper_required": True,
            "numeric_aggregate_cap_candidate_issued": False,
            "source_site_count": EXPECTED_PATH_COUNT,
            "source_site_manifest_semantically_verified": False,
            "production_owner_sites_wired": False,
            "aggregate_cardinality_evidence_verified": False,
            "formal_v7_route_decision_authority_present": False,
            "formal_actual_compliance_eligible": False,
            "official_execution_allowed": False,
            "construction_only": True,
            "blocker": BLOCKER,
        }

    def _unchecked_document(self) -> dict[str, Any]:
        return {**self._payload(), "source_site_manifest_id": self.manifest_id}

    def to_document(self) -> dict[str, Any]:
        raw = canonical_json_bytes(self._unchecked_document())
        _require_retained(_LIVE_MANIFESTS, self, raw, "shared source manifest")
        if content_id(SOURCE_MANIFEST_DOMAIN, self._payload()) != self.manifest_id:
            _fail("shared source manifest failed content-ID replay")
        return self._unchecked_document()

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    @property
    def source_site_ids(self) -> dict[str, tuple[str, ...]]:
        self.to_document()
        return {
            site.path: (site.to_document()["source_site_id"],)
            for site in self.sites
        }


def _has_cycle(nodes: set[str], edges: set[tuple[str, str]]) -> bool:
    successors: dict[str, set[str]] = {node: set() for node in nodes}
    indegree = {node: 0 for node in nodes}
    for left, right in edges:
        successors[left].add(right)
        indegree[right] += 1
    frontier = [node for node in nodes if indegree[node] == 0]
    visited = 0
    while frontier:
        node = frontier.pop()
        visited += 1
        for successor in successors[node]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                frontier.append(successor)
    return visited != len(nodes)


def _steps(*rows: tuple[str, str]) -> tuple[SourceOperationStepV1, ...]:
    return tuple(
        SourceOperationStepV1(index, key, semantics)
        for index, (key, semantics) in enumerate(rows, start=1)
    )


_SUCCESSOR_OWNER_MODULE = (
    "acfqp.construction_k7_direct_fallback_shared_resource_owner_v1"
)


def _site_specs() -> tuple[tuple[Any, ...], ...]:
    return (
        (
            "common.hash_invocations", "shared.hash", SharedAdmissionPrimitiveV1.SUM_RESERVATION,
            "record_hash_invocation", "acfqp.construction_shared_resource_common_journal_v2",
            "CommonJournalSessionV2.record_hash_invocation_v2",
            _steps(("admit", "reserve one event before hashing"), ("operate", "invoke the registered hash purpose"), ("settle", "commit one event or full-charge failure")),
        ),
        (
            "common.integrity_checks", "shared.integrity", SharedAdmissionPrimitiveV1.SUM_RESERVATION,
            "record_integrity_check", "acfqp.construction_shared_resource_common_journal_v2",
            "CommonJournalSessionV2.record_integrity_check_v2",
            _steps(("admit", "reserve one named integrity check"), ("operate", "evaluate the registered obligation"), ("settle", "commit one check or full-charge failure")),
        ),
        (
            "common.protocol_checks", "shared.protocol", SharedAdmissionPrimitiveV1.SUM_RESERVATION,
            "record_protocol_check", "acfqp.construction_shared_resource_common_journal_v2",
            "CommonJournalSessionV2.record_protocol_check_v2",
            _steps(("admit", "reserve one named protocol check"), ("operate", "evaluate the registered obligation"), ("settle", "commit one check or full-charge failure")),
        ),
        (
            "io.mounted_bytes_peak", "shared.mount", SharedAdmissionPrimitiveV1.DISTINCT_PAYLOAD_MOUNT_LIFECYCLE,
            "track_mounted_payload", "acfqp.v075_k7_production_broker_runtime_v2",
            "run_v075_k7_production_broker_runtime_v2",
            _steps(("admit", "admit projected distinct-payload peak"), ("open", "open before child visibility"), ("retain", "retain identity through visibility interval"), ("close", "close only after reap or terminal cleanup")),
        ),
        (
            "io.output_bytes", "shared.output", SharedAdmissionPrimitiveV1.SUM_RESERVATION,
            "write_route_output", "acfqp.v075_k7_production_broker_runtime_v2", "_promote_output_v2",
            _steps(("formula", "require a verified whole-route output fixed point"), ("admit", "reserve the verified upper before first launch"), ("operate", "write all registered output roles"), ("fixedpoint", "close the self-describing size fixed point"), ("settle", "commit exact output bytes and proven slack")),
        ),
        (
            "io.read_bytes", "shared.read", SharedAdmissionPrimitiveV1.BOUNDED_READ,
            "read_registered_payload", "acfqp.v075_k7_production_broker_runtime_v2", "_read_exact_file",
            _steps(("admit", "reserve the group extent before each read"), ("operate", "perform one bounded read"), ("settle", "commit returned bytes or full-charge unverifiable failure"), ("authenticate", "bind child reads to trusted receipts")),
        ),
        (
            "io.staged_bytes", "shared.stage", SharedAdmissionPrimitiveV1.NAMED_SANDBOX_INGRESS,
            "stage_registered_payload", "acfqp.v075_k7_outer_attempt_broker_preparation_v1",
            "prepare_v075_k7_outer_attempt_broker_session_v1",
            _steps(("classify", "require COPY or BIND ingress"), ("admit", "reserve paired payload extent"), ("operate", "stage the named payload"), ("settle", "commit ingress bytes or full-charge failure")),
        ),
        (
            "memory.working_bytes_peak", "shared.memory", SharedAdmissionPrimitiveV1.MAX_OBSERVATION,
            "track_hierarchy_working_peak", "acfqp.v075_k7_outer_attempt_cgroup_v1", "_read_retained_peak",
            _steps(("bind", "bind typed hierarchy memory.max before launch"), ("execute", "run all descendants in that hierarchy"), ("reap", "prove the hierarchy reaped"), ("observe", "read same-OFD hierarchy memory.peak"), ("admit", "admit observed peak; never report memory.max as actual")),
        ),
        (
            "process.launches", "shared.launch", SharedAdmissionPrimitiveV1.SUM_RESERVATION,
            "launch_registered_role", "acfqp.v075_k7_production_broker_runtime_v2", "_launch_production_role_v2",
            _steps(("admit", "reserve one launch immediately before clone3"), ("operate", "perform native launch attempt"), ("commit", "commit positive edge with matching pidfd"), ("settle", "refund only trusted proof of no child")),
        ),
    )


def _group(
    key: str,
    roles: tuple[AggregateOperandRoleV1, ...],
    count: int | None,
    completeness: str,
) -> AggregateOperandGroupSpecV1:
    return AggregateOperandGroupSpecV1(
        key,
        tuple(sorted(roles, key=lambda role: role.value)),
        count,
        completeness,
    )


def _admission_group() -> AggregateOperandGroupSpecV1:
    return _group(
        "path-specific-shared-admission-total",
        (AggregateOperandRoleV1.SHARED_ADMISSION_COUNT,),
        1,
        "one-path-bound-admission-total-with-no-cross-path-reuse",
    )


def _formula_specs() -> tuple[tuple[Any, ...], ...]:
    admission = _admission_group()
    common = lambda key, completeness: (  # noqa: E731
        _group(
            key,
            (
                AggregateOperandRoleV1.REGISTERED_EVENT_COUNT,
                AggregateOperandRoleV1.UNIT_ONE,
            ),
            None,
            completeness,
        ),
        admission,
    )
    return (
        (
            "common.hash_invocations",
            AggregateFormulaKindV1.SUM_TYPED_COUNTS,
            common(
                "registered-hash-purpose-key",
                "complete-registered-hash-purpose-catalogue",
            ),
            "verified-hash-purpose-cardinality-authority",
            "v6-candidate-lacks-semantic-cardinality-evidence",
        ),
        (
            "common.integrity_checks",
            AggregateFormulaKindV1.SUM_TYPED_COUNTS,
            common(
                "registered-integrity-obligation-key",
                "complete-registered-integrity-obligation-catalogue",
            ),
            "verified-integrity-obligation-cardinality-authority",
            "v6-candidate-lacks-semantic-cardinality-evidence",
        ),
        (
            "common.protocol_checks",
            AggregateFormulaKindV1.SUM_TYPED_COUNTS,
            common(
                "registered-protocol-obligation-key",
                "complete-registered-protocol-obligation-catalogue",
            ),
            "verified-protocol-obligation-cardinality-authority",
            "v6-candidate-lacks-semantic-cardinality-evidence",
        ),
        (
            "io.mounted_bytes_peak",
            AggregateFormulaKindV1.UNIQUE_PAYLOAD_INTERVAL_SWEEP_MAX,
            (
                _group(
                    "payload-identity-plus-visibility-interval",
                    (
                        AggregateOperandRoleV1.PAYLOAD_EXTENT_BYTES,
                        AggregateOperandRoleV1.PAYLOAD_IDENTITY,
                        AggregateOperandRoleV1.VISIBILITY_CLOSE_SEQUENCE,
                        AggregateOperandRoleV1.VISIBILITY_OPEN_SEQUENCE,
                    ),
                    None,
                    "complete-preregistered-payload-visibility-interval-catalogue",
                ),
                admission,
            ),
            "verified-distinct-payload-visibility-interval-authority",
            "v6-stream-cap-is-not-an-aggregate-formula",
        ),
        (
            "io.output_bytes",
            AggregateFormulaKindV1.VERIFIED_ROUTE_OUTPUT_FIXED_POINT,
            (
                _group(
                    "fixed-point-attestation",
                    (AggregateOperandRoleV1.OUTPUT_FIXED_POINT_RESULT_ID,),
                    1,
                    "one-verified-whole-route-output-fixed-point",
                ),
                _group(
                    "registered-output-role",
                    (
                        AggregateOperandRoleV1.OUTPUT_ROLE,
                        AggregateOperandRoleV1.OUTPUT_ROLE_EXTENT_UPPER_BYTES,
                    ),
                    8,
                    "exact-eight-role-output-catalogue",
                ),
                admission,
            ),
            "verified-route-output-fixed-point-authority",
            "v6-worker-output-cap-is-not-whole-route-output",
        ),
        (
            "io.read_bytes",
            AggregateFormulaKindV1.SUM_PAIRED_COUNT_TIMES_EXTENT,
            (
                _group(
                    "registered-read-family",
                    (
                        AggregateOperandRoleV1.READ_EXTENT_UPPER_BYTES,
                        AggregateOperandRoleV1.READ_OPERATION_COUNT,
                    ),
                    None,
                    "complete-preregistered-read-family-catalogue",
                ),
                admission,
            ),
            "verified-read-cardinality-and-extent-authority",
            "v6-stream-cap-is-not-an-aggregate-formula",
        ),
        (
            "io.staged_bytes",
            AggregateFormulaKindV1.SUM_PAIRED_COUNT_TIMES_EXTENT,
            (
                _group(
                    "registered-sandbox-ingress",
                    (
                        AggregateOperandRoleV1.SANDBOX_INGRESS_COUNT,
                        AggregateOperandRoleV1.SANDBOX_PAYLOAD_EXTENT_UPPER_BYTES,
                    ),
                    None,
                    "complete-copy-or-bind-sandbox-ingress-catalogue",
                ),
                admission,
            ),
            "verified-sandbox-ingress-cardinality-authority",
            "v6-stream-cap-is-not-an-aggregate-formula",
        ),
        (
            "memory.working_bytes_peak",
            AggregateFormulaKindV1.MIN_OUTER_CAP_AND_SUM_ROLE_CAPS,
            (
                _group(
                    "outer-cgroup-hierarchy",
                    (
                        AggregateOperandRoleV1.CGROUP_HIERARCHY_ID,
                        AggregateOperandRoleV1.OUTER_CGROUP_CAP_BYTES,
                        AggregateOperandRoleV1.SAME_OFD_PEAK_PLAN_ID,
                    ),
                    1,
                    "one-outer-hierarchy-cap-and-same-ofd-plan",
                ),
                _group(
                    "production-role-cgroup-cap",
                    (
                        AggregateOperandRoleV1.CGROUP_ROLE,
                        AggregateOperandRoleV1.ROLE_CGROUP_CAP_BYTES,
                    ),
                    2,
                    "exact-worker-and-business-role-caps",
                ),
                admission,
            ),
            "verified-hierarchy-cap-and-same-ofd-peak-authority",
            "memory-limit-is-not-an-actual-peak",
        ),
        (
            "process.launches",
            AggregateFormulaKindV1.SUM_TYPED_COUNTS,
            (
                _group(
                    "registered-production-role",
                    (
                        AggregateOperandRoleV1.FIXED_ROLE_LAUNCH_COUNT,
                        AggregateOperandRoleV1.PRODUCTION_ROLE,
                    ),
                    2,
                    "exact-worker-and-business-positive-edge-role-catalogue",
                ),
                admission,
            ),
            "verified-fixed-role-launch-cardinality-authority",
            "two-role-count-lacks-live-admission-owner",
        ),
    )


def freeze_direct_fallback_shared_source_manifest_v1(
) -> DirectFallbackSharedSourceManifestV1:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    sites: list[DirectFallbackSharedSourceSiteV1] = []
    for path, site_key, primitive, owner_symbol, downstream_module, downstream_symbol, steps in _site_specs():
        site = DirectFallbackSharedSourceSiteV1(
            _SITE_ISSUER, path, site_key, registry.by_path[path].reducer,
            registry.by_path[path].unit, primitive, _SUCCESSOR_OWNER_MODULE,
            owner_symbol, downstream_module, downstream_symbol, steps,
        )
        _retain(_LIVE_SITES, site, canonical_json_bytes(site._unchecked_document()))
        sites.append(site)
    formulas: list[AggregateCapFormulaSpecV1] = []
    for path, kind, groups, authority, blocker in _formula_specs():
        formula = AggregateCapFormulaSpecV1(
            _FORMULA_ISSUER, path, registry.by_path[path].reducer, kind,
            tuple(sorted(groups, key=lambda group: group.group_key_semantics)),
            authority, blocker,
        )
        _retain(
            _LIVE_FORMULAS,
            formula,
            canonical_json_bytes(formula._unchecked_document()),
        )
        formulas.append(formula)
    by_path = {
        site.path: {
            step.step_key: f"{site.site_key}:{step.step_key}"
            for step in site.operation_steps
        }
        for site in sites
    }
    edges = tuple(
        sorted(
            (
                CrossSiteOrderingEdgeV1(by_path["io.output_bytes"]["admit"], by_path["process.launches"]["admit"], "whole-route output reserve precedes launch"),
                CrossSiteOrderingEdgeV1(by_path["io.staged_bytes"]["settle"], by_path["io.mounted_bytes_peak"]["open"], "staging settles before visibility"),
                CrossSiteOrderingEdgeV1(by_path["io.mounted_bytes_peak"]["open"], by_path["process.launches"]["admit"], "payload visibility precedes launch"),
                CrossSiteOrderingEdgeV1(by_path["memory.working_bytes_peak"]["bind"], by_path["process.launches"]["admit"], "hierarchy cap precedes launch"),
                CrossSiteOrderingEdgeV1(by_path["process.launches"]["settle"], by_path["memory.working_bytes_peak"]["reap"], "launch outcomes settle before hierarchy reap"),
                CrossSiteOrderingEdgeV1(by_path["memory.working_bytes_peak"]["reap"], by_path["memory.working_bytes_peak"]["observe"], "peak is observed after reap"),
                CrossSiteOrderingEdgeV1(by_path["memory.working_bytes_peak"]["reap"], by_path["io.mounted_bytes_peak"]["close"], "visibility closes after reap"),
            ),
            key=lambda edge: (edge.predecessor, edge.successor),
        )
    )
    manifest = DirectFallbackSharedSourceManifestV1(
        _MANIFEST_ISSUER,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        tuple(sites),
        tuple(formulas),
        edges,
    )
    _retain(
        _LIVE_MANIFESTS,
        manifest,
        canonical_json_bytes(manifest._unchecked_document()),
    )
    return manifest


_EXACT_MANIFEST_FACTORY = freeze_direct_fallback_shared_source_manifest_v1


def verify_direct_fallback_shared_source_manifest_bytes_v1(
    raw: bytes,
) -> DirectFallbackSharedSourceManifestV1:
    """Replay exact canonical bytes against a newly issued registered manifest."""

    if type(raw) is not bytes:
        _fail("shared source manifest verifier requires exact bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7DirectFallbackSharedSourceManifestV1Error(
            "shared source manifest bytes are not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("shared source manifest bytes are not one canonical object")
    expected = _EXACT_MANIFEST_FACTORY()
    retained = _LIVE_MANIFESTS.get(id(expected))
    if (
        type(expected) is not DirectFallbackSharedSourceManifestV1
        or retained is None
        or retained[0] is not expected
        or not hmac.compare_digest(raw, retained[1])
    ):
        _fail("shared source manifest differs from exact independent replay")
    return expected


_EXACT_MANIFEST_BYTE_VERIFIER = (
    verify_direct_fallback_shared_source_manifest_bytes_v1
)


def _derive_exact_manifest_binding_from_bytes_v1(
    manifest_bytes: bytes,
) -> tuple[
    DirectFallbackSharedSourceManifestV1,
    str,
    Mapping[str, tuple[str, ...]],
]:
    """Return the immutable manifest/site binding parsed only from exact bytes."""

    manifest = _EXACT_MANIFEST_BYTE_VERIFIER(manifest_bytes)
    try:
        document = loads_canonical_json(manifest_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7DirectFallbackSharedSourceManifestV1Error(
            "exact manifest binding bytes failed canonical replay"
        ) from error
    if (
        type(document) is not dict
        or set(document) != _EXACT_MANIFEST_DOCUMENT_FIELDS
        or document.get("source_site_count") != EXPECTED_PATH_COUNT
    ):
        _fail("exact manifest binding has a malformed top-level schema")
    rows = document.get("sites")
    if type(rows) is not list or len(rows) != EXPECTED_PATH_COUNT:
        _fail("exact manifest binding must contain the ordered nine source sites")
    ordered: list[tuple[str, tuple[str, ...]]] = []
    seen_ids: set[str] = set()
    for expected_path, row in zip(SHARED_RESOURCE_PATHS, rows, strict=True):
        if (
            type(row) is not dict
            or set(row) != _EXACT_SOURCE_SITE_DOCUMENT_FIELDS
            or type(row.get("path")) is not str
            or row["path"] != expected_path
        ):
            _fail("exact manifest source-site field set or path order changed")
        try:
            source_site_id = parse_content_id(row.get("source_site_id"))
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackSharedSourceManifestV1Error(
                "exact manifest source-site ID is malformed"
            ) from error
        if source_site_id in seen_ids:
            _fail("exact manifest source-site IDs must be unique")
        seen_ids.add(source_site_id)
        ordered.append((expected_path, (source_site_id,)))
    try:
        manifest_id = parse_content_id(document.get("source_site_manifest_id"))
    except (TypeError, ValueError) as error:
        raise ConstructionK7DirectFallbackSharedSourceManifestV1Error(
            "exact manifest ID is malformed"
        ) from error
    return manifest, manifest_id, MappingProxyType(dict(ordered))


def _validate_profile_manifest_binding_v1(
    manifest_bytes: bytes,
    profile: Any,
) -> tuple[
    DirectFallbackSharedSourceManifestV1,
    str,
    Mapping[str, tuple[str, ...]],
]:
    manifest, manifest_id, byte_derived_sites = (
        _derive_exact_manifest_binding_from_bytes_v1(manifest_bytes)
    )
    if type(profile) is not cap_v1.DirectFallbackSharedCapProfileV1:
        _fail("manifest-bound join requires the exact historical cap-profile type")
    try:
        retained_profile = _HISTORICAL_PROFILE_REQUIRE(profile)
        if (
            type(retained_profile) is not tuple
            or len(retained_profile) != 2
            or retained_profile[0] is not profile
        ):
            _fail("historical cap-profile live replay changed object identity")
        supplied_sites = {
            path: profile.by_path[path].source_site_ids
            for path in SHARED_RESOURCE_PATHS
        }
    except Exception as error:
        raise ConstructionK7DirectFallbackSharedSourceManifestV1Error(
            "manifest-bound join cap profile failed live replay"
        ) from error
    if (
        profile.source_site_manifest_id != manifest_id
        or supplied_sites != dict(byte_derived_sites)
    ):
        _fail(
            "cap profile manifest ID and source-site IDs are not one exact manifest binding"
        )
    return manifest, manifest_id, byte_derived_sites


class ManifestBoundSharedCapProfileJoinV1:
    """Issuer-retained proof that one legacy profile came from exact manifest bytes."""

    __slots__ = (
        "_manifest_bytes",
        "_manifest_id",
        "_source_site_binding",
        "_cap_profile",
        "_join_id",
    )

    def __init__(
        self,
        issuer: object,
        *,
        manifest_bytes: bytes,
        cap_profile: cap_v1.DirectFallbackSharedCapProfileV1,
    ) -> None:
        if issuer is not _JOIN_ISSUER:
            _fail("manifest-bound cap-profile join is issuer-owned")
        if type(manifest_bytes) is not bytes:
            _fail("manifest-bound join requires exact canonical manifest bytes")
        _, manifest_id, byte_derived_sites = _validate_profile_manifest_binding_v1(
            manifest_bytes, cap_profile
        )
        self._manifest_bytes = manifest_bytes
        self._manifest_id = manifest_id
        self._source_site_binding = tuple(byte_derived_sites.items())
        self._cap_profile = cap_profile
        self._join_id = content_id(
            MANIFEST_BOUND_CAP_JOIN_DOMAIN, self._payload_unchecked()
        )

    def _payload_unchecked(self) -> dict[str, Any]:
        profile_document = self._cap_profile.to_document()
        return {
            "schema": "acfqp.construction_k7_direct_fallback_manifest_bound_cap_join.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_site_manifest_id": self._manifest_id,
            "source_site_manifest_canonical_sha256": hashlib.sha256(
                self._manifest_bytes
            ).hexdigest(),
            "production_shared_cap_profile_id": self._cap_profile.profile_id,
            "RouteDecisionContext_id": self._cap_profile.route_decision_context_id,
            "decision_point_id": self._cap_profile.decision_point_id,
            "route_attempt_id": self._cap_profile.route_attempt_id,
            "joined_source_site_ids": [
                {
                    "path": path,
                    "source_site_ids": list(source_site_ids),
                }
                for path, source_site_ids in self._source_site_binding
            ],
            "historical_cap_profile_document_sha256": hashlib.sha256(
                canonical_json_bytes(profile_document)
            ).hexdigest(),
            "manifest_bytes_independently_replayed": True,
            "site_ids_derived_internally_from_manifest": True,
            "caller_supplied_site_ids_accepted": False,
            "legacy_generic_factory_alone_proves_manifest_join": False,
            "production_owner_sites_wired": False,
            "formal_v7_route_decision_authority_present": False,
            "formal_actual_compliance_eligible": False,
            "official_execution_allowed": False,
            "construction_only": True,
            "blocker": BLOCKER,
        }

    def _document_unchecked(self) -> dict[str, Any]:
        payload = self._payload_unchecked()
        if content_id(MANIFEST_BOUND_CAP_JOIN_DOMAIN, payload) != self._join_id:
            _fail("manifest-bound cap-profile join failed content-ID replay")
        return {**payload, "manifest_bound_cap_profile_join_id": self._join_id}

    def _assert_live(self) -> None:
        retained = _LIVE_JOINS.get(id(self))
        if retained is None or retained[0] is not self:
            _fail("manifest-bound cap-profile join is not a live issuer artifact")
        try:
            _, manifest_id, byte_derived_sites = _validate_profile_manifest_binding_v1(
                self._manifest_bytes, self._cap_profile
            )
            if (
                manifest_id != self._manifest_id
                or tuple(byte_derived_sites.items()) != self._source_site_binding
            ):
                _fail("manifest-bound join crossed its byte-derived identity binding")
            current = canonical_json_bytes(self._document_unchecked())
        except ConstructionK7DirectFallbackSharedSourceManifestV1Error:
            raise
        except Exception as error:
            raise ConstructionK7DirectFallbackSharedSourceManifestV1Error(
                "manifest-bound cap-profile join failed live replay"
            ) from error
        if not hmac.compare_digest(current, retained[1]):
            _fail("manifest-bound cap-profile join changed after issuer sealing")

    @property
    def join_id(self) -> str:
        self._assert_live()
        return self._join_id

    @property
    def manifest_id(self) -> str:
        self._assert_live()
        return self._manifest_id

    @property
    def cap_profile(self) -> cap_v1.DirectFallbackSharedCapProfileV1:
        self._assert_live()
        return self._cap_profile

    def to_document(self) -> dict[str, Any]:
        self._assert_live()
        return self._document_unchecked()


def freeze_manifest_bound_shared_cap_profile_join_v1(
    *,
    manifest_bytes: bytes,
    route_context: Any,
    route_decision_candidate: Any,
    stage_profile_id: str,
    caps: Mapping[str, int],
    max_control_cap_checks: int,
) -> ManifestBoundSharedCapProfileJoinV1:
    """Mint a legacy cap profile only from independently replayed exact bytes.

    There is deliberately no ``source_site_manifest_id`` or
    ``source_site_ids`` argument.  Both are derived after exact byte replay.
    """

    _manifest, manifest_id, byte_derived_sites = (
        _derive_exact_manifest_binding_from_bytes_v1(manifest_bytes)
    )
    if (
        cap_v1.freeze_direct_fallback_shared_cap_profile_v1
        is not _HISTORICAL_CAP_FACTORY
        or cap_v1._require_live_profile is not _HISTORICAL_PROFILE_REQUIRE
    ):
        _fail("historical cap-profile factory or live verifier binding changed")
    cap_profile = _HISTORICAL_CAP_FACTORY(
        route_context=route_context,
        route_decision_candidate=route_decision_candidate,
        stage_profile_id=stage_profile_id,
        source_site_manifest_id=manifest_id,
        caps=caps,
        source_site_ids=dict(byte_derived_sites),
        max_control_cap_checks=max_control_cap_checks,
    )
    _validate_profile_manifest_binding_v1(manifest_bytes, cap_profile)
    result = ManifestBoundSharedCapProfileJoinV1(
        _JOIN_ISSUER,
        manifest_bytes=manifest_bytes,
        cap_profile=cap_profile,
    )
    _retain(
        _LIVE_JOINS,
        result,
        canonical_json_bytes(result._document_unchecked()),
    )
    return result


def require_manifest_bound_shared_cap_profile_join_v1(
    value: Any,
) -> ManifestBoundSharedCapProfileJoinV1:
    if type(value) is not ManifestBoundSharedCapProfileJoinV1:
        _fail("exact manifest-bound cap-profile join type is required")
    value._assert_live()
    return value


__all__ = [
    "AggregateCapFormulaSpecV1",
    "AggregateOperandGroupSpecV1",
    "AggregateFormulaKindV1",
    "AggregateOperandRoleV1",
    "BLOCKER",
    "CANONICAL_OWNER_CONTROL_CAP_CHECKS_UPPER",
    "ConstructionK7DirectFallbackSharedSourceManifestV1Error",
    "DirectFallbackSharedSourceManifestV1",
    "DirectFallbackSharedSourceSiteV1",
    "EXPECTED_PATH_COUNT",
    "ManifestBoundSharedCapProfileJoinV1",
    "NUMERICAL_AGGREGATE_CAP_CANDIDATE_ISSUED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PRODUCTION_OWNER_WIRING_COMPLETE",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SHARED_RESOURCE_PATHS",
    "SharedAdmissionPrimitiveV1",
    "SourceOperationStepV1",
    "freeze_direct_fallback_shared_source_manifest_v1",
    "freeze_manifest_bound_shared_cap_profile_join_v1",
    "require_manifest_bound_shared_cap_profile_join_v1",
    "verify_direct_fallback_shared_source_manifest_bytes_v1",
]
