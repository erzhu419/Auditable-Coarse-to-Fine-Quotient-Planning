"""Observation-derived constructor capability proposal for graph contexts.

The proposer receives one frozen public graph context and computes an
isomorphism-invariant structural signature.  Every preregistered constructor
capability is evaluated against that signature; no context key participates in
matching.  Exactly one matching capability may be selected.  An unmatched
structure is a typed no-capability decision and does not inherit a nearby
model or constructor.

The capability predicates are still a small human-registered vocabulary.  The
module removes context-key lookup as construction authority, but does not
claim automatic primitive/operator invention or broad graph generalization.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_DECISION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_SIGNATURE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.143"
PROFILE_KEY = "construction_k7_observed_constructor_capability_v1"

SIGNATURE_DOMAIN = CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_SIGNATURE_V1_DOMAIN
CANDIDATE_DOMAIN = CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_CANDIDATE_V1_DOMAIN
DECISION_DOMAIN = CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_DECISION_V1_DOMAIN
LOCAL_DOMAINS = frozenset({SIGNATURE_DOMAIN, CANDIDATE_DOMAIN, DECISION_DOMAIN})
if len(LOCAL_DOMAINS) != 3 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("observed constructor capability domains are not central")

_SIGNATURE_ISSUER = object()
_CANDIDATE_ISSUER = object()
_DECISION_ISSUER = object()


class ConstructionK7ObservedConstructorCapabilityV1Error(ValueError):
    """The observed signature, candidate trace, or selection changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservedConstructorCapabilityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservedConstructorCapabilityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _component_sizes(vertex_count: int, edges: tuple[tuple[int, int], ...]) -> tuple[int, ...]:
    neighbours = {vertex: set() for vertex in range(vertex_count)}
    for left, right in edges:
        neighbours[left].add(right)
        neighbours[right].add(left)
    unseen = set(neighbours)
    sizes: list[int] = []
    while unseen:
        frontier = {min(unseen)}
        seen: set[int] = set()
        while frontier:
            vertex = frontier.pop()
            if vertex in seen:
                continue
            seen.add(vertex)
            frontier.update(neighbours[vertex] - seen)
        unseen -= seen
        sizes.append(len(seen))
    return tuple(sorted(sizes))


def _triangle_count(vertex_count: int, edges: tuple[tuple[int, int], ...]) -> int:
    edge_set = {tuple(sorted(edge)) for edge in edges}
    return sum(
        1
        for left in range(vertex_count)
        for middle in range(left + 1, vertex_count)
        for right in range(middle + 1, vertex_count)
        if (left, middle) in edge_set
        and (left, right) in edge_set
        and (middle, right) in edge_set
    )


