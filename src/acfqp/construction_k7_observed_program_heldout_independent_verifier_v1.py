"""Producer-free replay of the held-out capability-program campaign."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import combinations
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_SIGNATURE_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_CORPUS_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_GRAMMAR_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_CAMPAIGN_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_EVALUATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_OBSERVATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_PROPOSAL_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_observed_program_heldout_independent_verifier_v1"
PROGRAM_PROFILE = "construction_k7_observed_capability_program_synthesis_v1"
PROGRAM_CONTRACT = "2.0.145"
SIGNATURE_PROFILE = "construction_k7_observed_constructor_capability_v1"
SIGNATURE_CONTRACT = "2.0.143"
HELDOUT_PROFILE = "construction_k7_observed_program_heldout_campaign_v1"
HELDOUT_CONTRACT = "2.0.150"
GRAPH_SCHEMA = "GRAPH_TOPOLOGY_INVARIANTS_V1"
LMB_SCHEMA = "LMB_PUBLIC_STRUCTURE_V1"
GRAPH_TOPOLOGY_DOMAIN = "acfqp:relational-graph-topology:v1"
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_INDEPENDENT_VERIFICATION_V1_DOMAIN
)
if VERIFICATION_DOMAIN not in PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out program verification domain is not central")

FEATURES = (
    "connected_component_sizes",
    "edge_count",
    "sorted_degree_sequence",
    "triangle_count",
    "vertex_count",
)
SUBSETS = tuple(
    subset
    for size in range(1, len(FEATURES) + 1)
    for subset in combinations(FEATURES, size)
)
SOURCE_SIGNATURES = (
    (
        "8766333359a2c2f80ea0819be6c4ebafdf170b82912ba573b9cd6e3a486daceb",
        "76496aa59674a2bae4cf5f43f7f5eaa86c63370bad8b53425c5b84add938e098",
        5,
        8,
        (3, 3, 3, 3, 4),
        (5,),
        4,
    ),
    (
        "f5a228a9ea48652a38feac07f6144a027192ad57fefb862ac8f444a2f3c6a783",
        "136b1849ed066cd3f12feb205c3b3bc165a99ded6106437977dd0287e8ffeac0",
        6,
        15,
        (5, 5, 5, 5, 5, 5),
        (6,),
        20,
    ),
    (
        "5a6f748d691230ca7173288a790812d165efc0f0f723dba70e4d312304474037",
        "77f6955117462a0b7d12882217698c0a4ed7bf4616c8ac288c0c84e28f6948f4",
        6,
        14,
        (4, 4, 5, 5, 5, 5),
        (6,),
        16,
    ),
)
CONSTRUCTORS = (
    ("W5", "W5_CHECKPOINT_OVERLAY_V1", 0),
    ("K6", "K6_CHECKPOINT_OVERLAY_V1", 1),
)
EXPECTED_CASES = (
    (
        "W5_ISOMORPHIC_RELABEL_HELDOUT",
        GRAPH_SCHEMA,
        "VERTEX_RELABEL_OF_SOURCE_W5",
        "PROGRAM_TRANSFER_MATCH",
        "W5_CHECKPOINT_OVERLAY_V1",
    ),
    (
        "WHEEL6_OOD",
        GRAPH_SCHEMA,
        "SAME_DOMAIN_UNSEEN_STRUCTURE",
        "NO_SOUND_PROGRAM",
        None,
    ),
    (
        "COMPLETE7_OOD",
        GRAPH_SCHEMA,
        "CROSS_VERTEX_COUNT_UNSEEN_STRUCTURE",
        "NO_SOUND_PROGRAM",
        None,
    ),
    (
        "PATH6_OOD",
        GRAPH_SCHEMA,
        "SAME_DOMAIN_UNSEEN_STRUCTURE",
        "NO_SOUND_PROGRAM",
        None,
    ),
    (
        "LMB_N6_T2_K3_D2_CROSS_DOMAIN",
        LMB_SCHEMA,
        "CROSS_DOMAIN_TYPED_CONTROL",
        "TYPED_SCHEMA_NO_TRANSFER",
        None,
    ),
)


class ConstructionK7ObservedProgramHeldoutIndependentVerifierV1Error(ValueError):
    """Canonical held-out program bytes do not independently replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservedProgramHeldoutIndependentVerifierV1Error(message)


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{label} field set changed")
    return value


