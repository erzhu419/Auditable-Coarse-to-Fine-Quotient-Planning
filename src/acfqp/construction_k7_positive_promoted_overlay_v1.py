"""Positive cross-occurrence control for a reusable abstract world model.

One preregistered V0-075 H=2 occurrence first fails its abstract proof, then
acquires only the authorized local child rows and produces a positive
observation-driven candidate.  This module projects that final learned graph
to the query-neutral V2 numerical model, freezes it as an immutable promoted
epoch, and plans one fresh occurrence from the promoted model without an
observer, kernel, transition law, or new ground draw.

The selected fresh policy is evaluated against the already frozen
construction-only exact replay in a separate evaluation lane.  That check is
useful as a positive construction certificate, but it is deliberately not a
scientific endpoint, production, official-execution, or workload-economics
claim.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from fractions import Fraction
from typing import Any, Mapping, NoReturn

from acfqp import v075_batched_causal_occurrence_successor_v1 as successor_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_batch_native_total_lift_authority_v1 as total_lift_v1
from acfqp import v075_learned_support_quotient_planners_v1 as planners_v1
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_POSITIVE_PROMOTED_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_EXACT_LIFT_BINDING_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_EPOCH_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_QUERY_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.115"
PROFILE_KEY = "construction_k7_positive_promoted_overlay_v1"

EPOCH_DOMAIN = CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_EPOCH_V1_DOMAIN
QUERY_DOMAIN = CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_QUERY_V1_DOMAIN
PLAN_DOMAIN = CONSTRUCTION_K7_POSITIVE_PROMOTED_ABSTRACT_PLAN_V1_DOMAIN
EXACT_LIFT_DOMAIN = (
    CONSTRUCTION_K7_POSITIVE_PROMOTED_EXACT_LIFT_BINDING_V1_DOMAIN
)
RESULT_DOMAIN = CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {EPOCH_DOMAIN, QUERY_DOMAIN, PLAN_DOMAIN, EXACT_LIFT_DOMAIN, RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 5 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("positive promoted-overlay domains are not central")

OFFICIAL_EXECUTION_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"

_EPOCH_ISSUER = object()
_QUERY_ISSUER = object()
_PLAN_ISSUER = object()
_EXACT_LIFT_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7PositivePromotedOverlayV1Error(ValueError):
    """The positive source, projection, fresh plan, or exact lift changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PositivePromotedOverlayV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7PositivePromotedOverlayV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("positive promoted-overlay arithmetic must remain exact")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _policy_signature(
    policy: planning_v2.V075DeterministicPolicyV2,
) -> tuple[tuple[str, int, tuple[int, int, int]], ...]:
    if type(policy) is not planning_v2.V075DeterministicPolicyV2:
        _fail("fresh promoted policy is untyped")
    return tuple(
        sorted(
            (
                choice.state_id,
                decision.remaining_horizon,
                action,
            )
            for decision in policy.decisions
            for choice in decision.state_choices
            for action in choice.ground_actions
        )
    )


def _source_policy_signature(
    policy: planners_v1.V075DeterministicH2PolicyV1,
) -> tuple[tuple[str, int, tuple[int, int, int]], ...]:
    if type(policy) is not planners_v1.V075DeterministicH2PolicyV1:
        _fail("source promoted policy is untyped")
    return tuple(
        sorted(
            (
                choice.state_id,
                decision.remaining_horizon,
                action,
            )
            for decision in policy.decisions
            for choice in decision.state_choices
            for action in choice.ground_actions
        )
    )


def _require_positive_source(
    value: successor_v1.V075BatchedCausalOccurrencePrecloseResultV1,
) -> successor_v1.V075BatchedCausalOccurrenceVerificationV1:
    if type(value) is not successor_v1.V075BatchedCausalOccurrencePrecloseResultV1:
        _fail("positive promoted overlay requires one typed source occurrence")
    try:
        verification = (
            successor_v1.verify_v075_batched_causal_occurrence_successor_v1(
                value
            )
        )
    except Exception as error:
        raise ConstructionK7PositivePromotedOverlayV1Error(
            "positive source failed public backend/planner replay"
        ) from error
    graph = value.final_planner_result.graph
    initial_frontier = (
        value.initial_planner_result.diagnostic_failed_frontier_row_ids
    )
    final_policy = value.final_planner_result.policy
    if (
        verification.result_id != value.result_id
        or value.initial_planner_result.status
        is not planners_v1.V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY
        or not initial_frontier
        or value.final_planner_result.status
        is not (
            planners_v1.V075PlannerStatusV1
            .CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT
        )
        or not value.ready_for_exact_total_lift
        or type(final_policy) is not planners_v1.V075DeterministicH2PolicyV1
        or value.final_planner_result.envelope is None
        or value.final_planner_result.diagnostic_failed_frontier_row_ids
        or value.counters.incremental_draws <= 0
        or value.counters.child_action_rows_materialized <= 0
        or len(value.authorization.selected_candidate_ids) <= 1
        or value.counters.backend_compilations != 2
        or value.counters.planner_invocations != 2
        or value.counters.process_launches != 0
        or graph.context.horizon != 2
        or any(not row.intervals for node in graph.nodes for row in node.rows)
    ):
        _fail("source is not the preregistered failed-then-recovered H=2 control")
    return verification