@dataclass(frozen=True, slots=True)
class ObservedGraphConstructorSignatureV1:
    _issuer: InitVar[object]
    context_id: str
    topology_id: str
    vertex_count: int
    edge_count: int
    sorted_degree_sequence: tuple[int, ...]
    connected_component_sizes: tuple[int, ...]
    triangle_count: int
    _signature_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _SIGNATURE_ISSUER
            or type(self.vertex_count) is not int
            or self.vertex_count <= 0
            or type(self.edge_count) is not int
            or self.edge_count < 0
            or type(self.sorted_degree_sequence) is not tuple
            or len(self.sorted_degree_sequence) != self.vertex_count
            or self.sorted_degree_sequence != tuple(sorted(self.sorted_degree_sequence))
            or any(type(value) is not int or value < 0 for value in self.sorted_degree_sequence)
            or sum(self.sorted_degree_sequence) != 2 * self.edge_count
            or type(self.connected_component_sizes) is not tuple
            or self.connected_component_sizes != tuple(sorted(self.connected_component_sizes))
            or sum(self.connected_component_sizes) != self.vertex_count
            or type(self.triangle_count) is not int
            or self.triangle_count < 0
        ):
            _fail("observed graph signature is malformed")
        _cid(self.context_id, "signature context")
        _cid(self.topology_id, "signature topology")
        object.__setattr__(
            self, "_signature_id", content_id(SIGNATURE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_constructor_signature.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "topology_id": self.topology_id,
            "vertex_count": self.vertex_count,
            "edge_count": self.edge_count,
            "sorted_degree_sequence": list(self.sorted_degree_sequence),
            "connected_component_sizes": list(self.connected_component_sizes),
            "triangle_count": self.triangle_count,
            "signature_is_vertex_relabelling_invariant": True,
            "context_key_used_as_signature_input": False,
            "query_value_policy_or_ground_oracle_input_present": False,
        }

    @property
    def signature_id(self) -> str:
        current = content_id(SIGNATURE_DOMAIN, self._payload())
        if current != self._signature_id:
            _fail("observed graph signature changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observed_constructor_signature_id": self.signature_id}


@dataclass(frozen=True, slots=True)
class RegisteredConstructorCapabilitySpecV1:
    capability_key: str
    constructor_key: str
    vertex_count: int
    edge_count: int
    sorted_degree_sequence: tuple[int, ...]
    connected_component_sizes: tuple[int, ...]
    triangle_count: int

    def __post_init__(self) -> None:
        if (
            type(self.capability_key) is not str
            or not self.capability_key
            or type(self.constructor_key) is not str
            or not self.constructor_key
            or type(self.vertex_count) is not int
            or type(self.edge_count) is not int
            or type(self.sorted_degree_sequence) is not tuple
            or type(self.connected_component_sizes) is not tuple
            or type(self.triangle_count) is not int
        ):
            _fail("constructor capability spec is malformed")

    def matches(self, signature: ObservedGraphConstructorSignatureV1) -> bool:
        return (
            self.vertex_count,
            self.edge_count,
            self.sorted_degree_sequence,
            self.connected_component_sizes,
            self.triangle_count,
        ) == (
            signature.vertex_count,
            signature.edge_count,
            signature.sorted_degree_sequence,
            signature.connected_component_sizes,
            signature.triangle_count,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "capability_key": self.capability_key,
            "constructor_key": self.constructor_key,
            "required_vertex_count": self.vertex_count,
            "required_edge_count": self.edge_count,
            "required_sorted_degree_sequence": list(self.sorted_degree_sequence),
            "required_connected_component_sizes": list(self.connected_component_sizes),
            "required_triangle_count": self.triangle_count,
        }


REGISTERED_CAPABILITY_SPECS = (
    RegisteredConstructorCapabilitySpecV1(
        "W5_OBSERVED_GRAPH_SIGNATURE_V1",
        "W5_CHECKPOINT_OVERLAY_V1",
        5,
        8,
        (3, 3, 3, 3, 4),
        (5,),
        4,
    ),
    RegisteredConstructorCapabilitySpecV1(
        "K6_COMPLETE_OBSERVED_GRAPH_SIGNATURE_V1",
        "K6_CHECKPOINT_OVERLAY_V1",
        6,
        15,
        (5, 5, 5, 5, 5, 5),
        (6,),
        20,
    ),
)


@dataclass(frozen=True, slots=True)
class ObservedConstructorCapabilityCandidateV1:
    _issuer: InitVar[object]
    signature_id: str
    ordinal: int
    spec: RegisteredConstructorCapabilitySpecV1
    matched: bool
    mismatch_fields: tuple[str, ...]
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CANDIDATE_ISSUER
            or type(self.ordinal) is not int
            or not 0 <= self.ordinal < len(REGISTERED_CAPABILITY_SPECS)
            or self.spec != REGISTERED_CAPABILITY_SPECS[self.ordinal]
            or type(self.matched) is not bool
            or type(self.mismatch_fields) is not tuple
            or self.matched != (not self.mismatch_fields)
            or self.mismatch_fields != tuple(sorted(set(self.mismatch_fields)))
        ):
            _fail("constructor capability candidate changed")
        _cid(self.signature_id, "candidate signature")
        object.__setattr__(
            self, "_candidate_id", content_id(CANDIDATE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_constructor_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "observed_constructor_signature_id": self.signature_id,
            "candidate_ordinal": self.ordinal,
            "capability_spec": self.spec.to_document(),
            "matched": self.matched,
            "mismatch_fields": list(self.mismatch_fields),
            "complete_registered_invariant_comparison": True,
            "context_key_comparison_performed": False,
        }

    @property
    def candidate_id(self) -> str:
        current = content_id(CANDIDATE_DOMAIN, self._payload())
        if current != self._candidate_id:
            _fail("constructor capability candidate identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "constructor_capability_candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class ObservedConstructorCapabilityDecisionV1:
    _issuer: InitVar[object]
    signature: ObservedGraphConstructorSignatureV1
    candidates: tuple[ObservedConstructorCapabilityCandidateV1, ...]
    outcome: str
    selected_candidate_id: str | None
    selected_capability_key: str | None
    selected_constructor_key: str | None
    _decision_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        matches = tuple(row for row in self.candidates if row.matched)
        selected = matches[0] if len(matches) == 1 else None
        if (
            _issuer is not _DECISION_ISSUER
            or type(self.signature) is not ObservedGraphConstructorSignatureV1
            or type(self.candidates) is not tuple
            or len(self.candidates) != len(REGISTERED_CAPABILITY_SPECS)
            or tuple(row.ordinal for row in self.candidates) != tuple(range(len(self.candidates)))
            or any(row.signature_id != self.signature.signature_id for row in self.candidates)
            or len(matches) > 1
            or self.outcome != ("CAPABILITY_MATCH" if selected is not None else "NO_SOUND_CAPABILITY")
            or self.selected_candidate_id != (None if selected is None else selected.candidate_id)
            or self.selected_capability_key != (None if selected is None else selected.spec.capability_key)
            or self.selected_constructor_key != (None if selected is None else selected.spec.constructor_key)
        ):
            _fail("constructor capability decision changed")
        object.__setattr__(
            self, "_decision_id", content_id(DECISION_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_constructor_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "observed_constructor_signature_id": self.signature.signature_id,
            "ordered_candidate_ids": [row.candidate_id for row in self.candidates],
            "decision_outcome": self.outcome,
            "selected_candidate_id": self.selected_candidate_id,
            "selected_capability_key": self.selected_capability_key,
            "selected_constructor_key": self.selected_constructor_key,
            "selection_rule": "unique_exact_observed_graph_invariant_match_v1",
            "context_key_registry_authoritative": False,
            "fixed_human_capability_signature_registry": True,
            "automatic_coordinate_primitive_invention_claimed": False,
            "broad_graph_generalization_claimed": False,
            "nearby_capability_transfer_allowed": False,
            "ground_access_authorized_here": False,
        }

    @property
    def decision_id(self) -> str:
        current = content_id(DECISION_DOMAIN, self._payload())
        if current != self._decision_id:
            _fail("constructor capability decision identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "signature": self.signature.to_document(),
            "candidates": [row.to_document() for row in self.candidates],
            "constructor_capability_decision_id": self.decision_id,
        }


def observed_graph_constructor_signature_v1(
    context: observer_v1.PublicGraphContextV1,
) -> ObservedGraphConstructorSignatureV1:
    """Compute one label-invariant signature from a frozen public topology."""

    if type(context) is not observer_v1.PublicGraphContextV1:
        _fail("constructor signature requires one exact public graph context")
    topology = context.topology
    edges = tuple(tuple(edge) for edge in topology.edges)
    degrees = [0] * topology.vertex_count
    for left, right in edges:
        degrees[left] += 1
        degrees[right] += 1
    return ObservedGraphConstructorSignatureV1(
        _SIGNATURE_ISSUER,
        context.context_id,
        topology.topology_id,
        topology.vertex_count,
        len(edges),
        tuple(sorted(degrees)),
        _component_sizes(topology.vertex_count, edges),
        _triangle_count(topology.vertex_count, edges),
    )


def propose_observed_constructor_capability_v1(
    context: observer_v1.PublicGraphContextV1,
) -> ObservedConstructorCapabilityDecisionV1:
    """Evaluate all registered capabilities without consulting context keys."""

    signature = observed_graph_constructor_signature_v1(context)
    candidates = []
    fields = (
        ("vertex_count", "vertex_count"),
        ("edge_count", "edge_count"),
        ("sorted_degree_sequence", "sorted_degree_sequence"),
        ("connected_component_sizes", "connected_component_sizes"),
        ("triangle_count", "triangle_count"),
    )
    for ordinal, spec in enumerate(REGISTERED_CAPABILITY_SPECS):
        mismatch = tuple(
            sorted(
                label
                for label, attribute in fields
                if getattr(spec, attribute) != getattr(signature, attribute)
            )
        )
        candidates.append(
            ObservedConstructorCapabilityCandidateV1(
                _CANDIDATE_ISSUER,
                signature.signature_id,
                ordinal,
                spec,
                not mismatch,
                mismatch,
            )
        )
    matches = tuple(row for row in candidates if row.matched)
    selected = matches[0] if len(matches) == 1 else None
    return ObservedConstructorCapabilityDecisionV1(
        _DECISION_ISSUER,
        signature,
        tuple(candidates),
        "CAPABILITY_MATCH" if selected is not None else "NO_SOUND_CAPABILITY",
        None if selected is None else selected.candidate_id,
        None if selected is None else selected.spec.capability_key,
        None if selected is None else selected.spec.constructor_key,
    )


def verify_observed_constructor_capability_v1(
    context: observer_v1.PublicGraphContextV1,
    decision: ObservedConstructorCapabilityDecisionV1,
) -> ObservedConstructorCapabilityDecisionV1:
    """Recompute the structural signature and all candidate comparisons."""

    if type(decision) is not ObservedConstructorCapabilityDecisionV1:
        _fail("constructor capability verifier rejects foreign values")
    expected = propose_observed_constructor_capability_v1(context)
    if decision != expected or decision.decision_id != expected.decision_id:
        _fail("constructor capability differs from observed replay")
    return decision


__all__ = (
    "ConstructionK7ObservedConstructorCapabilityV1Error",
    "LOCAL_DOMAINS",
    "ObservedConstructorCapabilityCandidateV1",
    "ObservedConstructorCapabilityDecisionV1",
    "ObservedGraphConstructorSignatureV1",
    "REGISTERED_CAPABILITY_SPECS",
    "RegisteredConstructorCapabilitySpecV1",
    "observed_graph_constructor_signature_v1",
    "propose_observed_constructor_capability_v1",
    "verify_observed_constructor_capability_v1",
)
