"""Producer-free replay of the positive promoted-world-model control.

The verifier intentionally does not import the positive-overlay producer.  It
replays the upstream signed occurrence, reconstructs the public V2 model and
proof from canonical bytes, checks the V1-to-V2 aggregate projection row by
row, and independently evaluates the fresh V2 policy against the frozen
construction exact replay.  It then rebuilds every V0-115 artifact document
and content ID locally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, NoReturn

from acfqp import v075_batched_causal_occurrence_successor_v1 as successor_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_batch_native_total_lift_authority_v1 as total_lift_v1
from acfqp import v075_learned_support_quotient_planners_v1 as planners_v1
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_POSITIVE_PROMOTED_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_EXACT_LIFT_BINDING_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_EPOCH_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_QUERY_V1_DOMAIN,
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.116"
PROFILE_KEY = (
    "construction_k7_positive_promoted_overlay_independent_verifier_v1"
)

PRODUCER_CONTRACT_VERSION = "2.0.115"
PRODUCER_PROFILE_KEY = "construction_k7_positive_promoted_overlay_v1"

EPOCH_DOMAIN = CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_EPOCH_V1_DOMAIN
QUERY_DOMAIN = CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_QUERY_V1_DOMAIN
PLAN_DOMAIN = CONSTRUCTION_K7_POSITIVE_PROMOTED_ABSTRACT_PLAN_V1_DOMAIN
EXACT_LIFT_DOMAIN = (
    CONSTRUCTION_K7_POSITIVE_PROMOTED_EXACT_LIFT_BINDING_V1_DOMAIN
)
RESULT_DOMAIN = CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_RESULT_V1_DOMAIN
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_INDEPENDENT_VERIFICATION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({VERIFICATION_DOMAIN})
if len(LOCAL_DOMAINS) != 1 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("positive-overlay independent domain is not central")


class ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error(
    ValueError
):
    """The source, projection, plan, lift, or result bytes changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("independent verification arithmetic must remain exact")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _load(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail("positive promoted-overlay bytes are absent")
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error(
            "positive promoted-overlay bytes are not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("positive promoted-overlay bytes are not one canonical object")
    return document


def _policy_signature(
    policy: planning_v2.V075DeterministicPolicyV2,
) -> tuple[tuple[str, int, tuple[int, int, int]], ...]:
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


def _signature_document(
    signature: tuple[tuple[str, int, tuple[int, int, int]], ...],
) -> list[dict[str, Any]]:
    return [
        {
            "state_id": state_id,
            "remaining_horizon": horizon,
            "ground_action": list(action),
        }
        for state_id, horizon, action in signature
    ]


def _verify_projection(
    *,
    source: successor_v1.V075BatchedCausalOccurrencePrecloseResultV1,
    model: planning_v2.V075NumericalModelV2,
) -> None:
    graph = source.final_planner_result.graph
    old_rows = {
        row.row_binding_id: (node, row)
        for node in graph.nodes
        for row in node.rows
    }
    new_rows = {row.row_binding_id: row for row in model.rows}
    if (
        len(old_rows) != sum(len(node.rows) for node in graph.nodes)
        or len(new_rows) != len(model.rows)
        or set(old_rows) != set(new_rows)
        or model.context != graph.context
        or model.evidence_kind != "SIGNED_V2_AGGREGATES"
    ):
        _fail("promoted model does not cover the exact source row registry")
    for row_binding_id in sorted(old_rows):
        node, old = old_rows[row_binding_id]
        new = new_rows[row_binding_id]
        rewards = {item.realized_row_reward for item in old.support}
        old_support = {
            (item.next_state_id, item.next_ranks, item.failure, item.terminal): item
            for item in old.support
        }
        new_support = {
            (item.next_state_id, item.next_ranks, item.failure, item.terminal): item
            for item in new.support
        }
        if (
            len(rewards) != 1
            or old.context_id != new.context_id
            or old.source_state_id != new.source_state_id
            or old.remaining_horizon != new.remaining_horizon
            or old.action != new.action
            or node.catalogue.state.ranks != new.source_ranks
            or next(iter(rewards)) != new.immediate_reward
            or set(old_support) != set(new_support)
        ):
            _fail("one promoted row changed its public graph semantics")
        old_intervals: dict[Any, Any] = {"OTHER": None}
        for interval in old.intervals:
            if interval.event_key == "OTHER":
                old_intervals["OTHER"] = interval
            else:
                descriptor = interval.descriptor
                assert descriptor is not None
                old_intervals[
                    (
                        descriptor.next_state_id,
                        descriptor.next_ranks,
                        descriptor.failure,
                        descriptor.terminal,
                    )
                ] = interval
        new_intervals: dict[Any, Any] = {"OTHER": None}
        for interval in new.intervals:
            if interval.event_key == "OTHER":
                new_intervals["OTHER"] = interval
            else:
                descriptor = interval.descriptor
                assert descriptor is not None
                new_intervals[
                    (
                        descriptor.next_state_id,
                        descriptor.next_ranks,
                        descriptor.failure,
                        descriptor.terminal,
                    )
                ] = interval
        if set(old_intervals) != set(new_intervals):
            _fail("one promoted row changed its confidence event partition")
        alpha = planning_v2.ROW_BETA / len(old.intervals)
        for key in old_intervals:
            prior = old_intervals[key]
            projected = new_intervals[key]
            if (
                prior is None
                or projected is None
                or prior.draw_count != projected.draw_count
                or prior.success_count != projected.success_count
                or prior.empirical_probability != projected.empirical_probability
                or prior.lower_probability != projected.lower_probability
                or prior.upper_probability != projected.upper_probability
                or prior.exact_likelihood_comparisons
                != projected.exact_likelihood_comparisons
                or prior.log_search_evaluations
                != projected.log_search_evaluations
                or projected.event_alpha != alpha
                or projected.method_id != planning_v2.EXACT_BERNOULLI_METHOD_ID
            ):
                _fail("one promoted confidence interval changed")


@dataclass(frozen=True, slots=True)
class _ExactMetricsV1:
    selected_reward: Fraction
    environment_failure: Fraction
    policy_abort_failure: Fraction
    selected_failure: Fraction
    exact_normalized_regret: Fraction
    partitions: tuple[total_lift_v1.V075BatchLiftBranchPartitionV1, ...]


def _evaluate_exact(
    *,
    proof: planning_v2.V075NumericalPlanningProofV2,
    exact_replay: total_lift_v1.V075BatchNativeConstructionExactReplayV1,
    optimal_expected_reward: Fraction,
) -> _ExactMetricsV1:
    policy = proof.policy
    if policy is None:
        _fail("fresh proof lacks its candidate policy")
    model_rows = {
        (row.source_state_id, row.remaining_horizon, row.action): row
        for row in proof.model.rows
    }
    exact_rows = {
        (
            row.row_binding.state_id,
            row.row_binding.remaining_horizon,
            row.row_binding.action,
        ): row
        for row in exact_replay.rows
    }
    if (
        len(model_rows) != len(proof.model.rows)
        or len(exact_rows) != len(exact_replay.rows)
    ):
        _fail("fresh or exact model repeats one state-time-action row")
    choices: dict[tuple[str, int], planning_v2.V075PolicyStateChoiceV2] = {}
    for decision in policy.decisions:
        for choice in decision.state_choices:
            key = (choice.state_id, decision.remaining_horizon)
            if key in choices:
                _fail("fresh policy repeats one state-time decision")
            choices[key] = choice
    roots = {
        row.source_state_id
        for row in proof.model.rows
        if row.remaining_horizon == 2
    }
    if len(roots) != 1:
        _fail("fresh model lacks one exact H=2 root")
    root_state_id = next(iter(roots))
    root_choice = choices.get((root_state_id, 2))
    if root_choice is None:
        _fail("fresh policy lacks the root decision")

    selected_reward = Fraction(0)
    environment_failure = Fraction(0)
    policy_abort = Fraction(0)
    partitions: list[total_lift_v1.V075BatchLiftBranchPartitionV1] = []

    def evaluate_row(
        *,
        state_id: str,
        horizon: int,
        action: tuple[int, int, int],
        row_id: str,
        weight: Fraction,
    ) -> dict[str, Fraction]:
        nonlocal selected_reward, environment_failure, policy_abort
        row = model_rows.get((state_id, horizon, action))
        exact = exact_rows.get((state_id, horizon, action))
        if (
            row is None
            or exact is None
            or row.row_id != row_id
            or row.immediate_reward != exact.reward
            or not 0 < weight <= 1
        ):
            _fail("fresh selected row does not bind one exact row")
        modeled_keys = {
            (item.next_state_id, item.failure, item.terminal)
            for item in row.support
        }
        environment_ids: list[str] = []
        modeled_ids: list[str] = []
        abort_ids: list[str] = []
        recurse: dict[str, Fraction] = {}
        selected_reward += weight * exact.reward
        for atom in exact.atoms:
            key = (
                atom.next_state_id,
                atom.atom.failure,
                atom.atom.terminal,
            )
            weighted = weight * atom.atom.probability
            if atom.atom.failure:
                environment_ids.append(atom.atom_id)
                environment_failure += weighted
            elif key not in modeled_keys:
                abort_ids.append(atom.atom_id)
                policy_abort += weighted
            elif horizon == 1:
                modeled_ids.append(atom.atom_id)
            elif (atom.next_state_id, 1) not in choices:
                abort_ids.append(atom.atom_id)
                policy_abort += weighted
            else:
                modeled_ids.append(atom.atom_id)
                recurse[atom.next_state_id] = (
                    recurse.get(atom.next_state_id, Fraction(0))
                    + atom.atom.probability
                )
        partitions.append(
            total_lift_v1.V075BatchLiftBranchPartitionV1(
                state_id,
                horizon,
                action,
                row_id,
                exact.row_id,
                weight,
                tuple(
                    (atom.atom_id, atom.atom.probability)
                    for atom in exact.atoms
                ),
                tuple(sorted(environment_ids)),
                tuple(sorted(modeled_ids)),
                tuple(sorted(abort_ids)),
            )
        )
        return recurse

    for action, row_id, root_weight in zip(
        root_choice.ground_actions,
        root_choice.row_ids,
        root_choice.uniform_weights,
        strict=True,
    ):
        recurse = evaluate_row(
            state_id=root_state_id,
            horizon=2,
            action=action,
            row_id=row_id,
            weight=root_weight,
        )
        for child_state_id in sorted(recurse):
            child = choices[(child_state_id, 1)]
            for child_action, child_row_id, child_weight in zip(
                child.ground_actions,
                child.row_ids,
                child.uniform_weights,
                strict=True,
            ):
                evaluate_row(
                    state_id=child_state_id,
                    horizon=1,
                    action=child_action,
                    row_id=child_row_id,
                    weight=(
                        root_weight * recurse[child_state_id] * child_weight
                    ),
                )
    selected_failure = environment_failure + policy_abort
    exact_regret = (
        optimal_expected_reward - selected_reward
    ) / worker_v1.V075WorkerThresholdProfileV1().reward_ceiling
    if exact_regret < 0 or not 0 <= selected_failure <= 1:
        _fail("fresh exact metrics exceed their registered bounds")
    return _ExactMetricsV1(
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
class PositivePromotedOverlayIndependentVerificationV1:
    result_id: str
    epoch_id: str
    query_id: str
    plan_id: str
    exact_lift_binding_id: str
    numerical_model_id: str
    numerical_proof_id: str
    policy_id: str
    selected_reward: Fraction
    selected_failure: Fraction
    exact_normalized_regret: Fraction
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_id, "positive result"),
            (self.epoch_id, "positive epoch"),
            (self.query_id, "fresh query"),
            (self.plan_id, "fresh plan"),
            (self.exact_lift_binding_id, "fresh exact lift"),
            (self.numerical_model_id, "promoted model"),
            (self.numerical_proof_id, "fresh proof"),
            (self.policy_id, "fresh policy"),
        ):
            _cid(value, label)
        if (
            type(self.selected_reward) is not Fraction
            or type(self.selected_failure) is not Fraction
            or type(self.exact_normalized_regret) is not Fraction
            or self.selected_reward < 0
            or not 0 <= self.selected_failure <= 1
            or self.exact_normalized_regret < 0
        ):
            _fail("independent positive verification metrics are malformed")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.construction_k7_positive_promoted_overlay_"
                "independent_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "positive_promoted_overlay_result_id": self.result_id,
            "positive_promoted_overlay_epoch_id": self.epoch_id,
            "positive_promoted_overlay_query_id": self.query_id,
            "positive_promoted_abstract_plan_id": self.plan_id,
            "positive_promoted_exact_lift_binding_id": self.exact_lift_binding_id,
            "promoted_numerical_model_id": self.numerical_model_id,
            "fresh_numerical_proof_id": self.numerical_proof_id,
            "fresh_policy_id": self.policy_id,
            "fresh_selected_expected_reward": _fdoc(self.selected_reward),
            "fresh_selected_failure_probability": _fdoc(self.selected_failure),
            "fresh_exact_normalized_regret": _fdoc(
                self.exact_normalized_regret
            ),
            "source_occurrence_publicly_replayed": True,
            "v1_to_v2_projection_independently_replayed": True,
            "fresh_abstract_planner_independently_replayed": True,
            "fresh_policy_exact_lift_independently_recomputed": True,
            "producer_module_imported": False,
            "operational_new_ground_draw_count": 0,
            "construction_scope_plan_certificate_verified": True,
            "scientific_endpoint_credit_allowed": False,
            "official_execution_allowed": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        current = content_id(VERIFICATION_DOMAIN, self._payload())
        if current != self._verification_id:
            _fail("independent positive verification changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "positive_promoted_overlay_independent_verification_id": (
                self.verification_id
            ),
        }


