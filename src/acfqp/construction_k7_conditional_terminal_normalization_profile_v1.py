"""Conditional normalization for the 14 unresolved V075 status rows.

Contract 2.0.40 consumes the exact Contract-2.0.33 all-path profile and
removes the semantic ambiguity from its fourteen
``PROFILE_EXTENSION_REQUIRED`` rows.  This is deliberately a normalization
profile, not a terminal authority:

* a successful total-lift status needs retained route provenance before one
  of the three FQ9 plan codes can be selected;
* risk/regret/statistical misses, missing frontiers, policy aborts and
  construction controls remain route-continuation statuses;
* process failure needs retained process *and* protocol evidence;
* timeout is a cap terminal only when a preregistered cap and trusted replay
  identify the cap scope, and otherwise normalizes to protocol failure; and
* a generic noncertificate needs a typed cause-evidence binding.

Even when a conditional target is selected, the result explicitly states
that no live terminal artifact was issued.  A downstream semantic authority
must verify the referenced evidence and mint the actual terminal.

All five content domains are imported from the central Phase-3E registry and
asserted registered before any identity can be issued.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import RouteKindEnum
from acfqp import construction_k7_all_path_accounting_profile_v1 as all_path_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_RULE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    parse_content_id,
)
from acfqp.routing_v1 import TerminalClass, TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.40"
PROFILE_KEY = "construction_k7_conditional_terminal_normalization_profile_v1"

EXPECTED_EXTENSION_ROW_COUNT = 14
EXPECTED_PLAN_ROUTE_ROW_COUNT = 2
EXPECTED_CONTINUATION_ROW_COUNT = 7
EXPECTED_PROCESS_FAILURE_ROW_COUNT = 2
EXPECTED_TIMEOUT_ROW_COUNT = 2
EXPECTED_GENERIC_NONCERTIFICATE_ROW_COUNT = 1

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

PROFILE_DOMAIN = (
    CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_PROFILE_V1_DOMAIN
)
RULE_DOMAIN = CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_RULE_V1_DOMAIN
EVIDENCE_DOMAIN = (
    CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_EVIDENCE_V1_DOMAIN
)
RESULT_DOMAIN = (
    CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_RESULT_V1_DOMAIN
)
REPLAY_DOMAIN = (
    CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_REPLAY_V1_DOMAIN
)

_REGISTERED_DOMAINS = frozenset(
    {PROFILE_DOMAIN, RULE_DOMAIN, EVIDENCE_DOMAIN, RESULT_DOMAIN, REPLAY_DOMAIN}
)
if len(_REGISTERED_DOMAINS) != 5 or not _REGISTERED_DOMAINS.issubset(  # pragma: no cover
    PHASE3E_DOMAIN_TAGS
):
    raise RuntimeError(
        "K7 conditional-normalization domains must be centrally registered"
    )
_PROFILE_ISSUER = object()
_RESULT_ISSUER = object()
_REPLAY_ISSUER = object()


class ConstructionK7ConditionalTerminalNormalizationProfileV1Error(ValueError):
    """A source row, condition, target, or portable document is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ConditionalTerminalNormalizationProfileV1Error(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in _REGISTERED_DOMAINS:
        _fail("conditional-normalization profile used an unregistered domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ConditionalTerminalNormalizationProfileV1Error(
            f"{field_name} must be one exact content ID"
        ) from error


def _exact_fields(
    document: Mapping[str, Any], expected: set[str], context: str
) -> None:
    if type(document) is not dict or set(document) != expected:
        _fail(f"{context} field set differs from the exact schema")


class NormalizationFamilyV1(str, Enum):
    PLAN_ROUTE_PROVENANCE_REQUIRED = "PLAN_ROUTE_PROVENANCE_REQUIRED"
    ROUTE_CONTINUATION_NONTERMINAL = "ROUTE_CONTINUATION_NONTERMINAL"
    PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED = (
        "PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED"
    )
    TIMEOUT_CAP_REPLAY_OR_PROTOCOL_FAILURE = (
        "TIMEOUT_CAP_REPLAY_OR_PROTOCOL_FAILURE"
    )
    TYPED_NONCERTIFICATE_CAUSE_REQUIRED = (
        "TYPED_NONCERTIFICATE_CAUSE_REQUIRED"
    )


class NormalizationEvidenceKindV1(str, Enum):
    NONE = "NONE"
    PLAN_ROUTE_PROVENANCE = "PLAN_ROUTE_PROVENANCE"
    PROCESS_AND_PROTOCOL = "PROCESS_AND_PROTOCOL"
    PREREGISTERED_CAP_AND_TRUSTED_REPLAY = (
        "PREREGISTERED_CAP_AND_TRUSTED_REPLAY"
    )
    TYPED_NONCERTIFICATE_CAUSE = "TYPED_NONCERTIFICATE_CAUSE"


class TimeoutCapScopeV1(str, Enum):
    ATTEMPT_BUDGET = "ATTEMPT_BUDGET"
    DIRECT_FALLBACK = "DIRECT_FALLBACK"


class ConditionalNormalizationOutcomeV1(str, Enum):
    ROUTE_CONTINUATION_NONTERMINAL = "ROUTE_CONTINUATION_NONTERMINAL"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    FQ9_TARGET_SELECTED_REQUIRES_TERMINAL_AUTHORITY = (
        "FQ9_TARGET_SELECTED_REQUIRES_TERMINAL_AUTHORITY"
    )


_FQ9_CLASS_BY_CODE = {
    TerminalCode.ABSTRACT_CERTIFIED: TerminalClass.PLAN_CERTIFICATE,
    TerminalCode.LOCAL_GROUND_RECOVERY: TerminalClass.PLAN_CERTIFICATE,
    TerminalCode.FULL_GROUND_FALLBACK: TerminalClass.PLAN_CERTIFICATE,
    TerminalCode.CACHED_EXACT_INFEASIBLE: TerminalClass.INFEASIBILITY_CERTIFICATE,
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

_PLAN_CODE_BY_ROUTE = {
    RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE: TerminalCode.ABSTRACT_CERTIFIED,
    RouteKindEnum.LOCAL_ATTEMPT: TerminalCode.LOCAL_GROUND_RECOVERY,
    RouteKindEnum.DIRECT_FALLBACK: TerminalCode.FULL_GROUND_FALLBACK,
}

_GENERIC_NONCERTIFICATE_CODES = frozenset(
    {
        TerminalCode.INTEGRITY_FAILURE,
        TerminalCode.PROTOCOL_FAILURE,
        TerminalCode.REBUILD_REQUIRED,
        TerminalCode.FALLBACK_CAP_EXHAUSTED,
        TerminalCode.ATTEMPT_BUDGET_EXHAUSTED,
    }
)


@dataclass(frozen=True, slots=True, order=True)
class ConditionalNormalizationRuleV1:
    source_module: str
    enum_class: str
    member_name: str
    member_value: str
    source_mapping_reason_code: str
    normalization_family: NormalizationFamilyV1
    allowed_evidence_kinds: tuple[NormalizationEvidenceKindV1, ...]
    allowed_fq9_terminal_codes: tuple[TerminalCode, ...]
    source_disposition: str = (
        all_path_v1.V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED.value
    )
    source_status_alone_authorizes_terminal: bool = False

    def __post_init__(self) -> None:
        text_values = (
            self.source_module,
            self.enum_class,
            self.member_name,
            self.member_value,
            self.source_mapping_reason_code,
        )
        if not all(type(value) is str and value for value in text_values):
            _fail("conditional-normalization source binding is incomplete")
        try:
            family = NormalizationFamilyV1(self.normalization_family)
            evidence = tuple(
                NormalizationEvidenceKindV1(value)
                for value in self.allowed_evidence_kinds
            )
            targets = tuple(TerminalCode(value) for value in self.allowed_fq9_terminal_codes)
        except (TypeError, ValueError) as error:
            raise ConstructionK7ConditionalTerminalNormalizationProfileV1Error(
                "conditional-normalization family/evidence/target is invalid"
            ) from error
        object.__setattr__(self, "normalization_family", family)
        object.__setattr__(self, "allowed_evidence_kinds", evidence)
        object.__setattr__(self, "allowed_fq9_terminal_codes", targets)
        if (
            self.source_disposition
            != all_path_v1.V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED.value
            or self.source_status_alone_authorizes_terminal is not False
            or not evidence
            or tuple(sorted(evidence, key=lambda item: item.value)) != evidence
            or len(set(evidence)) != len(evidence)
            or tuple(sorted(targets, key=lambda item: item.value)) != targets
            or len(set(targets)) != len(targets)
        ):
            _fail("conditional-normalization rule is noncanonical")
        expected_shape = _family_shape_v1(family)
        if evidence != expected_shape[0] or targets != expected_shape[1]:
            _fail("conditional-normalization rule violates its family semantics")

    @property
    def source_key(self) -> str:
        return f"{self.source_module}:{self.enum_class}:{self.member_name}"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_conditional_terminal_normalization_rule.v1",
            "schema_version": SCHEMA_VERSION,
            "source_module": self.source_module,
            "enum_class": self.enum_class,
            "member_name": self.member_name,
            "member_value": self.member_value,
            "source_mapping_reason_code": self.source_mapping_reason_code,
            "source_disposition": self.source_disposition,
            "normalization_family": self.normalization_family.value,
            "allowed_evidence_kinds": [item.value for item in self.allowed_evidence_kinds],
            "allowed_fq9_terminal_codes": [
                item.value for item in self.allowed_fq9_terminal_codes
            ],
            "source_status_alone_authorizes_terminal": False,
        }

    @property
    def rule_id(self) -> str:
        return _content_id(RULE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "rule_id": self.rule_id}


def _family_shape_v1(
    family: NormalizationFamilyV1,
) -> tuple[tuple[NormalizationEvidenceKindV1, ...], tuple[TerminalCode, ...]]:
    if family is NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED:
        return (
            tuple(
                sorted(
                    {
                        NormalizationEvidenceKindV1.NONE,
                        NormalizationEvidenceKindV1.PLAN_ROUTE_PROVENANCE,
                    },
                    key=lambda item: item.value,
                )
            ),
            tuple(sorted(_PLAN_CODE_BY_ROUTE.values(), key=lambda item: item.value)),
        )
    if family is NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL:
        return ((NormalizationEvidenceKindV1.NONE,), ())
    if family is NormalizationFamilyV1.PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED:
        return (
            tuple(
                sorted(
                    {
                        NormalizationEvidenceKindV1.NONE,
                        NormalizationEvidenceKindV1.PROCESS_AND_PROTOCOL,
                    },
                    key=lambda item: item.value,
                )
            ),
            (TerminalCode.PROTOCOL_FAILURE,),
        )
    if family is NormalizationFamilyV1.TIMEOUT_CAP_REPLAY_OR_PROTOCOL_FAILURE:
        return (
            tuple(
                sorted(
                    {
                        NormalizationEvidenceKindV1.NONE,
                        NormalizationEvidenceKindV1.PREREGISTERED_CAP_AND_TRUSTED_REPLAY,
                    },
                    key=lambda item: item.value,
                )
            ),
            tuple(
                sorted(
                    {
                        TerminalCode.PROTOCOL_FAILURE,
                        TerminalCode.ATTEMPT_BUDGET_EXHAUSTED,
                        TerminalCode.FALLBACK_CAP_EXHAUSTED,
                    },
                    key=lambda item: item.value,
                )
            ),
        )
    if family is NormalizationFamilyV1.TYPED_NONCERTIFICATE_CAUSE_REQUIRED:
        return (
            tuple(
                sorted(
                    {
                        NormalizationEvidenceKindV1.NONE,
                        NormalizationEvidenceKindV1.TYPED_NONCERTIFICATE_CAUSE,
                    },
                    key=lambda item: item.value,
                )
            ),
            tuple(sorted(_GENERIC_NONCERTIFICATE_CODES, key=lambda item: item.value)),
        )
    raise AssertionError("unreachable normalization family")


_EXACT_RULE_FAMILY_BY_SOURCE_KEY = {
    (
        "v075_batch_occurrence_lifecycle_authority_v2:"
        "V075BatchFailureTerminalCodeV2:POLICY_ABORT_NONCERTIFICATE"
    ): NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL,
    (
        "v075_campaign_reconciliation_v1:V075OccurrenceTerminalCodeV1:"
        "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE"
    ): NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED,
    (
        "v075_campaign_reconciliation_v1:V075OccurrenceTerminalCodeV1:"
        "TOTAL_LIFT_NONCERTIFICATE"
    ): NormalizationFamilyV1.TYPED_NONCERTIFICATE_CAUSE_REQUIRED,
    (
        "v075_integrated_occurrence_pipeline_v1:"
        "V075IntegratedOccurrenceTerminalCodeV1:NO_UNCERTAIN_PROOF_FRONTIER"
    ): NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL,
    (
        "v075_occurrence_failure_lifecycle_authority_v1:"
        "V075OccurrenceFailureTerminalCodeV1:PROCESS_FAILURE"
    ): NormalizationFamilyV1.PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED,
    (
        "v075_occurrence_failure_lifecycle_authority_v1:"
        "V075OccurrenceFailureTerminalCodeV1:TIMEOUT"
    ): NormalizationFamilyV1.TIMEOUT_CAP_REPLAY_OR_PROTOCOL_FAILURE,
    (
        "v075_production_occurrence_authority_v1:"
        "V075ProductionOccurrenceTerminalCodeV1:EXACT_POLICY_REGRET_FAILURE"
    ): NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL,
    (
        "v075_production_occurrence_authority_v1:"
        "V075ProductionOccurrenceTerminalCodeV1:EXACT_POLICY_RISK_FAILURE"
    ): NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL,
    (
        "v075_production_occurrence_authority_v1:"
        "V075ProductionOccurrenceTerminalCodeV1:"
        "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE"
    ): NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED,
    (
        "v075_production_occurrence_authority_v1:"
        "V075ProductionOccurrenceTerminalCodeV1:NO_UNCERTAIN_PROOF_FRONTIER"
    ): NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL,
    (
        "v075_production_occurrence_authority_v1:"
        "V075ProductionOccurrenceTerminalCodeV1:PROCESS_FAILURE"
    ): NormalizationFamilyV1.PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED,
    (
        "v075_production_occurrence_authority_v1:"
        "V075ProductionOccurrenceTerminalCodeV1:STATISTICAL_ENVELOPE_MISS"
    ): NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL,
    (
        "v075_production_occurrence_authority_v1:"
        "V075ProductionOccurrenceTerminalCodeV1:TIMEOUT"
    ): NormalizationFamilyV1.TIMEOUT_CAP_REPLAY_OR_PROTOCOL_FAILURE,
    (
        "v075_production_occurrence_authority_v2:"
        "V075OccurrenceTerminalCodeV2:CONSTRUCTION_CONTROL_ONLY"
    ): NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL,
}


def _expected_rules_v1(
    source_profile: all_path_v1.ConstructionK7AllPathAccountingProfileV1,
) -> tuple[ConditionalNormalizationRuleV1, ...]:
    extension_rows = tuple(
        row
        for row in source_profile.v075_status_mappings
        if row.disposition
        is all_path_v1.V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED
    )
    observed = {row.source_key for row in extension_rows}
    if (
        len(extension_rows) != EXPECTED_EXTENSION_ROW_COUNT
        or observed != set(_EXACT_RULE_FAMILY_BY_SOURCE_KEY)
    ):
        _fail("the exact fourteen-row source profile binding changed")
    rules = []
    for row in extension_rows:
        family = _EXACT_RULE_FAMILY_BY_SOURCE_KEY[row.source_key]
        evidence_kinds, targets = _family_shape_v1(family)
        rules.append(
            ConditionalNormalizationRuleV1(
                row.source_module,
                row.enum_class,
                row.member_name,
                row.member_value,
                row.reason_code,
                family,
                evidence_kinds,
                targets,
            )
        )
    result = tuple(sorted(rules, key=lambda row: row.source_key))
    counts = {
        family: sum(row.normalization_family is family for row in result)
        for family in NormalizationFamilyV1
    }
    if counts != {
        NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED: (
            EXPECTED_PLAN_ROUTE_ROW_COUNT
        ),
        NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL: (
            EXPECTED_CONTINUATION_ROW_COUNT
        ),
        NormalizationFamilyV1.PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED: (
            EXPECTED_PROCESS_FAILURE_ROW_COUNT
        ),
        NormalizationFamilyV1.TIMEOUT_CAP_REPLAY_OR_PROTOCOL_FAILURE: (
            EXPECTED_TIMEOUT_ROW_COUNT
        ),
        NormalizationFamilyV1.TYPED_NONCERTIFICATE_CAUSE_REQUIRED: (
            EXPECTED_GENERIC_NONCERTIFICATE_ROW_COUNT
        ),
    }:
        _fail("the fourteen conditional-normalization families changed")
    return result


def _profile_payload_v1(
    source_profile_id: str,
    source_inventory_id: str,
    rules: tuple[ConditionalNormalizationRuleV1, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.construction_k7_conditional_terminal_normalization_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "source_all_path_accounting_profile_id": source_profile_id,
        "source_v075_terminal_status_inventory_id": source_inventory_id,
        "source_disposition": (
            all_path_v1.V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED.value
        ),
        "exact_source_row_count": EXPECTED_EXTENSION_ROW_COUNT,
        "rules": [row.to_document() for row in rules],
        "new_member_requires_explicit_profile_revision": True,
        "no_default_or_class_level_inheritance": True,
        "conditional_normalization_only": True,
        "source_status_string_alone_never_authorizes_terminal": True,
        "downstream_semantic_terminal_authority_required": True,
        "terminal_artifacts_issued": 0,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_n_break_even": None,
        "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
        "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
    }


@dataclass(frozen=True, slots=True)
class ConstructionK7ConditionalTerminalNormalizationProfileV1:
    _issuer: object = field(repr=False, compare=False)
    source_all_path_accounting_profile_id: str
    source_v075_terminal_status_inventory_id: str
    rules: tuple[ConditionalNormalizationRuleV1, ...]
    terminal_artifacts_issued: int = 0
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_n_break_even: None = None
    counter_completeness_gate_status: str = COUNTER_COMPLETENESS_GATE_STATUS
    workload_economics_gate_status: str = WORKLOAD_ECONOMICS_GATE_STATUS

    def __post_init__(self) -> None:
        if self._issuer is not _PROFILE_ISSUER:
            _fail("conditional-normalization profile is caller-minted")
        _cid(
            self.source_all_path_accounting_profile_id,
            "source_all_path_accounting_profile_id",
        )
        _cid(
            self.source_v075_terminal_status_inventory_id,
            "source_v075_terminal_status_inventory_id",
        )
        source = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
        expected = _expected_rules_v1(source)
        rules = tuple(self.rules)
        object.__setattr__(self, "rules", rules)
        if (
            self.source_all_path_accounting_profile_id != source.profile_id
            or self.source_v075_terminal_status_inventory_id
            != source.v075_terminal_status_inventory_id
            or rules != expected
            or len({row.source_key for row in rules}) != EXPECTED_EXTENSION_ROW_COUNT
            or self.terminal_artifacts_issued != 0
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_n_break_even is not None
            or self.counter_completeness_gate_status
            != COUNTER_COMPLETENESS_GATE_STATUS
            or self.workload_economics_gate_status
            != WORKLOAD_ECONOMICS_GATE_STATUS
        ):
            _fail("conditional-normalization profile differs from Contract 2.0.40")

    @property
    def rule_by_source_key(self) -> dict[str, ConditionalNormalizationRuleV1]:
        return {row.source_key: row for row in self.rules}

    def _payload(self) -> dict[str, Any]:
        return _profile_payload_v1(
            self.source_all_path_accounting_profile_id,
            self.source_v075_terminal_status_inventory_id,
            self.rules,
        )

    @property
    def profile_id(self) -> str:
        return _content_id(PROFILE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


def freeze_construction_k7_conditional_terminal_normalization_profile_v1(
) -> ConstructionK7ConditionalTerminalNormalizationProfileV1:
    source = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    return ConstructionK7ConditionalTerminalNormalizationProfileV1(
        _PROFILE_ISSUER,
        source.profile_id,
        source.v075_terminal_status_inventory_id,
        _expected_rules_v1(source),
    )


@dataclass(frozen=True, slots=True)
class ConditionalNormalizationEvidenceV1:
    kind: NormalizationEvidenceKindV1
    route_kind: RouteKindEnum | None = None
    route_provenance_evidence_id: str | None = None
    process_failure_evidence_id: str | None = None
    protocol_failure_evidence_id: str | None = None
    preregistered_cap_profile_id: str | None = None
    trusted_budget_replay_id: str | None = None
    timeout_cap_scope: TimeoutCapScopeV1 | None = None
    noncertificate_cause_code: TerminalCode | None = None
    noncertificate_cause_evidence_id: str | None = None

    def __post_init__(self) -> None:
        try:
            kind = NormalizationEvidenceKindV1(self.kind)
        except (TypeError, ValueError) as error:
            raise ConstructionK7ConditionalTerminalNormalizationProfileV1Error(
                "normalization evidence kind is invalid"
            ) from error
        object.__setattr__(self, "kind", kind)
        populated = {
            "route_kind": self.route_kind,
            "route_provenance_evidence_id": self.route_provenance_evidence_id,
            "process_failure_evidence_id": self.process_failure_evidence_id,
            "protocol_failure_evidence_id": self.protocol_failure_evidence_id,
            "preregistered_cap_profile_id": self.preregistered_cap_profile_id,
            "trusted_budget_replay_id": self.trusted_budget_replay_id,
            "timeout_cap_scope": self.timeout_cap_scope,
            "noncertificate_cause_code": self.noncertificate_cause_code,
            "noncertificate_cause_evidence_id": (
                self.noncertificate_cause_evidence_id
            ),
        }
        required: dict[NormalizationEvidenceKindV1, set[str]] = {
            NormalizationEvidenceKindV1.NONE: set(),
            NormalizationEvidenceKindV1.PLAN_ROUTE_PROVENANCE: {
                "route_kind",
                "route_provenance_evidence_id",
            },
            NormalizationEvidenceKindV1.PROCESS_AND_PROTOCOL: {
                "process_failure_evidence_id",
                "protocol_failure_evidence_id",
            },
            NormalizationEvidenceKindV1.PREREGISTERED_CAP_AND_TRUSTED_REPLAY: {
                "preregistered_cap_profile_id",
                "trusted_budget_replay_id",
                "timeout_cap_scope",
            },
            NormalizationEvidenceKindV1.TYPED_NONCERTIFICATE_CAUSE: {
                "noncertificate_cause_code",
                "noncertificate_cause_evidence_id",
            },
        }
        populated_names = {name for name, value in populated.items() if value is not None}
        if populated_names != required[kind]:
            _fail("normalization evidence variant is incomplete or contains extra fields")
        id_fields = (
            self.route_provenance_evidence_id,
            self.process_failure_evidence_id,
            self.protocol_failure_evidence_id,
            self.preregistered_cap_profile_id,
            self.trusted_budget_replay_id,
            self.noncertificate_cause_evidence_id,
        )
        for value in id_fields:
            if value is not None:
                _cid(value, "normalization evidence reference")
        if kind is NormalizationEvidenceKindV1.PLAN_ROUTE_PROVENANCE:
            try:
                route = RouteKindEnum(self.route_kind)
            except (TypeError, ValueError) as error:
                raise ConstructionK7ConditionalTerminalNormalizationProfileV1Error(
                    "plan route provenance is invalid"
                ) from error
            if route not in _PLAN_CODE_BY_ROUTE:
                _fail("plan route provenance cannot select an FQ9 plan code")
            object.__setattr__(self, "route_kind", route)
        if kind is NormalizationEvidenceKindV1.PREREGISTERED_CAP_AND_TRUSTED_REPLAY:
            try:
                object.__setattr__(
                    self, "timeout_cap_scope", TimeoutCapScopeV1(self.timeout_cap_scope)
                )
            except (TypeError, ValueError) as error:
                raise ConstructionK7ConditionalTerminalNormalizationProfileV1Error(
                    "timeout cap scope is invalid"
                ) from error
        if kind is NormalizationEvidenceKindV1.TYPED_NONCERTIFICATE_CAUSE:
            try:
                code = TerminalCode(self.noncertificate_cause_code)
            except (TypeError, ValueError) as error:
                raise ConstructionK7ConditionalTerminalNormalizationProfileV1Error(
                    "typed noncertificate cause is invalid"
                ) from error
            if code not in _GENERIC_NONCERTIFICATE_CODES:
                _fail("typed generic cause must select an FQ9 noncertificate code")
            object.__setattr__(self, "noncertificate_cause_code", code)

    @classmethod
    def none(cls) -> "ConditionalNormalizationEvidenceV1":
        return cls(NormalizationEvidenceKindV1.NONE)

    @classmethod
    def plan_route(
        cls, route_kind: RouteKindEnum, route_provenance_evidence_id: str
    ) -> "ConditionalNormalizationEvidenceV1":
        return cls(
            NormalizationEvidenceKindV1.PLAN_ROUTE_PROVENANCE,
            route_kind=route_kind,
            route_provenance_evidence_id=route_provenance_evidence_id,
        )

    @classmethod
    def process_and_protocol(
        cls, process_failure_evidence_id: str, protocol_failure_evidence_id: str
    ) -> "ConditionalNormalizationEvidenceV1":
        return cls(
            NormalizationEvidenceKindV1.PROCESS_AND_PROTOCOL,
            process_failure_evidence_id=process_failure_evidence_id,
            protocol_failure_evidence_id=protocol_failure_evidence_id,
        )

    @classmethod
    def timeout_cap_replay(
        cls,
        timeout_cap_scope: TimeoutCapScopeV1,
        preregistered_cap_profile_id: str,
        trusted_budget_replay_id: str,
    ) -> "ConditionalNormalizationEvidenceV1":
        return cls(
            NormalizationEvidenceKindV1.PREREGISTERED_CAP_AND_TRUSTED_REPLAY,
            preregistered_cap_profile_id=preregistered_cap_profile_id,
            trusted_budget_replay_id=trusted_budget_replay_id,
            timeout_cap_scope=timeout_cap_scope,
        )

    @classmethod
    def typed_noncertificate_cause(
        cls, code: TerminalCode, evidence_id: str
    ) -> "ConditionalNormalizationEvidenceV1":
        return cls(
            NormalizationEvidenceKindV1.TYPED_NONCERTIFICATE_CAUSE,
            noncertificate_cause_code=code,
            noncertificate_cause_evidence_id=evidence_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_conditional_terminal_normalization_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "kind": self.kind.value,
            "route_kind": None if self.route_kind is None else self.route_kind.value,
            "route_provenance_evidence_id": self.route_provenance_evidence_id,
            "process_failure_evidence_id": self.process_failure_evidence_id,
            "protocol_failure_evidence_id": self.protocol_failure_evidence_id,
            "preregistered_cap_profile_id": self.preregistered_cap_profile_id,
            "trusted_budget_replay_id": self.trusted_budget_replay_id,
            "timeout_cap_scope": (
                None if self.timeout_cap_scope is None else self.timeout_cap_scope.value
            ),
            "noncertificate_cause_code": (
                None
                if self.noncertificate_cause_code is None
                else self.noncertificate_cause_code.value
            ),
            "noncertificate_cause_evidence_id": (
                self.noncertificate_cause_evidence_id
            ),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id(EVIDENCE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class ConditionalNormalizationResultV1:
    _issuer: object = field(repr=False, compare=False)
    profile_id: str
    rule_id: str
    source_key: str
    member_value: str
    evidence_id: str
    outcome: ConditionalNormalizationOutcomeV1
    fq9_terminal_class: TerminalClass | None
    fq9_terminal_code: TerminalCode | None
    reason_code: str
    normalization_only: bool = True
    terminal_artifact_issued: bool = False
    downstream_semantic_terminal_authority_required: bool = True

    def __post_init__(self) -> None:
        if self._issuer is not _RESULT_ISSUER:
            _fail("conditional-normalization result is caller-minted")
        for value, name in (
            (self.profile_id, "profile_id"),
            (self.rule_id, "rule_id"),
            (self.evidence_id, "evidence_id"),
        ):
            _cid(value, name)
        if not all(
            type(value) is str and value
            for value in (self.source_key, self.member_value, self.reason_code)
        ):
            _fail("conditional-normalization result lacks source/reason binding")
        try:
            outcome = ConditionalNormalizationOutcomeV1(self.outcome)
        except (TypeError, ValueError) as error:
            raise ConstructionK7ConditionalTerminalNormalizationProfileV1Error(
                "conditional-normalization outcome is invalid"
            ) from error
        object.__setattr__(self, "outcome", outcome)
        if outcome is (
            ConditionalNormalizationOutcomeV1
            .FQ9_TARGET_SELECTED_REQUIRES_TERMINAL_AUTHORITY
        ):
            try:
                terminal_class = TerminalClass(self.fq9_terminal_class)
                terminal_code = TerminalCode(self.fq9_terminal_code)
            except (TypeError, ValueError) as error:
                raise ConstructionK7ConditionalTerminalNormalizationProfileV1Error(
                    "selected conditional target lacks an exact FQ9 class/code"
                ) from error
            if _FQ9_CLASS_BY_CODE[terminal_code] is not terminal_class:
                _fail("selected conditional FQ9 class/code is inconsistent")
            object.__setattr__(self, "fq9_terminal_class", terminal_class)
            object.__setattr__(self, "fq9_terminal_code", terminal_code)
        elif self.fq9_terminal_class is not None or self.fq9_terminal_code is not None:
            _fail("non-target normalization result must not carry an FQ9 target")
        if (
            self.normalization_only is not True
            or self.terminal_artifact_issued is not False
            or self.downstream_semantic_terminal_authority_required is not True
        ):
            _fail("normalization result attempted to mint or imply a live terminal")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_conditional_terminal_normalization_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "rule_id": self.rule_id,
            "source_key": self.source_key,
            "member_value": self.member_value,
            "evidence_id": self.evidence_id,
            "outcome": self.outcome.value,
            "fq9_terminal_class": (
                None if self.fq9_terminal_class is None else self.fq9_terminal_class.value
            ),
            "fq9_terminal_code": (
                None if self.fq9_terminal_code is None else self.fq9_terminal_code.value
            ),
            "reason_code": self.reason_code,
            "normalization_only": True,
            "terminal_artifact_issued": False,
            "downstream_semantic_terminal_authority_required": True,
        }

    @property
    def result_id(self) -> str:
        return _content_id(RESULT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _result_v1(
    profile: ConstructionK7ConditionalTerminalNormalizationProfileV1,
    rule: ConditionalNormalizationRuleV1,
    evidence: ConditionalNormalizationEvidenceV1,
    outcome: ConditionalNormalizationOutcomeV1,
    target: TerminalCode | None,
    reason: str,
) -> ConditionalNormalizationResultV1:
    return ConditionalNormalizationResultV1(
        _RESULT_ISSUER,
        profile.profile_id,
        rule.rule_id,
        rule.source_key,
        rule.member_value,
        evidence.evidence_id,
        outcome,
        None if target is None else _FQ9_CLASS_BY_CODE[target],
        target,
        reason,
    )


def normalize_v075_profile_extension_status_v1(
    *,
    profile: ConstructionK7ConditionalTerminalNormalizationProfileV1,
    source_key: str,
    member_value: str,
    evidence: ConditionalNormalizationEvidenceV1,
) -> ConditionalNormalizationResultV1:
    """Select a conditional semantic target without minting a terminal."""

    if type(profile) is not ConstructionK7ConditionalTerminalNormalizationProfileV1:
        _fail("normalization requires the frozen Contract-2.0.40 profile")
    if type(evidence) is not ConditionalNormalizationEvidenceV1:
        _fail("normalization requires one typed evidence variant")
    try:
        rule = profile.rule_by_source_key[source_key]
    except (KeyError, TypeError) as error:
        raise ConstructionK7ConditionalTerminalNormalizationProfileV1Error(
            "unknown source member has no default normalization rule"
        ) from error
    if member_value != rule.member_value:
        _fail("source member value differs from the exact fourteen-row binding")
    if evidence.kind not in rule.allowed_evidence_kinds:
        _fail("evidence kind is inapplicable to the selected source status")

    family = rule.normalization_family
    if family is NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL:
        return _result_v1(
            profile,
            rule,
            evidence,
            ConditionalNormalizationOutcomeV1.ROUTE_CONTINUATION_NONTERMINAL,
            None,
            "ROUTE_CONTINUATION_AWAITS_LATER_EVIDENCE",
        )
    if family is NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED:
        if evidence.kind is NormalizationEvidenceKindV1.NONE:
            return _result_v1(
                profile,
                rule,
                evidence,
                ConditionalNormalizationOutcomeV1.EVIDENCE_REQUIRED,
                None,
                "PLAN_ROUTE_PROVENANCE_EVIDENCE_REQUIRED",
            )
        target = _PLAN_CODE_BY_ROUTE[evidence.route_kind]  # type: ignore[index]
        return _result_v1(
            profile,
            rule,
            evidence,
            ConditionalNormalizationOutcomeV1
            .FQ9_TARGET_SELECTED_REQUIRES_TERMINAL_AUTHORITY,
            target,
            "PLAN_ROUTE_PROVENANCE_SELECTS_FQ9_TARGET",
        )
    if family is NormalizationFamilyV1.PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED:
        if evidence.kind is NormalizationEvidenceKindV1.NONE:
            return _result_v1(
                profile,
                rule,
                evidence,
                ConditionalNormalizationOutcomeV1.EVIDENCE_REQUIRED,
                None,
                "PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED",
            )
        return _result_v1(
            profile,
            rule,
            evidence,
            ConditionalNormalizationOutcomeV1
            .FQ9_TARGET_SELECTED_REQUIRES_TERMINAL_AUTHORITY,
            TerminalCode.PROTOCOL_FAILURE,
            "RETAINED_PROCESS_AND_PROTOCOL_EVIDENCE_SELECTS_PROTOCOL_FAILURE",
        )
    if family is NormalizationFamilyV1.TIMEOUT_CAP_REPLAY_OR_PROTOCOL_FAILURE:
        if evidence.kind is NormalizationEvidenceKindV1.NONE:
            target = TerminalCode.PROTOCOL_FAILURE
            reason = "TIMEOUT_WITHOUT_TRUSTED_CAP_REPLAY_SELECTS_PROTOCOL_FAILURE"
        elif evidence.timeout_cap_scope is TimeoutCapScopeV1.ATTEMPT_BUDGET:
            target = TerminalCode.ATTEMPT_BUDGET_EXHAUSTED
            reason = "TRUSTED_ATTEMPT_CAP_REPLAY_SELECTS_ATTEMPT_BUDGET_EXHAUSTED"
        else:
            target = TerminalCode.FALLBACK_CAP_EXHAUSTED
            reason = "TRUSTED_FALLBACK_CAP_REPLAY_SELECTS_FALLBACK_CAP_EXHAUSTED"
        return _result_v1(
            profile,
            rule,
            evidence,
            ConditionalNormalizationOutcomeV1
            .FQ9_TARGET_SELECTED_REQUIRES_TERMINAL_AUTHORITY,
            target,
            reason,
        )
    if family is NormalizationFamilyV1.TYPED_NONCERTIFICATE_CAUSE_REQUIRED:
        if evidence.kind is NormalizationEvidenceKindV1.NONE:
            return _result_v1(
                profile,
                rule,
                evidence,
                ConditionalNormalizationOutcomeV1.EVIDENCE_REQUIRED,
                None,
                "TYPED_NONCERTIFICATE_CAUSE_EVIDENCE_REQUIRED",
            )
        target = evidence.noncertificate_cause_code
        assert target is not None
        return _result_v1(
            profile,
            rule,
            evidence,
            ConditionalNormalizationOutcomeV1
            .FQ9_TARGET_SELECTED_REQUIRES_TERMINAL_AUTHORITY,
            target,
            "TYPED_NONCERTIFICATE_CAUSE_SELECTS_EXACT_FQ9_TARGET",
        )
    raise AssertionError("unreachable conditional-normalization family")


@dataclass(frozen=True, slots=True)
class ConditionalNormalizationProfileReplayV1:
    _issuer: object = field(repr=False, compare=False)
    profile_id: str
    source_all_path_accounting_profile_id: str
    source_v075_terminal_status_inventory_id: str
    exact_source_row_count: int
    plan_route_row_count: int
    continuation_row_count: int
    process_failure_row_count: int
    timeout_row_count: int
    generic_noncertificate_row_count: int
    exact_source_binding_replayed: bool = True
    no_default_or_new_member_inheritance: bool = True
    terminal_artifacts_issued: int = 0
    gate_unlocked: bool = False

    def __post_init__(self) -> None:
        if self._issuer is not _REPLAY_ISSUER:
            _fail("conditional-normalization replay is caller-minted")
        for value, name in (
            (self.profile_id, "profile_id"),
            (
                self.source_all_path_accounting_profile_id,
                "source_all_path_accounting_profile_id",
            ),
            (
                self.source_v075_terminal_status_inventory_id,
                "source_v075_terminal_status_inventory_id",
            ),
        ):
            _cid(value, name)
        if (
            (
                self.exact_source_row_count,
                self.plan_route_row_count,
                self.continuation_row_count,
                self.process_failure_row_count,
                self.timeout_row_count,
                self.generic_noncertificate_row_count,
            )
            != (
                EXPECTED_EXTENSION_ROW_COUNT,
                EXPECTED_PLAN_ROUTE_ROW_COUNT,
                EXPECTED_CONTINUATION_ROW_COUNT,
                EXPECTED_PROCESS_FAILURE_ROW_COUNT,
                EXPECTED_TIMEOUT_ROW_COUNT,
                EXPECTED_GENERIC_NONCERTIFICATE_ROW_COUNT,
            )
            or self.exact_source_binding_replayed is not True
            or self.no_default_or_new_member_inheritance is not True
            or self.terminal_artifacts_issued != 0
            or self.gate_unlocked is not False
        ):
            _fail("conditional-normalization replay made an invalid claim")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_conditional_terminal_normalization_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "source_all_path_accounting_profile_id": (
                self.source_all_path_accounting_profile_id
            ),
            "source_v075_terminal_status_inventory_id": (
                self.source_v075_terminal_status_inventory_id
            ),
            "exact_source_row_count": self.exact_source_row_count,
            "plan_route_row_count": self.plan_route_row_count,
            "continuation_row_count": self.continuation_row_count,
            "process_failure_row_count": self.process_failure_row_count,
            "timeout_row_count": self.timeout_row_count,
            "generic_noncertificate_row_count": (
                self.generic_noncertificate_row_count
            ),
            "exact_source_binding_replayed": True,
            "no_default_or_new_member_inheritance": True,
            "terminal_artifacts_issued": 0,
            "gate_unlocked": False,
        }

    @property
    def replay_id(self) -> str:
        return _content_id(REPLAY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "replay_id": self.replay_id}


def verify_construction_k7_conditional_terminal_normalization_profile_document_v1(
    document: Mapping[str, Any],
) -> ConditionalNormalizationProfileReplayV1:
    """Independently replay the exact portable 14-row profile document."""

    if type(document) is not dict:
        _fail("conditional-normalization profile document must be one dictionary")
    source = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    # Replay the consumed profile as well; a matching opaque ID alone is not
    # enough to establish the live source inventory and exact dispositions.
    all_path_v1.verify_construction_k7_all_path_accounting_profile_document_v1(
        source.to_document()
    )
    rules = _expected_rules_v1(source)
    expected_payload = _profile_payload_v1(
        source.profile_id,
        source.v075_terminal_status_inventory_id,
        rules,
    )
    expected_id = _content_id(PROFILE_DOMAIN, expected_payload)
    expected_document = {**expected_payload, "profile_id": expected_id}
    if document != expected_document:
        _fail("conditional-normalization document differs from exact replay")
    if document["profile_id"] != expected_id:
        _fail("conditional-normalization profile ID does not replay")
    counts = {
        family: sum(row.normalization_family is family for row in rules)
        for family in NormalizationFamilyV1
    }
    return ConditionalNormalizationProfileReplayV1(
        _REPLAY_ISSUER,
        expected_id,
        source.profile_id,
        source.v075_terminal_status_inventory_id,
        len(rules),
        counts[NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED],
        counts[NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL],
        counts[NormalizationFamilyV1.PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED],
        counts[NormalizationFamilyV1.TIMEOUT_CAP_REPLAY_OR_PROTOCOL_FAILURE],
        counts[NormalizationFamilyV1.TYPED_NONCERTIFICATE_CAUSE_REQUIRED],
    )


__all__ = [
    "ConditionalNormalizationEvidenceV1",
    "ConditionalNormalizationOutcomeV1",
    "ConditionalNormalizationProfileReplayV1",
    "ConditionalNormalizationResultV1",
    "ConditionalNormalizationRuleV1",
    "ConstructionK7ConditionalTerminalNormalizationProfileV1",
    "ConstructionK7ConditionalTerminalNormalizationProfileV1Error",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "EXPECTED_CONTINUATION_ROW_COUNT",
    "EXPECTED_EXTENSION_ROW_COUNT",
    "EXPECTED_GENERIC_NONCERTIFICATE_ROW_COUNT",
    "EXPECTED_PLAN_ROUTE_ROW_COUNT",
    "EXPECTED_PROCESS_FAILURE_ROW_COUNT",
    "EXPECTED_TIMEOUT_ROW_COUNT",
    "NormalizationEvidenceKindV1",
    "NormalizationFamilyV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "TimeoutCapScopeV1",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "freeze_construction_k7_conditional_terminal_normalization_profile_v1",
    "normalize_v075_profile_extension_status_v1",
    "verify_construction_k7_conditional_terminal_normalization_profile_document_v1",
]
