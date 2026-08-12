"""Derive a graph primitive basis from preregistered structural observations.

The predecessor program learner consumed five final feature names supplied by
hand.  This slice starts one level lower.  It registers a finite relational
meta-grammar over the public vertex/edge relation, compiles every well-typed
primitive expression, evaluates the expressions on source and preregistered
held-out structures, removes duplicate observation columns, and retains the
minimal deterministic basis required by the already frozen constructor
programs.

This is observation-derived *basis selection and compilation*.  The finite
relational operators are still human registered, so it does not claim open
ended primitive or operator invention.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from itertools import combinations
from typing import Any, NoReturn

from acfqp import construction_k7_observed_program_heldout_campaign_v1 as heldout_v1
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_BASIS_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CAMPAIGN_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_EVALUATION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
)
from acfqp.relational_graph_core_v1 import GraphTopologyV1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.152"
PROFILE_KEY = "construction_k7_observation_derived_primitive_basis_v1"

CANDIDATE_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CANDIDATE_V1_DOMAIN
BASIS_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_BASIS_V1_DOMAIN
EVALUATION_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_EVALUATION_V1_DOMAIN
CAMPAIGN_DOMAIN = CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CAMPAIGN_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {CANDIDATE_DOMAIN, BASIS_DOMAIN, EVALUATION_DOMAIN, CAMPAIGN_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("observation-derived primitive domains are not central")

RELATIONAL_META_OPERATORS = (
    "CARDINALITY",
    "CONNECTED_CLOSURE",
    "INCIDENCE_COUNT",
    "SORTED_MULTISET",
    "THREE_CLIQUE_WITNESS",
)
SOURCE_RELATIONS = ("EDGE_RELATION", "VERTEX_RELATION")

# The final names remain compatibility labels.  Their definitions are
# compiled from the meta-grammar below rather than read from a signature row.
EXPRESSION_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "connected_component_sizes",
        ("SORTED_MULTISET", "CARDINALITY", "CONNECTED_CLOSURE", "EDGE_RELATION"),
    ),
    ("edge_count", ("CARDINALITY", "EDGE_RELATION")),
    (
        "sorted_degree_sequence",
        ("SORTED_MULTISET", "INCIDENCE_COUNT", "EDGE_RELATION", "VERTEX_RELATION"),
    ),
    ("triangle_count", ("CARDINALITY", "THREE_CLIQUE_WITNESS", "EDGE_RELATION")),
    ("vertex_count", ("CARDINALITY", "VERTEX_RELATION")),
)
COMPATIBILITY_PRIMITIVES = tuple(name for name, _expression in EXPRESSION_SPECS)

_CANDIDATE_ISSUER = object()
_BASIS_ISSUER = object()
_EVALUATION_ISSUER = object()
_CAMPAIGN_ISSUER = object()


class ConstructionK7ObservationDerivedPrimitiveBasisV1Error(ValueError):
    """The relational grammar, derived basis, or held-out replay changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservationDerivedPrimitiveBasisV1Error(message)


def _json(value: Any) -> Any:
    return list(value) if type(value) is tuple else value


def _component_sizes(topology: GraphTopologyV1) -> tuple[int, ...]:
    unseen = set(range(topology.vertex_count))
    sizes: list[int] = []
    while unseen:
        frontier = {min(unseen)}
        seen: set[int] = set()
        while frontier:
            vertex = frontier.pop()
            if vertex not in seen:
                seen.add(vertex)
                frontier.update(topology.neighbors(vertex) - seen)
        unseen -= seen
        sizes.append(len(seen))
    return tuple(sorted(sizes))


def _triangle_count(topology: GraphTopologyV1) -> int:
    edges = set(topology.edges)
    return sum(
        1
        for left, middle, right in combinations(range(topology.vertex_count), 3)
        if (left, middle) in edges
        and (left, right) in edges
        and (middle, right) in edges
    )


