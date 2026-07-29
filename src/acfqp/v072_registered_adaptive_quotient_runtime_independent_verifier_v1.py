"""Independent no-target replay of registered adaptive occurrence results."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import exact_lazy_h2_robust_planner_v1 as lazy
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_model_builders_independent_verifier_v1 as model_verifier
from acfqp import v072_exact_lazy_planner_component_v1 as planner
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_registered_cold_h2_orchestrator_v1 as cold_runtime
from acfqp import v072_registered_incremental_epoch_materializer_v1 as incremental
from acfqp import (
    v072_registered_incremental_epoch_independent_verifier_v1
    as incremental_independent,
)
from acfqp import (
    v072_registered_target_selector_independent_verifier_v1
    as selector_verifier,
)
from acfqp import v072_registered_target_selector_v1 as selector
from acfqp import v072_registered_adaptive_quotient_runtime_v1 as runtime


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_registered_adaptive_runtime_independent_verifier_v1"
VERIFICATION_DOMAIN = (
    "acfqp:v072-registered-adaptive-runtime-independent-verification:v1"
)


class V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(ValueError):
    """A model, proof, selector, policy, status, lineage, or work replay differs."""


class RegisteredAdaptiveRuntimeIndependentGateLockedV1(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        observer_stream_opens: int = 0,
        observer_draw_calls: int = 0,
    ) -> None:
        super().__init__(message)
        self.observer_stream_opens = observer_stream_opens
        self.observer_draw_calls = observer_draw_calls


def _hash(payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            VERIFICATION_DOMAIN.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            str(error)
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            f"{label} must be one full content ID"
        ) from error


def _epoch_pair(epoch: Any) -> Any:
    if type(epoch) is cold_runtime.RegisteredColdH2ModelEpochV1:
        return epoch.model_pair
    if type(epoch) is incremental.RegisteredIncrementalH2ModelEpochV1:
        return epoch.model_pair
    raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
        "independent replay found an unknown epoch type"
    )


def _epoch_acquisitions(epoch: Any) -> tuple[Any, ...]:
    if type(epoch) is cold_runtime.RegisteredColdH2ModelEpochV1:
        return epoch.acquisitions
    if type(epoch) is incremental.RegisteredIncrementalH2ModelEpochV1:
        return epoch.acquisition_history
    raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
        "independent replay found an unknown acquisition history"
    )


def _epoch_access(epoch: Any) -> Any:
    if type(epoch) is cold_runtime.RegisteredColdH2ModelEpochV1:
        return epoch.access_audit
    if type(epoch) is incremental.RegisteredIncrementalH2ModelEpochV1:
        return epoch.access_audit
    raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
        "independent replay found an unknown access record"
    )


def _search_counters(
    result: planner.V072ExactLazyPlannerComponentResultV1,
) -> tuple[int, int, int, int]:
    solve = result.solve_result
    if solve.status is lazy.ExactLazyH2SolveStatus.SOLVED:
        if solve.trace is None:
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "solved planner result lacks its trace"
            )
        values = [solve.trace.original]
        if solve.trace.zero_other_counterfactual is not None:
            values.append(solve.trace.zero_other_counterfactual)
    else:
        if solve.exhaustion is None:
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "resource closure lacks exact counters"
            )
        values = [solve.exhaustion.counters]
    return (
        sum(item.branch_nodes for item in values),
        sum(item.complete_policies for item in values),
        sum(item.root_bound_evaluations for item in values),
        sum(item.pruned_branches for item in values),
    )


def _work(
    claimed: runtime.RegisteredAdaptiveOccurrenceResultV1,
) -> runtime.RegisteredAdaptiveOccurrenceWorkV1:
    accesses = tuple(_epoch_access(item) for item in claimed.epochs)
    counters = tuple(
        _search_counters(item) for item in claimed.planner_results
    )
    return runtime.RegisteredAdaptiveOccurrenceWorkV1(
        cold_epoch_builds=1,
        incremental_epoch_builds=len(claimed.epochs) - 1,
        incremental_epoch_independent_replay_calls=(
            len(claimed.epochs) - 1
        ),
        acquisition_calls=sum(item.acquisition_calls for item in accesses),
        confidence_replay_calls=sum(
            item.independent_confidence_replay_calls for item in accesses
        ),
        producer_stream_opens=sum(
            item.producer_stream_opens for item in accesses
        ),
        producer_draw_calls=sum(
            item.producer_draw_calls for item in accesses
        ),
        replay_stream_opens=sum(
            item.replay_stream_opens for item in accesses
        ),
        replay_draw_calls=sum(item.replay_draw_calls for item in accesses),
        unique_online_sample_evidence_draws=sum(
            item.unique_online_sample_evidence_draws for item in accesses
        ),
        total_observer_draw_calls=sum(
            item.total_observer_draw_calls for item in accesses
        ),
        closure_builds=len(claimed.epochs),
        closure_independent_verifications=len(claimed.epochs),
        confidence_projection_calls=sum(
            item.projection_calls for item in accesses
        ),
        model_pair_builds=len(claimed.epochs),
        model_pair_independent_verifications=len(claimed.epochs),
        quotient_planner_calls=len(claimed.planner_results),
        planner_proof_verification_calls=sum(
            item.independent_proof_replay_complete
            for item in claimed.planner_results
        ),
        selector_calls=len(claimed.selector_closures),
        selector_independent_replay_calls=len(claimed.selector_closures),
        branch_nodes=sum(item[0] for item in counters),
        complete_policies=sum(item[1] for item in counters),
        root_bound_evaluations=sum(item[2] for item in counters),
        pruned_branches=sum(item[3] for item in counters),
        source_ordering_recipe_reads=(
            2
            * sum(
                item.claim.arm
                in (
                    "SOURCE_CONSENSUS_PRIOR",
                    "WRONG_CONSENSUS_PRIOR",
                )
                for item in claimed.selector_closures
            )
        ),
    )


def _policy_support(
    pair: Any,
    audit: robust.RobustPlanAuditV1,
) -> tuple[
    tuple[runtime.RegisteredAdaptiveConcretizerDecisionV1, ...],
    tuple[runtime.RegisteredAdaptiveGroundPolicyDecisionV1, ...],
]:
    """Rebuild support and exact uniform weights without producer helpers."""

    model = pair.quotient_planner_model
    if (
        audit.model_id != model.model_id
        or audit.threshold_profile_id
        != pair.threshold_profile.threshold_profile_id
        or audit.solver_kind is not robust.RobustSolverKind.QUOTIENT
        or audit.status is not robust.RobustAuditStatus.CERTIFIED
    ):
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            "independent policy replay requires a certified quotient audit"
        )
    robust.verify_robust_plan_audit_v1(
        model,
        pair.threshold_profile,
        audit,
    )
    projection_by_key = {
        (item.interval_row.state_id, item.interval_row.action_id): item
        for item in pair.row_projections
    }
    catalogues = {item.state_id: item for item in model.catalogues}
    concretizers = {
        (
            item.state_coordinate_key,
            item.state_id,
            item.abstract_action_key,
        ): item
        for item in model.concretizer_entries
    }
    output = []
    seen: set[tuple[str, int]] = set()
    for assignment in audit.assignments:
        if assignment.scope is not robust.PolicyScope.QUOTIENT_CELL:
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "independent replay found a ground assignment in quotient policy"
            )
        state_ids = tuple(
            sorted(
                item.state_id
                for item in model.catalogues
                if item.state_coordinate_key == assignment.scope_key
                and (
                    (
                        assignment.remaining_horizon == 2
                        and item.state_id == model.root_state_id
                    )
                    or (
                        assignment.remaining_horizon == 1
                        and item.state_id != model.root_state_id
                    )
                )
            )
        )
        if not state_ids:
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "independent policy replay found an empty selected cell"
            )
        for state_id in state_ids:
            state_key = (state_id, assignment.remaining_horizon)
            if state_key in seen:
                raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                    "independent policy replay found duplicate state assignment"
                )
            seen.add(state_key)
            catalogue = catalogues[state_id]
            entry = concretizers.get(
                (
                    catalogue.state_coordinate_key,
                    state_id,
                    assignment.selected_action_key,
                )
            )
            if entry is None:
                raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                    "independent policy replay lacks selected concretizer"
                )
            projections = tuple(
                projection_by_key.get((state_id, action_id))
                for action_id in entry.ground_action_ids
            )
            if any(item is None for item in projections):
                raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                    "independent policy replay lacks a physical support row"
                )
            exact = tuple(item for item in projections if item is not None)
            ranks = {
                tuple(dict(item.row_evidence.state.document).get("ranks", ()))
                for item in exact
            }
            public_ids = {
                item.row_evidence.state.semantic_state_id for item in exact
            }
            actions = tuple(
                tuple(
                    dict(item.row_evidence.action.document).get("action", ())
                )
                for item in exact
            )
            if (
                len(ranks) != 1
                or len(public_ids) != 1
                or any(
                    len(item) != 3
                    or any(type(member) is not int for member in item)
                    for item in actions
                )
            ):
                raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                    "independent policy public semantics conflict"
                )
            output.append(
                runtime.RegisteredAdaptiveConcretizerDecisionV1(
                    model.model_id,
                    state_id,
                    next(iter(public_ids)),
                    next(iter(ranks)),
                    assignment.remaining_horizon,
                    catalogue.state_coordinate_key,
                    assignment.selected_action_key,
                    entry.concretizer_entry_id,
                    entry.ground_action_ids,
                    tuple(
                        item.row_evidence.action.semantic_action_id
                        for item in exact
                    ),
                    actions,
                    tuple(
                        Fraction(1, len(entry.ground_action_ids))
                        for _ in entry.ground_action_ids
                    ),
                )
            )
    concretizer_policy = tuple(
        sorted(output, key=lambda item: item.decision_id)
    )
    if (
        {item.ground_state_id for item in concretizer_policy}
        != {item.state_id for item in model.catalogues}
        or sum(
            item.remaining_horizon == 2 for item in concretizer_policy
        )
        != 1
    ):
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            "independent policy replay is not complete"
        )
    ground_policy = (
        tuple(
            sorted(
                (
                    runtime.RegisteredAdaptiveGroundPolicyDecisionV1(
                        item.ground_state_id,
                        item.public_state_id,
                        item.state_ranks,
                        item.remaining_horizon,
                        item.ground_actions[0],
                        item.decision_id,
                    )
                    for item in concretizer_policy
                ),
                key=lambda item: item.decision_id,
            )
        )
        if all(item.singleton for item in concretizer_policy)
        else ()
    )
    return concretizer_policy, ground_policy


def _terminal_status(
    claimed: runtime.RegisteredAdaptiveOccurrenceResultV1,
) -> runtime.RegisteredAdaptiveOccurrenceStatusV1:
    final_solve = claimed.planner_results[-1].solve_result
    if (
        final_solve.status
        is lazy.ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED
    ):
        return (
            runtime.RegisteredAdaptiveOccurrenceStatusV1
            .EXACT_DP_RESOURCE_EXHAUSTED
        )
    final_audit = final_solve.audit
    if (
        final_audit is not None
        and final_audit.status is robust.RobustAuditStatus.CERTIFIED
    ):
        return runtime.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
    final_selector = (
        claimed.selector_closures[-1]
        if len(claimed.selector_closures) == len(claimed.epochs)
        else None
    )
    if final_selector is not None:
        outcome = final_selector.claim.decision.outcome
        if outcome is selector.RegisteredSelectorOutcomeV1.NO_SOUND_COVER:
            return runtime.RegisteredAdaptiveOccurrenceStatusV1.NO_SOUND_COVER
        if outcome is selector.RegisteredSelectorOutcomeV1.CAP_EXHAUSTED:
            return (
                runtime.RegisteredAdaptiveOccurrenceStatusV1
                .ACQUISITION_CAP_EXHAUSTED
            )
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            "terminal selector has no registered noncertificate outcome"
        )
    if len(claimed.epochs) == runtime.MAX_LOCAL_ROUNDS + 1:
        return (
            runtime.RegisteredAdaptiveOccurrenceStatusV1
            .NOT_CERTIFIED_MAX_ROUNDS
        )
    raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
        "adaptive occurrence stopped before a replayable terminal condition"
    )


def _adapter_status(
    *,
    status: runtime.RegisteredAdaptiveOccurrenceStatusV1,
    concretizer_policy: tuple[
        runtime.RegisteredAdaptiveConcretizerDecisionV1, ...
    ],
    ground_policy: tuple[
        runtime.RegisteredAdaptiveGroundPolicyDecisionV1, ...
    ],
) -> runtime.RegisteredAdaptiveGroundAdapterStatusV1:
    if status is not runtime.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED:
        return (
            runtime.RegisteredAdaptiveGroundAdapterStatusV1
            .NOT_APPLICABLE_NONCERTIFICATE
        )
    if (
        concretizer_policy
        and len(ground_policy) == len(concretizer_policy)
        and all(item.singleton for item in concretizer_policy)
    ):
        return (
            runtime.RegisteredAdaptiveGroundAdapterStatusV1
            .SINGLETON_GROUND_POLICY_READY
        )
    return (
        runtime.RegisteredAdaptiveGroundAdapterStatusV1
        .FIXED_CONCRETIZER_OPERATIONAL_POLICY_SCHEMA_NOT_INTEGRATED
    )


def _certificate_id(
    *,
    authority_chain_id: str,
    anchor_id: str,
    occurrence_id: str,
    context_id: str,
    final_model_pair_id: str,
    planner_component_result_id: str,
    audit_id: str,
    concretizer_decision_ids: tuple[str, ...],
) -> str:
    payload = {
        "schema": "acfqp.v072_registered_adaptive_plan_certificate.v1",
        "schema_version": runtime.SCHEMA_VERSION,
        "authority_chain_id": authority_chain_id,
        "anchor_id": anchor_id,
        "occurrence_id": occurrence_id,
        "context_id": context_id,
        "final_model_pair_id": final_model_pair_id,
        "planner_component_result_id": planner_component_result_id,
        "audit_id": audit_id,
        "concretizer_decision_ids": list(concretizer_decision_ids),
        "fixed_concretizer_preserved": True,
        "source_quantities_used": False,
    }
    return hashlib.sha256(
        runtime.DOMAIN_TAGS["registered_certificate"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


def _incremental_attestation_ids(
    *,
    epoch_ids: tuple[str, ...],
    bindings: tuple[tuple[int, str, str, str], ...],
) -> tuple[str, ...]:
    if (
        type(epoch_ids) is not tuple
        or not epoch_ids
        or any(type(item) is not str for item in epoch_ids)
        or type(bindings) is not tuple
        or len(bindings) != len(epoch_ids) - 1
    ):
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            "incremental epoch attestations are missing or excessive"
        )
    for value in epoch_ids:
        _cid(value, "adaptive incremental lineage epoch")
    attestation_ids: list[str] = []
    for index, binding in enumerate(bindings, start=1):
        if (
            type(binding) is not tuple
            or len(binding) != 4
            or type(binding[0]) is not int
        ):
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "incremental epoch attestation binding is malformed"
            )
        round_index, predecessor_id, claimed_id, attestation_id = binding
        for value in (predecessor_id, claimed_id, attestation_id):
            _cid(value, "adaptive incremental attestation identity")
        if (
            round_index != index
            or predecessor_id != epoch_ids[index - 1]
            or claimed_id != epoch_ids[index]
        ):
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "incremental epoch attestation is reordered or stale"
            )
        attestation_ids.append(attestation_id)
    if len(attestation_ids) != len(set(attestation_ids)):
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            "incremental epoch attestation was reused"
        )
    return tuple(attestation_ids)


def verify_registration_disjoint_incremental_attestation_sequence_v1(
    *,
    epoch_ids: tuple[str, ...],
    attestations: tuple[
        incremental_independent
        .RegistrationDisjointIncrementalEpochVerificationV1,
        ...,
    ],
) -> tuple[str, ...]:
    """Exercise missing/reordered/stale lineage without target authority."""

    if (
        type(attestations) is not tuple
        or any(
            type(item)
            is not (
                incremental_independent
                .RegistrationDisjointIncrementalEpochVerificationV1
            )
            for item in attestations
        )
    ):
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            "registration-disjoint attestations have the wrong exact type"
        )
    return _incremental_attestation_ids(
        epoch_ids=epoch_ids,
        bindings=tuple(
            (
                item.round_index,
                item.prior_epoch_id,
                item.claimed_epoch_id,
                item.verification_id,
            )
            for item in attestations
        ),
    )


def _preflight(
    *,
    authority_chain: Any,
    anchor: Any,
    occurrence_plan: Any,
    context: Any,
    claimed: Any,
) -> None:
    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or authority_chain.remote_main_anchor is not anchor
        or type(occurrence_plan)
        is not consumer.RegisteredOccurrenceExecutionPlanV1
        or occurrence_plan.chain_id != authority_chain.chain_id
        or type(context) is not prereg.HeldoutPublicGraphContextV2
        or context not in prereg.registered_heldout_public_contexts_v2()
        or occurrence_plan.template.context_id != context.context_id
        or occurrence_plan.template.arm not in prereg.ARM_ORDER[:-1]
        or occurrence_plan.template.route_kind
        is not consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT
        or type(claimed) is not runtime.RegisteredAdaptiveOccurrenceResultV1
    ):
        raise RegisteredAdaptiveRuntimeIndependentGateLockedV1(
            "independent adaptive replay requires exact chain-bound inputs"
        )
    try:
        consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (
        consumer.RegisteredCampaignAuthorityGateLockedV1,
        ValueError,
    ) as error:
        raise RegisteredAdaptiveRuntimeIndependentGateLockedV1(
            "independent adaptive authority chain is stale"
        ) from error
    if (
        claimed.authority_chain_id != authority_chain.chain_id
        or claimed.anchor_id != anchor.anchor_id
        or claimed.occurrence_plan != occurrence_plan
        or claimed.context != context
    ):
        raise RegisteredAdaptiveRuntimeIndependentGateLockedV1(
            "independent adaptive result identity is foreign"
        )


_VERIFICATION_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredAdaptiveRuntimeIndependentVerificationV1:
    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    occurrence_id: str
    context_id: str
    result_id: str
    certificate_id: str | None
    status: runtime.RegisteredAdaptiveOccurrenceStatusV1
    adapter_status: runtime.RegisteredAdaptiveGroundAdapterStatusV1
    epoch_ids: tuple[str, ...]
    incremental_epoch_attestations: tuple[
        incremental_independent
        .RegisteredIncrementalEpochIndependentAttestationV1,
        ...,
    ]
    model_replay_attestation_ids: tuple[str, ...]
    planner_component_result_ids: tuple[str, ...]
    planner_independent_verification_ids: tuple[str, ...]
    selector_independent_attestation_ids: tuple[str, ...]
    concretizer_decision_ids: tuple[str, ...]
    ground_policy_decision_ids: tuple[str, ...]
    work_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.authority_chain_id,
            self.anchor_id,
            self.occurrence_id,
            self.context_id,
            self.result_id,
            self.work_id,
            *self.epoch_ids,
            *self.model_replay_attestation_ids,
            *self.planner_component_result_ids,
            *self.planner_independent_verification_ids,
            *self.selector_independent_attestation_ids,
            *self.concretizer_decision_ids,
            *self.ground_policy_decision_ids,
        ):
            _cid(value, "independent adaptive identity")
        if self.certificate_id is not None:
            _cid(self.certificate_id, "independent adaptive certificate")
        if (
            type(self.incremental_epoch_attestations) is not tuple
            or any(
                type(item)
                is not (
                    incremental_independent
                    .RegisteredIncrementalEpochIndependentAttestationV1
                )
                for item in self.incremental_epoch_attestations
            )
        ):
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "incremental epoch attestations have the wrong exact type"
            )
        _incremental_attestation_ids(
            epoch_ids=self.epoch_ids,
            bindings=tuple(
                (
                    item.round_index,
                    item.predecessor_epoch_id,
                    item.claimed_epoch_id,
                    item.attestation_id,
                )
                for item in self.incremental_epoch_attestations
            ),
        )
        if (
            self._minting_capability is not _VERIFICATION_MINTING_SENTINEL
            or type(self.status)
            is not runtime.RegisteredAdaptiveOccurrenceStatusV1
            or type(self.adapter_status)
            is not runtime.RegisteredAdaptiveGroundAdapterStatusV1
            or not self.epoch_ids
            or len(self.epoch_ids) != len(self.model_replay_attestation_ids)
            or len(self.epoch_ids) != len(self.planner_component_result_ids)
            or any(
                item.authority_chain_id != self.authority_chain_id
                or item.anchor_id != self.anchor_id
                or item.occurrence_id != self.occurrence_id
                or item.context_id != self.context_id
                for item in self.incremental_epoch_attestations
            )
            or (
                self.status
                is runtime.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
            )
            != (
                self.certificate_id is not None
                and bool(self.concretizer_decision_ids)
            )
            or (
                self.adapter_status
                is (
                    runtime.RegisteredAdaptiveGroundAdapterStatusV1
                    .SINGLETON_GROUND_POLICY_READY
                )
            )
            != (
                bool(self.ground_policy_decision_ids)
                and len(self.ground_policy_decision_ids)
                == len(self.concretizer_decision_ids)
            )
            or (
                self.adapter_status
                is (
                    runtime.RegisteredAdaptiveGroundAdapterStatusV1
                    .FIXED_CONCRETIZER_OPERATIONAL_POLICY_SCHEMA_NOT_INTEGRATED
                )
            )
            != (
                self.status
                is runtime.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
                and not self.ground_policy_decision_ids
            )
        ):
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "independent adaptive verification was not privately replayed"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _hash(self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_adaptive_runtime_"
                "independent_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "result_id": self.result_id,
            "certificate_id": self.certificate_id,
            "status": self.status.value,
            "adapter_status": self.adapter_status.value,
            "epoch_ids": list(self.epoch_ids),
            "incremental_epoch_independent_attestation_ids": list(
                self.incremental_epoch_independent_attestation_ids
            ),
            "model_replay_attestation_ids": list(
                self.model_replay_attestation_ids
            ),
            "planner_component_result_ids": list(
                self.planner_component_result_ids
            ),
            "planner_independent_verification_ids": list(
                self.planner_independent_verification_ids
            ),
            "selector_independent_attestation_ids": list(
                self.selector_independent_attestation_ids
            ),
            "concretizer_decision_ids": list(
                self.concretizer_decision_ids
            ),
            "ground_policy_decision_ids": list(
                self.ground_policy_decision_ids
            ),
            "work_id": self.work_id,
            "model_replays": len(self.epoch_ids),
            "incremental_epoch_replays": len(
                self.incremental_epoch_attestations
            ),
            "planner_replays": len(self.planner_component_result_ids),
            "selector_replays": len(
                self.selector_independent_attestation_ids
            ),
            "observer_stream_opens": 0,
            "observer_draw_calls": 0,
            "fixed_concretizer_support_independently_recomputed": True,
            "exact_fraction_weights_independently_recomputed": True,
            "source_quantities_used_in_confidence_model_certificate": False,
        }

    @property
    def incremental_epoch_independent_attestation_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            item.attestation_id
            for item in self.incremental_epoch_attestations
        )

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_registered_adaptive_runtime_independently_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
    claimed: runtime.RegisteredAdaptiveOccurrenceResultV1,
) -> RegisteredAdaptiveRuntimeIndependentVerificationV1:
    """Replay all model/proof/selector/policy/status identities, target-free."""

    _preflight(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=occurrence_plan,
        context=context,
        claimed=claimed,
    )
    model_attestation_ids = []
    planner_verification_ids = []
    selected_closures = tuple(
        item
        for item in claimed.selector_closures
        if item.claim.decision.outcome
        is selector.RegisteredSelectorOutcomeV1.SELECTED
    )
    if len(selected_closures) != len(claimed.epochs) - 1:
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            "incremental epochs and selected selector closures diverge"
        )
    incremental_attestations = []
    for index, (epoch, closure) in enumerate(
        zip(
            claimed.epochs[1:],
            selected_closures,
            strict=True,
        ),
        start=1,
    ):
        if (
            type(epoch)
            is not incremental.RegisteredIncrementalH2ModelEpochV1
            or epoch.selector_closure != closure
        ):
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "incremental epoch uses a missing or reordered selector closure"
            )
        replayed_epoch = (
            incremental_independent
            .verify_registered_incremental_h2_model_epoch_independently_v1(
                authority_chain=authority_chain,
                anchor=anchor,
                occurrence_plan=occurrence_plan,
                context=context,
                prior_epoch=claimed.epochs[index - 1],
                selector_closure=closure,
                claimed=epoch,
            )
        )
        if (
            replayed_epoch.claimed_epoch_id != epoch.epoch_id
            or replayed_epoch.predecessor_epoch_id
            != claimed.epochs[index - 1].epoch_id
            or replayed_epoch.selector_closure_id != closure.closure_id
            or replayed_epoch.access_audit.observer_stream_opens != 0
            or replayed_epoch.access_audit.observer_draw_calls != 0
        ):
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "incremental epoch independent attestation is stale"
            )
        incremental_attestations.append(replayed_epoch)
    _incremental_attestation_ids(
        epoch_ids=tuple(item.epoch_id for item in claimed.epochs),
        bindings=tuple(
            (
                item.round_index,
                item.predecessor_epoch_id,
                item.claimed_epoch_id,
                item.attestation_id,
            )
            for item in incremental_attestations
        ),
    )
    for epoch, component in zip(
        claimed.epochs,
        claimed.planner_results,
        strict=True,
    ):
        pair = _epoch_pair(epoch)
        model_replay = (
            model_verifier
            .verify_registered_cold_h2_model_pair_independently_v1(
                anchor,
                authority_chain.remote_main_anchor_attestation,
                pair,
            )
        )
        if (
            model_replay.to_document()
            != epoch.model_replay_attestation.to_document()
        ):
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "independent adaptive model replay differs"
            )
        model_attestation_ids.append(model_replay.attestation_id)
        replanned = planner.solve_and_verify_v072_exact_lazy_h2_v1(
            model=pair.quotient_planner_model,
            threshold=pair.threshold_profile,
            solver_kind=robust.RobustSolverKind.QUOTIENT,
        )
        if replanned.to_document() != component.to_document():
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "independent adaptive exact-lazy replay differs"
            )
        if replanned.independent_verification is not None:
            planner_verification_ids.append(
                replanned.independent_verification.verification_id
            )
    selector_attestation_ids = []
    for index, closure in enumerate(claimed.selector_closures):
        epoch = claimed.epochs[index]
        solve = claimed.planner_results[index].solve_result
        audit = solve.audit
        if audit is None:
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "selector follows a resource-exhausted planner result"
            )
        predecessor = (
            None
            if index == 0
            else claimed.epochs[index].frontier
        )
        replayed = selector_verifier.verify_registered_selector_independently_v1(
            authority_chain=authority_chain,
            anchor=anchor,
            occurrence_plan=occurrence_plan,
            failed_audit=audit,
            model_pair=_epoch_pair(epoch),
            model_replay_attestation=epoch.model_replay_attestation,
            acquisitions=_epoch_acquisitions(epoch),
            round_index=index + 1,
            predecessor_frontier=predecessor,
            claimed=closure.claim,
        )
        if replayed.to_document() != closure.independent_attestation.to_document():
            raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
                "independent adaptive selector replay differs"
            )
        selector_attestation_ids.append(replayed.attestation_id)
    expected_status = _terminal_status(claimed)
    if expected_status is runtime.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED:
        audit = claimed.planner_results[-1].solve_result.audit
        assert audit is not None
        concretizer_policy, ground_policy = _policy_support(
            _epoch_pair(claimed.epochs[-1]),
            audit,
        )
    else:
        concretizer_policy, ground_policy = (), ()
    expected_adapter_status = _adapter_status(
        status=expected_status,
        concretizer_policy=concretizer_policy,
        ground_policy=ground_policy,
    )
    expected_certificate_id = None
    if expected_status is runtime.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED:
        final_audit = claimed.planner_results[-1].solve_result.audit
        assert final_audit is not None
        expected_certificate_id = _certificate_id(
            authority_chain_id=authority_chain.chain_id,
            anchor_id=anchor.anchor_id,
            occurrence_id=occurrence_plan.occurrence_id,
            context_id=context.context_id,
            final_model_pair_id=_epoch_pair(
                claimed.epochs[-1]
            ).model_pair_id,
            planner_component_result_id=(
                claimed.planner_results[-1].component_result_id
            ),
            audit_id=final_audit.audit_id,
            concretizer_decision_ids=tuple(
                item.decision_id for item in concretizer_policy
            ),
        )
    if (
        claimed.status is not expected_status
        or claimed.adapter_status is not expected_adapter_status
        or claimed.certificate_id != expected_certificate_id
        or concretizer_policy != claimed.concretizer_policy
        or ground_policy != claimed.ground_policy
        or _work(claimed) != claimed.work
    ):
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            "independent adaptive policy or work replay differs"
        )
    # Re-run the raw result invariants through its canonical document hash.
    if claimed.result_id != hashlib.sha256(
        runtime.DOMAIN_TAGS["registered_result"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(claimed._payload())
    ).hexdigest():
        raise V072RegisteredAdaptiveRuntimeIndependentVerificationFailure(
            "independent adaptive result content ID differs"
        )
    return RegisteredAdaptiveRuntimeIndependentVerificationV1(
        _VERIFICATION_MINTING_SENTINEL,
        authority_chain.chain_id,
        anchor.anchor_id,
        occurrence_plan.occurrence_id,
        context.context_id,
        claimed.result_id,
        expected_certificate_id,
        expected_status,
        expected_adapter_status,
        tuple(item.epoch_id for item in claimed.epochs),
        tuple(incremental_attestations),
        tuple(model_attestation_ids),
        tuple(
            item.component_result_id for item in claimed.planner_results
        ),
        tuple(planner_verification_ids),
        tuple(selector_attestation_ids),
        tuple(
            item.decision_id for item in claimed.concretizer_policy
        ),
        tuple(item.decision_id for item in claimed.ground_policy),
        claimed.work.work_id,
    )


__all__ = [
    "PROFILE_KEY",
    "RegisteredAdaptiveRuntimeIndependentGateLockedV1",
    "RegisteredAdaptiveRuntimeIndependentVerificationV1",
    "SCHEMA_VERSION",
    "V072RegisteredAdaptiveRuntimeIndependentVerificationFailure",
    "verify_registration_disjoint_incremental_attestation_sequence_v1",
    "verify_registered_adaptive_runtime_independently_v1",
]
