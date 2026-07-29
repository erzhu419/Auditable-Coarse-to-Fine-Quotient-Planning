"""Anchor-first production consumer for the registered V0-072 campaign.

The only execution entry point accepts one exact typed

    source recipe -> manifest -> final preregistration
                  -> independently verified remote-main anchor

chain.  That chain and the compact source-reconstruction recipe are replayed
before any held-out target access.  The consumer then executes the frozen
context-major 3 x 5 schedule, derives plan terminals only from independently
verified route results, evaluates every certified fixed-κ policy exactly,
reconciles all online/replay/evaluation/source lanes, and passes one internally
minted complete bundle to the standalone endpoint verifier.

No injected observer, transition law, seed, terminal, count, route result, or
synthetic campaign control is accepted by the production entry point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_confirmatory_execution_manifest_v1 as manifest
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_source_reconstruction_recipe_v1 as source_recipe
from acfqp import (
    v072_remote_main_anchor_independent_verifier_v1
    as anchor_independent,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_three_context_five_arm_consumer_v1"
REGISTERED_EXECUTION_STATUS = (
    "PRODUCTION_EXECUTOR_INSTALLED_AUTHORITY_CHAIN_REQUIRED"
)
REGISTERED_OBSERVATIONS_GENERATED = 0
SAMPLE_EFFICIENCY_GATE_STATUS = "NOT_RUN"

EXPECTED_CONTEXT_COUNT = 3
EXPECTED_ARM_COUNT = 5
EXPECTED_OCCURRENCE_COUNT = 15
CRN_PAIRING_KEY_FIELDS = (
    "context_id",
    "physical_row_binding_id",
    "arm_free_support_set_id",
    "arm_free_support_lineage_id",
    "round_index",
    "epoch_semantics",
    "lane",
    "checkpoint",
    "random_word_index",
)

DOMAIN_TAGS = {
    "blocker": "acfqp:v072-registered-consumer-capability-blocker:v1",
    "readiness": "acfqp:v072-registered-consumer-readiness:v1",
    "chain": "acfqp:v072-registered-execution-authority-chain:v1",
    "occurrence_template": (
        "acfqp:v072-registered-occurrence-template:v1"
    ),
    "occurrence_plan": "acfqp:v072-registered-occurrence-plan:v1",
    "campaign_plan": "acfqp:v072-registered-campaign-plan:v1",
    "access_audit": "acfqp:v072-registered-access-audit:v1",
    "campaign_result": "acfqp:v072-registered-campaign-result:v1",
}


class V072RegisteredCampaignConsumerInvariantViolation(ValueError):
    """A registered authority, order, plan, or identity is malformed."""


class RegisteredCampaignAuthorityGateLockedV1(RuntimeError):
    """No exact final-preregistration/remote-anchor chain was supplied."""

    def __init__(
        self,
        message: str,
        *,
        access_audit: "RegisteredAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.access_audit = access_audit


class RegisteredCampaignProductionCapabilityBlockedV1(RuntimeError):
    """A post-anchor production-only stage still has a typed blocker."""

    def __init__(
        self,
        message: str,
        *,
        execution_plan: "RegisteredCampaignExecutionPlanV1",
        blockers: tuple["RegisteredProductionCapabilityBlockerV1", ...],
        access_audit: "RegisteredAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.execution_plan = execution_plan
        self.blockers = blockers
        self.access_audit = access_audit


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072RegisteredCampaignConsumerInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredCampaignConsumerInvariantViolation(
            f"{field_name} is not one canonical content ID"
        ) from error


class RegisteredRouteKindV1(str, Enum):
    ADAPTIVE_QUOTIENT = "ADAPTIVE_QUOTIENT"
    MATCHED_DIRECT_GROUND = "MATCHED_DIRECT_GROUND"


class RegisteredArmProposalSemanticsV1(str, Enum):
    SOURCE_FORWARD_MIDRANK = "SOURCE_ARCHIVE_FORWARD_MIDRANK"
    NO_PRIOR = "NO_PRIOR"
    WRONG_REVERSED_MIDRANK = "SOURCE_ARCHIVE_REVERSED_MIDRANK"
    OOD_TYPED_ABSTENTION = "OOD_TYPED_SCHEMA_ABSTENTION_NEUTRAL"
    DIRECT_NOT_APPLICABLE = "MATCHED_DIRECT_NO_SELECTOR"


class RegisteredStageV1(str, Enum):
    AUTHORITY_CHAIN = "AUTHORITY_CHAIN"
    SOURCE_PERSISTENCE = "SOURCE_PERSISTENCE"
    OBSERVER = "OBSERVER"
    CONFIDENCE_PROJECTION = "CONFIDENCE_PROJECTION"
    COLD_H2_BUILD = "COLD_H2_BUILD"
    ADAPTIVE_RECOVERY = "ADAPTIVE_RECOVERY"
    MATCHED_DIRECT = "MATCHED_DIRECT"
    EXACT_EVALUATION = "EXACT_EVALUATION"
    RECONCILIATION = "RECONCILIATION"
    ENDPOINT_VERIFICATION = "ENDPOINT_VERIFICATION"


@dataclass(frozen=True, slots=True)
class RegisteredAccessAuditV1:
    authority_chain_verifications: int = 0
    hidden_law_reads: int = 0
    seed_derivations: int = 0
    splitmix_calls: int = 0
    observer_stream_opens: int = 0
    observer_draw_calls: int = 0
    accepted_observations: int = 0
    confidence_projection_calls: int = 0
    cold_model_build_calls: int = 0
    adaptive_route_calls: int = 0
    matched_direct_calls: int = 0
    exact_evaluation_calls: int = 0
    reconciliation_calls: int = 0
    endpoint_verification_calls: int = 0

    def __post_init__(self) -> None:
        values = tuple(
            getattr(self, name)
            for name in self.__dataclass_fields__
        )
        if any(type(item) is not int or item < 0 for item in values):
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "registered access counters must be nonnegative integers"
            )

    @property
    def target_access_started(self) -> bool:
        return any(
            (
                self.hidden_law_reads,
                self.seed_derivations,
                self.splitmix_calls,
                self.observer_stream_opens,
                self.observer_draw_calls,
                self.accepted_observations,
                self.confidence_projection_calls,
                self.cold_model_build_calls,
                self.adaptive_route_calls,
                self.matched_direct_calls,
                self.exact_evaluation_calls,
                self.reconciliation_calls,
                self.endpoint_verification_calls,
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_access_audit.v1",
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
            "target_access_started": self.target_access_started,
        }

    @property
    def audit_id(self) -> str:
        return _hash("access_audit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


ZERO_ACCESS_AUDIT = RegisteredAccessAuditV1()


@dataclass(frozen=True, slots=True)
class RegisteredProductionCapabilityBlockerV1:
    stage: RegisteredStageV1
    module_name: str
    entrypoint_name: str
    blocker_code: str
    target_access_required: bool

    def __post_init__(self) -> None:
        if (
            type(self.stage) is not RegisteredStageV1
            or type(self.module_name) is not str
            or not self.module_name.startswith("acfqp.")
            or type(self.entrypoint_name) is not str
            or not self.entrypoint_name
            or type(self.blocker_code) is not str
            or not self.blocker_code
            or self.blocker_code != self.blocker_code.upper()
            or any(
                not (character.isupper() or character.isdigit()
                     or character == "_")
                for character in self.blocker_code
            )
            or type(self.target_access_required) is not bool
        ):
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "registered production capability blocker is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_production_capability_blocker.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "stage": self.stage.value,
            "module_name": self.module_name,
            "entrypoint_name": self.entrypoint_name,
            "blocker_code": self.blocker_code,
            "target_access_required": self.target_access_required,
            "injection_can_satisfy": False,
        }

    @property
    def blocker_id(self) -> str:
        return _hash("blocker", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "blocker_id": self.blocker_id}


# Every production-only stage now has one concrete exact implementation.
# The source recipe, final manifest, final preregistration, and remote-main
# anchor remain runtime authorities, not missing code capabilities.  Their
# absence is rejected by ``RegisteredCampaignAuthorityGateLockedV1`` before
# target access.
PRODUCTION_CAPABILITY_BLOCKERS: tuple[
    RegisteredProductionCapabilityBlockerV1, ...
] = ()


@dataclass(frozen=True, slots=True)
class RegisteredOccurrenceTemplateV1:
    context_id: str
    context_key: str
    context_ordinal: int
    arm: str
    arm_ordinal: int
    occurrence_ordinal: int
    route_kind: RegisteredRouteKindV1
    maximum_adaptive_rounds: int

    @property
    def proposal_semantics(
        self,
    ) -> RegisteredArmProposalSemanticsV1:
        return {
            "SOURCE_CONSENSUS_PRIOR": (
                RegisteredArmProposalSemanticsV1
                .SOURCE_FORWARD_MIDRANK
            ),
            "NO_PRIOR": RegisteredArmProposalSemanticsV1.NO_PRIOR,
            "WRONG_CONSENSUS_PRIOR": (
                RegisteredArmProposalSemanticsV1
                .WRONG_REVERSED_MIDRANK
            ),
            "OOD_ABSTENTION": (
                RegisteredArmProposalSemanticsV1.OOD_TYPED_ABSTENTION
            ),
            "MATCHED_DIRECT_GROUND": (
                RegisteredArmProposalSemanticsV1.DIRECT_NOT_APPLICABLE
            ),
        }[self.arm]

    def __post_init__(self) -> None:
        contexts = prereg.registered_heldout_public_contexts_v2()
        expected_route = (
            RegisteredRouteKindV1.MATCHED_DIRECT_GROUND
            if self.arm == "MATCHED_DIRECT_GROUND"
            else RegisteredRouteKindV1.ADAPTIVE_QUOTIENT
        )
        if (
            self.context_ordinal not in range(len(contexts))
            or contexts[self.context_ordinal].context_id
            != _cid(self.context_id, "template context")
            or contexts[self.context_ordinal].context_key
            != self.context_key
            or self.arm_ordinal not in range(len(prereg.ARM_ORDER))
            or prereg.ARM_ORDER[self.arm_ordinal] != self.arm
            or self.occurrence_ordinal
            != self.context_ordinal * len(prereg.ARM_ORDER)
            + self.arm_ordinal
            or type(self.route_kind) is not RegisteredRouteKindV1
            or self.route_kind is not expected_route
            or self.maximum_adaptive_rounds
            != (
                0
                if self.route_kind
                is RegisteredRouteKindV1.MATCHED_DIRECT_GROUND
                else prereg.MAX_ROUNDS
            )
        ):
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "registered occurrence template is reordered or malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_occurrence_template.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "context_key": self.context_key,
            "context_ordinal": self.context_ordinal,
            "arm": self.arm,
            "arm_ordinal": self.arm_ordinal,
            "occurrence_ordinal": self.occurrence_ordinal,
            "route_kind": self.route_kind.value,
            "proposal_semantics": self.proposal_semantics.value,
            "source_quantities_are_proposal_only": self.arm in (
                "SOURCE_CONSENSUS_PRIOR",
                "WRONG_CONSENSUS_PRIOR",
            ),
            "source_quantities_in_confidence_or_certificate": 0,
            "maximum_adaptive_rounds": self.maximum_adaptive_rounds,
            "replacement_allowed": False,
            "campaign_early_stop_allowed": False,
            "round_two_requires_fresh_frontier": (
                self.route_kind
                is RegisteredRouteKindV1.ADAPTIVE_QUOTIENT
            ),
            "crn_pairing_allowed": True,
            "crn_pairing_key_fields": list(CRN_PAIRING_KEY_FIELDS),
            "arm_excluded_from_crn_entropy_key": True,
            "arm_included_in_evidence_and_work_identity": True,
            "crn_draw_discount": 0,
        }

    @property
    def template_id(self) -> str:
        return _hash("occurrence_template", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "template_id": self.template_id}


def registered_occurrence_templates_v1(
) -> tuple[RegisteredOccurrenceTemplateV1, ...]:
    return tuple(
        RegisteredOccurrenceTemplateV1(
            context.context_id,
            context.context_key,
            context_index,
            arm,
            arm_index,
            context_index * len(prereg.ARM_ORDER) + arm_index,
            (
                RegisteredRouteKindV1.MATCHED_DIRECT_GROUND
                if arm == "MATCHED_DIRECT_GROUND"
                else RegisteredRouteKindV1.ADAPTIVE_QUOTIENT
            ),
            0 if arm == "MATCHED_DIRECT_GROUND" else prereg.MAX_ROUNDS,
        )
        for context_index, context in enumerate(
            prereg.registered_heldout_public_contexts_v2()
        )
        for arm_index, arm in enumerate(prereg.ARM_ORDER)
    )


@dataclass(frozen=True, slots=True)
class RegisteredCampaignConsumerReadinessV1:
    occurrence_templates: tuple[RegisteredOccurrenceTemplateV1, ...]
    capability_blockers: tuple[
        RegisteredProductionCapabilityBlockerV1, ...
    ]
    access_audit: RegisteredAccessAuditV1 = ZERO_ACCESS_AUDIT
    final_manifest_available: bool = False
    final_preregistration_available: bool = False
    verified_remote_main_anchor_available: bool = False
    target_execution_allowed: bool = False
    registered_observations_generated: int = 0
    sample_efficiency_gate_status: str = SAMPLE_EFFICIENCY_GATE_STATUS

    def __post_init__(self) -> None:
        expected_templates = registered_occurrence_templates_v1()
        if (
            self.occurrence_templates != expected_templates
            or len(self.occurrence_templates) != EXPECTED_OCCURRENCE_COUNT
            or self.capability_blockers != PRODUCTION_CAPABILITY_BLOCKERS
            or type(self.access_audit) is not RegisteredAccessAuditV1
            or self.access_audit.target_access_started
            or self.final_manifest_available
            or self.final_preregistration_available
            or self.verified_remote_main_anchor_available
            or self.target_execution_allowed
            or self.registered_observations_generated != 0
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "registered consumer readiness overstates execution"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_campaign_consumer_readiness.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "registered_execution_status": REGISTERED_EXECUTION_STATUS,
            "occurrence_template_ids": [
                item.template_id for item in self.occurrence_templates
            ],
            "context_major_frozen_arm_order": True,
            "logical_occurrence_denominator": 15,
            "all_terminal_artifacts_required": True,
            "occurrence_replacement_allowed": False,
            "campaign_early_stop_allowed": False,
            "capability_blocker_ids": [
                item.blocker_id for item in self.capability_blockers
            ],
            "access_audit_id": self.access_audit.audit_id,
            "final_manifest_available": False,
            "final_preregistration_available": False,
            "verified_remote_main_anchor_available": False,
            "target_execution_allowed": False,
            "registered_observations_generated": 0,
            "development_synthetic_transition_authority_allowed": False,
            "injected_observer_allowed": False,
            "caller_supplied_terminal_allowed": False,
            "caller_supplied_counts_allowed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
        }

    @property
    def readiness_id(self) -> str:
        return _hash("readiness", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_templates": [
                item.to_document() for item in self.occurrence_templates
            ],
            "capability_blockers": [
                item.to_document() for item in self.capability_blockers
            ],
            "access_audit": self.access_audit.to_document(),
            "readiness_id": self.readiness_id,
        }


def inspect_registered_campaign_consumer_readiness_v1(
) -> RegisteredCampaignConsumerReadinessV1:
    """Return the zero-access, nonauthorizing production wiring snapshot."""

    return RegisteredCampaignConsumerReadinessV1(
        registered_occurrence_templates_v1(),
        PRODUCTION_CAPABILITY_BLOCKERS,
    )


@dataclass(frozen=True, slots=True)
class RegisteredCampaignAuthorityChainV1:
    """Exact consumer-owned wrapper for the future three-artifact chain."""

    manifest: Any
    final_preregistration: Any
    remote_main_anchor: Any
    remote_main_anchor_attestation: Any
    repository_root: str
    _chain_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        (
            source_reconstruction_recipe_id,
            manifest_id,
            final_preregistration_id,
            anchor_id,
            anchor_attestation_id,
        ) = _verify_exact_authority_chain_v1(self)
        object.__setattr__(
            self,
            "_chain_id",
            _hash(
                "chain",
                {
                    "schema": (
                        "acfqp.v072_registered_execution_authority_chain.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "source_reconstruction_recipe_id": (
                        source_reconstruction_recipe_id
                    ),
                    "manifest_id": manifest_id,
                    "final_preregistration_id":
                        final_preregistration_id,
                    "remote_main_anchor_id": anchor_id,
                    "remote_main_anchor_attestation_id":
                        anchor_attestation_id,
                    "authority_order": [
                        "SOURCE_RECONSTRUCTION_RECIPE",
                        "CONFIRMATORY_EXECUTION_MANIFEST",
                        "FINAL_PREREGISTRATION",
                        "INDEPENDENTLY_VERIFIED_REMOTE_MAIN_ANCHOR",
                    ],
                    "target_access_before_chain_verification": False,
                },
            ),
        )

    @property
    def chain_id(self) -> str:
        return self._chain_id


def _verify_exact_authority_chain_v1(
    chain: RegisteredCampaignAuthorityChainV1,
) -> tuple[str, str, str, str, str]:
    if (
        type(chain.manifest) is not manifest.ConfirmatoryExecutionManifestV1
        or type(chain.final_preregistration)
        is not final_authority.V072FinalPreregistrationV1
        or type(chain.remote_main_anchor)
        is not final_authority.V072RemoteMainAnchorV1
        or type(chain.remote_main_anchor_attestation)
        is not (
            anchor_independent
            .IndependentRemoteMainAnchorAttestationV1
        )
        or type(chain.repository_root) is not str
        or not chain.repository_root
    ):
        raise RegisteredCampaignAuthorityGateLockedV1(
            "registered campaign requires the exact manifest, final "
            "preregistration, remote-main anchor, and independent "
            "attestation types",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    try:
        replayed = (
            anchor_independent
            .verify_remote_main_anchor_claim_independently_v1(
                chain.repository_root,
                chain.remote_main_anchor.claim,
            )
        )
    except (
        anchor_independent.IndependentRemoteMainAnchorVerificationViolation
    ) as error:
        raise RegisteredCampaignAuthorityGateLockedV1(
            "independent remote-main Git/object replay rejected the chain",
            access_audit=ZERO_ACCESS_AUDIT,
        ) from error
    if replayed != chain.remote_main_anchor_attestation:
        raise RegisteredCampaignAuthorityGateLockedV1(
            "remote-main anchor independent attestation is stale",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    source_recipe_id = _cid(
        chain.manifest.global_bindings[
            "source_reconstruction_recipe_id"
        ],
        "source reconstruction recipe",
    )
    manifest_id = _cid(chain.manifest.manifest_id, "final manifest")
    final_id = _cid(
        chain.final_preregistration.final_preregistration_id,
        "final preregistration",
    )
    anchor_id = _cid(
        chain.remote_main_anchor.anchor_id,
        "remote-main anchor",
    )
    attestation_id = _cid(
        replayed.verification_id,
        "remote-main anchor independent attestation",
    )
    production_scope = (
        final_authority.RemoteMainAnchorVerificationScopeV1
        .REGISTERED_PRODUCTION_CANDIDATE
    )
    if (
        chain.final_preregistration.manifest_id != manifest_id
        or chain.remote_main_anchor.claim.source_reconstruction_recipe_id
        != source_recipe_id
        or chain.remote_main_anchor.claim.manifest_id != manifest_id
        or chain.remote_main_anchor.claim.final_preregistration_id
        != final_id
        or chain.remote_main_anchor.independent_semantic_attestation_id
        != attestation_id
        or replayed.verification_scope is not production_scope
        or replayed.claim_id
        != chain.remote_main_anchor.claim.claim_id
        or replayed.source_reconstruction_recipe_id != source_recipe_id
        or replayed.manifest_id != manifest_id
        or replayed.final_preregistration_id != final_id
        or chain.remote_main_anchor.target_execution_allowed is not True
        or replayed.target_execution_allowed is not False
        or replayed.registered_observer_calls != 0
    ):
        raise RegisteredCampaignAuthorityGateLockedV1(
            "manifest/final-preregistration/anchor identity chain is stale, "
            "local-only, or not independently replayed",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    return (
        source_recipe_id,
        manifest_id,
        final_id,
        anchor_id,
        attestation_id,
    )


def verify_registered_campaign_authority_chain_v1(
    chain: Any,
) -> tuple[str, str, str, str, str]:
    """Public nonobserving replay of the exact production authority chain."""

    if type(chain) is not RegisteredCampaignAuthorityChainV1:
        raise RegisteredCampaignAuthorityGateLockedV1(
            "registered authority replay requires the exact chain type",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    return _verify_exact_authority_chain_v1(chain)


@dataclass(frozen=True, slots=True)
class RegisteredOccurrenceExecutionPlanV1:
    chain_id: str
    template: RegisteredOccurrenceTemplateV1
    occurrence_id: str = field(init=False)

    def __post_init__(self) -> None:
        _cid(self.chain_id, "occurrence authority chain")
        if type(self.template) is not RegisteredOccurrenceTemplateV1:
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "occurrence plan requires one exact frozen template"
            )
        object.__setattr__(
            self,
            "occurrence_id",
            _hash(
                "occurrence_plan",
                {
                    "schema": (
                        "acfqp.v072_registered_occurrence_execution_plan.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "authority_chain_id": self.chain_id,
                    "template_id": self.template.template_id,
                    "context_id": self.template.context_id,
                    "arm": self.template.arm,
                    "occurrence_ordinal":
                        self.template.occurrence_ordinal,
                    "replacement_allowed": False,
                },
            ),
        )


@dataclass(frozen=True, slots=True)
class RegisteredCampaignExecutionPlanV1:
    authority_chain_id: str
    occurrences: tuple[RegisteredOccurrenceExecutionPlanV1, ...]
    plan_id: str = field(init=False)

    def __post_init__(self) -> None:
        _cid(self.authority_chain_id, "campaign authority chain")
        templates = registered_occurrence_templates_v1()
        if (
            type(self.occurrences) is not tuple
            or len(self.occurrences) != EXPECTED_OCCURRENCE_COUNT
            or any(
                type(item) is not RegisteredOccurrenceExecutionPlanV1
                or item.chain_id != self.authority_chain_id
                or item.template != template
                for item, template in zip(
                    self.occurrences,
                    templates,
                    strict=True,
                )
            )
            or len({item.occurrence_id for item in self.occurrences}) != 15
        ):
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "registered campaign plan skipped, reordered, or replaced "
                "an occurrence"
            )
        object.__setattr__(
            self,
            "plan_id",
            _hash(
                "campaign_plan",
                {
                    "schema": (
                        "acfqp.v072_registered_campaign_execution_plan.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "authority_chain_id": self.authority_chain_id,
                    "occurrence_ids": [
                        item.occurrence_id for item in self.occurrences
                    ],
                    "order": "CONTEXT_MAJOR_THEN_FROZEN_ARM_ORDER",
                    "logical_occurrence_denominator": 15,
                    "replacement_allowed": False,
                    "campaign_early_stop_allowed": False,
                    "crn_cost_discount_draws": 0,
                    "crn_pairing_key_fields": list(
                        CRN_PAIRING_KEY_FIELDS
                    ),
                    "paired_words_do_not_deduplicate_draws_or_work":
                        True,
                },
            ),
        )


def _execution_plan_v1(
    chain: RegisteredCampaignAuthorityChainV1,
) -> RegisteredCampaignExecutionPlanV1:
    return RegisteredCampaignExecutionPlanV1(
        chain.chain_id,
        tuple(
            RegisteredOccurrenceExecutionPlanV1(
                chain.chain_id,
                template,
            )
            for template in registered_occurrence_templates_v1()
        ),
    )


def prepare_registered_campaign_execution_plan_v1(
    authority_chain: Any,
) -> RegisteredCampaignExecutionPlanV1:
    """Derive the immutable schedule without opening source or target data."""

    if type(authority_chain) is not RegisteredCampaignAuthorityChainV1:
        raise RegisteredCampaignAuthorityGateLockedV1(
            "campaign-plan preparation requires one exact authority chain",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    return _execution_plan_v1(authority_chain)


def _load_and_replay_source_recipe_v1(
    authority_chain: RegisteredCampaignAuthorityChainV1,
) -> source_recipe.SourceReconstructionReplayV1:
    """Validate and reuse the exact source replay paid by finalization."""

    root = Path(authority_chain.repository_root)
    if (
        not root.is_absolute()
        or not root.is_dir()
        or root.is_symlink()
    ):
        raise RegisteredCampaignAuthorityGateLockedV1(
            "registered source replay requires one absolute non-symlink "
            "repository root",
            access_audit=RegisteredAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    recipe_path = (
        root / manifest.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
    )
    try:
        recipe = source_recipe.load_source_reconstruction_recipe_v1(
            recipe_path
        )
        expected_recipe_id = _cid(
            authority_chain.manifest.global_bindings[
                "source_reconstruction_recipe_id"
            ],
            "chain-bound source recipe",
        )
        if recipe.recipe_id != expected_recipe_id:
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "loaded source recipe differs from the final manifest"
            )
        already_paid = (
            authority_chain.manifest.source_reconstruction_replay
        )
        if already_paid.recipe_id != recipe.recipe_id:
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "final-manifest source replay differs from its recipe"
            )
        replay = already_paid
    except (
        OSError,
        ValueError,
        source_recipe.V072SourceReconstructionRecipeInvariantViolation,
    ) as error:
        raise RegisteredCampaignAuthorityGateLockedV1(
            "chain-bound source reconstruction failed before held-out "
            "target access",
            access_audit=RegisteredAccessAuditV1(
                authority_chain_verifications=1
            ),
        ) from error
    if replay.recipe_id != expected_recipe_id:
        raise RegisteredCampaignAuthorityGateLockedV1(
            "source reconstruction replay returned a stale recipe identity",
            access_audit=RegisteredAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    return replay


def _execute_registered_occurrences_v1(
    *,
    authority_chain: RegisteredCampaignAuthorityChainV1,
    execution_plan: RegisteredCampaignExecutionPlanV1,
) -> tuple[tuple[Any, ...], tuple[Any | None, ...], tuple[Any | None, ...]]:
    """Execute the immutable 15-occurrence schedule without injection."""

    # Lazy imports are required because every route authority binds the exact
    # consumer-owned occurrence types.
    from acfqp import v072_registered_adaptive_quotient_runtime_v1 as adaptive
    from acfqp import v072_registered_matched_direct_runtime_v1 as direct
    from acfqp import (
        v072_registered_operational_terminal_authority_v1 as terminal,
    )
    from acfqp import v072_independent_exact_ground_evaluator_v1 as evaluator
    from acfqp import (
        v072_registered_campaign_attempt_journal_v1 as attempt_journal,
    )

    anchor = authority_chain.remote_main_anchor
    contexts = {
        item.context_id: item
        for item in prereg.registered_heldout_public_contexts_v2()
    }
    route_results: list[Any] = []
    terminal_authorities: list[Any | None] = []
    exact_evaluations: list[Any | None] = []
    journal = attempt_journal.active_attempt_journal_v1(
        authority_chain=authority_chain,
        execution_plan=execution_plan,
    )

    for occurrence_plan in execution_plan.occurrences:
        context = contexts[occurrence_plan.template.context_id]
        terminal_occurrence_plan: Any = occurrence_plan
        if journal is not None:
            journal.begin_occurrence(occurrence_plan)
        if (
            occurrence_plan.template.route_kind
            is RegisteredRouteKindV1.ADAPTIVE_QUOTIENT
        ):
            route_result = (
                adaptive.run_registered_adaptive_quotient_occurrence_v1(
                    authority_chain=authority_chain,
                    anchor=anchor,
                    occurrence_plan=occurrence_plan,
                    context=context,
                )
            )
            certified = (
                route_result.execution.status
                is adaptive.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
            )
        elif (
            occurrence_plan.template.route_kind
            is RegisteredRouteKindV1.MATCHED_DIRECT_GROUND
        ):
            terminal_occurrence_plan = (
                direct.registered_matched_direct_occurrence_plan_v1(
                    anchor=anchor,
                    context=context,
                )
            )
            route_result = (
                direct.run_registered_matched_direct_occurrence_v1(
                    authority_chain=authority_chain,
                    anchor=anchor,
                    occurrence_plan=terminal_occurrence_plan,
                    context=context,
                )
            )
            certified = (
                route_result.terminal_class
                is direct.RegisteredMatchedDirectTerminalClassV1.PLAN_CERTIFICATE
            )
        else:
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "registered occurrence has an unknown route kind"
            )

        if not certified:
            terminal_authority = None
            exact_evaluation = None
            if journal is not None:
                journal.complete_occurrence(
                    occurrence_plan=occurrence_plan,
                    route_result=route_result,
                    terminal_authority=None,
                    exact_evaluation=None,
                )
            route_results.append(route_result)
            terminal_authorities.append(terminal_authority)
            exact_evaluations.append(exact_evaluation)
            continue

        terminal_authority = (
            terminal.derive_registered_operational_terminal_authority_v1(
                authority_chain=authority_chain,
                anchor=anchor,
                occurrence_plan=terminal_occurrence_plan,
                context=context,
                verified_runtime_result=route_result,
            )
        )
        bundle = terminal_authority.evaluator_bundle
        exact_evaluation = (
            evaluator.evaluate_registered_independent_exact_ground_v1(
                anchor=anchor,
                context=context,
                operational_terminal=bundle.operational_terminal,
                selected_policy=bundle.selected_policy,
            )
        )
        if exact_evaluation.certificate_metrics_pass is not True:
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "a route-native plan certificate failed independent exact "
                "risk/regret evaluation"
            )
        if journal is not None:
            journal.complete_occurrence(
                occurrence_plan=occurrence_plan,
                route_result=route_result,
                terminal_authority=terminal_authority,
                exact_evaluation=exact_evaluation,
            )
        route_results.append(route_result)
        terminal_authorities.append(terminal_authority)
        exact_evaluations.append(exact_evaluation)

    output = (
        tuple(route_results),
        tuple(terminal_authorities),
        tuple(exact_evaluations),
    )
    if any(len(items) != EXPECTED_OCCURRENCE_COUNT for items in output):
        raise V072RegisteredCampaignConsumerInvariantViolation(
            "registered executor skipped or replaced an occurrence"
        )
    return output


def _derive_execution_access_audit_v1(
    *,
    route_results: tuple[Any, ...],
    exact_evaluations: tuple[Any | None, ...],
    endpoint_verification_calls: int,
) -> RegisteredAccessAuditV1:
    """Derive the consumer-level access summary from native route records."""

    from acfqp import v072_registered_adaptive_quotient_runtime_v1 as adaptive
    from acfqp import v072_registered_matched_direct_runtime_v1 as direct

    adaptive_results = tuple(
        item
        for item in route_results
        if type(item)
        is adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1
    )
    direct_results = tuple(
        item
        for item in route_results
        if type(item) is direct.RegisteredMatchedDirectOccurrenceResultV1
    )
    if (
        len(adaptive_results) != 12
        or len(direct_results) != 3
        or len(adaptive_results) + len(direct_results)
        != EXPECTED_OCCURRENCE_COUNT
    ):
        raise V072RegisteredCampaignConsumerInvariantViolation(
            "consumer access audit saw the wrong route multiplicities"
        )
    adaptive_work = tuple(item.execution.work for item in adaptive_results)
    direct_access = tuple(item.access_audit for item in direct_results)
    stream_opens = (
        sum(
            item.producer_stream_opens + item.replay_stream_opens
            for item in adaptive_work
        )
        + sum(item.observer_stream_opens for item in direct_access)
    )
    draw_calls = (
        sum(item.total_observer_draw_calls for item in adaptive_work)
        + sum(item.observer_draw_calls for item in direct_access)
    )
    accepted = (
        sum(item.unique_online_sample_evidence_draws for item in adaptive_work)
        + sum(item.accepted_observations for item in direct_access)
    )
    evaluation_count = sum(item is not None for item in exact_evaluations)
    return RegisteredAccessAuditV1(
        authority_chain_verifications=1,
        hidden_law_reads=draw_calls,
        seed_derivations=stream_opens,
        splitmix_calls=draw_calls,
        observer_stream_opens=stream_opens,
        observer_draw_calls=draw_calls,
        accepted_observations=accepted,
        confidence_projection_calls=sum(
            item.confidence_projection_calls for item in adaptive_work
        ),
        cold_model_build_calls=sum(
            item.cold_epoch_builds for item in adaptive_work
        ),
        adaptive_route_calls=len(adaptive_results),
        matched_direct_calls=len(direct_results),
        exact_evaluation_calls=evaluation_count,
        reconciliation_calls=1,
        endpoint_verification_calls=endpoint_verification_calls,
    )


@dataclass(frozen=True, slots=True)
class RegisteredCampaignExecutionResultV1:
    """One complete production execution and its standalone endpoint replay."""

    execution_plan: RegisteredCampaignExecutionPlanV1
    complete_bundle: Any
    endpoint_verification: Any
    access_audit: RegisteredAccessAuditV1
    _execution_result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from acfqp import (
            v072_registered_complete_bundle_endpoint_verifier_v1 as endpoint,
        )

        if (
            type(self.execution_plan)
            is not RegisteredCampaignExecutionPlanV1
            or type(self.complete_bundle)
            is not endpoint.RegisteredCampaignCompleteBundleV1
            or self.complete_bundle.execution_plan != self.execution_plan
            or type(self.endpoint_verification)
            is not endpoint.RegisteredCompleteBundleEndpointVerificationV1
            or self.endpoint_verification.bundle_id
            != self.complete_bundle.bundle_id
            or self.endpoint_verification.execution_plan_id
            != self.execution_plan.plan_id
            or self.endpoint_verification.logical_occurrence_denominator
            != EXPECTED_OCCURRENCE_COUNT
            or self.endpoint_verification.registered_v072_endpoints_pass
            is not True
            or type(self.access_audit) is not RegisteredAccessAuditV1
            or self.access_audit.adaptive_route_calls != 12
            or self.access_audit.matched_direct_calls != 3
            or self.access_audit.reconciliation_calls != 1
            or self.access_audit.endpoint_verification_calls != 1
        ):
            raise V072RegisteredCampaignConsumerInvariantViolation(
                "registered campaign result is partial, stale, or lacks the "
                "independently verified V0-072 endpoints"
            )
        object.__setattr__(
            self,
            "_execution_result_id",
            _hash(
                "campaign_result",
                {
                    "schema": (
                        "acfqp.v072_registered_campaign_execution_result.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "execution_plan_id": self.execution_plan.plan_id,
                    "complete_bundle_id": self.complete_bundle.bundle_id,
                    "endpoint_verification_id": (
                        self.endpoint_verification.verification_id
                    ),
                    "access_audit_id": self.access_audit.audit_id,
                    "logical_occurrence_denominator": 15,
                    "broad_sample_efficiency_claimed": False,
                    "total_objective_claimed": False,
                },
            ),
        )

    @property
    def execution_result_id(self) -> str:
        return self._execution_result_id

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_campaign_execution_result.v1",
            "schema_version": SCHEMA_VERSION,
            "execution_plan_id": self.execution_plan.plan_id,
            "complete_bundle": self.complete_bundle.to_document(),
            "endpoint_verification": (
                self.endpoint_verification.to_document()
            ),
            "access_audit": self.access_audit.to_document(),
            "logical_occurrence_denominator": 15,
            "broad_sample_efficiency_claimed": False,
            "total_objective_claimed": False,
            "execution_result_id": self.execution_result_id,
        }


def run_registered_v072_campaign_v1(
    *,
    authority_chain: Any,
) -> Any:
    """Execute, reconcile, and independently verify the registered campaign."""

    if type(authority_chain) is not RegisteredCampaignAuthorityChainV1:
        raise RegisteredCampaignAuthorityGateLockedV1(
            "registered campaign entry requires one exact typed authority "
            "chain; placeholders, local-only claims, and duck types are "
            "nonauthorizing",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    _verify_exact_authority_chain_v1(authority_chain)
    execution_plan = prepare_registered_campaign_execution_plan_v1(
        authority_chain
    )
    if PRODUCTION_CAPABILITY_BLOCKERS:
        raise RegisteredCampaignProductionCapabilityBlockedV1(
            "exact anchor chain passed, but registered-only production "
            "capabilities remain blocked; no observer was opened",
            execution_plan=execution_plan,
            blockers=PRODUCTION_CAPABILITY_BLOCKERS,
            access_audit=RegisteredAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    source_replay = _load_and_replay_source_recipe_v1(authority_chain)
    (
        route_results,
        operational_terminal_authorities,
        exact_evaluations,
    ) = _execute_registered_occurrences_v1(
        authority_chain=authority_chain,
        execution_plan=execution_plan,
    )
    from acfqp import v072_registered_campaign_reconciliation_v1 as reconcile
    from acfqp import (
        v072_registered_campaign_reconciliation_independent_verifier_v1
        as reconcile_independent,
    )
    from acfqp import (
        v072_registered_complete_bundle_endpoint_verifier_v1 as endpoint,
    )

    reconciliation = reconcile.reconcile_registered_v072_campaign_v1(
        authority_chain=authority_chain,
        execution_plan=execution_plan,
        route_results=route_results,
        operational_terminal_authorities=(
            operational_terminal_authorities
        ),
        exact_evaluations=exact_evaluations,
        source_reconstruction_replay=source_replay,
    )
    reconciliation_attestation = (
        reconcile_independent
        .verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=authority_chain,
            execution_plan=execution_plan,
            source_reconstruction_replay=source_replay,
            claimed=reconciliation,
        )
    )
    complete_bundle = endpoint.mint_registered_v072_complete_bundle_v1(
        authority_chain=authority_chain,
        execution_plan=execution_plan,
        source_reconstruction_replay=source_replay,
        route_results=route_results,
        operational_terminal_authorities=(
            operational_terminal_authorities
        ),
        exact_evaluations=exact_evaluations,
        reconciliation=reconciliation,
        reconciliation_attestation=reconciliation_attestation,
    )
    endpoint_verification = (
        endpoint.verify_registered_v072_complete_bundle_v1(
            bundle=complete_bundle
        )
    )
    access_audit = _derive_execution_access_audit_v1(
        route_results=route_results,
        exact_evaluations=exact_evaluations,
        endpoint_verification_calls=1,
    )
    return RegisteredCampaignExecutionResultV1(
        execution_plan,
        complete_bundle,
        endpoint_verification,
        access_audit,
    )


__all__ = [
    "EXPECTED_OCCURRENCE_COUNT",
    "CRN_PAIRING_KEY_FIELDS",
    "PROFILE_KEY",
    "PRODUCTION_CAPABILITY_BLOCKERS",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_EXECUTION_STATUS",
    "REGISTERED_OBSERVATIONS_GENERATED",
    "RegisteredAccessAuditV1",
    "RegisteredArmProposalSemanticsV1",
    "RegisteredCampaignAuthorityChainV1",
    "RegisteredCampaignAuthorityGateLockedV1",
    "RegisteredCampaignConsumerReadinessV1",
    "RegisteredCampaignExecutionResultV1",
    "RegisteredCampaignExecutionPlanV1",
    "RegisteredCampaignProductionCapabilityBlockedV1",
    "RegisteredOccurrenceExecutionPlanV1",
    "RegisteredOccurrenceTemplateV1",
    "RegisteredProductionCapabilityBlockerV1",
    "RegisteredRouteKindV1",
    "RegisteredStageV1",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "V072RegisteredCampaignConsumerInvariantViolation",
    "ZERO_ACCESS_AUDIT",
    "inspect_registered_campaign_consumer_readiness_v1",
    "prepare_registered_campaign_execution_plan_v1",
    "registered_occurrence_templates_v1",
    "run_registered_v072_campaign_v1",
    "verify_registered_campaign_authority_chain_v1",
]