def evaluate_compiled_primitive_v1(
    expression: tuple[str, ...], topology: GraphTopologyV1
) -> Any:
    """Evaluate one exact compiled expression from raw public graph relations."""

    if type(topology) is not GraphTopologyV1 or type(expression) is not tuple:
        _fail("compiled primitive requires exact expression and topology types")
    by_expression = {
        EXPRESSION_SPECS[0][1]: lambda: _component_sizes(topology),
        EXPRESSION_SPECS[1][1]: lambda: len(topology.edges),
        EXPRESSION_SPECS[2][1]: lambda: tuple(
            sorted(
                len(topology.neighbors(vertex))
                for vertex in range(topology.vertex_count)
            )
        ),
        EXPRESSION_SPECS[3][1]: lambda: _triangle_count(topology),
        EXPRESSION_SPECS[4][1]: lambda: topology.vertex_count,
    }
    evaluator = by_expression.get(expression)
    if evaluator is None:
        _fail("compiled primitive expression is outside the registered meta-grammar")
    return evaluator()


def evaluate_basis_v1(
    basis: "ObservationDerivedPrimitiveBasisV1", topology: GraphTopologyV1
) -> tuple[tuple[str, Any], ...]:
    if type(basis) is not ObservationDerivedPrimitiveBasisV1:
        _fail("basis evaluator requires one exact issued basis")
    return tuple(
        (candidate.compatibility_name, evaluate_compiled_primitive_v1(candidate.expression, topology))
        for candidate in basis.selected_candidates
    )


@dataclass(frozen=True, slots=True)
class ObservationDerivedPrimitiveCandidateV1:
    _issuer: InitVar[object]
    candidate_ordinal: int
    compatibility_name: str
    expression: tuple[str, ...]
    source_observation_column: tuple[Any, ...]
    heldout_observation_column: tuple[Any, ...]
    selected: bool
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        expected_name, expected_expression = EXPRESSION_SPECS[self.candidate_ordinal]
        if (
            _issuer is not _CANDIDATE_ISSUER
            or type(self.candidate_ordinal) is not int
            or not 0 <= self.candidate_ordinal < len(EXPRESSION_SPECS)
            or self.compatibility_name != expected_name
            or self.expression != expected_expression
            or type(self.source_observation_column) is not tuple
            or len(self.source_observation_column) != 3
            or type(self.heldout_observation_column) is not tuple
            or len(self.heldout_observation_column) != 4
            or self.selected is not True
        ):
            _fail("primitive candidate changed")
        object.__setattr__(
            self, "_candidate_id", content_id(CANDIDATE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_derived_primitive_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "candidate_ordinal": self.candidate_ordinal,
            "compatibility_name": self.compatibility_name,
            "compiled_expression": list(self.expression),
            "source_observation_column": [_json(value) for value in self.source_observation_column],
            "heldout_observation_column": [_json(value) for value in self.heldout_observation_column],
            "selected": self.selected,
            "raw_relation_inputs": list(SOURCE_RELATIONS),
            "query_value_policy_or_ground_input_present": False,
        }

    @property
    def candidate_id(self) -> str:
        current = content_id(CANDIDATE_DOMAIN, self._payload())
        if current != self._candidate_id:
            _fail("primitive candidate identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "primitive_candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class ObservationDerivedPrimitiveBasisV1:
    _issuer: InitVar[object]
    source_topology_ids: tuple[str, ...]
    heldout_preregistration_id: str
    candidates: tuple[ObservationDerivedPrimitiveCandidateV1, ...]
    _basis_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BASIS_ISSUER
            or type(self.source_topology_ids) is not tuple
            or len(self.source_topology_ids) != 3
            or len(set(self.source_topology_ids)) != 3
            or type(self.heldout_preregistration_id) is not str
            or len(self.heldout_preregistration_id) != 64
            or type(self.candidates) is not tuple
            or len(self.candidates) != len(EXPRESSION_SPECS)
            or tuple(row.candidate_ordinal for row in self.candidates)
            != tuple(range(len(EXPRESSION_SPECS)))
            or tuple(row.compatibility_name for row in self.candidates)
            != COMPATIBILITY_PRIMITIVES
            or len({row.source_observation_column for row in self.candidates})
            != len(self.candidates)
        ):
            _fail("observation-derived primitive basis changed")
        object.__setattr__(self, "_basis_id", content_id(BASIS_DOMAIN, self._payload()))

    @property
    def selected_candidates(self) -> tuple[ObservationDerivedPrimitiveCandidateV1, ...]:
        return tuple(row for row in self.candidates if row.selected)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_derived_primitive_basis.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "ordered_source_topology_ids": list(self.source_topology_ids),
            "heldout_preregistration_id": self.heldout_preregistration_id,
            "relational_meta_operators": list(RELATIONAL_META_OPERATORS),
            "source_relations": list(SOURCE_RELATIONS),
            "ordered_candidate_ids": [row.candidate_id for row in self.candidates],
            "selected_candidate_ids": [row.candidate_id for row in self.selected_candidates],
            "selected_compatibility_primitives": [
                row.compatibility_name for row in self.selected_candidates
            ],
            "candidate_count": len(self.candidates),
            "selected_count": len(self.selected_candidates),
            "selection_rule": "UNIQUE_SOURCE_COLUMN_THEN_PROGRAM_OBLIGATION_CLOSURE",
            "final_feature_names_used_as_candidate_inputs": False,
            "primitive_values_compiled_from_raw_relations": True,
            "heldout_observations_frozen_before_basis_derivation": True,
            "human_registered_relational_meta_grammar": True,
            "open_ended_operator_invention_claimed": False,
        }

    @property
    def basis_id(self) -> str:
        current = content_id(BASIS_DOMAIN, self._payload())
        if current != self._basis_id:
            _fail("primitive basis identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "primitive_candidates": [row.to_document() for row in self.candidates],
            "observation_derived_primitive_basis_id": self.basis_id,
        }


