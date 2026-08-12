"""Synthesize constructor-capability programs from observed graph features.

The previous capability authority compared an observed signature with two
hand-written rows.  This successor keeps a small, preregistered relational
language, but derives each literal value and the resulting conjunction from a
frozen observation corpus.  For every positive constructor example it
enumerates the complete non-empty subset lattice of the five registered
features.  Single-feature counterfactual controls force the selected program
to depend on every feature; nearby real structures are independent negative
controls.

The result is deliberately bounded.  The primitive and operator vocabulary,
the two constructor labels, and the finite training corpus remain human
registered.  This is program proposal inside that language, not primitive
invention or broad graph-theorem discovery.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from itertools import combinations
from typing import Any, NoReturn

from acfqp import construction_k7_observed_constructor_capability_v1 as signature_v1
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVED_PROGRAM_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_CORPUS_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_DECISION_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_GRAMMAR_V1_DOMAIN,
    CONSTRUCTION_K7_OBSERVED_PROGRAM_PROPOSAL_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.145"
PROFILE_KEY = "construction_k7_observed_capability_program_synthesis_v1"

GRAMMAR_DOMAIN = CONSTRUCTION_K7_OBSERVED_PROGRAM_GRAMMAR_V1_DOMAIN
CORPUS_DOMAIN = CONSTRUCTION_K7_OBSERVED_PROGRAM_CORPUS_V1_DOMAIN
CANDIDATE_DOMAIN = CONSTRUCTION_K7_OBSERVED_PROGRAM_CANDIDATE_V1_DOMAIN
PROPOSAL_DOMAIN = CONSTRUCTION_K7_OBSERVED_PROGRAM_PROPOSAL_V1_DOMAIN
DECISION_DOMAIN = CONSTRUCTION_K7_OBSERVED_PROGRAM_DECISION_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {GRAMMAR_DOMAIN, CORPUS_DOMAIN, CANDIDATE_DOMAIN, PROPOSAL_DOMAIN, DECISION_DOMAIN}
)
if len(LOCAL_DOMAINS) != 5 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("observed program-synthesis domains are not central")

FEATURES = (
    "connected_component_sizes",
    "edge_count",
    "sorted_degree_sequence",
    "triangle_count",
    "vertex_count",
)
OPERATORS = ("EQUALS", "AND")
CONSTRUCTOR_EXAMPLES = (
    ("W5", "W5_CHECKPOINT_OVERLAY_V1", "opaque_graph_w5_v0"),
    ("K6", "K6_CHECKPOINT_OVERLAY_V1", "opaque_graph_k6_v0"),
)
REAL_NEGATIVE_CONTEXT_KEYS = (
    "opaque_graph_w5_v0",
    "opaque_graph_k6_v0",
    "opaque_graph_k6_minus_edge_v0",
)
EXPECTED_CANDIDATE_COUNT_PER_CONSTRUCTOR = (1 << len(FEATURES)) - 1

_GRAMMAR_ISSUER = object()
_CORPUS_ISSUER = object()
_CANDIDATE_ISSUER = object()
_PROPOSAL_ISSUER = object()
_DECISION_ISSUER = object()


class ConstructionK7ObservedCapabilityProgramSynthesisV1Error(ValueError):
    """The grammar, corpus, enumerated program, or decision changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ObservedCapabilityProgramSynthesisV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ObservedCapabilityProgramSynthesisV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _feature_values(
    signature: signature_v1.ObservedGraphConstructorSignatureV1,
) -> tuple[tuple[str, Any], ...]:
    if type(signature) is not signature_v1.ObservedGraphConstructorSignatureV1:
        _fail("program features require one exact observed signature")
    return tuple((name, getattr(signature, name)) for name in FEATURES)


def _json_value(value: Any) -> Any:
    return list(value) if type(value) is tuple else value


def _mutated_value(name: str, value: Any) -> Any:
    if type(value) is int:
        return value + 1
    if type(value) is tuple and value:
        changed = list(value)
        changed[0] += 1
        return tuple(sorted(changed))
    _fail(f"feature {name!r} has no registered mutation operator")


