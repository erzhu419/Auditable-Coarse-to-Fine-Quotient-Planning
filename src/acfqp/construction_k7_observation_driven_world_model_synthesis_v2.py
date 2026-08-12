"""Capability-authoritative observation-driven world-model synthesis.

V2 freezes an observation-derived constructor capability decision before it
delegates execution to the V1 synthesis engine.  The legacy context-key branch
inside that engine is not authority: its selected constructor must exactly
match the independently frozen structural capability, and any disagreement is
a protocol failure.  Exact catalogue hits continue to bypass construction;
unmatched structures remain no-access noncertificates.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import construction_k7_observation_driven_world_model_synthesis_v1 as executor_v1
from acfqp import construction_k7_observed_constructor_capability_v1 as capability_v1
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_V2_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.144"
PROFILE_KEY = "construction_k7_observation_driven_world_model_synthesis_v2"
RESULT_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_V2_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset({RESULT_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("observation-driven synthesis V2 domain is not central")

_RESULT_ISSUER = object()


class ConstructionK7ObservationDrivenWorldModelSynthesisV2Error(ValueError):
    """The capability decision and executor branch disagree."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservationDrivenWorldModelSynthesisV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservationDrivenWorldModelSynthesisV2Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class ObservationDrivenWorldModelSynthesisV2ResultV1:
    _issuer: InitVar[object]
    capability_decision: capability_v1.ObservedConstructorCapabilityDecisionV1
    executor_result: executor_v1.ObservationDrivenWorldModelSynthesisResultV1 = field(
        repr=False, compare=False
    )
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.capability_decision)
            is not capability_v1.ObservedConstructorCapabilityDecisionV1
            or type(self.executor_result)
            is not executor_v1.ObservationDrivenWorldModelSynthesisResultV1
            or self.executor_result.dispatch.context_id
            != self.capability_decision.signature.context_id
            or self.executor_result.dispatch.topology_id
            != self.capability_decision.signature.topology_id
        ):
            _fail("synthesis V2 result is caller-minted or structurally crossed")
        dispatch = self.executor_result.dispatch
        capability = self.capability_decision
        constructed = dispatch.dispatch_outcome == "CONSTRUCT_REGISTERED_MODEL"
        unsupported = dispatch.dispatch_outcome == "NO_CERTIFIABLE_CONSTRUCTOR"
        if (
            constructed
            and (
                capability.outcome != "CAPABILITY_MATCH"
                or dispatch.constructor_key != capability.selected_constructor_key
            )
        ):
            _fail("executor constructor differs from observed capability authority")
        if unsupported and capability.outcome != "NO_SOUND_CAPABILITY":
            _fail("executor rejected a sound observed constructor capability")
        if (
            dispatch.dispatch_outcome == "REUSE_EXACT_MODEL"
            and self.executor_result.initial_route.selection.outcome
            != "EXACT_MODEL_MATCH"
        ):
            _fail("synthesis V2 exact reuse did not precede constructor execution")
        object.__setattr__(
            self, "_result_id", content_id(RESULT_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        dispatch = self.executor_result.dispatch
        return {
            "schema": "acfqp.construction_k7_observation_driven_synthesis_v2_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "constructor_capability_decision_id": self.capability_decision.decision_id,
            "executor_synthesis_result_id": self.executor_result.result_id,
            "result_outcome": self.executor_result.to_document()["result_outcome"],
            "executor_dispatch_outcome": dispatch.dispatch_outcome,
            "selected_constructor_key": self.capability_decision.selected_constructor_key,
            "constructor_selection_authority": (
                "OBSERVED_GRAPH_INVARIANT_CAPABILITY_DECISION_V1"
            ),
            "legacy_context_key_dispatch_authoritative": False,
            "legacy_executor_selection_exactly_cross_checked": True,
            "exact_catalogue_hit_bypasses_constructor": (
                dispatch.dispatch_outcome == "REUSE_EXACT_MODEL"
            ),
            "nearby_model_or_capability_transfer_allowed": False,
            "fixed_human_capability_signature_registry": True,
            "automatic_coordinate_primitive_invention_claimed": False,
            "broad_graph_or_domain_generalization_claimed": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("synthesis V2 result identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "capability_decision": self.capability_decision.to_document(),
            "executor_result": self.executor_result.to_document(),
            "world_model_synthesis_v2_result_id": self.result_id,
        }


def run_observation_driven_world_model_synthesis_v2(
    catalogue: catalogue_v1.HeldoutReusableModelCatalogueV1,
    context: observer_v1.PublicGraphContextV1,
    *,
    logical_occurrence_id: str,
    occurrence_ordinal: int,
    selected_reuse_result_bytes: bytes | None,
) -> ObservationDrivenWorldModelSynthesisV2ResultV1:
    """Freeze structural capability, then execute and cross-check one route."""

    decision = capability_v1.propose_observed_constructor_capability_v1(context)
    capability_v1.verify_observed_constructor_capability_v1(context, decision)
    result = executor_v1.run_observation_driven_world_model_synthesis_v1(
        catalogue,
        context,
        logical_occurrence_id=_cid(logical_occurrence_id, "logical occurrence"),
        occurrence_ordinal=occurrence_ordinal,
        selected_reuse_result_bytes=selected_reuse_result_bytes,
    )
    return ObservationDrivenWorldModelSynthesisV2ResultV1(
        _RESULT_ISSUER, decision, result
    )


def verify_observation_driven_world_model_synthesis_v2(
    context: observer_v1.PublicGraphContextV1,
    result: ObservationDrivenWorldModelSynthesisV2ResultV1,
) -> ObservationDrivenWorldModelSynthesisV2ResultV1:
    """Replay capability and executor result, then rejoin both authorities."""

    if type(result) is not ObservationDrivenWorldModelSynthesisV2ResultV1:
        _fail("synthesis V2 verifier rejects foreign values")
    capability_v1.verify_observed_constructor_capability_v1(
        context, result.capability_decision
    )
    executor_v1.verify_observation_driven_world_model_synthesis_v1(
        result.executor_result
    )
    result.__post_init__(_RESULT_ISSUER)
    return result


__all__ = (
    "ConstructionK7ObservationDrivenWorldModelSynthesisV2Error",
    "LOCAL_DOMAINS",
    "ObservationDrivenWorldModelSynthesisV2ResultV1",
    "run_observation_driven_world_model_synthesis_v2",
    "verify_observation_driven_world_model_synthesis_v2",
)
