"""Registered 15-occurrence accounting reconciliation for V0-072.

This authority consumes only the frozen production authority chain, the
context-major 3 x 5 execution plan, exact route-native results, operational
terminal/evaluation artifacts, and the already-computed source reconstruction
replay.  It never accepts caller totals.

The four accounting lanes remain disjoint:

* target online acquisition draws;
* deterministic/independent target replay draws;
* exact evaluation-only work; and
* the unique raw-ID union of the frozen source archive (offline).

Common random numbers are a pairing device only.  They never deduplicate
online draws or operational work across arms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import observation_support_campaign_v1 as source_campaign
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import verified_source_acquisition_archive_v2 as source_archive
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as source_archive_independent,
)
from acfqp import v072_independent_exact_ground_evaluator_v1 as evaluator
from acfqp import v072_registered_adaptive_quotient_runtime_v1 as adaptive
from acfqp import (
    v072_registered_adaptive_quotient_runtime_independent_verifier_v1
    as adaptive_independent,
)
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_registered_cold_h2_orchestrator_v1 as cold_runtime
from acfqp import v072_registered_incremental_epoch_materializer_v1 as incremental
from acfqp import v072_registered_matched_direct_runtime_v1 as direct
from acfqp import v072_registered_operational_terminal_authority_v1 as terminal
from acfqp import v072_source_reconstruction_recipe_v1 as source_recipe
from acfqp import v072_verified_source_archive_component_v1 as source_component


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_campaign_reconciliation_v1"
LOGICAL_OCCURRENCE_DENOMINATOR = 15


DOMAIN_TAGS = {
    "typed_na": "acfqp:v072-registered-reconciliation-typed-na:v1",
    "source_offline": (
        "acfqp:v072-registered-reconciliation-source-offline:v1"
    ),
    "work": "acfqp:v072-registered-reconciliation-occurrence-work:v1",
    "occurrence": "acfqp:v072-registered-reconciliation-occurrence:v1",
    "totals": "acfqp:v072-registered-reconciliation-totals:v1",
    "campaign": "acfqp:v072-registered-campaign-reconciliation:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("registered reconciliation domains must be unique")


class V072RegisteredCampaignReconciliationViolation(ValueError):
    """One identity, terminal, work lane, or denominator is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072RegisteredCampaignReconciliationViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredCampaignReconciliationViolation(
            f"{field_name} is not one canonical content ID"
        ) from error


class RegisteredReconciliationTerminalClassV1(str, Enum):
    PLAN_CERTIFICATE = "PLAN_CERTIFICATE"
    ATTEMPT_CLOSURE_NONCERTIFICATE = "ATTEMPT_CLOSURE_NONCERTIFICATE"


class RegisteredReconciliationScopeV1(str, Enum):
    CONTEXT = "CONTEXT"
    ARM = "ARM"
    CAMPAIGN = "CAMPAIGN"


class RegisteredReconciliationNotApplicableRoleV1(str, Enum):
    OPERATIONAL_PLAN_TERMINAL = "OPERATIONAL_PLAN_TERMINAL"
    EXACT_PLAN_EVALUATION = "EXACT_PLAN_EVALUATION"


_TYPED_NA_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredReconciliationTypedNotApplicableV1:
    """Internally minted absence of plan-only evidence for a noncertificate."""

    _minting_capability: object
    occurrence_id: str
    role: RegisteredReconciliationNotApplicableRoleV1
    terminal_code: str
    reason_code: str = "ROUTE_NATIVE_NONCERTIFICATE"
    _typed_na_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "typed-N/A occurrence")
        if (
            self._minting_capability is not _TYPED_NA_SENTINEL
            or type(self.role) is not RegisteredReconciliationNotApplicableRoleV1
            or self.terminal_code not in prereg.TERMINAL_CODES
            or self.terminal_code == "CONDITIONAL_PLAN_CERTIFICATE"
            or self.reason_code != "ROUTE_NATIVE_NONCERTIFICATE"
        ):
            raise V072RegisteredCampaignReconciliationViolation(
                "noncertificate typed N/A was caller-minted or malformed"
            )
        object.__setattr__(
            self,
            "_typed_na_id",
            _content_id("typed_na", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_reconciliation_typed_na.v1",
            "schema_version": SCHEMA_VERSION,
            "kind": "NOT_APPLICABLE",
            "occurrence_id": self.occurrence_id,
            "role": self.role.value,
            "terminal_code": self.terminal_code,
            "reason_code": self.reason_code,
            "caller_supplied": False,
        }

    @property
    def typed_na_id(self) -> str:
        return self._typed_na_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "typed_na_id": self.typed_na_id}