def _rows(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        _fail(f"{label} must be one exact list")
    return value


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservedProgramHeldoutIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _base(row: dict[str, Any], profile: str, contract: str, schema: str) -> None:
    if (
        row.get("schema") != schema
        or row.get("schema_version") != SCHEMA_VERSION
        or row.get("proposed_contract_version") != contract
        or row.get("profile_key") != profile
    ):
        _fail(f"{schema} contract changed")


def _signature(document: Any, expected: tuple[Any, ...]) -> tuple[str, dict[str, Any]]:
    row = _exact(
        document,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "context_id",
            "topology_id",
            "vertex_count",
            "edge_count",
            "sorted_degree_sequence",
            "connected_component_sizes",
            "triangle_count",
            "signature_is_vertex_relabelling_invariant",
            "context_key_used_as_signature_input",
            "query_value_policy_or_ground_oracle_input_present",
            "observed_constructor_signature_id",
        },
        "source signature",
    )
    _base(
        row,
        SIGNATURE_PROFILE,
        SIGNATURE_CONTRACT,
        "acfqp.construction_k7_observed_constructor_signature.v1",
    )
    observed = (
        row["context_id"],
        row["topology_id"],
        row["vertex_count"],
        row["edge_count"],
        tuple(row["sorted_degree_sequence"]),
        tuple(row["connected_component_sizes"]),
        row["triangle_count"],
    )
    if (
        observed != expected
        or row["signature_is_vertex_relabelling_invariant"] is not True
        or row["context_key_used_as_signature_input"] is not False
        or row["query_value_policy_or_ground_oracle_input_present"] is not False
    ):
        _fail("source signature semantics changed")
    payload = {key: value for key, value in row.items() if key != "observed_constructor_signature_id"}
    identifier = content_id(CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_SIGNATURE_V1_DOMAIN, payload)
    if row["observed_constructor_signature_id"] != identifier:
        _fail("source signature content ID changed")
    return identifier, row


def _grammar(document: Any) -> str:
    row = _exact(
        document,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "ordered_primitives",
            "ordered_operators",
            "maximum_conjunction_atom_count",
            "literal_values_must_come_from_positive_observations",
            "context_key_query_value_policy_or_ground_oracle_primitive_present",
            "human_registered_primitive_and_operator_vocabulary",
            "automatic_primitive_or_operator_invention_claimed",
            "observed_program_grammar_id",
        },
        "source program grammar",
    )
    _base(
        row,
        PROGRAM_PROFILE,
        PROGRAM_CONTRACT,
        "acfqp.construction_k7_observed_program_grammar.v1",
    )
    if (
        row["ordered_primitives"] != list(FEATURES)
        or row["ordered_operators"] != ["EQUALS", "AND"]
        or row["maximum_conjunction_atom_count"] != len(FEATURES)
        or row["literal_values_must_come_from_positive_observations"] is not True
        or row["context_key_query_value_policy_or_ground_oracle_primitive_present"] is not False
        or row["human_registered_primitive_and_operator_vocabulary"] is not True
        or row["automatic_primitive_or_operator_invention_claimed"] is not False
    ):
        _fail("source program grammar semantics changed")
    payload = {key: value for key, value in row.items() if key != "observed_program_grammar_id"}
    identifier = content_id(CONSTRUCTION_K7_OBSERVED_PROGRAM_GRAMMAR_V1_DOMAIN, payload)
    if row["observed_program_grammar_id"] != identifier:
        _fail("source grammar content ID changed")
    return identifier