def _project_query_neutral_model(
    source: successor_v1.V075BatchedCausalOccurrencePrecloseResultV1,
) -> planning_v2.V075NumericalModelV2:
    """Project signed V1 aggregates while discarding acquisition provenance."""

    graph = source.final_planner_result.graph
    if planning_v2.ROW_BETA != Fraction(1, 300_000):
        _fail("V2 registered row confidence allocation changed")
    rows: list[planning_v2.V075NumericalRowV2] = []
    for node in graph.nodes:
        for old_row in node.rows:
            old_by_semantics = {
                (item.next_ranks, item.failure, item.terminal): item
                for item in old_row.support
            }
            if len(old_by_semantics) != len(old_row.support):
                _fail("source row support is not semantically unique")
            support = tuple(
                sorted(
                    (
                        planning_v2.V075SupportDescriptorV2(
                            planning_v2._DESCRIPTOR_ISSUER,
                            item.context_id,
                            item.next_state_id,
                            item.next_ranks,
                            item.failure,
                            item.terminal,
                        )
                        for item in old_row.support
                    ),
                    key=lambda item: item.descriptor_id,
                )
            )
            old_intervals = {item.event_key: item for item in old_row.intervals}
            if len(old_intervals) != len(old_row.intervals):
                _fail("source row confidence events are duplicated")
            event_alpha = planning_v2.ROW_BETA / len(old_row.intervals)
            intervals: list[planning_v2.V075EventIntervalV2] = []
            for descriptor in support:
                old_descriptor = old_by_semantics[
                    (
                        descriptor.next_ranks,
                        descriptor.failure,
                        descriptor.terminal,
                    )
                ]
                old_interval = old_intervals[old_descriptor.descriptor_id]
                intervals.append(
                    planning_v2.V075EventIntervalV2(
                        planning_v2._INTERVAL_ISSUER,
                        descriptor.descriptor_id,
                        descriptor,
                        old_interval.draw_count,
                        old_interval.success_count,
                        old_interval.empirical_probability,
                        old_interval.lower_probability,
                        old_interval.upper_probability,
                        event_alpha,
                        old_interval.exact_likelihood_comparisons,
                        old_interval.log_search_evaluations,
                        planning_v2.EXACT_BERNOULLI_METHOD_ID,
                    )
                )
            other = old_intervals.get("OTHER")
            if other is None:
                _fail("source row lacks its explicit OTHER confidence event")
            intervals.append(
                planning_v2.V075EventIntervalV2(
                    planning_v2._INTERVAL_ISSUER,
                    "OTHER",
                    None,
                    other.draw_count,
                    other.success_count,
                    other.empirical_probability,
                    other.lower_probability,
                    other.upper_probability,
                    event_alpha,
                    other.exact_likelihood_comparisons,
                    other.log_search_evaluations,
                    planning_v2.EXACT_BERNOULLI_METHOD_ID,
                )
            )
            rewards = {
                descriptor.realized_row_reward
                for descriptor in old_row.support
            }
            if len(rewards) != 1:
                _fail("source row has outcome-dependent immediate rewards")
            rows.append(
                planning_v2.V075NumericalRowV2(
                    planning_v2._ROW_ISSUER,
                    old_row.context_id,
                    old_row.row_binding_id,
                    old_row.source_state_id,
                    node.catalogue.state.ranks,
                    old_row.remaining_horizon,
                    old_row.action,
                    next(iter(rewards)),
                    support,
                    tuple(intervals),
                )
            )
    model = planning_v2.V075NumericalModelV2(
        planning_v2._MODEL_ISSUER,
        graph.context,
        tuple(sorted(rows, key=lambda item: item.row_id)),
        "SIGNED_V2_AGGREGATES",
    )
    try:
        replayed = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(model.to_document())
        )
    except Exception as error:
        raise ConstructionK7PositivePromotedOverlayV1Error(
            "projected query-neutral model failed portable replay"
        ) from error
    if replayed != model:
        _fail("projected query-neutral model differs from portable replay")
    return model