@dataclass(frozen=True, slots=True)
class RegisteredSourceOfflineAccountingV1:
    """The exact source-campaign raw-ID union, charged once and offline."""

    source_recipe_id: str
    source_campaign_id: str
    source_campaign_verification_id: str
    source_archive_id: str
    production_archive_verification_id: str
    independent_archive_attestation_id: str
    source_component_id: str
    physical_raw_observation_ids: tuple[str, ...]
    unique_physical_raw_draws: int
    online_draws_charged: int = 0
    lane: str = "SOURCE_ARCHIVE_OFFLINE"
    _accounting_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_recipe_id, "source recipe"),
            (self.source_campaign_id, "source campaign"),
            (
                self.source_campaign_verification_id,
                "source campaign verification",
            ),
            (self.source_archive_id, "source archive"),
            (
                self.production_archive_verification_id,
                "production archive verification",
            ),
            (
                self.independent_archive_attestation_id,
                "independent archive attestation",
            ),
            (self.source_component_id, "source archive component"),
            *(
                (item, "source raw observation")
                for item in self.physical_raw_observation_ids
            ),
        ):
            _cid(value, label)
        if (
            self.physical_raw_observation_ids
            != tuple(sorted(set(self.physical_raw_observation_ids)))
            or self.unique_physical_raw_draws
            != len(self.physical_raw_observation_ids)
            or self.unique_physical_raw_draws <= 0
            or self.online_draws_charged != 0
            or self.lane != "SOURCE_ARCHIVE_OFFLINE"
        ):
            raise V072RegisteredCampaignReconciliationViolation(
                "source offline raw-ID accounting is incomplete or mixed online"
            )
        object.__setattr__(
            self,
            "_accounting_id",
            _content_id("source_offline", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_source_offline_accounting.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "source_recipe_id": self.source_recipe_id,
            "source_campaign_id": self.source_campaign_id,
            "source_campaign_verification_id": (
                self.source_campaign_verification_id
            ),
            "source_archive_id": self.source_archive_id,
            "production_archive_verification_id": (
                self.production_archive_verification_id
            ),
            "independent_archive_attestation_id": (
                self.independent_archive_attestation_id
            ),
            "source_component_id": self.source_component_id,
            "physical_raw_observation_ids": list(
                self.physical_raw_observation_ids
            ),
            "unique_physical_raw_draws": self.unique_physical_raw_draws,
            "online_draws_charged": 0,
            "lane": "SOURCE_ARCHIVE_OFFLINE",
            "union_not_cumulative_prefix_sum": True,
        }

    @property
    def accounting_id(self) -> str:
        return self._accounting_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_id": self.accounting_id}


@dataclass(frozen=True, slots=True)
class RegisteredOccurrenceLaneAccountingV1:
    """Native per-occurrence work with strictly separated accounting lanes."""

    occurrence_id: str
    route_kind: consumer.RegisteredRouteKindV1
    operational_route_work_id: str
    runtime_independent_verification_id: str
    online_acquisition_draws: int
    target_replay_draws: int
    exact_evaluation_work_id: str | None
    exact_evaluation_atom_calls: int
    exact_evaluation_rows: int
    exact_evaluation_atoms: int
    exact_evaluation_candidate_extensions: int
    exact_evaluation_dominance_comparisons: int
    exact_evaluation_frontier_points: int
    exact_evaluation_policy_assignments: int
    source_offline_draws: int = 0
    crn_discount_draws: int = 0
    _accounting_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "work occurrence"),
            (self.operational_route_work_id, "operational route work"),
            (
                self.runtime_independent_verification_id,
                "runtime independent verification",
            ),
        ):
            _cid(value, label)
        if self.exact_evaluation_work_id is not None:
            _cid(self.exact_evaluation_work_id, "exact evaluation work")
        numeric_names = (
            "online_acquisition_draws",
            "target_replay_draws",
            "exact_evaluation_atom_calls",
            "exact_evaluation_rows",
            "exact_evaluation_atoms",
            "exact_evaluation_candidate_extensions",
            "exact_evaluation_dominance_comparisons",
            "exact_evaluation_frontier_points",
            "exact_evaluation_policy_assignments",
            "source_offline_draws",
            "crn_discount_draws",
        )
        evaluation_values = tuple(
            getattr(self, name)
            for name in numeric_names
            if name.startswith("exact_evaluation_")
        )
        if (
            type(self.route_kind) is not consumer.RegisteredRouteKindV1
            or any(
                type(getattr(self, name)) is not int
                or getattr(self, name) < 0
                for name in numeric_names
            )
            or self.online_acquisition_draws <= 0
            or self.target_replay_draws <= 0
            or self.source_offline_draws != 0
            or self.crn_discount_draws != 0
            or (
                self.exact_evaluation_work_id is None
                and any(evaluation_values)
            )
            or (
                self.exact_evaluation_work_id is not None
                and (
                    self.exact_evaluation_atom_calls <= 0
                    or self.exact_evaluation_rows <= 0
                    or self.exact_evaluation_atoms
                    < self.exact_evaluation_rows
                    or self.exact_evaluation_candidate_extensions <= 0
                    or self.exact_evaluation_frontier_points <= 0
                    or self.exact_evaluation_policy_assignments <= 0
                )
            )
        ):
            raise V072RegisteredCampaignReconciliationViolation(
                "occurrence work lanes are missing, discounted, or mixed"
            )
        object.__setattr__(
            self,
            "_accounting_id",
            _content_id("work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_occurrence_lane_accounting.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "route_kind": self.route_kind.value,
            "operational_route_work_id": self.operational_route_work_id,
            "runtime_independent_verification_id": (
                self.runtime_independent_verification_id
            ),
            "online_acquisition_draws": self.online_acquisition_draws,
            "target_replay_draws": self.target_replay_draws,
            "exact_evaluation_work_id": self.exact_evaluation_work_id,
            "exact_evaluation_atom_calls": (
                self.exact_evaluation_atom_calls
            ),
            "exact_evaluation_rows": self.exact_evaluation_rows,
            "exact_evaluation_atoms": self.exact_evaluation_atoms,
            "exact_evaluation_candidate_extensions": (
                self.exact_evaluation_candidate_extensions
            ),
            "exact_evaluation_dominance_comparisons": (
                self.exact_evaluation_dominance_comparisons
            ),
            "exact_evaluation_frontier_points": (
                self.exact_evaluation_frontier_points
            ),
            "exact_evaluation_policy_assignments": (
                self.exact_evaluation_policy_assignments
            ),
            "source_offline_draws": 0,
            "crn_discount_draws": 0,
            "online_replay_evaluation_source_lanes_separate": True,
        }

    @property
    def accounting_id(self) -> str:
        return self._accounting_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_id": self.accounting_id}


RouteResultV1 = (
    adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1
    | direct.RegisteredMatchedDirectOccurrenceResultV1
)
RuntimeVerificationV1 = (
    adaptive_independent.RegisteredAdaptiveRuntimeIndependentVerificationV1
    | direct.RegisteredMatchedDirectOccurrenceIndependentVerificationV1
)


@dataclass(frozen=True, slots=True)
class RegisteredReconciledOccurrenceV1:
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1
    route_result: RouteResultV1
    runtime_verification: RuntimeVerificationV1
    terminal_class: RegisteredReconciliationTerminalClassV1
    terminal_code: str
    final_model_epoch_id: str
    final_planner_model_id: str
    operational_terminal_authority: (
        terminal.RegisteredOperationalTerminalAuthorityResultV1 | None
    )
    exact_evaluation: (
        evaluator.RegisteredIndependentExactGroundEvaluationResultV1 | None
    )
    terminal_not_applicable: (
        RegisteredReconciliationTypedNotApplicableV1 | None
    )
    evaluation_not_applicable: (
        RegisteredReconciliationTypedNotApplicableV1 | None
    )
    work: RegisteredOccurrenceLaneAccountingV1
    _occurrence_record_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.final_model_epoch_id, "final model epoch"),
            (self.final_planner_model_id, "final planner model"),
        ):
            _cid(value, label)
        certified = (
            self.terminal_class
            is RegisteredReconciliationTerminalClassV1.PLAN_CERTIFICATE
        )
        if (
            type(self.occurrence_plan)
            is not consumer.RegisteredOccurrenceExecutionPlanV1
            or type(self.terminal_class)
            is not RegisteredReconciliationTerminalClassV1
            or self.terminal_code not in prereg.TERMINAL_CODES
            or type(self.work) is not RegisteredOccurrenceLaneAccountingV1
            or self.work.occurrence_id != self.occurrence_plan.occurrence_id
            or self.work.route_kind is not self.occurrence_plan.template.route_kind
            or certified
            != (self.terminal_code == "CONDITIONAL_PLAN_CERTIFICATE")
            or (
                certified
                and (
                    type(self.operational_terminal_authority)
                    is not terminal.RegisteredOperationalTerminalAuthorityResultV1
                    or type(self.exact_evaluation)
                    is not evaluator.RegisteredIndependentExactGroundEvaluationResultV1
                    or self.terminal_not_applicable is not None
                    or self.evaluation_not_applicable is not None
                )
            )
            or (
                not certified
                and (
                    self.operational_terminal_authority is not None
                    or self.exact_evaluation is not None
                    or type(self.terminal_not_applicable)
                    is not RegisteredReconciliationTypedNotApplicableV1
                    or type(self.evaluation_not_applicable)
                    is not RegisteredReconciliationTypedNotApplicableV1
                    or self.terminal_not_applicable.occurrence_id
                    != self.occurrence_plan.occurrence_id
                    or self.evaluation_not_applicable.occurrence_id
                    != self.occurrence_plan.occurrence_id
                    or self.terminal_not_applicable.terminal_code
                    != self.terminal_code
                    or self.evaluation_not_applicable.terminal_code
                    != self.terminal_code
                )
            )
        ):
            raise V072RegisteredCampaignReconciliationViolation(
                "reconciled occurrence terminal/evaluation binding is invalid"
            )
        object.__setattr__(
            self,
            "_occurrence_record_id",
            _content_id("occurrence", self._payload()),
        )

    @property
    def route_result_id(self) -> str:
        if type(self.route_result) is adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1:
            return self.route_result.verified_result_id
        if type(self.route_result) is direct.RegisteredMatchedDirectOccurrenceResultV1:
            return self.route_result.result_id
        raise V072RegisteredCampaignReconciliationViolation(
            "reconciled occurrence has a foreign route result"
        )

    @property
    def runtime_verification_id(self) -> str:
        if type(self.runtime_verification) is (
            adaptive_independent.RegisteredAdaptiveRuntimeIndependentVerificationV1
        ):
            return self.runtime_verification.verification_id
        if type(self.runtime_verification) is (
            direct.RegisteredMatchedDirectOccurrenceIndependentVerificationV1
        ):
            return self.runtime_verification.verification_id
        raise V072RegisteredCampaignReconciliationViolation(
            "reconciled occurrence has a foreign runtime verification"
        )

    @property
    def operational_terminal_id(self) -> str | None:
        if self.operational_terminal_authority is None:
            return None
        return (
            self.operational_terminal_authority.evaluator_bundle
            .operational_terminal.terminal_id
        )

    @property
    def selected_policy_id(self) -> str | None:
        if self.operational_terminal_authority is None:
            return None
        return (
            self.operational_terminal_authority.evaluator_bundle
            .selected_policy.selected_policy_id
        )

    @property
    def exact_evaluation_result_id(self) -> str | None:
        return (
            None
            if self.exact_evaluation is None
            else self.exact_evaluation.result_id
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_reconciled_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_plan.occurrence_id,
            "occurrence_ordinal": (
                self.occurrence_plan.template.occurrence_ordinal
            ),
            "context_id": self.occurrence_plan.template.context_id,
            "context_key": self.occurrence_plan.template.context_key,
            "arm": self.occurrence_plan.template.arm,
            "route_kind": self.occurrence_plan.template.route_kind.value,
            "route_result_id": self.route_result_id,
            "runtime_verification_id": self.runtime_verification_id,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code,
            "final_model_epoch_id": self.final_model_epoch_id,
            "final_planner_model_id": self.final_planner_model_id,
            "operational_terminal_authority_result_id": (
                None
                if self.operational_terminal_authority is None
                else self.operational_terminal_authority.authority_result_id
            ),
            "operational_terminal_id": self.operational_terminal_id,
            "selected_policy_id": self.selected_policy_id,
            "exact_evaluation_result_id": self.exact_evaluation_result_id,
            "terminal_not_applicable_id": (
                None
                if self.terminal_not_applicable is None
                else self.terminal_not_applicable.typed_na_id
            ),
            "evaluation_not_applicable_id": (
                None
                if self.evaluation_not_applicable is None
                else self.evaluation_not_applicable.typed_na_id
            ),
            "work_accounting_id": self.work.accounting_id,
            "replacement_allowed": False,
            "crn_draw_discount": 0,
        }

    @property
    def occurrence_record_id(self) -> str:
        return self._occurrence_record_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "route_result": self.route_result.to_document(),
            "runtime_verification": self.runtime_verification.to_document(),
            "operational_terminal_authority": (
                None
                if self.operational_terminal_authority is None
                else {
                    "authority_result_id": (
                        self.operational_terminal_authority.authority_result_id
                    ),
                    "evaluator_bundle": (
                        self.operational_terminal_authority.evaluator_bundle
                        .to_document()
                    ),
                }
            ),
            "exact_evaluation": (
                None
                if self.exact_evaluation is None
                else self.exact_evaluation.to_document()
            ),
            "terminal_not_applicable": (
                None
                if self.terminal_not_applicable is None
                else self.terminal_not_applicable.to_document()
            ),
            "evaluation_not_applicable": (
                None
                if self.evaluation_not_applicable is None
                else self.evaluation_not_applicable.to_document()
            ),
            "work": self.work.to_document(),
            "occurrence_record_id": self.occurrence_record_id,
        }