def _feature_values(signature: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return (
        ("connected_component_sizes", tuple(signature["connected_component_sizes"])),
        ("edge_count", signature["edge_count"]),
        ("sorted_degree_sequence", tuple(signature["sorted_degree_sequence"])),
        ("triangle_count", signature["triangle_count"]),
        ("vertex_count", signature["vertex_count"]),
    )


def _mutate(value: Any) -> Any:
    if type(value) is int:
        return value + 1
    if type(value) is tuple and value:
        changed = list(value)
        changed[0] += 1
        return tuple(sorted(changed))
    _fail("source control mutation changed")


def _matches(atoms: tuple[tuple[str, Any], ...], values: tuple[tuple[str, Any], ...]) -> bool:
    observed = dict(values)
    return all(observed.get(name, object()) == literal for name, literal in atoms)


def _candidate_rows(
    atoms: tuple[tuple[str, Any], ...],
    positive_index: int,
    signatures: tuple[tuple[str, dict[str, Any]], ...],
) -> list[dict[str, Any]]:
    positive_id, positive = signatures[positive_index]
    positive_values = _feature_values(positive)
    rows = [
        {
            "example_key": f"POSITIVE:{positive_id}",
            "expected": True,
            "observed": _matches(atoms, positive_values),
        }
    ]
    for index, (signature_id, signature) in enumerate(signatures):
        if index != positive_index:
            rows.append(
                {
                    "example_key": f"REAL_NEGATIVE:{signature_id}",
                    "expected": False,
                    "observed": _matches(atoms, _feature_values(signature)),
                }
            )
    for changed_name, original in positive_values:
        mutated = tuple(
            (name, _mutate(value) if name == changed_name else value)
            for name, value in positive_values
        )
        rows.append(
            {
                "example_key": f"SINGLE_FEATURE_COUNTERFACTUAL:{changed_name}",
                "expected": False,
                "observed": _matches(atoms, mutated),
            }
        )
    return rows


def _corpus(document: Any, grammar_id: str) -> tuple[str, tuple[tuple[str, dict[str, Any]], ...]]:
    row = _exact(
        document,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "observed_program_grammar_id",
            "ordered_real_signature_ids",
            "constructor_labels",
            "single_feature_counterfactual_control_count_per_constructor",
            "real_nearby_negative_control_present",
            "all_corpus_identities_frozen_before_subset_enumeration",
            "context_keys_are_labels_not_program_inputs",
            "real_signatures",
            "observed_program_corpus_id",
        },
        "source program corpus",
    )
    _base(
        row,
        PROGRAM_PROFILE,
        PROGRAM_CONTRACT,
        "acfqp.construction_k7_observed_program_corpus.v1",
    )
    signatures = tuple(
        _signature(item, expected)
        for item, expected in zip(
            _rows(row["real_signatures"], "source signatures"), SOURCE_SIGNATURES
        )
    )
    expected_labels = [
        {
            "family_key": family,
            "constructor_key": constructor,
            "positive_context_id": SOURCE_SIGNATURES[index][0],
        }
        for family, constructor, index in CONSTRUCTORS
    ]
    if (
        len(signatures) != len(SOURCE_SIGNATURES)
        or row["observed_program_grammar_id"] != grammar_id
        or row["ordered_real_signature_ids"] != [item[0] for item in signatures]
        or row["constructor_labels"] != expected_labels
        or row["single_feature_counterfactual_control_count_per_constructor"] != 5
        or row["real_nearby_negative_control_present"] is not True
        or row["all_corpus_identities_frozen_before_subset_enumeration"] is not True
        or row["context_keys_are_labels_not_program_inputs"] is not True
    ):
        _fail("source program corpus semantics changed")
    payload = {
        key: value
        for key, value in row.items()
        if key != "observed_program_corpus_id"
    }
    identifier = content_id(CONSTRUCTION_K7_OBSERVED_PROGRAM_CORPUS_V1_DOMAIN, payload)
    if row["observed_program_corpus_id"] != identifier:
        _fail("source program corpus content ID changed")
    return identifier, signatures


