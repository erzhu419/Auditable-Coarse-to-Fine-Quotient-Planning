"""Bounded model-only contingent-plan proposal over a verified partial RAPM.

The legacy entry point reconstructs the complete manual V0-042 source graph.
The typed entry point instead replays one complete V0-045 synthesis result and
then freezes its verified model.  Both enumerate deterministic finite-horizon
global semantic-action assignments under one fixed canonical candidate cap.
Candidate scores come from the shared V0-043 fixed-model audit core, but this
module remains a proposal layer: its selected plan must be submitted to an
independent V0-043 audit before any certificate claim is made.

No transition callback, kernel, J0 comparator, ground solver, caller-provided
search cap, or second query object is accepted by the production API.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import product
from typing import Any, Iterable, Mapping

import acfqp.observed_typed_coordinate_synthesis_v1 as observed_synthesis_v1
from acfqp.observation_partial_rapm_v1 import (
    DeterministicObservationProfileV1,
    FrozenCoordinateProposalV1,
    ObservationLogManifestV1,
    ObservationPartialRAPMBuildV1,
    PartialCellV1,
    PlanningKind,
    PreregisteredObservationAuthorityV1,
    PortablePartialRAPMV1,
    verify_observation_partial_rapm_v1,
)
from acfqp.partial_sound_audit_v1 import (
    ContingentPlanAssignmentV1,
    ContingentPlanStageV1,
    FrozenContingentAbstractPlanV1,
    FrozenPartialAuditThresholdsV1,
    PartialAuditOutcome,
    PartialSoundAuditResultV1,
    _audit_verified_partial_model_v1,
    _validate_return_bound_authority,
    audit_partial_fixed_plan_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
TYPED_PLANNER_SCHEMA_VERSION = "1.1.0"
PROFILE_KEY = "partial_model_contingent_plan_proposal_v0"
TYPED_PROFILE_KEY = "partial_model_contingent_plan_from_observed_synthesis_v1"
PRODUCTION_CANDIDATE_CAP = 65536

DOMAIN_TAGS = {
    "cap_profile": "acfqp:partial-model-planner-cap-profile:v1",
    "action_domain": "acfqp:partial-model-planner-action-domain:v1",
    "candidate_summary": "acfqp:partial-model-planner-candidate-summary:v1",
    "trace": "acfqp:partial-model-planner-trace:v1",
    "result": "acfqp:partial-model-plan-proposal-result:v1",
    "typed_trace": "acfqp:typed-partial-model-planner-trace:v2",
    "typed_result": "acfqp:typed-partial-model-plan-proposal-result:v2",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("partial-model planner content domains must be unique")


class PartialModelPlannerInvariantViolation(ValueError):
    """The proposal context, trace, or content identity is invalid."""


class PartialModelPlannerOutcome(str, Enum):
    PLAN_PROPOSED = "PLAN_PROPOSED"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"


class PartialModelPlannerSelectionMode(str, Enum):
    INTERNAL_V0043_AUDIT_PASS_REWARD_MAX = "INTERNAL_V0043_AUDIT_PASS_REWARD_MAX"
    RISK_FEASIBLE_REWARD_MAX = "RISK_FEASIBLE_REWARD_MAX"
    MIN_FAILURE_RISK_FALLBACK = "MIN_FAILURE_RISK_FALLBACK"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class PartialModelPlannerExecutionProfile(str, Enum):
    PRODUCTION_CANONICAL = "PRODUCTION_CANONICAL"
    NONPRODUCTION_CAP_CONTROL = "NONPRODUCTION_CAP_CONTROL"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, ValueError) as error:
        raise PartialModelPlannerInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PartialModelPlannerInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise PartialModelPlannerInvariantViolation(
            f"{field} must be an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise PartialModelPlannerInvariantViolation(f"{field} must be exact")
    return Fraction(value)


def _fraction_document(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _sorted_ids(values: Iterable[str], field: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise PartialModelPlannerInvariantViolation(
            f"{field} must be an exact tuple"
        )
    if any(type(value) is not str for value in values):
        raise PartialModelPlannerInvariantViolation(
            f"{field} rejects nested duck IDs before canonical access"
        )
    if values != tuple(sorted(set(values))):
        raise PartialModelPlannerInvariantViolation(
            f"{field} must be unique and sorted"
        )
    for value in values:
        _cid(value, field)
    return values


def _cap_profile_payload(
    execution_profile: PartialModelPlannerExecutionProfile,
    candidate_cap: int,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.partial_model_planner_cap_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "execution_profile": execution_profile.value,
        "candidate_cap": candidate_cap,
        "cap_semantics": "GLOBAL_DETERMINISTIC_STAGE_ASSIGNMENT_PLANS",
        "caller_cap_allowed": (
            execution_profile
            is PartialModelPlannerExecutionProfile.NONPRODUCTION_CAP_CONTROL
        ),
        "production_claimed": (
            execution_profile
            is PartialModelPlannerExecutionProfile.PRODUCTION_CANONICAL
        ),
    }


def _cap_profile_id(
    execution_profile: PartialModelPlannerExecutionProfile,
    candidate_cap: int,
) -> str:
    return _content_id(
        "cap_profile", _cap_profile_payload(execution_profile, candidate_cap)
    )


PRODUCTION_CAP_PROFILE_ID = _cap_profile_id(
    PartialModelPlannerExecutionProfile.PRODUCTION_CANONICAL,
    PRODUCTION_CANDIDATE_CAP,
)


@dataclass(frozen=True, slots=True)
class PartialPlannerCellActionDomainV1:
    cell_id: str
    semantic_action_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.cell_id, "action domain cell_id")
        if not _sorted_ids(
            self.semantic_action_ids, "action domain semantic actions"
        ):
            raise PartialModelPlannerInvariantViolation(
                "every active cell needs a semantic action"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_model_planner_action_domain.v1",
            "schema_version": SCHEMA_VERSION,
            "cell_id": self.cell_id,
            "semantic_action_ids": list(self.semantic_action_ids),
        }

    @property
    def action_domain_id(self) -> str:
        return _content_id("action_domain", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "action_domain_id": self.action_domain_id}


@dataclass(frozen=True, slots=True)
class PartialPlannerCandidateSummaryV1:
    partial_model_id: str
    thresholds_id: str
    return_bound_proof_id: str
    contingent_plan_id: str
    audit_result_id: str
    audit_outcome: PartialAuditOutcome
    policy_reward_lower: Fraction
    policy_reward_upper: Fraction
    policy_failure_lower: Fraction
    policy_failure_upper: Fraction
    raw_distribution_regret: Fraction
    normalized_distribution_regret: Fraction
    maximum_support_point_normalized_regret: Fraction
    risk_tolerance: Fraction
    risk_feasible: bool
    external_coverage_certified: bool

    def __post_init__(self) -> None:
        for field in (
            "partial_model_id",
            "thresholds_id",
            "return_bound_proof_id",
            "contingent_plan_id",
            "audit_result_id",
        ):
            _cid(getattr(self, field), f"candidate {field}")
        if type(self.audit_outcome) is not PartialAuditOutcome:
            raise PartialModelPlannerInvariantViolation(
                "candidate audit outcome requires the exact enum"
            )
        for field in (
            "policy_reward_lower",
            "policy_reward_upper",
            "policy_failure_lower",
            "policy_failure_upper",
            "raw_distribution_regret",
            "normalized_distribution_regret",
            "maximum_support_point_normalized_regret",
            "risk_tolerance",
        ):
            object.__setattr__(self, field, _fraction(getattr(self, field), field))
        if self.policy_reward_lower > self.policy_reward_upper or not (
            0
            <= self.policy_failure_lower
            <= self.policy_failure_upper
            <= 1
            and 0 <= self.risk_tolerance <= 1
        ):
            raise PartialModelPlannerInvariantViolation(
                "candidate reward/risk bounds are invalid"
            )
        if self.raw_distribution_regret < 0 or not (
            0
            <= self.normalized_distribution_regret
            <= 1
            and 0
            <= self.maximum_support_point_normalized_regret
            <= 1
        ):
            raise PartialModelPlannerInvariantViolation(
                "candidate regret diagnostics are invalid"
            )
        if type(self.risk_feasible) is not bool or self.risk_feasible != (
            self.policy_failure_upper <= self.risk_tolerance
        ):
            raise PartialModelPlannerInvariantViolation(
                "candidate risk-feasible flag disagrees with its upper"
            )
        if type(self.external_coverage_certified) is not bool:
            raise PartialModelPlannerInvariantViolation(
                "candidate coverage flag must be an exact boolean"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_model_planner_candidate_summary.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "return_bound_proof_id": self.return_bound_proof_id,
            "contingent_plan_id": self.contingent_plan_id,
            "audit_result_id": self.audit_result_id,
            "audit_outcome": self.audit_outcome.value,
            "policy_reward_lower": _fraction_document(self.policy_reward_lower),
            "policy_reward_upper": _fraction_document(self.policy_reward_upper),
            "policy_failure_lower": _fraction_document(self.policy_failure_lower),
            "policy_failure_upper": _fraction_document(self.policy_failure_upper),
            "raw_distribution_regret": _fraction_document(
                self.raw_distribution_regret
            ),
            "normalized_distribution_regret": _fraction_document(
                self.normalized_distribution_regret
            ),
            "maximum_support_point_normalized_regret": _fraction_document(
                self.maximum_support_point_normalized_regret
            ),
            "risk_tolerance": _fraction_document(self.risk_tolerance),
            "risk_feasible": self.risk_feasible,
            "external_coverage_certified": self.external_coverage_certified,
        }

    @property
    def candidate_summary_id(self) -> str:
        return _content_id("candidate_summary", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "candidate_summary_id": self.candidate_summary_id,
        }


def _selected_summary(
    summaries: tuple[PartialPlannerCandidateSummaryV1, ...],
) -> tuple[PartialModelPlannerSelectionMode, PartialPlannerCandidateSummaryV1]:
    internal_audit_pass = tuple(
        item
        for item in summaries
        if item.audit_outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    )
    if internal_audit_pass:
        return (
            PartialModelPlannerSelectionMode.INTERNAL_V0043_AUDIT_PASS_REWARD_MAX,
            min(
                internal_audit_pass,
                key=lambda item: (
                    -item.policy_reward_lower,
                    item.policy_failure_upper,
                    item.contingent_plan_id,
                ),
            ),
        )
    risk_feasible = tuple(item for item in summaries if item.risk_feasible)
    if risk_feasible:
        return (
            PartialModelPlannerSelectionMode.RISK_FEASIBLE_REWARD_MAX,
            min(
                risk_feasible,
                key=lambda item: (
                    -item.policy_reward_lower,
                    item.policy_failure_upper,
                    item.contingent_plan_id,
                ),
            ),
        )
    return (
        PartialModelPlannerSelectionMode.MIN_FAILURE_RISK_FALLBACK,
        min(
            summaries,
            key=lambda item: (
                item.policy_failure_upper,
                -item.policy_reward_lower,
                item.contingent_plan_id,
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class PartialModelPlannerTraceV1:
    partial_model_id: str
    partial_build_result_id: str
    thresholds_id: str
    return_bound_proof_id: str
    horizon: int
    action_domains: tuple[PartialPlannerCellActionDomainV1, ...]
    per_stage_assignment_count: int
    candidate_count: int
    execution_profile: PartialModelPlannerExecutionProfile
    candidate_cap: int
    cap_profile_id: str
    candidate_evaluated_count: int
    candidate_summaries: tuple[PartialPlannerCandidateSummaryV1, ...]
    outcome: PartialModelPlannerOutcome
    selection_mode: PartialModelPlannerSelectionMode
    selected_plan_id: str | None
    source_graph_reconstruction_passed: bool
    source_graph_reconstruction_count: int
    fixed_plan_audit_count: int
    enumeration_complete: bool
    production_profile: bool
    work_economics_claimed: bool
    external_transition_authority_calls: int = 0
    ground_search_calls: int = 0

    def __post_init__(self) -> None:
        for field in (
            "partial_model_id",
            "partial_build_result_id",
            "thresholds_id",
            "return_bound_proof_id",
            "cap_profile_id",
        ):
            _cid(getattr(self, field), f"trace {field}")
        _integer(self.horizon, "trace horizon", 1)
        if type(self.action_domains) is not tuple or any(
            type(item) is not PartialPlannerCellActionDomainV1
            for item in self.action_domains
        ):
            raise PartialModelPlannerInvariantViolation(
                "trace rejects duck action domains"
            )
        domain_keys = tuple(item.cell_id for item in self.action_domains)
        if not domain_keys or domain_keys != tuple(sorted(set(domain_keys))):
            raise PartialModelPlannerInvariantViolation(
                "trace action domains must be nonempty, unique, and sorted"
            )
        _integer(self.per_stage_assignment_count, "stage assignment count", 1)
        expected_stage_count = 1
        for item in self.action_domains:
            expected_stage_count *= len(item.semantic_action_ids)
        if self.per_stage_assignment_count != expected_stage_count:
            raise PartialModelPlannerInvariantViolation(
                "stage assignment count differs from action domains"
            )
        _integer(self.candidate_count, "candidate count", 1)
        if self.candidate_count != self.per_stage_assignment_count**self.horizon:
            raise PartialModelPlannerInvariantViolation(
                "candidate count differs from the global plan product"
            )
        if type(self.execution_profile) is not PartialModelPlannerExecutionProfile:
            raise PartialModelPlannerInvariantViolation(
                "trace execution profile requires the exact enum"
            )
        _integer(self.candidate_cap, "candidate cap", 1)
        expected_cap_id = _cap_profile_id(
            self.execution_profile, self.candidate_cap
        )
        if self.cap_profile_id != expected_cap_id:
            raise PartialModelPlannerInvariantViolation(
                "trace cap profile ID is inconsistent"
            )
        if self.execution_profile is PartialModelPlannerExecutionProfile.PRODUCTION_CANONICAL:
            if (
                self.candidate_cap != PRODUCTION_CANDIDATE_CAP
                or self.cap_profile_id != PRODUCTION_CAP_PROFILE_ID
                or self.production_profile is not True
            ):
                raise PartialModelPlannerInvariantViolation(
                    "production trace must use the fixed canonical cap"
                )
        elif (
            self.candidate_cap >= PRODUCTION_CANDIDATE_CAP
            or self.production_profile is not False
        ):
            raise PartialModelPlannerInvariantViolation(
                "nonproduction cap control cannot impersonate production"
            )
        _integer(self.candidate_evaluated_count, "candidate evaluated count")
        if type(self.candidate_summaries) is not tuple or any(
            type(item) is not PartialPlannerCandidateSummaryV1
            for item in self.candidate_summaries
        ):
            raise PartialModelPlannerInvariantViolation(
                "trace rejects duck candidate summaries"
            )
        summary_keys = tuple(
            item.contingent_plan_id for item in self.candidate_summaries
        )
        if summary_keys != tuple(sorted(set(summary_keys))):
            raise PartialModelPlannerInvariantViolation(
                "candidate summaries must be unique and plan-ID sorted"
            )
        if any(
            item.partial_model_id != self.partial_model_id
            or item.thresholds_id != self.thresholds_id
            or item.return_bound_proof_id != self.return_bound_proof_id
            for item in self.candidate_summaries
        ):
            raise PartialModelPlannerInvariantViolation(
                "candidate summaries do not bind this planner context"
            )
        if type(self.outcome) is not PartialModelPlannerOutcome or type(
            self.selection_mode
        ) is not PartialModelPlannerSelectionMode:
            raise PartialModelPlannerInvariantViolation(
                "trace outcome/selection mode requires exact enums"
            )
        _integer(
            self.source_graph_reconstruction_count,
            "source graph reconstruction count",
            1,
        )
        _integer(self.fixed_plan_audit_count, "fixed-plan audit count")
        for field in (
            "source_graph_reconstruction_passed",
            "enumeration_complete",
            "production_profile",
            "work_economics_claimed",
        ):
            if type(getattr(self, field)) is not bool:
                raise PartialModelPlannerInvariantViolation(
                    f"trace {field} must be an exact boolean"
                )
        if self.source_graph_reconstruction_passed is not True:
            raise PartialModelPlannerInvariantViolation(
                "planner trace requires full V0-042 reconstruction"
            )
        if (
            self.fixed_plan_audit_count != self.candidate_evaluated_count
            or self.source_graph_reconstruction_count
            != 1 + self.fixed_plan_audit_count
            or self.work_economics_claimed is not False
        ):
            raise PartialModelPlannerInvariantViolation(
                "planner work-tax counters or economics scope are inconsistent"
            )
        if self.outcome is PartialModelPlannerOutcome.CAP_EXHAUSTED:
            if (
                self.candidate_count <= self.candidate_cap
                or self.candidate_evaluated_count != 0
                or self.candidate_summaries
                or self.selection_mode
                is not PartialModelPlannerSelectionMode.NOT_APPLICABLE
                or self.selected_plan_id is not None
                or self.enumeration_complete is not False
            ):
                raise PartialModelPlannerInvariantViolation(
                    "cap-exhausted trace contains candidate work or a plan"
                )
        else:
            if (
                self.candidate_count > self.candidate_cap
                or self.candidate_evaluated_count != self.candidate_count
                or len(self.candidate_summaries) != self.candidate_count
                or self.selected_plan_id is None
                or self.enumeration_complete is not True
            ):
                raise PartialModelPlannerInvariantViolation(
                    "proposed trace is not a complete within-cap enumeration"
                )
            _cid(self.selected_plan_id, "trace selected_plan_id")
            expected_mode, expected = _selected_summary(self.candidate_summaries)
            if (
                self.selection_mode is not expected_mode
                or self.selected_plan_id != expected.contingent_plan_id
            ):
                raise PartialModelPlannerInvariantViolation(
                    "trace selection differs from the canonical constrained rule"
                )
        if self.external_transition_authority_calls != 0 or self.ground_search_calls != 0:
            raise PartialModelPlannerInvariantViolation(
                "planner trace leaked transition or ground-search authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_model_planner_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "partial_model_id": self.partial_model_id,
            "partial_build_result_id": self.partial_build_result_id,
            "thresholds_id": self.thresholds_id,
            "return_bound_proof_id": self.return_bound_proof_id,
            "horizon": self.horizon,
            "action_domains": [item.to_document() for item in self.action_domains],
            "per_stage_assignment_count": self.per_stage_assignment_count,
            "candidate_count": self.candidate_count,
            "execution_profile": self.execution_profile.value,
            "candidate_cap": self.candidate_cap,
            "cap_profile_id": self.cap_profile_id,
            "candidate_evaluated_count": self.candidate_evaluated_count,
            "candidate_summaries": [
                item.to_document() for item in self.candidate_summaries
            ],
            "outcome": self.outcome.value,
            "selection_mode": self.selection_mode.value,
            "selected_plan_id": self.selected_plan_id,
            "source_graph_reconstruction_passed": (
                self.source_graph_reconstruction_passed
            ),
            "source_graph_reconstruction_count": (
                self.source_graph_reconstruction_count
            ),
            "fixed_plan_audit_count": self.fixed_plan_audit_count,
            "enumeration_complete": self.enumeration_complete,
            "production_profile": self.production_profile,
            "work_economics_claimed": self.work_economics_claimed,
            "external_transition_authority_calls": (
                self.external_transition_authority_calls
            ),
            "ground_search_calls": self.ground_search_calls,
        }

    @property
    def trace_id(self) -> str:
        return _content_id("trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


@dataclass(frozen=True, slots=True)
class PartialModelPlanProposalResultV1:
    trace: PartialModelPlannerTraceV1
    selected_plan: FrozenContingentAbstractPlanV1 | None
    proposal_is_certificate_authority: bool = False
    selected_plan_requires_independent_v0043_audit: bool = True
    feasible_plan_claimed: bool = False
    infeasible_query_claimed: bool = False
    optimal_ground_policy_claimed: bool = False
    claim_kind: str = "MODEL_ONLY_CONTINGENT_PLAN_PROPOSAL"

    def __post_init__(self) -> None:
        if type(self.trace) is not PartialModelPlannerTraceV1:
            raise PartialModelPlannerInvariantViolation(
                "proposal result rejects duck traces"
            )
        if self.trace.outcome is PartialModelPlannerOutcome.PLAN_PROPOSED:
            if (
                type(self.selected_plan) is not FrozenContingentAbstractPlanV1
                or self.selected_plan.plan_id != self.trace.selected_plan_id
                or self.selected_plan.partial_model_id != self.trace.partial_model_id
                or self.selected_plan.horizon != self.trace.horizon
            ):
                raise PartialModelPlannerInvariantViolation(
                    "proposal result does not bind its selected plan"
                )
        elif self.selected_plan is not None:
            raise PartialModelPlannerInvariantViolation(
                "cap-exhausted proposal cannot contain a plan"
            )
        if (
            self.proposal_is_certificate_authority is not False
            or self.selected_plan_requires_independent_v0043_audit is not True
            or self.feasible_plan_claimed is not False
            or self.infeasible_query_claimed is not False
            or self.optimal_ground_policy_claimed is not False
            or self.claim_kind != "MODEL_ONLY_CONTINGENT_PLAN_PROPOSAL"
        ):
            raise PartialModelPlannerInvariantViolation(
                "proposal result overclaims its model-only authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_model_plan_proposal_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "trace": self.trace.to_document(),
            "selected_plan": (
                None
                if self.selected_plan is None
                else self.selected_plan.to_document()
            ),
            "proposal_is_certificate_authority": (
                self.proposal_is_certificate_authority
            ),
            "selected_plan_requires_independent_v0043_audit": (
                self.selected_plan_requires_independent_v0043_audit
            ),
            "feasible_plan_claimed": self.feasible_plan_claimed,
            "infeasible_query_claimed": self.infeasible_query_claimed,
            "optimal_ground_policy_claimed": self.optimal_ground_policy_claimed,
            "claim_kind": self.claim_kind,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class TypedPartialModelPlannerTraceV2:
    """Truthful one-replay trace for planning from a retained V0-045 model."""

    observation_log_id: str
    semantics_profile_id: str
    observation_authority_id: str
    observed_synthesis_result_id: str
    observed_synthesis_certificate_id: str
    coordinate_proposal_id: str
    partial_build_result_id: str
    partial_model_id: str
    thresholds_id: str
    return_bound_proof_id: str
    horizon: int
    action_domains: tuple[PartialPlannerCellActionDomainV1, ...]
    per_stage_assignment_count: int
    candidate_count: int
    candidate_cap: int
    cap_profile_id: str
    candidate_evaluated_count: int
    candidate_summaries: tuple[PartialPlannerCandidateSummaryV1, ...]
    outcome: PartialModelPlannerOutcome
    selection_mode: PartialModelPlannerSelectionMode
    selected_plan_id: str | None
    retained_v0045_full_replay_count: int
    fixed_plan_audit_count: int
    internal_audit_source_replay_count: int = 0
    retained_v0045_full_replay_passed: bool = True
    enumeration_complete: bool = True
    production_profile: bool = True
    work_economics_claimed: bool = False
    external_transition_authority_calls: int = 0
    ground_search_calls: int = 0
    source_authority_kind: str = "RETAINED_V0045_FULL_SYNTHESIS_REPLAY_V1"

    def __post_init__(self) -> None:
        for field in (
            "observation_log_id",
            "semantics_profile_id",
            "observation_authority_id",
            "observed_synthesis_result_id",
            "observed_synthesis_certificate_id",
            "coordinate_proposal_id",
            "partial_build_result_id",
            "partial_model_id",
            "thresholds_id",
            "return_bound_proof_id",
            "cap_profile_id",
        ):
            _cid(getattr(self, field), f"typed planner trace {field}")
        _integer(self.horizon, "typed trace horizon", 1)
        if type(self.action_domains) is not tuple or any(
            type(item) is not PartialPlannerCellActionDomainV1
            for item in self.action_domains
        ):
            raise PartialModelPlannerInvariantViolation(
                "typed planner trace rejects duck action domains"
            )
        domain_keys = tuple(item.cell_id for item in self.action_domains)
        if not domain_keys or domain_keys != tuple(sorted(set(domain_keys))):
            raise PartialModelPlannerInvariantViolation(
                "typed trace action domains must be nonempty, unique, and sorted"
            )
        _integer(
            self.per_stage_assignment_count,
            "typed stage assignment count",
            1,
        )
        expected_stage_count = 1
        for item in self.action_domains:
            expected_stage_count *= len(item.semantic_action_ids)
        if self.per_stage_assignment_count != expected_stage_count:
            raise PartialModelPlannerInvariantViolation(
                "typed stage assignment count differs from action domains"
            )
        _integer(self.candidate_count, "typed candidate count", 1)
        if self.candidate_count != self.per_stage_assignment_count**self.horizon:
            raise PartialModelPlannerInvariantViolation(
                "typed candidate count differs from the global plan product"
            )
        _integer(self.candidate_cap, "typed candidate cap", 1)
        if (
            self.candidate_cap != PRODUCTION_CANDIDATE_CAP
            or self.cap_profile_id != PRODUCTION_CAP_PROFILE_ID
        ):
            raise PartialModelPlannerInvariantViolation(
                "typed planner must use the fixed canonical cap"
            )
        _integer(
            self.candidate_evaluated_count,
            "typed candidate evaluated count",
        )
        if type(self.candidate_summaries) is not tuple or any(
            type(item) is not PartialPlannerCandidateSummaryV1
            for item in self.candidate_summaries
        ):
            raise PartialModelPlannerInvariantViolation(
                "typed trace rejects duck candidate summaries"
            )
        summary_keys = tuple(
            item.contingent_plan_id for item in self.candidate_summaries
        )
        if summary_keys != tuple(sorted(set(summary_keys))):
            raise PartialModelPlannerInvariantViolation(
                "typed candidate summaries must be unique and plan-ID sorted"
            )
        if any(
            item.partial_model_id != self.partial_model_id
            or item.thresholds_id != self.thresholds_id
            or item.return_bound_proof_id != self.return_bound_proof_id
            for item in self.candidate_summaries
        ):
            raise PartialModelPlannerInvariantViolation(
                "typed candidate summaries do not bind this planner context"
            )
        if type(self.outcome) is not PartialModelPlannerOutcome or type(
            self.selection_mode
        ) is not PartialModelPlannerSelectionMode:
            raise PartialModelPlannerInvariantViolation(
                "typed trace outcome/selection requires exact enums"
            )
        _integer(
            self.retained_v0045_full_replay_count,
            "retained V0-045 full replay count",
            1,
        )
        _integer(
            self.fixed_plan_audit_count,
            "fixed-plan audit count",
        )
        _integer(
            self.internal_audit_source_replay_count,
            "internal audit source replay count",
        )
        _integer(
            self.external_transition_authority_calls,
            "external transition authority calls",
        )
        _integer(self.ground_search_calls, "ground search calls")
        if (
            self.retained_v0045_full_replay_count != 1
            or self.fixed_plan_audit_count != self.candidate_evaluated_count
            or self.internal_audit_source_replay_count != 0
        ):
            raise PartialModelPlannerInvariantViolation(
                "typed planner replay/audit counters do not reconcile"
            )
        for field in (
            "retained_v0045_full_replay_passed",
            "enumeration_complete",
            "production_profile",
            "work_economics_claimed",
        ):
            if type(getattr(self, field)) is not bool:
                raise PartialModelPlannerInvariantViolation(
                    f"typed trace {field} must be an exact boolean"
                )
        if (
            self.retained_v0045_full_replay_passed is not True
            or self.production_profile is not True
            or self.work_economics_claimed is not False
            or self.external_transition_authority_calls != 0
            or self.ground_search_calls != 0
        ):
            raise PartialModelPlannerInvariantViolation(
                "typed planner leaked authority or overclaimed work"
            )
        if self.outcome is PartialModelPlannerOutcome.CAP_EXHAUSTED:
            if (
                self.candidate_count <= self.candidate_cap
                or self.candidate_evaluated_count != 0
                or self.candidate_summaries
                or self.selection_mode
                is not PartialModelPlannerSelectionMode.NOT_APPLICABLE
                or self.selected_plan_id is not None
                or self.enumeration_complete is not False
            ):
                raise PartialModelPlannerInvariantViolation(
                    "typed cap-exhausted trace contains candidate work or a plan"
                )
        else:
            if (
                self.candidate_count > self.candidate_cap
                or self.candidate_evaluated_count != self.candidate_count
                or len(self.candidate_summaries) != self.candidate_count
                or self.selected_plan_id is None
                or self.enumeration_complete is not True
            ):
                raise PartialModelPlannerInvariantViolation(
                    "typed proposed trace is not a complete within-cap enumeration"
                )
            _cid(self.selected_plan_id, "typed trace selected plan")
            expected_mode, expected = _selected_summary(self.candidate_summaries)
            if (
                self.selection_mode is not expected_mode
                or self.selected_plan_id != expected.contingent_plan_id
            ):
                raise PartialModelPlannerInvariantViolation(
                    "typed trace selection differs from the canonical rule"
                )
        if self.source_authority_kind != "RETAINED_V0045_FULL_SYNTHESIS_REPLAY_V1":
            raise PartialModelPlannerInvariantViolation(
                "typed planner relaxed its retained synthesis authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.typed_partial_model_planner_trace.v2",
            "schema_version": TYPED_PLANNER_SCHEMA_VERSION,
            "profile_key": TYPED_PROFILE_KEY,
            "observation_log_id": self.observation_log_id,
            "semantics_profile_id": self.semantics_profile_id,
            "observation_authority_id": self.observation_authority_id,
            "observed_synthesis_result_id": self.observed_synthesis_result_id,
            "observed_synthesis_certificate_id": (
                self.observed_synthesis_certificate_id
            ),
            "coordinate_proposal_id": self.coordinate_proposal_id,
            "partial_build_result_id": self.partial_build_result_id,
            "partial_model_id": self.partial_model_id,
            "thresholds_id": self.thresholds_id,
            "return_bound_proof_id": self.return_bound_proof_id,
            "horizon": self.horizon,
            "action_domains": [
                item.to_document() for item in self.action_domains
            ],
            "per_stage_assignment_count": self.per_stage_assignment_count,
            "candidate_count": self.candidate_count,
            "candidate_cap": self.candidate_cap,
            "cap_profile_id": self.cap_profile_id,
            "candidate_evaluated_count": self.candidate_evaluated_count,
            "candidate_summaries": [
                item.to_document() for item in self.candidate_summaries
            ],
            "outcome": self.outcome.value,
            "selection_mode": self.selection_mode.value,
            "selected_plan_id": self.selected_plan_id,
            "retained_v0045_full_replay_count": (
                self.retained_v0045_full_replay_count
            ),
            "fixed_plan_audit_count": self.fixed_plan_audit_count,
            "internal_audit_source_replay_count": (
                self.internal_audit_source_replay_count
            ),
            "retained_v0045_full_replay_passed": (
                self.retained_v0045_full_replay_passed
            ),
            "enumeration_complete": self.enumeration_complete,
            "production_profile": self.production_profile,
            "work_economics_claimed": self.work_economics_claimed,
            "external_transition_authority_calls": (
                self.external_transition_authority_calls
            ),
            "ground_search_calls": self.ground_search_calls,
            "source_authority_kind": self.source_authority_kind,
        }

    @property
    def trace_id(self) -> str:
        return _content_id("typed_trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


@dataclass(frozen=True, slots=True)
class TypedPartialModelPlanProposalResultV2:
    """A model-only proposal whose source is one replayed V0-045 result."""

    trace: TypedPartialModelPlannerTraceV2
    selected_plan: FrozenContingentAbstractPlanV1 | None
    proposal_is_certificate_authority: bool = False
    selected_plan_requires_independent_typed_v0043_audit: bool = True
    feasible_plan_claimed: bool = False
    infeasible_query_claimed: bool = False
    optimal_ground_policy_claimed: bool = False
    claim_kind: str = (
        "MODEL_ONLY_CONTINGENT_PLAN_PROPOSAL_FROM_RETAINED_V0045"
    )

    def __post_init__(self) -> None:
        if type(self.trace) is not TypedPartialModelPlannerTraceV2:
            raise PartialModelPlannerInvariantViolation(
                "typed proposal result rejects duck traces"
            )
        if self.trace.outcome is PartialModelPlannerOutcome.PLAN_PROPOSED:
            if (
                type(self.selected_plan) is not FrozenContingentAbstractPlanV1
                or self.selected_plan.plan_id != self.trace.selected_plan_id
                or self.selected_plan.partial_model_id != self.trace.partial_model_id
                or self.selected_plan.horizon != self.trace.horizon
            ):
                raise PartialModelPlannerInvariantViolation(
                    "typed proposal result does not bind its selected plan"
                )
        elif self.selected_plan is not None:
            raise PartialModelPlannerInvariantViolation(
                "typed cap-exhausted proposal cannot contain a plan"
            )
        if (
            self.proposal_is_certificate_authority is not False
            or self.selected_plan_requires_independent_typed_v0043_audit is not True
            or self.feasible_plan_claimed is not False
            or self.infeasible_query_claimed is not False
            or self.optimal_ground_policy_claimed is not False
            or self.claim_kind
            != "MODEL_ONLY_CONTINGENT_PLAN_PROPOSAL_FROM_RETAINED_V0045"
        ):
            raise PartialModelPlannerInvariantViolation(
                "typed proposal result overclaims its model-only authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.typed_partial_model_plan_proposal_result.v2",
            "schema_version": TYPED_PLANNER_SCHEMA_VERSION,
            "profile_key": TYPED_PROFILE_KEY,
            "trace": self.trace.to_document(),
            "selected_plan": (
                None
                if self.selected_plan is None
                else self.selected_plan.to_document()
            ),
            "proposal_is_certificate_authority": (
                self.proposal_is_certificate_authority
            ),
            "selected_plan_requires_independent_typed_v0043_audit": (
                self.selected_plan_requires_independent_typed_v0043_audit
            ),
            "feasible_plan_claimed": self.feasible_plan_claimed,
            "infeasible_query_claimed": self.infeasible_query_claimed,
            "optimal_ground_policy_claimed": self.optimal_ground_policy_claimed,
            "claim_kind": self.claim_kind,
        }

    @property
    def result_id(self) -> str:
        return _content_id("typed_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _verified_partial_model(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    partial_build_result: ObservationPartialRAPMBuildV1,
) -> PortablePartialRAPMV1:
    failures = verify_observation_partial_rapm_v1(
        observation_log,
        coordinate_proposal,
        semantics_profile,
        observation_authority,
        partial_build_result,
    )
    if failures:
        raise PartialModelPlannerInvariantViolation(
            "partial RAPM source graph failed trusted reconstruction: "
            + ",".join(failures)
        )
    return partial_build_result.model


def _planner_context(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    partial_model: PortablePartialRAPMV1,
    thresholds: FrozenPartialAuditThresholdsV1,
) -> tuple[
    tuple[PartialCellV1, ...],
    tuple[PartialPlannerCellActionDomainV1, ...],
]:
    if type(thresholds) is not FrozenPartialAuditThresholdsV1:
        raise PartialModelPlannerInvariantViolation(
            "planner rejects duck thresholds"
        )
    if (
        thresholds.partial_model_id != partial_model.model_id
        or thresholds.horizon > partial_model.semantics_horizon_cap
    ):
        raise PartialModelPlannerInvariantViolation(
            "planner threshold/model identity or horizon mismatch"
        )
    try:
        _validate_return_bound_authority(
            observation_log,
            semantics_profile,
            observation_authority,
            partial_model,
            thresholds,
        )
    except ValueError as error:
        raise PartialModelPlannerInvariantViolation(str(error)) from error
    active_cells = tuple(
        sorted(
            (
                item
                for item in partial_model.cells
                if item.planning_kind is PlanningKind.ACTIVE
            ),
            key=lambda item: item.cell_id,
        )
    )
    state_to_cell = {
        state_id: cell.cell_id
        for cell in active_cells
        for state_id in cell.member_state_ids
    }
    if any(
        item.state_id not in state_to_cell
        for item in thresholds.initial_state_distribution
    ):
        raise PartialModelPlannerInvariantViolation(
            "planner initial support contains an unknown/non-active ground state"
        )
    actions_by_cell: dict[str, list[str]] = {
        item.cell_id: [] for item in active_cells
    }
    for action in partial_model.semantic_actions:
        if action.cell_id in actions_by_cell:
            actions_by_cell[action.cell_id].append(action.semantic_action_id)
    domains = tuple(
        PartialPlannerCellActionDomainV1(
            cell.cell_id,
            tuple(sorted(actions_by_cell[cell.cell_id])),
        )
        for cell in active_cells
    )
    realization_states: dict[tuple[str, str], list[str]] = {}
    for item in partial_model.semantic_realizations:
        realization_states.setdefault(
            (item.cell_id, item.semantic_action_id), []
        ).append(item.state_id)
    for cell, domain in zip(active_cells, domains):
        for action_id in domain.semantic_action_ids:
            if tuple(sorted(realization_states.get((cell.cell_id, action_id), ()))) != (
                cell.member_state_ids
            ):
                raise PartialModelPlannerInvariantViolation(
                    "planner action domain lacks complete cell-member realizations"
                )
    return active_cells, domains


def _stage_assignments(
    domains: tuple[PartialPlannerCellActionDomainV1, ...],
) -> tuple[tuple[ContingentPlanAssignmentV1, ...], ...]:
    return tuple(
        tuple(
            ContingentPlanAssignmentV1(domain.cell_id, action_id)
            for domain, action_id in zip(domains, action_ids)
        )
        for action_ids in product(
            *(item.semantic_action_ids for item in domains)
        )
    )


def _candidate_summary(
    thresholds: FrozenPartialAuditThresholdsV1,
    plan: FrozenContingentAbstractPlanV1,
    audit: PartialSoundAuditResultV1,
) -> PartialPlannerCandidateSummaryV1:
    bounds = audit.robust_bounds
    return PartialPlannerCandidateSummaryV1(
        bounds.partial_model_id,
        bounds.thresholds_id,
        bounds.return_bound_proof_id,
        plan.plan_id,
        audit.result_id,
        audit.outcome,
        bounds.policy_reward_lower,
        bounds.policy_reward_upper,
        bounds.policy_failure_lower,
        bounds.policy_failure_upper,
        bounds.raw_distribution_regret,
        bounds.normalized_distribution_regret,
        bounds.maximum_support_point_normalized_regret,
        thresholds.risk_tolerance,
        bounds.policy_failure_upper <= thresholds.risk_tolerance,
        bounds.external_coverage_certified,
    )


def _propose(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    partial_build_result: ObservationPartialRAPMBuildV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    *,
    execution_profile: PartialModelPlannerExecutionProfile,
    candidate_cap: int,
) -> PartialModelPlanProposalResultV1:
    # Reconstruction deliberately precedes all threshold access.
    partial_model = _verified_partial_model(
        observation_log,
        coordinate_proposal,
        semantics_profile,
        observation_authority,
        partial_build_result,
    )
    _, domains = _planner_context(
        observation_log,
        semantics_profile,
        observation_authority,
        partial_model,
        thresholds,
    )
    _integer(candidate_cap, "candidate cap", 1)
    stage_count = 1
    for domain in domains:
        stage_count *= len(domain.semantic_action_ids)
    candidate_count = stage_count**thresholds.horizon
    cap_id = _cap_profile_id(execution_profile, candidate_cap)
    if candidate_count > candidate_cap:
        trace = PartialModelPlannerTraceV1(
            partial_model.model_id,
            partial_build_result.result_id,
            thresholds.thresholds_id,
            thresholds.return_bound_proof.proof_id,
            thresholds.horizon,
            domains,
            stage_count,
            candidate_count,
            execution_profile,
            candidate_cap,
            cap_id,
            0,
            (),
            PartialModelPlannerOutcome.CAP_EXHAUSTED,
            PartialModelPlannerSelectionMode.NOT_APPLICABLE,
            None,
            True,
            1,
            0,
            False,
            execution_profile
            is PartialModelPlannerExecutionProfile.PRODUCTION_CANONICAL,
            False,
        )
        return PartialModelPlanProposalResultV1(trace, None)

    stages = _stage_assignments(domains)
    plans: dict[str, FrozenContingentAbstractPlanV1] = {}
    summaries: list[PartialPlannerCandidateSummaryV1] = []
    for stage_schedule in product(stages, repeat=thresholds.horizon):
        plan = FrozenContingentAbstractPlanV1(
            partial_model.model_id,
            thresholds.horizon,
            tuple(
                ContingentPlanStageV1(time_index, assignments)
                for time_index, assignments in enumerate(stage_schedule)
            ),
        )
        audit = audit_partial_fixed_plan_v1(
            observation_log,
            coordinate_proposal,
            semantics_profile,
            observation_authority,
            partial_build_result,
            thresholds,
            plan,
        )
        plans[plan.plan_id] = plan
        summaries.append(_candidate_summary(thresholds, plan, audit))
    summaries_tuple = tuple(
        sorted(summaries, key=lambda item: item.contingent_plan_id)
    )
    if len(plans) != candidate_count or len(summaries_tuple) != candidate_count:
        raise PartialModelPlannerInvariantViolation(
            "global deterministic plan enumeration was not one-to-one"
        )
    selection_mode, selected = _selected_summary(summaries_tuple)
    trace = PartialModelPlannerTraceV1(
        partial_model.model_id,
        partial_build_result.result_id,
        thresholds.thresholds_id,
        thresholds.return_bound_proof.proof_id,
        thresholds.horizon,
        domains,
        stage_count,
        candidate_count,
        execution_profile,
        candidate_cap,
        cap_id,
        candidate_count,
        summaries_tuple,
        PartialModelPlannerOutcome.PLAN_PROPOSED,
        selection_mode,
        selected.contingent_plan_id,
        True,
        1 + candidate_count,
        candidate_count,
        True,
        execution_profile
        is PartialModelPlannerExecutionProfile.PRODUCTION_CANONICAL,
        False,
    )
    return PartialModelPlanProposalResultV1(
        trace, plans[selected.contingent_plan_id]
    )


def _verified_observed_synthesis_model_v2(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: (
        observed_synthesis_v1.ObservedTypedPartialRAPMResultV1
    ),
) -> PortablePartialRAPMV1:
    """Replay the complete V0-045 result before returning its bound model."""

    if (
        type(observed_synthesis_result)
        is not observed_synthesis_v1.ObservedTypedPartialRAPMResultV1
    ):
        raise PartialModelPlannerInvariantViolation(
            "typed planner rejects duck V0-045 synthesis results"
        )
    try:
        failures = observed_synthesis_v1.verify_observed_lmb_partial_rapm_v1(
            observation_log,
            semantics_profile,
            observation_authority,
            observed_synthesis_result,
        )
    except ValueError as error:
        raise PartialModelPlannerInvariantViolation(
            "typed partial RAPM failed retained V0-045 reconstruction: "
            + str(error)
        ) from error
    if failures:
        raise PartialModelPlannerInvariantViolation(
            "typed partial RAPM failed retained V0-045 reconstruction: "
            + ",".join(failures)
        )
    proposal = observed_synthesis_result.coordinate_proposal
    build = observed_synthesis_result.partial_build_result
    model = build.model
    certificate = observed_synthesis_result.certificate
    if (
        certificate.coordinate_proposal_id != proposal.proposal_id
        or certificate.partial_build_result_id != build.result_id
        or certificate.partial_model_id != model.model_id
        or build.coordinate_proposal_id != proposal.proposal_id
        or model.coordinate_proposal_id != proposal.proposal_id
    ):
        raise PartialModelPlannerInvariantViolation(
            "typed V0-045 result/proposal/build/model identity chain mismatch"
        )
    return model


def propose_partial_model_plan_from_observed_synthesis_v2(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: (
        observed_synthesis_v1.ObservedTypedPartialRAPMResultV1
    ),
    thresholds: FrozenPartialAuditThresholdsV1,
) -> TypedPartialModelPlanProposalResultV2:
    """Plan only after replaying one exact full V0-045 synthesis result."""

    # Retained synthesis replay deliberately precedes all threshold access.
    partial_model = _verified_observed_synthesis_model_v2(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
    )
    _, domains = _planner_context(
        observation_log,
        semantics_profile,
        observation_authority,
        partial_model,
        thresholds,
    )
    stage_count = 1
    for domain in domains:
        stage_count *= len(domain.semantic_action_ids)
    candidate_count = stage_count**thresholds.horizon

    build = observed_synthesis_result.partial_build_result
    certificate = observed_synthesis_result.certificate
    common_trace_arguments = {
        "observation_log_id": observation_log.log_id,
        "semantics_profile_id": semantics_profile.profile_id,
        "observation_authority_id": observation_authority.authority_id,
        "observed_synthesis_result_id": observed_synthesis_result.result_id,
        "observed_synthesis_certificate_id": certificate.certificate_id,
        "coordinate_proposal_id": (
            observed_synthesis_result.coordinate_proposal.proposal_id
        ),
        "partial_build_result_id": build.result_id,
        "partial_model_id": partial_model.model_id,
        "thresholds_id": thresholds.thresholds_id,
        "return_bound_proof_id": thresholds.return_bound_proof.proof_id,
        "horizon": thresholds.horizon,
        "action_domains": domains,
        "per_stage_assignment_count": stage_count,
        "candidate_count": candidate_count,
        "candidate_cap": PRODUCTION_CANDIDATE_CAP,
        "cap_profile_id": PRODUCTION_CAP_PROFILE_ID,
    }
    if candidate_count > PRODUCTION_CANDIDATE_CAP:
        typed_trace = TypedPartialModelPlannerTraceV2(
            **common_trace_arguments,
            candidate_evaluated_count=0,
            candidate_summaries=(),
            outcome=PartialModelPlannerOutcome.CAP_EXHAUSTED,
            selection_mode=PartialModelPlannerSelectionMode.NOT_APPLICABLE,
            selected_plan_id=None,
            retained_v0045_full_replay_count=1,
            fixed_plan_audit_count=0,
            enumeration_complete=False,
        )
        return TypedPartialModelPlanProposalResultV2(typed_trace, None)

    stages = _stage_assignments(domains)
    plans: dict[str, FrozenContingentAbstractPlanV1] = {}
    summaries: list[PartialPlannerCandidateSummaryV1] = []
    for stage_schedule in product(stages, repeat=thresholds.horizon):
        plan = FrozenContingentAbstractPlanV1(
            partial_model.model_id,
            thresholds.horizon,
            tuple(
                ContingentPlanStageV1(time_index, assignments)
                for time_index, assignments in enumerate(stage_schedule)
            ),
        )
        audit = _audit_verified_partial_model_v1(
            partial_model,
            observation_log,
            semantics_profile,
            observation_authority,
            thresholds,
            plan,
        )
        plans[plan.plan_id] = plan
        summaries.append(_candidate_summary(thresholds, plan, audit))
    summaries_tuple = tuple(
        sorted(summaries, key=lambda item: item.contingent_plan_id)
    )
    if (
        len(plans) != candidate_count
        or len(summaries_tuple) != candidate_count
    ):
        raise PartialModelPlannerInvariantViolation(
            "typed global deterministic plan enumeration was not one-to-one"
    )
    selection_mode, selected = _selected_summary(summaries_tuple)
    typed_trace = TypedPartialModelPlannerTraceV2(
        **common_trace_arguments,
        candidate_evaluated_count=candidate_count,
        candidate_summaries=summaries_tuple,
        outcome=PartialModelPlannerOutcome.PLAN_PROPOSED,
        selection_mode=selection_mode,
        selected_plan_id=selected.contingent_plan_id,
        retained_v0045_full_replay_count=1,
        fixed_plan_audit_count=candidate_count,
    )
    return TypedPartialModelPlanProposalResultV2(
        typed_trace, plans[selected.contingent_plan_id]
    )


def verify_partial_model_plan_from_observed_synthesis_v2(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    observed_synthesis_result: (
        observed_synthesis_v1.ObservedTypedPartialRAPMResultV1
    ),
    thresholds: FrozenPartialAuditThresholdsV1,
    claimed_result: TypedPartialModelPlanProposalResultV2,
) -> TypedPartialModelPlanProposalResultV2:
    """Replay synthesis once, internal audits, enumeration, and selection."""

    if type(claimed_result) is not TypedPartialModelPlanProposalResultV2:
        raise PartialModelPlannerInvariantViolation(
            "typed proposal verifier rejects duck result artifacts"
        )
    replayed = propose_partial_model_plan_from_observed_synthesis_v2(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        thresholds,
    )
    if claimed_result.to_document() != replayed.to_document():
        raise PartialModelPlannerInvariantViolation(
            "claimed typed proposal differs from retained full-chain replay"
        )
    return replayed


def propose_partial_model_plan_v1(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    partial_build_result: ObservationPartialRAPMBuildV1,
    thresholds: FrozenPartialAuditThresholdsV1,
) -> PartialModelPlanProposalResultV1:
    """Enumerate with the fixed production cap and return a proposal only."""

    return _propose(
        observation_log,
        coordinate_proposal,
        semantics_profile,
        observation_authority,
        partial_build_result,
        thresholds,
        execution_profile=PartialModelPlannerExecutionProfile.PRODUCTION_CANONICAL,
        candidate_cap=PRODUCTION_CANDIDATE_CAP,
    )


def _propose_partial_model_plan_nonproduction_cap_control_v1(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    partial_build_result: ObservationPartialRAPMBuildV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    *,
    candidate_cap: int,
) -> PartialModelPlanProposalResultV1:
    """Named internal control path; its output can never claim production."""

    if type(candidate_cap) is not int or not 1 <= candidate_cap < (
        PRODUCTION_CANDIDATE_CAP
    ):
        raise PartialModelPlannerInvariantViolation(
            "nonproduction control cap must lie below the production cap"
        )
    return _propose(
        observation_log,
        coordinate_proposal,
        semantics_profile,
        observation_authority,
        partial_build_result,
        thresholds,
        execution_profile=(
            PartialModelPlannerExecutionProfile.NONPRODUCTION_CAP_CONTROL
        ),
        candidate_cap=candidate_cap,
    )


def verify_partial_model_plan_proposal_v1(
    observation_log: ObservationLogManifestV1,
    coordinate_proposal: FrozenCoordinateProposalV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    partial_build_result: ObservationPartialRAPMBuildV1,
    thresholds: FrozenPartialAuditThresholdsV1,
    claimed_result: PartialModelPlanProposalResultV1,
) -> PartialModelPlanProposalResultV1:
    """Independently reconstruct, enumerate, audit, select, and compare bytes."""

    if type(claimed_result) is not PartialModelPlanProposalResultV1:
        raise PartialModelPlannerInvariantViolation(
            "proposal verifier rejects duck result artifacts"
        )
    if (
        claimed_result.trace.execution_profile
        is not PartialModelPlannerExecutionProfile.PRODUCTION_CANONICAL
    ):
        raise PartialModelPlannerInvariantViolation(
            "public verifier accepts production proposals only"
        )
    replayed = propose_partial_model_plan_v1(
        observation_log,
        coordinate_proposal,
        semantics_profile,
        observation_authority,
        partial_build_result,
        thresholds,
    )
    if claimed_result.to_document() != replayed.to_document():
        raise PartialModelPlannerInvariantViolation(
            "claimed proposal differs from full deterministic replay"
        )
    return replayed


__all__ = [
    "PRODUCTION_CANDIDATE_CAP",
    "PRODUCTION_CAP_PROFILE_ID",
    "TYPED_PLANNER_SCHEMA_VERSION",
    "TYPED_PROFILE_KEY",
    "PartialModelPlanProposalResultV1",
    "PartialModelPlannerExecutionProfile",
    "PartialModelPlannerInvariantViolation",
    "PartialModelPlannerOutcome",
    "PartialModelPlannerSelectionMode",
    "PartialModelPlannerTraceV1",
    "PartialPlannerCandidateSummaryV1",
    "PartialPlannerCellActionDomainV1",
    "TypedPartialModelPlanProposalResultV2",
    "TypedPartialModelPlannerTraceV2",
    "propose_partial_model_plan_v1",
    "propose_partial_model_plan_from_observed_synthesis_v2",
    "verify_partial_model_plan_proposal_v1",
    "verify_partial_model_plan_from_observed_synthesis_v2",
]