@dataclass(frozen=True, slots=True)
class PositivePromotedOverlayEpochV1:
    _issuer: InitVar[object]
    source: successor_v1.V075BatchedCausalOccurrencePrecloseResultV1 = field(
        repr=False
    )
    model: planning_v2.V075NumericalModelV2 = field(repr=False)
    _epoch_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _EPOCH_ISSUER
            or type(self.source)
            is not successor_v1.V075BatchedCausalOccurrencePrecloseResultV1
            or type(self.model) is not planning_v2.V075NumericalModelV2
        ):
            _fail("positive promoted epoch is caller-minted")
        document = self.model.to_document()
        if (
            self.model.context != self.source.final_planner_result.graph.context
            or len(self.model.rows) != sum(
                len(node.rows)
                for node in self.source.final_planner_result.graph.nodes
            )
            or document.get("occurrence_or_arm_fields_present") is not False
            or document.get("private_law_access") is not False
        ):
            _fail("positive promoted epoch changed during projection")
        object.__setattr__(self, "_epoch_id", content_id(EPOCH_DOMAIN, self._payload()))

    @property
    def source_occurrence_id(self) -> str:
        return self.source.occurrence_identity.occurrence_id

    def _payload(self) -> dict[str, Any]:
        graph = self.source.final_planner_result.graph
        return {
            "schema": "acfqp.construction_k7_positive_promoted_overlay_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_batched_causal_result_id": self.source.result_id,
            "source_occurrence_id": self.source_occurrence_id,
            "source_occurrence_ordinal": (
                self.source.occurrence_identity.occurrence_ordinal
            ),
            "source_initial_planner_result_id": (
                self.source.initial_planner_result.result_id
            ),
            "source_initial_proof_status": (
                self.source.initial_planner_result.status.value
            ),
            "source_initial_failed_frontier_row_ids": list(
                self.source.initial_planner_result
                .diagnostic_failed_frontier_row_ids
            ),
            "source_causal_authorization_id": self.source.authorization.authorization_id,
            "source_selected_causal_candidate_count": len(
                self.source.authorization.selected_candidate_ids
            ),
            "source_incremental_local_draw_count": self.source.counters.incremental_draws,
            "source_child_action_rows_materialized": (
                self.source.counters.child_action_rows_materialized
            ),
            "source_final_planner_result_id": (
                self.source.final_planner_result.result_id
            ),
            "source_final_proof_status": self.source.final_planner_result.status.value,
            "source_learned_support_graph_id": graph.graph_id,
            "promoted_numerical_model_id": self.model.model_id,
            "promoted_row_count": len(self.model.rows),
            "promoted_state_node_count": len(graph.nodes),
            "promotion_kind": "QUERY_NEUTRAL_SIGNED_AGGREGATE_WORLD_MODEL",
            "failed_certificate_preceded_local_distinction_recovery": True,
            "only_authorized_local_child_rows_acquired": True,
            "observation_capability_identity_projected_out": True,
            "occurrence_and_arm_identity_projected_out": True,
            "private_transition_law_projected_out": True,
            "query_neutral_model_reusable_across_occurrences": True,
            "automatic_coordinate_invention_claimed": False,
            "ground_access_during_promotion": 0,
            "planner_calls_during_promotion": 0,
            "immutable_promoted_epoch": True,
            "official_execution_allowed": False,
        }

    @property
    def epoch_id(self) -> str:
        current = content_id(EPOCH_DOMAIN, self._payload())
        if current != self._epoch_id:
            _fail("positive promoted epoch changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "promoted_numerical_model": self.model.to_document(),
            "positive_promoted_overlay_epoch_id": self.epoch_id,
        }


def promote_positive_query_neutral_overlay_v1(
    source: successor_v1.V075BatchedCausalOccurrencePrecloseResultV1,
) -> PositivePromotedOverlayEpochV1:
    _require_positive_source(source)
    return PositivePromotedOverlayEpochV1(
        _EPOCH_ISSUER,
        source,
        _project_query_neutral_model(source),
    )