def _proposal(
    document: Any,
    grammar_id: str,
    corpus_id: str,
    signatures: tuple[tuple[str, dict[str, Any]], ...],
    expected_constructor: tuple[str, str, int],
) -> tuple[str, tuple[tuple[str, Any], ...], str]:
    row = _exact(
        document,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "observed_program_grammar_id",
            "observed_program_corpus_id",
            "family_key",
            "constructor_key",
            "ordered_candidate_ids",
            "selected_candidate_id",
            "selected_atoms",
            "candidate_count",
            "selection_rule",
            "literal_values_observation_derived",
            "fixed_human_signature_value_table_used",
            "human_registered_primitive_and_operator_vocabulary",
            "automatic_primitive_or_operator_invention_claimed",
            "observed_program_proposal_id",
            "candidates",
        },
        "source program proposal",
    )
    _base(
        row,
        PROGRAM_PROFILE,
        PROGRAM_CONTRACT,
        "acfqp.construction_k7_observed_program_proposal.v1",
    )
    family, constructor, positive_index = expected_constructor
    positive_values = dict(_feature_values(signatures[positive_index][1]))
    candidates = []
    for ordinal, document_candidate in enumerate(
        _rows(row["candidates"], "source program candidates")
    ):
        candidate = _exact(
            document_candidate,
            {
                "schema",
                "schema_version",
                "proposed_contract_version",
                "profile_key",
                "observed_program_grammar_id",
                "observed_program_corpus_id",
                "family_key",
                "constructor_key",
                "candidate_ordinal",
                "atoms",
                "evaluation_rows",
                "accepted",
                "context_key_read_during_program_evaluation",
                "observed_program_candidate_id",
            },
            "source program candidate",
        )
        _base(
            candidate,
            PROGRAM_PROFILE,
            PROGRAM_CONTRACT,
            "acfqp.construction_k7_observed_program_candidate.v1",
        )
        if ordinal >= len(SUBSETS):
            _fail("source program candidate count increased")
        atoms = tuple((name, positive_values[name]) for name in SUBSETS[ordinal])
        atom_doc = [
            {
                "primitive": name,
                "operator": "EQUALS",
                "observed_value": list(value) if type(value) is tuple else value,
            }
            for name, value in atoms
        ]
        evaluation_rows = _candidate_rows(atoms, positive_index, signatures)
        accepted = all(item["expected"] == item["observed"] for item in evaluation_rows)
        if (
            candidate["observed_program_grammar_id"] != grammar_id
            or candidate["observed_program_corpus_id"] != corpus_id
            or candidate["family_key"] != family
            or candidate["constructor_key"] != constructor
            or candidate["candidate_ordinal"] != ordinal
            or candidate["atoms"] != atom_doc
            or candidate["evaluation_rows"] != evaluation_rows
            or candidate["accepted"] is not accepted
            or candidate["context_key_read_during_program_evaluation"] is not False
        ):
            _fail("source program candidate differs from complete enumeration")
        payload = {
            key: value
            for key, value in candidate.items()
            if key != "observed_program_candidate_id"
        }
        candidate_id = content_id(
            CONSTRUCTION_K7_OBSERVED_PROGRAM_CANDIDATE_V1_DOMAIN, payload
        )
        if candidate["observed_program_candidate_id"] != candidate_id:
            _fail("source program candidate content ID changed")
        candidates.append((candidate_id, atoms, accepted))
    accepted_rows = [item for item in candidates if item[2]]
    if (
        len(candidates) != len(SUBSETS)
        or len(accepted_rows) != 1
        or row["observed_program_grammar_id"] != grammar_id
        or row["observed_program_corpus_id"] != corpus_id
        or (row["family_key"], row["constructor_key"]) != (family, constructor)
        or row["ordered_candidate_ids"] != [item[0] for item in candidates]
        or row["selected_candidate_id"] != accepted_rows[0][0]
        or row["selected_atoms"]
        != [
            {
                "primitive": name,
                "operator": "EQUALS",
                "observed_value": list(value) if type(value) is tuple else value,
            }
            for name, value in accepted_rows[0][1]
        ]
        or row["candidate_count"] != len(SUBSETS)
        or row["selection_rule"]
        != "UNIQUE_COMPLETE_CORPUS_AND_SINGLE_FEATURE_CONTROL_SEPARATOR"
        or row["literal_values_observation_derived"] is not True
        or row["fixed_human_signature_value_table_used"] is not False
        or row["human_registered_primitive_and_operator_vocabulary"] is not True
        or row["automatic_primitive_or_operator_invention_claimed"] is not False
    ):
        _fail("source program proposal semantics changed")
    payload = {
        key: value
        for key, value in row.items()
        if key not in {"candidates", "observed_program_proposal_id"}
    }
    identifier = content_id(CONSTRUCTION_K7_OBSERVED_PROGRAM_PROPOSAL_V1_DOMAIN, payload)
    if row["observed_program_proposal_id"] != identifier:
        _fail("source program proposal content ID changed")
    return identifier, accepted_rows[0][1], constructor