@dataclass(frozen=True, slots=True)
class ObservedCapabilityProgramGrammarV1:
    _issuer: InitVar[object]
    primitives: tuple[str, ...]
    operators: tuple[str, ...]
    _grammar_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _GRAMMAR_ISSUER
            or self.primitives != FEATURES
            or self.operators != OPERATORS
        ):
            _fail("observed capability program grammar changed")
        object.__setattr__(self, "_grammar_id", content_id(GRAMMAR_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_program_grammar.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "ordered_primitives": list(self.primitives),
            "ordered_operators": list(self.operators),
            "maximum_conjunction_atom_count": len(FEATURES),
            "literal_values_must_come_from_positive_observations": True,
            "context_key_query_value_policy_or_ground_oracle_primitive_present": False,
            "human_registered_primitive_and_operator_vocabulary": True,
            "automatic_primitive_or_operator_invention_claimed": False,
        }

    @property
    def grammar_id(self) -> str:
        current = content_id(GRAMMAR_DOMAIN, self._payload())
        if current != self._grammar_id:
            _fail("observed program grammar identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observed_program_grammar_id": self.grammar_id}


@dataclass(frozen=True, slots=True)
class ObservedCapabilityProgramCorpusV1:
    _issuer: InitVar[object]
    grammar_id: str
    real_signatures: tuple[signature_v1.ObservedGraphConstructorSignatureV1, ...]
    _corpus_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.grammar_id, "program grammar")
        expected = tuple(
            signature_v1.observed_graph_constructor_signature_v1(
                observer_v1.public_context_by_key_v1(key)
            )
            for key in REAL_NEGATIVE_CONTEXT_KEYS
        )
        if (
            _issuer is not _CORPUS_ISSUER
            or type(self.real_signatures) is not tuple
            or self.real_signatures != expected
        ):
            _fail("observed capability program corpus changed")
        object.__setattr__(self, "_corpus_id", content_id(CORPUS_DOMAIN, self._payload()))

    @property
    def by_context_id(self) -> dict[str, signature_v1.ObservedGraphConstructorSignatureV1]:
        return {row.context_id: row for row in self.real_signatures}

    def positive_signature(self, family_key: str) -> signature_v1.ObservedGraphConstructorSignatureV1:
        matches = [
            signature
            for family, _constructor, context_key in CONSTRUCTOR_EXAMPLES
            if family == family_key
            for signature in self.real_signatures
            if signature.context_id
            == observer_v1.public_context_by_key_v1(context_key).context_id
        ]
        if len(matches) != 1:
            _fail("constructor corpus has no unique positive signature")
        return matches[0]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_program_corpus.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "observed_program_grammar_id": self.grammar_id,
            "ordered_real_signature_ids": [row.signature_id for row in self.real_signatures],
            "constructor_labels": [
                {
                    "family_key": family,
                    "constructor_key": constructor,
                    "positive_context_id": observer_v1.public_context_by_key_v1(context_key).context_id,
                }
                for family, constructor, context_key in CONSTRUCTOR_EXAMPLES
            ],
            "single_feature_counterfactual_control_count_per_constructor": len(FEATURES),
            "real_nearby_negative_control_present": True,
            "all_corpus_identities_frozen_before_subset_enumeration": True,
            "context_keys_are_labels_not_program_inputs": True,
            "real_signatures": [row.to_document() for row in self.real_signatures],
        }

    @property
    def corpus_id(self) -> str:
        current = content_id(CORPUS_DOMAIN, self._payload())
        if current != self._corpus_id:
            _fail("observed program corpus identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observed_program_corpus_id": self.corpus_id}


def _program_matches(
    atoms: tuple[tuple[str, Any], ...], values: tuple[tuple[str, Any], ...]
) -> bool:
    by_name = dict(values)
    return all(name in by_name and by_name[name] == expected for name, expected in atoms)


