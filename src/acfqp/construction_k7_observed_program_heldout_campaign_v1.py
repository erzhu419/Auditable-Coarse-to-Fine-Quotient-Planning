"""Held-out transfer/no-transfer evaluation for observation-derived programs.

The source programs are synthesized from the frozen W5/K6 training corpus.
Before that synthesis runs, this module freezes one isomorphic W5 relabelling
control, three same-domain OOD graph controls, and one typed LMB cross-domain
control.  Program evaluation reads only a domain schema and observed feature
rows; case labels, expected outcomes, query/value/policy fields, transition
laws, and ground kernels are not program inputs.

This slice evaluates capability-program transfer only.  It does not execute a
constructor, transfer a model, authorize ground access, or claim that the
five graph primitives/operators were automatically invented.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from itertools import combinations
from typing import Any, NoReturn

from acfqp import construction_k7_observed_capability_program_synthesis_v1 as programs_v1
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_CAMPAIGN_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_EVALUATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_OBSERVATION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_PREREGISTRATION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)
from acfqp.relational_graph_core_v1 import GraphTopologyV1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.150"
PROFILE_KEY = "construction_k7_observed_program_heldout_campaign_v1"

OBSERVATION_DOMAIN = CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_OBSERVATION_V1_DOMAIN
PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_PREREGISTRATION_V1_DOMAIN
)
EVALUATION_DOMAIN = CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_EVALUATION_V1_DOMAIN
CAMPAIGN_DOMAIN = CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_CAMPAIGN_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {OBSERVATION_DOMAIN, PREREGISTRATION_DOMAIN, EVALUATION_DOMAIN, CAMPAIGN_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out program campaign domains are not central")

GRAPH_SCHEMA = "GRAPH_TOPOLOGY_INVARIANTS_V1"
LMB_SCHEMA = "LMB_PUBLIC_STRUCTURE_V1"
PROGRAM_MATCH = "PROGRAM_TRANSFER_MATCH"
NO_SOUND_PROGRAM = "NO_SOUND_PROGRAM"
SCHEMA_NO_TRANSFER = "TYPED_SCHEMA_NO_TRANSFER"

_OBSERVATION_ISSUER = object()
_PREREGISTRATION_ISSUER = object()
_EVALUATION_ISSUER = object()
_CAMPAIGN_ISSUER = object()


class ConstructionK7ObservedProgramHeldoutCampaignV1Error(ValueError):
    """A held-out observation, decision, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservedProgramHeldoutCampaignV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservedProgramHeldoutCampaignV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _component_sizes(topology: GraphTopologyV1) -> tuple[int, ...]:
    unseen = set(range(topology.vertex_count))
    sizes: list[int] = []
    while unseen:
        frontier = {min(unseen)}
        seen: set[int] = set()
        while frontier:
            vertex = frontier.pop()
            if vertex in seen:
                continue
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


def _graph_features(topology: GraphTopologyV1) -> tuple[tuple[str, Any], ...]:
    if type(topology) is not GraphTopologyV1:
        _fail("graph features require one exact topology")
    degrees = tuple(
        sorted(len(topology.neighbors(vertex)) for vertex in range(topology.vertex_count))
    )
    values = {
        "connected_component_sizes": _component_sizes(topology),
        "edge_count": len(topology.edges),
        "sorted_degree_sequence": degrees,
        "triangle_count": _triangle_count(topology),
        "vertex_count": topology.vertex_count,
    }
    return tuple((name, values[name]) for name in programs_v1.FEATURES)


def _json_value(value: Any) -> Any:
    return list(value) if type(value) is tuple else value


def _relabel(
    topology: GraphTopologyV1, permutation: tuple[int, ...]
) -> GraphTopologyV1:
    if (
        type(topology) is not GraphTopologyV1
        or type(permutation) is not tuple
        or tuple(sorted(permutation)) != tuple(range(topology.vertex_count))
    ):
        _fail("held-out graph relabelling is malformed")
    edges = tuple(
        sorted(
            tuple(sorted((permutation[left], permutation[right])))
            for left, right in topology.edges
        )
    )
    return GraphTopologyV1(topology.vertex_count, edges)


