"""Producer-free replay of the observation-derived graph primitive basis."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import combinations
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_BASIS_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CAMPAIGN_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_EVALUATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_CAMPAIGN_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT = "2.0.152"
PROFILE = "construction_k7_observation_derived_primitive_basis_v1"
VERIFIER_PROFILE = (
    "construction_k7_observation_derived_primitive_independent_verifier_v1"
)
VERIFY_DOMAIN = (
    CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_INDEPENDENT_VERIFICATION_V1_DOMAIN
)
if VERIFY_DOMAIN not in PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("primitive independent verification domain is not central")

META_OPERATORS = (
    "CARDINALITY",
    "CONNECTED_CLOSURE",
    "DISTINCT",
    "INCIDENCE_COUNT",
    "MAXIMUM",
    "ORDERED_PAIR_LIFT",
    "SORTED_MULTISET",
    "THREE_CLIQUE_WITNESS",
    "ZERO_COUNT",
)
SOURCE_RELATIONS = ("EDGE_RELATION", "VERTEX_RELATION")
SPECS = (
    ("connected_component_sizes", ("SORTED_MULTISET", "CARDINALITY", "CONNECTED_CLOSURE", "EDGE_RELATION")),
    ("edge_count", ("CARDINALITY", "EDGE_RELATION")),
    ("sorted_degree_sequence", ("SORTED_MULTISET", "INCIDENCE_COUNT", "EDGE_RELATION", "VERTEX_RELATION")),
    ("triangle_count", ("CARDINALITY", "THREE_CLIQUE_WITNESS", "EDGE_RELATION")),
    ("vertex_count", ("CARDINALITY", "VERTEX_RELATION")),
    ("connected_component_count_candidate", ("CARDINALITY", "CONNECTED_CLOSURE", "EDGE_RELATION")),
    ("maximum_degree_candidate", ("MAXIMUM", "INCIDENCE_COUNT", "EDGE_RELATION", "VERTEX_RELATION")),
    ("distinct_degree_count_candidate", ("CARDINALITY", "DISTINCT", "INCIDENCE_COUNT", "EDGE_RELATION", "VERTEX_RELATION")),
    ("ordered_edge_endpoint_count_candidate", ("CARDINALITY", "ORDERED_PAIR_LIFT", "EDGE_RELATION")),
    ("isolated_vertex_count_candidate", ("ZERO_COUNT", "INCIDENCE_COUNT", "EDGE_RELATION", "VERTEX_RELATION")),
)
GRAPH_TOPOLOGY_DOMAIN = "acfqp:relational-graph-topology:v1"
SOURCE_GRAPHS = (
    (5, ((0, 1), (0, 3), (0, 4), (1, 2), (1, 4), (2, 3), (2, 4), (3, 4))),
    (6, tuple(combinations(range(6), 2))),
    (6, tuple(edge for edge in combinations(range(6), 2) if edge != (4, 5))),
)


class ConstructionK7ObservationDerivedPrimitiveIndependentVerifierV1Error(ValueError):
    """Canonical primitive-basis bytes do not independently replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservationDerivedPrimitiveIndependentVerifierV1Error(message)


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} field set changed")
    return value


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservationDerivedPrimitiveIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _topology_id(vertex_count: int, edges: tuple[tuple[int, int], ...]) -> str:
    payload = {
        "schema": "acfqp.graph_topology.v1",
        "schema_version": "1.0.0",
        "vertex_count": vertex_count,
        "edges": [list(edge) for edge in edges],
    }
    return hashlib.sha256(
        GRAPH_TOPOLOGY_DOMAIN.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _values(vertex_count: int, edges: tuple[tuple[int, int], ...]) -> tuple[Any, ...]:
    neighbours = {vertex: set() for vertex in range(vertex_count)}
    for left, right in edges:
        neighbours[left].add(right)
        neighbours[right].add(left)
    unseen = set(neighbours)
    components = []
    while unseen:
        frontier = {min(unseen)}
        seen = set()
        while frontier:
            vertex = frontier.pop()
            if vertex not in seen:
                seen.add(vertex)
                frontier.update(neighbours[vertex] - seen)
        unseen -= seen
        components.append(len(seen))
    edge_set = set(edges)
    triangles = sum(
        1
        for left, middle, right in combinations(range(vertex_count), 3)
        if (left, middle) in edge_set
        and (left, right) in edge_set
        and (middle, right) in edge_set
    )
    return (
        tuple(sorted(components)),
        len(edges),
        tuple(sorted(len(row) for row in neighbours.values())),
        triangles,
        vertex_count,
        len(components),
        max(len(row) for row in neighbours.values()),
        len({len(row) for row in neighbours.values()}),
        2 * len(edges),
        sum(len(row) == 0 for row in neighbours.values()),
    )


def _decode(value: Any) -> Any:
    return tuple(value) if type(value) is list else value


@dataclass(frozen=True, slots=True)
class ObservationDerivedPrimitiveIndependentVerificationV1:
    campaign_id: str
    basis_id: str
    candidate_ids: tuple[str, ...]
    evaluation_ids: tuple[str, ...]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observation_derived_primitive_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": VERIFIER_PROFILE,
            "observation_derived_primitive_campaign_id": self.campaign_id,
            "observation_derived_primitive_basis_id": self.basis_id,
            "ordered_primitive_candidate_ids": list(self.candidate_ids),
            "ordered_primitive_evaluation_ids": list(self.evaluation_ids),
            "raw_relation_expressions_replayed": True,
            "source_observation_columns_replayed": True,
            "heldout_observation_columns_replayed": True,
            "program_obligation_basis_selection_replayed": True,
            "constructor_or_ground_execution_verified": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return content_id(VERIFY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "independent_verification_id": self.verification_id}


def verify_observation_derived_primitive_campaign_bytes_independently_v1(
    raw: bytes,
) -> ObservationDerivedPrimitiveIndependentVerificationV1:
    if type(raw) is not bytes:
        _fail("primitive independent verifier requires exact bytes")
    root = loads_canonical_json(raw)
    if type(root) is not dict or canonical_json_bytes(root) != raw:
        _fail("primitive campaign is not canonical JSON")
    root = _exact(
        root,
        {
            "schema", "schema_version", "proposed_contract_version", "profile_key",
            "source_heldout_program_campaign_id", "observation_derived_primitive_basis_id",
            "ordered_primitive_evaluation_ids", "graph_heldout_replay_match_count",
            "typed_cross_domain_no_evaluation_count", "basis_ready_for_constructor_authority",
            "constructor_invocation_count", "ground_access_count",
            "human_registered_relational_meta_grammar", "open_ended_operator_invention_claimed",
            "official_execution_allowed", "basis", "evaluations",
            "observation_derived_primitive_campaign_id",
        },
        "primitive campaign",
    )
    if (
        root["schema"] != "acfqp.construction_k7_observation_derived_primitive_campaign.v1"
        or root["schema_version"] != SCHEMA_VERSION
        or root["proposed_contract_version"] != CONTRACT
        or root["profile_key"] != PROFILE
        or root["graph_heldout_replay_match_count"] != 4
        or root["typed_cross_domain_no_evaluation_count"] != 1
        or root["basis_ready_for_constructor_authority"] is not True
        or root["constructor_invocation_count"] != 0
        or root["ground_access_count"] != 0
        or root["human_registered_relational_meta_grammar"] is not True
        or root["open_ended_operator_invention_claimed"] is not False
        or root["official_execution_allowed"] is not False
    ):
        _fail("primitive campaign claim boundary changed")
    _cid(root["source_heldout_program_campaign_id"], "source program campaign")

    basis = _exact(
        root["basis"],
        {
            "schema", "schema_version", "proposed_contract_version", "profile_key",
            "ordered_source_topology_ids", "heldout_preregistration_id",
            "relational_meta_operators", "source_relations", "ordered_candidate_ids",
            "selected_candidate_ids", "selected_compatibility_primitives",
            "candidate_count", "selected_count", "selection_rule",
            "final_feature_names_used_as_candidate_inputs",
            "primitive_values_compiled_from_raw_relations",
            "heldout_observations_frozen_before_basis_derivation",
            "human_registered_relational_meta_grammar", "open_ended_operator_invention_claimed",
            "primitive_candidates", "observation_derived_primitive_basis_id",
        },
        "primitive basis",
    )
    source_ids = [_topology_id(count, edges) for count, edges in SOURCE_GRAPHS]
    source_columns = tuple(zip(*(_values(count, edges) for count, edges in SOURCE_GRAPHS)))
    candidates = basis["primitive_candidates"]
    if type(candidates) is not list or len(candidates) != len(SPECS):
        _fail("primitive candidate inventory changed")
    candidate_ids = []
    heldout_columns = []
    for ordinal, (candidate, spec, expected_column) in enumerate(
        zip(candidates, SPECS, source_columns)
    ):
        candidate = _exact(
            candidate,
            {
                "schema", "schema_version", "proposed_contract_version", "profile_key",
                "candidate_ordinal", "candidate_key", "compatibility_name", "compiled_expression",
                "source_observation_column", "heldout_observation_column", "selected",
                "raw_relation_inputs", "query_value_policy_or_ground_input_present",
                "primitive_candidate_id",
            },
            "primitive candidate",
        )
        if (
            candidate["schema"] != "acfqp.construction_k7_observation_derived_primitive_candidate.v1"
            or candidate["schema_version"] != SCHEMA_VERSION
            or candidate["proposed_contract_version"] != CONTRACT
            or candidate["profile_key"] != PROFILE
            or candidate["candidate_ordinal"] != ordinal
            or candidate["candidate_key"] != spec[0]
            or candidate["compatibility_name"]
            != (spec[0] if ordinal < 5 else None)
            or candidate["compiled_expression"] != list(spec[1])
            or tuple(_decode(value) for value in candidate["source_observation_column"])
            != expected_column
            or candidate["selected"] is not (ordinal < 5)
            or candidate["raw_relation_inputs"] != list(SOURCE_RELATIONS)
            or candidate["query_value_policy_or_ground_input_present"] is not False
        ):
            _fail("primitive candidate semantic replay changed")
        payload = {key: value for key, value in candidate.items() if key != "primitive_candidate_id"}
        identifier = content_id(
            CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CANDIDATE_V1_DOMAIN,
            payload,
        )
        if candidate["primitive_candidate_id"] != identifier:
            _fail("primitive candidate content ID changed")
        candidate_ids.append(identifier)
        heldout_columns.append(
            tuple(_decode(value) for value in candidate["heldout_observation_column"])
        )
    expected_basis_payload = {key: value for key, value in basis.items() if key not in {"primitive_candidates", "observation_derived_primitive_basis_id"}}
    if (
        basis["schema"] != "acfqp.construction_k7_observation_derived_primitive_basis.v1"
        or basis["ordered_source_topology_ids"] != source_ids
        or basis["relational_meta_operators"] != list(META_OPERATORS)
        or basis["source_relations"] != list(SOURCE_RELATIONS)
        or basis["ordered_candidate_ids"] != candidate_ids
        or basis["selected_candidate_ids"] != candidate_ids[:5]
        or basis["selected_compatibility_primitives"] != [name for name, _ in SPECS[:5]]
        or basis["candidate_count"] != 10
        or basis["selected_count"] != 5
        or basis["selection_rule"] != "UNIQUE_SOURCE_COLUMN_THEN_PROGRAM_OBLIGATION_CLOSURE"
        or basis["final_feature_names_used_as_candidate_inputs"] is not False
        or basis["primitive_values_compiled_from_raw_relations"] is not True
        or basis["heldout_observations_frozen_before_basis_derivation"] is not True
        or basis["human_registered_relational_meta_grammar"] is not True
        or basis["open_ended_operator_invention_claimed"] is not False
    ):
        _fail("primitive basis semantic replay changed")
    basis_id = content_id(
        CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_BASIS_V1_DOMAIN,
        expected_basis_payload,
    )
    if basis["observation_derived_primitive_basis_id"] != basis_id or root["observation_derived_primitive_basis_id"] != basis_id:
        _fail("primitive basis content ID changed")

    evaluations = root["evaluations"]
    if type(evaluations) is not list or len(evaluations) != 5:
        _fail("primitive evaluation inventory changed")
    evaluation_ids = []
    for index, evaluation in enumerate(evaluations):
        evaluation = _exact(
            evaluation,
            {
                "schema", "schema_version", "proposed_contract_version", "profile_key",
                "observation_derived_primitive_basis_id", "heldout_observation_id",
                "case_key", "domain_schema", "derived_feature_rows", "expected_feature_rows",
                "evaluation_outcome", "transition_or_ground_access_count",
                "primitive_evaluation_id",
            },
            "primitive evaluation",
        )
        expected_values = tuple(column[index] for column in heldout_columns[:5]) if index < 4 else ()
        derived_values = tuple(_decode(row["value"]) for row in evaluation["derived_feature_rows"])
        expected_row_values = tuple(_decode(row["value"]) for row in evaluation["expected_feature_rows"])
        expected_outcome = "BASIS_REPLAY_MATCH" if index < 4 else "TYPED_SCHEMA_NO_EVALUATION"
        if (
            evaluation["schema"] != "acfqp.construction_k7_observation_derived_primitive_evaluation.v1"
            or evaluation["observation_derived_primitive_basis_id"] != basis_id
            or derived_values != expected_values
            or (index < 4 and expected_row_values != expected_values)
            or (index == 4 and derived_values != ())
            or evaluation["evaluation_outcome"] != expected_outcome
            or evaluation["transition_or_ground_access_count"] != 0
        ):
            _fail("primitive held-out evaluation replay changed")
        payload = {key: value for key, value in evaluation.items() if key != "primitive_evaluation_id"}
        identifier = content_id(
            CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_EVALUATION_V1_DOMAIN,
            payload,
        )
        if evaluation["primitive_evaluation_id"] != identifier:
            _fail("primitive evaluation content ID changed")
        evaluation_ids.append(identifier)
    root_payload = {
        key: value
        for key, value in root.items()
        if key not in {"basis", "evaluations", "observation_derived_primitive_campaign_id"}
    }
    campaign_id = content_id(
        CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CAMPAIGN_V1_DOMAIN,
        root_payload,
    )
    if (
        root["ordered_primitive_evaluation_ids"] != evaluation_ids
        or root["observation_derived_primitive_campaign_id"] != campaign_id
    ):
        _fail("primitive campaign content chain changed")
    return ObservationDerivedPrimitiveIndependentVerificationV1(
        campaign_id,
        basis_id,
        tuple(candidate_ids),
        tuple(evaluation_ids),
    )


__all__ = (
    "ConstructionK7ObservationDerivedPrimitiveIndependentVerifierV1Error",
    "ObservationDerivedPrimitiveIndependentVerificationV1",
    "verify_observation_derived_primitive_campaign_bytes_independently_v1",
)
