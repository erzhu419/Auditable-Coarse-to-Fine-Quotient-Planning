"""Private authority for registered operational terminals and policies.

Only an independently replayed route-runtime result may reach the evaluator
factory.  Adaptive semantic decisions retain their complete fixed uniform
concretizer support.  Matched-direct deterministic decisions are represented
as singleton concretizers.  No caller can supply a terminal code, status,
policy, value, risk, support, or weight to the production mint.

The registration-disjoint core exercises the complete authority semantics
without minting production capabilities or touching the registered target.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_independent_exact_ground_evaluator_v1 as evaluator
from acfqp import v072_registered_campaign_consumer_v1 as consumer


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_operational_terminal_authority_v1"

ADAPTIVE_RUNTIME_ADAPTER_BLOCKER = None
DIRECT_RUNTIME_ADAPTER_BLOCKER = None
PRODUCTION_ADAPTERS_AVAILABLE = True


class V072RegisteredOperationalTerminalAuthorityViolation(ValueError):
    """An authority, occurrence, runtime, policy, or terminal invariant failed."""


class RegisteredOperationalTerminalAuthorityLockedV1(RuntimeError):
    """Production authority inputs are absent, stale, or unauthorized."""

    def __init__(
        self,
        message: str,
        *,
        access_audit: "RegisteredOperationalTerminalAuthorityAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.access_audit = access_audit


class RegisteredRuntimeResultAdapterDependencyBlockedV1(RuntimeError):
    """The route-specific verified production result adapter is unavailable."""

    def __init__(
        self,
        message: str,
        *,
        adapter_protocol: "RegisteredRuntimeResultAdapterProtocolV1",
        access_audit: "RegisteredOperationalTerminalAuthorityAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.adapter_protocol = adapter_protocol
        self.access_audit = access_audit


DOMAIN_TAGS = {
    "access": (
        "acfqp:v072-registered-operational-terminal-authority-access:v1"
    ),
    "protocol": (
        "acfqp:v072-registered-runtime-result-adapter-protocol:v1"
    ),
    "adapter": (
        "acfqp:v072-registered-verified-runtime-result-adapter:v1"
    ),
    "kappa_spec": (
        "acfqp:v072-registered-verified-kappa-decision-spec:v1"
    ),
    "mint_authority": (
        "acfqp:v072-registered-evaluator-terminal-mint-authority:v1"
    ),
    "authority_result": (
        "acfqp:v072-registered-operational-terminal-authority-result:v1"
    ),
    "synthetic_occurrence": (
        "acfqp:v072-registration-disjoint-terminal-occurrence:v1"
    ),
    "synthetic_child": (
        "acfqp:v072-registration-disjoint-terminal-child-decision:v1"
    ),
    "synthetic_runtime": (
        "acfqp:v072-registration-disjoint-verified-runtime-result:v1"
    ),
    "synthetic_runtime_verification": (
        "acfqp:v072-registration-disjoint-runtime-result-verification:v1"
    ),
    "synthetic_policy": (
        "acfqp:v072-registration-disjoint-operational-policy:v1"
    ),
    "synthetic_terminal": (
        "acfqp:v072-registration-disjoint-operational-terminal:v1"
    ),
    "synthetic_commitment": (
        "acfqp:v072-registration-disjoint-terminal-commitment:v1"
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
        raise V072RegisteredOperationalTerminalAuthorityViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredOperationalTerminalAuthorityViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _action(value: Any, field_name: str) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
    ):
        raise V072RegisteredOperationalTerminalAuthorityViolation(
            f"{field_name} must be one exact integer action triple"
        )
    return value


@dataclass(frozen=True, slots=True)
class RegisteredOperationalTerminalAuthorityAccessAuditV1:
    anchor_checks: int = 0
    authority_chain_verifications: int = 0
    occurrence_identity_checks: int = 0
    verified_runtime_adapter_checks: int = 0
    evaluator_factory_calls: int = 0
    observer_stream_opens: int = 0
    observer_draw_calls: int = 0
    evaluation_exact_atom_calls: int = 0

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0
            for value in (
                getattr(self, name)
                for name in self.__dataclass_fields__
            )
        ):
            raise V072RegisteredOperationalTerminalAuthorityViolation(
                "terminal authority access counters are malformed"
            )

    @property
    def target_access_started(self) -> bool:
        return any(
            (
                self.observer_stream_opens,
                self.observer_draw_calls,
                self.evaluation_exact_atom_calls,
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_operational_terminal_"
                "authority_access.v1"
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


ZERO_ACCESS_AUDIT = RegisteredOperationalTerminalAuthorityAccessAuditV1()


@dataclass(frozen=True, slots=True)
class RegisteredRuntimeResultAdapterProtocolV1:
    adaptive_runtime_module: str = (
        "acfqp.v072_registered_adaptive_quotient_runtime_v1"
    )
    adaptive_runtime_result_type: str = (
        "RegisteredAdaptiveQuotientVerifiedRuntimeResultV1"
    )
    adaptive_runtime_verifier_entrypoint: str = (
        "verify_registered_adaptive_quotient_occurrence_result_v1"
    )
    direct_runtime_module: str = (
        "acfqp.v072_registered_matched_direct_runtime_v1"
    )
    direct_runtime_result_type: str = (
        "RegisteredMatchedDirectOccurrenceResultV1"
    )
    direct_runtime_verifier_entrypoint: str = (
        "verify_registered_matched_direct_occurrence_result_v1"
    )
    evaluator_factory_entrypoint: str = (
        "acfqp.v072_independent_exact_ground_evaluator_v1."
        "mint_registered_occurrence_operational_terminal_policy_v1"
    )
    blockers: tuple[str, ...] = ()
    production_adapters_available: bool = True

    def __post_init__(self) -> None:
        if any(
            getattr(self, name) != definition.default
            for name, definition in self.__dataclass_fields__.items()
        ):
            raise V072RegisteredOperationalTerminalAuthorityViolation(
                "registered runtime-result adapter protocol changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_runtime_result_adapter_protocol.v1"
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
            "terminal_status_or_policy_caller_injection_allowed": False,
            "value_or_risk_caller_injection_allowed": False,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("protocol", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


def inspect_registered_runtime_result_adapter_protocol_v1(
) -> RegisteredRuntimeResultAdapterProtocolV1:
    return RegisteredRuntimeResultAdapterProtocolV1()


_VERIFIED_RUNTIME_ADAPTER_SENTINEL = object()
_VERIFIED_KAPPA_SPEC_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredVerifiedKappaDecisionSpecV1:
    """Private, verifier-derived realization spec consumed by the evaluator."""

    _minting_capability: object
    ground_state_id: str
    public_state_id: str
    state_ranks: tuple[int, ...]
    remaining_horizon: int
    semantic_action_id: str
    ground_action_ids: tuple[str, ...]
    ground_semantic_action_ids: tuple[str, ...]
    ground_actions: tuple[tuple[int, int, int], ...]
    uniform_weights: tuple[Fraction, ...]
    source_action_realization_artifact_id: str
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.ground_state_id, "verified kappa ground state"),
            (self.public_state_id, "verified kappa public state"),
            (self.semantic_action_id, "verified kappa semantic action"),
            (
                self.source_action_realization_artifact_id,
                "verified kappa source",
            ),
            *(
                (item, "verified kappa action")
                for item in self.ground_action_ids
            ),
            *(
                (item, "verified kappa semantic action")
                for item in self.ground_semantic_action_ids
            ),
        ):
            _cid(value, label)
        if type(self.ground_actions) is tuple:
            for action in self.ground_actions:
                _action(action, "verified kappa action")
        support_size = len(self.ground_action_ids)
        if (
            self._minting_capability is not _VERIFIED_KAPPA_SPEC_SENTINEL
            or type(self.state_ranks) is not tuple
            or len(self.state_ranks) != 7
            or any(
                type(item) is not int
                or not 0 <= item <= prereg.RANK_CAP
                for item in self.state_ranks
            )
            or self.remaining_horizon not in (1, prereg.HORIZON)
            or type(self.ground_action_ids) is not tuple
            or self.ground_action_ids
            != tuple(sorted(set(self.ground_action_ids)))
            or support_size == 0
            or type(self.ground_semantic_action_ids) is not tuple
            or len(self.ground_semantic_action_ids) != support_size
            or len(set(self.ground_semantic_action_ids)) != support_size
            or type(self.ground_actions) is not tuple
            or len(self.ground_actions) != support_size
            or len(set(self.ground_actions)) != support_size
            or type(self.uniform_weights) is not tuple
            or self.uniform_weights
            != tuple(Fraction(1, support_size) for _ in range(support_size))
        ):
            raise RegisteredOperationalTerminalAuthorityLockedV1(
                "verified fixed-kappa support is malformed",
                access_audit=ZERO_ACCESS_AUDIT,
            )
        object.__setattr__(
            self,
            "_spec_id",
            _content_id("kappa_spec", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_verified_kappa_decision_spec.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "ground_state_id": self.ground_state_id,
            "public_state_id": self.public_state_id,
            "state_ranks": list(self.state_ranks),
            "remaining_horizon": self.remaining_horizon,
            "semantic_action_id": self.semantic_action_id,
            "ground_action_ids": list(self.ground_action_ids),
            "ground_semantic_action_ids": list(
                self.ground_semantic_action_ids
            ),
            "ground_actions": [list(item) for item in self.ground_actions],
            "uniform_weights": [
                {"numerator": item.numerator, "denominator": item.denominator}
                for item in self.uniform_weights
            ],
            "source_action_realization_artifact_id": (
                self.source_action_realization_artifact_id
            ),
            "fixed_concretizer": True,
            "policy_randomization": False,
        }

    @property
    def spec_id(self) -> str:
        return self._spec_id


@dataclass(frozen=True, slots=True)
class RegisteredVerifiedOccurrenceRuntimeAdapterV1:
    """Private output of one route-specific independent verifier."""

    _minting_capability: object
    route_kind: consumer.RegisteredRouteKindV1
    occurrence: evaluator.RegisteredOccurrenceIdentityV1
    operational_result_artifact_id: str
    independent_runtime_verification_id: str
    root_decision: RegisteredVerifiedKappaDecisionSpecV1
    child_decisions: tuple[RegisteredVerifiedKappaDecisionSpecV1, ...]
    _adapter_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (
                self.operational_result_artifact_id,
                "verified operational runtime result",
            ),
            (
                self.independent_runtime_verification_id,
                "independent runtime verification",
            ),
        ):
            _cid(value, label)
        if (
            self._minting_capability
            is not _VERIFIED_RUNTIME_ADAPTER_SENTINEL
            or type(self.route_kind)
            is not consumer.RegisteredRouteKindV1
            or type(self.occurrence)
            is not evaluator.RegisteredOccurrenceIdentityV1
        ):
            raise RegisteredOperationalTerminalAuthorityLockedV1(
                "REGISTERED_VERIFIED_ROUTE_RUNTIME_REQUIRED",
                access_audit=ZERO_ACCESS_AUDIT,
            )
        direct = self.occurrence.arm == "MATCHED_DIRECT_GROUND"
        if (
            direct
            != (
                self.route_kind
                is consumer.RegisteredRouteKindV1.MATCHED_DIRECT_GROUND
            )
            or (
                not direct
                and self.occurrence.arm not in prereg.ARM_ORDER[:-1]
            )
            or type(self.root_decision)
            is not RegisteredVerifiedKappaDecisionSpecV1
            or self.root_decision.remaining_horizon != prereg.HORIZON
            or type(self.child_decisions) is not tuple
            or any(
                type(item) is not RegisteredVerifiedKappaDecisionSpecV1
                or item.remaining_horizon != 1
                for item in self.child_decisions
            )
            or tuple(
                (item.state_ranks, item.semantic_action_id)
                for item in self.child_decisions
            )
            != tuple(
                sorted(
                    {
                        (item.state_ranks, item.semantic_action_id)
                        for item in self.child_decisions
                    }
                )
            )
            or len({item.public_state_id for item in self.child_decisions})
            != len(self.child_decisions)
            or (
                direct
                and (
                    len(self.root_decision.ground_actions) != 1
                    or any(
                        len(item.ground_actions) != 1
                        for item in self.child_decisions
                    )
                )
            )
        ):
            raise RegisteredOperationalTerminalAuthorityLockedV1(
                "REGISTERED_VERIFIED_ROUTE_RUNTIME_REQUIRED",
                access_audit=ZERO_ACCESS_AUDIT,
            )
        object.__setattr__(
            self,
            "_adapter_id",
            _content_id("adapter", self._payload()),
        )

    @property
    def terminal_code(self) -> str:
        return "CONDITIONAL_PLAN_CERTIFICATE"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_verified_runtime_result_adapter.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "route_kind": self.route_kind.value,
            "occurrence_id": self.occurrence.occurrence_id,
            "operational_result_artifact_id": (
                self.operational_result_artifact_id
            ),
            "independent_runtime_verification_id": (
                self.independent_runtime_verification_id
            ),
            "root_decision_spec_id": self.root_decision.spec_id,
            "child_decision_ids": [
                item.spec_id for item in self.child_decisions
            ],
            "terminal_code": self.terminal_code,
            "runtime_status_independently_recomputed": True,
            "policy_extracted_from_verified_runtime": True,
            "caller_terminal_status_or_policy_accepted": False,
        }

    @property
    def adapter_id(self) -> str:
        return self._adapter_id


_EVALUATOR_MINT_AUTHORITY_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredEvaluatorTerminalMintAuthorityV1:
    """Private single-role authority consumed only by the evaluator factory."""

    _minting_capability: object
    verified_runtime: RegisteredVerifiedOccurrenceRuntimeAdapterV1
    _mint_authority_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._minting_capability
            is not _EVALUATOR_MINT_AUTHORITY_SENTINEL
            or type(self.verified_runtime)
            is not RegisteredVerifiedOccurrenceRuntimeAdapterV1
        ):
            raise RegisteredOperationalTerminalAuthorityLockedV1(
                "REGISTERED_VERIFIED_ROUTE_RUNTIME_REQUIRED",
                access_audit=ZERO_ACCESS_AUDIT,
            )
        object.__setattr__(
            self,
            "_mint_authority_id",
            _content_id("mint_authority", self._payload()),
        )

    @property
    def occurrence(self) -> evaluator.RegisteredOccurrenceIdentityV1:
        return self.verified_runtime.occurrence

    @property
    def operational_result_artifact_id(self) -> str:
        return self.verified_runtime.operational_result_artifact_id

    @property
    def route_kind(self) -> consumer.RegisteredRouteKindV1:
        return self.verified_runtime.route_kind

    @property
    def independent_runtime_verification_id(self) -> str:
        return self.verified_runtime.independent_runtime_verification_id

    @property
    def root_decision(self) -> RegisteredVerifiedKappaDecisionSpecV1:
        return self.verified_runtime.root_decision

    @property
    def child_decisions(
        self,
    ) -> tuple[RegisteredVerifiedKappaDecisionSpecV1, ...]:
        return self.verified_runtime.child_decisions

    @property
    def terminal_code(self) -> str:
        return self.verified_runtime.terminal_code

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_evaluator_terminal_"
                "mint_authority.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "verified_runtime_adapter_id": (
                self.verified_runtime.adapter_id
            ),
            "occurrence_id": self.occurrence.occurrence_id,
            "operational_result_artifact_id": (
                self.operational_result_artifact_id
            ),
            "independent_runtime_verification_id": (
                self.verified_runtime.independent_runtime_verification_id
            ),
            "terminal_code": self.terminal_code,
            "caller_terminal_status_or_policy_accepted": False,
        }

    @property
    def mint_authority_id(self) -> str:
        return self._mint_authority_id


def consume_evaluator_terminal_mint_authority_v1(
    authority: Any,
) -> RegisteredEvaluatorTerminalMintAuthorityV1:
    """Evaluator-only exact-type replay; arbitrary objects fail closed."""

    if (
        type(authority) is not RegisteredEvaluatorTerminalMintAuthorityV1
        or authority._minting_capability
        is not _EVALUATOR_MINT_AUTHORITY_SENTINEL
        or type(authority.verified_runtime)
        is not RegisteredVerifiedOccurrenceRuntimeAdapterV1
        or authority.verified_runtime._minting_capability
        is not _VERIFIED_RUNTIME_ADAPTER_SENTINEL
        or authority.verified_runtime.root_decision._minting_capability
        is not _VERIFIED_KAPPA_SPEC_SENTINEL
        or any(
            item._minting_capability is not _VERIFIED_KAPPA_SPEC_SENTINEL
            for item in authority.verified_runtime.child_decisions
        )
    ):
        raise evaluator.RegisteredIndependentExactGroundEvaluationLocked(
            evaluator.REGISTERED_OPERATIONAL_TERMINAL_BLOCKER
        )
    return authority


@dataclass(frozen=True, slots=True)
class RegisteredOperationalTerminalAuthorityResultV1:
    verified_runtime_adapter_id: str
    mint_authority_id: str
    evaluator_bundle: evaluator.RegisteredOperationalTerminalPolicyBundleV1
    access_audit: RegisteredOperationalTerminalAuthorityAccessAuditV1
    _authority_result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (
                self.verified_runtime_adapter_id,
                "authority runtime adapter",
            ),
            (self.mint_authority_id, "authority mint capability"),
        ):
            _cid(value, label)
        if (
            type(self.evaluator_bundle)
            is not evaluator.RegisteredOperationalTerminalPolicyBundleV1
            or self.evaluator_bundle.mint_authority_id
            != self.mint_authority_id
            or type(self.access_audit)
            is not RegisteredOperationalTerminalAuthorityAccessAuditV1
            or self.access_audit.target_access_started
            or self.access_audit.evaluator_factory_calls != 1
        ):
            raise V072RegisteredOperationalTerminalAuthorityViolation(
                "registered terminal authority result does not reconcile"
            )
        object.__setattr__(
            self,
            "_authority_result_id",
            _content_id("authority_result", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_operational_terminal_"
                "authority_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "verified_runtime_adapter_id": (
                self.verified_runtime_adapter_id
            ),
            "mint_authority_id": self.mint_authority_id,
            "evaluator_bundle_id": self.evaluator_bundle.bundle_id,
            "access_audit_id": self.access_audit.audit_id,
            "terminal_status_or_policy_caller_supplied": False,
        }

    @property
    def authority_result_id(self) -> str:
        return self._authority_result_id


def _require_production_identity_without_target_access(
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
        or occurrence_plan.template.context_key != context.context_key
    ):
        raise RegisteredOperationalTerminalAuthorityLockedV1(
            "terminal authority requires one exact chain-bound occurrence "
            "and identical anchor",
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
        raise RegisteredOperationalTerminalAuthorityLockedV1(
            "terminal authority chain replay failed before target access",
            access_audit=ZERO_ACCESS_AUDIT,
        ) from error
    return authority_chain, anchor, occurrence_plan, context


def _require_common_production_identity_without_target_access(
    *,
    authority_chain: Any,
    anchor: Any,
    context: Any,
) -> tuple[
    consumer.RegisteredCampaignAuthorityChainV1,
    final_authority.V072RemoteMainAnchorV1,
    prereg.HeldoutPublicGraphContextV2,
]:
    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or authority_chain.remote_main_anchor is not anchor
        or type(context) is not prereg.HeldoutPublicGraphContextV2
        or context not in prereg.registered_heldout_public_contexts_v2()
    ):
        raise RegisteredOperationalTerminalAuthorityLockedV1(
            "terminal authority requires one exact chain, anchor, and "
            "registered context",
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
        raise RegisteredOperationalTerminalAuthorityLockedV1(
            "terminal authority chain replay failed before target access",
            access_audit=ZERO_ACCESS_AUDIT,
        ) from error
    return authority_chain, anchor, context


def _kappa_spec_from_adaptive_decision(
    decision: Any,
) -> RegisteredVerifiedKappaDecisionSpecV1:
    return RegisteredVerifiedKappaDecisionSpecV1(
        _VERIFIED_KAPPA_SPEC_SENTINEL,
        decision.ground_state_id,
        decision.public_state_id,
        decision.state_ranks,
        decision.remaining_horizon,
        decision.selected_abstract_action_key,
        decision.ground_action_ids,
        decision.ground_semantic_action_ids,
        decision.ground_actions,
        decision.uniform_weights,
        decision.concretizer_entry_id,
    )


def _kappa_spec_from_direct_decision(
    decision: Any,
) -> RegisteredVerifiedKappaDecisionSpecV1:
    return RegisteredVerifiedKappaDecisionSpecV1(
        _VERIFIED_KAPPA_SPEC_SENTINEL,
        decision.ground_state_id,
        decision.state_semantic_id,
        decision.state_ranks,
        decision.remaining_horizon,
        decision.selected_action_semantic_id,
        (decision.selected_ground_action_id,),
        (decision.selected_action_semantic_id,),
        (decision.action,),
        (Fraction(1),),
        decision.decision_id,
    )


def _mint_authority_result_from_adapter(
    adapter: RegisteredVerifiedOccurrenceRuntimeAdapterV1,
) -> RegisteredOperationalTerminalAuthorityResultV1:
    mint_authority = RegisteredEvaluatorTerminalMintAuthorityV1(
        _EVALUATOR_MINT_AUTHORITY_SENTINEL,
        adapter,
    )
    bundle = evaluator.mint_registered_occurrence_operational_terminal_policy_v1(
        mint_authority=mint_authority
    )
    audit = RegisteredOperationalTerminalAuthorityAccessAuditV1(
        anchor_checks=1,
        authority_chain_verifications=1,
        occurrence_identity_checks=1,
        verified_runtime_adapter_checks=1,
        evaluator_factory_calls=1,
    )
    return RegisteredOperationalTerminalAuthorityResultV1(
        adapter.adapter_id,
        mint_authority.mint_authority_id,
        bundle,
        audit,
    )


def derive_registered_adaptive_operational_terminal_authority_v1(
    *,
    authority_chain: Any,
    anchor: Any,
    occurrence_plan: Any,
    context: Any,
    verified_runtime_result: Any,
) -> RegisteredOperationalTerminalAuthorityResultV1:
    """Replay an adaptive result, then retain its complete fixed κ support."""

    from acfqp import v072_registered_adaptive_quotient_runtime_v1 as adaptive

    (
        _,
        canonical_anchor,
        canonical_plan,
        canonical_context,
    ) = _require_production_identity_without_target_access(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=occurrence_plan,
        context=context,
    )
    if (
        type(verified_runtime_result)
        is not adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1
    ):
        raise RegisteredOperationalTerminalAuthorityLockedV1(
            "adaptive terminal authority requires the exact verified wrapper",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    # Mandatory independent replay occurs inside this route verifier.
    replayed = adaptive.verify_registered_adaptive_quotient_occurrence_result_v1(
        authority_chain=authority_chain,
        anchor=canonical_anchor,
        occurrence_plan=canonical_plan,
        context=canonical_context,
        claimed=verified_runtime_result.execution,
    )
    execution = replayed.execution
    if (
        replayed.verified_result_id
        != verified_runtime_result.verified_result_id
        or replayed.independent_verification_id
        != verified_runtime_result.independent_verification_id
        or execution.status
        is not adaptive.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
        or not execution.concretizer_policy
    ):
        raise V072RegisteredOperationalTerminalAuthorityViolation(
            "adaptive result did not independently replay to a certified "
            "fixed-concretizer policy"
        )
    decisions = tuple(
        _kappa_spec_from_adaptive_decision(item)
        for item in execution.concretizer_policy
    )
    roots = tuple(
        item for item in decisions if item.remaining_horizon == prereg.HORIZON
    )
    children = tuple(
        sorted(
            (item for item in decisions if item.remaining_horizon == 1),
            key=lambda item: (item.state_ranks, item.semantic_action_id),
        )
    )
    if len(roots) != 1:
        raise V072RegisteredOperationalTerminalAuthorityViolation(
            "adaptive verified policy has no unique root semantic decision"
        )
    occurrence = evaluator.registered_occurrence_identity_v1(
        anchor=canonical_anchor,
        context=canonical_context,
        arm=canonical_plan.template.arm,
    )
    adapter = RegisteredVerifiedOccurrenceRuntimeAdapterV1(
        _VERIFIED_RUNTIME_ADAPTER_SENTINEL,
        consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT,
        occurrence,
        execution.result_id,
        replayed.independent_verification_id,
        roots[0],
        children,
    )
    return _mint_authority_result_from_adapter(adapter)


def derive_registered_matched_direct_operational_terminal_authority_v1(
    *,
    authority_chain: Any,
    anchor: Any,
    occurrence_plan: Any,
    context: Any,
    verified_runtime_result: Any,
) -> RegisteredOperationalTerminalAuthorityResultV1:
    """Replay a direct result, then represent its policy as singleton κ."""

    from acfqp import v072_registered_matched_direct_runtime_v1 as direct

    _, canonical_anchor, canonical_context = (
        _require_common_production_identity_without_target_access(
            authority_chain=authority_chain,
            anchor=anchor,
            context=context,
        )
    )
    if (
        type(occurrence_plan)
        is not direct.RegisteredMatchedDirectOccurrencePlanV1
        or occurrence_plan.anchor_id != canonical_anchor.anchor_id
        or occurrence_plan.context_id != canonical_context.context_id
        or occurrence_plan.context_key != canonical_context.context_key
        or type(verified_runtime_result)
        is not direct.RegisteredMatchedDirectOccurrenceResultV1
    ):
        raise RegisteredOperationalTerminalAuthorityLockedV1(
            "direct terminal authority requires one exact occurrence and "
            "runtime result",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    # Mandatory independent replay occurs before any policy extraction.
    verification = direct.verify_registered_matched_direct_occurrence_result_v1(
        verified_runtime_result
    )
    selected = verified_runtime_result.selected_policy
    if (
        verification.occurrence_result_id
        != verified_runtime_result.result_id
        or verified_runtime_result.occurrence_plan_id
        != occurrence_plan.plan_id
        or verified_runtime_result.context_id
        != canonical_context.context_id
        or selected is None
        or verification.selected_policy_id != selected.policy_id
        or verified_runtime_result.terminal_class
        is not direct.RegisteredMatchedDirectTerminalClassV1.PLAN_CERTIFICATE
        or verified_runtime_result.terminal_code
        is not (
            direct.RegisteredMatchedDirectTerminalCodeV1
            .CONDITIONAL_PLAN_CERTIFICATE
        )
    ):
        raise V072RegisteredOperationalTerminalAuthorityViolation(
            "direct result did not independently replay to a plan "
            "certificate"
        )
    occurrence = evaluator.registered_occurrence_identity_v1(
        anchor=canonical_anchor,
        context=canonical_context,
        arm="MATCHED_DIRECT_GROUND",
    )
    adapter = RegisteredVerifiedOccurrenceRuntimeAdapterV1(
        _VERIFIED_RUNTIME_ADAPTER_SENTINEL,
        consumer.RegisteredRouteKindV1.MATCHED_DIRECT_GROUND,
        occurrence,
        verified_runtime_result.result_id,
        verification.verification_id,
        _kappa_spec_from_direct_decision(selected.root_decision),
        tuple(
            sorted(
                (
                    _kappa_spec_from_direct_decision(item)
                    for item in selected.child_decisions
                ),
                key=lambda item: (item.state_ranks, item.semantic_action_id),
            )
        ),
    )
    return _mint_authority_result_from_adapter(adapter)


def derive_registered_operational_terminal_authority_v1(
    *,
    authority_chain: Any,
    anchor: Any,
    occurrence_plan: Any,
    context: Any,
    verified_runtime_result: Any,
) -> RegisteredOperationalTerminalAuthorityResultV1:
    """Dispatch exact route result types; arbitrary private adapters fail."""

    from acfqp import v072_registered_adaptive_quotient_runtime_v1 as adaptive
    from acfqp import v072_registered_matched_direct_runtime_v1 as direct

    if type(verified_runtime_result) is (
        adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1
    ):
        return derive_registered_adaptive_operational_terminal_authority_v1(
            authority_chain=authority_chain,
            anchor=anchor,
            occurrence_plan=occurrence_plan,
            context=context,
            verified_runtime_result=verified_runtime_result,
        )
    if type(verified_runtime_result) is (
        direct.RegisteredMatchedDirectOccurrenceResultV1
    ):
        return derive_registered_matched_direct_operational_terminal_authority_v1(
            authority_chain=authority_chain,
            anchor=anchor,
            occurrence_plan=occurrence_plan,
            context=context,
            verified_runtime_result=verified_runtime_result,
        )
    raise RegisteredOperationalTerminalAuthorityLockedV1(
        "terminal authority accepts only exact route runtime result types",
        access_audit=ZERO_ACCESS_AUDIT,
    )


class RegistrationDisjointTerminalRouteV1(str, Enum):
    ADAPTIVE_QUOTIENT = "ADAPTIVE_QUOTIENT"
    MATCHED_DIRECT_GROUND = "MATCHED_DIRECT_GROUND"


@dataclass(frozen=True, slots=True)
class RegistrationDisjointTerminalOccurrenceV1:
    occurrence_key: str
    route: RegistrationDisjointTerminalRouteV1
    _occurrence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.occurrence_key) is not str
            or not self.occurrence_key.startswith(
                "SYNTHETIC_DISJOINT_OCCURRENCE_"
            )
            or type(self.route) is not RegistrationDisjointTerminalRouteV1
        ):
            raise V072RegisteredOperationalTerminalAuthorityViolation(
                "registration-disjoint terminal occurrence is malformed"
            )
        object.__setattr__(
            self,
            "_occurrence_id",
            _content_id("synthetic_occurrence", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_terminal_occurrence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_key": self.occurrence_key,
            "route": self.route.value,
            "registered_occurrence": False,
        }

    @property
    def occurrence_id(self) -> str:
        return self._occurrence_id


@dataclass(frozen=True, slots=True)
class RegistrationDisjointTerminalChildDecisionV1:
    occurrence_id: str
    state_id: str
    action: tuple[int, int, int]
    _decision_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "synthetic decision occurrence")
        _cid(self.state_id, "synthetic decision state")
        _action(self.action, "synthetic child action")
        object.__setattr__(
            self,
            "_decision_id",
            _content_id("synthetic_child", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_terminal_"
                "child_decision.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "state_id": self.state_id,
            "action": list(self.action),
        }

    @property
    def decision_id(self) -> str:
        return self._decision_id


@dataclass(frozen=True, slots=True)
class RegistrationDisjointVerifiedRuntimeResultV1:
    occurrence_id: str
    route: RegistrationDisjointTerminalRouteV1
    root_action: tuple[int, int, int]
    child_decisions: tuple[
        RegistrationDisjointTerminalChildDecisionV1, ...
    ]
    _runtime_result_id: str = field(init=False, repr=False)
    _independent_verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "synthetic verified runtime occurrence")
        _action(self.root_action, "synthetic verified root action")
        if (
            type(self.route) is not RegistrationDisjointTerminalRouteV1
            or type(self.child_decisions) is not tuple
            or any(
                type(item)
                is not RegistrationDisjointTerminalChildDecisionV1
                or item.occurrence_id != self.occurrence_id
                for item in self.child_decisions
            )
            or tuple(item.state_id for item in self.child_decisions)
            != tuple(sorted({item.state_id for item in self.child_decisions}))
        ):
            raise V072RegisteredOperationalTerminalAuthorityViolation(
                "registration-disjoint verified runtime policy is malformed"
            )
        runtime_id = _content_id("synthetic_runtime", self._payload())
        object.__setattr__(self, "_runtime_result_id", runtime_id)
        object.__setattr__(
            self,
            "_independent_verification_id",
            _content_id(
                "synthetic_runtime_verification",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_runtime_"
                        "result_verification.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "runtime_result_id": runtime_id,
                    "verification_result": "CERTIFIED_PLAN_RECOMPUTED",
                    "status_recomputed": True,
                    "policy_recomputed": True,
                    "registered_target_accesses": 0,
                },
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_verified_"
                "runtime_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "route": self.route.value,
            "root_action": list(self.root_action),
            "child_decision_ids": [
                item.decision_id for item in self.child_decisions
            ],
            "certification_recomputed": True,
            "caller_terminal_status_or_policy_accepted": False,
            "registered_target_evidence": False,
        }

    @property
    def runtime_result_id(self) -> str:
        return self._runtime_result_id

    @property
    def independent_verification_id(self) -> str:
        return self._independent_verification_id


_SYNTHETIC_COMMITMENT_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegistrationDisjointOperationalTerminalCommitmentV1:
    _minting_capability: object
    occurrence_id: str
    runtime_result_id: str
    independent_verification_id: str
    terminal_code: str
    selected_policy_id: str
    operational_terminal_id: str
    _commitment_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "synthetic commitment occurrence"),
            (self.runtime_result_id, "synthetic commitment runtime"),
            (
                self.independent_verification_id,
                "synthetic runtime verification",
            ),
            (self.selected_policy_id, "synthetic selected policy"),
            (self.operational_terminal_id, "synthetic terminal"),
        ):
            _cid(value, label)
        if (
            self._minting_capability is not _SYNTHETIC_COMMITMENT_SENTINEL
            or self.terminal_code != "CONDITIONAL_PLAN_CERTIFICATE"
        ):
            raise V072RegisteredOperationalTerminalAuthorityViolation(
                "registration-disjoint terminal commitment is unminted"
            )
        object.__setattr__(
            self,
            "_commitment_id",
            _content_id("synthetic_commitment", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_terminal_commitment.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "runtime_result_id": self.runtime_result_id,
            "independent_verification_id": (
                self.independent_verification_id
            ),
            "terminal_code": self.terminal_code,
            "selected_policy_id": self.selected_policy_id,
            "operational_terminal_id": self.operational_terminal_id,
            "terminal_status_or_policy_caller_supplied": False,
            "production_authority_minted": False,
            "registered_target_accesses": 0,
        }

    @property
    def commitment_id(self) -> str:
        return self._commitment_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "commitment_id": self.commitment_id}


def derive_registration_disjoint_operational_terminal_commitment_v1(
    *,
    occurrence_identity: RegistrationDisjointTerminalOccurrenceV1,
    verified_runtime_result: RegistrationDisjointVerifiedRuntimeResultV1,
) -> RegistrationDisjointOperationalTerminalCommitmentV1:
    """Derive terminal and policy commitments; no caller decision fields."""

    if (
        type(occurrence_identity)
        is not RegistrationDisjointTerminalOccurrenceV1
        or type(verified_runtime_result)
        is not RegistrationDisjointVerifiedRuntimeResultV1
        or verified_runtime_result.occurrence_id
        != occurrence_identity.occurrence_id
        or verified_runtime_result.route is not occurrence_identity.route
    ):
        raise V072RegisteredOperationalTerminalAuthorityViolation(
            "registration-disjoint runtime result was transplanted"
        )
    terminal_code = "CONDITIONAL_PLAN_CERTIFICATE"
    selected_policy_id = _content_id(
        "synthetic_policy",
        {
            "schema": (
                "acfqp.v072_registration_disjoint_operational_policy.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": occurrence_identity.occurrence_id,
            "runtime_result_id": verified_runtime_result.runtime_result_id,
            "root_action": list(verified_runtime_result.root_action),
            "child_decision_ids": [
                item.decision_id
                for item in verified_runtime_result.child_decisions
            ],
            "policy_extracted_from_verified_runtime": True,
            "caller_policy_accepted": False,
        },
    )
    terminal_id = _content_id(
        "synthetic_terminal",
        {
            "schema": (
                "acfqp.v072_registration_disjoint_operational_terminal.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": occurrence_identity.occurrence_id,
            "runtime_result_id": verified_runtime_result.runtime_result_id,
            "independent_verification_id": (
                verified_runtime_result.independent_verification_id
            ),
            "selected_policy_id": selected_policy_id,
            "terminal_code": terminal_code,
            "status_recomputed": True,
            "caller_terminal_or_status_accepted": False,
        },
    )
    return RegistrationDisjointOperationalTerminalCommitmentV1(
        _SYNTHETIC_COMMITMENT_SENTINEL,
        occurrence_identity.occurrence_id,
        verified_runtime_result.runtime_result_id,
        verified_runtime_result.independent_verification_id,
        terminal_code,
        selected_policy_id,
        terminal_id,
    )


__all__ = [
    "ADAPTIVE_RUNTIME_ADAPTER_BLOCKER",
    "DIRECT_RUNTIME_ADAPTER_BLOCKER",
    "PROFILE_KEY",
    "PRODUCTION_ADAPTERS_AVAILABLE",
    "PROPOSED_CONTRACT_VERSION",
    "RegisteredEvaluatorTerminalMintAuthorityV1",
    "RegisteredVerifiedKappaDecisionSpecV1",
    "RegisteredOperationalTerminalAuthorityAccessAuditV1",
    "RegisteredOperationalTerminalAuthorityLockedV1",
    "RegisteredOperationalTerminalAuthorityResultV1",
    "RegisteredRuntimeResultAdapterDependencyBlockedV1",
    "RegisteredRuntimeResultAdapterProtocolV1",
    "RegisteredVerifiedOccurrenceRuntimeAdapterV1",
    "RegistrationDisjointOperationalTerminalCommitmentV1",
    "RegistrationDisjointTerminalChildDecisionV1",
    "RegistrationDisjointTerminalOccurrenceV1",
    "RegistrationDisjointTerminalRouteV1",
    "RegistrationDisjointVerifiedRuntimeResultV1",
    "SCHEMA_VERSION",
    "V072RegisteredOperationalTerminalAuthorityViolation",
    "ZERO_ACCESS_AUDIT",
    "consume_evaluator_terminal_mint_authority_v1",
    "derive_registered_operational_terminal_authority_v1",
    "derive_registered_adaptive_operational_terminal_authority_v1",
    "derive_registered_matched_direct_operational_terminal_authority_v1",
    "derive_registration_disjoint_operational_terminal_commitment_v1",
    "inspect_registered_runtime_result_adapter_protocol_v1",
]
