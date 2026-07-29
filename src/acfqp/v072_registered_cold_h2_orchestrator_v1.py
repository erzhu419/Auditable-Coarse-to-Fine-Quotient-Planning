"""Registered observation-to-cold-model orchestration for V0-072.

This module is the production bridge from one exact registered occurrence
identity to a complete observation-only cold H=2 model epoch.  It owns all
row selection needed for the complete cold closure, opens the target streams
through the registered accumulator, independently replays every row, freezes
and independently verifies the closure, projects confidence rows, and builds
and independently verifies the direct/quotient model pair.

The public entry point accepts no observation, transition law, seed,
probability, count, row inventory, support set, projection, or model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import heldout_graph_transition_observer_v2 as observer
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
from acfqp import (
    v072_registered_target_confidence_accumulator_v1 as accumulator,
)
from acfqp import (
    v072_registered_target_confidence_independent_verifier_v1
    as confidence_independent,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_cold_h2_orchestrator_v1"
REGISTERED_COLD_ORCHESTRATOR_ENABLED = True
REGISTERED_COLD_ORCHESTRATOR_STATUS = (
    "ENABLED_ONLY_BY_EXACT_REMOTE_MAIN_AUTHORITY_CHAIN"
)

DOMAIN_TAGS = {
    "access": "acfqp:v072-registered-cold-h2-orchestrator-access:v1",
    "epoch": "acfqp:v072-registered-cold-h2-model-epoch:v1",
}


class V072RegisteredColdH2OrchestratorInvariantViolation(ValueError):
    """An occurrence, public inventory, lineage, or epoch invariant failed."""


class RegisteredColdH2OrchestratorLockedV1(RuntimeError):
    """The exact production authority chain was absent or stale."""

    def __init__(
        self,
        message: str,
        *,
        access_audit: "RegisteredColdH2OrchestratorAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.access_audit = access_audit


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072RegisteredColdH2OrchestratorInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredColdH2OrchestratorInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class RegisteredColdH2OrchestratorAccessAuditV1:
    authority_chain_verifications: int = 0
    public_adapter_builds: int = 0
    public_catalogue_builds: int = 0
    acquisition_calls: int = 0
    independent_confidence_replay_calls: int = 0
    producer_stream_opens: int = 0
    producer_draw_calls: int = 0
    replay_stream_opens: int = 0
    replay_draw_calls: int = 0
    unique_online_sample_evidence_draws: int = 0
    total_observer_draw_calls: int = 0
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
            raise V072RegisteredColdH2OrchestratorInvariantViolation(
                "cold orchestrator access counters are malformed"
            )
        if (
            self.unique_online_sample_evidence_draws
            != self.producer_draw_calls
            or self.total_observer_draw_calls
            != self.producer_draw_calls + self.replay_draw_calls
        ):
            raise V072RegisteredColdH2OrchestratorInvariantViolation(
                "sample evidence and observer replay work do not reconcile"
            )

    @property
    def target_access_started(self) -> bool:
        return any(
            getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "authority_chain_verifications"
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_cold_h2_"
                "orchestrator_access_audit.v1"
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


ZERO_ACCESS_AUDIT = RegisteredColdH2OrchestratorAccessAuditV1()


def _require_exact_preobserver_identity_v1(
    *,
    authority_chain: Any,
    anchor: Any,
    occurrence_plan: Any,
    context: Any,
) -> tuple[
    consumer.RegisteredCampaignAuthorityChainV1,
    final_authority.V072RemoteMainAnchorV1,
    consumer.RegisteredOccurrenceExecutionPlanV1,
    prereg.HeldoutPublicGraphContextV2,
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
    ):
        raise RegisteredColdH2OrchestratorLockedV1(
            "registered cold H2 orchestration requires one exact "
            "adaptive occurrence authority chain",
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
        raise RegisteredColdH2OrchestratorLockedV1(
            "registered cold H2 authority replay failed before target access",
            access_audit=ZERO_ACCESS_AUDIT,
        ) from error
    return authority_chain, anchor, occurrence_plan, context


def _ordered_public_actions_v1(
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: observer.HeldoutLegalActionCatalogueV2,
) -> tuple[tuple[int, int, int], ...]:
    if (
        type(catalogue) is not observer.HeldoutLegalActionCatalogueV2
        or catalogue.context_id != context.context_id
        or catalogue.state.failure
    ):
        raise V072RegisteredColdH2OrchestratorInvariantViolation(
            "cold acquisition requires one complete active public catalogue"
        )
    expected = observer.legal_action_catalogue_v2(
        context,
        catalogue.state,
        catalogue.remaining_horizon,
    )
    if catalogue.to_document() != expected.to_document():
        raise V072RegisteredColdH2OrchestratorInvariantViolation(
            "cold public catalogue omits or adds a legal action"
        )
    return tuple(
        item[1]
        for item in sorted(
            (
                (
                    observer.observation_row_binding_v2(
                        context,
                        catalogue,
                        action,
                    ).row_binding_id,
                    action,
                )
                for action in catalogue.actions
            ),
            key=lambda item: item[0],
        )
    )


def _public_child_catalogues_from_root_evidence_v1(
    *,
    adapter: public_adapter.HeldoutPublicGraphColdClosureAdapterV1,
    root_row_evidence: tuple[cold.ColdRowEvidenceV1, ...],
) -> tuple[observer.HeldoutLegalActionCatalogueV2, ...]:
    """Derive the complete H1 catalogue set from discovery support only."""

    if (
        type(adapter)
        is not public_adapter.HeldoutPublicGraphColdClosureAdapterV1
        or type(root_row_evidence) is not tuple
        or not root_row_evidence
        or any(type(item) is not cold.ColdRowEvidenceV1
               for item in root_row_evidence)
    ):
        raise V072RegisteredColdH2OrchestratorInvariantViolation(
            "child discovery requires exact adapter and root evidence"
        )
    states: dict[str, tuple[cold.ColdPublicStateV1, Any]] = {}
    for row in root_row_evidence:
        if (
            row.context_id != adapter.context_id
            or row.remaining_horizon != cold.HORIZON
        ):
            raise V072RegisteredColdH2OrchestratorInvariantViolation(
                "root evidence was transplanted across context or horizon"
            )
        for descriptor in row.discovery_support:
            if not descriptor.active_nonterminal:
                continue
            state = descriptor.successor_state
            assert state is not None
            canonical = adapter.canonical_state_v1(state)
            document = dict(canonical.document)
            ranks = document.get("ranks")
            failure = document.get("failure")
            if (
                document.get("context_id") != adapter.context_id
                or document.get("remaining_horizon") != 1
                or type(ranks) is not list
                or len(ranks) != adapter.context.topology.vertex_count
                or any(type(rank) is not int for rank in ranks)
                or failure is not False
            ):
                raise V072RegisteredColdH2OrchestratorInvariantViolation(
                    "discovery child lacks exact active public H1 semantics"
                )
            public_state = observer.HeldoutSymbolicGraphStateV2(
                tuple(ranks),
                failure,
            )
            prior = states.setdefault(
                canonical.semantic_state_id,
                (canonical, public_state),
            )
            if prior[0] != canonical or prior[1] != public_state:
                raise V072RegisteredColdH2OrchestratorInvariantViolation(
                    "one public child identity has conflicting semantics"
                )
    result = tuple(
        observer.legal_action_catalogue_v2(
            adapter.context,
            public_state,
            1,
        )
        for _canonical, public_state in sorted(
            states.values(),
            key=lambda item: item[0].state_record_id,
        )
    )
    for catalogue in result:
        adapter.adapt_public_legal_action_catalogue_v1(catalogue)
    return result


def _acquire_and_replay_row_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: observer.HeldoutLegalActionCatalogueV2,
    action: tuple[int, int, int],
    arm: str,
) -> tuple[
    accumulator.RegisteredTargetRowAcquisitionV1,
    confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
]:
    purpose = accumulator.RegisteredTargetAcquisitionPurposeV1.COLD_INITIAL
    acquisition = accumulator.acquire_registered_target_row_v1(
        authority_chain=authority_chain,
        anchor=anchor,
        context=context,
        catalogue=catalogue,
        action=action,
        arm=arm,
        purpose=purpose,
        checkpoint=purpose.required_checkpoint,
    )
    replay = (
        confidence_independent
        .verify_registered_target_confidence_independently_v1(
            authority_chain=authority_chain,
            anchor=anchor,
            acquisition=acquisition,
        )
    )
    return acquisition, replay


_EPOCH_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ModelEpochV1:
    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1
    context: prereg.HeldoutPublicGraphContextV2
    adapter: public_adapter.HeldoutPublicGraphColdClosureAdapterV1
    acquisitions: tuple[
        accumulator.RegisteredTargetRowAcquisitionV1, ...
    ]
    confidence_replays: tuple[
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
    access_audit: RegisteredColdH2OrchestratorAccessAuditV1
    _epoch_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authority_chain_id, "cold epoch authority chain"),
            (self.anchor_id, "cold epoch anchor"),
        ):
            _cid(value, label)
        row_ids = tuple(
            sorted(item.row_evidence.row_evidence_id
                   for item in self.confidence_replays)
        )
        projection_row_ids = tuple(
            sorted(item.row_evidence_id for item in self.row_projections)
        )
        if (
            self._minting_capability is not _EPOCH_MINTING_SENTINEL
            or type(self.occurrence_plan)
            is not consumer.RegisteredOccurrenceExecutionPlanV1
            or self.occurrence_plan.chain_id != self.authority_chain_id
            or type(self.context) is not prereg.HeldoutPublicGraphContextV2
            or self.occurrence_plan.template.context_id
            != self.context.context_id
            or type(self.adapter)
            is not public_adapter.HeldoutPublicGraphColdClosureAdapterV1
            or self.adapter.context_id != self.context.context_id
            or type(self.acquisitions) is not tuple
            or not self.acquisitions
            or type(self.confidence_replays) is not tuple
            or len(self.confidence_replays) != len(self.acquisitions)
            or tuple(item.acquisition for item in self.confidence_replays)
            != self.acquisitions
            or type(self.closure_bundle)
            is not cold.V072ColdH2ClosureBundleV1
            or self.closure_bundle.context_id != self.context.context_id
            or self.closure_bundle.arm != self.occurrence_plan.template.arm
            or tuple(
                sorted(item.row_evidence_id
                       for item in self.closure_bundle.all_rows)
            ) != row_ids
            or type(self.closure_verification)
            is not cold_independent.V072ColdH2IndependentVerificationV1
            or self.closure_verification.closure_id
            != self.closure_bundle.closure_id
            or self.closure_verification.context_id
            != self.context.context_id
            or type(self.row_projections) is not tuple
            or projection_row_ids != row_ids
            or type(self.model_pair)
            is not models.RegisteredColdH2ModelPairV1
            or self.model_pair.model_pair_id
            != self.model_replay_attestation.model_pair_id
            or self.model_pair.closure_bundle != self.closure_bundle
            or self.model_replay_attestation.remote_main_anchor_id
            != self.anchor_id
            or self.model_replay_attestation.context_id
            != self.context.context_id
            or self.model_replay_attestation.closure_id
            != self.closure_bundle.closure_id
            or type(self.access_audit)
            is not RegisteredColdH2OrchestratorAccessAuditV1
            or self.access_audit.acquisition_calls != len(self.acquisitions)
            or self.access_audit.independent_confidence_replay_calls
            != len(self.confidence_replays)
            or self.access_audit.projection_calls
            != len(self.row_projections)
        ):
            raise V072RegisteredColdH2OrchestratorInvariantViolation(
                "registered cold model epoch does not reconcile"
            )
        object.__setattr__(
            self,
            "_epoch_id",
            _content_id("epoch", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_cold_h2_model_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "occurrence_id": self.occurrence_plan.occurrence_id,
            "context_id": self.context.context_id,
            "arm": self.occurrence_plan.template.arm,
            "adapter_id": self.adapter.adapter_id,
            "acquisition_ids": [
                item.acquisition_id for item in self.acquisitions
            ],
            "confidence_replay_bundle_ids": [
                item.bundle_id for item in self.confidence_replays
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
            "complete_discovery_closed_h2_inventory": True,
            "source_prior_used_in_confidence_or_model": False,
            "caller_evidence_accepted": False,
        }

    @property
    def epoch_id(self) -> str:
        return self._epoch_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_plan": {
                "occurrence_id": self.occurrence_plan.occurrence_id,
                "template_id": self.occurrence_plan.template.template_id,
            },
            "context": self.context.to_document(),
            "adapter": self.adapter.to_document(),
            "acquisitions": [
                item.to_document() for item in self.acquisitions
            ],
            "confidence_replays": [
                item.to_document() for item in self.confidence_replays
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


def build_registered_cold_h2_model_epoch_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
) -> RegisteredColdH2ModelEpochV1:
    """Acquire and independently replay one complete registered cold epoch."""

    (
        authority_chain,
        anchor,
        occurrence_plan,
        context,
    ) = _require_exact_preobserver_identity_v1(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=occurrence_plan,
        context=context,
    )
    adapter = public_adapter.registered_heldout_public_graph_adapter_v1(
        context
    )
    arm = occurrence_plan.template.arm
    acquisition_values: list[
        accumulator.RegisteredTargetRowAcquisitionV1
    ] = []
    replay_values: list[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1
    ] = []

    root_catalogue = adapter.public_root_catalogue
    for action in _ordered_public_actions_v1(context, root_catalogue):
        acquisition, replay = _acquire_and_replay_row_v1(
            authority_chain=authority_chain,
            anchor=anchor,
            context=context,
            catalogue=root_catalogue,
            action=action,
            arm=arm,
        )
        acquisition_values.append(acquisition)
        replay_values.append(replay)

    child_catalogues = _public_child_catalogues_from_root_evidence_v1(
        adapter=adapter,
        root_row_evidence=tuple(
            item.row_evidence for item in replay_values
        ),
    )
    for catalogue in child_catalogues:
        for action in _ordered_public_actions_v1(context, catalogue):
            acquisition, replay = _acquire_and_replay_row_v1(
                authority_chain=authority_chain,
                anchor=anchor,
                context=context,
                catalogue=catalogue,
                action=action,
                arm=arm,
            )
            acquisition_values.append(acquisition)
            replay_values.append(replay)

    paired = tuple(
        sorted(
            zip(acquisition_values, replay_values, strict=True),
            key=lambda item: item[0].acquisition_id,
        )
    )
    acquisitions = tuple(item[0] for item in paired)
    replays = tuple(item[1] for item in paired)
    row_evidence = tuple(item.row_evidence for item in replays)
    cap_evidence = (
        cold.registered_confirmatory_cold_h2_cap_registry_v1()
        .evidence_for_context(context.context_id)
    )
    closure_bundle = cold.freeze_v072_cold_h2_closure_v1(
        public_graph=adapter,
        row_evidence=row_evidence,
        logical_occurrence_id=occurrence_plan.occurrence_id,
        arm=arm,
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
                for item in replays
            ),
            key=lambda item: item.projection_id,
        )
    )
    relational_context = models.registered_cold_h2_relational_context_v1(
        context
    )
    model_pair = models.build_registered_target_cold_h2_models_v1(
        anchor=anchor,
        closure_bundle=closure_bundle,
        row_projections=projections,
        relational_context=relational_context,
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
        1 + int(item.transcript.discovery_work is not None)
        for item in acquisitions
    )
    producer_draws = sum(
        len(item.transcript.entries) for item in acquisitions
    )
    replay_stream_opens = sum(
        item.attestation.replayed_stream_opens for item in replays
    )
    replay_draws = sum(
        item.attestation.replayed_draw_calls for item in replays
    )
    access_audit = RegisteredColdH2OrchestratorAccessAuditV1(
        authority_chain_verifications=1,
        public_adapter_builds=1,
        public_catalogue_builds=1 + len(child_catalogues),
        acquisition_calls=len(acquisitions),
        independent_confidence_replay_calls=len(replays),
        producer_stream_opens=producer_stream_opens,
        producer_draw_calls=producer_draws,
        replay_stream_opens=replay_stream_opens,
        replay_draw_calls=replay_draws,
        unique_online_sample_evidence_draws=producer_draws,
        total_observer_draw_calls=producer_draws + replay_draws,
        closure_builds=1,
        closure_independent_verifications=1,
        projection_calls=len(projections),
        model_pair_builds=1,
        model_pair_independent_verifications=1,
    )
    return RegisteredColdH2ModelEpochV1(
        _EPOCH_MINTING_SENTINEL,
        authority_chain.chain_id,
        anchor.anchor_id,
        occurrence_plan,
        context,
        adapter,
        acquisitions,
        replays,
        closure_bundle,
        closure_verification,
        projections,
        model_pair,
        model_replay_attestation,
        access_audit,
    )


__all__ = [
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_COLD_ORCHESTRATOR_ENABLED",
    "REGISTERED_COLD_ORCHESTRATOR_STATUS",
    "RegisteredColdH2ModelEpochV1",
    "RegisteredColdH2OrchestratorAccessAuditV1",
    "RegisteredColdH2OrchestratorLockedV1",
    "SCHEMA_VERSION",
    "V072RegisteredColdH2OrchestratorInvariantViolation",
    "ZERO_ACCESS_AUDIT",
    "build_registered_cold_h2_model_epoch_v1",
]
