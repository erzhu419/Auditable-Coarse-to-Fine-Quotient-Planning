"""Two-domain variable-cardinality relational RAPM campaign.

The campaign composes one independently verified graph-source relational
skeleton with two strictly isolated target consumers:

* the variable-order graph arm; and
* the Layered Matching Buffer arm.

Only the source observation-log identity, skeleton identity, and selected
state/action program identities are shared.  Target contexts, evidence,
models, bindings, and dynamics remain domain-local and content-distinct.

The statistical statement is deliberately conditional.  A Boole union bound
combines the graph arm's registered counter-PRNG/iid-simulator condition and
the LMB arm's registered SHA-256-random-oracle/iid-simulator condition.  No
cross-arm independence or unconditional iid statement is made.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import functools
import hashlib
from typing import Any, Callable, Mapping

import acfqp.cross_domain_lmb_rapm_v1 as lmb
import acfqp.variable_order_graph_rapm_v1 as graph
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.portable_relational_independent_verifier_v1 import (
    IndependentPortableRelationalVerificationV1,
    verify_portable_relational_source_documents_v1,
)
from acfqp.portable_relational_skeleton_v1 import (
    AnonymousRelationalObservationLogV1,
    PortableRelationalSkeletonV1,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.30.0"
PROFILE_KEY = "variable_cardinality_two_domain_relational_rapm_v0"
SUCCESS_STATUS = "CONDITIONAL_TWO_DOMAIN_VARIABLE_CARDINALITY_RAPM_CLOSED"


DOMAIN_TAGS = {
    "calibration": "acfqp:variable-cardinality-multidomain-calibration:v1",
    "dynamics": "acfqp:variable-cardinality-target-dynamics:v1",
    "isolation": "acfqp:variable-cardinality-domain-isolation:v1",
    "transplant": "acfqp:variable-cardinality-cross-arm-transplant:v1",
    "campaign": "acfqp:variable-cardinality-multidomain-campaign:v1",
    "verification": (
        "acfqp:variable-cardinality-multidomain-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("multidomain content domains must be unique")


class VariableCardinalityMultidomainInvariantViolation(ValueError):
    """A source, target-arm, isolation, calibration, or claim invariant failed."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, TypeError, ValueError) as error:
        raise VariableCardinalityMultidomainInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + encoded
    ).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise VariableCardinalityMultidomainInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _canonical_ids(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or not values
        or values != tuple(sorted(set(values)))
    ):
        raise VariableCardinalityMultidomainInvariantViolation(
            f"{field} must be a nonempty canonical ID set"
        )
    for value in values:
        _cid(value, field)
    return values