@dataclass(frozen=True, slots=True)
class RegisteredReconciliationTotalsV1:
    scope: RegisteredReconciliationScopeV1
    scope_key: str
    occurrence_record_ids: tuple[str, ...]
    online_acquisition_draws: int
    target_replay_draws: int
    exact_evaluation_atom_calls: int
    exact_evaluation_rows: int
    exact_evaluation_atoms: int
    exact_evaluation_candidate_extensions: int
    exact_evaluation_dominance_comparisons: int
    exact_evaluation_frontier_points: int
    exact_evaluation_policy_assignments: int
    plan_certificate_count: int
    noncertificate_count: int
    crn_discount_draws: int = 0
    _totals_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in self.occurrence_record_ids:
            _cid(value, "totals occurrence")
        numeric_names = tuple(
            name
            for name in self.__dataclass_fields__
            if name
            not in (
                "scope",
                "scope_key",
                "occurrence_record_ids",
                "_totals_id",
            )
        )
        expected_size = {
            RegisteredReconciliationScopeV1.CONTEXT: len(prereg.ARM_ORDER),
            RegisteredReconciliationScopeV1.ARM: len(
                prereg.registered_heldout_public_contexts_v2()
            ),
            RegisteredReconciliationScopeV1.CAMPAIGN: (
                LOGICAL_OCCURRENCE_DENOMINATOR
            ),
        }.get(self.scope)
        if (
            type(self.scope) is not RegisteredReconciliationScopeV1
            or type(self.scope_key) is not str
            or not self.scope_key
            or type(self.occurrence_record_ids) is not tuple
            or len(self.occurrence_record_ids) != expected_size
            or len(set(self.occurrence_record_ids))
            != len(self.occurrence_record_ids)
            or any(
                type(getattr(self, name)) is not int
                or getattr(self, name) < 0
                for name in numeric_names
            )
            or self.plan_certificate_count + self.noncertificate_count
            != len(self.occurrence_record_ids)
            or self.crn_discount_draws != 0
        ):
            raise V072RegisteredCampaignReconciliationViolation(
                "context/arm/campaign totals are malformed or discounted"
            )
        object.__setattr__(
            self,
            "_totals_id",
            _content_id("totals", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_reconciliation_totals.v1",
            "schema_version": SCHEMA_VERSION,
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "occurrence_record_ids": list(self.occurrence_record_ids),
            "online_acquisition_draws": self.online_acquisition_draws,
            "target_replay_draws": self.target_replay_draws,
            "exact_evaluation_atom_calls": (
                self.exact_evaluation_atom_calls
            ),
            "exact_evaluation_rows": self.exact_evaluation_rows,
            "exact_evaluation_atoms": self.exact_evaluation_atoms,
            "exact_evaluation_candidate_extensions": (
                self.exact_evaluation_candidate_extensions
            ),
            "exact_evaluation_dominance_comparisons": (
                self.exact_evaluation_dominance_comparisons
            ),
            "exact_evaluation_frontier_points": (
                self.exact_evaluation_frontier_points
            ),
            "exact_evaluation_policy_assignments": (
                self.exact_evaluation_policy_assignments
            ),
            "plan_certificate_count": self.plan_certificate_count,
            "noncertificate_count": self.noncertificate_count,
            "crn_discount_draws": 0,
            "source_offline_draws_included": False,
        }

    @property
    def totals_id(self) -> str:
        return self._totals_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "totals_id": self.totals_id}


