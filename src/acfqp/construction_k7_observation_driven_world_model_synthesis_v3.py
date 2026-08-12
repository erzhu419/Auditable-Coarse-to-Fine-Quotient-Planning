"""Program-authoritative observation-driven world-model synthesis.

V3 first synthesizes constructor programs from the frozen observation corpus,
then delegates execution to V2.  V2's fixed capability rows are retained only
as a compatibility cross-check around the existing W5/K6 constructor engine;
they are no longer the selection authority.  Exact catalogue hits still avoid
construction and an unmatched program remains a zero-ground noncertificate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import construction_k7_observation_driven_world_model_synthesis_v2 as executor_v2
from acfqp import construction_k7_observed_capability_program_synthesis_v1 as program_v1
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_V3_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.146"
PROFILE_KEY = "construction_k7_observation_driven_world_model_synthesis_v3"
RESULT_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_V3_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset({RESULT_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("observation-driven synthesis V3 domain is not central")

_RESULT_ISSUER = object()


class ConstructionK7ObservationDrivenWorldModelSynthesisV3Error(ValueError):
    """The synthesized program and compatibility executor disagreed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservationDrivenWorldModelSynthesisV3Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservationDrivenWorldModelSynthesisV3Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class ObservationDrivenWorldModelSynthesisV3ResultV1:
    _issuer: InitVar[object]
    program_decision: program_v1.ObservedCapabilityProgramDecisionV1
    executor_result: executor_v2.ObservationDrivenWorldModelSynthesisV2ResultV1 = field(
        repr=False, compare=False
    )
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.program_decision)
            is not program_v1.ObservedCapabilityProgramDecisionV1
            or type(self.executor_result)
            is not executor_v2.ObservationDrivenWorldModelSynthesisV2ResultV1
            or self.program_decision.signature.context_id
            != self.executor_result.capability_decision.signature.context_id
            or self.program_decision.signature.topology_id
            != self.executor_result.capability_decision.signature.topology_id
        ):
            _fail("synthesis V3 result is caller-minted or structurally crossed")
        dispatch = self.executor_result.executor_result.dispatch
        if dispatch.dispatch_outcome == "CONSTRUCT_REGISTERED_MODEL" and (
            self.program_decision.outcome != "PROGRAM_MATCH"
            or self.program_decision.selected_constructor_key != dispatch.constructor_key
        ):
            _fail("constructor differs from the synthesized program authority")
        if dispatch.dispatch_outcome == "NO_CERTIFIABLE_CONSTRUCTOR" and (
            self.program_decision.outcome != "NO_SOUND_PROGRAM"
        ):
            _fail("executor rejected a matching synthesized program")
        if dispatch.dispatch_outcome == "REUSE_EXACT_MODEL" and (
            self.executor_result.executor_result.initial_route.selection.outcome
            != "EXACT_MODEL_MATCH"
        ):
            _fail("synthesis V3 exact reuse did not precede construction")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        dispatch = self.executor_result.executor_result.dispatch
        return {
            "schema": "acfqp.construction_k7_observation_driven_synthesis_v3_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "observed_program_decision_id": self.program_decision.decision_id,
            "executor_synthesis_v2_result_id": self.executor_result.result_id,
            "result_outcome": self.executor_result.executor_result.to_document()["result_outcome"],
            "executor_dispatch_outcome": dispatch.dispatch_outcome,
            "selected_constructor_key": self.program_decision.selected_constructor_key,
            "constructor_selection_authority": "OBSERVATION_DERIVED_PROGRAM_PROPOSAL_V1",
            "literal_values_observation_derived": True,
            "fixed_human_signature_value_table_authoritative": False,
            "v2_fixed_signature_rows_compatibility_cross_check_only": True,
            "operational_program_replay_performed": False,
            "complete_program_replay_reserved_for_evaluation_verifier": True,
            "exact_catalogue_hit_bypasses_constructor": (
                dispatch.dispatch_outcome == "REUSE_EXACT_MODEL"
            ),
            "human_registered_primitive_and_operator_vocabulary": True,
            "automatic_primitive_or_operator_invention_claimed": False,
            "broad_graph_or_domain_generalization_claimed": False,
            "nearby_model_or_program_transfer_allowed": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("synthesis V3 result identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "program_decision": self.program_decision.to_document(),
            "executor_result": self.executor_result.to_document(),
            "world_model_synthesis_v3_result_id": self.result_id,
        }


def run_observation_driven_world_model_synthesis_v3(
    catalogue: catalogue_v1.HeldoutReusableModelCatalogueV1,
    context: observer_v1.PublicGraphContextV1,
    *,
    logical_occurrence_id: str,
    occurrence_ordinal: int,
    selected_reuse_result_bytes: bytes | None,
) -> ObservationDrivenWorldModelSynthesisV3ResultV1:
    decision = program_v1.propose_observed_capability_program_v1(context)
    result = executor_v2.run_observation_driven_world_model_synthesis_v2(
        catalogue,
        context,
        logical_occurrence_id=_cid(logical_occurrence_id, "logical occurrence"),
        occurrence_ordinal=occurrence_ordinal,
        selected_reuse_result_bytes=selected_reuse_result_bytes,
    )
    return ObservationDrivenWorldModelSynthesisV3ResultV1(
        _RESULT_ISSUER, decision, result
    )


def verify_observation_driven_world_model_synthesis_v3(
    context: observer_v1.PublicGraphContextV1,
    result: ObservationDrivenWorldModelSynthesisV3ResultV1,
) -> ObservationDrivenWorldModelSynthesisV3ResultV1:
    if type(result) is not ObservationDrivenWorldModelSynthesisV3ResultV1:
        _fail("synthesis V3 verifier rejects foreign values")
    program_v1.verify_observed_capability_program_v1(context, result.program_decision)
    executor_v2.verify_observation_driven_world_model_synthesis_v2(
        context, result.executor_result
    )
    result.__post_init__(_RESULT_ISSUER)
    return result


__all__ = (
    "ConstructionK7ObservationDrivenWorldModelSynthesisV3Error",
    "LOCAL_DOMAINS",
    "ObservationDrivenWorldModelSynthesisV3ResultV1",
    "run_observation_driven_world_model_synthesis_v3",
    "verify_observation_driven_world_model_synthesis_v3",
)