def _ids(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _dynamics_id(
    domain: str,
    context_id: str,
    context_document: Mapping[str, Any],
) -> str:
    return _content_id(
        "dynamics",
        {
            "schema": "acfqp.variable_cardinality_target_dynamics.v1",
            "schema_version": SCHEMA_VERSION,
            "domain": domain,
            "context_id": context_id,
            "context": dict(context_document),
        },
    )


@dataclass(frozen=True, slots=True)
class VariableCardinalityUnionCalibrationV1:
    graph_calibration_id: str
    lmb_calibration_id: str
    graph_family_tail_upper: Fraction
    lmb_family_tail_upper: Fraction
    union_tail_upper: Fraction
    union_confidence_lower: Fraction
    graph_prng_semantics_id: str
    graph_statistical_claim_scope: str
    lmb_randomness_assumption_id: str
    union_bound_kind: str = (
        "boole_union_bound_without_cross_arm_independence_v1"
    )
    confidence_semantics: str = (
        "conditional_on_both_registered_arm_assumptions_v1"
    )
    cross_arm_independence_required: bool = False
    unconditional_iid_claimed: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.graph_calibration_id, "graph calibration"),
            (self.lmb_calibration_id, "LMB calibration"),
            (
                self.lmb_randomness_assumption_id,
                "LMB randomness assumption",
            ),
        ):
            _cid(value, field)
        fractions = (
            self.graph_family_tail_upper,
            self.lmb_family_tail_upper,
            self.union_tail_upper,
            self.union_confidence_lower,
        )
        if (
            any(type(item) is not Fraction for item in fractions)
            or not 0 <= self.graph_family_tail_upper < 1
            or not 0 <= self.lmb_family_tail_upper < 1
            or self.union_tail_upper
            != self.graph_family_tail_upper + self.lmb_family_tail_upper
            or self.union_confidence_lower != 1 - self.union_tail_upper
            or self.union_confidence_lower <= Fraction(19, 20)
            or self.graph_prng_semantics_id
            != graph.REGISTERED_PRNG_SEMANTICS_ID
            or self.graph_statistical_claim_scope
            != graph.STATISTICAL_CLAIM_SCOPE
            or self.lmb_randomness_assumption_id
            != lmb.lmb_randomness_assumption_v1().assumption_id
            or self.union_bound_kind
            != "boole_union_bound_without_cross_arm_independence_v1"
            or self.confidence_semantics
            != "conditional_on_both_registered_arm_assumptions_v1"
            or self.cross_arm_independence_required is not False
            or self.unconditional_iid_claimed is not False
        ):
            raise VariableCardinalityMultidomainInvariantViolation(
                "multidomain conditional union-bound calibration changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.variable_cardinality_multidomain_calibration.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "graph_calibration_id": self.graph_calibration_id,
            "lmb_calibration_id": self.lmb_calibration_id,
            "graph_family_tail_upper": _fdoc(
                self.graph_family_tail_upper
            ),
            "lmb_family_tail_upper": _fdoc(self.lmb_family_tail_upper),
            "union_tail_upper": _fdoc(self.union_tail_upper),
            "union_confidence_lower": _fdoc(
                self.union_confidence_lower
            ),
            "graph_prng_semantics_id": self.graph_prng_semantics_id,
            "graph_statistical_claim_scope": (
                self.graph_statistical_claim_scope
            ),
            "lmb_randomness_assumption_id": (
                self.lmb_randomness_assumption_id
            ),
            "union_bound_kind": self.union_bound_kind,
            "confidence_semantics": self.confidence_semantics,
            "cross_arm_independence_required": (
                self.cross_arm_independence_required
            ),
            "unconditional_iid_claimed": self.unconditional_iid_claimed,
        }

    @property
    def calibration_id(self) -> str:
        return _content_id("calibration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "calibration_id": self.calibration_id}


def build_variable_cardinality_union_calibration_v1(
    graph_campaign: graph.VariableOrderGraphCampaignV1,
    lmb_campaign: lmb.CrossDomainLMBCampaignV1,
) -> VariableCardinalityUnionCalibrationV1:
    if (
        type(graph_campaign) is not graph.VariableOrderGraphCampaignV1
        or type(lmb_campaign) is not lmb.CrossDomainLMBCampaignV1
    ):
        raise VariableCardinalityMultidomainInvariantViolation(
            "union calibration requires exact arm campaign types"
        )
    graph_tail = graph_campaign.calibration.family_tail_upper
    lmb_tail = lmb_campaign.calibration.family_tail_upper
    return VariableCardinalityUnionCalibrationV1(
        graph_campaign.calibration.calibration_id,
        lmb_campaign.calibration.calibration_id,
        graph_tail,
        lmb_tail,
        graph_tail + lmb_tail,
        1 - graph_tail - lmb_tail,
        graph_campaign.calibration.prng_semantics_id,
        graph_campaign.calibration.statistical_claim_scope,
        lmb_campaign.calibration.randomness_assumption_id,
    )


@dataclass(frozen=True, slots=True)
class VariableCardinalityDomainIsolationV1:
    source_log_id: str
    skeleton_id: str
    state_program_id: str
    action_program_id: str
    graph_context_ids: tuple[str, ...]
    lmb_context_ids: tuple[str, ...]
    graph_evidence_ids: tuple[str, ...]
    lmb_evidence_ids: tuple[str, ...]
    graph_model_ids: tuple[str, ...]
    lmb_model_ids: tuple[str, ...]
    graph_binding_ids: tuple[str, ...]
    lmb_binding_ids: tuple[str, ...]
    graph_dynamics_ids: tuple[str, ...]
    lmb_dynamics_ids: tuple[str, ...]
    same_state_program_id: bool = True
    same_action_program_id: bool = True
    context_identities_isolated: bool = True
    evidence_identities_isolated: bool = True
    model_identities_isolated: bool = True
    binding_identities_isolated: bool = True
    dynamics_identities_isolated: bool = True
    source_registry_rows_imported: int = 0
    source_dynamics_rows_imported: int = 0
    cross_target_transition_rows_imported: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.source_log_id, "isolation source log"),
            (self.skeleton_id, "isolation skeleton"),
            (self.state_program_id, "isolation state program"),
            (self.action_program_id, "isolation action program"),
        ):
            _cid(value, field)
        pairs = (
            (
                _canonical_ids(self.graph_context_ids, "graph contexts"),
                _canonical_ids(self.lmb_context_ids, "LMB contexts"),
                self.context_identities_isolated,
            ),
            (
                _canonical_ids(self.graph_evidence_ids, "graph evidence"),
                _canonical_ids(self.lmb_evidence_ids, "LMB evidence"),
                self.evidence_identities_isolated,
            ),
            (
                _canonical_ids(self.graph_model_ids, "graph models"),
                _canonical_ids(self.lmb_model_ids, "LMB models"),
                self.model_identities_isolated,
            ),
            (
                _canonical_ids(self.graph_binding_ids, "graph bindings"),
                _canonical_ids(self.lmb_binding_ids, "LMB bindings"),
                self.binding_identities_isolated,
            ),
            (
                _canonical_ids(self.graph_dynamics_ids, "graph dynamics"),
                _canonical_ids(self.lmb_dynamics_ids, "LMB dynamics"),
                self.dynamics_identities_isolated,
            ),
        )
        if (
            any(set(left) & set(right) for left, right, _ in pairs)
            or any(flag is not True for _, _, flag in pairs)
            or self.same_state_program_id is not True
            or self.same_action_program_id is not True
            or self.source_registry_rows_imported != 0
            or self.source_dynamics_rows_imported != 0
            or self.cross_target_transition_rows_imported != 0
        ):
            raise VariableCardinalityMultidomainInvariantViolation(
                "target identities crossed domain boundaries"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.variable_cardinality_domain_isolation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "source_log_id": self.source_log_id,
            "skeleton_id": self.skeleton_id,
            "state_program_id": self.state_program_id,
            "action_program_id": self.action_program_id,
            "graph_context_ids": list(self.graph_context_ids),
            "lmb_context_ids": list(self.lmb_context_ids),
            "graph_evidence_ids": list(self.graph_evidence_ids),
            "lmb_evidence_ids": list(self.lmb_evidence_ids),
            "graph_model_ids": list(self.graph_model_ids),
            "lmb_model_ids": list(self.lmb_model_ids),
            "graph_binding_ids": list(self.graph_binding_ids),
            "lmb_binding_ids": list(self.lmb_binding_ids),
            "graph_dynamics_ids": list(self.graph_dynamics_ids),
            "lmb_dynamics_ids": list(self.lmb_dynamics_ids),
            "same_state_program_id": self.same_state_program_id,
            "same_action_program_id": self.same_action_program_id,
            "context_identities_isolated": self.context_identities_isolated,
            "evidence_identities_isolated": self.evidence_identities_isolated,
            "model_identities_isolated": self.model_identities_isolated,
            "binding_identities_isolated": self.binding_identities_isolated,
            "dynamics_identities_isolated": self.dynamics_identities_isolated,
            "source_registry_rows_imported": (
                self.source_registry_rows_imported
            ),
            "source_dynamics_rows_imported": (
                self.source_dynamics_rows_imported
            ),
            "cross_target_transition_rows_imported": (
                self.cross_target_transition_rows_imported
            ),
        }

    @property
    def isolation_id(self) -> str:
        return _content_id("isolation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "isolation_id": self.isolation_id}


def build_variable_cardinality_domain_isolation_v1(
    graph_campaign: graph.VariableOrderGraphCampaignV1,
    lmb_campaign: lmb.CrossDomainLMBCampaignV1,
) -> VariableCardinalityDomainIsolationV1:
    if (
        type(graph_campaign) is not graph.VariableOrderGraphCampaignV1
        or type(lmb_campaign) is not lmb.CrossDomainLMBCampaignV1
        or lmb_campaign.skeleton_id
        != graph_campaign.source_skeleton.skeleton_id
    ):
        raise VariableCardinalityMultidomainInvariantViolation(
            "domain isolation requires one shared source skeleton"
        )
    skeleton = graph_campaign.source_skeleton
    graph_context_ids = _ids(
        tuple(item.context.context_id for item in graph_campaign.results)
    )
    lmb_context_ids = _ids(
        tuple(item.context.context_id for item in lmb_campaign.target_results)
    )
    graph_evidence_ids = _ids(
        tuple(item.evidence.evidence_id for item in graph_campaign.results)
    )
    lmb_evidence_ids = _ids(
        tuple(
            trace.trace_id
            for item in lmb_campaign.target_results
            for trace in (item.first_trace, item.second_trace)
        )
    )
    graph_model_ids = _ids(
        tuple(
            model.model_id
            for item in graph_campaign.results
            for model in (item.base_model, item.final_model)
        )
    )
    lmb_model_ids = _ids(
        tuple(
            model.model_id
            for item in lmb_campaign.target_results
            for model in (
                item.initial_model,
                item.intermediate_model,
                item.final_model,
            )
        )
    )
    graph_binding_ids = _ids(
        tuple(
            profile.profile_id
            for item in graph_campaign.results
            for profile in (item.base_profile, item.final_profile)
        )
    )
    lmb_binding_ids = (lmb_campaign.binding.binding_id,)
    graph_dynamics_ids = _ids(
        tuple(
            _dynamics_id(
                "graph",
                item.context.context_id,
                item.context.to_document(),
            )
            for item in graph_campaign.results
        )
    )
    lmb_dynamics_ids = _ids(
        tuple(
            _dynamics_id(
                "lmb",
                item.context.context_id,
                item.context.to_document(),
            )
            for item in lmb_campaign.target_results
        )
    )
    if (
        graph_campaign.source_transition_rows_imported != 0
        or any(
            item.evidence.source_dynamics_rows_used != 0
            or item.evidence.complete_target_closure_rows_used != 0
            or any(
                event.source_registry_accessed
                or event.source_dynamics_accessed
                for event in item.evidence.access_log.events
            )
            for item in graph_campaign.results
        )
        or any(
            model.source_dynamics_imported
            or model.source_frozen_refinement_registry_used
            or model.exact_target_rows_enumerated != 0
            for item in lmb_campaign.target_results
            for model in (
                item.initial_model,
                item.intermediate_model,
                item.final_model,
            )
        )
    ):
        raise VariableCardinalityMultidomainInvariantViolation(
            "an arm imported forbidden source or target closure rows"
        )
    return VariableCardinalityDomainIsolationV1(
        graph_campaign.source_log.observation_log_id,
        skeleton.skeleton_id,
        skeleton.state_program.program_id,
        skeleton.action_program.program_id,
        graph_context_ids,
        lmb_context_ids,
        graph_evidence_ids,
        lmb_evidence_ids,
        graph_model_ids,
        lmb_model_ids,
        graph_binding_ids,
        lmb_binding_ids,
        graph_dynamics_ids,
        lmb_dynamics_ids,
    )


def _expected_rejection(
    function: Callable[[], Any],
    exception: type[Exception],
) -> bool:
    try:
        function()
    except exception:
        return True
    return False


@dataclass(frozen=True, slots=True)
class VariableCardinalityCrossArmTransplantV1:
    graph_campaign_rejected_by_lmb_verifier: bool
    lmb_campaign_rejected_by_graph_verifier: bool
    lmb_evidence_rejected_by_graph_verifier: bool
    graph_evidence_rejected_by_lmb_verifier: bool
    graph_model_rejected_by_lmb_overlay: bool
    graph_source_log_rejected_as_lmb_bridge: bool
    executed_check_count: int = 6
    declared_only_check_count: int = 0

    def __post_init__(self) -> None:
        flags = (
            self.graph_campaign_rejected_by_lmb_verifier,
            self.lmb_campaign_rejected_by_graph_verifier,
            self.lmb_evidence_rejected_by_graph_verifier,
            self.graph_evidence_rejected_by_lmb_verifier,
            self.graph_model_rejected_by_lmb_overlay,
            self.graph_source_log_rejected_as_lmb_bridge,
        )
        if (
            any(item is not True for item in flags)
            or self.executed_check_count != len(flags)
            or self.declared_only_check_count != 0
        ):
            raise VariableCardinalityMultidomainInvariantViolation(
                "cross-arm type/identity transplants did not fail closed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.variable_cardinality_cross_arm_transplant.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "graph_campaign_rejected_by_lmb_verifier": (
                self.graph_campaign_rejected_by_lmb_verifier
            ),
            "lmb_campaign_rejected_by_graph_verifier": (
                self.lmb_campaign_rejected_by_graph_verifier
            ),
            "lmb_evidence_rejected_by_graph_verifier": (
                self.lmb_evidence_rejected_by_graph_verifier
            ),
            "graph_evidence_rejected_by_lmb_verifier": (
                self.graph_evidence_rejected_by_lmb_verifier
            ),
            "graph_model_rejected_by_lmb_overlay": (
                self.graph_model_rejected_by_lmb_overlay
            ),
            "graph_source_log_rejected_as_lmb_bridge": (
                self.graph_source_log_rejected_as_lmb_bridge
            ),
            "executed_check_count": self.executed_check_count,
            "declared_only_check_count": self.declared_only_check_count,
        }

    @property
    def control_id(self) -> str:
        return _content_id("transplant", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


def run_variable_cardinality_cross_arm_transplants_v1(
    graph_campaign: graph.VariableOrderGraphCampaignV1,
    lmb_campaign: lmb.CrossDomainLMBCampaignV1,
) -> VariableCardinalityCrossArmTransplantV1:
    if (
        type(graph_campaign) is not graph.VariableOrderGraphCampaignV1
        or type(lmb_campaign) is not lmb.CrossDomainLMBCampaignV1
    ):
        raise VariableCardinalityMultidomainInvariantViolation(
            "cross-arm controls require exact campaign types"
        )
    skeleton = graph_campaign.source_skeleton
    graph_result = graph_campaign.results[0]
    lmb_result = lmb_campaign.target_results[0]
    return VariableCardinalityCrossArmTransplantV1(
        _expected_rejection(
            lambda: lmb.verify_cross_domain_lmb_campaign_v1(
                skeleton,
                graph_campaign,  # type: ignore[arg-type]
            ),
            lmb.CrossDomainLMBInvariantViolation,
        ),
        _expected_rejection(
            lambda: graph.verify_variable_order_graph_campaign_v1(
                lmb_campaign,  # type: ignore[arg-type]
            ),
            graph.VariableOrderGraphInvariantViolation,
        ),
        _expected_rejection(
            lambda: graph.verify_sparse_variable_graph_evidence_v1(
                graph_result.context,
                skeleton,
                lmb_result.first_trace,  # type: ignore[arg-type]
            ),
            graph.VariableOrderGraphInvariantViolation,
        ),
        _expected_rejection(
            lambda: lmb.verify_lmb_support_trace_v1(
                lmb_result.context,
                lmb_result.first_authorization,
                graph_result.evidence,  # type: ignore[arg-type]
            ),
            lmb.CrossDomainLMBInvariantViolation,
        ),
        _expected_rejection(
            lambda: lmb.overlay_lmb_statistical_row_v1(
                lmb_result.initial_model,
                graph_result.final_model,  # type: ignore[arg-type]
            ),
            lmb.CrossDomainLMBInvariantViolation,
        ),
        _expected_rejection(
            lambda: lmb.bind_lmb_relational_slot_v1(
                skeleton,
                graph_campaign.source_log,  # type: ignore[arg-type]
            ),
            lmb.CrossDomainLMBInvariantViolation,
        ),
    )


@dataclass(frozen=True, slots=True)
class VariableCardinalityMultidomainCampaignV1:
    source_log: AnonymousRelationalObservationLogV1
    source_skeleton: PortableRelationalSkeletonV1
    independent_source_verification: (
        IndependentPortableRelationalVerificationV1
    )
    graph_campaign: graph.VariableOrderGraphCampaignV1
    graph_verification: graph.VariableOrderGraphCampaignVerificationV1
    lmb_campaign: lmb.CrossDomainLMBCampaignV1
    lmb_verification: lmb.CrossDomainLMBVerificationV1
    union_calibration: VariableCardinalityUnionCalibrationV1
    isolation: VariableCardinalityDomainIsolationV1
    cross_arm_transplant: VariableCardinalityCrossArmTransplantV1
    status: str = SUCCESS_STATUS
    domain_count: int = 2
    graph_target_context_count: int = 3
    lmb_target_context_count: int = 3
    graph_sparse_ground_rows: int = 142
    graph_generative_draws: int = 18_612_224
    graph_sparse_complete_closure_calls: int = 0
    graph_fallback_exact_ground_rows: int = 60
    lmb_operational_support_count: int = 6
    lmb_operational_draws: int = 98_304
    lmb_operational_exact_ground_rows: int = 0
    lmb_standalone_cold_ground_rows: int = 13
    source_registry_rows_imported: int = 0
    source_dynamics_rows_imported: int = 0
    cross_target_transition_rows_imported: int = 0
    independent_source_verification_only: bool = True
    target_same_implementation_verification: bool = True
    independent_target_verification_claimed: bool = False
    automatic_ontology_alignment_claimed: bool = False
    generic_model_selected_planning_claimed: bool = False
    unconditional_statistics_claimed: bool = False
    observational_ood_generalization_claimed: bool = False
    changed_query_reuse_claimed: bool = False
    lmb_reuse_scope: str = (
        "identity_distinct_repeated_occurrence_same_query_parameters_only"
    )
    sample_efficiency_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    counter_completeness_gate: str = "COUNTER_COMPLETENESS_GATE_NOT_RUN"

    def __post_init__(self) -> None:
        exact_types = (
            (self.source_log, AnonymousRelationalObservationLogV1),
            (self.source_skeleton, PortableRelationalSkeletonV1),
            (
                self.independent_source_verification,
                IndependentPortableRelationalVerificationV1,
            ),
            (
                self.graph_campaign,
                graph.VariableOrderGraphCampaignV1,
            ),
            (
                self.graph_verification,
                graph.VariableOrderGraphCampaignVerificationV1,
            ),
            (self.lmb_campaign, lmb.CrossDomainLMBCampaignV1),
            (self.lmb_verification, lmb.CrossDomainLMBVerificationV1),
            (
                self.union_calibration,
                VariableCardinalityUnionCalibrationV1,
            ),
            (self.isolation, VariableCardinalityDomainIsolationV1),
            (
                self.cross_arm_transplant,
                VariableCardinalityCrossArmTransplantV1,
            ),
        )
        if any(type(value) is not expected for value, expected in exact_types):
            raise VariableCardinalityMultidomainInvariantViolation(
                "multidomain campaign runtime type changed"
            )
        if (
            self.source_log.observation_log_id
            != self.graph_campaign.source_log.observation_log_id
            or self.source_skeleton.skeleton_id
            != self.graph_campaign.source_skeleton.skeleton_id
            or self.lmb_campaign.skeleton_id
            != self.source_skeleton.skeleton_id
            or self.independent_source_verification.source_observation_log_id
            != self.source_log.observation_log_id
            or self.independent_source_verification.skeleton_id
            != self.source_skeleton.skeleton_id
            or self.independent_source_verification.independent_implementation
            is not True
            or self.independent_source_verification.producer_imported
            is not False
            or self.graph_verification.campaign_id
            != self.graph_campaign.campaign_id
            or self.lmb_verification.campaign_id
            != self.lmb_campaign.campaign_id
            or self.union_calibration.graph_calibration_id
            != self.graph_campaign.calibration.calibration_id
            or self.union_calibration.lmb_calibration_id
            != self.lmb_campaign.calibration.calibration_id
            or self.isolation.source_log_id
            != self.source_log.observation_log_id
            or self.isolation.skeleton_id != self.source_skeleton.skeleton_id
            or self.status != SUCCESS_STATUS
            or self.domain_count != 2
            or self.graph_target_context_count
            != len(self.graph_campaign.results)
            or self.lmb_target_context_count
            != len(self.lmb_campaign.target_results)
            or self.graph_sparse_ground_rows
            != sum(
                item.evidence.ground_row_count
                for item in self.graph_campaign.results
            )
            or self.graph_generative_draws
            != self.graph_campaign.calibration.family_generative_draws
            or self.graph_sparse_complete_closure_calls
            != self.graph_campaign.sparse_construction_complete_closure_calls
            or self.graph_fallback_exact_ground_rows
            != self.graph_campaign.fallback_exact_ground_rows
            or self.lmb_operational_support_count
            != self.lmb_campaign.operational_support_count
            or self.lmb_operational_draws
            != self.lmb_campaign.operational_target_draw_count
            or self.lmb_operational_exact_ground_rows
            != self.lmb_campaign.operational_exact_ground_row_count
            or self.lmb_standalone_cold_ground_rows
            != self.lmb_campaign.standalone_cold_ground_row_count
            or any(
                value != 0
                for value in (
                    self.source_registry_rows_imported,
                    self.source_dynamics_rows_imported,
                    self.cross_target_transition_rows_imported,
                )
            )
            or self.independent_source_verification_only is not True
            or self.target_same_implementation_verification is not True
            or self.independent_target_verification_claimed is not False
            or self.automatic_ontology_alignment_claimed is not False
            or self.generic_model_selected_planning_claimed is not False
            or self.unconditional_statistics_claimed is not False
            or self.observational_ood_generalization_claimed is not False
            or self.changed_query_reuse_claimed is not False
            or self.lmb_reuse_scope
            != (
                "identity_distinct_repeated_occurrence_same_query_"
                "parameters_only"
            )
            or self.sample_efficiency_claimed is not False
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate
            != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
            or self.counter_completeness_gate
            != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
        ):
            raise VariableCardinalityMultidomainInvariantViolation(
                "multidomain metrics, identity chain, or claim locks changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.variable_cardinality_multidomain_campaign.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_log_id": self.source_log.observation_log_id,
            "source_skeleton_id": self.source_skeleton.skeleton_id,
            "state_program_id": self.source_skeleton.state_program.program_id,
            "action_program_id": (
                self.source_skeleton.action_program.program_id
            ),
            "independent_source_verification_id": (
                self.independent_source_verification.verification_id
            ),
            "graph_campaign_id": self.graph_campaign.campaign_id,
            "graph_verification_id": self.graph_verification.verification_id,
            "lmb_campaign_id": self.lmb_campaign.campaign_id,
            "lmb_verification_id": self.lmb_verification.verification_id,
            "union_calibration_id": self.union_calibration.calibration_id,
            "isolation_id": self.isolation.isolation_id,
            "cross_arm_transplant_id": (
                self.cross_arm_transplant.control_id
            ),
            "status": self.status,
            "domain_count": self.domain_count,
            "metrics": {
                "graph_target_context_count": (
                    self.graph_target_context_count
                ),
                "lmb_target_context_count": self.lmb_target_context_count,
                "graph_sparse_ground_rows": self.graph_sparse_ground_rows,
                "graph_generative_draws": self.graph_generative_draws,
                "graph_sparse_complete_closure_calls": (
                    self.graph_sparse_complete_closure_calls
                ),
                "graph_fallback_exact_ground_rows": (
                    self.graph_fallback_exact_ground_rows
                ),
                "lmb_operational_support_count": (
                    self.lmb_operational_support_count
                ),
                "lmb_operational_draws": self.lmb_operational_draws,
                "lmb_operational_exact_ground_rows": (
                    self.lmb_operational_exact_ground_rows
                ),
                "lmb_standalone_cold_ground_rows": (
                    self.lmb_standalone_cold_ground_rows
                ),
                "source_registry_rows_imported": (
                    self.source_registry_rows_imported
                ),
                "source_dynamics_rows_imported": (
                    self.source_dynamics_rows_imported
                ),
                "cross_target_transition_rows_imported": (
                    self.cross_target_transition_rows_imported
                ),
            },
            "claims": {
                "independent_source_verification_only": (
                    self.independent_source_verification_only
                ),
                "target_same_implementation_verification": (
                    self.target_same_implementation_verification
                ),
                "independent_target_verification_claimed": (
                    self.independent_target_verification_claimed
                ),
                "automatic_ontology_alignment_claimed": (
                    self.automatic_ontology_alignment_claimed
                ),
                "generic_model_selected_planning_claimed": (
                    self.generic_model_selected_planning_claimed
                ),
                "unconditional_statistics_claimed": (
                    self.unconditional_statistics_claimed
                ),
                "observational_ood_generalization_claimed": (
                    self.observational_ood_generalization_claimed
                ),
                "changed_query_reuse_claimed": (
                    self.changed_query_reuse_claimed
                ),
                "lmb_reuse_scope": self.lmb_reuse_scope,
                "sample_efficiency_claimed": (
                    self.sample_efficiency_claimed
                ),
            },
            "official_execution_allowed": self.official_execution_allowed,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "workload_economics_gate": self.workload_economics_gate,
            "counter_completeness_gate": self.counter_completeness_gate,
        }

    @property
    def campaign_id(self) -> str:
        return _content_id("campaign", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_id": self.campaign_id}


def _assemble_campaign_v1(
    graph_campaign: graph.VariableOrderGraphCampaignV1,
    lmb_campaign: lmb.CrossDomainLMBCampaignV1,
    source_verification: IndependentPortableRelationalVerificationV1,
    graph_verification: graph.VariableOrderGraphCampaignVerificationV1,
    lmb_verification: lmb.CrossDomainLMBVerificationV1,
) -> VariableCardinalityMultidomainCampaignV1:
    return VariableCardinalityMultidomainCampaignV1(
        graph_campaign.source_log,
        graph_campaign.source_skeleton,
        source_verification,
        graph_campaign,
        graph_verification,
        lmb_campaign,
        lmb_verification,
        build_variable_cardinality_union_calibration_v1(
            graph_campaign,
            lmb_campaign,
        ),
        build_variable_cardinality_domain_isolation_v1(
            graph_campaign,
            lmb_campaign,
        ),
        run_variable_cardinality_cross_arm_transplants_v1(
            graph_campaign,
            lmb_campaign,
        ),
    )


@functools.lru_cache(maxsize=1)
def run_variable_cardinality_multidomain_campaign_v1(
) -> VariableCardinalityMultidomainCampaignV1:
    graph_campaign = graph.run_variable_order_graph_campaign_v1()
    source_verification = verify_portable_relational_source_documents_v1(
        graph_campaign.source_log.to_document(),
        graph_campaign.source_skeleton.to_document(),
    )
    graph_verification = graph.verify_variable_order_graph_campaign_v1(
        graph_campaign
    )
    lmb_campaign = lmb.run_cross_domain_lmb_campaign_v1(
        graph_campaign.source_skeleton
    )
    lmb_verification = lmb.verify_cross_domain_lmb_campaign_v1(
        graph_campaign.source_skeleton,
        lmb_campaign,
    )
    return _assemble_campaign_v1(
        graph_campaign,
        lmb_campaign,
        source_verification,
        graph_verification,
        lmb_verification,
    )


@dataclass(frozen=True, slots=True)
class VariableCardinalityMultidomainVerificationV1:
    campaign_id: str
    independent_source_verification_id: str
    graph_verification_id: str
    lmb_verification_id: str
    union_calibration_id: str
    isolation_id: str
    cross_arm_transplant_id: str
    verified_domain_count: int = 2
    independent_source_verified: bool = True
    graph_target_same_implementation_verified: bool = True
    lmb_target_same_implementation_verified: bool = True
    independent_target_verification_claimed: bool = False
    conditional_union_bound_verified: bool = True
    claim_locks_verified: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.campaign_id, "verification campaign"),
            (
                self.independent_source_verification_id,
                "verification independent source",
            ),
            (self.graph_verification_id, "verification graph arm"),
            (self.lmb_verification_id, "verification LMB arm"),
            (self.union_calibration_id, "verification calibration"),
            (self.isolation_id, "verification isolation"),
            (self.cross_arm_transplant_id, "verification transplant"),
        ):
            _cid(value, field)
        if (
            self.verified_domain_count != 2
            or self.independent_source_verified is not True
            or self.graph_target_same_implementation_verified is not True
            or self.lmb_target_same_implementation_verified is not True
            or self.independent_target_verification_claimed is not False
            or self.conditional_union_bound_verified is not True
            or self.claim_locks_verified is not True
        ):
            raise VariableCardinalityMultidomainInvariantViolation(
                "multidomain verification scope or result changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.variable_cardinality_multidomain_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "independent_source_verification_id": (
                self.independent_source_verification_id
            ),
            "graph_verification_id": self.graph_verification_id,
            "lmb_verification_id": self.lmb_verification_id,
            "union_calibration_id": self.union_calibration_id,
            "isolation_id": self.isolation_id,
            "cross_arm_transplant_id": self.cross_arm_transplant_id,
            "verified_domain_count": self.verified_domain_count,
            "independent_source_verified": (
                self.independent_source_verified
            ),
            "graph_target_same_implementation_verified": (
                self.graph_target_same_implementation_verified
            ),
            "lmb_target_same_implementation_verified": (
                self.lmb_target_same_implementation_verified
            ),
            "independent_target_verification_claimed": (
                self.independent_target_verification_claimed
            ),
            "conditional_union_bound_verified": (
                self.conditional_union_bound_verified
            ),
            "claim_locks_verified": self.claim_locks_verified,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


