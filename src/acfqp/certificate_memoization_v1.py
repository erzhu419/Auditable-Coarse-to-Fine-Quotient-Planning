"""V0-050 exact identity-bound fixed-plan certificate memoization.

V0-049 deliberately repeated complete fixed-plan audits for ten preregistered
held-out occurrences.  This module keeps the same planner, plan candidates,
selected plans, model, thresholds, and final certificates, but inserts a
role-separated, append-only, process-local memo in front of the exact auditor.

Only byte-identical proof requests may hit.  Logical occurrence identity is
excluded from the semantic key so a repeated occurrence can reuse a proof,
but every use receipt binds the current occurrence and the original miss.
Candidate-ranking audits and independent selected-plan certificates occupy
different key roles even when their inner proof payloads are byte-identical.

This is proof-computation deduplication.  It is not cross-identity incremental
proof, a sample-efficiency result, a persistent cache, or workload economics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import product
from pathlib import Path
from typing import Any, Mapping

import acfqp.heldout_family_amortization_v1 as family_module
import acfqp.partial_sound_audit_v1 as partial_audit_module
from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.cross_query_promotion_v1 import (
    HeldOutPlanAuditV1,
    HeldOutPlanProposalV1,
    HeldOutThresholdBindingV1,
)
from acfqp.heldout_family_amortization_v1 import (
    FamilyHeldOutQuerySpecV1,
    FamilyLogicalOccurrenceV1,
    HeldOutFamilyAmortizationResultV1,
    HeldOutFamilyProtocolV1,
    HeldOutFamilyPromotionBuildV1,
    MatchedHeldOutOccurrenceV1,
    _query_for_occurrence,
    verify_lmb_heldout_family_amortization_v1,
)
from acfqp.domains.matching_buffer import LMBKernel
from acfqp.multistep_query_refinement_v1 import (
    MultiStepQueryRefinementResultV1,
)
from acfqp.observation_partial_rapm_v1 import (
    DeterministicObservationProfileV1,
    ObservationLogManifestV1,
    PreregisteredObservationAuthorityV1,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    ObservedTypedPartialRAPMResultV1,
)
from acfqp.partial_model_planner_v1 import (
    PartialModelPlannerSelectionMode,
    TypedPartialModelPlanProposalResultV2,
    _candidate_summary,
    _planner_context,
    _selected_summary,
    _stage_assignments,
)
from acfqp.partial_sound_audit_v1 import (
    ContingentPlanStageV1,
    FrozenContingentAbstractPlanV1,
    FrozenPartialAuditThresholdsV1,
    InitialStateMassV1,
    PartialAuditOutcome,
    PartialSoundAuditResultV1,
    TypedPartialSoundAuditResultV2,
    _audit_verified_partial_model_v1,
    canonical_lmb_n6_return_bound_proof_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.13.0"
PROFILE_KEY = "lmb_identity_bound_certificate_memoization_v0"
SUCCESS_STATUS = "CERTIFIED_IDENTITY_BOUND_PROOF_REUSE_CONTROL"

EXPECTED_PARTIAL_AUDIT_SOURCE_SHA256 = (
    "661aee3732afda05c860f5dadae2b3545ecbbed7cee86f27517d1ea5dfcb7934"
)
EXPECTED_FAMILY_PLANNER_SOURCE_SHA256 = (
    "30020f7fd0e060970063a35d1365a52a1a28549119b12217c397f8252f35e84d"
)

DOMAIN_TAGS = {
    "semantics": "acfqp:fixed-plan-audit-memo-semantics:v1",
    "planner_semantics": "acfqp:held-out-family-planner-memo-semantics:v1",
    "key": "acfqp:fixed-plan-audit-memo-key:v1",
    "execution_attestation": "acfqp:full-audit-execution-attestation:v1",
    "entry": "acfqp:fixed-plan-audit-memo-entry:v1",
    "cache_state": "acfqp:fixed-plan-audit-cache-state:v1",
    "receipt": "acfqp:fixed-plan-audit-cache-use-receipt:v1",
    "occurrence_work": "acfqp:memoized-proof-occurrence-work:v1",
    "memo_occurrence": "acfqp:memoized-held-out-occurrence:v1",
    "cache": "acfqp:fixed-plan-audit-memo-cache:v1",
    "aggregate_work": "acfqp:proof-memoization-aggregate-work:v1",
    "prefix": "acfqp:proof-memoization-prefix:v1",
    "execution": "acfqp:memoized-held-out-family-execution:v1",
    "match": "acfqp:matched-proof-memoization-occurrence:v1",
    "telemetry": "acfqp:proof-memoization-telemetry:v1",
    "result": "acfqp:proof-memoization-control-result:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-050 content-ID domains must be unique")


class CertificateMemoizationInvariantViolation(ValueError):
    """The memo key, append-only trace, match, or claim boundary is invalid."""


class FixedPlanAuditRole(str, Enum):
    CANDIDATE_RANKING_AUDIT = "CANDIDATE_RANKING_AUDIT"
    INDEPENDENT_SELECTED_PLAN_CERTIFICATE = (
        "INDEPENDENT_SELECTED_PLAN_CERTIFICATE"
    )


class MemoLookupOutcome(str, Enum):
    MISS_FULL_AUDIT_EXECUTED = "MISS_FULL_AUDIT_EXECUTED"
    HIT_EXACT_IDENTITY = "HIT_EXACT_IDENTITY"


class MemoRouteKind(str, Enum):
    NO_REUSE_CONTROL = "NO_REUSE_CONTROL"
    EXACT_IDENTITY_MEMO = "EXACT_IDENTITY_MEMO"


class AuditExecutionRelation(str, Enum):
    EQUAL = "EQUAL"
    MEMO_FEWER_FULL_AUDITS = "MEMO_FEWER_FULL_AUDITS"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise CertificateMemoizationInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise CertificateMemoizationInvariantViolation(
            f"{field_name} must be a full content ID"
        ) from error


def _integer(value: Any, field_name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CertificateMemoizationInvariantViolation(
            f"{field_name} must be an integer >= {minimum}"
        )
    return value


def _runtime_source_sha256(module: Any) -> str:
    path = Path(module.__file__)
    if path.suffix != ".py" or not path.is_file():
        raise CertificateMemoizationInvariantViolation(
            "memoization semantics require the registered Python source file"
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class FixedPlanAuditMemoSemanticsV1:
    partial_audit_schema_version: str
    partial_audit_profile_key: str
    robust_bellman_formula_id: str
    unrestricted_upper_formula_id: str
    partial_audit_source_sha256: str
    family_planner_source_sha256: str
    arithmetic_kind: str = "EXACT_FRACTIONS_FRACTION"
    cache_match_kind: str = "FULL_CONTENT_IDENTITY_EQUALITY_ONLY"
    candidate_and_selected_roles_separated: bool = True
    cross_identity_reuse_forbidden: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "partial_audit_source_sha256",
            "family_planner_source_sha256",
        ):
            _cid(getattr(self, field_name), f"memo semantics {field_name}")
        if (
            self.partial_audit_schema_version != partial_audit_module.SCHEMA_VERSION
            or self.partial_audit_profile_key != partial_audit_module.PROFILE_KEY
            or self.robust_bellman_formula_id
            != partial_audit_module.ROBUST_BELLMAN_FORMULA_ID
            or self.unrestricted_upper_formula_id
            != partial_audit_module.UNRESTRICTED_UPPER_FORMULA_ID
            or self.partial_audit_source_sha256
            != EXPECTED_PARTIAL_AUDIT_SOURCE_SHA256
            or self.family_planner_source_sha256
            != EXPECTED_FAMILY_PLANNER_SOURCE_SHA256
            or self.arithmetic_kind != "EXACT_FRACTIONS_FRACTION"
            or self.cache_match_kind != "FULL_CONTENT_IDENTITY_EQUALITY_ONLY"
            or self.candidate_and_selected_roles_separated is not True
            or self.cross_identity_reuse_forbidden is not True
        ):
            raise CertificateMemoizationInvariantViolation(
                "fixed-plan memo semantics differ from the registered profile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.fixed_plan_audit_memo_semantics.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field_name: getattr(self, field_name)
                for field_name in self.__dataclass_fields__
            },
        }

    @property
    def semantics_id(self) -> str:
        return _content_id("semantics", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantics_id": self.semantics_id}


def fixed_plan_audit_memo_semantics_v1() -> FixedPlanAuditMemoSemanticsV1:
    partial_digest = _runtime_source_sha256(partial_audit_module)
    family_digest = _runtime_source_sha256(family_module)
    return FixedPlanAuditMemoSemanticsV1(
        partial_audit_module.SCHEMA_VERSION,
        partial_audit_module.PROFILE_KEY,
        partial_audit_module.ROBUST_BELLMAN_FORMULA_ID,
        partial_audit_module.UNRESTRICTED_UPPER_FORMULA_ID,
        partial_digest,
        family_digest,
    )


@dataclass(frozen=True, slots=True)
class FixedPlanAuditMemoKeyV1:
    audit_role: FixedPlanAuditRole
    memo_semantics_id: str
    structural_id: str
    environment_instance_id: str
    base_model_id: str
    source_refinement_result_id: str
    family_protocol_id: str
    family_promotion_result_id: str
    family_eligibility_proof_id: str
    promoted_model_id: str
    observation_log_id: str
    semantics_profile_id: str
    observation_authority_id: str
    target_query_id: str
    threshold_binding_id: str
    thresholds_id: str
    return_bound_proof_id: str
    contingent_plan_id: str
    planner_semantics_id: str
    planner_result_id: str | None

    def __post_init__(self) -> None:
        if type(self.audit_role) is not FixedPlanAuditRole:
            raise CertificateMemoizationInvariantViolation(
                "memo key requires the exact audit-role enum"
            )
        for field_name in (
            "memo_semantics_id",
            "structural_id",
            "environment_instance_id",
            "base_model_id",
            "source_refinement_result_id",
            "family_protocol_id",
            "family_promotion_result_id",
            "family_eligibility_proof_id",
            "promoted_model_id",
            "observation_log_id",
            "semantics_profile_id",
            "observation_authority_id",
            "target_query_id",
            "threshold_binding_id",
            "thresholds_id",
            "return_bound_proof_id",
            "contingent_plan_id",
            "planner_semantics_id",
        ):
            _cid(getattr(self, field_name), f"memo key {field_name}")
        if self.planner_result_id is not None:
            _cid(self.planner_result_id, "memo key planner_result_id")
        if (
            self.audit_role is FixedPlanAuditRole.CANDIDATE_RANKING_AUDIT
            and self.planner_result_id is not None
        ) or (
            self.audit_role
            is FixedPlanAuditRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE
            and self.planner_result_id is None
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo key planner-result binding does not match its proof role"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.fixed_plan_audit_memo_key.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "audit_role": self.audit_role.value,
            **{
                field_name: getattr(self, field_name)
                for field_name in (
                    "memo_semantics_id",
                    "structural_id",
                    "environment_instance_id",
                    "base_model_id",
                    "source_refinement_result_id",
                    "family_protocol_id",
                    "family_promotion_result_id",
                    "family_eligibility_proof_id",
                    "promoted_model_id",
                    "observation_log_id",
                    "semantics_profile_id",
                    "observation_authority_id",
                    "target_query_id",
                    "threshold_binding_id",
                    "thresholds_id",
                    "return_bound_proof_id",
                    "contingent_plan_id",
                    "planner_semantics_id",
                    "planner_result_id",
                )
            },
        }

    @property
    def key_id(self) -> str:
        return _content_id("key", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "key_id": self.key_id}


@dataclass(frozen=True, slots=True)
class FullAuditExecutionAttestationV1:
    memo_key_id: str
    audit_result_id: str
    certificate_id: str | None
    source_occurrence_id: str
    source_resolution_sequence: int
    memo_semantics_id: str
    full_audit_execution_count: int = 1
    exact_kernel_calls: int = 0
    ground_optimizer_calls: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "memo_key_id",
            "audit_result_id",
            "source_occurrence_id",
            "memo_semantics_id",
        ):
            _cid(getattr(self, field_name), f"audit attestation {field_name}")
        if self.certificate_id is not None:
            _cid(self.certificate_id, "audit attestation certificate_id")
        for field_name in (
            "source_resolution_sequence",
            "full_audit_execution_count",
            "exact_kernel_calls",
            "ground_optimizer_calls",
        ):
            _integer(getattr(self, field_name), f"audit attestation {field_name}")
        if (
            self.source_resolution_sequence < 1
            or self.full_audit_execution_count != 1
            or self.exact_kernel_calls != 0
            or self.ground_optimizer_calls != 0
        ):
            raise CertificateMemoizationInvariantViolation(
                "full-audit attestation count or no-ground boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.full_audit_execution_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field_name: getattr(self, field_name)
                for field_name in self.__dataclass_fields__
            },
        }

    @property
    def attestation_id(self) -> str:
        return _content_id("execution_attestation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


@dataclass(frozen=True, slots=True)
class FixedPlanAuditMemoEntryV1:
    memo_key: FixedPlanAuditMemoKeyV1
    audit_result: PartialSoundAuditResultV1
    execution_attestation: FullAuditExecutionAttestationV1
    reusable_only_on_exact_key: bool = True
    append_only: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.memo_key) is not FixedPlanAuditMemoKeyV1
            or type(self.audit_result) is not PartialSoundAuditResultV1
            or type(self.execution_attestation)
            is not FullAuditExecutionAttestationV1
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo entry rejects substituted key, proof, or attestation"
            )
        certificate = self.audit_result.certificate
        expected_certificate_id = (
            certificate.certificate_id if certificate is not None else None
        )
        if (
            self.audit_result.partial_model_id != self.memo_key.promoted_model_id
            or self.audit_result.thresholds_id != self.memo_key.thresholds_id
            or self.audit_result.contingent_plan_id
            != self.memo_key.contingent_plan_id
            or (
                self.memo_key.audit_role
                is FixedPlanAuditRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE
                and (
                    self.audit_result.outcome
                    is not PartialAuditOutcome.CERTIFIED_FIXED_PLAN
                    or certificate is None
                )
            )
            or self.execution_attestation.memo_key_id != self.memo_key.key_id
            or self.execution_attestation.audit_result_id
            != self.audit_result.result_id
            or self.execution_attestation.certificate_id
            != expected_certificate_id
            or self.execution_attestation.memo_semantics_id
            != self.memo_key.memo_semantics_id
            or self.reusable_only_on_exact_key is not True
            or self.append_only is not True
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo entry proof payload or source attestation is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.fixed_plan_audit_memo_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "memo_key": self.memo_key.to_document(),
            "audit_result": self.audit_result.to_document(),
            "execution_attestation": self.execution_attestation.to_document(),
            "reusable_only_on_exact_key": self.reusable_only_on_exact_key,
            "append_only": self.append_only,
        }

    @property
    def entry_id(self) -> str:
        return _content_id("entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


def _cache_state_id(
    entries: Mapping[str, FixedPlanAuditMemoEntryV1],
) -> str:
    payload = {
        "schema": "acfqp.fixed_plan_audit_cache_state.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "entry_bindings": [
            {"memo_key_id": key_id, "entry_id": entries[key_id].entry_id}
            for key_id in sorted(entries)
        ],
    }
    return _content_id("cache_state", payload)


@dataclass(frozen=True, slots=True)
class FixedPlanAuditCacheUseReceiptV1:
    lookup_sequence: int
    occurrence_id: str
    target_query_id: str
    request_ordinal_within_occurrence: int
    proof_role: FixedPlanAuditRole
    memo_key_id: str
    cache_entry_id: str
    audit_result_id: str
    source_miss_occurrence_id: str
    source_miss_sequence: int
    outcome: MemoLookupOutcome
    pre_cache_state_id: str
    post_cache_state_id: str
    full_audit_execution_count: int
    cache_insert_count: int
    entry_identity_validation_count: int = 1

    def __post_init__(self) -> None:
        for field_name in (
            "lookup_sequence",
            "request_ordinal_within_occurrence",
            "source_miss_sequence",
            "full_audit_execution_count",
            "cache_insert_count",
            "entry_identity_validation_count",
        ):
            _integer(getattr(self, field_name), f"cache receipt {field_name}")
        for field_name in (
            "occurrence_id",
            "target_query_id",
            "memo_key_id",
            "cache_entry_id",
            "audit_result_id",
            "source_miss_occurrence_id",
            "pre_cache_state_id",
            "post_cache_state_id",
        ):
            _cid(getattr(self, field_name), f"cache receipt {field_name}")
        if (
            type(self.proof_role) is not FixedPlanAuditRole
            or type(self.outcome) is not MemoLookupOutcome
            or self.lookup_sequence < 1
            or self.request_ordinal_within_occurrence not in (1, 2, 3)
            or self.source_miss_sequence < 1
            or self.entry_identity_validation_count != 1
        ):
            raise CertificateMemoizationInvariantViolation(
                "cache receipt sequence, role, or validation count is invalid"
            )
        expected_counts = {
            MemoLookupOutcome.MISS_FULL_AUDIT_EXECUTED: (1, 1),
            MemoLookupOutcome.HIT_EXACT_IDENTITY: (0, 0),
        }
        if (
            (self.full_audit_execution_count, self.cache_insert_count)
            != expected_counts[self.outcome]
            or (
                self.outcome is MemoLookupOutcome.HIT_EXACT_IDENTITY
                and self.pre_cache_state_id != self.post_cache_state_id
            )
        ):
            raise CertificateMemoizationInvariantViolation(
                "cache receipt hit/miss accounting or state transition changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.fixed_plan_audit_cache_use_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "lookup_sequence": self.lookup_sequence,
            "occurrence_id": self.occurrence_id,
            "target_query_id": self.target_query_id,
            "request_ordinal_within_occurrence": (
                self.request_ordinal_within_occurrence
            ),
            "proof_role": self.proof_role.value,
            "memo_key_id": self.memo_key_id,
            "cache_entry_id": self.cache_entry_id,
            "audit_result_id": self.audit_result_id,
            "source_miss_occurrence_id": self.source_miss_occurrence_id,
            "source_miss_sequence": self.source_miss_sequence,
            "outcome": self.outcome.value,
            "pre_cache_state_id": self.pre_cache_state_id,
            "post_cache_state_id": self.post_cache_state_id,
            "full_audit_execution_count": self.full_audit_execution_count,
            "cache_insert_count": self.cache_insert_count,
            "entry_identity_validation_count": (
                self.entry_identity_validation_count
            ),
        }

    @property
    def receipt_id(self) -> str:
        return _content_id("receipt", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "receipt_id": self.receipt_id}



@dataclass(frozen=True, slots=True)
class MemoizedOccurrenceWorkV1:
    occurrence_id: str
    plan_candidate_count: int
    logical_proof_request_count: int
    candidate_role_request_count: int
    selected_role_request_count: int
    full_audit_execution_count: int
    memo_lookup_count: int
    memo_hit_count: int
    memo_miss_count: int
    cache_insert_count: int
    entry_identity_validation_count: int
    target_transition_calls: int = 0
    target_catalogue_calls: int = 0
    direct_ground_optimizer_calls: int = 0

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "memo occurrence work occurrence_id")
        for field_name in self.__dataclass_fields__:
            if field_name != "occurrence_id":
                _integer(getattr(self, field_name), f"memo work {field_name}")
        if (
            self.plan_candidate_count != 2
            or self.logical_proof_request_count != 3
            or self.candidate_role_request_count != 2
            or self.selected_role_request_count != 1
            or self.memo_lookup_count != 3
            or self.memo_hit_count + self.memo_miss_count != 3
            or self.full_audit_execution_count != self.memo_miss_count
            or self.cache_insert_count != self.memo_miss_count
            or self.entry_identity_validation_count != 3
            or (self.memo_hit_count, self.memo_miss_count) not in {(0, 3), (3, 0)}
            or self.target_transition_calls != 0
            or self.target_catalogue_calls != 0
            or self.direct_ground_optimizer_calls != 0
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo occurrence work does not reconcile three role-bound requests"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.memoized_proof_occurrence_work.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field_name: getattr(self, field_name)
                for field_name in self.__dataclass_fields__
            },
        }

    @property
    def work_id(self) -> str:
        return _content_id("occurrence_work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class MemoizedHeldOutOccurrenceV1:
    occurrence: FamilyLogicalOccurrenceV1
    target_query_id: str
    threshold_binding: HeldOutThresholdBindingV1
    plan_proposal: HeldOutPlanProposalV1
    plan_audit: HeldOutPlanAuditV1
    candidate_resolution_receipt_ids: tuple[str, str]
    selected_resolution_receipt_id: str
    work: MemoizedOccurrenceWorkV1

    def __post_init__(self) -> None:
        if (
            type(self.occurrence) is not FamilyLogicalOccurrenceV1
            or type(self.threshold_binding) is not HeldOutThresholdBindingV1
            or type(self.plan_proposal) is not HeldOutPlanProposalV1
            or type(self.plan_audit) is not HeldOutPlanAuditV1
            or type(self.work) is not MemoizedOccurrenceWorkV1
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo occurrence rejects substituted planning artifacts"
            )
        _cid(self.target_query_id, "memo occurrence target_query_id")
        if (
            type(self.candidate_resolution_receipt_ids) is not tuple
            or len(self.candidate_resolution_receipt_ids) != 2
            or len(set(self.candidate_resolution_receipt_ids)) != 2
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo occurrence requires two distinct candidate receipts"
            )
        for receipt_id in self.candidate_resolution_receipt_ids:
            _cid(receipt_id, "memo occurrence candidate receipt")
        _cid(
            self.selected_resolution_receipt_id,
            "memo occurrence selected receipt",
        )
        if (
            self.occurrence.query_id != self.target_query_id
            or self.threshold_binding.target_query_id != self.target_query_id
            or self.plan_proposal.target_query_id != self.target_query_id
            or self.plan_audit.target_query_id != self.target_query_id
            or self.plan_proposal.threshold_binding_id
            != self.threshold_binding.binding_id
            or self.plan_audit.threshold_binding_id
            != self.threshold_binding.binding_id
            or self.plan_proposal.thresholds_id
            != self.threshold_binding.thresholds.thresholds_id
            or self.plan_audit.audit_result.thresholds_id
            != self.threshold_binding.thresholds.thresholds_id
            or self.plan_audit.planner_result_id != self.plan_proposal.result_id
            or self.plan_audit.selected_plan_id
            != self.plan_proposal.selected_plan.plan_id
            or self.work.occurrence_id != self.occurrence.occurrence_id
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo occurrence model/query/threshold/plan binding changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.memoized_held_out_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence": self.occurrence.to_document(),
            "target_query_id": self.target_query_id,
            "threshold_binding": self.threshold_binding.to_document(),
            "plan_proposal": self.plan_proposal.to_document(),
            "plan_audit": self.plan_audit.to_document(),
            "candidate_resolution_receipt_ids": list(
                self.candidate_resolution_receipt_ids
            ),
            "selected_resolution_receipt_id": (
                self.selected_resolution_receipt_id
            ),
            "work": self.work.to_document(),
        }

    @property
    def result_id(self) -> str:
        return _content_id("memo_occurrence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class FixedPlanAuditMemoCacheV1:
    entries: tuple[FixedPlanAuditMemoEntryV1, ...]
    initial_cache_empty: bool = True
    append_only: bool = True
    persistent_cross_process_cache_claimed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.entries) is not tuple
            or len(self.entries) != 9
            or any(type(item) is not FixedPlanAuditMemoEntryV1 for item in self.entries)
            or tuple(item.memo_key.key_id for item in self.entries)
            != tuple(sorted(set(item.memo_key.key_id for item in self.entries)))
            or len({item.entry_id for item in self.entries}) != 9
            or self.initial_cache_empty is not True
            or self.append_only is not True
            or self.persistent_cross_process_cache_claimed is not False
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo cache is not the frozen nine-entry append-only store"
            )

    @property
    def cache_state_id(self) -> str:
        return _cache_state_id(
            {item.memo_key.key_id: item for item in self.entries}
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.fixed_plan_audit_memo_cache.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "entries": [item.to_document() for item in self.entries],
            "cache_state_id": self.cache_state_id,
            "initial_cache_empty": self.initial_cache_empty,
            "append_only": self.append_only,
            "persistent_cross_process_cache_claimed": (
                self.persistent_cross_process_cache_claimed
            ),
        }

    @property
    def cache_id(self) -> str:
        return _content_id("cache", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cache_id": self.cache_id}


@dataclass(frozen=True, slots=True)
class ProofMemoizationAggregateWorkV1:
    route_kind: MemoRouteKind
    logical_occurrence_count: int
    plan_candidate_count: int
    logical_proof_request_count: int
    candidate_role_request_count: int
    selected_role_request_count: int
    full_audit_execution_count: int
    memo_key_construction_count: int
    memo_lookup_count: int
    memo_hit_count: int
    memo_miss_count: int
    cache_insert_count: int
    entry_identity_validation_count: int
    target_transition_calls: int
    target_catalogue_calls: int
    direct_ground_optimizer_calls: int
    complete_phase3e_counter_vector_claimed: bool = False

    def __post_init__(self) -> None:
        if type(self.route_kind) is not MemoRouteKind:
            raise CertificateMemoizationInvariantViolation(
                "aggregate work requires the exact route enum"
            )
        for field_name in self.__dataclass_fields__:
            if field_name not in {
                "route_kind",
                "complete_phase3e_counter_vector_claimed",
            }:
                _integer(getattr(self, field_name), f"aggregate work {field_name}")
        common = (
            self.logical_occurrence_count,
            self.plan_candidate_count,
            self.logical_proof_request_count,
            self.candidate_role_request_count,
            self.selected_role_request_count,
            self.target_transition_calls,
            self.target_catalogue_calls,
            self.direct_ground_optimizer_calls,
        )
        if common != (10, 20, 30, 20, 10, 0, 0, 0):
            raise CertificateMemoizationInvariantViolation(
                "aggregate work changed the matched workload or no-ground boundary"
            )
        route_expected = {
            MemoRouteKind.NO_REUSE_CONTROL: (30, 0, 0, 0, 0, 0, 0),
            MemoRouteKind.EXACT_IDENTITY_MEMO: (9, 30, 30, 21, 9, 9, 30),
        }
        actual = (
            self.full_audit_execution_count,
            self.memo_key_construction_count,
            self.memo_lookup_count,
            self.memo_hit_count,
            self.memo_miss_count,
            self.cache_insert_count,
            self.entry_identity_validation_count,
        )
        if (
            actual != route_expected[self.route_kind]
            or self.complete_phase3e_counter_vector_claimed is not False
        ):
            raise CertificateMemoizationInvariantViolation(
                "aggregate work does not match its frozen no-reuse/memo route"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.proof_memoization_aggregate_work.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_kind": self.route_kind.value,
            **{
                field_name: getattr(self, field_name)
                for field_name in self.__dataclass_fields__
                if field_name != "route_kind"
            },
        }

    @property
    def work_id(self) -> str:
        return _content_id("aggregate_work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class ProofMemoizationPrefixV1:
    prefix_length: int
    occurrence_ids: tuple[str, ...]
    no_reuse_full_audit_executions: int
    memo_full_audit_executions: int
    memo_hits: int
    memo_entries: int
    plan_candidates_each_arm: int
    relation: AuditExecutionRelation
    official_scalar_cost: None = None
    official_N_break_even: None = None
    scalar_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        _integer(self.prefix_length, "memo prefix length", 1)
        for field_name in (
            "no_reuse_full_audit_executions",
            "memo_full_audit_executions",
            "memo_hits",
            "memo_entries",
            "plan_candidates_each_arm",
        ):
            _integer(getattr(self, field_name), f"memo prefix {field_name}")
        if (
            type(self.occurrence_ids) is not tuple
            or len(self.occurrence_ids) != self.prefix_length
            or len(set(self.occurrence_ids)) != self.prefix_length
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo prefix occurrence IDs are incomplete or duplicate"
            )
        for occurrence_id in self.occurrence_ids:
            _cid(occurrence_id, "memo prefix occurrence")
        expected_memo = 3 * min(self.prefix_length, 3)
        expected_hits = 3 * max(self.prefix_length - 3, 0)
        expected_relation = (
            AuditExecutionRelation.EQUAL
            if self.prefix_length <= 3
            else AuditExecutionRelation.MEMO_FEWER_FULL_AUDITS
        )
        if (
            self.prefix_length > 10
            or self.no_reuse_full_audit_executions != 3 * self.prefix_length
            or self.memo_full_audit_executions != expected_memo
            or self.memo_hits != expected_hits
            or self.memo_entries != expected_memo
            or self.plan_candidates_each_arm != 2 * self.prefix_length
            or self.relation is not expected_relation
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.scalar_gate_status != "NOT_RUN"
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo prefix curve or scalar claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.proof_memoization_prefix.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "prefix_length": self.prefix_length,
            "occurrence_ids": list(self.occurrence_ids),
            "no_reuse_full_audit_executions": (
                self.no_reuse_full_audit_executions
            ),
            "memo_full_audit_executions": self.memo_full_audit_executions,
            "memo_hits": self.memo_hits,
            "memo_entries": self.memo_entries,
            "plan_candidates_each_arm": self.plan_candidates_each_arm,
            "relation": self.relation.value,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "scalar_gate_status": self.scalar_gate_status,
        }

    @property
    def prefix_id(self) -> str:
        return _content_id("prefix", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prefix_id": self.prefix_id}

_MEMOIZED_EXECUTION_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class MemoizedHeldOutFamilyExecutionV1:
    memo_semantics: FixedPlanAuditMemoSemanticsV1
    family_promotion_result_id: str
    family_protocol_id: str
    occurrences: tuple[MemoizedHeldOutOccurrenceV1, ...]
    use_receipts: tuple[FixedPlanAuditCacheUseReceiptV1, ...]
    final_cache: FixedPlanAuditMemoCacheV1
    aggregate_work: ProofMemoizationAggregateWorkV1
    prefixes: tuple[ProofMemoizationPrefixV1, ...]
    initial_store_empty: bool
    no_control_warm_start: bool
    _authority: object = field(repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._authority is not _MEMOIZED_EXECUTION_AUTHORITY:
            raise CertificateMemoizationInvariantViolation(
                "memoized execution was not minted by the trusted runner"
            )
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_MEMOIZED_EXECUTION_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise CertificateMemoizationInvariantViolation(
                    "memoized execution is copied, replaced, or modified"
                ) from error
        if (
            type(self.memo_semantics) is not FixedPlanAuditMemoSemanticsV1
            or type(self.final_cache) is not FixedPlanAuditMemoCacheV1
            or type(self.aggregate_work) is not ProofMemoizationAggregateWorkV1
        ):
            raise CertificateMemoizationInvariantViolation(
                "memoized execution rejects substituted core artifacts"
            )
        for field_name in ("family_promotion_result_id", "family_protocol_id"):
            _cid(getattr(self, field_name), f"memo execution {field_name}")
        if (
            type(self.occurrences) is not tuple
            or len(self.occurrences) != 10
            or any(
                type(item) is not MemoizedHeldOutOccurrenceV1
                for item in self.occurrences
            )
            or type(self.use_receipts) is not tuple
            or len(self.use_receipts) != 30
            or any(
                type(item) is not FixedPlanAuditCacheUseReceiptV1
                for item in self.use_receipts
            )
            or type(self.prefixes) is not tuple
            or len(self.prefixes) != 10
            or any(type(item) is not ProofMemoizationPrefixV1 for item in self.prefixes)
            or self.aggregate_work.route_kind is not MemoRouteKind.EXACT_IDENTITY_MEMO
            or self.initial_store_empty is not True
            or self.no_control_warm_start is not True
        ):
            raise CertificateMemoizationInvariantViolation(
                "memoized execution cardinality, work, or empty-start contract changed"
            )
        _validate_memoized_execution_trace(self)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.memoized_held_out_family_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "memo_semantics": self.memo_semantics.to_document(),
            "family_promotion_result_id": self.family_promotion_result_id,
            "family_protocol_id": self.family_protocol_id,
            "occurrences": [item.to_document() for item in self.occurrences],
            "use_receipts": [item.to_document() for item in self.use_receipts],
            "final_cache": self.final_cache.to_document(),
            "aggregate_work": self.aggregate_work.to_document(),
            "prefixes": [item.to_document() for item in self.prefixes],
            "initial_store_empty": self.initial_store_empty,
            "no_control_warm_start": self.no_control_warm_start,
        }

    @property
    def execution_id(self) -> str:
        return _content_id("execution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_id": self.execution_id}


def _validate_memoized_execution_trace(
    execution: MemoizedHeldOutFamilyExecutionV1,
) -> None:
    entries_by_id = {
        item.entry_id: item for item in execution.final_cache.entries
    }
    if len(entries_by_id) != 9:
        raise CertificateMemoizationInvariantViolation(
            "memo execution final entry IDs are not unique"
        )
    state: dict[str, FixedPlanAuditMemoEntryV1] = {}
    empty_state_id = _cache_state_id(state)
    if execution.use_receipts[0].pre_cache_state_id != empty_state_id:
        raise CertificateMemoizationInvariantViolation(
            "memo execution did not start from an empty cache"
        )
    for sequence, receipt in enumerate(execution.use_receipts, start=1):
        if receipt.lookup_sequence != sequence:
            raise CertificateMemoizationInvariantViolation(
                "memo lookup sequence is not contiguous"
            )
        entry = entries_by_id.get(receipt.cache_entry_id)
        if entry is None:
            raise CertificateMemoizationInvariantViolation(
                "memo receipt references an unknown final entry"
            )
        key = entry.memo_key
        if (
            receipt.memo_key_id != key.key_id
            or receipt.audit_result_id != entry.audit_result.result_id
            or receipt.proof_role is not key.audit_role
            or receipt.target_query_id != key.target_query_id
            or receipt.source_miss_occurrence_id
            != entry.execution_attestation.source_occurrence_id
            or receipt.source_miss_sequence
            != entry.execution_attestation.source_resolution_sequence
            or receipt.pre_cache_state_id != _cache_state_id(state)
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo receipt key, proof payload, provenance, or pre-state changed"
            )
        existing = state.get(key.key_id)
        if receipt.outcome is MemoLookupOutcome.MISS_FULL_AUDIT_EXECUTED:
            if (
                existing is not None
                or receipt.source_miss_occurrence_id != receipt.occurrence_id
                or receipt.source_miss_sequence != sequence
            ):
                raise CertificateMemoizationInvariantViolation(
                    "memo miss overwrites an entry or has foreign source provenance"
                )
            state[key.key_id] = entry
        else:
            if (
                existing is None
                or existing.entry_id != entry.entry_id
                or receipt.source_miss_sequence >= sequence
            ):
                raise CertificateMemoizationInvariantViolation(
                    "memo hit precedes or substitutes its trusted miss"
                )
        if receipt.post_cache_state_id != _cache_state_id(state):
            raise CertificateMemoizationInvariantViolation(
                "memo receipt post-state does not match append-only replay"
            )

    if (
        set(state) != {item.memo_key.key_id for item in execution.final_cache.entries}
        or _cache_state_id(state) != execution.final_cache.cache_state_id
    ):
        raise CertificateMemoizationInvariantViolation(
            "memo trace does not reconstruct the final cache"
        )

    all_receipt_ids = tuple(item.receipt_id for item in execution.use_receipts)
    for occurrence_index, occurrence in enumerate(execution.occurrences):
        group = execution.use_receipts[
            3 * occurrence_index : 3 * occurrence_index + 3
        ]
        expected_ids = (
            *occurrence.candidate_resolution_receipt_ids,
            occurrence.selected_resolution_receipt_id,
        )
        if (
            tuple(item.receipt_id for item in group) != expected_ids
            or tuple(item.occurrence_id for item in group)
            != (occurrence.occurrence.occurrence_id,) * 3
            or tuple(item.target_query_id for item in group)
            != (occurrence.target_query_id,) * 3
            or tuple(item.request_ordinal_within_occurrence for item in group)
            != (1, 2, 3)
            or tuple(item.proof_role for item in group)
            != (
                FixedPlanAuditRole.CANDIDATE_RANKING_AUDIT,
                FixedPlanAuditRole.CANDIDATE_RANKING_AUDIT,
                FixedPlanAuditRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE,
            )
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo occurrence receipts are reordered, cross-query, or cross-role"
            )
        group_entries = tuple(
            entries_by_id[item.cache_entry_id] for item in group
        )
        candidate_plan_ids = tuple(
            sorted(
                item.memo_key.contingent_plan_id
                for item in group_entries[:2]
            )
        )
        expected_candidate_plan_ids = tuple(
            item.contingent_plan_id
            for item in occurrence.plan_proposal.candidate_summaries
        )
        selected_entry = group_entries[2]
        if (
            candidate_plan_ids != expected_candidate_plan_ids
            or selected_entry.memo_key.contingent_plan_id
            != occurrence.plan_proposal.selected_plan.plan_id
            or selected_entry.memo_key.planner_result_id
            != occurrence.plan_proposal.result_id
            or selected_entry.audit_result.result_id
            != occurrence.plan_audit.audit_result.result_id
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo receipt keys do not bind the candidate set or selected plan"
            )
        hits = sum(
            item.outcome is MemoLookupOutcome.HIT_EXACT_IDENTITY
            for item in group
        )
        misses = 3 - hits
        if (
            occurrence.work.memo_hit_count != hits
            or occurrence.work.memo_miss_count != misses
            or occurrence.work.full_audit_execution_count != misses
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo occurrence work differs from its use receipts"
            )

    if len(set(all_receipt_ids)) != 30:
        raise CertificateMemoizationInvariantViolation(
            "memo receipt IDs are not unique"
        )
    aggregate = execution.aggregate_work
    if (
        aggregate.plan_candidate_count
        != sum(item.work.plan_candidate_count for item in execution.occurrences)
        or aggregate.logical_proof_request_count != len(execution.use_receipts)
        or aggregate.full_audit_execution_count
        != sum(
            item.full_audit_execution_count for item in execution.use_receipts
        )
        or aggregate.memo_hit_count
        != sum(
            item.outcome is MemoLookupOutcome.HIT_EXACT_IDENTITY
            for item in execution.use_receipts
        )
        or aggregate.memo_miss_count
        != sum(
            item.outcome is MemoLookupOutcome.MISS_FULL_AUDIT_EXECUTED
            for item in execution.use_receipts
        )
        or aggregate.cache_insert_count
        != sum(item.cache_insert_count for item in execution.use_receipts)
        or aggregate.entry_identity_validation_count
        != sum(
            item.entry_identity_validation_count
            for item in execution.use_receipts
        )
    ):
        raise CertificateMemoizationInvariantViolation(
            "memo aggregate work cannot be replayed from native receipts"
        )
    expected_prefixes: list[ProofMemoizationPrefixV1] = []
    for length in range(1, len(execution.occurrences) + 1):
        prefix_occurrences = execution.occurrences[:length]
        prefix_receipts = execution.use_receipts[: 3 * length]
        memo_executions = sum(
            item.full_audit_execution_count for item in prefix_receipts
        )
        expected_prefixes.append(
            ProofMemoizationPrefixV1(
                length,
                tuple(
                    item.occurrence.occurrence_id
                    for item in prefix_occurrences
                ),
                3 * length,
                memo_executions,
                sum(
                    item.outcome is MemoLookupOutcome.HIT_EXACT_IDENTITY
                    for item in prefix_receipts
                ),
                sum(item.cache_insert_count for item in prefix_receipts),
                sum(
                    item.work.plan_candidate_count
                    for item in prefix_occurrences
                ),
                (
                    AuditExecutionRelation.EQUAL
                    if memo_executions == 3 * length
                    else AuditExecutionRelation.MEMO_FEWER_FULL_AUDITS
                ),
            )
        )
    if tuple(item.to_document() for item in execution.prefixes) != tuple(
        item.to_document() for item in expected_prefixes
    ):
        raise CertificateMemoizationInvariantViolation(
            "memo prefixes cannot be reconstructed from receipt slices"
        )


def require_memoized_heldout_family_execution_v1(
    execution: MemoizedHeldOutFamilyExecutionV1,
) -> MemoizedHeldOutFamilyExecutionV1:
    if type(execution) is not MemoizedHeldOutFamilyExecutionV1:
        raise CertificateMemoizationInvariantViolation(
            "memo execution requires the exact runtime-authority type"
        )
    try:
        require_runtime_authority_v1(
            execution,
            issuer=_MEMOIZED_EXECUTION_AUTHORITY,
        )
    except ValueError as error:
        raise CertificateMemoizationInvariantViolation(
            "memo execution lacks its exact owner-bound authority"
        ) from error
    _validate_memoized_execution_trace(execution)
    return execution


@dataclass(frozen=True, slots=True)
class MatchedProofMemoizationOccurrenceV1:
    occurrence_id: str
    target_query_id: str
    cold_direct_result_id: str
    no_reuse_threshold_binding_id: str
    memo_threshold_binding_id: str
    no_reuse_planner_result_id: str
    memo_planner_result_id: str
    selected_plan_id: str
    no_reuse_plan_audit_result_id: str
    memo_plan_audit_result_id: str
    memoized_occurrence_result_id: str
    memo_full_audit_execution_count: int
    memo_hit_count: int
    exact_threshold_binding_match: bool = True
    exact_planner_artifact_match: bool = True
    exact_audit_artifact_match: bool = True
    exact_cold_reward_risk_regret_match: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "occurrence_id",
            "target_query_id",
            "cold_direct_result_id",
            "no_reuse_threshold_binding_id",
            "memo_threshold_binding_id",
            "no_reuse_planner_result_id",
            "memo_planner_result_id",
            "selected_plan_id",
            "no_reuse_plan_audit_result_id",
            "memo_plan_audit_result_id",
            "memoized_occurrence_result_id",
        ):
            _cid(getattr(self, field_name), f"memo match {field_name}")
        _integer(
            self.memo_full_audit_execution_count,
            "memo match full audit count",
        )
        _integer(self.memo_hit_count, "memo match hit count")
        if (
            self.no_reuse_threshold_binding_id != self.memo_threshold_binding_id
            or self.no_reuse_planner_result_id != self.memo_planner_result_id
            or self.no_reuse_plan_audit_result_id
            != self.memo_plan_audit_result_id
            or (
                self.memo_full_audit_execution_count,
                self.memo_hit_count,
            )
            not in {(3, 0), (0, 3)}
            or self.exact_threshold_binding_match is not True
            or self.exact_planner_artifact_match is not True
            or self.exact_audit_artifact_match is not True
            or self.exact_cold_reward_risk_regret_match is not True
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo/no-reuse occurrence artifacts or semantic outcomes differ"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.matched_proof_memoization_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                field_name: getattr(self, field_name)
                for field_name in self.__dataclass_fields__
            },
        }

    @property
    def match_id(self) -> str:
        return _content_id("match", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "match_id": self.match_id}


@dataclass(frozen=True, slots=True)
class CertificateMemoizationTelemetryV1:
    unique_query_count: int
    logical_occurrence_count: int
    logical_proof_request_count: int
    candidate_role_request_count: int
    selected_role_request_count: int
    no_reuse_full_audit_executions: int
    memo_full_audit_executions: int
    memo_hits: int
    memo_misses: int
    cache_entries: int
    saved_full_audit_executions: int
    audit_execution_reduction: Fraction
    plan_candidates_each_arm: int
    matched_certificate_count: int
    first_prefix_with_full_audit_reduction: int
    target_ground_calls_each_arm: int
    proof_role_separation_enforced: bool = True
    full_artifact_equality_enforced: bool = True
    exact_identity_only: bool = True
    incremental_proof_claimed: bool = False
    cross_identity_reuse_claimed: bool = False
    persistent_cross_process_cache_claimed: bool = False
    sample_tax_operator_claimed: bool = False
    sample_efficiency_claimed: bool = False
    statistical_generalization_claimed: bool = False
    overall_workload_economics_claimed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate_status: str = "NOT_RUN"
    counter_completeness_gate_status: str = "NOT_RUN"
    sample_efficiency_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        expected = {
            "unique_query_count": 3,
            "logical_occurrence_count": 10,
            "logical_proof_request_count": 30,
            "candidate_role_request_count": 20,
            "selected_role_request_count": 10,
            "no_reuse_full_audit_executions": 30,
            "memo_full_audit_executions": 9,
            "memo_hits": 21,
            "memo_misses": 9,
            "cache_entries": 9,
            "saved_full_audit_executions": 21,
            "plan_candidates_each_arm": 20,
            "matched_certificate_count": 10,
            "first_prefix_with_full_audit_reduction": 4,
            "target_ground_calls_each_arm": 0,
        }
        for field_name, expected_value in expected.items():
            _integer(getattr(self, field_name), f"memo telemetry {field_name}")
            if getattr(self, field_name) != expected_value:
                raise CertificateMemoizationInvariantViolation(
                    f"memo telemetry {field_name} changed"
                )
        try:
            reduction = Fraction(self.audit_execution_reduction)
        except (TypeError, ValueError, ZeroDivisionError) as error:
            raise CertificateMemoizationInvariantViolation(
                "memo audit-execution reduction must be rational"
            ) from error
        object.__setattr__(self, "audit_execution_reduction", reduction)
        if (
            self.audit_execution_reduction != Fraction(7, 10)
            or self.proof_role_separation_enforced is not True
            or self.full_artifact_equality_enforced is not True
            or self.exact_identity_only is not True
            or self.incremental_proof_claimed is not False
            or self.cross_identity_reuse_claimed is not False
            or self.persistent_cross_process_cache_claimed is not False
            or self.sample_tax_operator_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.statistical_generalization_claimed is not False
            or self.overall_workload_economics_claimed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate_status != "NOT_RUN"
            or self.counter_completeness_gate_status != "NOT_RUN"
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo telemetry crossed the exact-repeat proof-compute claim boundary"
            )

    def _payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "acfqp.proof_memoization_telemetry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
        }
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            payload[field_name] = (
                {
                    "numerator": value.numerator,
                    "denominator": value.denominator,
                }
                if type(value) is Fraction
                else value
            )
        return payload

    @property
    def telemetry_id(self) -> str:
        return _content_id("telemetry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "telemetry_id": self.telemetry_id}


@dataclass(frozen=True, slots=True)
class CertificateMemoizationControlResultV1:
    parent_family_result_id: str
    family_promotion_result_id: str
    memoized_execution: MemoizedHeldOutFamilyExecutionV1
    matched_occurrences: tuple[MatchedProofMemoizationOccurrenceV1, ...]
    no_reuse_work: ProofMemoizationAggregateWorkV1
    memo_work: ProofMemoizationAggregateWorkV1
    telemetry: CertificateMemoizationTelemetryV1
    status: str = SUCCESS_STATUS
    incremental_proof_claimed: bool = False
    sample_efficiency_claimed: bool = False
    unrestricted_reuse_claimed: bool = False
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "parent_family_result_id",
            "family_promotion_result_id",
        ):
            _cid(getattr(self, field_name), f"memo control {field_name}")
        require_memoized_heldout_family_execution_v1(self.memoized_execution)
        if (
            type(self.matched_occurrences) is not tuple
            or len(self.matched_occurrences) != 10
            or any(
                type(item) is not MatchedProofMemoizationOccurrenceV1
                for item in self.matched_occurrences
            )
            or type(self.no_reuse_work) is not ProofMemoizationAggregateWorkV1
            or type(self.memo_work) is not ProofMemoizationAggregateWorkV1
            or type(self.telemetry) is not CertificateMemoizationTelemetryV1
            or self.family_promotion_result_id
            != self.memoized_execution.family_promotion_result_id
            or self.no_reuse_work.route_kind
            is not MemoRouteKind.NO_REUSE_CONTROL
            or self.memo_work.to_document()
            != self.memoized_execution.aggregate_work.to_document()
            or tuple(item.occurrence_id for item in self.matched_occurrences)
            != tuple(
                item.occurrence.occurrence_id
                for item in self.memoized_execution.occurrences
            )
            or self.status != SUCCESS_STATUS
            or self.incremental_proof_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.unrestricted_reuse_claimed is not False
            or self.official_execution_allowed is not False
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo control result identity, route, ordering, or claim lock changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.proof_memoization_control_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "parent_family_result_id": self.parent_family_result_id,
            "family_promotion_result_id": self.family_promotion_result_id,
            "memoized_execution": self.memoized_execution.to_document(),
            "matched_occurrences": [
                item.to_document() for item in self.matched_occurrences
            ],
            "no_reuse_work": self.no_reuse_work.to_document(),
            "memo_work": self.memo_work.to_document(),
            "telemetry": self.telemetry.to_document(),
            "status": self.status,
            "incremental_proof_claimed": self.incremental_proof_claimed,
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "unrestricted_reuse_claimed": self.unrestricted_reuse_claimed,
            "official_execution_allowed": self.official_execution_allowed,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}



def _planner_semantics_id(
    semantics: FixedPlanAuditMemoSemanticsV1,
) -> str:
    return _content_id(
        "planner_semantics",
        {
            "schema": "acfqp.held_out_family_planner_memo_semantics.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "parent_family_profile_key": family_module.PROFILE_KEY,
            "parent_family_schema_version": family_module.SCHEMA_VERSION,
            "family_planner_source_sha256": semantics.family_planner_source_sha256,
            "candidate_generation": "COMPLETE_H1_STAGE_ASSIGNMENT_ENUMERATION",
            "selection_mode": (
                PartialModelPlannerSelectionMode.INTERNAL_V0043_AUDIT_PASS_REWARD_MAX.value
            ),
            "tie_break": "NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1",
        },
    )


def _memo_key(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: HeldOutFamilyPromotionBuildV1,
    query: FamilyHeldOutQuerySpecV1,
    binding: HeldOutThresholdBindingV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    plan: FrozenContingentAbstractPlanV1,
    semantics: FixedPlanAuditMemoSemanticsV1,
    role: FixedPlanAuditRole,
    planner_result_id: str | None,
) -> FixedPlanAuditMemoKeyV1:
    if (
        observation_log.log_id != query.observation_log_id
        or semantics_profile.profile_id != query.semantics_profile_id
        or observation_authority.authority_id
        != promotion.model.observation_authority_id
        or binding.target_query_id != query.query_id
        or binding.promoted_model_id != promotion.model.model_id
        or thresholds.thresholds_id != binding.thresholds.thresholds_id
        or thresholds.partial_model_id != promotion.model.model_id
        or plan.partial_model_id != promotion.model.model_id
    ):
        raise CertificateMemoizationInvariantViolation(
            "live authority, query, threshold binding, or plan changed before lookup"
        )
    return FixedPlanAuditMemoKeyV1(
        role,
        semantics.semantics_id,
        query.structural_id,
        query.environment_instance_id,
        query.base_model_id,
        promotion.source_refinement_result_id,
        promotion.protocol.protocol_id,
        promotion.result_id,
        promotion.eligibility_proof.proof_id,
        promotion.model.model_id,
        observation_log.log_id,
        semantics_profile.profile_id,
        observation_authority.authority_id,
        query.query_id,
        binding.binding_id,
        thresholds.thresholds_id,
        thresholds.return_bound_proof.proof_id,
        plan.plan_id,
        _planner_semantics_id(semantics),
        planner_result_id,
    )


class _MemoRuntime:
    def __init__(
        self,
        observation_log: ObservationLogManifestV1,
        semantics_profile: DeterministicObservationProfileV1,
        observation_authority: PreregisteredObservationAuthorityV1,
        promotion: HeldOutFamilyPromotionBuildV1,
        semantics: FixedPlanAuditMemoSemanticsV1,
    ) -> None:
        self.observation_log = observation_log
        self.semantics_profile = semantics_profile
        self.observation_authority = observation_authority
        self.promotion = promotion
        self.semantics = semantics
        self.entries: dict[str, FixedPlanAuditMemoEntryV1] = {}
        self.receipts: list[FixedPlanAuditCacheUseReceiptV1] = []

    def resolve(
        self,
        occurrence: FamilyLogicalOccurrenceV1,
        query: FamilyHeldOutQuerySpecV1,
        binding: HeldOutThresholdBindingV1,
        thresholds: FrozenPartialAuditThresholdsV1,
        plan: FrozenContingentAbstractPlanV1,
        role: FixedPlanAuditRole,
        planner_result_id: str | None,
        request_ordinal: int,
    ) -> tuple[PartialSoundAuditResultV1, FixedPlanAuditCacheUseReceiptV1]:
        key = _memo_key(
            self.observation_log,
            self.semantics_profile,
            self.observation_authority,
            self.promotion,
            query,
            binding,
            thresholds,
            plan,
            self.semantics,
            role,
            planner_result_id,
        )
        sequence = len(self.receipts) + 1
        pre_state = _cache_state_id(self.entries)
        entry = self.entries.get(key.key_id)
        if entry is None:
            audit_result = _audit_verified_partial_model_v1(
                self.promotion.model,
                self.observation_log,
                self.semantics_profile,
                self.observation_authority,
                thresholds,
                plan,
            )
            if (
                audit_result.thresholds_id != thresholds.thresholds_id
                or (
                    role
                    is FixedPlanAuditRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE
                    and (
                        audit_result.outcome
                        is not PartialAuditOutcome.CERTIFIED_FIXED_PLAN
                        or audit_result.certificate is None
                    )
                )
            ):
                raise CertificateMemoizationInvariantViolation(
                    "memo miss produced an invalid threshold-bound role payload"
                )
            attestation = FullAuditExecutionAttestationV1(
                key.key_id,
                audit_result.result_id,
                (
                    audit_result.certificate.certificate_id
                    if audit_result.certificate is not None
                    else None
                ),
                occurrence.occurrence_id,
                sequence,
                self.semantics.semantics_id,
            )
            entry = FixedPlanAuditMemoEntryV1(key, audit_result, attestation)
            self.entries[key.key_id] = entry
            outcome = MemoLookupOutcome.MISS_FULL_AUDIT_EXECUTED
            execution_count = 1
            insert_count = 1
        else:
            if entry.memo_key.to_document() != key.to_document():
                raise CertificateMemoizationInvariantViolation(
                    "memo key hash collision or conflicting exact identity"
                )
            audit_result = entry.audit_result
            outcome = MemoLookupOutcome.HIT_EXACT_IDENTITY
            execution_count = 0
            insert_count = 0
        if (
            entry.audit_result.thresholds_id != thresholds.thresholds_id
            or entry.audit_result.partial_model_id
            != self.promotion.model.model_id
            or entry.audit_result.contingent_plan_id != plan.plan_id
            or entry.memo_key.audit_role is not role
        ):
            raise CertificateMemoizationInvariantViolation(
                "memo entry is stale, cross-threshold, cross-plan, or cross-role"
            )
        post_state = _cache_state_id(self.entries)
        receipt = FixedPlanAuditCacheUseReceiptV1(
            sequence,
            occurrence.occurrence_id,
            query.query_id,
            request_ordinal,
            role,
            key.key_id,
            entry.entry_id,
            audit_result.result_id,
            entry.execution_attestation.source_occurrence_id,
            entry.execution_attestation.source_resolution_sequence,
            outcome,
            pre_state,
            post_state,
            execution_count,
            insert_count,
        )
        self.receipts.append(receipt)
        return audit_result, receipt


def _run_memoized_occurrence(
    runtime: _MemoRuntime,
    occurrence: FamilyLogicalOccurrenceV1,
) -> MemoizedHeldOutOccurrenceV1:
    promotion = runtime.promotion
    query = _query_for_occurrence(promotion.protocol, occurrence)
    if query.initial_state.state_id not in promotion.model.authorized_initial_state_ids:
        raise CertificateMemoizationInvariantViolation(
            "memo occurrence lies outside the V5 family scope"
        )
    proof = canonical_lmb_n6_return_bound_proof_v1()
    thresholds = FrozenPartialAuditThresholdsV1(
        promotion.model.model_id,
        query.horizon,
        (InitialStateMassV1(query.initial_state.state_id, Fraction(1)),),
        query.reward_weights,
        query.normalized_regret_tolerance,
        query.risk_tolerance,
        proof,
    )
    binding = HeldOutThresholdBindingV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        query.query_id,
        promotion.model.model_id,
        thresholds,
    )

    # This call remains on every occurrence, including hits.  It revalidates
    # the live log/profile/authority and return-bound authority before lookup.
    _, domains = _planner_context(
        runtime.observation_log,
        runtime.semantics_profile,
        runtime.observation_authority,
        promotion.model,
        thresholds,
    )
    stage_count = 1
    for domain in domains:
        stage_count *= len(domain.semantic_action_ids)
    schedules = _stage_assignments(domains)
    plans: dict[str, FrozenContingentAbstractPlanV1] = {}
    summaries = []
    candidate_receipts: list[FixedPlanAuditCacheUseReceiptV1] = []
    for ordinal, schedule in enumerate(
        product(schedules, repeat=thresholds.horizon),
        start=1,
    ):
        plan = FrozenContingentAbstractPlanV1(
            promotion.model.model_id,
            thresholds.horizon,
            tuple(
                ContingentPlanStageV1(time_index, assignments)
                for time_index, assignments in enumerate(schedule)
            ),
        )
        audit_result, receipt = runtime.resolve(
            occurrence,
            query,
            binding,
            thresholds,
            plan,
            FixedPlanAuditRole.CANDIDATE_RANKING_AUDIT,
            None,
            ordinal,
        )
        plans[plan.plan_id] = plan
        summaries.append(_candidate_summary(thresholds, plan, audit_result))
        candidate_receipts.append(receipt)
    if len(candidate_receipts) != 2:
        raise CertificateMemoizationInvariantViolation(
            "memo planner must enumerate exactly two H1 candidates"
        )
    summaries_tuple = tuple(
        sorted(summaries, key=lambda item: item.contingent_plan_id)
    )
    mode, provisional = _selected_summary(summaries_tuple)
    numeric_key = family_module._selection_numeric_key(mode, provisional)
    tied = tuple(
        item
        for item in summaries_tuple
        if family_module._selection_numeric_key(mode, item) == numeric_key
    )
    selected = min(
        tied,
        key=lambda item: (
            family_module._semantic_plan_key(
                promotion.model,
                plans[item.contingent_plan_id],
            ),
            item.contingent_plan_id,
        ),
    )
    selected_plan = plans[selected.contingent_plan_id]
    proposal = HeldOutPlanProposalV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        query.query_id,
        promotion.model.model_id,
        binding.binding_id,
        thresholds.thresholds_id,
        domains,
        stage_count,
        stage_count,
        summaries_tuple,
        mode,
        selected_plan,
        family_module._semantic_plan_key(promotion.model, selected_plan),
        len(summaries_tuple),
    )
    independent, selected_receipt = runtime.resolve(
        occurrence,
        query,
        binding,
        thresholds,
        selected_plan,
        FixedPlanAuditRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE,
        proposal.result_id,
        3,
    )
    audit = HeldOutPlanAuditV1(
        promotion.result_id,
        promotion.protocol.protocol_id,
        query.query_id,
        promotion.model.model_id,
        binding.binding_id,
        proposal.result_id,
        selected_plan.plan_id,
        independent,
    )
    group = (*candidate_receipts, selected_receipt)
    hits = sum(
        item.outcome is MemoLookupOutcome.HIT_EXACT_IDENTITY for item in group
    )
    misses = 3 - hits
    work = MemoizedOccurrenceWorkV1(
        occurrence.occurrence_id,
        proposal.candidate_count,
        3,
        2,
        1,
        misses,
        3,
        hits,
        misses,
        misses,
        3,
    )
    return MemoizedHeldOutOccurrenceV1(
        occurrence,
        query.query_id,
        binding,
        proposal,
        audit,
        tuple(item.receipt_id for item in candidate_receipts),
        selected_receipt.receipt_id,
        work,
    )


def _memo_prefixes(
    occurrences: tuple[MemoizedHeldOutOccurrenceV1, ...],
) -> tuple[ProofMemoizationPrefixV1, ...]:
    prefixes: list[ProofMemoizationPrefixV1] = []
    for length in range(1, len(occurrences) + 1):
        prefix = occurrences[:length]
        memo_executions = sum(
            item.work.full_audit_execution_count for item in prefix
        )
        memo_hits = sum(item.work.memo_hit_count for item in prefix)
        prefixes.append(
            ProofMemoizationPrefixV1(
                length,
                tuple(item.occurrence.occurrence_id for item in prefix),
                3 * length,
                memo_executions,
                memo_hits,
                memo_executions,
                2 * length,
                (
                    AuditExecutionRelation.EQUAL
                    if 3 * length == memo_executions
                    else AuditExecutionRelation.MEMO_FEWER_FULL_AUDITS
                ),
            )
        )
    return tuple(prefixes)


def _mint_memoized_execution(
    semantics: FixedPlanAuditMemoSemanticsV1,
    promotion: HeldOutFamilyPromotionBuildV1,
    occurrences: tuple[MemoizedHeldOutOccurrenceV1, ...],
    receipts: tuple[FixedPlanAuditCacheUseReceiptV1, ...],
    cache: FixedPlanAuditMemoCacheV1,
    work: ProofMemoizationAggregateWorkV1,
    prefixes: tuple[ProofMemoizationPrefixV1, ...],
) -> MemoizedHeldOutFamilyExecutionV1:
    raw = MemoizedHeldOutFamilyExecutionV1(
        semantics,
        promotion.result_id,
        promotion.protocol.protocol_id,
        occurrences,
        receipts,
        cache,
        work,
        prefixes,
        True,
        True,
        _MEMOIZED_EXECUTION_AUTHORITY,
    )
    return bind_runtime_authority_v1(
        raw,
        issuer=_MEMOIZED_EXECUTION_AUTHORITY,
    )


def run_identity_bound_memoized_family_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    promotion: HeldOutFamilyPromotionBuildV1,
) -> MemoizedHeldOutFamilyExecutionV1:
    """Execute the frozen family from an empty role-separated exact memo."""

    if type(promotion) is not HeldOutFamilyPromotionBuildV1:
        raise CertificateMemoizationInvariantViolation(
            "memo runner rejects substituted promotion artifacts"
        )
    semantics = fixed_plan_audit_memo_semantics_v1()
    runtime = _MemoRuntime(
        observation_log,
        semantics_profile,
        observation_authority,
        promotion,
        semantics,
    )
    occurrences = tuple(
        _run_memoized_occurrence(runtime, occurrence)
        for occurrence in promotion.protocol.logical_occurrences
    )
    receipts = tuple(runtime.receipts)
    cache = FixedPlanAuditMemoCacheV1(
        tuple(sorted(runtime.entries.values(), key=lambda item: item.memo_key.key_id))
    )
    work = ProofMemoizationAggregateWorkV1(
        route_kind=MemoRouteKind.EXACT_IDENTITY_MEMO,
        logical_occurrence_count=10,
        plan_candidate_count=sum(
            item.work.plan_candidate_count for item in occurrences
        ),
        logical_proof_request_count=len(receipts),
        candidate_role_request_count=sum(
            item.proof_role is FixedPlanAuditRole.CANDIDATE_RANKING_AUDIT
            for item in receipts
        ),
        selected_role_request_count=sum(
            item.proof_role
            is FixedPlanAuditRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE
            for item in receipts
        ),
        full_audit_execution_count=sum(
            item.full_audit_execution_count for item in receipts
        ),
        memo_key_construction_count=len(receipts),
        memo_lookup_count=len(receipts),
        memo_hit_count=sum(
            item.outcome is MemoLookupOutcome.HIT_EXACT_IDENTITY
            for item in receipts
        ),
        memo_miss_count=sum(
            item.outcome is MemoLookupOutcome.MISS_FULL_AUDIT_EXECUTED
            for item in receipts
        ),
        cache_insert_count=sum(
            item.cache_insert_count for item in receipts
        ),
        entry_identity_validation_count=sum(
            item.entry_identity_validation_count for item in receipts
        ),
        target_transition_calls=0,
        target_catalogue_calls=0,
        direct_ground_optimizer_calls=0,
    )
    return _mint_memoized_execution(
        semantics,
        promotion,
        occurrences,
        receipts,
        cache,
        work,
        _memo_prefixes(occurrences),
    )


def lookup_fixed_plan_audit_memo_entry_v1(
    cache: FixedPlanAuditMemoCacheV1,
    memo_key: FixedPlanAuditMemoKeyV1,
) -> FixedPlanAuditMemoEntryV1 | None:
    """Diagnostic exact-key lookup; a public cache alone is not authority."""

    if type(cache) is not FixedPlanAuditMemoCacheV1:
        raise CertificateMemoizationInvariantViolation(
            "memo lookup rejects substituted caches"
        )
    if type(memo_key) is not FixedPlanAuditMemoKeyV1:
        raise CertificateMemoizationInvariantViolation(
            "memo lookup rejects substituted keys"
        )
    result = next(
        (
            entry
            for entry in cache.entries
            if entry.memo_key.key_id == memo_key.key_id
        ),
        None,
    )
    if result is not None and result.memo_key.to_document() != memo_key.to_document():
        raise CertificateMemoizationInvariantViolation(
            "memo lookup detected a key-ID collision"
        )
    return result


def _match_control_occurrence(
    no_reuse: MatchedHeldOutOccurrenceV1,
    memo: MemoizedHeldOutOccurrenceV1,
) -> MatchedProofMemoizationOccurrenceV1:
    if (
        no_reuse.occurrence.to_document() != memo.occurrence.to_document()
        or no_reuse.threshold_binding.to_document()
        != memo.threshold_binding.to_document()
        or no_reuse.warm_plan.to_document() != memo.plan_proposal.to_document()
        or no_reuse.warm_audit.to_document() != memo.plan_audit.to_document()
        or memo.plan_audit.audit_result.thresholds_id
        != memo.threshold_binding.thresholds.thresholds_id
    ):
        raise CertificateMemoizationInvariantViolation(
            "memo arm differs from the no-reuse planning/certificate artifacts"
        )
    bounds = memo.plan_audit.audit_result.robust_bounds
    if (
        bounds.policy_reward_lower != no_reuse.cold_direct.optimal_reward
        or bounds.policy_failure_upper
        != no_reuse.cold_direct.failure_probability
        or bounds.normalized_distribution_regret
        != no_reuse.cold_direct.normalized_regret
    ):
        raise CertificateMemoizationInvariantViolation(
            "memo certificate differs from the independent cold semantics"
        )
    return MatchedProofMemoizationOccurrenceV1(
        no_reuse.occurrence.occurrence_id,
        no_reuse.query.query_id,
        no_reuse.cold_direct.result_id,
        no_reuse.threshold_binding.binding_id,
        memo.threshold_binding.binding_id,
        no_reuse.warm_plan.result_id,
        memo.plan_proposal.result_id,
        memo.plan_proposal.selected_plan.plan_id,
        no_reuse.warm_audit.result_id,
        memo.plan_audit.result_id,
        memo.result_id,
        memo.work.full_audit_execution_count,
        memo.work.memo_hit_count,
    )


def run_lmb_certificate_memoization_control_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    parent_family_result: HeldOutFamilyAmortizationResultV1,
) -> CertificateMemoizationControlResultV1:
    """Compare a fresh empty memo arm with the frozen V0-049 no-reuse arm."""

    if type(parent_family_result) is not HeldOutFamilyAmortizationResultV1:
        raise CertificateMemoizationInvariantViolation(
            "memo control rejects substituted V0-049 parent results"
        )
    execution = run_identity_bound_memoized_family_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        parent_family_result.promotion_build,
    )
    matches = tuple(
        _match_control_occurrence(no_reuse, memo)
        for no_reuse, memo in zip(
            parent_family_result.matched_occurrences,
            execution.occurrences,
        )
    )
    no_reuse_work = ProofMemoizationAggregateWorkV1(
        route_kind=MemoRouteKind.NO_REUSE_CONTROL,
        logical_occurrence_count=len(
            parent_family_result.matched_occurrences
        ),
        plan_candidate_count=sum(
            item.warm_work.model_plan_candidates
            for item in parent_family_result.matched_occurrences
        ),
        logical_proof_request_count=sum(
            item.warm_work.model_fixed_plan_audits
            for item in parent_family_result.matched_occurrences
        ),
        candidate_role_request_count=20,
        selected_role_request_count=10,
        full_audit_execution_count=sum(
            item.warm_work.model_fixed_plan_audits
            for item in parent_family_result.matched_occurrences
        ),
        memo_key_construction_count=0,
        memo_lookup_count=0,
        memo_hit_count=0,
        memo_miss_count=0,
        cache_insert_count=0,
        entry_identity_validation_count=0,
        target_transition_calls=sum(
            item.warm_work.exact_transition_calls
            for item in parent_family_result.matched_occurrences
        ),
        target_catalogue_calls=sum(
            item.warm_work.direct_catalogue_calls
            for item in parent_family_result.matched_occurrences
        ),
        direct_ground_optimizer_calls=0,
    )
    telemetry = CertificateMemoizationTelemetryV1(
        3,
        len(matches),
        no_reuse_work.logical_proof_request_count,
        no_reuse_work.candidate_role_request_count,
        no_reuse_work.selected_role_request_count,
        no_reuse_work.full_audit_execution_count,
        execution.aggregate_work.full_audit_execution_count,
        execution.aggregate_work.memo_hit_count,
        execution.aggregate_work.memo_miss_count,
        len(execution.final_cache.entries),
        (
            no_reuse_work.full_audit_execution_count
            - execution.aggregate_work.full_audit_execution_count
        ),
        Fraction(
            no_reuse_work.full_audit_execution_count
            - execution.aggregate_work.full_audit_execution_count,
            no_reuse_work.full_audit_execution_count,
        ),
        no_reuse_work.plan_candidate_count,
        len(matches),
        next(
            item.prefix_length
            for item in execution.prefixes
            if item.relation
            is AuditExecutionRelation.MEMO_FEWER_FULL_AUDITS
        ),
        0,
    )
    return CertificateMemoizationControlResultV1(
        parent_family_result.result_id,
        parent_family_result.promotion_build.result_id,
        execution,
        matches,
        no_reuse_work,
        execution.aggregate_work,
        telemetry,
    )


def verify_lmb_certificate_memoization_control_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: ObservedTypedPartialRAPMResultV1,
    source_thresholds: FrozenPartialAuditThresholdsV1,
    source_base_plan_proposal: TypedPartialModelPlanProposalResultV2,
    source_failed_audit: TypedPartialSoundAuditResultV2,
    protocol: HeldOutFamilyProtocolV1,
    source_result: MultiStepQueryRefinementResultV1,
    kernel: LMBKernel,
    parent_family_result: HeldOutFamilyAmortizationResultV1,
    claimed_result: CertificateMemoizationControlResultV1,
) -> CertificateMemoizationControlResultV1:
    """Rebuild V0-049, then replay the empty memo trace and exact comparison."""

    if type(claimed_result) is not CertificateMemoizationControlResultV1:
        raise CertificateMemoizationInvariantViolation(
            "memo verifier rejects substituted claimed results"
        )
    require_memoized_heldout_family_execution_v1(
        claimed_result.memoized_execution
    )
    verified_parent = verify_lmb_heldout_family_amortization_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        source_thresholds,
        source_base_plan_proposal,
        source_failed_audit,
        protocol,
        source_result,
        kernel,
        parent_family_result,
    )
    replayed = run_lmb_certificate_memoization_control_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        verified_parent,
    )
    if replayed.to_document() != claimed_result.to_document():
        raise CertificateMemoizationInvariantViolation(
            "independent V0-050 replay differs from the claimed artifact"
        )
    return replayed


__all__ = [
    "AuditExecutionRelation",
    "CertificateMemoizationControlResultV1",
    "CertificateMemoizationInvariantViolation",
    "CertificateMemoizationTelemetryV1",
    "FixedPlanAuditCacheUseReceiptV1",
    "FixedPlanAuditMemoCacheV1",
    "FixedPlanAuditMemoEntryV1",
    "FixedPlanAuditMemoKeyV1",
    "FixedPlanAuditMemoSemanticsV1",
    "FixedPlanAuditRole",
    "FullAuditExecutionAttestationV1",
    "MatchedProofMemoizationOccurrenceV1",
    "MemoLookupOutcome",
    "MemoRouteKind",
    "MemoizedHeldOutFamilyExecutionV1",
    "MemoizedHeldOutOccurrenceV1",
    "MemoizedOccurrenceWorkV1",
    "ProofMemoizationAggregateWorkV1",
    "ProofMemoizationPrefixV1",
    "fixed_plan_audit_memo_semantics_v1",
    "lookup_fixed_plan_audit_memo_entry_v1",
    "require_memoized_heldout_family_execution_v1",
    "run_identity_bound_memoized_family_v1",
    "run_lmb_certificate_memoization_control_v1",
    "verify_lmb_certificate_memoization_control_v1",
]
