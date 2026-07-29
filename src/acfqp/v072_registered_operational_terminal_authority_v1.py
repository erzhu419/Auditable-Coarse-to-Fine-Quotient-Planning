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
MODELED_SUPPORT_CONTRACT_VERSION = "1.39.0"
MODELED_SUPPORT_PROFILE_KEY = (
    "v074_modeled_policy_support_total_lift_v0"
)
# This key is a registered component of the V0-074 total-lift profile.
# Historical V0-072 authorization does not authorize these new semantics.
MODELED_SUPPORT_PROFILE_REGISTRATION = (
    "REGISTERED_COMPONENT_OF_V074_PARTIAL_SUPPORT_TOTAL_LIFT_"
    "PARALLEL_EXECUTION_V0"
)
GLOBAL_OTHER_BEHAVIOR = "ABSORBING_POLICY_ABORT_FAILURE"

ADAPTIVE_RUNTIME_ADAPTER_BLOCKER = None
DIRECT_RUNTIME_ADAPTER_BLOCKER = None
PRODUCTION_ADAPTERS_AVAILABLE = True


class V072RegisteredOperationalTerminalAuthorityViolation(ValueError):
    """An authority, occurrence, runtime, policy, or terminal invariant failed."""


class V074ModeledPolicySupportProtocolViolation(
    V072RegisteredOperationalTerminalAuthorityViolation
):
    """The independently replayed model/policy support contract was violated."""


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
        "acfqp:v074-modeled-support-verified-runtime-result-adapter:v1"
    ),
    "kappa_spec": (
        "acfqp:v072-registered-verified-kappa-decision-spec:v1"
    ),
    "mint_authority": (
        "acfqp:v074-modeled-support-evaluator-terminal-mint-authority:v1"
    ),
    "authority_result": (
        "acfqp:v074-modeled-support-operational-terminal-authority-result:v1"
    ),
    "v074_action_realization": (
        "acfqp:v074-modeled-support-action-realization:v1"
    ),
    "v074_modeled_child": (
        "acfqp:v074-modeled-policy-support-child:v1"
    ),
    "v074_root_support": (
        "acfqp:v074-modeled-policy-root-row-support:v1"
    ),
    "v074_child_decision_binding": (
        "acfqp:v074-modeled-policy-child-decision-binding:v1"
    ),
    "v074_other_handler": (
        "acfqp:v074-modeled-policy-global-other-handler:v1"
    ),
    "v074_modeled_support": (
        "acfqp:v074-modeled-policy-support-authority:v1"
    ),
    "v074_query_binding": (
        "acfqp:v074-modeled-policy-support-query-binding:v1"
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


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V074ModeledPolicySupportProtocolViolation(
            "modeled-support arithmetic must use exact Fractions"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _modeled_query_binding_payload(
    *,
    context_id: str,
    threshold_profile_id: str,
    risk_tolerance: Fraction,
    reward_ceiling: Fraction,
    normalized_regret_tolerance: Fraction,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v074_modeled_policy_support_query_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "contract_version": MODELED_SUPPORT_CONTRACT_VERSION,
        "profile_key": MODELED_SUPPORT_PROFILE_KEY,
        "profile_registration": MODELED_SUPPORT_PROFILE_REGISTRATION,
        "context_id": context_id,
        "threshold_profile_id": threshold_profile_id,
        "horizon": prereg.HORIZON,
        "rank_cap": prereg.RANK_CAP,
        "risk_tolerance": _fdoc(risk_tolerance),
        "reward_ceiling": _fdoc(reward_ceiling),
        "normalized_regret_tolerance": _fdoc(
            normalized_regret_tolerance
        ),
    }


def _modeled_query_binding_id(
    *,
    context_id: str,
    threshold_profile_id: str,
    risk_tolerance: Fraction,
    reward_ceiling: Fraction,
    normalized_regret_tolerance: Fraction,
) -> str:
    return _content_id(
        "v074_query_binding",
        _modeled_query_binding_payload(
            context_id=context_id,
            threshold_profile_id=threshold_profile_id,
            risk_tolerance=risk_tolerance,
            reward_ceiling=reward_ceiling,
            normalized_regret_tolerance=normalized_regret_tolerance,
        ),
    )


def _modeled_other_handler_payload(
    *,
    context_id: str,
    direct_planner_model_id: str,
    observed_closure_id: str,
    global_other_destination_id: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v074_modeled_policy_global_other_handler.v1",
        "schema_version": SCHEMA_VERSION,
        "contract_version": MODELED_SUPPORT_CONTRACT_VERSION,
        "profile_key": MODELED_SUPPORT_PROFILE_KEY,
        "profile_registration": MODELED_SUPPORT_PROFILE_REGISTRATION,
        "context_id": context_id,
        "direct_planner_model_id": direct_planner_model_id,
        "observed_closure_id": observed_closure_id,
        "global_other_destination_id": global_other_destination_id,
        "behavior": GLOBAL_OTHER_BEHAVIOR,
        "failure_value": 1,
        "continuation_reward": _fdoc(Fraction(0)),
    }


def _modeled_other_handler_id(
    *,
    context_id: str,
    direct_planner_model_id: str,
    observed_closure_id: str,
    global_other_destination_id: str,
) -> str:
    return _content_id(
        "v074_other_handler",
        _modeled_other_handler_payload(
            context_id=context_id,
            direct_planner_model_id=direct_planner_model_id,
            observed_closure_id=observed_closure_id,
            global_other_destination_id=global_other_destination_id,
        ),
    )


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
        "mint_registered_occurrence_operational_terminal_policy_v2"
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
_MODELED_POLICY_SUPPORT_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredVerifiedActionRealizationV1:
    """One atomic fixed-κ realization; parallel arrays are not authority."""

    ground_action_id: str
    ground_semantic_action_id: str
    action: tuple[int, int, int]
    weight: Fraction
    _realization_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.ground_action_id, "modeled-support ground action")
        _cid(
            self.ground_semantic_action_id,
            "modeled-support semantic action",
        )
        _action(self.action, "modeled-support action")
        if type(self.weight) is not Fraction or not 0 < self.weight <= 1:
            raise V074ModeledPolicySupportProtocolViolation(
                "modeled-support realization weight is malformed"
            )
        object.__setattr__(
            self,
            "_realization_id",
            _content_id("v074_action_realization", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v074_verified_action_realization.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": MODELED_SUPPORT_CONTRACT_VERSION,
            "profile_key": MODELED_SUPPORT_PROFILE_KEY,
            "profile_registration": MODELED_SUPPORT_PROFILE_REGISTRATION,
            "ground_action_id": self.ground_action_id,
            "ground_semantic_action_id": self.ground_semantic_action_id,
            "action": list(self.action),
            "weight": _fdoc(self.weight),
            "atomic_alignment_authority": True,
        }

    @property
    def realization_id(self) -> str:
        return self._realization_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "realization_id": self.realization_id}


@dataclass(frozen=True, slots=True)
class RegisteredModeledActiveChildSupportV1:
    """One positive-upper ACTIVE_STATE destination in a frozen model row."""

    destination_id: str
    model_state_id: str
    public_state_id: str
    state_ranks: tuple[int, ...]
    upper_probability: Fraction
    _support_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.destination_id, "modeled child destination"),
            (self.model_state_id, "modeled child model state"),
            (self.public_state_id, "modeled child public state"),
        ):
            _cid(value, label)
        if (
            type(self.state_ranks) is not tuple
            or len(self.state_ranks) != 7
            or any(
                type(item) is not int
                or not 0 <= item <= prereg.RANK_CAP
                for item in self.state_ranks
            )
            or type(self.upper_probability) is not Fraction
            or not 0 < self.upper_probability <= 1
        ):
            raise V074ModeledPolicySupportProtocolViolation(
                "positive-upper modeled child support is malformed"
            )
        object.__setattr__(
            self,
            "_support_id",
            _content_id("v074_modeled_child", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v074_modeled_active_child_support.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": MODELED_SUPPORT_CONTRACT_VERSION,
            "profile_key": MODELED_SUPPORT_PROFILE_KEY,
            "profile_registration": MODELED_SUPPORT_PROFILE_REGISTRATION,
            "destination_id": self.destination_id,
            "model_state_id": self.model_state_id,
            "public_state_id": self.public_state_id,
            "state_ranks": list(self.state_ranks),
            "upper_probability": _fdoc(self.upper_probability),
            "destination_category": "ACTIVE_STATE",
            "positive_upper_required": True,
        }

    @property
    def support_id(self) -> str:
        return self._support_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "support_id": self.support_id}