def verify_positive_promoted_overlay_bytes_independently_v1(
    *,
    source: successor_v1.V075BatchedCausalOccurrencePrecloseResultV1,
    lineage: total_lift_v1.V075BatchNativeLineageBindingV1,
    exact_replay: total_lift_v1.V075BatchNativeConstructionExactReplayV1,
    source_verification: (
        total_lift_v1.V075BatchNativeConstructionTotalLiftVerificationV1
    ),
    result_bytes: bytes,
) -> PositivePromotedOverlayIndependentVerificationV1:
    document = _load(result_bytes)
    # Cheap fail-closed gates precede expensive public source replay.
    if (
        document.get("schema")
        != "acfqp.construction_k7_positive_promoted_overlay_result.v1"
        or document.get("official_execution_allowed") is not False
        or document.get("scientific_endpoint_credit_allowed") is not False
        or document.get("scientific_plan_certificate_count") != 0
        or document.get("fresh_occurrence_new_ground_draw_count") != 0
        or document.get("fresh_occurrence_operational_planner_call_count") != 1
        or document.get("counter_records_issued") != 0
        or document.get("counter_completeness_gate_status") != "NOT_RUN"
        or document.get("workload_economics_gate_status") != "NOT_RUN"
    ):
        _fail("positive promoted-overlay outer claim locks changed")
    try:
        epoch_document = document["promoted_epoch"]
        query_document = document["fresh_query"]
        plan_document = document["fresh_abstract_plan"]
        lift_document = document["construction_exact_lift"]
        model_document = epoch_document["promoted_numerical_model"]
        proof_document = plan_document["fresh_numerical_proof"]
    except (KeyError, TypeError) as error:
        raise ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error(
            "positive promoted-overlay artifact graph is incomplete"
        ) from error
    try:
        model = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(model_document)
        )
        proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
            canonical_json_bytes(proof_document)
        )
    except Exception as error:
        raise ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error(
            "promoted model or fresh proof failed portable replay"
        ) from error
    if (
        proof.model != model
        or proof.route is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        or proof.outcome is not planning_v2.V075NumericalOutcomeV2.CANDIDATE
        or proof.policy is None
        or proof.envelope is None
        or proof.failed_frontier is not None
    ):
        _fail("fresh promoted proof is not one abstract H=2 candidate")
    if type(source) is not successor_v1.V075BatchedCausalOccurrencePrecloseResultV1:
        _fail("independent verifier source is untyped")
    try:
        source_replay = (
            successor_v1.verify_v075_batched_causal_occurrence_successor_v1(
                source
            )
        )
        lift_replay = (
            total_lift_v1
            .verify_v075_batch_native_construction_total_lift_candidate_v1(
                lineage=lineage,
                exact_replay=exact_replay,
                claimed=source_verification.candidate,
            )
        )
    except Exception as error:
        raise ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error(
            "positive source or source exact lift failed independent replay"
        ) from error
    candidate = lift_replay.candidate
    source_policy = source.final_planner_result.policy
    if (
        source_replay.result_id != source.result_id
        or source.initial_planner_result.status
        is not planners_v1.V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY
        or not source.initial_planner_result.diagnostic_failed_frontier_row_ids
        or source.final_planner_result.status
        is not (
            planners_v1.V075PlannerStatusV1
            .CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT
        )
        or type(source_policy) is not planners_v1.V075DeterministicH2PolicyV1
        or source.counters.incremental_draws <= 0
        or source.counters.child_action_rows_materialized <= 0
        or len(source.authorization.selected_candidate_ids) <= 1
        or source.counters.backend_compilations != 2
        or source.counters.planner_invocations != 2
        or source.counters.process_launches != 0
        or lift_replay.verification_id != source_verification.verification_id
        or lineage.envelope.policy.planner_result != source.final_planner_result
        or lineage.model.backend_result != source.final_backend_result
        or exact_replay.lineage_id != lineage.lineage_id
        or candidate.status
        is not (
            total_lift_v1.V075BatchTotalLiftConstructionStatusV1
            .EXACT_POSITIVE_CONSTRUCTION_CONTROL
        )
        or candidate.optimal_expected_reward is None
        or candidate.optimal_failure_probability is None
    ):
        _fail("source is not the exact failed-then-recovered positive control")
    _verify_projection(source=source, model=model)
    metrics = _evaluate_exact(
        proof=proof,
        exact_replay=exact_replay,
        optimal_expected_reward=candidate.optimal_expected_reward,
    )
    threshold = worker_v1.V075WorkerThresholdProfileV1()
    envelope = proof.envelope
    if (
        metrics.selected_reward < envelope.selected_reward_lower
        or metrics.selected_reward > envelope.selected_reward_upper
        or metrics.selected_failure > envelope.selected_failure_upper
        or candidate.optimal_expected_reward
        > envelope.unrestricted_ground_reward_upper
        or metrics.exact_normalized_regret > envelope.normalized_regret_upper
        or metrics.selected_failure > threshold.risk_tolerance
        or metrics.exact_normalized_regret
        > threshold.normalized_regret_tolerance
    ):
        _fail("fresh abstract policy failed independent exact-lift validation")

    source_identity = source.occurrence_identity
    logical_occurrence_id = _cid(
        query_document.get("logical_occurrence_id"), "fresh logical occurrence"
    )
    query_ordinal = query_document.get("query_ordinal")
    if (
        logical_occurrence_id == source_identity.occurrence_id
        or type(query_ordinal) is not int
        or query_ordinal != source_identity.occurrence_ordinal + 1
    ):
        _fail("positive promoted query is not the next fresh occurrence")

    epoch_payload = {
        "schema": "acfqp.construction_k7_positive_promoted_overlay_epoch.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": PRODUCER_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "source_batched_causal_result_id": source.result_id,
        "source_occurrence_id": source_identity.occurrence_id,
        "source_occurrence_ordinal": source_identity.occurrence_ordinal,
        "source_initial_planner_result_id": source.initial_planner_result.result_id,
        "source_initial_proof_status": source.initial_planner_result.status.value,
        "source_initial_failed_frontier_row_ids": list(
            source.initial_planner_result.diagnostic_failed_frontier_row_ids
        ),
        "source_causal_authorization_id": source.authorization.authorization_id,
        "source_selected_causal_candidate_count": len(
            source.authorization.selected_candidate_ids
        ),
        "source_incremental_local_draw_count": source.counters.incremental_draws,
        "source_child_action_rows_materialized": (
            source.counters.child_action_rows_materialized
        ),
        "source_final_planner_result_id": source.final_planner_result.result_id,
        "source_final_proof_status": source.final_planner_result.status.value,
        "source_learned_support_graph_id": source.final_planner_result.graph.graph_id,
        "promoted_numerical_model_id": model.model_id,
        "promoted_row_count": len(model.rows),
        "promoted_state_node_count": len(source.final_planner_result.graph.nodes),
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
    epoch_id = content_id(EPOCH_DOMAIN, epoch_payload)
    expected_epoch = {
        **epoch_payload,
        "promoted_numerical_model": model.to_document(),
        "positive_promoted_overlay_epoch_id": epoch_id,
    }
    query_payload = {
        "schema": "acfqp.construction_k7_positive_promoted_overlay_query.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": PRODUCER_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "positive_promoted_overlay_epoch_id": epoch_id,
        "promoted_numerical_model_id": model.model_id,
        "source_occurrence_id": source_identity.occurrence_id,
        "source_occurrence_ordinal": source_identity.occurrence_ordinal,
        "logical_occurrence_id": logical_occurrence_id,
        "query_ordinal": query_ordinal,
        "context_id": model.context.context_id,
        "horizon": model.context.horizon,
        "threshold_profile_id": source_identity.threshold_profile_id,
        "route": planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT.value,
        "promoted_epoch_frozen_before_fresh_planning": True,
        "observer_or_ground_input_present": False,
        "same_registered_structural_query": True,
        "independent_random_tape_claimed": False,
    }
    query_id = content_id(QUERY_DOMAIN, query_payload)
    expected_query = {
        **query_payload,
        "positive_promoted_overlay_query_id": query_id,
    }
    signature = _policy_signature(proof.policy)
    plan_payload = {
        "schema": "acfqp.construction_k7_positive_promoted_abstract_plan.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": PRODUCER_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "positive_promoted_overlay_query_id": query_id,
        "logical_occurrence_id": logical_occurrence_id,
        "promoted_numerical_model_id": model.model_id,
        "fresh_numerical_proof_id": proof.proof_id,
        "fresh_policy_id": proof.policy.policy_id,
        "fresh_envelope_id": proof.envelope.envelope_id,
        "fresh_outcome": proof.outcome.value,
        "policy_assignments_evaluated": proof.policy_assignments_evaluated,
        "fresh_policy_signature": _signature_document(signature),
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
    plan_id = content_id(PLAN_DOMAIN, plan_payload)
    expected_plan = {
        **plan_payload,
        "fresh_numerical_proof": proof.to_document(),
        "positive_promoted_abstract_plan_id": plan_id,
    }
    source_signature = _source_policy_signature(source_policy)
    lift_payload = {
        "schema": (
            "acfqp.construction_k7_positive_promoted_exact_lift_binding.v1"
        ),
        "schema_version": "1.0.0",
        "proposed_contract_version": PRODUCER_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "positive_promoted_abstract_plan_id": plan_id,
        "fresh_policy_id": proof.policy.policy_id,
        "fresh_policy_signature": _signature_document(signature),
        "source_policy_signature": _signature_document(source_signature),
        "fresh_policy_was_replanned_not_replayed": True,
        "behavior_tie_break_may_select_different_ground_representatives": (
            signature != source_signature
        ),
        "source_total_lift_lineage_id": lineage.lineage_id,
        "source_construction_exact_replay_id": exact_replay.replay_id,
        "source_total_lift_candidate_id": candidate.candidate_id,
        "source_total_lift_verification_id": source_verification.verification_id,
        "source_total_lift_status": candidate.status.value,
        "fresh_selected_expected_reward": metrics.selected_reward,
        "fresh_environment_failure_probability": metrics.environment_failure,
        "fresh_policy_abort_failure_probability": metrics.policy_abort_failure,
        "fresh_selected_failure_probability": metrics.selected_failure,
        "fresh_exact_normalized_regret": metrics.exact_normalized_regret,
        "exact_optimal_expected_reward": candidate.optimal_expected_reward,
        "exact_optimal_failure_probability": candidate.optimal_failure_probability,
        "fresh_branch_partition_ids": [
            item.partition_id for item in metrics.partitions
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
    lift_id = content_id(EXACT_LIFT_DOMAIN, lift_payload)
    expected_lift = {
        **lift_payload,
        "fresh_branch_partitions": [
            item.to_document() for item in metrics.partitions
        ],
        "positive_promoted_exact_lift_binding_id": lift_id,
    }
    result_payload = {
        "schema": "acfqp.construction_k7_positive_promoted_overlay_result.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": PRODUCER_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "positive_promoted_overlay_epoch_id": epoch_id,
        "positive_promoted_overlay_query_id": query_id,
        "positive_promoted_abstract_plan_id": plan_id,
        "positive_promoted_exact_lift_binding_id": lift_id,
        "source_occurrence_id": source_identity.occurrence_id,
        "fresh_logical_occurrence_id": logical_occurrence_id,
        "source_failed_before_local_recovery": True,
        "source_incremental_local_draw_count": source.counters.incremental_draws,
        "source_child_action_rows_materialized": (
            source.counters.child_action_rows_materialized
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
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "official_execution_allowed": False,
        "scientific_endpoint_credit_allowed": False,
    }
    result_id = content_id(RESULT_DOMAIN, result_payload)
    expected_result = {
        **result_payload,
        "promoted_epoch": expected_epoch,
        "fresh_query": expected_query,
        "fresh_abstract_plan": expected_plan,
        "construction_exact_lift": expected_lift,
        "positive_promoted_overlay_result_id": result_id,
    }
    if canonical_json_bytes(expected_result) != result_bytes:
        _fail("positive promoted-overlay bytes differ from independent replay")
    return PositivePromotedOverlayIndependentVerificationV1(
        result_id,
        epoch_id,
        query_id,
        plan_id,
        lift_id,
        model.model_id,
        proof.proof_id,
        proof.policy.policy_id,
        metrics.selected_reward,
        metrics.selected_failure,
        metrics.exact_normalized_regret,
    )


__all__ = [
    "ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error",
    "LOCAL_DOMAINS",
    "PositivePromotedOverlayIndependentVerificationV1",
    "verify_positive_promoted_overlay_bytes_independently_v1",
]