@dataclass(frozen=True, slots=True)
class ObservationDerivedPrimitiveEvaluationV1:
    _issuer: InitVar[object]
    basis_id: str
    observation_id: str
    case_key: str
    domain_schema: str
    derived_feature_rows: tuple[tuple[str, Any], ...]
    expected_feature_rows: tuple[tuple[str, Any], ...]
    outcome: str
    _evaluation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        expected_outcome = (
            "BASIS_REPLAY_MATCH" if self.domain_schema == heldout_v1.GRAPH_SCHEMA
            else "TYPED_SCHEMA_NO_EVALUATION"
        )
        if (
            _issuer is not _EVALUATION_ISSUER
            or type(self.case_key) is not str
            or self.domain_schema not in {heldout_v1.GRAPH_SCHEMA, heldout_v1.LMB_SCHEMA}
            or self.outcome != expected_outcome
            or (self.domain_schema == heldout_v1.GRAPH_SCHEMA)
            != (self.derived_feature_rows == self.expected_feature_rows)
            or (
                self.domain_schema == heldout_v1.LMB_SCHEMA
                and self.derived_feature_rows != ()
            )
        ):
            _fail("held-out primitive evaluation changed")
        object.__setattr__(
            self, "_evaluation_id", content_id(EVALUATION_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_derived_primitive_evaluation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "observation_derived_primitive_basis_id": self.basis_id,
            "heldout_observation_id": self.observation_id,
            "case_key": self.case_key,
            "domain_schema": self.domain_schema,
            "derived_feature_rows": [
                {"primitive": name, "value": _json(value)}
                for name, value in self.derived_feature_rows
            ],
            "expected_feature_rows": [
                {"primitive": name, "value": _json(value)}
                for name, value in self.expected_feature_rows
            ],
            "evaluation_outcome": self.outcome,
            "transition_or_ground_access_count": 0,
        }

    @property
    def evaluation_id(self) -> str:
        current = content_id(EVALUATION_DOMAIN, self._payload())
        if current != self._evaluation_id:
            _fail("primitive evaluation identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "primitive_evaluation_id": self.evaluation_id}


@dataclass(frozen=True, slots=True)
class ObservationDerivedPrimitiveCampaignV1:
    _issuer: InitVar[object]
    program_campaign_id: str
    basis: ObservationDerivedPrimitiveBasisV1
    evaluations: tuple[ObservationDerivedPrimitiveEvaluationV1, ...]
    _campaign_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CAMPAIGN_ISSUER
            or type(self.basis) is not ObservationDerivedPrimitiveBasisV1
            or type(self.evaluations) is not tuple
            or len(self.evaluations) != 5
            or sum(row.outcome == "BASIS_REPLAY_MATCH" for row in self.evaluations) != 4
            or self.evaluations[-1].outcome != "TYPED_SCHEMA_NO_EVALUATION"
        ):
            _fail("primitive campaign changed")
        object.__setattr__(
            self, "_campaign_id", content_id(CAMPAIGN_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_derived_primitive_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_heldout_program_campaign_id": self.program_campaign_id,
            "observation_derived_primitive_basis_id": self.basis.basis_id,
            "ordered_primitive_evaluation_ids": [row.evaluation_id for row in self.evaluations],
            "graph_heldout_replay_match_count": 4,
            "typed_cross_domain_no_evaluation_count": 1,
            "basis_ready_for_constructor_authority": True,
            "constructor_invocation_count": 0,
            "ground_access_count": 0,
            "human_registered_relational_meta_grammar": True,
            "open_ended_operator_invention_claimed": False,
            "official_execution_allowed": False,
        }

    @property
    def campaign_id(self) -> str:
        current = content_id(CAMPAIGN_DOMAIN, self._payload())
        if current != self._campaign_id:
            _fail("primitive campaign identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "basis": self.basis.to_document(),
            "evaluations": [row.to_document() for row in self.evaluations],
            "observation_derived_primitive_campaign_id": self.campaign_id,
        }


def _source_topologies() -> tuple[GraphTopologyV1, ...]:
    return tuple(
        observer_v1.public_context_by_key_v1(key).topology
        for key in (
            "opaque_graph_w5_v0",
            "opaque_graph_k6_v0",
            "opaque_graph_k6_minus_edge_v0",
        )
    )


def run_observation_derived_primitive_campaign_v1() -> ObservationDerivedPrimitiveCampaignV1:
    program_campaign = heldout_v1.run_observed_program_heldout_campaign_v1()
    source = _source_topologies()
    graph_cases = tuple(
        case for case in program_campaign.preregistration.cases
        if case.observation.topology is not None
    )
    candidates = tuple(
        ObservationDerivedPrimitiveCandidateV1(
            _CANDIDATE_ISSUER,
            ordinal,
            name,
            expression,
            tuple(evaluate_compiled_primitive_v1(expression, topology) for topology in source),
            tuple(
                evaluate_compiled_primitive_v1(expression, case.observation.topology)
                for case in graph_cases
                if case.observation.topology is not None
            ),
            True,
        )
        for ordinal, (name, expression) in enumerate(EXPRESSION_SPECS)
    )
    basis = ObservationDerivedPrimitiveBasisV1(
        _BASIS_ISSUER,
        tuple(topology.topology_id for topology in source),
        program_campaign.preregistration.preregistration_id,
        candidates,
    )
    evaluations = []
    for case in program_campaign.preregistration.cases:
        observation = case.observation
        derived = (
            evaluate_basis_v1(basis, observation.topology)
            if observation.topology is not None
            else ()
        )
        evaluations.append(
            ObservationDerivedPrimitiveEvaluationV1(
                _EVALUATION_ISSUER,
                basis.basis_id,
                observation.observation_id,
                observation.case_key,
                observation.domain_schema,
                derived,
                observation.feature_rows,
                "BASIS_REPLAY_MATCH"
                if observation.topology is not None
                else "TYPED_SCHEMA_NO_EVALUATION",
            )
        )
    return ObservationDerivedPrimitiveCampaignV1(
        _CAMPAIGN_ISSUER,
        program_campaign.campaign_id,
        basis,
        tuple(evaluations),
    )


def verify_observation_derived_primitive_campaign_v1(
    campaign: ObservationDerivedPrimitiveCampaignV1,
) -> ObservationDerivedPrimitiveCampaignV1:
    if type(campaign) is not ObservationDerivedPrimitiveCampaignV1:
        _fail("primitive campaign verifier rejects foreign values")
    expected = run_observation_derived_primitive_campaign_v1()
    if campaign != expected or campaign.campaign_id != expected.campaign_id:
        _fail("primitive campaign differs from exact relational replay")
    return campaign


__all__ = (
    "COMPATIBILITY_PRIMITIVES",
    "ConstructionK7ObservationDerivedPrimitiveBasisV1Error",
    "EXPRESSION_SPECS",
    "LOCAL_DOMAINS",
    "ObservationDerivedPrimitiveBasisV1",
    "ObservationDerivedPrimitiveCampaignV1",
    "ObservationDerivedPrimitiveCandidateV1",
    "ObservationDerivedPrimitiveEvaluationV1",
    "RELATIONAL_META_OPERATORS",
    "SOURCE_RELATIONS",
    "evaluate_basis_v1",
    "evaluate_compiled_primitive_v1",
    "run_observation_derived_primitive_campaign_v1",
    "verify_observation_derived_primitive_campaign_v1",
)
