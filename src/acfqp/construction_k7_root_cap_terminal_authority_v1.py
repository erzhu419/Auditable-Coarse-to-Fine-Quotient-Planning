"""Non-retroactive K7 root-cap attempt-terminal accounting authority.

This successor consumes the independently replayable formal K7 accounting
materialization and the same full semantic roots used to create it.  It then
replays the actual production child-closure bytes that caused
``CHILD_ACTION_ROW_CAP_EXCEEDED`` and derives exactly one route-attempt
noncertificate terminal:

``ROUTE_ATTEMPT / ATTEMPT_CLOSURE_NONCERTIFICATE /
ATTEMPT_BUDGET_EXHAUSTED``.

The module does not alter the historical generic terminal verifier.  It does
not close a logical occurrence, certify infeasibility, unlock an official
Gate, or discard work.  The portable terminal bundle embeds the complete
202-record formal materialization so an ID-only claim is never sufficient.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import RouteKindEnum, SHARED_AXES
from acfqp import campaign_v1
from acfqp import construction_k7_formal_accounting_materializer_v1 as materializer_v1
from acfqp import construction_occurrence_identity_cutoff_semantic_authority_v2 as occurrence_v2
from acfqp import v075_k7_broker_worker_entry_v1 as worker_v1
from acfqp import v075_construction_native_accounting_foundation_v2 as foundation_v2
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic_v2
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as multiround_v2
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN,
    CONSTRUCTION_K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN,
    CONSTRUCTION_K7_ROOT_CAP_TERMINAL_ACCOUNTING_VERIFICATION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.30"
PROFILE_KEY = "construction_k7_root_cap_terminal_authority_v1"

K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN = CONSTRUCTION_K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN
K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN = CONSTRUCTION_K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN
K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN = CONSTRUCTION_K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN
K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN = CONSTRUCTION_K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN
K7_ROOT_CAP_TERMINAL_ACCOUNTING_VERIFICATION_V1_DOMAIN = CONSTRUCTION_K7_ROOT_CAP_TERMINAL_ACCOUNTING_VERIFICATION_V1_DOMAIN

LOCAL_DOMAINS = frozenset(
    {
        K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN,
        K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN,
        K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN,
        K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN,
        K7_ROOT_CAP_TERMINAL_ACCOUNTING_VERIFICATION_V1_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 5:  # pragma: no cover
    raise RuntimeError("K7 root-cap terminal domains must be unique")
if not LOCAL_DOMAINS.issubset(PHASE3E_DOMAIN_TAGS):  # pragma: no cover
    raise RuntimeError("K7 root-cap terminal domains must be centrally registered")

EXPECTED_COUNTER_RECORD_COUNT = materializer_v1.EXPECTED_COUNTER_RECORD_COUNT
EXPECTED_COMPARISON_AXIS_COUNT = len(SHARED_AXES)
SOURCE_CAUSE = "CHILD_ACTION_ROW_CAP_EXCEEDED"
CAP_RELATION = "EXISTING_PLUS_UNRESOLVED_CHILD_ACTION_ROWS_GT_REGISTERED_CAP"


class K7AttemptTerminalScopeV1(str, Enum):
    ROUTE_ATTEMPT = "ROUTE_ATTEMPT"


class K7AttemptTerminalClassV1(str, Enum):
    ATTEMPT_CLOSURE_NONCERTIFICATE = "ATTEMPT_CLOSURE_NONCERTIFICATE"


class K7AttemptTerminalCodeV1(str, Enum):
    ATTEMPT_BUDGET_EXHAUSTED = "ATTEMPT_BUDGET_EXHAUSTED"


TERMINAL_SCOPE = K7AttemptTerminalScopeV1.ROUTE_ATTEMPT
TERMINAL_CLASS = K7AttemptTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE
TERMINAL_CODE = K7AttemptTerminalCodeV1.ATTEMPT_BUDGET_EXHAUSTED

_CAP_EVIDENCE_ISSUER = object()
_TERMINAL_AUTHORITY_ISSUER = object()
_BUNDLE_ISSUER = object()
_VERIFICATION_ISSUER = object()


class ConstructionK7RootCapTerminalAuthorityV1Error(ValueError):
    """A cap source, accounting vector, terminal, or identity failed replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RootCapTerminalAuthorityV1Error(message)


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("K7 root-cap terminal used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RootCapTerminalAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _canonical_object(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RootCapTerminalAuthorityV1Error(
            f"{label} bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} bytes are noncanonical")
    return document


def _exact_single_role(
    portable: portable_v2.V075PortableOccurrenceEvidenceBundleV2,
    role: str,
) -> portable_v2.V075PortableEvidenceArtifactRecordV2:
    matches = tuple(row for row in portable.records if row.role == role)
    if len(matches) != 1:
        _fail(f"portable production bundle lacks exactly one {role}")
    return matches[0]