@dataclass(frozen=True, slots=True)
class HeldoutStructuralObservationV1:
    _issuer: InitVar[object]
    case_key: str
    domain_schema: str
    topology: GraphTopologyV1 | None
    lmb_summary: tuple[tuple[str, int], ...] | None
    relation_kind: str
    source_topology: GraphTopologyV1 | None
    vertex_permutation: tuple[int, ...] | None
    feature_rows: tuple[tuple[str, Any], ...]
    _observation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _OBSERVATION_ISSUER
            or type(self.case_key) is not str
            or not self.case_key
            or self.domain_schema not in {GRAPH_SCHEMA, LMB_SCHEMA}
            or type(self.relation_kind) is not str
            or not self.relation_kind
            or type(self.feature_rows) is not tuple
        ):
            _fail("held-out structural observation is malformed")
        if self.domain_schema == GRAPH_SCHEMA:
            if (
                type(self.topology) is not GraphTopologyV1
                or self.lmb_summary is not None
                or self.feature_rows != _graph_features(self.topology)
            ):
                _fail("held-out graph observation changed")
            if self.vertex_permutation is not None and (
                type(self.vertex_permutation) is not tuple
                or tuple(sorted(self.vertex_permutation))
                != tuple(range(self.topology.vertex_count))
            ):
                _fail("held-out graph permutation changed")
            if (self.source_topology is None) is not (
                self.vertex_permutation is None
            ):
                _fail("held-out relation evidence is incomplete")
            if self.source_topology is not None and (
                type(self.source_topology) is not GraphTopologyV1
                or self.topology != _relabel(
                    self.source_topology, self.vertex_permutation or ()
                )
                or self.topology.topology_id == self.source_topology.topology_id
            ):
                _fail("held-out relabelling evidence changed")
        elif (
            self.topology is not None
            or self.source_topology is not None
            or self.vertex_permutation is not None
            or self.lmb_summary
            != (
                ("buffer_capacity", 3),
                ("layer_count", 6),
                ("program_depth", 2),
                ("tile_type_count", 2),
            )
            or self.feature_rows != self.lmb_summary
        ):
            _fail("held-out LMB observation changed")
        object.__setattr__(
            self, "_observation_id", content_id(OBSERVATION_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        structure = (
            self.topology.to_document()
            if self.topology is not None
            else {name: value for name, value in self.lmb_summary or ()}
        )
        return {
            "schema": "acfqp.construction_k7_observed_program_heldout_observation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "case_key": self.case_key,
            "domain_schema": self.domain_schema,
            "structure": structure,
            "relation_kind": self.relation_kind,
            "source_topology": (
                None
                if self.source_topology is None
                else self.source_topology.to_document()
            ),
            "vertex_permutation": (
                None if self.vertex_permutation is None else list(self.vertex_permutation)
            ),
            "observed_feature_rows": [
                {"primitive": name, "value": _json_value(value)}
                for name, value in self.feature_rows
            ],
            "context_key_query_value_policy_or_ground_input_present": False,
            "transition_row_count": 0,
        }

    @property
    def observation_id(self) -> str:
        current = content_id(OBSERVATION_DOMAIN, self._payload())
        if current != self._observation_id:
            _fail("held-out structural observation identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "heldout_observation_id": self.observation_id}


@dataclass(frozen=True, slots=True)
class HeldoutProgramCaseV1:
    observation: HeldoutStructuralObservationV1
    expected_outcome: str
    expected_constructor_key: str | None

    def __post_init__(self) -> None:
        if (
            type(self.observation) is not HeldoutStructuralObservationV1
            or self.expected_outcome
            not in {PROGRAM_MATCH, NO_SOUND_PROGRAM, SCHEMA_NO_TRANSFER}
            or (self.expected_constructor_key is not None)
            is not (self.expected_outcome == PROGRAM_MATCH)
        ):
            _fail("held-out program case is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "observation": self.observation.to_document(),
            "expected_outcome": self.expected_outcome,
            "expected_constructor_key": self.expected_constructor_key,
        }


def _heldout_cases() -> tuple[HeldoutProgramCaseV1, ...]:
    source_w5 = observer_v1.public_context_by_key_v1("opaque_graph_w5_v0").topology
    permutation = (1, 2, 3, 4, 0)
    relabelled = _relabel(source_w5, permutation)
    if relabelled.topology_id == source_w5.topology_id:
        _fail("W5 held-out relabelling did not change encoded topology identity")
    wheel6_edges = tuple(
        sorted(
            {
                (0, outer) for outer in range(1, 6)
            }
            | {(1, 2), (2, 3), (3, 4), (4, 5), (1, 5)}
        )
    )
    observations = (
        HeldoutStructuralObservationV1(
            _OBSERVATION_ISSUER,
            "W5_ISOMORPHIC_RELABEL_HELDOUT",
            GRAPH_SCHEMA,
            relabelled,
            None,
            "VERTEX_RELABEL_OF_SOURCE_W5",
            source_w5,
            permutation,
            _graph_features(relabelled),
        ),
        HeldoutStructuralObservationV1(
            _OBSERVATION_ISSUER,
            "WHEEL6_OOD",
            GRAPH_SCHEMA,
            GraphTopologyV1(6, wheel6_edges),
            None,
            "SAME_DOMAIN_UNSEEN_STRUCTURE",
            None,
            None,
            _graph_features(GraphTopologyV1(6, wheel6_edges)),
        ),
        HeldoutStructuralObservationV1(
            _OBSERVATION_ISSUER,
            "COMPLETE7_OOD",
            GRAPH_SCHEMA,
            GraphTopologyV1(7, tuple(combinations(range(7), 2))),
            None,
            "CROSS_VERTEX_COUNT_UNSEEN_STRUCTURE",
            None,
            None,
            _graph_features(GraphTopologyV1(7, tuple(combinations(range(7), 2)))),
        ),
        HeldoutStructuralObservationV1(
            _OBSERVATION_ISSUER,
            "PATH6_OOD",
            GRAPH_SCHEMA,
            GraphTopologyV1(6, tuple((index, index + 1) for index in range(5))),
            None,
            "SAME_DOMAIN_UNSEEN_STRUCTURE",
            None,
            None,
            _graph_features(
                GraphTopologyV1(6, tuple((index, index + 1) for index in range(5)))
            ),
        ),
        HeldoutStructuralObservationV1(
            _OBSERVATION_ISSUER,
            "LMB_N6_T2_K3_D2_CROSS_DOMAIN",
            LMB_SCHEMA,
            None,
            (
                ("buffer_capacity", 3),
                ("layer_count", 6),
                ("program_depth", 2),
                ("tile_type_count", 2),
            ),
            "CROSS_DOMAIN_TYPED_CONTROL",
            None,
            None,
            (
                ("buffer_capacity", 3),
                ("layer_count", 6),
                ("program_depth", 2),
                ("tile_type_count", 2),
            ),
        ),
    )
    return (
        HeldoutProgramCaseV1(observations[0], PROGRAM_MATCH, "W5_CHECKPOINT_OVERLAY_V1"),
        HeldoutProgramCaseV1(observations[1], NO_SOUND_PROGRAM, None),
        HeldoutProgramCaseV1(observations[2], NO_SOUND_PROGRAM, None),
        HeldoutProgramCaseV1(observations[3], NO_SOUND_PROGRAM, None),
        HeldoutProgramCaseV1(observations[4], SCHEMA_NO_TRANSFER, None),
    )


@dataclass(frozen=True, slots=True)
class HeldoutProgramPreregistrationV1:
    _issuer: InitVar[object]
    cases: tuple[HeldoutProgramCaseV1, ...]
    _preregistration_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PREREGISTRATION_ISSUER or self.cases != _heldout_cases():
            _fail("held-out program preregistration changed")
        object.__setattr__(
            self,
            "_preregistration_id",
            content_id(PREREGISTRATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_program_heldout_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "ordered_cases": [row.to_document() for row in self.cases],
            "heldout_case_count": len(self.cases),
            "source_program_ids_absent_at_preregistration": True,
            "heldout_observations_frozen_before_source_program_synthesis": True,
            "expected_labels_not_available_to_program_evaluator": True,
        }

    @property
    def preregistration_id(self) -> str:
        current = content_id(PREREGISTRATION_DOMAIN, self._payload())
        if current != self._preregistration_id:
            _fail("held-out program preregistration identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "heldout_preregistration_id": self.preregistration_id}


@dataclass(frozen=True, slots=True)
class HeldoutProgramEvaluationV1:
    _issuer: InitVar[object]
    preregistration_id: str
    observation_id: str
    ordered_proposal_ids: tuple[str, ...]
    matched_proposal_ids: tuple[str, ...]
    outcome: str
    selected_constructor_key: str | None
    _evaluation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.preregistration_id, "held-out evaluation preregistration")
        _cid(self.observation_id, "held-out evaluation observation")
        for value in (*self.ordered_proposal_ids, *self.matched_proposal_ids):
            _cid(value, "held-out program proposal")
        if (
            _issuer is not _EVALUATION_ISSUER
            or type(self.ordered_proposal_ids) is not tuple
            or len(self.ordered_proposal_ids) != 2
            or type(self.matched_proposal_ids) is not tuple
            or not set(self.matched_proposal_ids) <= set(self.ordered_proposal_ids)
            or len(self.matched_proposal_ids) > 1
            or self.outcome not in {PROGRAM_MATCH, NO_SOUND_PROGRAM, SCHEMA_NO_TRANSFER}
            or (self.selected_constructor_key is not None)
            is not (self.outcome == PROGRAM_MATCH)
        ):
            _fail("held-out program evaluation is malformed")
        object.__setattr__(
            self, "_evaluation_id", content_id(EVALUATION_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_program_heldout_evaluation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "heldout_preregistration_id": self.preregistration_id,
            "heldout_observation_id": self.observation_id,
            "ordered_source_program_proposal_ids": list(self.ordered_proposal_ids),
            "matched_source_program_proposal_ids": list(self.matched_proposal_ids),
            "decision_outcome": self.outcome,
            "selected_constructor_key": self.selected_constructor_key,
            "context_key_or_expected_label_read_by_evaluator": False,
            "constructor_invocation_count": 0,
            "model_transfer_attempt_count": 0,
            "ground_access_count": 0,
            "program_transfer_evaluation_only": True,
        }

    @property
    def evaluation_id(self) -> str:
        current = content_id(EVALUATION_DOMAIN, self._payload())
        if current != self._evaluation_id:
            _fail("held-out program evaluation identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "heldout_evaluation_id": self.evaluation_id}


def _matches(
    atoms: tuple[tuple[str, Any], ...], feature_rows: tuple[tuple[str, Any], ...]
) -> bool:
    observed = dict(feature_rows)
    return all(observed.get(name, object()) == literal for name, literal in atoms)


def _evaluate(
    preregistration_id: str,
    observation: HeldoutStructuralObservationV1,
    proposals: tuple[programs_v1.ObservedCapabilityProgramProposalV1, ...],
) -> HeldoutProgramEvaluationV1:
    _cid(preregistration_id, "held-out evaluator preregistration")
    ordered = tuple(row.proposal_id for row in proposals)
    if type(observation) is not HeldoutStructuralObservationV1:
        _fail("held-out evaluator requires one exact observation")
    if observation.domain_schema != GRAPH_SCHEMA:
        matches: tuple[programs_v1.ObservedCapabilityProgramProposalV1, ...] = ()
        outcome = SCHEMA_NO_TRANSFER
    else:
        matches = tuple(
            row
            for row in proposals
            if _matches(row.selected_atoms, observation.feature_rows)
        )
        if len(matches) > 1:
            _fail("held-out observation matched multiple source programs")
        outcome = PROGRAM_MATCH if matches else NO_SOUND_PROGRAM
    selected = matches[0] if matches else None
    return HeldoutProgramEvaluationV1(
        _EVALUATION_ISSUER,
        preregistration_id,
        observation.observation_id,
        ordered,
        tuple(row.proposal_id for row in matches),
        outcome,
        None if selected is None else selected.constructor_key,
    )


@dataclass(frozen=True, slots=True)
class ObservedProgramHeldoutCampaignV1:
    _issuer: InitVar[object]
    preregistration: HeldoutProgramPreregistrationV1
    grammar: programs_v1.ObservedCapabilityProgramGrammarV1
    corpus: programs_v1.ObservedCapabilityProgramCorpusV1
    proposals: tuple[programs_v1.ObservedCapabilityProgramProposalV1, ...]
    evaluations: tuple[HeldoutProgramEvaluationV1, ...]
    _campaign_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CAMPAIGN_ISSUER
            or type(self.preregistration) is not HeldoutProgramPreregistrationV1
            or type(self.grammar) is not programs_v1.ObservedCapabilityProgramGrammarV1
            or type(self.corpus) is not programs_v1.ObservedCapabilityProgramCorpusV1
            or self.corpus.grammar_id != self.grammar.grammar_id
            or type(self.proposals) is not tuple
            or tuple(row.constructor_key for row in self.proposals)
            != ("W5_CHECKPOINT_OVERLAY_V1", "K6_CHECKPOINT_OVERLAY_V1")
            or tuple(row.outcome for row in self.evaluations)
            != tuple(row.expected_outcome for row in self.preregistration.cases)
            or tuple(row.selected_constructor_key for row in self.evaluations)
            != tuple(row.expected_constructor_key for row in self.preregistration.cases)
        ):
            _fail("held-out program campaign changed")
        object.__setattr__(
            self, "_campaign_id", content_id(CAMPAIGN_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_program_heldout_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "heldout_preregistration_id": self.preregistration.preregistration_id,
            "source_program_grammar_id": self.grammar.grammar_id,
            "source_program_corpus_id": self.corpus.corpus_id,
            "ordered_source_program_proposal_ids": [
                row.proposal_id for row in self.proposals
            ],
            "ordered_heldout_evaluation_ids": [
                row.evaluation_id for row in self.evaluations
            ],
            "heldout_case_count": len(self.evaluations),
            "isomorphic_positive_program_transfer_count": 1,
            "same_domain_no_transfer_count": 3,
            "cross_vertex_count_no_transfer_count": 1,
            "cross_domain_typed_no_transfer_count": 1,
            "constructor_invocation_count": 0,
            "model_transfer_attempt_count": 0,
            "ground_access_count": 0,
            "heldout_program_transfer_evaluation_complete": True,
            "human_registered_primitive_and_operator_vocabulary": True,
            "automatic_primitive_or_operator_invention_claimed": False,
            "constructor_or_model_transfer_authority_present": False,
            "broad_graph_or_cross_domain_generalization_claimed": False,
            "official_execution_allowed": False,
        }

    @property
    def campaign_id(self) -> str:
        current = content_id(CAMPAIGN_DOMAIN, self._payload())
        if current != self._campaign_id:
            _fail("held-out program campaign identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "preregistration": self.preregistration.to_document(),
            "source_program_grammar": self.grammar.to_document(),
            "source_program_corpus": self.corpus.to_document(),
            "source_program_proposals": [
                {
                    **row.to_document(),
                    "candidates": [candidate.to_document() for candidate in row.candidates],
                }
                for row in self.proposals
            ],
            "heldout_evaluations": [row.to_document() for row in self.evaluations],
            "heldout_program_campaign_id": self.campaign_id,
        }


def run_observed_program_heldout_campaign_v1() -> ObservedProgramHeldoutCampaignV1:
    preregistration = HeldoutProgramPreregistrationV1(
        _PREREGISTRATION_ISSUER, _heldout_cases()
    )
    grammar = programs_v1.freeze_observed_capability_program_grammar_v1()
    corpus = programs_v1.freeze_observed_capability_program_corpus_v1(grammar)
    proposals = tuple(
        programs_v1.synthesize_observed_capability_program_v1(
            grammar=grammar,
            corpus=corpus,
            family_key=family,
            constructor_key=constructor,
        )
        for family, constructor, _context_key in programs_v1.CONSTRUCTOR_EXAMPLES
    )
    evaluations = tuple(
        _evaluate(preregistration.preregistration_id, case.observation, proposals)
        for case in preregistration.cases
    )
    return ObservedProgramHeldoutCampaignV1(
        _CAMPAIGN_ISSUER,
        preregistration,
        grammar,
        corpus,
        proposals,
        evaluations,
    )


def verify_observed_program_heldout_campaign_v1(
    campaign: ObservedProgramHeldoutCampaignV1,
) -> ObservedProgramHeldoutCampaignV1:
    if type(campaign) is not ObservedProgramHeldoutCampaignV1:
        _fail("held-out program verifier rejects foreign values")
    expected = run_observed_program_heldout_campaign_v1()
    if campaign != expected or campaign.campaign_id != expected.campaign_id:
        _fail("held-out program campaign differs from exact replay")
    return campaign


__all__ = (
    "ConstructionK7ObservedProgramHeldoutCampaignV1Error",
    "GRAPH_SCHEMA",
    "HeldoutProgramCaseV1",
    "HeldoutProgramEvaluationV1",
    "HeldoutProgramPreregistrationV1",
    "HeldoutStructuralObservationV1",
    "LMB_SCHEMA",
    "LOCAL_DOMAINS",
    "NO_SOUND_PROGRAM",
    "ObservedProgramHeldoutCampaignV1",
    "PROGRAM_MATCH",
    "SCHEMA_NO_TRANSFER",
    "run_observed_program_heldout_campaign_v1",
    "verify_observed_program_heldout_campaign_v1",
)
