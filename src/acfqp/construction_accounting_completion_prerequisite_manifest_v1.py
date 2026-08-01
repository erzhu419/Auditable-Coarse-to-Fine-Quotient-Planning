"""Content-addressed prerequisite manifest for K7 accounting completion.

This module joins the construction-only V0-099 prerequisite schemas into one
identity chain.  It deliberately represents the current state as ``NOT_READY``:
the existing evidence closure has no independently verified shared-resource
join, occurrence/cutoff authority, owner-site closures, profile-native-zero
attestations, or derived reconciliation proofs.

The manifest is not a ``CounterRecord``, ``WorkVector`` or
``ComparisonVector``.  Its deterministic replay proves only that the exact
authorities and exact missing sets have been bound without omission.  No
numeric value is inferred from an absent event or prerequisite.

All content IDs use the centrally registered Phase 3E domains.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from functools import lru_cache
import re
from typing import Any, Mapping

from acfqp import construction_accounting_completion_readiness_v1 as readiness_v1
from acfqp import construction_accounting_evidence_closure_v1 as closure_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_profile_native_zero_rules_v1 as zero_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_BLOCKER_V1_DOMAIN,
    CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_MANIFEST_V1_DOMAIN,
    CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_REPLAY_V1_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as execution_v1
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_accounting_completion_prerequisite_manifest_v1"

COMPLETION_PREREQUISITE_BLOCKER_V1_DOMAIN = (
    CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_BLOCKER_V1_DOMAIN
)
COMPLETION_PREREQUISITE_MANIFEST_V1_DOMAIN = (
    CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_MANIFEST_V1_DOMAIN
)
COMPLETION_PREREQUISITE_REPLAY_V1_DOMAIN = (
    CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_REPLAY_V1_DOMAIN
)

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_BLOCKER_V1_DOMAIN",
    "CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_MANIFEST_V1_DOMAIN",
    "CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_REPLAY_V1_DOMAIN",
)

LOCAL_DOMAIN_TAGS = frozenset(
    {
        COMPLETION_PREREQUISITE_BLOCKER_V1_DOMAIN,
        COMPLETION_PREREQUISITE_MANIFEST_V1_DOMAIN,
        COMPLETION_PREREQUISITE_REPLAY_V1_DOMAIN,
    }
)

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_SHARED_RESOURCE_PATH_COUNT = 9
EXPECTED_DERIVED_RECONCILIATION_PATH_COUNT = 8
EXPECTED_PROFILE_NATIVE_ZERO_PATH_COUNT = 114
EXPECTED_PROFILE_NATIVE_ZERO_OBLIGATION_COUNT = 588
EXPECTED_OWNER_PATH_COUNT = 71
EXPECTED_OWNER_SITE_COUNT = 89
EXPECTED_OWNER_EVIDENCE_OBLIGATION_COUNT = 445
EXPECTED_BLOCKER_COUNT = 6

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_BLOCKER_ISSUER = object()
_MANIFEST_ISSUER = object()
_REPLAY_ISSUER = object()


class ConstructionAccountingCompletionPrerequisiteV1Error(ValueError):
    """A prerequisite identity, missing set, or replay is invalid."""


class CompletionPrerequisiteStatusV1(str, Enum):
    NOT_READY_MISSING_SEMANTIC_AUTHORITIES = (
        "NOT_READY_MISSING_SEMANTIC_AUTHORITIES"
    )


class CompletionPrerequisiteBlockerCodeV1(str, Enum):
    DERIVED_RECONCILIATION_PROOFS_MISSING = (
        "DERIVED_RECONCILIATION_PROOFS_MISSING"
    )
    OCCURRENCE_IDENTITY_SEMANTIC_AUTHORITY_NOT_AVAILABLE = (
        "OCCURRENCE_IDENTITY_SEMANTIC_AUTHORITY_NOT_AVAILABLE"
    )
    OPERATIONAL_CUTOFF_SEMANTIC_AUTHORITY_NOT_AVAILABLE = (
        "OPERATIONAL_CUTOFF_SEMANTIC_AUTHORITY_NOT_AVAILABLE"
    )
    OWNER_COMPLETE_CLOSURES_MISSING = "OWNER_COMPLETE_CLOSURES_MISSING"
    PROFILE_NATIVE_ZERO_ATTESTATIONS_MISSING = (
        "PROFILE_NATIVE_ZERO_ATTESTATIONS_MISSING"
    )
    SHARED_RESOURCE_SEMANTIC_JOIN_NOT_AVAILABLE = (
        "SHARED_RESOURCE_SEMANTIC_JOIN_NOT_AVAILABLE"
    )


_REQUIRED_ROLES = {
    CompletionPrerequisiteBlockerCodeV1.DERIVED_RECONCILIATION_PROOFS_MISSING: (
        "derived_reconciliation_semantic_proof_set"
    ),
    CompletionPrerequisiteBlockerCodeV1.OCCURRENCE_IDENTITY_SEMANTIC_AUTHORITY_NOT_AVAILABLE: (
        "occurrence_route_identity_semantic_authority"
    ),
    CompletionPrerequisiteBlockerCodeV1.OPERATIONAL_CUTOFF_SEMANTIC_AUTHORITY_NOT_AVAILABLE: (
        "outer_supervisor_operational_cutoff_semantic_authority"
    ),
    CompletionPrerequisiteBlockerCodeV1.OWNER_COMPLETE_CLOSURES_MISSING: (
        "owner_boundary_complete_closure_set"
    ),
    CompletionPrerequisiteBlockerCodeV1.PROFILE_NATIVE_ZERO_ATTESTATIONS_MISSING: (
        "profile_native_zero_semantic_attestation_set"
    ),
    CompletionPrerequisiteBlockerCodeV1.SHARED_RESOURCE_SEMANTIC_JOIN_NOT_AVAILABLE: (
        "shared_resource_receipt_semantic_join"
    ),
}

_REASON_CODES = {
    CompletionPrerequisiteBlockerCodeV1.DERIVED_RECONCILIATION_PROOFS_MISSING: (
        "NO_REGISTERED_RECONCILIATION_PROOF_SET"
    ),
    CompletionPrerequisiteBlockerCodeV1.OCCURRENCE_IDENTITY_SEMANTIC_AUTHORITY_NOT_AVAILABLE: (
        "NO_INDEPENDENT_OCCURRENCE_ROUTE_IDENTITY_REPLAY"
    ),
    CompletionPrerequisiteBlockerCodeV1.OPERATIONAL_CUTOFF_SEMANTIC_AUTHORITY_NOT_AVAILABLE: (
        "NO_OUTER_SUPERVISOR_CUTOFF_REPLAY"
    ),
    CompletionPrerequisiteBlockerCodeV1.OWNER_COMPLETE_CLOSURES_MISSING: (
        "NO_89_SITE_OWNER_COMPLETE_CLOSURE_SET"
    ),
    CompletionPrerequisiteBlockerCodeV1.PROFILE_NATIVE_ZERO_ATTESTATIONS_MISSING: (
        "NO_114_PATH_NATIVE_ZERO_ATTESTATION_SET"
    ),
    CompletionPrerequisiteBlockerCodeV1.SHARED_RESOURCE_SEMANTIC_JOIN_NOT_AVAILABLE: (
        "NO_NINE_PATH_SHARED_RECEIPT_SEMANTIC_JOIN"
    ),
}


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            "prerequisite manifest used an unknown local domain"
        )
    return content_id(domain, dict(payload))


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            f"{field_name} must be one exact content ID"
        ) from error


def _sorted_unique_strings(values: Any, field_name: str) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or tuple(sorted(values)) != values
        or len(set(values)) != len(values)
        or any(
            type(value) is not str or _IDENTIFIER.fullmatch(value) is None
            for value in values
        )
    ):
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            f"{field_name} must be one sorted unique canonical tuple"
        )
    return values


def _sorted_unique_ids(values: Any, field_name: str) -> tuple[str, ...]:
    result = _sorted_unique_strings(values, field_name)
    for value in result:
        _cid(value, field_name)
    return result


def _ordered_unique_ids(values: Any, field_name: str) -> tuple[str, ...]:
    if type(values) is not tuple or len(set(values)) != len(values):
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            f"{field_name} must be one ordered unique content-ID tuple"
        )
    for value in values:
        _cid(value, field_name)
    return values


@lru_cache(maxsize=1)
def _exact_authorities() -> tuple[Any, ...]:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    projection = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    boundary = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    execution = execution_v1.official_v075_k7_root_cap_execution_identity_profile_v1()
    partition = readiness_v1.official_required_path_partition_v1()
    zero_registry = zero_v1.official_profile_native_zero_rule_registry_v1()
    zero_readiness = zero_v1.current_profile_native_zero_rule_readiness_v1()
    owner_coverage = zero_v1.official_owner_boundary_coverage_profile_v1()

    try:
        registry.validate_official_catalogue()
        stage.validate(registry)
        boundary.validate_official()
    except Exception as error:
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            "one exact prerequisite authority rejected replay"
        ) from error

    zero_paths = tuple(rule.path for rule in zero_registry.rules)
    owner_paths = tuple(sorted({site.path for site in owner_coverage.sites}))
    zero_obligation_keys = tuple(
        requirement.obligation_key
        for rule in zero_registry.rules
        for requirement in rule.evidence_requirements
    )
    owner_obligation_keys = tuple(
        key
        for site in owner_coverage.sites
        for key in site.required_evidence_keys
    )
    if (
        len(registry.required_paths) != EXPECTED_REQUIRED_PATH_COUNT
        or boundary.counter_registry_id != registry.registry_id
        or boundary.stage_profile_id != stage.stage_profile_id
        or boundary.comparison_profile_id != comparison.comparison_profile_id
        or boundary.actual_projection_profile_id
        != projection.actual_projection_profile_id
        or execution.boundary_manifest_id != boundary.manifest_id
        or partition.counter_registry_id != registry.registry_id
        or partition.stage_profile_id != stage.stage_profile_id
        or partition.comparison_profile_id != comparison.comparison_profile_id
        or partition.actual_projection_profile_id
        != projection.actual_projection_profile_id
        or partition.boundary_manifest_id != boundary.manifest_id
        or partition.execution_profile_id != execution.profile_id
        or zero_registry.counter_registry_id != registry.registry_id
        or zero_registry.stage_profile_id != stage.stage_profile_id
        or zero_registry.comparison_profile_id != comparison.comparison_profile_id
        or zero_registry.actual_projection_profile_id
        != projection.actual_projection_profile_id
        or zero_registry.boundary_manifest_id != boundary.manifest_id
        or zero_registry.execution_profile_id != execution.profile_id
        or zero_readiness.rule_registry_id != zero_registry.registry_id
        or owner_coverage.counter_registry_id != registry.registry_id
        or owner_coverage.stage_profile_id != stage.stage_profile_id
        or owner_coverage.boundary_manifest_id != boundary.manifest_id
        or owner_coverage.execution_profile_id != execution.profile_id
        or partition.profile_static_zero_paths != zero_paths
        or partition.emittable_owner_paths != owner_paths
        or tuple(map(
            len,
            (
                partition.shared_resource_paths,
                partition.derived_reconciliation_paths,
                zero_paths,
                owner_paths,
                owner_coverage.sites,
            ),
        ))
        != (
            EXPECTED_SHARED_RESOURCE_PATH_COUNT,
            EXPECTED_DERIVED_RECONCILIATION_PATH_COUNT,
            EXPECTED_PROFILE_NATIVE_ZERO_PATH_COUNT,
            EXPECTED_OWNER_PATH_COUNT,
            EXPECTED_OWNER_SITE_COUNT,
        )
        or any(
            row.status
            is not zero_v1.ProfileNativeZeroRuleReadinessStatusV1
            .BLOCKED_MISSING_PREREQUISITES
            for row in zero_readiness.rows
        )
        or zero_readiness.to_document()["live_ready_path_count"] != 0
        or owner_coverage.to_document()["live_owner_boundaries_closed"] is not False
        or len(zero_obligation_keys)
        != EXPECTED_PROFILE_NATIVE_ZERO_OBLIGATION_COUNT
        or len(set(zero_obligation_keys)) != len(zero_obligation_keys)
        or len(owner_obligation_keys)
        != EXPECTED_OWNER_EVIDENCE_OBLIGATION_COUNT
        or len(set(owner_obligation_keys)) != len(owner_obligation_keys)
    ):
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            "prerequisite authority chain or exact 9+8+114+71/89 disposition changed"
        )
    return (
        registry,
        stage,
        comparison,
        projection,
        boundary,
        execution,
        partition,
        zero_registry,
        zero_readiness,
        owner_coverage,
    )


@dataclass(frozen=True, slots=True)
class MissingCompletionPrerequisiteRefV1:
    """A typed absent semantic authority; never a zero or evidence artifact."""

    _issuer: InitVar[object]
    context_id: str
    evidence_closure_id: str
    code: CompletionPrerequisiteBlockerCodeV1
    required_artifact_role: str
    affected_paths: tuple[str, ...]
    missing_subject_keys: tuple[str, ...]
    missing_subject_ids: tuple[str, ...]
    reason_code: str
    reference_state: str = "NOT_AVAILABLE"

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BLOCKER_ISSUER:
            raise ConstructionAccountingCompletionPrerequisiteV1Error(
                "completion prerequisite blocker is caller-minted"
            )
        _cid(self.context_id, "blocker context")
        _cid(self.evidence_closure_id, "blocker evidence closure")
        try:
            code = CompletionPrerequisiteBlockerCodeV1(self.code)
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingCompletionPrerequisiteV1Error(
                "unknown completion prerequisite blocker"
            ) from error
        object.__setattr__(self, "code", code)
        _sorted_unique_strings(self.affected_paths, "blocker affected paths")
        _sorted_unique_strings(
            self.missing_subject_keys, "blocker missing subject keys"
        )
        _sorted_unique_ids(self.missing_subject_ids, "blocker missing subject IDs")
        if (
            _IDENTIFIER.fullmatch(self.required_artifact_role) is None
            or _IDENTIFIER.fullmatch(self.reason_code) is None
            or self.required_artifact_role != _REQUIRED_ROLES[code]
            or self.reason_code != _REASON_CODES[code]
            or self.reference_state != "NOT_AVAILABLE"
            or not self.missing_subject_keys
        ):
            raise ConstructionAccountingCompletionPrerequisiteV1Error(
                "completion prerequisite blocker is noncanonical"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_completion_prerequisite_blocker.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "evidence_closure_id": self.evidence_closure_id,
            "code": self.code.value,
            "required_artifact_role": self.required_artifact_role,
            "affected_paths": list(self.affected_paths),
            "missing_subject_keys": list(self.missing_subject_keys),
            "missing_subject_ids": list(self.missing_subject_ids),
            "reason_code": self.reason_code,
            "reference_state": self.reference_state,
            "evidence_artifact_id": {
                "kind": "NOT_AVAILABLE",
                "reason": self.reason_code,
            },
            "absence_is_zero_evidence": False,
            "semantic_authority_present": False,
            "formal_accounting_authority": False,
        }

    @property
    def blocker_id(self) -> str:
        return _content_id(
            COMPLETION_PREREQUISITE_BLOCKER_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "completion_prerequisite_blocker_id": self.blocker_id}


def _blocker(
    *,
    context_id: str,
    closure_id: str,
    code: CompletionPrerequisiteBlockerCodeV1,
    affected_paths: tuple[str, ...],
    subject_keys: tuple[str, ...],
    subject_ids: tuple[str, ...] = (),
) -> MissingCompletionPrerequisiteRefV1:
    return MissingCompletionPrerequisiteRefV1(
        _BLOCKER_ISSUER,
        context_id,
        closure_id,
        code,
        _REQUIRED_ROLES[code],
        tuple(sorted(affected_paths)),
        tuple(sorted(subject_keys)),
        tuple(sorted(subject_ids)),
        _REASON_CODES[code],
    )


@lru_cache(maxsize=32)
def _expected_blockers(
    *,
    context_id: str,
    closure_id: str,
) -> tuple[MissingCompletionPrerequisiteRefV1, ...]:
    (
        registry,
        _stage,
        _comparison,
        _projection,
        _boundary,
        _execution,
        partition,
        zero_registry,
        _zero_readiness,
        owner_coverage,
    ) = _exact_authorities()
    all_paths = registry.required_paths
    result = (
        _blocker(
            context_id=context_id,
            closure_id=closure_id,
            code=(
                CompletionPrerequisiteBlockerCodeV1
                .SHARED_RESOURCE_SEMANTIC_JOIN_NOT_AVAILABLE
            ),
            affected_paths=partition.shared_resource_paths,
            subject_keys=partition.shared_resource_paths,
        ),
        _blocker(
            context_id=context_id,
            closure_id=closure_id,
            code=(
                CompletionPrerequisiteBlockerCodeV1
                .OCCURRENCE_IDENTITY_SEMANTIC_AUTHORITY_NOT_AVAILABLE
            ),
            affected_paths=all_paths,
            subject_keys=(
                "decision_point_identity",
                "occurrence_identity",
                "route_attempt_identity",
            ),
        ),
        _blocker(
            context_id=context_id,
            closure_id=closure_id,
            code=(
                CompletionPrerequisiteBlockerCodeV1
                .OPERATIONAL_CUTOFF_SEMANTIC_AUTHORITY_NOT_AVAILABLE
            ),
            affected_paths=all_paths,
            subject_keys=("operational_cutoff", "outer_supervisor_replay"),
        ),
        _blocker(
            context_id=context_id,
            closure_id=closure_id,
            code=(
                CompletionPrerequisiteBlockerCodeV1
                .OWNER_COMPLETE_CLOSURES_MISSING
            ),
            affected_paths=partition.emittable_owner_paths,
            subject_keys=tuple(
                sorted(
                    key
                    for site in owner_coverage.sites
                    for key in site.required_evidence_keys
                )
            ),
            subject_ids=tuple(site.coverage_site_id for site in owner_coverage.sites),
        ),
        _blocker(
            context_id=context_id,
            closure_id=closure_id,
            code=(
                CompletionPrerequisiteBlockerCodeV1
                .PROFILE_NATIVE_ZERO_ATTESTATIONS_MISSING
            ),
            affected_paths=partition.profile_static_zero_paths,
            subject_keys=tuple(
                sorted(
                    requirement.obligation_key
                    for rule in zero_registry.rules
                    for requirement in rule.evidence_requirements
                )
            ),
            subject_ids=tuple(rule.rule_id for rule in zero_registry.rules),
        ),
        _blocker(
            context_id=context_id,
            closure_id=closure_id,
            code=(
                CompletionPrerequisiteBlockerCodeV1
                .DERIVED_RECONCILIATION_PROOFS_MISSING
            ),
            affected_paths=partition.derived_reconciliation_paths,
            subject_keys=partition.derived_reconciliation_paths,
        ),
    )
    return tuple(sorted(result, key=lambda item: item.code.value))


@dataclass(frozen=True, slots=True)
class ConstructionAccountingCompletionPrerequisiteManifestV1:
    """Exact prerequisite identity graph, fixed in the current NOT_READY state."""

    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundary_manifest_id: str
    execution_profile_id: str
    required_path_partition_id: str
    profile_native_zero_rule_registry_id: str
    profile_native_zero_rule_readiness_id: str
    profile_native_zero_rule_ids: tuple[str, ...]
    profile_native_zero_readiness_row_ids: tuple[str, ...]
    owner_boundary_coverage_profile_id: str
    owner_boundary_coverage_site_ids: tuple[str, ...]
    evidence_closure_context_id: str
    evidence_closure_id: str
    evidence_closure_coverage_replay_id: str
    same_process_completion_readiness_id: str
    transcript_id: str
    terminal_id: str
    unresolved_paths: tuple[str, ...]
    blockers: tuple[MissingCompletionPrerequisiteRefV1, ...] = field(repr=False)
    status: CompletionPrerequisiteStatusV1 = (
        CompletionPrerequisiteStatusV1.NOT_READY_MISSING_SEMANTIC_AUTHORITIES
    )

    def __post_init__(self, _issuer: object) -> None:
        for name in (
            "counter_registry_id",
            "stage_profile_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "boundary_manifest_id",
            "execution_profile_id",
            "required_path_partition_id",
            "profile_native_zero_rule_registry_id",
            "profile_native_zero_rule_readiness_id",
            "owner_boundary_coverage_profile_id",
            "evidence_closure_context_id",
            "evidence_closure_id",
            "evidence_closure_coverage_replay_id",
            "same_process_completion_readiness_id",
            "transcript_id",
            "terminal_id",
        ):
            _cid(getattr(self, name), name)
        _ordered_unique_ids(
            self.profile_native_zero_rule_ids,
            "manifest native-zero rule IDs",
        )
        _ordered_unique_ids(
            self.profile_native_zero_readiness_row_ids,
            "manifest native-zero readiness-row IDs",
        )
        _ordered_unique_ids(
            self.owner_boundary_coverage_site_ids,
            "manifest owner-boundary site IDs",
        )
        _sorted_unique_strings(self.unresolved_paths, "manifest unresolved paths")
        try:
            status = CompletionPrerequisiteStatusV1(self.status)
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingCompletionPrerequisiteV1Error(
                "unknown completion prerequisite status"
            ) from error
        object.__setattr__(self, "status", status)
        (
            registry,
            stage,
            comparison,
            projection,
            boundary,
            execution,
            partition,
            zero_registry,
            zero_readiness,
            owner_coverage,
        ) = _exact_authorities()
        expected_blockers = _expected_blockers(
            context_id=self.evidence_closure_context_id,
            closure_id=self.evidence_closure_id,
        )
        if (
            _issuer is not _MANIFEST_ISSUER
            or status
            is not CompletionPrerequisiteStatusV1
            .NOT_READY_MISSING_SEMANTIC_AUTHORITIES
            or self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage.stage_profile_id
            or self.comparison_profile_id != comparison.comparison_profile_id
            or self.actual_projection_profile_id
            != projection.actual_projection_profile_id
            or self.boundary_manifest_id != boundary.manifest_id
            or self.execution_profile_id != execution.profile_id
            or self.required_path_partition_id != partition.partition_id
            or self.profile_native_zero_rule_registry_id != zero_registry.registry_id
            or self.profile_native_zero_rule_readiness_id != zero_readiness.readiness_id
            or self.profile_native_zero_rule_ids
            != tuple(rule.rule_id for rule in zero_registry.rules)
            or self.profile_native_zero_readiness_row_ids
            != tuple(row.readiness_row_id for row in zero_readiness.rows)
            or self.owner_boundary_coverage_profile_id
            != owner_coverage.coverage_profile_id
            or self.owner_boundary_coverage_site_ids
            != tuple(site.coverage_site_id for site in owner_coverage.sites)
            or self.unresolved_paths != registry.required_paths
            or type(self.blockers) is not tuple
            or self.blockers != expected_blockers
            or len(self.blockers) != EXPECTED_BLOCKER_COUNT
            or len({item.blocker_id for item in self.blockers})
            != EXPECTED_BLOCKER_COUNT
        ):
            raise ConstructionAccountingCompletionPrerequisiteV1Error(
                "completion prerequisite manifest differs from the exact current missing graph"
            )

    @property
    def blocker_by_code(
        self,
    ) -> dict[CompletionPrerequisiteBlockerCodeV1, MissingCompletionPrerequisiteRefV1]:
        return {item.code: item for item in self.blockers}

    def _payload(self) -> dict[str, Any]:
        blockers = self.blocker_by_code
        owner = blockers[
            CompletionPrerequisiteBlockerCodeV1.OWNER_COMPLETE_CLOSURES_MISSING
        ]
        zeros = blockers[
            CompletionPrerequisiteBlockerCodeV1
            .PROFILE_NATIVE_ZERO_ATTESTATIONS_MISSING
        ]
        derived = blockers[
            CompletionPrerequisiteBlockerCodeV1
            .DERIVED_RECONCILIATION_PROOFS_MISSING
        ]
        shared = blockers[
            CompletionPrerequisiteBlockerCodeV1
            .SHARED_RESOURCE_SEMANTIC_JOIN_NOT_AVAILABLE
        ]
        return {
            "schema": "acfqp.construction_accounting_completion_prerequisite_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "execution_profile_id": self.execution_profile_id,
            "required_path_partition_id": self.required_path_partition_id,
            "profile_native_zero_rule_registry_id": (
                self.profile_native_zero_rule_registry_id
            ),
            "profile_native_zero_rule_readiness_id": (
                self.profile_native_zero_rule_readiness_id
            ),
            "profile_native_zero_rule_ids": [
                *self.profile_native_zero_rule_ids
            ],
            "profile_native_zero_readiness_row_ids": [
                *self.profile_native_zero_readiness_row_ids
            ],
            "owner_boundary_coverage_profile_id": (
                self.owner_boundary_coverage_profile_id
            ),
            "owner_boundary_coverage_site_ids": [
                *self.owner_boundary_coverage_site_ids
            ],
            "evidence_closure_context_id": self.evidence_closure_context_id,
            "evidence_closure_id": self.evidence_closure_id,
            "evidence_closure_coverage_replay_id": (
                self.evidence_closure_coverage_replay_id
            ),
            "same_process_completion_readiness_id": (
                self.same_process_completion_readiness_id
            ),
            "transcript_id": self.transcript_id,
            "terminal_id": self.terminal_id,
            "status": self.status.value,
            "required_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "unresolved_path_count": len(self.unresolved_paths),
            "unresolved_paths": list(self.unresolved_paths),
            "blocker_ids": [item.blocker_id for item in self.blockers],
            "blocker_codes": [item.code.value for item in self.blockers],
            "missing_shared_resource_paths": list(shared.affected_paths),
            "missing_owner_complete_closure_paths": list(owner.affected_paths),
            "missing_owner_complete_closure_site_ids": list(
                owner.missing_subject_ids
            ),
            "missing_owner_boundary_evidence_keys": list(
                owner.missing_subject_keys
            ),
            "missing_profile_native_zero_paths": list(zeros.affected_paths),
            "missing_profile_native_zero_rule_ids": list(
                zeros.missing_subject_ids
            ),
            "missing_profile_native_zero_obligation_keys": list(
                zeros.missing_subject_keys
            ),
            "missing_derived_reconciliation_paths": list(
                derived.affected_paths
            ),
            "semantic_missing_required_paths": list(self.unresolved_paths),
            "shared_resource_semantic_join_present": False,
            "occurrence_identity_semantic_authority_present": False,
            "operational_cutoff_semantic_authority_present": False,
            "owner_complete_closure_count": 0,
            "profile_native_zero_attestation_count": 0,
            "derived_reconciliation_proof_count": 0,
            "absence_is_zero_evidence": False,
            "structural_identity_binding_only": True,
            "semantic_source_evidence_verified": False,
            "semantic_prerequisites_complete": False,
            "formal_accounting_authority": False,
            "counter_records_allowed": False,
            "counter_records_issued": False,
            "work_vector_allowed": False,
            "work_vector_issued": False,
            "comparison_vector_allowed": False,
            "comparison_vector_issued": False,
            "actual_projection_allowed": False,
            "formal_vector_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id(
            COMPLETION_PREREQUISITE_MANIFEST_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "completion_prerequisite_manifest_id": self.manifest_id,
        }


def freeze_current_completion_prerequisite_manifest_v1(
    evidence_closure: closure_v1.EvidenceClosureV1,
) -> ConstructionAccountingCompletionPrerequisiteManifestV1:
    """Freeze the exact all-missing V0-099 prerequisite graph."""

    if type(evidence_closure) is not closure_v1.EvidenceClosureV1:
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            "current prerequisite factory requires one exact EvidenceClosureV1"
        )
    (
        registry,
        stage,
        comparison,
        projection,
        boundary,
        execution,
        partition,
        zero_registry,
        zero_readiness,
        owner_coverage,
    ) = _exact_authorities()
    try:
        coverage = closure_v1.verify_evidence_closure_coverage_v1(
            evidence_closure, registry=registry
        )
        current_readiness = (
            readiness_v1.evaluate_current_same_process_completion_readiness_v1(
                evidence_closure
            )
        )
        readiness_v1.verify_current_same_process_completion_readiness_v1(
            current_readiness, closure=evidence_closure
        )
    except Exception as error:
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            "current evidence closure failed exact structural/readiness replay"
        ) from error
    if (
        coverage.coverage_state
        is not closure_v1.EvidenceClosureCoverageStateV1.INCOMPLETE
        or coverage.unresolved_paths != registry.required_paths
        or coverage.resolved_path_count != 0
    ):
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            "V0-099 current factory requires the exact all-UNRESOLVED 202-path closure"
        )
    context = evidence_closure.context
    return ConstructionAccountingCompletionPrerequisiteManifestV1(
        _MANIFEST_ISSUER,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        projection.actual_projection_profile_id,
        boundary.manifest_id,
        execution.profile_id,
        partition.partition_id,
        zero_registry.registry_id,
        zero_readiness.readiness_id,
        tuple(rule.rule_id for rule in zero_registry.rules),
        tuple(row.readiness_row_id for row in zero_readiness.rows),
        owner_coverage.coverage_profile_id,
        tuple(site.coverage_site_id for site in owner_coverage.sites),
        context.context_id,
        evidence_closure.closure_id,
        coverage.verification_id,
        current_readiness.readiness_id,
        context.transcript_id,
        context.terminal_id,
        coverage.unresolved_paths,
        _expected_blockers(
            context_id=context.context_id,
            closure_id=evidence_closure.closure_id,
        ),
    )


@dataclass(frozen=True, slots=True)
class ConstructionAccountingCompletionPrerequisiteReplayV1:
    """Factory-issued deterministic replay of the negative manifest."""

    _issuer: InitVar[object]
    manifest_id: str
    evidence_closure_context_id: str
    evidence_closure_id: str
    status: CompletionPrerequisiteStatusV1
    blocker_ids: tuple[str, ...]
    missing_shared_resource_path_count: int
    missing_owner_site_count: int
    missing_native_zero_attestation_count: int
    missing_reconciliation_proof_count: int

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPLAY_ISSUER:
            raise ConstructionAccountingCompletionPrerequisiteV1Error(
                "completion prerequisite replay is caller-minted"
            )
        for name in (
            "manifest_id",
            "evidence_closure_context_id",
            "evidence_closure_id",
        ):
            _cid(getattr(self, name), name)
        _sorted_unique_ids(self.blocker_ids, "replay blocker IDs")
        try:
            status = CompletionPrerequisiteStatusV1(self.status)
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingCompletionPrerequisiteV1Error(
                "unknown prerequisite replay status"
            ) from error
        object.__setattr__(self, "status", status)
        if (
            status
            is not CompletionPrerequisiteStatusV1
            .NOT_READY_MISSING_SEMANTIC_AUTHORITIES
            or len(self.blocker_ids) != EXPECTED_BLOCKER_COUNT
            or self.missing_shared_resource_path_count
            != EXPECTED_SHARED_RESOURCE_PATH_COUNT
            or self.missing_owner_site_count != EXPECTED_OWNER_SITE_COUNT
            or self.missing_native_zero_attestation_count
            != EXPECTED_PROFILE_NATIVE_ZERO_PATH_COUNT
            or self.missing_reconciliation_proof_count
            != EXPECTED_DERIVED_RECONCILIATION_PATH_COUNT
        ):
            raise ConstructionAccountingCompletionPrerequisiteV1Error(
                "completion prerequisite replay summary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_completion_prerequisite_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "completion_prerequisite_manifest_id": self.manifest_id,
            "evidence_closure_context_id": self.evidence_closure_context_id,
            "evidence_closure_id": self.evidence_closure_id,
            "status": self.status.value,
            "blocker_ids": list(self.blocker_ids),
            "missing_shared_resource_path_count": (
                self.missing_shared_resource_path_count
            ),
            "missing_owner_site_count": self.missing_owner_site_count,
            "missing_native_zero_attestation_count": (
                self.missing_native_zero_attestation_count
            ),
            "missing_reconciliation_proof_count": (
                self.missing_reconciliation_proof_count
            ),
            "exact_missing_sets_replayed": True,
            "structural_identity_binding_only": True,
            "semantic_source_evidence_verified": False,
            "semantic_prerequisites_complete": False,
            "formal_accounting_authority": False,
            "formal_vector_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def replay_id(self) -> str:
        return _content_id(
            COMPLETION_PREREQUISITE_REPLAY_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "completion_prerequisite_replay_id": self.replay_id,
        }


def verify_current_completion_prerequisite_manifest_v1(
    manifest: ConstructionAccountingCompletionPrerequisiteManifestV1,
    *,
    evidence_closure: closure_v1.EvidenceClosureV1,
) -> ConstructionAccountingCompletionPrerequisiteReplayV1:
    """Deterministically rebuild the manifest and replay its exact omissions."""

    if type(manifest) is not ConstructionAccountingCompletionPrerequisiteManifestV1:
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            "prerequisite replay requires one exact manifest"
        )
    expected = freeze_current_completion_prerequisite_manifest_v1(evidence_closure)
    if manifest != expected or manifest.manifest_id != expected.manifest_id:
        raise ConstructionAccountingCompletionPrerequisiteV1Error(
            "prerequisite manifest differs from deterministic replay"
        )
    blockers = manifest.blocker_by_code
    return ConstructionAccountingCompletionPrerequisiteReplayV1(
        _REPLAY_ISSUER,
        manifest.manifest_id,
        manifest.evidence_closure_context_id,
        manifest.evidence_closure_id,
        manifest.status,
        tuple(sorted(item.blocker_id for item in manifest.blockers)),
        len(
            blockers[
                CompletionPrerequisiteBlockerCodeV1
                .SHARED_RESOURCE_SEMANTIC_JOIN_NOT_AVAILABLE
            ].affected_paths
        ),
        len(
            blockers[
                CompletionPrerequisiteBlockerCodeV1
                .OWNER_COMPLETE_CLOSURES_MISSING
            ].missing_subject_ids
        ),
        len(
            blockers[
                CompletionPrerequisiteBlockerCodeV1
                .PROFILE_NATIVE_ZERO_ATTESTATIONS_MISSING
            ].missing_subject_ids
        ),
        len(
            blockers[
                CompletionPrerequisiteBlockerCodeV1
                .DERIVED_RECONCILIATION_PROOFS_MISSING
            ].affected_paths
        ),
    )


__all__ = [
    "COMPLETION_PREREQUISITE_BLOCKER_V1_DOMAIN",
    "COMPLETION_PREREQUISITE_MANIFEST_V1_DOMAIN",
    "COMPLETION_PREREQUISITE_REPLAY_V1_DOMAIN",
    "CompletionPrerequisiteBlockerCodeV1",
    "CompletionPrerequisiteStatusV1",
    "ConstructionAccountingCompletionPrerequisiteManifestV1",
    "ConstructionAccountingCompletionPrerequisiteReplayV1",
    "ConstructionAccountingCompletionPrerequisiteV1Error",
    "EXPECTED_BLOCKER_COUNT",
    "EXPECTED_DERIVED_RECONCILIATION_PATH_COUNT",
    "EXPECTED_OWNER_PATH_COUNT",
    "EXPECTED_OWNER_SITE_COUNT",
    "EXPECTED_OWNER_EVIDENCE_OBLIGATION_COUNT",
    "EXPECTED_PROFILE_NATIVE_ZERO_OBLIGATION_COUNT",
    "EXPECTED_PROFILE_NATIVE_ZERO_PATH_COUNT",
    "EXPECTED_REQUIRED_PATH_COUNT",
    "EXPECTED_SHARED_RESOURCE_PATH_COUNT",
    "LOCAL_DOMAIN_TAGS",
    "MissingCompletionPrerequisiteRefV1",
    "PROFILE_KEY",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "freeze_current_completion_prerequisite_manifest_v1",
    "verify_current_completion_prerequisite_manifest_v1",
]