def _evaluation_rows(
    *,
    corpus: ObservedCapabilityProgramCorpusV1,
    family_key: str,
    atoms: tuple[tuple[str, Any], ...],
) -> tuple[tuple[str, bool, bool], ...]:
    positive = corpus.positive_signature(family_key)
    positive_values = _feature_values(positive)
    rows: list[tuple[str, bool, bool]] = [
        (f"POSITIVE:{positive.signature_id}", True, _program_matches(atoms, positive_values))
    ]
    for signature in corpus.real_signatures:
        if signature.signature_id == positive.signature_id:
            continue
        rows.append(
            (
                f"REAL_NEGATIVE:{signature.signature_id}",
                False,
                _program_matches(atoms, _feature_values(signature)),
            )
        )
    for feature_name, original in positive_values:
        mutated = tuple(
            (
                name,
                _mutated_value(name, value) if name == feature_name else value,
            )
            for name, value in positive_values
        )
        rows.append(
            (
                f"SINGLE_FEATURE_COUNTERFACTUAL:{feature_name}",
                False,
                _program_matches(atoms, mutated),
            )
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class ObservedCapabilityProgramCandidateV1:
    _issuer: InitVar[object]
    grammar_id: str
    corpus_id: str
    family_key: str
    constructor_key: str
    candidate_ordinal: int
    atoms: tuple[tuple[str, Any], ...]
    evaluation_rows: tuple[tuple[str, bool, bool], ...]
    accepted: bool
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.grammar_id, "candidate grammar")
        _cid(self.corpus_id, "candidate corpus")
        if (
            _issuer is not _CANDIDATE_ISSUER
            or (self.family_key, self.constructor_key)
            not in {(row[0], row[1]) for row in CONSTRUCTOR_EXAMPLES}
            or type(self.candidate_ordinal) is not int
            or not 0 <= self.candidate_ordinal < EXPECTED_CANDIDATE_COUNT_PER_CONSTRUCTOR
            or type(self.atoms) is not tuple
            or not self.atoms
            or tuple(name for name, _value in self.atoms)
            != tuple(sorted(name for name, _value in self.atoms))
            or not set(name for name, _value in self.atoms) <= set(FEATURES)
            or type(self.evaluation_rows) is not tuple
            or self.accepted != all(observed == expected for _key, expected, observed in self.evaluation_rows)
        ):
            _fail("observed program candidate changed")
        object.__setattr__(
            self, "_candidate_id", content_id(CANDIDATE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_program_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "observed_program_grammar_id": self.grammar_id,
            "observed_program_corpus_id": self.corpus_id,
            "family_key": self.family_key,
            "constructor_key": self.constructor_key,
            "candidate_ordinal": self.candidate_ordinal,
            "atoms": [
                {"primitive": name, "operator": "EQUALS", "observed_value": _json_value(value)}
                for name, value in self.atoms
            ],
            "evaluation_rows": [
                {"example_key": key, "expected": expected, "observed": observed}
                for key, expected, observed in self.evaluation_rows
            ],
            "accepted": self.accepted,
            "context_key_read_during_program_evaluation": False,
        }

    @property
    def candidate_id(self) -> str:
        current = content_id(CANDIDATE_DOMAIN, self._payload())
        if current != self._candidate_id:
            _fail("observed program candidate identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observed_program_candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class ObservedCapabilityProgramProposalV1:
    _issuer: InitVar[object]
    grammar: ObservedCapabilityProgramGrammarV1
    corpus: ObservedCapabilityProgramCorpusV1
    family_key: str
    constructor_key: str
    candidates: tuple[ObservedCapabilityProgramCandidateV1, ...]
    selected_candidate_id: str
    selected_atoms: tuple[tuple[str, Any], ...]
    _proposal_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        accepted = tuple(row for row in self.candidates if row.accepted)
        selected = accepted[0] if len(accepted) == 1 else None
        if (
            _issuer is not _PROPOSAL_ISSUER
            or type(self.grammar) is not ObservedCapabilityProgramGrammarV1
            or type(self.corpus) is not ObservedCapabilityProgramCorpusV1
            or self.corpus.grammar_id != self.grammar.grammar_id
            or len(self.candidates) != EXPECTED_CANDIDATE_COUNT_PER_CONSTRUCTOR
            or tuple(row.candidate_ordinal for row in self.candidates)
            != tuple(range(EXPECTED_CANDIDATE_COUNT_PER_CONSTRUCTOR))
            or any(
                row.grammar_id != self.grammar.grammar_id
                or row.corpus_id != self.corpus.corpus_id
                or row.family_key != self.family_key
                or row.constructor_key != self.constructor_key
                for row in self.candidates
            )
            or selected is None
            or self.selected_candidate_id != selected.candidate_id
            or self.selected_atoms != selected.atoms
            or tuple(name for name, _value in self.selected_atoms) != FEATURES
        ):
            _fail("observed program proposal is not the unique robust program")
        object.__setattr__(self, "_proposal_id", content_id(PROPOSAL_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_program_proposal.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "observed_program_grammar_id": self.grammar.grammar_id,
            "observed_program_corpus_id": self.corpus.corpus_id,
            "family_key": self.family_key,
            "constructor_key": self.constructor_key,
            "ordered_candidate_ids": [row.candidate_id for row in self.candidates],
            "selected_candidate_id": self.selected_candidate_id,
            "selected_atoms": [
                {"primitive": name, "operator": "EQUALS", "observed_value": _json_value(value)}
                for name, value in self.selected_atoms
            ],
            "candidate_count": EXPECTED_CANDIDATE_COUNT_PER_CONSTRUCTOR,
            "selection_rule": "UNIQUE_COMPLETE_CORPUS_AND_SINGLE_FEATURE_CONTROL_SEPARATOR",
            "literal_values_observation_derived": True,
            "fixed_human_signature_value_table_used": False,
            "human_registered_primitive_and_operator_vocabulary": True,
            "automatic_primitive_or_operator_invention_claimed": False,
        }

    @property
    def proposal_id(self) -> str:
        current = content_id(PROPOSAL_DOMAIN, self._payload())
        if current != self._proposal_id:
            _fail("observed program proposal identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observed_program_proposal_id": self.proposal_id}


@dataclass(frozen=True, slots=True)
class ObservedCapabilityProgramDecisionV1:
    _issuer: InitVar[object]
    signature: signature_v1.ObservedGraphConstructorSignatureV1
    grammar: ObservedCapabilityProgramGrammarV1
    corpus: ObservedCapabilityProgramCorpusV1
    proposals: tuple[ObservedCapabilityProgramProposalV1, ...]
    outcome: str
    selected_proposal_id: str | None
    selected_constructor_key: str | None
    _decision_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        matches = tuple(
            row
            for row in self.proposals
            if _program_matches(row.selected_atoms, _feature_values(self.signature))
        )
        selected = matches[0] if len(matches) == 1 else None
        if (
            _issuer is not _DECISION_ISSUER
            or type(self.signature) is not signature_v1.ObservedGraphConstructorSignatureV1
            or type(self.grammar) is not ObservedCapabilityProgramGrammarV1
            or type(self.corpus) is not ObservedCapabilityProgramCorpusV1
            or self.corpus.grammar_id != self.grammar.grammar_id
            or type(self.proposals) is not tuple
            or len(self.proposals) != len(CONSTRUCTOR_EXAMPLES)
            or len(matches) > 1
            or self.outcome != ("PROGRAM_MATCH" if selected is not None else "NO_SOUND_PROGRAM")
            or self.selected_proposal_id != (None if selected is None else selected.proposal_id)
            or self.selected_constructor_key != (None if selected is None else selected.constructor_key)
        ):
            _fail("observed capability program decision changed")
        object.__setattr__(self, "_decision_id", content_id(DECISION_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_observed_program_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "target_observed_signature_id": self.signature.signature_id,
            "observed_program_grammar_id": self.grammar.grammar_id,
            "observed_program_corpus_id": self.corpus.corpus_id,
            "ordered_program_proposal_ids": [row.proposal_id for row in self.proposals],
            "decision_outcome": self.outcome,
            "selected_program_proposal_id": self.selected_proposal_id,
            "selected_constructor_key": self.selected_constructor_key,
            "selection_rule": "UNIQUE_OBSERVATION_DERIVED_PROGRAM_MATCH",
            "context_key_used_as_program_input": False,
            "fixed_human_signature_value_table_authoritative": False,
            "nearby_program_transfer_allowed": False,
            "ground_access_authorized_here": False,
            "broad_graph_generalization_claimed": False,
        }

    @property
    def decision_id(self) -> str:
        current = content_id(DECISION_DOMAIN, self._payload())
        if current != self._decision_id:
            _fail("observed program decision identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "target_signature": self.signature.to_document(),
            "grammar": self.grammar.to_document(),
            "corpus": self.corpus.to_document(),
            "proposals": [row.to_document() for row in self.proposals],
            "observed_program_decision_id": self.decision_id,
        }


def freeze_observed_capability_program_grammar_v1() -> ObservedCapabilityProgramGrammarV1:
    return ObservedCapabilityProgramGrammarV1(_GRAMMAR_ISSUER, FEATURES, OPERATORS)


def freeze_observed_capability_program_corpus_v1(
    grammar: ObservedCapabilityProgramGrammarV1,
) -> ObservedCapabilityProgramCorpusV1:
    if type(grammar) is not ObservedCapabilityProgramGrammarV1:
        _fail("program corpus requires one exact grammar")
    signatures = tuple(
        signature_v1.observed_graph_constructor_signature_v1(
            observer_v1.public_context_by_key_v1(key)
        )
        for key in REAL_NEGATIVE_CONTEXT_KEYS
    )
    return ObservedCapabilityProgramCorpusV1(_CORPUS_ISSUER, grammar.grammar_id, signatures)


def synthesize_observed_capability_program_v1(
    *,
    grammar: ObservedCapabilityProgramGrammarV1,
    corpus: ObservedCapabilityProgramCorpusV1,
    family_key: str,
    constructor_key: str,
) -> ObservedCapabilityProgramProposalV1:
    """Enumerate every non-empty conjunction and select the unique robust one."""

    if (family_key, constructor_key) not in {
        (row[0], row[1]) for row in CONSTRUCTOR_EXAMPLES
    }:
        _fail("program synthesis received an unregistered constructor label")
    positive = corpus.positive_signature(family_key)
    values = dict(_feature_values(positive))
    atom_sets = tuple(
        atoms
        for size in range(1, len(FEATURES) + 1)
        for atoms in combinations(FEATURES, size)
    )
    candidates = []
    for ordinal, names in enumerate(atom_sets):
        atoms = tuple((name, values[name]) for name in names)
        evaluations = _evaluation_rows(corpus=corpus, family_key=family_key, atoms=atoms)
        candidates.append(
            ObservedCapabilityProgramCandidateV1(
                _CANDIDATE_ISSUER,
                grammar.grammar_id,
                corpus.corpus_id,
                family_key,
                constructor_key,
                ordinal,
                atoms,
                evaluations,
                all(observed == expected for _key, expected, observed in evaluations),
            )
        )
    accepted = tuple(row for row in candidates if row.accepted)
    if len(accepted) != 1:
        _fail("registered mutation controls did not identify one program")
    return ObservedCapabilityProgramProposalV1(
        _PROPOSAL_ISSUER,
        grammar,
        corpus,
        family_key,
        constructor_key,
        tuple(candidates),
        accepted[0].candidate_id,
        accepted[0].atoms,
    )


def propose_observed_capability_program_v1(
    context: observer_v1.PublicGraphContextV1,
) -> ObservedCapabilityProgramDecisionV1:
    """Synthesize the frozen programs, then evaluate a target observation."""

    if type(context) is not observer_v1.PublicGraphContextV1:
        _fail("program decision requires one exact public graph context")
    grammar = freeze_observed_capability_program_grammar_v1()
    corpus = freeze_observed_capability_program_corpus_v1(grammar)
    proposals = tuple(
        synthesize_observed_capability_program_v1(
            grammar=grammar,
            corpus=corpus,
            family_key=family,
            constructor_key=constructor,
        )
        for family, constructor, _context_key in CONSTRUCTOR_EXAMPLES
    )
    target = signature_v1.observed_graph_constructor_signature_v1(context)
    matches = tuple(
        row for row in proposals if _program_matches(row.selected_atoms, _feature_values(target))
    )
    selected = matches[0] if len(matches) == 1 else None
    return ObservedCapabilityProgramDecisionV1(
        _DECISION_ISSUER,
        target,
        grammar,
        corpus,
        proposals,
        "PROGRAM_MATCH" if selected is not None else "NO_SOUND_PROGRAM",
        None if selected is None else selected.proposal_id,
        None if selected is None else selected.constructor_key,
    )


def verify_observed_capability_program_v1(
    context: observer_v1.PublicGraphContextV1,
    decision: ObservedCapabilityProgramDecisionV1,
) -> ObservedCapabilityProgramDecisionV1:
    if type(decision) is not ObservedCapabilityProgramDecisionV1:
        _fail("program verifier rejects foreign values")
    expected = propose_observed_capability_program_v1(context)
    if decision != expected or decision.decision_id != expected.decision_id:
        _fail("observed program decision differs from complete replay")
    return decision


__all__ = (
    "CONSTRUCTOR_EXAMPLES",
    "ConstructionK7ObservedCapabilityProgramSynthesisV1Error",
    "EXPECTED_CANDIDATE_COUNT_PER_CONSTRUCTOR",
    "FEATURES",
    "LOCAL_DOMAINS",
    "ObservedCapabilityProgramCandidateV1",
    "ObservedCapabilityProgramCorpusV1",
    "ObservedCapabilityProgramDecisionV1",
    "ObservedCapabilityProgramGrammarV1",
    "ObservedCapabilityProgramProposalV1",
    "freeze_observed_capability_program_corpus_v1",
    "freeze_observed_capability_program_grammar_v1",
    "propose_observed_capability_program_v1",
    "synthesize_observed_capability_program_v1",
    "verify_observed_capability_program_v1",
)
