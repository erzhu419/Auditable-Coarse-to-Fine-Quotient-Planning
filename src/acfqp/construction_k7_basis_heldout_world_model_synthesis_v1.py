"""Use an observation-derived basis in an actual held-out world-model route.

The positive held-out case is an independently encoded vertex relabelling of
W5.  The query is frozen first.  The observation-derived primitive basis and
program must then agree before the registered W5 constructor is allowed to
run on the canonical representative.  Its base abstract certificate fails,
exactly two distinctions are restored with local observations, and the new
query-neutral interval model certifies H=2 planning.  A second occurrence
reuses the immutable model with zero new ground work.  The permutation lifts
that certificate to the preregistered held-out representative.

This is a real constructor/planner integration for one isomorphism closure,
not evidence of transfer to unseen graph structures or another domain.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import construction_k7_observation_derived_primitive_basis_v1 as basis_v1
from acfqp import construction_k7_observation_driven_world_model_synthesis_v3 as synthesis_v3
from acfqp import construction_k7_observed_program_heldout_campaign_v1 as heldout_v1
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_BASIS_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_BASIS_HELDOUT_MODEL_TRANSPORT_V1_DOMAIN,
    CONSTRUCTION_K7_BASIS_HELDOUT_QUERY_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_BASIS_HELDOUT_SYNTHESIS_CAMPAIGN_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.relational_graph_core_v1 import GraphTopologyV1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.153"
PROFILE_KEY = "construction_k7_basis_heldout_world_model_synthesis_v1"

QUERY_DOMAIN = CONSTRUCTION_K7_BASIS_HELDOUT_QUERY_PREREGISTRATION_V1_DOMAIN
TRANSPORT_DOMAIN = CONSTRUCTION_K7_BASIS_HELDOUT_MODEL_TRANSPORT_V1_DOMAIN
PLAN_DOMAIN = CONSTRUCTION_K7_BASIS_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN
CAMPAIGN_DOMAIN = CONSTRUCTION_K7_BASIS_HELDOUT_SYNTHESIS_CAMPAIGN_V1_DOMAIN
LOCAL_DOMAINS = frozenset({QUERY_DOMAIN, TRANSPORT_DOMAIN, PLAN_DOMAIN, CAMPAIGN_DOMAIN})
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("basis-heldout synthesis domains are not central")

_QUERY_ISSUER = object()
_TRANSPORT_ISSUER = object()
_PLAN_ISSUER = object()
_CAMPAIGN_ISSUER = object()


class ConstructionK7BasisHeldoutWorldModelSynthesisV1Error(ValueError):
    """The held-out query, construction, transport, or reuse chain changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7BasisHeldoutWorldModelSynthesisV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7BasisHeldoutWorldModelSynthesisV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _occurrence(label: str, parent_id: str) -> str:
    return content_id(
        CAMPAIGN_DOMAIN,
        {"role": label, "parent_id": _cid(parent_id, f"{label} parent")},
    )


