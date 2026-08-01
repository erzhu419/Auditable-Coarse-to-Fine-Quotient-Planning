"""Fail-closed completion readiness for the exact V0-075 K7 path.

This module answers only whether the current same-process construction
evidence is ready to be converted into formal accounting artifacts.  It binds
the exact V6 registry/stage/comparison/projection profiles, the K7 V3
operation-boundary manifest, and the V0-075 execution-identity overlay.

The answer for the current path is deliberately negative.  In particular all
nine shared-resource leaves remain outside live evidence closure, including
the mounted- and working-byte peaks.  No function here creates a
``CounterRecord``, ``WorkVector`` or ``ComparisonVector`` and unresolved work
is never inferred to be zero.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any, Mapping

from acfqp.accounting_v1 import LaneEnum
from acfqp import construction_accounting_evidence_closure_v1 as evidence
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACCOUNTING_COMPLETION_READINESS_BLOCKER_V1_DOMAIN,
    CONSTRUCTION_ACCOUNTING_COMPLETION_READINESS_V1_DOMAIN,
    CONSTRUCTION_ACCOUNTING_REQUIRED_PATH_PARTITION_V1_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as execution
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_accounting_completion_readiness_v1"

REQUIRED_PATH_PARTITION_V1_DOMAIN = (
    CONSTRUCTION_ACCOUNTING_REQUIRED_PATH_PARTITION_V1_DOMAIN
)
COMPLETION_READINESS_BLOCKER_V1_DOMAIN = (
    CONSTRUCTION_ACCOUNTING_COMPLETION_READINESS_BLOCKER_V1_DOMAIN
)
COMPLETION_READINESS_V1_DOMAIN = (
    CONSTRUCTION_ACCOUNTING_COMPLETION_READINESS_V1_DOMAIN
)
LOCAL_DOMAIN_TAGS = frozenset(
    {
        REQUIRED_PATH_PARTITION_V1_DOMAIN,
        COMPLETION_READINESS_BLOCKER_V1_DOMAIN,
        COMPLETION_READINESS_V1_DOMAIN,
    }
)

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_SHARED_RESOURCE_PATH_COUNT = 9
EXPECTED_DERIVED_PATH_COUNT = 8
EXPECTED_PROFILE_STATIC_ZERO_PATH_COUNT = 114
EXPECTED_EMITTABLE_OWNER_PATH_COUNT = 71

MOUNTED_PEAK_PATH = "io.mounted_bytes_peak"
WORKING_PEAK_PATH = "memory.working_bytes_peak"

_PARTITION_ISSUER = object()
_BLOCKER_ISSUER = object()
_READINESS_ISSUER = object()


class ConstructionAccountingCompletionReadinessV1Error(ValueError):
    """The exact readiness authority or supplied evidence is invalid."""


class CompletionReadinessStatusV1(str, Enum):
    NOT_READY_PARTIAL_EVIDENCE = "NOT_READY_PARTIAL_EVIDENCE"


class CompletionReadinessBlockerCodeV1(str, Enum):
    DERIVED_RECONCILIATION_INCOMPLETE = (
        "DERIVED_RECONCILIATION_INCOMPLETE"
    )
    EMITTABLE_OWNER_EVIDENCE_INCOMPLETE = (
        "EMITTABLE_OWNER_EVIDENCE_INCOMPLETE"
    )
    EVIDENCE_CLOSURE_INCOMPLETE = "EVIDENCE_CLOSURE_INCOMPLETE"
    FORMAL_ACCOUNTING_ARTIFACTS_FORBIDDEN = (
        "FORMAL_ACCOUNTING_ARTIFACTS_FORBIDDEN"
    )
    MOUNTED_BYTES_PEAK_NOT_LIVE_CLOSED = (
        "MOUNTED_BYTES_PEAK_NOT_LIVE_CLOSED"
    )
    PROFILE_STATIC_ZERO_EVIDENCE_INCOMPLETE = (
        "PROFILE_STATIC_ZERO_EVIDENCE_INCOMPLETE"
    )
    SHARED_RESOURCE_RECEIPTS_NOT_LIVE_CLOSED = (
        "SHARED_RESOURCE_RECEIPTS_NOT_LIVE_CLOSED"
    )
    WORKING_BYTES_PEAK_NOT_LIVE_CLOSED = (
        "WORKING_BYTES_PEAK_NOT_LIVE_CLOSED"
    )


_BLOCKER_REASONS = {
    CompletionReadinessBlockerCodeV1.DERIVED_RECONCILIATION_INCOMPLETE: (
        "one or more derived-only required paths lack registered reconciliation evidence"
    ),
    CompletionReadinessBlockerCodeV1.EMITTABLE_OWNER_EVIDENCE_INCOMPLETE: (
        "one or more owner-emittable required paths remain unresolved"
    ),
    CompletionReadinessBlockerCodeV1.EVIDENCE_CLOSURE_INCOMPLETE: (
        "the bound EvidenceClosure still contains UNRESOLVED required paths"
    ),
    CompletionReadinessBlockerCodeV1.FORMAL_ACCOUNTING_ARTIFACTS_FORBIDDEN: (
        "partial evidence cannot authorize CounterRecord, WorkVector, or ComparisonVector"
    ),
    CompletionReadinessBlockerCodeV1.MOUNTED_BYTES_PEAK_NOT_LIVE_CLOSED: (
        "the same-process path has no live sandbox mount-peak measurement"
    ),
    CompletionReadinessBlockerCodeV1.PROFILE_STATIC_ZERO_EVIDENCE_INCOMPLETE: (
        "one or more profile-static-zero paths lack explicit zero attestations"
    ),
    CompletionReadinessBlockerCodeV1.SHARED_RESOURCE_RECEIPTS_NOT_LIVE_CLOSED: (
        "all nine shared-resource paths lack live-closed typed receipts"
    ),
    CompletionReadinessBlockerCodeV1.WORKING_BYTES_PEAK_NOT_LIVE_CLOSED: (
        "the same-process path has no verified working-set peak or frozen cap"
    ),
}


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        raise ConstructionAccountingCompletionReadinessV1Error(
            "completion readiness used an unknown local domain"
        )
    return content_id(domain, dict(payload))


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionAccountingCompletionReadinessV1Error(
            f"{field_name} must be one full content ID"
        ) from error


def _canonical_paths(values: Any, field_name: str) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or tuple(sorted(values)) != values
        or len(set(values)) != len(values)
        or any(type(value) is not str or not value for value in values)
    ):
        raise ConstructionAccountingCompletionReadinessV1Error(
            f"{field_name} must be one sorted unique path tuple"
        )
    return values


@lru_cache(maxsize=1)
def _exact_authorities() -> tuple[Any, Any, Any, Any, Any, Any]:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    projection = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    execution_profile = (
        execution.official_v075_k7_root_cap_execution_identity_profile_v1()
    )
    try:
        registry.validate_official_catalogue()
        stage.validate(registry)
        manifest.validate_official()
    except Exception as error:
        raise ConstructionAccountingCompletionReadinessV1Error(
            "one exact V3/V6 authority rejected replay"
        ) from error
    if (
        manifest.counter_registry_id != registry.registry_id
        or manifest.stage_profile_id != stage.stage_profile_id
        or manifest.comparison_profile_id != comparison.comparison_profile_id
        or manifest.actual_projection_profile_id
        != projection.actual_projection_profile_id
        or execution_profile.boundary_manifest_id != manifest.manifest_id
    ):
        raise ConstructionAccountingCompletionReadinessV1Error(
            "K7 V3/V6/execution authority chain is stale"
        )
    return registry, stage, comparison, projection, manifest, execution_profile


@lru_cache(maxsize=1)
def _expected_partition_paths() -> tuple[
    tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]
]:
    registry, _stage, _comparison, _projection, manifest, _execution = (
        _exact_authorities()
    )
    shared = tuple(sorted(evidence.SHARED_RESOURCE_PATHS_V1))
    derived = tuple(
        path
        for path in registry.required_paths
        if registry.by_path[path].lane is LaneEnum.DERIVED_ONLY
    )
    emittable = tuple(
        sorted(
            {
                row.target_path
                for row in manifest.boundaries
                if row.classification in boundary_v3._EMITTABLE_CLASSIFICATIONS  # noqa: SLF001
            }
        )
    )
    profile_static_zero = tuple(
        sorted(set(registry.required_paths) - set(shared) - set(derived) - set(emittable))
    )
    return shared, derived, profile_static_zero, emittable


@dataclass(frozen=True, slots=True)
class RequiredPathPartitionV1:
    """Exact disjoint disposition of all 202 V6 required paths."""

    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundary_manifest_id: str
    execution_profile_id: str
    shared_resource_paths: tuple[str, ...]
    derived_reconciliation_paths: tuple[str, ...]
    profile_static_zero_paths: tuple[str, ...]
    emittable_owner_paths: tuple[str, ...]

    def __post_init__(self, _issuer: object) -> None:
        for name in (
            "counter_registry_id",
            "stage_profile_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "boundary_manifest_id",
            "execution_profile_id",
        ):
            _cid(getattr(self, name), name)
        for name in (
            "shared_resource_paths",
            "derived_reconciliation_paths",
            "profile_static_zero_paths",
            "emittable_owner_paths",
        ):
            _canonical_paths(getattr(self, name), name)
        registry, stage, comparison, projection, manifest, execution_profile = (
            _exact_authorities()
        )
        expected = _expected_partition_paths()
        groups = (
            self.shared_resource_paths,
            self.derived_reconciliation_paths,
            self.profile_static_zero_paths,
            self.emittable_owner_paths,
        )
        flattened = tuple(path for group in groups for path in group)
        if (
            _issuer is not _PARTITION_ISSUER
            or self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage.stage_profile_id
            or self.comparison_profile_id != comparison.comparison_profile_id
            or self.actual_projection_profile_id
            != projection.actual_projection_profile_id
            or self.boundary_manifest_id != manifest.manifest_id
            or self.execution_profile_id != execution_profile.profile_id
            or groups != expected
            or tuple(map(len, groups))
            != (
                EXPECTED_SHARED_RESOURCE_PATH_COUNT,
                EXPECTED_DERIVED_PATH_COUNT,
                EXPECTED_PROFILE_STATIC_ZERO_PATH_COUNT,
                EXPECTED_EMITTABLE_OWNER_PATH_COUNT,
            )
            or len(flattened) != EXPECTED_REQUIRED_PATH_COUNT
            or len(set(flattened)) != EXPECTED_REQUIRED_PATH_COUNT
            or set(flattened) != set(registry.required_paths)
        ):
            raise ConstructionAccountingCompletionReadinessV1Error(
                "required-path partition differs from the exact 9+8+114+71 V6 disposition"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_required_path_partition.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "execution_profile_id": self.execution_profile_id,
            "required_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "shared_resource_paths": list(self.shared_resource_paths),
            "derived_reconciliation_paths": list(self.derived_reconciliation_paths),
            "profile_static_zero_paths": list(self.profile_static_zero_paths),
            "emittable_owner_paths": list(self.emittable_owner_paths),
            "partition_counts": {
                "shared_resource": len(self.shared_resource_paths),
                "derived_reconciliation": len(self.derived_reconciliation_paths),
                "profile_static_zero": len(self.profile_static_zero_paths),
                "emittable_owner": len(self.emittable_owner_paths),
            },
            "exact_disjoint_union": True,
        }

    @property
    def partition_id(self) -> str:
        return _content_id(REQUIRED_PATH_PARTITION_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "required_path_partition_id": self.partition_id}


@lru_cache(maxsize=1)
def official_required_path_partition_v1() -> RequiredPathPartitionV1:
    registry, stage, comparison, projection, manifest, execution_profile = (
        _exact_authorities()
    )
    shared, derived, profile_zero, emittable = _expected_partition_paths()
    return RequiredPathPartitionV1(
        _PARTITION_ISSUER,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        projection.actual_projection_profile_id,
        manifest.manifest_id,
        execution_profile.profile_id,
        shared,
        derived,
        profile_zero,
        emittable,
    )


@dataclass(frozen=True, slots=True)
class CompletionReadinessBlockerV1:
    _issuer: InitVar[object]
    code: CompletionReadinessBlockerCodeV1
    affected_paths: tuple[str, ...]
    reason: str

    def __post_init__(self, _issuer: object) -> None:
        try:
            code = CompletionReadinessBlockerCodeV1(self.code)
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingCompletionReadinessV1Error(
                "unknown completion blocker code"
            ) from error
        object.__setattr__(self, "code", code)
        _canonical_paths(self.affected_paths, "blocker affected_paths")
        if (
            _issuer is not _BLOCKER_ISSUER
            or not self.affected_paths
            or self.reason != _BLOCKER_REASONS[code]
        ):
            raise ConstructionAccountingCompletionReadinessV1Error(
                "completion blocker is caller-minted or noncanonical"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_completion_readiness_blocker.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "code": self.code.value,
            "affected_paths": list(self.affected_paths),
            "reason": self.reason,
        }

    @property
    def blocker_id(self) -> str:
        return _content_id(COMPLETION_READINESS_BLOCKER_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "completion_blocker_id": self.blocker_id}


def _blocker(
    code: CompletionReadinessBlockerCodeV1,
    paths: tuple[str, ...],
) -> CompletionReadinessBlockerV1:
    return CompletionReadinessBlockerV1(
        _BLOCKER_ISSUER, code, tuple(sorted(paths)), _BLOCKER_REASONS[code]
    )


def _expected_blockers(
    partition: RequiredPathPartitionV1,
    unresolved_paths: tuple[str, ...],
) -> tuple[CompletionReadinessBlockerV1, ...]:
    unresolved = set(unresolved_paths)
    result = [
        _blocker(
            CompletionReadinessBlockerCodeV1.EVIDENCE_CLOSURE_INCOMPLETE,
            unresolved_paths,
        ),
        _blocker(
            CompletionReadinessBlockerCodeV1.SHARED_RESOURCE_RECEIPTS_NOT_LIVE_CLOSED,
            partition.shared_resource_paths,
        ),
        _blocker(
            CompletionReadinessBlockerCodeV1.MOUNTED_BYTES_PEAK_NOT_LIVE_CLOSED,
            (MOUNTED_PEAK_PATH,),
        ),
        _blocker(
            CompletionReadinessBlockerCodeV1.WORKING_BYTES_PEAK_NOT_LIVE_CLOSED,
            (WORKING_PEAK_PATH,),
        ),
        _blocker(
            CompletionReadinessBlockerCodeV1.FORMAL_ACCOUNTING_ARTIFACTS_FORBIDDEN,
            unresolved_paths,
        ),
    ]
    category_codes = (
        (
            partition.derived_reconciliation_paths,
            CompletionReadinessBlockerCodeV1.DERIVED_RECONCILIATION_INCOMPLETE,
        ),
        (
            partition.emittable_owner_paths,
            CompletionReadinessBlockerCodeV1.EMITTABLE_OWNER_EVIDENCE_INCOMPLETE,
        ),
        (
            partition.profile_static_zero_paths,
            CompletionReadinessBlockerCodeV1.PROFILE_STATIC_ZERO_EVIDENCE_INCOMPLETE,
        ),
    )
    for paths, code in category_codes:
        affected = tuple(path for path in paths if path in unresolved)
        if affected:
            result.append(_blocker(code, affected))
    return tuple(sorted(result, key=lambda item: item.code.value))


@dataclass(frozen=True, slots=True)
class CurrentSameProcessCompletionReadinessV1:
    """Negative readiness result for one exact partial EvidenceClosure."""

    _issuer: InitVar[object]
    partition: RequiredPathPartitionV1 = field(repr=False)
    evidence_closure_id: str
    evidence_closure_context_id: str
    evidence_closure_verification_id: str
    unresolved_paths: tuple[str, ...]
    blockers: tuple[CompletionReadinessBlockerV1, ...] = field(repr=False)
    status: CompletionReadinessStatusV1 = (
        CompletionReadinessStatusV1.NOT_READY_PARTIAL_EVIDENCE
    )

    def __post_init__(self, _issuer: object) -> None:
        if type(self.partition) is not RequiredPathPartitionV1:
            raise ConstructionAccountingCompletionReadinessV1Error(
                "readiness partition has a foreign type"
            )
        for name in (
            "evidence_closure_id",
            "evidence_closure_context_id",
            "evidence_closure_verification_id",
        ):
            _cid(getattr(self, name), name)
        _canonical_paths(self.unresolved_paths, "readiness unresolved_paths")
        try:
            status = CompletionReadinessStatusV1(self.status)
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingCompletionReadinessV1Error(
                "unknown completion readiness status"
            ) from error
        object.__setattr__(self, "status", status)
        if (
            _issuer is not _READINESS_ISSUER
            or status
            is not CompletionReadinessStatusV1.NOT_READY_PARTIAL_EVIDENCE
            or not self.unresolved_paths
            or type(self.blockers) is not tuple
            or any(type(item) is not CompletionReadinessBlockerV1 for item in self.blockers)
            or self.blockers != _expected_blockers(self.partition, self.unresolved_paths)
            or not set(self.partition.shared_resource_paths)
            <= set(self.unresolved_paths)
        ):
            raise ConstructionAccountingCompletionReadinessV1Error(
                "same-process readiness differs from its deterministic partial state"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_completion_readiness.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "required_path_partition_id": self.partition.partition_id,
            "evidence_closure_id": self.evidence_closure_id,
            "evidence_closure_context_id": self.evidence_closure_context_id,
            "evidence_closure_verification_id": self.evidence_closure_verification_id,
            "status": self.status.value,
            "unresolved_path_count": len(self.unresolved_paths),
            "unresolved_paths": list(self.unresolved_paths),
            "blocker_ids": [item.blocker_id for item in self.blockers],
            "deterministic_blocker_codes": [item.code.value for item in self.blockers],
            "shared_resource_path_count": EXPECTED_SHARED_RESOURCE_PATH_COUNT,
            "shared_resource_live_closed": False,
            "shared_resource_live_closed_paths": [],
            "mounted_bytes_peak_live_closed": False,
            "working_bytes_peak_live_closed": False,
            "missing_paths_inferred_zero": False,
            "counter_records_allowed": False,
            "work_vector_allowed": False,
            "comparison_vector_allowed": False,
            "formal_vectors_forbidden": True,
            "official_execution_allowed": False,
        }

    @property
    def readiness_id(self) -> str:
        return _content_id(COMPLETION_READINESS_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "completion_readiness_id": self.readiness_id}


def evaluate_current_same_process_completion_readiness_v1(
    closure: evidence.EvidenceClosureV1,
) -> CurrentSameProcessCompletionReadinessV1:
    """Return deterministic blockers for an exact still-partial K7 closure."""

    if type(closure) is not evidence.EvidenceClosureV1:
        raise ConstructionAccountingCompletionReadinessV1Error(
            "completion readiness requires one exact EvidenceClosureV1"
        )
    partition = official_required_path_partition_v1()
    registry, stage, _comparison, _projection, manifest, execution_profile = (
        _exact_authorities()
    )
    context = closure.context
    if (
        context.counter_registry_id != registry.registry_id
        or context.stage_profile_id != stage.stage_profile_id
        or context.boundary_profile_id != manifest.manifest_id
        or context.execution_profile_id != execution_profile.profile_id
    ):
        raise ConstructionAccountingCompletionReadinessV1Error(
            "EvidenceClosure context is not the exact K7 V3/V6 execution chain"
        )
    try:
        verification = evidence.verify_evidence_closure_coverage_v1(
            closure, registry=registry
        )
    except Exception as error:
        raise ConstructionAccountingCompletionReadinessV1Error(
            "EvidenceClosure coverage replay failed"
        ) from error
    unresolved = verification.unresolved_paths
    if (
        verification.completeness
        is not evidence.EvidenceClosureCompletenessV1.INCOMPLETE
        or not unresolved
        or not set(partition.shared_resource_paths) <= set(unresolved)
        or any(
            closure.by_path[path].resolution_kind
            is not evidence.RequiredPathResolutionKindV1.UNRESOLVED
            for path in partition.shared_resource_paths
        )
    ):
        raise ConstructionAccountingCompletionReadinessV1Error(
            "current same-process readiness requires all nine shared paths to remain UNRESOLVED"
        )
    return CurrentSameProcessCompletionReadinessV1(
        _READINESS_ISSUER,
        partition,
        closure.closure_id,
        context.context_id,
        verification.verification_id,
        unresolved,
        _expected_blockers(partition, unresolved),
    )


def verify_current_same_process_completion_readiness_v1(
    readiness: CurrentSameProcessCompletionReadinessV1,
    *,
    closure: evidence.EvidenceClosureV1,
) -> CurrentSameProcessCompletionReadinessV1:
    """Replay the negative readiness result against its exact closure."""

    if type(readiness) is not CurrentSameProcessCompletionReadinessV1:
        raise ConstructionAccountingCompletionReadinessV1Error(
            "readiness verifier requires one exact readiness artifact"
        )
    expected = evaluate_current_same_process_completion_readiness_v1(closure)
    if readiness != expected or readiness.readiness_id != expected.readiness_id:
        raise ConstructionAccountingCompletionReadinessV1Error(
            "completion readiness differs from deterministic replay"
        )
    return readiness


__all__ = [
    "COMPLETION_READINESS_BLOCKER_V1_DOMAIN",
    "COMPLETION_READINESS_V1_DOMAIN",
    "CompletionReadinessBlockerCodeV1",
    "CompletionReadinessBlockerV1",
    "CompletionReadinessStatusV1",
    "ConstructionAccountingCompletionReadinessV1Error",
    "CurrentSameProcessCompletionReadinessV1",
    "EXPECTED_DERIVED_PATH_COUNT",
    "EXPECTED_EMITTABLE_OWNER_PATH_COUNT",
    "EXPECTED_PROFILE_STATIC_ZERO_PATH_COUNT",
    "EXPECTED_REQUIRED_PATH_COUNT",
    "EXPECTED_SHARED_RESOURCE_PATH_COUNT",
    "LOCAL_DOMAIN_TAGS",
    "MOUNTED_PEAK_PATH",
    "PROFILE_KEY",
    "REQUIRED_PATH_PARTITION_V1_DOMAIN",
    "RequiredPathPartitionV1",
    "SCHEMA_VERSION",
    "WORKING_PEAK_PATH",
    "evaluate_current_same_process_completion_readiness_v1",
    "official_required_path_partition_v1",
    "verify_current_same_process_completion_readiness_v1",
]