@dataclass(frozen=True, slots=True)
class RegisteredModeledRootRowSupportV1:
    """Row-specific modeled continuation support for one root realization."""

    realization: RegisteredVerifiedActionRealizationV1
    selected_row_id: str
    active_children: tuple[RegisteredModeledActiveChildSupportV1, ...]
    _root_support_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.selected_row_id, "modeled selected root row")
        if (
            type(self.realization) is not RegisteredVerifiedActionRealizationV1
            or type(self.active_children) is not tuple
            or tuple(item.support_id for item in self.active_children)
            != tuple(
                sorted(
                    {
                        item.support_id
                        for item in self.active_children
                        if type(item)
                        is RegisteredModeledActiveChildSupportV1
                    }
                )
            )
            or any(
                type(item) is not RegisteredModeledActiveChildSupportV1
                for item in self.active_children
            )
            or len(
                {item.model_state_id for item in self.active_children}
            )
            != len(self.active_children)
        ):
            raise V074ModeledPolicySupportProtocolViolation(
                "row-specific modeled child support is noncanonical"
            )
        object.__setattr__(
            self,
            "_root_support_id",
            _content_id("v074_root_support", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v074_modeled_root_row_support.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": MODELED_SUPPORT_CONTRACT_VERSION,
            "profile_key": MODELED_SUPPORT_PROFILE_KEY,
            "profile_registration": MODELED_SUPPORT_PROFILE_REGISTRATION,
            "realization_id": self.realization.realization_id,
            "selected_row_id": self.selected_row_id,
            "active_child_support_ids": [
                item.support_id for item in self.active_children
            ],
            "row_specific": True,
        }

    @property
    def root_support_id(self) -> str:
        return self._root_support_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "realization": self.realization.to_document(),
            "active_children": [
                item.to_document() for item in self.active_children
            ],
            "root_support_id": self.root_support_id,
        }