def _relabel_ranks(values: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    if tuple(sorted(permutation)) != tuple(range(len(values))):
        _fail("held-out rank relabelling is not one permutation")
    output = [0] * len(values)
    for source_vertex, target_vertex in enumerate(permutation):
        output[target_vertex] = values[source_vertex]
    return tuple(output)


def _source_result(
    result: synthesis_v3.ObservationDrivenWorldModelSynthesisV3ResultV1,
):
    if type(result) is not synthesis_v3.ObservationDrivenWorldModelSynthesisV3ResultV1:
        _fail("world-model execution has the wrong concrete type")
    return result.executor_result.executor_result


@dataclass(frozen=True, slots=True)
class BasisHeldoutQueryPreregistrationV1:
    _issuer: InitVar[object]
    basis_validation_observation_id: str
    basis_validation_program_evaluation_id: str
    source_context_id: str
    source_topology: GraphTopologyV1
    heldout_topology: GraphTopologyV1
    vertex_permutation: tuple[int, ...]
    source_root_ranks: tuple[int, ...]
    heldout_root_ranks: tuple[int, ...]
    _query_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.basis_validation_observation_id, "basis validation observation"),
            (self.basis_validation_program_evaluation_id, "basis validation program evaluation"),
            (self.source_context_id, "source context"),
        ):
            _cid(value, label)
        relabelled_edges = tuple(
            sorted(
                tuple(sorted((self.vertex_permutation[left], self.vertex_permutation[right])))
                for left, right in self.source_topology.edges
            )
        )
        if (
            _issuer is not _QUERY_ISSUER
            or type(self.source_topology) is not GraphTopologyV1
            or type(self.heldout_topology) is not GraphTopologyV1
            or type(self.vertex_permutation) is not tuple
            or tuple(sorted(self.vertex_permutation))
            != tuple(range(self.source_topology.vertex_count))
            or self.heldout_topology
            != GraphTopologyV1(self.source_topology.vertex_count, relabelled_edges)
            or self.source_topology.topology_id == self.heldout_topology.topology_id
            or type(self.source_root_ranks) is not tuple
            or self.heldout_root_ranks
            != _relabel_ranks(self.source_root_ranks, self.vertex_permutation)
        ):
            _fail("held-out query preregistration changed")
        object.__setattr__(self, "_query_id", content_id(QUERY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_basis_heldout_query_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "basis_validation_observation_id": self.basis_validation_observation_id,
            "basis_validation_program_evaluation_id": self.basis_validation_program_evaluation_id,
            "source_context_id": self.source_context_id,
            "source_topology": self.source_topology.to_document(),
            "heldout_topology": self.heldout_topology.to_document(),
            "vertex_permutation_source_to_heldout": list(self.vertex_permutation),
            "source_root_ranks": list(self.source_root_ranks),
            "heldout_root_ranks": list(self.heldout_root_ranks),
            "horizon": 2,
            "environment_semantics": "VERTEX_RELABEL_TRANSPORT_OF_SOURCE_W5_V1",
            "query_frozen_before_basis_derivation_and_authorized_constructor": True,
            "construction_topology_absent_from_basis_validation_rows": True,
            "query_value_policy_or_ground_input_present": False,
        }

    @property
    def query_id(self) -> str:
        current = content_id(QUERY_DOMAIN, self._payload())
        if current != self._query_id:
            _fail("held-out query identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "basis_heldout_query_id": self.query_id}


@dataclass(frozen=True, slots=True)
class BasisHeldoutModelTransportV1:
    _issuer: InitVar[object]
    query: BasisHeldoutQueryPreregistrationV1
    primitive_campaign_id: str
    primitive_basis_id: str
    source_synthesis: synthesis_v3.ObservationDrivenWorldModelSynthesisV3ResultV1 = field(
        repr=False, compare=False
    )
    source_reuse_result_id: str
    source_reuse_bytes_sha256: str
    source_overlay_id: str
    quotient_model_id: str
    certified_audit_id: str
    _transport_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.primitive_campaign_id, "primitive campaign"),
            (self.primitive_basis_id, "primitive basis"),
            (self.source_reuse_result_id, "source reuse"),
            (self.source_reuse_bytes_sha256, "source reuse digest"),
            (self.source_overlay_id, "source overlay"),
            (self.quotient_model_id, "quotient model"),
            (self.certified_audit_id, "certified audit"),
        ):
            _cid(value, label)
        result = _source_result(self.source_synthesis)
        promotion = result.promotion
        reuse_document = result.reuse_result_document
        final_route = result.final_route
        if (
            _issuer is not _TRANSPORT_ISSUER
            or type(self.query) is not BasisHeldoutQueryPreregistrationV1
            or self.source_synthesis.program_decision.outcome != "PROGRAM_MATCH"
            or self.source_synthesis.program_decision.selected_constructor_key
            != "W5_CHECKPOINT_OVERLAY_V1"
            or result.dispatch.dispatch_outcome != "CONSTRUCT_REGISTERED_MODEL"
            or promotion is None
            or promotion.family_key != "W5"
            or promotion.incremental_ground_draw_count != 4096
            or promotion.changed_row_count != 2
            or promotion.final_overlay_id != self.source_overlay_id
            or promotion.entry.quotient_model_id != self.quotient_model_id
            or promotion.final_audit_id != self.certified_audit_id
            or type(reuse_document) is not dict
            or reuse_document.get("result_id") != self.source_reuse_result_id
            or hashlib.sha256(canonical_json_bytes(reuse_document)).hexdigest()
            != self.source_reuse_bytes_sha256
            or final_route is None
            or final_route.plan is None
            or final_route.plan.audit.audit_id != self.certified_audit_id
        ):
            _fail("basis-authorized source construction chain changed")
        object.__setattr__(
            self, "_transport_id", content_id(TRANSPORT_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_basis_heldout_model_transport.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "basis_heldout_query_id": self.query.query_id,
            "observation_derived_primitive_campaign_id": self.primitive_campaign_id,
            "observation_derived_primitive_basis_id": self.primitive_basis_id,
            "source_world_model_synthesis_v3_result_id": self.source_synthesis.result_id,
            "source_reuse_result_id": self.source_reuse_result_id,
            "source_reuse_bytes_sha256": self.source_reuse_bytes_sha256,
            "source_overlay_id": self.source_overlay_id,
            "quotient_model_id": self.quotient_model_id,
            "certified_audit_id": self.certified_audit_id,
            "selected_constructor_key": "W5_CHECKPOINT_OVERLAY_V1",
            "constructor_selection_authority": "OBSERVATION_DERIVED_PRIMITIVE_BASIS_AND_PROGRAM_V1",
            "legacy_v3_executor_compatibility_cross_check_only": True,
            "base_abstract_certificate_status": "FAILED_PROOF_FRONTIER",
            "local_ground_recovery_triggered_after_failure": True,
            "changed_ground_distinction_count": 2,
            "incremental_local_ground_draw_count": 4096,
            "final_abstract_certificate_status": "CERTIFIED",
            "transport_kind": "VERTEX_PERMUTATION_EQUIVALENCE_CLASS",
            "state_action_bijection_rule": "VERTEX_PERMUTATION_LIFT_V1",
            "canonical_quotient_model_reused_without_row_rewrite": True,
            "heldout_specific_model_bytes_materialized": False,
            "unseen_structure_transfer_allowed": False,
        }

    @property
    def transport_id(self) -> str:
        current = content_id(TRANSPORT_DOMAIN, self._payload())
        if current != self._transport_id:
            _fail("held-out model transport identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "basis_heldout_model_transport_id": self.transport_id}


@dataclass(frozen=True, slots=True)
class BasisHeldoutAbstractPlanV1:
    _issuer: InitVar[object]
    query: BasisHeldoutQueryPreregistrationV1
    transport: BasisHeldoutModelTransportV1
    exact_reuse: synthesis_v3.ObservationDrivenWorldModelSynthesisV3ResultV1 = field(
        repr=False, compare=False
    )
    _plan_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        result = _source_result(self.exact_reuse)
        route = result.final_route
        if (
            _issuer is not _PLAN_ISSUER
            or type(self.query) is not BasisHeldoutQueryPreregistrationV1
            or type(self.transport) is not BasisHeldoutModelTransportV1
            or self.transport.query != self.query
            or self.exact_reuse.program_decision.outcome != "PROGRAM_MATCH"
            or result.dispatch.dispatch_outcome != "REUSE_EXACT_MODEL"
            or result.promotion is not None
            or result.unsupported is not None
            or route is None
            or route.plan is None
            or route.plan.audit.model_id != self.transport.quotient_model_id
            or route.plan.audit.audit_id != self.transport.certified_audit_id
            or route.to_document()["ground_draw_count"] != 0
            or route.to_document()["observer_call_count"] != 0
        ):
            _fail("held-out abstract reuse plan changed")
        object.__setattr__(self, "_plan_id", content_id(PLAN_DOMAIN, self._payload()))

    @property
    def source_route(self):
        route = _source_result(self.exact_reuse).final_route
        assert route is not None and route.plan is not None
        return route

    def _payload(self) -> dict[str, Any]:
        audit = self.source_route.plan.audit
        return {
            "schema": "acfqp.construction_k7_basis_heldout_abstract_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "basis_heldout_query_id": self.query.query_id,
            "basis_heldout_model_transport_id": self.transport.transport_id,
            "exact_reuse_world_model_synthesis_v3_result_id": self.exact_reuse.result_id,
            "source_catalogue_query_result_id": self.source_route.result_id,
            "source_abstract_plan_id": self.source_route.plan.plan_id,
            "quotient_model_id": audit.model_id,
            "certified_audit_id": audit.audit_id,
            "transported_policy_assignment_count": len(audit.assignments),
            "horizon": 2,
            "plan_certificate_kind": "ISOMORPHISM_TRANSPORTED_CONDITIONAL_STATISTICAL",
            "multi_step_plan_completed_in_abstract_model": True,
            "fresh_occurrence_abstract_planner_invocations": 1,
            "fresh_occurrence_model_construction_invocations": 0,
            "fresh_occurrence_observer_call_count": 0,
            "fresh_occurrence_ground_draw_count": 0,
            "ground_solver_invocations": 0,
            "formal_exact_iid_plan_certificate": False,
            "official_execution_allowed": False,
        }

    @property
    def plan_id(self) -> str:
        current = content_id(PLAN_DOMAIN, self._payload())
        if current != self._plan_id:
            _fail("held-out abstract plan identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_replayed_audit": self.source_route.plan.audit.to_document(),
            "basis_heldout_abstract_plan_id": self.plan_id,
        }


@dataclass(frozen=True, slots=True)
class BasisHeldoutWorldModelSynthesisCampaignV1:
    _issuer: InitVar[object]
    primitive_campaign: basis_v1.ObservationDerivedPrimitiveCampaignV1
    query: BasisHeldoutQueryPreregistrationV1
    transport: BasisHeldoutModelTransportV1
    plan: BasisHeldoutAbstractPlanV1
    source_reuse_bytes: bytes = field(repr=False, compare=False)
    heldout_program_campaign_bytes: bytes = field(repr=False, compare=False)
    no_transfer_evaluation_ids: tuple[str, ...]
    _campaign_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        try:
            reuse_document = loads_canonical_json(self.source_reuse_bytes)
            program_document = loads_canonical_json(self.heldout_program_campaign_bytes)
        except (TypeError, ValueError) as error:
            raise ConstructionK7BasisHeldoutWorldModelSynthesisV1Error(
                "source reuse bytes are not canonical"
            ) from error
        if (
            _issuer is not _CAMPAIGN_ISSUER
            or type(self.primitive_campaign) is not basis_v1.ObservationDerivedPrimitiveCampaignV1
            or type(self.query) is not BasisHeldoutQueryPreregistrationV1
            or type(self.transport) is not BasisHeldoutModelTransportV1
            or type(self.plan) is not BasisHeldoutAbstractPlanV1
            or self.transport.query != self.query
            or self.plan.transport != self.transport
            or self.primitive_campaign.campaign_id != self.transport.primitive_campaign_id
            or self.primitive_campaign.basis.basis_id != self.transport.primitive_basis_id
            or type(reuse_document) is not dict
            or canonical_json_bytes(reuse_document) != self.source_reuse_bytes
            or reuse_document.get("result_id") != self.transport.source_reuse_result_id
            or hashlib.sha256(self.source_reuse_bytes).hexdigest()
            != self.transport.source_reuse_bytes_sha256
            or type(program_document) is not dict
            or canonical_json_bytes(program_document) != self.heldout_program_campaign_bytes
            or program_document.get("heldout_program_campaign_id")
            != self.primitive_campaign.program_campaign_id
            or type(self.no_transfer_evaluation_ids) is not tuple
            or len(self.no_transfer_evaluation_ids) != 4
            or self.no_transfer_evaluation_ids
            != tuple(
                row["heldout_evaluation_id"]
                for row in program_document.get("heldout_evaluations", [])[1:]
            )
        ):
            _fail("basis-heldout synthesis campaign changed")
        object.__setattr__(self, "_campaign_id", content_id(CAMPAIGN_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_basis_heldout_synthesis_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "observation_derived_primitive_campaign_id": self.primitive_campaign.campaign_id,
            "basis_heldout_query_id": self.query.query_id,
            "basis_heldout_model_transport_id": self.transport.transport_id,
            "basis_heldout_abstract_plan_id": self.plan.plan_id,
            "source_reuse_result_id": self.transport.source_reuse_result_id,
            "source_reuse_bytes_sha256": self.transport.source_reuse_bytes_sha256,
            "ordered_no_transfer_evaluation_ids": list(self.no_transfer_evaluation_ids),
            "world_model_construction_count": 1,
            "abstract_h2_plan_count": 2,
            "local_ground_recovery_count": 1,
            "incremental_local_ground_draw_count": 4096,
            "local_ground_triggered_only_after_certificate_failure": True,
            "fresh_reuse_ground_draw_count": 0,
            "unseen_structure_constructor_invocation_count": 0,
            "cross_domain_constructor_invocation_count": 0,
            "reusable_abstract_world_model_synthesized": True,
            "multi_step_planning_mainly_completed_in_abstract_model": True,
            "heldout_positive_scope": "FRESH_PREREGISTERED_W5_VERTEX_RELABEL_ISOMORPHISM_ONLY",
            "broad_graph_or_cross_domain_generalization_claimed": False,
            "human_registered_relational_meta_grammar": True,
            "open_ended_operator_invention_claimed": False,
            "formal_exact_iid_plan_certificate": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": "NOT_RUN",
            "workload_economics_gate_status": "NOT_RUN",
        }

    @property
    def campaign_id(self) -> str:
        current = content_id(CAMPAIGN_DOMAIN, self._payload())
        if current != self._campaign_id:
            _fail("basis-heldout campaign identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        reuse_document = loads_canonical_json(self.source_reuse_bytes)
        return {
            **self._payload(),
            "primitive_campaign": self.primitive_campaign.to_document(),
            "heldout_query": self.query.to_document(),
            "model_transport": self.transport.to_document(),
            "heldout_plan": self.plan.to_document(),
            "source_reuse_result": reuse_document,
            "heldout_program_campaign": loads_canonical_json(
                self.heldout_program_campaign_bytes
            ),
            "basis_heldout_synthesis_campaign_id": self.campaign_id,
        }


def run_basis_heldout_world_model_synthesis_v1() -> BasisHeldoutWorldModelSynthesisCampaignV1:
    program_campaign = heldout_v1.run_observed_program_heldout_campaign_v1()
    positive_case = program_campaign.preregistration.cases[0]
    positive_evaluation = program_campaign.evaluations[0]
    validation_observation = positive_case.observation
    source_context = observer_v1.public_context_by_key_v1("opaque_graph_w5_v0")
    if (
        validation_observation.topology is None
        or validation_observation.source_topology != source_context.topology
        or validation_observation.vertex_permutation is None
        or positive_evaluation.outcome != heldout_v1.PROGRAM_MATCH
        or positive_evaluation.selected_constructor_key != "W5_CHECKPOINT_OVERLAY_V1"
    ):
        _fail("held-out positive program evidence changed before query freeze")
    construction_permutation = (2, 4, 1, 3, 0)
    construction_topology = GraphTopologyV1(
        source_context.topology.vertex_count,
        tuple(
            sorted(
                tuple(sorted((construction_permutation[left], construction_permutation[right])))
                for left, right in source_context.topology.edges
            )
        ),
    )
    if construction_topology.topology_id in {
        source_context.topology.topology_id,
        validation_observation.topology.topology_id,
    }:
        _fail("fresh construction relabelling did not create a new encoded identity")
    query = BasisHeldoutQueryPreregistrationV1(
        _QUERY_ISSUER,
        validation_observation.observation_id,
        positive_evaluation.evaluation_id,
        source_context.context_id,
        source_context.topology,
        construction_topology,
        construction_permutation,
        source_context.root_ranks,
        _relabel_ranks(source_context.root_ranks, construction_permutation),
    )

    primitive_campaign = basis_v1.run_observation_derived_primitive_campaign_v1()
    if (
        primitive_campaign.program_campaign_id != program_campaign.campaign_id
        or primitive_campaign.evaluations[0].observation_id
        != validation_observation.observation_id
        or primitive_campaign.evaluations[0].outcome != "BASIS_REPLAY_MATCH"
    ):
        _fail("primitive basis did not validate the preregistered positive")
    fresh_rows = basis_v1.evaluate_basis_v1(
        primitive_campaign.basis, construction_topology
    )
    w5_program = next(
        row
        for row in program_campaign.proposals
        if row.constructor_key == "W5_CHECKPOINT_OVERLAY_V1"
    )
    if fresh_rows != w5_program.selected_atoms:
        _fail("fresh held-out topology did not match the validated basis/program")

    empty_catalogue = catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(())
    source = synthesis_v3.run_observation_driven_world_model_synthesis_v3(
        empty_catalogue,
        source_context,
        logical_occurrence_id=_occurrence("basis-authorized-construction", query.query_id),
        occurrence_ordinal=1,
        selected_reuse_result_bytes=None,
    )
    source_result = _source_result(source)
    if source_result.reuse_result_document is None or source_result.promotion is None:
        _fail("basis-authorized constructor produced no reusable model")
    reuse_bytes = canonical_json_bytes(source_result.reuse_result_document)
    entry = catalogue_v1.build_heldout_reusable_model_catalogue_entry_v1("W5", reuse_bytes)
    catalogue = catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1((entry,))
    reused = synthesis_v3.run_observation_driven_world_model_synthesis_v3(
        catalogue,
        source_context,
        logical_occurrence_id=_occurrence("heldout-isomorphism-reuse", query.query_id),
        occurrence_ordinal=2,
        selected_reuse_result_bytes=reuse_bytes,
    )
    promotion = source_result.promotion
    transport = BasisHeldoutModelTransportV1(
        _TRANSPORT_ISSUER,
        query,
        primitive_campaign.campaign_id,
        primitive_campaign.basis.basis_id,
        source,
        source_result.reuse_result_document["result_id"],
        hashlib.sha256(reuse_bytes).hexdigest(),
        promotion.final_overlay_id,
        promotion.entry.quotient_model_id,
        promotion.final_audit_id,
    )
    plan = BasisHeldoutAbstractPlanV1(_PLAN_ISSUER, query, transport, reused)
    no_transfer_ids = tuple(row.evaluation_id for row in program_campaign.evaluations[1:])
    return BasisHeldoutWorldModelSynthesisCampaignV1(
        _CAMPAIGN_ISSUER,
        primitive_campaign,
        query,
        transport,
        plan,
        reuse_bytes,
        canonical_json_bytes(program_campaign.to_document()),
        no_transfer_ids,
    )


def verify_basis_heldout_world_model_synthesis_v1(
    campaign: BasisHeldoutWorldModelSynthesisCampaignV1,
) -> BasisHeldoutWorldModelSynthesisCampaignV1:
    if type(campaign) is not BasisHeldoutWorldModelSynthesisCampaignV1:
        _fail("basis-heldout verifier rejects foreign values")
    basis_v1.verify_observation_derived_primitive_campaign_v1(campaign.primitive_campaign)
    synthesis_v3.verify_observation_driven_world_model_synthesis_v3(
        observer_v1.public_context_by_key_v1("opaque_graph_w5_v0"),
        campaign.transport.source_synthesis,
    )
    synthesis_v3.verify_observation_driven_world_model_synthesis_v3(
        observer_v1.public_context_by_key_v1("opaque_graph_w5_v0"),
        campaign.plan.exact_reuse,
    )
    campaign.__post_init__(_CAMPAIGN_ISSUER)
    return campaign


__all__ = (
    "BasisHeldoutAbstractPlanV1",
    "BasisHeldoutModelTransportV1",
    "BasisHeldoutQueryPreregistrationV1",
    "BasisHeldoutWorldModelSynthesisCampaignV1",
    "ConstructionK7BasisHeldoutWorldModelSynthesisV1Error",
    "LOCAL_DOMAINS",
    "run_basis_heldout_world_model_synthesis_v1",
    "verify_basis_heldout_world_model_synthesis_v1",
)