@functools.lru_cache(maxsize=1)
def verify_variable_cardinality_multidomain_campaign_v1(
    claimed: VariableCardinalityMultidomainCampaignV1,
) -> VariableCardinalityMultidomainVerificationV1:
    if type(claimed) is not VariableCardinalityMultidomainCampaignV1:
        raise VariableCardinalityMultidomainInvariantViolation(
            "multidomain verifier rejects runtime substitutions"
        )
    # Revalidate frozen fields before any expensive arm replay so obvious
    # claim-lock or nested-type tampering fails closed immediately.
    claimed.__post_init__()
    source_verification = verify_portable_relational_source_documents_v1(
        claimed.source_log.to_document(),
        claimed.source_skeleton.to_document(),
    )
    graph_verification = graph.verify_variable_order_graph_campaign_v1(
        claimed.graph_campaign
    )
    lmb_verification = lmb.verify_cross_domain_lmb_campaign_v1(
        claimed.source_skeleton,
        claimed.lmb_campaign,
    )
    expected = _assemble_campaign_v1(
        claimed.graph_campaign,
        claimed.lmb_campaign,
        source_verification,
        graph_verification,
        lmb_verification,
    )
    if claimed.to_document() != expected.to_document():
        raise VariableCardinalityMultidomainInvariantViolation(
            "multidomain campaign differs from semantic replay"
        )
    return VariableCardinalityMultidomainVerificationV1(
        claimed.campaign_id,
        source_verification.verification_id,
        graph_verification.verification_id,
        lmb_verification.verification_id,
        expected.union_calibration.calibration_id,
        expected.isolation.isolation_id,
        expected.cross_arm_transplant.control_id,
    )


__all__ = [
    "CONTRACT_VERSION",
    "PROFILE_KEY",
    "SUCCESS_STATUS",
    "VariableCardinalityCrossArmTransplantV1",
    "VariableCardinalityDomainIsolationV1",
    "VariableCardinalityMultidomainCampaignV1",
    "VariableCardinalityMultidomainInvariantViolation",
    "VariableCardinalityMultidomainVerificationV1",
    "VariableCardinalityUnionCalibrationV1",
    "build_variable_cardinality_domain_isolation_v1",
    "build_variable_cardinality_union_calibration_v1",
    "run_variable_cardinality_cross_arm_transplants_v1",
    "run_variable_cardinality_multidomain_campaign_v1",
    "verify_variable_cardinality_multidomain_campaign_v1",
]