def _cap_profile_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.construction_k7_root_cap_semantics_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "source_module": "acfqp.v075_live_dynamic_acquisition_authority_v2",
        "source_schema": "acfqp.v075_live_dynamic_child_closure.v2",
        "source_profile_key": dynamic_v2.PROFILE_KEY,
        "maximum_new_child_action_rows": (
            dynamic_v2.MAXIMUM_NEW_CHILD_ACTION_ROWS
        ),
        "counted_quantity": (
            "existing_child_action_row_count_plus_"
            "unresolved_child_action_row_count"
        ),
        "cap_relation": CAP_RELATION,
        "partial_subset_selection_allowed": False,
        "caller_cap_override_allowed": False,
    }


K7_ROOT_CAP_SEMANTICS_PROFILE_ID_V1 = _local_id(
    K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN,
    _cap_profile_payload(),
)


@dataclass(frozen=True, slots=True)
class K7RootCapExhaustionEvidenceV1:
    """Replayed production evidence that the exact K7 action-row cap fired."""

    _issuer: InitVar[object]
    occurrence_authority_bundle_id: str
    occurrence_authority_id: str
    operational_cutoff_authority_id: str
    production_runtime_envelope_id: str
    portable_request_replay_id: str
    owned_partial_result_id: str
    partial_native_transcript_id: str
    partial_native_terminal_id: str
    transcript_document_sha256: str
    ordered_chain_node_count: int
    terminal_closure_observation_id: str
    runtime_business_result_id: str
    runtime_business_result_sha256: str
    runtime_business_result_byte_count: int
    portable_evidence_bundle_id: str
    multiround_record_id: str
    multiround_result_id: str
    child_closure_record_id: str
    child_closure_id: str
    child_closure_verification_record_id: str
    child_closure_verification_id: str
    logical_occurrence_id: str
    rebuild_policy_id: str
    route_attempt_id: str
    decision_point_id: str
    transaction_id: str
    transaction_index: int
    route_cap_profile_id: str
    action_row_cap_profile_id: str
    terminal_derivation_registry_id: str
    existing_child_action_row_count: int
    unresolved_child_action_row_count: int
    maximum_new_child_action_rows: int
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CAP_EVIDENCE_ISSUER:
            _fail("K7 root-cap evidence is caller-minted")
        for value, label in (
            (self.occurrence_authority_bundle_id, "occurrence authority bundle"),
            (self.occurrence_authority_id, "occurrence authority"),
            (self.operational_cutoff_authority_id, "cutoff authority"),
            (self.production_runtime_envelope_id, "production runtime"),
            (self.portable_request_replay_id, "portable request replay"),
            (self.owned_partial_result_id, "owned partial result"),
            (self.partial_native_transcript_id, "partial transcript"),
            (self.partial_native_terminal_id, "partial terminal"),
            (self.terminal_closure_observation_id, "terminal observation"),
            (self.runtime_business_result_id, "runtime business result"),
            (self.portable_evidence_bundle_id, "portable evidence bundle"),
            (self.multiround_record_id, "multiround source record"),
            (self.multiround_result_id, "multiround result"),
            (self.child_closure_record_id, "child closure source record"),
            (self.child_closure_id, "child closure"),
            (
                self.child_closure_verification_record_id,
                "child closure verification record",
            ),
            (
                self.child_closure_verification_id,
                "child closure verification",
            ),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.rebuild_policy_id, "rebuild policy"),
            (self.route_attempt_id, "route attempt"),
            (self.decision_point_id, "decision point"),
            (self.transaction_id, "transaction"),
            (self.route_cap_profile_id, "route cap profile"),
            (self.action_row_cap_profile_id, "action-row cap profile"),
            (
                self.terminal_derivation_registry_id,
                "terminal derivation registry",
            ),
        ):
            _cid(value, label)
        for value, label in (
            (self.transcript_document_sha256, "transcript document digest"),
            (
                self.runtime_business_result_sha256,
                "runtime business-result digest",
            ),
        ):
            if (
                type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                _fail(f"{label} must be one lowercase SHA-256")
        for value, label in (
            (self.transaction_index, "transaction index"),
            (self.ordered_chain_node_count, "ordered chain node count"),
            (
                self.runtime_business_result_byte_count,
                "runtime business-result byte count",
            ),
            (self.existing_child_action_row_count, "existing child rows"),
            (self.unresolved_child_action_row_count, "unresolved child rows"),
            (self.maximum_new_child_action_rows, "maximum child rows"),
        ):
            _nonnegative(value, label)
        if (
            self.transaction_index < 1
            or self.ordered_chain_node_count <= 0
            or self.runtime_business_result_byte_count <= 0
            or self.action_row_cap_profile_id
            != K7_ROOT_CAP_SEMANTICS_PROFILE_ID_V1
            or self.maximum_new_child_action_rows
            != dynamic_v2.MAXIMUM_NEW_CHILD_ACTION_ROWS
            or self.unresolved_child_action_row_count <= 0
            or self.existing_child_action_row_count
            + self.unresolved_child_action_row_count
            <= self.maximum_new_child_action_rows
        ):
            _fail("K7 child action-row cap was not exactly exhausted")
        object.__setattr__(
            self,
            "_evidence_id",
            _local_id(
                K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_root_cap_exhaustion_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_authority_bundle_id": self.occurrence_authority_bundle_id,
            "occurrence_authority_id": self.occurrence_authority_id,
            "operational_cutoff_authority_id": self.operational_cutoff_authority_id,
            "production_runtime_envelope_id": self.production_runtime_envelope_id,
            "portable_request_replay_id": self.portable_request_replay_id,
            "owned_partial_result_id": self.owned_partial_result_id,
            "partial_native_transcript_id": self.partial_native_transcript_id,
            "partial_native_terminal_id": self.partial_native_terminal_id,
            "transcript_document_sha256": self.transcript_document_sha256,
            "ordered_chain_node_count": self.ordered_chain_node_count,
            "terminal_closure_observation_id": self.terminal_closure_observation_id,
            "runtime_business_result_id": self.runtime_business_result_id,
            "runtime_business_result_sha256": self.runtime_business_result_sha256,
            "runtime_business_result_byte_count": (
                self.runtime_business_result_byte_count
            ),
            "portable_evidence_bundle_id": self.portable_evidence_bundle_id,
            "multiround_record_id": self.multiround_record_id,
            "multiround_result_id": self.multiround_result_id,
            "child_closure_record_id": self.child_closure_record_id,
            "child_closure_id": self.child_closure_id,
            "child_closure_verification_record_id": (
                self.child_closure_verification_record_id
            ),
            "child_closure_verification_id": (
                self.child_closure_verification_id
            ),
            "logical_occurrence_id": self.logical_occurrence_id,
            "rebuild_policy_id": self.rebuild_policy_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
            "transaction_index": self.transaction_index,
            "route_cap_profile_id": self.route_cap_profile_id,
            "action_row_cap_profile_id": self.action_row_cap_profile_id,
            "terminal_derivation_registry_id": (
                self.terminal_derivation_registry_id
            ),
            "source_cause": SOURCE_CAUSE,
            "existing_child_action_row_count": (
                self.existing_child_action_row_count
            ),
            "unresolved_child_action_row_count": (
                self.unresolved_child_action_row_count
            ),
            "total_child_action_row_count": (
                self.existing_child_action_row_count
                + self.unresolved_child_action_row_count
            ),
            "maximum_new_child_action_rows": (
                self.maximum_new_child_action_rows
            ),
            "cap_relation": CAP_RELATION,
            "cap_exceeded_from_exact_source_closure": True,
            "issuer_owned_multiround_result_replayed": True,
            "actual_business_result_bytes_replayed": True,
            "full_owner_transcript_replayed": True,
            "cap_claim_derived_from_status_string_or_hash_only": False,
            "default_rebuild_policy_replayed": True,
            "rebuild_allowed": False,
            "specific_cause_retained": True,
            "worker_self_claim_accepted": False,
            "caller_cap_value_accepted": False,
            "infeasibility_mapping_allowed": False,
            "official_execution_allowed": False,
        }

    @property
    def evidence_id(self) -> str:
        expected = _local_id(
            K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._evidence_id:
            _fail("K7 root-cap evidence changed after issuance")
        return self._evidence_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "root_cap_exhaustion_evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class K7AttemptBudgetTerminalAuthorityV1:
    """Attempt-scoped noncertificate terminal joined to complete actual work."""

    _issuer: InitVar[object]
    cap_evidence: K7RootCapExhaustionEvidenceV1 = field(repr=False)
    formal_materialization_bundle_id: str
    semantic_evidence_closure_id: str
    semantic_evidence_closure_context_id: str
    actual_projection_proof_id: str
    work_vector_id: str
    comparison_vector_id: str
    counter_record_ids: tuple[str, ...]
    route_attempt_count: int
    route_success_count: int
    route_failure_count: int
    _authority_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _TERMINAL_AUTHORITY_ISSUER
            or type(self.cap_evidence) is not K7RootCapExhaustionEvidenceV1
        ):
            _fail("K7 attempt terminal authority is caller-minted")
        for value, label in (
            (self.formal_materialization_bundle_id, "formal materialization"),
            (self.semantic_evidence_closure_id, "semantic evidence closure"),
            (
                self.semantic_evidence_closure_context_id,
                "semantic evidence closure context",
            ),
            (self.actual_projection_proof_id, "actual projection proof"),
            (self.work_vector_id, "work vector"),
            (self.comparison_vector_id, "comparison vector"),
            *((value, "counter record") for value in self.counter_record_ids),
        ):
            _cid(value, label)
        for value, label in (
            (self.route_attempt_count, "route attempt count"),
            (self.route_success_count, "route success count"),
            (self.route_failure_count, "route failure count"),
        ):
            _nonnegative(value, label)
        if (
            type(self.counter_record_ids) is not tuple
            or len(self.counter_record_ids) != EXPECTED_COUNTER_RECORD_COUNT
            or len(set(self.counter_record_ids)) != len(self.counter_record_ids)
            or (
                self.route_attempt_count,
                self.route_success_count,
                self.route_failure_count,
            )
            != (1, 0, 1)
            or self.route_attempt_count
            != self.route_success_count + self.route_failure_count
        ):
            _fail("attempt terminal lacks exact 202-path work or 1/0/1 outcome")
        object.__setattr__(
            self,
            "_authority_id",
            _local_id(
                K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        cap = self.cap_evidence
        return {
            "schema": "acfqp.construction_k7_attempt_budget_terminal_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE.value,
            "terminal_class": TERMINAL_CLASS.value,
            "terminal_code": TERMINAL_CODE.value,
            "specific_cause": SOURCE_CAUSE,
            "root_cap_exhaustion_evidence_id": cap.evidence_id,
            "logical_occurrence_id": cap.logical_occurrence_id,
            "rebuild_policy_id": cap.rebuild_policy_id,
            "route_attempt_id": cap.route_attempt_id,
            "decision_point_id": cap.decision_point_id,
            "transaction_id": cap.transaction_id,
            "transaction_index": cap.transaction_index,
            "route_cap_profile_id": cap.route_cap_profile_id,
            "terminal_derivation_registry_id": (
                cap.terminal_derivation_registry_id
            ),
            "child_closure_id": cap.child_closure_id,
            "terminal_closure_observation_id": (
                cap.terminal_closure_observation_id
            ),
            "formal_accounting_materialization_bundle_id": (
                self.formal_materialization_bundle_id
            ),
            "semantic_evidence_closure_id": self.semantic_evidence_closure_id,
            "semantic_evidence_closure_context_id": (
                self.semantic_evidence_closure_context_id
            ),
            "formal_actual_projection_proof_id": self.actual_projection_proof_id,
            "actual_work_vector_id": self.work_vector_id,
            "actual_comparison_vector_id": self.comparison_vector_id,
            "counter_record_count": len(self.counter_record_ids),
            "counter_record_ids": list(self.counter_record_ids),
            "route_attempt_count": self.route_attempt_count,
            "route_success_count": self.route_success_count,
            "route_failure_count": self.route_failure_count,
            "all_observed_work_preserved": True,
            "failed_route_work_discarded": False,
            "counter_values_rewritten_by_terminal": False,
            "worker_terminal_self_report_authoritative": False,
            "terminal_recomputed_from_source_cap_authority": True,
            "trusted_budget_replay_used": False,
            "local_transaction_budget_outcome_claimed": False,
            "construction_root_cap_derivation_rule_used": True,
            "terminal_is_infeasibility_certificate": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "logical_occurrence_closed": False,
            "rebuild_policy_bound_for_successor_occurrence_closure": True,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def authority_id(self) -> str:
        expected = _local_id(
            K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._authority_id:
            _fail("K7 attempt terminal authority changed after issuance")
        return self._authority_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "attempt_budget_terminal_authority_id": self.authority_id,
        }


@dataclass(frozen=True, slots=True)
class K7RootCapTerminalAccountingBundleV1:
    """Portable attempt terminal with the complete formal work embedded."""

    _issuer: InitVar[object]
    formal_materialization: (
        materializer_v1.K7FormalAccountingMaterializationBundleV1
    ) = field(repr=False)
    cap_evidence: K7RootCapExhaustionEvidenceV1 = field(repr=False)
    terminal_authority: K7AttemptBudgetTerminalAuthorityV1 = field(repr=False)
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BUNDLE_ISSUER
            or type(self.formal_materialization)
            is not materializer_v1.K7FormalAccountingMaterializationBundleV1
            or type(self.cap_evidence) is not K7RootCapExhaustionEvidenceV1
            or type(self.terminal_authority)
            is not K7AttemptBudgetTerminalAuthorityV1
            or self.terminal_authority.cap_evidence is not self.cap_evidence
            or self.terminal_authority.formal_materialization_bundle_id
            != self.formal_materialization.bundle_id
        ):
            _fail("K7 terminal accounting bundle is caller-minted or crossed")
        object.__setattr__(
            self,
            "_bundle_id",
            _local_id(
                K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_root_cap_terminal_accounting_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE.value,
            "terminal_class": TERMINAL_CLASS.value,
            "terminal_code": TERMINAL_CODE.value,
            "specific_cause": SOURCE_CAUSE,
            "formal_accounting_materialization_bundle": (
                self.formal_materialization.to_document()
            ),
            "root_cap_exhaustion_evidence": self.cap_evidence.to_document(),
            "attempt_budget_terminal_authority": (
                self.terminal_authority.to_document()
            ),
            "complete_202_path_work_embedded": True,
            "id_only_materialization_accepted": False,
            "worker_terminal_self_report_authoritative": False,
            "forged_terminal_classification_accepted": False,
            "incomplete_work_accepted": False,
            "terminal_is_infeasibility_certificate": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "logical_occurrence_closed": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def bundle_id(self) -> str:
        expected = _local_id(
            K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._bundle_id:
            _fail("K7 terminal accounting bundle changed after issuance")
        return self._bundle_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "root_cap_terminal_accounting_bundle_id": self.bundle_id,
        }


@dataclass(frozen=True, slots=True)
class K7RootCapTerminalAccountingVerificationV1:
    """Independent full-root replay attestation for the portable terminal."""

    _issuer: InitVar[object]
    verified_bundle: K7RootCapTerminalAccountingBundleV1 = field(
        repr=False, compare=False
    )
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.verified_bundle)
            is not K7RootCapTerminalAccountingBundleV1
        ):
            _fail("K7 terminal verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _local_id(
                K7_ROOT_CAP_TERMINAL_ACCOUNTING_VERIFICATION_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        bundle = self.verified_bundle
        terminal = bundle.terminal_authority
        return {
            "schema": "acfqp.construction_k7_root_cap_terminal_accounting_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "root_cap_terminal_accounting_bundle_id": bundle.bundle_id,
            "root_cap_exhaustion_evidence_id": bundle.cap_evidence.evidence_id,
            "attempt_budget_terminal_authority_id": terminal.authority_id,
            "formal_accounting_materialization_bundle_id": (
                bundle.formal_materialization.bundle_id
            ),
            "actual_work_vector_id": terminal.work_vector_id,
            "actual_comparison_vector_id": terminal.comparison_vector_id,
            "counter_record_count": len(terminal.counter_record_ids),
            "terminal_scope": TERMINAL_SCOPE.value,
            "terminal_class": TERMINAL_CLASS.value,
            "terminal_code": TERMINAL_CODE.value,
            "specific_cause": SOURCE_CAUSE,
            "full_semantic_roots_replayed": True,
            "formal_materialization_replayed": True,
            "source_cap_identity_replayed": True,
            "complete_work_preservation_replayed": True,
            "worker_self_claim_used": False,
            "infeasibility_certificate": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
        }

    @property
    def verification_id(self) -> str:
        expected = _local_id(
            K7_ROOT_CAP_TERMINAL_ACCOUNTING_VERIFICATION_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._verification_id:
            _fail("K7 terminal verification changed after issuance")
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "root_cap_terminal_accounting_verification_id": (
                self.verification_id
            ),
        }


def _derive_root_cap_evidence(
    *,
    closure_replay_inputs: Mapping[str, Any],
) -> K7RootCapExhaustionEvidenceV1:
    if type(closure_replay_inputs) is not dict:
        _fail("closure replay inputs must be one exact dictionary")
    replay_roots = closure_replay_inputs.get("replay_roots")
    claimed_occurrence = closure_replay_inputs.get("occurrence_authority")
    if type(replay_roots) is not dict:
        _fail("closure replay inputs lack complete occurrence replay roots")
    try:
        occurrence = (
            occurrence_v2.replay_k7_occurrence_cutoff_semantic_authorities_v2(
                claimed_occurrence,
                **replay_roots,
            )
        )
        runtime = replay_roots["runtime_envelope"]
        request_replay = replay_roots["request_replay"]
        owned = replay_roots["owned_result"]
        output = worker_v1.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=replay_roots["operational_output_bytes"],
            expected_request_replay=request_replay,
            expected_binding=runtime.binding,
        )
        business = output.to_document()["business_result"]
        portable_raw = canonical_json_bytes(business["portable_evidence_bundle"])
        portable = portable_v2.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            portable_raw
        )
        closure_record = _exact_single_role(portable, "DYNAMIC_CHILD_CLOSURE")
        closure_verification_record = _exact_single_role(
            portable,
            "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
        )
        multiround_record = _exact_single_role(portable, "MULTIROUND_RESULT")
        closure_document = closure_record.artifact_document
        closure_verification_document = (
            closure_verification_record.artifact_document
        )
        multiround_document = multiround_record.artifact_document
        result = owned.result
        route = request_replay.request.route_identity
        route._assert_current()  # noqa: SLF001 - exact route identity replay
        derivation_registry = foundation_v2.V075TerminalDerivationRegistryV2(
            foundation_v2.EXPECTED_GENERIC_TERMINAL_MAPPING,
            SOURCE_CAUSE,
            TERMINAL_SCOPE.value,
            TERMINAL_CLASS.value,
            TERMINAL_CODE.value,
        )
    except ConstructionK7RootCapTerminalAuthorityV1Error:
        raise
    except Exception as error:
        raise ConstructionK7RootCapTerminalAuthorityV1Error(
            "production cap source failed full-root public replay"
        ) from error

    occurrence_row = occurrence.occurrence_authority
    cutoff_row = occurrence.cutoff_authority
    existing = closure_document.get("existing_child_action_row_count")
    unresolved = closure_document.get("unresolved_child_action_row_count")
    maximum = closure_document.get("maximum_new_child_action_rows")
    for value, label in (
        (existing, "source existing child rows"),
        (unresolved, "source unresolved child rows"),
        (maximum, "source child-row cap"),
    ):
        _nonnegative(value, label)
    transaction = route.transaction
    if (
        type(result) is not multiround_v2.V075ObserverSignedMultiroundResultV2
        or result.status
        is not (
            multiround_v2.V075ObserverSignedMultiroundTerminalStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        )
        or result.child_closure_status
        is not dynamic_v2.V075LiveDynamicChildClosureStatusV2.CHILD_ACTION_ROW_CAP_EXCEEDED
        or occurrence_row.terminal_status != SOURCE_CAUSE
        or occurrence_row.terminal_kind != "COMPLETED"
        or occurrence_row.route_attempt_outcome != "FAILURE"
        or (
            occurrence_row.route_attempt_count,
            occurrence_row.route_success_count,
            occurrence_row.route_failure_count,
        )
        != (1, 0, 1)
        or closure_record.semantic_artifact_id != result.child_closure_id
        or closure_document.get("closure_id") != result.child_closure_id
        or closure_document.get("schema")
        != "acfqp.v075_live_dynamic_child_closure.v2"
        or closure_document.get("profile_key") != dynamic_v2.PROFILE_KEY
        or closure_document.get("status") != SOURCE_CAUSE
        or closure_document.get("terminal_class")
        != "ATTEMPT_CLOSURE_NONCERTIFICATE"
        or maximum != dynamic_v2.MAXIMUM_NEW_CHILD_ACTION_ROWS
        or unresolved <= 0
        or existing + unresolved <= maximum
        or closure_document.get("discovery_intent_ids") != []
        or closure_document.get("validation_template_ids") != []
        or closure_document.get("discovery_intents") != []
        or closure_document.get("validation_templates") != []
        or closure_document.get("all_root_support_descriptors_examined") is not True
        or closure_document.get("complete_child_catalogues") is not True
        or closure_document.get("all_or_none_child_base_authorization") is not True
        or closure_document.get("official_execution_allowed") is not False
        or closure_document.get("plan_certificate") is not False
        or closure_document.get("infeasibility_certificate") is not False
        or closure_verification_record.semantic_artifact_id
        != result.child_closure_verification_id
        or closure_verification_document.get("verification_id")
        != result.child_closure_verification_id
        or closure_verification_document.get("closure_id")
        != result.child_closure_id
        or closure_verification_document.get("status") != SOURCE_CAUSE
        or closure_verification_document.get("semantic_replay_complete") is not True
        or closure_verification_document.get("discovery_intent_ids") != []
        or closure_verification_document.get("validation_template_ids") != []
        or multiround_record.semantic_artifact_id != result.result_id
        or multiround_document.get("result_id") != result.result_id
        or multiround_document.get("status") != SOURCE_CAUSE
        or multiround_document.get("child_closure_status") != SOURCE_CAUSE
        or multiround_document.get("child_closure_id") != result.child_closure_id
        or multiround_document.get("child_closure_verification_id")
        != result.child_closure_verification_id
        or multiround_document.get("plan_certificate") is not False
        or multiround_document.get("infeasibility_certificate") is not False
        or multiround_document.get("official_execution_allowed") is not False
        or business.get("owned_partial_result_id") != owned.wrapper_id
        or portable.bundle_id != business.get("portable_evidence_bundle_id")
        or portable.occurrence_id != occurrence_row.scientific_occurrence_id
        or occurrence_row.logical_occurrence_id
        != route.logical_occurrence.logical_occurrence_id
        or occurrence_row.route_attempt_id != route.route_attempt.route_attempt_id
        or occurrence_row.decision_point_id != route.decision_point.decision_point_id
        or occurrence_row.owned_partial_result_id != owned.wrapper_id
        or occurrence_row.partial_native_transcript_id
        != owned.transcript.transcript_id
        or occurrence_row.production_runtime_envelope_id != runtime.envelope_id
        or occurrence_row.portable_request_replay_id != request_replay.replay_id
        or cutoff_row.terminal_closure_observation_id
        != occurrence_row.terminal_closure_observation_id
        or transaction.logical_occurrence_id != occurrence_row.logical_occurrence_id
        or transaction.route_attempt_id != occurrence_row.route_attempt_id
        or transaction.decision_point_id != occurrence_row.decision_point_id
        or route.logical_occurrence.rebuild_policy_id
        != campaign_v1.RebuildPolicyV1().rebuild_policy_id
        or derivation_registry.specific_cause != SOURCE_CAUSE
        or derivation_registry.specific_terminal_scope != TERMINAL_SCOPE.value
        or derivation_registry.specific_derived_class != TERMINAL_CLASS.value
        or derivation_registry.specific_derived_code != TERMINAL_CODE.value
    ):
        _fail("source cap, terminal, route, or occurrence identity changed")

    return K7RootCapExhaustionEvidenceV1(
        _CAP_EVIDENCE_ISSUER,
        occurrence.bundle_id,
        occurrence_row.authority_id,
        cutoff_row.authority_id,
        occurrence_row.production_runtime_envelope_id,
        occurrence_row.portable_request_replay_id,
        owned.wrapper_id,
        owned.transcript.transcript_id,
        occurrence_row.transcript_terminal_id,
        occurrence_row.transcript_document_sha256,
        len(occurrence_row.ordered_chain_node_ids),
        occurrence_row.terminal_closure_observation_id,
        occurrence_row.runtime_business_result_id,
        occurrence_row.runtime_business_result_sha256,
        occurrence_row.runtime_business_result_byte_count,
        portable.bundle_id,
        multiround_record.record_id,
        result.result_id,
        closure_record.record_id,
        result.child_closure_id,
        closure_verification_record.record_id,
        result.child_closure_verification_id,
        occurrence_row.logical_occurrence_id,
        route.logical_occurrence.rebuild_policy_id,
        occurrence_row.route_attempt_id,
        occurrence_row.decision_point_id,
        transaction.transaction_id,
        transaction.transaction_index,
        transaction.route_cap_profile_id,
        K7_ROOT_CAP_SEMANTICS_PROFILE_ID_V1,
        derivation_registry.registry_id,
        existing,
        unresolved,
        maximum,
    )


def _issue(
    *,
    formal_materialization_raw: bytes,
    semantic_closure_raw: bytes,
    closure_replay_inputs: Mapping[str, Any],
) -> K7RootCapTerminalAccountingBundleV1:
    try:
        formal = (
            materializer_v1.verify_k7_formal_accounting_materialization_bytes_v1(
                raw=formal_materialization_raw,
                semantic_closure_raw=semantic_closure_raw,
                closure_replay_inputs=closure_replay_inputs,
            )
        )
    except Exception as error:
        raise ConstructionK7RootCapTerminalAuthorityV1Error(
            "complete formal accounting materialization failed replay"
        ) from error
    cap = _derive_root_cap_evidence(
        closure_replay_inputs=closure_replay_inputs,
    )
    vector = formal.work_vector
    comparison = formal.comparison_vector
    proof = formal.actual_projection_proof
    values = vector.values
    closure_context = closure_replay_inputs["occurrence_authority"].occurrence_authority
    if (
        formal.semantic_evidence_closure_id
        != _canonical_object(semantic_closure_raw, "semantic closure").get(
            "semantic_evidence_closure_id"
        )
        or formal.semantic_evidence_closure_context_id
        != _canonical_object(semantic_closure_raw, "semantic closure").get(
            "context", {}
        ).get("semantic_evidence_closure_context_id")
        or formal.semantic_evidence_closure_context_id
        != proof.semantic_evidence_closure_context_id
        or vector.subject_id != cap.logical_occurrence_id
        or vector.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
        or comparison.subject_id != vector.subject_id
        or comparison.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
        or comparison.work_vector_id != vector.work_vector_id
        or len(comparison.values) != EXPECTED_COMPARISON_AXIS_COUNT
        or tuple(axis for axis, _value in comparison.values) != SHARED_AXES
        or len(vector.records) != EXPECTED_COUNTER_RECORD_COUNT
        or (
            values.get("route.attempts"),
            values.get("route.successes"),
            values.get("route.failures"),
        )
        != (1, 0, 1)
        or closure_context.authority_id != cap.occurrence_authority_id
        or closure_context.logical_occurrence_id != cap.logical_occurrence_id
        or closure_context.route_attempt_id != cap.route_attempt_id
        or closure_context.decision_point_id != cap.decision_point_id
    ):
        _fail("formal work and source cap terminal crossed their occurrence")
    terminal = K7AttemptBudgetTerminalAuthorityV1(
        _TERMINAL_AUTHORITY_ISSUER,
        cap,
        formal.bundle_id,
        formal.semantic_evidence_closure_id,
        formal.semantic_evidence_closure_context_id,
        proof.proof_id,
        vector.work_vector_id,
        comparison.comparison_vector_id,
        tuple(row.record_id for row in vector.records),
        values["route.attempts"],
        values["route.successes"],
        values["route.failures"],
    )
    return K7RootCapTerminalAccountingBundleV1(
        _BUNDLE_ISSUER,
        formal,
        cap,
        terminal,
    )


def issue_k7_root_cap_terminal_accounting_bundle_v1(
    *,
    formal_materialization_raw: bytes,
    semantic_closure_raw: bytes,
    closure_replay_inputs: Mapping[str, Any],
) -> K7RootCapTerminalAccountingBundleV1:
    """Derive the attempt terminal from full roots and complete actual work."""

    return _issue(
        formal_materialization_raw=formal_materialization_raw,
        semantic_closure_raw=semantic_closure_raw,
        closure_replay_inputs=closure_replay_inputs,
    )


_BUNDLE_DOCUMENT_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "terminal_scope",
    "terminal_class",
    "terminal_code",
    "specific_cause",
    "formal_accounting_materialization_bundle",
    "root_cap_exhaustion_evidence",
    "attempt_budget_terminal_authority",
    "complete_202_path_work_embedded",
    "id_only_materialization_accepted",
    "worker_terminal_self_report_authoritative",
    "forged_terminal_classification_accepted",
    "incomplete_work_accepted",
    "terminal_is_infeasibility_certificate",
    "plan_certificate",
    "infeasibility_certificate",
    "logical_occurrence_closed",
    "campaign_closure_issued",
    "official_execution_allowed",
    "counter_completeness_gate_passed",
    "workload_economics_gate_passed",
    "official_scalar_cost",
    "official_N_break_even",
    "root_cap_terminal_accounting_bundle_id",
}


def verify_k7_root_cap_terminal_accounting_bundle_bytes_v1(
    *,
    raw: bytes,
    semantic_closure_raw: bytes,
    closure_replay_inputs: Mapping[str, Any],
) -> K7RootCapTerminalAccountingVerificationV1:
    """Recompute the terminal and all work; never trust caller classifications."""

    document = _canonical_object(raw, "K7 root-cap terminal accounting bundle")
    if set(document) != _BUNDLE_DOCUMENT_FIELDS:
        _fail("K7 root-cap terminal bundle field set changed")
    payload = dict(document)
    claimed_id = payload.pop("root_cap_terminal_accounting_bundle_id", None)
    if (
        type(claimed_id) is not str
        or _local_id(
            K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN,
            payload,
        )
        != claimed_id
    ):
        _fail("K7 root-cap terminal bundle content identity changed")
    formal_document = document.get("formal_accounting_materialization_bundle")
    if type(formal_document) is not dict:
        _fail("K7 root-cap terminal requires embedded complete formal work")
    expected = _issue(
        formal_materialization_raw=canonical_json_bytes(formal_document),
        semantic_closure_raw=semantic_closure_raw,
        closure_replay_inputs=closure_replay_inputs,
    )
    if document != expected.to_document():
        _fail("terminal, cap evidence, or preserved formal work differs from replay")
    return K7RootCapTerminalAccountingVerificationV1(
        _VERIFICATION_ISSUER,
        expected,
    )


__all__ = (
    "CAP_RELATION",
    "ConstructionK7RootCapTerminalAuthorityV1Error",
    "EXPECTED_COMPARISON_AXIS_COUNT",
    "EXPECTED_COUNTER_RECORD_COUNT",
    "K7AttemptBudgetTerminalAuthorityV1",
    "K7AttemptTerminalClassV1",
    "K7AttemptTerminalCodeV1",
    "K7AttemptTerminalScopeV1",
    "K7RootCapExhaustionEvidenceV1",
    "K7RootCapTerminalAccountingBundleV1",
    "K7RootCapTerminalAccountingVerificationV1",
    "K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN",
    "K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN",
    "K7_ROOT_CAP_SEMANTICS_PROFILE_ID_V1",
    "K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN",
    "K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN",
    "K7_ROOT_CAP_TERMINAL_ACCOUNTING_VERIFICATION_V1_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SOURCE_CAUSE",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "issue_k7_root_cap_terminal_accounting_bundle_v1",
    "verify_k7_root_cap_terminal_accounting_bundle_bytes_v1",
)