@dataclass(frozen=True, slots=True)
class RegisteredCampaignReconciliationV1:
    authority_chain_id: str
    anchor_id: str
    source_reconstruction_recipe_id: str
    manifest_id: str
    final_preregistration_id: str
    execution_plan: consumer.RegisteredCampaignExecutionPlanV1
    source_offline: RegisteredSourceOfflineAccountingV1
    occurrences: tuple[RegisteredReconciledOccurrenceV1, ...]
    context_totals: tuple[RegisteredReconciliationTotalsV1, ...]
    arm_totals: tuple[RegisteredReconciliationTotalsV1, ...]
    campaign_totals: RegisteredReconciliationTotalsV1
    logical_occurrence_denominator: int = LOGICAL_OCCURRENCE_DENOMINATOR
    endpoint_claimed: bool = False
    sample_efficiency_gate_status: str = "NOT_RUN"
    _reconciliation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authority_chain_id, "campaign authority chain"),
            (self.anchor_id, "campaign anchor"),
            (
                self.source_reconstruction_recipe_id,
                "source reconstruction recipe",
            ),
            (self.manifest_id, "campaign manifest"),
            (self.final_preregistration_id, "final preregistration"),
        ):
            _cid(value, label)
        if (
            type(self.execution_plan)
            is not consumer.RegisteredCampaignExecutionPlanV1
            or self.execution_plan.authority_chain_id
            != self.authority_chain_id
            or type(self.source_offline)
            is not RegisteredSourceOfflineAccountingV1
            or self.source_offline.source_recipe_id
            != self.source_reconstruction_recipe_id
            or type(self.occurrences) is not tuple
            or len(self.occurrences) != LOGICAL_OCCURRENCE_DENOMINATOR
            or any(
                type(item) is not RegisteredReconciledOccurrenceV1
                for item in self.occurrences
            )
            or tuple(item.occurrence_plan for item in self.occurrences)
            != self.execution_plan.occurrences
            or len({item.route_result_id for item in self.occurrences})
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or len(
                {
                    item.runtime_verification_id
                    for item in self.occurrences
                }
            )
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or type(self.context_totals) is not tuple
            or len(self.context_totals)
            != len(prereg.registered_heldout_public_contexts_v2())
            or type(self.arm_totals) is not tuple
            or len(self.arm_totals) != len(prereg.ARM_ORDER)
            or type(self.campaign_totals)
            is not RegisteredReconciliationTotalsV1
            or self.campaign_totals.scope
            is not RegisteredReconciliationScopeV1.CAMPAIGN
            or self.logical_occurrence_denominator
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or self.campaign_totals.plan_certificate_count
            + self.campaign_totals.noncertificate_count
            != self.logical_occurrence_denominator
            or self.endpoint_claimed is not False
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            raise V072RegisteredCampaignReconciliationViolation(
                "registered 15-occurrence reconciliation is incomplete"
            )
        object.__setattr__(
            self,
            "_reconciliation_id",
            _content_id("campaign", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_campaign_reconciliation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "source_reconstruction_recipe_id": (
                self.source_reconstruction_recipe_id
            ),
            "manifest_id": self.manifest_id,
            "final_preregistration_id": self.final_preregistration_id,
            "execution_plan_id": self.execution_plan.plan_id,
            "source_offline_accounting_id": (
                self.source_offline.accounting_id
            ),
            "occurrence_record_ids": [
                item.occurrence_record_id for item in self.occurrences
            ],
            "context_totals_ids": [
                item.totals_id for item in self.context_totals
            ],
            "arm_totals_ids": [
                item.totals_id for item in self.arm_totals
            ],
            "campaign_totals_id": self.campaign_totals.totals_id,
            "logical_occurrence_denominator": 15,
            "all_occurrences_retained": True,
            "replacement_allowed": False,
            "campaign_early_stop_allowed": False,
            "crn_draw_discount": 0,
            "source_offline_in_online_totals": False,
            "endpoint_claimed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
        }

    @property
    def reconciliation_id(self) -> str:
        return self._reconciliation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_offline": self.source_offline.to_document(),
            "occurrences": [item.to_document() for item in self.occurrences],
            "context_totals": [
                item.to_document() for item in self.context_totals
            ],
            "arm_totals": [item.to_document() for item in self.arm_totals],
            "campaign_totals": self.campaign_totals.to_document(),
            "reconciliation_id": self.reconciliation_id,
        }


def _expected_execution_plan(
    chain_id: str,
) -> consumer.RegisteredCampaignExecutionPlanV1:
    return consumer.RegisteredCampaignExecutionPlanV1(
        chain_id,
        tuple(
            consumer.RegisteredOccurrenceExecutionPlanV1(chain_id, template)
            for template in consumer.registered_occurrence_templates_v1()
        ),
    )


def _validate_source_replay(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    source_reconstruction_replay: source_recipe.SourceReconstructionReplayV1,
) -> RegisteredSourceOfflineAccountingV1:
    if type(source_reconstruction_replay) is not source_recipe.SourceReconstructionReplayV1:
        raise V072RegisteredCampaignReconciliationViolation(
            "source offline accounting requires the exact reconstruction replay"
        )
    replay = source_reconstruction_replay
    manifest_bindings = authority_chain.manifest.global_bindings
    if (
        replay.recipe_id
        != manifest_bindings["source_reconstruction_recipe_id"]
        or type(replay.source_campaign)
        is not source_campaign.ObservationSupportCampaignV1
        or type(replay.source_verification)
        is not source_campaign.ObservationSupportCampaignVerificationV1
        or type(replay.archive)
        is not source_archive.VerifiedSourceAcquisitionArchiveV2
        or type(replay.production_verification)
        is not source_archive.VerifiedSourceAcquisitionArchiveVerificationV2
        or type(replay.independent_attestation)
        is not source_archive_independent.IndependentSourceAcquisitionArchiveVerificationV2
        or type(replay.component)
        is not source_component.V072VerifiedSourceArchiveComponentV1
        or replay.source_verification.campaign_id
        != replay.source_campaign.campaign_id
        or replay.source_verification.replayed_campaign_id
        != replay.source_campaign.campaign_id
        or replay.archive.source_campaign_id
        != replay.source_campaign.campaign_id
        or replay.archive.source_campaign_verification_id
        != replay.source_verification.verification_id
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "source reconstruction replay is stale or structurally incomplete"
        )
    replayed_production = (
        source_archive.verify_verified_source_acquisition_archive_v2(
            source_campaign=replay.source_campaign,
            source_verification=replay.source_verification,
            claimed=replay.archive,
        )
    )
    replayed_independent = (
        source_archive_independent
        .verify_source_acquisition_archive_independently_v2(
            source_campaign=replay.source_campaign,
            source_verification=replay.source_verification,
            claimed=replay.archive,
        )
    )
    replayed_component = (
        source_component.bind_v072_verified_source_archive_component_v1(
            archive=replay.archive,
            production_verification=replayed_production,
            independent_attestation=replayed_independent,
        )
    )
    if (
        replayed_production != replay.production_verification
        or replayed_independent != replay.independent_attestation
        or replayed_component != replay.component
        or manifest_bindings["source_archive_id"] != replay.archive.archive_id
        or manifest_bindings[
            "source_archive_verification_attestation_id"
        ]
        != replay.independent_attestation.verification_id
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "source archive production/independent/component chain differs"
        )
    raw_ids = tuple(
        sorted(
            {
                raw_id
                for context_result in replay.source_campaign.context_results
                for raw_id in (
                    context_result.accounting
                    .physical_unique_observation_ids
                )
            }
        )
    )
    if (
        len(raw_ids) != replay.source_campaign.physical_unique_observer_draws
        or len(raw_ids)
        != replay.source_campaign.counters.physical_unique_observer_draws
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "source campaign raw-ID union differs from native source counters"
        )
    return RegisteredSourceOfflineAccountingV1(
        replay.recipe_id,
        replay.source_campaign.campaign_id,
        replay.source_verification.verification_id,
        replay.archive.archive_id,
        replay.production_verification.verification_id,
        replay.independent_attestation.verification_id,
        replay.component.component_id,
        raw_ids,
        len(raw_ids),
    )


def _expected_evaluator_occurrence(
    *,
    anchor_id: str,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
) -> evaluator.RegisteredOccurrenceIdentityV1:
    template = plan.template
    return evaluator.RegisteredOccurrenceIdentityV1(
        anchor_id,
        template.context_id,
        template.context_key,
        template.arm,
        template.context_ordinal,
        template.arm_ordinal,
        template.occurrence_ordinal,
    )


def _evaluation_work_values(
    value: evaluator.RegisteredIndependentExactGroundEvaluationResultV1 | None,
) -> tuple[str | None, int, int, int, int, int, int, int]:
    if value is None:
        return (None, 0, 0, 0, 0, 0, 0, 0)
    work = value.work
    return (
        work.work_id,
        work.evaluation_exact_atom_api_calls,
        work.exact_rows_reconstructed,
        work.exact_atoms_reconstructed,
        work.dp_candidate_extensions,
        work.dp_dominance_comparisons,
        work.dp_frontier_points_retained,
        work.selected_policy_assignments_checked,
    )


def _validate_certified_terminal_and_evaluation(
    *,
    anchor_id: str,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    operational_result_artifact_id: str,
    runtime_verification_id: str,
    operational_terminal_authority: Any,
    exact_evaluation: Any,
) -> tuple[
    terminal.RegisteredOperationalTerminalAuthorityResultV1,
    evaluator.RegisteredIndependentExactGroundEvaluationResultV1,
]:
    if (
        type(operational_terminal_authority)
        is not terminal.RegisteredOperationalTerminalAuthorityResultV1
        or type(exact_evaluation)
        is not evaluator.RegisteredIndependentExactGroundEvaluationResultV1
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "certified route lacks exact terminal authority/evaluation"
        )
    authority = operational_terminal_authority
    bundle = authority.evaluator_bundle
    operational_terminal = bundle.operational_terminal
    selected_policy = bundle.selected_policy
    expected_occurrence = _expected_evaluator_occurrence(
        anchor_id=anchor_id,
        plan=plan,
    )
    selected_runtime_verification = getattr(
        selected_policy,
        "independent_runtime_verification_id",
        runtime_verification_id,
    )
    selected_route_kind = getattr(
        selected_policy,
        "route_kind",
        plan.template.route_kind.value,
    )
    if (
        operational_terminal.occurrence != expected_occurrence
        or selected_policy.occurrence != expected_occurrence
        or operational_terminal.terminal_code
        != "CONDITIONAL_PLAN_CERTIFICATE"
        or operational_terminal.operational_result_artifact_id
        != operational_result_artifact_id
        or selected_policy.operational_policy_source_artifact_id
        != operational_result_artifact_id
        or selected_runtime_verification != runtime_verification_id
        or selected_route_kind != plan.template.route_kind.value
        or operational_terminal.selected_policy_id
        != selected_policy.selected_policy_id
        or exact_evaluation.anchor_id != anchor_id
        or exact_evaluation.occurrence != expected_occurrence
        or exact_evaluation.operational_terminal_id
        != operational_terminal.terminal_id
        or exact_evaluation.operational_selected_policy_id
        != selected_policy.selected_policy_id
        or exact_evaluation.status
        is not (
            evaluator.RegisteredExactGroundEvaluationStatusV1
            .CERTIFICATE_METRICS_PASS
        )
        or exact_evaluation.certificate_metrics_pass is not True
        or exact_evaluation.execution_lane != evaluator.EVALUATION_LANE
        or exact_evaluation.operational_work_included is not False
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "terminal/policy/evaluation identity or exact metrics differ"
        )
    return authority, exact_evaluation


_ADAPTIVE_TERMINAL_CODES = {
    adaptive.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED: (
        "CONDITIONAL_PLAN_CERTIFICATE"
    ),
    adaptive.RegisteredAdaptiveOccurrenceStatusV1.EXACT_DP_RESOURCE_EXHAUSTED: (
        "EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE"
    ),
    adaptive.RegisteredAdaptiveOccurrenceStatusV1.NO_SOUND_COVER: (
        "NO_POSITIVE_GAIN_NONCERTIFICATE"
    ),
    adaptive.RegisteredAdaptiveOccurrenceStatusV1.ACQUISITION_CAP_EXHAUSTED: (
        "INCREMENTAL_CAP_EXHAUSTED_NONCERTIFICATE"
    ),
    adaptive.RegisteredAdaptiveOccurrenceStatusV1.NOT_CERTIFIED_MAX_ROUNDS: (
        "TWO_ROUND_CAP_EXHAUSTED_NONCERTIFICATE"
    ),
}


def _adaptive_occurrence(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor_id: str,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
    route_result: Any,
    operational_terminal_authority: Any,
    exact_evaluation: Any,
) -> RegisteredReconciledOccurrenceV1:
    if type(route_result) is not adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1:
        raise V072RegisteredCampaignReconciliationViolation(
            "adaptive schedule entry has a foreign route result"
        )
    execution = route_result.execution
    replayed = adaptive_independent.verify_registered_adaptive_runtime_independently_v1(
        authority_chain=authority_chain,
        anchor=authority_chain.remote_main_anchor,
        occurrence_plan=plan,
        context=context,
        claimed=execution,
    )
    if (
        replayed != route_result.independent_verification
        or execution.authority_chain_id != authority_chain.chain_id
        or execution.anchor_id != anchor_id
        or execution.occurrence_plan != plan
        or execution.context != context
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "adaptive runtime result or independent replay was transplanted"
        )
    terminal_code = _ADAPTIVE_TERMINAL_CODES[execution.status]
    certified = execution.status is adaptive.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
    final_epoch = execution.epochs[-1]
    if type(final_epoch) is cold_runtime.RegisteredColdH2ModelEpochV1:
        acquisitions = final_epoch.acquisitions
    elif type(final_epoch) is incremental.RegisteredIncrementalH2ModelEpochV1:
        acquisitions = final_epoch.acquisition_history
    else:  # pragma: no cover - execution type already guards this
        raise V072RegisteredCampaignReconciliationViolation(
            "adaptive final model epoch has a foreign type"
        )
    producer_draws = sum(
        len(item.transcript.entries) for item in acquisitions
    )
    if (
        len({item.acquisition_id for item in acquisitions}) != len(acquisitions)
        or producer_draws != execution.work.producer_draw_calls
        or producer_draws
        != execution.work.unique_online_sample_evidence_draws
        or execution.work.total_observer_draw_calls
        != producer_draws + execution.work.replay_draw_calls
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "adaptive cold/failed/incremental target draws were omitted"
        )
    operational_artifact_id = execution.result_id
    if certified:
        authority, evaluation = _validate_certified_terminal_and_evaluation(
            anchor_id=anchor_id,
            plan=plan,
            operational_result_artifact_id=operational_artifact_id,
            runtime_verification_id=replayed.verification_id,
            operational_terminal_authority=operational_terminal_authority,
            exact_evaluation=exact_evaluation,
        )
        terminal_na = None
        evaluation_na = None
    else:
        if operational_terminal_authority is not None or exact_evaluation is not None:
            raise V072RegisteredCampaignReconciliationViolation(
                "noncertificate adaptive route received plan-only evidence"
            )
        authority = None
        evaluation = None
        terminal_na = RegisteredReconciliationTypedNotApplicableV1(
            _TYPED_NA_SENTINEL,
            plan.occurrence_id,
            RegisteredReconciliationNotApplicableRoleV1.OPERATIONAL_PLAN_TERMINAL,
            terminal_code,
        )
        evaluation_na = RegisteredReconciliationTypedNotApplicableV1(
            _TYPED_NA_SENTINEL,
            plan.occurrence_id,
            RegisteredReconciliationNotApplicableRoleV1.EXACT_PLAN_EVALUATION,
            terminal_code,
        )
    evaluation_values = _evaluation_work_values(evaluation)
    work = RegisteredOccurrenceLaneAccountingV1(
        plan.occurrence_id,
        plan.template.route_kind,
        execution.work.work_id,
        replayed.verification_id,
        producer_draws,
        execution.work.replay_draw_calls,
        *evaluation_values,
    )
    final_pair = final_epoch.model_pair
    return RegisteredReconciledOccurrenceV1(
        plan,
        route_result,
        replayed,
        (
            RegisteredReconciliationTerminalClassV1.PLAN_CERTIFICATE
            if certified
            else RegisteredReconciliationTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
        terminal_code,
        final_epoch.epoch_id,
        final_pair.quotient_planner_model.model_id,
        authority,
        evaluation,
        terminal_na,
        evaluation_na,
        work,
    )


def _direct_occurrence(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor_id: str,
    final_preregistration_id: str,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
    route_result: Any,
    operational_terminal_authority: Any,
    exact_evaluation: Any,
) -> RegisteredReconciledOccurrenceV1:
    if type(route_result) is not direct.RegisteredMatchedDirectOccurrenceResultV1:
        raise V072RegisteredCampaignReconciliationViolation(
            "direct schedule entry has a foreign route result"
        )
    try:
        canonical_direct_plan = (
            direct.registered_matched_direct_occurrence_plan_v1(
                anchor=authority_chain.remote_main_anchor,
                context=context,
            )
        )
    except (ValueError, RuntimeError) as error:
        raise V072RegisteredCampaignReconciliationViolation(
            "canonical matched-direct occurrence plan replay failed"
        ) from error
    template = plan.template
    if (
        type(canonical_direct_plan)
        is not direct.RegisteredMatchedDirectOccurrencePlanV1
        or canonical_direct_plan.anchor_id != anchor_id
        or canonical_direct_plan.context_id != template.context_id
        or canonical_direct_plan.context_key != template.context_key
        or canonical_direct_plan.context_ordinal != template.context_ordinal
        or canonical_direct_plan.arm != template.arm
        or canonical_direct_plan.arm_ordinal != template.arm_ordinal
        or canonical_direct_plan.occurrence_ordinal
        != template.occurrence_ordinal
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "canonical direct plan is outside the consumer schedule position"
        )
    replayed = direct.verify_registered_matched_direct_occurrence_result_v1(
        route_result
    )
    if (
        route_result.authority_chain_id != authority_chain.chain_id
        or route_result.anchor_id != anchor_id
        or route_result.final_preregistration_id != final_preregistration_id
        or route_result.occurrence_plan_id != canonical_direct_plan.plan_id
        or route_result.context_id != context.context_id
        or route_result.crn_draw_discount != 0
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "matched-direct runtime result was reused or transplanted"
        )
    terminal_code = route_result.terminal_code.value
    if terminal_code not in prereg.TERMINAL_CODES:
        raise V072RegisteredCampaignReconciliationViolation(
            "matched-direct terminal code is outside preregistration"
        )
    certified = route_result.certified
    operational_artifact_id = route_result.result_id
    if certified:
        authority, evaluation = _validate_certified_terminal_and_evaluation(
            anchor_id=anchor_id,
            plan=plan,
            operational_result_artifact_id=operational_artifact_id,
            runtime_verification_id=replayed.verification_id,
            operational_terminal_authority=operational_terminal_authority,
            exact_evaluation=exact_evaluation,
        )
        terminal_na = None
        evaluation_na = None
    else:
        if operational_terminal_authority is not None or exact_evaluation is not None:
            raise V072RegisteredCampaignReconciliationViolation(
                "noncertificate direct route received plan-only evidence"
            )
        authority = None
        evaluation = None
        terminal_na = RegisteredReconciliationTypedNotApplicableV1(
            _TYPED_NA_SENTINEL,
            plan.occurrence_id,
            RegisteredReconciliationNotApplicableRoleV1.OPERATIONAL_PLAN_TERMINAL,
            terminal_code,
        )
        evaluation_na = RegisteredReconciliationTypedNotApplicableV1(
            _TYPED_NA_SENTINEL,
            plan.occurrence_id,
            RegisteredReconciliationNotApplicableRoleV1.EXACT_PLAN_EVALUATION,
            terminal_code,
        )
    evaluation_values = _evaluation_work_values(evaluation)
    final_checkpoint = route_result.checkpoint_records[-1].inventory_checkpoint
    work = RegisteredOccurrenceLaneAccountingV1(
        plan.occurrence_id,
        plan.template.route_kind,
        final_checkpoint.work.work_id,
        replayed.verification_id,
        route_result.acquisition_sample_total,
        route_result.deterministic_verifier_replay_total,
        *evaluation_values,
    )
    return RegisteredReconciledOccurrenceV1(
        plan,
        route_result,
        replayed,
        (
            RegisteredReconciliationTerminalClassV1.PLAN_CERTIFICATE
            if certified
            else RegisteredReconciliationTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
        terminal_code,
        final_checkpoint.checkpoint_id,
        final_checkpoint.direct_snapshot.planner_model.model_id,
        authority,
        evaluation,
        terminal_na,
        evaluation_na,
        work,
    )


_TOTAL_NUMERIC_FIELDS = (
    "online_acquisition_draws",
    "target_replay_draws",
    "exact_evaluation_atom_calls",
    "exact_evaluation_rows",
    "exact_evaluation_atoms",
    "exact_evaluation_candidate_extensions",
    "exact_evaluation_dominance_comparisons",
    "exact_evaluation_frontier_points",
    "exact_evaluation_policy_assignments",
)


def _totals(
    *,
    scope: RegisteredReconciliationScopeV1,
    scope_key: str,
    occurrences: tuple[RegisteredReconciledOccurrenceV1, ...],
) -> RegisteredReconciliationTotalsV1:
    values = {
        field_name: sum(
            getattr(item.work, field_name) for item in occurrences
        )
        for field_name in _TOTAL_NUMERIC_FIELDS
    }
    certified = sum(
        item.terminal_class
        is RegisteredReconciliationTerminalClassV1.PLAN_CERTIFICATE
        for item in occurrences
    )
    return RegisteredReconciliationTotalsV1(
        scope,
        scope_key,
        tuple(item.occurrence_record_id for item in occurrences),
        **values,
        plan_certificate_count=certified,
        noncertificate_count=len(occurrences) - certified,
    )


def _reconcile_route_occurrence_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor_id: str,
    final_preregistration_id: str,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
    route_result: Any,
    operational_terminal_authority: Any,
    exact_evaluation: Any,
) -> RegisteredReconciledOccurrenceV1:
    if (
        plan.template.route_kind
        is consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT
    ):
        return _adaptive_occurrence(
            authority_chain=authority_chain,
            anchor_id=anchor_id,
            plan=plan,
            context=context,
            route_result=route_result,
            operational_terminal_authority=operational_terminal_authority,
            exact_evaluation=exact_evaluation,
        )
    if (
        plan.template.route_kind
        is consumer.RegisteredRouteKindV1.MATCHED_DIRECT_GROUND
    ):
        return _direct_occurrence(
            authority_chain=authority_chain,
            anchor_id=anchor_id,
            final_preregistration_id=final_preregistration_id,
            plan=plan,
            context=context,
            route_result=route_result,
            operational_terminal_authority=operational_terminal_authority,
            exact_evaluation=exact_evaluation,
        )
    raise V072RegisteredCampaignReconciliationViolation(
        "registered occurrence has an unknown route kind"
    )


def reconcile_registered_v072_campaign_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    execution_plan: consumer.RegisteredCampaignExecutionPlanV1,
    route_results: tuple[RouteResultV1, ...],
    operational_terminal_authorities: tuple[
        terminal.RegisteredOperationalTerminalAuthorityResultV1 | None, ...
    ],
    exact_evaluations: tuple[
        evaluator.RegisteredIndependentExactGroundEvaluationResultV1 | None,
        ...,
    ],
    source_reconstruction_replay: source_recipe.SourceReconstructionReplayV1,
) -> RegisteredCampaignReconciliationV1:
    """Recompute the complete native 15-occurrence ledger.

    ``None`` is accepted only in the two plan-only input lanes of a
    route-native noncertificate.  The corresponding typed N/A artifacts are
    minted internally and cannot be supplied by the caller.
    """

    if type(authority_chain) is not consumer.RegisteredCampaignAuthorityChainV1:
        raise V072RegisteredCampaignReconciliationViolation(
            "reconciliation requires the exact registered authority chain"
        )
    try:
        (
            source_recipe_id,
            manifest_id,
            final_preregistration_id,
            anchor_id,
            _anchor_attestation_id,
        ) = consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (ValueError, RuntimeError) as error:
        raise V072RegisteredCampaignReconciliationViolation(
            "registered authority chain replay failed"
        ) from error
    expected_plan = _expected_execution_plan(authority_chain.chain_id)
    if (
        type(execution_plan) is not consumer.RegisteredCampaignExecutionPlanV1
        or execution_plan != expected_plan
        or execution_plan.plan_id != expected_plan.plan_id
        or any(
            type(values) is not tuple
            or len(values) != LOGICAL_OCCURRENCE_DENOMINATOR
            for values in (
                route_results,
                operational_terminal_authorities,
                exact_evaluations,
            )
        )
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "campaign input skipped, reordered, duplicated, or replaced an occurrence"
        )
    source_offline = _validate_source_replay(
        authority_chain=authority_chain,
        source_reconstruction_replay=source_reconstruction_replay,
    )
    if source_offline.source_recipe_id != source_recipe_id:
        raise V072RegisteredCampaignReconciliationViolation(
            "source replay is not the chain-bound source recipe"
        )
    contexts = {
        item.context_id: item
        for item in prereg.registered_heldout_public_contexts_v2()
    }
    reconciled: list[RegisteredReconciledOccurrenceV1] = []
    for plan, route_result, terminal_authority, evaluation in zip(
        execution_plan.occurrences,
        route_results,
        operational_terminal_authorities,
        exact_evaluations,
        strict=True,
    ):
        context = contexts[plan.template.context_id]
        item = _reconcile_route_occurrence_v1(
            authority_chain=authority_chain,
            anchor_id=anchor_id,
            final_preregistration_id=final_preregistration_id,
            plan=plan,
            context=context,
            route_result=route_result,
            operational_terminal_authority=terminal_authority,
            exact_evaluation=evaluation,
        )
        reconciled.append(item)
    occurrences = tuple(reconciled)
    if (
        len({item.occurrence_plan.occurrence_id for item in occurrences})
        != LOGICAL_OCCURRENCE_DENOMINATOR
        or len({item.route_result_id for item in occurrences})
        != LOGICAL_OCCURRENCE_DENOMINATOR
        or len({item.runtime_verification_id for item in occurrences})
        != LOGICAL_OCCURRENCE_DENOMINATOR
    ):
        raise V072RegisteredCampaignReconciliationViolation(
            "one route result/verification was reused across occurrences"
        )
    context_totals = tuple(
        _totals(
            scope=RegisteredReconciliationScopeV1.CONTEXT,
            scope_key=context.context_key,
            occurrences=tuple(
                item
                for item in occurrences
                if item.occurrence_plan.template.context_id
                == context.context_id
            ),
        )
        for context in prereg.registered_heldout_public_contexts_v2()
    )
    arm_totals = tuple(
        _totals(
            scope=RegisteredReconciliationScopeV1.ARM,
            scope_key=arm,
            occurrences=tuple(
                item
                for item in occurrences
                if item.occurrence_plan.template.arm == arm
            ),
        )
        for arm in prereg.ARM_ORDER
    )
    campaign_totals = _totals(
        scope=RegisteredReconciliationScopeV1.CAMPAIGN,
        scope_key="REGISTERED_V072_CONTEXT_MAJOR_3_X_5",
        occurrences=occurrences,
    )
    return RegisteredCampaignReconciliationV1(
        authority_chain.chain_id,
        anchor_id,
        source_recipe_id,
        manifest_id,
        final_preregistration_id,
        execution_plan,
        source_offline,
        occurrences,
        context_totals,
        arm_totals,
        campaign_totals,
    )


__all__ = [
    "LOGICAL_OCCURRENCE_DENOMINATOR",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RegisteredCampaignReconciliationV1",
    "RegisteredOccurrenceLaneAccountingV1",
    "RegisteredReconciledOccurrenceV1",
    "RegisteredReconciliationNotApplicableRoleV1",
    "RegisteredReconciliationScopeV1",
    "RegisteredReconciliationTerminalClassV1",
    "RegisteredReconciliationTotalsV1",
    "RegisteredReconciliationTypedNotApplicableV1",
    "RegisteredSourceOfflineAccountingV1",
    "SCHEMA_VERSION",
    "V072RegisteredCampaignReconciliationViolation",
    "reconcile_registered_v072_campaign_v1",
]
