"""Exact K7 native-zero rules and owner-boundary coverage, schema only.

The 202 required V6 paths split into 9 shared-resource receipts, 8 derived
reconciliations, 114 profile-static-zero candidates, and 71 owner-emittable
paths.  This module freezes the latter two catalogues for the exact V0-075 K7
root-cap execution identity.

It does not issue a native-zero attestation.  Every zero rule requires exact
stage, branch, loaded-code, execution-identity, and semantic-verifier evidence;
absence of an operation event is never accepted as zero.  Likewise, the 89
owner-boundary sites are frozen as coverage obligations, not as proof that a
live event was emitted.  No formal accounting vector is constructed here.

All domain tags are registered centrally in :mod:`acfqp.phase3e_ids`.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import LaneEnum, ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import (
    CONSTRUCTION_OWNER_BOUNDARY_COVERAGE_PROFILE_V1_DOMAIN,
    CONSTRUCTION_OWNER_BOUNDARY_COVERAGE_SITE_V1_DOMAIN,
    CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_READINESS_ROW_V1_DOMAIN,
    CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_READINESS_V1_DOMAIN,
    CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_REGISTRY_V1_DOMAIN,
    CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_V1_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as execution
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_profile_native_zero_rules_v1"

PROFILE_NATIVE_ZERO_RULE_V1_DOMAIN = (
    CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_V1_DOMAIN
)
PROFILE_NATIVE_ZERO_RULE_REGISTRY_V1_DOMAIN = (
    CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_REGISTRY_V1_DOMAIN
)
PROFILE_NATIVE_ZERO_RULE_READINESS_ROW_V1_DOMAIN = (
    CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_READINESS_ROW_V1_DOMAIN
)
PROFILE_NATIVE_ZERO_RULE_READINESS_V1_DOMAIN = (
    CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_READINESS_V1_DOMAIN
)
OWNER_BOUNDARY_COVERAGE_SITE_V1_DOMAIN = (
    CONSTRUCTION_OWNER_BOUNDARY_COVERAGE_SITE_V1_DOMAIN
)
OWNER_BOUNDARY_COVERAGE_PROFILE_V1_DOMAIN = (
    CONSTRUCTION_OWNER_BOUNDARY_COVERAGE_PROFILE_V1_DOMAIN
)

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "CONSTRUCTION_OWNER_BOUNDARY_COVERAGE_PROFILE_V1_DOMAIN",
    "CONSTRUCTION_OWNER_BOUNDARY_COVERAGE_SITE_V1_DOMAIN",
    "CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_READINESS_ROW_V1_DOMAIN",
    "CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_READINESS_V1_DOMAIN",
    "CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_REGISTRY_V1_DOMAIN",
    "CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_V1_DOMAIN",
)

LOCAL_DOMAIN_TAGS = frozenset(
    {
        PROFILE_NATIVE_ZERO_RULE_V1_DOMAIN,
        PROFILE_NATIVE_ZERO_RULE_REGISTRY_V1_DOMAIN,
        PROFILE_NATIVE_ZERO_RULE_READINESS_ROW_V1_DOMAIN,
        PROFILE_NATIVE_ZERO_RULE_READINESS_V1_DOMAIN,
        OWNER_BOUNDARY_COVERAGE_SITE_V1_DOMAIN,
        OWNER_BOUNDARY_COVERAGE_PROFILE_V1_DOMAIN,
    }
)

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_SHARED_RESOURCE_PATH_COUNT = 9
EXPECTED_DERIVED_PATH_COUNT = 8
EXPECTED_PROFILE_NATIVE_ZERO_RULE_COUNT = 114
EXPECTED_OWNER_EMITTABLE_PATH_COUNT = 71
EXPECTED_OWNER_EMITTABLE_SITE_COUNT = 89

SHARED_RESOURCE_PATHS = frozenset(
    {
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.mounted_bytes_peak",
        "io.output_bytes",
        "io.read_bytes",
        "io.staged_bytes",
        "memory.working_bytes_peak",
        "process.launches",
    }
)

_RULE_ISSUER = object()
_REGISTRY_ISSUER = object()
_READINESS_ROW_ISSUER = object()
_READINESS_ISSUER = object()
_COVERAGE_SITE_ISSUER = object()
_COVERAGE_PROFILE_ISSUER = object()


class ConstructionProfileNativeZeroRulesV1Error(ValueError):
    """A zero-rule or owner-boundary authority is malformed or stale."""


class ProfileNativeZeroLiveEvidenceNotReady(RuntimeError):
    """The schema catalogue cannot issue a live native-zero attestation."""


class ProfileNativeZeroReasonCodeV1(str, Enum):
    FORBIDDEN_STAGE_NOT_EXECUTED = "FORBIDDEN_STAGE_NOT_EXECUTED"
    K7_PROFILE_BRANCH_NOT_EXECUTED = "K7_PROFILE_BRANCH_NOT_EXECUTED"
    LEGACY_OWNER_REPLACED = "LEGACY_OWNER_REPLACED"
    LEGACY_SEMANTIC_SPLIT_REPLACED = "LEGACY_SEMANTIC_SPLIT_REPLACED"


class ProfileNativeZeroEvidenceKindV1(str, Enum):
    BRANCH_NONEXECUTION = "BRANCH_NONEXECUTION"
    EXECUTION_IDENTITY = "EXECUTION_IDENTITY"
    LOADED_CODE_IDENTITY = "LOADED_CODE_IDENTITY"
    REPLACEMENT_PATH_RESOLUTION = "REPLACEMENT_PATH_RESOLUTION"
    STAGE_EXECUTION = "STAGE_EXECUTION"
    ZERO_SEMANTIC_VERIFIER = "ZERO_SEMANTIC_VERIFIER"


class ProfileNativeZeroRuleReadinessStatusV1(str, Enum):
    BLOCKED_MISSING_PREREQUISITES = "BLOCKED_MISSING_PREREQUISITES"


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        raise ConstructionProfileNativeZeroRulesV1Error(
            "native-zero catalogue used an unknown local domain"
        )
    return content_id(domain, dict(payload))


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionProfileNativeZeroRulesV1Error(
            f"{field_name} must be one full content ID"
        ) from error


def _sorted_unique(values: Any, field_name: str) -> tuple[Any, ...]:
    if (
        type(values) is not tuple
        or tuple(sorted(values)) != values
        or len(set(values)) != len(values)
    ):
        raise ConstructionProfileNativeZeroRulesV1Error(
            f"{field_name} must be one sorted unique tuple"
        )
    return values


@lru_cache(maxsize=1)
def _authorities() -> tuple[Any, Any, Any, Any, Any, Any]:
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
        raise ConstructionProfileNativeZeroRulesV1Error(
            "an exact V3/V6 authority rejected replay"
        ) from error
    if (
        manifest.counter_registry_id != registry.registry_id
        or manifest.stage_profile_id != stage.stage_profile_id
        or manifest.comparison_profile_id != comparison.comparison_profile_id
        or manifest.actual_projection_profile_id
        != projection.actual_projection_profile_id
        or execution_profile.boundary_manifest_id != manifest.manifest_id
    ):
        raise ConstructionProfileNativeZeroRulesV1Error(
            "K7 V3/V6/execution authority chain changed"
        )
    return registry, stage, comparison, projection, manifest, execution_profile


def _emittable_boundaries(manifest: Any) -> tuple[Any, ...]:
    result = tuple(
        row
        for row in manifest.boundaries
        if row.to_document()["emittable_in_this_fixture"] is True
    )
    if (
        len(result) != EXPECTED_OWNER_EMITTABLE_SITE_COUNT
        or len({row.target_path for row in result})
        != EXPECTED_OWNER_EMITTABLE_PATH_COUNT
    ):
        raise ConstructionProfileNativeZeroRulesV1Error(
            "emittable V3 boundary cardinality changed"
        )
    return result


@lru_cache(maxsize=1)
def _partition_paths() -> tuple[
    tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]
]:
    registry, _stage, _comparison, _projection, manifest, _execution = (
        _authorities()
    )
    shared = tuple(sorted(SHARED_RESOURCE_PATHS))
    derived = tuple(
        path
        for path in registry.required_paths
        if registry.by_path[path].lane is LaneEnum.DERIVED_ONLY
    )
    emittable = tuple(
        sorted({row.target_path for row in _emittable_boundaries(manifest)})
    )
    zero = tuple(
        sorted(set(registry.required_paths) - set(shared) - set(derived) - set(emittable))
    )
    flattened = (*shared, *derived, *zero, *emittable)
    if (
        tuple(map(len, (shared, derived, zero, emittable)))
        != (
            EXPECTED_SHARED_RESOURCE_PATH_COUNT,
            EXPECTED_DERIVED_PATH_COUNT,
            EXPECTED_PROFILE_NATIVE_ZERO_RULE_COUNT,
            EXPECTED_OWNER_EMITTABLE_PATH_COUNT,
        )
        or len(flattened) != EXPECTED_REQUIRED_PATH_COUNT
        or len(set(flattened)) != EXPECTED_REQUIRED_PATH_COUNT
        or set(flattened) != set(registry.required_paths)
    ):
        raise ConstructionProfileNativeZeroRulesV1Error(
            "required path disposition is not the exact 9+8+114+71 partition"
        )
    return shared, derived, zero, emittable


def _applicable_stages(path: str, stage_profile: Any) -> tuple[str, ...]:
    return tuple(
        sorted(
            stage.value
            for stage, rule in stage_profile.by_stage.items()
            if path in rule.allowed_nonzero_paths
        )
    )


def _rule_reason(
    *,
    path: str,
    rows: tuple[Any, ...],
    applicable_stages: tuple[str, ...],
) -> tuple[ProfileNativeZeroReasonCodeV1, str, tuple[str, ...]]:
    classifications = {row.classification for row in rows}
    replacements = tuple(
        sorted({value for row in rows for value in row.replacement_paths})
    )
    if (
        boundary_v3.OperationBoundaryClassificationV3
        .LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN
        in classifications
    ):
        code = ProfileNativeZeroReasonCodeV1.LEGACY_SEMANTIC_SPLIT_REPLACED
        reason = (
            f"{path} is a legacy semantically conflated leaf replaced by the exact "
            f"owner families {', '.join(replacements)}; zero requires proof that "
            "the legacy operation never executed and every replacement is reconciled"
        )
    elif (
        boundary_v3.OperationBoundaryClassificationV3
        .LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN
        in classifications
    ):
        code = ProfileNativeZeroReasonCodeV1.LEGACY_OWNER_REPLACED
        reason = (
            f"{path} is a legacy owner-mismatched leaf replaced by "
            f"{', '.join(replacements)}; zero requires old-owner nonexecution and "
            "replacement-path resolution evidence"
        )
    elif (
        boundary_v3.OperationBoundaryClassificationV3
        .OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO
        in classifications
    ):
        code = ProfileNativeZeroReasonCodeV1.FORBIDDEN_STAGE_NOT_EXECUTED
        reason = (
            f"{path} is registered only for the K7-forbidden stage set "
            f"{', '.join(applicable_stages)}; zero requires exact stage nonentry, "
            "branch, and loaded-code evidence"
        )
    else:
        code = ProfileNativeZeroReasonCodeV1.K7_PROFILE_BRANCH_NOT_EXECUTED
        reason = (
            f"{path} has no owner-emittable V3 site in the exact K7 root-cap graph; "
            "zero requires a path-specific stage transcript, branch nonexecution "
            "proof, and loaded-code identity"
        )
    return code, reason, replacements


def _evidence_requirements(
    path: str,
    *,
    replacements: tuple[str, ...],
) -> tuple[tuple[ProfileNativeZeroEvidenceKindV1, str], ...]:
    result = [
        (
            ProfileNativeZeroEvidenceKindV1.BRANCH_NONEXECUTION,
            f"branch_nonexecution:{path}",
        ),
        (
            ProfileNativeZeroEvidenceKindV1.EXECUTION_IDENTITY,
            f"execution_identity:{path}",
        ),
        (
            ProfileNativeZeroEvidenceKindV1.LOADED_CODE_IDENTITY,
            f"loaded_code_identity:{path}",
        ),
        (
            ProfileNativeZeroEvidenceKindV1.STAGE_EXECUTION,
            f"stage_execution:{path}",
        ),
        (
            ProfileNativeZeroEvidenceKindV1.ZERO_SEMANTIC_VERIFIER,
            f"zero_semantic_verifier:{path}",
        ),
    ]
    if replacements:
        result.append(
            (
                ProfileNativeZeroEvidenceKindV1.REPLACEMENT_PATH_RESOLUTION,
                f"replacement_path_resolution:{path}",
            )
        )
    return tuple(sorted(result, key=lambda item: (item[0].value, item[1])))


@dataclass(frozen=True, slots=True)
class ProfileNativeZeroEvidenceRequirementV1:
    kind: ProfileNativeZeroEvidenceKindV1
    obligation_key: str

    def __post_init__(self) -> None:
        try:
            kind = ProfileNativeZeroEvidenceKindV1(self.kind)
        except (TypeError, ValueError) as error:
            raise ConstructionProfileNativeZeroRulesV1Error(
                "unknown native-zero evidence requirement"
            ) from error
        object.__setattr__(self, "kind", kind)
        if (
            type(self.obligation_key) is not str
            or not self.obligation_key
            or ":" not in self.obligation_key
        ):
            raise ConstructionProfileNativeZeroRulesV1Error(
                "native-zero evidence obligation key is noncanonical"
            )

    def to_document(self) -> dict[str, str]:
        return {"kind": self.kind.value, "obligation_key": self.obligation_key}


@dataclass(frozen=True, slots=True)
class ProfileNativeZeroRuleV1:
    _issuer: InitVar[object]
    counter_registry_id: str
    boundary_manifest_id: str
    execution_profile_id: str
    path: str
    semantics_id: str
    registered_owner: str
    unit: str
    scope: str
    reducer: ReducerEnum
    applicable_stages: tuple[str, ...]
    source_boundary_ids: tuple[str, ...]
    replacement_paths: tuple[str, ...]
    reason_code: ProfileNativeZeroReasonCodeV1
    path_specific_reason: str
    evidence_requirements: tuple[ProfileNativeZeroEvidenceRequirementV1, ...]

    def __post_init__(self, _issuer: object) -> None:
        for value, name in (
            (self.counter_registry_id, "zero-rule registry"),
            (self.boundary_manifest_id, "zero-rule manifest"),
            (self.execution_profile_id, "zero-rule execution profile"),
        ):
            _cid(value, name)
        try:
            reducer = ReducerEnum(self.reducer)
            reason_code = ProfileNativeZeroReasonCodeV1(self.reason_code)
        except (TypeError, ValueError) as error:
            raise ConstructionProfileNativeZeroRulesV1Error(
                "zero-rule reducer or reason code is invalid"
            ) from error
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "reason_code", reason_code)
        for name in (
            "applicable_stages",
            "source_boundary_ids",
            "replacement_paths",
        ):
            _sorted_unique(getattr(self, name), name)
        for value in self.source_boundary_ids:
            _cid(value, "zero-rule source boundary")
        if (
            type(self.evidence_requirements) is not tuple
            or any(
                type(item) is not ProfileNativeZeroEvidenceRequirementV1
                for item in self.evidence_requirements
            )
            or tuple(
                sorted(
                    self.evidence_requirements,
                    key=lambda item: (item.kind.value, item.obligation_key),
                )
            )
            != self.evidence_requirements
            or len({item.obligation_key for item in self.evidence_requirements})
            != len(self.evidence_requirements)
        ):
            raise ConstructionProfileNativeZeroRulesV1Error(
                "zero-rule evidence requirements are noncanonical"
            )
        kinds = {item.kind for item in self.evidence_requirements}
        if not {
            ProfileNativeZeroEvidenceKindV1.BRANCH_NONEXECUTION,
            ProfileNativeZeroEvidenceKindV1.EXECUTION_IDENTITY,
            ProfileNativeZeroEvidenceKindV1.LOADED_CODE_IDENTITY,
            ProfileNativeZeroEvidenceKindV1.STAGE_EXECUTION,
            ProfileNativeZeroEvidenceKindV1.ZERO_SEMANTIC_VERIFIER,
        } <= kinds:
            raise ConstructionProfileNativeZeroRulesV1Error(
                "zero rule omits stage, branch, code, identity, or verifier evidence"
            )
        registry, _stage, _comparison, _projection, manifest, profile = _authorities()
        leaf = registry.by_path.get(self.path)
        rows = tuple(
            row for row in manifest.boundaries if row.target_path == self.path
        )
        code, reason, replacements = _rule_reason(
            path=self.path,
            rows=rows,
            applicable_stages=self.applicable_stages,
        )
        expected_requirements = tuple(
            ProfileNativeZeroEvidenceRequirementV1(kind, key)
            for kind, key in _evidence_requirements(
                self.path, replacements=replacements
            )
        )
        if (
            _issuer is not _RULE_ISSUER
            or self.path not in _partition_paths()[2]
            or leaf is None
            or self.counter_registry_id != registry.registry_id
            or self.boundary_manifest_id != manifest.manifest_id
            or self.execution_profile_id != profile.profile_id
            or self.semantics_id != leaf.semantics_id
            or self.registered_owner != leaf.owner
            or self.unit != leaf.unit
            or self.scope != leaf.scope
            or reducer is not leaf.reducer
            or self.applicable_stages
            != _applicable_stages(self.path, _stage)
            or self.source_boundary_ids
            != tuple(sorted(row.boundary_id for row in rows))
            or self.replacement_paths != replacements
            or reason_code is not code
            or self.path_specific_reason != reason
            or self.evidence_requirements != expected_requirements
        ):
            raise ConstructionProfileNativeZeroRulesV1Error(
                "profile-native-zero rule differs from exact V3/V6 derivation"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_profile_native_zero_rule.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "execution_profile_id": self.execution_profile_id,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "registered_owner": self.registered_owner,
            "unit": self.unit,
            "scope": self.scope,
            "reducer": self.reducer.value,
            "applicable_stages": list(self.applicable_stages),
            "source_boundary_ids": list(self.source_boundary_ids),
            "replacement_paths": list(self.replacement_paths),
            "reason_code": self.reason_code.value,
            "path_specific_reason": self.path_specific_reason,
            "evidence_requirements": [
                item.to_document() for item in self.evidence_requirements
            ],
            "absence_is_zero_evidence": False,
            "live_attestation_allowed": False,
            "native_zero_attestation_issued": False,
        }

    @property
    def rule_id(self) -> str:
        return _content_id(PROFILE_NATIVE_ZERO_RULE_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_native_zero_rule_id": self.rule_id}


def _freeze_rule(path: str) -> ProfileNativeZeroRuleV1:
    registry, stage, _comparison, _projection, manifest, profile = _authorities()
    leaf = registry.by_path[path]
    rows = tuple(row for row in manifest.boundaries if row.target_path == path)
    stages = _applicable_stages(path, stage)
    code, reason, replacements = _rule_reason(
        path=path, rows=rows, applicable_stages=stages
    )
    requirements = tuple(
        ProfileNativeZeroEvidenceRequirementV1(kind, key)
        for kind, key in _evidence_requirements(path, replacements=replacements)
    )
    return ProfileNativeZeroRuleV1(
        _RULE_ISSUER,
        registry.registry_id,
        manifest.manifest_id,
        profile.profile_id,
        path,
        leaf.semantics_id,
        leaf.owner,
        leaf.unit,
        leaf.scope,
        leaf.reducer,
        stages,
        tuple(sorted(row.boundary_id for row in rows)),
        replacements,
        code,
        reason,
        requirements,
    )


@dataclass(frozen=True, slots=True)
class ProfileNativeZeroRuleRegistryV1:
    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundary_manifest_id: str
    execution_profile_id: str
    rules: tuple[ProfileNativeZeroRuleV1, ...] = field(repr=False)

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
        registry, stage, comparison, projection, manifest, profile = _authorities()
        if (
            _issuer is not _REGISTRY_ISSUER
            or self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage.stage_profile_id
            or self.comparison_profile_id != comparison.comparison_profile_id
            or self.actual_projection_profile_id
            != projection.actual_projection_profile_id
            or self.boundary_manifest_id != manifest.manifest_id
            or self.execution_profile_id != profile.profile_id
            or type(self.rules) is not tuple
            or len(self.rules) != EXPECTED_PROFILE_NATIVE_ZERO_RULE_COUNT
            or any(type(item) is not ProfileNativeZeroRuleV1 for item in self.rules)
            or tuple(item.path for item in self.rules) != _partition_paths()[2]
            or len({item.rule_id for item in self.rules}) != len(self.rules)
        ):
            raise ConstructionProfileNativeZeroRulesV1Error(
                "native-zero rule registry differs from the exact 114-path catalogue"
            )

    @property
    def by_path(self) -> dict[str, ProfileNativeZeroRuleV1]:
        return {item.path: item for item in self.rules}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_profile_native_zero_rule_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "execution_profile_id": self.execution_profile_id,
            "rule_count": len(self.rules),
            "rule_ids": [item.rule_id for item in self.rules],
            "paths": [item.path for item in self.rules],
            "absence_is_zero_evidence": False,
            "live_attestation_api_available": False,
            "native_zero_attestations_issued": False,
            "formal_vectors_allowed": False,
        }

    @property
    def registry_id(self) -> str:
        return _content_id(
            PROFILE_NATIVE_ZERO_RULE_REGISTRY_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_native_zero_rule_registry_id": self.registry_id}


@lru_cache(maxsize=1)
def official_profile_native_zero_rule_registry_v1(
) -> ProfileNativeZeroRuleRegistryV1:
    registry, stage, comparison, projection, manifest, profile = _authorities()
    return ProfileNativeZeroRuleRegistryV1(
        _REGISTRY_ISSUER,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        projection.actual_projection_profile_id,
        manifest.manifest_id,
        profile.profile_id,
        tuple(_freeze_rule(path) for path in _partition_paths()[2]),
    )


@dataclass(frozen=True, slots=True)
class ProfileNativeZeroRuleReadinessRowV1:
    _issuer: InitVar[object]
    rule_id: str
    path: str
    missing_obligation_keys: tuple[str, ...]
    status: ProfileNativeZeroRuleReadinessStatusV1

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.rule_id, "zero-readiness rule")
        _sorted_unique(self.missing_obligation_keys, "missing_obligation_keys")
        try:
            status = ProfileNativeZeroRuleReadinessStatusV1(self.status)
        except (TypeError, ValueError) as error:
            raise ConstructionProfileNativeZeroRulesV1Error(
                "unknown native-zero readiness status"
            ) from error
        object.__setattr__(self, "status", status)
        rules = official_profile_native_zero_rule_registry_v1().by_path
        rule = rules.get(self.path)
        expected = tuple(
            sorted(item.obligation_key for item in rule.evidence_requirements)
        ) if rule is not None else ()
        if (
            _issuer is not _READINESS_ROW_ISSUER
            or rule is None
            or rule.rule_id != self.rule_id
            or self.missing_obligation_keys != expected
            or status
            is not ProfileNativeZeroRuleReadinessStatusV1.BLOCKED_MISSING_PREREQUISITES
        ):
            raise ConstructionProfileNativeZeroRulesV1Error(
                "native-zero readiness row differs from its unsatisfied rule"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_profile_native_zero_rule_readiness_row.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "rule_id": self.rule_id,
            "path": self.path,
            "status": self.status.value,
            "satisfied_obligation_keys": [],
            "missing_obligation_keys": list(self.missing_obligation_keys),
            "stage_evidence_present": False,
            "branch_evidence_present": False,
            "loaded_code_evidence_present": False,
            "live_attestation_allowed": False,
        }

    @property
    def readiness_row_id(self) -> str:
        return _content_id(
            PROFILE_NATIVE_ZERO_RULE_READINESS_ROW_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "native_zero_readiness_row_id": self.readiness_row_id}


@dataclass(frozen=True, slots=True)
class ProfileNativeZeroRuleReadinessV1:
    _issuer: InitVar[object]
    rule_registry_id: str
    rows: tuple[ProfileNativeZeroRuleReadinessRowV1, ...] = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.rule_registry_id, "zero readiness registry")
        registry = official_profile_native_zero_rule_registry_v1()
        if (
            _issuer is not _READINESS_ISSUER
            or self.rule_registry_id != registry.registry_id
            or type(self.rows) is not tuple
            or len(self.rows) != EXPECTED_PROFILE_NATIVE_ZERO_RULE_COUNT
            or tuple(item.path for item in self.rows)
            != tuple(item.path for item in registry.rules)
            or any(type(item) is not ProfileNativeZeroRuleReadinessRowV1 for item in self.rows)
            or len({item.readiness_row_id for item in self.rows}) != len(self.rows)
        ):
            raise ConstructionProfileNativeZeroRulesV1Error(
                "native-zero readiness differs from its 114-rule registry"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_profile_native_zero_rule_readiness.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "rule_registry_id": self.rule_registry_id,
            "row_count": len(self.rows),
            "readiness_row_ids": [item.readiness_row_id for item in self.rows],
            "blocked_path_count": len(self.rows),
            "live_ready_path_count": 0,
            "absence_is_zero_evidence": False,
            "native_zero_attestations_issued": False,
            "formal_vectors_allowed": False,
        }

    @property
    def readiness_id(self) -> str:
        return _content_id(
            PROFILE_NATIVE_ZERO_RULE_READINESS_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "native_zero_rule_readiness_id": self.readiness_id}


@lru_cache(maxsize=1)
def current_profile_native_zero_rule_readiness_v1(
) -> ProfileNativeZeroRuleReadinessV1:
    registry = official_profile_native_zero_rule_registry_v1()
    rows = tuple(
        ProfileNativeZeroRuleReadinessRowV1(
            _READINESS_ROW_ISSUER,
            rule.rule_id,
            rule.path,
            tuple(sorted(item.obligation_key for item in rule.evidence_requirements)),
            ProfileNativeZeroRuleReadinessStatusV1.BLOCKED_MISSING_PREREQUISITES,
        )
        for rule in registry.rules
    )
    return ProfileNativeZeroRuleReadinessV1(
        _READINESS_ISSUER, registry.registry_id, rows
    )


@dataclass(frozen=True, slots=True)
class OwnerBoundaryCoverageSiteV1:
    _issuer: InitVar[object]
    boundary_id: str
    boundary_key: str
    dispatch_key: str
    stage: str
    path: str
    registered_owner: str
    reducer: ReducerEnum
    operation_source_module: str
    operation_source_symbol: str
    required_evidence_keys: tuple[str, ...]

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.boundary_id, "owner coverage boundary")
        try:
            reducer = ReducerEnum(self.reducer)
        except (TypeError, ValueError) as error:
            raise ConstructionProfileNativeZeroRulesV1Error(
                "owner coverage reducer is invalid"
            ) from error
        object.__setattr__(self, "reducer", reducer)
        _sorted_unique(self.required_evidence_keys, "owner required_evidence_keys")
        _registry, _stage, _comparison, _projection, manifest, _profile = _authorities()
        matches = tuple(
            row for row in _emittable_boundaries(manifest) if row.boundary_key == self.boundary_key
        )
        expected_keys = tuple(
            sorted(
                (
                    f"active_stage_binding:{self.boundary_key}",
                    f"direct_caller_owner_binding:{self.boundary_key}",
                    f"loaded_module_bytes:{self.boundary_key}",
                    f"runtime_event_transcript:{self.boundary_key}",
                    f"source_symbol_code_identity:{self.boundary_key}",
                )
            )
        )
        if (
            _issuer is not _COVERAGE_SITE_ISSUER
            or len(matches) != 1
            or matches[0].boundary_id != self.boundary_id
            or matches[0].dispatch_key != self.dispatch_key
            or matches[0].stage.value != self.stage
            or matches[0].target_path != self.path
            or matches[0].registered_owner != self.registered_owner
            or matches[0].reducer is not reducer
            or matches[0].operation_source_module != self.operation_source_module
            or matches[0].operation_source_symbol != self.operation_source_symbol
            or self.required_evidence_keys != expected_keys
        ):
            raise ConstructionProfileNativeZeroRulesV1Error(
                "owner-boundary site differs from exact V3 manifest"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_owner_boundary_coverage_site.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "boundary_id": self.boundary_id,
            "boundary_key": self.boundary_key,
            "dispatch_key": self.dispatch_key,
            "stage": self.stage,
            "path": self.path,
            "registered_owner": self.registered_owner,
            "reducer": self.reducer.value,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "required_evidence_keys": list(self.required_evidence_keys),
            "schema_coverage_frozen": True,
            "loaded_code_evidence_present": False,
            "runtime_event_evidence_present": False,
            "live_boundary_closed": False,
        }

    @property
    def coverage_site_id(self) -> str:
        return _content_id(OWNER_BOUNDARY_COVERAGE_SITE_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owner_boundary_coverage_site_id": self.coverage_site_id}


def _freeze_coverage_site(row: Any) -> OwnerBoundaryCoverageSiteV1:
    keys = tuple(
        sorted(
            (
                f"active_stage_binding:{row.boundary_key}",
                f"direct_caller_owner_binding:{row.boundary_key}",
                f"loaded_module_bytes:{row.boundary_key}",
                f"runtime_event_transcript:{row.boundary_key}",
                f"source_symbol_code_identity:{row.boundary_key}",
            )
        )
    )
    return OwnerBoundaryCoverageSiteV1(
        _COVERAGE_SITE_ISSUER,
        row.boundary_id,
        row.boundary_key,
        row.dispatch_key,
        row.stage.value,
        row.target_path,
        row.registered_owner,
        row.reducer,
        row.operation_source_module,
        row.operation_source_symbol,
        keys,
    )


@dataclass(frozen=True, slots=True)
class OwnerBoundaryCoverageProfileV1:
    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    boundary_manifest_id: str
    execution_profile_id: str
    sites: tuple[OwnerBoundaryCoverageSiteV1, ...] = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for name in (
            "counter_registry_id",
            "stage_profile_id",
            "boundary_manifest_id",
            "execution_profile_id",
        ):
            _cid(getattr(self, name), name)
        registry, stage, _comparison, _projection, manifest, profile = _authorities()
        if (
            _issuer is not _COVERAGE_PROFILE_ISSUER
            or self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage.stage_profile_id
            or self.boundary_manifest_id != manifest.manifest_id
            or self.execution_profile_id != profile.profile_id
            or type(self.sites) is not tuple
            or len(self.sites) != EXPECTED_OWNER_EMITTABLE_SITE_COUNT
            or tuple(item.boundary_key for item in self.sites)
            != tuple(row.boundary_key for row in _emittable_boundaries(manifest))
            or len({item.coverage_site_id for item in self.sites}) != len(self.sites)
            or len({item.path for item in self.sites})
            != EXPECTED_OWNER_EMITTABLE_PATH_COUNT
            or tuple(sorted({item.path for item in self.sites}))
            != _partition_paths()[3]
        ):
            raise ConstructionProfileNativeZeroRulesV1Error(
                "owner-boundary coverage is not the exact 71-path/89-site profile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_owner_boundary_coverage_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "execution_profile_id": self.execution_profile_id,
            "emittable_path_count": EXPECTED_OWNER_EMITTABLE_PATH_COUNT,
            "emittable_site_count": EXPECTED_OWNER_EMITTABLE_SITE_COUNT,
            "emittable_paths": list(_partition_paths()[3]),
            "coverage_site_ids": [item.coverage_site_id for item in self.sites],
            "schema_coverage_frozen": True,
            "loaded_code_coverage_ready": False,
            "runtime_event_coverage_ready": False,
            "live_owner_boundaries_closed": False,
            "formal_vectors_allowed": False,
        }

    @property
    def coverage_profile_id(self) -> str:
        return _content_id(
            OWNER_BOUNDARY_COVERAGE_PROFILE_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owner_boundary_coverage_profile_id": self.coverage_profile_id}


@lru_cache(maxsize=1)
def official_owner_boundary_coverage_profile_v1(
) -> OwnerBoundaryCoverageProfileV1:
    registry, stage, _comparison, _projection, manifest, profile = _authorities()
    return OwnerBoundaryCoverageProfileV1(
        _COVERAGE_PROFILE_ISSUER,
        registry.registry_id,
        stage.stage_profile_id,
        manifest.manifest_id,
        profile.profile_id,
        tuple(_freeze_coverage_site(row) for row in _emittable_boundaries(manifest)),
    )


def open_profile_native_zero_attestation_v1(**_unused: Any) -> NoReturn:
    """Fail closed until every rule prerequisite has a semantic verifier."""

    raise ProfileNativeZeroLiveEvidenceNotReady(
        "profile-native-zero attestations are blocked until exact stage, branch, "
        "loaded-code, execution-identity, and zero-verifier evidence is live-closed"
    )


__all__ = [
    "EXPECTED_DERIVED_PATH_COUNT",
    "EXPECTED_OWNER_EMITTABLE_PATH_COUNT",
    "EXPECTED_OWNER_EMITTABLE_SITE_COUNT",
    "EXPECTED_PROFILE_NATIVE_ZERO_RULE_COUNT",
    "EXPECTED_REQUIRED_PATH_COUNT",
    "EXPECTED_SHARED_RESOURCE_PATH_COUNT",
    "LOCAL_DOMAIN_TAGS",
    "OWNER_BOUNDARY_COVERAGE_PROFILE_V1_DOMAIN",
    "OWNER_BOUNDARY_COVERAGE_SITE_V1_DOMAIN",
    "OwnerBoundaryCoverageProfileV1",
    "OwnerBoundaryCoverageSiteV1",
    "PROFILE_KEY",
    "PROFILE_NATIVE_ZERO_RULE_READINESS_ROW_V1_DOMAIN",
    "PROFILE_NATIVE_ZERO_RULE_READINESS_V1_DOMAIN",
    "PROFILE_NATIVE_ZERO_RULE_REGISTRY_V1_DOMAIN",
    "PROFILE_NATIVE_ZERO_RULE_V1_DOMAIN",
    "ProfileNativeZeroEvidenceKindV1",
    "ProfileNativeZeroEvidenceRequirementV1",
    "ProfileNativeZeroLiveEvidenceNotReady",
    "ProfileNativeZeroReasonCodeV1",
    "ProfileNativeZeroRuleReadinessRowV1",
    "ProfileNativeZeroRuleReadinessStatusV1",
    "ProfileNativeZeroRuleReadinessV1",
    "ProfileNativeZeroRuleRegistryV1",
    "ProfileNativeZeroRuleV1",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "SHARED_RESOURCE_PATHS",
    "ConstructionProfileNativeZeroRulesV1Error",
    "current_profile_native_zero_rule_readiness_v1",
    "official_owner_boundary_coverage_profile_v1",
    "official_profile_native_zero_rule_registry_v1",
    "open_profile_native_zero_attestation_v1",
]