def _topology(document: Any, label: str) -> tuple[str, int, tuple[tuple[int, int], ...]]:
    row = _exact(
        document,
        {"schema", "schema_version", "vertex_count", "edges", "topology_id"},
        label,
    )
    vertex_count = row["vertex_count"]
    edges = tuple(tuple(edge) for edge in _rows(row["edges"], f"{label} edges"))
    if (
        row["schema"] != "acfqp.graph_topology.v1"
        or row["schema_version"] != "1.0.0"
        or type(vertex_count) is not int
        or vertex_count <= 1
        or not edges
        or edges != tuple(sorted(set(edges)))
        or any(
            len(edge) != 2
            or any(type(vertex) is not int for vertex in edge)
            or not 0 <= edge[0] < edge[1] < vertex_count
            for edge in edges
        )
    ):
        _fail(f"{label} topology changed")
    payload = {key: value for key, value in row.items() if key != "topology_id"}
    identifier = hashlib.sha256(
        GRAPH_TOPOLOGY_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    if row["topology_id"] != identifier:
        _fail(f"{label} topology ID changed")
    return identifier, vertex_count, edges


def _graph_features(vertex_count: int, edges: tuple[tuple[int, int], ...]) -> tuple[tuple[str, Any], ...]:
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
    values = {
        "connected_component_sizes": tuple(sorted(components)),
        "edge_count": len(edges),
        "sorted_degree_sequence": tuple(sorted(len(neighbours[row]) for row in neighbours)),
        "triangle_count": triangles,
        "vertex_count": vertex_count,
    }
    return tuple((name, values[name]) for name in FEATURES)


def _observation(
    document: Any,
    expected: tuple[str, str, str, str, str | None],
    source_w5_topology_id: str,
) -> tuple[str, str, tuple[tuple[str, Any], ...]]:
    row = _exact(
        document,
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "case_key",
            "domain_schema",
            "structure",
            "relation_kind",
            "source_topology",
            "vertex_permutation",
            "observed_feature_rows",
            "context_key_query_value_policy_or_ground_input_present",
            "transition_row_count",
            "heldout_observation_id",
        },
        "held-out observation",
    )
    _base(
        row,
        HELDOUT_PROFILE,
        HELDOUT_CONTRACT,
        "acfqp.construction_k7_observed_program_heldout_observation.v1",
    )
    case_key, domain_schema, relation_kind, _outcome, _constructor = expected
    if (
        (row["case_key"], row["domain_schema"], row["relation_kind"])
        != (case_key, domain_schema, relation_kind)
        or row["context_key_query_value_policy_or_ground_input_present"] is not False
        or row["transition_row_count"] != 0
    ):
        _fail("held-out observation labels or access locks changed")
    if domain_schema == GRAPH_SCHEMA:
        topology_id, vertex_count, edges = _topology(row["structure"], "held-out")
        features = _graph_features(vertex_count, edges)
        if relation_kind == "VERTEX_RELABEL_OF_SOURCE_W5":
            source_id, source_count, source_edges = _topology(
                row["source_topology"], "held-out source"
            )
            permutation = tuple(row["vertex_permutation"])
            if (
                source_id != source_w5_topology_id
                or tuple(sorted(permutation)) != tuple(range(source_count))
                or vertex_count != source_count
                or edges
                != tuple(
                    sorted(
                        tuple(sorted((permutation[left], permutation[right])))
                        for left, right in source_edges
                    )
                )
                or topology_id == source_id
            ):
                _fail("held-out isomorphic relation evidence changed")
        elif row["source_topology"] is not None or row["vertex_permutation"] is not None:
            _fail("held-out OOD graph acquired source relation evidence")
        feature_doc = [
            {"primitive": name, "value": list(value) if type(value) is tuple else value}
            for name, value in features
        ]
        if row["observed_feature_rows"] != feature_doc:
            _fail("held-out graph features differ from topology replay")
    else:
        expected_structure = {
            "buffer_capacity": 3,
            "layer_count": 6,
            "program_depth": 2,
            "tile_type_count": 2,
        }
        if (
            row["structure"] != expected_structure
            or row["source_topology"] is not None
            or row["vertex_permutation"] is not None
            or row["observed_feature_rows"]
            != [{"primitive": key, "value": value} for key, value in expected_structure.items()]
        ):
            _fail("held-out cross-domain structure changed")
        features = tuple(expected_structure.items())
    payload = {key: value for key, value in row.items() if key != "heldout_observation_id"}
    identifier = content_id(
        CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_OBSERVATION_V1_DOMAIN, payload
    )
    if row["heldout_observation_id"] != identifier:
        _fail("held-out observation content ID changed")
    return identifier, domain_schema, features


