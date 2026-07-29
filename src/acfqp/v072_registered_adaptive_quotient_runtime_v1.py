"""Fail-closed registered adaptive-quotient occurrence runtime for V0-072.

The production entry point accepts only the exact campaign authority chain,
its identical remote-main anchor object, one consumer-owned occurrence plan,
and one registered public context.  It accepts no observation, transcript,
law, seed, probability, count, status, terminal, planner result, or callback.

The production path builds one complete cold H=2 epoch, solves the quotient
model with the exact lazy solver and its independent proof replay, and, only
after a failed proof, invokes the registered failed-frontier selector and
immutable incremental epoch materializer.  It performs at most two fresh
no-replacement local rounds.  A separately implemented runtime verifier
replays every model/proof/selector dependency without target access before a
verified result wrapper can be exposed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import exact_lazy_h2_robust_planner_v1 as lazy
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_exact_lazy_planner_component_v1 as planner
from acfqp import v072_cold_h2_model_builders_v1 as models
from acfqp import v072_registered_cold_h2_orchestrator_v1 as cold_runtime
from acfqp import (
    v072_registered_incremental_epoch_materializer_v1 as incremental,
)
from acfqp import v072_registered_target_selector_v1 as selector


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_adaptive_quotient_occurrence_runtime_v1"
ADAPTIVE_ARMS = tuple(prereg.ARM_ORDER[:-1])
MAX_LOCAL_ROUNDS = prereg.MAX_ROUNDS
REGISTERED_RUNTIME_ENABLED = True
REGISTERED_RUNTIME_STATUS = (
    "ENABLED_WITH_INDEPENDENT_RUNTIME_REPLAY_AND_TYPED_TERMINAL_ADAPTER_GAP"
)

EVALUATOR_TERMINAL_MINT_BLOCKER = (
    "REGISTERED_FIXED_CONCRETIZER_OPERATIONAL_POLICY_SCHEMA_NOT_INTEGRATED"
)
INCREMENTAL_MODEL_EPOCH_BLOCKER = None
FIXED_CONCRETIZER_OPERATIONAL_POLICY_SCHEMA_BLOCKER = (
    EVALUATOR_TERMINAL_MINT_BLOCKER
)


class V072RegisteredAdaptiveRuntimeInvariantViolation(ValueError):
    """An occurrence, transition, lineage, or work invariant failed."""


class RegisteredAdaptiveRuntimeLockedV1(RuntimeError):
    """The exact production anchor or occurrence identity is unavailable."""

    def __init__(
        self,
        message: str,
        *,
        access_audit: "RegisteredAdaptiveAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.access_audit = access_audit


class RegisteredAdaptiveDependencyBlockedV1(RuntimeError):
    """The registered runtime stopped at one frozen typed dependency."""

    def __init__(
        self,
        message: str,
        *,
        occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
        dependency_protocol: "RegisteredAdaptiveDependencyProtocolV1",
        access_audit: "RegisteredAdaptiveAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.occurrence_plan = occurrence_plan
        self.dependency_protocol = dependency_protocol
        self.access_audit = access_audit


DOMAIN_TAGS = {
    "access": "acfqp:v072-registered-adaptive-access-audit:v1",
    "dependency": (
        "acfqp:v072-registered-adaptive-dependency-protocol:v1"
    ),
    "proposal": (
        "acfqp:v072-registration-disjoint-adaptive-proposal-order:v1"
    ),
    "acquisition": (
        "acfqp:v072-registration-disjoint-adaptive-acquisition:v1"
    ),
    "frontier_causal": (
        "acfqp:v072-registration-disjoint-adaptive-causal-evidence:v1"
    ),
    "frontier": (
        "acfqp:v072-registration-disjoint-adaptive-frontier:v1"
    ),
    "round": (
        "acfqp:v072-registration-disjoint-adaptive-local-round:v1"
    ),
    "closure": (
        "acfqp:v072-registration-disjoint-adaptive-observed-closure:v1"
    ),
    "closure_verification": (
        "acfqp:v072-registration-disjoint-adaptive-"
        "observed-closure-verification:v1"
    ),
    "model": "acfqp:v072-registration-disjoint-adaptive-model-pair:v1",
    "model_verification": (
        "acfqp:v072-registration-disjoint-adaptive-model-verification:v1"
    ),
    "epoch": "acfqp:v072-registration-disjoint-adaptive-model-epoch:v1",
    "planner": (
        "acfqp:v072-registration-disjoint-adaptive-planner-result:v1"
    ),
    "proof": (
        "acfqp:v072-registration-disjoint-adaptive-planner-proof:v1"
    ),
    "policy": (
        "acfqp:v072-registration-disjoint-adaptive-selected-policy:v1"
    ),
    "audit": "acfqp:v072-registration-disjoint-adaptive-audit:v1",
    "work": "acfqp:v072-registration-disjoint-adaptive-work:v1",
    "certificate": (
        "acfqp:v072-registration-disjoint-adaptive-certificate:v1"
    ),
    "run": "acfqp:v072-registration-disjoint-adaptive-run:v1",
    "registered_concretizer_decision": (
        "acfqp:v072-registered-adaptive-concretizer-decision:v1"
    ),
    "registered_ground_decision": (
        "acfqp:v072-registered-adaptive-ground-policy-decision:v1"
    ),
    "registered_work": "acfqp:v072-registered-adaptive-occurrence-work:v1",
    "registered_certificate": (
        "acfqp:v072-registered-adaptive-plan-certificate:v1"
    ),
    "registered_result": (
        "acfqp:v072-registered-adaptive-occurrence-result:v1"
    ),
    "registered_verified_result": (
        "acfqp:v072-registered-adaptive-verified-runtime-result:v1"
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
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class RegisteredAdaptiveAccessAuditV1:
    anchor_checks: int = 0
    occurrence_identity_checks: int = 0
    authority_chain_verifications: int = 0
    observer_stream_opens: int = 0
    observer_draw_calls: int = 0
    accepted_observations: int = 0
    confidence_accumulator_calls: int = 0
    confidence_replay_calls: int = 0
    cold_closure_build_calls: int = 0
    cold_model_build_calls: int = 0
    cold_model_verification_calls: int = 0
    quotient_planner_calls: int = 0
    proof_verification_calls: int = 0
    frontier_freeze_calls: int = 0
    immutable_epoch_rebuild_calls: int = 0
    evaluator_terminal_mint_calls: int = 0

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0
            for value in (
                getattr(self, name)
                for name in self.__dataclass_fields__
            )
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registered adaptive access counters are malformed"
            )

    @property
    def observer_or_target_access_started(self) -> bool:
        return any(
            getattr(self, name)
            for name in self.__dataclass_fields__
            if name
            not in (
                "anchor_checks",
                "occurrence_identity_checks",
                "authority_chain_verifications",
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_adaptive_access_audit.v1",
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
            "observer_or_target_access_started": (
                self.observer_or_target_access_started
            ),
        }

    @property
    def audit_id(self) -> str:
        return _content_id("access", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


ZERO_ACCESS_AUDIT = RegisteredAdaptiveAccessAuditV1()


@dataclass(frozen=True, slots=True)
class RegisteredAdaptiveDependencyProtocolV1:
    """Frozen production dependencies; none can be caller-injected."""

    authority_chain_type: str = (
        "acfqp.v072_registered_campaign_consumer_v1."
        "RegisteredCampaignAuthorityChainV1"
    )
    authority_chain_verifier_entrypoint: str = (
        "acfqp.v072_registered_campaign_consumer_v1."
        "verify_registered_campaign_authority_chain_v1"
    )
    cold_model_epoch_type: str = (
        "acfqp.v072_registered_cold_h2_orchestrator_v1."
        "RegisteredColdH2ModelEpochV1"
    )
    cold_model_epoch_entrypoint: str = (
        "acfqp.v072_registered_cold_h2_orchestrator_v1."
        "build_registered_cold_h2_model_epoch_v1"
    )
    target_accumulator_type: str = (
        "acfqp.v072_registered_target_confidence_accumulator_v1."
        "RegisteredTargetRowAcquisitionV1"
    )
    target_accumulator_entrypoint: str = (
        "acfqp.v072_registered_target_confidence_accumulator_v1."
        "acquire_registered_target_row_v1"
    )
    target_confidence_replay_entrypoint: str = (
        "acfqp.v072_registered_target_confidence_"
        "independent_verifier_v1."
        "verify_registered_target_confidence_independently_v1"
    )
    frontier_type: str = (
        "acfqp.v072_registered_target_confidence_accumulator_v1."
        "RegisteredAcquisitionFrontierV1"
    )
    frontier_freeze_entrypoint: str = (
        "acfqp.v072_registered_target_confidence_accumulator_v1."
        "freeze_registered_acquisition_frontier_v1"
    )
    cold_closure_entrypoint: str = (
        "acfqp.v072_cold_h2_closure_v1."
        "freeze_v072_cold_h2_closure_v1"
    )
    cold_closure_verifier_entrypoint: str = (
        "acfqp.v072_cold_h2_closure_independent_verifier_v1."
        "verify_v072_cold_h2_closure_independently_v1"
    )
    confidence_projection_entrypoint: str = (
        "acfqp.v072_confidence_row_projection_v1."
        "project_registered_target_confidence_row_v1"
    )
    cold_model_builder_entrypoint: str = (
        "acfqp.v072_cold_h2_model_builders_v1."
        "build_registered_target_cold_h2_models_v1"
    )
    cold_model_verifier_entrypoint: str = (
        "acfqp.v072_cold_h2_model_builders_"
        "independent_verifier_v1."
        "verify_registered_cold_h2_model_pair_independently_v1"
    )
    frontier_selector_type: str = (
        "acfqp.v072_registered_target_selector_v1."
        "RegisteredSelectorClosureV1"
    )
    frontier_selector_entrypoint: str = (
        "acfqp.v072_registered_target_selector_v1."
        "prepare_registered_acquisition_frontier_v1"
    )
    frontier_selector_verifier_entrypoint: str = (
        "acfqp.v072_registered_target_selector_"
        "independent_verifier_v1."
        "verify_registered_selector_independently_v1"
    )
    incremental_model_epoch_type: str = (
        "acfqp.v072_registered_incremental_epoch_materializer_v1."
        "RegisteredIncrementalH2ModelEpochV1"
    )
    incremental_model_epoch_entrypoint: str = (
        "acfqp.v072_registered_incremental_epoch_materializer_v1."
        "materialize_registered_incremental_h2_model_epoch_v1"
    )
    incremental_model_epoch_verifier_type: str = (
        "acfqp.v072_registered_incremental_epoch_"
        "independent_verifier_v1."
        "RegisteredIncrementalEpochIndependentAttestationV1"
    )
    incremental_model_epoch_verifier_entrypoint: str = (
        "acfqp.v072_registered_incremental_epoch_"
        "independent_verifier_v1."
        "verify_registered_incremental_h2_model_epoch_independently_v1"
    )
    quotient_planner_entrypoint: str = (
        "acfqp.v072_exact_lazy_planner_component_v1."
        "solve_and_verify_v072_exact_lazy_h2_v1"
    )
    proof_verifier_entrypoint: str = (
        "acfqp.exact_lazy_h2_independent_verifier_v1."
        "verify_exact_lazy_h2_solve_result_v1"
    )
    evaluator_terminal_factory_entrypoint: str = (
        "acfqp.v072_registered_operational_terminal_authority_v1."
        "derive_registered_operational_terminal_authority_v1"
    )
    blockers: tuple[str, ...] = (
        EVALUATOR_TERMINAL_MINT_BLOCKER,
    )
    dependencies_available: bool = True

    def __post_init__(self) -> None:
        if (
            any(
                getattr(self, name) != definition.default
                for name, definition in self.__dataclass_fields__.items()
            )
            or self.dependencies_available is not True
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registered adaptive dependency protocol changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_adaptive_dependency_protocol.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                name: (
                    list(getattr(self, name))
                    if name == "blockers"
                    else getattr(self, name)
                )
                for name in self.__dataclass_fields__
            },
            "dependencies_available": True,
            "adaptive_planning_dependencies_available": True,
            "operational_terminal_adapter_available": False,
            "caller_callback_allowed": False,
            "caller_observations_allowed": False,
            "caller_law_seed_probability_count_status_allowed": False,
            "source_quantities_allowed_in_confidence_model_certificate":
                False,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("dependency", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


def inspect_registered_adaptive_dependency_protocol_v1(
) -> RegisteredAdaptiveDependencyProtocolV1:
    return RegisteredAdaptiveDependencyProtocolV1()


def validate_registered_adaptive_occurrence_identity_v1(
    *,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
) -> consumer.RegisteredOccurrenceExecutionPlanV1:
    """Validate the public schedule identity without authorizing target access."""

    contexts = prereg.registered_heldout_public_contexts_v2()
    if (
        type(occurrence_plan)
        is not consumer.RegisteredOccurrenceExecutionPlanV1
        or type(context) is not prereg.HeldoutPublicGraphContextV2
        or context not in contexts
        or type(occurrence_plan.template)
        is not consumer.RegisteredOccurrenceTemplateV1
        or occurrence_plan.template.context_id != context.context_id
        or occurrence_plan.template.context_key != context.context_key
        or occurrence_plan.template.arm not in ADAPTIVE_ARMS
        or occurrence_plan.template.route_kind
        is not consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT
        or occurrence_plan.template.maximum_adaptive_rounds
        != MAX_LOCAL_ROUNDS
    ):
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            "occurrence is stale, foreign, direct-only, or outside the "
            "four registered adaptive arms"
        )
    return occurrence_plan


class RegistrationDisjointAdaptiveProposalBasisV1(str, Enum):
    SOURCE_ARCHIVE = "SOURCE_ARCHIVE"
    NO_PRIOR = "NO_PRIOR"
    WRONG_SOURCE_ARCHIVE = "WRONG_SOURCE_ARCHIVE"
    OOD_TYPED_ABSTENTION = "OOD_TYPED_ABSTENTION"


_PROPOSAL_BASIS_BY_ARM = {
    "SOURCE_CONSENSUS_PRIOR": (
        RegistrationDisjointAdaptiveProposalBasisV1.SOURCE_ARCHIVE
    ),
    "NO_PRIOR": RegistrationDisjointAdaptiveProposalBasisV1.NO_PRIOR,
    "WRONG_CONSENSUS_PRIOR": (
        RegistrationDisjointAdaptiveProposalBasisV1.WRONG_SOURCE_ARCHIVE
    ),
    "OOD_ABSTENTION": (
        RegistrationDisjointAdaptiveProposalBasisV1.OOD_TYPED_ABSTENTION
    ),
}


@dataclass(frozen=True, slots=True)
class RegistrationDisjointAdaptiveProposalOrderV1:
    arm: str
    proposal_basis: RegistrationDisjointAdaptiveProposalBasisV1
    ordering_basis_id: str | None
    ordered_row_binding_ids: tuple[str, ...]
    _proposal_order_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.ordering_basis_id is not None:
            _cid(self.ordering_basis_id, "synthetic proposal ordering basis")
        if (
            self.arm not in ADAPTIVE_ARMS
            or type(self.proposal_basis)
            is not RegistrationDisjointAdaptiveProposalBasisV1
            or self.proposal_basis is not _PROPOSAL_BASIS_BY_ARM[self.arm]
            or (
                self.proposal_basis
                is RegistrationDisjointAdaptiveProposalBasisV1.NO_PRIOR
                and self.ordering_basis_id is not None
            )
            or (
                self.proposal_basis
                is not RegistrationDisjointAdaptiveProposalBasisV1.NO_PRIOR
                and self.ordering_basis_id is None
            )
            or type(self.ordered_row_binding_ids) is not tuple
            or not self.ordered_row_binding_ids
            or len(set(self.ordered_row_binding_ids))
            != len(self.ordered_row_binding_ids)
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registration-disjoint proposal order is malformed"
            )
        for value in self.ordered_row_binding_ids:
            _cid(value, "synthetic proposal row binding")
        object.__setattr__(
            self,
            "_proposal_order_id",
            _content_id("proposal", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_adaptive_"
                "proposal_order.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "arm": self.arm,
            "proposal_basis": self.proposal_basis.value,
            "ordering_basis_id": self.ordering_basis_id,
            "ordered_row_binding_ids": list(
                self.ordered_row_binding_ids
            ),
            "ordering_only": True,
            "enters_confidence": False,
            "enters_model_identity": False,
            "enters_certificate_identity": False,
            "registered_target_evidence": False,
        }

    @property
    def proposal_order_id(self) -> str:
        return self._proposal_order_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "proposal_order_id": self.proposal_order_id,
        }


class RegistrationDisjointAcquisitionPurposeV1(str, Enum):
    COLD_INITIAL = "COLD_INITIAL"
    NEW_CHILD = "NEW_CHILD"
    PROMOTION = "PROMOTION"


@dataclass(frozen=True, slots=True)
class RegistrationDisjointAdaptiveAcquisitionV1:
    round_index: int
    row_binding_id: str
    purpose: RegistrationDisjointAcquisitionPurposeV1
    frontier_id: str | None = None
    parent_acquisition_id: str | None = None
    _acquisition_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.row_binding_id, "synthetic acquisition row binding")
        if self.frontier_id is not None:
            _cid(self.frontier_id, "synthetic acquisition frontier")
        if self.parent_acquisition_id is not None:
            _cid(
                self.parent_acquisition_id,
                "synthetic acquisition parent",
            )
        cold = (
            self.purpose
            is RegistrationDisjointAcquisitionPurposeV1.COLD_INITIAL
        )
        promotion = (
            self.purpose
            is RegistrationDisjointAcquisitionPurposeV1.PROMOTION
        )
        if (
            type(self.round_index) is not int
            or self.round_index not in range(MAX_LOCAL_ROUNDS + 1)
            or type(self.purpose)
            is not RegistrationDisjointAcquisitionPurposeV1
            or (cold and self.round_index != 0)
            or (not cold and self.round_index not in (1, 2))
            or (
                cold
                and (
                    self.frontier_id is not None
                    or self.parent_acquisition_id is not None
                )
            )
            or (
                not cold
                and self.frontier_id is None
            )
            or (
                promotion
                != (self.parent_acquisition_id is not None)
            )
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registration-disjoint acquisition is malformed"
            )
        object.__setattr__(
            self,
            "_acquisition_id",
            _content_id("acquisition", self._payload()),
        )

    @property
    def discovery_draws(self) -> int:
        return (
            0
            if self.purpose
            is RegistrationDisjointAcquisitionPurposeV1.PROMOTION
            else prereg.INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
        )

    @property
    def validation_draws(self) -> int:
        return (
            prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
            if self.purpose
            is RegistrationDisjointAcquisitionPurposeV1.NEW_CHILD
            else prereg.INITIAL_VALIDATION_DRAWS_PER_PHYSICAL_ROW
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_adaptive_"
                "acquisition.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "round_index": self.round_index,
            "row_binding_id": self.row_binding_id,
            "purpose": self.purpose.value,
            "frontier_id": self.frontier_id,
            "parent_acquisition_id": self.parent_acquisition_id,
            "discovery_draws": self.discovery_draws,
            "validation_draws": self.validation_draws,
            "append_only": True,
            "source_quantities_used": False,
            "registered_target_evidence": False,
        }

    @property
    def acquisition_id(self) -> str:
        return self._acquisition_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "acquisition_id": self.acquisition_id}


@dataclass(frozen=True, slots=True)
class RegistrationDisjointAdaptiveFrontierV1:
    round_index: int
    failed_epoch_id: str
    failed_audit_id: str
    predecessor_frontier_id: str | None
    supporting_acquisition_ids: tuple[str, ...]
    selected_row_binding_ids: tuple[str, ...]
    proof_obligation_ids: tuple[str, ...]
    _causal_evidence_id: str = field(init=False, repr=False)
    _frontier_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.failed_epoch_id, "synthetic frontier failed epoch"),
            (self.failed_audit_id, "synthetic frontier failed audit"),
        ):
            _cid(value, label)
        if self.predecessor_frontier_id is not None:
            _cid(
                self.predecessor_frontier_id,
                "synthetic predecessor frontier",
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
            or self.selected_row_binding_ids
            != tuple(sorted(set(self.selected_row_binding_ids)))
            or not self.selected_row_binding_ids
            or self.proof_obligation_ids
            != tuple(sorted(set(self.proof_obligation_ids)))
            or not self.proof_obligation_ids
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registration-disjoint failed-proof frontier is malformed"
            )
        for value in (
            *self.supporting_acquisition_ids,
            *self.selected_row_binding_ids,
            *self.proof_obligation_ids,
        ):
            _cid(value, "synthetic frontier member")
        causal_payload = {
            "schema": (
                "acfqp.v072_registration_disjoint_adaptive_"
                "causal_evidence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "round_index": self.round_index,
            "failed_epoch_id": self.failed_epoch_id,
            "failed_audit_id": self.failed_audit_id,
            "supporting_acquisition_ids": list(
                self.supporting_acquisition_ids
            ),
            "selected_row_binding_ids": list(
                self.selected_row_binding_ids
            ),
            "proof_obligation_ids": list(self.proof_obligation_ids),
            "source_quantities_used": False,
        }
        object.__setattr__(
            self,
            "_causal_evidence_id",
            _content_id("frontier_causal", causal_payload),
        )
        object.__setattr__(
            self,
            "_frontier_id",
            _content_id("frontier", self._payload()),
        )

    @property
    def causal_evidence_id(self) -> str:
        return self._causal_evidence_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_adaptive_frontier.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "round_index": self.round_index,
            "failed_epoch_id": self.failed_epoch_id,
            "failed_audit_id": self.failed_audit_id,
            "predecessor_frontier_id": self.predecessor_frontier_id,
            "supporting_acquisition_ids": list(
                self.supporting_acquisition_ids
            ),
            "selected_row_binding_ids": list(
                self.selected_row_binding_ids
            ),
            "proof_obligation_ids": list(self.proof_obligation_ids),
            "causal_evidence_id": self.causal_evidence_id,
            "fresh_round_two_frontier": self.round_index == 2,
            "replacement_allowed": False,
            "source_quantities_used": False,
        }

    @property
    def frontier_id(self) -> str:
        return self._frontier_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "frontier_id": self.frontier_id}


@dataclass(frozen=True, slots=True)
class RegistrationDisjointAdaptiveLocalRoundV1:
    frontier: RegistrationDisjointAdaptiveFrontierV1
    acquisitions: tuple[RegistrationDisjointAdaptiveAcquisitionV1, ...]
    _local_round_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.frontier)
            is not RegistrationDisjointAdaptiveFrontierV1
            or type(self.acquisitions) is not tuple
            or not self.acquisitions
            or any(
                type(item)
                is not RegistrationDisjointAdaptiveAcquisitionV1
                or item.round_index != self.frontier.round_index
                or item.frontier_id != self.frontier.frontier_id
                for item in self.acquisitions
            )
            or len({item.acquisition_id for item in self.acquisitions})
            != len(self.acquisitions)
            or tuple(
                sorted(item.row_binding_id for item in self.acquisitions)
            )
            != self.frontier.selected_row_binding_ids
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registration-disjoint local acquisition round is malformed"
            )
        object.__setattr__(
            self,
            "_local_round_id",
            _content_id("round", self._payload()),
        )

    @property
    def round_index(self) -> int:
        return self.frontier.round_index

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_adaptive_local_round.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "round_index": self.round_index,
            "frontier_id": self.frontier.frontier_id,
            "acquisition_ids": [
                item.acquisition_id for item in self.acquisitions
            ],
            "target_only": True,
            "source_quantities_used": False,
        }

    @property
    def local_round_id(self) -> str:
        return self._local_round_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "frontier": self.frontier.to_document(),
            "acquisitions": [
                item.to_document() for item in self.acquisitions
            ],
            "local_round_id": self.local_round_id,
        }


@dataclass(frozen=True, slots=True)
class RegistrationDisjointAdaptiveModelEpochV1:
    epoch_index: int
    predecessor_epoch_id: str | None
    applied_frontier_id: str | None
    cumulative_acquisition_ids: tuple[str, ...]
    new_acquisition_ids: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)
    _closure_verification_id: str = field(init=False, repr=False)
    _model_pair_id: str = field(init=False, repr=False)
    _model_verification_id: str = field(init=False, repr=False)
    _epoch_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.predecessor_epoch_id is not None:
            _cid(self.predecessor_epoch_id, "synthetic predecessor epoch")
        if self.applied_frontier_id is not None:
            _cid(self.applied_frontier_id, "synthetic applied frontier")
        if (
            type(self.epoch_index) is not int
            or self.epoch_index not in range(MAX_LOCAL_ROUNDS + 1)
            or self.cumulative_acquisition_ids
            != tuple(sorted(set(self.cumulative_acquisition_ids)))
            or not self.cumulative_acquisition_ids
            or self.new_acquisition_ids
            != tuple(sorted(set(self.new_acquisition_ids)))
            or not self.new_acquisition_ids
            or not set(self.new_acquisition_ids)
            <= set(self.cumulative_acquisition_ids)
            or (
                self.epoch_index == 0
                and (
                    self.predecessor_epoch_id is not None
                    or self.applied_frontier_id is not None
                    or self.new_acquisition_ids
                    != self.cumulative_acquisition_ids
                )
            )
            or (
                self.epoch_index > 0
                and (
                    self.predecessor_epoch_id is None
                    or self.applied_frontier_id is None
                )
            )
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registration-disjoint immutable model epoch is malformed"
            )
        for value in self.cumulative_acquisition_ids:
            _cid(value, "synthetic epoch acquisition")
        closure_id = _content_id(
            "closure",
            {
                "schema": (
                    "acfqp.v072_registration_disjoint_adaptive_"
                    "observed_closure.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "cumulative_acquisition_ids": list(
                    self.cumulative_acquisition_ids
                ),
                "complete_observed_h2_closure": True,
                "source_quantities_used": False,
                "registered_target_evidence": False,
            },
        )
        object.__setattr__(self, "_closure_id", closure_id)
        object.__setattr__(
            self,
            "_closure_verification_id",
            _content_id(
                "closure_verification",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_adaptive_"
                        "observed_closure_verification.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "closure_id": closure_id,
                    "verification_result": "VALID_COMPLETE_CLOSURE",
                    "source_quantities_used": False,
                },
            ),
        )
        model_payload = {
            "schema": (
                "acfqp.v072_registration_disjoint_adaptive_model_pair.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "closure_id": closure_id,
            "closure_verification_id": self.closure_verification_id,
            "direct_and_quotient_built_together": True,
            "source_quantities_used": False,
            "registered_target_evidence": False,
        }
        model_id = _content_id("model", model_payload)
        object.__setattr__(self, "_model_pair_id", model_id)
        object.__setattr__(
            self,
            "_model_verification_id",
            _content_id(
                "model_verification",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_adaptive_"
                        "model_verification.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "model_pair_id": model_id,
                    "verification_result": "VALID",
                    "source_quantities_used": False,
                },
            ),
        )
        object.__setattr__(
            self,
            "_epoch_id",
            _content_id("epoch", self._payload()),
        )

    @property
    def model_pair_id(self) -> str:
        return self._model_pair_id

    @property
    def closure_id(self) -> str:
        return self._closure_id

    @property
    def closure_verification_id(self) -> str:
        return self._closure_verification_id

    @property
    def model_verification_id(self) -> str:
        return self._model_verification_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_adaptive_model_epoch.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "epoch_index": self.epoch_index,
            "predecessor_epoch_id": self.predecessor_epoch_id,
            "applied_frontier_id": self.applied_frontier_id,
            "cumulative_acquisition_ids": list(
                self.cumulative_acquisition_ids
            ),
            "new_acquisition_ids": list(self.new_acquisition_ids),
            "closure_id": self.closure_id,
            "closure_verification_id": self.closure_verification_id,
            "model_pair_id": self.model_pair_id,
            "model_verification_id": self.model_verification_id,
            "immutable": True,
            "source_quantities_used": False,
        }

    @property
    def epoch_id(self) -> str:
        return self._epoch_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "epoch_id": self.epoch_id}


class RegistrationDisjointAdaptiveAuditStatusV1(str, Enum):
    CERTIFIED = "CERTIFIED"
    NOT_CERTIFIED = "NOT_CERTIFIED"
    SOLVER_RESOURCE_EXHAUSTED = "SOLVER_RESOURCE_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class RegistrationDisjointAdaptiveAuditV1:
    epoch_id: str
    epoch_index: int
    status: RegistrationDisjointAdaptiveAuditStatusV1
    _planner_result_id: str = field(init=False, repr=False)
    _proof_verification_id: str | None = field(init=False, repr=False)
    _selected_policy_id: str | None = field(init=False, repr=False)
    _audit_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.epoch_id, "synthetic audit epoch")
        if (
            self.epoch_index not in range(MAX_LOCAL_ROUNDS + 1)
            or type(self.status)
            is not RegistrationDisjointAdaptiveAuditStatusV1
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registration-disjoint abstract audit is malformed"
            )
        planner_id = _content_id(
            "planner",
            {
                "schema": (
                    "acfqp.v072_registration_disjoint_adaptive_"
                    "planner_result.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "epoch_id": self.epoch_id,
                "status": self.status.value,
                "solver": "EXACT_LAZY_H2_QUOTIENT",
                "source_quantities_used": False,
            },
        )
        object.__setattr__(self, "_planner_result_id", planner_id)
        proof_id = (
            None
            if self.status
            is (
                RegistrationDisjointAdaptiveAuditStatusV1
                .SOLVER_RESOURCE_EXHAUSTED
            )
            else _content_id(
                "proof",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_adaptive_"
                        "planner_proof.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "planner_result_id": planner_id,
                    "independent_replay": True,
                    "source_quantities_used": False,
                },
            )
        )
        object.__setattr__(self, "_proof_verification_id", proof_id)
        selected_policy_id = (
            _content_id(
                "policy",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_adaptive_"
                        "selected_policy.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "epoch_id": self.epoch_id,
                    "planner_result_id": planner_id,
                    "source_quantities_used": False,
                },
            )
            if self.status
            is RegistrationDisjointAdaptiveAuditStatusV1.CERTIFIED
            else None
        )
        object.__setattr__(
            self,
            "_selected_policy_id",
            selected_policy_id,
        )
        object.__setattr__(
            self,
            "_audit_id",
            _content_id("audit", self._payload()),
        )

    @property
    def planner_result_id(self) -> str:
        return self._planner_result_id

    @property
    def proof_verification_id(self) -> str | None:
        return self._proof_verification_id

    @property
    def selected_policy_id(self) -> str | None:
        return self._selected_policy_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_adaptive_audit.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "epoch_id": self.epoch_id,
            "epoch_index": self.epoch_index,
            "status": self.status.value,
            "planner_result_id": self.planner_result_id,
            "proof_verification_id": self.proof_verification_id,
            "selected_policy_id": self.selected_policy_id,
            "source_quantities_used": False,
        }

    @property
    def audit_id(self) -> str:
        return self._audit_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


class RegistrationDisjointAdaptiveTerminalStatusV1(str, Enum):
    CERTIFIED = "CERTIFIED"
    SOLVER_RESOURCE_EXHAUSTED = "SOLVER_RESOURCE_EXHAUSTED"
    NOT_CERTIFIED_MAX_ROUNDS = "NOT_CERTIFIED_MAX_ROUNDS"


@dataclass(frozen=True, slots=True)
class RegistrationDisjointAdaptiveWorkV1:
    cold_acquisition_count: int
    local_acquisition_count: int
    producer_discovery_draws: int
    producer_validation_draws: int
    independent_replay_draws: int
    total_target_draws: int
    confidence_replay_calls: int
    confidence_projection_calls: int
    cold_closure_builds: int
    cold_closure_verifications: int
    direct_model_builds: int
    quotient_model_builds: int
    cold_model_independent_verifications: int
    quotient_planner_calls: int
    planner_proof_verifications: int
    abstract_audits: int
    frontier_freezes: int
    local_target_acquisition_rounds: int
    immutable_epoch_rebuilds: int
    operational_terminal_mints: int
    proposal_basis_reads: int
    source_quantities_in_confidence: int = 0
    source_quantities_in_model: int = 0
    source_quantities_in_certificate: int = 0
    direct_ground_planner_calls: int = 0
    fallback_calls: int = 0
    crn_draw_discount: int = 0
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0
            for value in (
                getattr(self, name)
                for name in self.__dataclass_fields__
                if name != "_work_id"
            )
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registration-disjoint adaptive work is malformed"
            )
        acquisition_count = (
            self.cold_acquisition_count + self.local_acquisition_count
        )
        if (
            self.confidence_replay_calls != acquisition_count
            or self.confidence_projection_calls != acquisition_count
            or self.independent_replay_draws
            != self.producer_discovery_draws
            + self.producer_validation_draws
            or self.total_target_draws
            != 2
            * (
                self.producer_discovery_draws
                + self.producer_validation_draws
            )
            or self.cold_closure_builds != self.abstract_audits
            or self.cold_closure_verifications != self.abstract_audits
            or self.direct_model_builds != self.abstract_audits
            or self.quotient_model_builds != self.abstract_audits
            or self.cold_model_independent_verifications
            != self.abstract_audits
            or self.quotient_planner_calls != self.abstract_audits
            or self.frontier_freezes
            != self.local_target_acquisition_rounds
            or self.immutable_epoch_rebuilds
            != self.local_target_acquisition_rounds
            or any(
                (
                    self.source_quantities_in_confidence,
                    self.source_quantities_in_model,
                    self.source_quantities_in_certificate,
                    self.direct_ground_planner_calls,
                    self.fallback_calls,
                    self.crn_draw_discount,
                )
            )
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registration-disjoint adaptive work does not reconcile"
            )
        object.__setattr__(
            self,
            "_work_id",
            _content_id("work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registration_disjoint_adaptive_work.v1",
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

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


@dataclass(frozen=True, slots=True)
class RegistrationDisjointAdaptiveRunV1:
    proposal_order: RegistrationDisjointAdaptiveProposalOrderV1
    cold_acquisitions: tuple[
        RegistrationDisjointAdaptiveAcquisitionV1, ...
    ]
    local_rounds: tuple[RegistrationDisjointAdaptiveLocalRoundV1, ...]
    epochs: tuple[RegistrationDisjointAdaptiveModelEpochV1, ...]
    audits: tuple[RegistrationDisjointAdaptiveAuditV1, ...]
    terminal_status: RegistrationDisjointAdaptiveTerminalStatusV1
    work: RegistrationDisjointAdaptiveWorkV1
    _certificate_id: str | None = field(init=False, repr=False)
    _run_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.proposal_order)
            is not RegistrationDisjointAdaptiveProposalOrderV1
            or type(self.terminal_status)
            is not RegistrationDisjointAdaptiveTerminalStatusV1
            or type(self.work) is not RegistrationDisjointAdaptiveWorkV1
            or not self.epochs
            or len(self.epochs) != len(self.audits)
            or len(self.local_rounds) != len(self.epochs) - 1
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registration-disjoint adaptive run is malformed"
            )
        final_audit = self.audits[-1]
        certificate_id = (
            _content_id(
                "certificate",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_adaptive_"
                        "certificate.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "final_epoch_id": self.epochs[-1].epoch_id,
                    "final_audit_id": final_audit.audit_id,
                    "selected_policy_id": final_audit.selected_policy_id,
                    "source_quantities_used": False,
                    "registered_target_certificate": False,
                },
            )
            if self.terminal_status
            is RegistrationDisjointAdaptiveTerminalStatusV1.CERTIFIED
            else None
        )
        object.__setattr__(self, "_certificate_id", certificate_id)
        object.__setattr__(
            self,
            "_run_id",
            _content_id("run", self._payload()),
        )

    @property
    def certificate_id(self) -> str | None:
        return self._certificate_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registration_disjoint_adaptive_run.v1",
            "schema_version": SCHEMA_VERSION,
            "proposal_order_id": self.proposal_order.proposal_order_id,
            "cold_acquisition_ids": [
                item.acquisition_id for item in self.cold_acquisitions
            ],
            "local_round_ids": [
                item.local_round_id for item in self.local_rounds
            ],
            "epoch_ids": [item.epoch_id for item in self.epochs],
            "audit_ids": [item.audit_id for item in self.audits],
            "terminal_status": self.terminal_status.value,
            "work_id": self.work.work_id,
            "certificate_id": self.certificate_id,
            "registered_target_accesses": 0,
            "production_authority_minted": False,
        }

    @property
    def run_id(self) -> str:
        return self._run_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "proposal_order": self.proposal_order.to_document(),
            "cold_acquisitions": [
                item.to_document() for item in self.cold_acquisitions
            ],
            "local_rounds": [
                item.to_document() for item in self.local_rounds
            ],
            "epochs": [item.to_document() for item in self.epochs],
            "audits": [item.to_document() for item in self.audits],
            "work": self.work.to_document(),
            "run_id": self.run_id,
        }


def _proposal_relative_order(
    proposal: RegistrationDisjointAdaptiveProposalOrderV1,
    row_ids: tuple[str, ...],
) -> tuple[str, ...]:
    selected = set(row_ids)
    return tuple(
        row_id
        for row_id in proposal.ordered_row_binding_ids
        if row_id in selected
    )


def run_registration_disjoint_adaptive_state_machine_core_v1(
    *,
    proposal_order: RegistrationDisjointAdaptiveProposalOrderV1,
    cold_acquisitions: tuple[
        RegistrationDisjointAdaptiveAcquisitionV1, ...
    ],
    local_rounds: tuple[RegistrationDisjointAdaptiveLocalRoundV1, ...],
    epochs: tuple[RegistrationDisjointAdaptiveModelEpochV1, ...],
    audits: tuple[RegistrationDisjointAdaptiveAuditV1, ...],
) -> RegistrationDisjointAdaptiveRunV1:
    """Replay the full adaptive schedule without registered target evidence."""

    if (
        type(proposal_order)
        is not RegistrationDisjointAdaptiveProposalOrderV1
        or type(cold_acquisitions) is not tuple
        or not cold_acquisitions
        or any(
            type(item)
            is not RegistrationDisjointAdaptiveAcquisitionV1
            or item.round_index != 0
            or item.purpose
            is not RegistrationDisjointAcquisitionPurposeV1.COLD_INITIAL
            for item in cold_acquisitions
        )
        or type(local_rounds) is not tuple
        or any(
            type(item) is not RegistrationDisjointAdaptiveLocalRoundV1
            for item in local_rounds
        )
        or type(epochs) is not tuple
        or type(audits) is not tuple
        or not epochs
        or len(epochs) not in range(1, MAX_LOCAL_ROUNDS + 2)
        or len(audits) != len(epochs)
        or len(local_rounds) != len(epochs) - 1
    ):
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            "registration-disjoint adaptive schedule is malformed"
        )
    cold_rows = tuple(item.row_binding_id for item in cold_acquisitions)
    if (
        len(set(cold_rows)) != len(cold_rows)
        or len({item.acquisition_id for item in cold_acquisitions})
        != len(cold_acquisitions)
        or _proposal_relative_order(proposal_order, cold_rows) != cold_rows
        or not set(cold_rows)
        <= set(proposal_order.ordered_row_binding_ids)
    ):
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            "cold observed closure was replaced or ignores proposal order"
        )

    all_acquisitions: dict[
        str, RegistrationDisjointAdaptiveAcquisitionV1
    ] = {
        item.acquisition_id: item for item in cold_acquisitions
    }
    cold_ids = tuple(sorted(all_acquisitions))
    if (
        type(epochs[0])
        is not RegistrationDisjointAdaptiveModelEpochV1
        or epochs[0].epoch_index != 0
        or epochs[0].cumulative_acquisition_ids != cold_ids
        or epochs[0].new_acquisition_ids != cold_ids
    ):
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            "cold model epoch does not bind the complete observed closure"
        )

    previous_frontier: (
        RegistrationDisjointAdaptiveFrontierV1 | None
    ) = None
    for index, (epoch, audit) in enumerate(
        zip(epochs, audits, strict=True)
    ):
        if (
            type(epoch) is not RegistrationDisjointAdaptiveModelEpochV1
            or epoch.epoch_index != index
            or type(audit) is not RegistrationDisjointAdaptiveAuditV1
            or audit.epoch_index != index
            or audit.epoch_id != epoch.epoch_id
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "model epoch and abstract audit sequence diverged"
            )
        if index == 0:
            continue
        previous_epoch = epochs[index - 1]
        previous_audit = audits[index - 1]
        local_round = local_rounds[index - 1]
        frontier = local_round.frontier
        if (
            previous_audit.status
            is not RegistrationDisjointAdaptiveAuditStatusV1.NOT_CERTIFIED
            or local_round.round_index != index
            or frontier.failed_epoch_id != previous_epoch.epoch_id
            or frontier.failed_audit_id != previous_audit.audit_id
            or frontier.supporting_acquisition_ids
            != previous_epoch.cumulative_acquisition_ids
            or (
                index == 1
                and frontier.predecessor_frontier_id is not None
            )
            or (
                index == 2
                and (
                    previous_frontier is None
                    or frontier.predecessor_frontier_id
                    != previous_frontier.frontier_id
                    or not set(
                        previous_frontier.supporting_acquisition_ids
                    )
                    < set(frontier.supporting_acquisition_ids)
                )
            )
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "failed-proof frontier is stale or round two is not a "
                "fresh strict extension"
            )
        acquisition_rows = tuple(
            item.row_binding_id for item in local_round.acquisitions
        )
        if (
            _proposal_relative_order(proposal_order, acquisition_rows)
            != acquisition_rows
            or not set(acquisition_rows)
            <= set(proposal_order.ordered_row_binding_ids)
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "local acquisition order is not the proposal-only order"
            )
        previous_ids = set(previous_epoch.cumulative_acquisition_ids)
        previous_rows = {
            all_acquisitions[item].row_binding_id for item in previous_ids
        }
        new_ids: list[str] = []
        for acquisition in local_round.acquisitions:
            if acquisition.acquisition_id in all_acquisitions:
                raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                    "local acquisition replaced existing evidence"
                )
            if (
                acquisition.purpose
                is RegistrationDisjointAcquisitionPurposeV1.NEW_CHILD
                and acquisition.row_binding_id in previous_rows
            ):
                raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                    "new-child acquisition replaced an observed row"
                )
            if acquisition.purpose is (
                RegistrationDisjointAcquisitionPurposeV1.PROMOTION
            ):
                parent = all_acquisitions.get(
                    acquisition.parent_acquisition_id or ""
                )
                if (
                    parent is None
                    or parent.acquisition_id not in previous_ids
                    or parent.row_binding_id
                    != acquisition.row_binding_id
                ):
                    raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                        "promotion does not append to a prior same-row "
                        "acquisition"
                    )
            all_acquisitions[acquisition.acquisition_id] = acquisition
            new_ids.append(acquisition.acquisition_id)
        expected_new = tuple(sorted(new_ids))
        expected_cumulative = tuple(sorted(all_acquisitions))
        if (
            epoch.predecessor_epoch_id != previous_epoch.epoch_id
            or epoch.applied_frontier_id != frontier.frontier_id
            or epoch.new_acquisition_ids != expected_new
            or epoch.cumulative_acquisition_ids != expected_cumulative
            or set(previous_epoch.cumulative_acquisition_ids)
            & set(epoch.new_acquisition_ids)
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "immutable epoch rebuild skipped, rewrote, or replaced "
                "target evidence"
            )
        previous_frontier = frontier

    terminal_indices = tuple(
        index
        for index, audit in enumerate(audits)
        if audit.status
        is not RegistrationDisjointAdaptiveAuditStatusV1.NOT_CERTIFIED
    )
    if terminal_indices and terminal_indices != (len(audits) - 1,):
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            "adaptive state machine continued after a terminal audit"
        )
    final = audits[-1]
    if (
        final.status
        is RegistrationDisjointAdaptiveAuditStatusV1.NOT_CERTIFIED
        and len(local_rounds) != MAX_LOCAL_ROUNDS
    ):
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            "adaptive state machine stopped before both authorized local "
            "rounds were exhausted"
        )
    terminal = {
        RegistrationDisjointAdaptiveAuditStatusV1.CERTIFIED: (
            RegistrationDisjointAdaptiveTerminalStatusV1.CERTIFIED
        ),
        RegistrationDisjointAdaptiveAuditStatusV1
        .SOLVER_RESOURCE_EXHAUSTED: (
            RegistrationDisjointAdaptiveTerminalStatusV1
            .SOLVER_RESOURCE_EXHAUSTED
        ),
        RegistrationDisjointAdaptiveAuditStatusV1.NOT_CERTIFIED: (
            RegistrationDisjointAdaptiveTerminalStatusV1
            .NOT_CERTIFIED_MAX_ROUNDS
        ),
    }[final.status]

    acquisition_values = tuple(all_acquisitions.values())
    producer_discovery = sum(
        item.discovery_draws for item in acquisition_values
    )
    producer_validation = sum(
        item.validation_draws for item in acquisition_values
    )
    epoch_count = len(epochs)
    local_count = len(all_acquisitions) - len(cold_acquisitions)
    work = RegistrationDisjointAdaptiveWorkV1(
        cold_acquisition_count=len(cold_acquisitions),
        local_acquisition_count=local_count,
        producer_discovery_draws=producer_discovery,
        producer_validation_draws=producer_validation,
        independent_replay_draws=(
            producer_discovery + producer_validation
        ),
        total_target_draws=2 * (producer_discovery + producer_validation),
        confidence_replay_calls=len(all_acquisitions),
        confidence_projection_calls=len(all_acquisitions),
        cold_closure_builds=epoch_count,
        cold_closure_verifications=epoch_count,
        direct_model_builds=epoch_count,
        quotient_model_builds=epoch_count,
        cold_model_independent_verifications=epoch_count,
        quotient_planner_calls=epoch_count,
        planner_proof_verifications=sum(
            audit.proof_verification_id is not None for audit in audits
        ),
        abstract_audits=epoch_count,
        frontier_freezes=len(local_rounds),
        local_target_acquisition_rounds=len(local_rounds),
        immutable_epoch_rebuilds=len(local_rounds),
        operational_terminal_mints=int(
            terminal
            is RegistrationDisjointAdaptiveTerminalStatusV1.CERTIFIED
        ),
        proposal_basis_reads=int(
            proposal_order.ordering_basis_id is not None
        ),
    )
    return RegistrationDisjointAdaptiveRunV1(
        proposal_order,
        cold_acquisitions,
        local_rounds,
        epochs,
        audits,
        terminal,
        work,
    )


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            "registered adaptive arithmetic must use exact Fractions"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _action(
    value: Any,
    field_name: str,
) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
    ):
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            f"{field_name} must be one exact integer action triple"
        )
    return value


@dataclass(frozen=True, slots=True)
class RegisteredAdaptiveConcretizerDecisionV1:
    """One deterministic semantic decision and its complete fixed support."""

    model_id: str
    ground_state_id: str
    public_state_id: str
    state_ranks: tuple[int, ...]
    remaining_horizon: int
    state_coordinate_key: str
    selected_abstract_action_key: str
    concretizer_entry_id: str
    ground_action_ids: tuple[str, ...]
    ground_semantic_action_ids: tuple[str, ...]
    ground_actions: tuple[tuple[int, int, int], ...]
    uniform_weights: tuple[Fraction, ...]
    _decision_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.model_id, "adaptive policy model"),
            (self.ground_state_id, "adaptive ground state"),
            (self.public_state_id, "adaptive public state"),
            (self.state_coordinate_key, "adaptive state coordinate"),
            (
                self.selected_abstract_action_key,
                "adaptive abstract action",
            ),
            (self.concretizer_entry_id, "adaptive concretizer"),
            *(
                (item, "adaptive ground action")
                for item in self.ground_action_ids
            ),
            *(
                (item, "adaptive ground semantic action")
                for item in self.ground_semantic_action_ids
            ),
        ):
            _cid(value, label)
        for item in self.ground_actions:
            _action(item, "adaptive concretized action")
        support_size = len(self.ground_action_ids)
        if (
            type(self.state_ranks) is not tuple
            or not self.state_ranks
            or any(
                type(item) is not int
                or not 0 <= item <= prereg.RANK_CAP
                for item in self.state_ranks
            )
            or self.remaining_horizon not in (1, 2)
            or self.ground_action_ids
            != tuple(sorted(set(self.ground_action_ids)))
            or support_size == 0
            or len(self.ground_actions) != support_size
            or len(self.ground_semantic_action_ids) != support_size
            or len(set(self.ground_semantic_action_ids)) != support_size
            or len(set(self.ground_actions)) != support_size
            or type(self.uniform_weights) is not tuple
            or self.uniform_weights
            != tuple(Fraction(1, support_size) for _ in range(support_size))
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registered adaptive concretizer support is malformed"
            )
        object.__setattr__(
            self,
            "_decision_id",
            _content_id(
                "registered_concretizer_decision",
                self._payload(),
            ),
        )

    @property
    def singleton(self) -> bool:
        return len(self.ground_action_ids) == 1

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_adaptive_"
                "concretizer_decision.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model_id,
            "ground_state_id": self.ground_state_id,
            "public_state_id": self.public_state_id,
            "state_ranks": list(self.state_ranks),
            "remaining_horizon": self.remaining_horizon,
            "state_coordinate_key": self.state_coordinate_key,
            "selected_abstract_action_key": (
                self.selected_abstract_action_key
            ),
            "concretizer_entry_id": self.concretizer_entry_id,
            "ground_action_ids": list(self.ground_action_ids),
            "ground_semantic_action_ids": list(
                self.ground_semantic_action_ids
            ),
            "ground_actions": [
                list(item) for item in self.ground_actions
            ],
            "uniform_weights": [
                _fdoc(item) for item in self.uniform_weights
            ],
            "singleton": self.singleton,
            "fixed_concretizer": True,
            "source_quantities_used": False,
        }

    @property
    def decision_id(self) -> str:
        return self._decision_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


@dataclass(frozen=True, slots=True)
class RegisteredAdaptiveGroundPolicyDecisionV1:
    """Adapter-ready deterministic ground decision, available if singleton."""

    ground_state_id: str
    state_id: str
    state_ranks: tuple[int, ...]
    remaining_horizon: int
    action: tuple[int, int, int]
    source_concretizer_decision_id: str
    _decision_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.ground_state_id, "ground policy ground state"),
            (self.state_id, "ground policy public state"),
            (
                self.source_concretizer_decision_id,
                "ground policy concretizer source",
            ),
        ):
            _cid(value, label)
        _action(self.action, "ground policy action")
        if (
            type(self.state_ranks) is not tuple
            or not self.state_ranks
            or any(
                type(item) is not int
                or not 0 <= item <= prereg.RANK_CAP
                for item in self.state_ranks
            )
            or self.remaining_horizon not in (1, 2)
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "adapter-ready ground policy decision is malformed"
            )
        object.__setattr__(
            self,
            "_decision_id",
            _content_id("registered_ground_decision", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_adaptive_"
                "ground_policy_decision.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "ground_state_id": self.ground_state_id,
            "state_id": self.state_id,
            "state_ranks": list(self.state_ranks),
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "source_concretizer_decision_id": (
                self.source_concretizer_decision_id
            ),
            "singleton_concretizer_verified": True,
            "source_quantities_used": False,
        }

    @property
    def decision_id(self) -> str:
        return self._decision_id

    @property
    def semantic_key(
        self,
    ) -> tuple[tuple[int, ...], tuple[int, int, int]]:
        return self.state_ranks, self.action

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


def derive_registered_adaptive_policy_support_v1(
    *,
    model_pair: models.RegisteredColdH2ModelPairV1,
    audit: robust.RobustPlanAuditV1,
) -> tuple[
    tuple[RegisteredAdaptiveConcretizerDecisionV1, ...],
    tuple[RegisteredAdaptiveGroundPolicyDecisionV1, ...],
]:
    """Mechanically extract complete fixed supports; never choose a mixture."""

    if (
        type(model_pair) is not models.RegisteredColdH2ModelPairV1
        or type(audit) is not robust.RobustPlanAuditV1
        or audit.model_id != model_pair.quotient_planner_model.model_id
        or audit.threshold_profile_id
        != model_pair.threshold_profile.threshold_profile_id
        or audit.solver_kind is not robust.RobustSolverKind.QUOTIENT
        or audit.status is not robust.RobustAuditStatus.CERTIFIED
    ):
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            "adaptive policy support requires one certified quotient audit"
        )
    model = model_pair.quotient_planner_model
    robust.verify_robust_plan_audit_v1(
        model,
        model_pair.threshold_profile,
        audit,
    )
    projection_by_key = {
        (
            item.interval_row.state_id,
            item.interval_row.action_id,
        ): item
        for item in model_pair.row_projections
    }
    catalogue_by_state = {
        item.state_id: item for item in model.catalogues
    }
    concretizer_by_key = {
        (
            item.state_coordinate_key,
            item.state_id,
            item.abstract_action_key,
        ): item
        for item in model.concretizer_entries
    }
    decisions: list[RegisteredAdaptiveConcretizerDecisionV1] = []
    seen_states: set[tuple[str, int]] = set()
    for assignment in audit.assignments:
        if assignment.scope is not robust.PolicyScope.QUOTIENT_CELL:
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "certified quotient audit contains a ground-scope assignment"
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
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "adaptive assignment has no state in its frozen cell"
            )
        for state_id in state_ids:
            key = (state_id, assignment.remaining_horizon)
            if key in seen_states:
                raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                    "adaptive policy assigns one state more than once"
                )
            seen_states.add(key)
            catalogue = catalogue_by_state[state_id]
            entry = concretizer_by_key.get(
                (
                    catalogue.state_coordinate_key,
                    state_id,
                    assignment.selected_action_key,
                )
            )
            if entry is None:
                raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                    "adaptive assignment lacks its fixed concretizer"
                )
            projections = tuple(
                projection_by_key.get((state_id, action_id))
                for action_id in entry.ground_action_ids
            )
            if any(item is None for item in projections):
                raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                    "adaptive concretizer support lacks physical row evidence"
                )
            exact_projections = tuple(
                item for item in projections if item is not None
            )
            state_documents = tuple(
                dict(item.row_evidence.state.document)
                for item in exact_projections
            )
            action_documents = tuple(
                dict(item.row_evidence.action.document)
                for item in exact_projections
            )
            ranks_values = {
                tuple(item.get("ranks", ())) for item in state_documents
            }
            public_state_ids = {
                item.row_evidence.state.semantic_state_id
                for item in exact_projections
            }
            actions = tuple(
                tuple(item.get("action", ()))
                for item in action_documents
            )
            if (
                len(ranks_values) != 1
                or len(public_state_ids) != 1
                or any(
                    type(value) is not tuple
                    or len(value) != 3
                    or any(type(member) is not int for member in value)
                    for value in actions
                )
            ):
                raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                    "adaptive support has conflicting public semantics"
                )
            decisions.append(
                RegisteredAdaptiveConcretizerDecisionV1(
                    model.model_id,
                    state_id,
                    next(iter(public_state_ids)),
                    next(iter(ranks_values)),
                    assignment.remaining_horizon,
                    catalogue.state_coordinate_key,
                    assignment.selected_action_key,
                    entry.concretizer_entry_id,
                    entry.ground_action_ids,
                    tuple(
                        item.row_evidence.action.semantic_action_id
                        for item in exact_projections
                    ),
                    actions,
                    tuple(
                        Fraction(1, len(entry.ground_action_ids))
                        for _ in entry.ground_action_ids
                    ),
                )
            )
    output = tuple(
        sorted(decisions, key=lambda item: item.decision_id)
    )
    expected_states = {
        item.state_id for item in model.catalogues
    }
    if (
        {item.ground_state_id for item in output} != expected_states
        or sum(item.remaining_horizon == 2 for item in output) != 1
    ):
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            "adaptive policy support does not cover every model state"
        )
    ground = (
        tuple(
            sorted(
                (
                    RegisteredAdaptiveGroundPolicyDecisionV1(
                        item.ground_state_id,
                        item.public_state_id,
                        item.state_ranks,
                        item.remaining_horizon,
                        item.ground_actions[0],
                        item.decision_id,
                    )
                    for item in output
                ),
                key=lambda item: item.decision_id,
            )
        )
        if all(item.singleton for item in output)
        else ()
    )
    return output, ground


class RegisteredAdaptiveOccurrenceStatusV1(str, Enum):
    CERTIFIED = "CERTIFIED"
    EXACT_DP_RESOURCE_EXHAUSTED = "EXACT_DP_RESOURCE_EXHAUSTED"
    NO_SOUND_COVER = "NO_SOUND_COVER"
    ACQUISITION_CAP_EXHAUSTED = "ACQUISITION_CAP_EXHAUSTED"
    NOT_CERTIFIED_MAX_ROUNDS = "NOT_CERTIFIED_MAX_ROUNDS"


class RegisteredAdaptiveGroundAdapterStatusV1(str, Enum):
    SINGLETON_GROUND_POLICY_READY = "SINGLETON_GROUND_POLICY_READY"
    FIXED_CONCRETIZER_OPERATIONAL_POLICY_SCHEMA_NOT_INTEGRATED = (
        "REGISTERED_FIXED_CONCRETIZER_"
        "OPERATIONAL_POLICY_SCHEMA_NOT_INTEGRATED"
    )
    NOT_APPLICABLE_NONCERTIFICATE = "NOT_APPLICABLE_NONCERTIFICATE"


def _terminal_status_from_selector_outcome_v1(
    outcome: selector.RegisteredSelectorOutcomeV1,
) -> RegisteredAdaptiveOccurrenceStatusV1:
    if outcome is selector.RegisteredSelectorOutcomeV1.NO_SOUND_COVER:
        return RegisteredAdaptiveOccurrenceStatusV1.NO_SOUND_COVER
    if outcome is selector.RegisteredSelectorOutcomeV1.CAP_EXHAUSTED:
        return (
            RegisteredAdaptiveOccurrenceStatusV1
            .ACQUISITION_CAP_EXHAUSTED
        )
    if outcome is selector.RegisteredSelectorOutcomeV1.SELECTED:
        raise V072RegisteredAdaptiveRuntimeInvariantViolation(
            "a SELECTED terminal selector outcome was not materialized "
            "into a subsequent immutable model epoch"
        )
    raise V072RegisteredAdaptiveRuntimeInvariantViolation(
        "adaptive runtime has an unknown terminal selector outcome"
    )


@dataclass(frozen=True, slots=True)
class RegisteredAdaptiveOccurrenceWorkV1:
    cold_epoch_builds: int
    incremental_epoch_builds: int
    incremental_epoch_independent_replay_calls: int
    acquisition_calls: int
    confidence_replay_calls: int
    producer_stream_opens: int
    producer_draw_calls: int
    replay_stream_opens: int
    replay_draw_calls: int
    unique_online_sample_evidence_draws: int
    total_observer_draw_calls: int
    closure_builds: int
    closure_independent_verifications: int
    confidence_projection_calls: int
    model_pair_builds: int
    model_pair_independent_verifications: int
    quotient_planner_calls: int
    planner_proof_verification_calls: int
    selector_calls: int
    selector_independent_replay_calls: int
    branch_nodes: int
    complete_policies: int
    root_bound_evaluations: int
    pruned_branches: int
    source_ordering_recipe_reads: int
    source_quantities_in_confidence: int = 0
    source_quantities_in_model: int = 0
    source_quantities_in_certificate: int = 0
    direct_ground_planner_calls: int = 0
    fallback_calls: int = 0
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if any(
            type(getattr(self, name)) is not int
            or getattr(self, name) < 0
            for name in self.__dataclass_fields__
            if name != "_work_id"
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registered adaptive occurrence work is malformed"
            )
        if (
            self.cold_epoch_builds != 1
            or self.incremental_epoch_independent_replay_calls
            != self.incremental_epoch_builds
            or self.total_observer_draw_calls
            != self.producer_draw_calls + self.replay_draw_calls
            or self.unique_online_sample_evidence_draws
            != self.producer_draw_calls
            or self.closure_builds
            != self.cold_epoch_builds + self.incremental_epoch_builds
            or self.closure_independent_verifications
            != self.closure_builds
            or self.model_pair_builds != self.closure_builds
            or self.model_pair_independent_verifications
            != self.closure_builds
            or self.quotient_planner_calls != self.closure_builds
            or self.selector_independent_replay_calls
            != self.selector_calls
            or self.incremental_epoch_builds > MAX_LOCAL_ROUNDS
            or any(
                (
                    self.source_quantities_in_confidence,
                    self.source_quantities_in_model,
                    self.source_quantities_in_certificate,
                    self.direct_ground_planner_calls,
                    self.fallback_calls,
                )
            )
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registered adaptive occurrence work does not reconcile"
            )
        object.__setattr__(
            self,
            "_work_id",
            _content_id("registered_work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_adaptive_occurrence_work.v1",
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
                if name != "_work_id"
            },
            "evidence_and_replay_work_separate": True,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


RegisteredProductionModelEpochV1 = (
    cold_runtime.RegisteredColdH2ModelEpochV1
    | incremental.RegisteredIncrementalH2ModelEpochV1
)


def _epoch_model_pair(
    epoch: RegisteredProductionModelEpochV1,
) -> models.RegisteredColdH2ModelPairV1:
    if type(epoch) is cold_runtime.RegisteredColdH2ModelEpochV1:
        return epoch.model_pair
    if type(epoch) is incremental.RegisteredIncrementalH2ModelEpochV1:
        return epoch.model_pair
    raise V072RegisteredAdaptiveRuntimeInvariantViolation(
        "adaptive runtime epoch has the wrong exact type"
    )


def _epoch_access(
    epoch: RegisteredProductionModelEpochV1,
) -> Any:
    if type(epoch) is cold_runtime.RegisteredColdH2ModelEpochV1:
        return epoch.access_audit
    if type(epoch) is incremental.RegisteredIncrementalH2ModelEpochV1:
        return epoch.access_audit
    raise V072RegisteredAdaptiveRuntimeInvariantViolation(
        "adaptive runtime epoch access has the wrong exact type"
    )


def _search_counters(
    result: planner.V072ExactLazyPlannerComponentResultV1,
) -> tuple[int, int, int, int]:
    solve = result.solve_result
    if solve.status is lazy.ExactLazyH2SolveStatus.SOLVED:
        assert solve.trace is not None
        values = [solve.trace.original]
        if solve.trace.zero_other_counterfactual is not None:
            values.append(solve.trace.zero_other_counterfactual)
    else:
        assert solve.exhaustion is not None
        values = [solve.exhaustion.counters]
    return (
        sum(item.branch_nodes for item in values),
        sum(item.complete_policies for item in values),
        sum(item.root_bound_evaluations for item in values),
        sum(item.pruned_branches for item in values),
    )


def _derive_registered_adaptive_work(
    epochs: tuple[RegisteredProductionModelEpochV1, ...],
    planner_results: tuple[
        planner.V072ExactLazyPlannerComponentResultV1, ...
    ],
    selector_closures: tuple[selector.RegisteredSelectorClosureV1, ...],
) -> RegisteredAdaptiveOccurrenceWorkV1:
    accesses = tuple(_epoch_access(item) for item in epochs)
    counters = tuple(_search_counters(item) for item in planner_results)
    return RegisteredAdaptiveOccurrenceWorkV1(
        cold_epoch_builds=1,
        incremental_epoch_builds=len(epochs) - 1,
        incremental_epoch_independent_replay_calls=len(epochs) - 1,
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
        replay_draw_calls=sum(
            item.replay_draw_calls for item in accesses
        ),
        unique_online_sample_evidence_draws=sum(
            item.unique_online_sample_evidence_draws for item in accesses
        ),
        total_observer_draw_calls=sum(
            item.total_observer_draw_calls for item in accesses
        ),
        closure_builds=len(epochs),
        closure_independent_verifications=len(epochs),
        confidence_projection_calls=sum(
            item.projection_calls for item in accesses
        ),
        model_pair_builds=len(epochs),
        model_pair_independent_verifications=len(epochs),
        quotient_planner_calls=len(planner_results),
        planner_proof_verification_calls=sum(
            item.independent_proof_replay_complete
            for item in planner_results
        ),
        selector_calls=len(selector_closures),
        selector_independent_replay_calls=len(selector_closures),
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
                for item in selector_closures
            )
        ),
    )


_REGISTERED_RESULT_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredAdaptiveOccurrenceResultV1:
    """Complete typed production result before independent runtime wrapping."""

    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1
    context: prereg.HeldoutPublicGraphContextV2
    epochs: tuple[RegisteredProductionModelEpochV1, ...]
    planner_results: tuple[
        planner.V072ExactLazyPlannerComponentResultV1, ...
    ]
    selector_closures: tuple[selector.RegisteredSelectorClosureV1, ...]
    status: RegisteredAdaptiveOccurrenceStatusV1
    concretizer_policy: tuple[
        RegisteredAdaptiveConcretizerDecisionV1, ...
    ]
    ground_policy: tuple[
        RegisteredAdaptiveGroundPolicyDecisionV1, ...
    ]
    adapter_status: RegisteredAdaptiveGroundAdapterStatusV1
    work: RegisteredAdaptiveOccurrenceWorkV1
    _certificate_id: str | None = field(init=False, repr=False)
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authority_chain_id, "adaptive result authority chain"),
            (self.anchor_id, "adaptive result anchor"),
        ):
            _cid(value, label)
        if (
            self._minting_capability is not _REGISTERED_RESULT_MINTING_SENTINEL
            or type(self.occurrence_plan)
            is not consumer.RegisteredOccurrenceExecutionPlanV1
            or self.occurrence_plan.chain_id != self.authority_chain_id
            or type(self.context) is not prereg.HeldoutPublicGraphContextV2
            or self.occurrence_plan.template.context_id
            != self.context.context_id
            or self.occurrence_plan.template.arm not in ADAPTIVE_ARMS
            or type(self.epochs) is not tuple
            or not 1 <= len(self.epochs) <= MAX_LOCAL_ROUNDS + 1
            or type(self.epochs[0])
            is not cold_runtime.RegisteredColdH2ModelEpochV1
            or any(
                type(item)
                is not incremental.RegisteredIncrementalH2ModelEpochV1
                or item.round_index != index
                for index, item in enumerate(self.epochs[1:], start=1)
            )
            or any(
                item.authority_chain_id != self.authority_chain_id
                or item.anchor_id != self.anchor_id
                or item.occurrence_plan != self.occurrence_plan
                or item.context != self.context
                for item in self.epochs
            )
            or type(self.planner_results) is not tuple
            or len(self.planner_results) != len(self.epochs)
            or any(
                type(item)
                is not planner.V072ExactLazyPlannerComponentResultV1
                for item in self.planner_results
            )
            or type(self.selector_closures) is not tuple
            or any(
                type(item) is not selector.RegisteredSelectorClosureV1
                for item in self.selector_closures
            )
            or type(self.status) is not RegisteredAdaptiveOccurrenceStatusV1
            or type(self.adapter_status)
            is not RegisteredAdaptiveGroundAdapterStatusV1
            or type(self.work) is not RegisteredAdaptiveOccurrenceWorkV1
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "registered adaptive occurrence result is malformed"
            )
        for epoch, result in zip(
            self.epochs,
            self.planner_results,
            strict=True,
        ):
            pair = _epoch_model_pair(epoch)
            if (
                result.model_id
                != pair.quotient_planner_model.model_id
                or result.threshold_profile_id
                != pair.threshold_profile.threshold_profile_id
                or result.solver_kind
                is not robust.RobustSolverKind.QUOTIENT
            ):
                raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                    "adaptive planner result was transplanted across epochs"
                )
        selected_closures = tuple(
            item
            for item in self.selector_closures
            if item.claim.decision.outcome
            is selector.RegisteredSelectorOutcomeV1.SELECTED
        )
        if (
            len(selected_closures) != len(self.epochs) - 1
            or any(
                item.selector_closure != selected_closures[index - 1]
                for index, item in enumerate(self.epochs[1:], start=1)
            )
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "adaptive selector and immutable epoch lineage diverged"
            )
        for index, closure in enumerate(self.selector_closures):
            if index >= len(self.epochs):
                raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                    "adaptive selector closure lacks its failed epoch"
                )
            solve = self.planner_results[index].solve_result
            audit = solve.audit
            pair = _epoch_model_pair(self.epochs[index])
            if (
                audit is None
                or audit.status
                is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
                or closure.claim.round_index != index + 1
                or closure.claim.model_pair_id != pair.model_pair_id
                or closure.claim.failed_audit_id != audit.audit_id
            ):
                raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                    "selector closure does not follow its exact failed audit"
                )
        final_result = self.planner_results[-1]
        final_solve = final_result.solve_result
        final_audit = final_solve.audit
        final_selector = (
            None
            if len(self.selector_closures) < len(self.epochs)
            else self.selector_closures[-1]
        )
        expected_status: RegisteredAdaptiveOccurrenceStatusV1
        if final_solve.status is (
            lazy.ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED
        ):
            expected_status = (
                RegisteredAdaptiveOccurrenceStatusV1
                .EXACT_DP_RESOURCE_EXHAUSTED
            )
        elif (
            final_audit is not None
            and final_audit.status is robust.RobustAuditStatus.CERTIFIED
        ):
            expected_status = RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
        elif final_selector is not None:
            expected_status = _terminal_status_from_selector_outcome_v1(
                final_selector.claim.decision.outcome
            )
        elif len(self.epochs) == MAX_LOCAL_ROUNDS + 1:
            expected_status = (
                RegisteredAdaptiveOccurrenceStatusV1
                .NOT_CERTIFIED_MAX_ROUNDS
            )
        else:
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "adaptive runtime stopped before a typed terminal condition"
            )
        if self.status is not expected_status:
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "adaptive runtime terminal status was caller-selected"
            )
        certified = (
            self.status is RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
        )
        if certified:
            assert final_audit is not None
            expected_concretizer, expected_ground = (
                derive_registered_adaptive_policy_support_v1(
                    model_pair=_epoch_model_pair(self.epochs[-1]),
                    audit=final_audit,
                )
            )
            expected_adapter = (
                RegisteredAdaptiveGroundAdapterStatusV1
                .SINGLETON_GROUND_POLICY_READY
                if expected_ground
                else RegisteredAdaptiveGroundAdapterStatusV1
                .FIXED_CONCRETIZER_OPERATIONAL_POLICY_SCHEMA_NOT_INTEGRATED
            )
            if (
                self.concretizer_policy != expected_concretizer
                or self.ground_policy != expected_ground
                or self.adapter_status is not expected_adapter
            ):
                raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                    "certified adaptive policy support was not mechanical"
                )
        elif (
            self.concretizer_policy
            or self.ground_policy
            or self.adapter_status
            is not (
                RegisteredAdaptiveGroundAdapterStatusV1
                .NOT_APPLICABLE_NONCERTIFICATE
            )
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "noncertificate adaptive result exposes a policy"
            )
        if self.work != _derive_registered_adaptive_work(
            self.epochs,
            self.planner_results,
            self.selector_closures,
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "adaptive occurrence work cannot be replayed"
            )
        certificate_id = (
            _content_id(
                "registered_certificate",
                {
                    "schema": (
                        "acfqp.v072_registered_adaptive_plan_certificate.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "authority_chain_id": self.authority_chain_id,
                    "anchor_id": self.anchor_id,
                    "occurrence_id": self.occurrence_plan.occurrence_id,
                    "context_id": self.context.context_id,
                    "final_model_pair_id": (
                        _epoch_model_pair(self.epochs[-1]).model_pair_id
                    ),
                    "planner_component_result_id": (
                        final_result.component_result_id
                    ),
                    "audit_id": final_audit.audit_id,
                    "concretizer_decision_ids": [
                        item.decision_id
                        for item in self.concretizer_policy
                    ],
                    "fixed_concretizer_preserved": True,
                    "source_quantities_used": False,
                },
            )
            if certified
            else None
        )
        object.__setattr__(self, "_certificate_id", certificate_id)
        object.__setattr__(
            self,
            "_result_id",
            _content_id("registered_result", self._payload()),
        )

    @property
    def certificate_id(self) -> str | None:
        return self._certificate_id

    @property
    def result_id(self) -> str:
        return self._result_id

    @property
    def selected_root_action(self) -> tuple[int, int, int] | None:
        if (
            self.adapter_status
            is not (
                RegisteredAdaptiveGroundAdapterStatusV1
                .SINGLETON_GROUND_POLICY_READY
            )
        ):
            return None
        return next(
            item.action
            for item in self.ground_policy
            if item.remaining_horizon == 2
        )

    @property
    def complete_child_policy(
        self,
    ) -> tuple[RegisteredAdaptiveGroundPolicyDecisionV1, ...]:
        if self.selected_root_action is None:
            return ()
        return tuple(
            sorted(
                (
                    item
                    for item in self.ground_policy
                    if item.remaining_horizon == 1
                ),
                key=lambda item: item.semantic_key,
            )
        )

    @property
    def operational_terminal_adapter_ready(self) -> bool:
        return (
            self.status is RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
            and self.adapter_status
            is (
                RegisteredAdaptiveGroundAdapterStatusV1
                .SINGLETON_GROUND_POLICY_READY
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_adaptive_occurrence_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "occurrence_id": self.occurrence_plan.occurrence_id,
            "context_id": self.context.context_id,
            "arm": self.occurrence_plan.template.arm,
            "epoch_ids": [item.epoch_id for item in self.epochs],
            "planner_component_result_ids": [
                item.component_result_id for item in self.planner_results
            ],
            "selector_closure_ids": [
                item.closure_id for item in self.selector_closures
            ],
            "status": self.status.value,
            "certificate_id": self.certificate_id,
            "concretizer_decision_ids": [
                item.decision_id for item in self.concretizer_policy
            ],
            "ground_policy_decision_ids": [
                item.decision_id for item in self.ground_policy
            ],
            "adapter_status": self.adapter_status.value,
            "operational_terminal_adapter_ready": (
                self.operational_terminal_adapter_ready
            ),
            "work_id": self.work.work_id,
            "source_quantities_in_confidence_model_or_certificate": False,
            "caller_rows_law_seed_count_status_policy_callback_accepted": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "epochs": [item.to_document() for item in self.epochs],
            "planner_results": [
                item.to_document() for item in self.planner_results
            ],
            "selector_closures": [
                {
                    "closure_id": item.closure_id,
                    "claim_id": item.claim.claim_id,
                    "attestation_id": (
                        item.independent_attestation.attestation_id
                    ),
                    "outcome": item.claim.decision.outcome.value,
                }
                for item in self.selector_closures
            ],
            "concretizer_policy": [
                item.to_document() for item in self.concretizer_policy
            ],
            "ground_policy": [
                item.to_document() for item in self.ground_policy
            ],
            "work": self.work.to_document(),
            "result_id": self.result_id,
        }


# Name frozen by the operational-terminal adapter protocol.
RegisteredAdaptiveQuotientOccurrenceResultV1 = (
    RegisteredAdaptiveOccurrenceResultV1
)


_VERIFIED_RESULT_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredAdaptiveQuotientVerifiedRuntimeResultV1:
    _minting_capability: object
    execution: RegisteredAdaptiveOccurrenceResultV1
    independent_verification: Any
    _verified_result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from acfqp import (
            v072_registered_adaptive_quotient_runtime_independent_verifier_v1
            as independent,
        )

        if (
            self._minting_capability
            is not _VERIFIED_RESULT_MINTING_SENTINEL
            or type(self.execution) is not RegisteredAdaptiveOccurrenceResultV1
            or type(self.independent_verification)
            is not independent.RegisteredAdaptiveRuntimeIndependentVerificationV1
            or self.independent_verification.result_id
            != self.execution.result_id
        ):
            raise V072RegisteredAdaptiveRuntimeInvariantViolation(
                "verified adaptive runtime result was not independently minted"
            )
        object.__setattr__(
            self,
            "_verified_result_id",
            _content_id(
                "registered_verified_result",
                {
                    "schema": (
                        "acfqp.v072_registered_adaptive_"
                        "verified_runtime_result.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "execution_result_id": self.execution.result_id,
                    "independent_verification_id": (
                        self.independent_verification.verification_id
                    ),
                    "source_quantities_used_in_verification": False,
                },
            ),
        )

    @property
    def result_id(self) -> str:
        return self.execution.result_id

    @property
    def independent_verification_id(self) -> str:
        return self.independent_verification.verification_id

    @property
    def verified_result_id(self) -> str:
        return self._verified_result_id

    @property
    def selected_root_action(self) -> tuple[int, int, int] | None:
        return self.execution.selected_root_action

    @property
    def complete_child_policy(
        self,
    ) -> tuple[RegisteredAdaptiveGroundPolicyDecisionV1, ...]:
        return self.execution.complete_child_policy

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_adaptive_"
                "verified_runtime_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "execution": self.execution.to_document(),
            "independent_verification": (
                self.independent_verification.to_document()
            ),
            "verified_result_id": self.verified_result_id,
        }


def _require_anchor_without_observer_access(
    anchor: Any,
) -> final_authority.V072RemoteMainAnchorV1:
    if (
        type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or final_authority.REMOTE_MAIN_ANCHOR_AUTHORITY_ENABLED is not True
        or anchor.target_execution_allowed is not True
        or type(anchor.claim)
        is not final_authority.V072RemoteMainAnchorClaimV1
        or anchor.claim.verification_scope
        is not (
            final_authority.RemoteMainAnchorVerificationScopeV1
            .REGISTERED_PRODUCTION_CANDIDATE
        )
    ):
        raise RegisteredAdaptiveRuntimeLockedV1(
            "registered adaptive runtime requires the exact enabled "
            "V072RemoteMainAnchorV1",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    return anchor


def _require_authority_chain_without_observer_access(
    *,
    authority_chain: Any,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
) -> consumer.RegisteredCampaignAuthorityChainV1:
    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or authority_chain.remote_main_anchor is not anchor
        or occurrence_plan.chain_id != authority_chain.chain_id
    ):
        raise RegisteredAdaptiveRuntimeLockedV1(
            "registered adaptive runtime requires the exact occurrence-bound "
            "authority chain and identical anchor object",
            access_audit=RegisteredAdaptiveAccessAuditV1(
                anchor_checks=1,
                occurrence_identity_checks=1,
            ),
        )
    try:
        consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (
        consumer.RegisteredCampaignAuthorityGateLockedV1,
        ValueError,
    ) as error:
        raise RegisteredAdaptiveRuntimeLockedV1(
            "registered adaptive authority chain replay failed before "
            "observer access",
            access_audit=RegisteredAdaptiveAccessAuditV1(
                anchor_checks=1,
                occurrence_identity_checks=1,
            ),
        ) from error
    return authority_chain


def run_registered_adaptive_quotient_occurrence_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
) -> RegisteredAdaptiveQuotientVerifiedRuntimeResultV1:
    """Execute and independently verify one registered adaptive occurrence."""

    _require_anchor_without_observer_access(anchor)
    canonical_plan = validate_registered_adaptive_occurrence_identity_v1(
        occurrence_plan=occurrence_plan,
        context=context,
    )
    _require_authority_chain_without_observer_access(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=canonical_plan,
    )
    dependency = inspect_registered_adaptive_dependency_protocol_v1()
    if (
        REGISTERED_RUNTIME_ENABLED is not True
        or dependency.dependencies_available is not True
    ):
        raise RegisteredAdaptiveDependencyBlockedV1(
            "registered adaptive planning dependency is unavailable; blockers="
            + ",".join(dependency.blockers),
            occurrence_plan=canonical_plan,
            dependency_protocol=dependency,
            access_audit=RegisteredAdaptiveAccessAuditV1(
                anchor_checks=1,
                occurrence_identity_checks=1,
                authority_chain_verifications=1,
            ),
        )
    cold_epoch = cold_runtime.build_registered_cold_h2_model_epoch_v1(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=canonical_plan,
        context=context,
    )
    epochs: list[RegisteredProductionModelEpochV1] = [cold_epoch]
    planner_results: list[
        planner.V072ExactLazyPlannerComponentResultV1
    ] = []
    selector_closures: list[selector.RegisteredSelectorClosureV1] = []
    status: RegisteredAdaptiveOccurrenceStatusV1 | None = None

    while status is None:
        epoch = epochs[-1]
        pair = _epoch_model_pair(epoch)
        planned = planner.solve_and_verify_v072_exact_lazy_h2_v1(
            model=pair.quotient_planner_model,
            threshold=pair.threshold_profile,
            solver_kind=robust.RobustSolverKind.QUOTIENT,
        )
        planner_results.append(planned)
        solve = planned.solve_result
        if solve.status is (
            lazy.ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED
        ):
            status = (
                RegisteredAdaptiveOccurrenceStatusV1
                .EXACT_DP_RESOURCE_EXHAUSTED
            )
            break
        audit = solve.audit
        assert audit is not None
        if audit.status is robust.RobustAuditStatus.CERTIFIED:
            status = RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
            break
        completed_rounds = len(epochs) - 1
        if completed_rounds >= MAX_LOCAL_ROUNDS:
            status = (
                RegisteredAdaptiveOccurrenceStatusV1
                .NOT_CERTIFIED_MAX_ROUNDS
            )
            break
        predecessor = (
            None
            if type(epoch) is cold_runtime.RegisteredColdH2ModelEpochV1
            else epoch.frontier
        )
        acquisitions = (
            epoch.acquisitions
            if type(epoch) is cold_runtime.RegisteredColdH2ModelEpochV1
            else epoch.acquisition_history
        )
        closure = selector.prepare_registered_acquisition_frontier_v1(
            authority_chain=authority_chain,
            anchor=anchor,
            occurrence_plan=canonical_plan,
            failed_audit=audit,
            model_pair=pair,
            model_replay_attestation=epoch.model_replay_attestation,
            acquisitions=acquisitions,
            round_index=completed_rounds + 1,
            predecessor_frontier=predecessor,
        )
        selector_closures.append(closure)
        if (
            closure.claim.decision.outcome
            is selector.RegisteredSelectorOutcomeV1.NO_SOUND_COVER
        ):
            status = RegisteredAdaptiveOccurrenceStatusV1.NO_SOUND_COVER
            break
        if (
            closure.claim.decision.outcome
            is selector.RegisteredSelectorOutcomeV1.CAP_EXHAUSTED
        ):
            status = (
                RegisteredAdaptiveOccurrenceStatusV1
                .ACQUISITION_CAP_EXHAUSTED
            )
            break
        next_epoch = (
            incremental.materialize_registered_incremental_h2_model_epoch_v1(
                authority_chain=authority_chain,
                anchor=anchor,
                occurrence_plan=canonical_plan,
                context=context,
                prior_epoch=epoch,
                selector_closure=closure,
            )
        )
        epochs.append(next_epoch)

    assert status is not None
    epoch_tuple = tuple(epochs)
    planner_tuple = tuple(planner_results)
    selector_tuple = tuple(selector_closures)
    if status is RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED:
        final_audit = planner_tuple[-1].solve_result.audit
        assert final_audit is not None
        concretizer_policy, ground_policy = (
            derive_registered_adaptive_policy_support_v1(
                model_pair=_epoch_model_pair(epoch_tuple[-1]),
                audit=final_audit,
            )
        )
        adapter_status = (
            RegisteredAdaptiveGroundAdapterStatusV1
            .SINGLETON_GROUND_POLICY_READY
            if ground_policy
            else RegisteredAdaptiveGroundAdapterStatusV1
            .FIXED_CONCRETIZER_OPERATIONAL_POLICY_SCHEMA_NOT_INTEGRATED
        )
    else:
        concretizer_policy = ()
        ground_policy = ()
        adapter_status = (
            RegisteredAdaptiveGroundAdapterStatusV1
            .NOT_APPLICABLE_NONCERTIFICATE
        )
    execution = RegisteredAdaptiveOccurrenceResultV1(
        _REGISTERED_RESULT_MINTING_SENTINEL,
        authority_chain.chain_id,
        anchor.anchor_id,
        canonical_plan,
        context,
        epoch_tuple,
        planner_tuple,
        selector_tuple,
        status,
        concretizer_policy,
        ground_policy,
        adapter_status,
        _derive_registered_adaptive_work(
            epoch_tuple,
            planner_tuple,
            selector_tuple,
        ),
    )
    return verify_registered_adaptive_quotient_occurrence_result_v1(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=canonical_plan,
        context=context,
        claimed=execution,
    )


def verify_registered_adaptive_quotient_occurrence_result_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
    claimed: RegisteredAdaptiveOccurrenceResultV1,
) -> RegisteredAdaptiveQuotientVerifiedRuntimeResultV1:
    """Independently replay a complete result before minting its wrapper."""

    from acfqp import (
        v072_registered_adaptive_quotient_runtime_independent_verifier_v1
        as independent,
    )

    verification = (
        independent.verify_registered_adaptive_runtime_independently_v1(
            authority_chain=authority_chain,
            anchor=anchor,
            occurrence_plan=occurrence_plan,
            context=context,
            claimed=claimed,
        )
    )
    return RegisteredAdaptiveQuotientVerifiedRuntimeResultV1(
        _VERIFIED_RESULT_MINTING_SENTINEL,
        claimed,
        verification,
    )


__all__ = [
    "ADAPTIVE_ARMS",
    "EVALUATOR_TERMINAL_MINT_BLOCKER",
    "FIXED_CONCRETIZER_OPERATIONAL_POLICY_SCHEMA_BLOCKER",
    "INCREMENTAL_MODEL_EPOCH_BLOCKER",
    "MAX_LOCAL_ROUNDS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_RUNTIME_ENABLED",
    "REGISTERED_RUNTIME_STATUS",
    "RegisteredAdaptiveAccessAuditV1",
    "RegisteredAdaptiveConcretizerDecisionV1",
    "RegisteredAdaptiveDependencyBlockedV1",
    "RegisteredAdaptiveDependencyProtocolV1",
    "RegisteredAdaptiveGroundAdapterStatusV1",
    "RegisteredAdaptiveGroundPolicyDecisionV1",
    "RegisteredAdaptiveOccurrenceResultV1",
    "RegisteredAdaptiveOccurrenceStatusV1",
    "RegisteredAdaptiveOccurrenceWorkV1",
    "RegisteredAdaptiveQuotientOccurrenceResultV1",
    "RegisteredAdaptiveQuotientVerifiedRuntimeResultV1",
    "RegisteredAdaptiveRuntimeLockedV1",
    "RegistrationDisjointAcquisitionPurposeV1",
    "RegistrationDisjointAdaptiveAcquisitionV1",
    "RegistrationDisjointAdaptiveAuditStatusV1",
    "RegistrationDisjointAdaptiveAuditV1",
    "RegistrationDisjointAdaptiveFrontierV1",
    "RegistrationDisjointAdaptiveLocalRoundV1",
    "RegistrationDisjointAdaptiveModelEpochV1",
    "RegistrationDisjointAdaptiveProposalBasisV1",
    "RegistrationDisjointAdaptiveProposalOrderV1",
    "RegistrationDisjointAdaptiveRunV1",
    "RegistrationDisjointAdaptiveTerminalStatusV1",
    "RegistrationDisjointAdaptiveWorkV1",
    "SCHEMA_VERSION",
    "V072RegisteredAdaptiveRuntimeInvariantViolation",
    "ZERO_ACCESS_AUDIT",
    "derive_registered_adaptive_policy_support_v1",
    "inspect_registered_adaptive_dependency_protocol_v1",
    "run_registered_adaptive_quotient_occurrence_v1",
    "run_registration_disjoint_adaptive_state_machine_core_v1",
    "validate_registered_adaptive_occurrence_identity_v1",
    "verify_registered_adaptive_quotient_occurrence_result_v1",
]