@dataclass(frozen=True, slots=True)
class PositivePromotedOverlayQueryV1:
    _issuer: InitVar[object]
    epoch: PositivePromotedOverlayEpochV1 = field(repr=False)
    logical_occurrence_id: str
    query_ordinal: int
    threshold_profile_id: str
    _query_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _QUERY_ISSUER
            or type(self.epoch) is not PositivePromotedOverlayEpochV1
        ):
            _fail("positive promoted query is caller-minted")
        self.epoch.epoch_id
        for value, label in (
            (self.logical_occurrence_id, "fresh logical occurrence"),
            (self.threshold_profile_id, "fresh threshold profile"),
        ):
            _cid(value, label)
        source_identity = self.epoch.source.occurrence_identity
        if (
            self.logical_occurrence_id == source_identity.occurrence_id
            or type(self.query_ordinal) is not int
            or self.query_ordinal != source_identity.occurrence_ordinal + 1
            or self.threshold_profile_id != source_identity.threshold_profile_id
            or self.threshold_profile_id
            != worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id
        ):
            _fail("fresh promoted query identity or threshold changed")
        object.__setattr__(self, "_query_id", content_id(QUERY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_positive_promoted_overlay_query.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "positive_promoted_overlay_epoch_id": self.epoch.epoch_id,
            "promoted_numerical_model_id": self.epoch.model.model_id,
            "source_occurrence_id": self.epoch.source_occurrence_id,
            "source_occurrence_ordinal": (
                self.epoch.source.occurrence_identity.occurrence_ordinal
            ),
            "logical_occurrence_id": self.logical_occurrence_id,
            "query_ordinal": self.query_ordinal,
            "context_id": self.epoch.model.context.context_id,
            "horizon": self.epoch.model.context.horizon,
            "threshold_profile_id": self.threshold_profile_id,
            "route": planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT.value,
            "promoted_epoch_frozen_before_fresh_planning": True,
            "observer_or_ground_input_present": False,
            "same_registered_structural_query": True,
            "independent_random_tape_claimed": False,
        }

    @property
    def query_id(self) -> str:
        current = content_id(QUERY_DOMAIN, self._payload())
        if current != self._query_id:
            _fail("positive promoted query changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "positive_promoted_overlay_query_id": self.query_id}


def freeze_positive_promoted_overlay_query_v1(
    epoch: PositivePromotedOverlayEpochV1,
    *,
    logical_occurrence_id: str,
    query_ordinal: int,
) -> PositivePromotedOverlayQueryV1:
    if type(epoch) is not PositivePromotedOverlayEpochV1:
        _fail("positive promoted query requires one exact epoch")
    return PositivePromotedOverlayQueryV1(
        _QUERY_ISSUER,
        epoch,
        _cid(logical_occurrence_id, "fresh logical occurrence"),
        query_ordinal,
        worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id,
    )


@dataclass(frozen=True, slots=True)
class PositivePromotedAbstractPlanV1:
    _issuer: InitVar[object]
    query: PositivePromotedOverlayQueryV1 = field(repr=False)
    proof: planning_v2.V075NumericalPlanningProofV2 = field(repr=False)
    _plan_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PLAN_ISSUER
            or type(self.query) is not PositivePromotedOverlayQueryV1
            or type(self.proof) is not planning_v2.V075NumericalPlanningProofV2
        ):
            _fail("positive promoted abstract plan is caller-minted")
        self.query.query_id
        if (
            self.proof.model != self.query.epoch.model
            or self.proof.route
            is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            or self.proof.outcome is not planning_v2.V075NumericalOutcomeV2.CANDIDATE
            or self.proof.policy is None
            or self.proof.envelope is None
            or self.proof.failed_frontier is not None
        ):
            _fail("fresh promoted model did not produce one abstract candidate")
        object.__setattr__(self, "_plan_id", content_id(PLAN_DOMAIN, self._payload()))

    @property
    def policy_signature(
        self,
    ) -> tuple[tuple[str, int, tuple[int, int, int]], ...]:
        assert self.proof.policy is not None
        return _policy_signature(self.proof.policy)

    def _payload(self) -> dict[str, Any]:
        assert self.proof.policy is not None
        assert self.proof.envelope is not None
        return {
            "schema": "acfqp.construction_k7_positive_promoted_abstract_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "positive_promoted_overlay_query_id": self.query.query_id,
            "logical_occurrence_id": self.query.logical_occurrence_id,
            "promoted_numerical_model_id": self.query.epoch.model.model_id,
            "fresh_numerical_proof_id": self.proof.proof_id,
            "fresh_policy_id": self.proof.policy.policy_id,
            "fresh_envelope_id": self.proof.envelope.envelope_id,
            "fresh_outcome": self.proof.outcome.value,
            "policy_assignments_evaluated": self.proof.policy_assignments_evaluated,
            "fresh_policy_signature": [
                {
                    "state_id": state_id,
                    "remaining_horizon": horizon,
                    "ground_action": list(action),
                }
                for state_id, horizon, action in self.policy_signature
            ],
            "operational_planner_call_count": 1,
            "operational_model_build_count": 0,
            "operational_new_ground_draw_count": 0,
            "operational_observer_call_count": 0,
            "operational_private_law_access_count": 0,
            "multi_step_plan_formed_in_abstract_model": True,
            "exact_total_lift_not_run_in_operational_lane": True,
            "generic_v2_proof_is_not_yet_a_plan_certificate": True,
            "plan_certificate_issued_here": False,
            "official_execution_allowed": False,
        }

    @property
    def plan_id(self) -> str:
        current = content_id(PLAN_DOMAIN, self._payload())
        if current != self._plan_id:
            _fail("positive promoted abstract plan changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "fresh_numerical_proof": self.proof.to_document(),
            "positive_promoted_abstract_plan_id": self.plan_id,
        }


def plan_positive_promoted_overlay_query_v1(
    query: PositivePromotedOverlayQueryV1,
) -> PositivePromotedAbstractPlanV1:
    if type(query) is not PositivePromotedOverlayQueryV1:
        _fail("fresh abstract planning requires one exact promoted query")
    proof = planning_v2.plan_v075_construction_numerical_model_v2(
        model=query.epoch.model,
        route=planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    return PositivePromotedAbstractPlanV1(_PLAN_ISSUER, query, proof)


@dataclass(frozen=True, slots=True)
class _FreshExactMetricsV1:
    selected_reward: Fraction
    environment_failure: Fraction
    policy_abort_failure: Fraction
    selected_failure: Fraction
    exact_normalized_regret: Fraction
    partitions: tuple[total_lift_v1.V075BatchLiftBranchPartitionV1, ...]


def _fresh_exact_metrics(
    *,
    plan: PositivePromotedAbstractPlanV1,
    exact_replay: total_lift_v1.V075BatchNativeConstructionExactReplayV1,
    optimal_expected_reward: Fraction,
) -> _FreshExactMetricsV1:
    policy = plan.proof.policy
    if policy is None:
        _fail("fresh exact lift lacks an abstract policy")
    model = plan.query.epoch.model
    rows_by_key = {
        (row.source_state_id, row.remaining_horizon, row.action): row
        for row in model.rows
    }
    if len(rows_by_key) != len(model.rows):
        _fail("fresh promoted model repeats one state-time-action row")
    exact_by_key = {
        (
            row.row_binding.state_id,
            row.row_binding.remaining_horizon,
            row.row_binding.action,
        ): row
        for row in exact_replay.rows
    }
    if len(exact_by_key) != len(exact_replay.rows):
        _fail("construction exact replay repeats one state-time-action row")
    choices: dict[tuple[str, int], planning_v2.V075PolicyStateChoiceV2] = {}
    for decision in policy.decisions:
        for choice in decision.state_choices:
            key = (choice.state_id, decision.remaining_horizon)
            if key in choices:
                _fail("fresh abstract policy repeats one state-time decision")
            choices[key] = choice
    root_states = {
        row.source_state_id for row in model.rows if row.remaining_horizon == 2
    }
    if len(root_states) != 1:
        _fail("fresh promoted model lacks one exact H=2 root")
    root_state_id = next(iter(root_states))
    root_choice = choices.get((root_state_id, 2))
    if root_choice is None:
        _fail("fresh abstract policy lacks the actual root decision")

    selected_reward = Fraction(0)
    environment_failure = Fraction(0)
    policy_abort = Fraction(0)
    partitions: list[total_lift_v1.V075BatchLiftBranchPartitionV1] = []

    def evaluate_row(
        *,
        state_id: str,
        remaining_horizon: int,
        action: tuple[int, int, int],
        statistical_row_id: str,
        execution_weight: Fraction,
    ) -> dict[str, Fraction]:
        nonlocal selected_reward, environment_failure, policy_abort
        row = rows_by_key.get((state_id, remaining_horizon, action))
        exact_row = exact_by_key.get((state_id, remaining_horizon, action))
        if (
            row is None
            or exact_row is None
            or row.row_id != statistical_row_id
            or row.immediate_reward != exact_row.reward
            or not 0 < execution_weight <= 1
        ):
            _fail("fresh policy row does not bind one exact replay row")
        modeled_keys = {
            (item.next_state_id, item.failure, item.terminal)
            for item in row.support
        }
        environment_ids: list[str] = []
        modeled_ids: list[str] = []
        abort_ids: list[str] = []
        recurse: dict[str, Fraction] = {}
        selected_reward += execution_weight * exact_row.reward
        for atom in exact_row.atoms:
            semantic_key = (
                atom.next_state_id,
                atom.atom.failure,
                atom.atom.terminal,
            )
            weighted_probability = execution_weight * atom.atom.probability
            if atom.atom.failure:
                environment_ids.append(atom.atom_id)
                environment_failure += weighted_probability
            elif semantic_key not in modeled_keys:
                abort_ids.append(atom.atom_id)
                policy_abort += weighted_probability
            elif remaining_horizon == 1:
                modeled_ids.append(atom.atom_id)
            elif (atom.next_state_id, 1) not in choices:
                abort_ids.append(atom.atom_id)
                policy_abort += weighted_probability
            else:
                modeled_ids.append(atom.atom_id)
                recurse[atom.next_state_id] = (
                    recurse.get(atom.next_state_id, Fraction(0))
                    + atom.atom.probability
                )
        partitions.append(
            total_lift_v1.V075BatchLiftBranchPartitionV1(
                state_id,
                remaining_horizon,
                action,
                statistical_row_id,
                exact_row.row_id,
                execution_weight,
                tuple(
                    (atom.atom_id, atom.atom.probability)
                    for atom in exact_row.atoms
                ),
                tuple(sorted(environment_ids)),
                tuple(sorted(modeled_ids)),
                tuple(sorted(abort_ids)),
            )
        )
        return recurse

    for root_action, root_row_id, root_weight in zip(
        root_choice.ground_actions,
        root_choice.row_ids,
        root_choice.uniform_weights,
        strict=True,
    ):
        recurse = evaluate_row(
            state_id=root_state_id,
            remaining_horizon=2,
            action=root_action,
            statistical_row_id=root_row_id,
            execution_weight=root_weight,
        )
        for child_state_id in sorted(recurse):
            child_choice = choices[(child_state_id, 1)]
            for child_action, child_row_id, child_weight in zip(
                child_choice.ground_actions,
                child_choice.row_ids,
                child_choice.uniform_weights,
                strict=True,
            ):
                evaluate_row(
                    state_id=child_state_id,
                    remaining_horizon=1,
                    action=child_action,
                    statistical_row_id=child_row_id,
                    execution_weight=(
                        root_weight * recurse[child_state_id] * child_weight
                    ),
                )
    selected_failure = environment_failure + policy_abort
    threshold = worker_v1.V075WorkerThresholdProfileV1()
    exact_regret = (
        optimal_expected_reward - selected_reward
    ) / threshold.reward_ceiling
    if exact_regret < 0 or not 0 <= selected_failure <= 1:
        _fail("fresh exact lift exceeds the registered ground optimum")
    return _FreshExactMetricsV1(
        selected_reward,
        environment_failure,
        policy_abort,
        selected_failure,
        exact_regret,
        tuple(
            sorted(
                partitions,
                key=lambda item: (
                    -item.remaining_horizon,
                    item.source_state_id,
                    item.ground_action,
                ),
            )
        ),
    )


@dataclass(frozen=True, slots=True)
class PositivePromotedExactLiftBindingV1:
    _issuer: InitVar[object]
    plan: PositivePromotedAbstractPlanV1 = field(repr=False)
    lineage: total_lift_v1.V075BatchNativeLineageBindingV1 = field(repr=False)
    exact_replay: total_lift_v1.V075BatchNativeConstructionExactReplayV1 = field(
        repr=False
    )
    source_verification: (
        total_lift_v1.V075BatchNativeConstructionTotalLiftVerificationV1
    ) = field(repr=False)
    metrics: _FreshExactMetricsV1 = field(repr=False)
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _EXACT_LIFT_ISSUER
            or type(self.plan) is not PositivePromotedAbstractPlanV1
            or type(self.lineage) is not total_lift_v1.V075BatchNativeLineageBindingV1
            or type(self.exact_replay)
            is not total_lift_v1.V075BatchNativeConstructionExactReplayV1
            or type(self.source_verification)
            is not (
                total_lift_v1
                .V075BatchNativeConstructionTotalLiftVerificationV1
            )
            or type(self.metrics) is not _FreshExactMetricsV1
        ):
            _fail("positive promoted exact lift is caller-minted")
        source = self.plan.query.epoch.source
        candidate = self.source_verification.candidate
        envelope = self.plan.proof.envelope
        threshold = worker_v1.V075WorkerThresholdProfileV1()
        if envelope is None:
            _fail("fresh exact lift lacks a statistical envelope")
        expected = _fresh_exact_metrics(
            plan=self.plan,
            exact_replay=self.exact_replay,
            optimal_expected_reward=candidate.optimal_expected_reward,
        ) if candidate.optimal_expected_reward is not None else None
        if (
            self.source_verification.independently_recomputed_candidate_id
            != candidate.candidate_id
            or self.lineage.envelope.policy.planner_result
            != source.final_planner_result
            or self.lineage.model.backend_result != source.final_backend_result
            or self.lineage.model.context != self.plan.query.epoch.model.context
            or self.exact_replay.lineage_id != self.lineage.lineage_id
            or candidate.status
            is not (
                total_lift_v1.V075BatchTotalLiftConstructionStatusV1
                .EXACT_POSITIVE_CONSTRUCTION_CONTROL
            )
            or candidate.optimal_expected_reward is None
            or candidate.optimal_failure_probability is None
            or expected is None
            or expected != self.metrics
            or self.metrics.selected_reward < envelope.selected_reward_lower
            or self.metrics.selected_reward > envelope.selected_reward_upper
            or self.metrics.selected_failure > envelope.selected_failure_upper
            or candidate.optimal_expected_reward
            > envelope.unrestricted_ground_reward_upper
            or self.metrics.exact_normalized_regret
            > envelope.normalized_regret_upper
            or self.metrics.selected_failure > threshold.risk_tolerance
            or self.metrics.exact_normalized_regret
            > threshold.normalized_regret_tolerance
        ):
            _fail("fresh abstract policy failed construction exact-lift validation")
        object.__setattr__(
            self,
            "_binding_id",
            content_id(EXACT_LIFT_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        source_policy = self.plan.query.epoch.source.final_planner_result.policy
        assert source_policy is not None
        candidate = self.source_verification.candidate
        return {
            "schema": "acfqp.construction_k7_positive_promoted_exact_lift_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "positive_promoted_abstract_plan_id": self.plan.plan_id,
            "fresh_policy_id": self.plan.proof.policy.policy_id,
            "fresh_policy_signature": [
                {
                    "state_id": state_id,
                    "remaining_horizon": horizon,
                    "ground_action": list(action),
                }
                for state_id, horizon, action in self.plan.policy_signature
            ],
            "source_policy_signature": [
                {
                    "state_id": state_id,
                    "remaining_horizon": horizon,
                    "ground_action": list(action),
                }
                for state_id, horizon, action
                in _source_policy_signature(source_policy)
            ],
            "fresh_policy_was_replanned_not_replayed": True,
            "behavior_tie_break_may_select_different_ground_representatives": (
                self.plan.policy_signature != _source_policy_signature(source_policy)
            ),
            "source_total_lift_lineage_id": self.lineage.lineage_id,
            "source_construction_exact_replay_id": self.exact_replay.replay_id,
            "source_total_lift_candidate_id": candidate.candidate_id,
            "source_total_lift_verification_id": (
                self.source_verification.verification_id
            ),
            "source_total_lift_status": candidate.status.value,
            "fresh_selected_expected_reward": _fdoc(self.metrics.selected_reward),
            "fresh_environment_failure_probability": _fdoc(
                self.metrics.environment_failure
            ),
            "fresh_policy_abort_failure_probability": _fdoc(
                self.metrics.policy_abort_failure
            ),
            "fresh_selected_failure_probability": _fdoc(
                self.metrics.selected_failure
            ),
            "fresh_exact_normalized_regret": _fdoc(
                self.metrics.exact_normalized_regret
            ),
            "exact_optimal_expected_reward": _fdoc(
                candidate.optimal_expected_reward
            ),
            "exact_optimal_failure_probability": _fdoc(
                candidate.optimal_failure_probability
            ),
            "fresh_branch_partition_ids": [
                item.partition_id for item in self.metrics.partitions
            ],
            "fresh_exact_lift_status": (
                "CONSTRUCTION_EXACT_LIFT_VALIDATED_ABSTRACT_PLAN"
            ),
            "exact_total_lift_execution_lane": "STANDALONE_EVALUATION_ONLY",
            "exact_lift_excluded_from_operational_route_work": True,
            "construction_scope_plan_certificate_issued": True,
            "scientific_endpoint_credit_allowed": False,
            "official_execution_allowed": False,
        }

    @property
    def binding_id(self) -> str:
        current = content_id(EXACT_LIFT_DOMAIN, self._payload())
        if current != self._binding_id:
            _fail("positive promoted exact lift changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "fresh_branch_partitions": [
                item.to_document() for item in self.metrics.partitions
            ],
            "positive_promoted_exact_lift_binding_id": self.binding_id,
        }


def bind_positive_promoted_exact_lift_v1(
    plan: PositivePromotedAbstractPlanV1,
    *,
    lineage: total_lift_v1.V075BatchNativeLineageBindingV1,
    exact_replay: total_lift_v1.V075BatchNativeConstructionExactReplayV1,
    source_verification: (
        total_lift_v1.V075BatchNativeConstructionTotalLiftVerificationV1
    ),
) -> PositivePromotedExactLiftBindingV1:
    if type(plan) is not PositivePromotedAbstractPlanV1:
        _fail("positive exact lift requires one exact fresh abstract plan")
    try:
        replayed = (
            total_lift_v1
            .verify_v075_batch_native_construction_total_lift_candidate_v1(
                lineage=lineage,
                exact_replay=exact_replay,
                claimed=source_verification.candidate,
            )
        )
    except Exception as error:
        raise ConstructionK7PositivePromotedOverlayV1Error(
            "source construction exact lift failed independent recomputation"
        ) from error
    if replayed.verification_id != source_verification.verification_id:
        _fail("source construction exact-lift verification identity changed")
    candidate = replayed.candidate
    if candidate.optimal_expected_reward is None:
        _fail("positive exact lift source lacks an exact ground optimum")
    metrics = _fresh_exact_metrics(
        plan=plan,
        exact_replay=exact_replay,
        optimal_expected_reward=candidate.optimal_expected_reward,
    )
    return PositivePromotedExactLiftBindingV1(
        _EXACT_LIFT_ISSUER,
        plan,
        lineage,
        exact_replay,
        source_verification,
        metrics,
    )


@dataclass(frozen=True, slots=True)
class PositivePromotedOverlayResultV1:
    _issuer: InitVar[object]
    epoch: PositivePromotedOverlayEpochV1
    query: PositivePromotedOverlayQueryV1
    plan: PositivePromotedAbstractPlanV1
    exact_lift: PositivePromotedExactLiftBindingV1
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.epoch) is not PositivePromotedOverlayEpochV1
            or type(self.query) is not PositivePromotedOverlayQueryV1
            or type(self.plan) is not PositivePromotedAbstractPlanV1
            or type(self.exact_lift) is not PositivePromotedExactLiftBindingV1
            or self.query.epoch != self.epoch
            or self.plan.query != self.query
            or self.exact_lift.plan != self.plan
        ):
            _fail("positive promoted-overlay result identity graph changed")
        self.epoch.epoch_id
        self.query.query_id
        self.plan.plan_id
        self.exact_lift.binding_id
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        counters = self.epoch.source.counters
        return {
            "schema": "acfqp.construction_k7_positive_promoted_overlay_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "positive_promoted_overlay_epoch_id": self.epoch.epoch_id,
            "positive_promoted_overlay_query_id": self.query.query_id,
            "positive_promoted_abstract_plan_id": self.plan.plan_id,
            "positive_promoted_exact_lift_binding_id": self.exact_lift.binding_id,
            "source_occurrence_id": self.epoch.source_occurrence_id,
            "fresh_logical_occurrence_id": self.query.logical_occurrence_id,
            "source_failed_before_local_recovery": True,
            "source_incremental_local_draw_count": counters.incremental_draws,
            "source_child_action_rows_materialized": (
                counters.child_action_rows_materialized
            ),
            "fresh_occurrence_new_ground_draw_count": 0,
            "fresh_occurrence_observer_call_count": 0,
            "fresh_occurrence_operational_planner_call_count": 1,
            "fresh_occurrence_used_promoted_model": True,
            "fresh_occurrence_multi_step_abstract_candidate": True,
            "fresh_occurrence_construction_exact_lift_validated": True,
            "local_ground_restoration_triggered_for_fresh_occurrence": False,
            "mainline_loop_demonstrated": (
                "FAILED_CERTIFICATE_TO_LOCAL_DISTINCTIONS_TO_PROMOTED_OVERLAY_"
                "TO_FRESH_ABSTRACT_REPLAN_TO_CONSTRUCTION_EXACT_LIFT"
            ),
            "same_registered_structural_query_positive_control": True,
            "held_out_structural_family_claimed": False,
            "automatic_coordinate_invention_claimed": False,
            "construction_scope_plan_certificate_count": 1,
            "scientific_plan_certificate_count": 0,
            "counter_records_issued": 0,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("positive promoted-overlay result changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "promoted_epoch": self.epoch.to_document(),
            "fresh_query": self.query.to_document(),
            "fresh_abstract_plan": self.plan.to_document(),
            "construction_exact_lift": self.exact_lift.to_document(),
            "positive_promoted_overlay_result_id": self.result_id,
        }


def run_positive_promoted_overlay_v1(
    source: successor_v1.V075BatchedCausalOccurrencePrecloseResultV1,
    *,
    logical_occurrence_id: str,
    query_ordinal: int,
    lineage: total_lift_v1.V075BatchNativeLineageBindingV1,
    exact_replay: total_lift_v1.V075BatchNativeConstructionExactReplayV1,
    source_verification: (
        total_lift_v1.V075BatchNativeConstructionTotalLiftVerificationV1
    ),
) -> PositivePromotedOverlayResultV1:
    epoch = promote_positive_query_neutral_overlay_v1(source)
    query = freeze_positive_promoted_overlay_query_v1(
        epoch,
        logical_occurrence_id=logical_occurrence_id,
        query_ordinal=query_ordinal,
    )
    plan = plan_positive_promoted_overlay_query_v1(query)
    exact_lift = bind_positive_promoted_exact_lift_v1(
        plan,
        lineage=lineage,
        exact_replay=exact_replay,
        source_verification=source_verification,
    )
    return PositivePromotedOverlayResultV1(
        _RESULT_ISSUER,
        epoch,
        query,
        plan,
        exact_lift,
    )


def verify_positive_promoted_overlay_v1(
    claimed: PositivePromotedOverlayResultV1,
) -> PositivePromotedOverlayResultV1:
    if type(claimed) is not PositivePromotedOverlayResultV1:
        _fail("positive promoted-overlay verifier rejects foreign types")
    expected = run_positive_promoted_overlay_v1(
        claimed.epoch.source,
        logical_occurrence_id=claimed.query.logical_occurrence_id,
        query_ordinal=claimed.query.query_ordinal,
        lineage=claimed.exact_lift.lineage,
        exact_replay=claimed.exact_lift.exact_replay,
        source_verification=claimed.exact_lift.source_verification,
    )
    if expected != claimed or expected.result_id != claimed.result_id:
        _fail("positive promoted-overlay result differs from exact replay")
    return expected


def verify_positive_promoted_overlay_bytes_v1(
    *,
    source: successor_v1.V075BatchedCausalOccurrencePrecloseResultV1,
    lineage: total_lift_v1.V075BatchNativeLineageBindingV1,
    exact_replay: total_lift_v1.V075BatchNativeConstructionExactReplayV1,
    source_verification: (
        total_lift_v1.V075BatchNativeConstructionTotalLiftVerificationV1
    ),
    result_bytes: bytes,
) -> PositivePromotedOverlayResultV1:
    if type(result_bytes) is not bytes or not result_bytes:
        _fail("positive promoted-overlay result bytes are absent")
    try:
        document = loads_canonical_json(result_bytes)
    except Exception as error:
        raise ConstructionK7PositivePromotedOverlayV1Error(
            "positive promoted-overlay result is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != result_bytes:
        _fail("positive promoted-overlay result is not one canonical object")
    try:
        query = document["fresh_query"]
        logical_occurrence_id = query["logical_occurrence_id"]
        query_ordinal = query["query_ordinal"]
    except (KeyError, TypeError) as error:
        raise ConstructionK7PositivePromotedOverlayV1Error(
            "positive promoted-overlay result lacks its fresh query"
        ) from error
    expected = run_positive_promoted_overlay_v1(
        source,
        logical_occurrence_id=logical_occurrence_id,
        query_ordinal=query_ordinal,
        lineage=lineage,
        exact_replay=exact_replay,
        source_verification=source_verification,
    )
    if canonical_json_bytes(expected.to_document()) != result_bytes:
        _fail("positive promoted-overlay bytes differ from exact reconstruction")
    return expected


__all__ = [
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7PositivePromotedOverlayV1Error",
    "LOCAL_DOMAINS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PositivePromotedAbstractPlanV1",
    "PositivePromotedExactLiftBindingV1",
    "PositivePromotedOverlayEpochV1",
    "PositivePromotedOverlayQueryV1",
    "PositivePromotedOverlayResultV1",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "bind_positive_promoted_exact_lift_v1",
    "freeze_positive_promoted_overlay_query_v1",
    "plan_positive_promoted_overlay_query_v1",
    "promote_positive_query_neutral_overlay_v1",
    "run_positive_promoted_overlay_v1",
    "verify_positive_promoted_overlay_bytes_v1",
    "verify_positive_promoted_overlay_v1",
]