@dataclass(frozen=True, slots=True)
class HeldoutProgramIndependentVerificationV1:
    campaign_id: str
    preregistration_id: str
    source_program_proposal_ids: tuple[str, ...]
    evaluation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (
            self.campaign_id,
            self.preregistration_id,
            *self.source_program_proposal_ids,
            *self.evaluation_ids,
        ):
            _cid(value, "held-out independent verification input")
        if len(self.source_program_proposal_ids) != 2 or len(self.evaluation_ids) != 5:
            _fail("held-out independent verification inventory changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_program_heldout_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "heldout_program_campaign_id": self.campaign_id,
            "heldout_preregistration_id": self.preregistration_id,
            "ordered_source_program_proposal_ids": list(self.source_program_proposal_ids),
            "ordered_heldout_evaluation_ids": list(self.evaluation_ids),
            "source_candidate_lattice_replayed": True,
            "heldout_topology_features_replayed": True,
            "transfer_and_no_transfer_decisions_replayed": True,
            "constructor_or_model_execution_verified": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return content_id(VERIFICATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "independent_verification_id": self.verification_id}


def verify_observed_program_heldout_campaign_bytes_independently_v1(
    raw: bytes,
) -> HeldoutProgramIndependentVerificationV1:
    if type(raw) is not bytes:
        _fail("held-out independent verifier requires exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("held-out campaign is not canonical JSON")
    root_keys = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "heldout_preregistration_id",
        "source_program_grammar_id",
        "source_program_corpus_id",
        "ordered_source_program_proposal_ids",
        "ordered_heldout_evaluation_ids",
        "heldout_case_count",
        "isomorphic_positive_program_transfer_count",
        "same_domain_no_transfer_count",
        "cross_vertex_count_no_transfer_count",
        "cross_domain_typed_no_transfer_count",
        "constructor_invocation_count",
        "model_transfer_attempt_count",
        "ground_access_count",
        "heldout_program_transfer_evaluation_complete",
        "human_registered_primitive_and_operator_vocabulary",
        "automatic_primitive_or_operator_invention_claimed",
        "constructor_or_model_transfer_authority_present",
        "broad_graph_or_cross_domain_generalization_claimed",
        "official_execution_allowed",
        "preregistration",
        "source_program_grammar",
        "source_program_corpus",
        "source_program_proposals",
        "heldout_evaluations",
        "heldout_program_campaign_id",
    }
    root = _exact(document, root_keys, "held-out campaign")
    _base(
        root,
        HELDOUT_PROFILE,
        HELDOUT_CONTRACT,
        "acfqp.construction_k7_observed_program_heldout_campaign.v1",
    )
    grammar_id = _grammar(root["source_program_grammar"])
    corpus_id, signatures = _corpus(root["source_program_corpus"], grammar_id)
    proposals = tuple(
        _proposal(item, grammar_id, corpus_id, signatures, expected)
        for item, expected in zip(
            _rows(root["source_program_proposals"], "source proposals"), CONSTRUCTORS
        )
    )
    if len(proposals) != 2:
        _fail("held-out source proposal count changed")
    prereg = _exact(
        root["preregistration"],
        {
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "ordered_cases",
            "heldout_case_count",
            "source_program_ids_absent_at_preregistration",
            "heldout_observations_frozen_before_source_program_synthesis",
            "expected_labels_not_available_to_program_evaluator",
            "heldout_preregistration_id",
        },
        "held-out preregistration",
    )
    _base(
        prereg,
        HELDOUT_PROFILE,
        HELDOUT_CONTRACT,
        "acfqp.construction_k7_observed_program_heldout_preregistration.v1",
    )
    observations = []
    for case_document, expected in zip(
        _rows(prereg["ordered_cases"], "held-out cases"), EXPECTED_CASES
    ):
        case = _exact(
            case_document,
            {"observation", "expected_outcome", "expected_constructor_key"},
            "held-out case",
        )
        observation = _observation(case["observation"], expected, signatures[0][1]["topology_id"])
        if (case["expected_outcome"], case["expected_constructor_key"]) != expected[3:]:
            _fail("held-out expected decision changed")
        observations.append(observation)
    if (
        len(observations) != len(EXPECTED_CASES)
        or prereg["heldout_case_count"] != len(EXPECTED_CASES)
        or prereg["source_program_ids_absent_at_preregistration"] is not True
        or prereg["heldout_observations_frozen_before_source_program_synthesis"] is not True
        or prereg["expected_labels_not_available_to_program_evaluator"] is not True
    ):
        _fail("held-out preregistration semantics changed")
    prereg_payload = {
        key: value for key, value in prereg.items() if key != "heldout_preregistration_id"
    }
    preregistration_id = content_id(
        CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_PREREGISTRATION_V1_DOMAIN,
        prereg_payload,
    )
    if prereg["heldout_preregistration_id"] != preregistration_id:
        _fail("held-out preregistration content ID changed")
    proposal_ids = tuple(row[0] for row in proposals)
    evaluations = []
    for document_evaluation, observation, expected in zip(
        _rows(root["heldout_evaluations"], "held-out evaluations"),
        observations,
        EXPECTED_CASES,
    ):
        evaluation = _exact(
            document_evaluation,
            {
                "schema",
                "schema_version",
                "proposed_contract_version",
                "profile_key",
                "heldout_preregistration_id",
                "heldout_observation_id",
                "ordered_source_program_proposal_ids",
                "matched_source_program_proposal_ids",
                "decision_outcome",
                "selected_constructor_key",
                "context_key_or_expected_label_read_by_evaluator",
                "constructor_invocation_count",
                "model_transfer_attempt_count",
                "ground_access_count",
                "program_transfer_evaluation_only",
                "heldout_evaluation_id",
            },
            "held-out evaluation",
        )
        _base(
            evaluation,
            HELDOUT_PROFILE,
            HELDOUT_CONTRACT,
            "acfqp.construction_k7_observed_program_heldout_evaluation.v1",
        )
        observation_id, domain_schema, features = observation
        matched = (
            ()
            if domain_schema != GRAPH_SCHEMA
            else tuple(row for row in proposals if _matches(row[1], features))
        )
        outcome = (
            "TYPED_SCHEMA_NO_TRANSFER"
            if domain_schema != GRAPH_SCHEMA
            else "PROGRAM_TRANSFER_MATCH"
            if len(matched) == 1
            else "NO_SOUND_PROGRAM"
            if not matched
            else "AMBIGUOUS"
        )
        selected = None if len(matched) != 1 else matched[0][2]
        if (
            outcome == "AMBIGUOUS"
            or evaluation["heldout_preregistration_id"] != preregistration_id
            or evaluation["heldout_observation_id"] != observation_id
            or evaluation["ordered_source_program_proposal_ids"] != list(proposal_ids)
            or evaluation["matched_source_program_proposal_ids"]
            != [row[0] for row in matched]
            or (evaluation["decision_outcome"], evaluation["selected_constructor_key"])
            != (outcome, selected)
            or (outcome, selected) != expected[3:]
            or evaluation["context_key_or_expected_label_read_by_evaluator"] is not False
            or evaluation["constructor_invocation_count"] != 0
            or evaluation["model_transfer_attempt_count"] != 0
            or evaluation["ground_access_count"] != 0
            or evaluation["program_transfer_evaluation_only"] is not True
        ):
            _fail("held-out transfer decision differs from independent replay")
        evaluation_payload = {
            key: value for key, value in evaluation.items() if key != "heldout_evaluation_id"
        }
        evaluation_id = content_id(
            CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_EVALUATION_V1_DOMAIN,
            evaluation_payload,
        )
        if evaluation["heldout_evaluation_id"] != evaluation_id:
            _fail("held-out evaluation content ID changed")
        evaluations.append(evaluation_id)
    root_payload = {
        key: value
        for key, value in root.items()
        if key
        not in {
            "preregistration",
            "source_program_grammar",
            "source_program_corpus",
            "source_program_proposals",
            "heldout_evaluations",
            "heldout_program_campaign_id",
        }
    }
    campaign_id = content_id(
        CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_CAMPAIGN_V1_DOMAIN, root_payload
    )
    if (
        root["heldout_program_campaign_id"] != campaign_id
        or root["heldout_preregistration_id"] != preregistration_id
        or root["source_program_grammar_id"] != grammar_id
        or root["source_program_corpus_id"] != corpus_id
        or root["ordered_source_program_proposal_ids"] != list(proposal_ids)
        or root["ordered_heldout_evaluation_ids"] != evaluations
        or root["heldout_case_count"] != 5
        or root["isomorphic_positive_program_transfer_count"] != 1
        or root["same_domain_no_transfer_count"] != 3
        or root["cross_vertex_count_no_transfer_count"] != 1
        or root["cross_domain_typed_no_transfer_count"] != 1
        or root["constructor_invocation_count"] != 0
        or root["model_transfer_attempt_count"] != 0
        or root["ground_access_count"] != 0
        or root["heldout_program_transfer_evaluation_complete"] is not True
        or root["human_registered_primitive_and_operator_vocabulary"] is not True
        or root["automatic_primitive_or_operator_invention_claimed"] is not False
        or root["constructor_or_model_transfer_authority_present"] is not False
        or root["broad_graph_or_cross_domain_generalization_claimed"] is not False
        or root["official_execution_allowed"] is not False
    ):
        _fail("held-out campaign root differs from independent replay")
    return HeldoutProgramIndependentVerificationV1(
        campaign_id,
        preregistration_id,
        proposal_ids,
        tuple(evaluations),
    )


__all__ = (
    "ConstructionK7ObservedProgramHeldoutIndependentVerifierV1Error",
    "HeldoutProgramIndependentVerificationV1",
    "verify_observed_program_heldout_campaign_bytes_independently_v1",
)
