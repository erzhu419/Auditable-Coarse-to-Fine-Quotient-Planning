"""Registered incremental acquisition and immutable model-epoch rebuild.

The production entry point consumes one exact cold/incremental model epoch and
one independently verified ``RegisteredSelectorClosureV1``.  It mechanically
executes the selected promotion and every selected new-child row, independently
replays each acquisition, retains the complete evidence history, chooses only
the latest version of each physical row for the active closure, and rebuilds
and independently verifies a new immutable direct/quotient model epoch.

No caller can provide rows, observations, laws, seeds, counts, statuses,
projections, models, or callbacks.  Registration-disjoint types at the bottom
exercise the same lineage/latest-row/accounting rules without target access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_v1 as cold
from acfqp import (
    v072_cold_h2_closure_independent_verifier_v1 as cold_independent,
)
from acfqp import v072_cold_h2_model_builders_v1 as models
from acfqp import (
    v072_cold_h2_model_builders_independent_verifier_v1
    as model_independent,
)
from acfqp import v072_confidence_row_projection_v1 as projection
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_heldout_public_graph_adapter_v1 as public_adapter
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_registered_cold_h2_orchestrator_v1 as cold_runtime
from acfqp import (
    v072_registered_target_confidence_accumulator_v1 as accumulator,
)
from acfqp import (
    v072_registered_target_confidence_independent_verifier_v1
    as confidence_independent,
)
from acfqp import v072_registered_target_selector_v1 as selector
from acfqp import (
    v072_registered_target_selector_independent_verifier_v1
    as selector_independent,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_incremental_epoch_materializer_v1"
MAX_INCREMENTAL_ROUNDS = prereg.MAX_ROUNDS


class V072RegisteredIncrementalEpochMaterializerViolation(ValueError):
    """A gate, selector, lineage, evidence, closure, or model invariant failed."""


class RegisteredIncrementalEpochMaterializerLockedV1(RuntimeError):
    """Production inputs were not one exact chain-bound materialization."""

    def __init__(
        self,
        message: str,
        *,
        access_audit: "RegisteredIncrementalEpochAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.access_audit = access_audit


DOMAIN_TAGS = {
    "access": (
        "acfqp:v072-registered-incremental-epoch-materializer-access:v1"
    ),
    "epoch": "acfqp:v072-registered-incremental-h2-model-epoch:v1",
    "synthetic_acquisition": (
        "acfqp:v072-registration-disjoint-incremental-acquisition:v1"
    ),
    "synthetic_replay": (
        "acfqp:v072-registration-disjoint-incremental-replay:v1"
    ),
    "synthetic_selector": (
        "acfqp:v072-registration-disjoint-selector-closure:v1"
    ),
    "synthetic_frontier": (
        "acfqp:v072-registration-disjoint-incremental-frontier:v1"
    ),
    "synthetic_closure": (
        "acfqp:v072-registration-disjoint-incremental-active-closure:v1"
    ),
    "synthetic_closure_verification": (
        "acfqp:v072-registration-disjoint-incremental-"
        "active-closure-verification:v1"
    ),
    "synthetic_model": (
        "acfqp:v072-registration-disjoint-incremental-model-pair:v1"
    ),
    "synthetic_model_verification": (
        "acfqp:v072-registration-disjoint-incremental-"
        "model-verification:v1"
    ),
    "synthetic_work": (
        "acfqp:v072-registration-disjoint-incremental-work:v1"
    ),
    "synthetic_epoch": (
        "acfqp:v072-registration-disjoint-incremental-epoch:v1"
    ),
}


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072RegisteredIncrementalEpochMaterializerViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredIncrementalEpochMaterializerViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class RegisteredIncrementalEpochAccessAuditV1:
    authority_chain_verifications: int = 0
    prior_epoch_checks: int = 0
    selector_closure_checks: int = 0
    acquisition_calls: int = 0
    independent_confidence_replay_calls: int = 0
    producer_stream_opens: int = 0
    producer_draw_calls: int = 0
    replay_stream_opens: int = 0
    replay_draw_calls: int = 0
    unique_online_sample_evidence_draws: int = 0
    total_observer_draw_calls: int = 0
    historical_acquisition_count: int = 0
    active_physical_row_count: int = 0
    superseded_historical_version_count: int = 0
    closure_builds: int = 0
    closure_independent_verifications: int = 0
    projection_calls: int = 0
    model_pair_builds: int = 0
    model_pair_independent_verifications: int = 0

    def __post_init__(self) -> None:
        if any(
            type(getattr(self, name)) is not int
            or getattr(self, name) < 0
            for name in self.__dataclass_fields__
        ):
            raise V072RegisteredIncrementalEpochMaterializerViolation(
                "incremental materializer access counters are malformed"
            )
        if (
            self.unique_online_sample_evidence_draws
            != self.producer_draw_calls
            or self.total_observer_draw_calls
            != self.producer_draw_calls + self.replay_draw_calls
            or self.superseded_historical_version_count
            != (
                self.historical_acquisition_count
                - self.active_physical_row_count
            )
        ):
            raise V072RegisteredIncrementalEpochMaterializerViolation(
                "incremental sample/history accounting does not reconcile"
            )

    @property
    def target_access_started(self) -> bool:
        return any(
            getattr(self, name)
            for name in self.__dataclass_fields__
            if name
            not in (
                "authority_chain_verifications",
                "prior_epoch_checks",
                "selector_closure_checks",
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_incremental_epoch_"
                "materializer_access.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
            "target_access_started": self.target_access_started,
        }

    @property
    def audit_id(self) -> str:
        return _content_id("access", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


ZERO_ACCESS_AUDIT = RegisteredIncrementalEpochAccessAuditV1()


def _paired_history(
    acquisitions: tuple[
        accumulator.RegisteredTargetRowAcquisitionV1, ...
    ],
    replays: tuple[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ...,
    ],
) -> tuple[
    tuple[
        accumulator.RegisteredTargetRowAcquisitionV1,
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
    ],
    ...,
]:
    if (
        type(acquisitions) is not tuple
        or not acquisitions
        or type(replays) is not tuple
        or len(acquisitions) != len(replays)
        or any(
            type(acquisition)
            is not accumulator.RegisteredTargetRowAcquisitionV1
            or type(replay)
            is not (
                confidence_independent
                .RegisteredTargetConfidenceReplayBundleV1
            )
            or replay.acquisition != acquisition
            for acquisition, replay in zip(
                acquisitions,
                replays,
                strict=True,
            )
        )
        or tuple(item.acquisition_id for item in acquisitions)
        != tuple(
            sorted({item.acquisition_id for item in acquisitions})
        )
    ):
        raise V072RegisteredIncrementalEpochMaterializerViolation(
            "incremental acquisition/replay history is incomplete or reordered"
        )
    return tuple(zip(acquisitions, replays, strict=True))


def _latest_active_pairs(
    pairs: tuple[
        tuple[
            accumulator.RegisteredTargetRowAcquisitionV1,
            confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ],
        ...,
    ],
) -> tuple[
    tuple[
        accumulator.RegisteredTargetRowAcquisitionV1,
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
    ],
    ...,
]:
    by_row: dict[
        str,
        tuple[
            accumulator.RegisteredTargetRowAcquisitionV1,
            confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ],
    ] = {}
    for acquisition, replay in pairs:
        previous = by_row.get(acquisition.row_binding_id)
        if previous is None:
            by_row[acquisition.row_binding_id] = (acquisition, replay)
            continue
        previous_acquisition = previous[0]
        if acquisition.round_index == previous_acquisition.round_index:
            raise V072RegisteredIncrementalEpochMaterializerViolation(
                "one physical row has replacement evidence in the same round"
            )
        if acquisition.round_index > previous_acquisition.round_index:
            by_row[acquisition.row_binding_id] = (acquisition, replay)
    return tuple(
        sorted(by_row.values(), key=lambda item: item[0].row_binding_id)
    )


_EPOCH_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredIncrementalH2ModelEpochV1:
    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1
    context: prereg.HeldoutPublicGraphContextV2
    round_index: int
    predecessor_epoch_id: str
    predecessor_acquisition_ids: tuple[str, ...]
    predecessor_frontier_id: str | None
    selector_closure: selector.RegisteredSelectorClosureV1
    adapter: public_adapter.HeldoutPublicGraphColdClosureAdapterV1
    acquisition_history: tuple[
        accumulator.RegisteredTargetRowAcquisitionV1, ...
    ]
    confidence_replay_history: tuple[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ...,
    ]
    new_acquisitions: tuple[
        accumulator.RegisteredTargetRowAcquisitionV1, ...
    ]
    new_confidence_replays: tuple[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ...,
    ]
    active_confidence_replays: tuple[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ...,
    ]
    closure_bundle: cold.V072ColdH2ClosureBundleV1
    closure_verification: (
        cold_independent.V072ColdH2IndependentVerificationV1
    )
    row_projections: tuple[
        projection.RegisteredConfidenceIntervalSimplexRowProjectionV1,
        ...,
    ]
    model_pair: models.RegisteredColdH2ModelPairV1
    model_replay_attestation: (
        model_independent
        .RegisteredColdH2ModelIndependentReplayAttestationV1
    )
    access_audit: RegisteredIncrementalEpochAccessAuditV1
    _epoch_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authority_chain_id, "incremental epoch authority chain"),
            (self.anchor_id, "incremental epoch anchor"),
            (self.predecessor_epoch_id, "incremental predecessor epoch"),
        ):
            _cid(value, label)
        if self.predecessor_frontier_id is not None:
            _cid(
                self.predecessor_frontier_id,
                "incremental predecessor frontier",
            )
        for value in self.predecessor_acquisition_ids:
            _cid(value, "incremental predecessor acquisition")
        history_pairs = _paired_history(
            self.acquisition_history,
            self.confidence_replay_history,
        )
        new_pairs = _paired_history(
            self.new_acquisitions,
            self.new_confidence_replays,
        )
        active_pairs = _latest_active_pairs(history_pairs)
        active_replays = tuple(item[1] for item in active_pairs)
        active_row_ids = tuple(
            sorted(item.row_evidence.row_evidence_id
                   for item in active_replays)
        )
        projection_row_ids = tuple(
            sorted(item.row_evidence_id for item in self.row_projections)
        )
        history_ids = tuple(
            item.acquisition_id for item in self.acquisition_history
        )
        new_ids = tuple(item.acquisition_id for item in self.new_acquisitions)
        if (
            self._minting_capability is not _EPOCH_MINTING_SENTINEL
            or self.round_index not in (1, 2)
            or type(self.occurrence_plan)
            is not consumer.RegisteredOccurrenceExecutionPlanV1
            or self.occurrence_plan.chain_id != self.authority_chain_id
            or self.occurrence_plan.template.context_id
            != self.context.context_id
            or self.occurrence_plan.template.arm
            not in prereg.ARM_ORDER[:-1]
            or type(self.context) is not prereg.HeldoutPublicGraphContextV2
            or type(self.selector_closure)
            is not selector.RegisteredSelectorClosureV1
            or self.selector_closure.frontier is None
            or self.selector_closure.claim.round_index != self.round_index
            or self.selector_closure.claim.occurrence_id
            != self.occurrence_plan.occurrence_id
            or self.selector_closure.frontier.predecessor_frontier_id
            != self.predecessor_frontier_id
            or type(self.adapter)
            is not public_adapter.HeldoutPublicGraphColdClosureAdapterV1
            or self.adapter.context_id != self.context.context_id
            or self.predecessor_acquisition_ids
            != tuple(sorted(set(self.predecessor_acquisition_ids)))
            or not self.predecessor_acquisition_ids
            or set(self.predecessor_acquisition_ids)
            & set(new_ids)
            or tuple(
                sorted((*self.predecessor_acquisition_ids, *new_ids))
            )
            != history_ids
            or self.active_confidence_replays != active_replays
            or type(self.closure_bundle)
            is not cold.V072ColdH2ClosureBundleV1
            or self.closure_bundle.context_id != self.context.context_id
            or self.closure_bundle.arm != self.occurrence_plan.template.arm
            or tuple(
                sorted(item.row_evidence_id
                       for item in self.closure_bundle.all_rows)
            ) != active_row_ids
            or type(self.closure_verification)
            is not cold_independent.V072ColdH2IndependentVerificationV1
            or self.closure_verification.closure_id
            != self.closure_bundle.closure_id
            or projection_row_ids != active_row_ids
            or type(self.model_pair)
            is not models.RegisteredColdH2ModelPairV1
            or self.model_pair.closure_bundle != self.closure_bundle
            or self.model_pair.model_pair_id
            != self.model_replay_attestation.model_pair_id
            or self.model_replay_attestation.remote_main_anchor_id
            != self.anchor_id
            or self.model_replay_attestation.context_id
            != self.context.context_id
            or self.model_replay_attestation.closure_id
            != self.closure_bundle.closure_id
            or type(self.access_audit)
            is not RegisteredIncrementalEpochAccessAuditV1
            or self.access_audit.acquisition_calls != len(new_ids)
            or self.access_audit.independent_confidence_replay_calls
            != len(new_ids)
            or self.access_audit.historical_acquisition_count
            != len(history_ids)
            or self.access_audit.active_physical_row_count
            != len(active_replays)
            or self.access_audit.projection_calls
            != len(self.row_projections)
        ):
            raise V072RegisteredIncrementalEpochMaterializerViolation(
                "registered incremental model epoch does not reconcile"
            )
        object.__setattr__(
            self,
            "_epoch_id",
            _content_id("epoch", self._payload()),
        )

    @property
    def acquisitions(
        self,
    ) -> tuple[accumulator.RegisteredTargetRowAcquisitionV1, ...]:
        return self.acquisition_history

    @property
    def confidence_replays(
        self,
    ) -> tuple[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ...,
    ]:
        return self.confidence_replay_history

    @property
    def frontier(self) -> accumulator.RegisteredAcquisitionFrontierV1:
        assert self.selector_closure.frontier is not None
        return self.selector_closure.frontier

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_incremental_h2_model_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "occurrence_id": self.occurrence_plan.occurrence_id,
            "context_id": self.context.context_id,
            "arm": self.occurrence_plan.template.arm,
            "round_index": self.round_index,
            "predecessor_epoch_id": self.predecessor_epoch_id,
            "predecessor_acquisition_ids": list(
                self.predecessor_acquisition_ids
            ),
            "predecessor_frontier_id": self.predecessor_frontier_id,
            "selector_closure_id": self.selector_closure.closure_id,
            "frontier_id": self.frontier.frontier_id,
            "acquisition_history_ids": [
                item.acquisition_id for item in self.acquisition_history
            ],
            "confidence_replay_history_ids": [
                item.bundle_id for item in self.confidence_replay_history
            ],
            "new_acquisition_ids": [
                item.acquisition_id for item in self.new_acquisitions
            ],
            "new_confidence_replay_ids": [
                item.bundle_id for item in self.new_confidence_replays
            ],
            "active_confidence_replay_ids": [
                item.bundle_id for item in self.active_confidence_replays
            ],
            "closure_id": self.closure_bundle.closure_id,
            "closure_verification_id": (
                self.closure_verification.verification_id
            ),
            "projection_ids": [
                item.projection_id for item in self.row_projections
            ],
            "model_pair_id": self.model_pair.model_pair_id,
            "model_replay_attestation_id": (
                self.model_replay_attestation.attestation_id
            ),
            "access_audit_id": self.access_audit.audit_id,
            "all_historical_evidence_retained": True,
            "active_closure_latest_physical_row_only": True,
            "immutable": True,
            "caller_rows_status_counts_or_callbacks_accepted": False,
        }

    @property
    def epoch_id(self) -> str:
        return self._epoch_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "selector_closure": {
                "closure_id": self.selector_closure.closure_id,
                "claim_id": self.selector_closure.claim.claim_id,
                "attestation_id": (
                    self.selector_closure
                    .independent_attestation.attestation_id
                ),
            },
            "acquisition_history": [
                item.to_document() for item in self.acquisition_history
            ],
            "confidence_replay_history": [
                item.to_document() for item in self.confidence_replay_history
            ],
            "active_confidence_replays": [
                item.to_document() for item in self.active_confidence_replays
            ],
            "closure_bundle": self.closure_bundle.to_document(),
            "closure_verification": (
                self.closure_verification.to_document()
            ),
            "row_projections": [
                item.to_document() for item in self.row_projections
            ],
            "model_pair": self.model_pair.to_document(),
            "model_replay_attestation": (
                self.model_replay_attestation.to_document()
            ),
            "access_audit": self.access_audit.to_document(),
            "epoch_id": self.epoch_id,
        }


PriorRegisteredModelEpochV1 = (
    cold_runtime.RegisteredColdH2ModelEpochV1
    | RegisteredIncrementalH2ModelEpochV1
)


def _prior_parts(
    prior_epoch: PriorRegisteredModelEpochV1,
) -> tuple[
    int,
    str,
    tuple[accumulator.RegisteredTargetRowAcquisitionV1, ...],
    tuple[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ...,
    ],
    tuple[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ...,
    ],
    public_adapter.HeldoutPublicGraphColdClosureAdapterV1,
    models.RegisteredColdH2ModelPairV1,
    model_independent.RegisteredColdH2ModelIndependentReplayAttestationV1,
    accumulator.RegisteredAcquisitionFrontierV1 | None,
    tuple[str, ...],
]:
    if type(prior_epoch) is cold_runtime.RegisteredColdH2ModelEpochV1:
        history = prior_epoch.acquisitions
        replays = prior_epoch.confidence_replays
        return (
            0,
            prior_epoch.epoch_id,
            history,
            replays,
            replays,
            prior_epoch.adapter,
            prior_epoch.model_pair,
            prior_epoch.model_replay_attestation,
            None,
            (),
        )
    if type(prior_epoch) is RegisteredIncrementalH2ModelEpochV1:
        return (
            prior_epoch.round_index,
            prior_epoch.epoch_id,
            prior_epoch.acquisition_history,
            prior_epoch.confidence_replay_history,
            prior_epoch.active_confidence_replays,
            prior_epoch.adapter,
            prior_epoch.model_pair,
            prior_epoch.model_replay_attestation,
            prior_epoch.frontier,
            prior_epoch.frontier.supporting_acquisition_ids,
        )
    raise RegisteredIncrementalEpochMaterializerLockedV1(
        "incremental materializer requires one exact cold/incremental epoch",
        access_audit=ZERO_ACCESS_AUDIT,
    )


def _validate_preobserver_inputs(
    *,
    authority_chain: Any,
    anchor: Any,
    occurrence_plan: Any,
    context: Any,
    prior_epoch: Any,
    selector_closure: Any,
) -> tuple[
    consumer.RegisteredCampaignAuthorityChainV1,
    final_authority.V072RemoteMainAnchorV1,
    consumer.RegisteredOccurrenceExecutionPlanV1,
    prereg.HeldoutPublicGraphContextV2,
    PriorRegisteredModelEpochV1,
    selector.RegisteredSelectorClosureV1,
]:
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
        or type(prior_epoch)
        not in (
            cold_runtime.RegisteredColdH2ModelEpochV1,
            RegisteredIncrementalH2ModelEpochV1,
        )
        or type(selector_closure)
        is not selector.RegisteredSelectorClosureV1
    ):
        raise RegisteredIncrementalEpochMaterializerLockedV1(
            "incremental materializer requires exact chain-bound typed inputs",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    try:
        consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (
        consumer.RegisteredCampaignAuthorityGateLockedV1,
        ValueError,
    ) as error:
        raise RegisteredIncrementalEpochMaterializerLockedV1(
            "incremental materializer authority replay failed preobserver",
            access_audit=ZERO_ACCESS_AUDIT,
        ) from error
    (
        prior_round,
        _prior_id,
        acquisitions,
        _replays,
        _active,
        _adapter,
        prior_model,
        prior_model_attestation,
        prior_frontier,
        prior_selector_support,
    ) = _prior_parts(prior_epoch)
    if (
        prior_epoch.authority_chain_id != authority_chain.chain_id
        or prior_epoch.anchor_id != anchor.anchor_id
        or prior_epoch.occurrence_plan != occurrence_plan
        or prior_epoch.context != context
        or prior_round >= MAX_INCREMENTAL_ROUNDS
        or selector_closure.claim.round_index != prior_round + 1
        or selector_closure.claim.authority_chain_id
        != authority_chain.chain_id
        or selector_closure.claim.anchor_id != anchor.anchor_id
        or selector_closure.claim.occurrence_id
        != occurrence_plan.occurrence_id
        or selector_closure.claim.context_id != context.context_id
        or selector_closure.claim.arm != occurrence_plan.template.arm
        or selector_closure.claim.model_pair_id
        != prior_model.model_pair_id
        or selector_closure.claim.model_replay_attestation_id
        != prior_model_attestation.attestation_id
        or selector_closure.claim.supporting_acquisition_ids
        != tuple(item.acquisition_id for item in acquisitions)
        or selector_closure.claim.decision.outcome
        is not selector.RegisteredSelectorOutcomeV1.SELECTED
        or type(selector_closure.independent_attestation)
        is not selector_independent.RegisteredSelectorIndependentAttestationV1
        or selector_closure.selection_authority is None
        or selector_closure.frontier is None
        or selector_closure.frontier.supporting_acquisition_ids
        != tuple(item.acquisition_id for item in acquisitions)
        or (
            prior_round == 0
            and (
                selector_closure.claim.predecessor_frontier_id is not None
                or selector_closure.frontier.predecessor_frontier_id
                is not None
            )
        )
        or (
            prior_round == 1
            and (
                prior_frontier is None
                or selector_closure.claim.predecessor_frontier_id
                != prior_frontier.frontier_id
                or selector_closure.frontier.predecessor_frontier_id
                != prior_frontier.frontier_id
                or not set(prior_selector_support)
                < set(selector_closure.claim.supporting_acquisition_ids)
            )
        )
    ):
        raise RegisteredIncrementalEpochMaterializerLockedV1(
            "selector closure is stale, nonselected, or breaks round lineage",
            access_audit=RegisteredIncrementalEpochAccessAuditV1(
                authority_chain_verifications=1,
                prior_epoch_checks=1,
            ),
        )
    return (
        authority_chain,
        anchor,
        occurrence_plan,
        context,
        prior_epoch,
        selector_closure,
    )


def _purpose(
    round_index: int,
    *,
    promotion: bool,
) -> accumulator.RegisteredTargetAcquisitionPurposeV1:
    return {
        (1, True): (
            accumulator.RegisteredTargetAcquisitionPurposeV1
            .INCREMENTAL_PROMOTION_ROUND_1
        ),
        (2, True): (
            accumulator.RegisteredTargetAcquisitionPurposeV1
            .INCREMENTAL_PROMOTION_ROUND_2
        ),
        (1, False): (
            accumulator.RegisteredTargetAcquisitionPurposeV1
            .INCREMENTAL_NEW_CHILD_ROUND_1
        ),
        (2, False): (
            accumulator.RegisteredTargetAcquisitionPurposeV1
            .INCREMENTAL_NEW_CHILD_ROUND_2
        ),
    }[(round_index, promotion)]


def materialize_registered_incremental_h2_model_epoch_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
    prior_epoch: PriorRegisteredModelEpochV1,
    selector_closure: selector.RegisteredSelectorClosureV1,
) -> RegisteredIncrementalH2ModelEpochV1:
    """Execute one selected target-only round and rebuild one exact epoch."""

    (
        authority_chain,
        anchor,
        occurrence_plan,
        context,
        prior_epoch,
        selector_closure,
    ) = _validate_preobserver_inputs(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=occurrence_plan,
        context=context,
        prior_epoch=prior_epoch,
        selector_closure=selector_closure,
    )
    (
        prior_round,
        prior_epoch_id,
        prior_acquisitions,
        prior_replays,
        prior_active_replays,
        adapter,
        _prior_model,
        _prior_model_attestation,
        prior_frontier,
        _prior_selector_support,
    ) = _prior_parts(prior_epoch)
    round_index = prior_round + 1
    frontier = selector_closure.frontier
    candidate = selector_closure.claim.selected_candidate
    assert frontier is not None and candidate is not None
    history_by_id = {
        item.acquisition_id: item for item in prior_acquisitions
    }
    replay_by_id = {
        item.acquisition_id: replay
        for item, replay in zip(
            prior_acquisitions,
            prior_replays,
            strict=True,
        )
    }
    active_ids = {
        item.acquisition.acquisition_id for item in prior_active_replays
    }
    parent = history_by_id.get(candidate.parent_acquisition_id)
    parent_replay = replay_by_id.get(candidate.parent_acquisition_id)
    if (
        parent is None
        or parent_replay is None
        or parent.acquisition_id not in active_ids
        or parent.row_binding_id != candidate.promotion_row_binding_id
        or parent.round_index != prior_round
        or candidate.selected_row_binding_ids
        != frontier.selected_row_binding_ids
        or candidate.new_child_rows
        != tuple(
            sorted(
                candidate.new_child_rows,
                key=lambda item: item.row_binding_id,
            )
        )
        or tuple(
            item.row_binding_id for item in candidate.new_child_rows
        ) != frontier.new_child_row_binding_ids
    ):
        raise RegisteredIncrementalEpochMaterializerLockedV1(
            "selector candidate is not the complete latest-row acquisition",
            access_audit=RegisteredIncrementalEpochAccessAuditV1(
                authority_chain_verifications=1,
                prior_epoch_checks=1,
                selector_closure_checks=1,
            ),
        )

    new_pairs: list[
        tuple[
            accumulator.RegisteredTargetRowAcquisitionV1,
            confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ]
    ] = []
    promotion_purpose = _purpose(round_index, promotion=True)
    promotion = accumulator.acquire_registered_target_row_v1(
        authority_chain=authority_chain,
        anchor=anchor,
        context=context,
        catalogue=parent.catalogue,
        action=parent.action,
        arm=occurrence_plan.template.arm,
        purpose=promotion_purpose,
        checkpoint=promotion_purpose.required_checkpoint,
        frontier=frontier,
        parent=parent,
    )
    promotion_replay = (
        confidence_independent
        .verify_registered_target_confidence_independently_v1(
            authority_chain=authority_chain,
            anchor=anchor,
            acquisition=promotion,
            parent_replay=parent_replay,
        )
    )
    new_pairs.append((promotion, promotion_replay))
    new_child_purpose = _purpose(round_index, promotion=False)
    for spec in candidate.new_child_rows:
        acquisition = accumulator.acquire_registered_target_row_v1(
            authority_chain=authority_chain,
            anchor=anchor,
            context=context,
            catalogue=spec.catalogue,
            action=spec.action,
            arm=occurrence_plan.template.arm,
            purpose=new_child_purpose,
            checkpoint=new_child_purpose.required_checkpoint,
            frontier=frontier,
        )
        replay = (
            confidence_independent
            .verify_registered_target_confidence_independently_v1(
                authority_chain=authority_chain,
                anchor=anchor,
                acquisition=acquisition,
            )
        )
        new_pairs.append((acquisition, replay))

    combined = tuple(
        sorted(
            (
                *zip(prior_acquisitions, prior_replays, strict=True),
                *new_pairs,
            ),
            key=lambda item: item[0].acquisition_id,
        )
    )
    if len({item[0].acquisition_id for item in combined}) != len(combined):
        raise V072RegisteredIncrementalEpochMaterializerViolation(
            "incremental materialization replaced historical evidence"
        )
    history = tuple(item[0] for item in combined)
    replay_history = tuple(item[1] for item in combined)
    new_sorted = tuple(
        sorted(new_pairs, key=lambda item: item[0].acquisition_id)
    )
    new_acquisitions = tuple(item[0] for item in new_sorted)
    new_replays = tuple(item[1] for item in new_sorted)
    active_pairs = _latest_active_pairs(combined)
    active_replays = tuple(item[1] for item in active_pairs)
    row_evidence = tuple(item.row_evidence for item in active_replays)

    cap_evidence = (
        cold.registered_confirmatory_cold_h2_cap_registry_v1()
        .evidence_for_context(context.context_id)
    )
    closure_bundle = cold.freeze_v072_cold_h2_closure_v1(
        public_graph=adapter,
        row_evidence=row_evidence,
        logical_occurrence_id=occurrence_plan.occurrence_id,
        arm=occurrence_plan.template.arm,
        cap_evidence=cap_evidence,
    )
    closure_verification = (
        cold_independent.verify_v072_cold_h2_closure_independently_v1(
            public_graph=adapter,
            authoritative_row_evidence=row_evidence,
            claimed=closure_bundle,
        )
    )
    projections = tuple(
        sorted(
            (
                projection.project_registered_target_confidence_row_v1(
                    anchor=anchor,
                    confidence_authority=item.confidence_authority,
                )
                for item in active_replays
            ),
            key=lambda item: item.projection_id,
        )
    )
    model_pair = models.build_registered_target_cold_h2_models_v1(
        anchor=anchor,
        closure_bundle=closure_bundle,
        row_projections=projections,
        relational_context=(
            models.registered_cold_h2_relational_context_v1(context)
        ),
    )
    model_replay_attestation = (
        model_independent
        .verify_registered_cold_h2_model_pair_independently_v1(
            anchor,
            authority_chain.remote_main_anchor_attestation,
            model_pair,
        )
    )
    producer_stream_opens = sum(
        1 if item.discovery_support_epoch_chain is None else 2
        for item in new_acquisitions
    )
    producer_draws = sum(
        len(item.transcript.entries) for item in new_acquisitions
    )
    replay_stream_opens = sum(
        item.attestation.replayed_stream_opens for item in new_replays
    )
    replay_draws = sum(
        item.attestation.replayed_draw_calls for item in new_replays
    )
    access_audit = RegisteredIncrementalEpochAccessAuditV1(
        authority_chain_verifications=1,
        prior_epoch_checks=1,
        selector_closure_checks=1,
        acquisition_calls=len(new_acquisitions),
        independent_confidence_replay_calls=len(new_replays),
        producer_stream_opens=producer_stream_opens,
        producer_draw_calls=producer_draws,
        replay_stream_opens=replay_stream_opens,
        replay_draw_calls=replay_draws,
        unique_online_sample_evidence_draws=producer_draws,
        total_observer_draw_calls=producer_draws + replay_draws,
        historical_acquisition_count=len(history),
        active_physical_row_count=len(active_replays),
        superseded_historical_version_count=(
            len(history) - len(active_replays)
        ),
        closure_builds=1,
        closure_independent_verifications=1,
        projection_calls=len(projections),
        model_pair_builds=1,
        model_pair_independent_verifications=1,
    )
    return RegisteredIncrementalH2ModelEpochV1(
        _EPOCH_MINTING_SENTINEL,
        authority_chain.chain_id,
        anchor.anchor_id,
        occurrence_plan,
        context,
        round_index,
        prior_epoch_id,
        tuple(item.acquisition_id for item in prior_acquisitions),
        None if prior_frontier is None else prior_frontier.frontier_id,
        selector_closure,
        adapter,
        history,
        replay_history,
        new_acquisitions,
        new_replays,
        active_replays,
        closure_bundle,
        closure_verification,
        projections,
        model_pair,
        model_replay_attestation,
        access_audit,
    )


class RegistrationDisjointAcquisitionKindV1(str, Enum):
    COLD = "COLD"
    PROMOTION = "PROMOTION"
    NEW_CHILD = "NEW_CHILD"


@dataclass(frozen=True, slots=True)
class RegistrationDisjointIncrementalAcquisitionV1:
    row_binding_id: str
    round_index: int
    kind: RegistrationDisjointAcquisitionKindV1
    parent_acquisition_id: str | None = None
    frontier_id: str | None = None
    _acquisition_id: str = field(init=False, repr=False)
    _replay_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.row_binding_id, "synthetic incremental row")
        if self.parent_acquisition_id is not None:
            _cid(self.parent_acquisition_id, "synthetic promotion parent")
        if self.frontier_id is not None:
            _cid(self.frontier_id, "synthetic acquisition frontier")
        cold_kind = self.kind is RegistrationDisjointAcquisitionKindV1.COLD
        promotion = (
            self.kind is RegistrationDisjointAcquisitionKindV1.PROMOTION
        )
        if (
            type(self.kind) is not RegistrationDisjointAcquisitionKindV1
            or self.round_index not in (0, 1, 2)
            or cold_kind != (self.round_index == 0)
            or cold_kind != (self.frontier_id is None)
            or promotion != (self.parent_acquisition_id is not None)
        ):
            raise V072RegisteredIncrementalEpochMaterializerViolation(
                "registration-disjoint acquisition is malformed"
            )
        acquisition_id = _content_id(
            "synthetic_acquisition",
            self._payload(),
        )
        object.__setattr__(self, "_acquisition_id", acquisition_id)
        object.__setattr__(
            self,
            "_replay_id",
            _content_id(
                "synthetic_replay",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_"
                        "incremental_replay.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "acquisition_id": acquisition_id,
                    "producer_draws": self.producer_draws,
                    "independent_replay_draws": self.producer_draws,
                    "source_prior_used_in_confidence": False,
                    "registered_target_accesses": 0,
                },
            ),
        )

    @property
    def producer_draws(self) -> int:
        if self.kind is RegistrationDisjointAcquisitionKindV1.COLD:
            return (
                prereg.INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
                + prereg.INITIAL_VALIDATION_DRAWS_PER_PHYSICAL_ROW
            )
        if self.kind is RegistrationDisjointAcquisitionKindV1.PROMOTION:
            return prereg.PROMOTION_VALIDATION_DRAWS_PER_ROUND
        return (
            prereg.NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
            + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_incremental_"
                "acquisition.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding_id,
            "round_index": self.round_index,
            "kind": self.kind.value,
            "parent_acquisition_id": self.parent_acquisition_id,
            "frontier_id": self.frontier_id,
            "producer_draws": self.producer_draws,
            "caller_observations_or_counts_accepted": False,
        }

    @property
    def acquisition_id(self) -> str:
        return self._acquisition_id

    @property
    def replay_id(self) -> str:
        return self._replay_id


@dataclass(frozen=True, slots=True)
class RegistrationDisjointSelectorClosureV1:
    round_index: int
    prior_epoch_id: str
    predecessor_frontier_id: str | None
    supporting_acquisition_ids: tuple[str, ...]
    promotion_parent_acquisition_id: str
    promotion_row_binding_id: str
    new_child_row_binding_ids: tuple[str, ...]
    _frontier_id: str = field(init=False, repr=False)
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.prior_epoch_id, "synthetic selector prior epoch"),
            (
                self.promotion_parent_acquisition_id,
                "synthetic selector promotion parent",
            ),
            (
                self.promotion_row_binding_id,
                "synthetic selector promotion row",
            ),
        ):
            _cid(value, label)
        if self.predecessor_frontier_id is not None:
            _cid(
                self.predecessor_frontier_id,
                "synthetic selector predecessor frontier",
            )
        if (
            self.round_index not in (1, 2)
            or (
                self.round_index == 1
                and self.predecessor_frontier_id is not None
            )
            or (
                self.round_index == 2
                and self.predecessor_frontier_id is None
            )
            or self.supporting_acquisition_ids
            != tuple(sorted(set(self.supporting_acquisition_ids)))
            or not self.supporting_acquisition_ids
            or self.new_child_row_binding_ids
            != tuple(sorted(set(self.new_child_row_binding_ids)))
            or self.promotion_parent_acquisition_id
            not in self.supporting_acquisition_ids
        ):
            raise V072RegisteredIncrementalEpochMaterializerViolation(
                "registration-disjoint selector closure is malformed"
            )
        for value in (
            *self.supporting_acquisition_ids,
            *self.new_child_row_binding_ids,
        ):
            _cid(value, "synthetic selector member")
        frontier_id = _content_id(
            "synthetic_frontier",
            {
                "schema": (
                    "acfqp.v072_registration_disjoint_"
                    "incremental_frontier.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "round_index": self.round_index,
                "prior_epoch_id": self.prior_epoch_id,
                "predecessor_frontier_id": self.predecessor_frontier_id,
                "supporting_acquisition_ids": list(
                    self.supporting_acquisition_ids
                ),
                "promotion_parent_acquisition_id": (
                    self.promotion_parent_acquisition_id
                ),
                "promotion_row_binding_id": self.promotion_row_binding_id,
                "new_child_row_binding_ids": list(
                    self.new_child_row_binding_ids
                ),
                "independently_verified": True,
                "caller_rows_or_status_accepted": False,
            },
        )
        object.__setattr__(self, "_frontier_id", frontier_id)
        object.__setattr__(
            self,
            "_closure_id",
            _content_id(
                "synthetic_selector",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_"
                        "selector_closure.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "frontier_id": frontier_id,
                    "independent_attestation_bound": True,
                },
            ),
        )

    @property
    def frontier_id(self) -> str:
        return self._frontier_id

    @property
    def closure_id(self) -> str:
        return self._closure_id


@dataclass(frozen=True, slots=True)
class RegistrationDisjointIncrementalWorkV1:
    acquisition_calls: int
    independent_replay_calls: int
    promotion_count: int
    new_child_count: int
    producer_draws: int
    independent_replay_draws: int
    total_observer_draws: int
    historical_acquisition_count: int
    active_physical_row_count: int
    superseded_historical_version_count: int
    closure_builds: int = 1
    closure_verifications: int = 1
    projection_calls: int = 0
    model_pair_builds: int = 1
    model_pair_verifications: int = 1
    caller_rows_status_counts_callbacks: int = 0
    registered_target_accesses: int = 0
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if any(
            type(getattr(self, name)) is not int
            or getattr(self, name) < 0
            for name in self.__dataclass_fields__
            if name != "_work_id"
        ):
            raise V072RegisteredIncrementalEpochMaterializerViolation(
                "registration-disjoint materializer work is malformed"
            )
        if (
            self.acquisition_calls
            != self.promotion_count + self.new_child_count
            or self.independent_replay_calls != self.acquisition_calls
            or self.independent_replay_draws != self.producer_draws
            or self.total_observer_draws
            != self.producer_draws + self.independent_replay_draws
            or self.superseded_historical_version_count
            != (
                self.historical_acquisition_count
                - self.active_physical_row_count
            )
            or self.projection_calls != self.active_physical_row_count
            or self.closure_builds != 1
            or self.closure_verifications != 1
            or self.model_pair_builds != 1
            or self.model_pair_verifications != 1
            or self.caller_rows_status_counts_callbacks != 0
            or self.registered_target_accesses != 0
        ):
            raise V072RegisteredIncrementalEpochMaterializerViolation(
                "registration-disjoint materializer work does not reconcile"
            )
        object.__setattr__(
            self,
            "_work_id",
            _content_id("synthetic_work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_incremental_work.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
                if name != "_work_id"
            },
        }

    @property
    def work_id(self) -> str:
        return self._work_id


_SYNTHETIC_EPOCH_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegistrationDisjointIncrementalEpochV1:
    _minting_capability: object
    round_index: int
    predecessor_epoch_id: str | None
    predecessor_frontier_id: str | None
    frontier_id: str | None
    selector_supporting_acquisition_ids: tuple[str, ...]
    acquisition_history: tuple[
        RegistrationDisjointIncrementalAcquisitionV1, ...
    ]
    active_acquisition_ids: tuple[str, ...]
    new_acquisition_ids: tuple[str, ...]
    work: RegistrationDisjointIncrementalWorkV1 | None
    _closure_id: str = field(init=False, repr=False)
    _closure_verification_id: str = field(init=False, repr=False)
    _model_pair_id: str = field(init=False, repr=False)
    _model_verification_id: str = field(init=False, repr=False)
    _epoch_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.predecessor_epoch_id,
            self.predecessor_frontier_id,
            self.frontier_id,
        ):
            if value is not None:
                _cid(value, "synthetic epoch lineage")
        history_ids = tuple(
            item.acquisition_id for item in self.acquisition_history
        )
        by_id = {
            item.acquisition_id: item for item in self.acquisition_history
        }
        latest_by_row: dict[
            str, RegistrationDisjointIncrementalAcquisitionV1
        ] = {}
        for item in self.acquisition_history:
            previous = latest_by_row.get(item.row_binding_id)
            if (
                previous is not None
                and previous.round_index == item.round_index
            ):
                raise V072RegisteredIncrementalEpochMaterializerViolation(
                    "synthetic epoch replaces a same-round physical row"
                )
            if (
                previous is None
                or item.round_index > previous.round_index
            ):
                latest_by_row[item.row_binding_id] = item
        expected_active = tuple(
            sorted(item.acquisition_id for item in latest_by_row.values())
        )
        if (
            self._minting_capability is not _SYNTHETIC_EPOCH_SENTINEL
            or self.round_index not in (0, 1, 2)
            or history_ids != tuple(sorted(set(history_ids)))
            or not history_ids
            or self.active_acquisition_ids != expected_active
            or self.new_acquisition_ids
            != tuple(sorted(set(self.new_acquisition_ids)))
            or not set(self.new_acquisition_ids).issubset(history_ids)
            or self.selector_supporting_acquisition_ids
            != tuple(
                sorted(set(self.selector_supporting_acquisition_ids))
            )
            or (
                self.round_index == 0
                and any(
                    (
                        self.predecessor_epoch_id is not None,
                        self.predecessor_frontier_id is not None,
                        self.frontier_id is not None,
                        self.selector_supporting_acquisition_ids,
                        self.new_acquisition_ids != history_ids,
                        self.work is not None,
                    )
                )
            )
            or (
                self.round_index > 0
                and (
                    self.predecessor_epoch_id is None
                    or self.frontier_id is None
                    or not self.selector_supporting_acquisition_ids
                    or not self.new_acquisition_ids
                    or type(self.work)
                    is not RegistrationDisjointIncrementalWorkV1
                )
            )
            or any(
                acquisition_id not in by_id
                for acquisition_id in self.active_acquisition_ids
            )
        ):
            raise V072RegisteredIncrementalEpochMaterializerViolation(
                "registration-disjoint immutable epoch is malformed"
            )
        closure_id = _content_id(
            "synthetic_closure",
            {
                "schema": (
                    "acfqp.v072_registration_disjoint_incremental_"
                    "active_closure.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "active_acquisition_ids": list(
                    self.active_acquisition_ids
                ),
                "latest_physical_row_only": True,
                "history_retained_elsewhere": True,
            },
        )
        object.__setattr__(self, "_closure_id", closure_id)
        closure_verification_id = _content_id(
            "synthetic_closure_verification",
            {
                "schema": (
                    "acfqp.v072_registration_disjoint_incremental_"
                    "active_closure_verification.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "closure_id": closure_id,
                "verification_result": "VALID_COMPLETE_ACTIVE_CLOSURE",
            },
        )
        object.__setattr__(
            self,
            "_closure_verification_id",
            closure_verification_id,
        )
        model_id = _content_id(
            "synthetic_model",
            {
                "schema": (
                    "acfqp.v072_registration_disjoint_incremental_"
                    "model_pair.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "closure_id": closure_id,
                "closure_verification_id": closure_verification_id,
                "direct_and_quotient_built": True,
            },
        )
        object.__setattr__(self, "_model_pair_id", model_id)
        object.__setattr__(
            self,
            "_model_verification_id",
            _content_id(
                "synthetic_model_verification",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_incremental_"
                        "model_verification.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "model_pair_id": model_id,
                    "verification_result": "VALID",
                },
            ),
        )
        object.__setattr__(
            self,
            "_epoch_id",
            _content_id("synthetic_epoch", self._payload()),
        )

    @property
    def closure_id(self) -> str:
        return self._closure_id

    @property
    def closure_verification_id(self) -> str:
        return self._closure_verification_id

    @property
    def model_pair_id(self) -> str:
        return self._model_pair_id

    @property
    def model_verification_id(self) -> str:
        return self._model_verification_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_incremental_epoch.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "round_index": self.round_index,
            "predecessor_epoch_id": self.predecessor_epoch_id,
            "predecessor_frontier_id": self.predecessor_frontier_id,
            "frontier_id": self.frontier_id,
            "selector_supporting_acquisition_ids": list(
                self.selector_supporting_acquisition_ids
            ),
            "acquisition_history_ids": [
                item.acquisition_id for item in self.acquisition_history
            ],
            "replay_history_ids": [
                item.replay_id for item in self.acquisition_history
            ],
            "active_acquisition_ids": list(self.active_acquisition_ids),
            "new_acquisition_ids": list(self.new_acquisition_ids),
            "closure_id": self.closure_id,
            "closure_verification_id": self.closure_verification_id,
            "model_pair_id": self.model_pair_id,
            "model_verification_id": self.model_verification_id,
            "work_id": None if self.work is None else self.work.work_id,
            "immutable": True,
            "registered_target_accesses": 0,
        }

    @property
    def epoch_id(self) -> str:
        return self._epoch_id


def freeze_registration_disjoint_cold_epoch_v1(
    *,
    cold_acquisitions: tuple[
        RegistrationDisjointIncrementalAcquisitionV1, ...
    ],
) -> RegistrationDisjointIncrementalEpochV1:
    if (
        type(cold_acquisitions) is not tuple
        or not cold_acquisitions
        or any(
            type(item) is not RegistrationDisjointIncrementalAcquisitionV1
            or item.kind is not RegistrationDisjointAcquisitionKindV1.COLD
            for item in cold_acquisitions
        )
    ):
        raise V072RegisteredIncrementalEpochMaterializerViolation(
            "synthetic cold epoch requires only cold acquisitions"
        )
    ordered = tuple(
        sorted(cold_acquisitions, key=lambda item: item.acquisition_id)
    )
    ids = tuple(item.acquisition_id for item in ordered)
    return RegistrationDisjointIncrementalEpochV1(
        _SYNTHETIC_EPOCH_SENTINEL,
        0,
        None,
        None,
        None,
        (),
        ordered,
        ids,
        ids,
        None,
    )


def materialize_registration_disjoint_incremental_epoch_v1(
    *,
    prior_epoch: RegistrationDisjointIncrementalEpochV1,
    selector_closure: RegistrationDisjointSelectorClosureV1,
) -> RegistrationDisjointIncrementalEpochV1:
    """Mechanically materialize every row in one verified synthetic frontier."""

    if (
        type(prior_epoch) is not RegistrationDisjointIncrementalEpochV1
        or type(selector_closure)
        is not RegistrationDisjointSelectorClosureV1
        or prior_epoch.round_index >= MAX_INCREMENTAL_ROUNDS
        or selector_closure.round_index != prior_epoch.round_index + 1
        or selector_closure.prior_epoch_id != prior_epoch.epoch_id
        or selector_closure.supporting_acquisition_ids
        != tuple(
            item.acquisition_id for item in prior_epoch.acquisition_history
        )
        or (
            prior_epoch.round_index == 0
            and selector_closure.predecessor_frontier_id is not None
        )
        or (
            prior_epoch.round_index == 1
            and (
                selector_closure.predecessor_frontier_id
                != prior_epoch.frontier_id
                or not set(
                    prior_epoch.selector_supporting_acquisition_ids
                )
                < set(selector_closure.supporting_acquisition_ids)
            )
        )
    ):
        raise V072RegisteredIncrementalEpochMaterializerViolation(
            "synthetic selector lineage is stale or not a strict extension"
        )
    by_id = {
        item.acquisition_id: item for item in prior_epoch.acquisition_history
    }
    parent = by_id.get(
        selector_closure.promotion_parent_acquisition_id
    )
    if (
        parent is None
        or parent.acquisition_id not in prior_epoch.active_acquisition_ids
        or parent.row_binding_id
        != selector_closure.promotion_row_binding_id
        or parent.round_index != prior_epoch.round_index
        or selector_closure.promotion_row_binding_id
        in selector_closure.new_child_row_binding_ids
    ):
        raise V072RegisteredIncrementalEpochMaterializerViolation(
            "synthetic promotion does not extend the latest physical row"
        )
    active_rows = {
        by_id[item].row_binding_id
        for item in prior_epoch.active_acquisition_ids
    }
    if set(selector_closure.new_child_row_binding_ids) & active_rows:
        raise V072RegisteredIncrementalEpochMaterializerViolation(
            "synthetic new-child inventory replaces an active row"
        )
    promotion = RegistrationDisjointIncrementalAcquisitionV1(
        selector_closure.promotion_row_binding_id,
        selector_closure.round_index,
        RegistrationDisjointAcquisitionKindV1.PROMOTION,
        selector_closure.promotion_parent_acquisition_id,
        selector_closure.frontier_id,
    )
    new_children = tuple(
        RegistrationDisjointIncrementalAcquisitionV1(
            row_id,
            selector_closure.round_index,
            RegistrationDisjointAcquisitionKindV1.NEW_CHILD,
            None,
            selector_closure.frontier_id,
        )
        for row_id in selector_closure.new_child_row_binding_ids
    )
    new_values = tuple(
        sorted(
            (promotion, *new_children),
            key=lambda item: item.acquisition_id,
        )
    )
    history = tuple(
        sorted(
            (*prior_epoch.acquisition_history, *new_values),
            key=lambda item: item.acquisition_id,
        )
    )
    latest_by_row: dict[
        str, RegistrationDisjointIncrementalAcquisitionV1
    ] = {}
    for item in history:
        previous = latest_by_row.get(item.row_binding_id)
        if (
            previous is None
            or item.round_index > previous.round_index
        ):
            latest_by_row[item.row_binding_id] = item
    active_ids = tuple(
        sorted(item.acquisition_id for item in latest_by_row.values())
    )
    producer_draws = sum(item.producer_draws for item in new_values)
    work = RegistrationDisjointIncrementalWorkV1(
        acquisition_calls=len(new_values),
        independent_replay_calls=len(new_values),
        promotion_count=1,
        new_child_count=len(new_children),
        producer_draws=producer_draws,
        independent_replay_draws=producer_draws,
        total_observer_draws=2 * producer_draws,
        historical_acquisition_count=len(history),
        active_physical_row_count=len(active_ids),
        superseded_historical_version_count=(
            len(history) - len(active_ids)
        ),
        projection_calls=len(active_ids),
    )
    return RegistrationDisjointIncrementalEpochV1(
        _SYNTHETIC_EPOCH_SENTINEL,
        selector_closure.round_index,
        prior_epoch.epoch_id,
        selector_closure.predecessor_frontier_id,
        selector_closure.frontier_id,
        selector_closure.supporting_acquisition_ids,
        history,
        active_ids,
        tuple(item.acquisition_id for item in new_values),
        work,
    )


__all__ = [
    "MAX_INCREMENTAL_ROUNDS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "PriorRegisteredModelEpochV1",
    "RegisteredIncrementalEpochAccessAuditV1",
    "RegisteredIncrementalEpochMaterializerLockedV1",
    "RegisteredIncrementalH2ModelEpochV1",
    "RegistrationDisjointAcquisitionKindV1",
    "RegistrationDisjointIncrementalAcquisitionV1",
    "RegistrationDisjointIncrementalEpochV1",
    "RegistrationDisjointIncrementalWorkV1",
    "RegistrationDisjointSelectorClosureV1",
    "SCHEMA_VERSION",
    "V072RegisteredIncrementalEpochMaterializerViolation",
    "ZERO_ACCESS_AUDIT",
    "freeze_registration_disjoint_cold_epoch_v1",
    "materialize_registered_incremental_h2_model_epoch_v1",
    "materialize_registration_disjoint_incremental_epoch_v1",
]
