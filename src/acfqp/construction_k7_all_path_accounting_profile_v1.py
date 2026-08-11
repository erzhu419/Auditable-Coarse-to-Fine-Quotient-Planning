"""Non-retroactive all-path accounting profile for the K7 successor.

Contract 2.0.33 freezes the *schema obligations* needed before any additional
K7 production path may be called counter-complete.  It does not execute a
route, issue a counter, classify a live terminal, or unlock a Gate.

The profile has three deliberately separate parts:

* the exact FQ9 terminal class/code taxonomy and one accounting recipe per
  terminal code;
* the finite attempt/rebuild policy from FQ4/FQ8;
* an exhaustive inventory of every current ``v075_*.py`` ``str, Enum`` whose
  class name contains ``Terminal`` or ``Status``.  Every member is explicitly
  classified as ``MAP_TO_FQ9``, ``PROFILE_EXTENSION_REQUIRED`` or
  ``NONTERMINAL``.  A new class/member cannot silently inherit a default.

All content domains are centrally registered and IDs use the normative
``SHA256(domain || 0x00 || canonical-json)`` construction.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
import hashlib
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import RouteKindEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ALL_PATH_ACCOUNTING_PROFILE_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_ALL_PATH_ACCOUNTING_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_V075_TERMINAL_STATUS_INVENTORY_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    parse_content_id,
)
from acfqp.routing_v1 import TerminalClass, TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.33"
PROFILE_KEY = "construction_k7_all_path_accounting_profile_v1"

ALL_PATH_ACCOUNTING_PROFILE_V1_DOMAIN = (
    CONSTRUCTION_K7_ALL_PATH_ACCOUNTING_PROFILE_V1_DOMAIN
)
ALL_PATH_ACCOUNTING_PROFILE_REPLAY_V1_DOMAIN = (
    CONSTRUCTION_K7_ALL_PATH_ACCOUNTING_PROFILE_REPLAY_V1_DOMAIN
)
V075_TERMINAL_STATUS_INVENTORY_V1_DOMAIN = (
    CONSTRUCTION_K7_V075_TERMINAL_STATUS_INVENTORY_V1_DOMAIN
)

LOCAL_DOMAIN_TAGS = frozenset(
    {
        ALL_PATH_ACCOUNTING_PROFILE_V1_DOMAIN,
        ALL_PATH_ACCOUNTING_PROFILE_REPLAY_V1_DOMAIN,
        V075_TERMINAL_STATUS_INVENTORY_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS.issubset(PHASE3E_DOMAIN_TAGS):  # pragma: no cover
    raise RuntimeError("K7 all-path profile domains must be centrally registered")

EXPECTED_FQ9_TERMINAL_CLASS_COUNT = 3
EXPECTED_FQ9_TERMINAL_CODE_COUNT = 10
EXPECTED_ROUTE_KIND_COUNT = 5
EXPECTED_STAGE_COUNT = 10
EXPECTED_ACCOUNTING_FAMILY_COUNT = 7
EXPECTED_V075_STATUS_ENUM_CLASS_COUNT = 48
EXPECTED_V075_STATUS_ENUM_MEMBER_COUNT = 167

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_PROFILE_ISSUER = object()
_REPLAY_ISSUER = object()


class ConstructionK7AllPathAccountingProfileV1Error(ValueError):
    """An all-path taxonomy, identity, or explicit disposition is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AllPathAccountingProfileV1Error(message)


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("all-path profile used an unknown local content domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AllPathAccountingProfileV1Error(
            f"{field_name} must be one exact content ID"
        ) from error