@dataclass(frozen=True, slots=True)
class RegisteredModeledChildDecisionBindingV1:
    """State-indexed binding from the model registry to one decision spec."""

    model_state_id: str
    public_state_id: str
    state_ranks: tuple[int, ...]
    decision_spec_id: str
    semantic_action_id: str
    source_action_realization_artifact_id: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.model_state_id, "child binding model state"),
            (self.public_state_id, "child binding public state"),
            (self.decision_spec_id, "child binding decision spec"),
            (self.semantic_action_id, "child binding semantic action"),
            (
                self.source_action_realization_artifact_id,
                "child binding action realization",
            ),
        ):
            _cid(value, label)
        if (
            type(self.state_ranks) is not tuple
            or len(self.state_ranks) != 7
            or any(
                type(value) is not int
                or not 0 <= value <= prereg.RANK_CAP
                for value in self.state_ranks
            )
        ):
            raise V074ModeledPolicySupportProtocolViolation(
                "child decision binding state is malformed"
            )
        object.__setattr__(
            self,
            "_binding_id",
            _content_id(
                "v074_child_decision_binding",
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v074_modeled_policy_child_decision_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": MODELED_SUPPORT_CONTRACT_VERSION,
            "profile_key": MODELED_SUPPORT_PROFILE_KEY,
            "profile_registration": MODELED_SUPPORT_PROFILE_REGISTRATION,
            "model_state_id": self.model_state_id,
            "public_state_id": self.public_state_id,
            "state_ranks": list(self.state_ranks),
            "decision_spec_id": self.decision_spec_id,
            "semantic_action_id": self.semantic_action_id,
            "source_action_realization_artifact_id": (
                self.source_action_realization_artifact_id
            ),
            "state_indexed": True,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class RegisteredModeledPolicySupportAuthorityV1:
    """Content-addressed authority derived only from replayed operational model."""

    _minting_capability: object
    occurrence_id: str
    context_id: str
    query_binding_id: str
    operational_occurrence_plan_id: str
    threshold_profile_id: str
    query_risk_tolerance: Fraction
    query_reward_ceiling: Fraction
    query_normalized_regret_tolerance: Fraction
    route_kind: consumer.RegisteredRouteKindV1
    operational_result_artifact_id: str
    independent_runtime_verification_id: str
    model_epoch_id: str
    selected_plan_id: str
    operational_audit_id: str
    root_decision_spec_id: str
    child_decision_spec_ids: tuple[str, ...]
    child_decision_bindings: tuple[
        RegisteredModeledChildDecisionBindingV1, ...
    ]
    operational_root_reward_lower: Fraction
    operational_unrestricted_reward_upper: Fraction
    operational_root_failure_upper: Fraction
    operational_normalized_regret_upper: Fraction
    source_kind: str
    source_model_container_id: str
    direct_planner_model_id: str
    observed_closure_id: str
    root_model_state_id: str
    global_other_destination_id: str
    global_other_handler_id: str
    global_modeled_children: tuple[
        RegisteredModeledActiveChildSupportV1, ...
    ]
    selected_root_rows: tuple[RegisteredModeledRootRowSupportV1, ...]
    _authority_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "modeled-support occurrence"),
            (self.context_id, "modeled-support context"),
            (self.query_binding_id, "modeled-support query binding"),
            (
                self.operational_occurrence_plan_id,
                "modeled-support operational occurrence plan",
            ),
            (
                self.threshold_profile_id,
                "modeled-support threshold profile",
            ),
            (
                self.operational_result_artifact_id,
                "modeled-support operational result",
            ),
            (
                self.independent_runtime_verification_id,
                "modeled-support runtime verification",
            ),
            (self.model_epoch_id, "modeled-support model epoch"),
            (self.selected_plan_id, "modeled-support selected plan"),
            (self.operational_audit_id, "modeled-support audit"),
            (
                self.root_decision_spec_id,
                "modeled-support root decision spec",
            ),
            (
                self.source_model_container_id,
                "modeled-support source container",
            ),
            (
                self.direct_planner_model_id,
                "modeled-support direct planner model",
            ),
            (self.observed_closure_id, "modeled-support closure"),
            (self.root_model_state_id, "modeled-support root state"),
            (
                self.global_other_destination_id,
                "modeled-support global OTHER",
            ),
            (
                self.global_other_handler_id,
                "modeled-support OTHER handler",
            ),
        ):
            _cid(value, label)
        if (
            type(self.child_decision_spec_ids) is not tuple
            or self.child_decision_spec_ids
            != tuple(sorted(set(self.child_decision_spec_ids)))
        ):
            raise V074ModeledPolicySupportProtocolViolation(
                "modeled-support child decision identities are noncanonical"
            )
        for value in self.child_decision_spec_ids:
            _cid(value, "modeled-support child decision spec")
        if (
            type(self.child_decision_bindings) is not tuple
            or any(
                type(item)
                is not RegisteredModeledChildDecisionBindingV1
                for item in self.child_decision_bindings
            )
            or tuple(
                item.model_state_id
                for item in self.child_decision_bindings
            )
            != tuple(
                sorted(
                    {
                        item.model_state_id
                        for item in self.child_decision_bindings
                    }
                )
            )
            or self.child_decision_spec_ids
            != tuple(
                sorted(
                    item.decision_spec_id
                    for item in self.child_decision_bindings
                )
            )
        ):
            raise V074ModeledPolicySupportProtocolViolation(
                "state-indexed modeled child decision bindings are malformed"
            )
        for value, label in (
            (self.query_risk_tolerance, "modeled-support query risk"),
            (self.query_reward_ceiling, "modeled-support query reward"),
            (
                self.query_normalized_regret_tolerance,
                "modeled-support query regret",
            ),
            (
                self.operational_root_reward_lower,
                "modeled-support audit reward lower",
            ),
            (
                self.operational_root_failure_upper,
                "modeled-support audit failure upper",
            ),
            (
                self.operational_unrestricted_reward_upper,
                "modeled-support audit unrestricted reward upper",
            ),
            (
                self.operational_normalized_regret_upper,
                "modeled-support audit normalized regret upper",
            ),
        ):
            if type(value) is not Fraction or value < 0:
                raise V074ModeledPolicySupportProtocolViolation(
                    f"{label} is malformed"
                )
        expected_source_kind = (
            "FINAL_CERTIFIED_DIRECT_CHECKPOINT"
            if self.route_kind
            is consumer.RegisteredRouteKindV1.MATCHED_DIRECT_GROUND
            else "FINAL_ADAPTIVE_EPOCH_MODEL_PAIR"
        )
        if (
            self._minting_capability is not _MODELED_POLICY_SUPPORT_SENTINEL
            or type(self.route_kind)
            is not consumer.RegisteredRouteKindV1
            or self.source_kind != expected_source_kind
            or self.query_reward_ceiling <= 0
            or self.query_risk_tolerance > 1
            or self.operational_root_failure_upper > 1
            or self.operational_root_reward_lower
            > self.operational_unrestricted_reward_upper
            or self.query_binding_id
            != _modeled_query_binding_id(
                context_id=self.context_id,
                threshold_profile_id=self.threshold_profile_id,
                risk_tolerance=self.query_risk_tolerance,
                reward_ceiling=self.query_reward_ceiling,
                normalized_regret_tolerance=(
                    self.query_normalized_regret_tolerance
                ),
            )
            or self.global_other_handler_id
            != _modeled_other_handler_id(
                context_id=self.context_id,
                direct_planner_model_id=self.direct_planner_model_id,
                observed_closure_id=self.observed_closure_id,
                global_other_destination_id=(
                    self.global_other_destination_id
                ),
            )
            or type(self.global_modeled_children) is not tuple
            or any(
                type(item) is not RegisteredModeledActiveChildSupportV1
                for item in self.global_modeled_children
            )
            or tuple(
                item.model_state_id for item in self.global_modeled_children
            )
            != tuple(
                sorted(
                    {
                        item.model_state_id
                        for item in self.global_modeled_children
                    }
                )
            )
            or type(self.selected_root_rows) is not tuple
            or not self.selected_root_rows
            or any(
                type(item) is not RegisteredModeledRootRowSupportV1
                for item in self.selected_root_rows
            )
            or tuple(
                item.realization.ground_action_id
                for item in self.selected_root_rows
            )
            != tuple(
                sorted(
                    {
                        item.realization.ground_action_id
                        for item in self.selected_root_rows
                    }
                )
            )
            or sum(
                (
                    item.realization.weight
                    for item in self.selected_root_rows
                ),
                Fraction(0),
            )
            != 1
        ):
            raise V074ModeledPolicySupportProtocolViolation(
                "modeled-policy support authority is malformed or caller-minted"
            )
        global_by_state = {
            item.model_state_id: item
            for item in self.global_modeled_children
        }
        child_binding_by_state = {
            item.model_state_id: item
            for item in self.child_decision_bindings
        }
        required_child_states = {
            child.model_state_id
            for row in self.selected_root_rows
            for child in row.active_children
        }
        if (
            not required_child_states <= set(child_binding_by_state)
            or not set(child_binding_by_state) <= set(global_by_state)
            or any(
                (
                    binding.public_state_id,
                    binding.state_ranks,
                )
                != (
                    global_by_state[state_id].public_state_id,
                    global_by_state[state_id].state_ranks,
                )
                for state_id, binding in child_binding_by_state.items()
            )
            or any(
                (
                    global_by_state.get(child.model_state_id) is None
                    or (
                        global_by_state[
                            child.model_state_id
                        ].destination_id,
                        global_by_state[
                            child.model_state_id
                        ].public_state_id,
                        global_by_state[
                            child.model_state_id
                        ].state_ranks,
                    )
                    != (
                        child.destination_id,
                        child.public_state_id,
                        child.state_ranks,
                    )
                )
                for row in self.selected_root_rows
                for child in row.active_children
            )
        ):
            raise V074ModeledPolicySupportProtocolViolation(
                "row support or child decision binding is outside the frozen "
                "model state registry"
            )
        object.__setattr__(
            self,
            "_authority_id",
            _content_id("v074_modeled_support", self._payload()),
        )

    @property
    def required_selected_child_state_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    child.model_state_id
                    for row in self.selected_root_rows
                    for child in row.active_children
                }
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v074_modeled_policy_support_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": MODELED_SUPPORT_CONTRACT_VERSION,
            "profile_key": MODELED_SUPPORT_PROFILE_KEY,
            "profile_registration": MODELED_SUPPORT_PROFILE_REGISTRATION,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "query_binding_id": self.query_binding_id,
            "operational_occurrence_plan_id": (
                self.operational_occurrence_plan_id
            ),
            "threshold_profile_id": self.threshold_profile_id,
            "query_risk_tolerance": _fdoc(self.query_risk_tolerance),
            "query_reward_ceiling": _fdoc(self.query_reward_ceiling),
            "query_normalized_regret_tolerance": _fdoc(
                self.query_normalized_regret_tolerance
            ),
            "route_kind": self.route_kind.value,
            "operational_result_artifact_id": (
                self.operational_result_artifact_id
            ),
            "independent_runtime_verification_id": (
                self.independent_runtime_verification_id
            ),
            "model_epoch_id": self.model_epoch_id,
            "selected_plan_id": self.selected_plan_id,
            "operational_audit_id": self.operational_audit_id,
            "root_decision_spec_id": self.root_decision_spec_id,
            "child_decision_spec_ids": list(
                self.child_decision_spec_ids
            ),
            "child_decision_binding_ids": [
                item.binding_id for item in self.child_decision_bindings
            ],
            "operational_root_reward_lower": _fdoc(
                self.operational_root_reward_lower
            ),
            "operational_unrestricted_reward_upper": _fdoc(
                self.operational_unrestricted_reward_upper
            ),
            "operational_root_failure_upper": _fdoc(
                self.operational_root_failure_upper
            ),
            "operational_normalized_regret_upper": _fdoc(
                self.operational_normalized_regret_upper
            ),
            "source_kind": self.source_kind,
            "source_model_container_id": self.source_model_container_id,
            "direct_planner_model_id": self.direct_planner_model_id,
            "observed_closure_id": self.observed_closure_id,
            "root_model_state_id": self.root_model_state_id,
            "global_other_destination_id": (
                self.global_other_destination_id
            ),
            "global_other_handler_id": self.global_other_handler_id,
            "global_modeled_child_support_ids": [
                item.support_id for item in self.global_modeled_children
            ],
            "selected_root_row_support_ids": [
                item.root_support_id for item in self.selected_root_rows
            ],
            "support_derived_before_exact_evaluation": True,
            "support_derived_from_child_decision_set": False,
            "caller_supplied_support_allowed": False,
        }

    @property
    def authority_id(self) -> str:
        return self._authority_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "global_modeled_children": [
                item.to_document() for item in self.global_modeled_children
            ],
            "selected_root_rows": [
                item.to_document() for item in self.selected_root_rows
            ],
            "child_decision_bindings": [
                item.to_document()
                for item in self.child_decision_bindings
            ],
            "global_other_handler": {
                **_modeled_other_handler_payload(
                    context_id=self.context_id,
                    direct_planner_model_id=self.direct_planner_model_id,
                    observed_closure_id=self.observed_closure_id,
                    global_other_destination_id=(
                        self.global_other_destination_id
                    ),
                ),
                "handler_id": self.global_other_handler_id,
            },
            "query_binding": {
                **_modeled_query_binding_payload(
                    context_id=self.context_id,
                    threshold_profile_id=self.threshold_profile_id,
                    risk_tolerance=self.query_risk_tolerance,
                    reward_ceiling=self.query_reward_ceiling,
                    normalized_regret_tolerance=(
                        self.query_normalized_regret_tolerance
                    ),
                ),
                "query_binding_id": self.query_binding_id,
            },
            "authority_id": self.authority_id,
        }


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
    modeled_support_authority: RegisteredModeledPolicySupportAuthorityV1
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
            or len({item.ground_state_id for item in self.child_decisions})
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
            or type(self.modeled_support_authority)
            is not RegisteredModeledPolicySupportAuthorityV1
            or self.modeled_support_authority._minting_capability
            is not _MODELED_POLICY_SUPPORT_SENTINEL
            or self.modeled_support_authority.occurrence_id
            != self.occurrence.occurrence_id
            or self.modeled_support_authority.context_id
            != self.occurrence.context_id
            or self.modeled_support_authority.route_kind is not self.route_kind
            or self.modeled_support_authority.operational_result_artifact_id
            != self.operational_result_artifact_id
            or self.modeled_support_authority.root_decision_spec_id
            != self.root_decision.spec_id
            or (
                self.modeled_support_authority
                .independent_runtime_verification_id
            )
            != self.independent_runtime_verification_id
            or tuple(
                (
                    item.realization.ground_action_id,
                    item.realization.ground_semantic_action_id,
                    item.realization.action,
                    item.realization.weight,
                )
                for item in self.modeled_support_authority.selected_root_rows
            )
            != tuple(
                zip(
                    self.root_decision.ground_action_ids,
                    self.root_decision.ground_semantic_action_ids,
                    self.root_decision.ground_actions,
                    self.root_decision.uniform_weights,
                    strict=True,
                )
            )
        ):
            raise RegisteredOperationalTerminalAuthorityLockedV1(
                "REGISTERED_VERIFIED_ROUTE_RUNTIME_REQUIRED",
                access_audit=ZERO_ACCESS_AUDIT,
            )
        child_by_state = {
            item.ground_state_id: item for item in self.child_decisions
        }
        global_by_state = {
            item.model_state_id: item
            for item in self.modeled_support_authority.global_modeled_children
        }
        required = set(
            self.modeled_support_authority.required_selected_child_state_ids
        )
        if (
            self.modeled_support_authority.child_decision_spec_ids
            != tuple(sorted(item.spec_id for item in self.child_decisions))
            or tuple(
                (
                    item.model_state_id,
                    item.public_state_id,
                    item.state_ranks,
                    item.decision_spec_id,
                    item.semantic_action_id,
                    item.source_action_realization_artifact_id,
                )
                for item
                in self.modeled_support_authority.child_decision_bindings
            )
            != tuple(
                sorted(
                    (
                        item.ground_state_id,
                        item.public_state_id,
                        item.state_ranks,
                        item.spec_id,
                        item.semantic_action_id,
                        item.source_action_realization_artifact_id,
                    )
                    for item in self.child_decisions
                )
            )
            or not required <= set(child_by_state)
            or not set(child_by_state) <= set(global_by_state)
            or any(
                (
                    child_by_state[state_id].public_state_id,
                    child_by_state[state_id].state_ranks,
                )
                != (
                    global_by_state[state_id].public_state_id,
                    global_by_state[state_id].state_ranks,
                )
                for state_id in child_by_state
            )
        ):
            raise V074ModeledPolicySupportProtocolViolation(
                "MODELED_SELECTED_ROOT_CHILD_DECISION_OMISSION_OR_TRANSPLANT"
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
                "acfqp.v074_modeled_support_verified_runtime_result_adapter.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": MODELED_SUPPORT_CONTRACT_VERSION,
            "profile_key": MODELED_SUPPORT_PROFILE_KEY,
            "profile_registration": MODELED_SUPPORT_PROFILE_REGISTRATION,
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
            "modeled_policy_support_authority_id": (
                self.modeled_support_authority.authority_id
            ),
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
    def modeled_support_authority(
        self,
    ) -> RegisteredModeledPolicySupportAuthorityV1:
        return self.verified_runtime.modeled_support_authority

    @property
    def terminal_code(self) -> str:
        return self.verified_runtime.terminal_code

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v074_modeled_support_evaluator_terminal_"
                "mint_authority.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": MODELED_SUPPORT_CONTRACT_VERSION,
            "profile_key": MODELED_SUPPORT_PROFILE_KEY,
            "profile_registration": MODELED_SUPPORT_PROFILE_REGISTRATION,
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
            "modeled_policy_support_authority_id": (
                self.modeled_support_authority.authority_id
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
        or type(authority.verified_runtime.modeled_support_authority)
        is not RegisteredModeledPolicySupportAuthorityV1
        or (
            authority.verified_runtime.modeled_support_authority
            ._minting_capability
        )
        is not _MODELED_POLICY_SUPPORT_SENTINEL
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
                "acfqp.v074_modeled_support_operational_terminal_"
                "authority_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": MODELED_SUPPORT_CONTRACT_VERSION,
            "profile_key": MODELED_SUPPORT_PROFILE_KEY,
            "profile_registration": MODELED_SUPPORT_PROFILE_REGISTRATION,
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

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "evaluator_bundle": self.evaluator_bundle.to_document(),
            "access_audit": self.access_audit.to_document(),
            "authority_result_id": self.authority_result_id,
        }


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


def _atomic_realizations_from_spec(
    spec: RegisteredVerifiedKappaDecisionSpecV1,
) -> tuple[RegisteredVerifiedActionRealizationV1, ...]:
    realizations = tuple(
        RegisteredVerifiedActionRealizationV1(
            ground_action_id,
            semantic_action_id,
            action,
            weight,
        )
        for (
            ground_action_id,
            semantic_action_id,
            action,
            weight,
        ) in zip(
            spec.ground_action_ids,
            spec.ground_semantic_action_ids,
            spec.ground_actions,
            spec.uniform_weights,
            strict=True,
        )
    )
    if tuple(item.ground_action_id for item in realizations) != (
        spec.ground_action_ids
    ):
        raise V074ModeledPolicySupportProtocolViolation(
            "fixed-kappa realization alignment changed"
        )
    return realizations


def _derive_modeled_policy_support_authority_v1(
    *,
    occurrence: evaluator.RegisteredOccurrenceIdentityV1,
    route_kind: consumer.RegisteredRouteKindV1,
    operational_result_artifact_id: str,
    independent_runtime_verification_id: str,
    operational_occurrence_plan_id: str,
    model_epoch_id: str,
    selected_plan_id: str,
    operational_audit: Any,
    threshold_profile: Any,
    source_kind: str,
    source_model_container_id: str,
    direct_planner_model: Any,
    observed_closure: Any,
    global_other_destination_id: str,
    root_decision: RegisteredVerifiedKappaDecisionSpecV1,
    child_decisions: tuple[RegisteredVerifiedKappaDecisionSpecV1, ...],
) -> RegisteredModeledPolicySupportAuthorityV1:
    """Derive support from one independently replayed final direct model."""

    from acfqp import partial_support_robust_planner_v1 as robust
    from acfqp import v072_cold_h2_closure_v1 as cold
    from acfqp import v072_cold_h2_model_builders_v1 as models

    if (
        type(direct_planner_model)
        is not robust.PartialSupportIntervalModelV1
        or type(observed_closure) is not cold.V072ColdH2ClosureBundleV1
        or type(occurrence) is not evaluator.RegisteredOccurrenceIdentityV1
        or type(root_decision) is not RegisteredVerifiedKappaDecisionSpecV1
        or type(child_decisions) is not tuple
        or any(
            type(item) is not RegisteredVerifiedKappaDecisionSpecV1
            for item in child_decisions
        )
        or type(operational_audit) is not robust.RobustPlanAuditV1
        or type(threshold_profile)
        is not robust.RobustThresholdProfileV1
        or not operational_audit.certified
        or operational_audit.threshold_profile_id
        != threshold_profile.threshold_profile_id
        or threshold_profile.context_id != occurrence.context_id
    ):
        raise V074ModeledPolicySupportProtocolViolation(
            "modeled support requires the independently replayed final model "
            "pair and root decision"
        )
    model = direct_planner_model
    closure = observed_closure
    if (
        model.root_state_id != root_decision.ground_state_id
        or closure.context_id != occurrence.context_id
    ):
        raise V074ModeledPolicySupportProtocolViolation(
            "modeled support source model, closure, or root was transplanted"
        )
    catalogue_by_model_state: dict[str, Any] = {}
    public_by_model_state: dict[
        str, tuple[str, tuple[int, ...]]
    ] = {}
    for catalogue in (
        closure.root_catalogue,
        *closure.child_catalogues,
    ):
        model_state_id = models.ground_state_id_v1(
            closure.context_id,
            catalogue.state,
            catalogue.remaining_horizon,
        )
        if model_state_id in catalogue_by_model_state:
            raise V074ModeledPolicySupportProtocolViolation(
                "closure maps two catalogues to one model state"
            )
        catalogue_by_model_state[model_state_id] = catalogue
        ranks = tuple(catalogue.state.document["ranks"])
        public_by_model_state[model_state_id] = (
            catalogue.state.semantic_state_id,
            ranks,
        )
    if set(catalogue_by_model_state) != {
        item.state_id for item in model.catalogues
    }:
        raise V074ModeledPolicySupportProtocolViolation(
            "direct planner model state registry differs from its closure"
        )
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    active_destination_by_state = {
        item.state_id: item
        for item in model.destinations
        if item.category is robust.DestinationCategory.ACTIVE_STATE
    }
    child_model_state_ids = tuple(
        sorted(set(catalogue_by_model_state) - {model.root_state_id})
    )
    if set(active_destination_by_state) != set(child_model_state_ids):
        raise V074ModeledPolicySupportProtocolViolation(
            "direct planner model ACTIVE_STATE registry differs from closure"
        )
    max_upper_by_destination: dict[str, Fraction] = {}
    for row in model.rows:
        for mass in row.masses:
            if (
                destination_by_id[mass.destination_id].category
                is robust.DestinationCategory.ACTIVE_STATE
            ):
                max_upper_by_destination[mass.destination_id] = max(
                    max_upper_by_destination.get(
                        mass.destination_id,
                        Fraction(0),
                    ),
                    mass.upper,
                )
    global_children: list[RegisteredModeledActiveChildSupportV1] = []
    for model_state_id in child_model_state_ids:
        destination = active_destination_by_state[model_state_id]
        public_state_id, state_ranks = public_by_model_state[model_state_id]
        upper = max_upper_by_destination.get(
            destination.destination_id,
            Fraction(0),
        )
        global_children.append(
            RegisteredModeledActiveChildSupportV1(
                destination.destination_id,
                model_state_id,
                public_state_id,
                state_ranks,
                upper,
            )
        )
    global_by_state = {
        item.model_state_id: item for item in global_children
    }
    row_by_action_id = {
        row.action_id: row
        for row in model.rows
        if (
            row.state_id == model.root_state_id
            and row.remaining_horizon == prereg.HORIZON
        )
    }
    root_rows: list[RegisteredModeledRootRowSupportV1] = []
    for realization in _atomic_realizations_from_spec(root_decision):
        row = row_by_action_id.get(realization.ground_action_id)
        if row is None:
            raise V074ModeledPolicySupportProtocolViolation(
                "selected root realization has no direct-planner row"
            )
        children: list[RegisteredModeledActiveChildSupportV1] = []
        for mass in row.masses:
            destination = destination_by_id[mass.destination_id]
            if (
                destination.category
                is robust.DestinationCategory.ACTIVE_STATE
                and mass.upper > 0
            ):
                assert destination.state_id is not None
                registered = global_by_state[destination.state_id]
                children.append(
                    RegisteredModeledActiveChildSupportV1(
                        registered.destination_id,
                        registered.model_state_id,
                        registered.public_state_id,
                        registered.state_ranks,
                        mass.upper,
                    )
                )
        root_rows.append(
            RegisteredModeledRootRowSupportV1(
                realization,
                row.row_id,
                tuple(sorted(children, key=lambda item: item.support_id)),
            )
        )
    other_destination_id = _cid(
        global_other_destination_id,
        "modeled-support global OTHER source",
    )
    if (
        other_destination_id
        != next(
            item.destination_id
            for item in model.destinations
            if item.category is robust.DestinationCategory.OTHER
        )
    ):
        raise V074ModeledPolicySupportProtocolViolation(
            "global OTHER destination differs from direct planner model"
        )
    handler_id = _modeled_other_handler_id(
        context_id=occurrence.context_id,
        direct_planner_model_id=model.model_id,
        observed_closure_id=closure.closure_id,
        global_other_destination_id=other_destination_id,
    )
    return RegisteredModeledPolicySupportAuthorityV1(
        _MODELED_POLICY_SUPPORT_SENTINEL,
        occurrence.occurrence_id,
        occurrence.context_id,
        _modeled_query_binding_id(
            context_id=occurrence.context_id,
            threshold_profile_id=threshold_profile.threshold_profile_id,
            risk_tolerance=threshold_profile.risk_tolerance,
            reward_ceiling=threshold_profile.reward_ceiling,
            normalized_regret_tolerance=(
                threshold_profile.normalized_regret_tolerance
            ),
        ),
        operational_occurrence_plan_id,
        threshold_profile.threshold_profile_id,
        threshold_profile.risk_tolerance,
        threshold_profile.reward_ceiling,
        threshold_profile.normalized_regret_tolerance,
        route_kind,
        operational_result_artifact_id,
        independent_runtime_verification_id,
        model_epoch_id,
        selected_plan_id,
        operational_audit.audit_id,
        root_decision.spec_id,
        tuple(sorted(item.spec_id for item in child_decisions)),
        tuple(
            sorted(
                (
                    RegisteredModeledChildDecisionBindingV1(
                        item.ground_state_id,
                        item.public_state_id,
                        item.state_ranks,
                        item.spec_id,
                        item.semantic_action_id,
                        item.source_action_realization_artifact_id,
                    )
                    for item in child_decisions
                ),
                key=lambda item: item.model_state_id,
            )
        ),
        operational_audit.root_reward_lower,
        operational_audit.unrestricted_reward_upper,
        operational_audit.root_failure_upper,
        operational_audit.normalized_regret_upper,
        source_kind,
        source_model_container_id,
        model.model_id,
        closure.closure_id,
        model.root_state_id,
        other_destination_id,
        handler_id,
        tuple(
            sorted(
                global_children,
                key=lambda item: item.model_state_id,
            )
        ),
        tuple(
            sorted(
                root_rows,
                key=lambda item: item.realization.ground_action_id,
            )
        ),
    )


def _mint_authority_result_from_adapter(
    adapter: RegisteredVerifiedOccurrenceRuntimeAdapterV1,
) -> RegisteredOperationalTerminalAuthorityResultV1:
    mint_authority = RegisteredEvaluatorTerminalMintAuthorityV1(
        _EVALUATOR_MINT_AUTHORITY_SENTINEL,
        adapter,
    )
    bundle = evaluator.mint_registered_occurrence_operational_terminal_policy_v2(
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
    final_model_pair = execution.epochs[-1].model_pair
    final_audit = execution.planner_results[-1].solve_result.audit
    if final_audit is None or execution.certificate_id is None:
        raise V074ModeledPolicySupportProtocolViolation(
            "certified adaptive result lacks its final audit or certificate"
        )
    modeled_support = _derive_modeled_policy_support_authority_v1(
        occurrence=occurrence,
        route_kind=consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT,
        operational_result_artifact_id=execution.result_id,
        independent_runtime_verification_id=(
            replayed.independent_verification_id
        ),
        operational_occurrence_plan_id=(
            execution.occurrence_plan.occurrence_id
        ),
        model_epoch_id=execution.epochs[-1].epoch_id,
        selected_plan_id=execution.certificate_id,
        operational_audit=final_audit,
        threshold_profile=final_model_pair.threshold_profile,
        source_kind="FINAL_ADAPTIVE_EPOCH_MODEL_PAIR",
        source_model_container_id=final_model_pair.model_pair_id,
        direct_planner_model=final_model_pair.direct_planner_model,
        observed_closure=final_model_pair.closure_bundle,
        global_other_destination_id=(
            final_model_pair.direct_collapse_proof
            .global_other_destination_id
        ),
        root_decision=roots[0],
        child_decisions=children,
    )
    adapter = RegisteredVerifiedOccurrenceRuntimeAdapterV1(
        _VERIFIED_RUNTIME_ADAPTER_SENTINEL,
        consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT,
        occurrence,
        execution.result_id,
        replayed.independent_verification_id,
        roots[0],
        children,
        modeled_support,
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
    root_decision = _kappa_spec_from_direct_decision(
        selected.root_decision
    )
    child_decisions = tuple(
        sorted(
            (
                _kappa_spec_from_direct_decision(item)
                for item in selected.child_decisions
            ),
            key=lambda item: (item.state_ranks, item.semantic_action_id),
        )
    )
    final_checkpoint = (
        verified_runtime_result.checkpoint_records[-1].inventory_checkpoint
    )
    final_audit = (
        verified_runtime_result.checkpoint_records[-1].planner_result.audit
    )
    if final_audit is None:
        raise V074ModeledPolicySupportProtocolViolation(
            "certified direct result lacks its final operational audit"
        )
    if (
        selected.context_id != canonical_context.context_id
        or selected.checkpoint_id != final_checkpoint.checkpoint_id
        or selected.threshold_profile_id
        != (
            final_checkpoint.direct_snapshot.threshold_profile
            .threshold_profile_id
        )
        or selected.audit_id != final_audit.audit_id
    ):
        raise V074ModeledPolicySupportProtocolViolation(
            "direct selected plan is not bound to its final "
            "context/checkpoint/threshold/audit"
        )
    modeled_support = _derive_modeled_policy_support_authority_v1(
        occurrence=occurrence,
        route_kind=consumer.RegisteredRouteKindV1.MATCHED_DIRECT_GROUND,
        operational_result_artifact_id=verified_runtime_result.result_id,
        independent_runtime_verification_id=verification.verification_id,
        operational_occurrence_plan_id=occurrence_plan.plan_id,
        model_epoch_id=final_checkpoint.checkpoint_id,
        selected_plan_id=selected.policy_id,
        operational_audit=final_audit,
        threshold_profile=(
            final_checkpoint.direct_snapshot.threshold_profile
        ),
        source_kind="FINAL_CERTIFIED_DIRECT_CHECKPOINT",
        source_model_container_id=final_checkpoint.checkpoint_id,
        direct_planner_model=final_checkpoint.direct_snapshot.planner_model,
        observed_closure=final_checkpoint.closure_bundle,
        global_other_destination_id=next(
            item.destination_id
            for item in final_checkpoint.direct_snapshot.planner_model.destinations
            if item.category.value == "OTHER"
        ),
        root_decision=root_decision,
        child_decisions=child_decisions,
    )
    adapter = RegisteredVerifiedOccurrenceRuntimeAdapterV1(
        _VERIFIED_RUNTIME_ADAPTER_SENTINEL,
        consumer.RegisteredRouteKindV1.MATCHED_DIRECT_GROUND,
        occurrence,
        verified_runtime_result.result_id,
        verification.verification_id,
        root_decision,
        child_decisions,
        modeled_support,
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
    "GLOBAL_OTHER_BEHAVIOR",
    "MODELED_SUPPORT_CONTRACT_VERSION",
    "MODELED_SUPPORT_PROFILE_KEY",
    "MODELED_SUPPORT_PROFILE_REGISTRATION",
    "PROFILE_KEY",
    "PRODUCTION_ADAPTERS_AVAILABLE",
    "PROPOSED_CONTRACT_VERSION",
    "RegisteredEvaluatorTerminalMintAuthorityV1",
    "RegisteredModeledActiveChildSupportV1",
    "RegisteredModeledChildDecisionBindingV1",
    "RegisteredModeledPolicySupportAuthorityV1",
    "RegisteredModeledRootRowSupportV1",
    "RegisteredVerifiedActionRealizationV1",
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
    "V074ModeledPolicySupportProtocolViolation",
    "ZERO_ACCESS_AUDIT",
    "consume_evaluator_terminal_mint_authority_v1",
    "derive_registered_operational_terminal_authority_v1",
    "derive_registered_adaptive_operational_terminal_authority_v1",
    "derive_registered_matched_direct_operational_terminal_authority_v1",
    "derive_registration_disjoint_operational_terminal_commitment_v1",
    "inspect_registered_runtime_result_adapter_protocol_v1",
]