def _identifier(value: Any, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        _fail(f"{field_name} must be one canonical identifier")
    return value


class StageDispositionV1(str, Enum):
    REQUIRED_ONCE = "REQUIRED_ONCE"
    REQUIRED_AT_LEAST_ONCE = "REQUIRED_AT_LEAST_ONCE"
    OPTIONAL_ONCE = "OPTIONAL_ONCE"
    OPTIONAL_REPEATABLE = "OPTIONAL_REPEATABLE"
    PREFIX_DEPENDENT_THROUGH_FAILURE_CUTOFF = (
        "PREFIX_DEPENDENT_THROUGH_FAILURE_CUTOFF"
    )
    FORBIDDEN = "FORBIDDEN"


class AccountingFamilyV1(str, Enum):
    COMMON_OWNER = "COMMON_OWNER"
    LOCAL_OWNER = "LOCAL_OWNER"
    FALLBACK_OWNER = "FALLBACK_OWNER"
    REBUILD_OWNER = "REBUILD_OWNER"
    PROFILE_NATIVE_ZERO = "PROFILE_NATIVE_ZERO"
    SHARED_RESOURCE = "SHARED_RESOURCE"
    DERIVED_RECONCILIATION = "DERIVED_RECONCILIATION"


class AccountingFamilyDispositionV1(str, Enum):
    OWNER_EVIDENCE_REQUIRED = "OWNER_EVIDENCE_REQUIRED"
    OWNER_EVIDENCE_IF_REACHED_ELSE_NATIVE_ZERO = (
        "OWNER_EVIDENCE_IF_REACHED_ELSE_NATIVE_ZERO"
    )
    NATIVE_ZERO_ATTESTATION_REQUIRED = "NATIVE_ZERO_ATTESTATION_REQUIRED"
    REQUIRED_FOR_EVERY_UNREACHED_OR_INACTIVE_REQUIRED_LEAF = (
        "REQUIRED_FOR_EVERY_UNREACHED_OR_INACTIVE_REQUIRED_LEAF"
    )
    COMPLETE_RECEIPTS_THROUGH_TERMINAL_CUTOFF_REQUIRED = (
        "COMPLETE_RECEIPTS_THROUGH_TERMINAL_CUTOFF_REQUIRED"
    )
    EXACT_REPLAY_NO_DOUBLE_CHARGE_REQUIRED = (
        "EXACT_REPLAY_NO_DOUBLE_CHARGE_REQUIRED"
    )


class RetryDispositionV1(str, Enum):
    CLOSE_LOGICAL_OCCURRENCE = "CLOSE_LOGICAL_OCCURRENCE"
    REBUILD_POLICY_CONTROLLED = "REBUILD_POLICY_CONTROLLED"


class EvidenceAuthorityStateV1(str, Enum):
    REGISTERED_CURRENT_AUTHORITY = "REGISTERED_CURRENT_AUTHORITY"
    SUCCESSOR_AUTHORITY_REQUIRED = "SUCCESSOR_AUTHORITY_REQUIRED"


class V075StatusDispositionV1(str, Enum):
    MAP_TO_FQ9 = "MAP_TO_FQ9"
    PROFILE_EXTENSION_REQUIRED = "PROFILE_EXTENSION_REQUIRED"
    NONTERMINAL = "NONTERMINAL"


@dataclass(frozen=True, slots=True, order=True)
class StagePlanEntryV1:
    stage_kind: registry_v6.ConstructionStageKindV6
    disposition: StageDispositionV1

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "stage_kind",
                registry_v6.ConstructionStageKindV6(self.stage_kind),
            )
            object.__setattr__(
                self, "disposition", StageDispositionV1(self.disposition)
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7AllPathAccountingProfileV1Error(
                "stage-plan entry is invalid"
            ) from error

    def to_document(self) -> dict[str, str]:
        return {
            "stage_kind": self.stage_kind.value,
            "disposition": self.disposition.value,
        }


@dataclass(frozen=True, slots=True, order=True)
class AccountingFamilyRuleV1:
    family: AccountingFamilyV1
    disposition: AccountingFamilyDispositionV1

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "family", AccountingFamilyV1(self.family))
            object.__setattr__(
                self,
                "disposition",
                AccountingFamilyDispositionV1(self.disposition),
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7AllPathAccountingProfileV1Error(
                "accounting-family rule is invalid"
            ) from error

    def to_document(self) -> dict[str, str]:
        return {
            "family": self.family.value,
            "disposition": self.disposition.value,
        }


@dataclass(frozen=True, slots=True, order=True)
class RequiredEvidenceRoleV1:
    role: str
    required_outcome: str
    authority_state: EvidenceAuthorityStateV1

    def __post_init__(self) -> None:
        _identifier(self.role, "evidence role")
        _identifier(self.required_outcome, "required evidence outcome")
        try:
            object.__setattr__(
                self,
                "authority_state",
                EvidenceAuthorityStateV1(self.authority_state),
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7AllPathAccountingProfileV1Error(
                "evidence authority state is invalid"
            ) from error

    def to_document(self) -> dict[str, str]:
        return {
            "role": self.role,
            "required_outcome": self.required_outcome,
            "authority_state": self.authority_state.value,
        }


@dataclass(frozen=True, slots=True)
class TerminalPathRuleV1:
    terminal_class: TerminalClass
    terminal_code: TerminalCode
    route_kinds_permitted_in_attempt: tuple[RouteKindEnum, ...]
    stage_plan: tuple[StagePlanEntryV1, ...]
    accounting_family_rules: tuple[AccountingFamilyRuleV1, ...]
    required_evidence_roles: tuple[RequiredEvidenceRoleV1, ...]
    retry_disposition: RetryDispositionV1
    separate_work_vector_per_route_segment_required: bool = True
    local_failure_and_fallback_must_remain_distinct_vectors: bool = True

    def __post_init__(self) -> None:
        try:
            terminal_class = TerminalClass(self.terminal_class)
            terminal_code = TerminalCode(self.terminal_code)
            routes = tuple(
                RouteKindEnum(item) for item in self.route_kinds_permitted_in_attempt
            )
            retry = RetryDispositionV1(self.retry_disposition)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AllPathAccountingProfileV1Error(
                "terminal-path taxonomy value is invalid"
            ) from error
        object.__setattr__(self, "terminal_class", terminal_class)
        object.__setattr__(self, "terminal_code", terminal_code)
        object.__setattr__(self, "route_kinds_permitted_in_attempt", routes)
        object.__setattr__(self, "retry_disposition", retry)
        stages = tuple(self.stage_plan)
        families = tuple(self.accounting_family_rules)
        evidence = tuple(self.required_evidence_roles)
        object.__setattr__(self, "stage_plan", stages)
        object.__setattr__(self, "accounting_family_rules", families)
        object.__setattr__(self, "required_evidence_roles", evidence)
        if (
            not routes
            or len(set(routes)) != len(routes)
            or any(type(row) is not StagePlanEntryV1 for row in stages)
            or tuple(row.stage_kind for row in stages) != _CANONICAL_STAGE_ORDER
            or any(type(row) is not AccountingFamilyRuleV1 for row in families)
            or tuple(row.family for row in families) != tuple(AccountingFamilyV1)
            or not evidence
            or any(type(row) is not RequiredEvidenceRoleV1 for row in evidence)
            or tuple(sorted(evidence)) != evidence
            or len({row.role for row in evidence}) != len(evidence)
            or evidence != _evidence_roles(terminal_code)
            or self.separate_work_vector_per_route_segment_required is not True
            or self.local_failure_and_fallback_must_remain_distinct_vectors
            is not True
        ):
            _fail("terminal-path stage/family/evidence coverage is incomplete")
        if _FQ9_CLASS_BY_CODE[terminal_code] is not terminal_class:
            _fail("terminal class/code violates the exact FQ9 taxonomy")
        if (
            terminal_code is TerminalCode.REBUILD_REQUIRED
            and retry is not RetryDispositionV1.REBUILD_POLICY_CONTROLLED
        ) or (
            terminal_code is not TerminalCode.REBUILD_REQUIRED
            and retry is not RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE
        ):
            _fail("terminal retry disposition violates FQ8/FQ9")

    def to_document(self) -> dict[str, Any]:
        return {
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "route_kinds_permitted_in_attempt": [
                item.value for item in self.route_kinds_permitted_in_attempt
            ],
            "stage_plan": [item.to_document() for item in self.stage_plan],
            "accounting_family_rules": [
                item.to_document() for item in self.accounting_family_rules
            ],
            "required_evidence_roles": [
                item.to_document() for item in self.required_evidence_roles
            ],
            "retry_disposition": self.retry_disposition.value,
            "separate_work_vector_per_route_segment_required": True,
            "local_failure_and_fallback_must_remain_distinct_vectors": True,
        }


@dataclass(frozen=True, slots=True, order=True)
class V075StatusMappingV1:
    source_module: str
    enum_class: str
    member_name: str
    member_value: str
    disposition: V075StatusDispositionV1
    fq9_terminal_class: str | None
    fq9_terminal_code: str | None
    reason_code: str

    def __post_init__(self) -> None:
        for field_name in (
            "source_module",
            "enum_class",
            "member_name",
            "member_value",
            "reason_code",
        ):
            _identifier(getattr(self, field_name), field_name)
        try:
            disposition = V075StatusDispositionV1(self.disposition)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AllPathAccountingProfileV1Error(
                "V075 status disposition is invalid"
            ) from error
        object.__setattr__(self, "disposition", disposition)
        if disposition is V075StatusDispositionV1.MAP_TO_FQ9:
            try:
                terminal_class = TerminalClass(self.fq9_terminal_class)
                terminal_code = TerminalCode(self.fq9_terminal_code)
            except (TypeError, ValueError) as error:
                raise ConstructionK7AllPathAccountingProfileV1Error(
                    "MAP_TO_FQ9 requires one exact FQ9 class/code"
                ) from error
            if _FQ9_CLASS_BY_CODE[terminal_code] is not terminal_class:
                _fail("V075 mapping targets a mismatched FQ9 class/code")
            object.__setattr__(self, "fq9_terminal_class", terminal_class.value)
            object.__setattr__(self, "fq9_terminal_code", terminal_code.value)
        elif self.fq9_terminal_class is not None or self.fq9_terminal_code is not None:
            _fail("non-mapping V075 status must not carry an FQ9 target")

    @property
    def source_key(self) -> str:
        return f"{self.source_module}:{self.enum_class}:{self.member_name}"

    def to_document(self) -> dict[str, Any]:
        return {
            "source_module": self.source_module,
            "enum_class": self.enum_class,
            "member_name": self.member_name,
            "member_value": self.member_value,
            "disposition": self.disposition.value,
            "fq9_terminal_class": self.fq9_terminal_class,
            "fq9_terminal_code": self.fq9_terminal_code,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class AttemptRebuildPolicyV1:
    max_local_transactions_per_logical_occurrence: int = 2
    legal_transaction_indices: tuple[int, ...] = (1, 2)
    default_rebuild_allowed: bool = False
    max_rebuild_attempts_when_registered: int = 1
    max_route_attempts_per_logical_occurrence: int = 2
    economics_denominator: str = "LOGICAL_OCCURRENCE"
    new_build_epoch_required_on_rebuild: bool = True
    new_route_attempt_required_on_rebuild: bool = True
    regenerate_all_route_identities_after_rebuild: bool = True
    preserve_all_prior_attempt_work: bool = True

    def __post_init__(self) -> None:
        if (
            self.max_local_transactions_per_logical_occurrence != 2
            or self.legal_transaction_indices != (1, 2)
            or self.default_rebuild_allowed is not False
            or self.max_rebuild_attempts_when_registered != 1
            or self.max_route_attempts_per_logical_occurrence != 2
            or self.economics_denominator != "LOGICAL_OCCURRENCE"
            or self.new_build_epoch_required_on_rebuild is not True
            or self.new_route_attempt_required_on_rebuild is not True
            or self.regenerate_all_route_identities_after_rebuild is not True
            or self.preserve_all_prior_attempt_work is not True
        ):
            _fail("attempt/rebuild policy differs from FQ4/FQ8")

    def to_document(self) -> dict[str, Any]:
        return {
            "max_local_transactions_per_logical_occurrence": 2,
            "legal_transaction_indices": [1, 2],
            "default_rebuild_allowed": False,
            "max_rebuild_attempts_when_registered": 1,
            "max_route_attempts_per_logical_occurrence": 2,
            "economics_denominator": "LOGICAL_OCCURRENCE",
            "new_build_epoch_required_on_rebuild": True,
            "new_route_attempt_required_on_rebuild": True,
            "regenerate_all_route_identities_after_rebuild": True,
            "preserve_all_prior_attempt_work": True,
        }


_FQ9_CLASS_BY_CODE: Mapping[TerminalCode, TerminalClass] = MappingProxyType(
    {
        TerminalCode.ABSTRACT_CERTIFIED: TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.LOCAL_GROUND_RECOVERY: TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.FULL_GROUND_FALLBACK: TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.CACHED_EXACT_INFEASIBLE: (
            TerminalClass.INFEASIBILITY_CERTIFICATE
        ),
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: (
            TerminalClass.INFEASIBILITY_CERTIFICATE
        ),
        TerminalCode.INTEGRITY_FAILURE: (
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
        TerminalCode.PROTOCOL_FAILURE: (
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
        TerminalCode.REBUILD_REQUIRED: (
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
        TerminalCode.FALLBACK_CAP_EXHAUSTED: (
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
        TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: (
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
    }
)

_CANONICAL_STAGE_ORDER = (
    registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX,
    registry_v6.ConstructionStageKindV6.INITIAL_ACQUISITION,
    registry_v6.ConstructionStageKindV6.INITIAL_MODEL_BUILD,
    registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX,
    registry_v6.ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION,
    registry_v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING,
    registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT,
    registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
    registry_v6.ConstructionStageKindV6.REBUILD,
    registry_v6.ConstructionStageKindV6.CLOSED_RECONCILIATION_AND_TERMINALIZATION,
)


# This is the exact source inventory at Contract 2.0.33.  The live AST replay
# below must match it byte-for-semantic-value; this is what prevents a new
# member in an already nonterminal class from inheriting that disposition.
_EXPECTED_V075_STATUS_ENUM_INVENTORY_V1 = (
    (
        "v075_adaptive_acquisition_proposal_authority_v1",
        "V075RoundProposalStatusV1",
        (
            ("AUTHORIZED", "AUTHORIZED"),
            ("NO_UNCERTAIN_SELECTED_FRONTIER", "NO_UNCERTAIN_SELECTED_FRONTIER"),
            ("INCREMENTAL_CAP_EXHAUSTED", "INCREMENTAL_CAP_EXHAUSTED"),
        ),
    ),
    (
        "v075_adaptive_acquisition_round_bundle_authority_v1",
        "V075BundleAuthorizationStatusV1",
        (
            ("AUTHORIZED", "AUTHORIZED"),
            ("NO_UNCERTAIN_PROOF_FRONTIER", "NO_UNCERTAIN_PROOF_FRONTIER"),
            ("INCREMENTAL_CAP_EXHAUSTED", "INCREMENTAL_CAP_EXHAUSTED"),
        ),
    ),
    (
        "v075_batch_native_total_lift_authority_v1",
        "V075BatchTotalLiftConstructionStatusV1",
        (
            ("EXACT_POSITIVE_CONSTRUCTION_CONTROL", "EXACT_POSITIVE_CONSTRUCTION_CONTROL"),
            ("EXACT_POLICY_RISK_FAILURE", "EXACT_POLICY_RISK_FAILURE"),
            ("EXACT_POLICY_REGRET_FAILURE", "EXACT_POLICY_REGRET_FAILURE"),
            ("EXACT_GROUND_QUERY_INFEASIBLE", "EXACT_GROUND_QUERY_INFEASIBLE"),
            ("STATISTICAL_ENVELOPE_MISS", "STATISTICAL_ENVELOPE_MISS"),
        ),
    ),
    (
        "v075_batch_native_total_lift_authority_v1",
        "V075BatchTotalLiftProductionStatusV1",
        (
            ("EXACT_POSITIVE_PRODUCTION_CANDIDATE", "EXACT_POSITIVE_PRODUCTION_CANDIDATE"),
            ("EXACT_POLICY_RISK_FAILURE", "EXACT_POLICY_RISK_FAILURE"),
            ("EXACT_POLICY_REGRET_FAILURE", "EXACT_POLICY_REGRET_FAILURE"),
            ("EXACT_GROUND_QUERY_INFEASIBLE", "EXACT_GROUND_QUERY_INFEASIBLE"),
            ("STATISTICAL_ENVELOPE_MISS", "STATISTICAL_ENVELOPE_MISS"),
        ),
    ),
    (
        "v075_batch_native_total_lift_authority_v2",
        "V075V2TotalLiftStatus",
        (
            ("EXACT_POSITIVE_CONSTRUCTION_CONTROL", "EXACT_POSITIVE_CONSTRUCTION_CONTROL"),
            ("EXACT_GROUND_QUERY_INFEASIBLE", "EXACT_GROUND_QUERY_INFEASIBLE"),
            ("EXACT_POLICY_RISK_FAILURE", "EXACT_POLICY_RISK_FAILURE"),
            ("EXACT_POLICY_REGRET_FAILURE", "EXACT_POLICY_REGRET_FAILURE"),
            ("STATISTICAL_BACKEND_INCOMPLETE", "STATISTICAL_BACKEND_INCOMPLETE"),
        ),
    ),
    (
        "v075_batch_occurrence_lifecycle_authority_v2",
        "V075BatchLifecycleTerminalCodeV2",
        (("COMPLETE_OBSERVED_REQUIRED_ROWS_CONSTRUCTION_CONTROL", "COMPLETE_OBSERVED_REQUIRED_ROWS_CONSTRUCTION_CONTROL"),),
    ),
    (
        "v075_batch_occurrence_lifecycle_authority_v2",
        "V075BatchFailureTerminalCodeV2",
        (
            ("CAP_EXHAUSTED", "CAP_EXHAUSTED"),
            ("PROTOCOL_FAILURE", "PROTOCOL_FAILURE"),
            ("INTEGRITY_FAILURE", "INTEGRITY_FAILURE"),
            ("POLICY_ABORT_NONCERTIFICATE", "POLICY_ABORT_NONCERTIFICATE"),
        ),
    ),
    (
        "v075_campaign_reconciliation_v1",
        "V075OccurrenceTerminalClassV1",
        (
            ("PLAN_CERTIFICATE", "PLAN_CERTIFICATE"),
            ("INFEASIBILITY_CERTIFICATE", "INFEASIBILITY_CERTIFICATE"),
            ("ATTEMPT_CLOSURE_NONCERTIFICATE", "ATTEMPT_CLOSURE_NONCERTIFICATE"),
        ),
    ),
    (
        "v075_campaign_reconciliation_v1",
        "V075OccurrenceTerminalCodeV1",
        (
            ("EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE", "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE"),
            ("EXACT_INFEASIBILITY_CERTIFICATE", "EXACT_INFEASIBILITY_CERTIFICATE"),
            ("TOTAL_LIFT_NONCERTIFICATE", "TOTAL_LIFT_NONCERTIFICATE"),
            ("CAP_EXHAUSTED", "CAP_EXHAUSTED"),
            ("PROTOCOL_FAILURE", "PROTOCOL_FAILURE"),
            ("INTEGRITY_FAILURE", "INTEGRITY_FAILURE"),
        ),
    ),
    (
        "v075_campaign_reconciliation_v1",
        "V075ConstructionTerminalEvidenceKindV1",
        (
            ("EXACT_VALID_PLAN", "EXACT_VALID_PLAN"),
            ("EXACT_INFEASIBLE", "EXACT_INFEASIBLE"),
            ("TOTAL_LIFT_FAILED", "TOTAL_LIFT_FAILED"),
            ("CAP_EXHAUSTED", "CAP_EXHAUSTED"),
            ("PROTOCOL_FAILURE", "PROTOCOL_FAILURE"),
            ("INTEGRITY_FAILURE", "INTEGRITY_FAILURE"),
        ),
    ),
    (
        "v075_dynamic_child_closure_intent_authority_v2",
        "V075DynamicChildClosureIntentStatusV2",
        (
            ("AUTHORIZED", "CHILD_CLOSURE_DISCOVERY_INTENTS_AUTHORIZED"),
            ("ALREADY_COMPLETE", "CHILD_CLOSURE_ALREADY_COMPLETE"),
            ("CHILD_ACTION_ROW_CAP_EXCEEDED", "CHILD_ACTION_ROW_CAP_EXCEEDED"),
            ("CHILD_ACTION_CATALOGUE_NOT_YET_BOUND", "CHILD_ACTION_CATALOGUE_NOT_YET_BOUND"),
        ),
    ),
    (
        "v075_integrated_direct_occurrence_pipeline_v1",
        "V075IntegratedDirectTerminalV1",
        (
            ("READY_FOR_EXACT_TOTAL_LIFT", "READY_FOR_EXACT_TOTAL_LIFT"),
            ("DIRECT_CHECKPOINT_CAP_EXHAUSTED", "DIRECT_CHECKPOINT_CAP_EXHAUSTED"),
        ),
    ),
    (
        "v075_integrated_occurrence_pipeline_v1",
        "V075IntegratedOccurrenceTerminalCodeV1",
        (
            ("CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT", "CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT"),
            ("NO_UNCERTAIN_PROOF_FRONTIER", "NO_UNCERTAIN_PROOF_FRONTIER"),
            ("INCREMENTAL_CAP_EXHAUSTED", "INCREMENTAL_CAP_EXHAUSTED"),
            ("PLANNER_SEARCH_CAP_EXHAUSTED", "PLANNER_SEARCH_CAP_EXHAUSTED"),
            ("ADAPTIVE_ROUND_LIMIT_REACHED", "ADAPTIVE_ROUND_LIMIT_REACHED"),
        ),
    ),
    (
        "v075_k7_atomic_shared_resource_authority_v1",
        "ProductionConnectionStatusV1",
        (
            ("VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE", "VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE"),
            ("VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE", "VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE"),
            ("NOT_CONNECTED", "NOT_CONNECTED"),
        ),
    ),
    (
        "v075_k7_os_supervisor_admission_v1",
        "K7OSSupervisorAdmissionStatusV1",
        (("NOT_AVAILABLE", "NOT_AVAILABLE"),),
    ),
    (
        "v075_learned_support_quotient_planners_v1",
        "V075PlannerStatusV1",
        (
            ("CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT", "CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT"),
            ("STATISTICAL_ENVELOPE_NOT_CERTIFIED", "STATISTICAL_ENVELOPE_NOT_CERTIFIED"),
            ("NO_RISK_FEASIBLE_POLICY", "NO_RISK_FEASIBLE_POLICY"),
            ("SEARCH_CAP_EXHAUSTED", "SEARCH_CAP_EXHAUSTED"),
        ),
    ),
    (
        "v075_live_batched_causal_promotion_v3",
        "V075LiveBatchedCausalPromotionDecisionStatusV3",
        (
            ("AUTHORIZED", "PROMOTION_AUTHORIZED"),
            ("CANDIDATE_EARLY_STOP", "CANDIDATE_EARLY_STOP"),
            ("NO_ELIGIBLE_FRONTIER_ROW", "NO_ELIGIBLE_FRONTIER_ROW"),
        ),
    ),
    (
        "v075_live_dynamic_acquisition_authority_v2",
        "V075LiveDynamicChildClosureStatusV2",
        (
            ("AUTHORIZED", "DYNAMIC_CHILD_BASE_ACQUISITION_AUTHORIZED"),
            ("CANDIDATE_EARLY_STOP", "CANDIDATE_EARLY_STOP"),
            ("ALREADY_COMPLETE", "DYNAMIC_CHILD_CLOSURE_ALREADY_COMPLETE"),
            ("CHILD_ACTION_ROW_CAP_EXCEEDED", "CHILD_ACTION_ROW_CAP_EXCEEDED"),
        ),
    ),
    (
        "v075_live_dynamic_acquisition_authority_v2",
        "V075LivePromotionDecisionStatusV2",
        (
            ("AUTHORIZED", "PROMOTION_AUTHORIZED"),
            ("CANDIDATE_EARLY_STOP", "CANDIDATE_EARLY_STOP"),
            ("NO_ELIGIBLE_FRONTIER_ROW", "NO_ELIGIBLE_FRONTIER_ROW"),
        ),
    ),
    (
        "v075_multistage_observer_lifecycle_v1",
        "V075LifecycleTerminalCodeV1",
        (
            ("COMPLETE_REGISTERED_CHECKPOINT_CLOSED", "COMPLETE_REGISTERED_CHECKPOINT_CLOSED"),
            ("NONCERTIFICATE_PROTOCOL_CLOSED", "NONCERTIFICATE_PROTOCOL_CLOSED"),
            ("NONCERTIFICATE_CAP_CLOSED", "NONCERTIFICATE_CAP_CLOSED"),
        ),
    ),
    (
        "v075_observer_signed_multiround_occurrence_runner_v2",
        "V075ObserverSignedMultiroundTerminalStatusV2",
        (
            ("CANDIDATE_EARLY_STOP", "CANDIDATE_EARLY_STOP"),
            ("CHILD_ACTION_ROW_CAP_EXCEEDED", "CHILD_ACTION_ROW_CAP_EXCEEDED"),
            ("CANDIDATE_AFTER_CHILD_CLOSURE", "CANDIDATE_AFTER_CHILD_CLOSURE"),
            ("CANDIDATE_AFTER_PROMOTION_ONE", "CANDIDATE_AFTER_PROMOTION_ONE"),
            ("CANDIDATE_AFTER_PROMOTION_TWO", "CANDIDATE_AFTER_PROMOTION_TWO"),
            ("NO_ELIGIBLE_PROMOTION_ROW", "NO_ELIGIBLE_PROMOTION_ROW"),
            ("PROMOTION_BUDGET_EXHAUSTED", "PROMOTION_BUDGET_EXHAUSTED"),
        ),
    ),
    (
        "v075_occurrence_failure_lifecycle_authority_v1",
        "V075OccurrenceFailureTerminalCodeV1",
        (
            ("PROTOCOL_FAILURE", "PROTOCOL_FAILURE"),
            ("PROCESS_FAILURE", "PROCESS_FAILURE"),
            ("TIMEOUT", "TIMEOUT"),
            ("DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED", "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED"),
        ),
    ),
    (
        "v075_portable_construction_closed_reconciliation_authority_v2",
        "V075ConstructionClosedReconciliationRoleStatusV2",
        (
            ("FULL_CONSTRUCTION_COMPILER_REPLAY", "FULL_CONSTRUCTION_COMPILER_REPLAY"),
            ("FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY", "FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY"),
            ("STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED", "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"),
        ),
    ),
    (
        "v075_portable_construction_lifecycle_authority_v2",
        "V075PortableConstructionLifecycleRoleStatusV2",
        (
            ("FULL_PUBLIC", "FULL_PUBLIC"),
            ("STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED", "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"),
            ("NOT_PRESENT_IN_OCCURRENCE", "NOT_PRESENT_IN_OCCURRENCE"),
        ),
    ),
    (
        "v075_portable_construction_multiround_result_authority_v2",
        "V075ConstructionMultiroundResultRoleStatusV2",
        (
            ("FULL_CONSTRUCTION_COMPILER_REPLAY", "FULL_CONSTRUCTION_COMPILER_REPLAY"),
            ("FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY", "FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY"),
            ("FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY", "FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY"),
        ),
    ),
    (
        "v075_portable_construction_planning_input_authority_v2",
        "V075ConstructionPlanningInputRoleStatusV2",
        (
            ("FULL_CONSTRUCTION_COMPILER_REPLAY", "FULL_CONSTRUCTION_COMPILER_REPLAY"),
            ("STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED", "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"),
        ),
    ),
    (
        "v075_portable_construction_private_replay_authority_v2",
        "V075ConstructionPrivateReplayRoleStatusV2",
        (
            ("FULL_CONSTRUCTION_PRIVATE_REPLAY", "FULL_CONSTRUCTION_PRIVATE_REPLAY"),
            ("FULL_CONSTRUCTION_TRANSITIVE", "FULL_CONSTRUCTION_TRANSITIVE"),
            ("STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED", "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"),
        ),
    ),
    (
        "v075_portable_dynamic_child_proposal_authority_v2",
        "V075PortableDynamicChildProposalRoleStatusV2",
        (
            ("FULL_PUBLIC", "FULL_PUBLIC"),
            ("STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED", "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"),
            ("NOT_PRESENT_IN_OCCURRENCE", "NOT_PRESENT_IN_OCCURRENCE"),
        ),
    ),
    (
        "v075_portable_live_epoch_authority_v2",
        "V075PortableLiveEpochRoleStatusV2",
        (
            ("FULL_PUBLIC", "FULL_PUBLIC"),
            ("STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED", "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"),
            ("NOT_PRESENT_IN_OCCURRENCE", "NOT_PRESENT_IN_OCCURRENCE"),
        ),
    ),
    (
        "v075_portable_planning_authority_v2",
        "V075PortablePlanningRoleStatusV2",
        (
            ("FULL_PUBLIC", "FULL_PUBLIC"),
            ("STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED", "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"),
            ("NOT_PRESENT_IN_OCCURRENCE", "NOT_PRESENT_IN_OCCURRENCE"),
        ),
    ),
    (
        "v075_portable_public_lineage_authority_v2",
        "V075PortablePublicLineageRoleStatusV2",
        (
            ("FULL_PUBLIC", "FULL_PUBLIC"),
            ("STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED", "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"),
            ("NOT_PRESENT_IN_OCCURRENCE", "NOT_PRESENT_IN_OCCURRENCE"),
        ),
    ),
    (
        "v075_portable_public_semantic_replay_v2",
        "V075PortablePublicRoleReplayStatusV2",
        (("COMPLETE", "COMPLETE"), ("INCOMPLETE", "INCOMPLETE")),
    ),
    (
        "v075_portable_root_boundary_authority_v2",
        "V075PortableRootRoleClosureStatusV2",
        (
            ("FULL_PUBLIC", "FULL_PUBLIC"),
            ("STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED", "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"),
            ("NOT_PRESENT_IN_OCCURRENCE", "NOT_PRESENT_IN_OCCURRENCE"),
        ),
    ),
    (
        "v075_portable_semantic_registry_v2",
        "V075PortableSemanticReplayStatusV2",
        (("COMPLETE", "COMPLETE"), ("INCOMPLETE", "INCOMPLETE")),
    ),
    (
        "v075_portable_semantic_terminal_closure_v2",
        "V075PortableSemanticTerminalRoleStatusV2",
        (
            ("FULL_TYPED_REPLAY", "FULL_TYPED_REPLAY"),
            ("NOT_PRESENT_IN_VERIFIED_OCCURRENCE", "NOT_PRESENT_IN_VERIFIED_OCCURRENCE"),
        ),
    ),
    (
        "v075_portable_signed_batch_graph_authority_v2",
        "V075PortableM1ARoleReplayStatusV2",
        (
            ("COMPLETE", "COMPLETE"),
            ("INCOMPLETE_DEPENDENCY_CLOSURE", "INCOMPLETE_DEPENDENCY_CLOSURE"),
            ("UNRESOLVED_PRIVATE_REPLAY_CLAIM", "UNRESOLVED_PRIVATE_REPLAY_CLAIM"),
        ),
    ),
    (
        "v075_portable_signed_control_graph_authority_v2",
        "V075PortableControlRoleClosureStatusV2",
        (
            ("FULL_PUBLIC", "FULL_PUBLIC"),
            ("STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED", "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"),
            ("NOT_PRESENT_IN_OCCURRENCE", "NOT_PRESENT_IN_OCCURRENCE"),
        ),
    ),
    (
        "v075_production_occurrence_authority_v1",
        "V075ProductionOccurrenceTerminalClassV1",
        (
            ("PLAN_CERTIFICATE", "PLAN_CERTIFICATE"),
            ("INFEASIBILITY_CERTIFICATE", "INFEASIBILITY_CERTIFICATE"),
            ("ATTEMPT_CLOSURE_NONCERTIFICATE", "ATTEMPT_CLOSURE_NONCERTIFICATE"),
        ),
    ),
    (
        "v075_production_occurrence_authority_v1",
        "V075ProductionOccurrenceTerminalCodeV1",
        (
            ("EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE", "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE"),
            ("EXACT_INFEASIBILITY_CERTIFICATE", "EXACT_INFEASIBILITY_CERTIFICATE"),
            ("EXACT_POLICY_RISK_FAILURE", "EXACT_POLICY_RISK_FAILURE"),
            ("EXACT_POLICY_REGRET_FAILURE", "EXACT_POLICY_REGRET_FAILURE"),
            ("STATISTICAL_ENVELOPE_MISS", "STATISTICAL_ENVELOPE_MISS"),
            ("PLANNER_SEARCH_CAP_EXHAUSTED", "PLANNER_SEARCH_CAP_EXHAUSTED"),
            ("INCREMENTAL_CAP_EXHAUSTED", "INCREMENTAL_CAP_EXHAUSTED"),
            ("ADAPTIVE_ROUND_LIMIT_REACHED", "ADAPTIVE_ROUND_LIMIT_REACHED"),
            ("NO_UNCERTAIN_PROOF_FRONTIER", "NO_UNCERTAIN_PROOF_FRONTIER"),
            ("DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED", "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED"),
            ("INTEGRITY_FAILURE", "INTEGRITY_FAILURE"),
            ("PROTOCOL_FAILURE", "PROTOCOL_FAILURE"),
            ("PROCESS_FAILURE", "PROCESS_FAILURE"),
            ("TIMEOUT", "TIMEOUT"),
        ),
    ),
    (
        "v075_production_occurrence_authority_v2",
        "V075OccurrenceTerminalClassV2",
        (("ATTEMPT_CLOSURE_NONCERTIFICATE", "ATTEMPT_CLOSURE_NONCERTIFICATE"),),
    ),
    (
        "v075_production_occurrence_authority_v2",
        "V075OccurrenceTerminalCodeV2",
        (("CONSTRUCTION_CONTROL_ONLY", "CONSTRUCTION_CONTROL_ONLY"),),
    ),
    (
        "v075_registered_occurrence_worker_v1",
        "V075WorkerBackendStatusV1",
        (("NOT_READY", "NOT_READY"),),
    ),
    (
        "v075_route_native_backend_core_v1",
        "V075BackendScheduleStatusV1",
        (
            ("COMPLETE_REGISTERED_CHECKPOINT", "COMPLETE_REGISTERED_CHECKPOINT"),
            ("PREFIX_BEFORE_REGISTERED_CHECKPOINT", "PREFIX_BEFORE_REGISTERED_CHECKPOINT"),
            ("INVALID_OR_OVER_CAP", "INVALID_OR_OVER_CAP"),
        ),
    ),
    (
        "v075_route_native_backend_core_v1",
        "V075BackendCandidateStatusV1",
        (
            ("NOT_READY_NO_VALIDATION", "NOT_READY_NO_VALIDATION"),
            ("NOT_READY_INCOMPLETE_ACTION_CATALOGUE", "NOT_READY_INCOMPLETE_ACTION_CATALOGUE"),
            ("NOT_READY_TYPED_SUPPORT_GRAPH_BINDER", "NOT_READY_TYPED_SUPPORT_GRAPH_BINDER"),
            ("NOT_READY_V075_QUOTIENT_COMPILER", "NOT_READY_V075_QUOTIENT_COMPILER"),
            ("NOT_READY_V075_DIRECT_ROBUST_SOLVER", "NOT_READY_V075_DIRECT_ROBUST_SOLVER"),
        ),
    ),
    (
        "v075_schedule_bound_acquisition_lifecycle_v2",
        "V075InitialAcquisitionTerminalCodeV2",
        (
            ("INITIAL_COMPLETE_AWAITING_SOUND_PLANNER", "INITIAL_COMPLETE_AWAITING_SOUND_PLANNER"),
            ("ROOT_DISCOVERY_COMPLETE_AWAITING_CHILD_EXPANSION", "ROOT_DISCOVERY_COMPLETE_AWAITING_CHILD_EXPANSION"),
        ),
    ),
    (
        "v075_schedule_bound_acquisition_lifecycle_v2",
        "V075InitialIntentExecutionStatusV2",
        (
            ("DISCOVERY_BATCH_MATCHED", "DISCOVERY_BATCH_MATCHED"),
            ("DIRECT_DISCOVERY_BATCH_MATCHED", "DIRECT_DISCOVERY_BATCH_MATCHED"),
            ("SUPPORT_FREEZE_MATCHED", "SUPPORT_FREEZE_MATCHED"),
            ("VALIDATION_BATCH_MATCHED", "VALIDATION_BATCH_MATCHED"),
            ("PENDING_DIRECT_CHILD_EXPANSION", "PENDING_DIRECT_CHILD_EXPANSION"),
        ),
    ),
    (
        "v075_schedule_bound_sound_planning_authority_v2",
        "V075ScheduleBoundPlanningTerminalCodeV2",
        (
            ("CANDIDATE_AWAITING_INDEPENDENT_TOTAL_LIFT", "CANDIDATE_AWAITING_INDEPENDENT_TOTAL_LIFT"),
            ("FAILED_FRONTIER_AWAITING_DYNAMIC_ACQUISITION", "FAILED_FRONTIER_AWAITING_DYNAMIC_ACQUISITION"),
            ("PLANNING_DEFERRED_AWAITING_CHILD_EXPANSION", "PLANNING_DEFERRED_AWAITING_CHILD_EXPANSION"),
        ),
    ),
    (
        "v075_total_lift_authority_v1",
        "V075TotalLiftEndpointStatusV1",
        (
            ("EXACT_POSITIVE_ENDPOINT", "EXACT_POSITIVE_ENDPOINT"),
            ("EXACT_POLICY_RISK_FAILURE", "EXACT_POLICY_RISK_FAILURE"),
            ("EXACT_POLICY_REGRET_FAILURE", "EXACT_POLICY_REGRET_FAILURE"),
            ("EXACT_GROUND_QUERY_INFEASIBLE", "EXACT_GROUND_QUERY_INFEASIBLE"),
        ),
    ),
)


_EXPLICIT_NONTERMINAL_ENUM_CLASSES_V1 = frozenset(
    {
        ("v075_adaptive_acquisition_proposal_authority_v1", "V075RoundProposalStatusV1"),
        ("v075_adaptive_acquisition_round_bundle_authority_v1", "V075BundleAuthorizationStatusV1"),
        ("v075_batch_native_total_lift_authority_v1", "V075BatchTotalLiftConstructionStatusV1"),
        ("v075_batch_native_total_lift_authority_v1", "V075BatchTotalLiftProductionStatusV1"),
        ("v075_batch_native_total_lift_authority_v2", "V075V2TotalLiftStatus"),
        ("v075_batch_occurrence_lifecycle_authority_v2", "V075BatchLifecycleTerminalCodeV2"),
        ("v075_campaign_reconciliation_v1", "V075OccurrenceTerminalClassV1"),
        ("v075_campaign_reconciliation_v1", "V075ConstructionTerminalEvidenceKindV1"),
        ("v075_dynamic_child_closure_intent_authority_v2", "V075DynamicChildClosureIntentStatusV2"),
        ("v075_k7_atomic_shared_resource_authority_v1", "ProductionConnectionStatusV1"),
        ("v075_k7_os_supervisor_admission_v1", "K7OSSupervisorAdmissionStatusV1"),
        ("v075_learned_support_quotient_planners_v1", "V075PlannerStatusV1"),
        ("v075_live_batched_causal_promotion_v3", "V075LiveBatchedCausalPromotionDecisionStatusV3"),
        ("v075_live_dynamic_acquisition_authority_v2", "V075LiveDynamicChildClosureStatusV2"),
        ("v075_live_dynamic_acquisition_authority_v2", "V075LivePromotionDecisionStatusV2"),
        ("v075_observer_signed_multiround_occurrence_runner_v2", "V075ObserverSignedMultiroundTerminalStatusV2"),
        ("v075_portable_construction_closed_reconciliation_authority_v2", "V075ConstructionClosedReconciliationRoleStatusV2"),
        ("v075_portable_construction_lifecycle_authority_v2", "V075PortableConstructionLifecycleRoleStatusV2"),
        ("v075_portable_construction_multiround_result_authority_v2", "V075ConstructionMultiroundResultRoleStatusV2"),
        ("v075_portable_construction_planning_input_authority_v2", "V075ConstructionPlanningInputRoleStatusV2"),
        ("v075_portable_construction_private_replay_authority_v2", "V075ConstructionPrivateReplayRoleStatusV2"),
        ("v075_portable_dynamic_child_proposal_authority_v2", "V075PortableDynamicChildProposalRoleStatusV2"),
        ("v075_portable_live_epoch_authority_v2", "V075PortableLiveEpochRoleStatusV2"),
        ("v075_portable_planning_authority_v2", "V075PortablePlanningRoleStatusV2"),
        ("v075_portable_public_lineage_authority_v2", "V075PortablePublicLineageRoleStatusV2"),
        ("v075_portable_public_semantic_replay_v2", "V075PortablePublicRoleReplayStatusV2"),
        ("v075_portable_root_boundary_authority_v2", "V075PortableRootRoleClosureStatusV2"),
        ("v075_portable_semantic_registry_v2", "V075PortableSemanticReplayStatusV2"),
        ("v075_portable_semantic_terminal_closure_v2", "V075PortableSemanticTerminalRoleStatusV2"),
        ("v075_portable_signed_batch_graph_authority_v2", "V075PortableM1ARoleReplayStatusV2"),
        ("v075_portable_signed_control_graph_authority_v2", "V075PortableControlRoleClosureStatusV2"),
        ("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalClassV1"),
        ("v075_production_occurrence_authority_v2", "V075OccurrenceTerminalClassV2"),
        ("v075_registered_occurrence_worker_v1", "V075WorkerBackendStatusV1"),
        ("v075_route_native_backend_core_v1", "V075BackendScheduleStatusV1"),
        ("v075_route_native_backend_core_v1", "V075BackendCandidateStatusV1"),
        ("v075_schedule_bound_acquisition_lifecycle_v2", "V075InitialAcquisitionTerminalCodeV2"),
        ("v075_schedule_bound_acquisition_lifecycle_v2", "V075InitialIntentExecutionStatusV2"),
        ("v075_schedule_bound_sound_planning_authority_v2", "V075ScheduleBoundPlanningTerminalCodeV2"),
        ("v075_total_lift_authority_v1", "V075TotalLiftEndpointStatusV1"),
    }
)


def _special(
    module: str,
    enum_class: str,
    member_name: str,
    disposition: V075StatusDispositionV1,
    target: TerminalCode | None,
    reason_code: str,
) -> tuple[tuple[str, str, str], tuple[V075StatusDispositionV1, TerminalCode | None, str]]:
    return (
        (module, enum_class, member_name),
        (disposition, target, reason_code),
    )


_SPECIAL_V075_MEMBER_POLICIES_V1 = dict(
    (
        _special("v075_batch_occurrence_lifecycle_authority_v2", "V075BatchFailureTerminalCodeV2", "CAP_EXHAUSTED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "BATCH_CAP_IS_ATTEMPT_BUDGET_WITH_CAUSE_PRESERVED"),
        _special("v075_batch_occurrence_lifecycle_authority_v2", "V075BatchFailureTerminalCodeV2", "PROTOCOL_FAILURE", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.PROTOCOL_FAILURE, "EXACT_FQ9_PROTOCOL_FAILURE"),
        _special("v075_batch_occurrence_lifecycle_authority_v2", "V075BatchFailureTerminalCodeV2", "INTEGRITY_FAILURE", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.INTEGRITY_FAILURE, "EXACT_FQ9_INTEGRITY_FAILURE"),
        _special("v075_batch_occurrence_lifecycle_authority_v2", "V075BatchFailureTerminalCodeV2", "POLICY_ABORT_NONCERTIFICATE", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_POLICY_ABORT_CODE"),
        _special("v075_campaign_reconciliation_v1", "V075OccurrenceTerminalCodeV1", "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_PLAN_CODE_REQUIRES_ROUTE_PROVENANCE"),
        _special("v075_campaign_reconciliation_v1", "V075OccurrenceTerminalCodeV1", "EXACT_INFEASIBILITY_CERTIFICATE", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.FULL_GROUND_EXACT_INFEASIBLE, "EXACT_GROUND_INFEASIBILITY_PROOF"),
        _special("v075_campaign_reconciliation_v1", "V075OccurrenceTerminalCodeV1", "TOTAL_LIFT_NONCERTIFICATE", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_GENERIC_TOTAL_LIFT_FAILURE_CODE"),
        _special("v075_campaign_reconciliation_v1", "V075OccurrenceTerminalCodeV1", "CAP_EXHAUSTED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "OCCURRENCE_CAP_IS_ATTEMPT_BUDGET_WITH_CAUSE_PRESERVED"),
        _special("v075_campaign_reconciliation_v1", "V075OccurrenceTerminalCodeV1", "PROTOCOL_FAILURE", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.PROTOCOL_FAILURE, "EXACT_FQ9_PROTOCOL_FAILURE"),
        _special("v075_campaign_reconciliation_v1", "V075OccurrenceTerminalCodeV1", "INTEGRITY_FAILURE", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.INTEGRITY_FAILURE, "EXACT_FQ9_INTEGRITY_FAILURE"),
        _special("v075_integrated_direct_occurrence_pipeline_v1", "V075IntegratedDirectTerminalV1", "READY_FOR_EXACT_TOTAL_LIFT", V075StatusDispositionV1.NONTERMINAL, None, "AWAITS_INDEPENDENT_TOTAL_LIFT"),
        _special("v075_integrated_direct_occurrence_pipeline_v1", "V075IntegratedDirectTerminalV1", "DIRECT_CHECKPOINT_CAP_EXHAUSTED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "DIRECT_CHECKPOINT_CAP_IS_ATTEMPT_BUDGET"),
        _special("v075_integrated_occurrence_pipeline_v1", "V075IntegratedOccurrenceTerminalCodeV1", "CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT", V075StatusDispositionV1.NONTERMINAL, None, "AWAITS_INDEPENDENT_TOTAL_LIFT"),
        _special("v075_integrated_occurrence_pipeline_v1", "V075IntegratedOccurrenceTerminalCodeV1", "NO_UNCERTAIN_PROOF_FRONTIER", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_NO_FRONTIER_CODE"),
        _special("v075_integrated_occurrence_pipeline_v1", "V075IntegratedOccurrenceTerminalCodeV1", "INCREMENTAL_CAP_EXHAUSTED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "INCREMENTAL_CAP_IS_ATTEMPT_BUDGET"),
        _special("v075_integrated_occurrence_pipeline_v1", "V075IntegratedOccurrenceTerminalCodeV1", "PLANNER_SEARCH_CAP_EXHAUSTED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "PLANNER_CAP_IS_ATTEMPT_BUDGET"),
        _special("v075_integrated_occurrence_pipeline_v1", "V075IntegratedOccurrenceTerminalCodeV1", "ADAPTIVE_ROUND_LIMIT_REACHED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "ROUND_LIMIT_IS_ATTEMPT_BUDGET"),
        _special("v075_multistage_observer_lifecycle_v1", "V075LifecycleTerminalCodeV1", "COMPLETE_REGISTERED_CHECKPOINT_CLOSED", V075StatusDispositionV1.NONTERMINAL, None, "LIFECYCLE_CHECKPOINT_PRECEDES_ATTEMPT_TERMINAL"),
        _special("v075_multistage_observer_lifecycle_v1", "V075LifecycleTerminalCodeV1", "NONCERTIFICATE_PROTOCOL_CLOSED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.PROTOCOL_FAILURE, "EXACT_FQ9_PROTOCOL_FAILURE"),
        _special("v075_multistage_observer_lifecycle_v1", "V075LifecycleTerminalCodeV1", "NONCERTIFICATE_CAP_CLOSED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "LIFECYCLE_CAP_IS_ATTEMPT_BUDGET_WITH_CAUSE_PRESERVED"),
        _special("v075_occurrence_failure_lifecycle_authority_v1", "V075OccurrenceFailureTerminalCodeV1", "PROTOCOL_FAILURE", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.PROTOCOL_FAILURE, "EXACT_FQ9_PROTOCOL_FAILURE"),
        _special("v075_occurrence_failure_lifecycle_authority_v1", "V075OccurrenceFailureTerminalCodeV1", "PROCESS_FAILURE", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_PROCESS_FAILURE_CODE"),
        _special("v075_occurrence_failure_lifecycle_authority_v1", "V075OccurrenceFailureTerminalCodeV1", "TIMEOUT", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_TIMEOUT_CODE"),
        _special("v075_occurrence_failure_lifecycle_authority_v1", "V075OccurrenceFailureTerminalCodeV1", "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "DIRECT_ROW_CAP_IS_ATTEMPT_BUDGET_WITH_CAUSE_PRESERVED"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_PLAN_CODE_REQUIRES_ROUTE_PROVENANCE"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "EXACT_INFEASIBILITY_CERTIFICATE", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.FULL_GROUND_EXACT_INFEASIBLE, "EXACT_GROUND_INFEASIBILITY_PROOF"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "EXACT_POLICY_RISK_FAILURE", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_POLICY_RISK_FAILURE_CODE"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "EXACT_POLICY_REGRET_FAILURE", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_POLICY_REGRET_FAILURE_CODE"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "STATISTICAL_ENVELOPE_MISS", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_STATISTICAL_ENVELOPE_MISS_CODE"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "PLANNER_SEARCH_CAP_EXHAUSTED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "PLANNER_CAP_IS_ATTEMPT_BUDGET"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "INCREMENTAL_CAP_EXHAUSTED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "INCREMENTAL_CAP_IS_ATTEMPT_BUDGET"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "ADAPTIVE_ROUND_LIMIT_REACHED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "ROUND_LIMIT_IS_ATTEMPT_BUDGET"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "NO_UNCERTAIN_PROOF_FRONTIER", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_NO_FRONTIER_CODE"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.ATTEMPT_BUDGET_EXHAUSTED, "DIRECT_ROW_CAP_IS_ATTEMPT_BUDGET_WITH_CAUSE_PRESERVED"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "INTEGRITY_FAILURE", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.INTEGRITY_FAILURE, "EXACT_FQ9_INTEGRITY_FAILURE"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "PROTOCOL_FAILURE", V075StatusDispositionV1.MAP_TO_FQ9, TerminalCode.PROTOCOL_FAILURE, "EXACT_FQ9_PROTOCOL_FAILURE"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "PROCESS_FAILURE", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_PROCESS_FAILURE_CODE"),
        _special("v075_production_occurrence_authority_v1", "V075ProductionOccurrenceTerminalCodeV1", "TIMEOUT", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_TIMEOUT_CODE"),
        _special("v075_production_occurrence_authority_v2", "V075OccurrenceTerminalCodeV2", "CONSTRUCTION_CONTROL_ONLY", V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED, None, "FQ9_HAS_NO_CONSTRUCTION_CONTROL_ONLY_CODE"),
    )
)


@lru_cache(maxsize=1)
def _discover_live_v075_status_enum_inventory_v1() -> tuple[
    tuple[str, str, tuple[tuple[str, str], ...]], ...
]:
    """Replay the explicitly scoped V075 enum inventory without imports."""

    rows: list[tuple[str, str, tuple[tuple[str, str], ...]]] = []
    package_root = Path(__file__).resolve().parent
    try:
        sources = tuple(sorted(package_root.glob("v075_*.py")))
        for source in sources:
            raw = source.read_bytes()
            tree = ast.parse(raw, filename=str(source))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef) or (
                    "Terminal" not in node.name and "Status" not in node.name
                ):
                    continue
                base_names = {
                    base.id for base in node.bases if isinstance(base, ast.Name)
                }
                if not {"str", "Enum"} <= base_names:
                    continue
                members: list[tuple[str, str]] = []
                for statement in node.body:
                    if (
                        not isinstance(statement, ast.Assign)
                        or len(statement.targets) != 1
                        or not isinstance(statement.targets[0], ast.Name)
                    ):
                        continue
                    try:
                        value = ast.literal_eval(statement.value)
                    except (TypeError, ValueError, SyntaxError, MemoryError):
                        continue
                    if type(value) is str:
                        members.append((statement.targets[0].id, value))
                if not members:
                    _fail("V075 status enum has no literal string members")
                rows.append((source.stem, node.name, tuple(members)))
    except (OSError, SyntaxError, ValueError) as error:
        raise ConstructionK7AllPathAccountingProfileV1Error(
            "V075 terminal/status source inventory could not be replayed"
        ) from error
    # File order is lexical and class/member order is source declaration order;
    # both are part of this schema's canonical array order.
    result = tuple(rows)
    if (
        len(result) != EXPECTED_V075_STATUS_ENUM_CLASS_COUNT
        or sum(len(row[2]) for row in result)
        != EXPECTED_V075_STATUS_ENUM_MEMBER_COUNT
    ):
        _fail("V075 terminal/status enum cardinality changed")
    return result


def _inventory_payload(
    inventory: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...]
) -> dict[str, Any]:
    return {
        "schema": "acfqp.construction_k7_v075_terminal_status_inventory.v1",
        "schema_version": SCHEMA_VERSION,
        "scope": "V075_MODULE_LEVEL_STR_ENUM_CLASS_NAME_CONTAINS_TERMINAL_OR_STATUS",
        "classes": [
            {
                "source_module": module,
                "enum_class": enum_class,
                "members": [
                    {"member_name": name, "member_value": value}
                    for name, value in members
                ],
            }
            for module, enum_class, members in inventory
        ],
    }


@lru_cache(maxsize=1)
def _expected_v075_status_mappings_v1() -> tuple[V075StatusMappingV1, ...]:
    live = _discover_live_v075_status_enum_inventory_v1()
    if live != _EXPECTED_V075_STATUS_ENUM_INVENTORY_V1:
        _fail("V075 terminal/status inventory changed without explicit disposition")
    observed_classes = {(module, enum_class) for module, enum_class, _ in live}
    special_classes = {
        (module, enum_class)
        for module, enum_class, _member in _SPECIAL_V075_MEMBER_POLICIES_V1
    }
    if (
        observed_classes
        != _EXPLICIT_NONTERMINAL_ENUM_CLASSES_V1 | special_classes
        or _EXPLICIT_NONTERMINAL_ENUM_CLASSES_V1 & special_classes
    ):
        _fail("V075 enum-class disposition coverage is incomplete or overlapping")

    result: list[V075StatusMappingV1] = []
    consumed_specials: set[tuple[str, str, str]] = set()
    for module, enum_class, members in live:
        class_key = (module, enum_class)
        for member_name, member_value in members:
            member_key = (module, enum_class, member_name)
            if class_key in _EXPLICIT_NONTERMINAL_ENUM_CLASSES_V1:
                disposition = V075StatusDispositionV1.NONTERMINAL
                target = None
                reason = "EXPLICIT_INTERMEDIATE_SCHEMA_OR_EVIDENCE_STATUS"
            else:
                try:
                    disposition, target, reason = (
                        _SPECIAL_V075_MEMBER_POLICIES_V1[member_key]
                    )
                except KeyError as error:
                    raise ConstructionK7AllPathAccountingProfileV1Error(
                        "V075 terminal/status member lacks an explicit disposition"
                    ) from error
                consumed_specials.add(member_key)
            target_class = None if target is None else _FQ9_CLASS_BY_CODE[target].value
            result.append(
                V075StatusMappingV1(
                    module,
                    enum_class,
                    member_name,
                    member_value,
                    disposition,
                    target_class,
                    None if target is None else target.value,
                    reason,
                )
            )
    if consumed_specials != set(_SPECIAL_V075_MEMBER_POLICIES_V1):
        _fail("V075 special disposition registry contains a stale member")
    rows = tuple(sorted(result, key=lambda row: row.source_key))
    if len(rows) != EXPECTED_V075_STATUS_ENUM_MEMBER_COUNT or len(
        {row.source_key for row in rows}
    ) != len(rows):
        _fail("V075 status mappings are incomplete or duplicated")
    return rows


def _stage_plan(
    dispositions: Mapping[
        registry_v6.ConstructionStageKindV6, StageDispositionV1
    ],
) -> tuple[StagePlanEntryV1, ...]:
    if set(dispositions) != set(_CANONICAL_STAGE_ORDER):
        _fail("terminal path must explicitly disposition every V6 stage")
    return tuple(
        StagePlanEntryV1(stage, dispositions[stage])
        for stage in _CANONICAL_STAGE_ORDER
    )


def _stages(
    *,
    preopen: StageDispositionV1,
    initial_acquisition: StageDispositionV1,
    initial_build: StageDispositionV1,
    failed_abstract: StageDispositionV1,
    open_acquisition: StageDispositionV1,
    open_checkpoint: StageDispositionV1,
    local: StageDispositionV1,
    fallback: StageDispositionV1,
    rebuild: StageDispositionV1,
    closed: StageDispositionV1,
) -> tuple[StagePlanEntryV1, ...]:
    values = (
        preopen,
        initial_acquisition,
        initial_build,
        failed_abstract,
        open_acquisition,
        open_checkpoint,
        local,
        fallback,
        rebuild,
        closed,
    )
    return _stage_plan(dict(zip(_CANONICAL_STAGE_ORDER, values, strict=True)))


def _family_rules(
    *,
    common: AccountingFamilyDispositionV1,
    local: AccountingFamilyDispositionV1,
    fallback: AccountingFamilyDispositionV1,
    rebuild: AccountingFamilyDispositionV1,
) -> tuple[AccountingFamilyRuleV1, ...]:
    values = {
        AccountingFamilyV1.COMMON_OWNER: common,
        AccountingFamilyV1.LOCAL_OWNER: local,
        AccountingFamilyV1.FALLBACK_OWNER: fallback,
        AccountingFamilyV1.REBUILD_OWNER: rebuild,
        AccountingFamilyV1.PROFILE_NATIVE_ZERO: (
            AccountingFamilyDispositionV1
            .REQUIRED_FOR_EVERY_UNREACHED_OR_INACTIVE_REQUIRED_LEAF
        ),
        AccountingFamilyV1.SHARED_RESOURCE: (
            AccountingFamilyDispositionV1
            .COMPLETE_RECEIPTS_THROUGH_TERMINAL_CUTOFF_REQUIRED
        ),
        AccountingFamilyV1.DERIVED_RECONCILIATION: (
            AccountingFamilyDispositionV1
            .EXACT_REPLAY_NO_DOUBLE_CHARGE_REQUIRED
        ),
    }
    return tuple(
        AccountingFamilyRuleV1(family, values[family])
        for family in AccountingFamilyV1
    )


_OWNER_REQUIRED = AccountingFamilyDispositionV1.OWNER_EVIDENCE_REQUIRED
_OWNER_IF_REACHED = (
    AccountingFamilyDispositionV1.OWNER_EVIDENCE_IF_REACHED_ELSE_NATIVE_ZERO
)
_ZERO = AccountingFamilyDispositionV1.NATIVE_ZERO_ATTESTATION_REQUIRED


def _evidence_role(
    role: str,
    outcome: str,
    state: EvidenceAuthorityStateV1 = (
        EvidenceAuthorityStateV1.REGISTERED_CURRENT_AUTHORITY
    ),
) -> RequiredEvidenceRoleV1:
    return RequiredEvidenceRoleV1(role, outcome, state)


def _evidence_roles(code: TerminalCode) -> tuple[RequiredEvidenceRoleV1, ...]:
    # Accounting evidence is required on every terminal, including failures.
    # The successor markers are intentional: this profile freezes the work
    # still required; it does not claim those all-path authorities exist.
    rows: dict[str, RequiredEvidenceRoleV1] = {
        "COUNTER_RECORD_SET": _evidence_role(
            "COUNTER_RECORD_SET",
            "COMPLETE_THROUGH_TERMINAL_CUTOFF",
            EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED,
        ),
        "WORK_VECTOR": _evidence_role("WORK_VECTOR", "VALID"),
        "ACTUAL_PROJECTION": _evidence_role("ACTUAL_PROJECTION", "VALID"),
        "SHARED_RESOURCE_RECEIPT_SET": _evidence_role(
            "SHARED_RESOURCE_RECEIPT_SET",
            "COMPLETE_THROUGH_TERMINAL_CUTOFF",
            EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED,
        ),
        "DERIVED_RECONCILIATION": _evidence_role(
            "DERIVED_RECONCILIATION",
            "VALID_NO_DOUBLE_CHARGE",
            EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED,
        ),
        "TERMINAL_CLASSIFICATION": _evidence_role(
            "TERMINAL_CLASSIFICATION",
            code.value,
            (
                EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED
                if code
                in {
                    TerminalCode.INTEGRITY_FAILURE,
                    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED,
                }
                else EvidenceAuthorityStateV1.REGISTERED_CURRENT_AUTHORITY
            ),
        ),
        "OCCURRENCE_TERMINAL": _evidence_role(
            "OCCURRENCE_TERMINAL",
            "VALID",
            (
                EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED
                if code
                in {
                    TerminalCode.INTEGRITY_FAILURE,
                    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED,
                }
                else EvidenceAuthorityStateV1.REGISTERED_CURRENT_AUTHORITY
            ),
        ),
    }
    specific: dict[TerminalCode, tuple[RequiredEvidenceRoleV1, ...]] = {
        TerminalCode.ABSTRACT_CERTIFIED: (
            _evidence_role("ABSTRACT_AUDIT", "PASS"),
        ),
        TerminalCode.LOCAL_GROUND_RECOVERY: (
            _evidence_role("ROUTE_UPPER", "VALID"),
            _evidence_role("ROUTE_DECISION", "LOCAL"),
            _evidence_role("LOCAL_SOLVER_RESULT", "CANDIDATE_FOUND"),
            _evidence_role("POST_AUDIT", "CERTIFIED"),
        ),
        TerminalCode.FULL_GROUND_FALLBACK: (
            _evidence_role("ROUTE_UPPER", "VALID"),
            _evidence_role("ROUTE_DECISION", "FALLBACK"),
            _evidence_role("GROUND_FALLBACK", "FEASIBLE_CERTIFIED"),
        ),
        TerminalCode.CACHED_EXACT_INFEASIBLE: (
            _evidence_role("EXACT_CACHED_INFEASIBILITY", "IDENTICAL_MATCH"),
            _evidence_role(
                "DURABLE_EXACT_PROOF_PAYLOAD",
                "IDENTITY_BOUND_COMPLETE",
                EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED,
            ),
        ),
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: (
            _evidence_role("ROUTE_UPPER", "VALID"),
            _evidence_role("ROUTE_DECISION", "FALLBACK"),
            _evidence_role("GROUND_FALLBACK", "INFEASIBLE_CERTIFIED"),
        ),
        TerminalCode.INTEGRITY_FAILURE: (
            _evidence_role(
                "INTEGRITY_FAILURE_EVIDENCE",
                "INTEGRITY_FAILURE",
                EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED,
            ),
        ),
        TerminalCode.PROTOCOL_FAILURE: (
            _evidence_role("PROTOCOL_ACCESS", "PROTOCOL_FAILURE"),
        ),
        TerminalCode.REBUILD_REQUIRED: (
            _evidence_role("ROUTE_UPPER", "VALID"),
            _evidence_role("ROUTE_DECISION", "LOCAL"),
            _evidence_role("LOCAL_SOLVER_RESULT", "CANDIDATE_FOUND"),
            _evidence_role("POST_AUDIT", "FAILED"),
        ),
        TerminalCode.FALLBACK_CAP_EXHAUSTED: (
            _evidence_role("ROUTE_UPPER", "VALID"),
            _evidence_role("ROUTE_DECISION", "FALLBACK"),
            _evidence_role("GROUND_FALLBACK", "CAP_EXHAUSTED"),
        ),
        TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: (
            _evidence_role(
                "TRUSTED_BUDGET_REPLAY",
                "ATTEMPT_BUDGET_EXHAUSTED",
                EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED,
            ),
        ),
    }
    for row in specific[code]:
        if row.role in rows:
            _fail("terminal-specific evidence role duplicates a common role")
        rows[row.role] = row
    return tuple(sorted(rows.values()))


@lru_cache(maxsize=1)
def _expected_terminal_path_rules_v1() -> tuple[TerminalPathRuleV1, ...]:
    required = StageDispositionV1.REQUIRED_ONCE
    required_many = StageDispositionV1.REQUIRED_AT_LEAST_ONCE
    optional = StageDispositionV1.OPTIONAL_ONCE
    optional_many = StageDispositionV1.OPTIONAL_REPEATABLE
    prefix = StageDispositionV1.PREFIX_DEPENDENT_THROUGH_FAILURE_CUTOFF
    forbidden = StageDispositionV1.FORBIDDEN

    rules = {
        TerminalCode.ABSTRACT_CERTIFIED: TerminalPathRuleV1(
            TerminalClass.PLAN_CERTIFICATE,
            TerminalCode.ABSTRACT_CERTIFIED,
            (RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,),
            _stages(
                preopen=required,
                initial_acquisition=required,
                initial_build=required,
                failed_abstract=optional_many,
                open_acquisition=optional_many,
                open_checkpoint=optional_many,
                local=forbidden,
                fallback=forbidden,
                rebuild=forbidden,
                closed=required,
            ),
            _family_rules(common=_OWNER_REQUIRED, local=_ZERO, fallback=_ZERO, rebuild=_ZERO),
            _evidence_roles(TerminalCode.ABSTRACT_CERTIFIED),
            RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE,
        ),
        TerminalCode.LOCAL_GROUND_RECOVERY: TerminalPathRuleV1(
            TerminalClass.PLAN_CERTIFICATE,
            TerminalCode.LOCAL_GROUND_RECOVERY,
            (RouteKindEnum.ABSTRACT_FAILED_PREFIX, RouteKindEnum.LOCAL_ATTEMPT),
            _stages(
                preopen=required,
                initial_acquisition=required,
                initial_build=required,
                failed_abstract=required_many,
                open_acquisition=optional_many,
                open_checkpoint=optional_many,
                local=required_many,
                fallback=forbidden,
                rebuild=forbidden,
                closed=required,
            ),
            _family_rules(common=_OWNER_REQUIRED, local=_OWNER_REQUIRED, fallback=_ZERO, rebuild=_ZERO),
            _evidence_roles(TerminalCode.LOCAL_GROUND_RECOVERY),
            RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE,
        ),
        TerminalCode.FULL_GROUND_FALLBACK: TerminalPathRuleV1(
            TerminalClass.PLAN_CERTIFICATE,
            TerminalCode.FULL_GROUND_FALLBACK,
            (
                RouteKindEnum.ABSTRACT_FAILED_PREFIX,
                RouteKindEnum.LOCAL_ATTEMPT,
                RouteKindEnum.DIRECT_FALLBACK,
            ),
            _stages(
                preopen=required,
                initial_acquisition=required,
                initial_build=required,
                failed_abstract=required_many,
                open_acquisition=optional_many,
                open_checkpoint=optional_many,
                local=optional_many,
                fallback=required,
                rebuild=forbidden,
                closed=required,
            ),
            _family_rules(common=_OWNER_REQUIRED, local=_OWNER_IF_REACHED, fallback=_OWNER_REQUIRED, rebuild=_ZERO),
            _evidence_roles(TerminalCode.FULL_GROUND_FALLBACK),
            RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE,
        ),
        TerminalCode.CACHED_EXACT_INFEASIBLE: TerminalPathRuleV1(
            TerminalClass.INFEASIBILITY_CERTIFICATE,
            TerminalCode.CACHED_EXACT_INFEASIBLE,
            (RouteKindEnum.ABSTRACT_FAILED_PREFIX,),
            _stages(
                preopen=required,
                initial_acquisition=optional,
                initial_build=optional,
                failed_abstract=forbidden,
                open_acquisition=forbidden,
                open_checkpoint=forbidden,
                local=forbidden,
                fallback=forbidden,
                rebuild=forbidden,
                closed=required,
            ),
            _family_rules(common=_OWNER_REQUIRED, local=_ZERO, fallback=_ZERO, rebuild=_ZERO),
            _evidence_roles(TerminalCode.CACHED_EXACT_INFEASIBLE),
            RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE,
        ),
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: TerminalPathRuleV1(
            TerminalClass.INFEASIBILITY_CERTIFICATE,
            TerminalCode.FULL_GROUND_EXACT_INFEASIBLE,
            (
                RouteKindEnum.ABSTRACT_FAILED_PREFIX,
                RouteKindEnum.LOCAL_ATTEMPT,
                RouteKindEnum.DIRECT_FALLBACK,
            ),
            _stages(
                preopen=required,
                initial_acquisition=required,
                initial_build=required,
                failed_abstract=required_many,
                open_acquisition=optional_many,
                open_checkpoint=optional_many,
                local=optional_many,
                fallback=required,
                rebuild=forbidden,
                closed=required,
            ),
            _family_rules(common=_OWNER_REQUIRED, local=_OWNER_IF_REACHED, fallback=_OWNER_REQUIRED, rebuild=_ZERO),
            _evidence_roles(TerminalCode.FULL_GROUND_EXACT_INFEASIBLE),
            RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE,
        ),
        TerminalCode.INTEGRITY_FAILURE: TerminalPathRuleV1(
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
            TerminalCode.INTEGRITY_FAILURE,
            tuple(RouteKindEnum),
            _stages(
                preopen=prefix,
                initial_acquisition=prefix,
                initial_build=prefix,
                failed_abstract=prefix,
                open_acquisition=prefix,
                open_checkpoint=prefix,
                local=prefix,
                fallback=prefix,
                rebuild=prefix,
                closed=required,
            ),
            _family_rules(common=_OWNER_IF_REACHED, local=_OWNER_IF_REACHED, fallback=_OWNER_IF_REACHED, rebuild=_OWNER_IF_REACHED),
            _evidence_roles(TerminalCode.INTEGRITY_FAILURE),
            RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE,
        ),
        TerminalCode.PROTOCOL_FAILURE: TerminalPathRuleV1(
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
            TerminalCode.PROTOCOL_FAILURE,
            tuple(RouteKindEnum),
            _stages(
                preopen=prefix,
                initial_acquisition=prefix,
                initial_build=prefix,
                failed_abstract=prefix,
                open_acquisition=prefix,
                open_checkpoint=prefix,
                local=prefix,
                fallback=prefix,
                rebuild=prefix,
                closed=required,
            ),
            _family_rules(common=_OWNER_IF_REACHED, local=_OWNER_IF_REACHED, fallback=_OWNER_IF_REACHED, rebuild=_OWNER_IF_REACHED),
            _evidence_roles(TerminalCode.PROTOCOL_FAILURE),
            RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE,
        ),
        TerminalCode.REBUILD_REQUIRED: TerminalPathRuleV1(
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
            TerminalCode.REBUILD_REQUIRED,
            (RouteKindEnum.ABSTRACT_FAILED_PREFIX, RouteKindEnum.LOCAL_ATTEMPT),
            _stages(
                preopen=required,
                initial_acquisition=required,
                initial_build=required,
                failed_abstract=required_many,
                open_acquisition=optional_many,
                open_checkpoint=optional_many,
                local=required_many,
                fallback=forbidden,
                rebuild=forbidden,
                closed=required,
            ),
            _family_rules(common=_OWNER_REQUIRED, local=_OWNER_REQUIRED, fallback=_ZERO, rebuild=_ZERO),
            _evidence_roles(TerminalCode.REBUILD_REQUIRED),
            RetryDispositionV1.REBUILD_POLICY_CONTROLLED,
        ),
        TerminalCode.FALLBACK_CAP_EXHAUSTED: TerminalPathRuleV1(
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
            TerminalCode.FALLBACK_CAP_EXHAUSTED,
            (
                RouteKindEnum.ABSTRACT_FAILED_PREFIX,
                RouteKindEnum.LOCAL_ATTEMPT,
                RouteKindEnum.DIRECT_FALLBACK,
            ),
            _stages(
                preopen=required,
                initial_acquisition=required,
                initial_build=required,
                failed_abstract=required_many,
                open_acquisition=optional_many,
                open_checkpoint=optional_many,
                local=optional_many,
                fallback=required,
                rebuild=forbidden,
                closed=required,
            ),
            _family_rules(common=_OWNER_REQUIRED, local=_OWNER_IF_REACHED, fallback=_OWNER_REQUIRED, rebuild=_ZERO),
            _evidence_roles(TerminalCode.FALLBACK_CAP_EXHAUSTED),
            RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE,
        ),
        TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: TerminalPathRuleV1(
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
            TerminalCode.ATTEMPT_BUDGET_EXHAUSTED,
            (RouteKindEnum.ABSTRACT_FAILED_PREFIX, RouteKindEnum.LOCAL_ATTEMPT),
            _stages(
                preopen=required,
                initial_acquisition=required,
                initial_build=required,
                failed_abstract=required_many,
                open_acquisition=optional_many,
                open_checkpoint=optional_many,
                local=optional_many,
                fallback=forbidden,
                rebuild=forbidden,
                closed=required,
            ),
            _family_rules(common=_OWNER_REQUIRED, local=_OWNER_IF_REACHED, fallback=_ZERO, rebuild=_ZERO),
            _evidence_roles(TerminalCode.ATTEMPT_BUDGET_EXHAUSTED),
            RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE,
        ),
    }
    if set(rules) != set(TerminalCode):
        _fail("FQ9 terminal path profile is incomplete")
    return tuple(rules[code] for code in TerminalCode)


def _profile_payload_v1(
    *,
    counter_registry_id: str,
    stage_profile_id: str,
    comparison_profile_id: str,
    actual_projection_profile_id: str,
    v075_terminal_status_inventory_id: str,
    terminal_path_rules: tuple[TerminalPathRuleV1, ...],
    attempt_rebuild_policy: AttemptRebuildPolicyV1,
    v075_status_mappings: tuple[V075StatusMappingV1, ...],
) -> dict[str, Any]:
    counts = {
        disposition.value: sum(
            row.disposition is disposition for row in v075_status_mappings
        )
        for disposition in V075StatusDispositionV1
    }
    return {
        "schema": "acfqp.construction_k7_all_path_accounting_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "counter_registry_id": counter_registry_id,
        "stage_profile_id": stage_profile_id,
        "comparison_profile_id": comparison_profile_id,
        "actual_projection_profile_id": actual_projection_profile_id,
        "v075_terminal_status_inventory_id": v075_terminal_status_inventory_id,
        "fq9_terminal_classes": [item.value for item in TerminalClass],
        "fq9_terminal_codes": [item.value for item in TerminalCode],
        "route_kinds": [item.value for item in RouteKindEnum],
        "stage_kinds": [item.value for item in _CANONICAL_STAGE_ORDER],
        "accounting_families": [item.value for item in AccountingFamilyV1],
        "terminal_path_rules": [item.to_document() for item in terminal_path_rules],
        "attempt_rebuild_policy": attempt_rebuild_policy.to_document(),
        "v075_inventory_scope": (
            "V075_MODULE_LEVEL_STR_ENUM_CLASS_NAME_CONTAINS_TERMINAL_OR_STATUS"
        ),
        "v075_status_enum_class_count": EXPECTED_V075_STATUS_ENUM_CLASS_COUNT,
        "v075_status_enum_member_count": EXPECTED_V075_STATUS_ENUM_MEMBER_COUNT,
        "v075_status_disposition_counts": counts,
        "v075_status_mappings": [
            item.to_document() for item in v075_status_mappings
        ],
        "new_v075_status_requires_explicit_profile_revision": True,
        "source_status_string_alone_never_authorizes_terminal": True,
        "specific_v075_cause_must_be_preserved_after_fq9_mapping": True,
        "profile_only": True,
        "terminal_execution_performed": False,
        "counter_records_issued": 0,
        "work_vectors_issued": 0,
        "comparison_vectors_issued": 0,
        "all_path_native_accounting_complete": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_n_break_even": None,
        "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
        "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
    }


@dataclass(frozen=True, slots=True)
class ConstructionK7AllPathAccountingProfileV1:
    _issuer: object = field(repr=False, compare=False)
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    v075_terminal_status_inventory_id: str
    terminal_path_rules: tuple[TerminalPathRuleV1, ...]
    attempt_rebuild_policy: AttemptRebuildPolicyV1
    v075_status_mappings: tuple[V075StatusMappingV1, ...]
    official_execution_allowed: bool = False
    all_path_native_accounting_complete: bool = False
    terminal_execution_performed: bool = False
    counter_records_issued: int = 0
    work_vectors_issued: int = 0
    comparison_vectors_issued: int = 0
    official_scalar_cost: None = None
    official_n_break_even: None = None
    counter_completeness_gate_status: str = COUNTER_COMPLETENESS_GATE_STATUS
    workload_economics_gate_status: str = WORKLOAD_ECONOMICS_GATE_STATUS

    def __post_init__(self) -> None:
        if self._issuer is not _PROFILE_ISSUER:
            _fail("all-path accounting profile must be issued by its freezer")
        for field_name in (
            "counter_registry_id",
            "stage_profile_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "v075_terminal_status_inventory_id",
        ):
            _cid(getattr(self, field_name), field_name)
        rules = tuple(self.terminal_path_rules)
        mappings = tuple(self.v075_status_mappings)
        object.__setattr__(self, "terminal_path_rules", rules)
        object.__setattr__(self, "v075_status_mappings", mappings)
        if type(self.attempt_rebuild_policy) is not AttemptRebuildPolicyV1:
            _fail("all-path profile lacks the exact attempt/rebuild policy")

        registry = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        projection = registry_v6.official_actual_projection_profile_v6(
            registry, comparison
        )
        inventory = _discover_live_v075_status_enum_inventory_v1()
        inventory_id = _local_id(
            V075_TERMINAL_STATUS_INVENTORY_V1_DOMAIN,
            _inventory_payload(inventory),
        )
        if (
            self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage.stage_profile_id
            or self.comparison_profile_id != comparison.comparison_profile_id
            or self.actual_projection_profile_id
            != projection.actual_projection_profile_id
            or self.v075_terminal_status_inventory_id != inventory_id
            or rules != _expected_terminal_path_rules_v1()
            or mappings != _expected_v075_status_mappings_v1()
            or len(rules) != EXPECTED_FQ9_TERMINAL_CODE_COUNT
            or {row.terminal_code for row in rules} != set(TerminalCode)
            or {row.terminal_class for row in rules} != set(TerminalClass)
            or len(mappings) != EXPECTED_V075_STATUS_ENUM_MEMBER_COUNT
            or len({row.source_key for row in mappings}) != len(mappings)
        ):
            _fail("all-path accounting profile differs from Contract 2.0.33")
        if (
            self.official_execution_allowed is not False
            or self.all_path_native_accounting_complete is not False
            or self.terminal_execution_performed is not False
            or self.counter_records_issued != 0
            or self.work_vectors_issued != 0
            or self.comparison_vectors_issued != 0
            or self.official_scalar_cost is not None
            or self.official_n_break_even is not None
            or self.counter_completeness_gate_status
            != COUNTER_COMPLETENESS_GATE_STATUS
            or self.workload_economics_gate_status
            != WORKLOAD_ECONOMICS_GATE_STATUS
        ):
            _fail("schema-only all-path profile attempted to claim execution or a Gate")

    @property
    def terminal_path_rule_by_code(self) -> dict[TerminalCode, TerminalPathRuleV1]:
        return {row.terminal_code: row for row in self.terminal_path_rules}

    @property
    def v075_status_mapping_by_key(self) -> dict[str, V075StatusMappingV1]:
        return {row.source_key: row for row in self.v075_status_mappings}

    def _payload(self) -> dict[str, Any]:
        return _profile_payload_v1(
            counter_registry_id=self.counter_registry_id,
            stage_profile_id=self.stage_profile_id,
            comparison_profile_id=self.comparison_profile_id,
            actual_projection_profile_id=self.actual_projection_profile_id,
            v075_terminal_status_inventory_id=(
                self.v075_terminal_status_inventory_id
            ),
            terminal_path_rules=self.terminal_path_rules,
            attempt_rebuild_policy=self.attempt_rebuild_policy,
            v075_status_mappings=self.v075_status_mappings,
        )

    @property
    def profile_id(self) -> str:
        return _local_id(ALL_PATH_ACCOUNTING_PROFILE_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


@lru_cache(maxsize=1)
def freeze_construction_k7_all_path_accounting_profile_v1(
) -> ConstructionK7AllPathAccountingProfileV1:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    projection = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    inventory = _discover_live_v075_status_enum_inventory_v1()
    if inventory != _EXPECTED_V075_STATUS_ENUM_INVENTORY_V1:
        _fail("V075 terminal/status inventory changed before profile freeze")
    return ConstructionK7AllPathAccountingProfileV1(
        _PROFILE_ISSUER,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        projection.actual_projection_profile_id,
        _local_id(
            V075_TERMINAL_STATUS_INVENTORY_V1_DOMAIN,
            _inventory_payload(inventory),
        ),
        _expected_terminal_path_rules_v1(),
        AttemptRebuildPolicyV1(),
        _expected_v075_status_mappings_v1(),
    )


@dataclass(frozen=True, slots=True)
class ConstructionK7AllPathAccountingProfileReplayV1:
    _issuer: object = field(repr=False, compare=False)
    profile_id: str
    v075_terminal_status_inventory_id: str
    fq9_terminal_class_count: int
    fq9_terminal_code_count: int
    route_kind_count: int
    stage_count: int
    accounting_family_count: int
    v075_status_enum_class_count: int
    v075_status_enum_member_count: int
    mapped_to_fq9_count: int
    profile_extension_required_count: int
    nonterminal_count: int
    explicit_disposition_coverage_complete: bool = True
    fq9_taxonomy_complete: bool = True
    stage_and_route_accounting_recipes_complete: bool = True
    attempt_rebuild_policy_replayed: bool = True
    execution_performed: bool = False
    gate_unlocked: bool = False

    def __post_init__(self) -> None:
        if self._issuer is not _REPLAY_ISSUER:
            _fail("all-path profile replay must be issued by its verifier")
        _cid(self.profile_id, "profile_id")
        _cid(
            self.v075_terminal_status_inventory_id,
            "v075_terminal_status_inventory_id",
        )
        counts = (
            self.fq9_terminal_class_count,
            self.fq9_terminal_code_count,
            self.route_kind_count,
            self.stage_count,
            self.accounting_family_count,
            self.v075_status_enum_class_count,
            self.v075_status_enum_member_count,
        )
        if counts != (
            EXPECTED_FQ9_TERMINAL_CLASS_COUNT,
            EXPECTED_FQ9_TERMINAL_CODE_COUNT,
            EXPECTED_ROUTE_KIND_COUNT,
            EXPECTED_STAGE_COUNT,
            EXPECTED_ACCOUNTING_FAMILY_COUNT,
            EXPECTED_V075_STATUS_ENUM_CLASS_COUNT,
            EXPECTED_V075_STATUS_ENUM_MEMBER_COUNT,
        ):
            _fail("all-path replay cardinalities changed")
        if (
            self.mapped_to_fq9_count
            + self.profile_extension_required_count
            + self.nonterminal_count
            != EXPECTED_V075_STATUS_ENUM_MEMBER_COUNT
            or min(
                self.mapped_to_fq9_count,
                self.profile_extension_required_count,
                self.nonterminal_count,
            )
            < 1
            or self.explicit_disposition_coverage_complete is not True
            or self.fq9_taxonomy_complete is not True
            or self.stage_and_route_accounting_recipes_complete is not True
            or self.attempt_rebuild_policy_replayed is not True
            or self.execution_performed is not False
            or self.gate_unlocked is not False
        ):
            _fail("all-path replay made an incomplete or execution claim")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_all_path_accounting_profile_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "v075_terminal_status_inventory_id": (
                self.v075_terminal_status_inventory_id
            ),
            "fq9_terminal_class_count": self.fq9_terminal_class_count,
            "fq9_terminal_code_count": self.fq9_terminal_code_count,
            "route_kind_count": self.route_kind_count,
            "stage_count": self.stage_count,
            "accounting_family_count": self.accounting_family_count,
            "v075_status_enum_class_count": self.v075_status_enum_class_count,
            "v075_status_enum_member_count": self.v075_status_enum_member_count,
            "mapped_to_fq9_count": self.mapped_to_fq9_count,
            "profile_extension_required_count": (
                self.profile_extension_required_count
            ),
            "nonterminal_count": self.nonterminal_count,
            "explicit_disposition_coverage_complete": True,
            "fq9_taxonomy_complete": True,
            "stage_and_route_accounting_recipes_complete": True,
            "attempt_rebuild_policy_replayed": True,
            "execution_performed": False,
            "gate_unlocked": False,
            "counter_completeness_gate_status": (
                COUNTER_COMPLETENESS_GATE_STATUS
            ),
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        }

    @property
    def replay_id(self) -> str:
        return _local_id(
            ALL_PATH_ACCOUNTING_PROFILE_REPLAY_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "replay_id": self.replay_id}


def verify_construction_k7_all_path_accounting_profile_document_v1(
    document: Mapping[str, Any],
) -> ConstructionK7AllPathAccountingProfileReplayV1:
    """Independently replay a portable profile document, not a live route."""

    if type(document) is not dict:
        _fail("all-path profile document must be one exact dictionary")
    live_inventory = _discover_live_v075_status_enum_inventory_v1()
    if live_inventory != _EXPECTED_V075_STATUS_ENUM_INVENTORY_V1:
        _fail("live V075 terminal/status inventory differs from the profile")
    inventory_id = _local_id(
        V075_TERMINAL_STATUS_INVENTORY_V1_DOMAIN,
        _inventory_payload(live_inventory),
    )
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    projection = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    rules = _expected_terminal_path_rules_v1()
    mappings = _expected_v075_status_mappings_v1()
    expected_payload = _profile_payload_v1(
        counter_registry_id=registry.registry_id,
        stage_profile_id=stage.stage_profile_id,
        comparison_profile_id=comparison.comparison_profile_id,
        actual_projection_profile_id=projection.actual_projection_profile_id,
        v075_terminal_status_inventory_id=inventory_id,
        terminal_path_rules=rules,
        attempt_rebuild_policy=AttemptRebuildPolicyV1(),
        v075_status_mappings=mappings,
    )
    expected_id = _local_id(
        ALL_PATH_ACCOUNTING_PROFILE_V1_DOMAIN, expected_payload
    )
    expected_document = {**expected_payload, "profile_id": expected_id}
    if document != expected_document:
        _fail("all-path profile document differs from exact schema replay")
    claimed_id = document["profile_id"]
    if claimed_id != expected_id:
        _fail("all-path profile content ID does not replay")

    counts = {
        disposition: sum(row.disposition is disposition for row in mappings)
        for disposition in V075StatusDispositionV1
    }
    return ConstructionK7AllPathAccountingProfileReplayV1(
        _REPLAY_ISSUER,
        claimed_id,
        inventory_id,
        len(TerminalClass),
        len(TerminalCode),
        len(RouteKindEnum),
        len(_CANONICAL_STAGE_ORDER),
        len(AccountingFamilyV1),
        len(live_inventory),
        sum(len(row[2]) for row in live_inventory),
        counts[V075StatusDispositionV1.MAP_TO_FQ9],
        counts[V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED],
        counts[V075StatusDispositionV1.NONTERMINAL],
    )


__all__ = [
    "AccountingFamilyDispositionV1",
    "AccountingFamilyRuleV1",
    "AccountingFamilyV1",
    "ALL_PATH_ACCOUNTING_PROFILE_REPLAY_V1_DOMAIN",
    "ALL_PATH_ACCOUNTING_PROFILE_V1_DOMAIN",
    "AttemptRebuildPolicyV1",
    "ConstructionK7AllPathAccountingProfileReplayV1",
    "ConstructionK7AllPathAccountingProfileV1",
    "ConstructionK7AllPathAccountingProfileV1Error",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "EvidenceAuthorityStateV1",
    "EXPECTED_ACCOUNTING_FAMILY_COUNT",
    "EXPECTED_FQ9_TERMINAL_CLASS_COUNT",
    "EXPECTED_FQ9_TERMINAL_CODE_COUNT",
    "EXPECTED_ROUTE_KIND_COUNT",
    "EXPECTED_STAGE_COUNT",
    "EXPECTED_V075_STATUS_ENUM_CLASS_COUNT",
    "EXPECTED_V075_STATUS_ENUM_MEMBER_COUNT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RequiredEvidenceRoleV1",
    "RetryDispositionV1",
    "SCHEMA_VERSION",
    "StageDispositionV1",
    "StagePlanEntryV1",
    "TerminalPathRuleV1",
    "V075StatusDispositionV1",
    "V075StatusMappingV1",
    "V075_TERMINAL_STATUS_INVENTORY_V1_DOMAIN",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "freeze_construction_k7_all_path_accounting_profile_v1",
    "verify_construction_k7_all_path_accounting_profile_document_v1",
]
